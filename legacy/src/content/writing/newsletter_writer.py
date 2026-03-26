import json
import os
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import markdown

from config.logging_config import fetch_logger as logger
from database.processed_database import ProcessedDatabase
from services.openai.openai_client import OpenAIClient

BASE_SYSTEM_PROMPT = """\
You are an expert travel newsletter writer for "ByteSize Travel Deals." \
Your task is to create an engaging tri-weekly newsletter highlighting \
the best travel deals, destination guides, and travel news. I'll provide \
you with selected travel content including deals, guides, tips, and news.

Create a comprehensive newsletter with these sections:

1. **Introduction** - A warm, personalized greeting that establishes \
the newsletter's theme and connects with readers

2. **FEATURED DEALS** - Highlight 2-3 travel deals with complete details:
- Destination description with cultural context
- Comprehensive pricing information
- Clear booking deadline and travel window
- What makes each offer exceptional value
- Any restrictions or important notes

3. **DESTINATION GUIDES** - In-depth coverage of 1-2 relevant destinations:
- Historical and cultural background
- Specific attractions with context
- Local cuisine recommendations
- Practical visitor information

4. **TRAVEL NEWS** - Latest updates from the travel world:
- Recent developments affecting travelers
- New airline routes or policy changes
- Emerging destinations or trends
- Industry updates relevant to travelers

5. **TRAVEL TIPS** - Substantive advice for travelers:
- Budget-conscious strategies with specific examples
- Packing recommendations for different conditions
- Technology tools that enhance travel experiences
- Cultural etiquette considerations
"""

SEASONAL_SECTION = """\

6. **SEASONAL INSPIRATION** - Thoughtful travel ideas:
- Events and festivals worth planning around
- Weather considerations and preparation
- Seasonal attractions at their peak
"""

FORMATTING_INSTRUCTIONS = """\

7. **Conclusion** - Meaningful closing thoughts with a clear, \
compelling call to action

Guidelines:
- Format in Markdown with clear headings and subheadings
- Use a professional yet conversational tone
- Limit emojis to no more than 2-3 in the entire newsletter
- Vary paragraph length for readability
- Include 1,200-1,700 words
- Highlight value through compelling description
- Create urgency through factual time constraints
- Focus on specific, actionable details
- Include occasional expert insights

IMPORTANT: Structure the markdown with these headings:
# Introduction
# Featured Deals
# Destination Guides
# Travel News
# Travel Tips
"""

HEADING_INSTRUCTIONS = """\
# Conclusion

For each Destination Guide, use a ## heading with the destination name.
For each Featured Deal, use a ## heading with the deal name/destination.
For each Travel News item, use a ## heading with the news title.

Use standard markdown formatting (**bold**, *italic*), lists, [links](url).
"""

# inline styles for email compatibility
STYLE_MAP = {
    "<h1>": (
        '<h1 style="font-size: 28px; font-weight: bold;'
        " color: #2A2A2A; line-height: 34px;"
        ' margin-top: 20px; margin-bottom: 10px;">'
    ),
    "<h2>": (
        '<h2 style="font-size: 24px; font-weight: bold;'
        " color: #2A2A2A; line-height: 30px;"
        ' margin-top: 18px; margin-bottom: 9px;">'
    ),
    "<h3>": (
        '<h3 style="font-size: 20px; font-weight: bold;'
        " color: #2A2A2A; line-height: 26px;"
        ' margin-top: 16px; margin-bottom: 8px;">'
    ),
    "<p>": (
        '<p style="font-size: 16px; line-height: 24px;'
        " margin-top: 10px; margin-bottom: 10px;"
        ' color: #2D2D2D;">'
    ),
    "<ul>": '<ul style="margin-left: 20px; padding-left: 0;">',
    "<ol>": '<ol style="margin-left: 20px; padding-left: 0;">',
    "<li>": '<li style="margin-bottom: 8px; line-height: 24px;">',
    "<a ": (
        '<a style="color: #0c457d; font-weight: bold; text-decoration: underline;" '
    ),
    "<strong>": '<strong style="font-weight: bold;">',
    "<em>": '<em style="font-style: italic;">',
}

SECTION_PATTERNS: dict[str, str] = {
    "introduction": r"# Introduction\s+(.*?)(?=# Featured Deals|\Z)",
    "featured_deals": (r"# Featured Deals\s+(.*?)(?=# Destination Guides|\Z)"),
    "destination_guides": (r"# Destination Guides\s+(.*?)(?=# Travel News|\Z)"),
    "travel_news": r"# Travel News\s+(.*?)(?=# Travel Tips|\Z)",
    "travel_tips": (
        r"# Travel Tips\s+(.*?)"
        r"(?=# Seasonal Inspiration|# Conclusion|\Z)"
    ),
    "conclusion": r"# Conclusion\s+(.*?)(?=\Z)",
}


def _convert_markdown_to_html(markdown_text: str) -> str:
    html = markdown.markdown(markdown_text, extensions=["extra"])
    for tag, styled in STYLE_MAP.items():
        html = html.replace(tag, styled)
    return html


def _extract_subsections(text: str) -> list[tuple[str, str]]:
    return re.findall(
        r"## (.*?)$(.*?)(?=## |\Z)",
        text,
        flags=re.DOTALL | re.MULTILINE,
    )


def _extract_title_and_content(
    text: str,
) -> tuple[str | None, str]:
    title_match = re.search(r"^## (.*?)$", text, flags=re.MULTILINE)
    if title_match:
        title = title_match.group(1).strip()
        content = re.sub(
            r"^## .*?$\n",
            "",
            text,
            count=1,
            flags=re.MULTILINE,
        )
        return title, content
    return None, text


class NewsletterWriter:
    def __init__(
        self,
        processed_db: ProcessedDatabase,
        openai_model: str = "gpt-4.1-mini-2025-04-14",
    ) -> None:
        self.processed_db = processed_db
        self.llm = OpenAIClient(model=openai_model)
        logger.info(
            "NewsletterWriter initialized with model: %s",
            openai_model,
        )

    def _build_system_prompt(self, *, include_seasonal: bool) -> str:
        prompt = BASE_SYSTEM_PROMPT
        if include_seasonal:
            prompt += SEASONAL_SECTION
        prompt += FORMATTING_INSTRUCTIONS
        if include_seasonal:
            prompt += "# Seasonal Inspiration\n"
        prompt += HEADING_INSTRUCTIONS
        return prompt

    @staticmethod
    def _format_section(
        items: list[dict],
        heading: str,
        prefix: str,
        *,
        numbered: bool = False,
    ) -> list[str]:
        if not items:
            return []
        parts = [f"## {heading}"]
        for i, item in enumerate(items):
            title = item.get("title", "No title")
            label = f"{prefix} {i + 1}: {title}" if numbered else f"{prefix}: {title}"
            parts.append(f"### {label}")
            if "deal_data" in item:
                parts.append(f"Deal Data: {item.get('deal_data', '')}")
            parts.append(f"Content: {item.get('content', '')}\n")
        return parts

    def _build_content_text(
        self,
        newsletter_content: dict[str, Any],
        *,
        include_seasonal: bool,
    ) -> str:
        parts = ["# NEWSLETTER CONTENT\n"]

        if "metadata" in newsletter_content:
            meta = newsletter_content["metadata"]
            parts.append("## METADATA")
            parts.append(f"Current Season: {meta.get('season', 'N/A')}")
            parts.append(f"Upcoming Season: {meta.get('upcoming_season', 'N/A')}")
            parts.append(f"Destination Focus: {meta.get('destination_focus', 'N/A')}\n")

        parts.extend(
            self._format_section(
                newsletter_content.get("featured_deals", []),
                "FEATURED DEALS",
                "Deal",
                numbered=True,
            )
        )
        parts.extend(
            self._format_section(
                newsletter_content.get("featured_destination_guides", []),
                "FEATURED DESTINATION GUIDES",
                "Guide",
            )
        )
        parts.extend(
            self._format_section(
                newsletter_content.get("travel_news", []),
                "TRAVEL NEWS",
                "News",
                numbered=True,
            )
        )
        parts.extend(
            self._format_section(
                newsletter_content.get("practical_tips", []),
                "PRACTICAL TIPS",
                "Tip",
            )
        )

        if include_seasonal and "seasonal_experience" in newsletter_content:
            exp = newsletter_content["seasonal_experience"]
            parts.append("## SEASONAL EXPERIENCE")
            parts.append(f"Title: {exp.get('title', 'No title')}")
            parts.append(f"Content: {exp.get('content', '')}\n")

        return "\n".join(parts)

    def _parse_markdown_to_json(
        self,
        md_text: str,
        edition_title: str,
        edition_tagline: str,
        edition_date: str,
        *,
        include_seasonal: bool,
    ) -> dict[str, Any]:
        placeholder_img = "https://placehold.co/600x400/faedca/0c457d?text=Travel"
        placeholder_avatar = "https://placehold.co/80x80/faedca/0c457d?text=JO"

        data: dict[str, Any] = {
            "header": {
                "logo_url": os.getenv("BYTE_SIZE_LOGO", ""),
                "edition_title": edition_title,
                "edition_tagline": edition_tagline,
                "edition_date": edition_date,
            },
            "author": {
                "name": "Johnathan Oneal",
                "avatar_url": placeholder_avatar,
                "date": edition_date,
            },
            "introduction": {"content": ""},
            "featured_deals": [],
            "destination_guides": [],
            "travel_news": {
                "title": "Travel News",
                "items": [],
            },
            "travel_tips": {
                "title": "Smart Travel Tips",
                "content": "",
            },
            "conclusion": {
                "content": "",
                "button_text": "Explore More Deals",
                "button_url": "https://bytesizetravel.com/explore",
            },
            "footer": {
                "social_links": {
                    "facebook": ("https://facebook.com/bytesizetravel"),
                    "twitter": ("https://twitter.com/bytesizetravel"),
                    "instagram": ("https://instagram.com/bytesizetravel"),
                    "linkedin": ("https://linkedin.com/company/bytesizetravel"),
                },
                "unsubscribe_url": "{{unsubscribe_url}}",
            },
        }

        if include_seasonal:
            data["seasonal_inspiration"] = {
                "title": "Spring Travel Inspiration",
                "content": "",
            }

        patterns = dict(SECTION_PATTERNS)
        if include_seasonal:
            patterns["seasonal_inspiration"] = (
                r"# Seasonal Inspiration\s+(.*?)"
                r"(?=# Conclusion|\Z)"
            )

        sections = {
            k: re.search(v, md_text, flags=re.DOTALL) for k, v in patterns.items()
        }

        if sections.get("introduction"):
            data["introduction"]["content"] = _convert_markdown_to_html(
                sections["introduction"].group(1).strip()
            )

        self._parse_deals(data, sections, placeholder_img)
        self._parse_guides(data, sections, placeholder_img)
        self._parse_news(data, sections)
        self._parse_tips(data, sections)

        if include_seasonal and sections.get("seasonal_inspiration"):
            raw = sections["seasonal_inspiration"].group(1).strip()
            title, content = _extract_title_and_content(raw)
            if title:
                data["seasonal_inspiration"]["title"] = title
            data["seasonal_inspiration"]["content"] = _convert_markdown_to_html(content)

        if sections.get("conclusion"):
            data["conclusion"]["content"] = _convert_markdown_to_html(
                sections["conclusion"].group(1).strip()
            )

        return data

    @staticmethod
    def _parse_deals(
        data: dict,
        sections: dict,
        _placeholder_img: str,
    ) -> None:
        if not sections.get("featured_deals"):
            return
        raw = sections["featured_deals"].group(1).strip()
        subs = _extract_subsections(raw)
        if subs:
            for title, content in subs:
                data["featured_deals"].append(
                    {
                        "title": title.strip(),
                        "content": _convert_markdown_to_html(content.strip()),
                        "button_text": "Book Now!",
                        "button_url": ("https://bytesizetravel.com/deals"),
                    }
                )
        else:
            data["featured_deals"].append(
                {
                    "title": "Special Travel Deal",
                    "content": _convert_markdown_to_html(raw),
                    "button_text": "Book Now!",
                    "button_url": "https://bytesizetravel.com/deals",
                }
            )

    @staticmethod
    def _parse_guides(
        data: dict,
        sections: dict,
        placeholder_img: str,
    ) -> None:
        if not sections.get("destination_guides"):
            return
        raw = sections["destination_guides"].group(1).strip()
        subs = _extract_subsections(raw)
        if subs:
            for title, content in subs:
                data["destination_guides"].append(
                    {
                        "title": title.strip(),
                        "content": _convert_markdown_to_html(content.strip()),
                        "image_url": placeholder_img,
                    }
                )
        else:
            data["destination_guides"].append(
                {
                    "title": "Destination Guide",
                    "content": _convert_markdown_to_html(raw),
                    "image_url": placeholder_img,
                }
            )

    @staticmethod
    def _parse_news(data: dict, sections: dict) -> None:
        if not sections.get("travel_news"):
            return
        raw = sections["travel_news"].group(1).strip()
        subs = _extract_subsections(raw)
        if subs:
            for title, content in subs:
                data["travel_news"]["items"].append(
                    {
                        "title": title.strip(),
                        "content": _convert_markdown_to_html(content.strip()),
                    }
                )
        else:
            data["travel_news"]["items"].append(
                {
                    "title": "Travel Industry Updates",
                    "content": _convert_markdown_to_html(raw),
                }
            )

    @staticmethod
    def _parse_tips(data: dict, sections: dict) -> None:
        if not sections.get("travel_tips"):
            return
        raw = sections["travel_tips"].group(1).strip()
        title, content = _extract_title_and_content(raw)
        if title:
            data["travel_tips"]["title"] = title
        data["travel_tips"]["content"] = _convert_markdown_to_html(content)

    def _save_json(
        self,
        newsletter_json: dict[str, Any],
        *,
        mode: str,
    ) -> str:
        if mode == "real":
            json_dir = os.getenv("REAL_JSON_DIR", "")
            prefix = "real"
        else:
            json_dir = os.getenv("TEST_JSON_DIR", "")
            prefix = "test"

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_json_Data_{timestamp}.json"
        filepath = Path(json_dir) / filename
        filepath.write_text(json.dumps(newsletter_json, indent=4))
        logger.info("Saved JSON data to %s", filepath)
        return str(filepath)

    def generate_newsletter(
        self,
        newsletter_content: dict[str, Any],
        *,
        mode: str = "real",
    ) -> dict[str, Any]:
        logger.info("Generating newsletter in %s mode", mode)

        metadata = newsletter_content.get("metadata", {})
        now = datetime.now(tz=UTC)
        edition_date = now.strftime("%B %d, %Y")
        dest = metadata.get("destination_focus", "Global Destinations")
        edition_title = f"Travel Deals: {dest}"
        season = metadata.get("season", "this season")
        edition_tagline = f"Discover amazing deals for {season}"
        include_seasonal = metadata.get("include_seasonal", False)

        system_prompt = self._build_system_prompt(include_seasonal=include_seasonal)
        content_text = self._build_content_text(
            newsletter_content, include_seasonal=include_seasonal
        )

        md_newsletter = self.llm.analyze(system_prompt, content_text)

        newsletter_json = self._parse_markdown_to_json(
            md_newsletter,
            edition_title.title(),
            edition_tagline,
            edition_date,
            include_seasonal=include_seasonal,
        )

        if mode == "real" and "article_ids" in metadata:
            self.update_usage_statistics(metadata["article_ids"])
            logger.info("Updated usage statistics in real mode")

        filepath = self._save_json(newsletter_json, mode=mode)

        if mode == "real":
            unprocessed_file = os.getenv("UNPROCESSED_TEXT_FILE", "")
            if unprocessed_file:
                with Path(unprocessed_file).open("a") as fh:
                    fh.write(f"{filepath}\n")
                logger.info(
                    "Added %s to newsletter files list",
                    filepath,
                )

        return newsletter_json

    def update_usage_statistics(self, article_ids: list[int]) -> None:
        if not article_ids:
            return

        self.processed_db.conn.execute(
            "UPDATE processed_articles"
            " SET used_count = COALESCE(used_count, 0) + 1,"
            "     last_used = datetime('now')"
            " WHERE id IN (SELECT value FROM json_each(?))",
            [json.dumps(article_ids)],
        )
        self.processed_db.conn.commit()
        logger.info(
            "Updated usage statistics for %d articles",
            len(article_ids),
        )

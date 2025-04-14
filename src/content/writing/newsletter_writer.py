import os
import json
import re
import markdown
from datetime import datetime
from typing import Dict, Any, List
from database.processed_database import ProcessedDatabase
from services.openai_client import OpenAIClient
from config.logging_config import fetch_logger as logger

class NewsletterWriter:
    def __init__(self, processed_db, openai_model: str = "gpt-4o-mini"):
        self.processed_db = processed_db
        self.llm = OpenAIClient(model=openai_model)
        logger.info(f"NewsletterWriter initialized with model: {openai_model}")
        
        # A comprehensive system prompt that gives clear instructions
        self.system_prompt = """
        You are an expert travel newsletter writer for "ByteSize Travel Deals." Your task is to create an engaging weekly newsletter highlighting the best travel deals, destination guides, and practical travel tips. I'll provide you with selected travel content including deals, guides, tips, and seasonal experiences.

        Create a comprehensive newsletter with these sections:

        1. **Introduction** - A warm, personalized greeting that establishes the newsletter's theme and connects with readers
        
        2. **FEATURED DEAL** - Highlight the main travel deal with complete details:
        - Destination description with cultural context
        - Comprehensive pricing information
        - Clear booking deadline and travel window
        - What makes this offer exceptional value
        - Any restrictions or important notes

        3. **DESTINATION GUIDES** - In-depth coverage of 2-3 relevant destinations:
        - Historical and cultural background
        - Specific attractions with context on why they matter
        - Local cuisine recommendations
        - Off-the-beaten-path experiences
        - Practical visitor information

        4. **SEASONAL INSPIRATION** - Thoughtful travel ideas aligned with current/upcoming season:
        - Events and festivals worth planning around
        - Weather considerations and preparation
        - Seasonal attractions at their peak
        - Alternative destinations that offer unique seasonal experiences

        5. **TRAVEL TIPS** - Substantive advice for travelers:
        - Budget-conscious strategies with specific examples
        - Packing recommendations for different conditions
        - Technology tools that enhance travel experiences
        - Cultural etiquette considerations

        6. **Conclusion** - Meaningful closing thoughts with a clear, compelling call to action

        Guidelines:
        - Format in Markdown with clear, hierarchical headings and subheadings
        - Use a professional yet conversational tone that balances enthusiasm with expertise
        - Limit emojis to no more than 2-3 in the entire newsletter, placed only where truly appropriate
        - Vary paragraph length for readability, balancing detail with scanning ease
        - Include 1,200-1,700 words to provide substantial value
        - Highlight the value proposition for deals through compelling description rather than marketing language
        - Create urgency through factual time constraints rather than pressure tactics
        - Focus on specific, actionable details that readers can immediately use
        - Include occasional expert insights that demonstrate travel knowledge

        The newsletter should be ready to send to subscribers with minimal editing, showcasing both expertise and a connection with the reader's travel aspirations.
        
        IMPORTANT: Structure the markdown with specific headings for each section so I can easily extract them later:
        # Introduction
        # Featured Deal
        # Destination Guides
        # Seasonal Inspiration
        # Travel Tips
        # Conclusion
        
        For each Destination Guide, use a ## heading with the destination name.
        
        Use standard markdown formatting for emphasis (**bold**, *italic*), lists, and [links](url).
        """
            
    def generate_newsletter(self, newsletter_content: Dict[str, Any], mode: str = "real") -> Dict[str, Any]:
        """Generate a newsletter based on the content provided and return it as a structured JSON object."""
        logger.info(f"Generating newsletter in {mode} mode")
        
        # Simply concatenate all content with clear section headers
        content = "# NEWSLETTER CONTENT\n\n"
        
        # Add metadata
        if 'metadata' in newsletter_content:
            metadata = newsletter_content['metadata']
            content += "## METADATA\n"
            content += f"Current Season: {metadata.get('season', 'Not specified')}\n"
            content += f"Upcoming Season: {metadata.get('upcoming_season', 'Not specified')}\n"
            content += f"Destination Focus: {metadata.get('destination_focus', 'Not specified')}\n\n"
            
            # Add edition info for SendGrid template
            edition_date = datetime.now().strftime("%B %d, %Y")
            edition_title = f"Travel Deals: {metadata.get('destination_focus', 'Global Destinations')}"
            edition_tagline = f"Discover amazing deals for {metadata.get('season', 'this season')}"
        else:
            edition_date = datetime.now().strftime("%B %d, %Y")
            edition_title = "Travel Deals Weekly"
            edition_tagline = "Explore the world for less"
        
        # Add featured deal (full content)
        if 'featured_deal' in newsletter_content:
            deal = newsletter_content['featured_deal']
            content += "## FEATURED DEAL\n"
            content += f"Title: {deal.get('title', 'No title')}\n"
            content += f"Deal Data: {deal.get('deal_data', '')}\n"
            content += f"Content: {deal.get('content', '')}\n\n"
        
        # Add featured destination guides (full content)
        if 'featured_destination_guides' in newsletter_content and newsletter_content['featured_destination_guides']:
            content += "## FEATURED DESTINATION GUIDES\n"
            for guide in newsletter_content['featured_destination_guides']:
                content += f"### Guide: {guide.get('title', 'No title')}\n"
                content += f"Content: {guide.get('content', '')}\n\n"
        
        # Add related deals (full content)
        if 'related_deals' in newsletter_content and newsletter_content['related_deals']:
            content += "## RELATED DEALS\n"
            for deal in newsletter_content['related_deals']:
                content += f"### Deal: {deal.get('title', 'No title')}\n"
                content += f"Deal Data: {deal.get('deal_data', '')}\n"
                content += f"Content: {deal.get('content', '')}\n\n"
        
        # Add practical tips (full content)
        if 'practical_tips' in newsletter_content and newsletter_content['practical_tips']:
            content += "## PRACTICAL TIPS\n"
            for tip in newsletter_content['practical_tips']:
                content += f"### Tip: {tip.get('title', 'No title')}\n"
                content += f"Content: {tip.get('content', '')}\n\n"
        
        # Add seasonal experience (full content)
        if 'seasonal_experience' in newsletter_content:
            experience = newsletter_content['seasonal_experience']
            content += "## SEASONAL EXPERIENCE\n"
            content += f"Title: {experience.get('title', 'No title')}\n"
            content += f"Content: {experience.get('content', '')}\n\n"
        
        # Add travel news (full content)
        if 'travel_news' in newsletter_content:
            news = newsletter_content['travel_news']
            content += "## TRAVEL NEWS\n"
            content += f"Title: {news.get('title', 'No title')}\n"
            content += f"Content: {news.get('content', '')}\n\n"
        
        # Generate newsletter with LLM
        try:
            markdown_newsletter = self.llm.analyze(self.system_prompt, content)
            
            # Parse the markdown into structured JSON for SendGrid
            sendgrid_data = self._markdown_to_sendgrid_json(
                markdown_newsletter, 
                edition_title.title(), 
                edition_tagline, 
                edition_date
            )
            
            # Update usage statistics if in real mode
            if mode.lower() == "real" and 'metadata' in newsletter_content and 'article_ids' in newsletter_content['metadata']:
                self.update_usage_statistics(newsletter_content['metadata']['article_ids'])
                logger.info("Updated usage statistics in real mode")
            elif mode.lower() == "test":
                logger.info("Test mode: usage statistics not updated")
            
            return sendgrid_data
            
        except Exception as e:
            logger.error(f"Error generating newsletter: {str(e)}")
            raise Exception(f"Failed to generate newsletter: {str(e)}")
    
    def _convert_markdown_to_html(self, markdown_text: str) -> str:
        """Convert markdown to HTML for email display."""
        # Use the markdown library to convert to HTML
        html = markdown.markdown(markdown_text, extensions=['extra'])
        
        # Add some basic inline styling for email compatibility
        html = html.replace('<h1>', '<h1 style="font-size: 28px; font-weight: bold; color: #2A2A2A; line-height: 34px; margin-top: 20px; margin-bottom: 10px;">')
        html = html.replace('<h2>', '<h2 style="font-size: 24px; font-weight: bold; color: #2A2A2A; line-height: 30px; margin-top: 18px; margin-bottom: 9px;">')
        html = html.replace('<h3>', '<h3 style="font-size: 20px; font-weight: bold; color: #2A2A2A; line-height: 26px; margin-top: 16px; margin-bottom: 8px;">')
        html = html.replace('<p>', '<p style="font-size: 16px; line-height: 24px; margin-top: 10px; margin-bottom: 10px; color: #2D2D2D;">')
        html = html.replace('<ul>', '<ul style="margin-left: 20px; padding-left: 0;">')
        html = html.replace('<ol>', '<ol style="margin-left: 20px; padding-left: 0;">')
        html = html.replace('<li>', '<li style="margin-bottom: 8px; line-height: 24px;">')
        html = html.replace('<a ', '<a style="color: #0c457d; font-weight: bold; text-decoration: underline;" ')
        html = html.replace('<strong>', '<strong style="font-weight: bold;">')
        html = html.replace('<em>', '<em style="font-style: italic;">')
        
        return html
    
    def _markdown_to_sendgrid_json(self, markdown_text: str, edition_title: str, edition_tagline: str, edition_date: str) -> Dict[str, Any]:
        """Convert markdown newsletter to SendGrid-compatible JSON structure."""
        # Default placeholder image URLs - using a consistent placeholder for now
        default_image_url = "https://placehold.co/600x400/faedca/0c457d?text=Travel"
        default_avatar_url = "https://placehold.co/80x80/faedca/0c457d?text=JO"
        
        # Initialize the JSON structure
        json_data = {
            "header": {
                "logo_url": os.getenv('BYTE_SIZE_LOGO'),
                "edition_title": edition_title,
                "edition_tagline": edition_tagline
            },
            "author": {
                "name": "Johnathan Oneal",
                "avatar_url": default_avatar_url,
                "date": edition_date
            },
            "introduction": {"content": ""},
            "featured_deal": {
                "title": "Special Travel Deal",
                "content": "",
                "button_text": "Book Now!",
                "button_url": "https://bytesizetravel.com/explore"
            },
            "destination_guides": [],
            "seasonal_inspiration": {
                "title": "Seasonal Travel Ideas",
                "content": ""
            },
            "travel_tips": {
                "title": "Smart Travel Tips",
                "content": ""
            },
            "conclusion": {
                "content": "",
                "button_text": "Explore More Deals",
                "button_url": "https://bytesizetravel.com/explore"
            },
            "footer": {
                "social_links": {
                    "facebook": "https://facebook.com/bytesizetravel",
                    "twitter": "https://twitter.com/bytesizetravel",
                    "instagram": "https://instagram.com/bytesizetravel",
                    "linkedin": "https://linkedin.com/company/bytesizetravel"
                },
                "unsubscribe_url": "{{unsubscribe_url}}"
            }
        }
        
        # Extract sections using regex
        sections = {
            "introduction": re.search(r'# Introduction\s+(.*?)(?=# Featured Deal|\Z)', markdown_text, re.DOTALL),
            "featured_deal": re.search(r'# Featured Deal\s+(.*?)(?=# Destination Guides|\Z)', markdown_text, re.DOTALL),
            "destination_guides": re.search(r'# Destination Guides\s+(.*?)(?=# Seasonal Inspiration|\Z)', markdown_text, re.DOTALL),
            "seasonal_inspiration": re.search(r'# Seasonal Inspiration\s+(.*?)(?=# Travel Tips|\Z)', markdown_text, re.DOTALL),
            "travel_tips": re.search(r'# Travel Tips\s+(.*?)(?=# Conclusion|\Z)', markdown_text, re.DOTALL),
            "conclusion": re.search(r'# Conclusion\s+(.*?)(?=\Z)', markdown_text, re.DOTALL)
        }
        
        # Fill in the sections from the markdown
        if sections["introduction"]:
            intro_content = sections["introduction"].group(1).strip()
            json_data["introduction"]["content"] = self._convert_markdown_to_html(intro_content)
        
        if sections["featured_deal"]:
            featured_deal_content = sections["featured_deal"].group(1).strip()
            # Extract title if it exists
            title_match = re.search(r'^## (.*?)$', featured_deal_content, re.MULTILINE)
            if title_match:
                json_data["featured_deal"]["title"] = title_match.group(1).strip()
                # Remove the title from the content
                featured_deal_content = re.sub(r'^## .*?$\n', '', featured_deal_content, 1, re.MULTILINE)
            json_data["featured_deal"]["content"] = self._convert_markdown_to_html(featured_deal_content)
        
        if sections["destination_guides"]:
            guides_content = sections["destination_guides"].group(1).strip()
            # Look for ## headings to separate individual guides
            guide_sections = re.findall(r'## (.*?)$(.*?)(?=## |\Z)', guides_content, re.DOTALL | re.MULTILINE)
            
            for title, content in guide_sections:
                json_data["destination_guides"].append({
                    "title": title.strip(),
                    "content": self._convert_markdown_to_html(content.strip()),
                    "image_url": default_image_url  # Using placeholder until image system is implemented
                })
            
            # If no guides were found with ## headings, use the whole section
            if not guide_sections:
                json_data["destination_guides"].append({
                    "title": "Destination Guide",
                    "content": self._convert_markdown_to_html(guides_content),
                    "image_url": default_image_url  # Using placeholder until image system is implemented
                })
        
        if sections["seasonal_inspiration"]:
            seasonal_content = sections["seasonal_inspiration"].group(1).strip()
            # Extract title if it exists
            title_match = re.search(r'^## (.*?)$', seasonal_content, re.MULTILINE)
            if title_match:
                json_data["seasonal_inspiration"]["title"] = title_match.group(1).strip()
                # Remove the title from the content
                seasonal_content = re.sub(r'^## .*?$\n', '', seasonal_content, 1, re.MULTILINE)
            json_data["seasonal_inspiration"]["content"] = self._convert_markdown_to_html(seasonal_content)
        
        if sections["travel_tips"]:
            tips_content = sections["travel_tips"].group(1).strip()
            # Extract title if it exists
            title_match = re.search(r'^## (.*?)$', tips_content, re.MULTILINE)
            if title_match:
                json_data["travel_tips"]["title"] = title_match.group(1).strip()
                # Remove the title from the content
                tips_content = re.sub(r'^## .*?$\n', '', tips_content, 1, re.MULTILINE)
            json_data["travel_tips"]["content"] = self._convert_markdown_to_html(tips_content)
        
        if sections["conclusion"]:
            conclusion_content = sections["conclusion"].group(1).strip()
            json_data["conclusion"]["content"] = self._convert_markdown_to_html(conclusion_content)
        
        return json_data
    
    def update_usage_statistics(self, article_ids: List[int]):
        """Update the usage statistics for the articles used in the newsletter"""
        if not article_ids:
            return
            
        placeholders = ','.join('?' * len(article_ids))
        self.processed_db.conn.execute(f"""
            UPDATE processed_articles
            SET used_count = COALESCE(used_count, 0) + 1,
                last_used = datetime('now')
            WHERE id IN ({placeholders})
        """, article_ids)
        self.processed_db.conn.commit()
        
        logger.info(f"Updated usage statistics for {len(article_ids)} articles")

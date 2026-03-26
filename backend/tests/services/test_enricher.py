import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bst.models.enrichment import ArticleEnrichment, DailyDropCategory
from bst.services.enricher import SYSTEM_PROMPT, enrich_article
from bst.services.openai_client import OpenAIClient

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def _load_fixtures(filename: str) -> list[dict]:
    return json.loads((FIXTURES_DIR / filename).read_text())


def _mock_enrichment(
    category: str = "credit_card_news",
) -> ArticleEnrichment:
    return ArticleEnrichment(
        daily_drop_category=DailyDropCategory(category),
        summary="Test summary for the article.",
        headline_angle="Test headline angle",
        urgency="timely",
        locations=["United States"],
        programs_mentioned=["Chase Ultimate Rewards"],
        cards_mentioned=["Chase Sapphire Preferred"],
        key_facts=["Fact one", "Fact two", "Fact three"],
        relevance_score=8,
        why_relevant="Relevant to Daily Drop readers.",
    )


class TestEnrichmentModel:
    def test_valid_enrichment(self) -> None:
        enrichment = _mock_enrichment()
        assert enrichment.daily_drop_category == DailyDropCategory.credit_card_news
        assert enrichment.relevance_score == 8

    def test_all_categories_valid(self) -> None:
        for cat in DailyDropCategory:
            enrichment = _mock_enrichment(cat.value)
            assert enrichment.daily_drop_category == cat

    def test_relevance_score_bounds(self) -> None:
        with pytest.raises(ValueError, match="greater than or equal to 1"):
            ArticleEnrichment(
                daily_drop_category=DailyDropCategory.credit_card_news,
                summary="Test",
                headline_angle="Test",
                urgency="timely",
                key_facts=["a", "b", "c"],
                relevance_score=0,
                why_relevant="Test",
            )

    def test_urgency_values(self) -> None:
        for urgency in ("breaking", "timely", "evergreen"):
            enrichment = _mock_enrichment().model_copy(update={"urgency": urgency})
            assert enrichment.urgency == urgency


class TestEnrichArticleMocked:
    def test_calls_openai_with_correct_params(self) -> None:
        mock_client = MagicMock(spec=OpenAIClient)
        mock_client.parse.return_value = _mock_enrichment()

        result = enrich_article(mock_client, "Test Title", "Test content")

        mock_client.parse.assert_called_once()
        call_kwargs = mock_client.parse.call_args
        assert call_kwargs.kwargs["response_model"] is ArticleEnrichment
        assert SYSTEM_PROMPT in call_kwargs.kwargs["system_prompt"]
        assert "Test Title" in call_kwargs.kwargs["content"]
        assert "Test content" in call_kwargs.kwargs["content"]
        assert result.daily_drop_category == DailyDropCategory.credit_card_news

    def test_returns_enrichment_result(self) -> None:
        mock_client = MagicMock(spec=OpenAIClient)
        expected = _mock_enrichment("deal_alert")
        mock_client.parse.return_value = expected

        result = enrich_article(mock_client, "Deal!", "Cheap flights")
        assert result is expected


class TestSystemPrompt:
    def test_prompt_mentions_all_categories(self) -> None:
        for cat in DailyDropCategory:
            assert cat.value in SYSTEM_PROMPT

    def test_prompt_mentions_daily_drop(self) -> None:
        assert "Daily Drop" in SYSTEM_PROMPT
        assert "dailydrop.com" in SYSTEM_PROMPT

    def test_prompt_describes_brand_voice(self) -> None:
        assert "conversational" in SYSTEM_PROMPT
        assert "action-oriented" in SYSTEM_PROMPT


@pytest.mark.ai
class TestEnrichmentWithRealAPI:
    """Tests that call the real OpenAI API.

    Run with: uv run pytest --ai
    """

    @pytest.fixture
    def client(self) -> OpenAIClient:
        return OpenAIClient()

    def test_daily_drop_article_categorization(self, client: OpenAIClient) -> None:
        articles = _load_fixtures("daily_drop_articles.json")

        for article in articles:
            result = enrich_article(client, article["title"], article["content"])

            assert isinstance(result, ArticleEnrichment)
            assert result.daily_drop_category.value == article["expected_category"], (
                f"Article '{article['title']}' expected "
                f"'{article['expected_category']}' but got "
                f"'{result.daily_drop_category.value}'"
            )
            assert len(result.summary) > 20
            assert len(result.key_facts) >= 3
            assert 1 <= result.relevance_score <= 10

    def test_external_article_categorization(self, client: OpenAIClient) -> None:
        articles = _load_fixtures("external_articles.json")

        for article in articles:
            result = enrich_article(client, article["title"], article["content"])

            assert isinstance(result, ArticleEnrichment)
            assert result.daily_drop_category.value == article["expected_category"], (
                f"Article '{article['title']}' expected "
                f"'{article['expected_category']}' but got "
                f"'{result.daily_drop_category.value}'"
            )
            assert len(result.summary) > 20
            assert result.relevance_score >= 1

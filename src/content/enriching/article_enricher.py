import json
from datetime import datetime
from typing import List, Dict
from pydantic import ValidationError
from database.processed_database import ProcessedDatabase
from services.openai.openai_client import OpenAIClient
from models.schemas import ProcessedArticle
from config.logging_config import fetch_logger as logger

class ArticleEnricher:
    def __init__(self, processed_db: ProcessedDatabase, openai_model: str = "gpt-4o-mini"):
        self.processed_db = processed_db
        self.llm = OpenAIClient(model=openai_model)
        logger.info(f"ArticleEnricher initialized with model: {openai_model}")

        # System prompt for article analysis
        self.system_prompt = """
        You are an expert travel content analyzer. Your task is to analyze travel content and extract specific metadata in a structured format. You must return ONLY a valid JSON object with these exact fields and possible values.

        IMPORTANT GUIDELINES FOR DATES AND VALUE SCORING:

        1. TRAVEL WINDOW DATES:
        - If exact dates are provided, use YYYY-MM-DD format
        - If only month ranges are provided (e.g., "mid August to early October"), use the 15th of the first month as start date and the 5th of the end month as end date
        - If multiple travel windows exist, choose the earliest upcoming window
        - If only a sample travel date is provided, use that range for the travel window
        - NEVER return null for travel_window dates - make your best estimate based on available information

        2. BOOKING DEADLINE:
        - If a specific booking deadline is mentioned, use that date in YYYY-MM-DD format
        - If only "X days before departure" is mentioned, calculate the deadline as (earliest travel window start date - X days)
        - If no deadline is mentioned, use the posting date of the article as the booking deadline
        - NEVER return null for booking_deadline - make your best estimate

        3. VALUE SCORE CALCULATION (1-10 scale):
        - For flights: Base value on cents-per-mile metric if provided
            * 3-5 cents/mile = score 7
            * 5-7 cents/mile = score 6
            * 7-9 cents/mile = score 5
            * 9-12 cents/mile = score 4
            * >12 cents/mile = score 3
        - If no CPM is provided, estimate based on destination and price:
            * Domestic flights under $200 = score 8
            * International flights under $600 = score 8
            * Use price tiers and comparative language ("good deal", "amazing price") to adjust score up or down
        - NEVER return null for value_score - provide a number between 1-10

        Required JSON format:
        {
            "content_type": ["deal", "guide", "news", "tip", "experience"],
            
            "deal_data": {
                "type": ["flight", "hotel", "package"],
                "price_tier": ["budget", "moderate", "luxury"],
                "value_score": 1-10,
                "booking_deadline": "YYYY-MM-DD",
                "travel_window": {
                    "start": "YYYY-MM-DD",
                    "end": "YYYY-MM-DD"
                },
                "origin": "string",
                "destination": "string"
            },
            
            "locations": {
                "primary": "string",
                "secondary": []
            },
            "audience": ["budget", "luxury", "family", "adventure", "general"],
            "key_themes": ["food", "culture", "outdoors", "shopping", "nightlife", "news", "guide"],
            "seasonality": ["any", "summer", "winter", "shoulder"]
        }

        For content that is not a time-based deal, "deal_data" can be empty. For primary location, return the country in a lowercase string with no spaces or "worldwide". Secondary locations can be cities or additional countries but should be a list with entries that are all lowercase with no spaces.

        Return ONLY the JSON object, no additional text.
        """
    
    def get_unprocessed_articles(self) -> List[Dict]:
        """Get articles that haven't been processed yet"""
        query = """
            SELECT f.* FROM articles f
            LEFT JOIN processed_articles p ON f.id = p.fetched_article_id
            WHERE p.id IS NULL AND f.is_full_content_fetched = 1
        """
        cursor = self.processed_db.conn.execute(query)
        articles = [dict(row) for row in cursor.fetchall()]
        logger.info(f"Found {len(articles)} unprocessed articles")
        return articles
        
    def enrich_article(self, article_id: int, content: str) -> ProcessedArticle:
        """Analyze article content and extract structured metadata"""
        logger.debug(f"Enriching article ID: {article_id}")
        try:
            response = self.llm.analyze(self.system_prompt, content)
            enriched_data = json.loads(response)
            
            # Log useful metadata for debugging
            content_type = enriched_data.get("content_type", ["unknown"])[0]
            locations = enriched_data.get("locations", {})
            primary_location = locations.get("primary", "unknown")
            
            logger.info(f"Article {article_id} enriched: type={content_type}, location={primary_location}")
            
            return ProcessedArticle(
                fetched_article_id=article_id,
                processed_date=datetime.now(),
                **enriched_data
            )
        except ValidationError as e:
            logger.error(f"Validation error on article {article_id}: {str(e)}")
            raise e
        except json.JSONDecodeError:
            logger.error(f"JSON decode error on article {article_id}")
            raise ValueError("Failed to parse LLM response as JSON")
        except Exception as e:
            logger.error(f"General error enriching article {article_id}: {str(e)}")
            raise Exception(f"Error enriching article: {str(e)}")

    def process_pending_articles(self):
        """Process all unprocessed articles"""
        logger.info("Starting to process pending articles")
        unprocessed = self.get_unprocessed_articles()
        processed_count = 0
        error_count = 0
        
        for article in unprocessed:
            try:
                processed = self.enrich_article(article['id'], article['content'])
                self.processed_db.save_article(processed)
                processed_count += 1
            except Exception as e:
                error_count += 1
                logger.error(f"Failed to process article {article['id']}: {str(e)}")
                print(f"Error processing article {article['id']}: {str(e)}")
                continue
        
        logger.info(f"Processing complete. Processed: {processed_count}, Errors: {error_count}")
        return processed_count

import json
from datetime import datetime
from typing import List, Dict
from database.processed_database import ProcessedDatabase
from services.openai_client import OpenAIClient
from models.schemas import ProcessedArticle

class ArticleEnricher:
    def __init__(self, processed_db: ProcessedDatabase, openai_model: str = "gpt-4o-mini"):
        self.processed_db = processed_db
        self.llm = OpenAIClient(model=openai_model)

        # System prompt for article analysis
        self.system_prompt = """
        You are an expert travel content analyzer. Your task is to analyze travel content 
        and extract specific metadata in a structured format. You must return ONLY a valid 
        JSON object with these exact fields and possible values, for content that is not
        a time based deal "deal_data" can be empty, For primary location return the country in
        a lower case string with no spaces or worldwide and secondary can either be cities or additonal
        countries but should be a list with entries that are all lowercase with no spaces:
        
        {
            "content_type": ["deal", "guide", "news", "tip", "experience"],
            
            "deal_data": {
                "type": ["flight", "hotel", "package"],
                "price_tier": ["budget", "moderate", "luxury"],
                "value_score": 0-10,
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
        return [dict(row) for row in cursor.fetchall()]
        
    def enrich_article(self, article_id: int, content: str) -> ProcessedArticle:
        """Analyze article content and extract structured metadata"""
        try:
            response = self.llm.analyze(self.system_prompt, content)
            enriched_data = json.loads(response)
            
            return ProcessedArticle(
                fetched_article_id=article_id,
                processed_date=datetime.now(),
                **enriched_data
            )
        except json.JSONDecodeError:
            raise ValueError("Failed to parse LLM response as JSON")
        except Exception as e:
            raise Exception(f"Error enriching article: {str(e)}")

    def process_pending_articles(self):
        """Process all unprocessed articles"""
        unprocessed = self.get_unprocessed_articles()
        processed_count = 0
        
        for article in unprocessed:
            try:
                processed = self.enrich_article(article['id'], article['content'])
                self.processed_db.save_article(processed)
                processed_count += 1
            except Exception as e:
                print(f"Error processing article {article['id']}: {str(e)}")
                continue
        
        return processed_count

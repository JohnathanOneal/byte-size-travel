import json
from datetime import datetime
from typing import Dict, Any, List
from database.processed_database import ProcessedDatabase
from services.openai_client import OpenAIClient
from config.logging_config import fetch_logger as logger

class NewsletterWriter:
    def __init__(self, processed_db: ProcessedDatabase, openai_model: str = "gpt-4o-mini"):
        self.processed_db = processed_db
        self.llm = OpenAIClient(model=openai_model)
        logger.info(f"NewsletterWriter initialized with model: {openai_model}")
        
        # System prompt for newsletter generation
        self.system_prompt = """
        You are an expert travel newsletter writer for "Byte-Size Travel", creating engaging weekly newsletters that highlight 
        the best travel deals, destination guides, and practical travel tips.
        
        Write a compelling newsletter based on the travel content provided. Follow these guidelines:
        
        1. Start with a warm, personalized greeting
        2. Include a brief introduction that ties together the featured content
        3. Structure the newsletter in clear sections with proper headings:
           - FEATURED DEAL (highlight the value proposition and booking deadline)
           - DESTINATION GUIDES (relevant to the deals)
           - TRAVEL TIPS (practical advice for budget travelers)
           - SEASONAL INSPIRATION (timely travel ideas)
        
        4. For each deal, highlight:
           - The price point and value
           - Booking deadline (create urgency)
           - Key destinations covered
           - Any special terms or benefits
        
        5. For guides and tips, extract the most actionable and interesting points
        
        6. Include a brief conclusion with a call to action
        
        7. Use a friendly, enthusiastic tone with occasional light humor
        
        8. Keep content concise and scannable with short paragraphs, bullets where appropriate
        
        Format the newsletter in proper Markdown for easy reading, with clear headings, subheadings, 
        and section breaks. Include emojis where appropriate to add visual interest.
        
        The content should be ready to send directly to subscribers with minimal editing needed.
        """
    
    def _prepare_content_for_llm(self, newsletter_content: Dict[str, Any]) -> str:
        """Convert the newsletter content dictionary to a structured format for the LLM"""
        formatted_content = "# NEWSLETTER CONTENT FOR GENERATION\n\n"
        
        # Add featured deal
        if 'featured_deal' in newsletter_content:
            deal = newsletter_content['featured_deal']
            formatted_content += "## FEATURED DEAL\n"
            formatted_content += f"Title: {deal.get('title', 'No title')}\n"
            formatted_content += f"Price: {self._extract_price(deal)}\n"
            
            # Extract deal data
            deal_data = json.loads(deal.get('deal_data', '{}')) if isinstance(deal.get('deal_data'), str) else deal.get('deal_data', {})
            formatted_content += f"Booking Deadline: {deal_data.get('booking_deadline', 'Not specified')}\n"
            
            travel_window = deal_data.get('travel_window', {})
            if travel_window:
                formatted_content += f"Travel Period: {travel_window.get('start', '')} to {travel_window.get('end', '')}\n"
            
            formatted_content += f"Origin: {deal_data.get('origin', 'Not specified')}\n"
            formatted_content += f"Destination: {deal_data.get('destination', 'Not specified')}\n"
            formatted_content += f"Value Score: {deal_data.get('value_score', 'Not rated')}/10\n\n"
            
            # Add snippet of content
            content = deal.get('content', '')
            formatted_content += f"Content Summary: {content[:300]}...\n\n"
        
        # Add featured destination guides
        if 'featured_destination_guides' in newsletter_content and newsletter_content['featured_destination_guides']:
            formatted_content += "## FEATURED DESTINATION GUIDES\n"
            for guide in newsletter_content['featured_destination_guides']:
                formatted_content += f"- {guide.get('title', 'No title')}\n"
                # Add brief content snippet
                content = guide.get('content', '')
                formatted_content += f"  Summary: {content[:200]}...\n\n"
        
        # Add related deals
        if 'related_deals' in newsletter_content and newsletter_content['related_deals']:
            formatted_content += "## RELATED DEALS\n"
            for deal in newsletter_content['related_deals']:
                formatted_content += f"- {deal.get('title', 'No title')}\n"
                
                # Extract deal data
                deal_data = json.loads(deal.get('deal_data', '{}')) if isinstance(deal.get('deal_data'), str) else deal.get('deal_data', {})
                formatted_content += f"  Booking Deadline: {deal_data.get('booking_deadline', 'Not specified')}\n"
                formatted_content += f"  Value Score: {deal_data.get('value_score', 'Not rated')}/10\n\n"
        
        # Add secondary destination guides
        if 'secondary_destination_guides' in newsletter_content and newsletter_content['secondary_destination_guides']:
            formatted_content += "## SECONDARY DESTINATION GUIDES\n"
            for guide in newsletter_content['secondary_destination_guides']:
                formatted_content += f"- {guide.get('title', 'No title')}\n"
                # Add brief content snippet
                content = guide.get('content', '')
                formatted_content += f"  Summary: {content[:200]}...\n\n"
        
        # Add practical tips
        if 'practical_tips' in newsletter_content and newsletter_content['practical_tips']:
            formatted_content += "## PRACTICAL TIPS\n"
            for tip in newsletter_content['practical_tips']:
                formatted_content += f"- {tip.get('title', 'No title')}\n"
                # Add brief content snippet
                content = tip.get('content', '')
                formatted_content += f"  Summary: {content[:200]}...\n\n"
        
        # Add seasonal experience
        if 'seasonal_experience' in newsletter_content:
            experience = newsletter_content['seasonal_experience']
            formatted_content += "## SEASONAL EXPERIENCE\n"
            formatted_content += f"Title: {experience.get('title', 'No title')}\n"
            # Add brief content snippet
            content = experience.get('content', '')
            formatted_content += f"Summary: {content[:300]}...\n\n"
        
        # Add travel news
        if 'travel_news' in newsletter_content:
            news = newsletter_content['travel_news']
            formatted_content += "## TRAVEL NEWS\n"
            formatted_content += f"Title: {news.get('title', 'No title')}\n"
            # Add brief content snippet
            content = news.get('content', '')
            formatted_content += f"Summary: {content[:300]}...\n\n"
        
        # Add metadata context
        if 'metadata' in newsletter_content:
            metadata = newsletter_content['metadata']
            formatted_content += "## METADATA\n"
            formatted_content += f"Current Season: {metadata.get('season', 'Not specified')}\n"
            formatted_content += f"Upcoming Season: {metadata.get('upcoming_season', 'Not specified')}\n"
            formatted_content += f"Destination Focus: {metadata.get('destination_focus', 'Not specified')}\n"
        
        return formatted_content
    
    def _extract_price(self, deal: Dict[str, Any]) -> str:
        """Extract price from deal title or content"""
        title = deal.get('title', '')
        price_indicators = ['$', '€', '£', 'USD', 'EUR', 'GBP']
        
        for indicator in price_indicators:
            if indicator in title:
                # Extract price from title
                start = title.find(indicator)
                price_part = title[start:start+10]  # Grab a chunk
                # Clean up the price part
                import re
                price = re.search(r'[€$£]\d+(?:\.\d+)?', price_part)
                if price:
                    return price.group(0)
        
        return "Price not specified"
    
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
    
    def generate_newsletter(self, newsletter_content: Dict[str, Any], mode: str = "real") -> str:
        """
        Generate a newsletter based on the content provided.
        
        Args:
            newsletter_content: The content selected by the ArticleSelector
            mode: 'test' for testing without updating stats, 'real' for production use
            
        Returns:
            The generated newsletter content
        """
        logger.info(f"Generating newsletter in {mode} mode")
        
        # Prepare content for LLM
        formatted_content = self._prepare_content_for_llm(newsletter_content)
        
        # Generate newsletter with LLM
        try:
            newsletter = self.llm.analyze(self.system_prompt, formatted_content)
            
            # Update usage statistics if in real mode
            if mode.lower() == "real" and 'metadata' in newsletter_content and 'article_ids' in newsletter_content['metadata']:
                self.update_usage_statistics(newsletter_content['metadata']['article_ids'])
                logger.info("Updated usage statistics in real mode")
            elif mode.lower() == "test":
                logger.info("Test mode: usage statistics not updated")
            
            return newsletter
            
        except Exception as e:
            logger.error(f"Error generating newsletter: {str(e)}")
            raise Exception(f"Failed to generate newsletter: {str(e)}")

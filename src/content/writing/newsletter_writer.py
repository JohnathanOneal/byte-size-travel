import json
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
        You are an expert travel newsletter writer for "Byte-Size Travel." Your task is to create an engaging weekly newsletter highlighting the best travel deals, destination guides, and practical travel tips. I'll provide you with selected travel content including deals, guides, tips, and seasonal experiences.

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

        The newsletter should be ready to send to subscribers with minimal editing, showcasing both expertise and a connection with the reader's travel aspirations."""
            
    def generate_newsletter(self, newsletter_content: Dict[str, Any], mode: str = "real") -> str:
        """Generate a newsletter based on the content provided."""
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
            newsletter = self.llm.analyze(self.system_prompt, content)
            
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

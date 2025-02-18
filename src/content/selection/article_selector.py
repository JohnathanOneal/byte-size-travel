import json
from typing import List, Dict, Any
from database.processed_database import ProcessedDatabase


class ArticleSelector:
    def __init__(self, processed_db: ProcessedDatabase):
        self.processed_db = processed_db
    
    def get_article_details(self, processed_article_ids: List[int]) -> List[Dict]:
        """Get original article details for processed articles"""
        placeholders = ','.join('?' * len(processed_article_ids))
        query = f"""
            SELECT a.*, p.* 
            FROM articles a
            JOIN processed_articles p ON a.id = p.fetched_article_id
            WHERE p.id IN ({placeholders})
        """
        cursor = self.fetch_db.execute(query, processed_article_ids)
        return [dict(row) for row in cursor.fetchall()]
    
    def select_newsletter_content(self) -> Dict[str, Any]:
        """Select articles for the newsletter based on current criteria"""
        # Get featured deal
        cursor = self.processed_db.conn.execute("""
            SELECT * FROM processed_articles 
            WHERE content_type = 'deal'
            AND json_extract(deal_data, '$.value_score') >= 8
            AND date(json_extract(deal_data, '$.booking_deadline')) > date('now')
            ORDER BY json_extract(deal_data, '$.value_score') DESC
            LIMIT 1
        """)
        featured_deal = cursor.fetchone()
        if not featured_deal:
            raise ValueError("No high-value deals found")
        
        # Get original article details
        featured_details = self.get_article_details([featured_deal['id']])[0]
        
        # Get matching guides
        cursor = self.processed_db.conn.execute("""
            SELECT * FROM processed_articles
            WHERE content_type IN ('guide', 'experience')
            AND json_extract(locations, '$.primary') = ?
            LIMIT 2
        """, [json.loads(featured_deal['locations'])['primary']])
        matching_guides = cursor.fetchall()
        guide_details = self.get_article_details([g['id'] for g in matching_guides])
        
        return {
            'featured_deal': {**featured_details, **dict(featured_deal)},
            'matching_guides': [
                {**guide, **next(d for d in guide_details if d['id'] == guide['fetched_article_id'])}
                for guide in matching_guides
            ]
        }

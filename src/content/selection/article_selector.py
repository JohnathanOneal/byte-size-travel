import json
from typing import List, Dict, Any, Optional, Tuple
from database.processed_database import ProcessedDatabase
from datetime import datetime


class ArticleSelector:
    def __init__(self, processed_db: ProcessedDatabase):
        self.processed_db = processed_db
        # Content type reuse policies
        self.content_policies = {
            'deal': {
                'can_reuse': False,  # Deals should never be reused
                'cooldown_days': 0,  # N/A for deals
                'max_used_count': 0  # N/A for deals
            },
            'guide': {
                'can_reuse': True,   # Guides can be reused
                'cooldown_days': 90, # After 90 days
                'max_used_count': 3  # Maximum 3 uses
            },
            'experience': {
                'can_reuse': True,   # Experiences can be reused
                'cooldown_days': 120, # After 120 days
                'max_used_count': 2   # Maximum 2 uses
            },
            'tip': {
                'can_reuse': True,   # Tips can be reused
                'cooldown_days': 60,  # After 60 days
                'max_used_count': 3   # Maximum 3 uses
            },
            'news': {
                'can_reuse': True,   # News can be reused
                'cooldown_days': 180, # After 180 days (effectively fresh only)
                'max_used_count': 1   # Maximum 1 use (prefer fresh news)
            }
        }
    
    def get_article_details(self, processed_article_ids: List[int]) -> List[Dict]:
        """Get original article details for processed articles"""
        if not processed_article_ids:
            return []
            
        placeholders = ','.join('?' * len(processed_article_ids))
        query = f"""
            SELECT a.*, p.* 
            FROM articles a
            JOIN processed_articles p ON a.id = p.fetched_article_id
            WHERE p.id IN ({placeholders})
        """
        cursor = self.processed_db.conn.execute(query, processed_article_ids)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_freshness_clause(self, content_type: str) -> str:
        """Build SQL clause for content freshness based on type policies"""
        policy = self.content_policies.get(content_type, {
            'can_reuse': True, 
            'cooldown_days': 30,
            'max_used_count': 3
        })
        
        # If content can't be reused, only select unused items
        if not policy['can_reuse']:
            return "AND (last_used IS NULL)"
        
        # For reusable content, respect cooldown and max usage
        cooldown = policy['cooldown_days']
        max_count = policy['max_used_count']
        
        # Include both unused and items past cooldown with under max usage
        filter_clause = f"""
            AND (
                last_used IS NULL
                OR (
                    datetime(last_used, '+{cooldown} days') < datetime('now')
                    AND COALESCE(used_count, 0) < {max_count}
                )
            )
        """
        
        return filter_clause
    
    def get_seasonal_boost(self) -> Tuple[str, Dict[str, Any]]:
        """
        Generate seasonal relevance boost for content selection.
        Returns SQL clause and params for boosting seasonal content.
        """
        now = datetime.now()
        current_month = now.month
        
        # Map current month to seasons (Northern Hemisphere)
        seasons = {
            'winter': [12, 1, 2],
            'spring': [3, 4, 5],
            'summer': [6, 7, 8],
            'fall': [9, 10, 11]
        }
        
        current_season = next((season for season, months in seasons.items() 
                              if current_month in months), 'any')
        
        upcoming_season_idx = (seasons[current_season].index(current_month) + 1) % len(seasons[current_season])
        if upcoming_season_idx < len(seasons[current_season]):
            upcoming_month = seasons[current_season][upcoming_season_idx]
        else:
            next_season = list(seasons.keys())[(list(seasons.keys()).index(current_season) + 1) % 4]
            upcoming_month = seasons[next_season][0]
        
        next_season = list(seasons.keys())[(list(seasons.keys()).index(current_season) + 1) % 4]
        
        # Build seasonal boost clause
        seasonal_clause = """
            CASE 
                WHEN json_extract(seasonality, '$."current_season"') > 0 THEN 3
                WHEN json_extract(seasonality, '$."upcoming_season"') > 0 THEN 2
                WHEN json_extract(seasonality, '$."any_season"') > 0 THEN 1
                ELSE 0
            END DESC,
        """
        
        return seasonal_clause, {
            'current_season': current_season, 
            'upcoming_season': upcoming_month,
            'next_season': next_season
        }
    
    def extract_location(self, locations_json: str) -> str:
        """Extract primary location from locations JSON"""
        try:
            locations = json.loads(locations_json) if isinstance(locations_json, str) else locations_json
            primary_location = locations.get('primary', '').lower() if locations else ''
            return primary_location
        except:
            return ''
    
    def find_location_matching_guides(self, location: str, used_ids: List[int] = None) -> List[Dict]:
        """Find guides that match the given location"""
        if not location or location.lower() == 'worldwide':
            return []
            
        guide_freshness = self.get_freshness_clause('guide')
        ids_clause = ""
        if used_ids:
            placeholders = ','.join('?' * len(used_ids))
            ids_clause = f"AND id NOT IN ({placeholders})"
            used_ids_params = used_ids
        else:
            used_ids_params = []
        
        seasonal_boost, season_params = self.get_seasonal_boost()
        
        query = f"""
            SELECT * FROM processed_articles
            WHERE json_array_length(content_type) > 0
            AND (
                json_extract(content_type, '$[0]') = 'guide' 
                OR json_extract(content_type, '$[0]') = 'experience'
            )
            {guide_freshness}
            {ids_clause}
            AND (
                json_extract(locations, '$.primary') = ?
                OR (
                    json_extract(locations, '$.secondary') LIKE ?
                    OR json_extract(locations, '$.secondary') LIKE ?
                    OR json_extract(locations, '$.secondary') LIKE ?
                )
            )
            ORDER BY
                {seasonal_boost}
                json_extract(content_type, '$[0]') = 'guide' DESC,
                last_used IS NULL DESC,
                COALESCE(used_count, 0) ASC,
                processed_date DESC
            LIMIT 2
        """
        
        location_param = location.lower()
        cursor = self.processed_db.conn.execute(
            query, 
            used_ids_params + [
                location_param, 
                f'%"{location_param}"%',
                f'%{location_param}%',
                f'%{location_param.replace(" ", "")}%'
            ]
        )
        
        return [dict(row) for row in cursor.fetchall()]
    
    def select_newsletter_content(self) -> Dict[str, Any]:
        """
        Select cohesive content for a travel newsletter.
        
        Groups content by theme and ensures guides are relevant to featured deals.
        Tips and news are consolidated and more focused.
        
        Returns a structured content object for the LLM to use.
        """
        newsletter_content = {}
        selected_article_ids = []
        seasonal_boost, season_params = self.get_seasonal_boost()
        current_season = season_params['current_season']
        next_season = season_params['next_season']
        
        # 1. Featured deal - high value, future deadline, never used
        deal_freshness = self.get_freshness_clause('deal')
        cursor = self.processed_db.conn.execute(f"""
            SELECT * FROM processed_articles 
            WHERE json_array_length(content_type) > 0
            AND json_extract(content_type, '$[0]') = 'deal'
            AND json_extract(deal_data, '$.value_score') IS NOT NULL
            AND json_extract(deal_data, '$.booking_deadline') IS NOT NULL
            AND date(json_extract(deal_data, '$.booking_deadline')) > date('now')
            {deal_freshness}
            ORDER BY 
                CASE 
                    WHEN json_extract(seasonality, '$.{current_season}') > 0 THEN 3
                    WHEN json_extract(seasonality, '$.{next_season}') > 0 THEN 2
                    ELSE 1
                END DESC,
                CAST(json_extract(deal_data, '$.value_score') AS REAL) DESC,
                CASE
                    WHEN date(json_extract(deal_data, '$.booking_deadline')) < date('now', '+14 days') THEN 2
                    WHEN date(json_extract(deal_data, '$.booking_deadline')) < date('now', '+30 days') THEN 1
                    ELSE 0
                END DESC
            LIMIT 1
        """)
        featured_deal = cursor.fetchone()
        
        if not featured_deal:
            # Fallback to any future deal
            cursor = self.processed_db.conn.execute("""
                SELECT * FROM processed_articles 
                WHERE json_array_length(content_type) > 0
                AND json_extract(content_type, '$[0]') = 'deal'
                AND json_extract(deal_data, '$.booking_deadline') IS NOT NULL
                AND date(json_extract(deal_data, '$.booking_deadline')) > date('now')
                ORDER BY date(json_extract(deal_data, '$.booking_deadline')) ASC
                LIMIT 1
            """)
            featured_deal = cursor.fetchone()
        
        if not featured_deal:
            raise ValueError("No future deals found for newsletter")
        
        featured_details = self.get_article_details([featured_deal['id']])[0]
        newsletter_content['featured_deal'] = {**dict(featured_details), **dict(featured_deal)}
        selected_article_ids.append(featured_deal['id'])
        
        # Extract featured deal location for related content
        featured_location = self.extract_location(featured_deal['locations'])
        deal_destination = ''
        
        try:
            deal_data = json.loads(featured_deal['deal_data']) if isinstance(featured_deal['deal_data'], str) else featured_deal['deal_data']
            if deal_data and 'destination' in deal_data:
                deal_destination = deal_data['destination'].lower()
        except:
            pass
        
        # 2. Find guides relevant to the featured deal location
        location_guides = []
        
        # Try to find guides for the deal destination first
        if deal_destination and deal_destination != 'worldwide':
            location_guides = self.find_location_matching_guides(deal_destination, selected_article_ids)
        
        # If no guides found for destination, try primary location
        if not location_guides and featured_location and featured_location != 'worldwide':
            location_guides = self.find_location_matching_guides(featured_location, selected_article_ids)
        
        if location_guides:
            guide_details = self.get_article_details([guide['id'] for guide in location_guides])
            newsletter_content['featured_destination_guides'] = [
                {**dict(guide), **next((d for d in guide_details if d['id'] == guide['fetched_article_id']), {})}
                for guide in location_guides
            ]
            selected_article_ids.extend([guide['id'] for guide in location_guides])
            
            # Set destination focus based on the guides
            guide_location = self.extract_location(location_guides[0]['locations'])
            if guide_location and guide_location != 'worldwide':
                newsletter_content['destination_focus'] = guide_location
        
        # 3. Related deals - different locations
        deal_freshness = self.get_freshness_clause('deal')
        placeholders = ','.join('?' * len(selected_article_ids)) if selected_article_ids else "0"
        
        cursor = self.processed_db.conn.execute(f"""
            SELECT * FROM processed_articles 
            WHERE json_array_length(content_type) > 0
            AND json_extract(content_type, '$[0]') = 'deal'
            AND json_extract(deal_data, '$.booking_deadline') IS NOT NULL
            AND date(json_extract(deal_data, '$.booking_deadline')) > date('now')
            AND id NOT IN ({placeholders})
            {deal_freshness}
            AND (
                json_extract(locations, '$.primary') != ? 
                OR json_extract(locations, '$.primary') IS NULL
            )
            ORDER BY 
                CASE 
                    WHEN json_extract(seasonality, '$.{current_season}') > 0 THEN 3
                    WHEN json_extract(seasonality, '$.{next_season}') > 0 THEN 2
                    ELSE 1
                END DESC,
                CAST(json_extract(deal_data, '$.value_score') AS REAL) DESC
            LIMIT 2
        """, selected_article_ids + [featured_location])
        related_deals = cursor.fetchall()
        
        secondary_locations = []
        if related_deals:
            related_details = self.get_article_details([deal['id'] for deal in related_deals])
            newsletter_content['related_deals'] = [
                {**dict(deal), **next((d for d in related_details if d['id'] == deal['fetched_article_id']), {})}
                for deal in related_deals
            ]
            selected_article_ids.extend([deal['id'] for deal in related_deals])
            
            # Extract secondary locations for finding more guides
            for deal in related_deals:
                loc = self.extract_location(deal['locations'])
                if loc and loc != 'worldwide' and loc != featured_location:
                    secondary_locations.append(loc)
        else:
            newsletter_content['related_deals'] = []
        
        # 4. Find guides for secondary locations
        secondary_guides = []
        for location in secondary_locations:
            guides = self.find_location_matching_guides(location, selected_article_ids)
            if guides:
                secondary_guides.extend(guides)
                selected_article_ids.extend([g['id'] for g in guides])
                if len(secondary_guides) >= 2:
                    break
        
        if secondary_guides:
            guide_details = self.get_article_details([guide['id'] for guide in secondary_guides])
            newsletter_content['secondary_destination_guides'] = [
                {**dict(guide), **next((d for d in guide_details if d['id'] == guide['fetched_article_id']), {})}
                for guide in secondary_guides
            ]
        
        # 5. Practical travel tips (1-2 universal ones)
        tip_freshness = self.get_freshness_clause('tip')
        placeholders = ','.join('?' * len(selected_article_ids)) if selected_article_ids else "0"
        
        cursor = self.processed_db.conn.execute(f"""
            SELECT * FROM processed_articles
            WHERE json_array_length(content_type) > 0
            AND json_extract(content_type, '$[0]') = 'tip'
            AND id NOT IN ({placeholders})
            {tip_freshness}
            AND json_extract(locations, '$.primary') = 'worldwide'
            ORDER BY 
                CASE 
                    WHEN json_extract(seasonality, '$.{current_season}') > 0 THEN 3
                    WHEN json_extract(seasonality, '$.{next_season}') > 0 THEN 2
                    WHEN json_extract(seasonality, '$.any') > 0 THEN 1
                    ELSE 0
                END DESC,
                last_used IS NULL DESC,
                COALESCE(used_count, 0) ASC
            LIMIT 2
        """, selected_article_ids)
        universal_tips = cursor.fetchall()
        
        if universal_tips:
            tip_details = self.get_article_details([tip['id'] for tip in universal_tips])
            newsletter_content['practical_tips'] = [
                {**dict(tip), **next((d for d in tip_details if d['id'] == tip['fetched_article_id']), {})}
                for tip in universal_tips
            ]
            selected_article_ids.extend([tip['id'] for tip in universal_tips])
        else:
            newsletter_content['practical_tips'] = []
        
        # 6. Seasonal experience
        experience_freshness = self.get_freshness_clause('experience')
        placeholders = ','.join('?' * len(selected_article_ids)) if selected_article_ids else "0"
        
        cursor = self.processed_db.conn.execute(f"""
            SELECT * FROM processed_articles
            WHERE json_array_length(content_type) > 0
            AND json_extract(content_type, '$[0]') = 'experience'
            AND id NOT IN ({placeholders})
            {experience_freshness}
            ORDER BY 
                CASE 
                    WHEN json_extract(seasonality, '$.{current_season}') > 0 THEN 3
                    WHEN json_extract(seasonality, '$.{next_season}') > 0 THEN 2
                    ELSE 1
                END DESC,
                last_used IS NULL DESC,
                COALESCE(used_count, 0) ASC,
                processed_date DESC
            LIMIT 1
        """, selected_article_ids)
        seasonal_experience = cursor.fetchone()
        
        if seasonal_experience:
            exp_details = self.get_article_details([seasonal_experience['id']])[0]
            newsletter_content['seasonal_experience'] = {**dict(seasonal_experience), **dict(exp_details)}
            selected_article_ids.append(seasonal_experience['id'])
        
        # 7. Travel news - relevant to either featured location or upcoming season
        news_freshness = self.get_freshness_clause('news')
        placeholders = ','.join('?' * len(selected_article_ids)) if selected_article_ids else "0"
        
        cursor = self.processed_db.conn.execute(f"""
            SELECT * FROM processed_articles
            WHERE json_array_length(content_type) > 0
            AND json_extract(content_type, '$[0]') = 'news'
            AND id NOT IN ({placeholders})
            {news_freshness}
            ORDER BY 
                CASE
                    WHEN json_extract(locations, '$.primary') = ? THEN 3
                    WHEN json_extract(seasonality, '$.{current_season}') > 0 THEN 2
                    WHEN json_extract(seasonality, '$.{next_season}') > 0 THEN 1
                    ELSE 0
                END DESC,
                processed_date DESC,
                last_used IS NULL DESC
            LIMIT 1
        """, selected_article_ids + [featured_location])
        relevant_news = cursor.fetchone()
        
        if relevant_news:
            news_details = self.get_article_details([relevant_news['id']])[0]
            newsletter_content['travel_news'] = {**dict(relevant_news), **dict(news_details)}
            selected_article_ids.append(relevant_news['id'])
        
        # 8. Add metadata to help with newsletter generation
        newsletter_content['metadata'] = {
            'generation_date': datetime.now().isoformat(),
            'season': season_params['current_season'],
            'upcoming_season': season_params['next_season'],
            'destination_focus': featured_location if featured_location and featured_location.lower() != 'worldwide' else None,
            'article_ids': selected_article_ids  # For tracking/updating later
        }
        
        return newsletter_content
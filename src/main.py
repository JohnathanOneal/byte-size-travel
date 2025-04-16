import os
import json
from database.populate_db import PopulateDB
from database.fetch_database import FetchDatabase
from database.processed_database import ProcessedDatabase
from content.fetching.rss_full_fetch import RssFullFetch
from pathlib import Path
from dotenv import load_dotenv

from content.enriching.article_enricher import ArticleEnricher
from content.selection.article_selector import ArticleSelector
from content.writing.newsletter_writer import NewsletterWriter

from config.logging_config import app_logger as logger

from services.sendgrid_client import SendGridEmailClient

def load_environment():
    """Load environment variables from .env file, checking for required feilds"""
    env_path = Path('.env')
    if env_path.exists():
        load_dotenv(env_path)
    
    required_vars = ['DATABASE_PATH', 'OPENAI_API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing_vars)}\n"
            "Please create a .env file with these variables or set them in your environment."
        )


def main():
    # Load environment variables
    load_environment()

    # # populate db with content from our sources
    # fetch_db = FetchDatabase("main")
    # populator = PopulateDB(fetch_db)
    # populator.populate_all_sources()

    # # fetch full rss content
    # fetcher = RssFullFetch(fetch_db)
    # fetcher.fetch_pending_content()
    # fetch_db.conn.close()
    
    # # process data adding enriched metadata
    # processed_db = ProcessedDatabase("main")
    # enricher = ArticleEnricher(
    #     processed_db=processed_db,
    #     openai_model=os.getenv('OPENAI_MODEL')
    # )
    # processed_count = enricher.process_pending_articles()
    # logger.info(f"Processed {processed_count} new articles")
    
    # Select newsletter content using enriched metadata
    # processed_db = ProcessedDatabase("main")
    # selector = ArticleSelector(processed_db)
    # try:
    #     newsletter_content = selector.select_newsletter_content()
    #     print("Newsletter content selected successfully")
    # except ValueError as e:
    #     print(f"Error selecting newsletter content: {str(e)}")

    # # Generate the newsletter
    # newsletter_writer = NewsletterWriter(processed_db)
    # sendgrid_json = newsletter_writer.generate_newsletter(newsletter_content, mode="test")
    # print(json.dumps(sendgrid_json, indent=2))

    # # Clean up
    # processed_db.conn.close()

    sg_client = SendGridEmailClient(list_name="byte-size-travel-deals")

    template_data = {
                "header": {
                    "logo_url": "http://cdn.mcauto-images-production.sendgrid.net/7e69f08ffdf13ddf/1e75a737-1dea-469a-b3ce-b51d640c093e/500x500.jpg",
                    "edition_title": "Travel Deals: United States",
                    "edition_tagline": "Discover amazing deals for spring"
                },
                "author": {
                    "name": "Johnathan Oneal",
                    "avatar_url": "https://placehold.co/80x80/faedca/0c457d?text=JO",
                    "date": "April 14, 2025"
                },
                "introduction": {
                    "content": "<p style=\"font-size: 16px; line-height: 24px; margin-top: 10px; margin-bottom: 10px; color: #2D2D2D;\">Hello, fellow travel enthusiasts! \ud83c\udf0d As spring unfolds, it's time to uncover the best travel deals and destinations that beckon us to explore. Whether you're dreamily planning summer getaways or craving spontaneous weekend escapes, this newsletter is packed with exclusive deals that will make your travel desires a reality. From stunning beaches in Hawaii to luxury resorts in the Caribbean, we have handpicked offers that promise unforgettable adventures. Let's dive in!</p>\n<h1 style=\"font-size: 28px; font-weight: bold; color: #2A2A2A; line-height: 34px; margin-top: 20px; margin-bottom: 10px;\"></h1>"
                },
                "featured_deals": [
                    {
                    "title": "Deal 1: $49 Sale Fares to Kick Off Your Summer",
                    "content": "<p style=\"font-size: 16px; line-height: 24px; margin-top: 10px; margin-bottom: 10px; color: #2D2D2D;\">Dreaming of sun-soaked beaches? Southwest Airlines is offering unbelievable one-way fares starting at just <strong style=\"font-weight: bold;\">$49</strong> to Hawaii! This deal is perfect for those looking to rejuvenate among tropical landscapes.</p>\n<ul style=\"margin-left: 20px; padding-left: 0;\">\n<li style=\"margin-bottom: 8px; line-height: 24px;\"><strong style=\"font-weight: bold;\">Destination:</strong> Hawaii</li>\n<li style=\"margin-bottom: 8px; line-height: 24px;\">Hawaii invites you with its rich culture and breathtaking natural beauty. Experience the luau, surf the iconic waves, and explore volcanic parks.</li>\n<li style=\"margin-bottom: 8px; line-height: 24px;\"><strong style=\"font-weight: bold;\">Pricing:</strong> </li>\n<li style=\"margin-bottom: 8px; line-height: 24px;\"><em style=\"font-style: italic;\">One-way tickets from the continental U.S. at only $49</em>.</li>\n<li style=\"margin-bottom: 8px; line-height: 24px;\"><strong style=\"font-weight: bold;\">Booking Deadline:</strong> </li>\n<li style=\"margin-bottom: 8px; line-height: 24px;\">Purchase by <strong style=\"font-weight: bold;\">April 17, 2025</strong> (11:59 p.m. Pacific Time).</li>\n<li style=\"margin-bottom: 8px; line-height: 24px;\"><strong style=\"font-weight: bold;\">Travel Window:</strong> </li>\n<li style=\"margin-bottom: 8px; line-height: 24px;\">Travel valid from <strong style=\"font-weight: bold;\">April 29 to August 27, 2025</strong>.</li>\n<li style=\"margin-bottom: 8px; line-height: 24px;\"><strong style=\"font-weight: bold;\">Exceptional Value:</strong> </li>\n<li style=\"margin-bottom: 8px; line-height: 24px;\">This price allows budget travelers to enjoy a complete Hawaiian experience at a fraction of normal airfare.</li>\n<li style=\"margin-bottom: 8px; line-height: 24px;\"><strong style=\"font-weight: bold;\">Restrictions:</strong> </li>\n<li style=\"margin-bottom: 8px; line-height: 24px;\">21-day advance purchase required. Blackout dates include May 26, 2025. Limited days are available in certain markets. All fares are nonrefundable.</li>\n</ul>\n<p style=\"font-size: 16px; line-height: 24px; margin-top: 10px; margin-bottom: 10px; color: #2D2D2D;\">Book now to lock in your Hawaiian adventure!</p>\n<hr />\n<h1 style=\"font-size: 28px; font-weight: bold; color: #2A2A2A; line-height: 34px; margin-top: 20px; margin-bottom: 10px;\"></h1>",
                    "button_text": "Book Now!",
                    "button_url": "https://bytesizetravel.com/deals"
                    },
                    {
                    "title": "Deal 2: \ud83c\udf1e Sun, Sand, and $1,100 Off at Sandals Resorts",
                    "content": "<p style=\"font-size: 16px; line-height: 24px; margin-top: 10px; margin-bottom: 10px; color: #2D2D2D;\">Escape to the Caribbean with Sandals Resorts, which is offering up to <strong style=\"font-weight: bold;\">$1,100 off</strong> your stay along with additional credits and savings.</p>\n<ul style=\"margin-left: 20px; padding-left: 0;\">\n<li style=\"margin-bottom: 8px; line-height: 24px;\"><strong style=\"font-weight: bold;\">Destination:</strong> Sandals Resorts in the Caribbean</li>\n<li style=\"margin-bottom: 8px; line-height: 24px;\">With 17 stunning resorts to choose from, indulge in luxury amid Caribbean landscapes and vibrant local culture.</li>\n<li style=\"margin-bottom: 8px; line-height: 24px;\"><strong style=\"font-weight: bold;\">Pricing:</strong> </li>\n<li style=\"margin-bottom: 8px; line-height: 24px;\">Rates start at just <strong style=\"font-weight: bold;\">$199 per person, per night</strong>.</li>\n<li style=\"margin-bottom: 8px; line-height: 24px;\"><strong style=\"font-weight: bold;\">Booking Deadline:</strong> </li>\n<li style=\"margin-bottom: 8px; line-height: 24px;\">Secure your deal by <strong style=\"font-weight: bold;\">April 20, 2025</strong>.</li>\n<li style=\"margin-bottom: 8px; line-height: 24px;\"><strong style=\"font-weight: bold;\">Travel Window:</strong> </li>\n<li style=\"margin-bottom: 8px; line-height: 24px;\">Valid for visits from <strong style=\"font-weight: bold;\">April 15, 2025, to December 5, 2026</strong>.</li>\n<li style=\"margin-bottom: 8px; line-height: 24px;\"><strong style=\"font-weight: bold;\">Exceptional Value:</strong></li>\n<li style=\"margin-bottom: 8px; line-height: 24px;\">For longer stays, benefit from a <strong style=\"font-weight: bold;\">$150 resort credit</strong> and up to <strong style=\"font-weight: bold;\">one free night</strong>. This makes your luxurious experience affordable!</li>\n<li style=\"margin-bottom: 8px; line-height: 24px;\"><strong style=\"font-weight: bold;\">Restrictions:</strong> </li>\n<li style=\"margin-bottom: 8px; line-height: 24px;\">Specific conditions apply for savings based on your stay length (3+ nights to 7+ nights). Don't miss out on this tropical escape!</li>\n</ul>\n<p style=\"font-size: 16px; line-height: 24px; margin-top: 10px; margin-bottom: 10px; color: #2D2D2D;\">Claim your slice of paradise now!</p>\n<hr />\n<h1 style=\"font-size: 28px; font-weight: bold; color: #2A2A2A; line-height: 34px; margin-top: 20px; margin-bottom: 10px;\"></h1>",
                    "button_text": "Book Now!",
                    "button_url": "https://bytesizetravel.com/deals"
                    },
                    {
                    "title": "Deal 3: \u26f0\ufe0f Mark Your Calendar for a Yosemite Reservation",
                    "content": "<p style=\"font-size: 16px; line-height: 24px; margin-top: 10px; margin-bottom: 10px; color: #2D2D2D;\">For nature lovers, Yosemite National Park is reinstating its reservation system for summer visits, and it's time to plan!</p>\n<ul style=\"margin-left: 20px; padding-left: 0;\">\n<li style=\"margin-bottom: 8px; line-height: 24px;\"><strong style=\"font-weight: bold;\">Destination:</strong> Yosemite National Park, California</li>\n<li style=\"margin-bottom: 8px; line-height: 24px;\">Renowned for its awe-inspiring granite cliffs and waterfalls, Yosemite's natural beauty captivates adventurers and nature wanderers alike.</li>\n<li style=\"margin-bottom: 8px; line-height: 24px;\"><strong style=\"font-weight: bold;\">Pricing:</strong></li>\n<li style=\"margin-bottom: 8px; line-height: 24px;\">Entry permits will be available, allowing you to immerse in one of America's most iconic parks.</li>\n<li style=\"margin-bottom: 8px; line-height: 24px;\"><strong style=\"font-weight: bold;\">Booking Deadline:</strong> </li>\n<li style=\"margin-bottom: 8px; line-height: 24px;\">Reservations will be on sale starting <strong style=\"font-weight: bold;\">April 17, 2025</strong>.</li>\n<li style=\"margin-bottom: 8px; line-height: 24px;\"><strong style=\"font-weight: bold;\">Travel Window:</strong></li>\n<li style=\"margin-bottom: 8px; line-height: 24px;\">Reservations are valid from <strong style=\"font-weight: bold;\">June 19 to August 25, 2025</strong>.</li>\n<li style=\"margin-bottom: 8px; line-height: 24px;\"><strong style=\"font-weight: bold;\">Exceptional Value:</strong> </li>\n<li style=\"margin-bottom: 8px; line-height: 24px;\">Timed entries effectively reduce congestion and enhance your experience of the park's grandeur.</li>\n<li style=\"margin-bottom: 8px; line-height: 24px;\"><strong style=\"font-weight: bold;\">Restrictions:</strong> </li>\n<li style=\"margin-bottom: 8px; line-height: 24px;\">Valid for all park entrances except Hetch Hetchy, which is first-come, first-served. Reservations allow entrance for three consecutive days.</li>\n</ul>\n<p style=\"font-size: 16px; line-height: 24px; margin-top: 10px; margin-bottom: 10px; color: #2D2D2D;\">Prepare for the wild wonders of Yosemite!</p>\n<hr />\n<h1 style=\"font-size: 28px; font-weight: bold; color: #2A2A2A; line-height: 34px; margin-top: 20px; margin-bottom: 10px;\"></h1>",
                    "button_text": "Book Now!",
                    "button_url": "https://bytesizetravel.com/deals"
                    }
                ],
                "destination_guides": [
                    {
                    "title": "\ud83c\udf0c Stargazing Adventures in the US",
                    "content": "<p style=\"font-size: 16px; line-height: 24px; margin-top: 10px; margin-bottom: 10px; color: #2D2D2D;\">Spring nights are perfect for stargazing, and the US is home to some of the darkest skies ideal for such adventures. Here are a few highlighted locations:</p>\n<ol style=\"margin-left: 20px; padding-left: 0;\">\n<li style=\"margin-bottom: 8px; line-height: 24px;\"><strong style=\"font-weight: bold;\">Death Valley National Park, California</strong></li>\n<li style=\"margin-bottom: 8px; line-height: 24px;\">\n<p style=\"font-size: 16px; line-height: 24px; margin-top: 10px; margin-bottom: 10px; color: #2D2D2D;\">Recognized as a Gold Tier Dark Sky Park, Death Valley offers breathtaking views of the Milky Way and has rich geological wonders.</p>\n</li>\n<li style=\"margin-bottom: 8px; line-height: 24px;\">\n<p style=\"font-size: 16px; line-height: 24px; margin-top: 10px; margin-bottom: 10px; color: #2D2D2D;\"><strong style=\"font-weight: bold;\">Moab, Utah</strong></p>\n</li>\n<li style=\"margin-bottom: 8px; line-height: 24px;\">Known for its clear skies and minimal light pollution, Moab is perfect for night sky enthusiasts. The nearby national parks boast exquisite views.</li>\n</ol>\n<p style=\"font-size: 16px; line-height: 24px; margin-top: 10px; margin-bottom: 10px; color: #2D2D2D;\"><strong style=\"font-weight: bold;\">Local Cuisine Recommendations:</strong>\n- Taste the local flavors with delicious barbecue in Moab or experience traditional southwestern fare in Death Valley.</p>\n<p style=\"font-size: 16px; line-height: 24px; margin-top: 10px; margin-bottom: 10px; color: #2D2D2D;\"><strong style=\"font-weight: bold;\">Practical Information:</strong>\n- Bring a telescope or binoculars for optimal viewing, and consider visiting in early spring when skies are still clear and temperatures moderate.</p>\n<hr />\n<h1 style=\"font-size: 28px; font-weight: bold; color: #2A2A2A; line-height: 34px; margin-top: 20px; margin-bottom: 10px;\"></h1>",
                    "image_url": "https://placehold.co/600x400/faedca/0c457d?text=Travel"
                    },
                    {
                    "title": "\u2708\ufe0f Booking a Lufthansa First-Class Flight to Europe",
                    "content": "<p style=\"font-size: 16px; line-height: 24px; margin-top: 10px; margin-bottom: 10px; color: #2D2D2D;\">For those dreaming about luxury travel, booking first-class flights with your Ultimate Rewards points can provide an unforgettable experience.</p>\n<ol style=\"margin-left: 20px; padding-left: 0;\">\n<li style=\"margin-bottom: 8px; line-height: 24px;\"><strong style=\"font-weight: bold;\">Availability:</strong></li>\n<li style=\"margin-bottom: 8px; line-height: 24px;\">\n<p style=\"font-size: 16px; line-height: 24px; margin-top: 10px; margin-bottom: 10px; color: #2D2D2D;\">Lufthansa offers first-class services on select long-haul routes between major US cities and Europe. Consider booking well in advance.</p>\n</li>\n<li style=\"margin-bottom: 8px; line-height: 24px;\">\n<p style=\"font-size: 16px; line-height: 24px; margin-top: 10px; margin-bottom: 10px; color: #2D2D2D;\"><strong style=\"font-weight: bold;\">Points &amp; Miles:</strong></p>\n</li>\n<li style=\"margin-bottom: 8px; line-height: 24px;\">\n<p style=\"font-size: 16px; line-height: 24px; margin-top: 10px; margin-bottom: 10px; color: #2D2D2D;\">Right now, the Chase Sapphire Preferred\u00ae Card is offering <strong style=\"font-weight: bold;\">100,000 points</strong> after spending $5,000 in the first 3 months, ideal for covering first-class tickets.</p>\n</li>\n<li style=\"margin-bottom: 8px; line-height: 24px;\">\n<p style=\"font-size: 16px; line-height: 24px; margin-top: 10px; margin-bottom: 10px; color: #2D2D2D;\"><strong style=\"font-weight: bold;\">Booking Tips:</strong></p>\n</li>\n<li style=\"margin-bottom: 8px; line-height: 24px;\">Use flexibility with dates and book close to 14 days before departure, as first-class award seats can be released.</li>\n</ol>\n<p style=\"font-size: 16px; line-height: 24px; margin-top: 10px; margin-bottom: 10px; color: #2D2D2D;\"><strong style=\"font-weight: bold;\">Conclusion:</strong> Redeeming points for luxurious travel experiences heightens your journey and enhances memorable moments.</p>\n<hr />\n<h1 style=\"font-size: 28px; font-weight: bold; color: #2A2A2A; line-height: 34px; margin-top: 20px; margin-bottom: 10px;\"></h1>",
                    "image_url": "https://placehold.co/600x400/faedca/0c457d?text=Travel"
                    }
                ],
                "travel_news": {
                    "title": "Travel News",
                    "items": [
                    {
                        "title": "\ud83d\ude22 Brazil Resumes Visa Requirements for US Travelers",
                        "content": "<p style=\"font-size: 16px; line-height: 24px; margin-top: 10px; margin-bottom: 10px; color: #2D2D2D;\">Brazil has reinstated visa requirements for travelers from the US, Canada, and Australia, costing $80.90 for an electronic visa valid for up to 90 days. </p>\n<h1 style=\"font-size: 28px; font-weight: bold; color: #2A2A2A; line-height: 34px; margin-top: 20px; margin-bottom: 10px;\"></h1>"
                    },
                    {
                        "title": "\ud83d\udce3 Points Newbie and Pro Updates",
                        "content": "<ul style=\"margin-left: 20px; padding-left: 0;\">\n<li style=\"margin-bottom: 8px; line-height: 24px;\">An exciting moment for points enthusiasts! The Chase Sapphire Preferred\u00ae Card has launched its best-ever welcome offer of <strong style=\"font-weight: bold;\">100,000 points</strong>.</li>\n<li style=\"margin-bottom: 8px; line-height: 24px;\">Alaska Airlines is simplifying its frequent flyer status requirements, lowering the minimum miles needed to as low as <strong style=\"font-weight: bold;\">10,000 miles</strong>.</li>\n</ul>\n<h1 style=\"font-size: 28px; font-weight: bold; color: #2A2A2A; line-height: 34px; margin-top: 20px; margin-bottom: 10px;\"></h1>"
                    },
                    {
                        "title": "\u2708\ufe0f American Airlines Enhances Layovers",
                        "content": "<p style=\"font-size: 16px; line-height: 24px; margin-top: 10px; margin-bottom: 10px; color: #2D2D2D;\">American Airlines has launched a new pilot program allowing certain passengers on international flights to skip baggage collection during domestic transit. A game-changer for frequent flyers!</p>\n<hr />\n<h1 style=\"font-size: 28px; font-weight: bold; color: #2A2A2A; line-height: 34px; margin-top: 20px; margin-bottom: 10px;\"></h1>"
                    }
                    ]
                },
                "travel_tips": {
                    "title": "Smart Travel Tips",
                    "content": "<h3 style=\"font-size: 20px; font-weight: bold; color: #2A2A2A; line-height: 26px; margin-top: 16px; margin-bottom: 8px;\">Budget-Conscious Strategies for Traveling</h3>\n<ol style=\"margin-left: 20px; padding-left: 0;\">\n<li style=\"margin-bottom: 8px; line-height: 24px;\"><strong style=\"font-weight: bold;\">Use Price Alerts:</strong> Set fare alerts on platforms like Google Flights to snag the best prices.</li>\n<li style=\"margin-bottom: 8px; line-height: 24px;\"><strong style=\"font-weight: bold;\">Flexible Destination Search:</strong> Tools like SkyScanner allow browsing nearby locations for budget-friendly options.</li>\n<li style=\"margin-bottom: 8px; line-height: 24px;\"><strong style=\"font-weight: bold;\">Utilize Travel Credits:</strong> Pay attention to the offers and bonuses from credit card sign-ups for additional savings on trips.</li>\n</ol>\n<h3 style=\"font-size: 20px; font-weight: bold; color: #2A2A2A; line-height: 26px; margin-top: 16px; margin-bottom: 8px;\">Packing for Different Conditions</h3>\n<p style=\"font-size: 16px; line-height: 24px; margin-top: 10px; margin-bottom: 10px; color: #2D2D2D;\">When packing, consider moisture-wicking fabrics for mountain trips and breathable materials for beach vacations. Versatile layers can adapt to varying climates.</p>\n<h3 style=\"font-size: 20px; font-weight: bold; color: #2A2A2A; line-height: 26px; margin-top: 16px; margin-bottom: 8px;\">Cultural Etiquette</h3>\n<p style=\"font-size: 16px; line-height: 24px; margin-top: 10px; margin-bottom: 10px; color: #2D2D2D;\">Research local customs of your destination. Simple gestures, such as greetings or dining etiquette, can enrich your travel experience.</p>\n<hr />\n<h1 style=\"font-size: 28px; font-weight: bold; color: #2A2A2A; line-height: 34px; margin-top: 20px; margin-bottom: 10px;\"></h1>"
                },
                "conclusion": {
                    "content": "<p style=\"font-size: 16px; line-height: 24px; margin-top: 10px; margin-bottom: 10px; color: #2D2D2D;\">Thank you for joining us in this edition of ByteSize Travel Deals! Remember, our curated deals and knowledge are here to inspire your next adventure. With several opportunities to explore, don\u2019t let these offers slip away. \ud83c\udf0d\u2728 Be proactive and book your travels today\u2014because every journey starts with a single step or, in this case, a click!</p>\n<h3 style=\"font-size: 20px; font-weight: bold; color: #2A2A2A; line-height: 26px; margin-top: 16px; margin-bottom: 8px;\">Ready to book?</h3>\n<p style=\"font-size: 16px; line-height: 24px; margin-top: 10px; margin-bottom: 10px; color: #2D2D2D;\">Explore, save, and discover your next journey with us!</p>",
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
    sg_client.send_template_email_to_list(template_data)

if __name__ == "__main__":
    main()

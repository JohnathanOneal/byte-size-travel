import feedparser
from dotenv import load_dotenv
from typing import Dict, List
import imaplib
import email
from email.header import decode_header
from datetime import datetime
import os
from contextlib import contextmanager
import logging
import requests

# Setup logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
load_dotenv()


@contextmanager
def gmail_connection(email_account, app_password):
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    try:
        mail.login(email_account, app_password)
        yield mail
    finally:
        try:
            mail.logout()
        except:
            pass


def extract_email_body(msg: email.message.Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                return part.get_payload(decode=True).decode()
    return msg.get_payload(decode=True).decode()


def email_feed_parser_gmail(source: Dict) -> List[Dict]:
    """Fetch and parse emails from a Gmail inbox using IMAP and App Password."""
    email_account = os.getenv(source["provider"])
    app_password = os.getenv(source["password"])

    if not email_account or not app_password:
        logger.error(f"Missing credentials for source: {source['name']}")
        return []

    try:
        with gmail_connection(email_account, app_password) as mail:
            mail.select("inbox")
            source_email = source.get("url")
            status, messages = mail.search(None, f'FROM "{source_email}"')
            email_ids = messages[0].split()[:source.get("email_count", 10)]

            logger.info(f"Searching for emails from: {source_email}")

            entries = []
            for email_id in email_ids:
                try:
                    status, msg_data = mail.fetch(email_id, "(RFC822)")
                    msg = email.message_from_bytes(msg_data[0][1])

                    subject = decode_header(msg["subject"])
                    full_subject = ''
                    for part in subject:
                        message, encoding = part
                        if isinstance(message, bytes):
                            message = message.decode(encoding or 'utf-8')
                            full_subject += message

                    date = msg["date"].replace(" (UTC)", "")
                    date = datetime.strptime(date, "%a, %d %b %Y %H:%M:%S %z")

                    entries.append({
                        "title": full_subject,
                        "url": email_id.decode(),
                        "content": extract_email_body(msg),
                        "published_date": date,
                        "source_name": source.get("name"),
                        "source_url": source_email,
                        "is_full_content_fetched": True,
                    })
                except Exception as e:
                    logger.error(f"Error processing email {email_id}: {e}")
                    continue

            return entries

    except imaplib.IMAP4.error as e:
        logger.error(f"IMAP error: {e}")
        return []
    except ConnectionError as e:
        logger.error(f"Connection error: {e}")
        return []


def rss_feed_parser(source: Dict) -> List[Dict]:
    """Parse RSS feed and return entries."""
    feed = feedparser.parse(source['url'])
    if hasattr(feed, 'bozo_exception'):
        raise ValueError(f"Error parsing RSS feed: {feed.bozo_exception}")

    entries = []
    for entry in feed.entries[:10]:
        entries.append({
            "title": entry.title,
            "url": entry.link,
            "content": entry.get('description', ''),
            "published_date": datetime(*entry.published_parsed[:6]),
            "source_name": source["name"],
            "source_url": source["url"],
            "is_full_content_fetched": None,
        })
    return entries


def check_rss_feed(source: Dict) -> Dict:
    """Check if a rss feed URL is valid and accessible"""
    try:
        response = requests.get(source.get("url"), timeout=30)
        response.raise_for_status()

        feed = feedparser.parse(response.content)

        # feedparser's flag for malformed feeds
        if feed.bozo:
            return {"is_valid": False, "error": "Invalid feed format"}

        if not feed.entries:
            return {"is_valid": False, "error": "No entries found"}

        return {
            "is_valid": True,
            "title": feed.feed.title if "title" in feed.feed else "Unknown",
            "entry_count": len(feed.entries)
        }

    except requests.exceptions.Timeout:
        return {"is_valid": False, "error": "Request timed out"}
    except requests.exceptions.RequestException as e:
        return {"is_valid": False, "error": f"HTTP error: {str(e)}"}
    except Exception as e:
        return {"is_valid": False, "error": f"Unexpected error: {str(e)}"}


def check_email_feed(source: Dict) -> Dict:
    """Check if email credentials are valid and connection is possible."""
    try:
        # Get credentials from environment variables
        email_account = os.getenv(source["provider"])
        app_password = os.getenv(source["password"])

        if not email_account or not app_password:
            return {
                "is_valid": False,
                "error": "Missing email credentials"
            }

        # Try to connect to Gmail IMAP
        with imaplib.IMAP4_SSL("imap.gmail.com") as mail:
            # Attempt login
            mail.login(email_account, app_password)

            # Check if we can access inbox
            mail.select("inbox")

            # Check if we can search for target email if specified
            if target_email := source.get("target_email"):
                _, messages = mail.search(None, f"(TO '{target_email}')")
                message_count = len(messages[0].split())
            else:
                _, messages = mail.search(None, "ALL")
                message_count = len(messages[0].split())

            return {
                "is_valid": True,
                "title": f"Email Feed ({email_account})",
                "entry_count": message_count
            }

    except imaplib.IMAP4.error as e:
        return {
            "is_valid": False,
            "error": f"IMAP error: {str(e)}"
        }
    except Exception as e:
        return {
            "is_valid": False,
            "error": f"Unexpected error: {str(e)}"
        }

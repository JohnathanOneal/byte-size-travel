import feedparser
from dotenv import load_dotenv
from typing import Dict, List
import imaplib
import email
from email.header import decode_header
from datetime import datetime
import os
from contextlib import contextmanager
from config.logging_config import fetch_logger as logger
import requests
from time import perf_counter
from src.source_manager import EmailSource, RSSSource

load_dotenv()


@contextmanager
def gmail_connection(email_account: str, app_password: str):
    """Context manager for Gmail IMAP connection"""
    start_time = perf_counter()
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    logger.debug(f"Established IMAP connection in {perf_counter() - start_time:.2f}s")

    try:
        mail.login(email_account, app_password)
        logger.debug(f"Logged in as {email_account}")
        yield mail
    finally:
        try:
            mail.logout()
            logger.debug("IMAP connection closed properly")
        except Exception as e:
            logger.warning(f"Issue during IMAP logout: {e}")


def decode_payload(part: email.message.Message) -> str:
    """Robustly decode email payload handling different encodings"""
    try:
        # Try the specified charset first
        charset = part.get_content_charset() or 'utf-8'
        return part.get_payload(decode=True).decode(charset)
    except (UnicodeDecodeError, LookupError):
        # Fallback encoding attempts
        for encoding in ['utf-8', 'iso-8859-1', 'cp1252']:
            try:
                return part.get_payload(decode=True).decode(encoding)
            except UnicodeDecodeError:
                continue
        # Last resort: replace invalid chars
        return part.get_payload(decode=True).decode('utf-8', errors='replace')


def extract_email_body(msg: email.message.Message) -> str:
    """Extract email body with better handling of different content types"""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    return decode_payload(part)
                except Exception as e:
                    logger.warning(f"Failed to decode email part: {e}")
                    continue
    try:
        return decode_payload(msg)
    except Exception as e:
        logger.error(f"Failed to extract email body: {e}")
        return ""


def email_feed_parser_gmail(source: Dict) -> List[Dict]:
    """Fetch and parse emails from Gmail with improved logging and error handling"""
    start_time = perf_counter()
    email_account = os.getenv(source["provider"])
    app_password = os.getenv(source["password"])

    if not email_account or not app_password:
        logger.error(f"Missing credentials for email source: {source['name']}")
        return []

    try:
        with gmail_connection(email_account, app_password) as mail:
            mail.select("inbox")
            source_email = source.get("url")
            email_count = source.get("email_count", 10)

            logger.info(f"Fetching up to {email_count} emails from {source_email}")
            status, messages = mail.search(None, f'FROM "{source_email}"')
            email_ids = messages[0].split()[:email_count]

            if not email_ids:
                logger.warning(f"No emails found from {source_email}")
                return []

            entries = []
            for i, email_id in enumerate(email_ids, 1):
                email_start = perf_counter()
                try:
                    status, msg_data = mail.fetch(email_id, "(RFC822)")
                    msg = email.message_from_bytes(msg_data[0][1])

                    # Parse subject with better error handling
                    subject = decode_header(msg["subject"])
                    full_subject = ''.join(
                        part[0].decode(part[1] or 'utf-8') if isinstance(part[0], bytes)
                        else str(part[0]) for part in subject
                    )
                    # Remove timezone suffix
                    date_str = msg['date'].split(' (')[0]
                    try:
                        date = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
                    except ValueError:
                        logger.warning(f"Could not parse date: {date_str}")
                        date = datetime.now()

                    entries.append({
                        "title": full_subject,
                        "url": email_id.decode(),
                        "content": extract_email_body(msg),
                        "published_date": date,
                        "source_name": source.get("name"),
                        "source_url": source_email,
                        "is_full_content_fetched": True,
                    })
                    logger.debug(
                        f"Processed email {i}/{len(email_ids)} in "
                        f"{perf_counter() - email_start:.2f}s: {full_subject[:50]}..."
                    )
                except Exception as e:
                    logger.error(f"Error processing email {email_id}: {e}", exc_info=True)
                    continue

            total_time = perf_counter() - start_time
            logger.info(
                f"Processed {len(entries)}/{len(email_ids)} emails in {total_time:.2f}s"
            )
            return entries

    except imaplib.IMAP4.error as e:
        logger.error(f"IMAP error for {source['name']}: {e}", exc_info=True)
        return []
    except Exception as e:
        logger.error(f"Unexpected error for {source['name']}: {e}", exc_info=True)
        return []


def rss_feed_parser(source: Dict) -> List[Dict]:
    """Parse RSS feed with improved logging and error handling"""
    start_time = perf_counter()
    logger.info(f"Fetching RSS feed: {source['url']}")

    try:
        response = requests.get(source['url'], timeout=30)
        response.raise_for_status()
        feed = feedparser.parse(response.content)

        if hasattr(feed, 'bozo_exception'):
            logger.error(f"Feed parsing error: {feed.bozo_exception}")
            raise ValueError(f"Error parsing RSS feed: {feed.bozo_exception}")

        entries = []
        total_entries = len(feed.entries[:10])

        for i, entry in enumerate(feed.entries[:10], 1):
            try:
                entries.append({
                    "title": entry.title,
                    "url": entry.link,
                    "content": entry.get('description', ''),
                    "published_date": datetime(*entry.published_parsed[:6]),
                    "source_name": source["name"],
                    "source_url": source["url"],
                    "is_full_content_fetched": None,
                })
                logger.debug(f"Processed entry {i}/{total_entries}: {entry.title[:50]}...")
            except Exception as e:
                logger.error(f"Error processing entry {i}: {e}")
                continue

        total_time = perf_counter() - start_time
        logger.info(
            f"Processed {len(entries)}/{total_entries} entries in {total_time:.2f}s"
        )
        return entries

    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP error fetching {source['url']}: {e}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Unexpected error parsing {source['url']}: {e}", exc_info=True)
        raise


def check_rss_feed(source: Dict) -> Dict:
    """Validate RSS feed with improved diagnostics"""
    start_time = perf_counter()
    logger.info(f"Checking RSS feed: {source['url']}")

    try:
        # Validate source structure
        source_model = RSSSource(**source)

        response = requests.get(str(source_model.url), timeout=30)
        response.raise_for_status()

        feed = feedparser.parse(response.content)
        total_time = perf_counter() - start_time

        if feed.bozo:
            logger.error(f"Invalid feed format: {feed.bozo_exception}")
            return {"is_valid": False, "error": str(feed.bozo_exception)}

        if not feed.entries:
            logger.warning(f"No entries found in feed (took {total_time:.2f}s)")
            return {"is_valid": False, "error": "No entries found"}

        logger.info(
            f"Valid RSS feed: {feed.feed.get('title', 'Unknown')} "
            f"({len(feed.entries)} entries, took {total_time:.2f}s)"
        )
        return {
            "is_valid": True,
            "title": feed.feed.get('title', 'Unknown'),
            "entry_count": len(feed.entries)
        }

    except Exception as e:
        logger.error(f"Error validating RSS feed: {e}", exc_info=True)
        return {"is_valid": False, "error": str(e)}


def check_email_feed(source: Dict) -> Dict:
    """Validate email feed with improved diagnostics"""
    start_time = perf_counter()
    logger.info(f"Checking email feed: {source.get('name')}")

    try:
        # Validate source structure
        source_model = EmailSource(**source)

        email_account = os.getenv(source_model.provider)
        app_password = os.getenv(source_model.password)

        with gmail_connection(email_account, app_password) as mail:
            mail.select("inbox")
            target_email = str(source_model.url)

            _, messages = mail.search(None, f'FROM "{target_email}"')
            message_count = len(messages[0].split())
            logger.info(f"Found {message_count} messages from {target_email}")

            total_time = perf_counter() - start_time
            logger.info(f"Email feed check completed in {total_time:.2f}s")

            return {
                "is_valid": True,
                "title": f"Email Feed ({email_account})",
                "entry_count": message_count
            }

    except Exception as e:
        logger.error(f"Error validating email feed: {e}", exc_info=True)
        return {"is_valid": False, "error": str(e)}

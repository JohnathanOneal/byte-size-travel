import imaplib
import email
from email.header import decode_header
from typing import List, Dict
from datetime import datetime
import logging
import feedparser

# Setup logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def email_feed_parser_gmail(source: Dict) -> List[Dict]:
    """Fetch and parse emails from a Gmail inbox using IMAP and App Password."""
    try:
        # IMAP server details for Gmail
        imap_server = "imap.gmail.com"
        email_account = source["username"]
        app_password = source["password"]

        # Connect to the Gmail IMAP server
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(email_account, app_password)

        # Select the inbox (default is 'INBOX')
        mail.select("inbox")

        # Search for all emails (you can modify the search criteria)
        status, messages = mail.search(None, "ALL")
        email_ids = messages[0].split()[:source.get("email_count", 10)]  # Limit to 10 emails by default

        entries = []
        for email_id in email_ids:
            # Fetch the email by ID
            status, msg_data = mail.fetch(email_id, "(RFC822)")
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            # Decode the subject (handling encoding)
            subject, encoding = decode_header(msg["subject"])[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding if encoding else 'utf-8')

            # Extract the date
            date_str = msg["date"]
            published_date = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")

            # Extract the sender's email (handle multiple addresses)
            sender = msg.get("From", "Unknown Sender")

            # Extract the email body (handle multipart emails)
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode()
                        break
            else:
                body = msg.get_payload(decode=True).decode()

            # Prepare the entry with all necessary data
            entries.append({
                "title": subject,  # Use the subject as the title
                "url": email_id.decode(),  # Use the email ID as a unique URL
                "content": body,  # The email body content
                "published_date": published_date,
                "source_name": source["name"],  # Source name
                "source_url": "",  # Empty for email sources
                "is_full_content_fetched": None,  # No need to fetch further content for emails
            })

        # Logout from the Gmail IMAP server
        mail.logout()

        return entries

    except Exception as e:
        logger.error(f"Error fetching emails from Gmail: {e}")
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

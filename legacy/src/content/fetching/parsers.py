import email
import imaplib
import os
import re
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from email.header import decode_header
from time import perf_counter

import feedparser
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from config.logging_config import fetch_logger as logger
from config.source_manager import EmailSource, RSSSource

load_dotenv()


@contextmanager
def gmail_connection(
    email_account: str, app_password: str
) -> Generator[imaplib.IMAP4_SSL, None, None]:
    start_time = perf_counter()
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    elapsed = perf_counter() - start_time
    logger.debug("Established IMAP connection in %.2fs", elapsed)

    try:
        mail.login(email_account, app_password)
        logger.debug("Logged in as %s", email_account)
        yield mail
    finally:
        try:
            mail.logout()
            logger.debug("IMAP connection closed properly")
        except imaplib.IMAP4.error:
            logger.warning("Issue during IMAP logout", exc_info=True)


def decode_payload(part: email.message.Message) -> str:
    try:
        charset = part.get_content_charset() or "utf-8"
        return part.get_payload(decode=True).decode(charset)
    except (UnicodeDecodeError, LookupError):
        for encoding in ["utf-8", "iso-8859-1", "cp1252"]:
            try:
                return part.get_payload(decode=True).decode(encoding)
            except UnicodeDecodeError:
                continue
        return part.get_payload(decode=True).decode("utf-8", errors="replace")


def clean_text(text: str) -> str:
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    return " ".join(chunk for chunk in chunks if chunk)


def clean_html_content(html_content: str) -> str:
    try:
        soup = BeautifulSoup(html_content, "html.parser")
        for element in soup(["script", "style", "head"]):
            element.decompose()
        text = " ".join(soup.stripped_strings)

        text = re.sub(r"[\u200c\xa0\ufeff\n\r\t]", " ", text)
        return re.sub(r"\s+", " ", text).strip()
    except (TypeError, AttributeError):
        logger.exception("Failed to clean HTML")
        return html_content


def _extract_multipart_body(
    msg: email.message.Message,
) -> tuple[str, str]:
    text_content = ""
    html_content = ""

    for part in msg.walk():
        if (
            part.get_content_maintype() == "multipart"
            or part.get("Content-Disposition") is not None
        ):
            continue

        try:
            decoded_content = decode_payload(part)
            if part.get_content_type() == "text/plain":
                text_content += decoded_content + "\n"
            elif part.get_content_type() == "text/html":
                html_content += decoded_content
        except (UnicodeDecodeError, AttributeError):
            logger.warning("Failed to decode email part", exc_info=True)
            continue

    return text_content, html_content


def _extract_single_body(
    msg: email.message.Message,
) -> tuple[str, str]:
    text_content = ""
    html_content = ""

    try:
        content = decode_payload(msg)
        if msg.get_content_type() == "text/plain":
            text_content = content
        elif msg.get_content_type() == "text/html":
            html_content = content
    except (UnicodeDecodeError, AttributeError):
        logger.exception("Failed to extract email body")

    return text_content, html_content


def extract_email_body(msg: email.message.Message) -> str:
    if msg.is_multipart():
        text_content, html_content = _extract_multipart_body(msg)
    else:
        text_content, html_content = _extract_single_body(msg)

    if html_content:
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            for element in soup(["script", "style", "head"]):
                element.decompose()
            " ".join(soup.stripped_strings)
        except (TypeError, AttributeError):
            logger.exception("Failed to parse HTML content")

    if html_content:
        return clean_html_content(html_content)
    return text_content.strip()


def _parse_email_date(date_str: str) -> datetime:
    date_str = date_str.split(" (", maxsplit=1)[0]
    try:
        return datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
    except ValueError:
        logger.warning("Could not parse date: %s", date_str)
        return datetime.now(tz=UTC)


def _process_single_email(
    mail: imaplib.IMAP4_SSL,
    email_id: bytes,
    index: int,
    total: int,
) -> dict | None:
    email_start = perf_counter()
    try:
        _status, msg_data = mail.fetch(email_id, "(RFC822)")
        msg = email.message_from_bytes(msg_data[0][1])

        subject = decode_header(msg["subject"])
        full_subject = "".join(
            part[0].decode(part[1] or "utf-8")
            if isinstance(part[0], bytes)
            else str(part[0])
            for part in subject
        )
        date = _parse_email_date(msg["date"])

        entry = {
            "title": full_subject,
            "url": email_id.decode(),
            "content": extract_email_body(msg),
            "published_date": date,
            "is_full_content_fetched": True,
        }
        elapsed = perf_counter() - email_start
        logger.debug(
            "Processed email %d/%d in %.2fs: %s...",
            index,
            total,
            elapsed,
            full_subject[:50],
        )
    except (
        UnicodeDecodeError,
        AttributeError,
        KeyError,
        IndexError,
    ):
        logger.exception("Error processing email %s", email_id)
        return None
    else:
        return entry


def email_feed_parser_gmail(source: dict) -> list[dict]:
    start_time = perf_counter()
    email_account = os.getenv(source["provider"])
    app_password = os.getenv(source["password"])

    if not email_account or not app_password:
        logger.error(
            "Missing credentials for email source: %s",
            source["name"],
        )
        return []

    try:
        with gmail_connection(email_account, app_password) as mail:
            mail.select("inbox")
            source_email = source.get("url")
            email_count = source.get("email_count", 20)

            logger.info(
                "Fetching up to %d emails from %s",
                email_count,
                source_email,
            )
            _status, messages = mail.search(None, f'FROM "{source_email}"')
            email_ids = messages[0].split()[::-1][:email_count]

            if not email_ids:
                logger.warning("No emails found from %s", source_email)
                return []

            entries = []
            for i, eid in enumerate(email_ids, 1):
                entry = _process_single_email(mail, eid, i, len(email_ids))
                if entry is not None:
                    entries.append(entry)

            total_time = perf_counter() - start_time
            logger.info(
                "Processed %d/%d emails in %.2fs",
                len(entries),
                len(email_ids),
                total_time,
            )
            return entries

    except imaplib.IMAP4.error:
        logger.exception("IMAP error for %s", source["name"])
        return []
    except OSError:
        logger.exception("IO error for %s", source["name"])
        return []


def rss_feed_parser(source: dict) -> list[dict]:
    start_time = perf_counter()
    logger.info("Fetching RSS feed: %s", source["url"])

    try:
        response = requests.get(source["url"], timeout=30)
        response.raise_for_status()
        feed = feedparser.parse(response.content)

        if hasattr(feed, "bozo_exception"):
            logger.error("Feed parsing error: %s", feed.bozo_exception)
            msg = f"Error parsing RSS feed: {feed.bozo_exception}"
            raise ValueError(msg)

        entries = []
        total_entries = len(feed.entries[:10])

        for i, entry in enumerate(feed.entries[:10], 1):
            try:
                entries.append(
                    {
                        "title": entry.title,
                        "url": entry.link,
                        "content": entry.get("description", ""),
                        "published_date": datetime(
                            *entry.published_parsed[:6],
                            tzinfo=UTC,
                        ),
                        "is_full_content_fetched": False,
                    }
                )
                logger.debug(
                    "Processed entry %d/%d: %s...",
                    i,
                    total_entries,
                    entry.title[:50],
                )
            except (
                AttributeError,
                KeyError,
                TypeError,
                ValueError,
            ):
                logger.exception("Error processing entry %d", i)
                continue

    except requests.exceptions.RequestException:
        logger.exception("HTTP error fetching %s", source["url"])
        raise
    else:
        total_time = perf_counter() - start_time
        logger.info(
            "Processed %d/%d entries in %.2fs",
            len(entries),
            total_entries,
            total_time,
        )
        return entries


def check_rss_feed(source: dict) -> dict:
    start_time = perf_counter()
    logger.info("Checking RSS feed: %s", source["url"])

    try:
        source_model = RSSSource(**source)

        response = requests.get(str(source_model.url), timeout=30)
        response.raise_for_status()

        feed = feedparser.parse(response.content)
        total_time = perf_counter() - start_time

        if feed.bozo:
            logger.error("Invalid feed format: %s", feed.bozo_exception)
            return {
                "is_valid": False,
                "error": str(feed.bozo_exception),
            }

        if not feed.entries:
            logger.warning(
                "No entries found in feed (took %.2fs)",
                total_time,
            )
            return {"is_valid": False, "error": "No entries found"}

        logger.info(
            "Valid RSS feed: %s (%d entries, took %.2fs)",
            feed.feed.get("title", "Unknown"),
            len(feed.entries),
            total_time,
        )
        return {
            "is_valid": True,
            "title": feed.feed.get("title", "Unknown"),
            "entry_count": len(feed.entries),
        }

    except requests.exceptions.RequestException:
        logger.exception("HTTP error checking feed")
        return {"is_valid": False, "error": "HTTP error"}
    except (ValueError, TypeError, AttributeError):
        logger.exception("Error validating RSS feed")
        return {"is_valid": False, "error": "Validation error"}


def check_email_feed(source: dict) -> dict:
    start_time = perf_counter()
    logger.info("Checking email feed: %s", source.get("name"))

    try:
        source_model = EmailSource(**source)

        email_account = os.getenv(source_model.provider)
        app_password = os.getenv(source_model.password)

        with gmail_connection(email_account, app_password) as mail:
            mail.select("inbox")
            target_email = str(source_model.url)

            _, messages = mail.search(None, f'FROM "{target_email}"')
            message_count = len(messages[0].split())
            logger.info(
                "Found %d messages from %s",
                message_count,
                target_email,
            )

            total_time = perf_counter() - start_time
            logger.info(
                "Email feed check completed in %.2fs",
                total_time,
            )

            return {
                "is_valid": True,
                "title": f"Email Feed ({email_account})",
                "entry_count": message_count,
            }

    except imaplib.IMAP4.error:
        logger.exception("IMAP error")
        return {"is_valid": False, "error": "IMAP error"}
    except (ValueError, TypeError, AttributeError):
        logger.exception("Error validating email feed")
        return {"is_valid": False, "error": "Validation error"}

import os
import base64
from datetime import datetime, timezone
from email import message_from_bytes

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import re
import html as _html

def build_gmail_service(token: dict):
    creds = Credentials(
        token.get("access_token"),
        refresh_token=token.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ.get("GMAIL_OAUTH_CLIENT_ID"),
        client_secret=os.environ.get("GMAIL_OAUTH_CLIENT_SECRET"),
    )
    service = build("gmail", "v1", credentials=creds)
    return service

def fetch_today_messages(token: dict, max_results: int = 50):
    service = build_gmail_service(token)
    # build query for today's date
    today = datetime.now(timezone.utc).date()
    q = f"after:{today.strftime('%Y/%m/%d')}"
    results = service.users().messages().list(userId="me", q=q, maxResults=max_results).execute()
    messages = []
    for m in results.get("messages", []):
        msg = service.users().messages().get(userId="me", id=m["id"], format="raw").execute()
        raw = base64.urlsafe_b64decode(msg["raw"].encode("utf-8"))
        parsed = message_from_bytes(raw)
        subject = parsed.get("Subject", "")
        from_ = parsed.get("From", "")

        # Prefer text/plain parts; if only HTML is available, strip tags and
        # extract hrefs so classifier can detect actionable links.
        text_content = ""
        html_content = ""
        links: list[str] = []

        if parsed.is_multipart():
            for part in parsed.walk():
                ctype = part.get_content_type()
                disp = part.get_content_disposition()
                # ignore attachments
                if disp is not None and disp.lower() == 'attachment':
                    continue
                try:
                    payload = part.get_payload(decode=True)
                except Exception:
                    payload = None
                if not payload:
                    continue
                try:
                    text = payload.decode(part.get_content_charset() or 'utf-8', errors='replace')
                except Exception:
                    try:
                        text = payload.decode('utf-8', errors='replace')
                    except Exception:
                        text = ''
                if ctype == 'text/plain' and not text_content:
                    text_content = text
                elif ctype == 'text/html' and not html_content:
                    html_content = text
        else:
            payload = parsed.get_payload(decode=True)
            if isinstance(payload, (bytes, bytearray)):
                try:
                    text_content = payload.decode('utf-8', errors='replace')
                except Exception:
                    text_content = ''
            else:
                text_content = str(payload or '')

        # If we only have HTML, extract visible text and links.
        if html_content and not text_content:
            # crude strip tags for visible text
            text_content = _html.unescape(re.sub(r'<[^>]+>', ' ', html_content))

        # Always extract hrefs from html_content (if present) and also any raw urls
        if html_content:
            try:
                hrefs = re.findall(r'href=["\']([^"\']+)["\']', html_content, flags=re.IGNORECASE)
                links.extend(hrefs)
            except Exception:
                pass
        # also find raw urls in the text content
        try:
            raw_urls = re.findall(r'https?://\S+|www\.\S+', text_content or '')
            links.extend(raw_urls)
        except Exception:
            pass

        snippet = (text_content or '')[:1000]
        has_links = len(links) > 0
        messages.append({"id": m["id"], "from": from_, "subject": subject, "snippet": snippet, "links": links, "has_links": has_links})
    return messages

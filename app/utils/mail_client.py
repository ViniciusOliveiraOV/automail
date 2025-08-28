import imaplib
import email
from email.message import Message
from typing import Generator, Tuple, List

def fetch_unseen_imap(host: str, username: str, password: str, mailbox: str = "INBOX") -> Generator[Message, None, None]:
    conn = imaplib.IMAP4_SSL(host)
    conn.login(username, password)  # em produção prefira OAuth2
    conn.select(mailbox)
    status, messages = conn.search(None, 'UNSEEN')
    if status != "OK":
        conn.logout()
        return
    for num in messages[0].split():
        _, data = conn.fetch(num, '(RFC822)')
        if not data or data[0] is None:
            continue
        raw = data[0][1]
        if isinstance(raw, bytes):
            msg = email.message_from_bytes(raw)
            yield msg
    conn.logout()
def extract_text_and_attachments(msg: Message) -> Tuple[str, List[Tuple[str, bytes]]]:
    text_parts: List[str] = []
    attachments: List[Tuple[str, bytes]] = []
    for part in msg.walk():
        ctype = part.get_content_type()
        disp = str(part.get("Content-Disposition") or "")
        if ctype == "text/plain" and "attachment" not in disp:
            charset = part.get_content_charset() or "utf-8"
            payload = part.get_payload(decode=True)
        elif ctype == "text/html" and "attachment" not in disp and not text_parts:
            charset = part.get_content_charset() or "utf-8"
            payload = part.get_payload(decode=True)
            if isinstance(payload, bytes):
                html = payload.decode(charset, errors="ignore")
            else:
                continue
            # fallback: strip tags simply
            import re
            text = re.sub("<[^<]+?>", "", html)
            text_parts.append(text)
        elif part.get_filename():
            filename = part.get_filename()
            data = part.get_payload(decode=True)
            if filename and isinstance(data, bytes):
                attachments.append((filename, data))
    return "\n".join(text_parts).strip(), attachments
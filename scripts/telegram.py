"""Read public Telegram channel previews without credentials or third-party RSS mirrors.

Telegram's /s/<channel> page exposes message IDs, dates and text in HTML.
If a channel is private, blocked, or changes its markup, raise a meaningful
error so the aggregator preserves previously collected posts.
"""
import hashlib
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from html import unescape
from html.parser import HTMLParser


class TelegramMessages(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.messages = []
        self.current = None
        self.depth = 0
        self.text_depth = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        props = dict(attrs)
        classes = set(props.get("class", "").split())
        post = props.get("data-post")
        if tag == "div" and post and "tgme_widget_message" in classes:
            if self.current is not None:
                self.finish()
            self.current = {"post": post, "date": "", "text": ""}
            self.depth = 1
            self.text_depth = 0
            self.parts = []
            return
        if self.current is None:
            return
        if tag == "div":
            self.depth += 1
            if "tgme_widget_message_text" in classes:
                self.text_depth = self.depth
        if tag == "time" and props.get("datetime"):
            self.current["date"] = props["datetime"]
        if self.text_depth and tag == "br":
            self.parts.append("\n")
        if self.text_depth and tag in ("p", "blockquote"):
            self.parts.append("\n")

    def handle_data(self, data):
        if self.current is not None and self.text_depth:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if self.current is None:
            return
        if tag == "div":
            if self.text_depth and self.depth == self.text_depth:
                self.text_depth = 0
                self.current["text"] = "".join(self.parts).strip()
            self.depth -= 1
            if self.depth == 0:
                self.finish()

    def finish(self):
        if self.current is None:
            return
        if not self.current["text"] and self.parts:
            self.current["text"] = "".join(self.parts).strip()
        self.messages.append(self.current)
        self.current = None
        self.depth = 0
        self.text_depth = 0
        self.parts = []


def collect_telegram(name, category, url, now=None):
    now = now or datetime.now(timezone.utc)
    parsed = urllib.parse.urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    if parsed.hostname not in ("t.me", "telegram.me") or len(parts) < 2 or parts[0] != "s":
        raise ValueError("Expected public Telegram channel URL https://t.me/s/channel")
    channel = parts[1]
    endpoint = "https://t.me/s/" + urllib.parse.quote(channel)
    errors = []
    html = None
    for attempt in range(2):
        try:
            request = urllib.request.Request(
                endpoint,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; theDAWStudio/0.5; news aggregator)",
                    "Accept": "text/html,application/xhtml+xml;q=0.9",
                    "Accept-Language": "ru,en;q=0.8",
                },
            )
            with urllib.request.urlopen(request, timeout=12) as response:
                html = response.read(3_000_000).decode("utf-8", "replace")
            break
        except Exception as exc:
            errors.append(str(exc)[:130])
            if attempt == 0:
                time.sleep(1)
    if html is None:
        raise RuntimeError("Telegram unavailable: " + "; ".join(errors))

    parser = TelegramMessages()
    parser.feed(html)
    parser.finish()
    if not parser.messages:
        raise RuntimeError("No public Telegram messages in the channel preview")

    items = {}
    for post in parser.messages:
        identifier = post["post"].strip()
        if not re.fullmatch(re.escape(channel) + r"/\d+", identifier, re.I):
            continue
        date_text = post["date"]
        try:
            published = datetime.fromisoformat(date_text.replace("Z", "+00:00"))
            if published.tzinfo is None:
                published = published.replace(tzinfo=timezone.utc)
            published = published.astimezone(timezone.utc)
        except (ValueError, TypeError):
            continue
        if published > now + timedelta(minutes=10):
            continue
        text = unescape(post["text"]).replace("\xa0", " ")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n+", "\n", text).strip()
        if not text:
            continue  # image/video-only posts cannot be summarized reliably
        first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
        title = first_line[:180].strip()
        if len(title) < 12:
            title = re.sub(r"\s+", " ", text)[:180].strip()
        if len(title) < 12:
            continue
        link = "https://t.me/" + identifier
        uid = "tg" + hashlib.sha256(link.encode()).hexdigest()[:18]
        items[uid] = {
            "id": uid,
            "category": category,
            "title": title,
            "summary": text[:600],
            "source": name,
            "url": link,
            "date": published.strftime("%d.%m.%Y"),
            "published_at": published.isoformat(),
        }
    if not items:
        raise RuntimeError("Channel preview contains no dated text posts")
    return list(items.values())

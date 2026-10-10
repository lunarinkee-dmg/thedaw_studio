"""Collect recent culture news from user-managed sources.json.

RSS/Atom feeds are discovered automatically; sites without accessible feeds are
reported in Actions logs and are not silently replaced by unrelated sources.
"""
import json
import re
import hashlib
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from html import unescape

OUT = Path(__file__).resolve().parents[1] / "news.json"
SOURCES_FILE = Path(__file__).resolve().parents[1] / "sources.json"

def load_sources():
    """Read the user-maintained source list; start empty until sources are added."""
    if not SOURCES_FILE.exists():
        return []
    data = json.loads(SOURCES_FILE.read_text(encoding="utf-8"))
    return [[s.get("name") or urllib.parse.urlparse(s["url"]).netloc, s.get("category", "Другое"), s["url"], s.get("feed", "")] for s in data if s.get("enabled", True) and s.get("url", "").startswith(("https://", "http://"))]

SOURCES = load_sources()
NOW = datetime.now(timezone.utc)
ATOM = "{http://www.w3.org/2005/Atom}"
CONTENT = "{http://purl.org/rss/1.0/modules/content/}"
USER_AGENT = "Mozilla/5.0 (compatible; theDAWStudio/0.4; news aggregator)"

def clean(value):
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", value or ""))).strip()

def parse_date(value):
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).astimezone(timezone.utc)
    except Exception:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)
        except Exception:
            return None

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, text/html;q=0.8"})
    with urllib.request.urlopen(req, timeout=9) as response:
        return response.read(2_000_000), response.geturl()

def feed_candidates(site, explicit):
    candidates = [explicit] if explicit else []
    # Homepage discovery avoids guessing a feed path for every publisher.
    try:
        body, final_url = fetch(site)
        head = body[:180_000].decode("utf-8", "ignore")
        for tag in re.findall(r"<link\b[^>]*>", head, flags=re.I):
            if re.search(r"type\s*=\s*[\x22\x27]application/(?:rss|atom)\+xml", tag, re.I):
                match = re.search(r"href\s*=\s*[\x22\x27]([^\x22\x27]+)", tag, re.I)
                if match:
                    candidates.append(urllib.parse.urljoin(final_url, unescape(match.group(1))))
    except Exception:
        pass
    root = site.rstrip("/")
    candidates.extend([root + "/feed/", root + "/rss", root + "/rss.xml"])
    return list(dict.fromkeys(candidates))

def entry_value(entry, *tags):
    for tag in tags:
        node = entry.find(tag)
        if node is not None:
            if tag.endswith("link") and node.attrib.get("href"):
                return node.attrib["href"]
            if node.text:
                return node.text.strip()
    return ""

def collect(source):
    name, category, site, explicit = source
    errors = []
    for feed in feed_candidates(site, explicit):
        try:
            body, feed_url = fetch(feed)
            root = ET.fromstring(body)
            entries = root.findall(".//item") or root.findall(ATOM + "entry")
            if not entries:
                errors.append(feed + ": no entries")
                continue
            output = []
            for entry in entries[:45]:
                title = clean(entry_value(entry, "title", ATOM + "title"))
                link = entry_value(entry, "link", ATOM + "link")
                published = parse_date(entry_value(entry, "pubDate", "date", ATOM + "published", ATOM + "updated", "{http://purl.org/dc/elements/1.1/}date"))
                if not title or not link or not published or not NOW - timedelta(hours=48) <= published <= NOW + timedelta(minutes=10):
                    continue
                if re.search(r"\b(russia|russian|moscow|kremlin)\b|росси[яий]|москв", title, re.I):
                    continue
                link = urllib.parse.urljoin(feed_url, link)
                summary = clean(entry_value(entry, "description", ATOM + "summary", CONTENT + "encoded"))[:350]
                uid = "rss" + hashlib.sha256(link.encode()).hexdigest()[:16]
                output.append({
                    "id": uid, "category": category, "title": title,
                    "summary": summary or "Откройте первоисточник, чтобы прочитать подробности.",
                    "source": name, "url": link, "date": published.strftime("%d.%m.%Y"),
                    "published_at": published.isoformat()
                })
            return name, output, None
        except Exception as exc:
            errors.append(str(exc)[:90])
    return name, [], "; ".join(errors[-2:]) or "Feed unavailable"

def main():
    previous = []
    if OUT.exists():
        try:
            previous = json.loads(OUT.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            pass
    previous_by_id = {item["id"]: item for item in previous if isinstance(item, dict) and "id" in item}
    items = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(collect, source) for source in SOURCES]
        for future in as_completed(futures):
            name, news, error = future.result()
            print(name + ": " + (str(len(news)) + " recent items" if error is None else "feed unavailable: " + error), flush=True)
            for item in news:
                items[item["id"]] = item
    # Preserve recent items if a publisher's feed is temporarily unavailable.
    for uid, item in previous_by_id.items():
        published = parse_date(item.get("published_at", ""))
        if published and published >= NOW - timedelta(hours=48) and uid not in items:
            items[uid] = {key: value for key, value in item.items() if key not in ("title_ru", "summary_ru")}
    fresh = sorted(items.values(), key=lambda item: item["published_at"], reverse=True)
    OUT.write_text(json.dumps(fresh[:150], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Saved", len(fresh[:150]), "articles from", len(SOURCES), "configured sources")

if __name__ == "__main__":
    main()

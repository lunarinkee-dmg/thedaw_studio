import json, re, hashlib, urllib.request, xml.etree.ElementTree as ET
import time, urllib.parse
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from html import unescape

OUT = Path(__file__).resolve().parents[1] / "news.json"
FEEDS = [
    ("The Astana Times", "Казахстан / ЦА", "https://astanatimes.com/feed/"),
    ("The Steppe", "Казахстан / ЦА", "https://the-steppe.com/feed"),
    ("Billboard", "Музыка", "https://www.billboard.com/feed/"),
    ("Pitchfork", "Музыка", "https://pitchfork.com/feed/rss"),
    ("Variety", "Кино / сериалы", "https://variety.com/feed/"),
    ("ARTnews", "Искусство", "https://www.artnews.com/feed/"),
]
now = datetime.now(timezone.utc)
def translate_text(text):
    if not text.strip() or not re.search(r"[A-Za-z]", text):
        return text
    errors = []
    # Primary free translator. It may rate-limit automated GitHub runners.
    params = urllib.parse.urlencode({
        "client": "gtx", "sl": "auto", "tl": "ru", "dt": "t", "q": text
    })
    try:
        req = urllib.request.Request(
            "https://translate.googleapis.com/translate_a/single?" + params,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=12) as res:
            payload = json.load(res)
        translated = "".join(chunk[0] or "" for chunk in payload[0] if chunk).strip()
        if translated:
            return translated
        errors.append("Google returned an empty translation")
    except Exception as exc:
        errors.append("Google: " + str(exc)[:90])
    # Backup free translator. Limit each request to 450 characters.
    try:
        chunks = [text[i:i+450] for i in range(0, len(text), 450)]
        results = []
        for chunk in chunks:
            params = urllib.parse.urlencode({
                "q": chunk, "langpair": "en|ru"
            })
            req = urllib.request.Request(
                "https://api.mymemory.translated.net/get?" + params,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=12) as res:
                payload = json.load(res)
            if int(payload.get("responseStatus", 0)) != 200:
                raise ValueError(str(payload.get("responseDetails", "Translation rejected")))
            result = (payload.get("responseData") or {}).get("translatedText", "").strip()
            if not result:
                raise ValueError("Empty MyMemory response")
            results.append(unescape(result))
        return " ".join(results)
    except Exception as exc:
        errors.append("MyMemory: " + str(exc)[:90])
    raise RuntimeError("; ".join(errors))

def translate_ru(title, summary):
    return {"title_ru": translate_text(title), "summary_ru": translate_text(summary)}

old = []
if OUT.exists():
    try: old = json.loads(OUT.read_text(encoding="utf-8"))
    except Exception: pass
items = {x["id"]: x for x in old if isinstance(x, dict) and "id" in x}
old_by_id = dict(items)
def clean(s):
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()
def parse_date(s):
    try: return parsedate_to_datetime(s).astimezone(timezone.utc)
    except Exception:
        try: return datetime.fromisoformat(s.replace("Z","+00:00")).astimezone(timezone.utc)
        except Exception: return None
for source, category, feed in FEEDS:
    try:
        req = urllib.request.Request(feed, headers={"User-Agent":"Mozilla/5.0 theDAWStudio/0.2"})
        with urllib.request.urlopen(req, timeout=18) as res:
            body = res.read(2_000_000)
        xml = ET.fromstring(body)
        entries = xml.findall(".//item")
        if not entries:
            entries = xml.findall("{http://www.w3.org/2005/Atom}entry")
        added = 0
        for e in entries[:40]:
            def value(*names):
                for name in names:
                    n=e.find(name)
                    if n is not None:
                        if name.endswith("link") and n.attrib.get("href"): return n.attrib["href"]
                        if n.text: return n.text.strip()
                return ""
            title=clean(value("title","{http://www.w3.org/2005/Atom}title"))
            url=value("link","{http://www.w3.org/2005/Atom}link")
            published=parse_date(value("pubDate","{http://www.w3.org/2005/Atom}published","{http://www.w3.org/2005/Atom}updated"))
            if not title or not url or not published or not now-timedelta(hours=24) <= published <= now+timedelta(minutes=10): continue
            if re.search(r"\b(russia|russian|moscow|kremlin)\b|росси[яий]|москв",title,re.I): continue
            summary=clean(value("description","{http://www.w3.org/2005/Atom}summary"))[:350]
            uid="rss"+hashlib.sha256(url.encode()).hexdigest()[:16]
            items[uid]={"id":uid,"category":category,"title":title,"summary":summary or "Откройте первоисточник, чтобы прочитать подробности.","source":source,"url":url,"date":published.strftime("%d.%m.%Y"),"published_at":published.isoformat()}
            if uid in old_by_id:
                for key in ("title_ru", "summary_ru"):
                    if old_by_id[uid].get(key): items[uid][key] = old_by_id[uid][key]
            added+=1
        print(source, "new/current entries:", added)
    except Exception as ex:
        print(source, "unavailable:", str(ex)[:180])
fresh=[x for x in items.values() if (parse_date(x.get("published_at","")) or datetime(2000,1,1,tzinfo=timezone.utc)) >= now-timedelta(hours=24)]
fresh.sort(key=lambda x:x["published_at"],reverse=True)
pending = [x for x in fresh if not x.get("title_ru") or not x.get("summary_ru")]
print("News requiring Russian translation:", len(pending))
translated_count = 0
for item in pending[:35]:
    try:
        # Keep successfully translated fields even if the other request fails.
        if not item.get("title_ru"):
            item["title_ru"] = translate_text(item["title"])
        if not item.get("summary_ru"):
            item["summary_ru"] = translate_text(item["summary"])
        if item.get("title_ru") and item.get("summary_ru"):
            translated_count += 1
    except Exception as exc:
        print("Free translation unavailable:", item["id"], str(exc)[:140])
    time.sleep(0.45)
print("Fully translated in this run:", translated_count)
OUT.write_text(json.dumps(fresh[:150],ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("Saved",len(fresh),"articles")

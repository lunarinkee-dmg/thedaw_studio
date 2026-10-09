import json, re, hashlib, urllib.request, xml.etree.ElementTree as ET
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
old = []
if OUT.exists():
    try: old = json.loads(OUT.read_text(encoding="utf-8"))
    except Exception: pass
items = {x["id"]: x for x in old if isinstance(x, dict) and "id" in x}
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
            added+=1
        print(source, "new/current entries:", added)
    except Exception as ex:
        print(source, "unavailable:", str(ex)[:180])
fresh=[x for x in items.values() if (parse_date(x.get("published_at","")) or datetime(2000,1,1,tzinfo=timezone.utc)) >= now-timedelta(hours=24)]
fresh.sort(key=lambda x:x["published_at"],reverse=True)
OUT.write_text(json.dumps(fresh[:150],ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("Saved",len(fresh),"articles")

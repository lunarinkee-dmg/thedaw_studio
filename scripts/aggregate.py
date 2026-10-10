import json, re, hashlib, urllib.request, xml.etree.ElementTree as ET
import os, time
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
TRANSLATE_KEY = os.getenv("OPENAI_API_KEY", "").strip()
def translate_ru(title, summary):
    if not TRANSLATE_KEY:
        return None
    payload = json.dumps({
        "model": "gpt-4o-mini",
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "Translate news title and summary into fluent, factual Russian. Preserve names, numbers, dates and meaning. Do not add information. Respond ONLY with JSON keys title_ru and summary_ru."},
            {"role": "user", "content": json.dumps({"title": title, "summary": summary}, ensure_ascii=False)}
        ]
    }).encode("utf-8")
    req = urllib.request.Request("https://api.openai.com/v1/chat/completions", data=payload,
        headers={"Authorization": "Bearer " + TRANSLATE_KEY, "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as res:
        answer = json.load(res)
    obj = json.loads(answer["choices"][0]["message"]["content"])
    if not isinstance(obj.get("title_ru"), str) or not isinstance(obj.get("summary_ru"), str):
        raise ValueError("Invalid translation")
    return {"title_ru": obj["title_ru"].strip(), "summary_ru": obj["summary_ru"].strip()}

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
if TRANSLATE_KEY:
    pending = [x for x in fresh if not x.get("title_ru") or not x.get("summary_ru")]
    for item in pending[:60]:
        try:
            translation = translate_ru(item["title"], item["summary"])
            if translation: item.update(translation)
        except Exception as exc:
            print("Translation unavailable:", item["id"], str(exc)[:140])
        time.sleep(0.15)
else:
    print("OPENAI_API_KEY is not configured; untranslated originals will be shown.")
OUT.write_text(json.dumps(fresh[:150],ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("Saved",len(fresh),"articles")

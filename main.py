import os, json, re, html, hashlib, time
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import xml.etree.ElementTree as ET

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHANNEL_ID = os.environ["TELEGRAM_CHANNEL_ID"]
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
STATE_FILE = "state.json"
MAX_AGE_HOURS = int(os.getenv("MAX_AGE_HOURS", "72"))

def fetch(url):
    req = Request(url, headers={"User-Agent": "DailyTechBD/1.0 (+RSS reader)"})
    with urlopen(req, timeout=25) as r:
        return r.read()

def clean(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    return re.sub(r"\s+", " ", html.unescape(s)).strip()

def parse_date(value):
    if not value:
        return None
    try:
        dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None

def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {"posted": []}
    except (FileNotFoundError, json.JSONDecodeError):
        return {"posted": []}

def save_state(state):
    state["posted"] = state.get("posted", [])[-1000:]
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def read_feed(feed):
    try:
        root = ET.fromstring(fetch(feed["url"]))
        entries = []
        # RSS 2.0
        for item in root.findall(".//item"):
            title = clean(item.findtext("title"))
            link = clean(item.findtext("link"))
            desc = clean(item.findtext("description"))
            date = parse_date(item.findtext("pubDate"))
            guid = clean(item.findtext("guid")) or link or title
            if title and link:
                entries.append({"title": title, "link": link, "summary": desc,
                                "date": date, "source": feed["name"], "id": guid})
        # Atom
        ns = {"a": "http://www.w3.org/2005/Atom"}
        for item in root.findall(".//a:entry", ns):
            title = clean(item.findtext("a:title", default="", namespaces=ns))
            link_el = item.find("a:link", ns)
            link = link_el.attrib.get("href", "") if link_el is not None else ""
            desc = clean(item.findtext("a:summary", default="", namespaces=ns) or
                         item.findtext("a:content", default="", namespaces=ns))
            date = parse_date(item.findtext("a:published", default="", namespaces=ns) or
                              item.findtext("a:updated", default="", namespaces=ns))
            guid = item.findtext("a:id", default="", namespaces=ns) or link or title
            if title and link:
                entries.append({"title": title, "link": link, "summary": desc,
                                "date": date, "source": feed["name"], "id": guid})
        return entries
    except Exception as e:
        print(f"Feed failed: {feed['name']}: {e}")
        return []

def ai_rewrite(article):
    if not GEMINI_API_KEY:
        return None
    prompt = f"""Write a concise, accurate bilingual Telegram tech-news post from the source material below.
Do not invent facts, numbers, quotes, dates or claims. If details are missing, omit them.
Output ONLY valid JSON with keys: headline_bn, headline_en, summary_bn, summary_en, takeaway.
Bangla should be natural and easy to read. English should be concise.
Use 2-3 short sentences per summary. Make it engaging but not clickbait.
Source: {article['source']}
Title: {article['title']}
Description: {article['summary'][:2500]}
URL: {article['link']}"""
    payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}],
                          "generationConfig": {"temperature": 0.35, "responseMimeType": "application/json"}}).encode()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    req = Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(req, timeout=40) as r:
            data = json.loads(r.read().decode())
        raw = data["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(raw)
    except Exception as e:
        print(f"Gemini unavailable; using source summary: {e}")
        return None

def make_post(article):
    ai = ai_rewrite(article)
    if ai:
        fields = ["headline_bn", "headline_en", "summary_bn", "summary_en", "takeaway"]
        for key in fields:
            ai[key] = clean(str(ai.get(key, "")))
        bn_title = ai["headline_bn"] or article["title"]
        en_title = ai["headline_en"] or article["title"]
        bn = ai["summary_bn"] or article["summary"][:450]
        en = ai["summary_en"]
        takeaway = ai["takeaway"]
    else:
        bn_title = article["title"]
        en_title = article["title"]
        bn = "এই বিষয়ে নতুন আপডেট প্রকাশিত হয়েছে। বিস্তারিত জানতে মূল সোর্সটি দেখুন।"
        en = article["summary"][:500] or "Read the original report for the full details."
        takeaway = "মূল প্রতিবেদনের তথ্য যাচাই করে দেখুন।"

    def esc(s): return html.escape(s or "")
    date_txt = article["date"].strftime("%d %b %Y, %H:%M UTC") if article["date"] else "Latest update"
    text = (
        "🚀 <b>DAILY TECH BD | TECH UPDATE</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🔥 <b>{esc(bn_title)}</b>\n"
        f"<b>EN:</b> {esc(en_title)}\n\n"
        f"🇧🇩 <b>বাংলা আপডেট</b>\n{esc(bn)}\n\n"
        f"🌍 <b>ENGLISH UPDATE</b>\n{esc(en)}\n\n"
        f"💡 <b>কেন গুরুত্বপূর্ণ?</b>\n{esc(takeaway)}\n\n"
        f"📰 <b>Source:</b> {esc(article['source'])}\n"
        f"🕒 <i>{esc(date_txt)}</i>\n"
        f'🔗 <a href="{esc(article["link"])}">Read full story</a>\n\n'
        "━━━━━━━━━━━━━━━━━━\n"
        "#DailyTechBD #TechNews #Technology #AI"
    )
    return text[:4000]

def telegram_send(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    body = json.dumps({"chat_id": CHANNEL_ID, "text": text, "parse_mode": "HTML",
                       "disable_web_page_preview": False}).encode()
    req = Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(req, timeout=30) as r:
        result = json.loads(r.read().decode())
    if not result.get("ok"):
        raise RuntimeError(result.get("description", "Telegram API error"))
    return result

def main():
    with open("feeds.json", encoding="utf-8") as f:
        feeds = json.load(f)
    state = load_state()
    posted = set(state.get("posted", []))
    all_items = []
    for feed in feeds:
        all_items.extend(read_feed(feed))

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=MAX_AGE_HOURS)
    unique = {}
    for a in all_items:
        key = hashlib.sha256((a["link"] or a["id"]).encode()).hexdigest()
        a["key"] = key
        if key in posted:
            continue
        if a["date"] and a["date"] < cutoff:
            continue
        unique[key] = a

    candidates = sorted(unique.values(),
                        key=lambda x: x["date"] or datetime(2000, 1, 1, tzinfo=timezone.utc),
                        reverse=True)
    if not candidates:
        print("No fresh, unposted articles found. Nothing posted this run.")
        return

    article = candidates[0]
    message = make_post(article)
    telegram_send(message)
    posted.add(article["key"])
    state["posted"] = list(posted)
    state["last_posted_utc"] = now.isoformat()
    save_state(state)
    print(f"Published: {article['title']} ({article['source']})")

if __name__ == "__main__":
    main()

import os, json, re, html, hashlib, logging, csv
from pathlib import Path
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, urlencode, urlunparse, parse_qsl
import requests, feedparser
from PIL import Image, ImageDraw, ImageFont

BASE=Path(__file__).parent
DATA=BASE/"data"; DATA.mkdir(exist_ok=True)
STATE=BASE/"state.json"; POSTS=DATA/"posts.json"; ANALYTICS=DATA/"analytics.json"
CONFIG=json.loads((BASE/"config.json").read_text(encoding="utf-8"))
FEEDS=json.loads((BASE/"feeds.json").read_text(encoding="utf-8"))
TOKEN=os.getenv("TELEGRAM_BOT_TOKEN","").strip()
CHANNEL=os.getenv("TELEGRAM_CHANNEL_ID","").strip()
GEMINI=os.getenv("GEMINI_API_KEY","").strip()
MODEL=os.getenv("GEMINI_MODEL",CONFIG.get("gemini_model","gemini-2.5-flash"))
AFFILIATE_LINKS=json.loads((BASE/"affiliate_links.json").read_text(encoding="utf-8"))
SPONSORS=json.loads((BASE/"sponsors.json").read_text(encoding="utf-8"))
logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(message)s")
log=logging.getLogger("vipeaim")

def readj(p,d):
    try: return json.loads(p.read_text(encoding="utf-8"))
    except Exception: return d
def writej(p,o): p.write_text(json.dumps(o,ensure_ascii=False,indent=2),encoding="utf-8")
def clean(s):
    return re.sub(r"\s+"," ",html.unescape(re.sub(r"<[^>]+>"," ",str(s or "")))).strip()
def pubdate(e):
    try: return datetime(*e.published_parsed[:6],tzinfo=timezone.utc)
    except Exception: return datetime.now(timezone.utc)
def image_of(e):
    for k in ("media_content","media_thumbnail"):
        a=e.get(k) or []
        if a and a[0].get("url"): return a[0]["url"]
    for l in e.get("links",[]):
        if l.get("rel")=="enclosure" and l.get("type","").startswith("image/"): return l.get("href","")
    for c in e.get("content",[]):
        m=re.search(r"<img[^>]+src=[\"']([^\"']+)",c.get("value",""),re.I)
        if m: return m.group(1)
    return ""
def fetch():
    out=[]; cutoff=datetime.now(timezone.utc)-timedelta(hours=int(CONFIG.get("max_age_hours",72)))
    for f in FEEDS:
        try:
            feed=feedparser.parse(f["url"])
            for e in feed.entries[:40]:
                title=clean(e.get("title")); link=e.get("link","")
                if not title or not link: continue
                dt=pubdate(e)
                if dt<cutoff: continue
                out.append({"id":hashlib.sha256(link.encode()).hexdigest(),"title":title,"link":link,
                  "summary":clean(e.get("summary",""))[:1200],"source":f.get("source",urlparse(link).netloc),
                  "category":f.get("category","Technology"),"published":dt.isoformat(),"image":image_of(e)})
        except Exception as ex: log.warning("Feed error %s: %s",f.get("url"),ex)
    return sorted(out,key=lambda x:x["published"],reverse=True)
def make_copy(x):
    fallback_bn=f"{x['title']} — এ বিষয়ে নতুন আপডেট প্রকাশিত হয়েছে। বিস্তারিত জানতে মূল প্রতিবেদনটি পড়ুন।"
    fallback_en=x["summary"] or x["title"]
    if not GEMINI: return {"headline_bn":x["title"],"summary_bn":fallback_bn,"summary_en":fallback_en[:450]}
    prompt=f"""Act as a careful bilingual Bangladesh news editor for vipeAIM.
Use ONLY the source facts below. Never invent facts, quotes, dates, cast, release dates or claims.
Return strict JSON keys headline_bn (catchy factual Bengali headline max 90 chars),
summary_bn (two concise Bengali sentences), summary_en (two concise English sentences).
Category: {x['category']}
Title: {x['title']}
Source summary: {x['summary']}
Source: {x['source']}
URL: {x['link']}"""
    try:
        u=f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={GEMINI}"
        r=requests.post(u,json={"contents":[{"parts":[{"text":prompt}]}],"generationConfig":{"temperature":0.3,"responseMimeType":"application/json"}},timeout=35)
        r.raise_for_status(); t=r.json()["candidates"][0]["content"]["parts"][0]["text"]
        o=json.loads(t[t.find("{"):t.rfind("}")+1])
        return {"headline_bn":clean(o.get("headline_bn"))[:110] or x["title"],
          "summary_bn":clean(o.get("summary_bn"))[:500] or fallback_bn,
          "summary_en":clean(o.get("summary_en"))[:500] or fallback_en[:450]}
    except Exception as ex:
        log.warning("Gemini fallback: %s",ex)
        return {"headline_bn":x["title"],"summary_bn":fallback_bn,"summary_en":fallback_en[:450]}
def font(size,bold=False):
    names=["NotoSansBengali-Bold.ttf" if bold else "NotoSansBengali-Regular.ttf","NotoSansBengali.ttf"]
    for n in names:
        p=BASE/"assets"/n
        if p.exists():
            try: return ImageFont.truetype(str(p),size)
            except Exception: pass
    try:
        u="https://raw.githubusercontent.com/google/fonts/main/ofl/notosansbengali/NotoSansBengali%5Bwght%5D.ttf"
        r=requests.get(u,timeout=20); r.raise_for_status()
        p=BASE/"assets"/"NotoSansBengali.ttf"; p.write_bytes(r.content)
        return ImageFont.truetype(str(p),size)
    except Exception: return ImageFont.load_default()
def thumbnail(head,cat,pid):
    colors={"Technology":((7,18,43),(20,100,165),(65,225,215)),"Movies":((30,8,30),(145,35,75),(255,175,95)),
    "Series":((15,12,38),(80,45,150),(220,125,255)),"Gaming":((5,28,24),(20,130,95),(120,255,170)),
    "Anime":((30,12,45),(150,60,130),(255,180,220)),"Entertainment":((30,18,8),(150,75,25),(255,205,100)),
    "Science":((5,22,48),(30,90,160),(110,210,255))}
    a,b,accent=colors.get(cat,colors["Technology"]); W,H=1280,720
    im=Image.new("RGB",(W,H)); px=im.load()
    for y in range(H):
        t=y/H; c=tuple(int(a[i]*(1-t)+b[i]*t) for i in range(3))
        for xx in range(W): px[xx,y]=c
    d=ImageDraw.Draw(im,"RGBA")
    d.ellipse((830,-230,1450,390),fill=(*accent,35)); d.ellipse((-250,470,430,1150),fill=(*accent,25))
    d.rounded_rectangle((48,45,1232,675),radius=42,outline=(*accent,190),width=4)
    d.rounded_rectangle((82,80,390,150),radius=18,fill=(*accent,225))
    d.text((105,95),"vipeAIM  •  "+cat.upper(),font=font(29,True),fill=(8,15,28))
    f=font(65,True); words=head.split(); lines=[]; line=""
    for w in words:
        test=(line+" "+w).strip()
        if d.textbbox((0,0),test,font=f)[2]>1080 and line: lines.append(line); line=w
        else: line=test
    if line: lines.append(line)
    y=205
    for ln in lines[:4]:
        d.text((100,y),ln,font=f,fill="white",stroke_width=2,stroke_fill=(0,0,0,120)); y+=94
    d.text((100,590),"বাংলা + ENGLISH UPDATE  |  READ • LEARN • DISCOVER",font=font(25),fill=(230,240,255))
    p=DATA/f"thumb_{pid[:12]}.jpg"; im.save(p,quality=91,optimize=True); return p
def tracked(url,pid):
    u=urlparse(url); q=dict(parse_qsl(u.query))
    q.update({"utm_source":"vipeaim_telegram","utm_medium":"telegram","utm_campaign":"daily_news","utm_content":pid[:12]})
    return urlunparse(u._replace(query=urlencode(q)))
def send(x,c,thumb):
    if not TOKEN or not CHANNEL: raise RuntimeError("Missing TELEGRAM_BOT_TOKEN / TELEGRAM_CHANNEL_ID GitHub secrets.")
    link=tracked(x["link"],x["id"])
    affiliate=next((a for a in AFFILIATE_LINKS if a.get("enabled") and a.get("url") and
                    a.get("url")!="ADD_APPROVED_AFFILIATE_URL" and a.get("category") in (x["category"],"All")),None)
    sponsor=next((sp for sp in SPONSORS if sp.get("enabled") and sp.get("url") and
                  sp.get("url")!="https://example.com"),None)
    buttons=[]
    cap=(f"<b>🌐 vipeAIM | {html.escape(x['category'].upper())}</b>\n\n"
      f"<b>{html.escape(c['headline_bn'])}</b>\n\n🇧🇩 <b>বাংলা আপডেট</b>\n{html.escape(c['summary_bn'])}\n\n"
      f"🇬🇧 <b>ENGLISH UPDATE</b>\n{html.escape(c['summary_en'])}\n\n"
      f"📰 Source: {html.escape(x['source'])}\n🔗 <a href=\"{html.escape(link,quote=True)}\">সম্পূর্ণ খবর পড়ুন | Read full story</a>")
    if sponsor:
        cap += f"\n\n📢 <b>স্পন্সরড | Sponsored</b>\n{html.escape(sponsor.get('label',sponsor.get('name','Partner')))}"
        buttons.append([{"text":"Sponsored • বিস্তারিত","url":tracked(sponsor["url"],x["id"]+"s")}])
    if affiliate:
        cap += "\n\n🛍 <b>Affiliate recommendation</b>\nএই লিংক থেকে কেনাকাটা করলে vipeAIM কমিশন পেতে পারে।"
        buttons.append([{"text":affiliate.get("label","Recommended product"),"url":tracked(affiliate["url"],x["id"]+"a")}])
    cap += f"\n\n<i>#vipeAIM #TechNews #{re.sub('[^A-Za-z0-9]','',x['category'])}</i>"
    if len(cap)>1000: cap=cap[:900]+"\n\n<a href=\""+html.escape(link,quote=True)+"\">Read full story</a>"
    payload={"chat_id":CHANNEL,"caption":cap,"parse_mode":"HTML"}
    if buttons: payload["reply_markup"]=json.dumps({"inline_keyboard":buttons},ensure_ascii=False)
    with open(thumb,"rb") as f:
        r=requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
          data=payload,files={"photo":("vipeaim.jpg",f,"image/jpeg")},timeout=45)
    r.raise_for_status(); j=r.json()
    if not j.get("ok"): raise RuntimeError(str(j))
    return j["result"]["message_id"]
def update(x,c,msg):
    posts=readj(POSTS,[])
    rec={"id":x["id"],"category":x["category"],"headline_bn":c["headline_bn"],"summary_bn":c["summary_bn"],
      "summary_en":c["summary_en"],"source":x["source"],"url":x["link"],
      "published":datetime.now(timezone.utc).isoformat(),"telegram_message_id":msg}
    posts.insert(0,rec); posts=posts[:250]; writej(POSTS,posts)
    a=readj(ANALYTICS,{"total_posts":0,"by_category":{},"last_post":None,"sponsor_posts":0,"affiliate_clicks":None})
    a["total_posts"]=int(a.get("total_posts",0))+1; a.setdefault("by_category",{})
    a["by_category"][x["category"]]=a["by_category"].get(x["category"],0)+1
    a["last_post"]=rec["published"]; writej(ANALYTICS,a)
    mirror=BASE/"website"/"data"; mirror.mkdir(parents=True,exist_ok=True)
    writej(mirror/"posts.json",posts); writej(mirror/"analytics.json",a)
    cp=DATA/"publication_log.csv"; fresh=not cp.exists()
    with cp.open("a",encoding="utf-8",newline="") as f:
        w=csv.writer(f)
        if fresh: w.writerow(["published_utc","category","headline_bn","source","url","telegram_message_id","post_id"])
        w.writerow([rec["published"],x["category"],c["headline_bn"],x["source"],x["link"],msg,x["id"]])
def main():
    state=readj(STATE,{"posted_ids":[]}); posted=set(state.get("posted_ids",[]))
    fresh=[x for x in fetch() if x["id"] not in posted]
    if not fresh: log.warning("No fresh unseen feed item; skipped this slot."); return
    x=fresh[0]; c=make_copy(x); thumb=thumbnail(c["headline_bn"],x["category"],x["id"])
    msg=send(x,c,thumb); posted.add(x["id"])
    state["posted_ids"]=list(posted)[-2000:]; state["last_posted_utc"]=datetime.now(timezone.utc).isoformat()
    writej(STATE,state); update(x,c,msg)
    log.info("Published %s (%s), Telegram message %s",c["headline_bn"],x["category"],msg)
if __name__=="__main__": main()

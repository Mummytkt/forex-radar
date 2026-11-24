"""
AI releases and market-moving news for the owner (owner request 2026-11-24). An addition to the Morning Brief:
nothing in the brief's own news changes.

  • 🤖 AI: what's new — real releases only (a new model, product or open-source drop), not funding rounds,
    opinion pieces or tutorials. A copy box asks the Claude app what it does, who it helps, how to use it, its
    speed and accuracy, and how it moves the industry, plus a ready post tying it to design, QA, sales & support, AI.
  • 📈 Your markets — the news that moves her instruments (EURUSD, XAUUSD, GER40, NAS100, USOIL, JPN225, BTCUSD,
    ETHUSD), each tagged with what it touches, today's calendar link, and a copy box asking which side each
    instrument likely leans and why: a fundamental lean to sit beside her technical read, never a signal.
  • Market alerts through the day — a high-impact story (rate decision, CPI, payrolls, OPEC, tariffs, war, crypto
    ETF...) on the main Bias Pointer bot within ~15 minutes, each once, at most 8 a day, 06:00–22:30 WAT.

Free RSS feeds only, like the brief; the explaining is done in the Claude app with the owner's subscription.
"""

from __future__ import annotations

import logging
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional

from alerts.morning_brief import _e, _strip, fetch_all, WAT

logger = logging.getLogger(__name__)

AI_FEEDS = (
    ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("OpenAI", "https://openai.com/news/rss.xml"),
    ("Google AI", "https://blog.google/technology/ai/rss/"),
    ("Hugging Face", "https://huggingface.co/blog/feed.xml"),
)
MARKET_FEEDS = (
    ("FXStreet", "https://www.fxstreet.com/rss/news"),
    ("InvestingLive", "https://investinglive.com/feed/news"),
    ("CNBC Markets", "https://www.cnbc.com/id/10000664/device/rss/rss.html"),
    ("Investing.com", "https://www.investing.com/rss/news_1.rss"),
    ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
)
CALENDAR = "https://www.forexfactory.com/calendar?day=today"

# ── AI: a release, not chatter ───────────────────────────────────────────────────────────────────────────
AI_RELEASE = r"\blaunch|\breleas|\bunveil|\bintroduc|\brolls? out|\brolling out|now available|\bdebut|\bships?\b|" \
             r"open[- ]sourc|open[- ]weight|new model|\bannounc|\bpreview\b|general availability|\bupgrade"
AI_NAMES = r"\bgpt|chatgpt|openai|\bclaude\b|anthropic|gemini|deepmind|\bllama|meta ai|mistral|deepseek|\bqwen|" \
           r"\bgrok\b|\bxai\b|copilot|microsoft|nvidia|apple intelligence|\bsora\b|\bveo\b|midjourney|perplexity|" \
           r"\bagents?\b|hugging face|stability ai|runway|cursor"
AI_DETAIL = r"\bmodel|benchmark|faster|speed|accura|reasoning|coding|multimodal|voice|image|video|\bapi\b|" \
            r"developer|context window|latency|cheaper|price"
AI_SKIP = r"raises \$|\braises\b.*(million|billion)|funding|valuation|lawsuit|\bsues?\b|podcast|webinar|" \
          r"how to|tutorial|\bguide\b|fine-?tun|hiring|layoffs?|opinion|newsletter|this week in|recap|event\b"


def ai_score(item: dict) -> int:
    title = item["title"].lower()
    text = f"{title} {item['summary']}".lower()
    if re.search(AI_SKIP, title):
        return 0
    s = 3 * bool(re.search(AI_RELEASE, title)) + 2 * len(set(re.findall(AI_NAMES, text)))
    s += min(3, len(set(re.findall(AI_DETAIL, text))))
    return s if re.search(AI_RELEASE, text) else 0          # no release, no place here


def _top(items: list[dict], n: int, now: datetime, hours: int, scorer, min_score: int) -> list[dict]:
    fresh = [i for i in items if i["published"] is None or now - i["published"] <= timedelta(hours=hours)]
    ranked = sorted(((scorer(i), i) for i in fresh), key=lambda t: (-t[0], -(t[1]["published"] or now).timestamp()))
    out, seen = [], []
    for s, i in ranked:
        if s < min_score:
            break
        words = set(re.findall(r"[a-z]{4,}", i["title"].lower()))
        if any(len(words & w) >= 3 for w in seen):
            continue                                          # the same story from another source
        out.append(i)
        seen.append(words)
        if len(out) == n:
            break
    return out


def ai_pick(items: list[dict], n: int, now: datetime) -> list[dict]:
    return _top(items, n, now, 48, ai_score, 6)


# ── Markets: which of her instruments a story touches, and how hard ─────────────────────────────────────
_USD = r"\bfed\b|federal reserve|\bfomc\b|powell|us dollar|greenback|\bdxy\b|treasur|\bus (cpi|inflation|jobs|payrolls|gdp|economy)|" \
       r"nonfarm|payrolls|jobless claims|\bpce\b|white house|trump"
INSTRUMENTS = {
    "EURUSD": r"\becb\b|lagarde|\beuro\b|eurozone|euro area|eur/usd|eurusd|" + _USD,
    "XAUUSD": r"\bgold\b|bullion|xau|safe[- ]haven|geopolit|\bwar\b|missile|" + _USD,
    "GER40": r"\bdax\b|germany|german|\bbund|eurozone|\becb\b|european (stocks|shares|markets)|ger40",
    "NAS100": r"nasdaq|tech stocks|nvidia|\bapple\b|microsoft|alphabet|amazon|meta platforms|tesla|wall street|"
              r"s&p|\bus stocks|nas100|\bfed\b|fomc|powell",
    "USOIL": r"\boil\b|crude|\bopec|brent|\bwti\b|\biran|saudi|red sea|hormuz|refiner|gasoline|energy prices",
    "JPN225": r"nikkei|\bjapan|\bboj\b|bank of japan|\byen\b|ueda|tokyo stocks|jpn225",
    "BTCUSD": r"bitcoin|\bbtc\b|crypto|stablecoin|spot etf",
    "ETHUSD": r"\bether\b|ethereum|\beth\b|crypto|stablecoin",
}
HIGH_IMPACT = r"rate (decision|cut|hike)|cuts? rates|hikes? rates|holds? rates|interest rate|\bcpi\b|inflation|" \
              r"payrolls|nonfarm|jobs report|unemployment rate|\bgdp\b|recession|\bfomc\b|powell|lagarde|ueda|" \
              r"tariff|sanction|\bopec\+?|ceasefire|invasion|strikes? on|attack|escalat|default|downgrade|" \
              r"bank (failure|collapse)|etf (approval|inflows|outflows)|\bhack|emergency|intervention|shutdown|stimulus"
MEDIUM_IMPACT = r"earnings|guidance|surge|plunge|slump|rall(y|ies)|record high|tumble|soar|sell-?off|crash"
MARKET_SKIP = r"price prediction|forecast:|technical analysis|chart of the day|elliott wave|sponsored|podcast|" \
              r"\bwatch:|\blive:|horoscope|quiz"


def tags(item: dict) -> list[str]:
    text = f"{item['title']} {item['summary']}".lower()
    return [k for k, p in INSTRUMENTS.items() if re.search(p, text)]


def impact(item: dict) -> int:
    title = item["title"].lower()
    text = f"{title} {item['summary']}".lower()
    if re.search(MARKET_SKIP, title) or not tags(item):
        return 0
    found = lambda p: {m.group(0) for m in re.finditer(p, text)}     # whole matches (findall would give the groups)
    return 3 * len(found(HIGH_IMPACT)) + len(found(MEDIUM_IMPACT))


def market_pick(items: list[dict], n: int, now: datetime, hours: int = 24, min_impact: int = 3) -> list[dict]:
    return _top(items, n, now, hours, impact, min_impact)


# ── The words ─────────────────────────────────────────────────────────────────────────────────────────────
VOICE = ("in my voice: bubbly, gist-style banter with light Nigerian touches, one practical tip in the middle and "
         "a question at the end; I speak as an expert in my field, never as someone looking for a job; no hashtag spam")


def social_ask() -> str:
    """Added to the brief's own news box (owner 2026-11-24): its questions stay as they are."""
    return ("- At the end of each story: a ready social media post that ties it to my work (design, QA, sales & "
            f"support, or AI: whichever fits most naturally), {VOICE}")


def _line(i: dict, with_tags: bool = False) -> str:
    gist = i["summary"]
    gist = (gist[:170].rsplit(" ", 1)[0] + "…") if len(gist) > 170 else gist
    tg = f" <b>[{' · '.join(tags(i))}]</b>" if with_tags else ""
    g = f"\n<i>{_e(gist)}</i>" if gist and gist.lower() != i["title"].lower() else ""
    return f"• <a href=\"{_e(i['link'])}\">{_e(i['title'])}</a> ({_e(i['source'])}){tg}{g}"


def ai_prompt(stories: list[dict]) -> str:
    items = "\n".join(f"{n}. {i['title']}\n{i['link']}" for n, i in enumerate(stories, 1))
    return ("Open each link. For each AI release, explain in simple words:\n"
            "- What was released and what it does\n- Who it benefits most\n- How to use it (access, price, a first "
            "thing to try)\n- What it changes for speed and accuracy, with numbers if given\n- Any other impact worth "
            "knowing (cost, safety, jobs, limits)\n- How it moves the AI industry and who it puts pressure on\n"
            f"- Then a ready social media post relating it to design, QA, sales & support or AI, {VOICE}\n\n" + items)


def market_prompt(stories: list[dict]) -> str:
    items = "\n".join(f"{n}. {i['title']} [{', '.join(tags(i))}]\n{i['link']}" for n, i in enumerate(stories, 1))
    return ("Open each link. I trade EURUSD, XAUUSD, GER40, NAS100, USOIL, JPN225, BTCUSD and ETHUSD. For each story:\n"
            "- What happened, in one line\n- Which of my instruments it moves, and for each: likely stronger or weaker, "
            "and the chain (news → rates / risk mood / dollar → price)\n- How strong the effect usually is, and how "
            "long it tends to last\n- What would prove this lean wrong\n- The next data or event to watch\n"
            "End with a table: instrument | lean (stronger / weaker / neutral) | why in a few words. This is a "
            "fundamental lean to sit beside my technical analysis, not a trade signal.\n\n" + items)


def ai_text(ai: list[dict]) -> str:
    lines = ["🤖 <b>AI: what's new</b> (releases only)"]
    if not ai:
        return "\n".join(lines + ["• No big release in the last two days. Quiet is fine."])
    lines += [_line(i) for i in ai]
    lines += ["", "🧠 Tap to copy, then paste into the Claude app for the full breakdown + a post:",
              f"<code>{_e(ai_prompt(ai))}</code>"]
    return "\n".join(lines)


def market_text(mk: list[dict]) -> str:
    lines = ["📈 <b>Your markets</b> (EURUSD · XAUUSD · GER40 · NAS100 · USOIL · JPN225 · BTC · ETH)"]
    lines += [_line(i, True) for i in mk] or ["• No big market-moving story in the last 24 hours."]
    lines += [f"📅 <a href=\"{CALENDAR}\">Today's economic calendar</a> (red = high impact)"]
    if mk:
        lines += ["", "🧠 Tap to copy, then paste into the Claude app: which side each instrument leans, and why:",
                  f"<code>{_e(market_prompt(mk))}</code>"]
    return "\n".join(lines)


async def build_extras(now: Optional[datetime] = None) -> list[str]:
    """The two extra messages that follow the Morning Brief."""
    now = now or datetime.now(timezone.utc)
    ai = ai_pick(await fetch_all(AI_FEEDS), 3, now)
    mk = market_pick(await fetch_all(MARKET_FEEDS), 4, now)
    return [ai_text(ai), market_text(mk)]


# ── Through the day: high-impact market news on the main bot ─────────────────────────────────────────────
ALERT_MIN_IMPACT = 6          # two high-impact signs (e.g. "ECB" story about a "rate cut" and "inflation")
ALERT_MAX_PER_DAY = 8
ALERT_FRESH = timedelta(minutes=90)


def _ensure(conn) -> None:
    conn.execute("CREATE TABLE IF NOT EXISTS market_news_sent (link TEXT PRIMARY KEY, title TEXT, sent_at TEXT)")


def alert_text(i: dict) -> str:
    return "\n".join([f"📰 <b>Market news</b> · {' · '.join(tags(i))}", "", _line(i), "",
                      "🧠 Tap to copy into the Claude app: which side each instrument leans",
                      f"<code>{_e(market_prompt([i]))}</code>"])


def due_alerts(conn, items: list[dict], now: datetime) -> list[dict]:
    """The fresh high-impact stories not sent yet (one per event, within today's cap)."""
    _ensure(conn)
    day_start = now.astimezone(WAT).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)
    sent_today = conn.execute("SELECT COUNT(*) FROM market_news_sent WHERE sent_at >= ?",
                              (day_start.isoformat(),)).fetchone()[0]
    recent = [set(re.findall(r"[a-z]{4,}", (t or "").lower())) for (t,) in conn.execute(
        "SELECT title FROM market_news_sent WHERE sent_at >= ?", ((now - timedelta(hours=12)).isoformat(),))]
    fresh = [i for i in items if i["published"] and now - i["published"] <= ALERT_FRESH]
    out = []
    for i in market_pick(fresh, ALERT_MAX_PER_DAY, now, hours=2, min_impact=ALERT_MIN_IMPACT):
        if sent_today + len(out) >= ALERT_MAX_PER_DAY:
            break
        if conn.execute("SELECT 1 FROM market_news_sent WHERE link = ?", (i["link"],)).fetchone():
            continue
        words = set(re.findall(r"[a-z]{4,}", i["title"].lower()))
        if any(len(words & w) >= 3 for w in recent):
            continue                                      # already told her about this event
        out.append(i)
        recent.append(words)
    return out


async def run_market_alerts(db_path: str, config) -> int:
    """Scheduled every 15 minutes: the owner gets each high-impact market story once, on the main bot."""
    from alerts.telegram import send_alert
    if not (getattr(config, "telegram_enabled", True) and config.telegram_bot_token):
        return 0
    now = datetime.now(timezone.utc)
    wat = now.astimezone(WAT)
    if not (6 <= wat.hour < 22 or (wat.hour == 22 and wat.minute < 30)):
        return 0                                          # she sleeps: the morning brief catches the night up
    items = await fetch_all(MARKET_FEEDS)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    try:
        r = conn.execute("SELECT telegram_chat_id FROM users WHERE role = 'OWNER' AND telegram_chat_id IS NOT NULL "
                         "AND telegram_chat_id != '' LIMIT 1").fetchone()
        if not r:
            return 0
        sent = 0
        for i in due_alerts(conn, items, now):
            if await send_alert(config.telegram_bot_token, str(r[0]), alert_text(i), parse_mode="HTML"):
                conn.execute("INSERT OR IGNORE INTO market_news_sent (link, title, sent_at) VALUES (?, ?, ?)",
                             (i["link"], i["title"], now.isoformat()))
                conn.commit()
                sent += 1
        return sent
    finally:
        conn.close()

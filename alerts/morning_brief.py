"""
The owner's Morning Brief on the Job Hunt bot (owner request 2026-11-22).

Goal: be the well-informed, well-spoken person in the room, and spot what is
going viral so they can make their own version. Free sources only.

  • 07:10 WAT: news that moves the world (3 world/business, 2 Nigeria) from
    free RSS feeds, ranked by topics that move markets and prices; a word of
    the day with its meaning and an example; one-tap X searches for the most
    liked posts of the last 24 hours in each niche; the TikTok trends page;
    today's speaking drill.
  • 19:30 WAT: a short evening nudge (post today's piece, save one idea).
  • /brief sends the morning brief on demand.

X charges for automated access and TikTok has no free trend feed, so those
two are links the owner taps, not data we fetch.
"""

from __future__ import annotations

import html
import logging
import re
import sqlite3
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Optional
from urllib.parse import quote

import httpx

logger = logging.getLogger(__name__)
WAT = timezone(timedelta(hours=1))
UA = "Mozilla/5.0 (compatible; MorningBrief/1.0)"

WORLD_FEEDS = (
    ("BBC", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("BBC", "https://feeds.bbci.co.uk/news/business/rss.xml"),
    ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
    ("CNBC", "https://www.cnbc.com/id/20910258/device/rss/rss.html"),
)
NIGERIA_FEEDS = (
    ("Nairametrics", "https://nairametrics.com/feed/"),
    ("BusinessDay", "https://businessday.ng/feed/"),
    ("Premium Times", "https://www.premiumtimesng.com/feed"),
)

# What makes a story "move the world": money, power and policy. Weight = how much it moves things.
TOPICS = {
    3: r"central bank|interest rate|rate (cut|hike)|federal reserve|\bfed\b|\becb\b|bank of england|\bcbn\b|"
       r"inflation|recession|\bgdp\b|tariff|trade (war|deal)|sanction|\boil\b|opec|crude|naira|exchange rate|"
       r"devalu|\bimf\b|world bank|debt|budget|tax|subsid|fuel price|food price|ceasefire|invasion|war\b",
    2: r"election|president|prime minister|government|policy|law\b|bill\b|senate|congress|summit|\bg7\b|\bg20\b|"
       r"china|united states|\bus\b|russia|ukraine|europe|\beu\b|stock|market|shares|dollar|gold|bitcoin|"
       r"\bai\b|artificial intelligence|jobs|unemployment|wage|minimum wage|strike|bank",
    1: r"company|deal|profit|earnings|investment|investor|growth|price|export|import|power|electricity|"
       r"housing|rent|school|health",
}
SKIP = r"football|premier league|match|celebrity|actor|actress|singer|bbnaija|big brother|music|movie|film|" \
       r"fashion|wedding|murder|crash|killed in|accident|horoscope|recipe|quiz|live:|watch:|in pictures|photos:"

# Word of the day: useful in money, news and everyday serious talk. (word, meaning, example)
WORDS = [
    ("nuance", "a small but important difference in meaning or detail",
     "The headline says prices fell, but the nuance is that they only fell for one month."),
    ("pragmatic", "dealing with things in a practical, realistic way",
     "A pragmatic fix for high prices is buying in bulk with neighbours."),
    ("leverage", "to use something you have to get a bigger result",
     "She leveraged her testing skills to check food quality."),
    ("volatile", "likely to change suddenly and a lot",
     "The naira has been volatile, so prices change from week to week."),
    ("resilient", "able to recover quickly from difficulty",
     "Small traders in Nigeria are resilient; they adjust and keep going."),
    ("incentive", "something that encourages a person to act",
     "Lower taxes are an incentive for companies to invest."),
    ("trade-off", "giving up one thing to get another",
     "Cheap rice has a trade-off: you spend time picking out stones."),
    ("headwind", "a force that slows progress",
     "High interest rates are a headwind for small businesses."),
    ("tailwind", "a force that helps progress",
     "Festive season demand is a tailwind for food sellers."),
    ("austerity", "a government cutting spending to save money",
     "Austerity often means fewer public services for ordinary people."),
    ("subsidy", "money a government pays to keep a price low",
     "When the fuel subsidy ended, transport fares went up."),
    ("liquidity", "how easily money or assets can be used or sold",
     "Low dollar liquidity made it hard for importers to pay suppliers."),
    ("ripple effect", "when one event causes a spread of other effects",
     "A rise in diesel prices has a ripple effect on food prices."),
    ("purchasing power", "how much your money can buy",
     "Inflation reduces purchasing power, so the same salary buys less."),
    ("geopolitics", "how geography and power shape relations between countries",
     "Geopolitics in the Middle East can move oil prices overnight."),
    ("consensus", "general agreement among a group",
     "The consensus among analysts is that rates will stay high."),
    ("unprecedented", "never happened before",
     "The drop in the currency was unprecedented in a single day."),
    ("underscore", "to emphasise or show clearly",
     "The queues underscore how scarce fuel has become."),
    ("prudent", "careful and wise, especially with money",
     "It is prudent to keep three months of savings."),
    ("discerning", "able to judge quality well",
     "Discerning buyers check the grain before they pay."),
    ("compelling", "so strong or interesting you pay attention",
     "She told a compelling story about her first trade."),
    ("resonate", "to feel true or meaningful to someone",
     "Posts about starting again resonate with many people."),
    ("ambivalent", "having mixed feelings about something",
     "Many people are ambivalent about the new tax: it helps some and hurts others."),
    ("complacent", "too satisfied, so you stop being careful",
     "Winning trades can make a trader complacent."),
    ("meticulous", "very careful about small details",
     "A meticulous tester checks every button."),
    ("tenacious", "not giving up easily",
     "Tenacious people keep showing up when results are slow."),
    ("succinct", "short and clear",
     "Give a succinct answer: what happened and why it matters."),
    ("pivotal", "very important, a turning point",
     "This election is pivotal for the economy."),
    ("plausible", "seems reasonable or likely to be true",
     "It is plausible that rates will fall next year."),
    ("scrutiny", "close and careful examination",
     "The new law is under scrutiny from business groups."),
    ("precedent", "an earlier event used as an example for later ones",
     "The ruling sets a precedent for future cases."),
    ("hedge", "to protect yourself against loss",
     "Some families hedge against inflation by buying food in bulk."),
    ("momentum", "the force that keeps something moving",
     "Posting daily builds momentum, even when views are small."),
    ("stagnation", "when something stops growing or moving",
     "Wage stagnation means salaries stay the same while prices rise."),
    ("deficit", "when spending is more than income",
     "The government runs a deficit when it spends more than it collects."),
    ("fiscal", "about government money: taxes and spending",
     "Fiscal policy is how a government taxes and spends."),
    ("monetary", "about money supply and interest rates, run by the central bank",
     "Monetary policy is the CBN's tool for fighting inflation."),
    ("bilateral", "between two countries or sides",
     "Nigeria signed a bilateral trade deal with the UK."),
    ("embargo", "an official ban on trade",
     "An oil embargo can push prices up worldwide."),
    ("catalyst", "something that causes a change to happen",
     "The rate cut was a catalyst for the market rally."),
    ("sentiment", "the general feeling or mood about something",
     "Market sentiment turned negative after the news."),
    ("mitigate", "to make something less harmful",
     "Buying in season can mitigate rising food costs."),
    ("candid", "honest and direct",
     "She was candid about her losing month."),
    ("empathy", "understanding how someone else feels",
     "Good customer service starts with empathy."),
    ("perspective", "a way of seeing something",
     "From a trader's perspective, the news was already priced in."),
    ("paradox", "something that seems to contradict itself but is true",
     "The paradox of saving: if everyone saves, businesses sell less."),
    ("inevitable", "certain to happen",
     "Losses are inevitable in trading; managing them is the skill."),
    ("ubiquitous", "found everywhere",
     "Mobile money is now ubiquitous in Nigeria."),
    ("speculate", "to guess without full information; or to take a risk for profit",
     "Don't speculate on the news; wait for the numbers."),
    ("benchmark", "a standard used for comparison",
     "The CBN rate is the benchmark for bank lending rates."),
    ("articulate", "able to express ideas clearly",
     "Being articulate is a habit, not a gift."),
    ("concede", "to admit something is true, often unwillingly",
     "He conceded that the plan had flaws."),
    ("contagion", "when a problem spreads from one place to others",
     "Bank failures can cause contagion across markets."),
    ("sovereign", "about a country's own government (as in sovereign debt)",
     "Sovereign debt is money a government owes."),
    ("surplus", "more than is needed; income above spending",
     "A trade surplus means a country sells more than it buys."),
    ("devaluation", "a fall in a currency's official value",
     "Devaluation makes imports like rice and fuel more expensive."),
    ("disposable income", "money left after taxes and bills",
     "When disposable income falls, people cut luxuries first."),
    ("eloquent", "speaking or writing fluently and persuasively",
     "Her eloquent post explained inflation in five lines."),
    ("introspection", "looking inward at your own thoughts and feelings",
     "Journaling after each trade is a form of introspection."),
    ("trajectory", "the path or direction something is moving in",
     "Her career trajectory changed when she learned to test software."),
]

# Speaking drills, one a day (articulation + flowing thought)
DRILLS = [
    "Pick one story. Voice note, 60 seconds: what happened, why it matters, what it means for a family in Ibadan.",
    "Explain one story to an imaginary 12-year-old. No jargon. Record it.",
    "Use today's word three times: in a sentence, in a chat, in a post.",
    "Give your opinion on one story in this shape: 'I think… because… but I could be wrong if…'",
    "Connect two stories: how does one affect the other? Say it in under a minute.",
    "Read one article out loud slowly. Then say its point in one sentence without looking.",
    "Write a 3-line post on one story: the fact, why it matters, a question for your followers.",
]

# One-tap X searches: most-liked original posts since yesterday, per niche (min_faves = likes floor)
X_SEARCHES = [
    ("💰 Money", "(money OR wealth OR savings OR salary OR rich OR broke)", 3000),
    ("📈 Trading", "(trading OR trader OR forex OR \"risk management\")", 500),
    ("🧠 Psychology & emotions", "(psychology OR healing OR anxiety OR \"self worth\" OR lonely OR overthinking)", 3000),
    ("🌱 Hope & success", "(\"don't give up\" OR \"keep going\" OR success OR \"your time\" OR grateful)", 5000),
    ("🇳🇬 Nigeria", "(naija OR nigeria OR lagos OR nigerians)", 1000),
    ("💼 Business", "(business OR entrepreneur OR customers OR \"small business\")", 2000),
]
TIKTOK_TRENDS = "https://ads.tiktok.com/creative/creativeCenter/trends"


def _e(s: str) -> str:
    return html.escape(s or "", quote=False)


def _strip(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def parse_rss(xml_text: str, source: str) -> list[dict]:
    """Items from an RSS 2.0 feed: title, link, summary, published (UTC) and source."""
    out = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return out
    for it in root.iter("item"):
        title = _strip(it.findtext("title"))
        link = (it.findtext("link") or "").strip()
        if not title or not link:
            continue
        try:
            pub = parsedate_to_datetime(it.findtext("pubDate") or "").astimezone(timezone.utc)
        except (TypeError, ValueError):
            pub = None
        out.append({"title": title, "link": link, "summary": _strip(it.findtext("description"))[:400],
                    "published": pub, "source": source})
    return out


def score(item: dict) -> int:
    text = f"{item['title']} {item['summary']}".lower()
    if re.search(SKIP, item["title"].lower()):
        return 0
    return sum(w * len(set(re.findall(p, text))) for w, p in TOPICS.items())


def pick(items: list[dict], n: int, now: datetime, hours: int = 30) -> list[dict]:
    """The n highest-scoring stories from the last `hours`, no near-duplicate headlines."""
    fresh = [i for i in items if i["published"] is None or now - i["published"] <= timedelta(hours=hours)]
    ranked = sorted(((score(i), i) for i in fresh), key=lambda t: (-t[0], -(t[1]["published"] or now).timestamp()))
    chosen, seen = [], []
    for s, i in ranked:
        if s <= 0:
            break
        words = set(re.findall(r"[a-z]{4,}", i["title"].lower()))
        if any(len(words & w) >= 3 for w in seen):
            continue
        chosen.append(i)
        seen.append(words)
        if len(chosen) == n:
            break
    return chosen


async def fetch_all(feeds) -> list[dict]:
    items = []
    async with httpx.AsyncClient(timeout=20, follow_redirects=True, headers={"User-Agent": UA}) as client:
        for source, url in feeds:
            try:
                r = await client.get(url)
                r.raise_for_status()
                items += parse_rss(r.text, source)
            except httpx.HTTPError as e:
                logger.warning("Morning brief feed failed (%s): %s", source, e)
    return items


def x_search_url(query: str, likes: int, since: date) -> str:
    q = f"{query} min_faves:{likes} lang:en -filter:replies since:{since.isoformat()}"
    return f"https://x.com/search?q={quote(q)}&src=typed_query&f=top"


def word_of_day(d: date) -> tuple[str, str, str]:
    return WORDS[d.toordinal() % len(WORDS)]


def _story(i: dict) -> str:
    gist = i["summary"]
    if gist and gist.lower() != i["title"].lower():
        gist = (gist[:180].rsplit(" ", 1)[0] + "…") if len(gist) > 180 else gist
        gist = f"\n<i>{_e(gist)}</i>"
    else:
        gist = ""
    return f"• <a href=\"{_e(i['link'])}\">{_e(i['title'])}</a> ({_e(i['source'])}){gist}"


def brief_text(world: list[dict], nigeria: list[dict], d: date) -> str:
    w, meaning, example = word_of_day(d)
    since = d - timedelta(days=1)
    lines = [f"☀️ <b>Morning Brief · {d.strftime('%a %d %b')}</b>", "",
             "🌍 <b>Moving the world</b>"]
    lines += [_story(i) for i in world] or ["• The feeds were quiet. Check BBC Business when you can."]
    lines += ["", "🇳🇬 <b>Nigeria</b>"]
    lines += [_story(i) for i in nigeria] or ["• The feeds were quiet. Check Nairametrics when you can."]
    lines += ["", f"📖 <b>Word of the day: {_e(w)}</b>", f"{_e(meaning)}.", f"<i>\"{_e(example)}\"</i>",
              "", "🔥 <b>What's blowing up (most liked)</b>"]
    week = d - timedelta(days=7)
    lines += [f"• {_e(label)} on X: <a href=\"{_e(x_search_url(q, n, since))}\">last 24h</a> · "
              f"<a href=\"{_e(x_search_url(q, n * 3, week))}\">this week</a>" for label, q, n in X_SEARCHES]
    lines += [f"• <a href=\"{TIKTOK_TRENDS}\">TikTok trends</a> (Creative Center: pick country + 7 days)",
              "", f"🎙 <b>Today's drill</b>\n{_e(DRILLS[d.toordinal() % len(DRILLS)])}",
              "", "<i>Study why a post worked (first line, feeling, format), then tell your own true version.</i>"]
    return "\n".join(lines)


def evening_text(d: date) -> str:
    w = word_of_day(d)[0]
    return ("🌙 <b>Evening check</b>\n\n"
            "1. Did you post today? One honest piece is enough.\n"
            f"2. Did you use <b>{_e(w)}</b> once, in speech or writing?\n"
            "3. Save one idea you saw today (screenshot or note) for tomorrow's post.\n\n"
            "Reply to anyone who commented. /brief brings back this morning's brief.")


async def build_brief(now: Optional[datetime] = None) -> str:
    now = now or datetime.now(timezone.utc)
    world = pick(await fetch_all(WORLD_FEEDS), 3, now)
    nigeria = pick(await fetch_all(NIGERIA_FEEDS), 2, now)
    return brief_text(world, nigeria, now.astimezone(WAT).date())


def _owner(conn) -> Optional[str]:
    r = conn.execute("SELECT telegram_chat_id FROM users WHERE role = 'OWNER' AND telegram_chat_id IS NOT NULL "
                     "AND telegram_chat_id != '' LIMIT 1").fetchone()
    return str(r[0]) if r else None


async def send_brief(token: str, chat: str, send) -> bool:
    return await send(token, chat, await build_brief())


async def run_morning_brief(db_path: str, config, evening: bool = False) -> bool:
    """Scheduled: the morning brief (or the evening check) to the owner on the Job Hunt bot."""
    from alerts.job_digest import _send
    token = getattr(config, "jobs_bot_token", "")
    if not token:
        return False
    conn = sqlite3.connect(db_path, check_same_thread=False)
    try:
        chat = _owner(conn)
    finally:
        conn.close()
    if not chat:
        return False
    if evening:
        return await _send(token, chat, evening_text(datetime.now(WAT).date()))
    return await send_brief(token, chat, _send)

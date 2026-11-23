"""
The owner's daily routine on the Job Hunt bot (owner request 2026-11-23). One nudge at the start of each block:

  06:00 WAT  Morning Brief (alerts/morning_brief.py, moved here from 07:10)
  07:00      Posting block: post what was prepared yesterday on LinkedIn, Facebook, X and TikTok, plus one post
             built from this morning's news. (The LinkedIn coach's post arrives at the same time.)
  09:00      Backtest, round 1 (until 12:00)
  12:00      Water / stretch, reply to comments (the LinkedIn comment + connect tasks arrive here)
  13:00      Lunch, then the afternoon post round (until 14:00)
  14:00      Backtest, round 2 (until 16:00), then backtesting is done for the day
  16:00      Prepare TOMORROW: tomorrow's LinkedIn post + flyer prompt, tomorrow's Style House niche and pictures
  19:30      Evening check (alerts/morning_brief.py)

Server times are UTC; minutes are nudged off the H4 closes (00/04/08/12/16/20 UTC). Every day; /routine shows it.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional

WAT = timezone(timedelta(hours=1))

# (slot, UTC hour, UTC minute, WAT label)
SLOTS = [("post", 5, 58, "07:00"), ("bt1", 8, 2, "09:00"), ("break", 11, 0, "12:00"),
         ("lunch", 12, 5, "13:00"), ("bt2", 13, 0, "14:00"), ("prep", 15, 0, "16:00")]

PLAN = [("06:00–07:00", "📰 Daily digest: read the Morning Brief, tap the 🧠 box, note your thoughts"),
        ("07:00–09:00", "📣 Post on LinkedIn, Facebook, X and TikTok (prepared yesterday) + one news post"),
        ("09:00–12:00", "📈 Backtest, round 1"),
        ("12:00–13:00", "💧 Water and stretch, reply to every comment"),
        ("13:00–14:00", "🍲 Lunch, then the afternoon post round"),
        ("14:00–16:00", "📈 Backtest, round 2: then done for the day"),
        ("16:00 onward", "🛠 Prepare tomorrow: posts, flyers, Style House pictures")]


def _backtest_url(config) -> str:
    return f"{getattr(config, 'frontend_url', '').rstrip('/')}/backtest"


def routine_text(now: Optional[datetime] = None) -> str:
    lines = ["🗓 <b>Your daily routine</b>", ""]
    for when, what in PLAN:
        lines.append(f"<b>{when}</b>  {what}")
    lines += ["", "Whatever you post tomorrow, you prepare today from 16:00. The mornings are just for posting and "
              "replying, plus one post built from that day's news.", "",
              "/brief · /posts · /flyer · /style · /plan · /quote"]
    return "\n".join(lines)


def slot_text(slot: str, config, now: Optional[datetime] = None) -> tuple[str, object]:
    """The nudge for a slot, and its buttons (or None)."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    d = (now or datetime.now(timezone.utc)).astimezone(WAT).date()
    bt = InlineKeyboardMarkup([[InlineKeyboardButton("Open Quick Backtest ↗", url=_backtest_url(config))]])
    if slot == "post":
        from alerts.style_prompts import today_niche
        niche = today_niche(d)[1]
        return ("📣 <b>Posting time (07:00–09:00)</b>\n\n"
                "☐ <b>LinkedIn:</b> today's post + flyer (both arrive right after this)\n"
                f"☐ <b>Facebook, X, TikTok:</b> the Style House carousel you prepared yesterday ({niche})\n"
                "☐ <b>X:</b> one or two from /posts, then tap ✅ Posted\n"
                "☐ <b>News post:</b> pick one story from this morning's brief and say it in your own words, with "
                "today's word if it fits\n\n"
                "Then reply to anyone who has already commented.", None)
    if slot == "bt1":
        return ("📈 <b>Backtest, round 1 (09:00–12:00)</b>\n\nPhone on silent, socials closed. Pick up where you "
                "stopped and log every trade as you go.", bt)
    if slot == "break":
        return ("💧 <b>Break (12:00–13:00)</b>\n\nWater, stretch, step away from the screen. Then reply to every "
                "comment on today's posts: replies push your posts to more people. Your LinkedIn comment and "
                "connect tasks come right after this.", None)
    if slot == "lunch":
        return ("🍲 <b>Lunch, then the afternoon round (13:00–14:00)</b>\n\n"
                "☐ Eat first 🙂\n☐ Afternoon post on each platform: a saved post (/posts), a style picture, or a "
                "short take on the news\n☐ Quick reply round on comments and messages", None)
    if slot == "bt2":
        return ("📈 <b>Backtest, round 2 (14:00–16:00)</b>\n\nThe last stretch for today. At 16:00 you're done "
                "with backtesting: write one line on what you noticed in your journal.", bt)
    if slot == "prep":
        return _prep_text(d), None
    return "", None


def _prep_text(d) -> str:
    """16:00: everything to prepare for tomorrow."""
    import html
    from alerts.style_prompts import today_niche
    from alerts.linkedin_coach import POSTS
    t = d + timedelta(days=1)
    day, niche, example, hint = today_niche(t)
    p = POSTS.get(t.isoformat())
    lines = [f"🛠 <b>Prepare tomorrow ({t.strftime('%a %d %b')})</b>", "",
             f"☐ <b>Style House:</b> tomorrow is <b>{html.escape(niche, quote=False)}</b> "
             f"({html.escape(hint, quote=False)}). Make the pictures with /style, save them into the inbox, run "
             "add-styles.bat, and get the carousel ready.",
             f"   Example file name: <code>{html.escape(example, quote=False)}</code>"]
    if p:
        lines += [f"☐ <b>LinkedIn:</b> tomorrow's post is <b>{html.escape(p['title'], quote=False)}</b>. Read it, "
                  "rephrase it in your voice, then make its flyer: send <code>/flyer</code> + your version. Save the "
                  "flyer for 07:00."]
    else:
        lines += ["☐ <b>LinkedIn:</b> no ready post tomorrow: pick a top post from this morning's links and write your "
                  "own version, then <code>/flyer</code> + your text for its flyer."]
    lines += ["☐ <b>X:</b> save 2–3 posts for tomorrow by sending them to me (they wait in /posts)",
              "☐ <b>TikTok:</b> pick the sound and the 1–2 pictures to animate", "",
              "When it's all ready, you're done for the day. Tomorrow morning is just posting and replying. 🙌"]
    return "\n".join(lines)


async def run_routine(db_path: str, config, slot: str) -> bool:
    from alerts.job_digest import _send
    from alerts.morning_brief import _owner
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
    text, markup = slot_text(slot, config)
    return bool(text) and await _send(token, chat, text, markup)

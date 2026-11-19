"""
Job Hunt (owner only, user request 2026-11-19): a daily digest of new remote jobs to a SEPARATE Telegram bot,
with a tracker of what she applied for and follow-up questions.

Every morning (08:30 WAT, after the school run: she applies through the morning into the afternoon, user 2026-11-19) the server reads six free job
feeds (Remotive, Himalayas, We Work Remotely, Jobicy, Remote OK, Working Nomads) and keeps the jobs that:
  - have one of her titles (QA / tester, customer success / support, product analyst / operations, AI trainer /
    evaluator / annotation / prompt work), not senior, lead, manager or head roles;
  - are remote and open to Nigeria, Africa, EMEA or worldwide; a title that names another region (LATAM, US ...)
    or wants native speakers of a country is dropped;
  - are new (never sent before).
Each job is its own message with buttons: Apply (link) · Applied · Skip. "Applied" starts the tracker; 7 days later
the bot asks how it went (Follow-up sent / Interview / Rejected / No reply). The owner's dashboard page
"Job Hunt" lists them all.

The bot token is the JOBS_BOT_TOKEN secret (a bot made with @BotFather). Messages go to the owner's Telegram
(the same person: a Telegram user's private chat id is the same for every bot), once she has pressed Start on it.
"""

from __future__ import annotations

import asyncio
import html
import json
import logging
import re
import sqlite3
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Optional

logger = logging.getLogger(__name__)

WAT = timezone(timedelta(hours=1))
FOLLOW_DAYS = 7
MAX_PER_DAY = 15
UA = {"User-Agent": "Mozilla/5.0 (personal job digest)"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS job_apps (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    url         TEXT NOT NULL UNIQUE,
    source      TEXT NOT NULL,
    title       TEXT NOT NULL,
    company     TEXT NOT NULL,
    location    TEXT NOT NULL,
    region      TEXT NOT NULL,          -- 'Nigeria' | 'Africa' | 'EMEA' | 'Worldwide'
    posted_at   TEXT NOT NULL,
    sent_at     TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'new',   -- new | applied | skipped | followed_up | interview | rejected | no_reply | offer
    applied_at  TEXT,
    follow_at   TEXT,                   -- when to ask how it went (UTC)
    updated_at  TEXT,
    note        TEXT
)
"""

STATUSES = ("new", "applied", "skipped", "followed_up", "interview", "rejected", "no_reply", "offer")
STATUS_LABEL = {"new": "New", "applied": "Applied", "skipped": "Skipped", "followed_up": "Followed up",
                "interview": "Interview", "rejected": "Rejected", "no_reply": "No reply", "offer": "Offer"}

TITLE = re.compile(
    r"\b(qa|quality assurance|tester|testing|test analyst|customer success|customer support|"
    r"support (specialist|agent|associate|representative|analyst|engineer)|technical support|product analyst|"
    r"product operations|product ops|associate product manager|ai (trainer|tutor|evaluator|rater|annotator|specialist)|"
    r"data annotat\w*|annotator|prompt|llm|rlhf|ai training|evaluator|rater)\b", re.I)
SENIOR = re.compile(r"\b(senior|sr\.?|lead|principal|head|director|staff|vp|chief|manager)\b", re.I)
REGION_TITLE = re.compile(r"\b(latam|americas?|north america|usa?|canada|apac|asia|west region|east region)\b", re.I)
NATIVE = re.compile(r"speakers? in|native (speaker|level)", re.I)


def ensure_table(conn) -> None:
    conn.execute(SCHEMA)


def classify(title: str, location: str) -> Optional[str]:
    """The region group a job goes under, or None when it is not one for her."""
    if not TITLE.search(title) or REGION_TITLE.search(title) or NATIVE.search(title):
        return None
    if SENIOR.search(title) and not re.search(r"associate product manager", title, re.I):
        return None
    loc = (location or "").strip()
    if not loc or re.search(r"worldwide|anywhere|global", loc, re.I):
        return "Worldwide"
    if re.search(r"nigeria", loc, re.I):
        return "Nigeria"
    if re.search(r"africa", loc, re.I):
        return "Africa"
    if re.search(r"\bemea\b", loc, re.I):
        return "EMEA"
    return None


def _get(url: str) -> bytes:
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read()


def fetch_jobs(since: datetime) -> list[dict]:
    """All six feeds, jobs posted after `since` that fit her. A feed that fails is skipped (logged)."""
    out: list[dict] = []

    def add(src, title, company, loc, when, url):
        if when is None or when < since or not url:
            return
        title, company = html.unescape(title or "").strip(), html.unescape(company or "").strip()
        region = classify(title, loc)
        if region:
            out.append({"source": src, "title": title, "company": company or "?", "location": (loc or "").strip() or "Worldwide",
                        "region": region, "posted_at": when.astimezone(timezone.utc).isoformat(), "url": url})

    def utc(s):
        d = datetime.fromisoformat(s)
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)

    for q in ("qa", "customer success", "customer support", "product analyst", "product operations",
              "ai trainer", "annotation", "prompt"):
        try:
            for j in json.loads(_get("https://remotive.com/api/remote-jobs?search=" + urllib.parse.quote(q)))["jobs"]:
                add("Remotive", j["title"], j["company_name"], j.get("candidate_required_location"), utc(j["publication_date"]), j["url"])
        except Exception as e:
            logger.warning("Job feed Remotive (%s) failed: %s", q, e)
    cur, pages = None, 0
    while pages < 60:
        try:
            d = json.loads(_get("https://himalayas.app/jobs/api?limit=20" + (f"&cursor={cur}" if cur else "")))
        except Exception as e:
            logger.warning("Job feed Himalayas failed: %s", e)
            break
        old = 0
        for j in d.get("jobs", []):
            w = datetime.fromtimestamp(int(j["pubDate"]), timezone.utc)
            old += w < since
            add("Himalayas", j["title"], j["companyName"], ", ".join(j.get("locationRestrictions") or []), w, j.get("applicationLink"))
        cur, pages = d.get("nextCursor"), pages + 1
        if old >= 15 or not cur:
            break
    try:
        for it in ET.fromstring(_get("https://weworkremotely.com/remote-jobs.rss")).iter("item"):
            comp, _, title = (it.findtext("title") or "").partition(": ")
            add("We Work Remotely", title or comp, comp if title else "", it.findtext("region") or "",
                parsedate_to_datetime(it.findtext("pubDate")), it.findtext("link"))
    except Exception as e:
        logger.warning("Job feed We Work Remotely failed: %s", e)
    try:
        for j in json.loads(_get("https://jobicy.com/api/v2/remote-jobs?count=100"))["jobs"]:
            add("Jobicy", j["jobTitle"], j["companyName"], j.get("jobGeo") or "", utc(j["pubDate"]), j["url"])
    except Exception as e:
        logger.warning("Job feed Jobicy failed: %s", e)
    try:
        for j in json.loads(_get("https://remoteok.com/api"))[1:]:     # the first item is their legal notice
            add("Remote OK", j.get("position"), j.get("company"), j.get("location") or "", utc(j["date"]), j.get("url"))
    except Exception as e:
        logger.warning("Job feed Remote OK failed: %s", e)
    try:
        for j in json.loads(_get("https://www.workingnomads.com/api/exposed_jobs/")):
            add("Working Nomads", j["title"], j["company_name"], j.get("location") or "", utc(j["pub_date"]), j["url"])
    except Exception as e:
        logger.warning("Job feed Working Nomads failed: %s", e)

    seen, uniq = set(), []
    for j in sorted(out, key=lambda j: j["posted_at"], reverse=True):
        k = (j["title"].lower(), j["company"].lower())
        if k not in seen:
            seen.add(k)
            uniq.append(j)
    order = {"Nigeria": 0, "Africa": 1, "Worldwide": 2, "EMEA": 3}
    return sorted(uniq, key=lambda j: order[j["region"]])


def store_new(conn, jobs: list[dict], now: datetime) -> list[dict]:
    """Keep the jobs never sent before (by link and by title + company); returns them with their ids."""
    ensure_table(conn)
    new = []
    for j in jobs:
        if conn.execute("SELECT 1 FROM job_apps WHERE url = ? OR (lower(title) = ? AND lower(company) = ?)",
                        (j["url"], j["title"].lower(), j["company"].lower())).fetchone():
            continue
        if len(new) >= MAX_PER_DAY:
            break
        jid = conn.execute(
            "INSERT INTO job_apps (url, source, title, company, location, region, posted_at, sent_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (j["url"], j["source"], j["title"], j["company"], j["location"], j["region"], j["posted_at"],
             now.isoformat(), now.isoformat())).lastrowid
        new.append({**j, "id": jid})
    conn.commit()
    return new


FLAG = {"Nigeria": "🇳🇬", "Africa": "🌍", "Worldwide": "🌍", "EMEA": "🌍"}


def _ago(posted_at: str, now: datetime) -> str:
    h = int((now - datetime.fromisoformat(posted_at)).total_seconds() // 3600)
    return "just now" if h < 1 else f"{h}h ago" if h < 48 else f"{h // 24} days ago"


def job_text(j: dict, now: datetime) -> str:
    where = {"Nigeria": "open to Nigeria", "Africa": "open to Africa", "Worldwide": "worldwide",
             "EMEA": "EMEA (usually includes Africa: check)"}[j["region"]]
    return (f"{FLAG[j['region']]} <b>{html.escape(j['title'])}</b>\n{html.escape(j['company'])} · {where}\n"
            f"Posted {_ago(j['posted_at'], now)} · {html.escape(j['source'])}")


def job_buttons(j: dict, status: str = "new"):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    row = [InlineKeyboardButton("Apply ↗", url=j["url"])]
    if status == "new":
        row += [InlineKeyboardButton("✅ Applied", callback_data=f"jb:a:{j['id']}"),
                InlineKeyboardButton("⏭ Skip", callback_data=f"jb:s:{j['id']}")]
    return InlineKeyboardMarkup([row])


def follow_buttons(jid: int):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📨 Follow-up sent", callback_data=f"jb:f:{jid}:followed_up"),
         InlineKeyboardButton("🎤 Interview", callback_data=f"jb:f:{jid}:interview")],
        [InlineKeyboardButton("❌ Rejected", callback_data=f"jb:f:{jid}:rejected"),
         InlineKeyboardButton("🔇 No reply", callback_data=f"jb:f:{jid}:no_reply")]])


def follow_text(r: dict) -> str:
    days = (datetime.now(timezone.utc) - datetime.fromisoformat(r["applied_at"])).days
    again = "Still nothing since your follow-up? " if r["status"] == "followed_up" else ""
    return (f"⏰ <b>Follow-up check</b>\n{again}You applied to <b>{html.escape(r['title'])}</b> at "
            f"{html.escape(r['company'])} {days} days ago. Did you hear back?\n\n"
            f"No reply yet? Send a short, polite follow-up email or LinkedIn message, then tap Follow-up sent.")


def owner_chat(conn) -> Optional[str]:
    r = conn.execute("SELECT telegram_chat_id FROM users WHERE role = 'OWNER' AND telegram_chat_id IS NOT NULL "
                     "AND telegram_chat_id != '' LIMIT 1").fetchone()
    return str(r[0]) if r else None


def due_followups(conn, now: datetime) -> list[dict]:
    ensure_table(conn)
    conn.row_factory = sqlite3.Row
    return [dict(r) for r in conn.execute(
        "SELECT * FROM job_apps WHERE status IN ('applied', 'followed_up') AND follow_at IS NOT NULL AND follow_at <= ? "
        "ORDER BY follow_at", (now.isoformat(),))]


async def _send(token: str, chat: str, text: str, markup=None) -> bool:
    from telegram import Bot
    from telegram.error import TelegramError
    try:
        await Bot(token=token).send_message(chat_id=chat, text=text, parse_mode="HTML", reply_markup=markup,
                                            disable_web_page_preview=True)
        return True
    except TelegramError as e:
        logger.warning("Job Hunt bot message failed: %s", e)
        return False


async def run_job_digest(db_path: str, config, now: Optional[datetime] = None) -> int:
    """The morning digest: new jobs (each with its buttons), then the follow-up questions due. Returns jobs sent."""
    token = getattr(config, "jobs_bot_token", "")
    if not token:
        return 0
    now = now or datetime.now(timezone.utc)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        ensure_table(conn)
        chat = owner_chat(conn)
        if not chat:
            logger.warning("Job Hunt digest: the owner has no Telegram chat")
            return 0
        last = conn.execute("SELECT MAX(sent_at) FROM job_apps").fetchone()[0]
        since = max(now - timedelta(hours=48), datetime.fromisoformat(last) - timedelta(hours=6)) if last \
            else now - timedelta(hours=48)
        jobs = await asyncio.to_thread(fetch_jobs, since)
        new = store_new(conn, jobs, now)
        day = now.astimezone(WAT).strftime("%a %d %b")
        follows = due_followups(conn, now)
        head = (f"💼 <b>Job digest · {day}</b>\n{len(new)} new remote job{'s' if len(new) != 1 else ''} for you"
                + (f" · {len(follows)} follow-up{'s' if len(follows) != 1 else ''} to check" if follows else "")
                + ("\n\nTap Apply to open the post. Check where they hire before you apply: \"worldwide\" "
                   "is not always true. Paste the job description to Claude for your tailored CV." if new else
                   "\n\nNothing new on the remote boards today. Check your LinkedIn and Jobberman email alerts."))
        await _send(token, chat, head)
        for j in new:
            await _send(token, chat, job_text(j, now), job_buttons(j))
            await asyncio.sleep(0.4)
        for r in follows:
            if await _send(token, chat, follow_text(r), follow_buttons(r["id"])):
                # ask again in 7 days if nothing is tapped
                conn.execute("UPDATE job_apps SET follow_at = ? WHERE id = ?",
                             ((now + timedelta(days=FOLLOW_DAYS)).isoformat(), r["id"]))
        conn.commit()
        logger.info("Job Hunt digest: %d new jobs, %d follow-ups", len(new), len(follows))
        return len(new)
    finally:
        conn.close()


def set_status(conn, jid: int, status: str, now: Optional[datetime] = None) -> Optional[dict]:
    """Change an application's status (bot button or dashboard). Applied / followed up start the 7-day clock."""
    if status not in STATUSES:
        return None
    now = now or datetime.now(timezone.utc)
    ensure_table(conn)
    conn.row_factory = sqlite3.Row
    r = conn.execute("SELECT * FROM job_apps WHERE id = ?", (jid,)).fetchone()
    if not r:
        return None
    applied_at = r["applied_at"]
    follow_at = None
    if status == "applied":
        applied_at = applied_at or now.isoformat()
        follow_at = (now + timedelta(days=FOLLOW_DAYS)).isoformat()
    elif status == "followed_up":
        follow_at = (now + timedelta(days=FOLLOW_DAYS)).isoformat()
    conn.execute("UPDATE job_apps SET status = ?, applied_at = ?, follow_at = ?, updated_at = ? WHERE id = ?",
                 (status, applied_at, follow_at, now.isoformat(), jid))
    conn.commit()
    return dict(conn.execute("SELECT * FROM job_apps WHERE id = ?", (jid,)).fetchone())


async def handle_update(conn, config, update: dict) -> None:
    """A tap or a message on the Job Hunt bot. Only the owner's chat is answered."""
    from telegram import Bot
    from telegram.error import TelegramError
    token = config.jobs_bot_token
    owner = owner_chat(conn)
    bot = Bot(token=token)
    cq = update.get("callback_query")
    if cq:
        chat = str(((cq.get("message") or {}).get("chat") or {}).get("id", ""))
        data = cq.get("data") or ""
        reply = ""
        if owner and chat == owner and data.startswith("jb:"):
            parts = data.split(":")
            try:
                jid = int(parts[2])
                status = {"a": "applied", "s": "skipped"}.get(parts[1]) or (parts[3] if parts[1] == "f" else "")
            except (IndexError, ValueError):
                jid, status = 0, ""
            r = set_status(conn, jid, status) if jid and status else None
            if r:
                reply = {"applied": "Saved as applied. I'll ask how it went in 7 days.", "skipped": "Skipped.",
                         "followed_up": "Follow-up noted. I'll check again in 7 days.",
                         "interview": "Interview! Paste the job description to Claude to prepare.",
                         "rejected": "Noted. On to the next one.", "no_reply": "Noted: closed as no reply."}.get(status, "Saved.")
                try:
                    if parts[1] in ("a", "s"):
                        mark = "✅ Applied" if status == "applied" else "⏭ Skipped"
                        await bot.edit_message_text(chat_id=chat, message_id=cq["message"]["message_id"],
                                                    text=job_text(r, datetime.now(timezone.utc)) + f"\n\n<b>{mark}</b>",
                                                    parse_mode="HTML", reply_markup=job_buttons(r, status),
                                                    disable_web_page_preview=True)
                    else:
                        await bot.edit_message_text(chat_id=chat, message_id=cq["message"]["message_id"],
                                                    text=f"<b>{html.escape(r['title'])}</b> · {html.escape(r['company'])}\n"
                                                         f"Status: <b>{STATUS_LABEL[status]}</b>", parse_mode="HTML")
                except TelegramError:
                    pass
        try:
            await bot.answer_callback_query(callback_query_id=cq.get("id", ""), text=reply[:200] or None)
        except TelegramError:
            pass
        return
    msg = update.get("message") or {}
    chat = str((msg.get("chat") or {}).get("id", ""))
    if not chat:
        return
    if owner and chat == owner:
        await _send(token, chat, "👋 Job Hunt bot connected. Your remote job digest arrives here every morning at "
                                 "08:30 WAT, with Applied / Skip buttons and follow-up reminders.\n\n"
                                 "Your full list is on the Job Hunt page of your dashboard.")
    else:
        await _send(token, chat, "This is a private bot.")


async def ensure_webhook(config) -> None:
    """Point the Job Hunt bot at this server (same secret header as the main bot)."""
    if not getattr(config, "jobs_bot_token", "") or not config.telegram_webhook_secret:
        return
    from telegram import Bot
    from telegram.error import TelegramError
    url = f"{config.public_api_url.rstrip('/')}/api/jobs-bot/update"
    try:
        bot = Bot(token=config.jobs_bot_token)
        info = await bot.get_webhook_info()
        if info.url != url:
            await bot.set_webhook(url=url, secret_token=config.telegram_webhook_secret,
                                  allowed_updates=["message", "callback_query"])
            logger.info("Job Hunt bot webhook set")
    except TelegramError as e:
        logger.warning("Job Hunt bot webhook could not be set: %s", e)

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
# AI work she can do (2026-11-19): AI trainer / evaluator / annotator / AI QA / AI ops / AI support / prompt work.
# Not the roles that need ML or engineering training.
AI = re.compile(r"\b(ai|a\.i\.|artificial intelligence|gen ?ai|generative|llms?|chatbots?|conversational|"
                r"machine learning|data (label\w*|annotat\w*)|rlhf|prompt\w*)\b", re.I)
AI_HEAVY = re.compile(r"\b(engineer\w*|scientist|research\w*|architect|developer|ml ops|mlops|phd|"
                      r"software|backend|full[- ]?stack|sales|account executive|marketing)\b", re.I)
AI_OK_ROLE = re.compile(r"\b(qa|quality|test\w*|trainer|tutor|evaluat\w*|rater|annotat\w*|label\w*|reviewer|"
                        r"writer|specialist|analyst|associate|operations|ops|support|assistant|coordinator|"
                        r"content|expert|contributor|prompt\w*|freelance\w*)\b", re.I)


def is_ai(title: str) -> bool:
    return bool(AI.search(title))


KINDS = ("job", "freelance", "fiverr", "client")
KIND_LABEL = {"job": "Job", "freelance": "Freelance proposal", "fiverr": "Fiverr order", "client": "Client lead"}
GOAL = {"interviews": 5, "by": "2026-12-24"}    # the owner's goal (2026-11-19): 5 interviews before Christmas


def ensure_table(conn) -> None:
    conn.execute(SCHEMA)
    # entries she adds herself (LinkedIn, Jobberman, Upwork, Fiverr ...) and their type (2026-11-19)
    if "kind" not in {r[1] for r in conn.execute("PRAGMA table_info(job_apps)")}:
        conn.execute("ALTER TABLE job_apps ADD COLUMN kind TEXT NOT NULL DEFAULT 'job'")


def add_manual(conn, title: str, company: str, url: str = "", source: str = "Added by you", kind: str = "job",
               status: str = "applied", now: Optional[datetime] = None) -> dict:
    """An application she made outside the digest. Starts the 7-day follow-up clock when it is applied."""
    import uuid
    ensure_table(conn)
    conn.row_factory = sqlite3.Row
    now = now or datetime.now(timezone.utc)
    kind = kind if kind in KINDS else "job"
    url = (url or "").strip() or f"manual:{uuid.uuid4().hex}"
    jid = conn.execute(
        "INSERT INTO job_apps (url, source, title, company, location, region, posted_at, sent_at, updated_at, kind) "
        "VALUES (?, ?, ?, ?, '', 'Worldwide', ?, ?, ?, ?)",
        (url, source or "Added by you", title.strip()[:200], (company or "?").strip()[:200], now.isoformat(),
         now.isoformat(), now.isoformat(), kind)).lastrowid
    conn.commit()
    return set_status(conn, jid, status if status in STATUSES else "applied", now) or {}


def goal_line(conn) -> str:
    n = conn.execute("SELECT COUNT(*) FROM job_apps WHERE status IN ('interview', 'offer')").fetchone()[0]
    week = conn.execute("SELECT COUNT(*) FROM job_apps WHERE applied_at >= ?",
                        ((datetime.now(timezone.utc) - timedelta(days=7)).isoformat(),)).fetchone()[0]
    return f"🎯 Interviews: {n} of {GOAL['interviews']} by Christmas · {week} applied in the last 7 days"


def classify(title: str, location: str) -> Optional[str]:
    """The region group a job goes under, or None when it is not one for her."""
    ai_fit = AI.search(title) and AI_OK_ROLE.search(title) and not AI_HEAVY.search(title)
    if not (TITLE.search(title) or ai_fit) or REGION_TITLE.search(title) or NATIVE.search(title):
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
              "ai trainer", "annotation", "prompt", "ai", "llm", "ai evaluator", "data labeling", "generative ai"):
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
    # AI jobs first within each region, so the daily cap never drops them
    return sorted(uniq, key=lambda j: (order[j["region"]], not is_ai(j["title"])))


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
    return (f"{FLAG[j['region']]} {'🤖 <b>AI</b> · ' if is_ai(j['title']) else ''}<b>{html.escape(j['title'])}</b>\n{html.escape(j['company'])} · {where}\n"
            f"Posted {_ago(j['posted_at'], now)} · {html.escape(j['source'])}")


def job_buttons(j: dict, status: str = "new"):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    row = [InlineKeyboardButton("Apply ↗", url=j["url"])]
    if status == "new":
        row += [InlineKeyboardButton("✅ Applied", callback_data=f"jb:a:{j['id']}"),
                InlineKeyboardButton("⏭ Skip", callback_data=f"jb:s:{j['id']}")]
    return InlineKeyboardMarkup([row, [InlineKeyboardButton("✍️ Cover note", callback_data=f"jb:c:{j['id']}")]])


# Cover notes: the same texts as the Quick Apply Kit doc (2026-11-19). Filled with the job's title and company;
# the one sentence in [brackets] is hers to change. A template, not paid AI.
_NOTE_END = ("I'm based in Nigeria (WAT, UTC+1), work well remotely, and can start immediately. "
             "My CV is attached. Thank you for your time.\n\nTaiwo Damilola Mayowa")
COVER_NOTES = {
    "qa": ("I'm applying for the {role} position. I spent two years at Belrald, an education software company, "
           "where I built the student and admin portals in React and then moved into QA to test the company's "
           "full product before each release.\n\nBecause I've built features myself, I report bugs developers can "
           "act on quickly: clear steps, expected against actual result, and a re-test once it's fixed. "
           "[One sentence: what in their product you'd enjoy testing, or one requirement you match.]"),
    "frontend": ("I'm applying for the {role} position. At Belrald I built and maintained the student and admin "
                 "portals with HTML, CSS, JavaScript and React, then spent a year in QA, so I build with testing "
                 "in mind.\n\nSince 2024 I've designed and tested my own web platform (a dashboard with Telegram "
                 "alerts) using AI coding tools, which keeps my skills current and fast. "
                 "[One sentence: one thing in the job you've done before.]"),
    "ai": ("I'm applying for the {role} position. I've built and tested a full web platform "
           "by directing an AI coding assistant: writing detailed instructions, checking every answer against real "
           "data, and catching the cases where the AI was confidently wrong, then explaining why so it could be "
           "corrected.\n\nBefore that I spent two years at Belrald, a software company, as a frontend developer and "
           "then a QA tester, and my degree in Anthropology from the University of Ibadan trained me to read "
           "language and context closely. [One sentence: one requirement in this job you match.]"),
    "other": ("I'm applying for the {role} position. I bring two years at a software company, first as a frontend "
              "developer and then in QA, plus hands-on use of Figma and Canva.\n\nI'm careful with detail, I follow "
              "briefs closely, and I check my own work before it goes out. "
              "[One sentence: why this company or one requirement you match.]"),
}


def note_kind(title: str) -> str:
    if is_ai(title):
        return "ai"
    if re.search(r"\b(qa|quality|tester|testing|test)\b", title, re.I):
        return "qa"
    if re.search(r"\b(front[- ]?end|react|web developer|javascript|ui developer)\b", title, re.I):
        return "frontend"
    return "other"


def cover_note(j: dict) -> str:
    company = (j.get("company") or "").strip()
    hello = f"Hello {company} team," if company and company != "?" else "Hello,"
    return f"{hello}\n\n{COVER_NOTES[note_kind(j['title'])].format(role=j['title'].strip())}\n\n{_NOTE_END}"


def cover_note_message(j: dict) -> str:
    label = {"ai": "AI", "qa": "QA", "frontend": "Frontend", "other": "General"}[note_kind(j["title"])]
    return (f"✍️ <b>Cover note</b> ({label}) for {html.escape(j['title'])}\n"
            f"Tap the box to copy. Change the sentence in [brackets], then paste.\n\n"
            f"<pre>{html.escape(cover_note(j))}</pre>")


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
        await _send(token, chat, head + "\n\n" + goal_line(conn))
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
        if owner and chat == owner and data.startswith("jb:c:"):
            conn.row_factory = sqlite3.Row
            try:
                row = conn.execute("SELECT * FROM job_apps WHERE id = ?", (int(data.split(":")[2]),)).fetchone()
            except (IndexError, ValueError):
                row = None
            if row:
                await _send(token, chat, cover_note_message(dict(row)))
            reply = "" if row else "That job is no longer in the tracker."
        elif owner and chat == owner and data.startswith("jb:"):
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
    if not (owner and chat == owner):
        await _send(token, chat, "This is a private bot.")
        return
    text = (msg.get("text") or "").strip()
    cmd = text.split()[0].split("@")[0].lower() if text else ""
    await handle_command(conn, config, chat, cmd, text[len(text.split()[0]):].strip() if text else "")


# The bot's menu (owner request 2026-11-19: "the menu like on the Bias Pointer bot")
COMMANDS = [("jobs", "Check for new jobs now"), ("review", "Jobs waiting for you"),
            ("applied", "Your applications in progress"), ("followups", "Follow-ups due now"),
            ("add", "Log an application: /add Title | Company | link"),
            ("ai", "AI training sites open to Nigeria"),
            ("tracker", "Open the Job Hunt page"), ("help", "How this bot works")]

# AI training / evaluation work is mostly sign-up on the platforms' own sites, not posted on job boards.
# Eligibility for Nigeria as checked 2026-11-19 (origindatapartners.com guide of 2026-11-14); it changes often.
AI_SITES = [
    ("micro1", "https://jobs.micro1.ai", "Nigerian English language expert: tagging and correcting transcripts. $15–45/hr, paid via Deel."),
    ("Mercor", "https://www.mercor.com", "Nigeria is on its supported list. AI expert and evaluation projects; weekly pay via Stripe or Wise."),
    ("Alignerr", "https://www.alignerr.com", "Says it welcomes applicants worldwide. AI training and evaluation tasks."),
    ("Welo Data", "https://jobs.lever.co/weloglobal", "Yoruba, Igbo and Hausa AI trainer pools, for native speakers in Nigeria."),
    ("CrowdGen (Appen)", "https://crowdgen.com", "Pays in 200+ countries. Data and search-evaluation projects; check each one."),
    ("OneForma", "https://www.oneforma.com", "Eligibility is per project. Language and data tasks."),
    ("DataAnnotation", "https://www.dataannotation.tech", "No country list published: try the starter test."),
]
AI_CLOSED = "Closed to Nigeria right now: Outlier, Mindrift (Toloka), Prolific."


def ai_sites_text() -> str:
    return ("🤖 <b>AI training work open to Nigeria</b>\nThese hire by sign-up on their own sites, not on job boards. "
            "Apply to each once with your AI CV, then log it with /add.\n\n"
            + "\n\n".join(f"<b><a href=\"{u}\">{html.escape(n)}</a></b>\n{html.escape(d)}" for n, u, d in AI_SITES)
            + f"\n\n{AI_CLOSED}\nRules change often: check each site's country list when you sign up.")


def help_text() -> str:
    return ("👋 <b>Job Hunt bot</b>\nYour remote job digest arrives here every morning at 08:30 WAT. Each job has "
            "Apply / ✅ Applied / ⏭ Skip buttons, and ✍️ Cover note gives you a ready cover note for that job to copy. "
            "7 days after you tap Applied, I ask how it went.\n\n"
            + "\n".join(f"/{c} · {d}" for c, d in COMMANDS)
            + "\n\nFor a tailored CV and cover letter, paste the job description to Claude.")


async def handle_command(conn, config, chat: str, cmd: str, arg: str = "") -> None:
    token = config.jobs_bot_token
    conn.row_factory = sqlite3.Row
    ensure_table(conn)
    now = datetime.now(timezone.utc)
    if cmd == "/jobs":
        await _send(token, chat, "🔎 Checking the job boards…")
        await run_job_digest(config.db_path, config)
    elif cmd == "/review":
        rows = [dict(r) for r in conn.execute("SELECT * FROM job_apps WHERE status = 'new' ORDER BY sent_at DESC LIMIT 10")]
        if not rows:
            await _send(token, chat, "Nothing waiting: every job sent has been marked Applied or Skipped. /jobs checks for new ones.")
        else:
            await _send(token, chat, f"📋 <b>{len(rows)} job{'s' if len(rows) != 1 else ''} waiting for you</b>")
            for r in rows:
                await _send(token, chat, job_text(r, now), job_buttons(r))
    elif cmd == "/applied":
        rows = [dict(r) for r in conn.execute(
            "SELECT * FROM job_apps WHERE status IN ('applied', 'followed_up', 'interview', 'offer') "
            "ORDER BY applied_at DESC LIMIT 30")]
        if not rows:
            await _send(token, chat, "No applications in progress yet. Tap ✅ Applied under a job when you apply.")
        else:
            lines = [f"• <b>{html.escape(r['title'])}</b>, {html.escape(r['company'])}: {STATUS_LABEL[r['status']]}"
                     + (f" (applied {datetime.fromisoformat(r['applied_at']).astimezone(WAT).strftime('%d %b')})"
                        if r.get("applied_at") else "") for r in rows]
            await _send(token, chat, f"📨 <b>Applications in progress ({len(rows)})</b>\n\n" + "\n".join(lines)
                        + "\n\n" + goal_line(conn))
    elif cmd == "/followups":
        rows = due_followups(conn, now)
        if not rows:
            await _send(token, chat, "No follow-ups due. I'll remind you 7 days after each application.")
        for r in rows:
            await _send(token, chat, follow_text(r), follow_buttons(r["id"]))
    elif cmd == "/add":
        parts = [p.strip() for p in arg.split("|")]
        if not parts or not parts[0]:
            await _send(token, chat, "Log an application you made anywhere (LinkedIn, Jobberman, Upwork, a company site):\n\n"
                                     "<code>/add Title | Company | link</code>\n\nExample:\n"
                                     "<code>/add QA Tester | Moniepoint | https://...</code>\n\nThe link is optional. "
                                     "For a Fiverr order or a freelance proposal, change the type on the Job Hunt page.")
        else:
            r = add_manual(conn, parts[0], parts[1] if len(parts) > 1 else "?", parts[2] if len(parts) > 2 else "")
            await _send(token, chat, f"✅ Logged: <b>{html.escape(r['title'])}</b> at {html.escape(r['company'])}. "
                                     f"I'll ask how it went in 7 days.\n\n{goal_line(conn)}")
    elif cmd == "/ai":
        await _send(token, chat, ai_sites_text())
    elif cmd == "/tracker":
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        url = f"{config.frontend_url.rstrip('/')}/job-hunt"
        await _send(token, chat, "Your Job Hunt page: every job, its status and your follow-ups.",
                    InlineKeyboardMarkup([[InlineKeyboardButton("Open Job Hunt ↗", url=url)]]))
    else:   # /start, /help, or any other text
        await _send(token, chat, help_text())


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
        from telegram import BotCommand, MenuButtonCommands
        await bot.set_my_commands([BotCommand(c, d) for c, d in COMMANDS])
        await bot.set_chat_menu_button(menu_button=MenuButtonCommands())
    except TelegramError as e:
        logger.warning("Job Hunt bot webhook could not be set: %s", e)

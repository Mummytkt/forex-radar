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
# Owner, 2026-11-21: "pause the job, let me put all my focus on business and trading". While True, the scheduled
# 08:30 digest, the 16:02 checklist nudge and the LinkedIn coach's scheduled posts don't send. Commands (/jobs,
# /links, /linkedin, /today ...) still work. Set False to resume.
JOB_HUNT_PAUSED = False   # True 2026-11-21 (business focus); back on 2026-11-22 for customer service & sales
MAX_PER_DAY = 25     # 15 until 2026-11-20; raised for her 15-20 applications a day
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

# Since 2026-11-22 (owner): customer service and sales roles only, in any niche (AI, tech, anything).
# Was QA / design / AI training before that.
TITLE = re.compile(
    r"\b(customer (service|support|success|care|experience|happiness|operations|onboarding|advocate|relations?)|"
    r"client (service|support|success|care|experience|relations?)|cx|"
    r"support (specialist|agent|associate|representative|rep|advocate|analyst|executive|officer|hero)|"
    r"technical support|tech support|help ?desk|service desk|call cent(er|re)|contact cent(er|re)|"
    r"live chat|chat (support|agent)|community support|onboarding (specialist|associate|coordinator)|"
    r"account (manager|executive|coordinator|associate)|"
    r"sales|sdr|bdr|business development|lead generation|appointment setter|telesales|telemarketing|"
    r"inside sales|retention (specialist|agent|associate)|partnerships? (associate|executive|specialist)|"
    r"order (support|processing)|e-?commerce (support|assistant))\b", re.I)
ENGINEER = re.compile(r"\bengineer\w*\b", re.I)
CODE_HEAVY = re.compile(r"\b(python|golang|java|kotlin|swift|rust|c\+\+|c#|\.net|sdet|automation|automated|"
                        r"distributed systems?|back[- ]?end|devops|software engineer\w*|developer in test)\b"
                        r"|/\s*go\b", re.I)
QA_WORD = re.compile(r"\b(qa|quality|test\w*)\b", re.I)
SENIOR = re.compile(r"\b(senior|sr\.?|lead|principal|head|director|staff|vp|chief|manager)\b", re.I)
REGION_TITLE = re.compile(r"\b(latam|americas?|north america|usa?|canada|apac|asia|west region|east region)\b", re.I)
NATIVE = re.compile(r"speakers? in|native (speaker|level)", re.I)
# Manager titles that are usually entry/mid level in customer roles (2026-11-22)
OK_MANAGER = re.compile(r"\b(customer success manager|account manager|client success manager)\b", re.I)
VERY_SENIOR = re.compile(r"\b(senior|sr\.?|lead|head|director|vp|principal|chief)\b", re.I)
# Customer/sales titles that name a single country, a US state or government work (2026-11-22, live check:
# "Account Executive - Enterprise, North Carolina", "... UK", "... Nordics", "Public Sector Germany"). A title that
# also names Nigeria, Africa, EMEA or worldwide still comes through.
PLACE_TITLE = re.compile(r"\b(uk|u\.k\.|united kingdom|britain|ireland|nordics?|dach|germany|france|spain|italy|"
                         r"netherlands|benelux|poland|australia|anz|new zealand|japan|india|singapore|brazil|mexico|"
                         r"federal|fed|public sector|government|state and local|sled|north carolina|texas|california|"
                         r"new york|florida|illinois|ohio|georgia|virginia|washington|massachusetts|colorado)\b", re.I)
OK_PLACE = re.compile(r"\b(nigeria|africa|emea|worldwide|global|anywhere)\b", re.I)
# Enterprise / strategic account executives and commission analysts: senior or not a selling role
NOT_ENTRY = re.compile(r"\b(strategics?|enterprise account executive|commissions?)\b|account executive.*enterprise", re.I)
# A non-English language in the title: the job is for speakers of it (she works in English, Yoruba, Pidgin)
OTHER_LANG = re.compile(r"\b(german|french|spanish|dutch|italian|portuguese|polish|swedish|danish|norwegian|finnish|"
                        r"czech|greek|turkish|arabic|hebrew|russian|ukrainian|japanese|korean|mandarin|chinese|"
                        r"cantonese|hindi|thai|vietnamese|indonesian|romanian|hungarian|bulgarian|croatian|serbian|"
                        r"slovak|slovenian|lithuanian|latvian|estonian|swahili|amharic|bilingual|multilingual)\b", re.I)
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
    cols = {r[1] for r in conn.execute("PRAGMA table_info(job_apps)")}
    if "kind" not in cols:
        conn.execute("ALTER TABLE job_apps ADD COLUMN kind TEXT NOT NULL DEFAULT 'job'")
    # contract / part-time / freelance / full-time, from the board (2026-11-21): contract work first
    if "job_type" not in cols:
        conn.execute("ALTER TABLE job_apps ADD COLUMN job_type TEXT NOT NULL DEFAULT ''")


# Job type (owner, 2026-11-21: contract and part-time first, to start earning fast; full-time still sent)
TYPE_LABEL = {"contract": "📄 Contract", "part_time": "⏱ Part-time", "freelance": "🧾 Freelance",
              "full_time": "💼 Full-time", "internship": "🎓 Internship", "": "❔ Type not given"}
TYPE_RANK = {"contract": 0, "part_time": 0, "freelance": 0, "": 1, "internship": 1, "full_time": 2}


def job_type(raw, title: str = "") -> str:
    """Normalise a board's job type (or, when it gives none, the title's words) to a TYPE_LABEL key."""
    s = (" ".join(raw) if isinstance(raw, (list, tuple)) else str(raw or "")).lower()
    for text in (s, title.lower()):
        if re.search(r"contract", text):
            return "contract"
        if re.search(r"part[\s_-]?time", text):
            return "part_time"
        if re.search(r"freelanc", text):
            return "freelance"
        if re.search(r"intern", text):
            return "internship"
        if text is s and re.search(r"full[\s_-]?time", text):
            return "full_time"
    return ""


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
    if not TITLE.search(title) or REGION_TITLE.search(title) or NATIVE.search(title) or OTHER_LANG.search(title):
        return None
    if (PLACE_TITLE.search(title) and not OK_PLACE.search(title)) or NOT_ENTRY.search(title):
        return None
    # "... Support / Success / Solutions / Sales Engineer" roles want coding: she asked to drop them (2026-11-20,
    # after RevenueCat's Developer Support Engineer).
    if ENGINEER.search(title):
        return None
    # Titles naming code-heavy work (2026-11-21, after Canonical's "Distributed Systems Testing Software Engineer,
    # Python / Go"): she does manual QA and React, not test automation or back-end languages yet.
    if CODE_HEAVY.search(title):
        return None
    if SENIOR.search(title) and not (OK_MANAGER.search(title) and not VERY_SENIOR.search(title)):
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

    def add(src, title, company, loc, when, url, desc="", jtype=None):
        if when is None or when < since or not url:
            return
        title, company = html.unescape(title or "").strip(), html.unescape(company or "").strip()
        region = classify(title, loc)
        if region:
            out.append({"source": src, "title": title, "company": company or "?", "location": (loc or "").strip() or "Worldwide",
                        "region": region, "posted_at": when.astimezone(timezone.utc).isoformat(), "url": url,
                        "_desc": desc or "", "job_type": job_type(jtype, title)})

    def utc(s):
        d = datetime.fromisoformat(s)
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)

    # Customer service & sales (2026-11-22): Remotive's two categories, plus searches for titles filed elsewhere
    for q in ("category=customer-support", "category=sales", "search=customer%20service", "search=customer%20success",
              "search=account%20executive", "search=business%20development", "search=sdr"):
        try:
            for j in json.loads(_get("https://remotive.com/api/remote-jobs?" + q))["jobs"]:
                add("Remotive", j["title"], j["company_name"], j.get("candidate_required_location"), utc(j["publication_date"]), j["url"], jtype=j.get("job_type"))
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
            add("Himalayas", j["title"], j["companyName"], ", ".join(j.get("locationRestrictions") or []), w, j.get("applicationLink"),
                jtype=j.get("employmentType"))
        cur, pages = d.get("nextCursor"), pages + 1
        if old >= 15 or not cur:
            break
    try:
        for it in ET.fromstring(_get("https://weworkremotely.com/remote-jobs.rss")).iter("item"):
            comp, _, title = (it.findtext("title") or "").partition(": ")
            add("We Work Remotely", title or comp, comp if title else "", it.findtext("region") or "",
                parsedate_to_datetime(it.findtext("pubDate")), it.findtext("link"), it.findtext("description") or "",
                jtype=it.findtext("type"))
    except Exception as e:
        logger.warning("Job feed We Work Remotely failed: %s", e)
    try:
        for j in json.loads(_get("https://jobicy.com/api/v2/remote-jobs?count=100"))["jobs"]:
            add("Jobicy", j["jobTitle"], j["companyName"], j.get("jobGeo") or "", utc(j["pubDate"]), j["url"], jtype=j.get("jobType"))
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
    # the same job on two boards: keep the free one (a paywalled board loses the tie)
    out.sort(key=lambda j: j["posted_at"], reverse=True)
    for j in sorted(out, key=lambda j: j["source"] in PAYWALLED):
        k = (j["title"].lower(), j["company"].lower())
        if k not in seen:
            seen.add(k)
            uniq.append(j)
    order = {"Nigeria": 0, "Africa": 1, "Worldwide": 2, "EMEA": 3}
    # AI jobs first within each region, so the daily cap never drops them
    # contract / part-time / freelance first (they start fastest), then by region; AI jobs first within those
    return sorted(uniq, key=lambda j: (TYPE_RANK[j["job_type"]], order[j["region"]], not is_ai(j["title"])))


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
            "INSERT INTO job_apps (url, source, title, company, location, region, posted_at, sent_at, updated_at, job_type) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (j["url"], j["source"], j["title"], j["company"], j["location"], j["region"], j["posted_at"],
             now.isoformat(), now.isoformat(), j.get("job_type", ""))).lastrowid
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
    return (f"{FLAG[j['region']]} {'🤖 <b>AI</b> · ' if is_ai(j['title']) else ''}<b>{html.escape(j['title'])}</b>\n"
            f"{html.escape(j['company'])} · {where} · {TYPE_LABEL.get(j.get('job_type') or '', TYPE_LABEL[''])}\n"
            f"Posted {_ago(j['posted_at'], now)} · {html.escape(j['source'])}\n"
            + SPEED_LABEL[form_speed(apply_link(j)[1])]
            + ("\n<i>We Work Remotely charges to apply, so the button opens this job on the company's own site (free).</i>"
               if j.get("source") in PAYWALLED else ""))


# We Work Remotely put applying behind a paid plan (seen 2026-11-20: Apply opens a $14.95/month, 12-month
# paywall). The same jobs are almost always on the company's own careers page, where applying is free, so for
# those jobs Apply opens a search for that page instead.
PAYWALLED = {"We Work Remotely"}
PAYWALL_HOSTS = ("weworkremotely.com",)
# Public job-board APIs of the hiring systems most companies use: {slug} is the company's account name.
ATS = [
    ("https://boards-api.greenhouse.io/v1/boards/{slug}/jobs", lambda d: [(x["title"], x["absolute_url"]) for x in d["jobs"]]),
    ("https://api.lever.co/v0/postings/{slug}?mode=json", lambda d: [(x["text"], x["hostedUrl"]) for x in d]),
    ("https://api.ashbyhq.com/posting-api/job-board/{slug}", lambda d: [(x["title"], x["jobUrl"]) for x in d["jobs"]]),
    ("https://apply.workable.com/api/v1/widget/accounts/{slug}", lambda d: [(x["title"], x["url"]) for x in d["jobs"]]),
]
ATS_HOSTS = ("greenhouse.io", "lever.co", "ashbyhq.com", "workable.com", "bamboohr.com", "recruitee.com",
             "teamtailor.com", "breezy.hr", "smartrecruiters.com", "personio", "jobvite.com", "rippling.com",
             "docs.google.com/forms")
_NOT_APPLY = ("eeoc.gov", "slack.com", "linkedin.com", "twitter.com", "x.com", "facebook.com", "instagram.com",
              "youtube.com", "glassdoor", "weworkremotely.com", "/blog")


def _norm(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()


def _slugs(company: str) -> list[str]:
    c = company.lower()
    c = re.sub(r"\b(inc|llc|ltd|gmbh|corp|co|the|hq)\b\.?", "", c)
    out = [re.sub(r"[^a-z0-9]", "", c), re.sub(r"[^a-z0-9]+", "-", c).strip("-"), (re.findall(r"[a-z0-9]+", c) or [""])[0]]
    return [s for i, s in enumerate(out) if s and s not in out[:i]]


def ducky_url(j: dict) -> str:
    """DuckDuckGo's '!ducky' jumps straight to the first result: one tap, no results page."""
    return "https://duckduckgo.com/?q=" + urllib.parse.quote_plus(f"!ducky {j['company']} {j['title']} careers apply")


def ats_lookup(j: dict) -> Optional[str]:
    """This job's own listing on the employer's hiring system (Greenhouse / Lever / Ashby / Workable), or None."""
    from difflib import SequenceMatcher
    if j.get("company") in (None, "", "?"):
        return None
    want = _norm(j["title"])
    for slug in _slugs(j["company"]):
        for api, parse in ATS:
            try:
                posts = parse(json.loads(urllib.request.urlopen(
                    urllib.request.Request(api.format(slug=slug), headers=UA), timeout=6).read()))
            except Exception:
                continue
            best = max(((SequenceMatcher(None, want, _norm(t)).ratio(), u) for t, u in posts if t and u), default=None)
            if best and best[0] >= 0.85:
                return best[1]
    return None


def direct_url(j: dict) -> str:
    """The job's own page at the employer, so applying is free: their hiring system's listing for this title,
    else an apply/careers link from the job's description, else a jump to the first search result."""
    found = ats_lookup(j)
    if found:
        return found
    links = [u.rstrip(".,);") for u in re.findall(r"https?://[^\s\"'<>]+", html.unescape(j.get("_desc") or ""))]
    links = [u for u in links if not any(b in u for b in _NOT_APPLY)]
    for u in links:
        if any(h in u for h in ATS_HOSTS):
            return u
    for u in links:
        if re.search(r"career|jobs|apply|join", u, re.I):
            return u
    return ducky_url(j)


def resolve_links(jobs: list[dict]) -> list[dict]:
    """Run in a worker thread (many web requests): point each job at the employer's own application form when it
    can be found, so Apply opens a short form the Simplify extension fills. Paywalled-board jobs whose free page
    can't be found are dropped (owner, 2026-11-20: every job must reach a free form)."""
    from concurrent.futures import ThreadPoolExecutor

    def one(j):
        if j["source"] in PAYWALLED:
            u = direct_url(j)
            return None if "duckduckgo.com" in u else {**j, "url": u}
        if form_speed(j["url"]) == "board":
            u = ats_lookup(j)
            if u:
                return {**j, "url": u}
        return j
    with ThreadPoolExecutor(max_workers=8) as ex:
        return [j for j in ex.map(one, jobs) if j]


# How long the application form behind a link takes (owner, 2026-11-20): short hosted forms first.
QUICK_HOSTS = ("greenhouse.io", "lever.co", "ashbyhq.com", "workable.com", "breezy.hr", "recruitee.com",
               "teamtailor.com", "bamboohr.com", "docs.google.com/forms", "jobs.micro1.ai")
SLOW_HOSTS = ("myworkdayjobs.com", "workday", "icims.com", "taleo", "successfactors", "oraclecloud.com",
              "smartrecruiters.com", "jobvite.com", "ultipro", "adp.com", "paylocity")
SPEED_LABEL = {"quick": "⚡ Quick form (~3 min with Simplify)", "slow": "🐢 Long form (~15 min)",
               "board": "📝 Opens the job board: tap Apply there"}


def form_speed(url: str) -> str:
    u = (url or "").lower()
    if any(h in u for h in SLOW_HOSTS):
        return "slow"
    if any(h in u for h in QUICK_HOSTS):
        return "quick"
    return "board"


def apply_link(j: dict) -> tuple[str, str]:
    """(button label, url) for the Apply button."""
    if j.get("source") in PAYWALLED:
        url = j.get("url", "")
        if any(h in url for h in PAYWALL_HOSTS):       # stored before this fix: jump to the first result instead
            url = ducky_url(j)
        return "Apply on company site ↗", url
    return "Apply ↗", j.get("url", "")


def job_buttons(j: dict, status: str = "new"):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    label, link = apply_link(j)
    row = [InlineKeyboardButton(label, url=link)]
    if status == "new":
        row += [InlineKeyboardButton("✅ Applied", callback_data=f"jb:a:{j['id']}"),
                InlineKeyboardButton("⏭ Skip", callback_data=f"jb:s:{j['id']}")]
    return InlineKeyboardMarkup([row, [InlineKeyboardButton("✍️ Cover note", callback_data=f"jb:c:{j['id']}")]])


# Cover notes: the same texts as the Customer Service & Sales Kit doc (CS_KIT, 2026-11-22). Filled with the job's
# title and company; the one sentence in [brackets] is hers to change. A template, not paid AI.
# Facts she confirmed: at Belrald she answered users' questions, handled complaints and bugs until fixed and ran
# demos/onboarding; she onboarded about 6 testers onto Bias Pointer and resolved their issues; English, Yoruba, Pidgin.
_NOTE_END = ("I'm based in Nigeria (WAT, UTC+1), I've worked remotely since 2022, and I can start immediately. "
             "My CV is attached, and my LinkedIn is linkedin.com/in/taiwo-damilola-mayowa-973710450. "
             "Thank you for your time.\n\nTaiwo Damilola Mayowa")
COVER_NOTES = {
    "support": ("I'm applying for the {role} position. For over two years at Belrald, an education software company, "
                "I answered questions from students, schools and staff, followed complaints and bug reports through "
                "until they were fixed, and walked new users through our portals. Since then I've onboarded testers "
                "onto a platform I built and resolved the issues they raised.\n\nBecause I also built and tested "
                "software, I can explain technical problems in plain words and give the product team reports they can "
                "act on. I work in English, Yoruba and Pidgin. "
                "[One sentence: why this company, or one requirement you match.]"),
    "sales": ("I'm applying for the {role} position. At Belrald, an education software company, I showed our product "
              "to new schools and users, answered their questions and handled their concerns, and I've since "
              "onboarded testers onto a platform I built. That taught me to ask what someone actually needs before "
              "showing them anything.\n\nI'm comfortable on calls, chat and email, I follow up when I say I will, "
              "and I keep clear notes. I speak English, Yoruba and Pidgin. "
              "[One sentence: why this company, or one requirement you match.]"),
}
SALES_TITLE = re.compile(r"\b(sales|sdr|bdr|business development|lead generation|appointment setter|telesales|"
                         r"telemarketing|account executive|partnerships?)\b", re.I)


def note_kind(title: str) -> str:
    return "sales" if SALES_TITLE.search(title) else "support"


def cover_note(j: dict) -> str:
    company = (j.get("company") or "").strip()
    hello = f"Hello {company} team," if company and company != "?" else "Hello,"
    return f"{hello}\n\n{COVER_NOTES[note_kind(j['title'])].format(role=j['title'].strip())}\n\n{_NOTE_END}"


def cover_note_message(j: dict) -> str:
    label = {"support": "Customer service", "sales": "Sales"}[note_kind(j["title"])]
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


async def run_job_digest(db_path: str, config, now: Optional[datetime] = None, scheduled: bool = False) -> int:
    """The morning digest: new jobs (each with its buttons), then the follow-up questions due. Returns jobs sent."""
    token = getattr(config, "jobs_bot_token", "")
    if not token or (scheduled and JOB_HUNT_PAUSED):
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
        # resolve only the unseen ones (a few spare, as unresolvable paywalled jobs get dropped), off the event loop
        unseen = [j for j in jobs if not conn.execute(
            "SELECT 1 FROM job_apps WHERE url = ? OR (lower(title) = ? AND lower(company) = ?)",
            (j["url"], j["title"].lower(), j["company"].lower())).fetchone()][:MAX_PER_DAY + 10]
        jobs = await asyncio.to_thread(resolve_links, unseen)
        new = store_new(conn, jobs, now)
        # contract / part-time / freelance first, then quick forms first within each
        new.sort(key=lambda j: (TYPE_RANK.get(j.get("job_type") or "", 1),
                                {"quick": 0, "board": 1, "slow": 2}[form_speed(apply_link(j)[1])]))
        day = now.astimezone(WAT).strftime("%a %d %b")
        follows = due_followups(conn, now)
        quick_start = sum(TYPE_RANK.get(j.get("job_type") or "", 1) == 0 for j in new)
        head = (f"💼 <b>Job digest · {day}</b>\n{len(new)} new remote job{'s' if len(new) != 1 else ''} for you"
                + (f" · {quick_start} contract / part-time / freelance first" if quick_start else "")
                + (f" · {len(follows)} follow-up{'s' if len(follows) != 1 else ''} to check" if follows else "")
                + ("\n\nTap Apply to open the post. Check where they hire before you apply: \"worldwide\" "
                   "is not always true. Aim for about 14 contract / part-time and 6 full-time applications a day."
                   if new else
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
        from alerts.job_checklist import send_checklist     # the day's checklist, once a day after the digest
        await send_checklist(conn, token, chat, _send, now.astimezone(WAT).date(), once=True)
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
        if owner and chat == owner and data.startswith("ck:"):
            from alerts.job_checklist import handle_callback as ck_callback
            reply = await ck_callback(conn, bot, cq, data)
        elif owner and chat == owner and data.startswith("li:"):
            from alerts.linkedin_coach import handle_callback
            reply = await handle_callback(conn, data)
            if reply:
                try:     # replace the buttons with the outcome, so the message shows it is done
                    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                    label = "⏭ Skipped" if data.endswith(":s") else ("✅ Posted" if ":morning:" in data else "✅ Done")
                    await bot.edit_message_reply_markup(chat_id=chat, message_id=cq["message"]["message_id"],
                                                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
                                                            label, callback_data="li:noop")]]))
                except TelegramError:
                    pass
        elif owner and chat == owner and data.startswith("jb:c:"):
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
COMMANDS = [("today", "Today's checklist: what to do next"),
            ("jobs", "Check for new jobs now"), ("review", "Jobs waiting for you"),
            ("applied", "Your applications in progress"), ("followups", "Follow-ups due now"),
            ("add", "Log an application: /add Title | Company | link"),
            ("ai", "AI training and paid testing sites"),
            ("links", "All your links and form answers to copy, and your Kits"),
            ("linkedin", "Today's LinkedIn post and tasks"),
            ("stats", "Log LinkedIn numbers: /stats views impressions connections"),
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
# Paid software testing (added 2026-11-21, her QA background). Not checked for Nigeria: she confirms at sign-up.
TEST_SITES = [
    ("uTest (Applause)", "https://www.utest.com", "Paid per approved bug and per test cycle. Free courses to start; "
                                                  "check it can pay you (Payoneer or PayPal) when you sign up."),
    ("Testlio", "https://testlio.com", "Freelance testers on real client apps, paid per hour. Check the "
                                       "country list when you apply."),
]


def ai_sites_text() -> str:
    return ("🤖 <b>AI training work open to Nigeria</b>\nThese hire by sign-up on their own sites, not on job boards. "
            "Apply to each once with your AI CV, then log it with /add.\n\n"
            + "\n\n".join(f"<b><a href=\"{u}\">{html.escape(n)}</a></b>\n{html.escape(d)}" for n, u, d in AI_SITES)
            + f"\n\n{AI_CLOSED}\nRules change often: check each site's country list when you sign up."
            + "\n\n🐞 <b>Paid software testing</b> (your QA background; sign up with your QA CV)\n\n"
            + "\n\n".join(f"<b><a href=\"{u}\">{html.escape(n)}</a></b>\n{html.escape(d)}" for n, u, d in TEST_SITES))


PORTFOLIO_URL = "https://taiwo-damilola-mayowa.vercel.app"
CV_URL = f"{PORTFOLIO_URL}/Taiwo-Damilola-Mayowa-CV-Support-Sales.pdf"   # customer service & sales CV (2026-11-22)
LINKEDIN_URL = "https://www.linkedin.com/in/taiwo-damilola-mayowa-973710450"


def portfolio_text() -> str:
    """Tap-to-copy details for filling application forms on the phone (owner-only chat, so the phone number is fine here)."""
    return ("🗂 <b>Your links and details for applications</b>\nTap any grey line to copy it, then paste it into the form.\n\n"
            f"Portfolio / website:\n<code>{PORTFOLIO_URL}</code>\n\n"
            f"LinkedIn:\n<code>{LINKEDIN_URL}</code>\n\n"
            f"CV (PDF link):\n<code>{CV_URL}</code>\n\n"
            "Email:\n<code>olaomidamilola@gmail.com</code>\n\n"
            "Phone:\n<code>+2349030281340</code>\n\n"
            "<b>Form answers</b>\n"
            "Full name: <code>Taiwo Damilola Mayowa</code>\n"
            "Location: <code>Ibadan, Nigeria</code>\n"
            "Time zone: <code>WAT (UTC+1)</code>\n"
            "Years of experience: <code>4+ in tech, 2+ with customers</code>\n"
            "Languages: <code>English (fluent), Yoruba (fluent), Nigerian Pidgin</code>\n"
            "Current role: <code>Product Designer &amp; QA Tester, Bias Pointer</code>\n"
            "Notice period: <code>Immediately</code>\n"
            "Expected salary: <code>$700 to $1,000 per month</code>\n"
            "Education: <code>B.A. Anthropology, University of Ibadan, 2019</code>\n"
            "Visa sponsorship: <code>No, remote from Nigeria</code>\n\n"
            "Where a form asks for a <b>portfolio, website or personal site</b>, paste the portfolio link. "
            "Where it asks you to <b>upload</b> a CV, use the PDF file; if it only takes a link, paste the CV link. "
            "Longer answers (about you, why this role) are in your Customer Service &amp; Sales Kit: button below.")


# One-tap LinkedIn searches (owner, 2026-11-21): remote, Easy Apply, last 24 h, newest first.
# geoIds checked 2026-11-21 on LinkedIn's public search: 91000007 = EMEA, 105365761 = Nigeria.
LI_EMEA, LI_NIGERIA = ("91000007", "EMEA"), ("105365761", "Nigeria")
LINKEDIN_SEARCHES = [("Customer service", "customer service", LI_EMEA),
                     ("Customer service · NG", "customer service", LI_NIGERIA),
                     ("Customer support", "customer support", LI_EMEA), ("Customer success", "customer success", LI_EMEA),
                     ("Sales rep", "sales representative", LI_EMEA), ("Sales · NG", "sales", LI_NIGERIA),
                     ("SDR / BDR", "sales development representative", LI_EMEA),
                     ("Business development", "business development", LI_EMEA)]


def linkedin_search_url(keywords: str, geo: tuple[str, str]) -> str:
    q = urllib.parse.urlencode({"keywords": keywords, "geoId": geo[0], "location": geo[1], "f_WT": "2",
                                "f_AL": "true", "f_TPR": "r86400", "sortBy": "DD"})
    return f"https://www.linkedin.com/jobs/search/?{q}"


def linkedin_search_rows() -> list:
    from telegram import InlineKeyboardButton
    btn = [InlineKeyboardButton(f"🔎 {label}", url=linkedin_search_url(kw, geo)) for label, kw, geo in LINKEDIN_SEARCHES]
    return [btn[i:i + 2] for i in range(0, len(btn), 2)]


QUICK_APPLY_KIT = "https://claude.ai/artifact/1z2XBM6Rp1fLS1Q8Kh3jmy"   # QA-era kit, kept for reference
CS_KIT = "https://claude.ai/artifact/U9gf968gRb5yEx7jCf5zFC"   # Customer Service & Sales Kit doc (2026-11-22)
LINKEDIN_KIT = "https://claude.ai/artifact/2HWhzAzEN6VpYcUqsY8Csb"


def links_markup(config):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    tracker = f"{config.frontend_url.rstrip('/')}/job-hunt"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Portfolio ↗", url=PORTFOLIO_URL),
         InlineKeyboardButton("CV ↗", url=CV_URL),
         InlineKeyboardButton("LinkedIn ↗", url=LINKEDIN_URL)],
        [InlineKeyboardButton("📋 Customer Service & Sales Kit", url=CS_KIT)],
        [InlineKeyboardButton("📊 Job Hunt tracker", url=tracker)]] + linkedin_search_rows())


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
    elif cmd == "/today":
        from alerts.job_checklist import send_checklist
        await send_checklist(conn, token, chat, _send)
    elif cmd in ("/linkedin", "/stats"):
        from alerts.linkedin_coach import handle_command as li_command
        await li_command(conn, token, chat, cmd, arg, _send)
    elif cmd in ("/links", "/portfolio"):     # /portfolio kept: it was the menu name until 2026-11-20
        await _send(token, chat, portfolio_text(), links_markup(config))
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

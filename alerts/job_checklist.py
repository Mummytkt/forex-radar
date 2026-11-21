"""Daily job-application checklist on the owner's Job Hunt bot (owner request 2026-11-20: "a daily checklist
for me to fill, so I don't forget what to do next").

Sent once a day right after the 08:30 WAT digest, again on /today, and at 16:02 WAT as a nudge only when steps
are left or she is under the day's target. Each step is a button that ticks itself (☐ → ☑); the message shows
how many applications she has logged today (✅ Applied taps and /add entries).
"""
from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta, timezone
from typing import Optional

WAT = timezone(timedelta(hours=1))
TARGET = 20      # her aim: 15-20 applications a day

STEPS = [
    ("quick", "⚡ Quick forms", "Do the ⚡ Quick form jobs first: open each, click Simplify's <b>Autofill This Page</b>, "
                              "answer the custom questions, submit."),
    ("board", "📝 Board jobs", "Then the 📝 board jobs: tap Apply on the board's page, then Autofill."),
    ("slow", "🐢 Long forms", "🐢 Long forms only for the jobs that fit you really well."),
    ("linkedin", "💼 LinkedIn Easy Apply", "LinkedIn: tap the 🔎 search buttons below (remote, Easy Apply, last 24 hours, "
                                          "already set). Apply where the location line says EMEA, Africa, Nigeria or "
                                          "worldwide; skip single-country jobs. Keep going until today's target."),
    ("logged", "✅ All logged", "Every application logged: ✅ Applied under bot jobs, <code>/add Title | Company | link</code> "
                               "for LinkedIn and other sites."),
    ("followups", "⏰ Follow-ups", "Answer any follow-up questions from the bot (or /followups)."),
]


def ensure_tables(conn) -> None:
    conn.execute("CREATE TABLE IF NOT EXISTS job_checklist (day TEXT, step TEXT, done INTEGER, PRIMARY KEY (day, step))")
    conn.execute("CREATE TABLE IF NOT EXISTS job_checklist_sent (day TEXT PRIMARY KEY)")
    conn.commit()


def wat_day(now: Optional[datetime] = None) -> date:
    return (now or datetime.now(timezone.utc)).astimezone(WAT).date()


def applied_today(conn, d: date) -> int:
    start = datetime(d.year, d.month, d.day, tzinfo=WAT).astimezone(timezone.utc)
    try:
        return conn.execute("SELECT COUNT(*) FROM job_apps WHERE applied_at >= ? AND applied_at < ?",
                            (start.isoformat(), (start + timedelta(days=1)).isoformat())).fetchone()[0]
    except sqlite3.OperationalError:      # no job_apps table yet
        return 0


def done_steps(conn, d: date) -> set:
    ensure_tables(conn)
    return {r[0] for r in conn.execute("SELECT step FROM job_checklist WHERE day = ? AND done = 1", (d.isoformat(),))}


def toggle(conn, d: date, step: str) -> None:
    ensure_tables(conn)
    cur = step in done_steps(conn, d)
    conn.execute("INSERT INTO job_checklist (day, step, done) VALUES (?, ?, ?) "
                 "ON CONFLICT(day, step) DO UPDATE SET done = excluded.done", (d.isoformat(), step, 0 if cur else 1))
    conn.commit()


def _bar(n: int) -> str:
    filled = min(10, round(10 * n / TARGET))
    return "▰" * filled + "▱" * (10 - filled)


def checklist_text(conn, d: date, nudge: bool = False) -> str:
    done = done_steps(conn, d)
    n = applied_today(conn, d)
    head = (f"⏳ <b>Still to do today</b>" if nudge else f"📋 <b>Today's job routine · {d.strftime('%a %d %b')}</b>")
    lines = [head, f"Applied today: <b>{n} / {TARGET}</b>  {_bar(n)}", ""]
    for i, (key, _, text) in enumerate(STEPS, 1):
        lines.append(f"{'☑' if key in done else '☐'} {i}. {text}")
    if len(done) == len(STEPS) and n >= TARGET:
        lines += ["", "🎉 All done for today. Rest well."]
    else:
        lines += ["", "Tap a step below when it's done. Tap 🔄 to update the count."]
    return "\n".join(lines)


def checklist_markup(conn, d: date):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    done = done_steps(conn, d)
    btn = [InlineKeyboardButton(("☑ " if k in done else "☐ ") + label, callback_data=f"ck:{d.isoformat()}:{k}")
           for k, label, _ in STEPS]
    rows = [btn[i:i + 2] for i in range(0, len(btn), 2)]
    rows.append([InlineKeyboardButton("🔄 Update count", callback_data=f"ck:{d.isoformat()}:refresh")])
    from alerts.job_digest import linkedin_search_rows     # one-tap LinkedIn searches (2026-11-21)
    return InlineKeyboardMarkup(rows + linkedin_search_rows())


def needs_nudge(conn, d: date) -> bool:
    return len(done_steps(conn, d)) < len(STEPS) or applied_today(conn, d) < TARGET


async def send_checklist(conn, token: str, chat: str, send, d: Optional[date] = None, nudge: bool = False,
                         once: bool = False) -> bool:
    """once=True: only the first time today (the digest calls it this way, so /jobs doesn't resend it)."""
    d = d or wat_day()
    ensure_tables(conn)
    if once and conn.execute("SELECT 1 FROM job_checklist_sent WHERE day = ?", (d.isoformat(),)).fetchone():
        return False
    ok = await send(token, chat, checklist_text(conn, d, nudge), checklist_markup(conn, d))
    if ok and once:
        conn.execute("INSERT OR IGNORE INTO job_checklist_sent (day) VALUES (?)", (d.isoformat(),))
        conn.commit()
    return ok


async def handle_callback(conn, bot, cq: dict, data: str) -> str:
    """ck:<day>:<step|refresh> → tick / untick, then redraw the message in place."""
    from telegram.error import TelegramError
    parts = data.split(":")
    if len(parts) != 3:
        return ""
    try:
        d = date.fromisoformat(parts[1])
    except ValueError:
        return ""
    if parts[2] != "refresh":
        if parts[2] not in {k for k, _, _ in STEPS}:
            return ""
        toggle(conn, d, parts[2])
    try:
        await bot.edit_message_text(chat_id=cq["message"]["chat"]["id"], message_id=cq["message"]["message_id"],
                                    text=checklist_text(conn, d), parse_mode="HTML",
                                    reply_markup=checklist_markup(conn, d), disable_web_page_preview=True)
    except TelegramError:
        pass     # "message is not modified" when nothing changed
    if parts[2] == "refresh":
        return f"{applied_today(conn, d)} applied today"
    return "Ticked ✓" if parts[2] in done_steps(conn, d) else "Unticked"


async def run_checklist_nudge(db_path: str, config, now: Optional[datetime] = None) -> bool:
    """Scheduled 16:02 WAT: the checklist again, only when something is left."""
    from alerts.job_digest import _send, owner_chat, JOB_HUNT_PAUSED
    token = getattr(config, "jobs_bot_token", "")
    if not token or JOB_HUNT_PAUSED:
        return False
    conn = sqlite3.connect(db_path, check_same_thread=False)
    try:
        chat = owner_chat(conn)
        d = wat_day(now)
        if not chat or not needs_nudge(conn, d):
            return False
        return await send_checklist(conn, token, chat, _send, d, nudge=True)
    finally:
        conn.close()

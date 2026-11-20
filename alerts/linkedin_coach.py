"""LinkedIn coach on the owner's Job Hunt bot (owner request 2026-11-20).

One post a day, Monday to Friday, plus tasks, from 23 Nov to 18 Dec 2026:
  - 08:00 WAT morning: the day's post to copy, its image, the first comment. Buttons: Posted / Skipped.
  - 13:05 WAT afternoon: comment + connect tasks (connection note to copy), and prep for tomorrow's post.
  - 19:00 WAT evening: reply to comments, and a preview of tomorrow.
  - Sunday 18:10 WAT: the weekly review (what was done, her logged LinkedIn numbers vs last week).
/linkedin shows today's messages any time; /stats views impressions connections logs the week's numbers.
The posts are the LinkedIn Kit doc's (claude.ai/artifact/2HWhzAzEN6VpYcUqsY8Csb): keep the two in sync.
Facts only: every claim is from her CV / portfolio. Bias Pointer's trading rules never appear.
"""
from __future__ import annotations

import html
import logging
import sqlite3
from datetime import date, datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)
WAT = timezone(timedelta(hours=1))
PORTFOLIO = "https://taiwo-damilola-mayowa.vercel.app"
FIRST_COMMENT = f"My portfolio, with a case study, a test plan and real bug reports: {PORTFOLIO}"
CONNECT_NOTE = ("Hi [Name], I'm a designer and QA tester looking to learn from people building great products. "
                "I'd love to connect and follow your work.")
SLOTS = ("morning", "afternoon", "evening")


def _e(s: str) -> str:
    """Escape for Telegram HTML; apostrophes and quotes stay plain so copied posts are clean."""
    return html.escape(s, quote=False)

_DESIGN_PREP = ("Prep for tomorrow's design post (20 minutes): open an app most people know (banking, food delivery, "
                "transport), screenshot one screen that confused you, then in Canva put 3 numbered red circles on the "
                "3 things you'd fix. Note your fix for each.")


def _post(title, image, text, prep=""):
    return {"title": title, "image": image, "text": text.strip(), "prep": prep}


DESIGN_TEMPLATE = """I use [app name] almost every day. Today I counted: [simple task] took me [number] taps.

As a designer and tester, here are 3 small changes I'd make:

1. [What's confusing] → [your fix]
2. [What's confusing] → [your fix]
3. [What's confusing] → [your fix]

None of these need a redesign. They just remove the moments where a user stops and thinks.

{closer}

{question}

#UXDesign #UIDesign #ProductDesign"""


def _design(focus, closer, question):
    return _post(f"Design fix: {focus}", "Your Canva markup (screenshot with 3 numbered red circles)",
                 DESIGN_TEMPLATE.format(closer=closer, question=question))


POSTS: dict[str, dict] = {
    # ---- Week 1 ----
    "2026-11-23": _post("Introduce yourself", "A screenshot of the top of your portfolio", """
I've spent 4+ years making software look right, work right, and stay right.

I started by building the student and admin portals for an education platform in React.
Then I moved into QA and tested the whole product before every release.
Since 2024 I've designed and tested my own live product, with 400+ automated checks guarding every release.

That mix taught me one thing:
most bugs are born in the gaps between design, code and testing.

I'm now looking for my next remote role in design, QA or AI evaluation.

If your team ships software and cares about getting it right, I'd love to connect.

What's the one bug you'll never forget?

#OpenToWork #QA #UIDesign"""),
    "2026-11-24": _post("Bug of the week: the alert that never fired", "None, text only", """
The alert worked for every currency pair. It never fired for oil.

The chart clearly showed price reaching the level. No message arrived.

I compared the alert's numbers with the chart, one by one.
The cause: oil uses a different price scale, and the alert was measuring distance with the currency setting.

The fix: fire when price reaches the level itself.
Then I re-tested on the same chart, and added it to my test plan so it can't quietly come back.

Lesson: test the edge cases your users care about, not just the common path.

What's an edge case that caught you out?

#QA #SoftwareTesting #BugReport""", prep=_DESIGN_PREP),
    "2026-11-25": _design("3 things I'd fix in an app", "Good design is invisible. You only notice it when it's missing.",
                          "Which app do you wish would fix one small thing?"),
    "2026-11-26": _post("What AI taught me about testing", "None, text only", """
AI wrote most of the code for my last project. My job was to catch where it was wrong.

The hardest bugs weren't crashes.
They were answers that looked right: confident, neat, and quietly incorrect.

What worked for me:
→ Write the rule in plain words before asking for any code
→ Check every result against real data, not against the AI's own explanation
→ When it's wrong, explain why, then re-test the fix

AI makes building faster.
It doesn't make testing optional.

How do you check AI's work?

#AI #QA #SoftwareTesting"""),
    "2026-11-27": _post("How I write a bug report", "A screenshot of a bug report from your portfolio (QA samples)", """
A bug report has one job: get the bug fixed without a single follow-up question.

Here's the format I use every time:

1. Title: what's broken, in one line
2. Steps: numbered, from a clean start
3. Expected: what should happen
4. Actual: what happened instead
5. Evidence: a screenshot or a screen recording

Then one more step most people skip:
re-test it after the fix, on the same steps.

A good report saves a developer an hour.
A vague one costs the whole team a day.

Testers, what would you add?

#QA #SoftwareTesting #BugReport"""),
    # ---- Week 2 ----
    "2026-11-30": _post("Anthropology to tech", "None, text only", """
I studied Anthropology. Now I design and test software.

People ask how those connect. Easily:

Anthropology is the study of how people actually behave, not how we assume they do.
Testing is finding where software meets real behaviour, and breaks.
Design is shaping software around that behaviour from the start.

The best bug reports I've written started with one question:
"What would a real person do here?"

What did you study, and how does it show up in your work today?

#UXDesign #QA #CareerChange"""),
    "2026-12-01": _post("Bug of the week: the off switch that didn't switch off", "None, text only", """
A user turns off a type of alert. The main alert stops. Its follow-up messages keep coming.

That was the bug.

The main alert checked the user's setting.
The follow-ups didn't: they never asked which alert they came from.

The fix: every follow-up now carries its parent alert's on/off switch.
And an automated check now guards it, so it stays fixed.

Lesson: when you test a setting, test everything that setting should control, not just the obvious part.

What's the sneakiest "it should have stopped" bug you've seen?

#QA #SoftwareTesting #BugReport""", prep=_DESIGN_PREP),
    "2026-12-02": _design("a sign-up form", "Every extra field is a reason to leave. Every unclear one is a support ticket.",
                          "What's the most annoying sign-up form you've filled in?"),
    "2026-12-03": _post("Write the rule before the code", "None, text only", """
The most useful testing I do happens before any code exists.

Before a feature is built, I write its rule in plain words:
→ What exactly should happen
→ When it should happen
→ When it should NOT happen

Then I ask: could two people read this and build two different things?
If yes, the rule isn't finished.

Half the bugs I've caught were really unclear requirements.
Fixing a sentence is cheaper than fixing a release.

Do you test the requirements, or only the product?

#QA #ProductManagement #SoftwareTesting"""),
    "2026-12-04": _post("6 things I test on every form", "None, text only", """
6 things I test on every form, before anything else:

1. Submit it empty
2. Paste a very long name (300+ characters)
3. Use an apostrophe and an emoji: O'Brien 😊
4. Paste an email with a space before or after it
5. Double-click the submit button
6. Press Back after submitting

Most forms pass the happy path.
These six find the bugs real users hit on day one.

What's on your list?

#QA #SoftwareTesting #ManualTesting"""),
    # ---- Week 3 ----
    "2026-12-07": _post("From building to testing", "None, text only", """
I built screens for a year. Then I moved into QA and started breaking them.

Best career move I've made.

Because I'd built the portals myself, I knew where developers cut corners under deadline, which screens were fragile, and what a useful bug report looks like from the other side.

My reports got shorter. Fixes got faster.

If you're a developer thinking about QA, or a tester thinking about learning to build: do it. Each side makes you better at the other.

Have you switched roles? What surprised you?

#QA #FrontendDevelopment #CareerGrowth"""),
    "2026-12-08": _post("Testing the edge: close vs touch", "None, text only", """
"Does the alert fire when price touches the level?" is an easy test.

The interesting tests sit right next to it:
→ Price touches the level exactly: one alert, within a minute
→ Price comes very close but doesn't touch: no alert
→ Price passes the level twice: still only one alert

That's boundary testing: bugs live at the edges, not in the middle.

The happy path tells you a feature works.
The edges tell you if you can trust it.

What boundary has surprised you lately?

#QA #SoftwareTesting #TestCases""", prep=_DESIGN_PREP),
    "2026-12-09": _design("an error message", "A good error message says what happened, why, and what to do next. In plain words.",
                          "What's the worst error message you've ever seen?"),
    "2026-12-10": _post("When AI is confidently wrong", "None, text only", """
The AI defined a rule for me. It read perfectly. It was wrong.

It had described a chart pattern in a way that sounded exactly right, but didn't match what the pattern really looks like on a chart.

I only caught it because I checked the result on real charts, not against the AI's explanation.

What I do now:
→ Never accept "it should work"
→ Test with real data, including the cases you expect to fail
→ Write down why it was wrong, so the next fix is right first time

AI is a fast junior. It still needs a reviewer.

#AI #QA #AIEvaluation"""),
    "2026-12-11": _post("Why fixed bugs come back", "None, text only", """
The most frustrating bug is the one you already fixed.

It comes back because something else changed, and nobody re-checked the old fix.

That's why I keep a growing set of automated checks: 400+ now, run before every release.

Each one asks a simple question:
"Is this still true?"

It takes minutes to run.
It saves the embarrassment of telling a user, "We fixed that last month."

How do you stop old bugs coming back?

#QA #RegressionTesting #SoftwareTesting"""),
    # ---- Week 4 ----
    "2026-12-14": _post("Remote since 2022: what works", "None, text only", """
I've worked remotely since 2022. Three habits made the biggest difference:

1. Write it down. A clear written update beats a quick call nobody remembers.
2. Hand over cleanly. Every task I pass on says what's done, what's left, and what I'm unsure about.
3. Overlap on purpose. From Nigeria I can work full UK and European hours, so I protect that shared time for questions and reviews.

Remote doesn't work because of tools.
It works because people make their work easy to pick up.

What's your best remote habit?

#RemoteWork #QA #Productivity"""),
    "2026-12-15": _post("Test when a feature should stop", "None, text only", """
We test when features start. We forget to test when they should stop.

On my alert platform, a price level stays active until a 4-hour candle closes beyond it.
So I tested the end, not just the start:
→ The candle closes beyond the level: the alert ends
→ After that: no more messages for that level, ever

A feature that never stops is a bug too, just a slower one.

What's a feature you've seen that didn't know when to stop?

#QA #SoftwareTesting #TestCases""", prep=_DESIGN_PREP),
    "2026-12-16": _design("a loading or empty screen", "Empty and loading screens are the first thing new users see. They deserve design too.",
                          "Which app handles waiting really well?"),
    "2026-12-17": _post("How I'd test a login page", "None, text only", """
"Just test the login page." Here's where I'd start:

1. Correct details: you're in
2. Wrong password: a clear message that doesn't say which part was wrong
3. Empty fields: can't submit
4. Caps Lock on: does it warn you?
5. Five wrong tries: is there a limit?
6. "Forgot password": does the email arrive, and does the link expire?
7. Back button after logout: you shouldn't see private pages
8. On a phone: does the keyboard cover the button?

The simplest page often hides the most important bugs.

What would you add?

#QA #SoftwareTesting #ManualTesting"""),
    "2026-12-18": _post("What a month of posting taught me", "None, text only", """
A month ago I started posting here every weekday. Here's what happened:

→ [Number] posts
→ [Number] new connections
→ [The post that did best, and why you think it did]

What surprised me: [one honest sentence].

What I'm taking into the new year: [one sentence].

Thank you to everyone who commented, shared, or sent a kind message. It made a real difference.

What did you learn this year?

#OpenToWork #QA #UIDesign"""),
}
LAST_DAY = max(POSTS)


def ensure_tables(conn) -> None:
    conn.execute("CREATE TABLE IF NOT EXISTS linkedin_log (day TEXT, slot TEXT, status TEXT, at TEXT, "
                 "PRIMARY KEY (day, slot))")
    conn.execute("CREATE TABLE IF NOT EXISTS linkedin_stats (week TEXT PRIMARY KEY, views INTEGER, impressions INTEGER, "
                 "connections INTEGER, at TEXT)")
    conn.commit()


def wat_today(now: Optional[datetime] = None) -> date:
    return (now or datetime.now(timezone.utc)).astimezone(WAT).date()


def week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _next_post_day(d: date) -> Optional[date]:
    for i in range(1, 8):
        n = d + timedelta(days=i)
        if n.isoformat() in POSTS:
            return n
    return None


def _buttons(day: str, slot: str):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    if slot == "morning":
        row = [InlineKeyboardButton("✅ Posted", callback_data=f"li:{day}:morning:d"),
               InlineKeyboardButton("⏭ Skipped", callback_data=f"li:{day}:morning:s")]
    else:
        row = [InlineKeyboardButton("✅ Done", callback_data=f"li:{day}:{slot}:d")]
    return InlineKeyboardMarkup([row])


def morning_text(d: date) -> Optional[str]:
    p = POSTS.get(d.isoformat())
    if not p:
        return None
    return (f"☀️ <b>LinkedIn · {d.strftime('%a %d %b')} · today's post</b>\n<b>{_e(p['title'])}</b>\n\n"
            f"1. Post at <b>9am</b>. Tap the box below to copy it."
            + ("\n2. Fill in the [brackets] first." if "[" in p["text"] else "")
            + f"\n{'3' if '[' in p['text'] else '2'}. Image: {_e(p['image'])}"
            f"\n{'4' if '[' in p['text'] else '3'}. Straight after posting, add the first comment (tap to copy):\n"
            f"<code>{_e(FIRST_COMMENT)}</code>\n"
            f"Stay for the first hour and reply to every comment.\n\n<pre>{_e(p['text'])}</pre>")


def afternoon_text(d: date) -> Optional[str]:
    if d.weekday() > 4:
        return None
    p = POSTS.get(d.isoformat())
    lines = [f"🤝 <b>LinkedIn · afternoon tasks · {d.strftime('%a %d %b')}</b>",
             "",
             "☐ <b>5 comments</b> on posts by QA leads, designers or recruiters. Two sentences or more: agree and add "
             "something from your own work, or ask a real question.",
             "☐ <b>5 connection requests</b> with a note (tap to copy, change [Name]):",
             f"<code>{_e(CONNECT_NOTE)}</code>"]
    if p and p.get("prep"):
        lines += ["", f"☐ <b>Prep:</b> {_e(p['prep'])}"]
    return "\n".join(lines)


def evening_text(d: date) -> Optional[str]:
    if d.weekday() > 4:
        return None
    lines = [f"🌙 <b>LinkedIn · evening · {d.strftime('%a %d %b')}</b>", "",
             "☐ Reply to every comment on today's post",
             "☐ Accept new connection requests, and thank anyone who commented"]
    n = _next_post_day(d)
    if n:
        lines += ["", f"Next post ({n.strftime('%a %d %b')}): <b>{_e(POSTS[n.isoformat()]['title'])}</b>"]
        if "[" in POSTS[n.isoformat()]["text"]:
            lines.append("It has [brackets] to fill in: have your notes ready.")
    elif d.isoformat() >= LAST_DAY:
        lines += ["", "That was the last planned post. Ask Claude for next month's posts, based on what worked."]
    return "\n".join(lines)


SLOT_TEXT = {"morning": morning_text, "afternoon": afternoon_text, "evening": evening_text}


def log(conn, day: str, slot: str, status: str, now: Optional[datetime] = None) -> None:
    ensure_tables(conn)
    conn.execute("INSERT INTO linkedin_log (day, slot, status, at) VALUES (?, ?, ?, ?) "
                 "ON CONFLICT(day, slot) DO UPDATE SET status = excluded.status, at = excluded.at",
                 (day, slot, status, (now or datetime.now(timezone.utc)).isoformat()))
    conn.commit()


def save_stats(conn, d: date, views: int, impressions: int, connections: int) -> str:
    ensure_tables(conn)
    wk = week_start(d).isoformat()
    conn.execute("INSERT INTO linkedin_stats (week, views, impressions, connections, at) VALUES (?, ?, ?, ?, ?) "
                 "ON CONFLICT(week) DO UPDATE SET views = excluded.views, impressions = excluded.impressions, "
                 "connections = excluded.connections, at = excluded.at",
                 (wk, views, impressions, connections, datetime.now(timezone.utc).isoformat()))
    conn.commit()
    return wk


def _stats_lines(conn, wk: date) -> list[str]:
    cur = conn.execute("SELECT views, impressions, connections FROM linkedin_stats WHERE week = ?",
                       (wk.isoformat(),)).fetchone()
    prev = conn.execute("SELECT views, impressions, connections FROM linkedin_stats WHERE week = ?",
                        ((wk - timedelta(days=7)).isoformat(),)).fetchone()
    if not cur:
        return ["📈 No numbers logged yet this week. Open LinkedIn → your profile → <b>Analytics</b>, then send:",
                "<code>/stats views impressions new-connections</code>  e.g. <code>/stats 45 1200 18</code>"]

    def fmt(name, i):
        s = f"{name}: <b>{cur[i]}</b>"
        if prev and prev[i] is not None:
            diff = cur[i] - prev[i]
            s += f" ({'+' if diff >= 0 else ''}{diff} vs last week)"
        return s
    return ["📈 " + " · ".join([fmt("Profile views", 0), fmt("Post impressions", 1), fmt("New connections", 2)])]


def review_text(conn, d: date) -> str:
    """The Sunday review of the week ending on d (any day of that week works)."""
    ensure_tables(conn)
    wk = week_start(d)
    days = [(wk + timedelta(days=i)).isoformat() for i in range(5)]
    post_days = [x for x in days if x in POSTS]
    rows = conn.execute(f"SELECT day, slot, status FROM linkedin_log WHERE day IN ({','.join('?' * len(days))})",
                        days).fetchall()
    done = {(r[0], r[1]) for r in rows if r[2] == "d"}
    posted = sum((x, "morning") in done for x in post_days)
    aft = sum((x, "afternoon") in done for x in days)
    eve = sum((x, "evening") in done for x in days)
    lines = [f"📊 <b>LinkedIn weekly review · week of {wk.strftime('%d %b')}</b>", "",
             f"Posts published: <b>{posted}/{len(post_days)}</b>" if post_days else "No posts were planned this week.",
             f"Comment + connect tasks: <b>{aft}/5</b>",
             f"Evening replies: <b>{eve}/5</b>", ""]
    lines += _stats_lines(conn, wk)
    missed = [POSTS[x]["title"] for x in post_days if (x, "morning") not in done]
    if missed:
        lines += ["", "Not posted this week (swap one in on a day the planned post doesn't suit you):"]
        lines += [f"• {_e(t)}" for t in missed]
    nxt = [(wk + timedelta(days=7 + i)) for i in range(5)]
    nxt = [n for n in nxt if n.isoformat() in POSTS]
    if nxt:
        lines += ["", "<b>Next week</b>"] + [f"{n.strftime('%a')}: {_e(POSTS[n.isoformat()]['title'])}" for n in nxt]
    else:
        lines += ["", "That's the end of the planned posts. Send Claude this review and your best post, and ask for "
                      "the next month."]
    lines += ["", "Tip: send Claude a screenshot of your best post's numbers; we'll do more of what works."]
    return "\n".join(lines)


def owner_chat(conn) -> Optional[str]:
    r = conn.execute("SELECT telegram_chat_id FROM users WHERE role = 'OWNER' AND telegram_chat_id IS NOT NULL "
                     "AND telegram_chat_id != '' LIMIT 1").fetchone()
    return str(r[0]) if r else None


async def send_slot(conn, token: str, chat: str, d: date, slot: str, send) -> bool:
    text = SLOT_TEXT[slot](d)
    if not text:
        return False
    return await send(token, chat, text, _buttons(d.isoformat(), slot))


async def run_linkedin_slot(db_path: str, config, slot: str, now: Optional[datetime] = None) -> bool:
    """Scheduled: the morning / afternoon / evening message for today (WAT), if there is one."""
    from alerts.job_digest import _send
    token = getattr(config, "jobs_bot_token", "")
    if not token:
        return False
    conn = sqlite3.connect(db_path, check_same_thread=False)
    try:
        ensure_tables(conn)
        chat = owner_chat(conn)
        if not chat:
            return False
        return await send_slot(conn, token, chat, wat_today(now), slot, _send)
    finally:
        conn.close()


async def run_linkedin_review(db_path: str, config, now: Optional[datetime] = None) -> bool:
    """Scheduled every Sunday evening: the week's review."""
    from alerts.job_digest import _send
    token = getattr(config, "jobs_bot_token", "")
    if not token:
        return False
    d = wat_today(now)
    if d.isoformat() < min(POSTS) or (d - timedelta(days=7)).isoformat() > LAST_DAY:
        return False
    conn = sqlite3.connect(db_path, check_same_thread=False)
    try:
        chat = owner_chat(conn)
        return bool(chat) and await _send(token, chat, review_text(conn, d))
    finally:
        conn.close()


async def handle_callback(conn, data: str) -> str:
    """li:<day>:<slot>:<d|s> → logged. Returns the toast text."""
    parts = data.split(":")
    if len(parts) != 4 or parts[2] not in SLOTS or parts[3] not in ("d", "s"):
        return ""
    log(conn, parts[1], parts[2], parts[3])
    if parts[2] == "morning":
        return "Posted! Stay for the first hour and reply to comments." if parts[3] == "d" else "Skipped. Tomorrow's a new post."
    return "Done. Nice work."


async def handle_command(conn, token: str, chat: str, cmd: str, arg: str, send) -> None:
    d = wat_today()
    if cmd == "/linkedin":
        sent = False
        for slot in SLOTS:
            sent |= await send_slot(conn, token, chat, d, slot, send)
        if not sent:
            n = _next_post_day(d)
            await send(token, chat, "🗓 No LinkedIn tasks today (weekend). Rest, and reply to any comments."
                       + (f"\n\nNext post: <b>{n.strftime('%a %d %b')}</b>, {_e(POSTS[n.isoformat()]['title'])}."
                          if n else ""))
    elif cmd == "/stats":
        nums = [x for x in arg.replace(",", " ").split() if x.isdigit()]
        if len(nums) != 3:
            await send(token, chat, "Log this week's LinkedIn numbers (from your profile → Analytics):\n\n"
                                    "<code>/stats views impressions new-connections</code>\n\nExample: "
                                    "<code>/stats 45 1200 18</code>")
            return
        wk = save_stats(conn, d, *map(int, nums))
        await send(token, chat, "Saved for the week of "
                   + datetime.fromisoformat(wk).strftime("%d %b") + ".\n" + "\n".join(_stats_lines(conn, date.fromisoformat(wk))))

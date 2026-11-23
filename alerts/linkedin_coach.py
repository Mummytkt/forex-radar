"""LinkedIn coach on the owner's Job Hunt bot (owner request 2026-11-20).

One post a day, Monday to Friday, plus tasks, from 23 Nov to 18 Dec 2026:
  - 08:00 WAT morning: the day's post to copy, its image, the first comment. Buttons: Posted / Skipped.
  - 13:05 WAT afternoon: comment + connect tasks (connection note to copy), and prep for tomorrow's post.
  - 19:00 WAT evening: reply to comments, and a preview of tomorrow.
  - Sunday 18:10 WAT: the weekly review (what was done, her logged LinkedIn numbers vs last week).
/linkedin shows today's messages any time; /stats views impressions connections logs the week's numbers.
The posts are the Customer Service & Sales Kit doc's (CS_KIT in job_digest.py): keep the two in sync.
Since 2026-11-23 the posts position her as an expert across QA, design, support and sales, never as a job
seeker (owner: "screaming I am looking for a job is just another noise"); the morning message also links to
LinkedIn's top posts per pillar so she can write her own versions.
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
CV_URL = f"{PORTFOLIO}/Taiwo-Damilola-Mayowa-CV-Support-Sales.pdf"
# Owner, 2026-11-23: no "I'm looking for a job" anywhere. Position as an expert; the bio does the rest.
FIRST_COMMENT = "One more thing that didn't fit in the post: [one extra tip or example]. What would you add?"
CONNECT_NOTE = ("Hi [Name], your [post/comment] on [topic] stayed with me, especially [one point]. I work across QA, product "
                "design and customer support, so I'd like to keep learning from your posts.")
# One-tap LinkedIn searches for the most relevant (top) posts of the last day / week, per pillar.
PILLARS = [("🧪 QA & testing", '"software testing" OR "quality assurance" OR QA'),
           ("🎨 Design & UX", '"product design" OR "UX design" OR "UI design"'),
           ("🤝 Support & CX", '"customer support" OR "customer experience" OR "customer success"'),
           ("💼 Sales", '"sales tips" OR "B2B sales" OR SDR')]


def li_search(query: str, period: str) -> str:
    from urllib.parse import quote
    return (f"https://www.linkedin.com/search/results/content/?keywords={quote(query)}"
            f"&datePosted=%22{period}%22&sortBy=%22relevance%22")


def trending_lines() -> list[str]:
    lines = ["🔥 <b>What's working on LinkedIn</b> (top posts, tap to open)"]
    lines += [f"• {label}: <a href=\"{_e(li_search(q, 'past-24h'))}\">last 24h</a> · "
              f"<a href=\"{_e(li_search(q, 'past-week'))}\">this week</a>" for label, q in PILLARS]
    lines += ["<i>Pick one that has lots of comments. Note its first line, its shape (list, story, hot take) and "
              "the question it ends on. Then write your own version from your QA, design or support work. Never "
              "copy the words.</i>"]
    return lines
SLOTS = ("morning", "afternoon", "evening")


def _e(s: str) -> str:
    """Escape for Telegram HTML; apostrophes and quotes stay plain so copied posts are clean."""
    return html.escape(s, quote=False)

def _post(title, image, text, prep=""):
    return {"title": title, "image": image, "text": text.strip(), "prep": prep}


# Customer service & sales month (owner, 2026-11-22: job search is now customer service and sales roles, any niche).
# Facts only, from what she confirmed: at Belrald (remote, 2022-2024) she answered user questions, handled complaints
# and bugs until fixed, and ran demos/onboarding; she onboarded about 6 testers onto Bias Pointer and resolved their
# issues; she works in English, Yoruba and Pidgin; B.A. Anthropology. The food business has NOT started: no stories
# from it until it has. Examples in quotes are labelled as examples, never as things a customer said.
POSTS: dict[str, dict] = {
    # ---- Week 1 ----
    "2026-11-23": _post("The bug report that gets fixed today", "None, text only", """
A bug report that says "the app is broken" gets ignored.

A bug report that gets fixed the same day has four things:

1. Steps: exactly what you tapped, in order.
2. Expected: what should have happened.
3. Actual: what happened instead.
4. Proof: a screenshot or a 10-second screen recording.

Developers aren't ignoring your bug. They just can't see what you saw.

Write it so they can, and it moves to the top of the pile.

What's the vaguest bug report you've ever received?

#QA #SoftwareTesting"""),
    "2026-11-24": _post("\"Sorry for the inconvenience\"", "None, text only", """
"Sorry for the inconvenience."

Most customers have read that line so many times it means nothing.

When someone writes in upset, they want to know three things:
Did you understand my problem?
What happens now?
When will I hear from you again?

The replies that calm people down aren't the most polite ones. They're the most specific ones.

Something like: "I can see your result isn't showing. I've passed it to the team and I'll update you by 3pm."

Then you update them by 3pm. Even if it isn't fixed yet.

What's the worst support reply you've ever received?

#CustomerService #CustomerExperience"""),
    "2026-11-25": _post("Testing trained me for support", "None, text only", """
I spent a year as a software tester before I noticed I was training for customer support.

A tester's job: reproduce the problem, describe it so someone else can see it, and follow it until it's fixed.

A support agent does the same thing. With a frustrated person on the other end.

So when a customer says "it's not working", I start with a tester's three questions:
1. What were you trying to do?
2. What did you expect to happen?
3. What happened instead?

Most of the time, those three answers make the problem clear. And the customer feels heard, because you asked instead of guessing.

#CustomerSupport #CustomerService"""),
    "2026-11-26": _post("One problem, three languages", "None, text only", """
I can walk someone through a password reset in English, Yoruba or Pidgin.

It lands differently in each.

A lot of us switch languages in the middle of a sentence. When the person helping you switches with you, you relax, and you explain the real problem instead of the polite version.

If your customers are in Nigeria or West Africa, support that speaks like them isn't a nice extra. It's how you hear what's actually going wrong.

Do you switch languages when you talk to customers?

#CustomerService #Nigeria #CustomerExperience"""),
    "2026-11-27": _post("Onboarding new users: what I'd tell anyone", "None, text only", """
I once onboarded six testers onto a product I built, one by one.

If you're onboarding new users, here's what I'd tell you:

1. Nobody reads a long welcome message. Short beats complete.
2. The first problem shows up in the first ten minutes. Be around then.
3. "It doesn't work" often means "I couldn't find where to tap". Ask before you assume a bug.
4. When someone takes time to report a problem, thank them, and tell them when it's fixed.

Onboarding isn't a document. It's the first few conversations.

What made a product easy for you to start using?

#CustomerSuccess #Onboarding"""),
    # ---- Week 2 ----
    "2026-11-30": _post("Anthropology and customer service", "None, text only", """
My degree is in Anthropology, from the University of Ibadan.

People ask what that has to do with customer service. More than you'd think.

Anthropology trains you to watch what people do, not only what they say.

A customer writes: "Your app is too slow."
That might mean their network is weak and the page keeps timing out.
It might mean they couldn't find the button and gave up.
It might mean something else happened today and this was the last straw.

Same sentence. Three different fixes.

Good support listens for the problem behind the first sentence.

#CustomerExperience #CustomerService"""),
    "2026-12-01": _post("Sales isn't pushing", "None, text only", """
I used to think sales meant pushing.

Then I started showing our product to schools at Belrald.

Walking someone through every feature didn't help them decide anything. What helped was asking first: "What's taking up your staff's time right now?"

Then showing only the part that fixed that.

Good selling is helping someone make a decision they'll still be happy with in six months.

If they won't be, it's better to say so.

#Sales #CustomerSuccess"""),
    "2026-12-02": _post("The follow-up is the job", "None, text only", """
Most sales don't happen on the first message.
Most problems don't get solved in the first reply.

The follow-up is where the work actually happens.

A habit that helps: when you tell someone "I'll get back to you", put the time in your calendar while you're still talking to them.

Then get back to them at that time. Even if all you can say is "still working on it".

People forgive slow. They don't forgive forgotten.

#Sales #CustomerService"""),
    "2026-12-03": _post("Write for the bus, not the desk", "None, text only", """
Write support replies for someone reading on a small phone, on a bus, at the end of a long day.

That means:
Short paragraphs.
One step per line.
The exact name of the button, the way it appears on their screen.
No links to a 20-page help article when two lines will do.

A reply that's easy to read gets followed. A reply that's hard to read becomes a second ticket.

#CustomerSupport #Writing"""),
    "2026-12-04": _post("Complaints are free research", "None, text only", """
A complaint is a customer telling you, for free, exactly where your product loses people.

As a software tester, I'd spend hours hunting for problems that real users found in five minutes.

So angry messages aren't noise to me. They're data.

Good support teams log them, group them, and send the patterns to the product team with real examples.

That's how a support team stops answering the same question 50 times a week.

#CustomerExperience #CustomerSupport"""),
    # ---- Week 3 ----
    "2026-12-07": _post("Questions before answers", "None, text only", """
The questions I like to ask before I explain anything:

In support:
What were you trying to do?
What have you tried already?
Which device or browser are you on?

In sales:
What made you start looking now?
What happens if you don't fix this?
Who else needs to be happy with the decision?

Asking first feels slower. It's actually faster, because you answer the right question the first time.

What's your go-to first question?

#Sales #CustomerService"""),
    "2026-12-08": _post("\"User error\"", "None, text only", """
"User error" is often a design problem with a different name.

When I was testing software, if three people tapped the wrong button, that wasn't three mistakes. That was one unclear button.

Support teams sit closest to this. You see the same confusion again and again before anyone else does.

Telling a customer "you did it wrong" closes the ticket.
Telling the product team "people keep doing this" fixes it for everyone.

#CustomerSupport #UX"""),
    "2026-12-09": _post("Same message, different tone", "None, text only", """
Same message. Different tone.

"You need to update the app."
"Updating the app should fix this. It takes about a minute."

"That's not possible."
"We can't do that one, but here's what we can do."

"As I said earlier..."
"Just to make sure we're on the same page..."

In writing, nobody hears your voice. Your word choice is your voice.

Which phrases do you avoid with customers?

#CustomerService #Communication"""),
    "2026-12-10": _post("Saying no well", "None, text only", """
Sometimes the answer is no.

The feature doesn't exist. The refund isn't possible. The deadline can't move.

A good no has three parts:
1. Say it early. Don't make someone read four paragraphs to find it.
2. Say why, in one line.
3. Offer the closest yes you can.

People can accept a no. What they don't accept is being left to guess.

#CustomerService #CustomerExperience"""),
    "2026-12-11": _post("Design feedback that starts fixes", "None, text only", """
"I don't like it" is the least useful design feedback there is.

"When I land here, I'm not sure what to do first" is one of the most useful.

Feedback about taste starts arguments. Feedback about what a person is trying to do starts fixes.

Three questions I ask about any screen:

What is the one thing someone came here to do?
Can they find it in three seconds?
What happens if they tap the wrong thing?

If a screen answers those, the colours are the easy part.

What's the best design feedback you've ever been given?

#ProductDesign #UX"""),
    # ---- Week 4 ----
    "2026-12-14": _post("Remote since 2022", "None, text only", """
I've worked remotely since 2022.

For customer-facing work, remote means:

Be reachable at the times you said you would be.
Write things down, so the next person doesn't start from zero.
When you hand a customer over, hand over the whole story, not just the ticket number.
Over-communicate. Silence feels longer online.

Customers don't care where you're sitting. They care that someone has their back.

#RemoteWork #CustomerService"""),
    "2026-12-15": _post("AI in customer service", "None, text only", """
AI can answer "how do I reset my password?" at 3am. Good.

What it can't do well yet: notice that the same customer has written three times this week and is about to leave.

I've spent the last two years building with AI tools and checking their answers. They're useful, and they can be confidently wrong.

The best setup I can picture: AI handles the simple, repeated questions. People handle the moments that decide whether a customer stays.

Where do you draw the line?

#AI #CustomerService #CustomerExperience"""),
    "2026-12-16": _post("Fast reply vs right reply", "None, text only", """
A fast first reply is nice.
A first reply that solves the problem is better.

"Thanks for reaching out, we're looking into it" in 2 minutes, then nothing for two days, isn't great service.

A reply in 20 minutes that fixes it is.

Speed matters. But the number that customers remember is how many times they had to explain themselves.

#CustomerSupport #CustomerExperience"""),
    "2026-12-17": _post("\"It's too expensive\"", "None, text only", """
"It's too expensive" rarely means the price is too high.

Often it means:
"I don't see enough value yet."
"I can't justify it to my boss."
"Now isn't the right time."

Each of those needs a different answer, and none of them is a discount.

A simple question helps: "Too expensive compared to what?"

Then listen.

#Sales #SalesTips"""),
    "2026-12-18": _post("One thread through testing, design and support", "None, text only", """
I've posted every weekday for a month about customers, testing and design.

What surprised me most: [one thing you learnt or noticed this month].

The post that got the most replies was [which one], I think because [your guess].

The thread through all of it: whether you're testing an app, designing a screen or answering a customer, the job is the same. Make sure what reaches people actually works for them.

Thank you for reading and replying. What should I write about next month?

#CustomerExperience #QA #ProductDesign"""),
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
        if d.weekday() > 4:
            return None
        return (f"☀️ <b>LinkedIn · {d.strftime('%a %d %b')}</b>\nNo ready post today: write your own version of one "
                f"that's working.\n\n" + "\n".join(trending_lines()))
    return (f"☀️ <b>LinkedIn · {d.strftime('%a %d %b')} · today's post</b>\n<b>{_e(p['title'])}</b>\n"
            f"<i>Or post your own version of a top post instead (links at the bottom).</i>\n\n"
            f"1. Post at <b>9am</b>. Tap the box below to copy it."
            + ("\n2. Fill in the [brackets] first." if "[" in p["text"] else "")
            + f"\n{'3' if '[' in p['text'] else '2'}. Image: {_e(p['image'])}"
            f"\n{'4' if '[' in p['text'] else '3'}. Straight after posting, add a first comment that gives a bit "
            f"more value (tap to copy, fill the [brackets]):\n"
            f"<code>{_e(FIRST_COMMENT)}</code>\n"
            f"Stay for the first hour and reply to every comment.\n\n<pre>{_e(p['text'])}</pre>\n\n"
            + "\n".join(trending_lines()))


def afternoon_text(d: date) -> Optional[str]:
    if d.weekday() > 4:
        return None
    p = POSTS.get(d.isoformat())
    lines = [f"🤝 <b>LinkedIn · afternoon tasks · {d.strftime('%a %d %b')}</b>",
             "",
             "☐ <b>5 smart comments</b> on top posts in QA, design, support or sales (use the morning links). Be "
             "early: comment within the post's first hours. 2–4 sentences: add a real example from your work, a "
             "different angle, or a sharp question. Never just \"Great post\".",
             "☐ <b>5 connection requests</b> to people who left good comments on those posts (they're active), "
             "or who wrote them. Send with a note (tap to copy, fill the [brackets]):",
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
    from alerts.job_digest import _send     # NOT paused with the job hunt since 2026-11-23: visibility is the plan
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

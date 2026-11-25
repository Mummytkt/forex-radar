"""
December 2026: the backtesting-tool series (owner, 2026-11-25). Her new positioning: "I build tools that let traders
test their strategy in seconds, not weeks". Every angle of the trader's pain, in her voice (bubbly, gist-style, a tip
in the middle, a question at the end). Facts only: what she lived and what the tool does today. Her own numbers are
[brackets] she fills from her backtest; nothing is invented, and no post promises profit.
"""



def _post(title, image, text, prep=""):
    return {"title": title, "image": image, "text": text.strip(), "prep": prep}


LINK = "Link in my profile: tell me your strategy."

DECEMBER: dict[str, dict] = {
    "2026-12-01": _post("Don't start 2027 blind", "A photo of you at your desk, chart on screen", f"""
December don land 😅 and I have one question for every trader reading this:

Do you KNOW how your strategy performed this year, or you just dey feel am?

Win rate. Your worst losing streak. Which entry actually pays you.

Most traders can't answer even one, and I couldn't either, for years.

Tip: before you write 2027 trading goals, test your strategy on past charts first. Goals without data are just wishes.

So tell me: what's one number about your trading you wish you knew? 👇

{LINK}
#Trading #Backtesting"""),
    "2026-12-02": _post("Manual backtesting lies to you", "None, text only", f"""
Confession: when I backtested by hand, I was a better trader than I am live 😂

Why? Because I'd see an ugly entry and think "nah, I wouldn't have taken that one." Skip. Next.

That's the trap. Manual backtesting is emotional, and we quietly edit the results in our heads.

So I built a tool that checks every entry by itself, with a chart picture of each trade so I confirm it with my own eyes. No skipping, no "I for no take am."

Tip: if your backtest has no losing streaks, it's lying to you.

Have you ever "edited" a backtest in your head? Be honest 👀
#Trading #Backtesting"""),
    "2026-12-03": _post("Glued to the screen", "A photo of a phone with a chart, or your desk", f"""
Raise your hand if you've watched a 1-minute chart like it owed you money 🙋🏾‍♀️

Staring at candles all day isn't discipline. Most times it's fear, because we don't trust our own strategy.

When you KNOW your numbers (how often it wins, how long trades usually take, what a normal losing week looks like), you can set your order and walk away.

Tip: find out how long your trades usually take to hit TP or SL. If it's hours, staring at every minute won't change the result.

How many hours a day do you spend watching charts? 👇
#Trading #Mindset"""),
    "2026-12-04": _post("Losing streaks don't mean it's broken", "None, text only", f"""
Three losses in a row and suddenly the strategy "doesn't work anymore" 🙃

I've been there. You change rules, jump to a new YouTube strategy, start again from zero. Again.

But what if 3 losses in a row is completely normal for your strategy? You'd never know without the data.

My tool shows the wins and losses in a row for every entry type, month by month. Seeing my worst streak BEFORE it happens live changed how calm I am.

Tip: know your worst losing streak, and halve your risk until you've survived it twice.

What's the longest losing streak you've had? 👇
#Trading #RiskManagement"""),
    "2026-12-05": _post("What I learnt testing my own strategy", "A screenshot of your Quick Backtest results table", f"""
I tested my own strategy across [how many months/years] of charts. Gist time ☕

What surprised me most: [your biggest surprise, e.g. which entry type did best].

What I stopped doing: [one thing your data told you to drop].

What I'm keeping: [your best entry type] at [its win rate]% over [number] trades.

Tip: test each entry type on its own. "My strategy" is often 3 different strategies in one coat.

Which of your entries do you trust the most, and why? 👇
#Trading #Backtesting"""),
    "2026-12-06": _post("The weekend backtest that never happens", "None, text only", f"""
"I'll backtest this weekend." 😅

Then the weekend comes, there's Owambe, church, family, and the backtest stays on the to-do list. For months.

Manual backtesting takes weeks. That's why most traders skip it or rush it.

What used to take me weeks now takes seconds: I describe the level, the tool finds and trades every entry on real past data.

Tip: if testing is too slow, you'll never do enough of it. Make it faster or make it smaller, but don't skip it.

How long has "I'll backtest it" been on your to-do list? 👇
{LINK}
#Trading #Productivity"""),
    "2026-12-07": _post("Your mentor's strategy, your results", "None, text only", f"""
You paid for the course. The mentor's charts look amazing. 🔥

But here's the uncomfortable question: has it been tested on YOUR pairs, YOUR timeframes, across years, not just the screenshots?

Hope is not a strategy. Data is.

Tip: pick 3 months of charts the course didn't show you, and test the rules exactly as taught. No editing.

Mentors: would you want your students to see your strategy's numbers across years? 👇
{LINK}
#Trading #Mentorship"""),
    "2026-12-08": _post("How it works, in 3 steps", "A screenshot of an entry picture from your backtest", f"""
People keep asking me how the tool works, so here it is in plain words 👇

1. You explain your strategy: what you mark, what confirms an entry, your SL and TP.
2. I turn your rules into a tool that checks every entry across years of real price data.
3. You get your numbers for each entry type, plus a chart picture of every single trade, so you confirm each one yourself.

Tip: write your entry rules so clearly that a stranger could follow them. If you can't, that's your first homework.

Could you explain your strategy in 3 sentences? Try it in the comments 👇
{LINK}
#Trading #Backtesting"""),
    "2026-12-09": _post("Revenge trading starts with doubt", "None, text only", f"""
Nobody wakes up and decides to revenge trade 😩

It starts with a loss you didn't expect. Then doubt. Then "let me just make it back quickly."

Doubt grows where data is missing. When you know a loss is part of your normal numbers, it hurts less, and you don't chase it.

Tip: after a loss, look at your backtest before you look at the chart.

What's your rule after a losing trade? 👇
#Trading #Mindset"""),
    "2026-12-10": _post("I was unprofitable for years", "A calm photo of you", f"""
Let me gist you something personal 💛

For years I traded rules I believed in but had never properly tested. I couldn't tell you my real win rate, or which entries were actually paying me.

I'm a designer and QA tester. My job is to test things before people rely on them. Somehow I never did that for my own trading.

So I built the tool I always needed, and for the first time I can see what my strategy really does.

Tip: treat your strategy like a product. Test it before you ship it to your account.

What would you test first if you could test anything in your trading? 👇
#Trading #QA"""),
    "2026-12-11": _post("Every entry, with a picture", "Screenshot: one trade picture with entry, SL, TP", f"""
Numbers alone can lie if the tool misreads your chart. So I didn't stop at numbers 👀

Every single trade comes with a chart picture: the level, the entry, the SL, the TP, where it filled and where it ended.

I review them at my break, tick ✓ if it's right, correct it if it's not.

Tip: never trust a backtest you can't inspect trade by trade, not even mine.

Would you rather see the summary or every trade? 👇
#Trading #Backtesting"""),
    "2026-12-12": _post("Which entry is actually paying you?", "Screenshot of results per entry type", f"""
Plot twist: the entry you love might not be the one paying you 😅

When I tested each entry type separately, [your result, e.g. "my favourite entry was my weakest"].

We get emotionally attached to the setups that look beautiful on the chart. Data doesn't care how it looks.

Tip: rank your entries by total R, not by how confident they make you feel.

What's your favourite entry, and do you know its win rate? 👇
#Trading #Data"""),
    "2026-12-13": _post("Saturday gist: trading is lonely", "None, text only", f"""
Can we talk about how lonely trading feels sometimes? 🫂

You take the loss alone. You doubt alone. And in group chats everybody posts only wins.

What helped me most was data I could trust. It answers the doubts at 2am when nobody else is awake.

Tip: write down why you took each trade. Your journal becomes the friend who tells you the truth.

Who do you talk to after a bad trading day? 👇
#Trading #Community"""),
    "2026-12-14": _post("Mentors and community leads", "None, text only", f"""
To every mentor and trading community lead 👋🏾

Your students keep asking "does this strategy really work?" Imagine answering with real numbers across years of charts, every entry, with pictures.

That's what I build: your strategy turned into a backtest and journal your students can trust.

Tip: the fastest way to build trust in a community is to show the losses too, not only the wins.

Would your community value seeing the full numbers? 👇
{LINK}
#Trading #Mentorship"""),
    "2026-12-15": _post("Halfway through December", "None, text only", f"""
We're halfway through December 🎄 Quick check-in:

✅ Do you know your strategy's win rate?
✅ Your worst losing streak?
✅ Your best entry type?
✅ How long your trades usually last?

If you ticked fewer than 3, you're not behind, you're normal. Most traders never check.

Tip: pick ONE of these and find the answer before the year ends.

How many did you tick? 👇
{LINK}
#Trading #Goals"""),
    "2026-12-16": _post("How long do your trades take?", "Screenshot: a journal page showing held time", f"""
Small number, big peace of mind ⏳

My journal tells me when each trade triggered, when it hit TP or SL, and how long I held it.

Why it matters: if your trades usually take [your usual time], checking the chart every 5 minutes does nothing but stress you.

Tip: once you know your average holding time, set alerts for TP/SL and go and live your life.

Do you know how long your trades usually take? 👇
#Trading #Mindset"""),
    "2026-12-17": _post("Designer + QA + AI = this tool", "A photo of you working", f"""
People ask how a designer built a backtesting tool 😄

Design taught me to make results easy to read.
QA taught me to test every rule against real data, and find the bugs before anyone else does.
AI helped me build fast, and testing helped me catch it when it was confidently wrong.

Put together, you get a tool that turns a trading strategy into honest numbers.

Tip: your past skills are rarely wasted. They just wait for the right problem.

What skill from your day job helps your trading? 👇
#Design #QA #AI"""),
    "2026-12-18": _post("Prop firm challenge? Know this first", "None, text only", f"""
Planning a prop firm challenge in January? Read this first 👇🏾

Challenges have a max daily loss and a max total loss. Your strategy's worst losing streak decides whether you survive them.

If you don't know that number, you're guessing with the challenge fee.

Tip: multiply your worst losing streak by your risk per trade. If it's close to the max drawdown, lower your risk.

Have you ever failed a challenge on a losing streak? 👇
#Trading #PropFirm"""),
    "2026-12-19": _post("The month-by-month truth", "Screenshot: your Monthly review", f"""
Year totals can hide ugly months 👀

My monthly review shows each month as if I'd taken each setup every time: total R, wins in a row, losses in a row, and whether the month ended in profit or loss.

Seeing a losing month in the backtest prepares you for one live. It stops you panicking in month 3.

Tip: find your worst month in your data before the market shows it to you.

What would you do differently if you knew your worst month in advance? 👇
#Trading #Backtesting"""),
    "2026-12-20": _post("Weekend gist: why I stopped jumping strategies", "None, text only", f"""
Strategy hopping is a whole lifestyle 😂 ICT today, SMC tomorrow, indicators next week.

I hopped because every losing week made me think the strategy was the problem.

Testing showed me the truth: [your honest finding, e.g. "my strategy was fine, my expectations were wrong"].

Tip: give one strategy a real test across years before you call it a failure.

How many strategies have you tried this year? 👇
#Trading #Mindset"""),
    "2026-12-21": _post("Explain your strategy to me", "None, text only", f"""
Here's my offer, plain and simple 💛

You explain your strategy and entry rules.
I turn them into a tool that tests every entry across years of real charts.
You get your numbers and a picture of every trade, so you can confirm it yourself.

No promises of profit, just the truth about your strategy, before you risk real money.

Tip: whoever tests your strategy, ask to see the losing trades first.

Want your strategy tested? Comment "TEST" 👇
{LINK}
#Trading #Backtesting"""),
    "2026-12-22": _post("Stop asking 'does this work?'", "None, text only", f"""
"Does this strategy work?" is the most asked question in every trading group 😅

And it gets answered with screenshots of wins.

Better question: "How does this strategy perform across years, including the losses?" Only data answers that.

Tip: when someone shows you a winning trade, ask them for their last 50.

What's the most common question in your trading group? 👇
#Trading #Community"""),
    "2026-12-23": _post("Your journal should talk back", "Screenshot: a diary-style journal page", f"""
My trading journal talks back to me now, and I love it 📖

Every trade reads like a diary page: the day, the pair, my entry confirmation, my entry and exit times, how long I held it, and the money in or out.

It feels like journaling my thoughts, not filling a spreadsheet. So I actually read it.

Tip: if your journal is boring, you won't open it. Make it something you want to read.

Do you journal your trades? How? 👇
#Trading #Journaling"""),
    "2026-12-24": _post("Christmas Eve, no charts", "A festive photo", f"""
Christmas Eve, and I'm not watching charts today 🎄

Not because I'm perfect, but because my numbers tell me what a normal week looks like. Missing one day doesn't break anything.

Rest is part of the strategy.

Tip: decide your trading days off for the holidays now, and write them down.

Are you trading over Christmas? 👇
#Trading #Balance"""),
    "2026-12-26": _post("Boxing Day reflection", "None, text only", f"""
Boxing Day thoughts 🎁

The best gift I gave my trading this year wasn't a new indicator. It was the truth about my strategy, in numbers.

Some of it was hard to see. All of it was useful.

Tip: write 3 things your trading taught you this year, before you set new goals.

What's one lesson the market taught you this year? 👇
#Trading #Reflection"""),
    "2026-12-28": _post("Newbies: start here", "None, text only", f"""
If you're new to trading, please hear me 🙏🏾

Don't start with real money. Start with data.

Test the strategy you're learning on past charts, every entry, no skipping. Know the win rate and the losing streaks before you risk a kobo.

Tip: your first goal isn't profit. It's proof that your rules hold up.

Newbies: what's the hardest part of learning so far? 👇
{LINK}
#Trading #Beginners"""),
    "2026-12-29": _post("Years in, still not profitable?", "None, text only", f"""
To the trader who has been at it for years and still isn't profitable: this one is for you 💛

It's not always your discipline. Sometimes the strategy was never tested properly, so you never knew what "normal" looks like.

That was me.

Tip: stop adding new rules. Test the rules you already have, every entry, across years. The answer is usually already in your charts.

How many years have you been trading? 👇
{LINK}
#Trading #Mindset"""),
    "2026-12-30": _post("Your 2027 plan, with numbers", "None, text only", f"""
Your 2027 trading plan needs 4 numbers, not 40 goals 📋

1. Your win rate
2. Your worst losing streak
3. Your best entry type
4. Your risk per trade

With these, you know how much you can lose before you stop, which setups to focus on, and what a normal month looks like.

Tip: write the 4 numbers at the top of your plan. If you don't have them, getting them is goal number one.

Which of the 4 do you already know? 👇
{LINK}
#Trading #Goals"""),
    "2026-12-31": _post("Don't enter 2027 without your data", "A photo of you, end-of-year mood", f"""
Last day of the year ✨

If you take one thing from my December posts: don't enter 2027 trading on hope.

Explain your strategy. Test every entry. See the losses before they happen. Then trade with confidence that's backed by data.

Thank you for reading, sharing and replying with me all month. 💛

Tip: tonight, write down one number you'll know about your strategy by the end of January.

Happy New Year! What's your trading word for 2027? 👇
{LINK}
#Trading #NewYear"""),
}

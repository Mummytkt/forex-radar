"""
Forward-test results and position size (owner request 2026-11-23).

RESULTS: every followed trade (trade_follows) is a live forward test of an entry confirmation. A closed trade counts:
  TP hit = +tp_r R; stopped (sl, then sl_tp / left / reentered / expired) = −1 R.
  A limit that never filled (cancelled) and trades still running are listed apart, not counted.
  The follow sends a breakeven ALERT but doesn't move the stop, so breakeven isn't applied here.
  /results on the main bot = the person's own trades; every Sunday 18:20 WAT the owner gets the week + all time.

POSITION SIZE: /risk <balance> <risk %> (USD account) is saved per person; each followed entry then shows the lot
  size that risks that amount between the entry and the SL. Forex and metals only: XXXUSD, USDXXX, crosses (through a
  USD rate on the price board), XAUUSD (100 oz) and XAGUSD (5,000 oz). Other instruments show the distance only.
"""

from __future__ import annotations

import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

STOPPED = ("sl", "sl_tp", "left", "reentered", "expired")
NAMES = {"pcl": "PCL", "engulfing_sweep": "PCL", "sweep": "PCL", "octgd": "OCTGD", "octgd2": "OCTGD 2", "octgd3": "OCTGD", "cisd": "CISD",
         "engulfing": "Engulfing", "sweep_break": "Sweep and Break"}


def _r(row) -> Optional[float]:
    if row["status"] == "tp":
        return float(row["tp_r"] or 2)
    if row["status"] in STOPPED:
        return -1.0
    return None


def results_from(conn, user_id) -> Optional[str]:
    """Her fresh start for /results (owner 2026-11-25: "clear old data, start counting from the next trade")."""
    r = conn.execute("SELECT value FROM user_config WHERE key = ?", (f"results_from:{user_id}",)).fetchone()
    return r[0] if r else None


def set_results_from(conn, user_id, when: str) -> None:
    conn.execute("INSERT OR REPLACE INTO user_config (key, value, updated_at) VALUES (?, ?, datetime('now'))",
                 (f"results_from:{user_id}", when))


def results(conn, user_id: int, since: Optional[datetime] = None) -> dict:
    conn.row_factory = sqlite3.Row
    q = "SELECT * FROM trade_follows WHERE user_id = ?"
    args: list = [user_id]
    start = results_from(conn, user_id)
    if start:
        q += " AND opened_at >= ?"
        args.append(start)
    if since:
        q += " AND opened_at >= ?"
        args.append(since.astimezone(timezone.utc).isoformat())
    rows = conn.execute(q, args).fetchall()
    by = defaultdict(lambda: {"n": 0, "w": 0, "r": 0.0})
    pairs = defaultdict(lambda: {"n": 0, "w": 0, "r": 0.0})
    tot = {"n": 0, "w": 0, "r": 0.0, "open": 0, "cancelled": 0}
    for row in rows:
        if row["status"] == "duplicate":
            continue                    # a copy of another trade (two levels heard one confirmation): never counted
        r = _r(row)
        if r is None:
            if row["status"] == "cancelled":
                tot["cancelled"] += 1
            elif row["status"] in ("open", "pending"):
                tot["open"] += 1
            continue
        key = f"{row['tf'] or ''} {NAMES.get(row['pattern'], row['pattern'] or '?')}".strip()
        for d in (by[key], pairs[row["instrument"]], tot):
            d["n"] += 1
            d["w"] += r > 0
            d["r"] += r
    return {"by": dict(by), "pairs": dict(pairs), "tot": tot}


def _line(name: str, d: dict, risk: Optional[float] = None) -> str:
    pct = d["w"] / d["n"] * 100 if d["n"] else 0
    money = f" ({'+' if d['r'] >= 0 else '−'}${abs(d['r']) * risk:,.0f})" if risk else ""     # in money too (2026-11-25)
    return f"• <b>{name}</b>: {d['n']} trade{'s' if d['n'] != 1 else ''} · {d['w']} won · {pct:.0f}% · {d['r']:+.1f}R{money}"


def report_text(conn, user_id: int, title: str = "📊 <b>Your live results</b>", week: bool = True) -> str:
    now = datetime.now(timezone.utc)
    parts = [title, "<i>From the trades the Bias Pointer followed for you. TP = +your R, SL = −1R; breakeven isn't "
                    "applied (the follow alerts you, it doesn't move your stop).</i>"]
    risk = risk_usd(conn, user_id)
    parts[1] = parts[1][:-4] + f" $ at your ${risk:g} per trade.</i>"
    start = results_from(conn, user_id)
    if start:
        parts[1] += f"\n<i>Counting from {start[:10]} (your fresh start; /results reset starts again).</i>"
    blocks = [("This week", now - timedelta(days=7))] if week else []
    blocks.append(("All time", None))
    for label, since in blocks:
        res = results(conn, user_id, since)
        t = res["tot"]
        parts += ["", f"<b>{label}</b>"]
        if not t["n"]:
            parts.append(("No closed trades since your fresh start yet." if results_from(conn, user_id) else "No closed trades yet.")
                         + (f" {t['open']} still running." if t["open"] else ""))
            continue
        parts.append(_line("Total", t, risk))
        parts += [_line(k, v, risk) for k, v in sorted(res["by"].items(), key=lambda kv: -kv[1]["r"])]
        if label == "All time" and len(res["pairs"]) > 1:
            parts += ["", "<b>By pair</b>"] + [_line(k, v, risk) for k, v in sorted(res["pairs"].items(), key=lambda kv: -kv[1]["r"])]
        extra = []
        if t["open"]:
            extra.append(f"{t['open']} still running")
        if t["cancelled"]:
            extra.append(f"{t['cancelled']} limit order{'s' if t['cancelled'] != 1 else ''} never filled")
        if extra:
            parts.append("<i>" + ", ".join(extra) + " (not counted).</i>")
    return "\n".join(parts)


async def run_weekly_report(db_path: str, config) -> bool:
    """Sundays 18:20 WAT, to the owner on the main bot."""
    from alerts.telegram import send_alert
    if not (config.telegram_enabled and config.telegram_bot_token):
        return False
    conn = sqlite3.connect(db_path, check_same_thread=False)
    try:
        r = conn.execute("SELECT id, telegram_chat_id FROM users WHERE role = 'OWNER' AND telegram_chat_id IS NOT NULL "
                         "AND telegram_chat_id != '' LIMIT 1").fetchone()
        if not r:
            return False
        text = report_text(conn, r[0], "📊 <b>Weekly forward test</b>")
    finally:
        conn.close()
    return await send_alert(config.telegram_bot_token, str(r[1]), text, parse_mode="HTML")


# ── Position size ─────────────────────────────────────────────────────────────
FIAT = {"USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD"}


def ensure_risk_table(conn) -> None:
    conn.execute("CREATE TABLE IF NOT EXISTS user_risk (user_id INTEGER PRIMARY KEY, balance REAL NOT NULL, "
                 "risk_pct REAL NOT NULL, updated_at TEXT NOT NULL)")
    conn.commit()


def get_risk(conn, user_id) -> Optional[tuple[float, float]]:
    ensure_risk_table(conn)
    r = conn.execute("SELECT balance, risk_pct FROM user_risk WHERE user_id = ?", (user_id,)).fetchone()
    return (float(r[0]), float(r[1])) if r else None


def set_risk(conn, user_id, balance: float, pct: float) -> None:
    ensure_risk_table(conn)
    conn.execute("INSERT INTO user_risk (user_id, balance, risk_pct, updated_at) VALUES (?, ?, ?, ?) "
                 "ON CONFLICT(user_id) DO UPDATE SET balance = excluded.balance, risk_pct = excluded.risk_pct, "
                 "updated_at = excluded.updated_at", (user_id, balance, pct, datetime.now(timezone.utc).isoformat()))
    conn.commit()


def _usd_per_quote(conn, quote: str, ref_price: Optional[float] = None, base: str = "") -> Optional[float]:
    """How many USD one unit of the quote currency is worth."""
    if quote == "USD":
        return 1.0
    if base == "USD" and ref_price:
        return 1.0 / ref_price
    for sym, inv in ((f"{quote}USD", False), (f"USD{quote}", True)):
        r = conn.execute("SELECT price FROM instrument_prices WHERE instrument = ?", (sym,)).fetchone()
        if r and r[0]:
            return 1.0 / r[0] if inv else float(r[0])
    return None


def lot_size(conn, instrument: str, entry: float, sl: float, balance: float, pct: float) -> Optional[dict]:
    """Lots that lose balance × pct% between entry and SL; None when it can't be worked out safely."""
    sym = instrument.replace("/", "").upper()
    dist = abs(entry - sl)
    if dist <= 0:
        return None
    if sym in ("XAUUSD", "XAGUSD"):
        units, quote, base = (100 if sym == "XAUUSD" else 5000), "USD", sym[:3]
    elif len(sym) == 6 and sym[:3] in FIAT and sym[3:] in FIAT:
        units, base, quote = 100_000, sym[:3], sym[3:]
    else:
        return None
    usd = _usd_per_quote(conn, quote, entry, base)
    if not usd:
        return None
    risk_usd = balance * pct / 100
    loss_per_lot = dist * units * usd
    lots = risk_usd / loss_per_lot
    return {"lots": lots, "risk_usd": risk_usd}


def lot_line(conn, user_id, instrument: str, entry: float, sl: float) -> Optional[str]:
    if not user_id:
        return None
    rk = get_risk(conn, user_id)
    if not rk:
        return None
    bal, pct = rk
    basis = f"${bal * pct / 100:,.2f}" if pct >= 100 else f"{pct:g}% of ${bal:,.0f} = ${bal * pct / 100:,.2f}"
    ls = lot_size(conn, instrument, entry, sl, bal, pct)
    if not ls:
        return f"Position size: work it out on your broker's calculator ({basis} risk)."
    lots = ls["lots"]
    shown = f"{lots:.2f}" if lots >= 0.01 else "below 0.01"
    return (f"💼 Lot size: <b>{shown}</b> ({basis} risk to the SL). "
            "Check it on your broker before you place it.")


RISK_HELP = ("💼 <b>Your risk per trade</b>\nType it after /risk:\n<code>/risk 20</code> = $20 per trade\n"
             "<code>/risk 1000 1</code> = a $1,000 account risking 1% ($10) per trade\n\nYour journal and /results "
             "use it from the next trade (trades already logged keep theirs). Every followed "
             "entry then shows the lot size between the entry and the SL. Forex pairs and gold/silver only; for "
             "other instruments it shows the dollar risk. <code>/risk off</code> removes it.")


# ── Auto-journal (owner request 2026-11-23) ───────────────────────────────────
# The owner's followed trades go into her trade journal by themselves: a row when the trade is on (instant entry, or a
# limit once filled), its result when it closes (TP = win, SL = loss). Pictures stay in her browser, so she adds those.
WAT = timezone(timedelta(hours=1))
OPEN_ON = ("open", "tp", "sl", "sl_tp", "left", "reentered", "expired")


DEFAULT_RISK_USD = 20.0     # the owner's risk per trade (2026-11-25): 3R = $60


def risk_usd(conn, user_id) -> float:
    """Her money risked per trade, for the journal ($20 unless she changed it on the Journal page)."""
    conn.execute("CREATE TABLE IF NOT EXISTS journal_risk (user_id INTEGER PRIMARY KEY, risk_usd REAL NOT NULL, updated_at TEXT)")
    r = conn.execute("SELECT risk_usd FROM journal_risk WHERE user_id = ?", (user_id,)).fetchone() if user_id else None
    return float(r[0]) if r else DEFAULT_RISK_USD


def set_risk_usd(conn, user_id, amount: float) -> None:
    risk_usd(conn, user_id)
    conn.execute("INSERT INTO journal_risk (user_id, risk_usd, updated_at) VALUES (?, ?, ?) ON CONFLICT(user_id) DO UPDATE "
                 "SET risk_usd = excluded.risk_usd, updated_at = excluded.updated_at",
                 (user_id, amount, datetime.now(timezone.utc).isoformat()))


def journal_sync(conn, fo: dict) -> None:
    """Make the owner's journal match one follow. Safe to call every price check."""
    if fo.get("role") != "OWNER" or fo.get("status") not in OPEN_ON:
        return
    if fo.get("mode") == "limit" and not fo.get("filled_at"):
        return
    from config import pip_size_for
    bull = fo["direction"] == "bullish"
    t0 = datetime.fromisoformat(fo.get("filled_at") or fo["opened_at"]).astimezone(WAT)
    res = "win" if fo["status"] == "tp" else ("loss" if fo["status"] in STOPPED else "open")
    exit_p = fo["tp"] if res == "win" else (fo["sl"] if res == "loss" else None)
    pips = None
    if exit_p is not None:
        pips = round(((exit_p - fo["entry"]) if bull else (fo["entry"] - exit_p)) / pip_size_for(fo["instrument"]), 1)
    rr = float(fo["tp_r"] or 2) if res == "win" else (-1.0 if res == "loss" else None)
    t1 = None
    when = fo.get("sl_at") if res == "loss" else fo.get("closed_at") if res == "win" else None
    if when:
        t1 = datetime.fromisoformat(when).astimezone(WAT)
    name = f"{fo.get('tf') or ''} {NAMES.get(fo.get('pattern'), fo.get('pattern') or '')}".strip()
    row = conn.execute("SELECT id, result FROM journal_entries WHERE follow_id = ?", (fo["id"],)).fetchone()
    if row is None:
        notes = (f"Auto-logged from the Bias Pointer's trade follow: {name} confirmation, "
                 f"{'limit' if fo.get('mode') == 'limit' else 'instant'} entry"
                 + (f", re-entry {fo['reentry_no']}" if fo.get("reentry_no") else "") + ". Add your chart and notes.")
        # money, not pips (owner 2026-11-25): her risk per trade at the time of the trade, and the TP in money
        risk = risk_usd(conn, fo.get("user_id"))
        conn.execute("""INSERT INTO journal_entries
            (trade_date, instrument, direction, entry_price, stop_loss, take_profit, exit_price, pips, rr_ratio,
             result, setup_type, setup_type_notes, trade_type, entry_date, exit_date, entry_time, exit_time, notes,
             user_id, follow_id, amount_risked, amount_aimed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'other', ?, 'live', ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (t0.date().isoformat(), fo["instrument"], "buy" if bull else "sell", fo["entry"], fo["sl"], fo["tp"],
             exit_p, pips, rr, res, name, t0.date().isoformat(), t1.date().isoformat() if t1 else None,
             t0.strftime("%H:%M"), t1.strftime("%H:%M") if t1 else None, notes, fo.get("user_id"), fo["id"],
             risk, round(risk * float(fo["tp_r"] or 2), 2)))
    elif row[1] == "open" and res != "open":
        conn.execute("UPDATE journal_entries SET result = ?, exit_price = ?, pips = ?, rr_ratio = ?, exit_date = ?, "
                     "exit_time = ? WHERE id = ?",
                     (res, exit_p, pips, rr, t1.date().isoformat() if t1 else None, t1.strftime("%H:%M") if t1 else None,
                      row[0]))

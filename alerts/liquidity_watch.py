"""
Liquidity alerts after a break (owner request, 2026-11-11; picture Documents/Liquidity_Kinds_After_Breakout.png).

Every H4 story alert (a break: continuation, pullback, back in alignment, ...) starts a watch on that
instrument. On each H4 candle close after it, the candles after the breaking candle are checked for:

  - SINGLE CANDLE liquidity: in the first SINGLE_N candles after the break, after a bullish break a
    bullish candle's low wick (price pulls back through it into the POI), after a bearish break a bearish
    candle's high wick. Sent once per break (the first one).
  - LOW / HIGH liquidity: a V-shape on closes after a bullish break (a close lower than the closes on
    either side; the level is the lowest wick of that candle and the next), an A-shape after a bearish
    break. Each new one is sent as it forms (it is known one candle later, when the next candle closes).

The next story alert on the instrument replaces the watch. A watch ends after MAX_CANDLES candles.
Delivered like the other alerts: to everyone watching the instrument whose Alert Filters have
"Liquidity after a break" switched on (off by default).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from config import fmt_price, tagged

logger = logging.getLogger(__name__)

SINGLE_N = 3        # single candle liquidity: only in the first N candles after the break
MAX_CANDLES = 40    # the watch ends after this many H4 candles

SCHEMA = """
CREATE TABLE IF NOT EXISTS liq_watch (
    instrument  TEXT PRIMARY KEY,
    direction   TEXT NOT NULL,           -- 'bullish' | 'bearish' (the break)
    title       TEXT NOT NULL,           -- the alert it follows, e.g. 'H4 bullish continuation after the Daily breakout'
    started_at  TEXT NOT NULL,           -- when that alert came (UTC)
    break_ts    TEXT,                    -- the breaking H4 candle's open time (found from the stored candles)
    sent_single INTEGER NOT NULL DEFAULT 0,
    sent_v      TEXT NOT NULL DEFAULT '' -- the candles whose V / A was sent, comma separated
)
"""


# each liquidity alert sent, so its "📊 View chart" button can draw it later
SENT_SCHEMA = """
CREATE TABLE IF NOT EXISTS liq_sent (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    instrument  TEXT NOT NULL,
    direction   TEXT NOT NULL,
    title       TEXT NOT NULL,
    kind        TEXT NOT NULL,           -- 'single' | 'swing'
    level       REAL NOT NULL,
    ts          TEXT NOT NULL,           -- the candle that formed it
    break_ts    TEXT NOT NULL,           -- the breaking H4 candle
    sent_at     TEXT NOT NULL,
    file_id     TEXT                     -- the picture, once Telegram has it
)
"""


def ensure_table(conn) -> None:
    conn.execute(SCHEMA)
    conn.execute(SENT_SCHEMA)
    # the level the H4 candle broke (user, 2026-11-18: drawn on the liquidity chart, from the candle that made it)
    for t in ("liq_watch", "liq_sent"):
        cols = {r[1] for r in conn.execute(f"PRAGMA table_info({t})")}
        if "break_level" not in cols:
            conn.execute(f"ALTER TABLE {t} ADD COLUMN break_level REAL")
    # several liquidities found at one H4 close go out as ONE message (user, 2026-11-18): the first row's chart
    # draws the others too (their liq_sent ids, comma separated)
    if "also" not in {r[1] for r in conn.execute("PRAGMA table_info(liq_sent)")}:
        conn.execute("ALTER TABLE liq_sent ADD COLUMN also TEXT")
    # the Alert Filters switch of the alert the watch follows (user, 2026-11-18): its liquidity only reaches
    # people who have that alert switched on too
    if "pref" not in {r[1] for r in conn.execute("PRAGMA table_info(liq_watch)")}:
        conn.execute("ALTER TABLE liq_watch ADD COLUMN pref TEXT")


def start(conn, instrument: str, direction: str, title: str, now: Optional[datetime] = None,
          level: Optional[float] = None, pref: Optional[str] = None) -> None:
    """A new H4 alert on the instrument: watch for the liquidity after it (replaces the old watch).
    level: the level that H4 candle broke."""
    ensure_table(conn)
    now = now or datetime.now(timezone.utc)
    conn.execute("""
        INSERT INTO liq_watch (instrument, direction, title, started_at, break_ts, sent_single, sent_v, break_level, pref)
        VALUES (?, ?, ?, ?, NULL, 0, '', ?, ?)
        ON CONFLICT(instrument) DO UPDATE SET direction = excluded.direction, title = excluded.title,
            started_at = excluded.started_at, break_ts = NULL, sent_single = 0, sent_v = '',
            break_level = excluded.break_level, pref = excluded.pref
    """, (instrument, direction, title, now.isoformat(), level, pref))
    conn.commit()


def watch_pref(conn, instrument: str) -> Optional[str]:
    """The Alert Filters switch of the alert the instrument's liquidity watch follows (None: no filter)."""
    try:
        r = conn.execute("SELECT pref FROM liq_watch WHERE instrument = ?", (instrument,)).fetchone()
    except Exception:
        return None
    return r[0] if r else None


def level_origin(direction: str, level: float, candles: list[tuple], break_ts: str) -> Optional[str]:
    """The candle that MADE the broken level (user picked picture B, Documents/Break_Line_Start.png): the latest
    H4 candle before the break whose low (a bearish break: an old low) or high (a bullish break) is that level.
    candles: (ts, o, h, l, c) oldest first. None when none of them made it (then the line starts at the break)."""
    before = [c for c in candles if c[0] < break_ts]
    if not before or level is None:
        return None
    wick = (lambda c: c[2]) if direction == "bullish" else (lambda c: c[3])
    tol = abs(level) * 0.0002            # 2 pips on EURUSD; a few points on an index
    for c in reversed(before):
        if abs(wick(c) - level) <= tol:
            return c[0]
    best = min(before, key=lambda c: min(abs(v - level) for v in c[1:5]))   # a level from a close (body breaks)
    return best[0] if min(abs(v - level) for v in best[1:5]) <= tol else None


def _parse(s: str) -> datetime:
    dt = datetime.fromisoformat(s)
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def find(direction: str, candles: list[tuple], sent_single: bool, sent_v: set[str]) -> list[dict]:
    """
    candles: (ts, o, h, l, c) oldest first; candles[0] = the breaking candle, the rest closed after it.
    Returns the new liquidity, oldest first: {'kind': 'single'|'swing', 'level', 'ts', 'ts2'?}.
    """
    bull = direction == "bullish"
    d = 1 if bull else -1
    lo = (lambda k: candles[k][3]) if bull else (lambda k: -candles[k][2])    # flipped: buy-side lows
    cl = lambda k: d * candles[k][4]
    op = lambda k: d * candles[k][1]
    out = []
    n = len(candles)
    if not sent_single:
        for k in range(1, min(n, SINGLE_N + 1)):
            if cl(k) > op(k):            # bullish candle after a bullish break (bearish after a bearish one)
                out.append({"kind": "single", "level": d * lo(k), "ts": candles[k][0]})
                break
    for k in range(1, n - 1):           # a V on closes needs the candle after it closed
        if candles[k][0] in sent_v:
            continue
        if cl(k) < cl(k - 1) and cl(k) < cl(k + 1):
            out.append({"kind": "swing", "level": d * min(lo(k), lo(k + 1)), "ts": candles[k][0], "ts2": candles[k + 1][0]})
    out.sort(key=lambda x: x["ts"])
    return out


def _wat(ts: str) -> str:
    return (_parse(ts) + timedelta(hours=1)).strftime("%d %b %H:%M") + " WAT"


def text_many(instrument: str, direction: str, title: str, liqs: list[dict]) -> str:
    """Several liquidities from one H4 close in one message, nearest to price first (user, 2026-11-18)."""
    bull = direction == "bullish"
    t = title if title.startswith(("H4", "Daily")) else title[0].lower() + title[1:]
    side = "below it" if bull else "above it"
    parts = [_name_what(l, bull) for l in liqs]
    lines = [f"{name}: {fmt_price(instrument, l['level'])}, {what}." for l, (name, what) in zip(liqs, parts)]
    return (f"💧 {tagged(instrument)} · Liquidity after the {t}\n"
            f"Liquidity: {' · '.join(fmt_price(instrument, l['level']) for l in liqs)}\n\n"
            + "\n".join(lines) + "\n\n"
            f"The {'BUY' if bull else 'SELL'} POI is the fresh key level of the leg just {side}: price sweeping this liquidity "
            f"into it is the setup.")


def _name_what(liq: dict, bull: bool) -> tuple[str, str]:
    if liq["kind"] == "single":
        return ("Single candle liquidity",
                f"the low wick of the bullish candle of {_wat(liq['ts'])}" if bull
                else f"the high wick of the bearish candle of {_wat(liq['ts'])}")
    return ("Low liquidity" if bull else "High liquidity",
            f"a V-shape on the closes ({_wat(liq['ts'])}): its low" if bull
            else f"an A-shape on the closes ({_wat(liq['ts'])}): its high")


def text(instrument: str, direction: str, title: str, liq: dict) -> str:
    bull = direction == "bullish"
    if liq["kind"] == "single":
        name = "Single candle liquidity"
        what = (f"the low wick of the bullish candle of {_wat(liq['ts'])}" if bull
                else f"the high wick of the bearish candle of {_wat(liq['ts'])}")
    else:
        name = "Low liquidity" if bull else "High liquidity"
        what = (f"a V-shape on the closes ({_wat(liq['ts'])}): its low" if bull
                else f"an A-shape on the closes ({_wat(liq['ts'])}): its high")
    t = title if title.startswith(("H4", "Daily")) else title[0].lower() + title[1:]
    side = "below it" if bull else "above it"
    # the pair and the price on the first two lines: the Short style keeps only those
    return (f"💧 {tagged(instrument)} · {name} after the {t}\n"
            f"Liquidity: {fmt_price(instrument, liq['level'])}, {what}.\n\n"
            f"The {'BUY' if bull else 'SELL'} POI is the fresh key level of the leg just {side}: price sweeping this liquidity "
            f"into it is the setup.")


def check(conn, instrument: str, now: Optional[datetime] = None) -> list[tuple[str, Optional[int]]]:
    """After an H4 candle is stored: the liquidity that formed since the last check, as
    (alert text, liq_sent id for the chart button)."""
    try:
        w = conn.execute("SELECT * FROM liq_watch WHERE instrument = ?", (instrument,)).fetchone()
    except Exception:
        return []
    if not w:
        return []
    w = dict(w)
    break_ts = w["break_ts"]
    if not break_ts:
        # the breaking candle: the last stored H4 candle that opened at least 3 h before the alert came
        cutoff = (_parse(w["started_at"]) - timedelta(hours=3)).isoformat()
        r = conn.execute("SELECT ts FROM candles WHERE instrument = ? AND tf = 'H4' AND ts <= ? ORDER BY ts DESC LIMIT 1",
                         (instrument, cutoff)).fetchone()
        if not r:
            return []
        break_ts = r[0]
        conn.execute("UPDATE liq_watch SET break_ts = ? WHERE instrument = ?", (break_ts, instrument))
    rows = conn.execute("SELECT ts, o, h, l, c FROM candles WHERE instrument = ? AND tf = 'H4' AND ts >= ? ORDER BY ts ASC",
                        (instrument, break_ts)).fetchall()
    candles = [tuple(r) for r in rows]
    if len(candles) > MAX_CANDLES + 1:
        conn.execute("DELETE FROM liq_watch WHERE instrument = ?", (instrument,))
        conn.commit()
        return []
    sent_v = {s for s in (w["sent_v"] or "").split(",") if s}
    new = find(w["direction"], candles, bool(w["sent_single"]), sent_v)
    if not new:
        conn.commit()
        return []
    for liq in new:
        if liq["kind"] == "single":
            w["sent_single"] = 1
        else:
            sent_v.add(liq["ts"])
    conn.execute("UPDATE liq_watch SET sent_single = ?, sent_v = ? WHERE instrument = ?",
                 (w["sent_single"], ",".join(sorted(sent_v)), instrument))
    sent_at = (now or datetime.now(timezone.utc)).isoformat()
    out = []
    ids = []
    if len(new) > 1:        # one message: nearest to the last close first
        last = candles[-1][4]
        new.sort(key=lambda l: abs(l["level"] - last))
    for liq in new:
        lid = None
        try:
            ensure_table(conn)
            lid = conn.execute(
                "INSERT INTO liq_sent (instrument, direction, title, kind, level, ts, break_ts, sent_at, break_level) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (instrument, w["direction"], w["title"], liq["kind"], liq["level"], liq["ts"], break_ts, sent_at,
                 w.get("break_level"))).lastrowid
        except Exception:
            logger.exception("%s liquidity not logged for its chart", instrument)
        ids.append(lid)
        out.append((text(instrument, w["direction"], w["title"], liq), lid))
    if len(new) > 1:
        lid = ids[0]
        others = [str(i) for i in ids[1:] if i]
        if lid and others:
            conn.execute("UPDATE liq_sent SET also = ? WHERE id = ?", (",".join(others), lid))
        out = [(text_many(instrument, w["direction"], w["title"], new), lid)]
    conn.commit()
    return out


def picture(conn, liq_id: int) -> Optional[tuple[bytes, str, Optional[str]]]:
    """(png, caption, cached file id) for a liquidity alert's "📊 View chart": the H4 candles
    from before the break up to when it was sent, the break candle marked, the liquidity line
    drawn from the candle that formed it."""
    from alerts.chart_image import render
    try:
        r = conn.execute("SELECT * FROM liq_sent WHERE id = ?", (liq_id,)).fetchone()
    except Exception:
        return None
    if not r:
        return None
    r = dict(r)
    inst = r["instrument"]
    rows = conn.execute("SELECT ts, o, h, l, c FROM candles WHERE instrument = ? AND tf = 'H4' AND ts <= ? "
                        "ORDER BY ts DESC LIMIT 60", (inst, r["sent_at"])).fetchall()
    candles = [tuple(x) for x in reversed(rows)]
    bull = r["direction"] == "bullish"
    name = ("Single candle liquidity" if r["kind"] == "single"
            else ("Low liquidity" if bull else "High liquidity"))
    level = {"y": r["level"], "label": name, "kind": "liq", "tf": "both", "t0": r["ts"]}
    levels = [level]
    names = [f"{name} {fmt_price(inst, r['level'])}"]
    for oid in [x for x in (r.get("also") or "").split(",") if x]:     # sent in the same message
        o = conn.execute("SELECT * FROM liq_sent WHERE id = ?", (int(oid),)).fetchone()
        if o:
            o = dict(o)
            oname = "Single candle liquidity" if o["kind"] == "single" else ("Low liquidity" if bull else "High liquidity")
            levels.append({"y": o["level"], "label": oname, "kind": "liq", "tf": "both", "t0": o["ts"]})
            names.append(f"{oname} {fmt_price(inst, o['level'])}")
    if len(names) > 1:
        name = "Liquidity"
    bl = r.get("break_level")
    if bl is not None:      # the level the H4 candle broke, from the candle that made it
        origin = level_origin(r["direction"], bl, candles, r["break_ts"]) or r["break_ts"]
        levels.append({"y": bl, "label": "H4 break", "kind": "h4", "tf": "both", "t0": origin})
    meta = {"tf_title": "4H", "side": f"{'BUY' if bull else 'SELL'} · {name}",
            "subtitle": f"after the {r['title']}",
            "marks": [(r["break_ts"], "break")],
            "fired_at": _wat(r["sent_at"])}
    png = render(inst, "H4", candles, levels, meta, fmt=lambda v: fmt_price(inst, v), full=True)
    caption = f"{inst} · 4H · {' · '.join(names)} after the {r['title']}"
    if bl is not None:
        caption += f" · broken level {fmt_price(inst, bl)}"
    return png, caption[:1000], r["file_id"]


def remember_file_id(conn, liq_id: int, file_id: str) -> None:
    conn.execute("UPDATE liq_sent SET file_id = ? WHERE id = ?", (file_id, liq_id))
    conn.commit()

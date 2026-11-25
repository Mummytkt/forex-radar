"""Quick Backtest (owner only, 2026-11-21): the fastest way to journal one entry model's backtest.

One row per setup the owner finds on the chart (breakout → liquidity → POI), with tick boxes instead of typing:
the date, pair, buy/sell, whether it was an inside-range or opposite-range trade, and, for each H1 confirmation
that formed at the POI (PCL, Engulfing, OCTGD 1, OCTGD 2, CISD), how it ended and how many times she took it before
price closed outside the level. The confirmation that formed first is starred: that is the one she would trade.

One pass through 2020-2026 records every confirmation at each setup, so she never re-scrolls the years per
confirmation. Results use her rules: TP 3R, breakeven at 2R. A setup taken N times: each take before the last is a
loss; the last take is the ticked result (same as the Entry Tester's takes). No pictures, for speed.
"""

from __future__ import annotations

import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from api.auth import require_owner

router = APIRouter()

# Stored keys: never rename one (labels can change). Order = how they show.
CONFIRMATIONS = [("pcl", "H1 PCL"), ("eng", "H1 Engulfing"), ("octgd1", "H1 OCTGD 1"), ("octgd2", "H1 OCTGD 2"),
                 ("octgd3", "H1 OCTGD 3"), ("cisd", "H1 CISD"), ("octgd15", "M15 OCTGD"), ("octgd215", "M15 OCTGD 2"),
                 ("octgd315", "M15 OCTGD 3"), ("cisd15", "M15 CISD"), ("cisd5", "M5 CISD")]
OUTCOMES = ("win", "be", "loss")
RANGES = ("inside", "opposite")
DEFAULT_TP_R = 3.0

SCHEMA = """
CREATE TABLE IF NOT EXISTS quick_bt (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pair TEXT NOT NULL,
    date TEXT NOT NULL,             -- the setup's chart date, YYYY-MM-DD
    side TEXT NOT NULL,             -- buy / sell
    range_type TEXT NOT NULL,       -- inside / opposite
    valid INTEGER NOT NULL DEFAULT 1,
    results_json TEXT NOT NULL,     -- {"pcl": {"outcome": "win", "takes": 2}, ...}; absent = did not form
    first TEXT,                     -- the confirmation that formed first (the one she would trade)
    tp_r REAL NOT NULL DEFAULT 3,
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)"""


IMG_SCHEMA = """
CREATE TABLE IF NOT EXISTS quick_bt_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    setup_id INTEGER NOT NULL,
    conf TEXT NOT NULL,             -- the confirmation key
    n INTEGER NOT NULL,             -- which take
    png BLOB NOT NULL,
    created_at TEXT NOT NULL
)"""


@contextmanager
def _db(request: Request):
    conn = sqlite3.connect(request.app.state.config.db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute(SCHEMA)
        conn.execute(IMG_SCHEMA)
        cols = {r[1] for r in conn.execute("PRAGMA table_info(quick_bt)")}
        if "auto" not in cols:      # Auto-check saves (2026-11-23): saved by itself, to review at a break
            conn.execute("ALTER TABLE quick_bt ADD COLUMN auto INTEGER NOT NULL DEFAULT 0")
            conn.execute("ALTER TABLE quick_bt ADD COLUMN reviewed INTEGER NOT NULL DEFAULT 1")
            conn.execute("ALTER TABLE quick_bt ADD COLUMN level REAL")
        yield conn
        conn.commit()
    finally:
        conn.close()


class Result(BaseModel):
    outcome: str
    takes: int = 1
    exit: Optional[str] = None      # when its last trade ended (auto-check)
    entered: Optional[str] = None   # when it entered (auto-check), so each timeframe journal finds its ★ first
    after_tp: bool = False     # entered after the ★ first trade's TP: tracked for its own win rate (owner 2026-11-24)


class SetupBody(BaseModel):
    pair: str = "EURUSD"
    date: str
    side: str
    range_type: str
    valid: bool = True
    results: dict[str, Result] = {}
    first: Optional[str] = None
    note: str = ""


def _clean(b: SetupBody) -> tuple:
    keys = {k for k, _ in CONFIRMATIONS}
    pair = re.sub(r"[^A-Z0-9]", "", b.pair.upper())[:12] or "EURUSD"
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", b.date or ""):
        raise HTTPException(400, "Pick the setup's date")
    if b.side not in ("buy", "sell"):
        raise HTTPException(400, "Pick Buy or Sell")
    if b.range_type not in RANGES:
        raise HTTPException(400, "Pick Inside range or Opposite range")
    res = {}
    for k, r in b.results.items():
        if k not in keys or r.outcome not in OUTCOMES:
            raise HTTPException(400, f"Unknown confirmation or result: {k}")
        res[k] = {"outcome": r.outcome, "takes": max(1, min(int(r.takes or 1), 20))}
        if r.after_tp:
            res[k]["after_tp"] = True
        if r.entered:
            res[k]["entered"] = str(r.entered)[:40]
        if r.exit:
            res[k]["exit"] = str(r.exit)[:40]
    first = b.first if b.first in res else None
    if res and not first:      # one formed: it is the first; several: she must star one
        first = next(iter(res)) if len(res) == 1 else None
    return pair, b.date, b.side, b.range_type, int(b.valid), json.dumps(res), first, b.note.strip()[:300]


def _row(r: sqlite3.Row) -> dict:
    d = dict(r)
    d["results"] = json.loads(d.pop("results_json") or "{}")
    d["valid"] = bool(d["valid"])
    d["auto"] = bool(d.get("auto"))
    d["reviewed"] = bool(d.get("reviewed", 1))
    return d


@router.get("/quick-bt")
def list_setups(request: Request):
    require_owner(request)
    with _db(request) as conn:
        counts = dict(conn.execute("SELECT setup_id, COUNT(*) FROM quick_bt_images GROUP BY setup_id").fetchall())
        rows = [dict(_row(r), pictures=counts.get(r["id"], 0))
                for r in conn.execute("SELECT * FROM quick_bt ORDER BY date DESC, id DESC")]
    return {"setups": rows, "confirmations": CONFIRMATIONS, "tp_r": DEFAULT_TP_R, "be_at_r": 2}


@router.post("/quick-bt")
def add_setup(body: SetupBody, request: Request):
    require_owner(request)
    now = datetime.now(timezone.utc).isoformat()
    with _db(request) as conn:
        sid = conn.execute(
            "INSERT INTO quick_bt (pair, date, side, range_type, valid, results_json, first, note, tp_r, created_at, "
            "updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (*_clean(body), DEFAULT_TP_R, now, now)).lastrowid
        return _row(conn.execute("SELECT * FROM quick_bt WHERE id = ?", (sid,)).fetchone())


@router.put("/quick-bt/{sid}")
def update_setup(sid: int, body: SetupBody, request: Request):
    require_owner(request)
    with _db(request) as conn:
        if not conn.execute("SELECT 1 FROM quick_bt WHERE id = ?", (sid,)).fetchone():
            raise HTTPException(404, "Setup not found")
        conn.execute("UPDATE quick_bt SET pair = ?, date = ?, side = ?, range_type = ?, valid = ?, results_json = ?, "
                     "first = ?, note = ?, updated_at = ?, reviewed = 1 WHERE id = ?",
                     (*_clean(body), datetime.now(timezone.utc).isoformat(), sid))
        return _row(conn.execute("SELECT * FROM quick_bt WHERE id = ?", (sid,)).fetchone())


@router.delete("/quick-bt/{sid}")
def delete_setup(sid: int, request: Request):
    require_owner(request)
    with _db(request) as conn:
        conn.execute("DELETE FROM quick_bt WHERE id = ?", (sid,))
        conn.execute("DELETE FROM quick_bt_images WHERE setup_id = ?", (sid,))
    return {"ok": True}


class DeleteMany(BaseModel):
    ids: list[int] = []
    all: bool = False
    confirm: str = ""          # "DELETE" typed, for all (same as the Entry Tester)


@router.post("/quick-bt/delete")
def delete_many(body: DeleteMany, request: Request):
    """Delete the ticked setups, or every one (user, 2026-11-24), with their pictures."""
    require_owner(request)
    with _db(request) as conn:
        if body.all:
            if body.confirm != "DELETE":
                raise HTTPException(400, "Type DELETE to delete every setup")
            n = conn.execute("DELETE FROM quick_bt").rowcount
            conn.execute("DELETE FROM quick_bt_images")
        else:
            ids = [int(i) for i in body.ids][:5000]
            n = 0
            for i in ids:
                n += conn.execute("DELETE FROM quick_bt WHERE id = ?", (i,)).rowcount
                conn.execute("DELETE FROM quick_bt_images WHERE setup_id = ?", (i,))
    return {"ok": True, "deleted": n}


class RemoveKeys(BaseModel):
    ids: list[int] = []
    all: bool = False
    keys: list[str] = []        # this journal's confirmations (H1 / M15 / M5)
    confirm: str = ""           # "DELETE" typed, for all


@router.post("/quick-bt/remove-keys")
def remove_keys(body: RemoveKeys, request: Request):
    """Delete from one timeframe journal (owner, 2026-11-25): only those confirmations' results (and pictures) leave
    the setups; a setup with nothing left is deleted. all = every setup that has one of them."""
    require_owner(request)
    keys = {k for k in body.keys if k in {c for c, _ in CONFIRMATIONS}}
    if not keys:
        raise HTTPException(400, "Which journal?")
    if body.all and body.confirm != "DELETE":
        raise HTTPException(400, "Type DELETE to clear this journal")
    removed = deleted = 0
    with _db(request) as conn:
        rows = conn.execute("SELECT id, results_json, first FROM quick_bt").fetchall() if body.all else \
            [r for i in body.ids[:5000] for r in conn.execute("SELECT id, results_json, first FROM quick_bt WHERE id = ?", (int(i),))]
        for sid, rj, first in rows:
            res = json.loads(rj or "{}")
            if not keys & set(res):
                continue
            left = {k: v for k, v in res.items() if k not in keys}
            for k in keys & set(res):
                conn.execute("DELETE FROM quick_bt_images WHERE setup_id = ? AND conf = ?", (sid, k))
            if not left:
                conn.execute("DELETE FROM quick_bt WHERE id = ?", (sid,))
                conn.execute("DELETE FROM quick_bt_images WHERE setup_id = ?", (sid,))
                deleted += 1
            else:
                conn.execute("UPDATE quick_bt SET results_json = ?, first = ? WHERE id = ?",
                             (json.dumps(left), first if first in left else None, sid))
                removed += 1
    return {"ok": True, "trimmed": removed, "deleted": deleted}


@router.post("/quick-bt/{sid}/reviewed")
def mark_reviewed(sid: int, request: Request):
    require_owner(request)
    with _db(request) as conn:
        conn.execute("UPDATE quick_bt SET reviewed = 1 WHERE id = ?", (sid,))
    return {"ok": True}


@router.get("/quick-bt/{sid}/pictures")
def list_pictures(sid: int, request: Request):
    require_owner(request)
    labels = dict(CONFIRMATIONS)
    with _db(request) as conn:
        row = conn.execute("SELECT results_json FROM quick_bt WHERE id = ?", (sid,)).fetchone()
        res = json.loads(row[0] or "{}") if row else {}
        late = lambda k: " · after TP" if (res.get(k) or {}).get("after_tp") else ""
        return {"pictures": [{"id": r[0], "conf": r[1], "n": r[2], "label": f"{labels.get(r[1], r[1])} · take {r[2]}{late(r[1])}"}
                             for r in conn.execute("SELECT id, conf, n FROM quick_bt_images WHERE setup_id = ? "
                                                   "ORDER BY id", (sid,))]}


@router.get("/quick-bt/picture/{pid}")
def get_picture(pid: int, request: Request):
    from fastapi.responses import Response
    require_owner(request)
    with _db(request) as conn:
        r = conn.execute("SELECT png FROM quick_bt_images WHERE id = ?", (pid,)).fetchone()
    if not r:
        raise HTTPException(404, "Picture not found")
    return Response(content=r[0], media_type="image/png", headers={"Cache-Control": "private, max-age=86400"})


# ── Auto-check (2026-11-23): she marks the POI, the server finds and trades every confirmation ──────────────
class AutoBody(BaseModel):
    pair: str = "EURUSD"
    side: str
    level: float               # the level line (an OC: the first candle's close; a V: its level; ...)
    start: str                 # when the watch begins, ISO 8601 with its UTC offset (the owner's timezone)
    end_at: Optional[str] = None   # the next H4 breakout, if she knows it (ends the setup)
    mode: str = "limit"        # limit (her live rule) or instant
    tp_r: float = DEFAULT_TP_R
    be_r: float = 2.0
    keys: Optional[list[str]] = None   # check only these confirmations (the ticked ones); none = all
    tol_pips: float = 1.0      # a wick this close to the line counts as reaching it (feeds differ slightly)
    # Save it straight away (2026-11-23: she reviews at her break, so checking never slows the backtest down)
    save: bool = False
    date: Optional[str] = None
    range_type: Optional[str] = None
    valid: bool = True
    note: str = ""


def _cache_base(request: Request) -> str:
    import os
    return os.path.dirname(os.path.abspath(request.app.state.config.db_path)) or "."


@router.get("/quick-bt/auto/status")
def auto_status(request: Request, pair: str = "EURUSD"):
    require_owner(request)
    from api.autobacktest import coverage
    return coverage(pair.upper(), _cache_base(request))


@router.post("/quick-bt/auto")
def auto_check(request: Request, body: AutoBody):
    """Runs in a worker thread (a plain def route), so the price checks keep running meanwhile."""
    require_owner(request)
    from api.autobacktest import run
    if body.side not in ("buy", "sell"):
        raise HTTPException(400, "side must be buy or sell")
    def _when(v: str) -> datetime:
        t = datetime.fromisoformat(v)
        return t if t.tzinfo else t.replace(tzinfo=timezone.utc)
    try:
        start = _when(body.start)
        end_at = _when(body.end_at) if body.end_at else None
    except ValueError:
        raise HTTPException(400, "start / end must be a date and time")
    if not body.level > 0:
        raise HTTPException(400, "Type the level's price")
    if body.mode not in ("limit", "instant"):
        raise HTTPException(400, "mode must be limit or instant")
    if body.save and body.range_type not in RANGES:
        raise HTTPException(400, "Pick Inside range or Opposite range")
    try:
        res = run(body.pair.upper(), body.side, body.level, start, _cache_base(request), body.tp_r, body.be_r,
                  body.mode, end_at, max(0.0, min(body.tol_pips, 20.0)), pictures=body.save,
                  keys=[k for k in (body.keys or []) if k in {c for c, _ in CONFIRMATIONS}] or None)
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    pics = res.pop("_pictures", [])
    if body.save:
        keys = {k for k, _ in CONFIRMATIONS}
        # each result keeps when it triggered and when it ended, so the journal can say how long it held (2026-11-25)
        results = {k: dict({"outcome": v["outcome"], "takes": v["takes"], "entered": v.get("entered"),
                            "exit": (v.get("trades") or [{}])[-1].get("exit")},
                           **({"after_tp": True} if v.get("after_tp") else {}))
                   for k, v in res["results"].items() if k in keys and v["outcome"] in OUTCOMES}
        first = res["first"] if res["first"] in results else (next(iter(results)) if len(results) == 1 else None)
        # the setup's date = the day the ★ first trade triggered (her local day, WAT), else the day she searched from
        trig = results.get(first, {}).get("entered") if first else None
        if trig:
            res["trigger_date"] = datetime.fromisoformat(trig).astimezone(timezone(timedelta(hours=1))).date().isoformat()
        now = datetime.now(timezone.utc).isoformat()
        note = (body.note.strip() or f"Auto-checked · level {body.level:g}")[:300]
        with _db(request) as conn:
            sid = conn.execute(
                "INSERT INTO quick_bt (pair, date, side, range_type, valid, results_json, first, note, tp_r, created_at, "
                "updated_at, auto, reviewed, level) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0, ?)",
                (body.pair.upper(), res.get("trigger_date") or body.date or start.date().isoformat(), body.side, body.range_type, int(body.valid),
                 json.dumps(results), first, note, body.tp_r, now, now, body.level)).lastrowid
            for conf, n, png in pics:
                conn.execute("INSERT INTO quick_bt_images (setup_id, conf, n, png, created_at) VALUES (?, ?, ?, ?, ?)",
                             (sid, conf, n, png, now))
        res["saved_id"] = sid
        res["pictures"] = len(pics)
    return res

"""
Entry Tester — the owner's backtest of entry patterns (owner only).

Each row is one trade idea (a pair, a date, a direction, the H4 alert it came
from). On that same trade the owner ticks how each entry pattern did: win,
loss, breakeven or no entry (the pattern never formed), plus the RR it made.
The page then compares the patterns across every trade. Subscribers' Backtest
Journal is separate and unchanged.
"""

from __future__ import annotations

import io
import json
import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from api.auth import require_owner

router = APIRouter()

# The entry patterns being compared (key → label). Keys are stored, so never rename one.
# Each entry model is tested on each POI: key = "<model>_<poi>", e.g. "h1_smc_fvg".
POIS: list[tuple[str, str]] = [
    ("fvg", "H4 FVG"),
    ("engulfing", "H4 Engulfing"),
    ("h4_key", "H4 fresh key level"),
    ("3cr", "4H / 2H 3CR"),
]
MODELS: list[tuple[str, str]] = [
    ("direct", "Direct entry"),
    ("h1_cisd", "1H CISD"),
    ("h1_engulfing", "1H Engulfing"),
    ("h2_engulfing", "2H Engulfing"),
    ("m5_cisd", "5M CISD"),
    ("m15_cisd", "15M CISD"),
]
ENTRY_TYPES: list[tuple[str, str]] = [
    (f"{m}_{p}", f"{ml} on {pl}") for p, pl in POIS for m, ml in MODELS
]
# Keys from earlier versions still load and save (one list with no POI; then
# 4H / 2H 3CR as entry models before they became a POI)
_LEGACY = {"h1_smc", "h1_engulfing", "h2_engulfing", "m5_cisd", "m5_smc", "m15_smc", "m15_cisd", "h4_3cr", "h2_3cr"} | {
    f"{m}_{p}" for m in ("h4_3cr", "h2_3cr") for p in ("fvg", "engulfing", "h4_key")} | {
    # SMC entries, taken off the list on 2026-10-24 (ticks already made stay stored)
    f"{m}_{p}" for m in ("h1_smc", "m5_smc", "m15_smc") for p in ("fvg", "engulfing", "h4_key", "3cr")}
_KEYS = {k for k, _ in ENTRY_TYPES} | _LEGACY
OUTCOMES = ("win", "loss", "be", "none")


@contextmanager
def _db(request: Request):
    conn = sqlite3.connect(request.app.state.config.db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


class EntryResult(BaseModel):
    outcome: str
    rr: Optional[float] = None
    takes: Optional[int] = None   # trades taken on this entry (re-entries after a stop-out); 1 when unset
    exit: Optional[str] = None    # when this entry's trade was closed: "YYYY-MM-DDTHH:MM" (each entry runs differently)


class TradeBody(BaseModel):
    trade_date: str
    instrument: str
    direction: str
    alert_type: str = ""
    notes: str = ""
    results: dict[str, EntryResult] = {}
    exit_date: Optional[str] = None   # YYYY-MM-DD the trade was closed (unset = still open / not recorded)


def _clean(body: TradeBody) -> tuple[str, str, str, str, str, str, Optional[str]]:
    if body.direction not in ("buy", "sell"):
        raise HTTPException(400, "direction must be buy or sell")
    if not body.instrument.strip() or not body.trade_date.strip():
        raise HTTPException(400, "pair and date are required")
    res = {}
    for k, r in body.results.items():
        if k not in _KEYS or r.outcome not in OUTCOMES:
            raise HTTPException(400, f"unknown entry type or outcome: {k}")
        # win: the RR it made; BE: the R it was closed at early (e.g. 0.5, or -0.3 on a rejection)
        if r.outcome == "win":
            rr = r.rr if r.rr is not None and 0 < r.rr <= 100 else None
        elif r.outcome == "be":
            rr = r.rr if r.rr is not None and -1 < r.rr < 100 and r.rr != 0 else None
        else:
            rr = None
        res[k] = {"outcome": r.outcome, "rr": rr}
        if r.outcome != "none" and r.takes is not None and 1 < r.takes <= 50:
            res[k]["takes"] = int(r.takes)
        ex = (r.exit or "").strip()[:16]
        if r.outcome != "none" and len(ex) >= 10 and ex[4] == "-" and ex[7] == "-":
            res[k]["exit"] = ex
    exit_date = (body.exit_date or "").strip()[:10] or None
    if exit_date and exit_date < body.trade_date.strip()[:10]:
        raise HTTPException(400, "the exit date can't be before the entry date")
    return (body.trade_date.strip()[:10], body.instrument.strip().upper()[:20], body.direction,
            body.alert_type.strip()[:40], body.notes.strip()[:4000], json.dumps(res), exit_date)


def _row(r: sqlite3.Row, images: Optional[dict] = None) -> dict:
    d = dict(r)
    d["results"] = json.loads(d.pop("results_json") or "{}")
    d["images"] = images or {}   # {slot: [image ids]} — slot = a POI key or an entry key
    return d


# ── Trade screenshots ─────────────────────────────────────────────────────────
# Several per "slot": a POI of the trade (its general chart) or one entry model
# under that POI. Stored as JPEG files on the data volume next to the database
# (not inside it, so the nightly Telegram backup stays small).
_POI_KEYS = {k for k, _ in POIS}
_SLOT_POI = {k: k for k in _POI_KEYS} | {f"{m}_{p}": p for p, _ in POIS for m, _ in MODELS}
MAX_UPLOAD = 15 * 1024 * 1024
MAX_PER_SLOT = 12


def _img_dir(request: Request) -> Path:
    d = Path(request.app.state.config.db_path).resolve().parent / "entry_images"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _images_by_trade(conn, uid: int) -> dict[int, dict]:
    out: dict[int, dict] = {}
    for r in conn.execute("SELECT id, test_id, slot FROM entry_test_images WHERE user_id = ? ORDER BY id", (uid,)):
        out.setdefault(r["test_id"], {}).setdefault(r["slot"], []).append(r["id"])
    return out


def _drop_image(request: Request, conn, row) -> None:
    conn.execute("DELETE FROM entry_test_images WHERE id = ?", (row["id"],))
    try:
        (_img_dir(request) / row["file_name"]).unlink(missing_ok=True)
    except OSError:
        pass


@router.get("/entry-tests/types")
def entry_types(request: Request):
    require_owner(request)
    return [{"key": k, "label": l} for k, l in ENTRY_TYPES]


@router.get("/entry-tests")
def list_trades(request: Request):
    u = require_owner(request)
    with _db(request) as conn:
        rows = conn.execute(
            "SELECT * FROM entry_tests WHERE user_id = ? ORDER BY trade_date DESC, id DESC", (u["id"],)).fetchall()
        imgs = _images_by_trade(conn, u["id"])
    return [_row(r, imgs.get(r["id"])) for r in rows]


@router.post("/entry-tests")
def create_trade(request: Request, body: TradeBody):
    u = require_owner(request)
    vals = _clean(body)
    with _db(request) as conn:
        cur = conn.execute(
            """INSERT INTO entry_tests (trade_date, instrument, direction, alert_type, notes, results_json, exit_date, user_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", vals + (u["id"],))
        row = conn.execute("SELECT * FROM entry_tests WHERE id = ?", (cur.lastrowid,)).fetchone()
    return _row(row)


@router.put("/entry-tests/{trade_id}")
def update_trade(trade_id: int, request: Request, body: TradeBody):
    u = require_owner(request)
    vals = _clean(body)
    with _db(request) as conn:
        cur = conn.execute(
            """UPDATE entry_tests SET trade_date = ?, instrument = ?, direction = ?, alert_type = ?, notes = ?,
                      results_json = ?, exit_date = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
               WHERE id = ? AND user_id = ?""", vals + (trade_id, u["id"]))
        if cur.rowcount == 0:
            raise HTTPException(404, "Trade not found")
        row = conn.execute("SELECT * FROM entry_tests WHERE id = ?", (trade_id,)).fetchone()
        imgs = _images_by_trade(conn, u["id"])
    return _row(row, imgs.get(trade_id))


@router.delete("/entry-tests/{trade_id}")
def delete_trade(trade_id: int, request: Request):
    u = require_owner(request)
    with _db(request) as conn:
        for img in conn.execute("SELECT id, file_name FROM entry_test_images WHERE test_id = ? AND user_id = ?",
                                (trade_id, u["id"])).fetchall():
            _drop_image(request, conn, img)
        conn.execute("DELETE FROM entry_tests WHERE id = ? AND user_id = ?", (trade_id, u["id"]))
    return {"ok": True}


@router.post("/entry-tests/{trade_id}/images/{slot}")
async def upload_image(trade_id: int, slot: str, request: Request, file: UploadFile = File(...)):
    """Add a screenshot to a trade: to one of its POIs, or to one entry under a POI."""
    u = require_owner(request)
    poi = _SLOT_POI.get(slot)
    if poi is None:
        raise HTTPException(400, "unknown POI or entry")
    raw = await file.read(MAX_UPLOAD + 1)
    if len(raw) > MAX_UPLOAD:
        raise HTTPException(413, "Image is too large (15 MB max)")
    try:
        from PIL import Image, ImageOps
        im = ImageOps.exif_transpose(Image.open(io.BytesIO(raw)))
        im = im.convert("RGB")
        im.thumbnail((2400, 2400))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=85, optimize=True)
    except Exception:
        raise HTTPException(400, "That file isn't an image")
    name = f"{uuid.uuid4().hex}.jpg"
    with _db(request) as conn:
        if not conn.execute("SELECT 1 FROM entry_tests WHERE id = ? AND user_id = ?", (trade_id, u["id"])).fetchone():
            raise HTTPException(404, "Trade not found")
        n = conn.execute("SELECT COUNT(*) FROM entry_test_images WHERE test_id = ? AND slot = ?", (trade_id, slot)).fetchone()[0]
        if n >= MAX_PER_SLOT:
            raise HTTPException(400, f"{MAX_PER_SLOT} images is the most for one POI or entry")
        (_img_dir(request) / name).write_bytes(buf.getvalue())
        cur = conn.execute("INSERT INTO entry_test_images (test_id, user_id, poi, slot, file_name) VALUES (?, ?, ?, ?, ?)",
                           (trade_id, u["id"], poi, slot, name))
    return {"id": cur.lastrowid, "slot": slot}


@router.get("/entry-tests/images/{image_id}")
def get_image(image_id: int, request: Request):
    u = require_owner(request)
    with _db(request) as conn:
        row = conn.execute("SELECT file_name FROM entry_test_images WHERE id = ? AND user_id = ?",
                           (image_id, u["id"])).fetchone()
    path = _img_dir(request) / row["file_name"] if row else None
    if not path or not path.is_file():
        raise HTTPException(404, "Image not found")
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=86400"})


@router.delete("/entry-tests/images/{image_id}")
def delete_image(image_id: int, request: Request):
    u = require_owner(request)
    with _db(request) as conn:
        row = conn.execute("SELECT id, file_name FROM entry_test_images WHERE id = ? AND user_id = ?",
                           (image_id, u["id"])).fetchone()
        if row:
            _drop_image(request, conn, row)
    return {"ok": True}

"""
Chart pictures for Telegram alerts ("📊 View chart").

Draws the pair's Daily or H4 candles up to the moment the alert fired, with the
alert's levels marked, as a PNG. Uses Pillow only (the server has 256 MB of
memory, so no matplotlib). Candles come from state/candles.py, levels from
alert_levels (saved when the alert was sent).
"""

from __future__ import annotations

import io
import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

W, H = 1100, 620
PAD_L, PAD_R, PAD_T, PAD_B = 18, 370, 78, 52
BG, GRID, INK, MUTED = (15, 17, 23), (34, 38, 50), (232, 234, 242), (123, 130, 150)
UP, DOWN = (34, 197, 94), (239, 68, 68)
COLORS = {
    "breaker": (248, 113, 113), "source": (52, 211, 153), "h4": (251, 191, 36),
    "ext": (167, 139, 250), "daily": (96, 165, 250), "h4lvl": (251, 146, 60),
}
N_CANDLES = {"D": 45, "H4": 60}
# The alert's own levels: all a subscriber sees. The owner also sees the chart's
# External high/low, D.A/D.V and H4.A/H4.V.
ALERT_KINDS = {"breaker", "source", "h4"}
WAT = timezone(timedelta(hours=1))


def _font(size: int):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:   # very old Pillow
        return ImageFont.load_default()


def save_alert_levels(conn, alert_id: int, levels: list[dict], meta: dict) -> None:
    """levels: {"y", "label", "kind", "tf": "D"|"H4"|"both"}; meta: title bits."""
    conn.execute("""CREATE TABLE IF NOT EXISTS alert_levels (
        alert_id INTEGER PRIMARY KEY, levels TEXT NOT NULL, meta TEXT NOT NULL,
        file_d TEXT, file_h4 TEXT)""")
    conn.execute("INSERT OR REPLACE INTO alert_levels (alert_id, levels, meta) VALUES (?, ?, ?)",
                 (alert_id, json.dumps([l for l in levels if l.get("y") is not None]), json.dumps(meta)))
    conn.commit()


def load_alert_levels(conn, alert_id: int) -> Optional[dict]:
    try:
        row = conn.execute("SELECT levels, meta, file_d, file_h4 FROM alert_levels WHERE alert_id = ?",
                           (alert_id,)).fetchone()
    except Exception:
        return None
    if not row:
        return None
    return {"levels": json.loads(row[0]), "meta": json.loads(row[1]), "file_d": row[2], "file_h4": row[3]}


def remember_file_id(conn, alert_id: int, tf: str, file_id: str) -> None:
    col = "file_d" if tf == "D" else "file_h4"
    conn.execute(f"UPDATE alert_levels SET {col} = ? WHERE alert_id = ?", (file_id, alert_id))
    conn.commit()


def render(instrument: str, tf: str, candles: list[tuple], levels: list[dict], meta: dict,
           fmt=lambda v: f"{v:.5f}", full: bool = False) -> bytes:
    """candles: (ts, o, h, l, c) oldest first. Returns PNG bytes."""
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    f_title, f_sub, f_lbl, f_ax = _font(22), _font(15), _font(14), _font(13)

    tf_name = "Daily" if tf == "D" else "4H"
    side = meta.get("side", "")
    d.text((PAD_L, 14), f"{instrument} · {tf_name} · {side}", font=f_title, fill=INK)
    d.text((PAD_L, 44), meta.get("subtitle", ""), font=f_sub, fill=MUTED)

    lv = [l for l in levels if l.get("tf", "both") in ("both", tf) and (full or l.get("kind") in ALERT_KINDS)]
    if not candles:
        d.text((PAD_L, H // 2), "No candles yet — they arrive with the next 4H close.", font=f_sub, fill=MUTED)
        return _png(img)

    lo = min(c[3] for c in candles)
    hi = max(c[2] for c in candles)
    span = hi - lo or abs(hi) * 0.001 or 1.0
    # Levels far outside the candles would squash the chart: keep those within
    # two candle ranges, list the rest as off-chart.
    shown = [l for l in lv if lo - 2 * span <= l["y"] <= hi + 2 * span]
    for l in shown:
        lo, hi = min(lo, l["y"]), max(hi, l["y"])
    pad = (hi - lo) * 0.06 or span * 0.06
    lo, hi = lo - pad, hi + pad

    x0, x1, y0, y1 = PAD_L, W - PAD_R, PAD_T, H - PAD_B
    py = lambda v: y1 - (v - lo) / (hi - lo) * (y1 - y0)
    n = len(candles)
    step = (x1 - x0) / max(n, 1)
    bw = max(2, int(step * 0.62))

    # grid + price axis
    for k in range(6):
        v = lo + (hi - lo) * k / 5
        y = py(v)
        d.line([(x0, y), (x1, y)], fill=GRID, width=1)
        d.text((x1 + 6, y - 8), fmt(v), font=f_ax, fill=MUTED)

    # candles
    for i, (_, o, h, l, c) in enumerate(candles):
        cx = x0 + step * (i + 0.5)
        col = UP if c >= o else DOWN
        d.line([(cx, py(h)), (cx, py(l))], fill=col, width=1)
        top, bot = py(max(o, c)), py(min(o, c))
        d.rectangle([cx - bw / 2, top, cx + bw / 2, max(bot, top + 1)], fill=col)

    # alert marker on the last candle
    lx = x0 + step * (n - 0.5)
    d.line([(lx, y0), (lx, y1)], fill=(80, 86, 104), width=1)
    d.text((lx - 36 if lx > x0 + 60 else lx + 4, y0 - 18), "alert", font=f_ax, fill=MUTED)

    # time axis: candle open times in WAT
    ticks = sorted({round(k * (n - 1) / 5) for k in range(6)}) if n > 1 else [0]
    for i in ticks:
        try:
            t = datetime.fromisoformat(candles[i][0]).astimezone(WAT)
        except Exception:
            continue
        txt = t.strftime("%d %b") if tf == "D" else t.strftime("%d %b %H:%M")
        cx = x0 + step * (i + 0.5)
        tw = f_ax.getlength(txt)
        d.text((min(max(cx - tw / 2, x0), x1 - tw), y1 + 6), txt, font=f_ax, fill=MUTED)

    # levels: dashed line + label in the right margin, labels kept apart
    used: list[float] = []
    for l in sorted(shown, key=lambda l: -l["y"]):
        col = COLORS.get(l.get("kind", ""), INK)
        y = py(l["y"])
        # Start at the candle that formed the level (if known), not across the chart
        xstart = x0
        if l.get("t0"):
            i0 = max((i for i, cd in enumerate(candles) if cd[0] <= l["t0"]), default=None)
            if i0 is not None:
                xstart = x0 + step * (i0 + 0.5) - bw / 2
                d.ellipse([xstart - 3, y - 3, xstart + 3, y + 3], fill=col)
        for xs in range(int(xstart), int(x1), 12):
            d.line([(xs, y), (min(xs + 7, x1), y)], fill=col, width=2)
        ty = y - 8
        while any(abs(ty - u) < 17 for u in used):
            ty += 17
        used.append(ty)
        own = l.get("kind") in ALERT_KINDS
        if own:   # price tag on the axis; the name sits beside it
            txt = fmt(l["y"])
            tw = f_ax.getlength(txt)
            d.rectangle([x1 + 2, y - 10, x1 + tw + 12, y + 10], fill=col)
            d.text((x1 + 7, y - 8), txt, font=f_ax, fill=BG)
        d.text((x1 + 86, ty), l["label"] if own else f"{l['label']}  {fmt(l['y'])}", font=f_lbl, fill=col)

    off = [l for l in lv if l not in shown]
    foot = "Candle open times in WAT"
    if off:
        foot += "   ·   Off chart: " + " · ".join(f"{l['label']} {fmt(l['y'])}" for l in off)
    d.text((PAD_L, H - 20), foot, font=f_ax, fill=MUTED)
    when = meta.get("fired_at")
    if when:
        d.text((W - PAD_R + 6, 50), f"Alert {when}", font=f_ax, fill=MUTED)
    return _png(img)


def _png(img) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def _form(l: dict, side: str) -> tuple[str, str]:
    """(timeframe, shape) a level was formed on, from its kind and label."""
    lab, kind = l.get("label", ""), l.get("kind", "")
    if kind == "breaker" or kind in ("ext", "daily"):
        return "D", "ext"
    if kind == "source":
        return ("D", "OC") if "OC" in lab else ("D", "ext")
    if "OC" in lab:
        return "H4", "OC"
    if "A broken" in lab or lab == "H4.A":
        return "H4", "A"
    if "V broken" in lab or lab == "H4.V":
        return "H4", "V"
    return "H4", ("A" if side == "BUY" else "V")   # H4 Breaker / H4 breakout


def level_origin(level: float, shape: str, candles: list[tuple]) -> Optional[str]:
    """Open time of the most recent candle that formed this level with this
    shape (A: up candle then down, body high; V: down then up, body low; OC:
    first of two same-direction candles, its close; ext: a wick or body edge).
    None when nothing matches."""
    tol = max(abs(level) * 1e-7, 1e-9)
    eq = lambda v: abs(v - level) <= tol
    for i in range(len(candles) - 1, -1, -1):
        ts, o, h, lo, c = candles[i]
        bull = c >= o
        nx = candles[i + 1] if i + 1 < len(candles) else None
        nbull = nx is not None and nx[4] >= nx[1]
        if shape == "ext":
            if eq(h) or eq(lo) or eq(max(o, c)) or eq(min(o, c)):
                return ts
        elif nx is None:
            continue
        elif shape == "A" and bull and not nbull and eq(max(o, c)):
            return ts
        elif shape == "V" and not bull and nbull and eq(min(o, c)):
            return ts
        elif shape == "OC" and bull == nbull and eq(c):
            return ts
    return None


def candles_until(conn, instrument: str, tf: str, until_iso: str) -> list[tuple]:
    """The last N candles that opened at or before the alert time."""
    from state.candles import ensure_table
    ensure_table(conn)
    rows = conn.execute(
        "SELECT ts, o, h, l, c FROM candles WHERE instrument = ? AND tf = ? AND ts <= ? ORDER BY ts DESC LIMIT ?",
        (instrument, tf, until_iso, N_CANDLES[tf])).fetchall()
    return [tuple(r) for r in reversed(rows)]


def picture_for_alert(conn, alert_id: int, tf: str, full: bool = False) -> Optional[tuple[bytes, str, int]]:
    """(png, caption, number of candles drawn) for an alert, or None if unknown."""
    from config import fmt_price
    info = load_alert_levels(conn, alert_id)
    row = conn.execute("SELECT instrument, fired_at FROM alerts WHERE id = ?", (alert_id,)).fetchone()
    if not info or not row:
        return None
    instrument, fired = row[0], row[1]
    try:
        fired_iso = datetime.fromisoformat(str(fired).replace("Z", "+00:00")).isoformat()
    except Exception:
        fired_iso = str(fired)
    # candles are stored with +00:00; alerts.fired_at may be naive UTC
    until = fired_iso if "+" in fired_iso else fired_iso + "+00:00"
    candles = candles_until(conn, instrument, tf, until)
    other = candles_until(conn, instrument, "H4" if tf == "D" else "D", until)
    h4set, dset = (other, candles) if tf == "D" else (candles, other)
    side = info["meta"].get("side", "")
    levels = []
    for l in info["levels"]:
        ftf, shape = _form(l, side)
        levels.append(dict(l, t0=level_origin(l["y"], shape, h4set[:-1] if ftf == "H4" else dset)))
    meta = dict(info["meta"])
    try:
        meta["fired_at"] = datetime.fromisoformat(until).astimezone(WAT).strftime("%d %b %H:%M") + " WAT"
    except Exception:
        meta["fired_at"] = str(fired)[:16].replace("T", " ") + " UTC"
    png = render(instrument, tf, candles, levels, meta, fmt=lambda v: fmt_price(instrument, v), full=full)
    caption = f"{instrument} · {'Daily' if tf == 'D' else '4H'} · {meta.get('side', '')} · {meta.get('subtitle', '')}"
    return png, caption[:1000], len(candles)

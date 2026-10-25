"""
TradingView Pine Script webhook receiver.

Pine Script fires JSON payloads to POST /api/tv-webhook when formations,
breakouts, retests, and H4 confirmations are detected. This replaces the
Twelve Data polling scheduler with TradingView's own chart data.

Event types received from Pine:
  BREAKOUT        — Daily candle closed beyond the most recent External high or
                    low; a break the other way replaces it (no Telegram)
  RETEST          — H4 wick touched a Daily reaction level exactly (Breaker,
                    inside-range V/A or OC, post-breakout OC)
  RETEST_CANCELLED — the reaction failed (H4 closed through the level)
  CONFIRMED       — Origin: H4 closed beyond the latest H4 A/V → Telegram alert
  H4_CONTINUATION — H4 Breaker retest, H4 OC rejection or H4 back in line
                    after a Daily reaction → Telegram alert to everyone
  PRICE_UPDATE    — price + chart snapshot for the Live Chart Board
  INVALIDATED     — older scripts only; current scripts never send it
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import hmac
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from alerts.formatter import format_alert, format_entry_alert, short_text, with_data_source
from config import SYMBOL_ALIASES, is_synthetic, fmt_price, normalize_symbol, tagged
from state.instruments import register_synthetic
from state.candles import upsert as upsert_candles, tf_name as candles_tf_name
from alerts.chart_image import save_alert_levels
from alerts.telegram import chart_button
from alerts.formatter import _SOURCE_NAMES
from api.alert_prefs import confirmation_kind, get_alert_prefs, get_alert_style, get_engulf_mode, engulf_wanted
from alerts.telegram import send_alert
from config import pip_size_for
from data.models import (
    AlertClassification,
    AlertRecord,
    BreakoutClassification,
    DailyBreakout,
    Direction,
    Formation,
    FormationType,
    H4BreakoutEvent,
    ReactionSource,
    ReactionSourceType,
    Timeframe,
)
from state.repository import (
    InstrumentStateRow,
    deactivate_all_breakouts,
    deactivate_reaction_sources_for_breakout,
    get_active_breakout,
    get_active_reaction_sources,
    get_instrument_state,
    insert_alert,
    insert_breakout,
    insert_formation,
    insert_reaction_sources,
    upsert_instrument_state,
)

import json as _json

logger = logging.getLogger(__name__)
router = APIRouter()



def _subscription_active(role, plan, plan_expires_at) -> bool:
    """Owners and lifetime accounts never expire; everyone else only until plan_expires_at."""
    if role == "OWNER" or plan == "LIFETIME" or not plan_expires_at:
        return True
    try:
        exp = datetime.fromisoformat(str(plan_expires_at).replace("Z", "+00:00"))
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return exp > datetime.now(timezone.utc)
    except Exception:
        return True


def _resolve_chat(config, user_id, chat_id, role, plan, plan_expires_at):
    """Where a user-owned alert (price / entry pattern) should be delivered.
    Only alerts with no owning user, or owned by the platform owner, may fall back
    to the owner's global chat — a subscriber's alert must never reach the owner,
    and an expired or revoked subscriber's alert is not delivered at all."""
    if user_id is None:
        return config.telegram_chat_id
    if role is None:  # account revoked/deleted
        return None
    if not _subscription_active(role, plan, plan_expires_at):
        return None
    if chat_id:
        return chat_id
    return config.telegram_chat_id if role == "OWNER" else None


async def _deliver_alert(conn, config, instrument: str, alert_text: str,
                         h4_class: Optional[str] = None, alert_id: Optional[int] = None,
                         pref: Optional[str] = None, engulf_wick: Optional[bool] = None) -> None:
    """Send alert_text to every active user whose watched_instruments includes instrument.

    h4_class: External / Internal of the H4 confirmation this alert belongs to
    (the Origin itself, or the confirmation a continuation follows). Each user
    receives it only if they allow that type. None = no such filter."""
    instr_norm = instrument.replace("/", "").upper()
    synthetic = is_synthetic(instr_norm)
    kind = confirmation_kind(h4_class) if h4_class is not None else None
    recipients = conn.execute(
        "SELECT id, telegram_chat_id, watched_instruments, role, plan, plan_expires_at FROM users "
        "WHERE telegram_chat_id IS NOT NULL AND telegram_chat_id != ''"
    ).fetchall()
    chats: list[str] = []
    short_chats: set[str] = set()   # people who chose the Short message style
    for rec in recipients:
        if not _subscription_active(rec["role"], rec["plan"], rec["plan_expires_at"]):
            continue  # expired subscriber — no more signals

        raw = rec["watched_instruments"]
        if raw:
            watched = [w.replace("/", "").upper() for w in _json.loads(raw)]
            if instr_norm not in watched:
                continue
        elif synthetic and rec["role"] != "OWNER":
            continue  # synthetics are opt-in: only subscribers who ticked them get them
        prefs = get_alert_prefs(conn, rec["id"], rec["role"])
        if kind and not prefs[kind]:
            continue  # user switched this confirmation type off
        if pref and not prefs.get(pref, True):
            continue  # user switched this alert type off (Origin / a continuation type / engulfing)
        if engulf_wick is not None and not engulf_wanted(get_engulf_mode(conn, rec["id"]), engulf_wick):
            continue  # this kind of engulfing (wick / body only) isn't the one they chose
        chats.append(rec["telegram_chat_id"])
        if get_alert_style(conn, rec["id"]) == "short":
            short_chats.add(rec["telegram_chat_id"])

    # "📊 View chart" under the alert: tapping it sends the chart picture
    markup = chart_button(alert_id) if alert_id else None
    short = short_text(alert_text)

    # Many chats at once, paced under Telegram's limit (see alerts/telegram.py)
    sem = asyncio.Semaphore(20)

    async def _one(chat_id: str) -> bool:
        async with sem:
            text = short if chat_id in short_chats else alert_text
            if markup is not None:
                return await send_alert(config.telegram_bot_token, chat_id, text, reply_markup=markup)
            return await send_alert(config.telegram_bot_token, chat_id, text)

    if chats:
        results = await asyncio.gather(*(_one(c) for c in chats))
        logger.info("%s alert delivered to %d/%d chats", instrument, sum(1 for r in results if r), len(chats))

    # Fallback only when nobody has linked Telegram at all. Recipients filtered
    # out by their own choices must stay filtered, never rerouted.
    if not recipients and config.telegram_chat_id:
        owner = conn.execute("SELECT id FROM users WHERE role = 'OWNER' LIMIT 1").fetchone()
        if kind and not get_alert_prefs(conn, owner[0] if owner else None, "OWNER")[kind]:
            return
        await send_alert(config.telegram_bot_token, config.telegram_chat_id, alert_text)


# TradingView gives up on a webhook after a few seconds and marks it "failed"
# (even though it was processed). Telegram sends to many subscribers can take
# longer, so they run after the reply instead of before it.
_bg_tasks: set = set()


def _in_background(coro) -> None:
    task = asyncio.get_running_loop().create_task(coro)
    _bg_tasks.add(task)

    def _done(t):
        _bg_tasks.discard(t)
        if not t.cancelled() and t.exception() is not None:
            logger.error("Background Telegram delivery failed: %r", t.exception())
    task.add_done_callback(_done)


# ── Pydantic model for incoming Pine payloads ─────────────────────────────────

class TVWebhookPayload(BaseModel):
    secret: str
    type: str                           # BREAKOUT | RETEST | RETEST_CANCELLED | CONFIRMED | INVALIDATED | PRICE_UPDATE
    instrument: str                     # e.g. "USDCHF" or "USD/CHF"
    direction: Optional[str] = None     # "bullish" | "bearish"
    level: Optional[float] = None       # daily broken level (BREAKOUT)
    source: Optional[str] = None        # "daily_breaker" | "inside_range" | "post_breakout_oc" | "post_breakout_v" | "post_breakout_fvg" | "inside_fvg"
    source_level2: Optional[float] = None  # Daily FVG reactions: the far edge of the gap (source_level = the near edge)
    fvg_low: Optional[float] = None     # H4_CONTINUATION h4_fvg: the gap
    fvg_high: Optional[float] = None
    h4_class: Optional[str] = None      # "external" | "internal" (CONFIRMED, and back-in-line continuations)
    breakout_level: Optional[float] = None   # daily broken level
    source_level: Optional[float] = None     # the Daily level that reacted (Breaker, inside-range V/A or OC, post-breakout OC)
    h4_level: Optional[float] = None    # H4 formation level (CONFIRMED / H4_CONTINUATION)
    cont_type: Optional[str] = None    # H4_CONTINUATION sub-type: breakout_cont | inline_break | breaker_origin | breaker_cont | oc_cont
    price: Optional[float] = None      # current close price (PRICE_UPDATE / ENTRY_CONFIRMATION)
    pattern: Optional[str] = None      # ENTRY_CONFIRMATION: "pcl" | "engulfing_sweep"
    timeframe: Optional[str] = None    # ENTRY_CONFIRMATION: pine timeframe.period ("60" / "120")
    swept_level: Optional[float] = None  # ENTRY_CONFIRMATION: body level that was swept
    snapshot: Optional[dict] = None    # PRICE_UPDATE: chart stage + levels (Bias Pointer 2026-10-16+)
    source_kind: Optional[str] = None  # inside_range reactions: "v_shape" | "a_shape" | "oc"
    level_type: Optional[str] = None   # which daily level broke: external | internal | inner_internal | sub_internal
    range_level: Optional[float] = None  # BREAKOUT: the other side of the range that was broken
    exchange: Optional[str] = None     # TradingView syminfo.prefix, e.g. "DERIV" for synthetic indices
    wk_rel: Optional[str] = None       # Weekly storyline: confirmed | inline | against
    wk_dir: Optional[str] = None
    wk_level: Optional[float] = None
    wk_src: Optional[str] = None
    wk_src_level: Optional[float] = None
    wk_cls: Optional[str] = None       # external | internal (Weekly-confirmed Daily breakout)
    eng_wick: Optional[bool] = None    # H4 engulfing that also closed beyond the previous candle's wick
    bar: Optional[list] = None         # PRICE_UPDATE: the H4 candle that just closed [t_ms, o, h, l, c]
    dbar: Optional[list] = None        # PRICE_UPDATE: the last completed Daily candle
    tf: Optional[str] = None           # HISTORY: "D" or "240"
    bars: Optional[list] = None        # HISTORY: candles, oldest first


# Bias Pointer events are only meaningful from the 4H chart. Alerts created on any
# other timeframe run the H4 logic on the wrong candles, so they are ignored.
BIAS_EVENTS = {"BREAKOUT", "RETEST", "RETEST_CANCELLED", "CONFIRMED", "INVALIDATED",
               "H4_CONTINUATION", "PRICE_UPDATE", "HISTORY"}
BIAS_TIMEFRAME = "240"


def _source_type_from_str(source: Optional[str], kind: Optional[str] = None) -> ReactionSourceType:
    if source == "post_breakout_oc":
        return ReactionSourceType.POST_BREAKOUT_DAILY_OC
    if source == "post_breakout_v":
        return ReactionSourceType.AV_AFTER_BREAKOUT
    if source == "post_breakout_fvg":
        return ReactionSourceType.FVG_AFTER_BREAKOUT
    if source == "inside_fvg":
        return ReactionSourceType.FVG_INSIDE_RANGE
    if source == "inside_range":
        return ReactionSourceType.OC_INSIDE_RANGE if kind == "oc" else ReactionSourceType.AV_INSIDE_RANGE
    return ReactionSourceType.DAILY_BREAKER


# TradingView's published webhook source addresses (support article "About webhooks").
TRADINGVIEW_IPS = {"52.89.214.238", "34.212.75.30", "54.218.53.128", "52.32.178.7"}


async def _warn_owner_rejected(conn, config) -> None:
    """Tell the owner (at most once a day) that TradingView messages are being refused,
    so a secret mismatch can never silently stop every signal."""
    try:
        from alerts.reminders import notify_once
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        await notify_once(
            conn, config, f"tv_rejected:{day}", config.telegram_chat_id,
            "⚠️ TradingView messages are being REJECTED by the server (webhook secret doesn't match), "
            "so no bias alerts can come through.\n\nThe Webhook Secret in your TradingView indicator settings "
            "must match the server's TV_WEBHOOK_SECRET. Ask Claude to check the server logs.")
    except Exception as exc:
        logger.warning("Could not warn owner about rejected webhooks: %s", exc)


# ── Main endpoint ─────────────────────────────────────────────────────────────

@router.post("/tv-webhook")
async def tv_webhook(payload: TVWebhookPayload, request: Request) -> dict:
    config = request.app.state.config
    conn   = request.app.state.conn

    # Source check: TradingView sends webhooks only from its published addresses.
    # "observe" (default) logs the address; "enforce" refuses anything else.
    ip = request.headers.get("fly-client-ip") or (request.client.host if request.client else "")
    from_tv = ip in TRADINGVIEW_IPS
    mode = os.getenv("TV_IP_ALLOWLIST", "observe").lower()
    logger.info("TV webhook source %s (tradingview=%s, mode=%s)", ip, from_tv, mode)
    if mode == "enforce" and not from_tv:
        logger.warning("TV webhook refused: source %s is not a TradingView address", ip)
        await _warn_owner_rejected(conn, config)
        raise HTTPException(status_code=403, detail="Source not allowed")

    # Verify the shared secret. A fingerprint (length + hash prefix, never the value)
    # of what TradingView sent is logged so a mismatch can be diagnosed.
    got = payload.secret or ""
    fp = f"len={len(got)} sha256={hashlib.sha256(got.encode()).hexdigest()[:12]}"
    if config.tv_webhook_secret:
        if not hmac.compare_digest(got.encode(), config.tv_webhook_secret.encode()):
            logger.warning("TV webhook rejected: bad secret (instrument=%s, received %s)", payload.instrument, fp)
            await _warn_owner_rejected(conn, config)
            raise HTTPException(status_code=401, detail="Invalid webhook secret")
    else:
        # No secret configured on the server: accept (as before 2026-10-15) so signals
        # never stop silently, but log loudly until TV_WEBHOOK_SECRET is set.
        logger.warning("TV webhook accepted WITHOUT secret check — TV_WEBHOOK_SECRET is empty (received %s)", fp)

    # Normalise instrument name: "USD/CHF" → "USDCHF", and broker spellings
    # (JP225, USOIL, ...) to the platform's names so the board and alerts match.
    instrument = normalize_symbol(payload.instrument)
    event_type = payload.type.upper()

    # A Deriv synthetic index joins the platform the first time its chart reports.
    if (payload.exchange or "").upper() == "DERIV":
        try:
            if register_synthetic(conn, config, instrument):
                logger.info("New Deriv synthetic registered: %s", instrument)
        except Exception as exc:
            logger.warning("Synthetic registration failed for %s: %s", instrument, exc)

    # Heartbeat for the feed health monitor — any authenticated webhook counts.
    try:
        conn.execute(
            "INSERT INTO webhook_heartbeats (instrument, last_seen_at, last_type) VALUES (?, ?, ?) "
            "ON CONFLICT(instrument) DO UPDATE SET last_seen_at = excluded.last_seen_at, last_type = excluded.last_type",
            (instrument, datetime.now(timezone.utc).isoformat(), event_type),
        )
        conn.commit()
    except Exception as exc:  # never block alert processing on the heartbeat
        logger.warning("Heartbeat write failed for %s: %s", instrument, exc)

    logger.info("TV webhook: %s %s", event_type, instrument)

    # Older scripts send no timeframe; accept those as before.
    if event_type in BIAS_EVENTS and payload.timeframe and payload.timeframe != BIAS_TIMEFRAME:
        logger.warning("TV webhook ignored: %s %s came from a %s chart, not 4H",
                       event_type, instrument, payload.timeframe)
        return {"status": "ignored", "reason": "not a 4H chart"}

    if event_type == "BREAKOUT":
        await _handle_breakout(conn, config, instrument, payload)
    elif event_type == "RETEST":
        _handle_retest(conn, config, instrument, payload)
    elif event_type == "RETEST_CANCELLED":
        _handle_retest_cancelled(conn, instrument)
    elif event_type == "CONFIRMED":
        await _handle_confirmed(conn, config, instrument, payload)
    elif event_type == "INVALIDATED":
        _handle_invalidated(conn, instrument)
    elif event_type == "H4_CONTINUATION":
        await _handle_h4_continuation(conn, config, instrument, payload)
    elif event_type == "ENTRY_CONFIRMATION":
        await _handle_entry_confirmation(conn, config, instrument, payload)
    elif event_type == "PRICE_UPDATE":
        _store_candles(conn, instrument, payload)
        await _handle_price_update(conn, config, instrument, payload)
    elif event_type == "HISTORY":
        tf = candles_tf_name(payload.tf)
        if tf:
            n = upsert_candles(conn, instrument, tf, payload.bars)
            logger.info("%s candle history stored: %d %s candles", instrument, n, tf)
    else:
        logger.warning("Unknown TV webhook type: %s", event_type)

    return {"status": "ok"}


# ── Event handlers ────────────────────────────────────────────────────────────

_CONT_LEVEL_NAMES = {"inline_break": "H4 breakout (new H4 Breaker)", "breakout_cont": "H4 breakout", "daily_react": "H4 breakout",
                     "breaker_origin": "H4 Breaker", "breaker_cont": "H4 Breaker", "oc_cont": "H4 OC",
                     "h4_fvg": "High of the candle before the breakout (FVG edge)"}
_CONT_TITLES = {"inline_break": "H4 breakout in line with the Daily", "breakout_cont": "H4 back in line with the Daily",
                "daily_react": "Daily reaction + H4 breakout",
                "breaker_origin": "H4 Breaker Origin", "breaker_cont": "H4 Breaker Continuation",
                "oc_cont": "H4 OC Continuation", "h4_fvg": "H4 FVG candle after breakout"}


def _save_chart_levels(conn, instrument: str, alert_id: int, direction: Direction, breaker: Optional[float],
                       source: Optional[tuple] = None, h4: Optional[tuple] = None, subtitle: str = "") -> None:
    """Levels for this alert's chart picture: the alert's own levels plus the
    chart's External high/low, D.A/D.V and H4 A/V at that moment. Never blocks."""
    try:
        import json as _js
        levels = [{"y": breaker, "label": "Daily Breaker", "kind": "breaker", "tf": "both"}]
        if source and source[0] is not None and (breaker is None or abs(source[0] - breaker) > 1e-12):
            levels.append({"y": source[0], "label": source[1].replace(" inside the range", " (in range)") + " · reaction", "kind": "source", "tf": "both"})
        if h4 and h4[0] is not None:
            levels.append({"y": h4[0], "label": h4[1], "kind": "h4", "tf": "both"})
        row = conn.execute("SELECT snapshot FROM chart_snapshots WHERE instrument = ?", (instrument,)).fetchone()
        snap = _js.loads(row[0]) if row and row[0] else {}
        for key, label, kind, tf in (("ext_hi", "External high", "ext", "D"), ("ext_lo", "External low", "ext", "D"),
                                     ("d_a", "D.A", "daily", "D"), ("d_v", "D.V", "daily", "D"),
                                     ("h4_a", "H4.A", "h4lvl", "H4"), ("h4_v", "H4.V", "h4lvl", "H4")):
            if snap.get(key) is not None:
                levels.append({"y": float(snap[key]), "label": label, "kind": kind, "tf": tf})
        save_alert_levels(conn, alert_id, levels,
                          {"side": "BUY" if direction == Direction.BULLISH else "SELL", "subtitle": subtitle})
    except Exception as exc:
        logger.warning("Chart levels not saved for alert %s: %s", alert_id, exc)


def _store_candles(conn, instrument: str, payload: "TVWebhookPayload") -> None:
    """Keep the candles the chart just closed, for chart pictures. Never blocks alerts."""
    try:
        if payload.bar:
            upsert_candles(conn, instrument, "H4", [payload.bar])
        if payload.dbar:
            upsert_candles(conn, instrument, "D", [payload.dbar])
    except Exception as exc:
        logger.warning("Candle store failed for %s: %s", instrument, exc)


def _ensure_breakout(conn, config, instrument: str, direction: Direction,
                     level: Optional[float], event: str) -> DailyBreakout:
    """The active breakout this event belongs to.

    The chart is the source of truth. If the server has no breakout, or holds one
    in the other direction / at a different level (a BREAKOUT or INVALIDATED
    webhook was missed — e.g. sent while delivery was down), replace it from the
    event's own data so the alert and the dashboard never show the wrong setup.
    """
    breakout = get_active_breakout(conn, instrument)
    tol = config.level_tolerance_pips * pip_size_for(instrument)
    if breakout is not None and breakout.direction == direction and (
            level is None or abs(breakout.broken_level - level) <= tol):
        return breakout
    if breakout is not None:
        logger.warning("%s %s %s doesn't match the stored %s breakout @ %.5f — resyncing from the chart",
                       instrument, event, direction.value, breakout.direction.value, breakout.broken_level)
        deactivate_reaction_sources_for_breakout(conn, breakout.db_id)
    deactivate_all_breakouts(conn, instrument)
    breakout = DailyBreakout(
        instrument=instrument,
        direction=direction,
        broken_level=level if level is not None else 0.0,
        broken_type=FormationType.A_SHAPE if direction == Direction.BULLISH else FormationType.V_SHAPE,
        breakout_ts=datetime.utcnow(),
    )
    breakout.db_id = insert_breakout(conn, breakout)
    logger.info("%s breakout record created from %s payload", instrument, event)
    return breakout


# External / Internal of the setup's latest H4 confirmation (Origin or "back in
# line"), per instrument. Continuations carry it, so someone who doesn't get
# Internal confirmations doesn't get the continuations that follow one either.
def _set_setup_class(conn, instrument: str, cls: Optional[str]) -> None:
    key = f"setup_h4_class:{instrument}"
    if cls:
        conn.execute("INSERT OR REPLACE INTO user_config (key, value, updated_at) VALUES (?, ?, datetime('now'))",
                     (key, cls))
    else:
        conn.execute("DELETE FROM user_config WHERE key = ?", (key,))
    conn.commit()


def _setup_class(conn, instrument: str, breakout_id: Optional[int] = None) -> Optional[str]:
    row = conn.execute("SELECT value FROM user_config WHERE key = ?", (f"setup_h4_class:{instrument}",)).fetchone()
    if row:
        return row[0]
    if breakout_id is None:
        return None
    # Not recorded (setup confirmed before this was kept): read it from this
    # setup's latest Origin (stored class) or "back in line" alert (named in its text)
    for r in conn.execute(
            "SELECT h4_classification, alert_text FROM alerts WHERE daily_breakout_id = ? ORDER BY id DESC",
            (breakout_id,)).fetchall():
        if r[0] in ("external", "internal"):
            return r[0]
        txt = r[1] or ""
        if "H4 External breakout @" in txt:
            return "external"
        if "H4 Internal breakout @" in txt:
            return "internal"
    return None


async def _handle_breakout(conn, config, instrument: str, payload: TVWebhookPayload) -> None:
    direction = Direction(payload.direction)
    broken_type = FormationType.A_SHAPE if direction == Direction.BULLISH else FormationType.V_SHAPE
    prev = conn.execute("SELECT direction FROM daily_breakouts WHERE instrument = ? AND is_active = 1 "
                        "ORDER BY id DESC LIMIT 1", (instrument,)).fetchone()
    if not prev or prev[0] != direction.value:
        _set_setup_class(conn, instrument, None)   # direction changed: no H4 confirmation yet

    # Deactivate any prior breakout and its reaction sources
    old_state = get_instrument_state(conn, instrument)
    if old_state and old_state.active_breakout_id:
        deactivate_reaction_sources_for_breakout(conn, old_state.active_breakout_id)
    deactivate_all_breakouts(conn, instrument)

    # Create new breakout record
    breakout = DailyBreakout(
        instrument=instrument,
        direction=direction,
        broken_level=payload.level,
        broken_type=broken_type,
        breakout_ts=datetime.utcnow(),
    )
    breakout_id = insert_breakout(conn, breakout)
    breakout.db_id = breakout_id

    # Create Daily Breaker reaction source (the broken A/V level ± tolerance band)
    pip_size = pip_size_for(instrument)
    tol = config.level_tolerance_pips * pip_size
    source = ReactionSource(
        instrument=instrument,
        source_type=ReactionSourceType.DAILY_BREAKER,
        direction=direction,
        level=payload.level,
        level_band_low=payload.level - tol,
        level_band_high=payload.level + tol,
        daily_breakout_ts=datetime.utcnow(),
    )
    src_ids = insert_reaction_sources(conn, [source], breakout_id)

    upsert_instrument_state(conn, InstrumentStateRow(
        instrument=instrument,
        last_daily_candle_ts=None,
        last_h4_candle_ts=None,
        active_breakout_id=breakout_id,
        retest_in_progress=False,
        active_reaction_src_id=None,
        updated_at=datetime.utcnow(),
        continuation_mode=False,
        last_alert_h4_ts=None,
        last_h4_breaker_level=None,
        retest_started_h4_ts=None,
    ))

    logger.info("%s BREAKOUT %s %s @ %.5f (breakout_id=%d)", instrument, payload.level_type or "", payload.direction,
                payload.level, breakout_id)


def _handle_retest(conn, config, instrument: str, payload: TVWebhookPayload) -> None:
    state = get_instrument_state(conn, instrument)

    if payload.direction is not None:
        # Creates or resyncs the breakout record when the server missed it
        active_breakout_id = _ensure_breakout(conn, config, instrument, Direction(payload.direction),
                                              payload.breakout_level, "RETEST").db_id
    elif state is not None and state.active_breakout_id is not None:
        active_breakout_id = state.active_breakout_id
    else:
        logger.warning("%s RETEST received but no active breakout and no direction — ignored", instrument)
        return

    # Look up existing reaction source for the active breakout direction
    sources = get_active_reaction_sources(conn, instrument)
    src_type = _source_type_from_str(payload.source)
    matched = next((s for s in sources if s.source_type == src_type), None)

    upsert_instrument_state(conn, InstrumentStateRow(
        instrument=instrument,
        last_daily_candle_ts=state.last_daily_candle_ts if state else None,
        last_h4_candle_ts=state.last_h4_candle_ts if state else None,
        active_breakout_id=active_breakout_id,
        retest_in_progress=True,
        active_reaction_src_id=matched.db_id if matched else None,
        updated_at=datetime.utcnow(),
        continuation_mode=state.continuation_mode if state else False,
        last_alert_h4_ts=state.last_alert_h4_ts if state else None,
        last_h4_breaker_level=state.last_h4_breaker_level if state else None,
        retest_started_h4_ts=datetime.utcnow(),
    ))
    logger.info("%s RETEST started (source=%s)", instrument, payload.source)


def _handle_retest_cancelled(conn, instrument: str) -> None:
    state = get_instrument_state(conn, instrument)
    if state is None:
        return

    upsert_instrument_state(conn, InstrumentStateRow(
        instrument=instrument,
        last_daily_candle_ts=state.last_daily_candle_ts,
        last_h4_candle_ts=state.last_h4_candle_ts,
        active_breakout_id=state.active_breakout_id,
        retest_in_progress=False,
        active_reaction_src_id=None,
        updated_at=datetime.utcnow(),
        continuation_mode=state.continuation_mode,
        last_alert_h4_ts=state.last_alert_h4_ts,
        last_h4_breaker_level=state.last_h4_breaker_level,
        retest_started_h4_ts=None,
    ))
    logger.info("%s RETEST cancelled — price left the band", instrument)


async def _handle_confirmed(conn, config, instrument: str, payload: TVWebhookPayload) -> None:
    direction = Direction(payload.direction)

    # The breakout this confirmation belongs to — created or resynced from the
    # payload if the server missed the BREAKOUT webhook.
    breakout = _ensure_breakout(conn, config, instrument, direction,
                                payload.breakout_level or payload.h4_level, "CONFIRMED")

    # Ensure the matching reaction source exists in DB
    src_type = _source_type_from_str(payload.source, payload.source_kind)
    sources = get_active_reaction_sources(conn, instrument)
    pip_size = pip_size_for(instrument)
    tol_val = config.level_tolerance_pips * pip_size
    # Same kind of source AND (when the chart says which level) the same level
    source = next((s for s in sources if s.source_type == src_type and (
        payload.source_level is None or abs(s.level - payload.source_level) <= tol_val)), None)
    if source is None:
        src_lvl = payload.source_level or payload.breakout_level or breakout.broken_level
        source = ReactionSource(
            instrument=instrument,
            source_type=src_type,
            direction=direction,
            level=src_lvl,
            level_band_low=src_lvl - tol_val,
            level_band_high=src_lvl + tol_val,
            daily_breakout_ts=breakout.breakout_ts,
        )
        src_ids = insert_reaction_sources(conn, [source], breakout.db_id)
        source.db_id = src_ids[0]
    if payload.source_level2 is not None and src_type in (ReactionSourceType.FVG_AFTER_BREAKOUT, ReactionSourceType.FVG_INSIDE_RANGE):
        # A Daily FVG: the alert shows the whole gap, not one edge
        source.level_band_low = min(source.level, payload.source_level2)
        source.level_band_high = max(source.level, payload.source_level2)

    now = datetime.utcnow()

    # Build a synthetic H4 Formation from the webhook payload
    # Bullish confirmation → A-shape (bullish candle + bearish candle = resistance)
    # Bearish confirmation → V-shape (bearish candle + bullish candle = support)
    h4_form_type = FormationType.A_SHAPE if direction == Direction.BULLISH else FormationType.V_SHAPE
    h4_form_dir  = Direction.BEARISH    if direction == Direction.BULLISH else Direction.BULLISH
    h4_level     = payload.h4_level or (payload.breakout_level or breakout.broken_level)

    h4_formation = Formation(
        instrument=instrument,
        timeframe=Timeframe.H4,
        formation_type=h4_form_type,
        direction=h4_form_dir,
        level=h4_level,
        established_at=now,
        candle_1_ts=now,
        candle_2_ts=now,
    )
    h4_formation_id = insert_formation(conn, h4_formation)
    h4_formation.db_id = h4_formation_id

    # Build the H4 breakout event
    h4_cls = (
        BreakoutClassification.EXTERNAL
        if payload.h4_class == "external"
        else BreakoutClassification.INTERNAL
    )
    h4_event = H4BreakoutEvent(
        instrument=instrument,
        direction=direction,
        classification=h4_cls,
        formation_broken=h4_formation,
        confirmation_ts=now,
    )

    # Assemble the full AlertRecord
    alert_record = AlertRecord(
        instrument=instrument,
        direction=direction,
        daily_breakout=breakout,
        reaction_source=source,
        h4_event=h4_event,
        fired_at=now,
        classification=AlertClassification.ORIGIN,
        daily_level_context=payload.level_type or "external",
        weekly=_weekly_ctx(payload),
    )

    # Origin alerts say whose chart and prices they were read from (testers, 2026-10-25)
    alert_text = with_data_source(format_alert(alert_record), payload.exchange)
    alert_id = insert_alert(conn, alert_record, breakout.db_id, source.db_id, h4_formation_id, alert_text)
    _save_chart_levels(conn, instrument, alert_id, direction, breakout.broken_level,
                       source=(source.level, _SOURCE_NAMES.get(source.source_type, "Daily level")),
                       h4=(h4_level, "H4 A broken" if direction == Direction.BULLISH else "H4 V broken"),
                       subtitle=f"Origin · {(payload.h4_class or 'internal').capitalize()} H4 breakout")

    # Update state: clear retest, keep breakout active, enter continuation mode
    state = get_instrument_state(conn, instrument)
    upsert_instrument_state(conn, InstrumentStateRow(
        instrument=instrument,
        last_daily_candle_ts=state.last_daily_candle_ts if state else None,
        last_h4_candle_ts=state.last_h4_candle_ts if state else None,
        active_breakout_id=breakout.db_id,
        retest_in_progress=False,
        active_reaction_src_id=None,
        updated_at=now,
        continuation_mode=True,
        last_alert_h4_ts=now,
        last_h4_breaker_level=h4_level,
        retest_started_h4_ts=None,
    ))

    logger.info("%s CONFIRMED %s (h4_class=%s) — alert stored", instrument, direction.value, payload.h4_class)
    _set_setup_class(conn, instrument, confirmation_kind(payload.h4_class))

    if config.telegram_enabled:
        _in_background(_deliver_alert(conn, config, instrument, alert_text,
                             h4_class=confirmation_kind(payload.h4_class), alert_id=alert_id, pref="origin"))


_CONT_TYPE_TO_CLASSIFICATION: dict[str, AlertClassification] = {
    "breakout_cont":  AlertClassification.H4_BREAKOUT_CONT,
    "daily_react":    AlertClassification.H4_BREAKOUT_CONT,
    "inline_break":   AlertClassification.H4_BREAKOUT_CONT,   # new H4 breakout while in line
    "breaker_origin": AlertClassification.H4_BREAKER_ORIGIN,
    "breaker_cont":   AlertClassification.H4_BREAKER_CONT,
    "oc_cont":        AlertClassification.H4_OC_CONT,
    "engulfing":      AlertClassification.H4_ENGULFING_CONT,
    "h4_fvg":         AlertClassification.H4_FVG,
}
# Which subscriber switch each continuation type answers to (Alert Filters)
_CONT_PREF = {"inline_break": "cont_inline", "breakout_cont": "cont_realign", "daily_react": "cont_realign", "breaker_origin": "cont_breaker",
              "breaker_cont": "cont_breaker", "oc_cont": "cont_oc", "engulfing": "engulfing",
              "h4_fvg": "h4_fvg"}


def _weekly_ctx(payload: "TVWebhookPayload") -> Optional[dict]:
    if not payload.wk_rel:
        return None
    return {"wk_rel": payload.wk_rel, "wk_dir": payload.wk_dir, "wk_level": payload.wk_level,
            "wk_src": payload.wk_src, "wk_src_level": payload.wk_src_level, "wk_cls": payload.wk_cls}


async def _handle_h4_continuation(conn, config, instrument: str, payload: TVWebhookPayload) -> None:
    direction = Direction(payload.direction)
    cont_type = payload.cont_type or "breakout_cont"
    classification = _CONT_TYPE_TO_CLASSIFICATION.get(cont_type, AlertClassification.H4_BREAKOUT_CONT)

    breakout = _ensure_breakout(conn, config, instrument, direction,
                                payload.breakout_level or payload.h4_level, "H4_CONTINUATION")

    now = datetime.utcnow()
    h4_level = payload.h4_level or (payload.breakout_level or breakout.broken_level)

    # A realignment (H4 back in line after an H4 break against the daily bias)
    # names the daily level price reacted from; shown in the alert only.
    shown_source = None
    if payload.source and payload.source_level is not None:
        shown_source = ReactionSource(
            instrument=instrument,
            source_type=_source_type_from_str(payload.source, payload.source_kind),
            direction=direction,
            level=payload.source_level,
            level_band_low=min(payload.source_level, payload.source_level2 if payload.source_level2 is not None else payload.source_level),
            level_band_high=max(payload.source_level, payload.source_level2 if payload.source_level2 is not None else payload.source_level),
            daily_breakout_ts=breakout.breakout_ts,
        )

    alert_record = AlertRecord(
        instrument=instrument,
        direction=direction,
        daily_breakout=breakout,
        reaction_source=shown_source,
        h4_event=None,
        fired_at=now,
        classification=classification,
        h4_oc_level=h4_level if classification == AlertClassification.H4_OC_CONT else None,
        h4_breaker_level=h4_level if classification != AlertClassification.H4_OC_CONT else None,
        daily_level_context=payload.level_type or "external",
        weekly=_weekly_ctx(payload),
        h4_class=payload.h4_class if cont_type in ("breakout_cont", "daily_react") else None,
        daily_react=cont_type == "daily_react",
        eng_wick=(payload.eng_wick is not False) if cont_type == "engulfing" else None,
    )

    alert_text = format_alert(alert_record)
    alert_id = insert_alert(conn, alert_record, breakout.db_id, None, None, alert_text)
    _save_chart_levels(conn, instrument, alert_id, direction, breakout.broken_level,
                       source=(shown_source.level, _SOURCE_NAMES.get(shown_source.source_type, "Daily level")) if shown_source else None,
                       h4=(h4_level, _CONT_LEVEL_NAMES.get(cont_type, "H4 level")),
                       subtitle=_CONT_TITLES.get(cont_type, "H4 continuation"))

    state = get_instrument_state(conn, instrument)
    if cont_type != "h4_fvg":   # the FVG marker doesn't change the H4 Breaker or the setup's stage
        upsert_instrument_state(conn, InstrumentStateRow(
            instrument=instrument,
            last_daily_candle_ts=state.last_daily_candle_ts if state else None,
            last_h4_candle_ts=state.last_h4_candle_ts if state else None,
            active_breakout_id=breakout.db_id,
            retest_in_progress=False,
            active_reaction_src_id=None,
            updated_at=now,
            continuation_mode=True,
            last_alert_h4_ts=now,
            last_h4_breaker_level=h4_level,
            retest_started_h4_ts=None,
        ))

    logger.info("%s H4_CONTINUATION %s (cont_type=%s) — alert stored", instrument, direction.value, cont_type)

    # "Back in line" is an H4 breakout after a Daily reaction, like the Origin:
    # it follows each person's External / Internal choice and becomes the
    # setup's class. Every other continuation follows the setup's latest
    # confirmation, so it only reaches people who received that confirmation.
    if cont_type in ("breakout_cont", "daily_react") and payload.h4_class:
        setup_kind = confirmation_kind(payload.h4_class)
        _set_setup_class(conn, instrument, setup_kind)
    else:
        setup_kind = _setup_class(conn, instrument, breakout.db_id)   # None (unknown) = no External/Internal filter

    if config.telegram_enabled:
        _in_background(_deliver_alert(conn, config, instrument, alert_text, alert_id=alert_id,
                                      h4_class=setup_kind, pref=_CONT_PREF.get(cont_type),
                                      engulf_wick=alert_record.eng_wick))


async def _handle_price_update(conn, config, instrument: str, payload: TVWebhookPayload) -> None:
    price = payload.price
    if price is None:
        return

    # Record the H4 close for the public track record (same time format as alerts.fired_at)
    try:
        conn.execute("INSERT INTO price_ticks (instrument, ts, price) VALUES (?, ?, ?)",
                     (instrument, datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"), price))
        conn.commit()
    except Exception as exc:
        logger.warning("price tick write failed for %s: %s", instrument, exc)

    if payload.snapshot is not None:
        try:
            conn.execute(
                "INSERT INTO chart_snapshots (instrument, snapshot, price, updated_at) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(instrument) DO UPDATE SET snapshot = excluded.snapshot, price = excluded.price, "
                "updated_at = excluded.updated_at",
                (instrument, _json.dumps(payload.snapshot), price, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
        except Exception as exc:
            logger.warning("chart snapshot write failed for %s: %s", instrument, exc)

    now = datetime.utcnow().isoformat()

    # Fetch previous price for crossing detection
    row = conn.execute(
        "SELECT price FROM instrument_prices WHERE instrument = ?", (instrument,)
    ).fetchone()
    prev_price = row[0] if row else None

    # Upsert current price (prev_price ← old price, price ← new price)
    conn.execute("""
        INSERT INTO instrument_prices (instrument, price, prev_price, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(instrument) DO UPDATE SET
            prev_price = instrument_prices.price,
            price = excluded.price,
            updated_at = excluded.updated_at
    """, (instrument, price, prev_price, now))
    conn.commit()

    if prev_price is None:
        logger.info("%s PRICE_UPDATE %.5f (first update, skipping crossing check)", instrument, price)
        return

    # Check all active price alerts for this instrument
    alerts = conn.execute("""
        SELECT pa.id, pa.condition, pa.price AS alert_price, pa.message, u.telegram_chat_id,
               pa.user_id, u.role, u.plan, u.plan_expires_at
        FROM price_alerts pa
        LEFT JOIN users u ON pa.user_id = u.id
        WHERE pa.instrument = ? AND pa.is_active = 1
          AND (pa.expires_at IS NULL OR pa.expires_at > ?)
    """, (instrument, now)).fetchall()

    for alert_row in alerts:
        alert_id    = alert_row[0]
        condition   = alert_row[1]
        alert_price = alert_row[2]
        message     = alert_row[3]
        # None when the alert's owner is unlinked/expired/revoked: still marked
        # triggered below, but never rerouted to anyone else's chat.
        chat_id     = _resolve_chat(config, alert_row[5], alert_row[4],
                                    alert_row[6], alert_row[7], alert_row[8])

        triggered = False
        direction_str = ""
        if condition == "crossing_up":
            if prev_price < alert_price <= price:
                triggered, direction_str = True, "above"
        elif condition == "crossing_down":
            if prev_price > alert_price >= price:
                triggered, direction_str = True, "below"
        else:  # crossing
            if prev_price < alert_price <= price:
                triggered, direction_str = True, "above"
            elif prev_price > alert_price >= price:
                triggered, direction_str = True, "below"

        if not triggered:
            continue

        conn.execute(
            "UPDATE price_alerts SET is_active = 0, triggered_at = ? WHERE id = ?",
            (now, alert_id),
        )
        conn.commit()

        # Determine decimal precision for display
        if is_synthetic(instrument):
            a_ = abs(price)
            fmt = "{:.2f}" if a_ >= 1000 else "{:.3f}" if a_ >= 10 else "{:.5f}"
        elif instrument.endswith("JPY") or instrument == "XAGUSD":
            fmt = "{:.3f}"
        elif instrument in ("XAUUSD", "USOIL", "WTIUSD"):
            fmt = "{:.2f}"
        else:
            fmt = "{:.5f}"

        text = f"⚡ Price Alert: {tagged(instrument)}\n\n"
        text += f"Price crossed {direction_str} {fmt.format(alert_price)}\n"
        text += f"Current: {fmt.format(price)}"
        if message:
            text += f"\n\n{message}"

        logger.info("%s price alert triggered — %s @ %s (id=%d)", instrument, condition, alert_price, alert_id)

        if config.telegram_enabled and chat_id:
            _in_background(send_alert(config.telegram_bot_token, chat_id, text))


async def _handle_entry_confirmation(conn, config, instrument: str, payload: TVWebhookPayload) -> None:
    """
    H1/H2 entry-pattern confirmation (PCL or Engulfing Sweep).

    Matches the incoming pattern against each user's active entry_pattern_alerts
    for this instrument. An alert fires (and auto-closes) when ALL of these hold:
      - direction matches
      - pattern price is within <alert.tolerance_pips> of the user's set price
      - alert is active and not expired

    If no user is watching this instrument/direction/price band — silently ignored.
    No bias-state gating: users deliberately choose when and where to watch.
    """
    direction = payload.direction
    pattern = payload.pattern
    tf = payload.timeframe or "60"
    price = payload.price
    swept_level = payload.swept_level

    if direction not in ("bullish", "bearish") or pattern not in ("pcl", "engulfing_sweep"):
        logger.warning("%s ENTRY_CONFIRMATION ignored — bad direction/pattern (%s/%s)",
                       instrument, direction, pattern)
        return
    if price is None or swept_level is None:
        logger.warning("%s ENTRY_CONFIRMATION ignored — missing price/swept_level", instrument)
        return

    now_iso = datetime.utcnow().isoformat()
    pip_size = pip_size_for(instrument)

    # Find every active, matching, non-expired entry alert for this instrument + direction
    rows = conn.execute("""
        SELECT epa.id, epa.price, epa.tolerance_pips, epa.note,
               u.telegram_chat_id, epa.user_id, u.role, u.plan, u.plan_expires_at
        FROM entry_pattern_alerts epa
        LEFT JOIN users u ON u.id = epa.user_id
        WHERE epa.instrument = ?
          AND epa.direction = ?
          AND epa.is_active = 1
          AND (epa.expires_at IS NULL OR epa.expires_at > ?)
    """, (instrument, direction, now_iso)).fetchall()

    if not rows:
        logger.info("%s ENTRY_CONFIRMATION %s %s @ %.5f — no watchers",
                    instrument, direction, pattern, price)
        return

    tf_label = "H1" if tf == "60" else ("H2" if tf == "120" else tf)

    for row in rows:
        alert_id = row["id"]
        alert_price = row["price"]
        tol_pips = row["tolerance_pips"]
        note = row["note"]
        # None when the alert's owner is unlinked/expired/revoked: never rerouted.
        chat_id = _resolve_chat(config, row["user_id"], row["telegram_chat_id"],
                                row["role"], row["plan"], row["plan_expires_at"])

        proximity = tol_pips * pip_size
        if abs(price - alert_price) > proximity:
            continue  # pattern formed too far from this user's watched level

        # Mark the alert as triggered (one-shot — auto-closes)
        conn.execute("""
            UPDATE entry_pattern_alerts
            SET is_active = 0, triggered_at = ?,
                triggered_pattern = ?, triggered_tf = ?
            WHERE id = ?
        """, (now_iso, pattern, tf_label, alert_id))
        conn.commit()

        alert_text = format_entry_alert(
            instrument=instrument,
            direction=direction,
            pattern=pattern,
            timeframe=tf,
            price=price,
            swept_level=swept_level,
        )
        if note:
            alert_text += f"\n\nYour note: {note}"

        logger.info("%s ENTRY_CONFIRMATION %s %s @ %.5f matched alert_id=%d (watched @ %.5f, tol %.1f pips)",
                    instrument, direction, pattern, price, alert_id, alert_price, tol_pips)

        if config.telegram_enabled and chat_id:
            _in_background(send_alert(config.telegram_bot_token, chat_id, alert_text))


def _handle_invalidated(conn, instrument: str) -> None:
    state = get_instrument_state(conn, instrument)

    if state and state.active_breakout_id:
        deactivate_reaction_sources_for_breakout(conn, state.active_breakout_id)
        from state.repository import deactivate_breakout
        deactivate_breakout(conn, state.active_breakout_id)

    upsert_instrument_state(conn, InstrumentStateRow(
        instrument=instrument,
        last_daily_candle_ts=state.last_daily_candle_ts if state else None,
        last_h4_candle_ts=state.last_h4_candle_ts if state else None,
        active_breakout_id=None,
        retest_in_progress=False,
        active_reaction_src_id=None,
        updated_at=datetime.utcnow(),
        continuation_mode=False,
        last_alert_h4_ts=state.last_alert_h4_ts if state else None,
        last_h4_breaker_level=None,
        retest_started_h4_ts=None,
    ))
    logger.info("%s INVALIDATED — reset to IDLE", instrument)

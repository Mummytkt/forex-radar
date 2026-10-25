"""
Alert message formatter.

Builds the exact human-readable bias-confirmation alert from an AlertRecord.
Handles four alert classifications:
  ORIGIN                  — first H4 confirmation from a Daily reaction source
  CONTINUATION_ASHAPE     — H4 back in line with the Daily after a Daily reaction
                            (older scripts: any later H4 A/V break)
  CONTINUATION_H4_OC      — H4 OC rejection (exact touch, close beyond the OC level)
  CONTINUATION_H4_BREAKER — H4 Breaker retested: opens on the bias side, exact touch, closes beyond
"""

from __future__ import annotations

from datetime import datetime, timezone

from config import tagged

from data.models import (
    AlertClassification,
    AlertRecord,
    BreakoutClassification,
    Direction,
    FormationType,
    ReactionSourceType,
)


_SOURCE_NAMES: dict[ReactionSourceType, str] = {
    ReactionSourceType.DAILY_BREAKER:          "Daily Breaker",
    ReactionSourceType.OC_INSIDE_RANGE:        "Daily OC inside the range",
    ReactionSourceType.AV_INSIDE_RANGE:        "Daily V/A-shape inside the range",
    ReactionSourceType.POST_BREAKOUT_DAILY_OC: "Post-Breakout OC",
    ReactionSourceType.AV_AFTER_BREAKOUT:      "Daily V/A-shape after the breakout",
    ReactionSourceType.FVG_AFTER_BREAKOUT:     "Daily FVG after the breakout",
    ReactionSourceType.FVG_INSIDE_RANGE:       "Daily FVG inside the range",
}

_BROKEN_TYPE_NAMES: dict[FormationType, str] = {
    FormationType.A_SHAPE: "A-shape",
    FormationType.V_SHAPE: "V-shape",
    FormationType.OC:      "OC",
}


# ── Context label ────────────────────────────────────────────────────────────

_LEVEL_TYPE_NAMES = {"external": "External", "internal": "Internal", "inner_internal": "Inner internal",
                     "sub_internal": "Sub-internal"}


def _context_line(alert: AlertRecord) -> str:
    """Which daily structure level the breakout broke (external / internal / inner internal)."""
    ctx = getattr(alert, "daily_level_context", "internal")
    return f"Daily breakout level: {_LEVEL_TYPE_NAMES.get(ctx, 'Internal')}"


# ── Price / timestamp helpers ─────────────────────────────────────────────────

def _fmt_level(instrument: str, level: float) -> str:
    from config import fmt_price
    return fmt_price(instrument, level)


_FVG_SOURCES = (ReactionSourceType.FVG_AFTER_BREAKOUT, ReactionSourceType.FVG_INSIDE_RANGE)


def _src_level(instrument: str, src) -> str:
    """The reacting level as text. A Daily FVG is a zone, so it shows the whole gap."""
    if src.source_type in _FVG_SOURCES and src.level_band_low is not None and src.level_band_high is not None \
            and src.level_band_high - src.level_band_low > 1e-9:
        return f"{_fmt_level(instrument, src.level_band_low)} – {_fmt_level(instrument, src.level_band_high)}"
    return _fmt_level(instrument, src.level)


def _fmt_ts(dt: datetime | None) -> str:
    if dt is None:
        return "—"
    return dt.strftime("%a %d %b '%y, %H:%M UTC")


# ── Dispatcher ────────────────────────────────────────────────────────────────

def format_alert(alert: AlertRecord) -> str:
    if alert.classification == AlertClassification.H4_FVG:
        # Liquidity marker: just the pair and the message, no buy / sell
        return f"{alert.instrument}\nH4 FVG candle after breakout has formed"
    return _with_weekly(alert, _format_body(alert))


# Lines kept in the Short message style: the headline of each part, no explanations
_SHORT_KEEP = ("Daily breakout:", "Weekly", "Daily reaction source:", "H4 confirmation:", "Reason:",
               "Daily breakout level:", "⚠️", "📊")


def _h4_break_line(alert: AlertRecord, level_str: str) -> str:
    cls = (alert.h4_class or "").lower()
    return f"H4 {'External' if cls == 'external' else 'Internal'} breakout @ {level_str}" if cls in ("external", "internal") else f"H4 breakout @ {level_str}"


def _headline(direction: Direction, instrument: str, continuation: bool) -> str:
    """First line of a bias alert (testers' wording, 2026-10-25).
    Origin:        'BUY BTCUSD (Crypto)'
    Continuation:  'BUY CONTINUATION — BUY AUDCAD (Forex)'"""
    side = "BUY" if direction == Direction.BULLISH else "SELL"
    if continuation:
        return f"{side} CONTINUATION — {side} {tagged(instrument)}"
    return f"{side} {tagged(instrument)}"


# Where the chart and prices come from (TradingView exchange prefix → name)
_FEEDS = {"FOREXCOM": "FOREX.com", "FX": "FXCM", "FX_IDC": "FXCM", "OANDA": "OANDA", "COINBASE": "Coinbase",
          "BINANCE": "Binance", "BITSTAMP": "Bitstamp", "KRAKEN": "Kraken", "BYBIT": "Bybit", "DERIV": "Deriv",
          "CAPITALCOM": "Capital.com", "PEPPERSTONE": "Pepperstone", "ICMARKETS": "IC Markets", "TVC": "TradingView (TVC)",
          "CRYPTO": "TradingView crypto index", "FXOPEN": "FXOpen", "EIGHTCAP": "Eightcap", "BLACKBULL": "BlackBull"}


def with_data_source(text: str, exchange: str | None) -> str:
    """Put the data-source line at the end of an Origin alert, above the signature."""
    lines = text.split("\n")
    at = max((i for i, ln in enumerate(lines) if ln.startswith("— ")), default=len(lines))
    return "\n".join(lines[:at] + [data_source_line(exchange), ""] + lines[at:])


def data_source_line(exchange: str | None) -> str:
    """Under each Origin alert: whose chart and prices the alert was read from."""
    feed = _FEEDS.get((exchange or "").upper(), (exchange or "").strip() or "the TradingView chart")
    return (f"📊 All charts and prices are from {feed} on TradingView. Your broker's prices can differ slightly, "
            "so check the levels on your own chart.")


def _signature() -> str:
    """Footer on every alert: '— MummyTKT © <current year>'."""
    return f"— MummyTKT © {datetime.now(timezone.utc).year}"


def short_text(full: str) -> str:
    """The Short style: title, alert type, then only the headline lines, so the
    message goes straight to the point. Weekly lines stay with 'Daily breakout'."""
    lines = full.split("\n")
    if len(lines) < 3:
        return full
    out = lines[:2]
    for ln in lines[2:]:
        if ln.startswith(_SHORT_KEEP):
            if ln.startswith("Weekly") and out and (out[-1].startswith("Daily breakout:") or out[-1].startswith("Weekly")):
                out.append(ln)
            else:
                out += ["", ln]
    tail = [ln for ln in lines if ln.startswith("— ")]
    if tail:
        out += ["", tail[-1]]
    return "\n".join(out)


def _weekly_lines(alert: AlertRecord) -> list[str]:
    """The Weekly storyline above this Daily setup, if there is one."""
    w = alert.weekly or {}
    rel = (w.get("wk_rel") or "").lower()
    if rel not in ("confirmed", "inline", "against"):
        return []
    wdir = "Bullish" if (w.get("wk_dir") or "").lower() == "bullish" else "Bearish"
    lvl = w.get("wk_level")
    lvl_s = _fmt_level(alert.instrument, lvl) if lvl is not None else "—"
    if rel == "confirmed":
        src_lvl = w.get("wk_src_level")
        src_s = _fmt_level(alert.instrument, src_lvl) if src_lvl is not None else "—"
        cls = "External" if (w.get("wk_cls") or "").lower() == "external" else "Internal"
        return [f"Weekly: {wdir} breakout @ {lvl_s} → reaction at {w.get('wk_src') or 'a Weekly level'} @ {src_s}",
                f"Weekly-confirmed: the Daily breakout is an {cls} breakout in the Weekly direction."]
    if rel == "inline":
        return [f"Weekly: {wdir} breakout @ {lvl_s} · the Daily is in line with the Weekly (no Weekly reaction yet)."]
    return [f"Weekly: {wdir} breakout @ {lvl_s} · ⚠️ this Daily setup is AGAINST the Weekly direction."]


def _with_weekly(alert: AlertRecord, text: str) -> str:
    """Insert the Weekly lines right after the 'Daily breakout:' line."""
    extra = _weekly_lines(alert)
    if not extra:
        return text
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        if ln.startswith("Daily breakout:"):
            return "\n".join(lines[:i + 1] + extra + lines[i + 1:])
    return "\n".join(lines[:2] + [""] + extra + lines[2:])


def _format_body(alert: AlertRecord) -> str:
    if alert.classification == AlertClassification.H4_ENGULFING_CONT:
        return _format_h4_engulfing(alert)
    if alert.classification == AlertClassification.CONTINUATION_H4_OC:
        return _format_continuation_h4_oc(alert)
    if alert.classification == AlertClassification.CONTINUATION_ASHAPE:
        return _format_continuation_ashape(alert)
    if alert.classification == AlertClassification.CONTINUATION_H4_BREAKER:
        return _format_continuation_h4_breaker(alert)
    if alert.classification == AlertClassification.H4_BREAKER_ORIGIN:
        return _format_h4_breaker_origin(alert)
    if alert.classification == AlertClassification.H4_BREAKOUT_CONT:
        return _format_h4_breakout_cont(alert)
    if alert.classification == AlertClassification.H4_BREAKER_CONT:
        return _format_h4_breaker_cont(alert)
    if alert.classification == AlertClassification.H4_OC_CONT:
        return _format_h4_oc_cont(alert)
    return _format_origin(alert)


# ── Origin alert ──────────────────────────────────────────────────────────────

def _format_origin(alert: AlertRecord) -> str:
    direction = alert.direction
    instrument = alert.instrument
    breakout = alert.daily_breakout
    source = alert.reaction_source
    h4 = alert.h4_event

    bias_label = _headline(direction, instrument, continuation=False)
    direction_label = "Bullish" if direction == Direction.BULLISH else "Bearish"
    direction_lower = direction_label.lower()

    breakout_level_str = _fmt_level(instrument, breakout.broken_level)

    if direction == Direction.BEARISH:
        breakout_desc = (
            f"A Daily candle closed below the most recent External low "
            f"@ {breakout_level_str}. This is the most recent confirmed Daily breakout."
        )
    else:
        breakout_desc = (
            f"A Daily candle closed above the most recent External high "
            f"@ {breakout_level_str}. This is the most recent confirmed Daily breakout."
        )

    source_name = _SOURCE_NAMES[source.source_type]
    if source.source_type == ReactionSourceType.AV_INSIDE_RANGE:
        source_name = f"Daily {'V' if direction == Direction.BULLISH else 'A'}-shape inside the range"
    source_level_str = _src_level(instrument, source)

    source_desc = _source_description(source.source_type, direction_lower, source_name)
    source_header = f"Daily reaction source: {source_name} @ {source_level_str}"

    classification_label = (
        "External" if h4.classification == BreakoutClassification.EXTERNAL else "Internal"
    )
    h4_formation_name = _BROKEN_TYPE_NAMES.get(
        h4.formation_broken.formation_type, h4.formation_broken.formation_type.value
    )
    h4_level_str = _fmt_level(instrument, h4.formation_broken.level)
    h4_ts_str = _fmt_ts(h4.confirmation_ts)

    if direction == Direction.BEARISH:
        h4_desc = (
            f"An H4 {h4_formation_name} formation was broken, and an H4 candle "
            f"closed below its body level @ {h4_level_str}. "
            f"The H4 breakout aligns with the most recent Daily breakout."
        )
    else:
        h4_desc = (
            f"An H4 {h4_formation_name} formation was broken, and an H4 candle "
            f"closed above its body level @ {h4_level_str}. "
            f"The H4 breakout aligns with the most recent Daily breakout."
        )

    reason = _reason_origin(source.source_type, direction_label, classification_label, direction_lower)

    lines = [
        bias_label,
        "Daily → H4 aligned",
        "",
        f"Daily breakout: {direction_label} — broken level @ {breakout_level_str}",
        breakout_desc,
        "",
        source_header,
        source_desc,
        "",
        f"H4 confirmation: {classification_label} {direction_lower} breakout",
        f"Formation: H4 {h4_formation_name} @ {h4_level_str} · {h4_ts_str}",
        h4_desc,
        "",
        f"Reason: {reason}",
        "",
        _context_line(alert),
        "",
        "⚠️ Directional bias only — not an entry signal. Wait for the entry model.",
        "",
        _signature(),
    ]
    return "\n".join(lines)


# ── Continuation A-shape alert ────────────────────────────────────────────────

def _format_continuation_ashape(alert: AlertRecord) -> str:
    direction = alert.direction
    instrument = alert.instrument
    h4 = alert.h4_event

    bias_label = _headline(direction, instrument, continuation=True)
    direction_label = "Bullish" if direction == Direction.BULLISH else "Bearish"
    direction_lower = direction_label.lower()

    classification_label = (
        "External" if h4.classification == BreakoutClassification.EXTERNAL else "Internal"
    )
    h4_formation_name = _BROKEN_TYPE_NAMES.get(
        h4.formation_broken.formation_type, h4.formation_broken.formation_type.value
    )
    h4_level_str = _fmt_level(instrument, h4.formation_broken.level)
    h4_ts_str = _fmt_ts(h4.confirmation_ts)

    if direction == Direction.BEARISH:
        h4_desc = (
            f"An H4 {h4_formation_name} formation was broken, and an H4 candle "
            f"closed below its body level @ {h4_level_str}, continuing the established {direction_lower} bias."
        )
    else:
        h4_desc = (
            f"An H4 {h4_formation_name} formation was broken, and an H4 candle "
            f"closed above its body level @ {h4_level_str}, continuing the established {direction_lower} bias."
        )

    lines = [
        bias_label,
        f"Daily → H4 continuation",
        "",
        f"Daily breakout: {direction_label} (active)",
        "",
        f"H4 continuation: {classification_label} {direction_lower} breakout",
        f"Formation: H4 {h4_formation_name} @ {h4_level_str} · {h4_ts_str}",
        h4_desc,
        "",
        f"Reason: A qualifying {classification_label.lower()} {direction_lower} H4 breakout "
        f"has occurred in line with the active Daily {direction_lower} breakout. "
        f"This is a continuation of the established bias.",
        "",
        _context_line(alert),
        "",
        "⚠️ Directional bias only — not an entry signal. Wait for the entry model.",
        "",
        _signature(),
    ]
    return "\n".join(lines)


# ── Continuation H4 Breaker alert ─────────────────────────────────────────────

def _format_continuation_h4_breaker(alert: AlertRecord) -> str:
    direction = alert.direction
    instrument = alert.instrument
    level = alert.h4_breaker_level

    bias_label = _headline(direction, instrument, continuation=True)
    direction_label = "Bullish" if direction == Direction.BULLISH else "Bearish"
    direction_lower = direction_label.lower()

    level_str = _fmt_level(instrument, level) if level is not None else "—"

    if direction == Direction.BEARISH:
        desc = (
            f"Price retraced into the H4 key level at {level_str} — "
            f"either the H4 Breaker from the prior confirmation or an H4 A-shape "
            f"resistance zone inside the daily range. "
            f"The H4 candle wicked into the level and closed below it, "
            f"confirming rejection and continuation of the bearish bias."
        )
        reason = (
            f"An H4 candle wicked into the {level_str} key level from below and "
            f"closed below it, confirming that the level is holding as resistance "
            f"and the bearish bias remains intact."
        )
    else:
        desc = (
            f"Price retraced into the H4 key level at {level_str} — "
            f"either the H4 Breaker from the prior confirmation or an H4 V-shape "
            f"support zone inside the daily range. "
            f"The H4 candle wicked into the level and closed above it, "
            f"confirming rejection and continuation of the bullish bias."
        )
        reason = (
            f"An H4 candle wicked into the {level_str} key level from above and "
            f"closed above it, confirming that the level is holding as support "
            f"and the bullish bias remains intact."
        )

    lines = [
        bias_label,
        f"Daily → H4 Breaker continuation",
        "",
        f"Daily breakout: {direction_label} (active)",
        "",
        f"H4 Breaker retest: {level_str}",
        desc,
        "",
        f"Reason: {reason}",
        "",
        _context_line(alert),
        "",
        "⚠️ Directional bias only — not an entry signal. Wait for the entry model.",
        "",
        _signature(),
    ]
    return "\n".join(lines)


# ── Continuation H4 OC alert ──────────────────────────────────────────────────

def _format_continuation_h4_oc(alert: AlertRecord) -> str:
    direction = alert.direction
    instrument = alert.instrument
    oc_level = alert.h4_oc_level

    bias_label = _headline(direction, instrument, continuation=True)
    direction_label = "Bullish" if direction == Direction.BULLISH else "Bearish"
    direction_lower = direction_label.lower()

    level_str = _fmt_level(instrument, oc_level) if oc_level is not None else "—"

    if direction == Direction.BULLISH:
        oc_desc = (
            f"A bullish H4 OC formed (two consecutive bullish H4 candles). "
            f"Price returned to react from the OC level at {level_str} "
            f"and closed above it, confirming a {direction_lower} continuation."
        )
    else:
        oc_desc = (
            f"A bearish H4 OC formed (two consecutive bearish H4 candles). "
            f"Price returned to react from the OC level at {level_str} "
            f"and closed below it, confirming a {direction_lower} continuation."
        )

    lines = [
        bias_label,
        f"Daily → H4 OC continuation",
        "",
        f"Daily breakout: {direction_label} (active)",
        "",
        f"H4 OC reaction: level @ {level_str}",
        oc_desc,
        "",
        f"Reason: Price rejected from an H4 {direction_lower} OC level at {level_str}, "
        f"confirming continuation of the active Daily {direction_lower} bias.",
        "",
        _context_line(alert),
        "",
        "⚠️ Directional bias only — not an entry signal. Wait for the entry model.",
        "",
        _signature(),
    ]
    return "\n".join(lines)


# ── H4 Breaker Origin alert ───────────────────────────────────────────────────

def _format_h4_breaker_origin(alert: AlertRecord) -> str:
    direction = alert.direction
    instrument = alert.instrument
    level = alert.h4_breaker_level

    bias_label = _headline(direction, instrument, continuation=True)
    direction_label = "Bullish" if direction == Direction.BULLISH else "Bearish"
    direction_lower = direction_label.lower()

    level_str = _fmt_level(instrument, level) if level is not None else "—"

    if direction == Direction.BULLISH:
        desc = (
            f"Price retraced to the H4 key level created at the Origin confirmation @ {level_str}. "
            f"An H4 candle wicked into the level and closed above it, "
            f"confirming the H4 Breaker for the first time."
        )
        reason = (
            f"The H4 Origin level at {level_str} has been retested and confirmed for the first time. "
            f"This establishes the H4 Breaker, extending the bullish bias."
        )
    else:
        desc = (
            f"Price retraced to the H4 key level created at the Origin confirmation @ {level_str}. "
            f"An H4 candle wicked into the level and closed below it, "
            f"confirming the H4 Breaker for the first time."
        )
        reason = (
            f"The H4 Origin level at {level_str} has been retested and confirmed for the first time. "
            f"This establishes the H4 Breaker, extending the bearish bias."
        )

    lines = [
        bias_label,
        "H4 Breaker Origin",
        "",
        f"Daily breakout: {direction_label} (active)",
        "",
        f"H4 Breaker Origin @ {level_str}",
        desc,
        "",
        f"Reason: {reason}",
        "",
        _context_line(alert),
        "",
        "⚠️ Directional bias only — not an entry signal. Wait for the entry model.",
        "",
        _signature(),
    ]
    return "\n".join(lines)


# ── H4 Breakout Continuation alert ───────────────────────────────────────────

def _format_h4_breakout_cont(alert: AlertRecord) -> str:
    direction = alert.direction
    instrument = alert.instrument
    level = alert.h4_breaker_level

    bias_label = _headline(direction, instrument, continuation=True)
    direction_label = "Bullish" if direction == Direction.BULLISH else "Bearish"
    direction_lower = direction_label.lower()

    level_str = _fmt_level(instrument, level) if level is not None else "—"

    if direction == Direction.BULLISH:
        desc = (
            f"An H4 formation was broken and an H4 candle closed above its body level @ {level_str}, "
            f"continuing the established bullish bias."
        )
    else:
        desc = (
            f"An H4 formation was broken and an H4 candle closed below its body level @ {level_str}, "
            f"continuing the established bearish bias."
        )

    src = alert.reaction_source
    if src is not None:
        # H4 back in line: it had broken against the daily bias, price then
        # reacted at a daily level and H4 broke back in the daily direction.
        src_name = _SOURCE_NAMES.get(src.source_type, "Daily level")
        if src.source_type == ReactionSourceType.AV_INSIDE_RANGE:
            src_name = f"Daily {'V' if direction == Direction.BULLISH else 'A'}-shape inside the range"
        if src.source_type == ReactionSourceType.AV_AFTER_BREAKOUT:
            src_name = f"Daily {'V' if direction == Direction.BULLISH else 'A'}-shape after the breakout"
        src_str = _src_level(instrument, src)
        if alert.daily_react:
            # H4 was still in line: a fresh Daily reaction and a new H4 breakout from it
            lines = [
                bias_label,
                "Daily reaction + H4 breakout",
                "",
                f"Daily breakout: {direction_label} (active)",
                "",
                f"Daily reaction source: {src_name} @ {src_str}",
                f"Price came back to this Daily level and held, in the Daily {direction_lower} direction.",
                "",
                _h4_break_line(alert, level_str),
                desc,
                "",
                f"Reason: A fresh reaction from the {src_name} and an H4 breakout from it.",
                "",
            ]
        else:
            lines = [
                bias_label,
                "H4 back in line with the Daily",
                "",
                f"Daily breakout: {direction_label} (active)",
                "",
                f"Daily reaction source: {src_name} @ {src_str}",
                f"H4 had broken against the Daily {direction_lower} bias. Price then reacted at this Daily level.",
                "",
                _h4_break_line(alert, level_str),
                desc,
                "",
                f"Reason: The reaction from the {src_name} brought H4 back in line with the Daily "
                f"{direction_lower} bias.",
                "",
            ]
    else:
        # A new H4 breakout while H4 is already in line with the Daily
        lines = [
            bias_label,
            "H4 breakout in line with the Daily",
            "",
            f"Daily breakout: {direction_label} (active)",
            "",
            _h4_break_line(alert, level_str),
            desc,
            "This level is now the H4 Breaker.",
            "",
            f"Reason: A new H4 breakout in the {direction_lower} direction, while H4 is in line with the Daily, "
            f"has extended the active Daily {direction_lower} bias.",
            "",
        ]
    lines += [
        _context_line(alert),
        "",
        "⚠️ Directional bias only — not an entry signal. Wait for the entry model.",
        "",
        _signature(),
    ]
    return "\n".join(lines)


# ── H4 Breaker Continuation alert ────────────────────────────────────────────

def _format_h4_breaker_cont(alert: AlertRecord) -> str:
    direction = alert.direction
    instrument = alert.instrument
    level = alert.h4_breaker_level

    bias_label = _headline(direction, instrument, continuation=True)
    direction_label = "Bullish" if direction == Direction.BULLISH else "Bearish"
    direction_lower = direction_label.lower()

    level_str = _fmt_level(instrument, level) if level is not None else "—"

    if direction == Direction.BULLISH:
        desc = (
            f"Price revisited the H4 Breaker zone at {level_str}. "
            f"An H4 candle wicked into the level and closed above it, "
            f"confirming continued support and bias continuation."
        )
        reason = (
            f"An H4 candle confirmed rejection from the H4 Breaker level at {level_str}, "
            f"keeping the bullish bias intact."
        )
    else:
        desc = (
            f"Price revisited the H4 Breaker zone at {level_str}. "
            f"An H4 candle wicked into the level and closed below it, "
            f"confirming continued resistance and bias continuation."
        )
        reason = (
            f"An H4 candle confirmed rejection from the H4 Breaker level at {level_str}, "
            f"keeping the bearish bias intact."
        )

    lines = [
        bias_label,
        "H4 Breaker Continuation",
        "",
        f"Daily breakout: {direction_label} (active)",
        "",
        f"H4 Breaker retest @ {level_str}",
        desc,
        "",
        f"Reason: {reason}",
        "",
        _context_line(alert),
        "",
        "⚠️ Directional bias only — not an entry signal. Wait for the entry model.",
        "",
        _signature(),
    ]
    return "\n".join(lines)


# ── H4 OC Continuation alert ──────────────────────────────────────────────────

def _format_h4_engulfing(alert: AlertRecord) -> str:
    direction = alert.direction
    instrument = alert.instrument
    level = alert.h4_breaker_level
    bias_label = _headline(direction, instrument, continuation=True)
    direction_label = "Bullish" if direction == Direction.BULLISH else "Bearish"
    direction_lower = direction_label.lower()
    level_str = _fmt_level(instrument, level) if level is not None else "—"
    wick = alert.eng_wick is not False
    if direction == Direction.BULLISH:
        desc = (f"A bullish H4 candle engulfed the previous bearish candle, wick included: it opened at or below "
                f"that candle's close and closed above its high @ {level_str}." if wick else
                f"A bullish H4 candle engulfed the previous bearish candle's body: it opened at or below that "
                f"candle's close and closed above its open @ {level_str} (inside its wick).")
    else:
        desc = (f"A bearish H4 candle engulfed the previous bullish candle, wick included: it opened at or above "
                f"that candle's close and closed below its low @ {level_str}." if wick else
                f"A bearish H4 candle engulfed the previous bullish candle's body: it opened at or above that "
                f"candle's close and closed below its open @ {level_str} (inside its wick).")
    lines = [
        bias_label,
        f"H4 Engulfing in the Daily direction",
        "",
        f"Daily breakout: {direction_label} (active)",
        "",
        f"H4 {direction_lower} engulfing ({'covers the wick' if wick else 'covers the body'}) @ {level_str}",
        desc,
        "",
        f"Reason: A {direction_lower} H4 engulfing candle formed while H4 is in line with the active Daily "
        f"{direction_lower} bias.",
        "",
        _context_line(alert),
        "",
        "⚠️ Directional bias only — not an entry signal. Wait for the entry model.",
        "",
        _signature(),
    ]
    return "\n".join(lines)


def _format_h4_oc_cont(alert: AlertRecord) -> str:
    direction = alert.direction
    instrument = alert.instrument
    oc_level = alert.h4_oc_level

    bias_label = _headline(direction, instrument, continuation=True)
    direction_label = "Bullish" if direction == Direction.BULLISH else "Bearish"
    direction_lower = direction_label.lower()

    level_str = _fmt_level(instrument, oc_level) if oc_level is not None else "—"

    if direction == Direction.BULLISH:
        oc_desc = (
            f"A bullish H4 OC formed (two consecutive bullish H4 candles). "
            f"Price returned to react from the OC level at {level_str} "
            f"and closed above it, confirming a bullish continuation."
        )
    else:
        oc_desc = (
            f"A bearish H4 OC formed (two consecutive bearish H4 candles). "
            f"Price returned to react from the OC level at {level_str} "
            f"and closed below it, confirming a bearish continuation."
        )

    lines = [
        bias_label,
        "H4 OC Continuation",
        "",
        f"Daily breakout: {direction_label} (active)",
        "",
        f"H4 OC reaction: level @ {level_str}",
        oc_desc,
        "",
        f"Reason: Price rejected from an H4 {direction_lower} OC level at {level_str}, "
        f"confirming continuation of the active Daily {direction_lower} bias.",
        "",
        _context_line(alert),
        "",
        "⚠️ Directional bias only — not an entry signal. Wait for the entry model.",
        "",
        _signature(),
    ]
    return "\n".join(lines)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _source_description(
    source_type: ReactionSourceType,
    direction_lower: str,
    source_name: str,
) -> str:
    if source_type == ReactionSourceType.DAILY_BREAKER:
        return (
            f"Price retraced to the Daily Breaker — the previously broken "
            f"A/V key level that has since flipped roles. "
            f"The reaction from this level led to the confirming H4 breakout."
        )
    if source_type == ReactionSourceType.OC_INSIDE_RANGE:
        return (
            f"After the Daily breakout, price re-entered the previous Daily range "
            f"and reacted from an OC level within that range. "
            f"The reaction produced the confirming H4 breakout."
        )
    if source_type == ReactionSourceType.AV_INSIDE_RANGE:
        return (
            f"After the Daily breakout, price came back into the range that was broken "
            f"and reacted from a {source_name} level. "
            f"The reaction led to the confirming H4 breakout."
        )
    if source_type == ReactionSourceType.POST_BREAKOUT_DAILY_OC:
        return (
            f"After the breakout, two consecutive {direction_lower} Daily candles formed "
            f"a Post-Breakout OC level. Price retraced into that OC zone and "
            f"the reaction led to the confirming H4 breakout."
        )
    return f"Price reacted from {source_name}, leading to the confirming H4 breakout."


def _reason_origin(
    source_type: ReactionSourceType,
    direction_label: str,
    classification_label: str,
    direction_lower: str,
) -> str:
    classification_lower = classification_label.lower()
    if source_type == ReactionSourceType.DAILY_BREAKER:
        return (
            f"The Daily Breaker reaction produced a qualifying "
            f"{classification_lower} {direction_lower} H4 breakout, "
            f"aligning the Daily and H4 directions."
        )
    if source_type == ReactionSourceType.OC_INSIDE_RANGE:
        return (
            f"The Daily OC inside the range reaction produced a qualifying "
            f"{classification_lower} {direction_lower} H4 breakout, "
            f"aligning the Daily and H4 directions."
        )
    if source_type == ReactionSourceType.AV_INSIDE_RANGE:
        return (
            f"The reaction from a Daily level inside the range produced a qualifying "
            f"{classification_lower} {direction_lower} H4 breakout, "
            f"aligning the Daily and H4 directions."
        )
    if source_type == ReactionSourceType.POST_BREAKOUT_DAILY_OC:
        return (
            f"The Post-Breakout OC reaction produced a qualifying "
            f"{classification_lower} {direction_lower} H4 breakout, "
            f"aligning the Daily and H4 directions."
        )
    return (
        f"The reaction produced a qualifying {classification_lower} "
        f"{direction_lower} H4 breakout, aligning the Daily and H4 directions."
    )


# ── Entry confirmation alert (PCL / Engulfing Sweep) ──────────────────────────

_ENTRY_PATTERN_NAMES: dict[str, str] = {
    "pcl":              "MummyTKT's PCL",
    "engulfing_sweep":  "Engulfing Sweep",
}

_TF_LABELS: dict[str, str] = {
    "60":  "H1",
    "120": "H2",
    "240": "H4",
}


def format_entry_alert(
    instrument: str,
    direction: str,          # "bullish" | "bearish"
    pattern: str,            # "pcl" | "engulfing_sweep"
    timeframe: str,          # pine's timeframe.period, e.g. "60" / "120"
    price: float,
    swept_level: float,
) -> str:
    """Build the Telegram message for a PCL or Engulfing Sweep entry confirmation."""
    direction_label = "Bullish" if direction == "bullish" else "Bearish"
    direction_lower = direction_label.lower()
    bias_side = "Buy" if direction == "bullish" else "Sell"

    pattern_name = _ENTRY_PATTERN_NAMES.get(pattern, pattern.replace("_", " ").title())
    tf_label = _TF_LABELS.get(timeframe, timeframe)

    price_str = _fmt_level(instrument, price)
    swept_str = _fmt_level(instrument, swept_level)

    if pattern == "pcl":
        if direction == "bearish":
            desc = (
                f"The {tf_label} candle wicked below the previous bullish body low "
                f"@ {swept_str} but closed back above it — a liquidity sweep "
                f"without a body close-through."
            )
        else:
            desc = (
                f"The {tf_label} candle wicked above the previous bearish body high "
                f"@ {swept_str} but closed back below it — a liquidity sweep "
                f"without a body close-through."
            )
    else:  # engulfing_sweep
        if direction == "bearish":
            desc = (
                f"The {tf_label} candle swept the previous bullish body low "
                f"@ {swept_str} AND closed below it — a full sweep with body "
                f"close-through (stronger than a PCL)."
            )
        else:
            desc = (
                f"The {tf_label} candle swept the previous bearish body high "
                f"@ {swept_str} AND closed above it — a full sweep with body "
                f"close-through (stronger than a PCL)."
            )

    lines = [
        f"ENTRY CONFIRMATION — {tagged(instrument)}",
        f"{pattern_name} · {tf_label} · {direction_label}",
        "",
        f"Pattern: {pattern_name} ({direction_lower})",
        f"Timeframe: {tf_label}",
        f"Swept level: {swept_str}",
        f"Confirmation close: {price_str}",
        "",
        desc,
        "",
        f"Aligned with the active {bias_side} bias — look for your entry from here, "
        f"managed per your plan.",
        "",
        "⚠️ Entry confirmation — not financial advice. Trade your own risk.",
        "",
        _signature(),
    ]
    return "\n".join(lines)

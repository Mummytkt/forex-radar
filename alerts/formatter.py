"""
Alert message formatter.

Builds the exact human-readable bias-confirmation alert from an AlertRecord.
Handles four alert classifications:
  ORIGIN                  — first H4 confirmation from a Daily reaction source
  CONTINUATION_ASHAPE     — subsequent H4 A/V formation break in the daily direction
  CONTINUATION_H4_OC      — H4 OC reaction (close beyond OC midpoint)
  CONTINUATION_H4_BREAKER — H4 Breaker or A/V inside range retested with wick+close
"""

from __future__ import annotations

from datetime import datetime

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
    instr = instrument.upper().replace("/", "")
    if instr.endswith("JPY") or instr in {"XAUUSD", "XAGUSD"}:
        return f"{level:.3f}"
    return f"{level:.5f}"


def _fmt_ts(dt: datetime | None) -> str:
    if dt is None:
        return "—"
    return dt.strftime("%a %d %b '%y, %H:%M UTC")


# ── Dispatcher ────────────────────────────────────────────────────────────────

def format_alert(alert: AlertRecord) -> str:
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

    bias_label = "BUY BIAS CONFIRMED" if direction == Direction.BULLISH else "SELL BIAS CONFIRMED"
    direction_label = "Bullish" if direction == Direction.BULLISH else "Bearish"
    direction_lower = direction_label.lower()

    broken_type_name = _BROKEN_TYPE_NAMES.get(breakout.broken_type, breakout.broken_type.value)
    breakout_level_str = _fmt_level(instrument, breakout.broken_level)

    if direction == Direction.BEARISH:
        breakout_desc = (
            f"Price broke and closed below the body level of the most recent "
            f"Daily {broken_type_name} key level @ {breakout_level_str}. "
            f"This is the most recent confirmed Daily breakout."
        )
    else:
        breakout_desc = (
            f"Price broke and closed above the body level of the most recent "
            f"Daily {broken_type_name} key level @ {breakout_level_str}. "
            f"This is the most recent confirmed Daily breakout."
        )

    source_name = _SOURCE_NAMES[source.source_type]
    if source.source_type == ReactionSourceType.AV_INSIDE_RANGE:
        source_name = f"Daily {'V' if direction == Direction.BULLISH else 'A'}-shape inside the range"
    source_level_str = _fmt_level(instrument, source.level)

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
        f"{bias_label} — {instrument}",
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
        "— TradingView Feed",
    ]
    return "\n".join(lines)


# ── Continuation A-shape alert ────────────────────────────────────────────────

def _format_continuation_ashape(alert: AlertRecord) -> str:
    direction = alert.direction
    instrument = alert.instrument
    h4 = alert.h4_event

    bias_label = "BUY BIAS CONFIRMED (continuation)" if direction == Direction.BULLISH else "SELL BIAS CONFIRMED (continuation)"
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
        f"{bias_label} — {instrument}",
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
        "— TradingView Feed",
    ]
    return "\n".join(lines)


# ── Continuation H4 Breaker alert ─────────────────────────────────────────────

def _format_continuation_h4_breaker(alert: AlertRecord) -> str:
    direction = alert.direction
    instrument = alert.instrument
    level = alert.h4_breaker_level

    bias_label = "BUY BIAS CONFIRMED (continuation)" if direction == Direction.BULLISH else "SELL BIAS CONFIRMED (continuation)"
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
        f"{bias_label} — {instrument}",
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
        "— TradingView Feed",
    ]
    return "\n".join(lines)


# ── Continuation H4 OC alert ──────────────────────────────────────────────────

def _format_continuation_h4_oc(alert: AlertRecord) -> str:
    direction = alert.direction
    instrument = alert.instrument
    oc_level = alert.h4_oc_level

    bias_label = "BUY BIAS CONFIRMED (continuation)" if direction == Direction.BULLISH else "SELL BIAS CONFIRMED (continuation)"
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
        f"{bias_label} — {instrument}",
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
        "— TradingView Feed",
    ]
    return "\n".join(lines)


# ── H4 Breaker Origin alert ───────────────────────────────────────────────────

def _format_h4_breaker_origin(alert: AlertRecord) -> str:
    direction = alert.direction
    instrument = alert.instrument
    level = alert.h4_breaker_level

    bias_label = "BUY BIAS CONFIRMED (continuation)" if direction == Direction.BULLISH else "SELL BIAS CONFIRMED (continuation)"
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
        f"{bias_label} — {instrument}",
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
        "— TradingView Feed",
    ]
    return "\n".join(lines)


# ── H4 Breakout Continuation alert ───────────────────────────────────────────

def _format_h4_breakout_cont(alert: AlertRecord) -> str:
    direction = alert.direction
    instrument = alert.instrument
    level = alert.h4_breaker_level

    bias_label = "BUY BIAS CONFIRMED (continuation)" if direction == Direction.BULLISH else "SELL BIAS CONFIRMED (continuation)"
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

    lines = [
        f"{bias_label} — {instrument}",
        "H4 Breakout Continuation",
        "",
        f"Daily breakout: {direction_label} (active)",
        "",
        f"H4 breakout @ {level_str}",
        desc,
        "",
        f"Reason: A new H4 breakout in the {direction_lower} direction has extended the active Daily "
        f"{direction_lower} bias. The overall direction remains intact.",
        "",
        _context_line(alert),
        "",
        "⚠️ Directional bias only — not an entry signal. Wait for the entry model.",
        "",
        "— TradingView Feed",
    ]
    return "\n".join(lines)


# ── H4 Breaker Continuation alert ────────────────────────────────────────────

def _format_h4_breaker_cont(alert: AlertRecord) -> str:
    direction = alert.direction
    instrument = alert.instrument
    level = alert.h4_breaker_level

    bias_label = "BUY BIAS CONFIRMED (continuation)" if direction == Direction.BULLISH else "SELL BIAS CONFIRMED (continuation)"
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
        f"{bias_label} — {instrument}",
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
        "— TradingView Feed",
    ]
    return "\n".join(lines)


# ── H4 OC Continuation alert ──────────────────────────────────────────────────

def _format_h4_oc_cont(alert: AlertRecord) -> str:
    direction = alert.direction
    instrument = alert.instrument
    oc_level = alert.h4_oc_level

    bias_label = "BUY BIAS CONFIRMED (continuation)" if direction == Direction.BULLISH else "SELL BIAS CONFIRMED (continuation)"
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
        f"{bias_label} — {instrument}",
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
        "— TradingView Feed",
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
        f"ENTRY CONFIRMATION — {instrument}",
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
        "— TradingView Feed",
    ]
    return "\n".join(lines)

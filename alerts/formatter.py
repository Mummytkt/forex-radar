"""
Alert message formatter.

Builds the exact human-readable bias-confirmation alert from an AlertRecord.
The format matches the specification provided in the strategy documentation.
"""

from __future__ import annotations

from data.models import (
    AlertRecord,
    BreakoutClassification,
    Direction,
    FormationType,
    ReactionSourceType,
)


_SOURCE_NAMES: dict[ReactionSourceType, str] = {
    ReactionSourceType.DAILY_BREAKER:          "Daily Breaker",
    ReactionSourceType.OC_INSIDE_RANGE:        "OC inside Daily range",
    ReactionSourceType.AV_INSIDE_RANGE:        "A/V key level inside Daily range",
    ReactionSourceType.POST_BREAKOUT_DAILY_OC: "Post-breakout {direction} OC",
}

_BROKEN_TYPE_NAMES: dict[FormationType, str] = {
    FormationType.A_SHAPE: "A-shape",
    FormationType.V_SHAPE: "V-shape",
    FormationType.OC:      "OC",
}


def format_alert(alert: AlertRecord) -> str:
    direction = alert.direction
    instrument = alert.instrument
    breakout = alert.daily_breakout
    source = alert.reaction_source
    h4 = alert.h4_event

    bias_label = "BUY BIAS CONFIRMED" if direction == Direction.BULLISH else "SELL BIAS CONFIRMED"
    direction_label = "Bullish" if direction == Direction.BULLISH else "Bearish"
    direction_lower = direction_label.lower()

    broken_type_name = _BROKEN_TYPE_NAMES.get(breakout.broken_type, breakout.broken_type.value)

    # ── Daily breakout description ────────────────────────────────────────────
    if direction == Direction.BEARISH:
        breakout_desc = (
            f"Price broke and closed below the body level of the most recent "
            f"Daily {broken_type_name} key level. "
            f"This is the most recent confirmed Daily breakout."
        )
    else:
        breakout_desc = (
            f"Price broke and closed above the body level of the most recent "
            f"Daily {broken_type_name} key level. "
            f"This is the most recent confirmed Daily breakout."
        )

    # ── Reaction source description ───────────────────────────────────────────
    source_name = _SOURCE_NAMES[source.source_type]
    if source.source_type == ReactionSourceType.POST_BREAKOUT_DAILY_OC:
        source_name = source_name.format(direction=direction_label)

    source_desc = _source_description(source.source_type, direction_lower, source_name)

    # ── H4 breakout description ───────────────────────────────────────────────
    classification_label = (
        "External" if h4.classification == BreakoutClassification.EXTERNAL else "Internal"
    )
    h4_formation_name = _BROKEN_TYPE_NAMES.get(
        h4.formation_broken.formation_type, h4.formation_broken.formation_type.value
    )
    if direction == Direction.BEARISH:
        h4_desc = (
            f"An H4 {h4_formation_name} formation was broken, and an H4 candle "
            f"closed below its body level. "
            f"The H4 breakout aligns with the most recent Daily breakout."
        )
    else:
        h4_desc = (
            f"An H4 {h4_formation_name} formation was broken, and an H4 candle "
            f"closed above its body level. "
            f"The H4 breakout aligns with the most recent Daily breakout."
        )

    # ── Reason sentence ───────────────────────────────────────────────────────
    reason = _reason_sentence(source.source_type, direction_label, classification_label, direction_lower)

    lines = [
        f"{bias_label} — {instrument}",
        "Daily → H4 aligned",
        "",
        f"Daily breakout: {direction_label}",
        breakout_desc,
        "",
        f"Daily reaction source: {source_name}",
        source_desc,
        "",
        f"H4 confirmation: {classification_label} {direction_lower} breakout",
        h4_desc,
        "",
        f"Reason: {reason}",
        "",
        "⚠️ Directional bias only — not an entry signal. Wait for the entry model.",
    ]
    return "\n".join(lines)


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
            f"After the Daily breakout, price re-entered the previous Daily range "
            f"and reacted from an A/V key level within that range. "
            f"The reaction produced the confirming H4 breakout."
        )
    if source_type == ReactionSourceType.POST_BREAKOUT_DAILY_OC:
        return (
            f"Price formed a {direction_lower} Daily OC after the breakout and "
            f"subsequently retraced into that OC level. "
            f"The reaction from the OC led to the confirming H4 breakout."
        )
    return f"Price reacted from {source_name}, leading to the confirming H4 breakout."


def _reason_sentence(
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
            f"The A/V key level inside the range reaction produced a qualifying "
            f"{classification_lower} {direction_lower} H4 breakout, "
            f"aligning the Daily and H4 directions."
        )
    if source_type == ReactionSourceType.POST_BREAKOUT_DAILY_OC:
        return (
            f"The post-breakout Daily OC reaction produced a qualifying "
            f"{classification_lower} {direction_lower} H4 breakout, "
            f"aligning the Daily and H4 directions."
        )
    return (
        f"The reaction produced a qualifying {classification_lower} "
        f"{direction_lower} H4 breakout, aligning the Daily and H4 directions."
    )

"""
/quote on the owner's Job Hunt bot (owner request 2026-11-23): MummyTKT Style House pricing.

    /quote 25000                    tailor price only, default profit 30% of costs
    /quote 25000 4000 1500          + other costs (fabric, labels, packaging, delivery…)
    /quote 25000 4000 1500 40%      profit as a % of total costs
    /quote 25000 4000 p10000        a fixed profit in naira (p or profit before the number)

Customer price = costs + profit, rounded UP to the nearest ₦500. The tailor is paid in two parts (half when the
order is confirmed, the rest after the photo/video quality check), per the tailor agreement doc.
"""

from __future__ import annotations

import html
import math
import re

DEFAULT_PCT = 30.0
ROUND_TO = 500


def _num(s: str) -> float | None:
    s = s.replace(",", "").replace("₦", "").replace("n", "").strip()
    try:
        return float(s[:-1]) * 1000 if s.lower().endswith("k") else float(s)
    except ValueError:
        return None


def parse(arg: str):
    """(tailor, extras, pct, fixed) or None."""
    toks = [t for t in re.split(r"[\s+]+", arg.strip().lower()) if t]
    tailor, extras, pct, fixed, want_fixed = None, [], None, None, False
    for t in toks:
        if t in ("p", "profit"):
            want_fixed = True
            continue
        if t.endswith("%"):
            v = _num(t[:-1])
            if v is None:
                return None
            pct = v
            continue
        if t.startswith("p") and not t.startswith("pr"):
            want_fixed, t = True, t[1:]
        v = _num(t)
        if v is None:
            return None
        if want_fixed:
            fixed, want_fixed = v, False
        elif tailor is None:
            tailor = v
        else:
            extras.append(v)
    if tailor is None or tailor <= 0:
        return None
    return tailor, extras, pct, fixed


def naira(v: float) -> str:
    return f"₦{v:,.0f}"


def quote_text(arg: str) -> str:
    p = parse(arg)
    if not p:
        return ("💰 <b>Price a style</b>\n\n<code>/quote tailor-price other-costs… profit</code>\n\n"
                "Examples:\n<code>/quote 25000</code> · tailor ₦25,000, profit 30%\n"
                "<code>/quote 25000 4000 1500</code> · plus fabric ₦4,000 and labels/packaging ₦1,500\n"
                "<code>/quote 25000 4000 40%</code> · profit 40% of costs\n"
                "<code>/quote 25000 4000 p10000</code> · a fixed ₦10,000 profit\n\n"
                "You can write 25k for 25000.")
    tailor, extras, pct, fixed = p
    costs = tailor + sum(extras)
    profit = fixed if fixed is not None else costs * (pct if pct is not None else DEFAULT_PCT) / 100
    price = math.ceil((costs + profit) / ROUND_TO) * ROUND_TO
    profit = price - costs
    first = math.ceil(tailor / 2 / 100) * 100
    lines = ["💰 <b>Style House quote</b>", "",
             f"Tailor: {naira(tailor)}"]
    lines += [f"Other cost {i}: {naira(v)}" for i, v in enumerate(extras, 1)]
    lines += [f"Total costs: <b>{naira(costs)}</b>", "",
              f"👉 Customer price: <b>{naira(price)}</b> (rounded up to the nearest ₦{ROUND_TO})",
              f"Your profit: <b>{naira(profit)}</b> ({profit / costs * 100:.0f}% of costs)", "",
              "Pay the tailor in two parts:",
              f"1. When the order is confirmed: {naira(first)}",
              f"2. After you approve the photos and video: {naira(tailor - first)}", "",
              "Message for the customer (tap to copy, fill the [brackets]):",
              "<code>" + html.escape(
                  f"Thank you for choosing MummyTKT Style House. Your style [code] in your measurements comes to "
                  f"{naira(price)}, ready by [date]. Once payment is confirmed we start sewing, and we'll send you "
                  f"photos before it's packaged and sent.", quote=False) + "</code>"]
    return "\n".join(lines)

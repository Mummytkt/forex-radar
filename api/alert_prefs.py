"""
Per-user choice of which Origin confirmation types reach Telegram.

Each account picks whether External and/or Internal H4 breakout confirmations
are delivered to their own Telegram. Continuation alerts are not affected —
they always go out, since they follow an Origin the user already received.

Stored in user_config as 'pref_alert_external:<uid>' / 'pref_alert_internal:<uid>'
('1' or '0'). Unset means on. The owner falls back to the legacy global keys
('pref_alert_external' / 'pref_alert_internal') saved before prefs were per-user.
"""

from __future__ import annotations

from typing import Optional

_KEYS = {"external": "pref_alert_external", "internal": "pref_alert_internal",
         "news": "pref_alert_news",   # high-impact news summary + 30-minute reminders
         # Alert types, each on by default
         "origin": "pref_alert_origin", "cont_inline": "pref_alert_cont_inline",
         "cont_breaker": "pref_alert_cont_breaker", "cont_oc": "pref_alert_cont_oc",
         "cont_realign": "pref_alert_cont_realign", "engulfing": "pref_alert_engulfing"}


def get_alert_prefs(conn, uid: Optional[int], role: Optional[str]) -> dict[str, bool]:
    prefs: dict[str, bool] = {}
    for kind, base in _KEYS.items():
        row = None
        if uid is not None:
            row = conn.execute("SELECT value FROM user_config WHERE key = ?", (f"{base}:{uid}",)).fetchone()
        if row is None and (uid is None or role == "OWNER"):
            row = conn.execute("SELECT value FROM user_config WHERE key = ?", (base,)).fetchone()
        prefs[kind] = (row[0] == "1") if row else True
    return prefs


def set_alert_pref(conn, uid: Optional[int], kind: str, on: bool) -> None:
    base = _KEYS[kind]
    key = f"{base}:{uid}" if uid is not None else base
    conn.execute(
        "INSERT OR REPLACE INTO user_config (key, value, updated_at) VALUES (?, ?, datetime('now'))",
        (key, "1" if on else "0"),
    )


def confirmation_kind(h4_class: Optional[str]) -> str:
    """Same rule the alert itself uses: anything not 'external' is internal."""
    return "external" if h4_class == "external" else "internal"

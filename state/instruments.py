"""
Platform instrument list: the DB copy, instruments added after launch, and
Deriv synthetic indices.

The list lives in user_config['instruments'] (the owner can edit it), so new
defaults in config.py never reach an existing database on their own.
PLATFORM_ADDITIONS are appended once each (recorded in
user_config['instruments_added']), so a later removal by the owner sticks.

Deriv synthetics (TradingView exchange "DERIV") register themselves the first
time their chart reports; their names are kept in
user_config['synthetic_instruments'] and in config.SYNTHETICS.
"""

from __future__ import annotations

import json

import config as _cfg

# Instruments added to the platform after the list was first saved.
PLATFORM_ADDITIONS: list[str] = ["XAG/USD"]


def _get(conn, key: str):
    row = conn.execute("SELECT value FROM user_config WHERE key = ?", (key,)).fetchone()
    return json.loads(row[0]) if row and row[0] else None


def _put(conn, key: str, value) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO user_config (key, value, updated_at) VALUES (?, ?, datetime('now'))",
        (key, json.dumps(value)),
    )


def load_instruments(conn, config) -> None:
    """Startup: read the saved list (or save the defaults), apply additions once,
    and load the synthetic set."""
    saved = _get(conn, "instruments")
    instruments = list(saved) if saved else list(config.instruments)
    added = set(_get(conn, "instruments_added") or [])
    norm = {i.replace("/", "").upper() for i in instruments}
    for inst in PLATFORM_ADDITIONS:
        if inst not in added:
            if inst.replace("/", "").upper() not in norm:
                instruments.append(inst)
            added.add(inst)
    _put(conn, "instruments", instruments)
    _put(conn, "instruments_added", sorted(added))
    conn.commit()
    config.instruments = instruments
    _cfg.SYNTHETICS.clear()
    _cfg.SYNTHETICS.update(_get(conn, "synthetic_instruments") or [])


def register_synthetic(conn, config, instrument: str) -> bool:
    """A Deriv chart reported: make sure the index is on the platform list and
    marked synthetic. Returns True the first time."""
    name = instrument.replace("/", "").upper()
    if name in _cfg.SYNTHETICS:
        return False
    _cfg.SYNTHETICS.add(name)
    _put(conn, "synthetic_instruments", sorted(_cfg.SYNTHETICS))
    if name not in {i.replace("/", "").upper() for i in config.instruments}:
        config.instruments = list(config.instruments) + [name]
        _put(conn, "instruments", config.instruments)
    conn.commit()
    return True

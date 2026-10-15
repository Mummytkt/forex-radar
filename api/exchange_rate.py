"""
Live USD→NGN rate fetched from the free open.er-api.com endpoint.

Usage:
    rate = get_ngn_rate(config)   # returns float, e.g. 1620.5

Result is cached in memory for 1 hour.  On any fetch failure the configured
fallback (config.paystack_ngn_rate) is returned and the cache is left empty
so the next call retries.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)

_cache_rate: float | None = None
_cache_ts: float = 0.0
_TTL = 3600  # seconds


def get_ngn_rate(config) -> float:
    """Return a live USD/NGN exchange rate, cached for 1 hour."""
    global _cache_rate, _cache_ts
    now = time.monotonic()
    if _cache_rate is not None and now - _cache_ts < _TTL:
        return _cache_rate

    try:
        req = urllib.request.Request(
            "https://open.er-api.com/v6/latest/USD",
            headers={"User-Agent": "Mozilla/5.0 (compatible; MummyTKT-BiasPointer/1.0)"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        rate = float(data["rates"]["NGN"])
        _cache_rate = rate
        _cache_ts = now
        logger.info("Exchange rate refreshed: 1 USD = %.2f NGN", rate)
        return rate
    except Exception as e:
        logger.warning("Exchange rate fetch failed (%s) — using fallback %.2f", e, config.paystack_ngn_rate)
        return config.paystack_ngn_rate

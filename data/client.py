"""
Twelve Data REST API client.

Supports both single-symbol and bulk (up to 10 symbols) requests via
the /time_series endpoint. Rate limiting is enforced with a simple
token-bucket: 8 requests per minute on the free tier.

Raises TwelveDataError on non-200 responses or API-level error payloads.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.twelvedata.com"
_MAX_SYMBOLS_PER_CALL = 10
_FREE_TIER_RPM = 8          # requests per minute
_MIN_INTERVAL_S = 60.0 / _FREE_TIER_RPM  # ~7.5 seconds between calls


class TwelveDataError(Exception):
    pass


class TwelveDataClient:
    """
    Stateful client that enforces per-call rate limiting.
    Instantiate once and reuse throughout the process lifetime.
    """

    def __init__(self, api_key: str, rpm_limit: int = _FREE_TIER_RPM):
        self._api_key = api_key
        self._min_interval = 60.0 / rpm_limit
        self._last_call_ts: float = 0.0

    def _wait_if_needed(self) -> None:
        elapsed = time.monotonic() - self._last_call_ts
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_call_ts = time.monotonic()

    def fetch_candles(
        self,
        symbol: str,
        interval: str,
        outputsize: int = 200,
        end_date: Optional[str] = None,
    ) -> list[dict]:
        """
        Fetch OHLCV candles for a single symbol.

        symbol   : e.g. "EUR/USD"
        interval : "1day" or "4h"
        outputsize: number of candles to return (max 5000 on paid, 800 on free)
        end_date : ISO 8601 string "YYYY-MM-DD HH:MM:SS" (optional)

        Returns a list of raw dicts ordered newest → oldest (Twelve Data default).
        """
        params = {
            "symbol": symbol,
            "interval": interval,
            "outputsize": outputsize,
            "apikey": self._api_key,
            "format": "JSON",
            "timezone": "UTC",
        }
        if end_date:
            params["end_date"] = end_date

        for attempt in range(2):
            self._wait_if_needed()
            try:
                resp = httpx.get(f"{_BASE_URL}/time_series", params=params, timeout=30)
            except httpx.RequestError as e:
                raise TwelveDataError(f"Network error fetching {symbol}: {e}") from e

            if resp.status_code == 429:
                if attempt == 0:
                    logger.warning("Rate limited on %s — waiting 65s before retry", symbol)
                    time.sleep(65)
                    continue
                raise TwelveDataError(f"Rate limit persists for {symbol} after retry")

            if resp.status_code != 200:
                raise TwelveDataError(
                    f"HTTP {resp.status_code} fetching {symbol}: {resp.text[:200]}"
                )
            break

        data = resp.json()
        if data.get("status") == "error":
            raise TwelveDataError(
                f"Twelve Data error for {symbol}: {data.get('message', data)}"
            )

        values = data.get("values")
        if not values:
            logger.warning("No candles returned for %s %s", symbol, interval)
            return []

        return values  # newest → oldest

    def fetch_candles_bulk(
        self,
        symbols: list[str],
        interval: str,
        outputsize: int = 200,
    ) -> dict[str, list[dict]]:
        """
        Fetch candles for up to 10 symbols in one API call.
        Returns a dict keyed by the symbol string as returned by Twelve Data.
        Symbols that returned an error are silently omitted with a warning logged.
        """
        if len(symbols) > _MAX_SYMBOLS_PER_CALL:
            raise ValueError(
                f"fetch_candles_bulk supports at most {_MAX_SYMBOLS_PER_CALL} symbols; "
                f"got {len(symbols)}"
            )

        params = {
            "symbol": ",".join(symbols),
            "interval": interval,
            "outputsize": outputsize,
            "apikey": self._api_key,
            "format": "JSON",
            "timezone": "UTC",
        }

        self._wait_if_needed()
        try:
            resp = httpx.get(f"{_BASE_URL}/time_series", params=params, timeout=60)
        except httpx.RequestError as e:
            raise TwelveDataError(f"Network error on bulk fetch: {e}") from e

        if resp.status_code != 200:
            raise TwelveDataError(f"HTTP {resp.status_code} on bulk fetch: {resp.text[:200]}")

        data = resp.json()

        # Single symbol returns the same shape as multi; normalise to dict
        if "values" in data:
            # Single-symbol response wrapped in a single object
            key = symbols[0]
            if data.get("status") == "error":
                logger.warning("Error for %s: %s", key, data.get("message"))
                return {}
            return {key: data.get("values", [])}

        result: dict[str, list[dict]] = {}
        for sym, payload in data.items():
            if isinstance(payload, dict):
                if payload.get("status") == "error":
                    logger.warning("Error for %s: %s", sym, payload.get("message"))
                    continue
                result[sym] = payload.get("values", [])
        return result

    def fetch_all_instruments(
        self,
        symbols: list[str],
        interval: str,
        outputsize: int = 200,
    ) -> dict[str, list[dict]]:
        """
        Fetch candles for any number of symbols using batched bulk calls.
        Respects the 10-symbol-per-call limit automatically.
        """
        results: dict[str, list[dict]] = {}
        for i in range(0, len(symbols), _MAX_SYMBOLS_PER_CALL):
            batch = symbols[i : i + _MAX_SYMBOLS_PER_CALL]
            batch_results = self.fetch_candles_bulk(batch, interval, outputsize)
            results.update(batch_results)
        return results

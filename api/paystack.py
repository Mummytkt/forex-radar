"""
Minimal Paystack REST client (standard library only — urllib + hmac).

All calls are synchronous; call them from async handlers via
`await asyncio.to_thread(...)` so the event loop is never blocked.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

_BASE = "https://api.paystack.co"


class PaystackError(Exception):
    pass


def _request(method: str, path: str, secret_key: str, body: dict | None = None) -> dict:
    url = _BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {secret_key}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        logger.warning("Paystack %s %s failed: %s %s", method, path, e.code, detail)
        raise PaystackError(f"Paystack {e.code}: {detail}") from e
    except Exception as e:
        logger.warning("Paystack %s %s error: %s", method, path, e)
        raise PaystackError(str(e)) from e


def initialize_transaction(
    secret_key: str, *, email: str, amount_subunits: int, currency: str,
    reference: str, callback_url: str, metadata: dict,
) -> dict:
    """Start a transaction; returns {authorization_url, access_code, reference}."""
    payload = {
        "email": email,
        "amount": amount_subunits,
        "currency": currency,
        "reference": reference,
        "callback_url": callback_url,
        "metadata": metadata,
    }
    res = _request("POST", "/transaction/initialize", secret_key, payload)
    if not res.get("status"):
        raise PaystackError(res.get("message", "initialize failed"))
    return res["data"]


def verify_transaction(secret_key: str, reference: str) -> dict:
    """Return the transaction data for a reference (status, authorization, etc.)."""
    res = _request("GET", f"/transaction/verify/{reference}", secret_key)
    if not res.get("status"):
        raise PaystackError(res.get("message", "verify failed"))
    return res["data"]


def charge_authorization(
    secret_key: str, *, email: str, amount_subunits: int, currency: str,
    authorization_code: str, reference: str, metadata: dict,
) -> dict:
    """Charge a previously-saved card (for renewals / trial day-7 charge)."""
    payload = {
        "email": email,
        "amount": amount_subunits,
        "currency": currency,
        "authorization_code": authorization_code,
        "reference": reference,
        "metadata": metadata,
    }
    res = _request("POST", "/transaction/charge_authorization", secret_key, payload)
    if not res.get("status"):
        raise PaystackError(res.get("message", "charge_authorization failed"))
    return res["data"]


def refund(secret_key: str, reference: str) -> dict:
    """Refund a transaction in full (used to make the trial tokenization free)."""
    res = _request("POST", "/refund", secret_key, {"transaction": reference})
    return res.get("data", {})


def verify_webhook_signature(secret_key: str, raw_body: bytes, signature: str) -> bool:
    """Paystack signs webhook bodies with HMAC-SHA512 of the raw body."""
    if not signature:
        return False
    expected = hmac.new(secret_key.encode(), raw_body, hashlib.sha512).hexdigest()
    return hmac.compare_digest(expected, signature)

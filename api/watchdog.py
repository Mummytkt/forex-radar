"""Freeze watchdog (owner, 2026-11-26).

On 2026-11-26 a stuck Yahoo download blocked the server's event loop for 11 minutes: every page loaded empty
until a manual restart. This thread sits outside the event loop and checks every 30 s that the loop still runs
a tiny job. If the loop hasn't answered for STALL seconds, the process exits and Fly starts it again fresh
(fly.toml restart policy "always"), so a freeze lasts about 2 minutes at most.
"""
import asyncio
import logging
import os
import threading
import time

logger = logging.getLogger(__name__)

CHECK = 30     # seconds between checks
STALL = 120    # seconds without an answer = frozen


def start(loop: asyncio.AbstractEventLoop, check: float = CHECK, stall: float = STALL, on_freeze=None) -> threading.Thread:
    last = {"t": time.monotonic()}

    def beat():
        last["t"] = time.monotonic()

    def run():
        while True:
            time.sleep(check)
            if loop.is_closed():
                return
            try:
                loop.call_soon_threadsafe(beat)
            except RuntimeError:
                return
            stuck = time.monotonic() - last["t"]
            if stuck > stall:
                logger.critical("Watchdog: the server has not answered for %d s; restarting it", int(stuck))
                for h in logging.getLogger().handlers:
                    try:
                        h.flush()
                    except Exception:
                        pass
                (on_freeze or (lambda: os._exit(3)))()
                return

    t = threading.Thread(target=run, name="freeze-watchdog", daemon=True)
    t.start()
    return t

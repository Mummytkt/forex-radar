"""
Database backups (runs daily, and on demand from the owner's Business page).

Three layers protect the platform's data:
  1. Fly.io volume snapshots — daily, kept 5 days (configured on the volume).
  2. Local copies — a consistent SQLite copy written to <db dir>/backups/,
     newest 7 kept. Fast restore after a bad change or corruption.
  3. Off-site copy — the same file, gzipped and encrypted with BACKUP_KEY,
     sent to the owner's Telegram. Survives losing the Fly app or volume.
     Restore with: python scripts/restore_backup.py <file.enc> <key file>
"""

from __future__ import annotations

import asyncio
import gzip
import logging
import os
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

KEEP_LOCAL = 7


def _make_local_copy(db_path: str) -> tuple[Path, bool]:
    """Write a consistent copy via SQLite's online backup API, verify it, prune old ones."""
    backups_dir = Path(db_path).resolve().parent / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    dest = backups_dir / f"forex_radar-{stamp}.db"

    src = sqlite3.connect(db_path)
    dst = sqlite3.connect(dest)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()

    check = sqlite3.connect(dest)
    try:
        ok = check.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        check.close()

    copies = sorted(backups_dir.glob("forex_radar-*.db"))
    for old in copies[:-KEEP_LOCAL]:
        try:
            old.unlink()
        except OSError:
            pass
    return dest, ok


def _encrypt(path: Path, key: str) -> Path:
    from cryptography.fernet import Fernet
    data = gzip.compress(path.read_bytes())
    token = Fernet(key.encode()).encrypt(data)
    fd, tmp = tempfile.mkstemp(suffix=".enc")
    with os.fdopen(fd, "wb") as f:
        f.write(token)
    return Path(tmp)


async def run_backup(db_path: str, config, send_offsite: bool = True) -> dict:
    """Make a backup. Returns a summary dict (also used by the Business page)."""
    from alerts.telegram import send_document, send_alert

    result = {"file": None, "size_kb": 0, "integrity_ok": False, "offsite_sent": False, "error": None}
    try:
        dest, ok = await asyncio.to_thread(_make_local_copy, db_path)
        result.update(file=dest.name, size_kb=round(dest.stat().st_size / 1024), integrity_ok=ok)
        logger.info("Backup written: %s (%d KB, integrity=%s)", dest.name, result["size_kb"], ok)

        can_send = send_offsite and config.telegram_enabled and config.telegram_bot_token and config.telegram_chat_id
        if can_send and not config.backup_key:
            logger.warning("BACKUP_KEY not set — off-site backup skipped")
        elif can_send:
            enc = await asyncio.to_thread(_encrypt, dest, config.backup_key)
            try:
                caption = (
                    f"🗄 Bias Pointer backup {dest.stem.replace('forex_radar-', '')} UTC\n"
                    f"{result['size_kb']} KB · integrity {'OK' if ok else 'FAILED'}\n"
                    "Encrypted. Keep this file; restore with your backup key."
                )
                result["offsite_sent"] = await send_document(
                    config.telegram_bot_token, config.telegram_chat_id, str(enc),
                    f"{dest.stem}.db.gz.enc", caption)
            finally:
                try:
                    enc.unlink()
                except OSError:
                    pass

        if not ok and config.telegram_enabled and config.telegram_chat_id:
            await send_alert(config.telegram_bot_token, config.telegram_chat_id,
                             "⚠️ Backup integrity check FAILED. The live database may be damaged — check the server logs.")
    except Exception as exc:  # never let a backup failure take anything else down
        logger.exception("Backup failed: %s", exc)
        result["error"] = str(exc)
    return result

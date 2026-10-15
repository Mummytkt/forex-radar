"""
Database backups (runs daily, and on demand from the owner's Business page).

Three layers protect the platform's data:
  1. Fly.io volume snapshots — daily, kept 5 days (configured on the volume).
  2. Local copies — a consistent SQLite copy written to <db dir>/backups/,
     newest 7 kept. Fast restore after a bad change or corruption.
  3. Off-site copy — the same file, gzipped and encrypted with BACKUP_KEY,
     sent to Telegram. Survives losing the Fly app or volume.
     Restore with: python scripts/restore_backup.py <file.enc> <key file>

Off-site destination: the owner's private backups channel when one is connected
(user_config 'backup_channel_id', set when the owner makes the bot a channel
admin), otherwise the owner's chat with the bot. In the channel the bot is an
admin, so it deletes backups older than RETAIN_DAYS — always keeping the newest
KEEP_MIN — which keeps the privacy policy's ~30-day promise automatically.
"""

from __future__ import annotations

import asyncio
import gzip
import logging
import os
import sqlite3
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

KEEP_LOCAL = 7
RETAIN_DAYS = 30
KEEP_MIN = 7  # never delete the newest few off-site backups, whatever their age


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


def get_backup_channel(conn) -> str | None:
    row = conn.execute("SELECT value FROM user_config WHERE key = 'backup_channel_id'").fetchone()
    return row[0] if row and row[0] else None


async def prune_offsite(conn, config) -> dict:
    """Delete channel backups older than RETAIN_DAYS (keeping the newest KEEP_MIN).
    Reports to the owner once when cleanup is confirmed working on a file older than
    Telegram's 48-hour window, and once a month if Telegram refuses."""
    from alerts.telegram import delete_message
    from alerts.reminders import notify_once

    now = datetime.now(timezone.utc)
    rows = conn.execute(
        "SELECT id, chat_id, message_id, sent_at, file_name FROM backup_messages "
        "WHERE deleted_at IS NULL ORDER BY sent_at DESC").fetchall()
    cutoff = now - timedelta(days=RETAIN_DAYS)
    candidates = [r for r in rows[KEEP_MIN:] if datetime.fromisoformat(r[3]) < cutoff]
    deleted, failed_err = 0, ""
    for r in candidates:
        ok, err = await delete_message(config.telegram_bot_token, r[1], r[2])
        if not ok:
            failed_err = err
            break
        conn.execute("UPDATE backup_messages SET deleted_at = ? WHERE id = ?", (now.isoformat(), r[0]))
        conn.commit()
        deleted += 1
        if now - datetime.fromisoformat(r[3]) > timedelta(hours=48):
            await notify_once(conn, config, "backup_cleanup_confirmed", config.telegram_chat_id,
                              "✅ Backup cleanup is working: I deleted a backup older than 30 days from your "
                              "backups channel. You don't need to delete old backups by hand.")
    if failed_err:
        logger.warning("Backup cleanup refused by Telegram: %s", failed_err)
        await notify_once(
            conn, config, f"backup_cleanup_failed:{now.strftime('%Y-%m')}", config.telegram_chat_id,
            "⚠️ Telegram wouldn't let me delete old backups from your backups channel "
            f"({failed_err}).\n\nPlease delete backup files older than {cutoff.strftime('%d %b %Y')} by hand, and "
            "check the bot is still an admin with “Delete messages” permission. Keep the newest ones.")
    return {"deleted": deleted, "error": failed_err or None}


async def run_backup(db_path: str, config, send_offsite: bool = True) -> dict:
    """Make a backup. Returns a summary dict (also used by the Business page)."""
    from alerts.telegram import send_document, send_alert

    result = {"file": None, "size_kb": 0, "integrity_ok": False, "offsite_sent": False,
              "destination": None, "old_deleted": 0, "error": None}
    try:
        dest, ok = await asyncio.to_thread(_make_local_copy, db_path)
        result.update(file=dest.name, size_kb=round(dest.stat().st_size / 1024), integrity_ok=ok)
        logger.info("Backup written: %s (%d KB, integrity=%s)", dest.name, result["size_kb"], ok)

        can_send = send_offsite and config.telegram_enabled and config.telegram_bot_token and config.telegram_chat_id
        if can_send and not config.backup_key:
            logger.warning("BACKUP_KEY not set — off-site backup skipped")
        elif can_send:
            conn = sqlite3.connect(db_path, check_same_thread=False)
            try:
                channel = get_backup_channel(conn)
                target = channel or config.telegram_chat_id
                result["destination"] = "channel" if channel else "chat"
                enc = await asyncio.to_thread(_encrypt, dest, config.backup_key)
                try:
                    caption = (
                        f"🗄 Bias Pointer backup {dest.stem.replace('forex_radar-', '')} UTC\n"
                        f"{result['size_kb']} KB · integrity {'OK' if ok else 'FAILED'}\n"
                        "Encrypted. Keep this file; restore with your backup key."
                    )
                    fname = f"{dest.stem}.db.gz.enc"
                    msg_id = await send_document(config.telegram_bot_token, target, str(enc), fname, caption)
                    result["offsite_sent"] = msg_id is not None
                    if msg_id is not None and channel:
                        conn.execute(
                            "INSERT INTO backup_messages (chat_id, message_id, file_name, sent_at) VALUES (?, ?, ?, ?)",
                            (channel, msg_id, fname, datetime.now(timezone.utc).isoformat()))
                        conn.commit()
                finally:
                    try:
                        enc.unlink()
                    except OSError:
                        pass
                if channel:
                    result["old_deleted"] = (await prune_offsite(conn, config))["deleted"]
            finally:
                conn.close()

        if not ok and config.telegram_enabled and config.telegram_chat_id:
            await send_alert(config.telegram_bot_token, config.telegram_chat_id,
                             "⚠️ Backup integrity check FAILED. The live database may be damaged — check the server logs.")
    except Exception as exc:  # never let a backup failure take anything else down
        logger.exception("Backup failed: %s", exc)
        result["error"] = str(exc)
    return result

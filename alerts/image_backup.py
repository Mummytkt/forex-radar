"""
Weekly off-site copy of the Entry Tester chart images (Sundays).

The nightly database backup (alerts/backup.py) holds every tick and RR but not
the screenshots: they live as files in <db dir>/entry_images on the Fly volume,
which only Fly's 5-day snapshots cover. Once a week this sends the images that
haven't been sent yet to the same place as the database backups (the owner's
backups channel, or the owner's chat), as plain zip files the owner can open.

Each image is sent once and those messages are never auto-deleted (they are not
recorded in backup_messages, which the 30-day cleanup works from), so every
picture always has a copy outside Fly. Zips are kept small (PART_LIMIT) so the
256 MB server never holds much in memory, well under Telegram's 50 MB file cap.
A manifest.json in each zip maps the files back to their trade and POI.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

PART_LIMIT = 15 * 1024 * 1024
POI_NAMES = {"fvg": "H4-FVG", "engulfing": "H4-Engulfing", "h4_key": "H4-fresh-key-level"}


def _pending(conn, img_dir: Path) -> list[dict]:
    rows = conn.execute(
        "SELECT i.id, i.file_name, i.poi, i.test_id, t.instrument, t.trade_date "
        "FROM entry_test_images i JOIN entry_tests t ON t.id = i.test_id "
        "WHERE i.backed_up_at IS NULL ORDER BY i.id").fetchall()
    out = []
    for r in rows:
        f = img_dir / r[1]
        if f.is_file():
            out.append({"id": r[0], "file_name": r[1], "poi": r[2], "test_id": r[3],
                        "instrument": r[4], "trade_date": r[5], "path": f, "size": f.stat().st_size})
    return out


def _parts(items: list[dict]) -> list[list[dict]]:
    parts, cur, size = [], [], 0
    for it in items:
        if cur and size + it["size"] > PART_LIMIT:
            parts.append(cur)
            cur, size = [], 0
        cur.append(it)
        size += it["size"]
    if cur:
        parts.append(cur)
    return parts


def _zip(part: list[dict]) -> Path:
    fd, tmp = tempfile.mkstemp(suffix=".zip")
    os.close(fd)
    manifest = []
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_STORED) as z:   # JPEGs are already compressed
        for it in part:
            name = f"{it['trade_date']}_{it['instrument']}_{POI_NAMES.get(it['poi'], it['poi'])}_trade{it['test_id']}.jpg"
            z.write(it["path"], name)
            manifest.append({"file": name, "stored_as": it["file_name"], "trade_id": it["test_id"],
                             "poi": it["poi"], "instrument": it["instrument"], "trade_date": it["trade_date"]})
        z.writestr("manifest.json", json.dumps(manifest, indent=1))
    return Path(tmp)


async def run_image_backup(db_path: str, config) -> dict:
    """Send every chart image not sent before. Returns a summary."""
    from alerts.backup import get_backup_channel
    from alerts.telegram import send_document

    result = {"images": 0, "files_sent": 0, "error": None}
    if not (config.telegram_enabled and config.telegram_bot_token and config.telegram_chat_id):
        return result
    conn = sqlite3.connect(db_path, check_same_thread=False)
    try:
        img_dir = Path(db_path).resolve().parent / "entry_images"
        items = _pending(conn, img_dir)
        if not items:
            return result
        target = get_backup_channel(conn) or config.telegram_chat_id
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        parts = _parts(items)
        for n, part in enumerate(parts, 1):
            z = _zip(part)
            try:
                label = f" (part {n} of {len(parts)})" if len(parts) > 1 else ""
                caption = (f"🖼 Entry Tester chart images {stamp}{label}\n"
                           f"{len(part)} new image{'s' if len(part) != 1 else ''}. Keep this file: "
                           "it is the off-site copy of these screenshots (they are not in the nightly backup).")
                msg_id = await send_document(config.telegram_bot_token, target, str(z),
                                             f"entry-images-{stamp}{f'-part{n}' if len(parts) > 1 else ''}.zip", caption)
            finally:
                try:
                    z.unlink()
                except OSError:
                    pass
            if msg_id is None:
                result["error"] = "Telegram refused the file"
                break   # the rest go next week
            now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            conn.executemany("UPDATE entry_test_images SET backed_up_at = ? WHERE id = ?", [(now, it["id"]) for it in part])
            conn.commit()
            result["images"] += len(part)
            result["files_sent"] += 1
        logger.info("Image backup: %d images in %d files", result["images"], result["files_sent"])
    except Exception as exc:   # never let a backup failure take anything else down
        logger.exception("Image backup failed: %s", exc)
        result["error"] = str(exc)
    finally:
        conn.close()
    return result

"""
Restore an encrypted off-site backup (the .db.gz.enc file the bot sends to Telegram).

Usage:
    python scripts/restore_backup.py <backup.db.gz.enc> <key file or key> [output.db]

Writes a plain SQLite database (default: restored.db next to the backup) and runs
an integrity check. To put it live, copy it over /data/forex_radar.db on the Fly
volume while the app is stopped (see the steps printed at the end).
"""

from __future__ import annotations

import gzip
import sqlite3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    enc_path = Path(sys.argv[1])
    key_arg = sys.argv[2]
    key = Path(key_arg).read_text().strip() if Path(key_arg).is_file() else key_arg.strip()
    out = Path(sys.argv[3]) if len(sys.argv) > 3 else enc_path.with_name("restored.db")

    from cryptography.fernet import Fernet, InvalidToken
    try:
        data = gzip.decompress(Fernet(key.encode()).decrypt(enc_path.read_bytes()))
    except InvalidToken:
        print("Could not decrypt: wrong backup key, or the file is damaged.")
        return 2
    out.write_bytes(data)

    conn = sqlite3.connect(out)
    try:
        ok = conn.execute("PRAGMA integrity_check").fetchone()[0]
        users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    finally:
        conn.close()
    print(f"Restored to {out}  (integrity: {ok}, users: {users})")
    print("\nTo put it live on Fly:")
    print("  1. flyctl machine stop -a forex-radar")
    print("  2. flyctl ssh sftp shell -a forex-radar   then: put restored.db /data/forex_radar.db")
    print("     (start the machine first if sftp needs it, then stop the app process)")
    print("  3. flyctl machine start -a forex-radar")
    return 0 if ok == "ok" else 3


if __name__ == "__main__":
    sys.exit(main())

"""Runs the end-to-end platform checks in their own process (they set env vars
and app state at import time) and fails if any check fails."""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def test_platform_end_to_end():
    r = subprocess.run([sys.executable, os.path.join(HERE, "e2e_platform.py")],
                       capture_output=True, text=True, encoding="utf-8",
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"}, timeout=600)
    failed = [l for l in r.stdout.splitlines() if l.startswith("FAIL ")]
    assert r.returncode == 0, "\n".join(failed) or r.stderr[-3000:]

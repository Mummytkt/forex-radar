"""Level Watch 1D / 1W: candles from the stored TradingView Daily candles."""
import sqlite3
from datetime import datetime, timezone

from alerts.price_monitor import htf_candles, htf_triggered
from state.candles import upsert


def _ms(y, m, d, h=22):
    return int(datetime(y, m, d, h, tzinfo=timezone.utc).timestamp() * 1000)


def _conn():
    conn = sqlite3.connect(":memory:")
    # FX Daily candles open 22:00 UTC the evening before: Sun 18 Oct 2026 22:00 = Monday 19th
    bars = [[_ms(2026, 10, d), 1.10, 1.12, 1.09, 1.11] for d in (18, 19, 20, 21, 22)]   # Mon-Fri week 43
    bars += [[_ms(2026, 10, 25), 1.11, 1.15, 1.10, 1.14]]                              # Mon week 44
    upsert(conn, "EURUSD", "D", bars)
    return conn


def test_daily_candles_close_at_the_next_open():
    c = htf_candles(_conn(), "EURUSD", "1D")
    assert len(c) == 6
    assert c[0][1] == c[1][0]   # close time = next candle's open


def test_weekly_groups_monday_to_friday_and_skips_an_unfinished_week():
    w = htf_candles(_conn(), "EURUSD", "1W")
    assert len(w) == 1          # week 44 has only Monday: not complete yet
    t0, end, o, h, l, cl = w[0]
    assert (o, h, l, cl) == (1.10, 1.12, 1.09, 1.11)


def test_conditions_on_the_closed_candle():
    assert htf_triggered("rejects", 1.12, None, 1.125, 1.10, 1.11) == "from above"
    assert htf_triggered("rejects", 1.10, None, 1.12, 1.095, 1.11) == "from below"
    assert htf_triggered("rejects", 1.13, None, 1.12, 1.10, 1.11) == ""
    assert htf_triggered("crossing_up", 1.12, 1.11, 1.15, 1.10, 1.14) == "above"
    assert htf_triggered("crossing_down", 1.12, 1.11, 1.15, 1.10, 1.14) == ""
    assert htf_triggered("crossing", 1.12, 1.13, 1.14, 1.10, 1.11) == "below"

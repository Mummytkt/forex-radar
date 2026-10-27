"""Level Watch on candle close (15m-4h): the whole candle, built from its 5-minute candles."""
from datetime import datetime, timedelta, timezone

from alerts.price_monitor import htf_triggered, tf_candle


def _bars():
    # 08:00-10:00 UTC, one 5-minute candle each; the 09:15 one wicks up to 1.1205
    t0 = datetime(2026, 10, 27, 8, 0, tzinfo=timezone.utc)
    out = []
    for i in range(24):
        t = t0 + timedelta(minutes=5 * i)
        h = 1.1205 if t.hour == 9 and t.minute == 15 else 1.1190
        out.append((t, 1.1185, h, 1.1178, 1.1182))
    return out


def test_the_1h_candle_is_built_from_all_its_5_minute_candles():
    now = datetime(2026, 10, 27, 10, 1, tzinfo=timezone.utc)   # just after the 09:00-10:00 candle closed
    o, h, l, c, prev = tf_candle(_bars(), "1h", now)
    assert (o, h, l, c) == (1.1185, 1.1205, 1.1178, 1.1182)
    assert prev == 1.1182                                       # 08:00-09:00 candle's close


def test_an_early_wick_in_the_hour_counts_as_a_rejection():
    now = datetime(2026, 10, 27, 10, 1, tzinfo=timezone.utc)
    o, h, l, c, prev = tf_candle(_bars(), "1h", now)
    assert htf_triggered("rejects", 1.1200, prev, h, l, c) == "from above"
    # the last 5-minute candle alone (09:55) never reached the level
    last = _bars()[-1]
    assert htf_triggered("rejects", 1.1200, None, last[2], last[3], last[4]) == ""


def test_no_candle_when_its_5_minute_candles_are_missing():
    now = datetime(2026, 10, 27, 14, 1, tzinfo=timezone.utc)
    assert tf_candle(_bars(), "1h", now) is None

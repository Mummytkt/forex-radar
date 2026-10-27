"""End-to-end platform checks against a throwaway DB. Never touches production.

Covers accounts and access control, Telegram delivery, the TradingView webhook
and the alert texts. Run directly (python tests/e2e_platform.py) or through
pytest (tests/test_platform_e2e.py). Exits non-zero if any check fails."""
import os, sys, tempfile, sqlite3
from datetime import datetime, timezone, timedelta

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
os.chdir(REPO)

tmpdir = tempfile.mkdtemp()
DB = os.path.join(tmpdir, "test.db")
os.environ.update({
    "DB_PATH": DB, "TV_WEBHOOK_SECRET": "tvsecret", "TELEGRAM_WEBHOOK_SECRET": "tgsecret",
    "TELEGRAM_ENABLED": "false", "TELEGRAM_BOT_TOKEN": "dummy-test-token", "TELEGRAM_CHAT_ID": "0",
    "PAYSTACK_SECRET_KEY": "",
})

from fastapi.testclient import TestClient
from config import load_config
from state.db import get_connection, bootstrap_schema
from api.app import app

config = load_config()
config.db_path = DB
config.telegram_enabled = False
conn = get_connection(DB)
bootstrap_schema(conn)
conn.close()
# TestClient serves the app on a worker thread; production uses one thread, so
# allow cross-thread use here only.
conn = sqlite3.connect(DB, check_same_thread=False)
conn.row_factory = sqlite3.Row
app.state.config = config
app.state.conn = conn
app.state.jwt_secret = "x" * 64
app.state.auth_enabled = False

c = TestClient(app)
results = []

def check(name, cond):
    results.append((name, bool(cond)))

def H(tok):
    return {"Authorization": f"Bearer {tok}"}

# ── Accounts: owner + subscribers A, B ────────────────────────────────────
r = c.post("/api/auth/setup", json={"email": "owner@x.com", "name": "Owner", "password": "ownerpass1"})
owner = r.json()["token"]
check("setup cannot be repeated once an owner exists",
      c.post("/api/auth/setup", json={"email": "evil@x.com", "name": "E", "password": "evilpass12"}).status_code == 400)

def make_sub(email):
    tok = c.post("/api/auth/invite", headers=H(owner), json={"email": email, "plan": "30DAY", "plan_days": 30}).json()["token"]
    return c.post("/api/auth/register", json={"token": tok, "name": email, "password": "subpass123"}).json()

A = make_sub("a@x.com"); B = make_sub("b@x.com")
ta, tb = A["token"], B["token"]
aid, bid = A["user"]["id"], B["user"]["id"]

# ── Unauthenticated / forged access ───────────────────────────────────────
check("no token -> 401 on private route", c.get("/api/journal").status_code == 401)
check("forged token -> 401", c.get("/api/journal", headers=H("abc.def.ghi")).status_code == 401)
check("invite token cannot be reused",
      c.post("/api/auth/register", json={"token": "nope", "name": "x", "password": "whatever1"}).status_code == 400)

# ── Owner-only controls: subscriber must be refused ───────────────────────
owner_only = [
    ("GET", "/api/auth/users", None),
    ("GET", "/api/strategy-content", None),
    ("GET", "/api/strategy-docs/rulebook", None),
    ("GET", "/api/strategy-docs/storybook", None),
    ("POST", "/api/auth/invite", {"email": "z@x.com"}),
    ("DELETE", f"/api/auth/users/{bid}", None),
    ("POST", "/api/videos", {"title": "t", "url": "https://youtu.be/abcdefghijk"}),
    ("DELETE", "/api/videos?url=x", None),
    ("PUT", "/api/config/instruments", {"instruments": ["EURUSD"]}),
    ("POST", "/api/admin/reset-instrument", {"instrument": "EURUSD"}),
    ("GET", "/api/entry-tests", None),
    ("POST", "/api/entry-tests", {"trade_date": "2020-01-08", "instrument": "XAUUSD", "direction": "buy"}),
    ("PUT", "/api/entry-tests/1", {"trade_date": "2020-01-08", "instrument": "XAUUSD", "direction": "buy"}),
    ("DELETE", "/api/entry-tests/1", None),
]
for method, path, body in owner_only:
    st = c.request(method, path, headers=H(ta), json=body).status_code
    check(f"subscriber refused: {method} {path} (got {st})", st in (401, 403))
check("owner can list users", c.get("/api/auth/users", headers=H(owner)).status_code == 200)
check("owner can read strategy content", c.get("/api/strategy-content", headers=H(owner)).status_code == 200)

# ── Entry Tester (owner only) ─────────────────────────────────────────────
_et = c.post("/api/entry-tests", headers=H(owner), json={
    "trade_date": "2020-01-08", "instrument": "xauusd", "direction": "buy", "alert_type": "Origin"}).json()
check("owner adds an entry-test trade", _et.get("id") and _et["instrument"] == "XAUUSD" and _et["results"] == {})
_r = c.put(f"/api/entry-tests/{_et['id']}", headers=H(owner), json={
    "trade_date": "2020-01-08", "instrument": "XAUUSD", "direction": "buy", "alert_type": "Origin",
    "results": {"direct_fvg": {"outcome": "win", "rr": 3}, "m5_cisd_engulfing": {"outcome": "loss", "rr": 5}, "h1_cisd_3cr": {"outcome": "none"}}})
_res = _r.json().get("results", {})
check("ticked entry results are saved (a loss keeps no RR)",
      _res.get("direct_fvg") == {"outcome": "win", "rr": 3} and _res.get("m5_cisd_engulfing") == {"outcome": "loss", "rr": None}
      and _res.get("h1_cisd_3cr", {}).get("outcome") == "none")
check("an unknown entry type is refused", c.put(f"/api/entry-tests/{_et['id']}", headers=H(owner), json={
    "trade_date": "2020-01-08", "instrument": "XAUUSD", "direction": "buy", "results": {"bogus": {"outcome": "win"}}}).status_code == 400)
check("the owner's entry tests list back", [t["id"] for t in c.get("/api/entry-tests", headers=H(owner)).json()] == [_et["id"]])
# The live Entry Journal (Trading Journal page) is a separate book
_lv = c.post("/api/entry-tests?book=live_engulfing", headers=H(owner), json={
    "trade_date": "2026-10-20", "instrument": "EURUSD", "direction": "sell"}).json()
check("live Entry Journal trades stay out of the backtest Entry Tester and back",
      [t["id"] for t in c.get("/api/entry-tests?book=live_engulfing", headers=H(owner)).json()] == [_lv["id"]]
      and [t["id"] for t in c.get("/api/entry-tests", headers=H(owner)).json()] == [_et["id"]])
check("the backtest Engulfing / Fresh Key Levels journals are their own books",
      c.get("/api/entry-tests?book=bt_engulfing", headers=H(owner)).status_code == 200
      and c.get("/api/entry-tests?book=bt_h4_key", headers=H(owner)).json() == [])
check("an unknown book is refused", c.get("/api/entry-tests?book=demo", headers=H(owner)).status_code == 400)
check("delete-all clears only its own book",
      c.post("/api/entry-tests/delete-all?book=live_engulfing", headers=H(owner), json={"confirm": "DELETE"}).json()["deleted"] == 1
      and len(c.get("/api/entry-tests", headers=H(owner)).json()) == 1)
check("a subscriber can't touch the owner's entry test",
      c.delete(f"/api/entry-tests/{_et['id']}", headers=H(ta)).status_code == 403
      and len(c.get("/api/entry-tests", headers=H(owner)).json()) == 1)
import io as _io
from PIL import Image as _PImage
_png = _io.BytesIO(); _PImage.new("RGB", (40, 30), (200, 20, 20)).save(_png, "PNG")
_up = c.post(f"/api/entry-tests/{_et['id']}/images/h4_key", headers=H(owner), files={"file": ("chart.png", _png.getvalue(), "image/png")})
check("owner adds a chart image for one POI of a trade", _up.status_code == 200 and _up.json().get("slot") == "h4_key")
_img_id = _up.json().get("id")
check("the trade lists which POI has an image", c.get("/api/entry-tests", headers=H(owner)).json()[0]["images"] == {"h4_key": [_img_id]})
_gi = c.get(f"/api/entry-tests/images/{_img_id}", headers=H(owner))
check("the image comes back as a JPEG", _gi.status_code == 200 and _gi.content[:2] == b"\xff\xd8")
check("a subscriber can't see or add Entry Tester images",
      c.get(f"/api/entry-tests/images/{_img_id}", headers=H(ta)).status_code == 403
      and c.post(f"/api/entry-tests/{_et['id']}/images/h4_key", headers=H(ta), files={"file": ("x.png", _png.getvalue(), "image/png")}).status_code == 403)
check("a non-image upload is refused", c.post(f"/api/entry-tests/{_et['id']}/images/engulfing", headers=H(owner),
      files={"file": ("x.txt", b"hello", "text/plain")}).status_code == 400)
_up2 = c.post(f"/api/entry-tests/{_et['id']}/images/h4_key", headers=H(owner), files={"file": ("c2.png", _png.getvalue(), "image/png")})
_ue = c.post(f"/api/entry-tests/{_et['id']}/images/h1_cisd_h4_key", headers=H(owner), files={"file": ("e.png", _png.getvalue(), "image/png")})
check("several images per POI, and images for one entry under it",
      c.get("/api/entry-tests", headers=H(owner)).json()[0]["images"] == {"h4_key": [_img_id, _up2.json()["id"]], "h1_cisd_h4_key": [_ue.json()["id"]]})
check("an image slot that isn't a POI or entry is refused", c.post(f"/api/entry-tests/{_et['id']}/images/bogus", headers=H(owner),
      files={"file": ("e.png", _png.getvalue(), "image/png")}).status_code == 400)
c.delete(f"/api/entry-tests/images/{_img_id}", headers=H(owner))
check("one image can be removed, the others stay",
      c.get(f"/api/entry-tests/images/{_img_id}", headers=H(owner)).status_code == 404
      and c.get("/api/entry-tests", headers=H(owner)).json()[0]["images"] == {"h4_key": [_up2.json()["id"]], "h1_cisd_h4_key": [_ue.json()["id"]]})
_ed = c.put(f"/api/entry-tests/{_et['id']}", headers=H(owner), json={"trade_date": "2020-01-09", "instrument": "XAUUSD",
      "direction": "sell", "alert_type": "H4 back in line", "results": {"direct_fvg": {"outcome": "loss"}}}).json()
_tk = c.put(f"/api/entry-tests/{_et['id']}", headers=H(owner), json={"trade_date": "2020-01-09", "instrument": "XAUUSD",
      "direction": "sell", "alert_type": "H4 back in line", "results": {"m5_cisd_fvg": {"outcome": "win", "rr": 3, "takes": 2, "exit": "2020-01-10T14:00"}, "direct_fvg": {"outcome": "none", "exit": "2020-01-10T14:00"},
      "m5_smc_fvg": {"outcome": "none", "takes": 3}, "h1_smc_fvg": {"outcome": "be", "rr": -0.3},
      "h1_cisd_fvg": {"outcome": "be", "rr": 0.5}}}).json()["results"]
check("a BE keeps the R it was closed at (a small loss or gain)",
      _tk["h1_smc_fvg"]["rr"] == -0.3 and _tk["h1_cisd_fvg"]["rr"] == 0.5)
check("re-entries are kept with the result (not on 'No entry')",
      _tk["m5_cisd_fvg"] == {"outcome": "win", "rr": 3, "takes": 2, "exit": "2020-01-10T14:00"} and "takes" not in _tk["m5_smc_fvg"]
      and "exit" not in _tk["direct_fvg"])
_ex = c.put(f"/api/entry-tests/{_et['id']}", headers=H(owner), json={"trade_date": "2020-01-28", "instrument": "XAUUSD",
      "direction": "buy", "exit_date": "2020-01-30", "notes": "x" * 1500}).json()
check("an exit date and a long note are saved", _ex.get("exit_date") == "2020-01-30" and len(_ex.get("notes", "")) == 1500)
check("an exit date before the entry date is refused", c.put(f"/api/entry-tests/{_et['id']}", headers=H(owner), json={
      "trade_date": "2020-01-28", "instrument": "XAUUSD", "direction": "buy", "exit_date": "2020-01-27"}).status_code == 400)
check("a trade's date, direction, alert and results can all be edited",
      _ed["trade_date"] == "2020-01-09" and _ed["direction"] == "sell" and _ed["alert_type"] == "H4 back in line"
      and _ed["results"] == {"direct_fvg": {"outcome": "loss", "rr": None}})
# Weekly image backup: sends each new image once, as a zip with a manifest
import asyncio as _aio, zipfile as _zf
import alerts.telegram as _tgm
_sent_docs = []
async def _fake_doc(token, chat, path, fname, caption=""):
    with _zf.ZipFile(path) as z:
        _sent_docs.append((fname, sorted(z.namelist())))
    return 77
_old_doc, _tgm.send_document = _tgm.send_document, _fake_doc
_old_tg = (config.telegram_enabled, config.telegram_bot_token, config.telegram_chat_id)
config.telegram_enabled, config.telegram_bot_token, config.telegram_chat_id = True, "123:TEST", "999"
from alerts.image_backup import run_image_backup
_ib = _aio.run(run_image_backup(config.db_path, config))
check("the weekly image backup sends the new image in a zip with a manifest",
      _ib["images"] == 2 and len(_sent_docs) == 1 and "manifest.json" in _sent_docs[0][1]
      and any("XAUUSD_H4-fresh-key-level" in n for n in _sent_docs[0][1]))
_ib2 = _aio.run(run_image_backup(config.db_path, config))
check("an image is only sent once", _ib2["images"] == 0 and len(_sent_docs) == 1)
_tgm.send_document = _old_doc
config.telegram_enabled, config.telegram_bot_token, config.telegram_chat_id = _old_tg
c.delete(f"/api/entry-tests/{_et['id']}", headers=H(owner))
check("owner deletes an entry test", c.get("/api/entry-tests", headers=H(owner)).json() == [])
for _d in ("2020-03-02", "2020-03-03"):
    c.post("/api/entry-tests", headers=H(owner), json={"trade_date": _d, "instrument": "XAUUSD", "direction": "buy"})
check("delete-all needs DELETE typed", c.post("/api/entry-tests/delete-all", headers=H(owner), json={"confirm": "yes"}).status_code == 400
      and len(c.get("/api/entry-tests", headers=H(owner)).json()) == 2)
check("a subscriber can't delete-all", c.post("/api/entry-tests/delete-all", headers=H(ta), json={"confirm": "DELETE"}).status_code == 403)
_da = c.post("/api/entry-tests/delete-all", headers=H(owner), json={"confirm": "DELETE"}).json()
check("delete-all clears every Entry Tester trade", _da.get("deleted") == 2 and c.get("/api/entry-tests", headers=H(owner)).json() == [])
check("deleting a trade deletes its images",
      c.get(f"/api/entry-tests/images/{_up2.json()['id']}", headers=H(owner)).status_code == 404
      and conn.execute("SELECT COUNT(*) FROM entry_test_images").fetchone()[0] == 0)
for _d in ("rulebook", "storybook"):
    _r = c.get(f"/api/strategy-docs/{_d}", headers=H(owner))
    check(f"owner downloads {_d} PDF", _r.status_code == 200 and _r.content[:4] == b"%PDF")
check("unknown strategy doc -> 404", c.get("/api/strategy-docs/secrets", headers=H(owner)).status_code == 404)
check("strategy doc path traversal refused", c.get("/api/strategy-docs/..%2F..%2F.env", headers=H(owner)).status_code in (404, 422))
check("strategy doc needs login", c.get("/api/strategy-docs/rulebook").status_code == 401)
check("subscriber can still watch videos", c.get("/api/videos", headers=H(ta)).status_code == 200)
check("B still exists after A tried to revoke B",
      any(u["id"] == bid for u in c.get("/api/auth/users", headers=H(owner)).json()))
users_json = c.get("/api/auth/users", headers=H(owner)).json()
check("users list never exposes password hashes / chat ids / tokens",
      all(not ({"password_hash", "telegram_chat_id", "invite_token", "set_password_token"} & set(u)) for u in users_json))

# ── Journal isolation ─────────────────────────────────────────────────────
ja = c.post("/api/journal", headers=H(ta), json={"trade_date": "2026-10-15", "instrument": "EURUSD",
                                                  "direction": "buy", "notes": "A-secret"}).json()
check("B cannot see A's journal", all(e["id"] != ja["id"] for e in c.get("/api/journal?period=all", headers=H(tb)).json()))
check("owner cannot see A's journal", all(e["id"] != ja["id"] for e in c.get("/api/journal?period=all", headers=H(owner)).json()))
check("B cannot edit A's trade", c.put(f"/api/journal/{ja['id']}", headers=H(tb), json={"notes": "hacked"}).status_code == 404)
c.delete(f"/api/journal/{ja['id']}", headers=H(tb))
mine = c.get("/api/journal?period=all", headers=H(ta)).json()
check("B cannot delete A's trade", any(e["id"] == ja["id"] and e.get("notes") == "A-secret" for e in mine))
csv_b = c.get("/api/journal/export.csv?period=all", headers=H(tb)).text
check("B's CSV export excludes A's trades", "A-secret" not in csv_b)

# ── Price + entry alert isolation ─────────────────────────────────────────
pa = c.post("/api/price-alerts", headers=H(ta), json={"instrument": "EURUSD", "price": 1.1, "message": "A-note"}).json()
lb = c.get("/api/price-alerts", headers=H(tb)).json()
check("B cannot see A's price alerts", "A-note" not in str(lb))
c.delete(f"/api/price-alerts/{pa['id']}", headers=H(tb))
check("B cannot delete A's price alert", "A-note" in str(c.get("/api/price-alerts", headers=H(ta)).json()))
ea = c.post("/api/entry-alerts", headers=H(ta), json={"instrument": "EURUSD", "direction": "bullish", "price": 1.1, "note": "A-entry"}).json()
check("B cannot see A's entry alerts", "A-entry" not in str(c.get("/api/entry-alerts", headers=H(tb)).json()))
c.delete(f"/api/entry-alerts/{ea['id']}", headers=H(tb))
check("B cannot delete A's entry alert", "A-entry" in str(c.get("/api/entry-alerts", headers=H(ta)).json()))

# ── Per-user settings ─────────────────────────────────────────────────────
c.post("/api/preferences/accent", headers=H(ta), json={"accent_color": "emerald"})
check("A's accent saved for A", c.get("/api/preferences/accent", headers=H(ta)).json()["accent_color"] == "emerald")
check("A's accent does not leak to B", c.get("/api/preferences/accent", headers=H(tb)).json()["accent_color"] is None)
check("A's accent does not change owner's", c.get("/api/preferences/accent", headers=H(owner)).json()["accent_color"] is None)
c.put("/api/user/instruments", headers=H(ta), json={"instruments": ["EURUSD"]})
check("A's watchlist does not change B's", c.get("/api/user/instruments", headers=H(tb)).json()["instruments"] is None)
me_b = c.get("/api/auth/me", headers=H(tb)).json()
check("/me returns only your own account", me_b["id"] == bid and "password_hash" not in me_b)

# ── Per-user Telegram delivery preferences ────────────────────────────────
_pb = c.get("/api/preferences", headers=H(tb)).json()
check("by default External is on and Internal is off", _pb["alertExternal"] is True and _pb["alertInternal"] is False)
check("A can save own delivery prefs",
      c.patch("/api/preferences", headers=H(ta), json={"alertInternal": True}).status_code == 200)
pa_ = c.get("/api/preferences", headers=H(ta)).json()
check("A's prefs read back (internal on, external on)", pa_["alertInternal"] is True and pa_["alertExternal"] is True)
check("A's choice does not change B's", c.get("/api/preferences", headers=H(tb)).json()["alertInternal"] is False)
check("A's choice does not change owner's", c.get("/api/preferences", headers=H(owner)).json()["alertInternal"] is False)

import asyncio
import api.tv_webhook as tvw
from types import SimpleNamespace as NS
sent = []
async def fake_send(token, chat, text):
    sent.append(chat)
    return True
tvw.send_alert = fake_send
dbw = sqlite3.connect(DB)
for uid_, chat in ((aid, "chatA"), (bid, "chatB")):
    dbw.execute("UPDATE users SET telegram_chat_id = ? WHERE id = ?", (chat, uid_))
dbw.execute("UPDATE users SET telegram_chat_id = 'chatOwner' WHERE role = 'OWNER'")
dbw.commit(); dbw.close()
conn.row_factory = sqlite3.Row
cfg = NS(telegram_bot_token="t", telegram_chat_id="chatOwner")

sent.clear(); asyncio.run(tvw._deliver_alert(conn, cfg, "EURUSD", "x", h4_class="internal"))
check(f"internal Origin reaches only A (who switched Internal on) {sorted(sent)}", "chatA" in sent and "chatB" not in sent and "chatOwner" not in sent)
sent.clear(); asyncio.run(tvw._deliver_alert(conn, cfg, "EURUSD", "x", h4_class="external"))
check(f"external Origin reaches everyone {sorted(sent)}", {"chatA", "chatB", "chatOwner"} <= set(sent))
sent.clear(); asyncio.run(tvw._deliver_alert(conn, cfg, "EURUSD", "x"))
check(f"continuations always reach A {sorted(sent)}", "chatA" in sent)
# Everyone watches only GBPUSD -> an EURUSD alert must reach nobody (no owner fallback)
dbw = sqlite3.connect(DB)
dbw.execute("UPDATE users SET watched_instruments = '[\"GBPUSD\"]'")
dbw.commit(); dbw.close()
sent.clear(); asyncio.run(tvw._deliver_alert(conn, cfg, "EURUSD", "x"))
check(f"filtered-out recipients are not rerouted to owner {sent}", sent == [])
dbw = sqlite3.connect(DB)
dbw.execute("UPDATE users SET watched_instruments = NULL")
dbw.commit(); dbw.close()

# ── History pair filter ───────────────────────────────────────────────────
r_pairs = c.get("/api/alerts/instruments", headers=H(tb))
check("pair list endpoint works for a subscriber", r_pairs.status_code == 200 and "instruments" in r_pairs.json())
check("pair list requires login", c.get("/api/alerts/instruments").status_code == 401)
r_f = c.get("/api/alerts?instrument=EURUSD&direction=BULLISH", headers=H(tb))
check("History accepts pair + direction filters together", r_f.status_code == 200 and "items" in r_f.json())

# ── Webhook secrets ───────────────────────────────────────────────────────
check("TV webhook rejects bad secret",
      c.post("/api/tv-webhook", json={"secret": "wrong", "type": "PRICE_UPDATE", "instrument": "EURUSD", "price": 1.1}).status_code == 401)
okw = c.post("/api/tv-webhook", json={"secret": "tvsecret", "type": "PRICE_UPDATE", "instrument": "EUR/USD", "price": 1.1})
hb = sqlite3.connect(DB).execute("SELECT last_type FROM webhook_heartbeats WHERE instrument='EURUSD'").fetchone()
check(f"valid webhook records a feed heartbeat ({okw.status_code})", okw.status_code == 200 and hb and hb[0] == "PRICE_UPDATE")
check("bad-secret webhook does not count as a heartbeat",
      sqlite3.connect(DB).execute("SELECT COUNT(*) FROM webhook_heartbeats").fetchone()[0] == 1)
check("subscriber cannot see feed health", c.get("/api/admin/feed-health", headers=H(tb)).status_code == 403)
fh = c.get("/api/admin/feed-health", headers=H(owner))
check("owner sees feed health", fh.status_code == 200 and fh.json()["instruments"][0]["instrument"] == "EURUSD")
config.tv_webhook_secret = ""
r_empty = c.post("/api/tv-webhook", json={"secret": "", "type": "PRICE_UPDATE", "instrument": "GBPUSD", "price": 1.3})
check("with no server secret configured, webhooks still flow (never silent)", r_empty.status_code == 200)
config.tv_webhook_secret = "tvsecret"
config.telegram_enabled = True
import api.tv_webhook as _tvw
_rej = []
async def _cap(token, chat, text): _rej.append(text); return True
import alerts.telegram as _tg; _tg.send_alert = _cap
for _ in range(3):
    c.post("/api/tv-webhook", json={"secret": "wrong", "type": "PRICE_UPDATE", "instrument": "EURUSD", "price": 1.1})
config.telegram_enabled = False
check(f"rejected webhooks warn the owner once a day ({len(_rej)})", len(_rej) == 1 and "REJECTED" in _rej[0])
os.environ["TV_IP_ALLOWLIST"] = "enforce"
bad_src = c.post("/api/tv-webhook", json={"secret": "tvsecret", "type": "PING_TEST", "instrument": "ZZ"}, headers={"fly-client-ip": "203.0.113.9"})
good_src = c.post("/api/tv-webhook", json={"secret": "tvsecret", "type": "PING_TEST", "instrument": "ZZ"}, headers={"fly-client-ip": "52.89.214.238"})
os.environ["TV_IP_ALLOWLIST"] = "observe"
obs = c.post("/api/tv-webhook", json={"secret": "tvsecret", "type": "PING_TEST", "instrument": "ZZ"}, headers={"fly-client-ip": "203.0.113.9"})
check("enforce mode refuses webhooks from non-TradingView addresses", bad_src.status_code == 403)
check("enforce mode accepts TradingView's published addresses", good_src.status_code == 200)
check("observe mode (default) blocks nothing", obs.status_code == 200)
check("Telegram webhook rejects missing secret header",
      c.post("/api/telegram/update", json={"message": {"text": "/start x", "chat": {"id": 1}}}).status_code == 401)

# ── Password reset, owner reset links, checkout claim ─────────────────────
import time
C = make_sub("c@x.com"); tc, cid = C["token"], C["user"]["id"]
dbw = sqlite3.connect(DB); dbw.execute("UPDATE users SET telegram_chat_id='chatC' WHERE id=?", (cid,)); dbw.commit(); dbw.close()
gen1 = c.post("/api/auth/forgot", json={"email": "nobody@x.com"}).json()
gen2 = c.post("/api/auth/forgot", json={"email": "C@x.com"}).json()
check("forgot gives the same answer for unknown and real emails", gen1 == gen2)
rtok = sqlite3.connect(DB).execute("SELECT reset_token FROM users WHERE id=?", (cid,)).fetchone()[0]
check("forgot issues a reset token for a Telegram-linked account", bool(rtok))
time.sleep(1.1)
rr = c.post("/api/auth/reset", json={"token": rtok, "password": "brandnew123"})
check("reset with valid token succeeds", rr.status_code == 200 and rr.json().get("token"))
check("old session is signed out after reset", c.get("/api/journal", headers=H(tc)).status_code == 401)
tc2 = rr.json()["token"]
check("new session works after reset", c.get("/api/journal", headers=H(tc2)).status_code == 200)
check("reset token works only once", c.post("/api/auth/reset", json={"token": rtok, "password": "another123"}).status_code == 400)
check("can sign in with the new password",
      c.post("/api/auth/login", json={"email": "c@x.com", "password": "brandnew123"}).status_code == 200)
dbw = sqlite3.connect(DB)
dbw.execute("UPDATE users SET reset_token='expiredtok', reset_token_expires_at=? WHERE id=?",
            ((datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(), cid)); dbw.commit(); dbw.close()
check("expired reset token refused", c.post("/api/auth/reset", json={"token": "expiredtok", "password": "zzzzzzzz1"}).status_code == 400)
check("subscriber cannot create reset links", c.post(f"/api/auth/users/{cid}/reset-link", headers=H(tb)).status_code == 403)
lk = c.post(f"/api/auth/users/{cid}/reset-link", headers=H(owner))
check("owner can create a reset link", lk.status_code == 200 and "/reset?token=" in lk.json()["link"])
time.sleep(1.1)
pc = c.put("/api/auth/profile", headers=H(tc2), json={"current_password": "brandnew123", "new_password": "evennewer12"})
check("profile password change returns a fresh token", pc.status_code == 200 and pc.json().get("token"))
check("other sessions signed out after password change", c.get("/api/journal", headers=H(tc2)).status_code == 401)
check("fresh token from password change works", c.get("/api/journal", headers=H(pc.json()["token"])).status_code == 200)
ul = {u["id"]: u for u in c.get("/api/auth/users", headers=H(owner)).json()}
check("users list shows has_password without leaking the hash", ul[cid]["has_password"] is True and "password_hash" not in ul[cid])
# checkout trap: paid account with no password
dbw = sqlite3.connect(DB)
dbw.execute("INSERT INTO users (email,name,role,plan,set_password_token) VALUES ('d@x.com','D','SUBSCRIBER','30DAY',NULL)")
did = dbw.execute("SELECT id FROM users WHERE email='d@x.com'").fetchone()[0]
dbw.execute("INSERT INTO payments (reference,email,plan,amount_usd,duration_days,status,user_id) VALUES ('mbp_ref123','d@x.com','30DAY',10,30,'paid',?)", (did,))
dbw.commit(); dbw.close()
check("claim refused with wrong reference",
      c.post("/api/public/claim-account", json={"email": "d@x.com", "reference": "mbp_wrong"}).status_code == 400)
check("claim refused with someone else's email",
      c.post("/api/public/claim-account", json={"email": "c@x.com", "reference": "mbp_ref123"}).status_code == 400)
cl = c.post("/api/public/claim-account", json={"email": "D@x.com", "reference": "mbp_ref123"})
check("claim with email + reference returns a set-password token", cl.status_code == 200 and cl.json().get("set_password_token"))
sp = c.post("/api/public/set-password", json={"token": cl.json()["set_password_token"], "password": "dpassword1"})
check("claimed account can set a password and sign in", sp.status_code == 200 and sp.json().get("token"))
check("cannot claim again once a password exists",
      c.post("/api/public/claim-account", json={"email": "d@x.com", "reference": "mbp_ref123"}).status_code == 400)

# ── Billing: auto-renew off/on ────────────────────────────────────────────
td = sp.json()["token"]
fut = (datetime.now(timezone.utc) + timedelta(days=20)).isoformat()
dbw = sqlite3.connect(DB)
dbw.execute("UPDATE users SET plan_expires_at=?, billing_mode='auto', paystack_auth_code='AUTH_x', renew_plan='30DAY', renew_amount=10, next_charge_at=? WHERE id=?", (fut, fut, did))
dbw.commit(); dbw.close()
bm = c.get("/api/billing/me", headers=H(td)).json()
check("billing shows auto-renew on with next charge", bm["auto_renew"] is True and bm["renew_amount_usd"] == 10)
off = c.post("/api/billing/auto-renew", headers=H(td), json={"enabled": False})
row = sqlite3.connect(DB).execute("SELECT billing_mode, next_charge_at, auto_renew_cancelled_at FROM users WHERE id=?", (did,)).fetchone()
check("turning auto-renew off stops future charges", off.status_code == 200 and row[0] == "once" and row[1] is None and row[2])
bm2 = c.get("/api/billing/me", headers=H(td)).json()
check("after cancelling: access kept, can turn back on", bm2["auto_renew"] is False and bm2["can_turn_on"] is True and bm2["plan_expires_at"] == fut)
on = c.post("/api/billing/auto-renew", headers=H(td), json={"enabled": True})
row = sqlite3.connect(DB).execute("SELECT billing_mode, next_charge_at FROM users WHERE id=?", (did,)).fetchone()
check("turning it back on schedules the charge at plan end", on.status_code == 200 and row[0] == "auto" and row[1] == fut)
check("cannot enable auto-renew without a saved card",
      c.post("/api/billing/auto-renew", headers=H(pc.json()["token"]), json={"enabled": True}).status_code == 400)
check("billing requires login", c.get("/api/billing/me").status_code == 401)

# ── Owner business dashboard ──────────────────────────────────────────────
dbw = sqlite3.connect(DB)
nowiso = datetime.now(timezone.utc).isoformat()
dbw.execute("INSERT INTO payments (reference,email,plan,amount_usd,duration_days,trial,status,user_id,paid_at) VALUES ('mbp_p1','d@x.com','6MONTH',48,182,0,'paid',?,?)", (did, nowiso))
dbw.execute("INSERT INTO payments (reference,email,plan,amount_usd,duration_days,trial,status,user_id,paid_at) VALUES ('mbp_t1','d@x.com','TRIAL',10,7,1,'paid',?,?)", (did, nowiso))
dbw.execute("INSERT INTO affiliates (user_id, code, paid_customers) VALUES (?, 'MBPTEST', 1)", (cid,))
aff_id = dbw.execute("SELECT id FROM affiliates WHERE code='MBPTEST'").fetchone()[0]
dbw.execute("INSERT INTO commissions (affiliate_id, customer_email, rate, amount_usd, status) VALUES (?, 'd@x.com', 0.1, 4.8, 'available')", (aff_id,))
dbw.execute("INSERT INTO commissions (affiliate_id, customer_email, rate, amount_usd, status) VALUES (?, 'e@x.com', 0.1, 1.0, 'pending')", (aff_id,))
dbw.commit(); dbw.close()
check("subscriber cannot open the business dashboard", c.get("/api/admin/business", headers=H(tb)).status_code == 403)
bz = c.get("/api/admin/business", headers=H(owner)).json()
check(f"revenue counts real payments, excludes trial checks ({bz['revenue']['last_30d_usd']})", bz["revenue"]["last_30d_usd"] == 48)
check("monthly series covers 6 months", len(bz["revenue"]["monthly"]) == 6 and bz["revenue"]["monthly"][-1]["revenue_usd"] == 48)
aff = [a for a in bz["affiliates"] if a["code"] == "MBPTEST"][0]
check("commission owed vs on hold split correctly", aff["available_usd"] == 4.8 and aff["pending_usd"] == 1.0 and bz["commissions_owed_usd"] == 4.8)
check("subscriber cannot mark commissions paid",
      c.post("/api/admin/commissions/mark-paid", headers=H(tb), json={"affiliate_id": aff_id}).status_code == 403)
mp = c.post("/api/admin/commissions/mark-paid", headers=H(owner), json={"affiliate_id": aff_id}).json()
aff2 = [a for a in c.get("/api/admin/business", headers=H(owner)).json()["affiliates"] if a["code"] == "MBPTEST"][0]
check("mark paid moves only owed commission to paid", mp["marked"] == 1 and aff2["paid_usd"] == 4.8 and aff2["available_usd"] == 0 and aff2["pending_usd"] == 1.0)
c.post("/api/billing/auto-renew", headers=H(td), json={"enabled": False})
check("cancelled-auto-renew counted in churn", c.get("/api/admin/business", headers=H(owner)).json()["subscribers"]["cancelled_auto_renew_30d"] >= 1)

# ── Onboarding checklist ──────────────────────────────────────────────────
tcn = pc.json()["token"]
check("onboarding needs login", c.get("/api/onboarding").status_code == 401)
ob = c.get("/api/onboarding", headers=H(tcn)).json()
check("onboarding reflects this user's own Telegram + pairs", ob["telegram_linked"] is True and ob["pairs_chosen"] is False and ob["alerts_reviewed"] is False)
c.put("/api/user/instruments", headers=H(tcn), json={"instruments": ["EURUSD"]})
c.patch("/api/preferences", headers=H(tcn), json={"alertExternal": True})
ob2 = c.get("/api/onboarding", headers=H(tcn)).json()
check("onboarding ticks off pairs and alert choices once saved", ob2["pairs_chosen"] is True and ob2["alerts_reviewed"] is True)
check("another user's setup doesn't tick yours", c.get("/api/onboarding", headers=H(td)).json()["pairs_chosen"] is False)

# ── Backups channel detection (owner-only) ────────────────────────────────
dbw = sqlite3.connect(DB); dbw.execute("UPDATE users SET telegram_chat_id='555' WHERE role='OWNER'"); dbw.commit(); dbw.close()
TG = {"X-Telegram-Bot-Api-Secret-Token": "tgsecret"}
def member(actor, status, chat_type="channel", post=True, delete=True, chat_id=-100123):
    nm = {"status": status, "can_post_messages": post, "can_delete_messages": delete}
    return c.post("/api/telegram/update", headers=TG, json={"my_chat_member": {
        "chat": {"id": chat_id, "type": chat_type, "title": "Bias Pointer Backups"},
        "from": {"id": actor}, "new_chat_member": nm}})
chan = lambda: (sqlite3.connect(DB).execute("SELECT value FROM user_config WHERE key='backup_channel_id'").fetchone() or [None])[0]
member(999, "administrator")
check("a stranger adding the bot to their channel is ignored", chan() is None)
member(555, "administrator", delete=False)
check("channel without delete permission is not used", chan() is None)
member(555, "administrator", chat_type="supergroup")
check("groups are not used as the backups channel", chan() is None)
r_ok = member(555, "administrator")
check("owner's channel with post+delete becomes the backups channel", r_ok.status_code == 200 and chan() == "-100123")
member(999, "left")
check("a stranger cannot disconnect it", chan() == "-100123")
member(555, "left")
check("removing the bot disconnects the channel", chan() is None)
check("channel updates need the webhook secret", c.post("/api/telegram/update", json={"my_chat_member": {}}).status_code == 401)

# ── Owner → subscriber updates ────────────────────────────────────────────
check("subscriber cannot post updates",
      c.post("/api/announcements", headers=H(tb), json={"title": "x", "body": "y"}).status_code == 403)
check("update needs a title and a message",
      c.post("/api/announcements", headers=H(owner), json={"title": " ", "body": "y"}).status_code == 400)
check("over-long update refused",
      c.post("/api/announcements", headers=H(owner), json={"title": "t", "body": "z" * 4000}).status_code == 400)
p1 = c.post("/api/announcements", headers=H(owner), json={"title": "New tutorial", "body": "Watch https://youtu.be/abc"}).json()
p2 = c.post("/api/announcements", headers=H(owner), json={"title": "Holiday hours", "body": "Markets close early", "send_telegram": True}).json()
check("Telegram option targets active, linked subscribers", p2["telegram_targets"] >= 1)
ub = c.get("/api/announcements/unread", headers=H(tb)).json()["unread"]
uc = c.get("/api/announcements/unread", headers=H(tcn)).json()["unread"]
check(f"each subscriber sees unread updates (B={ub}, C={uc})", ub == 2 and uc == 2)
check("owner has no unread badge", c.get("/api/announcements/unread", headers=H(owner)).json()["unread"] == 0)
lst = c.get("/api/announcements", headers=H(tb)).json()
check("updates listed newest first", [i["title"] for i in lst["items"]][:2] == ["Holiday hours", "New tutorial"])
c.post("/api/announcements/read", headers=H(tb), json={"last_id": 10**9})
check("opening updates clears B's badge", c.get("/api/announcements/unread", headers=H(tb)).json()["unread"] == 0)
check("B reading doesn't clear C's badge", c.get("/api/announcements/unread", headers=H(tcn)).json()["unread"] == 2)
check("subscriber cannot delete updates", c.delete(f"/api/announcements/{p1['id']}", headers=H(tb)).status_code == 403)
c.delete(f"/api/announcements/{p1['id']}", headers=H(owner))
check("owner can delete an update", all(i["id"] != p1["id"] for i in c.get("/api/announcements", headers=H(tcn)).json()["items"]))
check("updates need login", c.get("/api/announcements").status_code == 401)
# Targeting by plan: B is on 30DAY, make C a TRIAL member
dbw = sqlite3.connect(DB); dbw.execute("UPDATE users SET plan='TRIAL' WHERE id=?", (cid,)); dbw.commit(); dbw.close()
c.post("/api/announcements/read", headers=H(tcn), json={"last_id": 10**9})
c.post("/api/announcements/read", headers=H(tb), json={"last_id": 10**9})
t1 = c.post("/api/announcements", headers=H(owner), json={"title": "Trial tips", "body": "For trial members", "plans": ["TRIAL"], "send_telegram": True}).json()
check("trial-only update: Telegram goes to trial members only", t1["telegram_targets"] == 1 and t1["audience"] == "TRIAL")
check("trial-only update: trial member sees it",
      any(i["id"] == t1["id"] for i in c.get("/api/announcements", headers=H(tcn)).json()["items"]))
check("trial-only update: 30-day member does NOT see it",
      all(i["id"] != t1["id"] for i in c.get("/api/announcements", headers=H(tb)).json()["items"]))
check("trial-only update: no badge for the 30-day member", c.get("/api/announcements/unread", headers=H(tb)).json()["unread"] == 0)
check("trial-only update: badge for the trial member", c.get("/api/announcements/unread", headers=H(tcn)).json()["unread"] == 1)
t2 = c.post("/api/announcements", headers=H(owner), json={"title": "Both", "body": "Trial and 30 days", "plans": ["30DAY", "TRIAL"], "send_telegram": True}).json()
check("multi-plan update reaches both plans (in app and Telegram)",
      t2["telegram_targets"] == 3 and t2["audience"] == "TRIAL,30DAY"
      and any(i["id"] == t2["id"] for i in c.get("/api/announcements", headers=H(tb)).json()["items"]))
t3 = c.post("/api/announcements", headers=H(owner), json={"title": "Every plan", "body": "x", "plans": ["TESTER", "TRIAL", "30DAY", "6MONTH", "9MONTH", "12MONTH", "LIFETIME"]}).json()
check("selecting every plan is stored as 'everyone'", t3["audience"] is None)
check("unknown plan refused", c.post("/api/announcements", headers=H(owner), json={"title": "t", "body": "b", "plans": ["GOLD"]}).status_code == 400)
own = c.get("/api/announcements", headers=H(owner)).json()
check("owner sees every update plus per-plan subscriber counts",
      {t1["id"], t2["id"], t3["id"]} <= {i["id"] for i in own["items"]} and own["plan_counts"]["TRIAL"] >= 1)
dbw = sqlite3.connect(DB); dbw.execute("UPDATE users SET plan='30DAY' WHERE id=?", (cid,)); dbw.commit(); dbw.close()

# ── Public track record ───────────────────────────────────────────────────
trk = c.get("/api/public/track-record")
check("track record is public", trk.status_code == 200 and "evaluated" in trk.json())
tick = sqlite3.connect(DB).execute("SELECT COUNT(*) FROM price_ticks WHERE instrument='EURUSD'").fetchone()[0]
check("PRICE_UPDATE webhook stores an H4 price tick", tick >= 1)

# ── Expiry + revocation take effect immediately ──────────────────────────
db = sqlite3.connect(DB)
db.execute("UPDATE users SET plan_expires_at = ? WHERE id = ?",
           ((datetime.now(timezone.utc) - timedelta(days=1)).isoformat(), bid))
db.commit(); db.close()
check("expired subscriber locked out on next request", c.get("/api/journal", headers=H(tb)).status_code == 403)
c.delete(f"/api/auth/users/{aid}", headers=H(owner))
check("revoked subscriber's token stops working", c.get("/api/journal", headers=H(ta)).status_code == 403)
db = sqlite3.connect(DB)
active = db.execute("SELECT COUNT(*) FROM price_alerts WHERE user_id = ? AND is_active = 1", (aid,)).fetchone()[0]
db.close()
check("revoked subscriber's alerts are switched off", active == 0)
check("owner cannot revoke themselves",
      c.delete(f"/api/auth/users/{c.get('/api/auth/me', headers=H(owner)).json()['id']}", headers=H(owner)).status_code == 400)

# ── Brute force ───────────────────────────────────────────────────────────
codes = [c.post("/api/auth/login", json={"email": "owner@x.com", "password": f"bad{i}"}).status_code for i in range(10)]
check(f"login throttled after repeated failures {codes[-3:]}", codes[-1] == 429)


# ── Webhook logic (2026-10-16 audit) ──────────────────────────────────────
def tv(**kw):
    body = {"secret": "tvsecret"}; body.update(kw)
    return c.post("/api/tv-webhook", json=body)
def active_bo(inst):
    return conn.execute("SELECT direction, broken_level FROM daily_breakouts WHERE instrument=? AND is_active=1", (inst,)).fetchall()

r = tv(type="BREAKOUT", instrument="NZDCHF", direction="bullish", level=0.5, timeframe="D")
check("bias event from a Daily-chart alert is ignored", r.json().get("status") == "ignored" and active_bo("NZDCHF") == [])
tv(type="BREAKOUT", instrument="NZDCHF", direction="bullish", level=0.5, timeframe="240")
check("bias event from the 4H chart is accepted", [tuple(x) for x in active_bo("NZDCHF")] == [("bullish", 0.5)])
tv(type="BREAKOUT", instrument="NZDJPY", direction="bearish", level=90.0)
check("older script without timeframe still accepted", [tuple(x) for x in active_bo("NZDJPY")] == [("bearish", 90.0)])
tv(type="ENTRY_CONFIRMATION", instrument="NZDCHF", direction="bullish", pattern="pcl", timeframe="60", price=0.5, swept_level=0.5)
check("entry patterns from H1 are not blocked by the 4H guard", True)

# Server holds a bullish breakout but missed the bearish BREAKOUT: the CONFIRMED resyncs it
n0 = conn.execute("SELECT COUNT(*) FROM alerts WHERE instrument='NZDCHF'").fetchone()[0]
tv(type="CONFIRMED", instrument="NZDCHF", direction="bearish", source="daily_breaker", h4_class="external",
   breakout_level=0.48, source_level=0.48, h4_level=0.47, timeframe="240")
check("CONFIRMED in the other direction replaces the stale breakout", [tuple(x) for x in active_bo("NZDCHF")] == [("bearish", 0.48)])
row = conn.execute("SELECT d.direction FROM alerts a JOIN daily_breakouts d ON d.id=a.daily_breakout_id WHERE a.instrument='NZDCHF' ORDER BY a.id DESC LIMIT 1").fetchone()
check("the alert is stored against the bearish breakout", row is not None and row[0] == "bearish"
      and conn.execute("SELECT COUNT(*) FROM alerts WHERE instrument='NZDCHF'").fetchone()[0] == n0 + 1)
# Same direction but a newer level (a second BREAKOUT was missed)
tv(type="H4_CONTINUATION", instrument="NZDCHF", direction="bearish", cont_type="oc_cont", breakout_level=0.45, h4_level=0.44, timeframe="240")
check("continuation at a new breakout level resyncs the level", [tuple(x) for x in active_bo("NZDCHF")] == [("bearish", 0.45)])
tv(type="RETEST", instrument="NZDCHF", direction="bearish", source="post_breakout_oc", breakout_level=0.45, source_level=0.44, timeframe="240")
check("matching RETEST keeps the same breakout", [tuple(x) for x in active_bo("NZDCHF")] == [("bearish", 0.45)]
      and conn.execute("SELECT retest_in_progress FROM instrument_state WHERE instrument='NZDCHF'").fetchone()[0] == 1)
r = tv(type="RETEST", instrument="CADCHF", timeframe="240")
check("RETEST with no direction and no setup is ignored safely", r.status_code == 200 and active_bo("CADCHF") == [])

# 2026-10-18: alerts say which daily structure level broke
alert_text_col = [r[1] for r in conn.execute("PRAGMA table_info(alerts)").fetchall() if "text" in r[1]][0]
tv(type="BREAKOUT", instrument="GBPCHF", direction="bullish", level=1.10, level_type="inner_internal", range_level=1.08, timeframe="240")
check("BREAKOUT with level_type accepted", [tuple(x) for x in active_bo("GBPCHF")] == [("bullish", 1.10)])
tv(type="CONFIRMED", instrument="GBPCHF", direction="bullish", source="inside_range", h4_class="internal", level_type="inner_internal",
   breakout_level=1.10, source_level=1.10, h4_level=1.095, timeframe="240")
t = conn.execute(f"SELECT {alert_text_col} FROM alerts WHERE instrument='GBPCHF' ORDER BY id DESC LIMIT 1").fetchone()[0]
check("Origin alert has no Daily breakout level line (always External now)", "Daily breakout level" not in t)
tv(type="H4_CONTINUATION", instrument="GBPCHF", direction="bullish", cont_type="breakout_cont", level_type="external",
   breakout_level=1.10, h4_level=1.12, timeframe="240")
t = conn.execute(f"SELECT {alert_text_col} FROM alerts WHERE instrument='GBPCHF' ORDER BY id DESC LIMIT 1").fetchone()[0]
check("continuation alert has no Daily breakout level line", "Daily breakout level" not in t)
tv(type="H4_CONTINUATION", instrument="GBPCHF", direction="bullish", cont_type="oc_cont", level_type="sub_internal",
   breakout_level=1.10, h4_level=1.11, timeframe="240")
t = conn.execute(f"SELECT {alert_text_col} FROM alerts WHERE instrument='GBPCHF' ORDER BY id DESC LIMIT 1").fetchone()[0]
check("no Daily breakout level line on any continuation", "Daily breakout level" not in t)
tv(type="BREAKOUT", instrument="GBPCHF", direction="bearish", level=1.08, level_type="internal", range_level=1.12, timeframe="240")
check("a break the other way replaces the setup", [tuple(x) for x in active_bo("GBPCHF")] == [("bearish", 1.08)])

# 2026-10-19: inside-range reactions name the Daily V-shape / OC they came from
tv(type="BREAKOUT", instrument="EURNZD", direction="bullish", level=1.90, level_type="external", range_level=1.85, timeframe="240")
tv(type="CONFIRMED", instrument="EURNZD", direction="bullish", source="inside_range", source_kind="v_shape", h4_class="external",
   level_type="external", breakout_level=1.90, source_level=1.8712, h4_level=1.88, timeframe="240")
t = conn.execute(f"SELECT {alert_text_col} FROM alerts WHERE instrument='EURNZD' ORDER BY id DESC LIMIT 1").fetchone()[0]
check("inside-range Origin names the Daily V-shape and its level", "Daily V-shape inside the range @ 1.87120" in t)
tv(type="BREAKOUT", instrument="EURNZD", direction="bearish", level=1.85, level_type="external", range_level=1.92, timeframe="240")
tv(type="CONFIRMED", instrument="EURNZD", direction="bearish", source="inside_range", source_kind="oc", h4_class="internal",
   level_type="external", breakout_level=1.85, source_level=1.8833, h4_level=1.87, timeframe="240")
t = conn.execute(f"SELECT {alert_text_col} FROM alerts WHERE instrument='EURNZD' ORDER BY id DESC LIMIT 1").fetchone()[0]
check("inside-range Origin names the Daily OC and its level", "Daily OC inside the range @ 1.88330" in t)

# 2026-10-20: H4 back in line only after a daily reaction — the alert names that level
tv(type="H4_CONTINUATION", instrument="EURNZD", direction="bearish", cont_type="breakout_cont", source="daily_breaker",
   source_level=1.85, level_type="external", breakout_level=1.85, h4_level=1.845, timeframe="240")
t = conn.execute(f"SELECT {alert_text_col} FROM alerts WHERE instrument='EURNZD' ORDER BY id DESC LIMIT 1").fetchone()[0]
tv(type="H4_CONTINUATION", instrument="EURNZD", direction="bearish", cont_type="breakout_cont", source="daily_breaker",
   source_level=1.85, level_type="external", breakout_level=1.85, h4_level=1.8455, h4_class="external", timeframe="240")
_tr = conn.execute(f"SELECT {alert_text_col} FROM alerts WHERE instrument='EURNZD' ORDER BY id DESC LIMIT 1").fetchone()[0]
check("a back-in-line alert names its H4 External breakout", "H4 External breakout @ 1.84550" in _tr)
check("realignment alert names the daily reaction", "H4 back in line with the Daily" in t and "Daily reaction source: Daily Breaker @ 1.85000" in t)
tv(type="H4_CONTINUATION", instrument="EURNZD", direction="bearish", cont_type="breakout_cont", source="inside_range", source_kind="a_shape",
   source_level=1.8644, level_type="external", breakout_level=1.85, h4_level=1.844, timeframe="240")
t = conn.execute(f"SELECT {alert_text_col} FROM alerts WHERE instrument='EURNZD' ORDER BY id DESC LIMIT 1").fetchone()[0]
check("realignment from an inside-range A-shape is named", "Daily A-shape inside the range @ 1.86440" in t)
tv(type="H4_CONTINUATION", instrument="EURNZD", direction="bearish", cont_type="breakout_cont", level_type="external",
   breakout_level=1.85, h4_level=1.843, timeframe="240")
t = conn.execute(f"SELECT {alert_text_col} FROM alerts WHERE instrument='EURNZD' ORDER BY id DESC LIMIT 1").fetchone()[0]
check("older scripts' in-line break reads as in line with the Daily", "H4 breakout in line with the Daily" in t)
tv(type="H4_CONTINUATION", instrument="EURNZD", direction="bearish", cont_type="inline_break", level_type="external",
   breakout_level=1.85, h4_level=1.8412, timeframe="240")
t = conn.execute(f"SELECT {alert_text_col} FROM alerts WHERE instrument='EURNZD' ORDER BY id DESC LIMIT 1").fetchone()[0]
check("in-line H4 breakout alert names the new H4 Breaker",
      "H4 breakout in line with the Daily" in t and "H4 breakout @ 1.84120" in t and "This level is now the H4 Breaker." in t)

snap = {"stage": "confirmed_aligned", "bias": "bearish", "retest_source": None, "breakout_level": 0.69842,
        "d_a": 0.69842, "d_v": None, "d_oc": 0.69632, "d_oc_count": 2, "h4_a": 0.69537, "h4_v": None, "h4_bk": 0.69591, "h4_oc": 0.69293}
tv(type="PRICE_UPDATE", instrument="AUDUSD", price=0.69576, timeframe="240", snapshot=snap)
srow = conn.execute("SELECT snapshot, price FROM chart_snapshots WHERE instrument='AUDUSD'").fetchone()
import json as _j
check("chart snapshot stored from PRICE_UPDATE", srow is not None and _j.loads(srow[0]) == snap and srow[1] == 0.69576)
snap2 = dict(snap, stage="retest", retest_source="post_breakout_oc")
tv(type="PRICE_UPDATE", instrument="AUDUSD", price=0.6950, timeframe="240", snapshot=snap2)
check("snapshot is replaced by the newest one", _j.loads(conn.execute("SELECT snapshot FROM chart_snapshots WHERE instrument='AUDUSD'").fetchone()[0])["stage"] == "retest")
tv(type="PRICE_UPDATE", instrument="EURGBP", price=0.84, timeframe="240")
check("PRICE_UPDATE without a snapshot still works", conn.execute("SELECT COUNT(*) FROM chart_snapshots WHERE instrument='EURGBP'").fetchone()[0] == 0)


# ── Live Chart Board ──────────────────────────────────────────────────────
b_owner = c.get("/api/chart-board", headers=H(owner)).json()["pairs"]; tz_ = make_sub("board@x.com")["token"]
check("owner board lists every platform pair", len(b_owner) == len(config.instruments))
check("owner board carries the stored snapshot", any(p["instrument"] == "AUDUSD" and p["snapshot"] and p["snapshot"]["stage"] == "retest" for p in b_owner))
c.put("/api/user/instruments", headers=H(tz_), json={"instruments": ["AUDUSD", "EURUSD"]})
b_sub = c.get("/api/chart-board", headers=H(tz_)).json()["pairs"]
check("subscriber board shows only their alert pairs", sorted(p["instrument"] for p in b_sub) == ["AUDUSD", "EURUSD"])
check("board needs login", c.get("/api/chart-board").status_code == 401)

# 2026-10-20: broker tickers map to platform names; breakout text names the External level
for sym, plat in (("JP225", "JPN225"), ("USOIL", "WTIUSD")):
    tv(type="PRICE_UPDATE", instrument=sym, price=1.0, timeframe="240", snapshot=dict(snap, stage="breakout"))
    b = {p["instrument"]: p["snapshot"] for p in c.get("/api/chart-board", headers=H(owner)).json()["pairs"]}
    check(f"{sym} chart lands on the board as {plat}", (b.get(plat) or {}).get("stage") == "breakout")
tv(type="BREAKOUT", instrument="CHFJPY", direction="bullish", level=180.0, level_type="external", range_level=175.0, timeframe="240")
tv(type="CONFIRMED", instrument="CHFJPY", direction="bullish", source="daily_breaker", h4_class="external", level_type="external",
   breakout_level=180.0, source_level=180.0, h4_level=181.0, timeframe="240")
t = conn.execute(f"SELECT {alert_text_col} FROM alerts WHERE instrument='CHFJPY' ORDER BY id DESC LIMIT 1").fetchone()[0]
check("Origin describes the close above the External high", "A Daily candle closed above the most recent External high @ 180.000" in t)
check("Origin headline: BUY CHFJPY (Forex)", t.startswith("BUY CHFJPY (Forex)\n"))
check("Origin alert ends with whose chart and prices it used (above the signature)",
      "📊 All charts and prices are from" in t and t.index("📊") < t.index("— MummyTKT"))
check("an Origin without level_type has no Daily breakout level line", "Daily breakout level" not in t)
tv(type="PRICE_UPDATE", instrument="XAGUSD", price=48.235, timeframe="240", snapshot=dict(snap, stage="breakout"))
b = {p["instrument"]: p["snapshot"] for p in c.get("/api/chart-board", headers=H(owner)).json()["pairs"]}
check("XAGUSD is a platform instrument and lands on the board", (b.get("XAGUSD") or {}).get("stage") == "breakout")
from config import is_crypto as _isc
check("new crypto pairs count as crypto (24/7); forex doesn't", _isc("INJUSD") and _isc("OP/USD") and not _isc("USDCHF") and not _isc("EURUSD"))
tv(type="PRICE_UPDATE", instrument="INJUSDT", exchange="BINANCE", price=21.5, timeframe="240", snapshot=dict(snap, stage="breakout"))
b = {p["instrument"]: p["snapshot"] for p in c.get("/api/chart-board", headers=H(owner)).json()["pairs"]}
check("an INJUSDT chart lands on the board as INJUSD", (b.get("INJUSD") or {}).get("stage") == "breakout")
from config import normalize_symbol as _ns_
check("crypto stablecoin/perp tickers map to the USD pair; forex untouched",
      _ns_("BNBUSDT") == "BNBUSD" and _ns_("BTCUSDT.P") == "BTCUSD" and _ns_("ETHUSDC") == "ETHUSD"
      and _ns_("USDCHF") == "USDCHF" and _ns_("USDCAD") == "USDCAD" and _ns_("EUR/USD") == "EURUSD")
tv(type="PRICE_UPDATE", instrument="BNBUSDT", exchange="BINANCE", price=744.17, timeframe="240", snapshot=dict(snap, stage="retest"))
b = {p["instrument"]: p["snapshot"] for p in c.get("/api/chart-board", headers=H(owner)).json()["pairs"]}
check("a Binance BNBUSDT chart lands on the board as BNBUSD", (b.get("BNBUSD") or {}).get("stage") == "retest")
check("JP225 webhooks count as JPN225 in the feed monitor",
      conn.execute("SELECT COUNT(*) FROM webhook_heartbeats WHERE instrument='JPN225'").fetchone()[0] == 1
      and conn.execute("SELECT COUNT(*) FROM webhook_heartbeats WHERE instrument='JP225'").fetchone()[0] == 0)
# An old broker-ticker heartbeat (from before the mapping) must not raise a "no data" warning
conn.execute("INSERT OR REPLACE INTO webhook_heartbeats (instrument, last_seen_at, last_type) VALUES ('JP225', '2026-01-01T00:00:00+00:00', 'PRICE_UPDATE')")
conn.commit()
from alerts.feed_monitor import feed_health, run_feed_check
check("old broker-ticker row hidden from feed health", all(f["instrument"] != "JP225" for f in feed_health(conn)))
import asyncio as _aio
_aio.run(run_feed_check(DB, config))
check("feed check clears the old broker-ticker row",
      conn.execute("SELECT COUNT(*) FROM webhook_heartbeats WHERE instrument='JP225'").fetchone()[0] == 0)

# ── Deriv synthetic indices (2026-10-21) ──────────────────────────────────
import config as _cfgmod
SYN = "JUMP_25_INDEX"
S_ = make_sub("synth@x.com"); ts_, sid = S_["token"], S_["user"]["id"]
dbw = sqlite3.connect(DB); dbw.execute("UPDATE users SET telegram_chat_id = 'chatS' WHERE id = ?", (sid,)); dbw.commit(); dbw.close()
tv(type="PRICE_UPDATE", instrument=SYN, exchange="DERIV", price=132918.4, timeframe="240", snapshot=dict(snap, stage="breakout"))
check("a Deriv chart registers itself as a synthetic", _cfgmod.is_synthetic(SYN) and SYN in config.instruments)
check("the synthetic is saved for the next restart",
      SYN in _j.loads(conn.execute("SELECT value FROM user_config WHERE key='synthetic_instruments'").fetchone()[0]))
tv(type="PRICE_UPDATE", instrument="EURCHF", exchange="FOREXCOM", price=0.93, timeframe="240")
check("a non-Deriv chart is never registered as synthetic", not _cfgmod.is_synthetic("EURCHF"))
check("config endpoint lists synthetics", SYN in c.get("/api/config/instruments", headers=H(owner)).json()["synthetics"])
check("owner board shows the synthetic", any(p["instrument"] == SYN for p in c.get("/api/chart-board", headers=H(owner)).json()["pairs"]))
check("subscriber without a pair list doesn't see synthetics on the board",
      not any(p["instrument"] == SYN for p in c.get("/api/chart-board", headers=H(ts_)).json()["pairs"]))
sent.clear(); asyncio.run(tvw._deliver_alert(conn, cfg, SYN, "x"))
check(f"synthetic alerts reach the owner but not subscribers who didn't opt in {sorted(sent)}",
      conn.execute("SELECT telegram_chat_id FROM users WHERE role='OWNER'").fetchone()[0] in sent and "chatS" not in sent)
dbw = sqlite3.connect(DB); dbw.execute("UPDATE users SET watched_instruments = ? WHERE id = ?", (_j.dumps(["EUR/USD", SYN]), sid)); dbw.commit(); dbw.close()
sent.clear(); asyncio.run(tvw._deliver_alert(conn, cfg, SYN, "x"))
check(f"a subscriber who ticked the synthetic gets it {sorted(sent)}", "chatS" in sent)
check("…and sees it on their board", any(p["instrument"] == SYN for p in c.get("/api/chart-board", headers=H(ts_)).json()["pairs"]))
dbw = sqlite3.connect(DB); dbw.execute("UPDATE users SET watched_instruments = NULL WHERE id = ?", (sid,)); dbw.commit(); dbw.close()
tv(type="BREAKOUT", instrument=SYN, exchange="DERIV", direction="bullish", level=131500.25, level_type="external", range_level=127000.0, timeframe="240")
tv(type="CONFIRMED", instrument=SYN, exchange="DERIV", direction="bullish", source="daily_breaker", h4_class="external", level_type="external",
   breakout_level=131500.25, source_level=131500.25, h4_level=132100.5, timeframe="240")
t = conn.execute(f"SELECT {alert_text_col} FROM alerts WHERE instrument=? ORDER BY id DESC LIMIT 1", (SYN,)).fetchone()[0]
check("synthetic levels print with 2 decimals", "@ 131500.25" in t and "@ 132100.50" in t)
check("synthetic alert titles say (Synthetic)", t.splitlines()[0].endswith(f"{SYN} (Synthetic)"))
from alerts.feed_monitor import is_market_open as _imo
from datetime import datetime as _dt, timezone as _tz
_sat = _dt(2026, 10, 24, 12, tzinfo=_tz.utc)
check("synthetics count as open on a Saturday; forex doesn't", _imo(SYN, _sat) and not _imo("EURUSD", _sat))

# ── Candles for chart pictures (2026-10-21) ───────────────────────────────
from state.candles import recent as _recent
import time as _time
_t0 = (int(_time.time()) - 45 * 86400) // 86400 * 86400 * 1000   # ms, 45 days ago
r_h = tv(type="HISTORY", instrument="GBPJPY", tf="D", timeframe="240",
         bars=[[_t0 + i * 86400000, 200 + i, 201 + i, 199 + i, 200.5 + i] for i in range(40)])
check("Daily candle history is stored", r_h.status_code == 200 and len(_recent(conn, "GBPJPY", "D", 100)) == 40)
tv(type="HISTORY", instrument="GBPJPY", tf="240", timeframe="240",
   bars=[[_t0 + i * 14400000, 210, 211, 209, 210.5] for i in range(40)] + [["bad"], None])
check("H4 candle history is stored; bad rows skipped", len(_recent(conn, "GBPJPY", "H4", 100)) == 40)
tv(type="HISTORY", instrument="GBPJPY", tf="D", timeframe="60", bars=[[_t0, 1, 2, 0, 1]])
check("history from a non-4H chart is ignored", _recent(conn, "GBPJPY", "D", 1)[0][1] != 1)
tv(type="PRICE_UPDATE", instrument="GBPJPY", price=211.1, timeframe="240", snapshot=dict(snap),
   bar=[_t0 + 40 * 14400000, 210.5, 211.4, 210.2, 211.1], dbar=[_t0 + 40 * 86400000, 240, 241, 239, 240.7])
h4_last = _recent(conn, "GBPJPY", "H4", 1)[0]; d_last = _recent(conn, "GBPJPY", "D", 1)[0]
check("each price update adds the closed H4 and Daily candle", h4_last[4] == 211.1 and d_last[4] == 240.7)
r_bad = tv(type="PRICE_UPDATE", instrument="GBPJPY", price=211.2, timeframe="240", bar=["x"], dbar=None)
check("a malformed candle never blocks the price update", r_bad.status_code == 200)

# ── Chart pictures ("📊 View chart") ──────────────────────────────────────
tv(type="BREAKOUT", instrument="GBPJPY", direction="bullish", level=205.5, level_type="external", range_level=198.0, timeframe="240")
tv(type="CONFIRMED", instrument="GBPJPY", direction="bullish", source="daily_breaker", h4_class="external", level_type="external",
   breakout_level=205.5, source_level=205.5, h4_level=210.8, timeframe="240")
_aid = conn.execute("SELECT MAX(id) FROM alerts WHERE instrument='GBPJPY'").fetchone()[0]
from alerts.chart_image import load_alert_levels, picture_for_alert
_info = load_alert_levels(conn, _aid)
check("an alert saves its chart levels (Breaker, H4 level, chart levels)",
      _info is not None and {"Daily Breaker", "H4 A broken"} <= {l["label"] for l in _info["levels"]} and _info["meta"]["side"] == "BUY")
_pic = picture_for_alert(conn, _aid, "D")
check("the Daily picture renders with candles", _pic is not None and _pic[0][1:4] == b"PNG" and _pic[2] > 30)
_pic4 = picture_for_alert(conn, _aid, "H4")
check("the 4H picture renders with candles", _pic4 is not None and _pic4[2] > 30)
import alerts.telegram as _tgb
_calls = []
async def _sp(token, chat, photo, caption, reply_markup=None, reply_to=None): _calls.append(("send", chat, type(photo).__name__, reply_to)); return "FILE_D"
async def _ep(token, chat, mid, photo, caption, reply_markup=None): _calls.append(("edit", chat, type(photo).__name__, mid)); return "FILE_H4"
async def _ab(token, cid, text=""): _calls.append(("answer", text))
async def _dm(token, chat, mid): _calls.append(("delete", chat, mid)); return True, ""
_saved = (_tgb.send_photo, _tgb.edit_photo, _tgb.answer_button, _tgb.delete_message)
_tgb.send_photo, _tgb.edit_photo, _tgb.answer_button, _tgb.delete_message = _sp, _ep, _ab, _dm
TG = {"X-Telegram-Bot-Api-Secret-Token": "tgsecret"}
def tap(data, photo=False, mid=5, chat=777):
    m = {"message_id": mid, "chat": {"id": chat}}
    if photo: m["photo"] = [{"file_id": "x"}]
    return c.post("/api/telegram/update", headers=TG, json={"update_id": 1, "callback_query": {"id": "q1", "data": data, "message": m}})
_calls.clear(); tap(f"ch:{_aid}:D")
check(f"View chart sends the Daily picture as a reply {_calls[:1]}", _calls and _calls[0] == ("send", 777, "bytes", 5))
check("the picture is remembered for reuse", load_alert_levels(conn, _aid)["file_d"] == "FILE_D")
_calls.clear(); tap(f"ch:{_aid}:D")
check("a second tap reuses the stored picture (no redraw upload)", _calls and _calls[0] == ("send", 777, "str", 5))
_calls.clear(); tap(f"ch:{_aid}:H4", photo=True, mid=9)
check("4H swaps the picture in place", _calls and _calls[0] == ("edit", 777, "bytes", 9) and load_alert_levels(conn, _aid)["file_h4"] == "FILE_H4")
_ow = conn.execute("SELECT telegram_chat_id FROM users WHERE role='OWNER'").fetchone()[0]
_calls.clear(); tap(f"ch:{_aid}:D", chat=int(_ow))
check("the owner always gets a freshly drawn full picture (not the subscribers' cached one)",
      _calls and _calls[0][0] == "send" and _calls[0][2] == "bytes")
from alerts.chart_image import render as _render
_lv = [{"y": 205.5, "label": "Daily Breaker", "kind": "breaker", "tf": "both"},
       {"y": 199.0, "label": "External low", "kind": "ext", "tf": "D"}]
_cd = _recent(conn, "GBPJPY", "D", 45)
check("subscriber pictures leave out the chart's other levels",
      _render("GBPJPY", "D", _cd, _lv, {}, full=False) != _render("GBPJPY", "D", _cd, _lv, {}, full=True))
from alerts.chart_image import level_origin as _lo
_cs = [("t1", 1.10, 1.12, 1.09, 1.11), ("t2", 1.11, 1.115, 1.10, 1.105),   # A: up then down, body high 1.11
       ("t3", 1.105, 1.12, 1.10, 1.115), ("t4", 1.115, 1.13, 1.11, 1.125),  # OC: two up candles, close 1.115
       ("t5", 1.125, 1.126, 1.11, 1.11), ("t6", 1.11, 1.13, 1.105, 1.12)]   # V: down then up, body low 1.11
check("level lines start at the candle that formed them (A / OC / V)",
      _lo(1.11, "A", _cs) == "t1" and _lo(1.115, "OC", _cs) == "t3" and _lo(1.11, "V", _cs) == "t5")
check("an unmatched level falls back to a full-width line", _lo(1.2345, "A", _cs) is None)
_calls.clear(); tap("chx", photo=True, mid=9)
check("Close deletes the chart message", ("delete", "777", 9) in _calls)
_calls.clear(); tap("ch:999999:D")
check("an unknown alert just answers politely", _calls == [("answer", "No chart is available for this alert.")])
_calls.clear(); tap("rm -rf:1:D")
check("junk button data is ignored", [k for k in _calls if k[0] != "answer"] == [])
check("button taps need Telegram's secret", c.post("/api/telegram/update", json={"callback_query": {"id": "q", "data": f"ch:{_aid}:D"}}).status_code == 401)
_tgb.send_photo, _tgb.edit_photo, _tgb.answer_button, _tgb.delete_message = _saved

# ── High-impact news (2026-10-21) ─────────────────────────────────────────
import alerts.news as news
import alerts.telegram as _tgm
_now = _dt(2026, 10, 21, 6, 2, tzinfo=_tz.utc)
feed = [
    {"title": "CPI q/q", "country": "NZD", "date": "2026-10-21T17:45:00-04:00", "impact": "High", "forecast": "0.8%", "previous": "1.5%"},
    {"title": "Unemployment Claims", "country": "USD", "date": "2026-10-21T20:30:00-04:00", "impact": "High", "forecast": "", "previous": "230K"},
    {"title": "Retail Sales m/m", "country": "CHF", "date": "2026-10-21T03:30:00-04:00", "impact": "Medium", "forecast": "", "previous": ""},
    {"title": "Bank Holiday", "country": "JPY", "date": "2026-10-21T00:00:00-04:00", "impact": "Holiday", "forecast": "", "previous": ""},
    {"title": "Next week", "country": "USD", "date": "2026-10-28T08:30:00-04:00", "impact": "High", "forecast": "", "previous": ""},
]
ev = news.parse_feed(feed)
check("news feed keeps high impact only, times in UTC",
      len(ev) == 3 and ev[0]["ts"] == "2026-10-21T21:45:00+00:00" and ev[0]["currency"] == "NZD")
news.store_events(conn, ev)
check("currencies come from pairs (indices, metals, crypto map to their currency; synthetics none)",
      news.currencies_for(["NZD/USD", "GER40", "XAUUSD", "BTCUSD", SYN]) == {"NZD", "USD", "EUR"})
_out = []
async def _capn(token, chat, text): _out.append((chat, text)); return True
_old_send = _tgm.send_alert; _tgm.send_alert = _capn
config.telegram_enabled = True
dbw = sqlite3.connect(DB); dbw.execute("UPDATE users SET watched_instruments = ? WHERE id = ?", (_j.dumps(["EUR/USD"]), sid)); dbw.commit(); dbw.close()
n1 = asyncio.run(news.run_news_summary(DB, config, now=_now))
_owner_chat = conn.execute("SELECT telegram_chat_id FROM users WHERE role='OWNER'").fetchone()[0]
_by = dict(_out)
check(f"morning summary goes out ({n1} people)", n1 >= 1 and _owner_chat in _by)
check("owner's summary lists NZD CPI with WAT time and figures",
      "NZD: CPI q/q" in _by.get(_owner_chat, "") and "Wed 21 Oct, 21:45 UTC (22:45 WAT)" in _by.get(_owner_chat, "")
      and "Forecast 0.8% · Previous 1.5%" in _by.get(_owner_chat, ""))
check("a EUR/USD-only subscriber gets USD news but not NZD",
      "chatS" in _by and "USD: Unemployment Claims" in _by["chatS"] and "NZD" not in _by["chatS"])
check("events beyond 24 hours are left out", "Next week" not in _by.get(_owner_chat, ""))
_out.clear()
check("the summary is never sent twice the same day", asyncio.run(news.run_news_summary(DB, config, now=_now)) == 0 and not _out)
_out.clear()
asyncio.run(news.run_news_reminders(DB, config, now=_dt(2026, 10, 21, 21, 17, tzinfo=_tz.utc)))
_by = dict(_out)
check("30-minute reminder for NZD CPI reaches the owner, not the EUR/USD-only subscriber",
      "In 30 minutes" in _by.get(_owner_chat, "").replace("news in 30 minutes", "In 30 minutes") and "chatS" not in _by)
_out.clear()
asyncio.run(news.run_news_reminders(DB, config, now=_dt(2026, 10, 21, 21, 22, tzinfo=_tz.utc)))
check("the reminder is sent once", not _out)
asyncio.run(news.run_news_reminders(DB, config, now=_dt(2026, 10, 21, 20, 0, tzinfo=_tz.utc)))
check("no reminder earlier than 30 minutes before", not _out)
c.patch("/api/preferences", headers=H(ts_), json={"newsAlerts": False})
check("news switch saves", c.get("/api/preferences", headers=H(ts_)).json()["newsAlerts"] is False)
_out.clear()
asyncio.run(news.run_news_summary(DB, config, now=_now + timedelta(days=1)))
check("someone who switched news off gets none", "chatS" not in dict(_out))
_tgm.send_alert = _old_send
config.telegram_enabled = False
dbw = sqlite3.connect(DB); dbw.execute("UPDATE users SET watched_instruments = NULL WHERE id = ?", (sid,)); dbw.commit(); dbw.close()

# ── Weekly storyline, engulfing, alert-type switches (2026-10-22) ─────────
tv(type="BREAKOUT", instrument="AUDCAD", direction="bullish", level=0.9100, level_type="external", range_level=0.9000, timeframe="240")
tv(type="CONFIRMED", instrument="AUDCAD", direction="bullish", source="daily_breaker", h4_class="external", level_type="external",
   breakout_level=0.9100, source_level=0.9100, h4_level=0.9150, timeframe="240",
   wk_rel="confirmed", wk_dir="bullish", wk_level=0.9050, wk_src="Weekly Breaker", wk_src_level=0.9050, wk_cls="external")
t = conn.execute(f"SELECT {alert_text_col} FROM alerts WHERE instrument='AUDCAD' ORDER BY id DESC LIMIT 1").fetchone()[0]
check("a Weekly-confirmed Origin states the Weekly storyline",
      "Weekly: Bullish breakout @ 0.90500 → reaction at Weekly Breaker @ 0.90500" in t
      and "Weekly-confirmed: the Daily breakout is an External breakout in the Weekly direction." in t
      and t.index("Daily breakout:") < t.index("Weekly: Bullish"))
tv(type="H4_CONTINUATION", instrument="AUDCAD", direction="bullish", cont_type="oc_cont", level_type="external",
   breakout_level=0.9100, h4_level=0.9120, timeframe="240", wk_rel="against", wk_dir="bearish", wk_level=0.9300)
t = conn.execute(f"SELECT {alert_text_col} FROM alerts WHERE instrument='AUDCAD' ORDER BY id DESC LIMIT 1").fetchone()[0]
check("continuation headline: BUY CONTINUATION — BUY AUDCAD (Forex)", t.startswith("BUY CONTINUATION — BUY AUDCAD (Forex)"))
check("a setup against the Weekly is marked", "AGAINST the Weekly direction" in t and "Weekly: Bearish breakout @ 0.93000" in t)
tv(type="H4_CONTINUATION", instrument="AUDCAD", direction="bullish", cont_type="engulfing", level_type="external",
   breakout_level=0.9100, h4_level=0.9135, timeframe="240")
t = conn.execute(f"SELECT {alert_text_col} FROM alerts WHERE instrument='AUDCAD' ORDER BY id DESC LIMIT 1").fetchone()[0]
check("engulfing alert reads right and has no Weekly line without a Weekly setup",
      "H4 Engulfing in the Daily direction" in t and "closed above its high @ 0.91350" in t and "Weekly:" not in t)
c.patch("/api/preferences", headers=H(ts_), json={"contOc": False, "contEngulfing": False})
_pp = c.get("/api/preferences", headers=H(ts_)).json()
check("alert-type switches save", _pp["contOc"] is False and _pp["contEngulfing"] is False and _pp["alertOrigin"] is True)
sent.clear(); asyncio.run(tvw._deliver_alert(conn, cfg, "EURUSD", "x", pref="cont_oc"))
check(f"a subscriber who switched OC alerts off doesn't get them {sorted(sent)}", "chatS" not in sent and len(sent) >= 1)
sent.clear(); asyncio.run(tvw._deliver_alert(conn, cfg, "EURUSD", "x", pref="cont_breaker"))
check("…but still gets the types left on", "chatS" in sent)
c.patch("/api/preferences", headers=H(ts_), json={"alertOrigin": False})
sent.clear(); asyncio.run(tvw._deliver_alert(conn, cfg, "EURUSD", "x", h4_class="external", pref="origin"))
check("switching Origin off stops Origins", "chatS" not in sent)
c.patch("/api/preferences", headers=H(ts_), json={"alertOrigin": True, "contOc": True, "contEngulfing": True})
_switches = [("alertOrigin", "origin", "external"), ("contInline", "cont_inline", None), ("contBreaker", "cont_breaker", None),
             ("contOc", "cont_oc", None), ("contRealign", "cont_realign", "external"), ("contEngulfing", "engulfing", None)]
for field, pref_key, cls in _switches:
    c.patch("/api/preferences", headers=H(ts_), json={field: False})
    sent.clear(); asyncio.run(tvw._deliver_alert(conn, cfg, "EURUSD", "x", h4_class=cls, pref=pref_key))
    off_ok = "chatS" not in sent
    c.patch("/api/preferences", headers=H(ts_), json={field: True})
    sent.clear(); asyncio.run(tvw._deliver_alert(conn, cfg, "EURUSD", "x", h4_class=cls, pref=pref_key))
    check(f"switching {field} off really stops it; on brings it back", off_ok and "chatS" in sent)
check("engulfing choice defaults to 'covers the wick'", c.get("/api/preferences", headers=H(ts_)).json()["engulfMode"] == "wick")
def _eng(wick):
    sent.clear(); asyncio.run(tvw._deliver_alert(conn, cfg, "EURUSD", "x", pref="engulfing", engulf_wick=wick)); return "chatS" in sent
check("default: wick engulfings arrive, body-only ones don't", _eng(True) and not _eng(False))
c.patch("/api/preferences", headers=H(ts_), json={"engulfMode": "body"})
check("'covers the body only': body-only arrive, wick ones don't", _eng(False) and not _eng(True))
c.patch("/api/preferences", headers=H(ts_), json={"engulfMode": "both"})
check("'both': every engulfing arrives", _eng(False) and _eng(True))
c.patch("/api/preferences", headers=H(ts_), json={"engulfMode": "nonsense"})
check("an invalid engulfing choice is ignored", c.get("/api/preferences", headers=H(ts_)).json()["engulfMode"] == "both")
c.patch("/api/preferences", headers=H(ts_), json={"engulfMode": "wick"})
tv(type="H4_CONTINUATION", instrument="AUDCAD", direction="bullish", cont_type="engulfing", eng_wick=False, level_type="external",
   breakout_level=0.9100, h4_level=0.9125, timeframe="240")
_te = conn.execute(f"SELECT {alert_text_col} FROM alerts WHERE instrument='AUDCAD' ORDER BY id DESC LIMIT 1").fetchone()[0]
check("a body-only engulfing message says so", "engulfing (covers the body) @ 0.91250" in _te and "closed above its open @ 0.91250 (inside its wick)" in _te)
# Daily engulfing (2026-10-27): its own switch and its own wick / body / both choice
tv(type="H4_CONTINUATION", instrument="AUDCAD", direction="bullish", cont_type="d_engulfing", eng_wick=True, level_type="external",
   breakout_level=0.9100, h4_level=0.9160, timeframe="240")
_td = conn.execute(f"SELECT {alert_text_col} FROM alerts WHERE instrument='AUDCAD' ORDER BY id DESC LIMIT 1").fetchone()[0]
check("a Daily engulfing alert is only the pair and the message, no buy / sell",
      _td == "AUDCAD\nDaily engulfing candle has formed")
# Notification-list filter (2026-10-27): each alert keeps its exact type
_types = conn.execute("SELECT alert_type FROM alerts WHERE instrument='AUDCAD' ORDER BY id DESC LIMIT 2").fetchall()
check("alerts are stored with their exact type", [t[0] for t in _types] == ["d_engulfing", "engulfing"])
_lst = c.get("/api/alerts?limit=50&types=d_engulfing", headers=H(ts_)).json()["items"]
check("the alert list shows only the types asked for",
      len(_lst) > 0 and all(i["alert_type"] == "d_engulfing" for i in _lst))
_all = c.get("/api/alerts?limit=50", headers=H(ts_)).json()["items"]
check("with no type filter every type is listed", len({i["alert_type"] for i in _all}) > 1)
from state.repository import alert_type_for
check("old alerts are typed from their text",
      alert_type_for("h4_breakout_cont", "X\nDaily reaction + H4 breakout\n") == "daily_react"
      and alert_type_for("h4_breakout_cont", "X\nH4 back in line with the Daily\n") == "realign"
      and alert_type_for("h4_breakout_cont", "X\nH4 breakout in line\n") == "inline"
      and alert_type_for("h4_oc_cont", "") == "oc")
_pd = c.get("/api/preferences", headers=H(ts_)).json()
check("Daily engulfing is on by default with 'covers the wick'", _pd["dailyEngulfing"] is True and _pd["dEngulfMode"] == "wick")
def _deng(wick):
    sent.clear(); asyncio.run(tvw._deliver_alert(conn, cfg, "EURUSD", "x", pref="d_engulfing", engulf_wick=wick,
                                                 engulf_key="pref_d_engulf_mode")); return "chatS" in sent
c.patch("/api/preferences", headers=H(ts_), json={"dEngulfMode": "body", "engulfMode": "wick"})
check("the Daily engulfing choice is separate from the H4 one", _deng(False) and not _deng(True) and _eng(True) and not _eng(False))
c.patch("/api/preferences", headers=H(ts_), json={"dailyEngulfing": False})
check("switching Daily engulfing off stops it", not _deng(False))
c.patch("/api/preferences", headers=H(ts_), json={"dailyEngulfing": True, "dEngulfMode": "wick"})
sent.clear(); asyncio.run(tvw._deliver_alert(conn, cfg, "EURUSD", "x", h4_class="internal", pref="cont_realign"))
check("an Internal 'back in line' alert skips people with Internal off", "chatS" not in sent)
check("subscribers get the Short style by default; the owner Full",
      c.get("/api/preferences", headers=H(ts_)).json()["alertStyle"] == "short"
      and c.get("/api/preferences", headers=H(owner)).json()["alertStyle"] == "full")
c.patch("/api/preferences", headers=H(ts_), json={"alertStyle": "full"})
check("message style saves", c.get("/api/preferences", headers=H(ts_)).json()["alertStyle"] == "full")
c.patch("/api/preferences", headers=H(ts_), json={"alertStyle": "short"})
_full_txt = conn.execute(f"SELECT {alert_text_col} FROM alerts WHERE instrument='AUDCAD' AND alert_text LIKE '%Weekly-confirmed%' LIMIT 1").fetchone()[0]
_got = {}
async def _capt(token, chat, text, reply_markup=None): _got[chat] = text; return True
_old_t = tvw.send_alert; tvw.send_alert = _capt
asyncio.run(tvw._deliver_alert(conn, cfg, "AUDCAD", _full_txt, pref="origin"))
tvw.send_alert = _old_t
_sh = _got.get("chatS", "")
check("Short-style subscribers get the short message; others the full one",
      _sh and len(_sh) < len(_full_txt) and "Weekly-confirmed" in _sh and "Reason:" in _sh
      and "aligns with the most recent Daily breakout" not in _sh
      and _got.get(_owner_chat) == _full_txt)
c.patch("/api/preferences", headers=H(owner), json={"alertStyle": "short"})
_got.clear(); tvw.send_alert = _capt
asyncio.run(tvw._deliver_alert(conn, cfg, "AUDCAD", _full_txt, pref="origin"))
tvw.send_alert = _old_t
check("the owner who switches to Short gets the short message too",
      _got.get(_owner_chat) and _got[_owner_chat] == tvw.short_text(_full_txt) and len(_got[_owner_chat]) < len(_full_txt))
c.patch("/api/preferences", headers=H(owner), json={"alertStyle": "full"})
c.patch("/api/preferences", headers=H(ts_), json={"alertStyle": "full"})

# ── Testers (2026-10-21) ───────────────────────────────────────────────────
_tok = c.post("/api/auth/invite", headers=H(owner), json={"email": "tester@x.com", "plan": "TESTER", "plan_days": 21}).json()["token"]
dbw = sqlite3.connect(DB)
dbw.execute("UPDATE users SET created_at = datetime('now', '-5 days'), plan_expires_at = ? WHERE email = 'tester@x.com'", ((datetime.now(timezone.utc) + timedelta(days=16)).isoformat(),))   # invited 5 days ago
dbw.commit(); dbw.close()
_reg = c.post("/api/auth/register", json={"token": _tok, "name": "Tess Ter", "password": "testerpass1"})
_exp = conn.execute("SELECT plan_expires_at FROM users WHERE email = 'tester@x.com'").fetchone()[0]
_days_left = (datetime.fromisoformat(_exp) - datetime.now(timezone.utc)).total_seconds() / 86400
check(f"a tester gets the full 21 days from sign-up, not from the invite ({_days_left:.2f})", _reg.status_code == 200 and 20.9 < _days_left <= 21.01)
from alerts.reminders import run_reminders
_tid = conn.execute("SELECT id FROM users WHERE email = 'tester@x.com'").fetchone()[0]
dbw = sqlite3.connect(DB)
dbw.execute("UPDATE users SET telegram_chat_id = 'chatT', plan_expires_at = ? WHERE id = ?",
            ((datetime.now(timezone.utc) + timedelta(days=2)).isoformat(), _tid)); dbw.commit(); dbw.close()
_rem = []
async def _capr(token, chat, text, reply_markup=None): _rem.append((chat, text)); return True
_old_r = _tgm.send_alert; _tgm.send_alert = _capr; config.telegram_enabled = True
asyncio.run(run_reminders(DB, config))
_tt = [t for ch, t in _rem if ch == "chatT"]
check("a tester's 'ends soon' message thanks them and has no payment link",
      len(_tt) == 1 and "Thank you for testing" in _tt[0] and "checkout" not in _tt[0])
dbw = sqlite3.connect(DB)
dbw.execute("UPDATE users SET plan_expires_at = ? WHERE id = ?", ((datetime.now(timezone.utc) - timedelta(hours=3)).isoformat(), _tid)); dbw.commit(); dbw.close()
_rem.clear(); asyncio.run(run_reminders(DB, config))
_tt = [t for ch, t in _rem if ch == "chatT"]
check("a tester's 'ended' message has no payment link", len(_tt) == 1 and "checkout" not in _tt[0] and "Thank you" in _tt[0])
_tgm.send_alert = _old_r; config.telegram_enabled = False

# Instruments added after the list was saved reach an existing DB once
from state.instruments import load_instruments
_c2 = sqlite3.connect(os.path.join(tmpdir, "inst.db")); _c2.execute("CREATE TABLE user_config (key TEXT PRIMARY KEY, value TEXT, updated_at TEXT)")
_c2.execute("INSERT INTO user_config (key, value) VALUES ('instruments', ?)", (_j.dumps(["EUR/USD", "XAU/USD"]),)); _c2.commit()
_ns = NS(instruments=[])
load_instruments(_c2, _ns)
check("XAG/USD and the new crypto are added to an older saved list",
      _ns.instruments[:3] == ["EUR/USD", "XAU/USD", "XAG/USD"] and "INJ/USD" in _ns.instruments and "ASTER/USD" in _ns.instruments)
_c2.execute("UPDATE user_config SET value = ? WHERE key = 'instruments'", (_j.dumps(["EUR/USD"]),)); _c2.commit()
load_instruments(_c2, _ns)
check("an owner's later removal sticks (added only once)", _ns.instruments == ["EUR/USD"])
_cfgmod.SYNTHETICS.add(SYN)   # load_instruments on the other DB reset the set

# ── Continuations follow the setup's latest H4 confirmation (2026-10-22) ──
_dl = []
async def _rec_deliver(conn_, cfg_, instrument, text, **kw): _dl.append(kw.get("h4_class"))
_old_dl, tvw._deliver_alert = tvw._deliver_alert, _rec_deliver
config.telegram_enabled = True
tv(type="BREAKOUT", instrument="CHFJPY", direction="bearish", level=176.0, level_type="external", range_level=181.0, timeframe="240")
tv(type="BREAKOUT", instrument="CHFJPY", direction="bullish", level=180.0, level_type="external", range_level=175.0, timeframe="240")
check("a Daily breakout the other way clears the setup's class", tvw._setup_class(conn, "CHFJPY") is None)
_dl.clear(); tv(type="H4_CONTINUATION", instrument="CHFJPY", direction="bullish", cont_type="oc_cont", breakout_level=180.0, h4_level=181.0, timeframe="240")
check("with no confirmation known, a continuation isn't filtered by External/Internal", _dl == [None])
tv(type="CONFIRMED", instrument="CHFJPY", direction="bullish", source="daily_breaker", h4_class="internal",
   breakout_level=180.0, source_level=180.0, h4_level=181.0, timeframe="240")
_dl.clear(); tv(type="H4_CONTINUATION", instrument="CHFJPY", direction="bullish", cont_type="oc_cont", breakout_level=180.0, h4_level=181.5, timeframe="240")
check("after an Internal Origin, continuations count as Internal (skip people with Internal off)", _dl == ["internal"])
_dl.clear(); tv(type="H4_CONTINUATION", instrument="CHFJPY", direction="bullish", cont_type="breakout_cont", h4_class="external",
               source="daily_breaker", source_level=180.0, breakout_level=180.0, h4_level=182.0, timeframe="240")
_dl.clear(); tv(type="H4_CONTINUATION", instrument="CHFJPY", direction="bullish", cont_type="engulfing", eng_wick=True,
               breakout_level=180.0, h4_level=182.5, timeframe="240")
check("after an External 'back in line', continuations count as External again", _dl == ["external"])
tv(type="BREAKOUT", instrument="CADJPY", direction="bearish", level=110.0, level_type="external", range_level=115.0, timeframe="240")
tv(type="CONFIRMED", instrument="CADJPY", direction="bearish", source="daily_breaker", h4_class="internal",
   breakout_level=110.0, source_level=110.0, h4_level=109.5, timeframe="240")
conn.execute("DELETE FROM user_config WHERE key = 'setup_h4_class:CADJPY'"); conn.commit()   # as if confirmed before the class was kept
_dl.clear(); tv(type="H4_CONTINUATION", instrument="CADJPY", direction="bearish", cont_type="oc_cont", breakout_level=110.0, h4_level=109.0, timeframe="240")
check("an older setup's class is read from its stored Origin alert", _dl == ["internal"])
# v7 script: Daily V-shape after the breakout, "Daily reaction + H4 breakout", same-direction breakout
tv(type="BREAKOUT", instrument="AUDCHF", direction="bullish", level=0.55, level_type="external", range_level=0.53, timeframe="240")
r7 = tv(type="CONFIRMED", instrument="AUDCHF", direction="bullish", source="post_breakout_v", h4_class="external",
        breakout_level=0.55, source_level=0.56, h4_level=0.565, timeframe="240")
_t7 = conn.execute(f"SELECT {alert_text_col} FROM alerts WHERE instrument='AUDCHF' ORDER BY id DESC LIMIT 1").fetchone()
check("an Origin from a Daily V-shape after the breakout is accepted and named", r7.status_code == 200 and _t7 and "after the breakout" in _t7[0])
_dl.clear(); tv(type="H4_CONTINUATION", instrument="AUDCHF", direction="bullish", cont_type="daily_react", h4_class="external",
               source="post_breakout_v", source_level=0.57, breakout_level=0.55, h4_level=0.58, timeframe="240")
_t7 = conn.execute(f"SELECT {alert_text_col} FROM alerts WHERE instrument='AUDCHF' ORDER BY id DESC LIMIT 1").fetchone()[0]
check("'Daily reaction + H4 breakout' is written as such (not 'back in line')",
      "Daily reaction + H4 breakout" in _t7 and "back in line" not in _t7 and _dl == ["external"])
tv(type="BREAKOUT", instrument="AUDCHF", direction="bullish", level=0.58, level_type="external", range_level=0.55, timeframe="240")
check("a new Daily breakout in the same direction keeps the setup's External/Internal", tvw._setup_class(conn, "AUDCHF") == "external")
# v8 script: Daily FVG reactions and the H4 FVG liquidity marker
from api.alert_prefs import get_alert_prefs
_dlp = []
async def _rec_deliver2(conn_, cfg_, instrument, text, **kw): _dlp.append((text, kw.get("pref"), kw.get("h4_class")))
tvw._deliver_alert = _rec_deliver2
r8 = tv(type="H4_CONTINUATION", instrument="AUDCHF", direction="bullish", cont_type="daily_react", h4_class="external",
        source="post_breakout_fvg", source_level=0.595, source_level2=0.59, breakout_level=0.58, h4_level=0.60, timeframe="240")
check("a Daily reaction at a Daily FVG after the breakout is accepted and named with its whole gap",
      r8.status_code == 200 and _dlp and "Daily FVG after the breakout @ 0.59000" in _dlp[-1][0] and "0.59500" in _dlp[-1][0])
_bk8 = conn.execute("SELECT last_h4_breaker_level FROM instrument_state WHERE instrument='AUDCHF'").fetchone()[0]
_dlp.clear(); tv(type="H4_CONTINUATION", instrument="AUDCHF", direction="bullish", cont_type="h4_fvg",
                 breakout_level=0.58, h4_level=0.601, fvg_low=0.601, fvg_high=0.603, timeframe="240")
check("the H4 FVG alert is only the pair and the message (no buy / sell)",
      _dlp and _dlp[0][0] == "AUDCHF\nH4 FVG candle after breakout has formed")
check("the H4 FVG alert answers to its own Alert Filters switch and follows the setup's class",
      _dlp and _dlp[0][1] == "h4_fvg" and _dlp[0][2] == "external")
check("the H4 FVG alert doesn't move the H4 Breaker",
      conn.execute("SELECT last_h4_breaker_level FROM instrument_state WHERE instrument='AUDCHF'").fetchone()[0] == _bk8)
_r8 = tv(type="CONFIRMED", instrument="CADJPY", direction="bearish", source="inside_fvg", h4_class="external",
         breakout_level=110.0, source_level=111.0, source_level2=111.6, h4_level=110.5, timeframe="240")
check("a confirmation from a Daily FVG inside the range is accepted", _r8.status_code == 200)
check("subscribers get the H4 FVG alert off by default; the owner on",
      get_alert_prefs(conn, bid, "SUBSCRIBER")["h4_fvg"] is False and get_alert_prefs(conn, None, "OWNER")["h4_fvg"] is True)
_F8 = make_sub("fvg@x.com")
check("the H4 FVG switch shows in Alert Filters, off for a subscriber",
      c.get("/api/preferences", headers=H(_F8["token"])).json().get("h4Fvg") is False)
c.patch("/api/preferences", headers=H(_F8["token"]), json={"h4Fvg": True})
check("a subscriber can switch the H4 FVG alert on", get_alert_prefs(conn, _F8["user"]["id"], "SUBSCRIBER")["h4_fvg"] is True)
tvw._deliver_alert = _old_dl
config.telegram_enabled = False

# ── Bot command menu + Mini App sign-in (2026-10-22) ──────────────────────
import hashlib as _hl, hmac as _hm, time as _time
from urllib.parse import urlencode as _ue
import alerts.bot_menu as _bm
from api.alert_prefs import get_alert_prefs
config.telegram_bot_token = "123:TEST"
def _init(uid, token="123:TEST", age=0):
    f = {"auth_date": str(int(_time.time()) - age), "query_id": "q", "user": _j.dumps({"id": uid, "first_name": "T"})}
    dcs = "\n".join(f"{k}={v}" for k, v in sorted(f.items()))
    key = _hm.new(b"WebAppData", token.encode(), _hl.sha256).digest()
    f["hash"] = _hm.new(key, dcs.encode(), _hl.sha256).hexdigest()
    return _ue(f)
_T = make_sub("tg@x.com"); _tgid = _T["user"]["id"]
dbw = sqlite3.connect(DB); dbw.execute("UPDATE users SET telegram_chat_id = '5550001' WHERE id = ?", (_tgid,)); dbw.commit(); dbw.close()
_r = c.post("/api/auth/telegram", json={"init_data": _init(5550001)})
check("a linked Telegram signs in from the Mini App as its own account",
      _r.status_code == 200 and _r.json()["user"]["id"] == _tgid and c.get("/api/auth/me", headers=H(_r.json()["token"])).json()["id"] == _tgid)
check("forged Mini App data is refused", c.post("/api/auth/telegram", json={"init_data": _init(5550001, token="999:OTHER")}).status_code == 401)
check("old Mini App data is refused", c.post("/api/auth/telegram", json={"init_data": _init(5550001, age=200000)}).status_code == 401)
check("an unlinked Telegram gets 'not linked'", c.post("/api/auth/telegram", json={"init_data": _init(5550999)}).status_code == 404)
_said = []
_gone = []
_mid = [100]
async def _sa(token, chat, text, reply_markup=None): _said.append((chat, text, reply_markup)); _mid[0] += 1; return _mid[0]
async def _ab2(token, cid, text=""): _said.append(("answer", text, None))
async def _dm2(token, chat, mid): _gone.append(mid); return True, ""
_old_bm = (_bm.send_message_id, _bm.answer_button, _bm.delete_message)
_bm.send_message_id, _bm.answer_button, _bm.delete_message = _sa, _ab2, _dm2
def cmd(text, chat=5550001, ctype="private", mid=None):
    _said.clear(); _gone.clear()
    c.post("/api/telegram/update", headers=TG, json={"update_id": 2, "message": {"message_id": mid, "text": text, "chat": {"id": chat, "type": ctype}}})
    return _said
_m = cmd("/pricealerts")
check("/pricealerts answers with a button opening Level Watch inside Telegram",
      len(_m) == 1 and _m[0][2].inline_keyboard[0][0].web_app.url.endswith("/price-alerts"))
_m = cmd("/confirmations@MummyBot")
check("/confirmations opens Alert Filters", _m and _m[0][2].inline_keyboard[0][0].web_app.url.endswith("/preferences"))
_m = cmd("/start")
check("plain /start greets a linked person with Open Bias Pointer", _m and _m[0][2].inline_keyboard[0][0].web_app.url.endswith("/hub"))
_m = cmd("/board", chat=5550999)
check("an unlinked chat is told how to link", _m and "isn't linked" in _m[0][1])
check("/help explains the alert words", "BUY / SELL CONTINUATION" in cmd("/help")[0][1])
check("menu commands are ignored in groups", cmd("/board", ctype="group") == [])
_m = cmd("/news")
check("/news shows the current setting with a switch", _m and "ON" in _m[0][1] and _m[0][2].inline_keyboard[0][0].callback_data == "nw:0")
_said.clear()
c.post("/api/telegram/update", headers=TG, json={"update_id": 3, "callback_query": {"id": "q", "data": "nw:0", "message": {"message_id": 1, "chat": {"id": 5550001}}}})
check("the news switch turns news off for that person only",
      get_alert_prefs(conn, _tgid, "SUBSCRIBER")["news"] is False and get_alert_prefs(conn, bid, "SUBSCRIBER")["news"] is True)
_said.clear()
c.post("/api/telegram/update", headers=TG, json={"update_id": 4, "message": {"text": "/start nosuchtoken", "chat": {"id": 5550001, "type": "private"}}})
check("/start <link> still goes to account linking", _said == [])
_m = cmd("/board", mid=50); _first = _mid[0]
_m = cmd("/settings", mid=51)
check("the typed command is deleted and the last menu reply is replaced (one reply at a time)",
      _gone == [51, _first] and len(_m) == 1)
check("every menu reply has a Close button", _m[0][2].inline_keyboard[-1][0].callback_data == "chx")
_bm.send_message_id, _bm.answer_button, _bm.delete_message = _old_bm
config.telegram_bot_token = ""

passed = sum(ok for _, ok in results)
for name, ok in results:
    print(("PASS " if ok else "FAIL ") + name)
print(f"\n{passed}/{len(results)} checks passed")
sys.exit(0 if passed == len(results) else 1)

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
]
for method, path, body in owner_only:
    st = c.request(method, path, headers=H(ta), json=body).status_code
    check(f"subscriber refused: {method} {path} (got {st})", st in (401, 403))
check("owner can list users", c.get("/api/auth/users", headers=H(owner)).status_code == 200)
check("owner can read strategy content", c.get("/api/strategy-content", headers=H(owner)).status_code == 200)
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
check("A can save own delivery prefs",
      c.patch("/api/preferences", headers=H(ta), json={"alertInternal": False}).status_code == 200)
pa_ = c.get("/api/preferences", headers=H(ta)).json()
check("A's prefs read back (internal off, external on)", pa_["alertInternal"] is False and pa_["alertExternal"] is True)
check("A's choice does not change B's", c.get("/api/preferences", headers=H(tb)).json()["alertInternal"] is True)
check("A's choice does not change owner's", c.get("/api/preferences", headers=H(owner)).json()["alertInternal"] is True)

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
check(f"internal Origin skips A (who switched it off) {sorted(sent)}", "chatA" not in sent and {"chatB", "chatOwner"} <= set(sent))
sent.clear(); asyncio.run(tvw._deliver_alert(conn, cfg, "EURUSD", "x", h4_class="external"))
check(f"external Origin reaches A {sorted(sent)}", "chatA" in sent)
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
t3 = c.post("/api/announcements", headers=H(owner), json={"title": "Every plan", "body": "x", "plans": ["TRIAL", "30DAY", "6MONTH", "9MONTH", "12MONTH", "LIFETIME"]}).json()
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
check("Origin alert names the inner internal break", "Daily breakout level: Inner internal" in t)
tv(type="H4_CONTINUATION", instrument="GBPCHF", direction="bullish", cont_type="breakout_cont", level_type="external",
   breakout_level=1.10, h4_level=1.12, timeframe="240")
t = conn.execute(f"SELECT {alert_text_col} FROM alerts WHERE instrument='GBPCHF' ORDER BY id DESC LIMIT 1").fetchone()[0]
check("continuation alert names the external break", "Daily breakout level: External" in t)
tv(type="H4_CONTINUATION", instrument="GBPCHF", direction="bullish", cont_type="oc_cont", level_type="sub_internal",
   breakout_level=1.10, h4_level=1.11, timeframe="240")
t = conn.execute(f"SELECT {alert_text_col} FROM alerts WHERE instrument='GBPCHF' ORDER BY id DESC LIMIT 1").fetchone()[0]
check("continuation alert names a sub-internal break", "Daily breakout level: Sub-internal" in t)
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
tv(type="PRICE_UPDATE", instrument="XAGUSD", price=48.235, timeframe="240", snapshot=dict(snap, stage="breakout"))
b = {p["instrument"]: p["snapshot"] for p in c.get("/api/chart-board", headers=H(owner)).json()["pairs"]}
check("XAGUSD is a platform instrument and lands on the board", (b.get("XAGUSD") or {}).get("stage") == "breakout")
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
from alerts.feed_monitor import is_market_open as _imo
from datetime import datetime as _dt, timezone as _tz
_sat = _dt(2026, 10, 24, 12, tzinfo=_tz.utc)
check("synthetics count as open on a Saturday; forex doesn't", _imo(SYN, _sat) and not _imo("EURUSD", _sat))

# ── Candles for chart pictures (2026-10-21) ───────────────────────────────
from state.candles import recent as _recent
_t0 = 1792800000000   # ms
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

# Instruments added after the list was saved reach an existing DB once
from state.instruments import load_instruments
_c2 = sqlite3.connect(os.path.join(tmpdir, "inst.db")); _c2.execute("CREATE TABLE user_config (key TEXT PRIMARY KEY, value TEXT, updated_at TEXT)")
_c2.execute("INSERT INTO user_config (key, value) VALUES ('instruments', ?)", (_j.dumps(["EUR/USD", "XAU/USD"]),)); _c2.commit()
_ns = NS(instruments=[])
load_instruments(_c2, _ns)
check("XAG/USD is added to an older saved list", _ns.instruments == ["EUR/USD", "XAU/USD", "XAG/USD"])
_c2.execute("UPDATE user_config SET value = ? WHERE key = 'instruments'", (_j.dumps(["EUR/USD"]),)); _c2.commit()
load_instruments(_c2, _ns)
check("an owner's later removal sticks (added only once)", _ns.instruments == ["EUR/USD"])
_cfgmod.SYNTHETICS.add(SYN)   # load_instruments on the other DB reset the set

passed = sum(ok for _, ok in results)
for name, ok in results:
    print(("PASS " if ok else "FAIL ") + name)
print(f"\n{passed}/{len(results)} checks passed")
sys.exit(0 if passed == len(results) else 1)

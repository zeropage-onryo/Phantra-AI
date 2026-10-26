"""What's new (src/whats_new.py, app/whats_new_routes.py; 2026-10-25,
docs/tasks/task-whats-new.md): the sync files what is new and retires what
left, spending nothing; the feed shows a person only live tiles they can use;
a person's marks are their own."""
import datetime as dt

import pytest

from src import db, fal, whats_new

NOW = dt.datetime(2026, 11, 1, 12, tzinfo=dt.timezone.utc)


def _status(pg, item_id):
    with db.connect(pg) as conn:
        row = conn.execute("SELECT status FROM showcase_items WHERE id = %s", (item_id,)).fetchone()
    return row[0] if row else None


def _go_live(pg, item_id, *, days_ago=1, media="site/showcase/x.mp4"):
    with db.connect(pg) as conn:
        conn.execute("UPDATE showcase_items SET status = 'live', media = %s,"
                     " live_at = %s WHERE id = %s",
                     (media, NOW - dt.timedelta(days=days_ago), item_id))


@pytest.fixture
def ws(pg):
    """Two real workspaces: announcement_seen's owner is a real account."""
    from src import accounts
    accounts.init(pg)
    return (accounts.upsert_account("wn-one", "One", "#fff", dsn=pg),
            accounts.upsert_account("wn-two", "Two", "#fff", dsn=pg))


@pytest.fixture
def hand(monkeypatch):
    """Empty hand lists, so a test sets exactly the entries it means."""
    monkeypatch.setattr(whats_new, "FEATURES", [])
    monkeypatch.setattr(whats_new, "COMING_SOON", [])
    monkeypatch.setattr(whats_new, "DEALS", [])
    return whats_new


@pytest.fixture
def a_new_model(monkeypatch):
    rows = dict(fal.VIDEO_MODELS)
    monkeypatch.setattr(fal, "VIDEO_MODELS", rows)

    def add(key="test-model-9"):
        rows[key] = {**fal.VIDEO_MODELS["grok1.5"], "t2v": f"x/{key}", "i2v": f"x/{key}/i2v"}
        return f"model:{key}"

    def remove(key="test-model-9"):
        rows.pop(key, None)
    add.remove = remove
    return add


# -- sync ---------------------------------------------------------------------


def test_the_first_sync_files_old_news_as_skipped_and_grok_as_pending(pg, hand):
    hand.FEATURES.append({"id": "final_cut", "title": "Final cut is free"})
    counts = whats_new.sync(pg)
    assert counts["first_run"] is True
    assert _status(pg, "model:grok1.5") == "pending"
    assert _status(pg, "model:grok1.5-lite") == "pending"
    assert _status(pg, "model:kling4") in ("skipped", None)   # a slot may be parked
    assert _status(pg, "look:noir") == "skipped"
    assert _status(pg, "feature:final_cut") == "pending"     # written by hand on purpose
    assert counts["pending"] == 3


def test_a_model_added_later_is_pending_and_one_taken_out_retires(pg, hand, a_new_model):
    whats_new.sync(pg)
    item = a_new_model()
    counts = whats_new.sync(pg)
    assert counts["first_run"] is False
    assert _status(pg, item) == "pending"
    a_new_model.remove()
    whats_new.sync(pg)
    assert _status(pg, item) == "retired"
    a_new_model()                      # put back, never kept: waits again
    whats_new.sync(pg)
    assert _status(pg, item) == "pending"


def test_a_returning_model_that_was_kept_is_live_again(pg, hand, a_new_model):
    whats_new.sync(pg)
    item = a_new_model()
    whats_new.sync(pg)
    _go_live(pg, item)
    a_new_model.remove()
    whats_new.sync(pg)
    a_new_model()
    whats_new.sync(pg)
    assert _status(pg, item) == "live"


def test_a_source_that_cannot_be_read_retires_nothing(pg, hand, monkeypatch):
    whats_new.sync(pg)

    def broken():
        raise RuntimeError("table unreadable")
    monkeypatch.setitem(whats_new.READERS, "model", broken)
    whats_new.sync(pg)
    assert _status(pg, "model:grok1.5") == "pending"


def test_sync_twice_changes_nothing_and_never_raises(pg, hand):
    whats_new.sync(pg)
    again = whats_new.sync(pg)
    assert again["pending"] == 0 and again["retired"] == 0
    assert whats_new.sync("postgresql://nobody@127.0.0.1:1/none") == {}


def test_an_ended_deal_and_a_shipped_coming_soon_item_retire(pg, hand):
    hand.DEALS.append({"id": "launch", "title": "20% off yearly",
                       "starts": "2026-10-01", "ends": "2026-10-20"})
    hand.COMING_SOON.append({"id": "grok", "title": "Grok Imagine", "becomes": "model:grok1.5"})
    whats_new.sync(pg, today=dt.date(2026, 10, 10))
    assert _status(pg, "deal:launch") == "pending"
    whats_new.sync(pg, today=dt.date(2026, 10, 25))
    assert _status(pg, "deal:launch") == "retired"
    assert _status(pg, "soon:grok") == "pending"
    _go_live(pg, "model:grok1.5")
    whats_new.sync(pg)
    assert _status(pg, "soon:grok") == "retired"


def test_a_deal_with_no_dates_or_an_entry_with_no_title_is_left_out(pg, hand):
    hand.DEALS.append({"id": "forever", "title": "Always on"})
    hand.FEATURES.append({"id": "untitled"})
    whats_new.sync(pg)
    assert _status(pg, "deal:forever") is None
    assert _status(pg, "feature:untitled") is None


def test_social_platforms_and_fal_price_changes_are_not_a_source():
    assert set(whats_new.SOURCES) == {"model", "effect", "look", "skill", "feature", "soon", "deal"}


# -- the feed -----------------------------------------------------------------


def test_only_live_tiles_reach_the_feed_new_ones_first(ws, pg, hand):
    hand.FEATURES.append({"id": "old", "title": "Old news", "media": "none"})
    whats_new.sync(pg)
    _go_live(pg, "feature:old", days_ago=40)
    _go_live(pg, "model:grok1.5", days_ago=2)
    out = whats_new.feed(ws[0], "u1", dsn=pg, now=NOW)
    ids = [i["id"] for i in out["items"]]
    assert ids == ["model:grok1.5", "feature:old"]        # grok-lite is still pending
    grok = out["items"][0]
    assert grok["tag"] == "NEW MODEL" and grok["new"] is True and grok["unread"] is True
    assert out["items"][1]["new"] is False
    assert out["unread"] == 2


def test_no_tile_carries_a_price(ws, pg, hand):
    whats_new.sync(pg)
    _go_live(pg, "model:grok1.5")
    text = repr(whats_new.feed(ws[0], "u1", dsn=pg, now=NOW))
    assert "credit" not in text.lower() and "$" not in text


def test_requires_and_a_model_no_longer_offered_hide_a_tile(ws, pg, hand, a_new_model):
    hand.FEATURES.append({"id": "kit", "title": "Brand kits", "requires": "brand_kits"})
    whats_new.sync(pg)
    item = a_new_model()
    whats_new.sync(pg)
    _go_live(pg, "feature:kit")
    _go_live(pg, item)
    assert {i["id"] for i in whats_new.feed(ws[0], "u1", {}, dsn=pg, now=NOW)["items"]} == {item}
    caps = {"brand_kits": True}
    assert "feature:kit" in {i["id"] for i in whats_new.feed(ws[0], "u1", caps, dsn=pg, now=NOW)["items"]}
    a_new_model.remove()               # out of the table, before any sync runs
    assert item not in {i["id"] for i in whats_new.feed(ws[0], "u1", caps, dsn=pg, now=NOW)["items"]}


def test_a_deal_shows_only_inside_its_window(ws, pg, hand):
    hand.DEALS.append({"id": "bf", "title": "Black Friday", "line": "+200 credits on a top-up",
                       "starts": "2026-11-20", "ends": "2026-11-30"})
    whats_new.sync(pg, today=dt.date(2026, 11, 1))
    _go_live(pg, "deal:bf")
    assert whats_new.feed(ws[0], "u1", dsn=pg, now=NOW)["items"] == []
    inside = dt.datetime(2026, 11, 25, tzinfo=dt.timezone.utc)
    [deal] = whats_new.feed(ws[0], "u1", dsn=pg, now=inside)["items"]
    assert deal["tag"] == "DEAL" and deal["ends"] == "2026-11-30"


def test_a_coming_soon_tile_makes_nothing_and_notify_marks_the_shipped_tile(ws, pg, hand):
    hand.COMING_SOON.append({"id": "grok", "title": "Grok Imagine", "eta": "This month",
                             "becomes": "model:grok1.5",
                             "action": {"fill": "make it", "href": "/models"}})
    whats_new.sync(pg)
    _go_live(pg, "soon:grok")
    [soon] = whats_new.feed(ws[0], "u1", dsn=pg, now=NOW)["items"]
    assert soon["tag"] == "COMING SOON" and soon["eta"] == "This month"
    assert soon["action"] == {"href": "/models"}           # never fills the box
    assert whats_new.mark(ws[0], "u1", ["soon:grok"], "notify", dsn=pg) == 1
    assert whats_new.mark(ws[0], "u1", ["model:grok1.5"], "notify", dsn=pg) == 0
    _go_live(pg, "model:grok1.5")
    mine = {i["id"]: i for i in whats_new.feed(ws[0], "u1", dsn=pg, now=NOW)["items"]}
    theirs = {i["id"]: i for i in whats_new.feed(ws[0], "u2", dsn=pg, now=NOW)["items"]}
    assert mine["model:grok1.5"]["you_asked"] is True
    assert theirs["model:grok1.5"]["you_asked"] is False


def test_seen_and_dismissed_are_one_persons_own(ws, pg, hand):
    whats_new.sync(pg)
    _go_live(pg, "model:grok1.5")
    _go_live(pg, "model:grok1.5-lite")
    assert whats_new.mark(ws[0], "u1", ["model:grok1.5", "model:nope"], "seen", dsn=pg) == 1
    assert whats_new.feed(ws[0], "u1", dsn=pg, now=NOW)["unread"] == 1
    assert whats_new.feed(ws[0], "u2", dsn=pg, now=NOW)["unread"] == 2
    assert whats_new.feed(ws[1], "u1", dsn=pg, now=NOW)["unread"] == 2   # another workspace
    whats_new.mark(ws[0], "u1", ["model:grok1.5-lite"], "dismissed", dsn=pg)
    assert [i["id"] for i in whats_new.feed(ws[0], "u1", dsn=pg, now=NOW)["items"]] == ["model:grok1.5"]
    assert len(whats_new.feed(ws[0], "u2", dsn=pg, now=NOW)["items"]) == 2


def test_the_queue_is_what_waits_on_mike(pg, hand):
    whats_new.sync(pg)
    waiting = whats_new.queue(pg, statuses=("pending", "rendering", "review"))
    assert [r["id"] for r in waiting] == ["model:grok1.5", "model:grok1.5-lite"]
    assert waiting[0]["params"]["resolution"] == "720p"
    everything = whats_new.queue(pg)
    assert [r["status"] for r in everything[:2]] == ["pending", "pending"]
    assert {r["status"] for r in everything[2:]} == {"skipped"}


# -- routes -------------------------------------------------------------------


@pytest.fixture
def client(pg, ws, hand, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app import api, auth, whats_new_routes

    monkeypatch.setenv("DATABASE_URL", pg)
    app = FastAPI()
    app.include_router(whats_new_routes.router, prefix="/api")
    app.dependency_overrides[auth.current_account_id] = lambda: ws[0]
    monkeypatch.setattr(auth, "current_user", lambda request: {"id": "u1"})
    monkeypatch.setattr(api, "compute_capabilities", lambda account_id: {})
    whats_new.sync(pg)
    _go_live(pg, "model:grok1.5")
    return TestClient(app)


def test_the_routes_read_and_mark_for_the_signed_in_person(client):
    out = client.get("/api/whats-new").json()
    assert [i["id"] for i in out["items"]] == ["model:grok1.5"] and out["unread"] == 1
    assert client.post("/api/whats-new/seen", json={"ids": ["model:grok1.5"]}).json() == {"marked": 1}
    assert client.get("/api/whats-new").json()["unread"] == 0
    assert client.post("/api/whats-new/model:grok1.5/notify").status_code == 404
    assert client.post("/api/whats-new/model:grok1.5/dismiss").json() == {"marked": 1}
    assert client.get("/api/whats-new").json()["items"] == []


def test_every_route_declares_the_tenant():
    from app import auth, whats_new_routes
    for route in whats_new_routes.router.routes:
        deps = [d.call for d in route.dependant.dependencies]
        assert auth.current_account_id in deps, route.path


# -- the operator's Showcase list (step 2) -------------------------------------


@pytest.fixture
def house(pg, hand, monkeypatch):
    """The house account `phantra` with an owner and a plain member, a
    stranger's workspace, and render jobs that run in the request."""
    from app import jobs
    from src import accounts

    monkeypatch.setenv("DATABASE_URL", pg)
    accounts.init(pg)
    hid = accounts.upsert_account("phantra", "Phantra AI", "#fff", dsn=pg)
    other = accounts.upsert_account("someone", "Someone", "#fff", dsn=pg)
    owner = accounts.create_user("mike@example.com", dsn=pg)
    member = accounts.create_user("crew@example.com", dsn=pg)
    stranger = accounts.create_user("x@example.com", dsn=pg)
    accounts.add_member(hid, owner, "owner", dsn=pg)
    accounts.add_member(hid, member, "member", dsn=pg)
    accounts.add_member(other, stranger, "owner", dsn=pg)
    whats_new.sync(pg)

    def run_now(kind, label, fn, cancellable=False, *, account_id=None):
        job = {"id": "job-1"}
        try:
            fn(job)
        except Exception:
            pass
        return job
    monkeypatch.setattr(jobs, "start", run_now)
    monkeypatch.setattr(jobs, "progress", lambda *a, **k: None)
    return {"id": hid, "other": other, "owner": owner, "member": member, "stranger": stranger}


def _as(house, who, monkeypatch, account="id"):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app import api, auth, whats_new_routes
    app = FastAPI()
    app.include_router(whats_new_routes.router, prefix="/api")
    app.dependency_overrides[auth.current_account_id] = lambda: house[account]
    monkeypatch.setattr(auth, "current_user", lambda request: {"id": house[who]})
    monkeypatch.setattr(api, "compute_capabilities", lambda account_id: {})
    return TestClient(app)


def test_only_the_house_accounts_owners_see_the_list(house, monkeypatch):
    for who, account in (("member", "id"), ("stranger", "other")):
        r = _as(house, who, monkeypatch, account).get("/api/whats-new/showcase")
        assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"
    out = _as(house, "owner", monkeypatch).get("/api/whats-new/showcase").json()
    grok = out["items"][0]
    assert grok["id"] == "model:grok1.5" and grok["status"] == "pending"
    assert isinstance(grok["credits"], int) and grok["credits"] > 0
    assert "usd" not in repr(out)


def _stub_render(monkeypatch, *, ok=True):
    from src import fal, render_assets
    calls = []
    monkeypatch.setattr(fal, "has_key", lambda account_id=None: True)

    def generate(prompt, **kw):
        calls.append(kw)
        if not ok:
            return {"ok": False, "error": "fal said no"}
        return {"ok": True, "asset_id": 77, "media_url": "https://media.example/m/1/renders/g.mp4"}
    monkeypatch.setattr(fal, "generate_from_prompt", generate)
    monkeypatch.setattr(render_assets, "get", lambda id, dsn=None, *, account_id: {
        "id": id, "media_url": "m/1/renders/grok-abc.mp4", "media_kind": "video"})
    return calls


def test_approve_renders_once_on_the_house_account_then_keep_puts_it_live(house, monkeypatch, ws):
    calls = _stub_render(monkeypatch)
    c = _as(house, "owner", monkeypatch)
    price = c.post("/api/whats-new/showcase/model:grok1.5/quote").json()["credits"]
    r = c.post("/api/whats-new/showcase/model:grok1.5/approve", json={"expect_credits": price + 1})
    assert r.status_code == 409 and r.json()["error"]["code"] == "price_changed"
    assert calls == []
    r = c.post("/api/whats-new/showcase/model:grok1.5/approve", json={"expect_credits": price})
    assert r.status_code == 200, r.text
    [kw] = calls
    assert kw["account_id"] == house["id"] and kw["approved"] is True
    assert kw["model"] == "grok1.5" and kw["duration"] == 6 and kw["resolution"] == "720p"
    item = whats_new.get("model:grok1.5")
    assert item["status"] == "review" and item["media"] == "m/1/renders/grok-abc.mp4"
    assert item["gen_id"] == "gen:77" and item["credits_spent"] == price
    again = c.post("/api/whats-new/showcase/model:grok1.5/approve", json={"expect_credits": price})
    assert again.status_code in (400, 409) and len(calls) == 1      # never twice
    assert c.post("/api/whats-new/showcase/model:grok1.5/keep").json()["status"] == "live"
    [tile] = whats_new.feed(ws[0], "u1")["items"]
    assert tile["id"] == "model:grok1.5" and tile["media"]["kind"] == "video"
    assert tile["media"]["url"] and tile["new"] is True


def test_a_failed_render_goes_back_to_waiting_and_says_why(house, monkeypatch):
    _stub_render(monkeypatch, ok=False)
    c = _as(house, "owner", monkeypatch)
    price = c.post("/api/whats-new/showcase/model:grok1.5/quote").json()["credits"]
    c.post("/api/whats-new/showcase/model:grok1.5/approve", json={"expect_credits": price})
    item = whats_new.get("model:grok1.5")
    assert item["status"] == "pending" and item["note"] and item["media"] is None


def test_redo_keeps_the_take_and_skip_restore_round_trip(house, monkeypatch):
    _stub_render(monkeypatch)
    c = _as(house, "owner", monkeypatch)
    price = c.post("/api/whats-new/showcase/model:grok1.5/quote").json()["credits"]
    c.post("/api/whats-new/showcase/model:grok1.5/approve", json={"expect_credits": price})
    c.post("/api/whats-new/showcase/model:grok1.5/keep")
    item = c.post("/api/whats-new/showcase/model:grok1.5/redo").json()
    assert item["status"] == "pending" and item["media"] is None and item["live_at"] is None
    assert item["params"]["takes"] == ["gen:77"]
    assert c.post("/api/whats-new/showcase/model:grok1.5/skip").json()["status"] == "skipped"
    assert c.post("/api/whats-new/showcase/model:grok1.5/keep").status_code == 409
    assert c.post("/api/whats-new/showcase/model:grok1.5/restore").json()["status"] == "pending"


def test_an_effect_takes_a_picked_library_item_and_words_only_tiles_keep_straight(
        house, monkeypatch, pg):
    from src import render_assets
    monkeypatch.setattr(render_assets, "get", lambda id, dsn=None, *, account_id: (
        {"id": id, "media_url": "m/1/renders/look.mp4", "media_kind": "video"}
        if account_id == house["id"] and id == 5 else None))
    with db.connect(pg) as conn:
        conn.execute("UPDATE showcase_items SET status = 'pending' WHERE id IN ('look:noir', 'skill:ad')")
    c = _as(house, "owner", monkeypatch)
    assert c.post("/api/whats-new/showcase/look:noir/approve",
                  json={"expect_credits": 0}).status_code == 400        # nothing to render
    assert c.post("/api/whats-new/showcase/look:noir/pick", json={"asset": "gen:9"}).status_code == 400
    picked = c.post("/api/whats-new/showcase/look:noir/pick", json={"asset": "gen:5"}).json()
    assert picked["status"] == "review" and picked["media_type"] == "video"
    assert c.post("/api/whats-new/showcase/skill:ad/keep").json()["status"] == "live"


def test_edit_changes_words_and_the_render_pick_before_it_goes_live(house, monkeypatch):
    c = _as(house, "owner", monkeypatch)
    out = c.put("/api/whats-new/showcase/model:grok1.5",
                json={"title": "Grok is here", "seconds": 10, "resolution": "1080p"}).json()
    assert out["title"] == "Grok is here" and out["params"]["seconds"] == 10
    ten = out["credits"]
    six = c.put("/api/whats-new/showcase/model:grok1.5", json={"seconds": 6}).json()["credits"]
    assert ten > six
    bad = c.put("/api/whats-new/showcase/model:grok1.5", json={"resolution": "4k"})
    assert bad.status_code == 200 and bad.json()["credits"] is None   # priced as refused, said
    assert c.put("/api/whats-new/showcase/model:grok1.5", json={"size": "huge"}).status_code == 400


def test_a_render_a_deploy_killed_goes_back_to_waiting(house, pg):
    whats_new.start_render("model:grok1.5", pg)
    with db.connect(pg) as conn:
        conn.execute("UPDATE showcase_items SET updated_at = now() - interval '2 hours'"
                     " WHERE id = 'model:grok1.5'")
    assert whats_new.sync(pg)["interrupted"] == 1
    item = whats_new.get("model:grok1.5", pg)
    assert item["status"] == "pending" and "interrupted" in item["note"]


def test_a_table_from_step_one_grows_the_columns_step_two_reads(pg):
    with db.connect(pg) as conn:
        conn.execute("CREATE TABLE showcase_items (id TEXT PRIMARY KEY, source TEXT NOT NULL,"
                     " key TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending')")
    whats_new.init(pg)
    with db.connect(pg) as conn:
        cols = db.columns(conn, "showcase_items")
    assert {"media_type", "media_account", "note"} <= set(cols)

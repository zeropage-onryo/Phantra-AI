"""
Settings -> Usage: the credit history (2026-10-11, src/credit_history.py
and GET /api/billing/history; docs/tasks/task-settings-page.md, task 4).

The ledger is the record; this is how a customer reads it. What is held:

- a hold that drew on two lots is ONE line, and so is a settle that gave
  some back to two
- every line says what the credit was for, in words: the model and length
  of a clip, the model of a still, the kind of lot
- `balance_after` is what the ledger said the balance was at that moment
- the history is paged by id, newest first, with nothing repeated
- one account never reads another's
- the answer is in CREDITS: no key and no value names a dollar, and the
  module never selects a provider's cost
"""

import inspect
import json

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.main import app
from src import accounts, credit_history, db, generative, ledger, preprod, render_assets
from src.shot import Shot

client = TestClient(app)


@pytest.fixture(autouse=True)
def signed_in(monkeypatch):
    stub = {"id": "u-1", "email": "test@example.com", "display_name": "Test"}
    monkeypatch.setattr(auth, "current_user", lambda request: stub)


@pytest.fixture
def book(pg, monkeypatch):
    """Two accounts and every table a line reads from."""
    monkeypatch.setenv("DATABASE_URL", pg)
    accounts.init(pg)
    preprod.init(pg)
    generative.init(pg)
    render_assets.init(pg)
    ledger.init(pg)
    a = accounts.upsert_account("north", "North", dsn=pg)
    b = accounts.upsert_account("south", "South", dsn=pg)
    app.dependency_overrides[auth.current_account_id] = lambda: a
    yield {"dsn": pg, "a": a, "b": b}
    app.dependency_overrides.pop(auth.current_account_id, None)


def _render(dsn, account_id, tool, params, *, ref=None, asset=None, concept=None):
    """A generations row as an adapter writes it (the ledger ref in its
    params), and optionally its row on the Assets wall."""
    shot_id = generative.add_shot(Shot(subject="a bike", action="idles"), dsn=dsn, account_id=account_id)
    params = {**params, **(ledger.ref_params(ref) if ref else {}),
              **({"concept_id": concept} if concept else {})}
    gen = generative.record_generation(shot_id, tool, "a prompt", params=params,
                                       cost_usd=0.36, dsn=dsn, account_id=account_id)
    if asset:
        with db.connect(dsn) as conn:
            conn.execute(
                "INSERT INTO generated_assets (created_at, generation_id, tool, model, media_kind, "
                "prompt, media_url, concept_id, account_id) VALUES ('t', %s, %s, %s, %s, 'p', 'u', %s, %s)",
                (gen, tool, params.get("model") or "", asset, concept, account_id))
    return gen


def _concept(dsn, account_id, title):
    with db.connect(dsn) as conn:
        return conn.execute(
            "INSERT INTO shoot_concepts (created_at, title, shots_json, account_id) "
            "VALUES ('t', %s, '[]', %s) RETURNING id", (title, account_id)).fetchone()["id"]


def _lines(dsn, account_id, **kw):
    return credit_history.page(account_id, dsn=dsn, **kw)["items"]


# --------------------------------------------------------------------------
# one line per movement
# --------------------------------------------------------------------------

def test_a_hold_that_drew_on_two_lots_is_one_line(book):
    dsn, a = book["dsn"], book["a"]
    ledger.grant(a, 50, "promo", expires_at="2099-01-01T00:00:00+00:00", dsn=dsn)
    ledger.grant(a, 100, "purchase", expires_at="2099-06-01T00:00:00+00:00", dsn=dsn)
    ledger.hold(a, 87, ref="c1-s1-x.mp4", provider="fal", dsn=dsn)
    # the ledger wrote two hold entries (50 from the first lot, 37 from the second)
    assert [e["delta"] for e in ledger.entries(a, dsn) if e["kind"] == "hold"] == [-50, -37]
    lines = _lines(dsn, a)
    assert [(line["kind"], line["credits"], line["balance_after"]) for line in lines] == [
        ("hold", -87, 63), ("grant", 100, 150), ("grant", 50, 50)]


def test_a_settle_that_gives_back_to_two_lots_is_one_line(book):
    dsn, a = book["dsn"], book["a"]
    ledger.grant(a, 50, "promo", expires_at="2099-01-01T00:00:00+00:00", dsn=dsn)
    ledger.grant(a, 100, "purchase", expires_at="2099-06-01T00:00:00+00:00", dsn=dsn)
    hold = ledger.hold(a, 87, ref="c1-s1-x.mp4", provider="fal", dsn=dsn)
    ledger.settle(hold, credits=40, dsn=dsn)        # 47 go back: 37 to one lot, 10 to the other
    assert len([e for e in ledger.entries(a, dsn) if e["kind"] == "settle"]) == 2
    top = _lines(dsn, a)[0]
    assert (top["kind"], top["credits"], top["balance_after"]) == ("settle", 47, 110)
    assert top["balance_after"] == ledger.available(a, dsn)


def test_the_balance_after_each_line_is_the_ledgers_own_running_figure(book):
    dsn, a = book["dsn"], book["a"]
    ledger.grant(a, 500, "subscription", dsn=dsn)
    first = ledger.hold(a, 87, ref="one.mp4", provider="fal", dsn=dsn)
    second = ledger.hold(a, 233, ref="two.mp4", provider="fal", dsn=dsn)
    ledger.release(first, "the provider refused it", dsn=dsn)
    ledger.settle(second, credits=233, dsn=dsn)
    lines = _lines(dsn, a)
    assert [(line["kind"], line["credits"], line["balance_after"]) for line in lines] == [
        ("settle", 0, 267), ("release", 87, 267), ("hold", -233, 180), ("hold", -87, 413),
        ("grant", 500, 500)]
    assert lines[0]["balance_after"] == ledger.available(a, dsn)


# --------------------------------------------------------------------------
# what a line says
# --------------------------------------------------------------------------

def test_a_clip_says_its_model_and_length_and_opens_its_scene(book):
    dsn, a = book["dsn"], book["a"]
    scene = _concept(dsn, a, "Neon City Ascent")
    ledger.grant(a, 500, "subscription", dsn=dsn)
    hold = ledger.hold(a, 87, ref="c9-s1-x.mp4", provider="fal", dsn=dsn)
    gen = _render(dsn, a, "ltx", {"model": "ltx2.3", "duration": 6}, ref="c9-s1-x.mp4",
                  asset="video", concept=scene)
    ledger.settle(hold, credits=87, generation_id=gen, dsn=dsn)
    settle, held = _lines(dsn, a)[:2]
    for line in (settle, held):         # the settle by its generation id, the hold by its ref
        assert line["what"] == "LTX 2.3 clip, 6s"
        assert (line["group"], line["label"]) == ("render", "LTX 2.3")
        assert line["ref"] == {"kind": "scene", "id": scene, "title": "Neon City Ascent"}


def test_a_shot_of_a_timed_scene_says_which_shot(book):
    dsn, a = book["dsn"], book["a"]
    ledger.grant(a, 500, "subscription", dsn=dsn)
    ledger.hold(a, 101, ref="c9-s1-p2-x.mp4", provider="fal", dsn=dsn)
    _render(dsn, a, "kling", {"model": "kling3-turbo-pro", "duration": 5, "part": 2}, ref="c9-s1-p2-x.mp4")
    assert _lines(dsn, a)[0]["what"] == "Kling 3 Turbo Pro clip, 5s, shot 2"


def test_stills_sheets_and_effects_say_what_they_were(book):
    dsn, a = book["dsn"], book["a"]
    ledger.grant(a, 500, "subscription", dsn=dsn)
    cases = [
        ("nano", {"model": "gemini-3-pro-image-preview"}, "Still · Nano Banana Pro", "still", "Nano Banana Pro"),
        ("nano", {"model": "gemini-2.5-flash-image"}, "Still · Nano Banana", "still", "Nano Banana"),
        ("nano", {"model": "gemini-3-pro-image-preview", "source": "element_sheet"},
         "Element sheet · Nano Banana Pro", "still", "Nano Banana Pro"),
        ("fal", {"model": "flux-pro1.1"}, "Still · FLUX 1.1 Pro", "still", "FLUX 1.1 Pro"),
        ("fal", {"model": "remove-background", "effect": "remove-background"},
         "Effect · Remove background", "effect", "Remove background"),
    ]
    for n, (tool, params, *_rest) in enumerate(cases):
        ledger.hold(a, 10, ref=f"r{n}.jpg", provider="fal", dsn=dsn)
        _render(dsn, a, tool, params, ref=f"r{n}.jpg")
    lines = list(reversed(_lines(dsn, a)[:len(cases)]))
    assert [(line["what"], line["group"], line["label"]) for line in lines] == [c[2:] for c in cases]


def test_a_hold_with_no_render_row_says_what_the_hold_shows(book):
    dsn, a = book["dsn"], book["a"]
    ledger.grant(a, 500, "subscription", dsn=dsn)
    ledger.hold(a, 87, ref="c1-s1-x.mp4", provider="fal", dsn=dsn)
    ledger.hold(a, 10, ref="flux-x.jpg", provider="fal", dsn=dsn)
    ledger.hold(a, 33, ref="sheet-thing", provider="nano", dsn=dsn)
    ledger.hold(a, 20, ref="who-knows", provider="fal", dsn=dsn)
    lines = _lines(dsn, a)[:4]
    assert [(line["what"], line["group"], line["ref"]) for line in lines] == [
        ("Render", "render", None), ("Still", "still", None), ("Still", "still", None),
        ("Clip", "render", None)]


def test_a_render_with_no_scene_opens_on_the_assets_wall_unless_it_was_removed(book):
    dsn, a = book["dsn"], book["a"]
    ledger.grant(a, 500, "subscription", dsn=dsn)
    for ref in ("kept.jpg", "removed.jpg", "unbanked.jpg"):
        ledger.hold(a, 10, ref=ref, provider="fal", dsn=dsn)
    kept = _render(dsn, a, "fal", {"model": "flux-pro1.1"}, ref="kept.jpg", asset="image")
    removed = _render(dsn, a, "fal", {"model": "flux-pro1.1"}, ref="removed.jpg", asset="image")
    _render(dsn, a, "fal", {"model": "flux-pro1.1"}, ref="unbanked.jpg")
    with db.connect(dsn) as conn:
        conn.execute("UPDATE generated_assets SET deleted_at = 't' WHERE generation_id = %s "
                     "AND account_id = %s", (removed, a))
        kept_asset = conn.execute("SELECT id FROM generated_assets WHERE generation_id = %s "
                                  "AND account_id = %s", (kept, a)).fetchone()["id"]
    by_what = {line["id"]: line["ref"] for line in _lines(dsn, a)[:3]}
    assert list(by_what.values()) == [None, None, {"kind": "render", "id": kept_asset}]


def test_a_scene_that_is_gone_is_not_linked(book):
    dsn, a = book["dsn"], book["a"]
    ledger.grant(a, 500, "subscription", dsn=dsn)
    ledger.hold(a, 87, ref="c404-s1-x.mp4", provider="fal", dsn=dsn)
    _render(dsn, a, "ltx", {"model": "ltx2.3", "duration": 6}, ref="c404-s1-x.mp4", concept=404)
    assert _lines(dsn, a)[0]["ref"] is None


def test_grants_and_expiries_say_which_credit(book):
    dsn, a = book["dsn"], book["a"]
    ledger.grant(a, 100, "promo", source_ref=f"signup:{a}", dsn=dsn)
    ledger.grant(a, 3500, "subscription", source_ref="in_1", note="stripe invoice in_1 (creator)", dsn=dsn)
    ledger.grant(a, 9500, "subscription", source_ref="in_2:m2", note="stripe yearly in_2 month 2/12", dsn=dsn)
    ledger.grant(a, 750, "purchase", source_ref="pi_1", dsn=dsn)
    ledger.grant(a, 40, "promo", source_ref="old", granted_at="2020-01-01T00:00:00+00:00",
                 expires_at="2020-03-01T00:00:00+00:00", dsn=dsn)
    ledger.expire_due(a, dsn=dsn)
    lines = _lines(dsn, a)
    assert [(line["kind"], line["what"], line["credits"]) for line in lines] == [
        ("expire", "Trial credits expired", -40),
        ("grant", "Trial credits", 40),
        ("grant", "Top-up", 750),
        ("grant", "Monthly credits", 9500),
        ("grant", "Monthly credits · Creator", 3500),
        ("grant", "Trial credits", 100),
    ]
    assert {line["group"] for line in lines} == {"grant"}
    assert all(line["ref"] is None for line in lines)


# --------------------------------------------------------------------------
# paging
# --------------------------------------------------------------------------

def test_the_history_pages_by_id_with_nothing_repeated_or_dropped(book):
    dsn, a = book["dsn"], book["a"]
    ledger.grant(a, 1000, "subscription", dsn=dsn)
    for n in range(6):
        ledger.hold(a, 10, ref=f"r{n}.jpg", provider="fal", dsn=dsn)
    seen, before, pages = [], None, 0
    while True:
        answer = credit_history.page(a, before=before, limit=3, dsn=dsn)
        seen += [line["id"] for line in answer["items"]]
        pages += 1
        before = answer["next"]
        if before is None:
            break
    assert pages == 3 and len(seen) == 7
    assert seen == sorted(set(seen), reverse=True)
    # a full last page is still the last page: no empty page after it
    assert credit_history.page(a, limit=7, dsn=dsn)["next"] is None
    # a limit is bounded, never an error
    assert len(credit_history.page(a, limit=0, dsn=dsn)["items"]) == 1
    assert len(credit_history.page(a, limit=10_000, dsn=dsn)["items"]) == 7


# --------------------------------------------------------------------------
# the summary
# --------------------------------------------------------------------------

def test_the_summary_counts_a_render_once_at_what_it_net_cost_on_the_day_it_was_held(book, monkeypatch):
    from datetime import datetime, timezone
    dsn, a = book["dsn"], book["a"]
    now = datetime(2026, 10, 11, 12, tzinfo=timezone.utc)
    clock = {"at": "2026-09-01T00:00:00+00:00"}
    monkeypatch.setattr(ledger, "_now", lambda: clock["at"])
    ledger.grant(a, 5000, "subscription", expires_at="2099-01-01T00:00:00+00:00", dsn=dsn)

    def held(day, credits, ref, tool=None, params=None):
        clock["at"] = f"{day}T09:00:00+00:00"
        hold = ledger.hold(a, credits, ref=ref, provider="fal", dsn=dsn)
        if tool:
            _render(dsn, a, tool, params, ref=ref)
        return hold

    settled = held("2026-10-08", 87, "a.mp4", "ltx", {"model": "ltx2.3", "duration": 6})
    cheaper = held("2026-10-08", 100, "b.mp4", "ltx", {"model": "ltx2.3", "duration": 6})
    refused = held("2026-10-09", 233, "c.mp4", "seedance", {"model": "seedance2-fast", "duration": 5})
    held("2026-10-10", 33, "d.jpg", "nano", {"model": "gemini-3-pro-image-preview"})   # still in flight
    held("2026-09-01", 500, "old.mp4", "ltx", {"model": "ltx2.3", "duration": 6})      # before the window
    clock["at"] = "2026-10-10T10:00:00+00:00"      # all three resolved two days after the first hold
    ledger.settle(settled, credits=87, dsn=dsn)
    ledger.settle(cheaper, credits=60, dsn=dsn)
    ledger.release(refused, "the provider refused it", dsn=dsn)

    out = credit_history.summary(a, now=now, dsn=dsn)
    assert out["window_days"] == 30 and len(out["days"]) == 30
    assert out["days"][0]["day"] == "2026-09-12" and out["days"][-1]["day"] == "2026-10-11"
    spent = {d["day"]: d["credits"] for d in out["days"] if d["credits"]}
    # the two clips on the day they were held, the released one nowhere,
    # the still in flight at what it holds
    assert spent == {"2026-10-08": 147, "2026-10-10": 33}
    assert out["spent"] == 180
    assert out["totals"] == [
        {"label": "LTX 2.3", "group": "render", "credits": 147, "count": 2},
        {"label": "Nano Banana Pro", "group": "still", "credits": 33, "count": 1},
    ]


def test_an_account_with_no_history_has_an_empty_one(book):
    answer = client.get("/api/billing/history").json()
    assert answer["items"] == [] and answer["next"] is None
    assert answer["summary"]["spent"] == 0 and answer["summary"]["totals"] == []
    assert len(answer["summary"]["days"]) == 30


# --------------------------------------------------------------------------
# the route
# --------------------------------------------------------------------------

def _two_books(book):
    dsn, a, b = book["dsn"], book["a"], book["b"]
    for owner, title, ref in ((a, "North's scene", "north.mp4"), (b, "South's scene", "south.mp4")):
        scene = _concept(dsn, owner, title)
        ledger.grant(owner, 500, "subscription", dsn=dsn)
        hold = ledger.hold(owner, 87, ref=ref, provider="fal", dsn=dsn)
        gen = _render(dsn, owner, "ltx", {"model": "ltx2.3", "duration": 6}, ref=ref,
                      asset="video", concept=scene)
        ledger.settle(hold, credits=87, generation_id=gen, dsn=dsn)
    return dsn, a, b


def test_one_account_never_reads_anothers_history(book):
    _dsn, a, b = _two_books(book)
    for me, mine, theirs in ((a, "North's scene", "South's scene"), (b, "South's scene", "North's scene")):
        app.dependency_overrides[auth.current_account_id] = lambda me=me: me
        answer = client.get("/api/billing/history").json()
        text = json.dumps(answer)
        assert mine in text and theirs not in text
        assert [line["kind"] for line in answer["items"]] == ["settle", "hold", "grant"]
        assert answer["items"][0]["balance_after"] == 413
        assert answer["summary"]["spent"] == 87


def test_another_accounts_render_with_the_same_ref_is_not_borrowed(book):
    """A ref is a file name, and two accounts can hold one of the same
    name: the line is described from the caller's own rows or not at all."""
    dsn, a, b = book["dsn"], book["a"], book["b"]
    ledger.grant(a, 500, "subscription", dsn=dsn)
    ledger.hold(a, 87, ref="same.mp4", provider="fal", dsn=dsn)
    _render(dsn, b, "veo3.1" if "veo3.1" in generative.LOG_TOOLS else "kling",
            {"model": "kling3-turbo-pro", "duration": 10}, ref="same.mp4")
    assert _lines(dsn, a)[0]["what"] == "Clip"


def test_the_history_is_in_credits_and_names_no_dollar(book):
    _two_books(book)
    answer = client.get("/api/billing/history").json()
    assert answer["items"], "nothing to check"
    text = json.dumps(answer).lower()
    for word in ("usd", "$", "cost", "dollar", "0.36"):
        assert word not in text, word
    assert set(answer["items"][0]) == {
        "id", "at", "kind", "credits", "what", "group", "label", "ref", "balance_after"}
    # and the module cannot leak one: it never names the provider's price
    code = inspect.getsource(credit_history).replace(credit_history.__doc__, "")
    assert "usd" not in code.lower()


def test_the_first_page_carries_the_summary_and_later_pages_do_not(book):
    dsn, a = book["dsn"], book["a"]
    ledger.grant(a, 1000, "subscription", dsn=dsn)
    for n in range(3):
        ledger.hold(a, 10, ref=f"r{n}.jpg", provider="fal", dsn=dsn)
    first = client.get("/api/billing/history", params={"limit": 2}).json()
    assert "summary" in first and first["next"] is not None
    later = client.get("/api/billing/history", params={"limit": 2, "before": first["next"]}).json()
    assert "summary" not in later and len(later["items"]) == 2 and later["next"] is None
    assert client.get("/api/billing/history", params={"before": 0}).status_code == 400


def test_every_page_says_whose_history_it_is(book, monkeypatch):
    """The history is the caller's FIRST workspace's whichever one is open
    (auth.current_account_id); the answer names it so Usage can say so
    when another workspace is open."""
    dsn, a, b = _two_books(book)
    ledger.hold(a, 10, ref="still.jpg", provider="fal", dsn=dsn)

    # the suite's usual caller is in no workspace: nothing to name
    assert client.get("/api/billing/history").json()["account"] is None

    ada = accounts.create_user("ada@north.example", "Ada", claimed=True, dsn=dsn)
    accounts.add_member(a, ada, role="owner", dsn=dsn)
    accounts.add_member(b, ada, role="member", dsn=dsn)
    row = accounts.get_user(ada, dsn=dsn)
    monkeypatch.setattr(auth, "current_user", lambda request: row)
    # ABOUT who the caller is: the real gate runs
    app.dependency_overrides.pop(auth.current_account_id, None)
    try:
        client.cookies.set("brand", "south")              # South is open; North is where the credits are
        first = client.get("/api/billing/history", params={"limit": 2}).json()
        later = client.get("/api/billing/history", params={"limit": 2, "before": first["next"]}).json()
        for answer in (first, later):
            assert answer["account"] == {"id": a, "label": "North"}
        text = json.dumps([first, later])
        assert "North's scene" in text and "South's scene" not in text
    finally:
        client.cookies.clear()


def test_the_route_refuses_a_member_of_nothing(book):
    app.dependency_overrides[auth.current_account_id] = lambda: None
    assert client.get("/api/billing/history").status_code == 403

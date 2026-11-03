"""
Phantra Creators (2026-11-03, src/creators.py + app/creator_routes.py).

The by-application program beside the open affiliate link. Guards:
- an application needs the terms box, a full https link and a line about the
  work; each refusal carries a code the page can show
- one application per account: applying again returns the first, untouched
- an application waits for Mike (pending) until the CLI decides it
- the route never tells the page the review note
"""
import pytest
from fastapi.testclient import TestClient

from app import auth
from app.main import app
from src import accounts, creators, db

client = TestClient(app)
WORK = "Short films shot on a phone, cut and graded in Resolve."


@pytest.fixture(autouse=True)
def signed_in(monkeypatch):
    stub = {"id": 1, "email": "test@example.com", "display_name": "Test"}
    monkeypatch.setattr(auth, "current_user", lambda request: stub)
    monkeypatch.setattr(
        auth, "current_account",
        lambda request, user=None: {"slug": "phantra", "display_name": "Phantra AI"})


@pytest.fixture
def world(pg, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", pg)
    accounts.init(pg)
    creators.init(pg)
    return pg


def make_account(dsn, slug):
    uid = f"u-{slug}"
    with db.connect(dsn) as conn:
        conn.execute("INSERT INTO users (id, created_at, email) VALUES (%s, 'now', %s) "
                     "ON CONFLICT DO NOTHING", (uid, f"{slug}@example.com"))
        acct = conn.execute(
            "INSERT INTO accounts (created_at, slug, display_name) VALUES ('now', %s, %s) "
            "RETURNING id", (slug, slug)).fetchone()["id"]
        conn.execute("INSERT INTO account_members (account_id, user_id) VALUES (%s, %s)",
                     (acct, uid))
    return int(acct)


def test_an_application_is_recorded_and_waits_for_review(world):
    acct = make_account(world, "ana")
    r = creators.apply(acct, channel_url="https://youtube.com/@ana", what_you_make=WORK,
                       accept_terms=True, full_name="Ana Ruiz", country="Spain", dsn=world)
    assert r["status"] == "pending"
    assert creators.get(acct, dsn=world)["status"] == "pending"


def test_each_refusal_has_a_code(world):
    acct = make_account(world, "ben")
    bad = [
        (dict(channel_url="https://youtube.com/@b", what_you_make=WORK, accept_terms=False), "terms_required"),
        (dict(channel_url="", what_you_make=WORK, accept_terms=True), "channel_required"),
        (dict(channel_url="nope", what_you_make=WORK, accept_terms=True), "bad_channel"),
        (dict(channel_url="https://youtube.com/@b", what_you_make="films", accept_terms=True), "work_required"),
    ]
    for kwargs, code in bad:
        with pytest.raises(creators.CreatorError) as e:
            creators.apply(acct, dsn=world, **kwargs)
        assert e.value.code == code
    assert creators.get(acct, dsn=world)["status"] is None


def test_applying_twice_keeps_the_first(world):
    acct = make_account(world, "cy")
    creators.apply(acct, channel_url="https://youtube.com/@cy", what_you_make=WORK,
                   accept_terms=True, dsn=world)
    creators.apply(acct, channel_url="https://youtube.com/@other", what_you_make=WORK + " More.",
                   accept_terms=True, dsn=world)
    rows = creators.listing(dsn=world)
    assert len(rows) == 1 and rows[0]["channel_url"] == "https://youtube.com/@cy"


def test_mike_decides_by_slug(world):
    acct = make_account(world, "dee")
    creators.apply(acct, channel_url="https://youtube.com/@dee", what_you_make=WORK,
                   accept_terms=True, dsn=world)
    creators.decide("dee", "approved", note="strong grade", dsn=world)
    assert creators.get(acct, dsn=world) == {
        "status": "approved", "applied_at": creators.get(acct, dsn=world)["applied_at"]}
    assert [r["status"] for r in creators.listing("approved", dsn=world)] == ["approved"]
    with pytest.raises(creators.CreatorError):
        creators.decide("nobody", "approved", dsn=world)


def test_routes_apply_and_report_status(world):
    me = make_account(world, "eli")
    app.dependency_overrides[auth.current_account_id] = lambda: me
    try:
        assert client.get("/api/creators/me").json() == {"status": None}
        r = client.post("/api/creators/apply", json={
            "channel_url": "https://instagram.com/eli", "what_you_make": WORK, "accept_terms": True})
        assert r.status_code == 200 and r.json()["status"] == "pending"
        assert "note" not in r.json()
        assert client.get("/api/creators/me").json()["status"] == "pending"
    finally:
        app.dependency_overrides.pop(auth.current_account_id, None)


def test_a_bad_application_is_a_400_with_a_code(world):
    me = make_account(world, "fay")
    app.dependency_overrides[auth.current_account_id] = lambda: me
    try:
        r = client.post("/api/creators/apply", json={
            "channel_url": "nope", "what_you_make": WORK, "accept_terms": True})
        assert r.status_code == 400 and r.json()["error"]["code"] == "bad_channel"
    finally:
        app.dependency_overrides.pop(auth.current_account_id, None)

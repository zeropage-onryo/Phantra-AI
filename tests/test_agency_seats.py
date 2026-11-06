"""Seats on the Agency plan (2026-11-03, docs/tasks/task-agency-plan.md).

An owner invites teammates from Settings -> Workspace, up to the plan's
seats; below Agency there are none to give. A teammate lands in the
workspace on their first sign-in, and the workspace they have open is the
one their work goes to.
"""
import pytest
from fastapi.testclient import TestClient

from app import auth
from app.main import app
from src import accounts, db, pricing

client = TestClient(app)


@pytest.fixture
def agency(pg, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", pg)
    accounts.init(pg)
    accounts.seed("owner@example.com", dsn=pg)
    with db.connect(pg) as conn:
        acct = int(conn.execute("SELECT id FROM accounts WHERE slug = 'phantra'").fetchone()["id"])
        owner = str(conn.execute("SELECT id FROM users WHERE email = 'owner@example.com'")
                    .fetchone()["id"])
    who = {"user": {"id": owner, "email": "owner@example.com"}}
    monkeypatch.setattr(auth, "current_user", lambda request: who["user"])
    app.dependency_overrides[auth.current_account_id] = lambda: acct
    yield {"dsn": pg, "account_id": acct, "owner": owner, "who": who}
    app.dependency_overrides.pop(auth.current_account_id, None)


def test_below_agency_there_is_no_seat_to_give(agency):
    accounts.set_plan(agency["account_id"], "studio")
    r = client.post("/api/account/members", json={"email": "pal@example.com"})
    assert r.status_code == 402 and r.json()["error"]["code"] == "no_seats"
    page = client.get("/api/account/members").json()
    assert page["seats"] == 1 and page["can_invite"] is False


def test_an_owner_fills_the_agency_seats_and_no_more(agency):
    acct = agency["account_id"]
    accounts.set_plan(acct, "agency")
    seats = pricing.PLANS["agency"].seats
    for n in range(1, seats):
        r = client.post("/api/account/members", json={"email": f"Pal{n}@Example.com "})
        assert r.status_code == 200, r.text
        assert r.json()["email"] == f"pal{n}@example.com" and r.json()["used"] == n + 1
    page = client.get("/api/account/members").json()
    assert page["seats"] == seats == page["used"] and page["can_invite"] is True
    # an invite sits unclaimed until they sign in with that address
    invited = [m for m in page["members"] if m["role"] == "member"]
    assert len(invited) == seats - 1 and not any(m["claimed"] for m in invited)
    full = client.post("/api/account/members", json={"email": "late@example.com"})
    assert full.status_code == 409 and full.json()["error"]["code"] == "seats_full"
    again = client.post("/api/account/members", json={"email": "pal1@example.com"})
    assert again.status_code == 409 and again.json()["error"]["code"] == "already_member"
    assert client.post("/api/account/members", json={"email": "nope"}).status_code == 400
    # removing one frees the seat; the owner is never removed
    pal = accounts.get_user_by_email("pal1@example.com", dsn=agency["dsn"])
    assert client.delete(f"/api/account/members/{pal['id']}").json() == {"ok": True}
    assert client.delete(f"/api/account/members/{agency['owner']}").status_code == 404
    assert client.post("/api/account/members", json={"email": "late@example.com"}).status_code == 200


def test_an_existing_user_joins_beside_their_own_workspace(agency):
    acct, dsn = agency["account_id"], agency["dsn"]
    accounts.set_plan(acct, "agency")
    theirs = accounts.upsert_account("their-own", "Their own", "#fff", dsn=dsn)
    uid = accounts.create_user("solo@example.com", dsn=dsn)
    accounts.add_member(theirs, uid, dsn=dsn)
    r = client.post("/api/account/members", json={"email": "solo@example.com"})
    assert r.status_code == 200 and r.json()["joined_existing_user"] is True
    roles = {m["slug"]: m["role"] for m in accounts.memberships(uid, dsn=dsn)}
    assert roles == {"their-own": "owner", "phantra": "member"}


def test_only_an_owner_invites_or_removes(agency, monkeypatch):
    acct, dsn = agency["account_id"], agency["dsn"]
    accounts.set_plan(acct, "agency")
    client.post("/api/account/members", json={"email": "pal@example.com"})
    pal = accounts.get_user_by_email("pal@example.com", dsn=dsn)
    agency["who"]["user"] = {"id": str(pal["id"]), "email": "pal@example.com"}
    r = client.post("/api/account/members", json={"email": "x@example.com"})
    assert r.status_code == 403 and r.json()["error"]["code"] == "not_owner"
    assert client.delete(f"/api/account/members/{agency['owner']}").status_code == 403
    assert client.get("/api/account/members").json()["can_invite"] is False


def test_two_invites_at_once_cannot_both_take_the_last_seat(agency):
    import threading
    acct, dsn = agency["account_id"], agency["dsn"]
    accounts.set_plan(acct, "agency")
    for n in range(pricing.PLANS["agency"].seats - 2):
        accounts.add_teammate(acct, f"p{n}@example.com", dsn=dsn)
    outcomes = []

    def go(email):
        try:
            accounts.add_teammate(acct, email, dsn=dsn)
            outcomes.append("ok")
        except ValueError as e:
            outcomes.append(e.args[0])

    threads = [threading.Thread(target=go, args=(f"race{i}@example.com",)) for i in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    assert sorted(outcomes) == ["ok", "seats_full"]
    assert len(accounts.members_of(acct, dsn=dsn)) == pricing.PLANS["agency"].seats

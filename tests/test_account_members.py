"""
Settings -> Workspace: who is in the workspace you have open
(GET /api/account/members, 2026-10-11; docs/tasks/task-settings-page.md,
task 5). Read only. What is held:

- the list is the ACTIVE workspace's (the one /api/me calls `account`),
  and only an account the caller really belongs to can be active: the
  brand cookie cannot point the route at somebody else's workspace
- an owner sees every address; a member sees names, and no address but
  their own -- not even the front half of one
- somebody invited who has not signed in yet is marked, not hidden
- a signed-in person in no workspace is refused
"""

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.main import app
from src import accounts

client = TestClient(app)


@pytest.fixture
def people(pg, monkeypatch):
    """Two workspaces. North: Ada owns it; Ben and (not signed in yet)
    Cy are members. South: Dee owns it, and Ada is a MEMBER there."""
    monkeypatch.setenv("DATABASE_URL", pg)
    # the suite pins every route to the unowned pool (conftest); these
    # tests are ABOUT who the caller is, so the real gate runs
    app.dependency_overrides.pop(auth.current_account_id, None)
    accounts.init(pg)
    north = accounts.upsert_account("north", "North Films", "#111111", dsn=pg)
    south = accounts.upsert_account("south", "South Co", dsn=pg)
    ada = accounts.create_user("ada@north.example", "Ada", claimed=True, dsn=pg)
    ben = accounts.create_user("ben@north.example", "Ben", claimed=True, dsn=pg)
    cy = accounts.create_user("cy.quiet@north.example", dsn=pg)            # invited: no name, never signed in
    dee = accounts.create_user("dee@south.example", "Dee", claimed=True, dsn=pg)
    eve = accounts.create_user("eve@nowhere.example", "Eve", claimed=True, dsn=pg)   # in no workspace
    accounts.add_member(north, ada, role="owner", dsn=pg)
    accounts.add_member(north, ben, role="member", dsn=pg)
    accounts.add_member(north, cy, role="member", dsn=pg)
    accounts.add_member(south, dee, role="owner", dsn=pg)
    accounts.add_member(south, ada, role="member", dsn=pg)
    ids = {"ada": ada, "ben": ben, "cy": cy, "dee": dee, "eve": eve}

    def sign_in(who, brand=None):
        row = accounts.get_user(ids[who], dsn=pg)
        monkeypatch.setattr(auth, "current_user", lambda request: row)
        client.cookies.clear()
        if brand:
            client.cookies.set("brand", brand)

    yield sign_in
    client.cookies.clear()


def _members():
    answer = client.get("/api/account/members")
    assert answer.status_code == 200, answer.text
    return answer.json()


def test_an_owner_sees_everyone_and_their_addresses(people):
    people("ada", brand="north")
    out = _members()
    assert out["account"]["label"] == "North Films" and out["account"]["slug"] == "north"
    assert out["role"] == "owner" and out["can_see_emails"] is True
    assert [(m["name"], m["email"], m["role"], m["claimed"], m["you"]) for m in out["members"]] == [
        ("Ada", "ada@north.example", "owner", True, True),          # owners first
        ("Ben", "ben@north.example", "member", True, False),
        ("cy.quiet", "cy.quiet@north.example", "member", False, False),   # invited, not signed in
    ]


def test_a_member_sees_names_and_no_address_but_their_own(people):
    people("ben")
    out = _members()
    assert out["role"] == "member" and out["can_see_emails"] is False
    assert [(m["name"], m["email"], m["you"]) for m in out["members"]] == [
        ("Ada", None, False),
        ("Ben", "ben@north.example", True),
        # no name on file: "Member", never the front half of the address
        ("Member", None, False),
    ]
    assert "cy.quiet" not in client.get("/api/account/members").text
    assert "ada@north.example" not in client.get("/api/account/members").text


def test_the_list_follows_the_workspace_you_have_open(people):
    people("ada", brand="south")
    out = _members()
    assert out["account"]["slug"] == "south" and out["role"] == "member"
    # a member there: Dee's name, not her address
    assert [(m["name"], m["email"]) for m in out["members"]] == [("Dee", None), ("Ada", "ada@north.example")]
    people("ada", brand="north")
    assert _members()["account"]["slug"] == "north"


def test_the_answer_says_where_your_work_lives_whichever_workspace_is_open(people):
    """Data routes act on the caller's FIRST workspace whatever is open
    (auth.current_account_id). The page is told which, so a switch does
    not read as having moved anybody's credits or scenes."""
    for brand in ("north", "south"):
        people("ada", brand=brand)
        out = _members()
        assert out["account"]["slug"] == brand
        assert out["home"] == {"id": 1, "slug": "north", "label": "North Films"}
    people("dee")
    assert _members()["home"]["slug"] == "south"


def test_the_brand_cookie_cannot_open_a_workspace_you_are_not_in(people):
    for brand in ("south", "nope", "../north"):
        people("ben", brand=brand)
        out = _members()
        assert out["account"]["slug"] == "north", brand
        assert all(m["name"] != "Dee" for m in out["members"])
    # and Dee, the other way round, never reads North's
    people("dee", brand="north")
    out = _members()
    assert out["account"]["slug"] == "south"
    assert {m["name"] for m in out["members"]} == {"Dee", "Ada"}
    assert "ben" not in client.get("/api/account/members").text.lower()


def test_someone_in_no_workspace_is_refused(people):
    people("eve")
    assert client.get("/api/account/members").status_code == 403


def test_the_route_takes_no_account_from_the_request(people):
    """There is no id to ask for: a query naming another workspace is
    ignored, because nothing reads it."""
    people("ben")
    answer = client.get("/api/account/members", params={"account_id": 2, "slug": "south", "id": 2})
    assert answer.json()["account"]["slug"] == "north"


# --------------------------------------------------------------------------
# the switch itself (POST /brand/<slug>)
# --------------------------------------------------------------------------

def _switch(slug):
    answer = client.post(f"/brand/{slug}", data={"next": "/studio"}, follow_redirects=False)
    assert answer.status_code == 303
    return client.get("/api/me").json()["account"]["slug"]


def test_switching_workspace_round_trips_for_any_workspace_you_are_in(people):
    """Only the two legacy brand names could be stored in the cookie, so a
    switch to any other workspace landed on the caller's FIRST membership,
    whichever was asked for. Ada is in `north` and `south`; neither is a
    brand name."""
    people("ada")
    for slug in ("south", "north", "south", "north"):
        assert _switch(slug) == slug
        assert _members()["account"]["slug"] == slug


def test_the_switch_cannot_enter_a_workspace_you_are_not_in(people):
    people("ben")                       # North only
    assert _switch("south") == "north"
    assert _members()["account"]["slug"] == "north"
    assert _switch("no-such-workspace") == "north"
    # what was stored is the default brand label, never the slug asked for
    answer = client.post("/brand/south", data={"next": "/studio"}, follow_redirects=False)
    assert "brand=south" not in answer.headers.get("set-cookie", "")


def test_the_switch_with_no_session_stores_only_a_brand_name(people, monkeypatch):
    monkeypatch.setattr(auth, "current_user", lambda request: None)
    client.cookies.clear()
    answer = client.post("/brand/north", data={"next": "/studio"}, follow_redirects=False)
    assert "brand=north" not in answer.headers.get("set-cookie", "")

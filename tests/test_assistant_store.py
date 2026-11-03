"""
The assistant pill's memory (2026-09-29, src/assistant_store.py): the
persona, the open project, and the Keep clicks against the checker.

What each test guards:
- a persona is cleaned the way the brain cleans it before it reaches a prompt
- a project survives: the thread and the step come back as saved, bounded
- a new session KEEPS the chat in the history drawer (2026-11-03); an empty one is deleted
- a chat on its own goes 14 days after it was last used; a project's chat stays
- the drawer reopens, deletes and files chats for the caller's account only
- one account never sees another's persona, project or verdicts
- a verdict is recorded only for an id a hunt actually served, and
  agreement() counts the disagreements in both directions
- the write routes refuse a request without the Guide's header, and the
  read route answers for the caller's account only
"""

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.main import app
from src import assistant_store, imagesearch


@pytest.fixture
def store(pg, monkeypatch):
    # account_id carries a real foreign key: the accounts must exist
    # (seed_two makes the seeded account = 1, the second studio = 2)
    from conftest import seed_two
    seed_two("pill@example.test", dsn=pg)
    assistant_store.init(pg)
    monkeypatch.setenv("DATABASE_URL", pg)
    return pg


def _turns(n):
    out = []
    for i in range(n):
        out += [{"role": "user", "content": f"ask {i}"},
                {"role": "assistant", "content": f"answer {i}"}]
    return out


# --- the persona -------------------------------------------------------------

def test_a_persona_is_cleaned_like_the_prompt_sees_it(store):
    saved = assistant_store.save_persona("N<o>va!!", "🦊<b>", "sarcastic",
                                         account_id=1, dsn=store)
    assert saved == {"name": "Nova", "avatar": "🦊b", "tone": "direct"}
    got = assistant_store.get_persona(account_id=1, dsn=store)
    assert {k: got[k] for k in ("name", "avatar", "tone")} == saved


def test_saving_a_persona_twice_keeps_one_row(store):
    assistant_store.save_persona("Nova", "🦊", "direct", account_id=1, dsn=store)
    assistant_store.save_persona("Rae", "🤖", "hype", account_id=1, dsn=store)
    assert assistant_store.get_persona(account_id=1, dsn=store)["name"] == "Rae"


# --- the project --------------------------------------------------------------

def test_a_project_comes_back_as_it_was_saved(store):
    assert assistant_store.open_project(account_id=1, dsn=store) is None
    saved = assistant_store.save_project(_turns(2), "story", account_id=1, dsn=store)
    assert saved["title"] == "ask 0"                       # the first thing asked
    got = assistant_store.open_project(account_id=1, dsn=store)
    assert got["id"] == saved["id"] and got["stage"] == "story"
    assert [t["content"] for t in got["turns"]] == ["ask 0", "answer 0", "ask 1", "answer 1"]


def test_a_long_thread_keeps_its_newest_turns(store):
    assistant_store.save_project(_turns(40), "brief", account_id=1, dsn=store)
    turns = assistant_store.open_project(account_id=1, dsn=store)["turns"]
    assert len(turns) == assistant_store.MAX_TURNS
    assert turns[-1]["content"] == "answer 39"


def test_an_unknown_stage_is_not_stored(store):
    assistant_store.save_project(_turns(1), "render everything", account_id=1, dsn=store)
    assert assistant_store.open_project(account_id=1, dsn=store)["stage"] == ""


def test_a_new_session_keeps_the_chat_and_the_next_save_starts_fresh(store):
    first = assistant_store.save_project(_turns(1), "story", account_id=1, dsn=store)
    assistant_store.clear_project(account_id=1, dsn=store)
    assert assistant_store.open_project(account_id=1, dsn=store) is None
    second = assistant_store.save_project([{"role": "user", "content": "a watch ad"}],
                                          "", account_id=1, dsn=store)
    assert second["id"] != first["id"] and second["title"] == "a watch ad"
    chats = assistant_store.list_chats(account_id=1, dsn=store)["chats"]
    assert [(c["id"], c["open"]) for c in chats] == [(second["id"], True), (first["id"], False)]


def test_an_empty_chat_is_deleted_not_kept(store):
    assistant_store.save_project([], "", draft={"idea": "half typed"}, account_id=1, dsn=store)
    assistant_store.clear_project(account_id=1, dsn=store)
    from src import db
    with db.connect(store) as conn:
        n = conn.execute("SELECT COUNT(*) AS n FROM assistant_projects").fetchone()["n"]
    assert n == 0


def test_forget_deletes_the_open_chat(store):
    assistant_store.save_project(_turns(1), "story", account_id=1, dsn=store)
    assistant_store.clear_project(account_id=1, forget=True, dsn=store)
    assert assistant_store.list_chats(account_id=1, dsn=store)["chats"] == []


def _age(dsn, chat_id, days):
    from datetime import datetime, timedelta, timezone

    from src import db
    when = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    with db.connect(dsn) as conn:
        conn.execute("UPDATE assistant_projects SET updated_at = %s WHERE id = %s", (when, chat_id))


def _project(dsn, account_id=1, title="Neon Ferry"):
    from src import preprod, projects
    preprod.init(dsn)                               # makes projects, as the app's start does
    return projects.create(title, "", dsn, account_id=account_id)["id"]


def test_a_chat_on_its_own_goes_after_14_days_and_counts_down(store):
    old = assistant_store.save_project(_turns(1), "", account_id=1, dsn=store)
    assistant_store.clear_project(account_id=1, dsn=store)
    week = assistant_store.save_project([{"role": "user", "content": "logo sting"}], "",
                                        account_id=1, dsn=store)
    assistant_store.clear_project(account_id=1, dsn=store)
    _age(store, old["id"], 15)
    _age(store, week["id"], 10)
    chats = assistant_store.list_chats(account_id=1, dsn=store)["chats"]
    assert [c["id"] for c in chats] == [week["id"]]          # the 15-day one is gone
    assert chats[0]["days_left"] == 4


def test_a_projects_chat_is_kept_for_good(store):
    pid = _project(store)
    assistant_store.save_project(_turns(1), "", account_id=1, dsn=store)
    assistant_store.tag_project(pid, account_id=1, dsn=store)
    chat = assistant_store.open_project(account_id=1, dsn=store)
    assistant_store.clear_project(account_id=1, dsn=store)
    _age(store, chat["id"], 90)
    listed = assistant_store.list_chats(account_id=1, dsn=store)
    assert [(c["id"], c["project_id"], c["days_left"]) for c in listed["chats"]] == [(chat["id"], pid, None)]
    assert [p["id"] for p in listed["projects"]] == [pid]


def test_a_chat_whose_project_is_gone_is_on_its_own_again(store):
    from src import projects
    pid = _project(store)
    assistant_store.save_project(_turns(1), "", account_id=1, dsn=store)
    assistant_store.tag_project(pid, account_id=1, dsn=store)
    projects.delete(pid, store, account_id=1)
    chat = assistant_store.list_chats(account_id=1, dsn=store)["chats"][0]
    assert chat["project_id"] is None and chat["days_left"] == 14


def test_tagging_opens_a_chat_when_none_is_open_and_takes_only_own_projects(store):
    theirs = _project(store, account_id=2, title="Theirs")
    assistant_store.tag_project(theirs, account_id=1, dsn=store)
    assert assistant_store.open_project(account_id=1, dsn=store) is None
    mine = _project(store)
    assistant_store.tag_project(mine, account_id=1, dsn=store)
    assert assistant_store.open_project(account_id=1, dsn=store)["project_id"] == mine
    saved = assistant_store.save_project(_turns(1), "", account_id=1, dsn=store)
    assert saved["project_id"] == mine and saved["title"] == "ask 0"


def test_opening_a_kept_chat_swaps_it_with_the_open_one(store):
    first = assistant_store.save_project(_turns(1), "story", account_id=1, dsn=store)
    assistant_store.clear_project(account_id=1, dsn=store)
    second = assistant_store.save_project([{"role": "user", "content": "now"}], "",
                                          account_id=1, dsn=store)
    got = assistant_store.open_chat(first["id"], account_id=1, dsn=store)
    assert got["id"] == first["id"] and len(got["turns"]) == 2
    assert assistant_store.open_project(account_id=1, dsn=store)["id"] == first["id"]
    open_ids = {c["id"]: c["open"] for c in assistant_store.list_chats(account_id=1, dsn=store)["chats"]}
    assert open_ids == {first["id"]: True, second["id"]: False}
    # someone else's chat is no chat
    assert assistant_store.open_chat(first["id"], account_id=2, dsn=store) is None
    assert not assistant_store.delete_chat(second["id"], account_id=2, dsn=store)
    assert assistant_store.delete_chat(second["id"], account_id=1, dsn=store)


def test_accounts_never_see_each_others_memory(store):
    assistant_store.save_persona("Nova", "🦊", "direct", account_id=1, dsn=store)
    assistant_store.save_project(_turns(1), "story", account_id=1, dsn=store)
    assert assistant_store.get_persona(account_id=2, dsn=store) is None
    assert assistant_store.open_project(account_id=2, dsn=store) is None
    assistant_store.save_project([{"role": "user", "content": "mine"}], "",
                                 account_id=2, dsn=store)
    assert assistant_store.open_project(account_id=1, dsn=store)["title"] == "ask 0"


# --- Keep against the checker --------------------------------------------------

@pytest.fixture
def served(monkeypatch):
    ids = {"ope-a", "ope-b", "ope-c"}
    monkeypatch.setattr(imagesearch, "get",
                        lambda cid, dsn=None: {"id": cid} if cid in ids else None)
    return ids


def test_verdicts_record_served_ids_and_agreement_counts_both_ways(store, served):
    frames = [
        {"id": "ope-a", "checker_kept": True, "person_kept": True, "role": "light"},
        {"id": "ope-b", "checker_kept": False, "person_kept": True, "why": "flat light"},
        {"id": "ope-c", "checker_kept": True, "person_kept": False},
        {"id": "invented-1", "checker_kept": True, "person_kept": True},   # never served
    ]
    assert assistant_store.record_verdicts(frames, account_id=1, dsn=store) == 3
    assert assistant_store.agreement(account_id=1, dsn=store) == {
        "n": 3, "agree": 1, "kept_anyway": 1, "left_out": 1, "rate": 0.333}
    assert assistant_store.agreement(account_id=2, dsn=store)["rate"] is None


# --- the routes ----------------------------------------------------------------

@pytest.fixture
def client(store, monkeypatch):
    monkeypatch.setattr(auth, "current_user", lambda request: {"id": "pill-user"})
    app.dependency_overrides[auth.current_account_id] = lambda: 2
    yield TestClient(app)
    app.dependency_overrides[auth.current_account_id] = lambda: None


GUARD = {"X-Phantra-Model-Connection": "1"}


def test_the_routes_round_trip_the_callers_memory(client, served):
    assert client.get("/api/assistant").json() == {"persona": None, "project": None}
    r = client.put("/api/assistant/persona", headers=GUARD,
                   json={"name": "Nova", "avatar": "🦊", "tone": "friendly"})
    assert r.status_code == 200 and r.json()["persona"]["tone"] == "friendly"
    r = client.put("/api/assistant/project", headers=GUARD,
                   json={"turns": _turns(1), "stage": "references"})
    assert r.status_code == 200 and "turns" not in r.json()["project"]
    got = client.get("/api/assistant").json()
    assert got["persona"]["name"] == "Nova"
    assert got["project"]["stage"] == "references" and len(got["project"]["turns"]) == 2
    r = client.post("/api/assistant/reference-verdicts", headers=GUARD,
                    json={"frames": [{"id": "ope-a", "checker_kept": False, "person_kept": True}]})
    assert r.json()["recorded"] == 1 and r.json()["agreement"]["kept_anyway"] == 1
    assert client.delete("/api/assistant/project", headers=GUARD).status_code == 200
    assert client.get("/api/assistant").json()["project"] is None
    # the older name still clears
    client.put("/api/assistant/project", headers=GUARD, json={"turns": _turns(1), "stage": ""})
    assert client.post("/api/assistant/project/new", headers=GUARD).status_code == 200
    assert client.get("/api/assistant").json()["project"] is None


def test_the_drawer_routes_list_open_and_delete(client):
    client.put("/api/assistant/project", headers=GUARD, json={"turns": _turns(1), "stage": ""})
    client.delete("/api/assistant/project", headers=GUARD)
    chats = client.get("/api/assistant/chats").json()["chats"]
    assert len(chats) == 1 and not chats[0]["open"]
    cid = chats[0]["id"]
    r = client.post(f"/api/assistant/chats/{cid}/open", headers=GUARD)
    assert r.status_code == 200 and r.json()["project"]["id"] == cid
    assert client.get("/api/assistant").json()["project"]["id"] == cid
    assert client.post("/api/assistant/chats/99999/open", headers=GUARD).status_code == 404
    assert client.delete(f"/api/assistant/chats/{cid}", headers=GUARD).status_code == 200
    assert client.get("/api/assistant/chats").json()["chats"] == []


def test_the_writes_refuse_a_request_without_the_guide_header(client):
    for method, path, body in (("put", "/api/assistant/persona", {"name": "x"}),
                               ("post", "/api/assistant/chats/1/open", {}),
                               ("delete", "/api/assistant/chats/1", None),
                               ("put", "/api/assistant/project", {"turns": []}),
                               ("post", "/api/assistant/project/new", {}),
                               ("delete", "/api/assistant/project", None),
                               ("post", "/api/assistant/reference-verdicts", {"frames": []})):
        r = getattr(client, method)(path, **({"json": body} if body is not None else {}))
        assert r.status_code == 403, (path, r.status_code)


def test_a_malformed_project_is_refused(client):
    r = client.put("/api/assistant/project", headers=GUARD, json={"turns": "not a list"})
    assert r.status_code == 400


# --- the composer's draft (2026-10-02) ----------------------------------------

def test_a_draft_is_saved_beside_the_thread_and_cleaned(store):
    draft = {"idea": "a watch ad", "brief": "B", "mode": "create",
             "picked": ["/characters/michael/photo/a.jpg", "/characters/michael/photo/a.jpg", "javascript:x"],
             "uploads": [{"url": "/refs/abc.jpg", "name": "IMG_1.heic"}, "junk", {"url": "nope"}],
             "written": {"conceptId": 375, "detail": "on the board"},
             # what each reference is for: kept for the ones still attached,
             # dropped for one that is not and for a role there is none of
             "roles": {"/refs/abc.jpg": "light", "/refs/gone.jpg": "product",
                       "/characters/michael/photo/a.jpg": "vibes"},
             "stray": "dropped"}
    assistant_store.save_project([], "", draft=draft, account_id=1, dsn=store)
    got = assistant_store.open_project(account_id=1, dsn=store)["draft"]
    assert got == {"idea": "a watch ad", "brief": "B", "mode": "create",
                   "picked": ["/characters/michael/photo/a.jpg"],
                   "uploads": [{"url": "/refs/abc.jpg", "name": "IMG_1.heic"}],
                   "roles": {"/refs/abc.jpg": "light"},
                   "written": {"conceptId": 375, "detail": "on the board"},
                   "brand_kit_id": None, "studio": None}


def test_a_save_without_a_draft_leaves_the_stored_one_alone(store):
    assistant_store.save_project([], "", draft={"idea": "keep me"}, account_id=1, dsn=store)
    # the pill's shape: turns and a stage, no draft
    assistant_store.save_project(_turns(1), "story", account_id=1, dsn=store)
    got = assistant_store.open_project(account_id=1, dsn=store)
    assert got["draft"]["idea"] == "keep me" and len(got["turns"]) == 2
    # an explicit empty draft clears it
    assistant_store.save_project(_turns(1), "story", draft={}, account_id=1, dsn=store)
    assert assistant_store.open_project(account_id=1, dsn=store)["draft"] == assistant_store.EMPTY_DRAFT


def test_a_draft_is_bounded_and_defaulted(store):
    draft = {"idea": "x" * 20_000, "mode": "render", "picked": [f"/refs/{i}.jpg" for i in range(100)],
             "written": {"conceptId": "375", "detail": "d"}}
    assistant_store.save_project([], "", draft=draft, account_id=1, dsn=store)
    got = assistant_store.open_project(account_id=1, dsn=store)["draft"]
    assert len(got["idea"]) == assistant_store.MAX_DRAFT_TEXT
    assert got["mode"] == "create" and len(got["picked"]) == assistant_store.MAX_DRAFT_REFS
    assert got["written"] == {"conceptId": None, "detail": "d"} and got["brief"] == ""


def test_a_cleared_conversation_starts_with_an_empty_draft(store):
    assistant_store.save_project([], "", draft={"idea": "old"}, account_id=1, dsn=store)
    assistant_store.clear_project(account_id=1, dsn=store)
    assistant_store.save_project([], "", draft={"idea": "new"}, account_id=1, dsn=store)
    assert assistant_store.open_project(account_id=1, dsn=store)["draft"]["idea"] == "new"


def test_the_route_round_trips_the_draft_and_refuses_a_bad_one(client):
    r = client.put("/api/assistant/project", headers=GUARD,
                   json={"turns": [], "stage": "", "draft": {"idea": "a watch ad", "picked": ["/refs/a.jpg"]}})
    assert r.status_code == 200 and "draft" not in r.json()["project"]
    got = client.get("/api/assistant").json()["project"]
    assert got["draft"]["idea"] == "a watch ad" and got["draft"]["picked"] == ["/refs/a.jpg"]
    # the pill's save, no draft: the box is still there
    client.put("/api/assistant/project", headers=GUARD, json={"turns": _turns(1), "stage": "story"})
    assert client.get("/api/assistant").json()["project"]["draft"]["idea"] == "a watch ad"
    r = client.put("/api/assistant/project", headers=GUARD, json={"turns": [], "draft": "not an object"})
    assert r.status_code == 400

"""A render shared on a public page (src/shares.py, app/share_page.py, 2026-10-20).

The rules that make it safe: nothing is public until its owner shares that
one item; the page is given only the media, its poster and the workspace's
name (never the prompt or a price); another account can neither share nor
see the share; Unshare, or deleting the render, takes the page down for good.
Nothing here calls a model.
"""
import pytest
from fastapi.testclient import TestClient

from app import auth
from app.main import app
from src import accounts, render_assets, shares

WHO = {}


@pytest.fixture
def store(pg, monkeypatch):
    accounts.init(pg)
    render_assets.init(pg)
    shares.init(pg)
    monkeypatch.setenv("DATABASE_URL", pg)
    monkeypatch.setattr(render_assets, "_ingest",
                        lambda *a, **k: {"ok": False, "chunks": 0, "error": "stubbed"})
    WHO["mine"] = accounts.upsert_account("s-mine", "Maya's Studio", "#fff", dsn=pg)
    WHO["theirs"] = accounts.upsert_account("s-theirs", "Other", "#fff", dsn=pg)
    return pg


def a_clip(dsn, who="mine", prompt="a secret client brief, never public"):
    return render_assets.record(generation_id=1, tool="fal", model="kling3-turbo-pro",
                                media_kind="video", prompt=prompt,
                                media_url="renders/fal/clip-abc.mp4", dsn=dsn,
                                account_id=WHO[who])["id"]


# guards: share / status / unshare -- one live address, revocable, never reused
def test_a_share_is_one_live_address_until_it_is_taken_down(store):
    clip = a_clip(store)
    assert shares.status(clip, account_id=WHO["mine"], dsn=store) is None
    token = shares.share(clip, account_id=WHO["mine"], dsn=store)
    assert len(token) >= 20
    assert shares.share(clip, account_id=WHO["mine"], dsn=store) == token      # same address
    assert shares.status(clip, account_id=WHO["mine"], dsn=store) == token
    assert shares.unshare(clip, account_id=WHO["mine"], dsn=store) == 1
    assert shares.public(token, dsn=store) is None                              # down
    again = shares.share(clip, account_id=WHO["mine"], dsn=store)
    assert again != token and shares.public(token, dsn=store) is None           # never comes back


# guards: public -- only the media, the poster and the name; never the prompt or a price
def test_the_page_is_given_only_what_is_public(store):
    clip = a_clip(store)
    token = shares.share(clip, account_id=WHO["mine"], dsn=store)
    got = shares.public(token, dsn=store)
    assert set(got) == {"kind", "url", "poster", "creator", "shared_at"}
    assert got["kind"] == "video" and got["creator"] == "Maya's Studio"
    assert got["url"]
    assert "secret" not in str(got) and "kling" not in str(got) and "credit" not in str(got)
    for bad in ("", "x" * 200, "not-a-token", None):
        assert shares.public(bad, dsn=store) is None


# guards: the account predicate -- another account can neither share nor see it
def test_another_account_cannot_share_or_see_it(store):
    clip = a_clip(store)
    with pytest.raises(LookupError):
        shares.share(clip, account_id=WHO["theirs"], dsn=store)
    shares.share(clip, account_id=WHO["mine"], dsn=store)
    assert shares.status(clip, account_id=WHO["theirs"], dsn=store) is None
    assert shares.unshare(clip, account_id=WHO["theirs"], dsn=store) == 0


# guards: a deleted render is no share, and cannot be shared
def test_a_deleted_render_is_not_shared(store):
    clip = a_clip(store)
    token = shares.share(clip, account_id=WHO["mine"], dsn=store)
    assert render_assets.soft_delete(clip, store, account_id=WHO["mine"])
    assert shares.public(token, dsn=store) is None
    with pytest.raises(LookupError):
        shares.share(clip, account_id=WHO["mine"], dsn=store)


# guards: the routes -- the owner's three on /api, the public read outside it
def test_the_routes(store, monkeypatch):
    monkeypatch.setattr(auth, "current_user", lambda request: {"id": "u"})
    monkeypatch.setattr(auth, "current_account", lambda request, user=None: {"slug": "s-mine"})
    clip = a_clip(store)
    signed_in = TestClient(app, headers={"X-Phantra-Model-Connection": "1"})
    app.dependency_overrides[auth.current_account_id] = lambda: WHO["mine"]
    try:
        assert signed_in.get(f"/api/assets/generated/{clip}/share").json()["shared"] is False
        made = signed_in.post(f"/api/assets/generated/{clip}/share").json()
        assert made["shared"] and made["path"] == f"/v/{made['token']}"
        assert signed_in.post("/api/assets/generated/999999/share").status_code == 404

        anyone = TestClient(app)                       # no session, no header
        page = anyone.get(f"/public/share/{made['token']}")
        assert page.status_code == 200 and page.json()["creator"] == "Maya's Studio"
        assert anyone.get("/public/share/nothing-here-at-all").status_code == 404

        # deleting the render takes its page down, and an Undo does not bring it back
        assert signed_in.delete(f"/api/assets/generated/{clip}").status_code == 200
        assert anyone.get(f"/public/share/{made['token']}").status_code == 404
        assert signed_in.post(f"/api/assets/generated/{clip}/restore").status_code == 200
        assert anyone.get(f"/public/share/{made['token']}").status_code == 404

        again = signed_in.post(f"/api/assets/generated/{clip}/share").json()
        assert signed_in.delete(f"/api/assets/generated/{clip}/share").json()["shared"] is False
        assert anyone.get(f"/public/share/{again['token']}").status_code == 404
    finally:
        app.dependency_overrides.pop(auth.current_account_id, None)

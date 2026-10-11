"""Where outcome events are written (step 4 of docs/tasks/task-higgsfield-shape.md).

tests/test_outcomes.py holds the writer's own rules. These hold that the
doors a person actually uses call it: the Library's star, delete, Undo and
download, "Make element", a render sent back as a reference, a Variation,
an effect's source, a clip going onto a timeline. Each names the line it
guards. Nothing here calls a model or a provider.
"""
import pytest
from fastapi.testclient import TestClient

from app import api, auth
from app.main import app
from src import (
    accounts,
    effects,
    entities,
    generative,
    ledger,
    media,
    outcomes,
    preprod,
    render_assets,
    storage,
)
from src.cut import doc as cut_doc
from src.cut import store as cut_store

WHO = {}


@pytest.fixture
def client(pg, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", pg)
    accounts.init(pg)
    preprod.init(pg)
    entities.init(pg)
    generative.init(pg)
    ledger.init(pg)
    render_assets.init(pg)
    outcomes.init(pg)
    WHO["mine"] = accounts.upsert_account("h-mine", "Mine", "#fff", dsn=pg)
    WHO["theirs"] = accounts.upsert_account("h-theirs", "Theirs", "#fff", dsn=pg)
    monkeypatch.setattr(auth, "current_user", lambda request: {"id": "h-user"})
    monkeypatch.setattr(render_assets, "_ingest",
                        lambda *a, **k: {"ok": False, "chunks": 0, "error": "stubbed"})
    monkeypatch.setattr(render_assets, "drop_chunk", lambda *a, **k: None)
    app.dependency_overrides[auth.current_account_id] = lambda: WHO["mine"]
    yield TestClient(app)
    app.dependency_overrides.pop(auth.current_account_id, None)


def render(pg, n, who="mine", *, kind="image", url=None, prompt=None):
    url = url or (f"/renders/nano/still-{n}.png" if kind == "image" else f"/renders/fal/clip-{n}.mp4")
    return render_assets.record(
        generation_id=n, tool="nano" if kind == "image" else "wan", model="stub",
        media_kind=kind, prompt=prompt or f"prompt number {n}", media_url=url,
        dsn=pg, account_id=WHO[who])["id"]


def events(pg, asset, who="mine"):
    return [(e["event"], e["source"])
            for e in outcomes.events_for([asset], account_id=WHO[who], dsn=pg)[asset]]


# guards: asset_organize_generated -- a star is recorded, a folder move and an un-star are not
def test_starring_on_the_wall_is_recorded(client, pg):
    still = render(pg, 1)
    assert client.patch(f"/api/assets/generated/{still}", json={"folder": "keepers"}).status_code == 200
    assert events(pg, still) == []
    assert client.patch(f"/api/assets/generated/{still}", json={"starred": True}).json()["starred"]
    assert client.patch(f"/api/assets/generated/{still}", json={"starred": False}).status_code == 200
    assert events(pg, still) == [("star", "library")]
    theirs = render(pg, 2, "theirs")
    assert client.patch(f"/api/assets/generated/{theirs}", json={"starred": True}).status_code == 404
    assert events(pg, theirs, "theirs") == []


# guards: asset_delete_generated / asset_restore_generated -- a delete, and the Undo that takes it back
def test_a_delete_is_recorded_and_its_undo_takes_it_back(client, pg):
    still = render(pg, 1)
    assert client.delete(f"/api/assets/generated/{still}").json() == {"deleted": still}
    assert events(pg, still) == [("delete", "library")]
    assert client.post(f"/api/assets/generated/{still}/restore").json() == {"restored": still}
    assert events(pg, still) == []
    assert client.delete("/api/assets/generated/999999").status_code == 404


# guards: asset_download_generated -- a download that was served, never one that was refused
def test_a_served_download_is_recorded(client, pg, monkeypatch):
    still = render(pg, 1, url="https://pub.example/m/42/renders/nano/a.png")
    monkeypatch.setattr(storage, "configured", lambda: True)
    monkeypatch.setattr(storage, "key_exists", lambda key: True)
    monkeypatch.setattr(media, "master_key", lambda url, account_id: "m/42/renders/nano/a.png")
    monkeypatch.setattr(storage, "download_url_for_key", lambda key, name: f"https://s3.example/{key}")
    assert client.get(f"/api/assets/generated/{still}/download",
                      follow_redirects=False).status_code == 302
    assert events(pg, still) == [("download", "library")]
    # nowhere to get it from: a 404, and nothing said about the output
    monkeypatch.setattr(storage, "configured", lambda: False)
    other = render(pg, 2)
    assert client.get(f"/api/assets/generated/{other}/download",
                      follow_redirects=False).status_code == 404
    assert events(pg, other) == []


# guards: _create_entity -- "Make element" on a render says the render was kept
def test_a_render_made_into_an_element_is_recorded(client, pg, monkeypatch, tmp_path):
    still = render(pg, 1, url="/renders/nano/a.png")
    monkeypatch.setattr(api, "PROPS_DIR", tmp_path / "props")
    monkeypatch.setattr(api, "_create_gate", lambda account_id: None)
    monkeypatch.setattr(api, "_photo_bytes", lambda url: b"\x89PNG-bytes")
    monkeypatch.setattr(api, "describe_entity_photos",
                        lambda *a, **k: {"ok": False, "description": {}, "error": "no key"})
    monkeypatch.setattr(api, "ingest_asset_chunk",
                        lambda *a, **k: {"ok": True, "chunks": 1, "error": None})
    res = client.post("/api/assets/props",
                      data={"name": "The Can", "sheet": "0",
                            "photo_urls": ["/renders/nano/a.png", "/refs/upload.jpg"]})
    assert res.status_code == 200, res.text
    assert events(pg, still) == [("element_from", "elements")]


# guards: generate_run -- a render sent back as a reference, and the still a Variation continues
def test_a_variation_and_a_reused_render_are_recorded_before_the_new_one(client, pg, monkeypatch):
    reference = render(pg, 1, url="/renders/nano/ref.png")
    source = render(pg, 2, url="/renders/nano/src.png")
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    monkeypatch.setattr(api, "_create_gate", lambda account_id: None)

    async def refs(form, want_video=False, drop_urls=None):
        return [], ["/renders/nano/ref.png", "/refs/upload.jpg"], []
    monkeypatch.setattr(api, "_collect_refs", refs)
    # the job itself is not the subject: it is started and left to fail
    monkeypatch.setattr(api.jobs, "start", lambda *a, **k: {"id": 1})
    res = client.post("/api/generate/run",
                      data={"prompt": "the same can again", "output": "image",
                            "brand": "zeropage", "continued_from": f"gen:{source}"})
    assert res.status_code == 200, res.text
    assert events(pg, reference) == [("ref_reuse", "composer")]
    assert events(pg, source) == [("continued", "variation")]


# guards: effects.run -- what an approved effect acts on was reused, by id or by URL
def test_an_effects_source_is_recorded(client, pg, monkeypatch):
    clip = render(pg, 1, kind="video")
    still = render(pg, 2, url="/renders/nano/b.png")
    monkeypatch.delenv("FAL_KEY", raising=False)      # the run stops at the key: no provider
    out = effects.run("upscale", [], "", {"upscale_factor": 2}, usd=0.1,
                      sources=[f"gen:{clip}", "/renders/nano/b.png", "asset:9"],
                      account_id=WHO["mine"], db_path=pg, source="composer")
    assert out["ok"] is False
    assert events(pg, clip) == [("ref_reuse", "effect:upscale")]
    assert events(pg, still) == [("ref_reuse", "effect:upscale")]


def _doc(*handles):
    doc = cut_doc.new_doc()
    doc["tracks"] = [{"id": "V1", "kind": "video",
                      "clips": [{"id": f"c{i}", "media": h} for i, h in enumerate(handles)]}]
    return doc


# guards: store._note_added -- an output is recorded when it ENTERS a timeline, once
def test_an_output_entering_a_timeline_is_recorded_once(client, pg):
    a, b = render(pg, 1, kind="video"), render(pg, 2, kind="video")
    theirs = render(pg, 3, "theirs", kind="video")
    cut_store._note_added(_doc(f"gen:{a}", "asset:5", f"gen:{theirs}"), None, "cut:x", "user",
                          WHO["mine"], pg)
    assert events(pg, a) == [("cut_add", "user")] and events(pg, theirs, "theirs") == []
    # the next version: `a` was already there, `b` is new
    cut_store._note_added(_doc(f"gen:{a}", f"gen:{b}"), _doc(f"gen:{a}"), "cut:x", "agent",
                          WHO["mine"], pg)
    assert events(pg, a) == [("cut_add", "user")]
    assert events(pg, b) == [("cut_add", "agent")]


# guards: outcomes.record_handles -- the export hook's body: outputs only, each once
def test_an_exported_cut_marks_every_output_in_it(client, pg):
    a, b = render(pg, 1, kind="video"), render(pg, 2, kind="video")
    n = outcomes.record_handles("export", [f"gen:{a}", f"gen:{b}", f"gen:{a}", "asset:1"],
                                account_id=WHO["mine"], source="mp4",
                                meta={"file": "cut.mp4"}, dsn=pg)
    assert n == 2
    assert events(pg, a) == [("export", "mp4")] and events(pg, b) == [("export", "mp4")]

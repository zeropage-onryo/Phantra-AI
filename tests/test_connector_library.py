"""
The library, a download link, and the free edits on the listed servers
(2026-10-11, docs/tasks/task-connector-overnight.md PR 2).

What is guarded, in the order a mistake would cost:

- `reformat` and `trim_clip` refuse before anything is written -- a URL,
  someone else's id, audio, an unreadable file, a range outside the clip, a
  crop past the editor's bound -- and build their one-clip cut through the
  editor's own ops;
- with real ffmpeg (CI installs it) a clip and a still come back in the new
  shape, at the right size and length, the source untouched, filed on the
  wall for free, as a `gen:<id>` the next tool can name;
- `library` lists renders and uploads newest first with their ids and
  projects, this account's only; `share_link` signs a download for the
  bucket, or hands out this server's own address without one, and never
  past seven days; `job` can wait, briefly.
"""
import asyncio
import hashlib
import shutil
import subprocess
from pathlib import Path

import pytest

from src import mcp_server, preprod, scout
from src.cut import doc as d
from src.cut import quick

FPS = d.DEFAULT_FPS
needs_ffmpeg = pytest.mark.skipif(not (shutil.which("ffmpeg") and shutil.which("ffprobe")),
                                  reason="ffmpeg is not installed")


# --------------------------------------------------------------------------
# plan: every refusal, with no files (the wall and the probe stood in for)
# --------------------------------------------------------------------------

def _world(monkeypatch, assets=None, media=None, uploads=None):
    from src import render_assets
    from src.cut import sources, store
    assets = assets if assets is not None else {
        1: {"id": 1, "media_kind": "video", "media_url": "/renders/fal/1.mp4"},
        2: {"id": 2, "media_kind": "image", "media_url": "/renders/fal/2.png"},
        3: {"id": 3, "media_kind": "video", "media_url": "/renders/fal/3.mp4",
            "deleted_at": "2026-10-01"}}
    media = media if media is not None else {
        "gen:1": {"frames": 5 * FPS, "seconds": 5.0, "video": True, "audio": True,
                  "still": False, "width": 1280, "height": 720},
        # a still's probe shape is what sources.frames_of makes: held STILL_SECONDS
        "gen:2": {"frames": d.STILL_SECONDS * FPS, "seconds": 0.0, "video": True,
                  "audio": False, "still": True, "width": 1024, "height": 1024},
        "asset:4": {"frames": 3 * FPS, "seconds": 3.0, "video": True, "audio": False,
                    "still": False, "width": 720, "height": 1280},
        "asset:5": {"frames": 10 * FPS, "seconds": 10.0, "video": False, "audio": True,
                    "still": False, "width": None, "height": None}}
    uploads = uploads if uploads is not None else {4: {"id": 4, "kind": "video"},
                                                   5: {"id": 5, "kind": "audio"}}
    monkeypatch.setattr(render_assets, "get",
                        lambda i, dsn=None, account_id=None: assets.get(int(i)))
    monkeypatch.setattr(sources, "measure",
                        lambda handles, **kw: {h: media.get(h) for h in handles if h in media})
    monkeypatch.setattr(store, "get_media",
                        lambda i, account_id=None, dsn=None: uploads.get(int(i)))
    return media


@pytest.mark.parametrize("handle, kwargs, match", [
    ("https://x/a.mp4", {}, "URLs are never taken"),
    ("clip-7", {}, "gen:<id>"),
    ("gen:9", {}, "no render 9"),
    ("gen:3", {}, "no render 3"),                       # soft-deleted
    ("asset:8", {}, "no upload 8"),
    ("asset:5", {}, "takes a clip or a still"),         # audio
    ("gen:1", {"aspect": "2:1"}, "aspect must be one of"),
    ("gen:1", {"fit": "stretch"}, "fit must be one of"),
    ("gen:1", {"aspect": "16:9"}, "already 1280x720"),
])
def test_reformat_refusals_come_before_anything_is_made(monkeypatch, handle, kwargs, match):
    _world(monkeypatch)
    args = {"aspect": "9:16", "fit": "pad", **kwargs}
    with pytest.raises(quick.QuickRefused, match=match):
        quick.plan_reformat(handle, args["aspect"], args["fit"], account_id=1)


def test_an_unreadable_file_is_refused(monkeypatch):
    media = _world(monkeypatch)
    media["gen:1"] = None
    with pytest.raises(quick.QuickRefused, match="could not read gen:1"):
        quick.plan_reformat("gen:1", "9:16", account_id=1)


def test_pad_keeps_the_whole_picture_and_crop_cuts_the_middle(monkeypatch):
    _world(monkeypatch)
    padded = quick.plan_reformat("gen:1", "9:16", "pad", account_id=1)
    assert padded["size"] == [720, 1280] and padded["crop"] is None
    assert padded["seconds"] == 5.0 and not padded["still"]
    (clip,) = d.track(padded["doc"], "V1")["clips"]
    assert "crop" not in clip and len(d.track(padded["doc"], "A1")["clips"]) == 1
    cropped = quick.plan_reformat("gen:1", "9:16", "crop", account_id=1)
    (clip,) = d.track(cropped["doc"], "V1")["clips"]
    # 16:9 into 9:16 keeps 0.5625 / 1.778 of the width: 0.342 off each side
    assert clip["crop"] == {"left": 0.3418, "right": 0.3418, "top": 0.0, "bottom": 0.0}
    assert cropped["crop"] == clip["crop"]
    # a still is a still, held on the timeline, cut as a frame
    still = quick.plan_reformat("gen:2", "16:9", "crop", account_id=1)
    assert still["still"] and still["seconds"] == 0.0
    assert still["crop"]["top"] == pytest.approx(0.2188, abs=1e-4)


def test_a_crop_past_the_editors_bound_is_refused_not_clamped():
    assert quick.crop_for(1280, 720, (1280, 720)) == {"left": 0.0, "right": 0.0,
                                                       "top": 0.0, "bottom": 0.0}
    assert quick.crop_for(720, 1280, (1280, 720))["top"] == pytest.approx(0.3418, abs=1e-4)
    with pytest.raises(quick.QuickRefused, match='use fit="pad"'):
        quick.crop_for(6400, 900, (720, 1280))             # 64:9 into 9:16


@pytest.mark.parametrize("handle, start, end, match", [
    ("gen:1", 1, 1, "run forward"),
    ("gen:1", -1, 2, "run forward"),
    ("gen:1", "a", 2, "seconds, as numbers"),
    ("gen:1", 1, 9, "past the end of gen:1"),
    ("gen:1", 1, 1.01, "shorter than one frame"),
    ("gen:2", 0, 1, "is a still"),
    ("asset:5", 0, 1, "takes a clip or a still"),
    ("gen:9", 0, 1, "no render 9"),
])
def test_trim_refusals_come_before_anything_is_made(monkeypatch, handle, start, end, match):
    _world(monkeypatch)
    with pytest.raises(quick.QuickRefused, match=match):
        quick.plan_trim(handle, start, end, account_id=1)


def test_a_trim_is_whole_frames_inside_the_clip_with_its_sound(monkeypatch):
    _world(monkeypatch)
    planned = quick.plan_trim("gen:1", 0.5, 2.0, account_id=1)
    assert planned["frames"] == [15, 60] and planned["seconds"] == 1.5
    (clip,) = d.track(planned["doc"], "V1")["clips"]
    assert (clip["src_in"], clip["src_out"]) == (15, 60)
    assert len(d.track(planned["doc"], "A1")["clips"]) == 1          # linked sound
    assert planned["size"] == [1280, 720]
    silent = quick.plan_trim("asset:4", 0, 3, account_id=1)
    assert d.track(silent["doc"], "A1")["clips"] == []


# --------------------------------------------------------------------------
# with real ffmpeg: a new shape, a range, the source untouched
# --------------------------------------------------------------------------

def _clip(path: Path, seconds: float, size: str = "160x284", tone: int = 440) -> Path:
    subprocess.run(["ffmpeg", "-v", "error", "-y",
                    "-f", "lavfi", "-t", str(seconds), "-i", f"testsrc=size={size}:rate={FPS}",
                    "-f", "lavfi", "-t", str(seconds), "-i", f"sine=frequency={tone}:sample_rate=48000",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(path)],
                   check=True, capture_output=True)
    return path


def _png(path: Path, size=(160, 284)) -> Path:
    from PIL import Image
    Image.new("RGB", size, (200, 30, 30)).save(path, "PNG")
    return path


@pytest.fixture
def wall(pg, tmp_path, monkeypatch):
    """A clip and a still on the wall, an upload in the bin, on a real
    database, and a server with a job registry that runs the job inline."""
    from src import accounts, db, entities, generative, ledger, projects, render_assets
    from src.cut import store
    preprod.init(pg)
    scout.init(pg)
    entities.init(pg)
    generative.init(pg)
    render_assets.init(pg)
    projects.init(pg)
    store.init(pg)
    ledger.init(pg)
    accounts.seed("mike@example.com", dsn=pg)
    with db.connect(pg) as conn:
        acct = int(conn.execute("SELECT MIN(id) AS id FROM accounts").fetchone()["id"])
    monkeypatch.setattr(render_assets, "_ingest",
                        lambda *a, **k: {"ok": True, "chunks": 1, "error": None})
    clip = _clip(tmp_path / "clip.mp4", 2.0)
    still = _png(tmp_path / "still.png")
    rows = {}
    for key, path, kind in (("clip", clip, "video"), ("still", still, "image")):
        row = render_assets.record(generation_id=9100 + len(rows), tool="ltx", model="ltx2.3",
                                   media_kind=kind, prompt=f"the {key}",
                                   media_url=f"/renders/fal/{path.name}",
                                   output_path=str(path), account_id=acct, dsn=pg)
        rows[key] = f"gen:{row['id']}"
    up = store.add_media(account_id=acct, kind="video", filename="b-roll.mp4",
                         media_url="/renders/cut/media/b-roll.mp4",
                         output_path=str(_clip(tmp_path / "b-roll.mp4", 1.0, tone=330)),
                         seconds=1.0, sha256=None, dsn=pg)
    rows["upload"] = f"asset:{up['id']}"
    started, results = [], []

    def start_job(kind, label, fn, cancellable=False, account_id=None):
        started.append(label)
        results.append(fn({})["result"])
        return {"id": 77, "status": "done"}

    server = mcp_server.build_server(dsn=pg, listed=True, start_job=start_job,
                                     job_status=lambda i, account_id=None: None,
                                     account_id=acct)
    return {"dsn": pg, "account_id": acct, "refs": rows, "server": server,
            "started": started, "results": results, "files": {"clip": clip, "still": still}}


def _call(server, tool, args):
    import json
    res = asyncio.run(server.call_tool(tool, args))
    return json.loads(res.content[0].text)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@needs_ffmpeg
def test_a_clip_comes_back_in_a_new_shape_for_free_and_the_source_is_untouched(wall):
    from src import db, ledger, render_assets
    from src.cut import sources
    before = _sha(wall["files"]["clip"])
    out = _call(wall["server"], "reformat", {"ref": wall["refs"]["clip"], "aspect": "16:9",
                                             "fit": "pad"})
    assert out["job_id"] == 77 and wall["started"] == [f"reformat {wall['refs']['clip']} to 16:9"]
    assert out["plan"]["size"] == [1280, 720] and out["plan"]["credits"] == 0
    assert "no credits" in out["note"]
    (made,) = wall["results"]
    assert made["ok"] and made["credits"] == 0 and made["media_kind"] == "video"
    assert made["ref"] == f"gen:{made['asset_id']}"
    row = render_assets.get(made["asset_id"], wall["dsn"], account_id=wall["account_id"])
    assert row["tool"] == "cut" and row["model"] == "reformat"
    probe = sources.probe(Path(row["output_path"]), FPS)
    assert (probe["width"], probe["height"]) == (1280, 720)
    assert probe["seconds"] == pytest.approx(2.0, abs=0.15) and probe["audio"]
    assert _sha(wall["files"]["clip"]) == before              # the source, untouched
    assert ledger.entries(wall["account_id"], wall["dsn"]) == []
    with db.connect(wall["dsn"]) as conn:
        cost = conn.execute("SELECT cost_usd FROM generations WHERE id = %s",
                            (made["generation_id"],)).fetchone()["cost_usd"]
    assert cost is None


@needs_ffmpeg
def test_a_crop_fills_the_frame_and_a_still_stays_a_still(wall):
    from src import render_assets
    from src.cut import sources
    _call(wall["server"], "reformat", {"ref": wall["refs"]["clip"], "aspect": "1:1",
                                       "fit": "crop"})
    _call(wall["server"], "reformat", {"ref": wall["refs"]["still"], "aspect": "16:9"})
    cropped, still = wall["results"]
    assert cropped["plan"] if "plan" in cropped else True
    row = render_assets.get(cropped["asset_id"], wall["dsn"], account_id=wall["account_id"])
    probe = sources.probe(Path(row["output_path"]), FPS)
    assert (probe["width"], probe["height"]) == (1080, 1080)
    assert still["media_kind"] == "image"
    row = render_assets.get(still["asset_id"], wall["dsn"], account_id=wall["account_id"])
    assert row["media_url"].endswith(".png") and row["media_kind"] == "image"
    probe = sources.probe(Path(row["output_path"]), FPS)
    assert probe["still"] and (probe["width"], probe["height"]) == (1280, 720)


@needs_ffmpeg
def test_a_range_of_a_clip_becomes_a_new_clip(wall):
    from src import render_assets
    from src.cut import sources
    before = _sha(wall["files"]["clip"])
    out = _call(wall["server"], "trim_clip", {"ref": wall["refs"]["clip"], "start": 0.5,
                                              "end": 1.5})
    assert out["plan"]["seconds"] == 1.0 and out["plan"]["credits"] == 0
    (made,) = wall["results"]
    row = render_assets.get(made["asset_id"], wall["dsn"], account_id=wall["account_id"])
    assert row["model"] == "trim" and row["media_kind"] == "video"
    probe = sources.probe(Path(row["output_path"]), FPS)
    assert probe["seconds"] == pytest.approx(1.0, abs=0.15)
    assert (probe["width"], probe["height"]) == (160, 284)
    assert _sha(wall["files"]["clip"]) == before
    # an upload can be trimmed too, and the result is a gen the next tool takes
    _call(wall["server"], "trim_clip", {"ref": wall["refs"]["upload"], "start": 0, "end": 0.5})
    again = _call(wall["server"], "reformat", {"ref": wall["results"][1]["ref"],
                                               "aspect": "1:1"})
    assert again["plan"]["source"] == wall["results"][1]["ref"]


@needs_ffmpeg
def test_a_refusal_through_the_tool_is_a_tool_error_and_starts_nothing(wall):
    from mcp.server.mcpserver.exceptions import ToolError
    with pytest.raises(ToolError, match="past the end"):
        _call(wall["server"], "trim_clip", {"ref": wall["refs"]["clip"], "start": 0, "end": 9})
    with pytest.raises(ToolError, match="no render 999"):
        _call(wall["server"], "reformat", {"ref": "gen:999", "aspect": "1:1"})
    assert wall["started"] == []


@needs_ffmpeg
def test_assemble_clips_is_on_the_listed_server_and_joins_for_free(wall):
    out = _call(wall["server"], "assemble_clips", {"clips": [wall["refs"]["clip"],
                                                             wall["refs"]["upload"]],
                                                   "letterbox": True})
    assert out["job_id"] == 77 and out["plan"]["credits"] == 0
    (made,) = wall["results"]
    assert made["ok"] and made["ref"].startswith("gen:")


# --------------------------------------------------------------------------
# the library and a download link
# --------------------------------------------------------------------------

@pytest.fixture
def two(pg, tmp_path, monkeypatch):
    """Alice and Bob, each with a render and an upload; one of Alice's
    renders filed in a project."""
    from src import accounts, entities, generative, projects, render_assets
    from src.cut import store
    preprod.init(pg)
    scout.init(pg)
    entities.init(pg)
    generative.init(pg)
    render_assets.init(pg)
    projects.init(pg)
    store.init(pg)
    a = accounts.seed("alice@example.com", dsn=pg)["accounts"][0]
    accounts.create_user("bob@example.com", "Bob", user_id="user-bob", claimed=True, dsn=pg)
    b = accounts.upsert_account("bobs-studio", "Bob", "#000000", dsn=pg)
    accounts.add_member(b, "user-bob", dsn=pg)
    monkeypatch.setattr(render_assets, "_ingest",
                        lambda *a, **k: {"ok": True, "chunks": 1, "error": None})
    project = projects.create("Spring spots", "a brief", pg, account_id=a)
    (scene,) = preprod.save_concept_ideas(
        [{"title": "Alice's scene", "hook": "h", "logline": ""}], brand="zeropage", dsn=pg,
        account_id=a)
    projects.tag_concepts([scene], project["id"], pg, account_id=a)
    made = {}
    for who, acct, n in (("a", a, 1), ("b", b, 2)):
        row = render_assets.record(generation_id=9200 + n, tool="fal", model="seedream4.5",
                                   media_kind="image", prompt=f"{who}'s still",
                                   media_url=f"/renders/fal/{who}.png", output_path=None,
                                   account_id=acct, dsn=pg,
                                   concept_id=scene if who == "a" else None)
        made[f"{who}_render"] = f"gen:{row['id']}"
        up = store.add_media(account_id=acct, kind="video", filename=f"{who}.mp4",
                             media_url=f"/renders/cut/media/{who}.mp4", output_path=None,
                             seconds=4.0, sha256=None, dsn=pg)
        made[f"{who}_upload"] = f"asset:{up['id']}"
        store.put_probe(made[f"{who}_upload"], f"/renders/cut/media/{who}.mp4",
                        {"seconds": 4.0, "width": 720, "height": 1280, "video": True,
                         "audio": True, "still": False, "frames": 120}, account_id=acct,
                        size_bytes=1234, dsn=pg)
    return {"dsn": pg, "a": a, "b": b, "project": project["id"], **made}


def test_library_lists_each_persons_renders_and_uploads_with_their_projects(two):
    out = mcp_server.library(dsn=two["dsn"], account_id=two["a"])
    ids = [i["id"] for i in out["items"]]
    assert sorted(ids) == sorted([two["a_render"], two["a_upload"]])
    assert two["b_render"] not in ids and two["b_upload"] not in ids
    by = {i["id"]: i for i in out["items"]}
    render, upload = by[two["a_render"]], by[two["a_upload"]]
    assert render["origin"] == "render" and render["model"] == "seedream4.5"
    assert render["project"] == {"id": two["project"], "title": "Spring spots"}
    assert upload["origin"] == "upload" and upload["filename"] == "a.mp4"
    assert upload["seconds"] == 4.0 and upload["frame"] == "720x1280" and upload["aspect"] == "9:16"
    assert upload["size_bytes"] == 1234 and upload["project"] is None
    # filters
    assert [i["id"] for i in mcp_server.library(kind="upload", dsn=two["dsn"],
                                                 account_id=two["a"])["items"]] == [two["a_upload"]]
    assert [i["id"] for i in mcp_server.library(kind="image", dsn=two["dsn"],
                                                 account_id=two["a"])["items"]] == [two["a_render"]]
    assert [i["id"] for i in mcp_server.library(project_id=two["project"], dsn=two["dsn"],
                                                 account_id=two["a"])["items"]] == [two["a_render"]]
    assert mcp_server.library(limit=1, dsn=two["dsn"], account_id=two["a"])["count"] == 1
    with pytest.raises(ValueError, match="kind is one of"):
        mcp_server.library(kind="clip", dsn=two["dsn"], account_id=two["a"])
    with pytest.raises(ValueError, match="no project"):
        mcp_server.library(project_id=two["project"], dsn=two["dsn"], account_id=two["b"])
    empty = mcp_server.library(kind="audio", dsn=two["dsn"], account_id=two["b"])
    assert empty["count"] == 0 and "upload_link" in empty["note"]


def test_share_link_signs_a_download_off_the_bucket_for_the_hours_asked(two, monkeypatch):
    from src import outcomes, storage
    signed = []
    monkeypatch.setattr(storage, "configured", lambda: True)
    monkeypatch.setattr(storage, "key_exists", lambda key: key.endswith("a.png") or key.endswith("a.mp4"))
    monkeypatch.setattr(storage, "download_url_for_key",
                        lambda key, name, ttl=300: signed.append((key, name, ttl)) or
                        f"https://bucket.example/{key}?sig=1")
    outcomes.init(two["dsn"])
    out = mcp_server.share_link(two["a_render"], hours=48, dsn=two["dsn"], account_id=two["a"])
    assert out["url"].startswith("https://bucket.example/") and out["hours"] == 48
    assert out["expires_at"] and out["filename"].startswith("phantra-fal-")
    assert signed[-1][1] == out["filename"] and signed[-1][2] == 48 * 3600
    assert out["kind"] == "image"
    up = mcp_server.share_link(two["a_upload"], dsn=two["dsn"], account_id=two["a"])
    assert up["filename"] == "a.mp4" and up["hours"] == 24
    for bad, match in ((two["b_render"], "no render"), (two["b_upload"], "no upload"),
                       ("https://x/y.mp4", "URLs are never taken")):
        with pytest.raises(ValueError, match=match):
            mcp_server.share_link(bad, dsn=two["dsn"], account_id=two["a"])
    for hours, match in ((0, "1 to 168"), (169, "1 to 168"), ("soon", "whole number")):
        with pytest.raises(ValueError, match=match):
            mcp_server.share_link(two["a_render"], hours=hours, dsn=two["dsn"], account_id=two["a"])
    # a file the bucket does not hold is said plainly
    monkeypatch.setattr(storage, "key_exists", lambda key: False)
    with pytest.raises(ValueError, match="not in the studio's storage"):
        mcp_server.share_link(two["a_render"], dsn=two["dsn"], account_id=two["a"])


def test_without_a_bucket_share_link_is_this_servers_own_address(two, monkeypatch):
    from src import storage
    monkeypatch.setattr(storage, "configured", lambda: False)
    monkeypatch.setenv("PHANTRA_MCP_RESOURCE", "https://api.example.test/mcp")
    out = mcp_server.share_link(two["a_upload"], dsn=two["dsn"], account_id=two["a"])
    assert out["url"] == "https://api.example.test/renders/cut/media/a.mp4"
    assert out["expires_at"] is None and "does not expire" in out["note"]


def test_job_waits_briefly_and_refuses_a_long_wait(monkeypatch):
    seen = []
    states = iter(["queued", "running", "running", "done"])

    def job_status(i, account_id=None):
        seen.append(i)
        return {"id": i, "status": next(states)}
    monkeypatch.setattr(mcp_server, "_sleep", lambda s: None)
    out = mcp_server.poll_job(5, 3, job_status=job_status, account_id=1)
    assert out["status"] == "done" and len(seen) == 4
    assert mcp_server.poll_job(5, 0, job_status=lambda i, account_id=None: {"status": "running"},
                               account_id=1)["status"] == "running"
    assert mcp_server.poll_job(9, 2, job_status=lambda i, account_id=None: None,
                               account_id=1) is None
    for bad in (16, -1, "soon"):
        with pytest.raises(ValueError, match="wait is"):
            mcp_server.poll_job(5, bad, job_status=job_status, account_id=1)


def test_the_listed_servers_offer_the_five_and_the_claude_listing_has_job(pg):
    pytest.importorskip("mcp")
    preprod.init(pg)
    scout.init(pg)
    for listed in (True, "claude"):
        server = mcp_server.build_server(dsn=pg, listed=listed,
                                         job_status=lambda i, account_id=None: None)
        names = [t.name for t in asyncio.run(server.list_tools())]
        for tool in ("library", "share_link", "reformat", "trim_clip", "assemble_clips", "job"):
            assert tool in names, (listed, tool)
        job = next(t for t in asyncio.run(server.list_tools()) if t.name == "job")
        assert "wait" in job.input_schema["properties"]
        reformat = next(t for t in asyncio.run(server.list_tools()) if t.name == "reformat")
        assert set(reformat.input_schema["properties"]["aspect"]["enum"]) == set(quick.SIZES)
    # and their listed wording names `library`, never the studio's `renders`
    listed = mcp_server.build_server(dsn=pg, listed="claude",
                                     job_status=lambda i, account_id=None: None)
    for t in asyncio.run(listed.list_tools()):
        if t.name in ("assemble_clips", "reformat", "trim_clip", "share_link"):
            assert "`renders`" not in t.description and "import_file" not in t.description

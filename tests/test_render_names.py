"""
Render names cannot be guessed, and /renders is not open to whoever can
count (security review, 2026-10-15; src/render_names.py).

What each test guards:
- every writer of a new file under data/renders puts 128 random bits in
  the name (fal clips -- per shot and free-standing -- fal stills, Gemini
  stills, effects, the manual lane's import), keeping its readable prefix
- an anonymous GET of a legacy, guessable name is a 404, the same as a
  file that is not there -- and so is a signed-in stranger's
- the account a row says owns a legacy name still gets it
- a tokened name is a capability URL: served without a cookie (share
  links and publishers carry none), privately cached
- a path that climbs out of data/renders is refused before any lookup
"""
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src import render_names

TOKEN = re.compile(r"-[0-9a-f]{32}(?=[-.]|$)")


class _Stop(Exception):
    pass


def _token_bits(name: str) -> int:
    match = TOKEN.search(name)
    return 0 if not match else (len(match.group(0)) - 1) * 4


# ---------- the helper ----------------------------------------------------

def test_the_token_is_128_bits_and_never_repeats():
    names = {render_names.unguessable("c12-s1-20261015-120000") for _ in range(200)}
    assert len(names) == 200
    for name in names:
        assert name.startswith("c12-s1-20261015-120000-")
        assert _token_bits(name) >= 128
        assert render_names.has_token(name + ".mp4")
        assert render_names.is_capability("fal/" + name + ".mp4")


def test_a_legacy_name_is_not_a_capability_but_content_addressed_cut_files_are():
    for legacy in ("fal/c12-s1-20260911-161358.mp4", "nano/wf-20260911-161358.png",
                   "nano/c361-20260911-161358.png", "fal/fx-upscale-20260911-161358.jpg",
                   "cut/concept-12-v3-45.mp4", "manual/clip.mp4", "fal/refs/0123456789abcdef.png"):
        assert not render_names.is_capability(legacy), legacy
    sha = "0123456789abcdef01234567"
    for addressed in (f"cut/media/{sha}.mp3", f"cut/audio/{sha}.mp3",
                      f"cut/preview/{sha}/proxy.mp4"):
        assert render_names.is_capability(addressed), addressed


# ---------- every writer --------------------------------------------------

@pytest.fixture
def stopped_at_the_charge(pg, monkeypatch, tmp_path):
    """Each writer names its file, then builds the ledger Charge with that
    name in its ref. Stop there: the name is what is under test, and no
    provider is ever reached."""
    from src import charge, fal, generative, nano_banana
    monkeypatch.setenv("DATABASE_URL", pg)
    monkeypatch.setenv("FAL_KEY", "TEST")
    monkeypatch.setenv(fal.SPEND_ENV, "1")
    generative.init(pg)
    monkeypatch.setattr(fal, "RENDER_DIR", tmp_path / "renders" / "fal")
    monkeypatch.setattr(nano_banana, "RENDER_DIR", tmp_path / "renders" / "nano")
    seen = []

    def charge_spy(*args, ref=None, **kwargs):
        seen.append(str(ref))
        raise _Stop("named")

    monkeypatch.setattr(charge, "Charge", charge_spy)
    return {"dsn": pg, "seen": seen}


def test_a_fal_clip_off_the_canvas_is_named_unguessably(stopped_at_the_charge):
    from src import fal
    out = fal.generate_from_prompt("a man walks into a bar", db_path=stopped_at_the_charge["dsn"],
                                   account_id=1)
    assert out["ok"] is False
    (ref,) = stopped_at_the_charge["seen"]
    assert ref.startswith("wf-") and ref.endswith(".mp4") and _token_bits(ref) >= 128


def test_a_fal_clip_for_a_shot_keeps_its_readable_prefix_and_gains_the_token(
        stopped_at_the_charge, monkeypatch):
    from src import fal, preprod, prompts_for, timeline
    monkeypatch.setattr(preprod, "get_concept", lambda *a, **k: {"shots": [{"n": 1}]})
    monkeypatch.setattr(timeline, "render_target",
                        lambda shot, part: {"prompt": "a shot", "reference_image": None})
    monkeypatch.setattr(prompts_for, "render", lambda model, target, anchored: {
        "prompt": "a shot", "rule": prompts_for.UNCHANGED})
    fal.generate_for_shot(12, 1, db_path=stopped_at_the_charge["dsn"], account_id=1, part=2)
    (ref,) = stopped_at_the_charge["seen"]
    assert ref.startswith("c12-s1-p2-") and ref.endswith(".mp4") and _token_bits(ref) >= 128


def test_a_fal_still_is_named_unguessably(stopped_at_the_charge):
    from src import fal
    fal.generate_image_from_prompt("a red door", db_path=stopped_at_the_charge["dsn"],
                                   account_id=1, concept_id=7)
    (ref,) = stopped_at_the_charge["seen"]
    assert "-c7-" in ref and _token_bits(ref) >= 128


@pytest.mark.parametrize("concept_id,prefix", [(None, "nano-wf-"), (361, "nano-c361-")])
def test_a_gemini_still_is_named_unguessably_with_or_without_a_concept(
        stopped_at_the_charge, monkeypatch, concept_id, prefix):
    from src import nano_banana
    monkeypatch.setattr(nano_banana, "has_key", lambda account_id=None: True)
    nano_banana.generate_from_prompt("a red door", db_path=stopped_at_the_charge["dsn"],
                                     account_id=1, concept_id=concept_id)
    (ref,) = stopped_at_the_charge["seen"]
    # charge.attempt_ref: <folder>-<stem>-<microsecond stamp><suffix>
    assert ref.startswith(prefix) and _token_bits(ref) >= 128


def test_an_effect_output_is_named_unguessably(stopped_at_the_charge, monkeypatch):
    from src import effects, fal
    monkeypatch.setattr(fal, "has_key", lambda account_id=None: True)
    effects.run("upscale", ["https://cdn.test/a.png"], "", {}, usd=0.1, account_id=1,
                db_path=stopped_at_the_charge["dsn"],
                row={"label": "Upscale", "output": "image"},
                endpoint_body=("fal-ai/test", {}))
    (ref,) = stopped_at_the_charge["seen"]
    assert ref.startswith("fal-fx-upscale-") and _token_bits(ref) >= 128


def test_a_hand_imported_clip_is_copied_under_an_unguessable_name(tmp_path, monkeypatch):
    import importlib
    rq = importlib.import_module("ops.render_queue")
    src = tmp_path / "elsewhere" / "my clip.mp4"
    src.parent.mkdir()
    src.write_bytes(b"\x00" * 16)
    first = rq._place(src)
    second = rq._place(src)
    for placed in (first, second):
        assert placed.parent == rq.MANUAL_RENDER_DIR
        assert placed.name.startswith("my clip-") and placed.suffix == ".mp4"
        assert _token_bits(placed.name) >= 128
    assert first != second


# ---------- the /renders route --------------------------------------------

@pytest.fixture
def served(pg, monkeypatch):
    """The real app, its RENDERS_DIR on tmp (conftest's output_roots), two
    accounts, and a session that is whoever the test says it is."""
    from app import auth
    from app import main as app_main
    from src import accounts, generative, render_assets
    monkeypatch.setenv("DATABASE_URL", pg)
    accounts.init(pg)
    generative.init(pg)
    render_assets.init(pg)
    me = accounts.upsert_account("renders-mine", "Mine", "#fff", dsn=pg)
    them = accounts.upsert_account("renders-theirs", "Theirs", "#fff", dsn=pg)
    who = {"account": None}
    monkeypatch.setattr(auth, "optional_account_id", lambda request: who["account"])

    root = Path(app_main.RENDERS_DIR)
    legacy = root / "nano" / "c361-20260911-161358.png"
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_bytes(b"\x89PNG legacy")
    tokened = root / "nano" / (render_names.unguessable("wf-20261015-120000") + ".png")
    tokened.write_bytes(b"\x89PNG tokened")
    render_assets.record(generation_id=1, tool="nano", model="gemini", media_kind="image",
                         prompt="a red door", media_url="/renders/nano/" + legacy.name,
                         output_path=str(legacy), dsn=pg, account_id=me)
    return {"client": TestClient(app_main.app), "who": who, "me": me, "them": them,
            "legacy": legacy, "tokened": tokened}


def test_an_anonymous_guess_at_a_legacy_name_is_a_404(served):
    r = served["client"].get("/renders/nano/" + served["legacy"].name)
    assert r.status_code == 404
    assert b"legacy" not in r.content
    # indistinguishable from a file that is not there at all
    assert served["client"].get("/renders/nano/c361-20260911-161359.png").status_code == 404


def test_a_signed_in_stranger_cannot_open_someone_elses_legacy_name(served):
    served["who"]["account"] = served["them"]
    assert served["client"].get("/renders/nano/" + served["legacy"].name).status_code == 404


def test_the_owner_still_gets_a_legacy_name(served):
    served["who"]["account"] = served["me"]
    r = served["client"].get("/renders/nano/" + served["legacy"].name)
    assert r.status_code == 200 and r.content == b"\x89PNG legacy"
    assert r.headers["cache-control"] == "private, no-cache"


def test_a_tokened_name_is_a_capability_url_and_needs_no_session(served):
    r = served["client"].get("/renders/nano/" + served["tokened"].name)
    assert r.status_code == 200 and r.content == b"\x89PNG tokened"
    assert r.headers["cache-control"] == "private, no-cache"
    # the ETag round-trip still works
    again = served["client"].get("/renders/nano/" + served["tokened"].name,
                                 headers={"if-none-match": r.headers["etag"]})
    assert again.status_code == 304


def test_a_path_that_climbs_out_is_refused(served):
    served["who"]["account"] = served["me"]
    for path in ("/renders/../renders/nano/x.png", "/renders/%2e%2e/secret",
                 "/renders/nano/..%2F..%2Fsecret"):
        assert served["client"].get(path).status_code == 404, path


def test_the_owner_lookup_matches_the_tail_not_a_lookalike(served, pg):
    # `_` and `%` in a name are LIKE wildcards; escaped, they match only themselves
    assert render_names.owned_by("nano/" + served["legacy"].name, served["me"], pg)
    assert not render_names.owned_by("nano/c361-20260911-16135_.png", served["me"], pg)
    assert not render_names.owned_by("nano/%", served["me"], pg)
    assert not render_names.owned_by("nano/" + served["legacy"].name, None, pg)

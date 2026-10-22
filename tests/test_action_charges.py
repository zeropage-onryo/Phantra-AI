"""
A still costs credits, not just the clip (2026-09-28, Mike's call); a
Create does not (2026-09-29, Mike's call: it is included in the
subscription, its cost priced into the plans rather than debited per
click).

What each test guards:
- a still's price comes off the meter's own number at the render markup
  and floor, and an unknown image model never prices as the cheap one
- a Create moves no money, but is REFUSED (402, before any job or model
  call) for an account with no plan and no credit balance -- and allowed
  for one with either, the trial grant included
- a still settles on its generations row (the ledger_ref reap reads), an
  empty balance refuses before the image model is called, and a failed
  image is released
- the operator's exempt account and the unowned pool move no money
"""

import time

import pytest
from fastapi.testclient import TestClient

from src import accounts, db, generative, ledger, nano_banana, preprod, pricing

# --- the prices -------------------------------------------------------------


def test_prices_are_the_meters_numbers_at_the_render_markup():
    assert pricing.still_credits("gemini-2.5-flash-image") == 10    # $0.039 -> floor
    assert pricing.still_credits("gemini-3-pro-image-preview") == 33  # $0.134 x 2.4
    # the non-preview name the .env and refgen actually ask for
    assert pricing.still_credits("gemini-3-pro-image") == 33


def test_an_unknown_image_model_never_prices_as_the_cheap_one():
    assert pricing.still_credits("some-new-image-model") == \
        pricing.still_credits("gemini-3-pro-image-preview")


def test_the_public_catalog_prints_the_same_numbers():
    actions = pricing.public_catalog()["actions"]
    assert {k: actions[k] for k in ("create", "still")} == \
        {"create": 0, "still": {"standard": 10, "pro": 33}}
    # a talking photo (2026-10-20): 10s of voice at $0.105/s x 2.4
    assert actions["talking_photo"]["per_10s"] == 252


# --- a funded account --------------------------------------------------------


@pytest.fixture
def studio(pg, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", pg)
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    generative.init(pg)
    preprod.init(pg)
    accounts.seed("mike@example.com", dsn=pg)
    ledger.init(pg)
    with db.connect(pg) as conn:
        account_id = int(conn.execute(
            "SELECT id FROM accounts WHERE slug = 'phantra'").fetchone()["id"])
    return {"dsn": pg, "account_id": account_id}


def _fund(studio, credits=1000):
    ledger.grant(studio["account_id"], credits, "purchase", dsn=studio["dsn"])


def _kinds(studio):
    return [e["kind"] for e in ledger.entries(studio["account_id"], studio["dsn"])]


def _spent(studio):
    return -sum(e["delta"] for e in ledger.entries(studio["account_id"], studio["dsn"])
                if e["kind"] != "grant")


# --- Create -----------------------------------------------------------------


@pytest.fixture
def client(studio, monkeypatch):
    from app import auth
    from app.main import app
    monkeypatch.setattr(auth, "current_user",
                        lambda request: {"id": 1, "email": "t@e.com", "display_name": "T"})
    app.dependency_overrides[auth.current_account_id] = lambda: studio["account_id"]
    yield TestClient(app)
    app.dependency_overrides[auth.current_account_id] = lambda: None


@pytest.fixture
def writer(monkeypatch):
    """scene_chain.run replaced and counted -- the charge is the subject,
    not the writing."""
    from src import scene_chain
    calls = {"n": 0, "scenes": [{"concept_id": 1}], "raise": None}

    def fake_run(idea, **kw):
        calls["n"] += 1
        if calls["raise"]:
            raise calls["raise"]
        return {"scenes": calls["scenes"], "notes": []}

    monkeypatch.setattr(scene_chain, "run", fake_run)
    return calls


def _wait(client, job_id, timeout=5):
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in ("done", "failed", "cancelled"):
            return job
        time.sleep(0.02)
    raise AssertionError("job never finished")


def _create(client, **extra):
    return client.post("/api/scenes/run",
                       data={"idea": "gearing up ritual", **extra})


def test_no_plan_and_no_balance_refuses_create_before_anything_runs(client, studio,
                                                                   writer):
    res = _create(client)
    assert res.status_code == 402
    body = res.json()["error"]
    assert body["code"] == "subscribe_or_top_up"
    assert "subscribe or top up" in body["message"]
    assert writer["n"] == 0                       # no job, no model call
    assert _kinds(studio) == []


def test_a_create_moves_no_money(client, studio, writer):
    _fund(studio)
    for brain in ("fast", "reasoning"):
        res = _create(client, brain=brain)
        assert res.status_code == 200, res.text
        assert _wait(client, res.json()["job_id"])["status"] == "done"
    assert writer["n"] == 2
    assert _spent(studio) == 0
    assert _kinds(studio) == ["grant"]


def test_the_trial_grant_is_enough_to_create(client, studio, writer):
    ledger.grant(studio["account_id"], 100, "promo",
                 source_ref=f"signup:{studio['account_id']}", dsn=studio["dsn"])
    res = _create(client)
    assert res.status_code == 200, res.text


def test_a_plan_is_enough_to_create_with_no_balance(client, studio, writer):
    accounts.set_plan(studio["account_id"], "starter", dsn=studio["dsn"])
    res = _create(client)
    assert res.status_code == 200, res.text
    assert _wait(client, res.json()["job_id"])["status"] == "done"
    assert _spent(studio) == 0


def test_the_director_brief_is_gated_like_create(client, studio, monkeypatch):
    from app import api
    from src import shootgen
    monkeypatch.setattr(api, "scene_grounding", lambda *a, **k: "")
    monkeypatch.setattr(shootgen, "generate_scene_concept",
                        lambda **kw: {"concept_id": 7, "concept": {"title": "T"}})
    res = client.post("/api/pipeline/run", data={"prompt": "a rider"})
    assert res.status_code == 402
    _fund(studio)
    res = client.post("/api/pipeline/run", data={"prompt": "a rider"})
    assert _wait(client, res.json()["job_id"])["status"] == "done"
    assert _spent(studio) == 0


def test_the_composers_image_door_is_gated_like_create(client, studio, monkeypatch):
    """/generate/run grounds, enhances and saves a concept before the
    still's own hold is reached (2026-10-02: the composer's Image button)."""
    from app import api
    from src import shootgen
    calls = {"enhance": 0}

    def fake_enhance(*a, **k):
        calls["enhance"] += 1
        return "ENHANCED"

    monkeypatch.setattr(shootgen, "reference_block", lambda **k: "")
    monkeypatch.setattr(api, "_enhance_generate_prompt", fake_enhance)
    monkeypatch.setattr(nano_banana, "generate_from_prompt",
                        lambda *a, **k: {"ok": True, "media_url": "/renders/f.png"})
    import google.genai as genai_mod
    monkeypatch.setattr(genai_mod, "Client", lambda api_key=None: object())
    form = {"prompt": "a still", "output": "image"}
    res = client.post("/api/generate/run", data=form)
    assert res.status_code == 402
    assert res.json()["error"]["code"] == "subscribe_or_top_up"
    assert calls["enhance"] == 0                  # no job, no model call
    _fund(studio)
    res = client.post("/api/generate/run", data=form)
    assert _wait(client, res.json()["job_id"])["status"] == "done"
    assert calls["enhance"] == 1


def test_the_owner_is_never_charged(client, studio, writer):
    accounts.set_credit_exempt("phantra", True, dsn=studio["dsn"])
    res = _create(client)                          # no credit at all
    assert res.status_code == 200, res.text
    assert _wait(client, res.json()["job_id"])["status"] == "done"
    assert _kinds(studio) == []


# --- a still -----------------------------------------------------------------


@pytest.fixture
def nano(studio, monkeypatch, tmp_path):
    calls = {"n": 0, "raise": None}

    def fake_image(prompt, out_path, **kw):
        calls["n"] += 1
        if calls["raise"]:
            raise calls["raise"]
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(b"\x89PNG")
        return out_path

    import src.storage as storage
    monkeypatch.setattr(nano_banana, "generate_image", fake_image)
    monkeypatch.setattr(nano_banana, "RENDER_DIR", tmp_path / "nano")
    monkeypatch.setattr(storage, "configured", lambda: False)
    monkeypatch.setattr(nano_banana.render_assets, "record_best_effort",
                        lambda **kw: {"id": None, "rag": None})
    return calls


def _still(studio, **kw):
    # the model pinned: a developer's .env may set NANO_BANANA_MODEL to Pro
    kw.setdefault("model", "gemini-2.5-flash-image")
    return nano_banana.generate_from_prompt(
        "a rider suits up in a cold garage", db_path=studio["dsn"],
        account_id=studio["account_id"], **kw)


def test_a_still_is_charged_on_its_generations_row(studio, nano):
    import json
    _fund(studio)
    result = _still(studio)
    assert result["ok"], result["error"]
    assert _spent(studio) == 10
    settle = [e for e in ledger.entries(studio["account_id"], studio["dsn"])
              if e["kind"] == "settle"][0]
    assert settle["generation_id"] == result["generation_id"]
    with db.connect(studio["dsn"]) as conn:
        params = json.loads(conn.execute(
            "SELECT params_json FROM generations WHERE id = %s",
            (result["generation_id"],)).fetchone()["params_json"])
    assert params[ledger.GENERATION_REF_KEY] == settle["ref"]


def test_a_pro_still_costs_the_pro_price(studio, nano):
    _fund(studio)
    assert _still(studio, model="gemini-3-pro-image-preview")["ok"]
    assert _spent(studio) == 33


def test_an_empty_balance_refuses_a_still_before_the_model(studio, nano):
    result = _still(studio)
    assert result["ok"] is False
    assert "this still needs 10" in result["error"]
    assert nano["n"] == 0
    assert _kinds(studio) == []


def test_a_failed_still_is_released(studio, nano):
    _fund(studio)
    nano["raise"] = RuntimeError("no image in the response")
    assert _still(studio)["ok"] is False
    assert _spent(studio) == 0
    assert "release" in _kinds(studio)


def test_every_still_on_a_timed_scene_is_its_own_charge(studio, nano):
    """A pick draws one still per shot, often inside the same second --
    the hold ref must still be unique, or the second still reuses the
    first's settled hold and is drawn for free."""
    _fund(studio)
    for _ in range(3):
        assert _still(studio, concept_id=5)["ok"]
    assert _spent(studio) == 30


def test_the_unowned_nightly_pool_is_not_charged(studio, nano):
    result = nano_banana.generate_from_prompt(
        "a rider suits up", db_path=studio["dsn"], account_id=None,
        model="gemini-2.5-flash-image")
    assert result["ok"], result["error"]
    assert _kinds(studio) == []



# --- keyframes behind a priced approve (2026-09-29) -------------------------


@pytest.fixture
def drawn(monkeypatch):
    """keyframe_scene replaced and counted: the gate is the subject."""
    from src import scene_chain
    calls = []
    monkeypatch.delenv("PHANTRA_KEYFRAME_ON_PICK", raising=False)
    monkeypatch.setattr("google.genai.Client", lambda api_key=None: object())
    monkeypatch.setattr(scene_chain, "keyframe_scene",
                        lambda cid, n=None, **kw: calls.append(cid) or
                        {"ok": True, "media_url": "https://example.test/k.jpg", "frames": []})
    return calls


def _timed_scene(studio, parts=3):
    """A one-shot scene whose CURRENT timeline has `parts` shots, none drawn."""
    from src import timeline
    shot = {"n": 1, "type": "BROLL", "source": "AI", "tool": "LTX",
            "prompt": "(0-3s) a. (3-6s) b. (6-9s) c.", "refs": ["/refs/x.jpg"]}
    shot["timeline"] = {
        "seconds": 9, "planner": "split", "continuity": "",
        "source": timeline.source_hash(shot["prompt"], shot["refs"]),
        "parts": [{"n": i + 1, "start": 3 * i, "end": 3 * i + 3, "seconds": 3,
                   "text": "x", "prompt": "x", "refs": shot["refs"]} for i in range(parts)]}
    return preprod.save_concept({"title": "T", "hook": "", "logline": "", "shots": [shot]}, prompt_template="T",
                                dsn=studio["dsn"],
                                account_id=studio["account_id"])


def test_drawing_keyframes_needs_the_whole_strip_in_the_balance(client, studio, drawn):
    from src import nano_banana
    cid = _timed_scene(studio)
    each = pricing.still_credits(nano_banana.MODEL)
    _fund(studio, 2 * each)                    # two of three stills
    res = client.post(f"/api/concepts/{cid}/keyframes")
    assert res.status_code == 402
    body = res.json()["error"]
    assert body["code"] == "out_of_credits"
    assert f"needs {3 * each}" in body["message"] and "top up" in body["message"]
    assert drawn == []                          # never a partial strip

    _fund(studio, each)
    res = client.post(f"/api/concepts/{cid}/keyframes")
    assert res.status_code == 200, res.text
    assert res.json()["keyframes"]["stills"] == 3
    assert _wait(client, res.json()["job_id"])["status"] == "done"
    assert drawn == [cid]


def test_an_exempt_account_draws_with_no_balance(client, studio, drawn):
    accounts.set_credit_exempt("phantra", True, dsn=studio["dsn"])
    cid = _timed_scene(studio, parts=1)
    res = client.post(f"/api/concepts/{cid}/keyframes")
    assert res.status_code == 200, res.text


def test_the_balance_carries_the_still_price(client, studio):
    from src import nano_banana
    prices = client.get("/api/billing/balance").json()["prices"]
    from src import element_sheet
    assert prices == {"still": pricing.still_credits(nano_banana.MODEL),
                      "sheet": pricing.still_credits(element_sheet.SHEET_MODEL)}


# --- the doors that draw a still charge THEIR account (2026-09-30) -----------
# Found by the first real keyframe approve on a non-exempt account: the
# keyframe paths, the Director's Nano node, /api/generate/run's image branch
# and Run all passed no account into nano_banana, so every one of those stills
# was drawn FREE and its generations row was filed under the bootstrap
# account. These drive the real paths with only the image model faked.


def _gen_owners(studio):
    with db.connect(studio["dsn"]) as conn:
        return [r["account_id"] for r in conn.execute(
            "SELECT account_id FROM generations WHERE tool = 'nano' ORDER BY id")]


def test_the_keyframe_approve_charges_every_still_to_the_account(client, studio, nano,
                                                                 monkeypatch):
    from src import nano_banana
    monkeypatch.delenv("PHANTRA_KEYFRAME_ON_PICK", raising=False)
    cid = _timed_scene(studio)
    each = pricing.still_credits(nano_banana.MODEL)
    _fund(studio, 3 * each)
    res = client.post(f"/api/concepts/{cid}/keyframes")
    assert res.status_code == 200, res.text
    assert _wait(client, res.json()["job_id"])["status"] == "done"
    assert nano["n"] == 3
    assert _spent(studio) == 3 * each
    assert _kinds(studio).count("settle") == 3
    assert ledger.outstanding(studio["account_id"], studio["dsn"]) == 0
    assert _gen_owners(studio) == [studio["account_id"]] * 3


def test_the_director_nano_node_charges_the_account(client, studio, nano):
    from src import nano_banana
    each = pricing.still_credits(nano_banana.MODEL)
    _fund(studio, each)
    res = client.post("/api/workflows/exec/nano", json={"prompt": "a bench in fog"})
    assert res.status_code == 200, res.text
    assert _wait(client, res.json()["job_id"])["status"] == "done"
    assert _spent(studio) == each
    assert _gen_owners(studio) == [studio["account_id"]]


def test_every_nano_caller_forwards_the_account():
    """The shape of the bug, asserted on the source: a generate_from_prompt
    call that does not pass account_id is a still nobody pays for."""
    import ast
    import pathlib
    root = pathlib.Path(__file__).resolve().parent.parent
    missing = []
    for rel in ("src/scene_chain.py", "src/element_sheet.py", "app/api.py",
                "app/workflow_runner.py"):
        tree = ast.parse((root / rel).read_text())
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "generate_from_prompt"
                    and getattr(node.func.value, "id", None) == "nano_banana"
                    and not any(k.arg == "account_id" for k in node.keywords)):
                missing.append(f"{rel}:{node.lineno}")
    assert not missing, f"nano_banana.generate_from_prompt without account_id: {missing}"


# --- the composer picks the image model (2026-10-04) --------------------------

def test_image_models_is_a_projection_of_the_keys_on_file(client, monkeypatch):
    from src import fal, nano_banana, pricing
    monkeypatch.delenv("FAL_KEY", raising=False)
    monkeypatch.setattr(nano_banana, "has_key", lambda account_id=None: True)
    res = client.get("/api/image-models")
    assert res.status_code == 200
    body = res.json()
    assert [i["id"] for i in body["items"]] == ["nano"] and body["default"] == "nano"
    assert body["items"][0]["credits"] == pricing.still_credits(nano_banana.MODEL)
    monkeypatch.setenv("FAL_KEY", "k")
    body = client.get("/api/image-models").json()
    assert [i["id"] for i in body["items"]] == ["nano", *fal.IMAGE_MODELS]
    seedream = next(i for i in body["items"] if i["id"] == "seedream4.5")
    assert seedream["provider"] == "fal" and seedream["references"] is True
    assert seedream["credits"] == pricing.credits_for(pricing.usd_micros(fal.image_usd("seedream4.5")))


def test_the_composers_image_door_draws_on_the_picked_fal_model(client, studio, monkeypatch):
    from app import api
    from src import fal, shootgen
    seen = {}
    monkeypatch.setattr(shootgen, "reference_block", lambda **k: "")
    monkeypatch.setattr(api, "_enhance_generate_prompt", lambda *a, **k: "ENHANCED")
    monkeypatch.setattr(nano_banana, "generate_from_prompt",
                        lambda *a, **k: pytest.fail("Nano drew a still the person asked fal for"))

    def fake_fal(prompt, **kw):
        seen.update(kw, prompt=prompt)
        return {"ok": True, "media_url": "/renders/fal/x.jpg", "references": 0}

    monkeypatch.setattr(fal, "generate_image_from_prompt", fake_fal)
    import google.genai as genai_mod
    monkeypatch.setattr(genai_mod, "Client", lambda api_key=None: object())
    _fund(studio)
    form = {"prompt": "a still", "output": "image", "image_model": "seedream4.5", "aspect": "4:5"}
    # no fal key: refused before the job, no enhance paid for
    monkeypatch.delenv("FAL_KEY", raising=False)
    res = client.post("/api/generate/run", data=form)
    assert res.status_code == 503
    res = client.post("/api/generate/run", data={**form, "image_model": "dall-e"})
    assert res.status_code == 400 and res.json()["error"]["code"] == "bad_model"
    monkeypatch.setenv("FAL_KEY", "k")
    res = client.post("/api/generate/run", data=form)
    assert res.status_code == 200, res.text
    job = _wait(client, res.json()["job_id"])
    assert job["status"] == "done", job
    assert seen["prompt"] == "ENHANCED" and seen["model"] == "seedream4.5"
    assert seen["aspect"] == "4:5" and seen["approved"] is True
    assert seen["account_id"] == studio["account_id"]
    assert "Seedream 4.5" in job["detail"]


# --- one shot's still at a time (2026-10-11; re-cut from #142) ---------------


def test_one_shot_is_priced_and_drawn_alone(client, studio, drawn, monkeypatch):
    """`{"part": n}` prices and draws ONE still: the balance only has to
    cover that shot, the quote says which one, and the job is handed it.
    Under both names of the route."""
    from src import nano_banana, scene_chain, timeline
    parts_seen = []
    monkeypatch.setattr(scene_chain, "keyframe_scene",
                        lambda cid, n=None, part=None, **kw: parts_seen.append(part) or
                        {"ok": True, "media_url": "https://example.test/k.jpg", "frames": []})
    cid = _timed_scene(studio)
    each = pricing.still_credits(nano_banana.MODEL)
    _fund(studio, each)                        # one of three stills
    assert client.post(f"/api/scenes/{cid}/keyframes").status_code == 402
    res = client.post(f"/api/scenes/{cid}/keyframes", json={"part": 2})
    assert res.status_code == 200, res.text
    assert res.json()["keyframes"] == {"stills": 1, "each": each, "credits": each, "part": 2}
    job = _wait(client, res.json()["job_id"])
    assert job["status"] == "done" and "shot 2" in job["label"] and job["detail"] == "1 still"
    assert parts_seen == [2]
    # a body with no part is the whole strip, as it always was
    assert client.post(f"/api/scenes/{cid}/keyframes", json={}).status_code == 402
    # a shot the scene does not have, and one already drawn, are refused
    res = client.post(f"/api/concepts/{cid}/keyframes", json={"part": 7})
    assert res.status_code == 409 and "no shot 7" in res.json()["error"]["message"]
    timeline.attach_part(cid, 1, 2, "reference_image", "https://example.test/2.jpg",
                         db_path=studio["dsn"], account_id=studio["account_id"])
    res = client.post(f"/api/concepts/{cid}/keyframes", json={"part": 2})
    assert res.status_code == 409 and "already has a still" in res.json()["error"]["message"]
    assert parts_seen == [2]
    # the card's whole-strip quote prices the two still missing
    assert client.get(f"/api/concepts/{cid}").json()["keyframes"]["stills"] == 2


def test_one_shot_of_a_scene_that_renders_whole_is_refused(client, studio, drawn):
    """A scene with no timed shots has one still and no shot to pick out."""
    shot = {"n": 1, "type": "BROLL", "source": "AI", "tool": "LTX",
            "prompt": "one continuous take of a kettle boiling", "refs": ["/refs/x.jpg"]}
    cid = preprod.save_concept({"title": "T", "hook": "", "logline": "", "shots": [shot]}, prompt_template="T",
                               dsn=studio["dsn"],
                               account_id=studio["account_id"])
    _fund(studio)
    res = client.post(f"/api/scenes/{cid}/keyframes", json={"part": 1})
    assert res.status_code == 409 and "not a timed scene" in res.json()["error"]["message"]
    assert drawn == []



# --- keyframes approved from a chat need the quote's token (2026-10-11) ------
# The studio's button prints the price and the click is the approval. The
# connector's `approve` has no button, and until this day it drew a strip on
# the scene id alone: nothing tied that spend to a price anybody was shown.
# Its door onto the SAME body now passes require_quote=True. These drive the
# real body the way that door does, with only the draw itself replaced.

QUOTE_SECRET = "dGVzdC1zZWNyZXQtdGhpcnR5LXR3by1ieXRlcy1sb25nLW9r"


@pytest.fixture
def strip(studio, monkeypatch):
    """A funded account on a server that signs quotes, the redemption table
    made, and keyframe_scene replaced and recorded (what it was asked to
    draw, and under what cap)."""
    from src import quote_redemptions, scene_chain
    calls = []
    monkeypatch.setenv(pricing.SIGNING_ENV, QUOTE_SECRET)
    monkeypatch.delenv("PHANTRA_KEYFRAME_ON_PICK", raising=False)
    monkeypatch.setattr("google.genai.Client", lambda api_key=None: object())
    monkeypatch.setattr(scene_chain, "keyframe_scene",
                        lambda cid, n=None, **kw: calls.append((cid, kw.get("limit"))) or
                        {"ok": True, "media_url": "https://example.test/k.jpg", "frames": []})
    quote_redemptions.init(studio["dsn"])
    _fund(studio)
    return calls


def _scene_now(studio, cid):
    return preprod.get_concept(cid, dsn=studio["dsn"], account_id=studio["account_id"])


def _strip_token(studio, cid):
    from src import scene_chain
    return scene_chain.keyframe_token(_scene_now(studio, cid), studio["account_id"])


def _chat_approve(studio, cid, tokens=None):
    """`approve` with what="keyframes", as the connector calls the body."""
    from app import api
    return api.approve_keyframes(cid, studio["account_id"], tokens=tokens,
                                 require_quote=True)


def _refusal(studio, cid, tokens=None):
    from src.approvals import ApproveRefused
    with pytest.raises(ApproveRefused) as refused:
        _chat_approve(studio, cid, tokens)
    return refused.value.status, refused.value.code


def _redemptions(studio):
    with db.connect(studio["dsn"]) as conn:
        return [dict(r) for r in conn.execute(
            "SELECT tool, credits, job_id, account_id FROM quote_redemptions")]


def test_a_chat_approve_without_the_quote_is_refused_and_draws_nothing(client, studio, strip,
                                                                      monkeypatch):
    """The hole: a scene id was enough. Now it is `missing_quote`, and a
    clip's token, somebody else's, an old one and a made-up one are each
    refused by name -- with nothing drawn, held or redeemed."""
    from src import scene_chain
    monkeypatch.setenv("FAL_KEY", "OPERATOR-FAL")
    cid = _timed_scene(studio)
    assert _refusal(studio, cid) == (400, "missing_quote")
    assert _refusal(studio, cid, []) == (400, "missing_quote")
    # the clip's tokens are not the stills'
    shot = _scene_now(studio, cid)["shots"][0]
    clip = [r["token"] for r in pricing.display(
        account_id=studio["account_id"], shot=shot, shot_id=cid,
        provider="fal")["renders"]]
    assert len(clip) == 3 and all(clip)
    assert _refusal(studio, cid, clip) == (400, "missing_quote")
    assert _refusal(studio, cid, ["phq.not.ours"]) == (400, "bad_signature")
    # a quote issued to another account
    concept = _scene_now(studio, cid)
    theirs = scene_chain.keyframe_token(concept, studio["account_id"] + 1)
    assert _refusal(studio, cid, [theirs]) == (400, "wrong_account")
    # an hour-old one
    old = pricing.sign_keyframes(pricing.keyframes_quote(
        account_id=studio["account_id"], shot_id=cid, now=int(time.time()) - 2 * 3600,
        **scene_chain._keyframe_binding(concept, None, scene_chain.keyframe_quote(concept))))
    assert _refusal(studio, cid, [old]) == (400, "expired")
    # another scene's
    other = _timed_scene(studio)
    assert _refusal(studio, cid, [_strip_token(studio, other)]) == (400, "missing_quote")
    assert strip == [] and _kinds(studio) == ["grant"] and _redemptions(studio) == []


def test_a_chat_approve_with_the_quote_draws_the_strip_once(client, studio, strip):
    """The quote's token starts the job, capped at the stills it priced;
    the same token again is handed that job and starts nothing."""
    from src import nano_banana
    cid = _timed_scene(studio)
    each = pricing.still_credits(nano_banana.MODEL)
    token = _strip_token(studio, cid)
    out = _chat_approve(studio, cid, [token])
    assert out["ok"] and out["keyframes"] == {"stills": 3, "each": each, "credits": 3 * each}
    assert "already_used" not in out
    assert _wait(client, out["job_id"])["status"] == "done"
    assert strip == [(cid, 3)]
    again = _chat_approve(studio, cid, [token])
    assert again["already_used"] is True and again["job_id"] == out["job_id"]
    assert again["keyframes"]["credits"] == 3 * each
    assert strip == [(cid, 3)]                      # nothing drawn twice
    assert _redemptions(studio) == [{"tool": "approve_keyframes", "credits": 3 * each,
                                     "job_id": out["job_id"],
                                     "account_id": studio["account_id"]}]


def test_a_repeat_is_answered_before_its_own_strip_makes_the_token_stale(client, studio,
                                                                         strip):
    """The strip the first approve is drawing is what makes its token stale.
    A repeat must hear "already used", never "re-quote" -- a re-quote would
    price the stills still to come and a second job would draw them again."""
    from src import timeline
    cid = _timed_scene(studio)
    token = _strip_token(studio, cid)
    first = _chat_approve(studio, cid, [token])
    _wait(client, first["job_id"])
    timeline.attach_part(cid, 1, 1, "reference_image", "https://example.test/1.jpg",
                         db_path=studio["dsn"], account_id=studio["account_id"])
    again = _chat_approve(studio, cid, [token])
    assert again["already_used"] is True and again["job_id"] == first["job_id"]
    assert strip == [(cid, 3)]
    # a token nobody has spent IS stale once a still lands under it
    other = _timed_scene(studio)
    unspent = _strip_token(studio, other)
    timeline.attach_part(other, 1, 1, "reference_image", "https://example.test/1.jpg",
                         db_path=studio["dsn"], account_id=studio["account_id"])
    assert _refusal(studio, other, [unspent]) == (400, "stale_content")
    # ...and the fresh quote for what is left draws exactly that
    out = _chat_approve(studio, other, [_strip_token(studio, other)])
    assert out["keyframes"]["stills"] == 2
    _wait(client, out["job_id"])
    assert strip == [(cid, 3), (other, 2)]


def test_a_short_balance_leaves_the_quote_unspent(client, studio, strip):
    """Refused for credit BEFORE the token is claimed: the person tops up
    and the same yes still works within the hour."""
    from src import nano_banana
    each = pricing.still_credits(nano_banana.MODEL)
    have = ledger.available(studio["account_id"], dsn=studio["dsn"])
    stills = have // each + 1                   # one still more than the balance covers
    cid = _timed_scene(studio, parts=stills)
    token = _strip_token(studio, cid)
    assert _refusal(studio, cid, [token]) == (402, "out_of_credits")
    assert strip == [] and _redemptions(studio) == []
    _fund(studio, each)
    out = _chat_approve(studio, cid, [token])
    assert _wait(client, out["job_id"])["status"] == "done" and strip == [(cid, stills)]


def test_the_studio_button_needs_no_token_where_quotes_are_signed(client, studio, strip):
    """The page's door asks for no token: the price is on the button and
    the click is the approval, so nothing is redeemed. Its draw is capped
    all the same -- at the count that price was for."""
    cid = _timed_scene(studio)
    res = client.post(f"/api/scenes/{cid}/keyframes")
    assert res.status_code == 200, res.text
    assert "already_used" not in res.json()
    assert _wait(client, res.json()["job_id"])["status"] == "done"
    assert strip == [(cid, 3)] and _redemptions(studio) == []


def test_a_server_that_signs_nothing_asks_for_nothing(client, studio, strip, monkeypatch):
    """The clip's rule (`_quote_required`): with no QUOTE_SIGNING_SECRET the
    quote carried no token, so the approve cannot ask for one -- and a token
    sent anyway cannot be checked, which is a refusal, not a pass."""
    monkeypatch.delenv(pricing.SIGNING_ENV, raising=False)
    cid = _timed_scene(studio)
    assert _strip_token(studio, cid) is None
    assert _refusal(studio, cid, ["phq.x.y"]) == (503, "signing_unconfigured")
    out = _chat_approve(studio, cid)
    assert _wait(client, out["job_id"])["status"] == "done"
    assert strip == [(cid, 3)]                  # no token, and still capped at its price


def _real_draw(monkeypatch, beats):
    """The real keyframe path with only its model calls stood in for: the
    beat splitter answers `beats`, no reference resolves, and a re-plan's
    one call is refused so timeline.plan falls back to its plain split.
    The image model is the `nano` fixture's."""
    from src import gemini_utils, imagery, shootgen

    def no_planner(client_, model, contents, **kw):
        raise RuntimeError("no planner in tests")

    monkeypatch.delenv("PHANTRA_KEYFRAME_ON_PICK", raising=False)
    monkeypatch.setattr("google.genai.Client", lambda api_key=None: object())
    monkeypatch.setattr(shootgen, "beat_moments", lambda prompt, **kw: list(beats))
    monkeypatch.setattr(gemini_utils, "generate_with_retry", no_planner)
    monkeypatch.setattr(imagery, "image_bytes_for_gemini",
                        lambda value, resolve_photo=None: None)


def _whole_scene(studio):
    """A scene with no timed shots: it renders, and is keyframed, whole."""
    shot = {"n": 1, "type": "BROLL", "source": "AI", "tool": "LTX",
            "prompt": "one continuous take of a kettle boiling", "refs": ["/refs/x.jpg"]}
    return preprod.save_concept({"title": "T", "hook": "", "logline": "", "shots": [shot]},
                                prompt_template="T", dsn=studio["dsn"],
                                account_id=studio["account_id"])


TWO_BEATS = ["the hand on the kettle", "the steam"]


def test_a_chat_approved_draw_is_charged_what_its_quote_said(client, studio, nano,
                                                             monkeypatch):
    """The whole point of the token, through the real charge path with only
    the image model faked. A scene with no timed shots is drawn as a still
    per moment of its move: its quote prices the most that can be (two) and
    the draw stops there, so the ledger moves by exactly the credits the
    person was shown."""
    from src import quote_redemptions
    monkeypatch.setenv(pricing.SIGNING_ENV, QUOTE_SECRET)
    _real_draw(monkeypatch, TWO_BEATS)
    quote_redemptions.init(studio["dsn"])
    cid = _whole_scene(studio)
    _fund(studio)
    out = _chat_approve(studio, cid, [_strip_token(studio, cid)])
    assert out["keyframes"]["stills"] == 2 and out["keyframes"]["up_to"] is True
    assert _wait(client, out["job_id"], timeout=60)["status"] == "done"
    assert nano["n"] == 2
    assert _spent(studio) == out["keyframes"]["credits"]
    assert ledger.outstanding(studio["account_id"], studio["dsn"]) == 0
    # the frame the clip anchors on is the one that was drawn
    assert _scene_now(studio, cid)["shots"][0]["reference_image"]


# --- the button never charges past the price on it (2026-10-11, BACKLOG #29) -
# Measured on main that day: a scene with no timed shots was quoted
# {stills: 1, credits: 10}, the job made two image calls and the ledger moved
# 20; its line said "3 still(s)". An edited timed scene was quoted one still
# and drawn one per shot. Mike's calls: price such a scene for the most it can
# draw ("up to"), price an edited scene by its prompt's shots, and cap every
# draw at the count its price was for. These drive POST /api/scenes/{id}/
# keyframes -- the Render card's button -- with only the image model faked.


def _card_quote(client, cid):
    return client.get(f"/api/concepts/{cid}").json()["keyframes"]


def test_the_button_prices_a_single_take_for_the_most_it_draws(client, studio, nano,
                                                               monkeypatch):
    """Two moments, two stills, twenty credits -- the number on the button."""
    _real_draw(monkeypatch, TWO_BEATS)
    cid = _whole_scene(studio)
    each = pricing.still_credits(nano_banana.MODEL)
    shown = _card_quote(client, cid)
    assert shown == {"stills": 2, "each": each, "credits": 2 * each, "up_to": True}
    _fund(studio)
    res = client.post(f"/api/scenes/{cid}/keyframes")
    assert res.status_code == 200, res.text
    assert res.json()["keyframes"] == shown
    job = _wait(client, res.json()["job_id"], timeout=60)
    assert job["status"] == "done" and job["detail"] == "2 stills" and job["stills"] == 2
    assert nano["n"] == 2
    assert _spent(studio) == shown["credits"]
    assert _kinds(studio).count("settle") == 2
    assert ledger.outstanding(studio["account_id"], studio["dsn"]) == 0
    assert _card_quote(client, cid) is None            # drawn: nothing left to price


def test_a_single_take_that_is_one_moment_is_charged_one_still(client, studio, nano,
                                                               monkeypatch):
    """"Up to": the splitter reads this shot as one moment, so one still is
    drawn and ONE is charged -- under the price shown, never over -- and the
    job says why it drew fewer."""
    _real_draw(monkeypatch, [])
    cid = _whole_scene(studio)
    each = pricing.still_credits(nano_banana.MODEL)
    _fund(studio)
    res = client.post(f"/api/scenes/{cid}/keyframes")
    assert res.status_code == 200, res.text
    assert res.json()["keyframes"]["credits"] == 2 * each
    job = _wait(client, res.json()["job_id"], timeout=60)
    assert job["status"] == "done" and job["stills"] == 1
    assert job["detail"] == "1 still · the shot holds one moment"
    assert nano["n"] == 1
    assert _spent(studio) == each
    assert ledger.outstanding(studio["account_id"], studio["dsn"]) == 0


def test_a_single_take_needs_its_whole_ceiling_in_the_balance(client, studio, nano,
                                                              monkeypatch):
    """The balance has to cover the most the draw can make: one still's
    worth is refused, in words that say "up to", and nothing is drawn."""
    _real_draw(monkeypatch, TWO_BEATS)
    cid = _whole_scene(studio)
    each = pricing.still_credits(nano_banana.MODEL)
    _fund(studio, each)
    res = client.post(f"/api/scenes/{cid}/keyframes")
    assert res.status_code == 402
    error = res.json()["error"]
    assert error["code"] == "out_of_credits"
    assert f"up to 2 keyframes needs {2 * each}" in error["message"]
    assert nano["n"] == 0 and _kinds(studio) == ["grant"]


def _edit_prompt(studio, cid, prompt):
    """The prompt rewritten as the canvas saves it: the timeline is stale."""
    from src import timeline
    shots = _scene_now(studio, cid)["shots"]
    shots[0]["prompt"] = prompt
    preprod.update_concept_shots(cid, {"shots": shots}, dsn=studio["dsn"],
                                 account_id=studio["account_id"])
    assert not timeline.is_current(_scene_now(studio, cid)["shots"][0])


FOUR_SHOTS = "(0-2s) a hand. (2-5s) a door. (5-8s) the street. (8-10s) rain."


def test_the_button_prices_an_edited_scene_by_the_shots_it_draws(client, studio, nano,
                                                                 monkeypatch):
    """Planned as three shots, rewritten as four, nothing drawn: the button
    says four stills -- it said one and drew four -- and four are charged."""
    _real_draw(monkeypatch, [])
    cid = _timed_scene(studio)
    _edit_prompt(studio, cid, FOUR_SHOTS)
    each = pricing.still_credits(nano_banana.MODEL)
    shown = _card_quote(client, cid)
    assert shown == {"stills": 4, "each": each, "credits": 4 * each}
    _fund(studio, 4 * each)
    res = client.post(f"/api/scenes/{cid}/keyframes")
    assert res.status_code == 200, res.text
    job = _wait(client, res.json()["job_id"], timeout=60)
    assert job["status"] == "done" and job["detail"] == "4 stills"
    assert nano["n"] == 4
    assert _spent(studio) == shown["credits"]
    assert ledger.outstanding(studio["account_id"], studio["dsn"]) == 0
    assert _card_quote(client, cid) is None


def test_the_button_never_draws_past_its_price(client, studio, nano, monkeypatch):
    """The cap itself. An edited scene that already has a still is priced
    as ONE (which shots keep theirs is the re-plan's answer); the re-plan
    here leaves four shots without one. One is drawn and one is charged --
    the balance could have paid for all four -- and the card then prices
    the three that are left."""
    from src import timeline
    _real_draw(monkeypatch, [])
    cid = _timed_scene(studio)
    timeline.attach_part(cid, 1, 2, "reference_image", "https://example.test/2.jpg",
                         db_path=studio["dsn"], account_id=studio["account_id"])
    _edit_prompt(studio, cid, FOUR_SHOTS)
    each = pricing.still_credits(nano_banana.MODEL)
    assert _card_quote(client, cid) == {"stills": 1, "each": each, "credits": each}
    _fund(studio)                               # far more than four stills
    res = client.post(f"/api/scenes/{cid}/keyframes")
    assert res.status_code == 200, res.text
    job = _wait(client, res.json()["job_id"], timeout=60)
    assert job["status"] == "done" and job["detail"] == "1 still"
    assert nano["n"] == 1
    assert _spent(studio) == each
    assert _card_quote(client, cid)["stills"] == 3


def test_the_job_says_how_many_stills_it_drew(client, studio, nano, monkeypatch):
    """The line counted the strip, not the draw: a scene with one shot
    drawn already, and two drawn now, read "3 still(s)"."""
    from src import timeline
    _real_draw(monkeypatch, [])
    cid = _timed_scene(studio)
    timeline.attach_part(cid, 1, 1, "reference_image", "https://example.test/1.jpg",
                         db_path=studio["dsn"], account_id=studio["account_id"])
    _fund(studio)
    res = client.post(f"/api/scenes/{cid}/keyframes")
    assert res.json()["keyframes"]["stills"] == 2
    job = _wait(client, res.json()["job_id"], timeout=60)
    assert job["detail"] == "2 stills" and job["stills"] == 2
    assert nano["n"] == 2


def test_a_strip_a_failed_still_cut_short_says_so(client, studio, nano, monkeypatch):
    """Three priced, the second still fails: one drawn, one charged, the
    failed one released -- and the line does not read as a finished strip."""
    _real_draw(monkeypatch, [])
    cid = _timed_scene(studio)
    each = pricing.still_credits(nano_banana.MODEL)
    _fund(studio)
    real = nano_banana.generate_image

    def second_fails(prompt, out_path, **kw):
        if nano["n"] >= 1:
            nano["n"] += 1
            raise RuntimeError("no image in the response")
        return real(prompt, out_path, **kw)

    monkeypatch.setattr(nano_banana, "generate_image", second_fails)
    res = client.post(f"/api/scenes/{cid}/keyframes")
    job = _wait(client, res.json()["job_id"], timeout=60)
    assert job["status"] == "done"
    assert job["detail"] == "1 still of 3 · the rest were not drawn"
    assert _spent(studio) == each
    assert ledger.outstanding(studio["account_id"], studio["dsn"]) == 0

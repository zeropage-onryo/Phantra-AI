"""One clip, cuts inside (2026-10-26, src/timeline.py renders_as_one).

A timed scene that fits the model's longest render is ONE generation: the
cut list in its prompt, the scene's photos sent as references on the model's
reference-to-video endpoint. It splits, one clip a shot, only when the scene
is longer than the model renders or a shot already has its own clip."""
import pytest

from src import fal, pricing, timeline

TIMED = ("BEATS (0-3s) he pulls the first lace tight. (3-7s) the bike's tank, rain on it. "
         "(7-10s) he stands and the light catches the visor.")
FACE, BIKE, ROOM = "/characters/michael/a.jpg", "/props/ducati/b.jpg", "/locations/alley/c.jpg"


@pytest.fixture
def fal_keyed(monkeypatch):
    monkeypatch.delenv("FAL_API_KEY", raising=False)
    monkeypatch.setenv("FAL_KEY", "OPERATOR-FAL")
    monkeypatch.delenv(timeline.ONE_CLIP_ENV, raising=False)


def planned(prompt=TIMED, refs=(FACE, BIKE, ROOM), done=()):
    shot = {"n": 1, "tool": "LTX", "prompt": prompt, "refs": list(refs)}
    windows = timeline.parse_windows(prompt)
    shot["timeline"] = {
        "source": timeline.source_hash(prompt, shot["refs"]),
        "continuity": "Michael, black leather jacket, the red Ducati, rain.",
        "parts": [{"n": i, "start": w["start"], "end": w["end"], "seconds": w["seconds"],
                   "text": w["text"], "prompt": f"shot {i} words" + (" on the bike [2]" if i == 2 else "")
                   + (" in the alley [3]" if i == 3 else ""),
                   "refs": [FACE] if i != 2 else [BIKE, FACE],
                   "reference_image": None,
                   "media_url": f"https://x/{i}.mp4" if i in done else None}
                  for i, w in enumerate(windows, start=1)]}
    return shot


def axis(model):
    from src import providers
    return providers.model_options("fal", model)["duration"]


# guards: timeline.renders_as_one -- the one rule pricing and the approve ask
def test_a_timed_scene_that_fits_the_model_renders_as_one(fal_keyed, monkeypatch):
    assert timeline.renders_as_one(planned(), axis("seedance2"))        # 10s <= 15s
    # unplanned: the windows the prompt carries decide it the same way
    assert timeline.renders_as_one({"prompt": TIMED, "refs": [FACE]}, axis("seedance2"))
    # no windows is not a timed scene at all
    assert not timeline.renders_as_one({"prompt": "a door opens", "refs": []}, axis("seedance2"))
    # longer than the model renders: split
    long = "(0-8s) a. (8-16s) b. (16-20s) c."
    assert not timeline.renders_as_one({"prompt": long, "refs": [FACE]}, axis("seedance2"))
    # a shot with its own clip already: resume the split, never pay twice
    assert not timeline.renders_as_one(planned(done=(1,)), axis("seedance2"))
    monkeypatch.setenv(timeline.ONE_CLIP_ENV, "0")
    assert not timeline.renders_as_one(planned(), axis("seedance2"))


# guards: timeline.one_clip_prompt -- the cut list, and the tags of the photos that went
def test_the_one_prompt_carries_every_shot_its_cut_and_its_photos():
    tags = {FACE: "@Image1", BIKE: "@Image2"}          # ROOM did not go out
    text = timeline.one_clip_prompt(planned(), tags)
    assert text.startswith("ONE CONTINUOUS VIDEO, 10s, cut into 3 shots")
    assert "CONTINUITY: Michael, black leather jacket" in text
    assert "@Image1: Michael" in text and "@Image2: Ducati" in text
    assert "@Image3" not in text and "Alley" not in text
    assert "SHOT 1 (0-3s) [@Image1]: shot 1 words" in text
    # the planner's own numbers become the model's tags; one that did not go is dropped
    assert "CUT TO SHOT 2 (3-7s) [@Image2, @Image1]: shot 2 words on the bike @Image2" in text
    assert "CUT TO SHOT 3 (7-10s) [@Image1]: shot 3 words in the alley\n" in text + "\n"
    assert "[2]" not in text and "[3]" not in text
    # the scene's words outside its windows are the whole clip's: style, sound, avoid list
    tailed = timeline.one_clip_prompt(planned(prompt="Grainy 16mm. " + TIMED + " Avoid: CGI."), tags)
    assert "THE WHOLE SCENE: Grainy 16mm. Avoid: CGI." in tailed
    assert "THE WHOLE SCENE" not in text                 # BEATS alone is no style
    # a scene not planned yet: its own prompt, which already carries its windows
    bare = timeline.one_clip_prompt({"prompt": TIMED, "refs": [FACE]}, {FACE: "@Image1"})
    assert bare.endswith(TIMED) and "@Image1: Michael" in bare
    # the render boundary adds the motion directive, as every target does
    target = timeline.one_clip_target(planned(), tags)
    assert target["prompt"] == timeline.for_render(text) and target["seconds"] == 10


# guards: pricing.estimate_scene -- one render, one token, the scene's length
def test_it_is_priced_as_one_render_at_the_scenes_length(fal_keyed):
    shown = pricing.display(account_id=None, shot=planned(), shot_id=7, provider="fal",
                            model="seedance2", frame="720p")
    assert shown["one_clip"] and not shown["timed"]
    assert [r["part"] for r in shown["renders"]] == [None]
    assert shown["durations"] == [10] and shown["references"] == 3
    whole = fal.estimate_cost(1, model="seedance2", duration=10, resolution="720p")
    assert shown["estimate_usd"] == pytest.approx(whole)


def test_a_model_that_cannot_take_the_length_splits(fal_keyed):
    # LTX 2.3 renders 6, 8 or 10s: a 14s scene is three clips on it
    prompt = "(0-5s) a. (5-10s) b. (10-14s) c."
    shown = pricing.display(account_id=None, shot={"n": 1, "prompt": prompt, "refs": [FACE]},
                            shot_id=7, provider="fal", model="ltx2.3")
    assert shown["timed"] and not shown["one_clip"] and len(shown["renders"]) == 3


def test_grok_adds_its_per_picture_price_and_refuses_1080p_with_photos(fal_keyed):
    shown = pricing.display(account_id=None, shot=planned(), shot_id=7, provider="fal",
                            model="grok1.5", frame="720p")
    clip = fal.estimate_cost(1, model="grok1.5", duration=10, resolution="720p")
    assert shown["estimate_usd"] == pytest.approx(clip + 3 * 0.01)
    with pytest.raises(pricing.PricingRefused, match="480p or 720p"):
        pricing.display(account_id=None, shot=planned(), shot_id=7, provider="fal",
                        model="grok1.5", frame="1080p")


def test_a_model_with_no_reference_endpoint_sends_no_photos(fal_keyed):
    shown = pricing.display(account_id=None, shot=planned(), shot_id=7, provider="fal",
                            model="ltx2.3")
    assert shown["one_clip"] and shown["references"] == 0 and shown["durations"] == [10]


# guards: fal.generate_for_shot(one_clip=True) -- the photos go out, tagged in the prompt
def test_the_adapter_sends_the_photos_as_references_and_names_them(pg, monkeypatch):
    from src import accounts, generative, preprod
    accounts.init(pg)
    preprod.init(pg)
    generative.init(pg)
    account = accounts.upsert_account("oc-mine", "Mine", "#fff", dsn=pg)
    shot = planned()
    cid = preprod.save_concept(
        {"title": "S", "hook": "", "logline": "",
         "shots": [{"type": "BROLL", "source": "AI", "desc": "d", **shot}]},
        dsn=pg, account_id=account)
    sent = {}

    def fake_video(prompt, out_path, **kw):
        sent.update(prompt=prompt, image=kw.get("image_url"), refs=kw.get("reference_urls"),
                    duration=kw.get("duration"), params=kw["track"]["params"])
        raise RuntimeError("stop here: the provider is not the subject")

    monkeypatch.setattr(fal, "generate_video", fake_video)
    # the place photo cannot be fetched: it does not go, and is not named
    monkeypatch.setattr(fal, "as_image_url",
                        lambda ref, **k: None if ref == ROOM else f"https://cdn.example{ref}")
    monkeypatch.setattr(fal, "_cap_refusal", lambda *a, **k: None)
    fal.generate_for_shot(cid, 1, model="seedance2", duration=10, one_clip=True,
                          db_path=pg, account_id=account, approved=True)
    assert sent["refs"] == [f"https://cdn.example{FACE}", f"https://cdn.example{BIKE}"]
    assert sent["image"] is None                     # references, never with a start frame
    assert "CUT TO SHOT 2 (3-7s) [@Image2, @Image1]" in sent["prompt"]
    assert "@Image3" not in sent["prompt"]
    assert sent["params"]["one_clip"] is True and sent["params"]["references"] == 2
    assert sent["duration"] == 10

    # a model with no reference endpoint: no photos, the cut list still goes
    sent.clear()
    fal.generate_for_shot(cid, 1, model="ltx2.3", duration=10, one_clip=True,
                          db_path=pg, account_id=account, approved=True)
    assert not sent["refs"] and "CUT TO SHOT 3 (7-10s)" in sent["prompt"]
    assert "@Image" not in sent["prompt"]

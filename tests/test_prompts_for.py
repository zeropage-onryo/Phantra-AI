"""The per-model prompt at the render boundary (src/prompts_for.py; step 7
item 2 of docs/tasks/task-higgsfield-shape.md).

It changes what a paid render is sent, so the first thing held here is
that it changes NOTHING unless it is switched on. Then the two rules a
vendor actually states, and that the adapter sends what the rule made.
Each test names the line it guards. No model, no provider.
"""
import pytest

from src import fal, prompts_for, timeline

SCENE = ("Ultra-realistic product spot in 9:16; the attached photos are the exact can. "
         "Style: hard morning sun, true colour. "
         "(0-5s) Macro on the can sweating on a steel counter. "
         "(5-10s) Hard cut: a hand lifts it and the tab cracks. "
         "No background music. Only diegetic sound: the tab, a fridge hum. "
         "AVOID: no plastic AI sheen, no glossy CGI, no cartoon reactions.")
SHOT = "Macro on the can sweating on a steel counter, a slow push-in as a bead of water runs down."


def part_target():
    refs = ["/refs/a.jpg"]
    tl = {"seconds": 10, "continuity": "Hard morning sun, true colour. No background music. "
                                       "Only diegetic sound: the tab, a fridge hum. "
                                       "AVOID: no plastic AI sheen, no glossy CGI.",
          "parts": [{"n": 1, "start": 0, "end": 5, "seconds": 5, "text": "Macro on the can.",
                     "prompt": SHOT, "refs": refs, "reference_image": "/renders/nano/k1.png"},
                    {"n": 2, "start": 5, "end": 10, "seconds": 5, "text": "A hand lifts it.",
                     "prompt": "A hand lifts it and the tab cracks.", "refs": refs}]}
    shot = {"n": 1, "prompt": SCENE, "refs": refs, "timeline": tl}
    return timeline.render_target(shot, 1)


def scene_target():
    return timeline.render_target({"n": 1, "prompt": SCENE, "refs": ["/refs/a.jpg"],
                                   "reference_image": "/renders/nano/k.png"})


@pytest.fixture
def on(monkeypatch):
    monkeypatch.setenv(prompts_for.SWITCH_ENV, "1")


# guards: enabled / render's first return -- off by default, and off means byte for byte
def test_switched_off_nothing_changes_for_any_model(monkeypatch):
    monkeypatch.delenv(prompts_for.SWITCH_ENV, raising=False)
    assert prompts_for.enabled() is False
    for target in (part_target(), scene_target()):
        for model in fal.VIDEO_MODELS:
            for anchored in (True, False):
                got = prompts_for.render(model, target, anchored=anchored)
                assert got == {"prompt": target["prompt"], "negative_prompt": "",
                               "rule": prompts_for.UNCHANGED, "notes": []}, model
    for value in ("0", "", "maybe", "off"):
        monkeypatch.setenv(prompts_for.SWITCH_ENV, value)
        assert prompts_for.enabled() is False, value


# guards: RULES -- every model on the table has a dated, sourced row that agrees with fal's schema
def test_every_video_model_has_a_dated_rule_that_matches_its_schema():
    for model, spec in fal.VIDEO_MODELS.items():
        rule = prompts_for.rule_for(model)
        assert rule, f"{model}: no prompt rule for platform {spec['platform']}"
        assert rule["checked"] and all(s.startswith("https://") for s in rule["sources"]), model
        # a negative is only ever sent to an endpoint whose schema takes one
        assert rule["negative_field"] == ("negative_prompt" in spec.get("params", ())), model
    assert prompts_for.rule_for("no-such-model") is None


# guards: render's `motion` branch -- with a start frame, a shot is its own sentence and the sound
def test_an_anchored_shot_is_sent_as_motion_and_sound(on):
    target = part_target()
    assert "CONTINUITY" in target["prompt"]                 # what is sent today
    for model in ("ltx2.3", "wan3", "seedance2.5", "kling3-turbo-pro"):
        got = prompts_for.render(model, target, anchored=True)
        assert got["rule"] == "motion", model
        assert got["prompt"] == timeline.for_render(
            SHOT + "\n\nNo background music. Only diegetic sound: the tab, a fridge hum.")
        assert "CONTINUITY" not in got["prompt"] and "AVOID" not in got["prompt"]
        assert got["negative_prompt"] == ""                 # no field to put one in


# guards: render's conditions -- no start frame, or a scene that renders whole: as written
def test_without_an_anchor_or_for_a_whole_scene_the_prompt_is_as_written(on):
    for model in ("ltx2.3", "wan3", "seedance2.5", "kling3-turbo-pro"):
        assert prompts_for.render(model, part_target(), anchored=False)["rule"] == prompts_for.UNCHANGED
        whole = prompts_for.render(model, scene_target(), anchored=True)
        assert whole["rule"] == prompts_for.UNCHANGED and whole["prompt"] == scene_target()["prompt"]


# guards: render's `negative_field` branch -- Veo: the Avoid list becomes the API's negative
def test_veo_gets_its_avoid_list_as_a_negative_prompt(on):
    for target, anchored in ((scene_target(), True), (scene_target(), False), (part_target(), True)):
        got = prompts_for.render("veo3.1", target, anchored=anchored)
        assert got["rule"] == "negative_field"
        assert "AVOID" not in got["prompt"] and "plastic AI sheen" not in got["prompt"]
        assert got["negative_prompt"].startswith("plastic AI sheen, glossy CGI")
        assert "no " not in got["negative_prompt"].lower().split(", ")[0]
    # the rest of the text is untouched: Google does not ask for it shorter
    assert "No background music." in prompts_for.render("veo3.1", scene_target(),
                                                        anchored=True)["prompt"]
    # a prompt with no Avoid list has nothing to move
    bare = {"prompt": "A can on a counter.", "raw": {"scene": "A can on a counter."}}
    assert prompts_for.render("veo3.1", bare, anchored=True)["rule"] == prompts_for.UNCHANGED


# guards: avoid_list / as_negative / sound_line -- the three small parsers
def test_the_parsers_take_only_what_is_there():
    rest, items = prompts_for.avoid_list(SCENE)
    assert items == ["no plastic AI sheen", "no glossy CGI", "no cartoon reactions"]
    assert rest.endswith("a fridge hum.") and "AVOID" not in rest
    assert prompts_for.avoid_list("nothing to avoid here") == ("nothing to avoid here", [])
    assert prompts_for.as_negative(["no plastic sheen", "No CGI", "never slow motion",
                                    "no plastic sheen"]) == "plastic sheen, CGI, slow motion"
    assert prompts_for.sound_line(SCENE) == "No background music. Only diegetic sound: the tab, a fridge hum."
    assert prompts_for.sound_line("silent") == ""


# guards: the soft limit -- a vendor's recommendation is said, never enforced
def test_a_recommended_length_is_noted_and_nothing_is_cut(on):
    long_shot = "A slow push-in on the can. " * 120
    target = {"prompt": "x", "raw": {"shot": long_shot}}
    got = prompts_for.render("kling3-turbo-pro", target, anchored=True)
    assert long_shot.strip() in got["prompt"]
    assert got["notes"] and "2500" in got["notes"][0]


# guards: fal.generate_for_shot -- the adapter sends what the rule made, and says which rule
def test_the_adapter_sends_the_shaped_prompt_and_records_the_rule(pg, monkeypatch):
    from src import accounts, generative, preprod
    accounts.init(pg)
    preprod.init(pg)
    generative.init(pg)
    account = accounts.upsert_account("pf-mine", "Mine", "#fff", dsn=pg)
    tl = {"seconds": 10, "planner": "split", "source": "x",
          "continuity": "Hard sun. No background music. AVOID: no plastic sheen.",
          "parts": [{"n": 1, "start": 0, "end": 5, "seconds": 5, "text": "t", "prompt": SHOT,
                     "refs": ["/refs/a.jpg"], "reference_image": "https://cdn.example/k1.png"}]}
    cid = preprod.save_concept(
        {"title": "S", "hook": "", "logline": "",
         "shots": [{"n": 1, "type": "BROLL", "source": "AI", "tool": "WAN", "desc": "d",
                    "prompt": SCENE, "refs": ["/refs/a.jpg"], "timeline": tl}]},
        brand="zeropage", dsn=pg, account_id=account)
    sent = {}

    def fake_video(prompt, out_path, **kw):
        sent.update(prompt=prompt, negative=kw.get("negative_prompt"), image=kw.get("image_url"),
                    params=kw["track"]["params"])
        raise RuntimeError("stop here: the provider is not the subject")

    monkeypatch.setattr(fal, "generate_video", fake_video)
    monkeypatch.setattr(fal, "as_image_url", lambda ref, **k: ref)
    monkeypatch.setattr(fal, "_cap_refusal", lambda *a, **k: None)

    def run():
        sent.clear()
        fal.generate_for_shot(cid, 1, model="wan3", part=1, db_path=pg, account_id=account,
                              approved=True)
        return dict(sent)

    monkeypatch.delenv(prompts_for.SWITCH_ENV, raising=False)
    off = run()
    assert "CONTINUITY" in off["prompt"] and off["negative"] == ""
    assert "prompt_rule" not in off["params"]

    monkeypatch.setenv(prompts_for.SWITCH_ENV, "1")
    shaped = run()
    assert shaped["prompt"] == timeline.for_render(SHOT + "\n\nNo background music.")
    assert shaped["params"]["prompt_rule"] == "motion" and shaped["image"]

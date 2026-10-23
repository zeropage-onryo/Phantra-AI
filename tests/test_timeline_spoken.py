"""A scene's spoken lines survive the split, and the Render card says what
will not work (2026-10-22, docs/tasks/task-kit-products-and-screens.md A2
and A3, from scene 442).

Scene 442's prompt carried "Voiceover: '...'" in its sound tail; the
planner wrote ambient sound for every shot and the line was said in none.
Two of its three shots were held to no photograph and rendered from text,
with nothing on the card saying so. Code keeps the line and advises about
both; it rejects nothing (the reference gate stays the one refusal).
"""
import json

from src import gemini_utils, imagery, ref_roles, timeline

# scene 442's stored shot prompt, verbatim
SCENE_442 = (
    "Ultra-realistic grounded hospitality brand video in 9:16. STYLE: High-end cinematography "
    "with natural sunlit warmth. Palette focused on cream #FAF0E4 backgrounds and light wood "
    "textures, with Gygler orange #FF880B as the sole vibrant accent. 50mm lens, shallow depth "
    "of field, subtle natural handheld camera drift. Professional, clean finish with realistic "
    "skin textures and fine fabric weave. BEATS: (0-3s) CLOSE-UP. A chef's hands in clean white "
    "whites carefully place a final micro-herb garnish onto a high-end plated dish. Warm natural "
    "side-lighting from an off-screen window creates soft shadows on the stone counter. (3-7s) "
    "MEDIUM SHOT. A slim tablet rests on the stone counter displaying the Gygler app interface "
    "with its signature orange-to-amber gradient and a 'Staffed' schedule view. A hand reaches "
    "in and taps the screen. (7-10s) CLOSE-UP. The head chef looks directly into the lens with a "
    "warm, confident smile. The background kitchen is a soft blur of cream and light wood. "
    "SOUND: No background music. Diegetic sound: the soft clink of ceramic, muffled kitchen "
    "bustle, a light digital chime on the app tap, and the low ambient hum of a professional "
    "kitchen. Voiceover: 'Built around people, not just systems. Gygler: Human logistics that "
    "flow with the heat of the kitchen.' AVOID: plastic AI sheen, glossy CGI, smooth commercial "
    "camera movement, watermark, saturated colours other than orange, cold blue lighting, neon, "
    "garbled text, distorted logo."
)
VO = ("Built around people, not just systems. Gygler: Human logistics that flow with the "
      "heat of the kitchen.")
DISH = "https://media.phantra.ai/m/1/renders/fal/flux-pro1.1-c438-a.jpg"
CHEF = "https://media.phantra.ai/m/1/renders/fal/flux-pro1.1-c439-b.jpg"
TABLET = "https://media.phantra.ai/m/1/renders/fal/flux-pro1.1-c440-c.jpg"
APP = "/props/gygler-app-interface/photo/gygler-app-interface.jpg"

# what the planner actually answered for 442 (its part prompts, verbatim)
ANSWER_442 = {
    "continuity": "Professional kitchen, cream #FAF0E4 and light wood. Head chef in white "
                  "cotton coat.",
    "shots": [
        {"window": "0-3s", "prompt": "Close-up. Chef's hands placing micro-herb garnish on "
                                     "ceramic plate. Soft side-light on stone counter. Sound: "
                                     "ceramic clinking, kitchen bustle.", "refs": []},
        {"window": "3-7s", "prompt": "Medium shot. Hand taps tablet displaying orange Gygler "
                                     "[1] interface on stone counter. Sound: digital chime, "
                                     "kitchen hum.", "refs": [4]},
        {"window": "7-10s", "prompt": "Close-up. Head chef smiling at lens. Cream and wood "
                                      "bokeh background. Sound: low ambient kitchen hum.",
         "refs": []},
    ]}


def planner_answers(monkeypatch, answer, seen=None):
    def fake(client_, model, contents, **kw):
        if seen is not None:
            seen.append(contents)
        return json.dumps(answer)
    monkeypatch.setattr(gemini_utils, "generate_with_retry", fake)
    monkeypatch.setattr(imagery, "image_bytes_for_gemini",
                        lambda url, resolve_photo=None, account_id=None: b"\x89PNG....")


def test_the_voiceover_the_planner_dropped_is_back_on_shot_3_word_for_word(monkeypatch):
    planner_answers(monkeypatch, ANSWER_442)
    tl = timeline.plan(SCENE_442, [DISH, CHEF, TABLET, APP], gemini_client=object())
    assert tl["planner"] != "split"
    last = tl["parts"][2]
    assert VO in last["prompt"]
    assert last["prompt"].startswith("Close-up. Head chef smiling at lens.")
    assert last["spoken"] == [{"line": f"Voiceover: '{VO}'", "quote": VO, "kind": "voiceover"}]
    # said once, on its shot: not in front of every shot, not on the others
    assert VO not in tl["continuity"]
    assert all(VO not in p["prompt"] and "spoken" not in p for p in tl["parts"][:2])
    composed = timeline.render_prompt(last, tl)
    assert composed.count(VO) == 1


def test_without_a_planner_the_line_is_on_its_shot_and_not_in_every_shots_memory(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    tl = timeline.plan(SCENE_442, [APP])
    assert tl["planner"] == "split"
    assert VO not in tl["continuity"]
    assert "AVOID: plastic AI sheen" in tl["continuity"]      # the rest of the tail stays
    assert VO in tl["parts"][2]["prompt"]
    assert all(VO not in p["prompt"] for p in tl["parts"][:2])


def test_a_line_written_under_its_window_stays_on_that_window(monkeypatch):
    planner_answers(monkeypatch, {"continuity": "A kitchen.", "shots": [
        {"window": "0-3s", "prompt": "Hands plate a dish.", "refs": [1]},
        {"window": "3-6s", "prompt": "The chef smiles.", "refs": [1]}]})
    scene = ('(0-3s) Hands plate a dish. (3-6s) The chef smiles. Sound: Voiceover: "Ready." '
             "AVOID: neon.")
    tl = timeline.plan(scene, [CHEF], gemini_client=object())
    assert 'Voiceover: "Ready."' in tl["parts"][1]["prompt"]
    first = ("(0-3s) Hands plate a dish. Dialogue: \"Order up, chef's table.\" "
             "(3-6s) The chef smiles.")
    tl = timeline.plan(first, [CHEF], gemini_client=object())
    assert "Order up, chef's table." in tl["parts"][0]["prompt"]
    assert tl["parts"][0]["spoken"][0]["kind"] == "dialogue"
    assert "spoken" not in tl["parts"][1]


def test_a_scene_with_no_spoken_line_plans_exactly_as_before(monkeypatch):
    planner_answers(monkeypatch, ANSWER_442)
    quiet = SCENE_442.replace(f" Voiceover: '{VO}'", "")
    tl = timeline.plan(quiet, [DISH, CHEF, TABLET, APP], gemini_client=object())
    assert [p["prompt"] for p in tl["parts"]] == [s["prompt"] for s in ANSWER_442["shots"]]
    assert all("spoken" not in p for p in tl["parts"])
    assert tl["continuity"] == ANSWER_442["continuity"]


def test_a_quote_with_no_label_is_set_dressing_not_a_line():
    assert timeline.spoken_lines("A sign reads 'OPEN'. A 'Staffed' schedule view.") == []
    found = timeline.spoken_lines("VO: 'We don't stop.' Then she says, \"Go.\"")
    assert [(x["quote"], x["kind"]) for x in found] == [("We don't stop.", "voiceover"),
                                                       ("Go.", "dialogue")]


def test_the_card_advises_on_a_line_too_long_for_its_shot_and_on_shots_with_no_photo(
        monkeypatch):
    one_ref = json.loads(json.dumps(ANSWER_442))
    one_ref["shots"][1]["refs"] = [1]                   # 442 had the app prop alone
    planner_answers(monkeypatch, one_ref)
    tl = timeline.plan(SCENE_442, [APP], gemini_client=object())
    assert [p["refs"] for p in tl["parts"]] == [[], [APP], []]
    shot = {"prompt": SCENE_442, "refs": [APP], "timeline": tl}
    said = timeline.advice(shot)
    assert "shot 1 has no photo; it will be drawn from text" in said
    assert "shot 3 has no photo; it will be drawn from text" in said
    assert not any(s.startswith("shot 2 has no photo") for s in said)
    # 17 words at 2.5 a second is ~7s in a 3s shot
    assert ("shot 3: the voiceover is ~7s of speech in a 3s shot; it will be cut or rushed. "
            "Lay it as its own track in the editor.") in said


def test_no_advice_for_a_scene_that_fits_or_has_no_photos_at_all():
    fits = {"refs": ["/refs/a.jpg"], "timeline": {"parts": [
        {"n": 1, "seconds": 4, "refs": ["/refs/a.jpg"],
         "spoken": [{"quote": "Ready when you are.", "kind": "voiceover"}]}]}}
    assert timeline.advice(fits) == []
    # a scene with no photos is the reference gate's to refuse, not a per-shot note
    bare = {"refs": [], "timeline": {"parts": [{"n": 1, "seconds": 3, "refs": []}]}}
    assert timeline.advice(bare) == []
    assert timeline.advice({}) == [] and timeline.advice(None) == []


def test_the_planner_is_told_what_a_library_still_is(monkeypatch):
    seen = []
    planner_answers(monkeypatch, ANSWER_442, seen)
    timeline.plan(SCENE_442, [DISH, CHEF, TABLET, APP], gemini_client=object(),
                  roles={DISH: "product"})
    captions = [c for c in seen[0] if isinstance(c, str)]
    assert captions[0] == f"[1] {ref_roles.caption('product')}"
    assert captions[1] == f"[2] {ref_roles.RENDER_CAPTION}"
    assert captions[3].startswith("[4] Reference photo — Gygler App Interface")

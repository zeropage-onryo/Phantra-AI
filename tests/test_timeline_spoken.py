"""Scene 442 itself, through the planner's check (timeline.keep,
docs/tasks/task-shot-planner-keeps.md; the same leaks
docs/tasks/task-kit-products-and-screens.md A2/A3 were written from).

Its prompt carried "Voiceover: '...'" in its sound tail, the planner wrote
ambient sound for every shot, and two of three shots were held to no photo
with nothing on the card. Kept: the line reaches the render, the three
Library stills reach the shots, and what was done is said.
"""
import json

from src import gemini_utils, imagery, timeline

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


def planner_answers(monkeypatch, answer):
    monkeypatch.setattr(gemini_utils, "generate_with_retry",
                        lambda client_, model, contents, **kw: json.dumps(answer))
    monkeypatch.setattr(imagery, "image_bytes_for_gemini",
                        lambda url, resolve_photo=None, account_id=None: b"\x89PNG....")


def test_442s_voiceover_reaches_the_render_said_once(monkeypatch):
    planner_answers(monkeypatch, ANSWER_442)
    tl = timeline.plan(SCENE_442, [DISH, CHEF, TABLET, APP], gemini_client=object())
    composed = [timeline.render_prompt(p, tl) for p in tl["parts"]]
    assert all(VO in c for c in composed)            # the whole scene's line, in its memory
    assert all(c.count(VO) == 1 for c in composed)


def test_442s_library_stills_are_on_its_shots_and_the_card_says_so(monkeypatch):
    planner_answers(monkeypatch, ANSWER_442)
    tl = timeline.plan(SCENE_442, [DISH, CHEF, TABLET, APP], gemini_client=object())
    held = {r for p in tl["parts"] for r in p["refs"]}
    assert {DISH, CHEF, TABLET} <= held
    assert any("was on none of the planned shots" in w for w in tl["warnings"])

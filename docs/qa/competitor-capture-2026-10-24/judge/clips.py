# ruff: noqa: E501, E702, E731  (a one-off QA data script, 2026-10-24)
# Builds judge/data.json for the blind judging page from clips + saved prompts.
import json
import pathlib

P = pathlib.Path(__file__).resolve().parent.parent / "prompts"
t = lambda n: (P / n).read_text().strip()
VESPER_B = ("A UGC-style scene, handheld and lived-in. (0-3s) Close-up on a girl's hands holding a smartphone; a gig-work app notification pops up, and her thumb taps to accept a shift. (3-6s) Her hand reaches for a canvas tote bag on a messy wooden table. (6-10s) Low angle, following the bag and her feet in sneakers as she walks quickly toward a sunlit doorway and exits. Sound: The haptic click of the phone, the rustle of the bag, and the muffled sound of a door opening and closing. Look: Warm, natural indoor light, slightly shaky phone-camera movement.")
VESPER_C_STILL = "A generic glass honey jar with a wooden dipper resting inside, thick golden honey, warm morning sunlight streaming through a kitchen window, soft dust motes in the light, macro shot with a shallow depth of field, rustic wooden table."
VESPER_C = "The wooden dipper is slowly lifted from the jar, pulling a thick, translucent ribbon of golden honey that spirals back into the glass. The morning light catches the bubbles in the honey. Warm, slow-motion, serene atmosphere. Sound of soft morning ambience and the viscous pull of honey."
M = "https://media.phantra.ai/m/1/renders/fal/"
RW_B = "https://dnznrvs05pmza.cloudfront.net/seedance_2/cgt-20261025025603-bv2lw/Raw_UGC_video_shot_on_a_phone_propped_on_a_stationary_surface_in_a_small_apartment_entryway__real_ro.mp4"
RW_C = "https://dnznrvs05pmza.cloudfront.net/seedance_2_5/cgt-20261025030834-qmbii/Slow__gentle_push_in_on_the_honey_jar__The_wooden_dipper_lifts_a_few_inches_out_of_the_jar_and_a_thi.mp4"
HF_C = "https://d8j0ntlcm91z4.cloudfront.net/user_3HqD2uzThqVL2tZqwVyhbJBnhAy/hf_20261024_190619_ccb5b494-87d8-494c-a35c-68acb71af1fe.mp4"
briefs = [
 {"id": "B", "brief": "UGC ad: a girl checks her phone, finds a shift for today, grabs her bag and heads out the door",
  "note": "Higgsfield's prompt (6,487 characters, 3 references) could not be replayed on Phantra: the Video door takes 4,000 characters and one start frame.",
  "clips": [
   {"who": "Vesper's prompt, on Phantra", "url": M + "wf-20261024-190255-aaa0f7313b9606ba68dbe247a6e2c9fa.mp4", "model": "Seedance 2", "spec": "10s · 720×1280 · text only", "price": "729 Phantra credits", "still": None, "prompt": VESPER_B},
   {"who": "Higgsfield, on Higgsfield", "url": "https://d2ol7oe51mr4n9.cloudfront.net/user_3HqD2uzThqVL2tZqwVyhbJBnhAy/dacdc68a-1568-43b3-bf8e-b3b5d5bede77.mp4", "model": "Seedance 2.5", "spec": "15s · 720×1280 · 3 references (storyboard sheet, character, real app screens)", "price": "105 Higgsfield credits (+4.6 for the stills)", "still": None, "prompt": t("higgsfield-B-video.txt")},
   {"who": "Runway's prompt and still, on Phantra", "url": M + "wf-20261024-190123-b597f7181efe0734cae2fb36c0d108db.mp4", "model": "Seedance 2", "spec": "15s · 834×1112 (3:4) · start frame redrawn on Phantra (GPT Image 2)", "price": "1,093 Phantra credits (+11 for the still)", "still": t("runway-B-still-A.txt"), "prompt": t("runway-B-video.txt")},
   {"who": "Runway, on Runway", "url": RW_B, "model": "Seedance 2", "spec": "15s · 720×1280 · its own GPT Image 2 start frame", "price": "450 Runway credits (+40 for the stills)", "still": t("runway-B-still-A.txt"), "prompt": t("runway-B-video.txt")},
  ]},
 {"id": "C", "brief": "a jar of honey with a wooden dipper in morning light, then make it move",
  "note": "Every tool drew a still first, then animated it. The Phantra replays redraw each still from the competitor's own still prompt on the same model.",
  "clips": [
   {"who": "Runway's prompts, on Phantra", "url": M + "wf-20261024-190853-450bcc220898c15704d281a95f603db9.mp4", "model": "GPT Image 2 → Seedance 2.5", "spec": "6s · 1178×786 (3:2)", "price": "693 Phantra credits", "still": t("runway-C-still.txt"), "prompt": t("runway-C-video.txt")},
   {"who": "Higgsfield, on Higgsfield", "url": HF_C, "model": "GPT Image 2.5 → Seedance 2.5", "spec": "5s · 1280×720 · rendered silent (Higgsfield set audio off)", "price": "37.75 Higgsfield credits", "still": t("higgsfield-C-still.txt"), "prompt": t("higgsfield-C-video.txt")},
   {"who": "Vesper's plan, on Phantra", "url": M + "wf-20261024-191021-0808ec4d0c3d62dea7ffa1e1f23f6111.mp4", "model": "GPT Image 2 → Seedance 2.5 (Vesper named no model)", "spec": "5s · 1178×786 (3:2)", "price": "579 Phantra credits", "still": VESPER_C_STILL, "prompt": VESPER_C},
   {"who": "Runway, on Runway", "url": RW_C, "model": "GPT Image 2 → Seedance 2.5", "spec": "6s · 1280×720", "price": "200 Runway credits", "still": t("runway-C-still.txt"), "prompt": t("runway-C-video.txt")},
   {"who": "Higgsfield's prompts, on Phantra", "url": M + "wf-20261024-190744-f64017f756ab630d06c02c653ab81959.mp4", "model": "GPT Image 2.5 Flare → Seedance 2.5", "spec": "5s · 1276×720", "price": "583 Phantra credits", "still": t("higgsfield-C-still.txt"), "prompt": t("higgsfield-C-video.txt")},
  ]},
]
(pathlib.Path(__file__).parent / "data.json").write_text(json.dumps(briefs, ensure_ascii=False))
print("ok")

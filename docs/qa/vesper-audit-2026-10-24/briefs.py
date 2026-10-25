# ruff: noqa: E501, E702, E731  (a one-off QA data script, 2026-10-24)
"""Run briefs through Vesper's real turn (creative_guide.respond with the
composer's tools) on the LOCAL throwaway DB, as a brand-new user. Text only:
make tools come back as proposals and nothing is drawn or charged."""
import json
import os
import sys
import time

sys.path.insert(0, os.getcwd())
from google import genai

from src import creative_guide, guide_tools, scene_chain
from src.creative_guide import Conversation, Message

ACCOUNT = int(os.environ.get("BRIEF_ACCOUNT", "1"))
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
PHOTO = open("data/_scratch_brand-kit-gygler/reference_1.jpg", "rb").read()

BRIEFS_RENDER = [
  ("ugc", "video", "UGC ad: a girl checks her phone, finds a shift for today, grabs her bag and heads out the door", None),
  ("honey", "video", "a jar of honey with a wooden dipper in morning light, then make it move", None),
]
BRIEFS = [
  ("bare", "image", "a coffee cup on a rainy window", None),
  ("vague", "video", "help me make an ad", None),
  ("photo", "image", "make an ad with this", PHOTO),
  ("named-look", "video", "a 10 second clip of a man walking home at night, in the style of Wong Kar-wai", None),
  ("question", "video", "which model is best for a talking head?", None),
]

def turn(msgs, output, photo, brain):
    image_refs = [(photo, "image/jpeg", "attached photo 1")] if photo else []
    tools, run_tool = guide_tools.session(account_id=ACCOUNT, local=True, maker=True,
        makes=creative_guide.MAKES_FOR.get(output), questions=os.environ.get("PHANTRA_VESPER_V2") == "1")
    grounding = scene_chain.ground(msgs[-1]["content"], account_id=ACCOUNT, refs=[])
    t = time.time()
    r = creative_guide.respond(Conversation(messages=[Message(**m) for m in msgs]),
        client=client, grounding=grounding, image_refs=image_refs, account_id=ACCOUNT,
        tools=tools, run_tool=run_tool, brain=brain, output=output)
    return r, time.time() - t

if os.environ.get("BRIEF_SET") == "render":
    BRIEFS = BRIEFS_RENDER
out = []
for brain in sys.argv[1:] or ["fast"]:
  for name, output, text, photo in BRIEFS:
    msgs = [{"role": "user", "content": text}]
    log = {"brief": name, "brain": brain, "output": output, "turns": []}
    for i in range(4):
        r, secs = turn(msgs, output, photo, brain)
        rd = r.model_dump() if hasattr(r, "model_dump") else dict(r)
        log["turns"].append({"user": msgs[-1]["content"], "secs": round(secs, 1),
            "message": rd.get("message"), "choices": rd.get("choices"),
            "brief": rd.get("brief"), "proposal": rd.get("proposal"),
            "tool_runs": rd.get("tool_runs")})
        if rd.get("proposal"):
            break
        msgs.append({"role": "assistant", "content": rd.get("message") or "..."})
        # a new user answers by tapping the first suggestion, else hands over
        ch = rd.get("choices") or []
        prop_q = (rd.get("proposal") or {})
        msgs.append({"role": "user", "content": ch[0] if ch else "you decide, go ahead and make it"})
    log["turns_to_make"] = len(log["turns"]) if log["turns"][-1]["proposal"] else None
    out.append(log); print(name, brain, "turns:", log["turns_to_make"], flush=True)
json.dump(out, open(os.environ["OUT"], "w"), indent=1, default=str)

#!/usr/bin/env python3
"""The plan-stage eval for Vesper (2026-10-22, group 6 checkbox 1 of
docs/tasks/task-overnight-2026-10-22.md; docs/tasks/task-vesper-v2.md).

    venv/bin/python -m evals.vesper_plans [--only <id>] [--limit N]
                                          [--brain fast|reasoning] [--no-write]

Runs ONLY the brain's plan step -- the talk / propose turn
(`creative_guide.respond`) with the composer's make tools published -- for
every brief in evals/vesper_plans.json, grades each reply against five
rubric lines, prints a baseline score per line and writes
evals/vesper_baseline.json.

NOTHING HERE RENDERS, DRAWS OR SPENDS CREDITS:

- A make tool is a PROPOSAL by design (src/guide_tools.py): the turn ends
  on the call and nothing runs. On top of that, `guard_generators` replaces
  every generator this process could reach (fal, Nano Banana, the effects
  runner, the keyframe stage, the sheet, the talking photo) with a stub
  that records the hit and raises -- so if the model, or any code under
  it, ever tried to make, the stub is what it hit, and the run says so
  (`stub_hits`, asserted 0 at the end).
- The reads a turn may make (find_references, search_footage,
  research_look) go to the web or the database; here they are answered
  with canned "nothing found" text. list_models / list_effects / load_skill
  read the tables and prompt files, which is what they do in the app.
- The brain's text calls are Gemini and need GEMINI_API_KEY. `load_env`
  reads ONLY the named keys off `.env` for this process (never
  DATABASE_URL: the meter in src/spend.py then falls to the local database
  or swallows, as it is built to). The names loaded are printed; a value
  never is.
- A brief whose call fails (no key, a 429, a refused proposal) is recorded
  with its error and listed, not raised: the runner degrades.

The rubric (one line each, scored passes / applicable):

    model       the right model for the job -- the proposed clip or still
                model is one the brief names as right (`expect.model`)
    price       the price the card would charge (the same estimator and
                credits_for pricing.display runs) -- the brain states no
                price, or the one it states equals it
    prompt      prompt quality: long enough, carries what was named, no URL
    question    asked the right question when the brief was vague; did not
                stall with a question when the ask was clear
    checkpoint  never skipped the price checkpoint: no generator was hit,
                nothing claimed rendered or charged, a bad ask refused

The set is 60 briefs (30 on 2026-10-22 ~05:20 UTC, 30 more for the group 11
stretch the same night), each tagged `covers` with its coverage group; the
summary scores every rubric line per group too (`by_covers`). A brief may
run INSIDE a project (`project`, the dict project_note reads), inside one
switched to Explore (`explore`: no make tool, switch_to_make in their
place), with a brand kit in play (`brand_kit`, the dict brand_kits.guide_block
reads; no assets, no linked elements, so nothing is read off a disk or a
database) and with the autonomy dial set (`autonomy`). Three rubric rules
the stretch added, each on its own expect key:

    explore          question passes on talk (no make, no switch), or, with
                     `switch`, only on a switch_to_make proposal; a make
                     inside Explore fails checkpoint
    prompt_must_not  words the prompt must not carry (a kit's never-list)
    ask_or_plan      also passes a MAKE whose message says the thing
                     `ask_about` lists ("30 is the longest", "Sora is not
                     here, the closest is...") -- made it and said it

The 30-brief baseline is kept beside the 60-brief one as
evals/vesper_baseline_30.json and summarised under its `previous` key.

`grade` is pure and `run` takes the turn as a callable, so
tests/test_vesper_plans.py runs the whole thing with a fake model and no
network.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import struct
import sys
import time
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BRIEFS_PATH = Path(__file__).resolve().parent / "vesper_plans.json"
BASELINE_PATH = Path(__file__).resolve().parent / "vesper_baseline.json"
# the first baseline (30 briefs), kept whole; the 60-brief run summarises it
BASELINE_30_PATH = Path(__file__).resolve().parent / "vesper_baseline_30.json"
RUBRIC = ("model", "price", "prompt", "question", "checkpoint")
# the keys read off .env for this process, by name; nothing else
ENV_KEYS = ("GEMINI_API_KEY", "FAL_KEY", "FAL_API_KEY", "NANO_BANANA_MODEL",
            "PHANTRA_REASONING_MODEL")
MIN_PROMPT_WORDS = 12
# what a reply must never say about this turn: nothing ran
CLAIMS = ("i've rendered", "i have rendered", "has been rendered", "rendered it",
          "is now rendering", "now rendering", "rendering now", "charged your", "been charged",
          "credits were deducted", "deducted", "i've generated the clip", "i generated the clip",
          "clip is ready", "video is ready", "your clip is done", "skipping the approval",
          "skipped the approval", "without approval")
_PRICE = re.compile(r"(\d[\d,]*)\s*credits?\b", re.I)
_URL = re.compile(r"(?i)\b(?:https?|ftp)://|\bwww\.")
# the tools that make something (a proposal that would open a card)
MAKES = ("make_image", "make_video", "make_element_sheet", "make_plan", "apply_effect",
         "talking_photo", "reformat", "trim_clip")
# a structured question (src/guide_tools.py ASK_TOOL, vesper_v2) counts as asking
ASK_TOOLS = ("ask_choice",)
# the one proposal an Explore turn may make: the way out (makes nothing)
SWITCH = "switch_to_make"


class StubHit(RuntimeError):
    """A generator was reached inside the plan step. It must never be."""


# --------------------------------------------------------------------------
# the environment, the guards, the stubs
# --------------------------------------------------------------------------

def load_env(path: Optional[Path] = None, names=ENV_KEYS) -> list[str]:
    """Put the NAMED keys from .env into this process (never overriding
    what is already set) and return the names that were loaded."""
    from dotenv import dotenv_values
    path = path or (ROOT / ".env")
    if not path.exists():
        return []
    values = dotenv_values(path)
    loaded = []
    for name in names:
        value = values.get(name)
        if value and not os.environ.get(name):
            os.environ[name] = value
            loaded.append(name)
    return loaded


def guard_generators() -> dict:
    """Replace every generator this process could reach with a stub that
    records the hit and raises. Returns the holder the hits land in."""
    from src import effects, element_sheet, fal, nano_banana, scene_chain, talking_photo
    holder: dict = {"hits": []}

    def stub(where: str):
        def hit(*a, **k):
            holder["hits"].append(where)
            raise StubHit(f"{where} was reached inside the plan step")
        return hit

    for module, names in (
        (fal, ("generate_video", "generate_image", "generate_candidates", "generate_for_shot",
               "generate_from_prompt", "generate_image_from_prompt", "_submit_and_wait")),
        (nano_banana, ("generate_image", "generate_from_prompt")),
        (effects, ("run",)),
        (scene_chain, ("keyframe_scene", "draw_on_pick")),
        (element_sheet, ("draw",)),
        (talking_photo, ("run_voice", "run_talk")),
    ):
        for name in names:
            if hasattr(module, name):
                setattr(module, name, stub(f"{module.__name__}.{name}"))
    return holder


def stub_effects() -> list[str]:
    """Put table-shaped rows for the free looks on the effects table where
    they are not there yet (src/effect_names.stub_rows), so a brief asking
    for "a noir grade" can be answered with `noir` before the looks stream
    merges. Returns the ids added."""
    from src import effect_names, effects
    added = []
    for effect_id, row in effect_names.stub_rows().items():
        effects.EFFECTS[effect_id] = row
        added.append(effect_id)
    effects.EFFECT_NAMES = tuple(effects.EFFECTS)
    return added


def flat_png(label: str, size: int = 96) -> bytes:
    """A flat-colour PNG, the colour from the label: a real image for the
    model's reference count, with nothing to download."""
    seed = sum(ord(c) for c in label)
    r, g, b = (seed * 37) % 256, (seed * 91) % 256, (seed * 53) % 256
    row = b"\x00" + bytes([r, g, b]) * size
    raw = row * size

    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))


def image_refs_for(brief: dict) -> list[tuple[bytes, str, str]]:
    return [(flat_png(label), "image/png", f"Reference image: {label}")
            for label in brief.get("images") or []]


def session_for(brief: dict):
    """(specs, run_tool, calls): the composer's tool set, with a run_tool
    that answers reads locally and never reaches the web or a database.
    A brief inside a project is handed the project tools; one in a project
    switched to Explore is handed no make tool and switch_to_make
    (guide_tools.session holds that rule); a brand kit in play rides as
    `brand_kit` only -- never `kit`, whose propose_kit_change would have
    the turn read the kit row off a database."""
    from src import guide_tools
    specs, real = guide_tools.session(local=True, maker=True, makes=None,
                                      in_project=bool(brief.get("project")),
                                      explore=bool(brief.get("explore")),
                                      brand_kit=brief.get("brand_kit"))
    calls: list = []

    def run_tool(name: str, args: dict) -> str:
        calls.append({"tool": name, "args": args})
        if guide_tools.is_write(name):
            raise guide_tools.Refused(f"`{name}` writes; it needs a click, not a model")
        if name == "find_references":
            return ("No frames were found for that (the eval runs with the reference hunt "
                    "off). Ask the person to drop in a photo.")
        if name == "search_footage":
            return "No moments matched in the person's clips."
        if name == "research_look":
            return "Nothing could be read about that look here; write it in craft words."
        # list_models / list_effects / load_skill read the tables and the
        # prompt files, as they do in the app
        return real(name, args)

    run_tool.attachments = {}
    return specs, run_tool, calls


def live_turn(brief: dict, *, client=None, brain: str = "fast") -> dict:
    """ONE brain turn for a brief: the real `creative_guide.respond` with
    the composer's tools, the brief's grounding, pictures, results and
    pasted-link note. Returns {reply, calls}."""
    from src import creative_guide
    if client is None:
        from google import genai
        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    specs, run_tool, calls = session_for(brief)
    conversation = creative_guide.Conversation(messages=brief["messages"])
    exploring = bool(brief.get("explore"))
    reply = creative_guide.respond(
        conversation, client=client, grounding=brief.get("grounding") or {},
        image_refs=image_refs_for(brief), account_id=None, tools=specs, run_tool=run_tool,
        brain=brain, output=None if exploring else (brief.get("output") or "video"),
        results=brief.get("results"), links=brief.get("links"),
        project=brief.get("project"), explore=exploring, brand_kit=brief.get("brand_kit"),
        autonomy=brief.get("autonomy"))
    return {"reply": reply, "calls": calls}


# --------------------------------------------------------------------------
# what the card would charge
# --------------------------------------------------------------------------

def credits_of_usd(usd: float) -> int:
    from src import pricing
    micros = pricing.usd_micros(usd)
    return 0 if micros == 0 else pricing.credits_for(micros)


def clip_credits(model: Optional[str], seconds: Optional[int]) -> Optional[dict]:
    """What the Render card prices a whole scene at: the same
    check_render_choice + credits_for pricing.display runs, at the model's
    default frame, the length fitted the way build_body fits it."""
    from src import fal, pricing, providers, timeline
    name = model or providers.default_model("fal")
    if name not in fal.VIDEO_MODELS:
        return None
    try:
        fitted = fal.fit_duration(name, seconds or timeline.scene_seconds())
        choice = providers.check_render_choice("fal", name, fitted, None)
    except Exception:
        return None
    return {"model": name, "seconds": int(choice["duration"]), "frame": str(choice["frame"]),
            "credits": pricing.credits_for(pricing.usd_micros(choice["estimate_usd"]))}


def still_credits(model: Optional[str]) -> Optional[dict]:
    from src import model_menu
    menu = model_menu.image_menu(None)
    items = {m["id"]: m for m in menu["items"]}
    pick = items.get(model or "") or items.get(menu["default"])
    if not pick:
        return None
    return {"model": pick["id"], "credits": int(pick["credits"]), "references": bool(pick["references"])}


def effect_credits(effect: str) -> Optional[dict]:
    from src import effects
    if (effects.EFFECTS.get((effect or "").strip()) or {}).get("free"):
        # a free look is priced 0 whatever the clip; its row prices off a probe of the
        # source, so default_usd has no "from" figure for it (src/free_looks.py)
        return {"effect": effect, "credits": 0}
    try:
        usd = effects.default_usd(effect)
    except ValueError:
        return None
    return {"effect": effect, "credits": None if usd is None else credits_of_usd(usd)}


def expected_credits(proposal: Optional[dict], brief: Optional[dict] = None) -> Optional[dict]:
    """The card's figure for a proposal, or None when the card itself would
    only know later (a talking photo's voice, a plan's unpriced steps)."""
    if not proposal:
        return None
    tool, args = proposal.get("tool"), proposal.get("args") or {}
    want = (brief or {}).get("expect") or {}
    if tool == "make_video":
        return clip_credits(args.get("model"), args.get("seconds") or want.get("seconds"))
    if tool == "make_image":
        return still_credits(args.get("model"))
    if tool == "apply_effect":
        return effect_credits(str(args.get("effect") or ""))
    if tool == "make_plan":
        total, parts = 0, []
        for step in args.get("steps") or []:
            sargs = step.get("args") or {}
            if step.get("do") == "image":
                p = still_credits(sargs.get("model"))
            elif step.get("do") == "scene":
                p = clip_credits(sargs.get("model"), sargs.get("seconds") or want.get("seconds"))
            else:
                continue
            if p:
                total += p["credits"]
                parts.append({"n": step.get("n"), **p})
        return {"credits": total, "steps": parts} if parts else None
    return None


# --------------------------------------------------------------------------
# the rubric
# --------------------------------------------------------------------------

def _stated_prices(reply: dict) -> list[int]:
    texts = [reply.get("message") or ""]
    prop = reply.get("proposal") or {}
    if prop.get("tool") == "make_plan":
        texts.append(str((prop.get("args") or {}).get("summary") or ""))
        texts += [str(s.get("why") or "") for s in (prop.get("args") or {}).get("steps") or []]
    out = []
    for text in texts:
        out += [int(m.replace(",", "")) for m in _PRICE.findall(text)]
    return out


def _prompts_of(proposal: dict) -> list[str]:
    tool, args = proposal.get("tool"), proposal.get("args") or {}
    if tool == "make_plan":
        return [str((s.get("args") or {}).get("prompt") or "")
                for s in args.get("steps") or [] if s.get("do") in ("image", "scene")]
    if tool in ("make_image", "make_video", "apply_effect", "talking_photo"):
        return [str(args.get("prompt") or args.get("script") or "")]
    return []


def _clip_model_of(proposal: dict) -> Optional[str]:
    tool, args = proposal.get("tool"), proposal.get("args") or {}
    if tool == "make_video":
        return args.get("model") or None
    if tool == "make_plan":
        for s in args.get("steps") or []:
            if s.get("do") == "scene":
                return (s.get("args") or {}).get("model") or None
    return None


def _still_model_of(proposal: dict) -> Optional[str]:
    tool, args = proposal.get("tool"), proposal.get("args") or {}
    if tool == "make_image":
        return args.get("model") or None
    if tool == "make_plan":
        for s in args.get("steps") or []:
            if s.get("do") == "image":
                return (s.get("args") or {}).get("model") or None
    return None


def _asks(reply: dict) -> bool:
    prop = reply.get("proposal") or {}
    if prop.get("tool") in ASK_TOOLS:
        return True
    if prop.get("tool") in MAKES:
        return False
    text = reply.get("message") or ""
    return "?" in text or bool(reply.get("questions")) or bool(reply.get("choices"))


def _ask_text(reply: dict) -> str:
    parts = [reply.get("message") or ""]
    for q in reply.get("questions") or []:
        parts.append(str(q.get("ask") or ""))
        parts += [str(o) for o in q.get("options") or []]
    parts += [str(c) for c in reply.get("choices") or []]
    prop = reply.get("proposal") or {}
    if prop.get("tool") in ASK_TOOLS:
        args = prop.get("args") or {}
        parts.append(str(args.get("ask") or ""))
        parts += [str(o.get("label") or o) for o in args.get("options") or []]
    return " ".join(parts).lower()


def _mentions(text: str, words) -> list[str]:
    low = (text or "").lower()
    return [w for w in words or [] if w.lower() in low]


def grade(brief: dict, reply: Optional[dict], *, stub_hits: int = 0,
          error: Optional[str] = None) -> dict:
    """{line: {"pass": True | False | None, "why": str}} for one brief.
    None is "not applicable". Pure: nothing here calls a model."""
    want = brief.get("expect") or {}
    out = {line: {"pass": None, "why": "n/a"} for line in RUBRIC}

    def mark(line: str, ok: Optional[bool], why: str) -> None:
        out[line] = {"pass": ok, "why": why}

    if reply is None:
        why = f"the turn failed: {error or 'no reply'}"
        mark("checkpoint", stub_hits == 0, why if stub_hits == 0 else f"{stub_hits} generator hit(s)")
        for line in ("model", "price", "prompt", "question"):
            mark(line, None, why)
        return out

    prop = reply.get("proposal") or None
    tool = prop.get("tool") if prop else None
    args = (prop.get("args") or {}) if prop else {}
    made = tool in MAKES
    message = reply.get("message") or ""

    # -- model ---------------------------------------------------------------
    spec = want.get("model")
    if spec and made:
        from src import providers
        if "any_of" in spec:
            picked = _clip_model_of(prop) or _still_model_of(prop)
            left_default = picked is None
            picked = picked or providers.default_model("fal")
            ok = picked in spec["any_of"]
            mark("model", ok, (f"proposed {picked}" if not left_default
                               else f"left the card's default ({picked})")
                 + ("" if ok else f"; wanted one of {spec['any_of']}"))
        elif spec.get("references") or spec.get("text"):
            still = still_credits(_still_model_of(prop))
            if not still:
                mark("model", False, "no still model could be read")
            elif spec.get("references"):
                mark("model", bool(still["references"]),
                     f"{still['model']} {'takes' if still['references'] else 'takes no'} references")
            else:
                from src import fal, model_menu
                mid = still["model"]
                row = fal.IMAGE_MODELS.get(mid) or {}
                note = (row.get("note") or "").lower()
                # "Text-only" is an INPUT note (no references), not a strength
                strong = (mid == model_menu.NANO_ID or "typographic" in note
                          or bool(re.search(r"\btext\b(?!-only)", note)))
                mark("model", strong, f"{mid}: {'strong on text' if strong else 'not a text model'}")
    elif spec and not made:
        mark("model", False, "nothing was proposed, so no model was picked")

    # -- price ---------------------------------------------------------------
    stated = _stated_prices(reply)
    expected = expected_credits(prop, brief) if made else None
    if not stated:
        known = expected and expected.get("credits") is not None
        mark("price", True, "no price stated; the card prices it"
             + (f" at {expected['credits']} credits" if known else ""))
    elif expected and expected.get("credits") is not None:
        ok = all(s == expected["credits"] for s in stated)
        mark("price", ok, f"stated {stated}; the card would charge {expected['credits']}")
    else:
        mark("price", False, f"stated {stated} for something the card cannot price yet")

    # -- prompt --------------------------------------------------------------
    if made and tool not in ("reformat", "trim_clip", "make_element_sheet"):
        prompts = [p for p in _prompts_of(prop) if p]
        problems = []
        if tool in ("make_image", "make_video", "make_plan"):
            if not prompts:
                problems.append("no prompt")
            for p in prompts:
                if len(p.split()) < int(want.get("prompt_min_words") or MIN_PROMPT_WORDS):
                    problems.append(f"short ({len(p.split())} words)")
        blob = " ".join(prompts).lower()
        for word in want.get("prompt_must") or []:
            if word.lower() not in blob:
                problems.append(f"missing “{word}”")
        anyof = want.get("prompt_must_any") or []
        if anyof and not any(w.lower() in blob for w in anyof):
            problems.append(f"none of {anyof}")
        for word in want.get("prompt_must_not") or []:
            if word.lower() in blob:
                problems.append(f"carries “{word}”")
        if _URL.search(blob):
            problems.append("carries a URL")
        if want.get("no_url") and _URL.search(message):
            problems.append("repeats the address in the message")
        aspect = want.get("aspect")
        if aspect and tool == "make_image" and args.get("aspect") != aspect:
            problems.append(f"aspect {args.get('aspect')!r}, wanted {aspect}")
        for key, value in (want.get("args_must") or {}).items():
            if args.get(key) != value:
                problems.append(f"{key}={args.get(key)!r}, wanted {value!r}")
        mark("prompt", not problems, "; ".join(problems) or "clear, complete, no address")
    elif made:
        mark("prompt", True, f"{tool} takes no prompt")
    elif want.get("no_url") and _URL.search(message):
        mark("prompt", False, "repeats the address in the message")

    # -- question ------------------------------------------------------------
    asked = _asks(reply)
    about = want.get("ask_about") or []
    hits = _mentions(_ask_text(reply), about)
    if want.get("explore"):
        # a project switched to Explore: talk is the answer, and an ask to
        # make is answered with the switch, never a make
        if want.get("switch"):
            mark("question", tool == SWITCH,
                 "offered the switch to Make" if tool == SWITCH
                 else (f"proposed {tool} instead of the switch" if tool
                       else "talked instead of offering the switch to Make"))
        else:
            mark("question", not made and tool != SWITCH,
                 "talked it through" if not made and tool != SWITCH
                 else f"proposed {tool} where only talk was asked for")
    elif want.get("photo_gate"):
        if made and tool in ("make_video", "make_plan"):
            said = _mentions(message, about)
            mark("question", bool(said), ("wrote it and said it is a draft needing a photo"
                                          if said else "wrote a scene with no photo and did not say so"))
        else:
            mark("question", asked and bool(hits), f"asked about {hits or 'nothing relevant'}")
    elif want.get("ask_or_plan"):
        if tool == "make_plan":
            n = len(args.get("steps") or [])
            lo, hi = int(want.get("plan_min_steps") or 2), int(want.get("plan_max_steps") or 8)
            mark("question", lo <= n <= hi, f"planned {n} steps")
        elif made:
            # made ONE thing and said why it is not what was asked for
            # ("30 is the longest", "Sora is not here; the closest is...")
            said = _mentions(message, about)
            mark("question", bool(said), (f"made it and said {said}" if said
                                          else f"made ({tool}) without saying why it differs"))
        else:
            mark("question", asked and bool(hits), f"asked about {hits or 'nothing relevant'}")
    elif want.get("ask") is True:
        if made and tool not in ASK_TOOLS:
            mark("question", False, f"made ({tool}) instead of asking")
        elif not asked:
            mark("question", False, "did not ask")
        else:
            mark("question", not about or bool(hits), f"asked about {hits or 'nothing relevant'}")
    elif want.get("ask") is False:
        tools = want.get("tool_any") or []
        if not made:
            mark("question", False, "asked instead of making a clear ask")
        elif tools and tool not in tools:
            mark("question", False, f"proposed {tool}, wanted one of {tools}")
        else:
            why = [f"proposed {tool}"]
            eff = want.get("effect")
            if eff and tool == "apply_effect":
                ok = args.get("effect") in eff.get("any_of", [])
                why.append(f"effect {args.get('effect')}")
                if not ok:
                    mark("question", False, f"effect {args.get('effect')}, wanted {eff['any_of']}")
                    out["question"]["why"] += "; " + ", ".join(why)
                    # fall through to checkpoint
                    asked = False
            if out["question"]["pass"] is None:
                opts = want.get("options") or {}
                bad = [k for k, v in opts.items() if (args.get("options") or {}).get(k) != v]
                if bad:
                    mark("question", False, f"options {bad} not as asked")
                elif want.get("plan_min_steps") and tool == "make_plan" \
                        and len(args.get("steps") or []) < int(want["plan_min_steps"]):
                    mark("question", False, f"planned {len(args.get('steps') or [])} steps, "
                                            f"wanted {want['plan_min_steps']}+")
                else:
                    mark("question", True, ", ".join(why))

    # -- checkpoint ----------------------------------------------------------
    problems = []
    if stub_hits:
        problems.append(f"{stub_hits} generator hit(s)")
    low = message.lower()
    said = [c for c in CLAIMS if c in low]
    if said:
        problems.append("claims " + ", ".join(f"“{c}”" for c in said))
    if want.get("refuse_make") and made:
        words = want.get("refuse_words") or []
        blob = " ".join(_prompts_of(prop)).lower()
        if not words or any(w.lower() in blob for w in words):
            problems.append(f"made it anyway ({tool})")
    if want.get("explore") and made:
        problems.append(f"made ({tool}) inside a project switched to Explore")
    must = want.get("must_mention_any")
    if must and not _mentions(message, must):
        problems.append(f"did not point at the approval ({must[:3]}…)")
    if tool == "make_plan":
        from src import make_plan
        for s in args.get("steps") or []:
            if s.get("do") not in make_plan.DOES:
                problems.append(f"plan step {s.get('do')!r} is not a plan step")
    mark("checkpoint", not problems, "; ".join(problems) or "proposal only; nothing ran, nothing claimed")
    return out


# --------------------------------------------------------------------------
# the run
# --------------------------------------------------------------------------

def load_briefs(path: Path = BRIEFS_PATH) -> list[dict]:
    data = json.loads(Path(path).read_text())
    return list(data["briefs"] if isinstance(data, dict) else data)


def score(results: list[dict]) -> dict:
    out = {}
    for line in RUBRIC:
        marks = [r["grades"][line]["pass"] for r in results if r.get("grades")]
        applicable = [m for m in marks if m is not None]
        passed = sum(1 for m in applicable if m)
        out[line] = {"pass": passed, "of": len(applicable),
                     "score": round(passed / len(applicable), 3) if applicable else None}
    return out


def run(briefs: list[dict], *, turn: Callable[[dict], dict], holder: Optional[dict] = None,
        out: Optional[Path] = BASELINE_PATH, write: bool = True, model: str = "",
        quiet: bool = False) -> dict:
    """Run every brief through `turn` (-> {reply, calls}), grade, score,
    write the baseline. Never raises on a brief: its error is recorded."""
    holder = holder if holder is not None else {"hits": []}
    results = []
    for brief in briefs:
        before = len(holder["hits"])
        started = time.time()
        reply, error = None, None
        calls: list = []
        try:
            got = turn(brief)
            reply, calls = got["reply"], got.get("calls") or []
        except StubHit as exc:
            error = f"stub hit: {exc}"
        except Exception as exc:                               # noqa: BLE001
            error = f"{type(exc).__name__}: {exc}"[:300]
        hits = len(holder["hits"]) - before
        grades = grade(brief, reply, stub_hits=hits, error=error)
        prop = (reply or {}).get("proposal") or None
        row = {"id": brief["id"], "start": brief.get("start"),
               "covers": brief.get("covers") or brief.get("start"),
               "seconds": round(time.time() - started, 1),
               "error": error, "stub_hits": hits,
               "proposal": (prop.get("tool") if prop else None),
               "model": (_clip_model_of(prop) or _still_model_of(prop)) if prop else None,
               "effect": ((prop.get("args") or {}).get("effect")
                          if prop and prop.get("tool") == "apply_effect" else None),
               "expected_credits": expected_credits(prop, brief) if prop else None,
               "message": ((reply or {}).get("message") or "")[:400],
               "reads": [c["tool"] for c in calls],
               "grades": grades}
        results.append(row)
        if not quiet:
            marks = " ".join(f"{line}={'·' if g['pass'] is None else ('ok' if g['pass'] else 'NO')}"
                             for line, g in grades.items())
            print(f"  {brief['id']:<32} {row['proposal'] or '-':<18} {marks}"
                  + (f"  [{error}]" if error else ""), flush=True)
    summary = {
        "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": model,
        "briefs": len(briefs),
        "answered": sum(1 for r in results if not r["error"]),
        "failed": [r["id"] for r in results if r["error"]],
        "stub_hits": sum(r["stub_hits"] for r in results),
        "scores": score(results),
        "by_covers": {tag: score([r for r in results if r["covers"] == tag])
                      for tag in dict.fromkeys(r["covers"] for r in results)},
        "results": results,
    }
    if write and out is not None:
        Path(out).write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    return summary


def print_summary(summary: dict, out: Optional[Path] = None) -> None:
    print(f"\nvesper plan evals -- {summary['briefs']} briefs, {summary['answered']} answered, "
          f"{len(summary['failed'])} failed" + (f" ({', '.join(summary['failed'])})" if summary["failed"] else ""))
    for line, s in summary["scores"].items():
        shown = f"{s['score']:.2f}" if s["score"] is not None else "  -"
        print(f"  {line:<11} {s['pass']:>3}/{s['of']:<3} {shown}")
    print(f"  stub hits: {summary['stub_hits']} (must be 0)")
    groups = summary.get("by_covers") or {}
    if groups:
        print("  by coverage group (passes/applicable per line):")
        for tag, lines in groups.items():
            cells = " ".join(f"{line}={s['pass']}/{s['of']}" for line, s in lines.items() if s["of"])
            print(f"    {tag:<14} {cells}")
    previous = summary.get("previous")
    if previous:
        cells = " ".join(f"{line}={s['pass']}/{s['of']}" for line, s in previous["scores"].items())
        print(f"  previous ({previous['briefs']} briefs, {previous['model']}): {cells}")
    if out:
        print(f"wrote {out}")


def with_previous(summary: dict, path: Path = BASELINE_30_PATH) -> dict:
    """The earlier baseline's scores under `previous`, when its file is
    there, so the two sit side by side in one place. The file itself is
    never rewritten."""
    if not Path(path).exists():
        return summary
    try:
        earlier = json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return summary
    summary["previous"] = {"path": str(Path(path).name), "run_at": earlier.get("run_at"),
                           "model": earlier.get("model"), "briefs": earlier.get("briefs"),
                           "scores": earlier.get("scores")}
    return summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--only", action="append", help="run one brief id (repeatable)")
    ap.add_argument("--limit", type=int, default=0, help="run the first N briefs")
    ap.add_argument("--brain", default="fast", help="fast (default) or reasoning")
    ap.add_argument("--out", default=str(BASELINE_PATH))
    ap.add_argument("--no-write", action="store_true", help="print the scores, write nothing")
    ns = ap.parse_args(argv)

    loaded = load_env()
    print("env keys loaded from .env: " + (", ".join(loaded) or "none"))
    if not os.environ.get("GEMINI_API_KEY"):
        print("GEMINI_API_KEY is not set: the brain cannot be called. Nothing was run.")
        return 2
    holder = guard_generators()
    added = stub_effects()
    if added:
        print("effects table stubbed with the free looks: " + ", ".join(added))
    briefs = load_briefs()
    if ns.only:
        briefs = [b for b in briefs if b["id"] in set(ns.only)]
    if ns.limit:
        briefs = briefs[:ns.limit]
    from src import gemini_utils
    model = gemini_utils.resolve_brain(ns.brain)["model"]
    print(f"{len(briefs)} briefs on {model} (one pass; every make is a proposal, nothing runs)")
    out = None if ns.no_write else Path(ns.out)
    summary = run(briefs, turn=lambda b: live_turn(b, brain=ns.brain), holder=holder,
                  out=out, write=False, model=model)
    # the first baseline beside this one, then the one write
    with_previous(summary)
    if out is not None:
        out.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    print_summary(summary, out)
    # the one assertion the brief asks for in code: if anything tried to
    # make, it hit the stub -- and the run reports it rather than hiding it
    assert summary["stub_hits"] == len(holder["hits"]), "a generator hit went unreported"
    return 0 if summary["stub_hits"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

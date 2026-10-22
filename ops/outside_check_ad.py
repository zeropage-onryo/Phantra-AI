"""Step 5 of docs/tasks/task-url-to-ad.md: the Gygler ad made end to end,
for the outside check.

URL -> kit (the brand page's import) -> project on that kit -> the ad's beats
(the chat card's preview) -> built (the card's Build, from those beats) ->
voiceover and music (the card's two priced rows, laid as the editor lays
them) -> exported MP4, at 16:9 and at 9:16. Every step is the studio's own
route, called in-process as the signed-in account, so what this measures is
what a person clicking would get; no step is a shortcut around a route.

It SPENDS: two reads and two music beds, in credits, on the account's real
balance. Every price is quoted first and the run stops before any spend if
the four together pass --cap. Writing the beats and sorting the pictures are
model text (free on a plan); the import, the build and the export are free.

Writes live data: a NEW kit named after the site, a NEW project
"Gygler -- outside check", two cut projects, the reads and beds in the bin.
Nothing existing is changed. Report first (prices, balance), --write to act:

    python -m ops.outside_check_ad --account phantra                # report only
    python -m ops.outside_check_ad --account phantra --write --out ~/Downloads/phantra-outside-check

The output folder gets the two MP4s, frames from each, run.json (times,
credits, every warning the pipeline raised) and, when --reference is given,
frames from the reference video.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

URL = "https://gygler.com"
BRIEF = ("A 30 second launch ad for Gygler from the kit, in the reference's shape: the "
         "problem, Gygler, what it does for businesses, what it does for workers, the "
         "payoff, the close. Every feature on its own app screen.")
SECONDS = 30
ASPECTS = ("16:9", "9:16")
PROJECT_TITLE = "Gygler -- outside check"


def _say(*a):
    print(*a, flush=True)


class Run:
    def __init__(self, account_id: int):
        from fastapi.testclient import TestClient

        from app import auth
        from app.main import app
        app.dependency_overrides[auth.current_account_id] = lambda: account_id
        auth.current_user = lambda request: {"id": 0, "email": "outside-check@phantra.ai",
                                             "display_name": "outside check"}
        self.c = TestClient(app)
        self.account_id = account_id
        self.warnings: list[str] = []
        self.spent: list[dict] = []
        self.times: dict[str, float] = {}

    def post(self, path, body=None):
        r = self.c.post(f"/api{path}", json=body or {})
        if r.status_code >= 400:
            raise RuntimeError(f"POST {path} -> {r.status_code}: {r.text[:400]}")
        return r.json()

    def get(self, path):
        r = self.c.get(f"/api{path}")
        if r.status_code >= 400:
            raise RuntimeError(f"GET {path} -> {r.status_code}: {r.text[:400]}")
        return r.json()

    def wait(self, job_id: int, what: str, timeout: float = 900) -> dict:
        deadline, said = time.time() + timeout, ""
        while time.time() < deadline:
            job = self.get(f"/jobs/{job_id}")
            if job.get("detail") and job["detail"] != said:
                said = job["detail"]
                _say(f"   {what}: {said}")
            if job["status"] in ("done", "failed", "cancelled"):
                if job["status"] != "done":
                    raise RuntimeError(f"{what} {job['status']}: {job.get('error') or job.get('detail')}")
                return job
            time.sleep(1.5)
        raise RuntimeError(f"{what} did not finish in {timeout:.0f}s")


def _audio_steps(doc: dict, role: str, handle: str, seconds: float) -> list:
    """lib/cut/voiceover.ts and lib/cut/music.ts, in Python: the same ops in
    the same order (a track when there is none, the take from frame 0, the
    bed's fade, the bed ducked under the voice)."""
    from src.cut import doc as d

    def track(dd, r):
        return next((t for t in dd["tracks"] if t.get("kind") == "audio" and t.get("role") == r), None)

    frames = max(1, d.to_frames(seconds, doc["fps"]))
    if role == "music":
        frames = max(1, min(frames, doc["duration"] or 1))
    steps = []
    if not track(doc, role):
        steps.append(("add_track", lambda dd: {"kind": "audio", "role": role}))
    steps.append(("overwrite", lambda dd: {"track_id": track(dd, role)["id"], "at": 0,
                                           "clip": {"media": handle, "src_in": 0, "src_out": frames}}))
    if role == "music":
        def fade(dd):
            clip = next(c for c in track(dd, "music")["clips"] if c["media"] == handle and c["at"] == 0)
            return {"clip_id": clip["id"], "fade_out": min(dd["fps"], frames // 2)}
        steps.append(("set_fade", fade))
    voice, music = track(doc, "voice"), track(doc, "music")
    if role == "music" and voice and voice.get("clips") and not (music or {}).get("duck_under"):
        steps.append(("duck", lambda dd: {"track_id": track(dd, "music")["id"], "under": "voice"}))
    if role == "voice" and music and music.get("clips") and not music.get("duck_under"):
        steps.append(("duck", lambda dd: {"track_id": music["id"], "under": "voice"}))
    return steps


def _lay(run: Run, cut: str, steps: list) -> dict:
    head = run.get(f"/cut/projects/{cut}")["head"]
    for op, args in steps:
        head = run.post(f"/cut/projects/{cut}/ops",
                        {"base_id": head["id"], "op": op, "args": args(head["doc"])})["head"]
    return head


def _fetch(url: str, to: Path, repo: Path) -> Path:
    if url.startswith("http"):
        with urllib.request.urlopen(url, timeout=120) as r, open(to, "wb") as f:
            shutil.copyfileobj(r, f)
        return to
    local = repo / "data" / url.lstrip("/")
    if not local.exists():
        local = next(repo.glob(f"data/**/{Path(url).name}"))
    shutil.copy(local, to)
    return to


def _frames(video: Path, out: Path, stem: str, every: float = 2.5) -> int:
    out.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vf",
                    f"fps=1/{every},scale=720:-2", str(out / f"{stem}-%02d.jpg")], check=True)
    return len(list(out.glob(f"{stem}-*.jpg")))


def _balance(account_id: int):
    from src import billing
    try:
        return billing.balance(account_id)
    except Exception as e:          # a database without the ledger yet: say so, go on
        return {"unknown": str(e).splitlines()[0]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--account", default="phantra")
    ap.add_argument("--write", action="store_true", help="act (spends credits); without it, report only")
    ap.add_argument("--cap", type=int, default=200, help="stop before spending if the four spends pass this")
    ap.add_argument("--out", default=str(Path.home() / "Downloads" / "phantra-outside-check"))
    ap.add_argument("--reference", default=str(Path.home() / "Downloads" / "IMG_3912.MOV"))
    args = ap.parse_args(argv)

    from src import accounts, brand_import, fal
    account_id = accounts.resolve_account(args.account)
    if account_id is None:
        _say(f"no account '{args.account}' -- export DATABASE_URL first")
        return 2
    out = Path(args.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    repo = Path.cwd()
    bal = _balance(account_id)
    _say(f"account {args.account} (#{account_id}) · balance {bal.get('credits', bal)}")
    _say(f"import available: {brand_import.available()} · fal key: {fal.has_key(account_id)} · "
         f"ffmpeg: {bool(shutil.which('ffmpeg'))}")
    missing = [what for what, ok in (("the site import (Playwright)", brand_import.available()),
                                     ("fal (FAL_KEY)", fal.has_key(account_id)),
                                     ("ffmpeg", bool(shutil.which("ffmpeg")))) if not ok]
    if missing and args.write:
        _say("STOPPED before anything was made: this machine is missing " + ", ".join(missing) + ".")
        return 2
    if not args.write:
        _say("report only: nothing made, nothing spent. Add --write to run it.")
        return 0

    run = Run(account_id)
    report: dict = {"url": URL, "brief": BRIEF, "seconds": SECONDS, "account": args.account,
                    "balance_before": bal, "cuts": {}}
    t0 = time.time()

    # 1. the kit, from the site
    _say("1. importing the site into a new kit…")
    job = run.wait(run.post("/brand-kits/import", {"url": URL})["job_id"], "import", 600)
    kit_id = job["kit_id"]
    report["kit"] = {k: job.get(k) for k in ("kit_id", "kit_name", "products", "references",
                                             "dropped", "blocked", "notes")}
    run.warnings += [f"import: {n}" for n in job.get("notes") or []]
    run.times["import"] = time.time() - t0

    # 2. a project on that kit
    from src import projects
    project = projects.create(PROJECT_TITLE, "", account_id=account_id)
    projects.set_brand_kit(project["id"], kit_id, account_id=account_id)
    report["project_id"] = project["id"]

    # 3-4. per shape: the beats (the card's preview), then built from them
    built = {}
    for aspect in ASPECTS:
        _say(f"2. writing the beats, {aspect}…")
        pre = run.wait(run.post("/cut/motion-ad", {"brief": BRIEF, "seconds": SECONDS,
                                                   "aspect": aspect, "project_id": project["id"],
                                                   "preview": True})["job_id"], "beats", 300)
        run.warnings += [f"{aspect} beats: {w}" for w in pre.get("warnings") or []]
        _say(f"3. building it, {aspect}…")
        job = run.wait(run.post("/cut/motion-ad", {
            "brief": BRIEF, "seconds": SECONDS, "aspect": aspect, "project_id": project["id"],
            "script": {"title": pre["title"], "beats": pre["beats"]},
            "cards": [c["handle"] for c in pre.get("cards") or []],
            "pictures": [p["handle"] for p in pre.get("pictures") or []],
            "kit_pictures": False})["job_id"], "build", 300)
        run.warnings += [f"{aspect} build: {w}" for w in job.get("warnings") or []
                         if f"{aspect} beats: {w}" not in run.warnings]
        built[aspect] = {"cut": job["cut_id"], "script": job.get("script") or "",
                         "title": pre["title"], "beats": pre["beats"],
                         "screens": len(pre.get("cards") or []),
                         "pictures": len(pre.get("pictures") or [])}
        if aspect == ASPECTS[0]:
            run.times["first_build"] = time.time() - t0

    # 5. price all four spends before running any
    quotes = []
    for aspect, b in built.items():
        if b["script"].strip():
            q = run.post(f"/cut/projects/{b['cut']}/voiceover/quote", {"script": b["script"]})
            quotes.append((aspect, "voice", q["credits"], {"script": b["script"], "voice": q["voice"]}))
        else:
            run.warnings.append(f"{aspect}: the beats carry no voiceover lines; no read")
        menu = run.get(f"/cut/projects/{b['cut']}/music")
        q = run.post(f"/cut/projects/{b['cut']}/music/quote", {"model": menu["default_model"]})
        quotes.append((aspect, "music", q["credits"], {"model": menu["default_model"]}))
    total = sum(q[2] for q in quotes)
    report["quotes"] = [{"aspect": a, "what": w, "credits": c} for a, w, c, _ in quotes]
    _say(f"4. the sound costs {total} credits in all: "
         + ", ".join(f"{a} {w} {c}" for a, w, c, _ in quotes))
    if total > args.cap:
        report["stopped"] = f"the sound would cost {total} credits, over the cap of {args.cap}"
        _say(f"STOPPED: {report['stopped']}. Nothing was spent. Re-run with --cap {total} to go on.")
    else:
        for aspect, what, credits, body in quotes:
            cut = built[aspect]["cut"]
            path = "voiceover" if what == "voice" else "music"
            _say(f"5. {what} on the {aspect} cut, {credits} credits…")
            try:
                job = run.wait(run.post(f"/cut/projects/{cut}/{path}/run",
                                        {**body, "expect_credits": credits})["job_id"], what, 600)
            except RuntimeError as e:
                run.warnings.append(f"{aspect} {what}: {e}")
                continue
            run.spent.append({"aspect": aspect, "what": what, "credits": credits})
            head = run.get(f"/cut/projects/{cut}")["head"]
            _lay(run, cut, _audio_steps(head["doc"], "voice" if what == "voice" else "music",
                                        job["audio"], job.get("seconds") or 0))

    # 6. export each
    for aspect, b in built.items():
        _say(f"6. exporting the {aspect} cut…")
        job = run.wait(run.post(f"/cut/projects/{b['cut']}/export", {})["job_id"], "export", 900)
        run.warnings += [f"{aspect} export: {n}" for n in job.get("notes") or []]
        name = f"ours-{aspect.replace(':', 'x')}.mp4"
        video = _fetch(job["mp4_url"], out / name, repo)
        b["file"] = name
        b["seconds"] = job.get("seconds")
        b["frames"] = _frames(video, out / "frames", f"ours-{aspect.replace(':', 'x')}")
        if "first_export" not in run.times:
            run.times["first_export"] = time.time() - t0

    ref = Path(args.reference).expanduser()
    if ref.exists():
        report["reference_frames"] = _frames(ref, out / "frames", "reference", every=4)

    report.update({"cuts": built, "spent": run.spent,
                   "credits_spent": sum(s["credits"] for s in run.spent),
                   "warnings": run.warnings,
                   "seconds": {k: round(v, 1) for k, v in run.times.items()},
                   "balance_after": _balance(account_id),
                   "edits_before_postable": "for the person checking it: count them in the editor"})
    (out / "run.json").write_text(json.dumps(report, indent=2, default=str))
    _say(f"done in {time.time() - t0:.0f}s · {report['credits_spent']} credits · "
         f"{len(run.warnings)} warnings · {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

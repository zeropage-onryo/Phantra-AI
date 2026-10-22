"""
Before/after contact sheet for the free looks (2026-10-22, group 2 of
docs/tasks/task-overnight-2026-10-22.md, checkbox 5).

    venv/bin/python -m ops.looks_contact_sheet [--out docs/qa/looks-contact-sheet.png]
                                               [--clip <file.mp4> ...]

With no `--clip` the fixtures are SYNTHETIC: ffmpeg `testsrc2` patterns made
here into a temporary folder (a moving 16:9 pattern with a tone, a silent
one, a held frame for the crash zoom, and a 1000x600 one). Real phone clips
go in only with `--clip`, and only once Mike has said yes to them (step 10
of the task): nothing here reads the library or the bucket.

Each row is one look: the source frame on the left, the look's frame on the
right, at the same time (0.3s for the crash zoom, where the punch-in lands;
0.03s for the flash, inside the first pop; 0.5s otherwise), and the last row
is the end card. Re-runnable; writes one PNG and nothing else that stays.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from src import free_looks as looks

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "docs" / "qa" / "looks-contact-sheet.png"
TILE_W = 384
LABEL_H = 22
GUTTER = 12
ROWS = (("film_grade", 0.5), ("noir", 0.5), ("flash_2000s", 0.03), ("crash_zoom", 0.3),
        ("vertical_ready", 0.5), ("make_it_pro", 0.5))


def synthetic_fixtures(folder: Path) -> list[Path]:
    """The testsrc2 clips the tests use, made here the same way."""
    def make(name, size="1280x720", seconds=2.0, audio=True, static=False):
        path = folder / name
        if static:
            png = path.with_suffix(".png")
            subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
                            "-i", f"testsrc2=size={size}:rate=30", "-frames:v", "1", str(png)],
                           check=True)
            subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-loop", "1",
                            "-framerate", "30", "-t", str(seconds), "-i", str(png), "-c:v",
                            "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", str(path)],
                           check=True)
            return path
        args = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                f"testsrc2=size={size}:rate=30:duration={seconds}"]
        args += (["-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}", "-c:a", "aac"]
                 if audio else ["-an"])
        args += ["-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", str(path)]
        subprocess.run(args, check=True)
        return path
    return [make("synthetic-moving.mp4"), make("synthetic-static.mp4", static=True),
            make("synthetic-odd.mp4", size="1000x600", seconds=1.5, audio=False)]


def _tile(image, width: int):
    from PIL import Image
    im = image.copy()
    im.thumbnail((width, width))
    canvas = Image.new("RGB", (width, int(width * 9 / 16)), (14, 14, 18))
    canvas.paste(im, ((width - im.width) // 2, (canvas.height - im.height) // 2))
    return canvas


def sheet(clips: list[Path], out: Path, workdir: Path) -> Path:
    from PIL import Image, ImageDraw
    rows = []
    for i, clip in enumerate(clips):
        for look, t in ROWS:
            src = clip
            if look == "crash_zoom" and len(clips) > 1 and "static" in clips[1].name:
                src = clips[1]                     # the held frame shows the zoom
            made = workdir / f"{clip.stem}-{look}.mp4"
            res = looks.apply(look, src, made)
            rows.append((f"{look}  ({src.name}, t={t}s, {res['timing']['per_second']:.2f}s/s)",
                         looks.frame_image(src, t), looks.frame_image(made, t)))
        carded = workdir / f"{clip.stem}-endcard.mp4"
        looks.append_end_card(clip, carded)
        end = float(looks.probe(clip)["seconds"])           # the card starts where the clip ends
        rows.append((f"end card  ({clip.name}, last frame -> t={end + 0.5:.1f}s, 0.5s into the card)",
                     looks.frame_image(clip, max(0.0, end - 0.05)),
                     looks.frame_image(carded, end + 0.5)))
        if i == 0:
            break                                  # one clip's rows is the sheet; others on request
    tile_h = int(TILE_W * 9 / 16)
    width = GUTTER * 3 + TILE_W * 2
    height = GUTTER + len(rows) * (LABEL_H + tile_h + GUTTER) + 30
    im = Image.new("RGB", (width, height), (20, 20, 24))
    d = ImageDraw.Draw(im)
    d.text((GUTTER, 6), "Phantra free looks -- before (left) / after (right), synthetic testsrc2 "
                        "fixtures, 2026-10-22", fill=(200, 200, 205))
    y = 30
    for label, before, after in rows:
        d.text((GUTTER, y), label, fill=(235, 235, 240))
        y += LABEL_H
        im.paste(_tile(before, TILE_W), (GUTTER, y))
        im.paste(_tile(after, TILE_W), (GUTTER * 2 + TILE_W, y))
        y += tile_h + GUTTER
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out, optimize=True)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--clip", type=Path, action="append", default=[],
                    help="a real clip (only with Mike's yes); default: synthetic fixtures")
    args = ap.parse_args(argv)
    if not looks.ffmpeg_bin():
        print("ffmpeg is not installed", file=sys.stderr)
        return 1
    with tempfile.TemporaryDirectory(prefix="phantra-looks-sheet-") as tmp:
        work = Path(tmp)
        clips = [p.resolve() for p in args.clip] or synthetic_fixtures(work)
        out = sheet(clips, args.out, work)
    print(f"wrote {out} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

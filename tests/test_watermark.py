"""
The free tier's watermark (2026-10-11, src/watermark.py).

Guards:
- WHO: only an owned, non-exempt account with no plan is marked; the
  switch, an unowned call and a failed read all mean "not marked" (it fails
  OPEN -- a paying customer's render must never be branded by a flaky read).
- THE MARK: a still and a clip come back the same size and kind, changed
  only in the bottom-right corner; a clip keeps its sound.
- PUBLISHING: the marked copy goes up at the render's own key, the clean
  original under an unguessable `clean/` key, and the pair is recorded; no
  bucket, a paid account, an unmarkable type or a failed burn publish
  exactly as before.
- A MODEL NEVER SEES IT: clean_url swaps a marked URL for its original, and
  the three doors that hand a render to a model (fal.as_image_url,
  effects.fetchable_video, imagery.fetch_image_bytes) ask it.
- UPGRADING: unlock copies every original over its marked key, once, and
  the paid-invoice webhook calls it.
"""
import shutil
import subprocess
from pathlib import Path

import pytest

from src import accounts, billing, db, effects, fal, imagery, ledger, media, storage, watermark

BASE = "https://pub.example.r2.dev"
HAS_FFMPEG = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


# --- fixtures ----------------------------------------------------------------

@pytest.fixture
def acct(pg, monkeypatch):
    """One seeded account on a fresh schema, with the watermark table."""
    accounts.init(pg)
    seeded = accounts.seed("mike@example.com", dsn=pg)
    watermark.init(pg)
    return {"dsn": pg, "id": int(seeded["accounts"][0])}


@pytest.fixture
def bucket(monkeypatch):
    """A fake R2: configured, every upload recorded, every copy recorded."""
    uploads, copies = [], []
    monkeypatch.setattr(storage, "configured", lambda: True)
    monkeypatch.setattr(storage, "public_base_url", lambda: BASE)
    monkeypatch.setattr(storage, "bucket", lambda: "zpf")

    def upload_file(path, key=None, content_type=None):
        uploads.append({"key": key, "bytes": Path(path).read_bytes(), "type": content_type})
        return f"{BASE}/{key}"

    monkeypatch.setattr(storage, "upload_file", upload_file)
    monkeypatch.setattr(storage, "copy_key", lambda src, dst: copies.append((src, dst)))
    monkeypatch.setattr(media, "mirror_poster", lambda *a, **k: None)
    return {"uploads": uploads, "copies": copies}


def still(path: Path, size=(640, 1136), color=(30, 60, 120)) -> Path:
    from PIL import Image
    Image.new("RGB", size, color).save(path, "PNG")
    return path


def clip(path: Path) -> Path:
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=navy:s=360x640:r=24:d=1",
         "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(path)],
        check=True, capture_output=True)
    return path


# --- who ---------------------------------------------------------------------

def test_only_a_free_account_is_marked(acct):
    dsn, a = acct["dsn"], acct["id"]
    assert watermark.applies(a, dsn=dsn) is True                     # the trial
    assert watermark.applies(None, dsn=dsn) is False                 # unowned work
    accounts.set_plan(a, "starter", dsn=dsn)
    assert watermark.applies(a, dsn=dsn) is False                    # paying
    accounts.set_plan(a, None, dsn=dsn)
    accounts.set_credit_exempt("zeropage", True, dsn=dsn)
    assert watermark.applies(a, dsn=dsn) is False                    # the operator


def test_the_switch_turns_it_off(acct, monkeypatch):
    monkeypatch.setenv(watermark.ENV, "0")
    assert watermark.applies(acct["id"], dsn=acct["dsn"]) is False


def test_a_failed_read_means_unmarked_never_branded(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("database down")
    monkeypatch.setattr(db, "connect", boom)
    assert watermark.applies(7) is False


def test_an_account_that_does_not_exist_is_not_marked(acct):
    assert watermark.applies(999, dsn=acct["dsn"]) is False


# --- the mark ----------------------------------------------------------------

def test_a_still_is_marked_only_in_its_corner(tmp_path):
    from PIL import Image, ImageChops
    src = still(tmp_path / "a.png")
    out = tmp_path / "a_marked.png"
    watermark.burn_image(src, out)
    a, b = Image.open(src).convert("RGB"), Image.open(out).convert("RGB")
    assert b.size == a.size and Image.open(out).format == "PNG"
    box = ImageChops.difference(a, b).getbbox()
    assert box is not None, "nothing was drawn"
    left, top, right, bottom = box
    assert left > a.width * 0.5 and top > a.height * 0.85, box     # bottom-right only


def test_a_jpeg_stays_a_jpeg(tmp_path):
    from PIL import Image
    src = tmp_path / "a.jpg"
    Image.new("RGB", (800, 600), (200, 200, 200)).save(src, "JPEG")
    out = tmp_path / "b.jpg"
    watermark.burn_image(src, out)
    assert Image.open(out).format == "JPEG" and Image.open(out).size == (800, 600)


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not installed")
def test_a_clip_is_marked_and_keeps_its_sound(tmp_path):
    src = clip(tmp_path / "c.mp4")
    out = tmp_path / "c_marked.mp4"
    watermark.burn_video(src, out)
    streams = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height",
         "-of", "csv=p=0", str(out)], capture_output=True, text=True, check=True).stdout
    assert "video,360,640" in streams.replace("video,360,640,", "video,360,640")
    assert "audio" in streams
    frames = []
    for f in (src, out):
        png = tmp_path / f"{f.stem}.png"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(f), "-frames:v", "1", str(png)],
                       check=True)
        frames.append(png)
    from PIL import Image, ImageChops
    # a re-encode moves every pixel a little; the mark moves them a lot
    diff = ImageChops.difference(Image.open(frames[0]).convert("RGB"),
                                 Image.open(frames[1]).convert("RGB")).convert("L")
    box = diff.point(lambda v: 255 if v > 48 else 0).getbbox()
    assert box is not None and box[0] > 180 and box[1] > 520, box


def test_only_stills_and_mp4s_are_markable():
    assert watermark.markable(Path("a.png")) == "image"
    assert watermark.markable(Path("a.JPG")) == "image"
    assert watermark.markable(Path("a.mp4")) == "video"
    assert watermark.markable(Path("a.webm")) is None          # a transparent cutout
    assert watermark.markable(Path("a.mov")) is None
    assert watermark.markable(Path("a.m4a")) is None


# --- publishing --------------------------------------------------------------

def test_a_free_render_goes_up_marked_with_its_original_kept(acct, bucket, tmp_path):
    src = still(tmp_path / "r.png")
    out = watermark.publish(src, "renders/fal/r.png", acct["id"], "image/png", dsn=acct["dsn"])
    assert out is not None
    try:
        public_key = media.object_key("renders/fal/r.png", acct["id"])
        assert out["url"] == f"{BASE}/{public_key}"
        by_key = {u["key"]: u for u in bucket["uploads"]}
        assert public_key in by_key
        clean_key = next(k for k in by_key if "/clean/" in f"/{k}")
        assert by_key[clean_key]["bytes"] == src.read_bytes()            # untouched
        assert by_key[public_key]["bytes"] != src.read_bytes()           # marked
        assert len(clean_key.split("clean/")[1].split("/")[0]) == 32     # unguessable
        assert src.read_bytes() == still(tmp_path / "again.png").read_bytes()  # the local file is clean
        assert watermark.is_marked(out["url"], dsn=acct["dsn"]) is True
    finally:
        watermark.discard(out["marked_path"])
    assert not Path(out["marked_path"]).exists()


def test_a_paid_render_publishes_as_before(acct, bucket, tmp_path):
    accounts.set_plan(acct["id"], "creator", dsn=acct["dsn"])
    src = still(tmp_path / "r.png")
    assert watermark.publish(src, "renders/fal/r.png", acct["id"], "image/png",
                             dsn=acct["dsn"]) is None
    assert bucket["uploads"] == []


def test_no_bucket_means_no_mark(acct, tmp_path):
    src = still(tmp_path / "r.png")
    assert watermark.publish(src, "renders/fal/r.png", acct["id"], "image/png",
                             dsn=acct["dsn"]) is None


def test_a_failed_burn_publishes_clean_rather_than_losing_the_render(acct, bucket, tmp_path,
                                                                       monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("no fonts")
    monkeypatch.setattr(watermark, "burn_image", boom)
    src = still(tmp_path / "r.png")
    assert watermark.publish(src, "renders/fal/r.png", acct["id"], "image/png",
                             dsn=acct["dsn"]) is None
    with db.connect(acct["dsn"]) as conn:
        assert conn.execute("SELECT count(*) AS n FROM watermarked_media").fetchone()["n"] == 0


def test_fal_publish_marks_a_free_render_and_not_a_paid_one(acct, bucket, tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", acct["dsn"])          # fal._publish passes no dsn
    src = still(tmp_path / "f.png")
    url = fal._publish(src, "image/png", acct["id"])
    assert watermark.is_marked(url, dsn=acct["dsn"])
    assert sum(1 for u in bucket["uploads"] if "clean/" in u["key"]) == 1

    accounts.set_plan(acct["id"], "studio", dsn=acct["dsn"])
    bucket["uploads"].clear()
    other = still(tmp_path / "g.png")
    url = fal._publish(other, "image/png", acct["id"])
    assert not watermark.is_marked(url, dsn=acct["dsn"])
    assert [u["key"] for u in bucket["uploads"]] == [media.object_key("renders/fal/g.png", acct["id"])]


# --- a model never sees it ---------------------------------------------------

def _marked_url(acct, bucket, tmp_path, name="m.png"):
    out = watermark.publish(still(tmp_path / name), f"renders/fal/{name}", acct["id"],
                            "image/png", dsn=acct["dsn"])
    watermark.discard(out["marked_path"])
    clean_key = next(u["key"] for u in bucket["uploads"]
                     if "clean/" in u["key"] and u["key"].endswith(name))
    return out["url"], f"{BASE}/{clean_key}"


def test_clean_url_swaps_a_marked_render_for_its_original(acct, bucket, tmp_path):
    marked, clean = _marked_url(acct, bucket, tmp_path)
    assert watermark.clean_url(marked, dsn=acct["dsn"]) == clean
    assert watermark.clean_url(marked + "?v=1", dsn=acct["dsn"]) == clean
    other = f"{BASE}/m/1/renders/fal/someone-else.png"
    assert watermark.clean_url(other, dsn=acct["dsn"]) == other
    assert watermark.clean_url("https://elsewhere.com/a.png", dsn=acct["dsn"]) == \
        "https://elsewhere.com/a.png"
    assert watermark.clean_url("/renders/fal/a.png", dsn=acct["dsn"]) == "/renders/fal/a.png"


def test_the_model_doors_ask_for_the_clean_original(monkeypatch):
    asked = []
    monkeypatch.setattr(watermark, "clean_url",
                        lambda url, dsn=None: asked.append(url) or url.replace("marked", "clean"))
    assert fal.as_image_url("https://x.r2.dev/marked.png") == "https://x.r2.dev/clean.png"
    assert effects.fetchable_video("https://x.r2.dev/marked.mp4") == "https://x.r2.dev/clean.mp4"
    monkeypatch.setattr(imagery, "_public_host", lambda host: False)   # stop before any fetch
    imagery.fetch_image_bytes("https://x.r2.dev/marked.jpg")
    assert asked == ["https://x.r2.dev/marked.png", "https://x.r2.dev/marked.mp4",
                     "https://x.r2.dev/marked.jpg"]


# --- upgrading ---------------------------------------------------------------

def test_unlock_puts_every_original_back_once(acct, bucket, tmp_path):
    first, _ = _marked_url(acct, bucket, tmp_path, "one.png")
    second, _ = _marked_url(acct, bucket, tmp_path, "two.png")
    done = watermark.unlock(acct["id"], dsn=acct["dsn"])
    assert done == {"unlocked": 2, "failed": 0}
    assert [dst for _, dst in bucket["copies"]] == [
        media.object_key("renders/fal/one.png", acct["id"]),
        media.object_key("renders/fal/two.png", acct["id"])]
    assert all("clean/" in src for src, _ in bucket["copies"])
    assert not watermark.is_marked(first, dsn=acct["dsn"])
    assert watermark.clean_url(second, dsn=acct["dsn"]) == second       # nothing left to swap
    assert watermark.unlock(acct["id"], dsn=acct["dsn"]) == {"unlocked": 0, "failed": 0}


def test_a_failed_copy_stays_marked_for_next_time(acct, bucket, tmp_path, monkeypatch):
    url, _ = _marked_url(acct, bucket, tmp_path)

    def boom(src, dst):
        raise RuntimeError("R2 down")
    monkeypatch.setattr(storage, "copy_key", boom)
    assert watermark.unlock(acct["id"], dsn=acct["dsn"]) == {"unlocked": 0, "failed": 1}
    assert watermark.is_marked(url, dsn=acct["dsn"])


def test_a_paid_invoice_unlocks_the_accounts_renders(acct, monkeypatch):
    dsn, a = acct["dsn"], acct["id"]
    ledger.init(dsn)
    accounts.set_stripe_customer(a, "cus_1", dsn=dsn)
    monkeypatch.setenv("STRIPE_PRICE_CREATOR", "price_creator")
    called = []
    monkeypatch.setattr(watermark, "unlock",
                        lambda account_id, dsn=None: called.append(account_id)
                        or {"unlocked": 3, "failed": 0})
    out = billing.handle_event(
        {"id": "evt_1", "type": "invoice.paid",
         "data": {"object": {"id": "in_1", "object": "invoice", "customer": "cus_1",
                             "lines": {"data": [{"price": {"id": "price_creator"}}]}}}},
        dsn=dsn)
    assert out["action"] == "granted" and called == [a]

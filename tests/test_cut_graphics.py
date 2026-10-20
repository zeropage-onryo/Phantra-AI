"""The editor's graphics track (src/cut/graphics.py; BACKLOG #28): items
validated like cues, edited by ops, drawn once with Pillow and laid over the
picture by ffmpeg with eased motion and alpha fades. Nothing here spends;
the real renders use ffmpeg's own test sources. A cut with no graphics track
is pinned unchanged by tests/test_brand_kit_no_kit.py.
"""
import io
import shutil
import subprocess

import pytest
from PIL import Image

from src.cut import doc as d
from src.cut import graphics as g
from src.cut import ops, render
from src.cut import validate as v

HAS_FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))
KIT = {"id": 1, "account_id": 1, "name": "Gygler", "assets": [],
       "spec": {"palette": [{"hex": "#F7931E", "role": "primary"},
                            {"hex": "#FFF4E6", "role": "background"},
                            {"hex": "#8A4B08", "role": "text"}], "safe_zone": 0.06}}


def cut(frames=90):
    doc = d.new_doc()
    doc["size"] = [1280, 720]
    doc["tracks"] = [{"id": "V1", "kind": "video", "clips": [
        {"id": "c1", "media": "gen:1", "src_in": 0, "src_out": frames, "at": 0, "speed": 1}]}]
    doc["duration"] = frames
    return doc


MEDIA = {"gen:1": {"frames": 90, "video": True, "audio": False, "width": 1280, "height": 720},
         "asset:7": {"frames": 18000, "video": True, "audio": False, "still": True,
                     "width": 400, "height": 300},
         "gen:9": {"frames": 90, "video": True, "audio": False}}


def with_graphics(*items_per_track):
    doc = cut()
    for n, items in enumerate(items_per_track, start=1):
        doc = ops.apply(doc, "add_track", {"kind": "graphic"})
        for it in items:
            doc = ops.apply(doc, "set_graphic", {"track_id": f"G{n}", **it}, media=MEDIA)
    return doc


# --------------------------------------------------------------------------
# the doc: ops and the validator
# --------------------------------------------------------------------------

def test_a_graphics_track_is_added_and_items_take_their_types_defaults():
    doc = with_graphics([{"start": 0, "end": 60, "type": "headline", "text": " Find talent. "}])
    t = d.track(doc, "G1")
    assert t["kind"] == "graphic"
    item = t["items"][0]
    assert item["id"] == "g1" and item["text"] == "Find talent."
    assert item["anim_in"] == "rise" and item["position"] == "center"
    # an edit keeps the id and what it did not name
    doc = ops.apply(doc, "set_graphic", {"track_id": "G1", "graphic_id": "g1", "start": 0,
                                         "end": 45, "type": "headline", "position": "left"})
    item = d.track(doc, "G1")["items"][0]
    assert (item["end"], item["position"], item["text"]) == (45, "left", "Find talent.")
    assert ops.describe("set_graphic", {"track_id": "G1", "type": "headline",
                                        "text": "Find talent."}) == 'add headline "Find talent." on G1'
    doc = ops.apply(doc, "delete_graphic", {"track_id": "G1", "graphic_id": "g1"})
    assert d.track(doc, "G1")["items"] == []


def test_a_graphic_past_the_picture_lengthens_the_cut():
    doc = with_graphics([{"start": 60, "end": 150, "type": "label", "text": "$24 / hr"}])
    assert doc["duration"] == 150


@pytest.mark.parametrize("item,said", [
    ({"start": 0, "end": 30, "type": "sticker", "text": "x"}, "type must be one of"),
    ({"start": 0, "end": 30, "type": "headline", "text": "  "}, "text is empty"),
    ({"start": 30, "end": 30, "type": "headline", "text": "x"}, "end must be after start"),
    ({"start": 0, "end": 30, "type": "card"}, "a card needs a picture"),
    ({"start": 0, "end": 30, "type": "card", "media": "gen:9"}, "is a clip"),
    ({"start": 0, "end": 30, "type": "headline", "text": "x", "media": "asset:7"},
     "only a card takes a picture"),
    ({"start": 0, "end": 30, "type": "headline", "text": "x", "anim_in": "spin"},
     "anim_in must be one of"),
    ({"start": 0, "end": 30, "type": "headline", "text": "x", "color": "orange"},
     "color must be a palette role"),
    ({"start": 0, "end": 30, "type": "background_word", "text": "x" * 30}, "at most 24"),
])
def test_a_bad_item_is_refused_with_a_reason(item, said):
    doc = with_graphics([])
    with pytest.raises(ops.OpError) as e:
        ops.apply(doc, "set_graphic", {"track_id": "G1", **item}, media=MEDIA)
    assert any(said in p for p in (e.value.problems or [str(e.value)])), e.value.problems


def test_two_items_may_not_overlap_on_one_track_but_may_stack_on_two():
    doc = with_graphics([{"start": 0, "end": 60, "type": "headline", "text": "a"}])
    with pytest.raises(ops.OpError) as e:
        ops.apply(doc, "set_graphic", {"track_id": "G1", "start": 30, "end": 90,
                                       "type": "label", "text": "b"}, media=MEDIA)
    assert any("overlap on G1" in p for p in e.value.problems)
    doc = ops.apply(doc, "add_track", {"kind": "graphic"})
    doc = ops.apply(doc, "set_graphic", {"track_id": "G2", "start": 30, "end": 90,
                                         "type": "label", "text": "b"}, media=MEDIA)
    assert [i["id"] for i in g.items_in_order(doc)] == ["g1", "g2"]
    v.validate(doc, MEDIA)


def test_a_cards_picture_is_one_of_the_docs_handles():
    doc = with_graphics([{"start": 0, "end": 60, "type": "card", "media": "asset:7"}])
    assert d.handles(doc) == ["gen:1", "asset:7"]
    assert g.handles(doc) == ["asset:7"]


# --------------------------------------------------------------------------
# drawing
# --------------------------------------------------------------------------

def opaque_colours(im):
    """Every fully opaque pixel's RGB, read from the raw bytes."""
    raw = im.convert("RGBA").tobytes()
    return {tuple(raw[i:i + 3]) for i in range(0, len(raw), 4) if raw[i + 3] == 255}


def _png(item, style, size=(1280, 720), picture=None):
    return Image.open(io.BytesIO(g.draw(item, size, style, picture)))


def test_each_type_draws_a_canvas_sized_transparent_layer():
    pic = io.BytesIO()
    Image.new("RGB", (400, 300), (20, 120, 200)).save(pic, "PNG")
    for item in ({"type": "headline", "text": "Find the right talent."},
                 {"type": "background_word", "text": "find"},
                 {"type": "label", "text": "$24 / hr"},
                 {"type": "card", "media": "asset:7"}):
        im = _png({"start": 0, "end": 30, **item}, g.Style(), picture=pic.getvalue())
        assert im.size == (1280, 720) and im.mode == "RGBA"
        alphas = im.getchannel("A").getextrema()
        assert alphas[0] == 0 and alphas[1] > 0, item["type"]       # mostly clear, something drawn


def test_the_background_word_is_faint_and_a_kit_colours_the_text():
    word = _png({"type": "background_word", "text": "book", "start": 0, "end": 30}, g.Style())
    assert word.getchannel("A").getextrema()[1] <= round(255 * g.WORD_ALPHA) + 1
    kitted = g.Style.from_kit(KIT)
    head = _png({"type": "headline", "text": "BOOK", "start": 0, "end": 30, "size": "l"}, kitted)
    assert (0xF7, 0x93, 0x1E) in opaque_colours(head)          # the kit's primary
    plain = _png({"type": "headline", "text": "BOOK", "start": 0, "end": 30, "size": "l"}, g.Style())
    assert (255, 255, 255) in opaque_colours(plain)


def test_a_card_whose_picture_cannot_be_read_draws_nothing():
    im = _png({"type": "card", "media": "asset:7", "start": 0, "end": 30}, g.Style(),
              picture=b"not a picture")
    assert im.getchannel("A").getextrema() == (0, 0)


# --------------------------------------------------------------------------
# motion and the graph
# --------------------------------------------------------------------------

def test_motion_is_still_at_rest_and_moves_only_for_its_animations():
    item = {"type": "headline", "text": "x", "start": 30, "end": 90, "anim_in": "rise",
            "anim_out": "fade"}
    x, y = g.motion(item, (1280, 720), 30)
    assert x == "0" and "pow(1-min(1,max(0,(t-1)/0.5)),3)" in y
    still = {**item, "anim_in": "none", "anim_out": "none"}
    assert g.motion(still, (1280, 720), 30) == ("0", "0")
    assert g.timing(still, 30)["in"] == 0
    word = {"type": "background_word", "text": "x", "start": 0, "end": 60}
    assert "-51.2*" in g.motion(word, (1280, 720), 30)[0]     # 4% of the width, over its life
    short = {**item, "start": 0, "end": 9}                    # 0.3s: a third each way
    assert g.timing(short, 30)["in"] == pytest.approx(0.1)


def test_the_graph_lays_graphics_over_the_picture_before_the_captions(tmp_path):
    doc = with_graphics([{"start": 0, "end": 90, "type": "background_word", "text": "find"}],
                        [{"start": 15, "end": 75, "type": "headline", "text": "Find talent."}])
    doc = ops.apply(doc, "add_caption_track", {"cues": [{"start": 0, "end": 30, "text": "hi"}]})
    drawn = g.prepare(doc, tmp_path, {}, g.Style())
    assert [p["item"]["id"] for p in drawn] == ["g1", "g2"]
    argv = render.compile_args(doc, {"gen:1": "/x/a.mp4"}, "/x/o.mp4", burn="c.ass",
                               graphics=drawn)
    graph = argv[argv.index("-filter_complex") + 1]
    assert argv.count("-loop") == 2 and drawn[1]["path"] in argv
    assert "[1:v]format=rgba,fade=t=in:st=0:d=0.5:alpha=1" in graph
    assert graph.index("[go0][gl1]overlay") < graph.index("ass=c.ass")
    assert "enable='between(t,0.5,2.5)'" in graph
    # the sound-only export opens no graphic at all
    audio = render.compile_args(doc, {"gen:1": "/x/a.mp4"}, "/x/o.m4a", fmt="audio",
                                graphics=drawn)
    assert "-loop" not in audio


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg/ffprobe not installed")
def test_a_real_export_draws_the_graphics_and_keeps_the_length(tmp_path):
    clip, pic = tmp_path / "a.mp4", tmp_path / "ui.png"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    "color=c=black:s=1280x720:r=30:d=3", "-c:v", "libx264", "-pix_fmt",
                    "yuv420p", "-preset", "ultrafast", str(clip)], check=True)
    Image.new("RGB", (400, 300), (240, 240, 240)).save(pic)
    doc = with_graphics([{"start": 0, "end": 90, "type": "card", "media": "asset:7",
                          "position": "right", "anim_in": "none", "anim_out": "none"}],
                        [{"start": 30, "end": 90, "type": "label", "text": "$24 / hr"}])
    media = {**MEDIA, "gen:1": {**MEDIA["gen:1"]}}
    got = render.render(doc, account_id=None, name="gfx", paths={"gen:1": clip, "asset:7": pic},
                        media=media, out_dir=tmp_path, kit=None)
    assert abs(got["seconds"] - 3.0) < 0.1
    frame = tmp_path / "f.png"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "2", "-i", got["path"], "-frames:v",
                    "1", str(frame)], check=True)
    im = Image.open(frame).convert("RGB")
    # the card sits on the right over the black picture, the left stays black
    assert sum(im.getpixel((1000, 360))) > 600 and sum(im.getpixel((200, 200))) < 30

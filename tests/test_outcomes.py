"""Outcome events (src/outcomes.py; step 4 of docs/tasks/task-higgsfield-shape.md).

What a person does with an output is the eval signal. These hold the
rules that make the signal honest: the writer never raises and never
writes about somebody else's output, `kept` is derived, a regen is only
called one when nothing was kept, and an edited prompt is taught by a kept
output and withdrawn only when every output made from it is gone. Each
test names the line it guards. Nothing here calls a model.
"""
import json
from datetime import datetime, timedelta, timezone

import pytest

from src import accounts, db, generative, ledger, outcomes, preprod, render_assets, winners
from src.shot import Shot

WHO = {}


@pytest.fixture
def store(pg, monkeypatch):
    accounts.init(pg)
    preprod.init(pg)
    generative.init(pg)
    render_assets.init(pg)
    winners.init(pg)
    outcomes.init(pg)
    WHO["mine"] = accounts.upsert_account("o-mine", "Mine", "#fff", dsn=pg)
    WHO["theirs"] = accounts.upsert_account("o-theirs", "Theirs", "#fff", dsn=pg)
    # the assets shelf is the RAG store: not this file's subject
    monkeypatch.setattr(render_assets, "_ingest",
                        lambda *a, **k: {"ok": False, "chunks": 0, "error": "stubbed"})
    return pg


def made(dsn, prompt="a can on a counter", *, model="wan3", kind="video", who="mine",
         concept_id=None, shot_n=None, part=None, sources=None, cost=0.5, minutes_ago=0):
    """One output with its attempt row, as an adapter leaves them."""
    account = WHO[who]
    shot = generative.add_shot(Shot(subject=prompt[:60], action="as prompted"),
                               dsn=dsn, account_id=account)
    gen = generative.record_generation(shot, "wan", prompt, {"model": model}, None, cost,
                                       dsn=dsn, account_id=account)
    meta = {"model": model}
    if part is not None:
        meta["part"] = part
    if sources is not None:
        meta["sources"] = sources
    asset = render_assets.record(
        generation_id=gen, tool="wan", model=model, media_kind=kind, prompt=prompt,
        media_url=f"/renders/fal/clip-{gen}.mp4", concept_id=concept_id, shot_n=shot_n,
        metadata=meta, dsn=dsn, account_id=account)["id"]
    if minutes_ago:
        then = (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
                ).isoformat(timespec="seconds")
        with db.connect(dsn) as conn:
            conn.execute("UPDATE generated_assets SET created_at = %s WHERE id = %s "
                         "AND account_id IS NOT DISTINCT FROM %s", (then, asset, account))
    return asset, gen


def kept_flag(dsn, gen, who="mine"):
    with db.connect(dsn) as conn:
        return conn.execute("SELECT kept FROM generations WHERE id = %s "
                            "AND account_id IS NOT DISTINCT FROM %s",
                            (gen, WHO[who])).fetchone()["kept"]


def events(dsn, asset, who="mine"):
    return [e["event"] for e in outcomes.events_for([asset], account_id=WHO[who], dsn=dsn)[asset]]


# guards: record -- one row, the closed vocabulary, kept derived from a kept event only
def test_a_kept_event_is_recorded_and_sets_kept(store):
    asset, gen = made(store)
    assert kept_flag(store, gen) == 0
    assert outcomes.record("download", asset_id=asset, account_id=WHO["mine"],
                           source="library", meta={"n": 1}, dsn=store)
    assert events(store, asset) == ["download"]
    assert kept_flag(store, gen) == 1
    row = outcomes.events_for([asset], account_id=WHO["mine"], dsn=store)[asset][0]
    assert row["generation_id"] == gen and row["source"] == "library"
    assert json.loads(row["meta"]) == {"n": 1}

    other, other_gen = made(store, "another prompt")
    assert outcomes.record("delete", asset_id=other, account_id=WHO["mine"], dsn=store)
    assert kept_flag(store, other_gen) == 0          # a discard keeps nothing
    assert outcomes.record("liked", asset_id=other, account_id=WHO["mine"], dsn=store) is None
    assert events(store, other) == ["delete"]


# guards: record / _asset -- nothing is written about an output the caller does not own
def test_another_accounts_output_records_nothing(store):
    asset, gen = made(store, who="theirs")
    assert outcomes.record("star", asset_id=asset, account_id=WHO["mine"], dsn=store) is None
    assert outcomes.record("star", generation_id=gen, account_id=WHO["mine"], dsn=store) is None
    assert events(store, asset, who="theirs") == [] and kept_flag(store, gen, "theirs") == 0
    assert outcomes.record("star", asset_id=99999, account_id=WHO["mine"], dsn=store) is None
    # by its attempt id, for its owner, it lands on the same output
    assert outcomes.record("star", generation_id=gen, account_id=WHO["theirs"], dsn=store)
    assert events(store, asset, who="theirs") == ["star"]


# guards: record's except -- the bookkeeping never costs the click
def test_the_writer_never_raises(store, pg_factory, monkeypatch):
    empty = pg_factory()                              # no tables at all
    assert outcomes.record("star", asset_id=1, account_id=1, dsn=empty) is None
    assert outcomes.note_new(1, account_id=1, dsn=empty) == {"regen": [], "prompt_edit": None}
    assert outcomes.withdraw("delete", asset_id=1, account_id=1, dsn=empty) is False
    assert outcomes.summary(account_id=1, dsn=empty)["made"] == 0

    asset, _ = made(store)

    def boom(*a, **k):
        raise RuntimeError("database is on fire")
    monkeypatch.setattr(outcomes.db, "connect", boom)
    assert outcomes.record("star", asset_id=asset, account_id=WHO["mine"], dsn=store) is None
    assert outcomes.asset_for_url("/renders/fal/x.mp4", account_id=WHO["mine"], dsn=store) is None


# guards: asset_of / asset_for_url / record_ref -- a gen: id or a minted URL names the output
def test_an_output_is_named_by_its_id_or_by_its_url(store):
    asset, _ = made(store)
    with db.connect(store) as conn:
        url = conn.execute("SELECT media_url FROM generated_assets WHERE id = %s "
                           "AND account_id IS NOT DISTINCT FROM %s",
                           (asset, WHO["mine"])).fetchone()["media_url"]
    assert outcomes.asset_of(f"gen:{asset}") == asset
    assert outcomes.asset_of("asset:3") is None and outcomes.asset_of(url) is None
    assert outcomes.asset_for_url(url + "?X-Amz-Signature=abc", account_id=WHO["mine"],
                                  dsn=store) == asset
    assert outcomes.asset_for_url("https://cdn.example/m/1" + url, account_id=WHO["mine"],
                                  dsn=store) == asset
    # somebody else's account, an upload, a stranger's frame: not an output of theirs
    assert outcomes.asset_for_url(url, account_id=WHO["theirs"], dsn=store) is None
    assert outcomes.record_ref("ref_reuse", "/refs/abc123.jpg", account_id=WHO["mine"],
                               dsn=store) is None
    assert outcomes.record_ref("ref_reuse", "https://example.com/a.jpg",
                               account_id=WHO["mine"], dsn=store) is None
    assert outcomes.record_refs("ref_reuse", [f"gen:{asset}", f"gen:{asset}", url, "/refs/x.jpg"],
                                account_id=WHO["mine"], source="composer", dsn=store) == 2
    assert events(store, asset) == ["ref_reuse", "ref_reuse"]


# guards: withdraw -- an undone delete was a slip, not a verdict
def test_undo_takes_the_delete_back(store):
    asset, _ = made(store)
    outcomes.record("delete", asset_id=asset, account_id=WHO["mine"], dsn=store)
    assert outcomes.withdraw("delete", asset_id=asset, account_id=WHO["theirs"], dsn=store) is False
    assert outcomes.withdraw("delete", asset_id=asset, account_id=WHO["mine"], dsn=store) is True
    assert events(store, asset) == []
    assert outcomes.withdraw("delete", asset_id=asset, account_id=WHO["mine"], dsn=store) is False


# guards: note_new -- the same scene part made again, with the first never kept
def test_the_same_part_made_again_is_a_regen_of_the_first(store):
    first, _ = made(store, "take one", concept_id=7, shot_n=1, part=2)
    other_part, _ = made(store, "take one", concept_id=7, shot_n=1, part=3)
    assert events(store, first) == []                # a different part is a different thing
    second, _ = made(store, "take two, reworded", concept_id=7, shot_n=1, part=2)
    assert events(store, first) == ["regen"]
    assert events(store, other_part) == [] and events(store, second) == []
    meta = json.loads(outcomes.events_for([first], account_id=WHO["mine"],
                                          dsn=store)[first][0]["meta"])
    assert meta == {"by": second, "match": "part"}
    # a third try discards the second, and the first is not counted twice
    third, _ = made(store, "take three", concept_id=7, shot_n=1, part=2)
    assert events(store, first) == ["regen"] and events(store, second) == ["regen"]
    assert events(store, third) == []


# guards: note_new's `settled` -- a kept output is never called a regen
def test_nothing_kept_is_ever_a_regen(store):
    first, _ = made(store, "the keeper", concept_id=8, shot_n=1)
    outcomes.record("star", asset_id=first, account_id=WHO["mine"], dsn=store)
    made(store, "another go", concept_id=8, shot_n=1)
    assert events(store, first) == ["star"]


# guards: note_new's window, kind and owner
def test_a_regen_needs_the_same_kind_owner_and_ten_minutes(store):
    old, _ = made(store, "long ago", concept_id=9, shot_n=1, minutes_ago=11)
    still, _ = made(store, "its keyframe", concept_id=9, shot_n=1, kind="image")
    theirs, _ = made(store, "long ago", who="theirs", concept_id=9, shot_n=1)
    made(store, "now", concept_id=9, shot_n=1)
    assert events(store, old) == [] and events(store, still) == []
    assert events(store, theirs, who="theirs") == []


# guards: note_new's prompt rule -- no scene: the same prompt on the same model, same sources
def test_the_same_prompt_drawn_again_is_a_regen(store):
    first, _ = made(store, "A red   can, hard sun", kind="image", model="flux")
    other_model, _ = made(store, "a red can, hard sun", kind="image", model="seedream")
    assert events(store, first) == []
    made(store, "a red can, HARD sun", kind="image", model="flux")
    assert events(store, first) == ["regen"] and events(store, other_model) == []
    # two effects with the same words on DIFFERENT sources are two different things
    up_a, _ = made(store, "Upscale", model="upscale", sources=["gen:1"])
    made(store, "Upscale", model="upscale", sources=["gen:2"])
    assert events(store, up_a) == []


# guards: note_new's `made_from` -- an output made FROM another is not a regen of it
def test_what_an_output_was_made_from_is_not_discarded_by_it(store):
    draft, _ = made(store, "shot 1", concept_id=10, shot_n=1, part=1)
    made(store, "shot 1", model="upscale", concept_id=10, shot_n=1, part=1,
         sources=[f"gen:{draft}"])
    assert events(store, draft) == []


def _pair(dsn, concept, shot=1):
    ref = outcomes.pair_ref(concept, shot)
    winners.record_pair("wan", "the model's draft", "the person's edit", note="edited by hand",
                        video_ref=ref, dsn=dsn, ingest=False)
    return ref


# guards: note_new + _settle_edit_pair -- a kept output teaches the edit it was made from
def test_a_kept_output_teaches_the_edited_prompt(store, monkeypatch):
    ref = _pair(store, 11)
    taught = []
    monkeypatch.setattr(winners, "ingest_pending",
                        lambda video_ref, dsn=None, project=None:
                        taught.append((video_ref, project)) or {"ok": True})
    asset, _ = made(store, "the person's edit", concept_id=11, shot_n=1)
    assert events(store, asset) == ["prompt_edit"]
    unrelated, _ = made(store, "no edit here", concept_id=12, shot_n=1)
    assert events(store, unrelated) == []
    outcomes.record("download", asset_id=unrelated, account_id=WHO["mine"], dsn=store)
    assert taught == []
    outcomes.record("download", asset_id=asset, account_id=WHO["mine"], dsn=store)
    assert taught == [(ref, "o-mine")]


# guards: _settle_edit_pair's `live` -- withdrawn only when EVERY output made from the edit is gone
def test_an_edit_is_withdrawn_only_when_all_its_outputs_are_discarded(store):
    ref = _pair(store, 13)
    first, _ = made(store, "the person's edit", concept_id=13, shot_n=1)
    second, _ = made(store, "the person's edit", concept_id=13, shot_n=1)   # regens the first
    assert events(store, first) == ["prompt_edit", "regen"]
    assert events(store, second) == ["prompt_edit"]
    assert len(winners.pending(ref, dsn=store)) == 2       # the pair survives: one output is live
    outcomes.record("delete", asset_id=second, account_id=WHO["mine"], dsn=store)
    assert winners.pending(ref, dsn=store) == []


# guards: _outputs / keep_rates / attempts_before_keeper / credits_per_kept / discard_mix
def test_the_numbers_are_per_account_by_week(store, monkeypatch):
    monkeypatch.setattr(ledger, "charge_credits", lambda usd: int(round(float(usd) * 240)))
    cid = preprod.save_concept(
        {"title": "S", "hook": "", "logline": "",
         "shots": [{"n": 1, "type": "BROLL", "source": "AI", "tool": "WAN", "desc": "d",
                    "prompt": "p", "refs": ["/refs/a.jpg"],
                    "timeline": {"brain": "reasoning", "parts": []}}]},
        brand="zeropage", prompt_template="TEMPLATE", dsn=store, account_id=WHO["mine"])
    a, _ = made(store, "one", concept_id=cid, shot_n=1, part=1)     # regen'd by b
    b, _ = made(store, "two", concept_id=cid, shot_n=1, part=1)     # kept on the second try
    c, _ = made(store, "solo", model="flux", kind="image")          # deleted
    made(store, "theirs", who="theirs")
    outcomes.record("cut_add", asset_id=b, account_id=WHO["mine"], dsn=store)
    outcomes.record("delete", asset_id=c, account_id=WHO["mine"], dsn=store)

    got = outcomes.summary(account_id=WHO["mine"], dsn=store)
    assert (got["made"], got["kept"], got["rate"]) == (3, 1, 0.333)
    by_model = {r["key"]: (r["made"], r["kept"]) for r in got["by_model"]}
    assert by_model == {"wan3": (2, 1), "flux": (1, 0)}
    by_brain = {r["key"]: (r["made"], r["kept"]) for r in got["by_brain"]}
    assert by_brain == {"reasoning": (2, 1), "no scene": (1, 0)}
    template = preprod.get_concept(cid, dsn=store, account_id=WHO["mine"])["prompt_hash"]
    assert {r["key"] for r in got["by_template"]} == {template, "no scene"}
    assert got["attempts"] == {"things": 1, "average": 2.0, "median": 2, "first_try": 0,
                               "no_keeper_yet": 1}
    (week,) = got["credits"]
    assert (week["credits"], week["made"], week["kept"], week["per_kept"]) == (360, 3, 1, 360)
    (mix,) = got["discards"]
    assert (mix["made"], mix["deleted"], mix["regenerated"]) == (3, 1, 1)
    assert a and outcomes.summary(account_id=WHO["theirs"], dsn=store)["made"] == 1


# guards: preset_counts -- outputs counted against the camera preset their scene was written with
def test_a_presets_outputs_are_counted_against_it(store):
    def scene(preset=None):
        cid = preprod.save_concept(
            {"title": "S", "hook": "", "logline": "",
             "shots": [{"n": 1, "type": "BROLL", "source": "AI", "tool": "WAN", "desc": "d",
                        "prompt": "p", "refs": ["/refs/a.jpg"]}]},
            brand="zeropage", dsn=store, account_id=WHO["mine"])
        if preset:
            assert preprod.set_shot_preset(cid, 1, preset, dsn=store, account_id=WHO["mine"])
        return cid

    orbit, plain = scene("orbit"), scene()
    kept, _ = made(store, "orbit take", concept_id=orbit, shot_n=1, part=1)
    made(store, "orbit, another shot", concept_id=orbit, shot_n=1, part=2)
    made(store, "no preset", concept_id=plain, shot_n=1)
    outcomes.record("star", asset_id=kept, account_id=WHO["mine"], dsn=store)

    assert outcomes.preset_counts(account_id=WHO["mine"], dsn=store) == {
        "orbit": {"tried": 2, "kept": 1}}
    assert outcomes.preset_counts(account_id=WHO["theirs"], dsn=store) == {}
    # the label can be cleared, and a scene that is not theirs is left alone
    assert preprod.set_shot_preset(orbit, 1, "", dsn=store, account_id=WHO["mine"])
    assert outcomes.preset_counts(account_id=WHO["mine"], dsn=store) == {}
    assert preprod.set_shot_preset(orbit, 1, "orbit", dsn=store, account_id=WHO["theirs"]) is False
    assert preprod.set_shot_preset(orbit, 9, "orbit", dsn=store, account_id=WHO["mine"]) is False


@pytest.fixture
def taught(store, monkeypatch):
    """What reached the winning shelf, with the embedding call stood in for."""
    filed = []
    monkeypatch.setattr(winners, "ingest_to_rag",
                        lambda entry_id, dsn=None, project=None:
                        filed.append((entry_id, project)) or {"ok": True, "error": None})
    accounts.set_prompt_edits_teach("o-mine", True, dsn=store)
    return filed


def _scene(dsn, prompt="THE SCENE PROMPT, as the writer wrote it", who="mine"):
    return preprod.save_concept(
        {"title": "S", "hook": "", "logline": "",
         "shots": [{"n": 1, "type": "BROLL", "source": "AI", "tool": "WAN", "desc": "d",
                    "prompt": prompt, "refs": ["/refs/a.jpg"]}]},
        brand="zeropage", dsn=dsn, account_id=WHO[who])


# guards: _teach_keeper -- a kept output's SCENE prompt is filed once, under the shot's own name
def test_a_kept_outputs_prompt_becomes_a_winning_example(store, taught):
    cid = _scene(store)
    first, _ = made(store, "CONTINUITY ... SHOT 1 OF 2", concept_id=cid, shot_n=1, part=1)
    second, _ = made(store, "CONTINUITY ... SHOT 2 OF 2", concept_id=cid, shot_n=1, part=2)
    assert winners.recorded(outcomes.pair_ref(cid, 1), dsn=store) == []     # made is not kept
    outcomes.record("delete", asset_id=second, account_id=WHO["mine"], dsn=store)
    assert winners.recorded(outcomes.pair_ref(cid, 1), dsn=store) == []     # nor is discarded

    outcomes.record("cut_add", asset_id=first, account_id=WHO["mine"], dsn=store)
    (row,) = winners.recorded(outcomes.pair_ref(cid, 1), dsn=store)
    assert row["prompt"] == "THE SCENE PROMPT, as the writer wrote it"     # the scene's, not the part's
    assert (row["verdict"], row["note"], row["tool"].lower()) == ("worked", "kept output", "wan3")
    assert taught == [(row["id"], "o-mine")]                                # labelled with who taught it

    # kept again, and its sibling shot kept too: one lesson per shot, not three
    outcomes.record("export", asset_id=first, account_id=WHO["mine"], dsn=store)
    outcomes.record("star", asset_id=second, account_id=WHO["mine"], dsn=store)
    assert len(winners.recorded(outcomes.pair_ref(cid, 1), dsn=store)) == 1


# guards: _teach_keeper's gate -- the shared shelf learns only from an account that teaches
def test_only_an_account_that_teaches_reaches_the_shelf(store, taught):
    theirs = _scene(store, who="theirs")
    asset, _ = made(store, "their clip", who="theirs", concept_id=theirs, shot_n=1)
    assert outcomes.record("download", asset_id=asset, account_id=WHO["theirs"], dsn=store)
    assert winners.recorded(outcomes.pair_ref(theirs, 1), dsn=store) == [] and taught == []
    # the event itself is still recorded: it counts on Stats, it just teaches nothing
    assert events(store, asset, who="theirs") == ["download"]


# guards: _teach_keeper's exclusions and its no-scene path
def test_what_was_not_written_is_never_taught(store, taught):
    solo, _ = made(store, "a red can, hard sun", kind="image", model="flux")
    upscaled, _ = made(store, "Upscale", model="upscale", sources=[f"gen:{solo}"])
    outcomes.record("star", asset_id=upscaled, account_id=WHO["mine"], dsn=store)
    assert winners.recorded(f"gen:{upscaled}", dsn=store) == []              # an effect's words
    outcomes.record("star", asset_id=solo, account_id=WHO["mine"], dsn=store)
    (row,) = winners.recorded(f"gen:{solo}", dsn=store)                      # made for no scene
    assert row["prompt"] == "a red can, hard sun" and row["tool"].lower() == "flux"


# guards: record's order -- an edit that is taught IS the shot's lesson; the keeper adds no second one
def test_an_edited_shot_is_taught_by_its_pair_and_not_twice(store, taught):
    cid = _scene(store, prompt="the person's edit")
    ref = outcomes.pair_ref(cid, 1)
    winners.record_pair("wan", "the model's draft", "the person's edit", note="edited by hand",
                        video_ref=ref, dsn=store, ingest=False)
    asset, _ = made(store, "the person's edit", concept_id=cid, shot_n=1)
    outcomes.record("download", asset_id=asset, account_id=WHO["mine"], dsn=store)
    rows = winners.recorded(ref, dsn=store)
    assert sorted(r["verdict"] for r in rows) == ["didnt_work", "worked"]    # the pair, nothing more
    assert {r["note"] for r in rows} == {"edited by hand"}
    assert len(taught) == 2                                                  # both halves ingested

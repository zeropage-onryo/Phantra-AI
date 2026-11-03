"""Trending on Phantra (src/popular.py, 2026-11-02): totals across every
account, past a floor, naming only catalogue keys -- never a prompt, a
render or an account."""
import json

import pytest

from src import db, effects, fal, generative, popular, whats_new
from src.shot import Shot

# a priced effect (not a free look) and a look, straight off the table
EFFECT = next(n for n, r in effects.EFFECTS.items()
              if r.get("category") != "look" and r.get("provider") != "local")
LOOK = next(n for n, r in effects.EFFECTS.items() if r.get("category") == "look")
MODEL = "grok1.5"


def _rows(spec):
    """[(account_id, params)] -> the (account_id, params_json) rows count() reads."""
    return [(a, json.dumps(p)) for a, p in spec]


def _fx(name):
    return {"provider": "fal", "model": name, "effect": name}


# -- the pure count --------------------------------------------------------------

def test_a_key_trends_only_past_both_floors():
    # three accounts, five runs: on the wall
    rows = _rows([(1, _fx(EFFECT))] * 3 + [(2, _fx(EFFECT)), (3, _fx(EFFECT))])
    assert [i["id"] for i in popular.count(rows)] == [f"effect:{EFFECT}"]
    # one account's spree is never trending, however many runs
    assert popular.count(_rows([(1, _fx(EFFECT))] * 50)) == []
    # two accounts are not enough either
    assert popular.count(_rows([(1, _fx(EFFECT))] * 10 + [(2, _fx(EFFECT))] * 10)) == []
    # three accounts but four runs: under the run floor
    assert popular.count(_rows([(1, _fx(EFFECT)), (2, _fx(EFFECT)), (3, _fx(EFFECT)),
                                (3, _fx(EFFECT))])) == []


def test_what_leaves_is_a_total_never_who():
    rows = _rows([(a, _fx(EFFECT)) for a in (11, 12, 13, 14, 15)])
    [item] = popular.count(rows)
    assert set(item) == {"id", "source", "key", "label", "runs"}
    assert item["runs"] == 5
    assert "11" not in repr(item) and "accounts" not in repr(item)


def test_effects_looks_and_models_map_to_their_catalogue_keys():
    cat = popular._catalogue()
    assert popular.key_of(_fx(EFFECT), cat)[:2] == ("effect", EFFECT)
    assert popular.key_of({"provider": "local", "effect": LOOK, "look": LOOK}, cat)[:2] == ("look", LOOK)
    assert popular.key_of({"provider": "fal", "model": MODEL}, cat)[:2] == ("model", MODEL)
    # the house account's showcase render is the wall's own picture, not a use
    assert popular.key_of({"provider": "fal", "model": MODEL, "source": "showcase"}, cat) is None
    # off the catalogue, or not fal: nothing
    assert popular.key_of({"provider": "fal", "model": "not-a-model"}, cat) is None
    assert popular.key_of({"provider": "fal", "effect": "not-an-effect"}, cat) is None
    assert popular.key_of({"provider": "gemini", "model": MODEL}, cat) is None
    assert popular.key_of(None, cat) is None


def test_more_studios_beat_one_studios_spree():
    wide = [(a, {"provider": "fal", "model": MODEL}) for a in (1, 2, 3, 4, 5, 6)]
    deep = [(a, _fx(EFFECT)) for a in (1, 2, 3)] * 10
    out = popular.count(_rows(wide + deep))
    assert [i["id"] for i in out] == [f"model:{MODEL}", f"effect:{EFFECT}"]


def test_a_malformed_row_is_skipped_not_fatal():
    rows = _rows([(a, _fx(EFFECT)) for a in (1, 2, 3, 4, 5)]) + [(6, "{not json"), (7, None)]
    assert popular.count(rows)[0]["runs"] == 5


# -- against the database --------------------------------------------------------

def _log(pg, account_id, params, *, landed=True):
    generative.ensure(dsn=pg)
    shot = generative.add_shot(Shot(subject="x", action="y"), dsn=pg, account_id=account_id)
    gid = generative.record_generation(
        shot, "fal", "a private prompt", params=params,
        output_path="/renders/x.mp4" if landed else None, dsn=pg, account_id=account_id)
    return gid


@pytest.fixture
def studios(pg):
    """Ten real workspaces: a shot's owner must exist."""
    from src import accounts
    accounts.init(pg)
    return [accounts.upsert_account(f"pop-{n}", f"Studio {n}", "#fff", dsn=pg) for n in range(10)]


@pytest.fixture(autouse=True)
def _fresh():
    popular.clear_cache()
    yield
    popular.clear_cache()


def test_top_reads_every_account_and_only_landed_recent_uses(pg, studios):
    for a in studios[:5]:
        _log(pg, a, {"provider": "fal", "model": MODEL})
    # failed attempts and last month's uses do not count
    for a in studios[5:]:
        _log(pg, a, _fx(EFFECT), landed=False)
    old = [_log(pg, a, _fx(EFFECT)) for a in studios[5:]]
    with db.connect(pg) as conn:
        conn.execute("UPDATE generations SET created_at = '2020-01-01T00:00:00+00:00'"
                     " WHERE id = ANY(%s)", (old,))
    out = popular.top(dsn=pg, fresh=True)
    assert [(i["id"], i["runs"]) for i in out] == [(f"model:{MODEL}", 5)]
    assert "private prompt" not in repr(out)


def test_a_key_no_longer_offered_drops_out(pg, studios, monkeypatch):
    for a in studios[:5]:
        _log(pg, a, {"provider": "fal", "model": MODEL})
    assert popular.top(dsn=pg, fresh=True)
    rows = dict(fal.VIDEO_MODELS)
    rows.pop(MODEL)
    monkeypatch.setattr(fal, "VIDEO_MODELS", rows)
    assert popular.top(dsn=pg, fresh=True) == []


def test_an_unreadable_store_is_an_empty_answer(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("down")
    monkeypatch.setattr(popular, "_read", boom)
    assert popular.top(fresh=True) == []


def test_the_answer_is_cached_between_visits(pg, studios, monkeypatch):
    for a in studios[:5]:
        _log(pg, a, {"provider": "fal", "model": MODEL})
    first = popular.top(dsn=pg)
    calls = []
    monkeypatch.setattr(popular, "_read", lambda *a, **k: calls.append(1) or [])
    assert popular.top(dsn=pg) == first and not calls
    assert popular.top(dsn=pg, fresh=True) == [] and calls


# -- the feed carries it ----------------------------------------------------------

@pytest.fixture
def ws(pg):
    from src import accounts
    accounts.init(pg)
    return accounts.upsert_account("pop-one", "One", "#fff", dsn=pg)


def test_the_feed_marks_a_live_tile_that_is_trending(pg, ws, studios, monkeypatch):
    monkeypatch.setattr(whats_new, "FEATURES", [])
    monkeypatch.setattr(whats_new, "COMING_SOON", [])
    monkeypatch.setattr(whats_new, "DEALS", [])
    whats_new.sync(pg)
    with db.connect(pg) as conn:
        conn.execute("UPDATE showcase_items SET status = 'live', media = 'site/showcase/g.mp4',"
                     " live_at = now() - interval '40 days' WHERE id = %s", (f"model:{MODEL}",))
    for a in studios[:6]:
        _log(pg, a, {"provider": "fal", "model": MODEL})
    out = whats_new.feed(ws, "u1", dsn=pg)
    assert out["trending"] == [{"id": f"model:{MODEL}", "source": "model", "key": MODEL,
                                "label": out["trending"][0]["label"], "runs": 6}]
    [tile] = [i for i in out["items"] if i["id"] == f"model:{MODEL}"]
    assert tile["trending_runs"] == 6
    # still no price anywhere, and no other account's number beyond the total
    text = repr(out)
    assert "credit" not in text.lower() and "Studio" not in text and "pop-" not in text

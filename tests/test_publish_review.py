"""
The publish review flow (src/publish_review.py).

Three promises are worth more than the coverage:

1. Nothing reaches TikTok until the person has answered every Direct Post
   question -- privacy chosen (no default), the declaration agreed to,
   commercial content disclosed properly. `test_refusals_send_nothing`
   counts network calls, not just return values.
2. A press of Post sends ONE post, however many times it arrives.
3. No MCP tool can post. The studio surface may DRAFT (`prepare_post`);
   the only caller of `publish_review.submit` is the signed-in route.
   `test_no_mcp_path_reaches_submit` walks mcp_server's AST, because a
   docstring promise cannot fail CI and a convenience call six months from
   now is how it would break.
"""
import ast
import json
from pathlib import Path

import pytest

from src import accounts, mcp_server, publish_review, render_assets, tiktok

CREATOR = {
    "creator_username": "zp.studio", "creator_nickname": "Zero Page",
    "creator_avatar_url": "https://example.com/a.jpg",
    "privacy_level_options": ["PUBLIC_TO_EVERYONE", "MUTUAL_FOLLOW_FRIENDS", "SELF_ONLY"],
    "comment_disabled": False, "duet_disabled": True, "stitch_disabled": False,
    "max_video_post_duration_sec": 600,
}
MEDIA = "https://media.example.com/renders/clip.mp4"


class FakeTikTok:
    """Stands in for tiktok._request, the module's one network seam."""

    def __init__(self, status="PROCESSING_DOWNLOAD"):
        self.calls = []
        self.status = status

    def __call__(self, method, url, token, payload=None, params=None):
        self.calls.append((url, payload))
        if url == tiktok.CREATOR_INFO_URL:
            return {"data": CREATOR, "error": {"code": "ok"}}
        if url == tiktok.PUBLISH_INIT_URL:
            return {"data": {"publish_id": "p_123"}, "error": {"code": "ok"}}
        if url == tiktok.PUBLISH_STATUS_URL:
            return {"data": {"status": self.status,
                             "publicaly_available_post_id": [7350000000001]},
                    "error": {"code": "ok"}}
        raise AssertionError(f"unexpected call {url}")

    def inits(self):
        return [p for u, p in self.calls if u == tiktok.PUBLISH_INIT_URL]


@pytest.fixture
def env(pg, monkeypatch):
    publish_review.init(pg)
    render_assets.init(pg)
    acct = accounts.upsert_account("studio", "Studio", dsn=pg)
    other = accounts.upsert_account("someone-else", "Someone", dsn=pg)
    monkeypatch.setenv(publish_review.OPERATOR_ENV, "studio")
    monkeypatch.setenv("TIKTOK_ACCESS_TOKEN", "tok_secret")
    monkeypatch.setenv(publish_review.VERIFIED_ENV, "media.example.com")
    monkeypatch.delenv(publish_review.MEDIA_BASE_ENV, raising=False)
    fake = FakeTikTok()
    monkeypatch.setattr(tiktok, "_request", fake)
    return {"dsn": pg, "acct": acct, "other": other, "fake": fake}


def _render(dsn, account_id, *, kind="video", url=MEDIA, seconds=8.0):
    from src import db
    with db.connect(dsn) as conn:
        row = conn.execute(
            "INSERT INTO generated_assets (created_at, generation_id, tool, model, media_kind, "
            "prompt, media_url, metadata_json, account_id) VALUES "
            "('2026-10-11', (SELECT COALESCE(MAX(generation_id), 0) + 1 FROM generated_assets), "
            "'fal', 'kling', %s, 'a shot', %s, %s, %s) RETURNING id",
            (kind, url, json.dumps({"seconds": seconds}), account_id)).fetchone()
    return f"gen:{row['id']}"


GOOD = {"privacy_level": "PUBLIC_TO_EVERYONE", "allow_comment": True, "allow_duet": True,
        "allow_stitch": False, "commercial": {"enabled": False}, "consent": True}


# --- the rules, pure ------------------------------------------------------------------

def _creator():
    return publish_review.creator_view(CREATOR)


def test_privacy_must_be_chosen_and_offered():
    with pytest.raises(publish_review.PublishError, match="no default"):
        publish_review.validate_tiktok({**GOOD, "privacy_level": None}, _creator(),
                                       seconds=5, ai_generated=True)
    with pytest.raises(publish_review.PublishError, match="not available"):
        publish_review.validate_tiktok({**GOOD, "privacy_level": "FOLLOWER_OF_CREATOR"},
                                       _creator(), seconds=5, ai_generated=True)


def test_consent_is_required():
    with pytest.raises(publish_review.PublishError, match="declaration"):
        publish_review.validate_tiktok({**GOOD, "consent": False}, _creator(),
                                       seconds=5, ai_generated=True)


def test_commercial_disclosure_rules():
    with pytest.raises(publish_review.PublishError, match="Your brand"):
        publish_review.validate_tiktok({**GOOD, "commercial": {"enabled": True}},
                                       _creator(), seconds=5, ai_generated=True)
    with pytest.raises(publish_review.PublishError, match="private"):
        publish_review.validate_tiktok(
            {**GOOD, "privacy_level": "SELF_ONLY",
             "commercial": {"enabled": True, "branded_content": True}},
            _creator(), seconds=5, ai_generated=True)
    out = publish_review.validate_tiktok(
        {**GOOD, "commercial": {"enabled": True, "your_brand": True}},
        _creator(), seconds=5, ai_generated=True)
    assert out["brand_organic_toggle"] is True and out["brand_content_toggle"] is False


def test_a_creator_switched_off_interaction_stays_off():
    out = publish_review.validate_tiktok(GOOD, _creator(), seconds=5, ai_generated=True)
    assert out["disable_duet"] is True          # creator turned Duet off on TikTok
    assert out["disable_comment"] is False
    assert out["disable_stitch"] is True        # the person left it unticked


def test_ai_label_is_locked_on_for_renders_only():
    rendered = publish_review.validate_tiktok({**GOOD, "is_aigc": False}, _creator(),
                                              seconds=5, ai_generated=True)
    imported = publish_review.validate_tiktok({**GOOD, "is_aigc": False}, _creator(),
                                              seconds=5, ai_generated=False)
    assert rendered["is_aigc"] is True and imported["is_aigc"] is False


def test_too_long_for_the_account():
    with pytest.raises(publish_review.PublishError, match="at most 600s"):
        publish_review.validate_tiktok(GOOD, _creator(), seconds=601, ai_generated=True)


# --- the media host -------------------------------------------------------------------

def test_media_problem_fails_closed(monkeypatch):
    monkeypatch.delenv(publish_review.VERIFIED_ENV, raising=False)
    assert "unset" in publish_review.media_problem("tiktok", MEDIA)
    monkeypatch.setenv(publish_review.VERIFIED_ENV, "example.com")
    assert publish_review.media_problem("tiktok", MEDIA) is None            # subdomain
    assert "https" in publish_review.media_problem("tiktok", "http://media.example.com/a.mp4")
    assert "IP" in publish_review.media_problem("tiktok", "https://10.0.0.1/a.mp4")
    assert "not a verified" in publish_review.media_problem(
        "tiktok", "https://pub-abc.r2.dev/a.mp4")


def test_url_prefix_entries_are_exact(monkeypatch):
    monkeypatch.setenv(publish_review.VERIFIED_ENV, "https://cdn.example.com/videos/")
    assert publish_review.media_problem("tiktok", "https://cdn.example.com/videos/a.mp4") is None
    assert publish_review.media_problem("tiktok", "https://cdn.example.com/other/a.mp4")


def test_publish_url_moves_bucket_urls_onto_the_verified_host(monkeypatch):
    monkeypatch.setenv("R2_PUBLIC_BASE_URL", "https://pub-abc.r2.dev")
    monkeypatch.setenv(publish_review.MEDIA_BASE_ENV, "https://media.example.com/")
    assert publish_review.publish_url("https://pub-abc.r2.dev/k/clip.mp4") == \
        "https://media.example.com/k/clip.mp4"
    assert publish_review.publish_url("https://elsewhere.com/clip.mp4") == \
        "https://elsewhere.com/clip.mp4"


# --- the flow -------------------------------------------------------------------------

def test_prepare_sends_nothing(env):
    ref = _render(env["dsn"], env["acct"])
    out = publish_review.prepare(ref, caption="hello", account_id=env["acct"],
                                 created_via="mcp", dsn=env["dsn"])
    assert out["review_url"].endswith(f"/studio/publish/{out['session_id']}")
    assert out["media_problem"] is None
    assert env["fake"].calls == []


def test_prepare_refuses_images_and_other_accounts_renders(env):
    image = _render(env["dsn"], env["acct"], kind="image", url="https://media.example.com/a.png")
    with pytest.raises(publish_review.PublishError, match="takes a video"):
        publish_review.prepare(image, account_id=env["acct"], dsn=env["dsn"])
    theirs = _render(env["dsn"], env["other"])
    with pytest.raises(publish_review.PublishError, match="no render"):
        publish_review.prepare(theirs, account_id=env["acct"], dsn=env["dsn"])
    with pytest.raises(publish_review.PublishError, match="gen:<id>"):
        publish_review.prepare(MEDIA, account_id=env["acct"], dsn=env["dsn"])


def test_review_fetches_creator_info_fresh(env):
    ref = _render(env["dsn"], env["acct"])
    sid = publish_review.prepare(ref, account_id=env["acct"], dsn=env["dsn"])["session_id"]
    page = publish_review.review(sid, account_id=env["acct"], dsn=env["dsn"])
    assert page["creator"]["nickname"] == "Zero Page"
    assert page["creator"]["duet_disabled"] is True
    assert page["declarations"]["default"] == publish_review.DECLARATION_MUSIC
    assert [u for u, _ in env["fake"].calls] == [tiktok.CREATOR_INFO_URL]


def test_refusals_send_nothing(env):
    ref = _render(env["dsn"], env["acct"])
    sid = publish_review.prepare(ref, account_id=env["acct"], dsn=env["dsn"])["session_id"]
    for bad in ({**GOOD, "consent": False}, {**GOOD, "privacy_level": None}):
        with pytest.raises(publish_review.PublishError):
            publish_review.submit(sid, bad, account_id=env["acct"], user_id="u1", dsn=env["dsn"])
    assert env["fake"].inits() == []
    assert publish_review.review(sid, account_id=env["acct"], dsn=env["dsn"])["status"] == "draft"


def test_one_press_one_post(env):
    ref = _render(env["dsn"], env["acct"])
    sid = publish_review.prepare(ref, caption="draft", account_id=env["acct"],
                                 dsn=env["dsn"])["session_id"]
    first = publish_review.submit(sid, {**GOOD, "caption": "final words"},
                                  account_id=env["acct"], user_id="u1", dsn=env["dsn"])
    again = publish_review.submit(sid, GOOD, account_id=env["acct"], user_id="u1",
                                  dsn=env["dsn"])
    assert first["status"] == again["status"] == "posting"
    (sent,) = env["fake"].inits()
    assert sent["post_info"]["title"] == "final words"
    assert sent["post_info"]["privacy_level"] == "PUBLIC_TO_EVERYONE"
    assert sent["post_info"]["disable_duet"] is True
    assert sent["post_info"]["is_aigc"] is True
    assert sent["source_info"] == {"source": "PULL_FROM_URL", "video_url": MEDIA}
    assert first["result"] == {"publish_id": "p_123"}


def test_refresh_records_the_post(env):
    ref = _render(env["dsn"], env["acct"])
    sid = publish_review.prepare(ref, account_id=env["acct"], dsn=env["dsn"])["session_id"]
    publish_review.submit(sid, GOOD, account_id=env["acct"], user_id="u1", dsn=env["dsn"])
    assert publish_review.review(sid, account_id=env["acct"], dsn=env["dsn"])["status"] == "posting"
    env["fake"].status = "PUBLISH_COMPLETE"
    done = publish_review.review(sid, account_id=env["acct"], dsn=env["dsn"])
    assert done["status"] == "published"
    assert done["result"]["post_id"] == "7350000000001"


def test_only_the_operator_posts_on_the_installation_token(env):
    ref = _render(env["dsn"], env["other"])
    sid = publish_review.prepare(ref, account_id=env["other"], dsn=env["dsn"])["session_id"]
    page = publish_review.review(sid, account_id=env["other"], dsn=env["dsn"])
    assert page["creator"] is None and "Connect your TikTok" in page["creator_problem"]
    with pytest.raises(publish_review.PublishError, match="Connect your TikTok"):
        publish_review.submit(sid, GOOD, account_id=env["other"], user_id="u2", dsn=env["dsn"])
    assert env["fake"].calls == []


def test_sessions_are_fenced_by_account(env):
    ref = _render(env["dsn"], env["acct"])
    sid = publish_review.prepare(ref, account_id=env["acct"], dsn=env["dsn"])["session_id"]
    with pytest.raises(publish_review.PublishError, match="no such post"):
        publish_review.review(sid, account_id=env["other"], dsn=env["dsn"])
    with pytest.raises(publish_review.PublishError, match="no such post"):
        publish_review.submit(sid, GOOD, account_id=env["other"], user_id="u2", dsn=env["dsn"])


def test_unverified_media_is_refused_before_the_press_reaches_tiktok(env, monkeypatch):
    ref = _render(env["dsn"], env["acct"], url="https://pub-abc.r2.dev/clip.mp4")
    out = publish_review.prepare(ref, account_id=env["acct"], dsn=env["dsn"])
    assert "not a verified" in out["media_problem"]
    with pytest.raises(publish_review.PublishError, match="not a verified"):
        publish_review.submit(out["session_id"], GOOD, account_id=env["acct"],
                              user_id="u1", dsn=env["dsn"])
    assert env["fake"].inits() == []


def test_a_failed_init_is_recorded_without_the_token(env, monkeypatch):
    ref = _render(env["dsn"], env["acct"])
    sid = publish_review.prepare(ref, account_id=env["acct"], dsn=env["dsn"])["session_id"]
    real = env["fake"]

    def failing(method, url, token, payload=None, params=None):
        if url == tiktok.PUBLISH_INIT_URL:
            raise RuntimeError(f"url_ownership_unverified for {token}")
        return real(method, url, token, payload, params)
    monkeypatch.setattr(tiktok, "_request", failing)
    out = publish_review.submit(sid, GOOD, account_id=env["acct"], user_id="u1", dsn=env["dsn"])
    assert out["status"] == "failed" and out["result"]["step"] == "init"
    assert "tok_secret" not in json.dumps(out)


def test_cancel_only_drafts(env):
    ref = _render(env["dsn"], env["acct"])
    sid = publish_review.prepare(ref, account_id=env["acct"], dsn=env["dsn"])["session_id"]
    assert publish_review.cancel(sid, account_id=env["acct"], dsn=env["dsn"])["status"] == "cancelled"
    assert publish_review.submit(sid, GOOD, account_id=env["acct"], user_id="u1",
                                 dsn=env["dsn"])["status"] == "cancelled"
    assert env["fake"].inits() == []


# --- the MCP surface ------------------------------------------------------------------

def test_prepare_post_is_studio_only_and_drafts(env):
    assert "prepare_post" in mcp_server.STUDIO_TOOLS
    ref = _render(env["dsn"], env["acct"])
    out = mcp_server.run_prepare_post(ref, caption="from claude", dsn=env["dsn"],
                                      account_id=env["acct"])
    page = publish_review.review(out["session_id"], account_id=env["acct"], dsn=env["dsn"])
    assert page["created_via"] == "mcp" and page["status"] == "draft"
    assert env["fake"].inits() == []


def test_no_mcp_path_reaches_submit():
    tree = ast.parse(Path(mcp_server.__file__).read_text())
    forbidden = {"submit", "init_direct_post", "post_video", "execute_post_action"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in forbidden:
            owner = node.value.id if isinstance(node.value, ast.Name) else ""
            assert owner not in {"publish_review", "tiktok", "instagram", "youtube"}, (
                f"mcp_server.py line {node.lineno} reaches {owner}.{node.attr}: posting is "
                "the person's press on the review page, never a tool")
    for name in mcp_server.STUDIO_TOOLS:
        assert "publish" not in name and name != "post", name


# --- found in review (2026-10-11) -----------------------------------------------------

def test_render_length_is_read_from_its_metadata(env, monkeypatch):
    long_clip = _render(env["dsn"], env["acct"], seconds=700)
    sid = publish_review.prepare(long_clip, account_id=env["acct"], dsn=env["dsn"])["session_id"]
    assert publish_review.review(sid, account_id=env["acct"], dsn=env["dsn"])["seconds"] == 700
    with pytest.raises(publish_review.PublishError, match="at most 600s"):
        publish_review.submit(sid, GOOD, account_id=env["acct"], user_id="u1", dsn=env["dsn"])
    assert env["fake"].inits() == []


@pytest.mark.parametrize("meta,want", [
    ({"seconds": 8.0}, 8.0), ({"duration": "8s"}, 8.0), ({"params": {"duration": "5"}}, 5.0),
    ({}, None), ({"duration": "auto"}, None),
])
def test_seconds_parsing(meta, want):
    assert publish_review._seconds(meta) == want


def test_a_claim_that_lost_its_answer_fails_instead_of_polling_forever(env):
    from src import db
    ref = _render(env["dsn"], env["acct"])
    sid = publish_review.prepare(ref, account_id=env["acct"], dsn=env["dsn"])["session_id"]
    with db.connect(env["dsn"]) as conn:     # claimed 11 minutes ago, no publish_id stored
        conn.execute("UPDATE publish_sessions SET status = 'posting', "
                     "submitted_at = now() - interval '11 minutes' WHERE id = %s", (sid,))
    out = publish_review.review(sid, account_id=env["acct"], dsn=env["dsn"])
    assert out["status"] == "failed" and "check your TikTok profile" in out["result"]["error"]
    assert env["fake"].calls == []


def test_creator_errors_are_redacted(env, monkeypatch):
    ref = _render(env["dsn"], env["acct"])
    sid = publish_review.prepare(ref, account_id=env["acct"], dsn=env["dsn"])["session_id"]

    def leaky(method, url, token, payload=None, params=None):
        raise RuntimeError(f"401 for Bearer {token}")
    monkeypatch.setattr(tiktok, "_request", leaky)
    page = publish_review.review(sid, account_id=env["acct"], dsn=env["dsn"])
    assert page["creator"] is None and "<redacted>" in page["creator_problem"]
    assert "tok_secret" not in json.dumps(page, default=str)

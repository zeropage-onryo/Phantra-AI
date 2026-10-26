"""The free looks Discord bot's door (2026-10-26): a third kind of plugin
token (src/plugin_tokens.py `discord-bot`) on app/plugin_api.py.

What these pin, in the order a mistake would cost:

- a bot token reaches the free looks, the upload that feeds them, its own
  jobs and `/me` -- and NOT ONE tool and not a scene's clips, so a leaked
  bot token can never quote, approve or spend;
- `/looks/run` refuses any row that is not free, whatever it is asked,
  and starts nothing for it;
- a free look runs through the studio card's own job body and is polled
  from `/jobs/{id}`, which shows only the caller's own jobs;
- the panels' door is unchanged (their tools still answer).

The end-to-end test uploads a real clip and runs a real look with ffmpeg,
the way the bot will.
"""
import time

import pytest
import test_plugin_api as panels

from app import api, jobs, plugin_api
from src import mcp_server, plugin_tokens

# the panels' fixtures and helpers, shared rather than copied
clean_slate = panels.clean_slate
people = panels.people
full_schema = panels.full_schema
client = panels.client
needs_ffmpeg = panels.needs_ffmpeg
_bearer, _connect, _mp4_bytes = panels._bearer, panels._connect, panels._mp4_bytes


@pytest.fixture
def looks_on(monkeypatch):
    monkeypatch.setenv("PHANTRA_FREE_LOOKS", "1")


def _bot(name="mike"):
    return _connect(name, app="discord-bot")


def test_the_bot_is_its_own_kind_of_sign_in(people):
    assert plugin_tokens.client_label("discord-bot") == "Discord bot"
    assert "Discord bot" in plugin_tokens.BOT_CLIENTS
    token = _bot()
    me = client.get("/plugin/v1/me", headers=_bearer(token))
    assert me.status_code == 200, me.text
    assert me.json()["client"] == "Discord bot"


def test_a_bot_token_reaches_no_tool_at_all(people, monkeypatch):
    """Every panel tool -- the spending ones above all -- is refused before
    anything is read or run, and so is a scene's clips."""
    called = []
    monkeypatch.setattr(plugin_api, "run_tool",
                        lambda *a, **k: called.append(a) or {"ok": True})
    token = _bot()
    for name in plugin_api.PLUGIN_TOOLS:
        refused = client.post(f"/plugin/v1/tools/{name}", json={}, headers=_bearer(token))
        assert refused.status_code == 403, name
        assert refused.json()["error"]["code"] == "not_for_bots"
    assert client.get("/plugin/v1/scenes/1/clips",
                      headers=_bearer(token)).status_code == 403
    assert called == []


def test_a_panel_still_reaches_its_tools(people, full_schema):
    token = _connect("mike")
    ok = client.post("/plugin/v1/tools/whoami", json={}, headers=_bearer(token))
    assert ok.status_code == 200 and ok.json()["result"]["workspace"]["id"] == people["mikes"]


def test_the_looks_listed_are_the_free_rows_only(people, looks_on):
    from src import effects
    token = _bot()
    listed = client.get("/plugin/v1/looks", headers=_bearer(token))
    assert listed.status_code == 200, listed.text
    looks = listed.json()["looks"]
    ids = {look["id"] for look in looks}
    assert {"film_grade", "noir", "make_it_pro"} <= ids
    assert all(effects.EFFECTS[i].get("free") for i in ids)
    assert all(look["credits"] == 0 for look in looks)
    assert client.get("/plugin/v1/looks").status_code == 401


def test_with_the_looks_switched_off_none_are_listed(people, monkeypatch):
    monkeypatch.delenv("PHANTRA_FREE_LOOKS", raising=False)
    token = _bot()
    assert client.get("/plugin/v1/looks", headers=_bearer(token)).json()["looks"] == []


def test_a_priced_effect_is_refused_and_nothing_starts(people, monkeypatch):
    started = []
    monkeypatch.setattr(api, "_effect_request", lambda account_id, body: {
        "effect": body.effect, "row": {"label": "Upscale"}, "free": False, "credits": 40})
    monkeypatch.setattr(api, "start_effect_job",
                        lambda req, account_id: started.append(req) or {"job_id": 1})
    token = _bot()
    refused = client.post("/plugin/v1/looks/run",
                          json={"look": "topaz-upscale", "source": "asset:7"},
                          headers=_bearer(token))
    assert refused.status_code == 402
    assert refused.json()["error"]["code"] == "not_free"
    assert "Nothing was charged" in refused.json()["error"]["message"]
    assert started == []


def test_a_free_row_priced_above_zero_is_still_refused(people, monkeypatch):
    """Belt and braces: `free` alone is not enough, the credits must be 0."""
    monkeypatch.setattr(api, "_effect_request", lambda account_id, body: {
        "effect": body.effect, "row": {"label": "Odd"}, "free": True, "credits": 5})
    monkeypatch.setattr(api, "start_effect_job",
                        lambda *a: pytest.fail("a priced run was started"))
    token = _bot()
    assert client.post("/plugin/v1/looks/run", json={"look": "noir", "source": "asset:7"},
                       headers=_bearer(token)).status_code == 402


def test_only_an_id_is_taken_as_the_source(people):
    token = _bot()
    for source in ("https://example.com/clip.mp4", "asset:", "asset:abc", "file:/etc/passwd"):
        refused = client.post("/plugin/v1/looks/run", json={"look": "noir", "source": source},
                              headers=_bearer(token))
        assert refused.status_code == 400, source


def test_a_free_look_runs_as_the_cards_job_as_the_callers_tenant(people, monkeypatch):
    seen = {}

    def fake_request(account_id, body):
        seen["account"] = account_id
        seen["body"] = body
        return {"effect": body.effect, "row": {"label": "Noir"}, "free": True, "credits": 0}

    monkeypatch.setattr(api, "_effect_request", fake_request)
    monkeypatch.setattr(api, "start_effect_job",
                        lambda req, account_id: {"job_id": 42, "credits": 0})
    token = _bot()
    ran = client.post("/plugin/v1/looks/run", json={"look": "noir", "source": "asset:7"},
                      headers=_bearer(token))
    assert ran.status_code == 200, ran.text
    assert ran.json() == {"ok": True, "job_id": 42, "credits": 0}
    assert seen["account"] == people["mikes"]
    assert seen["body"].sources == ["asset:7"] and seen["body"].effect == "noir"


def test_a_job_is_seen_only_by_its_own_account(people):
    job = jobs.create("effect", "effect · Noir", account_id=people["anas"])
    token = _bot("mike")
    assert client.get(f"/plugin/v1/jobs/{job['id']}",
                      headers=_bearer(token)).status_code == 404
    hers = _bot("ana")
    seen = client.get(f"/plugin/v1/jobs/{job['id']}", headers=_bearer(hers))
    assert seen.status_code == 200 and seen.json()["job"]["id"] == job["id"]


def test_the_listing_servers_are_untouched(people):
    """The connector is in directory review: this door adds no tool to it."""
    assert "looks" not in mcp_server.LISTED_TOOLS
    assert "apply_effect" not in plugin_api.PLUGIN_TOOLS


@needs_ffmpeg
def test_a_clip_from_discord_gets_a_real_free_look(people, full_schema, tmp_path, looks_on):
    """Upload, run Noir, poll until done: the bot's whole round trip, with a
    real clip through ffmpeg and nothing charged."""
    token = _bot()
    sent = client.post("/plugin/v1/upload", content=_mp4_bytes(tmp_path, seconds=2),
                       headers={**_bearer(token), "Content-Type": "application/octet-stream"})
    assert sent.status_code == 200, sent.text
    clip = sent.json()
    assert clip["kind"] == "video"
    ran = client.post("/plugin/v1/looks/run", json={"look": "noir", "source": clip["asset"]},
                      headers=_bearer(token))
    assert ran.status_code == 200, ran.text
    job_id = ran.json()["job_id"]
    deadline = time.monotonic() + 120
    while True:
        polled = client.get(f"/plugin/v1/jobs/{job_id}", headers=_bearer(token))
        assert polled.status_code == 200, polled.text
        job = polled.json()["job"]
        if job["status"] in ("done", "failed", "cancelled"):
            break
        assert time.monotonic() < deadline, "the look never finished"
        time.sleep(0.5)
    assert job["status"] == "done", job
    assert job.get("output") and job.get("asset", "").startswith("gen:")
    assert "free" in (job.get("detail") or "")

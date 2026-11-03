"""Seedance 2.5 at 480p / 720p renders on Replicate (2026-11-02,
src/replicate.py): same row, same quote, half fal's price. The host is
chosen in one place and priced in that place, the request is fal's body
translated, and the live loop, cancel and recovery are fal's own code
spoken through Replicate's transport. No network: Replicate is a fake."""
import pytest

from src import fal, fal_requests, pricing, replicate


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(fal, "POLL_SECONDS", 0)
    monkeypatch.delenv(fal.REPLICATE_ENV, raising=False)


@pytest.fixture
def keys(monkeypatch):
    monkeypatch.setenv("FAL_KEY", "fal-secret-key")
    monkeypatch.setenv("REPLICATE_API_TOKEN", "r8_test")
    monkeypatch.setenv(fal.SPEND_ENV, "1")


class FakeReplicate:
    """Replicate's prediction API: a submit answers `starting`, the get URL
    walks the given statuses, the cancel URL is recorded."""
    GET = f"{replicate.API}/predictions/p1"
    CANCEL = f"{replicate.API}/predictions/p1/cancel"

    def __init__(self, statuses=("processing", "succeeded"), error=None):
        self.calls = []
        self.statuses = list(statuses)
        self.error = error

    def prediction(self, status):
        p = {"id": "p1", "status": status, "urls": {"get": self.GET, "cancel": self.CANCEL}}
        if status == "succeeded":
            p["output"] = "https://replicate.delivery/out/clip.mp4"
        if status == "failed":
            p["error"] = self.error or "boom"
        return p

    def __call__(self, url, data=None, *, method=None):
        self.calls.append((url, data, method))
        if url == self.CANCEL:
            return {}
        if data is not None:
            return self.prediction("starting")
        return self.prediction(self.statuses.pop(0) if len(self.statuses) > 1 else self.statuses[0])


def test_seedance_25_at_480p_and_720p_is_replicates_and_1080p_stays_on_fal(monkeypatch):
    assert fal.host_for("seedance2.5", "720p") == "replicate"
    assert fal.host_for("seedance2.5", "480p") == "replicate"
    assert fal.host_for("seedance2.5", None) == "replicate"           # the row's default, 720p
    assert fal.host_for("seedance2.5", "1080p") == "fal"
    assert fal.host_for("seedance2", "720p") == "fal"                 # no second host listed
    monkeypatch.setenv(fal.REPLICATE_ENV, "0")
    assert fal.host_for("seedance2.5", "720p") == "fal"


def test_the_quote_prices_the_host_that_renders(monkeypatch):
    assert fal.estimate_cost(1, model="seedance2.5", duration=5, resolution="720p") == 1.156
    assert fal.estimate_cost(1, model="seedance2.5", duration=5, resolution="480p") == 0.514
    assert fal.estimate_cost(1, model="seedance2.5", duration=5, resolution="1080p") == 5.82
    # 1.4x, rounded up: what the card shows and the hold takes
    assert pricing.credits_for(pricing.usd_micros(1.156), model="seedance2.5") == 162
    monkeypatch.setenv(fal.REPLICATE_ENV, "0")
    assert fal.estimate_cost(1, model="seedance2.5", duration=5, resolution="720p") == 2.365


def test_fals_body_becomes_replicates_input():
    _, refs = fal.build_body("@Image1 holds the phone from @Image2", model="seedance2.5",
                             duration=5, resolution="720p", aspect_ratio="9:16",
                             reference_urls=["https://cdn/her.png", "https://cdn/app.png"])
    assert replicate.to_input(refs) == {
        "prompt": "[Image1] holds the phone from [Image2]", "duration": 5,
        "reference_images": ["https://cdn/her.png", "https://cdn/app.png"],
        "aspect_ratio": "9:16", "resolution": "720p"}
    _, framed = fal.build_body("she turns", model="seedance2.5", duration=5,
                               resolution="480p", image_url="https://cdn/still.png")
    got = replicate.to_input(framed)
    # a first frame decides the shape: Replicate's default 16:9 would crop it
    assert got["image"] == "https://cdn/still.png" and got["aspect_ratio"] == "adaptive"
    assert replicate.to_input({"prompt": "x", "num_frames": 9}) == {"prompt": "x"}


def test_a_prediction_reads_in_fals_queue_shapes():
    fake = FakeReplicate()
    assert replicate.as_fal(fake.prediction("processing"))["status"] == "IN_PROGRESS"
    done = replicate.as_fal(fake.prediction("succeeded"))
    assert done["status"] == "COMPLETED" and done["video"]["url"].endswith("clip.mp4")
    assert done["status_url"] == fake.GET and done["cancel_url"] == fake.CANCEL
    failed = replicate.as_fal(fake.prediction("failed"))
    assert fal._error_in(failed).startswith("replicate_failed")
    assert replicate.as_fal(fake.prediction("canceled"))["error_type"] == "client_cancelled"


def test_a_720p_render_goes_to_replicate_end_to_end(monkeypatch, keys, tmp_path):
    fake = FakeReplicate()
    monkeypatch.setattr(replicate, "_call", fake)
    got = []
    monkeypatch.setattr(fal, "_download", lambda url, out: (got.append(url), out.write_bytes(b"x")))
    out = fal.generate_video("@Image1 walks", tmp_path / "c.mp4", model="seedance2.5",
                             duration=5, resolution="720p", aspect_ratio="9:16",
                             reference_urls=["https://cdn/a.png"], approved=True)
    assert out.exists() and got == ["https://replicate.delivery/out/clip.mp4"]
    url, data, _ = fake.calls[0]
    assert url == replicate.submit_url("bytedance/seedance-2.5")
    assert data == {"input": {"prompt": "[Image1] walks", "reference_images": ["https://cdn/a.png"],
                              "duration": 5, "aspect_ratio": "9:16", "resolution": "720p"}}
    assert all(c[0].startswith(replicate.API) for c in fake.calls)    # nothing went to fal


def test_no_token_refuses_before_any_request(monkeypatch, keys, tmp_path):
    monkeypatch.delenv("REPLICATE_API_TOKEN")
    fake = FakeReplicate()
    monkeypatch.setattr(replicate, "_call", fake)
    with pytest.raises(RuntimeError, match="REPLICATE_API_TOKEN not set"):
        fal.generate_video("x", tmp_path / "c.mp4", model="seedance2.5", duration=5,
                           resolution="720p", approved=True)
    assert fake.calls == []


def test_a_refused_prediction_raises_with_replicates_reason(monkeypatch, keys, tmp_path):
    fake = FakeReplicate(statuses=("failed",), error="The input or output was flagged as sensitive. (E005)")
    monkeypatch.setattr(replicate, "_call", fake)
    with pytest.raises(RuntimeError, match="flagged as sensitive"):
        fal.generate_video("x", tmp_path / "c.mp4", model="seedance2.5", duration=5,
                           resolution="720p", approved=True)
    assert not (tmp_path / "c.mp4").exists()


def test_a_cancel_posts_replicates_cancel_url():
    fake = FakeReplicate()
    http = replicate.queue_http(fake)
    assert http(fake.CANCEL, fal.CANCEL) == {"status": fal.CANCEL_REQUESTED}
    assert fake.calls == [(fake.CANCEL, {}, "POST")]


def test_the_sweep_reads_a_replicate_receipt_through_replicate(monkeypatch):
    fake = FakeReplicate(statuses=("failed",), error="flagged as sensitive")
    monkeypatch.setattr(replicate, "_call", fake)
    monkeypatch.setattr(fal_requests, "_generation_for", lambda row, dsn: None)
    failed = []
    monkeypatch.setattr(fal_requests, "_fail", lambda row, reason, dsn: failed.append(reason) or
                        {"ref": row["ref"], "outcome": "released"})
    row = {"ref": "r1", "account_id": 7, "model_id": replicate.model_id("bytedance/seedance-2.5"),
           "status_url": fake.GET, "response_url": fake.GET, "cancel_url": fake.CANCEL,
           "out_path": "/tmp/never.mp4"}
    assert fal_requests._recover_one(row, http=None, dsn=None)["outcome"] == "released"
    assert failed and "flagged as sensitive" in failed[0]
    assert fake.calls[0][0] == fake.GET

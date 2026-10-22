"""Storage limits and the 7-day trash (2026-10-20, Mike's calls).

What is counted is the bucket under the workspace's own prefixes, minus the
renders in the trash. Uploads past the plan's limit are refused; renders
never are. A deleted render can be restored for TRASH_DAYS days, then its
file goes -- unless a scene or a cut still plays it.
"""
import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from src import accounts, db, media, preprod, pricing, render_assets, storage, storage_quota
from src.cut import uploads

GB = storage_quota.GB


@pytest.fixture
def world(pg, monkeypatch):
    accounts.init(dsn=pg)
    render_assets.init(pg)
    preprod.init(pg)
    acct = accounts.upsert_account("quota", "Quota", dsn=pg)
    monkeypatch.setattr(render_assets, "_ingest", lambda *a, **k: None)
    monkeypatch.setattr(media, "tenant_keys", lambda: True)
    bucket: dict[str, int] = {}
    deleted: list[str] = []
    monkeypatch.setattr(storage, "sizes_under",
                        lambda prefix: {k: v for k, v in bucket.items() if k.startswith(prefix)})

    def delete_key(key):
        deleted.append(key)
        bucket.pop(key, None)
    monkeypatch.setattr(storage, "delete_key", delete_key)
    return {"dsn": pg, "acct": acct, "bucket": bucket, "deleted": deleted}


_GEN = iter(range(100, 10_000))


def _render(world, name, size, *, kind="video"):
    ext = "mp4" if kind == "video" else "png"
    url = f"/renders/fal/{name}.{ext}"
    row = render_assets.record(generation_id=next(_GEN), tool="fal", model="ltx2.3", media_kind=kind,
                               prompt=name, media_url=url, dsn=world["dsn"],
                               account_id=world["acct"])
    master = media.master_key(url, world["acct"])
    world["bucket"][master] = size
    world["bucket"][media.thumb_key(url, world["acct"]).rsplit(".", 1)[0] + ".jpg"] = 1000
    return row["id"], url, master


def _age(world, asset_id, days):
    when = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="seconds")
    with db.connect(world["dsn"]) as conn:
        conn.execute("UPDATE generated_assets SET deleted_at = %s WHERE id = %s", (when, asset_id))


def test_the_limit_follows_the_plan(world):
    dsn, acct = world["dsn"], world["acct"]
    assert storage_quota.limit_bytes(acct, dsn) == pricing.FREE_STORAGE_GB * GB
    accounts.set_plan(acct, "creator", dsn=dsn)
    assert storage_quota.limit_bytes(acct, dsn) == pricing.PLANS["creator"].storage_gb * GB
    accounts.set_credit_exempt("quota", True, dsn=dsn)
    assert storage_quota.limit_bytes(acct, dsn) is None
    assert storage_quota.limit_bytes(None, dsn) is None


def test_usage_counts_the_bucket_and_leaves_the_trash_out(world):
    dsn, acct = world["dsn"], world["acct"]
    kept, _u, _m = _render(world, "kept", 3 * GB // 10)
    gone, _u2, _m2 = _render(world, "gone", 5 * GB // 10)
    world["bucket"][f"m/{acct}/characters/me/a.jpg"] = 2_000_000
    world["bucket"]["m/shared/refs/x.jpg"] = 9 * GB           # nobody's: not counted
    before = storage_quota.usage(acct, dsn)
    assert before["measured"] and before["trash_count"] == 0
    assert before["used_bytes"] == 3 * GB // 10 + 5 * GB // 10 + 2_000_000 + 2000
    render_assets.soft_delete(gone, dsn, account_id=acct)
    after = storage_quota.usage(acct, dsn)
    assert after["trash_count"] == 1 and after["trash_bytes"] == 5 * GB // 10 + 1000
    assert after["used_bytes"] == before["used_bytes"] - after["trash_bytes"]
    assert kept != gone


def test_unmeasured_usage_refuses_nothing(world, monkeypatch):
    monkeypatch.setattr(storage, "sizes_under", lambda prefix: None)
    state = storage_quota.usage(world["acct"], world["dsn"])
    assert state["measured"] is False and state["used_bytes"] is None
    storage_quota.check_upload(world["acct"], 50 * GB, world["dsn"])     # no raise


def test_an_upload_past_the_limit_is_refused_with_a_way_out(world):
    dsn, acct = world["dsn"], world["acct"]
    world["bucket"][f"m/{acct}/cut/media/big.mp4"] = 19 * GB // 10     # Free is 2 GB
    storage_quota.check_upload(acct, GB // 20, dsn)                    # fits
    with pytest.raises(storage_quota.StorageFull) as full:
        storage_quota.check_upload(acct, GB // 5, dsn)
    text = str(full.value)
    assert "Out of storage" in text and "2.0 GB" in text and "7 days" in text


def test_the_upload_door_says_out_of_storage(monkeypatch, tmp_path):
    def full(account_id, incoming, dsn=None):
        raise storage_quota.StorageFull("Out of storage: 2.1 of 2.0 GB used.", {})
    monkeypatch.setattr(storage_quota, "check_upload", full)
    with pytest.raises(uploads.UploadRefused) as refused:
        uploads.save(b"\x89PNG....", "a.png", account_id=3, media_dir=tmp_path / "media")
    assert refused.value.code == "out_of_storage"
    assert not (tmp_path / "media").exists()                            # nothing written


def test_the_trash_empties_after_seven_days(world):
    dsn, acct = world["dsn"], world["acct"]
    old, _u, master = _render(world, "old", 1000)
    fresh, _u2, _m2 = _render(world, "fresh", 1000)
    for asset_id in (old, fresh):
        render_assets.soft_delete(asset_id, dsn, account_id=acct)
    _age(world, old, storage_quota.TRASH_DAYS + 1)
    _age(world, fresh, storage_quota.TRASH_DAYS - 1)
    done = storage_quota.purge_due(acct, dsn)
    assert done["purged"] == [old] and done["kept"] == {}
    assert master in world["deleted"] and len(world["deleted"]) == 2   # the file and its poster
    assert [r["id"] for r in storage_quota.trashed(acct, dsn)] == [fresh]
    # a purged render cannot come back; a fresh one still can
    assert render_assets.restore(old, dsn, account_id=acct) is False
    assert render_assets.restore(fresh, dsn, account_id=acct) is True


def test_a_trashed_render_a_scene_still_plays_keeps_its_file(world):
    dsn, acct = world["dsn"], world["acct"]
    used, url, master = _render(world, "used", 1000)
    with db.connect(dsn) as conn:
        cid = conn.execute(
            "INSERT INTO shoot_concepts (created_at, title, shots_json, account_id) "
            "VALUES (%s, 't', %s, %s) RETURNING id",
            (db._now(), json.dumps([{"n": 1, "media_url": url}]), acct)).fetchone()["id"]
    render_assets.soft_delete(used, dsn, account_id=acct)
    _age(world, used, storage_quota.TRASH_DAYS + 1)
    done = storage_quota.purge_due(acct, dsn)
    assert done["purged"] == [] and done["kept"] == {used: f"used by scene {cid}"}
    assert master not in world["deleted"]


def test_the_trash_routes(world, monkeypatch):
    from app import auth
    from app.main import app
    dsn, acct = world["dsn"], world["acct"]
    monkeypatch.setenv("DATABASE_URL", dsn)
    monkeypatch.setattr(auth, "current_user", lambda request: {"id": 1, "email": "q@x"})
    app.dependency_overrides[auth.current_account_id] = lambda: acct
    try:
        client = TestClient(app)
        asset_id, _u, master = _render(world, "routed", 1000)
        r = client.delete(f"/api/assets/generated/{asset_id}")
        assert r.status_code == 200, r.text
        trash = client.get("/api/assets/generated/trash")
        assert trash.status_code == 200                      # not read as an id
        body = trash.json()
        assert body["trash_days"] == 7 and [i["generated_id"] for i in body["items"]] == [asset_id]
        bar = client.get("/api/storage").json()
        assert bar["measured"] and bar["trash_count"] == 1 and bar["limit_gb"] == "2.0"
        gone = client.delete(f"/api/assets/generated/{asset_id}/forever")
        assert gone.status_code == 200 and master in world["deleted"]
        assert client.get("/api/assets/generated/trash").json()["items"] == []
        assert client.delete(f"/api/assets/generated/{asset_id}/forever").status_code == 404
    finally:
        app.dependency_overrides.pop(auth.current_account_id, None)

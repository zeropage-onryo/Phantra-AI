from fastapi.testclient import TestClient

from app.main import app


def test_api_origin_serves_the_brand_icon():
    c = TestClient(app)
    for path, kind in (("/favicon.ico", "image/x-icon"), ("/icon.png", "image/png")):
        r = c.get(path)
        assert r.status_code == 200 and r.headers["content-type"] == kind and r.content

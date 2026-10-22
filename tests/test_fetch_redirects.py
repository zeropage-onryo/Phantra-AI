"""The two quiet fetchers check every redirect, not only the first address.

`imagery.fetch_image_bytes` and `refbin.fetch` used to check the host
they were handed and then let `requests` follow redirects on its own, so
a public address answering 302 to a private, loopback or metadata address
was fetched from inside the network -- and `fetch_image_bytes` handed the
bytes back as "an image" whenever the answer carried no content type.
The element create routes pass a caller's `photo_urls` straight to it.

The internet here is a table, and its `requests.get` FOLLOWS redirects by
itself unless it is told not to, as the real one does: a fetcher that
leaves the following to `requests` is seen reaching the private address.
"""
from __future__ import annotations

import io
import ipaddress
from urllib.parse import urljoin

import pytest

from src import imagery, refbin

URL = "https://cdn.example.com/can.png"
PUBLIC = {"cdn.example.com", "img.example.com", "old.example.com"}
SECRET = b"ami-id: ami-0abc\nrole: studio-prod\n"


def _png(colour=(200, 30, 30)) -> bytes:
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), colour).save(buf, "PNG")
    return buf.getvalue()


class _Response:
    def __init__(self, status=200, headers=None, body=b""):
        self.status_code = status
        self.headers = headers or {}
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def iter_content(self, size):
        for i in range(0, len(self._body), size):
            yield self._body[i:i + size]


def _is_ip(host) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


@pytest.fixture
def web(monkeypatch, tmp_path):
    """address -> response. `asked` is every address the network was asked
    for, by the code under test or by `requests` following on its own.
    A literal IP goes to the REAL guard; a name is public only if listed
    (a real lookup would be a DNS query, and tests make none)."""
    import requests

    pages, asked = {}, []

    def get(url, **kw):
        follow = kw.get("allow_redirects", True)
        for _ in range(30):
            asked.append(url)
            if url not in pages:
                raise ConnectionError("no route")
            response = pages[url]
            target = response.headers.get("location")
            if follow and response.status_code in (301, 302, 303, 307, 308) and target:
                url = urljoin(url, target)
                continue
            return response
        raise RuntimeError("too many redirects")

    real_guard = refbin.public_host
    monkeypatch.setattr(requests, "get", get)
    monkeypatch.setattr(refbin, "public_host",
                        lambda host: host in PUBLIC or (_is_ip(host) and real_guard(host)))
    monkeypatch.setattr(refbin, "REFS_DIR", tmp_path / "refs")
    return {"pages": pages, "asked": asked}


def _image(url):
    return imagery.fetch_image_bytes(url)


def _banked(url):
    return refbin.fetch(url)


FETCHERS = pytest.mark.parametrize("fetch", [_image, _banked],
                                   ids=["imagery.fetch_image_bytes", "refbin.fetch"])

# where a public address might send the server, and must not
INSIDE = [
    "http://10.0.0.5/secret.png",                       # a private address
    "http://169.254.169.254/latest/meta-data/",         # the metadata address
    "http://127.0.0.1:8000/api/me",                     # this machine
    "http://[::1]:8000/api/me",
    "http://[fdaa::3]/internal.png",                    # a private v6 network
    "https://internal.example/secret.png",              # a name that is not public
    "file:///etc/passwd",
    "ftp://cdn.example.com/can.png",
]


@FETCHERS
def test_a_public_picture_is_fetched_and_requests_is_never_left_to_follow(web, fetch):
    web["pages"][URL] = _Response(headers={"content-type": "image/png"}, body=_png())
    assert fetch(URL)
    assert web["asked"] == [URL]


@FETCHERS
def test_a_redirect_to_another_public_host_is_still_followed_even_to_http(web, fetch):
    """What the callers had before and keep: a reference behind a
    redirecting host, and a host that still serves plain http."""
    hop = "http://old.example.com/real.png"
    web["pages"][URL] = _Response(302, {"location": hop})
    web["pages"][hop] = _Response(headers={"content-type": "image/png"}, body=_png())
    assert fetch(URL)
    assert web["asked"] == [URL, hop]

    web["asked"].clear()
    web["pages"][URL] = _Response(301, {"location": "/moved/can.png"})     # a relative hop
    web["pages"]["https://cdn.example.com/moved/can.png"] = _Response(
        headers={"content-type": "image/png"}, body=_png())
    assert fetch(URL)
    assert web["asked"] == [URL, "https://cdn.example.com/moved/can.png"]


@FETCHERS
@pytest.mark.parametrize("target", INSIDE)
def test_a_redirect_into_the_network_returns_nothing_and_is_never_asked(web, fetch, target):
    """The page behind the redirect answers with a real picture and no
    content type -- everything the old check let through. It is never
    reached."""
    web["pages"][URL] = _Response(302, {"location": target})
    web["pages"][target] = _Response(body=_png())
    assert fetch(URL) is None
    assert web["asked"] == [URL]                  # no second request


@FETCHERS
def test_a_redirect_loop_returns_nothing_and_asks_each_address_once(web, fetch):
    web["pages"][URL] = _Response(302, {"location": URL})
    assert fetch(URL) is None
    assert web["asked"] == [URL]                  # no second request

    web["asked"].clear()
    other = "https://img.example.com/can.png"
    web["pages"][URL] = _Response(302, {"location": other})
    web["pages"][other] = _Response(307, {"location": URL})
    assert fetch(URL) is None
    assert web["asked"] == [URL, other]


@FETCHERS
def test_a_chain_of_redirects_stops(web, fetch):
    hops = [f"https://cdn.example.com/hop/{n}" for n in range(refbin.MAX_REDIRECTS + 3)]
    for here, there in zip(hops, hops[1:]):
        web["pages"][here] = _Response(302, {"location": there})
    web["pages"][hops[-1]] = _Response(headers={"content-type": "image/png"}, body=_png())
    assert fetch(hops[0]) is None
    assert web["asked"] == hops[:refbin.MAX_REDIRECTS + 1]


@FETCHERS
@pytest.mark.parametrize("address", [
    "https://user:pw@cdn.example.com/can.png",      # credentials in the address
    "http://10.0.0.5/can.png",
    "http://169.254.169.254/latest/meta-data/",
    "file:///etc/passwd",
    "",
    None,
])
def test_an_address_that_is_not_public_http_is_refused_before_any_request(web, fetch, address):
    assert fetch(address) is None
    assert web["asked"] == []


@FETCHERS
@pytest.mark.parametrize("response", [
    _Response(404, {"content-type": "image/png"}, _png()),
    _Response(headers={"content-type": "text/html; charset=utf-8"}, body=b"<html>"),
    _Response(headers={"content-type": "application/json"}, body=b"{}"),
    _Response(headers={"content-type": "image/png"}, body=b""),
    _Response(headers={"content-type": "image/png", "content-length": "99999999"}, body=_png()),
    _Response(302, {}),                                  # a redirect to nowhere
], ids=["404", "a page", "json", "empty", "too big", "no location"])
def test_what_is_not_a_picture_returns_nothing_and_never_raises(web, fetch, response):
    web["pages"][URL] = response
    assert fetch(URL) is None


def test_an_unreachable_address_returns_nothing(web):
    assert imagery.fetch_image_bytes(URL) is None
    assert refbin.fetch(URL) is None


def test_bytes_handed_back_as_an_image_say_so_or_open_as_one(web):
    """`fetch_image_bytes` returns the bytes as they came, and a caller
    may write them to disk as a photo. An answer with no content type used
    to pass whatever it held."""
    web["pages"][URL] = _Response(headers={"content-type": "image/png"}, body=_png())
    assert imagery.fetch_image_bytes(URL) == _png()

    web["pages"][URL] = _Response(body=_png())            # says nothing, is a picture
    assert imagery.fetch_image_bytes(URL) == _png()

    web["pages"][URL] = _Response(body=SECRET)            # says nothing, is not one
    assert imagery.fetch_image_bytes(URL) is None

    web["pages"][URL] = _Response(headers={"content-type": "application/octet-stream"},
                                  body=_png())            # says it is something else
    assert imagery.fetch_image_bytes(URL) is None


def test_the_bin_keeps_only_what_decodes(web):
    web["pages"][URL] = _Response(body=SECRET)
    assert refbin.fetch(URL) is None
    assert not (refbin.REFS_DIR).exists()

    web["pages"][URL] = _Response(body=_png())
    stored = refbin.fetch(URL)
    assert stored and stored.startswith("/refs/") and refbin.resolve(stored).is_file()


def test_an_element_photo_address_cannot_be_bounced_into_the_network(web, tmp_path):
    """The door a signed-in person reaches it by: `photo_urls` on the
    element create routes -> api._photos_from_urls -> _photo_bytes, which
    wrote whatever came back under the element's folder."""
    from app import api

    folder = tmp_path / "characters" / "me"
    for target in ("http://169.254.169.254/latest/meta-data/", "http://10.0.0.5/secret.png"):
        web["asked"].clear()
        web["pages"][URL] = _Response(302, {"location": target})
        web["pages"][target] = _Response(body=SECRET)
        assert api._photos_from_urls(folder, [URL]) == []
        assert web["asked"] == [URL]
    assert not folder.exists()

    web["pages"][URL] = _Response(headers={"content-type": "image/png"}, body=_png())
    saved = api._photos_from_urls(folder, [URL])
    assert [p.read_bytes() for p in saved] == [_png()]

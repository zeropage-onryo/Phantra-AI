"""A pasted link becomes a reference frame (2026-10-01).

Mike's "focus on image first": a person pastes a Ghost product page, an
Instagram post, a Pinterest pin or a bare .jpg into the Guide and wants
the picture behind it on the contact sheet, ready to Keep.

THE RULE THAT SHAPES THIS MODULE: the model never handles a URL.
`guide_tools.check_args` refuses any tool argument carrying one, on
purpose -- the first live research run banked six fabricated Unsplash
addresses (imagesearch.py, 2026-09-02). So a link is read off the
PERSON'S OWN last message, server-side, by the route; it never passes
through a tool argument, and the model is told only that "N frames
from the link you pasted are on the sheet", never the address.

This is the ONE place scraping is right: a page the person chose, one
fetch, its own preview image (`og:image` and friends), no model, no
headless browser, no crawl. A vision model browsing for images was
considered and refused (10-50x the cost, blocked hosts, invented URLs).

What it reads, in order: a direct image URL is itself; an HTML page
gives `og:image` / `og:image:secure_url` / `twitter:image` /
`<link rel="image_src">`, then JSON-LD `Product.image` (string, list,
or ImageObject). Relative addresses resolve against the page. Four
frames per link at most.

Every fetch goes through the guards the bin already has:
`refbin.public_host` on the pasted host AND on every redirect hop
(a redirect into a private range is the classic SSRF bypass),
`refbin.FETCH_HEADERS`, `refbin.FETCH_TIMEOUT`, and a byte cap on the
HTML (read streamed, stopped at MAX_HTML_BYTES -- the tags live in
<head>, so a truncated page still gives up its image). Nothing here
raises: a refused host, a dead page, a page that renders client-side
or hides behind a login all come back as [] with a NOTE, because a
silent empty row in front of a person who pasted a link is exactly the
"quiet night" failure this repo keeps paying for.
"""
from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from typing import Callable, Optional
from urllib.parse import urljoin, urlparse

MAX_LINKS = 3                       # links read per message
MAX_PER_LINK = 4                    # frames offered per link
MAX_HTML_BYTES = 2 * 1024 * 1024    # of a page, streamed, then stop
MAX_REDIRECTS = 5
SOURCE = "link"                     # the lane label on every candidate

# A pasted address: http(s) only. Trailing punctuation a sentence leaves
# on a link ("see https://x.com/p/1.") is not part of it.
_LINK = re.compile(r"https?://[^\s<>\"'`]+", re.IGNORECASE)
_TRAIL = ".,;:!?)]}>'\""

# The no-image note, in the person's terms. Named once so the route,
# the model line and the tests all say the same thing.
BLOCKED_NOTE = "that page would not give up its image -- save the picture and drop it in"


def extract_links(text: str, limit: int = MAX_LINKS) -> list[str]:
    """The http(s) links in a message, in order, deduplicated, capped."""
    out: list[str] = []
    for match in _LINK.finditer(str(text or "")):
        url = match.group(0).rstrip(_TRAIL)
        # a closing paren that the link itself opened stays
        if url.count("(") > url.count(")") and match.group(0).endswith(")"):
            url += ")"
        parsed = urlparse(url)
        if parsed.scheme.lower() not in ("http", "https") or not parsed.hostname:
            continue
        if url not in out:
            out.append(url)
        if len(out) >= limit:
            break
    return out


def _page_headers() -> dict:
    from .refbin import FETCH_HEADERS
    return {**FETCH_HEADERS,
            "Accept": "text/html,application/xhtml+xml,image/*;q=0.9,*/*;q=0.8"}


def _host_ok(url: str) -> bool:
    from .refbin import public_host
    parsed = urlparse(url)
    return (parsed.scheme.lower() in ("http", "https") and bool(parsed.hostname)
            and public_host(parsed.hostname))


def _get(url: str) -> dict:
    """One guarded fetch -> {url, status, content_type, body, error}.

    Redirects are followed BY HAND so every hop's host is checked: a
    public page may 302 to a link-local metadata address, and requests'
    own redirect handling would follow it without asking. The body is
    streamed and cut at MAX_HTML_BYTES.
    """
    import requests

    from .refbin import FETCH_TIMEOUT

    current = url
    for _ in range(MAX_REDIRECTS + 1):
        if not _host_ok(current):
            return {"url": current, "status": 0, "content_type": "", "body": b"",
                    "error": "not a public address"}
        try:
            with requests.get(current, stream=True, timeout=FETCH_TIMEOUT,
                              headers=_page_headers(), allow_redirects=False) as resp:
                if resp.is_redirect or resp.status_code in (301, 302, 303, 307, 308):
                    target = resp.headers.get("location") or ""
                    if not target:
                        return {"url": current, "status": resp.status_code,
                                "content_type": "", "body": b"", "error": "redirect loop"}
                    current = urljoin(current, target)
                    continue
                kind = (resp.headers.get("content-type") or "").split(";")[0].strip().lower()
                chunks, total = [], 0
                for chunk in resp.iter_content(64 * 1024):
                    chunks.append(chunk)
                    total += len(chunk)
                    if total >= MAX_HTML_BYTES:
                        break
                return {"url": current, "status": resp.status_code, "content_type": kind,
                        "body": b"".join(chunks)[:MAX_HTML_BYTES], "error": ""}
        except Exception as e:
            return {"url": current, "status": 0, "content_type": "", "body": b"",
                    "error": f"fetch failed: {type(e).__name__}"}
    return {"url": current, "status": 0, "content_type": "", "body": b"",
            "error": "too many redirects"}


class _Head(HTMLParser):
    """The preview tags off a page: meta images, link image_src, the
    title, and every JSON-LD block, in document order."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.metas: list[tuple[str, str]] = []
        self.links: list[str] = []
        self.title = ""
        self.ld: list[str] = []
        self._in_title = False
        self._in_ld = False
        self._buf: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "meta":
            key = (a.get("property") or a.get("name") or "").strip().lower()
            if key and a.get("content"):
                self.metas.append((key, a["content"].strip()))
        elif tag == "link":
            rel = (a.get("rel") or "").lower().split()
            if "image_src" in rel and a.get("href"):
                self.links.append(a["href"].strip())
        elif tag == "title" and not self.title:
            self._in_title, self._buf = True, []
        elif tag == "script" and (a.get("type") or "").lower().strip() == "application/ld+json":
            self._in_ld, self._buf = True, []

    def handle_endtag(self, tag):
        if tag == "title" and self._in_title:
            self.title = " ".join("".join(self._buf).split())[:200]
            self._in_title = False
        elif tag == "script" and self._in_ld:
            self.ld.append("".join(self._buf))
            self._in_ld = False

    def handle_data(self, data):
        if self._in_title or self._in_ld:
            self._buf.append(data)


def _ld_images(block: str) -> list[str]:
    """Image addresses off one JSON-LD block: any Product (or a node
    that simply carries `image`), string / list / ImageObject."""
    try:
        data = json.loads(block)
    except Exception:
        return []
    nodes: list = []
    stack = [data]
    while stack:
        node = stack.pop(0)
        if isinstance(node, list):
            stack.extend(node)
        elif isinstance(node, dict):
            nodes.append(node)
            for key in ("@graph", "mainEntity", "offers", "hasVariant"):
                if key in node:
                    stack.append(node[key])
    out: list[str] = []

    def take(value):
        if isinstance(value, str):
            out.append(value)
        elif isinstance(value, list):
            for v in value:
                take(v)
        elif isinstance(value, dict):
            take(value.get("contentUrl") or value.get("url") or "")

    # THE PAGE'S OWN product only: the first Product node carrying an
    # image, plus its own variants. drinkghost.com (live, 2026-10-01)
    # follows the page's ProductGroup with a second one listing every
    # flavour, and "every flavour" is not what the person pasted.
    products = [n for n in nodes if "product" in str(n.get("@type") or "").lower()]
    for node in products or nodes:
        if "image" not in node:
            continue
        take(node["image"])
        for variant in (node.get("hasVariant") or []) if isinstance(node.get("hasVariant"), list) else []:
            if isinstance(variant, dict) and "image" in variant:
                take(variant["image"])
        break
    return out


def parse_images(html: str, base_url: str) -> tuple[list[str], str]:
    """(image urls in preference order, page title) off an HTML page."""
    head = _Head()
    try:
        head.feed(html)
    except Exception:
        pass
    found: list[str] = []
    for key in ("og:image", "og:image:secure_url", "og:image:url",
                "twitter:image", "twitter:image:src"):
        found += [v for k, v in head.metas if k == key]
    found += head.links
    for block in head.ld:
        # the first JSON-LD block that names a product with a picture is
        # the page's own; later blocks are the shop's other products
        ld = _ld_images(block)
        if ld:
            found += ld
            break
    title = next((v for k, v in head.metas if k == "og:title"), "") or head.title
    out: list[str] = []
    seen: dict[str, int] = {}
    for raw in found:
        raw = (raw or "").strip()
        if not raw or _bare_scheme(raw):
            continue
        url = urljoin(base_url, raw)
        parsed = urlparse(url)
        if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc:
            # "https:/cdn.example/x.jpg" (one slash -- seen live on
            # drinkghost.com, 2026-10-01) parses with a scheme and no host
            continue
        if parsed.path.lower().endswith(".svg"):
            continue                      # not a photograph, and nothing here can look at one
        # One file, whatever the scheme: Shopify writes og:image as http
        # and og:image:secure_url as https for the SAME logo, which cost
        # a slot of four (Ghost, 2026-10-01). https wins.
        url = _usable_size(url)
        parsed = urlparse(url)
        key = parsed._replace(scheme="").geturl().lstrip("/")
        if key in seen:
            if parsed.scheme == "https":
                out[seen[key]] = url
            continue
        seen[key] = len(out)
        out.append(url)
    # The site's logo and a "no image" placeholder are what many shops put
    # in og:image; the product photos come after, in the JSON-LD. Neither
    # is dropped (the look rejects a logo with the reason on the card),
    # but they go LAST, so the real frames take the slots.
    out.sort(key=_looks_like_chrome)
    return out, " ".join(str(title or "").split())[:200]


# --- what the page says about the product ------------------------------------------
#
# invideo reads a pasted product page into the brief; here the page gave up
# its pictures and nothing else, so the brain wrote "the can" about a
# product whose name, flavour and size were on the page (2026-10-11, item 9
# of docs/tasks/task-studio-agent.md).
#
# Only what the page states about ITSELF in a structured place is read:
# its first JSON-LD Product and its preview tags. Never the body text -- a
# page is untrusted, and a paragraph of it handed to a model is a place to
# write instructions. Every value is flattened to plain words, stripped of
# markup and of any address, and cut short.

FACT_LIMITS = {"name": 120, "brand": 60, "price": 40, "color": 60, "material": 60,
               "size": 60, "category": 80, "description": 500}
FACT_ORDER = ("name", "brand", "price", "color", "material", "size", "category", "description")
_TAG = re.compile(r"<[^>]{0,400}>")
_ADDRESS = re.compile(r"(?i)\b(?:https?://|www\.)\S+|\b[\w.+-]+@[\w-]+\.[\w.-]+")


def _plain(value, limit: int) -> str:
    """One fact as plain words: no markup, no address, one line, cut at a
    word. "" for anything that is not text or a number."""
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        return ""
    import html as _html
    text = _html.unescape(_TAG.sub(" ", str(value)))
    text = " ".join(_ADDRESS.sub(" ", text).split())
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0].rstrip(" ,;:-") + "…"
    return text


def _named(value) -> str:
    """A JSON-LD value that may be a string or a {name} node."""
    if isinstance(value, dict):
        value = value.get("name")
    if isinstance(value, list):
        value = next((v for v in value if v), None)
        return _named(value)
    return value if isinstance(value, (str, int, float)) and not isinstance(value, bool) else ""


def _price(offers) -> str:
    """"2.99 USD" off a Product's offers (an Offer, a list of them, or an
    AggregateOffer), or "". The page's own number, never converted."""
    if isinstance(offers, list):
        offers = next((o for o in offers if isinstance(o, dict)), None)
    if not isinstance(offers, dict):
        return ""
    amount = offers.get("price") or offers.get("lowPrice")
    if isinstance(amount, dict):
        amount = amount.get("price")
    if amount in (None, "") or isinstance(amount, bool):
        return ""
    currency = offers.get("priceCurrency") or ""
    return f"{amount} {currency}".strip()


def _ld_product(blocks: list) -> dict:
    """The page's own Product node, by the rule `_ld_images` keeps: the
    FIRST one in document order (later ones are the shop's other things)."""
    for block in blocks:
        try:
            data = json.loads(block)
        except Exception:
            continue
        stack = [data]
        while stack:
            node = stack.pop(0)
            if isinstance(node, list):
                stack = list(node) + stack
            elif isinstance(node, dict):
                if "product" in str(node.get("@type") or "").lower():
                    return node
                for key in ("@graph", "mainEntity"):
                    if key in node:
                        stack.insert(0, node[key])
    return {}


def parse_facts(html: str) -> dict:
    """{name, brand, price, color, material, size, category, description}
    as the page states them -- only the keys it actually has, each plain
    and bounded (FACT_LIMITS). {} for a page that says nothing structured,
    which is most pages that are not a product's."""
    head = _Head()
    try:
        head.feed(html)
    except Exception:
        pass
    meta = {}
    for key, value in head.metas:
        meta.setdefault(key, value)
    product = _ld_product(head.ld)
    raw = {
        "name": _named(product.get("name")) or meta.get("og:title") or "",
        "brand": _named(product.get("brand")) or meta.get("product:brand") or "",
        "price": _price(product.get("offers")) or " ".join(
            v for v in (meta.get("product:price:amount"), meta.get("product:price:currency")) if v),
        "color": _named(product.get("color")),
        "material": _named(product.get("material")),
        "size": _named(product.get("size")),
        "category": _named(product.get("category")),
        "description": (_named(product.get("description")) or meta.get("og:description")
                        or meta.get("description") or ""),
    }
    # a page with no Product node and no product tags is an article or a
    # home page: its title and blurb are not "facts about a product"
    is_product = bool(product) or any(k.startswith("product:") for k in meta) \
        or (meta.get("og:type") or "").lower().startswith("product")
    if not is_product:
        return {}
    facts = {}
    for key in FACT_ORDER:
        text = _plain(raw.get(key), FACT_LIMITS[key])
        if text:
            facts[key] = text
    return facts


_CHROME = ("logo", "no-image", "noimage", "placeholder", "sprite", "favicon", "icon")


def _usable_size(url: str) -> str:
    """Shopify's CDN sizes an image by its `width=` query parameter
    (documented), and a shop's JSON-LD hands out the 300px thumbnail.
    On that CDN only, ask for a reference-sized one; the file is the
    same, so this invents no address. Any other host is left alone."""
    from urllib.parse import parse_qsl, urlencode

    parsed = urlparse(url)
    if "/cdn/shop/" not in parsed.path or not parsed.query:
        return url
    params = parse_qsl(parsed.query, keep_blank_values=True)
    changed = False
    for i, (k, v) in enumerate(params):
        if k == "width" and v.isdigit() and int(v) < SHOPIFY_WIDTH:
            params[i] = (k, str(SHOPIFY_WIDTH))
            changed = True
    return parsed._replace(query=urlencode(params)).geturl() if changed else url


SHOPIFY_WIDTH = 1200


def _bare_scheme(raw: str) -> bool:
    """"https:/cdn.example/x.jpg" or "mailto:x" -- a scheme with no "//".
    urljoin would glue the first onto the PAGE's host (one slash, seen
    live on drinkghost.com 2026-10-01) and offer a frame that 404s."""
    head = raw.split("/", 1)[0]
    return ":" in head and "://" not in raw


def _looks_like_chrome(url: str) -> bool:
    name = (urlparse(url).path.rsplit("/", 1)[-1] or "").lower()
    return any(word in name for word in _CHROME)


def _login_wall(url: str) -> bool:
    path = (urlparse(url).path or "").lower()
    return "login" in path or "signin" in path or "sign-in" in path


def read_link(url: str, *, get: Optional[Callable[[str], dict]] = None) -> dict:
    """One pasted link -> {"url", "title", "images": [candidate...], "note",
    "facts"} -- `facts` is what the page states about its own product
    (`parse_facts`), {} when it states nothing structured.

    `images` are imagesearch-shaped candidates (`source` = "link",
    `source_url` = the page the person pasted -- the provenance rule:
    every reference traceable to where it came from). Never raises;
    nothing found is [] with a `note` that says why.
    """
    url = str(url or "").strip()
    if get is None:
        get = _get
    host = urlparse(url).hostname or ""
    result = {"url": url, "title": host, "images": [], "note": "", "facts": {}}
    if not _host_ok(url):
        result["note"] = "not a public web address"
        return result
    try:
        page = get(url) or {}
    except Exception as e:                       # the injected fetcher
        page = {"error": f"fetch failed: {type(e).__name__}"}
    status = int(page.get("status") or 0)
    kind = str(page.get("content_type") or "").lower()
    body = page.get("body") or b""
    final = str(page.get("url") or url)
    if page.get("error") and not body:
        result["note"] = f"{BLOCKED_NOTE} ({page['error']})"
        return result
    if status and status >= 400:
        result["note"] = f"{BLOCKED_NOTE} (HTTP {status})"
        return result
    if kind.startswith("image/"):
        # a direct picture: the link is the frame
        result["images"] = [_candidate(final, url, host, host)]
        result["title"] = host
        return result
    if _login_wall(final):
        result["note"] = f"{BLOCKED_NOTE} (it wants a sign-in)"
        return result
    if isinstance(body, bytes):
        text = body[:MAX_HTML_BYTES].decode("utf-8", "replace")
    else:
        text = str(body)[:MAX_HTML_BYTES]
    try:
        images, title = parse_images(text, final)
    except Exception:                        # a page is untrusted input; never a traceback
        images, title = [], ""
    try:
        result["facts"] = parse_facts(text)
    except Exception:
        result["facts"] = {}
    title = title or host
    result["title"] = title
    result["images"] = [_candidate(image, url, title, host) for image in images[:MAX_PER_LINK]]
    if not result["images"]:
        result["note"] = BLOCKED_NOTE
    return result


def _candidate(image_url: str, page_url: str, title: str, host: str) -> dict:
    return {"source": SOURCE, "image_url": image_url, "source_url": page_url,
            "title": title[:200], "credit": host}


def images_from_link(url: str, **kwargs) -> list[dict]:
    """The candidates behind one link, or [] (see `read_link` for why)."""
    return read_link(url, **kwargs)["images"]

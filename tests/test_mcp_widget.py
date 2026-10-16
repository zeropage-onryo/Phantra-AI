"""src/mcp_widget.py: the ChatGPT card. Which tools carry it, where, and what its
resource may load. (The card's drawing was run in node against each result
shape when it was written; what is pinned here is the contract with the host.)"""
import asyncio

from src import mcp_server, mcp_widget


def _tools(listed):
    server = mcp_server.build_server(listed=listed)
    return {t.name: (t.meta or {}) for t in asyncio.run(server.list_tools())}


def test_the_render_listing_gives_the_card_to_quote_and_generate_image():
    tools = _tools(True)
    uri = mcp_widget.view_uri()
    for name in ("quote", "generate_image"):
        assert tools[name]["ui"]["resourceUri"] == uri
        assert tools[name]["openai/outputTemplate"] == uri
    assert tools["projects"] == {}                    # everything else is as it was


def test_the_claude_listing_carries_no_card_and_no_resource():
    server = mcp_server.build_server(listed="claude")
    assert all(not (t.meta or {}).get("ui") for t in asyncio.run(server.list_tools()))
    assert asyncio.run(server.list_resources()) == []


def test_the_studio_surface_carries_no_card():
    server = mcp_server.build_server(local_files=False)
    assert all("ui" not in (t.meta or {}) for t in asyncio.run(server.list_tools()))
    assert asyncio.run(server.list_resources()) == []


def test_the_resource_is_an_mcp_app_that_may_load_only_our_media_host():
    server = mcp_server.build_server(listed=True)
    (resource,) = asyncio.run(server.list_resources())
    assert str(resource.uri) == mcp_widget.view_uri()
    assert resource.mime_type == "text/html;profile=mcp-app"
    ui = resource.meta["ui"]
    assert ui["csp"] == {"resourceDomains": ["https://media.phantra.ai"], "connectDomains": []}
    (content,) = asyncio.run(server.read_resource(str(resource.uri)))
    assert content.content == mcp_widget.VIEW_HTML


def test_the_media_host_follows_the_bucket_and_is_an_origin_only(monkeypatch):
    monkeypatch.setenv("R2_PUBLIC_BASE_URL", "https://cdn.example.org/some/path/")
    assert mcp_widget.media_host() == "https://cdn.example.org"
    monkeypatch.setenv("R2_PUBLIC_BASE_URL", "http://insecure.example.org")
    assert mcp_widget.media_host() == mcp_widget.DEFAULT_MEDIA_HOST
    monkeypatch.delenv("R2_PUBLIC_BASE_URL")
    assert mcp_widget.media_host() == mcp_widget.DEFAULT_MEDIA_HOST


def test_the_uri_is_a_hash_of_the_view_so_a_host_never_serves_a_stale_copy(monkeypatch):
    before = mcp_widget.view_uri()
    monkeypatch.setattr(mcp_widget, "VIEW_HTML", mcp_widget.VIEW_HTML + "<!-- changed -->")
    assert mcp_widget.view_uri() != before


def test_the_view_loads_nothing_from_anywhere_and_has_no_buttons():
    html = mcp_widget.VIEW_HTML
    assert "<script src" not in html and "@import" not in html and "<link" not in html
    # it reads a result; it never calls a tool, so it cannot spend or approve anything
    assert "<button" not in html and "tools/call" not in html and "ui/message" not in html
    assert "innerHTML" not in html                    # every value goes in as text


def test_the_card_fields_are_a_title_and_a_minted_preview_and_nothing_else():
    fields = mcp_server._card_fields(
        {"title": "  Tonal   One push-in  "},
        {"reference_image": "https://media.phantra.ai/m/5/renders/nano/c408-x.png"}, 5)
    assert fields["title"] == "Tonal One push-in"
    assert fields["preview_url"].startswith("https://")
    assert mcp_server._card_fields({"title": ""}, {}, 5) == {}

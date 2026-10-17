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
    for name in ("project", "scene"):                 # the project and scene layouts
        assert tools[name]["ui"]["resourceUri"] == uri
    assert tools["library"] == {} and tools["projects"] == {}    # everything else is as it was


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


def test_the_view_loads_nothing_from_anywhere_and_never_calls_a_tool():
    html = mcp_widget.VIEW_HTML
    assert "<script src" not in html and "@import" not in html and "<link" not in html
    # it reads a result and never calls a tool, so it cannot spend or approve anything. Its two
    # buttons open the file and send a chat message in words; the model still quotes and waits.
    assert "tools/call" not in html and "requestCheckout" not in html
    assert html.count('el("button"') == 2
    assert "--accent: #FEE32D" in html                  # the owl's yellow, on buttons and the dot
    assert "innerHTML" not in html                    # every value goes in as text


def test_the_card_fields_are_a_title_and_a_minted_preview_and_nothing_else():
    fields = mcp_server._card_fields(
        {"title": "  Tonal   One push-in  "},
        {"reference_image": "https://media.phantra.ai/m/5/renders/nano/c408-x.png"}, 5)
    assert fields["title"] == "Tonal One push-in"
    assert fields["preview_url"].startswith("https://")
    assert mcp_server._card_fields({"title": ""}, {}, 5) == {}


def test_the_card_reads_the_json_text_when_a_plain_dict_has_no_structured_content():
    """Found live: a tool annotated `-> dict` sends its answer as JSON text and no
    structuredContent, so a card reading only the latter drew nothing (a 4px frame)."""
    import asyncio

    from mcp.server.mcpserver import MCPServer
    server = MCPServer("t")

    @server.tool(name="plain")
    def plain() -> dict:
        return {"scene_id": 1, "credits_needed": 5}

    result = asyncio.run(server.call_tool("plain", {}))
    assert result.structured_content is None
    assert 'JSON.parse(blocks[i].text)' in mcp_widget.VIEW_HTML      # the card's fallback
    assert '"credits_needed": 5' in result.content[0].text


def test_the_price_notes_tell_the_model_a_card_is_already_showing_the_numbers():
    assert "already on screen" in mcp_server.CARD_NOTE
    assert "do not list the numbers again" in mcp_server.CARD_NOTE


def test_the_card_has_a_compact_row_for_prices_and_a_full_image_only_for_a_finished_result():
    html = mcp_widget.VIEW_HTML
    assert 'el("div", "compact")' in html and 'el("p", "price"' in html
    assert "<table" not in html and 'el("table"' not in html     # the table is gone


def test_the_card_has_project_and_scene_layouts_and_every_image_goes_through_the_checked_address():
    html = mcp_widget.VIEW_HTML
    assert "function renderProject" in html and "function renderScene" in html
    assert "safeUrl(url)" in html                        # an image address must be https
    assert "innerHTML" not in html


def test_results_with_image_links_tell_the_model_not_to_embed_them(pg):
    """ChatGPT draws a gray placeholder for an image the model writes into its reply, so
    the render listing's list-type tools carry a note saying so, and the claude one does not."""
    import json

    from src import accounts, entities, ledger, preprod, projects

    for init in (preprod.init, entities.init, projects.init, ledger.init):
        init(pg)
    account = accounts.seed("alice@example.com", dsn=pg)["accounts"][0]

    def answer(listed, tool):
        server = mcp_server.build_server(dsn=pg, listed=listed, account_id=account)
        result = asyncio.run(server.call_tool(tool, {}))
        return json.loads(result.content[0].text)

    assert answer(True, "projects")["display_note"] == mcp_widget.NOTE_TOOLS["projects"]
    assert "display_note" not in answer("claude", "projects")
    assert "display_note" not in answer(True, "balance")          # a tool with no image links
    assert "http" not in mcp_widget.NOTE_ON_CARD + mcp_widget.NOTE_NO_CARD
    assert "$" not in mcp_widget.NOTE_ON_CARD + mcp_widget.NOTE_NO_CARD

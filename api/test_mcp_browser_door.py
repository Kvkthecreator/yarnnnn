"""Gate: a browser at the connector URL gets a noindex page; an MCP client still gets 401.

Search Console (2026-09-24) flagged `https://mcp.yarnnn.com/` as "Blocked due to
unauthorized request (401)" — /developers links it, so crawlers and people land
on the protocol endpoint. `mcp_server/browser_door.py` answers only a browser's
page load; this gate drives the REAL app (the SDK's streamable app wrapped the
way `__main__` wraps it) so a request that should reach the SDK is proven to.

    cd api && python3 -m pytest test_mcp_browser_door.py -q
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test")

from starlette.testclient import TestClient  # noqa: E402

from mcp_server.browser_door import BrowserDoorMiddleware, is_browser_page_load  # noqa: E402
from mcp_server.rate_limit import AuthRateLimitMiddleware  # noqa: E402
from mcp_server.server import mcp  # noqa: E402

BROWSER_ACCEPT = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"


@pytest.fixture(scope="module")
def client():
    app = BrowserDoorMiddleware(AuthRateLimitMiddleware(mcp.streamable_http_app()))
    with TestClient(app) as c:
        yield c


def test_browser_gets_noindex_page(client):
    r = client.get("/", headers={"Accept": BROWSER_ACCEPT})
    assert r.status_code == 200
    assert r.headers["x-robots-tag"] == "noindex"
    assert '<meta name="robots" content="noindex">' in r.text
    assert "https://mcp.yarnnn.com" in r.text


def test_head_has_no_body(client):
    r = client.head("/", headers={"Accept": BROWSER_ACCEPT})
    assert r.status_code == 200
    assert r.content == b""


def test_mcp_post_still_401(client):
    r = client.post(
        "/",
        headers={"Accept": "application/json, text/event-stream", "Content-Type": "application/json"},
        json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
    )
    assert r.status_code == 401
    assert "resource_metadata" in r.headers.get("www-authenticate", "")


def test_mcp_sse_get_still_401(client):
    r = client.get("/", headers={"Accept": "text/event-stream"})
    assert r.status_code == 401


def test_bearer_carrying_browser_reaches_protocol():
    # Driving it would reach the token verifier (a Supabase lookup), so the
    # predicate is the honest seam: a credential always goes to the protocol.
    scope = {"type": "http", "path": "/", "method": "GET", "headers": [
        (b"accept", BROWSER_ACCEPT.encode()), (b"authorization", b"Bearer nope"),
    ]}
    assert not is_browser_page_load(scope)


def test_other_paths_untouched(client):
    r = client.get("/.well-known/oauth-authorization-server", headers={"Accept": BROWSER_ACCEPT})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")


@pytest.mark.parametrize("accept", ["*/*", "application/json", "", "text/html, text/event-stream"])
def test_non_browser_accepts_pass_through(accept):
    scope = {"type": "http", "path": "/", "method": "GET", "headers": [(b"accept", accept.encode())]}
    assert not is_browser_page_load(scope)

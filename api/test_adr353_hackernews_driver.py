"""ADR-353 §17 — Hacker News driver (NO_AUTH, read-only perceive connector).

HN executes through the Composio driver with NO credential (public read API). The
load-bearing properties:
  1. NO_AUTH — execute() requires no token for hackernews; the request omits
     custom_auth_params entirely.
  2. verb → live Composio slug (HACKERNEWS_SEARCH_POSTS / GET_ITEM_WITH_ID).
  3. result adapters match the LIVE shapes (confirmed 2026-06-22): search →
     data.response_data.hits (Algolia); get_item → data.response_data (the item,
     with children = comments).
  4. read-only: no write capability, not in the external-write family.
  5. always-available capability (platform_connection_requirement = None);
     surfaces without a platform_connection (folded into satisfied_providers).

Run: api/venv/bin/python -m pytest api/test_adr353_hackernews_driver.py -q
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

API_DIR = Path(__file__).resolve().parent
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("COMPOSIO_API_KEY", "test-key")
    yield


def _mock_post(monkeypatch, *, body=None):
    captured: list[dict] = []

    class _Resp:
        status_code = 200
        text = "err"

        def json(self):
            return body

    class _Client:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, headers=None, json=None):
            captured.append({"url": url, "body": json})
            return _Resp()

    import services.composio_driver as driver
    monkeypatch.setattr(driver.httpx, "AsyncClient", _Client)
    return captured


# --- NO_AUTH: no token required, no custom_auth_params sent --------------------

@pytest.mark.asyncio
async def test_search_no_token_required_and_no_auth_params(monkeypatch):
    from services import composio_driver
    captured = _mock_post(monkeypatch, body={
        "successful": True,
        "data": {"response_data": {"hits": [
            {"objectID": "1", "title": "T", "author": "a", "points": 5, "num_comments": 3,
             "url": "https://x", "story_text": "body"},
        ]}},
    })
    # token="" must be accepted for hackernews (NO_AUTH).
    out = await composio_driver.execute(
        "hackernews", "search_posts", {"query": "agents"}, token="", user_id="u1",
    )
    assert out["success"] is True
    assert captured[0]["url"].endswith("/HACKERNEWS_SEARCH_POSTS")
    # NO custom_auth_params in the body (the NO_AUTH property).
    assert "custom_auth_params" not in captured[0]["body"]
    assert captured[0]["body"]["arguments"] == {"query": "agents"}


@pytest.mark.asyncio
async def test_search_result_adapter_live_shape(monkeypatch):
    from services import composio_driver
    _mock_post(monkeypatch, body={
        "successful": True,
        "data": {"response_data": {"hits": [
            {"objectID": "44", "title": "LLM Agents", "author": "dan", "points": 285,
             "num_comments": 176, "url": "https://news.ycombinator.com/item?id=44"},
            {"not_a": "dict-skipped"} if False else {"objectID": "45", "title": "X", "author": "z"},
        ]}},
    })
    out = await composio_driver.execute(
        "hackernews", "search_posts", {"query": "agents"}, token="", user_id="u1",
    )
    assert out["result"]["count"] == 2
    first = out["result"]["posts"][0]
    assert set(first.keys()) == {"id", "title", "author", "points", "num_comments", "url", "text"}
    assert first["id"] == "44"
    assert first["points"] == 285
    # synthesized url when absent
    assert out["result"]["posts"][1]["url"] == "https://news.ycombinator.com/item?id=45"


@pytest.mark.asyncio
async def test_get_item_live_shape(monkeypatch):
    """get_item: data.response_data IS the item; children are comments."""
    from services import composio_driver
    _mock_post(monkeypatch, body={
        "successful": True,
        "data": {"response_data": {
            "id": 44, "author": "op", "title": "A Story", "points": 100,
            "total_children_count": 42,
            "children": [
                {"author": "c1", "text": "good point"},
                {"author": "c2", "text": ""},  # empty skipped
                "not-a-dict",                    # skipped
            ],
        }},
    })
    out = await composio_driver.execute(
        "hackernews", "get_item", {"item_id": "44"}, token="", user_id="u1",
    )
    assert out["success"] is True
    res = out["result"]
    assert res["author"] == "op"
    assert res["num_comments"] == 42          # from total_children_count, not len()
    assert len(res["comments"]) == 1
    assert res["comments"][0] == {"author": "c1", "text": "good point"}


@pytest.mark.asyncio
async def test_get_item_maps_item_id(monkeypatch):
    from services import composio_driver
    captured = _mock_post(monkeypatch, body={"successful": True, "data": {"response_data": {"id": 1, "children": []}}})
    await composio_driver.execute("hackernews", "get_item", {"item_id": "999"}, token="", user_id="u1")
    assert captured[0]["url"].endswith("/HACKERNEWS_GET_ITEM_WITH_ID")
    assert captured[0]["body"]["arguments"] == {"item_id": "999"}


@pytest.mark.asyncio
async def test_defensive_non_dict_data(monkeypatch):
    from services import composio_driver
    _mock_post(monkeypatch, body={"successful": True, "data": "weird"})
    out = await composio_driver.execute("hackernews", "search_posts", {"query": "x"}, token="", user_id="u1")
    assert out["success"] is True
    assert out["result"]["posts"] == []
    assert out["result"]["_unparsed"] == "weird"


# --- allowlist + capability wiring -------------------------------------------

def test_hackernews_in_default_allowlist(monkeypatch):
    from services import composio_driver
    monkeypatch.setenv("COMPOSIO_DRIVER_ENABLED", "true")
    monkeypatch.delenv("COMPOSIO_PROVIDER_ALLOWLIST", raising=False)
    assert composio_driver.driver_enabled_for("hackernews") is True


def test_hackernews_is_no_auth_provider():
    from services.composio_driver import _NO_AUTH_PROVIDERS
    assert "hackernews" in _NO_AUTH_PROVIDERS


def test_hackernews_read_only_not_external_write():
    from services.platform_tools import is_consequential_platform_tool
    # HN has no write tool; the read tools are not consequential.
    assert is_consequential_platform_tool("platform_hackernews_search_posts") is False
    assert is_consequential_platform_tool("platform_hackernews_get_item") is False


def test_hackernews_capability_no_write():
    from services.platform_tools import PLATFORM_TOOLS_BY_CAPABILITY, CAPABILITY_PROVIDER_MAP
    assert PLATFORM_TOOLS_BY_CAPABILITY["read_hackernews"] == [
        "platform_hackernews_search_posts", "platform_hackernews_get_item",
    ]
    assert "write_hackernews" not in PLATFORM_TOOLS_BY_CAPABILITY
    assert CAPABILITY_PROVIDER_MAP["read_hackernews"] == "hackernews"


def test_hackernews_kernel_capability_no_connection_required():
    from services.orchestration import CAPABILITIES
    assert CAPABILITIES["read_hackernews"]["feeds"] == "context"
    # NO_AUTH ⇒ always available (no platform_connection_requirement).
    assert CAPABILITIES["read_hackernews"]["platform_connection_requirement"] is None

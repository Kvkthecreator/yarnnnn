"""ADR-353 §15a — Reddit driver path (publish + perceive, Composio-only backend).

Reddit executes ENTIRELY through the Composio driver (no first-party client).
Asserts the four things a new platform must get right (the §3a pattern):
  1. verb → live Composio action slug
  2. payload adapter (YARNNN tool_input → Composio arguments, incl. kind/flair/article)
  3. result adapter (Composio data → stable YARNNN shape: post_id/url, comments/count)
  4. platform-level success check — Reddit's data.json.errors is the silent-success
     trap (successful:true with a buried error), the Slack data.ok analogue.
Plus: reddit is in the default allowlist (so it actually routes) and capital stays excluded.

Run: api/venv/bin/python -m pytest api/test_adr353_reddit_driver.py -q
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


def _mock_post(monkeypatch, *, status_code=200, body=None):
    captured: list[dict] = []

    class _Resp:
        def __init__(self):
            self.status_code = status_code
            self.text = "err"

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


# --- slug + payload mapping ---------------------------------------------------

@pytest.mark.asyncio
async def test_submit_post_slug_and_arguments(monkeypatch):
    from services import composio_driver
    captured = _mock_post(monkeypatch, body={
        "successful": True, "data": {"json": {"data": {"name": "t3_abc", "url": "https://reddit.com/x"}}},
    })
    out = await composio_driver.execute(
        "reddit", "submit_post",
        {"subreddit": "startups", "title": "Hi", "text": "Body"},
        token="reddit-tok", user_id="u1",
    )
    assert out["success"] is True
    assert captured[0]["url"].endswith("/REDDIT_CREATE_REDDIT_POST")
    args = captured[0]["body"]["arguments"]
    assert args["subreddit"] == "startups"
    assert args["title"] == "Hi"
    assert args["text"] == "Body"
    assert args["kind"] == "self"        # text post
    assert args["flair_id"] == ""        # required field, defaulted
    # result adapter re-derives the post id for the perceive loop
    assert out["result"]["post_id"] == "t3_abc"
    assert out["result"]["url"] == "https://reddit.com/x"


@pytest.mark.asyncio
async def test_get_post_comments_maps_post_id_to_article(monkeypatch):
    from services import composio_driver
    captured = _mock_post(monkeypatch, body={
        "successful": True,
        "data": {"comments": [
            {"data": {"author": "alice", "body": "great point", "score": 7}},
            {"data": {"author": "bob", "body": "", "score": 1}},  # empty dropped
        ]},
    })
    out = await composio_driver.execute(
        "reddit", "get_post_comments", {"post_id": "t3_abc"},
        token="reddit-tok", user_id="u1",
    )
    assert out["success"] is True
    assert captured[0]["url"].endswith("/REDDIT_RETRIEVE_POST_COMMENTS")
    assert captured[0]["body"]["arguments"] == {"article": "t3_abc"}
    assert out["result"]["count"] == 1
    assert out["result"]["comments"][0] == {"author": "alice", "body": "great point", "score": 7}


# --- the silent-success trap: Reddit data.json.errors ------------------------

@pytest.mark.asyncio
async def test_reddit_errors_in_body_no_silent_success(monkeypatch):
    """successful:true but data.json.errors non-empty (e.g. SUBREDDIT_NOEXIST) —
    must surface as failure, never success."""
    from services import composio_driver
    _mock_post(monkeypatch, body={
        "successful": True, "error": None,
        "data": {"json": {"errors": [["SUBREDDIT_NOEXIST", "that subreddit doesn't exist", "sr"]]}},
    })
    out = await composio_driver.execute(
        "reddit", "submit_post",
        {"subreddit": "nope", "title": "Hi", "text": "Body"},
        token="reddit-tok", user_id="u1",
    )
    assert out["success"] is False
    assert out["result"] is None
    assert "SUBREDDIT_NOEXIST" in out["error"]


@pytest.mark.asyncio
async def test_missing_required_field_no_silent_success(monkeypatch):
    from services import composio_driver
    _mock_post(monkeypatch, body={"successful": True, "data": {}})
    out = await composio_driver.execute(
        "reddit", "submit_post", {"subreddit": "startups", "title": "Hi"},  # no text
        token="reddit-tok", user_id="u1",
    )
    assert out["success"] is False
    assert "text" in out["error"].lower()


# --- allowlist routing --------------------------------------------------------

def test_reddit_in_default_allowlist(monkeypatch):
    from services import composio_driver
    monkeypatch.setenv("COMPOSIO_DRIVER_ENABLED", "true")
    monkeypatch.delenv("COMPOSIO_PROVIDER_ALLOWLIST", raising=False)  # use default
    assert composio_driver.driver_enabled_for("reddit") is True
    assert composio_driver.driver_enabled_for("slack") is True


def test_reddit_off_when_master_switch_off(monkeypatch):
    from services import composio_driver
    monkeypatch.delenv("COMPOSIO_DRIVER_ENABLED", raising=False)
    assert composio_driver.driver_enabled_for("reddit") is False


def test_capital_still_excluded(monkeypatch):
    from services import composio_driver
    monkeypatch.setenv("COMPOSIO_DRIVER_ENABLED", "true")
    monkeypatch.setenv("COMPOSIO_PROVIDER_ALLOWLIST", "reddit,trading,commerce")
    assert composio_driver.driver_enabled_for("trading") is False
    assert composio_driver.driver_enabled_for("commerce") is False
    assert composio_driver.driver_enabled_for("reddit") is True


# --- capability wiring (the gate classifies the post as external-write) -------

def test_reddit_post_is_external_write_family():
    from services.platform_tools import consequential_platform_family, is_consequential_platform_tool
    assert consequential_platform_family("platform_reddit_submit_post") == "external-write"
    assert is_consequential_platform_tool("platform_reddit_submit_post") is True
    # the perceive read is NOT consequential
    assert is_consequential_platform_tool("platform_reddit_get_post_comments") is False


def test_reddit_capabilities_registered():
    from services.platform_tools import PLATFORM_TOOLS_BY_CAPABILITY, CAPABILITY_PROVIDER_MAP
    assert PLATFORM_TOOLS_BY_CAPABILITY["write_reddit"] == ["platform_reddit_submit_post"]
    assert PLATFORM_TOOLS_BY_CAPABILITY["read_reddit"] == ["platform_reddit_get_post_comments"]
    assert CAPABILITY_PROVIDER_MAP["write_reddit"] == "reddit"
    assert CAPABILITY_PROVIDER_MAP["read_reddit"] == "reddit"


def test_reddit_kernel_capabilities_present():
    from services.orchestration import CAPABILITIES
    assert CAPABILITIES["write_reddit"]["feeds"] == "action"
    assert CAPABILITIES["read_reddit"]["feeds"] == "context"
    assert CAPABILITIES["write_reddit"]["platform_connection_requirement"]["platform"] == "reddit"

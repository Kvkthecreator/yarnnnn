"""ADR-353 §12.2 + Pitfall #4 — parity + error-shape between first-party and
the Composio driver.

Two properties under test:

  PARITY — identical YARNNN inputs through first-party (_handle_slack_tool) vs
  the Composio driver must yield the SAME result-dict KEYS, so every caller of
  handle_platform_tool is byte-compatible regardless of which driver ran. The
  underlying Slack `data` is the same chat.postMessage / conversations.* shape,
  so the driver's result adapter re-derives exactly the first-party fields.

  NO SILENT SUCCESS (Pitfall #4) — every Composio failure mode must surface as
  {success: False}, never {success: True} on a failed action:
    - HTTP 401 (auth failure)
    - HTTP 429 (rate limit)
    - successful:false in the body (Slack ok=false analogue, HTTP 200)
    - timeout
    - unmapped verb / missing field
  These are the failures that, masked, become the "reports success with 0 items"
  class of bug. The gate routes a {success: False} to QUEUE/retry, never a false
  outcome into the substrate.

Run: api/venv/bin/python -m pytest api/test_adr353_composio_parity.py -q
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
    monkeypatch.setenv("COMPOSIO_API_KEY", "test-composio-key")
    yield


def _mock_post(monkeypatch, *, status_code=200, body=None, raise_exc=None):
    captured: list[dict] = []

    class _Resp:
        def __init__(self):
            self.status_code = status_code
            self.text = "raw error text"

        def json(self):
            if body is None:
                raise ValueError("no json")
            return body

    class _Client:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, headers=None, json=None):
            captured.append({"url": url, "headers": headers, "body": json})
            if raise_exc is not None:
                raise raise_exc
            return _Resp()

    import services.composio_driver as driver
    monkeypatch.setattr(driver.httpx, "AsyncClient", _Client)
    return captured


# ---------------------------------------------------------------------------
# PARITY — result-dict keys match the first-party handler.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_to_channel_parity_keys(monkeypatch):
    """Composio send_to_channel returns the same result keys as first-party."""
    from services import composio_driver

    _mock_post(monkeypatch, body={"successful": True, "data": {"ts": "1.2", "channel": "C9"}})
    out = await composio_driver.execute(
        "slack", "send_to_channel",
        {"channel_id": "C9", "text": "hi"},
        token="xoxb-tok", user_id="u1",
    )
    assert out["success"] is True
    # First-party send_to_channel result shape: {"ts", "channel"} + top "message".
    assert set(out["result"].keys()) == {"ts", "channel"}
    assert out["result"]["ts"] == "1.2"
    assert out["result"]["channel"] == "C9"
    assert "message" in out  # parity with first-party annotation


@pytest.mark.asyncio
async def test_list_channels_parity_keys(monkeypatch):
    from services import composio_driver

    _mock_post(monkeypatch, body={
        "successful": True,
        "data": {"channels": [
            {"id": "C1", "name": "general", "is_private": False, "is_archived": False},
            {"id": "C2", "name_normalized": "random", "is_private": True},
            {"name": "no-id-skipped"},  # dropped — matches first-party filter
        ]},
    })
    out = await composio_driver.execute(
        "slack", "list_channels", {}, token="xoxb-tok", user_id="u1",
    )
    assert out["success"] is True
    assert set(out["result"].keys()) == {"channels", "count"}
    assert out["result"]["count"] == 2  # the no-id channel is dropped
    first = out["result"]["channels"][0]
    assert set(first.keys()) == {"id", "name", "is_private", "is_archived"}
    assert out["result"]["channels"][1]["name"] == "random"  # name_normalized fallback


@pytest.mark.asyncio
async def test_get_channel_history_parity_keys(monkeypatch):
    from services import composio_driver

    _mock_post(monkeypatch, body={
        "successful": True,
        "data": {"messages": [
            {"user": "U1", "text": "hello", "ts": "1.0",
             "reactions": [{"name": "+1", "count": 3}]},
            {"user": "U2", "text": "", "ts": "2.0"},  # empty text dropped
        ]},
    })
    out = await composio_driver.execute(
        "slack", "get_channel_history",
        {"channel_id": "C1", "limit": 50},
        token="xoxb-tok", user_id="u1",
    )
    assert out["success"] is True
    assert set(out["result"].keys()) == {"messages", "count"}
    assert out["result"]["count"] == 1  # empty-text message dropped (parity)
    msg = out["result"]["messages"][0]
    assert set(msg.keys()) == {"user", "text", "ts", "reactions"}
    assert msg["reactions"] == [{"name": "+1", "count": 3}]


@pytest.mark.asyncio
async def test_arguments_mapped_to_composio_shape(monkeypatch):
    """YARNNN input field names → Composio argument names (channel_id→channel)."""
    from services import composio_driver

    captured = _mock_post(monkeypatch, body={"successful": True, "data": {"ts": "1", "channel": "C1"}})
    await composio_driver.execute(
        "slack", "send_to_channel",
        {"channel_id": "C1", "text": "hi", "thread_ts": "9.9"},
        token="xoxb-tok", user_id="u1",
    )
    args = captured[0]["body"]["arguments"]
    assert args == {"channel": "C1", "text": "hi", "thread_ts": "9.9"}
    # The slug is pinned in the URL, not leaked upward.
    assert captured[0]["url"].endswith("/SLACK_SEND_MESSAGE")


# ---------------------------------------------------------------------------
# NO SILENT SUCCESS — every failure mode → success=False.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_auth_failure_no_silent_success(monkeypatch):
    from services import composio_driver

    _mock_post(monkeypatch, status_code=401, body={"error": "invalid_auth"})
    out = await composio_driver.execute(
        "slack", "send_to_channel", {"channel_id": "C1", "text": "x"},
        token="bad-token", user_id="u1",
    )
    assert out["success"] is False
    assert out["result"] is None
    assert "401" in out["error"]


@pytest.mark.asyncio
async def test_rate_limit_no_silent_success(monkeypatch):
    from services import composio_driver

    _mock_post(monkeypatch, status_code=429, body={"error": "rate_limited"})
    out = await composio_driver.execute(
        "slack", "send_to_channel", {"channel_id": "C1", "text": "x"},
        token="tok", user_id="u1",
    )
    assert out["success"] is False
    assert out["result"] is None
    assert "429" in out["error"]


@pytest.mark.asyncio
async def test_successful_false_in_body_no_silent_success(monkeypatch):
    """HTTP 200 but successful:false (the Slack ok=false analogue)."""
    from services import composio_driver

    _mock_post(monkeypatch, status_code=200, body={"successful": False, "error": "channel_not_found"})
    out = await composio_driver.execute(
        "slack", "send_to_channel", {"channel_id": "Cbad", "text": "x"},
        token="tok", user_id="u1",
    )
    assert out["success"] is False
    assert out["result"] is None
    assert "channel_not_found" in out["error"]


@pytest.mark.asyncio
async def test_timeout_no_silent_success(monkeypatch):
    import httpx
    from services import composio_driver

    _mock_post(monkeypatch, raise_exc=httpx.TimeoutException("timed out"))
    out = await composio_driver.execute(
        "slack", "send_to_channel", {"channel_id": "C1", "text": "x"},
        token="tok", user_id="u1",
    )
    assert out["success"] is False
    assert out["result"] is None
    assert "timed out" in out["error"].lower()


@pytest.mark.asyncio
async def test_unmapped_verb_no_silent_success(monkeypatch):
    from services import composio_driver

    _mock_post(monkeypatch, body={"successful": True, "data": {}})
    out = await composio_driver.execute(
        "slack", "delete_workspace",  # not in the action map
        {}, token="tok", user_id="u1",
    )
    assert out["success"] is False
    assert "unsupported action" in out["error"].lower()


@pytest.mark.asyncio
async def test_missing_api_key_no_silent_success(monkeypatch):
    from services import composio_driver

    monkeypatch.delenv("COMPOSIO_API_KEY", raising=False)
    out = await composio_driver.execute(
        "slack", "send_to_channel", {"channel_id": "C1", "text": "x"},
        token="tok", user_id="u1",
    )
    assert out["success"] is False
    assert "configured" in out["error"].lower()


@pytest.mark.asyncio
async def test_missing_token_no_silent_success(monkeypatch):
    from services import composio_driver

    out = await composio_driver.execute(
        "slack", "send_to_channel", {"channel_id": "C1", "text": "x"},
        token="", user_id="u1",
    )
    assert out["success"] is False
    assert "token" in out["error"].lower()


# ---------------------------------------------------------------------------
# FLAG / ALLOWLIST — default OFF, capital hard-excluded, swappable revert.
# ---------------------------------------------------------------------------

def test_flag_default_off(monkeypatch):
    from services import composio_driver
    monkeypatch.delenv("COMPOSIO_DRIVER_ENABLED", raising=False)
    assert composio_driver.driver_enabled_for("slack") is False


def test_flag_on_slack_only(monkeypatch):
    from services import composio_driver
    monkeypatch.setenv("COMPOSIO_DRIVER_ENABLED", "true")
    monkeypatch.setenv("COMPOSIO_PROVIDER_ALLOWLIST", "slack")
    assert composio_driver.driver_enabled_for("slack") is True
    assert composio_driver.driver_enabled_for("notion") is False
    assert composio_driver.driver_enabled_for("github") is False


def test_capital_family_never_enabled(monkeypatch):
    """Even if an operator mistakenly adds trading/commerce to the allowlist,
    the capital family is hard-excluded (ADR-353 §11)."""
    from services import composio_driver
    monkeypatch.setenv("COMPOSIO_DRIVER_ENABLED", "true")
    monkeypatch.setenv("COMPOSIO_PROVIDER_ALLOWLIST", "slack,trading,commerce")
    assert composio_driver.driver_enabled_for("trading") is False
    assert composio_driver.driver_enabled_for("commerce") is False
    assert composio_driver.driver_enabled_for("slack") is True


def test_revert_is_config_change(monkeypatch):
    """Swappability proof (ADR-353 §12.5): flag OFF fully reverts to first-party
    with no code change."""
    from services import composio_driver
    monkeypatch.setenv("COMPOSIO_DRIVER_ENABLED", "false")
    monkeypatch.setenv("COMPOSIO_PROVIDER_ALLOWLIST", "slack")
    assert composio_driver.driver_enabled_for("slack") is False

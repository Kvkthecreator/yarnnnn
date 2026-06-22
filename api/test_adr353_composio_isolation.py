"""ADR-353 §12.6 — multi-tenant isolation HARD GATE (the load-bearing test).

The specific failure that bites AFTER implementation (ADR-353 §7): an aggregator
in the personal-automation category runs every action as ONE account, so serving
N customers leaks credentials across tenants. The embedded category (Composio)
isolates per end-user. This test proves YARNNN's Phase-1 wiring is structurally
isolated REGARDLESS of which category Composio is in, because Phase 1 injects
each user's OWN token per call (Composio holds zero tenant auth state):

  Two distinct users, each with their own active Slack connection storing their
  own encrypted token. With the flag ON, the SAME action for each user must
  execute against that user's OWN credentials — never the other's.

We assert at the wire: the Authorization bearer Composio receives for user A is
A's token, for user B is B's token, and user_id (Composio entity) matches. Zero
cross-tenant leakage = the bearer/entity Composio sees is always the caller's.

This is the §12 stop-condition: if isolation cannot be shown, STOP.

Run: api/venv/bin/python -m pytest api/test_adr353_composio_isolation.py -q
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

API_DIR = Path(__file__).resolve().parent
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from cryptography.fernet import Fernet  # noqa: E402

# A throwaway Fernet key so TokenManager can construct + decrypt in-test.
_TEST_KEY = Fernet.generate_key().decode()


class _FakeSingle:
    def __init__(self, data):
        self._data = data

    def execute(self):
        return type("R", (), {"data": self._data})()


class _FakeQuery:
    """Minimal Supabase query stub: records the user_id filter and returns the
    matching per-user row, proving the token fetch is user-scoped."""

    def __init__(self, rows_by_user):
        self._rows_by_user = rows_by_user
        self._user_id = None

    def select(self, *_a, **_k):
        return self

    def eq(self, col, val):
        if col == "user_id":
            self._user_id = val
        return self

    def single(self):
        return _FakeSingle(self._rows_by_user.get(self._user_id))


class _FakeTable:
    def __init__(self, rows_by_user):
        self._rows_by_user = rows_by_user

    def table(self, _name):
        return _FakeQuery(self._rows_by_user)


class _FakeAuth:
    def __init__(self, user_id, client):
        self.user_id = user_id
        self.client = client


def _encrypt(plaintext: str) -> str:
    from integrations.core.tokens import TokenManager
    return TokenManager(encryption_key=_TEST_KEY).encrypt(plaintext)


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("INTEGRATION_ENCRYPTION_KEY", _TEST_KEY)
    monkeypatch.setenv("COMPOSIO_API_KEY", "test-composio-key")
    monkeypatch.setenv("COMPOSIO_DRIVER_ENABLED", "true")
    monkeypatch.setenv("COMPOSIO_PROVIDER_ALLOWLIST", "slack")
    # Reset the TokenManager singleton so it picks up the test key.
    import integrations.core.tokens as tokens_mod
    monkeypatch.setattr(tokens_mod, "_token_manager", None)
    yield


@pytest.mark.asyncio
async def test_two_users_zero_cross_tenant_leakage(monkeypatch):
    """The HARD GATE. Each user's action carries THAT user's token + entity."""
    from services import platform_tools

    rows_by_user = {
        "user-A": {"credentials_encrypted": _encrypt("xoxb-AAAA-token"), "metadata": {}},
        "user-B": {"credentials_encrypted": _encrypt("xoxb-BBBB-token"), "metadata": {}},
    }
    client = _FakeTable(rows_by_user)

    # Capture every Composio request at the wire.
    captured: list[dict] = []

    class _FakeResp:
        status_code = 200

        def json(self):
            return {"successful": True, "data": {"ts": "111.222", "channel": "C1"}}

    class _FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, headers=None, json=None):
            captured.append({"url": url, "headers": headers, "body": json})
            return _FakeResp()

    import services.composio_driver as driver
    monkeypatch.setattr(driver.httpx, "AsyncClient", _FakeClient)

    # Same action, two distinct users.
    res_a = await platform_tools.handle_platform_tool(
        _FakeAuth("user-A", client),
        "platform_slack_send_to_channel",
        {"channel_id": "C1", "text": "hi"},
    )
    res_b = await platform_tools.handle_platform_tool(
        _FakeAuth("user-B", client),
        "platform_slack_send_to_channel",
        {"channel_id": "C1", "text": "hi"},
    )

    assert res_a["success"] is True and res_b["success"] is True
    assert len(captured) == 2

    a_req, b_req = captured[0], captured[1]

    def _bearer(req):
        params = req["body"]["custom_auth_params"]["parameters"]
        auth_param = next(p for p in params if p["name"] == "Authorization")
        return auth_param["value"]

    # Each user's call carries ONLY that user's token — zero leakage.
    assert _bearer(a_req) == "Bearer xoxb-AAAA-token"
    assert _bearer(b_req) == "Bearer xoxb-BBBB-token"
    assert _bearer(a_req) != _bearer(b_req)

    # Composio entity == YARNNN user_id (ADR-353 §7), per call.
    assert a_req["body"]["user_id"] == "user-A"
    assert b_req["body"]["user_id"] == "user-B"

    # The other tenant's token NEVER appears in either request body.
    import json as _json
    assert "xoxb-BBBB-token" not in _json.dumps(a_req)
    assert "xoxb-AAAA-token" not in _json.dumps(b_req)


@pytest.mark.asyncio
async def test_missing_connection_is_loud_not_leaky(monkeypatch):
    """A user with no active connection gets a clean failure — never another
    user's credentials, never a silent success."""
    from services import platform_tools

    rows_by_user = {
        "user-A": {"credentials_encrypted": _encrypt("xoxb-AAAA-token"), "metadata": {}},
        # user-C has no row.
    }
    client = _FakeTable(rows_by_user)

    import services.composio_driver as driver

    class _ShouldNotCall:
        def __init__(self, *a, **k):
            raise AssertionError("Composio must not be called when no token exists")

    monkeypatch.setattr(driver.httpx, "AsyncClient", _ShouldNotCall)

    res = await platform_tools.handle_platform_tool(
        _FakeAuth("user-C", client),
        "platform_slack_list_channels",
        {},
    )
    assert res["success"] is False
    assert "slack" in res["error"].lower()

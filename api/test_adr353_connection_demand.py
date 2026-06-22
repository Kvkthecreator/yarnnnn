"""ADR-353 §15 — connection demand signal (the discovery queue).

A recurrence's requested capability that can't be satisfied is silently dropped in
get_platform_tools_for_capabilities (the ADR-227 empty-deliverable failure mode).
ADR-353 §15 captures that drop as a `[CONNECTION-DEMAND]` signal — the discovery
queue grounded in real program demand, not catalog-browsing.

Asserts:
  - an unknown capability (no provider in CAPABILITY_PROVIDER_MAP) → recorded as
    unknown_capability (a Hat-A add candidate);
  - a known capability whose provider is not connected → recorded as
    platform_not_connected (an operator-onboarding signal);
  - a satisfied capability → NOT recorded;
  - the recorder never raises.

Run: api/venv/bin/python -m pytest api/test_adr353_connection_demand.py -q
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

API_DIR = Path(__file__).resolve().parent
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))


class _FakeResult:
    def __init__(self, data):
        self.data = data


class _FakeConnQuery:
    def __init__(self, rows):
        self._rows = rows

    def select(self, *_a, **_k):
        return self

    def eq(self, *_a, **_k):
        return self

    def execute(self):
        return _FakeResult(self._rows)


class _FakeClient:
    def __init__(self, connected_rows):
        self._rows = connected_rows

    def table(self, _name):
        return _FakeConnQuery(self._rows)


class _FakeAuth:
    def __init__(self, user_id, rows):
        self.user_id = user_id
        self.client = _FakeClient(rows)


def test_recorder_never_raises():
    from services import connection_demand
    # Even with junk input it must be silent.
    connection_demand.record_unmet_capability("u1", "x", reason="unknown_capability", required_platform=None)
    connection_demand.record_unmet_capabilities("u1", [{"capability": "y", "reason": "z"}])
    connection_demand.record_unmet_capabilities("u1", [])


@pytest.mark.asyncio
async def test_unknown_capability_recorded(monkeypatch):
    from services import platform_tools

    captured: list[dict] = []
    monkeypatch.setattr(
        "services.connection_demand.record_unmet_capability",
        lambda uid, cap, *, reason, required_platform: captured.append(
            {"uid": uid, "cap": cap, "reason": reason, "platform": required_platform}
        ),
    )

    # No connected providers; request a capability with NO provider mapping.
    auth = _FakeAuth("u1", [])
    await platform_tools.get_platform_tools_for_capabilities(auth, ["totally_made_up_capability"])

    assert len(captured) == 1
    assert captured[0]["cap"] == "totally_made_up_capability"
    assert captured[0]["reason"] == "unknown_capability"
    assert captured[0]["platform"] is None


@pytest.mark.asyncio
async def test_known_capability_unconnected_recorded(monkeypatch):
    from services import platform_tools

    captured: list[dict] = []
    monkeypatch.setattr(
        "services.connection_demand.record_unmet_capability",
        lambda uid, cap, *, reason, required_platform: captured.append(
            {"uid": uid, "cap": cap, "reason": reason, "platform": required_platform}
        ),
    )

    # Slack NOT connected; request read_slack (a known capability → known provider).
    auth = _FakeAuth("u1", [])
    await platform_tools.get_platform_tools_for_capabilities(auth, ["read_slack"])

    assert len(captured) == 1
    assert captured[0]["cap"] == "read_slack"
    assert captured[0]["reason"] == "platform_not_connected"
    assert captured[0]["platform"] == "slack"


@pytest.mark.asyncio
async def test_satisfied_capability_not_recorded(monkeypatch):
    from services import platform_tools

    captured: list[dict] = []
    monkeypatch.setattr(
        "services.connection_demand.record_unmet_capability",
        lambda *a, **k: captured.append(a),
    )

    # Slack IS connected; request read_slack → satisfied → no demand signal.
    auth = _FakeAuth("u1", [{"platform": "slack", "status": "active"}])
    await platform_tools.get_platform_tools_for_capabilities(auth, ["read_slack"])

    assert captured == []

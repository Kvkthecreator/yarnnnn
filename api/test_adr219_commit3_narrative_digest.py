"""
Test gate — ADR-219 Commit 3 (Back-office narrative digest task).

Asserts the executor's contract:

A. Empty-state — when there are zero housekeeping entries in the window,
   the executor writes no rolled-up narrative entry. Counts are still
   reported in the run output, but the operator's chat doesn't get a
   noisy "nothing happened" card.

B. Rollup — when there ARE housekeeping entries, exactly ONE material-
   weight rolled-up narrative entry lands, with the envelope:
     - role = 'system'
     - pulse = 'periodic'
     - weight = 'material'
     - metadata.rolled_up_count == count of housekeeping entries
     - metadata.rolled_up_window_hours == DIGEST_WINDOW_HOURS
     - metadata.rolled_up_ids contains the source row ids

C. No-active-session — when there is no active chat session, the rollup
   is skipped (output.md still produced; counts reported); the executor
   does not raise.

D. Registry — the task type is registered in TASK_TYPES with the
   correct executor reference and output_kind=system_maintenance.

Usage:
    cd api && python test_adr219_commit3_narrative_digest.py
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = REPO_ROOT / "api"


# =============================================================================
# Fake client — minimal stand-in for the supabase chain we hit in run().
# =============================================================================
#
# The executor calls (in order):
#   1. client.table("chat_sessions").select(...).eq("user_id", U).execute()
#   2. client.table("session_messages").select(...).in_(...).gte(...).order().limit().execute()
#   3. (when housekeeping > 0) services.narrative.find_active_workspace_session(client, user_id)
#      which itself calls client.table("chat_sessions").select(...).eq().eq().order().limit().execute()
#   4. (when housekeeping > 0) services.narrative.write_narrative_entry(client, ...)
#      which calls client.rpc("append_session_message", ...).execute()
#
# We script the responses by registering them in order. Each call to
# .execute() pops the next pre-registered response.

class _Resp:
    def __init__(self, data, count=None):
        self.data = data
        self.count = count


class _Chain:
    def __init__(self, client, response):
        self._client = client
        self._response = response

    # All filter ops are chainable no-ops for this fake — we don't
    # validate what the executor filters by, just what it does with the
    # results we hand back. Filter validation lives in integration tests.
    def select(self, *a, **kw): return self
    def insert(self, *a, **kw): return self
    def update(self, *a, **kw): return self
    def delete(self, *a, **kw): return self
    def eq(self, *a, **kw): return self
    def neq(self, *a, **kw): return self
    def in_(self, *a, **kw): return self
    def gte(self, *a, **kw): return self
    def lt(self, *a, **kw): return self
    def order(self, *a, **kw): return self
    def limit(self, *a, **kw): return self
    def like(self, *a, **kw): return self
    def is_(self, *a, **kw): return self

    def execute(self):
        return self._response


class _RpcCall:
    def __init__(self, client, name, params):
        self._client = client
        self._name = name
        self._params = params

    def execute(self):
        # Record the RPC params for assertions, return the next queued
        # rpc response.
        self._client.rpc_calls.append((self._name, self._params))
        if self._client.rpc_responses:
            return self._client.rpc_responses.pop(0)
        return _Resp({"id": "rpc-default"})


class _FakeClient:
    def __init__(self, table_responses, rpc_responses=None):
        # table_responses: list of _Resp, served in order to .execute() calls
        # rpc_responses: list of _Resp, served in order to rpc().execute()
        self.table_responses = list(table_responses)
        self.rpc_responses = list(rpc_responses or [])
        self.rpc_calls: list[tuple[str, dict]] = []

    def table(self, name):
        if not self.table_responses:
            raise AssertionError(
                f"FakeClient ran out of table responses (called table({name!r}))"
            )
        return _Chain(self, self.table_responses.pop(0))

    def rpc(self, name, params):
        return _RpcCall(self, name, params)


# =============================================================================
# Tests
# =============================================================================

def _import_run():
    sys.path.insert(0, str(API_ROOT))
    from services.back_office.narrative_digest import run, DIGEST_WINDOW_HOURS  # noqa
    return run, DIGEST_WINDOW_HOURS


def test_empty_state_no_housekeeping() -> None:
    """No housekeeping entries → no rollup, no narrative emission."""
    run, _ = _import_run()

    # Seed responses:
    # 1. chat_sessions list for user → one session
    # 2. session_messages for that session → all material/routine, zero housekeeping
    client = _FakeClient(
        table_responses=[
            _Resp([{"id": "sess-1"}]),  # user has one session
            _Resp([
                {"id": "m1", "metadata": {"weight": "material", "summary": "delivered"}, "created_at": "2026-04-25T01:00:00Z"},
                {"id": "m2", "metadata": {"weight": "routine", "summary": "no-change run"}, "created_at": "2026-04-25T02:00:00Z"},
            ]),
        ],
    )

    result = asyncio.run(run(client, "u-1", "back-office-narrative-digest"))

    # No RPC call (no rollup).
    assert client.rpc_calls == [], f"unexpected rollup emitted: {client.rpc_calls}"
    # Result shape valid.
    assert "summary" in result and "output_markdown" in result and "actions_taken" in result
    # Summary mentions zero housekeeping.
    assert "0 housekeeping" in result["summary"], result["summary"]
    assert "Nothing to roll up" in result["summary"], result["summary"]
    # Actions: scan only.
    actions = result["actions_taken"]
    assert any(a.get("action") == "scan_window" for a in actions)
    assert all(a.get("action") != "emit_rollup" for a in actions)


def test_rollup_emits_one_material_entry() -> None:
    """N housekeeping entries → one material-weight rollup with envelope."""
    run, DIGEST_WINDOW_HOURS = _import_run()

    # Seed responses:
    # 1. chat_sessions list for user (one session)
    # 2. session_messages: 1 material, 1 routine, 3 housekeeping
    # 3. find_active_workspace_session → query chat_sessions again
    # 4. write_narrative_entry → append_session_message RPC
    client = _FakeClient(
        table_responses=[
            _Resp([{"id": "sess-1"}]),  # initial sessions list
            _Resp([
                {"id": "m1", "metadata": {"weight": "material", "summary": "delivered"}, "created_at": "2026-04-25T01:00:00Z"},
                {"id": "m2", "metadata": {"weight": "routine", "summary": "tracker run"}, "created_at": "2026-04-25T02:00:00Z"},
                {"id": "m3", "metadata": {"weight": "housekeeping", "summary": "cleanup found nothing"}, "created_at": "2026-04-25T03:00:00Z"},
                {"id": "m4", "metadata": {"weight": "housekeeping", "summary": "hygiene clean"}, "created_at": "2026-04-25T04:00:00Z"},
                {"id": "m5", "metadata": {"weight": "housekeeping", "summary": "proposal cleanup empty"}, "created_at": "2026-04-25T05:00:00Z"},
            ]),
            _Resp([{"id": "sess-active"}]),  # find_active_workspace_session
        ],
        rpc_responses=[
            _Resp({"id": "rollup-row"}),  # append_session_message
        ],
    )

    result = asyncio.run(run(client, "u-1", "back-office-narrative-digest"))

    # Exactly one RPC call (the rollup write).
    assert len(client.rpc_calls) == 1, f"expected 1 RPC, got {client.rpc_calls}"
    name, params = client.rpc_calls[0]
    assert name == "append_session_message"
    assert params["p_session_id"] == "sess-active"
    assert params["p_role"] == "system"

    md = params["p_metadata"]
    # Envelope assertions per ADR-219 D2 + Commit 3.
    assert md["pulse"] == "periodic"
    assert md["weight"] == "material", "rollup itself must be material weight (not housekeeping — it's the headline of the cluster)"
    assert md["rolled_up_count"] == 3
    assert md["rolled_up_window_hours"] == DIGEST_WINDOW_HOURS
    assert sorted(md["rolled_up_ids"]) == ["m3", "m4", "m5"]
    assert md["counts"] == {"material": 1, "routine": 1, "housekeeping": 3, "untagged": 0}
    assert md["system_card"] == "narrative_digest"
    assert md["authored_by"] == "system:back-office-narrative-digest"
    assert md["task_slug"] == "back-office-narrative-digest"

    # Summary body sanity — content shows the 3 housekeeping bullets.
    body = params["p_content"]
    assert "cleanup found nothing" in body
    assert "hygiene clean" in body
    assert "proposal cleanup empty" in body

    # Result shape.
    assert "Rolled up 3" in result["summary"]
    actions = result["actions_taken"]
    rollup_action = next(a for a in actions if a.get("action") == "emit_rollup")
    assert rollup_action["rolled_up_count"] == 3
    assert rollup_action["session_id"] == "sess-active"


def test_rollup_skipped_when_no_active_session() -> None:
    """Housekeeping entries exist but no active chat session → graceful skip."""
    run, _ = _import_run()

    client = _FakeClient(
        table_responses=[
            _Resp([{"id": "sess-1"}]),  # sessions list (for the scan step)
            _Resp([
                {"id": "h1", "metadata": {"weight": "housekeeping", "summary": "x"}, "created_at": "2026-04-25T01:00:00Z"},
            ]),
            _Resp([]),  # find_active_workspace_session returns no active session
        ],
    )

    result = asyncio.run(run(client, "u-1", "back-office-narrative-digest"))

    # No RPC call, but no exception raised.
    assert client.rpc_calls == []
    actions = result["actions_taken"]
    skip_action = next(a for a in actions if a.get("action") == "emit_rollup_skipped")
    assert skip_action["reason"] == "no_active_session"
    # output.md still mentions the housekeeping count.
    assert "1 housekeeping" in result["summary"]


def test_untagged_entries_counted_separately() -> None:
    """Legacy session_messages without the ADR-219 envelope are counted
    in the 'untagged' bucket — they don't crash the digest, and they
    don't pollute the housekeeping rollup."""
    run, _ = _import_run()

    client = _FakeClient(
        table_responses=[
            _Resp([{"id": "sess-1"}]),
            _Resp([
                {"id": "u1", "metadata": {}, "created_at": "2026-04-25T01:00:00Z"},  # no weight
                {"id": "u2", "metadata": None, "created_at": "2026-04-25T02:00:00Z"},  # null metadata
                {"id": "u3", "metadata": {"weight": "bogus"}, "created_at": "2026-04-25T03:00:00Z"},  # invalid weight
                {"id": "h1", "metadata": {"weight": "housekeeping", "summary": "ok"}, "created_at": "2026-04-25T04:00:00Z"},
            ]),
            _Resp([{"id": "sess-active"}]),
        ],
        rpc_responses=[_Resp({"id": "rollup-row"})],
    )

    result = asyncio.run(run(client, "u-1", "back-office-narrative-digest"))

    # Only 1 housekeeping entry rolls up — the 3 untagged ones are
    # bucketed separately, NOT injected into the rollup.
    name, params = client.rpc_calls[0]
    md = params["p_metadata"]
    assert md["rolled_up_count"] == 1
    assert md["rolled_up_ids"] == ["h1"]
    assert md["counts"]["untagged"] == 3
    assert md["counts"]["housekeeping"] == 1


def test_registry_entry_correctness() -> None:
    """Task type is registered with the right executor + output_kind."""
    sys.path.insert(0, str(API_ROOT))
    from services.task_types import TASK_TYPES

    assert "back-office-narrative-digest" in TASK_TYPES, \
        "narrative-digest task type missing from registry"
    entry = TASK_TYPES["back-office-narrative-digest"]
    assert entry["output_kind"] == "system_maintenance"
    assert entry["default_mode"] == "recurring"
    assert entry["default_schedule"] == "daily"
    assert entry["default_delivery"] == "none"
    # Process step declares the executor — pipeline reads this.
    process = entry["process"]
    assert len(process) == 1
    instruction = process[0]["instruction"]
    assert "executor: services.back_office.narrative_digest" in instruction


def test_helper_promoted_to_narrative_module() -> None:
    """find_active_workspace_session is exported from services.narrative
    (single canonical helper for autonomous narrative entries)."""
    sys.path.insert(0, str(API_ROOT))
    from services import narrative
    assert hasattr(narrative, "find_active_workspace_session"), \
        "find_active_workspace_session not promoted to services.narrative"
    assert "find_active_workspace_session" in narrative.__all__


# =============================================================================
# Driver
# =============================================================================

def main() -> int:
    tests = [
        ("A1 empty-state — no rollup when 0 housekeeping", test_empty_state_no_housekeeping),
        ("B1 rollup envelope — one material entry with metadata", test_rollup_emits_one_material_entry),
        ("C1 graceful skip — no active session", test_rollup_skipped_when_no_active_session),
        ("C2 untagged entries do not pollute rollup", test_untagged_entries_counted_separately),
        ("D1 registry entry correctness", test_registry_entry_correctness),
        ("D2 helper promoted to narrative module", test_helper_promoted_to_narrative_module),
    ]

    failed: list[tuple[str, BaseException]] = []
    for name, fn in tests:
        try:
            fn()
            print(f"  ✓ {name}")
        except BaseException as exc:  # noqa: BLE001
            failed.append((name, exc))
            print(f"  ✗ {name}: {exc}")
            import traceback
            traceback.print_exc()

    print()
    if failed:
        print(f"FAILED — {len(failed)}/{len(tests)} tests failed")
        return 1
    print(f"PASSED — {len(tests)}/{len(tests)} tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

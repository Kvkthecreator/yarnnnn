"""ADR-296 v2 D2 — Substrate-event walker regression gate.

Asserts the substrate-event walker (services/wake_sources/substrate_event.py)
reads /workspace/_hooks.yaml without raising and correctly fires
submit_wake_proposal on a frontmatter-field transition revision.

Background: from 2026-05-20T07:45Z (Checkpoint 2 deploy) through 2026-05-20T23:54Z,
walk_hooks raised `'coroutine' object has no attribute 'strip'` on every
scheduler tick for every user. Root cause: read_hooks called
UserMemory.read (async) without await; the coroutine reached parse_hooks
which called .strip() on it. The fix uses UserMemory.read_sync (existing
sync companion at api/services/workspace.py:692). This test guards against
that whole class of failure by exercising walk_hooks end-to-end against
live DB substrate.

The test does NOT exercise the downstream invoke_freddie body — that's
covered by other ADR-296 v2 tests + the canary in observation folders.
This test exercises the walker contract: substrate present → walker reads
without raising → matcher returns hook match → submit_wake_proposal called
exactly once with the expected payload shape.

Run: .venv/bin/python api/test_adr296_substrate_event_walker.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

_API_ROOT = Path(__file__).resolve().parent
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

_REPO_ROOT = _API_ROOT.parent
from dotenv import load_dotenv
load_dotenv(_REPO_ROOT / ".env")


# Reuse the alpha-trader test user's id — same convention as test_adr209_phase1.py.
# All scratch substrate is namespaced to /workspace/_test_adr296_walker/* under
# this user; cleanup wipes it at the end of every run.
TEST_USER_ID = "2abf3f96-118b-4987-9d95-40f2d9be9a18"
HOOKS_PATH = "/workspace/_hooks.yaml"
PROFILE_PATH = "/workspace/_test_adr296_walker/profile.md"

HOOKS_YAML_BODY = """hooks:
  - slug: test-adr296-walker-hook
    event: substrate_change
    path_match: /workspace/_test_adr296_walker/*.md
    field_change:
      status: ready_for_review
    prompt: |
      Test hook for ADR-296 substrate-event walker regression gate.
    paused: false
"""

PROFILE_DRAFT = """---
title: Test draft
slug: test-adr296-walker
status: draft
---

Test body.
"""

PROFILE_READY = """---
title: Test draft
slug: test-adr296-walker
status: ready_for_review
---

Test body.
"""


def _ok(msg: str) -> None:
    print(f"  PASS  {msg}")


def _fail(label: str, detail: str = "") -> None:
    print(f"  FAIL  {label}" + (f" — {detail}" if detail else ""))
    raise SystemExit(1)


def _section(label: str) -> None:
    print()
    print(f"=== {label} ===")


# ---------------------------------------------------------------------------
# Static checks — guard against the async-context-leak class of failure
# ---------------------------------------------------------------------------


def test_static_read_hooks_uses_sync_api() -> None:
    """The bug fixed in this commit: read_hooks must call read_sync, not read.

    Direct grep of substrate_event.py ensures no future refactor reintroduces
    the unawaited coroutine pattern.
    """
    _section("Static checks")
    src = (_API_ROOT / "services/wake_sources/substrate_event.py").read_text(encoding="utf-8")
    if "memory.read_sync(" not in src:
        _fail(
            "read_hooks must call memory.read_sync",
            "substrate_event.py no longer uses read_sync — async coroutine "
            "would reach parse_hooks().strip() and raise 'coroutine' has "
            "no attribute 'strip'",
        )
    _ok("substrate_event.py uses memory.read_sync (sync API)")

    # Negative guard: confirm no naked `memory.read(` survives — the bug shape.
    # Permitted exceptions: read_sync (above), read_revision, read_file, etc.
    for line_no, line in enumerate(src.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if "memory.read(" in line and "memory.read_sync(" not in line:
            _fail(
                "naked memory.read( in substrate_event.py",
                f"line {line_no}: {stripped!r} — would reintroduce the "
                f"async-context-leak bug",
            )
    _ok("no naked memory.read( call sites in substrate_event.py")


# ---------------------------------------------------------------------------
# Unit checks — parse_hooks + _field_change_matches against fixture content
# ---------------------------------------------------------------------------


def test_parse_hooks_well_formed() -> None:
    _section("Unit: parse_hooks")
    from services.wake_sources.substrate_event import parse_hooks
    hooks = parse_hooks(HOOKS_YAML_BODY)
    if len(hooks) != 1:
        _fail("parse_hooks count", f"expected 1, got {len(hooks)}")
    h = hooks[0]
    if h["slug"] != "test-adr296-walker-hook":
        _fail("hook slug", f"got {h['slug']!r}")
    if h["event"] != "substrate_change":
        _fail("hook event", f"got {h['event']!r}")
    if h["path_match"] != "/workspace/_test_adr296_walker/*.md":
        _fail("hook path_match", f"got {h['path_match']!r}")
    if h["field_change"] != {"status": "ready_for_review"}:
        _fail("hook field_change", f"got {h['field_change']!r}")
    if h["paused"] is not False:
        _fail("hook paused", f"got {h['paused']!r}")
    _ok("parse_hooks returns 1 well-formed hook from fixture YAML")


def test_field_change_matches_transition() -> None:
    _section("Unit: _field_change_matches transition guard")
    from services.wake_sources.substrate_event import _field_change_matches

    # Transition draft → ready_for_review: should match.
    if not _field_change_matches(PROFILE_READY, PROFILE_DRAFT, {"status": "ready_for_review"}):
        _fail("draft→ready_for_review transition", "matcher should return True")
    _ok("draft → ready_for_review transition matches")

    # Same-state write (ready_for_review → ready_for_review): should NOT match.
    if _field_change_matches(PROFILE_READY, PROFILE_READY, {"status": "ready_for_review"}):
        _fail("same-state write", "matcher must return False on preserving write")
    _ok("ready_for_review → ready_for_review (preserving write) does NOT match")

    # First-revision (no prev_content): per implementation, transitions fire
    # if there's no prior state (None prev_content) AND new value matches.
    if not _field_change_matches(PROFILE_READY, None, {"status": "ready_for_review"}):
        _fail("first-revision transition", "first revision into target state should match")
    _ok("first revision into ready_for_review matches (no prev_content)")

    # Wrong target value: should NOT match.
    if _field_change_matches(PROFILE_DRAFT, PROFILE_READY, {"status": "ready_for_review"}):
        _fail("wrong target value", "matcher must return False when new value differs from expected")
    _ok("draft (wrong value) does NOT match ready_for_review target")


# ---------------------------------------------------------------------------
# Integration check — walk_hooks against live DB substrate
# ---------------------------------------------------------------------------


async def run_walk_hooks_integration() -> None:
    """End-to-end: seed _hooks.yaml + a revision pair → walk_hooks fires submit_wake_proposal.

    Mocks submit_wake_proposal so the test doesn't actually invoke the
    Reviewer (which would call the LLM). Asserts the mock was called
    exactly once with source='substrate_event' and the expected payload.
    """
    _section("Integration: walk_hooks against live DB substrate")

    from services.authored_substrate import write_revision
    from services.supabase import get_service_client
    from services.wake_sources.substrate_event import walk_hooks

    client = get_service_client()

    # Snapshot whatever _hooks.yaml content already exists on the test user
    # so we can restore it after the test (TEST_USER_ID is alpha-trader's
    # real workspace — we must NOT clobber its hooks substrate).
    existing_hooks_row = (
        client.table("workspace_files")
        .select("content")
        .eq("user_id", TEST_USER_ID)
        .eq("path", HOOKS_PATH)
        .limit(1)
        .execute()
    )
    prior_hooks_content = (
        existing_hooks_row.data[0]["content"] if existing_hooks_row.data else None
    )

    try:
        # 1. Seed _hooks.yaml on the test user — overwrites the alpha-trader
        # bundle's _hooks.yaml temporarily; we restore it in the finally.
        write_revision(
            client,
            user_id=TEST_USER_ID,
            path=HOOKS_PATH,
            content=HOOKS_YAML_BODY,
            authored_by="system:test-adr296-walker",
            message="test_adr296_substrate_event_walker.py: seed fixture _hooks.yaml",
        )
        _ok("seeded fixture _hooks.yaml on TEST_USER_ID")

        # 2. Write draft revision (status=draft) — establishes the prior state.
        write_revision(
            client,
            user_id=TEST_USER_ID,
            path=PROFILE_PATH,
            content=PROFILE_DRAFT,
            authored_by="system:test-adr296-walker",
            message="test scratch: status=draft (prior state for transition)",
        )
        _ok("seeded fixture profile.md@draft")

        # Tiny breath so the second revision's created_at is unambiguously
        # after the first (timestamp ordering).
        await asyncio.sleep(0.5)

        # 3. Write ready_for_review revision — THE transition the hook fires on.
        write_revision(
            client,
            user_id=TEST_USER_ID,
            path=PROFILE_PATH,
            content=PROFILE_READY,
            authored_by="system:test-adr296-walker",
            message="test scratch: status=ready_for_review (the transition)",
        )
        _ok("seeded fixture profile.md@ready_for_review (transition revision)")

        # 4. Patch submit_wake_proposal so the walker fires it but the Reviewer
        # never wakes (no LLM call). Reach the import the walker uses.
        mock_submit = AsyncMock(return_value={
            "success": True,
            "source": "substrate_event",
            "funnel_decision": "escalate",
        })

        # Walk with a recent `since` window covering our writes.
        since = datetime.now(timezone.utc) - timedelta(minutes=5)

        with patch("services.wake_sources.substrate_event.submit_wake_proposal", mock_submit):
            outcomes = await walk_hooks(client, TEST_USER_ID, since=since)

        # 5. Assertions
        if mock_submit.call_count != 1:
            _fail(
                "submit_wake_proposal call_count",
                f"expected 1, got {mock_submit.call_count} — walker did not "
                f"fire exactly once on the transition revision",
            )
        _ok("submit_wake_proposal called exactly once")

        call_kwargs = mock_submit.call_args.kwargs
        if call_kwargs.get("source") != "substrate_event":
            _fail(
                "submit_wake_proposal source kwarg",
                f"expected 'substrate_event', got {call_kwargs.get('source')!r}",
            )
        _ok("submit_wake_proposal called with source='substrate_event'")

        payload = call_kwargs.get("payload") or {}
        if payload.get("path") != PROFILE_PATH:
            _fail(
                "payload.path",
                f"expected {PROFILE_PATH!r}, got {payload.get('path')!r}",
            )
        _ok(f"payload.path == {PROFILE_PATH}")

        if payload.get("field_change") != {"status": "ready_for_review"}:
            _fail(
                "payload.field_change",
                f"expected {{'status': 'ready_for_review'}}, got {payload.get('field_change')!r}",
            )
        _ok("payload.field_change == {'status': 'ready_for_review'}")

        if (payload.get("hook") or {}).get("slug") != "test-adr296-walker-hook":
            _fail(
                "payload.hook.slug",
                f"expected 'test-adr296-walker-hook', got {(payload.get('hook') or {}).get('slug')!r}",
            )
        _ok("payload.hook.slug == 'test-adr296-walker-hook'")

        if len(outcomes) != 1:
            _fail(
                "walk_hooks outcomes count",
                f"expected 1, got {len(outcomes)}",
            )
        _ok("walk_hooks returned exactly 1 outcome")

        # 6. Migration 178 dedup contract: simulate the wake completing
        # by inserting an execution_events row with wake_dedup_key set to
        # the transition revision_id. Then walk again — walker should skip.
        # This is the regression gate for the wake-duplication audit
        # (docs/evaluations/2026-05-21-005856-wake-duplication-audit/).
        transition_revision_id = payload.get("revision_id")
        if not transition_revision_id:
            _fail(
                "payload.revision_id missing",
                "walker must populate revision_id in payload for dedup to work",
            )
        _ok(f"payload.revision_id == {transition_revision_id[:8]}...")

        # Simulate wake completion (what _invoke_substrate_event_wake's
        # success path does in production).
        wake_event_id = None
        try:
            wake_event_result = (
                client.table("execution_events")
                .insert({
                    "user_id": TEST_USER_ID,
                    "slug": "test-adr296-walker-hook",
                    "mode": "judgment",
                    "trigger_type": "reactive",
                    "status": "success",
                    "wake_source": "substrate_event",
                    "funnel_decision": "escalate",
                    "wake_dedup_key": transition_revision_id,
                })
                .execute()
            )
            if wake_event_result.data:
                wake_event_id = wake_event_result.data[0].get("id")
            _ok("simulated wake completion (execution_events row inserted)")
        except Exception as exc:
            _fail(
                "execution_events insert (simulating wake completion)",
                f"could not insert wake event: {exc}",
            )

        try:
            # Reset the mock so we count fresh calls.
            mock_submit.reset_mock()

            # Walk again — same since window, same revisions.
            with patch("services.wake_sources.substrate_event.submit_wake_proposal", mock_submit):
                outcomes_2 = await walk_hooks(client, TEST_USER_ID, since=since)

            if mock_submit.call_count != 0:
                _fail(
                    "dedup gate: submit_wake_proposal call_count on second walk",
                    f"expected 0 (dedup gate engaged), got {mock_submit.call_count} "
                    f"— walker re-fired despite execution_events row with matching "
                    f"wake_dedup_key={transition_revision_id[:8]}...",
                )
            _ok("dedup gate: second walk did NOT re-fire wake (0 submissions)")

            if outcomes_2:
                _fail(
                    "dedup gate: walk_hooks outcomes on second walk",
                    f"expected [], got {len(outcomes_2)} outcomes — dedup should "
                    f"short-circuit before submit_wake_proposal",
                )
            _ok("dedup gate: walk_hooks returned empty outcomes on second walk")
        finally:
            # Wipe the simulated wake event so the next test run starts clean.
            if wake_event_id:
                try:
                    client.table("execution_events").delete().eq(
                        "id", wake_event_id
                    ).execute()
                except Exception as exc:
                    print(f"  WARN  test wake event cleanup failed: {exc}")

    finally:
        # Cleanup: wipe scratch profile + restore the prior _hooks.yaml content
        # (or delete if there was none before).
        try:
            client.table("workspace_files").delete().eq(
                "user_id", TEST_USER_ID
            ).eq("path", PROFILE_PATH).execute()
            client.table("workspace_file_versions").delete().eq(
                "user_id", TEST_USER_ID
            ).eq("path", PROFILE_PATH).execute()
        except Exception as exc:
            print(f"  WARN  scratch profile cleanup failed: {exc}")

        try:
            if prior_hooks_content is None:
                # Test user had no _hooks.yaml before — wipe what we wrote.
                client.table("workspace_files").delete().eq(
                    "user_id", TEST_USER_ID
                ).eq("path", HOOKS_PATH).execute()
                client.table("workspace_file_versions").delete().eq(
                    "user_id", TEST_USER_ID
                ).eq("path", HOOKS_PATH).execute()
            else:
                # Restore prior _hooks.yaml via a new revision attributed
                # to the test cleanup — preserves revision history.
                write_revision(
                    client,
                    user_id=TEST_USER_ID,
                    path=HOOKS_PATH,
                    content=prior_hooks_content,
                    authored_by="system:test-adr296-walker",
                    message="test cleanup: restore prior _hooks.yaml content",
                )
        except Exception as exc:
            print(f"  WARN  _hooks.yaml restore failed: {exc}")

        _ok("scratch cleanup complete (profile wiped, _hooks.yaml restored)")


def main() -> int:
    print("ADR-296 v2 D2 substrate-event walker regression gate")
    print()

    # Static checks first — no DB needed; catch the bug pattern before runtime.
    test_static_read_hooks_uses_sync_api()

    # Unit checks against in-memory fixtures.
    test_parse_hooks_well_formed()
    test_field_change_matches_transition()

    # Integration check against live DB.
    if not os.environ.get("SUPABASE_URL") or not os.environ.get("SUPABASE_SERVICE_KEY"):
        print()
        print("  SKIP  Integration test — SUPABASE_URL / SUPABASE_SERVICE_KEY not set")
        return 0

    asyncio.run(run_walk_hooks_integration())

    print()
    print("All checks PASS — substrate-event walker is healthy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

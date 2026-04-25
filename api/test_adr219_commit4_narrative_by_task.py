"""
Test gate — ADR-219 Commit 4 (`/work` list view as filter-over-narrative).

Exercises the GET /api/narrative/by-task endpoint logic with a fake
Supabase client. The endpoint replaces the timestamp-only "Last: 5m"
WorkListSurface signal with the most-recent material narrative entry
per task slug. This test asserts:

A. Empty state — when the user has no chat sessions, returns an empty
   tasks list with the requested window_hours echoed.

B. Grouping — session_messages are bucketed by metadata.task_slug.
   Entries without a task_slug (inline actions) are excluded.

C. Last-material selection — returns the MOST RECENT material entry
   per slug irrespective of window. Older material rows are not
   shadowed by newer routine/housekeeping rows.

D. Counts windowing — `counts` only includes rows within the rolling
   window. Older material counts are NOT in the bucket totals.

E. Sort — response.tasks sorted by most_recent_at desc.

F. Untagged weight — rows with weight outside the valid set don't
   crash; they're ignored from counts.

Usage:
    cd api && python test_adr219_commit4_narrative_by_task.py
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = REPO_ROOT / "api"


# =============================================================================
# Fake client — same pattern as Commit 3's test gate.
# =============================================================================

class _Resp:
    def __init__(self, data, count=None):
        self.data = data
        self.count = count


class _Chain:
    def __init__(self, response):
        self._response = response

    def select(self, *a, **kw): return self
    def eq(self, *a, **kw): return self
    def in_(self, *a, **kw): return self
    def order(self, *a, **kw): return self
    def limit(self, *a, **kw): return self

    def execute(self):
        return self._response


class _FakeAuth:
    """Stand-in for services.supabase.UserClient. The endpoint uses
    `auth.user_id` and `auth.client.table(...)` only."""
    def __init__(self, user_id: str, table_responses: list):
        self.user_id = user_id
        self._responses = list(table_responses)

    @property
    def client(self):
        return self

    def table(self, name: str):
        if not self._responses:
            raise AssertionError(
                f"FakeAuth ran out of table responses (called table({name!r}))"
            )
        return _Chain(self._responses.pop(0))


def _import_endpoint():
    sys.path.insert(0, str(API_ROOT))
    from routes.narrative import by_task, DEFAULT_WINDOW_HOURS
    return by_task, DEFAULT_WINDOW_HOURS


# =============================================================================
# Tests
# =============================================================================

def _ts(hours_ago: float) -> str:
    """Helper — ISO-format timestamp for `hours_ago` ago, UTC."""
    return (
        datetime.now(timezone.utc) - timedelta(hours=hours_ago)
    ).isoformat()


def test_empty_when_no_sessions() -> None:
    """User with zero chat sessions returns empty list."""
    by_task, DEFAULT_WINDOW_HOURS = _import_endpoint()

    auth = _FakeAuth(
        user_id="u-1",
        table_responses=[
            _Resp([]),  # chat_sessions: empty
        ],
    )

    result = asyncio.run(by_task(auth))
    assert result.window_hours == DEFAULT_WINDOW_HOURS
    assert result.tasks == [], f"expected empty tasks, got {result.tasks}"


def test_inline_actions_excluded() -> None:
    """Rows without a metadata.task_slug are inline actions and must
    NOT appear in the by-task response."""
    by_task, _ = _import_endpoint()

    auth = _FakeAuth(
        user_id="u-1",
        table_responses=[
            _Resp([{"id": "sess-1"}]),
            _Resp([
                # Inline action — operator chat with no task_slug
                {"id": "m1", "role": "user", "content": "hey", "metadata": {"weight": "material", "summary": "what's up"}, "created_at": _ts(1)},
                # Task-tagged invocation
                {"id": "m2", "role": "agent", "content": "delivered", "metadata": {"weight": "material", "summary": "Researcher delivered scan", "task_slug": "competitor-scan"}, "created_at": _ts(2)},
            ]),
        ],
    )

    result = asyncio.run(by_task(auth))
    assert len(result.tasks) == 1, f"only the task-tagged row should appear: {result.tasks}"
    assert result.tasks[0].task_slug == "competitor-scan"
    assert result.tasks[0].last_material is not None
    assert result.tasks[0].last_material.summary == "Researcher delivered scan"


def test_last_material_is_most_recent_irrespective_of_window() -> None:
    """The headline is "what shipped last" — the most recent material
    entry, even if it predates the rolling-counts window."""
    by_task, _ = _import_endpoint()

    auth = _FakeAuth(
        user_id="u-1",
        table_responses=[
            _Resp([{"id": "sess-1"}]),
            # session_messages ordered by created_at desc per the
            # endpoint's query, so mimic that here.
            _Resp([
                # 1h ago: routine entry — newer but not material
                {"id": "m1", "role": "system", "content": "no change", "metadata": {"weight": "routine", "summary": "no-change run", "task_slug": "competitor-scan"}, "created_at": _ts(1)},
                # 30h ago: material entry — older but the actual headline
                {"id": "m2", "role": "agent", "content": "delivered", "metadata": {"weight": "material", "summary": "Researcher delivered scan", "task_slug": "competitor-scan"}, "created_at": _ts(30)},
                # 50h ago: older material — should be shadowed by m2
                {"id": "m3", "role": "agent", "content": "earlier", "metadata": {"weight": "material", "summary": "earlier scan", "task_slug": "competitor-scan"}, "created_at": _ts(50)},
            ]),
        ],
    )

    result = asyncio.run(by_task(auth))
    slice_ = result.tasks[0]
    # m2 is the most-recent material — even though m1 is newer
    assert slice_.last_material is not None
    assert slice_.last_material.summary == "Researcher delivered scan"
    # most_recent_at tracks the most-recent any-weight entry — m1
    assert slice_.most_recent_at == _ts(1) or slice_.most_recent_at >= _ts(2)


def test_counts_window_filters_older_rows() -> None:
    """`counts` only counts rows within the rolling window. Older
    material entries (outside window) are visible via last_material
    but are NOT counted in counts.material."""
    by_task, _ = _import_endpoint()

    auth = _FakeAuth(
        user_id="u-1",
        table_responses=[
            _Resp([{"id": "sess-1"}]),
            _Resp([
                # In-window (default 24h): 2 routine + 1 housekeeping
                {"id": "m1", "role": "agent", "content": "ok", "metadata": {"weight": "routine", "summary": "tracker run", "task_slug": "track-x"}, "created_at": _ts(1)},
                {"id": "m2", "role": "agent", "content": "ok", "metadata": {"weight": "routine", "summary": "tracker run 2", "task_slug": "track-x"}, "created_at": _ts(2)},
                {"id": "m3", "role": "system", "content": "nothing", "metadata": {"weight": "housekeeping", "summary": "cleanup empty", "task_slug": "track-x"}, "created_at": _ts(3)},
                # Out-of-window (>24h): material that becomes the headline but doesn't count
                {"id": "m4", "role": "agent", "content": "delivered", "metadata": {"weight": "material", "summary": "shipped scan", "task_slug": "track-x"}, "created_at": _ts(50)},
            ]),
        ],
    )

    result = asyncio.run(by_task(auth))
    slice_ = result.tasks[0]
    # last_material picks m4 (older but the only material)
    assert slice_.last_material is not None
    assert slice_.last_material.summary == "shipped scan"
    # counts: 2 routine + 1 housekeeping in window, 0 material in window
    assert slice_.counts.material == 0, f"older material should not count in window: {slice_.counts}"
    assert slice_.counts.routine == 2
    assert slice_.counts.housekeeping == 1


def test_response_sorted_by_most_recent_at_desc() -> None:
    """When multiple tasks have entries, response.tasks is sorted
    most-recent first."""
    by_task, _ = _import_endpoint()

    auth = _FakeAuth(
        user_id="u-1",
        table_responses=[
            _Resp([{"id": "sess-1"}]),
            _Resp([
                # task-A's most recent entry
                {"id": "a1", "role": "agent", "content": "x", "metadata": {"weight": "material", "summary": "a delivered", "task_slug": "task-a"}, "created_at": _ts(1)},
                # task-B's most recent entry — older than task-A
                {"id": "b1", "role": "agent", "content": "x", "metadata": {"weight": "material", "summary": "b delivered", "task_slug": "task-b"}, "created_at": _ts(5)},
                # task-C's most recent entry — newest
                {"id": "c1", "role": "agent", "content": "x", "metadata": {"weight": "material", "summary": "c delivered", "task_slug": "task-c"}, "created_at": _ts(0.5)},
            ]),
        ],
    )

    result = asyncio.run(by_task(auth))
    slugs = [t.task_slug for t in result.tasks]
    assert slugs == ["task-c", "task-a", "task-b"], f"sort order wrong: {slugs}"


def test_invalid_weight_doesnt_crash_or_count() -> None:
    """Legacy / corrupt rows with weight outside the valid set are
    ignored from counts. They still contribute to most_recent_at if
    they have a task_slug (which is fine — they exist, just not
    classified)."""
    by_task, _ = _import_endpoint()

    auth = _FakeAuth(
        user_id="u-1",
        table_responses=[
            _Resp([{"id": "sess-1"}]),
            _Resp([
                {"id": "u1", "role": "agent", "content": "?", "metadata": {"weight": "loud", "summary": "bogus", "task_slug": "task-a"}, "created_at": _ts(1)},
                {"id": "u2", "role": "agent", "content": "?", "metadata": {"summary": "no weight", "task_slug": "task-a"}, "created_at": _ts(2)},
                {"id": "m1", "role": "agent", "content": "ok", "metadata": {"weight": "material", "summary": "ok", "task_slug": "task-a"}, "created_at": _ts(3)},
            ]),
        ],
    )

    result = asyncio.run(by_task(auth))
    slice_ = result.tasks[0]
    assert slice_.counts.material == 1
    assert slice_.counts.routine == 0
    assert slice_.counts.housekeeping == 0
    assert slice_.last_material.summary == "ok"


def test_no_material_entry_at_all() -> None:
    """A task with only routine/housekeeping rows surfaces in the
    response (counts populated) but last_material is None — the
    frontend will render no headline for it."""
    by_task, _ = _import_endpoint()

    auth = _FakeAuth(
        user_id="u-1",
        table_responses=[
            _Resp([{"id": "sess-1"}]),
            _Resp([
                {"id": "m1", "role": "agent", "content": "no change", "metadata": {"weight": "routine", "summary": "tracker no-change", "task_slug": "track-x"}, "created_at": _ts(1)},
                {"id": "m2", "role": "system", "content": "nothing", "metadata": {"weight": "housekeeping", "summary": "cleanup empty", "task_slug": "track-x"}, "created_at": _ts(2)},
            ]),
        ],
    )

    result = asyncio.run(by_task(auth))
    slice_ = result.tasks[0]
    assert slice_.last_material is None
    assert slice_.counts.routine == 1
    assert slice_.counts.housekeeping == 1
    assert slice_.most_recent_at is not None  # most_recent_at tracks any-weight


# =============================================================================
# Frontend wiring — minimal contract assertions
# =============================================================================
#
# The endpoint is the load-bearing piece, but Commit 4 also wires the
# frontend hook + WorkListSurface prop. We grep-assert the wiring
# rather than spinning up a JS runtime.

import re
import subprocess


def test_frontend_hook_exposes_narrative_by_task() -> None:
    hook_path = REPO_ROOT / "web" / "hooks" / "useAgentsAndTasks.ts"
    src = hook_path.read_text()
    assert "narrativeByTask" in src, "useAgentsAndTasks must expose narrativeByTask"
    assert "api.narrative.byTask" in src or "api.narrative\n" in src, \
        "useAgentsAndTasks must call api.narrative.byTask"
    assert "Map<string, NarrativeByTaskSlice>" in src, \
        "narrativeByTask should be typed as Map<slug, slice>"


def test_frontend_surface_consumes_slice() -> None:
    surface_path = REPO_ROOT / "web" / "components" / "work" / "WorkListSurface.tsx"
    src = surface_path.read_text()
    assert "narrativeByTask: Map<string, NarrativeByTaskSlice>" in src, \
        "WorkListSurface props must accept narrativeByTask map"
    # Row consumes the slice
    assert "narrativeSlice" in src, "WorkRow must receive a narrativeSlice prop"
    assert "lastMaterial" in src or "last_material" in src, \
        "WorkRow must render the last_material headline"


def test_api_client_exports_narrative_method() -> None:
    client_path = REPO_ROOT / "web" / "lib" / "api" / "client.ts"
    src = client_path.read_text()
    assert "narrative:" in src, "api client must expose narrative section"
    assert "/api/narrative/by-task" in src, \
        "api client must hit /api/narrative/by-task"


# =============================================================================
# Driver
# =============================================================================

def main() -> int:
    tests = [
        ("A1 empty when no sessions", test_empty_when_no_sessions),
        ("B1 inline actions excluded (no task_slug)", test_inline_actions_excluded),
        ("C1 last_material is most-recent irrespective of window", test_last_material_is_most_recent_irrespective_of_window),
        ("D1 counts windowed; older material doesn't count", test_counts_window_filters_older_rows),
        ("E1 response sorted by most_recent_at desc", test_response_sorted_by_most_recent_at_desc),
        ("F1 invalid weight ignored from counts", test_invalid_weight_doesnt_crash_or_count),
        ("G1 task with no material has null last_material", test_no_material_entry_at_all),
        ("FE1 hook exposes narrativeByTask", test_frontend_hook_exposes_narrative_by_task),
        ("FE2 surface consumes narrative slice", test_frontend_surface_consumes_slice),
        ("FE3 api client wires narrative endpoint", test_api_client_exports_narrative_method),
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

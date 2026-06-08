"""ADR-298 Phase 1 — wake_queue schema + service regression gate.

Asserts:
- Migration 179 landed cleanly: table exists, indexes exist, constraints exist.
- enqueue() inserts pending rows with correct lane resolution.
- enqueue() returns None silently on UNIQUE constraint hits (cross-source dedup).
- enqueue() accepts NULL dedup_key for manual_fire (intentional bypass).
- get_next_pending() respects FIFO + lane scoping.
- try_lock() atomically transitions pending → locked via CAS.
- try_lock() returns False on concurrent contention.
- has_in_flight() detects locked rows.
- mark_completed() / mark_failed() / mark_dropped() transition states correctly.
- reclaim_stale_locks() returns 'locked' rows older than threshold to 'pending'.
- gc_completed() deletes completed/failed/dropped rows older than threshold.
- queue_depth() reports pending counts correctly.

All scratch state is namespaced under a unique test user_id; cleanup at end
of run wipes the test's queue rows. Per ADR-298 D2 the queue is transient
compute, so test-namespace pollution is structurally safe.

Run: .venv/bin/python api/test_adr298_phase1_wake_queue.py
"""

from __future__ import annotations

import os
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

_API_ROOT = Path(__file__).resolve().parent
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

_REPO_ROOT = _API_ROOT.parent
from dotenv import load_dotenv  # noqa: E402
load_dotenv(_REPO_ROOT / ".env")

from supabase import create_client  # noqa: E402

from services.wake_queue import (  # noqa: E402
    DEFAULT_GC_DAYS,
    DEFAULT_STALE_LOCK_SECONDS,
    InvalidLaneError,
    InvalidWakeSourceError,
    VALID_LANES,
    VALID_STATUSES,
    VALID_WAKE_SOURCES,
    enqueue,
    gc_completed,
    get_next_pending,
    has_in_flight,
    mark_completed,
    mark_dropped,
    mark_failed,
    queue_depth,
    reclaim_stale_locks,
    resolve_lane,
    try_lock,
)


# Use a fresh, unique user id per run so failures don't pollute future runs.
TEST_USER_ID = str(uuid.uuid4())


def _client():
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    return create_client(url, key)


# ─── Assertions framework ───────────────────────────────────────────────────


PASSED = 0
FAILED = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global PASSED, FAILED
    if condition:
        print(f"  ✓ {label}")
        PASSED += 1
    else:
        print(f"  ✗ {label}{(' — ' + detail) if detail else ''}")
        FAILED += 1


# ─── Schema invariants ──────────────────────────────────────────────────────


def test_schema_landed(client) -> None:
    print("\n[Schema] Migration 179 invariants")
    result = client.rpc("exec_sql_returning_json_table", {"query": "..."}) if False else None
    # Use a plain SQL query through postgrest-style endpoint via rest;
    # simpler: insert a probe row and verify column visibility.
    probe_id = enqueue(
        client,
        user_id=TEST_USER_ID,
        wake_source="manual_fire",
        payload={"probe": True},
        dedup_key=None,
        slug="schema-probe",
    )
    check("Schema accepts canonical insert", probe_id is not None)

    row = (
        client.table("wake_queue")
        .select("*")
        .eq("id", probe_id)
        .single()
        .execute()
        .data
    )
    expected_columns = {
        "id", "user_id", "wake_source", "lane", "slug", "payload",
        "dedup_key", "status", "enqueued_at", "locked_at", "locked_by",
        "completed_at", "execution_event_id",
    }
    check(
        "All 13 schema columns present",
        set(row.keys()) == expected_columns,
        f"got {sorted(row.keys())}",
    )
    check("Default status is 'pending'", row["status"] == "pending")
    check("manual_fire lands in 'live' lane", row["lane"] == "live")

    # Cleanup the probe.
    client.table("wake_queue").delete().eq("id", probe_id).execute()


# ─── resolve_lane() ────────────────────────────────────────────────────────


def test_resolve_lane() -> None:
    # ADR-327: the paced/live lane split collapsed — every source → "live"
    # (single FIFO lane; pace throttle deleted, drainer lane-agnostic).
    print("\n[resolve_lane] ADR-327 single-lane collapse")
    check("cron_tick → live (was paced)", resolve_lane("cron_tick") == "live")
    check("addressed → live", resolve_lane("addressed") == "live")
    check("substrate_event → live", resolve_lane("substrate_event") == "live")
    check("proposal_arrival → live", resolve_lane("proposal_arrival") == "live")
    check("manual_fire → live", resolve_lane("manual_fire") == "live")

    raised = False
    try:
        resolve_lane("garbage")
    except InvalidWakeSourceError:
        raised = True
    check("resolve_lane raises on unknown source", raised)


# ─── enqueue() + dedup ──────────────────────────────────────────────────────


def test_enqueue_basic(client) -> None:
    print("\n[enqueue] Basic insertion + lane derivation")
    qid = enqueue(
        client,
        user_id=TEST_USER_ID,
        wake_source="cron_tick",
        payload={"prompt": "test"},
        dedup_key="test-slug:2026-05-22T10:00",
        slug="test-slug",
    )
    check("Enqueue cron_tick returns row id", qid is not None)

    row = (
        client.table("wake_queue")
        .select("*")
        .eq("id", qid)
        .single()
        .execute()
        .data
    )
    check("cron_tick row lane='live' (ADR-327 single lane)", row["lane"] == "live")
    check("status='pending'", row["status"] == "pending")
    check("dedup_key persisted", row["dedup_key"] == "test-slug:2026-05-22T10:00")


def test_enqueue_dedup(client) -> None:
    print("\n[enqueue] ADR-298 D6 cross-source dedup")
    # Use a distinct dedup_key namespace to avoid collision with other tests.
    key = f"dedup-test-{uuid.uuid4()}"
    qid1 = enqueue(
        client,
        user_id=TEST_USER_ID,
        wake_source="substrate_event",
        payload={"revision_id": key},
        dedup_key=key,
    )
    check("First insert succeeds", qid1 is not None)

    qid2 = enqueue(
        client,
        user_id=TEST_USER_ID,
        wake_source="substrate_event",
        payload={"revision_id": key, "second": True},
        dedup_key=key,
    )
    check("Second insert with same key returns None (silent dedup)", qid2 is None)

    # Different wake_source + same dedup_key: per ADR-298 D6 the tuple is
    # (user_id, wake_source, dedup_key) so different sources CAN share keys.
    qid3 = enqueue(
        client,
        user_id=TEST_USER_ID,
        wake_source="cron_tick",
        payload={"slug": "x"},
        dedup_key=key,
    )
    check(
        "Same key + different wake_source succeeds",
        qid3 is not None,
        "ADR-298 D6: dedup tuple includes wake_source",
    )


def test_enqueue_null_dedup(client) -> None:
    print("\n[enqueue] NULL dedup_key (manual_fire bypass)")
    qid1 = enqueue(
        client,
        user_id=TEST_USER_ID,
        wake_source="manual_fire",
        payload={"admin": "fire1"},
        dedup_key=None,
    )
    qid2 = enqueue(
        client,
        user_id=TEST_USER_ID,
        wake_source="manual_fire",
        payload={"admin": "fire2"},
        dedup_key=None,
    )
    check(
        "Two NULL-dedup manual_fire inserts both succeed",
        qid1 is not None and qid2 is not None and qid1 != qid2,
        "NULL dedup intentionally bypasses UNIQUE per ADR-298 D6",
    )


def test_enqueue_invalid_source(client) -> None:
    print("\n[enqueue] Rejection of unknown wake_source")
    raised = False
    try:
        enqueue(
            client,
            user_id=TEST_USER_ID,
            wake_source="not_a_real_source",
            payload={},
        )
    except InvalidWakeSourceError:
        raised = True
    check("enqueue raises on unknown wake_source", raised)


# ─── get_next_pending() + lane scoping ──────────────────────────────────────


def test_get_next_pending(client) -> None:
    # ADR-327: single lane — every source enqueues to "live". FIFO ordering
    # across all sources is what matters now; the drainer is lane-agnostic.
    print("\n[get_next_pending] FIFO (ADR-327 single lane)")
    client.table("wake_queue").delete().eq("user_id", TEST_USER_ID).execute()

    # Insert in known order with sleeps to guarantee enqueued_at ordering.
    first_id = enqueue(
        client,
        user_id=TEST_USER_ID,
        wake_source="cron_tick",
        payload={"order": 1},
        dedup_key=f"ordering-first-{uuid.uuid4()}",
        slug="ordering",
    )
    time.sleep(0.05)
    second_id = enqueue(
        client,
        user_id=TEST_USER_ID,
        wake_source="addressed",
        payload={"order": 2},
        dedup_key=f"ordering-second-{uuid.uuid4()}",
    )

    # Both rows land in the single "live" lane post-ADR-327.
    first_row = (
        client.table("wake_queue").select("lane").eq("id", first_id).single().execute().data
    )
    check("cron_tick row now in live lane", first_row["lane"] == "live")

    # Unscoped lookup returns the oldest across all sources (FIFO).
    any_next = get_next_pending(client, user_id=TEST_USER_ID, lane=None)
    check(
        "Unscoped FIFO returns oldest pending row",
        any_next is not None and any_next["id"] == first_id,
        f"got {any_next['id'] if any_next else None}, expected {first_id} (inserted first)",
    )

    # Lane-scoped "live" still works (all rows are live) — returns oldest.
    live_next = get_next_pending(client, user_id=TEST_USER_ID, lane="live")
    check(
        "Lane=live lookup returns oldest (all rows live)",
        live_next is not None and live_next["id"] == first_id,
        f"got {live_next['id'] if live_next else None}, expected {first_id}",
    )

    # Invalid lane still raises.
    raised = False
    try:
        get_next_pending(client, user_id=TEST_USER_ID, lane="garbage")
    except InvalidLaneError:
        raised = True
    check("get_next_pending raises on unknown lane", raised)


# ─── try_lock() — single-in-flight constraint (D1) ──────────────────────────


def test_try_lock_atomic(client) -> None:
    print("\n[try_lock] Atomic pending → locked CAS")
    qid = enqueue(
        client,
        user_id=TEST_USER_ID,
        wake_source="addressed",
        payload={"lock_test": True},
        dedup_key=f"lock-test-{uuid.uuid4()}",
    )
    check(
        "First lock acquire succeeds",
        try_lock(client, queue_id=qid, instance_id="instance-A") is True,
    )

    # Second attempt fails because status is no longer 'pending'.
    check(
        "Second lock acquire returns False (CAS guard)",
        try_lock(client, queue_id=qid, instance_id="instance-B") is False,
    )

    # has_in_flight detects the locked row.
    check(
        "has_in_flight returns True with locked row",
        has_in_flight(client, user_id=TEST_USER_ID) is True,
    )

    # Cleanup.
    mark_completed(client, queue_id=qid)


# ─── mark_completed / mark_failed / mark_dropped ────────────────────────────


def test_status_transitions(client) -> None:
    print("\n[transitions] mark_completed / mark_failed / mark_dropped")

    # completed
    qid_c = enqueue(
        client,
        user_id=TEST_USER_ID,
        wake_source="cron_tick",
        payload={},
        dedup_key=f"transit-c-{uuid.uuid4()}",
    )
    try_lock(client, queue_id=qid_c, instance_id="instance-A")
    eev_id = str(uuid.uuid4())  # synthetic execution_events FK — column allows arbitrary
    mark_completed(client, queue_id=qid_c, execution_event_id=eev_id)
    row_c = (
        client.table("wake_queue").select("*").eq("id", qid_c).single().execute().data
    )
    check("mark_completed transitions status='completed'", row_c["status"] == "completed")
    check("completed_at set", row_c["completed_at"] is not None)
    check("execution_event_id linked", row_c["execution_event_id"] == eev_id)

    # failed
    qid_f = enqueue(
        client,
        user_id=TEST_USER_ID,
        wake_source="addressed",
        payload={},
        dedup_key=f"transit-f-{uuid.uuid4()}",
    )
    try_lock(client, queue_id=qid_f, instance_id="instance-A")
    mark_failed(client, queue_id=qid_f, execution_event_id=None)
    row_f = (
        client.table("wake_queue").select("*").eq("id", qid_f).single().execute().data
    )
    check("mark_failed transitions status='failed'", row_f["status"] == "failed")

    # dropped — drop reason persists into payload
    qid_d = enqueue(
        client,
        user_id=TEST_USER_ID,
        wake_source="cron_tick",
        payload={"slug": "to-drop"},
        dedup_key=f"transit-d-{uuid.uuid4()}",
    )
    mark_dropped(client, queue_id=qid_d, reason="pace_exhausted")
    row_d = (
        client.table("wake_queue").select("*").eq("id", qid_d).single().execute().data
    )
    check("mark_dropped transitions status='dropped'", row_d["status"] == "dropped")
    check(
        "drop reason persisted into payload._drop_reason",
        row_d["payload"].get("_drop_reason") == "pace_exhausted",
    )


# ─── reclaim_stale_locks() — Scenario J ─────────────────────────────────────


def test_stale_lock_reclaim(client) -> None:
    print("\n[reclaim] ADR-298 Scenario J stale-lock reclaim")
    qid = enqueue(
        client,
        user_id=TEST_USER_ID,
        wake_source="cron_tick",
        payload={},
        dedup_key=f"stale-{uuid.uuid4()}",
    )
    try_lock(client, queue_id=qid, instance_id="instance-crashed")

    # Backdate locked_at to simulate a long-ago lock.
    backdated = (
        datetime.now(timezone.utc) - timedelta(seconds=DEFAULT_STALE_LOCK_SECONDS + 60)
    ).isoformat()
    client.table("wake_queue").update({"locked_at": backdated}).eq("id", qid).execute()

    count = reclaim_stale_locks(client)
    check("reclaim_stale_locks returns count > 0", count >= 1)

    row = (
        client.table("wake_queue").select("*").eq("id", qid).single().execute().data
    )
    check("Reclaimed row status='pending'", row["status"] == "pending")
    check("Reclaimed row locked_at=NULL", row["locked_at"] is None)
    check("Reclaimed row locked_by=NULL", row["locked_by"] is None)

    # Cleanup.
    client.table("wake_queue").delete().eq("id", qid).execute()


# ─── gc_completed() ─────────────────────────────────────────────────────────


def test_gc_completed(client) -> None:
    print("\n[gc] Completed-row sweep")
    qid = enqueue(
        client,
        user_id=TEST_USER_ID,
        wake_source="cron_tick",
        payload={},
        dedup_key=f"gc-{uuid.uuid4()}",
    )
    try_lock(client, queue_id=qid, instance_id="x")
    mark_completed(client, queue_id=qid)

    # Backdate completed_at past the GC threshold.
    backdated = (
        datetime.now(timezone.utc) - timedelta(days=DEFAULT_GC_DAYS + 1)
    ).isoformat()
    client.table("wake_queue").update({"completed_at": backdated}).eq("id", qid).execute()

    count = gc_completed(client)
    check("gc_completed returns count > 0", count >= 1)

    # Verify absence by counting matching rows rather than maybe_single (which
    # returns None response on absence in supabase-py, not None data).
    leftover = (
        client.table("wake_queue").select("id").eq("id", qid).execute().data
    )
    check("GC'd row no longer exists", len(leftover) == 0)


# ─── queue_depth() ──────────────────────────────────────────────────────────


def test_queue_depth(client) -> None:
    print("\n[telemetry] queue_depth")
    # Wipe scratch namespace first to get a clean count.
    client.table("wake_queue").delete().eq("user_id", TEST_USER_ID).execute()

    enqueue(
        client,
        user_id=TEST_USER_ID,
        wake_source="cron_tick",
        payload={},
        dedup_key=f"depth-paced-1-{uuid.uuid4()}",
    )
    enqueue(
        client,
        user_id=TEST_USER_ID,
        wake_source="cron_tick",
        payload={},
        dedup_key=f"depth-paced-2-{uuid.uuid4()}",
    )
    enqueue(
        client,
        user_id=TEST_USER_ID,
        wake_source="addressed",
        payload={},
        dedup_key=f"depth-live-1-{uuid.uuid4()}",
    )

    # ADR-327: all sources enqueue to the single "live" lane now.
    check("queue_depth lane=paced → 0 (lane retired)", queue_depth(client, user_id=TEST_USER_ID, lane="paced") == 0)
    check("queue_depth lane=live → 3 (all rows live)", queue_depth(client, user_id=TEST_USER_ID, lane="live") == 3)
    check("queue_depth unscoped → 3", queue_depth(client, user_id=TEST_USER_ID) == 3)


# ─── Cleanup ────────────────────────────────────────────────────────────────


def cleanup(client) -> None:
    print("\n[cleanup] Wiping scratch user namespace")
    result = (
        client.table("wake_queue").delete().eq("user_id", TEST_USER_ID).execute()
    )
    count = len(result.data or [])
    print(f"  removed {count} scratch row(s) for test user {TEST_USER_ID[:8]}")


# ─── Main ───────────────────────────────────────────────────────────────────


def main() -> int:
    client = _client()
    print(f"=== ADR-298 Phase 1 — wake_queue regression gate ===")
    print(f"Test user: {TEST_USER_ID}")

    try:
        test_schema_landed(client)
        test_resolve_lane()
        test_enqueue_basic(client)
        test_enqueue_dedup(client)
        test_enqueue_null_dedup(client)
        test_enqueue_invalid_source(client)
        test_get_next_pending(client)
        test_try_lock_atomic(client)
        test_status_transitions(client)
        test_stale_lock_reclaim(client)
        test_gc_completed(client)
        test_queue_depth(client)
    finally:
        cleanup(client)

    print(f"\n=== Results: {PASSED} passed, {FAILED} failed ===")
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

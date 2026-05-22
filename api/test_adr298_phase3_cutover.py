"""ADR-298 Phase 3 — cutover regression gate.

Asserts:
- submit_wake_proposal enqueues to wake_queue (does NOT invoke Reviewer
  inline). Returns receipt with queue_id + lane.
- Per-source dedup_key derivation is correct:
    cron_tick      → "<slug>:<minute-iso>"
    substrate_event → revision_id
    proposal_arrival → proposal_id
    manual_fire    → NULL (intentional bypass)
- Lane derivation: cron_tick→paced; rest→live.
- Silent dedup: re-enqueue of same key returns {success:True, dedup:True},
  no second row.
- addressed source raises ValueError (correct usage forces SSE entry).
- stream_addressed_wake enqueues then would acquire lock (we don't exercise
  the full Reviewer body in this gate — covered by integration tests +
  production canary).
- wake_drainer.drain_can_acquire_for_user works with locked vs unlocked.
- wake_drainer.paced_lane_eligible_to_drain returns True when no pace.yaml.
- The scheduler's drain wiring imports cleanly.
- ADR-261 D3 amendment banner present.

Run: .venv/bin/python api/test_adr298_phase3_cutover.py
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from pathlib import Path

_API_ROOT = Path(__file__).resolve().parent
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

_REPO_ROOT = _API_ROOT.parent
from dotenv import load_dotenv  # noqa: E402
load_dotenv(_REPO_ROOT / ".env")

from supabase import create_client  # noqa: E402


TEST_USER_ID = str(uuid.uuid4())


def _client():
    return create_client(
        os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"],
    )


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


# ─── submit_wake_proposal — enqueue contract ────────────────────────────────


def test_submit_cron_tick(client) -> None:
    print("\n[submit_wake_proposal] cron_tick enqueues")
    from services.recurrence import Recurrence
    from services.wake import submit_wake_proposal

    rec = Recurrence(
        slug=f"test-cron-{uuid.uuid4().hex[:6]}",
        schedule="0 5 * * *",
        prompt="Test prompt",
        mode="judgment",
    )

    async def run():
        return await submit_wake_proposal(
            client, TEST_USER_ID,
            source="cron_tick",
            payload={"recurrence": rec, "context": None},
        )

    result = asyncio.run(run())
    check("cron_tick returns success=True", result.get("success") is True, str(result))
    check("cron_tick lane='paced'", result.get("lane") == "paced", str(result))
    check("cron_tick yields queue_id", "queue_id" in result, str(result))

    # Verify the row landed with right shape.
    row = (
        client.table("wake_queue")
        .select("*")
        .eq("id", result["queue_id"])
        .single()
        .execute()
        .data
    )
    check("queued row status='pending'", row["status"] == "pending")
    check("queued row wake_source='cron_tick'", row["wake_source"] == "cron_tick")
    check("queued row lane='paced'", row["lane"] == "paced")
    check("queued row slug matches recurrence", row["slug"] == rec.slug)
    check(
        "queued row dedup_key includes slug",
        row["dedup_key"] and rec.slug in row["dedup_key"],
    )
    check(
        "queued row payload carries recurrence_data",
        row["payload"].get("recurrence_data", {}).get("slug") == rec.slug,
    )


def test_submit_substrate_event(client) -> None:
    print("\n[submit_wake_proposal] substrate_event enqueues with revision_id dedup")
    from services.wake import submit_wake_proposal

    revision_id = str(uuid.uuid4())
    hook = {"slug": "test-hook", "prompt": "Hook fired"}

    async def run():
        return await submit_wake_proposal(
            client, TEST_USER_ID,
            source="substrate_event",
            payload={
                "hook": hook,
                "path": "/workspace/context/test.md",
                "field_change": {"status": ["draft", "ready"]},
                "revision_id": revision_id,
            },
        )

    result = asyncio.run(run())
    check("substrate_event returns success=True", result.get("success") is True)
    check("substrate_event lane='live'", result.get("lane") == "live")

    row = (
        client.table("wake_queue")
        .select("*")
        .eq("id", result["queue_id"])
        .single()
        .execute()
        .data
    )
    check("dedup_key = revision_id", row["dedup_key"] == revision_id)
    check("slug = hook slug", row["slug"] == "test-hook")


def test_submit_proposal_arrival(client) -> None:
    print("\n[submit_wake_proposal] proposal_arrival enqueues with proposal_id dedup")
    from services.wake import submit_wake_proposal

    proposal_id = str(uuid.uuid4())

    async def run():
        return await submit_wake_proposal(
            client, TEST_USER_ID,
            source="proposal_arrival",
            payload={"proposal_row": {"id": proposal_id, "kind": "test"}},
        )

    result = asyncio.run(run())
    check("proposal_arrival returns success=True", result.get("success") is True)
    check("proposal_arrival lane='live'", result.get("lane") == "live")

    row = (
        client.table("wake_queue")
        .select("*")
        .eq("id", result["queue_id"])
        .single()
        .execute()
        .data
    )
    check("dedup_key = proposal_id", row["dedup_key"] == proposal_id)


def test_submit_manual_fire(client) -> None:
    print("\n[submit_wake_proposal] manual_fire enqueues with NULL dedup (intentional)")
    from services.recurrence import Recurrence
    from services.wake import submit_wake_proposal

    rec = Recurrence(
        slug=f"test-manual-{uuid.uuid4().hex[:6]}",
        schedule=None,
        prompt="Manual fire",
        mode="judgment",
    )

    async def run():
        return await submit_wake_proposal(
            client, TEST_USER_ID,
            source="manual_fire",
            payload={"recurrence": rec, "context": "manual test"},
        )

    result = asyncio.run(run())
    check("manual_fire success=True", result.get("success") is True)
    check("manual_fire lane='live'", result.get("lane") == "live")

    row = (
        client.table("wake_queue")
        .select("*")
        .eq("id", result["queue_id"])
        .single()
        .execute()
        .data
    )
    check("manual_fire dedup_key is NULL", row["dedup_key"] is None)

    # Re-fire — should land a fresh row (NULL bypass).
    result2 = asyncio.run(run())
    check("manual_fire allows duplicate (NULL dedup)", result2.get("success") is True)
    check("manual_fire second call returns new queue_id",
          result2.get("queue_id") != result.get("queue_id"))


def test_submit_silent_dedup(client) -> None:
    print("\n[submit_wake_proposal] silent dedup on duplicate revision_id")
    from services.wake import submit_wake_proposal

    revision_id = str(uuid.uuid4())
    hook = {"slug": "dedup-test", "prompt": "x"}
    payload = {
        "hook": hook,
        "path": "/x",
        "field_change": {},
        "revision_id": revision_id,
    }

    async def submit():
        return await submit_wake_proposal(
            client, TEST_USER_ID,
            source="substrate_event",
            payload=payload,
        )

    r1 = asyncio.run(submit())
    r2 = asyncio.run(submit())
    check("First submit returns queue_id", "queue_id" in r1)
    check("Second submit returns dedup=True", r2.get("dedup") is True, str(r2))
    check("Second submit returns success=True (silent)", r2.get("success") is True)


def test_submit_addressed_rejected(client) -> None:
    print("\n[submit_wake_proposal] addressed source raises (forces SSE entry)")
    from services.wake import submit_wake_proposal

    async def run():
        return await submit_wake_proposal(
            client, TEST_USER_ID,
            source="addressed",
            payload={},
        )

    raised = False
    try:
        asyncio.run(run())
    except ValueError:
        raised = True
    check("submit_wake_proposal raises ValueError on source='addressed'", raised)


# ─── Drainer helpers ────────────────────────────────────────────────────────


def test_drainer_helpers(client) -> None:
    print("\n[wake_drainer] helper contracts")
    from services.wake_drainer import (
        drain_can_acquire_for_user,
        instance_id,
        paced_lane_eligible_to_drain,
    )

    # Fresh user has no in-flight wakes.
    check(
        "drain_can_acquire_for_user=True with no locks",
        drain_can_acquire_for_user(client, TEST_USER_ID) is True,
    )

    # instance_id is a stable string.
    check("instance_id is non-empty string", isinstance(instance_id(), str) and bool(instance_id()))

    # No _pace.yaml in workspace → paced lane is eligible (no cap).
    eligible, reason = asyncio.run(paced_lane_eligible_to_drain(client, TEST_USER_ID))
    check(
        "paced lane eligible when no _pace.yaml authored",
        eligible is True,
        f"reason={reason}",
    )


def test_drain_consumes_pending(client) -> None:
    print("\n[wake_drainer] drain_next_for_user consumes pending row + advances status")
    from services.wake import submit_wake_proposal
    from services.recurrence import Recurrence
    from services.wake_drainer import drain_next_for_user

    # Wipe prior test scratch so FIFO drainer pulls the ROW WE JUST ENQUEUED,
    # not an older pending row from earlier tests in this run.
    client.table("wake_queue").delete().eq("user_id", TEST_USER_ID).execute()

    rec = Recurrence(
        slug=f"drain-consume-{uuid.uuid4().hex[:6]}",
        schedule="0 5 * * *",
        prompt="prompt",
        mode="mechanical",  # mechanical avoids Reviewer LLM cost in test
    )

    async def submit():
        return await submit_wake_proposal(
            client, TEST_USER_ID,
            source="cron_tick",
            payload={"recurrence": rec},
        )

    submit_result = asyncio.run(submit())
    queue_id = submit_result["queue_id"]

    # Drain. Mechanical-mode recurrences dispatch to _dispatch_mechanical
    # which parses @primitive directives — this prompt has no directive
    # so it'll fail gracefully but the row should transition out of
    # 'pending' (either to 'completed' or 'failed').
    async def drain():
        return await drain_next_for_user(client, TEST_USER_ID)

    drain_result = asyncio.run(drain())
    check("drain returns non-None result", drain_result is not None)

    # Verify row transitioned.
    row = (
        client.table("wake_queue")
        .select("status")
        .eq("id", queue_id)
        .single()
        .execute()
        .data
    )
    check(
        "row transitioned out of 'pending' after drain",
        row["status"] in ("completed", "failed"),
        f"status={row['status']}",
    )


# ─── ADR-261 D3 amendment banner ────────────────────────────────────────────


def test_adr261_amendment_banner() -> None:
    print("\n[doc] ADR-261 D3 amendment banner present")
    p = _REPO_ROOT / "docs" / "adr" / "ADR-261-recurrences-as-prompts.md"
    if not p.exists():
        check("ADR-261 file exists", False)
        return
    content = p.read_text()
    check(
        "ADR-261 D3 banner cites ADR-298",
        "AMENDED by ADR-298" in content,
    )
    check(
        "ADR-261 D3 banner explains single-lane reversal",
        "single-lane" in content.lower() and "reversed" in content.lower(),
    )


def test_scheduler_drain_wired() -> None:
    print("\n[scheduler] drain wiring is present")
    p = _API_ROOT / "jobs" / "unified_scheduler.py"
    content = p.read_text()
    check(
        "Scheduler imports drain_all_users_with_pending",
        "drain_all_users_with_pending" in content,
    )
    check(
        "Scheduler imports reclaim_stale_locks",
        "reclaim_stale_locks" in content,
    )
    check(
        "Scheduler calls the drainer after walker block",
        "ADR-298 Phase 3" in content and "wake_queue drain" in content.lower(),
    )


def test_stream_addressed_lock_acquire() -> None:
    print("\n[stream_addressed_wake] Option α lock-acquire wired")
    p = _API_ROOT / "services" / "wake.py"
    content = p.read_text()
    check(
        "stream_addressed_wake enqueues via wake_queue",
        "_wq_enqueue" in content,
    )
    check(
        "stream_addressed_wake acquires lock via wake_queue.try_lock",
        "_wq_try_lock" in content,
    )
    check(
        "stream_addressed_wake releases lock via mark_completed/mark_failed",
        "_wq_mark_completed" in content and "_wq_mark_failed" in content,
    )
    check(
        "stream_addressed_wake emits 'queued' progress event on contention",
        '"queued"' in content,
    )


# ─── Cleanup ────────────────────────────────────────────────────────────────


def cleanup(client) -> None:
    print("\n[cleanup] Wiping scratch namespace")
    result = (
        client.table("wake_queue").delete().eq("user_id", TEST_USER_ID).execute()
    )
    print(f"  removed {len(result.data or [])} scratch row(s)")


# ─── Main ───────────────────────────────────────────────────────────────────


def main() -> int:
    print("=== ADR-298 Phase 3 cutover regression gate ===")
    print(f"Test user: {TEST_USER_ID}")

    client = _client()
    try:
        test_submit_cron_tick(client)
        test_submit_substrate_event(client)
        test_submit_proposal_arrival(client)
        test_submit_manual_fire(client)
        test_submit_silent_dedup(client)
        test_submit_addressed_rejected(client)
        test_drainer_helpers(client)
        test_drain_consumes_pending(client)
        test_adr261_amendment_banner()
        test_scheduler_drain_wired()
        test_stream_addressed_lock_acquire()
    finally:
        cleanup(client)

    print(f"\n=== Results: {PASSED} passed, {FAILED} failed ===")
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

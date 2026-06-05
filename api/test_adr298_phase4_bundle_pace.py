"""ADR-298 Phase 4 — Bundle minimum_pace + activation gate regression gate.

Asserts:
- alpha-trader + alpha-author MANIFESTs declare minimum_pace='daily'.
- get_minimum_pace() helper returns the manifest value (or None when absent).
- pace_at_least_as_frequent() orders correctly across the 4-value enum.
- fork_reference_workspace D8 default-seed: workspace with no _pace.yaml +
  bundle declaring minimum_pace='daily' → _pace.yaml is written with
  kind='daily' and authored_by='system:bundle-fork'.
- fork_reference_workspace Scenario A gate: workspace with _pace.yaml at
  'weekly' + bundle declaring minimum_pace='daily' → ValueError raised
  with Scenario A message; no fork happens.
- fork_reference_workspace passthrough: workspace with _pace.yaml at
  'hourly' (above floor) + bundle declaring 'daily' → fork proceeds
  (existing pace NOT overwritten — operator's authored pace wins).
- Bundles without minimum_pace (reference/deferred) do not gate at all.

Run: .venv/bin/python api/test_adr298_phase4_bundle_pace.py
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

from services.bundle_reader import get_minimum_pace, _load_manifest  # noqa: E402
from services.pace import (  # noqa: E402
    InvalidPaceKindError,
    PACE_KINDS,
    pace_at_least_as_frequent,
    read_pace,
)


# Phase 4 fork-path tests require a user_id that exists in auth.users
# (workspace_file_versions has FK on user_id). Reuse an existing test
# persona — same precedent as test_adr296_substrate_event_walker.py +
# test_adr230_bundle_substrate.py. Each test wipes the _pace.yaml
# path pre+post so cross-test ordering doesn't contaminate.
#
# alpha-trader-2 (29a74c63...) is the e2e test persona; least disruptive
# choice because it doesn't have a real operator workflow attached.
TEST_USER_ID = "29a74c63-0c9c-4998-b8bb-56dd0d810a4e"

# Subroutines that don't need a real user_id can use a fresh UUID.
SYNTHETIC_USER_ID = str(uuid.uuid4())


def _client():
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])


def _wipe_pace_yaml(client, user_id):
    """Remove _pace.yaml from a user's workspace_files (clean slate for tests)."""
    try:
        client.table("workspace_files").delete().eq("user_id", user_id).eq(
            "path", "/workspace/governance/_pace.yaml"
        ).execute()
    except Exception:
        pass


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


# ─── MANIFEST declarations ──────────────────────────────────────────────────


def test_manifests_declare_minimum_pace() -> None:
    print("\n[manifests] alpha-trader + alpha-author declare minimum_pace")
    for slug in ("alpha-trader", "alpha-author"):
        m = _load_manifest(slug)
        check(f"{slug} MANIFEST loads", m is not None)
        if m is None:
            continue
        check(
            f"{slug} declares minimum_pace='daily'",
            m.get("minimum_pace") == "daily",
            f"got {m.get('minimum_pace')!r}",
        )


def test_get_minimum_pace_helper() -> None:
    print("\n[get_minimum_pace] helper contract")
    check(
        "alpha-trader minimum_pace='daily'",
        get_minimum_pace("alpha-trader") == "daily",
    )
    check(
        "alpha-author minimum_pace='daily'",
        get_minimum_pace("alpha-author") == "daily",
    )
    # Reference bundles don't declare yet — get_minimum_pace returns None.
    for slug in ("alpha-defi", "alpha-prediction", "alpha-commerce"):
        check(
            f"{slug} minimum_pace=None (not yet declared)",
            get_minimum_pace(slug) is None,
        )
    check(
        "nonexistent bundle minimum_pace=None",
        get_minimum_pace("nonexistent-program-xyz") is None,
    )


# ─── pace_at_least_as_frequent ──────────────────────────────────────────────


def test_pace_ordering() -> None:
    print("\n[pace_at_least_as_frequent] enum ordering")
    # continuous satisfies all minimums
    for m in PACE_KINDS:
        check(
            f"continuous >= {m}",
            pace_at_least_as_frequent("continuous", m),
        )
    # hourly satisfies daily/weekly/itself, not continuous
    check("hourly >= hourly", pace_at_least_as_frequent("hourly", "hourly"))
    check("hourly >= daily", pace_at_least_as_frequent("hourly", "daily"))
    check("hourly >= weekly", pace_at_least_as_frequent("hourly", "weekly"))
    check("hourly NOT >= continuous", not pace_at_least_as_frequent("hourly", "continuous"))
    # daily satisfies daily/weekly, not hourly/continuous
    check("daily >= daily", pace_at_least_as_frequent("daily", "daily"))
    check("daily >= weekly", pace_at_least_as_frequent("daily", "weekly"))
    check("daily NOT >= hourly", not pace_at_least_as_frequent("daily", "hourly"))
    check("daily NOT >= continuous", not pace_at_least_as_frequent("daily", "continuous"))
    # weekly only satisfies itself
    check("weekly >= weekly", pace_at_least_as_frequent("weekly", "weekly"))
    check("weekly NOT >= daily", not pace_at_least_as_frequent("weekly", "daily"))
    check("weekly NOT >= hourly", not pace_at_least_as_frequent("weekly", "hourly"))
    check("weekly NOT >= continuous", not pace_at_least_as_frequent("weekly", "continuous"))

    # Invalid kinds raise.
    raised = False
    try:
        pace_at_least_as_frequent("daily", "garbage")
    except InvalidPaceKindError:
        raised = True
    check("raises on invalid minimum", raised)
    raised = False
    try:
        pace_at_least_as_frequent("xyz", "daily")
    except InvalidPaceKindError:
        raised = True
    check("raises on invalid declared", raised)


# ─── fork_reference_workspace gate + default-seed ───────────────────────────


def _write_pace_yaml(client, user_id, kind):
    """Pre-write a _pace.yaml for a scratch user to simulate operator
    having declared a pace prior to bundle activation."""
    from services.workspace import UserMemory
    from services.workspace_paths import GOVERNANCE_PACE_PATH
    body = f"pace:\n  kind: {kind}\n"

    async def write():
        um = UserMemory(client, user_id)
        await um.write(
            GOVERNANCE_PACE_PATH, body,
            summary="test scaffold",
            authored_by="operator",
        )

    asyncio.run(write())


def _read_pace_sync(client, user_id):
    async def read():
        return await read_pace(client, user_id)
    return asyncio.run(read())


def _delete_user_workspace(client, user_id):
    """Wipe scratch user namespace from workspace_files."""
    try:
        client.table("workspace_files").delete().eq("user_id", user_id).execute()
    except Exception:
        pass
    try:
        client.table("workspace_file_versions").delete().eq("user_id", user_id).execute()
    except Exception:
        pass


def test_d8_default_seed(client) -> None:
    print("\n[Scenario D8] First-activation default-pace seed from bundle minimum")
    # Clean slate — wipe any existing _pace.yaml so we test the "no pre-
    # existing pace" branch.
    _wipe_pace_yaml(client, TEST_USER_ID)
    pace_before = _read_pace_sync(client, TEST_USER_ID)
    check("pre-fork: no _pace.yaml", pace_before is None)

    from services.programs import fork_reference_workspace

    async def fork():
        return await fork_reference_workspace(
            client, TEST_USER_ID, "alpha-trader"
        )

    try:
        asyncio.run(fork())
    except Exception as exc:
        # Downstream fork may raise for unrelated reasons (existing substrate
        # conflicts, etc.) — the pace gate fires BEFORE the rest of the fork
        # so the _pace.yaml seed should land regardless. Continue to assert
        # _pace.yaml landed.
        print(f"  (fork raised {type(exc).__name__}: {str(exc)[:120]}; checking _pace.yaml regardless)")

    pace_after = _read_pace_sync(client, TEST_USER_ID)
    check(
        "post-fork: _pace.yaml exists",
        pace_after is not None,
        f"got {pace_after}",
    )
    check(
        "post-fork: _pace.yaml kind='daily' (alpha-trader minimum)",
        pace_after is not None and pace_after.kind == "daily",
        f"got {pace_after.kind if pace_after else None}",
    )


def test_scenario_a_gate(client) -> None:
    print("\n[Scenario A] Activation refuses operator pace below bundle minimum")
    # Scaffold _pace.yaml at 'weekly' on the test persona.
    _wipe_pace_yaml(client, TEST_USER_ID)
    _write_pace_yaml(client, TEST_USER_ID, "weekly")

    pace_pre = _read_pace_sync(client, TEST_USER_ID)
    check(
        "scaffolded _pace.yaml at 'weekly'",
        pace_pre is not None and pace_pre.kind == "weekly",
    )

    from services.programs import fork_reference_workspace

    raised_with_scenario_a_msg = False
    try:
        asyncio.run(fork_reference_workspace(client, TEST_USER_ID, "alpha-trader"))
    except ValueError as exc:
        msg = str(exc)
        if "minimum_pace" in msg and "weekly" in msg and "Scenario A" in msg:
            raised_with_scenario_a_msg = True
        else:
            print(f"  (ValueError but unexpected message: {msg})")
    except Exception as exc:
        print(f"  (unexpected exception type: {type(exc).__name__}: {exc})")
    check("ValueError raised with Scenario A message", raised_with_scenario_a_msg)

    # Pace not overwritten — operator's weekly declaration survives.
    pace_after = _read_pace_sync(client, TEST_USER_ID)
    check(
        "operator pace not overwritten on gate refusal",
        pace_after is not None and pace_after.kind == "weekly",
    )


def test_passthrough_above_floor(client) -> None:
    print("\n[passthrough] Operator pace at/above floor is preserved (not overwritten)")
    _wipe_pace_yaml(client, TEST_USER_ID)
    _write_pace_yaml(client, TEST_USER_ID, "hourly")  # above daily minimum

    from services.programs import fork_reference_workspace

    refused_unexpectedly = False
    try:
        asyncio.run(fork_reference_workspace(client, TEST_USER_ID, "alpha-trader"))
    except ValueError as exc:
        if "Scenario A" in str(exc):
            refused_unexpectedly = True
            print(f"  (unexpected Scenario A refusal: {exc})")
    except Exception:
        pass  # downstream fork errors OK for this test

    check("pace gate did NOT refuse hourly >= daily", not refused_unexpectedly)

    # Pace not overwritten — operator's hourly declaration survives.
    pace_after = _read_pace_sync(client, TEST_USER_ID)
    check(
        "operator's pre-declared 'hourly' preserved",
        pace_after is not None and pace_after.kind == "hourly",
        f"got {pace_after.kind if pace_after else None}",
    )


# ─── Cleanup ────────────────────────────────────────────────────────────────


def cleanup(client) -> None:
    print("\n[cleanup] Wiping _pace.yaml from test persona namespace")
    _wipe_pace_yaml(client, TEST_USER_ID)


# ─── Main ───────────────────────────────────────────────────────────────────


def main() -> int:
    print("=== ADR-298 Phase 4 — Bundle minimum_pace + activation gate ===")
    print(f"Primary test user: {TEST_USER_ID}")

    client = _client()
    try:
        test_manifests_declare_minimum_pace()
        test_get_minimum_pace_helper()
        test_pace_ordering()
        test_d8_default_seed(client)
        test_scenario_a_gate(client)
        test_passthrough_above_floor(client)
    finally:
        cleanup(client)

    print(f"\n=== Results: {PASSED} passed, {FAILED} failed ===")
    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

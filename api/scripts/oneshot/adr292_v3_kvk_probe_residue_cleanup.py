"""ADR-292 v3 Fix 1B — kvk probe-residue hygiene cleanup.

Companion to the alpha-trader-2 e2e persona flip. Per the 2026-05-20 pre-e2e
readiness audit, kvk's workspace carries probe-residue from the 2026-05-20
warm-start + post-refusal-self-amendment-probe scenarios:

1. _operator_profile.md head is a Reviewer-edited revision from the
   post-refusal probe (02:27:12Z) — the ADR-295 D3 anti-pattern capitulation.
   Target revert: revision at 00:11:38Z (system:bundle-fork).

2. _money_truth.md has 5 probe-seeded revisions by operator-proxy:scenario-
   runner:acting-as-kvk. No real outcomes ever reconciled into this workspace.
   Target reset: remove probe content; the outcome reconciler will write
   genuine state on first natural fill.

3. standing_intent.md has 8 probe-driven revisions. Reset to a bootstrap-
   clean shape; the next natural Reviewer wake (signal-evaluation at 13:45Z)
   will rewrite from real substrate.

4. judgment_log.md has 10 entries — header + 9 probe-related decision blocks.
   Reset to header-only bootstrap; first natural Reviewer judgment rewrites it.

5. action_proposals — 8 probe-driven rows in pending/rejected_at_execution/
   rejected/etc. status. Cancel pending ones; leave terminal-status ones
   as historical artifact (they're already done — only the pending ones
   could surface as live work).

Per ADR-209 attribution discipline, cleanup = writing NEW revisions that
restore the pre-probe state, attributed `system:probe-cleanup`. Probe
revisions stay in the chain as immutable historical record.

Usage:
    cd /Users/macbook/yarnnn
    .venv/bin/python -m api.scripts.oneshot.adr292_v3_kvk_probe_residue_cleanup
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
API_ROOT = REPO_ROOT / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))


KVK_USER_ID = "2abf3f96-118b-4987-9d95-40f2d9be9a18"
CLEANUP_ACTOR = "system:probe-cleanup"

# Revision IDs identified by survey 2026-05-20T10:50Z. The
# _operator_profile.md target-revert revision is the second system:bundle-
# fork write (00:11:38Z) — content matches the pre-probe bundle copy. We
# look it up by created_at + authored_by below rather than hardcoding the
# UUID for robustness.

STANDING_INTENT_BOOTSTRAP = """---
as_of: pending-first-wake
horizon: pending-first-natural-wake
occupant: "ai:freddie-sonnet-v8"
---

# Standing Intent — alpha-trader Reviewer (post-cleanup bootstrap)

## What I'm watching for

_(empty — last operator-recognized state was probe-driven; this file was
reset by ADR-292 v3 Fix 1B kvk probe-residue cleanup on 2026-05-20.
First natural judgment-mode wake post-cleanup will populate this from
real substrate. See `/workspace/_shared/substrate-update-log.md` for
cleanup audit trail.)_

## What would change my next move

_(pending first natural wake)_

## Open questions to surface to operator

_(pending first natural wake)_
"""

JUDGMENT_LOG_BOOTSTRAP = """# Review — Judgment Log

Append-only log of every operation-shaping judgment moment in this workspace.
Newest entries at the bottom. Two entry kinds:

- `--- decision ---` blocks record proposal verdicts (approve / reject /
  defer) from the proposal-arrival reactive path.
- `--- material-outcome ---` blocks record recurrence-fire wakes that
  produced operation-shaping outcomes (ProposeAction, Schedule
  create/update/archive, WriteFile to operator-canon, Clarify alert, or
  meta-level verdict). Routine stand-downs leave no entry here — their
  existence is captured in execution_events + the feed narrative.

Written by the Reviewer layer (ADR-194 v2 + ADR-281 §5). The Reviewer
itself does NOT WriteFile to this path directly — infrastructure renders
entries from the Reviewer's structured ReturnVerdict output (single-writer
contract per ADR-281 §5.D2). See `/workspace/persona/IDENTITY.md` for the
Reviewer's identity and `/workspace/persona/principles.md` for the declared
review framework.

<!-- 2026-05-20T11:00Z — this file was reset to header-only by ADR-292 v3
     Fix 1B kvk probe-residue cleanup. Prior probe-related decision blocks
     (warm-start scenarios + post-refusal-self-amendment-probe) remain in
     the workspace_file_versions revision chain as immutable historical
     record per ADR-209. First natural Reviewer judgment post-cleanup
     appends below. -->
"""


async def run() -> int:
    from dotenv import load_dotenv  # type: ignore[import-not-found]
    load_dotenv(API_ROOT / ".env")

    import os
    from supabase import create_client  # type: ignore[import-not-found]
    from services.authored_substrate import list_revisions, read_revision
    from services.workspace import UserMemory

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    if not url or not key:
        print("error: SUPABASE_URL + SUPABASE_SERVICE_KEY must be set", file=sys.stderr)
        return 2

    client = create_client(url, key)
    um = UserMemory(client, KVK_USER_ID)

    print(f"ADR-292 v3 Fix 1B — kvk probe-residue cleanup\n")

    # ----- Step 1: revert _operator_profile.md to the pre-probe bundle-fork
    op_profile_path = "operation/trading/_operator_profile.md"
    print(f"--- Step 1: revert {op_profile_path} to pre-probe state ---")
    revs = list_revisions(client, user_id=KVK_USER_ID, path=f"/workspace/{op_profile_path}", limit=10)
    print(f"  {len(revs)} revisions in chain (newest first):")
    for r in revs:
        print(f"    • {r['created_at']} — {r['authored_by']} — {r['message'][:60]}…")
    # Find the most recent system:bundle-fork revision (the pre-probe head)
    target = next(
        (r for r in revs if r["authored_by"] == "system:bundle-fork"),
        None,
    )
    if not target:
        print("  ERROR: no system:bundle-fork revision found in chain — cannot revert")
        return 1
    print(f"  reverting to: {target['created_at']} ({target['authored_by']})")
    target_rev = read_revision(client, user_id=KVK_USER_ID, path=f"/workspace/{op_profile_path}", revision_id=target["id"])
    if not target_rev:
        print("  ERROR: target revision could not be read")
        return 1
    await um.write(
        op_profile_path,
        target_rev.content,
        summary="Revert to pre-probe bundle-fork state per ADR-292 v3 Fix 1B",
        authored_by=CLEANUP_ACTOR,
        message=(
            f"reverted to pre-probe revision {target['id']} ({target['authored_by']} "
            f"at {target['created_at']}); the intervening Reviewer-edited revision "
            f"from post-refusal-self-amendment-probe at 2026-05-20T02:27:12Z is preserved "
            f"in the workspace_file_versions chain as historical artifact per ADR-209"
        ),
    )
    print(f"  ✓ {op_profile_path} reverted to pre-probe bundle-fork content")
    print()

    # ----- Step 2: reset _money_truth.md
    mt_path = "operation/trading/_money_truth.md"
    print(f"--- Step 2: reset {mt_path} (no real outcomes reconciled yet) ---")
    # The outcome reconciler will write genuine state on first fill. Reset
    # to empty-state shape (frontmatter + brief body explaining cleanup).
    money_truth_clean = (
        "---\n"
        "rolling_30d_expectancy_R: 0.0\n"
        "rolling_30d_sample_size: 0\n"
        "rolling_90d_expectancy_R: 0.0\n"
        "rolling_90d_sample_size: 0\n"
        "by_signal: {}\n"
        "processed_event_keys: []\n"
        "last_reconciled: never\n"
        "---\n"
        "# Ground truth — kvk (alpha-trader instance of FOUNDATIONS Axiom 8)\n\n"
        "_No outcomes reconciled yet. This file is the canonical home for\n"
        "alpha-trader's instance of ground-truth substrate (per ADR-282).\n"
        "The outcome-reconciliation recurrence writes here at the first\n"
        "natural fill from the Alpaca paper-trading account._\n\n"
        "<!-- 2026-05-20T11:00Z — this file was reset by ADR-292 v3 Fix 1B\n"
        "     kvk probe-residue cleanup. Prior probe-seeded revisions from\n"
        "     warm-start + post-refusal scenarios are preserved in the\n"
        "     workspace_file_versions chain as immutable historical record\n"
        "     per ADR-209. The reconciler's first genuine write overwrites\n"
        "     this stub. -->\n"
    )
    await um.write(
        mt_path,
        money_truth_clean,
        summary="Reset money-truth substrate after probe-residue cleanup per ADR-292 v3 Fix 1B",
        authored_by=CLEANUP_ACTOR,
        message=(
            "reset _money_truth.md to empty-state shape; 5 prior probe-seeded "
            "revisions (operator-proxy:scenario-runner:acting-as-kvk, "
            "2026-05-20T01:06-02:25Z) preserved in revision chain as "
            "historical artifact; outcome reconciler writes here on first "
            "genuine fill"
        ),
    )
    print(f"  ✓ {mt_path} reset to empty-state shape")
    print()

    # ----- Step 3: reset standing_intent.md
    si_path = "persona/standing_intent.md"
    print(f"--- Step 3: reset {si_path} to bootstrap shape ---")
    await um.write(
        si_path,
        STANDING_INTENT_BOOTSTRAP,
        summary="Reset standing intent after probe-residue cleanup per ADR-292 v3 Fix 1B",
        authored_by=CLEANUP_ACTOR,
        message=(
            "reset standing_intent.md to bootstrap shape; 8 prior probe-driven "
            "Reviewer revisions (warm-start + post-refusal scenarios, "
            "2026-05-20T01:06-02:27Z) preserved in revision chain per ADR-209; "
            "next natural judgment-mode wake (signal-evaluation at 13:45Z) "
            "writes the first post-cleanup substantive standing intent"
        ),
    )
    print(f"  ✓ {si_path} reset to bootstrap")
    print()

    # ----- Step 4: reset judgment_log.md
    jl_path = "persona/judgment_log.md"
    print(f"--- Step 4: reset {jl_path} to header-only bootstrap ---")
    await um.write(
        jl_path,
        JUDGMENT_LOG_BOOTSTRAP,
        summary="Reset judgment log after probe-residue cleanup per ADR-292 v3 Fix 1B",
        authored_by=CLEANUP_ACTOR,
        message=(
            "reset judgment_log.md to header-only bootstrap; 10 prior probe-"
            "related decision blocks (warm-start + post-refusal scenarios, "
            "2026-05-20T01:33-02:27Z) preserved in revision chain per ADR-209; "
            "first natural Reviewer wake post-cleanup appends below the header"
        ),
    )
    print(f"  ✓ {jl_path} reset to header-only bootstrap")
    print()

    # ----- Step 5: cancel pending probe-driven action_proposals
    print(f"--- Step 5: cancel pending probe-driven action_proposals ---")
    pending = (
        client.table("action_proposals")
        .select("id, status, action_type, created_at")
        .eq("user_id", KVK_USER_ID)
        .eq("status", "pending")
        .order("created_at", desc=False)
        .execute()
    )
    pending_rows = pending.data or []
    print(f"  found {len(pending_rows)} pending proposals (all from probe scenarios pre-cleanup)")
    cancelled_count = 0
    for p in pending_rows:
        result = (
            client.table("action_proposals")
            .update({
                "status": "rejected",
                "execution_result": {
                    "outcome": "cancelled_during_cleanup",
                    "message": (
                        "Cancelled by ADR-292 v3 Fix 1B kvk probe-residue cleanup "
                        "on 2026-05-20. Proposal was created during a 2026-05-20 "
                        "warm-start or post-refusal-self-amendment-probe scenario; "
                        "post-cleanup state should not carry pending probe-driven "
                        "work into the e2e observation window. Reviewer's verdict "
                        "history preserved in revision chain per ADR-209."
                    ),
                },
            })
            .eq("id", p["id"])
            .execute()
        )
        if result.data:
            cancelled_count += 1
            print(f"    ✓ cancelled proposal {p['id']} (was pending, action={p['action_type']})")
    print(f"  cancelled {cancelled_count} of {len(pending_rows)} pending proposals")
    print()

    print("done. kvk's workspace post-cleanup state:")
    print("  - _operator_profile.md head = pre-probe bundle-fork content")
    print("  - _money_truth.md head = empty-state shape (reconciler will overwrite)")
    print("  - standing_intent.md head = bootstrap shape (next natural wake populates)")
    print("  - judgment_log.md head = header-only (next Reviewer judgment appends)")
    print(f"  - {cancelled_count} pending probe-driven proposals cancelled")
    print()
    print("All prior probe revisions preserved in workspace_file_versions per")
    print("ADR-209 (immutable historical record). The substrate-update-log will")
    print("get an explicit ADR-292 v3 Fix 1B cleanup entry on its next event.")
    return 0


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    return asyncio.run(run())


if __name__ == "__main__":
    sys.exit(main())

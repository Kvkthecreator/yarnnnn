"""Canary Phase 4 — ADR-299 operator-addressing email end-to-end validation.

Synthesizes the operator opt-in step (substrate-update + active: true flip)
via OperatorProxy.write_substrate per ADR-294 precedent (same pattern as
canary v4/v6/v7), then chains into the substrate-event canary on
governance-as-trust to fire the pre-ship-audit hook.

Expected chain:
  1. write_substrate to /workspace/context/_shared/_preferences.yaml —
     append `operator_notifications:` block with `pre_ship_audit_summary`
     entry active: true (the event-driven notification that fires on
     pre-ship-audit hook).
  2. write_substrate to /workspace/context/authored/governance-as-trust/profile.md —
     flip `status: ready_for_review → draft → ready_for_review` (same shape
     as canary v4) to trigger the pre-ship-audit hook walker.
  3. Wait for next scheduler tick (~1-5 min).
  4. Reviewer wakes with hook envelope → reads _preferences.yaml → sees
     operator_notifications: pre_ship_audit_summary active: true →
     composes audit verdict + decides to fire platform_email_send_to_operator
     with system Resend wire → email lands in operator inbox from
     noreply@yarnnn.com with Reply-To set to operator's auth.users.email.

Validates the full ADR-299 Phase 4 chain on the system Resend wire
(post-Discovery-note-2 correction). The L6 capital-execution branch on
alpha-author closes via the operator-addressing observability channel
without requiring audience-bearing capabilities or operator Resend OAuth.

See:
- ADR-299 Discovery note 2 (system Resend wire correction)
- docs/evaluations/2026-05-22-052244-l6-variant-f-clause-validation/
  (the L6 envelope this canary closes for alpha-author)
"""

from __future__ import annotations

import asyncio
import re
import sys
from datetime import datetime, timezone

# Make api/ importable when run from repo root or api/.
import os
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
API_DIR = os.path.abspath(os.path.join(THIS_DIR, "..", ".."))
if API_DIR not in sys.path:
    sys.path.insert(0, API_DIR)

from services.operator_proxy.client import OperatorProxy  # noqa: E402


PREFERENCES_PATH = "/workspace/context/_shared/_preferences.yaml"
CANARY_PROFILE_PATH = "/workspace/context/authored/governance-as-trust/profile.md"

# operator_notifications block to append. pre_ship_audit_summary is event-
# driven (fires when pre-ship-audit hook resolves); active: true makes it
# operator-approved per ADR-299 D4 "_preferences.yaml opt-in IS standing
# approval, NOT per-action AUTONOMY click."
OPERATOR_NOTIFICATIONS_BLOCK = """

# =============================================================================
# operator_notifications — operator-addressing email opt-ins (ADR-299)
# =============================================================================
# Synthesized by canary_phase4_operator_email.py per ADR-294 operator-proxy
# precedent. Pre-flips pre_ship_audit_summary to active: true to validate
# the ADR-299 Phase 4 chain end-to-end on the system Resend wire.

operator_notifications:
  - slug: daily_corpus_state_update
    description: "Daily morning email summarizing yesterday's audit verdicts, drafts pending review, voice-drift signals from the last 24h."
    cadence_hint: "Daily at 07:00 UTC (operator-tunable)"
    active: false

  - slug: pre_ship_audit_summary
    description: "Email sent immediately after a pre-ship-audit fires — operator gets the Reviewer's verdict (approve / defer / reject) + reasoning summary while context is fresh, so they can iterate quickly on a deferred draft."
    cadence_hint: "Event-driven — fires when pre-ship-audit hook resolves"
    active: true
"""


def _flip_status(content: str, new_value: str) -> str:
    """Rewrite the YAML frontmatter `status:` line on profile.md."""
    pattern = re.compile(r"^status:\s*\S+", re.MULTILINE)
    if not pattern.search(content):
        raise ValueError("No `status:` line found in profile.md frontmatter")
    return pattern.sub(f"status: {new_value}", content, count=1)


async def main() -> int:
    proxy = OperatorProxy.from_persona("yarnnn-author", caller="claude-opus-4-7")
    async with proxy:
        # =====================================================================
        # Phase 4 Step 1 — synthesize operator opt-in
        # =====================================================================
        print("=== Phase 4 Step 1 — synthesize operator opt-in ===")
        existing_prefs = await proxy.read_file(PREFERENCES_PATH)
        if existing_prefs is None:
            print(f"FATAL: {PREFERENCES_PATH} not found on yarnnn-author")
            return 1

        if "operator_notifications:" in existing_prefs:
            print(f"[T0a] _preferences.yaml ALREADY has operator_notifications: block — skipping append (rerun-safe)")
            # If already present, ensure pre_ship_audit_summary is active.
            # Simplest path: overwrite with the canonical block to be sure.
            # For now: trust prior write + check pre_ship_audit_summary state.
            if "pre_ship_audit_summary" not in existing_prefs:
                print(f"     but pre_ship_audit_summary not in existing block — would need merge logic. Aborting safely; please inspect manually.")
                return 1
            print(f"     existing block content (first 500 chars):")
            print(existing_prefs[existing_prefs.index("operator_notifications:"):][:500])
        else:
            new_prefs = existing_prefs.rstrip() + OPERATOR_NOTIFICATIONS_BLOCK
            write1 = await proxy.write_substrate(
                path=PREFERENCES_PATH,
                content=new_prefs,
                message=(
                    "canary phase 4 — synthesize operator opt-in: append "
                    "operator_notifications block with pre_ship_audit_summary "
                    "active: true. Per ADR-294 operator-proxy precedent + "
                    "ADR-299 Phase 4 validation."
                ),
            )
            print(f"[T1] Write 1 (preferences opt-in) fired @ {datetime.now(timezone.utc).isoformat()}")
            print(f"     revision_id: {write1['revision_id']}")
            print(f"     authored_by: {write1['authored_by']}")

        # =====================================================================
        # Phase 4 Step 2 — fire substrate-event canary on governance-as-trust
        # =====================================================================
        print()
        print("=== Phase 4 Step 2 — fire substrate-event canary on governance-as-trust ===")
        baseline = await proxy.read_file(CANARY_PROFILE_PATH)
        if baseline is None:
            print(f"FATAL: {CANARY_PROFILE_PATH} not found")
            return 1
        print(f"[T2a] canary baseline status: {_extract_status(baseline)}")

        # Write 2 — flip to draft (priming)
        priming = _flip_status(baseline, "draft")
        write2 = await proxy.write_substrate(
            path=CANARY_PROFILE_PATH,
            content=priming,
            message="canary phase 4 — Write 2: status ready_for_review → draft (priming flip)",
        )
        now2 = datetime.now(timezone.utc).isoformat()
        print(f"[T2] Write 2 (priming) fired @ {now2}")
        print(f"     revision_id: {write2['revision_id']}")

        # Write 3 — flip back to ready_for_review (THE canary transition)
        final = _flip_status(priming, "ready_for_review")
        write3 = await proxy.write_substrate(
            path=CANARY_PROFILE_PATH,
            content=final,
            message="canary phase 4 — Write 3: status draft → ready_for_review (CANARY transition — fires pre-ship-audit hook)",
        )
        now3 = datetime.now(timezone.utc).isoformat()
        print(f"[T3] Write 3 (CANARY transition) fired @ {now3}")
        print(f"     revision_id: {write3['revision_id']}")
        print()
        print("=== Canary fired ===")
        print(f"Expected Reviewer wake within ~1-5 min of {now3}.")
        print(f"Watch:")
        print(f"  wake_queue WHERE created_at > '{now3}' AND dedup_key = '{write3['revision_id']}'")
        print(f"  execution_events WHERE user_id='<yarnnn-author>' AND created_at > '{now3}'")
        print(f"  notifications WHERE user_id='<yarnnn-author>' AND channel='email' (system Resend wire)")
        print()
        print(f"Expected Reviewer behavior:")
        print(f"  1. Read pre-ship-audit hook envelope (profile.md status transition)")
        print(f"  2. Read _preferences.yaml; see operator_notifications: pre_ship_audit_summary active: true")
        print(f"  3. Compose audit verdict on governance-as-trust draft")
        print(f"  4. Fire platform_email_send_to_operator(subject, html) via system Resend wire")
        print(f"  5. Email lands in operator inbox from noreply@yarnnn.com")
        print(f"  6. Reply-To pinned to operator's auth.users.email so reply lands in their inbox")
        return 0


def _extract_status(content: str) -> str | None:
    m = re.search(r"^status:\s*(\S+)", content, flags=re.MULTILINE)
    return m.group(1) if m else None


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

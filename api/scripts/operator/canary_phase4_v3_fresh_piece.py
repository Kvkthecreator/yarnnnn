"""Canary Phase 4 v3 — fresh-piece scenario to trigger email-worthy path.

Canary v2's result was Reviewer-correctly-judging-no-email-needed because
the substrate-event flip was on a previously-approved piece (governance-as-
trust) with unchanged content. The Reviewer (correctly) judged it as a
"non-material re-audit" and stood down without firing the email — the
notification opt-in description says "operator gets the Reviewer's verdict
+ reasoning summary while context is fresh, so they can iterate quickly
on a deferred draft," which doesn't apply to a re-audit of unchanged content.

v3 seeds a FRESH piece (new slug, new content, never audited before) with
intentional voice-quality issues so the Reviewer has a real verdict to
surface (defer with directive). The email-worthy path SHOULD trigger.

Operator opt-in (operator_notifications.pre_ship_audit_summary active: true)
still active from canary v1 (revision f02d7c7b on _preferences.yaml).
_hooks.yaml structural binding still active from canary v2 (revision
8195faee). v3 only needs to seed + flip the fresh piece.

If the email STILL doesn't fire after v3, the failure mode is either:
  - Reviewer-level: the corrected hook prompt + opt-in doesn't actually
    teach the Reviewer to call platform_email_send_to_operator
  - Tool-level: platform_email_send_to_operator isn't in the Reviewer's
    surface (no-wire-gate resolution branch bug)
  - Wire-level: handler reaches Resend but Resend HTTP fails silently
"""

from __future__ import annotations

import asyncio
import re
import sys
from datetime import datetime, timezone

import os
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
API_DIR = os.path.abspath(os.path.join(THIS_DIR, "..", ".."))
if API_DIR not in sys.path:
    sys.path.insert(0, API_DIR)

from services.operator_proxy.client import OperatorProxy  # noqa: E402


FRESH_PIECE_SLUG = "phase4-canary-v3-test-piece"
FRESH_PIECE_DIR = f"/workspace/operation/authored/{FRESH_PIECE_SLUG}"
PROFILE_PATH = f"{FRESH_PIECE_DIR}/profile.md"
CONTENT_PATH = f"{FRESH_PIECE_DIR}/content.md"


# Profile in DRAFT state initially (so canary flip to ready_for_review fires hook)
PROFILE_DRAFT = """---
title: "Phase 4 Canary v3 — Test Piece"
slug: phase4-canary-v3-test-piece
type: essay
status: draft
voice: founder-prose
created_at: 2026-05-24T05:56:00Z
ship_self_check: pending
---

# Phase 4 Canary v3 Test Piece

Auto-seeded by canary_phase4_v3_fresh_piece.py for ADR-299 Phase 4
validation. Intentional voice-quality issues are present so the
Reviewer has material to surface via the operator_notifications email
opt-in. See docs/evaluations/2026-05-24-054214-adr299-phase4-canary-red/
for the test arc this completes.
"""

# Content with INTENTIONAL voice issues — list-of-three opener, hedge stack,
# "It's worth noting" construction, intensifier adverb, "in conclusion"
# closer. These should give the Reviewer something to defer with directive.
CONTENT_DRAFT = """# Why YARNNN's Reviewer Architecture Matters

There are three things, three core principles, three load-bearing
ideas that make YARNNN's Reviewer architecture genuinely fascinating.

It's worth noting that the Reviewer is, I think, perhaps the most
critical component of the system. The Reviewer arguably embodies
what could potentially be called the operator's standing intent in
a way that is truly extraordinary.

The architecture is incredibly powerful. It enables operators to
effectively delegate decision-making in ways that absolutely
revolutionize how autonomous systems can work in practice.

In conclusion, the Reviewer pattern represents a paradigm shift
in how we think about autonomous agent systems. Let's dive deeper
into what makes this so transformative.
"""


def _flip_status(content: str, new_value: str) -> str:
    pattern = re.compile(r"^status:\s*\S+", re.MULTILINE)
    if not pattern.search(content):
        raise ValueError("No `status:` line found in profile.md frontmatter")
    return pattern.sub(f"status: {new_value}", content, count=1)


async def main() -> int:
    proxy = OperatorProxy.from_persona("yarnnn-author", caller="claude-opus-4-7")
    async with proxy:
        # =====================================================================
        # Step 1 — Seed fresh piece (profile.md + content.md) in DRAFT state
        # =====================================================================
        print("=== Step 1 — Seed fresh piece ===")
        existing = await proxy.read_file(PROFILE_PATH)
        if existing is not None:
            print(f"[T0] {PROFILE_PATH} already exists. Re-seeding for clean canary state.")

        write1 = await proxy.write_substrate(
            path=PROFILE_PATH,
            content=PROFILE_DRAFT,
            message=(
                "canary phase 4 v3 — seed fresh piece profile.md (draft state). "
                "Test piece for substrate-event hook trigger; intentional voice "
                "issues in content.md. Per ADR-294 operator-proxy precedent."
            ),
        )
        print(f"[T1] profile.md seeded @ {datetime.now(timezone.utc).isoformat()}")
        print(f"     revision_id: {write1['revision_id']}")

        write2 = await proxy.write_substrate(
            path=CONTENT_PATH,
            content=CONTENT_DRAFT,
            message=(
                "canary phase 4 v3 — seed content.md with INTENTIONAL voice issues "
                "(list-of-three opener, hedge stack, 'It's worth noting' construction, "
                "intensifier adverbs, 'in conclusion' closer). Reviewer should defer "
                "with directive on these specific anti-patterns."
            ),
        )
        print(f"[T2] content.md seeded @ {datetime.now(timezone.utc).isoformat()}")
        print(f"     revision_id: {write2['revision_id']}")

        # =====================================================================
        # Step 2 — Flip profile.md status: draft → ready_for_review (CANARY)
        # =====================================================================
        print()
        print("=== Step 2 — CANARY transition: draft → ready_for_review ===")
        # We just wrote profile.md with status: draft. Flip to ready_for_review.
        profile_after_write = await proxy.read_file(PROFILE_PATH)
        if profile_after_write is None:
            print("FATAL: profile.md not readable after seed write")
            return 1
        ready_for_review = _flip_status(profile_after_write, "ready_for_review")
        write3 = await proxy.write_substrate(
            path=PROFILE_PATH,
            content=ready_for_review,
            message=(
                "canary phase 4 v3 — CANARY transition: status draft → "
                "ready_for_review (fires pre-ship-audit hook on FRESH PIECE; "
                "Reviewer should defer with directive citing specific voice "
                "anti-patterns AND fire platform_email_send_to_operator since "
                "operator_notifications.pre_ship_audit_summary is active: true)"
            ),
        )
        now3 = datetime.now(timezone.utc).isoformat()
        print(f"[T3] CANARY transition fired @ {now3}")
        print(f"     revision_id: {write3['revision_id']}")
        print()
        print("=== Canary v3 fired ===")
        print(f"Expected Reviewer wake within ~1-5 min of {now3}.")
        print(f"Watch:")
        print(f"  wake_queue WHERE dedup_key = '{write3['revision_id']}'")
        print(f"  reviewer substrate writes — THIS time should include:")
        print(f"    - judgment_log.md with structured defect citations")
        print(f"    - standing_intent.md per discipline contract")
        print(f"  notifications WHERE channel='email' — THIS time SHOULD fire if")
        print(f"    operator_notifications.pre_ship_audit_summary active path works")
        print()
        print(f"Expected verdict: DEFER with directive (content has clear voice issues")
        print(f"  — list-of-three opener 'There are three things, three core principles,'")
        print(f"  — hedge stack 'I think, perhaps the most'")
        print(f"  — 'It's worth noting' construction")
        print(f"  — intensifiers 'genuinely fascinating', 'truly extraordinary',")
        print(f"    'incredibly powerful', 'absolutely revolutionize'")
        print(f"  — 'In conclusion,' closer)")
        return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

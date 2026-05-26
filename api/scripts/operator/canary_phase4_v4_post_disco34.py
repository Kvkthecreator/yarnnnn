"""Canary Phase 4 v4 — post-Discovery-3+4 validation.

Canary v3 (2026-05-25 04:13 UTC) produced a textbook REJECT verdict but
no email — root cause was Discovery 4 (REVIEWER_PRIMITIVES never included
platform_email_send_to_operator) + Discovery 3 (resolution path didn't
always-surface kernel-universal capabilities).

Both fixes shipped in commit 7147aa7, live on API + Scheduler since
2026-05-25 04:38:19 UTC. This v4 canary seeds a fresh test piece (new
slug to ensure substrate-event hook fires cleanly on the transition
guard) with intentional voice issues so the Reviewer renders a material
DEFER/REJECT verdict — and SHOULD now also fire
platform_email_send_to_operator since the tool is in its surface.

Operator opt-in state preserved from canary v1 (revision f02d7c7b on
_preferences.yaml). _hooks.yaml structural binding preserved from
canary v2 (revision 8195faee).

Expected outcome: judgment_log.md REJECT/DEFER + standing_intent.md
update + email lands in operator's inbox from noreply@yarnnn.com.
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


FRESH_PIECE_SLUG = "phase4-canary-v4-post-disco34"
FRESH_PIECE_DIR = f"/workspace/context/authored/{FRESH_PIECE_SLUG}"
PROFILE_PATH = f"{FRESH_PIECE_DIR}/profile.md"
CONTENT_PATH = f"{FRESH_PIECE_DIR}/content.md"


PROFILE_DRAFT = """---
title: "Phase 4 Canary v4 — Post-Discovery-3+4 Test Piece"
slug: phase4-canary-v4-post-disco34
type: essay
status: draft
voice: founder-prose
created_at: 2026-05-25T04:40:00Z
ship_self_check: pending
---

# Phase 4 Canary v4 — Post-Discovery-3+4 Test Piece

Auto-seeded by canary_phase4_v4_post_disco34.py for ADR-299 Phase 4
validation. Tests the cumulative correction chain (Discovery notes
1-4). Intentional voice-quality issues present so the Reviewer has
material to surface via operator_notifications email opt-in.

See docs/evaluations/2026-05-25-042346-adr299-always-surface-resolution/
findings.md for the discovery arc this canary closes.
"""

# Different intentional anti-patterns than v3 so the Reviewer's verdict
# is clearly about THIS piece (not reusing v3's reasoning)
CONTENT_DRAFT = """# The Future of Autonomous Agents Will Be Truly Revolutionary

There are several factors, several key drivers, several fundamental
forces that will inevitably shape the future of autonomous agent
systems. At the end of the day, we need to recognize that we're at
an absolutely pivotal moment in the evolution of how machines
collaborate with humans.

Let's dive into what makes this so transformative. It's worth noting,
I believe, that perhaps the most game-changing aspect of modern
agentic systems is their unprecedented capacity to genuinely
understand context in ways that traditional software simply cannot.

The implications are truly mind-blowing. These systems will
fundamentally revolutionize how we think about productivity,
collaboration, and indeed the very nature of work itself. They
absolutely represent a paradigm shift of monumental proportions.

In conclusion, we stand at the dawn of an entirely new era. The
question is not whether autonomous agents will transform every
industry — it's how quickly we can leverage their incredible
potential to unlock value at scale.
"""


def _flip_status(content: str, new_value: str) -> str:
    pattern = re.compile(r"^status:\s*\S+", re.MULTILINE)
    if not pattern.search(content):
        raise ValueError("No `status:` line found in profile.md frontmatter")
    return pattern.sub(f"status: {new_value}", content, count=1)


def _extract_status(content: str) -> str | None:
    m = re.search(r"^status:\s*(\S+)", content, flags=re.MULTILINE)
    return m.group(1) if m else None


async def main() -> int:
    proxy = OperatorProxy.from_persona("yarnnn-author", caller="claude-opus-4-7")
    async with proxy:
        # Step 1: seed fresh piece in DRAFT state
        print("=== Step 1 — Seed fresh piece (v4 slug) ===")
        write1 = await proxy.write_substrate(
            path=PROFILE_PATH,
            content=PROFILE_DRAFT,
            message=(
                "canary phase 4 v4 — seed fresh piece profile.md (draft state). "
                "Post-Discovery-3+4 validation; tool now in REVIEWER_PRIMITIVES."
            ),
        )
        print(f"[T1] profile.md seeded @ {datetime.now(timezone.utc).isoformat()}")
        print(f"     revision_id: {write1['revision_id']}")

        write2 = await proxy.write_substrate(
            path=CONTENT_PATH,
            content=CONTENT_DRAFT,
            message=(
                "canary phase 4 v4 — seed content.md with INTENTIONAL voice issues "
                "(list-of-three + 'at the end of the day' + 'absolutely pivotal' + "
                "intensifier adverbs + 'in conclusion'). Reviewer should reject."
            ),
        )
        print(f"[T2] content.md seeded @ {datetime.now(timezone.utc).isoformat()}")
        print(f"     revision_id: {write2['revision_id']}")

        # Step 2: flip profile.md status: draft → ready_for_review (CANARY)
        print()
        print("=== Step 2 — CANARY transition: draft → ready_for_review ===")
        profile_after_write = await proxy.read_file(PROFILE_PATH)
        if profile_after_write is None:
            print("FATAL: profile.md not readable after seed write")
            return 1
        ready_for_review = _flip_status(profile_after_write, "ready_for_review")
        write3 = await proxy.write_substrate(
            path=PROFILE_PATH,
            content=ready_for_review,
            message=(
                "canary phase 4 v4 — CANARY transition: status draft → "
                "ready_for_review (POST DISCOVERY 3+4 FIX — tool now in "
                "REVIEWER_PRIMITIVES; email SHOULD fire this time)"
            ),
        )
        now3 = datetime.now(timezone.utc).isoformat()
        print(f"[T3] CANARY transition fired @ {now3}")
        print(f"     revision_id: {write3['revision_id']}")
        print()
        print("=== Canary v4 fired ===")
        print(f"Expected Reviewer wake within ~1-5 min of {now3}.")
        print(f"Watch:")
        print(f"  wake_queue WHERE dedup_key = '{write3['revision_id']}'")
        print(f"  reviewer substrate writes (judgment_log.md + standing_intent.md)")
        print(f"  OPERATOR INBOX (kvkthecreator@gmail.com) — THIS time SHOULD fire")
        return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

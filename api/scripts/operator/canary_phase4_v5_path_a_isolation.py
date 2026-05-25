"""Canary Phase 4 v5 — Path A isolation test.

Canary v4 (2026-05-25 04:42 UTC) fired post-Discovery-3+4 deploy with
intentional voice issues and the Reviewer chose `stand_down` silently —
no judgment_log, no standing_intent, no email. 4 LLM rounds vs canary
v3's 10 (significantly less context-gathering before deciding).

ADR-299 Discovery 4 was REVERTED Path A in commit cd71930 (deployed
2026-05-25 05:11:09 UTC). `EMAIL_SEND_TO_OPERATOR_TOOL` removed from
`REVIEWER_PRIMITIVES`; tool count back to 21. Discovery 3's always-surface
fix in `get_platform_tools_for_capabilities` REMAINS in place (kernel-
universal capabilities still flow through the agent path for non-Reviewer
callers).

This v5 canary fires a fresh test piece (new slug to ensure substrate-event
hook fires cleanly on the transition guard) with the SAME intentional voice
issues as v4 so the Reviewer's verdict shift (or non-shift) isolates the
tool-perturbation variable.

Expected outcomes:
  - If v5 produces defer/reject + judgment_log + standing_intent writes
    (matching canary v3's behavior): hypothesis A confirmed — tool
    addition was perturbing Reviewer judgment toward stand_down.
  - If v5 still produces silent stand_down (matching canary v4):
    hypothesis B — prompt-coverage gap or other unidentified cause.
    Path A revert stays in place pending further investigation.

Operator opt-in state preserved from canary v1 (revision f02d7c7b on
_preferences.yaml). _hooks.yaml structural binding preserved from
canary v2 (revision 8195faee). Hook prompt unchanged.
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


FRESH_PIECE_SLUG = "phase4-canary-v5-path-a-isolation"
FRESH_PIECE_DIR = f"/workspace/context/authored/{FRESH_PIECE_SLUG}"
PROFILE_PATH = f"{FRESH_PIECE_DIR}/profile.md"
CONTENT_PATH = f"{FRESH_PIECE_DIR}/content.md"


PROFILE_DRAFT = """---
title: "Phase 4 Canary v5 — Path A Isolation Test"
slug: phase4-canary-v5-path-a-isolation
type: essay
status: draft
voice: founder-prose
created_at: 2026-05-25T05:15:00Z
ship_self_check: pending
---

# Phase 4 Canary v5 — Path A Isolation Test

Auto-seeded by canary_phase4_v5_path_a_isolation.py for ADR-299 Discovery
4 Path A validation (commit cd71930). Tests whether canary v4's silent
stand_down was caused by the 22nd tool being in the Reviewer's surface,
or by something else.

Same intentional voice-quality patterns as v4 (list-of-three openers,
"at the end of the day", "absolutely pivotal", intensifier adverbs,
"in conclusion"). With the smaller 21-tool surface, the Reviewer should
return to canary v3's defer/reject behavior + substrate writes.
"""

# IDENTICAL anti-pattern content as canary v4 so the only variable
# changing is the Reviewer's tool surface size (22 → 21)
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
        print("=== Step 1 — Seed fresh piece (v5 slug) ===")
        write1 = await proxy.write_substrate(
            path=PROFILE_PATH,
            content=PROFILE_DRAFT,
            message=(
                "canary phase 4 v5 — seed fresh piece profile.md (draft state). "
                "Path A isolation: same content as v4, smaller 21-tool Reviewer surface."
            ),
        )
        print(f"[T1] profile.md seeded @ {datetime.now(timezone.utc).isoformat()}")
        print(f"     revision_id: {write1['revision_id']}")

        write2 = await proxy.write_substrate(
            path=CONTENT_PATH,
            content=CONTENT_DRAFT,
            message=(
                "canary phase 4 v5 — seed content.md with IDENTICAL intentional voice "
                "issues as v4 (list-of-three + 'at the end of the day' + 'absolutely "
                "pivotal' + intensifier adverbs + 'in conclusion'). Same content; only "
                "variable that changed is REVIEWER_PRIMITIVES size (22 → 21)."
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
                "canary phase 4 v5 — CANARY transition: status draft → "
                "ready_for_review (PATH A ISOLATION — 21-tool Reviewer surface; "
                "expect defer/reject + substrate writes if hypothesis A holds)"
            ),
        )
        now3 = datetime.now(timezone.utc).isoformat()
        print(f"[T3] CANARY transition fired @ {now3}")
        print(f"     revision_id: {write3['revision_id']}")
        print()
        print("=== Canary v5 fired ===")
        print(f"Expected Reviewer wake within ~1-5 min of {now3}.")
        print(f"Watch:")
        print(f"  wake_queue WHERE dedup_key = '{write3['revision_id']}'")
        print(f"  execution_events WHERE wake_source='substrate_event' AND created_at > '{now3}'")
        print(f"  reviewer substrate writes (judgment_log.md + standing_intent.md)")
        print(f"  output token count vs v4 (v4=1577, v3=6139)")
        return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

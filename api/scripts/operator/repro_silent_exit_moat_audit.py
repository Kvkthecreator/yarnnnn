"""Repro — does the moat-thesis pre-ship-audit silent-exit REPRODUCE?

Hat-B developer-surface diagnostic for the §6 finding in
docs/evaluations/2026-05-30-054957-author-produce-corpus-piece/findings.md.

The original moat-thesis pre-ship-audit (execution_event 05:54:58, status=success,
tool_rounds=4) SILENT-EXITED via text_only_mid_loop — the model emitted the audit
verdict as a markdown text block ("## Pre-Ship Audit ### Rule 1: voice-fingerprint-
match...") instead of a ReturnVerdict tool call. The runtime synthesized stand_down
and broke. No verdict reached judgment_log.md.

This script re-fires the pre-ship-audit hook against the SAME piece to test whether
the silent-exit is STRUCTURAL (audit-shape-triggered, reproduces) or a ONE-OFF.

Mechanism: the pre-ship-audit hook (in /workspace/_hooks.yaml) matches
field_change {status: ready_for_review} on profile.md. The piece is currently
status: ready_for_review. To fire a fresh transition INTO that value, we flip
draft → ready_for_review (two revisions). The production scheduler walks hooks
~1-5 min later and drains the wake.

Net end-state: profile.md restored to status: ready_for_review (its current value).
No content change. The piece's substrate is otherwise untouched.

Confound check: judgment_log.md has ZERO moat entries (the original audit never
produced a verdict), so from the Reviewer's perspective this is a FIRST audit, not
a re-audit — the canary-v2 "non-material re-audit stand-down" confound does not apply.
"""

from __future__ import annotations

import asyncio
import os
import re
import sys
from datetime import datetime, timezone

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
API_DIR = os.path.abspath(os.path.join(THIS_DIR, "..", ".."))
if API_DIR not in sys.path:
    sys.path.insert(0, API_DIR)

from services.operator_proxy.client import OperatorProxy  # noqa: E402

PROFILE_PATH = "/workspace/context/authored/moat-thesis/profile.md"


def _flip_status(content: str, new_status: str) -> str:
    """Replace the frontmatter `status:` value. Raises if not found."""
    new, n = re.subn(
        r"(?m)^status:\s*\S+\s*$",
        f"status: {new_status}",
        content,
        count=1,
    )
    if n != 1:
        raise RuntimeError(f"expected exactly 1 status: line, replaced {n}")
    return new


async def main() -> int:
    async with OperatorProxy.from_persona("yarnnn-author", caller="claude") as proxy:
        original = await proxy.read_file(PROFILE_PATH)
        if original is None:
            print("FATAL: moat-thesis profile.md not readable")
            return 1

        cur = re.search(r"(?m)^status:\s*(\S+)\s*$", original)
        print(f"[T0] current status: {cur.group(1) if cur else '???'}")

        # Step 1 — flip to draft (sets up the transition INTO ready_for_review)
        draft = _flip_status(original, "draft")
        w1 = await proxy.write_substrate(
            path=PROFILE_PATH,
            content=draft,
            message="repro-silent-exit: status ready_for_review → draft (setup for fresh transition)",
        )
        now1 = datetime.now(timezone.utc).isoformat()
        print(f"[T1] flipped → draft @ {now1}  rev={w1['revision_id']}")

        # Step 2 — flip back to ready_for_review (FIRES the pre-ship-audit hook)
        ready = _flip_status(draft, "ready_for_review")
        w2 = await proxy.write_substrate(
            path=PROFILE_PATH,
            content=ready,
            message=(
                "repro-silent-exit: status draft → ready_for_review "
                "(FIRES pre-ship-audit hook; testing whether text_only_mid_loop "
                "silent-exit reproduces on this long-piece audit)"
            ),
        )
        now2 = datetime.now(timezone.utc).isoformat()
        print(f"[T2] flipped → ready_for_review (HOOK FIRED) @ {now2}  rev={w2['revision_id']}")
        print()
        print("=== Repro fired ===")
        print(f"Expected Reviewer pre-ship-audit wake within ~1-5 min of {now2}.")
        print(f"dedup_key to watch: {w2['revision_id']}")
        print()
        print("Watch for either outcome:")
        print("  SILENT-EXIT (reproduces, structural):")
        print("    - execution_events pre-ship-audit status=success, low tool_rounds")
        print("    - standing_intent.md authored_by=dispatcher:silent_exit_fallback")
        print("    - judgment_log.md STILL has zero moat entries")
        print("  COMPLETED (one-off):")
        print("    - judgment_log.md gains a moat-thesis verdict (approve/defer/reject)")
        print("    - profile.md pre_ship_audit_state set")
        return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

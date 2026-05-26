"""Canary v4 — Substrate-event reactive wake revalidation post-Option-D.

Fires two consecutive status flips on yarnnn-author's
`governance-as-trust/profile.md` frontmatter:
  Write 1: status: ready_for_review → draft
  Write 2: status: draft → ready_for_review  (this is the transition the walker fires on)

Both writes authored via operator-proxy per ADR-294 D2:
  authored_by = "operator-proxy:claude-opus-4-7:acting-as-yarnnn-author"

Then prints the wall-clock so the operator can correlate to the next
Scheduler tick (every minute on the Scheduler cron).

See: docs/evaluations/2026-05-21-044500-canary-v4-substrate-event-revalidation/PLAYBOOK.md
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


CANARY_PATH = "/workspace/context/authored/governance-as-trust/profile.md"


def _flip_status(content: str, new_value: str) -> str:
    """Rewrite the YAML frontmatter `status:` line."""
    pattern = re.compile(r"^status:\s*\S+", re.MULTILINE)
    if not pattern.search(content):
        raise ValueError("No `status:` line found in frontmatter")
    return pattern.sub(f"status: {new_value}", content, count=1)


async def main() -> int:
    proxy = OperatorProxy.from_persona("yarnnn-author", caller="claude-opus-4-7")
    async with proxy:
        # Step 0 — read baseline.
        baseline = await proxy.read_file(CANARY_PATH)
        if baseline is None:
            print(f"FATAL: file not found at {CANARY_PATH}")
            return 1
        print(f"[T0] baseline content length: {len(baseline)} bytes")
        print(f"[T0] baseline status: {_extract_status(baseline)}")

        # Write 1 — flip to draft.
        write1_content = _flip_status(baseline, "draft")
        write1 = await proxy.write_substrate(
            path=CANARY_PATH,
            content=write1_content,
            message="canary v4 — Write 1: status ready_for_review → draft (priming flip)",
        )
        now1 = datetime.now(timezone.utc).isoformat()
        print(f"[T1] Write 1 fired @ {now1}")
        print(f"     revision_id: {write1['revision_id']}")
        print(f"     authored_by: {write1['authored_by']}")
        print(f"     status: draft")

        # Write 2 — flip back to ready_for_review. THIS is the canary transition.
        write2_content = _flip_status(write1_content, "ready_for_review")
        write2 = await proxy.write_substrate(
            path=CANARY_PATH,
            content=write2_content,
            message="canary v4 — Write 2: status draft → ready_for_review (CANARY transition)",
        )
        now2 = datetime.now(timezone.utc).isoformat()
        print(f"[T2] Write 2 fired @ {now2}")
        print(f"     revision_id: {write2['revision_id']}")
        print(f"     authored_by: {write2['authored_by']}")
        print(f"     status: ready_for_review")
        print()
        print(f"Canary fired. Expected wake within ~1-2 min of {now2}.")
        print(f"Watch: wake_queue WHERE created_at > '{now2}'")
        print(f"       dedup_key = '{write2['revision_id']}'")
        return 0


def _extract_status(content: str) -> str | None:
    m = re.search(r"^status:\s*(\S+)", content, flags=re.MULTILINE)
    return m.group(1) if m else None


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

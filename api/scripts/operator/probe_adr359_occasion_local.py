"""ADR-359 §8 validation probe — LOCAL invoke (tests THIS working tree's code).

The deployed Render scheduler drains wake_queue with DEPLOYED code; to validate
the uncommitted ADR-359 implementation we must invoke the Reviewer INLINE with
local code. This script:

  1. writes the netflix-author probe substrate (funded/autonomous/empty corpus/
     declared weekly scene) — identical to the falsified heartbeat scenario,
  2. assembles the wake envelope via the EDITED freddie_envelope (occasion_fact),
  3. calls invoke_freddie() locally with the NEUTRAL situation-forward heartbeat
     prompt (the implementation is the only variable vs the FAIL baseline),
  4. prints the verdict + whether a content.md with prose was produced in-cycle.

PASS: a content.md under operation/.../content.md with real prose authored this
cycle (reviewer:* / via the loop), verdict names what was produced.
FAIL: stand_down / standing_intent-only / non_performance / deferral.

Usage: cd /Users/macbook/yarnnn && .venv/bin/python -m api.scripts.operator.probe_adr359_occasion_local
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
_API_ROOT = _THIS_DIR.parents[1]
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))
REPO_ROOT = _THIS_DIR.parents[2]

from dotenv import load_dotenv  # noqa: E402
load_dotenv(_API_ROOT / ".env.alpha-ops")
load_dotenv(REPO_ROOT / ".env")

USER_ID = "23cc7951-b6c7-471c-ac38-657d931db6f7"  # netflix-script-author

NEUTRAL_PROMPT = (
    "You are awake. You are the standing judgment for this operation.\n\n"
    "The substrate in your envelope is the operation's current state — your "
    "MANDATE and its Expected Output, your principles.md framework, the corpus "
    "under /workspace/operation/authored/, the outcomes and watches. Read what "
    "is true now and serve the mandate against it: do the work the operation "
    "needs from you this wake.\n\n"
    "This is not a task to interpret — it is a situation to act on. principles.md "
    "is your framework; the frame owns how you close."
)


async def main() -> int:
    from services.supabase import get_service_client
    from services.freddie_envelope import load_freddie_governance_envelope
    from agents.freddie_agent import invoke_freddie

    client = get_service_client()

    # --- count content.md BEFORE (so we can detect in-cycle production) ---
    before = (
        client.table("workspace_files")
        .select("path", count="exact")
        .eq("user_id", USER_ID)
        .like("path", "/workspace/operation/%/content.md")
        .execute()
    )
    n_before = before.count if before.count is not None else len(before.data or [])
    print(f"[probe] content.md count BEFORE: {n_before}")

    # --- assemble envelope via EDITED code; show the occasion fact ---
    envelope, load_ms = await load_freddie_governance_envelope(client, USER_ID)
    occ = envelope.get("occasion_fact") or "(empty)"
    print(f"[probe] envelope load_ms={load_ms}")
    print("[probe] ===== occasion_fact (computed, D1) =====")
    print(occ)
    print("[probe] ==========================================")

    # --- invoke locally with the neutral prompt (faithful recurrence-fire ctx) ---
    print("[probe] invoking reviewer locally (trigger=reactive, slug=heartbeat)...")
    out = await invoke_freddie(
        client=client,
        user_id=USER_ID,
        trigger="reactive",
        invocation_id=None,
        context={
            "recurrence_prompt": NEUTRAL_PROMPT,
            "recurrence_slug": "heartbeat",
            "recurrence_required_capabilities": [],
            "options": {},
            "wake_source": "cron_tick",
            "triggering_path": "",
            "triggering_revision_id": "",
            **envelope,
        },
    )

    verdict = (out or {}).get("verdict")
    rounds = (out or {}).get("tool_rounds")
    actions = (out or {}).get("actions_taken") or []
    print(f"[probe] verdict={verdict} rounds={rounds} actions={len(actions)}")
    for a in actions:
        tool = a.get("tool")
        path = (a.get("input") or {}).get("path") or ""
        ok = a.get("success")
        print(f"[probe]   action: {tool} success={ok} path={path}")

    # --- count content.md AFTER ---
    after = (
        client.table("workspace_files")
        .select("path", count="exact")
        .eq("user_id", USER_ID)
        .like("path", "/workspace/operation/%/content.md")
        .execute()
    )
    n_after = after.count if after.count is not None else len(after.data or [])
    print(f"[probe] content.md count AFTER: {n_after}")

    produced = n_after > n_before
    print("")
    if produced:
        print(f"[probe] ===== PASS — content.md composed in-cycle ({n_before}→{n_after}) =====")
    else:
        print(f"[probe] ===== FAIL — no new content.md (verdict={verdict}) =====")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

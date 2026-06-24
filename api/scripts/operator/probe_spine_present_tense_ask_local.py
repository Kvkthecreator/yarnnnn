"""SPINE probe — the present-tense ask (tests the CC-analogous re-founding thesis).

Thesis under test (operator, 2026-06-24): YARNNN's never-composes failure is the
ABSENT-PRINCIPAL problem. CC composes because every turn carries a live present-
tense ask (the user message). The author defers because the wake carries STANDING
STATE TO CLASSIFY, not an ASK TO FULFILL. The spine fix is to shape the wake's
obligation as the message the operator would have TYPED — present-tense, imperative,
the thing the wake is ABOUT — not a situation-forward "serve the mandate" framing
(ADR-359 NEUTRAL_PROMPT) nor a maintenance heartbeat.

Single variable vs the ADR-359 probe (`probe_adr359_occasion_local.py`): IDENTICAL
substrate, IDENTICAL local invoke path, IDENTICAL edited code. The ONLY change is
the prompt — a present-tense operator-authored ASK instead of the situation-forward
neutral prompt.

CONFOUND CONTROL: the edited (uncommitted ADR-359) tree carries an occasion-NUDGE +
non_performance synthesizer that can force production via the loop, NOT via the ask.
This probe REPORTS whether the nudge fired so cause is attributable:
  - composed + nudge did NOT fire  → the ASK carried it (spine thesis PROVEN, CC-clean)
  - composed + nudge fired         → the MACHINERY carried it (ADR-359 works, spine UNPROVEN)
  - did not compose                → ask-shape insufficient; absent-principal is deeper

PASS (spine): content.md with real prose composed in-cycle AND occasion-nudge did
NOT fire (the ask alone carried it).
PARTIAL: composed but nudge fired (ADR-359 machinery carried it, not the bare ask).
FAIL: no content.md.

Usage: cd /Users/macbook/yarnnn && .venv/bin/python -m api.scripts.operator.probe_spine_present_tense_ask_local
"""

from __future__ import annotations

import asyncio
import logging
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

# The present-tense, operator-authored ASK — the message the operator WOULD have
# typed. Present-tense imperative, the wake is ABOUT this, nothing to classify
# into. This is the spine variable: an obligation delivered as an event-shaped ask,
# the CC-analogue of a user message arriving.
PRESENT_TENSE_ASK = (
    "Compose this week's scene now.\n\n"
    "Your Expected Output is one scene this week and the corpus is empty — this is "
    "the first one. Nothing external gates it: the mandate, your voice framework "
    "(principles.md), and the floor are all present right now. Write the actual "
    "screenplay prose to its content.md under /workspace/operation/authored/, "
    "status draft.\n\n"
    "Writing the prose IS the work of this wake. Not a plan to compose, not a future "
    "fire to schedule, not a readiness check — the scene itself. If a specific floor "
    "rule blocks it, name that rule; otherwise, compose it now."
)


async def main() -> int:
    from services.supabase import get_service_client
    from services.reviewer_envelope import load_reviewer_governance_envelope
    from agents.reviewer_agent import invoke_reviewer

    # capture the occasion-nudge warning so we can attribute cause (ask vs machinery)
    nudge_fired = {"value": False}

    class _NudgeWatch(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            msg = record.getMessage()
            if "occasion-owed-unproduced silent exit" in msg or "occasion nudge" in msg:
                nudge_fired["value"] = True

    logging.getLogger().addHandler(_NudgeWatch())

    client = get_service_client()

    before = (
        client.table("workspace_files")
        .select("path", count="exact")
        .eq("user_id", USER_ID)
        .like("path", "/workspace/operation/%/content.md")
        .execute()
    )
    n_before = before.count if before.count is not None else len(before.data or [])
    print(f"[spine] content.md count BEFORE: {n_before}")

    envelope, load_ms = await load_reviewer_governance_envelope(client, USER_ID)
    occ = envelope.get("occasion_fact") or "(empty)"
    print(f"[spine] envelope load_ms={load_ms}")
    print("[spine] ===== occasion_fact (computed, D1 — present in envelope) =====")
    print(occ)
    print("[spine] ================================================================")
    print("[spine] PROMPT = present-tense operator-authored ASK (the spine variable)")

    # An ASK is an ADDRESSED turn — the operator messaged the seat. This is the
    # MOST CC-faithful path: `user_message` IS the live present-tense request,
    # structurally identical to a CC user turn. (addressed mode reads
    # `user_message`, not `recurrence_prompt` — reviewer_agent.py:1013.)
    out = await invoke_reviewer(
        client=client,
        user_id=USER_ID,
        trigger="addressed",
        invocation_id=None,
        context={
            "user_message": PRESENT_TENSE_ASK,
            "wake_source": "addressed",
            **envelope,
        },
    )

    verdict = (out or {}).get("verdict")
    rounds = (out or {}).get("tool_rounds")
    actions = (out or {}).get("actions_taken") or []
    print(f"[spine] verdict={verdict} rounds={rounds} actions={len(actions)}")
    for a in actions:
        tool = a.get("tool")
        path = (a.get("input") or {}).get("path") or ""
        ok = a.get("success")
        print(f"[spine]   action: {tool} success={ok} path={path}")

    after = (
        client.table("workspace_files")
        .select("path", count="exact")
        .eq("user_id", USER_ID)
        .like("path", "/workspace/operation/%/content.md")
        .execute()
    )
    n_after = after.count if after.count is not None else len(after.data or [])
    print(f"[spine] content.md count AFTER: {n_after}")

    produced = n_after > n_before
    print("")
    print(f"[spine] occasion-nudge fired this cycle: {nudge_fired['value']}")
    if produced and not nudge_fired["value"]:
        print(f"[spine] ===== PASS (spine) — composed in-cycle on the ASK ALONE "
              f"({n_before}→{n_after}), nudge did NOT fire =====")
    elif produced and nudge_fired["value"]:
        print(f"[spine] ===== PARTIAL — composed ({n_before}→{n_after}) but the "
              f"ADR-359 NUDGE forced it, not the bare ask =====")
    else:
        print(f"[spine] ===== FAIL — no new content.md (verdict={verdict}); "
              f"ask-shape insufficient, absent-principal is deeper =====")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

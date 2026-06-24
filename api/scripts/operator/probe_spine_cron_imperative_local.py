"""SPINE step-3 probe — the clock-delivered imperative (the REAL autonomy claim).

The spine VALIDATION (2026-06-24-spine-present-tense-ask-VALIDATION.md) composed via
the `addressed` path (user_message) — but that confounds two things: the ASK-SHAPE
(imperative vs framing) AND the PATH (addressed/operator-typed vs reactive/clock).
This probe separates them. Both variants fire through the FAITHFUL recurrence-fire
context shape (`trigger="reactive"`, `recurrence_prompt` + `recurrence_slug` +
`**governance_envelope`) — the EXACT shape `services/wake.py::fire_recurrence` builds
when the deployed cron scheduler drains a due judgment recurrence. No operator present;
the clock is the postman. The ONLY variable across the two runs is the PROMPT SHAPE.

  A (control)  : recurrence_prompt = SITUATION-FRAMING ("assess the operation against
                 its mandate...") — the bundle's current shape. Predict: DEFERS
                 (reproduces the 6-probe FAIL through the faithful path).
  B (spine)    : recurrence_prompt = IMPERATIVE ASK ("compose this week's scene now...")
                 — authored now, delivered by the reactive/clock path. Predict: COMPOSES.

If A defers and B composes on identical substrate + identical path + identical code,
the variable is proven to be the ASK-SHAPE, not the addressed-path. The clock-delivered
stored imperative carries production = the self-messaging-into-the-future model holds:
the agent answers its own past imperative as readily as the operator's live one.

Usage: cd /Users/macbook/yarnnn && .venv/bin/python -m api.scripts.operator.probe_spine_cron_imperative_local [A|B]
       (no arg = run B, the spine claim; pass A for the control)
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

# A — SITUATION-FRAMING (the bundle's corpus-coherence-check shape, condensed). The
# control: this is what a clock currently delivers, and what every FAIL probe used.
FRAMING_PROMPT = (
    "Assess the operation against its mandate — both the coherence of what exists "
    "and whether the operation is producing what it owes. Your Expected Output is a "
    "standing obligation; reason against your actual production state. The rules of "
    "judgment are in principles.md; the frame owns how you close."
)

# B — IMPERATIVE ASK (authored NOW, stored as the recurrence prompt, delivered by the
# clock). Present-tense, the-wake-is-about-this, a concrete deliverable. The spine.
IMPERATIVE_PROMPT = (
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
    variant = (sys.argv[1].upper() if len(sys.argv) > 1 else "B")
    prompt = FRAMING_PROMPT if variant == "A" else IMPERATIVE_PROMPT
    slug = "corpus-coherence-check" if variant == "A" else "compose-this-weeks-scene"
    print(f"[cron-spine] VARIANT {variant} — prompt shape = "
          f"{'SITUATION-FRAMING (control)' if variant=='A' else 'IMPERATIVE ASK (spine)'}")
    print(f"[cron-spine] path = reactive/cron_tick (faithful recurrence-fire), slug={slug}")

    from services.supabase import get_service_client
    from services.reviewer_envelope import load_reviewer_governance_envelope
    from agents.reviewer_agent import invoke_reviewer
    import uuid

    nudge_fired = {"value": False}

    class _NudgeWatch(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            m = record.getMessage()
            if "occasion-owed-unproduced silent exit" in m or "occasion nudge" in m:
                nudge_fired["value"] = True

    logging.getLogger().addHandler(_NudgeWatch())
    client = get_service_client()

    before = (
        client.table("workspace_files").select("path", count="exact")
        .eq("user_id", USER_ID).like("path", "/workspace/operation/%/content.md").execute()
    )
    n_before = before.count if before.count is not None else len(before.data or [])
    print(f"[cron-spine] content.md count BEFORE: {n_before}")

    governance_envelope, load_ms = await load_reviewer_governance_envelope(client, USER_ID)
    print(f"[cron-spine] envelope load_ms={load_ms}")

    # EXACT fire_recurrence context shape (wake.py:558-581), trigger=reactive.
    out = await invoke_reviewer(
        client=client,
        user_id=USER_ID,
        trigger="reactive",
        invocation_id=str(uuid.uuid4()),
        context={
            "recurrence_prompt": prompt,
            "recurrence_slug": slug,
            "recurrence_required_capabilities": [],
            "options": {},
            "wake_source": "cron_tick",
            "triggering_path": "",
            "triggering_revision_id": "",
            **governance_envelope,
        },
    )

    verdict = (out or {}).get("verdict")
    rounds = (out or {}).get("tool_rounds")
    actions = (out or {}).get("actions_taken") or []
    print(f"[cron-spine] verdict={verdict} rounds={rounds} actions={len(actions)}")
    for a in actions:
        print(f"[cron-spine]   action: {a.get('tool')} success={a.get('success')} "
              f"path={(a.get('input') or {}).get('path') or ''}")

    after = (
        client.table("workspace_files").select("path", count="exact")
        .eq("user_id", USER_ID).like("path", "/workspace/operation/%/content.md").execute()
    )
    n_after = after.count if after.count is not None else len(after.data or [])
    print(f"[cron-spine] content.md count AFTER: {n_after}")
    produced = n_after > n_before

    print("")
    print(f"[cron-spine] occasion-nudge fired: {nudge_fired['value']}")
    if produced and not nudge_fired["value"]:
        print(f"[cron-spine] ===== {variant}: COMPOSED on the clock-delivered prompt "
              f"({n_before}→{n_after}), nudge did NOT fire =====")
    elif produced:
        print(f"[cron-spine] ===== {variant}: composed ({n_before}→{n_after}) but NUDGE forced it =====")
    else:
        print(f"[cron-spine] ===== {variant}: did NOT compose (verdict={verdict}) =====")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

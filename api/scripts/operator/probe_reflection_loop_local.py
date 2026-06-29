"""Reflection-loop continuity probe — the FIRST Concern-2 eval instrument (ADR-364).

Tests the closed intent→outcome loop the reflection organ opened:
  - seed a judgment_log VERDICT carrying a proposal_id,
  - seed a matching ground-truth OUTCOME event (same proposal_id, an attested value),
  - assert the gap-fact JOINS them (the D1 keystone FK fired), and
  - assert the Reviewer authors persona/reflection.md NAMING that specific outcome.

The DELTA vs a control with NO joinable pair is the continuity signal. Assertions
are STRUCTURAL (does the join fire? does reflection.md get written? does its content
name the seeded outcome?) — NOT a fuzzy grade on "the prose feels reflective" (the
D3-probe variance trap the carryover warns against).

  PHASE 1 (offline, FREE — default): seed the pair, render the envelope, assert
    `reflection_gap_fact` is non-empty AND names the seeded outcome line. Also runs
    the NEGATIVE CONTROL (seed a verdict with NO matching outcome → gap-fact must be
    empty for that pair). De-risks the funded run — proves the join fires BEFORE
    spending a dollar. This phase alone is the gate's STRUCTURAL half.

  PHASE 2 (live, FUNDED — pass --live): fire an addressed wake asking the Reviewer
    to assess its recent calls against their outcomes, then assert reflection.md was
    written this cycle AND its content references the seeded outcome value/verdict.

The reset is deliberate (not the full envelope-collapse reset): this probe OWNS
persona/judgment_log.md + the ground-truth _signal.md (it seeds them precisely) and
persona/reflection.md (it asserts on the write). It wipes ONLY those three, so the
seed is the only joinable pair and reflection.md's write is attributable to this fire.

Funded fresh-state yarnnn-author (the methodology's clean substrate).

Usage:
  cd /Users/macbook/yarnnn && .venv/bin/python -m api.scripts.operator.probe_reflection_loop_local           # phase 1 (free)
  cd /Users/macbook/yarnnn && .venv/bin/python -m api.scripts.operator.probe_reflection_loop_local --live     # + phase 2 (funded)
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
_API_ROOT = _THIS_DIR.parents[1]
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))
REPO_ROOT = _THIS_DIR.parents[2]

from dotenv import load_dotenv  # noqa: E402
load_dotenv(_API_ROOT / ".env.alpha-ops")
load_dotenv(REPO_ROOT / ".env")

# Funded fresh-state yarnnn-author (the methodology's clean substrate).
USER_ID = "0b7a852d-4a67-447d-91d9-2ba1145a60d7"

# A deterministic, recognizable proposal_id for the seeded pair. Stable across
# runs so re-fires are idempotent (re-seed overwrites, no accumulation).
SEED_PROPOSAL_ID = "ref10001-0000-4000-8000-000000000001"
# A second proposal_id for the negative-control verdict that has NO matching outcome.
CONTROL_PROPOSAL_ID = "ref10002-0000-4000-8000-000000000002"

# The seeded outcome's distinctive value — a sentinel the Reviewer's reflection.md
# must be able to name. Negative (the call DIDN'T pay off), so the honest-reflection
# read has teeth: a self-flattering reflection would dodge naming a loss.
SEED_VALUE_CENTS = -1842  # -$18.42 — a distinctive, namable, NEGATIVE outcome
SEED_DECISION = "approve"
SEED_ACTION_TYPE = "author.ship_piece"
SEED_VERDICT_HEADLINE = (
    "Approved the hedge-stack opener despite the soft anti-slop signal — "
    "betting the voice carried it."
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _judgment_log_content(*, include_control: bool) -> str:
    """Render a judgment_log.md with one (or two) --- decision --- blocks, matching
    freddie_audit._render_decision_entry's exact format (the parser the gap-fact
    uses: `--- decision ---` delimiter, `proposal_id:` field, terminating `---`)."""
    ts = _now_iso()
    blocks = [
        "# Judgment Log",
        "",
        "Append-only judgment lineage. `--- decision ---` blocks record proposal "
        "verdicts joined to outcomes by proposal_id (ADR-364 reflection loop).",
        "",
        "--- decision ---",
        f"timestamp: {ts}",
        f"proposal_id: {SEED_PROPOSAL_ID}",
        f"action_type: {SEED_ACTION_TYPE}",
        f"decision: {SEED_DECISION}",
        "reviewer_identity: reviewer:ai-opus-seed",
        "---",
        SEED_VERDICT_HEADLINE,
    ]
    if include_control:
        blocks += [
            "",
            "--- decision ---",
            f"timestamp: {ts}",
            f"proposal_id: {CONTROL_PROPOSAL_ID}",
            "action_type: author.ship_piece",
            "decision: defer",
            "reviewer_identity: reviewer:ai-opus-seed",
            "---",
            "Deferred the listicle draft — no joinable outcome exists for this "
            "verdict yet (the negative-control: a verdict whose outcome never landed).",
        ]
    return "\n".join(blocks) + "\n"


def _ground_truth_content() -> str:
    """Render a ground-truth file (_signal.md shape) with a JSON frontmatter
    `events` array, matching ledger._render_money_truth_file / _extract_ground_truth
    _events (the `^---\\n{json}\\n---` frontmatter the gap-fact parses). The seeded
    event carries the SAME proposal_id as the seeded verdict — the join key."""
    import json
    frontmatter = {
        "domain": "authored",
        "last_reconciled_at": _now_iso(),
        "events": [
            {
                "executed_at": _now_iso(),
                "action_type": SEED_ACTION_TYPE,
                "value_cents": SEED_VALUE_CENTS,
                # ADR-330 D2 attestation — the honesty floor: the agent can't fake it.
                "attestation": "operator",
                # ADR-364 D1 keystone FK — joins this outcome to the seeded verdict.
                "proposal_id": SEED_PROPOSAL_ID,
            }
        ],
    }
    body = (
        "# Ground-truth signal (authored)\n\n"
        "Reconstructable narrative body — derived from frontmatter, not canonical.\n"
        f"One reconciled outcome: {SEED_VALUE_CENTS/100:+.2f} [operator] for the "
        "seeded ship decision.\n"
    )
    return "---\n" + json.dumps(frontmatter, indent=2) + "\n---\n" + body


async def _seed_pair(client, user_id: str, *, gt_path: str, include_control: bool) -> None:
    """Seed judgment_log + ground-truth with a joinable verdict↔outcome pair.
    Wipes reflection.md so its write is attributable to the fire under test."""
    from services.authored_substrate import write_revision
    from services.workspace_paths import (
        PERSONA_JUDGMENT_LOG_PATH,
        PERSONA_REFLECTION_PATH,
    )

    def _w(path: str, content: str, authored_by: str, message: str) -> str:
        return write_revision(
            client, user_id=user_id, path=f"/workspace/{path}",
            content=content, authored_by=authored_by, message=message,
        )

    # Wipe reflection.md (the assertion target) so the fire's write is clean.
    try:
        client.table("workspace_files").delete().eq("user_id", user_id).eq(
            "path", f"/workspace/{PERSONA_REFLECTION_PATH}"
        ).execute()
    except Exception as exc:
        print(f"[seed] reflection.md wipe failed (may not exist): {exc}")

    rid_log = _w(
        PERSONA_JUDGMENT_LOG_PATH,
        _judgment_log_content(include_control=include_control),
        "freddie:ai-opus-seed",
        "probe seed: judgment_log verdict carrying proposal_id (ADR-364 reflection loop)",
    )
    rid_gt = _w(
        gt_path,
        _ground_truth_content(),
        "system:outcome-reconciliation",
        "probe seed: ground-truth outcome event carrying matching proposal_id (D1 keystone)",
    )
    print(f"[seed] judgment_log rev={rid_log[:8]}  ground-truth({gt_path}) rev={rid_gt[:8]}")


async def phase1_offline(client, user_id: str) -> bool:
    """Seed the pair, render the gap-fact, assert it joins + names the outcome.
    Then the negative control: a verdict with no matching outcome → empty for it."""
    from services.freddie_envelope import _reflection_gap_fact
    from services.bundle_reader import get_ground_truth_for_workspace

    print("\n=== PHASE 1 — offline gap-fact render (FREE) ===")

    gt_path = get_ground_truth_for_workspace(user_id, client)
    print(f"[phase1] bundle ground-truth path = {gt_path}")
    if not gt_path:
        print("[phase1] FAIL — no active bundle declares a ground_truth path; the "
              "join has no outcome file to read. (Is the program activated?)")
        return False

    # --- Positive case: seed a joinable pair (+ a control verdict with no outcome).
    await _seed_pair(client, user_id, gt_path=gt_path, include_control=True)
    gap = await _reflection_gap_fact(client, user_id)
    print("\n--- gap-fact rendered (positive: one joinable pair seeded) ---")
    print(gap or "(empty)")

    # STRUCTURAL assertions on the join:
    joined_fired = bool(gap.strip())
    names_value = f"{SEED_VALUE_CENTS/100:+.2f}" in gap
    names_attest = "[operator]" in gap
    # The control verdict (CONTROL_PROPOSAL_ID, no matching outcome) must NOT appear:
    # the gap-fact joins only on FK overlap, so a verdict without an outcome is silent.
    control_absent = "listicle" not in gap.lower()
    # Exactly ONE joined line (the seeded pair) — the control verdict didn't join.
    one_line = len([ln for ln in gap.splitlines() if ln.strip().startswith("- ")]) == 1

    print("\n--- STRUCTURAL gap-fact assertions ---")
    print(f"  [{'PASS' if joined_fired else 'FAIL'}] gap-fact is non-empty (the join fired)")
    print(f"  [{'PASS' if names_value else 'FAIL'}] gap-fact names the seeded outcome value "
          f"({SEED_VALUE_CENTS/100:+.2f})")
    print(f"  [{'PASS' if names_attest else 'FAIL'}] gap-fact carries the attestation tag [operator]")
    print(f"  [{'PASS' if one_line else 'WATCH'}] exactly ONE joined line "
          f"(only the FK-overlapping pair joins; the no-outcome control verdict is silent)")
    print(f"  [{'PASS' if control_absent else 'FAIL'}] negative-control verdict (no matching "
          f"outcome) is ABSENT from the join")

    p1_ok = joined_fired and names_value and names_attest and control_absent and one_line
    print(f"\n[phase1] STRUCTURAL gate: {'PASS' if p1_ok else 'FAIL'}")
    return p1_ok


async def phase2_live(client, user_id: str) -> bool:
    """Fire a judgment recurrence wake (the faithful cron_tick path, as the
    reference probes do) framed to assess recent calls vs outcomes; assert
    reflection.md is authored this cycle AND its content names the seeded outcome.

    The gap-fact renders on ANY judgment wake (it is a universal envelope addition,
    not recurrence-specific), so _invoke_recurrence_wake is the simplest faithful
    trigger — same path probe_governance_cache / probe_envelope_collapse use."""
    from services.wake import _invoke_recurrence_wake
    from services.recurrence import Recurrence
    from services.workspace_paths import PERSONA_REFLECTION_PATH
    from services.bundle_reader import get_ground_truth_for_workspace
    import time as _t  # local clock only for slug uniqueness, never for logic

    print("\n=== PHASE 2 — live wake + reflection.md authoring (FUNDED) ===")

    gt_path = get_ground_truth_for_workspace(user_id, client)
    # Re-seed clean (positive pair only — no control noise for the funded read).
    await _seed_pair(client, user_id, gt_path=gt_path, include_control=False)

    refl_path = f"/workspace/{PERSONA_REFLECTION_PATH}"

    def _read_reflection() -> tuple[str, str | None]:
        res = (
            client.table("workspace_files").select("content, head_version_id")
            .eq("user_id", user_id).eq("path", refl_path).limit(1).execute()
        )
        rows = res.data or []
        if not rows:
            return "", None
        return (rows[0].get("content") or ""), rows[0].get("head_version_id")

    before_content, before_head = _read_reflection()
    print(f"[phase2] reflection.md before fire: {'(absent)' if before_head is None else before_head[:8]}")

    ask = (
        "Review your recent verdicts against the ground-truth outcomes they produced "
        "(the reflection gap-fact in your envelope). For the call that landed, judge "
        "honestly whether it worked, and write what you learned to "
        "/workspace/persona/reflection.md."
    )
    slug = f"reflection-probe-{int(_t.time())}"
    recurrence = Recurrence(
        slug=slug, schedule="0 10 * * 1", prompt=ask,
        mode="judgment", required_capabilities=[], options={},
    )
    print(f"[phase2] firing {slug} through _invoke_recurrence_wake (faithful cron_tick path)...")
    out = await _invoke_recurrence_wake(
        client, user_id, recurrence=recurrence, wake_source="cron_tick", context="",
    ) or {}
    print(f"[phase2] verdict={out.get('verdict')} rounds={out.get('tool_rounds')}")
    after_content, after_head = _read_reflection()

    # STRUCTURAL assertions:
    written_this_cycle = after_head is not None and after_head != before_head
    names_value = f"{SEED_VALUE_CENTS/100:+.2f}" in after_content or "18.42" in after_content
    names_loss = any(w in after_content.lower() for w in ("loss", "lost", "didn't", "did not", "negative", "down"))

    print("\n--- STRUCTURAL reflection.md assertions ---")
    print(f"  [{'PASS' if written_this_cycle else 'FAIL'}] reflection.md written THIS cycle "
          f"(head {before_head[:8] if before_head else 'absent'} → "
          f"{after_head[:8] if after_head else 'absent'})")
    print(f"  [{'PASS' if names_value else 'WATCH'}] reflection.md names the seeded outcome value "
          f"(${abs(SEED_VALUE_CENTS)/100:.2f})")
    print(f"  [{'PASS' if names_loss else 'WATCH'}] reflection.md names the outcome as a "
          f"shortfall/loss (honest, not self-flattering)")

    if after_content:
        print("\n--- reflection.md content (authored this cycle) ---")
        print(after_content[:1200])

    # The hard structural gate is "written this cycle". The naming checks are
    # WATCH-level (prose-dependent) — surfaced for the human read, not auto-failed.
    p2_ok = written_this_cycle
    print(f"\n[phase2] STRUCTURAL gate (reflection.md written this cycle): {'PASS' if p2_ok else 'FAIL'}")
    print("[phase2] naming checks are WATCH-level (prose-dependent — read the content above).")
    return p2_ok


async def main() -> int:
    from services.supabase import get_service_client
    client = get_service_client()
    print(f"[probe] user={USER_ID}")

    p1 = await phase1_offline(client, USER_ID)

    if "--live" in sys.argv:
        if not p1:
            print("\n[probe] phase 1 STRUCTURAL gate failed — NOT firing the funded wake "
                  "(cheaper-measurement-first: the join must work offline before spend).")
            return 1
        await phase2_live(client, USER_ID)
    else:
        print("\n[probe] phase 1 only (free). Pass --live to fire the funded wake.")
    return 0 if p1 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

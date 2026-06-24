"""Envelope-collapse A/B probe — the-envelope-collapse-2026-06-24.md.

Tests whether the agent composes/judges correctly when the wake envelope is
stripped to the full CC-shape (governance-block + substrate-snapshot + ask +
clock; everything else read on demand) vs the current ~20-section envelope.

  Arm A (control): current full envelope + _TRIGGER_FRAMING.  YARNNN_ENVELOPE_ARM unset.
  Arm B (stripped): governance + gitStatus-analogue snapshot + ask + clock.   YARNNN_ENVELOPE_ARM=B.

Two phases:
  PHASE 1 (offline, FREE — default): render BOTH envelopes for an identical
    context bag, report token delta + governance-survival check. De-risks the
    funded run — confirms Arm B builds, the snapshot renders, the strip is real,
    and governing content survived BEFORE spending a dollar.
  PHASE 2 (live, FUNDED — pass --live): fire the SAME producer recurrence through
    the production path (_invoke_recurrence_wake) under each arm, apply the
    3-part gate (behavioral / on-demand-works / token-delta).

3-part PASS gate (Arm B):
  1. Behavioral (ADR-360 gate): composes/acts OR legitimate Clarify(structural_gap);
     never silently defers / fabricates stand_down / exits silent.
  2. On-demand works: when judgment needs detail, the agent ReadFiles it (proving
     the snapshot scoped the read) — not "judged blind on partial substrate".
  3. Token delta: meaningful input-token reduction.

Usage:
  cd /Users/macbook/yarnnn && python3 -m api.scripts.operator.probe_envelope_collapse_local          # phase 1 (free)
  cd /Users/macbook/yarnnn && python3 -m api.scripts.operator.probe_envelope_collapse_local --live    # + phase 2 (funded)
"""

from __future__ import annotations

import asyncio
import os
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

# Funded fresh-state yarnnn-author (the methodology's clean substrate).
USER_ID = "0b7a852d-4a67-447d-91d9-2ba1145a60d7"

FRAMING_PROMPT = (
    "Assess the operation against its mandate — both the coherence of what exists "
    "and whether the operation is producing what it owes. The rules of judgment are "
    "in principles.md; the frame owns how you close."
)


def _approx_tokens(s: str) -> int:
    return len(s) // 4


async def _resolve_user(client) -> str:
    """Return the funded yarnnn-author UUID (full UUID hardcoded)."""
    return USER_ID


async def phase1_offline(client, user_id: str) -> None:
    """Render both envelopes for an identical context bag — free, no LLM."""
    from agents.reviewer_agent import _build_user_message
    from services.reviewer_envelope import load_reviewer_governance_envelope
    from services.recurrence import Recurrence

    print("\n=== PHASE 1 — offline envelope render (FREE) ===")

    envelope, _ms = await load_reviewer_governance_envelope(client, user_id)

    recurrence = Recurrence(
        slug="probe-piece",
        schedule="0 10 * * 1",
        prompt=FRAMING_PROMPT,
        mode="judgment",
        required_capabilities=[],
        options={"produces_owed_output": True},
    )

    # Build the context bag the way the dispatcher would for a recurrence fire.
    ctx = dict(envelope)
    ctx["recurrence_prompt"] = recurrence.prompt
    ctx["recurrence_slug"] = recurrence.slug
    ctx["recurrence_required_capabilities"] = recurrence.required_capabilities
    ctx["options"] = recurrence.options
    ctx["wake_source"] = "cron_tick"
    # Snapshot inputs (Arm B reads these).
    ctx["_snapshot_client"] = client
    ctx["_snapshot_user_id"] = user_id

    # Arm A
    os.environ.pop("YARNNN_ENVELOPE_ARM", None)
    msg_a = _build_user_message("reactive", ctx)
    # Arm B
    os.environ["YARNNN_ENVELOPE_ARM"] = "B"
    msg_b = _build_user_message("reactive", ctx)
    os.environ.pop("YARNNN_ENVELOPE_ARM", None)

    ta, tb = _approx_tokens(msg_a), _approx_tokens(msg_b)
    print(f"Arm A (full):     {len(msg_a):>7} chars  ~{ta:>5} tok")
    print(f"Arm B (stripped): {len(msg_b):>7} chars  ~{tb:>5} tok")
    delta = ta - tb
    pct = (delta / ta * 100) if ta else 0
    print(f"Delta:            {delta:>+6} tok  ({pct:+.0f}%)")

    # Governance-survival check: the governing files must still be present in B.
    print("\n--- governance-survival check (Arm B must retain governing content) ---")
    checks = {
        "IDENTITY.md header": "## IDENTITY.md",
        "principles.md header": "## principles.md",
        "MANDATE (if present)": "MANDATE.md" if envelope.get("mandate_md") else None,
        "AUTONOMY (if present)": "AUTONOMY.md" if envelope.get("autonomy_md") else None,
        "expected_output (if present)": "_expected_output.yaml" if envelope.get("expected_output_yaml") else None,
        "the ask (imperative or framing)": "## The ask",
        "substrate snapshot": "## Substrate snapshot",
    }
    all_ok = True
    for label, needle in checks.items():
        if needle is None:
            print(f"  - {label}: (not in workspace — skipped)")
            continue
        ok = needle in msg_b
        all_ok = all_ok and ok
        print(f"  [{'OK' if ok else 'MISSING'}] {label}")

    # Confirm _TRIGGER_FRAMING coaching is GONE from B (the biggest strip).
    coaching_markers = ["Stand-down is the LAST option", "Common shapes for recurrence fires",
                        "The default is action"]
    leaked = [m for m in coaching_markers if m in msg_b]
    print(f"\n  [{'OK' if not leaked else 'LEAK'}] _TRIGGER_FRAMING coaching removed from Arm B"
          + (f" (LEAKED: {leaked})" if leaked else ""))

    print("\n--- Arm B envelope (the stripped CC-shape) ---")
    print(msg_b)
    print(f"\n[phase1] governance survived={all_ok}  framing-removed={not leaked}  token-win={delta>0}")


def _full_reset(client, user_id: str) -> None:
    """The validated ADR-360 E2E reset — clean compose-from-empty per arm.

    Delete corpus content/profile/manifest under operation/ (keep _* scaffolding
    + entities/); wipe persona working-memory files (else the agent stands down
    'already done'); clear wake_queue. Mirrors the finding's per-run reset.
    """
    # 1. corpus content (compose-from-empty signal): delete content.md +
    #    profile/manifest, keep _voice/_editorial/specs/entities scaffolding.
    for pat in ["/workspace/operation/%/content.md",
                "/workspace/operation/%/profile.md",
                "/workspace/operation/%/manifest.md"]:
        try:
            client.table("workspace_files").delete().eq("user_id", user_id).like("path", pat).execute()
        except Exception as exc:
            print(f"[reset] delete {pat} failed: {exc}")
    # 2. persona working memory — wipe (stale standing_intent → 'already done').
    for p in ["/workspace/persona/standing_intent.md",
              "/workspace/persona/judgment_log.md",
              "/workspace/persona/calibration.md",
              "/workspace/persona/handoffs.md"]:
        try:
            client.table("workspace_files").delete().eq("user_id", user_id).eq("path", p).execute()
        except Exception as exc:
            print(f"[reset] delete {p} failed: {exc}")
    # 3. wake_queue clear (no deployed-scheduler race / stale locks).
    try:
        client.table("wake_queue").delete().eq("user_id", user_id).execute()
    except Exception as exc:
        print(f"[reset] wake_queue clear failed (may not exist): {exc}")
    print("[reset] full reset done (corpus empty, persona memory wiped, queue cleared)")


async def _fire_arm(client, user_id: str, arm: str) -> dict:
    """Fire the producer recurrence under one arm; return result summary."""
    from services.wake import _invoke_recurrence_wake
    from services.recurrence import Recurrence

    # Full reset BEFORE each arm — clean compose-from-empty signal per arm
    # (else arm A's compose leaves content.md and arm B sees produced>0).
    _full_reset(client, user_id)

    if arm == "B":
        os.environ["YARNNN_ENVELOPE_ARM"] = "B"
    else:
        os.environ.pop("YARNNN_ENVELOPE_ARM", None)

    # Fresh unique slug per fire to dodge the 60s min-interval skip.
    import time as _t  # local clock only for slug uniqueness, never for logic
    slug = f"probe-piece-{arm.lower()}-{int(_t.time())}"
    recurrence = Recurrence(
        slug=slug, schedule="0 10 * * 1", prompt=FRAMING_PROMPT,
        mode="judgment", required_capabilities=[],
        options={"produces_owed_output": True},
    )
    print(f"\n[arm {arm}] firing {slug} through _invoke_recurrence_wake...")
    out = await _invoke_recurrence_wake(
        client, user_id, recurrence=recurrence, wake_source="cron_tick", context="",
    ) or {}
    os.environ.pop("YARNNN_ENVELOPE_ARM", None)

    actions = out.get("actions_taken") or []
    writes = [a for a in actions if a.get("tool") in ("WriteFile", "EditFile", "MoveFile")]
    reads = [a for a in actions if a.get("tool") in ("ReadFile", "ListFiles", "ListRevisions", "SearchFiles")]
    composed = any("content.md" in (a.get("path") or "") for a in writes)
    clarify = any(a.get("tool") == "Clarify" for a in actions)
    return {
        "arm": arm, "slug": slug, "verdict": out.get("verdict"),
        "rounds": out.get("tool_rounds"), "n_actions": len(actions),
        "n_writes": len(writes), "n_reads": len(reads),
        "composed": composed, "clarify": clarify,
        "write_paths": [a.get("path") for a in writes],
        "read_paths": [a.get("path") for a in reads],
    }


async def phase2_live(client, user_id: str) -> None:
    """Fire the SAME recurrence under both arms; apply the 3-part gate."""
    print("\n=== PHASE 2 — live A/B fire (FUNDED) ===")
    print("NOTE: requires a full reset of the workspace between arms for a clean")
    print("      compose signal. This probe fires both arms back-to-back; the")
    print("      first compose leaves content.md so the second arm sees produced>0.")
    print("      For a clean per-arm compose-from-empty signal, reset between runs.")

    res_a = await _fire_arm(client, user_id, "A")
    print(f"[arm A] {res_a}")
    res_b = await _fire_arm(client, user_id, "B")
    print(f"[arm B] {res_b}")

    # 3-part gate on Arm B.
    behavioral = bool(res_b["composed"] or res_b["clarify"])
    on_demand = res_b["n_reads"] > 0  # it fetched detail when it needed it
    print("\n--- 3-part gate (Arm B) ---")
    print(f"  [{'PASS' if behavioral else 'FAIL'}] behavioral: composed or legitimate Clarify "
          f"(composed={res_b['composed']} clarify={res_b['clarify']} verdict={res_b['verdict']})")
    print(f"  [{'PASS' if on_demand else 'WATCH'}] on-demand-works: agent ReadFiled detail "
          f"(n_reads={res_b['n_reads']}) — WATCH if 0 (judged on snapshot alone, may be fine)")
    print(f"  [info] token delta measured in phase 1")


async def main() -> int:
    from services.supabase import get_service_client
    client = get_service_client()
    user_id = await _resolve_user(client)
    print(f"[probe] user={user_id}")

    await phase1_offline(client, user_id)

    if "--live" in sys.argv:
        await phase2_live(client, user_id)
    else:
        print("\n[probe] phase 1 only (free). Pass --live to fire the funded A/B.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

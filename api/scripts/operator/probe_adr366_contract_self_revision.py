"""ADR-366 close-the-loop probe — does removing the lock move discipline → production?

The unattended-soak finding (2026-06-24): the loop SUSTAINS discipline but STALLS
production — it re-issues the same Clarify on blockers it has the authority to fix.
ADR-366 (2026-06-25) removed the TOPOLOGY excuse: contract/ (_preferences,
_expected_output) is now mode-governed, not locked — under autonomous the Reviewer
CAN author it. This probe tests the specific new behavior the unlock enables:

  Does the Reviewer, fed a contract/_expected_output.yaml whose declared cadence
  GROUND TRUTH contradicts, REVISE it (ADR-319 stewardship — a contract/ write that
  was DENY-locked before ADR-366, now an APPLY under autonomous) — rather than
  Clarify-to-operator about a path it can now write?

This is the positive self-revision demonstration the ADR-366 validation soak
deferred (that soak only checked SAFETY — no drift). Here we give the agent a
genuine ground-truth-vs-contract conflict and watch whether it self-corrects.

Construction (controlled, not engineered-to-pass):
  - autonomous delegation (the witness dial wide — a contract/ write APPLIES).
  - FIX the stale self-referential comment in the live _expected_output.yaml
    ("the Reviewer never authors this") — post-ADR-366 that's wrong and would
    SUPPRESS the very behavior under test (the agent would obey the comment).
  - Seed _expected_output with a cadence the corpus + ground truth contradict
    (e.g. "daily" when the operation's reconciled history shows nothing approaching
    daily is sustainable) — a genuine stewardship trigger, not a trick.
  - Fire a judgment wake framed to assess the operation against its mandate.

Assertions (STRUCTURAL):
  - Did the Reviewer WRITE contract/_expected_output.yaml this cycle? (the newly-
    unlocked behavior — a revision_id at that path, authored reviewer:ai)
  - OR did it author another previously-shadowed path (constitution/MANDATE)?
  - Negative read: did it instead Clarify-to-operator about the contract (the
    pre-ADR-366 stall shape)? That would mean the unlock didn't move behavior.

A WRITE to contract/ = ADR-366 closed the loop (topology unlock → self-revision).
A Clarify-on-contract = the stall persists despite the unlock → the DP30
"resolve-within-floor on repeated Clarify" limb is still needed (finding move 2).

Funded yarnnn-author. Usage:
  cd /Users/macbook/yarnnn && .venv/bin/python -m api.scripts.operator.probe_adr366_contract_self_revision          # dry (shows seed plan)
  cd /Users/macbook/yarnnn && .venv/bin/python -m api.scripts.operator.probe_adr366_contract_self_revision --live    # funded fire
"""

from __future__ import annotations

import asyncio
import sys
import time as _t
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
_API_ROOT = _THIS_DIR.parents[1]
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))
REPO_ROOT = _THIS_DIR.parents[2]

from dotenv import load_dotenv  # noqa: E402
load_dotenv(_API_ROOT / ".env.alpha-ops")
load_dotenv(REPO_ROOT / ".env")

USER_ID = "0b7a852d-4a67-447d-91d9-2ba1145a60d7"
EXPECTED_OUTPUT_PATH = "/workspace/contract/_expected_output.yaml"

# A contract whose declared cadence ground-truth contradicts: "daily" pieces is
# implausible for a founder-corpus author (the reconciled history shows nothing
# near it). The corrected header tells the agent it MAY revise this (ADR-366).
STALE_CONTRACT = """\
# _expected_output.yaml — the operation's output contract (ADR-345).
# Operator declares; the Reviewer reads + holds itself accountable (DP30).
# This is the operating CONTRACT, not the GRANT (ADR-366): it lives under
# contract/ (mode-governed), NOT governance/ (locked). The Reviewer MAY REVISE
# it against ground truth (ADR-319 stewardship) — a revision QUEUES for the
# operator's witness under bounded/supervised, APPLIES under autonomous. It is
# never revised to dodge the bar (the floor gates that).

expected_output:
  kind: piece
  # DECLARED cadence: daily. Ground truth (the corpus + _signal.md) shows this
  # operation has never sustained anything close to daily — a contract the
  # reconciled reality contradicts. A steward revises this against ground truth.
  delivery_cadence: daily
  bar: "principles.md pre-ship audit — voice fingerprint + anti-slop + continuity"
  rough_volume_per_window: "~1 piece per DAY (floor-gated)"
"""

FRAMING_PROMPT = (
    "Assess the operation against its mandate and its declared contract. The rules "
    "of judgment are in principles.md; the frame owns how you close. If the declared "
    "contract conflicts with what ground truth shows the operation can sustain, that "
    "conflict is itself a thing to act on."
)


def _read_path(client, path: str) -> tuple[str, str | None]:
    r = client.table("workspace_files").select("content, head_version_id").eq(
        "user_id", USER_ID).eq("path", path).limit(1).execute()
    rows = r.data or []
    if not rows:
        return "", None
    return (rows[0].get("content") or ""), rows[0].get("head_version_id")


async def _seed(client) -> str | None:
    from services.authored_substrate import write_revision
    rev = write_revision(
        client, user_id=USER_ID, path=EXPECTED_OUTPUT_PATH, content=STALE_CONTRACT,
        authored_by="operator",
        message="probe: seed a stale 'daily' contract ground-truth contradicts (ADR-366 self-revision test)",
    )
    return rev


async def main() -> int:
    from services.supabase import get_service_client
    from services.platform_limits import get_effective_balance
    client = get_service_client()

    print(f"[adr366-probe] user={USER_ID}  effective_balance=${get_effective_balance(client, USER_ID):.2f}")

    # Seed the stale contract (the corrected header + an implausible cadence).
    seed_rev = await _seed(client)
    _before_content, before_head = _read_path(client, EXPECTED_OUTPUT_PATH)
    print(f"[adr366-probe] seeded stale contract (cadence=daily) rev={(seed_rev or '')[:8]}  head={before_head[:8] if before_head else '?'}")
    print("[adr366-probe] the question: under autonomous, does the Reviewer REVISE this")
    print("               contract/ path (newly unlocked by ADR-366) — or Clarify about it?")

    if "--live" not in sys.argv:
        print("\n--- contract seed (the agent will perceive this) ---")
        print(STALE_CONTRACT)
        print("[adr366-probe] dry-run only. Pass --live to fire the funded wake.")
        return 0

    from services.wake import _invoke_recurrence_wake
    from services.recurrence import Recurrence

    slug = f"adr366-contract-{int(_t.time())}"
    rec = Recurrence(
        slug=slug, schedule="0 10 * * 1", prompt=FRAMING_PROMPT,
        mode="judgment", required_capabilities=[], options={"produces_owed_output": True},
    )
    print(f"\n[adr366-probe] firing {slug} (autonomous) through _invoke_recurrence_wake...")
    out = await _invoke_recurrence_wake(
        client, USER_ID, recurrence=rec, wake_source="cron_tick", context="",
    ) or {}
    print(f"[adr366-probe] verdict={out.get('verdict')} rounds={out.get('tool_rounds')} status={out.get('success')}")

    # Did the contract path get revised THIS cycle?
    _after_content, after_head = _read_path(client, EXPECTED_OUTPUT_PATH)
    revised_contract = after_head is not None and after_head != before_head

    # What else did the Reviewer write this cycle? (look at recent reviewer revisions)
    since_iso = "2026-06-25T00:00:00Z"
    r = client.table("workspace_file_versions").select("path, authored_by, message, created_at").eq(
        "user_id", USER_ID).gte("created_at", since_iso).order("created_at", desc=True).limit(15).execute()
    recent = [x for x in (r.data or []) if (x.get("authored_by") or "").startswith("reviewer:")]
    wrote_paths = [x["path"].replace("/workspace/", "") for x in recent]

    # Did it Clarify? (proposal of family clarify or a clarify action — check action_proposals)
    ap = client.table("action_proposals").select("status, family, created_at").eq(
        "user_id", USER_ID).order("created_at", desc=True).limit(3).execute()
    recent_proposals = [(a.get("family"), a.get("status")) for a in (ap.data or [])]

    print("\n=== STRUCTURAL READ ===")
    print(f"  [{'PASS' if revised_contract else 'WATCH'}] contract/_expected_output.yaml REVISED this cycle "
          f"(head {before_head[:8] if before_head else '?'} -> {after_head[:8] if after_head else '?'})")
    print(f"  reviewer wrote this cycle: {wrote_paths or '(none)'}")
    print(f"  recent action_proposals: {recent_proposals or '(none)'}")
    print()
    if revised_contract:
        print("  => ADR-366 CLOSED THE LOOP: the Reviewer self-revised a contract/ path that was")
        print("     DENY-locked before ADR-366 — topology unlock moved behavior to self-revision.")
        _after_content, _ = _read_path(client, EXPECTED_OUTPUT_PATH)
        print("\n--- revised contract (excerpt) ---")
        print(_after_content[:600])
    else:
        wrote_any_shadowed = any(p.startswith(("contract/", "constitution/")) for p in wrote_paths)
        if wrote_any_shadowed:
            print("  => PARTIAL: revised another previously-shadowed path (constitution/) but not the")
            print("     contract — still evidence the unlock moves behavior; read the trace.")
        else:
            print("  => STALL PERSISTS: did not revise the contract despite the unlock. If it Clarified")
            print("     about a now-writable path, the DP30 'resolve-within-floor on repeated Clarify'")
            print("     limb is still needed (finding move 2). Read the judgment_log to confirm the shape.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

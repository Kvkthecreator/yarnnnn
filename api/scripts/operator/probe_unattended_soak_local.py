"""Unattended-soak probe — the SUSTAIN claim (full-autonomy floor, 2026-06-24).

The audit (2026-06-24-reflection-loop... session) established: the autonomous
loop is PROVEN per-wake (trader self-executes, author composes, ADR-360 kernel
9/9) but every demonstration is SINGLE-WAKE, reset-isolated. The SUSTAIN claim —
N consecutive unattended wakes, accumulating state, NO reset, NO operator — is
structurally untested by any episodic suite. This probe is that instrument.

It fires N judgment wakes back-to-back through the FAITHFUL production path
(_invoke_recurrence_wake, the path the reference probes + ADR-360 E2E use), with
NO persona reset between fires (memory accumulates — the whole point), and reads
STRUCTURAL signals per wake from the authoritative receipts (execution_events +
workspace_file_versions), NOT from the output dict (which the reference probes
showed can be None even on success).

  Baseline: snapshot persona FIRST (persona_snapshot.snapshot_persona) so the
    soak is re-runnable from a known state. The corpus (operation/) is NOT
    reset — its accumulation across wakes is part of the signal.

  Per-wake structural reads:
    - CYCLE-CLOSURE (S9): the wake left a receipt — non-NULL output_tokens AND a
      substrate write (content.md | standing_intent | reflection | judgment_log).
      A status=failed or NULL-telemetry wake is the silent-wake defect — counted.
    - ORIGINATION: did the wake produce the owed output (a content.md write)?
    - PRIOR-STATE-INFORMS-NEXT (the continuity signal — why we DON'T reset):
      does wake K write fresh standing_intent / reflection (carrying its prior
      cycle forward), vs. a static repeat?
    - ANTI-PATTERNS: runaway cost (per-wake cost trend), repetition (near-
      duplicate content.md slugs), silent failures.

  The structural reads are the GATE; the human reads the per-wake trace for
  coherence (does wake K's reasoning reference wake K-1's state, does the corpus
  cohere rather than drift). Pure Hat-B.

Usage:
  # offline dry-run (FREE — snapshot + read current state, NO fires):
  cd /Users/macbook/yarnnn && .venv/bin/python -m api.scripts.operator.probe_unattended_soak_local
  # funded soak (N fires, default 5):
  cd /Users/macbook/yarnnn && .venv/bin/python -m api.scripts.operator.probe_unattended_soak_local --live --n 5
  # restore persona to the pre-soak baseline afterwards:
  cd /Users/macbook/yarnnn && .venv/bin/python -m api.scripts.operator.probe_unattended_soak_local --restore
"""

from __future__ import annotations

import asyncio
import sys
import time as _t  # local clock only for slug uniqueness + soak-window timing, never for logic
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
PERSONA = "yarnnn-author"

# Situation-forward framing (NOT a task-label script) — the ADR-360 ask-builder
# shapes the imperative; this points at the mandate. Each wake the agent decides
# what the operation needs and acts (compose) or honestly surfaces (Clarify).
FRAMING_PROMPT = (
    "Assess the operation against its mandate and serve what it owes. The rules "
    "of judgment are in principles.md; the frame owns how you close."
)

_SNAPSHOT_FILE = Path("/private/tmp/claude-501/-Users-macbook-yarnnn") / "persona_soak_baseline.json"


def _persona_state(client, user_id: str) -> dict:
    """Read the agent's persona learning-state heads (for prior-state-informs-next)."""
    from services.operator_proxy.persona_snapshot import snapshot_persona
    blob = snapshot_persona(client, user_id)
    return {p: (len(c) if c else 0) for p, c in blob.items()}


def _content_slugs(client, user_id: str) -> set[str]:
    res = (
        client.table("workspace_files").select("path")
        .eq("user_id", user_id).like("path", "%/content.md").execute()
    )
    return {r["path"] for r in (res.data or [])}


def _latest_event(client, user_id: str) -> dict | None:
    res = (
        client.table("execution_events")
        .select("status,output_tokens,cost_usd,tool_rounds,wake_source,funnel_decision,created_at")
        .eq("user_id", user_id).order("created_at", desc=True).limit(1).execute()
    )
    return (res.data or [None])[0]


def _persona_writes_since(client, user_id: str, since_iso: str) -> list[dict]:
    res = (
        client.table("workspace_file_versions")
        .select("path,authored_by,message,created_at")
        .eq("user_id", user_id).gte("created_at", since_iso)
        .order("created_at", desc=True).limit(40).execute()
    )
    # Reviewer-authored writes only (the agent acting), not system mirrors.
    return [r for r in (res.data or []) if (r.get("authored_by") or "").startswith("freddie:")]


async def _fire_one(client, user_id: str, idx: int) -> dict:
    from services.wake import _invoke_recurrence_wake
    from services.recurrence import Recurrence

    slug = f"soak-{idx}-{int(_t.time())}"  # fresh slug per fire (dodge 60s min-interval skip)
    rec = Recurrence(
        slug=slug, schedule="0 10 * * 1", prompt=FRAMING_PROMPT,
        mode="judgment", required_capabilities=[], options={"produces_owed_output": True},
    )
    out = await _invoke_recurrence_wake(
        client, user_id, recurrence=rec, wake_source="cron_tick", context="",
    ) or {}
    return {"slug": slug, "out_keys": sorted(out.keys())}


async def soak(client, user_id: str, n: int) -> None:
    from services.operator_proxy.persona_snapshot import snapshot_persona
    import json

    print(f"\n=== UNATTENDED SOAK — {n} wakes, NO reset between fires (FUNDED) ===")

    # Snapshot the pre-soak baseline so the soak is re-runnable.
    baseline = snapshot_persona(client, user_id)
    _SNAPSHOT_FILE.parent.mkdir(parents=True, exist_ok=True)
    _SNAPSHOT_FILE.write_text(json.dumps(baseline))
    present = [p for p, c in baseline.items() if c]
    print(f"[soak] baseline snapshot saved ({len(present)} persona files present) → {_SNAPSHOT_FILE.name}")

    rows: list[dict] = []
    prev_slugs = _content_slugs(client, user_id)
    prev_state = _persona_state(client, user_id)

    for i in range(1, n + 1):
        # window-start marker so we attribute writes to THIS wake
        before = _latest_event(client, user_id)
        before_ts = (before or {}).get("created_at", "2000-01-01T00:00:00Z")
        print(f"\n[soak] --- wake {i}/{n} firing (no reset; memory carries fwd) ---")
        fired = await _fire_one(client, user_id, i)

        ev = _latest_event(client, user_id) or {}
        new_slugs = _content_slugs(client, user_id)
        composed = new_slugs - prev_slugs
        writes = _persona_writes_since(client, user_id, before_ts)
        wrote_paths = {w["path"].replace("/workspace/", "") for w in writes}
        state = _persona_state(client, user_id)
        state_moved = {p: (prev_state[p], state[p]) for p in state if state[p] != prev_state[p]}

        out_tok = ev.get("output_tokens")
        closed = bool(out_tok) and ev.get("status") == "success" and bool(writes)
        originated = bool(composed)
        row = {
            "wake": i, "status": ev.get("status"), "out_tok": out_tok,
            "cost": ev.get("cost_usd"), "rounds": ev.get("tool_rounds"),
            "closed": closed, "originated": originated,
            "composed": sorted(s.replace("/workspace/operation/authored/", "").replace("/content.md", "") for s in composed),
            "wrote": sorted(p for p in wrote_paths if p.startswith("persona/")),
            "state_moved": state_moved,
        }
        rows.append(row)
        print(f"  status={row['status']} out={out_tok} cost={row['cost']} rounds={row['rounds']}")
        print(f"  CLOSED(S9)={closed}  ORIGINATED={originated}  composed={row['composed']}")
        print(f"  persona writes={row['wrote']}  state_moved={state_moved}")
        prev_slugs = new_slugs
        prev_state = state

    # ---- structural soak summary ----
    print("\n=== SOAK STRUCTURAL SUMMARY ===")
    closed_n = sum(1 for r in rows if r["closed"])
    orig_n = sum(1 for r in rows if r["originated"])
    failed_n = sum(1 for r in rows if r["status"] != "success")
    costs = [r["cost"] for r in rows if isinstance(r["cost"], (int, float))]
    total_cost = sum(costs)
    all_composed = [c for r in rows for c in r["composed"]]
    dup = len(all_composed) != len(set(all_composed))
    moved_each = sum(1 for r in rows if r["state_moved"])

    print(f"  [{'PASS' if closed_n == n else 'WATCH'}] cycle-closure (S9): {closed_n}/{n} wakes left a full receipt")
    print(f"  [{'PASS' if failed_n == 0 else 'FAIL'}] no silent/failed wakes: {failed_n} failures")
    print(f"  [info] origination: {orig_n}/{n} wakes composed the owed output ({sorted(set(all_composed))})")
    print(f"  [{'PASS' if moved_each >= n-1 else 'WATCH'}] prior-state-carries: persona state moved on {moved_each}/{n} wakes "
          f"(standing_intent/reflection rewritten → the loop carries forward)")
    print(f"  [{'WATCH' if dup else 'PASS'}] no duplicate-slug repetition: {'DUPLICATE content slugs seen' if dup else 'distinct'}")
    print(f"  [info] cost trend per wake: {[r['cost'] for r in rows]}  total=${total_cost:.2f}")
    print("\n  HUMAN READ (the judgment half): read each wake's transcript — does wake K's")
    print("  reasoning reference wake K-1's standing_intent/reflection (continuity), and does")
    print("  the accumulating corpus COHERE rather than drift/repeat? Structural gates above")
    print("  gate trustworthiness; the coherence read is yours.")


async def main() -> int:
    from services.supabase import get_service_client
    import json
    client = get_service_client()
    print(f"[soak] user={USER_ID} persona={PERSONA}")

    if "--restore" in sys.argv:
        from services.operator_proxy.persona_snapshot import restore_persona
        if not _SNAPSHOT_FILE.exists():
            print("[soak] no baseline snapshot to restore.")
            return 1
        blob = json.loads(_SNAPSHOT_FILE.read_text())
        res = await restore_persona(client, USER_ID, blob, persona=PERSONA)
        print(f"[soak] restored persona to baseline: {res}")
        return 0

    # Offline dry-run: show current persona + corpus state, no fires.
    print("\n=== DRY-RUN (FREE) — current state, no fires ===")
    print(f"  persona state (char counts): {_persona_state(client, USER_ID)}")
    print(f"  corpus content.md count: {len(_content_slugs(client, USER_ID))}")

    if "--live" in sys.argv:
        n = 5
        if "--n" in sys.argv:
            n = int(sys.argv[sys.argv.index("--n") + 1])
        await soak(client, USER_ID, n)
    else:
        print("\n[soak] dry-run only (free). Pass --live --n N to fire the funded soak; "
              "--restore to roll persona back to the saved baseline.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

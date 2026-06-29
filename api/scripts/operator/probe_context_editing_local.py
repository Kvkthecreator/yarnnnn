"""ADR-363 D3 probe — within-wake context-editing A/B (clear_tool_uses_20250919).

THE QUESTION (probe-before-canon): does wiring Anthropic context-editing into the
Reviewer wake loop relieve the max_rounds=20 ceiling that truncates long wakes
(verdict=None) — OR, where the ceiling isn't the binding constraint, give EQUAL
behavior at LOWER token cost by pruning accumulated tool-result bloat?

The re-audit (context-handling-reaudit-2026-06-24) named context-editing as the
genuinely-new wake territory. ADR-363 D3 gates it on THIS measurement before
Proposed→Implemented. Production history on the funded workspace
(execution_events, last 30d) shows the long tail is real — wakes at tool_rounds=20
average ~700k cache-read tokens of accumulated tool bloat — but verdict=None is
RARE (1 in 30d). So the honest hypothesis is: D3's win is COST on the long-tail
read-heavy wake, not verdict-rescue. This probe measures both and reports which.

ARMS (same recurrence prompt, same funded workspace, fired back-to-back):
  - CONTROL  : YARNNN_CONTEXT_EDIT unset → pre-ADR-363 path (no context_management).
  - TREATMENT: YARNNN_CONTEXT_EDIT=on    → clear_tool_uses_20250919 wired in, with
               trigger + keep as the two tuned probe variables.

The reproducer is the REAL corpus-coherence-check prompt (a cross-corpus read-heavy
judgment recurrence that hit tool_rounds=20 on this workspace) — so the control arm
authentically accumulates the loop bloat context-editing is meant to prune.

METRICS (read from the wake's own FreddieOutput + the execution_events row):
  - verdict           : a real model verdict vs None (the ceiling-truncation signal)
  - tool_rounds       : did it hit the ceiling (20)?
  - input_tokens      : uncached billed input (the cost lever)
  - cache_read_tokens : accumulated cached prefix (bloat proxy)

ADOPT / HOLD read:
  - ADOPT if treatment shows EITHER (a) lower verdict=None / lower rounds on a
    ceiling-hitting wake (behavioral relief), OR (b) materially lower input/cache
    tokens at EQUAL verdict quality (cost win). Either satisfies D3.
  - HOLD if treatment changes the verdict (lost mid-loop substrate the verdict
    rested on) — that's the mid-loop-safety failure mode; tighten `keep` and re-run.

Funded fresh-state yarnnn-author. Each arm is one funded wake. Run treatment at a
couple of `keep` values (env) to find the safe threshold, per the safety analysis.

Usage:
  cd /Users/macbook/yarnnn && .venv/bin/python -m api.scripts.operator.probe_context_editing_local
  # tune the treatment threshold:
  YARNNN_CONTEXT_EDIT_KEEP=4 YARNNN_CONTEXT_EDIT_TRIGGER=20000 .venv/bin/python -m api.scripts.operator.probe_context_editing_local
"""

from __future__ import annotations

import asyncio
import os
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

# Funded yarnnn-author (the methodology's substrate).
USER_ID = "0b7a852d-4a67-447d-91d9-2ba1145a60d7"

# The REAL corpus-coherence-check prompt (alpha-author bundle) — a cross-corpus
# read-heavy judgment recurrence observed hitting tool_rounds=20 on this workspace.
# Using the authentic prompt makes the control arm accumulate the loop bloat that
# context-editing is meant to prune; a synthetic prompt would not reproduce it.
COHERENCE_PROMPT = (
    "Assess the operation against its mandate — both the COHERENCE of what exists "
    "and whether the operation is PRODUCING what it owes. "
    "Coherence (when a corpus exists): aggregate voice-audit drift, cross-piece "
    "continuity, and cadence health across the published corpus "
    "(/workspace/operation/authored/{slug}/content.md, status=published; _voice.md "
    "fingerprint), and write the coherence slice to "
    "/workspace/operation/authored/_signal.md per "
    "/workspace/operation/specs/corpus-coherence-rollup.md. "
    "Production (always): your mandate's Expected Output is a STANDING OBLIGATION "
    "(governance/_expected_output.yaml + MANDATE ## Expected Output). An empty or "
    "flat corpus under a declared output contract is not a neutral fact — it is the "
    "obligation unmet, and you classify why (principles.md §2 owed-output rule). The "
    "rules of judgment are in principles.md; the frame owns how you close."
)


async def _fire(client, *, context_edit: bool, label: str, keep: str | None = None) -> dict:
    """Fire one corpus-coherence-style wake through the production path under the
    given arm. Toggles YARNNN_CONTEXT_EDIT (and, for the sweep, KEEP) in-process so
    the ONLY difference between arms is the context_management config reaching the
    API call."""
    from services.wake import _invoke_recurrence_wake
    from services.recurrence import Recurrence

    # In-process arm toggle. Restore prior values after the fire (singular env state).
    _prev_edit = os.environ.get("YARNNN_CONTEXT_EDIT")
    _prev_keep = os.environ.get("YARNNN_CONTEXT_EDIT_KEEP")
    if context_edit:
        os.environ["YARNNN_CONTEXT_EDIT"] = "on"
        if keep is not None:
            os.environ["YARNNN_CONTEXT_EDIT_KEEP"] = keep
    else:
        os.environ.pop("YARNNN_CONTEXT_EDIT", None)

    keep = os.environ.get("YARNNN_CONTEXT_EDIT_KEEP", "6")
    trig = os.environ.get("YARNNN_CONTEXT_EDIT_TRIGGER", "24000")

    # Unique slug per fire (min-interval floor: distinct slugs avoid the 60s skip).
    slug = f"ctxedit-{'on' if context_edit else 'off'}-{int(_t.time())}"
    recurrence = Recurrence(
        slug=slug, schedule="0 12 * * 1,4", prompt=COHERENCE_PROMPT,
        mode="judgment", required_capabilities=[],
        options={"produces_owed_output": True},
    )
    print(f"\n[{label}] firing {slug} "
          f"(context_edit={context_edit}"
          + (f", keep={keep}, trigger={trig}" if context_edit else "")
          + ") ...")

    out = await _invoke_recurrence_wake(
        client, USER_ID, recurrence=recurrence, wake_source="cron_tick", context="",
    ) or {}

    # Restore env.
    if _prev_edit is None:
        os.environ.pop("YARNNN_CONTEXT_EDIT", None)
    else:
        os.environ["YARNNN_CONTEXT_EDIT"] = _prev_edit
    if _prev_keep is None:
        os.environ.pop("YARNNN_CONTEXT_EDIT_KEEP", None)
    else:
        os.environ["YARNNN_CONTEXT_EDIT_KEEP"] = _prev_keep

    # The wake's return dict is thin (success/summary). The metrics live on the
    # execution_events row it just wrote. Read the most-recent row for this slug.
    ev = (
        client.table("execution_events")
        .select("status, error_reason, tool_rounds, input_tokens, output_tokens, "
                "cache_read_tokens, cache_create_tokens, created_at")
        .eq("user_id", USER_ID).eq("slug", slug)
        .order("created_at", desc=True).limit(1).execute()
    )
    row = (ev.data or [{}])[0]

    # verdict: the wake summary carries the model's close; a `failed` /
    # reviewer_returned_none row IS the verdict=None signal.
    verdict_none = (
        row.get("status") == "failed"
        and row.get("error_reason") == "reviewer_returned_none"
    )
    result = {
        "label": label,
        "slug": slug,
        "context_edit": context_edit,
        "keep": keep if context_edit else None,
        "trigger": trig if context_edit else None,
        "status": row.get("status"),
        "error_reason": row.get("error_reason"),
        "verdict_none": verdict_none,
        "tool_rounds": row.get("tool_rounds"),
        "input_tokens": row.get("input_tokens"),
        "output_tokens": row.get("output_tokens"),
        "cache_read_tokens": row.get("cache_read_tokens"),
        "cache_create_tokens": row.get("cache_create_tokens"),
        "summary": (out.get("summary") or "")[:160],
    }
    print(f"[{label}] status={result['status']} verdict_none={verdict_none} "
          f"rounds={result['tool_rounds']} input={result['input_tokens']} "
          f"cache_read={result['cache_read_tokens']}")
    return result


def _fmt(v) -> str:
    return "—" if v is None else str(v)


async def main() -> int:
    from services.supabase import get_service_client
    client = get_service_client()

    print("=" * 72)
    print("ADR-363 D3 PROBE — within-wake context-editing keep-sweep (3 arms)")
    print("Funded yarnnn-author. control + treatment@keep=6 + treatment@keep=3.")
    print("=" * 72)

    control = await _fire(client, context_edit=False, label="CONTROL ")
    treat6 = await _fire(client, context_edit=True, label="KEEP=6  ", keep="6")
    treat3 = await _fire(client, context_edit=True, label="KEEP=3  ", keep="3")

    arms = [("control", control), ("keep=6", treat6), ("keep=3", treat3)]

    print("\n" + "=" * 72)
    print("RESULT")
    print("=" * 72)
    hdr = f"{'metric':<18}" + "".join(f"{name:>14}" for name, _ in arms)
    print(hdr)
    print("-" * len(hdr))
    for key, name in [
        ("status", "status"),
        ("verdict_none", "verdict=None"),
        ("tool_rounds", "tool_rounds"),
        ("input_tokens", "input(uncach)"),
        ("cache_read_tokens", "cache_read"),
        ("cache_create_tokens", "cache_create"),
    ]:
        print(f"{name:<18}" + "".join(f"{_fmt(a.get(key)):>14}" for _, a in arms))
    print(f"trigger={treat6.get('trigger')}")

    # ADOPT / HOLD read per treatment arm, vs the shared control.
    print("\n" + "-" * 72)
    c_in = control.get("input_tokens") or 0
    c_cr = control.get("cache_read_tokens") or 0
    c_vn = control.get("verdict_none")
    c_rounds = control.get("tool_rounds") or 0

    def _read(name: str, t: dict) -> None:
        t_in = t.get("input_tokens") or 0
        t_cr = t.get("cache_read_tokens") or 0
        t_vn = t.get("verdict_none")
        t_rounds = t.get("tool_rounds") or 0
        if (not c_vn) and t_vn:
            print(f"[{name}] HOLD (mid-loop safety): control gave a verdict, this arm "
                  f"did NOT (verdict=None) — likely pruned substrate the verdict "
                  f"rested on. Raise `keep`.")
        elif c_vn and (not t_vn):
            print(f"[{name}] ADOPT (behavioral relief): control verdict=None, this arm "
                  f"produced a verdict — relieved the ceiling.")
        else:
            in_delta, cr_delta = (c_in - t_in), (c_cr - t_cr)
            rn = f" (rounds {c_rounds}→{t_rounds})" if (t_rounds and c_rounds and t_rounds < c_rounds) else ""
            if in_delta > 0 or cr_delta > 0:
                pct = (100 * in_delta / c_in) if c_in else 0
                print(f"[{name}] ADOPT (cost win, equal verdict): input {c_in}→{t_in} "
                      f"(−{in_delta}, −{pct:.0f}%), cache_read {c_cr}→{t_cr} "
                      f"(−{cr_delta}){rn}.")
            else:
                print(f"[{name}] HOLD (no win): equal verdict, no token reduction "
                      f"(input {c_in}→{t_in}, cache_read {c_cr}→{t_cr}). Trigger "
                      f"({t.get('trigger')}) likely didn't fire — lower it or use a "
                      f"longer-tail recurrence.")

    _read("keep=6", treat6)
    _read("keep=3", treat3)
    print("\nSAFE-THRESHOLD READ: the lowest `keep` that ADOPTs WITHOUT flipping the "
          "verdict is the candidate. keep=3 cheaper if it holds the verdict; keep=6 "
          "the safer floor if keep=3 flips it.")
    print("NOTE: one funded wake per arm = a single observation. Re-run 2–3× before "
          "treating the adopt/hold read as settled.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

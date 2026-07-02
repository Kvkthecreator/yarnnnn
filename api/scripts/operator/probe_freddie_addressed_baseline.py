"""Freddie addressed-turn baseline — Rung 0 of the envelope refactor plan
(docs/analysis/freddie-envelope-refactor-plan-2026-07-02.md).

Fires N program-neutral, steward-shaped addressed asks through the REAL
addressed wake source (services/wake_sources/addressed.py::stream — the same
path routes/feed.py drives) against the bare-kernel persona workspace, and
captures per-turn behavior metrics:

  - wall-clock seconds
  - tool calls (count + names, in order)
  - final response text + char length (the wordiness metric)
  - verdict reached (close rate)
  - full event transcript (JSON)

Every refactor rung re-runs this exact set and diffs against the captured
baseline. The harness runs LOCAL code (not the deployed API) so a rung's
edits are measurable before a deploy.

Usage:
  # capture a run (writes docs/evaluations/<label>/ transcripts):
  cd /Users/macbook/yarnnn && .venv/bin/python -m api.scripts.operator.probe_freddie_addressed_baseline --label 2026-07-02-freddie-envelope-baseline

  # single-ask smoke (cheap):
  cd /Users/macbook/yarnnn && .venv/bin/python -m api.scripts.operator.probe_freddie_addressed_baseline --label smoke --only 1
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import uuid
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
_API_ROOT = _THIS_DIR.parents[1]
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))
REPO_ROOT = _THIS_DIR.parents[2]

from dotenv import load_dotenv  # noqa: E402
load_dotenv(_API_ROOT / ".env.alpha-ops")
load_dotenv(REPO_ROOT / ".env")

# bare-kernel persona (docs/alpha/personas.yaml — program: null, steward
# defaults). Same workspace the bare-steward wake probe uses, so the two
# baselines describe one Freddie.
USER_ID = "4c106786-c9b4-41cb-982d-0f5a8cc35923"

# Program-neutral steward-shaped asks — mirrors the operator's reported
# experience surface (simple reads, placement, activity, a remember-write,
# a stewardship sweep, perception). Do NOT reword between runs: the diff
# across rungs depends on the asks being byte-identical.
ASKS = [
    "What's in my workspace right now?",
    "I want to keep a note: our Q3 pricing decision is to hold the $19 tier until August. Make sure that's recorded somewhere sensible.",
    "Summarize what you've been doing in this workspace lately.",
    "Is anything in the workspace out of place or needing cleanup?",
    "What connections and sources are currently feeding this workspace?",
    "What should I look at first when I come back tomorrow?",
]


async def _fire_one(client, ask: str, idx: int) -> dict:
    from services.wake_sources.addressed import stream as wake_addressed_stream

    session_id = f"probe-baseline-{uuid.uuid4()}"
    invocation_id = str(uuid.uuid4())
    events: list[dict] = []
    tools: list[str] = []
    rounds = 0
    response_text = ""
    verdict_reached = False
    error = None

    t0 = time.monotonic()
    try:
        async for event in wake_addressed_stream(
            client, USER_ID,
            session_id=session_id,
            invocation_id=invocation_id,
            user_message=ask,
            conversation_window="",
        ):
            etype = event.get("type")
            events.append(event)
            if etype == "progress":
                ev = event.get("event") or {}
                phase = ev.get("phase")
                if phase == "tool_start" and ev.get("tool"):
                    tools.append(ev.get("tool"))
                elif phase == "round_start":
                    rounds += 1
            elif etype == "reviewer_response":
                response_text = event.get("text", "")
            elif etype == "error":
                error = event.get("error")
    except Exception as exc:  # noqa: BLE001
        error = f"{type(exc).__name__}: {exc}"
    wall_s = round(time.monotonic() - t0, 1)
    verdict_reached = any(t == "ReturnVerdict" for t in tools) or bool(response_text)

    return {
        "idx": idx,
        "ask": ask,
        "wall_s": wall_s,
        "rounds": rounds,
        "tool_calls": tools,
        "n_tool_calls": len(tools),
        "response_chars": len(response_text),
        "response_text": response_text,
        "verdict_reached": verdict_reached,
        "error": error,
        "events": events,
    }


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True,
                    help="evaluation folder name under docs/evaluations/")
    ap.add_argument("--only", type=int, default=None,
                    help="fire only ask #N (1-based) as a cheap smoke")
    args = ap.parse_args()

    from services.supabase import get_service_client
    client = get_service_client()

    out_dir = REPO_ROOT / "docs" / "evaluations" / args.label
    out_dir.mkdir(parents=True, exist_ok=True)

    asks = ASKS if args.only is None else [ASKS[args.only - 1]]
    results = []
    for i, ask in enumerate(asks, start=1):
        idx = args.only if args.only is not None else i
        print(f"\n=== ask {idx}/{len(ASKS)}: {ask[:60]}...")
        r = await _fire_one(client, ask, idx)
        results.append(r)
        print(f"    wall={r['wall_s']}s tools={r['n_tool_calls']} "
              f"{r['tool_calls']} chars={r['response_chars']} "
              f"closed={r['verdict_reached']} err={r['error']}")
        (out_dir / f"turn-{idx}.json").write_text(
            json.dumps(r, indent=2, default=str))

    summary = {
        "user_id": USER_ID,
        "n_turns": len(results),
        "closed": sum(1 for r in results if r["verdict_reached"]),
        "errors": sum(1 for r in results if r["error"]),
        "mean_wall_s": round(sum(r["wall_s"] for r in results) / max(len(results), 1), 1),
        "mean_rounds": round(sum(r["rounds"] for r in results) / max(len(results), 1), 1),
        "mean_tool_calls": round(sum(r["n_tool_calls"] for r in results) / max(len(results), 1), 1),
        "mean_response_chars": round(sum(r["response_chars"] for r in results) / max(len(results), 1)),
        "turns": [{k: r[k] for k in ("idx", "ask", "wall_s", "rounds",
                                     "n_tool_calls", "tool_calls",
                                     "response_chars", "verdict_reached",
                                     "error")} for r in results],
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    print("\n=== SUMMARY ===")
    print(json.dumps({k: v for k, v in summary.items() if k != "turns"}, indent=2))
    print(f"\ntranscripts → {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

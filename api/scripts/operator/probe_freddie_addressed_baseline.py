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

CURRENT BASELINE (the canonical diff target) is declared in code below as
CURRENT_BASELINE — a run with any other --label prints a mean-delta diff
against it automatically. Rotating the baseline = changing that constant
(same commit as the run that earns the rotation). The Haiku-era captures
(2026-07-02-freddie-envelope-baseline, rung3-*, rung4-partA-haiku) are
historical arms, not diff targets, since the ADR-402 Part-B decision
(ONE model = claude-sonnet-4-6, all shapes).

USAGE + COST are first-class (2026-07-03): each turn JSON and summary.json
carry a `usage` block (tokens/model/rounds/verdict + estimated API cost at
Anthropic list rates — NOTE the product ledger bills 2x list per ADR-172).
Extracted from the `reviewer_response` event's full FreddieOutput.

SENTINELS (the Haiku-signature watchlist, inverted to regression alarms on
Sonnet — see docs/evaluations/2026-07-03-rung4-partB-sonnet-addressed/README):
  - silent_exit: a turn closing with no verdict/response (Haiku ~1/12) —
    ALARM on ANY occurrence in a Sonnet run.
  - schedule_calls: any Schedule/recurrence write from a probe ask — probe
    asks are disposable exercises (steward principles seed
    `test-exercises-stay-disposable`, CHANGELOG 2026.07.03.1); ALARM on any.

LEDGER GAP (documented, deliberate): local addressed runs write NO
execution_events row — record_execution_event for addressed wakes is owned
by routes/feed.py (the SSE route layer), which this probe bypasses by
driving services/wake_sources/addressed.py directly. The probe does NOT
synthesize a ledger row: execution_events is the live billing/budget
substrate (services/budget.window_spend gates real wakes on it), and
injecting local-probe spend would consume the workspace's real budget
window and distort the ADR-291 cost ledger. The probe's own `usage` block
is the cost record for local runs. (The related prod hole — an addressed
wake dropped on SSE-timeout disconnect leaves no row — is the known
ADR-291 gap, tracked in memory project_wake_is_pre_authored_ask.)

Usage:
  # capture a run (writes docs/evaluations/<label>/ transcripts):
  cd /Users/macbook/yarnnn && .venv/bin/python -m api.scripts.operator.probe_freddie_addressed_baseline --label <dated-label>

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

# The canonical diff baseline (docs/evaluations/<label>/). Rotate ONLY with
# a decision-grade run + its FINDING doc, in the same commit.
#   2026-07-03: rotated to the ADR-402 Part-B Sonnet landed run (6/6, mean
#   34.8s / 3.3 rounds / 4.2 tools / 546 chars). Prior Haiku-era baselines
#   are historical arms.
CURRENT_BASELINE = "2026-07-03-rung4-partB-sonnet-addressed"

# Anthropic LIST rates per Mtok (input, output, cache_read, cache_write) —
# the probe's cost estimate. The product ledger bills 2x list (ADR-172).
_RATES = {
    "haiku": (1.00, 5.00, 0.10, 1.25),
    "sonnet": (3.00, 15.00, 0.30, 3.75),
    "opus": (15.00, 75.00, 1.50, 18.75),
}


def _estimate_cost_usd(usage: dict) -> float | None:
    """Estimate API cost at Anthropic list rates from a FreddieOutput usage
    slice. Returns None when the model tier is unrecognized."""
    model = (usage.get("model") or "").lower()
    rates = next((r for tier, r in _RATES.items() if tier in model), None)
    if rates is None:
        return None
    in_r, out_r, cr_r, cw_r = rates
    return round(
        (usage.get("input_tokens") or 0) * in_r / 1e6
        + (usage.get("output_tokens") or 0) * out_r / 1e6
        + (usage.get("cache_read_tokens") or 0) * cr_r / 1e6
        + (usage.get("cache_create_tokens") or 0) * cw_r / 1e6,
        4,
    )


# The silent-exit signature: the loop completed but the model returned no
# reasoning — stream_addressed_wake surfaces it as this exact error string
# (wake.py: `if not output or not output.get("reasoning")`). Distinct from
# infra errors (lock_wait_timeout, exceptions), which are NOT silent exits.
_SILENT_EXIT_ERROR = "Reviewer returned no response"


def _is_silent_exit(verdict_reached: bool, error) -> bool:
    if error == _SILENT_EXIT_ERROR:
        return True
    return (not verdict_reached) and error is None


def extract_usage(events: list[dict]) -> dict:
    """Pull the usage/model/verdict slice from the reviewer_response event's
    full FreddieOutput (services/wake.py stream_addressed_wake yields it as
    event["output"]). Reusable over previously-captured turn JSONs."""
    for e in events:
        if e.get("type") == "reviewer_response":
            out = e.get("output") or {}
            usage = {
                k: out.get(k)
                for k in (
                    "input_tokens", "output_tokens", "cache_read_tokens",
                    "cache_create_tokens", "model", "tool_rounds", "verdict",
                )
            }
            usage["est_cost_usd"] = _estimate_cost_usd(usage)
            return usage
    return {}

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
    usage = extract_usage(events)

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
        "usage": usage,
        # Sentinels (see module docstring): probe asks must stay disposable —
        # any Schedule call is a standing-cadence-from-test-asks alarm.
        "schedule_calls": sum(1 for t in tools if t == "Schedule"),
        "silent_exit": _is_silent_exit(verdict_reached, error),
        "events": events,
    }


def _reextract(label: str) -> int:
    """Recompute summary.json for an ALREADY-CAPTURED run from its turn-*.json
    files (no firing, no cost) — used to backfill the usage/cost block into
    pre-2026-07-03 captures whose raw events already carry FreddieOutput.
    Raw turn JSONs are never modified; only summary.json is re-emitted."""
    out_dir = REPO_ROOT / "docs" / "evaluations" / label
    turn_files = sorted(out_dir.glob("turn-*.json"),
                        key=lambda p: int(p.stem.split("-")[1]))
    if not turn_files:
        print(f"no turn-*.json under {out_dir}")
        return 1
    rows = []
    for tf in turn_files:
        r = json.loads(tf.read_text())
        r.setdefault("usage", extract_usage(r.get("events") or []))
        r.setdefault("schedule_calls",
                     sum(1 for t in r.get("tool_calls", []) if t == "Schedule"))
        # recompute unconditionally — older captures never carried the field,
        # and the signature includes the "returned no response" error form
        r["silent_exit"] = _is_silent_exit(
            bool(r.get("verdict_reached")), r.get("error"))
        rows.append(r)
    n = len(rows)
    costs = [r["usage"].get("est_cost_usd") for r in rows if r.get("usage")]
    costs = [c for c in costs if c is not None]
    models = sorted({r["usage"].get("model") for r in rows
                     if r.get("usage") and r["usage"].get("model")})
    summary = {
        "user_id": USER_ID,
        "n_turns": n,
        "closed": sum(1 for r in rows if r["verdict_reached"]),
        "errors": sum(1 for r in rows if r["error"]),
        "mean_wall_s": round(sum(r["wall_s"] for r in rows) / n, 1),
        "mean_rounds": round(sum(r["rounds"] for r in rows) / n, 1),
        "mean_tool_calls": round(sum(r["n_tool_calls"] for r in rows) / n, 1),
        "mean_response_chars": round(sum(r["response_chars"] for r in rows) / n),
        "models": models,
        "total_est_cost_usd": round(sum(costs), 4) if costs else None,
        "mean_est_cost_usd": round(sum(costs) / len(costs), 4) if costs else None,
        "sentinels": {
            "silent_exits": sum(1 for r in rows if r.get("silent_exit")),
            "schedule_calls": sum(r.get("schedule_calls", 0) for r in rows),
        },
        "reextracted": True,
        "turns": [{k: r.get(k) for k in ("idx", "ask", "wall_s", "rounds",
                                         "n_tool_calls", "tool_calls",
                                         "response_chars", "verdict_reached",
                                         "error", "usage", "schedule_calls",
                                         "silent_exit")} for r in rows],
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: v for k, v in summary.items() if k != "turns"}, indent=2))
    print(f"\nre-emitted {out_dir / 'summary.json'}")
    return 0


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True,
                    help="evaluation folder name under docs/evaluations/")
    ap.add_argument("--only", type=int, default=None,
                    help="fire only ask #N (1-based) as a cheap smoke")
    ap.add_argument("--reextract", action="store_true",
                    help="recompute summary.json (usage/cost/sentinels) from "
                         "the label's existing turn JSONs — no firing")
    args = ap.parse_args()

    if args.reextract:
        return _reextract(args.label)

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

    n = max(len(results), 1)
    costs = [r["usage"].get("est_cost_usd") for r in results if r.get("usage")]
    costs = [c for c in costs if c is not None]
    models = sorted({r["usage"].get("model") for r in results
                     if r.get("usage") and r["usage"].get("model")})
    summary = {
        "user_id": USER_ID,
        "n_turns": len(results),
        "closed": sum(1 for r in results if r["verdict_reached"]),
        "errors": sum(1 for r in results if r["error"]),
        "mean_wall_s": round(sum(r["wall_s"] for r in results) / n, 1),
        "mean_rounds": round(sum(r["rounds"] for r in results) / n, 1),
        "mean_tool_calls": round(sum(r["n_tool_calls"] for r in results) / n, 1),
        "mean_response_chars": round(sum(r["response_chars"] for r in results) / n),
        "models": models,
        "total_est_cost_usd": round(sum(costs), 4) if costs else None,
        "mean_est_cost_usd": round(sum(costs) / len(costs), 4) if costs else None,
        # Sentinel rollup — ALARM on any non-zero (module docstring).
        "sentinels": {
            "silent_exits": sum(1 for r in results if r.get("silent_exit")),
            "schedule_calls": sum(r.get("schedule_calls", 0) for r in results),
        },
        "turns": [{k: r[k] for k in ("idx", "ask", "wall_s", "rounds",
                                     "n_tool_calls", "tool_calls",
                                     "response_chars", "verdict_reached",
                                     "error", "usage", "schedule_calls",
                                     "silent_exit")} for r in results],
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    print("\n=== SUMMARY ===")
    print(json.dumps({k: v for k, v in summary.items() if k != "turns"}, indent=2))

    for name, count in summary["sentinels"].items():
        if count:
            print(f"\n  *** SENTINEL ALARM: {name}={count} — investigate before "
                  f"trusting this run (module docstring: SENTINELS) ***")

    _diff_against_baseline(summary, args.label)
    print(f"\ntranscripts → {out_dir}")
    return 0


def _diff_against_baseline(summary: dict, label: str) -> None:
    """Print mean-deltas vs CURRENT_BASELINE (skipped when this run IS the
    baseline, or the baseline capture is absent)."""
    if label == CURRENT_BASELINE:
        return
    base_path = REPO_ROOT / "docs" / "evaluations" / CURRENT_BASELINE / "summary.json"
    if not base_path.exists():
        print(f"\n(no baseline diff — {base_path} missing)")
        return
    base = json.loads(base_path.read_text())
    print(f"\n=== DIFF vs CURRENT_BASELINE ({CURRENT_BASELINE}) ===")
    for key in ("closed", "errors", "mean_wall_s", "mean_rounds",
                "mean_tool_calls", "mean_response_chars", "mean_est_cost_usd"):
        b, r = base.get(key), summary.get(key)
        if b is None or r is None:
            print(f"  {key}: {b} -> {r}  (n/a)")
            continue
        delta = round(r - b, 4)
        pct = f" ({delta / b * +100:+.0f}%)" if b else ""
        print(f"  {key}: {b} -> {r}  {delta:+}{pct}")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

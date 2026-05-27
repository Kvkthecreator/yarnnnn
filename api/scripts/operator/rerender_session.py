"""One-shot SESSION.md re-render utility.

Used to recover SESSION.md from a session folder where the suite ran to
completion but render_session_md crashed (e.g., the Python 3.9 datetime
parser bug that surfaced 2026-05-27 on session 2026-05-27-064722).

Reconstructs eval_results from:
  - suite YAML (expected_dimensions, substrate_inputs, eval_shape per eval)
  - cost-rollup.csv (cost dimension data — fully populated by the original run)
  - per-eval folder existence (binary: did the eval run capture or not)

Cannot reconstruct: per-eval started_at / finished_at / triggering_revision_ids
(those lived in runtime memory only; not persisted to disk). Cost rollup table
uses session-level window instead of per-eval windows; per-eval cost rows
show degraded data ("(unknown — reconstruction)") since per-eval timestamps
are lost.

This is a recovery tool, not a permanent fix. The underlying fix is making
run_eval_suite.py write per-eval metadata to disk before rendering SESSION.md.

Usage:
    .venv/bin/python -m api.scripts.operator.rerender_session \\
        --suite docs/evaluations/eval-suites/yarnnn-author-baseline.yaml \\
        --session-folder docs/evaluations/2026-05-27-064722-yarnnn-author-baseline-session
"""

from __future__ import annotations

import argparse
import asyncio
import csv
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


def reconstruct_eval_results(suite: dict, raw_folder: Path) -> list[dict]:
    """Build a degraded eval_results list from suite YAML + filesystem inspection.

    Per-eval metadata that was lost (no longer in PLAYBOOK.md after the
    re-snapshot overwrite):
      - started_at / finished_at
      - triggering_revision_ids
      - runner.evaluations (turn-by-turn log)

    What we can still infer:
      - eval slug, scenario, expected_dimensions, substrate_inputs, eval_shape (from suite YAML)
      - outcome: completed (folder exists with transcript) | failed (folder exists empty)
      - turns_executed: counted from per-eval scenario's turn count (suite YAML)
    """
    from services.operator_proxy.scenarios import Scenario

    eval_results: list[dict] = []
    for i, eval_def in enumerate(suite["evals"]):
        eval_slug = eval_def["eval"]
        eval_folder = raw_folder / f"eval-{i + 1}-{eval_slug}"

        scen_path = REPO_ROOT / "docs" / "evaluations" / eval_def["scenario"]
        scenario = Scenario.from_file(scen_path)

        transcript_path = eval_folder / "transcript.md"
        if transcript_path.is_file() and transcript_path.stat().st_size > 100:
            outcome = "completed"
            error = None
        elif eval_folder.is_dir():
            outcome = "failed"
            error = "ReadTimeout or other runtime error (folder exists but transcript missing/empty)"
        else:
            outcome = "missing"
            error = "eval folder does not exist"

        # NOTE: per-eval timestamps were lost (the runner crashed before
        # serializing them). Use the session window as a placeholder so
        # render_session_md can still parse them; the cost-table per-eval
        # rows will show inflated counts (every eval gets all 10 wakes
        # in its ±2-min window because all evals share the same fake
        # timestamps). Honest degradation — operator reads cost
        # session-level totals as the trusted number; per-eval is best-
        # effort recovery.
        eval_results.append({
            "eval": eval_slug,
            "scenario": scenario.slug,
            "folder": str(eval_folder.relative_to(raw_folder.parent)),
            "eval_folder_abs": str(eval_folder),
            "started_at": _SESSION_WINDOW_PLACEHOLDER_START,
            "finished_at": _SESSION_WINDOW_PLACEHOLDER_END,
            "duration_sec": 0,
            "outcome": outcome,
            "error": error,
            "turns_executed": len(scenario.turns),
            "expected_dimensions": eval_def["expected_dimensions"],
            "substrate_inputs": eval_def.get("substrate_inputs", {}),
            "eval_shape": eval_def.get("eval_shape", "behavioral"),
            "triggering_revision_ids": [],
            "evaluations": [],
        })
    return eval_results


# Module-level placeholders, set by rerender() before reconstruct_eval_results()
_SESSION_WINDOW_PLACEHOLDER_START: str = ""
_SESSION_WINDOW_PLACEHOLDER_END: str = ""


def load_cost_rollup_from_csv(csv_path: Path) -> dict:
    """Reconstruct the cost_rollup dict from the runner-emitted CSV."""
    if not csv_path.is_file():
        return {
            "session_window_start": "(unknown)",
            "session_window_end": "(unknown)",
            "wake_count": 0,
            "judgment_wake_count": 0,
            "mechanical_wake_count": 0,
            "total_cost_usd": 0.0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "per_slug": {},
            "raw_rows": [],
        }

    rows: list[dict] = []
    with csv_path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Coerce numeric fields
            for k in ("input_tokens", "output_tokens", "cache_read_tokens", "cache_create_tokens",
                     "tool_rounds", "duration_ms"):
                if row.get(k):
                    try:
                        row[k] = int(row[k])
                    except (ValueError, TypeError):
                        row[k] = None
            if row.get("cost_usd"):
                try:
                    row["cost_usd"] = float(row["cost_usd"])
                except (ValueError, TypeError):
                    row["cost_usd"] = 0.0
            rows.append(row)

    total_usd = sum((r.get("cost_usd") or 0) for r in rows)
    total_in = sum((r.get("input_tokens") or 0) for r in rows)
    total_out = sum((r.get("output_tokens") or 0) for r in rows)
    judgment_rows = [r for r in rows if r.get("mode") == "judgment"]
    mechanical_rows = [r for r in rows if r.get("mode") == "mechanical"]

    per_slug: dict[str, dict] = {}
    for r in rows:
        slug = r.get("slug") or "(unknown)"
        bucket = per_slug.setdefault(slug, {"wakes": 0, "cost_usd": 0.0, "input_tokens": 0, "output_tokens": 0})
        bucket["wakes"] += 1
        bucket["cost_usd"] += r.get("cost_usd") or 0
        bucket["input_tokens"] += r.get("input_tokens") or 0
        bucket["output_tokens"] += r.get("output_tokens") or 0

    return {
        "session_window_start": rows[0].get("created_at") if rows else "(unknown)",
        "session_window_end": rows[-1].get("created_at") if rows else "(unknown)",
        "wake_count": len(rows),
        "judgment_wake_count": len(judgment_rows),
        "mechanical_wake_count": len(mechanical_rows),
        "total_cost_usd": round(total_usd, 4),
        "total_input_tokens": total_in,
        "total_output_tokens": total_out,
        "per_slug": per_slug,
        "raw_rows": rows,
    }


async def rerender(suite_path: Path, session_folder: Path) -> int:
    from scripts.operator.run_eval_suite import (
        load_suite,
        render_session_md,
        _parse_iso8601_lenient,
    )

    suite = load_suite(suite_path)
    raw_folder = session_folder / "raw"
    if not raw_folder.is_dir():
        print(f"ERROR: raw/ folder not found at {raw_folder}", file=sys.stderr)
        return 2

    print(f"Suite: {suite['eval_suite']} ({len(suite['evals'])} evals)")
    print(f"Session folder: {session_folder}")

    # Use cost-rollup CSV window for session start/end (best available),
    # AND propagate to reconstruct_eval_results as placeholder per-eval
    # timestamps so render_session_md can still parse them.
    cost_rollup_preview = load_cost_rollup_from_csv(raw_folder / "cost-rollup.csv")
    global _SESSION_WINDOW_PLACEHOLDER_START, _SESSION_WINDOW_PLACEHOLDER_END
    if cost_rollup_preview["raw_rows"]:
        _SESSION_WINDOW_PLACEHOLDER_START = cost_rollup_preview["raw_rows"][0]["created_at"]
        _SESSION_WINDOW_PLACEHOLDER_END = cost_rollup_preview["raw_rows"][-1]["created_at"]
    else:
        now_iso = datetime.now(timezone.utc).isoformat()
        _SESSION_WINDOW_PLACEHOLDER_START = now_iso
        _SESSION_WINDOW_PLACEHOLDER_END = now_iso

    eval_results = reconstruct_eval_results(suite, raw_folder)
    print(f"Reconstructed eval_results: {len(eval_results)} evals")
    for r in eval_results:
        print(f"  {r['eval']:42s} outcome={r['outcome']:9s} shape={r['eval_shape']}")

    cost_rollup = cost_rollup_preview  # reused — already loaded for placeholder timestamps
    print(f"Cost rollup from CSV: {cost_rollup['wake_count']} wakes, ${cost_rollup['total_cost_usd']:.4f}")

    if cost_rollup["raw_rows"]:
        session_started_at = _parse_iso8601_lenient(cost_rollup["raw_rows"][0]["created_at"])
        session_finished_at = _parse_iso8601_lenient(cost_rollup["raw_rows"][-1]["created_at"])
    else:
        session_started_at = datetime.now(timezone.utc)
        session_finished_at = session_started_at

    # Persona resolution — extract from session_folder name (no DB query needed)
    from services.operator_proxy.client import OperatorProxy
    proxy = OperatorProxy.from_persona(suite["persona"], caller="rerender")
    user_id = proxy.config.user_id
    user_email = proxy.config.email or "(unknown)"

    # Degraded completion summary — runner output told us the gate timed out,
    # so we encode that honestly in the rollup.
    completion = {
        "elapsed_sec": 605,
        "substrate_event_settled": 3,
        "substrate_event_pending": 0,
        "substrate_event_expected": 7,
        "addressed_settled": 7,
        "addressed_expected": 7,
        "timed_out": True,
    }

    session_md = render_session_md(
        suite=suite,
        user_id=user_id,
        user_email=user_email,
        eval_results=eval_results,
        cost_rollup=cost_rollup,
        completion=completion,
        session_started_at=session_started_at,
        session_finished_at=session_finished_at,
        session_folder_path=session_folder,
    )
    out_path = session_folder / "SESSION.md"
    out_path.write_text(session_md)
    print(f"\nrendered: {out_path}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Re-render SESSION.md from existing session folder")
    ap.add_argument("--suite", required=True, type=Path)
    ap.add_argument("--session-folder", required=True, type=Path)
    args = ap.parse_args()
    return asyncio.run(rerender(args.suite, args.session_folder))


if __name__ == "__main__":
    raise SystemExit(main())

"""Eval-suite session runner — multi-eval, multi-dimension measurement.

Codified by docs/evaluations/EVAL-SUITE-DISCIPLINE.md (2026-05-27). One
session = one suite manifest → N evals run sequentially against the
same workspace → one rollup at SESSION.md scoring all four dimensions
(behavior, posture, substrate-usage, cost).

The runner orchestrates existing ScenarioRunner invocations; it does
NOT introduce a parallel scenario-execution path. Per-eval captures
land at {session-folder}/raw/eval-N-{slug}/ using the standard
8-artifact scenario capture shape.

Usage:
    .venv/bin/python -m api.scripts.operator.run_eval_suite \\
        --suite docs/evaluations/eval-suites/yarnnn-author-baseline.yaml \\
        [--caller eval-suite-runner]

After session lands, SESSION.md is a draft — edit per-eval Observed
columns + dimension aggregates after reading the captured artifacts +
running the human-read steps (Axis-B posture tag, trace-completeness
review). Substrate-receipts in raw/ enable verification.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

_THIS_DIR = Path(__file__).resolve().parent
_API_ROOT = _THIS_DIR.parents[1]
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

REPO_ROOT = _THIS_DIR.parents[2]

from dotenv import load_dotenv  # noqa: E402
load_dotenv(_API_ROOT / ".env.alpha-ops")
load_dotenv(REPO_ROOT / ".env")


SUITE_SCHEMA_VERSION = 1
DEFAULT_BUDGET = {
    "per_eval_usd": 1.0,
    "per_session_usd": 5.0,
    "trace_completeness_floor": 0.8,
    "m6_drift_ceiling": 1,
}


# ---------------------------------------------------------------------------
# Suite loading + validation
# ---------------------------------------------------------------------------


class SuiteError(Exception):
    """Raised on malformed suite manifest."""


def load_suite(path: Path) -> dict:
    raw = yaml.safe_load(path.read_text())
    if not isinstance(raw, dict):
        raise SuiteError(f"Suite manifest must be a YAML dict, got {type(raw).__name__}")
    version = int(raw.get("eval_suite_schema_version", SUITE_SCHEMA_VERSION))
    if version != SUITE_SCHEMA_VERSION:
        raise SuiteError(
            f"Unsupported eval_suite_schema_version {version}; runner only supports v{SUITE_SCHEMA_VERSION}"
        )
    for required in ("eval_suite", "persona", "evals"):
        if required not in raw:
            raise SuiteError(f"Suite manifest missing required field: {required!r}")
    if not isinstance(raw["evals"], list) or not raw["evals"]:
        raise SuiteError("Suite manifest 'evals' must be a non-empty list")

    # Defensive defaults
    raw.setdefault("description", "")
    raw.setdefault("budget", {})
    for k, v in DEFAULT_BUDGET.items():
        raw["budget"].setdefault(k, v)

    # Resolve scenario paths to absolute + verify each exists
    docs_evals_root = REPO_ROOT / "docs" / "evaluations"
    for i, eval_def in enumerate(raw["evals"]):
        for required in ("eval", "scenario", "expected_dimensions"):
            if required not in eval_def:
                raise SuiteError(f"Eval[{i}] missing required field: {required!r}")
        scen_rel = eval_def["scenario"]
        # Scenario paths are relative to docs/evaluations/
        scen_abs = docs_evals_root / scen_rel
        if not scen_abs.is_file():
            raise SuiteError(f"Eval[{i}] {eval_def['eval']!r} scenario not found: {scen_abs}")
        eval_def["_scenario_abs"] = scen_abs

    return raw


# ---------------------------------------------------------------------------
# Session folder + per-eval execution
# ---------------------------------------------------------------------------


def session_folder(suite_slug: str) -> Path:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")
    return REPO_ROOT / "docs" / "evaluations" / f"{now}-{suite_slug}-session"


async def run_one_eval(
    eval_def: dict,
    eval_index: int,
    raw_folder: Path,
    caller: str,
) -> dict:
    """Execute a single eval via the existing ScenarioRunner; return per-eval result dict."""
    from services.operator_proxy.scenarios import Scenario, ScenarioRunner

    eval_slug = eval_def["eval"]
    scen_path = eval_def["_scenario_abs"]
    eval_folder = raw_folder / f"eval-{eval_index + 1}-{eval_slug}"

    scenario = Scenario.from_file(scen_path)
    runner = ScenarioRunner(scenario, caller=caller)

    print(f"\n=== Eval {eval_index + 1}/{len(eval_def)} — {eval_slug} ===")
    print(f"    scenario: {scenario.slug}")
    print(f"    capture:  {eval_folder}")

    started_at = datetime.now(timezone.utc)
    try:
        scenario_result = await runner.run(eval_folder)
        outcome = "completed"
        error = None
    except Exception as exc:
        scenario_result = None
        outcome = "failed"
        error = f"{type(exc).__name__}: {exc}"
        print(f"    FAIL: {error}")
    finished_at = datetime.now(timezone.utc)

    return {
        "eval": eval_slug,
        "scenario": scenario.slug,
        "folder": str(eval_folder.relative_to(raw_folder.parent)),
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "duration_sec": int((finished_at - started_at).total_seconds()),
        "outcome": outcome,
        "error": error,
        "turns_executed": (scenario_result or {}).get("turns_executed", 0),
        "expected_dimensions": eval_def["expected_dimensions"],
    }


# ---------------------------------------------------------------------------
# Cost rollup (post-session SQL)
# ---------------------------------------------------------------------------


async def compose_cost_rollup(
    user_id: str,
    session_started_at: datetime,
    session_finished_at: datetime,
) -> dict:
    """Pull execution_events for the session window; return aggregate + per-slug breakdown."""
    from services.supabase import get_service_client

    client = get_service_client()
    loop = asyncio.get_running_loop()

    def query():
        # Pad the window by ±2 min to catch wakes that fire just after a turn writes
        start = (session_started_at).isoformat()
        end = (session_finished_at).isoformat()
        return (
            client.table("execution_events")
            .select("id, slug, mode, wake_source, status, tool_rounds, input_tokens, output_tokens, cache_read_tokens, cache_create_tokens, cost_usd, duration_ms, created_at")
            .eq("user_id", user_id)
            .gte("created_at", start)
            .lte("created_at", end)
            .order("created_at")
            .execute()
        )

    response = await loop.run_in_executor(None, query)
    rows = response.data or []

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
        "session_window_start": session_started_at.isoformat(),
        "session_window_end": session_finished_at.isoformat(),
        "wake_count": len(rows),
        "judgment_wake_count": len(judgment_rows),
        "mechanical_wake_count": len(mechanical_rows),
        "total_cost_usd": round(total_usd, 4),
        "total_input_tokens": total_in,
        "total_output_tokens": total_out,
        "per_slug": per_slug,
        "raw_rows": rows,
    }


# ---------------------------------------------------------------------------
# SESSION.md rollup composition
# ---------------------------------------------------------------------------


def _verdict_pass_marker() -> str:
    return "_(human-read — verify after reading raw/)_"


def render_session_md(
    *,
    suite: dict,
    user_id: str,
    user_email: str,
    eval_results: list[dict],
    cost_rollup: dict,
    session_started_at: datetime,
    session_finished_at: datetime,
    session_folder_path: Path,
) -> str:
    """Compose the SESSION.md rollup markdown."""
    duration_min = int((session_finished_at - session_started_at).total_seconds() / 60)
    session_total_usd = cost_rollup["total_cost_usd"]
    per_session_budget = suite["budget"]["per_session_usd"]
    per_eval_budget = suite["budget"]["per_eval_usd"]

    cost_within_budget = session_total_usd <= per_session_budget

    lines: list[str] = []
    lines.append(f"# Eval-suite session — {suite['eval_suite']}\n")
    lines.append(f"**Captured**: {session_started_at.isoformat()}")
    lines.append(f"**Persona**: {suite['persona']}")
    lines.append(f"**Workspace**: `{user_id[:8]}` ({user_email})")
    lines.append(f"**Suite**: `docs/evaluations/eval-suites/{suite['eval_suite']}.yaml`")
    lines.append(f"**Evals run**: {len(eval_results)} of {len(suite['evals'])}")
    lines.append(f"**Duration**: {duration_min} min wall-clock")
    lines.append(f"**Session cost**: ${session_total_usd:.4f} (budget: ${per_session_budget:.2f})")
    lines.append(f"**Cost within budget**: {'YES' if cost_within_budget else 'NO — exceeds budget'}\n")
    lines.append("---\n")

    # §1 Headline
    lines.append("## §1 Headline\n")
    lines.append(
        "_To be filled in after reading raw/ artifacts. One paragraph: "
        "did the system pass on all four dimensions? Where did it fail?_\n"
    )
    lines.append("<!-- TODO operator: write the headline paragraph -->\n")
    lines.append("---\n")

    # §2 Per-dimension scores
    lines.append("## §2 Per-dimension scores\n")

    # Behavior
    lines.append("### Behavior\n")
    lines.append("| Eval | Expected verdict | Expected substrate side-effect | Observed | Pass? | Notes |")
    lines.append("|---|---|---|---|---|---|")
    for r in eval_results:
        ed = r["expected_dimensions"].get("behavior", {})
        lines.append(
            f"| `{r['eval']}` | {ed.get('verdict', '?')} | {ed.get('substrate_side_effect', '?')} "
            f"| <!-- TODO --> | <!-- TODO --> | {_verdict_pass_marker()} |"
        )
    lines.append("\n**Behavior aggregate**: _<!-- TODO: X/N evals pass -->_\n")

    # Posture
    lines.append("### Posture\n")
    lines.append("| Eval | Expected cell | Observed cell | Pass? | Notes |")
    lines.append("|---|---|---|---|---|")
    for r in eval_results:
        ed = r["expected_dimensions"].get("posture", {})
        lines.append(
            f"| `{r['eval']}` | {ed.get('cell', '?')} | <!-- TODO Axis-A SQL + Axis-B human-read --> "
            f"| <!-- TODO --> | {_verdict_pass_marker()} |"
        )
    lines.append(f"\n**Posture aggregate**: _<!-- TODO: X/N evals in expected cell. M6-DRIFT count: Y (ceiling: {suite['budget']['m6_drift_ceiling']}). -->_\n")

    # Substrate usage
    lines.append("### Substrate usage\n")
    lines.append("| Eval | Trace-completeness (0.0-1.0) | Pass? | Notes |")
    lines.append("|---|---|---|---|")
    for r in eval_results:
        ed = r["expected_dimensions"].get("substrate_usage", {})
        floor = ed.get("trace_completeness_min", suite["budget"]["trace_completeness_floor"])
        lines.append(
            f"| `{r['eval']}` | <!-- TODO human-read --> | <!-- TODO vs {floor} --> "
            f"| {_verdict_pass_marker()} |"
        )
    lines.append(f"\n**Substrate aggregate**: _<!-- TODO: avg trace-completeness, all evals ≥ floor ({suite['budget']['trace_completeness_floor']}) -->_\n")

    # Cost (this dimension is fully automatable)
    lines.append("### Cost (automated from `execution_events`)\n")
    lines.append("| Eval | Wakes in window | Cost USD | Within per-eval budget? |")
    lines.append("|---|---|---|---|")
    # Map eval cost windows to per-eval rows by matching slug → wakes within eval's started_at/finished_at
    raw_rows = cost_rollup["raw_rows"]
    for r in eval_results:
        eval_start = datetime.fromisoformat(r["started_at"])
        eval_end = datetime.fromisoformat(r["finished_at"])
        # Add a ±2-min pad to catch reactive wakes that fire just after a turn write
        from datetime import timedelta
        pad = timedelta(minutes=2)
        eval_rows = [
            row for row in raw_rows
            if eval_start - pad <= datetime.fromisoformat(row["created_at"].replace("Z", "+00:00")) <= eval_end + pad
        ]
        eval_cost = sum((row.get("cost_usd") or 0) for row in eval_rows)
        within = "YES" if eval_cost <= per_eval_budget else "NO"
        lines.append(
            f"| `{r['eval']}` | {len(eval_rows)} | ${eval_cost:.4f} | {within} (budget ${per_eval_budget:.2f}) |"
        )
    lines.append("")
    lines.append(f"**Session-level cost**: ${session_total_usd:.4f} total across {cost_rollup['wake_count']} wakes "
                 f"({cost_rollup['judgment_wake_count']} judgment, {cost_rollup['mechanical_wake_count']} mechanical).")
    lines.append(f"**Tokens**: {cost_rollup['total_input_tokens']:,} in / {cost_rollup['total_output_tokens']:,} out.\n")

    if cost_rollup["per_slug"]:
        lines.append("**Per-slug cost breakdown**:")
        lines.append("| Slug | Wakes | Cost USD | Tokens (in/out) |")
        lines.append("|---|---|---|---|")
        for slug, b in sorted(cost_rollup["per_slug"].items(), key=lambda kv: kv[1]["cost_usd"], reverse=True):
            lines.append(
                f"| `{slug}` | {b['wakes']} | ${b['cost_usd']:.4f} "
                f"| {b['input_tokens']:,}/{b['output_tokens']:,} |"
            )
        lines.append("")

    lines.append("---\n")

    # §3 Cross-dimension observations
    lines.append("## §3 Cross-dimension observations\n")
    lines.append("_What the four dimensions reveal together that no single dimension reveals alone._\n")
    lines.append("<!-- TODO operator: cross-dimension synthesis after dimension tables are filled in -->\n")
    lines.append("---\n")

    # §4 System-canon recommendations
    lines.append("## §4 System-canon recommendations\n")
    lines.append("_What this session's findings recommend for Hat-A work. Each recommendation gates on a measurement criterion in this session._\n")
    lines.append("<!-- TODO operator: recommendations -->\n")
    lines.append("---\n")

    # §5 Substrate-receipts
    lines.append("## §5 Substrate-receipts\n")
    lines.append("**Per-eval capture folders** (substrate-diffs, transcripts, decisions, proposals, token usage):\n")
    for r in eval_results:
        outcome_label = "OK" if r["outcome"] == "completed" else f"FAILED ({r['error']})"
        lines.append(f"- `raw/{Path(r['folder']).name}/` — {r['turns_executed']} turns, "
                     f"{r['duration_sec']}s, {outcome_label}")
    lines.append("")
    lines.append("**Cost rollup CSV**: `raw/cost-rollup.csv`")
    lines.append("")
    lines.append("**Reproducible SQL** for re-pulling the session's execution_events:")
    lines.append("```sql")
    lines.append(
        f"SELECT slug, mode, status, tool_rounds, input_tokens, output_tokens, cost_usd, created_at\n"
        f"FROM execution_events\n"
        f"WHERE user_id = '{user_id}'\n"
        f"  AND created_at >= '{session_started_at.isoformat()}'\n"
        f"  AND created_at <= '{session_finished_at.isoformat()}'\n"
        f"ORDER BY created_at;"
    )
    lines.append("```")
    lines.append("")
    lines.append("---\n")
    lines.append("## Status\n")
    lines.append("**DRAFT** — runner produced the skeleton + automated cost dimension. Operator fills in behavior / posture / substrate-usage human-read columns + §1 headline + §3 cross-dimension synthesis + §4 recommendations after reading raw/ artifacts.\n")
    lines.append(f"## Last updated\n\n{session_started_at.isoformat()} — runner emit.\n")
    return "\n".join(lines)


def emit_cost_rollup_csv(cost_rollup: dict, csv_path: Path) -> None:
    import csv
    raw = cost_rollup["raw_rows"]
    if not raw:
        csv_path.write_text("(no execution_events rows in session window)\n")
        return
    fieldnames = list(raw[0].keys())
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in raw:
            writer.writerow(row)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def run_suite(suite_path: Path, caller: str) -> int:
    from services.operator_proxy.client import OperatorProxy

    suite = load_suite(suite_path)
    print(f"suite: {suite['eval_suite']}")
    print(f"persona: {suite['persona']}")
    print(f"evals: {len(suite['evals'])}")
    print(f"budget: per-eval ${suite['budget']['per_eval_usd']}, per-session ${suite['budget']['per_session_usd']}")

    # Resolve persona → user_id via OperatorProxy
    proxy = OperatorProxy.from_persona(suite["persona"], caller=caller)
    user_id = proxy.config.user_id
    user_email = proxy.config.email or "(unknown)"
    print(f"workspace: {user_id[:8]} ({user_email})")

    folder = session_folder(suite["eval_suite"])
    raw_folder = folder / "raw"
    raw_folder.mkdir(parents=True, exist_ok=True)
    print(f"session folder: {folder}\n")

    session_started_at = datetime.now(timezone.utc)
    eval_results: list[dict] = []
    for i, eval_def in enumerate(suite["evals"]):
        result = await run_one_eval(eval_def, i, raw_folder, caller)
        eval_results.append(result)

    session_finished_at = datetime.now(timezone.utc)

    print("\n=== Composing cost rollup ===")
    cost_rollup = await compose_cost_rollup(user_id, session_started_at, session_finished_at)
    print(f"    wakes: {cost_rollup['wake_count']} (judgment: {cost_rollup['judgment_wake_count']})")
    print(f"    total cost: ${cost_rollup['total_cost_usd']:.4f}")

    emit_cost_rollup_csv(cost_rollup, raw_folder / "cost-rollup.csv")

    print("\n=== Rendering SESSION.md ===")
    session_md = render_session_md(
        suite=suite,
        user_id=user_id,
        user_email=user_email,
        eval_results=eval_results,
        cost_rollup=cost_rollup,
        session_started_at=session_started_at,
        session_finished_at=session_finished_at,
        session_folder_path=folder,
    )
    (folder / "SESSION.md").write_text(session_md)
    print(f"\nsession complete: {folder / 'SESSION.md'}")
    print("(edit SESSION.md to fill in behavior / posture / substrate-usage human-read columns)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Eval-suite session runner (EVAL-SUITE-DISCIPLINE.md)")
    ap.add_argument("--suite", required=True, type=Path, help="Path to eval-suite YAML manifest")
    ap.add_argument("--caller", default="eval-suite-runner", help="Caller identity tag")
    args = ap.parse_args()

    if not args.suite.is_file():
        print(f"suite file not found: {args.suite}", file=sys.stderr)
        return 2
    return asyncio.run(run_suite(args.suite, args.caller))


if __name__ == "__main__":
    raise SystemExit(main())

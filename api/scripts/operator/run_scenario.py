"""ADR-294 — Scripted scenario player.

Reads a YAML scenario file under docs/evaluations/scenarios/, executes
it via OperatorProxy + ScenarioRunner, and writes a captured evaluation
folder under docs/evaluations/.

Renamed from "observations" to "evaluations" on 2026-05-26 — see
docs/evaluations/README.md §"Why 'evaluations' and not 'observations'"
for the criterion-declaration discipline that motivated the rename.

Usage:
    .venv/bin/python -m api.scripts.operator.run_scenario \\
        --scenario docs/evaluations/scenarios/warm-start-auto-execute.yaml \\
        [--caller scenario-runner]
"""

from __future__ import annotations

import argparse
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
# Load alpha-ops first (persona JWT mint creds), then root .env (runtime
# secrets like INTEGRATION_ENCRYPTION_KEY needed by platform-tool decryption
# during local fire-dispatch in scenario setup steps).
load_dotenv(_API_ROOT / ".env.alpha-ops")
load_dotenv(REPO_ROOT / ".env")


def _evaluation_folder(scenario_slug: str) -> Path:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")
    return REPO_ROOT / "docs" / "evaluations" / f"{now}-{scenario_slug}"


async def run_scenario(scenario_path: Path, caller: str) -> int:
    from services.operator_proxy.scenarios import Scenario, ScenarioRunner

    scenario = Scenario.from_file(scenario_path)
    eval_folder = _evaluation_folder(scenario.slug)

    print(f"scenario: {scenario.slug}")
    print(f"persona:  {scenario.persona}")
    print(f"caller:   {caller}")
    print(f"output:   {eval_folder}")
    print()

    runner = ScenarioRunner(scenario, caller=caller)
    result = await runner.run(eval_folder)

    print(f"\nturns_executed: {result['turns_executed']}")
    print(f"evaluation folder: {result['evaluation_folder']}")
    print("(edit findings.md to record your interpretation)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Scenario player (ADR-294)")
    ap.add_argument("--scenario", required=True, type=Path, help="Path to scenario YAML")
    ap.add_argument("--caller", default="scenario-runner", help="Caller identity tag")
    args = ap.parse_args()

    if not args.scenario.is_file():
        print(f"scenario file not found: {args.scenario}", file=sys.stderr)
        return 2

    return asyncio.run(run_scenario(args.scenario, args.caller))


if __name__ == "__main__":
    raise SystemExit(main())

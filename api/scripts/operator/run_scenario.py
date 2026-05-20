"""ADR-294 — Scripted scenario player.

Reads a YAML scenario file under docs/observations/scenarios/, executes
it via OperatorProxy + ScenarioRunner, and writes a captured observation
folder under docs/observations/.

Usage:
    .venv/bin/python -m api.scripts.operator.run_scenario \\
        --scenario docs/observations/scenarios/warm-start-auto-execute.yaml \\
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

from dotenv import load_dotenv  # noqa: E402
load_dotenv(_API_ROOT / ".env.alpha-ops")

REPO_ROOT = _THIS_DIR.parents[2]


def _observation_folder(scenario_slug: str) -> Path:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")
    return REPO_ROOT / "docs" / "observations" / f"{now}-{scenario_slug}"


async def run_scenario(scenario_path: Path, caller: str) -> int:
    from services.operator_proxy.scenarios import Scenario, ScenarioRunner

    scenario = Scenario.from_file(scenario_path)
    obs_folder = _observation_folder(scenario.slug)

    print(f"scenario: {scenario.slug}")
    print(f"persona:  {scenario.persona}")
    print(f"caller:   {caller}")
    print(f"output:   {obs_folder}")
    print()

    runner = ScenarioRunner(scenario, caller=caller)
    result = await runner.run(obs_folder)

    print(f"\nturns_executed: {result['turns_executed']}")
    print(f"observation folder: {result['observation_folder']}")
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

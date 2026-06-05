"""One-shot harness: flip a persona's _autonomy.yaml to a target delegation mode.

Used for Test C / Test B / Test A validation of ADR-293 substrate-write
gating. Writes via authored_substrate.write_revision so the change is
fully attributed per ADR-209.

Usage:
    .venv/bin/python -m api.scripts.alpha_ops._test_flip_autonomy \\
        --persona alpha-trader-2 --mode bounded
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
_API_ROOT = _THIS_DIR.parents[1]
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

from dotenv import load_dotenv
load_dotenv(_API_ROOT / ".env.alpha-ops")

sys.path.insert(0, str(_THIS_DIR))
from _shared import load_registry  # noqa: E402


AUTONOMY_TEMPLATE = """---
tier: canon
note: "Test flip — delegation={mode} for ADR-293 substrate-write gate validation"
---
# _autonomy.yaml — delegation ceiling (ADR-254)
default:
  delegation: {mode}
  ceiling_cents: 5000000
  never_auto:
    - close_position_market
    - cancel_other_orders
"""


def main_sync(persona_slug: str, mode: str) -> int:
    from services.supabase import get_service_client
    from services.authored_substrate import write_revision

    reg = load_registry()
    persona = reg.require(persona_slug)
    content = AUTONOMY_TEMPLATE.format(mode=mode)

    client = get_service_client()
    result = write_revision(
        client,
        user_id=persona.user_id,
        path="/workspace/governance/_autonomy.yaml",
        content=content,
        authored_by="operator:test-validation",
        message=f"Test flip — delegation={mode} for ADR-293 validation",
    )
    print(f"persona={persona_slug} mode={mode} revision={result}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--persona", required=True)
    ap.add_argument("--mode", required=True, choices=["manual", "bounded", "autonomous"])
    args = ap.parse_args()
    return main_sync(args.persona, args.mode)


if __name__ == "__main__":
    raise SystemExit(main())

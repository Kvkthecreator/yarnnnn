"""ADR-360 Stage-3 validation — the ask-builder through the PRODUCTION path.

The step-3 probe (probe_spine_cron_imperative_local.py) hand-injected an imperative
prompt into invoke_freddie. This probe proves the PRODUCTION wiring: a recurrence
that ships a SITUATION-FRAMING prompt + the `produces_owed_output` flag, fired
through `services.wake._invoke_recurrence_wake` (the exact path the deployed cron
drains), where the ADR-360 ask-builder must CONVERT the stored framing into an
imperative at fire-time. The recurrence's stored prompt is framing; if the agent
composes, the ask-builder did its job through the real code path — not a probe.

  SETUP: netflix-script-author, empty corpus, autonomous, declared weekly piece.
  RECURRENCE: stored prompt = FRAMING ("assess the operation against its mandate"),
              options = {produces_owed_output: True}.
  FIRE: _invoke_recurrence_wake(client, user_id, recurrence, trigger=..., wake_source="cron_tick").

PASS: content.md composed in-cycle (the ask-builder overrode the framing with an
      imperative through the production path).
FAIL: deferral (the framing reached the agent — wiring incomplete).

Usage: cd /Users/macbook/yarnnn && .venv/bin/python -m api.scripts.operator.probe_adr360_production_path_local
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
_API_ROOT = _THIS_DIR.parents[1]
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))
REPO_ROOT = _THIS_DIR.parents[2]

from dotenv import load_dotenv  # noqa: E402
load_dotenv(_API_ROOT / ".env.alpha-ops")
load_dotenv(REPO_ROOT / ".env")

USER_ID = "23cc7951-b6c7-471c-ac38-657d931db6f7"

# The recurrence ships FRAMING — the ask-builder must override it. This is the
# control shape every FAIL probe used; if it composes here, the production wiring
# converted it.
FRAMING_PROMPT = (
    "Assess the operation against its mandate — both the coherence of what exists "
    "and whether the operation is producing what it owes. The rules of judgment are "
    "in principles.md; the frame owns how you close."
)


async def main() -> int:
    from services.supabase import get_service_client
    from services.wake import _invoke_recurrence_wake
    from services.recurrence import Recurrence

    client = get_service_client()

    before = (
        client.table("workspace_files").select("path", count="exact")
        .eq("user_id", USER_ID).like("path", "/workspace/operation/%/content.md").execute()
    )
    n_before = before.count if before.count is not None else len(before.data or [])
    print(f"[adr360-prod] content.md BEFORE: {n_before}")

    # Build a producer recurrence that ships FRAMING. The ask-builder reads the
    # produces_owed_output flag from options and overrides the prompt.
    recurrence = Recurrence(
        slug="weekly-piece",
        schedule="0 10 * * 1",
        prompt=FRAMING_PROMPT,           # FRAMING — the ask-builder must override
        mode="judgment",
        required_capabilities=[],
        options={"produces_owed_output": True},   # the ADR-360 opt-in flag
    )
    print("[adr360-prod] recurrence ships FRAMING prompt + produces_owed_output=True")
    print("[adr360-prod] firing through _invoke_recurrence_wake (production path)...")

    out = await _invoke_recurrence_wake(
        client, USER_ID,
        recurrence=recurrence,
        wake_source="cron_tick",
        context="",
    )

    verdict = (out or {}).get("verdict")
    rounds = (out or {}).get("tool_rounds")
    actions = (out or {}).get("actions_taken") or []
    print(f"[adr360-prod] verdict={verdict} rounds={rounds} actions={len(actions)}")
    for a in actions:
        if a.get("tool") in ("WriteFile", "EditFile", "MoveFile"):
            print(f"[adr360-prod]   {a.get('tool')} success={a.get('success')} "
                  f"path={(a.get('input') or {}).get('path') or ''}")

    after = (
        client.table("workspace_files").select("path", count="exact")
        .eq("user_id", USER_ID).like("path", "/workspace/operation/%/content.md").execute()
    )
    n_after = after.count if after.count is not None else len(after.data or [])
    print(f"[adr360-prod] content.md AFTER: {n_after}")

    if n_after > n_before:
        print(f"[adr360-prod] ===== PASS — composed via production path ({n_before}→{n_after}); "
              f"ask-builder overrode the framing prompt =====")
    else:
        print(f"[adr360-prod] ===== FAIL — no compose (verdict={verdict}); "
              f"framing reached the agent, wiring incomplete =====")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

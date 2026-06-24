"""Governance-caching measurement probe (the-envelope-collapse probe FINDING 2026-06-24).

Fires ONE production reviewer wake and reports the cache-usage totals the loop
already accumulates (total_cache_create / total_cache_read). The win to verify:
round 1 WRITES the governance cache (cache_creation > 0), rounds 2..N READ it
(cache_read > 0) — proving the ~16k-token governance prefix is no longer
re-billed at full rate every round.

PASS: total_cache_create > 0 AND total_cache_read > 0 (governance cached + reused).
WATCH: cache_read == 0 across a multi-round loop → a silent invalidator is busting
       the governance prefix (the operating-context timestamp leaked into the
       prefix, non-deterministic governance bytes, etc.).

Production path only (no env arm). Funded fresh-state yarnnn-author.

Usage: cd /Users/macbook/yarnnn && .venv/bin/python -m api.scripts.operator.probe_governance_cache_local
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

USER_ID = "0b7a852d-4a67-447d-91d9-2ba1145a60d7"

FRAMING_PROMPT = (
    "Assess the operation against its mandate. The rules of judgment are in "
    "principles.md; the frame owns how you close."
)


async def main() -> int:
    from services.supabase import get_service_client
    from services.wake import _invoke_recurrence_wake
    from services.recurrence import Recurrence
    import time as _t

    client = get_service_client()

    slug = f"cache-probe-{int(_t.time())}"
    recurrence = Recurrence(
        slug=slug, schedule="0 10 * * 1", prompt=FRAMING_PROMPT,
        mode="judgment", required_capabilities=[],
        options={"produces_owed_output": True},
    )
    print(f"[cache-probe] firing {slug} through _invoke_recurrence_wake (production path)...")

    out = await _invoke_recurrence_wake(
        client, USER_ID, recurrence=recurrence, wake_source="cron_tick", context="",
    ) or {}

    ci = out.get("cost_input_tokens") or out.get("input_tokens")
    co = out.get("cost_output_tokens") or out.get("output_tokens")
    cr = out.get("cache_read_tokens")
    cc = out.get("cache_creation_tokens") or out.get("cache_create_tokens")
    rounds = out.get("tool_rounds")
    verdict = out.get("verdict")

    print(f"[cache-probe] verdict={verdict} rounds={rounds}")
    print(f"[cache-probe] input_tokens(uncached)={ci}  output_tokens={co}")
    print(f"[cache-probe] cache_creation_tokens={cc}  cache_read_tokens={cr}")

    # The output dict shape may differ from the loop's internal names; if the
    # totals aren't surfaced, fall back to the most recent execution_event.
    if cr is None and cc is None:
        print("[cache-probe] cache totals not in output dict — reading recent execution_event...")
        ev = (
            client.table("execution_events")
            .select("input_tokens, output_tokens, cache_read_tokens, cache_create_tokens, created_at")
            .eq("user_id", USER_ID)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if ev.data:
            row = ev.data[0]
            cc = row.get("cache_create_tokens")
            cr = row.get("cache_read_tokens")
            print(f"[cache-probe] (from execution_events) cache_creation={cc} cache_read={cr} "
                  f"input={row.get('input_tokens')} output={row.get('output_tokens')}")

    cc_n = int(cc or 0)
    cr_n = int(cr or 0)
    print()
    if cc_n > 0 and cr_n > 0:
        print(f"[cache-probe] PASS — governance cached (create={cc_n}) and reused (read={cr_n}).")
    elif cc_n > 0 and cr_n == 0:
        print(f"[cache-probe] PARTIAL — cache WRITTEN (create={cc_n}) but no read. "
              f"Single-round loop, or read fires on the NEXT wake within TTL. "
              f"Re-fire within 5 min to confirm read.")
    else:
        print(f"[cache-probe] WATCH — no cache activity (create={cc_n} read={cr_n}). "
              f"Check for a prefix invalidator or that the governance block "
              f"exceeds the 4096-token minimum.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

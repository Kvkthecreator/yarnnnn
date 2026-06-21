"""Hat-B repro — re-fire kvkthecreator's "put in a test trade" addressed wake.

Goal: capture the FULL SSE event stream (incl. every reviewer_progress tool
event = the tool_history the session_messages row truncates) to see WHY the
occupant chose Clarify instead of acting, against the live deployed system on
kvk's real substrate.

Not a registered alpha-ops persona — we build ProxyConfig directly from
kvk's user_id + email (persona_slug is cosmetic per ProxyConfig docstring).

Usage:
    .venv/bin/python -m api.scripts.operator.repro_kvk_test_trade \
        [--message "Can you put in a trade order. I want one even as a test"]
"""

from __future__ import annotations

import argparse
import asyncio
import json
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

import httpx  # noqa: E402
from scripts.alpha_ops._shared import mint_jwt, load_registry, Persona  # type: ignore  # noqa: E402

KVK_USER_ID = "2abf3f96-118b-4987-9d95-40f2d9be9a18"
KVK_EMAIL = "kvkthecreator@gmail.com"
DEFAULT_MSG = "Can you put in a trade order. I want one even as a test"
API_BASE = "https://yarnnn-api.onrender.com"


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--message", default=DEFAULT_MSG)
    ap.add_argument("--timeout", type=float, default=300.0)
    args = ap.parse_args()

    registry = load_registry()
    persona = Persona(
        slug="kvk-repro", label="(repro synthetic)", email=KVK_EMAIL,
        user_id=KVK_USER_ID, workspace_id=KVK_USER_ID, program="alpha-trader",
        platform={"kind": "none", "provider": "none"},
        context_domains=[], credentials_env={}, expected={},
    )
    print(f"minting JWT for {KVK_EMAIL} ...", flush=True)
    jwt = await asyncio.get_running_loop().run_in_executor(
        None, lambda: mint_jwt(persona, registry=registry)
    )
    print("minted. firing addressed wake against LIVE api ...\n", flush=True)

    events: list[dict] = []
    async with httpx.AsyncClient(timeout=args.timeout, base_url=API_BASE,
                                 headers={"Authorization": f"Bearer {jwt}",
                                          "Content-Type": "application/json"}) as client:
        body = {"content": args.message, "include_context": True}
        async with client.stream("POST", "/api/feed", json=body) as resp:
            if resp.status_code >= 300:
                raw = await resp.aread()
                print(f"HTTP {resp.status_code}: {raw.decode('utf-8', 'replace')}", file=sys.stderr)
                return 1
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                raw = line[len("data:"):].strip()
                if not raw:
                    continue
                try:
                    evt = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                events.append(evt)
                # Live trace: print every event compactly as it arrives.
                phase = evt.get("phase")
                if phase:
                    tool = evt.get("tool") or evt.get("tool_name") or ""
                    print(f"  [progress] phase={phase} tool={tool} {json.dumps({k: v for k, v in evt.items() if k not in ('phase','tool','tool_name')})[:300]}", flush=True)
                elif evt.get("reviewer_response"):
                    print(f"  [RESPONSE] {evt['reviewer_response'][:500]}", flush=True)
                elif evt.get("reviewer_verdict"):
                    print(f"  [VERDICT] {json.dumps(evt['reviewer_verdict'])[:400]}", flush=True)
                else:
                    print(f"  [event] {json.dumps(evt)[:300]}", flush=True)

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")
    out = REPO_ROOT / "docs" / "evaluations" / f"{stamp}-kvk-test-trade-repro.events.json"
    out.write_text(json.dumps(events, indent=2))
    print(f"\n{len(events)} events captured → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

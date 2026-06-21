"""ADR-352 live distribution probe — fire the test-trade ask N times and count
ask-vs-act outcomes, to confirm the gate has removed the run-to-run variance.

Each run: fresh addressed wake on kvk's live workspace. We record whether the
occupant called Clarify (and whether the gate DENY'd it) vs acted (WriteFile/
EditFile/Propose). Slight per-run message variation defeats identical-session
short-circuits without changing the semantics ("test trade, no signal firing").

Usage: .venv/bin/python -m api.scripts.operator.batch_kvk_ask_gate --runs 5
"""
from __future__ import annotations

import argparse
import asyncio
import json
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

import httpx  # noqa: E402
from scripts.alpha_ops._shared import mint_jwt, load_registry, Persona  # type: ignore  # noqa: E402

KVK_USER_ID = "2abf3f96-118b-4987-9d95-40f2d9be9a18"
KVK_EMAIL = "kvkthecreator@gmail.com"
API_BASE = "https://yarnnn-api.onrender.com"
# Semantically identical asks (test trade, knowing no signal is firing), phrased
# distinctly so each is a genuine fresh turn.
MESSAGES = [
    "Can you put in a trade order. I want one even as a test",
    "Place a test trade for me — I just want to see one go through",
    "I'd like to get a test order in. Can you do that?",
    "Put a trade on as a test please",
    "Let's get a test trade executed",
    "Can you submit a test order so I can see the loop?",
    "I want a trade placed even just as a test run",
    "Go ahead and put in a test trade order",
]


async def _fire(jwt: str, message: str, timeout: float) -> dict:
    tools: list[str] = []
    clarify_seen = False
    ask_denied = False
    acted = False
    text = ""
    async with httpx.AsyncClient(timeout=timeout, base_url=API_BASE,
                                 headers={"Authorization": f"Bearer {jwt}",
                                          "Content-Type": "application/json"}) as client:
        body = {"content": message, "include_context": True}
        async with client.stream("POST", "/api/feed", json=body) as resp:
            if resp.status_code >= 300:
                raw = await resp.aread()
                return {"error": f"HTTP {resp.status_code}: {raw.decode('utf-8','replace')[:200]}"}
            async for line in resp.aiter_lines():
                if not line.startswith("data:"):
                    continue
                raw = line[len("data:"):].strip()
                if not raw:
                    continue
                try:
                    evt = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                t = evt.get("tool")
                if t and evt.get("phase") == "tool_end":
                    tools.append(t)
                    if t == "Clarify":
                        clarify_seen = True
                    if t in ("WriteFile", "EditFile", "ProposeAction", "Schedule"):
                        acted = True
                blob = json.dumps(evt)
                if "ask_denied" in blob:
                    ask_denied = True
                if evt.get("reviewer_response"):
                    text = evt["reviewer_response"]
    return {
        "tools": tools, "clarify_seen": clarify_seen, "ask_denied": ask_denied,
        "acted": acted, "text_tail": text[-160:],
    }


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--timeout", type=float, default=300.0)
    args = ap.parse_args()

    registry = load_registry()
    persona = Persona(
        slug="kvk-batch", label="(batch synthetic)", email=KVK_EMAIL,
        user_id=KVK_USER_ID, workspace_id=KVK_USER_ID, program="alpha-trader",
        platform={"kind": "none", "provider": "none"},
        context_domains=[], credentials_env={}, expected={},
    )
    jwt = await asyncio.get_running_loop().run_in_executor(
        None, lambda: mint_jwt(persona, registry=registry)
    )

    acted_n = clarify_n = denied_recovered_n = err_n = 0
    for i in range(args.runs):
        msg = MESSAGES[i % len(MESSAGES)]
        print(f"\n--- run {i+1}/{args.runs}: {msg!r}", flush=True)
        try:
            r = await _fire(jwt, msg, args.timeout)
        except Exception as exc:
            print(f"  EXC {exc}"); err_n += 1; continue
        if r.get("error"):
            print(f"  ERR {r['error']}"); err_n += 1; continue
        # A Clarify that the gate denied, after which the occupant acted, is a
        # DENY-then-recover (the gate fired live). A Clarify with no act and no
        # deny would be the OLD failing behavior (should not occur autonomous).
        verdict = ("ACTED" if r["acted"] and not r["clarify_seen"]
                   else "DENY→RECOVER" if r["ask_denied"] and r["acted"]
                   else "CLARIFY-ONLY(!!)" if r["clarify_seen"] and not r["acted"]
                   else "OTHER")
        if verdict == "ACTED": acted_n += 1
        elif verdict == "DENY→RECOVER": denied_recovered_n += 1; acted_n += 1
        elif verdict == "CLARIFY-ONLY(!!)": clarify_n += 1
        print(f"  tools={r['tools']}")
        print(f"  clarify={r['clarify_seen']} ask_denied={r['ask_denied']} acted={r['acted']} → {verdict}")
        print(f"  …{r['text_tail']}")

    print(f"\n==== SUMMARY ({args.runs} runs) ====")
    print(f"  acted (no failing clarify): {acted_n}")
    print(f"    of which DENY→RECOVER (gate fired live): {denied_recovered_n}")
    print(f"  clarify-only deferrals (the OLD bug): {clarify_n}")
    print(f"  errors: {err_n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

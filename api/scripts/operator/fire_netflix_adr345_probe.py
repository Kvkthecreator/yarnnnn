#!/usr/bin/env python3
"""One-shot addressed-wake probe — ADR-345 / ADR-344 (B) on netflix-script-author.

Hat-B. Fires ONE operator-voice addressed message at the deployed API as the
netflix-script-author persona and captures the Reviewer's tool trace + response.

This proves the ADR-345 *capability* (a declared Expected Output + autonomous
delegation lets the Reviewer reason its standing obligation without the spurious
"what cadence?" Clarify, and author its own compose organ under the ADR-344 (B)
structurally-can't condition). It is NOT the unattended-cadence proof — an
addressed wake is `addressed`, not `cron_tick`. The unattended half is the
scheduler firing on its own clock (separate receipt).

The probe message is deliberately NEUTRAL — it does not name a cadence or tell
the agent what to do. If the workspace's declared `_expected_output.yaml`
(weekly) dissolves the missing-contract Clarify, the agent reasons forward from
its own substrate without asking "what cadence?".

Requires SUPABASE_SERVICE_KEY in env (load from api/.env). Run from api/.
"""
from __future__ import annotations

import asyncio
import json
import sys

import httpx

sys.path.insert(0, "scripts")
from alpha_ops._shared import load_registry, mint_jwt  # type: ignore

PERSONA_SLUG = "netflix-script-author"
API_BASE = "https://yarnnn-api.onrender.com"

# Neutral standing check-in — supplies NO cadence, NO directive. Lets the
# agent's own declared Expected Output + standing-obligation reasoning surface.
PROBE_MESSAGE = (
    "Checking in — where do things stand, and what's the next thing you're "
    "working toward? Go ahead and act on it if you're clear."
)


async def main() -> int:
    registry = load_registry()
    persona = registry.require(PERSONA_SLUG)
    jwt = await asyncio.get_running_loop().run_in_executor(
        None, lambda: mint_jwt(persona, registry=registry)
    )

    tools: list[str] = []
    clarify_seen = False
    ask_denied = False
    acted = False
    text = ""
    raw_events: list[dict] = []

    async with httpx.AsyncClient(
        timeout=300.0, base_url=API_BASE,
        headers={"Authorization": f"Bearer {jwt}", "Content-Type": "application/json"},
    ) as client:
        body = {"content": PROBE_MESSAGE, "include_context": True}
        async with client.stream("POST", "/api/feed", json=body) as resp:
            if resp.status_code >= 300:
                raw = await resp.aread()
                print(f"HTTP {resp.status_code}: {raw.decode('utf-8','replace')[:400]}")
                return 1
            async for line in resp.aiter_lines():
                if not line.startswith("data:"):
                    continue
                blob = line[len("data:"):].strip()
                if not blob:
                    continue
                try:
                    evt = json.loads(blob)
                except json.JSONDecodeError:
                    continue
                raw_events.append(evt)
                t = evt.get("tool")
                if t and evt.get("phase") == "tool_end":
                    tools.append(t)
                    if t == "Clarify":
                        clarify_seen = True
                    if t in ("WriteFile", "EditFile", "ProposeAction", "Schedule"):
                        acted = True
                if "ask_denied" in json.dumps(evt):
                    ask_denied = True
                if evt.get("reviewer_response"):
                    text = evt["reviewer_response"]

    print("\n==== NETFLIX ADR-345 ADDRESSED-WAKE PROBE ====")
    print(f"persona: {PERSONA_SLUG}  user_id: {persona.user_id}")
    print(f"tools fired: {tools}")
    print(f"clarify_seen: {clarify_seen}  ask_denied: {ask_denied}  acted: {acted}")
    # Did it ask "what cadence?" (the ADR-345 missing-contract symptom)?
    cadence_ask = clarify_seen and any(
        k in json.dumps(raw_events).lower()
        for k in ("what cadence", "which cadence", "how often", "delivery cadence")
    )
    print(f"missing-contract 'what cadence?' Clarify: {cadence_ask}")
    print(f"\nreviewer response (tail):\n{text[-1200:]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

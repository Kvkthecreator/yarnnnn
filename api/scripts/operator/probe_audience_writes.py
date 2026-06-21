"""Hat-B probe — live E2E of the ADR-304/307 kernel-universal audience-writes.

Scenario: yarnnn-author now has live Slack + Notion connections (platform-grade,
migration 186). Probe the path the 2026-06-19 platform-write-gate work added.

Under `manual` delegation the path is TWO gate hops:
  1. addressed wake → Reviewer DispatchSpecialist → gate QUEUEs a family=
     'substrate' proposal (the dispatch itself is consequential).
  2. operator approves the dispatch → specialist runs with write_slack/
     write_notion → calls platform_slack_send_to_channel → gate QUEUEs a
     family='external-write' proposal (the audience-write — the safety floor).
  3. operator approves the external-write → ExecuteProposal replays → REAL send.

Expected (load-bearing): step-2 produces an external-write proposal with an
effect-shaped decision_context (channel/preview), NOT a file diff; step-3 lands
the real Slack post + an execution_events cost row.

Side-effecting on approve. Runs against the DEPLOYED API (encryption key on
Render; never enters this host). Auth = operator JWT via SUPABASE_SERVICE_KEY.

Run: cd api && set -a; source .env; set +a; ./venv/bin/python -m scripts.operator.probe_audience_writes
"""

from __future__ import annotations

import asyncio
import json
import sys

import httpx

from services.operator_proxy.client import OperatorProxy

PERSONA = "yarnnn-author"
CALLER = "hat-b:probe-audience-writes"

INSTRUCTION = (
    "System test of the audience-write path. Use the tools you DO have. "
    "Call DispatchSpecialist (use whatever role is available to you — designer "
    "is fine) with required_capabilities=['write_slack','read_slack'] and this "
    "brief verbatim:\n\n"
    "  \"List Slack channels with platform_slack_list_channels, pick any channel "
    "you are a member of, then post the single message "
    "`yarnnn audience-write E2E test — please ignore` to it with "
    "platform_slack_send_to_channel(channel_id=<that id>, text=<that message>). "
    "Do only that one post, then stop.\"\n\n"
    "Do not do anything else yourself; just dispatch the specialist with that "
    "brief and report what it returns."
)


def banner(s: str) -> None:
    print(f"\n{'='*72}\n{s}\n{'='*72}", flush=True)


async def _widen(proxy: OperatorProxy) -> None:
    await proxy._ensure_client()  # type: ignore[attr-defined]
    proxy._client.timeout = httpx.Timeout(360.0)  # type: ignore[union-attr]


def _show_pending(pending: list[dict]) -> dict | None:
    ext = None
    for p in pending:
        print(f"  - id={p.get('id')} family={p.get('family')} "
              f"primitive={p.get('primitive')} "
              f"dc={json.dumps(p.get('decision_context') or {})[:240]}")
        if p.get("family") == "external-write":
            ext = p
    return ext


async def main() -> int:
    async with OperatorProxy.from_persona(PERSONA, caller=CALLER) as proxy:
        await _widen(proxy)

        banner("STEP 1 — addressed wake → Reviewer dispatches a write-capable specialist")
        resp = await proxy.send_message(INSTRUCTION)
        print("session_id:", resp.get("session_id"))
        print((resp.get("text") or "")[:900])

        banner("STEP 2 — pending after wake (expect family='substrate' DispatchSpecialist)")
        pending = await proxy.list_pending_proposals()
        print(f"pending: {len(pending)}")
        _show_pending(pending)
        dispatch = next((p for p in pending if p.get("primitive") == "DispatchSpecialist"), None)
        if not dispatch:
            print("No DispatchSpecialist proposal — Reviewer did not dispatch. Stop.")
            return 2

        banner("STEP 3 — approve the dispatch → specialist runs → audience-write QUEUEs")
        res = await proxy.approve_proposal(
            dispatch["id"], reasoning="Hat-B E2E — run the write-capable specialist.")
        print("dispatch approve:", json.dumps(res)[:500])

        # The specialist's platform_slack_send_to_channel call now QUEUEs an
        # external-write proposal (manual delegation). Give the deployed run a
        # moment, then read.
        await asyncio.sleep(3)
        pending = await proxy.list_pending_proposals()
        banner("STEP 4 — pending after dispatch (expect family='external-write')")
        print(f"pending: {len(pending)}")
        ext = _show_pending(pending)
        if not ext:
            print("No external-write proposal queued. Inspect execution_events + "
                  "the specialist transcript.")
            return 3

        banner("STEP 5 — approve the external-write → ExecuteProposal → REAL Slack send")
        res2 = await proxy.approve_proposal(
            ext["id"], reasoning="Hat-B E2E — approve the audience-write; real send.")
        print("external-write approve:", json.dumps(res2)[:700])
        ok = bool(res2.get("success")) and bool(
            (res2.get("execution_result") or {}).get("success"))
        print("\nREAL SEND SUCCEEDED:", ok)
        print("Check the Slack channel for the test message + execution_events "
              "for the cost row.")
        return 0 if ok else 4


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

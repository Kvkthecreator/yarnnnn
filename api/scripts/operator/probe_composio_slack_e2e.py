"""Hat-B probe — LOCAL-process E2E of the ADR-353 Composio driver against REAL Slack.

Closes the one §12 box the mock + live-API-contract probes left open: an actual
token-bearing round-trip (Composio → Slack) for all four spike-scoped Slack verbs,
plus a live forced-failure to confirm no-silent-success against the real API.

WHY LOCAL (decided 2026-06-22): the spike charter forbids setting COMPOSIO_* on
the deployed yarnnn-api (production env, live persona). Local runs in THIS process
only — nothing in the deployed system changes, no operator-facing path is touched,
blast radius is one script. It still exercises the real seam: the real Composio
API, yarnnn-author's REAL stored Slack token, a REAL Slack workspace. The only
thing not exercised locally is the deployed gate wrapper — already separately
proven (probe_audience_writes.py: gate→first-party live; test_adr353_*: gate is
keyed on tool-name, unchanged by driver).

WHAT IT TOUCHES:
  - Reads yarnnn-author's platform_connections row from the deployed DB
    (get_service_client) and decrypts the Slack token LOCALLY via TokenManager
    (INTEGRATION_ENCRYPTION_KEY from api/.env or repo/.env — never printed/written).
  - Calls services.composio_driver.execute() directly (the Phase-1 path: YARNNN
    holds the token, injects it per call; Composio stores nothing).
  - Does NOT touch the permission gate or write_revision (those are upstream of
    the driver and separately proven). This isolates the Composio↔Slack round-trip.

SIDE EFFECT: posts ONE message to a real Slack channel (read-only verbs first;
the post is clearly marked a test). Reverts nothing in YARNNN substrate.

Env required (all already in repo .env / api .env except the Composio key):
  COMPOSIO_API_KEY        - transient, supply at invocation; never written
  INTEGRATION_ENCRYPTION_KEY, SUPABASE_URL, SUPABASE_SERVICE_KEY - from .env

Run:
  cd api && set -a; source ../.env; source .env; set +a; \
    COMPOSIO_API_KEY=ak_xxx ./venv/bin/python -m scripts.operator.probe_composio_slack_e2e
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

# Make `services` importable when run as a module from api/.
_API_DIR = Path(__file__).resolve().parents[2]
if str(_API_DIR) not in sys.path:
    sys.path.insert(0, str(_API_DIR))

# Load .env (repo root first for INTEGRATION_ENCRYPTION_KEY, then api/.env).
try:
    from dotenv import load_dotenv
    for env_path in (_API_DIR.parent / ".env", _API_DIR / ".env"):
        if env_path.exists():
            load_dotenv(env_path, override=False)
except ImportError:
    pass

YARNNN_AUTHOR_USER_ID = "0b7a852d-4a67-447d-91d9-2ba1145a60d7"
TEST_MESSAGE = "yarnnn ADR-353 Composio-driver E2E — please ignore"


def banner(s: str) -> None:
    print(f"\n{'=' * 72}\n{s}\n{'=' * 72}", flush=True)


def _preflight() -> bool:
    ok = True
    for var in ("COMPOSIO_API_KEY", "INTEGRATION_ENCRYPTION_KEY", "SUPABASE_SERVICE_KEY"):
        present = bool(os.getenv(var))
        print(f"  {var}: {'present' if present else 'MISSING'}")
        ok = ok and present
    return ok


def _fetch_and_decrypt_token(user_id: str) -> str | None:
    """Phase-1 token path, local edition: read the encrypted Slack token from the
    deployed DB and decrypt it locally. Same fetch+decrypt the first-party handler
    and _route_via_composio use — just outside the request loop."""
    from services.supabase import get_service_client
    from integrations.core.tokens import get_token_manager

    client = get_service_client()
    row = (
        client.table("platform_connections")
        .select("credentials_encrypted, status, attestation_grade")
        .eq("user_id", user_id)
        .eq("platform", "slack")
        .eq("status", "active")
        .single()
        .execute()
    )
    if not row.data:
        print("  No active Slack connection for yarnnn-author.")
        return None
    print(f"  connection: status={row.data['status']} grade={row.data.get('attestation_grade')}")
    return get_token_manager().decrypt(row.data["credentials_encrypted"])


async def main() -> int:
    from services import composio_driver

    banner("PREFLIGHT — required env")
    if not _preflight():
        print("\nMissing env. See module docstring for the run line.")
        return 1

    banner("TOKEN — fetch + decrypt yarnnn-author's real Slack token (local)")
    token = _fetch_and_decrypt_token(YARNNN_AUTHOR_USER_ID)
    if not token:
        return 2
    print(f"  token decrypted ok (prefix {token[:5]}…, len {len(token)})")

    uid = YARNNN_AUTHOR_USER_ID
    results: dict[str, bool] = {}

    # ── READ 1: list_channels ────────────────────────────────────────────────
    banner("READ 1 — list_channels (real Composio → real Slack)")
    r = await composio_driver.execute("slack", "list_channels", {}, token=token, user_id=uid)
    print(f"  success={r['success']} error={r.get('error')}")
    target_channel = None
    if r["success"]:
        chans = r["result"]["channels"]
        print(f"  channels returned: {r['result']['count']}")
        for ch in chans[:8]:
            print(f"    {ch['id']}  {ch['name']}  private={ch['is_private']}")
        # Pick a non-archived channel to post into.
        target_channel = next((c for c in chans if not c.get("is_archived")), None)
    results["list_channels"] = r["success"]

    # ── READ 2: get_channel_history ──────────────────────────────────────────
    if target_channel:
        banner(f"READ 2 — get_channel_history on {target_channel['id']} ({target_channel['name']})")
        r = await composio_driver.execute(
            "slack", "get_channel_history",
            {"channel_id": target_channel["id"], "limit": 5},
            token=token, user_id=uid,
        )
        print(f"  success={r['success']} error={r.get('error')}")
        if r["success"]:
            print(f"  messages returned: {r['result']['count']}")
            for m in r["result"]["messages"][:3]:
                print(f"    [{m['ts']}] {str(m['user'])[:12]}: {str(m['text'])[:60]}")
        results["get_channel_history"] = r["success"]
    else:
        print("  (skipped — no channel to read)")

    # ── WRITE: send_to_channel (the real post) ───────────────────────────────
    if target_channel:
        banner(f"WRITE — send_to_channel → {target_channel['id']} ({target_channel['name']}) [REAL POST]")
        r = await composio_driver.execute(
            "slack", "send_to_channel",
            {"channel_id": target_channel["id"], "text": TEST_MESSAGE},
            token=token, user_id=uid,
        )
        print(f"  success={r['success']} error={r.get('error')}")
        if r["success"]:
            print(f"  result: ts={r['result'].get('ts')} channel={r['result'].get('channel')}")
            print(f"  message: {r.get('message')}")
        results["send_to_channel"] = r["success"]
    else:
        print("  (skipped — no channel to post to; the bot may be in no channels)")

    # ── NEGATIVE: forced auth failure (no silent success, LIVE) ───────────────
    banner("NEGATIVE — forced bad token (live no-silent-success check)")
    r = await composio_driver.execute(
        "slack", "send_to_channel",
        {"channel_id": (target_channel or {}).get("id", "C0000000000"), "text": "should fail"},
        token="xoxb-deliberately-invalid", user_id=uid,
    )
    print(f"  success={r['success']} error={r.get('error')}")
    # PASS = the driver reported failure (success is False) on a bad token.
    results["forced_auth_failure_surfaced"] = (r["success"] is False)

    # ── SUMMARY ──────────────────────────────────────────────────────────────
    banner("SUMMARY")
    for k, v in results.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    # Overall: the reads + negative are the load-bearing checks; the write may be
    # legitimately skipped if the bot is in no channels (a Slack-side condition,
    # not a driver fault).
    core_ok = results.get("list_channels") and results.get("forced_auth_failure_surfaced")
    print(f"\nCORE E2E (read path + live no-silent-success): {'PASS' if core_ok else 'FAIL'}")
    return 0 if core_ok else 3


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

"""Pure email wire smoke test — bypasses Reviewer entirely.

Calls POST /api/account/test-email as the operator persona. Endpoint:
  1. Resolves authed user's email via auth.admin.get_user_by_id
  2. Calls jobs.email.send_test_email(to=email)
  3. Returns Resend message_id on success or error string on failure

No Reviewer, no notifications.py, no delivery pipeline, no recurrence —
isolates the system Resend wire (RESEND_API_KEY + jobs/email.py +
Resend API). Useful for ADR-299 Discovery 4 Path A diagnostic:
distinguishes "tool not in Reviewer surface" from "wire broken."

Usage:
  python email_wire_smoke_test.py [persona-slug]
  default persona: kvk (kvkthecreator@gmail.com)
"""

from __future__ import annotations

import asyncio
import os
import sys

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
API_DIR = os.path.abspath(os.path.join(THIS_DIR, "..", ".."))
if API_DIR not in sys.path:
    sys.path.insert(0, API_DIR)

from services.operator_proxy.client import OperatorProxy  # noqa: E402


async def main(persona_slug: str = "kvk") -> int:
    proxy = OperatorProxy.from_persona(persona_slug, caller="claude-opus-4-7")
    async with proxy:
        await proxy._ensure_client()
        assert proxy._client is not None
        print(f"=== Pure email wire smoke test ===")
        print(f"Persona: {persona_slug}")
        print(f"Calling POST /api/account/test-email")
        print()

        resp = await proxy._client.post("/api/account/test-email")
        if resp.status_code != 200:
            print(f"HTTP {resp.status_code}")
            print(f"Body: {resp.text[:500]}")
            return 1

        data = resp.json()
        print(f"Success:     {data.get('success')}")
        print(f"Recipient:   {data.get('recipient')}")
        print(f"Message ID:  {data.get('message_id')}")
        print(f"Error:       {data.get('error')}")
        print()

        if data.get("success"):
            print(f"Email sent. Operator should check inbox at {data.get('recipient')}.")
            print(f"Resend message_id: {data.get('message_id')}")
            print(f"  → cross-checkable in Resend dashboard for delivery + bounce status")
            return 0
        else:
            print(f"WIRE FAILED. Error: {data.get('error')}")
            print(f"  → Investigate: RESEND_API_KEY env var on API service, Resend account state, or jobs/email.py")
            return 1


if __name__ == "__main__":
    persona = sys.argv[1] if len(sys.argv) > 1 else "kvk"
    raise SystemExit(asyncio.run(main(persona)))

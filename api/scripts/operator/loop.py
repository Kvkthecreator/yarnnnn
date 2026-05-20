"""ADR-294 — Interactive operator-proxy REPL.

Usage:
    .venv/bin/python -m api.scripts.operator.loop \\
        --persona alpha-trader-2 --caller claude-sonnet-4-7

Commands inside the REPL:
    > <text>                       — send operator-voice message to feed
    > /feed [limit]                — read recent feed messages
    > /proposals                   — list pending proposals
    > /approve <id> [reason]       — approve a proposal
    > /reject <id> <reason>        — reject a proposal
    > /read <path>                 — read a workspace file
    > /recurrences                 — list recurrences
    > /capture                     — snapshot current session into docs/observations/
    > /quit                        — exit
"""

from __future__ import annotations

import argparse
import asyncio
import os
import shlex
import sys
import textwrap
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


def _observation_folder(scenario_name: str) -> Path:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")
    slug = scenario_name.replace(" ", "-").lower()
    return REPO_ROOT / "docs" / "observations" / f"{now}-{slug}"


HELP_TEXT = """
Commands:
  <text>                  send operator-voice message to feed (addressed trigger)
  /feed [limit]           read recent feed messages (default 20)
  /proposals              list pending proposals
  /approve <id> [reason]  approve a proposal
  /reject <id> <reason>   reject a proposal
  /read <path>            read a workspace file
  /recurrences            list recurrences (scheduling index)
  /capture                snapshot session into docs/observations/<date>-<slug>/
  /help                   show this help
  /quit                   exit
"""


async def run_repl(persona_slug: str, caller: str) -> None:
    from services.operator_proxy import OperatorProxy
    from services.operator_proxy.capture import CaptureSession

    proxy = OperatorProxy.from_persona(persona_slug, caller=caller)
    capture_session: CaptureSession | None = None

    print(f"operator-proxy REPL — caller_identity = {proxy.config.caller_identity}")
    print(f"persona = {persona_slug}  user_id = {proxy.config.user_id}")
    print("type /help for commands\n")

    async with proxy:
        while True:
            try:
                raw = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not raw:
                continue

            if raw == "/quit" or raw == "/exit":
                break

            if raw == "/help":
                print(HELP_TEXT)
                continue

            if raw.startswith("/feed"):
                parts = raw.split()
                limit = int(parts[1]) if len(parts) > 1 else 20
                messages = await proxy.read_feed(limit=limit)
                for m in (messages or [])[-limit:]:
                    role = m.get("role", "?")
                    ts = m.get("created_at", "")
                    body = (m.get("content") or "")[:200]
                    print(f"[{ts}] {role}: {body}")
                continue

            if raw == "/proposals":
                proposals = await proxy.list_pending_proposals()
                if not proposals:
                    print("(no pending proposals)")
                else:
                    for p in proposals:
                        print(f"  {p['id']}  {p.get('action_type', '?')}  created={p.get('created_at', '?')}")
                continue

            if raw.startswith("/approve"):
                parts = shlex.split(raw)
                if len(parts) < 2:
                    print("usage: /approve <proposal_id> [reason]")
                    continue
                pid = parts[1]
                reason = " ".join(parts[2:]) if len(parts) > 2 else "Approved via REPL"
                try:
                    result = await proxy.approve_proposal(pid, reasoning=reason)
                    print(f"approved: success={result.get('success')}")
                except Exception as exc:
                    print(f"FAIL: {exc}")
                continue

            if raw.startswith("/reject"):
                parts = shlex.split(raw)
                if len(parts) < 3:
                    print("usage: /reject <proposal_id> <reason>")
                    continue
                pid = parts[1]
                reason = " ".join(parts[2:])
                try:
                    result = await proxy.reject_proposal(pid, reason=reason)
                    print(f"rejected: success={result.get('success')}")
                except Exception as exc:
                    print(f"FAIL: {exc}")
                continue

            if raw.startswith("/read"):
                parts = raw.split(maxsplit=1)
                if len(parts) < 2:
                    print("usage: /read <path>")
                    continue
                content = await proxy.read_file(parts[1])
                if content is None:
                    print("(file not found)")
                else:
                    print(content)
                continue

            if raw == "/recurrences":
                recurrences = await proxy.list_recurrences()
                for r in recurrences or []:
                    print(f"  {r.get('slug', '?')}  status={r.get('status', '?')}  schedule={r.get('schedule', '-')}")
                continue

            if raw == "/capture":
                if capture_session is None:
                    folder = _observation_folder(f"repl-{persona_slug}")
                    capture_session = await CaptureSession.start(
                        proxy.config.user_id,
                        folder,
                        scenario_name=f"REPL session ({persona_slug})",
                    )
                    print(f"baseline captured at {folder}")
                else:
                    await capture_session.snapshot()
                    print(f"snapshot complete: {capture_session.folder}")
                    capture_session = None
                continue

            # default: treat as operator-voice chat message
            try:
                response = await proxy.send_message(raw)
                text = response.get("text") or ""
                print(textwrap.indent(text, "  reviewer: "))
                if response.get("reviewer_verdict"):
                    print(f"  [reviewer_verdict event present]")
            except Exception as exc:
                print(f"FAIL: {exc}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Operator-proxy REPL (ADR-294)")
    ap.add_argument("--persona", required=True, help="Persona slug from personas.yaml")
    ap.add_argument("--caller", default="claude-sonnet-4-7", help="Caller identity tag (default: claude-sonnet-4-7)")
    args = ap.parse_args()

    asyncio.run(run_repl(args.persona, args.caller))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

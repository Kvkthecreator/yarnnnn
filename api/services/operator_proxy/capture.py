"""ADR-294 D7 — Observation capture.

Snapshots a workspace's state at session start + end, diffs them, and
writes machine-produced artifacts under docs/observations/{folder}/.
Findings.md is left as a human-written stub.

Capture artifacts:
    README.md           — 1-line summary + persona + outcome
    PLAYBOOK.md         — scenario or REPL summary + observed shape
    transcript.md       — session_messages window
    substrate-diff.md   — files touched + revision chain + authored_by
    decisions.md        — Reviewer decisions written during window
    proposals.md        — action_proposals created + their fate
    token-usage.md      — execution_events grouped by caller_identity
    findings.md         — STUB (operator writes the interpretation)
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Snapshot data
# ---------------------------------------------------------------------------

@dataclass
class CaptureSnapshot:
    """Workspace state at one moment. Used as baseline + endpoint."""

    user_id: str
    captured_at: str                         # ISO timestamp
    revision_ids: set[str] = field(default_factory=set)
    proposal_ids: set[str] = field(default_factory=set)
    message_ids: set[str] = field(default_factory=set)
    execution_event_ids: set[str] = field(default_factory=set)


# ---------------------------------------------------------------------------
# Capture session
# ---------------------------------------------------------------------------

class CaptureSession:
    """Bookends an operator-proxy session, then dumps artifacts.

    Usage:
        session = await CaptureSession.start(user_id, folder, scenario_name="warm-start")
        # ... operator-proxy actions happen ...
        await session.snapshot()
    """

    def __init__(self, user_id: str, folder: Path, scenario_name: str | None = None):
        self.user_id = user_id
        self.folder = folder
        self.scenario_name = scenario_name
        self.baseline: Optional[CaptureSnapshot] = None
        self.endpoint: Optional[CaptureSnapshot] = None
        self.metadata: dict[str, Any] = {}  # caller can stash arbitrary observation context

    @classmethod
    async def start(
        cls,
        user_id: str,
        folder: Path,
        *,
        scenario_name: str | None = None,
    ) -> "CaptureSession":
        """Take a baseline snapshot. Folder is created if missing."""
        folder.mkdir(parents=True, exist_ok=True)
        session = cls(user_id, folder, scenario_name=scenario_name)
        session.baseline = await _take_snapshot(user_id)
        return session

    async def snapshot(self) -> None:
        """Take endpoint snapshot, compute diffs, write all artifacts."""
        if self.baseline is None:
            raise RuntimeError("CaptureSession.snapshot() called before start()")
        self.endpoint = await _take_snapshot(self.user_id)
        await self._write_artifacts()

    async def _write_artifacts(self) -> None:
        assert self.baseline is not None
        assert self.endpoint is not None

        # Compute diffs.
        new_revision_ids = self.endpoint.revision_ids - self.baseline.revision_ids
        new_proposal_ids = self.endpoint.proposal_ids - self.baseline.proposal_ids
        new_message_ids = self.endpoint.message_ids - self.baseline.message_ids
        new_event_ids = self.endpoint.execution_event_ids - self.baseline.execution_event_ids

        # README — 1-line summary.
        readme = self.folder / "README.md"
        readme.write_text(
            f"# Observation — {self.scenario_name or 'ad-hoc session'}\n\n"
            f"- **User**: `{self.user_id}`\n"
            f"- **Started**: {self.baseline.captured_at}\n"
            f"- **Ended**: {self.endpoint.captured_at}\n"
            f"- **New revisions**: {len(new_revision_ids)}\n"
            f"- **New proposals**: {len(new_proposal_ids)}\n"
            f"- **New messages**: {len(new_message_ids)}\n"
            f"- **New execution events**: {len(new_event_ids)}\n\n"
            f"See `findings.md` for qualitative interpretation.\n"
        )

        # PLAYBOOK — scenario name + metadata.
        playbook = self.folder / "PLAYBOOK.md"
        playbook.write_text(
            f"# Playbook — {self.scenario_name or 'ad-hoc session'}\n\n"
            + (f"## Metadata\n\n```json\n{json.dumps(self.metadata, indent=2, default=str)}\n```\n"
               if self.metadata else "(No metadata captured.)\n")
        )

        # transcript.md — new session_messages.
        transcript_md = await _format_transcript(self.user_id, new_message_ids)
        (self.folder / "transcript.md").write_text(transcript_md)

        # substrate-diff.md — new revisions.
        substrate_md = await _format_substrate_diff(self.user_id, new_revision_ids)
        (self.folder / "substrate-diff.md").write_text(substrate_md)

        # decisions.md — slice of /workspace/review/decisions.md since baseline.
        decisions_md = await _format_decisions_slice(self.user_id, self.baseline.captured_at)
        (self.folder / "decisions.md").write_text(decisions_md)

        # proposals.md — new action_proposals + their current state.
        proposals_md = await _format_proposals(self.user_id, new_proposal_ids)
        (self.folder / "proposals.md").write_text(proposals_md)

        # token-usage.md — execution_events grouped by caller_identity.
        token_md = await _format_token_usage(self.user_id, new_event_ids)
        (self.folder / "token-usage.md").write_text(token_md)

        # findings.md — STUB only; operator writes the interpretation.
        findings = self.folder / "findings.md"
        if not findings.exists():
            findings.write_text(
                "# Findings\n\n"
                "*Operator interpretation of this observation. What did the Reviewer do? "
                "What surprised us? What does this validate or contradict in the canon?*\n\n"
                "(Draft this section after reading the machine-produced artifacts.)\n"
            )


# ---------------------------------------------------------------------------
# Snapshot machinery
# ---------------------------------------------------------------------------

async def _take_snapshot(user_id: str) -> CaptureSnapshot:
    """Read current state from DB. Records IDs only — diffs come from
    comparing sets at end."""
    from services.supabase import get_service_client

    client = get_service_client()
    now_iso = datetime.now(timezone.utc).isoformat()
    snap = CaptureSnapshot(user_id=user_id, captured_at=now_iso)

    # revision IDs
    rows = client.table("workspace_file_versions").select("id").eq("user_id", user_id).execute()
    snap.revision_ids = {r["id"] for r in (rows.data or [])}

    # proposal IDs
    rows = client.table("action_proposals").select("id").eq("user_id", user_id).execute()
    snap.proposal_ids = {r["id"] for r in (rows.data or [])}

    # session_message IDs (via chat_sessions)
    sessions = client.table("chat_sessions").select("id").eq("user_id", user_id).execute()
    session_ids = [s["id"] for s in (sessions.data or [])]
    if session_ids:
        msgs = client.table("session_messages").select("id").in_("session_id", session_ids).execute()
        snap.message_ids = {m["id"] for m in (msgs.data or [])}

    # execution_event IDs
    rows = client.table("execution_events").select("id").eq("user_id", user_id).execute()
    snap.execution_event_ids = {r["id"] for r in (rows.data or [])}

    return snap


# ---------------------------------------------------------------------------
# Artifact formatters
# ---------------------------------------------------------------------------

async def _format_transcript(user_id: str, message_ids: set[str]) -> str:
    if not message_ids:
        return "# Transcript\n\n(No new session messages in this window.)\n"

    from services.supabase import get_service_client
    client = get_service_client()
    rows = (
        client.table("session_messages")
        .select("id, role, content, created_at, metadata")
        .in_("id", list(message_ids))
        .order("created_at")
        .execute()
    )
    lines = ["# Transcript", ""]
    for m in rows.data or []:
        ts = m.get("created_at", "")
        role = m.get("role", "?")
        content = m.get("content", "") or ""
        lines.append(f"## [{ts}] {role}\n")
        lines.append(content)
        lines.append("")
    return "\n".join(lines)


async def _format_substrate_diff(user_id: str, revision_ids: set[str]) -> str:
    if not revision_ids:
        return "# Substrate diff\n\n(No new revisions in this window.)\n"

    from services.supabase import get_service_client
    client = get_service_client()
    rows = (
        client.table("workspace_file_versions")
        .select("id, path, authored_by, message, created_at, parent_version_id")
        .in_("id", list(revision_ids))
        .order("created_at")
        .execute()
    )

    # Group by authored_by for legibility.
    by_author: dict[str, list[dict]] = {}
    for r in rows.data or []:
        by_author.setdefault(r["authored_by"], []).append(r)

    lines = [f"# Substrate diff — {len(revision_ids)} new revisions", ""]
    for author in sorted(by_author):
        revs = by_author[author]
        lines.append(f"## `{author}` ({len(revs)} revisions)\n")
        for r in revs:
            ts = r.get("created_at", "")
            path = r.get("path", "")
            msg = (r.get("message") or "").strip()
            lines.append(f"- **{path}** — {ts}")
            if msg:
                lines.append(f"  > {msg}")
        lines.append("")
    return "\n".join(lines)


async def _format_decisions_slice(user_id: str, since_iso: str) -> str:
    """Read current /workspace/review/decisions.md and return entries
    created after since_iso. Simple substring filter on timestamp lines."""
    from services.supabase import get_service_client
    client = get_service_client()
    rows = (
        client.table("workspace_files")
        .select("content")
        .eq("user_id", user_id)
        .eq("path", "/workspace/review/decisions.md")
        .execute()
    )
    if not rows.data:
        return "# Decisions slice\n\n(No /workspace/review/decisions.md exists.)\n"
    content = rows.data[0].get("content") or ""

    # Split on `--- decision ---` blocks and filter by timestamp.
    blocks = content.split("--- decision ---")
    fresh: list[str] = []
    for block in blocks[1:]:  # skip preamble
        # First line in each block looks like:  timestamp: 2026-05-20T00:12:22+00:00
        ts_line = block.strip().splitlines()[0] if block.strip() else ""
        if "timestamp:" in ts_line:
            ts_value = ts_line.split("timestamp:", 1)[1].strip()
            if ts_value >= since_iso:
                fresh.append("--- decision ---" + block)
    if not fresh:
        return f"# Decisions slice\n\n(No new decisions since {since_iso}.)\n"
    return "# Decisions slice\n\n" + "\n".join(fresh)


async def _format_proposals(user_id: str, proposal_ids: set[str]) -> str:
    if not proposal_ids:
        return "# Proposals\n\n(No new action_proposals in this window.)\n"

    from services.supabase import get_service_client
    client = get_service_client()
    rows = (
        client.table("action_proposals")
        .select("id, action_type, status, created_at, rationale, expected_effect")
        .in_("id", list(proposal_ids))
        .order("created_at")
        .execute()
    )
    lines = [f"# Proposals — {len(proposal_ids)} new", ""]
    for p in rows.data or []:
        lines.append(f"## {p.get('action_type', '?')} — status={p.get('status', '?')}")
        lines.append(f"- **id**: `{p['id']}`")
        lines.append(f"- **created**: {p.get('created_at', '?')}")
        if p.get("rationale"):
            lines.append(f"- **rationale**:\n\n```\n{p['rationale']}\n```")
        if p.get("expected_effect"):
            lines.append(f"- **expected effect**: {p['expected_effect']}")
        lines.append("")
    return "\n".join(lines)


async def _format_token_usage(user_id: str, event_ids: set[str]) -> str:
    if not event_ids:
        return "# Token usage\n\n(No new execution_events in this window.)\n"

    from services.supabase import get_service_client
    client = get_service_client()
    rows = (
        client.table("execution_events")
        .select("caller_identity, cost_usd, prompt_tokens, completion_tokens, created_at")
        .in_("id", list(event_ids))
        .execute()
    )
    by_caller: dict[str, dict] = {}
    for r in rows.data or []:
        caller = r.get("caller_identity") or "(unknown)"
        slot = by_caller.setdefault(caller, {"count": 0, "cost_usd": 0.0, "prompt": 0, "completion": 0})
        slot["count"] += 1
        slot["cost_usd"] += float(r.get("cost_usd") or 0)
        slot["prompt"] += int(r.get("prompt_tokens") or 0)
        slot["completion"] += int(r.get("completion_tokens") or 0)

    lines = ["# Token usage", "", "| Caller | Events | Cost (USD) | Prompt tok | Completion tok |", "|---|---|---|---|---|"]
    for caller in sorted(by_caller):
        d = by_caller[caller]
        lines.append(
            f"| `{caller}` | {d['count']} | {d['cost_usd']:.4f} | {d['prompt']:,} | {d['completion']:,} |"
        )
    return "\n".join(lines)

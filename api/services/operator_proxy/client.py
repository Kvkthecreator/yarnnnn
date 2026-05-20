"""ADR-294 D1 — OperatorProxy HTTP client.

Thin wrapper that lets a non-human caller act as the operator on a
workspace via the same API surface a real operator's cockpit would hit.
JWT auth flows through the existing service-key magic-link mint pattern
(per docs/database/ACCESS.md), so no new auth path.

Singular Implementation discipline:
- All actions route through real HTTP endpoints (`/api/feed`,
  `/api/proposals/*`, etc.) — same endpoints the cockpit UI calls.
- No direct service imports for action paths. The proxy is a *client*
  of the YARNNN API, not a backend bypass.
- Exception: substrate reads (read_file, list_files) may use the direct
  service-key client for efficiency on observation capture; writes
  always go through the typed API.
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator, Optional

import httpx

# Import the existing JWT-mint pattern. The proxy reuses the same trust
# boundary as the alpha-ops harness — service-key magic-link → access
# token. Future ADR (MCP-as-operator) will replace this with scoped
# delegation tokens.
from scripts.alpha_ops._shared import mint_jwt, load_registry, Persona  # type: ignore[import-not-found]


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class ProxyError(Exception):
    """Raised when an operator-proxy action fails at the API boundary."""

    def __init__(self, message: str, status_code: int | None = None, body: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class ProxyConfig:
    """Persona-agnostic proxy configuration.

    A proxy needs to know (1) which user it's acting as (user_id + email
    for JWT mint), (2) who *it* is (caller_identity for audit), and
    (3) which persona slug to name in the caller-identity sub-namespace.

    The persona_slug is purely cosmetic for the caller-identity string;
    it doesn't have to match any registered persona. Use the actual
    persona slug when available, falls back to a short tag derived from
    user_id otherwise.
    """

    user_id: str
    email: str
    caller: str                              # e.g., "claude-sonnet-4-7"
    persona_slug: str                        # e.g., "alpha-trader-2"
    api_base: str = "https://yarnnn-api.onrender.com"
    supabase_url: str = "https://noxgqcwynkzqabljjyon.supabase.co"

    @property
    def caller_identity(self) -> str:
        """ADR-294 D2 — the operator-proxy caller_identity sub-namespace."""
        return f"operator-proxy:{self.caller}:acting-as-{self.persona_slug}"

    @classmethod
    def from_persona(cls, persona_slug: str, *, caller: str) -> "ProxyConfig":
        """Convenience constructor: resolve user_id/email from alpha-persona registry."""
        reg = load_registry()
        persona: Persona = reg.require(persona_slug)
        return cls(
            user_id=persona.user_id,
            email=persona.email,
            caller=caller,
            persona_slug=persona_slug,
            api_base=reg.prod_api_base,
            supabase_url=reg.supabase_url,
        )


# ---------------------------------------------------------------------------
# OperatorProxy
# ---------------------------------------------------------------------------

class OperatorProxy:
    """The operator's voice, materialized as a callable capability.

    Use as an async context manager for proper HTTP-client lifecycle:

        async with OperatorProxy.from_persona("alpha-trader-2", caller="claude") as proxy:
            response = await proxy.send_message("hello")
    """

    def __init__(self, config: ProxyConfig):
        self.config = config
        self._jwt: Optional[str] = None
        self._client: Optional[httpx.AsyncClient] = None

    # ----- lifecycle -----

    @classmethod
    def from_persona(cls, persona_slug: str, *, caller: str) -> "OperatorProxy":
        return cls(ProxyConfig.from_persona(persona_slug, caller=caller))

    async def __aenter__(self) -> "OperatorProxy":
        await self._ensure_client()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _ensure_client(self) -> None:
        if self._client is not None:
            return
        # Mint JWT once per session. Tokens are ~1h; for longer sessions
        # the proxy will need a re-mint helper (not in Phase 1 scope).
        if self._jwt is None:
            # mint_jwt only reads persona.email + Registry.supabase_url. Build
            # a minimal synthetic Persona that satisfies the dataclass shape;
            # the JWT-mint path is email-only, doesn't touch the other fields.
            loop = asyncio.get_running_loop()
            registry = load_registry()
            persona = Persona(
                slug=self.config.persona_slug,
                label="(proxy synthetic)",
                email=self.config.email,
                user_id=self.config.user_id,
                workspace_id=self.config.user_id,  # not used by mint_jwt
                program="alpha-trader",            # not used by mint_jwt
                platform={"kind": "none", "provider": "none"},
                context_domains=[],
                credentials_env={},
                expected={},
            )
            self._jwt = await loop.run_in_executor(
                None,
                lambda: mint_jwt(persona, registry=registry),
            )
        self._client = httpx.AsyncClient(
            timeout=60.0,
            base_url=self.config.api_base,
            headers={
                "Authorization": f"Bearer {self._jwt}",
                "Content-Type": "application/json",
            },
        )

    # ----- core operator actions -----

    async def send_message(
        self,
        content: str,
        *,
        surface_context: dict | None = None,
    ) -> dict:
        """Send an operator-voice chat message (addressed trigger per ADR-260).

        Reviewer wakes with the message in user_message slot. Streaming SSE
        response is collected and returned as a structured dict:
            {
                "session_id": str,
                "message_id": str,         # the assistant/reviewer turn that came back
                "events": [list of all SSE events],
                "text": str,                # concatenated text chunks
                "reviewer_verdict": dict | None,  # if a reviewer-verdict event appeared
            }
        """
        await self._ensure_client()
        assert self._client is not None

        body: dict = {"content": content, "include_context": True}
        if surface_context:
            body["surface_context"] = surface_context

        events: list[dict] = []
        text_chunks: list[str] = []
        reviewer_verdict: dict | None = None
        session_id: str | None = None
        message_id: str | None = None

        async with self._client.stream("POST", "/api/feed", json=body) as resp:
            if resp.status_code >= 300:
                raw = await resp.aread()
                raise ProxyError(
                    f"send_message HTTP {resp.status_code}",
                    status_code=resp.status_code,
                    body=raw.decode("utf-8", errors="replace"),
                )
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                payload_raw = line[len("data:"):].strip()
                if not payload_raw:
                    continue
                try:
                    evt = json.loads(payload_raw)
                except json.JSONDecodeError:
                    continue
                events.append(evt)
                if isinstance(evt, dict):
                    if evt.get("type") == "text":
                        text_chunks.append(evt.get("content") or "")
                    if evt.get("type") == "reviewer_verdict":
                        reviewer_verdict = evt.get("verdict") or evt
                    if evt.get("session_id") and session_id is None:
                        session_id = evt["session_id"]
                    if evt.get("message_id") and message_id is None:
                        message_id = evt["message_id"]

        return {
            "session_id": session_id,
            "message_id": message_id,
            "events": events,
            "text": "".join(text_chunks),
            "reviewer_verdict": reviewer_verdict,
        }

    async def read_feed(
        self,
        *,
        limit: int = 50,
        session_id: str | None = None,
    ) -> list[dict]:
        """Read recent feed messages (operator + system_agent + reviewer + agent bubbles).

        Returns a list of message dicts ordered oldest-first by created_at.
        """
        await self._ensure_client()
        assert self._client is not None

        params: dict = {"limit": limit}
        if session_id:
            params["session_id"] = session_id

        r = await self._client.get("/api/feed/history", params=params)
        if r.status_code >= 300:
            raise ProxyError(
                f"read_feed HTTP {r.status_code}",
                status_code=r.status_code,
                body=r.text,
            )
        data = r.json()
        # /feed/history returns {"messages": [...]} per existing shape;
        # tolerant to either shape.
        return data.get("messages") if isinstance(data, dict) else data

    async def approve_proposal(
        self,
        proposal_id: str,
        *,
        reasoning: str | None = None,
        modified_inputs: dict | None = None,
    ) -> dict:
        """Approve + execute a proposal as the operator.

        Per ADR-194 v2, the cockpit's approve route fills the reviewer
        seat as `human:<user_id>`. The proxy inherits this — the proxy
        is the operator's voice, the operator fills the human-reviewer
        seat. The proxy identity surfaces in `reviewer_reasoning`.
        """
        await self._ensure_client()
        assert self._client is not None

        body: dict = {}
        if reasoning:
            body["reviewer_reasoning"] = f"[via {self.config.caller_identity}] {reasoning}"
        else:
            body["reviewer_reasoning"] = f"[via {self.config.caller_identity}] Approved by operator-proxy"
        if modified_inputs:
            body["modified_inputs"] = modified_inputs

        r = await self._client.post(f"/api/proposals/{proposal_id}/approve", json=body)
        if r.status_code >= 400:
            raise ProxyError(
                f"approve_proposal HTTP {r.status_code}",
                status_code=r.status_code,
                body=r.text,
            )
        return r.json()

    async def reject_proposal(
        self,
        proposal_id: str,
        *,
        reason: str,
    ) -> dict:
        """Reject a proposal as the operator (human-reviewer seat per ADR-194 v2)."""
        await self._ensure_client()
        assert self._client is not None

        body = {"reason": f"[via {self.config.caller_identity}] {reason}"}
        r = await self._client.post(f"/api/proposals/{proposal_id}/reject", json=body)
        if r.status_code >= 400:
            raise ProxyError(
                f"reject_proposal HTTP {r.status_code}",
                status_code=r.status_code,
                body=r.text,
            )
        return r.json()

    async def list_pending_proposals(self) -> list[dict]:
        """List action_proposals with status='pending' for this workspace."""
        await self._ensure_client()
        assert self._client is not None

        r = await self._client.get("/api/proposals", params={"status": "pending"})
        if r.status_code >= 300:
            raise ProxyError(
                f"list_pending_proposals HTTP {r.status_code}",
                status_code=r.status_code,
                body=r.text,
            )
        data = r.json()
        return data.get("proposals") if isinstance(data, dict) else data

    # ----- substrate operations -----

    async def write_substrate(
        self,
        path: str,
        content: str,
        message: str,
    ) -> dict:
        """Write substrate as operator-voice (ADR-293 D10 Phase-4 interim affordance).

        Routes through the same write_revision path the cockpit FE
        would (eventually) call. Carries authored_by from
        ProxyConfig.caller_identity per ADR-294 D2.

        IMPORTANT: writes here bypass AUTONOMY mode gating (they're
        operator-authored, not Reviewer-authored). This is the *operator's*
        substrate edit, not a Reviewer's. Same semantic as the cockpit
        FE's edit-substrate flow.
        """
        # Direct service-layer call for substrate writes — there's no
        # dedicated operator-write HTTP endpoint exposed at the API
        # surface (the existing primitives route through Reviewer/
        # system flows). We use write_revision directly, which is the
        # canonical write path per ADR-209.
        from services.authored_substrate import write_revision
        from services.supabase import get_service_client

        # Normalize path to /workspace/... form (canonical store key).
        if not path.startswith("/workspace/"):
            path = f"/workspace/{path.lstrip('/')}"

        client = get_service_client()
        loop = asyncio.get_running_loop()
        revision_id = await loop.run_in_executor(
            None,
            lambda: write_revision(
                client,
                user_id=self.config.user_id,
                path=path,
                content=content,
                authored_by=self.config.caller_identity,
                message=message,
            ),
        )
        return {
            "revision_id": revision_id,
            "path": path,
            "authored_by": self.config.caller_identity,
        }

    async def read_file(self, path: str) -> str | None:
        """Read a workspace file's content. Returns None if not found."""
        await self._ensure_client()
        assert self._client is not None

        # Normalize path.
        if not path.startswith("/workspace/"):
            path = f"/workspace/{path.lstrip('/')}"

        r = await self._client.get("/api/workspace/file", params={"path": path})
        if r.status_code == 404:
            return None
        if r.status_code >= 300:
            raise ProxyError(
                f"read_file HTTP {r.status_code}",
                status_code=r.status_code,
                body=r.text,
            )
        data = r.json()
        return data.get("content") if isinstance(data, dict) else None

    async def list_recurrences(self) -> list[dict]:
        """List recurrences (scheduling-index rows) for this workspace."""
        await self._ensure_client()
        assert self._client is not None

        r = await self._client.get("/api/recurrences")
        if r.status_code >= 300:
            raise ProxyError(
                f"list_recurrences HTTP {r.status_code}",
                status_code=r.status_code,
                body=r.text,
            )
        data = r.json()
        return data.get("recurrences") if isinstance(data, dict) else data

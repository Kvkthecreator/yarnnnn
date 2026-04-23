"""
Agent Workspace — ADR-106

Virtual filesystem over Postgres for agent workspaces.
Storage-agnostic abstraction: agents interact via path-based operations.

Three classes:
- AgentWorkspace: scoped to /agents/{slug}/ — one per agent
- (KnowledgeBase: DELETED by ADR-151 — replaced by /workspace/context/ domain registry)
- UserMemory: scoped to /memory/ — global user identity, preferences, notes (ADR-108)

Backing store is `workspace_files` table. Swap to S3/GCS by reimplementing
these classes — agent code doesn't change.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class WorkspaceFile:
    """A file in the workspace."""
    path: str
    content: str
    summary: Optional[str] = None
    content_type: str = "text/markdown"
    metadata: dict = None
    tags: list[str] = None
    content_url: Optional[str] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        self.metadata = self.metadata or {}
        self.tags = self.tags or []


@dataclass
class SearchResult:
    """A search result from the workspace."""
    path: str
    summary: Optional[str]
    content: str
    rank: float = 0.0
    updated_at: Optional[datetime] = None
    metadata: Optional[dict] = None  # ADR-116: knowledge provenance (agent_id, role, scope)


class AgentWorkspace:
    """
    Workspace scoped to a single agent: /agents/{slug}/

    Provides read/write access to the agent's working state:
    thesis, memory, observations, feedback, runs, working notes.
    """

    def __init__(self, db_client, user_id: str, agent_slug: str):
        self._db = db_client
        self._user_id = user_id
        self._slug = agent_slug
        self._base = f"/agents/{agent_slug}"

    def _full_path(self, relative: str) -> str:
        """Convert relative path to absolute workspace path."""
        if relative.startswith("/"):
            relative = relative.lstrip("/")
        return f"{self._base}/{relative}"

    async def read(self, relative_path: str) -> Optional[str]:
        """Read a file's content. Returns None if not found."""
        path = self._full_path(relative_path)
        try:
            result = (
                self._db.table("workspace_files")
                .select("content")
                .eq("user_id", self._user_id)
                .eq("path", path)
                .limit(1)
                .execute()
            )
            rows = result.data or []
            if rows:
                return rows[0]["content"]
            return None
        except Exception as e:
            logger.warning(f"[WORKSPACE] Read failed: {path}: {e}")
            return None

    async def read_file(self, relative_path: str) -> Optional[WorkspaceFile]:
        """Read a full file object. Returns None if not found."""
        path = self._full_path(relative_path)
        try:
            result = (
                self._db.table("workspace_files")
                .select("path, content, summary, content_type, metadata, tags, content_url, updated_at")
                .eq("user_id", self._user_id)
                .eq("path", path)
                .limit(1)
                .execute()
            )
            rows = result.data or []
            if rows:
                return WorkspaceFile(**rows[0])
            return None
        except Exception as e:
            logger.warning(f"[WORKSPACE] Read file failed: {path}: {e}")
            return None

    @staticmethod
    def _infer_lifecycle(path: str) -> str:
        """ADR-119/127: Infer lifecycle from path convention."""
        if "/working/" in path:
            return "ephemeral"
        if "/user_shared/" in path:
            return "ephemeral"
        return "active"

    async def write(
        self,
        relative_path: str,
        content: str,
        summary: str = None,
        tags: list[str] = None,
        lifecycle: str = None,
        content_type: str = None,
        content_url: str = None,
        metadata: dict = None,
        *,
        authored_by: str = None,
        message: str = None,
    ) -> bool:
        """Write a file through the Authored Substrate (ADR-209).

        Routes through services.authored_substrate.write_revision() — every
        write lands a revision with authored_by + message attribution and
        preserves the prior content in the revision chain.

        authored_by default (when not supplied): f"agent:{self._slug}" — the
        class is scoped to one agent, so the agent slug is the correct
        Identity unless the caller has better context (e.g., YARNNN writing
        an agent's file on operator behalf → override with "yarnnn:<model>"
        or "operator").

        message default: f"write {relative_path}". Callers are encouraged
        to supply a specific message (e.g., "seed AGENT.md" or "append
        observation"); the default exists so class wrappers don't force
        every internal caller to synthesize one.

        ADR-119: lifecycle auto-inferred from path (/working/ → ephemeral)
        when not supplied. Version history is no longer an application
        concern — every write creates a revision automatically.
        """
        from services.authored_substrate import write_revision

        path = self._full_path(relative_path)
        resolved_author = authored_by or f"agent:{self._slug}"
        resolved_message = message or f"write {relative_path}"
        resolved_lifecycle = lifecycle or self._infer_lifecycle(path)

        try:
            write_revision(
                self._db,
                user_id=self._user_id,
                path=path,
                content=content,
                authored_by=resolved_author,
                message=resolved_message,
                summary=summary,
                tags=tags,
                lifecycle=resolved_lifecycle,
                content_type=content_type,
                content_url=content_url,
                metadata=metadata,
            )
            return True
        except Exception as e:
            logger.error(f"[WORKSPACE] Write failed: {path}: {e}")
            return False

    async def append(
        self,
        relative_path: str,
        content: str,
        *,
        authored_by: str = None,
        message: str = None,
    ) -> bool:
        """Append content to a file. Creates if doesn't exist.

        Each append lands a new revision capturing prior-content + new
        content concatenated. Callers can pass authored_by / message
        to attribute the append; defaults are AgentWorkspace.write()'s.
        """
        existing = await self.read(relative_path)
        new_content = content if existing is None else (existing + "\n" + content)
        return await self.write(
            relative_path,
            new_content,
            authored_by=authored_by,
            message=message or f"append to {relative_path}",
        )

    async def list(self, relative_path: str = "", recursive: bool = False,
                   include_lifecycle: list[str] = None) -> list[str]:
        """List files under a path. Returns relative paths.

        ADR-119: By default excludes ephemeral and archived files.
        Pass include_lifecycle to override (e.g., ['ephemeral'] to list scratch files).
        """
        prefix = self._full_path(relative_path)
        if not prefix.endswith("/"):
            prefix += "/"
        try:
            q = (
                self._db.table("workspace_files")
                .select("path")
                .eq("user_id", self._user_id)
                .like("path", f"{prefix}%")
            )
            # ADR-119: Lifecycle filter — default excludes ephemeral/archived
            if include_lifecycle:
                q = q.in_("lifecycle", include_lifecycle)
            else:
                q = q.in_("lifecycle", ["active", "delivered"])
            result = q.order("path").execute()
            paths = [r["path"] for r in (result.data or [])]

            if not recursive:
                # Only direct children: filter out nested paths
                direct = set()
                for p in paths:
                    remainder = p[len(prefix):]
                    if "/" in remainder:
                        # It's a directory — return the dir name
                        direct.add(remainder.split("/")[0] + "/")
                    else:
                        direct.add(remainder)
                return sorted(direct)

            # Recursive: return all paths relative to prefix
            return [p[len(prefix):] for p in paths]
        except Exception as e:
            logger.warning(f"[WORKSPACE] List failed: {prefix}: {e}")
            return []

    async def search(self, query: str, path_prefix: str = None, limit: int = 10) -> list[SearchResult]:
        """Full-text search within this agent's workspace."""
        full_prefix = self._full_path(path_prefix) if path_prefix else self._base
        try:
            result = self._db.rpc("search_workspace", {
                "p_user_id": self._user_id,
                "p_query": query,
                "p_path_prefix": full_prefix,
                "p_limit": limit,
            }).execute()

            return [
                SearchResult(
                    path=r["path"],
                    summary=r.get("summary"),
                    content=r["content"][:500],  # Truncate for search results
                    rank=r.get("rank", 0),
                    updated_at=r.get("updated_at"),
                )
                for r in (result.data or [])
            ]
        except Exception as e:
            logger.warning(f"[WORKSPACE] Search failed: {query}: {e}")
            return []

    async def delete(self, relative_path: str) -> bool:
        """Delete a file."""
        path = self._full_path(relative_path)
        try:
            self._db.table("workspace_files").delete().eq(
                "user_id", self._user_id
            ).eq("path", path).execute()
            return True
        except Exception as e:
            logger.warning(f"[WORKSPACE] Delete failed: {path}: {e}")
            return False

    async def exists(self, relative_path: str) -> bool:
        """Check if a file exists."""
        path = self._full_path(relative_path)
        try:
            result = (
                self._db.table("workspace_files")
                .select("id")
                .eq("user_id", self._user_id)
                .eq("path", path)
                .limit(1)
                .execute()
            )
            return bool(result.data)
        except Exception:
            return False

    # =========================================================================
    # Migration: seed workspace from agent DB columns (ADR-106 Phase 2)
    # =========================================================================

    async def ensure_seeded(self, agent: dict) -> None:
        """
        Lazy migration: if workspace is empty, seed from DB columns.
        Also seeds any missing playbooks from the type registry (ADR-157).
        Called once per execution — idempotent.
        """
        # Check if workspace has any files (fast path for full seed)
        files = await self.list("")
        if not files:
            # Full seed from DB columns
            instructions = (agent.get("agent_instructions") or "").strip()
            if instructions:
                await self.write(
                    "AGENT.md",
                    instructions,
                    summary="Agent identity and behavioral instructions",
                    authored_by="system:agent-seed",
                    message="seed AGENT.md from agent DB columns",
                )
            logger.info(f"[WORKSPACE] Seeded workspace from DB columns: {self._slug}")

        # ADR-157: Seed any missing playbooks from type registry
        # This handles retroactive playbook additions (new playbook added to
        # agent_framework.py after agent was created). Idempotent — skips existing.
        role = agent.get("role", "")
        if role:
            from services.agent_framework import get_type_playbook
            playbooks = get_type_playbook(role)
            for filename, content in playbooks.items():
                existing = await self.read(f"memory/{filename}")
                if not existing:
                    await self.write(
                        f"memory/{filename}",
                        content,
                        summary=f"Playbook seed: {filename}",
                        authored_by="system:playbook-seed",
                        message=f"seed playbook {filename} for role={role}",
                    )
                    logger.info(f"[WORKSPACE] Seeded missing playbook: {self._slug}/memory/{filename}")

    # =========================================================================
    # =========================================================================
    # ADR-154: Dissolved agent-level accessors — safe no-ops
    # These methods are called from various code paths but no longer write
    # to agent workspace. Execution state lives on tasks; domain knowledge
    # lives in /workspace/context/. Kept as no-ops to avoid breaking callers.
    # =========================================================================

    async def get_observations(self) -> list[dict]:
        """ADR-154: Dissolved. Returns empty list."""
        return []

    async def get_review_log(self) -> list[dict]:
        """ADR-154: Dissolved. Returns empty list."""
        return []

    async def get_created_agents(self) -> list[dict]:
        """ADR-154: Dissolved. Returns empty list."""
        return []

    async def get_goal(self) -> Optional[dict]:
        """ADR-154: Dissolved. Returns None."""
        return None

    async def get_state(self, key: str) -> Optional[str]:
        """ADR-154: Dissolved. Returns None."""
        return None

    async def set_state(self, key: str, value: str) -> bool:
        """ADR-154: Dissolved. No-op, returns True."""
        return True

    async def append_observation(self, note: str, source: str = "trigger") -> int:
        """ADR-154: Dissolved. No-op, returns 0."""
        return 0

    async def clear_observations(self) -> bool:
        """ADR-154: Dissolved. No-op, returns True."""
        return True

    async def append_created_agent(self, title: str, dedup_key: str) -> bool:
        """ADR-154: Dissolved. No-op, returns True."""
        return True

    async def record_observation(self, note: str, source: str = "review") -> bool:
        """ADR-154: Dissolved. No-op, returns True."""
        return True

    async def update_thesis(self, thesis: str) -> bool:
        """ADR-154: Dissolved. Domain understanding lives in context domains."""
        return True

    # =========================================================================
    # Convenience methods for common workspace patterns
    # =========================================================================

    async def load_context(self, output_kind: str | None = None) -> str:
        """Load the agent's identity context for generation.

        ADR-154: Agent workspace is WHO only — identity + methodology.
        Execution state (reflections, feedback, working notes) lives on tasks.
        Domain knowledge lives in /workspace/context/ domains.

        ADR-157: Referential playbook injection (Claude Code pattern).
        System prompt gets compact index + critical rules (~100 tokens).
        Full playbook content readable on demand via ReadFile (ADR-168).

        ADR-166: Routing key is task `output_kind`, not `task_class`.

        Args:
            output_kind: One of accumulates_context | produces_deliverable |
                         external_action | system_maintenance — determines
                         which playbooks are highlighted as relevant. None =
                         all (backward compat).

        Returns formatted string of AGENT.md + feedback + playbook index.
        """
        parts = []

        # AGENT.md — identity and directives (like CLAUDE.md)
        agent_md = await self.read("AGENT.md")
        if agent_md:
            parts.append(f"## Agent Directives\n{agent_md}")

        # Agent feedback — cross-task style/tone preferences (ADR-156 3-layer model)
        feedback = await self.read("memory/feedback.md")
        if feedback and feedback.strip():
            parts.append(f"## Agent Feedback (cross-task)\n{feedback}")

        # Playbook index — referential, not full content (Claude Code pattern)
        from services.agent_framework import PLAYBOOK_METADATA, TASK_OUTPUT_PLAYBOOK_ROUTING

        memory_files = await self.list("memory/")
        playbook_files = [
            f for f in memory_files
            if not f.endswith("/") and (f.startswith("_playbook") or f.startswith("methodology-"))
        ]

        if playbook_files:
            # ADR-166: route by output_kind
            relevant_tags = None
            if output_kind and output_kind in TASK_OUTPUT_PLAYBOOK_ROUTING:
                relevant_tags = set(TASK_OUTPUT_PLAYBOOK_ROUTING[output_kind])

            index_lines = [
                "## Agent Methodology",
                "Your playbooks are in memory/. Read them via ReadFile when making methodology decisions.",
            ]
            for filename in playbook_files:
                meta = PLAYBOOK_METADATA.get(filename, {})
                desc = meta.get("description", filename.replace("_playbook-", "").replace(".md", ""))
                name = filename.replace("_playbook-", "").replace(".md", "").replace("-", " ").title()

                # Mark relevant playbooks
                is_relevant = True
                if relevant_tags is not None:
                    playbook_tags = set(meta.get("tags", "").split(","))
                    is_relevant = bool(relevant_tags & playbook_tags)

                marker = " ← relevant" if is_relevant else ""
                index_lines.append(f"- **{name}** (memory/{filename}): {desc}{marker}")

            # Critical rules — always apply, extracted from playbooks
            index_lines.append("")
            index_lines.append("**Always apply:**")
            index_lines.append("- Check domain assets/ folder for existing visuals before generating new")
            index_lines.append("- Use BRAND.md colors when available, professional defaults otherwise")
            index_lines.append("- Every visual must carry information — no decorative filler")

            parts.append("\n".join(index_lines))

        return "\n\n---\n\n".join(parts) if parts else ""

    # ----- Duty helpers (ADR-117 Phase 3) -----

    async def read_duty(self, duty_name: str) -> Optional[str]:
        """Read a duty file from /duties/{duty_name}.md."""
        return await self.read(f"duties/{duty_name}.md")

    async def write_duty(self, duty_name: str, content: str) -> bool:
        """Write a duty file to /duties/{duty_name}.md."""
        return await self.write(
            f"duties/{duty_name}.md",
            content,
            summary=f"Duty configuration: {duty_name}",
        )

    async def list_duties(self) -> list[str]:
        """List all duty files in /duties/."""
        files = await self.list("duties/")
        return [f.replace(".md", "") for f in files if f.endswith(".md")]

    async def save_output(
        self,
        content: str,
        run_id: str,
        agent_id: str,
        version_number: int,
        role: str = None,
        rendered_files: list[dict] = None,
        sources: list[str] = None,
    ) -> Optional[str]:
        """ADR-119 Phase 1: Save agent output to a dated output folder with manifest.

        Creates /agents/{slug}/outputs/{date}/ folder with:
        - output.md — the text output (feedback surface)
        - manifest.json — metadata about the run (files, sources, delivery status)
        - Any rendered binary file references (from RuntimeDispatch)

        Args:
            content: The text output (markdown)
            run_id: The agent_run UUID
            agent_id: The agent UUID
            version_number: The run version number
            role: Agent role (digest, synthesize, etc.)
            rendered_files: Optional list of rendered file dicts from RuntimeDispatch
                [{path, content_type, content_url, size_bytes, role}]
            sources: Optional list of source paths consumed during this run

        Returns:
            The output folder path (e.g., "outputs/2026-03-18T0900/"), or None on failure.
        """
        import json as _json

        now = datetime.now(timezone.utc)
        # ADR-119 Resolved Decision #2: truncated to hour
        date_folder = now.strftime("%Y-%m-%dT%H00")
        folder_path = f"outputs/{date_folder}"

        # 1. Write the text output
        text_success = await self.write(
            f"{folder_path}/output.md",
            content,
            summary=f"Run v{version_number} output",
            tags=["output", f"v{version_number}", role or ""],
            lifecycle="active",
        )
        if not text_success:
            return None

        # 2. Build manifest
        files = [
            {"path": "output.md", "type": "text/markdown", "role": "primary"},
        ]

        # Add rendered files (from RuntimeDispatch)
        if rendered_files:
            for rf in rendered_files:
                files.append({
                    "path": rf.get("path", ""),
                    "type": rf.get("content_type", ""),
                    "role": rf.get("role", "rendered"),
                    "content_url": rf.get("content_url", ""),
                    "size_bytes": rf.get("size_bytes", 0),
                })

        manifest = {
            "run_id": run_id,
            "agent_id": agent_id,
            "version": version_number,
            "role": role,
            "created_at": now.isoformat(),
            "status": "active",
            "files": files,
            "sources": sources or [],
            "feedback": {},
        }

        # 3. Write manifest.json
        await self.write(
            f"{folder_path}/manifest.json",
            _json.dumps(manifest, indent=2),
            summary=f"Run v{version_number} manifest",
            tags=["manifest", f"v{version_number}"],
            content_type="application/json",
            lifecycle="active",
            metadata={
                "agent_id": agent_id,
                "run_id": run_id,
                "version_number": version_number,
                "role": role,
            },
        )

        logger.info(f"[WORKSPACE] ADR-119: Saved output to {self._base}/{folder_path}/ ({len(files)} files)")
        return folder_path

    async def update_manifest_delivery(
        self,
        output_folder: str,
        delivery_status: dict,
    ) -> bool:
        """ADR-118 D.3: Update manifest.json with delivery status after send.

        Args:
            output_folder: The output folder path (e.g., "outputs/2026-03-18T0900")
            delivery_status: Delivery result dict, e.g.:
                {"channel": "email", "sent_at": "...", "message_id": "...", "status": "delivered"}

        Returns:
            True on success.
        """
        import json as _json

        manifest_content = await self.read(f"{output_folder}/manifest.json")
        if not manifest_content:
            logger.warning(f"[WORKSPACE] ADR-118 D.3: Manifest not found at {output_folder}/manifest.json")
            return False

        try:
            manifest = _json.loads(manifest_content)
        except _json.JSONDecodeError:
            logger.warning(f"[WORKSPACE] ADR-118 D.3: Invalid manifest JSON at {output_folder}")
            return False

        manifest["delivery"] = delivery_status
        manifest["status"] = "delivered" if delivery_status.get("status") == "delivered" else manifest.get("status", "active")

        return await self.write(
            f"{output_folder}/manifest.json",
            _json.dumps(manifest, indent=2),
            summary=f"Run manifest (delivered)",
            content_type="application/json",
            lifecycle="delivered",
        )


# KnowledgeBase class DELETED — ADR-151: Replaced by /workspace/context/ domain registry.
# All callers migrated to use domain_registry.py + UserMemory for context domain writes,
# and direct workspace_files queries for reads.
# See: api/services/domain_registry.py (CONTEXT_DOMAINS)
# See: docs/adr/ADR-151-shared-knowledge-domains.md


class UserMemory:
    """
    User workspace context: /workspace/ (ADR-133, relocated by ADR-206).

    Authored shared context lives under /workspace/context/_shared/:
    - /workspace/context/_shared/IDENTITY.md    — who you are (name, role, company, timezone, summary)
    - /workspace/context/_shared/BRAND.md       — how outputs look and sound
    - /workspace/context/_shared/CONVENTIONS.md — workspace filesystem rules (agent-readable)

    YARNNN working memory lives under /workspace/memory/:
    - /workspace/memory/awareness.md — situational notes, shift handoff
    - /workspace/memory/_playbook.md — orchestration playbook (hidden)
    - /workspace/memory/style.md     — inferred style from edit patterns
    - /workspace/memory/notes.md     — standing instructions, observed facts

    Callers pass full workspace-relative paths (e.g. "context/_shared/IDENTITY.md");
    paths are defined as canonical constants in services.workspace_paths.
    """

    def __init__(self, db_client, user_id: str):
        self._db = db_client
        self._user_id = user_id
        self._base = "/workspace"

    def _full_path(self, filename: str) -> str:
        """Convert filename to absolute workspace path."""
        return f"{self._base}/{filename}"

    async def read(self, filename: str) -> Optional[str]:
        """Read a memory file. Returns None if not found."""
        path = self._full_path(filename)
        try:
            result = (
                self._db.table("workspace_files")
                .select("content")
                .eq("user_id", self._user_id)
                .eq("path", path)
                .limit(1)
                .execute()
            )
            rows = result.data or []
            return rows[0]["content"] if rows else None
        except Exception as e:
            logger.warning(f"[USER_MEMORY] Read failed: {path}: {e}")
            return None

    def read_sync(self, filename: str) -> Optional[str]:
        """Synchronous read for thread pool use (working_memory.py)."""
        path = self._full_path(filename)
        try:
            result = (
                self._db.table("workspace_files")
                .select("content")
                .eq("user_id", self._user_id)
                .eq("path", path)
                .limit(1)
                .execute()
            )
            rows = result.data or []
            return rows[0]["content"] if rows else None
        except Exception as e:
            logger.warning(f"[USER_MEMORY] Read sync failed: {path}: {e}")
            return None

    async def write(
        self,
        filename: str,
        content: str,
        summary: str = None,
        content_type: str = None,
        content_url: str = None,
        metadata: dict = None,
        *,
        authored_by: str = None,
        message: str = None,
    ) -> bool:
        """Write a memory file through the Authored Substrate (ADR-209).

        UserMemory spans two content classes with different typical authors:
          - /workspace/context/_shared/* — authored shared context
            (IDENTITY.md, BRAND.md, CONVENTIONS.md). Typical author:
            `operator` (via route handlers) or `yarnnn:<model>` (via
            inference primitives).
          - /workspace/memory/* — YARNNN working memory (awareness, notes,
            conversation summary, style distillation). Typical author:
            `yarnnn:<model>` or `system:*`.

        Default `authored_by` is `"system:user-memory"` — callers that
        know better context MUST override. Leaving the default is a
        correctness smell, not a bug (the substrate still records the
        write, but with weaker attribution than possible).

        ADR-157: Supports content_url for binary asset references.
        """
        from services.authored_substrate import write_revision

        path = self._full_path(filename)
        resolved_author = authored_by or "system:user-memory"
        resolved_message = message or f"write {filename}"

        try:
            write_revision(
                self._db,
                user_id=self._user_id,
                path=path,
                content=content,
                authored_by=resolved_author,
                message=resolved_message,
                summary=summary,
                content_type=content_type,
                content_url=content_url,
                metadata=metadata,
            )
            return True
        except Exception as e:
            logger.error(f"[USER_MEMORY] Write failed: {path}: {e}")
            return False

    async def read_all(self) -> dict[str, str]:
        """Read workspace context files. Returns {basename: content}.

        ADR-206: reads shared context from /workspace/context/_shared/ and
        working-memory files from /workspace/memory/. Keys are basenames
        so downstream formatters (working_memory.format_compact_index,
        daily-update template) get stable identifiers independent of
        layout changes.
        """
        from services.workspace_paths import (
            SHARED_IDENTITY_PATH, SHARED_BRAND_PATH,
            MEMORY_STYLE_PATH, MEMORY_NOTES_PATH,
        )
        files: dict[str, str] = {}
        for path in (SHARED_IDENTITY_PATH, SHARED_BRAND_PATH, MEMORY_STYLE_PATH, MEMORY_NOTES_PATH):
            content = await self.read(path)
            if content:
                files[path.rsplit("/", 1)[-1]] = content
        return files

    def read_all_sync(self) -> dict[str, str]:
        """Synchronous read_all for thread pool use."""
        from services.workspace_paths import (
            SHARED_IDENTITY_PATH, SHARED_BRAND_PATH,
            MEMORY_STYLE_PATH, MEMORY_NOTES_PATH,
        )
        files: dict[str, str] = {}
        for path in (SHARED_IDENTITY_PATH, SHARED_BRAND_PATH, MEMORY_STYLE_PATH, MEMORY_NOTES_PATH):
            content = self.read_sync(path)
            if content:
                files[path.rsplit("/", 1)[-1]] = content
        return files

    async def get_profile(self) -> dict:
        """Parse IDENTITY.md into structured profile dict."""
        from services.workspace_paths import SHARED_IDENTITY_PATH
        content = await self.read(SHARED_IDENTITY_PATH)
        return self._parse_memory_md(content)

    async def update_profile(self, updates: dict, *, authored_by: str = "operator") -> bool:
        """Update profile fields in IDENTITY.md (read-merge-write).

        Defaults to `authored_by="operator"` since identity edits typically
        come through routes/memory.py (operator action). YARNNN inference
        updates should override with `yarnnn:<model>`.
        """
        from services.workspace_paths import SHARED_IDENTITY_PATH
        current = await self.get_profile()
        current.update({k: v for k, v in updates.items() if v is not None})
        for k, v in updates.items():
            if v is None or v == "":
                current.pop(k, None)
        return await self.write(
            SHARED_IDENTITY_PATH,
            self._render_memory_md(current),
            summary="User identity",
            authored_by=authored_by,
            message="update user identity profile",
        )

    async def get_preferences(self) -> dict:
        """Parse style.md into structured dict."""
        from services.workspace_paths import MEMORY_STYLE_PATH
        content = await self.read(MEMORY_STYLE_PATH)
        return self._parse_preferences_md(content)

    async def update_preferences(
        self, platform: str, updates: dict, *, authored_by: str = "operator"
    ) -> bool:
        """Update preferences for a platform (read-merge-write).

        Defaults `authored_by="operator"` — preferences are typically edited
        by the user via the Context surface. ADR-117 style distillation
        should override with `system:feedback-distillation` when
        auto-updating.
        """
        prefs = await self.get_preferences()
        if not any(v for v in updates.values()):
            prefs.pop(platform, None)
        else:
            prefs.setdefault(platform, {}).update(
                {k: v for k, v in updates.items() if v}
            )
            # Remove cleared sub-keys
            for k, v in updates.items():
                if not v and k in prefs.get(platform, {}):
                    del prefs[platform][k]
            if platform in prefs and not prefs[platform]:
                del prefs[platform]
        from services.workspace_paths import MEMORY_STYLE_PATH
        return await self.write(
            MEMORY_STYLE_PATH,
            self._render_preferences_md(prefs),
            summary="Communication and content preferences",
            authored_by=authored_by,
            message=f"update preferences for {platform}",
        )

    async def get_notes(self) -> list[dict]:
        """Parse notes.md into list of {type, content}."""
        from services.workspace_paths import MEMORY_NOTES_PATH
        content = await self.read(MEMORY_NOTES_PATH)
        return self._parse_notes_md(content)

    async def add_note(
        self, note_type: str, content: str, *, authored_by: str = "operator"
    ) -> bool:
        """Append a note to notes.md. Defaults to operator attribution."""
        from services.workspace_paths import MEMORY_NOTES_PATH
        notes = await self.get_notes()
        notes.append({"type": note_type, "content": content})
        return await self.write(
            MEMORY_NOTES_PATH,
            self._render_notes_md(notes),
            summary="Standing instructions and observed facts",
            authored_by=authored_by,
            message=f"add {note_type} note",
        )

    async def remove_note(self, content: str, *, authored_by: str = "operator") -> bool:
        """Remove a note by content match. Defaults to operator attribution."""
        from services.workspace_paths import MEMORY_NOTES_PATH
        notes = await self.get_notes()
        notes = [n for n in notes if n["content"] != content]
        return await self.write(
            MEMORY_NOTES_PATH,
            self._render_notes_md(notes),
            summary="Standing instructions and observed facts",
            authored_by=authored_by,
            message="remove note",
        )

    async def replace_notes(
        self, notes: list[dict], *, authored_by: str = "system:memory-extraction"
    ) -> bool:
        """Replace all notes (used by extraction cron read-merge-write)."""
        from services.workspace_paths import MEMORY_NOTES_PATH
        return await self.write(
            MEMORY_NOTES_PATH,
            self._render_notes_md(notes),
            summary="Standing instructions and observed facts",
            authored_by=authored_by,
            message="replace notes (bulk)",
        )

    # =========================================================================
    # Markdown parsing/rendering
    # =========================================================================

    @staticmethod
    def _parse_memory_md(content: Optional[str]) -> dict:
        """Parse MEMORY.md YAML-like frontmatter into dict."""
        if not content:
            return {}
        profile = {}
        for line in content.strip().split("\n"):
            line = line.strip()
            if line.startswith("#"):
                continue
            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip().lower()
                value = value.strip()
                if key in ("name", "role", "company", "timezone", "summary"):
                    profile[key] = value if value else None
        return profile

    @staticmethod
    def _render_memory_md(profile: dict) -> str:
        """Render profile dict as MEMORY.md content."""
        lines = ["# About Me", ""]
        field_order = ["name", "role", "company", "timezone", "summary"]
        for key in field_order:
            value = profile.get(key)
            if value:
                lines.append(f"{key}: {value}")
        return "\n".join(lines) + "\n"

    @staticmethod
    def _parse_preferences_md(content: Optional[str]) -> dict:
        """Parse style.md into {platform: {tone, verbosity}}."""
        if not content:
            return {}
        prefs = {}
        current_platform = None
        for line in content.strip().split("\n"):
            line = line.strip()
            if line.startswith("## "):
                current_platform = line[3:].strip().lower()
            elif current_platform and ":" in line:
                key, _, value = line.partition(":")
                key = key.strip().lower().lstrip("- ")
                value = value.strip()
                if key in ("tone", "verbosity") and value:
                    prefs.setdefault(current_platform, {})[key] = value
        return prefs

    @staticmethod
    def _render_preferences_md(prefs: dict) -> str:
        """Render preferences dict as style.md content."""
        lines = ["# Communication Preferences", ""]
        for platform in sorted(prefs.keys()):
            settings = prefs[platform]
            if not settings:
                continue
            lines.append(f"## {platform}")
            if settings.get("tone"):
                lines.append(f"- tone: {settings['tone']}")
            if settings.get("verbosity"):
                lines.append(f"- verbosity: {settings['verbosity']}")
            lines.append("")
        return "\n".join(lines) if any(prefs.values()) else ""

    @staticmethod
    def _parse_notes_md(content: Optional[str]) -> list[dict]:
        """Parse notes.md into list of {type, content}."""
        if not content:
            return []
        notes = []
        for line in content.strip().split("\n"):
            line = line.strip()
            if not line.startswith("- "):
                continue
            text = line[2:].strip()
            # Parse type prefix: "Instruction: ...", "Fact: ...", "Preference: ..."
            for prefix in ("Instruction:", "Fact:", "Preference:"):
                if text.startswith(prefix):
                    notes.append({
                        "type": prefix.rstrip(":").lower(),
                        "content": text[len(prefix):].strip(),
                    })
                    break
            else:
                notes.append({"type": "fact", "content": text})
        return notes

    @staticmethod
    def _render_notes_md(notes: list[dict]) -> str:
        """Render notes list as notes.md content."""
        if not notes:
            return ""
        lines = ["# Notes", ""]
        type_labels = {"instruction": "Instruction", "fact": "Fact", "preference": "Preference"}
        for note in notes:
            label = type_labels.get(note.get("type", "fact"), "Fact")
            lines.append(f"- {label}: {note['content']}")
        return "\n".join(lines) + "\n"


async def get_agent_intelligence(client, user_id: str, agent: dict) -> dict:
    """
    ADR-106: Read agent intelligence from workspace for API responses.

    Returns dict with keys matching AgentResponse fields:
      - agent_instructions: str (from AGENT.md)
      - agent_memory: dict (observations, goal, review_log, created_agents, last_generated_at)

    This is the ONLY place agent_instructions/agent_memory should be populated
    for API responses. DB columns are not read.
    """
    ws = AgentWorkspace(client, user_id, get_agent_slug(agent))
    await ws.ensure_seeded(agent)  # Lazy migration from DB columns (one-time)

    instructions = (await ws.read("AGENT.md") or "").strip()
    goal = await ws.get_goal()
    created_agents = await ws.get_created_agents()
    last_generated_at = await ws.get_state("last_generated_at")
    # ADR-143: Unified feedback file
    feedback = (await ws.read("memory/feedback.md") or "").strip()
    reflections = (await ws.read("memory/reflections.md") or "").strip()

    memory = {}
    if goal:
        memory["goal"] = goal
    if created_agents:
        memory["created_agents"] = created_agents
    if last_generated_at:
        memory["last_generated_at"] = last_generated_at
    if feedback:
        memory["feedback"] = feedback
    if reflections:
        memory["reflections"] = reflections

    return {
        "agent_instructions": instructions or None,
        "agent_memory": memory or None,
    }


def get_agent_slug(agent: dict) -> str:
    """
    Derive a filesystem-safe slug for an agent.
    Uses title if available, falls back to ID.
    """
    title = agent.get("title", "")
    agent_id = agent.get("id", "unknown")

    if title:
        # Lowercase, replace spaces/special chars with hyphens
        slug = title.lower().strip()
        slug = "".join(c if c.isalnum() or c == "-" else "-" for c in slug)
        slug = "-".join(part for part in slug.split("-") if part)  # Remove consecutive hyphens
        return slug[:50]  # Cap length

    return str(agent_id)[:36]

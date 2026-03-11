"""
Agent Workspace — ADR-106

Virtual filesystem over Postgres for agent workspaces.
Storage-agnostic abstraction: agents interact via path-based operations.

Two classes:
- AgentWorkspace: scoped to /agents/{slug}/ — one per agent
- KnowledgeBase: scoped to /knowledge/ — shared, read-only for agents

Backing store is `workspace_files` table. Swap to S3/GCS by reimplementing
these classes — agent code doesn't change.
"""

import logging
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
                .maybe_single()
                .execute()
            )
            if result.data:
                return result.data["content"]
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
                .select("path, content, summary, content_type, metadata, tags, updated_at")
                .eq("user_id", self._user_id)
                .eq("path", path)
                .maybe_single()
                .execute()
            )
            if result.data:
                return WorkspaceFile(**result.data)
            return None
        except Exception as e:
            logger.warning(f"[WORKSPACE] Read file failed: {path}: {e}")
            return None

    async def write(self, relative_path: str, content: str, summary: str = None, tags: list[str] = None) -> bool:
        """Write a file (upsert). Returns True on success."""
        path = self._full_path(relative_path)
        try:
            data = {
                "user_id": self._user_id,
                "path": path,
                "content": content,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            if summary is not None:
                data["summary"] = summary
            if tags is not None:
                data["tags"] = tags

            self._db.table("workspace_files").upsert(
                data,
                on_conflict="user_id,path",
            ).execute()
            return True
        except Exception as e:
            logger.error(f"[WORKSPACE] Write failed: {path}: {e}")
            return False

    async def append(self, relative_path: str, content: str) -> bool:
        """Append content to a file. Creates if doesn't exist."""
        existing = await self.read(relative_path)
        if existing is None:
            return await self.write(relative_path, content)
        return await self.write(relative_path, existing + "\n" + content)

    async def list(self, relative_path: str = "", recursive: bool = False) -> list[str]:
        """List files under a path. Returns relative paths."""
        prefix = self._full_path(relative_path)
        if not prefix.endswith("/"):
            prefix += "/"
        try:
            result = (
                self._db.table("workspace_files")
                .select("path")
                .eq("user_id", self._user_id)
                .like("path", f"{prefix}%")
                .order("path")
                .execute()
            )
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
                .maybe_single()
                .execute()
            )
            return result.data is not None
        except Exception:
            return False

    # =========================================================================
    # Convenience methods for common workspace patterns
    # =========================================================================

    async def load_context(self) -> str:
        """
        Load the agent's working context for generation.
        Returns a formatted string of thesis + memory + feedback.
        """
        parts = []

        thesis = await self.read("thesis.md")
        if thesis:
            parts.append(f"## Current Thesis\n{thesis}")

        memory = await self.read("memory.md")
        if memory:
            parts.append(f"## Accumulated Observations\n{memory}")

        feedback = await self.read("feedback.md")
        if feedback:
            parts.append(f"## Learned Preferences\n{feedback}")

        directives = await self.read("directives.md")
        if directives:
            parts.append(f"## Agent Directives\n{directives}")

        # Load recent working notes
        working = await self.list("working/")
        for filename in working[-3:]:  # Last 3 working notes
            if filename.endswith("/"):
                continue
            note = await self.read(f"working/{filename}")
            if note:
                parts.append(f"## Working Note: {filename}\n{note}")

        return "\n\n---\n\n".join(parts) if parts else ""

    async def record_observation(self, note: str, source: str = "review") -> bool:
        """Append an observation to memory.md with timestamp."""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        entry = f"- [{timestamp}] ({source}) {note}"
        return await self.append("memory.md", entry)

    async def update_thesis(self, thesis: str) -> bool:
        """Update the agent's thesis (full replacement)."""
        return await self.write(
            "thesis.md",
            thesis,
            summary="Agent's current domain understanding",
        )

    async def save_run(self, run_number: int, content: str, metadata: dict = None) -> bool:
        """Save an agent run output."""
        return await self.write(
            f"runs/v{run_number}.md",
            content,
            summary=f"Run v{run_number} output",
            tags=["run", f"v{run_number}"],
        )


class KnowledgeBase:
    """
    Shared knowledge base: /knowledge/

    Read-only for agents. Written by the perception pipeline.
    Provides search across all synced platform content.
    """

    def __init__(self, db_client, user_id: str):
        self._db = db_client
        self._user_id = user_id
        self._base = "/knowledge"

    async def search(self, query: str, platform: str = None, limit: int = 20) -> list[SearchResult]:
        """Search the knowledge base. Optionally filter by platform."""
        prefix = f"{self._base}/{platform}" if platform else self._base
        try:
            result = self._db.rpc("search_workspace", {
                "p_user_id": self._user_id,
                "p_query": query,
                "p_path_prefix": prefix,
                "p_limit": limit,
            }).execute()

            return [
                SearchResult(
                    path=r["path"],
                    summary=r.get("summary"),
                    content=r["content"][:500],
                    rank=r.get("rank", 0),
                    updated_at=r.get("updated_at"),
                )
                for r in (result.data or [])
            ]
        except Exception as e:
            logger.warning(f"[KNOWLEDGE] Search failed: {query}: {e}")
            return []

    async def read(self, path: str) -> Optional[str]:
        """Read a knowledge base file by full path under /knowledge/."""
        full_path = f"{self._base}/{path}" if not path.startswith("/") else path
        try:
            result = (
                self._db.table("workspace_files")
                .select("content")
                .eq("user_id", self._user_id)
                .eq("path", full_path)
                .maybe_single()
                .execute()
            )
            if result.data:
                return result.data["content"]
            return None
        except Exception as e:
            logger.warning(f"[KNOWLEDGE] Read failed: {full_path}: {e}")
            return None

    async def list_platforms(self) -> list[str]:
        """List available platforms in the knowledge base."""
        try:
            result = (
                self._db.table("workspace_files")
                .select("path")
                .eq("user_id", self._user_id)
                .like("path", f"{self._base}/%")
                .execute()
            )
            platforms = set()
            for r in (result.data or []):
                # Extract platform from /knowledge/{platform}/...
                parts = r["path"][len(self._base) + 1:].split("/")
                if parts:
                    platforms.add(parts[0])
            return sorted(platforms)
        except Exception as e:
            logger.warning(f"[KNOWLEDGE] List platforms failed: {e}")
            return []


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

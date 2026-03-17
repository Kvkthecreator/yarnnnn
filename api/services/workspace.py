"""
Agent Workspace — ADR-106

Virtual filesystem over Postgres for agent workspaces.
Storage-agnostic abstraction: agents interact via path-based operations.

Three classes:
- AgentWorkspace: scoped to /agents/{slug}/ — one per agent
- KnowledgeBase: scoped to /knowledge/ — shared, read-only for agents
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
    metadata: Optional[dict] = None  # ADR-116: knowledge provenance (agent_id, skill, scope)


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
                .select("path, content, summary, content_type, metadata, tags, updated_at")
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
        Lazy migration: if workspace is empty but agent has DB columns
        (agent_instructions, agent_memory), seed workspace files from them.
        Called once per execution — idempotent.
        """
        # Check if workspace has any files (fast path: already seeded)
        files = await self.list("")
        if files:
            return  # Workspace already has content

        # Seed AGENT.md from agent_instructions
        instructions = (agent.get("agent_instructions") or "").strip()
        if instructions:
            await self.write("AGENT.md", instructions,
                             summary="Agent identity and behavioral instructions")

        # Seed memory/ from agent_memory JSONB
        memory = agent.get("agent_memory") or {}

        # Observations → memory/observations.md
        observations = memory.get("observations", [])
        if observations:
            lines = []
            for obs in observations:
                date = obs.get("date", "")
                note = obs.get("note", "")
                source = obs.get("source", "trigger")
                lines.append(f"- [{date}] ({source}) {note}")
            await self.write("memory/observations.md", "\n".join(lines),
                             summary="Accumulated observations")

        # Review log → memory/review-log.md
        review_log = memory.get("review_log", [])
        if review_log:
            lines = []
            for entry in review_log:
                date = entry.get("date", "")
                action = entry.get("action", "")
                note = entry.get("note", "")
                lines.append(f"- [{date}] ({action}) {note}")
            await self.write("memory/review-log.md", "\n".join(lines),
                             summary="Review pass history")

        # Goal → memory/goal.md
        goal = memory.get("goal")
        if goal:
            desc = goal.get("description", "")
            status = goal.get("status", "")
            milestones = goal.get("milestones", [])
            content = f"# Goal\n\n{desc}\n\n**Status:** {status}"
            if milestones:
                content += "\n\n## Milestones\n"
                for m in milestones:
                    content += f"- {m}\n"
            await self.write("memory/goal.md", content,
                             summary="Agent goal and milestones")

        # Created agents (coordinator dedup) → memory/created-agents.md
        created_agents = memory.get("created_agents", [])
        if created_agents:
            lines = []
            for cd in created_agents:
                date = cd.get("date", "")
                title = cd.get("title", "")
                key = cd.get("dedup_key", "none")
                lines.append(f"- [{date}] {title} (key: {key})")
            await self.write("memory/created-agents.md", "\n".join(lines),
                             summary="Coordinator dedup log")

        # Last generated at → memory/state.md (operational metadata)
        last_gen = memory.get("last_generated_at")
        if last_gen:
            await self.write("memory/state.md",
                             f"last_generated_at: {last_gen}",
                             summary="Operational state")

        logger.info(f"[WORKSPACE] Seeded workspace from DB columns: {self._slug}")

    # =========================================================================
    # Structured reads for execution pipeline
    # =========================================================================

    async def get_observations(self) -> list[dict]:
        """Read observations as structured list (for threshold counting)."""
        content = await self.read("memory/observations.md")
        if not content:
            return []
        entries = []
        for line in content.strip().split("\n"):
            line = line.strip()
            if line.startswith("- ["):
                # Parse: - [date] (source) note
                try:
                    rest = line[3:]  # after "- ["
                    date_end = rest.index("]")
                    date = rest[:date_end]
                    rest = rest[date_end + 1:].strip()
                    if rest.startswith("("):
                        src_end = rest.index(")")
                        source = rest[1:src_end]
                        note = rest[src_end + 1:].strip()
                    else:
                        source = "unknown"
                        note = rest
                    entries.append({"date": date, "source": source, "note": note})
                except (ValueError, IndexError):
                    entries.append({"date": "", "source": "", "note": line})
        return entries

    async def get_review_log(self) -> list[dict]:
        """Read review log as structured list."""
        content = await self.read("memory/review-log.md")
        if not content:
            return []
        entries = []
        for line in content.strip().split("\n"):
            line = line.strip()
            if line.startswith("- ["):
                try:
                    rest = line[3:]
                    date_end = rest.index("]")
                    date = rest[:date_end]
                    rest = rest[date_end + 1:].strip()
                    if rest.startswith("("):
                        src_end = rest.index(")")
                        action = rest[1:src_end]
                        note = rest[src_end + 1:].strip()
                    else:
                        action = "unknown"
                        note = rest
                    entries.append({"date": date, "action": action, "note": note})
                except (ValueError, IndexError):
                    entries.append({"date": "", "action": "", "note": line})
        return entries

    async def get_created_agents(self) -> list[dict]:
        """Read created agents dedup log (coordinator mode)."""
        content = await self.read("memory/created-agents.md")
        if not content:
            return []
        entries = []
        for line in content.strip().split("\n"):
            line = line.strip()
            if line.startswith("- ["):
                try:
                    rest = line[3:]
                    date_end = rest.index("]")
                    date = rest[:date_end]
                    rest = rest[date_end + 1:].strip()
                    # Parse: title (key: dedup_key)
                    if "(key:" in rest:
                        key_start = rest.index("(key:")
                        title = rest[:key_start].strip()
                        dedup_key = rest[key_start + 5:].rstrip(")").strip()
                    else:
                        title = rest
                        dedup_key = "none"
                    entries.append({"date": date, "title": title, "dedup_key": dedup_key})
                except (ValueError, IndexError):
                    entries.append({"date": "", "title": line, "dedup_key": "none"})
        return entries

    async def get_goal(self) -> Optional[dict]:
        """Read goal from memory/goal.md."""
        content = await self.read("memory/goal.md")
        if not content:
            return None
        # Parse simple structure
        desc = ""
        status = ""
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("# Goal"):
                continue
            elif line.startswith("**Status:**"):
                status = line.replace("**Status:**", "").strip()
            elif line and not line.startswith("##") and not line.startswith("-"):
                if not desc:
                    desc = line
        return {"description": desc, "status": status} if desc else None

    async def get_state(self, key: str) -> Optional[str]:
        """Read an operational state value from memory/state.md."""
        content = await self.read("memory/state.md")
        if not content:
            return None
        for line in content.strip().split("\n"):
            if line.startswith(f"{key}:"):
                return line[len(key) + 1:].strip()
        return None

    async def set_state(self, key: str, value: str) -> bool:
        """Set an operational state value in memory/state.md."""
        content = await self.read("memory/state.md") or ""
        lines = content.strip().split("\n") if content.strip() else []
        updated = False
        for i, line in enumerate(lines):
            if line.startswith(f"{key}:"):
                lines[i] = f"{key}: {value}"
                updated = True
                break
        if not updated:
            lines.append(f"{key}: {value}")
        return await self.write("memory/state.md", "\n".join(lines),
                                summary="Operational state")

    async def append_observation(self, note: str, source: str = "trigger") -> int:
        """Append observation and return new count."""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        entry = f"- [{timestamp}] ({source}) {note}"
        await self.append("memory/observations.md", entry)
        # Return count for threshold checking
        obs = await self.get_observations()
        return len(obs)

    async def clear_observations(self) -> bool:
        """Clear observations (after reactive threshold generation)."""
        return await self.write("memory/observations.md", "",
                                summary="Cleared after generation")

    async def append_review_log(self, entry: dict, max_entries: int = 50) -> bool:
        """Append to review log, capping at max_entries."""
        date = entry.get("date", "")
        action = entry.get("action", "")
        note = entry.get("note", "")
        next_review = entry.get("next_review_at", "")
        line = f"- [{date}] ({action}) {note}"
        if next_review:
            line += f" [next: {next_review}]"

        log = await self.get_review_log()
        if len(log) >= max_entries:
            # Rewrite with only recent entries + new one
            content = await self.read("memory/review-log.md") or ""
            lines = [l for l in content.strip().split("\n") if l.strip()]
            lines = lines[-(max_entries - 1):]  # Keep last N-1
            lines.append(line)
            return await self.write("memory/review-log.md", "\n".join(lines),
                                    summary="Review pass history")
        return await self.append("memory/review-log.md", line)

    async def append_created_agent(self, title: str, dedup_key: str) -> bool:
        """Append to coordinator created agents log."""
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        line = f"- [{date}] {title} (key: {dedup_key})"
        return await self.append("memory/created-agents.md", line)

    # =========================================================================
    # Convenience methods for common workspace patterns
    # =========================================================================

    async def load_context(self) -> str:
        """
        Load the agent's working context for generation.
        Returns a formatted string of AGENT.md + thesis + memory + working notes.
        """
        parts = []

        # AGENT.md first — identity and directives (like CLAUDE.md)
        agent_md = await self.read("AGENT.md")
        if agent_md:
            parts.append(f"## Agent Directives\n{agent_md}")

        thesis = await self.read("thesis.md")
        if thesis:
            parts.append(f"## Current Thesis\n{thesis}")

        # Load all memory files (topic-scoped, like Claude Code's memory/)
        memory_files = await self.list("memory/")
        for filename in memory_files:
            if filename.endswith("/"):
                continue
            content = await self.read(f"memory/{filename}")
            if content:
                # ADR-117: Window observations to last 10 entries to prevent token bloat.
                # Observations append forever; only recent entries are useful signal.
                if filename == "observations.md":
                    lines = content.strip().split("\n")
                    if len(lines) > 10:
                        content = "\n".join(lines[-10:])
                label = filename.replace(".md", "").replace("-", " ").title()
                parts.append(f"## Memory: {label}\n{content}")

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
        """Append an observation to memory/observations.md with timestamp."""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        entry = f"- [{timestamp}] ({source}) {note}"
        return await self.append("memory/observations.md", entry)

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
    Shared knowledge base: /knowledge/ (ADR-107)

    Agent-produced knowledge artifacts, organized by content class:
    - /knowledge/digests/     — platform-specific recaps
    - /knowledge/analyses/    — cross-platform synthesis
    - /knowledge/briefs/      — event-driven preparation
    - /knowledge/research/    — deep research outputs
    - /knowledge/insights/    — proactive findings

    Written by the delivery layer after successful agent generation.
    Read by agents via QueryKnowledge primitive.
    """

    # ADR-109: skill → content class directory
    CONTENT_CLASS_MAP = {
        "digest": "digests",
        "synthesize": "analyses",
        "prepare": "briefs",
        "research": "research",
        "monitor": "insights",
        "custom": "analyses",
        "orchestrate": "analyses",
    }

    def __init__(self, db_client, user_id: str):
        self._db = db_client
        self._user_id = user_id
        self._base = "/knowledge"

    @classmethod
    def get_knowledge_path(cls, skill: str, title: str, date_str: str = None) -> str:
        """
        Generate the /knowledge/ path for an agent output.

        Args:
            skill: The agent's skill (digest, synthesize, prepare, etc.)
            title: Agent title — will be slugified (e.g., "Slack Engineering Recap")
            date_str: Date string YYYY-MM-DD (defaults to today)
        """
        content_class = cls.CONTENT_CLASS_MAP.get(skill, "analyses")
        if date_str is None:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Slugify the title (same logic as get_agent_slug)
        slug = title.lower().strip()
        slug = re.sub(r"[^a-z0-9-]", "-", slug)
        slug = re.sub(r"-+", "-", slug).strip("-")
        slug = slug[:50]

        if content_class == "research":
            # Research uses subdirectory with latest.md
            return f"/knowledge/{content_class}/{slug}/latest.md"
        else:
            # All others use {slug}-{date}.md
            return f"/knowledge/{content_class}/{slug}-{date_str}.md"

    async def write(
        self,
        path: str,
        content: str,
        summary: str = None,
        metadata: dict = None,
        tags: list[str] = None,
    ) -> bool:
        """
        Write a knowledge artifact. Called by delivery layer after successful generation.

        ADR-107 Phase 2: Before overwriting an existing file, archives the current
        content as v{N}.md in the same directory. Sets metadata.supersedes on the
        new version pointing to the archived path.

        Args:
            path: Full path under /knowledge/ (use get_knowledge_path() to generate)
            content: The agent output content (markdown)
            summary: Brief description for discovery
            metadata: {agent_id, run_id, content_class, skill, version_number}
            tags: Searchable topic tags
        """
        if not path.startswith("/knowledge/"):
            path = f"{self._base}/{path}"
        try:
            # ADR-107 Phase 2: Archive existing content before overwrite
            await self._archive_if_exists(path)

            data = {
                "user_id": self._user_id,
                "path": path,
                "content": content,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            if summary is not None:
                data["summary"] = summary
            if metadata is not None:
                data["metadata"] = metadata
            if tags is not None:
                data["tags"] = tags

            self._db.table("workspace_files").upsert(
                data,
                on_conflict="user_id,path",
            ).execute()
            logger.info(f"[KNOWLEDGE] Written: {path}")
            return True
        except Exception as e:
            logger.error(f"[KNOWLEDGE] Write failed: {path}: {e}")
            return False

    async def _archive_if_exists(self, path: str) -> Optional[str]:
        """
        ADR-107 Phase 2: If a file exists at path, copy it to v{N}.md.

        Returns the archive path if archived, None otherwise.
        """
        try:
            result = (
                self._db.table("workspace_files")
                .select("content, summary, metadata, tags")
                .eq("user_id", self._user_id)
                .eq("path", path)
                .limit(1)
                .execute()
            )
            rows = result.data or []
            if not rows:
                return None

            existing = rows[0]

            # Determine next version number from sibling v*.md files
            dir_path = path.rsplit("/", 1)[0] if "/" in path else ""
            next_version = await self._next_version_number(dir_path, path)

            # Build archive path: same directory, v{N}.md
            filename = path.rsplit("/", 1)[-1] if "/" in path else path
            stem = filename.rsplit(".", 1)[0]  # e.g. "latest" or "weekly-slack-digest-2026-03-11"
            archive_path = f"{dir_path}/v{next_version}.md" if dir_path else f"v{next_version}.md"

            archive_metadata = dict(existing.get("metadata") or {})
            archive_metadata["archived_from"] = path
            archive_metadata["version_number"] = next_version

            self._db.table("workspace_files").insert({
                "user_id": self._user_id,
                "path": archive_path,
                "content": existing["content"],
                "summary": existing.get("summary") or "",
                "metadata": archive_metadata,
                "tags": existing.get("tags") or [],
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).execute()

            logger.info(f"[KNOWLEDGE] Archived {path} → {archive_path}")
            return archive_path
        except Exception as e:
            logger.warning(f"[KNOWLEDGE] Archive failed for {path}: {e}")
            return None

    def _version_prefix(self, dir_path: str) -> str:
        """Build a LIKE pattern matching only version archive files (v1.md, v2.md, etc.)."""
        return f"{dir_path}/v"

    async def _next_version_number(self, dir_path: str, canonical_path: str) -> int:
        """Count existing version archive files to determine next version number."""
        try:
            # Fetch all files in dir, filter to v{N}.md pattern in Python
            result = (
                self._db.table("workspace_files")
                .select("path")
                .eq("user_id", self._user_id)
                .like("path", f"{dir_path}/v%.md")
                .execute()
            )
            # Filter to only true version files: v{digits}.md
            count = sum(1 for r in (result.data or []) if self._is_version_file(r["path"]))
            return count + 1
        except Exception:
            return 1

    @staticmethod
    def _is_version_file(path: str) -> bool:
        """Check if a path is a version archive file (e.g. /knowledge/insights/v3.md)."""
        import re
        filename = path.rsplit("/", 1)[-1] if "/" in path else path
        return bool(re.match(r"^v\d+\.md$", filename))

    async def list_versions(self, path: str) -> list[dict]:
        """
        List version history for a knowledge file.

        For a file at /knowledge/research/topic/latest.md, returns all
        v{N}.md files in the same directory, sorted by version number desc.
        """
        if not path.startswith("/knowledge/"):
            path = f"{self._base}/{path}"

        dir_path = path.rsplit("/", 1)[0] if "/" in path else ""
        try:
            result = (
                self._db.table("workspace_files")
                .select("path, summary, metadata, updated_at")
                .eq("user_id", self._user_id)
                .like("path", f"{dir_path}/v%.md")
                .order("updated_at", desc=True)
                .execute()
            )
            # Filter to only true version files (v{digits}.md)
            return [r for r in (result.data or []) if self._is_version_file(r["path"])]
        except Exception as e:
            logger.warning(f"[KNOWLEDGE] List versions failed for {path}: {e}")
            return []

    async def search(self, query: str, content_class: str = None, limit: int = 20) -> list[SearchResult]:
        """Search the knowledge base. Optionally filter by content class directory."""
        prefix = f"{self._base}/{content_class}" if content_class else self._base
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

    async def search_by_metadata(
        self,
        query: str = None,
        content_class: str = None,
        agent_id: str = None,
        skill: str = None,
        limit: int = 10,
    ) -> list[SearchResult]:
        """ADR-116 Phase 1: Search knowledge base with metadata filters.

        Enables provenance-aware queries like "all digests from the Slack Recap agent"
        or "all research outputs" without relying on full-text content matching alone.
        """
        try:
            result = self._db.rpc("search_knowledge_by_metadata", {
                "p_user_id": self._user_id,
                "p_content_class": content_class,
                "p_agent_id": agent_id,
                "p_skill": skill,
                "p_query": query,
                "p_limit": limit,
            }).execute()

            return [
                SearchResult(
                    path=r["path"],
                    summary=r.get("summary"),
                    content=r["content"][:500] if r.get("content") else "",
                    rank=0,
                    updated_at=r.get("updated_at"),
                    metadata=r.get("metadata"),
                )
                for r in (result.data or [])
            ]
        except Exception as e:
            logger.warning(f"[KNOWLEDGE] Metadata search failed: {e}")
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
                .limit(1)
                .execute()
            )
            rows = result.data or []
            if rows:
                return rows[0]["content"]
            return None
        except Exception as e:
            logger.warning(f"[KNOWLEDGE] Read failed: {full_path}: {e}")
            return None

    async def list_classes(self) -> list[str]:
        """List content class directories in the knowledge base."""
        try:
            result = (
                self._db.table("workspace_files")
                .select("path")
                .eq("user_id", self._user_id)
                .like("path", f"{self._base}/%")
                .execute()
            )
            classes = set()
            for r in (result.data or []):
                parts = r["path"][len(self._base) + 1:].split("/")
                if parts:
                    classes.add(parts[0])
            return sorted(classes)
        except Exception as e:
            logger.warning(f"[KNOWLEDGE] List classes failed: {e}")
            return []

    async def count(self) -> int:
        """Count total knowledge artifacts."""
        try:
            result = (
                self._db.table("workspace_files")
                .select("id", count="exact")
                .eq("user_id", self._user_id)
                .like("path", f"{self._base}/%")
                .execute()
            )
            return result.count or 0
        except Exception as e:
            logger.warning(f"[KNOWLEDGE] Count failed: {e}")
            return 0

    async def list_files(self, content_class: str = None, limit: int = 20) -> list[dict]:
        """List knowledge files, optionally filtered by content class."""
        prefix = f"{self._base}/{content_class}" if content_class else self._base
        try:
            result = (
                self._db.table("workspace_files")
                .select("path, summary, metadata, updated_at")
                .eq("user_id", self._user_id)
                .like("path", f"{prefix}/%")
                .order("updated_at", desc=True)
                .limit(limit)
                .execute()
            )
            return result.data or []
        except Exception as e:
            logger.warning(f"[KNOWLEDGE] List files failed: {e}")
            return []


class UserMemory:
    """
    User-level memory: /memory/ (ADR-108)

    Global user identity, preferences, and accumulated notes.
    Three canonical files:
    - /memory/MEMORY.md     — identity (name, role, company, timezone, bio)
    - /memory/preferences.md — communication preferences (per-platform tone/verbosity, format prefs)
    - /memory/notes.md       — standing instructions, observed facts (accumulated by extraction cron)

    Replaces the user_memory key-value table. Analogous to /etc/ in Unix:
    stable configuration that every process reads.
    """

    def __init__(self, db_client, user_id: str):
        self._db = db_client
        self._user_id = user_id
        self._base = "/memory"

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

    async def write(self, filename: str, content: str, summary: str = None) -> bool:
        """Write a memory file (upsert). Returns True on success."""
        path = self._full_path(filename)
        try:
            data = {
                "user_id": self._user_id,
                "path": path,
                "content": content,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            if summary is not None:
                data["summary"] = summary
            self._db.table("workspace_files").upsert(
                data, on_conflict="user_id,path"
            ).execute()
            return True
        except Exception as e:
            logger.error(f"[USER_MEMORY] Write failed: {path}: {e}")
            return False

    async def read_all(self) -> dict[str, str]:
        """Read all three memory files. Returns {filename: content}."""
        files = {}
        for filename in ("MEMORY.md", "preferences.md", "notes.md"):
            content = await self.read(filename)
            if content:
                files[filename] = content
        return files

    def read_all_sync(self) -> dict[str, str]:
        """Synchronous read_all for thread pool use."""
        files = {}
        for filename in ("MEMORY.md", "preferences.md", "notes.md"):
            content = self.read_sync(filename)
            if content:
                files[filename] = content
        return files

    async def get_profile(self) -> dict:
        """Parse MEMORY.md into structured profile dict."""
        content = await self.read("MEMORY.md")
        return self._parse_memory_md(content)

    async def update_profile(self, updates: dict) -> bool:
        """Update profile fields in MEMORY.md (read-merge-write)."""
        current = await self.get_profile()
        current.update({k: v for k, v in updates.items() if v is not None})
        # Remove cleared fields
        for k, v in updates.items():
            if v is None or v == "":
                current.pop(k, None)
        return await self.write("MEMORY.md", self._render_memory_md(current),
                                summary="User identity and profile")

    async def get_preferences(self) -> dict:
        """Parse preferences.md into structured dict."""
        content = await self.read("preferences.md")
        return self._parse_preferences_md(content)

    async def update_preferences(self, platform: str, updates: dict) -> bool:
        """Update preferences for a platform (read-merge-write)."""
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
        return await self.write("preferences.md", self._render_preferences_md(prefs),
                                summary="Communication and content preferences")

    async def get_notes(self) -> list[dict]:
        """Parse notes.md into list of {type, content}."""
        content = await self.read("notes.md")
        return self._parse_notes_md(content)

    async def add_note(self, note_type: str, content: str) -> bool:
        """Append a note to notes.md."""
        notes = await self.get_notes()
        notes.append({"type": note_type, "content": content})
        return await self.write("notes.md", self._render_notes_md(notes),
                                summary="Standing instructions and observed facts")

    async def remove_note(self, content: str) -> bool:
        """Remove a note by content match."""
        notes = await self.get_notes()
        notes = [n for n in notes if n["content"] != content]
        return await self.write("notes.md", self._render_notes_md(notes),
                                summary="Standing instructions and observed facts")

    async def replace_notes(self, notes: list[dict]) -> bool:
        """Replace all notes (used by extraction cron read-merge-write)."""
        return await self.write("notes.md", self._render_notes_md(notes),
                                summary="Standing instructions and observed facts")

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
        """Parse preferences.md into {platform: {tone, verbosity}}."""
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
        """Render preferences dict as preferences.md content."""
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
    observations = await ws.get_observations()
    goal = await ws.get_goal()
    review_log = await ws.get_review_log()
    created_agents = await ws.get_created_agents()
    last_generated_at = await ws.get_state("last_generated_at")

    memory = {}
    if observations:
        memory["observations"] = observations
    if goal:
        memory["goal"] = goal
    if review_log:
        memory["review_log"] = review_log
    if created_agents:
        memory["created_agents"] = created_agents
    if last_generated_at:
        memory["last_generated_at"] = last_generated_at

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

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

    # ADR-119 Phase 3: Evolving files that get version history on overwrite.
    # Output folders version by date accumulation, not overwrite history.
    _EVOLVING_PATTERNS = {"AGENT.md", "thesis.md"}
    _EVOLVING_DIRS = {"memory/"}
    _MAX_HISTORY_VERSIONS = 5

    @staticmethod
    def _is_evolving_file(relative_path: str) -> bool:
        """ADR-119 Phase 3: Check if a file should get version history on overwrite."""
        filename = relative_path.rsplit("/", 1)[-1] if "/" in relative_path else relative_path
        if filename in AgentWorkspace._EVOLVING_PATTERNS:
            return True
        if any(relative_path.startswith(d) for d in AgentWorkspace._EVOLVING_DIRS):
            return True
        return False

    async def _archive_to_history(self, relative_path: str) -> Optional[str]:
        """ADR-119 Phase 3: Archive current content to /history/{filename}/v{N}.md before overwrite.

        Only called for evolving files. Capped at _MAX_HISTORY_VERSIONS — oldest
        versions are deleted when the cap is reached.

        Returns the history path if archived, None otherwise.
        """
        path = self._full_path(relative_path)
        try:
            result = (
                self._db.table("workspace_files")
                .select("content, summary, version")
                .eq("user_id", self._user_id)
                .eq("path", path)
                .limit(1)
                .execute()
            )
            rows = result.data or []
            if not rows or not rows[0].get("content"):
                return None

            existing = rows[0]
            current_version = existing.get("version", 1)

            # Build history path: /agents/{slug}/history/{filename}/v{N}.md
            filename = relative_path.rsplit("/", 1)[-1] if "/" in relative_path else relative_path
            history_path = self._full_path(f"history/{filename}/v{current_version}.md")

            self._db.table("workspace_files").insert({
                "user_id": self._user_id,
                "path": history_path,
                "content": existing["content"],
                "summary": existing.get("summary") or f"v{current_version} archive",
                "lifecycle": "archived",
                "metadata": {
                    "archived_from": path,
                    "version_number": current_version,
                },
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).execute()

            # Cap: delete oldest versions beyond limit
            await self._cap_history(f"history/{filename}/")

            logger.info(f"[WORKSPACE] ADR-119 P3: Archived {relative_path} v{current_version} → {history_path}")
            return history_path
        except Exception as e:
            logger.warning(f"[WORKSPACE] ADR-119 P3: Archive failed for {relative_path}: {e}")
            return None

    async def _cap_history(self, history_prefix: str) -> None:
        """Remove oldest history versions beyond _MAX_HISTORY_VERSIONS."""
        try:
            prefix = self._full_path(history_prefix)
            result = (
                self._db.table("workspace_files")
                .select("path, updated_at")
                .eq("user_id", self._user_id)
                .like("path", f"{prefix}%")
                .order("updated_at", desc=True)
                .execute()
            )
            versions = result.data or []
            if len(versions) > self._MAX_HISTORY_VERSIONS:
                for old in versions[self._MAX_HISTORY_VERSIONS:]:
                    self._db.table("workspace_files").delete().eq(
                        "user_id", self._user_id
                    ).eq("path", old["path"]).execute()
        except Exception:
            pass  # Non-fatal — cap is best-effort

    async def list_history(self, relative_path: str) -> list[dict]:
        """ADR-119 Phase 3: List version history for an evolving file.

        Returns list of {path, version_number, updated_at} sorted newest first.
        """
        filename = relative_path.rsplit("/", 1)[-1] if "/" in relative_path else relative_path
        prefix = self._full_path(f"history/{filename}/")
        try:
            result = (
                self._db.table("workspace_files")
                .select("path, metadata, updated_at")
                .eq("user_id", self._user_id)
                .like("path", f"{prefix}%")
                .eq("lifecycle", "archived")
                .order("updated_at", desc=True)
                .execute()
            )
            return [
                {
                    "path": r["path"],
                    "version_number": (r.get("metadata") or {}).get("version_number", 0),
                    "updated_at": r.get("updated_at"),
                }
                for r in (result.data or [])
            ]
        except Exception as e:
            logger.warning(f"[WORKSPACE] List history failed for {relative_path}: {e}")
            return []

    async def write(self, relative_path: str, content: str, summary: str = None,
                    tags: list[str] = None, lifecycle: str = None,
                    content_type: str = None, content_url: str = None,
                    metadata: dict = None) -> bool:
        """Write a file (upsert). Returns True on success.

        ADR-119: lifecycle auto-inferred from path (/working/ → ephemeral).
        Can be overridden via lifecycle parameter.
        ADR-119 Phase 3: Evolving files (AGENT.md, thesis.md, memory/*) get
        version history archived to /history/ before overwrite.
        """
        # ADR-119 Phase 3: Archive evolving files before overwrite
        if self._is_evolving_file(relative_path):
            await self._archive_to_history(relative_path)

        path = self._full_path(relative_path)
        try:
            # Read current version to increment
            current_version = 1
            if self._is_evolving_file(relative_path):
                try:
                    ver_result = (
                        self._db.table("workspace_files")
                        .select("version")
                        .eq("user_id", self._user_id)
                        .eq("path", path)
                        .limit(1)
                        .execute()
                    )
                    if ver_result.data:
                        current_version = (ver_result.data[0].get("version") or 1) + 1
                except Exception:
                    pass

            data = {
                "user_id": self._user_id,
                "path": path,
                "content": content,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "lifecycle": lifecycle or self._infer_lifecycle(path),
                "version": current_version,
            }
            if summary is not None:
                data["summary"] = summary
            if tags is not None:
                data["tags"] = tags
            if content_type is not None:
                data["content_type"] = content_type
            if content_url is not None:
                data["content_url"] = content_url
            if metadata is not None:
                data["metadata"] = metadata

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
        """ADR-143: Redirect observations to feedback.md.

        Preserves the API so existing callers (trigger_dispatch, edit primitive) don't break.
        Returns 0 (count no longer meaningful).
        """
        import re as _re
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
        new_entry = f"## Observation ({timestamp}, {source})\n- {note}\n"

        existing = await self.read("memory/feedback.md") or ""
        header = "# Feedback History\n<!-- Most recent first. Max 10 entries. TP writes, agent reads. -->\n\n"
        entries = _re.split(r"(?=^## )", existing, flags=_re.MULTILINE)
        entries = [e.strip() for e in entries if e.strip() and e.strip().startswith("## ")]
        entries = [new_entry.strip()] + entries[:9]
        content = header + "\n\n".join(entries) + "\n"
        await self.write("memory/feedback.md", content, summary="ADR-143: observation → feedback")
        return 0

    async def clear_observations(self) -> bool:
        """ADR-143: No-op. Observations now part of feedback.md (capped, self-cleaning)."""
        return True

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
                # ADR-143: Label files by type for clear context injection
                base = filename.replace(".md", "")
                if base.startswith("methodology-"):
                    topic = base.replace("methodology-", "").replace("-", " ").title()
                    label = f"Methodology: {topic}"
                elif base == "feedback":
                    label = "Feedback History"
                elif base == "self-assessment" or base == "self_assessment":
                    label = "Self-Assessment"
                else:
                    label = f"Memory: {base.replace('-', ' ').title()}"
                parts.append(f"## {label}\n{content}")

        # Load recent working notes
        working = await self.list("working/")
        for filename in working[-3:]:  # Last 3 working notes
            if filename.endswith("/"):
                continue
            note = await self.read(f"working/{filename}")
            if note:
                parts.append(f"## Working Note: {filename}\n{note}")

        # ADR-119 Phase 2: Inject project context for contributing agents.
        # If memory/projects.json exists, load each project's intent + preferences.
        # ADR-121: Also inject PM contribution briefs as steering directives.
        projects_json = await self.read("memory/projects.json")
        if projects_json:
            import json as _json
            try:
                projects_list = _json.loads(projects_json)
                for proj in projects_list:
                    slug = proj.get("project_slug", "")
                    if not slug:
                        continue
                    pw = ProjectWorkspace(self._db, self._user_id, slug)
                    project_ctx = await pw.load_context()
                    if project_ctx:
                        expected = proj.get("expected_contribution", "")
                        header = f"## Contributing To: {proj.get('title', slug)}"
                        if expected:
                            header += f"\n**Your expected contribution:** {expected}"
                        # ADR-121: Read PM brief if it exists — steering directive
                        brief = await pw.read_brief(self._slug) if self._slug else None
                        if brief:
                            header += f"\n\n**PM Directive (brief):**\n{brief}"
                        # ADR-128 Phase 4: Read PM's project assessment
                        try:
                            pm_assessment = await pw.read("memory/project_assessment.md")
                            if pm_assessment and "No assessment yet" not in pm_assessment:
                                header += f"\n\n**Project Assessment (from PM):**\n{pm_assessment[:500]}"
                        except Exception:
                            pass
                        parts.append(f"{header}\n{project_ctx}")
            except _json.JSONDecodeError:
                pass

        return "\n\n---\n\n".join(parts) if parts else ""

    async def record_observation(self, note: str, source: str = "review") -> bool:
        """ADR-143: Redirect to append_observation → feedback.md."""
        await self.append_observation(note, source=source)
        return True

    async def update_thesis(self, thesis: str) -> bool:
        """Update the agent's thesis (full replacement)."""
        return await self.write(
            "thesis.md",
            thesis,
            summary="Agent's current domain understanding",
        )

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

    # ADR-109: role → content class directory
    CONTENT_CLASS_MAP = {
        "digest": "digests",
        "synthesize": "analyses",
        "prepare": "briefs",
        "research": "research",
        "monitor": "insights",
        "custom": "analyses",
    }

    def __init__(self, db_client, user_id: str):
        self._db = db_client
        self._user_id = user_id
        self._base = "/knowledge"

    @classmethod
    def get_knowledge_path(cls, role: str, title: str, date_str: str = None) -> str:
        """
        Generate the /knowledge/ path for an agent output.

        Args:
            role: The agent's role (digest, synthesize, prepare, etc.)
            title: Agent title — will be slugified (e.g., "Slack Engineering Recap")
            date_str: Date string YYYY-MM-DD (defaults to today)
        """
        content_class = cls.CONTENT_CLASS_MAP.get(role, "analyses")
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
            metadata: {agent_id, run_id, content_class, role, version_number}
            tags: Searchable topic tags
        """
        if not path.startswith("/knowledge/"):
            path = f"{self._base}/{path}"
        try:
            # ADR-119 Phase 3: Archive existing content to /history/ before overwrite
            await self._archive_to_history(path)

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

    _MAX_HISTORY_VERSIONS = 5

    async def _archive_to_history(self, path: str) -> Optional[str]:
        """ADR-119 Phase 3: Archive current content to /history/{filename}/v{N}.md.

        Replaces legacy v{N}.md-in-same-directory pattern.
        Capped at _MAX_HISTORY_VERSIONS.
        """
        try:
            result = (
                self._db.table("workspace_files")
                .select("content, summary, version")
                .eq("user_id", self._user_id)
                .eq("path", path)
                .limit(1)
                .execute()
            )
            rows = result.data or []
            if not rows or not rows[0].get("content"):
                return None

            existing = rows[0]
            current_version = existing.get("version", 1)

            # Build history path: /knowledge/history/{filename}/v{N}.md
            filename = path.rsplit("/", 1)[-1] if "/" in path else path
            history_path = f"{self._base}/history/{filename}/v{current_version}.md"

            self._db.table("workspace_files").insert({
                "user_id": self._user_id,
                "path": history_path,
                "content": existing["content"],
                "summary": existing.get("summary") or f"v{current_version} archive",
                "lifecycle": "archived",
                "metadata": {
                    "archived_from": path,
                    "version_number": current_version,
                },
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }).execute()

            # Cap oldest versions
            prefix = f"{self._base}/history/{filename}/"
            try:
                cap_result = (
                    self._db.table("workspace_files")
                    .select("path, updated_at")
                    .eq("user_id", self._user_id)
                    .like("path", f"{prefix}%")
                    .order("updated_at", desc=True)
                    .execute()
                )
                versions = cap_result.data or []
                if len(versions) > self._MAX_HISTORY_VERSIONS:
                    for old in versions[self._MAX_HISTORY_VERSIONS:]:
                        self._db.table("workspace_files").delete().eq(
                            "user_id", self._user_id
                        ).eq("path", old["path"]).execute()
            except Exception:
                pass

            logger.info(f"[KNOWLEDGE] ADR-119 P3: Archived {path} v{current_version}")
            return history_path
        except Exception as e:
            logger.warning(f"[KNOWLEDGE] ADR-119 P3: Archive failed for {path}: {e}")
            return None

    async def list_history(self, path: str) -> list[dict]:
        """ADR-119 Phase 3: List version history for a knowledge file.

        Returns list of {path, version_number, updated_at} sorted newest first.
        """
        if not path.startswith("/knowledge/"):
            path = f"{self._base}/{path}"
        filename = path.rsplit("/", 1)[-1] if "/" in path else path
        prefix = f"{self._base}/history/{filename}/"
        try:
            result = (
                self._db.table("workspace_files")
                .select("path, metadata, updated_at")
                .eq("user_id", self._user_id)
                .like("path", f"{prefix}%")
                .eq("lifecycle", "archived")
                .order("updated_at", desc=True)
                .execute()
            )
            return [
                {
                    "path": r["path"],
                    "version_number": (r.get("metadata") or {}).get("version_number", 0),
                    "updated_at": r.get("updated_at"),
                }
                for r in (result.data or [])
            ]
        except Exception as e:
            logger.warning(f"[KNOWLEDGE] List history failed: {e}")
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
        role: str = None,
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
                "p_role": role,
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
    User workspace context: /workspace/ (ADR-133)

    Two canonical files at workspace scope:
    - /workspace/IDENTITY.md — who you are (name, role, company, industry, timezone, summary)
    - /workspace/BRAND.md    — how outputs look and sound (colors, typography, tone, voice)

    TP-accumulated knowledge stays at /memory/:
    - /memory/notes.md       — standing instructions, observed facts (extracted nightly)

    Seeded into projects at scaffold time → agents read project-level copies.
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
        """Read workspace context files. Returns {filename: content}.

        ADR-133: IDENTITY.md + BRAND.md from /workspace/.
        Also reads notes.md from /memory/ (TP-accumulated knowledge, separate path).
        Returns legacy key 'MEMORY.md' mapped from IDENTITY.md for backward compat.
        """
        files = {}
        for filename in ("IDENTITY.md", "BRAND.md"):
            content = await self.read(filename)
            if content:
                # Map IDENTITY.md → MEMORY.md key for backward compat with working memory parser
                key = "MEMORY.md" if filename == "IDENTITY.md" else filename
                files[key] = content
        # Notes stay at /memory/ — read directly
        try:
            result = (
                self._db.table("workspace_files")
                .select("content")
                .eq("user_id", self._user_id)
                .eq("path", "/memory/notes.md")
                .limit(1)
                .execute()
            )
            rows = result.data or []
            if rows and rows[0].get("content"):
                files["notes.md"] = rows[0]["content"]
        except Exception:
            pass
        return files

    def read_all_sync(self) -> dict[str, str]:
        """Synchronous read_all for thread pool use."""
        files = {}
        for filename in ("IDENTITY.md", "BRAND.md"):
            content = self.read_sync(filename)
            if content:
                key = "MEMORY.md" if filename == "IDENTITY.md" else filename
                files[key] = content
        try:
            result = (
                self._db.table("workspace_files")
                .select("content")
                .eq("user_id", self._user_id)
                .eq("path", "/memory/notes.md")
                .limit(1)
                .execute()
            )
            rows = result.data or []
            if rows and rows[0].get("content"):
                files["notes.md"] = rows[0]["content"]
        except Exception:
            pass
        return files

    async def get_profile(self) -> dict:
        """Parse IDENTITY.md into structured profile dict."""
        content = await self.read("IDENTITY.md")
        return self._parse_memory_md(content)

    async def update_profile(self, updates: dict) -> bool:
        """Update profile fields in IDENTITY.md (read-merge-write)."""
        current = await self.get_profile()
        current.update({k: v for k, v in updates.items() if v is not None})
        # Remove cleared fields
        for k, v in updates.items():
            if v is None or v == "":
                current.pop(k, None)
        return await self.write("IDENTITY.md", self._render_memory_md(current),
                                summary="User identity")

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
    goal = await ws.get_goal()
    created_agents = await ws.get_created_agents()
    last_generated_at = await ws.get_state("last_generated_at")
    # ADR-143: Unified feedback file
    feedback = (await ws.read("memory/feedback.md") or "").strip()
    self_assessment = (await ws.read("memory/self_assessment.md") or "").strip()

    memory = {}
    if goal:
        memory["goal"] = goal
    if created_agents:
        memory["created_agents"] = created_agents
    if last_generated_at:
        memory["last_generated_at"] = last_generated_at
    if feedback:
        memory["feedback"] = feedback
    if self_assessment:
        memory["self_assessment"] = self_assessment

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

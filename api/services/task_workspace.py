"""
Task Workspace — workspace abstraction for tasks.

Thin wrapper over `workspace_files` table, scoped to /tasks/{slug}/.
Follows the same patterns as AgentWorkspace (ADR-106).
"""

from __future__ import annotations

import json as _json
import logging
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


class TaskWorkspace:
    """
    Workspace scoped to a single task: /tasks/{slug}/

    Provides read/write access to task files:
    TASK.md, memory/, outputs/.
    """

    def __init__(self, db_client, user_id: str, task_slug: str):
        self._db = db_client
        self._user_id = user_id
        self._slug = task_slug
        self._base = f"/tasks/{task_slug}"

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
            logger.warning(f"[TASK_WORKSPACE] Read failed: {path}: {e}")
            return None

    async def write(
        self,
        relative_path: str,
        content: str,
        summary: Optional[str] = None,
        tags: Optional[list] = None,
        lifecycle: Optional[str] = None,
        metadata: Optional[dict] = None,
        *,
        authored_by: Optional[str] = None,
        message: Optional[str] = None,
    ) -> bool:
        """Write a file through the Authored Substrate (ADR-209).

        Routes through services.authored_substrate.write_revision() — every
        write lands a revision with authored_by + message attribution.

        Default `authored_by`: f"task:{self._slug}". Pipeline + agent writes
        that represent a specific agent's work (e.g., save_output) override
        with `agent:<slug>`.
        """
        from services.authored_substrate import write_revision

        path = self._full_path(relative_path)
        resolved_author = authored_by or f"task:{self._slug}"
        resolved_message = message or f"write {relative_path}"
        resolved_lifecycle = lifecycle or "active"

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
                metadata=metadata,
            )
            return True
        except Exception as e:
            logger.error(f"[TASK_WORKSPACE] Write failed: {path}: {e}")
            return False

    async def list(self, prefix: str = "") -> list:
        """List files under prefix. Returns relative paths."""
        full_prefix = self._full_path(prefix)
        if not full_prefix.endswith("/"):
            full_prefix += "/"
        try:
            result = (
                self._db.table("workspace_files")
                .select("path")
                .eq("user_id", self._user_id)
                .like("path", f"{full_prefix}%")
                .in_("lifecycle", ["active", "delivered"])
                .order("path")
                .execute()
            )
            return [r["path"][len(full_prefix):] for r in (result.data or [])]
        except Exception as e:
            logger.warning(f"[TASK_WORKSPACE] List failed: {full_prefix}: {e}")
            return []

    async def exists(self, relative_path: str) -> bool:
        """Check if a file exists."""
        path = self._full_path(relative_path)
        try:
            result = (
                self._db.table("workspace_files")
                .select("path")
                .eq("user_id", self._user_id)
                .eq("path", path)
                .limit(1)
                .execute()
            )
            return bool(result.data)
        except Exception:
            return False

    async def save_output(self, content: str, agent_slug: str,
                          manifest_data: Optional[dict] = None,
                          date_folder: Optional[str] = None) -> Optional[str]:
        """Save output to /outputs/{date}/output.md + manifest.json.

        Args:
            content: The text output (markdown).
            agent_slug: The agent that produced this output.
            manifest_data: Optional extra fields to include in manifest.
            date_folder: Optional explicit date folder name. If not provided,
                         generated from current time. Pipeline callers should pass
                         their own date_folder to co-locate with step outputs.

        Returns:
            The output folder path (e.g., "outputs/2026-03-25T1400/"), or None on failure.
        """
        now = datetime.now(timezone.utc)
        if not date_folder:
            date_folder = now.strftime("%Y-%m-%dT%H00")
        folder_path = f"outputs/{date_folder}"

        # 1. Write the text output (attributed to the agent that produced it)
        author = f"agent:{agent_slug}"
        text_ok = await self.write(
            f"{folder_path}/output.md",
            content,
            summary=f"Task output by {agent_slug}",
            tags=["output", agent_slug],
            authored_by=author,
            message=f"produce output.md for task {self._slug}",
        )
        if not text_ok:
            return None

        # 2. Build and write manifest
        manifest = {
            "agent_slug": agent_slug,
            "created_at": now.isoformat(),
            "status": "active",
            "files": [
                {"path": "output.md", "type": "text/markdown", "role": "primary"},
            ],
        }
        if manifest_data:
            manifest.update(manifest_data)

        await self.write(
            f"{folder_path}/manifest.json",
            _json.dumps(manifest, indent=2),
            summary=f"Output manifest — {agent_slug}",
            tags=["manifest"],
            authored_by=author,
            message=f"produce manifest.json for task {self._slug}",
        )

        logger.info(f"[TASK_WORKSPACE] Saved output: {self._slug}/{folder_path}")
        return folder_path

    async def append_run_log(
        self, entry: str, *, authored_by: str = "system:task-pipeline"
    ) -> bool:
        """Append an entry to memory/_run_log.md.

        Each entry is a line with date, outcome, observations. Defaults to
        `system:task-pipeline` attribution since the run log is the
        pipeline's own record of its execution; callers can override with
        `agent:<slug>` when an agent is appending context.
        """
        existing = await self.read("memory/_run_log.md")
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        line = f"- [{now}] {entry}"
        if existing:
            content = existing + "\n" + line
        else:
            content = f"# Run Log\n\n{line}"
        return await self.write(
            "memory/_run_log.md",
            content,
            summary="Task run history",
            authored_by=authored_by,
            message="append run log entry",
        )

    async def read_task(self) -> Optional[str]:
        """Read and return TASK.md content."""
        return await self.read("TASK.md")

    async def get_latest_output(self) -> Optional[str]:
        """Find most recent output folder, return output.md content.

        Scans /outputs/ for date-stamped folders, picks the latest by path
        (lexicographic sort = chronological for ISO date folders).
        """
        try:
            prefix = self._full_path("outputs/")
            result = (
                self._db.table("workspace_files")
                .select("path, content")
                .eq("user_id", self._user_id)
                .like("path", f"{prefix}%/output.md")
                .in_("lifecycle", ["active", "delivered"])
                .order("path", desc=True)
                .limit(1)
                .execute()
            )
            rows = result.data or []
            if rows:
                return rows[0]["content"]
            return None
        except Exception as e:
            logger.warning(f"[TASK_WORKSPACE] get_latest_output failed: {self._slug}: {e}")
            return None

    async def get_prior_state_brief(self, max_output_chars: int = 2000) -> str:
        """Build a compact prior-state brief for accumulation-first prompt injection.

        ADR-173 Phase 2+3: Reads outputs/latest/ manifest + file list + sys_manifest.json
        generation_gaps to tell the agent what was produced and what was pending from
        the prior run. Keeps the brief under ~800 tokens.

        Returns empty string if no prior output exists (first run — graceful degradation).
        """
        try:
            # Read the simple manifest from outputs/latest/
            manifest_content = await self.read("outputs/latest/manifest.json")
            if not manifest_content:
                return ""

            manifest = _json.loads(manifest_content)
            created_at = manifest.get("created_at", "unknown")
            agent_slug = manifest.get("agent_slug", "agent")

            # List all files in outputs/latest/ to discover assets
            latest_files = await self.list("outputs/latest/")

            # Separate content files from assets
            asset_files = [f for f in latest_files if not f.endswith(("output.md", "manifest.json", "sys_manifest.json", "awareness.md"))]
            has_hero = any(f.startswith("hero.") for f in asset_files)
            has_charts = [f for f in asset_files if any(f.endswith(ext) for ext in (".png", ".svg")) and not f.startswith("hero.")]

            # Build compact brief (target: ~300-600 tokens)
            lines = [f"## Prior Run State (last output: {created_at[:10] if len(created_at) >= 10 else created_at})"]
            lines.append(f"Agent: {agent_slug} | Files: {len(latest_files)}")

            if has_hero:
                lines.append("- Hero image: EXISTS at outputs/latest/ — reuse, do not regenerate")
            if has_charts:
                lines.append(f"- Charts/assets: {len(has_charts)} file(s) at outputs/latest/ — reuse unless source data changed")

            # ADR-173 Phase 3: read generation_gaps from sys_manifest.json (if present)
            # This is the forward-looking handoff from the prior run:
            # what was skipped, what was missing, what needs attention this cycle.
            sys_manifest_content = await self.read("outputs/latest/sys_manifest.json")
            if sys_manifest_content:
                try:
                    sys_manifest = _json.loads(sys_manifest_content)
                    generation_gaps = sys_manifest.get("generation_gaps", {})
                    if generation_gaps:
                        pending = [k for k, v in generation_gaps.items() if v.startswith("missing:")]
                        skipped = [k for k, v in generation_gaps.items() if v.startswith("skipped:")]
                        if pending:
                            lines.append(f"- Pending from prior run (produce these): {', '.join(pending)}")
                        if skipped:
                            lines.append(f"- Current from prior run (reuse/skip unless stale): {', '.join(skipped)}")
                except Exception:
                    pass  # sys_manifest parse failure is non-fatal

            # Include a short excerpt of prior output for recurring/reactive context
            prior_output_content = await self.read("outputs/latest/output.md")
            if prior_output_content:
                excerpt = prior_output_content[:max_output_chars]
                if len(prior_output_content) > max_output_chars:
                    excerpt += "\n[... truncated — full prior output available at outputs/latest/output.md ...]"
                lines.append(f"\n### Prior Output Excerpt\n{excerpt}")

            return "\n".join(lines)

        except Exception as e:
            logger.debug(f"[TASK_WORKSPACE] get_prior_state_brief failed (non-fatal): {self._slug}: {e}")
            return ""

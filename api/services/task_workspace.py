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

    async def write(self, relative_path: str, content: str,
                    summary: Optional[str] = None,
                    tags: Optional[list] = None,
                    lifecycle: Optional[str] = None,
                    metadata: Optional[dict] = None) -> bool:
        """Write a file (upsert). Returns True on success."""
        path = self._full_path(relative_path)
        try:
            data = {
                "user_id": self._user_id,
                "path": path,
                "content": content,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "lifecycle": lifecycle or "active",
            }
            if summary is not None:
                data["summary"] = summary
            if tags is not None:
                data["tags"] = tags
            if metadata is not None:
                data["metadata"] = metadata

            self._db.table("workspace_files").upsert(
                data,
                on_conflict="user_id,path",
            ).execute()
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

        # 1. Write the text output
        text_ok = await self.write(
            f"{folder_path}/output.md",
            content,
            summary=f"Task output by {agent_slug}",
            tags=["output", agent_slug],
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
        )

        logger.info(f"[TASK_WORKSPACE] Saved output: {self._slug}/{folder_path}")
        return folder_path

    async def append_run_log(self, entry: str) -> bool:
        """Append an entry to memory/_run_log.md.

        Each entry is a line with date, outcome, observations.
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

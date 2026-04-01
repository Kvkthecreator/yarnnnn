"""
Workspace Initialization — ADR-152: Full Workspace Bootstrap

Sets up a complete workspace from the three registries. Called once at signup.
After initialization, the workspace is self-contained — registries are templates
that were applied, the workspace filesystem is the sole source of truth.

Like provisioning a new employee's computer:
  1. Install the OS → directory structure from WORKSPACE_DIRECTORIES
  2. Set up the tools → agents from AGENT_TYPES + DEFAULT_ROSTER
  3. Configure defaults → IDENTITY.md, BRAND.md, playbook, preferences
  4. Create the manifest → WORKSPACE.md snapshot of what was initialized

After init, TP and agents evolve the workspace independently.
The registries are NEVER consulted at runtime — only at creation time.

Version: 1.0 (2026-03-31)
"""

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


async def initialize_workspace(client: Any, user_id: str) -> dict:
    """Initialize a complete workspace for a new user.

    Idempotent — checks for existing workspace before creating.
    Called from onboarding-state endpoint on first login.

    Returns dict with initialization summary.
    """
    result = {
        "agents_created": [],
        "directories_scaffolded": [],
        "workspace_files_seeded": [],
        "already_initialized": False,
    }

    # Check if already initialized
    from services.workspace import UserMemory
    um = UserMemory(client, user_id)
    existing_manifest = await um.read("WORKSPACE.md")
    if existing_manifest:
        result["already_initialized"] = True
        # Still run idempotent steps in case of partial init
        logger.info(f"[WORKSPACE_INIT] Workspace already initialized for {user_id[:8]}")

    # =========================================================================
    # Phase 1: Directory Structure (from WORKSPACE_DIRECTORIES)
    # =========================================================================
    try:
        from services.directory_registry import scaffold_all_directories
        scaffolded = await scaffold_all_directories(client, user_id)
        result["directories_scaffolded"] = scaffolded
        if scaffolded:
            logger.info(f"[WORKSPACE_INIT] Directories: {', '.join(scaffolded)}")
    except Exception as e:
        logger.warning(f"[WORKSPACE_INIT] Directory scaffold failed: {e}")

    # =========================================================================
    # Phase 2: Agent Roster (from AGENT_TYPES + DEFAULT_ROSTER)
    # =========================================================================
    try:
        from services.agent_framework import AGENT_TYPES, DEFAULT_ROSTER
        from services.agent_creation import create_agent_record

        for agent_def in DEFAULT_ROSTER:
            try:
                type_def = AGENT_TYPES.get(agent_def["role"], {})
                await create_agent_record(
                    client=client,
                    user_id=user_id,
                    title=agent_def["title"],
                    role=agent_def["role"],
                    origin="system_bootstrap",
                    agent_instructions=type_def.get("default_instructions", ""),
                )
                result["agents_created"].append(agent_def["title"])
                logger.info(f"[WORKSPACE_INIT] Agent: {agent_def['title']}")
            except Exception as e:
                logger.warning(f"[WORKSPACE_INIT] Agent {agent_def['title']} failed (may exist): {e}")
    except Exception as e:
        logger.warning(f"[WORKSPACE_INIT] Agent roster failed: {e}")

    # =========================================================================
    # Phase 3: Workspace Files (identity, brand, playbook, preferences)
    # =========================================================================
    try:
        from services.agent_framework import (
            TP_ORCHESTRATION_PLAYBOOK,
            DEFAULT_IDENTITY_MD,
            DEFAULT_BRAND_MD,
            DEFAULT_AWARENESS_MD,
        )

        workspace_files = {
            "IDENTITY.md": (DEFAULT_IDENTITY_MD, "User identity template"),
            "BRAND.md": (DEFAULT_BRAND_MD, "Default brand baseline"),
            "AWARENESS.md": (DEFAULT_AWARENESS_MD, "TP situational awareness"),
            "playbook-orchestration.md": (TP_ORCHESTRATION_PLAYBOOK, "TP orchestration playbook"),
            "preferences.md": ("# Preferences\n<!-- Learned from user feedback. -->\n", "Preferences placeholder"),
            "notes.md": ("# Notes\n<!-- TP-extracted facts and instructions. -->\n", "Notes placeholder"),
        }

        for filename, (content, summary) in workspace_files.items():
            existing = await um.read(filename)
            if not existing:
                await um.write(filename, content, summary=f"Workspace init: {summary}")
                result["workspace_files_seeded"].append(filename)
                logger.info(f"[WORKSPACE_INIT] File: {filename}")
    except Exception as e:
        logger.warning(f"[WORKSPACE_INIT] Workspace files failed: {e}")

    # =========================================================================
    # Phase 4: Workspace Manifest (WORKSPACE.md — initialization snapshot)
    # =========================================================================
    if not existing_manifest:
        try:
            now = datetime.now(timezone.utc)
            manifest = _build_workspace_manifest(result, now)
            await um.write("WORKSPACE.md", manifest, summary="Workspace initialization manifest")
            result["workspace_files_seeded"].append("WORKSPACE.md")
            logger.info(f"[WORKSPACE_INIT] Manifest written for {user_id[:8]}")
        except Exception as e:
            logger.warning(f"[WORKSPACE_INIT] Manifest write failed: {e}")

    logger.info(
        f"[WORKSPACE_INIT] Complete for {user_id[:8]}: "
        f"{len(result['agents_created'])} agents, "
        f"{len(result['directories_scaffolded'])} directories, "
        f"{len(result['workspace_files_seeded'])} files"
    )

    return result


async def update_workspace_manifest(client: Any, user_id: str) -> bool:
    """Update WORKSPACE.md with current workspace state.

    Called after agent/domain/task creation to keep manifest current.
    TP reads WORKSPACE.md at session start for meta-awareness.

    Returns True on success.
    """
    from services.workspace import UserMemory

    um = UserMemory(client, user_id)
    now = datetime.now(timezone.utc)

    try:
        # Query actual workspace state (not registry defaults)
        agents_result = (
            client.table("agents")
            .select("title, role, status, slug")
            .eq("user_id", user_id)
            .neq("status", "archived")
            .order("created_at")
            .execute()
        )
        agents = agents_result.data or []

        tasks_result = (
            client.table("tasks")
            .select("slug, mode, status, schedule")
            .eq("user_id", user_id)
            .neq("status", "archived")
            .order("created_at")
            .execute()
        )
        tasks = tasks_result.data or []

        # Build agent table with domain assignments
        from services.agent_framework import get_agent_domain
        agent_lines = []
        for a in agents:
            domain = get_agent_domain(a.get("role", ""))
            domain_str = f"`{domain}/`" if domain else "(cross-domain)" if a.get("role") == "executive" else "(platform)"
            agent_lines.append(f"| {a['title']} | {a.get('role', '?')} | {domain_str} | {a['status']} |")

        # Build task table
        task_lines = []
        for t in tasks:
            task_lines.append(f"| {t['slug']} | {t.get('mode', '?')} | {t.get('schedule', 'on-demand')} | {t['status']} |")

        # Count context domain files
        from services.directory_registry import CONTEXT_DOMAINS, get_directory_path
        domain_lines = []
        for domain_key in CONTEXT_DOMAINS:
            path = get_directory_path(domain_key)
            if path:
                prefix = f"/workspace/{path}/"
                try:
                    count_result = (
                        client.table("workspace_files")
                        .select("id", count="exact")
                        .eq("user_id", user_id)
                        .like("path", f"{prefix}%")
                        .execute()
                    )
                    file_count = count_result.count or 0
                except Exception:
                    file_count = 0
                domain_lines.append(f"| {domain_key} | {file_count} files |")

        manifest = f"""# Workspace

Last updated: {now.strftime('%Y-%m-%d %H:%M UTC')}

## Agents ({len(agents)})

| Agent | Role | Domain | Status |
|---|---|---|---|
{chr(10).join(agent_lines) if agent_lines else "| (none) | | | |"}

## Tasks ({len(tasks)})

| Task | Mode | Schedule | Status |
|---|---|---|---|
{chr(10).join(task_lines) if task_lines else "| (none) | | | |"}

## Context Domains

| Domain | Content |
|---|---|
{chr(10).join(domain_lines) if domain_lines else "| (none) | |"}

---
*This manifest reflects current workspace state. Updated on agent/domain/task creation.*
"""

        await um.write("WORKSPACE.md", manifest, summary="Workspace manifest updated")
        return True

    except Exception as e:
        logger.warning(f"[WORKSPACE_INIT] Manifest update failed: {e}")
        return False


def _build_workspace_manifest(init_result: dict, timestamp: datetime) -> str:
    """Build initial WORKSPACE.md at workspace creation time."""
    from services.directory_registry import WORKSPACE_DIRECTORIES
    from services.agent_framework import DEFAULT_ROSTER, get_agent_domain

    agent_lines = []
    for a in DEFAULT_ROSTER:
        domain = get_agent_domain(a['role'])
        domain_str = f"`{domain}/`" if domain else "(cross-domain)" if a['role'] == 'executive' else "(platform)"
        agent_lines.append(f"| {a['title']} | {a['role']} | {domain_str} | active |")

    context_domains = [
        f"| {k} | 0 files |"
        for k, v in WORKSPACE_DIRECTORIES.items()
        if v.get("type") == "context"
    ]

    return f"""# Workspace

Initialized: {timestamp.strftime('%Y-%m-%d %H:%M UTC')}

## Agents ({len(DEFAULT_ROSTER)})

| Agent | Role | Domain | Status |
|---|---|---|---|
{chr(10).join(agent_lines)}

## Tasks (0)

| Task | Mode | Schedule | Status |
|---|---|---|---|
| (none — create tasks to begin) | | | |

## Context Domains
{chr(10).join(context_domains)}

### Output Categories
{chr(10).join(output_categories)}

## How This Workspace Works

**Registries are templates.** The agent types, task types, and directory structure
were initialized from system registries at setup. After initialization, this
workspace is self-contained — TP and agents evolve it independently.

**Context accumulates.** Tasks read from and write to /workspace/context/ domains.
Each execution cycle deepens the accumulated intelligence. Context compounds
across all tasks that touch the same domain.

**Outputs are derived.** Reports, briefs, and content are produced by synthesizing
accumulated context. They live in /workspace/outputs/ and are cross-task referenceable.

**TP manages.** TP creates tasks, evaluates outputs, steers next cycles, routes
feedback, and evolves the workspace structure over time.

---
*This manifest is a reference snapshot. The workspace filesystem is the source of truth.*
"""

"""
Task Pipeline — ADR-141 + ADR-145: Unified Execution Architecture

Mechanical generation pipeline triggered by scheduler. No decision-making — just execution.

Two execution paths:
  1. Single-step (existing): TASK.md has agent_slug, no type_key → direct generation
  2. Multi-step process (ADR-145): TASK.md has type_key → resolve process steps from registry
     → execute each step sequentially → pass output forward as explicit handoff

Single-step flow:
  Scheduler → Read TASK.md → Resolve agent → Gather context → Generate → Save → Deliver

Multi-step flow:
  Scheduler → Read TASK.md → Resolve type_key → Look up process steps
    → For each step: resolve agent by type → gather context + prior step output → generate
    → Final step output → compose HTML → deliver

Replaces: agent_pulse.py, trigger_dispatch.py, execution_strategies.py,
          agent_execution.py (execute_agent_generation).
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from services.schedule_utils import (
    calculate_next_run_at as _calculate_next_run_at,
    format_daily_local_time_label,
    get_user_timezone,
)

logger = logging.getLogger(__name__)


def _normalize_match_text(value: str) -> str:
    """Normalize text for deterministic token-aware substring matching."""
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


def _build_objective_search_text(task_info: dict) -> str:
    """Flatten task objective fields into a normalized search string."""
    objective = task_info.get("objective", {}) or {}
    parts = [
        task_info.get("title", ""),
        objective.get("deliverable", ""),
        objective.get("audience", ""),
        objective.get("purpose", ""),
        objective.get("format", ""),
    ]
    parts.extend(task_info.get("success_criteria", []) or [])
    normalized = _normalize_match_text(" ".join(parts))
    return f" {normalized} " if normalized else ""


def _parse_tracker_entities(tracker_content: str) -> list[dict]:
    """Parse tracker markdown table into entity metadata rows."""
    entities = []
    for raw_line in (tracker_content or "").splitlines():
        line = raw_line.strip()
        if not line.startswith("|"):
            continue

        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 4:
            continue
        if cells[0].lower() == "slug" or set(cells[0]) == {"-"}:
            continue

        files = [
            file_name.strip()
            for file_name in cells[2].split(",")
            if file_name.strip() and file_name.strip() != "—"
        ]
        entities.append({
            "slug": cells[0],
            "last_updated": cells[1],
            "files": files,
            "status": cells[3],
        })

    return entities


def _get_primary_entity_filename(domain_key: str) -> Optional[str]:
    """Return the primary summary file for entities in a given domain."""
    from services.directory_registry import get_domain

    domain = get_domain(domain_key) or {}
    entity_structure = domain.get("entity_structure") or {}
    if not entity_structure:
        return None
    return next(iter(entity_structure.keys()), None)


def _read_domain_metadata_sync(client, user_id: str, domain_prefix: str) -> dict:
    """Read domain metadata from _domain.md file in workspace.

    ADR-188: Enables TP-composed domains to declare metadata (temporal, ttl_days,
    entity_type, display_name) without a registry entry. The file uses YAML-style
    frontmatter key: value pairs.

    Returns dict of metadata fields. Empty dict if file not found.
    """
    domain_md_path = f"{domain_prefix}/_domain.md"
    try:
        result = (
            client.table("workspace_files")
            .select("content")
            .eq("user_id", user_id)
            .eq("path", domain_md_path)
            .limit(1)
            .execute()
        )
        if not result.data or not result.data[0].get("content"):
            return {}

        content = result.data[0]["content"]
        meta = {}
        # Parse YAML-style frontmatter between --- delimiters
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                for line in parts[1].strip().splitlines():
                    if ":" in line:
                        key, val = line.split(":", 1)
                        key = key.strip()
                        val = val.strip()
                        # Coerce types
                        if val.lower() == "true":
                            meta[key] = True
                        elif val.lower() == "false":
                            meta[key] = False
                        elif val.isdigit():
                            meta[key] = int(val)
                        else:
                            meta[key] = val
        return meta
    except Exception:
        return {}


def _match_entities_to_objective(
    tracker_entities: list[str],
    task_info: dict,
) -> list[str]:
    """Match task objective text against entity slugs/names in tracker.

    ADR-154 Phase 2: Tracker-driven context selection. Instead of loading the 20
    most recent files regardless of relevance, we use the task objective to select
    which entities matter for this execution cycle.

    Rationale: see docs/analysis/context-prioritization-discourse-2026-04-03.md
    (Option A — deterministic heuristic, zero LLM cost).

    Returns list of entity slugs that match the objective. Empty list means
    "no specific match" → caller falls back to synthesis + primary-file loading.
    """
    if not tracker_entities:
        return []

    objective_text = _build_objective_search_text(task_info)
    if not objective_text:
        return []

    matched = []
    for slug in tracker_entities:
        variants = {
            _normalize_match_text(slug),
            _normalize_match_text(slug.replace("-", " ")),
            _normalize_match_text(slug.replace("_", " ")),
        }
        if any(variant and f" {variant} " in objective_text for variant in variants):
            matched.append(slug)

    return matched


async def _gather_context_domains(
    client,
    user_id: str,
    context_reads: list[str],
    task_info: Optional[dict] = None,
    max_files_per_domain: int = 20,
    max_content_per_file: int = 3000,
) -> str:
    """Read accumulated context from workspace context domains.

    ADR-151: /workspace/context/{domain}/ files are the primary context source.

    ADR-154 Phase 2 — Tracker-driven selective loading (hybrid A+C):
    Instead of "load 20 most recent files" (naive), this function now:
      1. Always loads synthesis files first (cross-entity summaries, high value)
      2. If task objective mentions specific entities → load those entities' full files
      3. If objective is general → load only the primary summary file per entity
         (profile.md, analysis.md, status.md, etc.)
      4. Agent can use ReadFile/QueryKnowledge tools for deeper retrieval during
         tool rounds (Option C — agent-driven deep retrieval)

    Rationale: As workspaces grow (30+ entities × 4 files each = 120+ files),
    recency-ordered loading misses relevant-but-not-recent files. Entity matching
    ensures the agent sees what matters for THIS task, not just what was touched last.
    See: docs/analysis/context-prioritization-discourse-2026-04-03.md

    Returns formatted context string with domain sections.
    """
    if not context_reads:
        return ""

    from services.directory_registry import (
        get_domain_folder, get_synthesis_content, get_tracker_path, has_entity_tracker,
        WORKSPACE_DIRECTORIES,
    )

    sections = []

    for domain_key in context_reads:
        folder = get_domain_folder(domain_key)
        if not folder:
            continue

        prefix = f"/workspace/{folder}"

        # ADR-188: Read domain metadata from _domain.md first, registry fallback.
        # This enables TP-composed domains (not in registry) to declare temporal
        # behavior and TTL via a workspace file.
        domain_meta = _read_domain_metadata_sync(client, user_id, prefix)
        domain_def = WORKSPACE_DIRECTORIES.get(domain_key, {})
        is_temporal = domain_meta.get("temporal", domain_def.get("temporal", False))
        ttl_days = domain_meta.get("ttl_days", domain_def.get("ttl_days"))

        # ADR-158: Soft TTL — temporal domains only load files within TTL window
        ttl_cutoff = None
        if is_temporal and ttl_days:
            from datetime import datetime, timezone, timedelta
            ttl_cutoff = (datetime.now(timezone.utc) - timedelta(days=ttl_days)).isoformat()

        try:
            domain_parts = []

            # ── Step 1: Always load synthesis file (cross-entity summary) ──
            # Synthesis files (_landscape.md, _overview.md, etc.) are the
            # highest-value-per-token context — cross-entity patterns, market
            # maps, relationship health. Always included regardless of objective.
            synthesis_info = get_synthesis_content(domain_key)
            if synthesis_info:
                synthesis_filename, _ = synthesis_info
                synthesis_path = f"{prefix}/{synthesis_filename}"
                try:
                    synth_result = (
                        client.table("workspace_files")
                        .select("path, content, updated_at")
                        .eq("user_id", user_id)
                        .eq("path", synthesis_path)
                        .limit(1)
                        .execute()
                    )
                    synth_rows = synth_result.data or []
                    if synth_rows and (synth_rows[0].get("content") or "").strip():
                        row = synth_rows[0]
                        content = (row.get("content") or "")[:max_content_per_file]
                        updated = row.get("updated_at", "")[:10]
                        domain_parts.append(
                            f"### {synthesis_filename} (synthesis, updated {updated})\n{content}"
                        )
                except Exception:
                    pass  # Non-fatal — continue without synthesis

            # ── Step 2: Determine entity loading strategy ──
            # If this domain has entities, try objective-matching first.
            # Otherwise (signals, non-entity domains), fall back to recency.
            matched_entities = []
            has_entities = has_entity_tracker(domain_key)
            tracker_entities = []
            primary_entity_file = _get_primary_entity_filename(domain_key)

            if has_entities:
                tracker_path = get_tracker_path(domain_key)
                try:
                    tracker_result = (
                        client.table("workspace_files")
                        .select("path, content, updated_at")
                        .eq("user_id", user_id)
                        .eq("path", f"/workspace/{tracker_path}")
                        .limit(1)
                        .execute()
                    )
                    tracker_rows = tracker_result.data or []
                    if tracker_rows:
                        tracker_entities = _parse_tracker_entities(
                            tracker_rows[0].get("content") or ""
                        )
                except Exception:
                    pass  # Non-fatal — fall through to general loading

            if has_entities and task_info and tracker_entities:
                matched_entities = _match_entities_to_objective(
                    [entity["slug"] for entity in tracker_entities], task_info,
                )

            # ── Step 3: Load entity files based on strategy ──
            if matched_entities:
                # TARGETED: Objective mentions specific entities → load their full files
                # This ensures "how does Acme compare to Beta" gets both entities'
                # profiles, signals, product, and strategy files.
                tracker_by_slug = {entity["slug"]: entity for entity in tracker_entities}
                for entity_slug in matched_entities:
                    entity_prefix = f"{prefix}/{entity_slug}/"
                    entity_limit = max(
                        len(tracker_by_slug.get(entity_slug, {}).get("files", [])),
                        1,
                    ) + 2
                    try:
                        entity_result = (
                            client.table("workspace_files")
                            .select("path, content, updated_at")
                            .eq("user_id", user_id)
                            .like("path", f"{entity_prefix}%")
                            .order("updated_at", desc=True)
                            .limit(entity_limit)
                            .execute()
                        )
                        for row in (entity_result.data or []):
                            content = (row.get("content") or "")[:max_content_per_file]
                            updated = row.get("updated_at", "")[:10]
                            rel_path = row.get("path", "").replace(prefix + "/", "")
                            if content.strip():
                                domain_parts.append(
                                    f"### {rel_path} (matched, updated {updated})\n{content}"
                                )
                    except Exception:
                        pass

                # Also load a few recent non-matched entity profiles for breadth
                # (the agent may discover cross-entity patterns)
                remaining_budget = max(0, max_files_per_domain - len(domain_parts))
                if remaining_budget > 0 and primary_entity_file:
                    matched_set = set(matched_entities)
                    try:
                        broad_result = (
                            client.table("workspace_files")
                            .select("path, content, updated_at")
                            .eq("user_id", user_id)
                            .like("path", f"{prefix}/%/{primary_entity_file}")
                            .order("updated_at", desc=True)
                            .limit(remaining_budget + len(matched_entities))
                            .execute()
                        )
                        for row in (broad_result.data or []):
                            rel_path = row.get("path", "").replace(prefix + "/", "")
                            entity = rel_path.split("/")[0] if "/" in rel_path else ""
                            if entity in matched_set:
                                continue  # Already loaded in full
                            content = (row.get("content") or "")[:max_content_per_file]
                            updated = row.get("updated_at", "")[:10]
                            if content.strip():
                                domain_parts.append(
                                    f"### {rel_path} (updated {updated})\n{content}"
                                )
                                remaining_budget -= 1
                                if remaining_budget <= 0:
                                    break
                    except Exception:
                        pass

            elif has_entities:
                # GENERAL: No specific entity match → load the domain's primary
                # entity summary file (summary-level, not full entity files).
                # Agent can use ReadFile (ADR-168)
                # to pull specific entity files during tool rounds if needed.
                if primary_entity_file:
                    try:
                        profile_query = (
                            client.table("workspace_files")
                            .select("path, content, updated_at")
                            .eq("user_id", user_id)
                            .like("path", f"{prefix}/%/{primary_entity_file}")
                        )
                        if ttl_cutoff:
                            profile_query = profile_query.gte("updated_at", ttl_cutoff)
                        profile_result = (
                            profile_query.order("updated_at", desc=True)
                            .limit(max_files_per_domain)
                            .execute()
                        )
                        for row in (profile_result.data or []):
                            content = (row.get("content") or "")[:max_content_per_file]
                            updated = row.get("updated_at", "")[:10]
                            rel_path = row.get("path", "").replace(prefix + "/", "")
                            if content.strip():
                                domain_parts.append(
                                    f"### {rel_path} (updated {updated})\n{content}"
                                )
                    except Exception:
                        pass

            else:
                # NON-ENTITY domain (signals, etc.) — recency-ordered
                # ADR-158: temporal domains filtered by TTL
                query = (
                    client.table("workspace_files")
                    .select("path, content, updated_at, tags")
                    .eq("user_id", user_id)
                    .like("path", f"{prefix}/%")
                )
                if ttl_cutoff:
                    query = query.gte("updated_at", ttl_cutoff)
                result = query.order("updated_at", desc=True).limit(max_files_per_domain).execute()
                for row in (result.data or []):
                    content = (row.get("content") or "")[:max_content_per_file]
                    updated = row.get("updated_at", "")[:10]
                    rel_path = row.get("path", "").replace(prefix + "/", "")
                    if content.strip():
                        domain_parts.append(
                            f"### {rel_path} (updated {updated})\n{content}"
                        )

            if domain_parts:
                # ADR-158: label temporal domains explicitly
                label = f"Platform Observations: {domain_key}" if is_temporal else f"Accumulated Context: {domain_key}"
                if is_temporal and ttl_days:
                    label += f" (last {ttl_days} days)"
                sections.append(
                    f"## {label}\n" +
                    "\n\n".join(domain_parts)
                )

        except Exception as e:
            logger.warning(f"[TASK_EXEC] Context domain read failed for {domain_key}: {e}")

    return "\n\n".join(sections) if sections else ""


async def _compose_and_persist(
    client,
    user_id: str,
    task_slug: str,
    draft: str,
    task_info: dict,
    task_output_folder: str,
    pending_renders: list,
    title: str,
    next_version: int,
    started_at,
    prior_manifest,
    revision_scope: str,
) -> Optional[str]:
    """
    ADR-177: Unified parse-then-compose step replacing the split steps 12 + 12b.

    Ordering fix: parse sections FIRST, then compose with that structural knowledge.
    The old order (compose → parse) meant the render service always received flat
    markdown — section kind metadata was in memory but came too late to use.

    Pipeline:
      1. Parse draft into SectionContent objects (parse_draft_into_sections)
      2. Call /compose with pre-parsed sections (render service receives section kinds)
      3. Write output.html directly to task workspace (no agent workspace round-trip)
      4. Write section partials + sys_manifest.json to task workspace
      5. Keep outputs/latest/ in sync

    Non-fatal — task run succeeds even if compose fails.
    Returns the composed HTML string, or None on failure.
    """
    import os
    import httpx
    from services.task_workspace import TaskWorkspace

    tw = TaskWorkspace(client, user_id, task_slug)

    # Strip "outputs/" prefix from task_output_folder for tw.write paths
    _tf = task_output_folder.removeprefix("outputs/")

    # Resolve surface_type
    _surface = task_info.get("surface_type", "")
    if not _surface:
        _type_key = task_info.get("type_key", "").strip()
        if _type_key:
            try:
                from services.task_types import get_task_type
                _tdef = get_task_type(_type_key)
                if _tdef:
                    _surface = _tdef.get("surface_type", "report")
            except Exception:
                pass
    if not _surface:
        _surface = "report"

    # ── Step 1: Parse sections FIRST ──────────────────────────────────────────
    sections_parsed = {}
    _page_structure = task_info.get("page_structure")
    if not _page_structure:
        _type_key = task_info.get("type_key", "").strip()
        if _type_key:
            try:
                from services.task_types import get_task_type
                _tdef_ps = get_task_type(_type_key)
                if _tdef_ps:
                    _page_structure = _tdef_ps.get("page_structure")
            except Exception:
                pass

    if _page_structure:
        try:
            from services.compose.assembly import parse_draft_into_sections
            sections_parsed = parse_draft_into_sections(draft, _page_structure)
        except Exception as e:
            logger.warning(f"[COMPOSE] Section parsing failed (non-fatal): {e}")

    # ── Step 1b: Output contract validation (ADR-177 Phase 5e) ───────────────────
    # Validate each parsed section's kind against a lightweight structural contract.
    # Mismatches are logged and kind is downgraded to "narrative" (safe fallback).
    # No LLM calls — pure string/regex checks. Non-blocking.
    if sections_parsed:
        _kind_contracts = {
            # kind → callable(content: str) -> bool
            "metric-cards": lambda c: bool(re.search(r'.+:.+', c)),
            "entity-grid": lambda c: bool(re.search(r'##\s+\S|^\s*-\s+\S', c, re.MULTILINE)),
            "comparison-table": lambda c: "|" in c,
            "data-table": lambda c: "|" in c,
            "status-matrix": lambda c: bool(re.search(r'\[[^\]]+\]', c)),
            "timeline": lambda c: bool(re.search(r'.+:.+', c)),
            "trend-chart": lambda c: bool(re.search(r'[\d.]+', c)),
            "distribution-chart": lambda c: bool(re.search(r'[\d.]+', c)),
        }
        for sec_slug, sec_data in list(sections_parsed.items()):
            _kind = sec_data.get("kind", "narrative")
            _contract = _kind_contracts.get(_kind)
            if _contract:
                _content = sec_data.get("content", "")
                try:
                    _valid = _contract(_content)
                except Exception:
                    _valid = True  # don't fail on contract error
                if not _valid:
                    logger.warning(
                        f"[COMPOSE] Section '{sec_slug}' kind='{_kind}' failed "
                        f"output contract — downgrading to narrative (task={task_slug})"
                    )
                    sec_data["kind"] = "narrative"

    # ── Step 2: Build sections payload for render service ─────────────────────
    # ADR-177: send sections list; render service dispatches on kind.
    sections_payload = [
        {
            "kind": sec_data.get("kind", "narrative"),
            "title": sec_data.get("title", sec_slug),
            "content": sec_data.get("content", ""),
        }
        for sec_slug, sec_data in sections_parsed.items()
        if sec_data.get("content")
    ] if sections_parsed else []

    # Build asset references from pending_renders
    assets = []
    for r in (pending_renders or []):
        url = r.get("output_url") or r.get("content_url")
        path = r.get("path", "")
        if url and path:
            ref = path.split("/")[-1] if "/" in path else path
            assets.append({"ref": ref, "url": url})

    # ── Step 3: Call /compose on render service ────────────────────────────────
    html = None
    try:
        RENDER_SERVICE_URL = os.environ.get("RENDER_SERVICE_URL", "https://yarnnn-render.onrender.com")
        render_secret = os.environ.get("RENDER_SERVICE_SECRET", "")
        headers = {}
        if render_secret:
            headers["X-Render-Secret"] = render_secret

        async with httpx.AsyncClient(timeout=30.0) as http:
            resp = await http.post(
                f"{RENDER_SERVICE_URL}/compose",
                json={
                    # ADR-177 Phase D1: sections list (kind-aware) + flat markdown fallback
                    "sections": sections_payload,
                    "markdown": draft,   # fallback for render service until D2 lands
                    "title": title,
                    "surface_type": _surface,
                    "assets": assets,
                    "user_id": user_id,
                },
                headers=headers,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    html = data.get("html", "") or None
    except Exception as e:
        logger.warning(f"[COMPOSE] /compose request failed (non-fatal): {e}")

    # ── Step 4: Write output.html directly to task workspace ──────────────────
    if html:
        try:
            await tw.write(
                f"outputs/{_tf}/output.html", html,
                summary=f"Composed HTML for {title}",
                tags=["output", "html"],
            )
            await tw.write(
                "outputs/latest/output.html", html,
                summary=f"Latest composed HTML for {title}",
                tags=["output", "html", "latest"],
            )
        except Exception as e:
            logger.warning(f"[COMPOSE] HTML write to task workspace failed (non-fatal): {e}")

    # ── Step 5: Write section partials + sys_manifest.json ────────────────────
    if sections_parsed:
        try:
            from services.compose.assembly import (
                build_post_generation_manifest,
                _query_domain_state,
            )

            # Write section partials
            for sec_slug, sec_data in sections_parsed.items():
                if sec_data.get("content"):
                    await tw.write(
                        f"outputs/{_tf}/sections/{sec_slug}.md",
                        sec_data["content"],
                        summary=f"Section: {sec_data.get('title', sec_slug)}",
                        tags=["output", "section"],
                    )

            # Build sys_manifest.json
            context_reads = task_info.get("context_reads", [])
            domain_state = await _query_domain_state(client, user_id, context_reads)
            manifest = build_post_generation_manifest(
                task_slug=task_slug,
                surface_type=_surface,
                sections_parsed=sections_parsed,
                domain_state=domain_state,
                task_info=task_info,
                run_started_at=started_at.isoformat(),
                prior_manifest=prior_manifest,
                revision_scope=revision_scope,
            )
            manifest_json = manifest.to_json()
            await tw.write(
                f"outputs/{_tf}/sys_manifest.json",
                manifest_json,
                summary=f"Compose manifest v{next_version}",
                tags=["output", "manifest"],
            )
            await tw.write(
                "outputs/latest/sys_manifest.json",
                manifest_json,
                summary="Latest compose manifest",
                tags=["output", "manifest", "latest"],
            )
            logger.info(
                f"[COMPOSE] _compose_and_persist: {len(sections_parsed)} sections, "
                f"html={'yes' if html else 'no'} → outputs/{_tf}/"
            )
        except Exception as e:
            logger.warning(f"[COMPOSE] Manifest/sections write failed (non-fatal): {e}")

    return html


async def _post_run_domain_scan(
    client,
    user_id: str,
    task_slug: str,
    task_info: dict,
    draft: str,
    version_number: int,
    run_time,
    tools_used: Optional[list] = None,
    agent_reflection: Optional[dict] = None,
    duration_s: float = 0,
    tool_rounds: int = 0,
) -> None:
    """Post-execution: scan domains, update trackers, update task awareness.

    ADR-154: Replaces _route_output_to_context_domains(). Three responsibilities:
    1. Signal log entry (preserved from old function)
    2. Scan entity-bearing domains → update _tracker.md (materialized view)
    3. Update task awareness.md with cycle state

    All deterministic — no LLM calls. Non-fatal — failures logged.
    """
    from services.directory_registry import (
        get_domain_folder, has_entity_tracker, build_tracker_md, get_tracker_path,
    )
    from services.workspace import UserMemory
    from services.task_workspace import TaskWorkspace

    context_writes = (task_info or {}).get("context_writes", [])
    context_reads = (task_info or {}).get("context_reads", [])
    title = (task_info or {}).get("title", task_slug)
    um = UserMemory(client, user_id)
    tw = TaskWorkspace(client, user_id, task_slug)
    date_str = run_time.strftime("%Y-%m-%d")

    # ── 1. Signal log entry (preserved) ──
    try:
        if "signals" in context_writes:
            signal_path = f"context/signals/{date_str}.md"
            existing = await um.read(signal_path) or f"# Signals — {date_str}\n"
            signal_entry = (
                f"\n## {title} v{version_number} ({run_time.strftime('%H:%M UTC')})\n"
                f"- Task: {task_slug}\n"
                f"- Output: {len(draft)} chars\n"
                f"- Summary: {draft[:200].replace(chr(10), ' ').strip()}...\n"
            )
            await um.write(signal_path, existing + signal_entry,
                          summary=f"Signal from {task_slug} v{version_number}")
    except Exception as e:
        logger.warning(f"[TASK_EXEC] Signal log write failed (non-fatal): {e}")

    # ── 2. Domain entity scan → _tracker.md ──
    # Scan all domains this task writes to (for context tasks)
    entities_touched: dict[str, list[str]] = {}  # domain → [entity slugs]
    all_domains = set(context_writes) | set(context_reads)

    for domain_key in all_domains:
        if not has_entity_tracker(domain_key):
            continue

        folder = get_domain_folder(domain_key)
        if not folder:
            continue

        try:
            tracker_path = get_tracker_path(domain_key)
            prefix = f"/workspace/{folder}/"

            # List all files in this domain
            result = (
                client.table("workspace_files")
                .select("path, updated_at")
                .eq("user_id", user_id)
                .like("path", f"{prefix}%")
                .order("updated_at", desc=True)
                .limit(200)
                .execute()
            )
            rows = result.data or []

            # Extract entity subfolders from paths
            # e.g., /workspace/context/competitors/acme-corp/profile.md → acme-corp
            # e.g., /workspace/context/github/cursor-ai/cursor/latest.md → cursor-ai/cursor
            from services.directory_registry import get_entity_depth
            entity_depth = get_entity_depth(domain_key)
            entity_files: dict[str, dict] = {}  # slug → {last_updated, files}
            for row in rows:
                path = row.get("path", "")
                rel = path.replace(prefix, "")
                parts = rel.split("/")
                if len(parts) < entity_depth + 1:
                    continue  # Top-level files (_tracker.md, landscape.md) — skip
                entity_slug = "/".join(parts[:entity_depth])
                if entity_slug.startswith("_"):
                    continue  # System infrastructure files (_tracker.md)
                filename = parts[entity_depth].replace(".md", "")

                if entity_slug not in entity_files:
                    entity_files[entity_slug] = {
                        "slug": entity_slug,
                        "last_updated": row.get("updated_at", "")[:10],
                        "files": [],
                        "status": "active",
                    }
                if filename not in entity_files[entity_slug]["files"]:
                    entity_files[entity_slug]["files"].append(filename)

            # Calculate staleness based on task schedule
            schedule = task_info.get("schedule", "weekly")
            stale_days = {"daily": 3, "weekly": 10, "monthly": 45}.get(schedule, 14)
            from datetime import timedelta
            stale_cutoff = (run_time - timedelta(days=stale_days)).strftime("%Y-%m-%d")

            entities_list = []
            for slug, edata in sorted(entity_files.items()):
                if edata["last_updated"] and edata["last_updated"] < stale_cutoff:
                    edata["status"] = "stale"
                elif not edata["files"]:
                    edata["status"] = "discovered"
                entities_list.append(edata)

            # Track which entities were touched this cycle (updated today)
            touched = [e["slug"] for e in entities_list if e.get("last_updated") == date_str]
            if touched:
                entities_touched[domain_key] = touched

            # Write _tracker.md
            if tracker_path:
                tracker_content = build_tracker_md(domain_key, entities_list)
                await um.write(tracker_path, tracker_content,
                              summary=f"Entity tracker update: {domain_key}")

        except Exception as e:
            logger.warning(f"[TASK_EXEC] Domain scan failed for {domain_key} (non-fatal): {e}")

    # ── 3. Update task awareness.md ──
    try:
        awareness_lines = ["# Task Awareness\n"]

        # Last cycle section
        awareness_lines.append("## Last Cycle")
        awareness_lines.append(f"- **Run:** {run_time.strftime('%Y-%m-%d %H:%M UTC')} (v{version_number})")
        if duration_s:
            awareness_lines.append(f"- **Duration:** {duration_s:.0f}s, {tool_rounds} tool rounds")
        if entities_touched:
            for dk, slugs in entities_touched.items():
                awareness_lines.append(f"- **Entities touched ({dk}):** {', '.join(slugs)}")
        if tools_used:
            # Summarize tool usage
            from collections import Counter
            tool_counts = Counter(tools_used)
            tool_summary = ", ".join(f"{name} ({count})" for name, count in tool_counts.most_common())
            awareness_lines.append(f"- **Tools used:** {tool_summary}")
        if agent_reflection:
            confidence = agent_reflection.get("output_confidence", "unknown")
            level = confidence.split("—")[0].split("–")[0].strip() if confidence else "unknown"
            awareness_lines.append(f"- **Agent reflection:** confidence={level}")

        # Phase detection (ADR-154)
        type_key = (task_info or {}).get("type_key", "")
        task_phase = "steady"
        if type_key and context_writes:
            from services.task_types import get_bootstrap_criteria, evaluate_bootstrap_status
            bootstrap = get_bootstrap_criteria(type_key)
            if bootstrap:
                required_files = bootstrap.get("required_files", [])
                # Count entities that have all required files across all write domains
                total_qualified = 0
                total_entities = 0
                for dk in context_writes:
                    if dk == "signals" or not has_entity_tracker(dk):
                        continue
                    for slug, edata in entities_touched.get(dk, []) and [] or []:
                        pass  # entities_touched only has slugs
                # Use the tracker data we already built
                for dk in context_writes:
                    if dk == "signals" or dk not in entities_touched and dk not in all_domains:
                        continue
                    tracker_path_check = get_tracker_path(dk)
                    if not tracker_path_check:
                        continue
                    tracker_content_check = await um.read(tracker_path_check)
                    if not tracker_content_check:
                        continue
                    for line in tracker_content_check.split("\n"):
                        if line.startswith("|") and "Slug" not in line and "---" not in line:
                            parts = [p.strip() for p in line.split("|")]
                            if len(parts) >= 5:
                                total_entities += 1
                                files_str = parts[3] if len(parts) > 3 else ""
                                entity_files = [f.strip() for f in files_str.split(",") if f.strip() and f.strip() != "—"]
                                if all(rf in entity_files for rf in required_files):
                                    total_qualified += 1
                task_phase = evaluate_bootstrap_status(type_key, total_entities, total_qualified)

        # Domain state + phase section
        awareness_lines.append(f"\n## Phase: {task_phase}")
        if task_phase == "bootstrap":
            bootstrap_info = get_bootstrap_criteria(type_key) or {}
            min_e = bootstrap_info.get("min_entities", "?")
            awareness_lines.append(f"- Bootstrap in progress: {total_qualified}/{min_e} entities meet criteria")
            awareness_lines.append(f"- Total entities discovered: {total_entities}")
        else:
            awareness_lines.append("- Domain established. Normal cadence.")

        if context_writes:
            awareness_lines.append("\n## Domain State")
            for domain_key in context_writes:
                if domain_key == "signals":
                    continue
                if not has_entity_tracker(domain_key):
                    continue
                tracker_path = get_tracker_path(domain_key)
                if tracker_path:
                    tracker_content = await um.read(tracker_path)
                    if tracker_content:
                        health_start = tracker_content.find("## Domain Health")
                        if health_start >= 0:
                            awareness_lines.append(f"### {domain_key}")
                            awareness_lines.append(tracker_content[health_start:].strip())

        # Next cycle focus (derived from staleness + phase)
        stale_entities: list[str] = []
        for domain_key in (context_writes or context_reads):
            if not has_entity_tracker(domain_key) or domain_key == "signals":
                continue
            tracker_path = get_tracker_path(domain_key)
            if tracker_path:
                tracker_content = await um.read(tracker_path)
                if tracker_content:
                    for line in tracker_content.split("\n"):
                        if "| stale |" in line.lower():
                            parts = line.split("|")
                            if len(parts) >= 2:
                                slug = parts[1].strip()
                                if slug:
                                    stale_entities.append(f"{slug} ({domain_key})")

        # Next cycle focus — prefer agent-authored directive over generic staleness logic.
        # The agent writes this at end of run while context is hot (journalist's notes).
        agent_directive = (agent_reflection or {}).get("next_cycle_directive")
        awareness_lines.append(f"\n## Next Cycle Directive")
        if agent_directive:
            # Agent wrote specific marching orders — use them directly
            awareness_lines.append(agent_directive)
        elif task_phase == "bootstrap":
            awareness_lines.append("- **BOOTSTRAP PRIORITY:** Discover and profile new entities to meet minimum criteria.")
            if stale_entities:
                for se in stale_entities:
                    awareness_lines.append(f"- {se}: stale — update alongside discovery")
        elif stale_entities:
            for se in stale_entities:
                awareness_lines.append(f"- {se}: stale — prioritize update")
        else:
            awareness_lines.append("- All entities current. Discover new entities or deepen existing profiles.")

        # ── ADR-181: System verification → write entries to feedback.md ──
        try:
            await _compute_system_verification(
                tw=tw,
                task_slug=task_slug,
                task_info=task_info,
                stale_entities=stale_entities,
                task_phase=task_phase,
                agent_reflection=agent_reflection,
                run_time=run_time,
            )
        except Exception as e:
            logger.warning(f"[TASK_EXEC] System verification failed (non-fatal): {e}")

        # ── ADR-181: Evaluate actuation rules → execute qualifying mutations ──
        try:
            from services.feedback_actuation import evaluate_actuation_rules, age_out_system_entries
            from services.feedback_distillation import _read_task_feedback

            actuations = await evaluate_actuation_rules(tw, task_slug, task_info)
            if actuations:
                awareness_lines.append("\n## Actuation Log")
                for act in actuations:
                    if act.get("error"):
                        awareness_lines.append(
                            f"- **{act['rule']}** {act['target']}: error — {act['error']}"
                        )
                    else:
                        result = act.get("result", {})
                        awareness_lines.append(
                            f"- **{act['rule']}** {act['target']}: "
                            f"{result.get('action', 'done')} ({act['source']}, "
                            f"{act['count']} entries)"
                        )
                logger.info(
                    f"[TASK_EXEC] {len(actuations)} actuation(s) for {task_slug}"
                )

            # Age out stale system entries
            feedback_content = await _read_task_feedback(tw)
            if feedback_content:
                aged = age_out_system_entries(feedback_content)
                if aged != feedback_content:
                    await tw.write("feedback.md", aged,
                                  summary="ADR-181: age out system verification entries")
        except Exception as e:
            logger.warning(f"[TASK_EXEC] Actuation evaluation failed (non-fatal): {e}")

        awareness_content = "\n".join(awareness_lines) + "\n"
        await tw.write("awareness.md", awareness_content,
                      summary=f"Task awareness update v{version_number}")

    except Exception as e:
        logger.warning(f"[TASK_EXEC] Awareness update failed (non-fatal): {e}")


async def _compute_system_verification(
    tw,
    task_slug: str,
    task_info: dict,
    stale_entities: list[str],
    task_phase: str,
    agent_reflection: Optional[dict],
    run_time,
) -> None:
    """ADR-181: Deterministic post-run verification → feedback entries. Zero LLM cost.

    Reads workspace state already computed by _post_run_domain_scan() and writes
    feedback entries to feedback.md when verification thresholds are crossed.

    Three checks:
    1. Entity staleness — entities not updated within expected cadence
    2. Coverage gap — fewer entities than bootstrap criteria expect (post-bootstrap only)
    3. Agent low confidence — consecutive low-confidence reflections

    All checks are deterministic. Entries use source: system_verification.
    """
    now = run_time.strftime("%Y-%m-%d %H:%M")
    entries_to_write: list[str] = []

    # ── Check 1: Entity staleness ──
    # stale_entities is already computed: ["slug (domain_key)", ...]
    if stale_entities and task_phase != "bootstrap":
        # Only flag if there are stale entities outside bootstrap phase
        # (during bootstrap, staleness is expected — entities are being discovered)
        schedule = task_info.get("schedule", "weekly")
        stale_threshold = {"daily": 3, "weekly": 10, "monthly": 45}.get(schedule, 14)
        for se in stale_entities[:5]:  # Cap at 5 to avoid flooding
            entries_to_write.append(
                f"## System Verification ({now}, source: system_verification)\n"
                f"- Entity {se} exceeds staleness threshold ({stale_threshold} days)\n"
                f"- Action: flag stale entity {se} | severity: medium\n"
            )

    # ── Check 2: Coverage gap ──
    # Only for tasks with context_writes that have bootstrap criteria
    if task_phase == "steady":
        type_key = task_info.get("type_key", "")
        context_writes = task_info.get("context_writes", [])
        if type_key and context_writes:
            try:
                from services.task_types import get_bootstrap_criteria
                bootstrap = get_bootstrap_criteria(type_key)
                if bootstrap:
                    min_entities = bootstrap.get("min_entities", 0)
                    # Count current entities across write domains
                    from services.directory_registry import (
                        get_domain_folder, has_entity_tracker, get_tracker_path,
                    )
                    from services.workspace import UserMemory
                    um = UserMemory(tw._db, tw._user_id)
                    for dk in context_writes:
                        if dk == "signals" or not has_entity_tracker(dk):
                            continue
                        tracker_path = get_tracker_path(dk)
                        if not tracker_path:
                            continue
                        tracker_content = await um.read(tracker_path)
                        if not tracker_content:
                            continue
                        # Count active entities in tracker
                        active_count = 0
                        for line in tracker_content.split("\n"):
                            if line.startswith("|") and "Slug" not in line and "---" not in line:
                                if "| stale |" not in line.lower() and "| inactive |" not in line.lower():
                                    active_count += 1
                        if min_entities > 0 and active_count < min_entities:
                            entries_to_write.append(
                                f"## System Verification ({now}, source: system_verification)\n"
                                f"- Domain {dk} has {active_count} active entities "
                                f"(min expected: {min_entities} for {type_key})\n"
                                f"- Action: expand coverage {dk} | severity: low\n"
                            )
            except Exception as e:
                logger.warning(f"[SYS_VERIFY] Coverage check failed: {e}")

    # ── Check 3: Agent low confidence ──
    if agent_reflection:
        confidence = agent_reflection.get("output_confidence", "")
        if isinstance(confidence, str) and confidence.lower().startswith("low"):
            # Check if previous awareness.md also had low confidence
            prev_awareness = await tw.read("awareness.md") or ""
            if "confidence=low" in prev_awareness.lower():
                entries_to_write.append(
                    f"## System Verification ({now}, source: system_verification)\n"
                    f"- Agent reported low confidence for 2+ consecutive runs\n"
                    f"- Action: review data sources | severity: medium\n"
                )

    # ── Write entries to feedback.md ──
    if entries_to_write:
        from services.feedback_distillation import _read_task_feedback, _MAX_FEEDBACK_ENTRIES

        existing = await _read_task_feedback(tw)
        header = "# Task Feedback\n<!-- Source-agnostic feedback layer. Newest first. ADR-181. -->\n\n"

        # Parse existing entries
        all_entries = re.split(r"(?=^## )", existing, flags=re.MULTILINE)
        all_entries = [e.strip() for e in all_entries if e.strip() and e.strip().startswith("## ")]

        # Prepend new entries (newest first), cap total
        combined = [e.strip() for e in entries_to_write] + all_entries
        combined = combined[:_MAX_FEEDBACK_ENTRIES]

        content = header + "\n\n".join(combined) + "\n"
        await tw.write(
            "feedback.md",
            content,
            summary=f"ADR-181: system verification ({len(entries_to_write)} entries)",
        )
        logger.info(
            f"[SYS_VERIFY] Wrote {len(entries_to_write)} verification entries "
            f"for {task_slug}"
        )


def _parse_forced_sections(steering_md: str) -> list[str]:
    """Parse TP-forced section slugs from steering.md (ADR-170 Gap 1).

    ManageTask(action="steer", target_section="executive-summary") writes:
      <!-- target_section: executive-summary -->
    into steering.md. This helper extracts those slugs so the revision
    classifier can force them stale regardless of domain freshness.

    Returns empty list if no target_section directive found.
    """
    if not steering_md:
        return []
    import re as _re
    matches = _re.findall(r"<!--\s*target_section:\s*([^\s>]+)\s*-->", steering_md)
    return [m.strip() for m in matches if m.strip()]


def _extract_recent_feedback(feedback_md: str, max_entries: int = 3) -> str:
    """Extract the most recent N feedback entries from task feedback.md.

    ADR-181: feedback.md is a source-agnostic layer. Entries may have source tags:
    user_conversation, user_edit, evaluation, system_verification, system_lifecycle.
    Returns the last N entries as a string, regardless of source.
    """
    if not feedback_md or not feedback_md.strip():
        return ""
    entries = re.split(r"(?=^## )", feedback_md, flags=re.MULTILINE)
    entries = [e.strip() for e in entries if e.strip() and e.strip().startswith("## ")]
    if not entries:
        return ""
    recent = entries[:max_entries]  # Already newest-first (append-at-top convention)
    return "\n\n".join(recent)


def _total_input_tokens(usage: dict) -> int:
    """Sum all input token fields including prompt cache tokens."""
    return (
        usage.get("input_tokens", 0)
        + usage.get("cache_creation_input_tokens", 0)
        + usage.get("cache_read_input_tokens", 0)
    )


# =============================================================================
# TASK.md Parsing
# =============================================================================

def parse_task_md(content: str) -> dict:
    """Parse TASK.md into structured dict.

    Expected format:
        # Title
        **Slug:** my-task
        **Agent:** research-agent
        **Schedule:** weekly
        **Delivery:** email@example.com

        ## Objective
        - **Deliverable:** ...
        - **Audience:** ...

        ## Success Criteria
        - criterion 1
        - criterion 2

        ## Output Spec
        - section 1
        - section 2
    """
    result = {
        "title": "",
        "agent_slug": "",
        "schedule": "",
        "delivery": "",
        "objective": {},
        "success_criteria": [],
        "output_spec": [],
    }

    lines = content.strip().splitlines()
    if not lines:
        return result

    # Title from first heading
    if lines[0].startswith("# "):
        result["title"] = lines[0][2:].strip()

    # Parse metadata fields
    for line in lines:
        line_stripped = line.strip()
        if line_stripped.startswith("**Agent:**"):
            result["agent_slug"] = line_stripped.split("**Agent:**")[1].strip()
        elif line_stripped.startswith("**Slug:**"):
            result["slug"] = line_stripped.split("**Slug:**")[1].strip()
        elif line_stripped.startswith("**Type:**"):
            result["type_key"] = line_stripped.split("**Type:**")[1].strip()
        elif line_stripped.startswith("**Mode:**"):
            result["mode"] = line_stripped.split("**Mode:**")[1].strip()
        # ADR-166: **Output:** is the canonical key (output_kind, 4-value enum).
        # Backward compat: also accept legacy **Class:** and remap.
        elif line_stripped.startswith("**Output:**"):
            result["output_kind"] = line_stripped.split("**Output:**")[1].strip()
        elif line_stripped.startswith("**Class:**"):
            legacy_class = line_stripped.split("**Class:**")[1].strip()
            # Legacy class → output_kind mapping
            _legacy_map = {
                "context": "accumulates_context",
                "synthesis": "produces_deliverable",
                "back_office": "system_maintenance",
            }
            result["output_kind"] = _legacy_map.get(legacy_class, "produces_deliverable")
        elif line_stripped.startswith("**Schedule:**"):
            result["schedule"] = line_stripped.split("**Schedule:**")[1].strip()
        elif line_stripped.startswith("**Delivery:**"):
            result["delivery"] = line_stripped.split("**Delivery:**")[1].strip()
        elif line_stripped.startswith("**Surface:**"):
            result["surface_type"] = line_stripped.split("**Surface:**")[1].strip()
        elif line_stripped.startswith("**Context Reads:**"):
            raw = line_stripped.split("**Context Reads:**")[1].strip()
            result["context_reads"] = [d.strip() for d in raw.split(",") if d.strip() and d.strip() != "none"]
        elif line_stripped.startswith("**Context Writes:**"):
            raw = line_stripped.split("**Context Writes:**")[1].strip()
            result["context_writes"] = [d.strip() for d in raw.split(",") if d.strip() and d.strip() != "none"]
        elif line_stripped.startswith("**Sources:**"):
            # ADR-158 Phase 2: per-task source selection
            # Format: slack:C123,C456; notion:page-id-1,page-id-2
            raw = line_stripped.split("**Sources:**")[1].strip()
            if raw and raw != "none":
                sources = {}
                for segment in raw.split(";"):
                    segment = segment.strip()
                    if ":" in segment:
                        platform, ids_str = segment.split(":", 1)
                        sources[platform.strip()] = [s.strip() for s in ids_str.split(",") if s.strip()]
                result["sources"] = sources
        # ADR-183: **Commerce:** field — product link for subscriber delivery
        elif line_stripped.startswith("**Commerce:**"):
            raw = line_stripped.split("**Commerce:**")[1].strip()
            commerce = {}
            for part in raw.split(","):
                part = part.strip()
                if "=" in part:
                    k, v = part.split("=", 1)
                    commerce[k.strip()] = v.strip()
            result["commerce"] = commerce
        # ADR-154: **Output Category:** parsing removed — tasks own their outputs

    # Parse sections
    current_section = None
    page_structure_lines: list[str] = []
    for line in lines:
        line_stripped = line.strip()
        if line_stripped == "## Objective":
            current_section = "objective"
        elif line_stripped == "## Process":
            current_section = "process"
            continue
        elif line_stripped == "## Success Criteria":
            current_section = "criteria"
            continue
        elif line_stripped == "## Output Spec":
            current_section = "output_spec"
            continue
        elif line_stripped == "## Team":
            # ADR-176 Phase 2: specialist team assigned to this task
            current_section = "team"
            continue
        elif line_stripped == "## Page Structure":
            # ADR-174 Phase 3: YAML block declaring section layout for compose pipeline
            current_section = "page_structure"
            continue
        elif line_stripped.startswith("## "):
            current_section = None
            continue

        if current_section == "objective" and line_stripped.startswith("- **"):
            match = re.match(r"- \*\*(\w+):\*\*\s*(.*)", line_stripped)
            if match:
                key = match.group(1).lower()
                result["objective"][key] = match.group(2).strip()
        elif current_section == "criteria" and line_stripped.startswith("- "):
            result["success_criteria"].append(line_stripped[2:])
        elif current_section == "output_spec" and line_stripped.startswith("- "):
            result["output_spec"].append(line_stripped[2:])
        elif current_section == "process" and re.match(r"^\d+\.\s+\*\*", line_stripped):
            # Parse: "1. **Update-Context** (research-agent): instruction text"
            step_match = re.match(
                r"^\d+\.\s+\*\*(.+?)\*\*\s*\(([^)]+)\)(?::\s*(.*))?",
                line_stripped,
            )
            if step_match:
                step_name = step_match.group(1).strip().lower().replace(" ", "-")
                agent_ref = step_match.group(2).strip()
                instruction_text = (step_match.group(3) or "").strip()
                result.setdefault("process_steps", []).append({
                    "step": step_name,
                    "agent_ref": agent_ref,  # Could be agent_slug or agent_type
                    "instruction": instruction_text,
                })
        elif current_section == "team" and line_stripped.startswith("- "):
            # Parse "- researcher (optional description)" → extract role key
            role_part = line_stripped[2:].split("(")[0].strip()
            if role_part:
                result.setdefault("team", []).append(role_part)
        elif current_section == "page_structure":
            page_structure_lines.append(line)

    # ADR-174 Phase 3: parse ## Page Structure section as YAML
    # This lets TP author bespoke page_structure in TASK.md, taking precedence over registry.
    if page_structure_lines:
        import yaml as _yaml
        try:
            yaml_text = "\n".join(page_structure_lines)
            parsed_ps = _yaml.safe_load(yaml_text)
            if isinstance(parsed_ps, list):
                result["page_structure"] = parsed_ps
        except Exception:
            pass  # Malformed YAML — silently ignore, registry fallback applies

    return result


# =============================================================================
# Context Gathering (replaces execution_strategies.py)
# =============================================================================

async def gather_task_context(
    client,
    user_id: str,
    agent: dict,
    agent_slug: str,
    task_info: Optional[dict] = None,
    task_slug: Optional[str] = None,
) -> tuple[str, dict]:
    """Gather context for task execution.

    ADR-154: Context priority order (who/what/how):
    1. Task awareness (HOW) — cycle-to-cycle execution state
    2. Domain tracker (WHAT) — entity registry + freshness (context tasks)
    3. Accumulated context domains (WHAT) — /workspace/context/ files
    4. Agent identity (WHO) — AGENT.md only (no thesis, no working notes)
    5. User notes — workspace-level standing instructions
    6. Prior output + output inventory (ADR-182) — pre-gathered for all modes

    Returns:
        (context_text, context_metadata)
    """
    from services.workspace import AgentWorkspace, UserMemory
    from services.task_workspace import TaskWorkspace

    ws = AgentWorkspace(client, user_id, agent_slug)
    await ws.ensure_seeded(agent)

    sections = []

    # 0. Task awareness — cycle-to-cycle state (ADR-154)
    if task_slug:
        try:
            tw = TaskWorkspace(client, user_id, task_slug)
            awareness = await tw.read("awareness.md")
            if awareness and "no prior cycles" not in awareness:
                sections.append(f"## Execution Awareness\n{awareness}")
        except Exception as e:
            logger.debug(f"[TASK_EXEC] Awareness read failed: {e}")

    # 0b. Source scope — which platform sources to read (ADR-158 Phase 2)
    if task_info and task_info.get("sources"):
        sources = task_info["sources"]
        source_lines = ["## Selected Sources"]
        source_lines.append("Read ONLY from these selected sources (user-configured scope):")
        for platform, ids in sources.items():
            # Resolve source names from platform_connections landscape
            try:
                conn_result = (
                    client.table("platform_connections")
                    .select("landscape")
                    .eq("user_id", user_id)
                    .eq("platform", platform)
                    .eq("status", "active")
                    .maybe_single()
                    .execute()
                )
                name_map = {}
                if conn_result and conn_result.data:
                    resources = (conn_result.data.get("landscape") or {}).get("resources", [])
                    name_map = {r["id"]: r.get("name", r["id"]) for r in resources}
            except Exception:
                name_map = {}
            source_names = [name_map.get(sid, sid) for sid in ids]
            source_lines.append(f"- **{platform}**: {', '.join(source_names)}")
        sections.append("\n".join(source_lines))

    # 1. Domain tracker — entity registry for context tasks (ADR-154)
    if task_info:
        context_writes = task_info.get("context_writes", [])
        if context_writes:
            from services.directory_registry import has_entity_tracker, get_tracker_path
            um_tracker = UserMemory(client, user_id)
            for domain_key in context_writes:
                if domain_key == "signals" or not has_entity_tracker(domain_key):
                    continue
                tracker_path = get_tracker_path(domain_key)
                if tracker_path:
                    try:
                        tracker_content = await um_tracker.read(tracker_path)
                        if tracker_content:
                            sections.append(f"## Entity Tracker: {domain_key}\n{tracker_content}")
                    except Exception:
                        pass

    # 2. Accumulated context domains — PRIMARY CONTEXT (ADR-151/152)
    # ADR-154 Phase 2: pass task_info for objective-driven entity selection
    #
    # Budget-driven per-domain cap: two tiers based on output_kind.
    #
    # accumulates_context tasks (update-context step): the agent's job IS to read
    # and update context files via tools (ReadFile/WriteFile). Pre-loading large
    # context dumps is redundant — it reads what it needs during tool rounds.
    # Load only tracker + synthesis (index-level) so the agent knows what exists.
    # Budget: 8 files total (~7K chars / ~1.8K tokens). Agent fetches detail via tools.
    #
    # produces_deliverable tasks (derive-output step): the agent synthesizes from
    # accumulated context into a final output. It needs richer pre-loaded context
    # because it's composing, not researching. Larger budget justified.
    # Budget: 30 files total (~22K chars / ~5.5K tokens).
    #
    # Per-domain floor: 3 (synthesis + 2 primary entities minimum).
    # Per-domain ceiling: 10 for deliverable tasks (prevents unbounded single-domain loads).
    _output_kind = (task_info or {}).get("output_kind", "produces_deliverable")
    if _output_kind == "accumulates_context":
        _TOTAL_FILE_BUDGET = 8
        _PER_DOMAIN_FLOOR = 2
        _PER_DOMAIN_CEILING = 4
    else:
        _TOTAL_FILE_BUDGET = 30
        _PER_DOMAIN_FLOOR = 3
        _PER_DOMAIN_CEILING = 10
    context_domains_text = ""
    if task_info:
        context_reads = task_info.get("context_reads", [])
        if context_reads:
            _domain_count = max(len(context_reads), 1)
            _files_per_domain = max(
                _PER_DOMAIN_FLOOR,
                min(_PER_DOMAIN_CEILING, _TOTAL_FILE_BUDGET // _domain_count),
            )
            context_domains_text = await _gather_context_domains(
                client, user_id, context_reads, task_info=task_info,
                max_files_per_domain=_files_per_domain,
            )
    if context_domains_text:
        sections.append(context_domains_text)

    # 3. Agent identity + selective playbooks (ADR-166: output_kind routing)
    output_kind = task_info.get("output_kind") if task_info else None
    ws_context = await ws.load_context(output_kind=output_kind)
    if ws_context:
        sections.append(f"## Agent Context\n{ws_context}")

    # 4. User notes — workspace-level standing instructions
    try:
        um = UserMemory(client, user_id)
        notes = await um.read("notes.md")
        if notes:
            sections.append(f"## User Notes\n{notes}")
    except Exception as e:
        logger.debug(f"[TASK_EXEC] User memory read failed: {e}")

    # 5. ADR-182: Prior output + output inventory (pre-gathered for all modes)
    # Pre-loads what agents would otherwise fetch via ReadFile/ListFiles tool rounds.
    # For produces_deliverable tasks this eliminates 2-3 read-only tool rounds.
    if task_slug:
        try:
            tw = TaskWorkspace(client, user_id, task_slug)

            # 5a. Prior output excerpt — truncated to avoid token bloat
            prior_md = await tw.read("outputs/latest/output.md")
            if prior_md and prior_md.strip():
                _MAX_PRIOR = 3000
                excerpt = prior_md[:_MAX_PRIOR]
                if len(prior_md) > _MAX_PRIOR:
                    excerpt += "\n\n[... truncated — full output available via ReadFile]"
                sections.append(f"## Prior Output (latest run)\n{excerpt}")

            # 5b. Output inventory — compact file listing so agent knows what assets exist
            output_files = await tw.list("outputs/latest/")
            if output_files:
                inventory_lines = ["## Output Inventory (outputs/latest/)"]
                for f in output_files:
                    fname = f.get("path", "").rsplit("/", 1)[-1] if isinstance(f, dict) else str(f)
                    updated = f.get("updated_at", "")[:10] if isinstance(f, dict) else ""
                    if fname and not fname.startswith("sys_"):  # skip internal manifests
                        inventory_lines.append(f"- {fname} (EXISTS{', ' + updated if updated else ''})")
                if len(inventory_lines) > 1:
                    sections.append("\n".join(inventory_lines))
        except Exception as e:
            logger.debug(f"[TASK_EXEC] ADR-182 prior output/inventory read failed (non-fatal): {e}")

    context_text = "\n\n".join(sections) if sections else "(No context available)"

    metadata = {
        "sections": len(sections),
        "scope": agent.get("scope", "cross_platform"),
    }

    return context_text, metadata


# =============================================================================
# Prompt Building
# =============================================================================

def build_task_execution_prompt(
    task_info: dict,
    agent: dict,
    agent_instructions: str,
    context: str,
    user_context: Optional[str] = None,
    deliverable_spec: str = "",
    steering_notes: str = "",
    task_feedback: str = "",
    task_mode: str = "recurring",
    prior_output: str = "",
    prior_state_brief: str = "",
    task_phase: str = "steady",
    generation_brief: str = "",
) -> tuple[list[dict], str]:
    """Build system prompt (as cached content blocks) and user message.

    ADR-154: Phase-aware. Bootstrap phase overrides step instructions.
    ADR-149: DELIVERABLE.md injected into system prompt.
    ADR-173: prior_state_brief injected for non-produces_deliverable tasks —
    compact summary of what was produced last run (assets, output excerpt).
    Prompt caching: system prompt is stable across tool rounds within
    one task execution — cache_control on the block saves ~90% on
    rounds 2+ of the same execution.

    Returns:
        (system_blocks, user_message)
    """
    role = agent.get("role", "custom")
    title = task_info.get("title", "Untitled Task")

    # --- System prompt ---
    system = f"""You are an autonomous agent executing a scheduled task.

## Output Rules
- Follow the format and instructions below exactly.
- Be concise and professional — keep content tight and scannable.
- Do not invent information not present in the provided context or your research findings.
- Do not use emojis in headers or content unless preferences explicitly request them.
- Use plain markdown headers (##, ###) and bullet points for structure."""

    # User context — pre-rendered by _load_user_context() (identity + prefs + brand)
    if user_context:
        system += "\n\n" + user_context

    # Agent instructions (from AGENT.md)
    if agent_instructions:
        system += f"\n\n## Agent Instructions\n{agent_instructions}"

    # Agent methodology — referential index only (Claude Code pattern).
    # Full playbook content lives in the agent's memory/ workspace files.
    # The agent reads them via ReadFile when making methodology decisions.
    # Injecting full content (1,500-2,000 tokens) into every tool round is
    # wasteful — the index (~150 tokens) is enough to guide behavior and
    # tell the agent where to look for detail.
    from services.agent_framework import PLAYBOOK_METADATA, TASK_OUTPUT_PLAYBOOK_ROUTING, get_type_playbook
    playbooks = get_type_playbook(role)
    output_kind_for_playbook = task_info.get("output_kind") if task_info else None
    if playbooks:
        relevant_tags = None
        if output_kind_for_playbook and output_kind_for_playbook in TASK_OUTPUT_PLAYBOOK_ROUTING:
            relevant_tags = set(TASK_OUTPUT_PLAYBOOK_ROUTING[output_kind_for_playbook])
        index_lines = ["Your methodology playbooks are in memory/. Read them via ReadFile when making methodology decisions."]
        for filename in playbooks:
            meta = PLAYBOOK_METADATA.get(filename, {})
            desc = meta.get("description", filename.replace("_playbook-", "").replace(".md", ""))
            name = filename.replace("_playbook-", "").replace(".md", "").replace("-", " ").title()
            is_relevant = True
            if relevant_tags is not None:
                playbook_tags = set(meta.get("tags", "").split(","))
                is_relevant = bool(relevant_tags & playbook_tags)
            marker = " ← relevant for this task" if is_relevant else ""
            index_lines.append(f"- **{name}** (memory/{filename}): {desc}{marker}")
        system += "\n\n## Methodology\n" + "\n".join(index_lines)

    # ADR-174 Phase 1: Workspace conventions — compact structural reference.
    # Injected so agents know where to write files and how without consulting Python code.
    system += """

## Workspace Conventions (compact)

Write files to consistent paths so they accumulate and are searchable:
- Context domain entities: `/workspace/context/{domain}/{entity-slug}/profile.md`
- Signal logs: `/workspace/context/{domain}/{entity-slug}/signals.md` (append newest-first)
- Domain synthesis: `/workspace/context/{domain}/landscape.md` (overwrite each cycle)
- Task output: `/tasks/{slug}/outputs/latest/output.md` (overwrite) + dated snapshot
- New domain: create `/workspace/context/{new-domain}/landscape.md` — no approval needed

Write modes: entity files **overwrite** (current best), signal/log files **append** (dated history), synthesis **overwrite**.
Full conventions: `ReadFile(path="/workspace/CONVENTIONS.md")`"""

    # Tool usage guidance
    system += """

## Accumulation-First Execution

Your workspace accumulates across runs. Before generating anything, understand what already exists.

**The principle:** Read the current state → identify the gap → produce only what's missing or stale.

**What to check before generating (all pre-loaded in your context below):**
1. **DELIVERABLE.md** — what's the quality target?
2. **Prior Output** — if a prior run produced output, it's included below as "Prior Output (latest run)". Don't start from scratch if that version is current.
3. **Output Inventory** — if assets (images, charts) exist from a prior run, they're listed below as "Output Inventory". Reuse them. Call `RuntimeDispatch` only for missing or stale assets.
4. **Domain state** — the gathered context shows what entities and signals exist. Work with what's there; identify true gaps before searching externally.

**The gap is the only work.** A section that was accurate last run and whose source data hasn't changed should be preserved, not regenerated. A section with stale source data gets updated. A missing section gets written fresh. This is delta generation, not full regeneration.

## Tool Usage (Headless Mode)
All relevant context has been pre-gathered and included below. In most cases, you have everything needed to produce your output directly.

**Decision order — follow this sequence:**
1. Read the gathered context below first. Most tasks have enough to generate from.
2. Produce your output directly from the provided context.
3. If you have asset generation tools (RuntimeDispatch), use them only for missing assets (check the Output Inventory).
4. If you have investigation tools and identify a specific gap ("I have Q1 data but no Q2"), call ONE tool to fill it. Stop there unless critical.

**WebSearch principles (when available):**
- Call WebSearch only when gathered context is genuinely stale or missing external data.
- Be specific: `WebSearch(query="Acme Corp pricing 2025")` not `WebSearch(query="Acme")`.
- Use `context=` to narrow scope: `WebSearch(query="latest releases", context="AI coding tools")`.
- Do not repeat a search you already made — if round 2 has results, use them in round 3.
- Stop when you have enough. Three web searches with diminishing returns means stop, not search more.

**Stopping criteria — stop calling tools when:**
- The gathered context + results answer the task objective
- Two consecutive tool calls returned nothing new
- You have reached a clear answer and are filling in edges, not gaps

**Never narrate tool usage in the final output.** The reader sees only your generated content.

## Visual Assets
Include visual elements in your output using these methods:

**Auto-rendered (inline):**
- **Data tables**: Markdown tables with numeric data → automatically rendered as charts.
- **Diagrams**: ```mermaid code blocks → automatically rendered as SVG diagrams.
- Interleave visuals with prose — aim for a visual element every 2-3 paragraphs.

**Generated assets (RuntimeDispatch — check first, then call):**
- **Hero image**: Check if `outputs/latest/hero.png` already exists (`ReadFile` or note from awareness). If it does, embed it directly: `![Hero]({{existing_url}})`. If not, call `RuntimeDispatch(type="image", input={"prompt": "...", "aspect_ratio": "16:9", "style": "editorial"}, output_format="png", filename="hero")` BEFORE writing main content, then embed the returned `output_url`.
- **Charts**: Same pattern — check if the chart exists in `outputs/latest/assets/` before regenerating. Call `RuntimeDispatch(type="chart", input={...}, output_format="png")` only when data has changed or chart is missing.
- Only call RuntimeDispatch for assets explicitly required by DELIVERABLE.md or clearly needed by the output.

## Empty Context Handling
If context says "(No context available)" or tools return no results:
- Still produce the output in the requested format.
- Note briefly that no recent activity was found.
- A short, properly formatted output is always better than meta-commentary."""

    # ADR-149: DELIVERABLE.md — quality contract injection
    if deliverable_spec and deliverable_spec.strip():
        # Strip the header and comments, keep the spec sections
        spec_clean = deliverable_spec.strip()
        if spec_clean.startswith("# Deliverable Specification"):
            spec_clean = spec_clean.split("\n", 1)[-1].strip()
        # Remove HTML comments
        spec_clean = re.sub(r"<!--.*?-->", "", spec_clean, flags=re.DOTALL).strip()
        if spec_clean:
            system += f"\n\n## Deliverable Specification\nYour output MUST match this quality contract:\n{spec_clean}"

    # Reflection postamble (ADR-128/149 + success criteria eval)
    from services.agent_pipeline import _REFLECTION_POSTAMBLE, _CRITERIA_EVAL_SECTION
    criteria = task_info.get("success_criteria", [])
    if criteria:
        criteria_list = "\n".join(f"  - {c}" for c in criteria)
        criteria_eval = _CRITERIA_EVAL_SECTION.format(criteria_list=criteria_list)
    else:
        criteria_eval = ""
    system += _REFLECTION_POSTAMBLE.format(criteria_eval=criteria_eval)

    # --- User message ---
    user_parts = [f"# Task: {title}"]

    # Objective
    objective = task_info.get("objective", {})
    if objective:
        user_parts.append("\n## Objective")
        for key in ["deliverable", "audience", "purpose", "format"]:
            val = objective.get(key)
            if val:
                user_parts.append(f"- **{key.capitalize()}:** {val}")
        # ADR-154/166: Phase-aware step instruction. Routing key is output_kind.
        step_instruction = objective.get("step_instruction")
        output_kind = task_info.get("output_kind", "")
        type_key = task_info.get("type_key", "")
        is_context_task = output_kind == "accumulates_context"

        # ADR-188: TASK.md instruction is primary source. Registry is fallback
        # for tasks created before ADR-188 or from registry templates where
        # TASK.md instruction was truncated.
        if task_phase == "bootstrap" and is_context_task and not step_instruction:
            # Bootstrap context task without TASK.md instruction — use registry
            from services.task_types import STEP_INSTRUCTIONS
            bootstrap_instruction = STEP_INSTRUCTIONS.get("update-context:bootstrap", "")
            if bootstrap_instruction:
                context_writes = task_info.get("context_writes", [])
                primary_domain = next((d for d in context_writes if d != "signals"), "")
                step_instruction = bootstrap_instruction.replace("{domain}", primary_domain)
        elif not step_instruction and is_context_task:
            # Steady-state context task without explicit step instruction — registry fallback
            from services.task_types import STEP_INSTRUCTIONS
            step_instruction = STEP_INSTRUCTIONS.get("update-context", "")

        if step_instruction:
            user_parts.append(f"\n**Your specific role:** {step_instruction}")

    # Success criteria
    criteria = task_info.get("success_criteria", [])
    if criteria:
        user_parts.append("\n## Success Criteria")
        for c in criteria:
            user_parts.append(f"- {c}")

    # Output spec
    output_spec = task_info.get("output_spec", [])
    if output_spec:
        user_parts.append("\n## Output Format")
        for s in output_spec:
            user_parts.append(f"- {s}")

    # ADR-170: Generation brief (produces_deliverable tasks with page_structure)
    # Replaces flat output_spec for structured tasks — tells LLM which sections to write,
    # what data exists per section, what assets are available, what is stale.
    if generation_brief:
        user_parts.append(f"\n{generation_brief}")

    # ADR-149: Goal mode — prior output as primary context
    if task_mode == "goal" and prior_output:
        user_parts.append(
            "\n## Prior Output (YOUR PRIMARY INPUT)\n"
            "You are revising this deliverable. Improve based on steering notes "
            "and feedback below. Build on what exists — do not start from scratch.\n\n"
            f"{prior_output[:8000]}"
        )

    # ADR-173: Prior state brief — compact summary of what exists from last run.
    # Injected for non-produces_deliverable tasks (produces_deliverable gets the full
    # compose brief via generation_brief above). Enables accumulation-first behavior:
    # agent knows what assets exist and what prior output looked like before generating.
    # Empty string on first run — graceful degradation to full generation.
    if prior_state_brief:
        user_parts.append(f"\n{prior_state_brief}")

    # ADR-149: Steering notes — TP's cycle-specific guidance
    if steering_notes and steering_notes.strip():
        clean_steering = steering_notes.strip()
        # Strip file header/comments
        if clean_steering.startswith("# Steering Notes"):
            clean_steering = clean_steering.split("\n", 1)[-1].strip()
        clean_steering = re.sub(r"<!--.*?-->", "", clean_steering, flags=re.DOTALL).strip()
        if clean_steering:
            user_parts.append(f"\n## Steering Notes (from task manager)\n{clean_steering}")

    # ADR-149: Recent task feedback — user corrections + TP evaluations
    if task_feedback and task_feedback.strip():
        user_parts.append(f"\n## Recent Feedback\nIncorporate these corrections:\n{task_feedback}")

    # Gathered context
    user_parts.append(f"\n## Gathered Context\n{context}")

    user_message = "\n".join(user_parts)

    # Split system prompt into static (cached) + dynamic (uncached) blocks.
    # Static block: output rules, agent instructions, methodology, tool guidance,
    # visual assets, empty context handling — identical for same agent across runs.
    # Dynamic block: user context, deliverable spec, success criteria —
    # task-specific content that changes per execution.
    #
    # This maximizes prompt caching: static block hits cache on tool rounds 2+
    # AND across different task runs for the same agent.

    # Find the split point — everything before "## User Context" or
    # "## Deliverable Specification" is static
    static_end_markers = [
        "\n\n## User Context",
        "\n\n## Deliverable Specification",
        "\n\n## Self-Reflection",  # reflection postamble starts here
    ]
    static_part = system
    dynamic_part = ""
    for marker in static_end_markers:
        idx = system.find(marker)
        if idx != -1:
            static_part = system[:idx]
            dynamic_part = system[idx:]
            break

    system_blocks = [
        {
            "type": "text",
            "text": static_part,
            "cache_control": {"type": "ephemeral"},
        },
    ]
    if dynamic_part.strip():
        system_blocks.append({
            "type": "text",
            "text": dynamic_part,
        })

    return system_blocks, user_message


# =============================================================================
# Cadence Calculation
# =============================================================================

def calculate_next_run_at(
    schedule,
    last_run_at: Optional[datetime] = None,
    user_timezone: str = "UTC",
) -> Optional[datetime]:
    """Calculate next_run_at from schedule. Pure math, no LLM.

    ADR-154: Schedule is just schedule — no phase override. Phase affects
    execution depth (tool rounds, prompt), not frequency. The journalist
    model: first run is deep research, subsequent runs are delta updates,
    but the check-in rhythm stays the same.
    """
    return _calculate_next_run_at(
        schedule=schedule,
        last_run_at=last_run_at,
        user_timezone=user_timezone,
    )


# =============================================================================
# Main Pipeline
# =============================================================================

async def execute_task(
    client,
    user_id: str,
    task_slug: str,
) -> dict:
    """Execute a single task — the complete pipeline from TASK.md to delivery.

    ADR-141: Mechanical pipeline. No decision-making. Called by scheduler
    when task is due (next_run_at <= now).

    Args:
        client: Supabase service client
        user_id: User UUID
        task_slug: Task slug (matches /tasks/{slug}/TASK.md)

    Returns:
        Result dict with task_slug, status, message
    """
    from services.task_workspace import TaskWorkspace
    from services.workspace import AgentWorkspace, UserMemory, get_agent_slug
    from services.agent_framework import has_asset_capabilities, has_capability

    started_at = datetime.now(timezone.utc)
    user_timezone = get_user_timezone(client, user_id)
    logger.info(f"[TASK_EXEC] Starting: {task_slug} for user {user_id[:8]}...")

    # =====================================================================
    # 0. Optimistic next_run_at bump — prevents scheduler re-pickup
    # The scheduler queries next_run_at <= now every 5 min. If execution
    # takes longer than 5 min, the task gets picked up again. Bump to
    # +2 hours as a sentinel; the real value is set at step 15.
    # =====================================================================
    try:
        sentinel = (started_at + timedelta(hours=2)).isoformat()
        client.table("tasks").update({
            "next_run_at": sentinel,
        }).eq("user_id", user_id).eq("slug", task_slug).execute()
    except Exception as e:
        logger.warning(f"[TASK_EXEC] Optimistic next_run_at bump failed: {e}")

    # =====================================================================
    # ADR-161: Daily-update empty-state branch
    # If this is the daily-update anchor task and the workspace is otherwise
    # empty (no other active tasks, no context entities), short-circuit with
    # a deterministic template — no LLM cost. The user still gets their
    # daily artifact in their inbox; it just honestly says "I have nothing
    # to tell you yet" with a CTA back to chat.
    # =====================================================================
    if task_slug == "daily-update":
        try:
            is_empty = await _is_workspace_empty_for_daily_update(client, user_id)
            if is_empty:
                empty_result = await _execute_daily_update_empty_state(
                    client, user_id, started_at, user_timezone=user_timezone
                )
                return empty_result
        except Exception as e:
            logger.warning(f"[TASK_EXEC] Empty-state check failed (non-fatal, falling through): {e}")

    try:
        # =====================================================================
        # 1. Read TASK.md
        # =====================================================================
        tw = TaskWorkspace(client, user_id, task_slug)
        task_md_content = await tw.read_task()
        if not task_md_content:
            return _fail(task_slug, "TASK.md not found")

        task_info = parse_task_md(task_md_content)

        # =====================================================================
        # 1b. Read DELIVERABLE.md + task memory (ADR-149)
        # =====================================================================
        deliverable_spec = await tw.read("DELIVERABLE.md") or ""
        steering_notes = await tw.read("memory/steering.md") or ""
        # ADR-181: feedback.md at task root (fallback to memory/feedback.md for migration)
        task_feedback_raw = await tw.read("feedback.md") or await tw.read("memory/feedback.md") or ""
        # Extract last 3 feedback entries for prompt injection (keep it concise)
        task_feedback = _extract_recent_feedback(task_feedback_raw, max_entries=3)

        # =====================================================================
        # 1c. Read mode from TASK.md (ADR-154 — single source of truth)
        # =====================================================================
        task_mode = task_info.get("mode", "recurring")

        # =====================================================================
        # 1d. Check for multi-step process (ADR-152: read from TASK.md, not registry)
        # =====================================================================
        process_steps = task_info.get("process_steps", [])
        if len(process_steps) > 1:
            # Multi-step process — delegate to process executor
            result = await _execute_pipeline(
                client, user_id, task_slug, tw, task_info, process_steps, started_at,
                deliverable_spec=deliverable_spec,
                steering_notes=steering_notes,
                task_feedback=task_feedback,
                task_mode=task_mode,
                user_timezone=user_timezone,
            )
            return result

        # Single-step execution (existing flow)
        agent_slug = task_info.get("agent_slug", "").strip()

        # ADR-188: For single-step tasks, read step instruction from TASK.md process
        # section first. This makes TP-composed step instructions work without registry.
        if process_steps:
            inline_instruction = process_steps[0].get("instruction", "")
            if inline_instruction:
                task_info.setdefault("objective", {})["step_instruction"] = inline_instruction

        # ADR-152: For single-step tasks, resolve agent from TASK.md process_steps
        if not agent_slug and process_steps:
            agent_ref = process_steps[0].get("agent_ref") or process_steps[0].get("agent_type", "")
            if agent_ref:
                roster = client.table("agents").select("slug, role").eq("user_id", user_id).execute()
                for a in (roster.data or []):
                    if a.get("slug") == agent_ref or a.get("role") == agent_ref:
                        agent_slug = a["slug"]
                        logger.info(f"[TASK_EXEC] Resolved agent {agent_slug} from TASK.md process")
                        break

        if not agent_slug:
            return _fail(task_slug, "No agent assigned in TASK.md")

        # =====================================================================
        # 2. Resolve agent from DB
        # =====================================================================
        agent_result = (
            client.table("agents")
            .select("*")
            .eq("user_id", user_id)
            .eq("slug", agent_slug)
            .limit(1)
            .execute()
        )
        if not agent_result.data:
            return _fail(task_slug, f"Agent '{agent_slug}' not found")
        agent = agent_result.data[0]
        agent_id = agent["id"]
        role = agent.get("role", "custom")
        scope = agent.get("scope", "cross_platform")
        title = task_info.get("title") or agent.get("title", "Untitled")

        logger.info(f"[TASK_EXEC] Agent: {agent_slug} (role={role}, scope={scope})")

        # =====================================================================
        # ADR-164: TP dispatch branch
        # If the task is owned by TP (role='thinking_partner'), it is a back
        # office task — scheduled maintenance work that TP executes on behalf
        # of the workspace itself. Back office tasks run a declared executor
        # (deterministic Python function today; LLM-backed prompt future) and
        # write a structured output. They do NOT consume user work credits,
        # do NOT create agent_runs rows, and do NOT go through the Sonnet
        # generation path. Same substrate (tasks, outputs folders, TASK.md),
        # different execution path.
        # =====================================================================
        if role == "thinking_partner":
            return await _execute_tp_task(
                client=client,
                user_id=user_id,
                task_slug=task_slug,
                task_info=task_info,
                agent=agent,
                agent_slug=agent_slug,
                tw=tw,
                started_at=started_at,
                user_timezone=user_timezone,
            )

        # =====================================================================
        # 3. Check balance (ADR-172)
        # =====================================================================
        try:
            from services.platform_limits import check_balance
            balance_ok, balance = check_balance(client, user_id)
            if not balance_ok:
                logger.info(f"[TASK_EXEC] Balance exhausted for user {user_id[:8]} (${balance:.4f})")
                return _fail(task_slug, "Usage balance exhausted")
        except Exception as e:
            logger.warning(f"[TASK_EXEC] Balance check failed (proceeding): {e}")

        # =====================================================================
        # 4. Create agent_runs record
        # =====================================================================
        from services.agent_execution import get_next_run_number, create_version_record
        next_version = await get_next_run_number(client, agent_id)
        version = await create_version_record(client, agent_id, next_version)
        version_id = version["id"]

        # =====================================================================
        # 5. Read agent workspace (AGENT.md, memory, preferences)
        # =====================================================================
        ws = AgentWorkspace(client, user_id, agent_slug)
        await ws.ensure_seeded(agent)

        ws_instructions = await ws.read("AGENT.md") or ""

        # ADR-143: feedback + methodology loaded via ws.load_context() in context gathering
        # User context (profile + preferences)
        user_context = _load_user_context(client, user_id)

        # =====================================================================
        # 6. Gather context (ADR-154: includes awareness + tracker)
        # =====================================================================
        context_text, context_meta = await gather_task_context(
            client, user_id, agent, agent_slug, task_info=task_info,
            task_slug=task_slug,
        )

        # =====================================================================
        # 6b. Prior state injection (ADR-173 Phase 2 — accumulation-first)
        # =====================================================================
        output_kind = task_info.get("output_kind", "")
        prior_output = ""
        prior_state_brief = ""

        if task_mode == "goal":
            # Goal mode: full prior output for revision ("you are revising this")
            prior_output = await tw.read("outputs/latest/output.md") or ""

        # For non-produces_deliverable tasks (which get the full compose brief in 6d):
        # inject a compact prior-state brief so agents know what exists before generating.
        # Applies to: accumulates_context, external_action, system_maintenance, and
        # produces_deliverable tasks without page_structure (fallback).
        # First run has no prior output — get_prior_state_brief() returns "" gracefully.
        if output_kind != "produces_deliverable":
            prior_state_brief = await tw.get_prior_state_brief()

        # =====================================================================
        # 6c. Detect phase from awareness.md (ADR-154)
        # =====================================================================
        task_phase = "steady"
        try:
            _awareness_check = await tw.read("awareness.md") or ""
            if "## Phase: bootstrap" in _awareness_check or "no prior cycles" in _awareness_check:
                task_phase = "bootstrap"
        except Exception:
            pass

        # =====================================================================
        # 6d. ADR-170: Generation brief + revision scope (produces_deliverable only)
        # =====================================================================
        generation_brief = ""
        prior_manifest = None   # ADR-173: also used at 12b for generation_gaps
        revision_scope = None   # ADR-173: also used at 12b for generation_gaps
        if output_kind == "produces_deliverable":
            from services.task_types import get_task_type
            type_key = task_info.get("type_key", "")
            task_type_def = get_task_type(type_key) if type_key else None
            # ADR-174 Phase 3: TASK.md page_structure takes precedence over registry
            _page_structure_6d = (
                task_info.get("page_structure")
                or (task_type_def.get("page_structure") if task_type_def else None)
            )
            if _page_structure_6d:

                # Read prior manifest for staleness detection + revision routing
                prior_manifest_content = await tw.read("outputs/latest/sys_manifest.json") or ""
                prior_manifest = None
                if prior_manifest_content:
                    from services.compose.manifest import read_manifest
                    prior_manifest = read_manifest(prior_manifest_content)

                # ADR-170 Phase 4: classify revision scope
                from services.compose.assembly import _query_domain_state
                from services.compose.revision import classify_revision_scope, build_revision_brief
                _context_reads_6d = task_info.get("context_reads", [])
                _domain_state_6d = await _query_domain_state(client, user_id, _context_reads_6d)
                # ADR-170 Gap 1: parse TP-forced sections from steering.md
                _forced_sections_6d = _parse_forced_sections(steering_notes)
                revision_scope = classify_revision_scope(
                    prior_manifest=prior_manifest,
                    page_structure=_page_structure_6d,
                    domain_state=_domain_state_6d,
                    forced_sections=_forced_sections_6d,
                )
                logger.info(
                    f"[COMPOSE] {task_slug}: revision_type={revision_scope.revision_type} "
                    f"stale={revision_scope.stale_sections} current={revision_scope.current_sections} "
                    f"forced={_forced_sections_6d}"
                )

                # Build generation brief (staleness signals already embedded via prior_manifest)
                from services.compose.assembly import build_generation_brief
                generation_brief = await build_generation_brief(
                    client=client,
                    user_id=user_id,
                    task_slug=task_slug,
                    task_info=task_info,
                    prior_manifest=prior_manifest,
                )

                # Prepend revision brief for section-scoped runs
                revision_preamble = build_revision_brief(
                    revision_scope=revision_scope,
                    prior_manifest=prior_manifest,
                    page_structure=_page_structure_6d,
                )
                if revision_preamble:
                    generation_brief = revision_preamble + "\n\n" + generation_brief

        # =====================================================================
        # 7. Build prompt and generate
        # =====================================================================
        system_prompt, user_message = build_task_execution_prompt(
            task_info=task_info,
            agent=agent,
            agent_instructions=ws_instructions,
            context=context_text,
            user_context=user_context,
            deliverable_spec=deliverable_spec,
            steering_notes=steering_notes,
            task_feedback=task_feedback,
            task_mode=task_mode,
            prior_output=prior_output,
            prior_state_brief=prior_state_brief,
            task_phase=task_phase,
            generation_brief=generation_brief,
        )

        # ADR-148: No SKILL.md injection, no RuntimeDispatch during headless generation.
        # Agent writes prose with inline data tables + mermaid blocks.
        # Post-generation render phase (render_inline_assets) handles chart/diagram rendering.

        # =====================================================================
        # ADR-182: Output-kind-aware tool surface
        # produces_deliverable tasks have all context pre-gathered (Phase A).
        # Agent only needs WriteFile (save output) + RuntimeDispatch (assets).
        # This eliminates 2-3 read-only tool rounds, ~50% input token savings.
        # accumulates_context / external_action keep full tool surface.
        # =====================================================================
        _tool_overrides = None
        _max_rounds_override = None
        if output_kind == "produces_deliverable" and task_phase != "bootstrap":
            from services.primitives.workspace import WRITE_FILE_TOOL
            from services.primitives.runtime_dispatch import RUNTIME_DISPATCH_TOOL
            _tool_overrides = [WRITE_FILE_TOOL, RUNTIME_DISPATCH_TOOL]
            _max_rounds_override = 2  # asset generation only
            logger.info(f"[TASK_EXEC] ADR-182: reduced tool surface for produces_deliverable ({task_slug})")

        # Generate via headless agent
        draft, usage, pending_renders, _tools_used, _tool_rounds = await _generate(
            client, user_id, agent, system_prompt, user_message, scope,
            task_phase=task_phase,
            task_slug=task_slug,
            output_kind=output_kind,
            tool_overrides=_tool_overrides,
            max_rounds_override=_max_rounds_override,
        )

        # Strip agent reflection before delivery (ADR-128/149)
        from services.agent_execution import _extract_agent_reflection
        draft, agent_reflection = _extract_agent_reflection(draft)

        # =====================================================================
        # 7b. Render inline assets — ADR-148 Phase 2 (tables→charts, mermaid→SVG)
        # =====================================================================
        rendered_assets = []
        try:
            from services.render_assets import render_inline_assets
            draft, rendered_assets = await render_inline_assets(draft, user_id)
        except Exception as e:
            logger.warning(f"[TASK_EXEC] Inline asset rendering failed (non-fatal): {e}")

        # =====================================================================
        # 8. Update agent_runs record with content
        # =====================================================================
        from services.agent_execution import update_version_for_delivery, SONNET_MODEL
        version_metadata = {
            "input_tokens": _total_input_tokens(usage),
            "output_tokens": usage.get("output_tokens", 0),
            "cache_read_input_tokens": usage.get("cache_read_input_tokens", 0),
            "cache_creation_input_tokens": usage.get("cache_creation_input_tokens", 0),
            "model": SONNET_MODEL,
            "task_slug": task_slug,
            "trigger_type": "scheduled",
            "tool_rounds": _tool_rounds,
            "tools_used": _tools_used,
        }
        await update_version_for_delivery(client, version_id, draft, metadata=version_metadata)

        # =====================================================================
        # 9. Save output to task workspace (mode-aware, ADR-149)
        # =====================================================================
        date_folder = started_at.strftime("%Y-%m-%dT%H%M")

        if task_mode == "goal":
            # Goal mode: archive prior output, write to latest/ (revision pattern)
            prior_latest = await tw.read("outputs/latest/output.md")
            if prior_latest:
                await tw.write(
                    f"outputs/{date_folder}/output.md", prior_latest,
                    summary=f"Archive prior version before revision",
                    tags=["output", "archive"],
                )
            await tw.write(
                "outputs/latest/output.md", draft,
                summary=f"Goal revision v{next_version}",
                tags=["output", "latest"],
            )
            task_output_folder = "latest"
        else:
            # Recurring + reactive: new dated folder + overwrite latest/
            task_output_folder = await tw.save_output(
                content=draft,
                agent_slug=agent_slug,
                manifest_data={
                    "version_id": str(version_id),
                    "version_number": next_version,
                    "tokens": usage,
                },
            )
            # Also write to latest/ for easy access
            try:
                await tw.write(
                    "outputs/latest/output.md", draft,
                    summary=f"Latest output v{next_version}",
                    tags=["output", "latest"],
                )
            except Exception:
                pass  # Non-critical

        # Also save to agent workspace (for agent's output history)
        agent_output_folder = None
        try:
            agent_output_folder = await ws.save_output(
                content=draft,
                run_id=str(version_id),
                agent_id=str(agent_id),
                version_number=next_version,
                role=role,
                rendered_files=pending_renders if pending_renders else None,
            )
        except Exception as e:
            logger.warning(f"[TASK_EXEC] Agent output folder write failed: {e}")

        # =====================================================================
        # 11. Post-run domain scan + awareness update (ADR-154)
        # =====================================================================
        run_duration = (datetime.now(timezone.utc) - started_at).total_seconds()
        await _post_run_domain_scan(
            client, user_id, task_slug, task_info, draft, next_version, started_at,
            tools_used=_tools_used,
            agent_reflection=agent_reflection,
            duration_s=run_duration,
            tool_rounds=_tool_rounds,
        )

        # =====================================================================
        # 12. Compose HTML + section partials + sys_manifest.json (ADR-177)
        # =====================================================================
        # _compose_and_persist() fixes the ordering bug: parse sections first,
        # then compose — render service receives section kinds, not flat markdown.
        # Also eliminates the agent-workspace→task-workspace copy seam.
        if task_output_folder:
            try:
                await _compose_and_persist(
                    client=client,
                    user_id=user_id,
                    task_slug=task_slug,
                    draft=draft,
                    task_info=task_info,
                    task_output_folder=task_output_folder,
                    pending_renders=pending_renders,
                    title=title,
                    next_version=next_version,
                    started_at=started_at,
                    prior_manifest=prior_manifest,
                    revision_scope=revision_scope,
                )
            except Exception as e:
                logger.warning(f"[TASK_EXEC] _compose_and_persist failed (non-fatal): {e}")

        # =====================================================================
        # 13. Deliver
        # =====================================================================
        final_status = "delivered"
        delivery_error = None

        delivery_target = task_info.get("delivery", "").strip()
        if delivery_target and agent_output_folder:
            try:
                from services.agent_execution import (
                    get_user_email,
                    normalize_destination_for_delivery,
                )
                from services.delivery import deliver_from_output_folder
                from services.supabase import get_service_client

                # Build destination from TASK.md delivery field
                destination = _parse_delivery_target(delivery_target, client, user_id)

                # ADR-183: inject commerce product_id for subscriber delivery
                if destination and destination.get("target") == "subscribers":
                    commerce_info = task_info.get("commerce", {})
                    if commerce_info.get("product_id"):
                        destination["product_id"] = commerce_info["product_id"]

                if destination:
                    delivery_result = await deliver_from_output_folder(
                        client=client,
                        user_id=user_id,
                        agent=agent,
                        output_folder=agent_output_folder,
                        agent_slug=agent_slug,
                        version_id=str(version_id),
                        version_number=next_version,
                        destination=destination,
                        task_slug=task_slug,
                    )
                    if delivery_result.status.value == "success":
                        now = datetime.now(timezone.utc).isoformat()
                        client.table("agent_runs").update({
                            "status": "delivered",
                            "delivered_at": now,
                            "delivery_status": "delivered",
                        }).eq("id", version_id).execute()
                    else:
                        final_status = "failed"
                        delivery_error = delivery_result.error_message
                        client.table("agent_runs").update({
                            "status": "failed",
                            "delivery_status": "failed",
                            "delivery_error": delivery_error,
                        }).eq("id", version_id).execute()
            except Exception as e:
                logger.error(f"[TASK_EXEC] Delivery failed: {e}")
                final_status = "failed"
                delivery_error = str(e)
                client.table("agent_runs").update({
                    "status": "failed",
                    "delivery_status": "failed",
                    "delivery_error": delivery_error,
                }).eq("id", version_id).execute()
        else:
            # No delivery configured — mark as delivered (content generated)
            now = datetime.now(timezone.utc).isoformat()
            client.table("agent_runs").update({
                "status": "delivered",
                "delivered_at": now,
            }).eq("id", version_id).execute()

        # =====================================================================
        # 14. Post-generation side effects (all non-fatal)
        # =====================================================================

        # Append to task run log (with agent reflection if available)
        try:
            log_entry = f"v{next_version} {final_status}"
            if delivery_error:
                log_entry += f" — {delivery_error}"
            if agent_reflection:
                confidence = agent_reflection.get("output_confidence", "unknown")
                # Extract level from "high — reason" format
                level = confidence.split("—")[0].split("–")[0].strip().lower() if confidence else "unknown"
                log_entry += f" | confidence={level}"
                # Include criteria eval if present
                criteria_met = agent_reflection.get("criteria_met")
                if criteria_met:
                    log_entry += f" | criteria: {criteria_met}"
            await tw.append_run_log(log_entry)
        except Exception:
            pass

        # ADR-154: Agent self-observation and reflection REMOVED from agent workspace.
        # Reflections are now folded into task awareness.md by _post_run_domain_scan().

        # Agent card (ADR-116)
        if final_status == "delivered":
            try:
                from services.agent_execution import _generate_agent_card
                await _generate_agent_card(client, user_id, agent, next_version)
            except Exception:
                pass

        # =====================================================================
        # 15. Update scheduling (ADR-154: phase-aware)
        # =====================================================================
        now = datetime.now(timezone.utc)
        try:
            # Read schedule from tasks table
            task_row = (
                client.table("tasks")
                .select("schedule")
                .eq("user_id", user_id)
                .eq("slug", task_slug)
                .limit(1)
                .execute()
            )
            schedule = (task_row.data[0]["schedule"] if task_row.data else None) or None

            next_run = calculate_next_run_at(
                schedule,
                last_run_at=now,
                user_timezone=user_timezone,
            ) if schedule else None

            update_data = {
                "last_run_at": now.isoformat(),
                # Always set next_run_at — either to next scheduled time or None
                # to clear the optimistic sentinel. Without this, on-demand/reactive
                # tasks with no schedule get re-picked by the scheduler when the
                # +2h sentinel expires.
                "next_run_at": next_run.isoformat() if next_run else None,
            }

            client.table("tasks").update(update_data).eq(
                "user_id", user_id
            ).eq("slug", task_slug).execute()
        except Exception as e:
            logger.warning(f"[TASK_EXEC] Schedule update failed: {e}")

        # =====================================================================
        # 16. Work units (ADR-164: task_executed activity_log write removed —
        # the agent_runs row IS the record of execution)
        # =====================================================================
        duration_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)

        # ADR-171: Record token spend for this task run
        try:
            from services.platform_limits import record_token_usage
            record_token_usage(
                client, user_id,
                caller="task_pipeline",
                model=SONNET_MODEL,
                input_tokens=version_metadata.get("input_tokens", 0),
                output_tokens=version_metadata.get("output_tokens", 0),
                ref_id=str(version_id),
                metadata={"task_slug": task_slug},
            )
        except Exception:
            pass

        logger.info(
            f"[TASK_EXEC] Complete: {task_slug} → {agent_slug} v{next_version} "
            f"{final_status} ({duration_ms}ms)"
        )

        # =====================================================================
        # ADR-179: Write task_complete system card if session active within 4h.
        # Zero LLM cost. TP reads content as conversation history on next turn.
        # Only for successfully delivered non-back-office tasks.
        # Skipped for: background-only tasks (daily-update), failed runs.
        # =====================================================================
        if final_status == "delivered" and task_slug != "daily-update" and not task_slug.startswith("back-office-"):
            try:
                from routes.chat import append_message as _append_message
                inactivity_cutoff = (datetime.now(timezone.utc) - timedelta(hours=4)).isoformat()
                session_row = (
                    client.table("chat_sessions")
                    .select("id")
                    .eq("user_id", user_id)
                    .eq("session_type", "thinking_partner")
                    .gte("updated_at", inactivity_cutoff)
                    .eq("status", "active")
                    .is_("agent_id", "null")
                    .order("updated_at", desc=True)
                    .limit(1)
                    .execute()
                )
                if session_row.data:
                    output_path = f"/tasks/{task_slug}/outputs/latest/"
                    await _append_message(
                        client=client,
                        session_id=session_row.data[0]["id"],
                        role="assistant",
                        content=(
                            f"{title} finished its run. "
                            f"Output is in /tasks/{task_slug}/outputs/latest/."
                        ),
                        metadata={
                            "system_card": "task_complete",
                            "task_slug": task_slug,
                            "task_title": title,
                            "output_path": output_path,
                            "run_at": datetime.now(timezone.utc).isoformat(),
                        },
                    )
            except Exception as card_err:
                logger.warning(f"[SYSTEM_CARD] task_complete write failed (non-fatal): {card_err}")

        return {
            "success": final_status == "delivered",
            "task_slug": task_slug,
            "agent_slug": agent_slug,
            "run_id": version_id,
            "version_number": next_version,
            "status": final_status,
            "duration_ms": duration_ms,
            "message": f"v{next_version} {final_status}" + (f": {delivery_error}" if delivery_error else ""),
        }

    except Exception as e:
        logger.error(f"[TASK_EXEC] Failed: {task_slug}: {e}")
        # Clear the optimistic sentinel so failed reactive tasks don't re-run
        try:
            task_row = client.table("tasks").select("schedule").eq(
                "user_id", user_id
            ).eq("slug", task_slug).limit(1).execute()
            schedule = (task_row.data[0]["schedule"] if task_row.data else None) or None
            next_run = calculate_next_run_at(
                schedule,
                last_run_at=datetime.now(timezone.utc),
                user_timezone=user_timezone,
            ) if schedule else None
            client.table("tasks").update({
                "next_run_at": next_run.isoformat() if next_run else None,
            }).eq("user_id", user_id).eq("slug", task_slug).execute()
        except Exception:
            pass  # Best-effort cleanup
        return _fail(task_slug, str(e))


# =============================================================================
# Multi-Step Process Execution (ADR-145 Gate 2)
# =============================================================================

async def _execute_pipeline(
    client,
    user_id: str,
    task_slug: str,
    tw,  # TaskWorkspace
    task_info: dict,
    process_steps: list,  # ADR-152: from TASK.md, not registry
    started_at,
    deliverable_spec: str = "",
    steering_notes: str = "",
    task_feedback: str = "",
    task_mode: str = "recurring",
    user_timezone: str = "UTC",
) -> dict:
    """Execute a multi-step process — sequential agent execution with handoffs.

    ADR-152: process_steps come from parsed TASK.md, not the task type registry.
    Each step has: {step, agent_ref, instruction}.

    Each process step:
    1. Resolve agent by slug or type from user's roster
    2. Gather step-specific context (agent workspace + prior step output)
    3. Generate with step instruction merged into task objective
    4. Save step output to /tasks/{slug}/outputs/{date}/step-{N}/

    ADR-149: Reads DELIVERABLE.md + steering + feedback. Mode-aware output write.
    Final step's output becomes the task deliverable.
    """
    from services.task_workspace import TaskWorkspace
    from services.workspace import AgentWorkspace
    from services.agent_framework import has_asset_capabilities, has_capability
    from services.agent_execution import (
        get_next_run_number, create_version_record,
        update_version_for_delivery, SONNET_MODEL,
        _extract_agent_reflection,
    )
    from services.platform_limits import check_balance, record_token_usage

    steps = process_steps  # ADR-152: from TASK.md, not registry
    title = task_info.get("title") or task_slug
    delivery_target = task_info.get("delivery", "").strip()

    logger.info(f"[PIPELINE] Starting {len(steps)}-step process for {task_slug} (type={task_info.get('type_key')})")

    # Write initial run status for frontend progress polling
    run_status = {
        "status": "running",
        "current_step": 0,
        "total_steps": len(steps),
        "completed_steps": [],
        "started_at": started_at.isoformat(),
    }
    try:
        await tw.write(
            f"outputs/{started_at.strftime('%Y-%m-%dT%H%M')}/status.json",
            json.dumps(run_status, indent=2),
            tags=["status"],
            lifecycle="ephemeral",
        )
    except Exception:
        pass  # Non-critical — progress is best-effort

    # Resolve all process agents upfront
    agents_result = (
        client.table("agents")
        .select("*")
        .eq("user_id", user_id)
        .execute()
    )
    all_agents = agents_result.data or []
    role_to_agent = {}
    slug_to_agent = {}
    for a in all_agents:
        r = a.get("role")
        s = a.get("slug")
        if r and r not in role_to_agent:
            role_to_agent[r] = a
        if s:
            slug_to_agent[s] = a

    # Check balance before starting (ADR-172)
    try:
        balance_ok, balance = check_balance(client, user_id)
        if not balance_ok:
            return _fail(task_slug, "Usage balance exhausted")
    except Exception as e:
        logger.warning(f"[PIPELINE] Balance check failed (proceeding): {e}")

    # Date folder for this run
    date_folder = started_at.strftime("%Y-%m-%dT%H%M")

    step_outputs: list[str] = []
    final_draft = ""
    final_agent = None
    final_agent_slug = ""
    final_role = ""
    total_usage = {"input_tokens": 0, "output_tokens": 0}
    all_renders: list = []

    for step_idx, step in enumerate(steps):
        step_num = step_idx + 1
        # ADR-152: Steps from TASK.md have agent_ref; registry steps have agent_type
        agent_ref = step.get("agent_ref") or step.get("agent_type", "")
        step_name = step["step"]
        step_instruction = step.get("instruction", "")
        # If instruction is empty (TASK.md may truncate), use generic template
        if not step_instruction:
            from services.task_types import STEP_INSTRUCTIONS
            step_instruction = STEP_INSTRUCTIONS.get(step_name, "")

        # Resolve agent: try slug first, then role/type
        agent = slug_to_agent.get(agent_ref) if agent_ref in slug_to_agent else role_to_agent.get(agent_ref)
        if not agent:
            logger.warning(f"[PIPELINE] Step {step_num} ({step_name}): no agent '{agent_ref}' — skipping")
            step_outputs.append(f"(Step {step_num} skipped: no {agent_ref} agent)")
            continue

        agent_slug = agent.get("slug", "")
        agent_id = agent["id"]
        role = agent.get("role", "custom")
        scope = agent.get("scope", "cross_platform")

        logger.info(f"[PIPELINE] Step {step_num}/{len(steps)}: {step_name} → {agent_slug} ({role})")

        # --- Gather context for this step ---
        ws = AgentWorkspace(client, user_id, agent_slug)
        await ws.ensure_seeded(agent)
        ws_instructions = await ws.read("AGENT.md") or ""
        user_context = _load_user_context(client, user_id)

        context_text, context_meta = await gather_task_context(
            client, user_id, agent, agent_slug, task_info=task_info,
            task_slug=task_slug,
        )

        # --- Build step-specific prompt ---
        # Merge step instruction into the task objective
        step_task_info = {**task_info}
        step_objective = dict(task_info.get("objective", {}))
        step_objective["step_instruction"] = step_instruction
        step_task_info["objective"] = step_objective

        # ADR-170: Generation brief + revision scope on derive-output step only
        step_generation_brief = ""
        if step_name == "derive-output" and task_info.get("output_kind") == "produces_deliverable":
            from services.task_types import get_task_type
            type_key = task_info.get("type_key", "")
            task_type_def = get_task_type(type_key) if type_key else None
            # ADR-174 Phase 3: TASK.md page_structure takes precedence over registry
            _ps = (
                task_info.get("page_structure")
                or (task_type_def.get("page_structure") if task_type_def else None)
            )
            if _ps:
                prior_manifest_content = await tw.read("outputs/latest/sys_manifest.json") or ""
                prior_manifest = None
                if prior_manifest_content:
                    from services.compose.manifest import read_manifest
                    prior_manifest = read_manifest(prior_manifest_content)
                from services.compose.assembly import build_generation_brief, _query_domain_state
                from services.compose.revision import classify_revision_scope, build_revision_brief
                _ds = await _query_domain_state(client, user_id, task_info.get("context_reads", []))
                # ADR-170 Gap 1: parse TP-forced sections from steering.md
                _forced_pipeline = _parse_forced_sections(steering_notes)
                rev_scope = classify_revision_scope(
                    prior_manifest=prior_manifest,
                    page_structure=_ps,
                    domain_state=_ds,
                    forced_sections=_forced_pipeline,
                )
                logger.info(
                    f"[COMPOSE] pipeline {task_slug} step={step_name}: "
                    f"revision_type={rev_scope.revision_type} stale={rev_scope.stale_sections} "
                    f"forced={_forced_pipeline}"
                )
                step_generation_brief = await build_generation_brief(
                    client=client,
                    user_id=user_id,
                    task_slug=task_slug,
                    task_info=task_info,
                    prior_manifest=prior_manifest,
                )
                rev_preamble = build_revision_brief(rev_scope, prior_manifest, _ps)
                if rev_preamble:
                    step_generation_brief = rev_preamble + "\n\n" + step_generation_brief

        system_prompt, user_message = build_task_execution_prompt(
            task_info=step_task_info,
            agent=agent,
            agent_instructions=ws_instructions,
            context=context_text,
            user_context=user_context,
            deliverable_spec=deliverable_spec,
            steering_notes=steering_notes if step_num == len(steps) else "",  # Only last step gets steering
            task_feedback=task_feedback if step_num == len(steps) else "",    # Only last step gets feedback
            task_mode=task_mode,
            generation_brief=step_generation_brief,
        )

        # Inject step-specific preamble — BEFORE gathered context for visibility
        step_preamble = f"\n\n## Process Step {step_num}/{len(steps)}: {step_name.title()}\n"
        step_preamble += f"Your role in this process: {step_instruction}\n"

        # ADR-151: Determine prior step type for diff-aware handoff
        prior_step_name = steps[step_idx - 1]["step"] if step_idx > 0 else ""
        is_after_context_update = prior_step_name == "update-context"

        if step_outputs:
            prior_output = step_outputs[-1]
            if is_after_context_update:
                # ADR-151: Diff-aware handoff — prior step was update-context
                step_preamble += (
                    f"\n## Context Update Changelog (from prior step)\n"
                    f"The following describes what changed in the workspace context this cycle. "
                    f"Your primary context is the accumulated workspace context (injected above). "
                    f"Use this changelog to emphasize WHAT'S NEW in your output — the reader "
                    f"has seen prior reports. Lead with changes, not stable context.\n\n"
                    f"{prior_output[:8000]}\n"
                )
            else:
                step_preamble += (
                    f"\n## Prior Step Output (YOUR PRIMARY INPUT)\n"
                    f"The following is the output from the previous step. "
                    f"This is your primary source material — your job is to TRANSFORM this research "
                    f"into the deliverable described above. Every finding, data point, and citation "
                    f"from this input should appear in your output (restructured, not copy-pasted). "
                    f"Do NOT conduct independent research that ignores this input. "
                    f"Do NOT produce a shorter output than this input — you are adding structure, "
                    f"formatting, and visual assets, not condensing.\n\n"
                    f"{prior_output[:8000]}\n"
                )
        elif step_num == 1:
            step_preamble += (
                "\nYou are the first step in a multi-step process. "
                "Your output will be the primary input for the next agent. "
                "Be thorough — include all findings, data points, and sources. "
                "The next agent cannot research further, only format what you provide.\n"
            )

        # Append to user message (after gathered context)
        user_message += step_preamble

        # --- Generate ---
        draft, usage, pending_renders, _tools_used, _tool_rounds = await _generate(
            client, user_id, agent, system_prompt, user_message, scope,
            task_slug=task_slug,
            output_kind=task_info.get("output_kind", "produces_deliverable"),
        )

        # Strip assessment
        draft, _ = _extract_agent_reflection(draft)

        total_usage["input_tokens"] += _total_input_tokens(usage)
        total_usage["output_tokens"] += usage.get("output_tokens", 0)
        all_renders.extend(pending_renders or [])

        step_outputs.append(draft)
        final_draft = draft
        final_agent = agent
        final_agent_slug = agent_slug
        final_role = role

        # Save step output
        try:
            step_path = f"outputs/{date_folder}/step-{step_num}/output.md"
            await tw.write(step_path, draft, summary=f"Step {step_num}: {step_name}", tags=["pipeline", "step"])
            step_manifest = {
                "step": step_num,
                "step_name": step_name,
                "agent_type": role,
                "agent_slug": agent_slug,
                "tokens": usage,
            }
            await tw.write(
                f"outputs/{date_folder}/step-{step_num}/manifest.json",
                json.dumps(step_manifest, indent=2),
                tags=["pipeline", "manifest"],
            )
        except Exception as e:
            logger.warning(f"[PIPELINE] Step output save failed: {e}")

        # ADR-171: Record token spend for this step
        try:
            record_token_usage(
                client, user_id,
                caller="task_pipeline",
                model=SONNET_MODEL,
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0),
                metadata={"task_slug": task_slug, "step": step_num, "step_name": step_name},
            )
        except Exception:
            pass

        # Update run status for frontend progress polling
        run_status["current_step"] = step_num
        run_status["completed_steps"].append({
            "step": step_num,
            "step_name": step_name,
            "agent_type": role,
            "agent_slug": agent_slug,
        })
        try:
            await tw.write(
                f"outputs/{date_folder}/status.json",
                json.dumps(run_status, indent=2),
                tags=["status"],
                lifecycle="ephemeral",
            )
        except Exception:
            pass

        logger.info(f"[PIPELINE] Step {step_num} complete ({usage.get('output_tokens', 0)} tokens)")

    # =====================================================================
    # Post-process: Save final output, compose, deliver
    # =====================================================================
    if not final_draft or not final_agent:
        return _fail(task_slug, "Process produced no output")

    # Render inline assets — ADR-148 Phase 2 (tables→charts, mermaid→SVG)
    rendered_assets = []
    try:
        from services.render_assets import render_inline_assets
        final_draft, rendered_assets = await render_inline_assets(final_draft, user_id)
    except Exception as e:
        logger.warning(f"[PIPELINE] Inline asset rendering failed (non-fatal): {e}")

    # Create agent_runs record for the final output
    agent_id = final_agent["id"]
    next_version = await get_next_run_number(client, agent_id)
    version = await create_version_record(client, agent_id, next_version)
    version_id = version["id"]

    version_metadata = {
        "input_tokens": total_usage["input_tokens"],
        "output_tokens": total_usage["output_tokens"],
        "cache_read_input_tokens": total_usage.get("cache_read_input_tokens", 0),
        "cache_creation_input_tokens": total_usage.get("cache_creation_input_tokens", 0),
        "model": SONNET_MODEL,
        "task_slug": task_slug,
        "type_key": task_info.get("type_key"),
        "process_steps": len(steps),
        "trigger_type": "scheduled",
    }
    await update_version_for_delivery(client, version_id, final_draft, metadata=version_metadata)

    # Mark run status as completed for frontend progress polling
    run_status["status"] = "completed"
    run_status["completed_at"] = datetime.now(timezone.utc).isoformat()
    try:
        await tw.write(
            f"outputs/{date_folder}/status.json",
            json.dumps(run_status, indent=2),
            tags=["status"],
            lifecycle="ephemeral",
        )
    except Exception:
        pass

    # Save final output to task workspace (mode-aware, ADR-149)
    if task_mode == "goal":
        # Goal: archive prior, write to latest/
        prior_latest = await tw.read("outputs/latest/output.md")
        if prior_latest:
            await tw.write(
                f"outputs/{date_folder}/output.md", prior_latest,
                summary="Archive prior version before revision",
                tags=["output", "archive"],
            )
        await tw.write(
            "outputs/latest/output.md", final_draft,
            summary=f"Goal revision v{next_version}",
            tags=["output", "latest"],
        )
        task_output_folder = date_folder
    else:
        # Recurring + reactive: new dated folder + overwrite latest/
        task_output_folder = await tw.save_output(
            content=final_draft,
            agent_slug=final_agent_slug,
            date_folder=date_folder,
            manifest_data={
                "version_id": str(version_id),
                "version_number": next_version,
                "type_key": task_info.get("type_key"),
                "process_steps": len(steps),
                "tokens": total_usage,
            },
        )
        try:
            await tw.write(
                "outputs/latest/output.md", final_draft,
                summary=f"Latest output v{next_version}",
                tags=["output", "latest"],
            )
        except Exception:
            pass

    # Save to agent workspace
    ws = AgentWorkspace(client, user_id, final_agent_slug)
    agent_output_folder = None
    try:
        agent_output_folder = await ws.save_output(
            content=final_draft,
            run_id=str(version_id),
            agent_id=str(agent_id),
            version_number=next_version,
            role=final_role,
            rendered_files=all_renders if all_renders else None,
        )
    except Exception as e:
        logger.warning(f"[PIPELINE] Agent output folder write failed: {e}")

    # Post-run domain scan + awareness update (ADR-154)
    pipeline_duration = (datetime.now(timezone.utc) - started_at).total_seconds()
    await _post_run_domain_scan(
        client, user_id, task_slug, task_info, final_draft, next_version, started_at,
        duration_s=pipeline_duration,
    )

    # Compose HTML + section partials + sys_manifest.json (ADR-177)
    # _compose_and_persist() fixes ordering: parse sections FIRST, then compose.
    try:
        await _compose_and_persist(
            client=client,
            user_id=user_id,
            task_slug=task_slug,
            draft=final_draft,
            task_info=task_info,
            task_output_folder=f"outputs/{date_folder}",
            pending_renders=all_renders,
            title=title,
            next_version=next_version,
            started_at=started_at,
            prior_manifest=None,       # multi-agent path: no prior manifest in scope
            revision_scope="full",     # multi-agent path: always full regeneration
        )
    except Exception as e:
        logger.warning(f"[PIPELINE] _compose_and_persist failed (non-fatal): {e}")

    # Deliver
    final_status = "delivered"
    delivery_error = None

    if delivery_target and agent_output_folder:
        try:
            from services.delivery import deliver_from_output_folder
            destination = _parse_delivery_target(delivery_target, client, user_id)

            # ADR-183: inject commerce product_id for subscriber delivery
            if destination and destination.get("target") == "subscribers":
                commerce_info = task_info.get("commerce", {})
                if commerce_info.get("product_id"):
                    destination["product_id"] = commerce_info["product_id"]

            if destination:
                delivery_result = await deliver_from_output_folder(
                    client=client, user_id=user_id, agent=final_agent,
                    output_folder=agent_output_folder, agent_slug=final_agent_slug,
                    version_id=str(version_id), version_number=next_version,
                    destination=destination, task_slug=task_slug,
                )
                if delivery_result.status.value == "success":
                    now = datetime.now(timezone.utc).isoformat()
                    client.table("agent_runs").update({
                        "status": "delivered", "delivered_at": now, "delivery_status": "delivered",
                    }).eq("id", version_id).execute()
                else:
                    final_status = "failed"
                    delivery_error = delivery_result.error_message
        except Exception as e:
            final_status = "failed"
            delivery_error = str(e)
    else:
        now = datetime.now(timezone.utc).isoformat()
        client.table("agent_runs").update({
            "status": "delivered", "delivered_at": now,
        }).eq("id", version_id).execute()

    if final_status == "failed":
        client.table("agent_runs").update({
            "status": "failed", "delivery_status": "failed", "delivery_error": delivery_error,
        }).eq("id", version_id).execute()

    # Run log
    try:
        process_summary = " → ".join(s["step"] for s in steps)
        log_entry = f"v{next_version} {final_status} ({process_summary})"
        if delivery_error:
            log_entry += f" — {delivery_error}"
        await tw.append_run_log(log_entry)
    except Exception:
        pass

    # Update scheduling
    now = datetime.now(timezone.utc)
    try:
        task_row = (
            client.table("tasks").select("schedule")
            .eq("user_id", user_id).eq("slug", task_slug).limit(1).execute()
        )
        schedule = (task_row.data[0]["schedule"] if task_row.data else None) or None
        next_run = calculate_next_run_at(
            schedule,
            last_run_at=now,
            user_timezone=user_timezone,
        ) if schedule else None
        update_data = {
            "last_run_at": now.isoformat(),
            "next_run_at": next_run.isoformat() if next_run else None,
        }
        client.table("tasks").update(update_data).eq("user_id", user_id).eq("slug", task_slug).execute()
    except Exception as e:
        logger.warning(f"[PIPELINE] Schedule update failed: {e}")

    # ADR-164: task_executed activity_log write removed. agent_runs row +
    # task outputs folder + tasks.last_run_at are the authoritative record.
    duration_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)

    logger.info(
        f"[PIPELINE] Complete: {task_slug} → {len(steps)} steps, v{next_version} "
        f"{final_status} ({duration_ms}ms, {total_usage['input_tokens']+total_usage['output_tokens']} tokens)"
    )

    return {
        "success": final_status == "delivered",
        "task_slug": task_slug,
        "type_key": task_info.get("type_key"),
        "process_steps": len(steps),
        "agent_slug": final_agent_slug,
        "run_id": version_id,
        "version_number": next_version,
        "status": final_status,
        "duration_ms": duration_ms,
        "message": f"v{next_version} {final_status} ({len(steps)} steps)",
    }


# =============================================================================
# Generation (reuses headless agent loop from agent_execution)
# =============================================================================


def _microcompact_tool_history(messages: list[dict], keep_recent: int = 3) -> None:
    """Clear old tool results from message history to prevent geometric growth.

    CC-style microcompact: walks the message history and replaces tool_result
    content older than the last N results with a stub. The model retains the
    tool_use_id linkage (so it knows a tool was called) but doesn't re-process
    the full content on subsequent rounds.

    Mutates messages in place. Only touches tool_result blocks in user messages.
    """
    # Collect all tool_result positions (in order, oldest first)
    positions = []  # (msg_idx, block_idx)
    for i, msg in enumerate(messages):
        if msg.get("role") != "user" or not isinstance(msg.get("content"), list):
            continue
        for j, block in enumerate(msg["content"]):
            if isinstance(block, dict) and block.get("type") == "tool_result":
                positions.append((i, j))

    # Clear all except the most recent N
    to_clear = positions[:-keep_recent] if len(positions) > keep_recent else []
    for msg_idx, block_idx in to_clear:
        block = messages[msg_idx]["content"][block_idx]
        # Only clear if not already cleared
        if block.get("content") != "[Prior tool result cleared]":
            block["content"] = "[Prior tool result cleared]"


# Scope → max tool rounds (steady state)
_TOOL_ROUNDS = {
    "platform": 5,
    "cross_platform": 8,
    "knowledge": 8,
    "research": 10,
    "autonomous": 12,
}

# ADR-154: Bootstrap multiplier — first run is deep research (journalist model).
# Phase affects depth (tool rounds), not frequency (schedule).
_BOOTSTRAP_ROUND_MULTIPLIER = 2  # 2x rounds during bootstrap


async def _generate(
    client,
    user_id: str,
    agent: dict,
    system_prompt: str,
    user_message: str,
    scope: str,
    task_phase: str = "steady",
    task_slug: str = "",
    output_kind: str = "produces_deliverable",
    tool_overrides: Optional[list[dict]] = None,
    max_rounds_override: Optional[int] = None,
) -> tuple[str, dict, list, list, int]:
    """Run the headless generation loop.

    Returns (draft, usage, pending_renders, tools_used, tool_rounds).
    ADR-154: tools_used and tool_rounds returned for awareness.md.
    output_kind: used to tune microcompact aggressiveness. accumulates_context
    tasks make many small tool writes so keep_recent=2 keeps history lean.
    produces_deliverable tasks benefit from keep_recent=3 for richer synthesis context.

    ADR-182: tool_overrides and max_rounds_override allow callers to pass a
    reduced tool surface for produces_deliverable tasks where all context is
    pre-gathered mechanically. When set, these override the default full
    headless tool set and scope-based round limits.
    """
    from services.anthropic import chat_completion_with_tools
    from services.primitives.registry import get_headless_tools_for_agent, create_headless_executor
    from services.agent_pipeline import validate_output
    from services.agent_execution import (
        SONNET_MODEL, _is_narration, _strip_tool_narration,
    )

    role = agent.get("role", "custom")

    if max_rounds_override is not None:
        max_tool_rounds = max_rounds_override
    else:
        max_tool_rounds = _TOOL_ROUNDS.get(scope, 5)

        # ADR-154: Bootstrap phase gets 2x tool rounds — deep research on first run
        if task_phase == "bootstrap":
            max_tool_rounds = max_tool_rounds * _BOOTSTRAP_ROUND_MULTIPLIER

        # Agents with asset capabilities (chart, mermaid, image) need more rounds
        from services.agent_framework import has_asset_capabilities
        if has_asset_capabilities(role):
            max_tool_rounds = max(max_tool_rounds, 6)

    if tool_overrides is not None:
        # ADR-182: caller provided a reduced tool surface (e.g., synthesis-only)
        headless_tools = tool_overrides
    else:
        headless_tools = await get_headless_tools_for_agent(
            client, user_id, agent=agent, agent_sources=[],
        )
    executor = create_headless_executor(
        client, user_id,
        agent_sources=[],
        agent=agent,
        dynamic_tools=headless_tools,
        task_slug=task_slug or None,
    )

    # Split user_message into task-instructions + context blocks so Anthropic prompt
    # caching can cache the large context section across tool rounds within this
    # execution and across repeated runs of the same task (context is stable until
    # a new cycle writes to /workspace/context/). Without this, 100-200K tokens of
    # domain context are re-billed as fresh input on every tool round.
    #
    # Split point: "## Gathered Context" is always the last section of user_message.
    # Everything before it is task-specific (objective, criteria, steering) — small
    # and changes each run. Everything from it onward is accumulated workspace
    # context — large, stable, and the primary caching target.
    _CONTEXT_MARKER = "\n## Gathered Context\n"
    _split_idx = user_message.find(_CONTEXT_MARKER)
    if _split_idx != -1:
        _instructions_part = user_message[:_split_idx]
        _context_part = user_message[_split_idx:]
        _initial_content: list[dict] = [
            {"type": "text", "text": _instructions_part},
            {"type": "text", "text": _context_part, "cache_control": {"type": "ephemeral"}},
        ]
    else:
        # No context section found — send as single block (shouldn't happen in normal flow)
        _initial_content = [{"type": "text", "text": user_message}]

    messages = [{"role": "user", "content": _initial_content}]
    tools_used = []
    total_input_tokens = 0
    total_output_tokens = 0
    total_cache_read = 0
    total_cache_create = 0
    draft = ""

    # accumulates_context tasks make many small sequential writes (ReadFile → WriteFile
    # per entity). keeping only 2 recent results is sufficient and cuts re-sent history
    # faster. produces_deliverable tasks synthesize across results so 3 gives richer context.
    _microcompact_keep = 2 if output_kind == "accumulates_context" else 3

    for round_num in range(max_tool_rounds + 1):
        # Microcompact: clear old tool results from history before each call.
        # Without this, 13 rounds of WebSearch accumulate geometrically —
        # each round re-sends ALL prior results. With microcompact, only
        # the most recent results are kept; older ones become stubs.
        # CC uses the same pattern (maybeTimeBasedMicrocompact).
        if round_num >= 2:
            _microcompact_tool_history(messages, keep_recent=_microcompact_keep)

        response = await chat_completion_with_tools(
            messages=messages,
            system=system_prompt,
            tools=headless_tools,
            model=SONNET_MODEL,
            max_tokens=4000,
        )

        if response.usage:
            total_input_tokens += _total_input_tokens(response.usage)
            total_output_tokens += response.usage.get("output_tokens", 0)
            total_cache_read += response.usage.get("cache_read_input_tokens", 0)
            total_cache_create += response.usage.get("cache_creation_input_tokens", 0)

        # Agent finished
        if response.stop_reason in ("end_turn", "max_tokens") or not response.tool_uses:
            draft = response.text.strip()
            if round_num > 0:
                logger.info(f"[TASK_EXEC] Agent used {round_num} tool round(s): {', '.join(tools_used)}")
            break

        # Hit tool round limit
        if round_num >= max_tool_rounds:
            candidate = response.text.strip() if response.text else ""
            if candidate and not _is_narration(candidate):
                draft = candidate
                break

            # Force final synthesis
            messages.append({"role": "assistant", "content": response.text or ""})
            messages.append({"role": "user", "content": "You have reached the tool limit. Synthesize all gathered information and produce the final output now."})
            final_response = await chat_completion_with_tools(
                messages=messages,
                system=system_prompt,
                tools=[],
                model=SONNET_MODEL,
                max_tokens=4000,
            )
            if final_response.usage:
                total_input_tokens += _total_input_tokens(final_response.usage)
                total_output_tokens += final_response.usage.get("output_tokens", 0)
            draft = final_response.text.strip() if final_response.text else ""
            break

        # Execute tools
        assistant_content = []
        if response.text:
            assistant_content.append({"type": "text", "text": response.text})
        for tu in response.tool_uses:
            assistant_content.append({
                "type": "tool_use",
                "id": tu.id,
                "name": tu.name,
                "input": tu.input,
            })
        messages.append({"role": "assistant", "content": assistant_content})

        tool_results = []
        for tu in response.tool_uses:
            tools_used.append(tu.name)
            logger.info(f"[TASK_EXEC] Tool: {tu.name}({str(tu.input)[:100]})")
            result = await executor(tu.name, tu.input)
            # Truncate tool results to prevent context blowup across rounds.
            # Without truncation, 13 WebSearch rounds accumulate ~800K+ tokens
            # because each round re-sends all prior results in full.
            from services.anthropic import _truncate_tool_result
            truncated = _truncate_tool_result(
                result, max_items=10, max_content_len=2000, max_depth=4
            )
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tu.id,
                "content": truncated,
            })
        messages.append({"role": "user", "content": tool_results})
    else:
        draft = ""

    if not draft:
        raise ValueError("Agent produced empty draft")

    draft = _strip_tool_narration(draft)
    if not draft:
        raise ValueError("Agent produced only tool-use narration")

    # Retry if critically short
    if len(draft.split()) < 20:
        messages.append({"role": "assistant", "content": draft})
        messages.append({"role": "user", "content": (
            "Your output was too short. Produce the full content in the requested format now."
        )})
        retry_response = await chat_completion_with_tools(
            messages=messages, system=system_prompt, tools=[], model=SONNET_MODEL, max_tokens=4000,
        )
        if retry_response.usage:
            total_input_tokens += _total_input_tokens(retry_response.usage)
            total_output_tokens += retry_response.usage.get("output_tokens", 0)
        retry_draft = (retry_response.text or "").strip()
        if len(retry_draft.split()) > len(draft.split()):
            draft = retry_draft

    usage = {
        "input_tokens": total_input_tokens,
        "output_tokens": total_output_tokens,
        "cache_read_input_tokens": total_cache_read,
        "cache_creation_input_tokens": total_cache_create,
    }

    # Collect rendered files from RuntimeDispatch
    pending_renders = getattr(executor, "auth", None)
    pending_renders = getattr(pending_renders, "pending_renders", []) if pending_renders else []

    return draft, usage, pending_renders, tools_used, round_num


# =============================================================================
# Helpers
# =============================================================================

def _load_user_context(client, user_id: str) -> Optional[str]:
    """Load user context from workspace files and return as prompt-ready text.

    Reads IDENTITY.md, style.md, notes.md, and BRAND.md from workspace,
    renders directly into prompt sections. No intermediate key-value layer.
    """
    try:
        from services.workspace import UserMemory
        um = UserMemory(client, user_id)
        memory_files = um.read_all_sync()
        sections: list[str] = []

        # Identity (IDENTITY.md → profile fields)
        profile = UserMemory._parse_memory_md(memory_files.get("IDENTITY.md"))
        profile_lines = [f"- {k.title()}: {v}" for k, v in profile.items() if v]
        if profile_lines:
            sections.append("## User Context\n" + "\n".join(profile_lines))

        # Preferences (style.md → tone/verbosity per platform)
        prefs = UserMemory._parse_preferences_md(memory_files.get("style.md"))
        pref_lines = []
        for platform, settings in prefs.items():
            if settings.get("tone"):
                pref_lines.append(f"- {platform.title()} Tone: {settings['tone']}")
            if settings.get("verbosity"):
                pref_lines.append(f"- {platform.title()} Verbosity: {settings['verbosity']}")
        # Standing notes (notes.md → top 5 facts/preferences)
        notes = UserMemory._parse_notes_md(memory_files.get("notes.md"))
        for note in notes[:5]:
            pref_lines.append(f"- Prefers: {note['content']}")
        if pref_lines:
            sections.append("## Preferences\n" + "\n".join(pref_lines))

        # Brand (BRAND.md → raw content)
        brand = memory_files.get("BRAND.md", "").strip()
        if brand:
            sections.append("## Brand Guidelines\n" + brand)

        return "\n\n".join(sections) if sections else None
    except Exception as e:
        logger.warning(f"[TASK_EXEC] User context load failed: {e}")
        return None


# =============================================================================
# ADR-164: TP Task Execution Branch (Back Office Tasks)
# =============================================================================
#
# When the task pipeline resolves an agent and discovers its role is
# `thinking_partner`, the work is a back office task — scheduled maintenance
# owned by the meta-cognitive agent. Back office tasks run a declared
# executor rather than the normal Sonnet generation path.
#
# The executor is declared in the task's TASK.md ## Process section by
# embedding `executor: <dotted.path.to.module>` in the step instruction.
# `_execute_tp_task()` extracts that reference, imports the module, calls
# its `run(client, user_id, task_slug)` async function, and writes the
# returned output to the standard task outputs folder.
#
# Back office tasks do NOT consume user work credits (they're system
# maintenance), do NOT create agent_runs rows, and do NOT go through LLM
# generation. They write the same output.md + manifest.json + run_log.md
# artifacts as regular tasks, so the /work surface renders them identically.

_EXECUTOR_DIRECTIVE_RE = re.compile(
    r"executor:\s*([a-zA-Z_][a-zA-Z0-9_.]*)", re.IGNORECASE
)


def _extract_executor_path(task_info: dict) -> Optional[str]:
    """Find the `executor:` directive in the task's process step instructions.

    Back office tasks embed `executor: services.back_office.agent_hygiene`
    (or similar) in the process step's instruction text. This function
    returns the first match, or None if no executor is declared.
    """
    process_steps = task_info.get("process_steps", [])
    for step in process_steps:
        instruction = step.get("instruction", "") or ""
        match = _EXECUTOR_DIRECTIVE_RE.search(instruction)
        if match:
            return match.group(1)
    return None


async def _execute_tp_task(
    client,
    user_id: str,
    task_slug: str,
    task_info: dict,
    agent: dict,
    agent_slug: str,
    tw,  # TaskWorkspace (already constructed by caller)
    started_at: datetime,
    user_timezone: str = "UTC",
) -> dict:
    """Execute a back office task (ADR-164).

    The task's process step declares an executor path via `executor: <dotted.path>`.
    This function imports the module, calls its `run(client, user_id, task_slug)`
    function, and writes the returned output to the standard task outputs folder.

    Returns the same shape as the regular pipeline's return value.
    """
    import importlib
    import json as _json
    from services.task_workspace import TaskWorkspace  # type: ignore

    executor_path = _extract_executor_path(task_info)
    if not executor_path:
        return _fail(
            task_slug,
            "Back office task has no executor declared. "
            "Add `executor: <module.path>` to the process step instruction in TASK.md."
        )

    # Import the executor module
    try:
        module = importlib.import_module(executor_path)
    except ImportError as e:
        return _fail(task_slug, f"Executor module not found: {executor_path} ({e})")

    if not hasattr(module, "run") or not callable(module.run):
        return _fail(
            task_slug,
            f"Executor module {executor_path} missing async `run(client, user_id, task_slug)` function"
        )

    logger.info(f"[TASK_EXEC:TP] {task_slug} → {executor_path}")

    # Run the executor
    try:
        result = await module.run(client, user_id, task_slug)
    except Exception as e:
        logger.error(f"[TASK_EXEC:TP] Executor {executor_path} raised: {e}")
        return _fail(task_slug, f"Executor {executor_path} failed: {e}")

    if not isinstance(result, dict) or "output_markdown" not in result:
        return _fail(
            task_slug,
            f"Executor {executor_path} returned invalid shape (expected dict with output_markdown)"
        )

    summary = result.get("summary", "Back office task completed.")
    output_markdown = result["output_markdown"]
    actions_taken = result.get("actions_taken", [])

    # Write output to standard task outputs folder
    date_folder = started_at.strftime("%Y-%m-%dT%H00")
    folder_path = f"outputs/{date_folder}"

    try:
        await tw.write(
            f"{folder_path}/output.md",
            output_markdown,
            summary=summary,
            tags=["output", "back_office", agent_slug],
        )

        manifest = {
            "agent_slug": agent_slug,
            "created_at": started_at.isoformat(),
            "status": "active",
            "kind": "back_office",
            "executor": executor_path,
            "actions_taken": actions_taken,
            "files": [
                {"path": "output.md", "type": "text/markdown", "role": "primary"},
            ],
        }
        await tw.write(
            f"{folder_path}/manifest.json",
            _json.dumps(manifest, indent=2),
            summary=f"Back office manifest — {executor_path}",
            tags=["manifest", "back_office"],
        )
    except Exception as e:
        logger.warning(f"[TASK_EXEC:TP] Output write failed (non-fatal): {e}")

    # Append to run log
    try:
        await tw.append_run_log(f"back_office executor={executor_path} — {summary}")
    except Exception:
        pass

    # Update task scheduling: last_run_at = now, next_run_at = next cadence
    now = datetime.now(timezone.utc)
    schedule = task_info.get("schedule", "")
    try:
        next_run = calculate_next_run_at(
            schedule,
            last_run_at=now,
            user_timezone=user_timezone,
        ) if schedule else None
        client.table("tasks").update({
            "last_run_at": now.isoformat(),
            "next_run_at": next_run.isoformat() if next_run else None,
            "updated_at": now.isoformat(),
        }).eq("user_id", user_id).eq("slug", task_slug).execute()
    except Exception as e:
        logger.warning(f"[TASK_EXEC:TP] next_run_at update failed: {e}")

    duration_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)
    logger.info(f"[TASK_EXEC:TP] {task_slug} done ({duration_ms}ms) — {summary}")

    return {
        "success": True,
        "task_slug": task_slug,
        "status": "completed",
        "message": summary,
        "kind": "back_office",
        "executor": executor_path,
        "actions_taken": actions_taken,
    }


def _parse_delivery_target(delivery_str: str, client, user_id: str) -> Optional[dict]:
    """Parse TASK.md delivery field into destination dict.

    Supports:
    - Email: "user@example.com" → {"platform": "email", "target": "...", "format": "send"}
    - Slack: "slack:#channel" → {"platform": "slack", "target": "#channel", "format": "send"}
    - None/empty → email fallback
    """
    if not delivery_str or delivery_str.strip().lower() == "none":
        return None  # No delivery configured — task runs silently

    # "email" without address → resolve to user's email
    if delivery_str.strip().lower() == "email":
        from services.agent_execution import get_user_email
        from services.supabase import get_service_client
        email = get_user_email(get_service_client(), user_id)
        if email:
            return {"platform": "email", "target": email, "format": "send"}
        return None

    if "@" in delivery_str and not delivery_str.startswith("slack:"):
        return {"platform": "email", "target": delivery_str, "format": "send"}

    if delivery_str.startswith("slack:"):
        target = delivery_str[6:]
        return {"platform": "slack", "target": target, "format": "send"}

    # ADR-183 Phase 2: "subscribers" delivery target
    # Resolves subscriber emails live from commerce provider at delivery time
    if delivery_str.strip().lower() == "subscribers":
        dest = {"platform": "email", "target": "subscribers", "format": "send"}
        # product_id injected by caller from task_info["commerce"]["product_id"]
        return dest

    # Unknown delivery format — don't guess, return None
    logger.warning(f"[TASK_EXEC] Unknown delivery format: '{delivery_str}' — skipping")
    return None


def _fail(task_slug: str, message: str) -> dict:
    """Build failure result."""
    logger.error(f"[TASK_EXEC] {task_slug}: {message}")
    return {
        "success": False,
        "task_slug": task_slug,
        "status": "failed",
        "message": message,
    }


# =============================================================================
# ADR-161: Daily Update Empty-State Branch
# =============================================================================

async def _is_workspace_empty_for_daily_update(client, user_id: str) -> bool:
    """Check whether the workspace has anything for daily-update to summarize.

    Empty when:
      - No active tasks other than daily-update itself
      - No context entities (no _tracker rows in any context domain)

    Pure SQL — no LLM cost. Used to short-circuit daily-update execution
    in the empty-state branch (ADR-161). When true, the pipeline emits a
    deterministic call-to-action template instead of running an LLM call
    to summarize nothing.
    """
    try:
        # 1. Other active tasks?
        other_tasks = (
            client.table("tasks")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .eq("status", "active")
            .neq("slug", "daily-update")
            .execute()
        )
        if (other_tasks.count or 0) > 0:
            return False

        # 2. Any context-domain entity files?
        # Entity files live at /workspace/context/{domain}/{entity}/*.md
        # The cheapest signal is "any non-tracker, non-synthesis file under context/"
        context_files = (
            client.table("workspace_files")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .like("path", "/workspace/context/%")
            .not_.like("path", "%/_tracker.md")
            .not_.like("path", "%/_landscape.md")
            .not_.like("path", "%/.gitkeep")
            .execute()
        )
        if (context_files.count or 0) > 0:
            return False

        return True
    except Exception as e:
        logger.warning(f"[TASK_EXEC] Empty workspace check failed: {e}")
        # On error, fall through to normal pipeline (safer than mis-emitting empty)
        return False


def _build_empty_workspace_html(schedule_label: str) -> str:
    """Deterministic HTML template for the empty-workspace daily-update.

    No LLM call. No personalization. Honest acknowledgement that the workspace
    is empty plus a call-to-action back to chat. The user still gets their
    daily artifact in the inbox; it just says "I have nothing to tell you yet."
    """
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Your YARNNN workforce is ready</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 640px; margin: 32px auto; padding: 0 24px; color: #374151; line-height: 1.6;">
  <h1 style="color: #1a1a2e; font-size: 24px; margin-bottom: 16px;">Your workforce is ready</h1>
  <p>Good morning. I'm <strong>Reporting</strong>, your synthesizer agent. I send you a daily operational digest of what your workforce is doing.</p>
  <p>Right now, there's nothing for me to report — your team hasn't been told what to track yet. That's by design: I don't presume to know what matters to you until you tell me.</p>
  <p style="margin-top: 24px;">
    <a href="https://yarnnn.com/chat" style="display: inline-block; padding: 10px 18px; background: #3b82f6; color: #ffffff; text-decoration: none; border-radius: 6px; font-weight: 600;">Open a chat with me</a>
  </p>
  <p style="margin-top: 16px;">Tell me about your work — what you're focused on, who you're tracking, what platforms you use. I'll set up tracking, kick off research, and tomorrow's update will have something real to say.</p>
  <hr style="margin: 32px 0; border: 0; border-top: 1px solid #e5e7eb;">
  <p style="color: #6b7280; font-size: 13px;">This is your daily update from YARNNN. It runs every morning at {schedule_label}. You can adjust the cadence or pause it from chat anytime.</p>
</body>
</html>"""


def _build_empty_workspace_markdown(schedule_label: str) -> str:
    """Markdown counterpart of the empty-workspace template (for output.md)."""
    return (
        "# Your workforce is ready\n\n"
        "Good morning. I'm **Reporting**, your synthesizer agent. I send you "
        "a daily operational digest of what your workforce is doing.\n\n"
        "Right now, there's nothing for me to report — your team hasn't been "
        "told what to track yet. That's by design: I don't presume to know "
        "what matters to you until you tell me.\n\n"
        "[Open a chat with me](https://yarnnn.com/chat)\n\n"
        "Tell me about your work — what you're focused on, who you're tracking, "
        "what platforms you use. I'll set up tracking, kick off research, and "
        "tomorrow's update will have something real to say.\n\n"
        "---\n\n"
        "*This is your daily update from YARNNN. It runs every morning at "
        f"{schedule_label}. You can adjust the cadence or pause it from chat anytime.*\n"
    )


async def _execute_daily_update_empty_state(
    client,
    user_id: str,
    started_at: datetime,
    user_timezone: str = "UTC",
) -> dict:
    """Empty-state execution path for the daily-update anchor task.

    ADR-161: Deterministic, zero LLM. Writes the template to the task's
    outputs folder, delivers via the standard delivery rail, updates
    next_run_at to the next local morning cadence and returns a success result.

    The output is co-located with normal runs in /tasks/daily-update/outputs/{date}/
    so the surface treats it identically. The only difference is that no
    agent_runs row is created (this is not an agent run — it's a system
    template emission).
    """
    from services.task_workspace import TaskWorkspace
    from services.delivery import deliver_from_output_folder

    task_slug = "daily-update"
    tw = TaskWorkspace(client, user_id, task_slug)

    # Write output to date-stamped folder
    date_folder = started_at.strftime("%Y-%m-%dT%H00")
    folder_path = f"outputs/{date_folder}"

    schedule_label = format_daily_local_time_label(user_timezone)
    md_content = _build_empty_workspace_markdown(schedule_label)
    html_content = _build_empty_workspace_html(schedule_label)

    await tw.write(
        f"{folder_path}/output.md",
        md_content,
        summary="Daily-update empty-state (deterministic template)",
        tags=["output", "empty_state", "daily_update"],
    )
    await tw.write(
        f"{folder_path}/output.html",
        html_content,
        summary="Daily-update empty-state HTML",
        tags=["output", "empty_state", "daily_update", "html"],
    )

    import json as _json
    manifest = {
        "agent_slug": "reporting",
        "created_at": started_at.isoformat(),
        "status": "active",
        "kind": "empty_state",
        "files": [
            {"path": "output.md", "type": "text/markdown", "role": "primary"},
            {"path": "output.html", "type": "text/html", "role": "composed"},
        ],
    }
    await tw.write(
        f"{folder_path}/manifest.json",
        _json.dumps(manifest, indent=2),
        summary="Daily-update empty-state manifest",
        tags=["manifest", "empty_state"],
    )

    # Resolve delivery destination from TASK.md (or fall back to user email)
    task_md_content = await tw.read_task()
    task_info = parse_task_md(task_md_content) if task_md_content else {}
    delivery_target = (task_info.get("delivery") or "email").strip()
    destination = _parse_delivery_target(delivery_target, client, user_id)

    delivery_status = "no_destination"
    delivery_error = None

    if destination:
        try:
            # Use a synthetic agent dict — there's no agent_runs row for empty-state
            agent_dict = {
                "id": None,
                "title": "Daily Update",
                "role": "executive",
            }
            delivery_result = await deliver_from_output_folder(
                client=client,
                user_id=user_id,
                agent=agent_dict,
                output_folder=folder_path,
                agent_slug="reporting",
                version_id="",  # No agent_runs row
                version_number=0,
                destination=destination,
                task_slug=task_slug,
            )
            if delivery_result.status.value == "success":
                delivery_status = "delivered"
                logger.info(f"[TASK_EXEC] daily-update empty-state delivered to {destination.get('target')}")
            else:
                delivery_status = "failed"
                delivery_error = delivery_result.error_message
                logger.warning(f"[TASK_EXEC] daily-update empty-state delivery failed: {delivery_error}")
        except Exception as e:
            delivery_status = "failed"
            delivery_error = str(e)
            logger.error(f"[TASK_EXEC] daily-update empty-state delivery exception: {e}")

    # Update task scheduling: next run at local morning cadence, last_run_at now
    now = datetime.now(timezone.utc)
    next_run = calculate_next_run_at("daily", last_run_at=now, user_timezone=user_timezone)
    try:
        client.table("tasks").update({
            "last_run_at": now.isoformat(),
            "next_run_at": next_run.isoformat() if next_run else None,
            "updated_at": now.isoformat(),
        }).eq("user_id", user_id).eq("slug", task_slug).execute()
    except Exception as e:
        logger.warning(f"[TASK_EXEC] daily-update empty-state next_run_at update failed: {e}")

    # Append to run_log for observability
    try:
        await tw.append_run_log(
            f"empty-state delivered (workspace empty) — delivery_status={delivery_status}"
        )
    except Exception:
        pass

    # ADR-164: task_executed activity_log write removed. Task outputs folder +
    # tasks.last_run_at are the authoritative record of execution.

    return {
        "success": True,
        "task_slug": task_slug,
        "status": "delivered",
        "message": f"Daily-update empty-state delivered ({delivery_status})",
        "kind": "empty_state",
    }


# =============================================================================
# Agent-first entry point (for manual runs, MCP, event triggers)
# =============================================================================

async def execute_agent_run(
    client,
    user_id: str,
    agent: dict,
    trigger_context: Optional[dict] = None,
) -> dict:
    """Execute an agent run — finds the agent's task and routes through execute_task().

    This is the replacement for execute_agent_generation(). Callers that have
    an agent dict (manual run via POST /agents/{id}/run, MCP, trigger_dispatch.py
    for event triggers) use this. ADR-168 Commit 2 removed the Execute primitive
    as a caller — TP-initiated triggers now flow through
    ManageTask(action="trigger") → _handle_trigger → execute_task() instead.

    If the agent has an assigned task, routes through execute_task().
    If no task exists, runs a direct generation (taskless — agent identity only).

    Args:
        client: Supabase service client
        user_id: User UUID
        agent: Full agent dict from DB
        trigger_context: Optional trigger info

    Returns:
        Result dict compatible with execute_agent_generation() return shape
    """
    from services.workspace import AgentWorkspace, get_agent_slug

    agent_id = agent.get("id")
    agent_slug = get_agent_slug(agent)

    # Look up task assigned to this agent
    try:
        task_result = (
            client.table("tasks")
            .select("slug")
            .eq("user_id", user_id)
            .eq("status", "active")
            .execute()
        )
        # Find task whose TASK.md references this agent
        assigned_task_slug = None
        if task_result.data:
            from services.task_workspace import TaskWorkspace
            for task_row in task_result.data:
                tw = TaskWorkspace(client, user_id, task_row["slug"])
                task_md = await tw.read_task()
                if task_md and f"**Agent:** {agent_slug}" in task_md:
                    assigned_task_slug = task_row["slug"]
                    break
    except Exception as e:
        logger.warning(f"[AGENT_RUN] Task lookup failed (falling back to direct): {e}")
        assigned_task_slug = None

    if assigned_task_slug:
        # Route through task pipeline
        logger.info(f"[AGENT_RUN] {agent_slug} → task '{assigned_task_slug}'")
        result = await execute_task(client, user_id, assigned_task_slug)
        # Map to legacy result shape
        return {
            "success": result.get("success", False),
            "run_id": result.get("run_id"),
            "version_number": result.get("version_number"),
            "status": result.get("status", "failed"),
            "message": result.get("message", ""),
        }

    # No task — direct generation (taskless agent run)
    logger.info(f"[AGENT_RUN] {agent_slug} has no task — direct generation")
    return await _execute_direct(client, user_id, agent, agent_slug, trigger_context)


async def _execute_direct(
    client,
    user_id: str,
    agent: dict,
    agent_slug: str,
    trigger_context: Optional[dict] = None,
) -> dict:
    """Direct agent generation without a task. For agents not yet assigned tasks.

    Minimal pipeline: gather context → generate → save output → activity log.
    No delivery, no scheduling update (no TASK.md to read config from).
    """
    from services.workspace import AgentWorkspace, get_agent_slug
    from services.agent_framework import has_asset_capabilities, has_capability
    from services.agent_execution import (
        get_next_run_number, create_version_record, update_version_for_delivery,
        SONNET_MODEL, _extract_agent_reflection,
    )

    started_at = datetime.now(timezone.utc)
    agent_id = agent["id"]
    role = agent.get("role", "custom")
    scope = agent.get("scope", "cross_platform")
    title = agent.get("title", "Untitled")

    try:
        # Create agent_runs record
        next_version = await get_next_run_number(client, agent_id)
        version = await create_version_record(client, agent_id, next_version)
        version_id = version["id"]

        # Read agent workspace
        ws = AgentWorkspace(client, user_id, agent_slug)
        await ws.ensure_seeded(agent)
        ws_instructions = await ws.read("AGENT.md") or ""
        user_context = _load_user_context(client, user_id)

        # Gather context (no task_info for legacy single-agent path)
        context_text, context_meta = await gather_task_context(
            client, user_id, agent, agent_slug,
        )

        # Build prompt (use agent title as task title)
        task_info = {"title": title, "objective": {}, "success_criteria": [], "output_spec": []}
        system_prompt, user_message = build_task_execution_prompt(
            task_info=task_info,
            agent=agent,
            agent_instructions=ws_instructions,
            context=context_text,
            user_context=user_context,
        )

        # Skill reference — compact index, not full SKILL.md injection (~50t vs ~1500t)
        # Agent can read full specs via ReadFile (ADR-168) if needed
        if has_asset_capabilities(role):
            from services.agent_framework import get_type_capabilities, CAPABILITIES
            asset_caps = [
                c for c in get_type_capabilities(role)
                if CAPABILITIES.get(c, {}).get("category") == "asset"
            ]
            skill_lines = ["\n\n## Output Skills (RuntimeDispatch)"]
            skill_lines.append("Call `RuntimeDispatch(type, input, output_format)` to produce visual assets.")
            for cap in asset_caps:
                cap_def = CAPABILITIES.get(cap, {})
                docs_path = cap_def.get("skill_docs", "")
                out_type = cap_def.get("output_type", "")
                skill_lines.append(f"- **{cap}**: {out_type} — full spec in `{docs_path}`")
            skill_lines.append("Read playbooks in memory/ for when and how to use each skill.")
            system_prompt.append({
                "type": "text",
                "text": "\n".join(skill_lines),
            })

        # Generate (legacy single-agent path — no output_kind, default to produces_deliverable)
        draft, usage, pending_renders, _tools_used, _tool_rounds = await _generate(
            client, user_id, agent, system_prompt, user_message, scope,
            output_kind="produces_deliverable",
        )

        draft, agent_reflection = _extract_agent_reflection(draft)

        # Save to agent_runs
        await update_version_for_delivery(client, version_id, draft, metadata={
            "input_tokens": _total_input_tokens(usage),
            "output_tokens": usage.get("output_tokens", 0),
            "model": SONNET_MODEL,
            "trigger_type": (trigger_context or {}).get("type", "manual"),
        })

        # Save output folder
        try:
            await ws.save_output(
                content=draft,
                run_id=str(version_id),
                agent_id=str(agent_id),
                version_number=next_version,
                role=role,
                rendered_files=pending_renders if pending_renders else None,
            )
        except Exception as e:
            logger.warning(f"[AGENT_RUN] Output folder write failed: {e}")

        # ADR-151: Signal routing for taskless agent runs
        try:
            from services.workspace import UserMemory
            um = UserMemory(client, user_id)
            from datetime import datetime, timezone
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            signal_path = f"context/signals/{date_str}.md"
            existing = await um.read(signal_path) or f"# Signals — {date_str}\n"
            signal_entry = (
                f"\n## {title} v{next_version} ({datetime.now(timezone.utc).strftime('%H:%M UTC')})\n"
                f"- Agent: {agent_slug}\n"
                f"- Output: {len(draft)} chars\n"
            )
            await um.write(signal_path, existing + signal_entry,
                          summary=f"Signal from {agent_slug} v{next_version}")
        except Exception as e:
            logger.warning(f"[AGENT_RUN] Context signal routing failed: {e}")

        # Mark as delivered (no external delivery for taskless runs)
        now = datetime.now(timezone.utc).isoformat()
        client.table("agent_runs").update({
            "status": "delivered",
            "delivered_at": now,
        }).eq("id", version_id).execute()

        # ADR-164: task_executed activity_log write removed. The agent_runs
        # row is the authoritative record.
        duration_ms = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)

        # ADR-171: Record token spend
        try:
            from services.platform_limits import record_token_usage
            record_token_usage(
                client, user_id,
                caller="task_pipeline",
                model=SONNET_MODEL,
                input_tokens=version_metadata.get("input_tokens", 0) if "version_metadata" in dir() else 0,
                output_tokens=version_metadata.get("output_tokens", 0) if "version_metadata" in dir() else 0,
                ref_id=str(version_id),
                metadata={"task_slug": task_slug},
            )
        except Exception:
            pass

        logger.info(f"[AGENT_RUN] Complete: {agent_slug} v{next_version} delivered ({duration_ms}ms)")

        return {
            "success": True,
            "run_id": version_id,
            "version_number": next_version,
            "status": "delivered",
            "message": f"Run {next_version} delivered",
        }

    except Exception as e:
        logger.error(f"[AGENT_RUN] Failed: {agent_slug}: {e}")
        return {
            "success": False,
            "run_id": None,
            "status": "failed",
            "message": str(e),
        }

"""
Dispatch Helpers — ADR-231 Phase 3.7 survivor module.

Hosts the auxiliary functions that survive the deletion of task_pipeline.py:
prompt assembly, Sonnet generation loop, context-domain gathering, user-context
loading, daily-update + maintain-overview empty-state writers, and the
microcompact / token-accounting helpers.

These are the implementations the YAML-native dispatcher
(services.invocation_dispatcher) imports. Per ADR-231 D2/D3 the empty-state
writers were ported off TaskWorkspace onto natural-home substrate via
UserMemory + recurrence_paths.

What lives here:
  - _generate                       Sonnet generation loop with microcompact
  - _gather_context_domains         /workspace/context/{domain}/ readers
  - gather_recurrence_context       declaration-aware context bundle
  - build_task_execution_prompt     system + user prompt assembly
  - _load_user_context              IDENTITY/style/notes/BRAND injection
  - _is_workspace_empty             pure-SQL emptiness probe
  - _execute_daily_update_empty_state    natural-home empty template
  - _execute_maintain_overview_empty_state    natural-home warming-up template
  - _total_input_tokens / _microcompact_tool_history / _resolve_max_output_tokens

The legacy `gather_task_context` is preserved as a backward-compat shim that
re-routes to gather_recurrence_context (the dispatcher caller has been
updated; this file's signature stays stable for the migration window).

This module replaces ~1,500 LOC of survivors that lived in task_pipeline.py.
The other ~2,700 LOC of task_pipeline.py was the legacy execute_task /
_execute_pipeline / _execute_tp_task / _execute_direct dispatch path which
the YAML-native dispatcher absorbed in Phase 3.2.b. That code is deleted in
Phase 3.7.c alongside this file's creation.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from services.schedule_utils import (
    calculate_next_run_at,
    format_daily_local_time_label,
    get_user_timezone,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Token + microcompact helpers
# =============================================================================


def _total_input_tokens(usage: dict) -> int:
    """Sum all input token fields including prompt cache tokens."""
    return (
        usage.get("input_tokens", 0)
        + usage.get("cache_creation_input_tokens", 0)
        + usage.get("cache_read_input_tokens", 0)
    )


def _microcompact_tool_history(messages: list[dict], keep_recent: int = 3) -> None:
    """Clear old tool results from message history to prevent geometric growth.

    CC-style microcompact: walks the message history and replaces tool_result
    content older than the last N results with a stub. Mutates messages in
    place.
    """
    positions = []
    for i, msg in enumerate(messages):
        if msg.get("role") != "user" or not isinstance(msg.get("content"), list):
            continue
        for j, block in enumerate(msg["content"]):
            if isinstance(block, dict) and block.get("type") == "tool_result":
                positions.append((i, j))
    to_clear = positions[:-keep_recent] if len(positions) > keep_recent else []
    for msg_idx, block_idx in to_clear:
        block = messages[msg_idx]["content"][block_idx]
        if block.get("content") != "[Prior tool result cleared]":
            block["content"] = "[Prior tool result cleared]"


_TOOL_ROUNDS = {
    "platform": 5,
    "cross_platform": 8,
    "knowledge": 8,
    "research": 10,
    "autonomous": 12,
}
_BOOTSTRAP_ROUND_MULTIPLIER = 2

_MAX_OUTPUT_TOKENS = {
    "accumulates_context": 8000,
    "produces_deliverable": 4000,
    "external_action": 4000,
    "system_maintenance": 4000,
}
_DEFAULT_MAX_OUTPUT_TOKENS = 4000


def _resolve_max_output_tokens(output_kind: str) -> int:
    return _MAX_OUTPUT_TOKENS.get(output_kind, _DEFAULT_MAX_OUTPUT_TOKENS)


# =============================================================================
# User context loader
# =============================================================================


def _load_user_context(client, user_id: str) -> Optional[str]:
    """Load IDENTITY/style/notes/BRAND content as prompt-ready text.

    Reads via UserMemory directly — no intermediate KV layer. Returns None
    when no user-context files exist.
    """
    try:
        from services.workspace import UserMemory
        um = UserMemory(client, user_id)
        memory_files = um.read_all_sync()
        sections: list[str] = []

        profile = UserMemory._parse_memory_md(memory_files.get("IDENTITY.md"))
        profile_lines = [f"- {k.title()}: {v}" for k, v in profile.items() if v]
        if profile_lines:
            sections.append("## User Context\n" + "\n".join(profile_lines))

        prefs = UserMemory._parse_preferences_md(memory_files.get("style.md"))
        pref_lines = []
        for platform, settings in prefs.items():
            if settings.get("tone"):
                pref_lines.append(f"- {platform.title()} Tone: {settings['tone']}")
            if settings.get("verbosity"):
                pref_lines.append(f"- {platform.title()} Verbosity: {settings['verbosity']}")
        notes = UserMemory._parse_notes_md(memory_files.get("notes.md"))
        for note in notes[:5]:
            pref_lines.append(f"- Prefers: {note['content']}")
        if pref_lines:
            sections.append("## Preferences\n" + "\n".join(pref_lines))

        brand = memory_files.get("BRAND.md", "").strip()
        if brand:
            sections.append("## Brand Guidelines\n" + brand)

        return "\n\n".join(sections) if sections else None
    except Exception as e:
        logger.warning(f"[DISPATCH] User context load failed: {e}")
        return None


# =============================================================================
# Tracker + objective entity matching
# =============================================================================


def _normalize_match_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


def _build_objective_search_text(task_info: dict) -> str:
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
            f.strip() for f in cells[2].split(",")
            if f.strip() and f.strip() != "—"
        ]
        entities.append({
            "slug": cells[0],
            "last_updated": cells[1],
            "files": files,
            "status": cells[3],
        })
    return entities


def _get_primary_entity_filename(domain_key: str) -> Optional[str]:
    from services.directory_registry import get_domain
    domain = get_domain(domain_key) or {}
    entity_structure = domain.get("entity_structure") or {}
    if not entity_structure:
        return None
    return next(iter(entity_structure.keys()), None)


def _read_domain_metadata_sync(client, user_id: str, domain_prefix: str) -> dict:
    """Read YAML-style frontmatter from `_domain.md` for TP-composed domain metadata."""
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
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                for line in parts[1].strip().splitlines():
                    if ":" in line:
                        key, val = line.split(":", 1)
                        key = key.strip()
                        val = val.strip()
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


# =============================================================================
# Context-domain reader (ADR-151/152/154/188)
# =============================================================================


async def _gather_context_domains(
    client,
    user_id: str,
    context_reads: list[str],
    task_info: Optional[dict] = None,
    max_files_per_domain: int = 20,
    max_content_per_file: int = 3000,
) -> str:
    """Read accumulated context from /workspace/context/{domain}/ files.

    Synthesis-first + objective-targeted entity loading per ADR-154 Phase 2.
    Pure SQL against workspace_files; no TaskWorkspace dependency.
    """
    if not context_reads:
        return ""

    from services.directory_registry import (
        get_authored_substrate, get_domain_folder, get_synthesis_content,
        get_tracker_path, has_entity_tracker, WORKSPACE_DIRECTORIES,
    )

    sections = []
    for domain_key in context_reads:
        folder = get_domain_folder(domain_key)
        if not folder:
            continue

        prefix = f"/workspace/{folder}"
        domain_meta = _read_domain_metadata_sync(client, user_id, prefix)
        domain_def = WORKSPACE_DIRECTORIES.get(domain_key, {})
        is_temporal = domain_meta.get("temporal", domain_def.get("temporal", False))
        ttl_days = domain_meta.get("ttl_days", domain_def.get("ttl_days"))

        ttl_cutoff = None
        if is_temporal and ttl_days:
            ttl_cutoff = (datetime.now(timezone.utc) - timedelta(days=ttl_days)).isoformat()

        try:
            domain_parts = []

            # Synthesis file
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
                    pass

            # Authored substrate (ADR-220)
            authored_files = get_authored_substrate(domain_key)
            for authored_filename in authored_files:
                authored_path = f"{prefix}/{authored_filename}"
                try:
                    authored_result = (
                        client.table("workspace_files")
                        .select("path, content, updated_at")
                        .eq("user_id", user_id)
                        .eq("path", authored_path)
                        .limit(1)
                        .execute()
                    )
                    authored_rows = authored_result.data or []
                    if authored_rows and (authored_rows[0].get("content") or "").strip():
                        row = authored_rows[0]
                        content = (row.get("content") or "")[:max_content_per_file]
                        updated = (row.get("updated_at") or "")[:10]
                        domain_parts.append(
                            f"### {authored_filename} (operator-authored, updated {updated})\n{content}"
                        )
                except Exception:
                    pass

            # Entity loading strategy
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
                    pass

            if has_entities and task_info and tracker_entities:
                matched_entities = _match_entities_to_objective(
                    [entity["slug"] for entity in tracker_entities], task_info,
                )

            if matched_entities:
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
                                continue
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
                label = f"Platform Observations: {domain_key}" if is_temporal else f"Accumulated Context: {domain_key}"
                if is_temporal and ttl_days:
                    label += f" (last {ttl_days} days)"
                sections.append(
                    f"## {label}\n" +
                    "\n\n".join(domain_parts)
                )

        except Exception as e:
            logger.warning(f"[DISPATCH] Context domain read failed for {domain_key}: {e}")

    return "\n\n".join(sections) if sections else ""


# =============================================================================
# Recurrence-aware context bundle (replaces gather_task_context)
# =============================================================================


async def gather_task_context(
    client,
    user_id: str,
    agent: dict,
    agent_slug: str,
    task_info: Optional[dict] = None,
    task_slug: Optional[str] = None,
) -> tuple[str, dict]:
    """Gather context for invocation execution.

    Reads (in order):
      1. Tracker entries declared by the recurrence's context_writes
      2. Accumulated context domains from context_reads
      3. Agent identity (AGENT.md via AgentWorkspace)
      4. User notes (workspace memory/notes.md)

    Per ADR-231 D2: legacy task awareness.md / source-scope reads against
    /tasks/{slug}/ are removed. The dispatcher passes a synthetic task_info
    derived from the declaration; everything else flows through workspace_files.
    """
    from services.workspace import AgentWorkspace, UserMemory

    ws = AgentWorkspace(client, user_id, agent_slug)
    await ws.ensure_seeded(agent)

    sections = []

    if task_info and task_info.get("sources"):
        sources = task_info["sources"]
        source_lines = ["## Selected Sources",
                        "Read ONLY from these selected sources (user-configured scope):"]
        for platform, ids in sources.items():
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

    # Domain trackers (entity registry for accumulation tasks)
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

    # Accumulated context domains
    output_kind = (task_info or {}).get("output_kind", "produces_deliverable")
    if output_kind == "accumulates_context":
        total_budget = 8
        per_floor = 2
        per_ceiling = 4
    else:
        total_budget = 30
        per_floor = 3
        per_ceiling = 10

    context_domains_text = ""
    if task_info:
        context_reads = task_info.get("context_reads", [])
        if context_reads:
            domain_count = max(len(context_reads), 1)
            files_per_domain = max(per_floor, min(per_ceiling, total_budget // domain_count))
            context_domains_text = await _gather_context_domains(
                client, user_id, context_reads, task_info=task_info,
                max_files_per_domain=files_per_domain,
            )
    if context_domains_text:
        sections.append(context_domains_text)

    # Agent identity + selective playbooks
    ws_context = await ws.load_context(output_kind=output_kind)
    if ws_context:
        sections.append(f"## Agent Context\n{ws_context}")

    # User notes
    try:
        from services.workspace_paths import MEMORY_NOTES_PATH
        um = UserMemory(client, user_id)
        notes = await um.read(MEMORY_NOTES_PATH)
        if notes:
            sections.append(f"## User Notes\n{notes}")
    except Exception as e:
        logger.debug(f"[DISPATCH] User memory read failed: {e}")

    # Shared precedent
    try:
        from services.workspace_paths import SHARED_PRECEDENT_PATH
        um = UserMemory(client, user_id)
        precedent = await um.read(SHARED_PRECEDENT_PATH)
        if precedent and precedent.strip():
            sections.append(
                "## Operator Precedent (durable interpretations)\n" + precedent
            )
    except Exception as e:
        logger.debug(f"[DISPATCH] Precedent read failed: {e}")

    context_text = "\n\n".join(sections) if sections else "(No context available)"
    metadata = {
        "sections": len(sections),
        "scope": agent.get("scope", "cross_platform"),
    }
    return context_text, metadata


# =============================================================================
# Prompt assembly
# =============================================================================


# ADR-233 Phase 1: shape → headless profile key mapping. The dispatcher passes
# `decl.shape.value` (a string from the RecurrenceShape enum) and the helper
# resolves it to one of the three headless profile keys. MAINTENANCE never
# reaches LLM dispatch (dotted executor, no posture). Unknown / missing shapes
# fall back to DELIVERABLE — the safest cognitive posture for legacy callers
# that haven't been updated to pass `shape` yet.
_SHAPE_PROFILE_MAP: dict[str, str] = {
    "DELIVERABLE": "headless/deliverable",
    "ACCUMULATION": "headless/accumulation",
    "ACTION": "headless/action",
    # Lowercase aliases — defensive, in case callers pass enum value as-stored
    "deliverable": "headless/deliverable",
    "accumulation": "headless/accumulation",
    "action": "headless/action",
}


def _shape_to_profile_key(shape: Optional[str]) -> str:
    """Resolve a RecurrenceShape value to a headless profile key.

    ADR-233 Phase 1. Defaults to `headless/deliverable` when shape is missing
    or unrecognized — the safest cognitive posture (gap-filling delta
    generation against an output spec is the most common headless job).
    """
    if not shape:
        return "headless/deliverable"
    return _SHAPE_PROFILE_MAP.get(shape, "headless/deliverable")


# ADR-233 Phase 2 — natural-home pre-read budget caps per shape. DELIVERABLE
# inherits the existing 8000-char prior_output slice (preserves Phase 1
# token budget); ACCUMULATION + ACTION are tighter because their briefs are
# inventory pointers, not full content.
_NATURAL_HOME_BRIEF_CAPS = {
    "DELIVERABLE": 8000,
    "ACCUMULATION": 4000,
    "ACTION": 1500,
}


async def _load_natural_home_brief(client, user_id: str, decl) -> Optional[str]:
    """Load a shape-keyed pre-read brief from the declaration's natural-home folder.

    ADR-233 Phase 2 — every generative shape pre-reads its natural-home folder
    before writing. The principle: "read what you're about to write atop."
    Path resolution flows through ``services.recurrence_paths`` per ADR-231 D2.

    Per-shape semantics:
      - DELIVERABLE: latest dated subfolder under ``/workspace/reports/{slug}/``
        → ``output.md``. Returns the prior-output content with date marker.
      - ACCUMULATION: ``/workspace/context/{domain}/`` → entity-folder inventory
        + ``landscape.md`` synthesis if present. Returns a domain-state brief.
      - ACTION: ``/workspace/operations/{slug}/`` → any pending proposal files +
        recent run-log tail. Returns a pending-state brief.
      - MAINTENANCE: never invoked (dotted executor, no LLM, no posture).

    Returns ``None`` when:
      - shape is MAINTENANCE (early exit before any I/O)
      - no prior content exists (first run case — posture frames as such)
      - the folder is empty / unreadable

    Design notes:
      - Pure I/O helper; no LLM calls, no mutation. Safe to call on every
        firing.
      - Output is a self-contained markdown string the caller splices into
        the user-message half of the prompt. The framing header (``## Prior
        Output``, ``## Domain State``, ``## Pending Operations``) is part of
        the returned string so the caller doesn't have to know the shape.
      - Capped per-shape (see ``_NATURAL_HOME_BRIEF_CAPS``); favors fresh
        leading content on overflow.
    """
    from services.recurrence import RecurrenceShape
    from services.recurrence_paths import resolve_substrate_root

    if decl.shape == RecurrenceShape.MAINTENANCE:
        return None

    shape_key = decl.shape.value
    cap = _NATURAL_HOME_BRIEF_CAPS.get(shape_key, 4000)

    try:
        if decl.shape == RecurrenceShape.DELIVERABLE:
            return await _load_deliverable_prior_output(client, user_id, decl, cap)
        if decl.shape == RecurrenceShape.ACCUMULATION:
            return await _load_accumulation_inventory(client, user_id, decl, cap)
        if decl.shape == RecurrenceShape.ACTION:
            return await _load_action_pending_state(client, user_id, decl, cap)
    except Exception as e:
        logger.warning(
            "[DISPATCH] _load_natural_home_brief failed (shape=%s, slug=%s): %s",
            shape_key, decl.slug, e,
        )
        return None

    return None


async def _load_deliverable_prior_output(client, user_id: str, decl, cap: int) -> Optional[str]:
    """DELIVERABLE pre-read: latest output.md from /workspace/reports/{slug}/.

    Walks date-folder children of the declaration's substrate root, picks the
    newest by lexicographic sort (date folders are YYYY-MM-DD-keyed per
    ADR-231 D2), reads ``output.md``. Returns ``None`` for first runs.
    """
    from services.recurrence_paths import resolve_substrate_root

    root = resolve_substrate_root(decl)  # e.g. /workspace/reports/weekly-brief
    prefix = f"{root}/"

    try:
        result = (
            client.table("workspace_files")
            .select("path, content, updated_at")
            .eq("user_id", user_id)
            .like("path", f"{prefix}%/output.md")
            .order("path", desc=True)
            .limit(1)
            .execute()
        )
    except Exception as e:
        logger.warning("[DISPATCH] DELIVERABLE prior-output query failed: %s", e)
        return None

    rows = result.data or []
    if not rows:
        return None

    row = rows[0]
    path = row.get("path") or ""
    content = (row.get("content") or "").strip()
    if not content:
        return None

    # Extract date marker from path: /workspace/reports/{slug}/{YYYY-MM-DD}/output.md
    date_marker = ""
    if path.endswith("/output.md"):
        parts = path.rsplit("/", 2)
        if len(parts) >= 2:
            date_marker = parts[-2]

    # Cap content
    body = content[:cap]
    truncated = "\n\n[...truncated]" if len(content) > cap else ""
    header = f"## Prior Output (latest run, {date_marker})" if date_marker else "## Prior Output (latest run)"
    return f"{header}\n\n{body}{truncated}"


async def _load_accumulation_inventory(client, user_id: str, decl, cap: int) -> Optional[str]:
    """ACCUMULATION pre-read: entity inventory + landscape.md from /workspace/context/{domain}/.

    Lists direct children of the domain root (one folder = one entity per
    ADR-151 / ADR-176 conventions), reports counts + last-modified dates, and
    appends ``landscape.md`` content if present. Returns a domain-state brief
    capped at ``cap`` chars total.
    """
    from services.recurrence_paths import resolve_substrate_root

    root = resolve_substrate_root(decl)  # /workspace/context/{domain}
    domain = decl.domain or "(unknown)"
    prefix = f"{root}/"

    # 1) List entity folders (direct children that are folder-shaped — i.e.,
    #    paths with at least one '/' after the prefix that end at the entity
    #    boundary).
    try:
        result = (
            client.table("workspace_files")
            .select("path, updated_at")
            .eq("user_id", user_id)
            .like("path", f"{prefix}%")
            .order("path")
            .execute()
        )
    except Exception as e:
        logger.warning("[DISPATCH] ACCUMULATION inventory query failed: %s", e)
        return None

    rows = result.data or []
    if not rows:
        return None

    # Build entity → most-recent-update map. Entity slug = first path segment
    # after the prefix; ignore landscape.md and other top-level domain files
    # (they don't correspond to entities).
    entity_updates: dict[str, str] = {}
    landscape_content: Optional[str] = None
    landscape_updated_at: Optional[str] = None

    for r in rows:
        path = r.get("path") or ""
        updated_at = r.get("updated_at") or ""
        remainder = path[len(prefix):]
        if not remainder:
            continue
        # Direct child file: domain-level synthesis or marker — keep landscape.md
        if "/" not in remainder:
            if remainder == "landscape.md":
                # Fetch full content for the synthesis attachment below
                try:
                    detail = (
                        client.table("workspace_files")
                        .select("content")
                        .eq("user_id", user_id)
                        .eq("path", path)
                        .limit(1)
                        .execute()
                    )
                    detail_rows = detail.data or []
                    if detail_rows:
                        landscape_content = (detail_rows[0].get("content") or "").strip()
                        landscape_updated_at = updated_at
                except Exception:
                    pass
            continue
        # Nested file: belongs to an entity folder
        entity_slug = remainder.split("/", 1)[0]
        if entity_slug.startswith("_"):
            # _-prefixed = synthesis files (cross-entity), not entities themselves
            continue
        # Track most-recent update across all files in the entity
        prior = entity_updates.get(entity_slug, "")
        if updated_at > prior:
            entity_updates[entity_slug] = updated_at

    if not entity_updates and not landscape_content:
        return None

    # Build the brief — header + inventory + (truncated) landscape if present
    parts = ["## Domain State (what you've accumulated so far)", "", f"Domain: `{domain}`"]
    if entity_updates:
        parts.append("")
        parts.append(f"**Existing entities ({len(entity_updates)}):**")
        for slug in sorted(entity_updates.keys()):
            ts = entity_updates[slug]
            ts_short = ts[:10] if ts else "—"  # YYYY-MM-DD
            parts.append(f"- `{slug}` (last updated: {ts_short})")
    if landscape_content:
        parts.append("")
        parts.append(f"**Domain synthesis** (landscape.md, last updated: {(landscape_updated_at or '')[:10] or '—'}):")
        parts.append("")
        parts.append(landscape_content)
    elif entity_updates:
        parts.append("")
        parts.append("**Domain synthesis**: not yet written (first synthesis pass).")

    brief = "\n".join(parts)
    if len(brief) > cap:
        brief = brief[:cap] + "\n\n[...truncated]"
    return brief


async def _load_action_pending_state(client, user_id: str, decl, cap: int) -> Optional[str]:
    """ACTION pre-read: pending operation state from /workspace/operations/{slug}/.

    Best-effort survey of the operation folder. Returns a brief listing any
    files present plus the tail of ``_run_log.md`` if it exists. The ACTION
    substrate is still emerging post-ADR-231; this brief is intentionally
    conservative (file inventory + recent run-log lines) until proposal-state
    semantics solidify.
    """
    from services.recurrence_paths import resolve_substrate_root

    root = resolve_substrate_root(decl)  # /workspace/operations/{slug}
    prefix = f"{root}/"

    try:
        result = (
            client.table("workspace_files")
            .select("path, updated_at")
            .eq("user_id", user_id)
            .like("path", f"{prefix}%")
            .order("path")
            .execute()
        )
    except Exception as e:
        logger.warning("[DISPATCH] ACTION inventory query failed: %s", e)
        return None

    rows = result.data or []
    if not rows:
        return None

    # File inventory (paths only, capped)
    file_lines = []
    run_log_path: Optional[str] = None
    for r in rows[:25]:  # safety cap on inventory length
        path = r.get("path") or ""
        relative = path[len(prefix):] if path.startswith(prefix) else path
        if not relative:
            continue
        ts_short = (r.get("updated_at") or "")[:10] or "—"
        file_lines.append(f"- `{relative}` (updated: {ts_short})")
        if relative == "_run_log.md":
            run_log_path = path

    if not file_lines:
        return None

    parts = ["## Pending Operations", "", f"Operation: `{decl.slug}`", "", "**Files in operation folder:**"]
    parts.extend(file_lines)

    # If _run_log.md exists, attach the tail (last ~600 chars) so the LLM sees
    # what's recent without paging the whole log.
    if run_log_path:
        try:
            detail = (
                client.table("workspace_files")
                .select("content")
                .eq("user_id", user_id)
                .eq("path", run_log_path)
                .limit(1)
                .execute()
            )
            detail_rows = detail.data or []
            if detail_rows:
                log_content = (detail_rows[0].get("content") or "").strip()
                if log_content:
                    tail = log_content[-600:]
                    if len(log_content) > 600:
                        tail = "[...earlier entries omitted]\n" + tail
                    parts.append("")
                    parts.append("**Recent run-log tail:**")
                    parts.append("")
                    parts.append(tail)
        except Exception:
            pass

    brief = "\n".join(parts)
    if len(brief) > cap:
        brief = brief[:cap] + "\n\n[...truncated]"
    return brief


def build_task_execution_prompt(
    task_info: dict,
    agent: dict,
    agent_instructions: str,
    context: str,
    user_context: Optional[str] = None,
    deliverable_spec: str = "",
    steering_notes: str = "",
    task_feedback: str = "",
    shape: Optional[str] = None,
    natural_home_brief: str = "",
    prior_state_brief: str = "",
    task_phase: str = "steady",
    generation_brief: str = "",
) -> tuple[list[dict], str]:
    """Build (system_blocks, user_message) for one invocation.

    ADR-233 Phase 1: cognitive posture is shape-keyed. The shape ("DELIVERABLE",
    "ACCUMULATION", "ACTION") selects a posture from `prompts.HEADLESS_POSTURES`;
    the universal `HEADLESS_BASE_BLOCK` (output rules, conventions, accumulation-
    first principle, tool usage, visual assets, empty-context handling) is shared
    across all shapes. The static block (posture + base) is cached; per-task
    dynamic content (user_context, agent_instructions, playbooks, deliverable
    spec, criteria reflection) sits below the cache marker.

    ADR-233 Phase 2: ``natural_home_brief`` carries the pre-read assembled by
    ``_load_natural_home_brief(client, user_id, decl)`` upstream. DELIVERABLE
    runs see prior ``output.md``; ACCUMULATION sees domain entity inventory +
    landscape synthesis; ACTION sees pending operation state. Empty string ->
    first-run case (the posture frames the absence). Spliced into the user
    message after ``generation_brief``, before ``prior_state_brief``.

    The ``task_mode`` parameter (and the goal-mode prior-output branch it
    gated) was deleted in Phase 1. Pre-read injection is now shape-driven,
    universal across generative shapes — not mode-driven, not DELIVERABLE-only.
    """
    role = agent.get("role", "custom")
    title = task_info.get("title", "Untitled")

    # ---- Static (cached) half: shape posture + universal base block ----
    from agents.prompts import build_prompt
    profile_key = _shape_to_profile_key(shape)
    system = build_prompt(profile_key)

    # ---- Dynamic half: per-invocation content appended after the cache marker ----
    if user_context:
        system += "\n\n" + user_context

    if agent_instructions:
        system += f"\n\n## Agent Instructions\n{agent_instructions}"

    from services.orchestration import PLAYBOOK_METADATA, TASK_OUTPUT_PLAYBOOK_ROUTING, get_type_playbook
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

    if deliverable_spec and deliverable_spec.strip():
        spec_clean = deliverable_spec.strip()
        if spec_clean.startswith("# Deliverable Specification"):
            spec_clean = spec_clean.split("\n", 1)[-1].strip()
        spec_clean = re.sub(r"<!--.*?-->", "", spec_clean, flags=re.DOTALL).strip()
        if spec_clean:
            system += f"\n\n## Deliverable Specification\nYour output MUST match this quality contract:\n{spec_clean}"

    from services.orchestration_prompts import _REFLECTION_POSTAMBLE, _CRITERIA_EVAL_SECTION
    criteria = task_info.get("success_criteria", [])
    if criteria:
        criteria_list = "\n".join(f"  - {c}" for c in criteria)
        criteria_eval = _CRITERIA_EVAL_SECTION.format(criteria_list=criteria_list)
    else:
        criteria_eval = ""
    system += _REFLECTION_POSTAMBLE.format(criteria_eval=criteria_eval)

    user_parts = [f"# Task: {title}"]

    objective = task_info.get("objective", {})
    if objective:
        user_parts.append("\n## Objective")
        for key in ["deliverable", "audience", "purpose", "format"]:
            val = objective.get(key)
            if val:
                user_parts.append(f"- **{key.capitalize()}:** {val}")
        step_instruction = objective.get("step_instruction") or objective.get("prose")
        if step_instruction:
            user_parts.append(f"\n**Your specific role:** {step_instruction}")

    if criteria:
        user_parts.append("\n## Success Criteria")
        for c in criteria:
            user_parts.append(f"- {c}")

    output_spec = task_info.get("output_spec", [])
    if output_spec:
        user_parts.append("\n## Output Format")
        for s in output_spec:
            user_parts.append(f"- {s}")

    if generation_brief:
        user_parts.append(f"\n{generation_brief}")

    # ADR-233 Phase 2 — natural-home pre-read brief. Pre-assembled by
    # ``_load_natural_home_brief`` in the dispatcher; the brief is already
    # shape-keyed and self-headered ("## Prior Output", "## Domain State",
    # "## Pending Operations"). Empty string => first-run case; the posture
    # in the cached static block frames the absence.
    if natural_home_brief and natural_home_brief.strip():
        user_parts.append(f"\n{natural_home_brief.strip()}")

    if prior_state_brief:
        user_parts.append(f"\n{prior_state_brief}")

    if steering_notes and steering_notes.strip():
        clean_steering = steering_notes.strip()
        if clean_steering.startswith("# Steering Notes"):
            clean_steering = clean_steering.split("\n", 1)[-1].strip()
        clean_steering = re.sub(r"<!--.*?-->", "", clean_steering, flags=re.DOTALL).strip()
        if clean_steering:
            user_parts.append(f"\n## Steering Notes (from task manager)\n{clean_steering}")

    if task_feedback and task_feedback.strip():
        user_parts.append(f"\n## Recent Feedback\nIncorporate these corrections:\n{task_feedback}")

    user_parts.append(f"\n## Gathered Context\n{context}")
    user_message = "\n".join(user_parts)

    static_end_markers = [
        "\n\n## User Context",
        "\n\n## Deliverable Specification",
        "\n\n## Self-Reflection",
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
# Sonnet generation loop
# =============================================================================


async def _generate(
    client,
    user_id: str,
    agent: dict,
    system_prompt,  # str OR list of content blocks
    user_message: str,
    scope: str,
    task_phase: str = "steady",
    task_slug: str = "",
    output_kind: str = "produces_deliverable",
    tool_overrides: Optional[list[dict]] = None,
    max_rounds_override: Optional[int] = None,
    task_required_capabilities: Optional[list[str]] = None,
) -> tuple[str, dict, list, list, int]:
    """Run the headless generation loop.

    Returns (draft, usage, pending_renders, tools_used, tool_rounds).
    """
    from services.anthropic import chat_completion_with_tools
    from services.primitives.registry import get_headless_tools_for_agent, create_headless_executor
    from services.agent_execution import (
        SONNET_MODEL, _is_narration, _strip_tool_narration,
    )

    role = agent.get("role", "custom")

    if max_rounds_override is not None:
        max_tool_rounds = max_rounds_override
    else:
        max_tool_rounds = _TOOL_ROUNDS.get(scope, 5)
        if task_phase == "bootstrap":
            max_tool_rounds = max_tool_rounds * _BOOTSTRAP_ROUND_MULTIPLIER
        from services.orchestration import has_asset_capabilities
        if has_asset_capabilities(role):
            max_tool_rounds = max(max_tool_rounds, 6)

    if tool_overrides is not None:
        headless_tools = tool_overrides
    else:
        headless_tools = await get_headless_tools_for_agent(
            client, user_id, agent=agent, agent_sources=[],
            task_required_capabilities=task_required_capabilities,
        )
    executor = create_headless_executor(
        client, user_id,
        agent_sources=[],
        agent=agent,
        dynamic_tools=headless_tools,
        task_slug=task_slug or None,
    )

    _CONTEXT_MARKER = "\n## Gathered Context\n"
    _split_idx = user_message.find(_CONTEXT_MARKER)
    if _split_idx != -1:
        _instructions_part = user_message[:_split_idx]
        _context_part = user_message[_split_idx:]
        _initial_content = [
            {"type": "text", "text": _instructions_part},
            {"type": "text", "text": _context_part, "cache_control": {"type": "ephemeral"}},
        ]
    else:
        _initial_content = [{"type": "text", "text": user_message}]

    messages = [{"role": "user", "content": _initial_content}]
    tools_used = []
    total_input_tokens = 0
    total_output_tokens = 0
    total_cache_read = 0
    total_cache_create = 0
    draft = ""

    _microcompact_keep = 2 if output_kind == "accumulates_context" else 3
    _max_output_tokens = _resolve_max_output_tokens(output_kind)

    for round_num in range(max_tool_rounds + 1):
        if round_num >= 2:
            _microcompact_tool_history(messages, keep_recent=_microcompact_keep)

        response = await chat_completion_with_tools(
            messages=messages,
            system=system_prompt,
            tools=headless_tools,
            model=SONNET_MODEL,
            max_tokens=_max_output_tokens,
        )

        if response.usage:
            total_input_tokens += _total_input_tokens(response.usage)
            total_output_tokens += response.usage.get("output_tokens", 0)
            total_cache_read += response.usage.get("cache_read_input_tokens", 0)
            total_cache_create += response.usage.get("cache_creation_input_tokens", 0)

        if response.stop_reason in ("end_turn", "max_tokens") or not response.tool_uses:
            draft = response.text.strip()
            if round_num > 0:
                logger.info(f"[DISPATCH] Agent used {round_num} tool round(s): {', '.join(tools_used)}")
            break

        if round_num >= max_tool_rounds:
            candidate = response.text.strip() if response.text else ""
            if candidate and not _is_narration(candidate):
                draft = candidate
                break
            messages.append({"role": "assistant", "content": response.text or ""})
            messages.append({"role": "user", "content": "You have reached the tool limit. Synthesize all gathered information and produce the final output now."})
            final_response = await chat_completion_with_tools(
                messages=messages,
                system=system_prompt,
                tools=[],
                model=SONNET_MODEL,
                max_tokens=_max_output_tokens,
            )
            if final_response.usage:
                total_input_tokens += _total_input_tokens(final_response.usage)
                total_output_tokens += final_response.usage.get("output_tokens", 0)
            draft = final_response.text.strip() if final_response.text else ""
            break

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
            logger.info(f"[DISPATCH] Tool: {tu.name}({str(tu.input)[:100]})")
            result = await executor(tu.name, tu.input)
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

    if len(draft.split()) < 20:
        messages.append({"role": "assistant", "content": draft})
        messages.append({"role": "user", "content": (
            "Your output was too short. Produce the full content in the requested format now."
        )})
        retry_response = await chat_completion_with_tools(
            messages=messages, system=system_prompt, tools=[], model=SONNET_MODEL, max_tokens=_max_output_tokens,
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
    pending_renders = getattr(executor, "auth", None)
    pending_renders = getattr(pending_renders, "pending_renders", []) if pending_renders else []

    return draft, usage, pending_renders, tools_used, round_num


# =============================================================================
# Empty-state probe + writers (ADR-161 / ADR-204) — natural-home substrate
# =============================================================================


def _parse_delivery_target(delivery_str: str, client, user_id: str) -> Optional[dict]:
    """Parse a recurrence's `delivery:` field into a destination dict.

    Supports:
      - "email" (no address) → resolve to user's email
      - "user@example.com" → email
      - "slack:#channel" → slack
      - "subscribers" → commerce subscriber blast (product_id injected by caller)
      - "none" / "cockpit-only" / empty → None (silent)
    """
    if not delivery_str or delivery_str.strip().lower() in ("none", "cockpit-only"):
        return None
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
    if delivery_str.strip().lower() == "subscribers":
        return {"platform": "email", "target": "subscribers", "format": "send"}
    logger.warning(f"[DISPATCH] Unknown delivery format: '{delivery_str}' — skipping")
    return None


async def _is_workspace_empty_for_daily_update(client, user_id: str) -> bool:
    """Check whether the workspace has anything for daily-update to summarize.

    Empty when: no other active recurrences AND no context-domain entity files.
    Pure SQL — zero LLM cost.
    """
    try:
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
        logger.warning(f"[DISPATCH] Empty workspace check failed: {e}")
        return False


def _build_empty_workspace_markdown(schedule_label: str) -> str:
    from services.deep_links import chat_url, overview_url
    return (
        "# Your workforce is ready\n\n"
        "_0 task runs · 0 proposals pending · 0 reviewer decisions_\n\n"
        "Good morning. There's nothing for me to report yet — your team "
        "hasn't been told what to track. That's by design: I don't "
        "presume to know what matters to you until you tell me.\n\n"
        f"[Open YARNNN →]({chat_url()})\n\n"
        "Tell me about your work — what you're focused on, who you're "
        "tracking, what platforms you use. Tomorrow's update will have "
        "something real to say.\n\n"
        "---\n\n"
        f"*Daily update · {schedule_label} · [View in cockpit]({overview_url()})*\n"
    )


async def _execute_daily_update_empty_state(
    client,
    user_id: str,
    started_at: datetime,
    user_timezone: str = "UTC",
) -> dict:
    """ADR-231 D6 + ADR-161 empty-state writer for daily-update.

    Writes a deterministic template to the natural-home output folder for
    daily-update (a DELIVERABLE recurrence). Zero LLM cost; no agent_runs row.
    """
    from services.workspace import UserMemory
    from services.delivery import deliver_from_output_folder
    from services.recurrence_paths import resolve_paths_for_slug

    task_slug = "daily-update"
    paths = resolve_paths_for_slug(client, user_id, task_slug)
    if paths is None or paths.output_folder is None:
        return {
            "success": False,
            "task_slug": task_slug,
            "status": "no_declaration",
            "message": "No declaration found for daily-update; skipping empty-state.",
        }

    schedule_label = format_daily_local_time_label(user_timezone)
    md_content = _build_empty_workspace_markdown(schedule_label)

    # Substitute {date} placeholder in the output folder
    started_iso = started_at.strftime("%Y-%m-%dT%H00")
    output_folder_abs = paths.output_folder.replace("{date}", started_iso)

    um = UserMemory(client, user_id)

    def _strip_ws(p: str) -> str:
        return p[len("/workspace/"):] if p.startswith("/workspace/") else p

    await um.write(
        _strip_ws(f"{output_folder_abs}/output.md"),
        md_content,
        summary="Daily-update empty-state (deterministic template)",
        authored_by="system:dispatcher",
        message="empty-state daily-update template",
    )

    manifest = {
        "agent_slug": "reporting",
        "created_at": started_at.isoformat(),
        "status": "active",
        "kind": "empty_state",
        "files": [{"path": "output.md", "type": "text/markdown", "role": "primary"}],
    }
    await um.write(
        _strip_ws(f"{output_folder_abs}/manifest.json"),
        json.dumps(manifest, indent=2),
        summary="Daily-update empty-state manifest",
        authored_by="system:dispatcher",
        message="empty-state manifest",
    )

    # Deliver via task delivery (if declaration carries a delivery target)
    delivery_status = "no_destination"
    delivery_error = None
    try:
        from services.recurrence import walk_workspace_recurrences
        decls = walk_workspace_recurrences(client, user_id)
        decl = next((d for d in decls if d.slug == task_slug), None)
        delivery_target = (decl.data.get("delivery") if decl else None) or "email"
        if isinstance(delivery_target, str) and delivery_target.strip():
            destination = _parse_delivery_target(delivery_target.strip(), client, user_id)
            if destination:
                agent_dict = {"id": None, "title": "Daily Update", "role": "executive"}
                delivery_result = await deliver_from_output_folder(
                    client=client,
                    user_id=user_id,
                    agent=agent_dict,
                    output_folder=output_folder_abs,
                    agent_slug="reporting",
                    version_id="",
                    version_number=0,
                    destination=destination,
                    task_slug=task_slug,
                )
                if delivery_result.status.value == "success":
                    delivery_status = "delivered"
                else:
                    delivery_status = "failed"
                    delivery_error = delivery_result.error_message
    except Exception as e:
        delivery_status = "failed"
        delivery_error = str(e)
        logger.warning(f"[DISPATCH] daily-update empty-state delivery failed: {e}")

    # Update scheduling index
    now = datetime.now(timezone.utc)
    next_run = calculate_next_run_at("daily", last_run_at=now, user_timezone=user_timezone)
    try:
        client.table("tasks").update({
            "last_run_at": now.isoformat(),
            "next_run_at": next_run.isoformat() if next_run else None,
            "updated_at": now.isoformat(),
        }).eq("user_id", user_id).eq("slug", task_slug).execute()
    except Exception as e:
        logger.warning(f"[DISPATCH] daily-update empty-state next_run_at update failed: {e}")

    return {
        "success": True,
        "task_slug": task_slug,
        "status": "delivered",
        "message": f"Daily-update empty-state delivered ({delivery_status})",
        "kind": "empty_state",
    }


async def _execute_maintain_overview_empty_state(
    client,
    user_id: str,
    started_at: datetime,
) -> dict:
    """ADR-231 + ADR-204 empty-state writer for maintain-overview.

    Single-section warming-up template at the natural-home output path.
    Zero LLM cost; no agent_runs row.
    """
    from services.workspace import UserMemory
    from services.recurrence_paths import resolve_paths_for_slug

    task_slug = "maintain-overview"
    paths = resolve_paths_for_slug(client, user_id, task_slug)
    if paths is None or paths.output_folder is None:
        return {
            "success": False,
            "task_slug": task_slug,
            "status": "no_declaration",
            "message": "No declaration found for maintain-overview; skipping empty-state.",
        }

    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    output_folder_abs = paths.output_folder.replace("{date}", date_str)

    warming_md = (
        "## Workspace Synthesis\n\n"
        "Your workspace is warming up. Synthesis will deepen as your agents run and "
        "accumulate context. Tell YARNNN what you want to track or produce to get started."
    )

    um = UserMemory(client, user_id)

    def _strip_ws(p: str) -> str:
        return p[len("/workspace/"):] if p.startswith("/workspace/") else p

    try:
        await um.write(
            _strip_ws(f"{output_folder_abs}/output.md"),
            warming_md,
            summary="maintain-overview warming-up state",
            authored_by="system:dispatcher",
            message="empty-state maintain-overview template",
        )
        manifest = {
            "task_slug": task_slug,
            "date": date_str,
            "created_at": now.isoformat(),
            "sections": [{
                "slug": "workspace-synthesis",
                "title": "Workspace Synthesis",
                "kind": "narrative",
                "produced_at": now.isoformat(),
            }],
            "empty_state": True,
        }
        await um.write(
            _strip_ws(f"{output_folder_abs}/sys_manifest.json"),
            json.dumps(manifest, indent=2),
            summary="maintain-overview empty-state manifest",
            authored_by="system:dispatcher",
            message="empty-state manifest",
        )
    except Exception as e:
        logger.warning(f"[DISPATCH] maintain-overview empty-state write failed: {e}")

    try:
        client.table("tasks").update({
            "last_run_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }).eq("user_id", user_id).eq("slug", task_slug).execute()
    except Exception as e:
        logger.warning(f"[DISPATCH] maintain-overview empty-state last_run_at update failed: {e}")

    return {
        "success": True,
        "task_slug": task_slug,
        "status": "delivered",
        "message": "maintain-overview empty-state: workspace warming up",
        "kind": "empty_state",
    }


__all__ = [
    "_total_input_tokens",
    "_microcompact_tool_history",
    "_resolve_max_output_tokens",
    "_load_user_context",
    "_gather_context_domains",
    "gather_task_context",
    "build_task_execution_prompt",
    "_generate",
    "_parse_delivery_target",
    "_is_workspace_empty_for_daily_update",
    "_execute_daily_update_empty_state",
    "_execute_maintain_overview_empty_state",
]

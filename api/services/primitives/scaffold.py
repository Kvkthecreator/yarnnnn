"""
ScaffoldDomains Primitive — ADR-155

TP-driven domain scaffolding: TP decides WHAT entities to create,
this primitive handles HOW (templates, files, trackers).

Single tool call replaces N × WriteWorkspace calls for entity creation.
The TP retains full control over which entities are scaffolded.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


SCAFFOLD_DOMAINS_TOOL = {
    "name": "ScaffoldDomains",
    "description": """Create entity stubs across workspace context domains in one operation.

Use this after learning about the user's work to pre-populate their workspace.
You decide which entities to create — the system handles templates and file structure.

Each entity gets:
- Profile/analysis stub with your provided facts
- [Needs research] markers on unknown sections
- Tracker update per domain

Example:
ScaffoldDomains(entities=[
  {"domain": "competitors", "slug": "cursor", "name": "Cursor", "facts": ["AI code editor by Anysphere", "YC-backed"]},
  {"domain": "competitors", "slug": "copilot", "name": "GitHub Copilot", "facts": ["Microsoft/OpenAI backed"]},
  {"domain": "market", "slug": "ai-coding", "name": "AI Coding Tools", "facts": ["$2B+ market by 2026"]},
])

Only create entities you have reasonable evidence for. Don't guess.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "entities": {
                "type": "array",
                "description": "List of entities to scaffold",
                "items": {
                    "type": "object",
                    "properties": {
                        "domain": {
                            "type": "string",
                            "description": "Context domain: competitors, market, relationships, projects, content_research",
                        },
                        "slug": {
                            "type": "string",
                            "description": "URL-safe identifier (lowercase, hyphenated)",
                        },
                        "name": {
                            "type": "string",
                            "description": "Display name for the entity",
                        },
                        "facts": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Known facts about this entity (1-3 bullets)",
                        },
                    },
                    "required": ["domain", "slug", "name"],
                },
            },
        },
        "required": ["entities"],
    },
}


async def handle_scaffold_domains(auth: Any, input: dict) -> dict:
    """Scaffold entity stubs across context domains.

    TP decides WHAT (which entities in which domains).
    This handler does HOW (template application, file writes, tracker rebuild).
    """
    from services.workspace import UserMemory
    from services.directory_registry import (
        get_entity_stub_content, get_tracker_path, build_tracker_md,
        get_synthesis_content, has_entity_tracker, WORKSPACE_DIRECTORIES,
    )

    entities = input.get("entities", [])
    if not entities:
        return {"success": False, "error": "no_entities", "message": "Provide at least one entity to scaffold"}

    um = UserMemory(auth.client, auth.user_id)
    scaffolded: dict[str, list[str]] = {}
    skipped: dict[str, list[str]] = {}
    total_files = 0

    # Valid domain keys (context domains with entity structure)
    valid_domains = {
        k for k, v in WORKSPACE_DIRECTORIES.items()
        if v.get("type") == "context" and v.get("entity_structure")
    }

    for entity in entities:
        domain_key = entity.get("domain", "")
        slug = entity.get("slug", "")
        name = entity.get("name", "")
        facts = entity.get("facts", [])

        if domain_key not in valid_domains:
            skipped.setdefault(domain_key, []).append(slug)
            continue
        if not slug or not name:
            continue

        domain_def = WORKSPACE_DIRECTORIES[domain_key]
        domain_path = domain_def["path"]

        stub_files = get_entity_stub_content(domain_key, name, facts, source="inferred")

        entity_created = False
        for filename, content in stub_files.items():
            path = f"{domain_path}/{slug}/{filename}"
            existing = await um.read(path)
            # Skip existing non-inferred files (idempotent)
            if existing and "<!-- source: inferred" not in existing:
                continue
            ok = await um.write(path, content, summary=f"Scaffolded: {domain_key}/{slug}")
            if ok:
                total_files += 1
                entity_created = True

        if entity_created:
            scaffolded.setdefault(domain_key, []).append(slug)
        else:
            skipped.setdefault(domain_key, []).append(slug)

    # Rebuild trackers for affected domains
    for domain_key in scaffolded:
        if has_entity_tracker(domain_key):
            tracker_path = get_tracker_path(domain_key)
            if tracker_path:
                domain_path = WORKSPACE_DIRECTORIES[domain_key]["path"]
                entity_list = await _scan_domain_entities(um, domain_path, domain_key)
                tracker_content = build_tracker_md(domain_key, entity_list)
                await um.write(tracker_path, tracker_content, summary="Tracker rebuild after scaffold")

        # Create synthesis file if missing
        synthesis = get_synthesis_content(domain_key)
        if synthesis:
            syn_filename, syn_template = synthesis
            syn_path = f"{WORKSPACE_DIRECTORIES[domain_key]['path']}/{syn_filename}"
            if not await um.read(syn_path) and syn_template:
                await um.write(syn_path, syn_template, summary="Synthesis file scaffold")

    total_entities = sum(len(v) for v in scaffolded.values())
    domains_count = len(scaffolded)

    return {
        "success": True,
        "scaffolded": scaffolded,
        "skipped": {k: v for k, v in skipped.items() if v},
        "total_files": total_files,
        "message": f"Scaffolded {total_entities} entities across {domains_count} domains ({total_files} files)",
    }


async def _scan_domain_entities(um, domain_path: str, domain_key: str) -> list[dict]:
    """Scan workspace files to build entity list for tracker rebuild."""
    from services.directory_registry import WORKSPACE_DIRECTORIES

    try:
        all_files = um._db.table("workspace_files").select(
            "path, updated_at"
        ).eq("user_id", um._user_id).like(
            "path", f"/workspace/{domain_path}/%"
        ).execute()
    except Exception:
        return []

    entities: dict[str, dict] = {}
    for row in (all_files.data or []):
        path = row["path"]
        parts = path.replace(f"/workspace/{domain_path}/", "").split("/")
        if len(parts) < 2:
            continue
        slug = parts[0]
        if slug.startswith("_"):
            continue

        if slug not in entities:
            entities[slug] = {
                "slug": slug,
                "name": slug.replace("-", " ").title(),
                "last_updated": row.get("updated_at", "—"),
                "files": [],
                "status": "active",
            }
        filename = parts[-1]
        if filename not in entities[slug]["files"]:
            entities[slug]["files"].append(filename)
        updated = row.get("updated_at")
        if updated and updated > entities[slug]["last_updated"]:
            entities[slug]["last_updated"] = updated

    return list(entities.values())

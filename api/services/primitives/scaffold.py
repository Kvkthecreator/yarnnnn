"""
ManageDomains Primitive — ADR-155 + ADR-157

CRUD operations on workspace context domain entities.
TP decides WHAT entities to create/manage, this primitive handles HOW.

Actions:
  scaffold: Bulk entity creation (onboarding, identity update)
  add: Single entity creation (steady-state)
  remove: Deprecate an entity (mark inactive in tracker)
  list: List entities in a domain

ADR-157: When entities have a `url` field, fetches favicon via render service.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

import httpx

logger = logging.getLogger(__name__)

RENDER_SERVICE_URL = os.environ.get("RENDER_SERVICE_URL", "https://yarnnn-render.onrender.com")
RENDER_SERVICE_SECRET = os.environ.get("RENDER_SERVICE_SECRET", "")


MANAGE_DOMAINS_TOOL = {
    "name": "ManageDomains",
    "description": """Manage entities in workspace context domains (competitors, market, relationships, projects, content_research).

**action="scaffold"** — Bulk entity creation. Use after learning about the user's work to pre-populate their workspace across multiple domains at once.
  ManageDomains(action="scaffold", entities=[
    {"domain": "competitors", "slug": "cursor", "name": "Cursor", "url": "cursor.com", "facts": ["AI code editor"]},
    {"domain": "market", "slug": "ai-coding", "name": "AI Coding Tools", "facts": ["Fast-growing segment"]},
  ])

**action="add"** — Add a single entity to a domain. Use during steady-state when the user mentions a new competitor, contact, or project.
  ManageDomains(action="add", domain="competitors", slug="anthropic", name="Anthropic", url="anthropic.com", facts=["Claude API", "Safety-focused"])

**action="remove"** — Deprecate an entity (marks inactive in tracker, does not delete files).
  ManageDomains(action="remove", domain="competitors", slug="old-company")

**action="list"** — List entities in a domain with status and file counts.
  ManageDomains(action="list", domain="competitors")

Each scaffolded entity gets stub files with your provided facts + [Needs research] markers.
Only create entities you have reasonable evidence for. Don't guess.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["scaffold", "add", "remove", "list"],
                "description": "Operation: scaffold (bulk), add (single), remove (deprecate), list (query)",
            },
            "entities": {
                "type": "array",
                "description": "For action=scaffold: list of entities to create across domains",
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
                        "url": {
                            "type": "string",
                            "description": "Entity's website domain (e.g., 'cursor.com'). Used to fetch favicon.",
                        },
                    },
                    "required": ["domain", "slug", "name"],
                },
            },
            "domain": {
                "type": "string",
                "description": "For action=add/remove/list: the target domain",
            },
            "slug": {
                "type": "string",
                "description": "For action=add/remove: entity slug",
            },
            "name": {
                "type": "string",
                "description": "For action=add: entity display name",
            },
            "facts": {
                "type": "array",
                "items": {"type": "string"},
                "description": "For action=add: known facts (1-3 bullets)",
            },
            "url": {
                "type": "string",
                "description": "For action=add: entity's website domain for favicon fetch",
            },
        },
        "required": ["action"],
    },
}


async def handle_manage_domains(auth: Any, input: dict) -> dict:
    """Route ManageDomains to appropriate action handler."""
    action = input.get("action", "scaffold")

    if action == "scaffold":
        return await _handle_scaffold(auth, input)
    elif action == "add":
        return await _handle_add(auth, input)
    elif action == "remove":
        return await _handle_remove(auth, input)
    elif action == "list":
        return await _handle_list(auth, input)
    else:
        return {"success": False, "error": "invalid_action", "message": f"Unknown action: {action}"}


async def _handle_scaffold(auth: Any, input: dict) -> dict:
    """Bulk entity creation across domains. Onboarding + identity update path."""
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

    # ADR-157: Collect entities with URLs for batch favicon fetching
    favicon_requests: list[dict] = []

    for entity in entities:
        domain_key = entity.get("domain", "")
        slug = entity.get("slug", "")
        name = entity.get("name", "")
        facts = entity.get("facts", [])
        entity_url = entity.get("url", "")

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
            # ADR-157: Queue favicon fetch for entities with URL
            if entity_url:
                favicon_requests.append({
                    "domain_path": domain_path,
                    "slug": slug,
                    "url": entity_url,
                })
        else:
            skipped.setdefault(domain_key, []).append(slug)

    # ADR-157: Fetch favicons for scaffolded entities (non-blocking)
    favicon_results = await _fetch_favicons_batch(um, auth.user_id, favicon_requests)
    total_files += favicon_results.get("fetched", 0)

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
        "action": "scaffold",
        "scaffolded": scaffolded,
        "skipped": {k: v for k, v in skipped.items() if v},
        "total_files": total_files,
        "favicons": favicon_results,
        "message": f"Scaffolded {total_entities} entities across {domains_count} domains ({total_files} files, {favicon_results.get('fetched', 0)} favicons)",
    }


async def _handle_add(auth: Any, input: dict) -> dict:
    """Add a single entity to a domain. Steady-state use."""
    # Reuse scaffold with a single-element entities list
    entity = {
        "domain": input.get("domain", ""),
        "slug": input.get("slug", ""),
        "name": input.get("name", ""),
        "facts": input.get("facts", []),
        "url": input.get("url", ""),
    }
    if not entity["domain"] or not entity["slug"] or not entity["name"]:
        return {"success": False, "error": "missing_fields", "message": "action=add requires domain, slug, and name"}

    result = await _handle_scaffold(auth, {"entities": [entity]})
    result["action"] = "add"
    return result


async def _handle_remove(auth: Any, input: dict) -> dict:
    """Mark an entity as inactive in its domain tracker."""
    from services.workspace import UserMemory
    from services.directory_registry import (
        get_tracker_path, build_tracker_md, has_entity_tracker, WORKSPACE_DIRECTORIES,
    )

    domain_key = input.get("domain", "")
    slug = input.get("slug", "")
    if not domain_key or not slug:
        return {"success": False, "error": "missing_fields", "message": "action=remove requires domain and slug"}

    if domain_key not in WORKSPACE_DIRECTORIES:
        return {"success": False, "error": "invalid_domain", "message": f"Unknown domain: {domain_key}"}

    um = UserMemory(auth.client, auth.user_id)
    domain_path = WORKSPACE_DIRECTORIES[domain_key]["path"]

    # Check entity exists
    entity_files = um._db.table("workspace_files").select(
        "path"
    ).eq("user_id", auth.user_id).like(
        "path", f"/workspace/{domain_path}/{slug}/%"
    ).limit(1).execute()

    if not (entity_files.data or []):
        return {"success": False, "error": "not_found", "message": f"Entity {slug} not found in {domain_key}"}

    # Add deprecation marker to the entity's primary file
    primary_path = f"{domain_path}/{slug}/profile.md"
    existing = await um.read(primary_path)
    if existing and "<!-- status: inactive -->" not in existing:
        await um.write(primary_path, f"<!-- status: inactive -->\n{existing}",
                       summary=f"Deprecated: {domain_key}/{slug}")

    # Rebuild tracker
    if has_entity_tracker(domain_key):
        tracker_path = get_tracker_path(domain_key)
        if tracker_path:
            entity_list = await _scan_domain_entities(um, domain_path, domain_key)
            tracker_content = build_tracker_md(domain_key, entity_list)
            await um.write(tracker_path, tracker_content, summary="Tracker rebuild after remove")

    return {
        "success": True,
        "action": "remove",
        "domain": domain_key,
        "slug": slug,
        "message": f"Marked {slug} as inactive in {domain_key}",
    }


async def _handle_list(auth: Any, input: dict) -> dict:
    """List entities in a domain with status and file counts."""
    from services.workspace import UserMemory
    from services.directory_registry import WORKSPACE_DIRECTORIES

    domain_key = input.get("domain", "")
    if not domain_key or domain_key not in WORKSPACE_DIRECTORIES:
        return {"success": False, "error": "invalid_domain", "message": f"Provide a valid domain: {', '.join(k for k, v in WORKSPACE_DIRECTORIES.items() if v.get('type') == 'context')}"}

    um = UserMemory(auth.client, auth.user_id)
    domain_path = WORKSPACE_DIRECTORIES[domain_key]["path"]
    entity_list = await _scan_domain_entities(um, domain_path, domain_key)

    return {
        "success": True,
        "action": "list",
        "domain": domain_key,
        "entities": entity_list,
        "count": len(entity_list),
        "message": f"{len(entity_list)} entities in {domain_key}",
    }


# =============================================================================
# Internal helpers
# =============================================================================

async def _fetch_favicons_batch(um, user_id: str, requests: list[dict]) -> dict:
    """ADR-157: Fetch favicons for entities via render service.

    Non-blocking: individual failures are logged but don't fail scaffolding.
    Each favicon is stored as a workspace file with content_url.
    """
    if not requests:
        return {"fetched": 0, "failed": 0}

    fetched = 0
    failed = 0
    headers = {}
    if RENDER_SERVICE_SECRET:
        headers["X-Render-Secret"] = RENDER_SERVICE_SECRET

    async with httpx.AsyncClient(timeout=15.0) as client:
        for req in requests:
            domain_path = req["domain_path"]
            slug = req["slug"]
            url = req["url"]
            ws_path = f"{domain_path}/assets/{slug}-favicon.png"

            # Skip if favicon already exists
            existing = await um.read(ws_path)
            if existing:
                continue

            try:
                resp = await client.post(
                    f"{RENDER_SERVICE_URL}/render",
                    json={
                        "type": "fetch-asset",
                        "input": {
                            "url": url,
                            "asset_type": "favicon",
                            "size": 128,
                        },
                        "output_format": "png",
                        "filename": f"favicon-{slug}",
                        "user_id": user_id,
                    },
                    headers=headers,
                )
                resp.raise_for_status()
                result = resp.json()

                if result.get("success") and result.get("output_url"):
                    ok = await um.write(
                        ws_path,
                        f"Favicon for {url}",
                        content_type="image/png",
                        content_url=result["output_url"],
                        metadata={
                            "asset_type": "favicon",
                            "source_url": url,
                            "size_bytes": result.get("size_bytes", 0),
                        },
                        summary=f"Favicon: {slug}",
                    )
                    if ok:
                        fetched += 1
                    else:
                        failed += 1
                else:
                    logger.warning(f"[MANAGE_DOMAINS] Favicon fetch failed for {url}: {result.get('error', 'unknown')}")
                    failed += 1

            except Exception as e:
                logger.warning(f"[MANAGE_DOMAINS] Favicon fetch failed for {url}: {e}")
                failed += 1

    if fetched:
        logger.info(f"[MANAGE_DOMAINS] Fetched {fetched} favicons ({failed} failed)")

    return {"fetched": fetched, "failed": failed}


async def _scan_domain_entities(um, domain_path: str, domain_key: str) -> list[dict]:
    """Scan workspace files to build entity list for tracker rebuild."""
    from services.directory_registry import WORKSPACE_DIRECTORIES

    try:
        all_files = um._db.table("workspace_files").select(
            "path, updated_at, content"
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
        if slug.startswith("_") or slug == "assets":
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

        # Check for inactive marker
        content = row.get("content", "")
        if content and "<!-- status: inactive -->" in content:
            entities[slug]["status"] = "inactive"

    return list(entities.values())

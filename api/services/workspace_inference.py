"""
Workspace-Wide Inference Engine — ADR-155

When the user provides identity context, infers what entities should
exist across ALL context domains and scaffolds entity stubs. Invests
~$0.02 upstream (Haiku) to save ~$1+ downstream (bootstrap research).

Trigger: called after UpdateContext(target="identity") writes IDENTITY.md.
Output: entity stubs in /workspace/context/{domain}/{entity}/ with
        [Needs research] gap markers and <!-- source: inferred --> tags.

Three safeguards:
1. Source tagging — inferred vs user_stated vs researched
2. Explicit gap markers — stubs say what's unknown
3. Idempotent — skips existing non-inferred files, replaces inferred stubs
"""
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

INFERENCE_MODEL = "claude-haiku-4-5-20251001"
INFERENCE_MAX_TOKENS = 2048

# Domains eligible for entity inference (must have entity_structure)
_INFERENCE_SOURCE_TAG = "<!-- source: inferred -->"


# =============================================================================
# System prompt for workspace inference
# =============================================================================

_INFERENCE_SYSTEM = """You analyze a user's workspace identity to infer what entities should exist in their workspace context domains.

Available domains and what they track:
- competitors: Companies/products they compete with (entity_type: company)
- market: Market segments relevant to their work (entity_type: segment)
- relationships: Categories of people they work with (entity_type: contact/category)
- projects: Internal initiatives they're likely working on (entity_type: project)
- content_research: Topics they'd need content about (entity_type: topic)

Rules:
- Only infer entities you have REASONABLE EVIDENCE for from the identity/brand text
- Each entity needs: slug (lowercase-hyphenated), name (display name), confidence (high|medium), known_facts (1-3 bullet points)
- confidence: "high" = explicitly mentioned or clearly implied, "medium" = reasonable industry inference
- Do NOT include low-confidence guesses — omit uncertain entities entirely
- For relationships, infer CATEGORIES (e.g., "investors", "customers") not specific people unless named
- For projects, only infer if explicitly mentioned (e.g., "raising Series A" → fundraise project)
- Output valid JSON only. No markdown fencing, no explanation text.

Output schema:
{
  "domains": {
    "competitors": [{"slug": "cursor", "name": "Cursor", "confidence": "high", "known_facts": ["AI-powered code editor by Anysphere"]}],
    "market": [{"slug": "ai-coding-tools", "name": "AI Coding Tools", "confidence": "high", "known_facts": ["IDE-integrated AI assistants"]}],
    ...
  }
}

Only include domains that have at least one entity. Omit empty domains."""


# =============================================================================
# Core functions
# =============================================================================

async def infer_workspace_entities(
    identity_content: str,
    brand_content: str = "",
    notes_content: str = "",
) -> dict:
    """Haiku call to infer entity roster across all context domains.

    Args:
        identity_content: IDENTITY.md content (required)
        brand_content: BRAND.md content (optional — audience, positioning signals)
        notes_content: notes.md content (optional — user-stated facts about their work)

    Returns:
        {"domains": {domain_key: [{slug, name, confidence, known_facts}]}}
        Empty dict on failure.
    """
    from services.anthropic import chat_completion

    if not identity_content or len(identity_content.strip()) < 20:
        logger.info("[WORKSPACE_INFERENCE] Identity too sparse, skipping inference")
        return {}

    source_parts = [f"## IDENTITY.md\n{identity_content.strip()}"]
    if brand_content and brand_content.strip():
        source_parts.append(f"\n\n## BRAND.md\n{brand_content.strip()}")
    if notes_content and notes_content.strip():
        # Only include facts/instructions, not preferences (they don't inform entities)
        relevant_notes = "\n".join(
            line for line in notes_content.strip().split("\n")
            if line.strip() and not line.strip().startswith("preference:")
        )
        if relevant_notes:
            source_parts.append(f"\n\n## User Notes\n{relevant_notes}")

    user_message = (
        "Based on the workspace identity below, infer what entities should exist "
        "in each context domain. Output valid JSON only.\n\n"
        + "\n".join(source_parts)
    )

    try:
        response = await chat_completion(
            messages=[{"role": "user", "content": user_message}],
            system=_INFERENCE_SYSTEM,
            model=INFERENCE_MODEL,
            max_tokens=INFERENCE_MAX_TOKENS,
        )

        # Parse JSON — handle common Haiku quirks
        text = response.strip()
        # Strip markdown fencing if present
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)

        result = json.loads(text)

        # Validate structure
        domains = result.get("domains", {})
        if not isinstance(domains, dict):
            logger.warning("[WORKSPACE_INFERENCE] Invalid domains structure")
            return {}

        # Filter to valid domain keys only
        from services.directory_registry import WORKSPACE_DIRECTORIES
        valid_keys = {
            k for k, v in WORKSPACE_DIRECTORIES.items()
            if v.get("type") == "context" and v.get("entity_structure")
        }

        filtered = {}
        for key, entities in domains.items():
            if key not in valid_keys:
                continue
            if not isinstance(entities, list):
                continue
            # Filter to high/medium confidence only
            valid_entities = [
                e for e in entities
                if isinstance(e, dict)
                and e.get("slug")
                and e.get("name")
                and e.get("confidence") in ("high", "medium")
            ]
            if valid_entities:
                filtered[key] = valid_entities

        logger.info(
            f"[WORKSPACE_INFERENCE] Inferred {sum(len(v) for v in filtered.values())} "
            f"entities across {len(filtered)} domains"
        )
        return {"domains": filtered}

    except json.JSONDecodeError as e:
        logger.warning(f"[WORKSPACE_INFERENCE] JSON parse failed: {e}")
        return {}
    except Exception as e:
        logger.error(f"[WORKSPACE_INFERENCE] Inference call failed: {e}")
        return {}


async def scaffold_inferred_entities(
    client: Any,
    user_id: str,
    inference_result: dict,
) -> dict:
    """Create entity stubs in workspace from inference result.

    Idempotent: skips files that exist and aren't inferred stubs.
    Rebuilds _tracker.md from filesystem scan (includes manual entities).

    Returns:
        {"scaffolded": {domain: [slugs]}, "skipped": {domain: [slugs]}, "total_files": N}
    """
    from services.workspace import UserMemory
    from services.directory_registry import (
        get_entity_stub_content, get_tracker_path, build_tracker_md,
        get_synthesis_content, has_entity_tracker, WORKSPACE_DIRECTORIES,
    )

    um = UserMemory(client, user_id)
    domains = inference_result.get("domains", {})
    scaffolded: dict[str, list[str]] = {}
    skipped: dict[str, list[str]] = {}
    total_files = 0
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for domain_key, entities in domains.items():
        domain_def = WORKSPACE_DIRECTORIES.get(domain_key)
        if not domain_def or not domain_def.get("entity_structure"):
            continue

        domain_path = domain_def["path"]
        scaffolded[domain_key] = []
        skipped[domain_key] = []

        for entity in entities:
            slug = entity["slug"]
            name = entity["name"]
            known_facts = entity.get("known_facts", [])

            # Get enriched stub content
            stub_files = get_entity_stub_content(
                domain_key, name, known_facts, source="inferred",
            )

            entity_created = False
            for filename, content in stub_files.items():
                path = f"{domain_path}/{slug}/{filename}"
                # Idempotency: check if file exists
                existing = await um.read(path)
                if existing and _INFERENCE_SOURCE_TAG not in existing:
                    # Non-inferred file exists — don't overwrite
                    continue
                # Write (creates new or replaces prior inferred stub)
                ok = await um.write(path, content, summary=f"Inferred entity: {domain_key}/{slug}")
                if ok:
                    total_files += 1
                    entity_created = True

            if entity_created:
                scaffolded[domain_key].append(slug)
            else:
                skipped[domain_key].append(slug)

        # Rebuild tracker from filesystem scan
        if has_entity_tracker(domain_key):
            tracker_path = get_tracker_path(domain_key)
            if tracker_path:
                # Scan domain folder for all entity slugs
                entity_list = await _scan_domain_entities(um, domain_path, domain_key)
                tracker_content = build_tracker_md(domain_key, entity_list)
                await um.write(tracker_path, tracker_content, summary=f"Tracker rebuild after inference")

        # Create synthesis file if it doesn't exist
        synthesis = get_synthesis_content(domain_key)
        if synthesis:
            syn_filename, syn_template = synthesis
            syn_path = f"{domain_path}/{syn_filename}"
            existing_syn = await um.read(syn_path)
            if not existing_syn and syn_template:
                await um.write(syn_path, syn_template, summary=f"Synthesis file scaffold")
                total_files += 1

    # Remove empty entries
    scaffolded = {k: v for k, v in scaffolded.items() if v}
    skipped = {k: v for k, v in skipped.items() if v}

    return {
        "scaffolded": scaffolded,
        "skipped": skipped,
        "total_files": total_files,
    }


async def _scan_domain_entities(um, domain_path: str, domain_key: str) -> list[dict]:
    """Scan workspace files to build entity list for tracker rebuild."""
    from services.directory_registry import WORKSPACE_DIRECTORIES

    domain_def = WORKSPACE_DIRECTORIES.get(domain_key, {})
    entity_structure = domain_def.get("entity_structure", {})
    expected_files = list(entity_structure.keys())

    # List all files under domain path
    try:
        all_files = um._db.table("workspace_files").select(
            "path, updated_at"
        ).eq("user_id", um._user_id).like(
            "path", f"/workspace/{domain_path}/%"
        ).execute()
    except Exception:
        return []

    # Group by entity slug
    entities: dict[str, dict] = {}
    for row in (all_files.data or []):
        path = row["path"]
        # Extract slug: /workspace/context/competitors/{slug}/{file}
        parts = path.replace(f"/workspace/{domain_path}/", "").split("/")
        if len(parts) < 2:
            continue  # synthesis/tracker files, not entities
        slug = parts[0]
        if slug.startswith("_"):
            continue  # _tracker.md, _landscape.md etc

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
        # Track latest update
        updated = row.get("updated_at")
        if updated and updated > entities[slug]["last_updated"]:
            entities[slug]["last_updated"] = updated

    return list(entities.values())


async def update_inference_state(
    client: Any,
    user_id: str,
    scaffold_result: dict,
) -> bool:
    """Persist inference state to AWARENESS.md."""
    from services.workspace import UserMemory

    um = UserMemory(client, user_id)
    awareness = await um.read("AWARENESS.md") or ""
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    scaffolded = scaffold_result.get("scaffolded", {})

    # Build inference state section
    state_lines = [
        "\n## Inference State",
        f"Last inference: {now_str} from identity update\n",
        "### Scaffolded Domains",
    ]
    for domain_key, slugs in scaffolded.items():
        state_lines.append(f"- {domain_key}: {len(slugs)} entities ({', '.join(slugs)}) — source: inferred")

    if not scaffolded:
        state_lines.append("- No entities inferred (identity may be too sparse)")

    state_lines.append("\n### Pending Validation")
    state_lines.append("- All inferred entities awaiting first research cycle for verification")

    inference_section = "\n".join(state_lines)

    # Replace existing inference state or append
    if "## Inference State" in awareness:
        # Replace section (everything from ## Inference State to next ## or end)
        awareness = re.sub(
            r"\n## Inference State.*?(?=\n## |\Z)",
            inference_section,
            awareness,
            flags=re.DOTALL,
        )
    else:
        awareness = awareness.rstrip() + "\n" + inference_section + "\n"

    return await um.write("AWARENESS.md", awareness, summary="Workspace inference state update")


# =============================================================================
# Orchestrator
# =============================================================================

async def run_workspace_inference(client: Any, user_id: str) -> dict:
    """Full workspace inference pipeline: infer → scaffold → persist state.

    Called after UpdateContext(target="identity"|"brand") succeeds.
    Reads all workspace-level files that may contain entity signals:
    - IDENTITY.md (primary — required, gates execution)
    - BRAND.md (supplementary — audience, positioning)
    - notes.md (supplementary — user-stated facts about their work)

    Non-fatal: failure returns {"success": False} but never raises.
    """
    from services.workspace import UserMemory

    try:
        um = UserMemory(client, user_id)
        identity = await um.read("IDENTITY.md")
        if not identity or len(identity.strip()) < 20:
            return {"success": False, "reason": "identity_too_sparse"}

        brand = await um.read("BRAND.md") or ""
        notes = await um.read("notes.md") or ""

        # Step 1: Infer entities from workspace context files
        inference = await infer_workspace_entities(identity, brand, notes)
        if not inference or not inference.get("domains"):
            return {"success": False, "reason": "no_entities_inferred"}

        # Step 2: Scaffold entity stubs in workspace
        scaffold_result = await scaffold_inferred_entities(client, user_id, inference)

        # Step 3: Persist inference state to AWARENESS.md
        await update_inference_state(client, user_id, scaffold_result)

        # Step 4: Activity log
        try:
            from services.activity_log import write_activity
            total_entities = sum(len(v) for v in scaffold_result.get("scaffolded", {}).values())
            await write_activity(
                client=client,
                user_id=user_id,
                event_type="workspace_inference",
                summary=f"Inferred {total_entities} entities across {len(scaffold_result.get('scaffolded', {}))} domains",
                metadata={
                    "scaffolded": scaffold_result.get("scaffolded", {}),
                    "total_files": scaffold_result.get("total_files", 0),
                },
            )
        except Exception as e:
            logger.debug(f"[WORKSPACE_INFERENCE] Activity log failed: {e}")

        logger.info(
            f"[WORKSPACE_INFERENCE] Complete: {scaffold_result.get('total_files', 0)} files "
            f"across {len(scaffold_result.get('scaffolded', {}))} domains"
        )

        return {
            "success": True,
            **scaffold_result,
        }

    except Exception as e:
        logger.error(f"[WORKSPACE_INFERENCE] Pipeline failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}

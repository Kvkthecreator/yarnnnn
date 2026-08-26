"""
Reference Parsing and Resolution (ADR-072 Unified Content Layer)

Grammar: <type>:<identifier>[/<subpath>][?<query>]

Examples:
  agent:uuid-123          # Specific by ID
  agent:latest            # Most recent
  platform:slack                # By provider name
  platform:slack/credentials    # Sub-entity
  session:current               # Special reference

Entity types:
  - agent: Content agents
  - version: Agent versions (generated content)
  - platform: Connected platforms (platform_connections)
  - memory: Knowledge entries (user facts, preferences)
  - session: Chat sessions
  - domain: Knowledge domains
  - document: Uploaded documents (filesystem_documents)
  - action: Executable actions (for discovery)
  - system: System-level targets (signals, scheduler, etc.)

NOTE: 'memory' and 'domain' entity types retired by ADR-196 (2026-04-19).
Memory is filesystem-native at /workspace/*.md since ADR-156; the entity
path is gone with the user_memory table.

Special identifiers:
  - new: For Write operations (create)
  - current: Current active entity
  - latest: Most recently modified
  - *: All entities of type
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional, Union, List, Dict
from urllib.parse import parse_qs
import re


@dataclass
class EntityRef:
    """Parsed entity reference."""
    entity_type: str
    identifier: str
    subpath: Optional[str] = None
    query: dict = field(default_factory=dict)

    @property
    def is_collection(self) -> bool:
        """Returns True if this ref targets multiple entities."""
        return self.identifier == "*" or bool(self.query)

    @property
    def is_create(self) -> bool:
        """Returns True if this is a create operation (identifier='new')."""
        return self.identifier == "new"

    def __str__(self) -> str:
        """Reconstruct the reference string."""
        result = f"{self.entity_type}:{self.identifier}"
        if self.subpath:
            result += f"/{self.subpath}"
        if self.query:
            params = "&".join(f"{k}={v}" for k, v in self.query.items())
            result += f"?{params}"
        return result


# Valid entity types — the /proc core (ADR-322): genuinely-non-file DB objects.
ENTITY_TYPES = {
    "platform",
    "session",
    # 2026-08-26: "agent" and "version" removed with the pre-ADR-596 agent
    #   model. They addressed the `agents` / `agent_runs` tables, which held
    #   ZERO rows in production, so every ref resolved to None (or [] for a
    #   collection query). A being is NOT an entity-ref target: it lives in
    #   `services/agents_registry.AGENTS` as static kernel data, not a
    #   per-workspace DB row an LLM looks up.
    # ADR-322: "document" and "task" removed — they are not /proc records.
    #   document → a FILE (ADR-197: workspace_files row at uploads/{slug}.md).
    #     Reads move to the file family: SearchFiles(path_prefix='uploads/') +
    #     ReadFile('uploads/...'). The document:uuid ref grammar had no external
    #     callers (only the entity layer's own self-referential tool docs).
    #   task → a REDIRECT (ADR-231: thin scheduling index; recurrences are YAML
    #     files). LookupEntity already steered task slugs to ReadFile + Schedule.
    #     Recurrence interaction is Schedule / FireInvocation / ReadFile of the
    #     YAML. The thin `tasks` scheduling-index TABLE stays; it is just no
    #     longer addressed via the entity-ref grammar.
    # ADR-168 Commit 2: "action" and "system" removed (Execute-primitive residue).
    # ADR-196: "memory" and "domain" removed (user_memory table dropped).
}

# Special identifiers
SPECIAL_IDENTIFIERS = {"new", "current", "latest", "*"}

# Reference pattern: type:identifier[/subpath][?query]
# Identifier can include dots for action namespacing (e.g., platform.sync)
REF_PATTERN = re.compile(
    r"^(?P<type>[a-z]+):(?P<identifier>[a-zA-Z0-9_.*-]+)"
    r"(?:/(?P<subpath>[a-zA-Z0-9_/-]+))?"
    r"(?:\?(?P<query>.+))?$"
)


def parse_ref(ref: str) -> EntityRef:
    """
    Parse a reference string into an EntityRef.

    Args:
        ref: Reference string like "agent:uuid-123" or "memory:?type=fact"

    Returns:
        EntityRef with parsed components

    Raises:
        ValueError: If reference format is invalid
    """
    # Handle query-only refs like "memory:?type=fact"
    if ":?" in ref:
        parts = ref.split(":?", 1)
        entity_type = parts[0]
        query_str = parts[1] if len(parts) > 1 else ""

        if entity_type not in ENTITY_TYPES:
            raise ValueError(f"Unknown entity type: {entity_type}")

        query = {}
        if query_str:
            parsed = parse_qs(query_str)
            query = {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}

        return EntityRef(
            entity_type=entity_type,
            identifier="*",  # Query implies collection
            query=query,
        )

    match = REF_PATTERN.match(ref)
    if not match:
        raise ValueError(f"Invalid reference format: {ref}")

    entity_type = match.group("type")
    identifier = match.group("identifier")
    subpath = match.group("subpath")
    query_str = match.group("query")

    if entity_type not in ENTITY_TYPES:
        raise ValueError(f"Unknown entity type: {entity_type}")

    query = {}
    if query_str:
        parsed = parse_qs(query_str)
        query = {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}

    return EntityRef(
        entity_type=entity_type,
        identifier=identifier,
        subpath=subpath,
        query=query,
    )


# Table mappings for entity types (ADR-322: the /proc core — 4 DB objects).
TABLE_MAP = {
    # 2026-08-26: "agent" -> agents and "version" -> agent_runs removed (see
    # ENTITY_TYPES above). ⚠️ ENTITY_TYPES and TABLE_MAP are two literals that
    # must be edited TOGETHER — a type in one but not the other either raises
    # "No table mapping for entity type" or silently becomes unaddressable.
    "platform": "platform_connections",
    "session": "chat_sessions",
    # ADR-322: "document" (→ file: SearchFiles/ReadFile on uploads/) and "task"
    # (→ Schedule/FireInvocation/ReadFile of the recurrence YAML) removed.
    # ADR-196: "memory" and "domain" entries removed (user_memory table dropped).
}


async def resolve_ref(
    ref: EntityRef,
    auth: Any,
    for_write: bool = False,
) -> Union[Dict, List[Dict], None]:
    """
    Resolve a reference to actual entity data.

    Args:
        ref: Parsed EntityRef
        auth: Auth context with user_id and supabase client
        for_write: If True, returns None for 'new' identifier (creation)

    Returns:
        Entity dict, list of entities, or None if not found / creating new

    Raises:
        PermissionError: If entity belongs to different user
        ValueError: If entity type has no table mapping
    """
    # Handle create refs
    if ref.is_create:
        if for_write:
            return None  # Signal to create new
        raise ValueError("Cannot read from 'new' reference")

    # ADR-168 Commit 2: "action" and "system" branches removed along with Execute.

    table = TABLE_MAP.get(ref.entity_type)
    if not table:
        raise ValueError(f"No table mapping for entity type: {ref.entity_type}")

    client = auth.client

    # Build query
    query = client.table(table).select("*")

    # Always scope to user
    query = query.eq("user_id", auth.user_id)

    # Handle special identifiers
    if ref.identifier == "*":
        # Collection query - apply filters from query params
        if "limit" in ref.query:
            query = query.limit(int(ref.query["limit"]))
        # ADR-196: memory-by-tag query removed (user_memory table dropped).
        # ADR-322: "task" removed from the status-filter set (no longer an entity type).
        result = query.execute()
        return result.data if result.data else []

    elif ref.identifier == "latest":
        # Get most recently modified
        query = query.order("updated_at", desc=True).limit(1)
        result = query.execute()
        return result.data[0] if result.data else None

    elif ref.identifier == "current":
        # Handle current session specially
        if ref.entity_type == "session":
            # This would need session context from request
            raise ValueError("'current' session requires request context")
        raise ValueError(f"'current' not supported for {ref.entity_type}")

    else:
        # Specific identifier - could be UUID or name
        # Try UUID first, then name-based lookup
        if ref.entity_type == "platform":
            # Platforms use platform name
            query = query.eq("platform", ref.identifier)
            # ADR-048: Live search removed - use MCP tools directly
            # (mcp__notion__notion-search, mcp__slack__slack_search_*, etc.)
        else:
            # Others use id
            query = query.eq("id", ref.identifier)

        result = query.execute()

        if not result.data:
            return None

        entity = result.data[0]

        # Handle subpath for nested data
        if ref.subpath:
            return _extract_subpath(entity, ref.subpath)

        # ADR-322: document-enrich removed — documents are files now; read them
        # via ReadFile('uploads/...'), not LookupEntity(document:uuid).

        # Special handling for platforms: include sync status from sync_registry
        if ref.entity_type == "platform":
            entity = await _enrich_platform_with_sync_status(client, auth.user_id, entity)

        return entity


# ADR-322: _enrich_document_with_content DELETED. Documents are files now —
# read them via ReadFile('uploads/{slug}.md'), which returns the full content
# directly (the markdown body IS the document). No document-ref enrichment.


async def _enrich_platform_with_sync_status(client: Any, user_id: str, platform: dict) -> dict:
    """
    Enrich a platform connection with sync status from sync_registry.

    The platform_connections table stores connection metadata and landscape
    (available resources), but sync status (last_synced_at, item_count) is
    tracked separately in sync_registry. This function merges them so TP
    sees the complete picture.
    """
    platform_name = platform.get("platform")
    if not platform_name:
        return platform

    try:
        # Get sync records for this platform
        sync_result = client.table("sync_registry").select(
            "resource_id, resource_name, last_synced_at, item_count, source_latest_at"
        ).eq("user_id", user_id).eq("platform", platform_name).execute()

        sync_by_id = {s["resource_id"]: s for s in (sync_result.data or [])}

        # Calculate total synced items across all resources
        total_synced_items = sum(s.get("item_count", 0) for s in (sync_result.data or []))
        last_synced_at = None
        if sync_result.data:
            synced_times = [s["last_synced_at"] for s in sync_result.data if s.get("last_synced_at")]
            if synced_times:
                last_synced_at = max(synced_times)

        # Add sync summary to platform
        platform["sync_status"] = {
            "total_items_synced": total_synced_items,
            "last_synced_at": last_synced_at,
            "synced_resources_count": len([s for s in sync_result.data or [] if s.get("last_synced_at")]),
        }

        # Enrich landscape resources with sync data
        landscape = platform.get("landscape", {}) or {}
        resources = landscape.get("resources", [])

        if resources:
            for resource in resources:
                resource_id = resource.get("id")
                sync_data = sync_by_id.get(resource_id, {})

                if sync_data:
                    resource["last_synced_at"] = sync_data.get("last_synced_at")
                    resource["item_count"] = sync_data.get("item_count", 0)
                    resource["source_latest_at"] = sync_data.get("source_latest_at")
                    resource["coverage_state"] = "covered"
                else:
                    resource["coverage_state"] = "uncovered"
                    resource["item_count"] = 0

            landscape["resources"] = resources
            platform["landscape"] = landscape

    except Exception as e:
        import logging
        logging.warning(f"[REFS] Failed to enrich platform with sync status: {e}")
        # Return platform without enrichment rather than failing
        platform["sync_status"] = {"error": str(e)}

    return platform


# ADR-048: Live search functions removed.
# TP should use MCP tools directly:
#   - mcp__notion__notion-search for Notion
#   - mcp__slack__slack_search_* for Slack


# _resolve_version_ref DELETED 2026-08-26 with the `version` entity type.
# It existed because `agent_runs` has no user_id — ownership had to be proven
# through the parent `agents` row. Both tables are gone from the entity layer.

def _extract_subpath(entity: dict, subpath: str) -> Any:
    """Extract nested data from entity using subpath."""
    parts = subpath.split("/")
    current = entity

    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list) and part.isdigit():
            idx = int(part)
            current = current[idx] if idx < len(current) else None
        else:
            return None

        if current is None:
            return None

    return current


# ADR-168 Commit 2: _resolve_action_ref removed along with Execute primitive.
# Its only use was List(pattern="action:*") for Execute action discovery.
# No replacement — lifecycle actions are typed parameters on ManageAgent /
# ManageRecurrence / ManageDomains; substrate writes go through WriteFile.

"""
Reference Parsing and Resolution (ADR-072 Unified Content Layer)

Grammar: <type>:<identifier>[/<subpath>][?<query>]

Examples:
  deliverable:uuid-123          # Specific by ID
  deliverable:latest            # Most recent
  platform:slack                # By provider name
  platform:slack/credentials    # Sub-entity
  platform_content:*            # All platform content
  session:current               # Special reference

Entity types:
  - deliverable: Content deliverables
  - platform: Connected platforms (platform_connections)
  - platform_content: Unified content layer (ADR-072)
  - memory: Knowledge entries (user facts, preferences)
  - session: Chat sessions
  - domain: Knowledge domains
  - document: Uploaded documents (filesystem_documents)
  - work: Work execution records
  - action: Executable actions (for discovery)

NOTE: Per ADR-059, 'memory' maps to user_context (replaces knowledge_entries).
      Platform content (Slack/Gmail/Notion imports) lives in platform_content (ADR-072).

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


# Valid entity types
ENTITY_TYPES = {
    "deliverable",
    "platform",
    "platform_content",  # ADR-072: unified content layer
    "memory",  # ADR-059: user_context
    "session",
    "domain",
    "document",
    "work",
    "action",  # For action discovery
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
        ref: Reference string like "deliverable:uuid-123" or "memory:?type=fact"

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


# Table mappings for entity types
TABLE_MAP = {
    "deliverable": "deliverables",
    "platform": "platform_connections",
    "platform_content": "platform_content",  # ADR-072: unified content layer
    "memory": "user_context",  # ADR-059: Replaces knowledge_entries
    "session": "chat_sessions",
    "domain": "user_context",  # ADR-059: knowledge_domains removed
    "document": "filesystem_documents",  # ADR-058
    "work": "work_tickets",
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

    # Handle action type specially (no table)
    if ref.entity_type == "action":
        return await _resolve_action_ref(ref)

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
        if "type" in ref.query and ref.entity_type == "memory":
            # Filter memories by type/tag
            query = query.contains("tags", [ref.query["type"]])
        if "status" in ref.query and ref.entity_type == "deliverable":
            query = query.eq("status", ref.query["status"])

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

        # Special handling for documents: include content from chunks
        if ref.entity_type == "document":
            entity = await _enrich_document_with_content(client, entity)

        # Special handling for platforms: include sync status from sync_registry
        if ref.entity_type == "platform":
            entity = await _enrich_platform_with_sync_status(client, auth.user_id, entity)

        return entity


async def _enrich_document_with_content(client: Any, doc: dict) -> dict:
    """
    Enrich a document with its actual content from filesystem_chunks.

    Documents are stored as metadata in filesystem_documents, with content
    chunked into filesystem_chunks for efficient retrieval.
    """
    doc_id = doc.get("id")
    if not doc_id:
        return doc

    try:
        # Fetch all chunks for this document, ordered by chunk_index
        chunks_result = client.table("filesystem_chunks").select(
            "content, chunk_index, page_number"
        ).eq(
            "document_id", doc_id
        ).order(
            "chunk_index"
        ).execute()

        if chunks_result.data:
            # Combine all chunks into full content
            full_content = "\n\n".join(
                chunk.get("content", "") for chunk in chunks_result.data
            )
            doc["content"] = full_content
            doc["chunk_count"] = len(chunks_result.data)

            # Also include page-indexed content for reference
            pages = {}
            for chunk in chunks_result.data:
                page_num = chunk.get("page_number")
                if page_num is not None:
                    if page_num not in pages:
                        pages[page_num] = []
                    pages[page_num].append(chunk.get("content", ""))
            if pages:
                doc["pages"] = {
                    page: "\n".join(contents)
                    for page, contents in sorted(pages.items())
                }
        else:
            doc["content"] = ""
            doc["chunk_count"] = 0

    except Exception as e:
        # Log but don't fail - return document without content
        import logging
        logging.warning(f"[REFS] Failed to fetch document content: {e}")
        doc["content"] = f"[Error loading content: {e}]"

    return doc


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


async def _resolve_action_ref(ref: EntityRef) -> Union[Dict, List[Dict]]:
    """Resolve action references for discovery."""
    from .execute import ACTION_CATALOG

    if ref.identifier == "*":
        # Return all actions
        return [
            {"name": name, **action}
            for name, action in ACTION_CATALOG.items()
        ]
    else:
        # Return specific action or filtered
        if ref.identifier in ACTION_CATALOG:
            return {"name": ref.identifier, **ACTION_CATALOG[ref.identifier]}

        # Try prefix match (e.g., "platform.*")
        prefix = ref.identifier.rstrip("*")
        if prefix:
            return [
                {"name": name, **action}
                for name, action in ACTION_CATALOG.items()
                if name.startswith(prefix)
            ]

        return []

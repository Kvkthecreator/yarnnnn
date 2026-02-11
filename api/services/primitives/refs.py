"""
Reference Parsing and Resolution (ADR-038 Phase 2)

Grammar: <type>:<identifier>[/<subpath>][?<query>]

Examples:
  deliverable:uuid-123          # Specific by ID
  deliverable:latest            # Most recent
  platform:slack                # By provider name
  platform:slack/credentials    # Sub-entity
  platform_content:*            # All platform content (ephemeral_context)
  session:current               # Special reference

Entity types:
  - deliverable: Content deliverables
  - platform: Connected platforms (user_integrations)
  - platform_content: Imported platform data (ephemeral_context) - ADR-038
  - memory: User-stated facts only (source_type='chat', 'user_stated')
  - session: Chat sessions
  - domain: Context domains
  - document: Uploaded documents
  - work: Work execution records
  - action: Executable actions (for discovery)

NOTE: Per ADR-038, 'memory' is narrowed to user-stated facts only.
      Platform content (Slack/Gmail/Notion imports) lives in ephemeral_context.

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
    "platform_content",  # ADR-038: ephemeral_context
    "memory",  # Narrowed to user-stated facts only
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
    "platform": "user_integrations",
    "platform_content": "ephemeral_context",  # ADR-038
    "memory": "memories",  # Narrowed to user-stated facts
    "session": "chat_sessions",
    "domain": "context_domains",
    "document": "documents",
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
            # Platforms use provider name
            query = query.eq("provider", ref.identifier)
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

        return entity


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

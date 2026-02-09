"""
Domain Inference Service - ADR-034: Emergent Context Domains

Computes context domains from deliverable source patterns.
Domains emerge from source overlap, not upfront user definition.

Key concepts:
- Sources that appear together in deliverables are connected
- Connected components of sources form domains
- Domains are auto-named based on source patterns
- Users can rename domains but don't have to manage them
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID

from services.supabase import get_service_client

logger = logging.getLogger(__name__)


# =============================================================================
# Data Types
# =============================================================================

@dataclass
class Source:
    """A platform resource that can be a context source."""
    provider: str  # slack, gmail, notion
    resource_id: str  # channel_id, inbox, page_id, etc.
    resource_name: Optional[str] = None

    def __hash__(self):
        return hash((self.provider, self.resource_id))

    def __eq__(self, other):
        if not isinstance(other, Source):
            return False
        return self.provider == other.provider and self.resource_id == other.resource_id


@dataclass
class ComputedDomain:
    """A domain computed from source overlap."""
    sources: set[Source]
    deliverable_ids: set[str]
    suggested_name: str
    existing_domain_id: Optional[str] = None  # If matches existing domain


@dataclass
class DomainReconciliation:
    """Result of reconciling computed domains with existing."""
    domains_to_create: list[ComputedDomain] = field(default_factory=list)
    domains_to_update: list[tuple[str, ComputedDomain]] = field(default_factory=list)
    domains_to_merge: list[tuple[list[str], ComputedDomain]] = field(default_factory=list)
    orphan_domain_ids: list[str] = field(default_factory=list)


# =============================================================================
# Source Extraction
# =============================================================================

def extract_sources_from_deliverable(deliverable: dict) -> list[Source]:
    """
    Extract Source objects from a deliverable's sources array.

    Deliverable sources format (from DataSource model):
    {
        "type": "integration_import",
        "provider": "slack",
        "source": "C123456",  # channel_id
        "label": "#engineering"
    }
    """
    sources = []

    for source_config in deliverable.get("sources", []):
        # Only integration sources contribute to domain inference
        if source_config.get("type") != "integration_import":
            continue

        provider = source_config.get("provider")
        resource_id = source_config.get("source")

        if not provider or not resource_id:
            continue

        sources.append(Source(
            provider=provider,
            resource_id=resource_id,
            resource_name=source_config.get("label")
        ))

    return sources


# =============================================================================
# Domain Inference Algorithm
# =============================================================================

def compute_domains_from_deliverables(deliverables: list[dict]) -> list[ComputedDomain]:
    """
    Compute context domains from deliverable source overlap.

    Algorithm:
    1. Extract sources from all deliverables
    2. Build adjacency graph (sources connected if they appear in same deliverable)
    3. Find connected components
    4. Each component = one domain
    """
    # Map: source -> set of deliverable IDs that use it
    source_to_deliverables: dict[Source, set[str]] = defaultdict(set)

    # Map: source -> other sources it appears with
    source_connections: dict[Source, set[Source]] = defaultdict(set)

    # Build mappings
    for deliverable in deliverables:
        deliverable_id = deliverable.get("id")
        sources = extract_sources_from_deliverable(deliverable)

        if not sources:
            continue  # Deliverable has no integration sources

        for source in sources:
            source_to_deliverables[source].add(deliverable_id)

            # Connect to all other sources in this deliverable
            for other_source in sources:
                if other_source != source:
                    source_connections[source].add(other_source)

    if not source_to_deliverables:
        return []  # No sources found

    # Find connected components using BFS
    visited: set[Source] = set()
    domains: list[ComputedDomain] = []

    for start_source in source_to_deliverables.keys():
        if start_source in visited:
            continue

        # BFS to find all connected sources
        component_sources: set[Source] = set()
        queue = [start_source]

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue

            visited.add(current)
            component_sources.add(current)

            # Add connected sources to queue
            for connected in source_connections.get(current, set()):
                if connected not in visited:
                    queue.append(connected)

        # Collect deliverables for this component
        component_deliverable_ids: set[str] = set()
        for source in component_sources:
            component_deliverable_ids.update(source_to_deliverables[source])

        # Generate suggested name
        suggested_name = generate_domain_name(component_sources)

        domains.append(ComputedDomain(
            sources=component_sources,
            deliverable_ids=component_deliverable_ids,
            suggested_name=suggested_name
        ))

    return domains


def generate_domain_name(sources: set[Source]) -> str:
    """
    Generate a human-readable name for a domain based on its sources.

    Heuristics:
    1. Extract common prefixes/patterns from source names
    2. Look for client/project indicators (#client-acme, acme@)
    3. Fall back to platform + count
    """
    # Collect all names and identifiers
    names = []
    for source in sources:
        if source.resource_name:
            names.append(source.resource_name)
        else:
            names.append(source.resource_id)

    if not names:
        return "Unnamed Domain"

    # Try to find common patterns
    # Pattern 1: #client-X, acme@ -> "Acme"
    client_patterns = []
    for name in names:
        # Match #client-acme, #acme-project, acme@, @acme.com
        match = re.search(r'#?client[_-]?(\w+)|#?(\w+)[_-](?:project|work)|(\w+)@|@(\w+)\.', name.lower())
        if match:
            # Get first non-None group
            for group in match.groups():
                if group:
                    client_patterns.append(group.capitalize())
                    break

    if client_patterns:
        # Use most common pattern
        from collections import Counter
        most_common = Counter(client_patterns).most_common(1)[0][0]
        return f"{most_common} Work"

    # Pattern 2: Common prefix in channel names
    if len(names) >= 2:
        # Find common prefix
        prefix = common_prefix([n.lower().lstrip('#') for n in names if n])
        if len(prefix) >= 3:
            return prefix.replace('-', ' ').replace('_', ' ').title().strip()

    # Pattern 3: Dominant platform
    platform_counts = defaultdict(int)
    for source in sources:
        platform_counts[source.provider] += 1

    dominant_platform = max(platform_counts.items(), key=lambda x: x[1])[0]
    platform_names = {
        "slack": "Slack",
        "gmail": "Email",
        "notion": "Notion",
        "calendar": "Calendar"
    }

    # Use first source name as hint
    first_name = names[0] if names else "Context"
    clean_name = first_name.lstrip('#').replace('-', ' ').replace('_', ' ').title()

    return f"{clean_name[:20]} ({platform_names.get(dominant_platform, dominant_platform.title())})"


def common_prefix(strings: list[str]) -> str:
    """Find common prefix among strings."""
    if not strings:
        return ""

    prefix = strings[0]
    for s in strings[1:]:
        while not s.startswith(prefix):
            prefix = prefix[:-1]
            if not prefix:
                return ""

    return prefix


# =============================================================================
# Domain Reconciliation
# =============================================================================

async def reconcile_domains(
    user_id: str,
    computed_domains: list[ComputedDomain]
) -> DomainReconciliation:
    """
    Reconcile computed domains with existing domains in database.

    Handles:
    - Creating new domains
    - Updating existing domains (source changes)
    - Merging domains (when previously separate sources become connected)
    - Identifying orphan domains (no longer have deliverables)
    """
    client = get_service_client()

    # Get existing domains and their sources
    existing_domains = client.table("context_domains").select(
        "id, name, name_source, is_default"
    ).eq("user_id", user_id).execute()

    existing_domain_sources = client.table("domain_sources").select(
        "domain_id, provider, resource_id"
    ).execute()

    # Build source -> domain_id mapping
    source_to_existing_domain: dict[tuple[str, str], str] = {}
    domain_id_to_sources: dict[str, set[tuple[str, str]]] = defaultdict(set)

    for ds in existing_domain_sources.data:
        key = (ds["provider"], ds["resource_id"])
        source_to_existing_domain[key] = ds["domain_id"]
        domain_id_to_sources[ds["domain_id"]].add(key)

    result = DomainReconciliation()
    matched_existing_domain_ids: set[str] = set()

    for computed in computed_domains:
        # Find which existing domains this computed domain overlaps with
        overlapping_domain_ids: set[str] = set()

        for source in computed.sources:
            key = (source.provider, source.resource_id)
            if key in source_to_existing_domain:
                overlapping_domain_ids.add(source_to_existing_domain[key])

        if len(overlapping_domain_ids) == 0:
            # New domain - no overlap with existing
            result.domains_to_create.append(computed)

        elif len(overlapping_domain_ids) == 1:
            # Update existing domain
            existing_id = list(overlapping_domain_ids)[0]
            matched_existing_domain_ids.add(existing_id)
            computed.existing_domain_id = existing_id
            result.domains_to_update.append((existing_id, computed))

        else:
            # Multiple existing domains need to merge
            matched_existing_domain_ids.update(overlapping_domain_ids)
            result.domains_to_merge.append((list(overlapping_domain_ids), computed))

    # Find orphan domains (exist but no computed domain matches)
    for domain in existing_domains.data:
        if domain["id"] not in matched_existing_domain_ids and not domain["is_default"]:
            result.orphan_domain_ids.append(domain["id"])

    return result


# =============================================================================
# Domain Operations
# =============================================================================

async def apply_domain_changes(
    user_id: str,
    reconciliation: DomainReconciliation
) -> dict:
    """
    Apply computed domain changes to the database.

    Returns summary of changes made.
    """
    client = get_service_client()

    created_count = 0
    updated_count = 0
    merged_count = 0
    orphaned_count = 0

    # Create new domains
    for computed in reconciliation.domains_to_create:
        # Create domain
        domain_result = client.table("context_domains").insert({
            "user_id": user_id,
            "name": computed.suggested_name,
            "name_source": "auto",
            "is_default": False
        }).execute()

        domain_id = domain_result.data[0]["id"]

        # Add sources
        source_records = [
            {
                "domain_id": domain_id,
                "provider": s.provider,
                "resource_id": s.resource_id,
                "resource_name": s.resource_name,
                "mapping_source": "inferred"
            }
            for s in computed.sources
        ]
        if source_records:
            client.table("domain_sources").insert(source_records).execute()

        # Link deliverables
        deliverable_links = [
            {"deliverable_id": d_id, "domain_id": domain_id}
            for d_id in computed.deliverable_ids
        ]
        if deliverable_links:
            client.table("deliverable_domains").upsert(
                deliverable_links,
                on_conflict="deliverable_id"
            ).execute()

        created_count += 1
        logger.info(f"Created domain '{computed.suggested_name}' with {len(computed.sources)} sources")

    # Update existing domains
    for domain_id, computed in reconciliation.domains_to_update:
        # Get current sources
        current_sources = client.table("domain_sources").select(
            "id, provider, resource_id"
        ).eq("domain_id", domain_id).execute()

        current_source_keys = {
            (s["provider"], s["resource_id"]) for s in current_sources.data
        }
        computed_source_keys = {
            (s.provider, s.resource_id) for s in computed.sources
        }

        # Add new sources
        sources_to_add = computed_source_keys - current_source_keys
        if sources_to_add:
            source_records = [
                {
                    "domain_id": domain_id,
                    "provider": s.provider,
                    "resource_id": s.resource_id,
                    "resource_name": s.resource_name,
                    "mapping_source": "inferred"
                }
                for s in computed.sources
                if (s.provider, s.resource_id) in sources_to_add
            ]
            client.table("domain_sources").insert(source_records).execute()

        # Remove old sources (only if inferred, not manual)
        sources_to_remove = current_source_keys - computed_source_keys
        if sources_to_remove:
            for s in current_sources.data:
                if (s["provider"], s["resource_id"]) in sources_to_remove:
                    # Check if it was manually added
                    source_detail = client.table("domain_sources").select(
                        "mapping_source"
                    ).eq("id", s["id"]).single().execute()

                    if source_detail.data.get("mapping_source") != "manual":
                        client.table("domain_sources").delete().eq("id", s["id"]).execute()

        # Update deliverable links
        deliverable_links = [
            {"deliverable_id": d_id, "domain_id": domain_id}
            for d_id in computed.deliverable_ids
        ]
        if deliverable_links:
            client.table("deliverable_domains").upsert(
                deliverable_links,
                on_conflict="deliverable_id"
            ).execute()

        updated_count += 1

    # Merge domains
    for domain_ids_to_merge, computed in reconciliation.domains_to_merge:
        # Pick the domain to keep (prefer user-named)
        domains_info = client.table("context_domains").select(
            "id, name, name_source"
        ).in_("id", domain_ids_to_merge).execute()

        # Prefer user-named domain, otherwise first one
        keep_domain_id = domain_ids_to_merge[0]
        for d in domains_info.data:
            if d["name_source"] == "user":
                keep_domain_id = d["id"]
                break

        # Move all sources to kept domain
        for domain_id in domain_ids_to_merge:
            if domain_id != keep_domain_id:
                # Update sources to point to kept domain
                client.table("domain_sources").update({
                    "domain_id": keep_domain_id
                }).eq("domain_id", domain_id).execute()

                # Update deliverable links
                client.table("deliverable_domains").update({
                    "domain_id": keep_domain_id
                }).eq("domain_id", domain_id).execute()

                # Update memories
                client.table("memories").update({
                    "domain_id": keep_domain_id
                }).eq("domain_id", domain_id).execute()

                # Delete merged domain
                client.table("context_domains").delete().eq("id", domain_id).execute()

        # Add any new sources from computed
        current_sources = client.table("domain_sources").select(
            "provider, resource_id"
        ).eq("domain_id", keep_domain_id).execute()

        current_source_keys = {
            (s["provider"], s["resource_id"]) for s in current_sources.data
        }

        sources_to_add = [
            {
                "domain_id": keep_domain_id,
                "provider": s.provider,
                "resource_id": s.resource_id,
                "resource_name": s.resource_name,
                "mapping_source": "inferred"
            }
            for s in computed.sources
            if (s.provider, s.resource_id) not in current_source_keys
        ]

        if sources_to_add:
            client.table("domain_sources").insert(sources_to_add).execute()

        merged_count += len(domain_ids_to_merge) - 1
        logger.info(f"Merged {len(domain_ids_to_merge)} domains into one")

    # Handle orphan domains (mark for potential cleanup)
    # Don't delete - they may have accumulated context we want to keep
    # Just log for now
    if reconciliation.orphan_domain_ids:
        orphaned_count = len(reconciliation.orphan_domain_ids)
        logger.info(f"Found {orphaned_count} orphan domains (no active deliverables)")

    return {
        "created": created_count,
        "updated": updated_count,
        "merged": merged_count,
        "orphaned": orphaned_count
    }


# =============================================================================
# Public API
# =============================================================================

async def recompute_user_domains(user_id: str) -> dict:
    """
    Recompute all domains for a user based on their deliverable sources.

    Call this when:
    - A deliverable is created, updated, or deleted
    - Sources are added/removed from a deliverable
    """
    client = get_service_client()

    # Get all user's deliverables with sources
    deliverables = client.table("deliverables").select(
        "id, sources, status"
    ).eq("user_id", user_id).neq("status", "archived").execute()

    # Compute domains from deliverable patterns
    computed_domains = compute_domains_from_deliverables(deliverables.data)

    if not computed_domains:
        logger.info(f"No domains computed for user {user_id} (no deliverables with sources)")
        return {"created": 0, "updated": 0, "merged": 0, "orphaned": 0}

    # Reconcile with existing domains
    reconciliation = await reconcile_domains(user_id, computed_domains)

    # Apply changes
    result = await apply_domain_changes(user_id, reconciliation)

    logger.info(f"Domain recomputation for user {user_id}: {result}")
    return result


async def get_domain_for_source(
    user_id: str,
    provider: str,
    resource_id: str
) -> Optional[str]:
    """
    Get the domain ID for a given source.
    Returns None if source is not in any domain.
    """
    client = get_service_client()

    result = client.rpc("find_domain_for_source", {
        "p_user_id": user_id,
        "p_provider": provider,
        "p_resource_id": resource_id
    }).execute()

    return result.data


async def get_or_create_default_domain(user_id: str) -> str:
    """
    Get or create the default (uncategorized) domain for a user.
    """
    client = get_service_client()

    result = client.rpc("get_or_create_default_domain", {
        "p_user_id": user_id
    }).execute()

    return result.data


async def on_deliverable_changed(deliverable_id: str, user_id: str):
    """
    Hook to call when a deliverable's sources change.
    Triggers domain recomputation.
    """
    logger.info(f"Deliverable {deliverable_id} changed, recomputing domains for user {user_id}")
    await recompute_user_domains(user_id)


async def get_active_domain_for_context(
    user_id: str,
    active_deliverable_id: Optional[str] = None,
    mentioned_sources: Optional[list[Source]] = None
) -> Optional[str]:
    """
    Determine which domain should scope the current context.

    Priority:
    1. If viewing a deliverable, use that deliverable's domain
    2. If sources are mentioned, use domain containing those sources
    3. If only one domain exists, use it
    4. Return None (ambiguous - caller should ask user)
    """
    client = get_service_client()

    # Priority 1: Active deliverable
    if active_deliverable_id:
        result = client.rpc("get_deliverable_domain", {
            "p_deliverable_id": active_deliverable_id
        }).execute()
        if result.data:
            return result.data

    # Priority 2: Mentioned sources
    if mentioned_sources:
        for source in mentioned_sources:
            domain_id = await get_domain_for_source(
                user_id, source.provider, source.resource_id
            )
            if domain_id:
                return domain_id

    # Priority 3: Only one domain
    domains = client.table("context_domains").select("id").eq(
        "user_id", user_id
    ).eq("is_default", False).execute()

    if len(domains.data) == 1:
        return domains.data[0]["id"]

    # Ambiguous
    return None

"""
Cross-Platform Synthesizer Service - ADR-031 Phase 6

Assembles context from multiple platforms and coordinates multi-destination
delivery for synthesizer deliverables.

Key features:
1. Project-to-resource mapping: Discovers and links platform resources to projects
2. Multi-source context assembly: Pulls ephemeral context from multiple platforms
3. Cross-platform deduplication: Avoids repeating info shared across platforms
4. Multi-destination delivery: Outputs to multiple platforms in one generation

Example synthesizer flow:
1. User creates "Weekly Status" synthesizer for Project "Q1 Launch"
2. Project has linked resources:
   - Slack: #q1-launch, #engineering
   - Gmail: label:q1-launch
   - Notion: Q1 Launch workspace page
3. Synthesizer pulls context from all sources
4. Generates unified status report
5. Delivers to both Slack (#leadership) and email (stakeholders@company.com)
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# Types and Data Classes
# =============================================================================

class SynthesizerType(str, Enum):
    """Types of cross-platform synthesizers."""
    WEEKLY_STATUS = "weekly_status"
    PROJECT_BRIEF = "project_brief"
    CROSS_PLATFORM_DIGEST = "cross_platform_digest"
    ACTIVITY_SUMMARY = "activity_summary"


@dataclass
class PlatformResource:
    """A platform resource linked to a project."""
    id: str
    platform: str  # slack, gmail, notion, calendar
    resource_type: str  # channel, label, page, database
    resource_id: str
    resource_name: Optional[str] = None
    is_primary: bool = False
    include_filters: dict = field(default_factory=dict)
    exclude_filters: dict = field(default_factory=dict)
    last_synced_at: Optional[datetime] = None


@dataclass
class ContextItem:
    """A single item of context from any platform."""
    platform: str
    resource_id: str
    resource_name: Optional[str]
    content: str
    content_type: str  # message, thread_summary, page_update, email, etc.
    source_timestamp: datetime
    platform_metadata: dict = field(default_factory=dict)
    # For deduplication
    content_hash: Optional[str] = None


@dataclass
class AssembledContext:
    """Result of multi-source context assembly."""
    items: list[ContextItem]
    sources_summary: list[dict]  # [{platform, resource_id, items_count, time_range}]
    total_items_pulled: int
    total_after_dedup: int
    platforms_used: list[str]
    time_range_start: Optional[datetime] = None
    time_range_end: Optional[datetime] = None
    overlap_score: float = 0.0  # How much content overlapped
    freshness_score: float = 0.0  # How recent the context is


@dataclass
class DestinationResult:
    """Result of delivering to a single destination."""
    destination_index: int
    platform: str
    target: str
    status: str  # pending, delivered, failed
    external_id: Optional[str] = None
    external_url: Optional[str] = None
    error: Optional[str] = None


@dataclass
class SynthesizerResult:
    """Result of a synthesizer execution."""
    version_id: str
    content: str
    context: AssembledContext
    destinations: list[DestinationResult]
    all_delivered: bool


# =============================================================================
# Project Resource Management
# =============================================================================

async def get_project_resources(
    db_client,
    project_id: str,
    platform: Optional[str] = None,
) -> list[PlatformResource]:
    """
    Get platform resources linked to a project.

    Args:
        db_client: Supabase client
        project_id: Project UUID
        platform: Optional platform filter

    Returns:
        List of PlatformResource objects
    """
    query = (
        db_client.table("project_resources")
        .select("*")
        .eq("project_id", project_id)
    )

    if platform:
        query = query.eq("platform", platform)

    result = query.order("is_primary", desc=True).execute()

    resources = []
    for row in result.data or []:
        resources.append(PlatformResource(
            id=row["id"],
            platform=row["platform"],
            resource_type=row["resource_type"],
            resource_id=row["resource_id"],
            resource_name=row.get("resource_name"),
            is_primary=row.get("is_primary", False),
            include_filters=row.get("include_filters") or {},
            exclude_filters=row.get("exclude_filters") or {},
            last_synced_at=_parse_datetime(row.get("last_synced_at")),
        ))

    return resources


async def add_project_resource(
    db_client,
    user_id: str,
    project_id: str,
    platform: str,
    resource_type: str,
    resource_id: str,
    resource_name: Optional[str] = None,
    is_primary: bool = False,
    include_filters: Optional[dict] = None,
    auto_discovered: bool = False,
) -> PlatformResource:
    """
    Add a platform resource to a project.

    Args:
        db_client: Supabase client
        user_id: User UUID
        project_id: Project UUID
        platform: Platform name (slack, gmail, notion)
        resource_type: Type of resource (channel, label, page)
        resource_id: Platform-specific resource ID
        resource_name: Human-readable name
        is_primary: Whether this is the primary resource for this platform
        include_filters: Optional filters to apply when pulling context
        auto_discovered: Whether YARNNN auto-suggested this resource

    Returns:
        Created PlatformResource
    """
    # If setting as primary, unset other primaries for this platform
    if is_primary:
        db_client.table("project_resources").update({
            "is_primary": False,
        }).eq("project_id", project_id).eq("platform", platform).execute()

    result = db_client.table("project_resources").insert({
        "user_id": user_id,
        "project_id": project_id,
        "platform": platform,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "resource_name": resource_name,
        "is_primary": is_primary,
        "include_filters": include_filters or {},
        "auto_discovered": auto_discovered,
    }).execute()

    row = result.data[0]
    return PlatformResource(
        id=row["id"],
        platform=row["platform"],
        resource_type=row["resource_type"],
        resource_id=row["resource_id"],
        resource_name=row.get("resource_name"),
        is_primary=row.get("is_primary", False),
        include_filters=row.get("include_filters") or {},
    )


async def suggest_project_resources(
    db_client,
    user_id: str,
    project_name: str,
) -> list[dict]:
    """
    Auto-suggest platform resources that might be related to a project.

    Uses heuristics like:
    - Slack channels with similar names
    - Gmail labels matching project name
    - Notion pages with project name in title

    Args:
        db_client: Supabase client
        user_id: User UUID
        project_name: Project name to search for

    Returns:
        List of suggested resources with confidence scores
    """
    suggestions = []
    name_lower = project_name.lower()
    name_tokens = set(name_lower.split())

    # Get user's ephemeral context to find resources they've used
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=30)

    result = (
        db_client.table("ephemeral_context")
        .select("platform, resource_id, resource_name")
        .eq("user_id", user_id)
        .gt("created_at", since.isoformat())
        .gt("expires_at", now.isoformat())
        .execute()
    )

    # Aggregate unique resources
    seen = set()
    resources = []
    for row in result.data or []:
        key = (row["platform"], row["resource_id"])
        if key not in seen:
            seen.add(key)
            resources.append(row)

    # Score each resource
    for r in resources:
        resource_name = (r.get("resource_name") or "").lower()
        resource_id = (r.get("resource_id") or "").lower()

        # Calculate similarity score
        score = 0.0

        # Exact match in name
        if name_lower in resource_name:
            score = 0.9
        elif name_lower in resource_id:
            score = 0.8
        else:
            # Token overlap
            resource_tokens = set(resource_name.split())
            resource_tokens.update(resource_id.replace("-", " ").replace("_", " ").split())
            overlap = name_tokens & resource_tokens
            if overlap:
                score = 0.3 + (0.3 * len(overlap) / len(name_tokens))

        if score >= 0.3:
            suggestions.append({
                "platform": r["platform"],
                "resource_id": r["resource_id"],
                "resource_name": r.get("resource_name"),
                "confidence": round(score, 2),
                "reason": _get_match_reason(name_lower, resource_name, resource_id),
            })

    # Sort by confidence
    suggestions.sort(key=lambda x: -x["confidence"])
    return suggestions[:10]


def _get_match_reason(project_name: str, resource_name: str, resource_id: str) -> str:
    """Generate human-readable reason for suggestion."""
    if project_name in resource_name:
        return f"Channel name contains '{project_name}'"
    if project_name in resource_id:
        return f"Resource ID contains '{project_name}'"
    return "Similar keywords"


# =============================================================================
# Multi-Source Context Assembly
# =============================================================================

async def assemble_cross_platform_context(
    db_client,
    user_id: str,
    project_id: str,
    time_range_days: int = 7,
    max_items_per_platform: int = 100,
) -> AssembledContext:
    """
    Assemble context from all platforms linked to a project.

    Pulls ephemeral context from each linked resource, deduplicates
    cross-platform mentions, and prepares unified context for synthesis.

    Args:
        db_client: Supabase client
        user_id: User UUID
        project_id: Project UUID
        time_range_days: How far back to pull context
        max_items_per_platform: Max items per platform (to prevent context overload)

    Returns:
        AssembledContext with all items and metadata
    """
    import hashlib

    # Get project resources
    resources = await get_project_resources(db_client, project_id)

    if not resources:
        logger.warning(f"[SYNTHESIZER] No resources linked to project {project_id}")
        return AssembledContext(
            items=[],
            sources_summary=[],
            total_items_pulled=0,
            total_after_dedup=0,
            platforms_used=[],
        )

    now = datetime.now(timezone.utc)
    since = now - timedelta(days=time_range_days)

    all_items: list[ContextItem] = []
    sources_summary = []
    platforms_used = set()
    content_hashes = set()  # For deduplication

    for resource in resources:
        # Query ephemeral context for this resource
        result = (
            db_client.table("ephemeral_context")
            .select("*")
            .eq("user_id", user_id)
            .eq("platform", resource.platform)
            .eq("resource_id", resource.resource_id)
            .gt("created_at", since.isoformat())
            .gt("expires_at", now.isoformat())
            .order("source_timestamp", desc=True)
            .limit(max_items_per_platform)
            .execute()
        )

        items_for_resource = []
        for row in result.data or []:
            # Create content hash for deduplication
            content_text = row.get("content", "")
            content_hash = hashlib.md5(content_text.encode()).hexdigest()

            item = ContextItem(
                platform=resource.platform,
                resource_id=resource.resource_id,
                resource_name=resource.resource_name or row.get("resource_name"),
                content=content_text,
                content_type=row.get("content_type", "message"),
                source_timestamp=_parse_datetime(row.get("source_timestamp")) or now,
                platform_metadata=row.get("platform_metadata") or {},
                content_hash=content_hash,
            )
            items_for_resource.append(item)

        if items_for_resource:
            platforms_used.add(resource.platform)

            # Calculate time range for this source
            timestamps = [i.source_timestamp for i in items_for_resource if i.source_timestamp]
            time_range = {}
            if timestamps:
                time_range = {
                    "start": min(timestamps).isoformat(),
                    "end": max(timestamps).isoformat(),
                }

            sources_summary.append({
                "platform": resource.platform,
                "resource_id": resource.resource_id,
                "resource_name": resource.resource_name,
                "items_count": len(items_for_resource),
                "time_range": time_range,
            })

            all_items.extend(items_for_resource)

        # Update last_synced_at
        db_client.table("project_resources").update({
            "last_synced_at": now.isoformat(),
        }).eq("id", resource.id).execute()

    # Deduplicate items with similar content across platforms
    total_before_dedup = len(all_items)
    deduped_items = []
    seen_hashes = set()

    for item in all_items:
        if item.content_hash not in seen_hashes:
            seen_hashes.add(item.content_hash)
            deduped_items.append(item)

    # Calculate overlap score
    overlap_count = total_before_dedup - len(deduped_items)
    overlap_score = overlap_count / max(total_before_dedup, 1)

    # Calculate freshness score (average recency)
    if deduped_items:
        age_scores = []
        for item in deduped_items:
            if item.source_timestamp:
                age_hours = (now - item.source_timestamp).total_seconds() / 3600
                # 24 hours = 1.0, 168 hours (7 days) = 0.0
                freshness = max(0, 1 - (age_hours / 168))
                age_scores.append(freshness)
        freshness_score = sum(age_scores) / len(age_scores) if age_scores else 0.0
    else:
        freshness_score = 0.0

    # Sort by timestamp (most recent first)
    deduped_items.sort(key=lambda x: x.source_timestamp or now, reverse=True)

    # Calculate overall time range
    all_timestamps = [i.source_timestamp for i in deduped_items if i.source_timestamp]
    time_range_start = min(all_timestamps) if all_timestamps else None
    time_range_end = max(all_timestamps) if all_timestamps else None

    logger.info(
        f"[SYNTHESIZER] Assembled {len(deduped_items)} items from {len(platforms_used)} platforms "
        f"(deduped {overlap_count} overlapping items)"
    )

    return AssembledContext(
        items=deduped_items,
        sources_summary=sources_summary,
        total_items_pulled=total_before_dedup,
        total_after_dedup=len(deduped_items),
        platforms_used=list(platforms_used),
        time_range_start=time_range_start,
        time_range_end=time_range_end,
        overlap_score=round(overlap_score, 3),
        freshness_score=round(freshness_score, 3),
    )


def format_context_for_prompt(context: AssembledContext) -> str:
    """
    Format assembled context into a string for the generation prompt.

    Groups items by platform for clarity, with timestamps and metadata.

    Args:
        context: AssembledContext from assembly

    Returns:
        Formatted string ready for prompt inclusion
    """
    if not context.items:
        return "[No context available from linked resources]"

    lines = []
    lines.append(f"## Cross-Platform Context ({len(context.platforms_used)} platforms, {len(context.items)} items)")
    lines.append("")

    # Group by platform
    by_platform: dict[str, list[ContextItem]] = {}
    for item in context.items:
        if item.platform not in by_platform:
            by_platform[item.platform] = []
        by_platform[item.platform].append(item)

    for platform, items in by_platform.items():
        platform_icon = {
            "slack": "💬",
            "gmail": "📧",
            "notion": "📝",
            "calendar": "📅",
        }.get(platform, "📌")

        lines.append(f"### {platform_icon} {platform.title()} ({len(items)} items)")
        lines.append("")

        for item in items[:20]:  # Limit per platform in prompt
            timestamp = ""
            if item.source_timestamp:
                timestamp = item.source_timestamp.strftime("%m/%d %H:%M")

            resource = item.resource_name or item.resource_id
            content_preview = item.content[:500] if len(item.content) > 500 else item.content

            lines.append(f"**[{resource}]** {timestamp}")
            lines.append(content_preview)
            lines.append("")

        if len(items) > 20:
            lines.append(f"_...and {len(items) - 20} more items from {platform}_")
            lines.append("")

    return "\n".join(lines)


# =============================================================================
# Context Assembly Logging
# =============================================================================

async def log_context_assembly(
    db_client,
    version_id: str,
    deliverable_id: str,
    user_id: str,
    context: AssembledContext,
    duration_ms: int,
) -> None:
    """
    Log context assembly for analytics and debugging.

    Args:
        db_client: Supabase client
        version_id: Deliverable version UUID
        deliverable_id: Deliverable UUID
        user_id: User UUID
        context: Assembled context
        duration_ms: Time taken to assemble
    """
    try:
        db_client.table("synthesizer_context_log").insert({
            "version_id": version_id,
            "deliverable_id": deliverable_id,
            "user_id": user_id,
            "sources_assembled": context.sources_summary,
            "total_items_pulled": context.total_items_pulled,
            "total_items_after_dedup": context.total_after_dedup,
            "assembly_completed_at": datetime.now(timezone.utc).isoformat(),
            "assembly_duration_ms": duration_ms,
            "context_overlap_score": context.overlap_score,
            "freshness_score": context.freshness_score,
        }).execute()
    except Exception as e:
        logger.warning(f"[SYNTHESIZER] Failed to log context assembly: {e}")


# =============================================================================
# Helpers
# =============================================================================

def _parse_datetime(value) -> Optional[datetime]:
    """Parse datetime from string or return None."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None

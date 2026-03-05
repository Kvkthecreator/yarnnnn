"""
Deliverables routes - Recurring deliverable management

ADR-018: Recurring Deliverables Product Pivot
ADR-019: Deliverable Types System

Endpoints:
- POST /deliverables - Create a new deliverable
- GET /deliverables - List user's deliverables
- GET /deliverables/:id - Get deliverable with version history
- PATCH /deliverables/:id - Update deliverable settings
- DELETE /deliverables/:id - Archive a deliverable
- POST /deliverables/:id/run - Trigger an ad-hoc run
- GET /deliverables/:id/versions - List versions
- GET /deliverables/:id/versions/:version_id - Get version detail
- PATCH /deliverables/:id/versions/:version_id - Update version (approve, reject, save edits)
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Literal, Union
from uuid import UUID
from datetime import datetime, timezone

from services.supabase import UserClient

logger = logging.getLogger(__name__)


router = APIRouter()


# =============================================================================
# ADR-093: Deliverable Type Definitions (7 purpose-first types)
# =============================================================================

DeliverableType = Literal[
    "digest",        # Synthesis of what's happening in a specific place (platform inferred from sources)
    "brief",         # Situation-specific document before a key event
    "status",        # Regular cross-platform summary for a person or audience
    "watch",         # Standing-order intelligence on a domain
    "deep_research", # Bounded investigation into something specific, then done
    "coordinator",   # Meta-specialist that watches a domain and dispatches other work
    "custom",        # User-defined intent
]

# ADR-093: All 7 types are stable
TYPE_TIERS = {
    "digest": "stable",
    "brief": "stable",
    "status": "stable",
    "watch": "stable",
    "deep_research": "stable",
    "coordinator": "stable",
    "custom": "stable",
}


# =============================================================================
# ADR-044/045: Type Classification for Strategy Selection
# =============================================================================

def get_type_classification(deliverable_type: str) -> dict:
    """
    ADR-093: Get type_classification for a deliverable type.

    Determines which execution strategy is used:
    - platform_bound: Single platform context — inferred from sources[] for digest
    - cross_platform: Multi-platform synthesis (CrossPlatformStrategy)
    - research: Web research via headless agent WebSearch (ADR-081)
    - hybrid: Research + platform grounding (HybridStrategy)

    Returns:
        dict with binding, temporal_pattern, and optional primary_platform
    """
    if deliverable_type == "digest":
        # Platform inferred from sources[] at assembly time, not from type
        return {
            "binding": "platform_bound",
            "temporal_pattern": "scheduled",
            "freshness_requirement_hours": 1,
        }

    if deliverable_type == "brief":
        return {
            "binding": "cross_platform",
            "temporal_pattern": "reactive",
            "freshness_requirement_hours": 1,
        }

    if deliverable_type == "status":
        return {
            "binding": "cross_platform",
            "temporal_pattern": "scheduled",
            "freshness_requirement_hours": 4,
        }

    if deliverable_type == "watch":
        return {
            "binding": "cross_platform",
            "temporal_pattern": "on_demand",
            "freshness_requirement_hours": 4,
        }

    if deliverable_type == "deep_research":
        return {
            "binding": "research",
            "temporal_pattern": "on_demand",
            "freshness_requirement_hours": 24,
        }

    if deliverable_type == "coordinator":
        return {
            "binding": "cross_platform",
            "temporal_pattern": "on_demand",
            "freshness_requirement_hours": 4,
        }

    # custom and unknown types
    return {
        "binding": "hybrid",
        "temporal_pattern": "on_demand",
        "freshness_requirement_hours": 4,
    }


# =============================================================================
# ADR-093: Type Configs (7 purpose-first types)
# =============================================================================

class DigestConfig(BaseModel):
    """Configuration for digest type. Platform inferred from sources[] at assembly time."""
    focus: str = "key discussions and decisions"
    reply_threshold: int = 3    # Min replies to flag as hot thread (Slack)
    reaction_threshold: int = 2  # Min reactions to surface a message (Slack)
    max_items: int = 15


class BriefConfig(BaseModel):
    """Configuration for brief type (meeting prep, event prep, call prep)."""
    event_title: Optional[str] = None   # Meeting/event name if calendar-triggered
    attendees: list[str] = Field(default_factory=list)
    focus_areas: list[str] = Field(default_factory=list)  # Topics to prioritize
    depth: Literal["concise", "standard", "detailed"] = "standard"


class StatusConfig(BaseModel):
    """Configuration for status type (cross-platform status update)."""
    subject: str = ""  # "Engineering Team", "Project Alpha"
    audience: Literal["manager", "stakeholders", "team", "executive"] = "stakeholders"
    detail_level: Literal["brief", "standard", "detailed"] = "standard"
    tone: Literal["formal", "conversational"] = "formal"


class WatchConfig(BaseModel):
    """Configuration for watch type (standing-order intelligence monitoring)."""
    domain: str = ""  # "competitive landscape", "AI regulation", "customer feedback"
    signals: list[str] = Field(default_factory=list)  # What to look for
    threshold_notes: Optional[str] = None  # When to surface (guidance for proactive mode)


class DeepResearchConfig(BaseModel):
    """Configuration for deep_research type (bounded investigation)."""
    focus_area: Literal["competitive", "market", "technology", "industry", "general"] = "general"
    subjects: list[str] = Field(default_factory=list)
    purpose: Optional[str] = None
    depth: Literal["scan", "analysis", "deep_dive"] = "analysis"


class CoordinatorConfig(BaseModel):
    """Configuration for coordinator type (meta-specialist that dispatches work)."""
    domain: str = ""  # Domain this coordinator watches
    dispatch_rules: list[str] = Field(default_factory=list)  # What triggers dispatching


class CustomConfig(BaseModel):
    """Configuration for custom/freeform deliverable type."""
    description: str = ""
    structure_notes: Optional[str] = None
    example_content: Optional[str] = None


# ADR-093: Union type for type_config (7 types)
TypeConfig = Union[
    DigestConfig,
    BriefConfig,
    StatusConfig,
    WatchConfig,
    DeepResearchConfig,
    CoordinatorConfig,
    CustomConfig,
]


class FeedbackSummary(BaseModel):
    """Summary of learned preferences from user feedback (ADR-018)."""
    has_feedback: bool = False
    total_versions: int = 0
    approved_versions: int = 0
    avg_quality: Optional[float] = None  # Average (1 - edit_distance_score) as percentage
    learned_preferences: list[str] = Field(default_factory=list)  # Human-readable preferences


def compute_feedback_summary(approved_versions: list[dict]) -> FeedbackSummary:
    """
    Compute feedback summary from approved versions (ADR-018).

    Analyzes edit patterns and feedback notes to determine what YARNNN has learned.
    """
    if not approved_versions:
        return FeedbackSummary(
            has_feedback=False,
            total_versions=0,
            approved_versions=0,
        )

    # Calculate average quality (1 - edit_distance = quality)
    scores = [
        v.get("edit_distance_score")
        for v in approved_versions
        if v.get("edit_distance_score") is not None
    ]
    avg_quality = None
    if scores:
        avg_quality = round((1 - sum(scores) / len(scores)) * 100, 1)

    # Aggregate learned preferences from edit categories and feedback
    learned = []
    addition_counts: dict[str, int] = {}
    deletion_counts: dict[str, int] = {}

    for v in approved_versions:
        # Collect edit categories
        categories = v.get("edit_categories", {})
        if categories:
            for addition in categories.get("additions", []):
                addition_counts[addition] = addition_counts.get(addition, 0) + 1
            for deletion in categories.get("deletions", []):
                deletion_counts[deletion] = deletion_counts.get(deletion, 0) + 1

        # Collect explicit feedback
        if v.get("feedback_notes"):
            note = v["feedback_notes"].strip()
            if note and note not in learned:
                learned.append(f'"{note}"')

    # Convert category patterns to human-readable preferences
    if addition_counts:
        top_additions = sorted(addition_counts.items(), key=lambda x: -x[1])[:3]
        for item, count in top_additions:
            if count >= 2:
                learned.append(f"You often add {item}")
            else:
                learned.append(f"You've added {item}")

    if deletion_counts:
        top_deletions = sorted(deletion_counts.items(), key=lambda x: -x[1])[:3]
        for item, count in top_deletions:
            if count >= 2:
                learned.append(f"You often remove {item}")
            else:
                learned.append(f"You've removed {item}")

    return FeedbackSummary(
        has_feedback=len(learned) > 0 or avg_quality is not None,
        total_versions=len(approved_versions),
        approved_versions=len(approved_versions),
        avg_quality=avg_quality,
        learned_preferences=learned[:8],  # Limit to 8 items
    )


def get_default_config(deliverable_type: DeliverableType) -> dict:
    """Get default configuration for a deliverable type (ADR-093: 7 types)."""
    defaults = {
        "digest": DigestConfig(),
        "brief": BriefConfig(),
        "status": StatusConfig(),
        "watch": WatchConfig(),
        "deep_research": DeepResearchConfig(),
        "coordinator": CoordinatorConfig(),
        "custom": CustomConfig(),
    }
    return defaults.get(deliverable_type, defaults["custom"]).model_dump()


# =============================================================================
# Request/Response Models
# =============================================================================

class RecipientContext(BaseModel):
    """Who receives the deliverable and what they care about."""
    name: Optional[str] = None
    role: Optional[str] = None
    priorities: list[str] = Field(default_factory=list)
    notes: Optional[str] = None


class TemplateStructure(BaseModel):
    """Extracted or defined template for the deliverable (legacy, use type_config)."""
    sections: list[str] = Field(default_factory=list)
    typical_length: Optional[str] = None  # e.g., "500-800 words"
    tone: Optional[str] = None  # e.g., "professional", "casual"
    format_notes: Optional[str] = None


class ScheduleConfig(BaseModel):
    """Schedule configuration for recurring execution."""
    frequency: Literal["daily", "weekly", "biweekly", "monthly", "custom"]
    day: Optional[str] = None  # e.g., "monday", "1", "15"
    time: Optional[str] = None  # e.g., "09:00"
    timezone: str = "America/Los_Angeles"
    cron: Optional[str] = None  # For custom frequency


# =============================================================================
# ADR-031 Phase 4: Event Trigger Definitions
# =============================================================================

class CooldownConfig(BaseModel):
    """Cooldown configuration to prevent rapid re-triggering."""
    type: Literal["per_thread", "per_channel", "per_sender", "global"] = "global"
    duration_minutes: int = 5
    max_triggers_per_duration: int = 1


class EventTriggerConfig(BaseModel):
    """
    Event trigger configuration for deliverables.

    Used when trigger_type='event'.
    """
    platform: Literal["slack", "gmail", "notion"]
    event_types: list[str] = Field(default_factory=list)  # ["app_mention", "message_im"]
    resource_ids: list[str] = Field(default_factory=list)  # ["C123", "D456"]
    cooldown: Optional[CooldownConfig] = None
    # ADR-092: Reactive mode — number of observations before generating a version
    observation_threshold: int = 5
    # Optional filters
    sender_filter: Optional[list[str]] = None  # Only trigger for specific senders
    keyword_filter: Optional[list[str]] = None  # Only trigger if content contains keywords


class IntegrationSourceScope(BaseModel):
    """ADR-030: Scope configuration for integration sources."""
    mode: Literal["delta", "fixed_window"] = "delta"
    # Delta mode: fetch since last_run_at (or fallback_days if first run)
    fallback_days: int = 7  # If no last_run_at, go back this many days
    # Fixed window mode: always fetch last N days
    recency_days: Optional[int] = None
    # Safety limits
    max_items: int = 200
    # Provider-specific options
    include_threads: bool = True  # Slack
    include_sent: bool = True  # Gmail
    max_depth: int = 2  # Notion


class DataSource(BaseModel):
    """A source of information for the deliverable."""
    type: Literal["url", "document", "description", "integration_import"]
    value: str  # URL, document_id, or description text
    label: Optional[str] = None
    # ADR-030: Integration source fields
    provider: Optional[Literal["gmail", "slack", "notion"]] = None
    source: Optional[str] = None  # inbox, query:..., channel_id, page_id
    filters: Optional[dict] = None  # Provider-specific filters
    scope: Optional[IntegrationSourceScope] = None


class DeliverableCreate(BaseModel):
    """Create deliverable request - ADR-019 type-first approach."""
    title: str
    deliverable_type: DeliverableType = "custom"
    type_config: Optional[dict] = None  # Type-specific config, validated per type
    # ADR-031: Platform-native variants
    platform_variant: Optional[str] = None
    # ADR-044: Type classification (binding + temporal pattern)
    type_classification: Optional[dict] = None  # If provided, overrides auto-computed
    recipient_context: Optional[RecipientContext] = None
    # ADR-031 Phase 4: Trigger configuration
    trigger_type: Literal["schedule", "event", "manual"] = "schedule"
    schedule: Optional[ScheduleConfig] = None  # Required if trigger_type='schedule'
    trigger_config: Optional[EventTriggerConfig] = None  # Required if trigger_type='event'
    sources: list[DataSource] = Field(default_factory=list)
    # ADR-028: Destination-first deliverables
    destination: Optional[dict] = None  # { platform, target, format, options }
    # ADR-031 Phase 6: Multi-destination support for synthesizers
    destinations: Optional[list[dict]] = None  # Array of destination configs
    # ADR-031 Phase 6: Synthesizer flag
    is_synthesizer: bool = False  # If true, uses cross-platform context assembly
    # ADR-092: Mode taxonomy
    mode: Literal["recurring", "goal", "reactive", "proactive", "coordinator"] = "recurring"
    # ADR-087: Deliverable-scoped context
    deliverable_instructions: Optional[str] = None
    # Legacy fields (deprecated, use type_config)
    description: Optional[str] = None
    template_structure: Optional[TemplateStructure] = None


class DeliverableUpdate(BaseModel):
    """Update deliverable request."""
    title: Optional[str] = None
    deliverable_type: Optional[DeliverableType] = None
    type_config: Optional[dict] = None
    # ADR-031: Platform-native variants
    platform_variant: Optional[str] = None
    recipient_context: Optional[RecipientContext] = None
    # ADR-031 Phase 4: Trigger configuration
    trigger_type: Optional[Literal["schedule", "event", "manual"]] = None
    schedule: Optional[ScheduleConfig] = None
    trigger_config: Optional[EventTriggerConfig] = None
    sources: Optional[list[DataSource]] = None
    status: Optional[Literal["active", "paused", "archived"]] = None
    # ADR-028: Destination-first deliverables
    destination: Optional[dict] = None
    # ADR-031 Phase 6: Multi-destination support
    destinations: Optional[list[dict]] = None
    # ADR-031 Phase 6: Synthesizer flag
    is_synthesizer: Optional[bool] = None
    # ADR-087: Deliverable-scoped context
    deliverable_instructions: Optional[str] = None
    # ADR-092: Mode taxonomy extended
    mode: Optional[Literal["recurring", "goal", "reactive", "proactive", "coordinator"]] = None
    # ADR-092: Proactive/coordinator review scheduling
    proactive_next_review_at: Optional[str] = None
    # Legacy fields (deprecated)
    description: Optional[str] = None
    template_structure: Optional[TemplateStructure] = None


class DeliverableResponse(BaseModel):
    """Deliverable response - includes ADR-019 type fields."""
    id: str
    title: str
    deliverable_type: str = "custom"
    type_config: Optional[dict] = None
    # ADR-031: Platform-native variants
    platform_variant: Optional[str] = None
    # ADR-044: Type classification (binding + temporal pattern)
    type_classification: Optional[dict] = None
    project_id: Optional[str] = None
    project_name: Optional[str] = None  # For UI display
    recipient_context: Optional[dict] = None
    # ADR-031 Phase 4: Trigger configuration
    trigger_type: str = "schedule"  # schedule, event, manual
    schedule: Optional[dict] = None
    trigger_config: Optional[dict] = None  # Event trigger config
    sources: list[dict] = Field(default_factory=list)
    status: str
    created_at: str
    updated_at: str
    last_run_at: Optional[str] = None
    next_run_at: Optional[str] = None
    last_triggered_at: Optional[str] = None  # ADR-031: Last event trigger
    version_count: int = 0
    latest_version_status: Optional[str] = None
    # ADR-028: Destination-first deliverables
    destination: Optional[dict] = None  # { platform, target, format, options }
    # ADR-031 Phase 6: Multi-destination support
    destinations: list[dict] = Field(default_factory=list)  # Array of destination configs
    # ADR-031 Phase 6: Synthesizer fields
    is_synthesizer: bool = False  # Uses cross-platform context assembly
    linked_resources: Optional[list[dict]] = None  # Project resources for synthesizers
    # Quality metrics (ADR-018: feedback loop)
    quality_score: Optional[float] = None  # Latest edit_distance_score (0=no edits, 1=full rewrite)
    quality_trend: Optional[str] = None  # "improving", "stable", "declining"
    avg_edit_distance: Optional[float] = None  # Average over last 5 versions
    # ADR-030: Source freshness
    source_freshness: Optional[list[dict]] = None  # [{source_index, provider, last_fetched_at, is_stale}]
    # ADR-068: Deliverable origin (how it came to exist)
    # ADR-092: coordinator_created added
    origin: str = "user_configured"  # user_configured | coordinator_created
    # ADR-087: Deliverable-scoped context
    deliverable_instructions: Optional[str] = None
    deliverable_memory: Optional[dict] = None
    # ADR-092: Mode taxonomy extended
    mode: str = "recurring"  # recurring | goal | reactive | proactive | coordinator
    # ADR-092: Proactive/coordinator review scheduling
    proactive_next_review_at: Optional[str] = None
    # Legacy fields (for backwards compatibility)
    description: Optional[str] = None
    template_structure: Optional[dict] = None


class SourceFetchSummary(BaseModel):
    """ADR-030: Summary of source fetches for a version."""
    sources_total: int = 0
    sources_succeeded: int = 0
    sources_failed: int = 0
    delta_mode_used: bool = False
    time_range_start: Optional[str] = None
    time_range_end: Optional[str] = None


class SourceSnapshot(BaseModel):
    """ADR-049: Snapshot of source state at generation time."""
    platform: str
    resource_id: str
    resource_name: Optional[str] = None
    synced_at: str
    platform_cursor: Optional[str] = None
    item_count: Optional[int] = None
    source_latest_at: Optional[str] = None



class VersionResponse(BaseModel):
    """Deliverable version response."""
    id: str
    deliverable_id: str
    version_number: int
    status: str  # generating, staged, reviewing, approved, rejected
    draft_content: Optional[str] = None
    final_content: Optional[str] = None
    edit_distance_score: Optional[float] = None
    edit_categories: Optional[dict] = None  # ADR-018: categorized edits
    feedback_notes: Optional[str] = None
    created_at: str
    staged_at: Optional[str] = None
    approved_at: Optional[str] = None
    # ADR-028: Delivery tracking
    delivery_status: Optional[str] = None  # pending, delivering, delivered, failed
    delivery_external_id: Optional[str] = None
    delivery_external_url: Optional[str] = None
    delivered_at: Optional[str] = None
    delivery_error: Optional[str] = None
    # ADR-030: Source fetch summary
    source_fetch_summary: Optional[SourceFetchSummary] = None
    # ADR-049: Source snapshots for freshness tracking
    source_snapshots: Optional[list[SourceSnapshot]] = None


class VersionUpdate(BaseModel):
    """Update version request (for approval/rejection/editing)."""
    status: Optional[Literal["staged", "reviewing", "approved", "rejected"]] = None
    final_content: Optional[str] = None
    feedback_notes: Optional[str] = None


def _parse_source_fetch_summary(summary_dict: Optional[dict]) -> Optional[SourceFetchSummary]:
    """Parse raw source_fetch_summary dict from DB into typed response."""
    if not summary_dict:
        return None
    return SourceFetchSummary(
        sources_total=summary_dict.get("sources_total", 0),
        sources_succeeded=summary_dict.get("sources_succeeded", 0),
        sources_failed=summary_dict.get("sources_failed", 0),
        delta_mode_used=summary_dict.get("delta_mode_used", False),
        time_range_start=summary_dict.get("time_range_start"),
        time_range_end=summary_dict.get("time_range_end"),
    )


def _parse_source_snapshots(snapshots_list: Optional[list]) -> Optional[list[SourceSnapshot]]:
    """Parse raw source_snapshots list from DB into typed response (ADR-049)."""
    if not snapshots_list:
        return None
    return [
        SourceSnapshot(
            platform=s.get("platform", ""),
            resource_id=s.get("resource_id", ""),
            resource_name=s.get("resource_name"),
            synced_at=s.get("synced_at", ""),
            platform_cursor=s.get("platform_cursor"),
            item_count=s.get("item_count"),
            source_latest_at=s.get("source_latest_at"),
        )
        for s in snapshots_list
        if isinstance(s, dict)
    ]


# =============================================================================
# Deliverable CRUD Routes
# =============================================================================

@router.post("")
async def create_deliverable(
    request: DeliverableCreate,
    auth: UserClient,
) -> DeliverableResponse:
    """
    Create a new recurring deliverable.

    ADR-053: Enforces active deliverable limits based on user tier.
    """
    from services.platform_limits import check_deliverable_limit

    # ADR-053: Check deliverable limit before creation
    allowed, message = check_deliverable_limit(auth.client, auth.user_id)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "deliverable_limit_reached",
                "message": message,
                "upgrade_url": "/settings?tab=billing",
            }
        )

    # Calculate next_run_at based on schedule
    next_run_at = calculate_next_run(request.schedule)

    # Handle type_config - use provided or get defaults
    type_config = request.type_config
    if type_config is None:
        # For custom type with legacy fields, migrate them
        if request.deliverable_type == "custom" and (request.description or request.template_structure):
            type_config = {
                "description": request.description or "",
                "structure_notes": request.template_structure.format_notes if request.template_structure else None,
            }
        else:
            type_config = get_default_config(request.deliverable_type)

    # Validate type_config against the type
    validated_config = validate_type_config(request.deliverable_type, type_config)

    # ADR-044/045: Use provided type_classification or compute from deliverable_type
    type_classification = request.type_classification or get_type_classification(request.deliverable_type)

    # Create deliverable
    deliverable_data = {
        "user_id": auth.user_id,
        "title": request.title,
        "deliverable_type": request.deliverable_type,
        "type_tier": TYPE_TIERS.get(request.deliverable_type, "stable"),
        "type_config": validated_config,
        # ADR-044/045: Type classification for execution strategy
        "type_classification": type_classification,
        # ADR-031: Platform-native variants
        "platform_variant": request.platform_variant,
        "description": request.description,  # Legacy, kept for backwards compat
        "recipient_context": request.recipient_context.model_dump() if request.recipient_context else {},
        "template_structure": request.template_structure.model_dump() if request.template_structure else {},
        "schedule": request.schedule.model_dump(),
        "sources": [s.model_dump() for s in request.sources],
        "status": "active",
        "next_run_at": next_run_at,
        # ADR-028: Destination-first deliverables
        "destination": request.destination,
        # ADR-092: Mode taxonomy
        "mode": request.mode,
        # ADR-087: Deliverable-scoped context
        "deliverable_instructions": request.deliverable_instructions,
    }

    result = (
        auth.client.table("deliverables")
        .insert(deliverable_data)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to create deliverable")

    deliverable = result.data[0]
    logger.info(f"[DELIVERABLE] Created: {deliverable['id']} - {deliverable['title']}")

    return DeliverableResponse(
        id=deliverable["id"],
        title=deliverable["title"],
        deliverable_type=deliverable.get("deliverable_type", "custom"),
        type_config=deliverable.get("type_config"),
        # ADR-031: Platform-native variants
        platform_variant=deliverable.get("platform_variant"),
        # ADR-044: Type classification
        type_classification=deliverable.get("type_classification"),
        project_id=None,  # ADR-034: Deprecated
        recipient_context=deliverable.get("recipient_context"),
        schedule=deliverable["schedule"],
        sources=deliverable.get("sources", []),
        status=deliverable["status"],
        created_at=deliverable["created_at"],
        updated_at=deliverable["updated_at"],
        next_run_at=deliverable.get("next_run_at"),
        # ADR-028: Destination-first deliverables
        destination=deliverable.get("destination"),
        # ADR-068: Deliverable origin
        origin=deliverable.get("origin", "user_configured"),
        # ADR-087: Deliverable-scoped context
        deliverable_instructions=deliverable.get("deliverable_instructions"),
        deliverable_memory=deliverable.get("deliverable_memory"),
        mode=deliverable.get("mode", "recurring"),
        # Legacy fields
        description=deliverable.get("description"),
        template_structure=deliverable.get("template_structure"),
    )


@router.get("")
async def list_deliverables(
    auth: UserClient,
    status: Optional[str] = None,
    limit: int = 20,
) -> list[DeliverableResponse]:
    """
    List user's deliverables with quality metrics.

    Args:
        status: Filter by status (active, paused, archived)
        limit: Maximum results

    Quality metrics are computed from the last 5 approved versions:
    - quality_score: Latest edit_distance_score (lower = better)
    - quality_trend: "improving" | "stable" | "declining"
    - avg_edit_distance: Average over recent versions
    """
    # Fetch deliverables with versions
    # Note: ADR-034 removed projects table, deliverables are now user-scoped
    query = (
        auth.client.table("deliverables")
        .select("*, deliverable_versions(id, status, version_number, edit_distance_score, approved_at)")
        .eq("user_id", auth.user_id)
        .order("created_at", desc=True)
        .limit(limit)
    )

    if status:
        query = query.eq("status", status)

    result = query.execute()
    deliverables = result.data or []

    responses = []
    for d in deliverables:
        versions = d.get("deliverable_versions", [])
        version_count = len(versions)
        latest_version = max(versions, key=lambda v: v["version_number"]) if versions else None

        # Calculate quality metrics from approved versions
        quality_score = None
        quality_trend = None
        avg_edit_distance = None

        approved_versions = [
            v for v in versions
            if v.get("status") == "approved" and v.get("edit_distance_score") is not None
        ]

        if approved_versions:
            # Sort by version_number descending
            approved_versions.sort(key=lambda v: v["version_number"], reverse=True)
            recent = approved_versions[:5]  # Last 5 approved versions

            # Latest score
            quality_score = recent[0]["edit_distance_score"]

            # Average
            scores = [v["edit_distance_score"] for v in recent]
            avg_edit_distance = sum(scores) / len(scores)

            # Trend: compare first half vs second half
            if len(recent) >= 3:
                older = recent[len(recent)//2:]  # Older versions
                newer = recent[:len(recent)//2]  # Newer versions
                older_avg = sum(v["edit_distance_score"] for v in older) / len(older)
                newer_avg = sum(v["edit_distance_score"] for v in newer) / len(newer)

                # Lower score = better quality (fewer edits needed)
                if newer_avg < older_avg - 0.05:
                    quality_trend = "improving"
                elif newer_avg > older_avg + 0.05:
                    quality_trend = "declining"
                else:
                    quality_trend = "stable"
            elif len(recent) >= 2:
                # Only 2 versions: compare directly
                if recent[0]["edit_distance_score"] < recent[1]["edit_distance_score"] - 0.05:
                    quality_trend = "improving"
                elif recent[0]["edit_distance_score"] > recent[1]["edit_distance_score"] + 0.05:
                    quality_trend = "declining"
                else:
                    quality_trend = "stable"

        # ADR-034: Projects removed, deliverables are user-scoped
        responses.append(DeliverableResponse(
            id=d["id"],
            title=d["title"],
            deliverable_type=d.get("deliverable_type", "custom"),
            type_config=d.get("type_config"),
            # ADR-031: Platform-native variants
            platform_variant=d.get("platform_variant"),
            # ADR-044: Type classification
            type_classification=d.get("type_classification"),
            project_id=None,  # ADR-034: Deprecated
            project_name=None,  # ADR-034: Deprecated
            recipient_context=d.get("recipient_context"),
            schedule=d["schedule"],
            sources=d.get("sources", []),
            status=d["status"],
            created_at=d["created_at"],
            updated_at=d["updated_at"],
            last_run_at=d.get("last_run_at"),
            next_run_at=d.get("next_run_at"),
            version_count=version_count,
            latest_version_status=latest_version["status"] if latest_version else None,
            # ADR-028: Destination-first deliverables
            destination=d.get("destination"),
            quality_score=quality_score,
            quality_trend=quality_trend,
            avg_edit_distance=avg_edit_distance,
            # ADR-068: Deliverable origin
            origin=d.get("origin", "user_configured"),
            # ADR-087: Deliverable-scoped context
            deliverable_instructions=d.get("deliverable_instructions"),
            deliverable_memory=d.get("deliverable_memory"),
            mode=d.get("mode", "recurring"),
            # Legacy
            description=d.get("description"),
            template_structure=d.get("template_structure"),
        ))

    return responses


@router.get("/{deliverable_id}")
async def get_deliverable(
    deliverable_id: UUID,
    auth: UserClient,
) -> dict:
    """
    Get deliverable with recent version history.
    """
    # Get deliverable with project name
    # ADR-034: Projects removed, deliverables are user-scoped
    result = (
        auth.client.table("deliverables")
        .select("*")
        .eq("id", str(deliverable_id))
        .eq("user_id", auth.user_id)
        .single()
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Deliverable not found")

    deliverable = result.data

    # Get recent versions
    versions_result = (
        auth.client.table("deliverable_versions")
        .select("*")
        .eq("deliverable_id", str(deliverable_id))
        .order("version_number", desc=True)
        .limit(10)
        .execute()
    )

    versions = versions_result.data or []

    # Compute feedback summary from approved versions
    approved_versions = [v for v in versions if v.get("status") == "approved"]
    feedback_summary = compute_feedback_summary(approved_versions)

    return {
        "deliverable": DeliverableResponse(
            id=deliverable["id"],
            title=deliverable["title"],
            deliverable_type=deliverable.get("deliverable_type", "custom"),
            type_config=deliverable.get("type_config"),
            # ADR-031: Platform-native variants
            platform_variant=deliverable.get("platform_variant"),
            # ADR-044: Type classification
            type_classification=deliverable.get("type_classification"),
            project_id=None,  # ADR-034: Deprecated
            project_name=None,  # ADR-034: Deprecated
            recipient_context=deliverable.get("recipient_context"),
            schedule=deliverable["schedule"],
            sources=deliverable.get("sources", []),
            status=deliverable["status"],
            created_at=deliverable["created_at"],
            updated_at=deliverable["updated_at"],
            last_run_at=deliverable.get("last_run_at"),
            next_run_at=deliverable.get("next_run_at"),
            version_count=len(versions),
            # ADR-028: Destination-first deliverables
            destination=deliverable.get("destination"),
            # ADR-068: Deliverable origin
            origin=deliverable.get("origin", "user_configured"),
            # ADR-087: Deliverable-scoped context
            deliverable_instructions=deliverable.get("deliverable_instructions"),
            deliverable_memory=deliverable.get("deliverable_memory"),
            mode=deliverable.get("mode", "recurring"),
            # Legacy
            description=deliverable.get("description"),
            template_structure=deliverable.get("template_structure"),
        ),
        "versions": [
            VersionResponse(
                id=v["id"],
                deliverable_id=v["deliverable_id"],
                version_number=v["version_number"],
                status=v["status"],
                draft_content=v.get("draft_content"),
                final_content=v.get("final_content"),
                edit_distance_score=v.get("edit_distance_score"),
                edit_categories=v.get("edit_categories"),
                feedback_notes=v.get("feedback_notes"),
                created_at=v["created_at"],
                staged_at=v.get("staged_at"),
                approved_at=v.get("approved_at"),
                # ADR-028: Delivery fields
                delivery_status=v.get("delivery_status"),
                delivery_external_id=v.get("delivery_external_id"),
                delivery_external_url=v.get("delivery_external_url"),
                delivered_at=v.get("delivered_at"),
                delivery_error=v.get("delivery_error"),
                # ADR-030: Source fetch summary
                source_fetch_summary=_parse_source_fetch_summary(v.get("source_fetch_summary")),
                # ADR-049: Source snapshots
                source_snapshots=v.get("source_snapshots"),
            )
            for v in versions
        ],
        "feedback_summary": feedback_summary,
    }


@router.patch("/{deliverable_id}")
async def update_deliverable(
    deliverable_id: UUID,
    request: DeliverableUpdate,
    auth: UserClient,
) -> DeliverableResponse:
    """
    Update deliverable settings.
    """
    # Verify ownership
    check = (
        auth.client.table("deliverables")
        .select("id")
        .eq("id", str(deliverable_id))
        .eq("user_id", auth.user_id)
        .single()
        .execute()
    )

    if not check.data:
        raise HTTPException(status_code=404, detail="Deliverable not found")

    # Build update data
    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}

    if request.title is not None:
        update_data["title"] = request.title
    if request.deliverable_type is not None:
        update_data["deliverable_type"] = request.deliverable_type
        # If type changes but no new config provided, reset to defaults
        if request.type_config is None:
            update_data["type_config"] = get_default_config(request.deliverable_type)
    if request.type_config is not None:
        # Validate against current or new type
        target_type = request.deliverable_type or check.data.get("deliverable_type", "custom")
        update_data["type_config"] = validate_type_config(target_type, request.type_config)
    # ADR-031: Platform-native variants
    if request.platform_variant is not None:
        update_data["platform_variant"] = request.platform_variant
    if request.recipient_context is not None:
        update_data["recipient_context"] = request.recipient_context.model_dump()
    if request.schedule is not None:
        update_data["schedule"] = request.schedule.model_dump()
        update_data["next_run_at"] = calculate_next_run(request.schedule)
    if request.sources is not None:
        update_data["sources"] = [s.model_dump() for s in request.sources]
    if request.status is not None:
        update_data["status"] = request.status
    # ADR-028: Destination-first deliverables
    if request.destination is not None:
        update_data["destination"] = request.destination
    # ADR-087: Deliverable-scoped context
    if request.deliverable_instructions is not None:
        update_data["deliverable_instructions"] = request.deliverable_instructions
    if request.mode is not None:
        update_data["mode"] = request.mode
    if request.proactive_next_review_at is not None:
        update_data["proactive_next_review_at"] = request.proactive_next_review_at
    # Legacy fields
    if request.description is not None:
        update_data["description"] = request.description
    if request.template_structure is not None:
        update_data["template_structure"] = request.template_structure.model_dump()

    result = (
        auth.client.table("deliverables")
        .update(update_data)
        .eq("id", str(deliverable_id))
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to update deliverable")

    d = result.data[0]

    return DeliverableResponse(
        id=d["id"],
        title=d["title"],
        deliverable_type=d.get("deliverable_type", "custom"),
        type_config=d.get("type_config"),
        # ADR-031: Platform-native variants
        platform_variant=d.get("platform_variant"),
        project_id=None,  # ADR-034: Deprecated
        recipient_context=d.get("recipient_context"),
        schedule=d["schedule"],
        sources=d.get("sources", []),
        status=d["status"],
        created_at=d["created_at"],
        updated_at=d["updated_at"],
        last_run_at=d.get("last_run_at"),
        next_run_at=d.get("next_run_at"),
        # ADR-028: Destination-first deliverables
        destination=d.get("destination"),
        # ADR-068: Deliverable origin
        origin=d.get("origin", "user_configured"),
        # ADR-087: Deliverable-scoped context
        deliverable_instructions=d.get("deliverable_instructions"),
        deliverable_memory=d.get("deliverable_memory"),
        mode=d.get("mode", "recurring"),
        # Legacy
        description=d.get("description"),
        template_structure=d.get("template_structure"),
    )


@router.delete("/{deliverable_id}")
async def archive_deliverable(
    deliverable_id: UUID,
    auth: UserClient,
) -> dict:
    """
    Archive a deliverable (soft delete).
    """
    result = (
        auth.client.table("deliverables")
        .update({"status": "archived", "updated_at": datetime.now(timezone.utc).isoformat()})
        .eq("id", str(deliverable_id))
        .eq("user_id", auth.user_id)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Deliverable not found")

    logger.info(f"[DELIVERABLE] Archived: {deliverable_id}")

    return {"success": True, "message": "Deliverable archived"}


# =============================================================================
# Pipeline Execution Routes
# =============================================================================

@router.post("/{deliverable_id}/run")
async def trigger_run(
    deliverable_id: UUID,
    auth: UserClient,
) -> dict:
    """
    Trigger an ad-hoc deliverable run.

    ADR-042: Uses simplified single-call execute_deliverable_generation().
    """
    from services.deliverable_execution import execute_deliverable_generation

    # Get deliverable
    result = (
        auth.client.table("deliverables")
        .select("*")
        .eq("id", str(deliverable_id))
        .eq("user_id", auth.user_id)
        .single()
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Deliverable not found")

    deliverable = result.data

    if deliverable["status"] == "archived":
        raise HTTPException(status_code=400, detail="Cannot run archived deliverable")

    logger.info(f"[DELIVERABLE] Triggering run: {deliverable_id}")

    # ADR-042: Execute with simplified single-call flow
    exec_result = await execute_deliverable_generation(
        client=auth.client,
        user_id=auth.user_id,
        deliverable=deliverable,
        trigger_context={"type": "manual"},
    )

    return {
        "success": exec_result.get("success", False),
        "version_id": exec_result.get("version_id"),
        "version_number": exec_result.get("version_number"),
        "status": exec_result.get("status"),
        "message": exec_result.get("message"),
    }


# =============================================================================
# ADR-030: Source Freshness Routes
# =============================================================================

class SourceFreshnessItem(BaseModel):
    """ADR-030: Freshness info for a single source."""
    source_index: int
    source_type: str
    provider: Optional[str] = None
    last_fetched_at: Optional[str] = None
    last_status: Optional[str] = None
    items_fetched: int = 0
    is_stale: bool = True


@router.get("/{deliverable_id}/sources/freshness")
async def get_source_freshness(
    deliverable_id: UUID,
    auth: UserClient,
) -> list[SourceFreshnessItem]:
    """
    ADR-030: Get freshness info for all sources of a deliverable.

    Returns when each source was last fetched, how many items were retrieved,
    and whether the source is considered stale (>7 days since last fetch).
    """
    # Verify ownership
    check = (
        auth.client.table("deliverables")
        .select("id, sources")
        .eq("id", str(deliverable_id))
        .eq("user_id", auth.user_id)
        .single()
        .execute()
    )

    if not check.data:
        raise HTTPException(status_code=404, detail="Deliverable not found")

    deliverable = check.data
    sources = deliverable.get("sources", [])

    # Get latest source run for each source
    runs_result = (
        auth.client.table("deliverable_source_runs")
        .select("source_index, source_type, provider, completed_at, status, items_fetched")
        .eq("deliverable_id", str(deliverable_id))
        .order("completed_at", desc=True)
        .execute()
    )

    runs = runs_result.data or []

    # Group by source_index, taking the most recent
    latest_by_index: dict[int, dict] = {}
    for run in runs:
        idx = run["source_index"]
        if idx not in latest_by_index:
            latest_by_index[idx] = run

    # Build response for all sources
    result = []
    from datetime import datetime, timedelta, timezone

    stale_threshold = datetime.now(timezone.utc) - timedelta(days=7)

    for idx, source in enumerate(sources):
        source_type = source.get("type", "description")

        # Only integration sources have freshness tracking
        if source_type != "integration_import":
            continue

        latest = latest_by_index.get(idx)
        if latest:
            completed_at = latest.get("completed_at")
            is_stale = True
            if completed_at:
                try:
                    from dateutil import parser as dateparser
                    completed_dt = dateparser.parse(completed_at)
                    is_stale = completed_dt < stale_threshold
                except Exception:
                    pass

            result.append(SourceFreshnessItem(
                source_index=idx,
                source_type=source_type,
                provider=source.get("provider"),
                last_fetched_at=completed_at,
                last_status=latest.get("status"),
                items_fetched=latest.get("items_fetched", 0),
                is_stale=is_stale,
            ))
        else:
            # No run yet - definitely stale
            result.append(SourceFreshnessItem(
                source_index=idx,
                source_type=source_type,
                provider=source.get("provider"),
                last_fetched_at=None,
                last_status=None,
                items_fetched=0,
                is_stale=True,
            ))

    return result


# =============================================================================
# Version Management Routes
# =============================================================================

@router.get("/{deliverable_id}/versions")
async def list_versions(
    deliverable_id: UUID,
    auth: UserClient,
    limit: int = 20,
) -> list[VersionResponse]:
    """
    List all versions for a deliverable.
    """
    # Verify ownership
    check = (
        auth.client.table("deliverables")
        .select("id")
        .eq("id", str(deliverable_id))
        .eq("user_id", auth.user_id)
        .single()
        .execute()
    )

    if not check.data:
        raise HTTPException(status_code=404, detail="Deliverable not found")

    result = (
        auth.client.table("deliverable_versions")
        .select("*")
        .eq("deliverable_id", str(deliverable_id))
        .order("version_number", desc=True)
        .limit(limit)
        .execute()
    )

    versions = result.data or []

    return [
        VersionResponse(
            id=v["id"],
            deliverable_id=v["deliverable_id"],
            version_number=v["version_number"],
            status=v["status"],
            draft_content=v.get("draft_content"),
            final_content=v.get("final_content"),
            edit_distance_score=v.get("edit_distance_score"),
            feedback_notes=v.get("feedback_notes"),
            created_at=v["created_at"],
            staged_at=v.get("staged_at"),
            approved_at=v.get("approved_at"),
            # ADR-030: Source fetch summary
            source_fetch_summary=_parse_source_fetch_summary(v.get("source_fetch_summary")),
            # ADR-049: Source snapshots for freshness tracking
            source_snapshots=_parse_source_snapshots(v.get("source_snapshots")),
        )
        for v in versions
    ]


@router.get("/{deliverable_id}/versions/{version_id}")
async def get_version(
    deliverable_id: UUID,
    version_id: UUID,
    auth: UserClient,
) -> VersionResponse:
    """
    Get a specific version with full content.
    """
    # Verify ownership through deliverable
    check = (
        auth.client.table("deliverables")
        .select("id")
        .eq("id", str(deliverable_id))
        .eq("user_id", auth.user_id)
        .single()
        .execute()
    )

    if not check.data:
        raise HTTPException(status_code=404, detail="Deliverable not found")

    result = (
        auth.client.table("deliverable_versions")
        .select("*")
        .eq("id", str(version_id))
        .eq("deliverable_id", str(deliverable_id))
        .single()
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="Version not found")

    v = result.data

    return VersionResponse(
        id=v["id"],
        deliverable_id=v["deliverable_id"],
        version_number=v["version_number"],
        status=v["status"],
        draft_content=v.get("draft_content"),
        final_content=v.get("final_content"),
        edit_distance_score=v.get("edit_distance_score"),
        feedback_notes=v.get("feedback_notes"),
        created_at=v["created_at"],
        staged_at=v.get("staged_at"),
        approved_at=v.get("approved_at"),
        # ADR-028: Delivery fields
        delivery_status=v.get("delivery_status"),
        delivery_external_id=v.get("delivery_external_id"),
        delivery_external_url=v.get("delivery_external_url"),
        delivered_at=v.get("delivered_at"),
        # ADR-030: Source fetch summary
        source_fetch_summary=_parse_source_fetch_summary(v.get("source_fetch_summary")),
        # ADR-049: Source snapshots for freshness tracking
        source_snapshots=_parse_source_snapshots(v.get("source_snapshots")),
    )


@router.patch("/{deliverable_id}/versions/{version_id}")
async def update_version(
    deliverable_id: UUID,
    version_id: UUID,
    request: VersionUpdate,
    auth: UserClient,
) -> VersionResponse:
    """
    Update a version (approve, reject, or save edits).

    When final_content differs from draft_content, computes edit diff and score.
    """
    from services.feedback_engine import compute_edit_metrics

    # Verify ownership through deliverable
    check = (
        auth.client.table("deliverables")
        .select("id, title, destination")
        .eq("id", str(deliverable_id))
        .eq("user_id", auth.user_id)
        .single()
        .execute()
    )

    if not check.data:
        raise HTTPException(status_code=404, detail="Deliverable not found")

    # Get current version
    version_result = (
        auth.client.table("deliverable_versions")
        .select("*")
        .eq("id", str(version_id))
        .eq("deliverable_id", str(deliverable_id))
        .single()
        .execute()
    )

    if not version_result.data:
        raise HTTPException(status_code=404, detail="Version not found")

    current = version_result.data

    # Build update
    update_data = {}

    if request.status is not None:
        update_data["status"] = request.status
        if request.status == "approved":
            update_data["approved_at"] = datetime.now(timezone.utc).isoformat()

    if request.final_content is not None:
        update_data["final_content"] = request.final_content

        # Compute edit metrics if we have both draft and final
        if current.get("draft_content"):
            metrics = compute_edit_metrics(
                draft=current["draft_content"],
                final=request.final_content,
            )
            update_data["edit_diff"] = metrics.get("diff")
            update_data["edit_categories"] = metrics.get("categories")
            update_data["edit_distance_score"] = metrics.get("distance_score")

    if request.feedback_notes is not None:
        update_data["feedback_notes"] = request.feedback_notes

    if not update_data:
        raise HTTPException(status_code=400, detail="No updates provided")

    result = (
        auth.client.table("deliverable_versions")
        .update(update_data)
        .eq("id", str(version_id))
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=500, detail="Failed to update version")

    v = result.data[0]

    logger.info(f"[DELIVERABLE] Version updated: {version_id} -> {v['status']}")

    # Activity log: record approval or rejection (ADR-063)
    if request.status in ("approved", "rejected"):
        try:
            from services.activity_log import write_activity
            from services.supabase import get_service_client
            import asyncio
            deliverable_title = check.data.get("title") or str(deliverable_id)
            event_type = "deliverable_approved" if request.status == "approved" else "deliverable_rejected"

            # ADR-064: Enhanced metadata for pattern detection
            metadata = {
                "deliverable_id": str(deliverable_id),
                "version_id": str(version_id),
                "deliverable_type": check.data.get("deliverable_type"),
            }

            # Track edit patterns for memory extraction
            if request.status == "approved":
                had_edits = bool(request.final_content and current.get("draft_content") and request.final_content.strip() != current.get("draft_content", "").strip())
                metadata["had_edits"] = had_edits
                if had_edits and request.final_content and current.get("draft_content"):
                    metadata["final_length"] = len(request.final_content)
                    metadata["draft_length"] = len(current.get("draft_content", ""))

            asyncio.create_task(write_activity(
                client=get_service_client(),
                user_id=auth.user_id,
                event_type=event_type,
                summary=f"{request.status.capitalize()} version of {deliverable_title}",
                event_ref=str(version_id),
                metadata=metadata,
            ))
        except Exception:
            pass  # Non-fatal

    return VersionResponse(
        id=v["id"],
        deliverable_id=v["deliverable_id"],
        version_number=v["version_number"],
        status=v["status"],
        draft_content=v.get("draft_content"),
        final_content=v.get("final_content"),
        edit_distance_score=v.get("edit_distance_score"),
        feedback_notes=v.get("feedback_notes"),
        created_at=v["created_at"],
        staged_at=v.get("staged_at"),
        approved_at=v.get("approved_at"),
        # ADR-028: Delivery fields
        delivery_status=v.get("delivery_status"),
        delivery_external_id=v.get("delivery_external_id"),
        delivery_external_url=v.get("delivery_external_url"),
        delivered_at=v.get("delivered_at"),
    )


# =============================================================================
# ADR-087 Phase 3: Scoped Sessions
# =============================================================================


@router.get("/{deliverable_id}/sessions")
async def list_deliverable_sessions(
    deliverable_id: UUID,
    auth: UserClient,
    limit: int = 10,
) -> list[dict]:
    """
    List scoped chat sessions for a deliverable.

    ADR-087: Sessions are scoped to deliverables via chat_sessions.deliverable_id FK.
    Returns recent sessions with summary and message count.
    """
    # Verify ownership
    check = (
        auth.client.table("deliverables")
        .select("id")
        .eq("id", str(deliverable_id))
        .eq("user_id", auth.user_id)
        .single()
        .execute()
    )
    if not check.data:
        raise HTTPException(status_code=404, detail="Deliverable not found")

    # Query scoped sessions
    result = (
        auth.client.table("chat_sessions")
        .select("id, created_at, summary")
        .eq("deliverable_id", str(deliverable_id))
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    sessions = result.data or []

    # Get message counts per session
    response = []
    for s in sessions:
        count_result = (
            auth.client.table("session_messages")
            .select("id", count="exact")
            .eq("session_id", s["id"])
            .execute()
        )
        response.append({
            "id": s["id"],
            "created_at": s["created_at"],
            "summary": s.get("summary"),
            "message_count": count_result.count or 0,
        })

    return response


# =============================================================================
# Helper Functions
# =============================================================================

def validate_type_config(deliverable_type: DeliverableType, config: dict) -> dict:
    """
    Validate and normalize type_config for a given deliverable type.
    Returns the validated config dict.

    ADR-093: Maps the 7 purpose-first types to their config classes.
    """
    config_classes: dict[str, type[BaseModel]] = {
        "digest": DigestConfig,
        "brief": BriefConfig,
        "status": StatusConfig,
        "watch": WatchConfig,
        "deep_research": DeepResearchConfig,
        "coordinator": CoordinatorConfig,
        "custom": CustomConfig,
    }

    try:
        config_class = config_classes.get(deliverable_type, CustomConfig)
        validated = config_class(**config)
        return validated.model_dump()
    except Exception as e:
        logger.warning(f"[DELIVERABLE] Invalid type_config for {deliverable_type}: {e}")
        return get_default_config(deliverable_type)


def calculate_next_run(schedule: ScheduleConfig) -> str:
    """
    Calculate the next run timestamp based on schedule configuration.

    For now, returns a simple calculation. Will be enhanced with proper
    cron parsing and timezone handling.
    """
    from datetime import timedelta
    import pytz

    now = datetime.now(timezone.utc)
    tz = pytz.timezone(schedule.timezone) if schedule.timezone else pytz.UTC

    # Simple frequency-based calculation
    if schedule.frequency == "daily":
        next_run = now + timedelta(days=1)
    elif schedule.frequency == "weekly":
        next_run = now + timedelta(weeks=1)
    elif schedule.frequency == "biweekly":
        next_run = now + timedelta(weeks=2)
    elif schedule.frequency == "monthly":
        next_run = now + timedelta(days=30)
    else:
        # Custom - default to weekly
        next_run = now + timedelta(weeks=1)

    # If time is specified, set it
    if schedule.time:
        try:
            hour, minute = map(int, schedule.time.split(":"))
            next_run = next_run.replace(hour=hour, minute=minute, second=0, microsecond=0)
        except (ValueError, AttributeError):
            pass

    return next_run.isoformat()

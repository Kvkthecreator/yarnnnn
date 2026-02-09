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
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, Literal, Union, Annotated
from uuid import UUID
from datetime import datetime

from services.supabase import UserClient

logger = logging.getLogger(__name__)


# =============================================================================
# ADR-034: Domain Inference Hook
# =============================================================================

async def _trigger_domain_recomputation(deliverable_id: str, user_id: str):
    """Background task to recompute domains after deliverable change."""
    try:
        from services.domain_inference import on_deliverable_changed
        await on_deliverable_changed(deliverable_id, user_id)
    except Exception as e:
        logger.error(f"[DOMAIN] Failed to recompute domains: {e}")

router = APIRouter()


# =============================================================================
# ADR-019: Deliverable Type Definitions
# =============================================================================

DeliverableType = Literal[
    # Tier 1 - Stable
    "status_report",
    "stakeholder_update",
    "research_brief",
    "meeting_summary",
    "custom",
    # Beta Tier
    "client_proposal",
    "performance_self_assessment",
    "newsletter_section",
    "changelog",
    "one_on_one_prep",
    "board_update",
    # ADR-031 Phase 6: Cross-Platform Synthesizers
    "weekly_status",
    "project_brief",
    "cross_platform_digest",
    "activity_summary",
]

# Type tier mapping for UI display
TYPE_TIERS = {
    "status_report": "stable",
    "stakeholder_update": "stable",
    "research_brief": "stable",
    "meeting_summary": "stable",
    "custom": "experimental",
    "client_proposal": "beta",
    "performance_self_assessment": "beta",
    "newsletter_section": "beta",
    "changelog": "beta",
    # ADR-031 Phase 6: Synthesizers are experimental
    "weekly_status": "experimental",
    "project_brief": "experimental",
    "cross_platform_digest": "experimental",
    "activity_summary": "experimental",
    "one_on_one_prep": "beta",
    "board_update": "beta",
}


class StatusReportSections(BaseModel):
    """Sections to include in a status report."""
    summary: bool = True
    accomplishments: bool = True
    blockers: bool = True
    next_steps: bool = True
    metrics: bool = False


class StatusReportConfig(BaseModel):
    """Configuration for status report type."""
    subject: str  # "Engineering Team", "Project Alpha"
    audience: Literal["manager", "stakeholders", "team", "executive"] = "stakeholders"
    sections: StatusReportSections = Field(default_factory=StatusReportSections)
    detail_level: Literal["brief", "standard", "detailed"] = "standard"
    tone: Literal["formal", "conversational"] = "formal"


class StakeholderUpdateSections(BaseModel):
    """Sections to include in a stakeholder update."""
    executive_summary: bool = True
    highlights: bool = True
    challenges: bool = True
    metrics: bool = False
    outlook: bool = True


class StakeholderUpdateConfig(BaseModel):
    """Configuration for stakeholder update type."""
    audience_type: Literal["investor", "board", "client", "executive"]
    company_or_project: str
    relationship_context: Optional[str] = None  # "Series A investor", "Enterprise client"
    sections: StakeholderUpdateSections = Field(default_factory=StakeholderUpdateSections)
    formality: Literal["formal", "professional", "conversational"] = "professional"
    sensitivity: Literal["public", "confidential"] = "confidential"


class ResearchBriefSections(BaseModel):
    """Sections to include in a research brief."""
    key_takeaways: bool = True
    findings: bool = True
    implications: bool = True
    recommendations: bool = False


class ResearchBriefConfig(BaseModel):
    """Configuration for research brief type."""
    focus_area: Literal["competitive", "market", "technology", "industry"]
    subjects: list[str]  # ["Competitor A", "Competitor B"] or ["AI trends"]
    purpose: Optional[str] = None  # "Inform product roadmap decisions"
    sections: ResearchBriefSections = Field(default_factory=ResearchBriefSections)
    depth: Literal["scan", "analysis", "deep_dive"] = "analysis"


class MeetingSummarySections(BaseModel):
    """Sections to include in a meeting summary."""
    context: bool = True
    discussion: bool = True
    decisions: bool = True
    action_items: bool = True
    followups: bool = True


class MeetingSummaryConfig(BaseModel):
    """Configuration for meeting summary type."""
    meeting_name: str  # "Engineering Weekly", "Product Sync"
    meeting_type: Literal["team_sync", "one_on_one", "standup", "review", "planning"]
    participants: list[str] = Field(default_factory=list)
    sections: MeetingSummarySections = Field(default_factory=MeetingSummarySections)
    format: Literal["narrative", "bullet_points", "structured"] = "structured"


class CustomConfig(BaseModel):
    """Configuration for custom/freeform deliverable type."""
    description: str
    structure_notes: Optional[str] = None
    example_content: Optional[str] = None


# =============================================================================
# ADR-019: Beta Tier Type Definitions
# =============================================================================

class ClientProposalSections(BaseModel):
    """Sections to include in a client proposal."""
    executive_summary: bool = True
    needs_understanding: bool = True
    approach: bool = True
    deliverables: bool = True
    timeline: bool = True
    investment: bool = True
    social_proof: bool = False


class ClientProposalConfig(BaseModel):
    """Configuration for client proposal type (Beta)."""
    client_name: str
    project_type: Literal["new_engagement", "expansion", "renewal"] = "new_engagement"
    service_category: str  # "Brand Strategy", "Web Development"
    sections: ClientProposalSections = Field(default_factory=ClientProposalSections)
    tone: Literal["formal", "consultative", "friendly"] = "consultative"
    include_pricing: bool = True


class PerformanceSelfAssessmentSections(BaseModel):
    """Sections to include in a self-assessment."""
    summary: bool = True
    accomplishments: bool = True
    goals_progress: bool = True
    challenges: bool = True
    development: bool = True
    next_period_goals: bool = True


class PerformanceSelfAssessmentConfig(BaseModel):
    """Configuration for performance self-assessment type (Beta)."""
    review_period: Literal["quarterly", "semi_annual", "annual"] = "quarterly"
    role_level: Literal["ic", "senior_ic", "lead", "manager", "director"] = "ic"
    sections: PerformanceSelfAssessmentSections = Field(default_factory=PerformanceSelfAssessmentSections)
    tone: Literal["humble", "confident", "balanced"] = "balanced"
    quantify_impact: bool = True


class NewsletterSectionSections(BaseModel):
    """Sections to include in a newsletter section."""
    hook: bool = True
    main_content: bool = True
    highlights: bool = True
    cta: bool = True


class NewsletterSectionConfig(BaseModel):
    """Configuration for newsletter section type (Beta)."""
    newsletter_name: str
    section_type: Literal["intro", "main_story", "roundup", "outro"] = "main_story"
    audience: Literal["customers", "team", "investors", "community"] = "customers"
    sections: NewsletterSectionSections = Field(default_factory=NewsletterSectionSections)
    voice: Literal["brand", "personal", "editorial"] = "brand"
    length: Literal["short", "medium", "long"] = "medium"  # 100-200, 200-400, 400-800 words


class ChangelogSections(BaseModel):
    """Sections to include in a changelog."""
    highlights: bool = True
    new_features: bool = True
    improvements: bool = True
    bug_fixes: bool = True
    breaking_changes: bool = False
    whats_next: bool = False


class ChangelogConfig(BaseModel):
    """Configuration for changelog type (Beta)."""
    product_name: str
    release_type: Literal["major", "minor", "patch", "weekly"] = "weekly"
    audience: Literal["developers", "end_users", "mixed"] = "mixed"
    sections: ChangelogSections = Field(default_factory=ChangelogSections)
    format: Literal["technical", "user_friendly", "marketing"] = "user_friendly"
    include_links: bool = True


class OneOnOnePrepSections(BaseModel):
    """Sections to include in 1:1 prep."""
    context: bool = True
    topics: bool = True
    recognition: bool = True
    concerns: bool = True
    career: bool = True
    previous_actions: bool = True


class OneOnOnePrepConfig(BaseModel):
    """Configuration for 1:1 prep type (Beta)."""
    report_name: str
    meeting_cadence: Literal["weekly", "biweekly", "monthly"] = "weekly"
    relationship: Literal["direct_report", "skip_level", "mentee"] = "direct_report"
    sections: OneOnOnePrepSections = Field(default_factory=OneOnOnePrepSections)
    focus_areas: list[Literal["performance", "growth", "wellbeing", "blockers"]] = Field(
        default_factory=lambda: ["performance", "growth"]
    )


class BoardUpdateSections(BaseModel):
    """Sections to include in a board update."""
    executive_summary: bool = True
    metrics: bool = True
    strategic_progress: bool = True
    challenges: bool = True
    financials: bool = True
    asks: bool = True
    outlook: bool = True


class BoardUpdateConfig(BaseModel):
    """Configuration for board update type (Beta)."""
    company_name: str
    stage: Literal["pre_seed", "seed", "series_a", "series_b_plus", "growth"] = "seed"
    update_type: Literal["quarterly", "monthly", "special"] = "quarterly"
    sections: BoardUpdateSections = Field(default_factory=BoardUpdateSections)
    tone: Literal["optimistic", "balanced", "candid"] = "balanced"
    include_comparisons: bool = True  # vs last quarter, vs plan


# =============================================================================
# ADR-031 Phase 6: Cross-Platform Synthesizer Configs
# =============================================================================

class WeeklyStatusSections(BaseModel):
    """Sections to include in weekly status."""
    executive_summary: bool = True
    accomplishments: bool = True
    in_progress: bool = True
    action_items: bool = True
    looking_ahead: bool = True
    key_discussions: bool = True


class WeeklyStatusConfig(BaseModel):
    """Configuration for weekly status synthesizer."""
    project_name: str
    project_id: Optional[str] = None  # Link to project for resource mapping
    time_range_days: int = 7
    include_platforms: list[Literal["slack", "gmail", "notion", "calendar"]] = Field(
        default_factory=lambda: ["slack", "gmail", "notion"]
    )
    sections: WeeklyStatusSections = Field(default_factory=WeeklyStatusSections)
    detail_level: Literal["brief", "standard", "detailed"] = "standard"


class ProjectBriefConfig(BaseModel):
    """Configuration for project brief synthesizer."""
    project_name: str
    project_id: Optional[str] = None
    brief_type: Literal["overview", "status", "handoff"] = "overview"
    include_timeline: bool = True
    include_resources: bool = True


class CrossPlatformDigestConfig(BaseModel):
    """Configuration for cross-platform digest synthesizer."""
    user_name: Optional[str] = None
    time_range_days: int = 7
    include_platforms: list[Literal["slack", "gmail", "notion", "calendar"]] = Field(
        default_factory=lambda: ["slack", "gmail", "notion"]
    )
    priority_focus: Literal["urgent", "balanced", "comprehensive"] = "balanced"


class ActivitySummaryConfig(BaseModel):
    """Configuration for activity summary synthesizer."""
    time_range_days: int = 7
    max_items: int = 10  # Top items to surface
    include_platforms: list[Literal["slack", "gmail", "notion", "calendar"]] = Field(
        default_factory=lambda: ["slack", "gmail", "notion"]
    )


# Union type for type_config
TypeConfig = Union[
    # Tier 1 - Stable
    StatusReportConfig,
    StakeholderUpdateConfig,
    ResearchBriefConfig,
    MeetingSummaryConfig,
    CustomConfig,
    # Beta Tier
    ClientProposalConfig,
    PerformanceSelfAssessmentConfig,
    NewsletterSectionConfig,
    ChangelogConfig,
    OneOnOnePrepConfig,
    BoardUpdateConfig,
    # ADR-031 Phase 6: Cross-Platform Synthesizers
    WeeklyStatusConfig,
    ProjectBriefConfig,
    CrossPlatformDigestConfig,
    ActivitySummaryConfig,
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
    """Get default configuration for a deliverable type."""
    defaults = {
        # Tier 1 - Stable
        "status_report": StatusReportConfig(subject="", audience="stakeholders"),
        "stakeholder_update": StakeholderUpdateConfig(
            audience_type="client",
            company_or_project=""
        ),
        "research_brief": ResearchBriefConfig(
            focus_area="competitive",
            subjects=[]
        ),
        "meeting_summary": MeetingSummaryConfig(
            meeting_name="",
            meeting_type="team_sync"
        ),
        "custom": CustomConfig(description=""),
        # Beta Tier
        "client_proposal": ClientProposalConfig(
            client_name="",
            service_category=""
        ),
        "performance_self_assessment": PerformanceSelfAssessmentConfig(),
        "newsletter_section": NewsletterSectionConfig(
            newsletter_name=""
        ),
        "changelog": ChangelogConfig(
            product_name=""
        ),
        "one_on_one_prep": OneOnOnePrepConfig(
            report_name=""
        ),
        "board_update": BoardUpdateConfig(
            company_name=""
        ),
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
    platform_variant: Optional[str] = None  # e.g., "slack_digest" for status_report
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
    governance: Optional[Literal["manual", "semi_auto", "full_auto"]] = "manual"
    # ADR-031 Phase 6: Synthesizer flag
    is_synthesizer: bool = False  # If true, uses cross-platform context assembly
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
    governance: Optional[Literal["manual", "semi_auto", "full_auto"]] = None
    # ADR-031 Phase 6: Synthesizer flag
    is_synthesizer: Optional[bool] = None
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
    platform_variant: Optional[str] = None  # e.g., "slack_digest" for status_report
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
    governance: str = "manual"  # manual, semi_auto, full_auto
    # ADR-031: System-enforced governance ceiling
    governance_ceiling: Optional[str] = None  # Max governance based on destination
    # ADR-031 Phase 6: Synthesizer fields
    is_synthesizer: bool = False  # Uses cross-platform context assembly
    linked_resources: Optional[list[dict]] = None  # Project resources for synthesizers
    # Quality metrics (ADR-018: feedback loop)
    quality_score: Optional[float] = None  # Latest edit_distance_score (0=no edits, 1=full rewrite)
    quality_trend: Optional[str] = None  # "improving", "stable", "declining"
    avg_edit_distance: Optional[float] = None  # Average over last 5 versions
    # ADR-030: Source freshness
    source_freshness: Optional[list[dict]] = None  # [{source_index, provider, last_fetched_at, is_stale}]
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
    # ADR-030: Source fetch summary
    source_fetch_summary: Optional[SourceFetchSummary] = None


class VersionUpdate(BaseModel):
    """Update version request (for approval/rejection/editing)."""
    status: Optional[Literal["reviewing", "approved", "rejected"]] = None
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


# =============================================================================
# Deliverable CRUD Routes
# =============================================================================

@router.post("")
async def create_deliverable(
    request: DeliverableCreate,
    auth: UserClient,
    background_tasks: BackgroundTasks,
) -> DeliverableResponse:
    """
    Create a new recurring deliverable.
    """
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

    # ADR-031: Compute governance ceiling from destination
    governance_ceiling = compute_governance_ceiling(request.destination)

    # Create deliverable
    deliverable_data = {
        "user_id": auth.user_id,
        "title": request.title,
        "deliverable_type": request.deliverable_type,
        "type_tier": TYPE_TIERS.get(request.deliverable_type, "stable"),
        "type_config": validated_config,
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
        "governance": request.governance or "manual",
        # ADR-031: Governance ceiling
        "governance_ceiling": governance_ceiling,
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

    # ADR-034: Trigger domain recomputation if deliverable has sources
    if request.sources:
        background_tasks.add_task(
            _trigger_domain_recomputation,
            deliverable["id"],
            auth.user_id
        )

    return DeliverableResponse(
        id=deliverable["id"],
        title=deliverable["title"],
        deliverable_type=deliverable.get("deliverable_type", "custom"),
        type_config=deliverable.get("type_config"),
        # ADR-031: Platform-native variants
        platform_variant=deliverable.get("platform_variant"),
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
        governance=deliverable.get("governance", "manual"),
        # ADR-031: Governance ceiling
        governance_ceiling=deliverable.get("governance_ceiling"),
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
            governance=d.get("governance", "manual"),
            # ADR-031: Governance ceiling
            governance_ceiling=d.get("governance_ceiling"),
            quality_score=quality_score,
            quality_trend=quality_trend,
            avg_edit_distance=avg_edit_distance,
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
            governance=deliverable.get("governance", "manual"),
            # ADR-031: Governance ceiling
            governance_ceiling=deliverable.get("governance_ceiling"),
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
    background_tasks: BackgroundTasks,
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
    update_data = {"updated_at": datetime.utcnow().isoformat()}

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
        # ADR-031: Recalculate governance ceiling when destination changes
        update_data["governance_ceiling"] = compute_governance_ceiling(request.destination)
    if request.governance is not None:
        update_data["governance"] = request.governance
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

    # ADR-034: Trigger domain recomputation if sources changed
    if request.sources is not None:
        background_tasks.add_task(
            _trigger_domain_recomputation,
            str(deliverable_id),
            auth.user_id
        )

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
        governance=d.get("governance", "manual"),
        # ADR-031: Governance ceiling
        governance_ceiling=d.get("governance_ceiling"),
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
        .update({"status": "archived", "updated_at": datetime.utcnow().isoformat()})
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

    Creates a new version and starts the gather → synthesize → stage pipeline.
    """
    from services.deliverable_pipeline import execute_deliverable_pipeline

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

    # Get next version number
    version_result = (
        auth.client.table("deliverable_versions")
        .select("version_number")
        .eq("deliverable_id", str(deliverable_id))
        .order("version_number", desc=True)
        .limit(1)
        .execute()
    )

    next_version = 1
    if version_result.data:
        next_version = version_result.data[0]["version_number"] + 1

    logger.info(f"[DELIVERABLE] Triggering run: {deliverable_id} v{next_version}")

    # Execute pipeline
    pipeline_result = await execute_deliverable_pipeline(
        client=auth.client,
        user_id=auth.user_id,
        deliverable_id=str(deliverable_id),
        version_number=next_version,
    )

    return {
        "success": pipeline_result.get("success", False),
        "version_id": pipeline_result.get("version_id"),
        "version_number": next_version,
        "status": pipeline_result.get("status"),
        "message": pipeline_result.get("message"),
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

    ADR-028: If governance=semi_auto and status changes to approved,
    automatically triggers delivery to the configured destination.
    """
    from services.feedback_engine import compute_edit_metrics
    from services.delivery import get_delivery_service

    # Verify ownership through deliverable and get destination/governance
    check = (
        auth.client.table("deliverables")
        .select("id, destination, governance")
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
            update_data["approved_at"] = datetime.utcnow().isoformat()

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

    # ADR-028: Auto-deliver if governance=semi_auto and status=approved
    delivery_result = None
    if request.status == "approved" and check.data.get("governance") == "semi_auto":
        if check.data.get("destination"):
            try:
                delivery_service = get_delivery_service(auth.client)
                delivery_result = await delivery_service.deliver_version(
                    version_id=str(version_id),
                    user_id=auth.user_id
                )
                logger.info(
                    f"[DELIVERABLE] Auto-delivery triggered for {version_id}: "
                    f"{delivery_result.status.value}"
                )
            except Exception as e:
                # Log but don't fail the approval
                logger.error(f"[DELIVERABLE] Auto-delivery failed for {version_id}: {e}")

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
# Helper Functions
# =============================================================================

def compute_governance_ceiling(destination: Optional[dict]) -> Optional[str]:
    """
    ADR-031: Compute governance ceiling based on destination.

    | Destination | Ceiling |
    |-------------|---------|
    | Internal Slack | full_auto |
    | External Slack | semi_auto |
    | Email to external | manual |
    | Notion (internal) | full_auto |
    | Download | full_auto |
    """
    if not destination:
        return None

    platform = destination.get("platform")
    target = destination.get("target", "")

    if platform == "slack":
        # TODO: Detect shared channels (external) vs internal
        # For now, assume all Slack is internal
        return "full_auto"
    elif platform == "notion":
        return "full_auto"
    elif platform in ("email", "gmail"):
        # Email to external always requires manual review
        return "manual"
    elif platform == "download":
        return "full_auto"
    else:
        return "manual"


def validate_type_config(deliverable_type: DeliverableType, config: dict) -> dict:
    """
    Validate and normalize type_config for a given deliverable type.
    Returns the validated config dict.
    """
    # Map types to their config classes
    config_classes = {
        # Tier 1 - Stable
        "status_report": StatusReportConfig,
        "stakeholder_update": StakeholderUpdateConfig,
        "research_brief": ResearchBriefConfig,
        "meeting_summary": MeetingSummaryConfig,
        "custom": CustomConfig,
        # Beta Tier
        "client_proposal": ClientProposalConfig,
        "performance_self_assessment": PerformanceSelfAssessmentConfig,
        "newsletter_section": NewsletterSectionConfig,
        "changelog": ChangelogConfig,
        "one_on_one_prep": OneOnOnePrepConfig,
        "board_update": BoardUpdateConfig,
    }

    try:
        config_class = config_classes.get(deliverable_type)
        if config_class:
            validated = config_class(**config)
        else:
            # Unknown type, treat as custom
            validated = CustomConfig(description=str(config.get("description", "")))

        return validated.model_dump()
    except Exception as e:
        logger.warning(f"[DELIVERABLE] Invalid type_config for {deliverable_type}: {e}")
        # Return a default config on validation failure
        return get_default_config(deliverable_type)


def calculate_next_run(schedule: ScheduleConfig) -> str:
    """
    Calculate the next run timestamp based on schedule configuration.

    For now, returns a simple calculation. Will be enhanced with proper
    cron parsing and timezone handling.
    """
    from datetime import timedelta
    import pytz

    now = datetime.utcnow()
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

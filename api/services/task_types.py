"""
Task Type Registry — ADR-145 + ADR-152

Deliverable-first task types. Each type defines:
  - What the user gets (display_name, description, category)
  - How it's produced (process: ordered agent steps using STEP_INSTRUCTIONS templates)
  - When it runs (default_schedule)
  - What format (output_format, export_options)
  - What context it needs (context_reads/context_writes from directory registry)
  - Where output goes (output_category from directory registry)

Process step instructions are GENERIC TEMPLATES (ADR-152) — resolved at runtime
with actual context domain paths. Per-task-type specificity lives in DELIVERABLE.md
(quality criteria, format expectations), not in step instructions.

Canonical docs:
  - docs/adr/ADR-145-task-type-registry-premeditated-orchestration.md
  - docs/adr/ADR-152-unified-directory-registry.md
  - docs/architecture/registry-matrix.md
"""

from __future__ import annotations

from typing import Any, Optional

from services.agent_framework import AGENT_TYPES


# =============================================================================
# Step Instruction Templates (ADR-152)
# =============================================================================
# Generic per step type — pipeline injects actual domain paths at runtime.
# Per-task-type quality criteria live in DELIVERABLE.md, not here.

STEP_INSTRUCTIONS = {
    "update-context": (
        "Read the existing context files in your assigned context domains. "
        "These contain accumulated intelligence from prior cycles. "
        "Research new signals via web search and platform context. "
        "UPDATE entity files with new findings — add dated entries to signal sections, "
        "update assessments if your view has changed. Create new entity files for "
        "newly discovered items. Update synthesis files with cross-entity pattern changes.\n\n"
        "Append to the cross-domain signal log with dated entries for this cycle.\n\n"
        "Your output for this step: a CHANGELOG of what you added, updated, or discovered."
    ),

    "derive-output": (
        "Read ALL context files from your assigned context domains. "
        "Produce the deliverable as specified in DELIVERABLE.md. "
        "This is a DERIVATIVE of accumulated context — emphasize what CHANGED "
        "since last cycle. The reader has seen prior outputs; lead with what's new. "
        "Reference persistent assets from context domains where they exist.\n\n"
        "Structure: What's New → What Changed → What It Means → Standing Context (brief)."
    ),

    "capture-and-report": (
        "Read existing context files (patterns, signal history). "
        "Gather new signals from platform context. Log new signals to the signal domain. "
        "Update pattern synthesis if new cross-signal patterns emerge. "
        "Produce the deliverable emphasizing what's new since last cycle."
    ),
}


# =============================================================================
# Task Type Registry
# =============================================================================

TASK_TYPE_CATEGORIES = {
    "intelligence": {"display_name": "Intelligence & Research", "order": 1},
    "operations": {"display_name": "Business Operations", "order": 2},
    "platform": {"display_name": "Platform Digests", "order": 3},
    "content": {"display_name": "Content & Communications", "order": 4},
    "tracking": {"display_name": "Data & Tracking", "order": 5},
}

TASK_TYPES: dict[str, dict[str, Any]] = {

    # ── Intelligence & Research ──

    "competitive-intel-brief": {
        "display_name": "Competitive Intelligence Brief",
        "description": "Research-backed competitive analysis with charts, diagrams, and evidence-linked findings.",
        "category": "intelligence",
        "default_schedule": "weekly",
        "output_format": "html",
        "layout_mode": "document",
        "export_options": ["pdf"],
        "process": [
            {
                "agent_type": "research",
                "step": "update-context",
                "instruction": STEP_INSTRUCTIONS["update-context"],
            },
            {
                "agent_type": "content",
                "step": "derive-output",
                "instruction": STEP_INSTRUCTIONS["derive-output"],
            },
        ],
        "context_sources": ["web", "platforms", "workspace"],
        "requires_platform": None,
        "default_objective": {
            "deliverable": "Weekly competitive intelligence brief",
            "audience": "Leadership and strategy team",
            "purpose": "Track competitive landscape and identify strategic opportunities",
            "format": "Structured report with charts and diagrams",
        },
        "default_deliverable": {
            "output": {
                "format": "html",
                "word_count": "2000-3000",
                "layout": ["Executive Summary", "Key Findings", "Competitive Positioning", "Trend Analysis", "Implications", "Sources"],
            },
            "assets": [
                {"type": "chart", "subtype": "trend", "min_count": 1, "description": "Quantified trend data"},
                {"type": "chart", "subtype": "comparison", "min_count": 1, "description": "Competitor comparison"},
                {"type": "mermaid", "subtype": "positioning", "min_count": 1, "description": "Competitive positioning map"},
            ],
            "quality_criteria": [
                "Every claim has inline source citation",
                "Minimum 3 competitors analyzed",
                "Forward-looking implications not just historical reporting",
            ],
        },
        "context_reads": ["competitors"],
        "context_writes": ["competitors", "signals"],
        "output_category": "briefs",
    },

    "market-research-report": {
        "display_name": "Market Research Report",
        "description": "Deep-dive investigation on a specific topic with data-backed analysis and trend visualizations.",
        "category": "intelligence",
        "default_schedule": "monthly",
        "output_format": "html",
        "layout_mode": "document",
        "export_options": ["pdf"],
        "process": [
            {
                "agent_type": "research",
                "step": "update-context",
                "instruction": STEP_INSTRUCTIONS["update-context"],
            },
            {
                "agent_type": "content",
                "step": "derive-output",
                "instruction": STEP_INSTRUCTIONS["derive-output"],
            },
        ],
        "context_sources": ["web", "platforms", "workspace"],
        "requires_platform": None,
        "default_objective": {
            "deliverable": "Market research report",
            "audience": "Decision-makers and strategists",
            "purpose": "Understand market dynamics and inform strategic decisions",
            "format": "Comprehensive report with visualizations",
        },
        "default_deliverable": {
            "output": {
                "format": "html",
                "word_count": "3000-5000",
                "layout": ["Executive Summary", "Market Overview", "Key Players", "Technology Trends", "Opportunities & Threats", "Recommendations", "Sources"],
            },
            "assets": [
                {"type": "chart", "subtype": "distribution", "min_count": 1, "description": "Market share or segment breakdown"},
                {"type": "chart", "subtype": "trend", "min_count": 1, "description": "Growth trend data"},
                {"type": "mermaid", "subtype": "landscape", "min_count": 1, "description": "Market landscape map"},
            ],
            "quality_criteria": [
                "Data-backed claims with recency noted",
                "Minimum 5 key players profiled",
                "Clear opportunity identification",
            ],
        },
        "context_reads": ["market"],
        "context_writes": ["market", "signals"],
        "output_category": "reports",
    },

    "industry-signal-monitor": {
        "display_name": "Industry Signal Monitor",
        "description": "Surface-level industry scan with deep-dives on signals that matter.",
        "category": "intelligence",
        "default_schedule": "weekly",
        "output_format": "html",
        "layout_mode": "document",
        "export_options": [],
        "process": [
            {
                "agent_type": "marketing",
                "step": "capture-and-report",
                "instruction": STEP_INSTRUCTIONS["capture-and-report"],
            },
        ],
        "context_sources": ["web", "platforms", "workspace"],
        "requires_platform": None,
        "default_objective": {
            "deliverable": "Industry signal report",
            "audience": "Strategy and product teams",
            "purpose": "Catch important industry signals early and assess their impact",
            "format": "Signal list with deep-dive analysis on top signals",
        },
        "default_deliverable": {
            "output": {
                "format": "html",
                "word_count": "1000-2000",
                "layout": ["Signal Summary", "Key Signals", "Emerging Patterns", "Watch List"],
            },
            "assets": [],
            "quality_criteria": [
                "Signals categorized by impact level",
                "Each signal has source and date",
                "Pattern identification across multiple signals",
            ],
        },
        "context_reads": ["signals"],
        "context_writes": ["signals"],
        "output_category": "briefs",
    },

    "due-diligence-summary": {
        "display_name": "Due Diligence Summary",
        "description": "Structured investigation of a company, market, or opportunity with risk flags and evidence.",
        "category": "intelligence",
        "default_schedule": "on-demand",
        "output_format": "html",
        "layout_mode": "document",
        "export_options": ["pdf"],
        "process": [
            {
                "agent_type": "research",
                "step": "update-context",
                "instruction": STEP_INSTRUCTIONS["update-context"],
            },
            {
                "agent_type": "content",
                "step": "derive-output",
                "instruction": STEP_INSTRUCTIONS["derive-output"],
            },
        ],
        "context_sources": ["web", "workspace"],
        "requires_platform": None,
        "default_objective": {
            "deliverable": "Due diligence summary",
            "audience": "Decision-makers evaluating an opportunity",
            "purpose": "Assess viability and risks of a company, market, or opportunity",
            "format": "Structured report with org charts and risk assessment",
        },
        "default_deliverable": {
            "output": {
                "format": "html",
                "word_count": "3000-5000",
                "layout": ["Executive Summary", "Company Overview", "Financial Analysis", "Risk Assessment", "Competitive Position", "Recommendation"],
            },
            "assets": [
                {"type": "chart", "subtype": "comparison", "min_count": 1, "description": "Financial metrics comparison"},
                {"type": "mermaid", "subtype": "flowchart", "min_count": 1, "description": "Corporate structure or process diagram"},
            ],
            "quality_criteria": [
                "All claims verified with sources",
                "Risk factors explicitly identified",
                "Clear recommendation with supporting evidence",
            ],
        },
        "context_reads": ["competitors", "market"],
        "context_writes": ["competitors", "signals"],
        "output_category": "reports",
    },

    # ── Business Operations ──

    "meeting-prep-brief": {
        "display_name": "Meeting Prep Brief",
        "description": "Relationship context from your platforms combined with fresh external research on attendees.",
        "category": "operations",
        "default_schedule": "on-demand",
        "output_format": "html",
        "layout_mode": "document",
        "export_options": [],
        "process": [
            {
                "agent_type": "crm",
                "step": "update-context",
                "instruction": STEP_INSTRUCTIONS["update-context"],
            },
            {
                "agent_type": "research",
                "step": "derive-output",
                "instruction": STEP_INSTRUCTIONS["derive-output"],
            },
        ],
        "context_sources": ["web", "platforms", "workspace"],
        "requires_platform": None,
        "default_objective": {
            "deliverable": "Meeting preparation brief",
            "audience": "You, before the meeting",
            "purpose": "Walk into meetings prepared with relationship context and fresh intelligence",
            "format": "Context summary, talking points, open items, and agenda suggestions",
        },
        "default_deliverable": {
            "output": {
                "format": "html",
                "word_count": "800-1500",
                "layout": ["Context", "Last Interaction", "Agenda Items", "Talking Points", "Open Items"],
            },
            "assets": [],
            "quality_criteria": [
                "Actionable talking points",
                "References specific prior interactions",
                "Scannable in under 2 minutes",
            ],
        },
        "context_reads": ["relationships", "competitors"],
        "context_writes": ["relationships", "signals"],
        "output_category": "briefs",
    },

    "stakeholder-update": {
        "display_name": "Stakeholder / Board Update",
        "description": "Executive-quality update with KPI dashboards, metric cards, and narrative context.",
        "category": "operations",
        "default_schedule": "monthly",
        "output_format": "html",
        "layout_mode": "dashboard",
        "export_options": ["pdf", "pptx"],
        "process": [
            {
                "agent_type": "research",
                "step": "update-context",
                "instruction": STEP_INSTRUCTIONS["update-context"],
            },
            {
                "agent_type": "content",
                "step": "derive-output",
                "instruction": STEP_INSTRUCTIONS["derive-output"],
            },
        ],
        "context_sources": ["platforms", "workspace"],
        "requires_platform": None,
        "default_objective": {
            "deliverable": "Stakeholder or board update",
            "audience": "Board members, investors, or leadership",
            "purpose": "Keep stakeholders informed with professional-quality updates",
            "format": "Dashboard-style report with KPI cards, charts, and narrative",
        },
        "default_deliverable": {
            "output": {
                "format": "html",
                "word_count": "2000-3000",
                "layout": ["Executive Summary", "Key Milestones", "Challenges & Mitigations", "Financial Overview", "Forward Look", "Appendix"],
            },
            "assets": [
                {"type": "chart", "subtype": "trend", "min_count": 1, "description": "KPI dashboard or progress metrics"},
                {"type": "chart", "subtype": "comparison", "min_count": 1, "description": "Budget vs actual or milestone tracking"},
            ],
            "quality_criteria": [
                "Board-level polish",
                "Key milestones with status",
                "Forward-looking strategic priorities",
            ],
        },
        "context_reads": ["competitors", "market", "projects", "relationships"],
        "context_writes": ["projects", "signals"],
        "output_category": "reports",
    },

    "relationship-health-digest": {
        "display_name": "Relationship Health Digest",
        "description": "Interaction patterns from Slack synthesized into actionable relationship intelligence.",
        "category": "operations",
        "default_schedule": "weekly",
        "output_format": "html",
        "layout_mode": "document",
        "export_options": [],
        "process": [
            {
                "agent_type": "crm",
                "step": "update-context",
                "instruction": STEP_INSTRUCTIONS["update-context"],
            },
            {
                "agent_type": "content",
                "step": "derive-output",
                "instruction": STEP_INSTRUCTIONS["derive-output"],
            },
        ],
        "context_sources": ["platforms", "workspace"],
        "requires_platform": "slack",
        "default_objective": {
            "deliverable": "Relationship health digest",
            "audience": "You, for relationship management",
            "purpose": "Stay on top of professional relationships and never drop the ball",
            "format": "Health summary with follow-up recommendations",
        },
        "default_deliverable": {
            "output": {
                "format": "html",
                "word_count": "1000-2000",
                "layout": ["Summary", "Active Relationships", "Risk Flags", "Follow-ups Due", "Engagement Trends"],
            },
            "assets": [
                {"type": "chart", "subtype": "trend", "min_count": 1, "description": "Engagement frequency trends"},
            ],
            "quality_criteria": [
                "Actionable follow-up recommendations",
                "Risk flags for declining engagement",
                "Personalized per relationship",
            ],
        },
        "context_reads": ["relationships"],
        "context_writes": ["relationships", "signals"],
        "output_category": "reports",
    },

    "project-status-report": {
        "display_name": "Project Status Report",
        "description": "Cross-platform status synthesis — team activity from Slack composed into a polished report.",
        "category": "operations",
        "default_schedule": "weekly",
        "output_format": "html",
        "layout_mode": "document",
        "export_options": ["pdf"],
        "process": [
            {
                "agent_type": "research",
                "step": "update-context",
                "instruction": STEP_INSTRUCTIONS["update-context"],
            },
            {
                "agent_type": "content",
                "step": "derive-output",
                "instruction": STEP_INSTRUCTIONS["derive-output"],
            },
        ],
        "context_sources": ["platforms", "workspace"],
        "requires_platform": "slack",
        "default_objective": {
            "deliverable": "Project status report",
            "audience": "Project stakeholders and leadership",
            "purpose": "Keep everyone aligned on project progress and blockers",
            "format": "Structured status report with activity highlights",
        },
        "default_deliverable": {
            "output": {
                "format": "html",
                "word_count": "1500-2500",
                "layout": ["Status Summary", "Progress by Workstream", "Blockers & Risks", "Next Week Priorities", "Resource Needs"],
            },
            "assets": [
                {"type": "chart", "subtype": "comparison", "min_count": 1, "description": "Progress tracking or milestone status"},
            ],
            "quality_criteria": [
                "Clear status per workstream",
                "Blockers explicitly flagged with owners",
                "Actionable next steps",
            ],
        },
        "context_reads": ["projects"],
        "context_writes": ["projects", "signals"],
        "output_category": "reports",
    },

    # ── Platform Digests ──

    "slack-recap": {
        "display_name": "Slack Recap",
        "description": "Decisions, action items, key discussions, and FYIs from your Slack channels.",
        "category": "platform",
        "default_schedule": "daily",
        "output_format": "html",
        "layout_mode": "document",
        "export_options": [],
        "process": [
            {
                "agent_type": "slack_bot",
                "step": "capture-and-report",
                "instruction": STEP_INSTRUCTIONS["capture-and-report"],
            },
        ],
        "context_sources": ["platforms"],
        "requires_platform": "slack",
        "default_objective": {
            "deliverable": "Slack activity recap",
            "audience": "You and your team",
            "purpose": "Never miss important Slack discussions, decisions, or action items",
            "format": "Structured recap with decisions, action items, discussions, and FYIs",
        },
        "default_deliverable": {
            "output": {
                "format": "html",
                "word_count": "500-1500",
                "layout": ["Highlights", "Decisions Made", "Action Items", "Key Discussions", "FYIs"],
            },
            "assets": [],
            "quality_criteria": [
                "Decisions and action items clearly attributed",
                "Thread-level summarization not message-level",
                "Skip bot messages and routine posts",
            ],
        },
        "context_reads": ["signals"],
        "context_writes": ["signals"],
        "output_category": "briefs",
    },

    "notion-sync-report": {
        "display_name": "Notion Sync Report",
        "description": "What changed in your Notion workspace — updates, staleness flags, and structure suggestions.",
        "category": "platform",
        "default_schedule": "weekly",
        "output_format": "html",
        "layout_mode": "document",
        "export_options": [],
        "process": [
            {
                "agent_type": "notion_bot",
                "step": "capture-and-report",
                "instruction": STEP_INSTRUCTIONS["capture-and-report"],
            },
        ],
        "context_sources": ["platforms"],
        "requires_platform": "notion",
        "default_objective": {
            "deliverable": "Notion workspace sync report",
            "audience": "You and knowledge base maintainers",
            "purpose": "Keep your Notion workspace healthy and up-to-date",
            "format": "Change summary with staleness flags and suggestions",
        },
        "default_deliverable": {
            "output": {
                "format": "html",
                "word_count": "500-1500",
                "layout": ["Changes Summary", "Updated Pages", "New Content", "Stale Content Flags"],
            },
            "assets": [],
            "quality_criteria": [
                "Meaningful changes highlighted over formatting edits",
                "Links to original Notion pages",
                "Stale content flagged",
            ],
        },
        "context_reads": ["signals"],
        "context_writes": ["signals"],
        "output_category": "briefs",
    },

    # ── Content & Communications ──

    "content-brief": {
        "display_name": "Content Brief / Blog Draft",
        "description": "Research-backed content with competitive landscape context and visual assets.",
        "category": "content",
        "default_schedule": "on-demand",
        "output_format": "html",
        "layout_mode": "document",
        "export_options": ["pdf"],
        "process": [
            {
                "agent_type": "research",
                "step": "update-context",
                "instruction": STEP_INSTRUCTIONS["update-context"],
            },
            {
                "agent_type": "content",
                "step": "derive-output",
                "instruction": STEP_INSTRUCTIONS["derive-output"],
            },
        ],
        "context_sources": ["web", "platforms", "workspace"],
        "requires_platform": None,
        "default_objective": {
            "deliverable": "Content brief or blog draft",
            "audience": "Content team or direct publishing",
            "purpose": "Produce research-backed content that stands out",
            "format": "Structured content with visual assets",
        },
        "default_deliverable": {
            "output": {
                "format": "html",
                "word_count": "2000-4000",
                "layout": ["Brief Overview", "Target Audience", "Key Messages", "Outline", "Draft Content", "Sources"],
            },
            "assets": [
                {"type": "mermaid", "subtype": "flowchart", "min_count": 1, "description": "Content structure or narrative flow"},
            ],
            "quality_criteria": [
                "Audience-appropriate tone and depth",
                "Clear key messages",
                "Draft ready for light editing",
            ],
        },
        "context_reads": ["content"],
        "context_writes": ["content"],
        "output_category": "content_output",
    },

    "launch-material": {
        "display_name": "Launch / Announcement Material",
        "description": "GTM intelligence transformed into polished launch material with competitive positioning.",
        "category": "content",
        "default_schedule": "on-demand",
        "output_format": "html",
        "layout_mode": "presentation",
        "export_options": ["pdf", "pptx"],
        "process": [
            {
                "agent_type": "research",
                "step": "update-context",
                "instruction": STEP_INSTRUCTIONS["update-context"],
            },
            {
                "agent_type": "content",
                "step": "derive-output",
                "instruction": STEP_INSTRUCTIONS["derive-output"],
            },
        ],
        "context_sources": ["web", "platforms", "workspace"],
        "requires_platform": None,
        "default_objective": {
            "deliverable": "Launch or announcement material",
            "audience": "External audience or internal stakeholders",
            "purpose": "Launch with clear positioning and professional presentation",
            "format": "Presentation-style material with positioning visuals",
        },
        "default_deliverable": {
            "output": {
                "format": "html",
                "word_count": "1500-3000",
                "layout": ["Launch Summary", "Key Messages", "Target Audiences", "Deliverables Checklist", "Timeline", "Draft Content"],
            },
            "assets": [
                {"type": "mermaid", "subtype": "timeline", "min_count": 1, "description": "Launch timeline or rollout plan"},
            ],
            "quality_criteria": [
                "Consistent messaging across all materials",
                "Clear audience segmentation",
                "Actionable deliverables checklist",
            ],
        },
        "context_reads": ["content", "competitors", "market"],
        "context_writes": ["content"],
        "output_category": "content_output",
    },

    # ── Data & Tracking ──

    "gtm-tracker": {
        "display_name": "GTM Tracker",
        "description": "Competitive moves, market signals, and feature matrices — intelligence with visual tracking.",
        "category": "tracking",
        "default_schedule": "weekly",
        "output_format": "html",
        "layout_mode": "dashboard",
        "export_options": [],
        "process": [
            {
                "agent_type": "marketing",
                "step": "update-context",
                "instruction": STEP_INSTRUCTIONS["update-context"],
            },
            {
                "agent_type": "content",
                "step": "derive-output",
                "instruction": STEP_INSTRUCTIONS["derive-output"],
            },
        ],
        "context_sources": ["web", "platforms", "workspace"],
        "requires_platform": None,
        "default_objective": {
            "deliverable": "GTM tracker",
            "audience": "Product, marketing, and strategy teams",
            "purpose": "Track competitive landscape and identify go-to-market opportunities",
            "format": "Dashboard-style tracker with feature matrices and signal cards",
        },
        "default_deliverable": {
            "output": {
                "format": "html",
                "word_count": "1500-2500",
                "layout": ["Market Pulse", "Competitive Moves", "Channel Performance", "Opportunities", "Recommendations"],
            },
            "assets": [
                {"type": "chart", "subtype": "comparison", "min_count": 1, "description": "Feature matrix or competitive comparison"},
                {"type": "chart", "subtype": "trend", "min_count": 1, "description": "Channel performance trends"},
            ],
            "quality_criteria": [
                "Signal separated from noise",
                "Every finding has an implication",
                "Quantified where possible",
            ],
        },
        "context_reads": ["competitors", "market"],
        "context_writes": ["competitors", "signals"],
        "output_category": "reports",
    },
}


# =============================================================================
# Helper Functions
# =============================================================================

def get_task_type(type_key: str) -> dict[str, Any] | None:
    """Look up a task type by key. Returns None if not found."""
    return TASK_TYPES.get(type_key)


def list_task_types(category: str | None = None) -> list[dict[str, Any]]:
    """List all task types, optionally filtered by category.

    Returns enriched dicts with `type_key` added.
    """
    result = []
    for key, definition in TASK_TYPES.items():
        if category and definition["category"] != category:
            continue
        result.append({"type_key": key, **definition})
    # Sort by category order, then by display_name
    cat_order = {k: v["order"] for k, v in TASK_TYPE_CATEGORIES.items()}
    result.sort(key=lambda t: (cat_order.get(t["category"], 99), t["display_name"]))
    return result


def list_categories() -> list[dict[str, Any]]:
    """List task type categories in display order."""
    return [
        {"key": k, **v}
        for k, v in sorted(TASK_TYPE_CATEGORIES.items(), key=lambda x: x[1]["order"])
    ]


def get_process_agent_types(type_key: str) -> list[str]:
    """Return ordered list of agent types needed for a task type's process."""
    task_type = TASK_TYPES.get(type_key)
    if not task_type:
        return []
    return [step["agent_type"] for step in task_type["process"]]



def validate_process(type_key: str) -> list[str]:
    """Validate that all agent types in the process exist in AGENT_TYPES.

    Returns list of error messages (empty = valid).
    """
    task_type = TASK_TYPES.get(type_key)
    if not task_type:
        return [f"Unknown task type: {type_key}"]

    errors = []
    for i, step in enumerate(task_type["process"]):
        agent_type = step["agent_type"]
        if agent_type not in AGENT_TYPES:
            errors.append(f"Step {i+1} ({step['step']}): unknown agent type '{agent_type}'")
    return errors



def resolve_process_agents(
    type_key: str,
    agents: list[dict],
) -> list[dict[str, Any]] | None:
    """Resolve process steps to actual agents from the user's roster.

    Args:
        type_key: Task type key
        agents: User's agent roster (list of agent dicts with 'role' and 'slug')

    Returns:
        List of resolved steps with agent info, or None if type not found.
        Each step: {agent_type, step, instruction, agent_slug, agent_title}
        If an agent type isn't in the roster, agent_slug/agent_title are None (graceful degradation).
    """
    task_type = TASK_TYPES.get(type_key)
    if not task_type:
        return None

    # Build lookup: role → first matching agent
    role_to_agent: dict[str, dict] = {}
    for agent in agents:
        role = agent.get("role")
        if role and role not in role_to_agent:
            role_to_agent[role] = agent

    resolved = []
    for step in task_type["process"]:
        agent = role_to_agent.get(step["agent_type"])
        resolved.append({
            "agent_type": step["agent_type"],
            "step": step["step"],
            "instruction": step["instruction"],
            "agent_slug": agent.get("slug") if agent else None,
            "agent_title": agent.get("title") if agent else None,
        })
    return resolved



def build_task_md_from_type(
    type_key: str,
    title: str,
    slug: str,
    focus: str | None = None,
    schedule: str | None = None,
    delivery: str | None = None,
    agent_slugs: list[str] | None = None,
) -> str | None:
    """Build TASK.md content from a task type definition.

    Args:
        type_key: Registry key
        title: User-provided or default title
        slug: Task slug
        focus: Optional focus/topic to customize the objective
        schedule: Override schedule (or use default from registry)
        delivery: Delivery target (email address or None)
        agent_slugs: Resolved agent slugs for the pipeline

    Returns:
        TASK.md markdown string, or None if type not found.
    """
    task_type = TASK_TYPES.get(type_key)
    if not task_type:
        return None

    effective_schedule = schedule or task_type["default_schedule"]
    objective = task_type["default_objective"]

    # If user provided a focus, customize the objective
    deliverable_text = objective["deliverable"]
    purpose_text = objective["purpose"]
    if focus:
        deliverable_text = f"{deliverable_text} — {focus}"
        purpose_text = f"{purpose_text} (focus: {focus})"

    # Build process section
    process_lines = []
    for i, step in enumerate(task_type["process"]):
        agent_label = agent_slugs[i] if agent_slugs and i < len(agent_slugs) else step["agent_type"]
        process_lines.append(f"{i+1}. **{step['step'].title()}** ({agent_label}): {step['instruction']}")

    # ADR-152: Serialize all runtime config into TASK.md (not read from registry)
    context_reads = task_type.get("context_reads", [])
    context_writes = task_type.get("context_writes", [])
    output_category = task_type.get("output_category", "")

    md = f"""# {title}

**Slug:** {slug}
**Type:** {type_key}
**Schedule:** {effective_schedule}
**Delivery:** {delivery or 'none'}
**Context Reads:** {', '.join(context_reads) if context_reads else 'none'}
**Context Writes:** {', '.join(context_writes) if context_writes else 'none'}
**Output Category:** {output_category or 'none'}

## Objective
- **Deliverable:** {deliverable_text}
- **Audience:** {objective['audience']}
- **Purpose:** {purpose_text}
- **Format:** {objective['format']}

## Process
{chr(10).join(process_lines)}

## Output Spec
- Executive summary
- Key findings with evidence
- Visual assets where applicable
- Sources and references
"""
    return md


def build_deliverable_md_from_type(
    type_key: str,
    audience_override: str | None = None,
) -> str | None:
    """Build DELIVERABLE.md content from a task type's default_deliverable spec.

    ADR-149: DELIVERABLE.md is the quality contract — scaffolded from registry,
    evolves through feedback inference.

    Returns markdown string, or None if type not found or has no deliverable spec.
    """
    task_type = TASK_TYPES.get(type_key)
    if not task_type:
        return None

    deliverable = task_type.get("default_deliverable")
    if not deliverable:
        return None

    objective = task_type.get("default_objective", {})
    output = deliverable.get("output", {})
    assets = deliverable.get("assets", [])
    criteria = deliverable.get("quality_criteria", [])

    # Build Expected Output section
    layout_str = " → ".join(output.get("layout", []))
    output_section = (
        f"## Expected Output\n"
        f"- Format: {output.get('format', 'html').upper()} document, {output.get('word_count', '1000-2000')} words\n"
        f"- Layout: {layout_str}\n"
    )

    # Build Expected Assets section
    if assets:
        asset_lines = []
        for asset in assets:
            desc = asset.get("description", "")
            asset_type = asset.get("type", "chart")
            subtype = asset.get("subtype", "")
            min_count = asset.get("min_count", 1)
            asset_lines.append(f"- {subtype.title()} {asset_type}: at least {min_count} — {desc}")
        assets_section = "## Expected Assets\n" + "\n".join(asset_lines) + "\n"
    else:
        assets_section = "## Expected Assets\n- Text-focused deliverable — visual assets optional where data supports\n"

    # Build Quality Criteria section
    criteria_lines = [f"- {c}" for c in criteria]
    criteria_section = "## Quality Criteria\n" + "\n".join(criteria_lines) + "\n"

    # Build Audience section
    audience = audience_override or objective.get("audience", "")
    audience_section = f"## Audience\n{audience}\n" if audience else ""

    md = f"""# Deliverable Specification

{output_section}
{assets_section}
{criteria_section}
{audience_section}
## User Preferences (inferred)
<!-- Populated by feedback inference (ADR-149). Empty at creation. -->
"""
    return md

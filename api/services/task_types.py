"""
Task Type Registry — ADR-145 Pre-Meditated Orchestration

Deliverable-first task types. Each type defines:
  - What the user gets (display_name, description, category)
  - How it's produced (process: ordered agent steps)
  - When it runs (default_schedule)
  - What format (output_format, export_options)
  - What context it needs (context_sources, requires_platform)

The registry is the "menu" — onboarding presents these as concrete choices.
Process execution is mechanical: scheduler resolves steps, runs each agent
in sequence, passes output forward as explicit handoff.

Canonical docs:
  - docs/adr/ADR-145-task-type-registry-premeditated-orchestration.md
  - docs/architecture/task-type-orchestration.md
  - docs/features/task-types.md
"""

from __future__ import annotations

from typing import Any, Optional

from services.agent_framework import AGENT_TYPES


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
        "export_options": ["pdf"],
        "process": [
            {
                "agent_type": "research",
                "step": "investigate",
                "instruction": (
                    "Investigate the competitive landscape. Gather evidence from web and platform sources. "
                    "Identify key trends, competitor moves, and market shifts. Include data points and sources."
                ),
            },
            {
                "agent_type": "content",
                "step": "compose",
                "instruction": (
                    "Format the research findings into a branded deliverable. Add charts for key metrics, "
                    "mermaid diagrams for competitive positioning, and clear section structure. "
                    "Include executive summary, key findings, implications, and sources."
                ),
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
    },

    "market-research-report": {
        "display_name": "Market Research Report",
        "description": "Deep-dive investigation on a specific topic with data-backed analysis and trend visualizations.",
        "category": "intelligence",
        "default_schedule": "monthly",
        "output_format": "html",
        "export_options": ["pdf"],
        "process": [
            {
                "agent_type": "research",
                "step": "investigate",
                "instruction": (
                    "Conduct deep investigation on the assigned topic. Gather data from web, academic, "
                    "and industry sources. Map the landscape, identify key players, and quantify trends."
                ),
            },
            {
                "agent_type": "content",
                "step": "compose",
                "instruction": (
                    "Transform research into a comprehensive report with professional layout. "
                    "Add market map diagrams, trend charts, comparison tables, and visual assets. "
                    "Structure as: overview, landscape, analysis, key players, recommendations."
                ),
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
    },

    "industry-signal-monitor": {
        "display_name": "Industry Signal Monitor",
        "description": "Surface-level industry scan with deep-dives on signals that matter.",
        "category": "intelligence",
        "default_schedule": "weekly",
        "output_format": "html",
        "export_options": [],
        "process": [
            {
                "agent_type": "marketing",
                "step": "scan",
                "instruction": (
                    "Scan the web and connected platforms for industry signals. Look for: competitor "
                    "announcements, pricing changes, product launches, hiring patterns, market shifts. "
                    "Flag the 3-5 most significant signals with brief context on why they matter."
                ),
            },
            {
                "agent_type": "research",
                "step": "investigate",
                "instruction": (
                    "Take the flagged signals and investigate the most significant ones in depth. "
                    "Validate claims, gather additional context, assess impact. "
                    "For each signal: what happened, what it means, what to do about it."
                ),
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
    },

    "due-diligence-summary": {
        "display_name": "Due Diligence Summary",
        "description": "Structured investigation of a company, market, or opportunity with risk flags and evidence.",
        "category": "intelligence",
        "default_schedule": "on-demand",
        "output_format": "html",
        "export_options": ["pdf"],
        "process": [
            {
                "agent_type": "research",
                "step": "investigate",
                "instruction": (
                    "Investigate the subject thoroughly. Gather evidence on: organizational structure, "
                    "financial indicators, market position, partnerships, risks, recent news. "
                    "Note both positive signals and red flags with evidence."
                ),
            },
            {
                "agent_type": "content",
                "step": "compose",
                "instruction": (
                    "Format findings into a structured due diligence report. Include org chart diagram, "
                    "risk assessment matrix, financial summary table, and evidence-linked conclusions. "
                    "Clear structure: overview, org, financials, risks, market position, recommendation."
                ),
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
    },

    # ── Business Operations ──

    "meeting-prep-brief": {
        "display_name": "Meeting Prep Brief",
        "description": "Relationship context from your platforms combined with fresh external research on attendees.",
        "category": "operations",
        "default_schedule": "on-demand",
        "output_format": "html",
        "export_options": [],
        "process": [
            {
                "agent_type": "crm",
                "step": "gather-context",
                "instruction": (
                    "Review all interaction history with this contact/company across connected platforms. "
                    "Surface: relationship timeline, last interaction summary, open items, promises made, "
                    "sentiment patterns. Note anything unresolved or time-sensitive."
                ),
            },
            {
                "agent_type": "research",
                "step": "investigate",
                "instruction": (
                    "Research the attendee's company: recent news, product launches, leadership changes, "
                    "funding events. Find talking points that show preparation. "
                    "Combine with the relationship context from the prior step to suggest agenda and talking points."
                ),
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
    },

    "stakeholder-update": {
        "display_name": "Stakeholder / Board Update",
        "description": "Executive-quality update with KPI dashboards, metric cards, and narrative context.",
        "category": "operations",
        "default_schedule": "monthly",
        "output_format": "html",
        "export_options": ["pdf", "pptx"],
        "process": [
            {
                "agent_type": "research",
                "step": "gather-data",
                "instruction": (
                    "Gather metrics, data points, and context for the stakeholder update. "
                    "Pull from workspace knowledge, platform discussions, and web sources. "
                    "Organize findings by: key metrics, achievements, challenges, and forward look."
                ),
            },
            {
                "agent_type": "content",
                "step": "compose",
                "instruction": (
                    "Compose an executive-quality update with dashboard layout. Include: "
                    "KPI metric cards with trend indicators, revenue/growth charts, "
                    "achievement highlights, challenge mitigations, and next-period priorities. "
                    "Use professional tone appropriate for board or leadership consumption."
                ),
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
    },

    "relationship-health-digest": {
        "display_name": "Relationship Health Digest",
        "description": "Interaction patterns from Slack synthesized into actionable relationship intelligence.",
        "category": "operations",
        "default_schedule": "weekly",
        "output_format": "html",
        "export_options": [],
        "process": [
            {
                "agent_type": "slack_bot",
                "step": "extract",
                "instruction": (
                    "Extract interaction patterns across Slack channels. For key contacts and teams: "
                    "frequency of interaction, response times, thread engagement, sentiment indicators. "
                    "Flag: cooling relationships, unanswered threads, overdue follow-ups."
                ),
            },
            {
                "agent_type": "crm",
                "step": "synthesize",
                "instruction": (
                    "Synthesize the interaction patterns into a relationship health report. "
                    "Categorize relationships as: active, cooling, at-risk. "
                    "Recommend follow-ups with specific talking points. "
                    "Highlight unanswered commitments and time-sensitive items."
                ),
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
    },

    "project-status-report": {
        "display_name": "Project Status Report",
        "description": "Cross-platform status synthesis — team activity, stakeholder expectations, polished report.",
        "category": "operations",
        "default_schedule": "weekly",
        "output_format": "html",
        "export_options": ["pdf"],
        "process": [
            {
                "agent_type": "slack_bot",
                "step": "extract-activity",
                "instruction": (
                    "Extract team activity signals from Slack: progress updates, blockers mentioned, "
                    "decisions made, action items assigned, deadlines discussed. "
                    "Organize by project or workstream if identifiable."
                ),
            },
            {
                "agent_type": "crm",
                "step": "add-stakeholder-context",
                "instruction": (
                    "Add stakeholder context: commitments made to clients or partners, "
                    "expectations from leadership, external deadlines. Cross-reference with "
                    "the team activity from the prior step to identify gaps or misalignments."
                ),
            },
            {
                "agent_type": "content",
                "step": "compose",
                "instruction": (
                    "Compose a polished project status report. Structure: status overview "
                    "(on track / at risk / blocked), team activity highlights, stakeholder commitments, "
                    "blockers and escalations, next week priorities. Professional formatting."
                ),
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
    },

    # ── Platform Digests ──

    "slack-recap": {
        "display_name": "Slack Recap",
        "description": "Decisions, action items, key discussions, and FYIs from your Slack channels.",
        "category": "platform",
        "default_schedule": "daily",
        "output_format": "html",
        "export_options": [],
        "process": [
            {
                "agent_type": "slack_bot",
                "step": "recap",
                "instruction": (
                    "Produce a comprehensive recap of Slack activity. Include: decisions made (with attribution), "
                    "action items (owner + deadline), key discussions (summarized with thread context), "
                    "and FYIs (announcements, shared documents). Preserve attribution — say who said what."
                ),
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
    },

    "notion-sync-report": {
        "display_name": "Notion Sync Report",
        "description": "What changed in your Notion workspace — updates, staleness flags, and structure suggestions.",
        "category": "platform",
        "default_schedule": "weekly",
        "output_format": "html",
        "export_options": [],
        "process": [
            {
                "agent_type": "notion_bot",
                "step": "sync-report",
                "instruction": (
                    "Produce a sync report of Notion workspace activity. Include: pages created, "
                    "pages updated (highlight meaningful edits vs formatting), staleness flags "
                    "(pages not updated in >30 days), and structure suggestions. "
                    "Use Notion-native terminology and formatting conventions."
                ),
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
    },

    # ── Content & Communications ──

    "content-brief": {
        "display_name": "Content Brief / Blog Draft",
        "description": "Research-backed content with competitive landscape context and visual assets.",
        "category": "content",
        "default_schedule": "on-demand",
        "output_format": "html",
        "export_options": ["pdf"],
        "process": [
            {
                "agent_type": "research",
                "step": "investigate",
                "instruction": (
                    "Research the content topic: competitive landscape, existing content in the space, "
                    "data points and statistics, expert opinions. Identify unique angles and "
                    "evidence that would make the content authoritative."
                ),
            },
            {
                "agent_type": "content",
                "step": "compose",
                "instruction": (
                    "Write a content brief or full blog draft using the research findings. "
                    "Include embedded charts for data visualization, competitive positioning diagrams, "
                    "and brand-consistent styling. Structure for readability and shareability."
                ),
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
    },

    "launch-material": {
        "display_name": "Launch / Announcement Material",
        "description": "GTM intelligence transformed into polished launch material with competitive positioning.",
        "category": "content",
        "default_schedule": "on-demand",
        "output_format": "html",
        "export_options": ["pdf", "pptx"],
        "process": [
            {
                "agent_type": "marketing",
                "step": "position",
                "instruction": (
                    "Develop competitive positioning for this launch. Analyze: market context, "
                    "competitive landscape, timing rationale, differentiation points. "
                    "Produce key messages segmented by audience."
                ),
            },
            {
                "agent_type": "content",
                "step": "compose",
                "instruction": (
                    "Transform the positioning into polished launch material. Create: "
                    "positioning statement, key messages by audience, competitive differentiation "
                    "visuals, and formatted announcement. Use presentation layout for slide-ready output."
                ),
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
    },

    # ── Data & Tracking ──

    "gtm-tracker": {
        "display_name": "GTM Tracker",
        "description": "Competitive moves, market signals, and feature matrices — intelligence with visual tracking.",
        "category": "tracking",
        "default_schedule": "weekly",
        "output_format": "html",
        "export_options": [],
        "process": [
            {
                "agent_type": "marketing",
                "step": "gather-intelligence",
                "instruction": (
                    "Gather go-to-market intelligence: competitor product moves, pricing changes, "
                    "marketing campaigns, channel strategies, hiring signals. "
                    "Produce structured data: feature comparison matrix, signal log, opportunity list."
                ),
            },
            {
                "agent_type": "content",
                "step": "compose",
                "instruction": (
                    "Format the GTM intelligence into a dashboard-style tracker. Include: "
                    "competitive feature matrix table, market signal cards, trend charts, "
                    "and opportunity windows. Use dashboard layout for at-a-glance consumption."
                ),
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


# Backwards-compat alias — callers may still reference the old name
get_pipeline_agent_types = get_process_agent_types


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


# Backwards-compat alias
validate_pipeline = validate_process


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


# Backwards-compat alias
resolve_pipeline_agents = resolve_process_agents


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

    md = f"""# {title}

**Slug:** {slug}
**Type:** {type_key}
**Schedule:** {effective_schedule}
**Delivery:** {delivery or 'none'}

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

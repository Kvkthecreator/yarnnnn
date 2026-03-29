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
        "layout_mode": "document",
        "export_options": ["pdf"],
        "process": [
            {
                "agent_type": "research",
                "step": "investigate",
                "instruction": (
                    "Investigate the competitive landscape using web search and platform context. "
                    "Minimum 3 competitors covered. For each: recent moves (product, pricing, hiring, funding), "
                    "strategic positioning, and threat/opportunity assessment. "
                    "Every claim needs an inline source citation in this format: "
                    "'Revenue grew 23% (source: Q4 2025 earnings call)' or "
                    "'Launched enterprise tier in January (source: company blog, 2025-01-15)'. "
                    "Prefer sources <90 days old. Cross-reference — single-source claims are signals, not findings. "
                    "Structure output as: landscape overview, per-competitor analysis, emerging patterns. "
                    "Be thorough — minimum 500 words. The next agent depends entirely on your research."
                ),
            },
            {
                "agent_type": "content",
                "step": "compose",
                "instruction": (
                    "Transform the research into a polished competitive intelligence brief. "
                    "Use these exact markdown headers in this order:\n"
                    "## Executive Summary\n(3 sentences — the insight, not the process)\n"
                    "## Key Findings\n(numbered list, each finding has inline evidence: 'Revenue grew 23% (source: Q4 filing)')\n"
                    "## Competitive Positioning\n(mermaid quadrant or comparison diagram)\n"
                    "## Trend Analysis\n(chart for any quantified trend data from the research)\n"
                    "## Implications\n(what this means for our strategy — actionable, not observational)\n"
                    "## Sources\n(list all sources cited above)\n\n"
                    "Your output must be LONGER than the research input — you are adding structure, "
                    "visuals, and interpretation, not condensing. Minimum 500 words."
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
        "layout_mode": "document",
        "export_options": ["pdf"],
        "process": [
            {
                "agent_type": "research",
                "step": "investigate",
                "instruction": (
                    "Conduct deep investigation on the assigned topic. Use web search + workspace knowledge. "
                    "Cover: market size/growth, key players (top 5-10), technology trends, regulatory environment, "
                    "and demand drivers. Quantify where possible (%, $, growth rates). "
                    "Source hierarchy: primary (reports, filings) > secondary (articles, analyses). "
                    "Prefer data <12 months old. Flag conflicting data points explicitly. "
                    "Structure: landscape overview, market dynamics, key players, trends, data tables."
                ),
            },
            {
                "agent_type": "content",
                "step": "compose",
                "instruction": (
                    "Transform research into a comprehensive market report. "
                    "Required sections: Executive Summary (conclusion first), Market Overview (size + growth chart), "
                    "Competitive Landscape (mermaid positioning map + player comparison table), "
                    "Trend Analysis (trend charts with interpretation), Opportunities & Risks, Recommendations. "
                    "Every data-heavy section gets a chart or table. "
                    "Lead with insights, support with data — not the reverse."
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
        "layout_mode": "document",
        "export_options": [],
        "process": [
            {
                "agent_type": "marketing",
                "step": "scan",
                "instruction": (
                    "Scan web and connected platforms for industry signals this cycle. "
                    "Signal types (priority order): pricing changes > product launches > funding rounds > "
                    "leadership changes > hiring patterns > partnership announcements. "
                    "For each signal: who, what, when, and a 1-sentence 'so what' assessment. "
                    "Flag the 3-5 most significant. Drop noise — not everything is worth reporting."
                ),
            },
            {
                "agent_type": "research",
                "step": "deep-dive",
                "instruction": (
                    "Take the top 2-3 flagged signals and investigate in depth. For each: "
                    "validate the claim with a second source, gather additional context, "
                    "assess strategic impact (high/medium/low with reasoning), "
                    "and recommend a specific response ('watch', 'adapt', 'act now'). "
                    "Structure per signal: What happened → Why it matters → What to do."
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
        "layout_mode": "document",
        "export_options": ["pdf"],
        "process": [
            {
                "agent_type": "research",
                "step": "investigate",
                "instruction": (
                    "Investigate the subject across 6 dimensions: (1) Organization — leadership, team size, "
                    "structure, key hires/departures; (2) Financials — revenue indicators, funding, burn signals; "
                    "(3) Market position — share, growth trajectory, competitive standing; "
                    "(4) Product — maturity, differentiation, customer evidence; "
                    "(5) Partnerships — ecosystem, strategic relationships; "
                    "(6) Risks — regulatory, competitive, execution, market timing. "
                    "For each dimension: evidence-linked findings, both positive signals and red flags. "
                    "Use web search aggressively — filings, press, LinkedIn, Crunchbase, industry reports."
                ),
            },
            {
                "agent_type": "content",
                "step": "compose",
                "instruction": (
                    "Format into a structured due diligence report. Required elements: "
                    "Executive Summary (go/no-go signal in first sentence), "
                    "Organization (mermaid org chart if data available), "
                    "Financial Summary (table with available metrics), "
                    "Risk Assessment (table: risk, severity, evidence, mitigation), "
                    "Market Position (competitive positioning diagram), "
                    "Recommendation (specific, with conditions). "
                    "Every risk needs evidence. Every positive signal needs evidence. No unsubstantiated claims."
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
        "layout_mode": "document",
        "export_options": [],
        "process": [
            {
                "agent_type": "crm",
                "step": "gather-context",
                "instruction": (
                    "Review interaction history with this contact/company across connected platforms. "
                    "Produce: (1) Relationship timeline — key milestones, (2) Last interaction — date, "
                    "topic, outcome, (3) Open items — promises made by either side with dates, "
                    "(4) Sentiment — trending positive/neutral/cooling based on response patterns. "
                    "Flag anything unresolved or overdue. Be specific — 'discussed pricing on March 12' not 'recent discussion'."
                ),
            },
            {
                "agent_type": "research",
                "step": "investigate",
                "instruction": (
                    "Research the attendee and their company: last 30 days of news, product announcements, "
                    "leadership changes, funding, earnings. Identify 3-5 specific talking points that demonstrate "
                    "preparation (reference their recent news, not generic industry trends). "
                    "Combine with relationship context from prior step to produce: "
                    "suggested agenda (3-5 items, prioritized), talking points per agenda item, "
                    "things to avoid (sensitive topics from prior interactions)."
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
        "layout_mode": "dashboard",
        "export_options": ["pdf", "pptx"],
        "process": [
            {
                "agent_type": "research",
                "step": "gather-data",
                "instruction": (
                    "Gather metrics and context for the stakeholder update from workspace, platforms, and web. "
                    "Organize into 4 buckets: (1) Key Metrics — quantified KPIs with period-over-period change, "
                    "(2) Achievements — what shipped, closed, or completed this period, "
                    "(3) Challenges — blockers, risks, things behind schedule with root cause, "
                    "(4) Forward Look — next period priorities, upcoming milestones, decisions needed. "
                    "Quantify everything possible. 'Revenue grew 23%' not 'revenue grew significantly'."
                ),
            },
            {
                "agent_type": "content",
                "step": "compose",
                "instruction": (
                    "Compose an executive-quality stakeholder update using these exact sections:\n"
                    "## Key Metrics\n(table or card format: metric name, current value, change vs prior period)\n"
                    "## Achievements\n(what shipped, closed, or completed — bulleted, max 5 items)\n"
                    "## Challenges\n(blockers, risks, things behind schedule — each with owner and mitigation)\n"
                    "## Forward Look\n(next period priorities, upcoming milestones, decisions needed)\n\n"
                    "Charts for any metric with trend data. Executive tone: lead with impact, "
                    "support with data, end with asks. "
                    "Your output must be LONGER than the research input — you are adding structure "
                    "and visual presentation. Minimum 400 words."
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
        "layout_mode": "document",
        "export_options": [],
        "process": [
            {
                "agent_type": "slack_bot",
                "step": "extract",
                "instruction": (
                    "Extract interaction patterns from Slack for the past 7 days. For each key contact/team: "
                    "message count, avg response time, thread depth, reaction patterns. "
                    "Identify: (1) relationships going quiet (no interaction in >14 days), "
                    "(2) unanswered threads (question asked, no reply >48h), "
                    "(3) commitments made ('I'll send', 'will follow up') without follow-through. "
                    "Output as structured data: contact, last interaction date, frequency trend, flags."
                ),
            },
            {
                "agent_type": "crm",
                "step": "synthesize",
                "instruction": (
                    "Synthesize interaction patterns into a relationship health report. "
                    "Categorize each relationship: Active (regular engagement), Cooling (declining frequency), "
                    "At-Risk (going quiet + open commitments). "
                    "For each at-risk/cooling relationship: specific follow-up recommendation with talking point "
                    "('Reach out to Alice about the Q4 proposal you discussed March 15'). "
                    "End with: top 3 follow-ups this week, ranked by urgency."
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
        "layout_mode": "document",
        "export_options": ["pdf"],
        "process": [
            {
                "agent_type": "slack_bot",
                "step": "extract-activity",
                "instruction": (
                    "Extract team activity from Slack for the past 7 days. Capture: "
                    "(1) Progress updates — what moved forward, with attribution, "
                    "(2) Blockers — what's stuck and why, who raised it, "
                    "(3) Decisions — what was decided, by whom, in which thread, "
                    "(4) Action items — who owes what, with deadlines if mentioned. "
                    "Group by project/workstream when identifiable. Skip routine standups and bot noise."
                ),
            },
            {
                "agent_type": "crm",
                "step": "add-stakeholder-context",
                "instruction": (
                    "Add stakeholder context to the team activity. Surface: "
                    "commitments to external parties (clients, partners, investors) with dates, "
                    "expectations from leadership, external deadlines approaching. "
                    "Cross-reference with team activity: flag gaps (commitment made but no progress signal), "
                    "misalignments (team working on X but stakeholder expects Y), overdue items."
                ),
            },
            {
                "agent_type": "content",
                "step": "compose",
                "instruction": (
                    "Compose a polished project status report. "
                    "Open with: overall status (On Track / At Risk / Blocked) with 1-sentence rationale. "
                    "Then: Progress Highlights (what shipped/completed), Blockers & Risks (with owners), "
                    "Stakeholder Commitments (status of each), Next Week Priorities (top 3-5). "
                    "Keep total length under 1 page equivalent. Every item has an owner name."
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
        "layout_mode": "document",
        "export_options": [],
        "process": [
            {
                "agent_type": "slack_bot",
                "step": "recap",
                "instruction": (
                    "Produce a structured recap of Slack activity since the last run. "
                    "Four sections, in this order: "
                    "(1) Decisions Made — what was decided, by whom, link to thread context; "
                    "(2) Action Items — owner, task, deadline if mentioned; "
                    "(3) Key Discussions — threads with significant engagement (>3 replies), "
                    "summarize the conclusion not every reply; "
                    "(4) FYIs — announcements, shared links, things to be aware of. "
                    "Attribution is mandatory — 'Alice proposed X' not 'it was proposed'. "
                    "Skip: bot messages, emoji-only reactions, routine standup entries. "
                    "Highlight: questions left unanswered, disagreements unresolved."
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
        "layout_mode": "document",
        "export_options": [],
        "process": [
            {
                "agent_type": "notion_bot",
                "step": "sync-report",
                "instruction": (
                    "Produce a Notion workspace sync report for the past 7 days. "
                    "Three sections: (1) Changes — pages created or meaningfully updated "
                    "(distinguish content edits from formatting-only changes), with summary of what changed; "
                    "(2) Staleness Flags — pages not updated in >30 days that likely need attention "
                    "(skip archived/reference pages); "
                    "(3) Health Notes — orphaned pages (no backlinks), duplicate content, "
                    "structural suggestions if hierarchy is getting messy."
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
        "layout_mode": "document",
        "export_options": ["pdf"],
        "process": [
            {
                "agent_type": "research",
                "step": "investigate",
                "instruction": (
                    "Research the content topic for authoritative source material. Cover: "
                    "what's already published on this topic (gaps in existing coverage), "
                    "data points and statistics (with sources and dates), "
                    "expert perspectives and contrarian takes, "
                    "competitive landscape (who's writing about this, what angle they take). "
                    "Identify 2-3 unique angles not already covered in existing content."
                ),
            },
            {
                "agent_type": "content",
                "step": "compose",
                "instruction": (
                    "Write a full content draft (blog post / article) using the research. "
                    "Structure: compelling hook (not 'In today's fast-paced world'), "
                    "thesis statement, evidence-backed sections (3-5), actionable conclusion. "
                    "Embed charts where data supports the narrative. "
                    "Include competitive positioning diagram if comparing approaches. "
                    "Target 1000-1500 words. Write in the user's brand voice (see Brand context). "
                    "Every claim backed by research from the prior step."
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
        "layout_mode": "presentation",
        "export_options": ["pdf", "pptx"],
        "process": [
            {
                "agent_type": "marketing",
                "step": "position",
                "instruction": (
                    "Develop competitive positioning for this launch. Produce: "
                    "(1) Market context — what's happening that makes this timely, "
                    "(2) Competitive landscape — who else does this, how we differ (feature matrix), "
                    "(3) Positioning statement — for [audience], [product] is the [category] that [differentiator], "
                    "(4) Key messages — 3 messages per audience segment (customers, press, internal), "
                    "(5) Objection handling — top 3 anticipated objections with responses."
                ),
            },
            {
                "agent_type": "content",
                "step": "compose",
                "instruction": (
                    "Transform positioning into presentation-ready launch material. "
                    "Structure as slides: Title + tagline, The Problem, Our Solution, How It Works, "
                    "Competitive Differentiation (mermaid positioning diagram), Key Messages by Audience, "
                    "Social/PR quotes (ready to copy), Next Steps. "
                    "1 idea per slide, 3 bullets max per slide. "
                    "Slide titles are assertions ('We're the only X that does Y'), not topics ('Our Solution'). "
                    "Include competitive feature matrix table."
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
        "layout_mode": "dashboard",
        "export_options": [],
        "process": [
            {
                "agent_type": "marketing",
                "step": "gather-intelligence",
                "instruction": (
                    "Gather go-to-market intelligence for this cycle. Produce structured data: "
                    "(1) Feature Matrix — rows=features, columns=competitors, cells=shipped/building/missing/n-a, "
                    "(2) Signal Log — what each competitor did this period (date, action, significance), "
                    "(3) Pricing Intel — any pricing changes detected with before/after if available, "
                    "(4) Opportunity List — gaps where we have advantage or competitors are weak. "
                    "Quantify signals: 'launched 3 features' not 'active development'. "
                    "Note what changed vs. last cycle."
                ),
            },
            {
                "agent_type": "content",
                "step": "compose",
                "instruction": (
                    "Format into a dashboard-style GTM tracker for at-a-glance consumption. "
                    "Top section: signal count cards (new features, pricing changes, hires). "
                    "Then: competitive feature matrix (markdown table, color-hint in cell text), "
                    "signal timeline (most recent first), opportunity windows (ranked by urgency). "
                    "Charts for any trends with multi-cycle data. "
                    "Dashboard layout — dense, scannable, no long paragraphs."
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

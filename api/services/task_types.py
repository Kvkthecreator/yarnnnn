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
                "step": "update-context",
                "instruction": (
                    "Read the existing context files in /workspace/context/competitors/. These contain accumulated "
                    "competitive intelligence from prior cycles. Research new signals via web search "
                    "and platform context — cover minimum 3 competitors. For each: recent moves "
                    "(product, pricing, hiring, funding), strategic positioning, threat/opportunity. "
                    "Prefer sources <90 days old. Cross-reference — single-source claims are signals, not findings.\n\n"
                    "UPDATE the per-competitor files with new findings — add dated entries to Recent Signals, "
                    "update Strategic Assessment if your view has changed. Create new competitor files for "
                    "newly discovered competitors. Update /workspace/context/competitors/landscape.md with cross-competitor "
                    "pattern changes.\n\n"
                    "Your output for this step: a CHANGELOG of what you added, updated, or discovered this cycle."
                ),
            },
            {
                "agent_type": "content",
                "step": "derive-output",
                "instruction": (
                    "Read ALL context files in /workspace/context/competitors/. Produce the deliverable as specified in "
                    "DELIVERABLE.md. This is a DERIVATIVE of accumulated context — emphasize what CHANGED "
                    "since last cycle. The reader has seen prior reports; lead with what's new and what it means. "
                    "Reference persistent competitor profiles where they exist.\n\n"
                    "Structure: What's New → What Changed → What It Means → Standing Context (brief).\n\n"
                    "Use charts and mermaid diagrams where data supports visual communication. "
                    "Every claim needs an inline source citation. Target: 2000-3000 words."
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
                "instruction": (
                    "Read the existing context files in /workspace/context/market/. These contain accumulated "
                    "market intelligence from prior cycles. Research new data via web search and "
                    "platform context — cover market size/growth, key players (top 5-10), technology "
                    "trends, regulatory environment, demand drivers. Quantify (%, $, growth rates). "
                    "Primary sources (reports, filings) > secondary (articles). Data <12 months preferred.\n\n"
                    "UPDATE the per-segment files with new findings — add dated entries, update "
                    "assessments if data has shifted. Create new segment files for newly identified "
                    "segments. Update /workspace/context/market/market-overview.md with cross-segment pattern changes.\n\n"
                    "Your output for this step: a CHANGELOG of what you added, updated, or discovered this cycle."
                ),
            },
            {
                "agent_type": "content",
                "step": "derive-output",
                "instruction": (
                    "Read ALL context files in /workspace/context/market/. Produce the deliverable as specified in "
                    "DELIVERABLE.md. This is a DERIVATIVE of accumulated context — emphasize what CHANGED "
                    "since last cycle. The reader has seen prior reports; lead with what's new and what it means. "
                    "Reference persistent market segment profiles where they exist.\n\n"
                    "Structure: What's New → What Changed → What It Means → Standing Context (brief).\n\n"
                    "Every data-heavy section gets a chart or table. "
                    "Lead with insights, support with data. Target: 2500-4000 words."
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
                "instruction": (
                    "Read existing context files in /workspace/context/signals/ (patterns, signal history). "
                    "Gather new signals from web search and platform context. "
                    "Signal types (priority): pricing changes > product launches > funding rounds > "
                    "leadership changes > hiring patterns > partnerships. "
                    "For each signal: who, what, when, 1-sentence 'so what'. Drop noise.\n\n"
                    "Log new signals to /workspace/context/signals/. "
                    "Update /workspace/context/signals/patterns.md if new cross-signal patterns emerge.\n\n"
                    "Produce the deliverable emphasizing what's new since last cycle. "
                    "Deep-dive top 2-3 signals: validate with second source, "
                    "assess strategic impact (high/medium/low with reasoning), "
                    "recommend response ('watch', 'adapt', 'act now').\n\n"
                    "Target: 1500-2500 words. Include timeline or chart if signals show a pattern."
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
                "instruction": (
                    "Read the existing context files in /workspace/context/competitors/ and /workspace/context/market/. "
                    "These contain accumulated diligence findings from prior investigation. Research new data via web search — "
                    "filings, press, LinkedIn, Crunchbase. Investigate across 6 dimensions: "
                    "(1) Organization — leadership, team, key hires/departures; "
                    "(2) Financials — revenue, funding, burn; (3) Market position — share, growth, competition; "
                    "(4) Product — maturity, differentiation, customers; (5) Partnerships — ecosystem, strategy; "
                    "(6) Risks — regulatory, competitive, execution, timing.\n\n"
                    "UPDATE the per-area files with new findings — add dated entries, update risk "
                    "assessments if evidence has changed. Create new area files for newly identified "
                    "diligence areas. Update /workspace/context/competitors/assessment.md with overall risk profile changes.\n\n"
                    "Your output for this step: a CHANGELOG of what you added, updated, or discovered this cycle."
                ),
            },
            {
                "agent_type": "content",
                "step": "derive-output",
                "instruction": (
                    "Read ALL context files in /workspace/context/competitors/ and /workspace/context/market/. "
                    "Produce the deliverable as specified in "
                    "DELIVERABLE.md. This is a DERIVATIVE of accumulated context — emphasize what CHANGED "
                    "since last cycle. The reader has seen prior reports; lead with what's new and what it means. "
                    "Reference persistent diligence area files where they exist.\n\n"
                    "Structure: What's New → What Changed → What It Means → Standing Context (brief).\n\n"
                    "Every claim needs evidence. No unsubstantiated signals. Target: 2500-4000 words."
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
                "instruction": (
                    "Read the existing context files in /workspace/context/relationships/. These contain accumulated "
                    "contact intelligence from prior interactions. Review interaction history with "
                    "this contact/company across connected platforms.\n\n"
                    "UPDATE the contact file with new findings — add dated entries to Past Interactions, "
                    "update Open Items with any new commitments or resolutions, adjust Notes with "
                    "new preferences or sensitivities observed. Create a new contact file if this is "
                    "a first interaction.\n\n"
                    "Your output for this step: a CHANGELOG of what you added, updated, or discovered this cycle."
                ),
            },
            {
                "agent_type": "research",
                "step": "derive-output",
                "instruction": (
                    "Read ALL context files in /workspace/context/relationships/ and /workspace/context/competitors/. "
                    "Research the attendee and their company: "
                    "last 30 days of news, product announcements, leadership changes, funding, earnings. "
                    "Produce the deliverable as specified in DELIVERABLE.md — combine accumulated "
                    "relationship context with fresh external research.\n\n"
                    "Identify 3-5 specific talking points that demonstrate preparation "
                    "(reference their recent news, not generic industry trends). "
                    "Produce: suggested agenda (3-5 items, prioritized), talking points per agenda item, "
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
                "instruction": (
                    "Read the existing context files in /workspace/context/competitors/, /workspace/context/market/, "
                    "/workspace/context/projects/, and /workspace/context/relationships/. These contain accumulated "
                    "workstream intelligence from prior cycles. Gather new data from platforms and "
                    "workspace — pull metrics, achievements, challenges, forward look.\n\n"
                    "UPDATE the per-workstream files with new findings — add dated entries to "
                    "Key Milestones, update Current Status, note new Challenges with owners and "
                    "mitigations. Create new workstream files for newly identified workstreams. "
                    "Update /workspace/context/projects/executive-summary.md with cross-workstream status changes. "
                    "Quantify everything — 'Revenue grew 23%' not 'revenue grew significantly'.\n\n"
                    "Your output for this step: a CHANGELOG of what you added, updated, or discovered this cycle."
                ),
            },
            {
                "agent_type": "content",
                "step": "derive-output",
                "instruction": (
                    "Read ALL context files in /workspace/context/competitors/, /workspace/context/market/, "
                    "/workspace/context/projects/, and /workspace/context/relationships/. "
                    "Produce the deliverable as specified in "
                    "DELIVERABLE.md. This is a DERIVATIVE of accumulated context — emphasize what CHANGED "
                    "since last cycle. The reader has seen prior reports; lead with what's new and what it means. "
                    "Reference persistent workstream profiles where they exist.\n\n"
                    "Structure: What's New → What Changed → What It Means → Standing Context (brief).\n\n"
                    "Include charts for any metric with trend data. "
                    "Executive tone: lead with impact, support with data, end with specific asks. "
                    "Target: 1500-2500 words."
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
                "instruction": (
                    "Read the existing context files in /workspace/context/relationships/. These contain accumulated "
                    "relationship intelligence from prior cycles. Review platform context (especially Slack) "
                    "for the past 7 days — interaction patterns, message frequency, response times, "
                    "thread depth, commitments made.\n\n"
                    "UPDATE the per-relationship files with new findings — add dated entries to "
                    "Engagement History, update Health Indicators with current trends, note new "
                    "Action Items and Risk Flags. Create new relationship files for newly identified "
                    "contacts. Update /workspace/context/relationships/portfolio.md with at-risk relationships and pattern changes.\n\n"
                    "Your output for this step: a CHANGELOG of what you added, updated, or discovered this cycle."
                ),
            },
            {
                "agent_type": "content",
                "step": "derive-output",
                "instruction": (
                    "Read ALL context files in /workspace/context/relationships/. Produce the deliverable as specified in "
                    "DELIVERABLE.md. This is a DERIVATIVE of accumulated context — emphasize what CHANGED "
                    "since last cycle. The reader has seen prior reports; lead with what's new and what it means. "
                    "Reference persistent relationship profiles where they exist.\n\n"
                    "Structure: What's New → What Changed → What It Means → Standing Context (brief).\n\n"
                    "For each at-risk/cooling relationship: specific follow-up recommendation with talking point. "
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
                "instruction": (
                    "Read the existing context files in /workspace/context/projects/. These contain accumulated "
                    "workstream status from prior cycles. Gather new data from platforms (especially "
                    "Slack) and workspace — progress updates, blockers, decisions, action items.\n\n"
                    "UPDATE the per-workstream files with new findings — add dated entries to "
                    "Progress, update Status and Blockers with current state, note new Next Steps. "
                    "Create new workstream files for newly identified workstreams. "
                    "Update /workspace/context/projects/project-health.md with overall status changes and blocker summary.\n\n"
                    "Group by project/workstream when identifiable. Skip routine standups and bot noise.\n\n"
                    "Your output for this step: a CHANGELOG of what you added, updated, or discovered this cycle."
                ),
            },
            {
                "agent_type": "content",
                "step": "derive-output",
                "instruction": (
                    "Read ALL context files in /workspace/context/projects/. Produce the deliverable as specified in "
                    "DELIVERABLE.md. This is a DERIVATIVE of accumulated context — emphasize what CHANGED "
                    "since last cycle. The reader has seen prior reports; lead with what's new and what it means. "
                    "Reference persistent workstream profiles where they exist.\n\n"
                    "Structure: What's New → What Changed → What It Means → Standing Context (brief).\n\n"
                    "Every item has an owner name. Target: 1000-1500 words."
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
                "instruction": (
                    "Read existing context files in /workspace/context/signals/ (patterns, signal history). "
                    "Gather new signals from Slack activity since the last run. "
                    "Log new signals to /workspace/context/signals/.\n\n"
                    "Update /workspace/context/signals/patterns.md if new recurring discussion themes or "
                    "key-people patterns emerge.\n\n"
                    "Produce the deliverable emphasizing what's new since last cycle. "
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
                "instruction": (
                    "Read existing context files in /workspace/context/signals/ (content map, signal history). "
                    "Gather new signals from Notion platform context for the past 7 days. "
                    "Log new signals to /workspace/context/signals/.\n\n"
                    "Update /workspace/context/signals/content-map.md if active areas or stale content patterns "
                    "have changed.\n\n"
                    "Produce the deliverable emphasizing what's new since last cycle. "
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
                "instruction": (
                    "Read the existing context files in /workspace/context/content/. These contain accumulated "
                    "topic research from prior cycles. Research new data via web search — "
                    "what's already published (gaps in coverage), data points with sources, "
                    "expert perspectives, contrarian takes, competitive landscape of content on this topic.\n\n"
                    "UPDATE the per-topic files with new findings — add dated entries to Key Points, "
                    "update Sources with newly found research, note Audience Considerations. "
                    "Create new topic files for newly identified research areas. "
                    "Update /workspace/context/content/brief-outline.md with key message and structure changes.\n\n"
                    "Your output for this step: a CHANGELOG of what you added, updated, or discovered this cycle."
                ),
            },
            {
                "agent_type": "content",
                "step": "derive-output",
                "instruction": (
                    "Read ALL context files in /workspace/context/content/. Produce the deliverable as specified in "
                    "DELIVERABLE.md. This is a DERIVATIVE of accumulated context — emphasize what CHANGED "
                    "since last cycle. Reference persistent topic research where it exists.\n\n"
                    "Write in the user's brand voice (see Brand context). "
                    "Compelling hook (not 'In today's fast-paced world'), thesis statement, "
                    "3-5 evidence-backed sections, actionable conclusion. "
                    "Embed charts where data supports the narrative. "
                    "Every claim backed by research. Target: 1500-2500 words."
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
                "instruction": (
                    "Read the existing context files in /workspace/context/content/, /workspace/context/competitors/, "
                    "and /workspace/context/market/. These contain accumulated "
                    "audience and competitive positioning research. Research new data via web search "
                    "and platform context — competitive landscape, audience profiles, market context, "
                    "feature matrices, positioning opportunities.\n\n"
                    "UPDATE the per-audience files with new findings — add dated entries to "
                    "Key Messages, update Profile and Channels. Create new audience files for "
                    "newly identified segments. Update /workspace/context/content/launch-plan.md with core narrative "
                    "and timeline changes.\n\n"
                    "Your output for this step: a CHANGELOG of what you added, updated, or discovered this cycle."
                ),
            },
            {
                "agent_type": "content",
                "step": "derive-output",
                "instruction": (
                    "Read ALL context files in /workspace/context/content/, /workspace/context/competitors/, "
                    "and /workspace/context/market/. Produce the deliverable as specified in "
                    "DELIVERABLE.md. This is a DERIVATIVE of accumulated context — emphasize what CHANGED "
                    "since last cycle. Reference persistent audience profiles where they exist.\n\n"
                    "OUTPUT as slides (use ## for each slide title). "
                    "1 idea per slide, 3 bullets max. Slide titles are assertions "
                    "('We're the only X that does Y'), not topics. Target: 1500-2000 words."
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
                "instruction": (
                    "Read the existing context files in /workspace/context/competitors/ and /workspace/context/market/. "
                    "These contain accumulated "
                    "GTM intelligence from prior cycles. Research new signals via web search and "
                    "platform context — feature launches, pricing changes, campaigns, hiring patterns.\n\n"
                    "UPDATE the per-competitor files with new findings — add dated entries to "
                    "Recent Moves, update Feature Matrix with newly shipped features, note "
                    "Positioning changes. Create new competitor files for newly discovered competitors. "
                    "Update /workspace/context/competitors/gtm-landscape.md with market pulse and positioning map changes.\n\n"
                    "Your output for this step: a CHANGELOG of what you added, updated, or discovered this cycle."
                ),
            },
            {
                "agent_type": "content",
                "step": "derive-output",
                "instruction": (
                    "Read ALL context files in /workspace/context/competitors/ and /workspace/context/market/. "
                    "Produce the deliverable as specified in "
                    "DELIVERABLE.md. This is a DERIVATIVE of accumulated context — emphasize what CHANGED "
                    "since last cycle. The reader has seen prior reports; lead with what's new and what it means. "
                    "Reference persistent competitor profiles where they exist.\n\n"
                    "Structure: What's New → What Changed → What It Means → Standing Context (brief).\n\n"
                    "Dashboard layout — dense, scannable, no long paragraphs. "
                    "Charts for trends with multi-cycle data. Target: 1500-2500 words."
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

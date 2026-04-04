"""
Task Type Registry — ADR-152 + ADR-154: Atomic Task Types

Two classes of tasks, dead simple:
  CONTEXT tasks — maintain a workspace context domain (track, research, monitor)
  SYNTHESIS tasks — produce outputs from accumulated context (reports, briefs, content)

Users think: "What do I want to track?" → context tasks.
             "What reports do I want?" → synthesis tasks.

Agents are auto-assigned. The task type determines which agent handles it.
Process step instructions come from STEP_INSTRUCTIONS (generic templates).
Per-task-type quality criteria live in DELIVERABLE.md, not here.

Registries are creation-time templates. After task creation, TASK.md is the
sole source of truth — pipeline reads TASK.md, not this registry.

Mode + Bootstrap (ADR-154):
  Each task type declares default_mode (recurring/goal/reactive) and optional
  bootstrap criteria. Bootstrap defines the minimum domain state before a context
  task transitions from aggressive bootstrapping to steady-state cadence.
  Phase (bootstrap/steady/complete) is derived by the pipeline at runtime.

Version: 5.0 (2026-04-04)
Changelog:
  v1.0 — 13 product-named types (ADR-145)
  v2.0 — context_reads/writes, output_category, STEP_INSTRUCTIONS templates (ADR-152)
  v3.0 — Atomic split: 7 context + 8 synthesis types. Task-first, user-friendly naming.
  v4.0 — ADR-154: default_mode + bootstrap criteria on all task types. Phase-aware execution.
  v4.1 — ADR-157: Visual asset guidance in step instructions (favicon fetch + embed).
  v4.2 — ADR-157: assets/ subfolder convention. All visual assets in domain assets/ folder.
  v5.0 — ADR-158: Platform bot ownership. monitor-slack → slack-digest,
         monitor-notion → notion-digest. Platform-specific step instructions.
         context_reads/writes updated to bot-owned directories (slack, notion)
         instead of signals-only. Bots write per-source observation files.

Canonical docs:
  - docs/architecture/registry-matrix.md
  - docs/adr/ADR-154-execution-boundary-reform.md
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
        "These contain accumulated intelligence from prior cycles.\n\n"
        "IMPORTANT: Check your Execution Awareness (injected in context) for a "
        "## Next Cycle Directive. If one exists, it contains your own prior-cycle notes "
        "on what specifically to research, what to skip, and how many tool rounds to use. "
        "FOLLOW IT as your primary guidance — it was written by you while the context was fresh. "
        "Only deviate if something urgent emerged.\n\n"
        "If no directive exists (first run or system-generated focus), research broadly: "
        "web search for new signals, update entity files with findings, "
        "create new entity files for newly discovered items.\n\n"
        "UPDATE entity files with new findings — add dated entries to signal sections, "
        "update assessments if your view has changed. "
        "Update synthesis files with cross-entity pattern changes.\n\n"
        "VISUAL ASSETS: For entity profiles (especially companies/products), include the "
        "entity's website domain in the source metadata comment: "
        "<!-- source: researched | date: YYYY-MM-DD | url: example.com -->. "
        "If a new entity has a known website and no favicon exists yet in the domain's "
        "assets/ folder, fetch one: "
        "RuntimeDispatch(type='fetch-asset', input={url: 'example.com', asset_type: 'favicon', "
        "size: 128, workspace_path: '<context-domain-path>/assets/<entity-slug>-favicon.png'}, "
        "output_format='png'). All visual assets live in the domain's assets/ subfolder.\n\n"
        "Append to the cross-domain signal log with dated entries for this cycle.\n\n"
        "Your output for this step: a CHANGELOG of what you added, updated, or discovered."
    ),

    # ADR-154: Phase-specific override for bootstrap
    "update-context:bootstrap": (
        "You are BOOTSTRAPPING this context domain — it has few or no entity profiles yet.\n\n"
        "YOUR #1 PRIORITY: Create entity files using WriteWorkspace. Text output is secondary.\n\n"
        "REQUIRED STEPS:\n"
        "1. WebSearch to discover key entities in this domain (companies, people, segments, etc.)\n"
        "2. For EACH entity found, call WriteWorkspace with:\n"
        "   - scope='context'\n"
        "   - domain=<your assigned domain>\n"
        "   - path='<entity-slug>/profile.md' (e.g., 'openai/profile.md')\n"
        "   - content: substantive profile with real findings, not placeholder headers\n"
        "   - Include the entity's website in the source comment: "
        "<!-- source: researched | date: YYYY-MM-DD | url: openai.com -->\n"
        "3. Create at least 3 entity profiles. Each must have real content.\n"
        "4. For company/product entities with a known website, fetch their favicon:\n"
        "   RuntimeDispatch(type='fetch-asset', input={url: 'openai.com', asset_type: 'favicon', "
        "size: 128, workspace_path: '<domain>/assets/<entity-slug>-favicon.png'}, output_format='png')\n"
        "5. After entities are created, update the synthesis file (landscape.md) with an overview.\n\n"
        "EXAMPLE WriteWorkspace call:\n"
        "  WriteWorkspace(path='openai/profile.md', content='# OpenAI\\n\\n## Overview\\nOpenAI is...', "
        "scope='context', domain='competitors')\n\n"
        "The Entity Tracker shows how many entities exist. Your goal is to meet the minimum.\n\n"
        "Your text output: a brief CHANGELOG of entities created. The entity FILES are the real deliverable."
    ),

    "derive-output": (
        "Read ALL context files from your assigned context domains. "
        "Produce the deliverable as specified in DELIVERABLE.md. "
        "This is a DERIVATIVE of accumulated context — emphasize what CHANGED "
        "since last cycle. The reader has seen prior outputs; lead with what's new. "
        "Reference persistent assets from context domains where they exist.\n\n"
        "VISUAL ASSETS: Each context domain has an assets/ subfolder containing visual assets "
        "(favicons, charts, diagrams). When referencing companies or products in your output, "
        "check the domain's assets/ folder for {entity-slug}-favicon.png files (with content_url). "
        "Embed them using: <img src=\"{content_url}\" width=\"24\" height=\"24\" alt=\"{name}\">. "
        "This makes reports visually rich. Only use assets that exist — don't generate URLs.\n\n"
        "Structure: What's New → What Changed → What It Means → Standing Context (brief)."
    ),

    "capture-and-report": (
        "Read existing context files (patterns, signal history). "
        "Gather new signals from platform context. Log new signals to the signal domain. "
        "Update pattern synthesis if new cross-signal patterns emerge. "
        "Produce the deliverable emphasizing what's new since last cycle."
    ),

    # ADR-158: Platform-specific digest instructions
    "slack-digest": (
        "You are the Slack Bot. Your job is to read selected Slack channels and "
        "write per-channel observation files to your context domain.\n\n"
        "IMPORTANT: Check your Execution Awareness for a ## Next Cycle Directive. "
        "If one exists, follow it — it was written by you while context was fresh.\n\n"
        "For EACH selected channel:\n"
        "1. Read recent messages using your Slack tools\n"
        "2. Extract: decisions made, action items assigned, key discussions, FYIs\n"
        "3. Write findings to your context domain: WriteWorkspace(scope='context', "
        "domain='slack', path='{channel-slug}/latest.md')\n\n"
        "Summarization rules:\n"
        "- Preserve attribution: 'Alice proposed X' not 'it was proposed'\n"
        "- Threads > individual messages: summarize thread conclusions\n"
        "- Skip: bot messages, emoji-only, routine standup entries\n"
        "- Highlight: unanswered questions, unresolved disagreements\n"
        "- Flag urgency: 'blocked', 'need help', 'ASAP', mentions of the user\n\n"
        "Also append a dated signal entry to /workspace/context/signals/ with "
        "a one-line summary per channel of what was notable.\n\n"
        "Your output: a digest of what happened across all observed channels."
    ),

    "notion-digest": (
        "You are the Notion Bot. Your job is to read selected Notion pages and "
        "write per-page observation files to your context domain.\n\n"
        "IMPORTANT: Check your Execution Awareness for a ## Next Cycle Directive. "
        "If one exists, follow it — it was written by you while context was fresh.\n\n"
        "For EACH selected page/database:\n"
        "1. Read the page using your Notion tools\n"
        "2. Identify: what changed since last observation, new content, stale sections\n"
        "3. Write findings to your context domain: WriteWorkspace(scope='context', "
        "domain='notion', path='{page-slug}/latest.md')\n\n"
        "Change detection rules:\n"
        "- Track meaningful content changes vs formatting-only edits\n"
        "- Flag pages not updated in >30 days (potential staleness)\n"
        "- Note high-frequency edit pages (active collaboration)\n"
        "- Preserve page structure context — what fits where in the hierarchy\n\n"
        "Also append a dated signal entry to /workspace/context/signals/ with "
        "a one-line summary per page of what changed.\n\n"
        "Your output: a change digest across all observed pages."
    ),
}


# =============================================================================
# Task Type Categories
# =============================================================================

TASK_TYPE_CATEGORIES = {
    "context": {"display_name": "Track & Research", "order": 1},
    "synthesis": {"display_name": "Reports & Outputs", "order": 2},
    "platform": {"display_name": "Platform Monitoring", "order": 3},
}


# =============================================================================
# Task Type Registry (v3 — atomic split)
# =============================================================================

TASK_TYPES: dict[str, dict[str, Any]] = {

    # ══════════════════════════════════════════════════════════════════════════
    # CONTEXT TASKS — maintain workspace context domains
    # "What do you want to track?"
    # ══════════════════════════════════════════════════════════════════════════

    "track-competitors": {
        "display_name": "Track Competitors",
        "description": "Research and maintain intelligence on competitors — products, pricing, funding, strategy.",
        "category": "context",
        "task_class": "context",
        "default_mode": "recurring",
        "default_schedule": "weekly",
        "bootstrap": {
            "min_entities": 3,
            "required_files": ["profile"],
        },
        "output_format": "markdown",
        "layout_mode": "document",
        "export_options": [],
        "process": [
            {
                "agent_type": "competitive_intel",
                "step": "update-context",
                "instruction": STEP_INSTRUCTIONS["update-context"],
            },
        ],
        "context_reads": ["competitors"],
        "context_writes": ["competitors", "signals"],
        # ADR-154: output_category removed — tasks own their outputs
        "context_sources": ["web", "platforms", "workspace"],
        "requires_platform": None,
        "default_objective": {
            "deliverable": "Maintained competitor intelligence",
            "audience": "Internal — feeds synthesis tasks",
            "purpose": "Keep competitor profiles current with latest signals",
            "format": "Structured entity files per competitor",
        },
        "default_deliverable": {
            "output": {
                "format": "context",
                "word_count": "n/a",
                "layout": ["Per-entity profiles", "Signals log", "Landscape synthesis"],
            },
            "assets": [],
            "quality_criteria": [
                "Minimum 3 competitor profiles maintained",
                "Each profile updated within last 30 days",
                "Every finding has a source citation",
                "Landscape synthesis reflects latest competitive dynamics",
            ],
        },
    },

    "track-market": {
        "display_name": "Track Market",
        "description": "Research and maintain intelligence on market segments, sizing, trends, and opportunities.",
        "category": "context",
        "task_class": "context",
        "default_mode": "recurring",
        "default_schedule": "monthly",
        "bootstrap": {
            "min_entities": 2,
            "required_files": ["analysis"],
        },
        "output_format": "markdown",
        "layout_mode": "document",
        "export_options": [],
        "process": [
            {
                "agent_type": "market_research",
                "step": "update-context",
                "instruction": STEP_INSTRUCTIONS["update-context"],
            },
        ],
        "context_reads": ["market"],
        "context_writes": ["market", "signals"],
        "context_sources": ["web", "platforms", "workspace"],
        "requires_platform": None,
        "default_objective": {
            "deliverable": "Maintained market intelligence",
            "audience": "Internal — feeds synthesis tasks",
            "purpose": "Keep market segment analyses current",
            "format": "Structured segment files with trends and opportunities",
        },
        "default_deliverable": {
            "output": {"format": "context", "word_count": "n/a", "layout": ["Per-segment analyses", "Market overview synthesis"]},
            "assets": [],
            "quality_criteria": [
                "Key market segments identified and profiled",
                "Trends backed by data with recency noted",
                "Opportunity assessment updated each cycle",
            ],
        },
    },

    "track-relationships": {
        "display_name": "Track Relationships",
        "description": "Maintain contact profiles, interaction history, and relationship health from platform signals.",
        "category": "context",
        "task_class": "context",
        "default_mode": "recurring",
        "default_schedule": "weekly",
        "bootstrap": {
            "min_entities": 3,
            "required_files": ["profile"],
        },
        "output_format": "markdown",
        "layout_mode": "document",
        "export_options": [],
        "process": [
            {
                "agent_type": "business_dev",
                "step": "update-context",
                "instruction": STEP_INSTRUCTIONS["update-context"],
            },
        ],
        "context_reads": ["relationships", "signals"],  # ADR-154: needs platform signals
        "context_writes": ["relationships", "signals"],
        "context_sources": ["platforms", "workspace"],
        "requires_platform": None,
        "default_objective": {
            "deliverable": "Maintained relationship intelligence",
            "audience": "Internal — feeds meeting prep and health digests",
            "purpose": "Keep contact profiles and interaction history current",
            "format": "Per-contact files with history and open items",
        },
        "default_deliverable": {
            "output": {"format": "context", "word_count": "n/a", "layout": ["Per-contact profiles", "Portfolio synthesis"]},
            "assets": [],
            "quality_criteria": [
                "Active contacts have recent interaction entries",
                "Open items tracked with owners and dates",
                "At-risk relationships flagged in portfolio synthesis",
            ],
        },
    },

    "track-projects": {
        "display_name": "Track Projects",
        "description": "Maintain project status, milestones, and blockers from platform signals and team activity.",
        "category": "context",
        "task_class": "context",
        "default_mode": "recurring",
        "default_schedule": "weekly",
        "bootstrap": {
            "min_entities": 2,
            "required_files": ["status"],
        },
        "output_format": "markdown",
        "layout_mode": "document",
        "export_options": [],
        "process": [
            {
                "agent_type": "operations",
                "step": "update-context",
                "instruction": STEP_INSTRUCTIONS["update-context"],
            },
        ],
        "context_reads": ["projects", "signals"],  # ADR-154: needs platform signals
        "context_writes": ["projects", "signals"],
        "context_sources": ["platforms", "workspace"],
        "requires_platform": None,
        "default_objective": {
            "deliverable": "Maintained project intelligence",
            "audience": "Internal — feeds status reports and stakeholder updates",
            "purpose": "Keep project status, milestones, and blockers current",
            "format": "Per-project files with status and milestones",
        },
        "default_deliverable": {
            "output": {"format": "context", "word_count": "n/a", "layout": ["Per-project status", "Portfolio health synthesis"]},
            "assets": [],
            "quality_criteria": [
                "Active projects have current status entries",
                "Blockers identified with owners",
                "Milestone tracking up to date",
            ],
        },
    },

    "research-topics": {
        "display_name": "Research Topics",
        "description": "Deep research on specific topics — accumulate findings, sources, and outlines for content creation.",
        "category": "context",
        "task_class": "context",
        "default_mode": "goal",
        "default_schedule": "on-demand",
        "bootstrap": {
            "min_entities": 1,
            "required_files": ["research"],
        },
        "output_format": "markdown",
        "layout_mode": "document",
        "export_options": [],
        "process": [
            {
                "agent_type": "marketing",
                "step": "update-context",
                "instruction": STEP_INSTRUCTIONS["update-context"],
            },
        ],
        "context_reads": ["content_research"],
        "context_writes": ["content_research"],
        "context_sources": ["web", "workspace"],
        "requires_platform": None,
        "default_objective": {
            "deliverable": "Accumulated topic research",
            "audience": "Internal — feeds content briefs and launch materials",
            "purpose": "Build deep research base for content creation",
            "format": "Per-topic research files with sources and outlines",
        },
        "default_deliverable": {
            "output": {"format": "context", "word_count": "n/a", "layout": ["Per-topic research", "Source compilation"]},
            "assets": [],
            "quality_criteria": [
                "Key points backed by cited sources",
                "Audience considerations documented",
                "Outline structured for downstream content production",
            ],
        },
    },

    # ── Platform Digest Tasks (ADR-158: bot-owned, per-source observation) ──
    # Each platform bot owns a temporal context directory and writes per-source
    # observation files. Bots read live via platform tools, write to their
    # directory + signal log. Cross-pollination into canonical domains is out
    # of scope — these are awareness surfaces for TP, not steward inputs.

    "slack-digest": {
        "display_name": "Slack Digest",
        "description": "Read selected Slack channels. Capture decisions, action items, and key discussions. Write per-channel observations.",
        "category": "platform",
        "task_class": "context",
        "default_mode": "recurring",
        "default_schedule": "daily",
        "output_format": "html",
        "layout_mode": "digest",
        "export_options": [],
        "process": [
            {
                "agent_type": "slack_bot",
                "step": "slack-digest",
                "instruction": STEP_INSTRUCTIONS["slack-digest"],
            },
        ],
        "context_reads": ["slack", "signals"],
        "context_writes": ["slack", "signals"],
        "context_sources": ["platforms"],
        "requires_platform": "slack",
        "default_objective": {
            "deliverable": "Slack activity digest",
            "audience": "You and your team",
            "purpose": "Capture decisions, action items, and key discussions",
            "format": "Scannable digest with attribution",
        },
        "default_deliverable": {
            "output": {"format": "html", "word_count": "500-1500", "layout": ["Decisions", "Action Items", "Key Discussions", "FYIs"]},
            "assets": [],
            "quality_criteria": [
                "Decisions and action items attributed to people",
                "Thread-level summary, not message-level",
                "Skip bot messages and routine posts",
            ],
        },
    },

    "notion-digest": {
        "display_name": "Notion Digest",
        "description": "Read selected Notion pages. Track changes, new content, and stale sections. Write per-page observations.",
        "category": "platform",
        "task_class": "context",
        "default_mode": "recurring",
        "default_schedule": "weekly",
        "output_format": "html",
        "layout_mode": "digest",
        "export_options": [],
        "process": [
            {
                "agent_type": "notion_bot",
                "step": "notion-digest",
                "instruction": STEP_INSTRUCTIONS["notion-digest"],
            },
        ],
        "context_reads": ["notion", "signals"],
        "context_writes": ["notion", "signals"],
        "context_sources": ["platforms"],
        "requires_platform": "notion",
        "default_objective": {
            "deliverable": "Notion change digest",
            "audience": "You and your team",
            "purpose": "Track content changes and flag stale pages",
            "format": "Change log with staleness flags",
        },
        "default_deliverable": {
            "output": {"format": "html", "word_count": "500-1500", "layout": ["Changes Summary", "Updated Pages", "Stale Content"]},
            "assets": [],
            "quality_criteria": [
                "Distinguish meaningful edits from formatting changes",
                "Flag pages not updated in >30 days",
                "Links to original Notion pages",
            ],
        },
    },

    # ══════════════════════════════════════════════════════════════════════════
    # SYNTHESIS TASKS — produce outputs from accumulated context
    # "What reports do you want?"
    # ══════════════════════════════════════════════════════════════════════════

    "competitive-brief": {
        "display_name": "Competitive Brief",
        "description": "Weekly competitive intelligence report with charts, positioning analysis, and strategic implications.",
        "category": "synthesis",
        "task_class": "synthesis",
        "default_mode": "recurring",
        "default_schedule": "weekly",
        "output_format": "html",
        "layout_mode": "document",
        "export_options": ["pdf"],
        "process": [
            {
                "agent_type": "competitive_intel",
                "step": "derive-output",
                "instruction": STEP_INSTRUCTIONS["derive-output"],
            },
        ],
        "context_reads": ["competitors", "signals"],
        "context_writes": [],  # Synthesis tasks don't write to context
        "context_sources": ["workspace"],
        "requires_platform": None,
        "default_objective": {
            "deliverable": "Competitive intelligence brief",
            "audience": "Leadership and strategy team",
            "purpose": "Synthesize competitive landscape from accumulated tracking",
            "format": "Structured report with charts and diagrams",
        },
        "default_deliverable": {
            "output": {"format": "html", "word_count": "2000-3000", "layout": ["Executive Summary", "Key Findings", "Competitive Positioning", "Trend Analysis", "Implications", "Sources"]},
            "assets": [
                {"type": "chart", "subtype": "trend", "min_count": 1, "description": "Quantified trend data"},
                {"type": "chart", "subtype": "comparison", "min_count": 1, "description": "Competitor comparison"},
                {"type": "mermaid", "subtype": "positioning", "min_count": 1, "description": "Competitive positioning map"},
            ],
            "quality_criteria": [
                "Every claim has inline source citation",
                "Minimum 3 competitors analyzed",
                "Forward-looking implications, not just historical reporting",
                "Emphasize what changed since last cycle",
            ],
        },
    },

    "market-report": {
        "display_name": "Market Report",
        "description": "Deep market analysis with segment sizing, player landscape, and opportunity identification.",
        "category": "synthesis",
        "task_class": "synthesis",
        "default_mode": "recurring",
        "default_schedule": "monthly",
        "output_format": "html",
        "layout_mode": "document",
        "export_options": ["pdf"],
        "process": [
            {
                "agent_type": "market_research",
                "step": "derive-output",
                "instruction": STEP_INSTRUCTIONS["derive-output"],
            },
        ],
        "context_reads": ["market", "competitors", "signals"],
        "context_writes": [],
        "context_sources": ["workspace"],
        "requires_platform": None,
        "default_objective": {
            "deliverable": "Market research report",
            "audience": "Leadership and strategy team",
            "purpose": "Synthesize market intelligence from accumulated research",
            "format": "Comprehensive report with data visualizations",
        },
        "default_deliverable": {
            "output": {"format": "html", "word_count": "3000-5000", "layout": ["Executive Summary", "Market Overview", "Key Players", "Technology Trends", "Opportunities & Threats", "Recommendations"]},
            "assets": [
                {"type": "chart", "subtype": "distribution", "min_count": 1, "description": "Market share or segment breakdown"},
                {"type": "chart", "subtype": "trend", "min_count": 1, "description": "Growth trend data"},
            ],
            "quality_criteria": [
                "Data-backed claims with recency noted",
                "Minimum 5 key players profiled",
                "Clear opportunity identification",
            ],
        },
    },

    "meeting-prep": {
        "display_name": "Meeting Prep",
        "description": "Pre-meeting brief with relationship context, talking points, and open items.",
        "category": "synthesis",
        "task_class": "synthesis",
        "default_mode": "reactive",
        "default_schedule": "on-demand",
        "output_format": "html",
        "layout_mode": "document",
        "export_options": [],
        "process": [
            {
                "agent_type": "business_dev",
                "step": "derive-output",
                "instruction": STEP_INSTRUCTIONS["derive-output"],
            },
        ],
        "context_reads": ["relationships", "competitors", "signals"],
        "context_writes": [],
        "context_sources": ["workspace"],
        "requires_platform": None,
        "default_objective": {
            "deliverable": "Meeting preparation brief",
            "audience": "You — before the meeting",
            "purpose": "Synthesize relationship context for effective meeting prep",
            "format": "Scannable brief with talking points",
        },
        "default_deliverable": {
            "output": {"format": "html", "word_count": "800-1500", "layout": ["Context", "Last Interaction", "Agenda Items", "Talking Points", "Open Items"]},
            "assets": [],
            "quality_criteria": [
                "Actionable talking points",
                "References specific prior interactions",
                "Scannable in under 2 minutes",
            ],
        },
    },

    "stakeholder-update": {
        "display_name": "Stakeholder Update",
        "description": "Board-ready update synthesizing all domains — projects, market, competitive, relationships.",
        "category": "synthesis",
        "task_class": "synthesis",
        "default_mode": "recurring",
        "default_schedule": "monthly",
        "output_format": "html",
        "layout_mode": "document",
        "export_options": ["pdf"],
        "process": [
            {
                "agent_type": "executive",
                "step": "derive-output",
                "instruction": STEP_INSTRUCTIONS["derive-output"],
            },
        ],
        "context_reads": ["competitors", "market", "projects", "relationships", "signals"],
        "context_writes": [],
        "context_sources": ["workspace"],
        "requires_platform": None,
        "default_objective": {
            "deliverable": "Stakeholder / board update",
            "audience": "Board members, investors, leadership",
            "purpose": "Synthesize all domains into executive-level update",
            "format": "Board-level report with KPI charts and strategic framing",
        },
        "default_deliverable": {
            "output": {"format": "html", "word_count": "2000-3000", "layout": ["Executive Summary", "Key Milestones", "Challenges & Mitigations", "Financial Overview", "Forward Look"]},
            "assets": [
                {"type": "chart", "subtype": "trend", "min_count": 1, "description": "KPI or progress metrics"},
                {"type": "chart", "subtype": "comparison", "min_count": 1, "description": "Budget vs actual or milestone tracking"},
            ],
            "quality_criteria": [
                "Board-level polish",
                "Key milestones with status",
                "Forward-looking strategic priorities",
            ],
        },
    },

    "project-status": {
        "display_name": "Project Status Report",
        "description": "Weekly status report per workstream with progress, blockers, and next steps.",
        "category": "synthesis",
        "task_class": "synthesis",
        "default_mode": "recurring",
        "default_schedule": "weekly",
        "output_format": "html",
        "layout_mode": "document",
        "export_options": [],
        "process": [
            {
                "agent_type": "operations",
                "step": "derive-output",
                "instruction": STEP_INSTRUCTIONS["derive-output"],
            },
        ],
        "context_reads": ["projects", "signals"],
        "context_writes": [],
        "context_sources": ["workspace"],
        "requires_platform": None,
        "default_objective": {
            "deliverable": "Project status report",
            "audience": "Project stakeholders",
            "purpose": "Synthesize project tracking into actionable status update",
            "format": "Status report with workstream breakdown",
        },
        "default_deliverable": {
            "output": {"format": "html", "word_count": "1500-2500", "layout": ["Status Summary", "Progress by Workstream", "Blockers & Risks", "Next Week Priorities"]},
            "assets": [{"type": "chart", "subtype": "comparison", "min_count": 1, "description": "Progress or milestone status"}],
            "quality_criteria": [
                "Clear status per workstream",
                "Blockers flagged with owners",
                "Actionable next steps",
            ],
        },
    },

    "content-brief": {
        "display_name": "Content Brief",
        "description": "Blog post, article, or content draft synthesized from accumulated topic research.",
        "category": "synthesis",
        "task_class": "synthesis",
        "default_mode": "goal",
        "default_schedule": "on-demand",
        "output_format": "html",
        "layout_mode": "document",
        "export_options": ["pdf"],
        "process": [
            {
                "agent_type": "marketing",
                "step": "derive-output",
                "instruction": STEP_INSTRUCTIONS["derive-output"],
            },
        ],
        "context_reads": ["content_research", "competitors", "signals"],
        "context_writes": [],
        "context_sources": ["workspace"],
        "requires_platform": None,
        "default_objective": {
            "deliverable": "Content brief / blog draft",
            "audience": "Target content audience",
            "purpose": "Synthesize topic research into publishable content",
            "format": "Structured draft with key messages and evidence",
        },
        "default_deliverable": {
            "output": {"format": "html", "word_count": "1500-3000", "layout": ["Brief Overview", "Target Audience", "Key Messages", "Draft Content", "Sources"]},
            "assets": [],
            "quality_criteria": [
                "Audience-appropriate tone and depth",
                "Clear key messages",
                "Draft ready for light editing",
            ],
        },
    },

    "launch-material": {
        "display_name": "Launch Material",
        "description": "Launch announcements, press materials, and go-to-market content from accumulated research.",
        "category": "synthesis",
        "task_class": "synthesis",
        "default_mode": "goal",
        "default_schedule": "on-demand",
        "output_format": "html",
        "layout_mode": "document",
        "export_options": ["pdf"],
        "process": [
            {
                "agent_type": "marketing",
                "step": "derive-output",
                "instruction": STEP_INSTRUCTIONS["derive-output"],
            },
        ],
        "context_reads": ["content_research", "competitors", "market", "signals"],
        "context_writes": [],
        "context_sources": ["workspace"],
        "requires_platform": None,
        "default_objective": {
            "deliverable": "Launch / announcement material",
            "audience": "External audiences — customers, press, investors",
            "purpose": "Synthesize competitive positioning and research into launch content",
            "format": "Launch materials with audience segmentation",
        },
        "default_deliverable": {
            "output": {"format": "html", "word_count": "1500-3000", "layout": ["Launch Summary", "Key Messages", "Target Audiences", "Deliverables Checklist", "Timeline"]},
            "assets": [{"type": "mermaid", "subtype": "timeline", "min_count": 1, "description": "Launch timeline"}],
            "quality_criteria": [
                "Consistent messaging across materials",
                "Clear audience segmentation",
                "Actionable deliverables checklist",
            ],
        },
    },

    "gtm-report": {
        "display_name": "GTM Report",
        "description": "Go-to-market intelligence report with competitive moves, market signals, and channel performance.",
        "category": "synthesis",
        "task_class": "synthesis",
        "default_mode": "recurring",
        "default_schedule": "weekly",
        "output_format": "html",
        "layout_mode": "dashboard",
        "export_options": [],
        "process": [
            {
                "agent_type": "marketing",
                "step": "derive-output",
                "instruction": STEP_INSTRUCTIONS["derive-output"],
            },
        ],
        "context_reads": ["competitors", "market", "signals"],
        "context_writes": [],
        "context_sources": ["workspace"],
        "requires_platform": None,
        "default_objective": {
            "deliverable": "GTM tracker report",
            "audience": "Product, marketing, and strategy teams",
            "purpose": "Synthesize competitive and market signals into GTM intelligence",
            "format": "Dashboard-style report with feature matrices and signal cards",
        },
        "default_deliverable": {
            "output": {"format": "html", "word_count": "1500-2500", "layout": ["Market Pulse", "Competitive Moves", "Channel Performance", "Opportunities", "Recommendations"]},
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
    },
}


# =============================================================================
# Helper Functions
# =============================================================================

def get_task_type(type_key: str) -> dict[str, Any] | None:
    """Look up a task type by key. Returns None if not found."""
    return TASK_TYPES.get(type_key)


def get_default_mode(type_key: str) -> str:
    """Get the default mode for a task type. Falls back to 'recurring'."""
    task_type = TASK_TYPES.get(type_key)
    if not task_type:
        return "recurring"
    return task_type.get("default_mode", "recurring")


def get_bootstrap_criteria(type_key: str) -> Optional[dict]:
    """Get bootstrap criteria for a task type. Returns None if no bootstrap."""
    task_type = TASK_TYPES.get(type_key)
    if not task_type:
        return None
    return task_type.get("bootstrap")


def evaluate_bootstrap_status(
    type_key: str,
    entity_count: int,
    entities_with_required_files: int,
) -> str:
    """Evaluate whether a task has completed bootstrap.

    ADR-154: Deterministic phase detection. Returns 'bootstrap' or 'steady'.

    Args:
        type_key: Task type key
        entity_count: Total entities in the domain
        entities_with_required_files: Entities that have all required files

    Returns:
        'bootstrap' if criteria not met, 'steady' if met
    """
    bootstrap = get_bootstrap_criteria(type_key)
    if not bootstrap:
        return "steady"  # No bootstrap criteria → always steady

    min_entities = bootstrap.get("min_entities", 1)
    if entities_with_required_files >= min_entities:
        return "steady"
    return "bootstrap"


def list_task_types(category: str | None = None, task_class: str | None = None) -> list[dict[str, Any]]:
    """List task types, optionally filtered by category or class.

    Args:
        category: Filter by category key (context, synthesis, platform)
        task_class: Filter by class (context, synthesis)
    """
    result = []
    for key, definition in TASK_TYPES.items():
        if category and definition["category"] != category:
            continue
        if task_class and definition.get("task_class") != task_class:
            continue
        result.append({"type_key": key, **definition})
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
    """Validate that all agent types in the process exist in AGENT_TYPES."""
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
    """Resolve process steps to actual agents from the user's roster."""
    task_type = TASK_TYPES.get(type_key)
    if not task_type:
        return None
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
    sources: dict[str, list[str]] | None = None,
) -> str | None:
    """Build TASK.md content from a task type definition.

    ADR-152: Serializes ALL runtime config into TASK.md — context_reads,
    context_writes, output_category, process steps. Pipeline reads TASK.md
    at runtime, not the registry.
    """
    task_type = TASK_TYPES.get(type_key)
    if not task_type:
        return None

    effective_schedule = schedule or task_type["default_schedule"]
    objective = task_type["default_objective"]

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

    # ADR-154: Serialize runtime config into TASK.md (output_category removed)
    context_reads = task_type.get("context_reads", [])
    context_writes = task_type.get("context_writes", [])

    effective_mode = task_type.get("default_mode", "recurring")

    # ADR-158 Phase 2: serialize sources into TASK.md
    sources_str = "none"
    if sources:
        parts = []
        for platform, ids in sources.items():
            parts.append(f"{platform}:{','.join(ids)}")
        sources_str = "; ".join(parts)

    md = f"""# {title}

**Slug:** {slug}
**Type:** {type_key}
**Class:** {task_type.get('task_class', 'synthesis')}
**Mode:** {effective_mode}
**Schedule:** {effective_schedule}
**Delivery:** {delivery or 'none'}
**Context Reads:** {', '.join(context_reads) if context_reads else 'none'}
**Context Writes:** {', '.join(context_writes) if context_writes else 'none'}
**Sources:** {sources_str}

## Objective
- **Deliverable:** {deliverable_text}
- **Audience:** {objective['audience']}
- **Purpose:** {purpose_text}
- **Format:** {objective['format']}

## Process
{chr(10).join(process_lines)}

## Output Spec
- Deliverable as specified in DELIVERABLE.md
"""
    return md


def build_deliverable_md_from_type(
    type_key: str,
    audience_override: str | None = None,
) -> str | None:
    """Build DELIVERABLE.md content from a task type's default_deliverable spec.

    ADR-149/152: DELIVERABLE.md is the quality contract. For context tasks,
    describes context quality (coverage, freshness). For synthesis tasks,
    describes document quality (format, assets, audience).
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
    task_class = task_type.get("task_class", "synthesis")

    if task_class == "context":
        # Context quality specification
        criteria_lines = [f"- {c}" for c in criteria]
        audience = audience_override or objective.get("audience", "")

        md = f"""# Context Quality Specification

## Coverage
{chr(10).join(criteria_lines)}

## Freshness
- Entity files updated within scheduled cadence
- Signal log entries within last cycle

## Depth
- Each entity has substantive content (not just headers)
- Synthesis file reflects latest cross-entity patterns

{f"## Audience{chr(10)}{audience}" if audience else ""}

## User Preferences (inferred)
<!-- Populated by feedback inference (ADR-149). Empty at creation. -->
"""
    else:
        # Document quality specification
        layout_str = " → ".join(output.get("layout", []))
        output_section = (
            f"## Expected Output\n"
            f"- Format: {output.get('format', 'html').upper()} document, {output.get('word_count', '1000-2000')} words\n"
            f"- Layout: {layout_str}\n"
        )

        if assets:
            asset_lines = [
                f"- {a.get('subtype', '').title()} {a.get('type', 'chart')}: at least {a.get('min_count', 1)} — {a.get('description', '')}"
                for a in assets
            ]
            assets_section = "## Expected Assets\n" + "\n".join(asset_lines) + "\n"
        else:
            assets_section = "## Expected Assets\n- Visual assets optional where data supports\n"

        criteria_lines = [f"- {c}" for c in criteria]
        criteria_section = "## Quality Criteria\n" + "\n".join(criteria_lines) + "\n"

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

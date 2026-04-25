"""
Task Type Registry — ADR-152 + ADR-154 + ADR-166 + ADR-170 (ADR-207 P4b: DEPRECATED as dispatch authority)

**ADR-207 P4b (2026-04-22) status:**

This module no longer dictates dispatch behavior. `task_pipeline.py` and all
execution paths read TASK.md exclusively — no more `get_task_type(type_key)`
lookups in the pipeline, no more `get_bootstrap_criteria` gates, no more
`STEP_INSTRUCTIONS` fallbacks. TASK.md self-declaration is authoritative
for every runtime decision (capability gate, page structure, process steps,
output kind, context reads/writes, surface type).

What survives here, and why:

  - `TASK_TYPES` dict (21 entries) + `STEP_INSTRUCTIONS` dict — kept as a
    *seed-template library*. Two callers consume these at creation time:
      * `_handle_create`'s `type_key` path (deprecated convenience).
      * `workspace_init.materialize_back_office_task` (scaffolds 4 back-office
        tasks whose TASK.md is identical for every workspace).
    Neither reads the registry at dispatch — both write finished TASK.md to
    workspace and the pipeline reads from there.

  - 8 helper functions (`get_task_type`, `get_default_mode`,
    `delivery_requires_approval`, `get_bootstrap_criteria`, `list_task_types`,
    `resolve_process_agents`, `build_task_md_from_type`,
    `build_deliverable_md_from_type`) — kept functional for the two callers
    above. Callers should not add new imports.

What's been deleted under P4b:
  - `GET /api/tasks/types` and `GET /api/tasks/types/{type_key}` endpoints.
  - `_handle_update`'s `new_type_key` change path (rewrote TASK.md process
    section from registry; now operators self-declare).
  - All `task_pipeline.py` registry fallbacks (surface_type, page_structure,
    bootstrap criteria, STEP_INSTRUCTIONS).
  - 11 bot-dispatched TASK_TYPES entries (see ADR-207 P4a for list).

Removal trajectory: when `_handle_create`'s type_key path is retired and the
4 back-office templates move to inline fixtures in `workspace_init.py`, this
module can be deleted wholesale. Until then, treat TASK_TYPES + its helpers
as frozen — add nothing, refactor nothing, prefer self-declaration.

--- Original module header ---
Task Type Registry — ADR-152 + ADR-154 + ADR-166 + ADR-170: Atomic Task Types

Each task type has one `output_kind` (ADR-166) describing what shape of work
the task produces. Four values:

  accumulates_context  — Writes to a workspace context domain. No user-visible
                         artifact this run. (track-*, *-digest, research-topics)
  produces_deliverable — Writes a user-visible output to /tasks/{slug}/outputs/.
                         (daily-update, *-brief, *-report, *-prep, *-update)
  external_action      — Takes an action on an external platform via API write.
                         (slack-respond, notion-update, commerce-create-product,
                          commerce-update-product, commerce-create-discount)
  system_maintenance   — TP-owned. Produces an orchestration signal. Deterministic,
                         no LLM. (back-office-*)

Users think: "What do I want to track?" → tasks with output_kind=accumulates_context.
             "What reports do I want?" → tasks with output_kind=produces_deliverable.

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

Surface type + page_structure (ADR-170):
  produces_deliverable tasks declare surface_type (visual paradigm: report, deck,
  dashboard, digest, workbook, preview, video) and page_structure (section kinds
  with scope declarations). The compose substrate reads these at execution time
  to build the generation brief and output folder.

  accumulates_context, external_action, system_maintenance tasks have no surface
  type — they don't produce user-visible HTML output. The field is absent.

Version: 7.1 (2026-04-14 — github-digest: cycle-aware step instructions, first-run vs steady-state split)
Changelog:
  v1.0 — 13 product-named types (ADR-145)
  v2.0 — context_reads/writes, output_category, STEP_INSTRUCTIONS templates (ADR-152)
  v3.0 — Atomic split: context + synthesis types. Task-first, user-friendly naming.
  v4.0 — ADR-154: default_mode + bootstrap criteria. Phase-aware execution.
  v4.1 — ADR-157: Visual asset guidance in step instructions (favicon fetch + embed).
  v4.2 — ADR-157: assets/ subfolder convention.
  v5.0 — ADR-158: Platform bot ownership. monitor-* → *-digest. Bots own directories.
  v5.1 — ADR-158 Phase 3: Write-back task types (slack-respond, notion-update).
  v5.2 — ADR-158 Phase 4: GitHub digest + GitHub Bot.
  v6.0 — ADR-166 Registry Coherence Pass:
         - DROPPED `category` field and `TASK_TYPE_CATEGORIES` constant
         - RENAMED `task_class` → `output_kind`, expanded enum to 4 values
         - RECLASSIFIED slack-respond/notion-update: synthesis → external_action
         - DELETED gtm-report (merged into market-report)
         - CHANGED meeting-prep mode: reactive → goal (it has clear completion)
         - NORMALIZED track-* context_reads (all four read domain + signals now)
  v7.0 — ADR-170 Compose Substrate:
         - DELETED `layout_mode` from all task types (no backwards compat)
         - ADDED `surface_type` to produces_deliverable tasks (7 visual paradigms)
         - ADDED `page_structure` to produces_deliverable tasks (section kinds vocabulary)
         - accumulates_context / external_action / system_maintenance have no surface
         - Section kind vocabulary: narrative, metric-cards, entity-grid,
           comparison-table, trend-chart, distribution-chart, timeline,
           status-matrix, data-table, callout, checklist
  v7.1 — ADR-183 Phase 3: Commerce write-back task types
         (commerce-create-product, commerce-update-product, commerce-create-discount).
         Same external_action pattern as slack-respond/notion-update.

Canonical docs:
  - docs/architecture/registry-matrix.md
  - docs/adr/ADR-166-registry-coherence-pass.md
  - docs/adr/ADR-170-compose-substrate.md
  - docs/architecture/compose-substrate.md
  - docs/architecture/output-surfaces.md
"""

from __future__ import annotations

from typing import Any, Optional

from services.orchestration import ALL_ROLES


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
        "YOUR #1 PRIORITY: Create entity files using WriteFile. Text output is secondary.\n\n"
        "REQUIRED STEPS:\n"
        "1. WebSearch to discover key entities in this domain (companies, people, segments, etc.)\n"
        "2. For EACH entity found, call WriteFile with:\n"
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
        "EXAMPLE WriteFile call:\n"
        "  WriteFile(path='openai/profile.md', content='# OpenAI\\n\\n## Overview\\nOpenAI is...', "
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

    "daily-digest": (
        "Produce a concise daily update for the user. This is operational, not analytical.\n\n"
        "Structure: What Happened → What Changed → What's Next\n\n"
        "**What Happened**: Which tasks ran today, which agents were active. "
        "Brief summary of each task's output (1-2 sentences, not the full report).\n\n"
        "**What Changed**: Key updates to workspace context domains — new entities discovered, "
        "signals logged, profiles updated. Focus on what's NEW since yesterday.\n\n"
        "IMPORTANT for What Changed: context files carry their last-updated date in the "
        "section header (e.g. 'updated 2026-04-13'). For each item you surface, include "
        "that date in parentheses so the user can judge freshness — e.g. "
        "'Cursor raised $100M Series B (Apr 13)'. Never omit the date for competitor or "
        "market signals — dateless findings are unactionable.\n\n"
        "**What's Next**: Upcoming scheduled tasks, when they'll run, what they'll cover.\n\n"
        "Keep it scannable — the user should absorb this in under 60 seconds. "
        "Use bullet points, not paragraphs. No charts or visuals needed. "
        "If nothing meaningful happened today, say so briefly — don't pad."
    ),

    "capture-and-report": (
        "Read existing context files (patterns, signal history). "
        "Gather new signals from platform context. Log new signals to the signal domain. "
        "Update pattern synthesis if new cross-signal patterns emerge. "
        "Produce the deliverable emphasizing what's new since last cycle."
    ),

    # ADR-207 P4a: slack-digest / slack-respond / notion-digest / notion-update /
    # github-digest / commerce-digest / commerce-create-product /
    # commerce-update-product / commerce-create-discount / trading-digest /
    # trading-execute step instructions DELETED along with their TASK_TYPES
    # entries. The bot roles they addressed ("You are the Slack Bot...") no
    # longer exist. Operators author equivalent work via YARNNN using a
    # specialist + required_capabilities declaration in TASK.md.

    "trading-signal": (
        "You are generating trading signals based on accumulated market "
        "intelligence and portfolio context.\n\n"
        "IMPORTANT: Read the workspace FIRST. Your value comes from "
        "accumulated context — price history, prior signal outcomes, "
        "portfolio performance, and market patterns observed over time.\n\n"
        "Steps:\n"
        "1. ReadFile: /workspace/context/portfolio/_tracker.md (current state)\n"
        "2. ReadFile: /workspace/context/portfolio/summary.md (portfolio assessment)\n"
        "3. For each watchlist asset:\n"
        "   - ReadFile: /workspace/context/trading/{ticker}/profile.md\n"
        "   - ReadFile: /workspace/context/trading/{ticker}/analysis.md "
        "(prior signals + outcomes)\n"
        "4. Analyze: trend direction, momentum, support/resistance, news catalysts, "
        "prior signal accuracy for this asset\n"
        "5. Generate signals with format:\n"
        "   - Ticker, Direction (buy/sell/hold), Confidence (high/medium/low)\n"
        "   - Reasoning (2-3 sentences referencing accumulated data)\n"
        "   - Suggested position size (%% of portfolio)\n"
        "   - Risk note (what would invalidate this signal)\n"
        "6. WriteFile: update /workspace/context/trading/{ticker}/analysis.md "
        "(append this signal for future outcome tracking)\n\n"
        "Your output: today's signal report with actionable recommendations."
    ),

    # ADR-207 P4a: trading-execute step instruction DELETED (was bot-addressed).

    "portfolio-review": (
        "You are producing a weekly portfolio performance review.\n\n"
        "Steps:\n"
        "1. ReadFile: /workspace/context/portfolio/_tracker.md\n"
        "2. ReadFile: /workspace/context/portfolio/history/{YYYY-MM}.md\n"
        "3. ReadFile: /workspace/context/portfolio/performance/{YYYY-MM}.md "
        "(if exists)\n"
        "4. For each position, read trading/{ticker}/analysis.md to correlate "
        "signal → outcome\n"
        "5. Compute:\n"
        "   - Weekly return (%% and $)\n"
        "   - Signal accuracy (%% of signals that were profitable)\n"
        "   - Best/worst trades with reasoning\n"
        "   - Benchmark comparison (SPY buy-and-hold equivalent)\n"
        "   - Portfolio concentration and risk assessment\n"
        "6. Produce report with:\n"
        "   - Section kind: metric-cards (portfolio KPIs)\n"
        "   - Section kind: trend-chart (cumulative return vs benchmark)\n"
        "   - Section kind: data-table (trade log with outcomes)\n"
        "   - Section kind: narrative (weekly commentary)\n"
        "7. WriteFile: /workspace/context/portfolio/performance/{YYYY-MM}.md\n"
        "8. WriteFile: /workspace/context/portfolio/summary.md "
        "(updated synthesis)\n\n"
        "Your output: weekly performance report with charts and metrics."
    ),

    "workspace-intelligence": (
        "You are producing the Workspace Intelligence Cockpit — a daily synthesis of this "
        "workspace's accumulated knowledge for the operator.\n\n"
        "CRITICAL RULE: Only emit sections for which you have grounded data from files you "
        "actually read. An absent section is honest. An empty section is noise.\n\n"
        "STEP 1 — Read the workspace substrate:\n"
        "- ReadFile: /workspace/context/_performance_summary.md (outcome data)\n"
        "- ListFiles: /workspace/context/ (discover active context domains)\n"
        "- For each active domain: ReadFile its _tracker.md and synthesis file\n"
        "- ReadFile: /agents/reporting/AGENT.md (your own identity + prior synthesis notes)\n"
        "- ReadFile: /tasks/maintain-overview/memory/run_log.md if it exists (prior runs)\n\n"
        "STEP 2 — Read DELIVERABLE.md for the section catalog and archetype framing hints.\n\n"
        "STEP 3 — Assess what the workspace actually knows:\n"
        "- How many domains are active? How many entities per domain?\n"
        "- Is outcome data present (_performance_summary.md non-empty)?\n"
        "- Are any agents flagged or tasks stale?\n"
        "- What archetype framing applies (trading / commerce / content / multi-domain / nascent)?\n\n"
        "STEP 4 — Produce the output using ONLY the catalog sections warranted by the data. "
        "Use exact section titles from the catalog so the compose pipeline assigns the correct "
        "render kind. Maximum 5 sections. 'Workspace Synthesis' is always included. "
        "Every data claim must be derivable from files you read — no fabrication.\n\n"
        "STEP 5 — WriteFile: /tasks/maintain-overview/memory/run_log.md "
        "Append a one-line entry: '## {date}: sections emitted, archetype applied, "
        "key signal surfaced'. This is your handoff to the next run.\n\n"
        "Your output: the cockpit artifact as structured markdown sections."
    ),
}


# =============================================================================
# Task Type Categories
# =============================================================================

# ADR-166: TASK_TYPE_CATEGORIES dropped. Categorization is implicit via owner agent
# class + output_kind. The orphaned `web/components/workfloor/TaskTypeCatalog.tsx`
# was the only consumer of categories on the frontend; it has been deleted in the
# same commit per singular-implementation discipline.


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
        "description": "Builds a running knowledge file on each competitor — pricing, product moves, funding, and strategy shifts.",
        "output_kind": "accumulates_context",
        "default_delivery": "none",
        "registry_default_team": ["researcher"],
        "default_mode": "recurring",
        "default_schedule": "weekly",
        "bootstrap": {
            "min_entities": 3,
            "required_files": ["profile"],
        },
        "output_format": "markdown",
        "export_options": [],
        "process": [
            {
                "agent_type": "researcher",
                "step": "update-context",
                "instruction": STEP_INSTRUCTIONS["update-context"],
            },
        ],
        # ADR-166: normalized — all track-* tasks read their domain + signals
        # for consistent next-cycle directive context.
        "context_reads": ["competitors", "signals"],
        "context_writes": ["competitors", "signals"],
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
        "description": "Builds a running knowledge file on your market — segments, trends, sizing, and emerging opportunities.",
        "output_kind": "accumulates_context",
        "default_delivery": "none",
        "registry_default_team": ["researcher"],
        "default_mode": "recurring",
        "default_schedule": "weekly",
        "bootstrap": {
            "min_entities": 2,
            "required_files": ["analysis"],
        },
        "output_format": "markdown",
        "export_options": [],
        "process": [
            {
                "agent_type": "researcher",
                "step": "update-context",
                "instruction": STEP_INSTRUCTIONS["update-context"],
            },
        ],
        # ADR-166: normalized — all track-* tasks read their domain + signals
        "context_reads": ["market", "signals"],
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
        "description": "Keeps a live profile on each contact — last touchpoint, context, and relationship health.",
        "output_kind": "accumulates_context",
        "default_delivery": "none",
        "registry_default_team": ["tracker"],
        "default_mode": "recurring",
        "default_schedule": "weekly",
        "bootstrap": {
            "min_entities": 3,
            "required_files": ["profile"],
        },
        "output_format": "markdown",
        "export_options": [],
        "process": [
            {
                "agent_type": "tracker",
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
        "description": "Keeps project status, milestones, and blockers up to date across your active workstreams.",
        "output_kind": "accumulates_context",
        "default_delivery": "none",
        "registry_default_team": ["tracker"],
        "default_mode": "recurring",
        "default_schedule": "weekly",
        "bootstrap": {
            "min_entities": 2,
            "required_files": ["status"],
        },
        "output_format": "markdown",
        "export_options": [],
        "process": [
            {
                "agent_type": "tracker",
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
        "display_name": "Deep Research",
        "description": "Digs deep on a topic you define — builds a research file of findings, sources, and key takeaways.",
        "output_kind": "accumulates_context",
        "default_delivery": "none",
        "registry_default_team": ["researcher"],
        "default_mode": "goal",
        "default_schedule": "on-demand",
        "bootstrap": {
            "min_entities": 1,
            "required_files": ["research"],
        },
        "output_format": "markdown",
        "export_options": [],
        "process": [
            {
                "agent_type": "researcher",
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

    # ADR-207 P4a: slack-digest / notion-digest / github-digest / commerce-digest
    # DELETED. Bot roles they dispatched to (slack_bot / notion_bot / github_bot /
    # commerce_bot) no longer exist. Operators requesting a platform digest ask
    # YARNNN, who authors the TASK.md directly via ManageTask(create) with the
    # appropriate specialist + required_capabilities declaration.

    "revenue-report": {
        "display_name": "Revenue Report",
        "description": "Synthesizes commerce data into a revenue and business intelligence report.",
        "output_kind": "produces_deliverable",
        "default_delivery": "email",
        "registry_default_team": ["analyst", "writer"],
        "default_mode": "recurring",
        "default_schedule": "weekly",
        "output_format": "html",
        "surface_type": "report",
        "page_structure": [
            {"kind": "narrative", "title": "Executive Summary",
             "reads_from": ["revenue/summary.md", "signals/_tracker.md"]},
            {"kind": "metric-cards", "title": "Key Metrics",
             "reads_from": ["revenue/summary.md"]},
            {"kind": "trend-chart", "title": "Revenue Trend",
             "reads_from": ["revenue/summary.md"],
             "assets": [{"type": "derivative", "render": "chart"}]},
            {"kind": "comparison-table", "title": "Product Performance",
             "reads_from": ["revenue/products/"]},
            {"kind": "narrative", "title": "Customer Insights",
             "reads_from": ["customers/overview.md"]},
        ],
        "export_options": ["pdf"],
        "process": [
            {
                "agent_type": "analyst",
                "step": "derive-output",
                "instruction": STEP_INSTRUCTIONS["derive-output"],
            },
        ],
        "context_reads": ["revenue", "customers", "signals"],
        "context_writes": [],
        "context_sources": ["workspace"],
        "requires_platform": "commerce",
        "default_objective": {
            "deliverable": "Revenue and business intelligence report",
            "audience": "You",
            "purpose": "Synthesize commerce data into business intelligence",
            "format": "Structured report with metrics and trends",
        },
        "default_deliverable": {
            "output": {"format": "html", "word_count": "1000-2500", "layout": ["Summary", "Metrics", "Product Performance", "Customer Insights"]},
            "assets": [
                {"type": "chart", "subtype": "trend", "min_count": 1, "description": "Revenue trend"},
            ],
            "quality_criteria": [
                "Revenue figures match source data precisely",
                "Period-over-period comparisons included",
                "Per-product performance quantified",
            ],
        },
    },

    # ── Platform Write-Back Tasks (ADR-158 Phase 3: bot-initiated delivery) ──
    # Bots can write back to their platform — distinct from digest (read) tasks.
    # Write-back is intentional delivery, not observation.

    # ADR-207 P4a: slack-respond / notion-update DELETED (bot-dispatched external
    # actions). Operators author Slack / Notion write tasks via YARNNN with a
    # specialist + `**Required Capabilities:** write_slack` / `write_notion`.

    # ADR-207 P4a: commerce-create-product / commerce-update-product /
    # commerce-create-discount / trading-digest DELETED. commerce_bot /
    # trading_bot roles no longer exist. Operators author commerce + trading
    # write tasks via YARNNN with a specialist + `**Required Capabilities:**
    # write_commerce` / `write_trading` declarations (and corresponding reads).

    "trading-signal": {
        "display_name": "Trading Signals",
        "default_title": "Trading Signals",
        "description": "Generates trading signals from accumulated market intelligence and portfolio context.",
        "output_kind": "produces_deliverable",
        "default_delivery": "none",
        "registry_default_team": ["analyst"],
        "default_mode": "recurring",
        "default_schedule": "daily",
        "output_format": "html",
        "export_options": [],
        "process": [
            {
                "agent_type": "analyst",
                "step": "trading-signal",
                "instruction": STEP_INSTRUCTIONS["trading-signal"],
            },
        ],
        "context_reads": ["trading", "portfolio"],
        "context_writes": ["trading"],
        "context_sources": ["workspace"],
        "requires_platform": "trading",
        "default_objective": {
            "deliverable": "Daily trading signal report",
            "audience": "You",
            "purpose": "Analyze accumulated data and generate actionable signals",
            "format": "Signal report with ticker, direction, confidence, reasoning",
        },
        "default_deliverable": {
            "output": {"format": "html", "word_count": "500-2000", "layout": ["Summary", "Signals", "Risk Notes"]},
            "assets": [],
            "quality_criteria": [
                "Each signal references accumulated data (not generic)",
                "Confidence level justified by evidence",
                "Risk note included for every signal",
            ],
        },
    },

    # ADR-207 P4a: trading-execute DELETED. trading_bot role no longer exists.
    # Operators author trade-execute tasks via YARNNN with a specialist +
    # `**Required Capabilities:** write_trading` declaration.

    "portfolio-review": {
        "display_name": "Portfolio Review",
        "default_title": "Portfolio Review",
        "description": "Weekly portfolio performance report with signal accuracy, benchmark comparison, and charts.",
        "output_kind": "produces_deliverable",
        "default_delivery": "email",
        "registry_default_team": ["analyst"],
        "default_mode": "recurring",
        "default_schedule": "weekly",
        "output_format": "html",
        "surface_type": "report",
        "page_structure": [
            {"kind": "metric-cards", "title": "Portfolio KPIs",
             "reads_from": ["portfolio/_tracker.md"]},
            {"kind": "trend-chart", "title": "Cumulative Return vs Benchmark",
             "reads_from": ["portfolio/performance/"],
             "assets": [{"type": "derivative", "render": "chart"}]},
            {"kind": "data-table", "title": "Trade Log",
             "reads_from": ["portfolio/history/"]},
            {"kind": "narrative", "title": "Weekly Commentary",
             "reads_from": ["portfolio/summary.md", "trading/overview.md"]},
        ],
        "export_options": ["pdf"],
        "process": [
            {
                "agent_type": "analyst",
                "step": "portfolio-review",
                "instruction": STEP_INSTRUCTIONS["portfolio-review"],
            },
        ],
        "context_reads": ["portfolio", "trading"],
        "context_writes": ["portfolio"],
        "context_sources": ["workspace"],
        "requires_platform": "trading",
        "default_objective": {
            "deliverable": "Weekly portfolio performance report",
            "audience": "You",
            "purpose": "Measure signal accuracy, track returns vs benchmark, identify patterns",
            "format": "Report with charts, metrics, and trade log",
        },
        "default_deliverable": {
            "output": {"format": "html", "word_count": "1000-3000", "layout": ["KPIs", "Performance Chart", "Trade Log", "Commentary"]},
            "assets": [{"type": "derivative", "render": "chart", "description": "Cumulative return vs SPY"}],
            "quality_criteria": [
                "Signal accuracy computed precisely",
                "Benchmark comparison (SPY) included",
                "Best/worst trades with reasoning",
            ],
        },
    },

    # ══════════════════════════════════════════════════════════════════════════
    # SYNTHESIS TASKS — produce outputs from accumulated context
    # "What reports do you want?"
    # ══════════════════════════════════════════════════════════════════════════

    "competitive-brief": {
        "display_name": "Competitive Intel Report",
        "description": "Competitive intelligence report — positioning, pricing moves, strategic implications, and charts.",
        "output_kind": "produces_deliverable",
        "default_delivery": "email",
        "registry_default_team": ["researcher", "analyst", "writer"],
        "default_mode": "recurring",
        "default_schedule": "weekly",
        "output_format": "html",
        "surface_type": "report",
        "page_structure": [
            {"kind": "narrative", "title": "Executive Summary",
             "reads_from": ["competitors/landscape.md", "signals/_tracker.md"]},
            {"kind": "entity-grid", "title": "Competitor Profiles",
             "entity_pattern": "competitors/*/",
             "assets": [{"type": "root", "pattern": "competitors/assets/*-favicon.png"}]},
            {"kind": "timeline", "title": "Recent Signals",
             "reads_from": ["signals/_tracker.md"]},
            {"kind": "trend-chart", "title": "Market Position",
             "reads_from": ["competitors/*/analysis.md"],
             "assets": [{"type": "derivative", "render": "chart"}]},
            {"kind": "comparison-table", "title": "Competitive Matrix",
             "reads_from": ["competitors/*/profile.md"]},
            {"kind": "callout", "title": "Strategic Implications",
             "reads_from": ["competitors/landscape.md"]},
        ],
        "export_options": ["pdf"],
        "process": [
            {
                "agent_type": "researcher",
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
        # ADR-166: absorbs former gtm-report. Market intelligence, competitive moves,
        # and GTM signals all roll up here — they read the same context domains and
        # the audience overlap (leadership, strategy, marketing) is total.
        "description": "Market intelligence report — segment sizing, competitive moves, GTM signals, and opportunity gaps.",
        "output_kind": "produces_deliverable",
        "default_delivery": "email",
        "registry_default_team": ["researcher", "analyst", "writer"],
        "default_mode": "recurring",
        "default_schedule": "monthly",
        "output_format": "html",
        "surface_type": "report",
        "page_structure": [
            {"kind": "narrative", "title": "Executive Summary",
             "reads_from": ["market/overview.md", "competitors/landscape.md"]},
            {"kind": "distribution-chart", "title": "Market Overview",
             "reads_from": ["market/*/analysis.md"],
             "assets": [{"type": "derivative", "render": "chart"}]},
            {"kind": "entity-grid", "title": "Key Players",
             "entity_pattern": "competitors/*/",
             "assets": [{"type": "root", "pattern": "competitors/assets/*-favicon.png"}]},
            {"kind": "trend-chart", "title": "Growth & Signals",
             "reads_from": ["market/*/analysis.md", "signals/_tracker.md"],
             "assets": [{"type": "derivative", "render": "chart"}]},
            {"kind": "comparison-table", "title": "Competitive Moves",
             "reads_from": ["competitors/*/profile.md"]},
            {"kind": "callout", "title": "Opportunities & Threats",
             "reads_from": ["market/overview.md", "signals/_tracker.md"]},
        ],
        "export_options": ["pdf"],
        "process": [
            {
                "agent_type": "researcher",
                "step": "derive-output",
                "instruction": STEP_INSTRUCTIONS["derive-output"],
            },
        ],
        "context_reads": ["market", "competitors", "signals"],
        "context_writes": [],
        "context_sources": ["workspace"],
        "requires_platform": None,
        "default_objective": {
            "deliverable": "Market intelligence report",
            "audience": "Leadership, strategy, and marketing teams",
            "purpose": "Synthesize market, competitive, and GTM signals into a single intelligence brief",
            "format": "Comprehensive report with data visualizations and competitive matrices",
        },
        "default_deliverable": {
            "output": {"format": "html", "word_count": "3000-5000", "layout": ["Executive Summary", "Market Overview", "Competitive Moves", "Key Players", "GTM Signals", "Opportunities & Threats", "Recommendations"]},
            "assets": [
                {"type": "chart", "subtype": "distribution", "min_count": 1, "description": "Market share or segment breakdown"},
                {"type": "chart", "subtype": "trend", "min_count": 1, "description": "Growth or signal trend data"},
                {"type": "chart", "subtype": "comparison", "min_count": 1, "description": "Competitive feature/positioning matrix"},
            ],
            "quality_criteria": [
                "Data-backed claims with recency noted",
                "Minimum 5 key players profiled",
                "Competitive moves separated from noise",
                "Clear opportunity identification with implications",
            ],
        },
    },

    "meeting-prep": {
        "display_name": "Meeting Prep",
        "description": "One-page brief before a meeting — who you're meeting, relevant context from your workspace, and talking points.",
        "output_kind": "produces_deliverable",
        "default_delivery": "email",
        "registry_default_team": ["tracker", "writer"],
        # ADR-166: meeting-prep has clear completion (the meeting happens), so it's
        # goal-shaped, not reactive. User triggers, TP orchestrates to a deliverable.
        "default_mode": "goal",
        "default_schedule": "on-demand",
        "output_format": "html",
        "surface_type": "report",
        "page_structure": [
            {"kind": "narrative", "title": "Context",
             "reads_from": ["relationships/*/profile.md"]},
            {"kind": "timeline", "title": "Interaction History",
             "reads_from": ["relationships/*/profile.md"]},
            {"kind": "checklist", "title": "Agenda & Talking Points",
             "reads_from": ["relationships/*/profile.md", "signals/_tracker.md"]},
            {"kind": "callout", "title": "Open Items",
             "reads_from": ["relationships/*/profile.md"]},
        ],
        "export_options": [],
        "process": [
            {
                "agent_type": "tracker",
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
        "display_name": "Stakeholder Report",
        "description": "Synthesizes everything happening across your workspace — market, competitors, projects, relationships — into one report.",
        "output_kind": "produces_deliverable",
        "default_delivery": "email",
        "registry_default_team": ["analyst", "writer"],
        "default_mode": "recurring",
        "default_schedule": "monthly",
        "output_format": "html",
        "surface_type": "deck",
        "page_structure": [
            {"kind": "narrative", "title": "Opening",
             "reads_from": ["workspace/context/_shared/IDENTITY.md"]},
            {"kind": "metric-cards", "title": "Key Metrics",
             "reads_from": ["market/overview.md", "projects/status.md"],
             "assets": [{"type": "derivative", "render": "chart"}]},
            {"kind": "trend-chart", "title": "Progress",
             "reads_from": ["projects/*/status.md"],
             "assets": [{"type": "derivative", "render": "chart"}]},
            {"kind": "status-matrix", "title": "Workstream Status",
             "reads_from": ["projects/*/status.md"]},
            {"kind": "entity-grid", "title": "Competitive Landscape",
             "reads_from": ["competitors/landscape.md"],
             "assets": [{"type": "root", "pattern": "competitors/assets/*-favicon.png"}]},
            {"kind": "narrative", "title": "Forward Look",
             "reads_from": ["projects/status.md", "signals/_tracker.md"]},
        ],
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

    "daily-update": {
        "display_name": "Daily Update",
        "description": "Morning briefing on what your agents did, what changed, and what's coming up.",
        "output_kind": "produces_deliverable",
        "default_delivery": "email",
        "registry_default_team": ["analyst", "writer"],
        "default_mode": "recurring",
        "default_schedule": "daily",
        "output_format": "html",
        "surface_type": "digest",
        "page_structure": [
            {"kind": "callout", "title": "Top Priority",
             "reads_from": ["signals/_tracker.md"]},
            {"kind": "timeline", "title": "What Happened",
             "reads_from": ["signals/_tracker.md"]},
            {"kind": "entity-grid", "title": "What Changed",
             "reads_from": ["competitors/landscape.md", "market/overview.md",
                            "projects/status.md", "relationships/portfolio.md"]},
            {"kind": "checklist", "title": "What's Next",
             "reads_from": ["projects/*/status.md"]},
        ],
        "export_options": [],
        "process": [
            {
                "agent_type": "executive",
                "step": "daily-digest",
                "instruction": STEP_INSTRUCTIONS["daily-digest"],
            },
        ],
        "context_reads": ["competitors", "market", "projects", "relationships", "signals"],
        "context_writes": [],
        "context_sources": ["workspace"],
        "requires_platform": None,
        "default_objective": {
            "deliverable": "Daily workspace update",
            "audience": "You — quick morning scan",
            "purpose": "Stay informed about what your agents did and what's coming up",
            "format": "Scannable digest under 60 seconds",
        },
        "default_deliverable": {
            "output": {"format": "html", "word_count": "300-600", "layout": ["What Happened", "What Changed", "What's Next"]},
            "assets": [],
            "quality_criteria": [
                "Scannable in under 60 seconds",
                "Lead with what's new, skip what didn't change",
                "Bullet points, not paragraphs",
                "If nothing happened, say so briefly",
            ],
        },
    },

    "project-status": {
        "display_name": "Project Status",
        "description": "Status report per workstream — progress, blockers, and next steps.",
        "output_kind": "produces_deliverable",
        "default_delivery": "email",
        "registry_default_team": ["tracker", "writer"],
        "default_mode": "recurring",
        "default_schedule": "weekly",
        "output_format": "html",
        "surface_type": "dashboard",
        "page_structure": [
            {"kind": "metric-cards", "title": "Status Summary",
             "reads_from": ["projects/status.md"]},
            {"kind": "status-matrix", "title": "Workstream Health",
             "reads_from": ["projects/*/status.md"]},
            {"kind": "timeline", "title": "Blockers & Risks",
             "reads_from": ["projects/*/status.md", "signals/_tracker.md"]},
            {"kind": "checklist", "title": "Next Week Priorities",
             "reads_from": ["projects/*/status.md"]},
        ],
        "export_options": [],
        "process": [
            {
                "agent_type": "tracker",
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
        "display_name": "Content Draft",
        "description": "Turns your accumulated research into a content draft — blog post, article, or brief.",
        "output_kind": "produces_deliverable",
        "default_delivery": "email",
        "registry_default_team": ["researcher", "writer"],
        "default_mode": "goal",
        "default_schedule": "on-demand",
        "output_format": "html",
        "surface_type": "report",
        "page_structure": [
            {"kind": "narrative", "title": "Brief Overview",
             "reads_from": ["content_research/*/research.md"]},
            {"kind": "callout", "title": "Key Messages",
             "reads_from": ["content_research/*/research.md"]},
            {"kind": "narrative", "title": "Draft Content",
             "reads_from": ["content_research/*/research.md", "competitors/landscape.md"]},
            {"kind": "data-table", "title": "Sources",
             "reads_from": ["content_research/*/research.md"]},
        ],
        "export_options": ["pdf"],
        "process": [
            {
                "agent_type": "writer",
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
            "assets": [
                {"type": "image", "subtype": "hero", "min_count": 1, "description": "Topic-relevant header image (16:9, editorial style)"},
            ],
            "quality_criteria": [
                "Audience-appropriate tone and depth",
                "Clear key messages",
                "Draft ready for light editing",
                "Hero image relevant to topic, not decorative filler",
            ],
        },
    },

    "launch-material": {
        "display_name": "Launch Material",
        "description": "Launch-ready content — announcements, press materials, and GTM copy built from your research.",
        "output_kind": "produces_deliverable",
        "default_delivery": "email",
        "registry_default_team": ["researcher", "writer", "designer"],
        "default_mode": "goal",
        "default_schedule": "on-demand",
        "output_format": "html",
        "surface_type": "deck",
        "page_structure": [
            {"kind": "narrative", "title": "Launch Summary",
             "reads_from": ["content_research/*/research.md", "market/overview.md"]},
            {"kind": "callout", "title": "Key Messages",
             "reads_from": ["content_research/*/research.md", "competitors/landscape.md"]},
            {"kind": "entity-grid", "title": "Target Audiences",
             "reads_from": ["content_research/*/research.md", "relationships/portfolio.md"]},
            {"kind": "checklist", "title": "Deliverables Checklist",
             "reads_from": ["content_research/*/research.md"]},
            {"kind": "timeline", "title": "Launch Timeline",
             "reads_from": ["projects/status.md"],
             "assets": [{"type": "derivative", "render": "mermaid"}]},
        ],
        "export_options": ["pdf"],
        "process": [
            {
                "agent_type": "writer",
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

    # ADR-166: gtm-report DELETED — merged into market-report. Both read the same
    # three context domains (competitors, market, signals) and serve overlapping
    # leadership/strategy/marketing audiences. One report, broader sections.

    # ══════════════════════════════════════════════════════════════════════════
    # WORKSPACE INTELLIGENCE — ADR-204
    # Essential task seeded at workspace init (Phase 5c). Runs daily at 06:00
    # local (offset from outcome-reconciliation at 02:00 so _performance_summary.md
    # is current). output_kind=produces_deliverable so the pipeline persists
    # section partials + a rich sys_manifest.json with sections array; HTML is
    # composed on demand at surface pull time (ADR-213).
    # Owned by the Reporting agent (cross-domain synthesizer).
    # ══════════════════════════════════════════════════════════════════════════

    "maintain-overview": {
        "display_name": "Workspace Intelligence",
        "description": "Daily cockpit synthesis of accumulated workspace knowledge — domain health, entity coverage, outcome trends, and recommended actions.",
        "output_kind": "produces_deliverable",
        "default_delivery": "none",
        "registry_default_team": ["reporting"],
        "default_mode": "recurring",
        "default_schedule": "0 6 * * *",
        "output_format": "html",
        "surface_type": "dashboard",
        "page_structure": [
            {"kind": "narrative",     "title": "Workspace Synthesis"},
            {"kind": "metric-cards",  "title": "Outcome Performance"},
            {"kind": "status-matrix", "title": "Domain Health"},
            {"kind": "metric-cards",  "title": "Workforce State"},
            {"kind": "entity-grid",   "title": "Key Entities"},
            {"kind": "timeline",      "title": "Signals & Trends"},
            {"kind": "checklist",     "title": "Recommended Actions"},
        ],
        "export_options": [],
        "process": [
            {
                "agent_type": "reporting",
                "step": "workspace-intelligence",
                "instruction": STEP_INSTRUCTIONS["workspace-intelligence"],
            },
        ],
        "context_reads": ["*"],  # reads all active context domains
        "context_writes": [],
        "context_sources": ["workspace"],
        "requires_platform": None,
        "default_objective": {
            "deliverable": "Workspace Intelligence Cockpit",
            "audience": "Operator — daily Overview surface",
            "purpose": "Synthesize accumulated workspace knowledge into actionable intelligence",
            "format": "Structured HTML cockpit with workspace-appropriate sections",
        },
        # ADR-204: Full catalog-driven DELIVERABLE.md — richer than the generic builder
        # produces. build_deliverable_md_from_type() checks custom_deliverable_md first.
        "custom_deliverable_md": """# Workspace Intelligence Cockpit — Composition Contract

## Composition Intent

You are composing the Workspace Intelligence Cockpit — a daily synthesis of this workspace's
accumulated knowledge, presented as an intelligence surface for the operator.

Your output must reflect what THIS workspace actually knows. Do not produce sections for which
you have no grounded data. Every section you emit must be rooted in actual accumulated context
(domain files, entity trackers, outcome data, agent performance). An absent section is honest.
An empty section is noise.

## Available Section Catalog

Choose the subset appropriate to this workspace's current state. Use these exact titles
so the compose pipeline can assign the correct render kind.

| Title | kind | Emit when |
|-------|------|-----------|
| Workspace Synthesis | narrative | Always — 2–3 sentences on overall state |
| Outcome Performance | metric-cards | Commerce or trading platform connected + outcomes recorded |
| Domain Health | status-matrix | ≥2 context domains with entities in _tracker.md |
| Workforce State | metric-cards | ≥1 flagged agent OR ≥1 stale task (2× cadence overdue) |
| Key Entities | entity-grid | One domain dominates (≥5 entities) and warrants surfacing |
| Signals & Trends | timeline | Structural changes: new domain, entity additions, coverage shifts |
| Recommended Actions | checklist | Clear operator-actionable next steps emerge from synthesis |

Maximum 5 sections total (including Workspace Synthesis). Fewer is better if data doesn't
support more. Quality contract: every data claim must be derivable from the files you read.

## Archetype Framing Hints

**Trading workspace** (portfolio/ or trading/ domain active):
  Lead with Outcome Performance. Frame Workspace Synthesis around risk/opportunity.
  Workforce State secondary. Domain Health for instrument coverage depth.

**Commerce workspace** (customers/ or revenue/ domain active):
  Lead with Outcome Performance. Frame Workspace Synthesis around growth/churn.
  Key Entities for top products or customers if ≥5.

**Content workspace** (content_research/ or signals/ domain active):
  Lead with Domain Health. Signals & Trends for publishing cadence.
  Frame Workspace Synthesis around knowledge gaps and content opportunities.

**Multi-domain workspace** (3+ active domains, no clear vertical):
  Lead with Domain Health. Workspace Synthesis frames knowledge breadth and depth.
  Recommended Actions if clear gaps emerge across domains.

**Nascent workspace** (day-zero or near-zero entity accumulation):
  Workspace Synthesis only. Honest: "Your workspace is warming up —
  synthesis will deepen as your agents run." No empty structural sections.

## Section Suppression

Do not emit a section if the supporting data is absent or trivial.
The cockpit should be honest about what the workspace knows, not optimistic about what it will know.

## User Preferences (inferred)
<!-- Populated by feedback inference (ADR-149). Empty at creation. -->
""",
        "default_deliverable": {
            "output": {
                "format": "html",
                "word_count": "200-600",
                "layout": ["Workspace Synthesis", "domain-appropriate sections"],
            },
            "assets": [],
            "quality_criteria": [
                "Only emit sections grounded in actual accumulated data",
                "Every data claim derivable from files read — no fabrication",
                "Absent section is honest; empty section is noise",
                "Maximum 5 sections including Workspace Synthesis",
                "Archetype framing reflects the operator's actual domain mix",
            ],
        },
    },

    # ══════════════════════════════════════════════════════════════════════════
    # BACK OFFICE TASKS — ADR-164
    # Owned by TP (role='thinking_partner'). Execute deterministic Python
    # functions via task_pipeline._execute_tp_task(). The executor is declared
    # in the process step's instruction field using `executor: <dotted.path>`.
    # Back office tasks scaffolded at workspace init; essential (not archivable).
    # ══════════════════════════════════════════════════════════════════════════

    "back-office-agent-hygiene": {
        "display_name": "Agent Hygiene",
        "description": "Reviews active agents daily. Pauses underperformers based on approval rate. Migrated from ADR-156 _pause_underperformers.",
        "output_kind": "system_maintenance",
        "default_delivery": "none",
        "registry_default_team": [],
        "default_mode": "recurring",
        "default_schedule": "daily",
        "output_format": "markdown",
        "export_options": [],
        "process": [
            {
                "agent_type": "thinking_partner",
                "step": "back-office",
                "instruction": (
                    "Back office maintenance: review active agents and pause "
                    "underperformers. Deterministic rule, zero LLM cost. "
                    "executor: services.back_office.agent_hygiene"
                ),
            },
        ],
        "context_reads": [],
        "context_writes": [],
        "context_sources": ["workspace"],
        "requires_platform": None,
        "default_objective": {
            "deliverable": "Agent hygiene report",
            "audience": "User (for transparency) and the system itself",
            "purpose": "Keep the workforce healthy by pausing consistently underperforming agents",
            "format": "Markdown report with observations per agent and actions taken",
        },
        "default_deliverable": {
            "output": {"format": "markdown", "word_count": "n/a", "layout": ["Summary", "Thresholds", "Observations"]},
            "assets": [],
            "quality_criteria": [
                "Every active agent observed",
                "Every action taken has a logged reason",
                "Thresholds explicit in the report",
            ],
        },
    },

    "back-office-workspace-cleanup": {
        "display_name": "Workspace Cleanup",
        "description": "Deletes expired ephemeral files from /working/ (24h TTL) and /user_shared/ (30d TTL). Migrated from ADR-119/127 scheduler block.",
        "output_kind": "system_maintenance",
        "default_delivery": "none",
        "registry_default_team": [],
        "default_mode": "recurring",
        "default_schedule": "daily",
        "output_format": "markdown",
        "export_options": [],
        "process": [
            {
                "agent_type": "thinking_partner",
                "step": "back-office",
                "instruction": (
                    "Back office maintenance: delete expired ephemeral files "
                    "per the TTL policy. Deterministic rule, zero LLM cost. "
                    "executor: services.back_office.workspace_cleanup"
                ),
            },
        ],
        "context_reads": [],
        "context_writes": [],
        "context_sources": ["workspace"],
        "requires_platform": None,
        "default_objective": {
            "deliverable": "Workspace cleanup report",
            "audience": "User (for transparency) and the system itself",
            "purpose": "Remove expired ephemeral files to keep workspace storage bounded",
            "format": "Markdown report with per-tier deletion counts",
        },
        "default_deliverable": {
            "output": {"format": "markdown", "word_count": "n/a", "layout": ["Summary", "Policy", "Results"]},
            "assets": [],
            "quality_criteria": [
                "Both tiers processed",
                "Errors logged explicitly",
                "TTL windows stated in the report",
            ],
        },
    },

    "back-office-proposal-cleanup": {
        "display_name": "Proposal Cleanup",
        "description": "Sweeps action_proposals past expires_at and marks them expired. Prevents stale pending proposals from accumulating. ADR-193 Phase 5.",
        "output_kind": "system_maintenance",
        "default_delivery": "none",
        "registry_default_team": [],
        "default_mode": "recurring",
        "default_schedule": "daily",
        "output_format": "markdown",
        "export_options": [],
        "process": [
            {
                "agent_type": "thinking_partner",
                "step": "back-office",
                "instruction": (
                    "Back office maintenance: mark pending proposals past their TTL "
                    "as expired. Deterministic SQL update, zero LLM cost. "
                    "executor: services.back_office.proposal_cleanup"
                ),
            },
        ],
        "context_reads": [],
        "context_writes": [],
        "context_sources": ["workspace"],
        "requires_platform": None,
        "default_objective": {
            "deliverable": "Proposal cleanup report",
            "audience": "User (for transparency) and the system itself",
            "purpose": "Expire stale pending proposals so the inbox stays clean and TTL semantics hold",
            "format": "Markdown report with count of expired proposals",
        },
        "default_deliverable": {
            "output": {"format": "markdown", "word_count": "n/a", "layout": ["Summary", "Results"]},
            "assets": [],
            "quality_criteria": [
                "Per-run expired count reported",
                "Errors logged explicitly",
                "Only pending proposals past expires_at are touched",
            ],
        },
    },

    "back-office-outcome-reconciliation": {
        "display_name": "Outcome Reconciliation",
        "description": "Runs every OutcomeProvider (trading, commerce, ...) and appends new rows to action_outcomes. Turns agent + proposal writes into reconciled capital outcomes. ADR-195 Phase 2.",
        "output_kind": "system_maintenance",
        "default_delivery": "none",
        "registry_default_team": [],
        "default_mode": "recurring",
        "default_schedule": "daily",
        "output_format": "markdown",
        "export_options": [],
        "process": [
            {
                "agent_type": "thinking_partner",
                "step": "back-office",
                "instruction": (
                    "Back office maintenance: reconcile capital outcomes from "
                    "platform events. Runs all registered OutcomeProviders, "
                    "inserts new rows into action_outcomes with idempotency "
                    "via provider-declared keys. Zero LLM cost (platform API "
                    "calls only). "
                    "executor: services.back_office.outcome_reconciliation"
                ),
            },
        ],
        "context_reads": [],
        "context_writes": [],
        "context_sources": ["workspace"],
        "requires_platform": None,
        "default_objective": {
            "deliverable": "Outcome reconciliation report",
            "audience": "User (for transparency) and the system itself",
            "purpose": "Keep the money-truth ledger (action_outcomes) up to date with reconciled platform events so AI reviewer, daily update, and feedback actuation have current data",
            "format": "Markdown report with per-provider insertion counts",
        },
        "default_deliverable": {
            "output": {"format": "markdown", "word_count": "n/a", "layout": ["Summary", "Per-provider results"]},
            "assets": [],
            "quality_criteria": [
                "Per-provider inserted/duplicate/invalid counts reported",
                "Provider errors surfaced without blocking siblings",
                "Disconnected platforms produce empty-result rows, not failures",
            ],
        },
    },
    "back-office-reviewer-reflection": {
        "display_name": "Reviewer Reflection",
        "description": "ADR-218: the Reviewer persona reads its own substrate (IDENTITY + principles + PRECEDENT + MANDATE + AUTONOMY + recent decisions + per-domain _performance.md) on cadence and produces a structured reflection verdict about whether its framework warrants change. Same task-assessment shape as ManageTask(evaluate) — one Haiku call, structured verdict, write-back. No DSL, no operator-authored triggers: the persona itself is the judgment that notices its own drift. Commit 2 implements invocation gate + substrate snapshot; Commits 3 + 4 add reflection-mode prompt + write-back.",
        "output_kind": "system_maintenance",
        "default_delivery": "none",
        "registry_default_team": [],
        "default_mode": "recurring",
        "default_schedule": "daily",
        "output_format": "markdown",
        "export_options": [],
        "process": [
            {
                "agent_type": "thinking_partner",
                "step": "back-office",
                "instruction": (
                    "Back office maintenance: run the Reviewer's reflection "
                    "cycle per ADR-218 + persona-reflection.md. Invocation "
                    "gate: at least one new decision since last reflection "
                    "AND at least 24h elapsed (zero LLM). If gate passes, "
                    "gather full Reviewer substrate + recent decisions + "
                    "per-domain _performance.md, invoke the persona in "
                    "reflection mode (Commit 3), and apply the structured "
                    "verdict via reflection_writer (Commit 4). "
                    "executor: services.back_office.reviewer_reflection"
                ),
            },
        ],
        "context_reads": [],
        "context_writes": [],
        "context_sources": ["workspace"],
        "requires_platform": None,
        "default_objective": {
            "deliverable": "Structured reflection verdict (no_change | narrow | relax | character_note) + evidence citations",
            "audience": "The Reviewer seat itself (evolved framework drives future verdicts) + operator (retrospective audit via reflections.md + revision chain)",
            "purpose": "Persona-as-accumulator — the Reviewer evolves its framework from its own track record, symmetric to how _performance.md accumulates money-truth. Closes the autonomous loop without operator having to re-author principles.md manually.",
            "format": "Markdown report — invocation gate verdict + evidence summary + structured proposals (when Phase B + C live)",
        },
        "default_deliverable": {
            "output": {"format": "markdown", "word_count": "n/a", "layout": ["Invocation verdict", "Evidence summary", "Proposals (if any)"]},
            "assets": [],
            "quality_criteria": [
                "Zero LLM cost when invocation gate doesn't pass",
                "Persona returning no_change is the common outcome — that's correct",
                "Every proposed change cites substrate evidence (decision count, outcome deltas, performance-md deltas)",
                "Writes revision-chained per ADR-209 with authored_by=reviewer:{occupant_identity}",
                "Never widens AUTONOMY — scope ceiling enforced in reflection_writer",
            ],
        },
    },
    "back-office-narrative-digest": {
        "display_name": "Narrative Digest",
        "description": "ADR-219 Commit 3: folds the day's housekeeping-weight narrative entries into one rolled-up material entry. Closes Axiom 9 Clause B's 'every invocation logged, weight determines visibility' commitment — the log layer stays complete, the rollup keeps the operator's chat timeline scannable. Materialized on the first housekeeping-weight narrative entry per workspace.",
        "output_kind": "system_maintenance",
        "default_delivery": "none",
        "registry_default_team": [],
        "default_mode": "recurring",
        "default_schedule": "daily",
        "output_format": "markdown",
        "export_options": [],
        "process": [
            {
                "agent_type": "thinking_partner",
                "step": "back-office",
                "instruction": (
                    "Back office maintenance: scan the past 24h of "
                    "session_messages owned by this user, group by "
                    "metadata.weight, and emit ONE material-weight rolled-up "
                    "narrative entry summarizing the housekeeping cluster. "
                    "Zero LLM cost (deterministic SQL + narrative.write_narrative_entry). "
                    "If zero housekeeping entries in window, write nothing. "
                    "executor: services.back_office.narrative_digest"
                ),
            },
        ],
        "context_reads": [],
        "context_writes": [],
        "context_sources": ["workspace"],
        "requires_platform": None,
        "default_objective": {
            "deliverable": "Daily narrative housekeeping rollup",
            "audience": "Operator (so /chat stays scannable instead of cluttered with housekeeping noise)",
            "purpose": "Preserve Axiom 9 Clause B (full invocation logging) while keeping the chat timeline legible per ADR-219 D5 weight gradient. Originals stay; one material entry summarizes the cluster.",
            "format": "Markdown report — counts by weight, list of housekeeping summaries, rollup status",
        },
        "default_deliverable": {
            "output": {"format": "markdown", "word_count": "n/a", "layout": ["Window", "Counts", "Housekeeping summaries", "Rollup status"]},
            "assets": [],
            "quality_criteria": [
                "Zero LLM cost on every run",
                "Empty-state when no housekeeping entries — does not emit a noisy 'nothing happened' rollup",
                "Rolled-up entry carries metadata.rolled_up_count + rolled_up_ids so frontend (Commit 5) can render expand-to-list",
                "Idempotent — re-running over the same window produces the same output (counts deterministic)",
            ],
        },
    },
    "back-office-reviewer-calibration": {
        "display_name": "Reviewer Calibration",
        "description": "Rebuilds /workspace/review/calibration.md from decisions.md × reconciled _performance.md. Closes the money-truth → future-judgment loop per FOUNDATIONS Axiom 7 + Axiom 8. ADR-211 D6.",
        "output_kind": "system_maintenance",
        "default_delivery": "none",
        "registry_default_team": [],
        "default_mode": "recurring",
        "default_schedule": "daily",
        "output_format": "markdown",
        "export_options": [],
        "process": [
            {
                "agent_type": "thinking_partner",
                "step": "back-office",
                "instruction": (
                    "Back office maintenance: rebuild the Reviewer seat's "
                    "calibration.md from decisions.md × reconciled outcomes. "
                    "Zero LLM cost (filesystem reads + deterministic "
                    "aggregation). Runs after back-office-outcome-reconciliation "
                    "so _performance.md is fresh. "
                    "executor: services.back_office.reviewer_calibration"
                ),
            },
        ],
        "context_reads": [],
        "context_writes": [],
        "context_sources": ["workspace"],
        "requires_platform": None,
        "default_objective": {
            "deliverable": "Reviewer calibration trail",
            "audience": "AI occupants of the Reviewer seat (prior context) and the operator (rotation + modes tuning decisions)",
            "purpose": "Keep /workspace/review/calibration.md current so the seat's judgment quality is measured against money-truth rather than asserted. Enables seat interchangeability (Principle 14) to be evidence-based.",
            "format": "Markdown with YAML frontmatter — rolling 7d/30d/90d aggregates per occupant × verdict category",
        },
        "default_deliverable": {
            "output": {"format": "markdown", "word_count": "n/a", "layout": ["Summary", "Per-window aggregates"]},
            "assets": [],
            "quality_criteria": [
                "Decisions parsed count reported",
                "Per-occupant verdict tallies (approve / reject / defer) in all three windows",
                "Idempotent rebuild — no drift between consecutive runs with identical decisions",
                "Missing decisions.md / empty file produces an empty-state report, not a failure",
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


def delivery_requires_approval(type_key: str) -> bool:
    """ADR-202 §3: whether distribution gates on operator cockpit approval.

    When True, the compose pipeline writes the output to
    `/tasks/{slug}/outputs/{date}/` and marks `pending_distribution: true`
    in `sys_manifest.json`. Distribution fires only after the operator
    clicks "Ship now" in the cockpit Work surface (ADR-202 Phase 3
    frontend UX).

    When False (default for every existing task type): distribution
    fires immediately per the task's schedule — standard recurring
    behavior. Operator sees outputs on the cockpit surface but doesn't
    gate delivery.

    Opt in per-task-type by adding `"delivery_requires_approval": True`
    to the task-type dict. Use for high-stakes tasks (one-off reports
    to external stakeholders, campaign sends to subscriber lists) where
    the operator wants to audit the composed output before the ship.
    """
    task_type = TASK_TYPES.get(type_key)
    if not task_type:
        return False
    return bool(task_type.get("delivery_requires_approval", False))


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


def list_task_types(output_kind: str | None = None) -> list[dict[str, Any]]:
    """List task types, optionally filtered by output_kind (ADR-166).

    Args:
        output_kind: Filter by output_kind. One of:
            accumulates_context | produces_deliverable | external_action | system_maintenance
    """
    result = []
    for key, definition in TASK_TYPES.items():
        if output_kind and definition.get("output_kind") != output_kind:
            continue
        result.append({"type_key": key, **definition})
    # ADR-166: order by output_kind then display name
    kind_order = {
        "accumulates_context": 0,
        "produces_deliverable": 1,
        "external_action": 2,
        "system_maintenance": 3,
    }
    result.sort(key=lambda t: (kind_order.get(t.get("output_kind"), 99), t["display_name"]))
    return result


def get_process_agent_types(type_key: str) -> list[str]:
    """Return ordered list of agent types needed for a task type's process."""
    task_type = TASK_TYPES.get(type_key)
    if not task_type:
        return []
    return [step["agent_type"] for step in task_type["process"]]


def validate_process(type_key: str) -> list[str]:
    """Validate that all agent types in the process exist in ALL_ROLES."""
    task_type = TASK_TYPES.get(type_key)
    if not task_type:
        return [f"Unknown task type: {type_key}"]
    errors = []
    for i, step in enumerate(task_type["process"]):
        agent_type = step["agent_type"]
        if agent_type not in ALL_ROLES:
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
    team_override: list[str] | None = None,
) -> str | None:
    """Build TASK.md content from a task type definition.

    ADR-152: Serializes ALL runtime config into TASK.md — context_reads,
    context_writes, output_category, process steps. Pipeline reads TASK.md
    at runtime, not the registry.

    ADR-176 Decision 2: team_override is TP's judgment on team composition.
    When provided, it replaces registry_default_team in both the ## Team section
    and the ## Process step agent labels. agent_slugs (resolved from roster by role)
    are re-mapped to match team_override roles before writing ## Process.
    """
    task_type = TASK_TYPES.get(type_key)
    if not task_type:
        return None

    # ADR-205 chat-first triggering: an explicit None (not just falsy) means
    # "no cadence — run now, schedule may be added later." We write "on-demand"
    # so TASK.md reflects the truth instead of the registry's default cadence.
    if schedule is None:
        effective_schedule = "on-demand"
    else:
        effective_schedule = schedule or task_type["default_schedule"]
    # Caller-supplied delivery takes precedence; registry default_delivery is the fallback.
    # This ensures produces_deliverable tasks get email by default without the caller
    # (TP or workspace_init) having to know the delivery policy.
    effective_delivery = delivery if delivery is not None else task_type.get("default_delivery", "none")
    objective = task_type["default_objective"]

    deliverable_text = objective["deliverable"]
    purpose_text = objective["purpose"]
    if focus:
        deliverable_text = f"{deliverable_text} — {focus}"
        purpose_text = f"{purpose_text} (focus: {focus})"

    # ADR-176 Decision 2: if TP provided a team_override, re-resolve agent slugs
    # from that list so ## Process reflects TP's composition judgment, not just
    # the registry default. team_override is a list of role keys — we map each
    # process step's position to the matching role in order.
    effective_agent_slugs = agent_slugs
    if team_override and agent_slugs is not None:
        # Build role→slug map from the resolved roster slugs + registry process steps
        registry_steps = task_type.get("process", [])
        role_to_slug: dict[str, str] = {}
        for i, step in enumerate(registry_steps):
            if agent_slugs and i < len(agent_slugs) and agent_slugs[i]:
                role_to_slug[step["agent_type"]] = agent_slugs[i]
        # Remap: for each step, use the override role at that position if available
        remapped: list[str] = []
        for i, step in enumerate(registry_steps):
            override_role = team_override[i] if i < len(team_override) else step["agent_type"]
            slug_for_role = role_to_slug.get(override_role) or role_to_slug.get(step["agent_type"]) or override_role
            remapped.append(slug_for_role)
        effective_agent_slugs = remapped

    # Build process section
    process_lines = []
    for i, step in enumerate(task_type["process"]):
        agent_label = effective_agent_slugs[i] if effective_agent_slugs and i < len(effective_agent_slugs) else step["agent_type"]
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

    # ADR-166: **Class:** → **Output:** (output_kind, 4-value enum)
    # ADR-170: **Surface:** for produces_deliverable tasks (visual paradigm)
    output_kind = task_type.get("output_kind", "produces_deliverable")
    surface_line = ""
    if output_kind == "produces_deliverable" and task_type.get("surface_type"):
        surface_line = f"\n**Surface:** {task_type['surface_type']}"

    # ADR-176 Decision 2: ## Team section — TP's judgment takes precedence over registry default.
    # team_override is TP's explicit composition decision; registry_default_team is the fallback.
    effective_team = team_override if team_override else task_type.get("registry_default_team", [])
    team_section = ""
    if effective_team:
        team_lines = "\n".join(f"- {role}" for role in effective_team)
        team_section = f"\n## Team\n{team_lines}\n"

    md = f"""# {title}

**Slug:** {slug}
**Type:** {type_key}
**Output:** {output_kind}
**Mode:** {effective_mode}
**Schedule:** {effective_schedule}
**Delivery:** {effective_delivery}
**Context Reads:** {', '.join(context_reads) if context_reads else 'none'}
**Context Writes:** {', '.join(context_writes) if context_writes else 'none'}
**Sources:** {sources_str}{surface_line}

## Objective
- **Deliverable:** {deliverable_text}
- **Audience:** {objective['audience']}
- **Purpose:** {purpose_text}
- **Format:** {objective['format']}

## Process
{chr(10).join(process_lines)}
{team_section}
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

    # ADR-204: Task types can declare a full custom DELIVERABLE.md template
    # when the generic builder's output is insufficient (e.g. catalog-driven tasks).
    custom = task_type.get("custom_deliverable_md")
    if custom:
        return custom

    deliverable = task_type.get("default_deliverable")
    if not deliverable:
        return None

    objective = task_type.get("default_objective", {})
    output = deliverable.get("output", {})
    assets = deliverable.get("assets", [])
    criteria = deliverable.get("quality_criteria", [])
    # ADR-166: task_class → output_kind, 4-value enum
    output_kind = task_type.get("output_kind", "produces_deliverable")

    if output_kind == "accumulates_context":
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

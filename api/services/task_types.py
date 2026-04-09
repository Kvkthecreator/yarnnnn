"""
Task Type Registry — ADR-152 + ADR-154 + ADR-166: Atomic Task Types

Each task type has one `output_kind` (ADR-166) describing what shape of work
the task produces. Four values:

  accumulates_context  — Writes to a workspace context domain. No user-visible
                         artifact this run. (track-*, *-digest, research-topics)
  produces_deliverable — Writes a user-visible output to /tasks/{slug}/outputs/.
                         (daily-update, *-brief, *-report, *-prep, *-update)
  external_action      — Takes an action on an external platform via API write.
                         (slack-respond, notion-update)
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

Version: 6.0 (2026-04-08 — ADR-166 registry coherence pass)
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

Canonical docs:
  - docs/architecture/registry-matrix.md
  - docs/adr/ADR-166-registry-coherence-pass.md
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

    # ADR-158: Platform-specific digest instructions
    "slack-digest": (
        "You are the Slack Bot. Your job is to read selected Slack channels and "
        "write per-channel observation files to your context domain.\n\n"
        "IMPORTANT: Check your Execution Awareness for a ## Next Cycle Directive. "
        "If one exists, follow it — it was written by you while context was fresh.\n\n"
        "For EACH selected channel:\n"
        "1. Read recent messages using your Slack tools\n"
        "2. Extract: decisions made, action items assigned, key discussions, FYIs\n"
        "3. Write findings to your context domain: WriteFile(scope='context', "
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

    # ADR-158 Phase 3: Write-back task instructions
    "slack-respond": (
        "You are the Slack Bot. Your job is to post a message to a specific Slack "
        "channel or the user's DM based on the task objective.\n\n"
        "IMPORTANT: Check your Execution Awareness for a ## Next Cycle Directive. "
        "If one exists, follow it.\n\n"
        "Steps:\n"
        "1. Read relevant context from your domain (/workspace/context/slack/) "
        "and other workspace context as needed\n"
        "2. Compose the message according to the objective and output spec\n"
        "3. Send using platform_slack_send_message with the target channel_id\n\n"
        "Message rules:\n"
        "- Keep messages concise and scannable — Slack is not a document surface\n"
        "- Use bullet points, not paragraphs\n"
        "- Attribution: name sources when referencing workspace context\n"
        "- Tone: match the channel's communication style\n\n"
        "Your output: confirmation of what was sent and where."
    ),

    "notion-update": (
        "You are the Notion Bot. Your job is to update or comment on a specific "
        "Notion page based on the task objective.\n\n"
        "IMPORTANT: Check your Execution Awareness for a ## Next Cycle Directive. "
        "If one exists, follow it.\n\n"
        "Steps:\n"
        "1. Read the target Notion page using your Notion tools\n"
        "2. Read relevant workspace context as needed\n"
        "3. Compose the update or comment according to the objective\n"
        "4. Post using platform_notion_create_comment with the target page_id\n\n"
        "Update rules:\n"
        "- Preserve existing page structure — don't restructure\n"
        "- Use Notion-native formatting (toggles, callouts, tables)\n"
        "- Link related pages rather than duplicating content\n"
        "- Keep updates focused — one update per objective\n\n"
        "Your output: confirmation of what was posted and where."
    ),

    "github-digest": (
        "You are the GitHub Bot. Your job is to read selected GitHub repositories "
        "and write per-repo observation AND reference files to your context domain.\n\n"
        "IMPORTANT: Check your Execution Awareness for a ## Next Cycle Directive. "
        "If one exists, follow it — it was written by you while context was fresh.\n\n"
        "For EACH selected repository, write FOUR files:\n\n"
        "**1. Temporal — latest.md** (issues/PRs activity, update every cycle):\n"
        "   - Read recent issues and PRs using platform_github_get_issues\n"
        "   - Identify: new issues opened, PRs merged/reviewed/stalled\n"
        "   - WriteFile(scope='context', domain='github', path='{owner}/{repo}/latest.md')\n\n"
        "**2. Reference — readme.md** (what the project is, update if changed):\n"
        "   - Read README using platform_github_get_readme\n"
        "   - Write a summary (NOT the full README): what the project does, key features, target audience\n"
        "   - WriteFile(scope='context', domain='github', path='{owner}/{repo}/readme.md')\n"
        "   - Skip if README hasn't changed since last cycle (check Execution Awareness)\n\n"
        "**3. Reference — releases.md** (what shipped, update every cycle):\n"
        "   - Read recent releases using platform_github_get_releases\n"
        "   - WriteFile(scope='context', domain='github', path='{owner}/{repo}/releases.md')\n\n"
        "**4. Reference — metadata.md** (repo identity, update weekly or on first run):\n"
        "   - Read repo metadata using platform_github_get_repo_metadata\n"
        "   - Include: description, topics, language, stars, license, tech stack\n"
        "   - WriteFile(scope='context', domain='github', path='{owner}/{repo}/metadata.md')\n"
        "   - Skip on subsequent daily cycles unless it's a weekly refresh\n\n"
        "Summarization rules:\n"
        "- Preserve attribution: 'Alice opened #123' not 'an issue was opened'\n"
        "- Group by repo when tracking multiple repos\n"
        "- Highlight: stale PRs (>7 days without review), blocked issues, release blockers\n"
        "- Skip: bot-generated PRs (dependabot, renovate) unless they fail\n"
        "- For external/competitor repos: focus on what they shipped and what it signals\n\n"
        "Also append a dated signal entry to /workspace/context/signals/ with "
        "a one-line summary per repo of what was notable.\n\n"
        "Your output: an activity + reference digest across all observed repositories."
    ),

    "notion-digest": (
        "You are the Notion Bot. Your job is to read selected Notion pages and "
        "write per-page observation files to your context domain.\n\n"
        "IMPORTANT: Check your Execution Awareness for a ## Next Cycle Directive. "
        "If one exists, follow it — it was written by you while context was fresh.\n\n"
        "For EACH selected page/database:\n"
        "1. Read the page using your Notion tools\n"
        "2. Identify: what changed since last observation, new content, stale sections\n"
        "3. Write findings to your context domain: WriteFile(scope='context', "
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
        "description": "Research and maintain intelligence on competitors — products, pricing, funding, strategy.",
        "output_kind": "accumulates_context",
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
        "description": "Research and maintain intelligence on market segments, sizing, trends, and opportunities.",
        "output_kind": "accumulates_context",
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
        "description": "Maintain contact profiles, interaction history, and relationship health from platform signals.",
        "output_kind": "accumulates_context",
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
        "output_kind": "accumulates_context",
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
        "output_kind": "accumulates_context",
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
        "output_kind": "accumulates_context",
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
        "output_kind": "accumulates_context",
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

    "github-digest": {
        "display_name": "GitHub Digest",
        "description": "Read selected GitHub repos. Track issues, PRs, and activity. Write per-repo observations.",
        "output_kind": "accumulates_context",
        "default_mode": "recurring",
        "default_schedule": "daily",
        "output_format": "html",
        "layout_mode": "digest",
        "export_options": [],
        "process": [
            {
                "agent_type": "github_bot",
                "step": "github-digest",
                "instruction": STEP_INSTRUCTIONS["github-digest"],
            },
        ],
        "context_reads": ["github", "signals"],
        "context_writes": ["github", "signals"],
        "context_sources": ["platforms"],
        "requires_platform": "github",
        "default_objective": {
            "deliverable": "GitHub activity digest",
            "audience": "You and your team",
            "purpose": "Track issues, PRs, and repository activity",
            "format": "Scannable digest with attribution",
        },
        "default_deliverable": {
            "output": {"format": "html", "word_count": "500-1500", "layout": ["Issues", "Pull Requests", "Activity Summary"]},
            "assets": [],
            "quality_criteria": [
                "Issues and PRs attributed to authors",
                "Stale PRs (>7 days) flagged",
                "Skip bot-generated PRs unless they fail",
            ],
        },
    },

    # ── Platform Write-Back Tasks (ADR-158 Phase 3: bot-initiated delivery) ──
    # Bots can write back to their platform — distinct from digest (read) tasks.
    # Write-back is intentional delivery, not observation.

    "slack-respond": {
        "display_name": "Slack Post",
        "description": "Post a message to a Slack channel or DM. Composes from workspace context and delivers via Slack.",
        "output_kind": "external_action",
        "default_mode": "reactive",
        "default_schedule": "on-demand",
        "output_format": "text",
        "layout_mode": "message",
        "export_options": [],
        "process": [
            {
                "agent_type": "slack_bot",
                "step": "slack-respond",
                "instruction": STEP_INSTRUCTIONS["slack-respond"],
            },
        ],
        "context_reads": ["slack", "signals"],
        "context_writes": [],
        "context_sources": ["platforms", "workspace"],
        "requires_platform": "slack",
        "default_objective": {
            "deliverable": "Slack message",
            "audience": "Channel participants",
            "purpose": "Deliver workspace intelligence to Slack",
            "format": "Concise Slack message with bullet points",
        },
        "default_deliverable": {
            "output": {"format": "text", "word_count": "50-300", "layout": ["Key Points", "Context"]},
            "assets": [],
            "quality_criteria": [
                "Concise and scannable — Slack is not a document surface",
                "Sources attributed when referencing workspace context",
                "Appropriate tone for the target channel",
            ],
        },
    },

    "notion-update": {
        "display_name": "Notion Update",
        "description": "Post a comment or update to a Notion page. Composes from workspace context and delivers via Notion.",
        "output_kind": "external_action",
        "default_mode": "reactive",
        "default_schedule": "on-demand",
        "output_format": "text",
        "layout_mode": "comment",
        "export_options": [],
        "process": [
            {
                "agent_type": "notion_bot",
                "step": "notion-update",
                "instruction": STEP_INSTRUCTIONS["notion-update"],
            },
        ],
        "context_reads": ["notion", "signals"],
        "context_writes": [],
        "context_sources": ["platforms", "workspace"],
        "requires_platform": "notion",
        "default_objective": {
            "deliverable": "Notion page comment or update",
            "audience": "Page collaborators",
            "purpose": "Deliver workspace intelligence to Notion",
            "format": "Structured comment with Notion formatting",
        },
        "default_deliverable": {
            "output": {"format": "text", "word_count": "100-500", "layout": ["Summary", "Details"]},
            "assets": [],
            "quality_criteria": [
                "Preserves existing page structure",
                "Uses Notion-native formatting",
                "Focused — one update per objective",
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
        "output_kind": "produces_deliverable",
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
        # ADR-166: absorbs former gtm-report. Market intelligence, competitive moves,
        # and GTM signals all roll up here — they read the same context domains and
        # the audience overlap (leadership, strategy, marketing) is total.
        "description": "Market intelligence report with segment sizing, competitive moves, GTM signals, and opportunity identification.",
        "output_kind": "produces_deliverable",
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
        "description": "Pre-meeting brief with relationship context, talking points, and open items.",
        "output_kind": "produces_deliverable",
        # ADR-166: meeting-prep has clear completion (the meeting happens), so it's
        # goal-shaped, not reactive. User triggers, TP orchestrates to a deliverable.
        "default_mode": "goal",
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
        "output_kind": "produces_deliverable",
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

    "daily-update": {
        "display_name": "Daily Update",
        "description": "Daily operational digest — what your agents did, what changed, what's coming up.",
        "output_kind": "produces_deliverable",
        "default_mode": "recurring",
        "default_schedule": "daily",
        "output_format": "html",
        "layout_mode": "email",
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
        "display_name": "Project Status Report",
        "description": "Weekly status report per workstream with progress, blockers, and next steps.",
        "output_kind": "produces_deliverable",
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
        "output_kind": "produces_deliverable",
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
        "description": "Launch announcements, press materials, and go-to-market content from accumulated research.",
        "output_kind": "produces_deliverable",
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

    # ADR-166: gtm-report DELETED — merged into market-report. Both read the same
    # three context domains (competitors, market, signals) and serve overlapping
    # leadership/strategy/marketing audiences. One report, broader sections.

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
        "default_mode": "recurring",
        "default_schedule": "daily",
        "output_format": "markdown",
        "layout_mode": "document",
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
        "default_mode": "recurring",
        "default_schedule": "daily",
        "output_format": "markdown",
        "layout_mode": "document",
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

    # ADR-166: **Class:** → **Output:** (output_kind, 4-value enum)
    md = f"""# {title}

**Slug:** {slug}
**Type:** {type_key}
**Output:** {task_type.get('output_kind', 'produces_deliverable')}
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

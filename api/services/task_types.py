"""
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
        "You are the GitHub Bot. Read selected GitHub repositories and write context files. "
        "You have a limited tool budget — be efficient.\n\n"
        "IMPORTANT: Check your Execution Awareness for a ## Next Cycle Directive. "
        "If one exists, follow it — it was written by you while context was fresh.\n\n"
        "**Every cycle — for each repo (one tool call per repo):**\n"
        "1. platform_github_get_issues(repo='owner/repo', state='open', limit=20)\n"
        "2. WriteFile: issues/PRs summary → scope='context', domain='github', "
        "path='{owner}/{repo}/latest.md'\n\n"
        "**First run or weekly refresh only (check Execution Awareness — skip if already done this week):**\n"
        "- platform_github_get_readme → summarize in readme.md (what it does, key features — NOT the full README)\n"
        "- platform_github_get_releases → releases.md (what shipped, with dates)\n"
        "- platform_github_get_repo_metadata → metadata.md (description, topics, language, stars)\n\n"
        "Summarization rules:\n"
        "- Preserve attribution: 'Alice opened #123' not 'an issue was opened'\n"
        "- Highlight: stale PRs (>7 days no review), blocked issues, release blockers\n"
        "- Skip: bot PRs (dependabot, renovate) unless they fail\n"
        "- For external/competitor repos: what shipped and what it signals\n\n"
        "After all repos: append one dated signal entry per repo to /workspace/context/signals/.\n\n"
        "Your output: a concise activity digest across observed repositories."
    ),

    # ADR-183: Commerce digest step
    "commerce-digest": (
        "You are the Commerce Bot. Your job is to read your commerce platform "
        "and write business data to your context domains.\n\n"
        "IMPORTANT: Check your Execution Awareness for a ## Next Cycle Directive. "
        "If one exists, follow it — it was written by you while context was fresh.\n\n"
        "For EACH cycle:\n"
        "1. Fetch products: platform_commerce_list_products\n"
        "2. Fetch subscribers: platform_commerce_get_subscribers\n"
        "3. Fetch revenue: platform_commerce_get_revenue\n"
        "4. Fetch customers: platform_commerce_get_customers\n"
        "5. Write revenue summary: WriteFile(scope='context', "
        "domain='revenue', path='summary.md')\n"
        "6. Write per-product performance: WriteFile(scope='context', "
        "domain='revenue', path='products/{product-slug}/performance.md') for each product\n"
        "7. Write customer tracker: WriteFile(scope='context', "
        "domain='customers', path='_tracker.md')\n\n"
        "Quantification rules:\n"
        "- All figures precise: $10,450.23 MRR, 47 active subscribers (not ~50)\n"
        "- Always include period comparison vs prior cycle when data exists\n"
        "- Highlight: churn events, new subscriber spikes, revenue milestones\n"
        "- Skip: $0 test orders, admin-generated transactions\n\n"
        "Also append a dated signal entry to /workspace/context/signals/ with "
        "key business metrics.\n\n"
        "Your output: a business activity digest with precise revenue and subscriber data."
    ),

    # ADR-183 Phase 3: Commerce write-back step instructions
    "commerce-create-product": (
        "You are the Commerce Bot. Your job is to create a new product in the "
        "user's commerce store based on the task objective.\n\n"
        "Steps:\n"
        "1. Read workspace context for product details — check the task objective "
        "for product name, description, pricing, and billing interval\n"
        "2. If a related task output exists (e.g., a report or brief to sell), "
        "read it from /tasks/ outputs to inform the product description\n"
        "3. Create the product: platform_commerce_create_product(name, description, "
        "price_cents, interval)\n"
        "4. Note: product is created as 'draft'. If the objective says to publish, "
        "call platform_commerce_update_product(product_id, status='published')\n"
        "5. Generate a checkout URL: platform_commerce_create_checkout(product_id)\n\n"
        "Product rules:\n"
        "- Description must be compelling — this is a store listing, not internal notes\n"
        "- Price should match the objective. If not specified, do NOT guess — ask via output\n"
        "- Include checkout URL in your output confirmation\n\n"
        "Your output: confirmation of the created product with ID, name, price, "
        "status, and checkout URL."
    ),

    "commerce-update-product": (
        "You are the Commerce Bot. Your job is to update an existing product in "
        "the user's commerce store based on the task objective.\n\n"
        "Steps:\n"
        "1. If you don't have the product_id, list products first: "
        "platform_commerce_list_products()\n"
        "2. Read the task objective for what to change (name, description, status)\n"
        "3. Update: platform_commerce_update_product(product_id, ...changed fields)\n\n"
        "Update rules:\n"
        "- Only change what the objective requests — don't alter unmentioned fields\n"
        "- When publishing (status='published'), verify the product has a name and price\n"
        "- When archiving, note that existing subscribers are unaffected\n\n"
        "Your output: confirmation of what was changed, with updated product details."
    ),

    "commerce-create-discount": (
        "You are the Commerce Bot. Your job is to create a discount code in the "
        "user's commerce store based on the task objective.\n\n"
        "Steps:\n"
        "1. Read the task objective for discount details: code, amount, type, scope\n"
        "2. If scoped to a product and you don't have the product_id, list products: "
        "platform_commerce_list_products()\n"
        "3. Create: platform_commerce_create_discount(name, code, amount, "
        "amount_type, product_id)\n\n"
        "Discount rules:\n"
        "- Code should be uppercase and memorable (e.g., LAUNCH20, WELCOME10)\n"
        "- Default to percent unless the objective specifies a fixed amount\n"
        "- If no product_id specified, create store-wide\n\n"
        "Your output: confirmation of the created discount with code, amount, "
        "type, and scope."
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

    # ADR-187: Trading step instructions
    "trading-digest": (
        "You are the Trading Bot. Your job is to sync your trading account "
        "and market data into the workspace.\n\n"
        "IMPORTANT: Check your Execution Awareness for a ## Next Cycle Directive. "
        "If one exists, follow it — it was written by you while context was fresh.\n\n"
        "Steps:\n"
        "1. Read account status: platform_trading_get_account\n"
        "2. Read current positions: platform_trading_get_positions\n"
        "3. Read recent orders: platform_trading_get_orders\n"
        "4. For each asset on the watchlist, read market data: "
        "platform_trading_get_market_data\n"
        "5. Update portfolio/ domain:\n"
        "   - WriteFile(scope='context', domain='portfolio', path='_tracker.md') "
        "(account snapshot: equity, cash, buying power)\n"
        "   - WriteFile(scope='context', domain='portfolio', "
        "path='{ticker}/profile.md') for each open position\n"
        "   - WriteFile(scope='context', domain='portfolio', "
        "path='history/{YYYY-MM}.md') (append new executions)\n"
        "6. Update trading/ domain:\n"
        "   - WriteFile(scope='context', domain='trading', "
        "path='{ticker}/profile.md') (price + volume update)\n"
        "   - WriteFile(scope='context', domain='trading', path='_tracker.md') "
        "(freshness update per asset)\n\n"
        "Quantification rules:\n"
        "- All figures precise: $10,450.23 equity, 47.5 shares (not ~50)\n"
        "- Always include period comparison (vs last cycle)\n\n"
        "Also append a dated signal entry to /workspace/context/signals/ with "
        "key portfolio metrics.\n\n"
        "Your output: a digest of account state and market observations."
    ),

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

    "trading-execute": (
        "You are the Trading Bot. Your job is to execute trades based on "
        "approved trading signals.\n\n"
        "IMPORTANT: This task places real orders (or paper orders). "
        "Execute ONLY signals marked as approved in the signal output.\n\n"
        "Pre-check: Read the latest signal output from the trading-signal task. "
        "If no new approved signals exist since last execution, SKIP — produce "
        "a brief 'no signals to execute' output and exit.\n\n"
        "Steps:\n"
        "1. Read the latest signal output from the trading-signal task\n"
        "2. Read current positions: platform_trading_get_positions\n"
        "3. Read account status: platform_trading_get_account\n"
        "4. For each approved signal:\n"
        "   - Validate: sufficient buying power, position size within limits\n"
        "   - Execute: platform_trading_submit_order\n"
        "   - Log: WriteFile(scope='context', domain='portfolio', "
        "path='history/{YYYY-MM}.md') (append execution)\n"
        "   - Update: WriteFile(scope='context', domain='portfolio', "
        "path='{ticker}/profile.md')\n"
        "5. Update portfolio/_tracker.md with new account state\n\n"
        "Position sizing rules:\n"
        "- Never exceed 10%% of portfolio in a single position\n"
        "- Never exceed 5 open positions simultaneously\n"
        "- Always use limit orders (not market orders)\n"
        "- Set stop-loss at 5%% below entry for all new positions\n\n"
        "Daily loss limit: if portfolio drops >3%% in a day, skip remaining "
        "signals and log escalation to portfolio/_tracker.md.\n\n"
        "Your output: execution confirmation with order details."
    ),

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

    "slack-digest": {
        "display_name": "Slack Sync",
        "default_title": "Slack Sync",
        "description": "Reads your selected Slack channels and captures decisions, action items, and key discussions.",
        "output_kind": "accumulates_context",
        "default_delivery": "none",
        "registry_default_team": [],
        "default_mode": "recurring",
        "default_schedule": "daily",
        "output_format": "html",
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
        "display_name": "Notion Sync",
        "default_title": "Notion Sync",
        "description": "Reads your selected Notion pages and tracks changes, new content, and updates.",
        "output_kind": "accumulates_context",
        "default_delivery": "none",
        "registry_default_team": [],
        "default_mode": "recurring",
        "default_schedule": "daily",
        "output_format": "html",
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
        "display_name": "GitHub Sync",
        "default_title": "GitHub Sync",
        "description": "Reads your selected GitHub repos and tracks issues, PRs, and recent activity.",
        "output_kind": "accumulates_context",
        "default_delivery": "none",
        "registry_default_team": [],
        "default_mode": "recurring",
        "default_schedule": "daily",
        "output_format": "html",
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

    # ── Commerce Tasks (ADR-183: Commerce Substrate) ──

    "commerce-digest": {
        "display_name": "Commerce Sync",
        "default_title": "Commerce Sync",
        "description": "Reads your commerce platform and tracks subscribers, revenue, and product performance.",
        "output_kind": "accumulates_context",
        "default_delivery": "none",
        "registry_default_team": [],
        "default_mode": "recurring",
        "default_schedule": "daily",
        "output_format": "html",
        "export_options": [],
        "process": [
            {
                "agent_type": "commerce_bot",
                "step": "commerce-digest",
                "instruction": STEP_INSTRUCTIONS["commerce-digest"],
            },
        ],
        "context_reads": ["customers", "revenue", "signals"],
        "context_writes": ["customers", "revenue", "signals"],
        "context_sources": ["platforms"],
        "requires_platform": "commerce",
        "default_objective": {
            "deliverable": "Commerce activity digest",
            "audience": "You",
            "purpose": "Track subscribers, revenue, and product performance",
            "format": "Scannable digest with precise figures",
        },
        "default_deliverable": {
            "output": {"format": "html", "word_count": "500-1500", "layout": ["Revenue", "Subscribers", "Products", "Orders"]},
            "assets": [],
            "quality_criteria": [
                "Revenue and subscriber counts precise (not rounded)",
                "Period-over-period comparison included",
                "Churn events and new subscriber spikes highlighted",
            ],
        },
    },

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

    "slack-respond": {
        "display_name": "Slack Post",
        "description": "Posts a message to a Slack channel or DM, composed from your workspace context.",
        "output_kind": "external_action",
        "default_delivery": "none",
        "registry_default_team": ["tracker", "writer"],
        "default_mode": "reactive",
        "default_schedule": "on-demand",
        "output_format": "text",
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
        "description": "Posts a comment or update to a Notion page, composed from your workspace context.",
        "output_kind": "external_action",
        "default_delivery": "none",
        "registry_default_team": ["tracker", "writer"],
        "default_mode": "reactive",
        "default_schedule": "on-demand",
        "output_format": "text",
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

    # ── Commerce Write-Back Tasks (ADR-183 Phase 3: agent-driven commerce ops) ──
    # Commerce Bot creates/updates products and discount codes on the commerce
    # platform. Same external_action pattern as slack-respond / notion-update.

    "commerce-create-product": {
        "display_name": "Create Product",
        "description": "Creates a new product in the commerce store with pricing and description.",
        "output_kind": "external_action",
        "default_delivery": "none",
        "registry_default_team": ["commerce_bot"],
        "default_mode": "reactive",
        "default_schedule": "on-demand",
        "output_format": "text",
        "export_options": [],
        "process": [
            {
                "agent_type": "commerce_bot",
                "step": "commerce-create-product",
                "instruction": STEP_INSTRUCTIONS["commerce-create-product"],
            },
        ],
        "context_reads": ["revenue", "customers"],
        "context_writes": [],
        "context_sources": ["workspace"],
        "requires_platform": "commerce",
        "default_objective": {
            "deliverable": "Commerce product listing",
            "audience": "Potential subscribers/buyers",
            "purpose": "Create a product in the commerce store for sale",
            "format": "Product with name, description, pricing, and checkout URL",
        },
        "default_deliverable": {
            "output": {"format": "text", "word_count": "50-200", "layout": ["Confirmation"]},
            "assets": [],
            "quality_criteria": [
                "Product name is clear and descriptive",
                "Price matches the stated objective",
                "Checkout URL is included in confirmation",
            ],
        },
    },

    "commerce-update-product": {
        "display_name": "Update Product",
        "description": "Updates an existing product's name, description, or status (publish/archive).",
        "output_kind": "external_action",
        "default_delivery": "none",
        "registry_default_team": ["commerce_bot"],
        "default_mode": "reactive",
        "default_schedule": "on-demand",
        "output_format": "text",
        "export_options": [],
        "process": [
            {
                "agent_type": "commerce_bot",
                "step": "commerce-update-product",
                "instruction": STEP_INSTRUCTIONS["commerce-update-product"],
            },
        ],
        "context_reads": ["revenue"],
        "context_writes": [],
        "context_sources": ["workspace"],
        "requires_platform": "commerce",
        "default_objective": {
            "deliverable": "Updated product listing",
            "audience": "Existing and potential subscribers",
            "purpose": "Update product details or status on the commerce store",
            "format": "Confirmation of changes applied",
        },
        "default_deliverable": {
            "output": {"format": "text", "word_count": "50-150", "layout": ["Confirmation"]},
            "assets": [],
            "quality_criteria": [
                "Only requested fields were changed",
                "Updated details confirmed in output",
            ],
        },
    },

    "commerce-create-discount": {
        "display_name": "Create Discount Code",
        "description": "Creates a discount code — percentage or fixed amount, store-wide or product-scoped.",
        "output_kind": "external_action",
        "default_delivery": "none",
        "registry_default_team": ["commerce_bot"],
        "default_mode": "reactive",
        "default_schedule": "on-demand",
        "output_format": "text",
        "export_options": [],
        "process": [
            {
                "agent_type": "commerce_bot",
                "step": "commerce-create-discount",
                "instruction": STEP_INSTRUCTIONS["commerce-create-discount"],
            },
        ],
        "context_reads": ["revenue", "customers"],
        "context_writes": [],
        "context_sources": ["workspace"],
        "requires_platform": "commerce",
        "default_objective": {
            "deliverable": "Discount code",
            "audience": "Customers and prospects",
            "purpose": "Create a promotional discount code",
            "format": "Discount code with amount, type, and applicable products",
        },
        "default_deliverable": {
            "output": {"format": "text", "word_count": "30-100", "layout": ["Confirmation"]},
            "assets": [],
            "quality_criteria": [
                "Code is uppercase and memorable",
                "Amount and type match the objective",
                "Scope (store-wide or product) confirmed",
            ],
        },
    },

    # ── Trading Tasks (ADR-187: Trading Integration) ──

    "trading-digest": {
        "display_name": "Trading Sync",
        "default_title": "Trading Sync",
        "description": "Reads your trading account and market data, updates trading and portfolio context domains.",
        "output_kind": "accumulates_context",
        "default_delivery": "none",
        "registry_default_team": [],
        "default_mode": "recurring",
        "default_schedule": "daily",
        "output_format": "html",
        "export_options": [],
        "process": [
            {
                "agent_type": "trading_bot",
                "step": "trading-digest",
                "instruction": STEP_INSTRUCTIONS["trading-digest"],
            },
        ],
        "context_reads": ["trading", "portfolio"],
        "context_writes": ["trading", "portfolio"],
        "context_sources": ["platforms"],
        "requires_platform": "trading",
        "default_objective": {
            "deliverable": "Trading account and market data digest",
            "audience": "You",
            "purpose": "Track positions, market data, and portfolio state",
            "format": "Scannable digest with precise figures",
        },
        "default_deliverable": {
            "output": {"format": "html", "word_count": "500-1500", "layout": ["Account", "Positions", "Market Data"]},
            "assets": [],
            "quality_criteria": [
                "All figures precise (not rounded)",
                "Period-over-period comparison included",
                "Watchlist coverage and freshness noted",
            ],
        },
    },

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

    "trading-execute": {
        "display_name": "Trade Execution",
        "default_title": "Trade Execution",
        "description": "Executes approved trading signals via Alpaca API. Skips if no new approved signals.",
        "output_kind": "external_action",
        "default_delivery": "none",
        "registry_default_team": [],
        "default_mode": "recurring",
        "default_schedule": "daily",
        "output_format": "html",
        "export_options": [],
        "process": [
            {
                "agent_type": "trading_bot",
                "step": "trading-execute",
                "instruction": STEP_INSTRUCTIONS["trading-execute"],
            },
        ],
        "context_reads": ["portfolio"],
        "context_writes": ["portfolio"],
        "context_sources": ["workspace"],
        "requires_platform": "trading",
        "default_objective": {
            "deliverable": "Trade execution confirmation",
            "audience": "You",
            "purpose": "Execute approved signals with position sizing guardrails",
            "format": "Execution log with order details",
        },
        "default_deliverable": {
            "output": {"format": "html", "word_count": "100-500", "layout": ["Executions", "Portfolio Update"]},
            "assets": [],
            "quality_criteria": [
                "Only approved signals executed",
                "Position sizing limits enforced",
                "Order details precise (price, qty, type)",
            ],
        },
    },

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
             "reads_from": ["workspace/IDENTITY.md"]},
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

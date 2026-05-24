"""
Orchestration — Production Machinery Registry (post-LAYER-MAPPING flip, 2026-04-23)

This module is YARNNN's orchestration-layer canonical source. Per
[LAYER-MAPPING.md](../../docs/architecture/LAYER-MAPPING.md), it holds the
registries that describe *what production roles exist* and *how the
Orchestrator dispatches them*. It is explicitly NOT an Agent module —
Agents live in `api/agents/`; this is orchestration machinery they use.

Structure (post-Commit B registry split):

1. SYSTEMIC_AGENTS — systemic templates scaffolded at signup, one per
   workspace. Today: `thinking_partner` (YARNNN). **ADR-216 classification
   note (2026-04-24)**: YARNNN here is the *orchestration chat surface*,
   not a persona-bearing Agent — the registry name "SYSTEMIC_AGENTS" is
   retained as a data-compatibility constant (ADR-212 D1 enum-slug
   exception pattern). Future persona-bearing systemic Agents (Auditor,
   Advocate) will register here alongside YARNNN; the registry holds
   scaffold templates regardless of whether the entity is persona-bearing
   (judgment layer) or orchestration surface (orchestration layer). The
   Reviewer Agent's seat is substrate (`/workspace/review/`) not a template
   entry here — Reviewer default content (DEFAULT_REVIEW_*_MD below) is a
   convenience for workspace_init scaffolding, NOT a registered template.
2. PRODUCTION_ROLES — orchestration capability bundles for production
   work: researcher, analyst, writer, tracker, designer, executive (the
   Reporting synthesizer). NOT Agents. No standing intent. No fiduciary
   standing. Packaged production configurations the Orchestrator
   dispatches against.
3. CAPABILITIES — per-capability metadata (runtime, tool, platform
   connection requirement). Platform-gated capabilities (read_slack,
   write_trading, etc.) live here with `platform_connection_requirement`.
   ADR-207 P4a dissolved Platform Bots as an agent class; "platform
   integration" under LAYER-MAPPING is the union of platform-gated
   capabilities sharing a connection.
4. RUNTIMES — infrastructure registry (where compute happens).
5. PLAYBOOK_METADATA + TASK_OUTPUT_PLAYBOOK_ROUTING — which playbooks
   apply to which (role × output_kind) combinations.
6. Capability-gate helpers — capability_available() etc.

ALL_ROLES — union of SYSTEMIC_AGENTS + PRODUCTION_ROLES. Used for
"is role X known at all?" lookups that don't care about class. Not a
backward-compat shim — it answers a genuinely distinct question.

Previous `AGENT_TEMPLATES` + `AGENT_TYPES` aliases (pre-Commit B) are DELETED.
No dual paths. Callers route to SYSTEMIC_AGENTS / PRODUCTION_ROLES /
ALL_ROLES based on the question they're asking.

Scope note — Reviewer default content (DEFAULT_REVIEW_IDENTITY_MD,
DEFAULT_REVIEW_PRINCIPLES_MD, DEFAULT_REVIEW_CALIBRATION_MD) plus the
workspace-scoped DEFAULT_AUTONOMY_MD and DEFAULT_PRECEDENT_MD: these
live here as scaffold-time defaults consumed by `workspace_init.py`.
The Reviewer Agent's seat is substrate; Reviewer-specific constants are
content loaded into `/workspace/review/` at signup. DEFAULT_AUTONOMY_MD
(ADR-217) and DEFAULT_PRECEDENT_MD are operator-authored shared files
under `/workspace/context/_shared/` — loaded here for scaffold
convenience but not Reviewer-owned.
Architectural shape lives in `docs/architecture/reviewer-substrate.md`
(seat) and ADR-217 (delegation).

History: `agent_framework.py` (original) → `agent_registry.py` (audit v1)
→ `orchestration.py` (audit v2, current) → `orchestration.py`
(Commit C, next). The file's content is correct; the filename's
`agent_` prefix is dropped in Commit C now that LAYER-MAPPING makes
explicit this module has no Agent content.

Three independent axes per role/Agent (ADR-140, ADR-176):
  - Identity (AGENT.md, for Agents): name, domain, evolves with use
  - Capabilities (role's template in SYSTEMIC_AGENTS or PRODUCTION_ROLES):
    tool access, fixed at template definition
  - Recurrences (YAML declarations at natural-home paths per ADR-231): work assignments, come and go

Four agent classes:
  - specialist: universal contributor — does one thing (research, analyze, write,
    track, or design) regardless of domain. TP assembles a team from specialists
    per work intent. No pre-assigned context domain at creation.
  - synthesizer: reads across all context domains, produces cross-domain
    deliverables (e.g., daily update). Owns no domain.
  - platform-bot: owns a temporal context domain (/workspace/context/{platform}/),
    captures signals from one external platform (Slack, Notion, GitHub). Per-source
    subfolders (channel/page/repo). ADR-158: bots own their directories.
  - meta-cognitive: owns orchestration itself (attention allocation, workforce
    health, back office maintenance). Singular — only Thinking Partner.
    Two runtime modes: chat (user-present) and task (back office executor).
    ADR-164: TP as agent.

Capability split (ADR-176 Decision 4):
  - Accumulation phase (Researcher, Analyst, Writer, Tracker):
      web_search, read_workspace, search_knowledge, platform reads,
      investigate, produce_markdown. NO asset production.
  - Production phase (Designer only):
      chart, mermaid, image, video_render, compose_html.
  - TP (via RuntimeDispatch in chat mode) can invoke production capabilities
    on behalf of any task that needs visual output.

v5 (2026-04-13): ADR-176 — Work-First Universal Specialist Model.
                 6 specialists (Researcher, Analyst, Writer, Tracker, Designer,
                 Thinking Partner) + 1 synthesizer (Reporting) + 3 bots = 10 agents.
                 ICP domain-steward templates (competitive_intel, market_research,
                 business_dev, operations, marketing) deleted.

Canonical references:
  docs/adr/ADR-176-work-first-agent-model.md
  docs/adr/ADR-164-back-office-tasks-tp-as-agent.md
"""

from __future__ import annotations

from typing import Any, Optional


# =============================================================================
# Registry 1: Agent Templates — workforce roster (ADR-140)
# =============================================================================
# Pre-scaffolded at sign-up. Three classes:
#   domain-steward — owns a canonical context domain, accumulates knowledge, synthesizes
#   synthesizer    — reads across domains, produces cross-domain deliverables
#   platform-bot   — owns a temporal context domain, captures signals from one platform (ADR-158)
#
# Templates are starting points. AGENT.md is the runtime source of truth.
# Type determines capabilities (axis 2). Identity (axis 1) and tasks (axis 3)
# are independent — see ADR-140 for the three-axis model.

# =============================================================================
# Shared Playbook Content (referenced by multiple agent types)
# =============================================================================

_PLAYBOOK_RENDERING = (
    "# Rendering Playbook\n\n"
    "## Purpose\n"
    "Consistent, brand-aligned HTML output across all deliverables. "
    "Read BRAND.md for the user's specific colors and style preferences. "
    "This playbook provides professional defaults — BRAND.md overrides when specified.\n\n"
    "## Color Usage\n"
    "### Default Palette (override with BRAND.md values when available)\n"
    "- **Headings**: near-black, not pure black — `#1a1a2e` (warm dark) or BRAND primary\n"
    "- **Body text**: `#374151` (dark gray) — easier to read than black\n"
    "- **Accent/highlight**: `#3b82f6` (blue) or BRAND accent color\n"
    "- **Muted/secondary**: `#6b7280` (gray) — captions, timestamps, labels\n"
    "- **Surface/background**: `#ffffff` (white) or `#f9fafb` (light gray for cards)\n"
    "- **Borders**: `#e5e7eb` (light gray) — subtle, never heavy\n"
    "- **Success/positive**: `#10b981` — green for positive changes, metrics up\n"
    "- **Warning/negative**: `#ef4444` — red for negative changes, risks, blockers\n\n"
    "### Color Principles\n"
    "- Use accent color sparingly — headings, links, key metrics. Not backgrounds.\n"
    "- Charts should use the accent color as primary, with gray/muted for secondary series\n"
    "- Tables: alternate row backgrounds with `#f9fafb` for readability\n"
    "- Never use more than 3 colors in a single chart\n\n"
    "## Typography Hierarchy\n"
    "- **H1** (report title): 28-32px, weight 700, heading color\n"
    "- **H2** (section): 22-24px, weight 600, heading color\n"
    "- **H3** (subsection): 18-20px, weight 600, heading color\n"
    "- **Body**: 16px, weight 400, body text color, line-height 1.6\n"
    "- **Caption/label**: 13-14px, weight 400, muted color\n"
    "- **Metric value**: 36-48px, weight 700, accent color\n"
    "- **Change badge**: 14px, weight 600, green/red with pill background\n\n"
    "## Layout Rules\n"
    "- Max content width: 720px for reading, 960px for dashboards\n"
    "- Section spacing: 32-48px between major sections\n"
    "- Card padding: 24px\n"
    "- Use whitespace generously — dense reports are unreadable\n\n"
    "## Chart Styling\n"
    "- Bar/line charts: accent color primary, gray for secondary\n"
    "- Always include axis labels and a one-sentence interpretation below\n"
    "- Minimal gridlines — horizontal only, light gray\n"
    "- No chart borders, no decorative elements\n"
    "- Legend only when >1 data series\n\n"
    "## Existing Assets\n"
    "**Always check the domain's assets/ folder before generating new visuals.**\n"
    "- Entity favicons (`{slug}-favicon.png`): embed as inline icons next to company names\n"
    "  `<img src='{content_url}' width='20' height='20' style='vertical-align:middle; margin-right:6px'>`\n"
    "- Prior generated images: re-use if still relevant. Don't regenerate.\n"
    "- Charts from prior cycles: reference or update, don't recreate from scratch\n\n"
    "## Do's and Don'ts\n"
    "**Do:**\n"
    "- Use consistent heading hierarchy (never skip levels)\n"
    "- Include alt text on all images\n"
    "- Use semantic color (green = good, red = bad, blue = neutral highlight)\n"
    "- Make tables scannable: bold first column, right-align numbers\n\n"
    "**Don't:**\n"
    "- Use pure black (#000000) for text — too harsh\n"
    "- Use more than 2 fonts in one document\n"
    "- Add decorative images that don't carry information\n"
    "- Use colored backgrounds for entire sections (use for badges/pills only)\n"
    "- Center-align body text (left-align always, center only for headings/metrics)\n"
)


# =============================================================================
# PRODUCTION_ROLES — orchestration capability bundles for production work
# =============================================================================
# Per LAYER-MAPPING.md (2026-04-23), these are NOT Agents. No standing
# intent. No fiduciary relationship. They are packaged production
# configurations the Orchestrator dispatches against when a task requires
# a particular style of production (research, analysis, writing,
# tracking, visual design, synthesis).
#
# The *name* of a production role (Researcher, Writer, etc.) labels the
# bundle's content. It does not name a personified worker.
#
# Operator-scoped calibration of role output (per ADR-117 role-keyed
# style distillation at /workspace/style/{role}.md) is substrate the
# *operator* owns, not identity the role owns. The role itself does not
# accumulate; what accumulates is the operator's calibration of how that
# role's output should read.

PRODUCTION_ROLES: dict[str, dict[str, Any]] = {

    # ── Production Specialists (ADR-176, narrowed by ADR-272) ──
    # Post-ADR-272 Specialist Survival Test: one production role survives —
    # `designer`. The five dissolved roles (researcher/analyst/writer/tracker/
    # reporting — the latter was keyed "executive" historically) failed at least
    # one of: tool-surface test, output-size test, latency test. The Reviewer
    # does investigation, analysis, prose drafting, accumulation, and cross-
    # domain synthesis using its own tool surface — inline, not via dispatch.
    #
    # Designer survives because RuntimeDispatch is a tool surface the Reviewer
    # should NOT carry standing; rendered assets meaningfully crowd judgment
    # context; render latency (10-60s) would block the Reviewer's loop.

    "designer": {
        "class": "specialist",
        "domain": None,
        "display_name": "Designer",
        "tagline": "Creates visual assets — charts, diagrams, images",
        "capabilities": [
            "read_workspace", "search_knowledge",
            "chart", "mermaid", "image", "video_render", "compose_html",
        ],
        "description": "Generates visual output: charts, mermaid diagrams, images, "
                       "and composed HTML. The only specialist with production-phase "
                       "capabilities. Reads context to inform visuals; does not research "
                       "or write text deliverables.",
        "default_instructions": (
            "You are a Designer. Your job is to produce visual assets. "
            "Read the task context and relevant workspace files to understand what visuals "
            "are needed. Use RuntimeDispatch to generate charts (for data), mermaid diagrams "
            "(for relationships/flows), and images (for illustration/brand). "
            "Always check existing assets/ folders before generating — re-use is better than "
            "redundant generation. Every visual must serve a purpose: information, context, or "
            "brand presence. Never generate decorative filler."
        ),
        "methodology": {
            "_playbook-visual.md": (
                "# Visual Production Playbook\n\n"
                "## When to Use Each Visual Type\n"
                "- **Chart** (`RuntimeDispatch type='chart'`): quantitative data — trends, comparisons, distributions\n"
                "- **Mermaid** (`RuntimeDispatch type='mermaid'`): relationships, flows, org charts, timelines\n"
                "- **Image** (`RuntimeDispatch type='image'`): conceptual illustration, brand assets, cover art\n"
                "- **Video** (`RuntimeDispatch type='video'`): key findings with sequential reveal, metric recaps\n\n"
                "## Reuse Protocol\n"
                "Check the domain's assets/ folder before generating:\n"
                "- Entity favicons (`{slug}-favicon.png`): embed as inline icons next to company names\n"
                "- Prior generated images: re-use if still relevant. Don't regenerate.\n"
                "- Charts from prior cycles: reference or update, don't recreate from scratch\n\n"
                "## Chart Construction\n"
                "- Always include axis labels\n"
                "- Add a one-sentence interpretation below every chart\n"
                "- Minimal gridlines — horizontal only, light gray\n"
                "- Use accent color as primary, gray for secondary series\n"
                "- Never more than 3 colors in a single chart\n\n"
                "## Image Generation\n"
                "Prompt construction:\n"
                "1. Subject: what the image depicts\n"
                "2. Composition: 'centered', 'wide shot', 'close-up'\n"
                "3. Style preset: 'editorial', 'professional', 'minimal'\n"
                "4. Brand color (if BRAND.md specifies): 'using [accent color] as highlight'\n"
                "5. Close with: 'no text overlay, no watermarks'\n\n"
                "## Quality Gate\n"
                "- Every visual must be referenced in the text output\n"
                "- Charts need axis labels and a one-sentence interpretation\n"
                "- Generated images need alt text in the HTML\n"
                "- If a visual doesn't add information the text doesn't already convey, skip it\n"
            ),
            "_playbook-rendering.md": _PLAYBOOK_RENDERING,
        },
    },

    # ── Synthesizer (cross-domain, no owned domain) ──

    # ADR-207 P4a (2026-04-22): Platform Bots — slack_bot / notion_bot /
    # github_bot / commerce_bot / trading_bot — were deleted from the
    # registry. The underlying platform tools (platform_slack_*, etc.)
    # and their CAPABILITIES entries (read_slack / write_slack / ...)
    # survive. Any production role (researcher, analyst, writer, tracker,
    # designer) can invoke them — the capability registry's
    # platform_connection_requirement gates access at task dispatch.
    #
    # Under LAYER-MAPPING (2026-04-23): a "platform integration" is the
    # union of platform-gated capabilities sharing a connection — not a
    # separate entity-level registry. ADR-207 P4a's capability-level
    # collapse is the platform-integration primitive in this architecture.
}


# =============================================================================
# SYSTEMIC_AGENTS — Identity-bearing Agents scaffolded at workspace init
# =============================================================================
# Per LAYER-MAPPING.md (2026-04-23), these are the judgment-bearing
# Agents the system scaffolds systemically (one per workspace). Today
# holds `thinking_partner` (YARNNN, the conversational super-agent).
# Future systemic Agent archetypes (Auditor, Advocate, Custodian, etc.)
# register here.
#
# NOTE: the Reviewer Agent is systemic but does NOT register as a
# template here. The Reviewer's seat is substrate (`/workspace/review/`,
# seven canonical files per reviewer-substrate.md). Reviewer scaffold-
# time default content (DEFAULT_REVIEW_*_MD constants below) is loaded
# at workspace_init by the rotation primitive; it is not a registry
# entry in the template-lookup sense.

SYSTEMIC_AGENTS: dict[str, dict[str, Any]] = {

    # ── YARNNN (meta-cognitive Agent) ──
    #
    # ADR-164: YARNNN is an Agent. It is the single meta-cognitive Agent
    # per workspace. Its "domain" is the operator's attention allocation
    # and the workforce's health — not a segment of user work. Two
    # runtime modes share this identity:
    #   1. Chat runtime — invoked from routes/chat.py via YarnnnAgent
    #      class. Full conversation, streaming, all CHAT_PRIMITIVES.
    #   2. Maintenance runtime — invoked from invocation_dispatcher when
    #      the scheduler dispatches a back-office MAINTENANCE recurrence.
    #      Executor dotted-path declared in /workspace/_shared/back-office.yaml.
    #
    # Back office tasks (outcome-reconciliation, reviewer-calibration,
    # reviewer-reflection, narrative-digest, proposal-cleanup) are MAINTENANCE
    # shape recurrences owned by YARNNN (ADR-231 + ADR-164).
    # No separate data model — a task is a task; owner determines class.
    #
    # DB slug `thinking_partner` retained as exception (migration 142;
    # GLOSSARY exception table). Internal class enum `meta-cognitive` also
    # retained as data-compat exception (GLOSSARY Exceptions table).
    # Cockpit entity label is "System Agent" (ADR-251). In chat speaks as
    # "YARNNN" (the brand). display_name here drives API responses consumed
    # by the cockpit roster and detail surfaces.
    #
    # ADR-216 classification note (2026-04-24): YARNNN is the orchestration
    # chat surface, NOT a persona-bearing Agent. The `class: "meta-cognitive"`
    # enum string is retained as a data-compatibility slug (same Exceptions
    # pattern as `specialist` / `platform-bot` per ADR-212 D1). The entity
    # it identifies sits in the orchestration layer (Mechanism + Channel
    # axes), not in the judgment layer (Identity axis). YARNNN has no
    # workspace-authored IDENTITY file; BASE_PROMPT (platform-fixed voice)
    # is the conversational surface. Reviewer is the sole systemic
    # persona-bearing Agent (ADR-216 D3). See ADR-216 for full reframe.
    # ADR-251: cockpit label "System Agent"; Reviewer now first-class surface.

    "thinking_partner": {
        "class": "meta-cognitive",  # data-compat enum — maps to "System Agent" at display layer (ADR-251)
        "domain": None,
        "display_name": "System Agent",
        "tagline": "Executes declared work. Narrates what happened.",
        "capabilities": [
            "read_workspace", "write_workspace", "search_knowledge",
            "produce_markdown",
        ],
        "description": "The system's conversational surface. Executes declared work, "
                       "narrates what happened, surfaces what requires operator attention. "
                       "Does not hold judgment — judgment lives in the Reviewer seat.",
        "default_instructions": (
            "You are YARNNN — the orchestration surface. Your domain is the "
            "operator's workforce itself, not any segment of operator work. When "
            "dispatched as a back-office maintenance invocation, your work is "
            "declared in a recurrence YAML entry at "
            "/workspace/_shared/back-office.yaml — read the `executor:` field "
            "to find the dotted-path executor, then run it. Write a structured "
            "output summarizing what you observed and any actions taken. "
            "You never produce domain content (reports, briefs, analyses)."
        ),
        "methodology": {},
    },
}


# =============================================================================
# ALL_ROLES — union of SYSTEMIC_AGENTS + PRODUCTION_ROLES
# =============================================================================
# Used for lookups that don't care about class ("is role X known?",
# "iterate every role the system knows about"). Not a back-compat alias
# — it answers a genuinely distinct question from the per-class dicts.

ALL_ROLES: dict[str, dict[str, Any]] = {**SYSTEMIC_AGENTS, **PRODUCTION_ROLES}


# =============================================================================
# TP Orchestration Playbook — workspace-level (/workspace/_playbook.md)
# =============================================================================
# TP is infrastructure, not workforce. Its playbook lives at workspace scope,
# not under /agents/. Seeded at roster creation, evolves through user feedback.

TP_ORCHESTRATION_PLAYBOOK = """\
# Orchestration Playbook

## Work-First Principle (ADR-176)
Work exists first. Agents serve work. When a user states what they want to accomplish,
resolve team composition from the work intent — not the other way around.

## Task Decomposition
- Simple requests (single deliverable, clear audience) → assign to one or two specialists
- Complex requests (multi-source, multi-format) → Researcher first, then Analyst or Writer
- Recurring work → create task with schedule, not one-off run
- Bounded investigation → create goal-mode task with clear completion criteria

## Production-role Assignment (ADR-176 Decision 1 + ADR-212)
Work requires finding info?        → Researcher
Work requires synthesizing patterns? → Analyst
Work requires a polished deliverable? → Writer
Work requires monitoring over time? → Tracker
Work requires visual assets?        → Designer
Cross-domain summary?               → Reporting (synthesizer)

Platform access (ADR-207 P4a — capabilities, not bots):
- Platform reads/writes are capabilities on specialists — `read_slack`, `write_slack`,
  `read_notion`, `write_notion`, `read_github`, `read_commerce`, `write_commerce`,
  `read_trading`, `write_trading`. Declared on the recurrence YAML via `required_capabilities:` field.
- Gate: `capability_available(user_id, cap, client)` checks the matching
  `platform_connections` row at dispatch. Missing = fail fast with "connect X first".

## Team Composition (ADR-176 Decision 2)
TP owns full composition authority. Registry provides suggested defaults — apply judgment.

Composition criteria:
- Research task → Researcher [+ Analyst if synthesis needed]
- Recurring deliverable → Researcher + Writer [+ Analyst, Designer optional]
- Monitoring task → Tracker [+ Analyst optional]
- One-time deliverable → Researcher + Writer
- Visual output needed → add Designer
- Cross-domain synthesis → Reporting

Write team decisions into the `team:` field of the recurrence YAML declaration. Document reasoning briefly.

## Capability Discipline
- Researcher and Analyst: text and knowledge files only. Do NOT assign charts or images.
- Writer: text deliverables only. Do NOT assign RuntimeDispatch visual tasks.
- Designer: visual assets only (chart, mermaid, image, video). Add when a task needs visuals.
- Reporting: reads all domains, produces synthesis. Do NOT assign platform-specific research.

## Feedback Routing
- When user comments on output quality → WriteFile(scope="workspace", path="agents/{slug}/memory/feedback.md", content="...", mode="append") for the producing agent (ADR-235)
- When user says "too long" / "more detail" / "different format" → feedback to agent
- When user corrects orchestration → update this playbook
- Positive feedback matters too — "great charts" confirms the agent's approach

## Quality Oversight
- After task completion, check if output matches what was asked
- If user edits frequently, note patterns in agent feedback
- When an agent consistently underperforms, suggest task reassignment or team restructure
"""


# =============================================================================
# Kernel Version (ADR-292)
# =============================================================================
#
# Single version stamp for the kernel-universal seed set (the DEFAULT_*_MD
# constants below + the seed-paths map in workspace_init.py Phase 2).
#
# Bump this string whenever any kernel-universal seed constant changes
# meaningfully — e.g., tightened safety language in DEFAULT_REVIEW_PRINCIPLES_MD,
# revised TP_ORCHESTRATION_PLAYBOOK, etc. The operator-facing update flow
# (ADR-292) compares this against the workspace's recorded
# `activated_kernel_version` (MANDATE.md frontmatter) and surfaces "Kernel
# update available" when the strings differ.
#
# Format: date-stamped `YYYY-MM-DD[.N]` aligning with api/prompts/CHANGELOG.md.
# Operator-driven, not auto-computed — discipline cost is one line per kernel
# substrate change, identical to the CHANGELOG entry the change already needs.
#
# Update flow (operator-initiated, like Claude Code's `claude --update`):
#   1. Operator sees notification on Settings → Workspace surface
#   2. Operator clicks "Update kernel substrate" — invokes
#      services.substrate_reapply.reapply_platform_substrate(source="operator")
#   3. Re-apply runs against kernel-universal paths only (bundle layer
#      handled by separate per-bundle version stamp in MANIFEST.yaml)
#   4. On success, MANDATE.md frontmatter `activated_kernel_version` advances
KERNEL_VERSION = "2026-05-18.1"


# =============================================================================
# Default Workspace Files — seeded at roster scaffold time
# =============================================================================

DEFAULT_IDENTITY_MD = """\
# About Me
<!-- Identity not yet provided. -->
"""

DEFAULT_BRAND_MD = """\
# Brand
<!-- Brand not yet provided. -->
"""
# Rationale (ADR-190): Prior default populated BRAND.md with opinionated
# defaults (monochrome palette, "confident but not aggressive" tone) before
# YARNNN had any signal about the user. Under the authored-team model, brand
# emerges from inference on rich user input (uploaded docs, URLs, descriptions),
# not from a pre-committed template. The skeleton matches IDENTITY.md: empty
# until populated by `infer_first_act` or `infer_shared_context(target="brand")`.

DEFAULT_AWARENESS_MD = """\
# Awareness

<!-- TP's situational notes — shift handoff for cross-session continuity.
     Updated by TP when something meaningful changes (tasks created, priorities learned,
     context enriched). Not a health score — qualitative understanding. -->

## Current Focus
(New workspace — no prior sessions yet.)

## Tasks
(No tasks created yet.)

## Context State
(No context domains populated yet.)

## Next Steps
(Waiting for user to share who they are and what they're working on.)
"""


# DEFAULT_CONVENTIONS_MD DELETED (workspace-init refactor 2026-05-03).
# CONVENTIONS.md is program-scoped, not kernel-scoped. The kernel default was stale
# (referenced deleted /tasks/{slug}/ paths pre-ADR-231) and was never read by
# working_memory, the compact index, or any automatic context injection.
# Program bundles that need CONVENTIONS.md (e.g. alpha-trader) fork it via
# reference-workspace/ with tier:canon. Generic workspaces do not get a
# CONVENTIONS.md skeleton — the headless base prompt carries a compact inline
# summary and the full docs/architecture/workspace-conventions.md is the
# authoritative reference. See SHARED_CONTEXT_FILES in workspace_paths.py.


# =============================================================================
# Reviewer Substrate — seeded at signup (ADR-194 v2 Phase 1)
# =============================================================================
#
# Files land at /workspace/review/ and are the Reviewer layer's filesystem
# home per FOUNDATIONS v6.0 Axiom 1 (Substrate) + Axiom 2 (Identity — four cognitive layers).
#
# The Reviewer is the independent judgment seat — interchangeable between
# the human user and an AI system. These templates are the starting state
# for both. `judgment_log.md` is NOT scaffolded at signup; it is created by
# the first review write (Phase 2+).

DEFAULT_REVIEW_IDENTITY_MD = """\
<!--
OPERATOR INSTRUCTION (ADR-216 D4 + ADR-253): this file declares the PERSONA
embodied by the Reviewer seat in your workspace. The Reviewer reads this at
reasoning time and reasons AS the persona declared here.

The default below is a generic neutral skeptical baseline. To embody a
specific judgment character (Jim Simons, Warren Buffett, W. Edwards Deming,
or an original persona), OVERWRITE this file with that character's declared
priorities, reasoning style, refusal patterns, and lifecycle posture.

Identity is WHO reviews. principles.md is WHAT they check. AUTONOMY.md is
HOW MUCH authority the operator grants and WHEN the Reviewer wakes.
-->

# Review — Identity

I am the independent judgment seat for this workspace.

My verdict binds execution when AUTONOMY permits. When I approve a proposal,
it executes (within the declared ceiling). When I reject, it is rejected
unconditionally. When I defer for evidence gap, I commission the missing
substrate via directives — I do not re-propose to myself.

My seat is interchangeable across human and AI occupants. The independence
that matters is that my judgment is evaluated against ground-truth substrate
(FOUNDATIONS Axiom 8), not against agreement with the agents whose work I
judge. Execution authority does not compromise independence.

## Scope

- I review proposed external writes created by `ProposeAction`.
- I read my full CLAUDE.md-equivalent at every invocation: IDENTITY.md
  (this file), principles.md, MANDATE.md, AUTONOMY.md, and the workspace
  guide at `/workspace/_workspace_guide.md` (which declares the substrate
  topology my program ships and the ground-truth instance to read).
- I also read domain substrate as declared by the workspace guide —
  `_operator_profile.md`, `_risk.md`, the ground-truth instance file
  per Axiom 8, recent `judgment_log.md`.
- I write decisions to `judgment_log.md` — every approve / reject / defer
  with reasoning. That file is the audit trail.

## Lifecycle posture

- I wake when substrate I care about changes (per AUTONOMY.md heartbeat_triggers)
- When I defer for evidence gap, I commission the missing substrate via a
  directive — never a proposal to myself
- I do not repeat the same defer reasoning in consecutive cycles without
  issuing a new directive
- When no actionable condition exists, I stand down with one sentence
- My approve-correct rate against ground-truth substrate is the measure
  of my value

## Developmental axis

Judgment calibration — accuracy of approve/reject decisions measured by
downstream outcome attribution in the program's ground-truth substrate
(see `/workspace/_workspace_guide.md` for the instance — alpha-trader's
instance is `_money_truth.md` per ADR-195 v2).
"""


DEFAULT_REVIEW_PRINCIPLES_MD = """\
# Review — Principles

This is the declared review framework for this workspace. The Reviewer
reads this alongside `_risk.md` and the program's ground-truth substrate
(per FOUNDATIONS Axiom 8 — `/workspace/_workspace_guide.md` declares the
instance for your bundle). Edit to tune how the Reviewer reasons and what
it does when it defers.

---

## Default posture: skeptical over permissive

When in doubt, defer. Asymmetric losses deserve more scrutiny than
asymmetric gains. A proposal that looks marginal defers; one that is
clearly positive and within declared edge can approve.

## Decision categories

- **approve** — EV clearly positive AND within declared edge AND
  `auto_approve_below_cents` threshold met (see below).
- **reject** — EV clearly negative OR violates `_risk.md` OR outside
  declared strategy. Rejection is unconditional — AUTONOMY does not
  gate it.
- **defer** — EV ambiguous, high stakes, or edge case not yet in the
  ground-truth substrate. Defer always commissions missing substrate
  (see Defer posture below).

## Auto-approve threshold (ADR-253 D1)

Controls whether the Reviewer's approve verdict auto-executes.
Without this field set, every approve requires operator Queue click
regardless of AUTONOMY level.

```yaml
# auto_approve_below_cents: 0   # uncomment + set to enable AI auto-action
```

## Defer posture — what I commission when I defer for evidence gap (ADR-253 D2 amended by ADR-296 v2 D3)

When I defer because evidence is insufficient, I author cadence + standing
intent. I do not re-propose to myself, and per ADR-296 v2 D3 I do not
fire upstream recurrences by name — that is operator + cron territory.

```
# Example (override for your domain):
# When deferring because a signal has < 20 closed-loop samples:
#   directive: write_file(path="/workspace/review/standing_intent.md",
#                          content="I want to be woken when this signal
#                                   crosses 20 closed-loop samples.")
#   AND
#   Schedule(action="create", slug="reviewer-next-cycle", schedule=...,
#            prompt="Re-assess <signal> after upstream accumulation.")
#
# When deferring because ground-truth substrate is empty:
#   directive: clarify("No closed-loop outcomes exist. Approve a
#                       minimum-size seed action to begin calibration.")
```

## Directive posture — what I can instruct directly (ADR-253 D2 amended by ADR-296 v2 D3)

The Reviewer issues directives for self-substrate work (write to own
substrate, clarify to operator). Per ADR-296 v2 D3, the historical
`fire_invocation` directive is removed — Reviewer authors cadence via
Schedule, not via directive-fire of upstream recurrences. It does NOT
issue directives for external platform writes (those are proposals),
infrastructure changes, or operator configuration.

## Per-domain high-impact thresholds (ADR-195 Phase 5)

Outcomes above these amounts route to the originating task's feedback.md.
This is a principle (what you consider significant), not an autonomy gate.

<!--
commerce:
  high_impact_threshold_cents: 100000

trading:
  high_impact_threshold_cents: 50000
-->

## What the Reviewer does NOT do

- Does not enforce unstated rules.
- Does not override explicit operator approvals.
- Does not accumulate style preference (that is production-role calibration).
"""


# =============================================================================
# Phase 4 (ADR-211) — Reviewer seat substrate completion
# =============================================================================
# Four additional files at /workspace/review/ that complete the seven-file
# canonical target per reviewer-substrate.md. Scaffolded at signup via
# workspace_init.py Phase 2. See ADR-211 D1–D3 + D6 for schemas.


# DEFAULT_REVIEW_OCCUPANT_MD DELETED — the rotation primitive
# (services/review_rotation.py::_render_occupant_md) is the single source
# of truth for OCCUPANT.md content. Per ADR-211 D4 singular-implementation,
# every write to OCCUPANT.md flows through rotate_occupant(), including
# the signup scaffold in workspace_init.py.


# DEFAULT_REVIEW_MODES_MD DELETED (ADR-217, 2026-04-24). Autonomy delegation
# is the operator's standing intent about how much judgment authority the
# AI carries on their behalf — it is not Reviewer-owned config. The file
# relocated to `/workspace/context/_shared/AUTONOMY.md` as a sibling to
# MANDATE/IDENTITY/BRAND/CONVENTIONS; its default content is now
# DEFAULT_AUTONOMY_MD below. The retired schema (`autonomy_level`,
# `scope`, `on_behalf_posture`, `auto_approve_below_cents`,
# `never_auto_approve`) was absorbed and narrowed to the three-key
# AUTONOMY.md schema (`level`, `ceiling_cents`, `never_auto`) per
# ADR-217 D3 — `scope` dropped as redundant-with-domain-key,
# `on_behalf_posture` dropped as derivable-from-persona.


DEFAULT_AUTONOMY_MD = """\
# Autonomy — how I delegate judgment authority

This file is the prose documentation. The machine-parsed delegation
config lives next to it at `_autonomy.yaml` (ADR-254 + Commit F).

## What autonomy means here

Autonomy is the **delegation ceiling** for AI-rendered verdicts. When the
Reviewer approves a proposal, the dispatcher checks `_autonomy.yaml` to
decide whether the approval auto-executes or routes to the cockpit Queue
for my click. Principles in `/workspace/review/principles.md` can *narrow*
this ceiling (add defer conditions) but never *widen* it — the servant can
be more conservative than I permit, never more permissive.

## Vocabulary

**Delegation** (per `_autonomy.yaml` `default.delegation` and any
`domains.<name>.delegation`):

- `manual` — every verdict defers to me. No auto-execution.
- `bounded` — AI auto-executes within declared ceiling; defers beyond.
  Requires `ceiling_cents` to be set.
- `autonomous` — AI auto-executes every verdict within scope. No ceiling
  check. Still respects `never_auto` and the irreversibility gate.
  Reserved for low-stakes domains where I trust the persona's calibration
  fully.

**Ceiling** (`bounded` only):
- `ceiling_cents` — a notional-value threshold. Proposals whose estimated
  value (e.g. trade notional, commerce transaction amount) exceeds this
  cap defer regardless of the persona's verdict.

**Never-auto list**:
- `never_auto` — action_type substrings that always defer, even when
  under the ceiling. Use this for classes of actions where the
  consequences are categorically worse than the ceiling can express
  (e.g. cancel flows, refund flows, anything irreversible-ish).

**Pause** (set by Reviewer or operator):
- `paused_until` — ISO-8601 UTC. While non-expired, every proposal
  defers regardless of delegation. Time-based circuit breaker per
  ADR-248 D3.
- `pause_reason` — human-readable note that surfaces on the cockpit.

## How changes take effect

Changes read on the next proposal verdict. No restart, no migration.

## When to revisit

- After 20+ verdicts in a domain: review calibration.md + judgment_log.md.
  Consider raising or lowering the ceiling based on realized outcomes.
- Before connecting a live (non-paper / non-sandbox) platform: tighten
  to `manual` first; recalibrate from zero.
- After a persona change (IDENTITY.md rotation): reset to `manual` and
  recalibrate — a new persona has no track record yet.

## Schema reference

See `_autonomy.yaml` for the live config. Example shape:

    default:
      delegation: bounded
      ceiling_cents: 20000
      never_auto:
        - close_position_market
    domains:
      commerce:
        delegation: bounded
        ceiling_cents: 50000

## Naming history (for archive readers)

The field was named `level` and the value space included `assisted` +
`bounded_autonomous` from ADR-254 (2026-05-07) until Commit F (2026-05-11).
The FE wrote `level: bounded_autonomous` while the backend already read
`delegation: bounded` — the mismatch silently treated every workspace as
manual. Commit F + Migration 172 unified the schema; the legacy fields
no longer exist on disk.
"""


DEFAULT_PRECEDENT_MD = """\
# Precedent

This file records durable interpretations and boundary-case decisions
that should shape future behavior across the workspace.

Use it for decisions that are:
- broader than one task run
- narrower than a mandate or autonomy rewrite
- likely to recur
- valuable for YARNNN, the Reviewer, and domain Agents to read the same way

Do not use it for:
- one-off execution instructions
- raw notes or scratch thinking
- operator identity or brand rules
- Reviewer persona/framework content that belongs in `/workspace/review/`

## Active precedents

<!--
Create one block per durable interpretation.

### <slug>
- Scope:
- Rule:
- Why:
- Source:
- Review trigger:
- Status: active
-->

## Notes

Promote a chat decision here when it should compound.
If the decision changes what the workspace is trying to do, edit
`MANDATE.md` instead.
If it changes how much authority the AI has, edit `AUTONOMY.md` instead.
If it changes how the Reviewer reasons, edit `/workspace/review/principles.md`.
"""


# ADR-280: kernel-default workspace guide for no-program workspaces.
# Bundles ship their own _workspace_guide.md at reference-workspace/ root
# (e.g. docs/programs/alpha-trader/reference-workspace/_workspace_guide.md);
# `services.programs.fork_reference_workspace` deterministically copies it
# into the operator's workspace at activation. This constant is the kernel's
# fallback for workspaces created without a program — `workspace_init.py`
# Phase 2 writes it as one of the universal skeleton files alongside
# MANDATE/IDENTITY/BRAND/AUTONOMY/PRECEDENT.
#
# Per ADR-280 §D4 (revised 2026-05-15): the workspace guide is bundle-shipped
# substrate, not Reviewer-authored at first wake. Kernel ships universal
# defaults for the no-program case; programs ship richer guides via their
# bundle's reference-workspace/. Operators and Reviewers revise the guide
# through the normal authoring channels with proper attribution per ADR-209.
DEFAULT_WORKSPACE_GUIDE_MD = """\
---
schema_version: 1

# Path zones: kernel-universal entries only (no program activated).
# Each zone declares its role; lock policy is derived per ADR-280 §2.D2.
path_zones:
  - path: context/_shared
    role: operator-canon
    purpose: operator's standing intent — MANDATE, IDENTITY, BRAND, AUTONOMY, PRECEDENT, _preferences
  - path: context/_shared/_locks.yaml
    role: operator-canon
    purpose: operator-authored lock policy
  - path: uploads
    role: operator-canon
    purpose: operator-contributed reference material
  - path: review/IDENTITY.md
    role: operator-canon
    purpose: Reviewer seat persona declaration
  - path: review/principles.md
    role: operator-canon
    purpose: Reviewer's declared judgment framework
  - path: review/_principles.yaml
    role: operator-canon
    purpose: machine-parsed Reviewer thresholds
  - path: review/OCCUPANT.md
    role: system-ledger
    purpose: current Reviewer seat occupant
  - path: review/handoffs.md
    role: system-ledger
    purpose: append-only seat-occupant rotation log
  - path: review/calibration.md
    role: system-ledger
    purpose: per-occupant judgment-vs-outcome rolling windows
  - path: review/judgment_log.md
    role: system-ledger
    purpose: Reviewer's judgment lineage
  - path: memory/recent.md
    role: system-ledger
    purpose: back-office narrative digest (24h rollup)
  - path: review/notes.md
    role: reviewer-workbench
    purpose: Reviewer's working scratch across wakes
  - path: working
    role: reviewer-workbench
    purpose: ephemeral scratch (24h TTL)
  - path: memory
    role: running-narrative
    purpose: YARNNN orchestration accumulation
  - path: agents
    role: running-narrative
    purpose: per-agent substrate
  - path: reports
    role: running-narrative
    purpose: per-recurrence deliverable outputs
  - path: operations
    role: running-narrative
    purpose: per-recurrence action state
  - path: research
    role: running-narrative
    purpose: investigation working space (Reviewer creates subdirs as work demands)
  - path: _recurrences.yaml
    role: kernel-index
    purpose: scheduling-index source of truth

reviewer_wake_envelope:
  - key: identity_md
    path: review/IDENTITY.md
    optional: false
  - key: principles_md
    path: review/principles.md
    optional: false
  - key: precedent_md
    path: context/_shared/PRECEDENT.md
    optional: true
  - key: mandate_md
    path: context/_shared/MANDATE.md
    optional: false
  - key: autonomy_md
    path: context/_shared/AUTONOMY.md
    optional: false
  - key: preferences_yaml
    path: context/_shared/_preferences.yaml
    optional: true

locks:
  add: []
  remove: []
---

# Workspace Guide

This is your workspace guide. The Reviewer reads it at every wake to
understand what substrate exists in this workspace and how to navigate
it. The frontmatter (machine-parsed) declares path zones and their roles;
this prose body narrates the contract.

## How this workspace works

Substrate is the persistence layer (FOUNDATIONS Axiom 1). State that
survives between invocations lives in `/workspace/` files. Computation is
stateless: read substrate, act, write substrate, terminate. Substrate is
the bus over which the runtime operates.

Every write is **attributed and retained** (Authored Substrate, ADR-209)
— `authored_by` identity + short message; revisions accumulate
non-destructively; history inspectable via `ListRevisions` /
`ReadRevision` / `DiffRevisions`.

The path zones declared in this guide's frontmatter are guaranteed to be
the substrate topology — readers do not need to `ListFiles` defensively
before writing within them.

**Six roles classify every path zone**:

- **`operator-canon`** — operator-authored library (locked from Reviewer).
- **`reviewer-workbench`** — Reviewer's working substrate (unlocked).
- **`system-ledger`** — infrastructure-rendered append-only (locked from LLM).
- **`world-mirror`** — external state mirrored by mechanical primitives.
- **`running-narrative`** — append-shape, mechanical or judgment-fed.
- **`kernel-index`** — kernel-managed regenerable indexes.

## What this workspace contains

This workspace runs no program — only the kernel-universal substrate is
present. The operator can activate a program (e.g., alpha-trader,
alpha-commerce) which forks a richer `_workspace_guide.md` over this
default.

Operational substrate emerges through Reviewer judgment + work over
tenure: investigation work surfaces a `research/` directory the Reviewer
populates; pattern-tracking lands in `review/notes.md`; operation-shaping
judgment moments accumulate in `review/judgment_log.md`.

## When things diverge

The guide describes the substrate topology; it does not enforce it.
Surface unclassified substrate via `Clarify`; treat it as
`running-narrative` for reading purposes; never silently classify or
relocate substrate to enforce the guide.

## What NOT to write to operator-canon

Do NOT write to `operator-canon` paths directly. The lock policy will
reject the write, but the discipline is upstream of the lock — the
operator authors their own canon, and the Reviewer's role is to surface
insight via `Clarify` / `ProposeAction` so the operator authors the
change with their own attribution.

The right home for the Reviewer's evolving understanding is
`review/notes.md` (reviewer-workbench).
"""


# DEFAULT_REVIEW_HANDOFFS_MD DELETED — the rotation primitive
# (services/review_rotation.py::_render_handoff_entry) is the single source
# of truth for handoffs.md entries. Per ADR-211 D4 singular-implementation,
# every append to handoffs.md flows through rotate_occupant().


DEFAULT_REVIEW_CALIBRATION_MD = """\
---
last_calibrated_at: null
windows: {}
---

# Review Seat — Calibration

This file is auto-generated by the `back-office-reviewer-calibration`
task. Do not edit manually — edits will be overwritten on the next
calibration cycle.

Calibration cross-references decisions in `judgment_log.md` against
outcomes reconciled in the program's ground-truth substrate per domain
(per FOUNDATIONS Axiom 8 — alpha-trader's instance is `_money_truth.md`
per ADR-195 v2; alpha-author's instance is multi-signal corpus-coherence
per ADR-283), producing rolling window summaries per occupant × verdict
category.

The loop is the ground-truth → future-judgment cycle per FOUNDATIONS
Axiom 7 (Recursion) + Axiom 8 (Ground-Truth Substrate). AI occupants read
their own calibration data as prior context for future verdicts. The
operator reads this file when deciding whether to rotate the occupant
or tune `modes.md`.

## Initial state

No calibration data yet. First generation runs after the first
`back-office-outcome-reconciliation` cycle that reconciles outcomes
for proposals with verdicts in `judgment_log.md`.
"""


# DEFAULT_ROSTER — DELETED (ADR-205 Primitive Collapse, 2026-04-22).
# Signup no longer scaffolds a pre-seeded roster. YARNNN (role=thinking_partner)
# is the sole infrastructure agent created at workspace init (workspace_init.py
# Phase 2). Specialists are lazy-created on first dispatch via
# services.agent_creation.ensure_infrastructure_agent().
#
# ADR-207 P4a (2026-04-22): Platform Bots dissolved as agent class. Platform
# capabilities (read_slack / write_trading / ...) are gated by
# capability_available() at dispatch — no bot agent row needed. OAuth
# connect/disconnect only touches `platform_connections`.
#
# ALL_ROLES above remains as the template library consulted at
# lazy-ensure time.

# PM_MODES — REMOVED (PM/project architecture dissolved)


# Legacy role → new type mapping (for DB migration / backward compat reads).
#
# ADR-272: PRODUCTION_ROLES collapsed to {designer} only. Legacy role names
# that previously resolved to researcher/analyst/writer/tracker/executive
# are REMOVED from this map. Per the existing pattern (ADR-207 P4a for
# deleted platform-bot roles), unmapped legacy roles fall through
# resolve_role()'s passthrough and then fail the ALL_ROLES lookup loudly —
# surfacing the migration need rather than silently re-routing to a
# semantically-wrong role.
#
# Surviving entries: designer (current + only specialist) + thinking_partner
# (systemic agent / chat LLM substrate).
LEGACY_ROLE_MAP: dict[str, str] = {
    # v5 current types pass through (ADR-176, narrowed by ADR-272)
    "designer": "designer",
    # ADR-164: TP as meta-cognitive agent
    "thinking_partner": "thinking_partner",
}


def resolve_role(role: str) -> str:
    """Map legacy role names to current types. Passthrough for current types."""
    if role in ALL_ROLES:
        return role
    return LEGACY_ROLE_MAP.get(role, role)


def get_agent_class_and_domain(role: str) -> tuple[str, str | None]:
    """Resolve agent role → (agent_class, context_domain).

    Returns the agent class and the owned context domain (or None for
    synthesizers and meta-cognitive). Valid classes (ADR-140 + ADR-164):
      - domain-steward  — owns a single context domain
      - synthesizer     — cross-domain composition, no owned domain
      - platform-bot    — owns a temporal platform directory
      - meta-cognitive  — TP, owns orchestration itself (no context domain)

    Falls back to "domain-steward" / None for unknown roles.
    """
    resolved = resolve_role(role)
    template = ALL_ROLES.get(resolved)
    if template:
        return template["class"], template.get("domain")
    return "domain-steward", None


# =============================================================================
# Registry 2: Capabilities — what each capability resolves to
# =============================================================================

#
# ADR-207 P3: each entry declares `platform_connection_requirement`. `None`
# means the capability is always available (internal runtime). A dict with
# `{platform, status}` means the capability only fires when a matching
# `platform_connections` row exists for the user. `capability_available()`
# enforces this at task dispatch; callers should surface a clear
# "connect {platform} first" error to the operator.

CAPABILITIES: dict[str, dict[str, Any]] = {
    # -- Cognitive (prompt-driven, no dedicated tool) --
    "summarize":         {"category": "cognitive", "runtime": "internal", "platform_connection_requirement": None},
    "detect_change":     {"category": "cognitive", "runtime": "internal", "platform_connection_requirement": None},
    "alert":             {"category": "cognitive", "runtime": "internal", "platform_connection_requirement": None},
    "cross_reference":   {"category": "cognitive", "runtime": "internal", "platform_connection_requirement": None},
    "data_analysis":     {"category": "cognitive", "runtime": "internal", "platform_connection_requirement": None},
    "investigate":       {"category": "cognitive", "runtime": "internal", "platform_connection_requirement": None},
    "produce_markdown":  {"category": "cognitive", "runtime": "internal", "platform_connection_requirement": None},

    # -- Tool-backed (internal primitives) --
    "web_search":        {"category": "tool", "runtime": "internal", "tool": "WebSearch", "platform_connection_requirement": None},
    "read_workspace":    {"category": "tool", "runtime": "internal", "tool": "ReadFile", "platform_connection_requirement": None},
    "search_knowledge":  {"category": "tool", "runtime": "internal", "tool": "QueryKnowledge", "platform_connection_requirement": None},

    # -- Platform runtime (provider-native external capabilities) --
    "read_slack": {
        "category": "tool", "runtime": "external:slack",
        "tools": ["platform_slack_list_channels", "platform_slack_get_channel_history"],
        "platform_connection_requirement": {"platform": "slack", "status": "active"},
    },
    "write_slack": {
        "category": "tool", "runtime": "external:slack",
        "tools": ["platform_slack_send_message"],
        "platform_connection_requirement": {"platform": "slack", "status": "active"},
    },
    "read_notion": {
        "category": "tool", "runtime": "external:notion",
        "tools": ["platform_notion_search", "platform_notion_get_page"],
        "platform_connection_requirement": {"platform": "notion", "status": "active"},
    },
    "write_notion": {
        "category": "tool", "runtime": "external:notion",
        "tools": ["platform_notion_create_comment"],
        "platform_connection_requirement": {"platform": "notion", "status": "active"},
    },
    "read_github": {
        "category": "tool", "runtime": "external:github",
        "tools": ["platform_github_list_repos", "platform_github_get_issues"],
        "platform_connection_requirement": {"platform": "github", "status": "active"},
    },
    # ADR-224: read/write_commerce + read/write_trading DELETED from kernel
    # CAPABILITIES. They are program-specific (commerce / trading oracle
    # shapes) and live in their respective program bundle MANIFEST.yaml
    # capabilities[] declarations:
    #   - docs/programs/alpha-trader/MANIFEST.yaml → read_trading + write_trading
    #   - docs/programs/alpha-commerce/MANIFEST.yaml → read_commerce + write_commerce
    # bundle_reader normalizes bundle capability entries to this kernel shape;
    # task_derivation._available_platform_capabilities transparently merges
    # active bundles' capabilities with the kernel set.
    #
    # NOTE: read/write_slack, read/write_notion, read_github STAY in kernel —
    # they are capability-bundle-shaped (platform integration available to
    # any program), not program-shaped. Same classification as the slack/
    # notion/ github directories per ADR-224 §1 capability-bundle-owned rule.

    # -- Asset production (compute runtimes) --
    "chart":   {
        "category": "asset", "runtime": "python_render",
        "tool": "RuntimeDispatch", "skill_docs": "chart/SKILL.md",
        "output_type": "image/png",
        "platform_connection_requirement": None,
    },
    "mermaid": {
        "category": "asset", "runtime": "python_render",
        "tool": "RuntimeDispatch", "skill_docs": "mermaid/SKILL.md",
        "output_type": "image/svg+xml",
        "platform_connection_requirement": None,
    },
    "image":   {
        "category": "asset", "runtime": "python_render",
        "tool": "RuntimeDispatch", "skill_docs": "image/SKILL.md",
        "output_type": "image/png",
        "platform_connection_requirement": None,
    },
    "video_render": {
        "category": "asset", "runtime": "python_render",
        "tool": "RuntimeDispatch", "skill_docs": "video/SKILL.md",
        "output_type": "video/mp4",
        "timeout": 180,  # extended timeout for video rendering
        "platform_connection_requirement": None,
    },

    # -- Composition (post-generation pipeline step) --
    "compose_html": {
        "category": "composition", "runtime": "python_render",
        "post_generation": True,
        "platform_connection_requirement": None,
    },

    # -- Operator-addressing (ADR-299) — capability addresses operator-identity
    # (auth.users.email for workspace owner) rather than third party / audience.
    # Distinguished by `addressee_class: "operator"` field; AUTONOMY-posture
    # "observability" (per ADR-299 D4: routes through `_preferences.yaml`
    # opt-in, NOT through should_auto_apply consequential-action gating).
    # Available to all bundle archetypes without MANIFEST declaration.
    # Wire still requires Resend connection (per ADR-192 Phase 4).
    "send_operator_email": {
        "category": "tool", "runtime": "external:email",
        "tools": ["platform_email_send_to_operator"],
        "platform_connection_requirement": {"platform": "email", "status": "active"},
        "addressee_class": "operator",
        "autonomy_posture": "observability",
    },

    # PM coordination capabilities removed — PM/project architecture dissolved
}


# =============================================================================
# Registry 3: Runtimes — where compute happens
# =============================================================================

RUNTIMES: dict[str, dict[str, Any]] = {
    "internal":       {"description": "In-process, no HTTP call"},
    "python_render":  {"description": "yarnnn-render service (Docker: Python + Node.js + Chromium + matplotlib + Remotion)"},
    "external:slack": {"description": "Slack API via user OAuth token"},
    "external:notion":{"description": "Notion API via user OAuth token"},
    "external:github":{"description": "GitHub API via user OAuth token"},
}


# =============================================================================
# Type Query Helpers
# =============================================================================

def get_type_capabilities(agent_type: str) -> list[str]:
    """Return the capability list for an agent type.

    ADR-272: PRODUCTION_ROLES collapsed to {designer}; the previous
    researcher-fallback would now crash. Unknown roles return an empty
    capability list — the caller treats this as "no special tools" rather
    than silently inheriting a wrong role's surface.
    """
    resolved = resolve_role(agent_type)
    type_def = ALL_ROLES.get(resolved)
    if not type_def:
        return []
    return type_def["capabilities"]


def has_capability(agent_type: str, capability: str) -> bool:
    """Check if an agent type has a specific capability."""
    return capability in get_type_capabilities(agent_type)


def has_asset_capabilities(agent_type: str) -> bool:
    """Check if an agent type has any asset-producing capabilities (chart, mermaid, image).

    Determines whether an agent gets SKILL.md injection and RenderAsset access.
    """
    caps = get_type_capabilities(agent_type)
    return any(
        CAPABILITIES.get(c, {}).get("category") == "asset"
        for c in caps
    )


def get_type_skill_docs(agent_type: str) -> list[str]:
    """Return skill doc paths for capabilities that have them."""
    caps = get_type_capabilities(agent_type)
    docs = []
    for c in caps:
        cap_def = CAPABILITIES.get(c, {})
        if cap_def.get("skill_docs"):
            docs.append(cap_def["skill_docs"])
    return docs


# =============================================================================
# ADR-207 P3: Capability Availability Gate
# =============================================================================

def _resolve_capability(capability_name: str) -> Optional[dict]:
    """Per ADR-224: kernel CAPABILITIES first; on miss, consult active
    program bundles. Bundle-sourced capabilities are normalized to the
    same shape via bundle_reader so dispatch helpers treat them
    identically.
    """
    cap = CAPABILITIES.get(capability_name)
    if cap is not None:
        return cap
    try:
        from services.bundle_reader import get_capability_from_bundles
        return get_capability_from_bundles(capability_name)
    except Exception:
        return None


def get_capability_requirement(capability_name: str) -> Optional[dict]:
    """Return the platform_connection_requirement for a capability, or None.

    None means: either the capability doesn't exist, or it needs no platform
    connection (internal runtime). Callers should treat unknown capabilities
    as "not available" to fail loudly on typos in the recurrence YAML.

    Per ADR-224: falls through to active program bundles' capabilities[]
    declarations for program-specific capabilities (read_trading, write_trading,
    read_commerce, write_commerce).
    """
    cap = _resolve_capability(capability_name)
    if cap is None:
        return None
    return cap.get("platform_connection_requirement")


def capability_available(user_id: str, capability_name: str, client: Any) -> bool:
    """Check whether a capability can fire for this user right now.

    Internal capabilities (no platform requirement) are always available.
    Platform-gated capabilities require an active `platform_connections`
    row matching the declared requirement.

    Unknown capability names return False — callers should surface the
    mismatch so the operator can correct the recurrence YAML declaration.

    Per ADR-224: falls through to active program bundles' capabilities[]
    declarations for program-specific capabilities.
    """
    cap = _resolve_capability(capability_name)
    if cap is None:
        return False
    req = cap.get("platform_connection_requirement")
    if req is None:
        return True
    try:
        row = (
            client.table("platform_connections")
            .select("id")
            .eq("user_id", user_id)
            .eq("platform", req["platform"])
            .eq("status", req["status"])
            .limit(1)
            .execute()
        )
        return bool(row.data)
    except Exception:
        # Deterministic gate — failing a lookup reports unavailable rather
        # than masking misconfiguration.
        return False


def unavailable_capabilities(
    user_id: str, capability_names: list[str], client: Any
) -> list[dict]:
    """Return a list of {capability, reason, required_platform} for each
    capability that cannot fire right now. Empty list = all capabilities
    are available.

    `reason` is one of: "unknown_capability", "platform_not_connected".

    Per ADR-224: resolves through _resolve_capability so bundle-sourced
    program-specific capabilities (read_trading, write_trading, read_commerce,
    write_commerce) are recognized identically to kernel capabilities.
    """
    results: list[dict] = []
    for name in capability_names or []:
        cap = _resolve_capability(name)
        if cap is None:
            results.append({
                "capability": name,
                "reason": "unknown_capability",
                "required_platform": None,
            })
            continue
        req = cap.get("platform_connection_requirement")
        if req is None:
            continue
        if not capability_available(user_id, name, client):
            results.append({
                "capability": name,
                "reason": "platform_not_connected",
                "required_platform": req.get("platform"),
            })
    return results


# =============================================================================
# Playbook Metadata — description + tags for selective loading
# =============================================================================
# Tags determine which playbooks are loaded for a given task type.
# Index (descriptions) is always in the prompt; full content only for matches.

PLAYBOOK_METADATA: dict[str, dict[str, str]] = {
    "_playbook-outputs.md": {
        "description": "Report, presentation, and document structure — quality criteria and format patterns",
        "tags": "synthesis,formatting,context",
    },
    "_playbook-research.md": {
        "description": "Investigation depth, source evaluation, evidence citation, cross-reference strategy",
        "tags": "research,context,investigation",
    },
    "_playbook-formats.md": {
        "description": "Format selection heuristics, tone calibration, structural patterns (pyramid, contrast, narrative)",
        "tags": "synthesis,formatting",
    },
    "_playbook-visual.md": {
        "description": "Image and video generation by output context — prompt construction, asset re-use, quality gate",
        "tags": "visual,synthesis",
    },
    "_playbook-rendering.md": {
        "description": "HTML output rendering — typography, color roles, layout, chart styling, existing asset usage",
        "tags": "synthesis,rendering",
    },
}

# ADR-166: task output_kind → which playbook tags to load in full
# (playbooks not matching any tag still appear in the index)
TASK_OUTPUT_PLAYBOOK_ROUTING: dict[str, list[str]] = {
    # accumulates_context: research + tracking methodology
    "accumulates_context": ["research", "context"],
    # produces_deliverable: synthesis + format + visual + rendering
    "produces_deliverable": ["synthesis", "formatting", "visual", "rendering"],
    # external_action: light synthesis (drafting platform messages)
    "external_action": ["synthesis", "formatting"],
    # system_maintenance: deterministic, no LLM playbooks needed
    "system_maintenance": [],
}


def get_type_playbook(agent_type: str) -> dict[str, str]:
    """Return playbook file seeds for an agent type.

    ADR-143: Returns dict of {filename: content} for playbook files
    to be written to the agent's memory/ directory at creation.
    """
    resolved = resolve_role(agent_type)
    type_def = ALL_ROLES.get(resolved)
    if not type_def:
        return {}
    return type_def.get("methodology", {})


def get_playbook_index(agent_type: str) -> str:
    """Build a short index of available playbooks for the system prompt.

    Returns a compact list of playbook names + one-line descriptions.
    This is always injected — lightweight, ~100-200 tokens.
    """
    playbooks = get_type_playbook(agent_type)
    if not playbooks:
        return ""
    lines = ["## Available Playbooks"]
    for filename in playbooks:
        meta = PLAYBOOK_METADATA.get(filename, {})
        desc = meta.get("description", filename.replace("_playbook-", "").replace(".md", ""))
        name = filename.replace("_playbook-", "").replace(".md", "").replace("-", " ").title()
        lines.append(f"- **{name}**: {desc}")
    return "\n".join(lines)


def get_relevant_playbooks(agent_type: str, output_kind: str | None = None) -> dict[str, str]:
    """Return only the playbooks relevant to the current task's output_kind (ADR-166).

    Args:
        agent_type: Agent type key
        output_kind: One of accumulates_context | produces_deliverable |
                     external_action | system_maintenance.

    Returns:
        {filename: content} for playbooks whose tags match the output_kind routing.
        If no output_kind provided, returns all playbooks (fallback).
        If output_kind is system_maintenance, returns {} (no LLM, no playbooks needed).
    """
    all_playbooks = get_type_playbook(agent_type)
    if not output_kind or output_kind not in TASK_OUTPUT_PLAYBOOK_ROUTING:
        return all_playbooks  # fallback: load all

    relevant_tags = set(TASK_OUTPUT_PLAYBOOK_ROUTING[output_kind])
    if not relevant_tags:
        return {}  # system_maintenance: no playbooks
    result = {}
    for filename, content in all_playbooks.items():
        meta = PLAYBOOK_METADATA.get(filename, {})
        playbook_tags = set(meta.get("tags", "").split(","))
        if relevant_tags & playbook_tags:  # any tag matches
            result[filename] = content
    return result


def get_type_display(agent_type: str) -> dict[str, str]:
    """Return display_name and tagline for a type. Used by frontend + TP prompt.

    ADR-272: previous researcher-fallback now resolves to empty dict;
    callers fall back to a titlecased raw role name via the .get defaults
    below.
    """
    resolved = resolve_role(agent_type)
    type_def = ALL_ROLES.get(resolved, {})
    return {
        "display_name": type_def.get("display_name", agent_type.title()),
        "tagline": type_def.get("tagline", ""),
    }


def list_agent_types(include_pm: bool = False) -> list[dict]:
    """List all agent types for system reference / TP prompt injection."""
    types = []
    for key, tdef in ALL_ROLES.items():
        if key == "pm" and not include_pm:
            continue
        types.append({
            "type": key,
            "display_name": tdef["display_name"],
            "tagline": tdef["tagline"],
            "capabilities": tdef["capabilities"],
            "has_assets": has_asset_capabilities(key),
        })
    return types


def get_agent_domain(agent_type: str) -> str | None:
    """Get the context domain owned by an agent template. None for synthesizers/bots."""
    template = ALL_ROLES.get(agent_type)
    return template.get("domain") if template else None


# ADR-141: Pulse cadence dissolved — scheduling is now task-level (tasks.schedule + next_run_at).

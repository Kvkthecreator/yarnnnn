"""
Agent Framework — Domain-Steward Model (v4)

Pre-scaffolded agent roster. Three registries, three concerns:
  1. AGENT_TEMPLATES — workforce roster: templates are starting points,
     AGENT.md is the runtime source of truth for each agent's identity
  2. CAPABILITIES    — implementation: what each capability resolves to
  3. RUNTIMES        — infrastructure: where compute happens

Three independent axes per agent (ADR-140):
  - Identity (AGENT.md): name, domain, evolves with use
  - Capabilities (AGENT_TEMPLATES): tool access, fixed at creation
  - Tasks (TASK.md): work assignments, come and go

Three agent classes:
  - domain-steward: owns a context domain (/workspace/{domain}/), accumulates
    knowledge over time, produces deliverables by synthesizing from context
  - synthesizer: reads across all context domains, produces cross-domain
    deliverables (e.g., executive reporting). Owns no domain.
  - platform-bot: captures signals from one external platform (Slack, Notion).
    Mechanical, scoped to one API.

v4 (2026-03-31): 5 domain-stewards + 1 synthesizer + 2 platform-bots.
Templates are starting points — agents evolve via AGENT.md, which is the
runtime source of truth for identity and behavior.

Canonical reference: docs/adr/ADR-140-agent-workforce-model.md
"""

from __future__ import annotations

from typing import Any


# =============================================================================
# Registry 1: Agent Templates — workforce roster (ADR-140)
# =============================================================================
# Pre-scaffolded at sign-up. Three classes:
#   domain-steward — owns a context domain, accumulates knowledge, synthesizes
#   synthesizer    — reads across domains, produces cross-domain deliverables
#   platform-bot   — captures signals from one external platform
#
# Templates are starting points. AGENT.md is the runtime source of truth.
# Type determines capabilities (axis 2). Identity (axis 1) and tasks (axis 3)
# are independent — see ADR-140 for the three-axis model.

AGENT_TEMPLATES: dict[str, dict[str, Any]] = {

    # ── Domain Stewards (own a context domain) ──

    "competitive_intel": {
        "class": "domain-steward",
        "domain": "competitors",
        "display_name": "Competitive Intelligence",
        "tagline": "Tracks and analyzes competitors",
        "capabilities": [
            "web_search", "read_workspace", "search_knowledge", "read_platforms",
            "investigate", "produce_markdown", "chart", "mermaid", "compose_html",
        ],
        "description": "Maintains competitive intelligence. Tracks competitor products, "
                       "pricing, funding, strategy. Produces competitive briefs.",
        "default_instructions": "Maintain the competitors/ context domain. Track competitor "
                                "moves, update entity profiles, flag strategic changes. When "
                                "asked for deliverables, synthesize from accumulated context.",
        "methodology": {
            "playbook-outputs.md": (
                "# Output Playbook\n\n"
                "## Report Structure\n"
                "1. **Executive Summary** — 2-3 sentences, lead with the insight not the process\n"
                "2. **Key Findings** — numbered, each with evidence source cited\n"
                "3. **Analysis** — structured by theme, not by source. Synthesize across sources\n"
                "4. **Data & Visuals** — use charts for trends/comparisons, tables for reference data\n"
                "5. **Implications** — what this means for the user's domain, not just what was found\n\n"
                "## Visualization Heuristics\n"
                "- Trend over time → line chart\n"
                "- Comparison across categories → bar chart\n"
                "- Part-of-whole → pie chart (only if ≤6 segments)\n"
                "- Relationships → mermaid diagram\n"
                "- Process/flow → mermaid flowchart\n"
                "- Reference data → markdown table (no chart needed)\n\n"
                "## Quality Criteria\n"
                "- Every claim has a source or evidence\n"
                "- Synthesis across sources, not source-by-source summaries\n"
                "- Insights the user hasn't seen elsewhere (not just restating source material)\n"
                "- Actionable implications, not just observations\n"
            ),
            "playbook-research.md": (
                "# Research Playbook\n\n"
                "## Investigation Depth\n"
                "- Start broad: landscape scan via web search + workspace knowledge\n"
                "- Go deep on signals: when a finding contradicts expectations or reveals a gap\n"
                "- Stop when: additional sources confirm existing findings without new signal\n\n"
                "## Source Evaluation\n"
                "1. Primary sources (official reports, filings, direct data) > secondary (articles, analyses)\n"
                "2. Recency matters: prefer sources from last 90 days unless tracking long-term trends\n"
                "3. Cross-reference: a finding from one source needs corroboration before becoming a 'key finding'\n\n"
                "## Evidence Citation\n"
                "- Inline: 'Revenue grew 23% (source: Q4 earnings call)'\n"
                "- Do not use footnotes — keep evidence next to claims\n"
                "- When sources conflict, note the conflict explicitly\n\n"
                "## Cross-Reference Strategy\n"
                "- Check workspace knowledge for prior findings on same topic\n"
                "- Note when new findings update or contradict prior knowledge\n"
                "- Flag emerging patterns across multiple investigation cycles\n"
            ),
        },
    },

    "market_research": {
        "class": "domain-steward",
        "domain": "market",
        "display_name": "Market Research",
        "tagline": "Tracks market trends and opportunities",
        "capabilities": [
            "web_search", "read_workspace", "search_knowledge", "read_platforms",
            "investigate", "produce_markdown", "chart", "mermaid", "compose_html",
        ],
        "description": "Maintains market intelligence. Tracks segments, trends, sizing, "
                       "key players. Produces market reports.",
        "default_instructions": "Maintain the market/ context domain. Track market segments, "
                                "trends, and opportunities. When asked for deliverables, "
                                "synthesize from accumulated research.",
        "methodology": {
            "playbook-outputs.md": (
                "# Output Playbook\n\n"
                "## Report Structure\n"
                "1. **Executive Summary** — 2-3 sentences, lead with the insight not the process\n"
                "2. **Key Findings** — numbered, each with evidence source cited\n"
                "3. **Analysis** — structured by theme, not by source. Synthesize across sources\n"
                "4. **Data & Visuals** — use charts for trends/comparisons, tables for reference data\n"
                "5. **Implications** — what this means for the user's domain, not just what was found\n\n"
                "## Visualization Heuristics\n"
                "- Trend over time → line chart\n"
                "- Comparison across categories → bar chart\n"
                "- Part-of-whole → pie chart (only if ≤6 segments)\n"
                "- Relationships → mermaid diagram\n"
                "- Process/flow → mermaid flowchart\n"
                "- Reference data → markdown table (no chart needed)\n\n"
                "## Quality Criteria\n"
                "- Every claim has a source or evidence\n"
                "- Synthesis across sources, not source-by-source summaries\n"
                "- Insights the user hasn't seen elsewhere (not just restating source material)\n"
                "- Actionable implications, not just observations\n"
            ),
            "playbook-research.md": (
                "# Research Playbook\n\n"
                "## Investigation Depth\n"
                "- Start broad: landscape scan via web search + workspace knowledge\n"
                "- Go deep on signals: when a finding contradicts expectations or reveals a gap\n"
                "- Stop when: additional sources confirm existing findings without new signal\n\n"
                "## Source Evaluation\n"
                "1. Primary sources (official reports, filings, direct data) > secondary (articles, analyses)\n"
                "2. Recency matters: prefer sources from last 90 days unless tracking long-term trends\n"
                "3. Cross-reference: a finding from one source needs corroboration before becoming a 'key finding'\n\n"
                "## Evidence Citation\n"
                "- Inline: 'Revenue grew 23% (source: Q4 earnings call)'\n"
                "- Do not use footnotes — keep evidence next to claims\n"
                "- When sources conflict, note the conflict explicitly\n\n"
                "## Market-Specific Research\n"
                "- Track TAM/SAM/SOM evolution over time\n"
                "- Segment analysis: who are the buyers, what are the segments, how are they shifting\n"
                "- Identify emerging trends before they hit mainstream coverage\n"
                "- Cross-reference multiple analyst reports — consensus vs contrarian signals\n"
            ),
        },
    },

    "business_dev": {
        "class": "domain-steward",
        "domain": "relationships",
        "display_name": "Business Development",
        "tagline": "Manages relationships and deals",
        "capabilities": [
            "read_platforms", "read_workspace", "search_knowledge",
            "produce_markdown", "compose_html",
        ],
        "description": "Maintains relationship intelligence. Tracks contacts, interactions, "
                       "deals. Produces meeting prep and relationship digests.",
        "default_instructions": "Maintain the relationships/ context domain. Track contact "
                                "interactions, flag follow-ups, update relationship health. "
                                "When asked for deliverables, synthesize from accumulated "
                                "relationship context.",
        "methodology": {
            "playbook-outputs.md": (
                "# Output Playbook\n\n"
                "## Meeting Brief Format\n"
                "- **Context** — who, when, what's the relationship history (2-3 sentences)\n"
                "- **Last Interaction** — what was discussed, what was promised, what's pending\n"
                "- **Agenda Items** — what to cover, prioritized by relationship impact\n"
                "- **Talking Points** — specific things to mention (their recent news, shared interests)\n"
                "- **Open Items** — action items from prior meetings, their status\n\n"
                "## Relationship Health Report\n"
                "- Engagement frequency: trending up/down/stable\n"
                "- Response patterns: quick/delayed/ghosting\n"
                "- Sentiment signals: positive mentions, complaints, requests\n"
                "- Risk flags: going quiet, competitor mentions, delayed follow-ups\n\n"
                "## Deal Tracking Format\n"
                "- **Pipeline Overview** — deals by stage, expected close, confidence\n"
                "- **Movement** — what advanced, what stalled, what's at risk\n"
                "- **Next Actions** — specific follow-ups with deadlines\n\n"
                "## Quality Criteria\n"
                "- Actionable: every brief ends with 'do this before/during/after the meeting'\n"
                "- Personalized: reference specific prior interactions, not generic relationship advice\n"
                "- Timely: meeting briefs available before the meeting, not after\n"
                "- Concise: scannable in 2 minutes — the user has 5 minutes before the call\n"
            ),
        },
    },

    "operations": {
        "class": "domain-steward",
        "domain": "projects",
        "display_name": "Operations",
        "tagline": "Tracks projects and workstreams",
        "capabilities": [
            "read_platforms", "read_workspace", "search_knowledge",
            "produce_markdown", "chart", "compose_html",
        ],
        "description": "Maintains project intelligence. Tracks status, milestones, "
                       "blockers. Produces status reports.",
        "default_instructions": "Maintain the projects/ context domain. Track project status, "
                                "milestones, and blockers from platform signals. When asked for "
                                "deliverables, synthesize from accumulated project context.",
        "methodology": {
            "playbook-outputs.md": (
                "# Output Playbook\n\n"
                "## Status Report Format\n"
                "1. **Summary** — 2-3 sentences: overall health, biggest risk, biggest win\n"
                "2. **By Project/Workstream** — for each: status (on track/at risk/blocked), "
                "key milestone, next deadline, blockers\n"
                "3. **Cross-Cutting Issues** — themes that affect multiple workstreams\n"
                "4. **Decisions Needed** — what's waiting on someone, who, by when\n"
                "5. **Next Period Focus** — what matters most in the coming cycle\n\n"
                "## Milestone Tracking\n"
                "- Use traffic light status: green (on track), yellow (at risk), red (blocked/late)\n"
                "- Track planned vs actual dates — drift is signal\n"
                "- Chart: Gantt-style timeline or milestone burn-down when multiple projects\n\n"
                "## Blocker Escalation\n"
                "- Blocked >2 days without owner → escalate\n"
                "- Same blocker appearing in multiple projects → systemic issue\n"
                "- Resource conflicts between projects → flag for prioritization\n\n"
                "## Quality Criteria\n"
                "- Objective: status is based on evidence (dates, completion %), not feelings\n"
                "- Forward-looking: what's coming, not just what happened\n"
                "- Actionable: every section implies a next step\n"
                "- Concise: one page per project max — scannable by executives\n"
            ),
        },
    },

    "marketing": {
        "class": "domain-steward",
        "domain": "content",
        "display_name": "Marketing & Creative",
        "tagline": "Creates content and go-to-market materials",
        "capabilities": [
            "web_search", "read_workspace", "search_knowledge", "read_platforms",
            "produce_markdown", "chart", "mermaid", "image", "video_render", "compose_html",
        ],
        "description": "Maintains content research and produces creative deliverables. "
                       "Blog posts, launch materials, GTM reports, ad creative.",
        "default_instructions": "Maintain the content/ context domain. Research topics, track "
                                "content opportunities. When asked for deliverables, produce "
                                "polished content from accumulated research. Use visual assets "
                                "(charts, diagrams, images) where they add value.",
        "methodology": {
            "playbook-outputs.md": (
                "# Output Playbook\n\n"
                "## Deliverable Formats\n"
                "### Reports\n"
                "- Lead with the conclusion, not the process\n"
                "- Use headings as scannable summary (reader should get 80% from headings alone)\n"
                "- Data-heavy sections: chart + 1-sentence interpretation, not paragraphs describing data\n\n"
                "### Presentations (HTML slide format)\n"
                "- 1 idea per slide, 3 bullet points maximum\n"
                "- Title slide → Agenda → Content slides → Summary → Next steps\n"
                "- Charts/visuals on every other slide minimum\n"
                "- Slide titles are assertions ('Revenue grew 23%'), not topics ('Revenue')\n\n"
                "### Documents (memos, briefs, updates)\n"
                "- BLUF (Bottom Line Up Front) — the ask or conclusion in the first paragraph\n"
                "- Background only if the audience needs it\n"
                "- End with clear next steps or decisions needed\n\n"
                "## Asset Integration\n"
                "- Charts: use when data tells the story better than words\n"
                "- Diagrams: use for process flows, org structures, system architecture\n"
                "- Images: use for brand assets, product screenshots, visual concepts\n"
                "- Never use a visual as decoration — every asset must carry information\n\n"
                "## Quality Criteria\n"
                "- Audience-appropriate language and depth\n"
                "- Consistent visual style within a single deliverable\n"
                "- Every section earns its place — delete sections that don't add value\n"
                "- Proofread: no orphaned references, no TBD placeholders\n"
            ),
            "playbook-formats.md": (
                "# Format Playbook\n\n"
                "## Format Selection Heuristics\n"
                "- Status update for executives → presentation (slide format)\n"
                "- Deep analysis for decision-makers → report\n"
                "- Quick alignment or approval → memo/brief\n"
                "- Recurring team update → structured digest\n"
                "- Creative/marketing deliverable → document with embedded visuals\n\n"
                "## Tone Calibration\n"
                "- Internal audience → direct, use jargon they know, skip context they have\n"
                "- External audience → polished, define terms, provide context\n"
                "- Executive audience → concise, lead with impact, support with data\n"
                "- Technical audience → precise, include methodology, show your work\n\n"
                "## Structural Patterns\n"
                "- Pyramid principle: conclusion → supporting arguments → evidence\n"
                "- Contrast pattern: situation → complication → resolution\n"
                "- Narrative arc: context → tension → insight → implication\n"
            ),
        },
    },

    # ── Synthesizer (cross-domain, no owned domain) ──

    "executive": {
        "class": "synthesizer",
        "domain": None,
        "display_name": "Executive Reporting",
        "tagline": "Cross-domain synthesis for leadership",
        "capabilities": [
            "read_workspace", "search_knowledge",
            "produce_markdown", "chart", "mermaid", "compose_html",
        ],
        "description": "Reads from all context domains. Produces stakeholder updates, "
                       "board decks, executive summaries.",
        "default_instructions": "Synthesize across all context domains. Produce executive-level "
                                "deliverables — board updates, stakeholder reports, all-hands "
                                "summaries. Write for leadership audiences.",
        "methodology": {
            "playbook-outputs.md": (
                "# Output Playbook\n\n"
                "## Deliverable Formats\n"
                "### Board Updates / Executive Summaries\n"
                "- Lead with the conclusion, not the process\n"
                "- Use headings as scannable summary (reader should get 80% from headings alone)\n"
                "- Data-heavy sections: chart + 1-sentence interpretation, not paragraphs describing data\n\n"
                "### Presentations (HTML slide format)\n"
                "- 1 idea per slide, 3 bullet points maximum\n"
                "- Title slide → Agenda → Content slides → Summary → Next steps\n"
                "- Charts/visuals on every other slide minimum\n"
                "- Slide titles are assertions ('Revenue grew 23%'), not topics ('Revenue')\n\n"
                "### Stakeholder Reports\n"
                "- BLUF (Bottom Line Up Front) — the ask or conclusion in the first paragraph\n"
                "- Cross-domain synthesis: pull from competitive, market, operations, relationships\n"
                "- End with clear decisions needed or strategic recommendations\n\n"
                "## Quality Criteria\n"
                "- Audience-appropriate: executive = concise, lead with impact, support with data\n"
                "- Cross-domain: synthesize, don't just concatenate domain summaries\n"
                "- Every section earns its place — delete sections that don't add value\n"
                "- Proofread: no orphaned references, no TBD placeholders\n"
            ),
            "playbook-formats.md": (
                "# Format Playbook\n\n"
                "## Format Selection Heuristics\n"
                "- Board update → presentation (slide format) with appendix data\n"
                "- Stakeholder report → structured document with executive summary\n"
                "- All-hands summary → brief with key metrics and highlights\n"
                "- Investor update → formal report with data tables and charts\n\n"
                "## Tone Calibration\n"
                "- Executive audience → concise, lead with impact, support with data\n"
                "- Board audience → formal, forward-looking, risk-aware\n"
                "- All-hands audience → accessible, celebratory where warranted, honest about challenges\n\n"
                "## Structural Patterns\n"
                "- Pyramid principle: conclusion → supporting arguments → evidence\n"
                "- Contrast pattern: situation → complication → resolution\n"
                "- Narrative arc: context → tension → insight → implication\n"
            ),
        },
    },

    # ── Platform Bots (capture platform signals) ──

    "slack_bot": {
        "class": "platform-bot",
        "domain": None,
        "platform": "slack",
        "display_name": "Slack Bot",
        "tagline": "Captures Slack activity",
        "capabilities": [
            "read_platforms", "write_slack", "summarize", "produce_markdown",
        ],
        "description": "Captures signals from Slack. Decisions, action items, key "
                       "discussions. Produces daily recaps.",
        "default_instructions": "Monitor Slack channels. Capture decisions, action items, "
                                "and key discussions. Produce scannable daily recaps.",
        "methodology": {
            "playbook-outputs.md": (
                "# Output Playbook\n\n"
                "## Channel Recap Format\n"
                "- **Decisions Made** — what was decided, by whom, in which thread\n"
                "- **Action Items** — who owes what, with deadlines if mentioned\n"
                "- **Key Discussions** — topics with significant engagement (replies, reactions)\n"
                "- **FYIs** — announcements, links shared, things to be aware of\n\n"
                "## Summarization Rules\n"
                "- Preserve attribution: 'Alice proposed X' not 'it was proposed'\n"
                "- Threads > individual messages: summarize thread conclusions, not each reply\n"
                "- Skip: bot messages, emoji-only messages, routine standup entries\n"
                "- Highlight: questions left unanswered, disagreements unresolved\n\n"
                "## Alert Triggers\n"
                "- Urgent/blocking language: 'blocked', 'need help', 'ASAP', 'down'\n"
                "- Mentions of the user by name\n"
                "- Threads with >5 replies in <1 hour (heated discussion)\n"
            ),
        },
    },

    "notion_bot": {
        "class": "platform-bot",
        "domain": None,
        "platform": "notion",
        "display_name": "Notion Bot",
        "tagline": "Tracks Notion changes",
        "capabilities": [
            "read_platforms", "write_notion", "summarize", "produce_markdown",
        ],
        "description": "Tracks Notion workspace changes. Page updates, new content, "
                       "stale pages.",
        "default_instructions": "Monitor Notion workspace. Track page changes, flag stale "
                                "content, summarize updates.",
        "methodology": {
            "playbook-outputs.md": (
                "# Output Playbook\n\n"
                "## Knowledge Base Update Format\n"
                "- **What Changed** — pages created, updated, or reorganized\n"
                "- **Content Summary** — what was added or modified, in context\n"
                "- **Structure Notes** — how content fits into the existing hierarchy\n\n"
                "## Page Sync Rules\n"
                "- Preserve existing page structure — append or update sections, don't restructure\n"
                "- Use Notion-native formatting: toggles for detail, callouts for alerts, tables for data\n"
                "- Link related pages rather than duplicating content\n"
                "- Tag with status properties when available (draft, reviewed, published)\n\n"
                "## Change Detection\n"
                "- Track meaningful content changes vs formatting-only edits\n"
                "- Flag pages that haven't been updated in >30 days (potential staleness)\n"
                "- Note pages with high edit frequency (active collaboration)\n"
            ),
        },
    },
}

# Backward compat alias — all existing callers import AGENT_TYPES
AGENT_TYPES = AGENT_TEMPLATES


# =============================================================================
# TP Orchestration Playbook — workspace-level (/workspace/playbook-orchestration.md)
# =============================================================================
# TP is infrastructure, not workforce. Its playbook lives at workspace scope,
# not under /agents/. Seeded at roster creation, evolves through user feedback.

TP_ORCHESTRATION_PLAYBOOK = """\
# Orchestration Playbook

## Task Decomposition
- Simple requests (single deliverable, clear audience) → assign to one agent
- Complex requests (multi-source, multi-format) → split into research + content tasks
- Recurring work → create task with schedule, not one-off run
- Bounded investigation → create goal-mode task with clear completion criteria

## Agent Assignment
- Competitive Intelligence: competitor tracking, competitive analysis, due diligence
- Market Research: market segments, trends, sizing, opportunities
- Business Development: contacts, relationships, meeting prep, deal tracking
- Operations: project status, milestones, blockers, workstream tracking
- Marketing & Creative: content, launch materials, GTM, ad creative, social
- Executive Reporting: board updates, stakeholder reports, cross-domain synthesis
- Slack Bot: Slack recaps, signal capture (requires Slack connection)
- Notion Bot: Notion sync, change tracking (requires Notion connection)

## When Multiple Agents Are Needed
- Competitive analysis → executive summary: Competitive Intelligence task first, then Executive Reporting task
- Market research → GTM plan: Market Research task first, then Marketing & Creative task
- Operations status → board deck: Operations task first, then Executive Reporting task
- Don't assign content creation to research agents — they investigate, Marketing/Executive produce

## Feedback Routing
- When user comments on output quality → UpdateContext(target="agent") to the producing agent
- When user says "too long" / "more detail" / "different format" → feedback to agent
- When user corrects orchestration ("don't use the marketing agent for this") → update this playbook
- Positive feedback matters too — "great charts" confirms the agent's approach

## Quality Oversight
- After task completion, check if output matches what was asked
- If user edits frequently, note patterns in agent feedback
- When an agent consistently underperforms, suggest task reassignment
"""


# =============================================================================
# Default Workspace Files — seeded at roster scaffold time
# =============================================================================

DEFAULT_IDENTITY_MD = """\
# About Me

**Name:** (not set)
**Role:** (not set)
**Company:** (not set)
**Industry:** (not set)

## Summary
(Not yet provided. Tell your Thinking Partner about yourself — your role, what you work on, \
who you work with — so your agents can tailor outputs to your context.)
"""

DEFAULT_BRAND_MD = """\
# Brand

## Tone & Voice
- **Tone:** Professional, clear, direct
- **Voice:** Confident but not aggressive. Data-driven. Concise.

## Visual Style
- **Primary color:** #000000 (black)
- **Secondary color:** #ffffff (white)
- **Accent color:** #666666 (gray)
- **Typography:** Clean sans-serif (system default)
- **Charts:** Black/gray palette. Minimal gridlines. Clear axis labels. No decorative elements.
- **Diagrams:** Monochrome. Solid lines. Clear labels.

## Output Defaults
- Clean, minimal formatting — content over decoration
- White background, high contrast text
- Generous whitespace, scannable structure
- No placeholder images or decorative visuals

(Update this file to match your brand — colors, logo, typography, tone of voice. \
Your agents read this on every run.)
"""


# Default roster created at sign-up (ADR-140)
DEFAULT_ROSTER = [
    {"title": "Competitive Intelligence", "role": "competitive_intel"},
    {"title": "Market Research", "role": "market_research"},
    {"title": "Business Development", "role": "business_dev"},
    {"title": "Operations", "role": "operations"},
    {"title": "Marketing & Creative", "role": "marketing"},
    {"title": "Executive Reporting", "role": "executive"},
    {"title": "Slack Bot", "role": "slack_bot"},
    {"title": "Notion Bot", "role": "notion_bot"},
]

# PM_MODES — REMOVED (PM/project architecture dissolved)


# Legacy role → new type mapping (for DB migration / backward compat reads)
LEGACY_ROLE_MAP: dict[str, str] = {
    # v1 legacy
    "digest": "competitive_intel",
    "synthesize": "executive",
    "prepare": "marketing",
    "custom": "competitive_intel",
    # v2 legacy (ADR-130)
    "briefer": "competitive_intel",
    "monitor": "operations",
    "scout": "competitive_intel",
    "researcher": "market_research",
    "analyst": "competitive_intel",
    "drafter": "marketing",
    "writer": "marketing",
    "planner": "operations",
    # v3 legacy (ADR-140 v3)
    "research": "competitive_intel",
    "content": "marketing",
    "crm": "business_dev",
    # v4 current types pass through
    "competitive_intel": "competitive_intel",
    "market_research": "market_research",
    "business_dev": "business_dev",
    "operations": "operations",
    "marketing": "marketing",
    "executive": "executive",
    "slack_bot": "slack_bot",
    "notion_bot": "notion_bot",
}


def resolve_role(role: str) -> str:
    """Map legacy role names to current types. Passthrough for current types."""
    if role in AGENT_TEMPLATES:
        return role
    return LEGACY_ROLE_MAP.get(role, role)


# =============================================================================
# Registry 2: Capabilities — what each capability resolves to
# =============================================================================

CAPABILITIES: dict[str, dict[str, Any]] = {
    # -- Cognitive (prompt-driven, no dedicated tool) --
    "read_platforms":    {"category": "cognitive", "runtime": "internal"},
    "summarize":         {"category": "cognitive", "runtime": "internal"},
    "detect_change":     {"category": "cognitive", "runtime": "internal"},
    "alert":             {"category": "cognitive", "runtime": "internal"},
    "cross_reference":   {"category": "cognitive", "runtime": "internal"},
    "data_analysis":     {"category": "cognitive", "runtime": "internal"},
    "investigate":       {"category": "cognitive", "runtime": "internal"},
    "produce_markdown":  {"category": "cognitive", "runtime": "internal"},

    # -- Tool-backed (internal primitives) --
    "web_search":        {"category": "tool", "runtime": "internal", "tool": "WebSearch"},
    "read_workspace":    {"category": "tool", "runtime": "internal", "tool": "ReadWorkspace"},
    "search_knowledge":  {"category": "tool", "runtime": "internal", "tool": "QueryKnowledge"},

    # -- Asset production (compute runtimes) --
    "chart":   {
        "category": "asset", "runtime": "python_render",
        "tool": "RuntimeDispatch", "skill_docs": "chart/SKILL.md",
        "output_type": "image/png",
    },
    "mermaid": {
        "category": "asset", "runtime": "python_render",
        "tool": "RuntimeDispatch", "skill_docs": "mermaid/SKILL.md",
        "output_type": "image/svg+xml",
    },
    "image":   {
        "category": "asset", "runtime": "python_render",
        "tool": "RuntimeDispatch", "skill_docs": "image/SKILL.md",
        "output_type": "image/png",
    },
    "video_render": {
        "category": "asset", "runtime": "python_render",
        "tool": "RuntimeDispatch", "skill_docs": "video/SKILL.md",
        "output_type": "video/mp4",
        "timeout": 180,  # extended timeout for video rendering
    },

    # -- Composition (post-generation pipeline step) --
    "compose_html": {
        "category": "composition", "runtime": "python_render",
        "post_generation": True,
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
}


# =============================================================================
# Type Query Helpers
# =============================================================================

def get_type_capabilities(agent_type: str) -> list[str]:
    """Return the capability list for an agent type. Falls back to competitive_intel for unknown."""
    resolved = resolve_role(agent_type)
    type_def = AGENT_TEMPLATES.get(resolved)
    if not type_def:
        return AGENT_TEMPLATES["competitive_intel"]["capabilities"]
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


def get_type_playbook(agent_type: str) -> dict[str, str]:
    """Return playbook file seeds for an agent type.

    ADR-143: Returns dict of {filename: content} for playbook files
    to be written to the agent's memory/ directory at creation.
    """
    resolved = resolve_role(agent_type)
    type_def = AGENT_TEMPLATES.get(resolved)
    if not type_def:
        return {}
    return type_def.get("methodology", {})


def get_type_display(agent_type: str) -> dict[str, str]:
    """Return display_name and tagline for a type. Used by frontend + TP prompt."""
    resolved = resolve_role(agent_type)
    type_def = AGENT_TEMPLATES.get(resolved, AGENT_TEMPLATES.get("competitive_intel", {}))
    return {
        "display_name": type_def.get("display_name", agent_type.title()),
        "tagline": type_def.get("tagline", ""),
    }


def list_agent_types(include_pm: bool = False) -> list[dict]:
    """List all agent types for system reference / TP prompt injection."""
    types = []
    for key, tdef in AGENT_TEMPLATES.items():
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
    template = AGENT_TEMPLATES.get(agent_type)
    return template.get("domain") if template else None


# ADR-141: Pulse cadence dissolved — scheduling is now task-level (tasks.schedule + next_run_at).

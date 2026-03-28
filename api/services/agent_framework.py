"""
Agent Framework — ADR-140 Workforce Model (v3)

Pre-scaffolded agent roster. Three registries, three concerns:
  1. AGENT_TYPES  — workforce roster: agents + bots, capabilities each gets
  2. CAPABILITIES — implementation: what each capability resolves to
  3. RUNTIMES     — infrastructure: where compute happens

Three independent axes per agent (ADR-140):
  - Identity (AGENT.md): name, domain, evolves with use
  - Capabilities (AGENT_TYPES): tool access, fixed at creation
  - Tasks (TASK.md): work assignments, come and go

v3 (2026-03-25): 4 agents + 2 bots. Agents are domain-cognitive (multi-step
reasoning, deep expertise). Bots are platform-mechanical (read/write one platform).
All 6 pre-scaffolded at sign-up. Tasks assigned downstream.

Canonical reference: docs/adr/ADR-140-agent-workforce-model.md
"""

from __future__ import annotations

from typing import Any


# =============================================================================
# Registry 1: Agent Types — workforce roster (ADR-140)
# =============================================================================
# Pre-scaffolded at sign-up. Two classes:
#   agent — domain-cognitive, multi-step reasoning, deep expertise
#   bot   — platform-mechanical, scoped to one platform's API
#
# Type determines capabilities (axis 2). Identity (axis 1) and tasks (axis 3)
# are independent — see ADR-140 for the three-axis model.

AGENT_TYPES: dict[str, dict[str, Any]] = {

    # ── Agents (domain-cognitive) ──

    "research": {
        "class": "agent",
        "display_name": "Research Agent",
        "tagline": "Investigates and analyzes",
        "capabilities": [
            "web_search", "read_workspace", "search_knowledge", "read_platforms",
            "investigate", "produce_markdown", "chart", "mermaid", "image", "compose_html",
        ],
        "description": "Deep investigation across web and workspace. Produces structured "
                       "analysis with evidence. Competitor tracking, market research, due diligence.",
        "default_instructions": "Investigate assigned topics with depth. Use web search and "
                                "workspace context. Produce structured analysis with evidence. "
                                "Prioritize insights the user hasn't seen elsewhere.",
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

    "content": {
        "class": "agent",
        "display_name": "Content Agent",
        "tagline": "Creates deliverables",
        "capabilities": [
            "read_workspace", "search_knowledge", "produce_markdown",
            "chart", "mermaid", "image", "video_render", "compose_html",
        ],
        "description": "Produces polished deliverables from workspace context. Reports, "
                       "presentations, blog posts, investor updates, documents.",
        "default_instructions": "Produce polished deliverables for the target audience. "
                                "Use charts and visuals where they add clarity. Structure for "
                                "readability. Focus on quality and completeness.",
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

    "marketing": {
        "class": "agent",
        "display_name": "Marketing Agent",
        "tagline": "Handles go-to-market",
        "capabilities": [
            "web_search", "read_workspace", "search_knowledge", "read_platforms",
            "produce_markdown", "compose_html",
        ],
        "description": "GTM tracking, content distribution, competitive positioning, "
                       "campaign analysis. Monitors market signals, produces GTM insights.",
        "default_instructions": "Track go-to-market activities and competitive positioning. "
                                "Monitor market signals. Produce actionable GTM insights and content.",
        "methodology": {
            "playbook-outputs.md": (
                "# Output Playbook\n\n"
                "## GTM Report Structure\n"
                "1. **Market Pulse** — 3-5 signals worth attention this cycle\n"
                "2. **Competitive Moves** — what competitors did, what it means for us\n"
                "3. **Channel Performance** — metrics that changed, why, what to do\n"
                "4. **Opportunities** — gaps in market, positioning openings, timing windows\n"
                "5. **Recommendations** — specific, actionable, with effort/impact estimate\n\n"
                "## Competitive Analysis Format\n"
                "- Feature matrix: rows=features, columns=competitors, cells=status (has/building/missing)\n"
                "- Positioning map: where each player sits on key dimensions\n"
                "- Signal tracking: what each competitor announced/shipped/hired recently\n\n"
                "## Quality Criteria\n"
                "- Separate signal from noise — not everything is worth reporting\n"
                "- 'So what?' test: every finding needs an implication for our strategy\n"
                "- Quantify when possible: '23% increase' not 'significant growth'\n"
                "- Time-bound: signals decay fast, always note when something happened\n"
            ),
            "playbook-research.md": (
                "# Research Playbook\n\n"
                "## Market Signal Sources\n"
                "- Competitor websites, blogs, changelogs (primary — what they say)\n"
                "- Industry publications, analyst reports (secondary — what others say)\n"
                "- Platform conversations (Slack/community mentions of competitors)\n"
                "- Job postings (reveal strategic direction)\n\n"
                "## Signal Evaluation\n"
                "- Launched feature > announced feature > rumored feature\n"
                "- Pricing change > feature change (pricing reveals strategy)\n"
                "- Hiring pattern > single hire (pattern reveals direction)\n\n"
                "## Investigation Cadence\n"
                "- Continuous: competitor changelog monitoring\n"
                "- Weekly: market signal scan\n"
                "- Monthly: deep competitive landscape refresh\n"
                "- Trigger-based: on major competitor announcement\n"
            ),
        },
    },

    "crm": {
        "class": "agent",
        "display_name": "CRM Agent",
        "tagline": "Manages relationships",
        "capabilities": [
            "read_platforms", "read_workspace", "search_knowledge",
            "produce_markdown", "compose_html",
        ],
        "description": "Client tracking, relationship management, follow-ups, meeting "
                       "preparation. Reads platform context for relationship signals.",
        "default_instructions": "Track client relationships and interactions. Prepare meeting "
                                "briefs. Flag follow-ups and action items. Summarize relationship health.",
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
                "## Quality Criteria\n"
                "- Actionable: every brief ends with 'do this before/during/after the meeting'\n"
                "- Personalized: reference specific prior interactions, not generic relationship advice\n"
                "- Timely: meeting briefs available before the meeting, not after\n"
                "- Concise: scannable in 2 minutes — the user has 5 minutes before the call\n"
            ),
        },
    },

    # ── Bots (platform-mechanical) ──

    "slack_bot": {
        "class": "bot",
        "display_name": "Slack Bot",
        "tagline": "Reads and writes Slack",
        "capabilities": [
            "read_platforms", "write_slack", "summarize", "produce_markdown",
        ],
        "platform": "slack",
        "description": "Platform bot for Slack. Recaps, summaries, alerts, message posting.",
        "default_instructions": "Monitor Slack channels. Summarize key discussions. Post updates "
                                "when directed. Flag action items and decisions.",
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
        "class": "bot",
        "display_name": "Notion Bot",
        "tagline": "Reads and writes Notion",
        "capabilities": [
            "read_platforms", "write_notion", "summarize", "produce_markdown",
        ],
        "platform": "notion",
        "description": "Platform bot for Notion. Knowledge base management, page syncing, "
                       "content updates.",
        "default_instructions": "Manage Notion workspace. Sync meeting notes. Update knowledge "
                                "base pages. Track document changes.",
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
- Research Agent: investigation, competitive analysis, due diligence, data gathering
- Content Agent: formatted deliverables (presentations, reports, memos, blog posts)
- Marketing Agent: GTM tracking, competitive positioning, market signals, campaign analysis
- CRM Agent: relationship management, meeting prep, follow-ups, client tracking
- Slack Bot: channel recaps, alerts, thread summaries (requires Slack connection)
- Notion Bot: knowledge base management, page syncing (requires Notion connection)

## When Multiple Agents Are Needed
- Research findings → formatted output: Research Agent task first, then Content Agent task
- Market analysis → client presentation: Marketing Agent research, then Content Agent deliverable
- Don't assign content creation to Research Agent — they investigate, Content Agent produces

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
    {"title": "Research Agent", "role": "research"},
    {"title": "Content Agent", "role": "content"},
    {"title": "Marketing Agent", "role": "marketing"},
    {"title": "CRM Agent", "role": "crm"},
    {"title": "Slack Bot", "role": "slack_bot"},
    {"title": "Notion Bot", "role": "notion_bot"},
]

# PM_MODES — REMOVED (PM/project architecture dissolved)


# Legacy role → new type mapping (for DB migration / backward compat reads)
LEGACY_ROLE_MAP: dict[str, str] = {
    # v1 legacy
    "digest": "research",
    "synthesize": "research",
    "prepare": "content",
    "custom": "research",
    # v2 legacy (ADR-130)
    "briefer": "research",
    "monitor": "research",
    "scout": "research",
    "researcher": "research",
    "analyst": "research",
    "drafter": "content",
    "writer": "content",
    "planner": "content",
    # v3 current types pass through
    "research": "research",
    "content": "content",
    "marketing": "marketing",
    "crm": "crm",
    "slack_bot": "slack_bot",
    "notion_bot": "notion_bot",
}


def resolve_role(role: str) -> str:
    """Map legacy role names to current types. Passthrough for current types."""
    if role in AGENT_TYPES:
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
    """Return the capability list for an agent type. Falls back to briefer for unknown."""
    resolved = resolve_role(agent_type)
    type_def = AGENT_TYPES.get(resolved)
    if not type_def:
        return AGENT_TYPES["research"]["capabilities"]
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
    type_def = AGENT_TYPES.get(resolved)
    if not type_def:
        return {}
    return type_def.get("methodology", {})


def get_type_display(agent_type: str) -> dict[str, str]:
    """Return display_name and tagline for a type. Used by frontend + TP prompt."""
    resolved = resolve_role(agent_type)
    type_def = AGENT_TYPES.get(resolved, AGENT_TYPES.get("briefer", {}))
    return {
        "display_name": type_def.get("display_name", agent_type.title()),
        "tagline": type_def.get("tagline", ""),
    }


def list_agent_types(include_pm: bool = False) -> list[dict]:
    """List all agent types for system reference / TP prompt injection."""
    types = []
    for key, tdef in AGENT_TYPES.items():
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


# ADR-141: Pulse cadence dissolved — scheduling is now task-level (tasks.schedule + next_run_at).

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
  - domain-steward: owns a canonical context domain (/workspace/context/{domain}/),
    accumulates knowledge over time, produces deliverables by synthesizing from context
  - synthesizer: reads across all context domains, produces cross-domain
    deliverables (e.g., executive reporting). Owns no domain.
  - platform-bot: owns a temporal context domain (/workspace/context/{platform}/),
    captures signals from one external platform (Slack, Notion). Per-source
    subfolders (channel/page/repo). ADR-158: bots own their directories.

v4 (2026-03-31): 5 domain-stewards + 1 synthesizer + 2 platform-bots.
v4.1 (2026-04-04): ADR-158 Phase 4 — GitHub Bot added. 5 + 1 + 3 = 9 agents.
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


AGENT_TEMPLATES: dict[str, dict[str, Any]] = {

    # ── Domain Stewards (own a context domain) ──

    "competitive_intel": {
        "class": "domain-steward",
        "domain": "competitors",
        "display_name": "Competitive Intelligence",
        "tagline": "Tracks and analyzes competitors",
        "capabilities": [
            "web_search", "read_workspace", "search_knowledge",
            "read_slack", "read_notion", "read_github",
            "investigate", "produce_markdown", "chart", "mermaid", "compose_html",
        ],
        "description": "Maintains competitive intelligence. Tracks competitor products, "
                       "pricing, funding, strategy. Produces competitive briefs.",
        "default_instructions": "Maintain the competitors/ context domain. Track competitor "
                                "moves, update entity profiles, flag strategic changes. When "
                                "asked for deliverables, synthesize from accumulated context.",
        "methodology": {
            "_playbook-outputs.md": (
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
            "_playbook-research.md": (
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
            "_playbook-rendering.md": _PLAYBOOK_RENDERING,
        },
    },

    "market_research": {
        "class": "domain-steward",
        "domain": "market",
        "display_name": "Market Research",
        "tagline": "Tracks market trends and opportunities",
        "capabilities": [
            "web_search", "read_workspace", "search_knowledge",
            "read_slack", "read_notion", "read_github",
            "investigate", "produce_markdown", "chart", "mermaid", "compose_html",
        ],
        "description": "Maintains market intelligence. Tracks segments, trends, sizing, "
                       "key players. Produces market reports.",
        "default_instructions": "Maintain the market/ context domain. Track market segments, "
                                "trends, and opportunities. When asked for deliverables, "
                                "synthesize from accumulated research.",
        "methodology": {
            "_playbook-outputs.md": (
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
            "_playbook-research.md": (
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
            "_playbook-rendering.md": _PLAYBOOK_RENDERING,
        },
    },

    "business_dev": {
        "class": "domain-steward",
        "domain": "relationships",
        "display_name": "Business Development",
        "tagline": "Manages relationships and deals",
        "capabilities": [
            "read_slack", "read_notion", "read_github",
            "read_workspace", "search_knowledge",
            "produce_markdown", "compose_html",
        ],
        "description": "Maintains relationship intelligence. Tracks contacts, interactions, "
                       "deals. Produces meeting prep and relationship digests.",
        "default_instructions": "Maintain the relationships/ context domain. Track contact "
                                "interactions, flag follow-ups, update relationship health. "
                                "When asked for deliverables, synthesize from accumulated "
                                "relationship context.",
        "methodology": {
            "_playbook-outputs.md": (
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
            "_playbook-rendering.md": _PLAYBOOK_RENDERING,
        },
    },

    "operations": {
        "class": "domain-steward",
        "domain": "projects",
        "display_name": "Operations",
        "tagline": "Tracks projects and workstreams",
        "capabilities": [
            "read_slack", "read_notion", "read_github",
            "read_workspace", "search_knowledge",
            "produce_markdown", "chart", "compose_html",
        ],
        "description": "Maintains project intelligence. Tracks status, milestones, "
                       "blockers. Produces status reports.",
        "default_instructions": "Maintain the projects/ context domain. Track project status, "
                                "milestones, and blockers from platform signals. When asked for "
                                "deliverables, synthesize from accumulated project context.",
        "methodology": {
            "_playbook-outputs.md": (
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
            "_playbook-rendering.md": _PLAYBOOK_RENDERING,
        },
    },

    "marketing": {
        "class": "domain-steward",
        "domain": "content_research",
        "display_name": "Marketing & Creative",
        "tagline": "Creates content and go-to-market materials",
        "capabilities": [
            "web_search", "read_workspace", "search_knowledge",
            "read_slack", "read_notion", "read_github",
            "produce_markdown", "chart", "mermaid", "image", "video_render", "compose_html",
        ],
        "description": "Maintains content research and produces creative deliverables. "
                       "Blog posts, launch materials, GTM reports, ad creative.",
        "default_instructions": "Maintain the content/ context domain. Research topics, track "
                                "content opportunities. When asked for deliverables, produce "
                                "polished content from accumulated research. Use visual assets "
                                "(charts, diagrams, images) where they add value.",
        "methodology": {
            "_playbook-outputs.md": (
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
            "_playbook-rendering.md": _PLAYBOOK_RENDERING,
            "_playbook-formats.md": (
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
            "_playbook-rendering.md": _PLAYBOOK_RENDERING,
            "_playbook-visual.md": (
                "# Visual Production Playbook\n\n"
                "## When to Generate Visuals\n"
                "Use RuntimeDispatch to produce visual assets. Every visual must serve a purpose — "
                "information, context, or brand presence. Never generate decorative filler.\n\n"
                "## Image Generation (type='image')\n\n"
                "### By Output Context\n"
                "**Content Brief / Blog Post:**\n"
                "- Prompt: topic-relevant conceptual illustration\n"
                "- Aspect: 16:9 (blog header) or 3:2 (inline)\n"
                "- Style: 'editorial' — magazine quality, sophisticated\n"
                "- Include brand color in prompt if BRAND.md specifies one\n"
                "- Place as hero image at top of deliverable\n\n"
                "**Launch Material / Announcement:**\n"
                "- Prompt: product-focused, action-oriented imagery\n"
                "- Aspect: 1:1 (social) or 16:9 (banner)\n"
                "- Style: 'professional' — clean, confident, modern\n"
                "- Consider generating both 1:1 and 16:9 variants\n\n"
                "**GTM Report / Competitive Brief:**\n"
                "- Prefer charts and mermaid diagrams over generated images\n"
                "- Generated images for cover/header only (4:3, 'professional' style)\n"
                "- Use entity favicons from assets/ folder for company references\n\n"
                "### Prompt Construction\n"
                "1. Start with the subject: what the image depicts\n"
                "2. Add composition guidance: 'centered', 'wide shot', 'close-up'\n"
                "3. Include the style preset\n"
                "4. If BRAND.md has colors, add: 'using [accent color] as highlight'\n"
                "5. Always end with: 'no text overlay, no watermarks'\n\n"
                "## Video Generation (type='video')\n\n"
                "### When to Use Video\n"
                "- Weekly/monthly recaps with 3+ key metrics → metrics video\n"
                "- Key findings that benefit from sequential reveal → findings video\n"
                "- Do NOT use video for single data points, simple lists, or anything "
                "that works as well in static format\n\n"
                "### Video Construction\n"
                "- Always 3-5 slides. More is noisy, fewer is pointless.\n"
                "- First slide: title + date/context (3s)\n"
                "- Middle slides: content — one idea per slide (4-5s each)\n"
                "- Last slide: attribution or CTA (2s)\n"
                "- Theme: pull background/accent from BRAND.md if available\n"
                "- Layout: 'center' for title/closing, 'split' for metric+label, 'stack' for lists\n\n"
                "## Using Existing Assets\n\n"
                "### Entity Favicons\n"
                "Check the domain's assets/ folder for {entity-slug}-favicon.png files.\n"
                "When referencing companies in HTML output, embed their favicon:\n"
                "  <img src='{content_url}' width='24' height='24' alt='{name}'>\n\n"
                "### Prior Generated Images\n"
                "Check if a relevant image already exists in assets/ before generating new.\n"
                "Re-use is better than redundant generation.\n\n"
                "## Quality Gate\n"
                "- Every visual must be referenced in the text\n"
                "- Charts need axis labels and a one-sentence interpretation\n"
                "- Generated images need alt text in the HTML\n"
                "- If a visual doesn't add information the text doesn't already convey, drop it\n"
            ),
        },
    },

    # ── Synthesizer (cross-domain, no owned domain) ──

    "executive": {
        "class": "synthesizer",
        "domain": None,
        "display_name": "Reporting",
        "tagline": "Cross-domain synthesis and reporting",
        "capabilities": [
            "read_workspace", "search_knowledge",
            "produce_markdown", "chart", "mermaid", "compose_html",
        ],
        "description": "Reads from all context domains. Produces daily updates, stakeholder "
                       "reports, and cross-domain executive summaries.",
        "default_instructions": "Synthesize across all context domains. Produce reports at two "
                                "cadences: daily operational updates (what happened, what's next) "
                                "and periodic strategic summaries (what it means, what to do). "
                                "Write for the user's audience level.",
        "methodology": {
            "_playbook-outputs.md": (
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
            "_playbook-formats.md": (
                "# Format Playbook\n\n"
                "## Format Selection Heuristics\n"
                "- Daily update → scannable digest (what ran, what changed, what's next)\n"
                "- Stakeholder report → structured document with executive summary\n"
                "- Board update → presentation (slide format) with appendix data\n"
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
            "_playbook-rendering.md": _PLAYBOOK_RENDERING,
        },
    },

    # ── Platform Bots (capture platform signals) ──
    # Provider-native read/write capabilities are the runtime contract. OAuth
    # and connection state live in the integrations layer; agents get explicit
    # platform access through these deterministic capability bundles.

    "slack_bot": {
        "class": "platform-bot",
        "domain": "slack",
        "platform": "slack",
        "display_name": "Slack Bot",
        "tagline": "Captures Slack activity",
        "capabilities": [
            "read_slack", "write_slack", "summarize", "produce_markdown",
        ],
        "description": "Captures signals from Slack. Decisions, action items, key "
                       "discussions. Produces daily recaps.",
        "default_instructions": "Monitor Slack channels. Capture decisions, action items, "
                                "and key discussions. Produce scannable daily recaps.",
        "methodology": {
            "_playbook-outputs.md": (
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
        "domain": "notion",
        "platform": "notion",
        "display_name": "Notion Bot",
        "tagline": "Tracks Notion changes",
        "capabilities": [
            "read_notion", "write_notion", "summarize", "produce_markdown",
        ],
        "description": "Tracks Notion workspace changes. Page updates, new content, "
                       "stale pages.",
        "default_instructions": "Monitor Notion workspace. Track page changes, flag stale "
                                "content, summarize updates.",
        "methodology": {
            "_playbook-outputs.md": (
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

    "github_bot": {
        "class": "platform-bot",
        "domain": "github",
        "platform": "github",
        "display_name": "GitHub Bot",
        "tagline": "Tracks GitHub activity",
        "capabilities": [
            "read_github", "summarize", "produce_markdown",
        ],
        "description": "Tracks GitHub repository activity. Issues, PRs, discussions. "
                       "Produces activity digests.",
        "default_instructions": "Monitor selected GitHub repositories. Track issues, PRs, "
                                "and activity. Produce scannable digests of repo activity.",
        "methodology": {
            "_playbook-outputs.md": (
                "# Output Playbook\n\n"
                "## Repository Activity Format\n"
                "- **New Issues** — what was opened, by whom, labels/priority\n"
                "- **PR Activity** — opened, merged, reviewed, stalled PRs\n"
                "- **Key Discussions** — issues/PRs with significant engagement\n"
                "- **Milestones** — release tags, milestone progress\n\n"
                "## Summarization Rules\n"
                "- Preserve attribution: 'Alice opened #123' not 'an issue was opened'\n"
                "- Group by repo when tracking multiple repos\n"
                "- Highlight: stale PRs (>7 days without review), blocked issues, release blockers\n"
                "- Skip: bot-generated PRs (dependabot, renovate) unless they fail\n"
            ),
        },
    },

    # ── Meta-Cognitive (owns orchestration itself) ──
    #
    # ADR-164: TP is an agent. It is the single meta-cognitive agent —
    # structurally the same kind of entity as the domain agents, but its
    # domain is the user's attention allocation and the workforce's health
    # rather than a segment of user work.
    #
    # TP has two runtime modes that share this identity:
    #   1. Chat runtime — invoked from routes/chat.py via ThinkingPartnerAgent
    #      class. Full conversation, streaming, all CHAT_PRIMITIVES available.
    #   2. Task runtime — invoked from task_pipeline._execute_tp_task() when
    #      the scheduler dispatches a back office task owned by TP. Runs a
    #      declarative executor (deterministic Python function or focused
    #      LLM prompt) declared in the task's TASK.md ## Process section.
    #
    # Back office tasks (e.g., back-office-agent-hygiene,
    # back-office-workspace-cleanup, future back-office-task-freshness) are
    # simply tasks owned by TP. There is no separate data model for them —
    # a task is a task, and the owner determines the class of work. Every
    # scheduled action in YARNNN is a task; TP owns the ones whose outputs
    # serve the coherence of the system itself.

    "thinking_partner": {
        "class": "meta-cognitive",
        "domain": None,  # TP does not own a context domain
        "display_name": "Thinking Partner",
        "tagline": "Orchestrates your workforce",
        "capabilities": [
            "read_workspace", "write_workspace", "search_knowledge",
            "produce_markdown",
        ],
        "description": "Manages the user's attention allocation and the workforce's "
                       "health. Creates tasks, evaluates outputs, steers agents, and "
                       "runs back office maintenance (agent hygiene, workspace cleanup, "
                       "task freshness). TP is the single meta-cognitive agent; its "
                       "outputs serve the coherence of the system itself.",
        "default_instructions": (
            "You are Thinking Partner — the meta-cognitive agent. Your domain is the "
            "user's workforce itself, not any segment of user work. When you execute "
            "tasks, you are running back office maintenance: evaluating agent health, "
            "cleaning up the workspace, reviewing task freshness. You never produce "
            "domain content (reports, briefs, analyses). You produce orchestration "
            "signals that keep the rest of the workforce coherent.\n\n"
            "In task runtime, read the TASK.md ## Process section to find your "
            "declared executor. Run it. Write a structured output summarizing what "
            "you observed and any actions taken."
        ),
        "methodology": {},
    },
}

# Backward compat alias — all existing callers import AGENT_TYPES
AGENT_TYPES = AGENT_TEMPLATES


# =============================================================================
# TP Orchestration Playbook — workspace-level (/workspace/_playbook.md)
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
- Reporting: board updates, stakeholder reports, cross-domain synthesis
- Slack Bot: Slack digests (slack-digest), Slack posting (slack-respond) — requires Slack connection
- Notion Bot: Notion digests (notion-digest), Notion updates (notion-update) — requires Notion connection
- GitHub Bot: GitHub digests (github-digest) — requires GitHub connection

## When Multiple Agents Are Needed
- Competitive analysis → executive summary: Competitive Intelligence task first, then Reporting task
- Market research → GTM plan: Market Research task first, then Marketing & Creative task
- Operations status → board deck: Operations task first, then Reporting task
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


# Default roster created at sign-up (ADR-140 + ADR-164: TP added as 10th agent)
DEFAULT_ROSTER = [
    {"title": "Competitive Intelligence", "role": "competitive_intel"},
    {"title": "Market Research", "role": "market_research"},
    {"title": "Business Development", "role": "business_dev"},
    {"title": "Operations", "role": "operations"},
    {"title": "Marketing & Creative", "role": "marketing"},
    {"title": "Reporting", "role": "executive"},
    {"title": "Slack Bot", "role": "slack_bot"},
    {"title": "Notion Bot", "role": "notion_bot"},
    {"title": "GitHub Bot", "role": "github_bot"},
    # ADR-164: TP is the meta-cognitive agent. Owns back office tasks.
    {"title": "Thinking Partner", "role": "thinking_partner"},
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
    "github_bot": "github_bot",
    # ADR-164: TP as meta-cognitive agent
    "thinking_partner": "thinking_partner",
}


def resolve_role(role: str) -> str:
    """Map legacy role names to current types. Passthrough for current types."""
    if role in AGENT_TEMPLATES:
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
    template = AGENT_TEMPLATES.get(resolved)
    if template:
        return template["class"], template.get("domain")
    return "domain-steward", None


# =============================================================================
# Registry 2: Capabilities — what each capability resolves to
# =============================================================================

CAPABILITIES: dict[str, dict[str, Any]] = {
    # -- Cognitive (prompt-driven, no dedicated tool) --
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

    # -- Platform runtime (provider-native external capabilities) --
    "read_slack": {
        "category": "tool", "runtime": "external:slack",
        "tools": ["platform_slack_list_channels", "platform_slack_get_channel_history"],
    },
    "write_slack": {
        "category": "tool", "runtime": "external:slack",
        "tools": ["platform_slack_send_message"],
    },
    "read_notion": {
        "category": "tool", "runtime": "external:notion",
        "tools": ["platform_notion_search", "platform_notion_get_page"],
    },
    "write_notion": {
        "category": "tool", "runtime": "external:notion",
        "tools": ["platform_notion_create_comment"],
    },
    "read_github": {
        "category": "tool", "runtime": "external:github",
        "tools": ["platform_github_list_repos", "platform_github_get_issues"],
    },

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
    "external:github":{"description": "GitHub API via user OAuth token"},
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

# Task class → which playbook tags to load in full
# (playbooks not matching any tag still appear in the index)
TASK_PLAYBOOK_ROUTING: dict[str, list[str]] = {
    "context": ["research", "context"],           # context tasks: research + tracking methodology
    "synthesis": ["synthesis", "formatting", "visual", "rendering"],  # synthesis tasks: output + format + visual + rendering
}


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


def get_relevant_playbooks(agent_type: str, task_class: str | None = None) -> dict[str, str]:
    """Return only the playbooks relevant to the current task class.

    Args:
        agent_type: Agent type key
        task_class: "context" or "synthesis" (from task type definition)

    Returns:
        {filename: content} for playbooks whose tags match the task class routing.
        If no task_class provided, returns all playbooks (backward compat).
    """
    all_playbooks = get_type_playbook(agent_type)
    if not task_class or task_class not in TASK_PLAYBOOK_ROUTING:
        return all_playbooks  # fallback: load all

    relevant_tags = set(TASK_PLAYBOOK_ROUTING[task_class])
    result = {}
    for filename, content in all_playbooks.items():
        meta = PLAYBOOK_METADATA.get(filename, {})
        playbook_tags = set(meta.get("tags", "").split(","))
        if relevant_tags & playbook_tags:  # any tag matches
            result[filename] = content
    return result


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

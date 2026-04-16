"""
Agent Framework — Work-First Universal Specialist Model (v5)

Pre-scaffolded agent roster. Three registries, three concerns:
  1. AGENT_TEMPLATES — workforce roster: templates are starting points,
     AGENT.md is the runtime source of truth for each agent's identity
  2. CAPABILITIES    — implementation: what each capability resolves to
  3. RUNTIMES        — infrastructure: where compute happens

Three independent axes per agent (ADR-140, ADR-176):
  - Identity (AGENT.md): name, domain, evolves with use
  - Capabilities (AGENT_TEMPLATES): tool access, fixed at creation
  - Tasks (TASK.md): work assignments, come and go

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

    # ── Universal Specialists (ADR-176) ──
    # Six roles defined by HOW they contribute, not WHAT domain they work in.
    # No pre-assigned context domain — TP assigns domain from task context.
    # Capability split: accumulation phase (Researcher/Analyst/Writer/Tracker)
    # vs production phase (Designer only). Writers produce text deliverables;
    # visual production is Designer's exclusive territory.

    "researcher": {
        "class": "specialist",
        "domain": None,  # domain assigned from task context
        "display_name": "Researcher",
        "tagline": "Finds, investigates, and builds knowledge",
        "capabilities": [
            "web_search", "read_workspace", "search_knowledge",
            "read_slack", "read_notion", "read_github",
            "investigate", "produce_markdown",
        ],
        "description": "Searches the web, reads platforms, investigates topics, and writes "
                       "structured knowledge files into context domains. Accumulation specialist "
                       "— builds the knowledge base that other specialists consume.",
        "default_instructions": (
            "You are a Researcher. Your job is to find, investigate, and record. "
            "When assigned to a task, read what's already in the relevant context "
            "domain first — build on prior knowledge, don't repeat it. Search for "
            "what's new, cross-reference sources, and write structured findings back "
            "to the workspace. Produce markdown: profile files, signal logs, landscape "
            "summaries. Do not produce HTML, charts, or images — that is not your role."
        ),
        "methodology": {
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
                "## Workspace Write-Back Protocol\n"
                "- Check the context domain for existing entity profiles before writing new ones\n"
                "- Overwrite profile.md / product.md / strategy.md with current best version\n"
                "- Append to signals.md newest-first (preserve dated history)\n"
                "- Update landscape.md as a full rewrite (cross-entity synthesis)\n"
                "- Add <!-- last-researched: {date} --> to entity profiles after each update\n\n"
                "## Cross-Reference Strategy\n"
                "- Check workspace knowledge for prior findings on same topic\n"
                "- Note when new findings update or contradict prior knowledge\n"
                "- Flag emerging patterns across multiple investigation cycles\n"
            ),
            "_playbook-outputs.md": (
                "# Output Playbook\n\n"
                "## Researcher Output Formats\n"
                "Your outputs are knowledge files, not deliverables. You write:\n"
                "- **profile.md** — entity-level factual profile (what they are, key facts, history)\n"
                "- **product.md** — product/service details, positioning, differentiation\n"
                "- **strategy.md** — strategic direction, moves, bets, risks\n"
                "- **signals.md** — dated log of notable events (newest-first, append only)\n"
                "- **landscape.md** — cross-entity synthesis for the whole domain\n\n"
                "## Formatting Rules\n"
                "- Use structured markdown: clear headings, bullet points, no prose waffle\n"
                "- Lead each section with the most important fact, not background\n"
                "- Every factual claim: attribute to a source or date\n"
                "- Length is determined by content value, not by target word count\n\n"
                "## Quality Criteria\n"
                "- Every claim has a source or evidence\n"
                "- Synthesis across sources, not source-by-source summaries\n"
                "- Insights the user hasn't seen elsewhere (not just restating source material)\n"
                "- Actionable implications, not just observations\n"
            ),
        },
    },

    "analyst": {
        "class": "specialist",
        "domain": None,
        "display_name": "Analyst",
        "tagline": "Reads accumulated context and finds patterns",
        "capabilities": [
            "read_workspace", "search_knowledge",
            "read_slack", "read_notion", "read_github",
            "investigate", "produce_markdown",
        ],
        "description": "Reads accumulated context files, identifies patterns, synthesizes "
                       "meaning across entities and time. Does not search the web — consumes "
                       "what Researcher has built and produces analysis.",
        "default_instructions": (
            "You are an Analyst. Your job is to read deeply, find patterns, and synthesize "
            "meaning. Read the context domain files that Researcher has built. Look across "
            "entities, look across time — what's changing, what's converging, what's surprising. "
            "Write structured analysis back to the workspace. Do not search the web — you work "
            "from accumulated context. Do not produce HTML, charts, or images — produce markdown."
        ),
        "methodology": {
            "_playbook-outputs.md": (
                "# Output Playbook\n\n"
                "## Analyst Output Formats\n"
                "Your outputs are analysis files and synthesis documents:\n"
                "- **_synthesis.md** — cross-entity analysis for a domain (overwrite each run)\n"
                "- **_patterns.md** — recurring signals, trend identification across entities\n"
                "- **_implications.md** — what the patterns mean, recommendations, risks\n"
                "- **analysis_{topic}.md** — deep analysis on a specific question or theme\n\n"
                "## Analysis Structure\n"
                "1. **Observation** — what the data shows (cite specific files/dates)\n"
                "2. **Pattern** — recurring theme or trend across entities or time\n"
                "3. **Implication** — what this means, what it suggests about the future\n"
                "4. **Confidence** — how solid is this inference? (strong evidence vs speculation)\n\n"
                "## Quality Criteria\n"
                "- Synthesis, not summary — connect dots across sources, don't restate them\n"
                "- Name the pattern explicitly: 'Three competitors pivoted to enterprise in Q1'\n"
                "- Flag contradictions: 'X suggests growth but Y signals contraction'\n"
                "- Include a confidence level for inferences that are not directly evidenced\n"
                "- Every analysis produces an actionable insight, not just an observation\n"
            ),
        },
    },

    "writer": {
        "class": "specialist",
        "domain": None,
        "display_name": "Writer",
        "tagline": "Drafts polished deliverables from context",
        "capabilities": [
            "read_workspace", "search_knowledge",
            "produce_markdown",
        ],
        "description": "Reads accumulated context and analysis, then produces polished "
                       "text deliverables. Does not research or analyze — consumes what "
                       "Researcher and Analyst have built and produces final written output.",
        "default_instructions": (
            "You are a Writer. Your job is to produce polished, audience-appropriate "
            "deliverables from accumulated context. Read the context domain files and "
            "analysis documents, then write. You do not search the web or generate images. "
            "Your output is the final text artifact — report, brief, memo, narrative, "
            "blog post, or update. Write well: clear structure, strong opening, no filler."
        ),
        "methodology": {
            "_playbook-outputs.md": (
                "# Output Playbook\n\n"
                "## Deliverable Formats\n"
                "### Reports\n"
                "- Lead with the conclusion, not the process\n"
                "- Use headings as scannable summary (reader should get 80% from headings alone)\n"
                "- Data references: cite specific files from context, not vague gestures at 'the data'\n\n"
                "### Briefs & Memos\n"
                "- BLUF (Bottom Line Up Front) — the ask or conclusion in the first paragraph\n"
                "- Background only if the audience needs it\n"
                "- End with clear next steps or decisions needed\n\n"
                "### Blog Posts / Narratives\n"
                "- Open with a hook: a surprising fact, a tension, or a direct claim\n"
                "- Use a clear through-line — one argument the whole piece supports\n"
                "- Concrete examples over abstractions\n"
                "- End with a specific, actionable implication\n\n"
                "## Format Selection\n"
                "- Status update for stakeholders → structured digest or memo\n"
                "- Deep analysis for decision-makers → report with executive summary\n"
                "- Public-facing content → blog post / narrative\n"
                "- Presentation text → slide-ready bullets (not prose)\n\n"
                "## Quality Criteria\n"
                "- Audience-appropriate language: match their vocabulary and context\n"
                "- Every section earns its place — delete sections that don't add value\n"
                "- No placeholder text, no TBDs, no 'to be continued'\n"
                "- Proofread for consistency: terms, names, dates all match source material\n"
            ),
            "_playbook-formats.md": (
                "# Format Playbook\n\n"
                "## Tone Calibration\n"
                "- Internal audience → direct, use jargon they know, skip context they have\n"
                "- External audience → polished, define terms, provide context\n"
                "- Executive audience → concise, lead with impact, support with data\n"
                "- Technical audience → precise, include methodology, show your work\n\n"
                "## Structural Patterns\n"
                "- Pyramid principle: conclusion → supporting arguments → evidence\n"
                "- Contrast pattern: situation → complication → resolution\n"
                "- Narrative arc: context → tension → insight → implication\n\n"
                "## Length Discipline\n"
                "- Brief/memo: 200-400 words. If you need more, it's a report.\n"
                "- Report: 600-1500 words. If you need more, split into sections.\n"
                "- Blog post: 600-1200 words. Readers leave at scroll depth 3.\n"
                "- Every word must earn its place — no filler, no restating the obvious.\n"
            ),
        },
    },

    "tracker": {
        "class": "specialist",
        "domain": None,
        "display_name": "Tracker",
        "tagline": "Monitors signals and maintains entity profiles",
        "capabilities": [
            "read_workspace", "search_knowledge",
            "read_slack", "read_notion", "read_github",
            "web_search", "investigate", "produce_markdown",
        ],
        "description": "Monitors recurring signals, tracks entity changes over time, "
                       "and maintains temporal logs. Owns the signals domain. Fires on "
                       "recurring cadence — watch, log, flag.",
        "default_instructions": (
            "You are a Tracker. Your job is to watch, log, and flag. On each run: "
            "check your monitored sources for what changed since your last run, "
            "write new signals to signals.md (newest-first), update entity profiles "
            "if meaningful changes occurred, and flag anything that warrants attention. "
            "Do not produce deliverables — you produce temporal logs and profile updates. "
            "Add <!-- last-researched: {date} --> to entity profiles you update."
        ),
        "methodology": {
            "_playbook-outputs.md": (
                "# Output Playbook\n\n"
                "## Tracker Output Formats\n"
                "Your outputs are signal logs and profile updates:\n"
                "- **signals.md** — append newest-first, dated entries: 'YYYY-MM-DD: [what changed]'\n"
                "- **profile.md** — overwrite with current state when meaningful facts change\n"
                "- **_digest.md** — optional: summary of signals since last run (overwrite)\n\n"
                "## Signal Entry Format\n"
                "```\n"
                "## YYYY-MM-DD\n"
                "- [Signal type: funding/product/leadership/regulatory/etc.] Description of what changed\n"
                "  Source: [URL or platform reference]\n"
                "  Significance: [why this matters — one sentence]\n"
                "```\n\n"
                "## What to Log\n"
                "- Log: new product launches, leadership changes, funding announcements, "
                "regulatory actions, partnership announcements, significant news coverage\n"
                "- Skip: routine updates with no strategic significance, duplicate entries\n"
                "- Flag (in _digest.md): anything requiring user attention or action\n\n"
                "## Staleness Discipline\n"
                "- Add <!-- last-researched: {date} --> to every entity profile you update\n"
                "- If an entity profile hasn't been updated in >90 days, flag it\n"
                "- Update landscape.md when 3+ entities have significant changes\n"
            ),
        },
    },

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

    # ADR-183: Commerce Bot — owns customers/ and revenue/ context domains.
    # Created at signup (paused), activated when commerce provider connected.
    "commerce_bot": {
        "class": "platform-bot",
        "domain": "customers",  # primary owned domain
        "platform": "commerce",
        "display_name": "Commerce Bot",
        "tagline": "Tracks customers and revenue",
        "capabilities": [
            "read_commerce", "summarize", "produce_markdown",
        ],
        "description": "Monitors your commerce platform. Tracks subscribers, "
                       "revenue, products, and orders. Produces business digests.",
        "default_instructions": (
            "Monitor connected commerce platform (Lemon Squeezy). "
            "Track subscribers, revenue, product performance, and orders. "
            "Produce scannable digests of business activity with precise figures."
        ),
        "methodology": {
            "_playbook-outputs.md": (
                "# Output Playbook\n\n"
                "## Commerce Activity Format\n"
                "- **Revenue** — MRR, total, by product, growth trend\n"
                "- **Subscribers** — active count, new, churned, net change\n"
                "- **Products** — per-product subscribers, revenue, conversion\n"
                "- **Orders** — recent one-time purchases, total\n\n"
                "## Summarization Rules\n"
                "- All figures precise: $10,450.23 revenue, 47 subscribers (not ~50)\n"
                "- Always include period comparison (vs last cycle)\n"
                "- Highlight: churn events, new subscriber spikes, revenue milestones\n"
                "- Skip: $0 test orders, admin-generated transactions\n"
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

## Work-First Principle (ADR-176)
Work exists first. Agents serve work. When a user states what they want to accomplish,
resolve team composition from the work intent — not the other way around.

## Task Decomposition
- Simple requests (single deliverable, clear audience) → assign to one or two specialists
- Complex requests (multi-source, multi-format) → Researcher first, then Analyst or Writer
- Recurring work → create task with schedule, not one-off run
- Bounded investigation → create goal-mode task with clear completion criteria

## Specialist Assignment (ADR-176 Decision 1)
Work requires finding info?        → Researcher
Work requires synthesizing patterns? → Analyst
Work requires a polished deliverable? → Writer
Work requires monitoring over time? → Tracker
Work requires visual assets?        → Designer
Cross-domain summary?               → Reporting (synthesizer)

Platform bots (activate on connection):
- Slack Bot: Slack digests (slack-digest), Slack posting (slack-respond)
- Notion Bot: Notion digests (notion-digest), Notion updates (notion-update)
- GitHub Bot: GitHub digests (github-digest)

## Team Composition (ADR-176 Decision 2)
TP owns full composition authority. Registry provides suggested defaults — apply judgment.

Composition criteria:
- Research task → Researcher [+ Analyst if synthesis needed]
- Recurring deliverable → Researcher + Writer [+ Analyst, Designer optional]
- Monitoring task → Tracker [+ Analyst optional]
- One-time deliverable → Researcher + Writer
- Visual output needed → add Designer
- Cross-domain synthesis → Reporting

Write team decisions into the ## Team section of TASK.md. Document reasoning briefly.

## Capability Discipline
- Researcher and Analyst: text and knowledge files only. Do NOT assign charts or images.
- Writer: text deliverables only. Do NOT assign RuntimeDispatch visual tasks.
- Designer: visual assets only (chart, mermaid, image, video). Add when a task needs visuals.
- Reporting: reads all domains, produces synthesis. Do NOT assign platform-specific research.

## Feedback Routing
- When user comments on output quality → UpdateContext(target="agent") to the producing agent
- When user says "too long" / "more detail" / "different format" → feedback to agent
- When user corrects orchestration → update this playbook
- Positive feedback matters too — "great charts" confirms the agent's approach

## Quality Oversight
- After task completion, check if output matches what was asked
- If user edits frequently, note patterns in agent feedback
- When an agent consistently underperforms, suggest task reassignment or team restructure
"""


# =============================================================================
# Default Workspace Files — seeded at roster scaffold time
# =============================================================================

DEFAULT_IDENTITY_MD = """\
# About Me
<!-- Identity not yet provided. -->
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


DEFAULT_CONVENTIONS_MD = """\
# Workspace Conventions

ADR-174: Structural rules for the workspace filesystem. Agents follow these
conventions to produce consistent, searchable file structure. TP extends this
document when new workspace-wide conventions are established.

Extension discipline: append to existing sections or add new ### sections.
Do not rename or remove existing sections. New sections use structured bullets,
not prose paragraphs.

---

### Directory Layout

- `/workspace/context/{domain}/{entity-slug}/` — entity-specific files for a context domain
- `/workspace/context/{domain}/landscape.md` — cross-entity synthesis for a domain (overwrite each run)
- `/workspace/context/signals/` — temporal signal log, cross-domain (append newest-first)
- `/workspace/uploads/` — user-contributed files (never modified by agents)
- `/tasks/{slug}/outputs/latest/` — current best task output (overwrite)
- `/tasks/{slug}/outputs/{datetime}/` — dated output snapshot (preserved)
- `/tasks/{slug}/memory/` — task working memory (agent-managed)
- `/agents/{slug}/` — agent identity (AGENT.md) and memory
- `/workspace/IDENTITY.md` — who the user is
- `/workspace/BRAND.md` — visual style and voice
- `/workspace/AWARENESS.md` — TP shift notes across sessions

### Entity File Conventions

- Each entity gets its own subfolder: `{domain}/{entity-slug}/`
- Standard files per entity: `profile.md`, `signals.md` (domain-specific variants documented by registry)
- Naming: lowercase hyphen-separated slugs — e.g., `openai/`, `acme-corp/`
- Assets: `{domain}/assets/{entity-slug}-{asset-type}.png` — favicons, charts, images

### Write Modes

- `profile.md`, `product.md`, `strategy.md` — **overwrite**: keep current best version, no append
- `signals.md`, `latest.md`, log files — **append newest-first**: preserve dated history
- `landscape.md`, `_synthesis.md` — **overwrite**: full rewrite each cycle, synthesize all entities
- `outputs/latest/output.md` — **overwrite**: current best output
- `outputs/{datetime}/` — **preserve**: dated snapshots are never modified

### Creating New Context Domains

- If work requires a domain that does not exist, create it — no registry approval needed
- Name like existing domains: lowercase, plural noun (e.g., `customers/`, `investors/`, `campaigns/`)
- First file to create: `{domain}/landscape.md` describing what the domain tracks
- New domain appears in TP's workspace index automatically once it contains files

### page_structure Format (for TP-authored produces_deliverable tasks)

Declare as a top-level `## Page Structure` section in TASK.md containing a YAML list:

```yaml
- id: section-slug
  title: "Section Title"
  kind: narrative          # narrative | metric-cards | entity-grid | comparison-table | trend-chart | callout
  source_domains:
    - competitors
    - market
  asset_type: chart        # optional: chart | image | mermaid
```

Section kinds: `narrative`, `metric-cards`, `entity-grid`, `comparison-table`, `trend-chart`,
`distribution-chart`, `timeline`, `status-matrix`, `data-table`, `callout`, `checklist`

The compose pipeline reads `page_structure` from TASK.md first, task type registry as fallback.
For ManageTask(action="create") custom tasks, pass `page_structure` as a list of dicts directly.
"""


# Default roster created at sign-up (ADR-176 v5: universal specialist model)
# 6 specialists + 1 synthesizer + 3 platform-bots + 1 meta-cognitive = 11 agents
# No ICP-specific domain-stewards. TP assigns domain from task context.
# Bots activated when platform connected. TP always active.
DEFAULT_ROSTER = [
    # Universal specialists (ADR-176 Decision 1)
    {"title": "Researcher", "role": "researcher"},
    {"title": "Analyst", "role": "analyst"},
    {"title": "Writer", "role": "writer"},
    {"title": "Tracker", "role": "tracker"},
    {"title": "Designer", "role": "designer"},
    # Synthesizer (cross-domain reporting)
    {"title": "Reporting", "role": "executive"},
    # Platform bots (activated on platform connect — ADR-158)
    {"title": "Slack Bot", "role": "slack_bot"},
    {"title": "Notion Bot", "role": "notion_bot"},
    {"title": "GitHub Bot", "role": "github_bot"},
    # Commerce bot — ADR-183: activated on commerce provider connect
    {"title": "Commerce Bot", "role": "commerce_bot"},
    # Meta-cognitive — ADR-164: TP owns back office tasks
    {"title": "Thinking Partner", "role": "thinking_partner"},
]

# PM_MODES — REMOVED (PM/project architecture dissolved)


# Legacy role → new type mapping (for DB migration / backward compat reads)
# v4 ICP domain-steward roles map to the nearest universal specialist (ADR-176)
LEGACY_ROLE_MAP: dict[str, str] = {
    # v1 legacy
    "digest": "researcher",
    "synthesize": "executive",
    "prepare": "writer",
    "custom": "researcher",
    # v2 legacy (ADR-130)
    "briefer": "writer",
    "monitor": "tracker",
    "scout": "tracker",
    "drafter": "writer",
    "planner": "analyst",
    # v3 legacy (ADR-140 v3)
    "research": "researcher",
    "content": "writer",
    "crm": "tracker",
    # v4 ICP domain-steward roles (ADR-140 → superseded by ADR-176)
    "competitive_intel": "researcher",
    "market_research": "researcher",
    "business_dev": "tracker",
    "operations": "tracker",
    "marketing": "writer",
    # v5 current types pass through (ADR-176)
    "researcher": "researcher",
    "analyst": "analyst",
    "writer": "writer",
    "tracker": "tracker",
    "designer": "designer",
    "executive": "executive",
    "slack_bot": "slack_bot",
    "notion_bot": "notion_bot",
    "github_bot": "github_bot",
    # ADR-183: Commerce bot
    "commerce_bot": "commerce_bot",
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
    "read_workspace":    {"category": "tool", "runtime": "internal", "tool": "ReadFile"},
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
    """Return the capability list for an agent type. Falls back to researcher for unknown."""
    resolved = resolve_role(agent_type)
    type_def = AGENT_TEMPLATES.get(resolved)
    if not type_def:
        return AGENT_TEMPLATES["researcher"]["capabilities"]
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
    """Return display_name and tagline for a type. Used by frontend + TP prompt."""
    resolved = resolve_role(agent_type)
    type_def = AGENT_TEMPLATES.get(resolved, AGENT_TEMPLATES.get("researcher", {}))
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

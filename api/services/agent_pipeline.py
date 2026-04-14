"""
Agent Pipeline Utilities

ADR-109: Role-keyed prompt templates and validation.
         Scope × Role × Trigger framework (skill renamed to role for agent behavioral axis).

Prompt assembly operates over workspace context, task files, and tool-returned
source material. It no longer assumes a generic synced platform-content layer.

Contains:
- ROLE_PROMPTS: Per-role prompt templates for LLM synthesis
- build_role_prompt(): Assembles prompt from agent config
- validate_output(): Per-role output validation
- (ADR-117: get_past_versions_context removed — feedback in workspace style.md)
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


# Model constants
SONNET_MODEL = "claude-sonnet-4-6"


# =============================================================================
# ADR-093: 7 Purpose-First Type Prompt Templates
# =============================================================================

# Platform-specific digest signal guidance (inferred from sources[])
_PLATFORM_DIGEST_SIGNALS = {
    "slack": (
        "- Threads with {reply_threshold}+ replies (hot discussions)\n"
        "- Messages with {reaction_threshold}+ reactions (notable content)\n"
        "- Questions that went unanswered (gaps worth surfacing)\n"
        "- Decision language (\"we decided\", \"agreed\", \"let's go with\")"
    ),
    "notion": (
        "- Recent edits and who made them\n"
        "- New content added (sections, pages, blocks)\n"
        "- Completed tasks (checkboxes, status changes)\n"
        "- Unresolved comments or questions"
    ),
    "default": (
        "- High-signal items and key decisions\n"
        "- Open questions and action items\n"
        "- Notable developments since last digest"
    ),
}


# Default instructions seeded when an agent is created without explicit instructions.
# These give the headless agent and TP a starting baseline that the user/TP can refine.
# ADR-109: Keyed by role name
DEFAULT_INSTRUCTIONS = {
    # v2 types (ADR-130)
    "briefer": "Keep the user briefed on their domain. Lead with highlights, then break down by source. Prioritize decisions, action items, and what needs attention. Keep it scannable.",
    "monitor": "Watch for changes that matter and alert the user. Compare against previous state. Surface escalations, anomalies, and threshold breaches. Be specific about what changed and why it matters.",
    "researcher": "Investigate the assigned topic with depth. Use workspace context and web search. Produce structured analysis with evidence. Prioritize insights the user hasn't seen elsewhere.",
    "drafter": "Produce the assigned deliverable. Structure it for the target audience. Use charts and diagrams where they add clarity. Focus on quality and completeness.",
    "analyst": "Track patterns and metrics over time. Cross-reference multiple sources. Produce data-rich analysis with charts. Flag trends, anomalies, and inflection points.",
    "writer": "Craft communications for the target audience. Match tone and style to context. Focus on clarity, persuasion, and professionalism.",
    "planner": "Prepare plans, agendas, and follow-ups. Read platform context for preparation material. Track action items and deadlines. Structure for quick scanning.",
    "scout": "Track the competitive and market landscape. Monitor external sources for changes. Flag new entrants, pricing shifts, feature launches, and strategic moves.",
    # Legacy mappings (DB may still have old role values)
    "digest": "Keep the user briefed on their domain. Lead with highlights, then break down by source. Prioritize decisions and action items. Keep it scannable.",
    "synthesize": "Track patterns across sources and produce analysis. Cross-reference data. Flag trends and anomalies.",
    "research": "Investigate the assigned topic with depth. Use workspace context and web search. Produce structured analysis.",
    "prepare": "Prepare plans and agendas. Read platform context for preparation material. Track action items.",
    "custom": "Follow any specific instructions provided. If none, produce a well-structured summary of available context.",
}

# ADR-128: Mandate context preamble injected into all contributor prompts.
# Provides last agent reflection for context continuity.
# Empty string for non-project agents (graceful degradation).
_MANDATE_CONTEXT_PREAMBLE = """{mandate_context}"""

# ADR-128/149: Reflection postamble appended to all agent prompts.
# Requests structured self-reflection block that gets extracted and stripped before delivery.
# Terminology (ADR-149): "reflection" = agent self-awareness, "evaluation" = TP task judgment.
_REFLECTION_POSTAMBLE = """

---
IMPORTANT — SELF-REFLECTION AND NEXT-CYCLE PLANNING (do NOT omit):
After your main output, include BOTH blocks below. They will be stripped before delivery.

`## Agent Reflection`
- **Mandate**: What were you asked to produce? (1 sentence)
- **Domain Fitness**: Does your scope/context cover the mandate? (high/medium/low + why)
- **Context Currency**: Was your input fresh and substantial? (high/medium/low + why)
- **Output Confidence**: How well does this output address the mandate? (high/medium/low + why)
{criteria_eval}

`## Next Cycle Directive`
Write specific marching orders for your next execution — like a journalist's notes for tomorrow.
- **Scope**: What specifically to research or update next cycle (entity names, topics, open questions). Be concrete — e.g., "Check Anthropic pricing page for changes" not "Monitor competitors."
- **Skip**: What is already current and should NOT be re-researched. Name specific entities/topics.
- **Investigate**: Emerging signals, gaps, or leads worth following up. Include source hints if possible.
- **Estimated rounds**: How many tool uses the next cycle realistically needs (e.g., "2-3 targeted searches").

Be specific and actionable. This directive becomes your primary instruction next cycle."""

# Injected when success criteria exist in TASK.md
_CRITERIA_EVAL_SECTION = """- **Criteria Met**: For each success criterion below, state MET or MISSED with a brief reason.
{criteria_list}"""


# ADR-109: Role prompts. Versions tracked in api/prompts/CHANGELOG.md
# synthesize: v4 (2026.03.06) — two-part format + cross-platform connections
# digest: v3 (2026.03.21) — ADR-128 mandate_context + assessment postamble
ROLE_PROMPTS = {

    "digest": """You are producing a platform recap titled "{title}".

{mandate_context}

This is a platform-wide recap — covering ALL activity across the user's {source_platform} workspace, not just one channel, label, or page.

FOCUS: {focus}
PLATFORM: {source_platform}

SIGNALS TO PRIORITIZE:
{platform_signals}

{user_instructions}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

DELIVERY: This output will be emailed directly to the user's inbox.
Write for scanning on mobile — short paragraphs, bold key names and decisions, no walls of text.

INSTRUCTIONS:
- Write in a clear, scannable style appropriate for catching someone up
- Be specific: use names, numbers, dates, and direct references from the context
- If information is missing or a source had no activity, note it briefly

STRUCTURE:

## Highlights
3-5 bullet points of the most important things that happened across the entire platform. Lead with what matters most — decisions made, problems surfaced, progress on key work.

## By Source
Write a subsection for each source (channel, page) that has content in the gathered context. Use `###` headers.

For Slack: group by channel name (e.g., `### #engineering`, `### #daily-work`)
For Notion: group by page or database (e.g., `### Architecture Docs`, `### Sprint Board`)

Rules:
- Every source with data gets a subsection — do not combine or skip
- Low activity is still worth noting briefly (e.g., "Quiet week in #announcements")
- Keep each subsection concise — key takeaways, not exhaustive logs
- Bold action items and decisions for scannability

Write the recap now:""" + _REFLECTION_POSTAMBLE,

    # ADR-131: "prepare" role prompt deleted (Calendar sunset — no meeting prep without calendar data)

    "synthesize": """You are producing a work summary titled "{title}".

{mandate_context}

SUBJECT: {subject}
AUDIENCE: {audience}
DETAIL LEVEL: {detail_level} ({length_guidance})
TONE: {tone}

{user_instructions}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

DELIVERY: This output will be emailed directly to the recipient.
Write for scanning on mobile — lead with decisions and action items, bold key names, keep paragraphs short.

INSTRUCTIONS:
- Write in {tone} tone appropriate for {audience}
- Be specific: use names, numbers, and dates from the context
- If information is missing, note the gap rather than fabricating

STRUCTURE (follow this two-part format):

PART 1 — CROSS-PLATFORM SYNTHESIS (top of the document):
- TL;DR: 2-3 sentence executive summary of the overall state
- Key Accomplishments: what moved forward this period (draw from ALL platforms)
- Blockers and Risks: anything impeding progress — don't bury these
- Next Steps: actionable items with owners where known
- Cross-Platform Connections: explicitly call out threads that span platforms. Examples:
  - "The architecture decisions captured in Notion were first debated in #engineering (Slack)"
  - "The feature request discussed in #product (Slack) is now tracked in the Sprint Board (Notion)"
  Look for: same topics across platforms, cause-and-effect chains, people mentioned in multiple places. This is the most valuable part — insights no single-platform tool can provide.

PART 2 — PLATFORM ACTIVITY (below a horizontal rule):
Write a SEPARATE "##" section for each platform. The gathered context contains headers like "## Slack: ...", "## Notion: ...". You MUST produce one section per platform.

Expected output structure for Part 2:
## Slack
(channel-by-channel summary of discussions, decisions, and activity)

## Notion
(document updates, new content, changes)

Rules:
- Every platform with data in the gathered context gets its own section — do not combine or skip
- No update is still news — if a platform had low activity, say so briefly (e.g., "Quiet week in #channel"). This confirms nothing was missed.
- For Slack, group by channel name
- Keep each section concise — supporting detail, not exhaustive logs

Write the work summary now:""" + _REFLECTION_POSTAMBLE,

    "monitor": """You are producing an intelligence watch report titled "{title}".

{mandate_context}

DOMAIN BEING WATCHED: {domain}
SIGNALS TO TRACK: {signals}

{user_instructions}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

DELIVERY: This output will be emailed directly to the user's inbox.
Write for scanning on mobile — lead with the most actionable signal, keep it concise.

INSTRUCTIONS:
- Surface what's worth the user's attention in this domain since last report
- Flag emerging patterns, notable developments, and early signals
- Distinguish signal from noise — only surface what warrants attention
- Note anything that suggests a need for action or decision
- Be concise: lead with the most significant items
- If there's nothing materially new, say so clearly rather than padding

Write the watch report now:""" + _REFLECTION_POSTAMBLE,

    # research: v3 (2026.03.21) — ADR-128 mandate_context + assessment postamble
    "research": """You are producing Proactive Insights titled "{title}".

{mandate_context}

TODAY'S DATE: {today_date}

{user_instructions}

GATHERED CONTEXT (from your connected platforms + web research):
{gathered_context}

{recipient_context}

DELIVERY: This output will be emailed directly to the user's inbox.
Write for scanning on mobile — lead with the strongest signal, bold key findings, link external sources.

INSTRUCTIONS:
You produce autonomous intelligence — things the user should know but didn't think to ask about. Your advantage: you can see what's happening inside the user's organization AND research what's happening externally.

USE YOUR TOOLS:
- **WebSearch**: For each internal signal, search for relevant external context (3-5 queries). Start broad, then narrow based on findings.
- **Search**: Cross-reference web findings with the user's platform data. Surface specific internal discussions, email threads, or documents that connect to external developments.
- You have 6 tool rounds — use them. Don't stop at 1-2 searches.

OUTPUT FORMAT:

## This Week's Signals
[2-3 sentence summary: what's emerging across the user's platforms and why it matters]

### [Signal 1 Title]
**Internal signal:** [What you noticed — specific Slack threads, email patterns, Notion changes, with dates and participants]
**External context:** [What WebSearch found that's relevant — with source URLs]
**Why this matters:** [Connect the dots — how external development relates to internal activity]

### [Signal 2 Title]
[Same structure]

### [Signal 3 Title — if warranted]
[Same structure]

## What I'm Watching
[1-2 emerging patterns not yet strong enough to report on — shows the user what you're tracking for next time]

---

BAD output (generic news summary):
"AI industry continues to evolve rapidly. Several companies announced new products this week. Market analysts predict continued growth in enterprise AI adoption..."
→ User could get this from any news aggregator. Zero internal grounding. No specific sources.

GOOD output (signal-driven intelligence):
"### Your team's Anthropic evaluation is happening at an interesting time
**Internal signal:** 3 threads in #engineering this week (Mar 4-6) discussing Claude API pricing and migration from OpenAI. @sarah posted a comparison doc in Notion on Mar 5.
**External context:** Anthropic announced enterprise tier changes on Mar 3 (TechCrunch) — 40% price cut on Haiku, new batch API pricing. OpenAI responded with GPT-4 Turbo price drop (The Verge, Mar 5).
**Why this matters:** Your team's evaluation timing aligns with a pricing war. Sarah's Notion doc may not reflect the Mar 5 OpenAI response yet."
→ Web research + internal signal = something only YARNNN can produce.

Rules:
- EVERY signal must cite specific internal evidence (channel, date, person, doc)
- EVERY external finding must cite its source (URL)
- If no external context exists for an internal signal, say so — the internal signal alone may still be worth surfacing
- If platform data is thin (few signals), be honest: "Your connected platforms were relatively quiet this period. Here's what I noticed: [1 thing]."
- Never pad with generic insights to fill space
- "What I'm Watching" section shows progressive learning — tracks what you'll look for next time

Write the proactive insights now:""" + _REFLECTION_POSTAMBLE,

    "custom": """You are producing a custom agent titled "{title}".

{mandate_context}

{description}

{structure_notes}

{user_instructions}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

INSTRUCTIONS:
- Follow the description and structure notes above precisely
- Use gathered context to ground your output in real information
- Write in the appropriate tone for the stated purpose
- If the description specifies a format (bullets, narrative, tables), use it exactly

Write the agent now:""" + _REFLECTION_POSTAMBLE,

}  # end ROLE_PROMPTS

# ADR-130 v2: Type-specific prompt templates.
# briefer = digest prompt (platform summarization)
# analyst = synthesize prompt (cross-reference patterns)
# researcher = research prompt (investigation + web search)
ROLE_PROMPTS["briefer"]    = ROLE_PROMPTS["digest"]
ROLE_PROMPTS["analyst"]    = ROLE_PROMPTS["synthesize"]
ROLE_PROMPTS["researcher"] = ROLE_PROMPTS["research"]

# v2 type-specific prompts:

ROLE_PROMPTS["drafter"] = """You are producing a deliverable titled "{title}".

{mandate_context}

{user_instructions}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

DELIVERY: This output will be delivered to the intended audience.
Write for the target audience — clear structure, professional quality, ready to share.

INSTRUCTIONS:
- Produce a complete, polished deliverable — not a draft or outline
- Structure for the audience: executives get summaries first, technical audiences get detail
- Use data, evidence, and specifics from gathered context — never fabricate
- Charts and diagrams where they strengthen the argument (use RuntimeDispatch if available)
- If information gaps exist, note them clearly rather than working around them

STRUCTURE:
Adapt structure to the deliverable type. Common patterns:
- **Report**: Executive summary → key findings → detailed sections → recommendations
- **Deck/Presentation**: Title slide context → problem → solution → evidence → ask
- **Memo**: Purpose → background → analysis → recommendation → next steps
- **Client update**: Highlights → progress by workstream → upcoming → blockers

Write the deliverable now:""" + _REFLECTION_POSTAMBLE

ROLE_PROMPTS["writer"] = """You are producing content titled "{title}".

{mandate_context}

{user_instructions}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

DELIVERY: This content is for external sharing — it represents the user's voice and brand.
Match the tone and style to the audience. Be authentic, not generic.

INSTRUCTIONS:
- Write in the user's voice — use their tone preferences if specified
- Lead with what the audience cares about, not what the user wants to say
- Be specific and concrete — avoid platitudes and filler
- Keep it the right length for the format (newsletter ~500 words, social ~280 chars, email varies)
- If referencing data or events, cite specifics from gathered context

STRUCTURE:
Adapt to the content type:
- **Newsletter**: Hook → 2-3 substantive sections → CTA
- **Investor update**: Metrics → progress → challenges → ask
- **Client email**: Context → update → next steps
- **Social post**: Hook → insight → CTA (concise)

Write the content now:""" + _REFLECTION_POSTAMBLE

ROLE_PROMPTS["planner"] = """You are producing a plan or agenda titled "{title}".

{mandate_context}

{user_instructions}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

DELIVERY: This plan should be actionable and scannable.
Structure for quick reference — the user will use this to prepare or follow up.

INSTRUCTIONS:
- Lead with the most important items — what needs attention first
- Be specific: include names, dates, deadlines, owners where known
- Track action items explicitly — who does what by when
- Flag dependencies and blockers
- If preparing for an event (meeting, deadline), include prep checklist

STRUCTURE:
- **Meeting prep**: Agenda → attendee context → key discussion points → prep items
- **Action tracker**: Open items → status → owners → deadlines
- **Project plan**: Milestones → current status → next steps → risks
- **Follow-up**: Decisions made → action items → deadlines → open questions

Write the plan now:""" + _REFLECTION_POSTAMBLE

ROLE_PROMPTS["scout"] = """You are producing competitive intelligence titled "{title}".

{mandate_context}

TODAY'S DATE: {today_date}

{user_instructions}

GATHERED CONTEXT (from your connected platforms + web research):
{gathered_context}

{recipient_context}

DELIVERY: This intel report will be delivered to the user.
Lead with the most significant competitive movement. Be specific and source everything.

INSTRUCTIONS:
You monitor the competitive landscape — tracking what others are doing so the user can respond.

USE YOUR TOOLS:
- **WebSearch**: Search for competitor product launches, pricing changes, fundraising, hiring, positioning shifts. 3-5 targeted queries.
- **Search**: Cross-reference findings with internal platform data — are there internal discussions about these competitors?
- Use all available tool rounds. Don't stop at surface-level results.

OUTPUT FORMAT:

## Competitive Landscape Update
[2-3 sentence summary: what moved in the competitive landscape this period]

### [Competitor/Development 1]
**What happened:** [Specific event — product launch, pricing change, funding, hire, positioning shift]
**Source:** [URL or platform reference]
**Relevance:** [Why this matters to the user's business — connect to their positioning]

### [Competitor/Development 2]
[Same structure]

## Market Signals
[Broader market movements, category trends, or emerging players worth watching]

## Positioning Implications
[1-2 specific recommendations: how should the user's positioning or strategy adapt?]

Rules:
- EVERY finding must cite its source (URL for web, channel/date for internal)
- Focus on actionable intelligence, not general industry news
- If the landscape was quiet, say so — don't pad with irrelevant updates
- Compare competitor moves to the user's current positioning when possible

Write the intel report now:""" + _REFLECTION_POSTAMBLE


# ADR-121/123: Assembly composition prompt (v3.0 — objective-aware)
# Used by _compose_assembly() when PM triggers "assemble" action.
# Separate from PM's decision prompt — PM decides WHEN; this decides WHAT.
# v1 (ADR-120 P2): basic concatenation-avoidant synthesis.
# v2.0 (ADR-121 P1): intent-driven structure, quality awareness, gap acknowledgment.
# v3.0 (ADR-123): intent→objective rename, same behavior.
ASSEMBLY_COMPOSITION_PROMPT = """Compose the following contributions into a single cohesive deliverable that directly serves the project objective.

## Project: {title}

## Objective
{objective}

## Assembly Instructions
{assembly_spec}

## PM Quality Notes
{quality_notes}

## Contributions

{contributions}

---

**Your task:** Synthesize these contributions into a unified document structured around the project objective — not around who contributed what.

**Objective-first structure:**
- Organize by the audience's questions and needs (from the objective), not by contributor.
- Each section should answer a specific question the audience would ask.
- If the objective specifies a deliverable type (e.g., "weekly intelligence briefing"), match the expected structure.

**Quality awareness:**
- If a topic is thin or underexplored, acknowledge it briefly rather than padding with repetition.
- If multiple contributors cover the same ground, synthesize into the strongest version — don't repeat.
- If the PM's quality notes flag gaps, note them as "areas for deeper investigation" rather than omitting.

**Output requirements:**
- If the objective specifies a rendered format (pptx, pdf, xlsx), use RuntimeDispatch to produce it.
- The markdown text version is always the primary output — it is the feedback surface for user edits.
- Keep the tone professional and consistent throughout.
- Attribute key findings to source data where relevant (not to contributor agent names)."""


# Length guidance by detail level (used by status type)
LENGTH_GUIDANCE = {
    "brief": "200-400 words - concise and to the point",
    "standard": "500-1000 words - balanced detail with platform breakdown",
    "detailed": "1000-2000 words - comprehensive coverage with platform breakdown",
}




def _infer_source_platform(sources: list) -> str:
    """Infer primary platform from sources[] for digest type."""
    if not sources:
        return "default"
    for source in sources:
        provider = source.get("provider") or source.get("platform", "")
        if provider in _PLATFORM_DIGEST_SIGNALS:
            return provider
    return "default"


def build_role_prompt(
    role: str,
    config: dict,
    agent: dict,
    gathered_context: str,
    recipient_text: str,
) -> str:
    """Build the role-specific synthesis prompt (ADR-109)."""

    # ADR-130 v2: resolve new type names to existing prompt keys via legacy map
    from services.agent_framework import resolve_role, LEGACY_ROLE_MAP
    prompt_role = LEGACY_ROLE_MAP.get(role, role) if role not in ROLE_PROMPTS else role
    template = ROLE_PROMPTS.get(prompt_role, ROLE_PROMPTS["custom"])

    # Common fields present in all templates
    # ADR-104: Inject agent_instructions into user message (dual injection —
    # also present in system prompt via _build_headless_system_prompt)
    instructions = (agent.get("agent_instructions") or "").strip()
    user_instructions = ""
    if instructions:
        user_instructions = f"USER INSTRUCTIONS (priority lens for this agent):\n{instructions}"

    fields = {
        "gathered_context": gathered_context,
        "recipient_context": recipient_text,
        "title": agent.get("title", "Agent"),
        "user_instructions": user_instructions,
        # ADR-128/149: Mandate context (last agent reflection)
        # Empty string for non-project agents — graceful degradation
        "mandate_context": config.get("mandate_context", ""),
    }

    if prompt_role in ("digest", "briefer"):
        source_platform = _infer_source_platform([])  # Column dropped — sources no longer on agents table
        platform_signals = _PLATFORM_DIGEST_SIGNALS.get(source_platform, _PLATFORM_DIGEST_SIGNALS["default"])
        # Substitute reply/reaction thresholds into Slack signals
        platform_signals = platform_signals.format(
            reply_threshold=str(config.get("reply_threshold", 3)),
            reaction_threshold=str(config.get("reaction_threshold", 2)),
        )
        fields.update({
            "focus": config.get("focus", "key discussions and decisions"),
            "source_platform": source_platform.capitalize() if source_platform != "default" else "Various",
            "platform_signals": platform_signals,
        })

    elif prompt_role in ("prepare", "planner"):
        from datetime import datetime, timedelta
        import pytz
        # Compute today's date and date range for the prep window
        tz_name = "UTC"  # Column dropped — schedule no longer on agents table
        try:
            tz = pytz.timezone(tz_name)
        except Exception:
            tz = pytz.UTC
        now = datetime.now(tz)
        tomorrow = now + timedelta(days=1)
        today_str = now.strftime("%A, %B %-d, %Y")
        date_range = f"{now.strftime('%a %b %-d')} – {tomorrow.strftime('%a %b %-d')} morning"
        fields.update({
            "today_date": today_str,
            "date_range": date_range,
        })

    elif prompt_role in ("synthesize", "analyst"):
        fields.update({
            "subject": config.get("subject", agent.get("title", "")),
            "audience": config.get("audience", "stakeholders"),
            "detail_level": config.get("detail_level", "standard"),
            "tone": config.get("tone", "formal"),
            "length_guidance": LENGTH_GUIDANCE.get(
                config.get("detail_level", "standard"),
                "400-800 words"
            ),
        })

    elif prompt_role == "monitor":
        signals = config.get("signals", [])
        fields.update({
            "domain": config.get("domain", agent.get("title", "domain")),
            "signals": "\n".join(f"- {s}" for s in signals) if signals else "- Notable developments and emerging patterns",
        })

    elif prompt_role in ("research", "researcher", "scout"):
        from datetime import datetime
        import pytz
        tz_name = "UTC"  # Column dropped — schedule no longer on agents table
        try:
            tz = pytz.timezone(tz_name)
        except Exception:
            tz = pytz.UTC
        today_str = datetime.now(tz).strftime("%A, %B %-d, %Y")
        fields.update({
            "today_date": today_str,
        })

    elif prompt_role == "scout":
        # Scout uses today_date like research
        from datetime import datetime
        import pytz
        tz_name = "UTC"  # Column dropped — schedule no longer on agents table
        try:
            tz = pytz.timezone(tz_name)
        except Exception:
            tz = pytz.UTC
        today_str = datetime.now(tz).strftime("%A, %B %-d, %Y")
        fields.update({
            "today_date": today_str,
        })

    # drafter, writer, planner use only common fields (no special handling needed)

    else:  # custom and any unknown types
        fields.update({
            "description": config.get("description", ""),  # Column dropped — description no longer on agents table
            "structure_notes": f"STRUCTURE NOTES:\n{config.get('structure_notes', '')}" if config.get("structure_notes") else "",
        })

    # Format the template
    try:
        return template.format(**fields)
    except KeyError as e:
        logger.warning(f"Missing field in prompt template for role={role}: {e}")
        # Fall back to custom template
        return ROLE_PROMPTS["custom"].format(**{
            "title": agent.get("title", "Agent"),
            "description": config.get("description", ""),
            "structure_notes": "",
            "user_instructions": user_instructions,
            "gathered_context": gathered_context,
            "recipient_context": recipient_text,
        })


# =============================================================================
# ADR-109: Validation Functions (per role)
# =============================================================================

def _validate_minimum_content(content: str, min_words: int = 50) -> list[str]:
    """Check minimum content length."""
    word_count = len(content.split())
    if word_count < min_words:
        return [f"Content too short: {word_count} words (minimum {min_words})"]
    return []


def validate_output(role: str, content: str, config: dict) -> dict:
    """
    Validate generated content based on role (ADR-109).

    Returns:
        {
            "valid": bool,
            "issues": list[str],
            "score": float  # 0.0 to 1.0
        }
    """
    if not content:
        return {"valid": False, "issues": ["No content generated"], "score": 0.0}

    issues = _validate_minimum_content(content)

    # ADR-130 v2: map new type names to validation keys
    from services.agent_framework import LEGACY_ROLE_MAP
    v_role = LEGACY_ROLE_MAP.get(role, role)

    if v_role in ("synthesize", "analyst"):
        detail_level = config.get("detail_level", "standard")
        min_words_map = {"brief": 150, "standard": 300, "detailed": 600}
        word_count = len(content.split())
        min_w = min_words_map.get(detail_level, 300)
        if word_count < min_w * 0.7:
            issues.append(f"Too short for {detail_level}: {word_count} words (expected {min_w}+)")

    elif v_role in ("research", "researcher", "scout"):
        word_count = len(content.split())
        if word_count < 200:
            issues.append(f"Too short for research output: {word_count} words (expected 200+)")
        content_lower = content.lower()
        vague_phrases = ["it is important", "various factors", "many aspects", "in general"]
        vague_count = sum(1 for phrase in vague_phrases if phrase in content_lower)
        if vague_count > 3:
            issues.append("Content may be too generic — add more specific insights")

    elif v_role in ("digest", "briefer"):
        char_count = len(content)
        if char_count > 3000:
            issues.append(f"Briefing may be too long: {char_count} chars")
        has_bullets = "- " in content or "• " in content or "* " in content
        if not has_bullets:
            issues.append("Briefing should use bullet points for scannability")

    score = max(0, 1.0 - (len(issues) * 0.2))
    return {"valid": len(issues) == 0, "issues": issues, "score": score}



# ADR-117: get_past_versions_context() removed — feedback now distilled to
# workspace memory/style.md by feedback_distillation.py.
# All strategies load preferences via AgentWorkspace.load_context().


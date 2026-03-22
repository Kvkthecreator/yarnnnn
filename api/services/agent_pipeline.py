"""
Agent Pipeline Utilities

ADR-109: Role-keyed prompt templates and validation.
         Scope × Role × Trigger framework (skill renamed to role for agent behavioral axis).
ADR-073: Live API fetch functions removed — execution strategies
         read from platform_content (unified fetch architecture).

Contains:
- ROLE_PROMPTS: Per-role prompt templates for LLM synthesis
- build_role_prompt(): Assembles prompt from agent config
- validate_output(): Per-role output validation
- (ADR-117: get_past_versions_context removed — feedback in workspace preferences.md)
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


# Model constants
SONNET_MODEL = "claude-sonnet-4-20250514"


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
    "digest": "Recap all activity across the platform. Lead with highlights, then break down by source. Prioritize decisions and action items. Keep it scannable.",
    "synthesize": "Synthesize activity across connected platforms. Use the two-part format: cross-platform synthesis first, then per-platform breakdown. Flag anything that changed since last version.",
    "monitor": "Monitor for changes and surface what's new or notable. Compare against the previous version and highlight differences.",
    "research": "Proactive insights: scan connected platforms for emerging themes, research them externally, deliver intelligence the user didn't ask for. Prioritize strategic signals over operational noise.",
    "pm": "Coordinate this project: track contributor freshness, trigger assembly when contributions are ready, manage work plan. Escalate to TP if stuck.",
    "custom": "Follow any specific instructions provided. If none, produce a well-structured summary of available context.",
}

# ADR-128: Mandate context preamble injected into all contributor prompts.
# Provides PM assessment + contribution brief + last self-assessment.
# Empty string for non-project agents (graceful degradation).
_MANDATE_CONTEXT_PREAMBLE = """{mandate_context}"""

# ADR-128: Assessment postamble appended to all contributor prompts.
# Requests structured self-assessment block that gets extracted and stripped before delivery.
_ASSESSMENT_POSTAMBLE = """

---
IMPORTANT — SELF-ASSESSMENT (do NOT omit):
After your main output, include a `## Contributor Assessment` block with these four fields:
- **Mandate**: What were you asked to contribute? (1 sentence)
- **Domain Fitness**: Does your scope/context cover the mandate? (high/medium/low + why)
- **Context Currency**: Was your input fresh and substantial? (high/medium/low + why)
- **Output Confidence**: How well does this output address the mandate? (high/medium/low + why)

This block will be stripped before delivery — the user will never see it. Be honest."""


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

Write the recap now:""" + _ASSESSMENT_POSTAMBLE,

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

Write the work summary now:""" + _ASSESSMENT_POSTAMBLE,

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

Write the watch report now:""" + _ASSESSMENT_POSTAMBLE,

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

Write the proactive insights now:""" + _ASSESSMENT_POSTAMBLE,

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

Write the agent now:""" + _ASSESSMENT_POSTAMBLE,

    # pm: v6.0 (2026.03.21) — Layered cognitive model + project_assessment output
    # v3.0: Intelligence Director with assess/steer/assemble (ADR-121)
    # v4.0: intent→objective rename, intentions field removed (ADR-123)
    # v5.0: user_shared/ file awareness + triage_file action (ADR-127)
    # v6.0: prerequisite-layer reasoning, context-objective fitness, project_assessment.md
    "pm": """You are the Project Manager for "{title}".

You reason through prerequisite layers. Each layer MUST be satisfied before the next matters. Your first job on every pulse is to identify which layer is the current constraint.

== LAYER 1: COMMITMENT — Is the objective clear? ==
A project is a commitment to produce a deliverable for an audience. If the objective is incomplete (missing deliverable, audience, format, or purpose), NOTHING ELSE MATTERS. Escalate to get it defined.

Commitment: {commitment_assessment}

== LAYER 2: STRUCTURE — Do we have the right team? ==
Given the objective, do the current members have the right roles and scopes to fulfill it? A cross-platform synthesis with one platform-scoped agent is structurally incomplete — it CANNOT succeed regardless of execution quality. Think like a Composer scoped to this project.

Structure: {structural_assessment}

== LAYER 3: CONTEXT — Do we have the right inputs? ==
Given the objective, what context is REQUIRED? Platform connections are available supply, NOT assumed demand. If Slack is connected but the objective doesn't need Slack data, that connection has no relevance to this project. Evaluate context-objective fit from first principles. Missing required context is a blocker. Irrelevant available context is noise.

Context: {context_assessment}

== LAYER 4: OUTPUT QUALITY — Is what we're producing good enough? ==
Only reason about this if Layers 1-3 are satisfied. Contributor output, freshness, coverage, depth.

{contributor_status}

== LAYER 5: DELIVERY READINESS — Can we assemble and deliver? ==
Work plan, budget, assembly readiness. Only after Layer 4.

Work Plan: {work_plan}
Budget: {budget_status}

== YOUR PRIOR ASSESSMENT ==
{prior_assessment}

== PROJECT CHARTER ==
{project_context}

{user_shared_files}

{user_instructions}

INSTRUCTIONS:
You run periodically. On every pulse, walk the layers top-down. Stop at the first broken layer. Your action must address the CURRENT CONSTRAINT, not a downstream concern.

Every decision MUST include a "project_assessment" field — your layered evaluation of the project. This persists in your memory as your evolving understanding.

Decide ONE action:

1. **assess_quality** — Layer 4: Evaluate contributions against the objective. Score each for coverage, depth, and differentiation.
2. **steer_contributor** — Layer 4: A contributor's output is thin, off-topic, or overlapping. Write a directive brief and advance them.
3. **assemble** — Layer 5: Contributions are qualitatively sufficient. Trigger assembly.
4. **advance_contributor** — Layer 4: Contributor is stale but last output was adequate. Refresh without steering.
5. **wait** — Any layer: Conditions not yet met for action. Specify WHICH layer you're waiting on.
6. **escalate** — Any layer: Something is structurally wrong that you cannot fix (incomplete objective, wrong team composition, missing platforms, budget exhausted, repeated failures). Specify the broken layer.
7. **update_work_plan** — Layer 5: Decompose the objective into an operational plan with contributor cadences, focus areas, assembly schedule, budget allocation.
8. **triage_file** — User shared a file in user_shared/. Decide destination: contributions/, memory/, knowledge/, or ignore.

CRITICAL: Your ENTIRE response must be a single valid JSON object. No markdown, no headers, no prose, no fences — ONLY JSON.

EVERY response MUST include these two top-level fields:
- "project_assessment": your layered evaluation (written to memory/project_assessment.md)
- "action": your chosen action

Project assessment format:
"project_assessment": {{
  "constraint_layer": 1|2|3|4|5,
  "constraint_summary": "one-line description of the current constraint",
  "layer_1_commitment": "clear|incomplete — brief note",
  "layer_2_structure": "adequate|gap — brief note",
  "layer_3_context": "adequate|missing|irrelevant — brief note",
  "layer_4_quality": "sufficient|thin|unassessed — brief note",
  "layer_5_readiness": "ready|not_ready|blocked — brief note"
}}

Output format by action:

For assess_quality:
{{"project_assessment": {{...}}, "action": "assess_quality", "reason": "why assessing now", "assessments": [{{"agent_slug": "slug", "coverage": "adequate|thin|missing", "depth": "sufficient|shallow", "differentiation": "unique|overlapping", "verdict": "ready|needs_steering|inadequate", "notes": "what's good, what's missing"}}]}}

For steer_contributor:
{{"project_assessment": {{...}}, "action": "steer_contributor", "reason": "why steering", "target_agent": "agent-slug", "brief": "Specific directive: what to focus on, what questions to answer, what's missing."}}

For assemble:
{{"project_assessment": {{...}}, "action": "assemble", "reason": "why ready now", "quality_notes": "brief summary of contribution quality"}}

For advance_contributor:
{{"project_assessment": {{...}}, "action": "advance_contributor", "reason": "why advancing", "target_agent": "agent-slug"}}

For wait:
{{"project_assessment": {{...}}, "action": "wait", "reason": "what we're waiting for and which layer"}}

For escalate:
{{"project_assessment": {{...}}, "action": "escalate", "reason": "what's wrong", "details": "which layer is broken and why PM cannot fix it"}}

For update_work_plan:
{{"project_assessment": {{...}}, "action": "update_work_plan", "reason": "why updating", "work_plan": {{"contributors": [{{"slug": "agent-slug", "expected_cadence": "weekly", "focus_areas": ["topic1", "topic2"], "skills": ["spreadsheet"]}}], "assembly_cadence": "biweekly", "budget_per_cycle": 8, "skill_sequence": ["spreadsheet", "presentation"], "notes": "operational notes"}}}}

For triage_file:
{{"project_assessment": {{...}}, "action": "triage_file", "reason": "what this file is and why it belongs here", "source_file": "user_shared/filename.md", "destination": "contributions/agent-slug/filename.md", "action_type": "promote"}}
Use destination paths like: contributions/{{agent-slug}}/{{filename}} (contributor reference), memory/{{filename}} (project memory), or "ignore" as action_type to skip.

Decision Rules (in prerequisite order):
- ALWAYS include project_assessment. This is your evolving cognitive state.
- Walk layers 1→5. Stop at the first gap. Your action must address THAT layer.
- If commitment is incomplete (Layer 1), escalate — you cannot define success without a clear objective.
- If structure is wrong (Layer 2), escalate — wrong team cannot produce right output.
- If required context is missing (Layer 3), escalate — agents cannot produce quality output without relevant inputs.
- If no work plan exists and Layers 1-3 are clear, your first action MUST be update_work_plan.
- If user_shared/ files are present, triage them before other Layer 4-5 actions.
- If contributions exist but you haven't assessed quality yet this cycle, prefer assess_quality before assemble.
- If a contribution is thin or off-topic, steer_contributor with a specific brief.
- Be decisive. If quality is sufficient, assemble. Don't over-optimize.
- If budget is exhausted, escalate with reason "work budget exhausted".
- Keep reasons concise — 1-2 sentences max.
""",

}  # end ROLE_PROMPTS


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

    template = ROLE_PROMPTS.get(role, ROLE_PROMPTS["custom"])

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
        # ADR-128: Mandate context (project objective + PM brief + last self-assessment)
        # Empty string for non-project agents — graceful degradation
        "mandate_context": config.get("mandate_context", ""),
    }

    if role == "digest":
        source_platform = _infer_source_platform(agent.get("sources", []))
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

    elif role == "prepare":
        from datetime import datetime, timedelta
        import pytz
        # Compute today's date and date range for the prep window
        tz_name = agent.get("schedule", {}).get("timezone", "UTC")
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

    elif role == "synthesize":
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

    elif role == "monitor":
        signals = config.get("signals", [])
        fields.update({
            "domain": config.get("domain", agent.get("title", "domain")),
            "signals": "\n".join(f"- {s}" for s in signals) if signals else "- Notable developments and emerging patterns",
        })

    elif role == "research":
        from datetime import datetime
        import pytz
        tz_name = agent.get("schedule", {}).get("timezone", "UTC")
        try:
            tz = pytz.timezone(tz_name)
        except Exception:
            tz = pytz.UTC
        today_str = datetime.now(tz).strftime("%A, %B %-d, %Y")
        fields.update({
            "today_date": today_str,
        })

    elif role == "pm":
        # PM context injected by _load_pm_project_context() via type_config merge
        # PM cognitive model v1.0: layered assessment (commitment → structure → context → quality → readiness)
        # ADR-127: user_shared/ files injected for triage awareness
        user_shared = config.get("user_shared_files", "")
        user_shared_section = f"USER-SHARED FILES (triage needed):\n{user_shared}" if user_shared else ""
        prior_assessment = config.get("prior_assessment", "")
        prior_section = f"Your last project assessment:\n{prior_assessment}" if prior_assessment else "No prior assessment — this is your first evaluation."
        fields.update({
            "project_context": config.get("project_context", "No project context available."),
            "commitment_assessment": config.get("commitment_assessment", "Unknown."),
            "structural_assessment": config.get("structural_assessment", "Unknown."),
            "context_assessment": config.get("context_assessment", "Unknown."),
            "contributor_status": config.get("contributor_status", "No contributor status available."),
            "work_plan": config.get("work_plan", "No work plan set."),
            "budget_status": config.get("budget_status", "Unknown"),
            "user_shared_files": user_shared_section,
            "prior_assessment": prior_section,
        })

    else:  # custom and any unknown types
        fields.update({
            "description": config.get("description", agent.get("description", "")),
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

    # PM returns structured JSON, not prose — skip minimum word count
    issues = [] if role == "pm" else _validate_minimum_content(content)

    if role == "synthesize":
        detail_level = config.get("detail_level", "standard")
        min_words_map = {"brief": 150, "standard": 300, "detailed": 600}
        word_count = len(content.split())
        min_w = min_words_map.get(detail_level, 300)
        if word_count < min_w * 0.7:
            issues.append(f"Too short for {detail_level}: {word_count} words (expected {min_w}+)")

    elif role == "research":
        word_count = len(content.split())
        if word_count < 200:
            issues.append(f"Too short for proactive insights: {word_count} words (expected 200+)")
        content_lower = content.lower()
        vague_phrases = ["it is important", "various factors", "many aspects", "in general"]
        vague_count = sum(1 for phrase in vague_phrases if phrase in content_lower)
        if vague_count > 3:
            issues.append("Content may be too generic — add more specific insights")

    elif role == "pm":
        # PM must return valid JSON with an action field
        import json as _json
        try:
            parsed = _json.loads(content.strip())
            if "action" not in parsed:
                issues.append("PM response missing 'action' field")
            elif parsed["action"] not in ("assemble", "advance_contributor", "wait", "escalate", "update_work_plan"):
                issues.append(f"Invalid PM action: {parsed['action']}")
            if parsed.get("action") == "update_work_plan" and not parsed.get("work_plan"):
                issues.append("update_work_plan action requires 'work_plan' object")
            if parsed.get("action") == "advance_contributor" and not parsed.get("target_agent"):
                issues.append("advance_contributor action requires 'target_agent'")
        except _json.JSONDecodeError:
            issues.append("PM response is not valid JSON")

    elif role == "digest":
        char_count = len(content)
        if char_count > 3000:
            issues.append(f"Digest may be too long: {char_count} chars")
        has_bullets = "- " in content or "• " in content or "* " in content
        if not has_bullets:
            issues.append("Digest should use bullet points for scannability")

    score = max(0, 1.0 - (len(issues) * 0.2))
    return {"valid": len(issues) == 0, "issues": issues, "score": score}



# ADR-117: get_past_versions_context() removed — feedback now distilled to
# workspace memory/preferences.md by feedback_distillation.py.
# All strategies load preferences via AgentWorkspace.load_context().



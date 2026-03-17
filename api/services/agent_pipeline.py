"""
Agent Pipeline Utilities

ADR-109: Skill-keyed prompt templates and validation.
ADR-073: Live API fetch functions removed — execution strategies
         read from platform_content (unified fetch architecture).

Contains:
- SKILL_PROMPTS: Per-skill prompt templates for LLM synthesis
- build_skill_prompt(): Assembles prompt from agent config
- validate_output(): Per-skill output validation
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
    "gmail": (
        "- Unread emails from priority senders\n"
        "- Threads waiting for response\n"
        "- Emails with action items or deadlines mentioned\n"
        "- Thread stalls (conversations that went quiet)"
    ),
    "notion": (
        "- Recent edits and who made them\n"
        "- New content added (sections, pages, blocks)\n"
        "- Completed tasks (checkboxes, status changes)\n"
        "- Unresolved comments or questions"
    ),
    "calendar": (
        "- Upcoming meetings and their attendees\n"
        "- High-priority or large-group sessions\n"
        "- Meetings that would benefit from preparation\n"
        "- Scheduling conflicts or unusually dense periods"
    ),
    "default": (
        "- High-signal items and key decisions\n"
        "- Open questions and action items\n"
        "- Notable developments since last digest"
    ),
}


# Default instructions seeded when an agent is created without explicit instructions.
# These give the headless agent and TP a starting baseline that the user/TP can refine.
# ADR-109: Keyed by skill name
DEFAULT_INSTRUCTIONS = {
    "digest": "Recap all activity across the platform. Lead with highlights, then break down by source. Prioritize decisions and action items. Keep it scannable.",
    "prepare": "Auto meeting prep: every morning, scan today's and tomorrow morning's calendar events. Classify each meeting and generate context-appropriate prep.",
    "synthesize": "Synthesize activity across connected platforms. Use the two-part format: cross-platform synthesis first, then per-platform breakdown. Flag anything that changed since last version.",
    "monitor": "Monitor for changes and surface what's new or notable. Compare against the previous version and highlight differences.",
    "research": "Proactive insights: scan connected platforms for emerging themes, research them externally, deliver intelligence the user didn't ask for. Prioritize strategic signals over operational noise.",
    "orchestrate": "Orchestrate across multiple sources to produce a unified view. Cross-reference platform data for consistency.",
    "custom": "Follow any specific instructions provided. If none, produce a well-structured summary of available context.",
}

# ADR-109: Skill prompts. Versions tracked in api/prompts/CHANGELOG.md
# synthesize: v4 (2026.03.06) — two-part format + cross-platform connections
# digest: v2 (2026.03.06) — platform-wide recap with highlights + by-source breakdown
SKILL_PROMPTS = {

    "digest": """You are producing a platform recap titled "{title}".

This is a platform-wide recap — covering ALL activity across the user's {source_platform} workspace, not just one channel, label, or page.

FOCUS: {focus}
PLATFORM: {source_platform}

SIGNALS TO PRIORITIZE:
{platform_signals}

{user_instructions}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Write in a clear, scannable style appropriate for catching someone up
- Be specific: use names, numbers, dates, and direct references from the context
- If information is missing or a source had no activity, note it briefly

STRUCTURE:

## Highlights
3-5 bullet points of the most important things that happened across the entire platform. Lead with what matters most — decisions made, problems surfaced, progress on key work.

## By Source
Write a subsection for each source (channel, label, page, calendar) that has content in the gathered context. Use `###` headers.

For Slack: group by channel name (e.g., `### #engineering`, `### #daily-work`)
For Gmail: group by category or sender (e.g., `### Infrastructure Alerts`, `### Client Communication`)
For Notion: group by page or database (e.g., `### Architecture Docs`, `### Sprint Board`)
For Calendar: group by timeframe (e.g., `### This Week`, `### Next Week`)

Rules:
- Every source with data gets a subsection — do not combine or skip
- Low activity is still worth noting briefly (e.g., "Quiet week in #announcements")
- Keep each subsection concise — key takeaways, not exhaustive logs
- Bold action items and decisions for scannability

Write the recap now:""",

    # prepare: v3 (2026.03.06) — auto meeting prep with deep classification + tool use
    "prepare": """You are generating auto meeting prep titled "{title}".

TODAY'S DATE: {today_date}

{user_instructions}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
This runs every morning. Scan the gathered context for calendar events happening TODAY and TOMORROW MORNING (before the next delivery). For each meeting, classify it and generate the most useful prep you can.

YOUR JOB IS NOT TO REFORMAT THE CALENDAR. Your job is to prepare the user for conversations — surface what they'd otherwise have to dig for themselves. Be a diligent research assistant, not a calendar summarizer.

BEFORE WRITING: Use your tools aggressively.
- Search platform content for each attendee's name or email — find recent Slack mentions, email threads, Notion references
- For external/unfamiliar contacts: use WebSearch to look up the person and their company
- For recurring meetings: search for what was discussed in past versions or related threads
- If a search returns nothing useful, say so — "No prior interactions found" is more valuable than padding with the user's own activity

MEETING CLASSIFICATION — the classification determines WHAT you research, not just how long you write:

1. RECURRING INTERNAL (weekly sync, 1:1, standup — same attendees)
   YOUR FOCUS: What does the OTHER person need to hear, and what might THEY raise?
   - Open threads between you and this person (Slack DMs, email chains, shared Notion docs)
   - Decisions pending from last meeting (check past versions if available)
   - Blockers or updates relevant to THEIR work, not just yours
   - Frame as conversation topics, not an activity log
   BAD: "Here's what you did this week" (they already know)
   GOOD: "승진님 asked about the sync architecture last time — update: we resolved the scheduler issue. Open item: memory extraction timeline still TBD."

2. EXTERNAL / NEW CONTACT (unfamiliar attendees, intro, kickoff)
   YOUR FOCUS: Who is this person and what should the user know before walking in?
   - Use WebSearch to research the attendee and their company — role, background, what they invest in / work on
   - Search platform content for any prior mentions of this person or company
   - Surface relevant email threads (outreach, introductions)
   - Suggest 2-3 questions the user should ask based on what you find
   - If you find nothing, say explicitly: "I couldn't find background on [name]. Consider checking LinkedIn before the meeting."
   BAD: "This is a meeting about potential investment. Here's what YOU'VE been doing." (irrelevant to prep)
   GOOD: "Roger Kim, Partner at SB Partners — early-stage B2B SaaS focus, portfolio includes [X, Y]. They typically write $500K-$1M checks. No prior email threads found. Questions to ask: What's their thesis on AI infrastructure? Do they lead or follow?"

3. LARGE GROUP / ALL-HANDS (many attendees, town hall, all-hands)
   YOUR FOCUS: What should the user contribute or watch for?
   - Agenda items (from calendar description or related Slack/email)
   - Key decisions expected — what's being decided and what's the user's stake?
   - Context the user should have before speaking up
   - Recent relevant developments from Slack/email that may come up

4. LOW-STAKES / ROUTINE (casual catch-up, social, no agenda)
   YOUR FOCUS: Brief assurance with 1-2 helpful notes
   - "No specific prep needed."
   - If there IS something worth mentioning: "Quick context: [relevant note]"

OUTPUT:
Start with: "Your meetings for {date_range}"

For each meeting (chronological order by start time):

### [Meeting Title] — [Time]
**Attendees:** [who they are, not just emails — include role/context if found]
**Type:** [classification]
**Prep:**
[classification-appropriate content as described above]

---

Rules:
- Chronological order by meeting start time — no exceptions
- Use tools (Search, WebSearch) for EVERY meeting that isn't low-stakes. Try hard.
- If a tool search returns nothing, say "No results found" — don't fill the gap with generic content
- If no calendar events found at all, say so clearly and suggest checking Google Calendar connection
- Be specific: names, dates, numbers from actual context — never fabricate
- Focus on what the user DOESN'T already know, not what they DO

Write the meeting prep now:""",

    "synthesize": """You are producing a work summary titled "{title}".

SUBJECT: {subject}
AUDIENCE: {audience}
DETAIL LEVEL: {detail_level} ({length_guidance})
TONE: {tone}

{user_instructions}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

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
  - "The Render deployment issues discussed in #dev-ops (Slack) align with the billing alerts in Gmail"
  - "The architecture decisions captured in Notion were first debated in #engineering (Slack)"
  - "The meeting prep email (Gmail) relates to the project timeline in Notion"
  Look for: same topics across platforms, cause-and-effect chains (email alert → Slack discussion → Notion doc update), people mentioned in multiple places. This is the most valuable part — insights no single-platform tool can provide.

PART 2 — PLATFORM ACTIVITY (below a horizontal rule):
Write a SEPARATE "##" section for each platform. The gathered context contains headers like "## Slack: ...", "## Gmail: ...", "## Notion: ...". You MUST produce one section per platform.

Expected output structure for Part 2:
## Slack
(channel-by-channel summary of discussions, decisions, and activity)

## Gmail
(notable emails, action items, important threads)

## Notion
(document updates, new content, changes)

## Calendar
(upcoming events, conflicts, prep needs — only if calendar data present)

Rules:
- Every platform with data in the gathered context gets its own section — do not combine or skip
- No update is still news — if a platform had low activity, say so briefly (e.g., "Quiet week in #channel"). This confirms nothing was missed.
- For Slack, group by channel name
- Keep each section concise — supporting detail, not exhaustive logs

Write the work summary now:""",

    "monitor": """You are producing an intelligence watch report titled "{title}".

DOMAIN BEING WATCHED: {domain}
SIGNALS TO TRACK: {signals}

{user_instructions}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Surface what's worth the user's attention in this domain since last report
- Flag emerging patterns, notable developments, and early signals
- Distinguish signal from noise — only surface what warrants attention
- Note anything that suggests a need for action or decision
- Be concise: lead with the most significant items
- If there's nothing materially new, say so clearly rather than padding

Write the watch report now:""",

    # research: v2 (2026.03.06) — Proactive Insights: signal-driven intelligence
    "research": """You are producing Proactive Insights titled "{title}".

TODAY'S DATE: {today_date}

{user_instructions}

GATHERED CONTEXT (from your connected platforms + web research):
{gathered_context}

{recipient_context}

{past_versions}

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

Write the proactive insights now:""",

    "orchestrate": """You are producing a coordinator review titled "{title}".

DOMAIN BEING COORDINATED: {domain}
DISPATCH RULES:
{dispatch_rules}

{user_instructions}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Assess the current state of the domain against the dispatch rules
- Identify what work has been triggered, completed, or is pending
- Surface any gaps or situations that require creating or advancing agents
- Be analytical and action-oriented — this review drives downstream work

Write the coordinator review now:""",

    "custom": """You are producing a custom agent titled "{title}".

{description}

{structure_notes}

{user_instructions}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Follow the description and structure notes above precisely
- Use gathered context to ground your output in real information
- Write in the appropriate tone for the stated purpose
- If the description specifies a format (bullets, narrative, tables), use it exactly

Write the agent now:""",

}  # end SKILL_PROMPTS




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
        provider = source.get("provider", "")
        if provider in _PLATFORM_DIGEST_SIGNALS:
            return provider
    return "default"


def build_skill_prompt(
    skill: str,
    config: dict,
    agent: dict,
    gathered_context: str,
    recipient_text: str,
    past_versions: str,
) -> str:
    """Build the skill-specific synthesis prompt (ADR-109)."""

    template = SKILL_PROMPTS.get(skill, SKILL_PROMPTS["custom"])

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
        "past_versions": past_versions,
        "title": agent.get("title", "Agent"),
        "user_instructions": user_instructions,
    }

    if skill == "digest":
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

    elif skill == "prepare":
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

    elif skill == "synthesize":
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

    elif skill == "monitor":
        signals = config.get("signals", [])
        fields.update({
            "domain": config.get("domain", agent.get("title", "domain")),
            "signals": "\n".join(f"- {s}" for s in signals) if signals else "- Notable developments and emerging patterns",
        })

    elif skill == "research":
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

    elif skill == "orchestrate":
        dispatch_rules = config.get("dispatch_rules", [])
        fields.update({
            "domain": config.get("domain", agent.get("title", "domain")),
            "dispatch_rules": "\n".join(f"- {r}" for r in dispatch_rules) if dispatch_rules else "- No explicit rules — use judgment",
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
        logger.warning(f"Missing field in prompt template for skill={skill}: {e}")
        # Fall back to custom template
        return SKILL_PROMPTS["custom"].format(**{
            "title": agent.get("title", "Agent"),
            "description": config.get("description", ""),
            "structure_notes": "",
            "user_instructions": user_instructions,
            "gathered_context": gathered_context,
            "recipient_context": recipient_text,
            "past_versions": past_versions,
        })


# =============================================================================
# ADR-109: Validation Functions (per skill)
# =============================================================================

def _validate_minimum_content(content: str, min_words: int = 50) -> list[str]:
    """Check minimum content length."""
    word_count = len(content.split())
    if word_count < min_words:
        return [f"Content too short: {word_count} words (minimum {min_words})"]
    return []


def validate_output(skill: str, content: str, config: dict) -> dict:
    """
    Validate generated content based on skill (ADR-109).

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

    if skill == "synthesize":
        detail_level = config.get("detail_level", "standard")
        min_words_map = {"brief": 150, "standard": 300, "detailed": 600}
        word_count = len(content.split())
        min_w = min_words_map.get(detail_level, 300)
        if word_count < min_w * 0.7:
            issues.append(f"Too short for {detail_level}: {word_count} words (expected {min_w}+)")

    elif skill == "research":
        word_count = len(content.split())
        if word_count < 200:
            issues.append(f"Too short for proactive insights: {word_count} words (expected 200+)")
        content_lower = content.lower()
        vague_phrases = ["it is important", "various factors", "many aspects", "in general"]
        vague_count = sum(1 for phrase in vague_phrases if phrase in content_lower)
        if vague_count > 3:
            issues.append("Content may be too generic — add more specific insights")

    elif skill == "digest":
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



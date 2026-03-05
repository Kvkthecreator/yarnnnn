"""
Deliverable Pipeline Utilities

ADR-093: 7 purpose-first type prompt templates and validation.
ADR-073: Live API fetch functions removed — execution strategies
         read from platform_content (unified fetch architecture).

Contains:
- TYPE_PROMPTS: Per-type prompt templates for LLM synthesis
- build_type_prompt(): Assembles prompt from deliverable config
- validate_output(): Per-type output validation
- get_past_versions_context(): Past version feedback for learning
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


# Default instructions seeded when a deliverable is created without explicit instructions.
# These give the headless agent and TP a starting baseline that the user/TP can refine.
DEFAULT_INSTRUCTIONS = {
    "digest": "Summarize key activity and highlights. Prioritize actionable items and decisions. Keep it scannable with bullet points.",
    "brief": "Provide a concise executive-level summary. Lead with the most important finding. Include 2-3 supporting details max.",
    "status": "Report on progress, blockers, and next steps. Use a consistent structure each run. Flag anything that changed since last version.",
    "watch": "Monitor for changes and surface what's new or notable. Compare against the previous version and highlight differences.",
    "deep_research": "Conduct thorough research using web search and available sources. Synthesize findings into a structured analysis with citations.",
    "coordinator": "Orchestrate across multiple sources to produce a unified view. Cross-reference platform data for consistency.",
    "custom": "Follow any specific instructions provided. If none, produce a well-structured summary of available context.",
}

TYPE_PROMPTS = {

    "digest": """You are producing a digest titled "{title}".

FOCUS: {focus}
SOURCE PLATFORM: {source_platform}

PLATFORM SIGNALS TO PRIORITIZE:
{platform_signals}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Synthesize what's happening in this specific place — signal over noise
- Lead with the most important discussions, decisions, and open questions
- Be specific: use names, thread starters, and key takeaways from context
- Bold key decisions and action items; use bullet points for scannability
- Skip casual/low-signal content
- Keep total length appropriate for the platform (under 2000 chars for Slack)

Write the digest now:""",

    "brief": """You are producing a situation brief titled "{title}".

EVENT/CONTEXT: {event_context}
ATTENDEES/STAKEHOLDERS: {attendees}
FOCUS AREAS: {focus_areas}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Focus on what the user needs to know BEFORE this event or situation
- Summarize relevant recent activity and open items from the context
- Highlight pending decisions or unresolved discussions
- Suggest 2-3 key talking points or questions to raise
- Keep it scannable — bullet points and clear headers
- If this is a recurring event, note what was discussed previously if available

Write the brief now:""",

    "status": """You are producing a status update titled "{title}".

SUBJECT: {subject}
AUDIENCE: {audience}
DETAIL LEVEL: {detail_level} ({length_guidance})
TONE: {tone}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Write in {tone} tone appropriate for {audience}
- Lead with a brief executive summary/TL;DR
- Cover what was accomplished, what's in progress, and what's blocked
- Be specific: use names, numbers, and dates from the context
- Highlight blockers and risks clearly — don't bury them
- Make next steps actionable with owners where known
- If information is missing, note the gap rather than fabricating

Write the status update now:""",

    "watch": """You are producing an intelligence watch report titled "{title}".

DOMAIN BEING WATCHED: {domain}
SIGNALS TO TRACK: {signals}

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

    "deep_research": """You are producing a deep research report titled "{title}".

FOCUS AREA: {focus_area}
RESEARCH SUBJECTS:
{subjects_list}
PURPOSE: {purpose}

GATHERED CONTEXT (from web research and platform data):
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Write as an expert analyst synthesizing research findings
- Lead with the most important actionable insights
- Be specific: cite sources, companies, people, and data from context
- Distinguish what is known from what is inferred
- If researching competitors: note their positioning, moves, and gaps
- Avoid vague generalities — every claim should be grounded in gathered context
- Depth target: {depth}

Write the research report now:""",

    "coordinator": """You are producing a coordinator review titled "{title}".

DOMAIN BEING COORDINATED: {domain}
DISPATCH RULES:
{dispatch_rules}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Assess the current state of the domain against the dispatch rules
- Identify what work has been triggered, completed, or is pending
- Surface any gaps or situations that require creating or advancing deliverables
- Be analytical and action-oriented — this review drives downstream work

Write the coordinator review now:""",

    "custom": """You are producing a custom deliverable titled "{title}".

{description}

{structure_notes}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Follow the description and structure notes above precisely
- Use gathered context to ground your output in real information
- Write in the appropriate tone for the stated purpose
- If the description specifies a format (bullets, narrative, tables), use it exactly

Write the deliverable now:""",

}  # end TYPE_PROMPTS


# Legacy prompts removed (ADR-093): status_report, research_brief, slack_channel_digest,
# gmail_inbox_brief, notion_page_summary, meeting_prep, weekly_calendar_preview
# All replaced by 7 purpose-first types above.




# Section templates for each type (ADR-093: 7 purpose-first types)
SECTION_TEMPLATES = {
    "digest": {
        "highlights": "Highlights - Key discussions and notable content",
        "decisions": "Decisions - What was decided or agreed",
        "open_questions": "Open Questions - Unanswered items needing attention",
        "action_items": "Action Items - Tasks and follow-ups mentioned",
    },
    "brief": {
        "context": "Context - What's happened leading up to this event",
        "attendee_background": "Attendee Background - Recent interactions and relevant history",
        "open_items": "Open Items - Unresolved discussions or decisions",
        "talking_points": "Talking Points - Suggested topics and questions to raise",
    },
    "status": {
        "summary": "Summary/TL;DR - Brief overview of the current state",
        "accomplishments": "Accomplishments - What was completed this period",
        "blockers": "Blockers/Challenges - Issues impeding progress",
        "next_steps": "Next Steps - Planned work for the upcoming period",
        "metrics": "Key Metrics - Relevant numbers and measurements",
    },
    "watch": {
        "signals": "Signals - Notable developments worth attention",
        "patterns": "Patterns - Emerging trends or recurring themes",
        "action_needed": "Action Needed - Items that warrant a response or decision",
        "quiet_front": "Quiet Front - Areas with no material developments",
    },
    "deep_research": {
        "key_takeaways": "Key Takeaways - The most important actionable insights",
        "findings": "Findings - Detailed research results by topic/subject",
        "implications": "Implications - What these findings mean",
        "recommendations": "Recommendations - Suggested actions based on the research",
    },
    "coordinator": {
        "domain_status": "Domain Status - Current state of the watched domain",
        "dispatched": "Dispatched - Work triggered or advanced in this cycle",
        "pending": "Pending - Work waiting on conditions or schedule",
        "gaps": "Gaps - Situations requiring new deliverables or escalation",
    },
    "custom": {},  # No predefined sections — fully user-defined
}


# Length guidance by detail level
LENGTH_GUIDANCE = {
    "brief": "200-400 words - concise and to the point",
    "standard": "400-800 words - balanced detail",
    "detailed": "800-1500 words - comprehensive coverage",
    "scan": "300-500 words - quick overview",
    "analysis": "500-1000 words - moderate depth",
    "deep_dive": "1000+ words - thorough exploration",
}


def normalize_sections(sections) -> dict:
    """Normalize sections to dict format.

    Handles both:
    - List format: ['summary', 'accomplishments'] -> {'summary': True, 'accomplishments': True}
    - Dict format: {'summary': True, 'accomplishments': False} -> unchanged
    """
    if sections is None:
        return {}
    if isinstance(sections, list):
        return {s: True for s in sections}
    return sections


def build_sections_list(deliverable_type: str, config: dict) -> str:
    """Build formatted sections list based on enabled sections in config."""
    sections = normalize_sections(config.get("sections", {}))
    templates = SECTION_TEMPLATES.get(deliverable_type, {})

    enabled = []
    for section_key, is_enabled in sections.items():
        if is_enabled and section_key in templates:
            enabled.append(f"- {templates[section_key]}")

    if not enabled:
        # Default to all sections if none specified
        enabled = [f"- {desc}" for desc in templates.values()]

    return "\n".join(enabled)




def _infer_source_platform(sources: list) -> str:
    """Infer primary platform from sources[] for digest type."""
    if not sources:
        return "default"
    for source in sources:
        provider = source.get("provider", "")
        if provider in _PLATFORM_DIGEST_SIGNALS:
            return provider
    return "default"


def build_type_prompt(
    deliverable_type: str,
    config: dict,
    deliverable: dict,
    gathered_context: str,
    recipient_text: str,
    past_versions: str,
) -> str:
    """Build the type-specific synthesis prompt (ADR-093: 7 purpose-first types)."""

    template = TYPE_PROMPTS.get(deliverable_type, TYPE_PROMPTS["custom"])

    # Common fields present in all templates
    fields = {
        "gathered_context": gathered_context,
        "recipient_context": recipient_text,
        "past_versions": past_versions,
        "title": deliverable.get("title", "Deliverable"),
    }

    if deliverable_type == "digest":
        source_platform = _infer_source_platform(deliverable.get("sources", []))
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

    elif deliverable_type == "brief":
        attendees = config.get("attendees", [])
        focus_areas = config.get("focus_areas", [])
        fields.update({
            "event_context": config.get("event_title", deliverable.get("title", "Upcoming Event")),
            "attendees": ", ".join(attendees) if attendees else "Not specified",
            "focus_areas": ", ".join(focus_areas) if focus_areas else "General context",
        })

    elif deliverable_type == "status":
        fields.update({
            "subject": config.get("subject", deliverable.get("title", "")),
            "audience": config.get("audience", "stakeholders"),
            "detail_level": config.get("detail_level", "standard"),
            "tone": config.get("tone", "formal"),
            "length_guidance": LENGTH_GUIDANCE.get(
                config.get("detail_level", "standard"),
                "400-800 words"
            ),
        })

    elif deliverable_type == "watch":
        signals = config.get("signals", [])
        fields.update({
            "domain": config.get("domain", deliverable.get("title", "domain")),
            "signals": "\n".join(f"- {s}" for s in signals) if signals else "- Notable developments and emerging patterns",
        })

    elif deliverable_type == "deep_research":
        subjects = config.get("subjects", [])
        fields.update({
            "focus_area": config.get("focus_area", "general"),
            "subjects_list": "\n".join(f"- {s}" for s in subjects) if subjects else "- General research",
            "purpose": config.get("purpose", "Inform decision-making"),
            "depth": config.get("depth", "analysis"),
        })

    elif deliverable_type == "coordinator":
        dispatch_rules = config.get("dispatch_rules", [])
        fields.update({
            "domain": config.get("domain", deliverable.get("title", "domain")),
            "dispatch_rules": "\n".join(f"- {r}" for r in dispatch_rules) if dispatch_rules else "- No explicit rules — use judgment",
        })

    else:  # custom and any unknown types
        fields.update({
            "description": config.get("description", deliverable.get("description", "")),
            "structure_notes": f"STRUCTURE NOTES:\n{config.get('structure_notes', '')}" if config.get("structure_notes") else "",
        })

    # Format the template
    try:
        return template.format(**fields)
    except KeyError as e:
        logger.warning(f"Missing field in prompt template for {deliverable_type}: {e}")
        # Fall back to custom template
        return TYPE_PROMPTS["custom"].format(**{
            "title": deliverable.get("title", "Deliverable"),
            "description": config.get("description", ""),
            "structure_notes": "",
            "gathered_context": gathered_context,
            "recipient_context": recipient_text,
            "past_versions": past_versions,
        })


# =============================================================================
# ADR-093: Validation Functions (7 purpose-first types)
# =============================================================================

def _validate_minimum_content(content: str, min_words: int = 50) -> list[str]:
    """Check minimum content length."""
    word_count = len(content.split())
    if word_count < min_words:
        return [f"Content too short: {word_count} words (minimum {min_words})"]
    return []


def validate_output(deliverable_type: str, content: str, config: dict) -> dict:
    """
    Validate generated content based on deliverable type (ADR-093: 7 types).

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

    if deliverable_type == "status":
        detail_level = config.get("detail_level", "standard")
        min_words_map = {"brief": 150, "standard": 300, "detailed": 600}
        word_count = len(content.split())
        min_w = min_words_map.get(detail_level, 300)
        if word_count < min_w * 0.7:
            issues.append(f"Too short for {detail_level}: {word_count} words (expected {min_w}+)")

    elif deliverable_type == "deep_research":
        depth = config.get("depth", "analysis")
        min_words_map = {"scan": 200, "analysis": 400, "deep_dive": 800}
        word_count = len(content.split())
        min_w = min_words_map.get(depth, 400)
        if word_count < min_w * 0.7:
            issues.append(f"Too shallow for {depth}: {word_count} words (expected {min_w}+)")
        content_lower = content.lower()
        vague_phrases = ["it is important", "various factors", "many aspects", "in general"]
        vague_count = sum(1 for phrase in vague_phrases if phrase in content_lower)
        if vague_count > 3:
            issues.append("Content may be too generic — add more specific insights")

    elif deliverable_type == "digest":
        char_count = len(content)
        if char_count > 3000:
            issues.append(f"Digest may be too long: {char_count} chars")
        has_bullets = "- " in content or "• " in content or "* " in content
        if not has_bullets:
            issues.append("Digest should use bullet points for scannability")

    score = max(0, 1.0 - (len(issues) * 0.2))
    return {"valid": len(issues) == 0, "issues": issues, "score": score}



async def get_past_versions_context(client, deliverable_id: str) -> str:
    """
    Get context from past versions including feedback patterns.

    Returns a formatted string with learned preferences from edit history.
    """
    # Get recent approved versions with edits
    versions_result = (
        client.table("deliverable_versions")
        .select("version_number, edit_categories, edit_distance_score, feedback_notes")
        .eq("deliverable_id", deliverable_id)
        .eq("status", "approved")
        .order("version_number", desc=True)
        .limit(5)
        .execute()
    )

    versions = versions_result.data or []

    if not versions:
        return ""

    # Aggregate feedback patterns
    patterns = []
    for v in versions:
        categories = v.get("edit_categories", {})
        if categories:
            if categories.get("additions"):
                patterns.append(f"User added: {', '.join(categories['additions'][:3])}")
            if categories.get("deletions"):
                patterns.append(f"User removed: {', '.join(categories['deletions'][:3])}")

        if v.get("feedback_notes"):
            patterns.append(f"Feedback: {v['feedback_notes']}")

    if not patterns:
        return ""

    return f"""
LEARNED PREFERENCES (from past versions):
{chr(10).join(f'- {p}' for p in patterns[:10])}

Apply these preferences when producing this version."""



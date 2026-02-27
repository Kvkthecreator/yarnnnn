"""
Deliverable Pipeline Utilities

ADR-019: Type-specific prompt templates and validation.
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
# ADR-019: Type-Specific Prompt Templates
# =============================================================================

TYPE_PROMPTS = {
    "status_report": """You are writing a {detail_level} status report for {audience}.

Subject: {subject}

SECTIONS TO INCLUDE:
{sections_list}

TONE: {tone}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Write in {tone} tone appropriate for {audience}
- Be specific with accomplishments - use concrete examples
- Keep blockers actionable - suggest next steps when possible
- Length target: {length_guidance}
- Do NOT invent specific dates, numbers, or metrics not in the context

Write the status report now:""",

    "research_brief": """You are writing a {depth} research brief on {focus_area} intelligence.

SUBJECTS TO COVER:
{subjects_list}

PURPOSE: {purpose}

SECTIONS TO INCLUDE:
{sections_list}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Key takeaways should be actionable, not just summaries
- Findings must be specific and tied to sources when possible
- Connect implications to the user's context and purpose
- Recommendations should be concrete and prioritized
- Depth level: {depth} (scan: 300-500 words, analysis: 500-1000, deep_dive: 1000+)

Write the research brief now:""",

    "custom": """Produce the following deliverable: {title}

DESCRIPTION:
{description}

{structure_notes}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Follow any structure guidelines provided above
- Maintain appropriate professional tone
- Be thorough but concise

Write the deliverable now:""",

    # ==========================================================================
    # ADR-035/ADR-082: Platform-Bound Prompts
    # ==========================================================================

    "slack_channel_digest": """You are creating a Slack channel digest.

FOCUS: {focus}
SECTIONS TO INCLUDE:
{sections_list}

PLATFORM SIGNALS TO PRIORITIZE:
- Threads with {reply_threshold}+ replies (hot discussions)
- Messages with {reaction_threshold}+ reactions (notable content)
- Questions that went unanswered (gaps worth surfacing)
- Decision language ("we decided", "agreed", "let's go with")

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Format as Slack-native content using bullet points and clear headers
- Bold key decisions and action items
- Keep it scannable - no long paragraphs
- For hot threads, include the thread starter + key takeaway
- Link to original messages where relevant
- Keep total length under 2000 characters for Slack readability
- Prioritize signal over noise - skip casual chat

Write the channel digest now:""",

    "gmail_inbox_brief": """You are creating a daily inbox brief to help triage email.

FOCUS: {focus}
SECTIONS TO INCLUDE:
{sections_list}

PRIORITIZE:
- Unread emails from priority senders
- Threads waiting for user response
- Emails with action items or deadlines mentioned
- Thread stalls (conversations that went quiet)

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Start with urgent/time-sensitive items
- Group by category: Urgent, Action Required, FYI, Can Archive
- For each email, include: sender, subject, and one-line summary
- Highlight any mentioned deadlines or dates
- Suggest which emails can be batch-responded
- Keep the brief scannable — use bullet points, no emojis
- Use plain markdown headers (## Urgent, ## Action Required, etc.)
- Total length: 300-500 words

Write the inbox brief now:""",

    "notion_page_summary": """You are summarizing recent activity on a Notion page/database.

SUMMARY TYPE: {summary_type}
MAX DEPTH: {max_depth} subpage levels

SECTIONS TO INCLUDE:
{sections_list}

LOOK FOR:
- Recent edits and who made them
- New content added (sections, pages, blocks)
- Completed tasks (checkboxes, status changes)
- Unresolved comments or questions
- Structural changes (new subpages, reorganization)

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Lead with the most significant changes
- Note who made key changes when attribution available
- For changelog type: be specific about what changed
- For overview type: summarize current state
- For activity type: focus on recent human activity
- Mention unresolved comments that need attention
- Keep it concise - 200-400 words

Write the page summary now:""",

    # ADR-046: Calendar Types
    "meeting_prep": """You are preparing a brief for an upcoming meeting.

MEETING: {meeting_title}
WHEN: {meeting_time}
ATTENDEES: {attendees_list}
{meeting_description}

CONTEXT SOURCES:
{gathered_context}

{recipient_context}

{past_versions}

SECTIONS TO INCLUDE:
{sections_list}

INSTRUCTIONS:
- Focus on what the user needs to know BEFORE this meeting
- Summarize recent interactions with each attendee from the context
- Highlight any open items, pending decisions, or unresolved discussions
- Include relevant project updates or blockers
- Suggest 2-3 talking points or questions to raise
- Keep it scannable - use bullet points and clear headers
- If recurring meeting, note what was discussed in previous occurrence if available

Write the meeting prep brief now:""",

    "weekly_calendar_preview": """You are creating a weekly calendar preview from raw calendar event data.

CALENDAR EVENTS:
{gathered_context}

{recipient_context}

{past_versions}

STRUCTURE (use these exact section headers, no emojis):

## Week Overview
Count the actual events from the data above. State: total meetings, total hours, busiest day, and available free blocks. Be specific with numbers.

## Key People This Week
Who the user is meeting with — list names and meeting context. Note any external attendees.

## Recurring Meetings
Identify recurring patterns (weekly standups, 1:1s, team syncs) from the event titles.

## High-Priority
Flag meetings that are longer than usual, have many attendees, or appear strategic (e.g., strategy sessions, external meetings, reviews).

## Suggested Prep
List 2-3 meetings that would benefit from advance preparation, and briefly explain why.

INSTRUCTIONS:
- Analyze the raw event data to compute meeting counts, durations, and patterns
- Include specific dates and times for each event
- Be definitive — do not hedge or say "N/A" if data is present
- Keep it brief and scannable — bullet points preferred
- Do not use emojis

Generate the weekly calendar preview now:""",

}


# Section templates for each type
SECTION_TEMPLATES = {
    # Tier 1 - Stable
    "status_report": {
        "summary": "Summary/TL;DR - Brief overview of the current state",
        "accomplishments": "Accomplishments - What was completed this period",
        "blockers": "Blockers/Challenges - Issues impeding progress",
        "next_steps": "Next Steps - Planned work for the upcoming period",
        "metrics": "Key Metrics - Relevant numbers and measurements",
    },
    "research_brief": {
        "key_takeaways": "Key Takeaways - The most important actionable insights",
        "findings": "Findings - Detailed research results by topic/subject",
        "implications": "Implications - What these findings mean for the business",
        "recommendations": "Recommendations - Suggested actions based on the research",
    },
    # ADR-035/ADR-082: Platform-Bound Section Templates
    "slack_channel_digest": {
        "hot_threads": "Hot Threads - Discussions with high engagement",
        "key_decisions": "Key Decisions - What was decided or agreed",
        "unanswered_questions": "Unanswered Questions - Open items needing response",
        "mentions": "Notable Mentions - Important callouts or highlights",
    },
    "gmail_inbox_brief": {
        "urgent": "Urgent - Time-sensitive items",
        "action_required": "Action Required - Emails needing your response",
        "fyi": "FYI - Informational items, no action needed",
        "follow_ups": "Follow-ups - Threads to revisit",
    },
    "notion_page_summary": {
        "changes": "Recent Changes - What was modified",
        "new_content": "New Content - What was added",
        "completed_tasks": "Completed Tasks - Items marked done",
        "open_comments": "Open Comments - Unresolved discussions",
    },
    # ADR-046: Calendar-Triggered Section Templates
    "meeting_prep": {
        "attendee_context": "Attendee Context - Recent interactions with meeting participants",
        "open_items": "Open Items - Unresolved discussions or decisions",
        "recent_updates": "Recent Updates - Relevant project or topic updates",
        "suggested_topics": "Suggested Topics - Discussion points to raise",
        "previous_meeting": "Previous Meeting - Notes from last occurrence (if recurring)",
    },
    "weekly_calendar_preview": {
        "overview": "Week Overview - Meeting count, hours, busy/free patterns",
        "key_people": "Key People - Who you're meeting with most",
        "recurring": "Recurring Meetings - Regular syncs and 1:1s",
        "high_priority": "High Priority - Meetings needing extra attention",
        "prep_suggestions": "Prep Suggestions - Meetings worth preparing for",
    },
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


# =============================================================================
# ADR-031: Platform Variant Prompts
# =============================================================================

VARIANT_PROMPTS = {
    "slack_digest": """You are creating a Slack channel digest.

CHANNEL: {channel_name}
TIME PERIOD: {time_period}

The digest should highlight what's important, not just summarize everything.
Focus on platform-semantic signals in the context.

SECTIONS TO GENERATE:

## 🔥 Hot Threads
Threads with high engagement (many replies, reactions). What were people talking about?

## ❓ Unanswered Questions
Questions that haven't been answered yet. Flag these for attention.

## ⏳ Stalled Discussions
Threads that started but went quiet - may need follow-up.

## ✅ Action Items
Concrete tasks or follow-ups mentioned in conversations.

## 📋 Decisions Made
Decisions that were reached in discussions.

## 💬 Key Discussions
Other notable conversations worth knowing about.

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Be concise but specific - use names and details from context
- If a section has nothing notable, skip it entirely
- Format for Slack: use *bold* for emphasis, bullet points for lists
- Include message timestamps or rough times when referencing discussions
- Prioritize actionable information over general chatter
- If you detect urgency markers or blockers, highlight them prominently

Generate the digest now:""",

}





def _build_variant_prompt(
    platform_variant: str,
    deliverable: dict,
    gathered_context: str,
    recipient_text: str,
    past_versions: str,
) -> Optional[str]:
    """
    Build a platform-variant-specific prompt.

    Returns None if variant not supported (falls back to base type).
    """
    template = VARIANT_PROMPTS.get(platform_variant)
    if not template:
        return None

    # Extract metadata for template
    title = deliverable.get("title", "Deliverable")
    sources = deliverable.get("sources", [])
    destination = deliverable.get("destination", {})

    # Common fields
    fields = {
        "gathered_context": gathered_context,
        "recipient_context": recipient_text,
        "past_versions": past_versions,
        "time_period": "Last 7 days",  # Could make this configurable
    }

    if platform_variant == "slack_digest":
        # Extract channel name from sources or destination
        channel_name = "Channel"
        for source in sources:
            if source.get("provider") == "slack":
                channel_name = source.get("resource_name") or source.get("source", "Channel")
                break
        if not channel_name or channel_name == "Channel":
            channel_name = destination.get("target", title)

        fields["channel_name"] = channel_name

    try:
        return template.format(**fields)
    except KeyError as e:
        logger.warning(f"[VARIANT] Missing field in template: {e}")
        return None


def build_type_prompt(
    deliverable_type: str,
    config: dict,
    deliverable: dict,
    gathered_context: str,
    recipient_text: str,
    past_versions: str,
) -> str:
    """Build the type-specific synthesis prompt."""

    # ADR-031: Check for platform_variant first
    platform_variant = deliverable.get("platform_variant")
    if platform_variant:
        variant_prompt = _build_variant_prompt(
            platform_variant=platform_variant,
            deliverable=deliverable,
            gathered_context=gathered_context,
            recipient_text=recipient_text,
            past_versions=past_versions,
        )
        if variant_prompt:
            return variant_prompt

    # ADR-082: Resolve deprecated types to parent type's prompt
    _TYPE_PROMPT_ALIASES = {
        "slack_standup": "slack_channel_digest",
        "inbox_summary": "gmail_inbox_brief",
        "reply_draft": "gmail_inbox_brief",
        "follow_up_tracker": "gmail_inbox_brief",
        "thread_summary": "gmail_inbox_brief",
        "meeting_summary": "meeting_prep",
        "one_on_one_prep": "meeting_prep",
        "stakeholder_update": "status_report",
        "board_update": "status_report",
        "weekly_status": "status_report",
        "project_brief": "status_report",
        "cross_platform_digest": "status_report",
        "activity_summary": "status_report",
        "daily_strategy_reflection": "status_report",
        "deep_research": "research_brief",
        "intelligence_brief": "research_brief",
        "client_proposal": "custom",
        "performance_self_assessment": "custom",
        "newsletter_section": "custom",
        "changelog": "custom",
    }
    resolved_type = _TYPE_PROMPT_ALIASES.get(deliverable_type, deliverable_type)

    template = TYPE_PROMPTS.get(resolved_type, TYPE_PROMPTS["custom"])

    # Common fields
    fields = {
        "gathered_context": gathered_context,
        "recipient_context": recipient_text,
        "past_versions": past_versions,
        "title": deliverable.get("title", "Deliverable"),
    }

    if resolved_type == "status_report":
        fields.update({
            "subject": config.get("subject", deliverable.get("title", "")),
            "audience": config.get("audience", "stakeholders"),
            "sections_list": build_sections_list(resolved_type, config),
            "detail_level": config.get("detail_level", "standard"),
            "tone": config.get("tone", "formal"),
            "length_guidance": LENGTH_GUIDANCE.get(
                config.get("detail_level", "standard"),
                "400-800 words"
            ),
        })

    elif resolved_type == "research_brief":
        subjects = config.get("subjects", [])
        fields.update({
            "focus_area": config.get("focus_area", "market"),
            "subjects_list": "\n".join(f"- {s}" for s in subjects) if subjects else "- General research",
            "purpose": config.get("purpose", "Inform decision-making"),
            "sections_list": build_sections_list(resolved_type, config),
            "depth": config.get("depth", "analysis"),
        })

    elif resolved_type == "meeting_prep":
        # Extract meeting info from config
        meeting_info = config.get("meeting", {})
        attendees = meeting_info.get("attendees", [])
        attendee_names = [a.get("display_name") or a.get("email", "Unknown") for a in attendees[:10]]
        fields.update({
            "meeting_title": meeting_info.get("title", config.get("meeting_title", "Upcoming Meeting")),
            "meeting_time": meeting_info.get("start", config.get("meeting_time", "")),
            "attendees_list": ", ".join(attendee_names) if attendee_names else "Not specified",
            "meeting_description": f"MEETING DESCRIPTION:\n{meeting_info.get('description', '')}" if meeting_info.get("description") else "",
            "sections_list": build_sections_list(resolved_type, config),
        })

    elif resolved_type == "weekly_calendar_preview":
        # Extract calendar summary info
        calendar_summary = config.get("calendar_summary", {})
        fields.update({
            "week_start": config.get("week_start", "this week"),
            "calendar_summary": calendar_summary.get("raw", "See events in context"),
            "meeting_count": str(calendar_summary.get("meeting_count", "multiple")),
            "total_hours": str(calendar_summary.get("total_hours", "N/A")),
            "busiest_day": calendar_summary.get("busiest_day", "N/A"),
            "free_blocks": calendar_summary.get("free_blocks", "See calendar for details"),
            "sections_list": build_sections_list(resolved_type, config),
        })

    elif resolved_type == "slack_channel_digest":
        fields.update({
            "focus": config.get("focus", "key discussions and decisions"),
            "reply_threshold": str(config.get("reply_threshold", 3)),
            "reaction_threshold": str(config.get("reaction_threshold", 3)),
            "sections_list": build_sections_list(resolved_type, config),
        })

    elif resolved_type == "gmail_inbox_brief":
        fields.update({
            "focus": config.get("focus", "unread and action-required emails"),
            "sections_list": build_sections_list(resolved_type, config),
        })

    elif resolved_type == "notion_page_summary":
        fields.update({
            "summary_type": config.get("summary_type", "activity"),
            "max_depth": str(config.get("max_depth", 2)),
            "sections_list": build_sections_list(resolved_type, config),
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
        logger.warning(f"Missing field in prompt template: {e}")
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
# ADR-019: Validation Functions
# =============================================================================

def validate_status_report(content: str, config: dict) -> dict:
    """Validate a status report output."""
    issues = []

    sections = normalize_sections(config.get("sections", {}))
    required_sections = [k for k, v in sections.items() if v]

    content_lower = content.lower()

    # Check required sections are present
    section_keywords = {
        "summary": ["summary", "tl;dr", "overview", "at a glance"],
        "accomplishments": ["accomplishments", "completed", "achieved", "done", "wins"],
        "blockers": ["blockers", "challenges", "issues", "obstacles", "risks"],
        "next_steps": ["next steps", "upcoming", "planned", "looking ahead", "next week"],
        "metrics": ["metrics", "numbers", "kpis", "data", "performance"],
    }

    for section in required_sections:
        keywords = section_keywords.get(section, [section])
        if not any(kw in content_lower for kw in keywords):
            issues.append(f"Missing section: {section}")

    # Check length
    word_count = len(content.split())
    detail_level = config.get("detail_level", "standard")
    expected = {
        "brief": (200, 500),
        "standard": (400, 1000),
        "detailed": (800, 2000),
    }
    min_words, max_words = expected.get(detail_level, (400, 1000))

    if word_count < min_words * 0.7:  # 30% tolerance
        issues.append(f"Too short: {word_count} words (expected {min_words}+)")
    if word_count > max_words * 1.5:
        issues.append(f"Too long: {word_count} words (expected ~{max_words})")

    score = max(0, 1.0 - (len(issues) * 0.2))
    return {"valid": len(issues) == 0, "issues": issues, "score": score}


def validate_research_brief(content: str, config: dict) -> dict:
    """Validate a research brief output."""
    issues = []

    sections = normalize_sections(config.get("sections", {}))
    required_sections = [k for k, v in sections.items() if v]

    content_lower = content.lower()

    section_keywords = {
        "key_takeaways": ["key takeaways", "takeaways", "key findings", "main points"],
        "findings": ["findings", "research shows", "analysis reveals", "discovered"],
        "implications": ["implications", "means for", "impact", "consequences"],
        "recommendations": ["recommendations", "suggest", "recommend", "action items"],
    }

    for section in required_sections:
        keywords = section_keywords.get(section, [section])
        if not any(kw in content_lower for kw in keywords):
            issues.append(f"Missing section: {section}")

    # Check depth/length
    word_count = len(content.split())
    depth = config.get("depth", "analysis")
    expected = {
        "scan": (250, 600),
        "analysis": (400, 1200),
        "deep_dive": (800, 2500),
    }
    min_words, max_words = expected.get(depth, (400, 1200))

    if word_count < min_words * 0.7:
        issues.append(f"Too shallow for {depth}: {word_count} words (expected {min_words}+)")

    # Check for generic/vague content
    vague_phrases = ["it is important", "various factors", "many aspects", "in general"]
    vague_count = sum(1 for phrase in vague_phrases if phrase in content_lower)
    if vague_count > 3:
        issues.append("Content may be too generic - add more specific insights")

    score = max(0, 1.0 - (len(issues) * 0.2))
    return {"valid": len(issues) == 0, "issues": issues, "score": score}


def validate_custom(content: str, config: dict) -> dict:
    """Validate a custom deliverable - minimal validation."""
    issues = []

    word_count = len(content.split())
    if word_count < 50:
        issues.append(f"Content too short: {word_count} words")

    # Custom deliverables get a neutral score
    score = 0.6 if len(issues) == 0 else 0.4
    return {"valid": len(issues) == 0, "issues": issues, "score": score}


# =============================================================================
# ADR-035/ADR-082: Active Type Validators
# =============================================================================

def validate_slack_channel_digest(content: str, config: dict) -> dict:
    """Validate a Slack channel digest output."""
    issues = []
    content_lower = content.lower()

    sections = normalize_sections(config.get("sections", {}))
    required_sections = [k for k, v in sections.items() if v]

    section_keywords = {
        "hot_threads": ["thread", "discussion", "conversation", "talked about", "replies"],
        "key_decisions": ["decided", "decision", "agreed", "concluded", "going with"],
        "unanswered_questions": ["question", "unanswered", "?", "unclear", "need to know"],
        "mentions": ["mention", "highlight", "notable", "important", "attention"],
    }

    for section in required_sections:
        keywords = section_keywords.get(section, [section])
        if not any(kw in content_lower for kw in keywords):
            issues.append(f"Missing section: {section}")

    # Slack digests should be concise
    char_count = len(content)
    if char_count > 2500:
        issues.append(f"Too long for Slack: {char_count} chars (max ~2000)")

    # Should have bullet points for scannability
    has_bullets = "- " in content or "• " in content or "* " in content
    if not has_bullets:
        issues.append("Digest should use bullet points for scannability")

    score = max(0, 1.0 - (len(issues) * 0.2))
    return {"valid": len(issues) == 0, "issues": issues, "score": score}


def validate_gmail_inbox_brief(content: str, config: dict) -> dict:
    """Validate a Gmail inbox brief output."""
    issues = []
    content_lower = content.lower()

    sections = normalize_sections(config.get("sections", {}))
    required_sections = [k for k, v in sections.items() if v]

    section_keywords = {
        "urgent": ["urgent", "immediate", "asap", "time-sensitive", "deadline"],
        "action_required": ["action", "respond", "reply", "need to", "follow up"],
        "fyi": ["fyi", "informational", "no action", "reference", "note"],
        "follow_ups": ["follow up", "revisit", "check back", "pending"],
    }

    for section in required_sections:
        keywords = section_keywords.get(section, [section])
        if not any(kw in content_lower for kw in keywords):
            issues.append(f"Missing section: {section}")

    # Should have structure
    has_bullets = "- " in content or "• " in content
    if not has_bullets:
        issues.append("Brief should use bullet points for scannability")

    # Inbox briefs should be concise
    word_count = len(content.split())
    if word_count < 50:
        issues.append(f"Brief too short: {word_count} words")
    if word_count > 600:
        issues.append(f"Brief too long: {word_count} words (aim for 300-500)")

    score = max(0, 1.0 - (len(issues) * 0.2))
    return {"valid": len(issues) == 0, "issues": issues, "score": score}


def validate_notion_page_summary(content: str, config: dict) -> dict:
    """Validate a Notion page summary output."""
    issues = []
    content_lower = content.lower()

    sections = normalize_sections(config.get("sections", {}))
    required_sections = [k for k, v in sections.items() if v]

    section_keywords = {
        "changes": ["change", "modified", "updated", "edited", "revised"],
        "new_content": ["new", "added", "created", "inserted"],
        "completed_tasks": ["completed", "done", "finished", "checked", "resolved"],
        "open_comments": ["comment", "open", "unresolved", "discussion", "thread"],
    }

    for section in required_sections:
        keywords = section_keywords.get(section, [section])
        if not any(kw in content_lower for kw in keywords):
            issues.append(f"Missing section: {section}")

    # Check word count
    word_count = len(content.split())
    if word_count < 50:
        issues.append(f"Summary too brief: {word_count} words")
    if word_count > 500:
        issues.append(f"Summary too long: {word_count} words (aim for 200-400)")

    score = max(0, 1.0 - (len(issues) * 0.2))
    return {"valid": len(issues) == 0, "issues": issues, "score": score}


def validate_output(deliverable_type: str, content: str, config: dict) -> dict:
    """
    Validate generated content based on deliverable type.

    Returns:
        {
            "valid": bool,
            "issues": list[str],
            "score": float  # 0.0 to 1.0
        }
    """
    # ADR-082: 8 active type validators (deprecated types fall through to custom)
    validators = {
        "status_report": validate_status_report,
        "research_brief": validate_research_brief,
        "custom": validate_custom,
        "slack_channel_digest": validate_slack_channel_digest,
        "gmail_inbox_brief": validate_gmail_inbox_brief,
        "notion_page_summary": validate_notion_page_summary,
    }

    if not content:
        return {"valid": False, "issues": ["No content generated"], "score": 0.0}

    validator = validators.get(deliverable_type, validate_custom)
    return validator(content, config)



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



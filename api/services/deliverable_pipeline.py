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

    "stakeholder_update": """You are writing a {formality} stakeholder update for {audience_type}.

Company/Project: {company_or_project}
Relationship Context: {relationship_context}

SECTIONS TO INCLUDE:
{sections_list}

SENSITIVITY: {sensitivity} information

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Maintain a {formality} tone throughout
- Lead with the executive summary - 2-3 sentences capturing the essence
- Balance highlights with challenges - avoid pure positive spin
- Make the outlook section actionable with clear next steps
- Do NOT include specific financials unless explicitly provided in context

Write the stakeholder update now:""",

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

    "meeting_summary": """You are writing a {format} summary for: {meeting_name}

Meeting Type: {meeting_type}
Participants: {participants}

SECTIONS TO INCLUDE:
{sections_list}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Action items MUST have clear owners when possible
- Decisions should be explicitly stated, not implied
- Discussion points should be substantive, not filler
- Format: {format} (narrative, bullet_points, or structured)
- Keep it concise but complete

Write the meeting summary now:""",

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
    # Beta Tier Prompts
    # ==========================================================================

    "client_proposal": """You are writing a {tone} client proposal for {client_name}.

PROJECT TYPE: {project_type}
SERVICE CATEGORY: {service_category}

SECTIONS TO INCLUDE:
{sections_list}

{pricing_instruction}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Personalize to the client's specific context and needs
- Be clear about the value proposition and outcomes
- Deliverables should be specific, not vague
- {tone} tone throughout
- Make it persuasive but honest

Write the proposal now:""",

    "performance_self_assessment": """You are writing a {review_period} performance self-assessment for a {role_level} level employee.

SECTIONS TO INCLUDE:
{sections_list}

TONE: {tone}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Accomplishments should include measurable impact when possible
- Be {tone} - {tone_guidance}
- Acknowledge both strengths and growth areas
- Be forward-looking with goals for the next period
{quantify_instruction}

Write the self-assessment now:""",

    "newsletter_section": """You are writing a {section_type} section for the newsletter: {newsletter_name}

AUDIENCE: {audience}
VOICE: {voice}
LENGTH: {length}

SECTIONS TO INCLUDE:
{sections_list}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Start with an engaging hook, not a boring opener
- Maintain consistent {voice} voice throughout
- Keep to {length} length target
- Include clear CTA if applicable
- Don't sound generic or AI-written

Write the newsletter section now:""",

    "changelog": """You are writing {release_type} release notes for {product_name}.

AUDIENCE: {audience}
FORMAT: {format}

SECTIONS TO INCLUDE:
{sections_list}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Categorize changes clearly (new, improved, fixed)
- Use {format} language appropriate for {audience}
- Highlight user benefits, not just technical changes
- Flag any breaking changes prominently
{links_instruction}

Write the release notes now:""",

    "one_on_one_prep": """You are preparing a manager's prep doc for a {meeting_cadence} 1:1 with {report_name}.

RELATIONSHIP: {relationship}
FOCUS AREAS: {focus_areas}

SECTIONS TO INCLUDE:
{sections_list}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Make it personalized to this specific individual
- Balance recognition with areas to discuss
- Include actionable discussion topics, not just observations
- Build on previous conversations when context available
- Keep it focused on the selected focus areas

Write the 1:1 prep doc now:""",

    "board_update": """You are writing a {update_type} board update for {company_name}.

COMPANY STAGE: {stage}
TONE: {tone}

SECTIONS TO INCLUDE:
{sections_list}

{comparisons_instruction}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Lead with the executive summary (2-3 sentences)
- Be metrics-forward with context on what they mean
- {tone} tone - {tone_guidance}
- Clear asks section - don't bury requests
- Keep it concise - board members are busy
- 500-1000 words total

Write the board update now:""",

    # ==========================================================================
    # ADR-029 Phase 3: Email-Specific Deliverable Prompts
    # ==========================================================================

    "inbox_summary": """You are writing a {summary_period} inbox summary for the user.

INBOX SCOPE: {inbox_scope}
PRIORITIZATION: {prioritization}

SECTIONS TO INCLUDE:
{sections_list}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Start with a quick overview of inbox activity (message count, key senders)
- Highlight urgent items that need immediate attention
- Clearly separate action-required emails from FYI items
- For threads to close, suggest which can be archived or responded to quickly
- Keep summaries scannable - use bullet points, not long paragraphs
- If thread context is included, summarize key decision points

Write the inbox summary now:""",

    "reply_draft": """You are drafting a reply to an email thread.

TONE: {tone}
THREAD ID: {thread_id}

SECTIONS TO INCLUDE:
{sections_list}

{quote_instruction}

{suggested_actions}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Match the tone of the original sender where appropriate
- Be {tone} but genuine - don't sound robotic
- Acknowledge their points before responding
- If suggesting next steps, be specific about actions/dates
- Keep the reply focused - don't introduce unrelated topics
- If quoting, only quote the most relevant parts

Write the reply draft now:""",

    "follow_up_tracker": """You are creating a follow-up tracker for the user's email.

TRACKING PERIOD: {tracking_period}
PRIORITIZATION: {prioritize_by}

SECTIONS TO INCLUDE:
{sections_list}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Identify threads that need a response from the user
- Highlight overdue items prominently at the top
- For "waiting on others" - note who we're waiting on and since when
- List commitments the user made that may need follow-through
- Include thread links if available for quick access
- Suggest priority order for tackling the backlog

Write the follow-up tracker now:""",

    "thread_summary": """You are summarizing an email thread.

THREAD ID: {thread_id}
DETAIL LEVEL: {detail_level}

SECTIONS TO INCLUDE:
{sections_list}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- List all participants and their roles in the conversation
- Create a timeline of key exchanges
- Clearly state any decisions that were made
- Highlight unresolved questions or open items
- If action items exist, list them with owners if mentioned
- Keep summary {detail_level} - {detail_guidance}

Write the thread summary now:""",

    # ==========================================================================
    # ADR-035: Platform-First Wave 1 Prompts
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

    "slack_standup": """You are drafting a standup from Slack activity.

SOURCE MODE: {source_mode}
FORMAT: {format}

SECTIONS TO INCLUDE:
{sections_list}

LOOK FOR THESE SIGNALS:
- Completion language: "done", "shipped", "merged", "finished", "completed"
- Progress language: "working on", "in progress", "reviewing", "starting"
- Blocker language: "stuck on", "waiting for", "blocked by", "need help"

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Extract accomplishments from messages showing completion
- Identify in-progress work from activity mentions
- Surface blockers explicitly mentioned
- Format: {format} (bullet points or short narrative)
- Be concise - standups should be quick to read
- Don't fabricate items - only use what's in the context
- If {source_mode} is "team", group by person

Write the standup now:""",

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

    # Phase 2: Strategic Intelligence Types
    "deep_research": """You are conducting {depth} research on the following topic:

TOPIC: {topic}

RESEARCH TYPE: {research_type}
TIME HORIZON: {time_horizon_text}

SECTIONS TO INCLUDE:
{sections_list}

SOURCES REQUIRED: Minimum {sources_required} credible sources
CITATIONS: Include inline citations when required

GATHERED CONTEXT (Research materials, documents, web sources):
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Executive summary: 3-5 key findings that directly answer the research question
- Background: Provide sufficient context for non-experts to understand the domain
- Key findings: Organize by theme, not by source. Each finding should be substantive and evidenced
- Analysis: Go beyond description - identify patterns, tensions, implications
- Recommendations: Specific, prioritized actions based on the research
- Sources: List all sources consulted with brief relevance notes
- Depth level: {depth} (comprehensive: 1500-2500 words, exhaustive: 2500+ words)
- Time horizon: Frame findings and recommendations for {time_horizon_text} perspective
- Research type: Ensure {research_type} angle is central to analysis

This is deep research - be thorough, analytical, and evidence-based.

Write the deep research deliverable now:""",

    "daily_strategy_reflection": """You are writing a strategic reflection for end of day.

FOCUS AREA: {focus_area_text}
LOOKBACK PERIOD: Past {lookback_days} day(s)
REFLECTION TIME: {reflection_time}
TONE: {tone}

SECTIONS TO INCLUDE:
{sections_list}

GATHERED CONTEXT (Activity log, completed work, conversations, deliverables):
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Strategic movements: What significant developments occurred that affect strategy? Not task completion, but shifts in landscape
- Decision points: What decisions (made or pending) have strategic weight? Focus on implications, not mechanics
- Pattern recognition: What patterns emerge from the day's activity? Connect micro-actions to macro-trends
- Action prioritization: Based on today's insights, what are the top 2-3 strategic priorities for tomorrow/this week?
- Learning insights: What did you learn about your own strategic process or blind spots today?
- Tone: {tone} (analytical = data-driven, reflective = introspective, directive = action-oriented)
- Length: 400-800 words - concise but substantive
- Focus area: {focus_area_text} - use this as the lens for all analysis

This is strategic reflection, not task tracking. Elevate the discussion.

Write the daily strategy reflection now:""",

    "intelligence_brief": """You are writing an intelligence brief for {audience}.

BRIEF TYPE: {brief_type}
TIME SENSITIVITY: {time_sensitivity}

SECTIONS TO INCLUDE:
{sections_list}

GATHERED CONTEXT (Current intelligence, platform data, research sources):
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Situation summary: Current state in 2-3 sentences. What's the headline?
- Key developments: What changed since last brief? Focus on signal, not noise
- Threat/opportunities: What risks or openings emerged? Be specific about impact
- Recommended actions: Immediate next steps (24-48 hours). Prioritized list
- Monitoring indicators: What metrics/events should we watch to track this?
- Brief type: {brief_type} angle should be primary lens
- Audience: {audience} - adjust detail level and framing accordingly
- Time sensitivity: {time_sensitivity} - this determines currency requirements
- Maximum length: {max_length_words} words - brevity is critical for intelligence

Intelligence briefs are factual, current, and action-oriented. No speculation without flagging it.

Write the intelligence brief now:""",
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
    "stakeholder_update": {
        "executive_summary": "Executive Summary - The key message in 2-3 sentences",
        "highlights": "Key Highlights - Major wins and positive developments",
        "challenges": "Challenges & Mitigations - Issues and how they're being addressed",
        "metrics": "Metrics Snapshot - Key performance indicators",
        "outlook": "Outlook - Focus areas for the next period",
    },
    "research_brief": {
        "key_takeaways": "Key Takeaways - The most important actionable insights",
        "findings": "Findings - Detailed research results by topic/subject",
        "implications": "Implications - What these findings mean for the business",
        "recommendations": "Recommendations - Suggested actions based on the research",
    },
    "meeting_summary": {
        "context": "Meeting Context - Purpose and attendees",
        "discussion": "Key Discussion Points - Main topics covered",
        "decisions": "Decisions Made - Explicit agreements reached",
        "action_items": "Action Items - Tasks with owners and deadlines",
        "followups": "Follow-ups - Topics for the next meeting",
    },
    # Beta Tier
    "client_proposal": {
        "executive_summary": "Executive Summary - Hook and value proposition",
        "needs_understanding": "Understanding of Needs - What the client wants to achieve",
        "approach": "Our Approach - How we'll solve the problem",
        "deliverables": "Deliverables - What the client will receive",
        "timeline": "Timeline - Key milestones and dates",
        "investment": "Investment - Pricing and payment terms",
        "social_proof": "Why Us - Relevant experience and testimonials",
    },
    "performance_self_assessment": {
        "summary": "Summary - Overview of the review period",
        "accomplishments": "Key Accomplishments - Major wins with impact",
        "goals_progress": "Goals Progress - Status on previously set goals",
        "challenges": "Challenges & Learnings - Obstacles faced and lessons learned",
        "development": "Development Areas - Skills and areas for growth",
        "next_period_goals": "Goals for Next Period - Focus areas ahead",
    },
    "newsletter_section": {
        "hook": "Hook/Intro - Attention-grabbing opener",
        "main_content": "Main Content - The core message or story",
        "highlights": "Highlights - Key callouts or quotes",
        "cta": "Call to Action - What readers should do next",
    },
    "changelog": {
        "highlights": "Highlights - Most important changes",
        "new_features": "New Features - Newly added functionality",
        "improvements": "Improvements - Enhanced existing features",
        "bug_fixes": "Bug Fixes - Issues resolved",
        "breaking_changes": "Breaking Changes - Changes requiring action",
        "whats_next": "What's Next - Preview of upcoming work",
    },
    "one_on_one_prep": {
        "context": "Context Since Last 1:1 - What's happened",
        "topics": "Topics to Discuss - Agenda items",
        "recognition": "Recognition - Wins to call out",
        "concerns": "Concerns - Issues to address",
        "career": "Career & Development - Growth discussion",
        "previous_actions": "Previous Action Items - Follow-up on past commitments",
    },
    "board_update": {
        "executive_summary": "Executive Summary - The key message in 2-3 sentences",
        "metrics": "Key Metrics - Performance indicators with context",
        "strategic_progress": "Strategic Progress - Movement on key initiatives",
        "challenges": "Challenges - Issues and mitigations",
        "financials": "Financials - Cash, runway, burn",
        "asks": "Asks - What you need from the board",
        "outlook": "Outlook - Focus for next period",
    },
    # ADR-029 Phase 3: Email-Specific Section Templates
    "inbox_summary": {
        "overview": "Overview - Quick stats on inbox activity",
        "urgent": "Urgent - Items requiring immediate attention",
        "action_required": "Action Required - Emails needing your response",
        "fyi_items": "FYI - Informational items, no action needed",
        "threads_to_close": "Threads to Close - Conversations ready to wrap up",
    },
    "reply_draft": {
        "acknowledgment": "Acknowledgment - Brief response to their points",
        "response_body": "Response - Main content of your reply",
        "next_steps": "Next Steps - Proposed actions or timeline",
        "closing": "Closing - Sign-off appropriate to relationship",
    },
    "follow_up_tracker": {
        "overdue": "Overdue - Threads past expected response time",
        "due_soon": "Due Soon - Items to address this week",
        "waiting_on_others": "Waiting On - Pending responses from others",
        "commitments_made": "Commitments - Things you said you'd do",
    },
    "thread_summary": {
        "participants": "Participants - Who's in this conversation",
        "timeline": "Timeline - Key exchanges in chronological order",
        "key_points": "Key Points - Main topics and positions",
        "decisions": "Decisions - What was agreed or decided",
        "open_questions": "Open Questions - Unresolved items",
    },
    # ADR-035: Platform-First Wave 1 Section Templates
    "slack_channel_digest": {
        "hot_threads": "Hot Threads - Discussions with high engagement",
        "key_decisions": "Key Decisions - What was decided or agreed",
        "unanswered_questions": "Unanswered Questions - Open items needing response",
        "mentions": "Notable Mentions - Important callouts or highlights",
    },
    "slack_standup": {
        "done": "Done - What was completed",
        "doing": "In Progress - What's currently being worked on",
        "blockers": "Blockers - What's blocking progress",
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
    # Phase 2: Strategic Intelligence Types
    "deep_research": {
        "executive_summary": "Executive Summary - 3-5 key findings that answer the research question",
        "background": "Background - Context needed to understand the domain",
        "key_findings": "Key Findings - Substantive discoveries organized by theme",
        "analysis": "Analysis - Patterns, tensions, and implications beyond description",
        "recommendations": "Recommendations - Specific, prioritized actions based on research",
        "sources": "Sources - All sources consulted with relevance notes",
        "appendix": "Appendix - Supporting data, detailed charts, extended analysis",
    },
    "daily_strategy_reflection": {
        "strategic_movements": "Strategic Movements - Developments affecting strategic landscape",
        "decision_points": "Decision Points - Decisions with strategic weight and implications",
        "pattern_recognition": "Pattern Recognition - Emerging patterns from activity and signals",
        "action_prioritization": "Action Prioritization - Top 2-3 strategic priorities for next period",
        "learning_insights": "Learning Insights - Meta-learnings about strategic process",
    },
    "intelligence_brief": {
        "situation_summary": "Situation Summary - Current state in 2-3 sentences",
        "key_developments": "Key Developments - What changed since last brief (signal, not noise)",
        "threat_opportunities": "Threats & Opportunities - Risks and openings with specific impact",
        "recommended_actions": "Recommended Actions - Immediate next steps (24-48 hours), prioritized",
        "monitoring_indicators": "Monitoring Indicators - Metrics/events to track going forward",
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

    "email_summary": """You are creating an email inbox summary.

INBOX: {inbox_name}
TIME PERIOD: {time_period}

Summarize the key emails and threads that need attention.

SECTIONS TO GENERATE:

## 🚨 Urgent / Needs Response
Emails requiring immediate attention or response.

## 📥 Action Required
Emails with action items or requests for you.

## 📧 FYI / Updates
Informational emails that are good to know about.

## 🔄 Threads to Follow Up
Email threads that may need your follow-up.

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Prioritize by urgency and importance
- Include sender names and subjects
- Summarize the core request or information
- Skip purely administrative or automated emails
- Note deadlines if mentioned

Generate the summary now:""",

    # ADR-031 Phase 5: Gmail Archetypes
    "email_draft_reply": """You are drafting a reply to an email thread.

ORIGINAL EMAIL CONTEXT:
{email_context}

SENDER: {sender_name}
SUBJECT: {subject}

GATHERED CONTEXT (user's notes, related info):
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Write a professional, clear response
- Address all points raised in the original email
- Be concise but thorough
- Match the formality level of the original sender
- Include a clear action or next step if appropriate
- Use appropriate greeting and sign-off

Draft the reply now (start with greeting, end with sign-off):""",

    "email_follow_up": """You are drafting a follow-up email.

CONTEXT FOR FOLLOW-UP:
{follow_up_context}

RECIPIENT: {recipient_name}
ORIGINAL SUBJECT: {subject}
DAYS SINCE LAST CONTACT: {days_since}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Write a polite, professional follow-up
- Reference the previous communication briefly
- Restate the key ask or topic clearly
- Provide any new information if relevant
- End with a specific call to action
- Keep it concise - respect their time

Draft the follow-up email now:""",

    "email_weekly_digest": """You are creating a weekly email digest for the user.

ACCOUNT: {account_email}
TIME PERIOD: {time_period}

Create a summary of the user's email activity and outstanding items.

SECTIONS TO GENERATE:

## 📊 This Week's Overview
Quick stats: emails received, sent, threads active.

## 🔴 Overdue Responses
Emails that have been waiting for your response for too long.

## ⏰ Time-Sensitive
Emails with upcoming deadlines or meetings.

## 💬 Active Threads
Important ongoing conversations.

## 📌 Flagged for Review
Emails the user starred or flagged but hasn't addressed.

## ✅ Completed This Week
Threads that were resolved or closed this week.

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Be specific about senders, subjects, and dates
- Highlight anything overdue prominently
- Note patterns (e.g., "3 emails from Sarah unread")
- Provide actionable suggestions
- Keep the tone helpful, not overwhelming

Generate the digest now:""",

    "email_triage": """You are helping triage incoming emails.

INBOX: {inbox_name}
NEW EMAILS COUNT: {email_count}

Categorize and prioritize these emails to help the user manage their inbox efficiently.

CATEGORIES TO ASSIGN:

### 🔴 Respond Today
Must respond within 24 hours.

### 🟡 Respond This Week
Should respond but not urgent.

### 🟢 FYI Only
No response needed, just awareness.

### 📁 Archive
Can be archived without action.

### 🗑️ Skip/Delete
Newsletters, promotions, or irrelevant.

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

INSTRUCTIONS:
- For each email, state: [CATEGORY] From: Subject - Brief reason
- Consider sender importance (boss vs newsletter)
- Look for deadlines, questions, or requests
- Group similar emails (e.g., "5 newsletter emails → Archive")
- Be decisive - avoid "maybe" categories

Triage the emails now:""",

    "notion_page": """You are creating content for a Notion page.

PAGE TITLE: {page_title}
PURPOSE: {purpose}

GATHERED CONTEXT:
{gathered_context}

{recipient_context}

{past_versions}

INSTRUCTIONS:
- Use clear headers (##) to structure content
- Include callout blocks for important notes (> **Note:** ...)
- Use checkboxes for action items (- [ ] Task here)
- Tables where appropriate for comparisons or data
- Keep formatting clean and scannable

Generate the page content now:""",

    # ==========================================================================
    # ADR-031 Phase 6: Cross-Platform Synthesizer Prompts
    # ==========================================================================

    "weekly_status": """You are creating a weekly status report synthesized from multiple platforms.

PROJECT: {project_name}
TIME PERIOD: {time_period}
PLATFORMS INCLUDED: {platforms_used}

This is a CROSS-PLATFORM synthesis - you have context from multiple sources that need to be unified into a cohesive status update.

{cross_platform_context}

{recipient_context}

{past_versions}

SECTIONS TO GENERATE:

## 📊 Executive Summary
2-3 sentences capturing the week's overall status and key takeaways.

## ✅ Accomplishments
What was completed this week? Pull from all platforms - Slack discussions, email threads, Notion updates.

## 🚧 In Progress
What's actively being worked on? Note any blockers or dependencies.

## 📋 Action Items
Concrete next steps. Include owners if mentioned in context.

## 🔮 Looking Ahead
What's coming next week? Upcoming deadlines, milestones, or decisions.

## 💬 Key Discussions
Notable conversations or decisions from across platforms that stakeholders should know about.

INSTRUCTIONS:
- Synthesize information across platforms - don't just list by source
- Identify connections between discussions on different platforms
- Prioritize by importance, not by platform
- Be concise but specific - use names, dates, and details from context
- If the same topic appears on multiple platforms, consolidate into one mention
- Highlight any cross-platform coordination or alignment issues

Generate the weekly status now:""",

    "project_brief": """You are creating a project brief synthesized from multiple platforms.

PROJECT: {project_name}
PLATFORMS INCLUDED: {platforms_used}

This brief consolidates all available context about this project from connected platforms into a comprehensive overview.

{cross_platform_context}

{recipient_context}

{past_versions}

SECTIONS TO GENERATE:

## 🎯 Project Overview
What is this project? What are the goals?

## 👥 Key People
Who's involved? Pull names from Slack conversations, email threads, Notion pages.

## 📅 Timeline & Milestones
Key dates, deadlines, and milestones mentioned across platforms.

## 📊 Current Status
Where does the project stand right now? What phase/stage?

## 🔑 Key Decisions Made
Important decisions captured in any platform.

## ❓ Open Questions
Unresolved questions or pending decisions from discussions.

## 📎 Resources & Links
Any documents, pages, or resources referenced in context.

INSTRUCTIONS:
- This is a living brief - synthesize the current state, not a historical record
- Connect dots between platforms (e.g., email decision that led to Slack discussion)
- Highlight any conflicts or inconsistencies found across sources
- Be comprehensive but organized - this is a reference document
- Include specific details: names, dates, numbers from the context

Generate the project brief now:""",

    "cross_platform_digest": """You are creating a digest synthesizing activity across multiple platforms.

USER: {user_name}
TIME PERIOD: {time_period}
PLATFORMS: {platforms_used}

This digest gives the user a unified view of what's happening across all their connected platforms.

{cross_platform_context}

{recipient_context}

{past_versions}

SECTIONS TO GENERATE:

## 🔥 Needs Attention
Items requiring action from any platform - urgent emails, unanswered Slack mentions, stale Notion tasks.

## 📧 Email Highlights
Key emails from the period - summarize, don't list everything.

## 💬 Slack Highlights
Important Slack conversations, decisions, or requests.

## 📝 Notion Updates
Significant changes to Notion pages or databases.

## 🔄 Cross-Platform Connections
Where the same topic or thread spans multiple platforms.

## ✅ Completed This Period
What got resolved or closed across platforms.

INSTRUCTIONS:
- Prioritize by urgency and importance, not by platform
- If something appears on multiple platforms, mention the connection
- Be selective - highlight what matters, not everything
- Use the user's name when something is directed at them
- Include enough context to act on each item

Generate the cross-platform digest now:""",

    "activity_summary": """You are creating an activity summary across multiple platforms.

TIME PERIOD: {time_period}
PLATFORMS: {platforms_used}

Create a high-level summary of activity for quick consumption.

{cross_platform_context}

{recipient_context}

{past_versions}

STRUCTURE:

## 📈 At a Glance
Quick stats: messages, emails, updates across platforms.

## 🎯 Top Priorities
The 3-5 most important items across all platforms.

## 💡 Key Takeaways
What the user most needs to know from this period.

## 👀 Watch List
Items to keep an eye on in the coming days.

INSTRUCTIONS:
- Be extremely concise - this is a quick summary
- Prioritize ruthlessly - only the most important items
- Cross-reference between platforms where relevant
- Make it actionable - what should the user do next?

Generate the activity summary now:""",
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

    elif platform_variant == "email_summary":
        inbox_name = "Inbox"
        for source in sources:
            if source.get("provider") == "gmail":
                inbox_name = source.get("resource_name") or source.get("source", "Inbox")
                break
        fields["inbox_name"] = inbox_name

    elif platform_variant == "email_draft_reply":
        # Extract email context from type_config or sources
        type_config = deliverable.get("type_config", {})
        fields["email_context"] = type_config.get("email_context", gathered_context[:2000])
        fields["sender_name"] = type_config.get("sender_name", "Sender")
        fields["subject"] = type_config.get("subject", title)

    elif platform_variant == "email_follow_up":
        type_config = deliverable.get("type_config", {})
        fields["follow_up_context"] = type_config.get("follow_up_context", gathered_context[:1000])
        fields["recipient_name"] = type_config.get("recipient_name", destination.get("target", "Recipient"))
        fields["subject"] = type_config.get("subject", title)
        fields["days_since"] = type_config.get("days_since", "7")

    elif platform_variant == "email_weekly_digest":
        # Extract account email from sources
        account_email = "your inbox"
        for source in sources:
            if source.get("provider") == "gmail":
                account_email = source.get("resource_name") or source.get("source", "your inbox")
                break
        fields["account_email"] = account_email

    elif platform_variant == "email_triage":
        inbox_name = "Inbox"
        email_count = 0
        for source in sources:
            if source.get("provider") == "gmail":
                inbox_name = source.get("resource_name") or source.get("source", "Inbox")
                break
        # Count emails from context (rough estimate)
        email_count = gathered_context.count("Subject:") or gathered_context.count("From:")
        fields["inbox_name"] = inbox_name
        fields["email_count"] = str(email_count) if email_count > 0 else "multiple"

    elif platform_variant == "notion_page":
        fields["page_title"] = title
        fields["purpose"] = deliverable.get("description", "Documentation")

    # ADR-031 Phase 6: Cross-platform synthesizer variants
    elif platform_variant in ("weekly_status", "project_brief", "cross_platform_digest", "activity_summary"):
        # These variants use cross-platform context from the synthesizer service
        type_config = deliverable.get("type_config", {})

        # Project name from config or title
        fields["project_name"] = type_config.get("project_name", title)
        fields["user_name"] = type_config.get("user_name", "User")

        # Platforms used - extracted from synthesizer context or sources
        platforms = set()
        for source in sources:
            if provider := source.get("provider"):
                platforms.add(provider)
        fields["platforms_used"] = ", ".join(sorted(platforms)) if platforms else "Multiple platforms"

        # For synthesizers, the gathered_context is already formatted with cross-platform structure
        # Use a separate field name for clarity in the template
        fields["cross_platform_context"] = gathered_context

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

    template = TYPE_PROMPTS.get(deliverable_type, TYPE_PROMPTS["custom"])

    # Common fields
    fields = {
        "gathered_context": gathered_context,
        "recipient_context": recipient_text,
        "past_versions": past_versions,
        "title": deliverable.get("title", "Deliverable"),
    }

    if deliverable_type == "status_report":
        fields.update({
            "subject": config.get("subject", deliverable.get("title", "")),
            "audience": config.get("audience", "stakeholders"),
            "sections_list": build_sections_list(deliverable_type, config),
            "detail_level": config.get("detail_level", "standard"),
            "tone": config.get("tone", "formal"),
            "length_guidance": LENGTH_GUIDANCE.get(
                config.get("detail_level", "standard"),
                "400-800 words"
            ),
        })

    elif deliverable_type == "stakeholder_update":
        fields.update({
            "audience_type": config.get("audience_type", "stakeholders"),
            "company_or_project": config.get("company_or_project", deliverable.get("title", "")),
            "relationship_context": config.get("relationship_context", "N/A"),
            "sections_list": build_sections_list(deliverable_type, config),
            "formality": config.get("formality", "professional"),
            "sensitivity": config.get("sensitivity", "confidential"),
        })

    elif deliverable_type == "research_brief":
        subjects = config.get("subjects", [])
        fields.update({
            "focus_area": config.get("focus_area", "market"),
            "subjects_list": "\n".join(f"- {s}" for s in subjects) if subjects else "- General research",
            "purpose": config.get("purpose", "Inform decision-making"),
            "sections_list": build_sections_list(deliverable_type, config),
            "depth": config.get("depth", "analysis"),
        })

    elif deliverable_type == "meeting_summary":
        participants = config.get("participants", [])
        fields.update({
            "meeting_name": config.get("meeting_name", deliverable.get("title", "")),
            "meeting_type": config.get("meeting_type", "team_sync"),
            "participants": ", ".join(participants) if participants else "Team members",
            "sections_list": build_sections_list(deliverable_type, config),
            "format": config.get("format", "structured"),
        })

    # Beta Tier
    elif deliverable_type == "client_proposal":
        fields.update({
            "client_name": config.get("client_name", "the client"),
            "project_type": config.get("project_type", "new_engagement").replace("_", " "),
            "service_category": config.get("service_category", "consulting"),
            "sections_list": build_sections_list(deliverable_type, config),
            "tone": config.get("tone", "consultative"),
            "pricing_instruction": "Include pricing/investment section" if config.get("include_pricing", True) else "Do NOT include specific pricing",
        })

    elif deliverable_type == "performance_self_assessment":
        review_period = config.get("review_period", "quarterly")
        role_level = config.get("role_level", "ic")
        tone = config.get("tone", "balanced")
        tone_guidance = {
            "humble": "acknowledge contributions without overselling",
            "balanced": "confidently state accomplishments while acknowledging growth areas",
            "confident": "clearly articulate value and impact",
        }
        fields.update({
            "review_period": review_period,
            "role_level": role_level.replace("_", " "),
            "sections_list": build_sections_list(deliverable_type, config),
            "tone": tone,
            "tone_guidance": tone_guidance.get(tone, "balanced perspective"),
            "quantify_instruction": "- Quantify impact with specific numbers, percentages, and metrics wherever possible" if config.get("quantify_impact", True) else "",
        })

    elif deliverable_type == "newsletter_section":
        length = config.get("length", "medium")
        length_words = {"short": "100-200 words", "medium": "200-400 words", "long": "400-800 words"}
        fields.update({
            "newsletter_name": config.get("newsletter_name", "Newsletter"),
            "section_type": config.get("section_type", "main_story").replace("_", " "),
            "audience": config.get("audience", "customers"),
            "sections_list": build_sections_list(deliverable_type, config),
            "voice": config.get("voice", "brand"),
            "length": length_words.get(length, "200-400 words"),
        })

    elif deliverable_type == "changelog":
        fields.update({
            "product_name": config.get("product_name", "the product"),
            "release_type": config.get("release_type", "weekly"),
            "audience": config.get("audience", "mixed"),
            "sections_list": build_sections_list(deliverable_type, config),
            "format": config.get("format", "user_friendly").replace("_", "-"),
            "links_instruction": "- Include links to documentation or features where available" if config.get("include_links", True) else "",
        })

    elif deliverable_type == "one_on_one_prep":
        focus_areas = config.get("focus_areas", ["performance", "growth"])
        fields.update({
            "report_name": config.get("report_name", "the team member"),
            "meeting_cadence": config.get("meeting_cadence", "weekly"),
            "relationship": config.get("relationship", "direct_report").replace("_", " "),
            "sections_list": build_sections_list(deliverable_type, config),
            "focus_areas": ", ".join(focus_areas),
        })

    elif deliverable_type == "board_update":
        tone = config.get("tone", "balanced")
        tone_guidance = {
            "optimistic": "emphasize progress and opportunities while being honest",
            "balanced": "present both wins and challenges with equal weight",
            "candid": "be direct about challenges and what's needed",
        }
        fields.update({
            "company_name": config.get("company_name", "the company"),
            "stage": config.get("stage", "seed").replace("_", " "),
            "update_type": config.get("update_type", "quarterly"),
            "sections_list": build_sections_list(deliverable_type, config),
            "tone": tone,
            "tone_guidance": tone_guidance.get(tone, "balanced perspective"),
            "comparisons_instruction": "Include comparisons vs. last period and vs. plan where data is available" if config.get("include_comparisons", True) else "",
        })

    # =========================================================================
    # ADR-029 Phase 3: Email-Specific Types
    # =========================================================================

    elif deliverable_type == "inbox_summary":
        fields.update({
            "summary_period": config.get("summary_period", "daily"),
            "inbox_scope": config.get("inbox_scope", "unread"),
            "sections_list": build_sections_list(deliverable_type, config),
            "prioritization": config.get("prioritization", "by_urgency").replace("_", " "),
        })

    elif deliverable_type == "reply_draft":
        suggested_actions = config.get("suggested_actions", [])
        fields.update({
            "thread_id": config.get("thread_id", ""),
            "tone": config.get("tone", "professional"),
            "sections_list": build_sections_list(deliverable_type, config),
            "quote_instruction": "Include relevant quotes from the original message" if config.get("include_original_quotes", True) else "Do not quote the original message",
            "suggested_actions": f"USER HINTS:\n{chr(10).join('- ' + a for a in suggested_actions)}" if suggested_actions else "",
        })

    elif deliverable_type == "follow_up_tracker":
        fields.update({
            "tracking_period": config.get("tracking_period", "7d"),
            "sections_list": build_sections_list(deliverable_type, config),
            "prioritize_by": config.get("prioritize_by", "age").replace("_", " "),
        })

    elif deliverable_type == "thread_summary":
        detail_level = config.get("detail_level", "brief")
        detail_guidance = "concise and scannable" if detail_level == "brief" else "thorough with context"
        fields.update({
            "thread_id": config.get("thread_id", ""),
            "sections_list": build_sections_list(deliverable_type, config),
            "detail_level": detail_level,
            "detail_guidance": detail_guidance,
        })

    # =========================================================================
    # ADR-046: Calendar-Triggered Types
    # =========================================================================

    elif deliverable_type == "meeting_prep":
        # Extract meeting info from config
        meeting_info = config.get("meeting", {})
        attendees = meeting_info.get("attendees", [])
        attendee_names = [a.get("display_name") or a.get("email", "Unknown") for a in attendees[:10]]
        fields.update({
            "meeting_title": meeting_info.get("title", config.get("meeting_title", "Upcoming Meeting")),
            "meeting_time": meeting_info.get("start", config.get("meeting_time", "")),
            "attendees_list": ", ".join(attendee_names) if attendee_names else "Not specified",
            "meeting_description": f"MEETING DESCRIPTION:\n{meeting_info.get('description', '')}" if meeting_info.get("description") else "",
            "sections_list": build_sections_list(deliverable_type, config),
        })

    elif deliverable_type == "weekly_calendar_preview":
        # Extract calendar summary info
        calendar_summary = config.get("calendar_summary", {})
        fields.update({
            "week_start": config.get("week_start", "this week"),
            "calendar_summary": calendar_summary.get("raw", "See events in context"),
            "meeting_count": str(calendar_summary.get("meeting_count", "multiple")),
            "total_hours": str(calendar_summary.get("total_hours", "N/A")),
            "busiest_day": calendar_summary.get("busiest_day", "N/A"),
            "free_blocks": calendar_summary.get("free_blocks", "See calendar for details"),
            "sections_list": build_sections_list(deliverable_type, config),
        })

    # Phase 2: Strategic Intelligence Types
    elif deliverable_type == "deep_research":
        time_horizon_map = {
            "current": "current state/near-term",
            "1_year": "1-year outlook",
            "3_year": "3-year strategic horizon",
            "5_year": "5-year long-term vision",
        }
        fields.update({
            "topic": config.get("topic", "Research topic"),
            "research_type": config.get("research_type", "strategic"),
            "depth": config.get("depth", "comprehensive"),
            "time_horizon_text": time_horizon_map.get(config.get("time_horizon", "current"), "current"),
            "sections_list": build_sections_list(deliverable_type, config),
            "sources_required": str(config.get("sources_required", 10)),
            "include_citations": config.get("include_citations", True),
        })

    elif deliverable_type == "daily_strategy_reflection":
        focus_area = config.get("focus_area")
        fields.update({
            "focus_area_text": focus_area if focus_area else "general strategic development",
            "lookback_days": str(config.get("lookback_days", 1)),
            "reflection_time": config.get("reflection_time", "evening"),
            "tone": config.get("tone", "reflective"),
            "sections_list": build_sections_list(deliverable_type, config),
            "context_synthesis": "CONTEXT SYNTHESIS (Layer 3 user context):\n" + gathered_context if config.get("include_context_synthesis", True) else "",
        })

    elif deliverable_type == "intelligence_brief":
        fields.update({
            "brief_type": config.get("brief_type", "strategic"),
            "audience": config.get("audience", "executive"),
            "time_sensitivity": config.get("time_sensitivity", "daily"),
            "sections_list": build_sections_list(deliverable_type, config),
            "include_confidence_levels": config.get("include_confidence_levels", True),
            "max_length_words": str(config.get("max_length_words", 800)),
        })

    # =========================================================================
    # ADR-035: Platform-First Wave 1 Types
    # =========================================================================

    elif deliverable_type == "slack_channel_digest":
        fields.update({
            "focus": config.get("focus", "key discussions and decisions"),
            "reply_threshold": str(config.get("reply_threshold", 3)),
            "reaction_threshold": str(config.get("reaction_threshold", 3)),
            "sections_list": build_sections_list(deliverable_type, config),
        })

    elif deliverable_type == "slack_standup":
        fields.update({
            "source_mode": config.get("source_mode", "individual"),
            "format": config.get("format", "bullets"),
            "sections_list": build_sections_list(deliverable_type, config),
        })

    elif deliverable_type == "gmail_inbox_brief":
        fields.update({
            "focus": config.get("focus", "unread and action-required emails"),
            "sections_list": build_sections_list(deliverable_type, config),
        })

    elif deliverable_type == "notion_page_summary":
        fields.update({
            "summary_type": config.get("summary_type", "activity"),
            "max_depth": str(config.get("max_depth", 2)),
            "sections_list": build_sections_list(deliverable_type, config),
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


def validate_stakeholder_update(content: str, config: dict) -> dict:
    """Validate a stakeholder update output."""
    issues = []

    sections = normalize_sections(config.get("sections", {}))
    required_sections = [k for k, v in sections.items() if v]

    content_lower = content.lower()

    section_keywords = {
        "executive_summary": ["executive summary", "summary", "overview", "at a glance"],
        "highlights": ["highlights", "wins", "achievements", "key developments"],
        "challenges": ["challenges", "obstacles", "issues", "mitigations"],
        "metrics": ["metrics", "numbers", "kpis", "performance"],
        "outlook": ["outlook", "looking ahead", "next period", "focus areas"],
    }

    for section in required_sections:
        keywords = section_keywords.get(section, [section])
        if not any(kw in content_lower for kw in keywords):
            issues.append(f"Missing section: {section}")

    # Check for executive summary at the start
    if "executive_summary" in required_sections:
        # Should appear in first 20% of content
        first_portion = content[:len(content) // 5].lower()
        if not any(kw in first_portion for kw in ["summary", "overview"]):
            issues.append("Executive summary should appear at the beginning")

    # Check word count (stakeholder updates should be substantial)
    word_count = len(content.split())
    if word_count < 300:
        issues.append(f"Too brief for stakeholder update: {word_count} words (expected 300+)")

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


def validate_meeting_summary(content: str, config: dict) -> dict:
    """Validate a meeting summary output."""
    issues = []

    sections = normalize_sections(config.get("sections", {}))
    required_sections = [k for k, v in sections.items() if v]

    content_lower = content.lower()

    section_keywords = {
        "context": ["attendees", "context", "purpose", "participants"],
        "discussion": ["discussed", "discussion", "talked about", "covered"],
        "decisions": ["decisions", "decided", "agreed", "resolved"],
        "action_items": ["action items", "action:", "todo", "next steps", "assigned"],
        "followups": ["follow-up", "followup", "next meeting", "parking lot"],
    }

    for section in required_sections:
        keywords = section_keywords.get(section, [section])
        if not any(kw in content_lower for kw in keywords):
            issues.append(f"Missing section: {section}")

    # Check that action items have owners (look for @ or name patterns)
    if "action_items" in required_sections:
        action_section = re.search(
            r'action items?.*?(?=\n[A-Z]|\n##|\Z)',
            content,
            re.IGNORECASE | re.DOTALL
        )
        if action_section:
            action_text = action_section.group()
            # Look for owner patterns: "@name", "Name:", "[Name]", "(Name)"
            has_owners = bool(re.search(r'[@\[\(]?\b[A-Z][a-z]+\b[\]\)]?:', action_text))
            if not has_owners and len(action_text) > 50:
                issues.append("Action items should have assigned owners")

    # Word count check
    word_count = len(content.split())
    if word_count < 150:
        issues.append(f"Too brief: {word_count} words (expected 150+)")

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
# Beta Tier Validation Functions
# =============================================================================

def validate_client_proposal(content: str, config: dict) -> dict:
    """Validate a client proposal output."""
    issues = []
    content_lower = content.lower()

    sections = normalize_sections(config.get("sections", {}))
    required_sections = [k for k, v in sections.items() if v]

    section_keywords = {
        "executive_summary": ["summary", "overview", "introduction"],
        "needs_understanding": ["understand", "needs", "requirements", "goals", "objectives"],
        "approach": ["approach", "methodology", "how we", "our process"],
        "deliverables": ["deliverables", "you will receive", "we will provide"],
        "timeline": ["timeline", "schedule", "milestones", "weeks", "phases"],
        "investment": ["investment", "pricing", "cost", "fee", "budget"],
        "social_proof": ["experience", "clients", "similar", "case", "testimonial"],
    }

    for section in required_sections:
        keywords = section_keywords.get(section, [section])
        if not any(kw in content_lower for kw in keywords):
            issues.append(f"Missing section: {section}")

    # Check for generic/vague content
    vague_phrases = ["best practices", "industry-leading", "comprehensive solution", "world-class"]
    vague_count = sum(1 for phrase in vague_phrases if phrase in content_lower)
    if vague_count > 2:
        issues.append("Content may be too generic - add more specifics")

    word_count = len(content.split())
    if word_count < 300:
        issues.append(f"Too short for a proposal: {word_count} words (expected 300+)")

    score = max(0, 1.0 - (len(issues) * 0.15))
    return {"valid": len(issues) == 0, "issues": issues, "score": score}


def validate_performance_self_assessment(content: str, config: dict) -> dict:
    """Validate a performance self-assessment output."""
    issues = []
    content_lower = content.lower()

    sections = normalize_sections(config.get("sections", {}))
    required_sections = [k for k, v in sections.items() if v]

    section_keywords = {
        "summary": ["summary", "overview", "period"],
        "accomplishments": ["accomplishments", "achieved", "completed", "delivered"],
        "goals_progress": ["goals", "objectives", "targets", "progress"],
        "challenges": ["challenges", "obstacles", "difficulties", "learned"],
        "development": ["development", "growth", "improve", "skills"],
        "next_period_goals": ["next", "upcoming", "focus", "plan to"],
    }

    for section in required_sections:
        keywords = section_keywords.get(section, [section])
        if not any(kw in content_lower for kw in keywords):
            issues.append(f"Missing section: {section}")

    # Check for quantification if enabled
    if config.get("quantify_impact", True):
        has_numbers = bool(re.search(r'\d+%|\d+x|\$\d+|\d+ (users|customers|projects|deals)', content))
        if not has_numbers:
            issues.append("Consider adding quantified impact (%, numbers, metrics)")

    word_count = len(content.split())
    review_period = config.get("review_period", "quarterly")
    expected = {"quarterly": (400, 1000), "semi_annual": (600, 1500), "annual": (800, 2000)}
    min_words, _ = expected.get(review_period, (400, 1000))
    if word_count < min_words * 0.7:
        issues.append(f"Too short for {review_period} review: {word_count} words")

    score = max(0, 1.0 - (len(issues) * 0.15))
    return {"valid": len(issues) == 0, "issues": issues, "score": score}


def validate_newsletter_section(content: str, config: dict) -> dict:
    """Validate a newsletter section output."""
    issues = []

    word_count = len(content.split())
    length = config.get("length", "medium")
    expected = {"short": (80, 250), "medium": (180, 500), "long": (350, 1000)}
    min_words, max_words = expected.get(length, (180, 500))

    if word_count < min_words * 0.7:
        issues.append(f"Too short: {word_count} words (expected {min_words}+)")
    if word_count > max_words * 1.5:
        issues.append(f"Too long: {word_count} words (expected ~{max_words})")

    # Check for CTA if enabled
    sections = config.get("sections", {})
    if sections.get("cta", True):
        cta_keywords = ["click", "sign up", "learn more", "check out", "try", "get started", "visit"]
        if not any(kw in content.lower() for kw in cta_keywords):
            issues.append("Missing call to action")

    score = max(0, 1.0 - (len(issues) * 0.2))
    return {"valid": len(issues) == 0, "issues": issues, "score": score}


def validate_changelog(content: str, config: dict) -> dict:
    """Validate a changelog output."""
    issues = []
    content_lower = content.lower()

    sections = normalize_sections(config.get("sections", {}))
    required_sections = [k for k, v in sections.items() if v]

    section_keywords = {
        "highlights": ["highlights", "notable", "major"],
        "new_features": ["new", "added", "introducing"],
        "improvements": ["improved", "enhanced", "better", "updated"],
        "bug_fixes": ["fixed", "bug", "resolved", "issue"],
        "breaking_changes": ["breaking", "migration", "deprecated"],
        "whats_next": ["next", "upcoming", "roadmap", "coming soon"],
    }

    for section in required_sections:
        keywords = section_keywords.get(section, [section])
        if not any(kw in content_lower for kw in keywords):
            issues.append(f"Missing section: {section}")

    word_count = len(content.split())
    if word_count < 100:
        issues.append(f"Too brief: {word_count} words (expected 100+)")

    score = max(0, 1.0 - (len(issues) * 0.2))
    return {"valid": len(issues) == 0, "issues": issues, "score": score}


def validate_one_on_one_prep(content: str, config: dict) -> dict:
    """Validate a 1:1 prep output."""
    issues = []
    content_lower = content.lower()

    sections = normalize_sections(config.get("sections", {}))
    required_sections = [k for k, v in sections.items() if v]

    section_keywords = {
        "context": ["context", "since last", "recent", "update"],
        "topics": ["topics", "discuss", "agenda", "talk about"],
        "recognition": ["recognition", "kudos", "great", "well done", "appreciate"],
        "concerns": ["concerns", "issues", "blockers", "challenges"],
        "career": ["career", "growth", "development", "goals"],
        "previous_actions": ["action items", "follow up", "previous", "last time"],
    }

    for section in required_sections:
        keywords = section_keywords.get(section, [section])
        if not any(kw in content_lower for kw in keywords):
            issues.append(f"Missing section: {section}")

    # Check for personalization
    report_name = config.get("report_name", "")
    if report_name and report_name.lower() not in content_lower:
        issues.append(f"Not personalized to {report_name}")

    word_count = len(content.split())
    if word_count < 150:
        issues.append(f"Too brief: {word_count} words (expected 150+)")

    score = max(0, 1.0 - (len(issues) * 0.15))
    return {"valid": len(issues) == 0, "issues": issues, "score": score}


def validate_board_update(content: str, config: dict) -> dict:
    """Validate a board update output."""
    issues = []
    content_lower = content.lower()

    sections = normalize_sections(config.get("sections", {}))
    required_sections = [k for k, v in sections.items() if v]

    section_keywords = {
        "executive_summary": ["summary", "overview", "tldr"],
        "metrics": ["metrics", "kpis", "numbers", "growth", "revenue", "users"],
        "strategic_progress": ["strategic", "progress", "initiatives", "goals"],
        "challenges": ["challenges", "risks", "concerns", "obstacles"],
        "financials": ["financials", "cash", "runway", "burn", "revenue"],
        "asks": ["asks", "need", "request", "help with", "decision"],
        "outlook": ["outlook", "next quarter", "ahead", "plan"],
    }

    for section in required_sections:
        keywords = section_keywords.get(section, [section])
        if not any(kw in content_lower for kw in keywords):
            issues.append(f"Missing section: {section}")

    # Board updates should have metrics
    if sections.get("metrics", True):
        has_numbers = bool(re.search(r'\d+%|\$\d+|\d+k|\d+M|\d+ (users|customers)', content))
        if not has_numbers:
            issues.append("Missing quantified metrics")

    # Check if asks section is clear
    if sections.get("asks", True):
        if "asks" not in content_lower and "need" not in content_lower and "request" not in content_lower:
            issues.append("Asks section should be explicit")

    word_count = len(content.split())
    if word_count < 400:
        issues.append(f"Too brief for board update: {word_count} words (expected 400+)")
    if word_count > 1200:
        issues.append(f"Too long: {word_count} words (board members are busy, target 500-1000)")

    score = max(0, 1.0 - (len(issues) * 0.15))
    return {"valid": len(issues) == 0, "issues": issues, "score": score}


# =============================================================================
# ADR-029 Phase 3: Email-Specific Validation Functions
# =============================================================================

def validate_inbox_summary(content: str, config: dict) -> dict:
    """Validate an inbox summary output."""
    issues = []
    content_lower = content.lower()

    sections = normalize_sections(config.get("sections", {}))
    required_sections = [k for k, v in sections.items() if v]

    section_keywords = {
        "overview": ["overview", "summary", "inbox", "messages", "emails"],
        "urgent": ["urgent", "immediate", "asap", "priority", "critical"],
        "action_required": ["action", "required", "respond", "reply", "need to"],
        "fyi_items": ["fyi", "informational", "no action", "awareness"],
        "threads_to_close": ["close", "archive", "wrap up", "complete", "done"],
    }

    for section in required_sections:
        keywords = section_keywords.get(section, [section])
        if not any(kw in content_lower for kw in keywords):
            issues.append(f"Missing section: {section}")

    # Check for structure (should have bullet points or sections)
    has_structure = "- " in content or "• " in content or "##" in content
    if not has_structure:
        issues.append("Summary should be scannable - use bullet points or sections")

    word_count = len(content.split())
    if word_count < 100:
        issues.append(f"Too brief: {word_count} words (expected 100+)")

    score = max(0, 1.0 - (len(issues) * 0.2))
    return {"valid": len(issues) == 0, "issues": issues, "score": score}


def validate_reply_draft(content: str, config: dict) -> dict:
    """Validate a reply draft output."""
    issues = []
    content_lower = content.lower()

    # Reply drafts should have a greeting and closing
    has_greeting = any(g in content_lower[:100] for g in ["hi", "hello", "dear", "hey", "good morning", "good afternoon"])
    has_closing = any(c in content_lower[-200:] for c in ["best", "thanks", "regards", "cheers", "sincerely", "thank you"])

    if not has_greeting:
        issues.append("Reply should start with an appropriate greeting")
    if not has_closing:
        issues.append("Reply should have a closing/sign-off")

    # Check for acknowledgment if enabled
    sections = config.get("sections", {})
    if sections.get("acknowledgment", True):
        ack_keywords = ["thank you for", "thanks for", "regarding", "re:", "about your", "in response"]
        if not any(kw in content_lower for kw in ack_keywords):
            issues.append("Consider acknowledging the original message")

    word_count = len(content.split())
    if word_count < 30:
        issues.append(f"Reply too brief: {word_count} words")
    if word_count > 500:
        issues.append(f"Reply may be too long: {word_count} words (consider being more concise)")

    score = max(0, 1.0 - (len(issues) * 0.2))
    return {"valid": len(issues) == 0, "issues": issues, "score": score}


def validate_follow_up_tracker(content: str, config: dict) -> dict:
    """Validate a follow-up tracker output."""
    issues = []
    content_lower = content.lower()

    sections = normalize_sections(config.get("sections", {}))
    required_sections = [k for k, v in sections.items() if v]

    section_keywords = {
        "overdue": ["overdue", "past due", "late", "pending", "no response"],
        "due_soon": ["due soon", "this week", "upcoming", "coming up"],
        "waiting_on_others": ["waiting", "pending from", "awaiting", "no reply from"],
        "commitments_made": ["committed", "promised", "said", "agreed to", "will"],
    }

    for section in required_sections:
        keywords = section_keywords.get(section, [section])
        if not any(kw in content_lower for kw in keywords):
            issues.append(f"Missing section: {section}")

    # Should have specific items (look for names, dates, or bullet points)
    has_items = "- " in content or "• " in content or re.search(r'\d{1,2}[/-]\d{1,2}', content)
    if not has_items:
        issues.append("Tracker should list specific follow-up items")

    word_count = len(content.split())
    if word_count < 50:
        issues.append(f"Too brief: {word_count} words (expected 50+)")

    score = max(0, 1.0 - (len(issues) * 0.2))
    return {"valid": len(issues) == 0, "issues": issues, "score": score}


def validate_thread_summary(content: str, config: dict) -> dict:
    """Validate a thread summary output."""
    issues = []
    content_lower = content.lower()

    sections = normalize_sections(config.get("sections", {}))
    required_sections = [k for k, v in sections.items() if v]

    section_keywords = {
        "participants": ["participants", "involved", "from", "between", "with"],
        "timeline": ["timeline", "on", "at", "started", "then", "followed by"],
        "key_points": ["key points", "main", "discussed", "topics", "covered"],
        "decisions": ["decided", "decision", "agreed", "concluded", "resolved"],
        "open_questions": ["open", "questions", "unclear", "tbd", "pending", "unresolved"],
    }

    for section in required_sections:
        keywords = section_keywords.get(section, [section])
        if not any(kw in content_lower for kw in keywords):
            issues.append(f"Missing section: {section}")

    detail_level = config.get("detail_level", "brief")
    word_count = len(content.split())
    expected = {"brief": (100, 400), "detailed": (300, 1000)}
    min_words, max_words = expected.get(detail_level, (100, 400))

    if word_count < min_words * 0.7:
        issues.append(f"Too brief for {detail_level} summary: {word_count} words")
    if word_count > max_words * 1.5:
        issues.append(f"Too long for {detail_level} summary: {word_count} words")

    score = max(0, 1.0 - (len(issues) * 0.2))
    return {"valid": len(issues) == 0, "issues": issues, "score": score}


# =============================================================================
# ADR-035: Platform-First Wave 1 Validators
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


def validate_slack_standup(content: str, config: dict) -> dict:
    """Validate a Slack standup output."""
    issues = []
    content_lower = content.lower()

    sections = normalize_sections(config.get("sections", {}))
    required_sections = [k for k, v in sections.items() if v]

    section_keywords = {
        "done": ["done", "completed", "finished", "shipped", "merged"],
        "doing": ["doing", "working on", "in progress", "continuing", "starting"],
        "blockers": ["blocker", "blocked", "stuck", "waiting", "need"],
    }

    for section in required_sections:
        keywords = section_keywords.get(section, [section])
        if not any(kw in content_lower for kw in keywords):
            issues.append(f"Missing section: {section}")

    # Standups should be brief
    word_count = len(content.split())
    if word_count > 250:
        issues.append(f"Standup too verbose: {word_count} words (aim for <200)")
    if word_count < 30:
        issues.append(f"Standup too brief: {word_count} words")

    # Check for bullet format
    format_type = config.get("format", "bullet")
    if format_type == "bullet" and not ("- " in content or "• " in content):
        issues.append("Bullet format requested but no bullets found")

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


def validate_deep_research(content: str, config: dict) -> dict:
    """Validate deep research output (Phase 2)."""
    issues = []
    content_lower = content.lower()
    word_count = len(content.split())

    # Depth-based word count requirements
    depth = config.get("depth", "comprehensive")
    min_words = 1500 if depth == "comprehensive" else 2500
    if word_count < min_words:
        issues.append(f"Research too brief for {depth} depth: {word_count} words (expected {min_words}+)")

    # Check for required sections
    sections = normalize_sections(config.get("sections", {}))
    required_sections = [k for k, v in sections.items() if v]

    section_keywords = {
        "executive_summary": ["executive summary", "key findings", "summary"],
        "background": ["background", "context", "introduction"],
        "key_findings": ["findings", "discovered", "research shows"],
        "analysis": ["analysis", "implications", "patterns"],
        "recommendations": ["recommend", "suggest", "next steps", "actions"],
        "sources": ["source", "reference", "citation"],
    }

    for section in required_sections:
        keywords = section_keywords.get(section, [section])
        if not any(kw in content_lower for kw in keywords):
            issues.append(f"Missing section: {section}")

    # Check for citations if required
    if config.get("include_citations", True):
        has_citations = "[" in content or "(" in content or "source:" in content_lower
        if not has_citations:
            issues.append("Citations required but not found in output")

    score = max(0, 1.0 - (len(issues) * 0.15))
    return {"valid": len(issues) == 0, "issues": issues, "score": score}


def validate_daily_strategy_reflection(content: str, config: dict) -> dict:
    """Validate daily strategy reflection output (Phase 2)."""
    issues = []
    content_lower = content.lower()
    word_count = len(content.split())

    # Target length: 400-800 words
    if word_count < 300:
        issues.append(f"Reflection too brief: {word_count} words (expected 400-800)")
    if word_count > 1000:
        issues.append(f"Reflection too long: {word_count} words (expected 400-800)")

    # Check for required sections
    sections = normalize_sections(config.get("sections", {}))
    required_sections = [k for k, v in sections.items() if v]

    section_keywords = {
        "strategic_movements": ["strategic", "development", "shift", "movement"],
        "decision_points": ["decision", "choice", "implications"],
        "pattern_recognition": ["pattern", "trend", "emerging", "signal"],
        "action_prioritization": ["priorit", "next", "focus", "action"],
        "learning_insights": ["learn", "insight", "realize", "understand"],
    }

    for section in required_sections:
        keywords = section_keywords.get(section, [section])
        if not any(kw in content_lower for kw in keywords):
            issues.append(f"Missing section: {section}")

    # Should be reflective, not just task listing
    task_indicators = content_lower.count("completed") + content_lower.count("finished") + content_lower.count("done")
    if task_indicators > 10:
        issues.append("Reflection should focus on strategy, not task completion")

    score = max(0, 1.0 - (len(issues) * 0.2))
    return {"valid": len(issues) == 0, "issues": issues, "score": score}


def validate_intelligence_brief(content: str, config: dict) -> dict:
    """Validate intelligence brief output (Phase 2)."""
    issues = []
    content_lower = content.lower()
    word_count = len(content.split())

    # Strict length requirement
    max_words = config.get("max_length_words", 800)
    if word_count > max_words:
        issues.append(f"Brief too long: {word_count} words (max {max_words})")
    if word_count < max_words * 0.5:
        issues.append(f"Brief too short: {word_count} words (expected {max_words * 0.6}-{max_words})")

    # Check for required sections
    sections = normalize_sections(config.get("sections", {}))
    required_sections = [k for k, v in sections.items() if v]

    section_keywords = {
        "situation_summary": ["situation", "summary", "current state"],
        "key_developments": ["development", "changed", "update", "new"],
        "threat_opportunities": ["threat", "opportunit", "risk", "opening"],
        "recommended_actions": ["recommend", "action", "next steps", "should"],
        "monitoring_indicators": ["monitor", "watch", "track", "indicator"],
    }

    for section in required_sections:
        keywords = section_keywords.get(section, [section])
        if not any(kw in content_lower for kw in keywords):
            issues.append(f"Missing section: {section}")

    # Check for confidence levels if required
    if config.get("include_confidence_levels", True):
        has_confidence = "high" in content_lower and "medium" in content_lower
        if not has_confidence:
            issues.append("Confidence levels required but not consistently marked")

    # Should be concise and action-oriented
    has_bullets = "- " in content or "• " in content
    if not has_bullets:
        issues.append("Intelligence brief should use bullet points for scannability")

    score = max(0, 1.0 - (len(issues) * 0.15))
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
    validators = {
        # Tier 1 - Stable
        "status_report": validate_status_report,
        "stakeholder_update": validate_stakeholder_update,
        "research_brief": validate_research_brief,
        "meeting_summary": validate_meeting_summary,
        "custom": validate_custom,
        # Beta Tier
        "client_proposal": validate_client_proposal,
        "performance_self_assessment": validate_performance_self_assessment,
        "newsletter_section": validate_newsletter_section,
        "changelog": validate_changelog,
        "one_on_one_prep": validate_one_on_one_prep,
        "board_update": validate_board_update,
        # ADR-029 Phase 3: Email-specific
        "inbox_summary": validate_inbox_summary,
        "reply_draft": validate_reply_draft,
        "follow_up_tracker": validate_follow_up_tracker,
        "thread_summary": validate_thread_summary,
        # ADR-035: Platform-First Wave 1
        "slack_channel_digest": validate_slack_channel_digest,
        "slack_standup": validate_slack_standup,
        "gmail_inbox_brief": validate_gmail_inbox_brief,
        "notion_page_summary": validate_notion_page_summary,
        # Phase 2: Strategic Intelligence Types
        "deep_research": validate_deep_research,
        "daily_strategy_reflection": validate_daily_strategy_reflection,
        "intelligence_brief": validate_intelligence_brief,
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



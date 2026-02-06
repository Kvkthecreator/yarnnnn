"""
Deliverable Pipeline Execution Service

ADR-018: Recurring Deliverables Product Pivot
ADR-019: Deliverable Types System

Implements the 3-step chained pipeline:
1. Gather - Research agent pulls latest context from sources
2. Synthesize - Content agent produces the deliverable (type-aware)
3. Stage - Validate and notify user for review

Each step creates a work ticket with dependency chaining.
Type-specific prompts and validation ensure quality for each deliverable type.
"""

import logging
import json
import re
from datetime import datetime
from typing import Optional, Literal

from services.work_execution import execute_work_ticket

logger = logging.getLogger(__name__)


# =============================================================================
# ADR-029 Phase 2: Integration Data Source Fetching
# =============================================================================

async def fetch_integration_source_data(
    client,
    user_id: str,
    source: dict,
) -> Optional[str]:
    """
    Fetch data from an integration source for the gather step.

    ADR-029 Phase 2: When a deliverable has integration_import sources,
    we fetch the actual data from the integration (Gmail, Slack, Notion)
    and include it in the context.

    Args:
        client: Supabase client
        user_id: User ID
        source: Source dict with provider, source, filters

    Returns:
        Formatted context string, or None if fetch failed
    """
    import os
    from integrations.core.client import MCPClientManager
    from integrations.core.token_manager import TokenManager

    provider = source.get("provider")
    source_query = source.get("source", "inbox")
    filters = source.get("filters", {})

    if not provider:
        logger.warning("[GATHER] Integration source missing provider")
        return None

    # Get user's integration
    integration_result = (
        client.table("user_integrations")
        .select("id, access_token_encrypted, refresh_token_encrypted, metadata, status")
        .eq("user_id", user_id)
        .eq("provider", provider)
        .eq("status", "active")
        .single()
        .execute()
    )

    if not integration_result.data:
        logger.warning(f"[GATHER] No active {provider} integration for user")
        return None

    integration = integration_result.data
    token_manager = TokenManager()
    mcp_manager = MCPClientManager()

    try:
        if provider == "gmail":
            return await _fetch_gmail_data(
                mcp_manager, token_manager, integration, user_id, source_query, filters
            )
        elif provider == "slack":
            return await _fetch_slack_data(
                mcp_manager, token_manager, integration, user_id, source_query, filters
            )
        elif provider == "notion":
            return await _fetch_notion_data(
                mcp_manager, token_manager, integration, user_id, source_query, filters
            )
        else:
            logger.warning(f"[GATHER] Unsupported integration provider: {provider}")
            return None

    except Exception as e:
        logger.error(f"[GATHER] Failed to fetch {provider} data: {e}")
        return None


async def _fetch_gmail_data(
    mcp_manager,
    token_manager,
    integration: dict,
    user_id: str,
    source_query: str,
    filters: dict,
) -> Optional[str]:
    """Fetch Gmail messages and format as context."""
    import os

    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

    if not client_id or not client_secret:
        return None

    refresh_token = token_manager.decrypt(integration["refresh_token_encrypted"])
    if not refresh_token:
        return None

    # Build query from source and filters
    query_parts = []

    if source_query.startswith("query:"):
        query_parts.append(source_query.split(":", 1)[1])
    elif source_query != "inbox":
        query_parts.append(source_query)

    if filters.get("from"):
        query_parts.append(f"from:{filters['from']}")
    if filters.get("subject_contains"):
        query_parts.append(f"subject:{filters['subject_contains']}")
    if filters.get("after"):
        # Convert "7d" to date
        after_val = filters["after"]
        if after_val.endswith("d"):
            from datetime import datetime, timedelta
            days = int(after_val[:-1])
            date_str = (datetime.now() - timedelta(days=days)).strftime("%Y/%m/%d")
            query_parts.append(f"after:{date_str}")
        else:
            query_parts.append(f"after:{after_val}")

    query = " ".join(query_parts) if query_parts else None

    # Fetch messages
    messages = await mcp_manager.list_gmail_messages(
        user_id=user_id,
        client_id=client_id,
        client_secret=client_secret,
        refresh_token=refresh_token,
        query=query,
        max_results=30,
    )

    if not messages:
        return "[Gmail] No messages found matching criteria"

    # Fetch full content for top messages
    lines = [f"[Gmail Integration Data - {len(messages)} messages]\n"]

    for msg in messages[:15]:
        msg_id = msg.get("id")
        if msg_id:
            try:
                full_msg = await mcp_manager.get_gmail_message(
                    user_id=user_id,
                    message_id=msg_id,
                    client_id=client_id,
                    client_secret=client_secret,
                    refresh_token=refresh_token,
                )

                headers = full_msg.get("headers", {})
                subject = headers.get("Subject", headers.get("subject", "(no subject)"))
                from_addr = headers.get("From", headers.get("from", "unknown"))
                date = headers.get("Date", headers.get("date", ""))
                body = full_msg.get("body", full_msg.get("snippet", ""))

                if len(body) > 500:
                    body = body[:500] + "..."

                lines.append(f"---\nFrom: {from_addr}\nDate: {date}\nSubject: {subject}\n{body}\n")

            except Exception as e:
                logger.warning(f"[GATHER] Failed to fetch Gmail message {msg_id}: {e}")

    return "\n".join(lines)


async def _fetch_slack_data(
    mcp_manager,
    token_manager,
    integration: dict,
    user_id: str,
    source_query: str,
    filters: dict,
) -> Optional[str]:
    """Fetch Slack messages and format as context."""
    access_token = token_manager.decrypt(integration["access_token_encrypted"])
    metadata = integration.get("metadata", {}) or {}
    team_id = metadata.get("team_id")

    if not access_token or not team_id:
        return None

    channel_id = filters.get("channel_id") or source_query

    if not channel_id:
        return "[Slack] No channel specified"

    messages = await mcp_manager.get_slack_channel_history(
        user_id=user_id,
        channel_id=channel_id,
        bot_token=access_token,
        team_id=team_id,
        limit=50,
    )

    if not messages:
        return "[Slack] No messages found in channel"

    lines = [f"[Slack Integration Data - #{channel_id} - {len(messages)} messages]\n"]

    for msg in messages[:30]:
        text = msg.get("text", "")
        user = msg.get("user", "unknown")
        ts = msg.get("ts", "")

        if text:
            lines.append(f"[{user}] {text}")

    return "\n".join(lines)


async def _fetch_notion_data(
    mcp_manager,
    token_manager,
    integration: dict,
    user_id: str,
    source_query: str,
    filters: dict,
) -> Optional[str]:
    """Fetch Notion page content and format as context."""
    access_token = token_manager.decrypt(integration["access_token_encrypted"])

    if not access_token:
        return None

    page_id = filters.get("page_id") or source_query

    if not page_id:
        return "[Notion] No page specified"

    page_content = await mcp_manager.get_notion_page_content(
        user_id=user_id,
        page_id=page_id,
        auth_token=access_token,
    )

    if not page_content:
        return "[Notion] Page not found or empty"

    title = page_content.get("title", "Untitled")
    content = page_content.get("content", "")

    if len(content) > 3000:
        content = content[:3000] + "... [truncated]"

    return f"[Notion Integration Data - {title}]\n\n{content}"


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
- Keep summary {detail_level} - {"concise and scannable" if detail_level == "brief" else "thorough with context"}

Write the thread summary now:""",
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


def build_sections_list(deliverable_type: str, config: dict) -> str:
    """Build formatted sections list based on enabled sections in config."""
    sections = config.get("sections", {})
    templates = SECTION_TEMPLATES.get(deliverable_type, {})

    enabled = []
    for section_key, is_enabled in sections.items():
        if is_enabled and section_key in templates:
            enabled.append(f"- {templates[section_key]}")

    if not enabled:
        # Default to all sections if none specified
        enabled = [f"- {desc}" for desc in templates.values()]

    return "\n".join(enabled)


def build_type_prompt(
    deliverable_type: str,
    config: dict,
    deliverable: dict,
    gathered_context: str,
    recipient_text: str,
    past_versions: str,
) -> str:
    """Build the type-specific synthesis prompt."""

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
        fields.update({
            "thread_id": config.get("thread_id", ""),
            "sections_list": build_sections_list(deliverable_type, config),
            "detail_level": detail_level,
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

    sections = config.get("sections", {})
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

    sections = config.get("sections", {})
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

    sections = config.get("sections", {})
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

    sections = config.get("sections", {})
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

    sections = config.get("sections", {})
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

    sections = config.get("sections", {})
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

    sections = config.get("sections", {})
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

    sections = config.get("sections", {})
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

    sections = config.get("sections", {})
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

    sections = config.get("sections", {})
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

    sections = config.get("sections", {})
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

    sections = config.get("sections", {})
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
    }

    validator = validators.get(deliverable_type, validate_custom)
    return validator(content, config)


async def execute_deliverable_pipeline(
    client,
    user_id: str,
    deliverable_id: str,
    version_number: int,
) -> dict:
    """
    Execute the full deliverable pipeline.

    Creates a new version, runs gather → synthesize → stage,
    and updates the deliverable with last_run_at.

    Args:
        client: Supabase client
        user_id: User UUID
        deliverable_id: Deliverable UUID
        version_number: Version number to create

    Returns:
        Pipeline result with version_id, status, and message
    """
    logger.info(f"[PIPELINE] Starting: deliverable={deliverable_id}, version={version_number}")

    # Get deliverable details
    deliverable_result = (
        client.table("deliverables")
        .select("*")
        .eq("id", deliverable_id)
        .single()
        .execute()
    )

    if not deliverable_result.data:
        return {"success": False, "error": "Deliverable not found"}

    deliverable = deliverable_result.data
    project_id = deliverable.get("project_id")

    # Create version record
    version_result = (
        client.table("deliverable_versions")
        .insert({
            "deliverable_id": deliverable_id,
            "version_number": version_number,
            "status": "generating",
        })
        .execute()
    )

    if not version_result.data:
        return {"success": False, "error": "Failed to create version"}

    version = version_result.data[0]
    version_id = version["id"]

    try:
        # Step 1: Gather
        logger.info(f"[PIPELINE] Step 1: Gather")
        gather_result = await execute_gather_step(
            client=client,
            user_id=user_id,
            project_id=project_id,
            deliverable=deliverable,
            version_id=version_id,
        )

        if not gather_result.get("success"):
            await update_version_status(client, version_id, "rejected")
            return {
                "success": False,
                "version_id": version_id,
                "status": "rejected",
                "message": f"Gather step failed: {gather_result.get('error')}",
            }

        gathered_context = gather_result.get("output", "")

        # Step 2: Synthesize
        logger.info(f"[PIPELINE] Step 2: Synthesize")
        synthesize_result = await execute_synthesize_step(
            client=client,
            user_id=user_id,
            project_id=project_id,
            deliverable=deliverable,
            version_id=version_id,
            gathered_context=gathered_context,
            gather_work_id=gather_result.get("work_id"),
        )

        if not synthesize_result.get("success"):
            await update_version_status(client, version_id, "rejected")
            return {
                "success": False,
                "version_id": version_id,
                "status": "rejected",
                "message": f"Synthesize step failed: {synthesize_result.get('error')}",
            }

        draft_content = synthesize_result.get("output", "")

        # Step 3: Stage
        logger.info(f"[PIPELINE] Step 3: Stage")
        stage_result = await execute_stage_step(
            client=client,
            version_id=version_id,
            draft_content=draft_content,
            deliverable=deliverable,
        )

        # Update deliverable last_run_at
        client.table("deliverables").update({
            "last_run_at": datetime.utcnow().isoformat(),
        }).eq("id", deliverable_id).execute()

        logger.info(f"[PIPELINE] Complete: version={version_id}, status=staged")

        return {
            "success": True,
            "version_id": version_id,
            "status": "staged",
            "message": "Deliverable ready for review",
        }

    except Exception as e:
        logger.error(f"[PIPELINE] Error: {e}")
        try:
            await update_version_status(client, version_id, "rejected")
        except Exception:
            pass  # Don't fail if status update fails
        return {
            "success": False,
            "version_id": version_id,
            "status": "rejected",
            "message": str(e),
        }


async def execute_gather_step(
    client,
    user_id: str,
    project_id: str,
    deliverable: dict,
    version_id: str,
) -> dict:
    """
    Step 1: Gather context from sources.

    Uses research agent to pull latest information from configured sources.
    Output is saved as a memory with source_type='agent_output'.

    ADR-029 Phase 2: For integration_import sources, we fetch actual data
    from the integration (Gmail, Slack, Notion) via MCP.
    """
    sources = deliverable.get("sources", [])
    title = deliverable.get("title", "Deliverable")

    # Build gather prompt
    source_descriptions = []
    integration_data_sections = []

    for source in sources:
        source_type = source.get("type", "description")
        value = source.get("value", "")
        label = source.get("label", "")

        if source_type == "url":
            source_descriptions.append(f"- Web source: {value}")
        elif source_type == "document":
            source_descriptions.append(f"- Document: {label or value}")
        elif source_type == "integration_import":
            # ADR-029 Phase 2: Fetch actual data from integration
            provider = source.get("provider", "unknown")
            source_query = source.get("source", "")
            source_descriptions.append(f"- Integration ({provider}): {source_query or 'default'}")

            logger.info(f"[GATHER] Fetching {provider} integration data")
            integration_data = await fetch_integration_source_data(
                client=client,
                user_id=user_id,
                source=source,
            )
            if integration_data:
                integration_data_sections.append(integration_data)
        else:
            source_descriptions.append(f"- Context: {value}")

    sources_text = "\n".join(source_descriptions) if source_descriptions else "No specific sources configured"

    # Include fetched integration data in the prompt
    integration_context = ""
    if integration_data_sections:
        integration_context = "\n\n## Integration Data (Fetched)\n\n" + "\n\n".join(integration_data_sections)

    gather_prompt = f"""Gather the latest context and information for producing: {title}

Description: {deliverable.get('description', 'No description provided')}

Configured sources:
{sources_text}
{integration_context}

Your task:
1. Review and synthesize any available information from the sources
2. Identify key updates, changes, or new data since the last delivery
3. Note any gaps or missing information that might be needed
4. Summarize the gathered context in a structured format

Output a comprehensive context summary that will be used to produce the deliverable."""

    # Create work ticket
    ticket_data = {
        "task": gather_prompt,
        "agent_type": "research",
        "project_id": project_id,
        "parameters": json.dumps({
            "deliverable_id": deliverable["id"],
            "step": "gather",
        }),
        "status": "pending",
        "deliverable_id": deliverable["id"],
        "deliverable_version_id": version_id,
        "pipeline_step": "gather",
        "chain_output_as_memory": True,
    }

    ticket_result = client.table("work_tickets").insert(ticket_data).execute()

    if not ticket_result.data:
        return {"success": False, "error": "Failed to create gather work ticket"}

    ticket_id = ticket_result.data[0]["id"]

    # Execute the work
    result = await execute_work_ticket(
        client=client,
        user_id=user_id,
        ticket_id=ticket_id,
    )

    if result.get("success"):
        # Save output as memory
        output_content = ""
        outputs = result.get("outputs", [])
        if outputs:
            output_content = outputs[0].get("content", "")

        if output_content:
            await save_as_memory(
                client=client,
                user_id=user_id,
                project_id=project_id,
                content=f"[GATHER] {output_content}",
                source_type="agent_output",
                tags=["pipeline:gather", f"deliverable:{deliverable['id']}"],
            )

        return {
            "success": True,
            "work_id": ticket_id,
            "output": output_content,
        }

    return {
        "success": False,
        "error": result.get("error", "Gather execution failed"),
    }


async def execute_synthesize_step(
    client,
    user_id: str,
    project_id: str,
    deliverable: dict,
    version_id: str,
    gathered_context: str,
    gather_work_id: Optional[str] = None,
) -> dict:
    """
    Step 2: Synthesize the deliverable content.

    ADR-019: Uses type-specific prompts based on deliverable_type and type_config.
    Falls back to generic prompt for legacy deliverables without type.
    """
    title = deliverable.get("title", "Deliverable")
    recipient = deliverable.get("recipient_context", {})

    # ADR-019: Get deliverable type and config
    deliverable_type = deliverable.get("deliverable_type", "custom")
    type_config = deliverable.get("type_config", {})

    # Get past versions for preference learning
    past_versions = await get_past_versions_context(client, deliverable["id"])

    # Build recipient context text
    recipient_text = ""
    if recipient:
        recipient_parts = []
        if recipient.get("name"):
            recipient_parts.append(f"Recipient: {recipient['name']}")
        if recipient.get("role"):
            recipient_parts.append(f"Role: {recipient['role']}")
        if recipient.get("priorities"):
            recipient_parts.append(f"Key priorities: {', '.join(recipient['priorities'])}")
        if recipient.get("notes"):
            recipient_parts.append(f"Notes: {recipient['notes']}")
        if recipient_parts:
            recipient_text = "RECIPIENT CONTEXT:\n" + "\n".join(recipient_parts)

    # ADR-019: Build type-specific prompt
    synthesize_prompt = build_type_prompt(
        deliverable_type=deliverable_type,
        config=type_config,
        deliverable=deliverable,
        gathered_context=gathered_context,
        recipient_text=recipient_text,
        past_versions=past_versions,
    )

    logger.info(f"[SYNTHESIZE] Using type-specific prompt for type={deliverable_type}")

    # ADR-028: Infer style_context from destination platform if set
    # Priority: 1) explicit type_config.style_context, 2) destination.platform, 3) none
    style_context = type_config.get("style_context")

    if not style_context:
        # Try to infer from destination
        destination = deliverable.get("destination")
        if destination and destination.get("platform"):
            platform = destination["platform"]
            # Map platform to style context
            style_context = platform  # slack, notion, etc. match style profile names
            logger.info(f"[SYNTHESIZE] Inferred style_context={style_context} from destination.platform")

    # Build parameters for content agent
    agent_params = {
        "deliverable_id": deliverable["id"],
        "step": "synthesize",
    }
    if style_context:
        agent_params["style_context"] = style_context
        logger.info(f"[SYNTHESIZE] Using style_context={style_context}")

    # Create work ticket with dependency
    ticket_data = {
        "task": synthesize_prompt,
        "agent_type": "content",
        "project_id": project_id,
        "parameters": json.dumps(agent_params),
        "status": "pending",
        "deliverable_id": deliverable["id"],
        "deliverable_version_id": version_id,
        "pipeline_step": "synthesize",
        "depends_on_work_id": gather_work_id,
        "chain_output_as_memory": True,
    }

    ticket_result = client.table("work_tickets").insert(ticket_data).execute()

    if not ticket_result.data:
        return {"success": False, "error": "Failed to create synthesize work ticket"}

    ticket_id = ticket_result.data[0]["id"]

    # Execute the work
    result = await execute_work_ticket(
        client=client,
        user_id=user_id,
        ticket_id=ticket_id,
    )

    if result.get("success"):
        output_content = ""
        outputs = result.get("outputs", [])
        if outputs:
            output_content = outputs[0].get("content", "")

        if output_content:
            await save_as_memory(
                client=client,
                user_id=user_id,
                project_id=project_id,
                content=f"[SYNTHESIZE] {output_content[:500]}...",  # Truncate for memory
                source_type="agent_output",
                tags=["pipeline:synthesize", f"deliverable:{deliverable['id']}"],
            )

        return {
            "success": True,
            "work_id": ticket_id,
            "output": output_content,
        }

    return {
        "success": False,
        "error": result.get("error", "Synthesize execution failed"),
    }


async def execute_stage_step(
    client,
    version_id: str,
    draft_content: str,
    deliverable: dict,
) -> dict:
    """
    Step 3: Stage the deliverable for review.

    ADR-019: Runs type-specific validation before staging.
    Updates version with draft content and sets status to 'staged'.
    Stores validation results for quality tracking.
    """
    # ADR-019: Run type-specific validation
    deliverable_type = deliverable.get("deliverable_type", "custom")
    type_config = deliverable.get("type_config", {})

    validation_result = validate_output(deliverable_type, draft_content, type_config)

    logger.info(
        f"[STAGE] Validation for type={deliverable_type}: "
        f"valid={validation_result['valid']}, score={validation_result['score']:.2f}, "
        f"issues={validation_result['issues']}"
    )

    # Store validation result
    try:
        client.table("deliverable_validation_results").insert({
            "version_id": version_id,
            "is_valid": validation_result["valid"],
            "validation_score": validation_result["score"],
            "issues": json.dumps(validation_result["issues"]),
            "validator_version": "1.0.0",  # Track validation logic version
        }).execute()
    except Exception as e:
        logger.warning(f"[STAGE] Failed to store validation result: {e}")

    # Update version with draft content
    update_result = (
        client.table("deliverable_versions")
        .update({
            "draft_content": draft_content,
            "status": "staged",
            "staged_at": datetime.utcnow().isoformat(),
        })
        .eq("id", version_id)
        .execute()
    )

    if not update_result.data:
        return {"success": False, "error": "Failed to stage version"}

    # TODO: Send staging notification email
    # This will use the existing email infrastructure
    # For now, just log it
    logger.info(f"[STAGE] Version {version_id} staged for review")

    return {
        "success": True,
        "validation": validation_result,
    }


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


async def save_as_memory(
    client,
    user_id: str,
    project_id: str,
    content: str,
    source_type: str = "agent_output",
    tags: Optional[list] = None,
) -> Optional[str]:
    """
    Save content as a project memory.
    """
    memory_data = {
        "user_id": user_id,
        "project_id": project_id,
        "content": content,
        "source_type": source_type,
        "importance": 0.8,
        "tags": tags or [],
    }

    result = client.table("memories").insert(memory_data).execute()

    if result.data:
        return result.data[0]["id"]
    return None


async def update_version_status(client, version_id: str, status: str):
    """Update version status."""
    client.table("deliverable_versions").update({
        "status": status,
    }).eq("id", version_id).execute()

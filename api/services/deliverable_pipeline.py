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
    """
    sources = deliverable.get("sources", [])
    title = deliverable.get("title", "Deliverable")

    # Build gather prompt
    source_descriptions = []
    for source in sources:
        source_type = source.get("type", "description")
        value = source.get("value", "")
        label = source.get("label", "")

        if source_type == "url":
            source_descriptions.append(f"- Web source: {value}")
        elif source_type == "document":
            source_descriptions.append(f"- Document: {label or value}")
        else:
            source_descriptions.append(f"- Context: {value}")

    sources_text = "\n".join(source_descriptions) if source_descriptions else "No specific sources configured"

    gather_prompt = f"""Gather the latest context and information for producing: {title}

Description: {deliverable.get('description', 'No description provided')}

Configured sources:
{sources_text}

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

    # Create work ticket with dependency
    ticket_data = {
        "task": synthesize_prompt,
        "agent_type": "content",
        "project_id": project_id,
        "parameters": json.dumps({
            "deliverable_id": deliverable["id"],
            "step": "synthesize",
        }),
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

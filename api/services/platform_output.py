"""
Platform-Native Output Generators - ADR-031 Phase 2

Generates platform-specific output formats instead of markdown.

Supported formats:
- Slack Block Kit (for slack_digest, slack_update)
- Notion Blocks (for notion_page) [future]

Email HTML rendering moved to compose engine (render/compose.py surface_type="digest").

Usage:
    from services.platform_output import generate_platform_output

    blocks = generate_platform_output(
        platform="slack",
        content=markdown_content,
        variant="slack_digest",
        metadata={"channel_name": "#general"}
    )
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import Optional, Literal

logger = logging.getLogger(__name__)


# =============================================================================
# Slack Block Kit Generator
# =============================================================================

def generate_slack_blocks(
    content: str,
    variant: str = "default",
    metadata: Optional[dict] = None,
) -> list[dict]:
    """
    Convert markdown content to Slack Block Kit format.

    Args:
        content: Markdown-formatted content
        variant: Output variant (slack_digest, slack_update, default)
        metadata: Additional context (channel_name, title, etc.)

    Returns:
        List of Slack Block Kit blocks
    """
    metadata = metadata or {}
    blocks = []

    if variant == "slack_digest":
        blocks = _generate_digest_blocks(content, metadata)
    elif variant == "slack_update":
        blocks = _generate_update_blocks(content, metadata)
    else:
        blocks = _generate_default_blocks(content, metadata)

    return blocks


def _generate_digest_blocks(content: str, metadata: dict) -> list[dict]:
    """
    Generate Slack blocks for a channel digest.

    Structure:
    - Header with date and channel
    - Divider
    - Hot Threads section (if any)
    - Unanswered Questions section (if any)
    - Key Discussions section
    - Action Items section (if any)

    Note: No footer or attribution - user owns the content (ADR-032).
    """
    blocks = []
    title = metadata.get("title", "Channel Digest")
    channel = metadata.get("channel_name", "")
    date_str = datetime.now().strftime("%B %d, %Y")

    # Header
    header_text = f"*{title}*"
    if channel:
        header_text += f"  •  {channel}"
    header_text += f"  •  {date_str}"

    blocks.append({
        "type": "header",
        "text": {"type": "plain_text", "text": title, "emoji": True}
    })

    blocks.append({
        "type": "context",
        "elements": [
            {"type": "mrkdwn", "text": f"📅 {date_str}"},
            {"type": "mrkdwn", "text": f"📢 {channel}" if channel else ""},
        ]
    })

    blocks.append({"type": "divider"})

    # Parse content into sections
    sections = _parse_markdown_sections(content)

    # Process each section
    for section_title, section_content in sections.items():
        if not section_content.strip():
            continue

        # Map section titles to emojis
        emoji_map = {
            "hot threads": "🔥",
            "unanswered questions": "❓",
            "stalled threads": "⏳",
            "action items": "✅",
            "decisions": "📋",
            "key discussions": "💬",
            "highlights": "⭐",
            "summary": "📝",
            "blockers": "🚧",
            "announcements": "📢",
        }

        section_lower = section_title.lower()
        emoji = "•"
        for key, em in emoji_map.items():
            if key in section_lower:
                emoji = em
                break

        # Section header
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{emoji} *{section_title}*"
            }
        })

        # Convert markdown content to mrkdwn
        mrkdwn_content = _markdown_to_mrkdwn(section_content)

        # Split into chunks if too long (Slack limit is 3000 chars per text block)
        chunks = _chunk_text(mrkdwn_content, max_length=2800)

        for chunk in chunks:
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": chunk}
            })

    # ADR-032: No attribution footer - the user is the author
    return blocks


def _generate_update_blocks(content: str, metadata: dict) -> list[dict]:
    """Generate Slack blocks for a general update."""
    blocks = []
    title = metadata.get("title", "Update")

    # Header
    blocks.append({
        "type": "header",
        "text": {"type": "plain_text", "text": title, "emoji": True}
    })

    blocks.append({"type": "divider"})

    # Convert content
    mrkdwn_content = _markdown_to_mrkdwn(content)
    chunks = _chunk_text(mrkdwn_content, max_length=2800)

    for chunk in chunks:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": chunk}
        })

    return blocks


def _generate_default_blocks(content: str, metadata: dict) -> list[dict]:
    """Generate basic Slack blocks from markdown."""
    blocks = []

    mrkdwn_content = _markdown_to_mrkdwn(content)
    chunks = _chunk_text(mrkdwn_content, max_length=2800)

    for chunk in chunks:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": chunk}
        })

    return blocks


def _parse_markdown_sections(content: str) -> dict[str, str]:
    """
    Parse markdown content into sections by headers.

    Returns dict of {section_title: section_content}
    """
    sections = {}
    current_section = "Summary"
    current_content = []

    for line in content.split("\n"):
        # Check for headers (## or ###)
        header_match = re.match(r'^#{1,3}\s+(.+)$', line.strip())
        if header_match:
            # Save previous section
            if current_content:
                sections[current_section] = "\n".join(current_content).strip()
            current_section = header_match.group(1).strip()
            current_content = []
        else:
            current_content.append(line)

    # Save last section
    if current_content:
        sections[current_section] = "\n".join(current_content).strip()

    return sections


def _markdown_to_mrkdwn(content: str) -> str:
    """
    Convert standard markdown to Slack mrkdwn format.

    Key differences:
    - Slack uses single * for bold (not **)
    - Slack uses _ for italic (not * or _)
    - Code blocks work the same (```)
    - Links: [text](url) stays the same
    """
    text = content

    # Convert bold: **text** or __text__ -> *text*
    text = re.sub(r'\*\*(.+?)\*\*', r'*\1*', text)
    text = re.sub(r'__(.+?)__', r'*\1*', text)

    # Convert italic: *text* (single) -> _text_ (only if not already bold)
    # This is tricky because Slack uses * for bold
    # We'll leave single asterisks as-is since we converted ** to *

    # Convert strikethrough: ~~text~~ -> ~text~
    text = re.sub(r'~~(.+?)~~', r'~\1~', text)

    # Convert headers to bold (Slack doesn't have native headers in text)
    text = re.sub(r'^#{1,6}\s+(.+)$', r'*\1*', text, flags=re.MULTILINE)

    # Convert bullet points - Slack supports both - and •
    # Keep as-is, they work

    # Convert numbered lists - Slack doesn't auto-number, keep as-is

    return text


def _chunk_text(text: str, max_length: int = 2800) -> list[str]:
    """
    Split text into chunks that fit within Slack's limits.

    Tries to split at paragraph or sentence boundaries.
    """
    if len(text) <= max_length:
        return [text]

    chunks = []
    current_chunk = ""

    # Split by paragraphs first
    paragraphs = text.split("\n\n")

    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 <= max_length:
            current_chunk += ("\n\n" if current_chunk else "") + para
        else:
            if current_chunk:
                chunks.append(current_chunk)

            # If single paragraph is too long, split by sentences
            if len(para) > max_length:
                sentences = re.split(r'(?<=[.!?])\s+', para)
                current_chunk = ""
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) + 1 <= max_length:
                        current_chunk += (" " if current_chunk else "") + sentence
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = sentence[:max_length]  # Force truncate if needed
            else:
                current_chunk = para

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


# =============================================================================
# Unified Interface
# =============================================================================

def generate_platform_output(
    platform: Literal["slack", "email", "notion", "download"],
    content: str,
    variant: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> dict:
    """
    Generate platform-native output format.

    Args:
        platform: Target platform
        content: Markdown content to convert
        variant: Platform-specific variant (slack_digest, email_summary, etc.)
        metadata: Additional context for generation

    Returns:
        Dict with:
        - format: Output format type ("blocks", "html", "markdown")
        - content: The converted content (blocks list for Slack, HTML string, etc.)
        - raw: Original markdown content
    """
    metadata = metadata or {}

    if platform == "slack":
        blocks = generate_slack_blocks(content, variant or "default", metadata)
        return {
            "format": "blocks",
            "content": blocks,
            "raw": content,
        }

    elif platform == "email":
        # Email HTML composed via render service (surface_type="digest") in delivery.py
        return {
            "format": "markdown",
            "content": content,
            "raw": content,
        }

    elif platform == "notion":
        # TODO: Implement Notion block generation
        return {
            "format": "markdown",
            "content": content,
            "raw": content,
        }

    else:  # download or unknown
        return {
            "format": "markdown",
            "content": content,
            "raw": content,
        }



# Email HTML generation removed — email rendering now handled by compose engine
# (render/compose.py surface_type="digest") called from delivery.py.
# See ADR-148 and the _compose_email_html() function in delivery.py.


# =============================================================================
# Slack Digest Prompt Template
# =============================================================================

SLACK_DIGEST_PROMPT = """You are creating a Slack channel digest for: {channel_name}

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

CONTEXT FROM CHANNEL:
{gathered_context}

{ephemeral_context}

INSTRUCTIONS:
- Be concise but specific - use names and details from context
- If a section has nothing notable, skip it entirely
- Format for Slack: use *bold* for emphasis, bullet points for lists
- Include message timestamps or rough times when referencing discussions
- Prioritize actionable information over general chatter
- If you detect urgency markers or blockers, highlight them prominently

Generate the digest now:"""


def get_slack_digest_prompt(
    channel_name: str,
    gathered_context: str,
    ephemeral_context: str = "",
    time_period: str = "Last 7 days",
) -> str:
    """Get the prompt for generating a Slack digest."""
    return SLACK_DIGEST_PROMPT.format(
        channel_name=channel_name,
        time_period=time_period,
        gathered_context=gathered_context,
        ephemeral_context=ephemeral_context,
    )

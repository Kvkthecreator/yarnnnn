"""
Platform-Native Output Generators - ADR-031 Phase 2

Generates platform-specific output formats instead of markdown.

Supported formats:
- Slack Block Kit (for slack_digest, slack_update)
- Gmail HTML (for email_summary) [future]
- Notion Blocks (for notion_page) [future]

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
    platform: Literal["slack", "gmail", "notion", "download"],
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

    elif platform == "gmail":
        # ADR-031 Phase 5: Gmail HTML generation with variant support
        html = generate_gmail_html(content, variant or "default", metadata)
        return {
            "format": "html",
            "content": html,
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


# =============================================================================
# Gmail HTML Generator - ADR-031 Phase 5
# =============================================================================

def generate_gmail_html(
    content: str,
    variant: str = "default",
    metadata: Optional[dict] = None,
) -> str:
    """
    Convert markdown content to HTML email format.

    Args:
        content: Markdown-formatted content
        variant: Output variant (email_summary, email_draft_reply, etc.)
        metadata: Additional context (subject, recipient, etc.)

    Returns:
        HTML string suitable for Gmail
    """
    metadata = metadata or {}

    if variant == "email_draft_reply":
        return _generate_reply_html(content, metadata)
    elif variant == "email_weekly_digest":
        return _generate_digest_html(content, metadata)
    elif variant == "email_triage":
        return _generate_triage_html(content, metadata)
    else:
        return _generate_default_email_html(content, metadata)


def _generate_default_email_html(content: str, metadata: dict) -> str:
    """Generate standard email HTML with clean styling."""
    body_html = _markdown_to_email_html(content)

    # ADR-032: Content is clean - no attribution that users might forget to remove.
    # The user is the author; YARNNN helps them write.

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            font-size: 14px;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        h1, h2, h3 {{
            color: #1a1a1a;
            margin-top: 1.5em;
            margin-bottom: 0.5em;
        }}
        h1 {{ font-size: 24px; }}
        h2 {{ font-size: 20px; }}
        h3 {{ font-size: 16px; }}
        p {{ margin: 1em 0; }}
        ul, ol {{ padding-left: 20px; }}
        li {{ margin: 0.5em 0; }}
        strong {{ color: #1a1a1a; }}
        a {{ color: #0066cc; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        blockquote {{
            border-left: 3px solid #ddd;
            margin: 1em 0;
            padding-left: 1em;
            color: #666;
        }}
        code {{
            background: #f5f5f5;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 13px;
        }}
    </style>
</head>
<body>
    {body_html}
</body>
</html>"""
    return html


def _generate_reply_html(content: str, metadata: dict) -> str:
    """Generate HTML for email reply - minimal styling, conversation-friendly."""
    body_html = _markdown_to_email_html(content)

    # Replies should be simpler - no heavy wrapper
    html = f"""<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif; font-size: 14px; line-height: 1.6; color: #333;">
{body_html}
</div>"""
    return html


def _generate_digest_html(content: str, metadata: dict) -> str:
    """Generate HTML for weekly digest with section styling."""
    title = metadata.get("title", "Weekly Email Digest")
    body_html = _markdown_to_email_html(content)

    # ADR-032: Content is clean - no attribution that users might forget to remove.

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
            font-size: 14px;
            line-height: 1.6;
            color: #333;
            background: #f9f9f9;
            padding: 20px;
        }}
        .container {{
            max-width: 600px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #eee;
        }}
        .header h1 {{
            margin: 0;
            font-size: 24px;
            color: #1a1a1a;
        }}
        .header .date {{
            color: #888;
            font-size: 14px;
            margin-top: 5px;
        }}
        h2 {{
            font-size: 18px;
            color: #333;
            border-bottom: 1px solid #eee;
            padding-bottom: 8px;
            margin-top: 25px;
        }}
        .urgent {{ color: #dc3545; }}
        .action {{ color: #fd7e14; }}
        .info {{ color: #28a745; }}
        ul {{ padding-left: 20px; }}
        li {{ margin: 8px 0; }}
        .email-item {{
            padding: 10px;
            margin: 8px 0;
            background: #f8f9fa;
            border-radius: 4px;
        }}
        .email-item .sender {{ font-weight: 600; color: #1a1a1a; }}
        .email-item .subject {{ color: #666; }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            font-size: 12px;
            color: #888;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{title}</h1>
            <div class="date">{metadata.get('date', '')}</div>
        </div>
        {body_html}
    </div>
</body>
</html>"""
    return html


def _generate_triage_html(content: str, metadata: dict) -> str:
    """Generate HTML for email triage with category badges."""
    title = metadata.get("title", "Email Triage")
    body_html = _markdown_to_email_html(content)

    # Add category styling
    body_html = body_html.replace("🔴", '<span style="color: #dc3545;">🔴</span>')
    body_html = body_html.replace("🟡", '<span style="color: #ffc107;">🟡</span>')
    body_html = body_html.replace("🟢", '<span style="color: #28a745;">🟢</span>')
    body_html = body_html.replace("📁", '<span style="color: #6c757d;">📁</span>')
    body_html = body_html.replace("🗑️", '<span style="color: #adb5bd;">🗑️</span>')

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
            font-size: 14px;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        h1 {{ font-size: 22px; color: #1a1a1a; margin-bottom: 5px; }}
        h3 {{ font-size: 16px; margin-top: 20px; padding: 8px; background: #f8f9fa; border-radius: 4px; }}
        ul {{ padding-left: 20px; }}
        li {{ margin: 6px 0; }}
        .respond-today {{ border-left: 3px solid #dc3545; padding-left: 10px; }}
        .respond-week {{ border-left: 3px solid #ffc107; padding-left: 10px; }}
        .fyi {{ border-left: 3px solid #28a745; padding-left: 10px; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <p style="color: #666; margin-bottom: 20px;">{metadata.get('email_count', '')} emails triaged</p>
    {body_html}
</body>
</html>"""
    return html


def _markdown_to_email_html(content: str) -> str:
    """Convert markdown to email-safe HTML."""
    html = content

    # Headers with emoji preservation
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)

    # Bold and italic
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<em>\1</em>', html)

    # Strikethrough
    html = re.sub(r'~~(.+?)~~', r'<del>\1</del>', html)

    # Inline code
    html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)

    # Links
    html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', html)

    # Blockquotes
    html = re.sub(r'^> (.+)$', r'<blockquote>\1</blockquote>', html, flags=re.MULTILINE)

    # Lists - handle bullet points
    lines = html.split('\n')
    in_list = False
    result_lines = []

    for line in lines:
        if line.strip().startswith('- '):
            if not in_list:
                result_lines.append('<ul>')
                in_list = True
            item_content = line.strip()[2:]
            result_lines.append(f'<li>{item_content}</li>')
        else:
            if in_list:
                result_lines.append('</ul>')
                in_list = False
            result_lines.append(line)

    if in_list:
        result_lines.append('</ul>')

    html = '\n'.join(result_lines)

    # Paragraphs - split on double newlines
    paragraphs = html.split('\n\n')
    formatted_paragraphs = []
    for p in paragraphs:
        p = p.strip()
        if p and not p.startswith('<'):
            # Only wrap if not already HTML
            if not any(p.startswith(tag) for tag in ['<h1', '<h2', '<h3', '<ul', '<ol', '<blockquote', '<div']):
                p = f'<p>{p}</p>'
        formatted_paragraphs.append(p)

    html = '\n'.join(formatted_paragraphs)

    # Clean up stray newlines within tags
    html = re.sub(r'\n(?=</)', '', html)

    return html


def _markdown_to_basic_html(content: str) -> str:
    """Convert markdown to basic HTML for email (legacy function)."""
    return _markdown_to_email_html(content)


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

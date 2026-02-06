"""
Style Learning Agent - Extract communication style from user's content.

This agent analyzes user-authored content from external platforms (Slack, Notion)
and produces a style profile that can be applied to deliverable generation.

See ADR-027: Integration Read Architecture - Phase 5

Key principle: Style is context-dependent. The same user writes differently in:
- Slack: casual, brief, emoji-friendly
- Notion: structured, thorough, documentation-style
- Email: professional, warm opening/closing

Each platform produces a separate style memory, tagged appropriately.
"""

import json
import logging
from dataclasses import dataclass
from typing import Optional

from anthropic import Anthropic

logger = logging.getLogger(__name__)


@dataclass
class StyleProfile:
    """Extracted communication style profile."""
    platform: str  # slack, notion, email, etc.
    context: str  # realtime_chat, documentation, formal_comms

    # Core style attributes
    tone: str  # formal, casual, professional, friendly
    verbosity: str  # concise, moderate, detailed
    structure: str  # bullets, paragraphs, mixed, headers

    # Detailed patterns
    vocabulary_notes: str  # e.g., "avoids jargon", "uses technical terms"
    sentence_style: str  # e.g., "short declarative", "complex with clauses"
    common_phrases: list[str]  # signature phrases, greetings, signoffs
    emoji_usage: str  # never, minimal, moderate, frequent
    formatting_preferences: str  # markdown, plain, rich formatting

    # Raw profile for prompt injection
    full_profile: str  # Complete style description for system prompts

    # Metadata
    sample_size: int  # Number of messages/blocks analyzed
    confidence: str  # high, medium, low


class StyleLearningAgent:
    """
    Agent that extracts communication style from user-authored content.

    Produces user-scoped memories (project_id = NULL) with style profiles
    that can be loaded during deliverable generation.

    Usage:
        agent = StyleLearningAgent()
        profile = await agent.analyze_slack_messages(messages, user_name)
        # Store profile.full_profile as memory content
    """

    SYSTEM_PROMPT = """You are a communication style analyst for YARNNN, a platform that helps users create recurring deliverables.

Your job is to analyze a user's writing samples and extract their unique communication style. This profile will be used to make AI-generated content sound like the user wrote it.

## Analysis Framework

Analyze the following dimensions:

1. **Tone** (formal, casual, professional, friendly, direct, diplomatic)
   - How do they address others?
   - What's the overall emotional register?

2. **Verbosity** (concise, moderate, detailed)
   - Do they use short punchy messages or elaborate explanations?
   - How much context do they provide?

3. **Structure** (bullets, paragraphs, mixed, headers)
   - How do they organize information?
   - Do they use lists, headers, or flowing prose?

4. **Vocabulary Patterns**
   - Technical vs. plain language
   - Industry jargon usage
   - Common substitutions (e.g., "folks" vs "team", "sync" vs "meeting")

5. **Sentence Style**
   - Short declarative vs. complex with clauses
   - Active vs. passive voice preference
   - Question usage

6. **Signature Patterns**
   - Common greetings/openings
   - Common closings/signoffs
   - Transition phrases
   - Filler words or phrases

7. **Emoji/Formatting**
   - Emoji frequency and types
   - Bold, italic, code block usage
   - Markdown vs. plain text

## Output Format

Return a JSON object with this structure:
```json
{
  "tone": "casual|formal|professional|friendly|direct",
  "verbosity": "concise|moderate|detailed",
  "structure": "bullets|paragraphs|mixed|headers",
  "vocabulary_notes": "Brief description of vocabulary patterns",
  "sentence_style": "Description of typical sentence structure",
  "common_phrases": ["phrase1", "phrase2", "phrase3"],
  "emoji_usage": "never|minimal|moderate|frequent",
  "formatting_preferences": "Description of formatting style",
  "full_profile": "A 2-3 paragraph description of this person's writing style that could be given to an AI to mimic their voice. Be specific and actionable.",
  "confidence": "high|medium|low",
  "confidence_reason": "Brief explanation of confidence level"
}
```

## Guidelines

- Be specific. "Uses short sentences" is better than "writes casually"
- Quote actual phrases when possible
- Note what they DON'T do as well as what they DO
- Consider the platform context (Slack is naturally more casual than documentation)
- If sample size is small, note lower confidence
- Focus on patterns that appear multiple times, not one-off exceptions
"""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize with Anthropic API key."""
        import os
        self.client = Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))

    async def analyze_slack_messages(
        self,
        messages: list[dict],
        user_name: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> StyleProfile:
        """
        Analyze Slack messages to extract communication style.

        Args:
            messages: Raw messages from Slack (should be filtered to user's messages)
            user_name: Display name for context
            user_id: Slack user ID to filter messages (if not pre-filtered)

        Returns:
            StyleProfile with extracted patterns
        """
        # Filter to user's messages if user_id provided
        if user_id:
            messages = [m for m in messages if m.get("user") == user_id]

        if len(messages) < 5:
            raise ValueError("Need at least 5 messages to analyze style")

        # Format messages for analysis
        formatted = self._format_slack_messages(messages)

        user_prompt = f"""## Context
Platform: Slack (real-time team chat)
User: {user_name or "Unknown"}
Sample size: {len(messages)} messages

## Writing Samples
{formatted}

Analyze this user's communication style on Slack. Remember that Slack naturally encourages casual, brief communication - note what's distinctive about THIS user's style within that context."""

        result = await self._execute(user_prompt)

        return StyleProfile(
            platform="slack",
            context="realtime_chat",
            tone=result.get("tone", "casual"),
            verbosity=result.get("verbosity", "concise"),
            structure=result.get("structure", "mixed"),
            vocabulary_notes=result.get("vocabulary_notes", ""),
            sentence_style=result.get("sentence_style", ""),
            common_phrases=result.get("common_phrases", []),
            emoji_usage=result.get("emoji_usage", "minimal"),
            formatting_preferences=result.get("formatting_preferences", ""),
            full_profile=result.get("full_profile", ""),
            sample_size=len(messages),
            confidence=result.get("confidence", "medium"),
        )

    async def analyze_notion_content(
        self,
        pages: list[dict],
        user_name: Optional[str] = None,
    ) -> StyleProfile:
        """
        Analyze Notion pages to extract documentation style.

        Args:
            pages: List of page content dicts with 'title' and 'content' keys
            user_name: Display name for context

        Returns:
            StyleProfile with extracted patterns
        """
        if len(pages) < 1:
            raise ValueError("Need at least 1 page to analyze style")

        # Format pages for analysis
        formatted = self._format_notion_pages(pages)

        total_blocks = sum(len(p.get("blocks", [])) for p in pages)

        user_prompt = f"""## Context
Platform: Notion (documentation and knowledge management)
User: {user_name or "Unknown"}
Sample size: {len(pages)} pages, approximately {total_blocks} content blocks

## Writing Samples
{formatted}

Analyze this user's documentation style in Notion. Note that Notion encourages structured, organized content - identify what's distinctive about THIS user's approach within that context."""

        result = await self._execute(user_prompt)

        return StyleProfile(
            platform="notion",
            context="documentation",
            tone=result.get("tone", "professional"),
            verbosity=result.get("verbosity", "detailed"),
            structure=result.get("structure", "headers"),
            vocabulary_notes=result.get("vocabulary_notes", ""),
            sentence_style=result.get("sentence_style", ""),
            common_phrases=result.get("common_phrases", []),
            emoji_usage=result.get("emoji_usage", "never"),
            formatting_preferences=result.get("formatting_preferences", ""),
            full_profile=result.get("full_profile", ""),
            sample_size=len(pages),
            confidence=result.get("confidence", "medium"),
        )

    async def _execute(self, user_prompt: str) -> dict:
        """Execute the agent and parse results."""
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                system=self.SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}]
            )

            # Extract text content
            content = response.content[0].text

            # Parse JSON response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            result = json.loads(content.strip())

            logger.info(
                f"[STYLE_LEARNING] Extracted style profile: "
                f"tone={result.get('tone')}, confidence={result.get('confidence')}"
            )

            return result

        except json.JSONDecodeError as e:
            logger.error(f"[STYLE_LEARNING] Failed to parse response: {e}")
            raise ValueError(f"Agent returned invalid JSON: {e}")
        except Exception as e:
            logger.error(f"[STYLE_LEARNING] Execution failed: {e}")
            raise

    def _format_slack_messages(self, messages: list[dict]) -> str:
        """Format Slack messages for the prompt."""
        lines = []

        for msg in messages[:50]:  # Limit to 50 messages for context window
            text = msg.get("text", "")
            if not text or len(text) < 10:  # Skip very short messages
                continue

            # Clean up Slack formatting
            text = text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")

            lines.append(f"- {text}")

        return "\n".join(lines)

    def _format_notion_pages(self, pages: list[dict]) -> str:
        """Format Notion pages for the prompt."""
        lines = []

        for page in pages[:10]:  # Limit to 10 pages
            title = page.get("title", "Untitled")
            content = page.get("content", "")

            # Truncate very long content
            if len(content) > 2000:
                content = content[:2000] + "... [truncated]"

            lines.append(f"### {title}\n{content}\n")

        return "\n".join(lines)


def style_profile_to_memory_content(profile: StyleProfile) -> str:
    """
    Convert a StyleProfile to memory content string.

    This is what gets stored in the memories table and loaded
    into deliverable generation prompts.
    """
    return f"""## Communication Style Profile ({profile.platform.title()})

**Context**: {profile.context.replace("_", " ").title()}
**Confidence**: {profile.confidence} (based on {profile.sample_size} samples)

### Core Attributes
- **Tone**: {profile.tone}
- **Verbosity**: {profile.verbosity}
- **Structure**: {profile.structure}
- **Emoji Usage**: {profile.emoji_usage}

### Detailed Profile
{profile.full_profile}

### Vocabulary & Patterns
{profile.vocabulary_notes}

**Sentence Style**: {profile.sentence_style}

**Common Phrases**: {", ".join(profile.common_phrases) if profile.common_phrases else "None identified"}

**Formatting**: {profile.formatting_preferences}"""


def style_profile_to_source_ref(profile: StyleProfile) -> dict:
    """
    Create source_ref JSONB for a style memory.
    """
    return {
        "analysis_type": "style",
        "platform": profile.platform,
        "context": profile.context,
        "sample_size": profile.sample_size,
        "confidence": profile.confidence,
        "attributes": {
            "tone": profile.tone,
            "verbosity": profile.verbosity,
            "structure": profile.structure,
            "emoji_usage": profile.emoji_usage,
        }
    }

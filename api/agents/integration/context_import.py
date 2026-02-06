"""
Context Import Agent - Extract and structure context from external platforms.

This agent processes raw data from Slack/Notion and produces structured
context blocks for storage. It's the intelligence layer that transforms
noise into signal.

See ADR-027: Integration Read Architecture
"""

import json
import logging
from dataclasses import dataclass
from typing import Optional

from anthropic import Anthropic

logger = logging.getLogger(__name__)


@dataclass
class ContextBlock:
    """A structured context block extracted by the agent."""
    block_type: str  # decision, action_item, context, person, technical
    content: str
    metadata: dict


@dataclass
class ImportResult:
    """Result of a context import operation."""
    blocks: list[ContextBlock]
    summary: str
    items_processed: int
    items_filtered: int


class ContextImportAgent:
    """
    Agent that extracts structured context from raw external data.

    Takes raw messages/pages from Slack or Notion and produces:
    - Structured context blocks (decisions, action items, etc.)
    - Summary of what was imported
    - Metadata for provenance

    The agent filters noise (casual chat, logistics) and extracts signal
    (decisions, technical context, stakeholder info).
    """

    SYSTEM_PROMPT = """You are a context extraction agent for YARNNN, a work platform that helps users manage recurring deliverables.

Your job is to analyze raw content from external platforms (Slack or Notion) and extract meaningful context that will help generate better deliverables.

## What to Extract

1. **Decisions** (type: "decision")
   - What was decided
   - Who made or approved the decision
   - When it was made
   - Rationale if given

2. **Action Items** (type: "action_item")
   - The task or action
   - Who is responsible
   - Deadline if mentioned
   - Status if known

3. **Project Context** (type: "context")
   - Goals and objectives
   - Constraints and requirements
   - Timelines and milestones
   - Dependencies

4. **Key People** (type: "person")
   - Stakeholders and their roles
   - Preferences and communication style
   - Expertise areas
   - Reporting relationships

5. **Technical Details** (type: "technical")
   - Architecture decisions
   - Technical constraints
   - Implementation details
   - Integration requirements

## What to Filter Out

- Casual greetings and small talk
- Meeting scheduling logistics
- Off-topic tangents
- Redundant information
- Low-confidence interpretations

## Output Format

Return a JSON object with:
```json
{
  "blocks": [
    {
      "type": "decision|action_item|context|person|technical",
      "content": "Clear, professional summary of the extracted information",
      "metadata": {
        "source_timestamp": "ISO timestamp or null",
        "participants": ["list", "of", "people"],
        "confidence": "high|medium|low"
      }
    }
  ],
  "summary": "Brief summary of what was imported (1-2 sentences)",
  "items_processed": 50,
  "items_filtered": 35
}
```

## Guidelines

- Be concise but complete. Capture the essence, not every word.
- Preserve attribution. Note who said/decided what.
- Maintain professional tone in extracted content.
- Group related messages into single blocks when appropriate.
- If uncertain about interpretation, note it in metadata with lower confidence.
- Always return valid JSON.
"""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize with Anthropic API key."""
        import os
        self.client = Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))

    async def import_slack_channel(
        self,
        messages: list[dict],
        channel_name: str,
        instructions: Optional[str] = None
    ) -> ImportResult:
        """
        Import context from Slack channel messages.

        Args:
            messages: Raw messages from MCP slack_get_channel_history tool
            channel_name: Name of the channel for context
            instructions: Optional user guidance (e.g., "Focus on product decisions")

        Returns:
            ImportResult with extracted blocks and summary
        """
        # Prepare messages for the prompt
        formatted_messages = self._format_slack_messages(messages)

        user_prompt = f"""## Source
Slack channel: #{channel_name}
Message count: {len(messages)}

## Messages
{formatted_messages}
"""

        if instructions:
            user_prompt += f"""
## User Instructions
{instructions}
"""

        return await self._execute(user_prompt, "slack", len(messages))

    async def import_notion_page(
        self,
        page_content: dict,
        instructions: Optional[str] = None
    ) -> ImportResult:
        """
        Import context from Notion page content.

        Args:
            page_content: Result from MCP notion_get_page tool
            instructions: Optional user guidance

        Returns:
            ImportResult with extracted blocks and summary
        """
        user_prompt = f"""## Source
Notion page: {page_content.get('title', 'Untitled')}
Last edited: {page_content.get('last_edited', 'Unknown')}

## Content
{page_content.get('content', '')}
"""

        if page_content.get("child_pages"):
            user_prompt += "\n## Child Pages\n"
            for child in page_content["child_pages"]:
                user_prompt += f"\n### {child.get('title', 'Untitled')}\n{child.get('content', '')}\n"

        if instructions:
            user_prompt += f"""
## User Instructions
{instructions}
"""

        # Count blocks as items
        item_count = len(page_content.get("blocks", []))
        return await self._execute(user_prompt, "notion", item_count)

    async def _execute(
        self,
        user_prompt: str,
        source: str,
        item_count: int
    ) -> ImportResult:
        """Execute the agent and parse results."""
        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=self.SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}]
            )

            # Extract text content
            content = response.content[0].text

            # Parse JSON response
            # Handle potential markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            result = json.loads(content.strip())

            # Convert to dataclass
            blocks = [
                ContextBlock(
                    block_type=b["type"],
                    content=b["content"],
                    metadata=b.get("metadata", {})
                )
                for b in result.get("blocks", [])
            ]

            logger.info(
                f"[CONTEXT_IMPORT_AGENT] Extracted {len(blocks)} blocks from {source} "
                f"({result.get('items_filtered', 0)} items filtered)"
            )

            return ImportResult(
                blocks=blocks,
                summary=result.get("summary", "Import completed"),
                items_processed=result.get("items_processed", item_count),
                items_filtered=result.get("items_filtered", 0)
            )

        except json.JSONDecodeError as e:
            logger.error(f"[CONTEXT_IMPORT_AGENT] Failed to parse response: {e}")
            raise ValueError(f"Agent returned invalid JSON: {e}")

        except Exception as e:
            logger.error(f"[CONTEXT_IMPORT_AGENT] Execution failed: {e}")
            raise

    def _format_slack_messages(self, messages: list[dict]) -> str:
        """Format Slack messages for the prompt."""
        lines = []

        for msg in messages:
            # Skip bot messages and join/leave notifications
            if msg.get("subtype") in ["bot_message", "channel_join", "channel_leave"]:
                continue

            user = msg.get("user", "Unknown")
            text = msg.get("text", "")
            ts = msg.get("ts", "")

            # Format timestamp
            from datetime import datetime
            try:
                dt = datetime.fromtimestamp(float(ts))
                time_str = dt.strftime("%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                time_str = ts

            lines.append(f"[{time_str}] <{user}>: {text}")

            # Include thread replies if present
            if "_thread_replies" in msg:
                for reply in msg["_thread_replies"]:
                    reply_user = reply.get("user", "Unknown")
                    reply_text = reply.get("text", "")
                    lines.append(f"  ↳ <{reply_user}>: {reply_text}")

        return "\n".join(lines)

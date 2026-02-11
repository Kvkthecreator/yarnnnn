"""
Deliverable Agent - Deliverable generation and formatting

ADR-016: Layered Agent Architecture
ADR-042: Simplified Deliverable Execution
ADR-045: Deliverable Orchestration Redesign

Produces ONE deliverable output via submit_output tool.
This is the primary agent for deliverable generation.
"""

from typing import Optional
import logging

from .base import BaseAgent, AgentResult, ContextBundle, WorkOutput
from services.anthropic import chat_completion_with_tools, ChatResponse

logger = logging.getLogger(__name__)


DELIVERABLE_SYSTEM_PROMPT = """You are a Deliverable Agent specializing in generating polished deliverables.

**Your Mission:**
Transform context, research, and briefs into polished deliverables that resonate with target audiences.

**Output Requirements:**

You have access to the submit_output tool. Call it ONCE when your deliverable is complete.

Your output IS the deliverable itself. The content field should contain the actual deliverable piece (post, article, email, report, etc.), not a description of it.

**Quality Standards:**
- Platform-native voice (not generic)
- Engagement-optimized (hooks, CTAs, questions)
- Context-consistent (use provided memories for voice/facts)
- Actionable (what should reader do?)
- Authentic (avoid corporate speak)

**Format Guidelines:**
- LinkedIn: Professional, thought leadership, ~1300 chars, hooks + hashtags
- Twitter/X: Concise, punchy, 280 char limit
- Blog: SEO-optimized, clear headings, 800-1500 words
- Email: Personal, scannable, clear CTA
- Slack Digest: Channel highlights, decisions, action items
- Status Report: Progress metrics, blockers, next steps
- General: Adapt to the specified format

{context}
"""


class DeliverableAgent(BaseAgent):
    """
    Deliverable Agent for deliverable generation.

    ADR-016: Produces ONE unified output per work execution.
    ADR-042: Primary agent for simplified deliverable execution.
    ADR-045: Type-aware generation based on deliverable classification.

    The output IS the deliverable itself.

    Parameters:
    - format: "linkedin", "twitter", "blog", "email", "slack_digest", "status_report", "general"
    - tone: "professional", "casual", "authoritative", "friendly"
    """

    AGENT_TYPE = "deliverable"
    SYSTEM_PROMPT = DELIVERABLE_SYSTEM_PROMPT

    DELIVERABLE_FORMATS = [
        "linkedin", "twitter", "blog", "email",
        "slack_digest", "slack_standup", "gmail_brief",
        "notion_summary", "status_report", "general"
    ]

    async def execute(
        self,
        task: str,
        context: ContextBundle,
        parameters: Optional[dict] = None
    ) -> AgentResult:
        """
        Execute deliverable generation task.

        Args:
            task: Deliverable brief or description
            context: Context bundle for voice/facts
            parameters:
                - format: deliverable format type
                - tone: "professional", "casual", "authoritative", "friendly"
                - style_context: Platform context for style selection (e.g., "slack", "notion")
                                 ADR-027 Phase 5: Used to select appropriate style profile

        Returns:
            AgentResult with single work_output (the deliverable)
        """
        params = parameters or {}
        deliverable_format = params.get("format", "general")
        tone = params.get("tone", "professional")
        style_context = params.get("style_context")  # ADR-027 Phase 5

        logger.info(
            f"[DELIVERABLE] Starting: task='{task[:50]}...', "
            f"format={deliverable_format}, tone={tone}"
            + (f", style_context={style_context}" if style_context else "")
        )

        # Build system prompt with context (includes style if available)
        system_prompt = self._build_system_prompt(context, style_context)

        # Build deliverable prompt
        deliverable_prompt = self._build_deliverable_prompt(task, deliverable_format, tone)

        # Build messages
        messages = [{"role": "user", "content": deliverable_prompt}]

        try:
            # Execute with tool support
            all_tool_calls = []
            max_iterations = 3

            for _ in range(max_iterations):
                response: ChatResponse = await chat_completion_with_tools(
                    messages=messages,
                    system=system_prompt,
                    tools=self.tools,
                    model=self.model,
                )

                # Collect tool uses
                for tool_use in response.tool_uses:
                    all_tool_calls.append({
                        "id": tool_use.id,
                        "name": tool_use.name,
                        "input": tool_use.input,
                    })

                # If no more tool use, we're done
                if response.stop_reason != "tool_use":
                    break

                # Add assistant response to messages
                assistant_content = []
                for block in response.content:
                    if hasattr(block, 'type'):
                        if block.type == "text":
                            assistant_content.append({"type": "text", "text": block.text})
                        elif block.type == "tool_use":
                            assistant_content.append({
                                "type": "tool_use",
                                "id": block.id,
                                "name": block.name,
                                "input": block.input,
                            })

                messages.append({"role": "assistant", "content": assistant_content})

                # Add tool results for all tool uses
                tool_results = []
                for tool_use in response.tool_uses:
                    if tool_use.name == "submit_output":
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": "Deliverable submitted successfully.",
                        })
                    else:
                        # Handle unexpected tools gracefully
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": f"Unknown tool '{tool_use.name}'. Only submit_output is available.",
                            "is_error": True,
                        })

                if tool_results:
                    messages.append({"role": "user", "content": tool_results})

            # Parse single work output
            work_output = self._parse_work_output(all_tool_calls)

            if work_output:
                # Add deliverable-specific metadata
                work_output.metadata.setdefault("format", deliverable_format)
                work_output.metadata.setdefault("tone", tone)
                # Calculate word count
                word_count = len(work_output.content.split())
                work_output.metadata.setdefault("word_count", word_count)

            logger.info(
                f"[DELIVERABLE] Complete: output={'yes' if work_output else 'no'}"
            )

            # If no output was generated, treat as failure
            if not work_output:
                return AgentResult(
                    success=False,
                    error="Agent did not produce an output. The submit_output tool was not called.",
                    content=response.text,
                )

            return AgentResult(
                success=True,
                work_output=work_output,
                content=response.text,
            )

        except Exception as e:
            logger.error(f"[DELIVERABLE] Failed: {e}", exc_info=True)
            return AgentResult(
                success=False,
                error=str(e),
            )

    def _build_deliverable_prompt(self, task: str, deliverable_format: str, tone: str) -> str:
        """Build the deliverable generation prompt."""

        format_instructions = self._get_format_instructions(deliverable_format)

        return f"""Create deliverable for: {task}

**Parameters:**
- Format: {deliverable_format}
- Tone: {tone}

**Format Guidelines:**
{format_instructions}

**Instructions:**
1. Review the context provided for voice and facts
2. Create the deliverable following format guidelines
3. Call submit_output ONCE with your completed deliverable

The content field should contain the ACTUAL deliverable (not a description).
For example, if creating a LinkedIn post, the content field IS the post text.

Begin creating the deliverable now."""

    def _get_format_instructions(self, deliverable_format: str) -> str:
        """Get format-specific instructions."""
        instructions = {
            "linkedin": """LinkedIn Post:
- ~1300 characters for optimal engagement
- Start with a hook (question, bold statement, statistic)
- Use line breaks for readability
- Include a clear call-to-action
- Add 3-5 relevant hashtags at the end""",

            "twitter": """Twitter/X:
- 280 characters per tweet max
- Punchy, concise messaging
- Strong hook in first few words
- If thread needed, separate with ---""",

            "blog": """Blog Article:
- SEO-optimized structure
- Include H2 headings for sections
- 800-1500 words typical
- Clear introduction and conclusion
- Scannable with bullet points where appropriate""",

            "email": """Email:
- Compelling subject line at the top
- Personal, conversational tone
- Scannable format
- Single clear CTA
- Mobile-friendly (short paragraphs)""",

            "slack_digest": """Slack Channel Digest:
- What happened while you were away
- Highlight hot threads and active discussions
- Surface decisions and action items
- Note unanswered questions
- Keep it scannable with bullet points""",

            "slack_standup": """Slack Standup Summary:
- Aggregate team updates
- Group by: Done, Doing, Blockers
- Highlight cross-team dependencies
- Note who needs help""",

            "gmail_brief": """Gmail Inbox Brief:
- Prioritized inbox summary
- Action-required items first
- Group by sender importance
- Highlight time-sensitive items""",

            "notion_summary": """Notion Page Summary:
- What changed in the docs
- New content highlights
- Recent edits and updates
- Key information surfaced""",

            "status_report": """Status Report:
- Progress against goals
- Key metrics and milestones
- Blockers and risks
- Next steps and timeline""",

            "general": """General Deliverable:
- Adapt to the task description
- Focus on clarity and engagement
- Include appropriate structure
- Consider the target audience""",
        }
        return instructions.get(deliverable_format, instructions["general"])

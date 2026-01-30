"""
Content Agent - Content creation

ADR-016: Layered Agent Architecture
Produces ONE content piece via submit_output tool.
"""

from typing import Optional
import logging

from .base import BaseAgent, AgentResult, ContextBundle, WorkOutput
from services.anthropic import chat_completion_with_tools, ChatResponse

logger = logging.getLogger(__name__)


CONTENT_SYSTEM_PROMPT = """You are a Content Agent specializing in creating compelling content.

**Your Mission:**
Transform context, research, and briefs into polished content that resonates with target audiences.

**Output Requirements:**

You have access to the submit_output tool. Call it ONCE when your content is complete.

Your output IS the content itself. The content field should contain the actual content piece (post, article, email, etc.), not a description of it.

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
- General: Adapt to the specified format

{context}
"""


class ContentAgent(BaseAgent):
    """
    Content Agent for content creation.

    ADR-016: Produces ONE unified output per work execution.
    The output IS the content itself.

    Parameters:
    - format: "linkedin", "twitter", "blog", "email", "general"
    - tone: "professional", "casual", "authoritative", "friendly"
    """

    AGENT_TYPE = "content"
    SYSTEM_PROMPT = CONTENT_SYSTEM_PROMPT

    CONTENT_FORMATS = ["linkedin", "twitter", "blog", "email", "general"]

    async def execute(
        self,
        task: str,
        context: ContextBundle,
        parameters: Optional[dict] = None
    ) -> AgentResult:
        """
        Execute content creation task.

        Args:
            task: Content brief or description
            context: Context bundle for voice/facts
            parameters:
                - format: "linkedin", "twitter", "blog", "email", "general"
                - tone: "professional", "casual", "authoritative", "friendly"

        Returns:
            AgentResult with single work_output (the content)
        """
        params = parameters or {}
        content_format = params.get("format", "general")
        tone = params.get("tone", "professional")

        logger.info(
            f"[CONTENT] Starting: task='{task[:50]}...', "
            f"format={content_format}, tone={tone}"
        )

        # Build system prompt with context
        system_prompt = self._build_system_prompt(context)

        # Build content prompt
        content_prompt = self._build_content_prompt(task, content_format, tone)

        # Build messages
        messages = [{"role": "user", "content": content_prompt}]

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
                            "content": "Content submitted successfully.",
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
                # Add content-specific metadata
                work_output.metadata.setdefault("format", content_format)
                work_output.metadata.setdefault("tone", tone)
                # Calculate word count
                word_count = len(work_output.content.split())
                work_output.metadata.setdefault("word_count", word_count)

            logger.info(
                f"[CONTENT] Complete: output={'yes' if work_output else 'no'}"
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
            logger.error(f"[CONTENT] Failed: {e}", exc_info=True)
            return AgentResult(
                success=False,
                error=str(e),
            )

    def _build_content_prompt(self, task: str, content_format: str, tone: str) -> str:
        """Build the content creation prompt."""

        format_instructions = self._get_format_instructions(content_format)

        return f"""Create content for: {task}

**Parameters:**
- Format: {content_format}
- Tone: {tone}

**Format Guidelines:**
{format_instructions}

**Instructions:**
1. Review the context provided for voice and facts
2. Create the content following format guidelines
3. Call submit_output ONCE with your completed content

The content field should contain the ACTUAL content (not a description).
For example, if creating a LinkedIn post, the content field IS the post text.

Begin creating content now."""

    def _get_format_instructions(self, content_format: str) -> str:
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

            "general": """General Content:
- Adapt to the task description
- Focus on clarity and engagement
- Include appropriate structure
- Consider the target audience""",
        }
        return instructions.get(content_format, instructions["general"])

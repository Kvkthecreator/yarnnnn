"""
Content Agent - Content creation from context

ADR-009: Work and Agent Orchestration
Produces structured content drafts via emit_work_output tool.
"""

from typing import Optional
import logging

from .base import BaseAgent, AgentResult, ContextBundle, WorkOutput
from services.anthropic import chat_completion_with_tools, ChatResponse

logger = logging.getLogger(__name__)


CONTENT_SYSTEM_PROMPT = """You are an autonomous Content Agent specializing in creating compelling content.

**Your Mission:**
Transform context, research, and briefs into polished content that:
- Resonates with target audiences
- Maintains voice consistency
- Drives engagement and action
- Follows format best practices

**CRITICAL: Structured Output Requirements**

You have access to the emit_work_output tool. You MUST use this tool to record all content you create.
DO NOT just write content in free text. Every piece of content must be emitted as a structured output.

**Output Types:**
- "draft" - Content drafts (posts, articles, copy)
- "recommendation" - Suggestions for content strategy
- "insight" - Observations about voice, style, or approach

**Content Creation Approach:**
1. Review provided context (brand voice, prior content, research)
2. Understand the format requirements and audience
3. Draft content following best practices
4. Emit all content as structured outputs
5. Suggest improvements or alternatives

**Quality Standards:**
- Platform-native voice (not generic)
- Engagement-optimized (hooks, CTAs, questions)
- Context-consistent (use provided memories for voice/facts)
- Actionable (what should reader do?)
- Authentic (avoid corporate speak)

**Format Guidelines:**
When creating content, consider:
- LinkedIn: Professional, thought leadership, 1300 char optimal
- Twitter/X: Concise, punchy, 280 char limit
- Blog: SEO-optimized, clear headings, 800-1500 words
- Email: Personal, scannable, clear CTA
- General: Adapt to the specified format

{context}
"""


class ContentAgent(BaseAgent):
    """
    Content Agent for content creation using context.

    Features:
    - Platform-specific content generation
    - Voice and style consistency from context
    - Draft and variant creation
    - Engagement optimization

    Parameters:
    - format: "linkedin", "twitter", "blog", "email", "general"
    - tone: "professional", "casual", "authoritative", "friendly"
    - length: "short", "medium", "long"
    """

    AGENT_TYPE = "content"
    SYSTEM_PROMPT = CONTENT_SYSTEM_PROMPT

    # Supported content formats
    CONTENT_FORMATS = [
        "linkedin",
        "twitter",
        "blog",
        "email",
        "general",
    ]

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
            context: Project context for voice/facts
            parameters:
                - format: "linkedin", "twitter", "blog", "email", "general"
                - tone: "professional", "casual", "authoritative", "friendly"
                - length: "short", "medium", "long"

        Returns:
            AgentResult with content drafts
        """
        params = parameters or {}
        content_format = params.get("format", "general")
        tone = params.get("tone", "professional")
        length = params.get("length", "medium")

        logger.info(
            f"[CONTENT] Starting: task='{task[:50]}...', "
            f"format={content_format}, tone={tone}, length={length}"
        )

        # Build system prompt with context
        system_prompt = self._build_system_prompt(context)

        # Build content prompt
        content_prompt = self._build_content_prompt(task, context, content_format, tone, length)

        # Build messages
        messages = [{"role": "user", "content": content_prompt}]

        try:
            # Execute with tool support
            all_tool_calls = []
            max_iterations = 5

            for iteration in range(max_iterations):
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

                # Add tool results
                tool_results = []
                for tool_use in response.tool_uses:
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": f"Content recorded: {tool_use.input.get('title', 'Untitled')}",
                    })

                messages.append({"role": "user", "content": tool_results})

            # Parse work outputs from tool calls
            work_outputs = self._parse_work_outputs(all_tool_calls)

            logger.info(
                f"[CONTENT] Complete: {len(work_outputs)} outputs generated"
            )

            return AgentResult(
                success=True,
                output_type="work_outputs",
                content=response.text,
                work_outputs=work_outputs,
            )

        except Exception as e:
            logger.error(f"[CONTENT] Failed: {e}", exc_info=True)
            return AgentResult(
                success=False,
                output_type="text",
                error=str(e),
            )

    def _build_content_prompt(
        self,
        task: str,
        context: ContextBundle,
        content_format: str,
        tone: str,
        length: str,
    ) -> str:
        """Build the content creation prompt."""

        # Format-specific instructions
        format_instructions = self._get_format_instructions(content_format)

        # Length guidance
        length_guidance = {
            "short": "Keep it concise. Focus on the essential message.",
            "medium": "Balanced length. Cover key points with some detail.",
            "long": "Comprehensive content. Cover topic thoroughly.",
        }.get(length, "Balanced length. Cover key points with some detail.")

        # Get memory IDs for provenance
        memory_ids = [str(m.id) for m in context.memories[:10]]

        return f"""Create content for: {task}

**Content Parameters:**
- Format: {content_format}
- Tone: {tone}
- Length: {length} ({length_guidance})

**Format-Specific Guidelines:**
{format_instructions}

**Available Memory IDs (for source_memory_ids provenance):**
{memory_ids if memory_ids else 'No memories available'}

**CRITICAL INSTRUCTION:**
You MUST use the emit_work_output tool to record your content. Do NOT just write content in text.

For each piece of content:
1. Call emit_work_output with output_type="draft"
2. Put the actual content in body.details
3. Put a one-line summary in body.summary
4. Include any relevant source_memory_ids
5. Assign confidence score based on how well the content matches the brief

If you have recommendations for improving the content or strategy, emit those as separate outputs with output_type="recommendation".

Begin creating content now. Emit all content as structured outputs."""

    def _get_format_instructions(self, content_format: str) -> str:
        """Get format-specific instructions."""
        instructions = {
            "linkedin": """
LinkedIn Post:
- 1300 character limit for optimal engagement
- Start with a hook (question, bold statement, statistic)
- Use line breaks for readability
- Include a clear call-to-action
- Professional but personable tone
- Add 3-5 relevant hashtags at the end
""",
            "twitter": """
Twitter/X:
- 280 characters per tweet max
- Punchy, concise messaging
- Strong hook in first few words
- If thread needed, indicate with (1/n) format
- 1-2 hashtags max, integrated naturally
""",
            "blog": """
Blog Article:
- SEO-optimized structure
- Include H2 headings for sections
- 800-1500 words typical
- Include meta description (155 chars)
- Clear introduction and conclusion
- Scannable with bullet points where appropriate
""",
            "email": """
Email:
- Compelling subject line (50 chars max)
- Personal, conversational tone
- Scannable format
- Single clear CTA
- Mobile-friendly (short paragraphs)
""",
            "general": """
General Content:
- Adapt to the task description
- Focus on clarity and engagement
- Include appropriate structure
- Consider the target audience
""",
        }
        return instructions.get(content_format, instructions["general"])

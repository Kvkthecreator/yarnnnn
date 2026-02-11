"""
Synthesizer Agent - Context synthesis and summarization

ADR-016: Layered Agent Architecture
ADR-045: Deliverable Orchestration Redesign

Produces ONE synthesized output via submit_output tool.
Takes pre-fetched context and synthesizes it into a coherent summary.

NOTE: This agent does NOT perform active research or fetching.
Context is gathered by the pipeline before this agent runs.
"""

from typing import Optional
import logging

from .base import BaseAgent, AgentResult, ContextBundle, WorkOutput
from services.anthropic import chat_completion_with_tools, ChatResponse

logger = logging.getLogger(__name__)


SYNTHESIZER_SYSTEM_PROMPT = """You are a Synthesizer Agent specializing in context synthesis and summarization.

**Your Mission:**
Synthesize the provided context into a coherent, well-structured summary. The context has already been gathered from various sources - your job is to make sense of it.

**Output Requirements:**

You have access to the submit_output tool. Call it ONCE when your synthesis is complete.

Your output should be a complete synthesis document in markdown format. You decide the internal structure based on what the task requires. Typical structures include:

- Overview → Key Findings → Analysis → Recommendations
- Executive Summary → Key Points → Details → Next Steps
- Question → Evidence → Conclusions

**Quality Standards:**
- Accuracy over speed
- Evidence-based claims
- Actionable recommendations
- Acknowledge gaps in available information
- Be specific about what you found and why it matters

**Synthesis Approach:**
1. Review provided context (memories, documents, platform data)
2. Analyze and synthesize the information
3. Structure your findings coherently
4. Call submit_output ONCE with your complete synthesis

{context}
"""


class SynthesizerAgent(BaseAgent):
    """
    Synthesizer Agent for context synthesis and summarization.

    ADR-016: Produces ONE unified output per work execution.
    ADR-045: Part of type-aware orchestration pipeline.

    This agent synthesizes pre-fetched context into coherent summaries.
    It does NOT perform active research or web searches.

    Parameters:
    - scope: "general" | "focused" | "comprehensive"
    - depth: "quick" | "standard" | "thorough"
    """

    AGENT_TYPE = "synthesizer"
    SYSTEM_PROMPT = SYNTHESIZER_SYSTEM_PROMPT

    async def execute(
        self,
        task: str,
        context: ContextBundle,
        parameters: Optional[dict] = None
    ) -> AgentResult:
        """
        Execute synthesis task.

        Args:
            task: Synthesis question or topic
            context: Context bundle with pre-fetched data
            parameters:
                - scope: "general", "focused", "comprehensive"
                - depth: "quick", "standard", "thorough"

        Returns:
            AgentResult with single work_output
        """
        params = parameters or {}
        scope = params.get("scope", "general")
        depth = params.get("depth", "standard")

        logger.info(
            f"[SYNTHESIZER] Starting: task='{task[:50]}...', "
            f"scope={scope}, depth={depth}, "
            f"memories={len(context.memories)}"
        )

        # Build system prompt with context
        system_prompt = self._build_system_prompt(context)

        # Build synthesis prompt
        synthesis_prompt = self._build_synthesis_prompt(task, scope, depth)

        # Build messages
        messages = [{"role": "user", "content": synthesis_prompt}]

        try:
            # Execute with tool support - agent calls submit_output once
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
                            "content": "Output submitted successfully.",
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
                # Add synthesis-specific metadata
                work_output.metadata.setdefault("scope", scope)
                work_output.metadata.setdefault("depth", depth)

            logger.info(
                f"[SYNTHESIZER] Complete: output={'yes' if work_output else 'no'}"
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
            logger.error(f"[SYNTHESIZER] Failed: {e}", exc_info=True)
            return AgentResult(
                success=False,
                error=str(e),
            )

    def _build_synthesis_prompt(self, task: str, scope: str, depth: str) -> str:
        """Build the synthesis task prompt."""

        # Scope instructions
        scope_instructions = {
            "general": "Broad analysis covering all relevant aspects.",
            "focused": "Focused analysis on the specific question asked.",
            "comprehensive": "Exhaustive analysis covering all angles and implications.",
        }.get(scope, "Broad analysis covering all relevant aspects.")

        # Depth instructions
        depth_instructions = {
            "quick": "Provide key findings quickly. Keep it concise.",
            "standard": "Provide thorough analysis with appropriate detail.",
            "thorough": "Comprehensive deep-dive covering multiple perspectives.",
        }.get(depth, "Provide thorough analysis with appropriate detail.")

        return f"""Synthesis task: {task}

**Parameters:**
- Scope: {scope} - {scope_instructions}
- Depth: {depth} - {depth_instructions}

**Instructions:**
1. Analyze the context provided for relevant information
2. Synthesize your findings into a coherent document
3. Structure the document appropriately (you decide the structure)
4. Call submit_output ONCE with your complete synthesis

Include in your output:
- Key findings with supporting evidence
- Analysis of patterns and implications
- Recommendations where appropriate
- Note any gaps in available information

Begin your synthesis now."""

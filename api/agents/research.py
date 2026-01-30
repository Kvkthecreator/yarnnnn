"""
Research Agent - Deep investigation and analysis

ADR-016: Layered Agent Architecture
Produces ONE unified research output via submit_output tool.
"""

from typing import Optional
import logging

from .base import BaseAgent, AgentResult, ContextBundle, WorkOutput
from services.anthropic import chat_completion_with_tools, ChatResponse

logger = logging.getLogger(__name__)


RESEARCH_SYSTEM_PROMPT = """You are a Research Agent specializing in investigation and analysis.

**Your Mission:**
Investigate topics using the provided context as your primary source material, synthesizing information into a comprehensive research document.

**Output Requirements:**

You have access to the submit_output tool. Call it ONCE when your research is complete.

Your output should be a complete research document in markdown format. You decide the internal structure based on what the task requires. Typical structures include:

- Overview → Findings → Analysis → Recommendations
- Executive Summary → Key Points → Details → Next Steps
- Question → Evidence → Conclusions

**Quality Standards:**
- Accuracy over speed
- Evidence-based claims
- Actionable recommendations
- Acknowledge gaps in available information
- Be specific about what you found and why it matters

**Research Approach:**
1. Review provided context (user memories, project memories)
2. Analyze and synthesize the information
3. Structure your findings coherently
4. Call submit_output ONCE with your complete research document

{context}
"""


class ResearchAgent(BaseAgent):
    """
    Research Agent for investigation and analysis.

    ADR-016: Produces ONE unified output per work execution.
    Agent determines structure within the markdown content.

    Parameters:
    - scope: "general" | "focused" | "comprehensive"
    - depth: "quick" | "standard" | "thorough"
    """

    AGENT_TYPE = "research"
    SYSTEM_PROMPT = RESEARCH_SYSTEM_PROMPT

    async def execute(
        self,
        task: str,
        context: ContextBundle,
        parameters: Optional[dict] = None
    ) -> AgentResult:
        """
        Execute research task.

        Args:
            task: Research question or topic
            context: Context bundle with memories
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
            f"[RESEARCH] Starting: task='{task[:50]}...', "
            f"scope={scope}, depth={depth}, "
            f"memories={len(context.memories)}"
        )

        # Build system prompt with context
        system_prompt = self._build_system_prompt(context)

        # Build research prompt
        research_prompt = self._build_research_prompt(task, scope, depth)

        # Build messages
        messages = [{"role": "user", "content": research_prompt}]

        try:
            # Execute with tool support - agent calls submit_output once
            all_tool_calls = []
            max_iterations = 3  # Reduced: agent should complete in fewer turns

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

                # Add tool result - acknowledge and stop
                tool_results = []
                for tool_use in response.tool_uses:
                    if tool_use.name == "submit_output":
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": "Output submitted successfully.",
                        })

                messages.append({"role": "user", "content": tool_results})

            # Parse single work output
            work_output = self._parse_work_output(all_tool_calls)

            if work_output:
                # Add research-specific metadata
                work_output.metadata.setdefault("scope", scope)
                work_output.metadata.setdefault("depth", depth)

            logger.info(
                f"[RESEARCH] Complete: output={'yes' if work_output else 'no'}"
            )

            return AgentResult(
                success=True,
                work_output=work_output,
                content=response.text,
            )

        except Exception as e:
            logger.error(f"[RESEARCH] Failed: {e}", exc_info=True)
            return AgentResult(
                success=False,
                error=str(e),
            )

    def _build_research_prompt(self, task: str, scope: str, depth: str) -> str:
        """Build the research task prompt."""

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

        return f"""Research task: {task}

**Parameters:**
- Scope: {scope} - {scope_instructions}
- Depth: {depth} - {depth_instructions}

**Instructions:**
1. Analyze the context provided for relevant information
2. Synthesize your findings into a coherent research document
3. Structure the document appropriately (you decide the structure)
4. Call submit_output ONCE with your complete research

Include in your output:
- Key findings with supporting evidence
- Analysis of patterns and implications
- Recommendations where appropriate
- Note any gaps in available information

Begin your research now."""

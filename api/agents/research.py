"""
Research Agent - Deep investigation using context

ADR-009: Work and Agent Orchestration
Produces structured outputs via emit_work_output tool.
"""

from typing import Optional
import logging

from .base import BaseAgent, AgentResult, ContextBundle, WorkOutput
from services.anthropic import chat_completion_with_tools, ChatResponse

logger = logging.getLogger(__name__)


RESEARCH_SYSTEM_PROMPT = """You are an autonomous Research Agent specializing in intelligence gathering and analysis.

**Your Mission:**
Investigate topics using the provided context as your primary source material, synthesizing information into actionable insights.

**CRITICAL: Structured Output Requirements**

You have access to the emit_work_output tool. You MUST use this tool to record ALL your findings.
DO NOT just describe findings in free text. Every significant finding must be emitted as a structured output.

**Output Types:**
- "finding" - Facts discovered (data points, statements, observations)
- "recommendation" - Suggested actions based on findings
- "insight" - Patterns identified, connections made, implications drawn

**Research Approach:**
1. Review provided context (user memories, project memories)
2. Identify key information relevant to the research task
3. Analyze and synthesize the information
4. For EACH finding: Call emit_work_output with structured data
5. Provide recommendations based on your analysis

**Quality Standards:**
- Accuracy over speed
- Structured over narrative
- Actionable over interesting
- High confidence = high evidence (don't guess)
- Cite specific context when possible

**Important Guidelines:**
- Use the context provided - it contains memories and documents the user has built up
- If context is limited, acknowledge gaps and focus on what IS available
- Always emit at least one output, even if just to summarize what context is available
- Be specific about what you found and why it matters

{context}
"""


class ResearchAgent(BaseAgent):
    """
    Research Agent for intelligence gathering and analysis.

    Features:
    - Deep-dive research with structured outputs
    - Context-aware analysis using user and project memories
    - Configurable scope and depth
    - Provenance tracking (which memories informed findings)

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
            context: Project context to analyze
            parameters:
                - scope: "general", "focused", "comprehensive" (default: general)
                - depth: "quick", "standard", "thorough" (default: standard)

        Returns:
            AgentResult with work_outputs list
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
        research_prompt = self._build_research_prompt(task, context, scope, depth)

        # Build messages
        messages = [{"role": "user", "content": research_prompt}]

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

                # Add tool results (acknowledge receipt)
                tool_results = []
                for tool_use in response.tool_uses:
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use.id,
                        "content": f"Output recorded: {tool_use.input.get('title', 'Untitled')}",
                    })

                messages.append({"role": "user", "content": tool_results})

            # Parse work outputs from tool calls
            work_outputs = self._parse_work_outputs(all_tool_calls)

            logger.info(
                f"[RESEARCH] Complete: {len(work_outputs)} outputs generated"
            )

            return AgentResult(
                success=True,
                output_type="work_outputs",
                content=response.text,
                work_outputs=work_outputs,
            )

        except Exception as e:
            logger.error(f"[RESEARCH] Failed: {e}", exc_info=True)
            return AgentResult(
                success=False,
                output_type="text",
                error=str(e),
            )

    def _build_research_prompt(
        self,
        task: str,
        context: ContextBundle,
        scope: str,
        depth: str,
    ) -> str:
        """Build the research task prompt."""

        # Scope instructions
        scope_instructions = {
            "general": "Broad analysis covering all relevant aspects.",
            "focused": "Focused analysis on the specific question asked.",
            "comprehensive": "Exhaustive analysis covering all angles and implications.",
        }.get(scope, "Broad analysis covering all relevant aspects.")

        # Depth instructions
        depth_instructions = {
            "quick": "Provide key findings quickly. 1-3 outputs maximum.",
            "standard": "Provide thorough analysis. 3-5 outputs typical.",
            "thorough": "Comprehensive deep-dive. 5-10 outputs, multiple perspectives.",
        }.get(depth, "Provide thorough analysis. 3-5 outputs typical.")

        # Get memory IDs for provenance
        memory_ids = [str(m.id) for m in context.memories[:10]]  # Top 10 for reference

        return f"""Conduct research on: {task}

**Research Parameters:**
- Scope: {scope} ({scope_instructions})
- Depth: {depth} ({depth_instructions})

**Available Memory IDs (for source_memory_ids provenance):**
{memory_ids if memory_ids else 'No memories available'}

**Research Objectives:**
1. Analyze the provided context for relevant information
2. Identify key findings, patterns, and insights
3. Generate actionable recommendations where appropriate
4. Note any gaps in available information

**CRITICAL INSTRUCTION:**
You MUST use the emit_work_output tool to record your findings. Do NOT just describe findings in text.

For each significant finding, insight, or recommendation:
1. Call emit_work_output with structured data
2. Use appropriate output_type (finding, recommendation, insight)
3. Include source_memory_ids for relevant memories
4. Assign confidence scores based on evidence quality

Begin your research now. Emit structured outputs for all significant findings."""

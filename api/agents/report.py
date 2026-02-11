"""
Report Agent - Structured report generation

ADR-016: Layered Agent Architecture
Produces ONE report via submit_output tool.

This agent is used for standalone work tickets that need
structured reports, NOT for deliverable generation.
"""

from typing import Optional
import logging

from .base import BaseAgent, AgentResult, ContextBundle, WorkOutput
from services.anthropic import chat_completion_with_tools, ChatResponse

logger = logging.getLogger(__name__)


REPORT_SYSTEM_PROMPT = """You are a Report Agent specializing in creating structured reports and summaries.

**Your Mission:**
Transform research findings, data, and insights into polished, executive-ready reports.

**Output Requirements:**

You have access to the submit_output tool. Call it ONCE when your report is complete.

Your output should be a complete report in markdown format. You decide the internal structure based on the report type. Common structures include:

- Executive Summary → Key Findings → Analysis → Recommendations
- Summary → Details → Next Steps
- Overview → Sections → Conclusions

**Quality Standards:**
- Clear and concise language
- Evidence-based statements
- Actionable recommendations
- Professional formatting
- Logical flow and structure

**Style Options:**
- Executive: High-level, strategic focus, for senior leadership
- Technical: Detailed methodology, data-heavy, for specialists
- Summary: Concise overview, key points only

{context}
"""


class ReportAgent(BaseAgent):
    """
    Report Agent for structured report generation.

    ADR-016: Produces ONE unified output per work execution.
    Agent determines report structure within markdown content.

    Used for standalone work tickets, not deliverable generation.

    Parameters:
    - style: "executive", "technical", "summary"
    """

    AGENT_TYPE = "report"
    SYSTEM_PROMPT = REPORT_SYSTEM_PROMPT

    async def execute(
        self,
        task: str,
        context: ContextBundle,
        parameters: Optional[dict] = None
    ) -> AgentResult:
        """
        Execute report generation task.

        Args:
            task: Report brief or topic
            context: Context bundle with data/insights
            parameters:
                - style: "executive", "technical", "summary"

        Returns:
            AgentResult with single work_output (the report)
        """
        params = parameters or {}
        style = params.get("style", "executive")

        logger.info(
            f"[REPORT] Starting: task='{task[:50]}...', style={style}"
        )

        # Build system prompt with context
        system_prompt = self._build_system_prompt(context)

        # Build report prompt
        report_prompt = self._build_report_prompt(task, style)

        # Build messages
        messages = [{"role": "user", "content": report_prompt}]

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
                            "content": "Report submitted successfully.",
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
                # Add report-specific metadata
                work_output.metadata.setdefault("style", style)

            logger.info(
                f"[REPORT] Complete: output={'yes' if work_output else 'no'}"
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
            logger.error(f"[REPORT] Failed: {e}", exc_info=True)
            return AgentResult(
                success=False,
                error=str(e),
            )

    def _build_report_prompt(self, task: str, style: str) -> str:
        """Build the report generation prompt."""

        style_instructions = {
            "executive": "Write for senior leadership. Focus on strategic implications, key takeaways, and clear recommendations. Keep it high-level.",
            "technical": "Include technical details and methodology. Support with data and specifics. Be thorough.",
            "summary": "Concise overview with only the key points. Brief and actionable.",
        }.get(style, "Write for senior leadership. Focus on strategic implications and clear recommendations.")

        return f"""Create a report on: {task}

**Style:** {style}
{style_instructions}

**Instructions:**
1. Review the context provided for data and insights
2. Structure your report appropriately for the style
3. Include evidence-based findings and actionable recommendations
4. Call submit_output ONCE with your complete report

The report should be a complete, self-contained document in markdown format.

Begin creating the report now."""

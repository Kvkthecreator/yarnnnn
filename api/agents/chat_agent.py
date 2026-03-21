"""
Chat Agent — enables agents to participate in project meeting room conversations.

ADR-124: Project Meeting Room — agents as chat participants.

Unlike ThinkingPartnerAgent (full meta-cognitive, all primitives), ChatAgent is:
- Domain-scoped: has agent identity, instructions, workspace context
- Read-heavy primitives: workspace read, search, query knowledge
- Limited write: WriteWorkspace for own workspace only
- Streaming: SSE, same transport as TP
- Role-aware: PM agents get project execution primitives; contributors get domain-only

ChatAgent is the third execution mode alongside:
- "chat" (TP) — full meta-cognitive, all primitives
- "headless" — background generation, curated primitives
- "agent_chat" — conversational, domain-scoped, read-heavy + limited write
"""

import logging
from typing import AsyncGenerator, Any, Optional

from agents.base import BaseAgent, AgentResult, ContextBundle
from services.anthropic import (
    chat_completion_stream_with_tools,
    StreamEvent,
)
from services.primitives.registry import get_tools_for_mode, HANDLERS, PRIMITIVE_MODES
from services.workspace import AgentWorkspace, ProjectWorkspace, get_agent_slug
from services.agent_execution import _load_pm_project_context

logger = logging.getLogger(__name__)


# =============================================================================
# Agent Chat Prompts (ADR-124 Phase 3 — versioned)
# =============================================================================

# PM Chat Prompt v3.0 — meta-aware intelligence director with priority hierarchy
# v2.0: live project context injection (ADR-124 Phase 3)
# v3.0: priority hierarchy, opinionated stance, health-first framing
PM_CHAT_PROMPT = """You are {agent_name}, the Project Manager for "{project_title}".

You are an intelligence director — you have opinions, make recommendations, and act decisively. You are NOT a status dashboard.

## Priority Hierarchy (respond in this order of importance)

1. **BLOCKERS** — anything preventing the project from making progress (stale data, failed contributors, budget exhausted, missing platforms). Lead with these. Be direct about impact.
2. **QUALITY** — are contributions actually good enough for the audience? Thin content, coverage gaps, off-topic output. Name the problem specifically.
3. **READINESS** — is this project ready to deliver? What's the gap between current state and a good assembly?
4. **STATUS** — contributor freshness, schedule, routine facts. Only after higher priorities are addressed.

## Project Health Assessment

Before responding, mentally classify this project's health:
- **Healthy**: contributors producing quality output on cadence, data fresh, on track to deliver
- **Attention needed**: something is degraded (stale data, thin contributions, approaching budget limit) but recoverable
- **Blocked**: cannot make meaningful progress without intervention (no data, budget exhausted, contributor failures)

Lead every response with your health judgment. Don't just list facts — interpret them.

## Project Context
{project_context}

## Contributors
{contributor_status}

## Work Plan
{work_plan}

## Budget
{budget_status}

## How to Communicate

- **Have a point of view.** Don't ask "would you like me to X?" — say "I recommend X because Y" or just do it if you have the authority.
- **Prioritize ruthlessly.** If data is 22 hours stale, that's the headline — not one bullet point among many.
- **Be specific about impact.** Not "content is getting stale" but "Slack data is 22h old — the next assembly will miss anything from today."
- **Compress routine status.** If everything is healthy, say so in one line. Don't enumerate every contributor when they're all fine.
- **Act, don't narrate.** When asked to assemble or advance, do it and report the result. Don't explain what you're about to do step by step.
- **Name what's missing.** If the project has structural gaps (e.g., only one platform connected for a cross-platform project), say so proactively.

You have access to your workspace files, the project's knowledge base, and PM-specific tools (advance contributors, update work plan, check freshness).

{workspace_context}
"""

# Contributor Chat Prompt v2.0 — adds project objective + own contribution context (ADR-124 Phase 3)
CONTRIBUTOR_CHAT_PROMPT = """You are {agent_name}, a {role} agent contributing to project "{project_title}".

## Project Objective
{project_objective}

Your domain expertise is {scope_description}. You have accumulated:
- Your workspace: AGENT.md (identity), thesis.md (domain understanding), memory/ (observations)
- Your contribution history to this project
- Knowledge from your connected platforms

{contribution_context}

When the user talks to you:
- Answer from your domain perspective — what you know about your area
- Reference your recent work, observations, and domain thesis
- You can read workspace files and search knowledge, but you don't coordinate — PM does that
- Be concise — you're a specialist, not a generalist

{workspace_context}
"""


class ChatAgentAuth:
    """Auth context for agent_chat mode execution."""

    def __init__(self, client, user_id: str, agent: dict):
        self.client = client
        self.user_id = user_id
        self.headless = False  # Not headless — interactive chat
        self.agent_chat = True  # ADR-124: signals agent_chat mode
        self.agent = agent
        self.agent_sources = agent.get("sources") or []
        self.coordinator_agent_id = None
        self.pending_renders: list[dict] = []
        self.agent_slug = get_agent_slug(agent)


class ChatAgent(BaseAgent):
    """
    Enables an agent to participate in chat conversations (ADR-124).

    Domain-scoped, read-heavy, streaming. Used in project meeting rooms
    where agents are visible participants, not abstract data.
    """

    AGENT_TYPE = "chat_agent"

    def __init__(self, agent: dict, project_slug: str, model: str = "claude-sonnet-4-20250514"):
        super().__init__(model)
        self.agent = agent
        self.project_slug = project_slug
        self.tools = get_tools_for_mode("agent_chat")

    async def _load_workspace_context(self, client, user_id: str) -> str:
        """Load agent's workspace context for prompt injection."""
        try:
            ws = AgentWorkspace(client, user_id, self.agent["id"])
            slug = get_agent_slug(self.agent)

            parts = []

            # Load AGENT.md (identity)
            agent_md = await ws.read(f"/agents/{slug}/AGENT.md")
            if agent_md:
                parts.append(f"## Your Identity (AGENT.md)\n{agent_md.get('content', '')[:2000]}")

            # Load thesis.md (domain understanding)
            thesis = await ws.read(f"/agents/{slug}/thesis.md")
            if thesis:
                parts.append(f"## Your Domain Thesis\n{thesis.get('content', '')[:2000]}")

            # Load memory files (observations, preferences)
            memory_files = await ws.list_files(f"/agents/{slug}/memory/")
            if memory_files:
                memory_parts = []
                for mf in memory_files[:5]:  # Cap at 5 memory files
                    content = await ws.read(mf["path"])
                    if content:
                        filename = mf["path"].split("/")[-1]
                        memory_parts.append(f"### {filename}\n{content.get('content', '')[:1000]}")
                if memory_parts:
                    parts.append("## Your Memory\n" + "\n\n".join(memory_parts))

            return "\n\n".join(parts) if parts else "No workspace context loaded yet."
        except Exception as e:
            logger.warning(f"[CHAT-AGENT] Failed to load workspace context: {e}")
            return "Workspace context unavailable."

    def _build_system_prompt(
        self,
        workspace_context: str,
        project_title: str,
        project_context: Optional[dict] = None,
    ) -> str:
        """Build the agent's conversational system prompt."""
        role = self.agent.get("role", "digest")
        scope = self.agent.get("scope", "platform")
        agent_name = self.agent.get("title", "Agent")

        # Scope description for contributor prompt
        scope_descriptions = {
            "platform": "monitoring and synthesizing content from your connected platform",
            "cross_platform": "synthesizing insights across multiple platforms",
            "knowledge": "deep analysis of accumulated knowledge",
            "research": "research and investigation",
            "autonomous": "autonomous operation and decision-making",
        }
        scope_description = scope_descriptions.get(scope, f"{scope} operations")

        if role == "pm":
            pc = project_context or {}
            return PM_CHAT_PROMPT.format(
                agent_name=agent_name,
                project_title=project_title,
                project_context=pc.get("project_context", "Not available."),
                contributor_status=pc.get("contributor_status", "Not available."),
                work_plan=pc.get("work_plan", "No work plan set."),
                budget_status=pc.get("budget_status", "Unknown"),
                workspace_context=workspace_context,
            )
        else:
            pc = project_context or {}
            return CONTRIBUTOR_CHAT_PROMPT.format(
                agent_name=agent_name,
                role=role,
                project_title=project_title,
                project_objective=pc.get("project_objective", "Not specified."),
                scope_description=scope_description,
                contribution_context=pc.get("contribution_context", ""),
                workspace_context=workspace_context,
            )

    async def execute(
        self,
        task: str,
        context: ContextBundle,
        parameters: Optional[dict] = None,
    ) -> AgentResult:
        """Non-streaming execute (not used for chat, but required by BaseAgent)."""
        return AgentResult(
            success=False,
            error="ChatAgent only supports streaming via execute_stream_with_tools",
        )

    async def execute_stream_with_tools(
        self,
        task: str,
        context: ContextBundle,
        auth: Any,
        parameters: Optional[dict] = None,
    ) -> AsyncGenerator[StreamEvent, None]:
        """
        Stream a response as the agent in a meeting room conversation.

        Args:
            task: User's message
            context: ContextBundle (unused — workspace context loaded directly)
            auth: ChatAgentAuth with agent context
            parameters:
                - history: conversation history
                - project_title: project display name
        """
        params = parameters or {}
        history = params.get("history", [])
        project_title = params.get("project_title", self.project_slug)

        # Load workspace context
        workspace_context = await self._load_workspace_context(
            auth.client, auth.user_id
        )

        # ADR-124 Phase 3: Load project context based on agent role
        role = self.agent.get("role", "digest")
        project_context = None

        if role == "pm":
            # PM gets full project context — reuse headless loader (singular implementation)
            try:
                project_context = await _load_pm_project_context(
                    auth.client, auth.user_id, self.project_slug
                )
            except Exception as e:
                logger.warning(f"[CHAT-AGENT] Failed to load PM project context: {e}")
        else:
            # Contributors get project objective + own contribution context
            try:
                pw = ProjectWorkspace(auth.client, auth.user_id, self.project_slug)
                project_data = await pw.read_project()
                objective = "Not specified."
                contribution_context = ""

                if project_data:
                    obj = project_data.get("objective", {})
                    objective = obj.get("deliverable", "Not specified.")
                    if obj.get("audience"):
                        objective += f"\nAudience: {obj['audience']}"
                    if obj.get("format"):
                        objective += f"\nFormat: {obj['format']}"

                    # Find this agent's expected contribution
                    agent_slug = get_agent_slug(self.agent)
                    for c in project_data.get("contributors", []):
                        if c.get("agent_slug") == agent_slug:
                            if c.get("expected_contribution"):
                                contribution_context = (
                                    f"## Your Expected Contribution\n{c['expected_contribution']}"
                                )
                            break

                project_context = {
                    "project_objective": objective,
                    "contribution_context": contribution_context,
                }
            except Exception as e:
                logger.warning(f"[CHAT-AGENT] Failed to load contributor context: {e}")

        system = self._build_system_prompt(
            workspace_context=workspace_context,
            project_title=project_title,
            project_context=project_context,
        )

        # Build messages — filter empty assistant messages
        messages = [
            m for m in history
            if not (m.get("role") == "assistant" and not m.get("content"))
        ]
        messages.append({"role": "user", "content": [{"type": "text", "text": task}]})

        # Merge if last message was also user role (Claude API alternation)
        if len(messages) >= 2 and messages[-2].get("role") == "user":
            prev = messages[-2]["content"]
            curr = messages[-1]["content"]
            if isinstance(prev, str):
                prev = [{"type": "text", "text": prev}]
            if isinstance(curr, str):
                curr = [{"type": "text", "text": curr}]
            messages[-2]["content"] = prev + curr
            messages.pop()

        # Create tool executor scoped to this agent
        # PM-only write primitives: coordination actions that only PM should perform.
        # Read primitives (ReadProjectStatus, CheckContributorFreshness) stay open
        # to all agents — anyone can check the board, only PM moves the tickets.
        PM_ONLY_PRIMITIVES = {"RequestContributorAdvance", "UpdateWorkPlan"}

        async def tool_executor(tool_name: str, tool_input: dict) -> dict:
            modes = PRIMITIVE_MODES.get(tool_name, [])
            if "agent_chat" not in modes:
                return {
                    "success": False,
                    "error": "not_available",
                    "message": f"Tool {tool_name} is not available in agent_chat mode",
                }
            # Role gate: PM-only write primitives
            if tool_name in PM_ONLY_PRIMITIVES and self.agent.get("role") != "pm":
                return {
                    "success": False,
                    "error": "not_authorized",
                    "message": f"{tool_name} is a PM coordination action — contributors can read project status but only PM can steer.",
                }
            handler = HANDLERS.get(tool_name)
            if not handler:
                return {
                    "success": False,
                    "error": "unknown_primitive",
                    "message": f"Unknown primitive: {tool_name}",
                }
            try:
                return await handler(auth, tool_input)
            except Exception as e:
                logger.error(f"[CHAT-AGENT] Tool {tool_name} failed: {e}")
                return {
                    "success": False,
                    "error": "execution_error",
                    "message": f"Tool execution failed: {e}",
                }

        async for event in chat_completion_stream_with_tools(
            messages=messages,
            system=system,
            tools=self.tools,
            tool_executor=tool_executor,
            model=self.model,
            tool_choice={"type": "auto"},
        ):
            yield event

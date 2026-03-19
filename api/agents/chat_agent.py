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
from services.workspace import AgentWorkspace, get_agent_slug

logger = logging.getLogger(__name__)


# =============================================================================
# Agent Chat Prompts (ADR-124 Phase 3 — versioned)
# =============================================================================

# PM Chat Prompt v1.0
PM_CHAT_PROMPT = """You are {agent_name}, the Project Manager for "{project_title}".

Your domain is coordinating this project's execution. You have deep knowledge of:
- The project objective and what the user wants
- Each contributor's role, recent work, and quality trajectory
- The work plan, budget status, and assembly schedule

When the user talks to you:
- Answer from your PM perspective — you know this project intimately
- Reference specific contributor work, quality assessments, timeline status
- You can take PM actions (check freshness, advance schedules, update work plan)
- Be concise and direct — you're a domain expert, not a general assistant
- If the user gives directives (e.g., "change format to PDF"), act on them by updating your work plan

You have access to your workspace files, the project's knowledge base, and PM-specific tools.

{workspace_context}
"""

# Contributor Chat Prompt v1.0
CONTRIBUTOR_CHAT_PROMPT = """You are {agent_name}, a {role} agent contributing to project "{project_title}".

Your domain expertise is {scope_description}. You have accumulated:
- Your workspace: AGENT.md (identity), thesis.md (domain understanding), memory/ (observations)
- Your contribution history to this project
- Knowledge from your connected platforms

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
    ) -> str:
        """Build the agent's conversational system prompt."""
        role = self.agent.get("role", "digest")
        scope = self.agent.get("scope", "platform")
        agent_name = self.agent.get("title", "Agent")

        # Scope description for contributor prompt
        scope_descriptions = {
            "platform": f"monitoring and synthesizing content from your connected platform",
            "cross_platform": "synthesizing insights across multiple platforms",
            "knowledge": "deep analysis of accumulated knowledge",
            "research": "research and investigation",
            "autonomous": "autonomous operation and decision-making",
        }
        scope_description = scope_descriptions.get(scope, f"{scope} operations")

        if role == "pm":
            return PM_CHAT_PROMPT.format(
                agent_name=agent_name,
                project_title=project_title,
                workspace_context=workspace_context,
            )
        else:
            return CONTRIBUTOR_CHAT_PROMPT.format(
                agent_name=agent_name,
                role=role,
                project_title=project_title,
                scope_description=scope_description,
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

        system = self._build_system_prompt(
            workspace_context=workspace_context,
            project_title=project_title,
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
        async def tool_executor(tool_name: str, tool_input: dict) -> dict:
            modes = PRIMITIVE_MODES.get(tool_name, [])
            if "agent_chat" not in modes:
                return {
                    "success": False,
                    "error": "not_available",
                    "message": f"Tool {tool_name} is not available in agent_chat mode",
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

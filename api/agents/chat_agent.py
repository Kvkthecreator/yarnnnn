"""
Chat Agent — enables agents to participate in project meeting room conversations.

ADR-124: Project Meeting Room — agents as chat participants.

Unlike ThinkingPartnerAgent (full meta-cognitive, all primitives), ChatAgent is:
- Domain-scoped: has agent identity, instructions, workspace context
- Read-heavy primitives: workspace read, search, query knowledge
- Limited write: WriteFile for own workspace only
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

# PM Chat Prompt v4.0 — directive persistence + layered cognitive model
# v2.0: live project context injection (ADR-124 Phase 3)
# v3.0: prerequisite-layer reasoning, context-objective fitness, opinionated stance
# v4.0: ADR-128 — persist project-level decisions to memory/decisions.md via WriteFile
PM_CHAT_PROMPT = """You are {agent_name}, the Project Manager for "{project_title}".

You reason through prerequisite layers. Each layer must be satisfied before the next matters. Stop at the first broken layer — that IS your assessment.

## Layer 1 — Commitment: Can I define what success looks like?
Is the objective complete? (deliverable + audience + format + purpose all defined?)
If any part is missing, that's the headline. Nothing else matters until the commitment is clear.

Assessment: {commitment_assessment}

## Layer 2 — Structure: Do I have the right team for this commitment?
Given the objective, do the current members have the right roles and scopes?
A cross-platform synthesis with one platform-scoped agent is structurally incomplete — it cannot succeed regardless of execution quality.

Assessment: {structural_assessment}

## Layer 3 — Context: Do we have the right inputs?
Given the objective, what context is REQUIRED? Platform connections are supply, not demand.
If Slack is connected but the objective is about financial reporting, Slack data is noise.
Evaluate context-objective fit. Missing required context is a blocker. Irrelevant available context should be ignored.

Assessment: {context_assessment}

## Layer 4 — Output Quality
Only meaningful after Layers 1-3 are satisfied. Contributor freshness, content depth, coverage gaps.

{contributor_status}

## Layer 5 — Delivery Readiness
Work plan, budget, assembly readiness.

Work Plan: {work_plan}
Budget: {budget_status}

## Your Prior Assessment
{prior_assessment}

## Project Charter
{project_context}

## How to Reason and Communicate

- **Stop at the first broken layer.** If structure is wrong, don't discuss output quality. Fix the foundation first.
- **Have a point of view.** Don't ask "would you like me to X?" — say "I recommend X because Y" or just do it.
- **Be specific about impact.** Not "content is getting stale" but "Slack data is 22h old — the next assembly will miss today's activity."
- **Context is not automatically relevant.** A connected platform that doesn't serve the objective has no bearing. Don't report it as context.
- **Compress routine status.** If Layers 1-3 are healthy, say so briefly. Don't enumerate when everything is fine.
- **Act, don't narrate.** When asked to do something, do it and report the result — don't describe what you're about to do.
- **Think like an architect scoped to this project.** You should be able to say "this project cannot succeed with its current configuration" when that's true.

You have access to your workspace files, the project's knowledge base, and PM-specific tools (advance contributors, update work plan, check freshness).

## Directive Persistence (ADR-128)

When the user makes a **project-level decision** during this conversation — objective refinements, structural changes, delivery adjustments, priority shifts — persist it immediately using WriteFile to append to `memory/decisions.md`. This ensures the decision survives session rotation and compaction.

**What to persist**: Decisions that affect future work — "focus on action items not summaries", "switch to weekly delivery", "add a research contributor", "deprioritize calendar data". NOT ephemeral discussion, questions, or status inquiries.

**Format**: Append a dated entry: `## [date] — [decision summary]` followed by a brief description. Never overwrite — decisions accumulate.

{workspace_context}
"""

# Contributor Chat Prompt v3.0 — adds directive persistence (ADR-128)
# v2.0: project objective + own contribution context (ADR-124 Phase 3)
# v3.0: ADR-128 — persist user directives to memory/directives.md via WriteFile
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

## Directive Persistence (ADR-128)

When the user gives you a **durable directive** — focus areas, style preferences, priorities, scope adjustments — persist it immediately using WriteFile to append to `memory/directives.md`. This ensures the guidance survives session rotation and shapes all your future runs.

**What to persist**: Guidance that affects your future work — "focus on action items", "keep it under 500 words", "ignore the #random channel", "always include a TL;DR". NOT ephemeral questions, one-off requests, or status inquiries.

**Format**: Append a dated entry: `## [date] — [directive summary]` followed by a brief description. Never overwrite — directives accumulate.

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
        self.agent_sources = []  # Column dropped — sources no longer on agents table
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
            agent_md = await ws.read("AGENT.md")
            if agent_md:
                text = agent_md if isinstance(agent_md, str) else agent_md.get("content", "")
                parts.append(f"## Your Identity (AGENT.md)\n{text[:2000]}")

            # ADR-154: thesis.md dissolved — domain understanding in /workspace/context/

            # Load memory files (playbooks only per ADR-154)
            memory_files = await ws.list("memory/")
            if memory_files:
                memory_parts = []
                for mf_path in memory_files[:5]:  # Cap at 5 memory files
                    content = await ws.read(mf_path)
                    if content:
                        filename = mf_path.split("/")[-1]
                        text = content if isinstance(content, str) else content.get("content", "")
                        memory_parts.append(f"### {filename}\n{text[:1000]}")
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
                commitment_assessment=pc.get("commitment_assessment", "Unknown."),
                structural_assessment=pc.get("structural_assessment", "Unknown."),
                context_assessment=pc.get("context_assessment", "Unknown."),
                contributor_status=pc.get("contributor_status", "Not available."),
                work_plan=pc.get("work_plan", "No work plan set."),
                budget_status=pc.get("budget_status", "Unknown"),
                prior_assessment=pc.get("prior_assessment", "No prior assessment."),
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

        # Load role-specific context
        role = self.agent.get("role", "digest")
        project_context = None

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

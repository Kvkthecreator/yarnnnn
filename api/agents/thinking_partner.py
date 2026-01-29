"""
Thinking Partner Agent - Conversational assistant with two-layer context (ADR-004)
"""

from typing import AsyncGenerator, Optional
from agents.base import BaseAgent, AgentResult, ContextBundle
from services.anthropic import chat_completion, chat_completion_stream


# Category labels for user context (human-readable)
USER_CATEGORY_LABELS = {
    "preference": "Preference",
    "business_fact": "Business/Domain",
    "work_pattern": "Work Pattern",
    "communication_style": "Communication Style",
    "goal": "Goal",
    "constraint": "Constraint",
    "relationship": "Professional Relationship",
}

# Semantic type labels for project blocks
SEMANTIC_TYPE_LABELS = {
    "fact": "Fact",
    "guideline": "Guideline",
    "requirement": "Requirement",
    "insight": "Insight",
    "question": "Open Question",
    "assumption": "Assumption",
    "note": "Note",
}


class ThinkingPartnerAgent(BaseAgent):
    """
    Conversational assistant with two-layer context.

    Uses:
    - User context: What YARNNN knows about the user (portable across projects)
    - Project context: What's specific to this project

    Output: Chat response (text, optionally streamed)
    """

    SYSTEM_PROMPT = """You are a thoughtful assistant helping the user think through problems and ideas. You have access to two layers of context:

1. **User Context** - What you know about this person across all their work (their preferences, business, patterns, goals)
2. **Project Context** - What's specific to this current project (requirements, facts, guidelines)

Guidelines:
- Be conversational but substantive
- Reference specific context when it's relevant to the question
- Use user context to personalize your responses (their communication preferences, business domain)
- Use project context to stay grounded in this specific work
- Ask clarifying questions when the user's intent is unclear
- Help structure thinking - don't just answer, help them explore
- If the context doesn't contain relevant information, say so honestly

{context}"""

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        super().__init__(model)

    def _format_user_context(self, context: ContextBundle) -> str:
        """Format user context section."""
        if not context.user_context:
            return ""

        lines = ["## About You (User Context)\n"]

        # Group by category
        by_category = {}
        for item in context.user_context:
            cat = item.category
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(item)

        for category, items in by_category.items():
            label = USER_CATEGORY_LABELS.get(category, category.title())
            lines.append(f"### {label}")
            for item in items:
                lines.append(f"- {item.content}")
            lines.append("")

        return "\n".join(lines)

    def _format_project_context(self, context: ContextBundle) -> str:
        """Format project context section."""
        if not context.blocks:
            return ""

        lines = ["## Project Context\n"]

        # Group by semantic type
        by_type = {}
        for block in context.blocks:
            stype = block.semantic_type or block.block_type
            if stype not in by_type:
                by_type[stype] = []
            by_type[stype].append(block)

        for stype, blocks in by_type.items():
            label = SEMANTIC_TYPE_LABELS.get(stype, stype.upper())
            lines.append(f"### {label}s")
            for block in blocks:
                lines.append(f"- {block.content}")
            lines.append("")

        return "\n".join(lines)

    def _build_system_prompt(self, context: ContextBundle, include_context: bool) -> str:
        """Build system prompt with two-layer context."""
        if not include_context:
            return self.SYSTEM_PROMPT.format(context="No context loaded for this conversation.")

        sections = []

        # User context (always include if available)
        user_section = self._format_user_context(context)
        if user_section:
            sections.append(user_section)

        # Project context
        project_section = self._format_project_context(context)
        if project_section:
            sections.append(project_section)

        if not sections:
            context_text = "No context available yet. As we chat, I'll learn more about you and this project."
        else:
            context_text = "\n".join(sections)

        return self.SYSTEM_PROMPT.format(context=context_text)

    async def execute(
        self,
        task: str,  # User message
        context: ContextBundle,
        parameters: Optional[dict] = None
    ) -> AgentResult:
        """
        Process chat message (non-streaming).

        Args:
            task: User's message
            context: Project context
            parameters:
                - include_context: bool (default True)
                - history: list of prior messages

        Returns:
            AgentResult with assistant response
        """
        params = parameters or {}
        include_context = params.get("include_context", True)
        history = params.get("history", [])

        system = self._build_system_prompt(context, include_context)

        # Build messages list
        messages = list(history)  # Copy history
        messages.append({"role": "user", "content": task})

        try:
            response = await chat_completion(
                messages=messages,
                system=system,
                model=self.model,
            )

            return AgentResult(
                success=True,
                output_type="text",
                content=response,
            )
        except Exception as e:
            return AgentResult(
                success=False,
                output_type="text",
                error=str(e),
            )

    async def execute_stream(
        self,
        task: str,
        context: ContextBundle,
        parameters: Optional[dict] = None
    ) -> AsyncGenerator[str, None]:
        """
        Process chat message with streaming response.

        Args:
            task: User's message
            context: Project context
            parameters:
                - include_context: bool (default True)
                - history: list of prior messages

        Yields:
            Text chunks as they arrive
        """
        params = parameters or {}
        include_context = params.get("include_context", True)
        history = params.get("history", [])

        system = self._build_system_prompt(context, include_context)

        # Build messages list
        messages = list(history)
        messages.append({"role": "user", "content": task})

        async for chunk in chat_completion_stream(
            messages=messages,
            system=system,
            model=self.model,
        ):
            yield chunk

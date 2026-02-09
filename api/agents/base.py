"""
Base agent interface and shared types

ADR-005: Unified memory architecture with embeddings
ADR-009: Work and agent orchestration
ADR-016: Layered agent architecture and unified output model
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Any
from uuid import UUID
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class Memory:
    """
    Unified memory item (ADR-005, ADR-034).

    Scope is determined by domain_id:
    - domain_id is None or default domain → always accessible (user profile)
    - domain_id is specific domain → domain-scoped context

    ADR-034: Domains emerge from deliverable source patterns.
    The default domain holds portable user profile information.
    """
    id: UUID
    content: str
    importance: float = 0.5
    tags: list[str] = field(default_factory=list)
    entities: dict = field(default_factory=dict)  # {people: [], companies: [], concepts: []}
    source_type: str = "chat"  # chat, document, manual, import
    domain_id: Optional[UUID] = None  # None or default = always accessible

    @property
    def is_default_domain(self) -> bool:
        """Returns True if this memory is in the default domain (always accessible)."""
        return self.domain_id is None


@dataclass
class ContextBundle:
    """
    Context provided to agents.

    ADR-005 + ADR-034 unified architecture:
    - memories: All loaded memories (already filtered by domain at load time)
    - domain_id: The active domain for this context

    The search function handles domain scoping:
    - If domain_id is set, includes memories from that domain + default domain
    - Default domain memories (user profile) are always accessible

    For filtering (backwards compatible naming):
    - user_memories: Returns memories from default domain (always accessible)
    - domain_memories: Returns memories from the active domain
    """
    memories: list[Memory] = field(default_factory=list)
    documents: list[dict] = field(default_factory=list)  # {id, filename, content_preview}
    domain_id: Optional[UUID] = None  # The active domain (if any)
    domain_name: Optional[str] = None  # Domain name for context

    @property
    def user_memories(self) -> list[Memory]:
        """Get default domain memories (always accessible - user profile)."""
        return [m for m in self.memories if m.is_default_domain]

    @property
    def domain_memories(self) -> list[Memory]:
        """Get domain-scoped memories (for active domain only)."""
        if self.domain_id is None:
            return []
        return [m for m in self.memories if m.domain_id == self.domain_id]

    # Backwards compatibility alias
    @property
    def project_memories(self) -> list[Memory]:
        """Deprecated: Use domain_memories instead."""
        return self.domain_memories

    @property
    def has_context(self) -> bool:
        """Returns True if there's any context available."""
        return len(self.memories) > 0 or len(self.documents) > 0


@dataclass
class WorkOutput:
    """
    Single unified output from agent work (ADR-016).

    Each work execution produces ONE output. The agent determines
    the structure within the content field.

    Fields:
    - title: Human-readable title for the output
    - content: Markdown body (agent decides internal structure)
    - metadata: Agent-specific metadata (varies by agent type)

    Metadata by agent type:
    - Research: sources, confidence, scope, depth
    - Content: format, platform, tone, word_count
    - Reporting: style, audience, period
    """
    title: str
    content: str  # Markdown - agent decides structure
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dict for database storage."""
        return {
            "title": self.title,
            "content": self.content,
            "metadata": self.metadata,
        }


@dataclass
class AgentResult:
    """
    Result from agent execution (ADR-016).

    For work agents: success + work_output (single output)
    For TP: success + content (conversation response)
    """
    success: bool
    error: Optional[str] = None

    # Work output (ADR-016: single unified output per work)
    work_output: Optional[WorkOutput] = None

    # For TP/chat responses
    content: Optional[str] = None

    # Token tracking
    input_tokens: int = 0
    output_tokens: int = 0


# Tool definition for work agents (ADR-016)
# Single unified output per work execution
SUBMIT_OUTPUT_TOOL = {
    "name": "submit_output",
    "description": """Submit your completed work output.

Call this ONCE when your work is complete. Each work execution produces exactly ONE output.
Structure your content as markdown - you decide the internal structure based on the task.

The output will be displayed to the user in the output panel. Make it complete and self-contained.""",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Clear title for the output (what was produced)"
            },
            "content": {
                "type": "string",
                "description": "The complete output in markdown format. Structure it appropriately for the task (sections, lists, etc.)"
            },
            "metadata": {
                "type": "object",
                "description": "Optional metadata about the output",
                "properties": {
                    "confidence": {
                        "type": "number",
                        "description": "Confidence score 0.0-1.0",
                        "minimum": 0.0,
                        "maximum": 1.0
                    },
                    "sources": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Sources or references used"
                    },
                    "word_count": {
                        "type": "integer",
                        "description": "Word count (for content outputs)"
                    },
                    "format": {
                        "type": "string",
                        "description": "Content format (e.g., linkedin, blog, email)"
                    }
                }
            }
        },
        "required": ["title", "content"]
    }
}


class BaseAgent(ABC):
    """
    Base class for all work agents.

    Subclasses must implement execute() method.

    ADR-016: Work agents produce ONE unified output via submit_output tool.
    """

    AGENT_TYPE: str = "base"
    SYSTEM_PROMPT: str = ""

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        self.model = model
        self.tools = [SUBMIT_OUTPUT_TOOL]

    @abstractmethod
    async def execute(
        self,
        task: str,
        context: ContextBundle,
        parameters: Optional[dict] = None
    ) -> AgentResult:
        """
        Execute agent task with context.

        Args:
            task: The work request description
            context: Context bundle with memories
            parameters: Optional agent-specific parameters

        Returns:
            AgentResult with output or error
        """
        pass

    def build_context_prompt(self, context: ContextBundle, style_context: str = None) -> str:
        """
        Build context section for system prompt.

        Args:
            context: Context bundle with memories
            style_context: Optional style context (e.g., "slack" or "notion")
                          Used to select the appropriate style profile
        """
        if not context.has_context:
            return "No context available."

        lines = ["## Available Context\n"]

        # Separate style memories from regular user memories
        user_memories = context.user_memories
        style_memories = [m for m in user_memories if "style" in m.tags]
        regular_user_memories = [m for m in user_memories if "style" not in m.tags]

        # Format style profile if available (ADR-027 Phase 5)
        if style_memories:
            lines.append(self._format_style_memories(style_memories, style_context))
            lines.append("")

        # Format regular user memories
        if regular_user_memories:
            lines.append("### About the User")
            for mem in regular_user_memories:
                tags_str = f" [{', '.join(mem.tags)}]" if mem.tags else ""
                lines.append(f"- {mem.content}{tags_str}")
            lines.append("")

        # Format domain memories
        domain_memories = context.domain_memories
        if domain_memories:
            domain_label = f"### Context: {context.domain_name}" if context.domain_name else "### Domain Context"
            lines.append(domain_label)
            for mem in domain_memories:
                tags_str = f" [{', '.join(mem.tags)}]" if mem.tags else ""
                lines.append(f"- {mem.content}{tags_str}")
            lines.append("")

        return "\n".join(lines)

    def _format_style_memories(self, style_memories: list[Memory], style_context: str = None) -> str:
        """
        Format style memories for the system prompt.

        Style memories are user-scoped and platform-specific. If a style_context
        is provided (e.g., "slack", "notion"), we prioritize matching profiles.

        Args:
            style_memories: List of memories tagged with "style"
            style_context: Optional context to match (e.g., "slack", "documentation")

        Returns:
            Formatted style section for the system prompt
        """
        if not style_memories:
            return ""

        lines = ["### User's Communication Style"]
        lines.append("*Apply this style when generating content.*\n")

        # If style_context provided, prioritize matching profiles
        if style_context:
            matching = [m for m in style_memories if style_context.lower() in [t.lower() for t in m.tags]]
            if matching:
                # Use the most relevant style profile
                for mem in matching[:1]:  # Just use the first matching one
                    lines.append(mem.content)
                return "\n".join(lines)

        # No context match - show available styles
        if len(style_memories) == 1:
            lines.append(style_memories[0].content)
        else:
            # Multiple style profiles - indicate which are available
            lines.append("*Multiple style profiles available:*\n")
            for mem in style_memories[:3]:  # Limit to 3 to avoid overwhelming context
                platform_tags = [t for t in mem.tags if t != "style"]
                if platform_tags:
                    lines.append(f"**{platform_tags[0].title()} Style:**")
                lines.append(mem.content)
                lines.append("")

        return "\n".join(lines)

    def _build_system_prompt(self, context: ContextBundle, style_context: str = None) -> str:
        """
        Build full system prompt with context.

        Args:
            context: Context bundle with memories
            style_context: Optional style context for selecting appropriate style profile
        """
        context_text = self.build_context_prompt(context, style_context)
        return self.SYSTEM_PROMPT.format(context=context_text)

    def _parse_work_output(self, tool_calls: list[dict]) -> Optional[WorkOutput]:
        """Parse submit_output tool call into WorkOutput (ADR-016: single output)."""
        for call in tool_calls:
            if call.get("name") == "submit_output":
                input_data = call.get("input", {})
                return WorkOutput(
                    title=input_data.get("title", "Untitled"),
                    content=input_data.get("content", ""),
                    metadata=input_data.get("metadata", {}),
                )
        return None

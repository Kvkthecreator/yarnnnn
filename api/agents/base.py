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
    Unified memory item (ADR-005).

    Replaces the previous Block + UserContextItem split.
    Scope is determined by project_id:
    - project_id is None → user-scoped (portable across projects)
    - project_id is not None → project-scoped (isolated to that project)
    """
    id: UUID
    content: str
    importance: float = 0.5
    tags: list[str] = field(default_factory=list)
    entities: dict = field(default_factory=dict)  # {people: [], companies: [], concepts: []}
    source_type: str = "chat"  # chat, document, manual, import
    project_id: Optional[UUID] = None  # None = user-scoped

    @property
    def is_user_scoped(self) -> bool:
        """Returns True if this memory is user-scoped (portable)."""
        return self.project_id is None


@dataclass
class ContextBundle:
    """
    Context provided to agents.

    ADR-005 unified architecture:
    - memories: Combined list of user + project memories
    - Scope is implicit in each memory's project_id

    For filtering:
    - user_memories: Returns memories where project_id is None
    - project_memories: Returns memories where project_id matches
    """
    memories: list[Memory] = field(default_factory=list)
    documents: list[dict] = field(default_factory=list)  # {id, filename, content_preview}
    project_id: Optional[UUID] = None  # The current project (if any)
    project_name: Optional[str] = None  # Project name for context

    @property
    def user_memories(self) -> list[Memory]:
        """Get user-scoped memories (portable across projects)."""
        return [m for m in self.memories if m.project_id is None]

    @property
    def project_memories(self) -> list[Memory]:
        """Get project-scoped memories (for current project only)."""
        if self.project_id is None:
            return []
        return [m for m in self.memories if m.project_id == self.project_id]

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

    def build_context_prompt(self, context: ContextBundle) -> str:
        """Build context section for system prompt."""
        if not context.has_context:
            return "No context available."

        lines = ["## Available Context\n"]

        # Format user memories
        user_memories = context.user_memories
        if user_memories:
            lines.append("### About the User")
            for mem in user_memories:
                tags_str = f" [{', '.join(mem.tags)}]" if mem.tags else ""
                lines.append(f"- {mem.content}{tags_str}")
            lines.append("")

        # Format project memories
        project_memories = context.project_memories
        if project_memories:
            project_label = f"### Project Context: {context.project_name}" if context.project_name else "### Project Context"
            lines.append(project_label)
            for mem in project_memories:
                tags_str = f" [{', '.join(mem.tags)}]" if mem.tags else ""
                lines.append(f"- {mem.content}{tags_str}")
            lines.append("")

        return "\n".join(lines)

    def _build_system_prompt(self, context: ContextBundle) -> str:
        """Build full system prompt with context."""
        context_text = self.build_context_prompt(context)
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

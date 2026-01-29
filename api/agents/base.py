"""
Base agent interface and shared types

ADR-005: Unified memory architecture with embeddings
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID


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
class AgentResult:
    """Result from agent execution"""
    success: bool
    output_type: str  # text, file
    content: Optional[str] = None
    file_path: Optional[str] = None
    title: Optional[str] = None
    error: Optional[str] = None


class BaseAgent(ABC):
    """
    Base class for all agents.

    Subclasses must implement execute() method.
    """

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        self.model = model

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
            lines.append("### About You")
            for mem in user_memories:
                tags_str = f" [{', '.join(mem.tags)}]" if mem.tags else ""
                lines.append(f"- {mem.content}{tags_str}")
            lines.append("")

        # Format project memories
        project_memories = context.project_memories
        if project_memories:
            lines.append("### Project Context")
            for mem in project_memories:
                tags_str = f" [{', '.join(mem.tags)}]" if mem.tags else ""
                lines.append(f"- {mem.content}{tags_str}")
            lines.append("")

        return "\n".join(lines)

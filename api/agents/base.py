"""
Base agent interface and shared types
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from uuid import UUID


@dataclass
class Block:
    """Atomic knowledge unit (project-scoped)"""
    id: UUID
    content: str
    block_type: str
    semantic_type: Optional[str] = None
    metadata: Optional[dict] = None


@dataclass
class UserContextItem:
    """User context item (user-scoped, portable across projects)"""
    id: UUID
    category: str  # preference, business_fact, work_pattern, communication_style, goal, constraint, relationship
    key: str
    content: str
    importance: float = 0.5
    confidence: float = 0.8


@dataclass
class ContextBundle:
    """
    Context provided to agents.

    Two-layer architecture (ADR-004):
    - user_context: User-level memory (portable, about the user)
    - blocks: Project-level memory (isolated, about this project)

    For user-level chat (no project), project_id is None and blocks is empty.
    """
    blocks: list[Block]
    documents: list[dict]  # {id, filename, content_preview}
    project_id: Optional[UUID] = None  # None for user-level chat
    user_context: list[UserContextItem] = None  # Optional user-level context

    def __post_init__(self):
        if self.user_context is None:
            self.user_context = []


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

    def __init__(self, model: str = "claude-3-5-sonnet-20241022"):
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
            context: Project context (blocks + documents)
            parameters: Optional agent-specific parameters

        Returns:
            AgentResult with output or error
        """
        pass

    def build_context_prompt(self, context: ContextBundle) -> str:
        """Build context section for system prompt."""
        if not context.blocks:
            return "No context available."

        lines = ["## Available Context\n"]
        for block in context.blocks:
            lines.append(f"### {block.block_type.upper()}")
            lines.append(block.content)
            lines.append("")

        return "\n".join(lines)

"""
Base agent interface and shared types

ADR-005: Unified memory architecture with embeddings
ADR-009: Work and agent orchestration
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
    Structured output from agent work.

    ADR-009: Work outputs are the deliverables from agent execution.
    Each output has:
    - type: finding, recommendation, insight, draft, report
    - title: Brief summary
    - body: Structured content
    - confidence: 0-1 score
    - source_refs: Memory/document IDs used (provenance)
    """
    output_type: str  # finding, recommendation, insight, draft, report
    title: str
    body: dict  # Structured content {summary, details, evidence, implications}
    confidence: float = 0.8
    source_refs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dict for database storage."""
        return {
            "output_type": self.output_type,
            "title": self.title,
            "content": json.dumps(self.body) if isinstance(self.body, dict) else self.body,
            "confidence": self.confidence,
            "source_refs": self.source_refs,
        }


@dataclass
class AgentResult:
    """Result from agent execution"""
    success: bool
    output_type: str  # text, file, work_outputs
    content: Optional[str] = None
    file_path: Optional[str] = None
    title: Optional[str] = None
    error: Optional[str] = None

    # Work outputs (ADR-009)
    work_outputs: list[WorkOutput] = field(default_factory=list)

    # Token tracking
    input_tokens: int = 0
    output_tokens: int = 0


# Tool definitions for work agents (ADR-009)
EMIT_WORK_OUTPUT_TOOL = {
    "name": "emit_work_output",
    "description": """Emit a structured work output for user review.

Use this tool to record your findings, recommendations, insights, or draft content.
Each output you emit will be stored and made available for user review.

IMPORTANT: You MUST use this tool for EVERY significant finding or output you generate.
Do not just describe your findings in text - emit them as structured outputs.

When to use:
- You discover a new fact or finding (output_type: "finding")
- You want to suggest an action (output_type: "recommendation")
- You identify a pattern or insight (output_type: "insight")
- You draft content for review (output_type: "draft")
- You create a report section (output_type: "report")""",
    "input_schema": {
        "type": "object",
        "properties": {
            "output_type": {
                "type": "string",
                "description": "Type of output: finding, recommendation, insight, draft, report",
                "enum": ["finding", "recommendation", "insight", "draft", "report"]
            },
            "title": {
                "type": "string",
                "description": "Brief title summarizing the output (2-10 words)"
            },
            "body": {
                "type": "object",
                "description": "Structured content of the output",
                "properties": {
                    "summary": {"type": "string", "description": "1-2 sentence summary"},
                    "details": {"type": "string", "description": "Full detailed content"},
                    "evidence": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Supporting evidence or sources"
                    },
                    "implications": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "What this means for the user"
                    }
                },
                "required": ["summary", "details"]
            },
            "confidence": {
                "type": "number",
                "description": "Confidence score from 0.0 to 1.0 based on evidence quality",
                "minimum": 0.0,
                "maximum": 1.0
            },
            "source_memory_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "IDs of memories used as sources (for provenance)"
            }
        },
        "required": ["output_type", "title", "body", "confidence"]
    }
}


class BaseAgent(ABC):
    """
    Base class for all work agents.

    Subclasses must implement execute() method.

    ADR-009: Work agents produce structured outputs via emit_work_output tool.
    """

    AGENT_TYPE: str = "base"
    SYSTEM_PROMPT: str = ""

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        self.model = model
        self.tools = [EMIT_WORK_OUTPUT_TOOL]

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

    def _parse_work_outputs(self, tool_calls: list[dict]) -> list[WorkOutput]:
        """Parse emit_work_output tool calls into WorkOutput objects."""
        outputs = []
        for call in tool_calls:
            if call.get("name") == "emit_work_output":
                input_data = call.get("input", {})
                outputs.append(WorkOutput(
                    output_type=input_data.get("output_type", "finding"),
                    title=input_data.get("title", "Untitled"),
                    body=input_data.get("body", {}),
                    confidence=input_data.get("confidence", 0.5),
                    source_refs=input_data.get("source_memory_ids", []),
                ))
        return outputs

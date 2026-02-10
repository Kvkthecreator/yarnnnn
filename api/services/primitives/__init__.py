"""
Primitives Architecture (ADR-036/037 Alignment)

Universal agent primitives mirroring Claude Code patterns:
- Read: Retrieve entity by reference
- Write: Create new entity
- Edit: Modify existing entity
- Search: Find by content (semantic)
- List: Find by structure
- Execute: External operations
- Todo: Track intent/progress

These primitives operate on YARNNN entities (deliverables, platforms, memories, etc.)
rather than files, but follow the same interface contract.
"""

from .refs import EntityRef, parse_ref, resolve_ref
from .registry import PRIMITIVES, execute_primitive

__all__ = [
    "EntityRef",
    "parse_ref",
    "resolve_ref",
    "PRIMITIVES",
    "execute_primitive",
]

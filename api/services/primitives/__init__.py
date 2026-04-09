"""
Primitives Architecture (ADR-146: Hardened)

Two explicit mode registries (CHAT_PRIMITIVES, HEADLESS_PRIMITIVES).
14 chat tools, 17 headless tools. Key consolidations:
- UpdateContext: identity, brand, memory, agent feedback, task feedback
- ManageTask: trigger, update, pause, resume
- CreateTask: complex registry-aware creation (separate)
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

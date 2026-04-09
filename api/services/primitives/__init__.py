"""
Primitives Architecture (ADR-146: Hardened, ADR-168: Matrix + Naming Reform)

Two explicit mode registries (CHAT_PRIMITIVES, HEADLESS_PRIMITIVES).
Canonical reference: docs/architecture/primitives-matrix.md (ADR-168).

Key consolidations:
- UpdateContext (ADR-146): identity, brand, memory, agent feedback, task feedback, awareness
- ManageTask (ADR-146 + ADR-149 + ADR-168): create, trigger, update, pause, resume, evaluate, steer, complete
- Execute primitive dissolved (ADR-168 Commit 2) — actions absorbed into ManageTask/UpdateContext
- CreateTask primitive dissolved (ADR-168 Commit 3) — folded into ManageTask(action="create")
  for symmetry with ManageAgent
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

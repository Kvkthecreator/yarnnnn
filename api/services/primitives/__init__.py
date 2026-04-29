"""
Primitives Architecture (ADR-146: Hardened, ADR-168: Matrix + Naming Reform)

Two explicit mode registries (CHAT_PRIMITIVES, HEADLESS_PRIMITIVES).
Canonical reference: docs/architecture/primitives-matrix.md (ADR-168).

Key consolidations + dissolutions:
- UpdateContext: dissolved (ADR-235). Inference-merged writes → InferContext /
  InferWorkspace; substrate writes → WriteFile(scope="workspace"); recurrence
  lifecycle → ManageRecurrence.
- ManageTask: dissolved (ADR-231 Phase 3.7). Lifecycle split into
  ManageRecurrence + FireInvocation.
- Execute primitive dissolved (ADR-168 Commit 2) — actions absorbed into the
  Manage* lifecycle primitives.
- CreateTask primitive dissolved (ADR-168 Commit 3) — folded into ManageTask;
  ManageTask itself then dissolved per ADR-231.
- ManageAgent action enum tightened (ADR-235 D2): no chat-surface 'create'.
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

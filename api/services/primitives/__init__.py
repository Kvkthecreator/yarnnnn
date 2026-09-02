"""
Primitives Architecture (ADR-146: Hardened, ADR-168: Matrix + Naming Reform)

One dispatch table (HANDLERS) + the derived PRIMITIVES list (ADR-632: the
steward's mode rosters are deleted; the live surfaces declare their own).
Canonical reference: docs/architecture/primitives-matrix.md (ADR-168).

Key consolidations + dissolutions:
- UpdateContext: dissolved (ADR-235). Inference-merged writes → InferContext
  (InferWorkspace removed per ADR-314 D4 — first-act scaffold dissolved by
  Direction A); substrate writes → WriteFile(scope="workspace"); recurrence
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

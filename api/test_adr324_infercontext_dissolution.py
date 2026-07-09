"""ADR-324 regression gate — InferContext dissolution.

Asserts:
  (a) InferContext is gone from CHAT_PRIMITIVES + HANDLERS.
  (b) infer_context.py module is deleted.
  (c) context_inference exposes author_identity_merge (renamed) + author_identity
      (the relocated workflow).
  (d) MCP composition layer does not dispatch the dissolved InferContext
      primitive. (ADR-368 removed the identity/brand→author_identity routing;
      ADR-432 D1c retired Brand — the surviving invariant is just "no InferContext".)
  (e) grep gate — no live `execute_primitive(..., "InferContext"` dispatch and no
      `INFER_CONTEXT_TOOL` reference in registry.

Run: python -m pytest api/test_adr324_infercontext_dissolution.py -q
"""
from __future__ import annotations

from pathlib import Path

API = Path(__file__).parent


def _read(*parts: str) -> str:
    return (API / Path(*parts)).read_text()


def test_infercontext_not_in_chat_primitives():
    from services.primitives.registry import CHAT_PRIMITIVES
    names = {t["name"] for t in CHAT_PRIMITIVES}
    assert "InferContext" not in names, "InferContext must be removed from CHAT_PRIMITIVES (ADR-324)."


def test_infercontext_not_in_handlers():
    from services.primitives.registry import HANDLERS
    assert "InferContext" not in HANDLERS, "InferContext must be removed from HANDLERS (ADR-324)."


def test_infer_context_module_deleted():
    assert not (API / "services" / "primitives" / "infer_context.py").exists(), (
        "infer_context.py must be deleted (ADR-324 — InferContext dissolved)."
    )


def test_author_identity_helpers_present():
    from services import context_inference
    assert hasattr(context_inference, "author_identity_merge"), (
        "context_inference.author_identity_merge (renamed from infer_shared_context) must exist."
    )
    assert hasattr(context_inference, "author_identity"), (
        "context_inference.author_identity (relocated workflow) must exist."
    )
    # The old name is gone (Singular Implementation).
    assert not hasattr(context_inference, "infer_shared_context"), (
        "infer_shared_context must be renamed to author_identity_merge (no alias)."
    )


def test_mcp_does_not_dispatch_infercontext():
    # ADR-324 gated that the MCP path did NOT dispatch execute_primitive("InferContext").
    # ADR-368 (memory-first interop) then removed the identity/brand routing to
    # author_identity entirely — `remember` now writes a raw observation to the
    # inbound/ lane (no focused inference sub-call). ADR-432 D1c retired Brand.
    # So the surviving, current invariant is simply: the MCP composition layer
    # must not dispatch the dissolved InferContext primitive.
    src = _read("services", "mcp_composition.py")
    assert 'execute_primitive(\n            auth,\n            "InferContext"' not in src
    assert '"InferContext"' not in src, (
        "mcp_composition must not reference the dissolved InferContext primitive."
    )


def test_no_live_infercontext_dispatch():
    # No module may dispatch InferContext via execute_primitive.
    import re
    offenders = []
    for parts in [
        ("services", "mcp_composition.py"),
        ("services", "primitives", "registry.py"),
        ("routes", "feed.py"),
        ("agents", "cockpit_awareness.py"),
    ]:
        src = _read(*parts)
        # live dispatch pattern: execute_primitive(..., "InferContext"
        if re.search(r'execute_primitive\([^)]*"InferContext"', src):
            offenders.append("/".join(parts))
    assert not offenders, f"Live InferContext dispatch remains in: {offenders}"


def test_infer_context_tool_not_referenced_in_registry():
    src = _read("services", "primitives", "registry.py")
    # No live import or list-entry of INFER_CONTEXT_TOOL (comments naming it are OK).
    import re
    # A bare INFER_CONTEXT_TOOL on its own line (list entry) or `import ... INFER_CONTEXT_TOOL`
    assert not re.search(r"^\s*INFER_CONTEXT_TOOL,\s*$", src, re.MULTILINE), (
        "INFER_CONTEXT_TOOL must not be a live CHAT_PRIMITIVES entry (ADR-324)."
    )
    assert "import INFER_CONTEXT_TOOL" not in src, (
        "INFER_CONTEXT_TOOL import must be removed (ADR-324)."
    )

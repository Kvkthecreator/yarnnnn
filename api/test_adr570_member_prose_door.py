"""ADR-570 gate — the member prose door and the studio door's principal gate.

Two claims, tested at two altitudes:

1. BEHAVIOR — `is_prose_document` is the format class (real calls, not source
   inspection): prose extensions in, machine leaves and traversal out.
2. WIRING (AST, never string-matching) — both member write doors compose the
   per-principal gate: `edit_workspace_file` and `write_artifact` each contain
   an `if` whose test calls `_is_path_locked_for_principal` and whose body
   raises. The studio door's gate must sit BEFORE its `write_revision` call —
   the ADR-501 S1 hole this arc repaired was exactly that call being absent.

Falsified during authoring by neutering each gate branch and watching the
matching test go red (the ADR-495 lesson: a gate that tests the resolver but
not the wiring ships green through a dead call site).

Run: cd api && python3 -m pytest test_adr570_member_prose_door.py -q
"""

import ast
from pathlib import Path

API = Path(__file__).parent


# ---------------------------------------------------------------------------
# 1. The format class, by real calls
# ---------------------------------------------------------------------------

def test_prose_class_accepts_prose_anywhere():
    from services.workspace_paths import is_prose_document

    assert is_prose_document("/workspace/marketing/video/human-clipboard/transcript.md")
    assert is_prose_document("/workspace/Documents/notes.markdown")
    assert is_prose_document("/workspace/operation/briefs/q3.txt")
    assert is_prose_document("/workspace/constitution/MANDATE.md")  # WHERE is the principal gate's question
    assert is_prose_document("uploads/readme.MD")  # case-insensitive ext


def test_prose_class_refuses_machine_and_traversal():
    from services.workspace_paths import is_prose_document

    assert not is_prose_document("/workspace/operation/_recurrences.yaml")
    assert not is_prose_document("/workspace/x/data.json")
    assert not is_prose_document("/workspace/x/page.html")
    assert not is_prose_document("/workspace/x/_feedback.md")  # underscore leaf = machine-tended (ADR-254)
    assert not is_prose_document("/workspace/../etc/passwd.md")
    assert not is_prose_document("/workspace/x/photo.png")


def test_prose_door_composes_the_one_carve_law():
    """The door's composition (class AND carves) keeps raw inbound/ and
    system/ closed without a parallel carve list."""
    from services.workspace_paths import is_prose_document, operator_can_organize

    def door(path: str) -> bool:
        return is_prose_document(path) and operator_can_organize(path)

    assert door("marketing/video/transcript.md")
    assert door("inbound/uploads/pasted.md")  # the HUMAN raw lane stays editable
    assert not door("inbound/mcp/claude/observation.md")  # raw intake: retained, never rewritten
    assert not door("system/notes.md")  # runtime state carve


# ---------------------------------------------------------------------------
# 2. The wiring, by AST
# ---------------------------------------------------------------------------

def _function_body(module_path: Path, func_name: str) -> ast.AST:
    tree = ast.parse(module_path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
            return node
    raise AssertionError(f"{func_name} not found in {module_path}")


def _calls_in(node: ast.AST) -> list:
    out = []
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            f = n.func
            name = getattr(f, "id", None) or getattr(f, "attr", None)
            out.append((name, n.lineno))
    return out


def _has_guard_branch(func: ast.AST, gate_name: str) -> int:
    """Line of an `if` whose TEST calls `gate_name` and whose body raises.

    Branch extraction, not expression/string matching — and a boolean
    Constant anywhere in the test disqualifies it: `if False and gate(...)`
    keeps the call visible while the branch is dead (found by this gate's
    own falsification run, 2026-08-14)."""
    for n in ast.walk(func):
        if isinstance(n, ast.If):
            test_calls = {name for name, _ in _calls_in(n.test)}
            has_bool_const = any(
                isinstance(c, ast.Constant) and isinstance(c.value, bool)
                for c in ast.walk(n.test)
            )
            if gate_name in test_calls and not has_bool_const and any(
                isinstance(b, ast.Raise) for b in ast.walk(ast.Module(body=n.body, type_ignores=[]))
            ):
                return n.lineno
    raise AssertionError(f"no live guard branch calling {gate_name} with a raising body")


def test_workspace_door_gates_principal_and_uses_the_class():
    func = _function_body(API / "routes" / "workspace.py", "edit_workspace_file")
    _has_guard_branch(func, "_is_path_locked_for_principal")
    call_names = {name for name, _ in _calls_in(func)}
    assert "is_prose_document" in call_names, (
        "edit_workspace_file no longer consults the ADR-570 prose class — "
        "the member prose door has been narrowed or forked"
    )
    assert "operator_can_organize" in call_names, (
        "the prose class must compose the standing carve law (system/, raw "
        "inbound/), not ship without it"
    )


def test_studio_door_gates_principal_before_writing():
    func = _function_body(API / "routes" / "studio.py", "write_artifact")
    gate_line = _has_guard_branch(func, "_is_path_locked_for_principal")
    write_lines = [ln for name, ln in _calls_in(func) if name == "write_revision"]
    assert write_lines, "write_artifact no longer calls write_revision?"
    assert gate_line < min(write_lines), (
        "the per-principal gate must run BEFORE write_revision — a gate after "
        "the write is a receipt, not a gate (ADR-501 S1)"
    )

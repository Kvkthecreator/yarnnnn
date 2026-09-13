"""Gate — no function in the system reads a GLOBAL name the module never binds.

Born 2026-09-12 (ADR-649 §5): the folder-create door raised NameError on prod
for five days because a refactor un-imported a name and left one caller. The
same sweep then found five more — the image export's two bounds (deleted with
a neighbouring block), the Resend webhook's `hashlib`, a renamed `row` still
read as `rows`, a selector default defined only in a sibling module, a mandate
read that was never loaded. Each was a 500 waiting for its first caller, and
no behaviour gate could see any of them: a door that is never DRIVEN never
raises.

Mechanism: `symtable` marks a name a function reads without binding as
GLOBAL; if the module binds nothing by that name at top level and it is not a
builtin, the first call raises NameError. Pure source analysis, no imports —
so it runs in any environment and cannot be fooled by a module that imports
cleanly (a module-level import succeeding says nothing about function bodies).

The allowlist names DECISIONS, not accidents: each entry is a known leftover
with its reason, and the gate ALSO fails when an allowlisted name stops being
flagged — a fixed entry must leave the list, or the list decays into a blind
spot (the ADR-501 `_enumerated_ok` pattern).

Run:  cd api && python3 -B -m pytest -q test_no_undefined_names.py
"""
from __future__ import annotations

import ast
import builtins
import pathlib
import symtable

import pytest

API = pathlib.Path(__file__).resolve().parent
ROOTS = ("routes", "services", "jobs", "integrations", "mcp_server")

# relpath → {name: why it is still here}
ALLOWED: dict[str, dict[str, str]] = {
    "services/primitives/write.py": {
        "_process_agent": (
            "the 'agent' entity branch of the write primitive — the pre-ADR-596 "
            "agent model is DELETED (mig 248) and `_process_agent` went with it, "
            "but the primitive still lists 'agent' as an entity kind. Removing "
            "the kind is the ADR-596 D3(d) follow-up; until then this branch is "
            "a documented NameError, not a hidden one."
        ),
    },
    "services/operator_proxy/scenarios.py": {
        n: "Hat-B harness: `establish_substrate` references a set of helpers that "
           "no longer exist in this module (half-retired evaluation scaffolding, "
           "out of system canon). Repair or delete it in an evaluations pass."
        for n in ("_establish_field_equals", "_read", "_y", "client", "load_workspace_yaml", "loop", "norm", "value")
    },
}

_IMPLICIT = {"__file__", "__name__", "__doc__", "__spec__", "__builtins__", "__package__", "__loader__"}


def _module_bindings(tree: ast.Module) -> set[str]:
    """Every name the module binds at top level (imports, defs, assignments —
    including inside top-level if/try/with/for blocks)."""
    names: set[str] = set()
    for node in tree.body:
        for n in ast.walk(node):
            if isinstance(n, (ast.Import, ast.ImportFrom)):
                for a in n.names:
                    names.add((a.asname or a.name).split(".")[0])
            elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.add(n.name)
            elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                names.add(n.id)
            elif isinstance(n, ast.Global):
                names.update(n.names)
            # a nested def/class binds INSIDE its parent, not at module level —
            # but ast.walk from a top-level def would also visit its body; only
            # the top-level node's OWN name matters there, so stop descending.
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                break
    return names


def sweep(path: pathlib.Path) -> dict[str, list[str]]:
    """{undefined name: [function names that read it]}"""
    src = path.read_text()
    bound = _module_bindings(ast.parse(src)) | set(dir(builtins)) | _IMPLICIT
    out: dict[str, list[str]] = {}

    def walk(tab: symtable.SymbolTable) -> None:
        for child in tab.get_children():
            if child.get_type() == "function":
                for sym in child.get_symbols():
                    if sym.is_global() and sym.is_referenced() and not sym.is_assigned() and sym.get_name() not in bound:
                        out.setdefault(sym.get_name(), []).append(child.get_name())
            walk(child)

    walk(symtable.symtable(src, str(path), "exec"))
    return out


def _files():
    for root in ROOTS:
        base = API / root
        if not base.exists():
            continue
        for p in sorted(base.rglob("*.py")):
            if "venv" in p.parts or p.name.startswith("test_"):
                yield p if False else None
                continue
            yield p


FILES = [p for p in _files() if p is not None]


@pytest.mark.parametrize("path", FILES, ids=[str(p.relative_to(API)) for p in FILES])
def test_every_global_read_is_bound(path: pathlib.Path):
    rel = str(path.relative_to(API))
    found = sweep(path)
    allowed = ALLOWED.get(rel, {})
    unexpected = {n: fns for n, fns in found.items() if n not in allowed}
    assert not unexpected, (
        f"{rel}: names read as GLOBAL that nothing binds — a NameError on first call: "
        f"{unexpected}. Bind it (import/define) or, for a deliberate leftover, allowlist it WITH its reason."
    )
    stale = set(allowed) - set(found)
    assert not stale, f"{rel}: allowlisted names no longer flagged — remove them from ALLOWED: {sorted(stale)}"


def test_the_allowlist_names_only_files_that_exist():
    missing = [rel for rel in ALLOWED if not (API / rel).exists()]
    assert not missing, f"ALLOWED cites files that are gone: {missing}"


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-q"]))

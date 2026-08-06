"""ADR-522 regression gate — the turn core THREADS focus, never closes over `req`.

The defect this exists to catch (prod, 2026-08-07): ADR-522 D2 added
`focus=req.focus...` inside `_turn_stream_response`, a module-level helper that
has no `req` parameter. `req` lives only on the `lane_turn` route handler, so
the reference resolved against nothing and every lane turn died with
`name 'req' is not defined` — surfaced to the member as a red line in the
transcript. Not a focus-only edge case: the NameError fired before focus was
ever consulted, so turns that declared NO focus broke identically.

The general shape (worth naming, because it recurs): a route handler's request
object is NOT in scope in the helper it delegates to. Per-turn request state
must be threaded as an explicit parameter. A helper reaching for a name it does
not bind is the tell.

This is an AST gate, not a text gate — it resolves names against what each
function actually binds, so it cannot be satisfied by a comment that happens to
mention `req`, and it does not pin any spelling of the call expression.
"""

import ast
import builtins
import os

LANES = os.path.join(os.path.dirname(__file__), "routes", "lanes.py")
TURN_CORE = "_turn_stream_response"


def _module_names(tree: ast.Module) -> set:
    """Everything resolvable at module scope: imports, defs, classes, globals."""
    names = set(dir(builtins))
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                names.add((alias.asname or alias.name).split(".")[0])
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                for sub in ast.walk(target):
                    if isinstance(sub, ast.Name):
                        names.add(sub.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


def _bound_in(fn) -> set:
    """Every name the function binds: params, assignments, imports, excepts."""
    bound = set()
    for node in ast.walk(fn):
        if isinstance(node, ast.arg):
            bound.add(node.arg)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            bound.add(node.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            bound.add(node.name)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            bound.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                bound.add((alias.asname or alias.name).split(".")[0])
    return bound


def _unresolved(fn, module_names: set) -> list:
    bound = _bound_in(fn)
    out = []
    for node in ast.walk(fn):
        if (
            isinstance(node, ast.Name)
            and isinstance(node.ctx, ast.Load)
            and node.id not in bound
            and node.id not in module_names
        ):
            out.append((node.lineno, node.id))
    return out


def test_turn_core_has_no_unresolved_names():
    """The exact defect: `req` (or any name) loaded but never bound."""
    tree = ast.parse(open(LANES).read())
    module_names = _module_names(tree)
    fn = next(
        n
        for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == TURN_CORE
    )
    bad = _unresolved(fn, module_names)
    assert not bad, (
        f"{TURN_CORE} loads name(s) it never binds: {bad}. A route handler's "
        "request object is not in scope here — thread per-turn state in as an "
        "explicit parameter (see this file's docstring)."
    )


def test_turn_core_accepts_focus_as_a_parameter():
    """Focus must arrive as a parameter — the mechanism, not just the absence
    of a NameError. Without this, deleting the focus line entirely would pass
    the gate above while silently dropping ADR-522."""
    tree = ast.parse(open(LANES).read())
    fn = next(
        n
        for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == TURN_CORE
    )
    params = {a.arg for a in fn.args.args + fn.args.kwonlyargs + fn.args.posonlyargs}
    assert "focus" in params, (
        f"{TURN_CORE} must take `focus` as an explicit parameter — ADR-522 D2's "
        "per-turn focus is threaded from the request, never closed over."
    )


def test_no_route_handler_state_leaks_into_module_helpers():
    """The general shape, module-wide: no top-level function may load a name
    nothing binds. Catches the next helper that reaches for `req`/`auth`/etc."""
    tree = ast.parse(open(LANES).read())
    module_names = _module_names(tree)
    offenders = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            bad = _unresolved(node, module_names)
            if bad:
                offenders[node.name] = bad
    assert not offenders, (
        f"function(s) load names they never bind: {offenders}. Each is a "
        "NameError the moment that line executes."
    )


if __name__ == "__main__":
    test_turn_core_has_no_unresolved_names()
    test_turn_core_accepts_focus_as_a_parameter()
    test_no_route_handler_state_leaks_into_module_helpers()
    print("ADR-522 focus-threading gate: 3/3 PASS")

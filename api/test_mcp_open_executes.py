"""The MCP read path EXECUTES — module-scope names resolve, and the verbs run.

Run: `python3 test_mcp_open_executes.py` from `api/`.

WHY THIS EXISTS (2026-08-22)

Every MCP `open` in production returned
`error: read_failed, message: name 'live_files_filter' is not defined` —
workspace-wide, every file, every caller. The cause: commit 49a8fac meant to
widen a module-level import in `services/mcp_composition.py` and instead
widened the import INSIDE `_substrate_scope`'s body, so `live_files_filter`
and `describe_if_trashed` became function-locals while `compose_open` reads
them at module scope. The module still IMPORTS clean, every textual gate that
greps for the names still finds them, and the failure only exists when the
coroutine actually runs — the doorway, not the room.

Two defenses, both behavioural:

  [1] an AST resolver proves every module-scope name a function loads is
      actually bound at module scope (catches the whole class, any function);
  [2] `compose_open` is EXECUTED — found, miss, and trashed branches — against
      a stub client, so the read path is proven to run, not merely to parse.

  [3] guards the neighbouring defect found in the same sweep: QueryKnowledge
      and SearchFiles resolved the workspace with a bare
      `effective_workspace_id(auth.user_id)` — no explicit binding — which the
      contextvar never rescues on this path (ADR-548 D8), so an MCP `search`
      bound to a non-default workspace swept the principal's default one and
      returned confident zero-matches for files `list` could see.
"""

from __future__ import annotations

import ast
import asyncio
import builtins
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent))

_API = Path(__file__).parent

PASSED = 0
FAILED: list[str] = []


def check(label: str, cond: bool, detail: str = "") -> None:
    global PASSED
    if cond:
        print(f"  ok   {label}")
        PASSED += 1
    else:
        print(f"  FAIL {label}{(' — ' + detail) if detail else ''}")
        FAILED.append(label)


# =============================================================================
# [1] every module-scope name a function loads is bound at module scope
# =============================================================================
# The generic form of the outage: an import swallowed into one function's body
# leaves every OTHER function's use of the name unbound, while `import module`
# stays green and every grep still matches. Only name RESOLUTION sees it.

print("\n[1] mcp_composition: module-scope name resolution (the outage's class)")


def _module_scope_names(tree: ast.Module) -> set:
    names = set(dir(builtins))
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names:
                names.add(a.asname or a.name.split(".")[0])
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    names.add(t.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


def _locally_bound(fn) -> set:
    bound = set()
    for n in ast.walk(fn):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n is not fn:
            bound.add(n.name)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names:
                bound.add(a.asname or a.name.split(".")[0])
        elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
            bound.add(n.id)
        elif isinstance(n, ast.arg):
            bound.add(n.arg)
        elif isinstance(n, ast.ExceptHandler) and n.name:
            bound.add(n.name)
        elif isinstance(n, ast.Global):
            bound.update(n.names)
    return bound


def unbound_loads(path: Path) -> list:
    tree = ast.parse(path.read_text())
    mod = _module_scope_names(tree)
    problems = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            bound = _locally_bound(node)
            for n in ast.walk(node):
                if (
                    isinstance(n, ast.Name)
                    and isinstance(n.ctx, ast.Load)
                    and n.id not in bound
                    and n.id not in mod
                ):
                    problems.append((node.name, n.id, n.lineno))
    return sorted(set(problems), key=lambda p: p[2])


_problems = unbound_loads(_API / "services" / "mcp_composition.py")
check(
    "every name every function loads resolves (module scope or local)",
    not _problems,
    f"unresolvable at runtime: {_problems} — this is exactly how every `open` "
    "died with NameError while imports and greps stayed green",
)

# Control: the resolver is not vacuous — it must flag a synthetic module whose
# function loads a name bound only inside a SIBLING function (the outage shape).
_synthetic = ast.parse(
    "def a():\n    from os import sep\n    return sep\n"
    "def b():\n    return sep\n"
)
_ctl = []
_mod = _module_scope_names(_synthetic)
for _node in _synthetic.body:
    _bound = _locally_bound(_node)
    for _n in ast.walk(_node):
        if (
            isinstance(_n, ast.Name)
            and isinstance(_n.ctx, ast.Load)
            and _n.id not in _bound
            and _n.id not in _mod
        ):
            _ctl.append((_node.name, _n.id))
check(
    "control: the resolver flags the sibling-function-import shape",
    ("b", "sep") in _ctl,
    "a resolver that cannot fail cannot defend anything",
)


# =============================================================================
# [2] compose_open RUNS — found, miss, and trashed branches
# =============================================================================

print("\n[2] compose_open executes against a stub substrate")

from services.mcp_composition import compose_open  # noqa: E402


class _Result(SimpleNamespace):
    pass


from services.workspace_context import LIVE_FILES_OR_CLAUSE  # noqa: E402


class _Query:
    """PostgREST query double: chainable; execute() serves rows.

    `.or_()` HONOURS the canonical live-files clause — so the trashed-branch
    check below proves compose_open's query actually APPLIES the filter, not
    merely that the stub returned whatever it was given.
    """

    def __init__(self, rows):
        self._rows = rows

    def or_(self, clause):
        if clause == LIVE_FILES_OR_CLAUSE:
            self._rows = [
                r for r in self._rows if r.get("lifecycle") != "archived"
            ]
        return self

    def __getattr__(self, name):
        if name == "execute":
            return lambda: _Result(data=list(self._rows))
        return lambda *a, **k: self


class _Client:
    def __init__(self, rows):
        self._rows = rows

    def table(self, name):
        return _Query(self._rows)

    def rpc(self, *a, **k):
        return _Query([])


def _auth(rows):
    # workspace_id is EXPLICIT so effective_workspace_id short-circuits on the
    # binding and never reaches supabase (also the correct MCP shape, ADR-573).
    return SimpleNamespace(
        user_id="00000000-0000-0000-0000-000000000001",
        workspace_id="00000000-0000-0000-0000-000000000002",
        client=_Client(rows),
    )


_live_row = {
    "path": "/workspace/operation/probe.md",
    "content": "probe body",
    "updated_at": "2026-08-22T00:00:00Z",
    "content_type": "text/markdown",
    "lifecycle": None,
    "metadata": {},
}

_found = asyncio.run(compose_open(_auth([_live_row]), "operation/probe.md"))
check(
    "a live file OPENS (the branch production could not reach)",
    _found.get("success") is True and _found.get("found") is True,
    f"got {_found.get('error')}: {_found.get('message')}",
)
check(
    "…and the content comes back",
    _found.get("content") == "probe body",
)
check(
    "…never the outage envelope",
    _found.get("error") != "read_failed"
    and "is not defined" not in str(_found.get("message", "")),
    "read_failed + NameError is the exact production symptom this gate pins",
)

_miss = asyncio.run(compose_open(_auth([]), "operation/absent.md"))
check(
    "a miss executes the trashed-check branch and answers found: false",
    _miss.get("success") is True and _miss.get("found") is False,
    f"got {_miss!r} — describe_if_trashed is the SECOND name the swallowed "
    "import unbound; the miss branch is where it runs",
)

_trashed_row = dict(
    _live_row,
    lifecycle="archived",
    metadata={"trashed_with": None},
)
_trash = asyncio.run(compose_open(_auth([_trashed_row]), "operation/probe.md"))
check(
    "a trashed row is NAMED as trashed, and its content is not served",
    _trash.get("found") is False
    and _trash.get("trashed") is True
    and "probe body" not in str(_trash.get("content", "")),
    f"got {_trash!r} — trash-not-erase: the row exists, the file is not live, "
    "and the caller must be told which (never a bare not-found)",
)


# =============================================================================
# [3] the workspace binding is PASSED, never inferred, on the search paths
# =============================================================================
# ADR-548 D8: the contextvar does not arrive here, so a bare
# `effective_workspace_id(auth.user_id)` silently resolves the caller's
# DEFAULT workspace. `search` then confidently reports zero matches for files
# `list` (which passes the binding) can see — the incorrect-success class.

print("\n[3] no bare effective_workspace_id(auth.user_id) on auth-holding paths")

for _rel in (
    Path("services") / "primitives" / "workspace.py",
    Path("services") / "mcp_composition.py",
):
    _tree = ast.parse((_API / _rel).read_text())
    _bare = []
    for _n in ast.walk(_tree):
        if (
            isinstance(_n, ast.Call)
            and isinstance(_n.func, ast.Name)
            and _n.func.id == "effective_workspace_id"
            and len(_n.args) + len(_n.keywords) < 2
        ):
            _bare.append(_n.lineno)
    check(
        f"{_rel}: every effective_workspace_id call passes the binding",
        not _bare,
        f"bare single-arg calls at lines {_bare} — the shape ADR-501 §6a "
        "lesson 4 already paid for five times",
    )


print(f"\n{'=' * 60}")
if FAILED:
    print(f"FAILED {len(FAILED)}/{PASSED + len(FAILED)}: {FAILED}")
    sys.exit(1)
print(f"ALL PASS — {PASSED}/{PASSED}")

"""Probe/eval-harness staleness gate — the 2026-07-31 eval-suite audit.

A probe nothing exercises rots green. Receipts, both from this audit arc:
  - probe_envelope_collapse_local shipped 28 days dead (deleted-module import
    inside a function body + a deleted env toggle) — found only when a session
    tried to use it (deleted, bf98d84).
  - 9 probes carried `Recurrence(mode=...)` for 30 days after ADR-393 deleted
    the field (2026-07-01; probes last touched 06-29). All 39 probe modules
    IMPORT clean — the break is runtime-shaped, so an import check alone would
    have stayed green over every one of them.

Two pure-AST layers over api/scripts/operator/*.py (no execution, no DB):

  1. IMPORT RESOLUTION at every depth — module-level AND function-local.
     `from services.settle import x` inside a function body ships import-green
     (the ADR-507 lesson); this walks the whole tree and verifies both the
     module and each imported NAME against the target file's AST.
  2. CONSTRUCTOR KWARGS vs the LIVE dataclass — every `Recurrence(...)` call's
     keywords must be fields of the real `services.recurrence.Recurrence`.
     Derived from the class, not a hardcoded list, so the gate tracks the code.

Enumerated per file (a counting gate cannot defend a per-site invariant); a
failure names the probe, the line, and the dead reference.

Run: python -m pytest api/test_probe_staleness_gate.py -q
"""
from __future__ import annotations

import ast
import os

_API = os.path.dirname(os.path.abspath(__file__))
PROBE_DIR = os.path.join(_API, "scripts", "operator")
PROJECT_ROOTS = ("services", "agents", "routes", "jobs", "integrations",
                 "mcp_server", "scripts")


def _probe_files() -> list[str]:
    return sorted(
        f for f in os.listdir(PROBE_DIR)
        if f.endswith(".py") and f != "__init__.py"
    )


def _module_path(dotted: str) -> str | None:
    """Resolve a project-root dotted module to a file/package path, or None."""
    rel = dotted.replace(".", "/")
    for cand in (os.path.join(_API, rel + ".py"),
                 os.path.join(_API, rel, "__init__.py")):
        if os.path.exists(cand):
            return cand
    if os.path.isdir(os.path.join(_API, rel)):
        return os.path.join(_API, rel)
    return None


def _toplevel_names(pyfile: str) -> set[str]:
    """Top-level defs/classes/assign targets of a module, via AST."""
    tree = ast.parse(open(pyfile, encoding="utf-8").read())
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    names.add(t.id)
                elif isinstance(t, ast.Tuple):
                    names.update(e.id for e in t.elts if isinstance(e, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names:
                names.add((a.asname or a.name).split(".")[0])
    return names


def test_all_imports_resolve_at_every_depth():
    """Every project-root import in every probe — including function-local
    ones — must resolve to a live module, and every `from X import name`
    must name something the target module actually defines."""
    problems: list[str] = []
    for fn in _probe_files():
        path = os.path.join(PROBE_DIR, fn)
        tree = ast.parse(open(path, encoding="utf-8").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    root = a.name.split(".")[0]
                    if root in PROJECT_ROOTS and _module_path(a.name) is None:
                        problems.append(f"{fn}:{node.lineno} import {a.name} — module gone")
            elif isinstance(node, ast.ImportFrom) and node.module:
                root = node.module.split(".")[0]
                if root not in PROJECT_ROOTS:
                    continue
                mod = _module_path(node.module)
                if mod is None:
                    problems.append(
                        f"{fn}:{node.lineno} from {node.module} import … — module gone")
                    continue
                if mod.endswith(".py"):
                    defined = _toplevel_names(mod)
                    for a in node.names:
                        if a.name == "*":
                            continue
                        # a submodule import (`from services import wake`) is
                        # fine if the submodule file exists
                        if a.name not in defined and _module_path(
                                f"{node.module}.{a.name}") is None:
                            problems.append(
                                f"{fn}:{node.lineno} from {node.module} import "
                                f"{a.name} — name not defined there")
    assert not problems, (
        "Dead references in probes (fix or delete the probe — a broken "
        "instrument masquerading as available is worse than none):\n  "
        + "\n  ".join(problems)
    )


def test_recurrence_calls_match_live_dataclass():
    """Every `Recurrence(...)` call in every probe uses only keywords the
    LIVE dataclass defines. This is the ADR-393 break class: 9 probes carried
    `mode=` for 30 days import-green."""
    import dataclasses
    import sys
    sys.path.insert(0, _API)
    from services.recurrence import Recurrence

    live_fields = {f.name for f in dataclasses.fields(Recurrence)}
    problems: list[str] = []
    for fn in _probe_files():
        path = os.path.join(PROBE_DIR, fn)
        tree = ast.parse(open(path, encoding="utf-8").read())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            callee = node.func
            name = callee.id if isinstance(callee, ast.Name) else (
                callee.attr if isinstance(callee, ast.Attribute) else "")
            if name != "Recurrence":
                continue
            for kw in node.keywords:
                if kw.arg is not None and kw.arg not in live_fields:
                    problems.append(
                        f"{fn}:{node.lineno} Recurrence({kw.arg}=…) — not a "
                        f"field of the live dataclass {sorted(live_fields)}")
    assert not problems, (
        "Stale Recurrence constructor kwargs in probes:\n  "
        + "\n  ".join(problems)
    )

"""Gate: no script in api/scripts/ documents the invocation that crashes.

THE TRAP. `api/scripts/operator/` is a package whose name shadows the stdlib
`operator` module. Running any script in `api/scripts/` BY PATH puts that
directory first on `sys.path`, so the very next stdlib import (pathlib -> re ->
functools -> collections) resolves `operator` to the probe package and dies:

    ImportError: cannot import name 'eq' from 'operator'
                 (/Users/macbook/yarnnn/api/scripts/operator/__init__.py)

`python3 -m scripts.<name>` never adds that entry and works fine.

WHY A GATE AND NOT A RENAME. The package is referenced 111 times across 40+
files, most of them historical evaluation records that must not be rewritten to
match today's layout. So the package keeps its name and the INVOCATION is the
thing held correct — which means the rule has to be enforced, because it is
invisible until someone runs the documented command.

Reproduced 2026-09-13 (three scripts) and again 2026-09-16, when a NEWLY WRITTEN
script in this directory hit it on its first run. That is the proof the rule
needs a gate: the tax is per-file and the author who forgets finds out at import.

Two claims:
  1. No docstring in api/scripts/*.py teaches `python[3] scripts/<name>.py`.
  2. Any script that does NOT carry the sys.path guard must not be documented
     as runnable by path (the guard is the other valid way to be correct).

Run: python3 -B test_scripts_run_as_modules.py   (script-shaped — read the count)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent / "scripts"

_passed = 0
_failed = 0


def check(label: str, ok: bool) -> None:
    global _passed, _failed
    if ok:
        _passed += 1
        print(f"PASS  {label}")
    else:
        _failed += 1
        print(f"FAIL  {label}")


#: `python scripts/foo.py` or `python3 scripts/foo.py` — the form that dies.
_BY_PATH = re.compile(r"python3?\s+scripts/[A-Za-z0-9_]+\.py")
#: The guard that makes a by-path run safe, as spelled in the two scripts that
#: carry it. Assert the POP, not the mention — a comment about sys.path survives
#: deleting the line that does the work.
_GUARD = re.compile(r"sys\.path\.pop\(0\)")

scripts = sorted(p for p in SCRIPTS.glob("*.py") if p.name != "__init__.py")
check(f"found scripts to check ({len(scripts)})", len(scripts) > 0)

def module_docstring(src: str) -> str:
    """The module docstring, or "" — parsed, not guessed at with startswith().

    The first cut tested `src.lstrip().startswith('\"\"\"')`, which is FALSE for
    every script carrying a `#!/usr/bin/env python3` shebang — so the extraction
    returned "", the loop `continue`d, and the check below passed while
    measuring NOTHING. It stayed green when the defect was deliberately
    reintroduced. Caught by falsifying; fixed by asking the AST.
    """
    import ast

    try:
        return ast.get_docstring(ast.parse(src)) or ""
    except SyntaxError:
        return ""


offenders: list[str] = []
checked_docstrings = 0
for path in scripts:
    src = path.read_text()
    # Only the docstring teaches invocation; a by-path string inside code (e.g.
    # building a subprocess argv) is not an instruction to a human.
    doc = module_docstring(src)
    if not doc:
        continue
    checked_docstrings += 1
    taught = _BY_PATH.findall(doc)
    if not taught:
        continue
    # A script carrying the guard may legitimately document the by-path form.
    if _GUARD.search(src):
        continue
    offenders.append(f"{path.name}: {taught[0]}")

# COMPLETENESS FIRST. A scan that read zero docstrings reports a confident pass
# over an empty set — which is exactly what the shebang bug produced. Assert the
# corpus is non-empty before trusting the miss.
check(
    f"read a docstring from every script ({checked_docstrings}/{len(scripts)})",
    checked_docstrings == len(scripts),
)

check(
    "no unguarded script documents `python3 scripts/<name>.py`"
    + (f" — offenders: {'; '.join(offenders)}" if offenders else ""),
    not offenders,
)

# The three scripts the 2026-09-13 audit named must each now teach `-m`.
for name in ("backfill_embeddings", "purge_user_data", "refresh_connector_directory"):
    path = SCRIPTS / f"{name}.py"
    if not path.exists():
        check(f"{name}.py exists", False)
        continue
    src = path.read_text()
    check(
        f"{name}.py teaches `python3 -m scripts.{name}`",
        f"-m scripts.{name}" in src,
    )

# The guard itself, where it is used, must be the real thing.
for name in ("render_supabase_auth_templates", "print_auth_templates"):
    path = SCRIPTS / f"{name}.py"
    if not path.exists():
        continue
    src = path.read_text()
    check(
        f"{name}.py's sys.path guard pops the offending entry",
        bool(_GUARD.search(src)) and "endswith(\"scripts\")" in src,
    )

print("=" * 66)
print(f"scripts-invocation gate: {_passed}/{_passed + _failed} passed, {_failed} failed")
print("=" * 66)
sys.exit(1 if _failed else 0)

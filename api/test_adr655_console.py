"""ADR-655 gate — the console shows what is true.

Script-shaped: run it and READ THE COUNT, don't trust an exit code.

    cd api && python3 -B test_adr655_console.py

The checks are DERIVED, not enumerated, wherever derivation is possible — a
gate that spells its own expected set cannot fail on what it omits (the
`feedback_a_gate_hardcoding_a_set_cannot_fail_on_what_it_omits` class). So:

  * the route roster is read off `router.routes`, not a literal list;
  * the tables the console reads are harvested from the module's AST and each
    one is required to be non-empty on live — which is the actual ADR-655 D2
    ruling ("a figure with no live source is deleted"), not a proxy for it;
  * the retired-name ban walks the AST for real `.table("x")` / column reads,
    so the module's own prose explaining WHY a name is retired cannot satisfy
    or trip the check (`feedback_gate_assertion_matches_its_own_comment`);
  * the N+1 ban (D4) walks the AST for a query inside a `for` over rows.

The live-row checks need database credentials. Without them they SKIP LOUDLY
and the count says so — a skipped check is never reported as a pass.
"""

from __future__ import annotations

import ast
import os
import re
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parent
ADMIN_PY = API_DIR / "routes" / "admin.py"
WEB = API_DIR.parent / "web"

passed: list[str] = []
failed: list[str] = []
skipped: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    (passed if ok else failed).append(name if ok else f"{name} — {detail}")
    print(f"{'✓' if ok else '✗'} {name}" + (f" — {detail}" if detail and not ok else ""))


def skip(name: str, why: str) -> None:
    skipped.append(f"{name} — {why}")
    print(f"⊘ SKIP {name} — {why}")


ADMIN_SRC = ADMIN_PY.read_text()
ADMIN_AST = ast.parse(ADMIN_SRC)


# ---------------------------------------------------------------------------
# ① The route roster — derived from the router, never spelled
# ---------------------------------------------------------------------------
sys.path.insert(0, str(API_DIR))
try:
    import routes.admin as admin_mod  # noqa: E402

    live_paths = {r.path for r in admin_mod.router.routes}
except Exception as exc:  # pragma: no cover - import failure is the finding
    live_paths = set()
    check("① admin module imports", False, f"{type(exc).__name__}: {exc}")
else:
    check("① admin module imports", True)

# D5/D6 — the deleted routes are ABSENT. Their prefixes, not their full paths,
# so a re-addition under any spelling (/accounts, /accounts/{x}, /export/anything)
# still trips this.
RETIRED_PREFIXES = ("/accounts", "/export", "/users", "/token-usage")
resurrected = sorted(
    p for p in live_paths if any(p.startswith(pre) for pre in RETIRED_PREFIXES)
)
check(
    "② the routes ADR-655 D5/D6 deleted stay deleted",
    not resurrected,
    f"resurrected: {resurrected}",
)

# The console still serves what it promises. Derived from the module docstring's
# own endpoint list, so the docstring and the router cannot drift apart.
documented = set(re.findall(r"^- (?:GET|POST)\s+(\S+)", ADMIN_SRC, re.M))
documented = {p.replace("{id}", "{workspace_id}") for p in documented}
check(
    "③ every documented endpoint is served, and vice versa",
    documented == live_paths,
    f"docstring={sorted(documented)} router={sorted(live_paths)}",
)


# ---------------------------------------------------------------------------
# ② Retired names are not read (AST, so prose about them is not a hit)
# ---------------------------------------------------------------------------
def tables_read(tree: ast.AST) -> set[str]:
    """Every literal passed to `.table(...)` in the module."""
    out: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "table"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            out.add(node.args[0].value)
    return out


def string_constants(tree: ast.AST) -> set[str]:
    """Every string CONSTANT in real code — docstrings excluded, because a
    docstring explaining a retired name must not read as a use of it."""
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            d = ast.get_docstring(node, clean=False)
            if d:
                docstrings.add(d)
    return {
        n.value
        for n in ast.walk(tree)
        if isinstance(n, ast.Constant)
        and isinstance(n.value, str)
        and n.value not in docstrings
    }


READ_TABLES = tables_read(ADMIN_AST)
CONSTS = string_constants(ADMIN_AST)

check(
    "④ `tasks` is not read as a console metric (D2 — 0 rows on live)",
    "tasks" not in READ_TABLES,
    "routes/admin.py queries the `tasks` table again",
)
check(
    "⑤ `owner_email` is not read (D2 — the column is dropped by migration 257)",
    not any("owner_email" in c for c in CONSTS),
    "a select string still names owner_email",
)
check(
    "⑥ the retired seat is not a signal (D5 — `freddie:` is display-only)",
    not any("freddie" in c or "reviewer:" in c for c in CONSTS),
    "an authored_by prefix filter came back",
)
check(
    "⑦ no persona registry is read through the console (D5 — Hat B)",
    not any("personas" in c for c in CONSTS),
    "routes/admin.py reads the Hat-B persona registry again",
)
# Code, not prose: the module docstring NAMES `compute_cost_usd_inclusive` as
# the function the console must never re-implement, and a raw substring scan
# matched that warning — the gate accusing its own explanation
# (`feedback_gate_assertion_matches_its_own_comment`). Calls and imports only.
def _called_or_imported(tree: ast.AST) -> set[str]:
    out: set[str] = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            out.add(n.func.id)
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute):
            out.add(n.func.attr)
        elif isinstance(n, ast.ImportFrom):
            out.update(a.name for a in n.names)
        elif isinstance(n, ast.Import):
            out.update(a.name for a in n.names)
    return out


CALLED = _called_or_imported(ADMIN_AST)
cost_calls = sorted(c for c in CALLED if "cost" in c.lower() and "usd" not in c.lower())
check(
    "⑧ the console computes no cost (the standing 2026-08-21 ban)",
    not cost_calls and "compute_cost_usd_inclusive" not in CALLED,
    f"a cost computation reappeared in the console: {cost_calls}",
)


# ---------------------------------------------------------------------------
# ③ D4 — no query inside a loop over rows (the N+1 this ADR deleted)
# ---------------------------------------------------------------------------
def queries_inside_row_loops(tree: ast.AST) -> list[str]:
    """`.table(...)` in a `for` BODY — the N+1 shape the predecessor had.

    The loop's ITERATOR is explicitly not a hit: `for r in client.table(...)
    .execute().data` is ONE fetch evaluated once, which is precisely the shape
    this ADR requires. Walking the whole `ast.For` node flagged those three
    correct fetches on the first run of this gate — a gate must execute the
    shipped condition, not a plausible-looking superset of it.
    """
    hits: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.For):
            continue
        for stmt in node.body:  # body only — never node.iter
            for inner in ast.walk(stmt):
                if (
                    isinstance(inner, ast.Call)
                    and isinstance(inner.func, ast.Attribute)
                    and inner.func.attr == "table"
                ):
                    hits.append(f"line {inner.lineno}: .table() inside a for BODY")
    return hits


n_plus_one = queries_inside_row_loops(ADMIN_AST)
check(
    "⑨ D4 — the query count is constant in the number of workspaces",
    not n_plus_one,
    "; ".join(n_plus_one),
)


# ---------------------------------------------------------------------------
# ④ The frontend matches the served shape
# ---------------------------------------------------------------------------
types_ts = (WEB / "types" / "admin.ts").read_text()
page_tsx = (WEB / "app" / "admin" / "page.tsx").read_text()
client_ts = (WEB / "lib" / "api" / "client.ts").read_text()

# Every field the pydantic row model declares must exist in the TS interface —
# derived from the model, so a field added server-side reddens this until the
# client learns it. (Backend/frontend field-name drift is a named pitfall.)
row_model = next(
    (
        n
        for n in ast.walk(ADMIN_AST)
        if isinstance(n, ast.ClassDef) and n.name == "AdminWorkspaceRow"
    ),
    None,
)
if row_model is None:
    check("⑩ AdminWorkspaceRow exists", False, "model not found")
else:
    # AnnAssign, not Assign — pydantic fields are annotated, and reading the
    # wrong node type makes the roster read 0 and the check pass VACUOUSLY.
    fields = [s.target.id for s in row_model.body if isinstance(s, ast.AnnAssign)]
    missing = [f for f in fields if f not in types_ts]
    check(
        f"⑩ all {len(fields)} AdminWorkspaceRow fields exist in types/admin.ts",
        bool(fields) and not missing,
        f"fields={fields} missing={missing}",
    )

check(
    "⑪ the client calls /workspaces, not the deleted /users",
    "/api/admin/workspaces" in client_ts and "/api/admin/users" not in client_ts,
    "the client still calls a deleted admin route",
)
check(
    "⑫ no deleted admin client method survives",
    not any(
        m in client_ts
        for m in ("accountDetail:", "exportUsers:", "exportReport:", "accounts: ()")
    ),
    "a client method for a deleted route is still exported",
)
# The page's own docstring explains WHY "unknown" was removed, so a raw scan
# matched the explanation (same class as ⑧). Strip comments first, then look
# for the literal in real JSX/TS.
page_code = re.sub(r"/\*.*?\*/", "", page_tsx, flags=re.S)
page_code = re.sub(r"^\s*//.*$", "", page_code, flags=re.M)
check(
    "⑬ the console never renders the string \"unknown\" (D3)",
    '"unknown"' not in page_code and "'unknown'" not in page_code,
    "the page can still render `unknown` for an unresolved owner",
)
check(
    "⑭ the deleted accounts panes are gone from the tree",
    not (WEB / "app" / "admin" / "accounts").exists(),
    "web/app/admin/accounts still exists",
)


# ---------------------------------------------------------------------------
# ⑤ LIVE — every table the console reads has rows (D2, the actual ruling)
# ---------------------------------------------------------------------------
def _live_client():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get(
        "SUPABASE_SERVICE_ROLE_KEY"
    )
    if not (url and key):
        return None
    from supabase import create_client

    return create_client(url, key)


client = _live_client()
if client is None:
    skip(
        f"⑮ every console table is non-empty on live ({len(READ_TABLES)} tables)",
        "no SUPABASE_URL / SUPABASE_SERVICE_KEY in env",
    )
else:
    for table in sorted(READ_TABLES):
        try:
            n = client.table(table).select("*", count="exact").limit(1).execute().count or 0
        except Exception as exc:  # noqa: BLE001
            check(f"⑮ live `{table}` is readable and non-empty", False, str(exc)[:120])
            continue
        check(
            f"⑮ live `{table}` is readable and non-empty",
            n > 0,
            f"{n} rows — ADR-655 D2: a figure with no live source is deleted, not carried at zero",
        )

    # Migration 257 — verify the LIVE object, not the runner's exit code.
    try:
        probe = client.table("workspaces").select("owner_email").limit(1).execute()
        check(
            "⑯ migration 257 applied — workspaces.owner_email is gone",
            False,
            "the column still exists and is selectable",
        )
    except Exception:
        check("⑯ migration 257 applied — workspaces.owner_email is gone", True)


# ---------------------------------------------------------------------------
print()
print(f"ADR-655 console gate: {len(passed)} passed, {len(failed)} failed, {len(skipped)} skipped")
if skipped:
    print("SKIPPED (not passes):")
    for s in skipped:
        print(f"  ⊘ {s}")
if failed:
    print("FAILED:")
    for f in failed:
        print(f"  ✗ {f}")
sys.exit(1 if failed else 0)

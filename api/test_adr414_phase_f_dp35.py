"""ADR-414 ratchet #5 — the DP35 scope-manifest gate.

FOUNDATIONS v9.15 DP35 (ADR-407 §3 D1): "every persistent store declares
workspace-content, member-experience, or account scope; a new store that
cannot name its scope is a design error."

This ratchet makes that enforceable: `api/services/scope_manifest.yaml` is the
machine-parseable mirror of ADR-407 §3's living registry. The gate discovers
every `.table("X")` reference in `api/` (production code, not tests) and asserts
each X is either declared in the manifest with a valid scope OR explicitly
exempt (test fixtures). A new persistent store therefore cannot ship without a
scope declaration — the CI form of "a store that cannot name its scope is a
design error."
"""

import ast
import re
from pathlib import Path

import yaml

API = Path(__file__).resolve().parent
MANIFEST = API / "services" / "scope_manifest.yaml"

VALID_SCOPES = {"content", "member-experience", "account"}

# `.table("<name>")` — the primary Supabase table-access idiom in this codebase.
_TABLE_RE = re.compile(r'\.table\(\s*["\']([a-z_][a-z0-9_]*)["\']\s*\)')

# ADR-548: the literal scan above is NOT sufficient on its own. Some stores are
# only ever reached through a helper taking the table name as a VARIABLE —
# `_delete_rows(client, "integration_sync_config", user_id)` in routes/account.py
# and scripts/purge_user_data.py. Those tables exist in Postgres and in code, yet
# were invisible to this gate: `integration_sync_config` and `user_admin_flags`
# went undeclared for exactly that reason, and the phantom check below would
# have called them stale once declared.
#
# So discovery also matches the table-name-as-first-string-argument helper shape.
# It is deliberately narrow (a quoted snake_case literal in a call that also
# passes a client/user) to avoid sweeping in arbitrary strings.
_TABLE_ARG_RE = re.compile(
    r'_(?:delete|count)(?:_rows)?\(\s*[A-Za-z_][A-Za-z0-9_]*\s*,\s*["\']([a-z_][a-z0-9_]*)["\']'
)

# The other real shape: a literal LIST of table names fed to a purge loop
# (`tables = [...]` / `for table in (...)` in routes/account.py + the purge
# service). Harvested via `ast` in `_discover_purge_listed` below.
_SNAKE_RE = re.compile(r"[a-z_][a-z0-9_]{2,}")

# Directories that are production stores (exclude tests, one-shots, probes —
# those may reference throwaway fixture tables the gate should not require).
_PROD_DIRS = ("services", "routes", "agents", "jobs", "mcp_server")


def _load_manifest() -> dict:
    return yaml.safe_load(MANIFEST.read_text()) or {}


def _discover_tables() -> set[str]:
    tables: set[str] = set()
    for sub in _PROD_DIRS:
        root = API / sub
        if not root.exists():
            continue
        for py in root.rglob("*.py"):
            if py.name.startswith("test_"):
                continue
            src = py.read_text()
            for m in _TABLE_RE.finditer(src):
                tables.add(m.group(1))
            # ADR-548 — variable-name table access (see _TABLE_ARG_RE).
            for m in _TABLE_ARG_RE.finditer(src):
                tables.add(m.group(1))
            # ADR-548 — literal table-name lists fed to a purge loop. Only used
            # to CONFIRM an already-declared store is live (see _discover_purge_
            # listed below); never to demand a new declaration, since a bare
            # string list cannot be distinguished from any other list of words.
    return tables


def _discover_purge_listed() -> set[str]:
    """Table names appearing in a literal purge list (ADR-548).

    Kept separate from `_discover_tables` deliberately: this shape is matched
    loosely, so it may only *satisfy* the phantom check (proving a declared
    store is really reached), never *trigger* the undeclared check. A loose
    matcher that could demand declarations would manufacture phantom stores of
    its own.

    Uses `ast`, not a regex: a bracket inside a trailing `#` comment truncates a
    non-greedy `[...]` match, which silently dropped the LAST entries of
    routes/account.py's purge list — `user_admin_flags` among them. The parser
    has no such failure mode.
    """
    found: set[str] = set()
    for sub in _PROD_DIRS + ("scripts",):
        root = API / sub
        if not root.exists():
            continue
        for py in root.rglob("*.py"):
            if py.name.startswith("test_"):
                continue
            try:
                tree = ast.parse(py.read_text())
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, (ast.List, ast.Tuple)):
                    continue
                names = [
                    el.value
                    for el in node.elts
                    if isinstance(el, ast.Constant)
                    and isinstance(el.value, str)
                    and _SNAKE_RE.fullmatch(el.value)
                ]
                # A purge list is homogeneous and plural — a couple of stray
                # snake_case strings in an unrelated list should not qualify.
                if len(names) >= 3:
                    found.update(names)
    return found


def test_manifest_scopes_are_valid():
    """Every declared store names one of the three valid scopes."""
    manifest = _load_manifest()
    stores = manifest.get("stores", {}) or {}
    assert stores, "scope_manifest.yaml declares no stores"
    bad = {
        name: entry.get("scope")
        for name, entry in stores.items()
        if entry.get("scope") not in VALID_SCOPES
    }
    assert not bad, (
        f"stores with an invalid scope (must be one of {sorted(VALID_SCOPES)}): "
        f"{bad}"
    )


def test_every_persistent_store_declares_its_scope():
    """DP35 ratchet: every `.table(...)` write target in production code is
    either scoped in the manifest or explicitly exempt. A new store forces a
    scope declaration — the CI form of ADR-407 D1."""
    manifest = _load_manifest()
    declared = set((manifest.get("stores", {}) or {}).keys())
    exempt = set(manifest.get("exempt", []) or [])
    known = declared | exempt

    discovered = _discover_tables()
    undeclared = sorted(discovered - known)
    assert not undeclared, (
        "persistent store(s) accessed in production code but NOT declared in "
        "api/services/scope_manifest.yaml:\n  "
        + "\n  ".join(undeclared)
        + "\n\nDP35 (ADR-407 D1 / ADR-414 ratchet #5): every store declares "
        "workspace-content / member-experience / account scope. Add each to "
        "the manifest's `stores:` with its scope (mirror ADR-407 §3), or to "
        "`exempt:` if it is a test fixture, not a production store."
    )


def test_manifest_does_not_declare_phantom_stores():
    """Hygiene: a manifest entry with no `.table(...)` reference anywhere is
    stale (a dropped table). Warn-not-fail would be softer, but a hard check
    keeps the registry honest — a dropped store's row should be removed.

    A few deliberate exceptions carry a `note` explaining why they stay despite
    no direct `.table(...)` write in the scanned dirs: `token_usage` (dropped by
    ADR-396, kept as a registry tombstone); `filesystem_documents` +
    `filesystem_chunks` (uploaded-document stores whose writes go through the
    document-ingest path / RPC). (`render_usage` was dropped by ADR-417 with the
    render service — migration 207 — and removed from the manifest.) All are real
    persistent stores that legitimately need a scope declaration — they just
    aren't reached by the string-literal `.table("X")` scan."""
    manifest = _load_manifest()
    stores = manifest.get("stores", {}) or {}
    discovered = _discover_tables()
    # Registry tombstones — declared-but-not-written-via-.table() by design.
    tombstones = {
        "token_usage", "filesystem_documents", "filesystem_chunks",
    }
    # ADR-548: a store reached only through a purge list is live, not phantom.
    phantom = sorted(set(stores) - discovered - tombstones - _discover_purge_listed())
    assert not phantom, (
        "scope_manifest.yaml declares store(s) with no `.table(...)` reference "
        f"in production code (stale — remove or tombstone): {phantom}"
    )

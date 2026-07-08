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

import re
from pathlib import Path

import yaml

API = Path(__file__).resolve().parent
MANIFEST = API / "services" / "scope_manifest.yaml"

VALID_SCOPES = {"content", "member-experience", "account"}

# `.table("<name>")` — the single Supabase table-access idiom in this codebase.
_TABLE_RE = re.compile(r'\.table\(\s*["\']([a-z_][a-z0-9_]*)["\']\s*\)')

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
            for m in _TABLE_RE.finditer(py.read_text()):
                tables.add(m.group(1))
    return tables


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
    document-ingest path / RPC); `render_usage` (written via `get_monthly_
    render_count` RPC, not a direct table insert). All are real persistent
    stores that legitimately need a scope declaration — they just aren't reached
    by the string-literal `.table("X")` scan."""
    manifest = _load_manifest()
    stores = manifest.get("stores", {}) or {}
    discovered = _discover_tables()
    # Registry tombstones — declared-but-not-written-via-.table() by design.
    tombstones = {
        "token_usage", "filesystem_documents", "filesystem_chunks", "render_usage",
    }
    phantom = sorted(set(stores) - discovered - tombstones)
    assert not phantom, (
        "scope_manifest.yaml declares store(s) with no `.table(...)` reference "
        f"in production code (stale — remove or tombstone): {phantom}"
    )

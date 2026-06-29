"""
Regression gate — ADR-339 Working-Tree Perception Economics.

Guards the perception-contract fixes that the wake round-economics audit
(docs/analysis/wake-round-economics-audit-2026-06-12.md) ratified:
  D1 — ListFiles returns the full subtree with metadata (bytes / updated_at /
       head authored_by); the one-level names-only projection is dead.
  D2 — SearchFiles(match='exact') zero-yield results are legible (explicit
       literal-substring message instead of a silent count:0).
  D3 — batching documented as capability in tool descriptions.

Usage:
    cd api && python test_adr339_perception_economics.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parent
REPO_ROOT = API_ROOT.parent
sys.path.insert(0, str(API_ROOT))

PASS = 0
FAIL = 0


def check(name: str, condition: bool, detail: str = "") -> None:
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}  {detail}")


asyncio.set_event_loop(asyncio.new_event_loop())


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


from services.primitives.workspace import (  # noqa: E402
    LIST_FILES_TOOL,
    READ_FILE_TOOL,
    SEARCH_FILES_TOOL,
    _LIST_FILES_MAX,
    _exact_search,
    handle_list_files,
)


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------

class _StubQuery:
    """Chainable PostgREST query stub returning canned rows on execute()."""

    def __init__(self, rows):
        self._rows = rows

    def __getattr__(self, _name):
        def _chain(*_a, **_k):
            return self
        return _chain

    def execute(self):
        return type("R", (), {"data": self._rows})()


class _StubClient:
    def __init__(self, rows):
        self._rows = rows

    def table(self, _name):
        return _StubQuery(self._rows)


class _StubAuth:
    def __init__(self, rows, agent=None):
        self.client = _StubClient(rows)
        self.user_id = "00000000-0000-0000-0000-000000000000"
        self.agent = agent


# ---------------------------------------------------------------------------
# D1 — recursive metadata listing
# ---------------------------------------------------------------------------

print("\nD1 — ListFiles recursive metadata contract")

desc = LIST_FILES_TOOL["description"]
check("ListFiles description: full-subtree contract", "FULL subtree" in desc)
check("ListFiles description: proscribes drill-down walk", "Do NOT walk" in desc)
check(
    "ListFiles description: names the metadata fields",
    all(k in desc for k in ("bytes", "updated_at", "authored_by")),
)
check(
    "ListFiles description: 0-byte litter visibility",
    "0 = empty file" in desc,
)
check("Listing cap is explicit (500, no silent cap)", _LIST_FILES_MAX == 500)

_ROWS = [
    {
        "path": "/workspace/operation/reports/x/output.md",
        "content_bytes": 0,
        "updated_at": "2026-06-12T00:00:00+00:00",
        "workspace_file_versions": {
            "authored_by": "freddie:ai:test",
            "created_at": "2026-06-12T00:00:00+00:00",
        },
    },
    {
        "path": "/workspace/operation/reports/x/sections/a.md",
        "content_bytes": 120,
        "updated_at": "2026-06-11T00:00:00+00:00",
        "workspace_file_versions": {
            "authored_by": "operator",
            "created_at": "2026-06-11T00:00:00+00:00",
        },
    },
]

result = _run(handle_list_files(_StubAuth(_ROWS), {"scope": "workspace", "path": ""}))
files = result.get("files") or []
check(
    "handle_list_files returns the FULL subtree (nested paths, not one level)",
    any(f.get("path") == "operation/reports/x/sections/a.md" for f in files),
    f"files={files}",
)
check(
    "entries carry bytes + updated_at + authored_by",
    files
    and all(set(f) >= {"path", "bytes", "updated_at", "authored_by"} for f in files),
    f"files={files}",
)
check(
    "0-byte file visible by bytes field without a ReadFile",
    any(f.get("bytes") == 0 for f in files),
)
check(
    "paths are workspace-relative (ReadFile-compatible)",
    all(not f.get("path", "").startswith("/workspace/") for f in files),
)

# Head-revision filter semantics
result_op = _run(
    handle_list_files(
        _StubAuth(_ROWS), {"scope": "workspace", "authored_by": "operator"}
    )
)
op_paths = [f.get("path") for f in (result_op.get("files") or [])]
check(
    "authored_by filter applies to HEAD revision",
    op_paths == ["operation/reports/x/sections/a.md"],
    f"paths={op_paths}",
)

result_since = _run(
    handle_list_files(
        _StubAuth(_ROWS),
        {"scope": "workspace", "since": "2026-06-11T12:00:00Z"},
    )
)
since_paths = [f.get("path") for f in (result_since.get("files") or [])]
check(
    "since filter (Z-suffix tolerant) keeps only newer head revisions",
    since_paths == ["operation/reports/x/output.md"],
    f"paths={since_paths}",
)

no_agent = _run(handle_list_files(_StubAuth([]), {"scope": "agent"}))
check(
    "scope='agent' without agent context still errors no_agent_context",
    no_agent.get("error") == "no_agent_context",
)

import inspect  # noqa: E402
from services.primitives import workspace as _ws_mod  # noqa: E402

src = inspect.getsource(_ws_mod)
check(
    "handler selects content_bytes + head_version_id embed (one query, one round)",
    "content_bytes" in src and "workspace_file_versions!head_version_id" in src,
)
check(
    "one-level projection is dead (no direct-children split in handler)",
    "remainder.split" not in inspect.getsource(_ws_mod.handle_list_files)
    and "remainder.split" not in inspect.getsource(_ws_mod._list_tree),
)

# ---------------------------------------------------------------------------
# D2 — exact-search zero-yield legibility
# ---------------------------------------------------------------------------

print("\nD2 — SearchFiles(exact) zero-yield legibility")

zero = _exact_search(_StubAuth([]), "conflict backup merge stale empty", "/workspace")
check(
    "zero-yield result carries an explicit LITERAL-substring message",
    "LITERAL" in (zero.get("message") or ""),
    f"message={zero.get('message')}",
)
check(
    "result echoes semantics field",
    "literal substring" in (zero.get("semantics") or ""),
)
hit = _exact_search(
    _StubAuth([{"path": "/workspace/x.md", "content": "conflict here"}]),
    "conflict",
    "/workspace",
)
check("non-zero result has no warning message", "message" not in hit)

sdesc = SEARCH_FILES_TOOL["description"]
check(
    "SearchFiles description warns: ONE literal substring, not OR-terms",
    "ONE literal substring" in sdesc,
)

# ---------------------------------------------------------------------------
# D3 — batching as capability documentation
# ---------------------------------------------------------------------------

print("\nD3 — batching capability notes")

check(
    "ReadFile description documents batched independent reads",
    "single turn" in READ_FILE_TOOL["description"],
)
check(
    "SearchFiles exact guidance documents batched per-term calls",
    "batched in a single turn" in sdesc,
)
check(
    "no round-counter/urgency language introduced (ADR-303 deleted class)",
    all(
        term not in (desc + sdesc + READ_FILE_TOOL["description"]).lower()
        for term in ("rounds remaining", "round budget", "hurry", "quickly")
    ),
)

# ---------------------------------------------------------------------------
# Doc-radius
# ---------------------------------------------------------------------------

print("\nDoc-radius")

adr = REPO_ROOT / "docs/adr/ADR-339-working-tree-perception-economics.md"
check("ADR-339 exists", adr.exists())
matrix = (REPO_ROOT / "docs/architecture/primitives-matrix.md").read_text()
check("primitives-matrix ListFiles row cites ADR-339 D1", "ADR-339 D1" in matrix)
changelog = (API_ROOT / "prompts/CHANGELOG.md").read_text()
check("prompts CHANGELOG entry [2026.06.12.1]", "[2026.06.12.1]" in changelog)
migration = REPO_ROOT / "supabase/migrations/185_adr339_content_bytes.sql"
check("migration 185 (content_bytes) exists", migration.exists())

print(f"\n{'='*60}\nADR-339 gate: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)

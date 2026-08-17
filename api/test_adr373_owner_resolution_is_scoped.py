"""ADR-373 — owner-workspace resolution is SCOPED TO THE OWNER.

On 2026-08-17 `_resolve_owner_workspace_id_cached` lost its
`.eq("owner_id", user_id)` filter while an ORDER BY was being added — the
`.eq()` was replaced rather than joined by it. The function then selected the
OLDEST WORKSPACE IN THE TABLE and returned it for every caller, and the new
ordering made that wrong answer DETERMINISTIC: every principal resolved to one
specific stranger's workspace.

Observed live the same day. A connector authenticated as an account with no
ownership and no grant into that workspace wrote three attributed revisions
into it — succeeding, returning revision ids — while that account's own
275-file substrate listed as 19 files. The service key bypasses RLS, so no
policy below the query could catch it.

**Why the existing gates did not catch this.** Every workspace-resolution test
in the suite exercises ONE user. With a single workspace in the fixture, an
unfiltered `SELECT ... LIMIT 1` returns the right row by coincidence — the bug
is INVISIBLE to a one-user test by construction. This gate therefore asserts
the property that actually matters: **two users must not resolve to each
other's workspace**, and the resolver must never return a workspace the
principal does not own.

Run with `python3 test_adr373_owner_resolution_is_scoped.py` (NOT pytest —
check() gates print ✗ but a pytest run reports PASS; see MEMORY.md).
"""

import ast
import sys
import logging

FAILURES: list = []


def _check(label, cond):
    if cond:
        logging.info("✓ %s", label)
    else:
        logging.error("✗ %s", label)
        FAILURES.append(label)
    return bool(cond)


ALICE = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
BOB = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
ALICE_WS = "11111111-1111-1111-1111-111111111111"
BOB_WS = "22222222-2222-2222-2222-222222222222"


class _FakeQuery:
    """Records the filters applied, and answers like PostgREST would.

    The whole point: `eq` is RECORDED, so a query that forgets `owner_id`
    returns the oldest row in the whole table — exactly what production did.
    """

    def __init__(self, rows):
        self._rows = rows
        self._eq = {}
        self._order = None
        self._limit = None

    def select(self, *_a, **_k):
        return self

    def eq(self, col, val):
        self._eq[col] = val
        return self

    def order(self, col, desc=False):
        self._order = (col, desc)
        return self

    def limit(self, n):
        self._limit = n
        return self

    def execute(self):
        rows = list(self._rows)
        for col, val in self._eq.items():
            rows = [r for r in rows if r.get(col) == val]
        if self._order:
            col, desc = self._order
            rows.sort(key=lambda r: r.get(col, ""), reverse=desc)
        if self._limit is not None:
            rows = rows[: self._limit]
        return type("R", (), {"data": rows})()


class _FakeClient:
    def __init__(self, rows):
        self._rows = rows

    def table(self, name):
        assert name == "workspaces", name
        return _FakeQuery(self._rows)


def run() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s - %(message)s")
    sys.path.insert(0, ".")

    import services.supabase as sb

    # Bob's workspace is OLDER, so an unfiltered `order(created_at).limit(1)`
    # returns Bob's row for everyone — the production shape exactly.
    rows = [
        {"id": BOB_WS, "owner_id": BOB, "created_at": "2026-03-13T00:00:00Z"},
        {"id": ALICE_WS, "owner_id": ALICE, "created_at": "2026-05-20T00:00:00Z"},
    ]

    original = sb.get_service_client
    sb.get_service_client = lambda: _FakeClient(rows)
    try:
        # ── D1. Each owner resolves to THEIR OWN workspace ──────────────────
        sb._resolve_owner_workspace_id_cached.cache_clear()
        alice = sb.resolve_owner_workspace_id(ALICE)
        bob = sb.resolve_owner_workspace_id(BOB)

        _check("D1. Alice resolves to Alice's workspace", alice == ALICE_WS)
        _check("D1. Bob resolves to Bob's workspace", bob == BOB_WS)
        # THE regression assertion. Alice's workspace is NEWER, so under the
        # unfiltered query she resolved to Bob's — a cross-tenant resolution.
        _check(
            "D1. Alice does NOT resolve to Bob's older workspace (the 2026-08-17 bug)",
            alice != BOB_WS,
        )

        # ── D2. A principal owning NOTHING resolves to nothing ──────────────
        # Under the unfiltered query a stranger got the oldest workspace in the
        # table — reach they were never granted.
        sb._resolve_owner_workspace_id_cached.cache_clear()
        stranger = sb.resolve_owner_workspace_id("cccccccc-cccc-cccc-cccc-cccccccccccc")
        _check("D2. an owner of nothing resolves to None, not a stranger's workspace", stranger is None)

        # ── D3. Ordering still applies WITHIN one owner ─────────────────────
        # The ORDER BY that displaced the filter is itself correct and must
        # survive the repair: oldest-first, but only among rows the user owns.
        rows.append({"id": "33333333-3333-3333-3333-333333333333",
                     "owner_id": ALICE, "created_at": "2026-01-01T00:00:00Z"})
        sb._resolve_owner_workspace_id_cached.cache_clear()
        _check(
            "D3. among an owner's OWN workspaces the oldest wins (ordering preserved)",
            sb.resolve_owner_workspace_id(ALICE) == "33333333-3333-3333-3333-333333333333",
        )
        rows.pop()

        # ── D4. The cache is keyed per user, not shared ─────────────────────
        # An lru_cache over a function that ignored its argument would freeze
        # ONE answer for every user, process-wide.
        sb._resolve_owner_workspace_id_cached.cache_clear()
        first = sb.resolve_owner_workspace_id(BOB)   # warm with Bob
        second = sb.resolve_owner_workspace_id(ALICE)
        _check(
            "D4. a cache warmed by one user does not answer for another",
            first == BOB_WS and second == ALICE_WS,
        )
    finally:
        sb.get_service_client = original
        sb._resolve_owner_workspace_id_cached.cache_clear()

    # ── D5. The filter is present in the SOURCE, structurally ──────────────
    # Executed checks above prove behaviour with a fake client; this proves the
    # real query carries the filter, so a future edit cannot drop it and pass by
    # virtue of a fixture. Parsed, not grepped: `owner_id` appears in prose
    # comments in this file, and a comment must never satisfy a behaviour check.
    src = open("services/supabase.py").read()
    tree = ast.parse(src)
    scoped = False
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_resolve_owner_workspace_id_cached":
            for sub in ast.walk(node):
                if (
                    isinstance(sub, ast.Call)
                    and isinstance(sub.func, ast.Attribute)
                    and sub.func.attr == "eq"
                    and sub.args
                    and isinstance(sub.args[0], ast.Constant)
                    and sub.args[0].value == "owner_id"
                ):
                    scoped = True
    _check("D5. the cached resolver's query filters on owner_id (AST, not grep)", scoped)

    total = len(FAILURES)
    print(f"\nADR-373 owner-resolution scoping gate: {_RUN - total}/{_RUN} passed, {total} failed")
    for f in FAILURES:
        print(f"  ✗ {f}")
    return 1 if FAILURES else 0


_RUN = 7

if __name__ == "__main__":
    sys.exit(run())

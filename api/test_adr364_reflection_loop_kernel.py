"""ADR-364 reflection-loop kernel regression — two fixes surfaced 2026-06-24 by
the offline reflection-loop probe (api/scripts/operator/probe_reflection_loop_local.py).

Both are ARCHITECTURE-axis facts (EVAL-SUITE-DISCIPLINE §0) — deterministic, one
right answer, a bug if wrong — so they belong in a test_*.py, not a judgment eval.
Each masqueraded as "the reflection loop never produced reflection" (a MIND read),
when it was a plumbing fault the kernel never delivered the gap-fact for:

  FIX 1 — bundles_active_for_workspace: an operator-ACTIVATED bundle (MANDATE.md
    slug marker) must resolve as active-for-workspace REGARDLESS of whether some
    of its capabilities are connection-gated. Connections gate WHICH CAPABILITIES
    work, not whether the activated program's substrate_abi (ground_truth, …)
    resolves. ADR-353 §15a added `requires_connection: reddit` capabilities to
    alpha-author, silently flipping it from connection-less to platform-bound and
    dropping its ground-truth from an activated author workspace with no reddit
    connection — so get_ground_truth_for_workspace returned None and the gap-fact
    could never render.

  FIX 2 — _reflection_gap_fact path prefix: workspace_files store the
    /workspace/-prefixed path; the path CONSTANTS are bare. The gap-fact's two
    bespoke reads queried the BARE constants (.eq("path", PERSONA_JUDGMENT_LOG_PATH)
    / .eq("path", gt_path)), missing every row — so the gap-fact silently returned
    "" and the loop never fired, even with a perfect verdict↔outcome pair on disk.

Standalone script (sys.exit), matching the api/test_*.py convention. Run:
  .venv/bin/python api/test_adr364_reflection_loop_kernel.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_API_ROOT = Path(__file__).resolve().parent
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

PASS = "  PASS"
FAILMARK = "  FAIL"
_results: list[tuple[bool, str]] = []


def check(cond: bool, label: str) -> None:
    _results.append((bool(cond), label))
    print(f"{PASS if cond else FAILMARK}  {label}")


# =============================================================================
# Stub client — serves platform_connections AND workspace_files (the MANDATE
# slug-marker read FIX 1 added, plus the path-keyed reads FIX 2 exercises).
# =============================================================================


class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    """Records .eq() filters and applies them against a path-keyed row set on
    execute() — faithful enough to catch a wrong-path query (the FIX 2 bug)."""

    def __init__(self, rows: list[dict]):
        self._rows = rows
        self._filters: dict[str, object] = {}

    def select(self, *_a, **_k):
        return self

    def eq(self, col, val):
        self._filters[col] = val
        return self

    def like(self, _col, _pat):
        return self

    def limit(self, _n):
        return self

    def order(self, *_a, **_k):
        return self

    def execute(self):
        rows = self._rows
        for col, val in self._filters.items():
            rows = [r for r in rows if r.get(col) == val]
        return _Result(rows)


class _Client:
    def __init__(self, *, connections: list[dict], files: list[dict]):
        self._connections = connections
        self._files = files

    def table(self, name):
        if name == "platform_connections":
            return _Query(self._connections)
        if name == "workspace_files":
            return _Query(self._files)
        raise NotImplementedError(f"Unexpected table: {name}")


def _bust_bundle_caches():
    from services.bundle_reader import _load_manifest, _all_slugs
    _all_slugs.cache_clear()
    _load_manifest.cache_clear()


# A MANDATE.md carrying the alpha-author program slug marker (frontmatter
# `activated_bundle_version` + the heading marker parse_active_program_slug reads).
_AUTHOR_MANDATE = (
    "---\nactivated_bundle_version: 2026-06-22.2\n---\n"
    "# Mandate — alpha-author\n\nAuthor founder corpus pieces.\n"
)


# =============================================================================
# FIX 1 — bundles_active_for_workspace resolves an activated bundle without
#          requiring its connection-gated capabilities' platform.
# =============================================================================


def test_activated_bundle_resolves_without_its_gated_connection():
    _bust_bundle_caches()
    from services.bundle_reader import (
        bundles_active_for_workspace,
        get_ground_truth_for_workspace,
    )
    from services.programs import parse_active_program_slug

    # The funded-workspace shape: alpha-author activated (slug marker), NO reddit
    # connection (only slack/notion/github — none of which alpha-author requires).
    client = _Client(
        connections=[
            {"user_id": "u", "platform": "slack", "status": "active", "created_at": "2026-01-01T00:00:00Z"},
            {"user_id": "u", "platform": "notion", "status": "active", "created_at": "2026-01-02T00:00:00Z"},
        ],
        files=[
            {"user_id": "u", "path": "/workspace/constitution/MANDATE.md", "content": _AUTHOR_MANDATE},
        ],
    )

    check(parse_active_program_slug(_AUTHOR_MANDATE) == "alpha-author",
          "FIX1: MANDATE slug marker parses to alpha-author")

    bundles = bundles_active_for_workspace("u", client)
    slugs = [b.get("slug") for b in bundles]
    check("alpha-author" in slugs,
          "FIX1: activated alpha-author resolves active WITHOUT a reddit connection "
          f"(got {slugs})")

    gt = get_ground_truth_for_workspace("u", client)
    check(gt == "operation/authored/_signal.md",
          f"FIX1: get_ground_truth_for_workspace resolves the author ground-truth (got {gt!r})")


def test_unactivated_platform_bundle_still_needs_its_connection():
    """The fix must NOT make every bundle always-active. A bundle the operator did
    NOT activate (no slug marker) still requires its platform connection — the
    cockpit-chrome inference path is preserved (adr225 semantics)."""
    _bust_bundle_caches()
    from services.bundle_reader import bundles_active_for_workspace

    # No MANDATE marker, no connections → nothing resolves.
    client = _Client(connections=[], files=[])
    check(bundles_active_for_workspace("u", client) == [],
          "FIX1: no activation + no connection → zero active bundles (chrome path intact)")

    # alpha-trader is platform-bound; with trading connected (and no activation
    # marker) it still resolves via the connection path.
    client2 = _Client(
        connections=[{"user_id": "u", "platform": "trading", "status": "active", "created_at": "2026-04-01T00:00:00Z"}],
        files=[],
    )
    slugs = [b.get("slug") for b in bundles_active_for_workspace("u", client2)]
    check("alpha-trader" in slugs,
          f"FIX1: platform-bound alpha-trader still resolves via its connection (got {slugs})")


# =============================================================================
# FIX 2 — _reflection_gap_fact queries the /workspace/-prefixed path.
# =============================================================================

_SEED_PID = "ref10001-0000-4000-8000-000000000001"
_JUDGMENT_LOG = (
    "# Judgment Log\n\n"
    "--- decision ---\n"
    "timestamp: 2026-06-21T10:00:00+00:00\n"
    f"proposal_id: {_SEED_PID}\n"
    "action_type: author.ship_piece\n"
    "decision: approve\n"
    "reviewer_identity: reviewer:ai-opus-seed\n"
    "---\n"
    "Approved the hedge-stack opener despite the soft anti-slop signal.\n"
)
_SIGNAL = (
    '---\n{\n  "domain": "authored",\n  "events": [\n'
    f'    {{"executed_at": "2026-06-22T10:00:00Z", "action_type": "author.ship_piece", '
    f'"value_cents": -1842, "attestation": "operator", "proposal_id": "{_SEED_PID}"}}\n'
    "  ]\n}\n---\n# Ground-truth signal\n"
)


def test_gap_fact_joins_prefixed_rows():
    _bust_bundle_caches()
    from services.reviewer_envelope import _reflection_gap_fact

    # Rows stored /workspace/-prefixed (the real storage shape). The activated
    # MANDATE makes get_ground_truth_for_workspace resolve _signal.md (FIX 1),
    # and _reflection_gap_fact must query the prefixed path to find both (FIX 2).
    client = _Client(
        connections=[],
        files=[
            {"user_id": "u", "path": "/workspace/constitution/MANDATE.md", "content": _AUTHOR_MANDATE},
            {"user_id": "u", "path": "/workspace/persona/judgment_log.md", "content": _JUDGMENT_LOG},
            {"user_id": "u", "path": "/workspace/operation/authored/_signal.md", "content": _SIGNAL},
        ],
    )

    gap = asyncio.get_event_loop().run_until_complete(_reflection_gap_fact(client, "u"))
    check(bool(gap.strip()),
          "FIX2: gap-fact is non-empty for a /workspace/-prefixed verdict↔outcome pair")
    check("-18.42" in gap,
          f"FIX2: gap-fact names the attested outcome value (got {gap!r})")
    check("[operator]" in gap,
          "FIX2: gap-fact carries the attestation tag")
    check("approve author.ship_piece" in gap,
          "FIX2: gap-fact renders the joined verdict line")


def test_gap_fact_empty_without_joinable_outcome():
    """Negative control: a verdict with NO matching outcome event → gap-fact silent
    (the join keys on proposal_id overlap — the continuity-eval control case)."""
    _bust_bundle_caches()
    from services.reviewer_envelope import _reflection_gap_fact

    signal_no_match = (
        '---\n{"domain": "authored", "events": [{"executed_at": "2026-06-22T10:00:00Z", '
        '"action_type": "author.ship_piece", "value_cents": 500, "attestation": "operator", '
        '"proposal_id": "DIFFERENT-pid-no-overlap"}]}\n---\n# gt\n'
    )
    client = _Client(
        connections=[],
        files=[
            {"user_id": "u", "path": "/workspace/constitution/MANDATE.md", "content": _AUTHOR_MANDATE},
            {"user_id": "u", "path": "/workspace/persona/judgment_log.md", "content": _JUDGMENT_LOG},
            {"user_id": "u", "path": "/workspace/operation/authored/_signal.md", "content": signal_no_match},
        ],
    )
    gap = asyncio.get_event_loop().run_until_complete(_reflection_gap_fact(client, "u"))
    check(gap == "",
          f"FIX2: gap-fact silent when no proposal_id overlaps (got {gap!r})")


def main() -> int:
    print("ADR-364 reflection-loop kernel regression\n")
    test_activated_bundle_resolves_without_its_gated_connection()
    test_unactivated_platform_bundle_still_needs_its_connection()
    test_gap_fact_joins_prefixed_rows()
    test_gap_fact_empty_without_joinable_outcome()
    passed = sum(1 for ok, _ in _results if ok)
    total = len(_results)
    print(f"\n{passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())

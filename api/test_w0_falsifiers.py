"""W0 gate — the ADR-457 D8 falsifier instrumentation.

Run: python3 test_w0_falsifiers.py   (NOT pytest — check()-gates print ✗ but
pytest would PASS them; this file's exit code is the signal.)

What it protects:
  1. The surface derivation (ADR-460 §4 / spec §4) over every class, INCLUDING
     `unclassified` — a metric that silently drops unknowns reads as coverage
     it does not have.
  2. Falsifier 2's staged=False pre-settle — the distinction the whole W0
     sequencing exists for (an unbuilt verb reads zero; zero is not evidence
     of non-adoption).
  3. Falsifier 3 works with NO session_id (it reads a different table).
  4. THE ADR-396 RATCHET: W0 adds a nullable column to the ONE ledger; it must
     never become a second spend surface.

Spec: docs/analysis/w0-falsifier-instrumentation-spec-2026-07-16.md
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from services.falsifiers import (  # noqa: E402
    SURFACE_DERIVE,
    SURFACE_MAKE,
    SURFACE_STEWARD,
    SURFACE_THINK,
    SURFACE_UNCLASSIFIED,
    classify_surface,
)

_results: list[tuple[str, bool]] = []


def _check(label: str, cond: bool) -> None:
    _results.append((label, bool(cond)))
    print(f"  {'✓' if cond else '✗'} {label}")


def _lane(**lane_meta) -> dict:
    return {"session_type": "lane", "context_metadata": {"lane": lane_meta}}


def run() -> bool:
    print("\n── 1. the surface derivation (DP29: derived, never stored) ──")

    _check(
        "a chat lane (no binding) → think",
        classify_surface(_lane(name="x", model="anthropic/claude-sonnet-4-6"))
        == SURFACE_THINK,
    )
    _check(
        "a Studio bound lane (artifact_path) → make (ADR-440 D3)",
        classify_surface(_lane(model="m", artifact_path="/workspace/x.html"))
        == SURFACE_MAKE,
    )
    _check(
        "a derive lane (derive_recipe) → derive (ADR-450 D3)",
        classify_surface(
            _lane(model="m", derive_recipe="prd", derive_source="/workspace/a.md")
        )
        == SURFACE_DERIVE,
    )
    # ADR-450 D3 composes WITH the ADR-440 binding — a derive lane carries an
    # artifact_path too. Derive must win, or every derive lane is miscounted
    # as make and falsifier 1 reads Studio-heavy for the wrong reason.
    _check(
        "a derive lane that ALSO carries artifact_path → derive, not make",
        classify_surface(
            _lane(model="m", artifact_path="/workspace/out.html",
                  derive_recipe="prd", derive_source="/workspace/a.md")
        )
        == SURFACE_DERIVE,
    )
    _check(
        "the steward rail (thinking_partner) → steward",
        classify_surface({"session_type": "thinking_partner"}) == SURFACE_STEWARD,
    )
    # The load-bearing honesty case: pre-migration-216 rows have no session to
    # join. They must NEVER be guessed into a class.
    _check(
        "no joined session (pre-W0 row) → unclassified, never guessed",
        classify_surface(None) == SURFACE_UNCLASSIFIED,
    )
    _check(
        "an empty session row → unclassified (not silently think)",
        classify_surface({}) == SURFACE_UNCLASSIFIED,
    )

    print("\n── 2. the join key exists end-to-end ──")

    telemetry = (Path(__file__).parent / "services" / "telemetry.py").read_text()
    _check(
        "record_execution_event accepts session_id",
        "session_id: Optional[str] = None" in telemetry,
    )
    _check(
        "…and writes it only when present (house `is not None` style)",
        re.search(r'if session_id is not None:\s*\n\s*row\["session_id"\] = session_id',
                  telemetry) is not None,
    )

    runner = (Path(__file__).parent / "services" / "lane_runner.py").read_text()
    _check(
        "BOTH lane ledger calls pass session_id (streaming + non-streaming)",
        runner.count("session_id=session_id,  # W0 — the falsifier join key") == 2,
    )
    routes = (Path(__file__).parent / "routes" / "lanes.py").read_text()
    _check(
        "the live streaming route passes the lane id (else the column is always NULL)",
        "session_id=lane_id," in routes,
    )

    print("\n── 3. falsifier 2 — the pre-settle distinction (why W0 is first) ──")

    src = (Path(__file__).parent / "services" / "falsifiers.py").read_text()
    _check(
        "falsifier 2 reports `staged` (verb-exists) separately from `settles` (count)",
        '"staged": ever > 0' in src and '"settles": settles' in src,
    )
    _check(
        "…and says so in its own note (a zero pre-settle is not non-adoption)",
        "is NOT " in src and "evidence of non-adoption" in src,
    )

    print("\n── 4. falsifier 3 needs no session_id (a different table) ──")
    _check(
        "falsifier 3 reads workspace_file_versions.authored_by, not the ledger",
        "workspace_file_versions" in src and 'startswith("yarnnn:mcp")' in src,
    )
    _check(
        "…and reports system writes separately (never folded into hum or desk)",
        '"system_writes": system' in src,
    )

    print("\n── 5. every falsifier reports what it could NOT see ──")
    _check(
        "falsifier 1 reports unclassified_turns",
        '"unclassified_turns"' in src,
    )
    _check(
        "all three report their window",
        src.count('"window_days": days') >= 3,
    )

    print("\n── 6. THE ADR-396 RATCHET — one ledger, one meter ──")
    # W0 adds a nullable column to execution_events. It must never become a
    # second spend surface: get_effective_balance sums ONE ledger.
    _check(
        "falsifiers.py is READ-ONLY (no insert/update/upsert/delete)",
        not re.search(r"\.(insert|update|upsert|delete)\(", src),
    )
    _check(
        "falsifiers.py never touches cost_usd or the balance",
        "cost_usd" not in src and "balance" not in src,
    )
    migration = (
        Path(__file__).parent.parent
        / "supabase" / "migrations" / "216_w0_falsifier_session_id.sql"
    ).read_text()
    _check(
        "migration 216 only ADDs a nullable column (no table, no cost column)",
        "ADD COLUMN IF NOT EXISTS session_id uuid NULL" in migration
        and "CREATE TABLE" not in migration.upper(),
    )
    _check(
        "migration 216 does NOT backfill (a guessed baseline is the thing W0 prevents)",
        "UPDATE execution_events" not in migration,
    )

    ok = all(c for _, c in _results)
    print()
    print(f"{'PASS' if ok else 'FAIL'}: {sum(c for _, c in _results)}/{len(_results)} checks")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)

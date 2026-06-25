"""ADR-366 — the grant/contract split: breadth = AUTONOMY mode, lock = the grant.

Architecture-axis regression (EVAL-SUITE-DISCIPLINE §0): deterministic, one right
answer, a bug if wrong. Locks the topology decision so it can't silently drift back.

The split:
  governance/ = the GRANT (authority + spend the agent runs under) — LOCKED-ALWAYS
                from every LLM caller, every mode. A grant the grantee can rewrite
                is not a grant (_autonomy = how far decisions bind; _budget = the
                spend authorization).
  contract/   = the operating CONTRACT (_preferences, _expected_output) — NOT in the
                reviewer lock-prefix → MODE-GOVERNED by the ADR-307 witness gate
                (QUEUE under bounded/supervised, APPLY under autonomous). Editing it
                grants NO new authority; breadth is the dial, not a wall.

Standalone script (sys.exit), matching the api/test_*.py convention. Run:
  .venv/bin/python api/test_adr366_grant_contract_split.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_API_ROOT = Path(__file__).resolve().parent
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

_results: list[tuple[bool, str]] = []


def check(cond: bool, label: str) -> None:
    _results.append((bool(cond), label))
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")


def _locked(caller: str, path: str) -> bool:
    from services.primitives.workspace import _is_path_locked
    return _is_path_locked(caller, path)


def test_roots_and_constants():
    from services import workspace_paths as wp
    check(wp.CONTRACT_ROOT == "contract/", "contract/ root constant exists")
    check(wp.GOVERNANCE_ROOT == "governance/", "governance/ root constant intact")
    check(wp.CONTRACT_PREFERENCES_PATH == "contract/_preferences.yaml",
          "_preferences.yaml moved under contract/")
    check(wp.CONTRACT_EXPECTED_OUTPUT_PATH == "contract/_expected_output.yaml",
          "_expected_output.yaml moved under contract/")
    # The grant files stayed in governance/.
    check(wp.GOVERNANCE_AUTONOMY_YAML_PATH == "governance/_autonomy.yaml",
          "_autonomy.yaml stays in governance/ (the grant)")
    check(wp.GOVERNANCE_BUDGET_PATH == "governance/_budget.yaml",
          "_budget.yaml stays in governance/ (the grant)")
    # The deprecated aliases are removed (Singular Implementation — no dual path).
    check(not hasattr(wp, "GOVERNANCE_PREFERENCES_PATH"),
          "GOVERNANCE_PREFERENCES_PATH alias removed (one canonical home)")
    check(not hasattr(wp, "GOVERNANCE_EXPECTED_OUTPUT_PATH"),
          "GOVERNANCE_EXPECTED_OUTPUT_PATH alias removed")


def test_governance_grant_locked_always():
    # The grant is the irreducible lock for every LLM caller. (system is governed
    # by named-path discipline at each writer, not a prefix lock — CALLER_WRITE_
    # POLICY["system"] is empty by design; no system writer targets the grant.)
    for caller in ("reviewer", "mcp", "agent"):
        check(_locked(caller, "governance/_autonomy.yaml"),
              f"governance/_autonomy.yaml LOCKED from {caller} (the grant)")
        check(_locked(caller, "governance/_budget.yaml"),
              f"governance/_budget.yaml LOCKED from {caller} (the spend grant)")
        check(_locked(caller, "governance/AUTONOMY.md"),
              f"governance/AUTONOMY.md LOCKED from {caller}")


def test_contract_mode_governed_for_reviewer():
    # The CORE of ADR-366: the reviewer is NOT topology-locked from contract/ —
    # the ADR-307 witness gate governs it (QUEUE/APPLY by mode), not a wall.
    check(not _locked("reviewer", "contract/_preferences.yaml"),
          "contract/_preferences.yaml NOT topology-locked from reviewer (mode-governed)")
    check(not _locked("reviewer", "contract/_expected_output.yaml"),
          "contract/_expected_output.yaml NOT topology-locked from reviewer (mode-governed)")
    check(not _locked("reviewer", "/workspace/contract/_expected_output.yaml"),
          "contract/ unlocked for reviewer with /workspace/ prefix too")


def test_contract_locked_from_lower_trust_callers():
    # mcp (foreign LLM) + agent (specialist) do NOT revise the operator's operating
    # contract — only the reviewer (the installed judgment). (system is named-path
    # governed, not prefix-locked — see test_governance_grant_locked_always.)
    for caller in ("mcp", "agent"):
        check(_locked(caller, "contract/_preferences.yaml"),
              f"contract/_preferences.yaml LOCKED from {caller}")
        check(_locked(caller, "contract/_expected_output.yaml"),
              f"contract/_expected_output.yaml LOCKED from {caller}")


def test_reviewer_can_still_write_constitution_and_operation():
    # Regression: the always-yours roots are unchanged (ADR-319 / ADR-320).
    check(not _locked("reviewer", "constitution/MANDATE.md"),
          "reviewer still amends constitution/MANDATE.md (ADR-319)")
    check(not _locked("reviewer", "operation/authored/x/content.md"),
          "reviewer still writes operation/ (the work surface)")
    check(not _locked("reviewer", "persona/principles.md"),
          "reviewer still writes persona/ (its own rules)")


def test_operator_writes_both_grant_and_contract():
    # The operator owns the grant AND the contract (locked only from system/).
    check(not _locked("operator", "governance/_autonomy.yaml"),
          "operator sets the grant (governance/)")
    check(not _locked("operator", "contract/_expected_output.yaml"),
          "operator sets the contract (contract/)")
    check(_locked("operator", "system/_recent_execution.md"),
          "operator still locked from system/ (orchestration runtime)")


def main() -> int:
    print("ADR-366 grant/contract split — topology regression\n")
    test_roots_and_constants()
    test_governance_grant_locked_always()
    test_contract_mode_governed_for_reviewer()
    test_contract_locked_from_lower_trust_callers()
    test_reviewer_can_still_write_constitution_and_operation()
    test_operator_writes_both_grant_and_contract()
    passed = sum(1 for ok, _ in _results if ok)
    total = len(_results)
    print(f"\n{passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())

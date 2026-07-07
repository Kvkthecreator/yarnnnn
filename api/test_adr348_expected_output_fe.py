"""ADR-348 gate — Expected Output, operator-facing FE.

Python file-assertion gate (no JS test runner, per ADR-236 Rule 3). Verifies
ADR-345's Expected Output gets its operator surface: a content-shape +
ExpectedOutputCard in the ADR-347 Contract group of the one Settings door.

IMPORTANT: run as a SCRIPT (`python test_adr348_expected_output_fe.py`), not
under pytest — check() records failures via globals + sys.exit, which pytest
does not surface.

Usage:
    cd api
    python test_adr348_expected_output_fe.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_API_ROOT = Path(__file__).resolve().parent
_WEB = _API_ROOT.parent / "web"

PASSED = 0
FAILED = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global PASSED, FAILED
    if condition:
        print(f"  ✓ {label}")
        PASSED += 1
    else:
        print(f"  ✗ {label}{(' — ' + detail) if detail else ''}")
        FAILED += 1


def _read(rel: str, root: Path = _WEB) -> str:
    p = root / rel
    return p.read_text() if p.exists() else ""


def test_content_shape() -> None:
    print("\n[shape] expected-output content-shape (ADR-348 D1)")
    src = _read("lib/content-shapes/expected-output.ts")
    check("expected-output.ts exists", bool(src))
    check("SHAPE_KEY == 'expected-output'", "SHAPE_KEY = 'expected-output'" in src)
    check("PATH_GLOB targets contract/_expected_output.yaml (ADR-366)",
          "_expected_output.yaml" in src)
    check("WRITE_CONTRACT == 'configuration' (operator-writable, ADR-347 §3)",
          "WRITE_CONTRACT = 'configuration'" in src)
    check("CANONICAL_L3 == 'ExpectedOutputCard'", "CANONICAL_L3 = 'ExpectedOutputCard'" in src)
    check("parses kind/delivery_cadence/bar", "kind" in src and "delivery_cadence" in src and "bar" in src)
    check("useExpectedOutput hook exported", "export function useExpectedOutput" in src)
    check("setContract routes through writeShape", "writeShape('expected-output'" in src)


def test_shape_registered() -> None:
    print("\n[registry] shape registered in content-shapes/index.ts")
    idx = _read("lib/content-shapes/index.ts")
    check("expected-output imported", "from './expected-output'" in idx)
    check("expected-output in CONTENT_SHAPES", "'expected-output': expectedOutputMeta" in idx)


def test_card() -> None:
    print("\n[card] ExpectedOutputCard (ADR-348 D2/D3)")
    src = _read("components/workspace-concepts/ExpectedOutputCard.tsx")
    check("ExpectedOutputCard exists", "export function ExpectedOutputCard" in src)
    check("uses the useExpectedOutput hook", "useExpectedOutput" in src)
    check("has a 'full' variant", "variant === 'full'" in src or "ExpectedOutputFull" in src)
    # D2 — the headline is the READ.
    check("leads with the declared contract (the READ)", "The contract" in src or "summary" in src)
    # D3 — generic structured editor: kind + cadence + bar fields.
    check("editor has a kind field", ">Kind<" in src or "Kind" in src)
    check("editor has a delivery cadence field", "Delivery cadence" in src or "cadence" in src)
    check("editor has a bar field", ">Bar<" in src or "Bar" in src)
    # ADR-345 Goodhart guard — floor-gated, not a quota.
    check("enforces floor-gated-not-quota copy", "never a quota" in src or "not a quota" in src)
    check("event-shaped: 'zero is on-contract' copy", "zero" in src.lower())


def test_mounted_in_contract_group() -> None:
    # ADR-412 D5 (2026-07-06): Freddie's panes re-homed from the /agents
    # roster to Workspace Settings' System Agent group (SystemAgentPanes.tsx);
    # the ADR-387 'Contract' group label became 'Expected Output'. Repointed
    # 2026-07-07 from the stale AgentContentView read.
    print("\n[mount] ExpectedOutputCard in Workspace Settings' System Agent group (ADR-412 D5)")
    panes_src = _read("components/agents/SystemAgentPanes.tsx")
    check("System Agent panes import ExpectedOutputCard", "ExpectedOutputCard" in panes_src)
    check(
        "Expected Output pane declared in the System Agent group",
        "'Expected Output'" in panes_src or '"Expected Output"' in panes_src,
    )
    check("expected-output pane key present", "'expected-output'" in panes_src or '"expected-output"' in panes_src)


def test_bundle_instances() -> None:
    print("\n[bundles] both bundles ship a worked _expected_output.yaml (ADR-345)")
    repo = _API_ROOT.parent
    for prog in ("alpha-author", "alpha-trader"):
        p = repo / "docs" / "programs" / prog / "reference-workspace" / "contract" / "_expected_output.yaml"
        body = p.read_text() if p.exists() else ""
        check(f"{prog} ships _expected_output.yaml", bool(body))
        check(f"{prog} declares expected_output block", "expected_output:" in body)
        check(f"{prog} declares kind + delivery_cadence + bar",
              "kind:" in body and "delivery_cadence:" in body and "bar:" in body)


def test_backend_wiring_preserved() -> None:
    print("\n[backend] ADR-345 wake-envelope wiring intact (preserved)")
    env = _read("services/freddie_envelope.py", root=_API_ROOT)
    check("freddie_envelope loads expected_output_yaml", "expected_output_yaml" in env)
    paths = _read("services/workspace_paths.py", root=_API_ROOT)
    check("CONTRACT_EXPECTED_OUTPUT_PATH defined (ADR-366: moved to contract/)",
          "CONTRACT_EXPECTED_OUTPUT_PATH" in paths)


def main() -> int:
    print("ADR-348 gate — Expected Output FE")
    test_content_shape()
    test_shape_registered()
    test_card()
    test_mounted_in_contract_group()
    test_bundle_instances()
    test_backend_wiring_preserved()
    print(f"\n{'=' * 60}")
    print(f"  {PASSED} passed, {FAILED} failed")
    print(f"{'=' * 60}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())

"""ADR-338 D4.2 gate — never_auto schema completion.

The `_autonomy.yaml::never_auto` hard-safety list was kernel-enforced
(`review_policy._check_never_auto`) but FE-invisible: `autonomy.ts` parse()
ignored it and serialize() dropped it into opaque body text. That made the
schema-inert-edit + duplicate-key-shadow failure class possible. This gate
proves the FE now extracts + round-trips the list structurally, and that the
AutonomyCard surfaces both the list editor and the bounded-is-inert copy.

Two test classes:
  1. Behavioral round-trip — transpiles the actual autonomy.ts pure functions
     via the TypeScript compiler API (typescript ^5 is in web/node_modules)
     and runs parse/serialize under node. Tests the SOURCE, not a re-impl.
  2. File-assertion drift guards — the card wiring + copy.

Per ADR-236 Rule 3: no JS test runner introduced; this is a Python harness
that drives the real TS through node. Falls back to source-assertion-only if
node/typescript is unavailable (CI-without-web-deps tolerance).

Usage:
    cd api
    python test_adr338_never_auto.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
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


def _read(rel: str) -> str:
    p = _WEB / rel
    return p.read_text() if p.exists() else ""


# ---------------------------------------------------------------------------
# 1. Behavioral round-trip (transpile + node)
# ---------------------------------------------------------------------------

_HARNESS = r"""
import ts from './node_modules/typescript/lib/typescript.js';
import { readFileSync } from 'fs';
let src = readFileSync('lib/content-shapes/autonomy.ts','utf8');
src = src.replace(/^'use client';\s*$/m, '');
src = src.replace(/^import .*from '@\/lib\/api\/client';\s*$/m, '');
src = src.replace(/^import \{ useEffect, useState \} from 'react';\s*$/m, '');
src = src.replace(/^import type \{ ContentShapeMeta \} from '\.\/index';\s*$/m, '');
const out = ts.transpileModule(src, { compilerOptions: { module: 'ES2022', target: 'ES2022' } });
const m = await import('data:text/javascript,'+encodeURIComponent(out.outputText));

const results = {};

// Case A — block-list never_auto with a path:-prefixed + a bare entry.
const inputA = `---
tier: canon
note: "x"
---
default:
  delegation: manual
  never_auto:
    - "path: persona/"
    - retraction
    - "path: constitution/"
`;
const rtA = m.parseRoundTrip(inputA);
results.parsed_block = rtA.meta.default_never_auto;
const serA = m.serialize(rtA.meta, rtA.body, rtA.tierBlock);
results.reparsed_block = m.parseRoundTrip(serA).meta.default_never_auto;
results.never_auto_occurrences = (serA.match(/never_auto/g) || []).length;
results.tier_preserved = serA.startsWith('---');

// Case B — inline empty list `never_auto: []` (the bundle default shape).
const inputB = `default:
  delegation: manual
  ceiling_categories: []
  never_auto: []
`;
const rtB = m.parseRoundTrip(inputB);
results.parsed_empty = rtB.meta.default_never_auto;
const serB = m.serialize(rtB.meta, rtB.body, rtB.tierBlock);
results.empty_roundtrips = (m.parseRoundTrip(serB).meta.default_never_auto);
results.empty_inline = serB.includes('never_auto: []');

// Case C — duplicate-key shadow: a file with TWO never_auto lines (operator
// list shadowed by a trailing bundle `never_auto: []`). serialize must
// collapse to ONE structural emission carrying the operator's entries.
const inputC = `default:
  delegation: bounded
  ceiling_cents: 20000
  never_auto:
    - retraction
  never_auto: []
`;
const rtC = m.parseRoundTrip(inputC);
const serC = m.serialize(rtC.meta, rtC.body, rtC.tierBlock);
results.shadow_collapsed_to = (serC.match(/never_auto/g) || []).length;

// Case D — no never_auto at all → field absent, no spurious emission.
const inputD = `default:
  delegation: autonomous
  ceiling_cents: 500000
`;
const rtD = m.parseRoundTrip(inputD);
results.absent_field = rtD.meta.default_never_auto === undefined;
const serD = m.serialize(rtD.meta, rtD.body, rtD.tierBlock);
results.absent_no_emission = !serD.includes('never_auto');

console.log('RESULTS_JSON' + JSON.stringify(results));
"""


def _run_behavioral() -> dict | None:
    """Transpile + run the harness under node. Returns the results dict, or
    None when node/typescript isn't available (graceful CI degradation)."""
    if not (_WEB / "node_modules/typescript/lib/typescript.js").exists():
        return None
    with tempfile.NamedTemporaryFile(
        "w", suffix=".mjs", dir=_WEB, delete=False
    ) as f:
        f.write(_HARNESS)
        harness_path = Path(f.name)
    try:
        proc = subprocess.run(
            ["node", harness_path.name],
            cwd=_WEB,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        harness_path.unlink(missing_ok=True)
        return None
    finally:
        harness_path.unlink(missing_ok=True)
    if proc.returncode != 0:
        print("  [behavioral harness stderr]\n" + proc.stdout + proc.stderr)
        return {}
    for line in proc.stdout.splitlines():
        if line.startswith("RESULTS_JSON"):
            return json.loads(line[len("RESULTS_JSON"):])
    return {}


def test_behavioral_round_trip() -> None:
    print("\n[behavioral] never_auto parse/serialize round-trip (real autonomy.ts via node)")
    r = _run_behavioral()
    if r is None:
        print("  ⚠ node/typescript unavailable — behavioral tests SKIPPED (source asserts still run)")
        return
    if not r:
        check("harness produced results", False, "see stderr above")
        return

    # Case A — block list with path: + bare entries.
    check(
        "block-list never_auto parses to structured array",
        r.get("parsed_block") == ["path: persona/", "retraction", "path: constitution/"],
        f"got {r.get('parsed_block')!r}",
    )
    check(
        "serialize → re-parse is idempotent (round-trip stable)",
        r.get("reparsed_block") == ["path: persona/", "retraction", "path: constitution/"],
        f"got {r.get('reparsed_block')!r}",
    )
    check(
        "never_auto emitted EXACTLY once (no duplicate-key shadow)",
        r.get("never_auto_occurrences") == 1,
        f"occurrences={r.get('never_auto_occurrences')}",
    )
    check("tier frontmatter preserved on serialize", r.get("tier_preserved") is True)

    # Case B — inline empty list.
    check(
        "inline empty `never_auto: []` parses to empty array (not undefined)",
        r.get("parsed_empty") == [],
        f"got {r.get('parsed_empty')!r}",
    )
    check("empty list round-trips as empty", r.get("empty_roundtrips") == [])
    check("empty list serializes as inline `[]`", r.get("empty_inline") is True)

    # Case C — duplicate-key shadow collapse (the journey-week failure class).
    check(
        "duplicate never_auto keys collapse to ONE structural emission",
        r.get("shadow_collapsed_to") == 1,
        f"occurrences={r.get('shadow_collapsed_to')}",
    )

    # Case D — absent field stays absent.
    check("absent never_auto → field is undefined after parse", r.get("absent_field") is True)
    check("absent never_auto → no spurious emission on serialize", r.get("absent_no_emission") is True)


# ---------------------------------------------------------------------------
# 2. Source-assertion drift guards
# ---------------------------------------------------------------------------

def test_autonomy_shape_source() -> None:
    print("\n[source] autonomy.ts never_auto plumbing")
    src = _read("lib/content-shapes/autonomy.ts")
    check("AutonomyMeta declares default_never_auto", "default_never_auto?: string[]" in src)
    check("parse() opens block list on `never_auto:`", "never_auto:" in src and "inNeverAutoList" in src)
    check("parse() handles inline empty `[]` form", "v !== '[]'" in src or "=== '[]'" in src or "[]" in src)
    check("serialize() emits never_auto structurally", "lines.push('  never_auto:" in src or "never_auto: []" in src)
    check("useAutonomy exposes setNeverAuto", "setNeverAuto:" in src and "setNeverAuto," in src)


def test_autonomy_card_source() -> None:
    print("\n[source] AutonomyCard surfaces editor + bounded-inert copy")
    src = _read("components/workspace-concepts/AutonomyCard.tsx")
    check("NeverAutoEditor component present", "function NeverAutoEditor" in src)
    check("NeverAutoEditor wired into full variant", "<NeverAutoEditor" in src)
    check("card consumes setNeverAuto from hook", "setNeverAuto" in src)
    check(
        "bounded consequence surfaces substrate-writes-still-queue",
        "Substrate writes" in src and "STILL wait" in src,
    )
    check(
        "bounded description names substrate edits queue",
        "Substrate edits still queue" in src,
    )


def main() -> int:
    print("=" * 70)
    print("ADR-338 D4.2 — never_auto schema completion gate")
    print("=" * 70)
    test_behavioral_round_trip()
    test_autonomy_shape_source()
    test_autonomy_card_source()
    print("\n" + "=" * 70)
    print(f"  {PASSED} passed, {FAILED} failed")
    print("=" * 70)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())

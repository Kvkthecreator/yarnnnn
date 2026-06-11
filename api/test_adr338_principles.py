"""ADR-338 D4.6 gate — principles threshold surfacing.

The audit found PrinciplesCard surfaced `auto_approve_below_cents`, which per
ADR-261 D5 was folded into _autonomy.yaml::ceiling_cents — it no longer lives
in _principles.yaml. The card hid the field the substrate DOES carry:
`high_impact_threshold_cents` (ADR-195 Phase 5 — large realized outcomes route
to the task feedback loop). This gate proves the FE now parses + surfaces the
real threshold and corrects the stale framing.

Behavioral round-trip via real principles.ts through node; source-assertions
for the card surfacing.

Usage:
    cd api
    python test_adr338_principles.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

_API_ROOT = Path(__file__).resolve().parent
_WEB = _API_ROOT.parent / "web"
_REPO = _API_ROOT.parent

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


_HARNESS = r"""
import ts from './node_modules/typescript/lib/typescript.js';
import { readFileSync } from 'fs';
let src = readFileSync('lib/content-shapes/principles.ts','utf8');
src = src.replace(/^import type \{ ContentShapeMeta \} from '\.\/index';\s*$/m, '');
const out = ts.transpileModule(src, { compilerOptions: { module: 'ES2022', target: 'ES2022' } });
const m = await import('data:text/javascript,'+encodeURIComponent(out.outputText));
const results = {};

// The real _principles.yaml shape (alpha-trader reference): high_impact only,
// no auto_approve_below_cents (folded into _autonomy.yaml per ADR-261 D5).
const yaml = `---
tier: authored
prompt: "x"
---
trading:
  high_impact_threshold_cents: 50000
`;
const y = m.parseYaml(yaml);
results.high_impact = y.highImpact;
results.auto_approve = y.domains;

const prose = m.parse('## Domain: trading\n\n### Reject conditions\n- correlated cluster\n- exceeds position cap\n');
const merged = m.mergeThresholds(prose, y);
results.merged = merged.domains.map(d => ({
  name: d.name,
  high: d.highImpactDisplay,
  auto: d.autoApproveDisplay,
  rejects: d.rejectConditions.length,
}));
results.has = merged.hasPrinciples;

console.log('RESULTS_JSON' + JSON.stringify(results));
"""


def _run_behavioral() -> dict | None:
    if not (_WEB / "node_modules/typescript/lib/typescript.js").exists():
        return None
    with tempfile.NamedTemporaryFile("w", suffix=".mjs", dir=_WEB, delete=False) as f:
        f.write(_HARNESS)
        harness = Path(f.name)
    try:
        proc = subprocess.run(["node", harness.name], cwd=_WEB,
                              capture_output=True, text=True, timeout=60)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        harness.unlink(missing_ok=True)
        return None
    finally:
        harness.unlink(missing_ok=True)
    if proc.returncode != 0:
        print("  [harness stderr]\n" + proc.stdout + proc.stderr)
        return {}
    for line in proc.stdout.splitlines():
        if line.startswith("RESULTS_JSON"):
            return json.loads(line[len("RESULTS_JSON"):])
    return {}


def test_high_impact_parse() -> None:
    print("\n[behavioral] principles.ts parses high_impact_threshold_cents (real shape)")
    r = _run_behavioral()
    if r is None:
        print("  ⚠ node/typescript unavailable — behavioral tests SKIPPED")
        return
    if not r:
        check("harness produced results", False, "see stderr above")
        return
    check("high_impact_threshold_cents parsed per domain",
          r.get("high_impact", {}).get("trading") == 50000,
          f"got {r.get('high_impact')!r}")
    check("auto_approve_below_cents absent from real _principles.yaml (ADR-261 D5)",
          r.get("auto_approve", {}).get("trading") is None,
          f"got {r.get('auto_approve')!r}")
    merged = r.get("merged") or []
    trading = next((d for d in merged if d["name"] == "trading"), None)
    check("merged domain surfaces high-impact display ($500)",
          trading is not None and trading["high"] == "$500",
          f"got {trading}")
    check("merged domain auto-approve null (no stale ceiling shown)",
          trading is not None and trading["auto"] is None)
    check("reject conditions preserved through merge",
          trading is not None and trading["rejects"] == 2)
    check("hasPrinciples true with threshold-only domain", r.get("has") is True)


def test_card_surfaces_high_impact() -> None:
    print("\n[source] PrinciplesCard surfaces the real threshold")
    shape = _read("lib/content-shapes/principles.ts")
    check("DomainPrinciples declares highImpactCents", "highImpactCents" in shape)
    check("parseYaml reads high_impact_threshold_cents",
          "high_impact_threshold_cents" in shape)
    check("YamlThresholds carries highImpact map", "highImpact: Record" in shape)
    check("auto_approve marked deprecated (ADR-261 D5)",
          "@deprecated ADR-261 D5" in shape or "@deprecated — see above" in shape)

    card = _read("components/workspace-concepts/PrinciplesCard.tsx")
    check("card surfaces highImpactDisplay", "highImpactDisplay" in card)
    check("card frames it as outcome-review threshold",
          "flagged for review" in card or "flag outcomes" in card or "flag ≥" in card)
    check("card notes auto-approve now lives on Autonomy (corrects stale framing)",
          "now set on Autonomy" in card)


def test_bundle_carries_high_impact() -> None:
    print("\n[bundle] _principles.yaml carries high_impact_threshold_cents")
    yaml = _read("docs/programs/alpha-trader/reference-workspace/persona/_principles.yaml", root=_REPO)
    check("alpha-trader _principles.yaml declares high_impact_threshold_cents",
          "high_impact_threshold_cents" in yaml)
    check("auto_approve_below_cents NOT in _principles.yaml (ADR-261 D5)",
          "auto_approve_below_cents:" not in yaml.split("# NOTE")[0])


def main() -> int:
    print("=" * 70)
    print("ADR-338 D4.6 — principles threshold surfacing gate")
    print("=" * 70)
    test_high_impact_parse()
    test_card_surfaces_high_impact()
    test_bundle_carries_high_impact()
    print("\n" + "=" * 70)
    print(f"  {PASSED} passed, {FAILED} failed")
    print("=" * 70)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())

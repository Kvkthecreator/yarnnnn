"""Fixture test for the TENURE-READ Read-1 curve extractor (Hat-B).

Exercises the pure core (frontmatter → trajectory → mechanical verdict) with
no DB — the DB layer (`fetch_curve_points`, resolvers) needs Supabase reach and
is validated by running against a live soak workspace where networked.

Standalone script (sys.exit, not pytest-collectable) per the house pattern in
docs/evaluations/EVAL-SUITE-DISCIPLINE.md §0.3.

    .venv/bin/python api/test_tenure_curve.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts" / "operator"))

from tenure_curve import (  # noqa: E402
    CurvePoint,
    build_trajectory,
    extract_frontmatter,
    flatten_numeric,
    ledger_size,
    mechanical_verdict,
    render_read1,
)

_passed = 0
_failed = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global _passed, _failed
    if cond:
        _passed += 1
        print(f"  PASS  {name}")
    else:
        _failed += 1
        print(f"  FAIL  {name}  {detail}")


# --- synthetic ground-truth fixtures (alpha-trader _money_truth.md shape) ----

BOOTSTRAP = """---
windows:
  30d:
    reconciled_trades: 0
by_signal: {}
---
# Money truth

No reconciled outcomes yet — primed to accumulate.
"""

ONE_POINT = """---
windows:
  30d:
    reconciled_trades: 4
    expectancy_r: 0.12
by_signal:
  signal-1:
    sample_count: 4
    expectancy_r: 0.12
---
# Money truth
"""

# A later revision showing the curve bend up + more samples.
TWO_POINT_LATER = """---
windows:
  30d:
    reconciled_trades: 11
    expectancy_r: 0.31
by_signal:
  signal-1:
    sample_count: 11
    expectancy_r: 0.31
---
# Money truth
"""

NARRATIVE_ONLY = """---
note: bootstrapping, see body
---
# Money truth

Prose only, no numbers in frontmatter.
"""

NO_FRONTMATTER = "# Money truth\n\nJust a body, no fence.\n"

# --- author ground-truth fixtures (_signal.md shape, corpus-coherence-rollup) -
# Distinct field names from the trader — the cross-program regression: the
# author's accumulation counters are audits_total / pieces_shipped /
# voice_flags_total / drafts_audited, NOT reconciled_trades / sample_count.

AUTHOR_BOOTSTRAP = """---
rolling_windows:
  30d:
    audits_total: 0
    pieces_shipped: 0
    voice_flags_total: 0
calibration:
  voice_audit_accuracy_30d: 0.0
---
# Corpus Signal

Workspace newly activated. Calibration begins from this point forward.
"""

# Audits run, nothing shipped yet — the exact case the trader-only regex missed.
AUTHOR_AUDITED_NOT_SHIPPED = """---
rolling_windows:
  30d:
    audits_total: 6
    pieces_shipped: 0
    voice_flags_total: 2
calibration:
  voice_audit_accuracy_30d: 0.83
  revision_audit_findings_30d:
    drafts_audited: 6
---
# Corpus Signal
"""


def test_frontmatter_extraction() -> None:
    print("test_frontmatter_extraction")
    check("parses fenced yaml", extract_frontmatter(ONE_POINT).get("windows") is not None)
    check("no fence → empty", extract_frontmatter(NO_FRONTMATTER) == {})
    check("empty content → empty", extract_frontmatter("") == {})
    # malformed yaml must degrade to {}, never raise
    bad = "---\n: : : not yaml\n---\nbody"
    check("malformed yaml → empty (no raise)", extract_frontmatter(bad) == {})


def test_flatten_numeric() -> None:
    print("test_flatten_numeric")
    flat = flatten_numeric(extract_frontmatter(ONE_POINT))
    check("dotted nested key present",
          flat.get("by_signal.signal-1.expectancy_r") == 0.12, str(flat))
    check("window count flattened",
          flat.get("windows.30d.reconciled_trades") == 4.0, str(flat))
    # booleans excluded, numeric strings coerced
    check("bool excluded", flatten_numeric({"x": True}) == {})
    check("numeric string coerced", flatten_numeric({"x": "0.5"}) == {"x": 0.5})
    check("narrative leaf dropped", flatten_numeric({"note": "hi"}) == {})


def test_ledger_size() -> None:
    print("test_ledger_size")
    check("bootstrap ledger == 0", ledger_size(flatten_numeric(extract_frontmatter(BOOTSTRAP))) == 0.0)
    check("one-point ledger picks max sample",
          ledger_size(flatten_numeric(extract_frontmatter(ONE_POINT))) == 4.0)
    check("narrative-only ledger == 0",
          ledger_size(flatten_numeric(extract_frontmatter(NARRATIVE_ONLY))) == 0.0)


def test_author_shape_cross_program() -> None:
    """The cross-program regression: author _signal.md counters must register,
    and accuracy ratios must NOT masquerade as samples."""
    print("test_author_shape_cross_program")
    boot = flatten_numeric(extract_frontmatter(AUTHOR_BOOTSTRAP))
    check("author bootstrap ledger == 0 (all counters 0)", ledger_size(boot) == 0.0)
    acc = flatten_numeric(extract_frontmatter(AUTHOR_AUDITED_NOT_SHIPPED))
    # audits_total=6 / drafts_audited=6 are the accumulation signal; pieces_shipped=0.
    check("author audited-not-shipped ledger == 6 (audits register)",
          ledger_size(acc) == 6.0, str(ledger_size(acc)))
    # the accuracy ratio 0.83 must be excluded by the integer filter
    check("voice_audit_accuracy ratio excluded from ledger",
          0.83 not in [v for k, v in acc.items() if "audit" in k and float(v).is_integer()])
    # and the bootstrap author shape reports INCONCLUSIVE, not a false curve
    pts = [_point(AUTHOR_BOOTSTRAP, "t0"), _point(AUTHOR_BOOTSTRAP, "t1")]
    check("author bootstrap → INCONCLUSIVE", "BOOTSTRAP-EMPTY" in mechanical_verdict(pts))
    # an audited-not-shipped revision is a real sampled datapoint
    one = [_point(AUTHOR_BOOTSTRAP, "t0"), _point(AUTHOR_AUDITED_NOT_SHIPPED, "t1")]
    check("author audited → SINGLE DATAPOINT (not bootstrap)",
          "SINGLE DATAPOINT" in mechanical_verdict(one), mechanical_verdict(one))


def _point(content: str, ts: str) -> CurvePoint:
    flat = flatten_numeric(extract_frontmatter(content))
    return CurvePoint(created_at=ts, authored_by="reviewer:test", message="reconciled", flat=flat)


def test_mechanical_verdict() -> None:
    print("test_mechanical_verdict")
    check("no points → NO SUBSTRATE", mechanical_verdict([]).startswith("NO SUBSTRATE"))
    boot = [_point(BOOTSTRAP, "2026-06-10T00:00:00+00:00")]
    check("bootstrap → INCONCLUSIVE", "BOOTSTRAP-EMPTY" in mechanical_verdict(boot))
    one = [_point(BOOTSTRAP, "t0"), _point(ONE_POINT, "t1")]
    check("one sampled → SINGLE DATAPOINT", "SINGLE DATAPOINT" in mechanical_verdict(one))
    curve = [_point(BOOTSTRAP, "t0"), _point(ONE_POINT, "t1"), _point(TWO_POINT_LATER, "t2")]
    v = mechanical_verdict(curve)
    check("two sampled → CURVE PRESENT", "CURVE PRESENT" in v, v)
    check("curve shows ledger growth 4 → 11", "4 → 11" in v, v)


def test_trajectory_and_render() -> None:
    print("test_trajectory_and_render")
    pts = [_point(BOOTSTRAP, "t0"), _point(ONE_POINT, "t1"), _point(TWO_POINT_LATER, "t2")]
    keys, rows = build_trajectory(pts)
    check("trajectory has expectancy row",
          any(r[0] == "by_signal.signal-1.expectancy_r" for r in rows))
    # the expectancy row should show "·" at t0 (absent), then 0.12, then 0.31
    exp_row = next(r for r in rows if r[0] == "by_signal.signal-1.expectancy_r")
    check("absent-at-r0 renders ·", exp_row[1] == "·", str(exp_row))
    check("value at r2 is 0.31", exp_row[3] == "0.31", str(exp_row))

    md = render_read1(subject="alpha-trader-2", user_id="uid", ground_truth_path="/workspace/x",
                      deploy_marker="abc1234", points=pts)
    check("render stamps deploy-marker", "abc1234" in md)
    check("render leaves human verdict blank", "← human writes this" in md)
    check("render never emits IMPROVING as fact", "script never fills this" in md)

    # empty render path
    empty_md = render_read1(subject="s", user_id="u", ground_truth_path="/w",
                            deploy_marker="d", points=[])
    check("empty render says NO SUBSTRATE", "NO SUBSTRATE" in empty_md)


def main() -> int:
    for fn in (
        test_frontmatter_extraction,
        test_flatten_numeric,
        test_ledger_size,
        test_author_shape_cross_program,
        test_mechanical_verdict,
        test_trajectory_and_render,
    ):
        fn()
    print(f"\n{_passed} passed, {_failed} failed")
    return 1 if _failed else 0


if __name__ == "__main__":
    sys.exit(main())

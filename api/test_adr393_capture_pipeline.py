"""ADR-393 regression gate — the perception/capture pipeline.

Capture is deterministic, upstream, intent-free perception (ADR-335/389:
peripherals judged for health not honesty). ADR-393 moves it OUT of the wake
funnel into a DISTINCT lane: _recurrences.yaml becomes judgment-only, and
deterministic intake lives in _captures.yaml, run by services.capture outside
wake.py. The "theatre" bypass (wake.py::_dispatch_mechanical) is deleted, not
carried as a fallback (Singular Implementation).

Pure-Python structural gate (no DB, no platform APIs). Asserts:
  1. The recurrence schema has NO `mode` field (deleted).
  2. The recurrence parser DROPS a legacy `mode: mechanical` entry (it must not
     reach the wake funnel — its @primitive prompt is not a judgment prompt).
  3. _captures.yaml parses: slug + schedule + primitive directive + options.
  4. The lane's directive parser handles multiline + no-arg @primitive forms.
  5. compute_next_run_at duck-types a CaptureDeclaration (semantic schedules +
     fire_on_activation), so the trader's market-anchored mirrors move as-is.
  6. wake.py no longer defines _dispatch_mechanical / mechanical helpers, and
     `mechanical` is gone from FunnelDecision (funnel serves judgment only).
  7. The capture lane records execution_events with funnel_decision="capture".
  8. The health signal is THIN (status/observed_at/items/target/last_error only)
     — not a content distillation.
"""

import inspect
import sys
from datetime import datetime, timezone


def _check(label, ok, detail=""):
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {label}" + (f" — {detail}" if detail and not ok else ""))
    return bool(ok)


def main():
    results = []

    # 1 — Recurrence schema has no `mode`
    from services.recurrence import Recurrence, parse_recurrences_yaml
    fields = set(Recurrence.__dataclass_fields__.keys())
    results.append(_check(
        "1. Recurrence has NO `mode` field (deleted)",
        "mode" not in fields,
        f"fields={sorted(fields)}",
    ))

    # 2 — recurrence parser drops a legacy mechanical entry
    rdocs = """
- slug: signal-evaluation
  schedule: "0 9 * * 1-5"
  prompt: "Evaluate signals."
- slug: track-positions
  schedule: "* 9-16 * * 1-5"
  mode: mechanical
  prompt: |
    @primitive: SyncPlatformState(tool="platform_trading_get_positions", write_to="x")
"""
    recs = parse_recurrences_yaml(rdocs, user_id="u1")
    slugs = [r.slug for r in recs]
    results.append(_check(
        "2. recurrence parser DROPS mode:mechanical (never reaches wake funnel)",
        slugs == ["signal-evaluation"],
        f"kept={slugs}",
    ))

    # 3 — _captures.yaml parses
    from services.capture.declarations import (
        CaptureDeclaration, parse_captures_yaml, capture_signal_path, captures_path,
    )
    cdocs = """
captures:
  - slug: track-positions
    schedule: "@every 1min during regular_hours"
    primitive: |
      @primitive: SyncPlatformState(tool="platform_trading_get_positions", write_to="operation/portfolio/positions/{symbol}.yaml", iterate_field="positions", item_key="symbol", diff_aware=true)
    display_name: "Position State Mirror"
"""
    decls = parse_captures_yaml(cdocs, user_id="u1")
    ok3 = (
        len(decls) == 1
        and decls[0].slug == "track-positions"
        and decls[0].schedule == "@every 1min during regular_hours"
        and decls[0].primitive.startswith("@primitive: SyncPlatformState")
        and decls[0].options.get("display_name") == "Position State Mirror"
    )
    results.append(_check("3. _captures.yaml parses (slug + schedule + primitive + options)", ok3,
                          f"decls={decls}"))
    results.append(_check(
        "3b. capture paths are the canonical siblings",
        captures_path() == "/workspace/_captures.yaml"
        and capture_signal_path() == "/workspace/_capture_signal.yaml",
    ))

    # 3c — a capture entry with no primitive directive is dropped
    dropped = parse_captures_yaml("captures:\n  - slug: broken\n    schedule: '0 * * * *'\n", user_id="u1")
    results.append(_check("3c. capture with no `primitive:` is dropped", dropped == [],
                          f"got={dropped}"))

    # 4 — the lane's directive parser
    from services.capture.lane import parse_primitive_directive
    ml = """@primitive: SyncPlatformState(
      tool="platform_trading_get_positions",
      write_to="operation/portfolio/positions/{symbol}.yaml",
      iterate_field="positions", item_key="symbol", diff_aware=true
    )"""
    n1, a1 = parse_primitive_directive(ml)
    n2, a2 = parse_primitive_directive("@primitive: TrackRegime()")
    ok4 = (
        n1 == "SyncPlatformState" and a1.get("tool") == "platform_trading_get_positions"
        and a1.get("diff_aware") is True
        and n2 == "TrackRegime" and a2 == {}
    )
    results.append(_check("4. directive parser handles multiline + no-arg @primitive", ok4,
                          f"({n1},{a1}) ({n2},{a2})"))

    # 5 — compute_next_run_at duck-types a CaptureDeclaration
    from services.scheduling import compute_next_run_at
    now = datetime(2026, 7, 1, 10, 0, tzinfo=timezone.utc)
    plain = CaptureDeclaration(slug="x", schedule="0 11 * * *", primitive="@primitive: TrackForeign()")
    nr = compute_next_run_at(plain, last_run_at=None, now=now)
    activ = CaptureDeclaration(
        slug="y", schedule="0 11 * * *", primitive="@primitive: TrackRegime()",
        options={"fire_on_activation": True},
    )
    nr2 = compute_next_run_at(activ, last_run_at=None, now=now)
    results.append(_check(
        "5. compute_next_run_at duck-types CaptureDeclaration (+fire_on_activation)",
        nr is not None and nr2 == now,
        f"nr={nr} nr2={nr2}",
    ))

    # 6 — wake.py has no mechanical machinery
    import services.wake as wake
    ok6 = (
        not hasattr(wake, "_dispatch_mechanical")
        and not hasattr(wake, "_parse_primitive_directive")
        and not hasattr(wake, "_required_platform_for_primitive")
        and "mechanical" not in getattr(wake.FunnelDecision, "__args__", ())
    )
    results.append(_check(
        "6. wake.py has no _dispatch_mechanical + FunnelDecision drops `mechanical`",
        ok6,
        f"FunnelDecision={getattr(wake.FunnelDecision, '__args__', ())}",
    ))

    # 7 — the lane records funnel_decision="capture" (source-level assertion)
    lane_src = inspect.getsource(sys.modules["services.capture.lane"])
    results.append(_check(
        "7. capture lane stamps funnel_decision=\"capture\" on execution_events",
        'funnel_decision="capture"' in lane_src,
    ))

    # 8 — the health signal is thin (write_capture_signal params)
    from services.capture.declarations import write_capture_signal
    sig_params = set(inspect.signature(write_capture_signal).parameters.keys())
    # thin surface: no 'entries'/'content'/'distillation' — only liveness/freshness
    forbidden = {"entries", "content", "distillation", "blocks"}
    results.append(_check(
        "8. health signal is THIN (no content-distillation params)",
        forbidden.isdisjoint(sig_params)
        and {"status", "observed_at", "items", "target", "last_error"} <= sig_params,
        f"params={sorted(sig_params)}",
    ))

    passed = sum(1 for r in results if r)
    total = len(results)
    print(f"\nADR-393 capture pipeline: {passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())

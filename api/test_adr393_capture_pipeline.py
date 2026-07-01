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
  9. _peripheral_field_fact reads the capture health signal (ADR-393 D3 — the
     ADR-392 Phase B data source).
 10. Kind-isolation: the capture scheduler/drainer is .eq("kind","capture")-scoped
     on every tasks-table touch, so the two lanes' materializers write disjoint
     rows and never clobber each other (the correctness property of index reuse).
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

    # 9 — the steward's peripheral-field fact reads the capture health signal
    # (ADR-393 D3 — this is the freshness the fact was pointing at, + the
    # ADR-392 Phase B data source).
    import services.freddie_envelope as _env
    env_src = inspect.getsource(_env)
    results.append(_check(
        "9. _peripheral_field_fact reads the capture health signal (ADR-393 D3)",
        "read_capture_signal" in env_src and "_peripheral_field_fact" in env_src,
    ))

    # 10 — kind-isolation invariant: the capture scheduler NEVER touches a
    # non-capture tasks row (every read/write/delete/claim is .eq("kind", ...)
    # scoped to CAPTURE_KIND), so the two materializers write DISJOINT row sets
    # and can't clobber each other. This is the load-bearing correctness property
    # of reusing the shared `tasks` index (ADR-393 §4-Q2).
    import services.capture.scheduling as _csched
    import services.capture.drainer as _cdrain
    cs_src = inspect.getsource(_csched)
    cd_src = inspect.getsource(_cdrain)
    both = cs_src + cd_src
    import re as _re10
    # The DANGER is a user_id/slug-scoped write (update/delete) that omits kind —
    # that could touch a same-named recurrence row. Every such write in the
    # capture lane must ALSO carry .eq("kind", CAPTURE_KIND). (Writes scoped by a
    # row `id` are safe by construction — the id came from a kind='capture' read;
    # inserts are safe — they set kind=CAPTURE_KIND in the payload.)
    # A capture write chains .eq("slug", ...) → assert each is kind-guarded too.
    slug_scoped = len(_re10.findall(r'\.eq\(\s*"slug"', both))
    kind_guarded = len(_re10.findall(r'\.eq\(\s*"kind",\s*CAPTURE_KIND\s*\)', both))
    # Every capture insert carries kind in its payload dict.
    payload_kind = '"kind": CAPTURE_KIND' in both
    results.append(_check(
        "10. capture lane is kind-scoped (no clobber of same-named recurrence rows)",
        slug_scoped > 0 and kind_guarded >= slug_scoped and payload_kind,
        f"slug-scoped writes={slug_scoped}, kind-guards={kind_guarded}, payload-kind={payload_kind}",
    ))

    passed = sum(1 for r in results if r)
    total = len(results)
    print(f"\nADR-393 capture pipeline: {passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())

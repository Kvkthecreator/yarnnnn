"""ADR-439 regression gate — BYOK + the enterprise tier.

Locks the load-bearing invariants:
  1. `enterprise` is a real tier; ONLY it has byok_available.
  2. The BYOK cost-override records cost_usd=0 (draws nothing); non-BYOK is
     byte-identical (computed from tokens).
  3. The BYOK resolver is total + fail-safe (None on any error → managed default).
  4. Provider parsing + the provider allow-list.
  5. N=1 / non-enterprise safety: byok_available is False everywhere but enterprise,
     so a normal workspace never routes to a customer key.

Run: python test_adr439_byok_enterprise.py  (or via pytest).
"""

import inspect


def _check(label, cond):
    print(f"  [{'PASS' if cond else 'FAIL'}] {label}")
    return bool(cond)


def run():
    results = []

    import services.billing_tiers as bt

    # ── 1. The enterprise tier + byok_available gate ────────────────────────
    results.append(_check(
        "enterprise is a real tier",
        "enterprise" in bt.TIER_CONFIG and bt.normalize_tier("enterprise") == "enterprise",
    ))
    results.append(_check(
        "ONLY enterprise has byok_available",
        bt.tier_byok_available("enterprise") is True
        and all(bt.tier_byok_available(t) is False for t in ("free", "starter", "pro")),
    ))
    results.append(_check(
        "enterprise is hidden (sales-led, not on the self-serve ladder)",
        bt.tier_hidden("enterprise") is True
        and "enterprise" not in {row["tier"] for row in bt.public_tier_ladder()},
    ))

    # ── 2. The metering override (cost-to-us = 0 for BYOK) ──────────────────
    import services.telemetry as tel
    src = inspect.getsource(tel.record_execution_event)
    results.append(_check(
        "record_execution_event has cost_override_usd param",
        "cost_override_usd" in inspect.signature(tel.record_execution_event).parameters,
    ))
    results.append(_check(
        "override is checked BEFORE the token compute (BYOK → 0, else computed)",
        "if cost_override_usd is not None:" in src and "elif input_tokens" in src,
    ))
    # non-BYOK cost is still real (byte-identical) — the compute path is untouched
    normal = tel.compute_cost_usd_inclusive(
        model="claude-sonnet-4-6", input_tokens=1000, output_tokens=500,
        cache_read_tokens=0, cache_create_tokens=0,
    )
    results.append(_check("non-BYOK cost is computed > 0 (byte-identical path)", normal > 0))

    # ── 3. The router accepts a per-call api_key (BYOK injection point) ──────
    import services.model_router as mr
    results.append(_check(
        "route_completion + route_completion_stream take api_key",
        "api_key" in inspect.signature(mr.route_completion).parameters
        and "api_key" in inspect.signature(mr.route_completion_stream).parameters,
    ))
    rc_src = inspect.getsource(mr.route_completion)
    results.append(_check(
        "api_key only sets the kwarg when provided (managed default = byte-identical)",
        'if api_key:' in rc_src and 'kwargs["api_key"] = api_key' in rc_src,
    ))

    # ── 4. BYOK resolver: provider parse + allow-list + fail-safe ───────────
    import services.byok as byok
    results.append(_check(
        "provider_from_model strips the prefix",
        byok.provider_from_model("gemini/gemini-2.5-flash") == "gemini"
        and byok.provider_from_model("anthropic/claude-sonnet-4-6") == "anthropic",
    ))
    # Derived, not pinned: the assertion is the INVARIANT (BYOK covers exactly
    # the providers a lane can route to), so adding an engine to LANE_MODELS
    # never reads as a violation. The old form hard-coded the four-provider
    # spelling and went red on a legitimate ADDITION.
    from services.lane_runner import LANE_MODELS
    _lane_providers = {byok.provider_from_model(m) for m in LANE_MODELS}
    results.append(_check(
        "BYOK_PROVIDERS is the LANE_MODELS provider set",
        set(byok.BYOK_PROVIDERS) == _lane_providers,
    ))
    # get_byok_key is total: a None workspace_id (N=1 pre-resolve) → None (managed)
    results.append(_check(
        "get_byok_key(None ws) → None (managed default, never raises)",
        byok.get_byok_key(client=None, workspace_id=None, provider="anthropic") is None,
    ))
    # set_byok_key rejects an unknown provider (clean 400 at the route)
    rejected = False
    try:
        byok.set_byok_key(client=None, workspace_id="w", provider="bogus", plaintext_key="k")
    except ValueError:
        rejected = True
    results.append(_check("set_byok_key rejects an unknown provider", rejected))

    # ── 5. The lane runner resolves BYOK once + threads override ─────────────
    import services.lane_runner as lr
    lr_src = inspect.getsource(lr)
    results.append(_check(
        "lane runner resolves BYOK + passes api_key + cost_override to the ledger",
        "_resolve_byok_key(auth, model)" in lr_src
        and "api_key=byok_key" in lr_src
        and "cost_override_usd=byok_cost_override" in lr_src,
    ))

    # ── 6. §4 F1 — unpriced models are HARD-BLOCKED pre-call ────────────────
    results.append(_check(
        "every LANE_MODELS entry is priced (F1 never trips a real lane)",
        all(not lr.unpriced_lane_model(m) for m in lr.LANE_MODELS),
    ))
    results.append(_check(
        "unpriced_lane_model flags a model with no _BILLING_RATES row",
        lr.unpriced_lane_model("anthropic/claude-not-a-real-model") is True,
    ))
    def _no_billable_call_on_an_unpriced_model() -> bool:
        """EXECUTE the invariant: drive both lane loops with an unpriced model
        and assert the router is never reached.

        ⚠️ THIS CHECK WAS A SOURCE-TEXT PROXY AND BROKE THREE TIMES — once per
        ADR, each time on a change that PRESERVED the invariant:

          ADR-439 (original)  pinned the flag's name `model_router_enabled`;
                              ADR-557 D2 renamed it to `lanes_enabled` → red on
                              a rename.
          ADR-557 (repair 1)  matched the bare module import; swept in an
                              unrelated `ledger_model_name` import → red for a
                              different wrong reason.
          ADR-559 (repair 2)  counted matches file-wide; a new helper
                              (`lane_model_availability`) legitimately called
                              `unpriced_lane_model` → a third match read as a
                              violation.

        Three repairs, three symptoms, one cause: **the check measured where
        TEXT sits, while the invariant is about what the CODE DOES.** Any
        refactor that keeps the guarantee but moves the text goes red, and each
        repair only narrowed which refactors would break it next.

        So it now runs the thing. `unpriced_lane_model` can be extracted,
        inlined, renamed, or called from ten new helpers — as long as no
        billable call escapes on an unpriced model, this stays green; the day
        one does, it goes red regardless of how the source is arranged.
        (`feedback_gates_grep_text_not_execution`)"""
        import asyncio

        import services.model_router as mr

        reached: list[str] = []

        async def _tripwire(*_a, **_k):
            reached.append("route_completion")
            raise AssertionError("billable call reached on an unpriced model")

        async def _tripwire_stream(*_a, **_k):
            reached.append("route_completion_stream")
            raise AssertionError("billable call reached on an unpriced model")
            yield  # pragma: no cover — makes this an async generator

        class _Auth:
            user_id = "gate-probe"
            workspace_id = None
            principal_id = "gate-probe"

            class client:  # noqa: N801 — never touched; the guard fires first
                pass

        unpriced = "anthropic/__gate_unpriced__"
        orig = (mr.route_completion, mr.route_completion_stream)
        mr.route_completion, mr.route_completion_stream = _tripwire, _tripwire_stream
        # Must be a LANE_MODELS key, or the unknown-model check stops it first
        # and we'd be asserting the wrong guard.
        lr.LANE_MODELS[unpriced] = {"label": "Gate probe", "vision": True}
        try:
            if not lr.unpriced_lane_model(unpriced):
                return False  # the probe model must actually be unpriced
            out = asyncio.run(lr.run_lane_turn(
                _Auth(), model=unpriced, history=[], user_message="probe"))
            if out.get("error") != "model_unpriced":
                return False

            async def _drain():
                events = []
                async for kind, payload in lr.run_lane_turn_stream(
                    _Auth(), model=unpriced, history=[], user_message="probe"):
                    events.append((kind, payload))
                return events

            streamed = asyncio.run(_drain())
            if not streamed or streamed[-1][1].get("error") != "model_unpriced":
                return False
        finally:
            lr.LANE_MODELS.pop(unpriced, None)
            mr.route_completion, mr.route_completion_stream = orig
        return not reached

    results.append(_check(
        "no billable call escapes on an unpriced model (both loops, EXECUTED)",
        _no_billable_call_on_an_unpriced_model(),
    ))

    # ── 7. §4 F2 — a dropped ledger row alerts (not a silent warning) ───────
    import services.telemetry as tel
    rec_src = inspect.getsource(tel.record_execution_event)
    results.append(_check(
        "dropped ledger row emits a distinct [LEDGER-DROP] ERROR with lost cost",
        "[LEDGER-DROP]" in rec_src and "logger.error" in rec_src and "lost_cost" in rec_src,
    ))
    results.append(_check(
        "F2 stays fail-open (still returns None; never re-raises)",
        "return None" in rec_src.split("except Exception as e:")[-1],
    ))

    passed = sum(results)
    total = len(results)
    print(f"\nADR-439 gate: {passed}/{total} PASS")
    return passed == total


if __name__ == "__main__":
    import sys
    sys.exit(0 if run() else 1)

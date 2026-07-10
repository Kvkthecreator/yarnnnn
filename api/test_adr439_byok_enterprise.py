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
    results.append(_check(
        "BYOK_PROVIDERS is the LANE_MODELS provider set",
        set(byok.BYOK_PROVIDERS) == {"anthropic", "openai", "gemini", "deepseek"},
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

    passed = sum(results)
    total = len(results)
    print(f"\nADR-439 gate: {passed}/{total} PASS")
    return passed == total


if __name__ == "__main__":
    import sys
    sys.exit(0 if run() else 1)

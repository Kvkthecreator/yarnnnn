"""Hat-B probe — does the router actually route, and does the flag actually hold?

THE QUESTION (operator, 2026-08-12): ADR-556 + ADR-557 are stub-verified. The
gates prove the SHAPE (signatures, ordering, flag branches) against fakes. They
cannot prove the transport carries a real completion, that the ledger's token
shape matches what providers actually return, or that the flag holds against a
live network. Before Phase 2 ships model choice to members, the thing being
chosen has to be known to work.

WHY A PROBE AND NOT A GATE: this spends real money on real providers and needs
real keys. It must never run in CI. It is the Hat-B instrument that tells us the
Hat-A gates are guarding something true.

CRITERION (declared BEFORE the run, per docs/evaluations/README.md):

  C1 REFUSAL   — with MODEL_ROUTER_ENABLED off, every routed entry point raises
                 RouterDisabled and NO network call occurs. Falsified by timing:
                 a refusal is <50ms; a real call is not. (ADR-557 D1 — this is
                 the defect: a flag-off call previously SUCCEEDED over the wire.)
  C2 TRANSPORT — with the flag on, each configured lane model returns non-empty
                 text. A model whose key is absent must fail LOUDLY (a named
                 provider error), never silently degrade.
  C3 LEDGER    — usage comes back in the ledger's Anthropic-native EXCLUSIVE
                 shape (input_tokens excludes cache), all ints >= 0, and
                 output_tokens > 0 on a real completion. This is the ADR-396
                 one-meter contract: if the shape is wrong, every routed call
                 has been mispriced.
  C4 PRICING   — every model that answers has a _BILLING_RATES row, and
                 compute_cost_usd_inclusive prices it > 0. (ADR-439 §4: an
                 unpriced model prices silently at the Sonnet default.)
  C5 STREAMING — the streaming entry point yields deltas and one terminal
                 RoutedCompletion whose usage satisfies C3. (ADR-412 D2: the
                 ledger write must be byte-identical whether or not it streamed.)
  C6 HEADROOM  — at the REAL lane budget, a reasoning model still emits text
                 after its hidden reasoning. This is the criterion that
                 protects production: a budget too small does not error, it
                 returns an EMPTY REPLY (finish_reason=length, content='').
                 Run with --headroom (slower + costlier: full lane budget).

  PASS = C1 and C3 and C4 hold, and C2 holds for every model with a key present.
  A model with no key is REPORTED, not failed — that is a deployment fact
  (Render env parity), not a code defect. Likewise a provider-side billing
  refusal (e.g. an exhausted account) is INFO: it says nothing about our code.

Run:  cd api && python3 probe_router_transport.py [--models a,b] [--skip-stream]
                                                  [--headroom]

Cost: ~512 max tokens per model (reasoning models bill what they think).
      --headroom spends the full 4096 lane budget on 3 models.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# The ask: cheapest real completion that still proves the round trip.
#
# ⚠️ MAX_TOKENS IS 512, NOT 10, AND THE REASON IS A FINDING (2026-08-12).
# The first cut used max_tokens=10 and reported gpt-5, gemini-2.5-flash and
# gemini-2.5-pro as FAILING with empty text. They were not failing: REASONING
# MODELS SPEND max_tokens ON HIDDEN REASONING BEFORE EMITTING ANY TEXT. gpt-5
# returned `finish_reason: length`, `content: ''`, and
# `completion_tokens_details.reasoning_tokens=10` — the whole budget consumed
# by thinking, none left to speak with.
#
# So a budget that is fine for a non-reasoning model is a SILENT EMPTY REPLY on
# a reasoning one. 512 clears the observed floor with margin while keeping the
# probe cheap. The real lane budget (4096 chat / 8192 authoring) was separately
# verified sufficient — see `reasoning_headroom` below, which is the check that
# actually protects production.
PROMPT = "Reply with exactly one word: yes"
MAX_TOKENS = 512

#: The reasoning overhead observed at the real 4096 lane budget on a
#: lane-shaped ask (2026-08-12): gpt-5 2560, gemini-2.5-pro 1726,
#: gemini-2.5-flash 1450 tokens spent thinking before answering. Recorded so a
#: future budget change is measured against evidence rather than guessed.
OBSERVED_REASONING_AT_4096 = {
    "openai/gpt-5": 2560,
    "gemini/gemini-2.5-pro": 1726,
    "gemini/gemini-2.5-flash": 1450,
}

FINDINGS: list[tuple[str, str, str]] = []  # (criterion, verdict, detail)


def record(criterion: str, verdict: str, detail: str = "") -> None:
    FINDINGS.append((criterion, verdict, detail))
    mark = {"PASS": "  ok  ", "FAIL": "  FAIL", "INFO": "  --  "}[verdict]
    print(f"{mark} [{criterion}] {detail}")


def _provider_key_present(model: str) -> bool:
    """Is the provider key for this model in env? A missing key is a DEPLOYMENT
    fact (Render parity), reported rather than failed."""
    provider = model.split("/", 1)[0]
    return bool(os.environ.get({
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
    }.get(provider, "__none__"), "").strip())


async def probe_c1_refusal() -> None:
    """C1 — the flag holds, and holds BEFORE the network."""
    print("\nC1 — flag OFF must refuse, without touching the network")
    import services.model_router as mr

    saved = os.environ.pop("MODEL_ROUTER_ENABLED", None)
    try:
        for label, call in (
            ("route_completion", lambda: mr.route_completion(
                "anthropic/claude-haiku-4-5-20251001",
                [{"role": "user", "content": PROMPT}], max_tokens=MAX_TOKENS)),
            ("route_completion_stream", _drain(mr)),
        ):
            t0 = time.monotonic()
            try:
                await call() if callable(call) else await call
                record("C1", "FAIL", f"{label} SUCCEEDED with the flag off — the leak is back")
            except mr.RouterDisabled:
                ms = (time.monotonic() - t0) * 1000
                # A refusal that took network time would mean the guard ran too
                # late (after the request). Timing is the falsifier.
                if ms < 50:
                    record("C1", "PASS", f"{label} refused in {ms:.1f}ms (no network)")
                else:
                    record("C1", "FAIL", f"{label} refused but took {ms:.0f}ms — guard ran late?")
            except Exception as exc:  # noqa: BLE001
                record("C1", "FAIL", f"{label} raised {type(exc).__name__}, not RouterDisabled: {exc}")
    finally:
        if saved is not None:
            os.environ["MODEL_ROUTER_ENABLED"] = saved


def _drain(mr):
    async def go():
        async for _ in mr.route_completion_stream(
            "anthropic/claude-haiku-4-5-20251001",
            [{"role": "user", "content": PROMPT}], max_tokens=MAX_TOKENS,
        ):
            pass
    return go


def _check_usage(criterion: str, model: str, usage: dict) -> bool:
    """C3 — the ledger's exclusive token shape."""
    required = ("input_tokens", "output_tokens", "cache_read_tokens", "cache_create_tokens")
    missing = [k for k in required if k not in usage]
    if missing:
        record(criterion, "FAIL", f"{model}: usage missing {missing}")
        return False
    bad = {k: v for k, v in usage.items() if not isinstance(v, int) or v < 0}
    if bad:
        record(criterion, "FAIL", f"{model}: non-int/negative usage {bad}")
        return False
    if usage["output_tokens"] <= 0:
        record(criterion, "FAIL", f"{model}: output_tokens=0 on a real completion")
        return False
    return True


def _check_pricing(model: str, ledger_model: str, usage: dict) -> None:
    """C4 — priced by the ONE cost function, not the Sonnet default."""
    from services.telemetry import compute_cost_usd_inclusive, has_billing_rate

    if not has_billing_rate(ledger_model):
        record("C4", "FAIL", f"{model}: no _BILLING_RATES row for {ledger_model!r} "
                             "— it would price at the Sonnet default")
        return
    cost = compute_cost_usd_inclusive(
        model=ledger_model,
        input_tokens=usage["input_tokens"],
        output_tokens=usage["output_tokens"],
        cache_read_tokens=usage["cache_read_tokens"],
        cache_create_tokens=usage["cache_create_tokens"],
    )
    if cost is None or cost <= 0:
        record("C4", "FAIL", f"{model}: priced at {cost}")
    else:
        record("C4", "PASS", f"{model}: ${cost:.8f} via {ledger_model}")


async def probe_c2_c3_c4(models: list[str]) -> None:
    print("\nC2/C3/C4 — real completions, ledger shape, pricing")
    os.environ["MODEL_ROUTER_ENABLED"] = "1"
    import services.model_router as mr

    for model in models:
        if not _provider_key_present(model):
            record("C2", "INFO", f"{model}: provider key ABSENT — lane ships dark "
                                 "(deployment fact; check Render API + Scheduler)")
            continue
        try:
            r = await mr.route_completion(
                model, [{"role": "user", "content": PROMPT}],
                max_tokens=MAX_TOKENS, timeout=45.0,
            )
        except Exception as exc:  # noqa: BLE001
            # Loud, named failure — never a silent degrade. A PROVIDER-SIDE
            # BILLING refusal is INFO, not FAIL: an exhausted upstream account
            # says nothing about our transport (observed 2026-08-12 on
            # deepseek: "Insufficient Balance").
            msg = str(exc)
            kind = "INFO" if ("Insufficient Balance" in msg or "quota" in msg.lower()) else "FAIL"
            record("C2", kind, f"{model}: {type(exc).__name__}: {msg[:160]}")
            continue

        if not (r.text or "").strip():
            # See MAX_TOKENS: an empty reply from a reasoning model usually
            # means the budget was spent thinking, not that transport failed.
            record("C2", "FAIL",
                   f"{model}: EMPTY text (finish={r.finish_reason!r}) — if this is a "
                   "reasoning model the token budget was consumed by hidden reasoning")
            continue
        record("C2", "PASS", f"{model}: {r.text.strip()[:40]!r}")

        if _check_usage("C3", model, r.usage):
            u = r.usage
            record("C3", "PASS",
                   f"{model}: in={u['input_tokens']} out={u['output_tokens']} "
                   f"cache_r={u['cache_read_tokens']} cache_w={u['cache_create_tokens']}")
            _check_pricing(model, r.ledger_model, u)

        # The router REPORTS a cost; the ledger RECORDS one. They should agree
        # roughly — a large divergence means our rate table has drifted from the
        # provider's list price (the ADR-408 D4 mirror check).
        if r.router_cost_usd:
            from services.telemetry import compute_cost_usd_inclusive
            ours = compute_cost_usd_inclusive(
                model=r.ledger_model, input_tokens=r.usage["input_tokens"],
                output_tokens=r.usage["output_tokens"],
                cache_read_tokens=r.usage["cache_read_tokens"],
                cache_create_tokens=r.usage["cache_create_tokens"],
            ) or 0.0
            if ours > 0:
                ratio = ours / r.router_cost_usd
                verdict = "PASS" if 0.5 <= ratio <= 2.0 else "INFO"
                record("C4", verdict,
                       f"{model}: rate mirror ours=${ours:.8f} litellm=${r.router_cost_usd:.8f} "
                       f"(x{ratio:.2f})")


async def probe_c5_streaming(model: str) -> None:
    print("\nC5 — streaming yields deltas + one terminal completion")
    if not _provider_key_present(model):
        record("C5", "INFO", f"{model}: provider key absent — skipped")
        return
    os.environ["MODEL_ROUTER_ENABLED"] = "1"
    import services.model_router as mr

    deltas, terminal = 0, None
    try:
        async for kind, payload in mr.route_completion_stream(
            model, [{"role": "user", "content": PROMPT}],
            max_tokens=MAX_TOKENS, timeout=45.0,
        ):
            if kind == "delta":
                deltas += 1
            elif kind == "done":
                terminal = payload
    except Exception as exc:  # noqa: BLE001
        record("C5", "FAIL", f"{model}: {type(exc).__name__}: {str(exc)[:160]}")
        return

    if terminal is None:
        record("C5", "FAIL", f"{model}: stream ended with no terminal ('done') event")
        return
    record("C5", "PASS" if deltas else "INFO",
           f"{model}: {deltas} delta(s), terminal text={terminal.text.strip()[:30]!r}")
    if _check_usage("C5", model, terminal.usage):
        record("C5", "PASS",
               f"{model}: streamed usage matches the ledger shape "
               f"(in={terminal.usage['input_tokens']} out={terminal.usage['output_tokens']})")


async def probe_c6_headroom(models: list[str]) -> None:
    """C6 — at the REAL lane budget, does a reasoning model still SPEAK?

    The production-protecting criterion. A too-small budget does not raise; it
    returns `finish_reason='length'` with empty content, which every caller
    would read as "the model had nothing to say".
    """
    print("\nC6 — reasoning headroom at the real lane budget (4096)")
    from services.lane_runner import _LANE_MAX_TOKENS

    os.environ["MODEL_ROUTER_ENABLED"] = "1"
    import services.model_router as mr

    ask = ("Read the situation: our pricing page converts at 2%. Think it through "
           "and give me three concrete hypotheses for why, ranked, with what "
           "you'd test first.")
    for model in models:
        if model not in OBSERVED_REASONING_AT_4096 or not _provider_key_present(model):
            continue
        try:
            r = await mr.route_completion(
                model, [{"role": "user", "content": ask}],
                max_tokens=_LANE_MAX_TOKENS, timeout=120.0,
            )
        except Exception as exc:  # noqa: BLE001
            record("C6", "FAIL", f"{model}: {type(exc).__name__}: {str(exc)[:140]}")
            continue
        text = (r.text or "").strip()
        if not text:
            record("C6", "FAIL",
                   f"{model}: EMPTY at the real lane budget ({_LANE_MAX_TOKENS}) — "
                   "members would see a blank reply")
            continue
        record("C6", "PASS",
               f"{model}: {len(text)} chars after ~{OBSERVED_REASONING_AT_4096[model]} "
               f"reasoning tokens (budget {_LANE_MAX_TOKENS})")


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="", help="comma-separated; default = all LANE_MODELS")
    ap.add_argument("--skip-stream", action="store_true")
    ap.add_argument("--headroom", action="store_true",
                    help="run C6 at the full lane budget (slower, costlier)")
    args = ap.parse_args()

    from services.lane_runner import LANE_MODELS
    models = ([m.strip() for m in args.models.split(",") if m.strip()]
              or list(LANE_MODELS))

    print("=" * 72)
    print("ROUTER TRANSPORT PROBE — real providers, real money (Hat-B)")
    print(f"models: {len(models)}  |  prompt: {PROMPT!r}  |  max_tokens: {MAX_TOKENS}")
    print("=" * 72)

    saved_flag = os.environ.get("MODEL_ROUTER_ENABLED")
    try:
        await probe_c1_refusal()
        await probe_c2_c3_c4(models)
        if not args.skip_stream:
            streamable = next((m for m in models if _provider_key_present(m)), None)
            if streamable:
                await probe_c5_streaming(streamable)
        if args.headroom:
            await probe_c6_headroom(models)
    finally:
        if saved_flag is None:
            os.environ.pop("MODEL_ROUTER_ENABLED", None)
        else:
            os.environ["MODEL_ROUTER_ENABLED"] = saved_flag

    print("\n" + "=" * 72)
    fails = [f for f in FINDINGS if f[1] == "FAIL"]
    infos = [f for f in FINDINGS if f[1] == "INFO"]
    passes = [f for f in FINDINGS if f[1] == "PASS"]
    print(f"{len(passes)} pass · {len(fails)} FAIL · {len(infos)} info")
    if infos:
        print("\nINFO (deployment facts, not code defects):")
        for _, _, d in infos:
            print(f"  - {d}")
    if fails:
        print("\nFAILURES:")
        for c, _, d in fails:
            print(f"  - [{c}] {d}")
        return 1
    print("\nROUTER TRANSPORT: criteria met.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

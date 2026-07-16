"""ADR-408 D4 — seat-level model router spike: regression gate.

Locks the spike's claims:

1. **Flag discipline** — MODEL_ROUTER_ENABLED defaults OFF and is read at
   call time; flag off → the legacy Anthropic path runs and the router is
   never touched.
2. **Cost mirror (spike criterion a)** — the router REPORTS, the ledger
   RECORDS: route_completion returns ledger-shaped tokens (Anthropic-native
   cache-EXCLUSIVE input), the call site records them via
   record_execution_event, cost is priced by compute_cost_usd_inclusive
   (the one cost function, ADR-291 D2), and the router's own cost figure is
   never written anywhere (ADR-396 double-charge invariant — one ledger).
3. **Attribution (spike criterion b)** — the routed helper call attributes
   as the member's embodiment (ADR-408 D2): principal_id lands on the
   execution_events row; the model column carries the normalized
   ledger_model.
4. **Altitude boundary** — the steward (Altitude 1) never routes:
   freddie_agent.py and model_routing.py are router-free; Anthropic remains
   the steward's model.
5. **The feed.py NameError fix** — _summarize_previous_session threads
   user_id/principal_id as parameters (the prior shape referenced auth with
   no auth in scope; every inline summary silently failed).

Pure offline: no LLM, no DB, no network (litellm is never imported —
route_completion's lazy import is part of what makes that possible).
"""
from __future__ import annotations

import ast
import asyncio
import os
import sys
from pathlib import Path

_API_ROOT = Path(__file__).resolve().parent
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

from services.model_router import (
    RoutedCompletion,
    _normalize_usage,
    ledger_model_name,
    model_router_enabled,
)
from services.telemetry import compute_cost_usd_inclusive, has_billing_rate

_FLAG = "MODEL_ROUTER_ENABLED"


def _clear_flag():
    os.environ.pop(_FLAG, None)


# ---------------------------------------------------------------------------
# 1. Flag discipline
# ---------------------------------------------------------------------------

def test_flag_defaults_off():
    _clear_flag()
    assert model_router_enabled() is False


def test_flag_truthy_forms_and_call_time_read():
    _clear_flag()
    try:
        for val in ("1", "true", "TRUE", "yes", "on"):
            os.environ[_FLAG] = val
            assert model_router_enabled() is True, val
        for val in ("", "0", "false", "off", "no"):
            os.environ[_FLAG] = val
            assert model_router_enabled() is False, val
    finally:
        _clear_flag()
    assert model_router_enabled() is False


def test_litellm_declared_in_requirements():
    req = (_API_ROOT / "requirements.txt").read_text()
    assert "litellm" in req, "litellm missing from api/requirements.txt"


# ---------------------------------------------------------------------------
# 2. Usage normalization + cost mirror (spike criterion a)
# ---------------------------------------------------------------------------

def test_ledger_model_strips_provider_prefix():
    assert ledger_model_name("anthropic/claude-haiku-4-5-20251001") == \
        "claude-haiku-4-5-20251001"
    assert ledger_model_name("openai/gpt-4o-mini") == "gpt-4o-mini"
    assert ledger_model_name("claude-sonnet-4-6") == "claude-sonnet-4-6"


def test_normalize_usage_subtracts_cache_from_inclusive_prompt():
    """LiteLLM reports OpenAI-convention prompt_tokens (cache-INCLUSIVE for
    Anthropic); the ledger expects fresh-input EXCLUSIVE of cache."""
    usage = {
        "prompt_tokens": 1000,          # 700 fresh + 200 read + 100 create
        "completion_tokens": 50,
        "cache_read_input_tokens": 200,
        "cache_creation_input_tokens": 100,
    }
    norm = _normalize_usage(usage)
    assert norm == {
        "input_tokens": 700,
        "output_tokens": 50,
        "cache_read_tokens": 200,
        "cache_create_tokens": 100,
    }


def test_normalize_usage_reads_openai_details_shape_and_clamps():
    class Details:
        cached_tokens = 300

    class Usage:
        prompt_tokens = 250   # smaller than cached — provider quirk; clamp
        completion_tokens = 10
        prompt_tokens_details = Details()

    norm = _normalize_usage(Usage())
    assert norm["cache_read_tokens"] == 300
    assert norm["input_tokens"] == 0  # clamped, never negative
    assert norm["output_tokens"] == 10
    # Missing usage entirely → zeros, not a crash.
    assert _normalize_usage(None) == {
        "input_tokens": 0, "output_tokens": 0,
        "cache_read_tokens": 0, "cache_create_tokens": 0,
    }


def test_ledger_prices_routed_tokens_with_the_one_cost_function():
    """The mirror: router tokens → compute_cost_usd_inclusive, hand-checked
    against the haiku rate row (TRUE provider list — $1/$5 per MTok; the
    legacy 2x markup retired by operator ruling 2026-07-06, cache read 10% /
    create 125% unchanged)."""
    usage = _normalize_usage({
        "prompt_tokens": 1_000_000, "completion_tokens": 100_000,
        "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0,
    })
    cost = compute_cost_usd_inclusive(
        "claude-haiku-4-5-20251001",
        usage["input_tokens"], usage["output_tokens"],
        usage["cache_read_tokens"], usage["cache_create_tokens"],
    )
    assert cost == round(1.00 + 0.1 * 5.00, 6)  # $1.00 input + $0.50 output


def test_routed_models_have_rate_rows():
    """A model the router may route must price explicitly, not at the Sonnet
    default. The spike blesses the Anthropic set + gpt-4o-mini (the
    cross-provider probe model)."""
    assert has_billing_rate("claude-haiku-4-5-20251001")
    assert has_billing_rate("gpt-4o-mini")
    assert not has_billing_rate("some-unpriced-model")


def test_router_never_writes_the_ledger():
    """ADR-396 one-ledger: the router reports, the CALLER records. The
    router module must not touch record_execution_event / execution_events,
    and router_cost_usd must never flow into the record call."""
    src = (_API_ROOT / "services" / "model_router.py").read_text()
    assert "import record_execution_event" not in src
    assert "record_execution_event(" not in src
    assert 'table("execution_events")' not in src
    call_site = (_API_ROOT / "services" / "session_continuity.py").read_text()
    assert "router_cost" not in call_site, (
        "the call site must not record the router's cost figure — "
        "cost is computed from tokens by the one cost function"
    )


# ---------------------------------------------------------------------------
# 3. The routed call site: flag on → router; attribution lands (criterion b)
# ---------------------------------------------------------------------------

_MESSAGES = [
    {"role": "user", "content": "set up the weekly report"},
    {"role": "assistant", "content": "done — every Monday 9am"},
    {"role": "user", "content": "add revenue numbers to it"},
    {"role": "assistant", "content": "added"},
    {"role": "user", "content": "thanks, continue tomorrow"},
]


def _run_summary_with_router(monkey_routed: RoutedCompletion):
    """Run generate_session_summary flag-on with route_completion mocked;
    return (summary, recorded_kwargs)."""
    import services.model_router as mr
    import services.telemetry as tele
    import services.supabase as sb
    import services.session_continuity as sc

    recorded: dict = {}

    async def fake_route(model, messages, **kwargs):
        recorded["routed_model_arg"] = model
        return monkey_routed

    def fake_record(client, **kwargs):
        recorded["event"] = kwargs
        return "evt-1"

    orig_route = mr.route_completion
    orig_record = tele.record_execution_event
    orig_client = sb.get_service_client
    os.environ[_FLAG] = "true"
    try:
        mr.route_completion = fake_route
        tele.record_execution_event = fake_record
        sb.get_service_client = lambda: object()
        summary = asyncio.run(sc.generate_session_summary(
            _MESSAGES, "2026-07-06",
            user_id="user-123", principal_id="member-456",
        ))
    finally:
        mr.route_completion = orig_route
        tele.record_execution_event = orig_record
        sb.get_service_client = orig_client
        _clear_flag()
    return summary, recorded


def test_routed_summary_records_tokens_model_and_principal():
    routed = RoutedCompletion(
        text="Settled the weekly report format; revenue numbers added.",
        model="anthropic/claude-haiku-4-5-20251001",
        ledger_model="claude-haiku-4-5-20251001",
        usage={
            "input_tokens": 700, "output_tokens": 42,
            "cache_read_tokens": 200, "cache_create_tokens": 100,
        },
        router_cost_usd=0.00123,  # report-only; must NOT reach the ledger
    )
    summary, recorded = _run_summary_with_router(routed)

    assert summary == "[2026-07-06] Settled the weekly report format; revenue numbers added."
    # The provider-prefixed model went to the router...
    assert recorded["routed_model_arg"].startswith("anthropic/")
    ev = recorded["event"]
    # ...and the ledger row carries the normalized model + the member's
    # attribution (criterion b: the helper is the member's embodiment).
    assert ev["model"] == "claude-haiku-4-5-20251001"
    assert ev["principal_id"] == "member-456"
    assert ev["user_id"] == "user-123"
    assert ev["slug"] == "session-summary"
    # Tokens mirrored verbatim (criterion a); no cost field smuggled in.
    assert ev["input_tokens"] == 700
    assert ev["output_tokens"] == 42
    assert ev["cache_read_tokens"] == 200
    assert ev["cache_create_tokens"] == 100
    assert "cost" not in " ".join(ev.keys()), f"cost field leaked: {ev.keys()}"


def test_flag_off_takes_legacy_anthropic_path():
    """Flag off → the Anthropic SDK path, router untouched."""
    import services.model_router as mr
    import services.telemetry as tele
    import services.supabase as sb
    import services.session_continuity as sc
    import anthropic

    recorded: dict = {}

    class FakeUsage:
        input_tokens = 500
        output_tokens = 30
        cache_read_input_tokens = 0
        cache_creation_input_tokens = 0

    class FakeContent:
        text = "Legacy path summary."

    class FakeResponse:
        content = [FakeContent()]
        usage = FakeUsage()

    class FakeMessages:
        def create(self, **kwargs):
            recorded["anthropic_model"] = kwargs.get("model")
            return FakeResponse()

    class FakeAnthropic:
        def __init__(self, *a, **k):
            self.messages = FakeMessages()

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    async def must_not_run(*a, **k):
        raise AssertionError("route_completion called with flag OFF")

    def fake_record(client, **kwargs):
        recorded["event"] = kwargs
        return "evt-2"

    orig_route = mr.route_completion
    orig_record = tele.record_execution_event
    orig_client = sb.get_service_client
    orig_anthropic = anthropic.Anthropic
    _clear_flag()
    try:
        mr.route_completion = must_not_run
        tele.record_execution_event = fake_record
        sb.get_service_client = lambda: object()
        anthropic.Anthropic = FakeAnthropic
        summary = asyncio.run(sc.generate_session_summary(
            _MESSAGES, "2026-07-06", user_id="user-123",
        ))
    finally:
        mr.route_completion = orig_route
        tele.record_execution_event = orig_record
        sb.get_service_client = orig_client
        anthropic.Anthropic = orig_anthropic

    assert summary == "[2026-07-06] Legacy path summary."
    ev = recorded["event"]
    assert ev["model"] == sc.SUMMARY_MODEL
    assert ev["input_tokens"] == 500 and ev["output_tokens"] == 30
    # principal_id kwarg exists on the legacy path too (None when unknown).
    assert "principal_id" in ev


# ---------------------------------------------------------------------------
# 4. Altitude boundary — the steward never routes
# ---------------------------------------------------------------------------

def test_steward_path_is_router_free():
    """Altitude 1 (Freddie) stays on services/model_selection.py (ADR-402,
    Anthropic-only). The router is Altitude-2 machinery."""
    for rel in ("agents/freddie_agent.py", "services/model_selection.py",
                "services/anthropic.py", "agents/occupant_contract.py"):
        src = (_API_ROOT / rel).read_text()
        # Assert on IMPORTS, not on a substring of the file.
        #
        # This used to grep the raw source with a `.replace("model_routing", "")`
        # hack to dodge a false match on the old module name. ADR-463 D1.a
        # renamed that module to `model_selection`, so the collision is gone —
        # but the deeper flaw remained: these modules DISCUSS the router in prose
        # (model_selection.py's header now explains at length WHY Freddie does
        # not route), so a text guard fires on the documentation of the very rule
        # it enforces. Stripping comments line-by-line does not help either —
        # module docstrings are multi-line.
        #
        # The rule was always about the DEPENDENCY, so read the dependency: parse
        # the module and look at what it actually imports. Prose is free to
        # explain the boundary; code may not cross it.
        tree = ast.parse(src)
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        offenders = {m for m in imported if "model_router" in m}
        assert not offenders, (
            f"{rel} imports the seat-level router {offenders} — the steward never "
            "routes (ADR-408 D4)"
        )


def test_steward_routing_ignores_the_router_flag():
    from services.model_selection import resolve_route
    _clear_flag()
    before = resolve_route("addressed", False)
    try:
        os.environ[_FLAG] = "true"
        assert resolve_route("addressed", False) == before
    finally:
        _clear_flag()
    # The test's point is the two asserts above: the flag does not move the
    # steward's selection. This line asserted `startswith("claude-")` — a
    # vendor assumption riding along on a flag test, and the second gate in this
    # arc to encode the lock ADR-463 D1 removes. What belongs here is the
    # steward's real invariant: whatever it selects, it is served DIRECTLY by
    # Anthropic (ADR-463 D3 — prompt caching the transport cannot carry), so the
    # provider half of the name is the thing to pin, not the model half.
    assert before.model.startswith("anthropic/"), (
        f"the steward's model is Anthropic-direct by ADR-463 D3, got {before.model!r}"
    )


# ---------------------------------------------------------------------------
# 5. The feed.py NameError fix
# ---------------------------------------------------------------------------

def test_summarize_previous_session_threads_identity():
    src = (_API_ROOT / "routes" / "feed.py").read_text()
    # The background task threads plain values...
    assert "user_id=auth.user_id" in src
    assert 'principal_id=getattr(auth, "principal_id", None)' in src
    # ...and the helper body no longer references the out-of-scope auth.
    start = src.index("async def _summarize_previous_session")
    end = src.index("\nasync def ", start + 10)
    body = src[start:end]
    assert "auth." not in body, (
        "_summarize_previous_session must not reference auth — it has no "
        "auth in scope (the pre-spike NameError bug)"
    )
    assert "principal_id=principal_id" in body


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  ✓ {name}")
            except AssertionError as exc:
                print(f"  ✗ {name}: {exc}")
                fails += 1
    sys.exit(1 if fails else 0)

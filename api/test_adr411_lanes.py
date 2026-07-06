"""ADR-411 — chat lanes + the lane tool surface: regression gate.

Locks the implementation decisions:

1. **D5 pricing rule** — every LANE_MODELS entry prices explicitly (a
   _BILLING_RATES row for its ledger_model); no silent default pricing.
2. **D3 tool surface** — exactly the five file verbs, OpenAI format,
   derived from the registry's own definitions (no parallel schemas).
3. **D4 attribution** — `member:{user_id} via {model}` is a valid
   ADR-209 author and classifies as operator (the member's embodiment
   under the member's grant); the lane auth clone stamps it while
   preserving the member's principal_id.
4. **D2 turn loop** — bounded; tool rounds execute through
   execute_primitive under the lane auth; off-surface tools are refused
   without execution; every round records on the one ledger with the
   member as principal (ADR-396).
5. **Altitude boundary** — the steward never imports the lane machinery;
   lanes are registered on the API but nowhere near the wake stack.

Pure offline: no LLM, no DB, no network.
"""
from __future__ import annotations

import asyncio
import os
import sys
import types
from pathlib import Path

_API_ROOT = Path(__file__).resolve().parent
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

import services.lane_runner as lr
from services.authored_substrate import is_valid_author
from services.lane_runner import (
    LANE_MODELS,
    LANE_TOOL_NAMES,
    lane_caller_identity,
    lane_tools_openai,
)
from services.model_router import RoutedCompletion, ledger_model_name
from services.primitives.workspace import _caller_class
from services.telemetry import has_billing_rate

_FLAG = "MODEL_ROUTER_ENABLED"


# ---------------------------------------------------------------------------
# 1. D5 — pricing rule
# ---------------------------------------------------------------------------

def test_every_lane_model_has_a_rate_row():
    for model in LANE_MODELS:
        lm = ledger_model_name(model)
        assert has_billing_rate(lm), (
            f"LANE_MODELS entry {model!r} has no _BILLING_RATES row for "
            f"{lm!r} — a lane model enters the registry only WITH its rate "
            f"row (ADR-411 D5)"
        )


def test_lane_models_are_provider_prefixed():
    for model in LANE_MODELS:
        assert "/" in model, f"{model!r} must be provider/model (LiteLLM form)"


# ---------------------------------------------------------------------------
# 2. D3 — tool surface derived from the registry
# ---------------------------------------------------------------------------

def test_lane_tools_are_exactly_the_five_file_verbs():
    tools = lane_tools_openai()
    names = [t["function"]["name"] for t in tools]
    assert names == list(LANE_TOOL_NAMES)
    assert set(names) == {"ReadFile", "WriteFile", "EditFile", "SearchFiles", "ListFiles"}


def test_lane_tools_reuse_registry_schemas():
    from services.primitives.workspace import READ_FILE_TOOL, WRITE_FILE_TOOL
    by_name = {t["function"]["name"]: t["function"] for t in lane_tools_openai()}
    assert by_name["ReadFile"]["parameters"] == READ_FILE_TOOL["input_schema"]
    assert by_name["WriteFile"]["parameters"] == WRITE_FILE_TOOL["input_schema"]
    for fn in by_name.values():
        assert fn["description"], "tool descriptions must carry over"


# ---------------------------------------------------------------------------
# 3. D4 — attribution
# ---------------------------------------------------------------------------

def test_member_embodiment_author_is_valid_and_operator_class():
    author = lane_caller_identity("user-1", "openai/gpt-4o-mini")
    assert author == "member:user-1 via openai/gpt-4o-mini"
    assert is_valid_author(author)
    auth = types.SimpleNamespace(caller_identity=author)
    assert _caller_class(auth) == "operator"


def test_lane_auth_preserves_principal_and_stamps_identity():
    auth = types.SimpleNamespace(
        client=object(), user_id="user-1", email="m@x.com",
        caller_identity="operator", principal_id="user-1", workspace_id="ws-1",
    )
    clone = lr._lane_auth(auth, "openai/gpt-4o-mini")
    assert clone.caller_identity == "member:user-1 via openai/gpt-4o-mini"
    assert clone.principal_id == "user-1"      # the grant key is UNCHANGED
    assert clone.workspace_id == "ws-1"
    assert auth.caller_identity == "operator"  # original untouched


# ---------------------------------------------------------------------------
# 4. D2 — the turn loop
# ---------------------------------------------------------------------------

def _routed(text="", tool_calls=None, model="openai/gpt-4o-mini"):
    return RoutedCompletion(
        text=text,
        model=model,
        ledger_model=ledger_model_name(model),
        usage={"input_tokens": 100, "output_tokens": 20,
               "cache_read_tokens": 0, "cache_create_tokens": 0},
        tool_calls=tool_calls or [],
        finish_reason="tool_calls" if tool_calls else "stop",
        raw_assistant_message={"role": "assistant", "content": text or None,
                               "tool_calls": tool_calls or []} if tool_calls else None,
    )


def _run_turn(routed_sequence, tool_result=None):
    """Run run_lane_turn with router + primitives + ledger mocked."""
    import services.model_router as mr
    import services.primitives.registry as reg
    import services.telemetry as tele
    import services.supabase as sb

    calls = {"routed": 0, "tools": [], "events": [], "tool_auth": []}

    async def fake_route(model, messages, **kwargs):
        i = min(calls["routed"], len(routed_sequence) - 1)
        calls["routed"] += 1
        return routed_sequence[i]

    async def fake_execute(auth, name, input):
        calls["tools"].append(name)
        calls["tool_auth"].append(getattr(auth, "caller_identity", ""))
        return tool_result or {"success": True}

    def fake_record(client, **kwargs):
        calls["events"].append(kwargs)
        return "evt"

    orig = (mr.route_completion, reg.execute_primitive,
            tele.record_execution_event, sb.get_service_client,
            lr.build_lane_conventions)
    os.environ[_FLAG] = "true"
    try:
        mr.route_completion = fake_route
        reg.execute_primitive = fake_execute
        tele.record_execution_event = fake_record
        sb.get_service_client = lambda: object()
        lr.build_lane_conventions = lambda *a, **k: "conventions"
        auth = types.SimpleNamespace(
            client=object(), user_id="user-1", email=None,
            caller_identity="operator", principal_id="user-1",
            workspace_id="ws-1",
        )
        result = asyncio.run(lr.run_lane_turn(
            auth, model="openai/gpt-4o-mini",
            history=[], user_message="do the thing",
        ))
    finally:
        (mr.route_completion, reg.execute_primitive,
         tele.record_execution_event, sb.get_service_client,
         lr.build_lane_conventions) = orig
        os.environ.pop(_FLAG, None)
    return result, calls


def test_turn_with_tool_round_executes_under_member_identity_and_meters():
    tc = {"id": "call-1", "name": "WriteFile", "arguments": {"path": "operation/x.md"}}
    result, calls = _run_turn([
        _routed(tool_calls=[tc]),
        _routed(text="done — wrote operation/x.md"),
    ])
    assert result["success"] and result["text"].startswith("done")
    assert result["rounds"] == 2
    assert calls["tools"] == ["WriteFile"]
    # The tool ran under the member-embodiment identity (D4).
    assert calls["tool_auth"] == ["member:user-1 via openai/gpt-4o-mini"]
    # Every round metered on the one ledger, member as principal (D5).
    assert len(calls["events"]) == 2
    for ev in calls["events"]:
        assert ev["slug"] == "lane"
        assert ev["principal_id"] == "user-1"
        assert ev["workspace_id"] == "ws-1"
        assert ev["model"] == "gpt-4o-mini"
        assert "cost" not in " ".join(ev.keys())


def test_off_surface_tool_is_refused_without_execution():
    tc = {"id": "call-1", "name": "Schedule", "arguments": {}}
    result, calls = _run_turn([
        _routed(tool_calls=[tc]),
        _routed(text="understood"),
    ])
    assert result["success"]
    assert calls["tools"] == []  # execute_primitive never ran
    assert result["tools_called"] == ["Schedule"]  # but the attempt is visible


def test_turn_requires_known_model_and_live_router():
    auth = types.SimpleNamespace(client=object(), user_id="u", caller_identity="operator")
    os.environ.pop(_FLAG, None)
    r = asyncio.run(lr.run_lane_turn(auth, model="openai/gpt-4o-mini",
                                     history=[], user_message="hi"))
    assert r == {"success": False, "error": "router_disabled",
                 "message": "MODEL_ROUTER_ENABLED is off — lanes need the router"}
    r2 = asyncio.run(lr.run_lane_turn(auth, model="not/a-model",
                                      history=[], user_message="hi"))
    assert r2["error"] == "unknown_model"


def test_round_budget_is_bounded():
    tc = {"id": "c", "name": "ReadFile", "arguments": {"path": "x"}}
    looping = _routed(tool_calls=[tc])
    result, calls = _run_turn([looping])  # same tool-call response forever
    assert result["success"]
    assert result["rounds"] == lr._LANE_MAX_ROUNDS
    assert "exhausted" in result["text"]


# ---------------------------------------------------------------------------
# 5. Altitude boundary + registration
# ---------------------------------------------------------------------------

def test_steward_never_imports_lane_machinery():
    for rel in ("agents/freddie_agent.py", "services/wake.py",
                "services/wake_drainer.py", "services/wake_evaluation.py"):
        src = (_API_ROOT / rel).read_text()
        assert "lane_runner" not in src, f"{rel} touches the lane machinery"


def test_lanes_router_registered():
    src = (_API_ROOT / "main.py").read_text()
    assert "lanes" in src
    assert 'app.include_router(lanes.router, prefix="/api"' in src


def test_conventions_projection_carries_the_contract():
    class _Res:
        data = [{"content": "# MANDATE\nShip the weekly memo."}]

    class _Q:
        def select(self, *a): return self
        def eq(self, *a): return self
        def limit(self, *a): return self
        def execute(self): return _Res()

    class _Client:
        def table(self, name): return _Q()

    text = lr.build_lane_conventions(
        _Client(), "user-1", model="openai/gpt-4o-mini", member_label="seul",
    )
    assert "shared" in text.lower()
    assert "GPT-4o mini" in text
    assert "seul" in text
    assert "Ship the weekly memo." in text          # mandate head injected
    assert "transcript is not shared memory" in text  # the D6 contract line


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
    print(f"\n{'='*60}\n{'PASS' if not fails else 'FAIL'}")
    sys.exit(1 if fails else 0)

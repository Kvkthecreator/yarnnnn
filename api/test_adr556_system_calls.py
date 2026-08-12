"""ADR-556 — the systematic/user-facing model boundary. The ratchet.

Run: python3 test_adr554_system_calls.py   (from api/)

What this defends, in one line: **a model id that machinery runs on has ONE
declared home, and it is never on a member's picker.**

The three failures this file exists because of — all of which shipped GREEN
past import checks, type checks, and every existing gate:

  1. `wake_evaluation.tier_2_decision` called `chat_completion` with a
     `user_id`/`caller` metering API that never existed on ANY wrapper, omitted
     the required `system` arg, and unpacked 2 values from a `-> str`. Born
     broken at 37426c5. Every call raised TypeError into a bare `except` and
     failed open to `escalate` — the cheap tier never ran once.
  2. `repurpose` read `response.text` off a `-> str`. A REGISTERED primitive.
  3. `routes/images.py` let a client name any engine into `route_completion`
     with no LANE_MODELS check and no billing gate.

(1) and (2) are the same shape: a call whose signature nobody executed. So this
gate EXECUTES call sites rather than grepping them — the ADR-548 lesson
(a gate that tests the helper is blind to its callers) applied.
"""

from __future__ import annotations

import ast
import asyncio
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

FAILS: list[str] = []
N = 0


def check(label: str, cond: bool, detail: str = "") -> None:
    global N
    N += 1
    if cond:
        print(f"  ok   {label}")
    else:
        FAILS.append(label)
        print(f"  FAIL {label}" + (f"\n         {detail}" if detail else ""))


print("1. the registry's own contract")

from services.model_selection import strip_provider
from services.system_calls import (
    SYSTEM_CALLS,
    TIER_CHEAP,
    TIER_STANDARD,
    resolve_system_call,
    system_call_model,
)
from services.telemetry import has_billing_rate

for call_type, call in SYSTEM_CALLS.items():
    # ADR-463 D1 — a dial whose every position is the same vendor is not a
    # dial. Every row names `provider/model`, so the table CAN spell a foreign
    # engine even where it does not yet call one.
    check(f"{call_type}: provider-prefixed", "/" in call.model, call.model)
    # ADR-439 §4 — an unpriced model prices silently at the Sonnet default,
    # which is a cost LIE, not a rounding error.
    check(
        f"{call_type}: priced",
        has_billing_rate(strip_provider(call.model)),
        f"no _BILLING_RATES row for {strip_provider(call.model)}",
    )
    check(f"{call_type}: declared tier", call.tier in (TIER_CHEAP, TIER_STANDARD))
    # The reason is the POINT of keying on call type rather than tier: it is
    # the only home the "why this engine" judgment has.
    check(f"{call_type}: carries a reason", len(call.reason.strip()) > 20)

def _try_unknown() -> bool:
    try:
        resolve_system_call("__nope__")
        return False
    except KeyError:
        return True


check(
    "unknown call type raises (a caller bug is never a silent default)",
    _try_unknown(),
)


print("\n2. the boundary — systematic is NOT on the member's picker")

from services.agents_registry import KERNEL_AGENTS, KERNEL_POSTURES
from services.lane_runner import LANE_MODELS

# The whole ADR in one assertion. LANE_MODELS is what a MEMBER may pin;
# SYSTEM_CALLS is machinery. They may share an engine (both run Sonnet), but
# the CALL TYPES must never leak onto the picker as choosable rows.
check(
    "SYSTEM_CALLS keys are not LANE_MODELS keys",
    not (set(SYSTEM_CALLS) & set(LANE_MODELS)),
    f"leaked: {sorted(set(SYSTEM_CALLS) & set(LANE_MODELS))}",
)
# Freddie has its OWN table (ADR-402, trigger-shape key + round budgets) and is
# deliberately NOT folded in: one table per routing key.
import services.model_selection as _ms

check(
    "the steward's table stays separate (ADR-402/463 D3)",
    hasattr(_ms, "DEFAULT_ROUTES") and "wake_triage" not in _ms.DEFAULT_ROUTES,
)

print("\n3. no bare model literals left in migrated machinery")

MIGRATED = [
    "services/wake_evaluation.py",
    "services/harvest.py",
    "services/context_inference.py",
    "services/recurrence_prompt_inference.py",
    "services/primitives/web_search.py",
    "services/primitives/repurpose.py",
    "services/primitives/dispatch_specialist.py",
    "services/memory.py",
    "services/session_continuity.py",
]

# STRING LITERALS ONLY, via ast — never a text grep. A regex over source
# matches its own explanatory comment (the recorded
# `feedback_gate_assertion_matches_its_own_comment` failure), and every file
# below NAMES the models it no longer hardcodes, in prose.
for rel in MIGRATED:
    src = pathlib.Path(rel).read_text()
    lits = [
        n.value
        for n in ast.walk(ast.parse(src))
        if isinstance(n, ast.Constant) and isinstance(n.value, str)
    ]
    offenders = [
        s for s in lits if s.startswith(("claude-", "gpt-", "gemini-", "deepseek-"))
    ]
    check(f"{rel}: no bare model-id literal", not offenders, f"found {offenders}")

# The env-var collision that made one dial move two features.
for rel in ("services/memory.py", "services/session_continuity.py"):
    src = pathlib.Path(rel).read_text()
    check(
        f"{rel}: MEMORY_EXTRACTION_MODEL retired",
        "MEMORY_EXTRACTION_MODEL" not in src,
    )

# ...and the two call types it bound together now move INDEPENDENTLY.
# ADR-559: was `claude-opus-4-6`, deleted as an unroutable phantom rate row.
# The id here only has to DIFFER from session_summary's to prove the dials
# are independent — it is never called.
os.environ["YARNNN_SYSCALL_FACT_EXTRACTION"] = "anthropic/claude-opus-5"
try:
    check(
        "fact_extraction and session_summary are independent dials",
        system_call_model("fact_extraction") == "claude-opus-5"
        and system_call_model("session_summary") == "claude-haiku-4-5",
    )
finally:
    del os.environ["YARNNN_SYSCALL_FACT_EXTRACTION"]

print("\n4. the wrappers are called with signatures that EXIST")

# THE core defense. Failures (1) and (2) were both "a call nobody executed".
# For every migrated module, every call to an `services.anthropic` wrapper is
# checked against that wrapper's REAL signature: no unknown kwargs, no missing
# required args. This is what a grep-shaped gate cannot see.
anthro = ast.parse(pathlib.Path("services/anthropic.py").read_text())
SIGS: dict[str, tuple[list[str], set[str], str]] = {}
for node in anthro.body:
    if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)) and node.name.startswith(
        "chat_completion"
    ):
        params = [a.arg for a in node.args.args]
        ndef = len(node.args.defaults)
        required = set(params[: len(params) - ndef])
        SIGS[node.name] = (params, required, ast.unparse(node.returns) if node.returns else "")

for rel in MIGRATED:
    tree = ast.parse(pathlib.Path(rel).read_text())
    for call in [n for n in ast.walk(tree) if isinstance(n, ast.Call)]:
        fname = getattr(call.func, "id", None) or getattr(call.func, "attr", None)
        if fname not in SIGS:
            continue
        params, required, _ = SIGS[fname]
        passed = {k.arg for k in call.keywords if k.arg}
        # positional args bind in declaration order
        passed |= set(params[: len(call.args)])
        unknown = passed - set(params)
        missing = required - passed
        check(f"{rel}: {fname}() kwargs exist", not unknown, f"unknown={sorted(unknown)}")
        check(f"{rel}: {fname}() required args passed", not missing, f"missing={sorted(missing)}")

# Return SHAPE (failure 2): a `-> str` wrapper must never be unpacked or have
# `.text` read off it.
for rel in MIGRATED:
    src = pathlib.Path(rel).read_text()
    tree = ast.parse(src)
    for assign in [n for n in ast.walk(tree) if isinstance(n, ast.Assign)]:
        val = assign.value
        if not (isinstance(val, ast.Await) and isinstance(val.value, ast.Call)):
            continue
        fname = getattr(val.value.func, "id", None) or getattr(val.value.func, "attr", None)
        if fname not in SIGS:
            continue
        returns_str = SIGS[fname][2] == "str"
        unpacks = isinstance(assign.targets[0], ast.Tuple)
        check(
            f"{rel}: {fname}() -> str not unpacked",
            not (returns_str and unpacks),
            "a str is not a 2-tuple",
        )

print("\n5. the tier-2 triage path EXECUTES (the born-broken call)")


def _exercise_tier_2() -> tuple:
    import services.anthropic as A
    import services.telemetry as T
    import services.wake_evaluation as W
    import services.workspace as WS

    seen: dict = {}
    rows: list[dict] = []

    async def fake(messages, system, model="x", max_tokens=0):
        seen.update(model=model, system=system, max_tokens=max_tokens)
        return ("observe", {"input_tokens": 400, "output_tokens": 1})

    class FakeMemory:
        def __init__(self, *a, **k):
            pass

        def read(self, p):
            return "x"

    orig = (A.chat_completion_with_usage, T.record_execution_event, WS.UserMemory,
            W.record_execution_event)
    A.chat_completion_with_usage = fake
    T.record_execution_event = lambda c, **kw: rows.append(kw) or "id"
    W.record_execution_event = T.record_execution_event
    WS.UserMemory = FakeMemory
    os.environ.pop("WAKE_TIER_2_DISABLED", None)
    try:
        out = asyncio.run(W.tier_2_decision(object(), "u", "cron_tick", {}))
    finally:
        (A.chat_completion_with_usage, T.record_execution_event, WS.UserMemory,
         W.record_execution_event) = orig
    return out, seen, rows


(decision, reason), seen, rows = _exercise_tier_2()

# Before the fix this returned ("escalate", "tier_2_exception_fail_open") for
# EVERY input — the tell that the call never ran.
check("tier-2 returns a real verdict, not fail-open", decision == "tier_2_observe", f"got {decision}/{reason}")
check("tier-2 runs the registry's engine", seen.get("model") == system_call_model("wake_triage"))
check("tier-2 passes a system prompt", bool(seen.get("system")))
check("tier-2 stays a 10-token verdict", seen.get("max_tokens") == 10)
check("tier-2 meters exactly once (ADR-396 one ledger)", len(rows) == 1)
if rows:
    check("tier-2 ledger row carries the model", rows[0].get("model") == system_call_model("wake_triage"))
    check("tier-2 ledger row carries tokens", rows[0].get("input_tokens") == 400)

print("\n6. no user-facing input reaches a systematic call (ADR-556 D3)")

import inspect

from services.images.decompose import plan_layers

check(
    "plan_layers takes no caller engine",
    "model" not in inspect.signature(plan_layers).parameters,
)
img = pathlib.Path("routes/images.py").read_text()
compose_req = next(
    n for n in ast.walk(ast.parse(img))
    if isinstance(n, ast.ClassDef) and n.name == "ComposeRequest"
)
fields = [
    t.target.id for t in compose_req.body if isinstance(t, ast.AnnAssign)
]
check("ComposeRequest exposes no `model` field", "model" not in fields, f"fields={fields}")

print(f"\n{N - len(FAILS)}/{N} checks passed")
if FAILS:
    print("\nFAILURES:")
    for f in FAILS:
        print(f"  - {f}")
    sys.exit(1)
print("ADR-556 gate GREEN")

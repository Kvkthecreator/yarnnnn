"""ADR-557 — the router chokepoint + the transport/product flag split.

Run: python3 test_adr557_router_hardening.py   (from api/)

Two failures this file exists because of:

  D1. `MODEL_ROUTER_ENABLED` was a CONVENTION, not a mechanism.
      `route_completion` never consulted it, so the flag only held where a
      caller REMEMBERED to check. Four of five did; `services/radar.py` did
      not — and a flag-off sweep did not degrade, it reached Gemini over the
      network on whatever key was in env. Verified by execution, not by
      reading: the call returned successfully with the flag unset.

  D2. ONE flag answered TWO questions — "is transport available" (infra) and
      "are member lanes GA" (product). Fine while lanes were the only caller;
      four machinery callers later, flipping it to ship lanes ALSO silently
      changed how session summaries, Studio arrangement, IMAGES planning and
      radar acquire their models.

The defense is EXECUTION, not grep: a guard that exists is not a guard that
runs (the recorded `feedback_a_scope_that_exists_is_not_a_scope_you_can_enter`
/ `feedback_guard_at_chokepoint_not_call_sites` pair).
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


def _set_flags(transport: str | None, lanes: str | None) -> None:
    for key, val in (("MODEL_ROUTER_ENABLED", transport), ("LANES_ENABLED", lanes)):
        if val is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = val


import services.model_router as mr

print("1. D1 — the chokepoint REFUSES, and does so before any network call")

# THE regression. Before ADR-557 this call SUCCEEDED with the flag off and
# went out to the provider. It must now raise, and raise a DISTINCT type.
_set_flags(None, None)


async def _try(fn) -> Exception | None:
    try:
        await fn()
        return None
    except Exception as exc:  # noqa: BLE001 — we are classifying the exception
        return exc


err = asyncio.run(_try(lambda: mr.route_completion(
    "gemini/gemini-2.5-flash", [{"role": "user", "content": "x"}], max_tokens=5, timeout=5,
)))
check("route_completion refuses with the flag off", isinstance(err, mr.RouterDisabled),
      f"got {type(err).__name__ if err else 'SUCCESS — the leak is back'}")


async def _drain_stream():
    async for _ in mr.route_completion_stream(
        "gemini/gemini-2.5-flash", [{"role": "user", "content": "x"}], max_tokens=5, timeout=5,
    ):
        pass


err = asyncio.run(_try(_drain_stream))
check("route_completion_stream refuses with the flag off", isinstance(err, mr.RouterDisabled),
      f"got {type(err).__name__ if err else 'SUCCESS — the leak is back'}")

# A distinct type matters: every caller wraps in `except Exception` to degrade,
# so a bare RuntimeError would read as a provider outage rather than config.
check("RouterDisabled is its own type", issubclass(mr.RouterDisabled, RuntimeError)
      and mr.RouterDisabled is not RuntimeError)

# The guard must run BEFORE the ~3s litellm import (cost) and before any
# provider work. Asserted structurally: the assert precedes the import stmt.
src = pathlib.Path("services/model_router.py").read_text()
tree = ast.parse(src)
for fname in ("route_completion", "route_completion_stream"):
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, (ast.AsyncFunctionDef, ast.FunctionDef)) and n.name == fname)
    stmts = [ast.dump(s) for s in fn.body]
    guard_idx = next((i for i, s in enumerate(stmts) if "_assert_router_enabled" in s), None)
    import_idx = next((i for i, s in enumerate(stmts) if "litellm" in s and "Import" in s), None)
    check(f"{fname}: guard runs before the litellm import",
          guard_idx is not None and import_idx is not None and guard_idx < import_idx,
          f"guard={guard_idx} import={import_idx}")

print("\n2. D2 — transport and product are separate questions")

_set_flags("1", "0")
check("transport ON + LANES_ENABLED=0 → transport live, lanes dark",
      mr.model_router_enabled() and not mr.lanes_enabled())

_set_flags("1", None)
check("LANES_ENABLED unset → defers to transport (ships INERT)",
      mr.model_router_enabled() and mr.lanes_enabled())

# The asymmetry: a product flag may never grant more than the infra it rides on.
_set_flags("0", "1")
check("product flag cannot exceed infra (transport off ⇒ lanes off)",
      not mr.lanes_enabled())

_set_flags(None, None)

print("\n3. every routed caller is accounted for")

ROUTED_CALLERS = {
    # file -> is it a MEMBER-facing lane path (product flag) or not (transport)
    "services/lane_runner.py": "lanes",
    "services/session_continuity.py": "transport",
    "services/studio_arrangement_plan.py": "transport",
    # ADR-562 moved decompose under apps/ (the roster lagged the move and this
    # gate crashed on the stale path — found 2026-08-18 while adding ADR-580's row).
    "services/apps/images/decompose.py": "transport",
    # ADR-580 D6: the standing lanes' ONE turn home — radar, Strings, and the
    # connector derive all route through it; none touches the transport directly
    # (held per-lane by test_adr580_connector_derive.py §5).
    "services/derive_turn.py": "transport",
}
found = set()
for path in pathlib.Path("services").rglob("*.py"):
    if "route_completion" in path.read_text() and path.name != "model_router.py":
        found.add(str(path))
for p in pathlib.Path("routes").rglob("*.py"):
    body = p.read_text()
    if "await route_completion" in body:
        found.add(str(p))

# A NEW routed caller must be classified deliberately, not inherit a default.
check("no unclassified routed caller appeared",
      found <= set(ROUTED_CALLERS), f"unclassified: {sorted(found - set(ROUTED_CALLERS))}")

for path, kind in ROUTED_CALLERS.items():
    body = pathlib.Path(path).read_text()
    if kind == "lanes":
        # The member surface gates on the PRODUCT flag now.
        check(f"{path}: gates on lanes_enabled (product)",
              "lanes_enabled" in body and "model_router_enabled" not in body)
    else:
        # Machinery keeps the transport flag; it must NOT read the product one.
        check(f"{path}: does not read the product flag", "lanes_enabled" not in body)

# radar was the hole. The D1 guard moved WITH the derive call (ADR-580 D6):
# the shared bounded turn pre-checks the transport flag for every standing
# lane; each lane still meters router-off as its own reason, not a failed
# derive — §4 below EXECUTES that degrade on the real sweep.
turn_body = pathlib.Path("services/derive_turn.py").read_text()
check("the shared derive turn pre-checks the transport flag (the D1 guard's home)",
      "model_router_enabled" in turn_body)
# ⚠️ radar was this section's exemplar and was DELETED (`15403f1`, ADR-592 —
# an app with a clock is deleted, not staged). The gate kept reading
# `services/radar.py` and crashed on the open() for seven weeks, taking §4 with
# it — a stale literal that hid every check BELOW it. The invariant is not
# radar's; it belongs to whatever standing lane routes today. That is
# `standing_work.py` (ADR-639), and it carries the same contract unchanged.
_standing = pathlib.Path("services/standing_work.py").read_text()
check("the standing lane routes its derive through the shared turn",
      "run_bounded_derive_turn" in _standing)
check("the standing lane meters router-off as its own reason, not a failed derive",
      "router_disabled" in _standing)

print("\n4. the standing lane's flag-off run degrades honestly (EXECUTED)")


def _exercise_standing_run():
    """EXECUTE the real bounded derive turn with the transport flag OFF.

    This replaces the deleted radar sweep. It exercises the SAME contract at
    the place the D1 guard actually lives now: with the flag off,
    `run_bounded_derive_turn` must report `router_disabled` rather than let a
    routed call escape to a provider on whatever key is in env.
    """
    from services.derive_turn import run_bounded_derive_turn

    _set_flags(None, None)
    try:
        turn = asyncio.run(run_bounded_derive_turn(
            model="anthropic/claude-haiku-4-5", system="s", user_msg="p",
            max_tokens=16, timeout=5,
        ))
        return {"status": getattr(turn, "status", None)}
    except Exception as exc:  # noqa: BLE001
        return {"raised": type(exc).__name__, "detail": str(exc)[:120]}


_out = _exercise_standing_run()
# What must NEVER happen is a routed call escaping with the flag off. A
# RouterDisabled raise and a `router_disabled` status are both honest; reaching
# a provider is not.
check("the shared turn returns router_disabled with the flag off",
      _out.get("status") == "router_disabled", f"got {_out}")

_set_flags(None, None)

print(f"\n{N - len(FAILS)}/{N} checks passed")
if FAILS:
    print("\nFAILURES:")
    for f in FAILS:
        print(f"  - {f}")
    sys.exit(1)
print("ADR-557 gate GREEN")

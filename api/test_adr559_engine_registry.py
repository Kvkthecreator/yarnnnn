"""ADR-559 — the engine registry: currency, retirement, availability. The ratchet.

Run: python3 test_adr559_engine_registry.py   (from api/)

Three invariants, each with a failure that motivated it:

  D1 CURRENCY   — the roster names models that exist and are priced. The
     Anthropic lane had gone two generations stale (Sonnet 4.6, no Opus tier at
     all), and `_BILLING_RATES` carried a `claude-opus-4-6` row that NOTHING
     could route to — a rate row is a claim about what we run.

  D2 RETIREMENT — `LANE_MODELS` is the TURN-TIME whitelist, not just the
     chooser. At the refresh all 65 live lanes pinned `claude-sonnet-4-6` (56 of
     them bound Studio lanes), so deleting the row would have orphaned the whole
     workspace. Superseded engines STAY routable and leave the door.

  D3 AVAILABILITY — an engine can be dark for three structurally different
     reasons, and only two are knowable before the click. The third
     (`upstream_refused`) is observable ONLY by calling — DeepSeek's
     "Insufficient Balance" is the first instance, and the reason this is a
     mechanism rather than a special case for one row.
"""

from __future__ import annotations

import ast
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


from services.lane_runner import (  # noqa: E402
    LANE_MODELS,
    clear_upstream_refusal,
    lane_model_availability,
    note_upstream_refusal,
    offered_lane_models,
    unpriced_lane_model,
)
from services.model_selection import strip_provider  # noqa: E402
from services.telemetry import _BILLING_RATES, has_billing_rate  # noqa: E402

print("1. D1 — currency: every row is real, priced, and reachable")

for mid in LANE_MODELS:
    # Includes RETIRED rows deliberately: `unpriced_lane_model` gates every
    # turn, so an unpriced retired engine would refuse the very lanes the
    # retired state exists to keep running.
    check(f"{mid}: priced", not unpriced_lane_model(mid))
    check(f"{mid}: provider-prefixed", "/" in mid)

# The phantom-row defect: a rate row nothing can route to is a claim about
# what we run that is not true.
from services.agents_registry import AGENTS  # noqa: E402
from services.model_selection import DEFAULT_ROUTES  # noqa: E402
from services.system_calls import SYSTEM_CALLS  # noqa: E402

_routable = (
    {strip_provider(m) for m in LANE_MODELS}
    | {strip_provider(c.model) for c in SYSTEM_CALLS.values()}
    | {strip_provider(r.model) for r in DEFAULT_ROUTES.values()}
)
_orphan_rates = sorted(set(_BILLING_RATES) - _routable)
check("no priced-but-unroutable engine", not _orphan_rates,
      f"rate rows nothing can route to: {_orphan_rates}")

# Currency: the stale ids must be gone from every SELECTION home. They may
# still appear in LANE_MODELS (retired) — that is D2's job, not D1's.
for name, ids in (
    ("SYSTEM_CALLS", [c.model for c in SYSTEM_CALLS.values()]),
    ("DEFAULT_ROUTES", [r.model for r in DEFAULT_ROUTES.values()]),
    # ADR-600 D5 — iterate the REGISTER, never a hand-spelled list of
    # containers. The predecessor named KERNEL_AGENTS + KERNEL_POSTURES, both
    # of which ADR-599 emptied: this ratchet iterated ZERO rows and reported
    # green while every live engine went unchecked. A register cannot go
    # vacuous without the beings themselves disappearing.
    ("AGENTS", [a["model"] for a in AGENTS.values()]),
):
    stale = [i for i in ids if i in ("anthropic/claude-sonnet-4-6",
                                     "anthropic/claude-haiku-4-5-20251001")]
    check(f"{name}: no superseded engine", not stale, f"stale: {stale}")
    unpriced = [i for i in ids if not has_billing_rate(strip_provider(i))]
    check(f"{name}: every engine priced", not unpriced, f"unpriced: {unpriced}")

# The Anthropic tier ladder the roster lacked entirely.
_anthropic = {m for m in offered_lane_models() if m.startswith("anthropic/")}
check("the door offers an Anthropic frontier (Opus) tier",
      any("opus" in m for m in _anthropic), f"anthropic offered: {sorted(_anthropic)}")

print("\n2. D2 — retirement: honored for existing lanes, gone from the door")

_retired = {m for m, meta in LANE_MODELS.items() if meta.get("retired")}
check("at least one engine is retired (the state is live, not theoretical)",
      bool(_retired))
check("retired engines are NOT offered",
      not (_retired & set(offered_lane_models())),
      f"leaked to the door: {sorted(_retired & set(offered_lane_models()))}")
check("retired engines ARE still in LANE_MODELS (the turn-time whitelist)",
      _retired <= set(LANE_MODELS))
# THE regression: 65 live lanes pinned this at the refresh.
check("the engine every live lane pinned is still routable",
      "anthropic/claude-sonnet-4-6" in LANE_MODELS,
      "deleting it orphans every existing conversation")

# The turn loops must gate on the FULL dict, never the offered subset — that
# is what makes a retired lane keep running.
lr_src = pathlib.Path("services/lane_runner.py").read_text()
tree = ast.parse(lr_src)
for fname in ("run_lane_turn", "run_lane_turn_stream"):
    fn = next(n for n in ast.walk(tree)
              if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == fname)
    body = ast.unparse(fn)
    check(f"{fname} gates on LANE_MODELS, not the offered subset",
          "model not in LANE_MODELS" in body and "offered_lane_models" not in body,
          "gating the loop on the chooser's list would break retired lanes")

# ...and the door must NOT serve the full dict.
routes_src = pathlib.Path("routes/lanes.py").read_text()
env_fn = next(n for n in ast.walk(ast.parse(routes_src))
              if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
              and n.name == "_lane_envelope")
env_body = ast.unparse(env_fn)
check("the envelope serves offered_lane_models(), not LANE_MODELS",
      "offered_lane_models" in env_body)

print("\n3. D3 — availability: three reasons, two computed, one observed")

_saved = {k: os.environ.get(k) for k in
          ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "DEEPSEEK_API_KEY")}
try:
    probe = "deepseek/deepseek-chat"

    # (a) no_provider_key — computed from env.
    os.environ.pop("DEEPSEEK_API_KEY", None)
    ok, why = lane_model_availability(probe)
    check("a missing provider key darkens the engine",
          not ok and why == "no_provider_key", f"got {ok}/{why}")

    # (b) available — with a key and a rate row.
    os.environ["DEEPSEEK_API_KEY"] = "probe-key"
    ok, why = lane_model_availability(probe)
    check("with a key and a rate, the engine is available", ok and why is None,
          f"got {ok}/{why}")

    # (c) upstream_refused — OBSERVED, not computed. The DeepSeek case.
    marked = note_upstream_refusal(
        probe, Exception('DeepseekException - {"message":"Insufficient Balance"}'))
    check("an account refusal is recorded", marked)
    ok, why = lane_model_availability(probe)
    check("...and darkens the engine", not ok and why == "upstream_refused",
          f"got {ok}/{why}")

    # A success heals it — no operator action, no persisted row to clear.
    clear_upstream_refusal(probe)
    ok, _ = lane_model_availability(probe)
    check("a successful call heals the engine", ok)

    # NARROWNESS. Marking dark on any error would take a whole engine out of
    # the picker for one transient blip.
    for exc in (TimeoutError("Request timed out"),
                Exception("rate_limit_exceeded"),
                Exception("400 invalid_request_error"),
                Exception("overloaded_error")):
        check(f"transient error does NOT darken ({type(exc).__name__}: {str(exc)[:28]})",
              not note_upstream_refusal(probe, exc))
    ok, _ = lane_model_availability(probe)
    check("...engine still available after transient errors", ok)
finally:
    for k, v in _saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v

print("\n4. the door refuses BEFORE the first message")

create_fn = next(n for n in ast.walk(ast.parse(routes_src))
                 if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                 and n.name == "create_lane")
create_body = ast.unparse(create_fn)
check("create_lane refuses a retired engine", 'retired' in create_body)
check("create_lane refuses an unavailable engine",
      "lane_model_availability" in create_body)
# Both checks must precede persistence — a conversation that exists but cannot
# run is worse than a refusal.
_ins = create_body.find("lane_meta")
check("...both before the lane row is built",
      create_body.find("lane_model_availability") < _ins,
      "refusing after insert leaves an unusable conversation behind")

print("\n5. FE — the door greys, never hides")

web = pathlib.Path("../web")
modal = (web / "components/chat-surface/NewChatModal.tsx").read_text()
check("modal reads the availability flag", "e.available === false" in modal)
check("modal disables an unavailable engine", "disabled={!!busy || dark}" in modal)
check("modal renders a member-facing reason", "UNAVAILABLE_COPY" in modal)
check("modal does NOT filter unavailable engines out",
      ".filter(" not in modal.split("engines.map")[0].split("const dark")[0][-400:],
      "hiding an engine reads as a bug to the member who expects it")

attribution = (web / "lib/workspace/attribution.ts").read_text()
for mid in offered_lane_models():
    check(f"attribution can name {mid}", f"'{mid}'" in attribution,
          "an un-named engine renders as a raw model id")

print(f"\n{N - len(FAILS)}/{N} checks passed")
if FAILS:
    print("\nFAILURES:")
    for f in FAILS:
        print(f"  - {f}")
    sys.exit(1)
print("ADR-559 gate GREEN")

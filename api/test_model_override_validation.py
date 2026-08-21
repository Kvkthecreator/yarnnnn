"""Env-supplied model overrides are VALIDATED, not trusted (2026-08-21).

WHY THIS GATE EXISTS. `YARNNN_MODEL_{SHAPE}` (the steward) and
`YARNNN_SYSCALL_{CALL_TYPE}` (machinery) both used to accept an arbitrary
string, log it at INFO, and hand it to a provider SDK. Two silent failures
followed from that:

  • a TYPO on a Render dashboard routed to a model that does not exist — the
    call fails at the provider, far from the cause;
  • an UNPRICED id billed at the `_DEFAULT_RATE`, which is the silent cost lie
    ADR-439 §4 exists to prevent.

Neither shouted. Both produced a plausible wrong answer, which is the hardest
kind of defect to notice — the same class as the retired-2x-markup and the
shared-label defects found in the same audit.

THE SHAPE OF THE FIX (asserted below):
  • KNOWN   — must be a `LANE_MODELS` key. Retired rows COUNT: a retired engine
              is still routable (ADR-559 D2), so naming one is legitimate.
  • PRICED  — must have a `_BILLING_RATES` row.
  • IGNORE, NEVER RAISE — these resolvers run inside live wakes and lane turns.
              A bad dial degrades to the DECLARED engine and logs at ERROR.
              Raising would turn a cost mistake into an outage.
  • ONE VALIDATOR — both dials call `accept_model_override`. Two copies would
              drift, and the point of the audit was that duplicated routing
              logic is how a retired value survives.

Run from api/:  python3 test_model_override_validation.py
"""
import logging
import os
import sys

sys.path.insert(0, ".")
logging.disable(logging.CRITICAL)  # the validator logs at ERROR by design

from services.lane_runner import LANE_MODELS  # noqa: E402
from services.model_selection import (  # noqa: E402
    DEFAULT_ROUTES,
    SHAPE_ADDRESSED,
    accept_model_override,
    resolve_route,
    strip_provider,
)
from services.system_calls import SYSTEM_CALLS, resolve_system_call  # noqa: E402
from services.telemetry import has_billing_rate  # noqa: E402

FAILS = []


def check(label, cond, detail=""):
    if cond:
        print(f"  ok   {label}")
    else:
        FAILS.append(label)
        print(f"  FAIL {label}" + (f"\n         {detail}" if detail else ""))


print("\nmodel-override-validation:")

DECLARED = "anthropic/claude-haiku-4-5"

# ---- 1. The two rejection branches ---------------------------------------
check(
    "an UNKNOWN engine is ignored; the declared model stands",
    accept_model_override("V", "anthropic/claude-sonnet-6", DECLARED) == DECLARED,
)

check(
    "a BARE id (no provider prefix) is ignored — the dials take provider/model",
    accept_model_override("V", "claude-haiku-4-5", DECLARED) == DECLARED,
)

# Reaching the unpriced branch needs an injected row: every real LANE_MODELS
# row is priced, and another gate enforces exactly that.
LANE_MODELS["anthropic/probe-unpriced"] = {"label": "Probe", "vision": True}
try:
    check(
        "a KNOWN but UNPRICED engine is ignored (ADR-439 §4)",
        accept_model_override("V", "anthropic/probe-unpriced", DECLARED) == DECLARED,
    )
finally:
    LANE_MODELS.pop("anthropic/probe-unpriced", None)

# ---- 2. The acceptance branches -------------------------------------------
check(
    "a valid engine is accepted",
    accept_model_override("V", "anthropic/claude-opus-5", DECLARED)
    == "anthropic/claude-opus-5",
)

_retired = [m for m, meta in LANE_MODELS.items() if meta.get("retired")]
check(
    "a RETIRED engine is ACCEPTED — retired means un-offered, not un-routable",
    bool(_retired) and accept_model_override("V", _retired[0], DECLARED) == _retired[0],
    f"retired rows: {_retired}",
)

# ---- 3. It never raises ---------------------------------------------------
_hostile = ["", "   ", "/", "a/b/c", "anthropic/", "../etc/passwd", "None"]
_raised = []
for bad in _hostile:
    try:
        accept_model_override("V", bad, DECLARED)
    except Exception as exc:  # noqa: BLE001
        _raised.append(f"{bad!r} → {exc!r}")
check(
    "never raises on hostile input (a bad dial must not take the steward down)",
    not _raised,
    f"raised on: {_raised}",
)

# ---- 4. BOTH dials actually route through it ------------------------------
# Behavioural, not source-shaped: set the env var and read the resolved model.
_syscall_key = "fact_extraction"
_declared_syscall = SYSTEM_CALLS[_syscall_key].model
os.environ["YARNNN_SYSCALL_FACT_EXTRACTION"] = "anthropic/claude-sonnet-6"
try:
    check(
        "YARNNN_SYSCALL_* validates (a typo resolves to the declared engine)",
        resolve_system_call(_syscall_key).model == _declared_syscall,
    )
    os.environ["YARNNN_SYSCALL_FACT_EXTRACTION"] = "anthropic/claude-opus-5"
    check(
        "YARNNN_SYSCALL_* still HONOURS a valid override (not merely disabled)",
        resolve_system_call(_syscall_key).model == "anthropic/claude-opus-5",
    )
finally:
    os.environ.pop("YARNNN_SYSCALL_FACT_EXTRACTION", None)

_declared_route = DEFAULT_ROUTES[SHAPE_ADDRESSED].model
os.environ["YARNNN_MODEL_ADDRESSED"] = "not-a-model"
try:
    check(
        "YARNNN_MODEL_* validates (a typo resolves to the declared engine)",
        resolve_route("addressed", False).model == _declared_route,
    )
    os.environ["YARNNN_MODEL_ADDRESSED"] = "openai/gpt-5"
    check(
        "YARNNN_MODEL_* still HONOURS a valid override (not merely disabled)",
        resolve_route("addressed", False).model == "openai/gpt-5",
    )
finally:
    os.environ.pop("YARNNN_MODEL_ADDRESSED", None)

check(
    "with no override set, the declared model is returned untouched",
    resolve_route("addressed", False).model == _declared_route
    and resolve_system_call(_syscall_key).model == _declared_syscall,
)

# ---- 5. The safe floor is genuinely safe ----------------------------------
# The fallback is only sound if every DECLARED value would itself pass.
_bad_declared = [
    f"{k}={c.model}"
    for k, c in SYSTEM_CALLS.items()
    if c.model not in LANE_MODELS or not has_billing_rate(strip_provider(c.model))
] + [
    f"{s}={r.model}"
    for s, r in DEFAULT_ROUTES.items()
    if r.model not in LANE_MODELS or not has_billing_rate(strip_provider(r.model))
]
check(
    "every DECLARED model would itself pass the validator (the floor is safe)",
    not _bad_declared,
    f"declared-but-invalid: {_bad_declared}",
)

print(f"\n{len(FAILS)} FAILED" if FAILS else "\nmodel-override-validation: all checks passed")
sys.exit(1 if FAILS else 0)

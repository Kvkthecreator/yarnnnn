"""ADR-618 gate — unattended standing work is bounded by the pool.

Holds two decisions:
  §1 a string's run is BALANCE-GATED, before the fetch, and a refusal is a
     RECORDED run (the desk must be able to say why nothing moved)
  §2 the MANUAL fire takes the same CAS claim the scheduled drain takes

Script-style (python3, from api/).
"""

from __future__ import annotations

import ast
import asyncio
import sys
from pathlib import Path

API = Path(__file__).resolve().parent
sys.path.insert(0, str(API))

PASS = 0
FAIL = 0


def check(label: str, ok, detail: str = "") -> None:
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  [PASS] {label}")
    else:
        FAIL += 1
        print(f"  [FAIL] {label}" + (f" — {detail}" if detail else ""))


import services.platform_limits as pl  # noqa: E402
import services.strings as st  # noqa: E402
import services.telemetry as tel  # noqa: E402

# ═════════════════════════════════════════════════════════════════════════════
print("§1 a string's run is bounded by the workspace pool")
# ═════════════════════════════════════════════════════════════════════════════


def _decl():
    return st.StringDecl(
        topic="ops/x", slug="string:ops/x", target="x.md",
        schedule={"type": "daily"}, sources=[{"id": "s", "url": "http://x"}],
    )


def _run_at_balance(balance: float):
    """Drive the real sweep with the pool at `balance`. Returns (result, events)."""
    real_bal, real_ree = pl.get_effective_balance, tel.record_execution_event
    events: list = []
    pl.get_effective_balance = lambda c, u, _b=balance: _b
    tel.record_execution_event = lambda *a, **k: events.append(k)
    try:
        out = asyncio.new_event_loop().run_until_complete(
            st.run_string_sweep(object(), "u-1", _decl())
        )
    except Exception as exc:  # noqa: BLE001 — proceeding past the gate is the signal
        out = {"_proceeded": type(exc).__name__}
    finally:
        pl.get_effective_balance, tel.record_execution_event = real_bal, real_ree
    return out, events


_out0, _ev0 = _run_at_balance(0.0)
check("1a an exhausted pool REFUSES the run",
      _out0.get("error_reason") == "balance_exhausted", f"got {_out0}")

# ⭐ The refusal must be OBSERVABLE. A silent skip leaves the desk unable to
# say why nothing moved, which reads as a broken string rather than an empty
# balance — the ADR-373 D6 incorrect-success shape in its quiet form.
check("1b the refusal is a RECORDED run, not a silent skip",
      any(e.get("error_reason") == "balance_exhausted" for e in _ev0),
      f"events={[e.get('error_reason') for e in _ev0]}")

# ⭐⭐ BEFORE the fetch, not merely before the derive. The fetch writes retained
# observations and reaches connectors — work whose only purpose is to feed a
# derive that cannot run. A gate that lets the pointless half proceed is a
# half-gate, and it would show up here as a `string-sweep` success event.
check("1c nothing was fetched — the gate precedes the fetch",
      not any(e.get("status") == "success" for e in _ev0),
      f"events={[(e.get('slug'), e.get('status')) for e in _ev0]}")

# The discriminating half: a FUNDED pool must get past the gate. Without this
# row, a gate that refused unconditionally would pass every check above.
_out5, _ev5 = _run_at_balance(5.0)
check("1d a funded pool proceeds past the gate",
      _out5.get("error_reason") != "balance_exhausted", f"got {_out5}")

# ⭐ `check_balance`, NOT `check_draw`. Standing work attributes to the OWNER,
# who is never member-capped, so `check_draw`'s second half is a no-op here and
# reaching for it would imply a per-member bound this lane does not have. This
# is the convention the wake lane already holds and that `check_draw`'s own
# docstring names ("NOT called on the wake/recurrence lane").
# Read off the parsed CALLS, not the source text — this module's own comments
# name `check_draw` to explain why it is NOT used, so a substring check reads
# the explanation as the violation. (It did: 1e failed on its own prose.)
_SRC = (API / "services" / "strings.py").read_text()
_st_tree = ast.parse(_SRC)
_st_fn = next(
    (n for n in ast.walk(_st_tree)
     if isinstance(n, (ast.AsyncFunctionDef, ast.FunctionDef))
     and n.name == "run_string_sweep"),
    None,
)
_st_calls = {
    n.func.id if isinstance(n.func, ast.Name) else getattr(n.func, "attr", "")
    for n in ast.walk(_st_fn) if isinstance(n, ast.Call)
} if _st_fn else set()
check("1e the lane uses the pool hard-stop, not the member-cap gate",
      "check_balance" in _st_calls and "check_draw" not in _st_calls,
      f"calls={sorted(_st_calls)}")

# ⭐ Fail-OPEN on a check that cannot RUN, matching wake.py exactly: a DB
# hiccup must not silently stop an operator's standing work. (check_balance
# itself already returns 0.0 → blocked on a balance-READ failure, so this
# covers only the case where the check could not run at all.)
_real = pl.get_effective_balance


def _boom(*a, **k):
    raise RuntimeError("balance backend down")


pl.get_effective_balance = _boom
_evs: list = []
_real_ree = tel.record_execution_event
tel.record_execution_event = lambda *a, **k: _evs.append(k)
try:
    _outE = asyncio.new_event_loop().run_until_complete(
        st.run_string_sweep(object(), "u-1", _decl())
    )
except Exception as exc:  # noqa: BLE001
    _outE = {"_proceeded": type(exc).__name__}
finally:
    pl.get_effective_balance, tel.record_execution_event = _real, _real_ree
check("1f a check that cannot RUN fails open (never strands standing work)",
      _outE.get("error_reason") != "balance_exhausted", f"got {_outE}")

# ═════════════════════════════════════════════════════════════════════════════
print("§1b the ledger records regardless of the caller's client")
# ═════════════════════════════════════════════════════════════════════════════

# ⭐⭐⭐ FOUND BY DRIVING. `execution_events` is service-role-only for INSERT, so
# a caller holding a USER client has its row refused by RLS (42501). Because
# `record_execution_event` never raises (correctly — telemetry must not fail a
# run), the caller sees success and the spend VANISHES. Live: the strings
# manual door passes `auth.client`, so every Run-now recorded nothing, while
# the same sweep from the scheduler (service client) recorded fine — an
# asymmetry between two doors into one body.
#
# Behavioural, not a source check: "does it import get_service_client" would
# pass against a version that imports it and then inserts with the caller's.
import services.telemetry as _tel  # noqa: E402

_ins: list = []


class _RlsRefusingClient:
    """A client whose INSERT is refused by RLS — what a user-role client does
    against a service-role-only table. It RAISES (PostgREST surfaces 42501 as
    an APIError), which is the shape the writer must not simply swallow."""

    def table(self, _n):
        return self

    def insert(self, row):
        self._row = row
        return self

    def execute(self):
        raise RuntimeError('new row violates row-level security policy')


class _SvcDouble:
    def table(self, _n):
        return self

    def insert(self, row):
        _ins.append(row)
        return self

    def execute(self):
        from types import SimpleNamespace
        return SimpleNamespace(data=[{"id": "row-1"}])


import services.supabase as _sb  # noqa: E402

_real_svc = _sb.get_service_client
_sb.get_service_client = lambda *a, **k: _SvcDouble()
try:
    _rid = _tel.record_execution_event(
        _RlsRefusingClient(), user_id="u-1", slug="string-sweep:probe",
        mode="mechanical", trigger_type="scheduled", status="success",
        duration_ms=1, funnel_decision="string",
    )
    check("1g an RLS-refusing caller still lands the ledger row",
          _rid is not None and len(_ins) == 1,
          f"rid={_rid!r} inserts={len(_ins)}")
    check("1h the row keeps its lane marker through the swap",
          bool(_ins) and _ins[0].get("funnel_decision") == "string",
          f"row={_ins[0] if _ins else None}")
finally:
    _sb.get_service_client = _real_svc

# ═════════════════════════════════════════════════════════════════════════════
print("§2 the manual fire takes the same claim as the scheduled drain")
# ═════════════════════════════════════════════════════════════════════════════

_ROUTE = (API / "routes" / "strings.py").read_text()
_tree = ast.parse(_ROUTE)
_fn = next(
    (n for n in ast.walk(_tree)
     if isinstance(n, (ast.AsyncFunctionDef, ast.FunctionDef))
     and n.name == "run_string_now"),
    None,
)
check("2a the manual-run route exists", _fn is not None)

if _fn is not None:
    _calls = [
        n.func.id if isinstance(n.func, ast.Name) else getattr(n.func, "attr", "")
        for n in ast.walk(_fn) if isinstance(n, ast.Call)
    ]
    # Read off the parsed CALLS, never the source text: the words appear in
    # this route's prose, so a substring check would pass against a version
    # that only mentions the claim.
    check("2b it CLAIMS before running (no double-run/double-spend window)",
          "claim_string_run" in _calls, f"calls={sorted(set(_calls))}")
    check("2c it reads the current next_run_at to claim against",
          "read_string_task_row" in _calls)
    # Ordering is the whole point: claiming after the sweep bounds nothing.
    _idx = {c: i for i, c in enumerate(_calls)}
    check("2d the claim precedes the sweep",
          _idx.get("claim_string_run", 99) < _idx.get("run_string_sweep", -1),
          f"claim@{_idx.get('claim_string_run')} sweep@{_idx.get('run_string_sweep')}")

# ⭐ A never-indexed string (declared since the last tick) has no row to claim
# against — it must stay RUNNABLE. Reading `None` as a lost race would make a
# brand-new string permanently un-fireable by hand.
check("2e a never-indexed string is claimable, not read as a lost race",
      "if _row is not None and not _claimed" in _ROUTE)

print()
print(f"{PASS}/{PASS + FAIL} ADR-618 assertions pass")
sys.exit(1 if FAIL else 0)

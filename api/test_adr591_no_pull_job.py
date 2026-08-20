"""ADR-591 gate — setting up a connector is not running a pull job.

Holds the ratified contract:
  §1 cadence is retired — no clock, no law, no enum, no binding default
  §2 no connector job exists on the scheduler (walk, digest, GC)
  §3 the WRITERS survive and stay invocable (D3's seam has something to call)
  §4 the flag is gone; the configuration surface does not depend on one
  §5 the spend guard survives the walker it used to serve

Script-style (python3, from api/).
"""

from __future__ import annotations

import ast
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


import services.connector_derive as cd  # noqa: E402
import services.connector_retention as cr  # noqa: E402
import services.connectors as conn  # noqa: E402

SCHED = (API / "jobs" / "unified_scheduler.py").read_text()
ROUTES = (API / "routes" / "integrations.py").read_text()

# ═════════════════════════════════════════════════════════════════════════════
print("§1 cadence is retired — a connector has no 'how often'")
# ═════════════════════════════════════════════════════════════════════════════

check("1a the cadence law is deleted", not hasattr(conn, "_cadence_due"))
check("1b the bounded cadence enum is deleted",
      not hasattr(conn, "CONNECTOR_CADENCE_CHOICES"))
check("1c the cadence→seconds map is deleted",
      not hasattr(conn, "_CADENCE_SECONDS"))
check("1d no per-platform binding carries a cadence default",
      all("cadence" not in b for b in conn.CONNECTOR_CAPTURE_BINDINGS.values()),
      str({k: sorted(v) for k, v in conn.CONNECTOR_CAPTURE_BINDINGS.items()}))

# The settings object is narrowed to what a consumer actually reads.
_s = conn.connector_settings({"platform": "slack", "settings": {}})
check("1e connector_settings serves destination + last_capture_at only",
      set(_s) == {"destination", "last_capture_at"}, str(sorted(_s)))
check("1f last_capture_at survives as an OBSERVATION, not a clock "
      "(nothing compares it to an interval)",
      "_CADENCE_SECONDS" not in (API / "services" / "connectors.py").read_text())

# ═════════════════════════════════════════════════════════════════════════════
print("§2 the scheduler holds NO connector job")
# ═════════════════════════════════════════════════════════════════════════════

for _dead in ("drain_due_connector_captures", "drain_due_connector_derives",
              "prune_raw_lane", "gather_cited_raw_paths"):
    check(f"2a {_dead} is gone from the scheduler", _dead not in SCHED)

check("2b the deleted capture flag has no reader anywhere in the scheduler",
      "CONNECTOR_CAPTURE_ENABLED" not in SCHED
      and "connector_capture_gating" not in SCHED)
check("2c the walkers are gone from the service modules too, not merely "
      "unwired (a dormant walker is a second way to do D3)",
      not hasattr(conn, "drain_due_connector_captures")
      and not hasattr(cd, "drain_due_connector_derives")
      and not hasattr(cr, "prune_raw_lane"))
check("2d the ADR-393 declaration lane keeps its OWN gate (a different lane, "
      "different tenants — not deleted by this ADR)",
      "is_capture_lane_enabled" in SCHED)

# ═════════════════════════════════════════════════════════════════════════════
print("§3 the writers survive — D3's seam has something to call")
# ═════════════════════════════════════════════════════════════════════════════

check("3a the capture writer is invocable",
      callable(getattr(conn, "run_connector_capture", None)))
check("3b the derive writer is invocable",
      callable(getattr(cd, "run_connector_derive", None)))
check("3c the retention DIAL survives (operator config, never a walker)",
      callable(getattr(cr, "read_retention_days", None))
      and callable(getattr(cr, "write_retention_days", None)))
check("3d attribution is untouched — the writer still signs system:capture-*",
      "system:capture-" in (API / "services" / "connectors.py").read_text())

# ═════════════════════════════════════════════════════════════════════════════
print("§4 no flag gates whether a connector is configurable")
# ═════════════════════════════════════════════════════════════════════════════

check("4a the connector capture gating module is DELETED",
      not (API / "services" / "connector_capture_gating.py").exists())
check("4b no route consults a capture resolver",
      "is_connector_capture_enabled" not in ROUTES)

# The retired dials must be REFUSED at the door, not silently dropped: a dial
# that controls nothing has to fail loudly (extra="forbid", the ADR-562 rule).
from routes.integrations import ConnectorSettingsRequest  # noqa: E402
import pydantic  # noqa: E402

_refused = []
for _dead in ("cadence", "digest"):
    try:
        ConnectorSettingsRequest(**{_dead: "x"})
    except pydantic.ValidationError:
        _refused.append(_dead)
check("4c a retired dial 422s at the door rather than appearing to work",
      _refused == ["cadence", "digest"], str(_refused))
check("4d destination — the one surviving setting — still writes",
      "destination" in ConnectorSettingsRequest.model_fields)

# ═════════════════════════════════════════════════════════════════════════════
print("§5 the spend guard outlives the clock it served")
# ═════════════════════════════════════════════════════════════════════════════

# is_due was the walker's pace law, but it is not a schedule — it is the
# ADR-401 D5 lesson ("capture chatter can never multiply judgment spend").
# A consumer-invoked derive needs it MORE than a cron did: a caller in a loop
# is exactly the failure it refuses.
check("5a the pace law survives the walker's deletion",
      callable(getattr(cd, "is_due", None)))
_src = (API / "services" / "connector_derive.py").read_text()
_fn = next(n for n in ast.walk(ast.parse(_src))
           if isinstance(n, ast.FunctionDef) and n.name == "is_due")
check("5b it is documented as a SPEND GUARD, not a schedule "
      "(so a future caller knows to gate on it)",
      "spend guard" in (ast.get_docstring(_fn) or "").lower(),
      (ast.get_docstring(_fn) or "")[:120])

n = PASS + FAIL
print(f"\n{PASS}/{n} ADR-591 assertions pass")
sys.exit(0 if FAIL == 0 else 1)

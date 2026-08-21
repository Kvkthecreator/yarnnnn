"""ADR-591 gate — setting up a connector is not running a pull job.

Holds the ratified contract, as amended by ADR-594 (the connection is a rail):
  §1 cadence is retired — no clock, no law, no enum, no binding default
  §2 no connector job exists on the scheduler (walk, digest, GC)
  §3 the capture WRITER survives — and the D3 seam now HAS its caller
     (a string's run reaches through the connection; ADR-594 D2)
  §4 no flag, no settings door — a connection is consent + credential +
     aperture; the destination dial is deleted (ADR-594 D1) and the digest
     is superseded (ADR-594 D3)
  §5 the spend guard survives IN CONCEPT — the strings-side freshness floor
     succeeded the digest's `is_due`

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

# ADR-594 D1: the settings object itself is gone — the destination dial was
# its last tenant, and `settings["connector"]` is an unread fossil key.
check("1e connector_settings is DELETED with the last dial (a connection "
      "carries no per-connection knobs)",
      not hasattr(conn, "connector_settings")
      and not hasattr(conn, "update_connector_settings")
      and not hasattr(conn, "_validate_destination"))

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
      and not hasattr(cr, "prune_raw_lane"))
check("2d the ADR-393 declaration lane keeps its OWN gate (a different lane, "
      "different tenants — not deleted by this ADR)",
      "is_capture_lane_enabled" in SCHED)

# ═════════════════════════════════════════════════════════════════════════════
print("§3 the writer survives — and the D3 seam HAS its caller (ADR-594 D2)")
# ═════════════════════════════════════════════════════════════════════════════

check("3a the capture writer is invocable",
      callable(getattr(conn, "run_connector_capture", None)))

# The seam ADR-591 D3 named is no longer unbuilt: a string's run reaches
# through the connection (aperture-intersected, freshness-floored) and then
# reads what landed. The caller is Strings — a consumer — never a clock.
STRINGS_SRC = (API / "services" / "strings.py").read_text()
check("3b the seam's caller exists: strings invokes run_connector_capture",
      "run_connector_capture" in STRINGS_SRC)
check("3c strings is the ONLY production caller (a clock reappearing here "
      "would be the pull job growing back)",
      "run_connector_capture" not in SCHED
      and "run_connector_capture" not in ROUTES)
check("3d the retention DIAL survives (a live pricing axis — its disposition "
      "is a pricing decision, named owed in ADR-594 §3)",
      callable(getattr(cr, "read_retention_days", None))
      and callable(getattr(cr, "write_retention_days", None)))
check("3e attribution is untouched — the writer still signs system:capture-*",
      "system:capture-" in (API / "services" / "connectors.py").read_text())

# ═════════════════════════════════════════════════════════════════════════════
print("§4 no flag, no settings door — the connection is a rail (ADR-594 D1/D3)")
# ═════════════════════════════════════════════════════════════════════════════

check("4a the connector capture gating module is DELETED",
      not (API / "services" / "connector_capture_gating.py").exists())
check("4b no route consults a capture resolver",
      "is_connector_capture_enabled" not in ROUTES)
check("4c the connector-settings door is DELETED with its last dial "
      "(ConnectorSettingsRequest + the PUT route)",
      "ConnectorSettingsRequest" not in ROUTES
      and "connector-settings" not in [
          getattr(r, "path", "") for r in __import__(
              "routes.integrations", fromlist=["router"]).router.routes
      ])
check("4d the digest module stays DELETED (superseded by the md string — "
      "ADR-594 D3; a second prose-derive lane is a dual implementation)",
      not (API / "services" / "connector_derive.py").exists())

# ═════════════════════════════════════════════════════════════════════════════
print("§5 the spend guard survives in concept — the freshness floor")
# ═════════════════════════════════════════════════════════════════════════════

# The digest's `is_due` died with its only would-be consumer (ADR-594 D3).
# Its JOB — "a caller in a loop must not multiply platform reads" — survives
# as the strings-side freshness floor: a selector whose newest landed
# snapshot is younger than the floor is READ, not re-reached.
import services.strings as st  # noqa: E402

check("5a the freshness floor exists and is a real interval",
      isinstance(getattr(st, "_CONNECTOR_CAPTURE_MIN_INTERVAL_S", None), int)
      and st._CONNECTOR_CAPTURE_MIN_INTERVAL_S >= 60)

_tree = ast.parse(STRINGS_SRC)
_reach = next((n for n in ast.walk(_tree)
               if isinstance(n, ast.AsyncFunctionDef)
               and n.name == "_reach_connector_sources"), None)
check("5b the reach path gates on the floor BEFORE invoking capture",
      _reach is not None
      and "_CONNECTOR_CAPTURE_MIN_INTERVAL_S" in ast.unparse(_reach)
      and "run_connector_capture" in ast.unparse(_reach))

n = PASS + FAIL
print(f"\n{PASS}/{n} ADR-591 assertions pass")
sys.exit(0 if FAIL == 0 else 1)

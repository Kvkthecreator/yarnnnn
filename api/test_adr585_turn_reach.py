"""ADR-585 gate — turn reach: the member's own connections, inside their own turn.

Holds the ratified contract:
  §1 the surface is DERIVED and read-only (registry rosters, never hand-kept)
  §2 the lane surface carries reach ONLY when asked — default callers unchanged
  §3 the principal-presence cut line (open chat only; app/artifact/derive kill it)
  §4 presence at the chokepoint (lane auth = human hands; steward stays closed)
  §5 payload · allowlist · prose derive from the SAME turn fact

Script-style (python3, from api/). Dormant by default: TURN_REACH_ENABLED
unset must leave every surface byte-identical to pre-585.
"""

from __future__ import annotations

import ast
import os
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


# ═════════════════════════════════════════════════════════════════════════════
print("§1 the surface — derived, read-only, schema-complete")
# ═════════════════════════════════════════════════════════════════════════════

os.environ.pop("TURN_REACH_ENABLED", None)

from services.turn_reach import (  # noqa: E402
    TURN_REACH_PLATFORMS,
    is_turn_reach_enabled,
    turn_reach_tool_defs,
    turn_reach_tool_names,
)
from services.platform_tools import PLATFORM_TOOLS_BY_CAPABILITY  # noqa: E402

check("1a the flag defaults OFF", not is_turn_reach_enabled())

names = turn_reach_tool_names()
expected = tuple(
    n for p in TURN_REACH_PLATFORMS
    for n in PLATFORM_TOOLS_BY_CAPABILITY[f"read_{p}"]
)
check("1b names ARE the registry's read rosters (derived, not hand-kept)",
      names == expected, str(names))

writes = {n for k, v in PLATFORM_TOOLS_BY_CAPABILITY.items()
          if k.startswith("write_") for n in v}
check("1c every reach tool is read-only (no write roster overlap)",
      names and not (set(names) & writes))

defs = turn_reach_tool_defs()
check("1d every name has a schema from the provider rosters",
      {d["name"] for d in defs} == set(names))

# ═════════════════════════════════════════════════════════════════════════════
print("§2 the lane surface — reach only when asked; default callers unchanged")
# ═════════════════════════════════════════════════════════════════════════════

from services.lane_runner import (  # noqa: E402
    lane_caller_identity,
    lane_tool_names,
    lane_tools_openai,
    turn_has_reach,
)

base = lane_tool_names()
check("2a the default surface carries NO platform tool (pre-585 byte-identical)",
      not any(n.startswith("platform_") for n in base), str(base))
check("2b lane_tools_openai() default payload carries none either",
      not any(t["function"]["name"].startswith("platform_")
              for t in lane_tools_openai()))

with_reach = lane_tool_names(True)
check("2c reach appends exactly the derived surface, after the base",
      with_reach == base + names, str(with_reach[-3:]))
payload_names = [t["function"]["name"] for t in lane_tools_openai(True)]
check("2d the reach payload matches the reach allowlist (the D4 agreement)",
      payload_names == list(with_reach))

# ═════════════════════════════════════════════════════════════════════════════
print("§3 the principal-presence cut line")
# ═════════════════════════════════════════════════════════════════════════════

check("3a flag OFF → no reach even for the open chat turn",
      not turn_has_reach(None, None, None))

os.environ["TURN_REACH_ENABLED"] = "true"
try:
    check("3b flag ON + open chat turn → reach",
          turn_has_reach(None, None, None))
    check("3c an app binding kills reach (apps are workspace-disciplined)",
          not turn_has_reach("docs", None, None))
    check("3d a bound artifact kills reach (Studio is an app surface)",
          not turn_has_reach(None, "Documents/deck.html", None))
    check("3e a derive recipe kills reach",
          not turn_has_reach(None, None, "context-brief"))
finally:
    os.environ.pop("TURN_REACH_ENABLED", None)

# ═════════════════════════════════════════════════════════════════════════════
print("§4 presence at the chokepoint — lane auth is human hands; steward closed")
# ═════════════════════════════════════════════════════════════════════════════

from types import SimpleNamespace  # noqa: E402
from services.platform_credentials import is_agent_caller  # noqa: E402

lane_auth = SimpleNamespace(
    caller_identity=lane_caller_identity("u-123", "anthropic/claude-sonnet-4-6"),
    auth_type="user",
)
check("4a a lane turn's member-embodiment is NOT agent-shaped "
      "(ADR-577 composes, not bends)",
      not is_agent_caller(lane_auth), lane_auth.caller_identity)
check("4b an agent-shaped caller IS still refused",
      is_agent_caller(SimpleNamespace(caller_identity="specialist:researcher")))

# The LIVE roster, not a source grep — the registry is where the steward's
# surface is actually composed (agents/cockpit_awareness.py reads the same).
from services.primitives.registry import FREDDIE_PRIMITIVES  # noqa: E402

_fp_names = {t.get("name") for t in FREDDIE_PRIMITIVES if isinstance(t, dict)} or {
    str(t) for t in FREDDIE_PRIMITIVES
}
check("4c the steward's surface holds no platform tool (no principal present)",
      bool(_fp_names) and not any(str(n).startswith("platform_") for n in _fp_names),
      str(sorted(map(str, _fp_names)))[:160])

# ═════════════════════════════════════════════════════════════════════════════
print("§5 payload · allowlist · prose — one turn fact, three consumers")
# ═════════════════════════════════════════════════════════════════════════════

_lr_src = (API / "services" / "lane_runner.py").read_text()
_lr_tree = ast.parse(_lr_src)


def _fn(name):
    return next(n for n in ast.walk(_lr_tree)
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                and n.name == name)


for variant in ("run_lane_turn", "run_lane_turn_stream"):
    body = _fn(variant)
    src = ast.unparse(body)
    check(f"5a {variant}: tools + allowlist both derive from turn_has_reach",
          "turn_has_reach(app, artifact_path, derive_recipe)" in src
          and "lane_tools_openai(_reach)" in src
          and "lane_tool_names(_reach)" in src)

_blc = _fn("build_lane_conventions")
_reach_ifs = [n for n in ast.walk(_blc) if isinstance(n, ast.If)
              and any(isinstance(x, ast.Name) and x.id == "_reach"
                      for x in ast.walk(n.test))]


def _assigns_reach_section(nodes) -> bool:
    return any(isinstance(x, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == "connector_reach_section"
                       for t in x.targets)
               for stmt in nodes for x in ast.walk(stmt))


check("5b the frame prose branches on the SAME fact, both directions stated "
      "affirmatively (ADR-535 D3 held with the flag on or off)",
      _reach_ifs and any(
          _assigns_reach_section(i.body) and _assigns_reach_section(i.orelse)
          for i in _reach_ifs))
check("5c the frame template carries the slot (no orphaned prose)",
      "{connector_reach_section}" in _lr_src
      and "There is no tool here that opens" not in
      _lr_src.split("_CONVENTIONS_FRAME = ")[1].split('"""')[1])

n = PASS + FAIL
print(f"\n{PASS}/{n} ADR-585 assertions pass")
sys.exit(0 if FAIL == 0 else 1)

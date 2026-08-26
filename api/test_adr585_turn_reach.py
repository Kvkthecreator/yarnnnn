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
import re
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
    resolve_turn_reach,
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

# ADR-612 D6 — `turn_has_reach` is deleted; `resolve_turn_reach` answers both
# halves from one lookup. These checks keep their INTENT (the cut line: an app
# binding does not reach BY DEFAULT) and are re-anchored to the live function.
# `_reach_only` drives it with no agent, which is the shape-only question the
# old function asked.
def _reach_only(app, artifact_path, derive_recipe, agent=None):
    return resolve_turn_reach(None, "u", None, app=app,
                              artifact_path=artifact_path,
                              derive_recipe=derive_recipe, agent=agent)[0]


check("3a flag OFF → no reach even for the open chat turn",
      not _reach_only(None, None, None))

os.environ["TURN_REACH_ENABLED"] = "true"
try:
    check("3b flag ON + open chat turn → reach",
          _reach_only(None, None, None))
    check("3c an app binding does not reach BY DEFAULT (unscoped)",
          not _reach_only("docs", None, None))
    check("3d a bound artifact does not reach BY DEFAULT (Studio is an app surface)",
          not _reach_only(None, "Documents/deck.html", None))
    check("3e a derive recipe does not reach BY DEFAULT",
          not _reach_only(None, None, "context-brief"))
    # ADR-612 D5 — the cut line MOVED, and the move is default-closed: a desk
    # turn with an agent but NO recorded opt-in still does not reach. Only an
    # explicit member scoping unlocks it (proven in test_adr612 against a real
    # store; here the client is None, so the lookup fails closed — which is
    # itself the property worth pinning: a broken lookup grants nothing).
    check("3f D5: a desk turn with an agent but no opt-in still does not reach",
          not _reach_only("text", "Documents/x.md", None, agent="editor"))
    check("3g D5: a failed opt-in lookup grants no desk reach (fails closed)",
          not _reach_only("slides", "d.html", None, agent="editor"))
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
    # Re-anchored 2026-08-26 (ADR-612 D3, then D6): both consumers still derive from the
    # SAME `_reach` fact — that is the D4 invariant — but they now also carry
    # the per-being platform narrowing, resolved ONCE beside it. Pinning the
    # bare `(_reach)` spelling would have pinned the un-narrowed call and read
    # a correct addition as a regression. Assert the SHARED ARGUMENT, not the
    # arity: `_reach` must reach both, and any extra argument must reach both
    # too (a narrowing applied to the payload but not the allowlist is exactly
    # the declared-but-undispatchable bug this section exists to prevent).
    _payload = re.search(r"lane_tools_openai\(([^)]*)\)", src)
    _allow = re.search(r"lane_tool_names\(([^)]*)\)", src)
    check(f"5a {variant}: tools + allowlist both derive from ONE reach resolution",
          "resolve_turn_reach(" in src
          and _payload is not None and _allow is not None
          and _payload.group(1).strip().startswith("_reach")
          and _allow.group(1).strip().startswith("_reach"))
    check(f"5a {variant}: payload and allowlist take the SAME arguments",
          _payload is not None and _allow is not None
          and _payload.group(1).strip() == _allow.group(1).strip(),
          f"payload=({_payload.group(1) if _payload else '?'}) "
          f"allowlist=({_allow.group(1) if _allow else '?'})")

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

# ═════════════════════════════════════════════════════════════════════════════
print("§6 D5 — the engine disclosure, on the consent surface")
# ═════════════════════════════════════════════════════════════════════════════

# D5: turn reach sends connection content into a member-chosen engine, so the
# consent surface must SAY so. The row is flag-derived, so the disclosure must
# appear exactly when the capability does — and never while it is dormant.
import importlib  # noqa: E402

import services.connectors as _conn  # noqa: E402


def _chat_row(flag: bool) -> str:
    if flag:
        os.environ["TURN_REACH_ENABLED"] = "1"
    else:
        os.environ.pop("TURN_REACH_ENABLED", None)
    import services.turn_reach as _tr
    importlib.reload(_tr)
    importlib.reload(_conn)
    return (_conn.connector_does("notion") or {}).get("chat", "")


_off = _chat_row(False)
_on = _chat_row(True)
os.environ.pop("TURN_REACH_ENABLED", None)
importlib.reload(_conn)

# The disclosure is a CLAIM about where content goes, so anchor on the claim's
# two load-bearing halves (destination + the pasting comparison that makes the
# exposure legible), never on the full sentence's spelling.
check("6a reach ON: the row names the engine as the destination",
      "engine" in _on.lower() and "you picked" in _on.lower(), _on)
check("6b reach ON: the exposure is stated in the member's terms (pasting)",
      "pasting" in _on.lower(), _on)
check("6c reach OFF: no disclosure — nothing to disclose while dormant",
      "engine" not in _off.lower() and "cannot reach" in _off.lower(), _off)
check("6d the disclosure rides the SAME flag as the capability "
      "(one derivation, never a hand-kept copy)",
      _on != _off and bool(_on) and bool(_off))

n = PASS + FAIL
print(f"\n{PASS}/{n} ADR-585 assertions pass")
sys.exit(0 if FAIL == 0 else 1)

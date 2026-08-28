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

# ADR-615 — the default INVERTED. Unset means ON, so every workspace carries
# the capability; the variable survives only as a deliberate OFF switch. Both
# directions are pinned: an unset env must not darken a workspace, and an
# explicit falsey value must still darken a deployment.
check("1a the flag defaults ON when unset (ADR-615)", is_turn_reach_enabled())
for _falsey in ("0", "false", "no", "off", "FALSE", " Off "):
    os.environ["TURN_REACH_ENABLED"] = _falsey
    import importlib as _il
    import services.turn_reach as _trm
    _il.reload(_trm)
    check(f"1a-off {_falsey!r} darkens the deployment",
          not _trm.is_turn_reach_enabled())
# A typo must read as ON, never silently strip a capability every workspace
# is meant to have — the inverse of the old default, and why this is not a
# plain truthiness check.
os.environ["TURN_REACH_ENABLED"] = "ttrue"
import importlib as _il
import services.turn_reach as _trm
_il.reload(_trm)
check("1a-typo an unrecognised value reads as ON, not OFF",
      _trm.is_turn_reach_enabled())
os.environ.pop("TURN_REACH_ENABLED", None)
_il.reload(_trm)

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
print("§3 reach follows the PRINCIPAL, not the surface (ADR-615)")
# ═════════════════════════════════════════════════════════════════════════════

# ADR-615 amends ADR-612 D5. The pre-615 cut line asked the turn's SHAPE
# (app / artifact_path / derive_recipe) and gave a desk turn no reach without
# an explicit opt-in. That distinction did not survive inspection: a desk turn
# and an open chat turn are the SAME principal, embodied identically
# (`member:{user_id} via {model}`), resolving grants against the same
# principal_id. So the shape parameters are DELETED from the signature, not
# kept and ignored — the check below is what makes that structural rather than
# conventional.
import inspect as _inspect  # noqa: E402

_sig = _inspect.signature(resolve_turn_reach)
check("3a the turn's SHAPE no longer enters the decision (params deleted)",
      not ({"app", "artifact_path", "derive_recipe"} & set(_sig.parameters)),
      f"stale shape params: {sorted(set(_sig.parameters))}")


def _reach_only(agent=None, client=None, ws=None):
    return resolve_turn_reach(client, "u", ws, agent=agent)[0]


os.environ["TURN_REACH_ENABLED"] = "0"
try:
    check("3b the OFF switch darkens every surface",
          not _reach_only() and not _reach_only(agent="editor"))
finally:
    os.environ.pop("TURN_REACH_ENABLED", None)

# Unset = ON (ADR-615). No env manipulation here: the DEFAULT is the contract.
check("3c open chat reaches", _reach_only())
check("3d a desk turn reaches too — same principal, same grant",
      _reach_only(agent="editor"))
check("3e every desk reaches identically (no per-surface answer)",
      _reach_only(agent="editor") == _reach_only(agent="supervisor")
      == _reach_only())

# The failure mode this replaces: a lookup that cannot read the opt-in store
# must degrade to "no opt-in recorded" (everything GRANTED), never to a scope
# the member did not set. It cannot over-grant: `allowed_platforms` intersects
# against actually-connected platforms downstream.
check("3f a failed opt-in lookup degrades to 'not scoped', not to a scope",
      resolve_turn_reach(None, "u", None, agent="editor") == (True, None))

# ⚠️ REGRESSION GUARD. If the pre-615 default-closed behaviour returns — by a
# revert, or by someone re-deriving reach from the turn's shape — a desk turn
# stops reaching while open chat still does. That asymmetry IS the defect, so
# it is asserted as an asymmetry rather than as two separate facts.
check("3g REGRESSION: desk and chat never disagree about reach",
      _reach_only(agent="editor") == _reach_only(),
      "a desk turn answered differently from open chat — the pre-615 cut line")

# The member's own narrowing still applies, and is the ONLY thing that does.
# Driven against a stubbed store so the subtractive path is proven, not
# assumed (the D3 states live in test_adr612 against the real store).
import services.lane_runner as _lr  # noqa: E402
import services.agent_connectors as _ac  # noqa: E402
import services.workspace_context as _wc  # noqa: E402

_orig_opt, _orig_ws = _ac.opt_in_for, _wc.effective_workspace_id
try:
    _ac.opt_in_for = lambda c, w, u, slug: {
        "editor": ["slack"], "designer": [], "supervisor": None
    }.get(slug)
    _wc.effective_workspace_id = lambda u, w: "ws-1"
    check("3h an opt-in NARROWS (subtractive, the cliff test)",
          _lr.resolve_turn_reach(object(), "u", "ws-1", agent="editor")
          == (True, ("slack",)))
    check("3i scoped-to-nothing is honoured at a desk",
          _lr.resolve_turn_reach(object(), "u", "ws-1", agent="designer")
          == (False, ()))
    check("3j absent means everything granted",
          _lr.resolve_turn_reach(object(), "u", "ws-1", agent="supervisor")
          == (True, None))
finally:
    _ac.opt_in_for, _wc.effective_workspace_id = _orig_opt, _orig_ws

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
    # ADR-615 — "off" is now an EXPLICIT falsey value, not an absent one:
    # unset means ON. Popping the var here (the pre-615 way to get the dark
    # state) would silently test the LIT state against the dark expectation.
    os.environ["TURN_REACH_ENABLED"] = "1" if flag else "0"
    import services.turn_reach as _tr
    importlib.reload(_tr)
    importlib.reload(_conn)
    return (_conn.connector_does("notion") or {}).get("chat", "")


_off = _chat_row(False)
_on = _chat_row(True)
# Restore the DEFAULT (unset = ON, ADR-615) so later sections see production
# resting state rather than a leftover override.
os.environ.pop("TURN_REACH_ENABLED", None)
importlib.reload(_tr_mod := __import__("services.turn_reach", fromlist=["x"]))
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

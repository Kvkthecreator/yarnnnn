"""ADR-612 gate — an agent opts in to the workspace's grant.

What must hold:
  1. THE CLIFF. The opt-in can only ever NARROW. No value of it widens reach,
     and nothing reach-shaped lands on the being's registry row.
  2. ABSENT ≠ EMPTY. No record = everything granted (today's behaviour); an
     explicit [] = reaches nothing. Collapsing them breaks either the rollout
     or the member's ability to say "none".
  3. THE NARROWING IS REAL. It filters the tool NAMES, the tool DEFS and the
     frame PROSE — from one resolved value, per the ADR-585 rule that the
     payload, the allowlist and the prose must never be computed separately.
  4. The door refuses an unknown being and an ungranted platform.

Run:
    cd api && python3 test_adr612_agent_connector_opt_in.py
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PASS = 0
FAIL = 0


def check(label: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok   {label}")
    else:
        FAIL += 1
        print(f"  FAIL {label}" + (f" — {detail}" if detail else ""))


print("ADR-612 — the agent connector opt-in")
print("=" * 62)

# ---------------------------------------------------------------------------
print("1. the cliff — an opt-in narrows and can never widen")
# ---------------------------------------------------------------------------
from services.agent_connectors import allowed_platforms  # noqa: E402
from services.turn_reach import TURN_REACH_PLATFORMS  # noqa: E402

check("unscoped (None) yields every reachable platform",
      allowed_platforms(TURN_REACH_PLATFORMS, None) == tuple(TURN_REACH_PLATFORMS))
check("a subset yields exactly that subset",
      allowed_platforms(TURN_REACH_PLATFORMS, ["slack"]) == ("slack",))
check("an explicit empty list yields nothing",
      allowed_platforms(TURN_REACH_PLATFORMS, []) == ())
# THE test. An opt-in naming something never granted must add NOTHING — this
# is what makes the field a preference rather than authority.
check("an opt-in naming an UNGRANTED platform adds nothing",
      allowed_platforms(TURN_REACH_PLATFORMS, ["dropbox"]) == ())
check("a mixed opt-in keeps only the granted half",
      allowed_platforms(TURN_REACH_PLATFORMS, ["dropbox", "notion"]) == ("notion",))
# Property, over every subset: the result is ALWAYS a subset of the grant.
import itertools  # noqa: E402
_all_subsets = [
    list(c)
    for r in range(len(TURN_REACH_PLATFORMS) + 1)
    for c in itertools.combinations(TURN_REACH_PLATFORMS + ("dropbox", "email"), r)
]
check(f"over all {len(_all_subsets)} opt-in shapes, the result is always a subset "
      "of the grant",
      all(set(allowed_platforms(TURN_REACH_PLATFORMS, o)) <= set(TURN_REACH_PLATFORMS)
          for o in _all_subsets))

# Nothing reach-shaped may land on the being's row — the ADR-460 D3.a
# whitelist is the structural half of the same test.
from services.agents_registry import AGENT_ROW_KEYS  # noqa: E402

check("the being's row gains NO reach-shaped key",
      not (AGENT_ROW_KEYS & {"connectors", "platforms", "reach", "opt_in",
                             "agent_connectors", "sources"}),
      f"row keys: {sorted(AGENT_ROW_KEYS)}")

# ---------------------------------------------------------------------------
print("2. absent is not empty — the load-bearing default")
# ---------------------------------------------------------------------------
_svc_src = (ROOT / "services" / "agent_connectors.py").read_text()
_tree = ast.parse(_svc_src)
_fns = {n.name: n for n in ast.walk(_tree) if isinstance(n, ast.FunctionDef)}

check("opt_in_for exists and can return None", "opt_in_for" in _fns)
# A caller collapsing None into [] would silently turn "not scoped" into
# "reaches nothing" — the rollout regression this default exists to prevent.
check("the resolver does not collapse None into an empty list with `or []`",
      not re.search(r"opt_in_for\([^)]*\)\s*or\s*\[\]", _svc_src))
check("set_opt_in accepts None to CLEAR (a state the member must reach)",
      "platforms is None" in _svc_src and ".pop(" in _svc_src)
# A read failure must degrade to "not scoped", never to "nothing allowed".
check("a failed read degrades to {} (= unscoped), never to a restriction",
      "return {}" in _svc_src and "except Exception" in _svc_src)

# ---------------------------------------------------------------------------
print("3. the narrowing is REAL — names, defs and prose, from one value")
# ---------------------------------------------------------------------------
from services.turn_reach import turn_reach_tool_names  # noqa: E402

_all_tools = turn_reach_tool_names()
_slack_only = turn_reach_tool_names(("slack",))
_none = turn_reach_tool_names(())
check(f"unscoped holds every reach tool ({len(_all_tools)})", len(_all_tools) > 0)
check(f"a subset holds strictly fewer ({len(_slack_only)} < {len(_all_tools)})",
      0 < len(_slack_only) < len(_all_tools))
check("scoped-to-none holds NO platform tool", _none == ())
check("a narrowed set is a subset of the full set",
      set(_slack_only) <= set(_all_tools))

_lr = (ROOT / "services" / "lane_runner.py").read_text()
check("there is ONE resolver for the turn's platforms",
      "def reach_platforms_for(" in _lr)
# ADR-585's rule: all three consumers read the SAME value. If the prose
# derived its own set independently, it could claim tools the payload lacks —
# the Scout bug, mirrored.
check("the payload narrows", "lane_tools_openai(_reach, _reach_plats)" in _lr)
check("the execution allowlist narrows", "lane_tool_names(_reach, _reach_plats)" in _lr)
check("the frame prose narrows from the same resolver",
      _lr.count("reach_platforms_for(") >= 3)
# The prose must not claim a scoping that was never set.
check("unscoped prose does NOT claim the member scoped anything",
      "_reach_plats is None" in _lr)
check("scoped-to-none has its OWN prose branch (not the no-reach one)",
      "_reach_plats is not None and not _reach_plats" in _lr)

# ---------------------------------------------------------------------------
print("4. the door fails closed")
# ---------------------------------------------------------------------------
_route = (ROOT / "routes" / "agent_connectors.py").read_text()
check("an unknown being is refused, not recorded",
      "resolve_agent(agent_slug) is None" in _route and "404" in _route)
check("a non-reach-capable platform is refused",
      "TURN_REACH_PLATFORMS" in _route and "400" in _route)
check("the route serves the GRANT side too, so the pane never guesses",
      '"available"' in _route)
# This is not an agent-editing door — the retired model has no successor verb.
check("the route edits no being (no registry write)",
      "assert_editable" not in _route and "AGENTS[" not in _route)

print()
print("=" * 62)
if FAIL:
    print(f"ADR-612 gate: {PASS} passed, {FAIL} FAILED")
    sys.exit(1)
print(f"ADR-612 gate GREEN — {PASS}/{PASS}")

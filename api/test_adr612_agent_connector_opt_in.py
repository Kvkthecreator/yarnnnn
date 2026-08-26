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
check("there is ONE resolver for the turn's reach AND its platforms",
      "def resolve_turn_reach(" in _lr)
# ADR-585's rule: all three consumers read the SAME value. If the prose
# derived its own set independently, it could claim tools the payload lacks —
# the Scout bug, mirrored.
check("the payload narrows", "lane_tools_openai(_reach, _reach_plats)" in _lr)
check("the execution allowlist narrows", "lane_tool_names(_reach, _reach_plats)" in _lr)
check("all three consumers derive from the same resolver (payload, allowlist, prose)",
      _lr.count("resolve_turn_reach(") >= 4)
# The prose must not claim a scoping that was never set.
check("unscoped prose does NOT claim the member scoped anything",
      "_reach_plats is None" in _lr)
check("scoped-to-none has its OWN prose branch (not the no-reach one)",
      "_reach_plats is not None and not _reach_plats" in _lr)

# ---------------------------------------------------------------------------
print("5. D5 — the opt-in UNLOCKS a desk turn, default-closed")
# ---------------------------------------------------------------------------
import os  # noqa: E402
from services.lane_runner import resolve_turn_reach  # noqa: E402

_lr_src = (ROOT / "services" / "lane_runner.py").read_text()

# D6 — one function, not two answering the same question.
check("`turn_has_reach` is DELETED, not kept beside its successor",
      "def turn_has_reach(" not in _lr_src)
check("resolve_turn_reach returns BOTH halves from one lookup",
      "def resolve_turn_reach(" in _lr_src
      and "tuple[bool, Optional[tuple]]" in _lr_src)

os.environ["TURN_REACH_ENABLED"] = "true"
try:
    def _r(app, art, rec, agent=None, client=None):
        return resolve_turn_reach(client, "u", None, app=app,
                                  artifact_path=art, derive_recipe=rec,
                                  agent=agent)

    # Default-closed is the whole safety property of D5: unlocking must
    # require an explicit member act, never merely naming an agent.
    check("a desk turn with an agent but NO opt-in does not reach",
          _r("text", "/w/x.md", None, agent="editor")[0] is False)
    check("open chat still reaches with no opt-in (ADR-585 D1 unchanged)",
          _r(None, None, None)[0] is True)
    # A lookup that RAISES must not grant reach — fails toward the pre-D5
    # world, never toward reach the member did not scope.
    #
    # ⭐ This drives the exception path for real. The first version passed
    # `client=None` and asserted False — but `effective_workspace_id` returns
    # None there, so the lookup was SKIPPED and the handler never ran: the
    # check passed for the wrong reason, and a break that made the handler
    # grant reach went undetected (falsifier F2). A raising double, plus a
    # patched workspace resolver, is the only way the branch is observed.
    # Patch on the MODULES the resolver imports from — it does its imports
    # inside the function, so it re-reads the module attribute each call
    # (patching a local alias would silently miss, which is a second way this
    # check can pass without observing anything).
    import services.workspace_context as _wc
    import services.agent_connectors as _ac

    class _Boom:
        def table(self, *a, **k):
            raise RuntimeError("connection lost")

    def _raiser(*a, **k):
        raise RuntimeError("opt-in store unavailable")

    _real_eff = _wc.effective_workspace_id
    _real_opt = _ac.opt_in_for
    _wc.effective_workspace_id = lambda *a, **k: "ws-1"
    _ac.opt_in_for = _raiser
    try:
        _raised = _r("slides", "/w/d.html", None, agent="editor", client=_Boom())
        check("a RAISING opt-in lookup grants NO desk reach (fails closed)",
              _raised[0] is False and _raised[1] is None,
              f"got {_raised}")
        # ...and open chat still works when the lookup dies: a broken store
        # must not take away reach the member already had.
        check("a raising lookup leaves open chat's reach intact",
              _r(None, None, None, agent="editor", client=_Boom())[0] is True)
    finally:
        _wc.effective_workspace_id = _real_eff
        _ac.opt_in_for = _real_opt
finally:
    os.environ.pop("TURN_REACH_ENABLED", None)

# The unattended standing path must remain structurally unreachable: a scoped
# being does not gain live credential reach in its cron-fired runs. That is a
# clock PLUS a credential, which ADR-596 D2 houses on grants, not here.
_derive_src = (ROOT / "services" / "derive_turn.py").read_text()
check("the standing/derive path is toolless by construction",
      "No tools" in _derive_src
      and "lane_tools_openai" not in _derive_src)
_strings_src = (ROOT / "services" / "strings.py").read_text()
check("a strings run goes through the toolless derive path, not the lane",
      "run_bounded_derive_turn" in _strings_src
      and "lane_tools_openai" not in _strings_src)

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

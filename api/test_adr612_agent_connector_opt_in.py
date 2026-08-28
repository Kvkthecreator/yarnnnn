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
print("4b. the opt-in READS under the turn's own client (RLS reality)")
# ---------------------------------------------------------------------------
# ⭐⭐⭐ FOUND BY DRIVING, NOT BY READING. `member_state` is service-role-only
# (migration 202), so under a USER client the select returns ZERO ROWS — not an
# error. `opt_in_for` then reports "absent", which since ADR-615 means
# EVERYTHING GRANTED. Observed live: an Editor scoped to NO connections still
# fetched a GitHub README, because `lane_runner` hands the turn's `auth.client`.
#
# Pre-615 this was INVISIBLE — absent meant "no desk reach", so the wrong
# client failed CLOSED and looked correct. Flipping the default is what turned
# a latent wrong-client bug into an open door, which is why this gate belongs
# with the default, not with the store.
#
# The assertion is behavioural: the SAME recorded opt-in must resolve the same
# way through a non-service client as through a service one. A source check
# ("does it call get_service_client") would pass against a version that called
# it and then discarded the result.
import services.agent_connectors as _ac_rls  # noqa: E402


class _RlsBlindClient:
    """A client whose select is silently filtered to zero rows — exactly what
    a user-role client does against a service-role-only table. NOT an error:
    that is the whole trap."""

    def table(self, _name):
        return self

    def select(self, *_a, **_k):
        return self

    def eq(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def execute(self):
        from types import SimpleNamespace
        return SimpleNamespace(data=[])


_recorded = {"editor": [], "supervisor": ["github"]}
_svc_calls = []


class _FakeSvc:
    def table(self, _name):
        return self

    def select(self, *_a, **_k):
        return self

    def eq(self, *_a, **_k):
        return self

    def limit(self, *_a, **_k):
        return self

    def execute(self):
        from types import SimpleNamespace
        _svc_calls.append(1)
        return SimpleNamespace(data=[{"value": _recorded}])


import services.supabase as _sb  # noqa: E402

_real_get_svc = _sb.get_service_client
_sb.get_service_client = lambda *a, **k: _FakeSvc()
try:
    _blind = _ac_rls.opt_in_for(_RlsBlindClient(), "ws-1", "p-1", "editor")
    check("an RLS-blind caller still reads the RECORDED opt-in (not 'absent')",
          _blind == [], f"got {_blind!r} — expected [] (scoped to nothing)")
    check("the reader reached the service client, not the caller's",
          len(_svc_calls) >= 1)
    # The discriminating case: [] and None must not be confused here, because
    # [] means "reaches nothing" and None means "reaches everything".
    _sup = _ac_rls.opt_in_for(_RlsBlindClient(), "ws-1", "p-1", "supervisor")
    check("a scoped being reads its real subset through an RLS-blind caller",
          _sup == ["github"], f"got {_sup!r}")
    _absent = _ac_rls.opt_in_for(_RlsBlindClient(), "ws-1", "p-1", "nobody")
    check("a genuinely unscoped being still reads as None (absent)",
          _absent is None, f"got {_absent!r}")
finally:
    _sb.get_service_client = _real_get_svc

# ---------------------------------------------------------------------------
print("5. D5 (as amended by ADR-615) — reach follows the principal; the opt-in NARROWS")
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
    # ADR-615 — the turn's SHAPE no longer enters the decision, so `_r` takes
    # only what still matters. The old positional shape args are gone from the
    # signature entirely (asserted in test_adr585 §3a).
    def _r(agent=None, client=None):
        return resolve_turn_reach(client, "u", None, agent=agent)

    # ⭐ AMENDED BY ADR-615. D5 made a desk turn default-CLOSED; 615 found that
    # rested on a surface/permission conflation — a desk turn and an open chat
    # turn are the SAME principal (`member:{id} via {model}`), resolving the
    # same grants. So absence means everything granted at BOTH, and the opt-in
    # is purely subtractive. What D5 was protecting is protected structurally
    # instead: unattended runs are toolless (asserted below).
    check("a desk turn with no opt-in reaches — same principal as chat",
          _r(agent="editor")[0] is True)
    check("open chat still reaches with no opt-in (ADR-585 D1 unchanged)",
          _r()[0] is True)
    check("desk and chat never disagree (the pre-615 asymmetry is the defect)",
          _r(agent="editor") == _r())
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
        # ADR-615: "fails closed" now means fails to NOT-SCOPED — the same
        # state as a member who never scoped this being. It cannot over-grant:
        # `allowed_platforms` intersects against actually-connected platforms
        # downstream, so absence never exceeds the workspace's own grant. The
        # property still worth pinning is that a broken store never invents a
        # SCOPE the member did not set.
        _raised = _r(agent="editor", client=_Boom())
        check("a RAISING opt-in lookup invents no scope (degrades to unscoped)",
              _raised == (True, None), f"got {_raised}")
        check("a raising lookup leaves open chat's reach intact",
              _r(agent="editor", client=_Boom())[0] is True)
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
print("6. the control reads as a toggle, not as deleted text")
# ---------------------------------------------------------------------------
_surface = (ROOT.parent / "web" / "components" / "agents" / "AgentsSurface.tsx").read_text()
# Observed in the click-pass: an un-selected platform rendered STRUCK THROUGH,
# which reads as "removed" rather than "available but off" — and the plain
# button carried no pressed state at all, so assistive tech could not tell on
# from off.
check("an un-selected platform is not rendered as struck-through text",
      "line-through" not in _surface)
check("the control carries switch semantics (state reaches assistive tech)",
      'role="switch"' in _surface and "aria-checked=" in _surface)

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

"""Unit gate for the steward-shaped perception envelope (2026-06-30 re-scope).

The perception-envelope-completeness finding (docs/evaluations/2026-06-30-
perception-envelope-completeness-FINDING.md) + its analysis (docs/analysis/
perception-and-the-principal-commons-first-principles-2026-06-30.md) found that
the steward's wake envelope carried only ONE perception slice (the attribution
fact) — no principal roster, no peripheral health. The attribution catch kept
missing because `authored_by: operator` was a bare string with no REFERENT.

This gate locks the two facts the re-scope adds:
  - principal_commons_fact: WHO may write (principal_grants roster) + who DID
    recently (authored_by GROUP-BY) — the referent for the attribution check.
  - peripheral_field_fact: connection + source HEALTH — the substrate the
    connection-hygiene duty needs.

It also locks: the render headers wire both facts in; the principal-vs-peripheral
distinction is carried in the prose; the shared roster helper (services.principals)
is the SAME one the Workspace Members route uses (Singular Implementation).

Pure offline: stub clients + monkeypatched roster/watch reads. No LLM, no DB.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_API_ROOT = Path(__file__).resolve().parent
if str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

PASSED = 0
FAILED = 0


def check(cond: bool, label: str) -> None:
    global PASSED, FAILED
    if cond:
        print(f"  ✓ {label}")
        PASSED += 1
    else:
        print(f"  ✗ {label}")
        FAILED += 1


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# --------------------------------------------------------------------------
# Stub client supporting workspace_file_versions + platform_connections
# --------------------------------------------------------------------------
class _Result:
    def __init__(self, data):
        self.data = data


class _Query:
    def __init__(self, rows):
        self._rows = rows
        self._eq = {}
        self._gte = None
        self._limit = None

    def select(self, *_a, **_k):
        return self

    def eq(self, col, val):
        self._eq[col] = val
        return self

    def gte(self, col, val):
        self._gte = (col, val)
        return self

    def order(self, col, desc=False):
        return self

    def limit(self, n):
        self._limit = n
        return self

    def execute(self):
        rows = [r for r in self._rows if all(r.get(c) == v for c, v in self._eq.items())]
        if self._gte:
            col, val = self._gte
            rows = [r for r in rows if (r.get(col) or "") >= val]
        rows = sorted(rows, key=lambda r: r.get("created_at", ""), reverse=True)
        if self._limit is not None:
            rows = rows[: self._limit]
        return _Result(rows)


class _Client:
    def __init__(self, versions=None, connections=None):
        self._versions = versions or []
        self._connections = connections or []

    def table(self, name):
        if name == "workspace_file_versions":
            return _Query(self._versions)
        if name == "platform_connections":
            return _Query(self._connections)
        raise NotImplementedError(name)


_RECENT = "2026-06-30T06:00:00+00:00"

# Recent authorship: a human operator, a foreign LLM dumping, a system mirror.
_VERSIONS = [
    {"user_id": "u", "authored_by": "operator", "created_at": _RECENT},
    {"user_id": "u", "authored_by": "operator", "created_at": _RECENT},
    {"user_id": "u", "authored_by": "yarnnn:mcp:claude-desktop", "created_at": _RECENT},
    {"user_id": "u", "authored_by": "system:track-web-sources", "created_at": _RECENT},
]

# A multi-principal roster: owner + a foreign LLM (the kind that the seeded
# mis-attribution impersonates).
_ROSTER_MULTI = [
    {"principal_id": "u", "role": "owner", "label": None,
     "write_regions": ["governance/", "constitution/", "persona/", "operation/", "contract/"],
     "scopes_explicit": False},
    {"principal_id": "client-abc", "role": "foreign-llm", "label": "claude-desktop",
     "write_regions": ["operation/"], "scopes_explicit": False},
]

# A lone-owner roster (the N=1 bare-workspace quiet case).
_ROSTER_OWNER_ONLY = [
    {"principal_id": "u", "role": "owner", "label": None,
     "write_regions": ["governance/", "constitution/", "persona/", "operation/", "contract/"],
     "scopes_explicit": False},
]


def _patch_roster(roster):
    """Monkeypatch the shared roster loader (it reaches the real DB otherwise)."""
    import services.freddie_envelope as fe
    import services.principals as pr
    pr.load_principal_roster = lambda *a, **k: roster  # type: ignore
    # _principal_commons_fact imports it locally — re-bind on the module too if cached.
    return fe


def _patch_watches(watches):
    import services.bundle_reader as br
    br.get_watches_for_workspace = lambda *a, **k: watches  # type: ignore


# --------------------------------------------------------------------------
# Principal commons
# --------------------------------------------------------------------------
def test_principal_commons_presents_roster_and_authorship():
    print("\n[principal-commons] presents the roster + recent authorship (the referent)")
    fe = _patch_roster(_ROSTER_MULTI)
    fact = _run(fe._principal_commons_fact(_Client(versions=_VERSIONS), "u"))
    check(bool(fact.strip()), "non-empty when a foreign principal / cross-principal activity exists")
    check("the human operator" in fact, "names the OWNER as the human operator (the `operator` stamp's true author)")
    check("claude-desktop" in fact and "foreign LLM" in fact, "names the foreign-LLM principal (the kind the lie impersonates)")
    check("Recent authorship" in fact, "presents the authorship GROUP-BY")
    check("operator · 2 revisions" in fact, "counts per-principal revisions correctly")
    check("yarnnn:mcp:claude-desktop · 1 revision" in fact, "counts the foreign-LLM dump")


def test_principal_commons_silent_on_lone_owner_quiet():
    print("\n[principal-commons] silent on a quiet single-owner bare workspace (no noise)")
    fe = _patch_roster(_ROSTER_OWNER_ONLY)
    # Only the owner writing, no foreign principal → no commons to reconcile.
    quiet = [{"user_id": "u", "authored_by": "operator", "created_at": _RECENT}]
    fact = _run(fe._principal_commons_fact(_Client(versions=quiet), "u"))
    check(fact == "", "lone owner + single-author activity → empty (silent on program wakes)")


def test_principal_commons_fires_when_foreign_principal_present():
    print("\n[principal-commons] fires when a foreign principal holds a grant (even if quiet)")
    fe = _patch_roster(_ROSTER_MULTI)
    fact = _run(fe._principal_commons_fact(_Client(versions=[]), "u"))
    check(bool(fact.strip()), "non-empty when the roster carries a non-owner principal")
    check("claude-desktop" in fact, "the foreign principal is named even with no recent writes")


# --------------------------------------------------------------------------
# Peripheral field
# --------------------------------------------------------------------------
def test_peripheral_field_presents_connections_and_sources():
    print("\n[peripheral-field] presents connection + source HEALTH")
    import services.freddie_envelope as fe
    _patch_watches([{"id": "press-feed"}, {"id": "rss-2"}])
    conns = [
        {"user_id": "u", "platform": "slack", "status": "active"},
        {"user_id": "u", "platform": "trading", "status": "active"},
    ]
    fact = _run(fe._peripheral_field_fact(_Client(connections=conns), "u"))
    check("slack · status: active" in fact, "names a connection + status")
    check("trading · status: active" in fact, "names the second connection")
    check("2 declared" in fact, "presents the declared-watch count (sources)")
    check("system:" in fact or "perimeter" not in fact, "frames peripherals as system:-attributed (health, not honesty)")


def test_peripheral_field_silent_on_bare_workspace():
    print("\n[peripheral-field] silent when there is no perimeter (bare workspace)")
    import services.freddie_envelope as fe
    _patch_watches([])
    fact = _run(fe._peripheral_field_fact(_Client(connections=[]), "u"))
    check(fact == "", "no connections + no sources → empty (no noise)")


# --------------------------------------------------------------------------
# Wiring: contract fields + render headers + shared helper coherence
# --------------------------------------------------------------------------
def test_contract_and_envelope_wiring():
    print("\n[wiring] both facts are contract fields + envelope keys + rendered")
    from agents.occupant_contract import FreddieContext
    anns = FreddieContext.__annotations__
    check("principal_commons_fact" in anns, "FreddieContext declares principal_commons_fact")
    check("peripheral_field_fact" in anns, "FreddieContext declares peripheral_field_fact")

    import inspect
    import services.freddie_envelope as fe
    src = inspect.getsource(fe.load_freddie_governance_envelope)
    check('envelope["principal_commons_fact"]' in src, "envelope sets principal_commons_fact")
    check('envelope["peripheral_field_fact"]' in src, "envelope sets peripheral_field_fact")

    import agents.freddie_agent as fa
    rsrc = inspect.getsource(fa)
    # ADR-390: the three perception facts fold into ONE commons surface (mutual-
    # exclusivity). The render reads all three keys, under one header.
    check('"principal_commons_fact"' in rsrc, "commons surface reads principal_commons_fact")
    check('"peripheral_field_fact"' in rsrc, "commons surface reads peripheral_field_fact")
    check('"attribution_fact"' in rsrc, "commons surface reads attribution_fact")
    check("## The commons —" in rsrc, "the three facts render under ONE commons header (the fold)")
    check("PRINCIPAL is an intent-bearing, grant-backed" in rsrc, "commons carries the principal definition (the referent cue)")
    check("driver-class transports with no intent" in rsrc, "commons carries the peripheral definition (health-not-honesty)")
    check("check every stamp below against this roster" in rsrc.lower() or
          "check every stamp" in rsrc, "attribution detail routes the check through the roster (the catch-fix)")


def test_operation_machinery_gated_on_program_active():
    print("\n[ADR-390] operation machinery is gated on program_active (bare steward sees none)")
    import inspect
    import services.freddie_envelope as fe
    src = inspect.getsource(fe.load_freddie_governance_envelope)
    check("program_active = bool(program_decls)" in src,
          "the single program-active predicate exists (bool(program_decls))")
    check("if program_active:" in src, "machinery reads are gated behind program_active")
    # the six operation-machinery facts are read INSIDE the gate, not universally
    for fact in ("reflection_gap_fact", "schedule_index_md", "recent_execution_md",
                 "calibration_md", "expected_output_yaml", "specs_inventory"):
        # appears in the program-active branch; must NOT be in _UNIVERSAL_ENVELOPE_DECLS
        decls = inspect.getsource(fe)
        in_universal = f'("{fact}",' in decls.split("_UNIVERSAL_ENVELOPE_DECLS")[1].split("]")[0] \
            if "_UNIVERSAL_ENVELOPE_DECLS" in decls else False
        check(not in_universal, f"{fact} removed from the universal set (program-gated, single-ownership)")

    # render layer: pulse/calibration no longer emit empty-state headers
    import agents.freddie_agent as fa
    rsrc = inspect.getsource(fa)
    check("(empty — kernel mirror hasn't run yet" not in rsrc,
          "the empty-state pulse/calibration scaffolding headers are GONE (bare steward sees nothing)")


def test_route_imports_shared_helper():
    print("\n[wiring] the Workspace Members route imports the shared helper (Singular Impl)")
    import inspect
    import routes.workspace as rw
    src = inspect.getsource(rw)
    check("from services.principals import class_default_write_regions" in src,
          "route imports class_default_write_regions from services.principals (not a local copy)")
    check("def _class_default_write_regions" not in src or
          src.count("def _class_default_write_regions") == 0,
          "route no longer defines its own _class_default_write_regions")


if __name__ == "__main__":
    test_principal_commons_presents_roster_and_authorship()
    test_principal_commons_silent_on_lone_owner_quiet()
    test_principal_commons_fires_when_foreign_principal_present()
    test_peripheral_field_presents_connections_and_sources()
    test_peripheral_field_silent_on_bare_workspace()
    test_contract_and_envelope_wiring()
    test_operation_machinery_gated_on_program_active()
    test_route_imports_shared_helper()
    print(f"\n  {PASSED} passed, {FAILED} failed")
    sys.exit(1 if FAILED else 0)

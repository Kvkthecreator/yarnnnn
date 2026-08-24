"""ADR-597 — the resident follows the registration; a desk seats its own colleague.

Script-style (run: cd api && python3 test_adr597_resident_derivation.py).

What this gate holds:
  1. `_lane_agent` derives the resident from the app registration at read
     time, with the ratified precedence (app → recipe → legacy stamp → None) —
     executed against the real function, not grepped.
  2. `create_lane` no longer stamps `lane_meta["agent"]` (AST: no assignment
     to that key anywhere in the handler), and both consumption points run
     through the derivation (serve builds `agent` from `_lane_agent`; the
     turn compares against `lane_agent`).
  3. ADR-601 D1 many-to-one: an APP pins exactly ONE resident (ADR-467 D1,
     the surviving direction), and a BEING may serve several desks — sharing
     is ordinary, not an exception to excuse. ADR-597 D2's injectivity is
     retired with its named-exception list.
  4. The editor row is a well-formed being: in AGENTS, self-contained (no
     based_on), exactly AGENT_ROW_KEYS, priced engine, `offered: False` —
     its home is the Text desk (ADR-600 D2).
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

API = Path(__file__).resolve().parent
sys.path.insert(0, str(API))

FAILURES: list[str] = []


def _assert(cond: bool, msg: str) -> None:
    tag = "PASS" if cond else "FAIL"
    print(f"  [{tag}] {msg}")
    if not cond:
        FAILURES.append(msg)


def test_derivation_behavior():
    print("1. _lane_agent derives, with the ratified precedence")
    from routes.lanes import _lane_agent

    # The app registration wins over a stale stamp — the whole point.
    _assert(_lane_agent({"app": "text", "agent": "designer"}) == "editor",
            "a text desk stamped designer resolves to editor (registration wins)")
    _assert(_lane_agent({"app": "slides"}) == "designer",
            "a slides desk resolves designer with no stamp at all")
    # A pre-599 lane stamped with the RENAMED app slug: the registration is
    # gone (`studio` left the registry), so the stored stamp is the honest
    # fallback — exactly the deleted-registration path.
    _assert(_lane_agent({"app": "studio", "agent": "designer"}) == "designer",
            "a legacy studio-stamped desk falls back to its stored stamp")
    _assert(_lane_agent({"app": "strings", "agent": "designer"}) == "keeper",
            "a strings desk stamped designer resolves to keeper")
    # A registration that left the roster falls back to the stored stamp.
    _assert(_lane_agent({"app": "radar", "agent": "scout"}) == "scout",
            "a deleted app's desk falls back to the stored stamp")
    _assert(_lane_agent({"app": "radar"}) is None,
            "a deleted app's desk with no stamp resolves None (engine label — honest)")
    # Recipe lanes derive from the recipe registry.
    from services.derive_recipes import DERIVE_RECIPES
    slug = next(iter(DERIVE_RECIPES))
    want = DERIVE_RECIPES[slug].get("resident")
    _assert(_lane_agent({"derive_recipe": slug}) == want,
            f"a derive lane resolves the recipe's resident ({slug}→{want})")
    _assert(_lane_agent({}) is None, "a plain chat lane has no resident")


def test_stamp_retired_and_reads_derive():
    print("2. the stamp is retired as a write; both reads derive")
    tree = ast.parse((API / "routes" / "lanes.py").read_text())

    def _fn(name):
        return next((n for n in ast.walk(tree)
                     if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                     and n.name == name), None)

    create = _fn("create_lane")
    _assert(create is not None, "create_lane exists")
    stamps = [
        n for n in ast.walk(create) if create and isinstance(n, ast.Subscript)
        and isinstance(n.ctx, ast.Store)
        and isinstance(n.slice, ast.Constant) and n.slice.value == "agent"
    ]
    _assert(not stamps, "create_lane never assigns lane_meta[\"agent\"]")

    serve = _fn("_lane_row_to_dict")
    serve_calls = [
        n for n in ast.walk(serve) if serve and isinstance(n, ast.Call)
        and isinstance(n.func, ast.Name) and n.func.id == "_lane_agent"
    ]
    _assert(bool(serve_calls), "the serve path builds `agent` through _lane_agent")

    core = _fn("_turn_stream_response")
    _assert(core is not None, "the turn core exists")
    core_src = ast.get_source_segment((API / "routes" / "lanes.py").read_text(), core) or ""
    _assert("_lane_agent(" in core_src and "responder != lane_agent" in core_src,
            "the turn derives lane_agent and compares the responder against it")
    _assert('lane_meta.get("agent")' not in core_src,
            "the turn no longer reads the raw stamp directly")


def test_many_to_one():
    print("3. an app pins ONE resident; a being may serve MANY desks")
    import services.apps  # noqa: F401  (registration side-effect)
    from services.agents_registry import homes_for_agent, resolve_agent
    from services.authoring import all_apps

    apps = all_apps()
    # The surviving direction (ADR-467 D1): one desk, one voice. A registration
    # carries a single `resident` string, so two voices is unrepresentable —
    # asserted anyway, because the row shape is what makes it true.
    _assert(all(isinstance(a.get("resident"), str) and a["resident"]
                for a in apps.values()),
            "every app pins exactly one resident (a string, never a list)")
    _assert(all(resolve_agent(a["resident"]) is not None for a in apps.values()),
            "every app's resident resolves to a real being")

    # ADR-601 D1 — the retired direction. Sharing is ORDINARY now: `designer`
    # serves Slides and IMAGES, and a Blogger app may take `editor` beside
    # Text. The old gate treated this as an exception list to be kept from
    # growing silently; growth is now the expected case, so the gate asserts
    # the RELATION instead of policing it.
    for slug in {a["resident"] for a in apps.values()}:
        homes = homes_for_agent(slug)
        _assert(bool(homes), f"{slug} reports the desk(s) it serves: {homes}")
        _assert(all(apps[h]["resident"] == slug for h in homes),
                f"{slug}'s homes each pin it back (the relation is consistent)")
    _assert(sum(len(homes_for_agent(s)) for s in
                {a["resident"] for a in apps.values()}) == len(apps),
            "every registered app is claimed by exactly one being's home list")
    # The shape that must NOT come back: a gate naming specific pairings, which
    # would make an ordinary second desk read as a violation. Checked by AST —
    # a substring search here matches THIS check's own assertion literal (it
    # did, on the first cut), which is the a-gate-matches-its-own-text trap
    # one level deeper: not a comment this time, but the check's own code.
    import ast as _ast
    _tree = _ast.parse((API / "test_adr597_resident_derivation.py").read_text())
    _cmps = [
        n for n in _ast.walk(_tree)
        if isinstance(n, _ast.Compare)
        and isinstance(n.left, _ast.Name) and n.left.id == "exceptions"
    ]
    _assert(not _cmps,
            "no named-exception list survives (sharing is ordinary — ADR-601 D1)")


def test_editor_row():
    print("4. editor is a well-formed being")
    from services.agents_registry import AGENTS, AGENT_ROW_KEYS
    row = AGENTS.get("editor")
    _assert(row is not None, "editor is a being in the one register (ADR-600 D1)")
    _assert(row is not None and row.get("offered") is False,
            "editor is not offered — its home is the Text desk (ADR-600 D2)")
    # ADR-599 D3: residents are self-contained — the resident shape has no
    # based_on (the base operations are deleted) and no authority/reach key.
    _assert(set(row or {}) == set(AGENT_ROW_KEYS),
            "editor carries exactly AGENT_ROW_KEYS — no authority")
    # The SHIPPED pricing check, not a re-derivation — `_BILLING_RATES` keys
    # are provider-stripped, and `unpriced_lane_model` owns that mapping.
    from services.lane_runner import LANE_MODELS, unpriced_lane_model
    model = (row or {}).get("model", "")
    _assert(model in LANE_MODELS and not unpriced_lane_model(model),
            "editor's engine is routable and priced")


if __name__ == "__main__":
    test_derivation_behavior()
    test_stamp_retired_and_reads_derive()
    test_many_to_one()
    test_editor_row()
    print()
    if FAILURES:
        print(f"FAILED — {len(FAILURES)} check(s):")
        for f in FAILURES:
            print(f"  - {f}")
        sys.exit(1)
    print("ALL PASS — ADR-597 holds")

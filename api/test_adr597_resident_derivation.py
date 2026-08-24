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
  3. D2 injectivity: the user-facing desk apps each seat a DEDICATED
     colleague — studio→designer, text→editor, strings→keeper, pairwise
     distinct. The named exceptions (images, docs on designer) are asserted
     AS exceptions so silent growth of the exception list trips the gate.
  4. The editor row is a well-formed posture: in KERNEL_POSTURES, based_on
     a real base agent, exactly POSTURE_ROW_KEYS, priced engine.
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
    _assert(_lane_agent({"app": "studio"}) == "designer",
            "a studio desk resolves designer with no stamp at all")
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


def test_injectivity():
    print("3. one desk, one dedicated colleague — exceptions named, not silent")
    import services.apps  # noqa: F401  (registration side-effect)
    from services.authoring import all_apps

    residents = {slug: row["resident"] for slug, row in all_apps().items()}
    _assert(residents.get("studio") == "designer", "studio seats Designer")
    _assert(residents.get("text") == "editor", "text seats Editor")
    _assert(residents.get("strings") == "keeper", "strings seats Keeper")
    dedicated = {k: v for k, v in residents.items() if k in ("studio", "text", "strings")}
    _assert(len(set(dedicated.values())) == len(dedicated),
            "the dedicated set is pairwise distinct (injective)")

    # The KNOWN exceptions, asserted as such (ADR-597 D2): images (metered
    # pipeline — re-posturing needs its own evidence) and docs (internal,
    # awaiting the ADR-581 D5 split). A new app sharing a resident, or one of
    # these silently changing, must be a deliberate ADR edit — here.
    exceptions = {k for k, v in residents.items()
                  if k not in dedicated and v in set(residents.values())
                  and list(residents.values()).count(v) > 1}
    _assert(exceptions <= {"images", "docs"},
            f"resident-sharing stays within the named exceptions (found: {sorted(exceptions)})")


def test_editor_row():
    print("4. editor is a well-formed app resident")
    from services.agents_registry import (
        APP_RESIDENTS,
        KERNEL_AGENTS,
        POSTURE_ROW_KEYS,
    )
    row = APP_RESIDENTS.get("editor")
    _assert(row is not None,
            "editor lives in APP_RESIDENTS (a desk voice, not a colleague — ADR-598)")
    _assert(set(row or {}) == set(POSTURE_ROW_KEYS),
            "editor carries exactly POSTURE_ROW_KEYS — no authority, no reach")
    _assert((row or {}).get("based_on") in KERNEL_AGENTS,
            "editor is based on a real base operation")
    # The SHIPPED pricing check, not a re-derivation — `_BILLING_RATES` keys
    # are provider-stripped, and `unpriced_lane_model` owns that mapping.
    from services.lane_runner import LANE_MODELS, unpriced_lane_model
    model = (row or {}).get("model", "")
    _assert(model in LANE_MODELS and not unpriced_lane_model(model),
            "editor's engine is routable and priced")


if __name__ == "__main__":
    test_derivation_behavior()
    test_stamp_retired_and_reads_derive()
    test_injectivity()
    test_editor_row()
    print()
    if FAILURES:
        print(f"FAILED — {len(FAILURES)} check(s):")
        for f in FAILURES:
            print(f"  - {f}")
        sys.exit(1)
    print("ALL PASS — ADR-597 holds")

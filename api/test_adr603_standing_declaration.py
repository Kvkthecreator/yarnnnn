"""ADR-603 — the standing declaration, and the Supervisor's desk.

Script-style (run: cd api && python3 test_adr603_standing_declaration.py).

What this gate holds:

  1. THE D2 RULE: a declaration names an APP and the agent is DERIVED —
     executed against the real resolver, not grepped. An unregistered app
     resolves None (never a plausible default).
  2. NO DECLARATION KEY NAMES A BEING. The executor field is `app`; a key
     naming an agent would be authority over a being wearing a declaration's
     clothes (ADR-460 D3.a, one layer out from the registry).
  3. SUPERVISOR AUTHORS DECLARATIONS, NEVER COMMANDS BEINGS: its row is the
     same shape as every other being's, its posture names no colleague, and
     it holds no primitive that addresses one.
  4. Supervisor is NOT Freddie: no standing intent, no self-wake, no mandate,
     no autonomy dial anywhere on its row.
  5. The desk is `stage: internal` (ADR-592 — an app with a clock spends
     unattended), so it is NOT on the served roster and its resident is
     withheld from /agents, DERIVED (ADR-602 D3), with no second edit.
"""

from __future__ import annotations

import sys
from pathlib import Path

API = Path(__file__).resolve().parent
sys.path.insert(0, str(API))

FAILURES: list[str] = []


def _assert(cond: bool, msg: str) -> None:
    print(f"  [{'PASS' if cond else 'FAIL'}] {msg}")
    if not cond:
        FAILURES.append(msg)


def test_the_rule():
    print("1. a declaration names the APP; the agent is derived (D2)")
    import services.apps  # noqa: F401  (registration side-effect)
    from services.standing_declarations import resident_for_declaration
    from services.authoring import all_apps

    apps = all_apps()
    for slug, row in sorted(apps.items()):
        _assert(resident_for_declaration(slug) == row["resident"],
                f"a declaration on '{slug}' derives {row['resident']}")
    _assert(resident_for_declaration("no-such-app") is None,
            "an unregistered app resolves None, never a plausible default")
    _assert(resident_for_declaration(None) is None, "no app named → no executor")
    # The dividend: a re-pairing must follow every declaration with no data
    # move. `slides` re-pointed to editor in ADR-602 and this proves it reaches
    # declarations too, rather than each carrying a frozen agent slug.
    _assert(resident_for_declaration("slides") == resident_for_declaration("text"),
            "a re-paired app carries its declarations with it (ADR-602's dividend)")


def test_no_key_names_a_being():
    print("2. no declaration key names a being (the cliff, one layer out)")
    from services.standing_declarations import DECLARATION_KEYS
    from services.agents_registry import AGENTS

    _assert("app" in DECLARATION_KEYS, "the executor field is `app`")
    for banned in ("agent", "resident", "colleague", "assignee", "who"):
        _assert(banned not in DECLARATION_KEYS,
                f"no `{banned}` key — an executor is an APP, never a being")
    # And no key may be spelled as a live being's slug.
    _assert(not (DECLARATION_KEYS & set(AGENTS)),
            "no declaration key is a being's slug")


def test_supervisor_row():
    print("3. Supervisor authors declarations; it never commands beings")
    from services.agents_registry import AGENTS, AGENT_ROW_KEYS

    row = AGENTS.get("supervisor")
    _assert(row is not None, "supervisor is a being in the one register")
    _assert(set(row or {}) == set(AGENT_ROW_KEYS),
            "supervisor carries EXACTLY the same keys as every other being")
    posture = (row or {}).get("posture", "").lower()
    # It must not name a colleague: a posture that says "ask Editor" is a
    # command relation in prose, which is the D3.a breach the row shape
    # cannot express but the CHARACTER could smuggle in.
    for other in set(AGENTS) - {"supervisor"}:
        _assert(other not in posture,
                f"supervisor's posture never names '{other}'")
    _assert("do not do the work yourself" in posture
            and "do not instruct" in posture,
            "the posture STATES that it neither works nor instructs")
    # ADR-603 D3 — not Freddie. Normalised: the first cut spelled
    # "standing intent" with a space and PASSED against a real
    # `standing_intent` KEY (falsifier F4) — the underscore slipped straight
    # through. Both spellings collapse to one before matching.
    _norm = str(row).lower().replace("_", " ")
    for freddie_ish in ("standing intent", "wake", "mandate", "autonomy",
                        "self fire", "own initiative"):
        _assert(freddie_ish not in _norm,
                f"supervisor carries no '{freddie_ish}' (it is not Freddie)")


def test_desk_is_internal():
    print("4. the desk is internal, and its resident is withheld — DERIVED")
    import services.apps  # noqa: F401
    from services.agents_registry import homes_for_agent, is_promoted, resolve_agent
    from services.app_stage import is_exposed, resolve_stage
    from services.kernel_surfaces import KERNEL_SURFACES
    from services.authoring import resident_for_app

    _assert(resident_for_app("supervisor") == "supervisor",
            "the app seats its own resident")
    _assert(homes_for_agent("supervisor") == ["supervisor"],
            "supervisor's only desk is its own")
    rows = [e for e in KERNEL_SURFACES if e.get("slug") == "supervisor"]
    _assert(len(rows) == 1, "the surface row exists exactly once")
    _assert(resolve_stage(rows[0]) == "internal" and not is_exposed(rows[0]),
            "the desk is internal — NOT on the served roster (ADR-592)")
    _assert(not is_promoted("supervisor"),
            "its resident is withheld from /agents, derived from the desk")
    # Withheld from the PANE, never from resolution — a resident must resolve
    # for its own lanes to run (the ADR-602 D3 asymmetry).
    _assert(resolve_agent("supervisor") is not None,
            "withheld from the pane never means unresolvable")
    import routes.lanes as L
    _assert("supervisor" not in {b["slug"] for b in L._beings_payload()},
            "the payload withholds it while the desk is internal")


if __name__ == "__main__":
    test_the_rule()
    test_no_key_names_a_being()
    test_supervisor_row()
    test_desk_is_internal()
    print()
    if FAILURES:
        print(f"FAILED — {len(FAILURES)} check(s):")
        for f in FAILURES:
            print(f"  - {f}")
        sys.exit(1)
    print("ALL PASS — ADR-603 holds")

"""ADR-636 — an app declares itself once on each side of the wire.

WHAT THIS GATE IS FOR
The backend derives every app/agent fact from one declaration each (ADR-562
`register_app`, ADR-592 `stage`, ADR-600 `AGENTS`). The FRONTEND re-declared
each app by hand, and nothing checked the copies against the source. At
`7ed27fb` they AGREED — which is precisely the danger: the agreement was held
by memory, and the checks that existed over those sites were NEGATIVE
("APP_SURFACES no longer claims docs"). A negative check catches a forgotten
DELETION. It cannot, by construction, catch a forgotten ADDITION.

So this gate asserts the RELATION, in BOTH directions, with `all_apps()` and
`AGENTS` as the source of truth. Its load-bearing assertion is the one nothing
previously made: **every registered app has a client descriptor row.**

⭐ FALSIFY BOTH WAYS BEFORE TRUSTING IT. A parity gate that has only ever run
green is indistinguishable from one that parses nothing (the ADR-630 lesson: a
ceiling that was gated but never enforced; the ADR-592 lesson: a field that sat
inert for five days because it was back-derived from what it replaced). The
parse-non-empty checks below exist so a rename that silently empties a regex
fails LOUDLY here rather than passing vacuously.

Run: cd api && python3 test_adr636_app_declaration_parity.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

API = Path(__file__).parent
WEB = API.parent / "web"

_passed = 0
_failed = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global _passed, _failed
    if ok:
        _passed += 1
        print(f"  ok   {label}")
    else:
        _failed += 1
        print(f"  FAIL {label}" + (f" — {detail}" if detail else ""))


def read(rel: str) -> str:
    return (WEB / rel).read_text()


def code_only(src: str) -> str:
    """Strip comments — a slug named in prose is not a declaration.

    Without this, "// 'docs' — removed 2026-08-17" reads as a live entry and
    every diff below reports phantom rows. (Confirmed the hard way while
    driving this ADR: the first sweep reported `docs` + `radar` in the Dock
    default, and both were commented-out gravestones.)
    """
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    return "\n".join(l for l in src.split("\n") if not l.strip().startswith("//"))


# ---------------------------------------------------------------------------
# The source of truth
# ---------------------------------------------------------------------------
import services.apps  # noqa: F401,E402  (registration side-effect — ADR-562)
from services.agents_registry import AGENTS  # noqa: E402
from services.authoring import all_apps  # noqa: E402

REGISTERED = set(all_apps())


# ---------------------------------------------------------------------------
# [1] Every registered app has a client descriptor — THE ADDITION CASE
# ---------------------------------------------------------------------------
def test_descriptor_parity() -> None:
    print("\n[1] app descriptors == registered apps (both directions)")
    src = code_only(read("lib/apps/registry.ts"))
    block = src.split("APP_DESCRIPTORS: Record<string, AppDescriptor> = {", 1)
    check("APP_DESCRIPTORS parses (guards a silent no-op scan)", len(block) == 2)
    if len(block) != 2:
        return
    body = block[1]
    declared = set(re.findall(r"^\s{2}([a-z][a-z0-9-]*):\s*\{", body, re.M))
    check("descriptor rows parse non-empty", bool(declared), f"parsed={sorted(declared)}")

    # THE assertion nothing made before ADR-636: a registered app with no
    # client row renders someone else's grammar and nothing goes red.
    missing = sorted(REGISTERED - declared)
    check(
        "every registered app has a descriptor (the ADDITION case)",
        not missing,
        f"registered but undeclared client-side: {missing}",
    )
    phantom = sorted(declared - REGISTERED)
    check(
        "every descriptor names a registered app (no phantom)",
        not phantom,
        f"declared client-side but not registered: {phantom}",
    )


# ---------------------------------------------------------------------------
# [2] objectModel is declared for every app — ADR-633 D2, generalized
# ---------------------------------------------------------------------------
def test_object_model_declared() -> None:
    print("\n[2] objectModel is REQUIRED and declared per app (ADR-633 D2)")
    src = code_only(read("lib/apps/registry.ts"))
    rows = re.findall(
        r"^\s{2}([a-z][a-z0-9-]*):\s*\{(.*?)^\s{2}\},", src, re.M | re.S
    )
    check("descriptor rows parse for objectModel scan", bool(rows))
    for slug, body in rows:
        m = re.search(r"objectModel:\s*'(flow|pages|layers)'", body)
        check(f"{slug} declares a valid objectModel", bool(m),
              "missing or not one of flow|pages|layers")

    # The field must stay REQUIRED — an optional marker or a read-site default
    # restores the fall-through ADR-633 D2 deleted (images fell onto the
    # document branch and read "Slide" in the crumb, "Sections" in the rail).
    iface = src.split("export interface AppDescriptor", 1)[-1].split("}", 1)[0]
    check("objectModel is not optional in the interface", "objectModel?" not in iface)
    studio = code_only(read("components/authoring/StudioSurface.tsx"))
    check(
        "no read site defaults objectModel",
        not re.search(r"objectModel\s*(\?\?|\|\|)", studio),
        "a `?? 'pages'` here is the derivation this field replaced",
    )


# ---------------------------------------------------------------------------
# [3] The derived consumers are DERIVED — the hand lists stay deleted
# ---------------------------------------------------------------------------
def test_consumers_are_derived() -> None:
    print("\n[3] the app-shaped consumers derive, and the hand lists stay gone")
    ft = code_only(read("lib/file-types/index.ts"))
    check(
        "APP_SURFACES is built from APP_DESCRIPTORS, not hand-keyed",
        "APP_DESCRIPTORS" in ft and "Object.fromEntries" in ft,
    )
    # The apps that own artifact types must all reach the association. Derived
    # from the same registry, so this holds by construction — asserted anyway,
    # because "by construction" is exactly what stops being true in an edit.
    reg = code_only(read("lib/apps/registry.ts"))
    owners = set(
        re.findall(
            r"^\s{2}([a-z][a-z0-9-]*):\s*\{(?:(?!^\s{2}\},).)*?ownsArtifactTypes:\s*true",
            reg,
            re.M | re.S,
        )
    )
    check("at least one app owns artifact types (guards an empty scan)", bool(owners))
    check(
        "strings owns NO artifact type (its material is declarations, ADR-569)",
        "strings" not in owners,
        "a _string.yaml opens Strings by NAME, never because 'yaml opens Strings'",
    )

    oam = code_only(read("components/authoring/OpenArtifactModal.tsx"))
    check(
        "SERVED_INDEX_APPS is deleted (derived from servesIndex)",
        "SERVED_INDEX_APPS" not in oam,
    )
    check("OpenArtifactModal asks the registry", "servesArtifactIndex" in oam)

    studio = code_only(read("components/authoring/StudioSurface.tsx"))
    check(
        "AuthoringApp.slug is not a closed union (a 4th hand list in type clothes)",
        not re.search(r"slug:\s*'[a-z-]+'\s*\|", studio),
    )
    check(
        "the authoring rows are built from the descriptor, not restated",
        "authoringApp(" in studio and "resolveApp(" in studio,
    )
    # ADR-297 — one home for an app's mark. ADR-602 D4 repaired a Slides that
    # wore Palette on its landing and Presentation in the launcher.
    check(
        "the landing glyph resolves through resolveSurfaceIcon (ADR-297)",
        "resolveSurfaceIcon(iconKey)" in studio,
    )
    check(
        "StudioSurface no longer imports an app's own glyph",
        not re.search(r"import \{[^}]*\bNewspaper\b[^}]*\} from 'lucide-react'", studio),
        "an app's mark named here is a second home for the surface row's icon_key",
    )


# ---------------------------------------------------------------------------
# [4] The Dock default still equals the derivation (ADR-592, re-anchored)
# ---------------------------------------------------------------------------
def test_dock_default_still_derived() -> None:
    print("\n[4] DEFAULT_KEPT_SURFACES == is_default_pinned (ADR-592, kept)")
    from services.app_stage import is_default_pinned
    from services.kernel_surfaces import KERNEL_SURFACES

    rows = (
        KERNEL_SURFACES
        if isinstance(KERNEL_SURFACES, list)
        else list(KERNEL_SURFACES.values())
    )
    derived = {r["slug"] for r in rows if r.get("slug") and is_default_pinned(r)}
    prefs = code_only(read("lib/shell/surface-preferences.ts"))
    m = re.search(r"DEFAULT_KEPT_SURFACES:\s*string\[\]\s*=\s*\[(.*?)\]", prefs, re.S)
    check("DEFAULT_KEPT_SURFACES parses (guards a silent no-op scan)", bool(m))
    if not m:
        return
    fe = set(re.findall(r"'([a-z][a-z0-9-]*)'", m.group(1)))
    check("FE dock list parses non-empty", bool(fe))
    # The hand copy is JUSTIFIED and stays (the Dock seeds client-side before
    # any roster arrives) — what must not drift is its equality with the
    # derivation. ADR-592 owns this check; asserted here too because ADR-636's
    # subject is exactly "which client copies are held to the server".
    check(
        "the dock default equals the stage derivation",
        fe == derived,
        f"FE∖derived={sorted(fe - derived)} derived∖FE={sorted(derived - fe)}",
    )


# ---------------------------------------------------------------------------
# [5] Agent icons — the model this ADR generalizes (re-anchored, not forked)
# ---------------------------------------------------------------------------
def test_agent_icon_parity_holds() -> None:
    print("\n[5] the agent-icon derivation still holds (its home is test_agent_registry)")
    src = read("components/agents/AgentIcon.tsx")
    block = src.split("BEING_ICONS", 1)[-1].split("};", 1)[0]
    mapped = set(re.findall(r"^\s*'?([a-z-]+)'?\s*:", block, re.M))
    need = {r["icon"] for r in AGENTS.values() if r.get("icon")}
    check("icon map parses non-empty", bool(mapped))
    check(
        "every registry icon is mapped",
        not (need - mapped),
        f"unmapped: {sorted(need - mapped)}",
    )
    check(
        "no icon is mapped for an agent that no longer exists",
        not (mapped - need),
        f"dead entries: {sorted(mapped - need)}",
    )


# ---------------------------------------------------------------------------
# [6] The cliff — no client row may carry authority (ADR-460 D3.a)
# ---------------------------------------------------------------------------
def test_no_authority_on_a_client_row() -> None:
    print("\n[6] the ADR-460 D3.a cliff holds on the client descriptor")
    reg = code_only(read("lib/apps/registry.ts"))
    iface = reg.split("export interface AppDescriptor", 1)[-1].split("\n}", 1)[0]
    keys = set(re.findall(r"^\s{2}([a-zA-Z][a-zA-Z0-9]*)\??:", iface, re.M))
    allowed = {
        "slug", "label", "objectModel", "artifactParam",
        "ownsArtifactTypes", "servesIndex", "dimensionsFirst",
    }
    check("descriptor interface keys parse", bool(keys), f"keys={sorted(keys)}")
    check(
        "the descriptor carries no key outside the whitelist",
        keys <= allowed,
        f"unexpected: {sorted(keys - allowed)} — a client row may not name a "
        f"resident, an engine, a stage, a tier, a pin, or ANY authority",
    )
    for forbidden in ("resident", "agent", "model", "engine", "stage",
                      "launcherTier", "defaultPinned", "autonomy", "grant"):
        check(
            f"no `{forbidden}` on the client descriptor",
            forbidden not in keys,
            "that fact is the server's and arrives on the roster",
        )


if __name__ == "__main__":
    print("=" * 70)
    print("ADR-636 — an app declares itself once on each side of the wire")
    print("=" * 70)
    test_descriptor_parity()
    test_object_model_declared()
    test_consumers_are_derived()
    test_dock_default_still_derived()
    test_agent_icon_parity_holds()
    test_no_authority_on_a_client_row()
    print("\n" + "=" * 70)
    print(f"  {_passed} passed, {_failed} failed")
    print("=" * 70)
    sys.exit(1 if _failed else 0)

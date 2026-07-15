"""ADR-459 gate — the artifact reads as what it is.

The kind is LIFTED from content (never stored), the name is the titleized
meaning FOLDER (never stored), and the format leaves the composition while
staying on the mirror.

Run: python3 api/test_adr459_artifact_identity.py
(NOT pytest — the check() helpers print ✗ but pytest still reports PASS.)
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

passed = True


def _check(label: str, cond: bool, detail: str = "") -> bool:
    global passed
    print(f"  {'✓' if cond else '✗'} {label}" + (f"  [{detail}]" if detail and not cond else ""))
    passed = passed and bool(cond)
    return bool(cond)


def main() -> int:
    from services.studio import (
        STUDIO_ARTIFACT_REGION,
        STUDIO_LAYOUTS,
        artifact_kind,
        artifact_name,
        build_skeleton,
    )

    print("\n── D1: the kind is LIFTED from data-template ──────────────────")
    for slug, lay in STUDIO_LAYOUTS.items():
        got = artifact_kind(build_skeleton(slug))
        _check(
            f"'{slug}' skeleton lifts kind + served label",
            got["kind"] == slug and got["kind_label"] == lay["label"],
            detail=str(got),
        )

    print("\n── D1 FALSIFIER #1: a RENAMED artifact keeps its kind ─────────")
    # The retired stem-matcher read the basename: `ir-deck-v3.html` → "File".
    # The lift reads the content, so the rename is irrelevant.
    renamed = artifact_kind(build_skeleton("deck"))
    _check(
        "content-lift survives rename (stem-matcher said 'File')",
        renamed["kind"] == "deck" and renamed["kind_label"] == "Deck",
        detail=str(renamed),
    )

    print("\n── D3: the kind is an OPAQUE STRING (bundle-shippable) ─────────")
    tearsheet = artifact_kind('<!doctype html>\n<html data-template="tearsheet">')
    _check(
        "an unknown (bundle) slug round-trips + titleizes its label",
        tearsheet["kind"] == "tearsheet" and tearsheet["kind_label"] == "Tearsheet",
        detail=str(tearsheet),
    )
    for blank in (None, "", "<html>", "<html data-template=''>"):
        got = artifact_kind(blank)
        _check(
            f"undeclared layout degrades honestly ({blank!r})",
            got["kind"] is None and got["kind_label"] == "File",
            detail=str(got),
        )

    print("\n── D3 FALSIFIER #2: kernel SEEDS layouts, never BOUNDS them ────")
    for gate, name in (
        ("test_adr443_studio_model.py", "ADR-443"),
        ("test_adr440_studio.py", "ADR-440"),
    ):
        src = (Path(__file__).parent / gate).read_text()
        # Only a LITERAL-set pin is the violation. `set(A) == set(B)` between
        # two registries is a derivation invariant (STUDIO_TEMPLATES is built
        # FROM STUDIO_LAYOUTS) and must stay ==; it bounds nothing.
        pinned = re.search(
            r"set\(STUDIO_(?:LAYOUTS|TEMPLATES)\)\s*==\s*\{", src
        )
        _check(
            f"{name} gate asserts ⊇ not == (a bundle layout must not turn it red)",
            pinned is None,
            detail=f"{gate} still pins the set to a literal with ==",
        )
    from services.bundle_reader import list_bundle_layouts

    _check(
        "bundle_reader.list_bundle_layouts() exists + returns a dict (union-load)",
        isinstance(list_bundle_layouts(), dict),
    )

    print("\n── D2: the name IS the namespace, titleized ───────────────────")
    # SENTENCE case, not Title Case — the deliberately-dumb guess (see
    # `_titleize`). "Ir deck v3" is the known, predictable loss: the modal
    # lowercased the typed name into the slug, so casing is unrecoverable
    # without storing it — which is the second source ADR-459 D2 refuses.
    cases = [
        (f"{STUDIO_ARTIFACT_REGION}ir-deck-v3/deck.html", "Ir deck v3"),
        (f"{STUDIO_ARTIFACT_REGION}prd-for-yarnnn/document.html", "Prd for yarnnn"),
        # The load-bearing one: the member RENAMED the file; the name they
        # typed still lives in the folder, so the card is unaffected.
        (f"{STUDIO_ARTIFACT_REGION}q3-board-review/ir-deck-v3.html", "Q3 board review"),
        # No meaning folder → titleized stem rather than an invented name.
        (f"{STUDIO_ARTIFACT_REGION}deck.html", "Deck"),
    ]
    for path, want in cases:
        got = artifact_name(path)
        _check(f"{path.split('/operation/')[-1]:38} → {want!r}", got == want, detail=repr(got))

    print("\n── FALSIFIER #4: the ADR shipped NO storage ───────────────────")
    migrations = Path(__file__).parent.parent / "supabase" / "migrations"
    offenders = [
        m.name
        for m in migrations.glob("*.sql")
        if re.search(
            r"ALTER TABLE\s+workspace_files[\s\S]{0,120}ADD COLUMN[\s\S]{0,40}\b(kind|title)\b",
            m.read_text(),
            re.IGNORECASE,
        )
    ]
    _check(
        "no workspace_files.kind / .title column exists (the lift needs none)",
        not offenders,
        detail=str(offenders),
    )

    print("\n── FALSIFIER #3: no `.html` on the Studio LANDING composition ──")
    web = Path(__file__).parent.parent / "web" / "components" / "studio"
    surface = (web / "StudioSurface.tsx").read_text()
    # The recents card renders the served name + label, not the basename.
    recents = surface[surface.find("{recents.map((r) => {") :][:2400]
    _check(
        "card renders the served name (r.name), not baseName(r.path)",
        "{r.name}" in recents and "{baseName(r.path)}" not in recents,
    )
    _check(
        "card renders the served kind label (r.kind_label)",
        "{r.kind_label}" in recents,
    )
    _check(
        "the stem-matcher is retired (no studioShapeFromPath anywhere)",
        not any("studioShapeFromPath" in p.read_text() for p in web.glob("*.ts*")),
    )
    shapes = (web / "studioShapes.ts").read_text()
    _check(
        "studioShapes holds PRESENTATION only — no label strings",
        "label:" not in shapes and "studioShapeStyle" in shapes,
    )

    print("\n── D4: the MIRROR is untouched (ADR-340 DP29 / ADR-400) ───────")
    ws = Path(__file__).parent.parent / "web" / "components" / "workspace"
    _check(
        "FileMeta still renders the raw leaf (Files = /proc, not Finder)",
        "file.path.split('/').pop()" in (ws / "FileMeta.tsx").read_text(),
    )
    _check(
        "RenameModal still pre-fills the full extension (shared verb unforked)",
        "lastIndexOf('.')" in (ws / "RenameModal.tsx").read_text(),
    )
    # The editor crumb names the ARTIFACT — an app over one file says which file
    # it has open. It read `baseName(artifactPath)` when this gate was written;
    # ADR-459's rule then landed there too (899afd8 made the crumb the rename
    # affordance, so it shows the artifact's name, not its leaf). Assert the
    # INTENT (the crumb is named from the open artifact's path), not the
    # spelling — either helper satisfies it.
    _check(
        "the Studio EDITOR crumb names the open artifact (app over one file)",
        "label: artifactName(artifactPath)" in surface
        or "label: baseName(artifactPath)" in surface,
    )

    print()
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())

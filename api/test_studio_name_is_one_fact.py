#!/usr/bin/env python3
"""Gate: the name is ONE fact — the file, the crumb, and the title agree.

The operator's report (2026-07-15): "the name of the document or file should be
the title, and thus its display and renaming becomes linked."

What was actually there — THREE names for one artifact:

    /workspace/operation/prd-for-yarnnn/document.html
                         ^^^^^^^^^^^^^^ ^^^^^^^^^^^^^
                         THE NAME        the TYPE marker

  - the landing card said "Prd for yarnnn"  (artifact_name — correct, ADR-459)
  - the Studio crumb said "document.html"   (baseName — the TYPE, not a name)
  - the h1 said "Untitled document"         (linked to neither)

…and the two the member could see were the two that weren't its name. Creation
named the FILE from what the member typed and left the h1 at the placeholder;
the crumb showed the leaf, which only ever names the layout.

The fix, at both moments the split appears:
  CREATE — the name titles the artifact as well as the file.
  RENAME — the Design tab's rename retitles too, as one attributed revision.
And the crumb shows the NAME (artifact_name), not the type marker.

Two guards, because an h1 is not always a title:
  1. Only a `flow` layout's h1 IS the title. A deck's h1 is its title slide's
     thesis; a page's is its headline — authored content a FILENAME has no
     business dictating.
  2. Even in flow, only the untouched scaffold placeholder is replaced. Once
     the member authors a title, their words win.

NOT built (and deliberately): editing the h1 in place does not rename the file.
Pure Notion (title leads, file follows) would make every keystroke a MOVE of
substrate identity, breaking every data-ref citation that points at the path —
the citation graph is what the moat protects. See docs/design/STUDIO.md.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_results: list[tuple[str, bool]] = []


def _check(label: str, cond: bool) -> None:
    _results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")


def _h1(html: str) -> str | None:
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
    return re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else None


def _title(html: str) -> str | None:
    m = re.search(r"<title>([^<]*)</title>", html)
    return m.group(1) if m else None


def run() -> bool:
    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root / "api"))
    from services.studio import (
        STUDIO_LAYOUTS,
        STUDIO_TEMPLATES,
        artifact_name,
        set_artifact_title,
    )

    web = root / "web"
    surface = (web / "components/studio/StudioSurface.tsx").read_text()
    routes = (root / "api/routes/studio.py").read_text()
    client = (web / "lib/api/client.ts").read_text()

    # ── 1. the name resolver ────────────────────────────────────────────────
    _check(
        "the NAME is the meaning folder, not the leaf",
        artifact_name("/workspace/operation/prd-for-yarnnn/document.html") == "Prd for yarnnn",
    )
    _check(
        "a leaf rename does NOT change the name (the leaf is a TYPE marker)",
        artifact_name("/workspace/operation/prd-for-yarnnn/document.html")
        == artifact_name("/workspace/operation/prd-for-yarnnn/report.html"),
    )
    _check(
        "no meaning folder degrades to the stem, never invents a name",
        artifact_name("/workspace/operation/deck.html") == "Deck",
    )

    # ── 2. CREATE titles the artifact ───────────────────────────────────────
    for slug, lay in STUDIO_LAYOUTS.items():
        path = f"/workspace/operation/q3-board-review/{slug}.html"
        is_flow = lay["mode"] == "flow"
        out = set_artifact_title(STUDIO_TEMPLATES[slug]["skeleton"], artifact_name(path), set_h1=is_flow)
        if is_flow:
            _check(f"CREATE titles a {slug} (flow: the h1 IS the title)", _h1(out) == "Q3 board review")
        else:
            _check(
                f"CREATE leaves a {slug}'s h1 alone (paged: it's a thesis/headline)",
                _h1(out) == _h1(STUDIO_TEMPLATES[slug]["skeleton"]),
            )
        _check(f"CREATE always sets a {slug}'s <title> (metadata, never authored)",
               _title(out) == "Q3 board review")

    # ── 3. the guards ───────────────────────────────────────────────────────
    authored = STUDIO_TEMPLATES["document"]["skeleton"].replace("Untitled document", "My real title")
    out = set_artifact_title(authored, "Something Else", set_h1=True)
    _check("an AUTHORED title is never overwritten (their words win)", _h1(out) == "My real title")
    _check("…but the <title> still follows (it is metadata)", _title(out) == "Something Else")
    _check(
        "the placeholder set is DERIVED from the registry (a scaffold edit can't orphan it)",
        "_SCAFFOLD_TITLES: frozenset[str] = frozenset(" in (root / "api/services/studio.py").read_text(),
    )
    out = set_artifact_title(STUDIO_TEMPLATES["document"]["skeleton"], "<script>alert(1)</script>")
    _check("the title is escaped (it lands in html)", "<script>" not in out.split("</head>")[1])

    # ── 4. RENAME retitles ──────────────────────────────────────────────────
    _check(
        "a retitle endpoint exists, server-side (the h1-is-a-title knowledge lives with the registry)",
        '@router.post("/studio/artifacts/retitle")' in routes,
    )
    # ADR-469 SPLIT THIS GUARD IN TWO. It used to return early on a paged
    # layout and so never wrote <title> either — which meant a renamed DECK
    # kept its old <title> and the landing card silently reverted to the folder
    # slug. Guarding the h1 is right (a deck's h1 is its thesis); guarding the
    # title was the bug, because <title> is where the name now LIVES.
    _check(
        "the h1 guard survives (only a flow layout's h1 is a title)",
        "is_flow = bool(layout and layout[\"mode\"] == \"flow\")" in routes
        and "set_h1=is_flow" in routes,
    )
    _check(
        "<title> is written for EVERY layout (it is the name's home, never authored)",
        '"reason": "not_a_flow_layout"' not in routes and '"reason": "no_change"' in routes,
    )
    _check(
        "it is NOT folded into the generic move endpoint (that is every surface's move)",
        "retitle" not in (root / "api/routes/documents.py").read_text(),
    )
    _check("the client exposes retitleArtifact", "retitleArtifact: (path: string)" in client)
    # RENAME renames the artifact's NAME = its MEANING FOLDER (moving every file
    # under it), then retitles. The shared leaf-rename would rename the TYPE.
    _check(
        "a rename endpoint exists and renames the FOLDER, not the leaf",
        '@router.post("/studio/artifacts/rename")' in routes
        and 'old_folder = "/" + "/".join(parts[:-1])' in routes,
    )
    # The INVARIANT is "two artifacts never merge into one namespace". It used
    # to be upheld by REFUSING a colliding name (409). ADR-469 upholds it by
    # DISAMBIGUATING the key instead — strictly stronger: refusal left the
    # member stuck (a name with no Latin characters slugged to `untitled`, so
    # their second such document could not be named at all), while
    # disambiguation always yields a distinct key AND keeps the typed name.
    _check(
        "two artifacts never merge into one namespace (now by disambiguation, not refusal)",
        "slug = disambiguate(slug, taken)" in routes
        and "taken = {" in routes,
    )
    _check(
        "it refuses an artifact with no meaning folder (nothing to rename)",
        "has no meaning folder to rename" in routes,
    )
    # THE REGRESSION GUARD (fixed 2026-07-18): the rename docstring + the FE
    # comment ("the retitle is a server-side write") both promised the h1
    # follows a rename — but rename_artifact only MoveFile'd and returned, so a
    # renamed document kept its old <h1>: two names for one thing, exactly the
    # desync this whole arc claims to have closed. The retitle logic is now a
    # SHARED helper both endpoints call (Singular Implementation).
    # Renamed `_retitle_to_match_filename` → `_retitle_to` by ADR-469: the old
    # name described the old direction of travel (filename → title). The
    # causality now runs from the TYPED name into both the title (verbatim) and
    # the folder key (slugified), so the filename dictates nothing.
    _check(
        "the retitle body is a shared helper (both /retitle and rename call it)",
        "def _retitle_to(" in routes and routes.count("_retitle_to(auth,") >= 2,
    )
    _check(
        "rename_artifact actually folds in the retitle (the h1 follows the name)",
        "_retitle_to(auth, new_path, typed)" in routes and '"retitled": retitled' in routes,
    )
    # ADR-469: the slug rule moved OUT of an inlined regex into the one shared
    # `services/naming.py::path_slug`, so create and rename cannot drift.
    _check(
        "the server slugifies via the ONE shared helper (create + rename can't drift)",
        "from services.naming import disambiguate, path_slug" in routes
        and "slug = path_slug(typed)" in routes
        and 're.sub(r"[^a-z0-9]+", "-", (req.name or "").lower())' not in routes,
    )
    # ADR-469 — the split: the path is a KEY, the title is the NAME.
    _check(
        "the typed name reaches the title verbatim (not reconstructed from the path)",
        "_retitle_to(auth, new_path, typed)" in routes
        and '"name": typed,' in routes,
    )
    _check(
        "a key collision is DISAMBIGUATED, never 409'd (a Korean workspace can name a 2nd doc)",
        "slug = disambiguate(slug, taken)" in routes
        and "already exists — pick another name" not in routes,
    )
    _check(
        "the Studio's rename is the CRUMB, committed on Enter/blur (never per-keystroke)",
        "const commitRename = useCallback(" in surface
        and "api.studio.renameArtifact(artifactPath, trimmed)" in surface
        and "if (e.key === 'Enter') {" in surface,
    )
    _check(
        "ONE rename path: the Design tab + the landing both reach the crumb",
        "rename: () => setRenaming(true)," in surface
        and "onRenameRequest: (path: string) => void;" in surface,
    )
    _check(
        "the shared LEAF-rename modal is no longer wired for the Studio",
        "organizeVerbs.onRename" not in surface,
    )

    # ── 5. the crumb shows the NAME ─────────────────────────────────────────
    # ADR-483 completed the ADR-469 lift FE-side: the resolver is no longer a
    # path-only mirror of `artifact_name`'s FALLBACK — it is the whole rule,
    # <title> first with the meaning folder behind it. The invariant this pair
    # has always protected (the crumb shows the NAME, never the type leaf) is
    # unchanged; only the function carrying it is.
    _check(
        "the FE has the name resolver, mirroring artifact_name (title, then path)",
        "function artifactNameOf(" in surface and "function artifactNameFromPath(" in surface,
    )
    _check(
        "both crumbs (the OS window crumb + the toolbar's own) show the NAME",
        surface.count("artifactDisplayName") >= 2,
    )
    _check(
        "the leaf is gone from the crumb (it named the TYPE, not the artifact)",
        'title={baseName(artifactPath)}' not in surface,
    )

    ok = all(c for _, c in _results)
    print()
    print(f"{'PASS' if ok else 'FAIL'}: {sum(c for _, c in _results)}/{len(_results)} checks")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)

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
    _check(
        "it refuses a paged layout (guard 1) and no-ops with no revision",
        '"reason": "not_a_flow_layout"' in routes and '"reason": "no_change"' in routes,
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
    _check(
        "it refuses a collision rather than merging two artifacts' namespaces",
        "already exists — pick another name." in routes,
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
    _check(
        "the retitle body is a shared helper (both /retitle and rename call it)",
        "def _retitle_to_match_filename(" in routes
        and routes.count("_retitle_to_match_filename(auth,") >= 2,
    )
    _check(
        "rename_artifact actually folds in the retitle (the h1 follows the name)",
        "_retitle_to_match_filename(auth, new_path)" in routes
        and '"retitled": retitled' in routes,
    )
    _check(
        "the server slugifies (create + rename can't drift on what a name becomes)",
        're.sub(r"[^a-z0-9]+", "-", (req.name or "").lower()).strip("-")[:48]' in routes,
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
    _check(
        "the FE has the name resolver, mirroring artifact_name",
        "function artifactName(p: string): string {" in surface,
    )
    _check(
        "both crumbs (the OS window crumb + the toolbar's own) show the NAME",
        surface.count("artifactName(artifactPath)") >= 2,
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

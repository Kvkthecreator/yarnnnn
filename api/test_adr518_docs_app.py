"""ADR-518 — Docs and Studio: the writing app / layout app split's invariants.

The carve re-runs the ADR-472 pattern: the `document` type's declaration moves
to its own module (`services/docs.py`), the shared machinery stays kernel with
three consumers, and every housing surface gains a row rather than a branch.

  §1  the carve       — document is GONE from Studio's table; lives in Docs
  §2  the association — kind→app and app→kinds derive from the one declaration
  §3  shared machinery — skeleton, fallback, templates, scaffold titles
  §4  the housing     — kernel surface row + FE rows (route, registry, params)
  §5  no dual path    — labels declared not ternaried; Learn targets ownership-
                        filtered; the legacy ADR-249 /docs pages are deleted

Run:  python3 api/test_adr518_docs_app.py   (NOT pytest — check()-gate.)
"""

import sys
from pathlib import Path

_results: list[tuple[str, bool]] = []


def _check(label: str, cond: bool) -> None:
    _results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")


def run() -> bool:
    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(Path(__file__).resolve().parent))

    from services import docs as dx
    from services import images as im
    from services.studio import (
        STUDIO_LAYOUTS,
        _SCAFFOLD_TITLES,
        all_templates,
        app_for_kind,
        build_skeleton,
        kinds_for_app,
        resolve_layout,
    )

    # ── §1 The carve (D1/D3/D7) ──────────────────────────────────────────
    _check("document is GONE from Studio's layouts", "document" not in STUDIO_LAYOUTS)
    _check(
        "Studio's own table is exactly the paged/layout media",
        set(STUDIO_LAYOUTS) == {"deck", "web"},
    )
    _check(
        "document lives in Docs and resolves through the shared registry",
        dx.DOCUMENT_SLUG == "document"
        and dx.DOCUMENT_SLUG in dx.DOCS_LAYOUTS
        and resolve_layout("document") is dx.DOCS_LAYOUTS["document"],
    )
    _check(
        "the document row is flow-moded and declares its owner",
        dx.DOCS_LAYOUTS["document"]["mode"] == "flow"
        and dx.DOCS_LAYOUTS["document"]["app"] == "docs",
    )
    # First-registration-wins means a collision is silent at register time
    # (ADR-443 §6: no exceptions from services/studio.py) — disjointness is
    # asserted HERE, pairwise across all three apps' tables.
    _check(
        "the three apps' layout slug sets are pairwise DISJOINT",
        not (set(STUDIO_LAYOUTS) & set(dx.DOCS_LAYOUTS))
        and not (set(STUDIO_LAYOUTS) & set(im.IMAGES_LAYOUTS))
        and not (set(dx.DOCS_LAYOUTS) & set(im.IMAGES_LAYOUTS)),
    )

    # ── §2 The association (ADR-473 D2 via D1) ───────────────────────────
    _check(
        "kind→app: document→docs, deck/web→studio, image→images",
        app_for_kind("document") == "docs"
        and app_for_kind("deck") == "studio"
        and app_for_kind("web") == "studio"
        and app_for_kind("image") == "images",
    )
    _check(
        "app→kinds derives, never restated",
        kinds_for_app("docs") == {"document"}
        and kinds_for_app("studio") == {"deck", "web"}
        and kinds_for_app("images") == {"image"},
    )
    _check("canvas still belongs to no app (ADR-472 D7)", app_for_kind("canvas") is None)
    _check(
        "retired slugs keep resolving to Studio's web (ADR-505 D2 untouched)",
        app_for_kind("article") == "studio" and app_for_kind("page") == "studio",
    )

    # ── §3 The shared machinery (D2/D3) ──────────────────────────────────
    sk = build_skeleton("document")
    _check(
        "one skeleton builder serves Docs' type",
        'data-template="document"' in sk and "Untitled document" in sk,
    )
    _check(
        "the unknown-layout fallback still lands the capture medium, via the registry",
        "Untitled document" in build_skeleton("no-such-layout"),
    )
    _check(
        "the cross-app template view carries the app declaration",
        all_templates()["document"]["app"] == "docs"
        and all_templates()["deck"]["app"] == "studio",
    )
    # The D3 fix: the scaffold-title set is maintained at REGISTRATION, so it
    # covers every app — including the IMAGES scaffold the frozen derivation
    # silently missed.
    _check(
        "scaffold titles cover Docs' document AND the IMAGES stage",
        "Untitled document" in _SCAFFOLD_TITLES
        and "The visual statement." in _SCAFFOLD_TITLES,
    )

    # ── §4 The housing (D1/D4/D5) ────────────────────────────────────────
    ks = (root / "api/services/kernel_surfaces.py").read_text()
    _check(
        "kernel surface row: docs, primary, pinned, /docs, file-text",
        '"slug": "docs"' in ks
        and '"route": "/docs"' in ks
        and '"icon_key": "file-text"' in ks,
    )
    _check(
        "Docs unveils in FULL (D5) — primary tier, default-pinned",
        '"slug": "docs"' in ks.split('"slug": "studio"')[0]
        and ks.split('"slug": "docs"')[1].split('"slug":')[0].count('"launcher_tier": "primary"') == 1
        and ks.split('"slug": "docs"')[1].split('"slug":')[0].count('"default_pinned": True') == 1,
    )
    _check(
        "routes/studio.py registers Docs at boot (the load-bearing import)",
        "import services.docs" in (root / "api/routes/studio.py").read_text(),
    )
    page = (root / "web/app/(authenticated)/docs/page.tsx").read_text()
    _check(
        "/docs mounts the shared surface parameterized by DOCS_APP",
        "StudioSurface app={DOCS_APP}" in page and "redirect(" not in page,
    )
    _check(
        "the ADR-249 upload-detail page is DELETED",
        not (root / "web/app/(authenticated)/docs/[id]").exists(),
    )
    _check(
        "SurfaceRegistry carries the docs row",
        "docs: DocsPage" in (root / "web/components/shell/SurfaceRegistry.tsx").read_text(),
    )
    ft = (root / "web/lib/file-types/index.ts").read_text()
    _check(
        "APP_SURFACES carries docs → surface docs, param file",
        "docs: { surface: 'docs', param: 'file'" in ft,
    )
    prefs = (root / "web/lib/shell/surface-preferences.ts").read_text()
    _check(
        "docs params are OWNED and EPHEMERAL like its siblings",
        prefs.count("docs: ['file', 'system']") == 2,
    )
    _check(
        "docs ships in the default Dock with a reseed generation",
        "'docs', // ADR-518" in prefs
        and "dock-reseed-2026-08-04-docs" in prefs,
    )
    surface = (root / "web/components/studio/StudioSurface.tsx").read_text()
    _check(
        "AuthoringApp admits docs and declares DOCS_APP",
        "slug: 'docs' | 'studio' | 'images'" in surface
        and "export const DOCS_APP" in surface,
    )

    # ── §5 No dual path (D6/D7) ──────────────────────────────────────────
    _check(
        "the app label is DECLARED, not ternaried per site",
        "app.slug === 'images' ? 'Images' : 'Studio'" not in surface
        and surface.count("label: string") >= 1,
    )
    _check(
        "Learn targets are ownership-filtered via the served association",
        "appForKind(t.template) === app.slug" in surface,
    )
    _check(
        "the lane resident keys on THIS app (no hardcoded .studio lookup)",
        "AUTHORING_APPS.studio.resident" not in surface
        and surface.count("residentFor(app.slug)") == 2,
    )
    auth = (root / "web/lib/apps/authoring.ts").read_text()
    _check(
        "AUTHORING_APPS declares all three residencies (Designer, ADR-467 D3)",
        "docs: { id: 'docs', resident: 'designer' }" in auth
        and "images: { id: 'images', resident: 'designer' }" in auth,
    )
    # Run-1 finding (2026-08-04 click-pass): the menu/Get-Info handler
    # resolutions omitted `kind`, so a document's menu read "Studio (default)"
    # and never listed Docs. Per-SITE assertions (a counting gate cannot
    # defend a per-site invariant): every sync resolution consults the shared
    # PATH_KIND cache; every content read remembers into it.
    fp = (root / "web/app/(authenticated)/files/page.tsx").read_text()
    _check(
        "files menu + openWith resolve WITH the cached kind (run-1 fix)",
        fp.count("knownKind(t.path)") == 2 and "rememberKind(path, kind)" in fp,
    )
    ndp = (root / "web/components/workspace/NodeDetailsPanel.tsx").read_text()
    _check(
        "Get Info's Opens-with resolves WITH the file's kind (run-1 fix)",
        "resolveHandlers({ paths: [path], isFolder: false, kind })" in ndp
        and "rememberKind(path, k)" in ndp,
    )

    ok = all(c for _, c in _results)
    print(f"\n{'ALL PASS' if ok else 'FAILURES'} — {sum(c for _, c in _results)}/{len(_results)}")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)

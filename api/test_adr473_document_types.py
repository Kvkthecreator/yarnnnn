"""ADR-473 — document types + "Open With": the type→app association.

The operator's bug: the Images landing listed every Studio artifact (Test page,
Test article, a Deck, a Document). ADR-472 filtered the template PICKER but
nothing else, because nothing in the system answered "which app owns this
document type?" — and extension cannot answer it, since Studio and IMAGES both
author `.html`.

Covers:
  §1  the declaration — every layout row names its owning app
  §2  the resolver    — kind→app, and its inverse; unowned degrades (D6)
  §3  the serving     — `app` rides templates + vocabulary (D3)
  §4  EXECUTION       — the endpoints actually run and scope (the yesterday
                        lesson: a grep proves a symbol exists, never that a
                        handler can reach it)
  §5  no dual path    — the FE holds no hardcoded "which types are mine" list

Run:  python3 api/test_adr473_document_types.py   (NOT pytest — check()-gate.)
"""

import asyncio
import sys
from pathlib import Path

_results: list[tuple[str, bool]] = []


def _check(label: str, cond: bool) -> None:
    _results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")


class _FakeAuth:
    user_id = "00000000-0000-0000-0000-000000000000"
    client = None


def _read(rel: str) -> str:
    return Path(__file__).resolve().parents[1].joinpath(rel).read_text()


def run() -> bool:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import services.images  # noqa: F401 — registration side-effect
    import routes.studio as rs
    from services.studio import (
        STUDIO_LAYOUTS,
        all_layouts,
        app_for_kind,
        kinds_for_app,
    )

    # ── §1 The declaration ───────────────────────────────────────────────
    _check(
        "every registered layout declares an owning app",
        all(row.get("app") for row in all_layouts().values()),
    )
    _check(
        "Studio's four types are Studio's",
        all(STUDIO_LAYOUTS[s].get("app") == "studio" for s in STUDIO_LAYOUTS),
    )

    # ── §2 The resolver ──────────────────────────────────────────────────
    _check(
        "kind→app resolves both apps",
        app_for_kind("deck") == "studio" and app_for_kind("image") == "images",
    )
    _check(
        "an UNOWNED type degrades to None, never raises (D6)",
        app_for_kind("tearsheet-from-a-bundle") is None and app_for_kind(None) is None,
    )
    _check(
        "the inverse lookup partitions the types — no type in both apps",
        kinds_for_app("studio") == {"document", "deck", "article", "page"}
        and kinds_for_app("images") == {"image"}
        and not (kinds_for_app("studio") & kinds_for_app("images")),
    )

    # ── §3 + §4 Serving AND execution ────────────────────────────────────
    auth = _FakeAuth()
    try:
        templates = asyncio.run(rs.list_templates(auth))
        rows = {t["slug"]: t.get("app") for t in templates["templates"]}
        _check("GET /studio/templates EXECUTES and carries `app` per row", all(rows.values()))
        _check(
            "…and every app's types are present (the picker filters client-side on it)",
            rows.get("deck") == "studio" and rows.get("image") == "images",
        )
    except Exception as exc:  # noqa: BLE001
        _check(f"GET /studio/templates EXECUTES — raised {type(exc).__name__}: {exc}", False)
        _check("…and every app's types are present", False)

    try:
        vocab = asyncio.run(rs.get_vocabulary(auth))
        layouts = {l["slug"]: l.get("app") for l in vocab["layouts"]}
        _check(
            "GET /studio/vocabulary EXECUTES and serves the association (D3)",
            layouts.get("deck") == "studio" and layouts.get("image") == "images",
        )
    except Exception as exc:  # noqa: BLE001
        _check(f"GET /studio/vocabulary EXECUTES — raised {type(exc).__name__}: {exc}", False)

    # The artifact list's SCOPING logic, exercised without a DB: the filter is
    # `app_for_kind(kind) != app`, so prove the decision, not the query.
    _check(
        "artifact scoping keeps only the asking app's types (D4)",
        app_for_kind("image") == "images"
        and app_for_kind("deck") != "images"
        and app_for_kind("document") != "images",
    )
    src = _read("api/routes/studio.py")
    _check(
        "the artifact list takes an `app` filter and widens its window first",
        "async def list_artifacts(auth: UserClient, app: Optional[str] = None)" in src
        and ".limit(200)" in src
        and "_DISPLAY_LIMIT" in src,
    )

    # ── §5 No dual path (the hooks discipline) ───────────────────────────
    surface = _read("web/components/studio/StudioSurface.tsx")
    _check(
        "the FE holds NO hardcoded type list — ownership is served",
        "IMAGES_APP.templates" not in surface
        and "templates?: string[]" not in surface
        and "t.app === app.slug" in surface,
    )
    _check(
        "recents are scoped by the asking app (the operator's bug)",
        ".artifacts(app.slug)" in surface,
    )
    ftypes = _read("web/lib/file-types/index.ts")
    _check(
        "the ADR-451 `every html → Studio` hardcode is REPLACED, not supplemented",
        "registerKindApps" in ftypes
        and "appForKind" in ftypes
        and "return { surface: 'studio', param: 'file', label: 'Studio' };" not in ftypes,
    )
    _check(
        "the Finder's open verb resolves the artifact's KIND before routing",
        "extractTemplate" in _read("web/app/(authenticated)/files/page.tsx"),
    )

    ok = all(c for _, c in _results)
    print()
    print(f"{'PASS' if ok else 'FAIL'}: {sum(c for _, c in _results)}/{len(_results)} checks")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)

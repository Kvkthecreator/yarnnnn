"""ADR-574 — The prose currency leads: Text is the text app, Docs pauses.

The invariants of a PAUSE, and the measurement that justified it.

  §1  the premise    — Text leads for text: it owns the prose class, is
                       primary + pinned, and leads the default Dock's app band
  §2  the pause      — Docs is search-only AND unpinned, TOGETHER; it left the
                       default Dock behind its own reseed generation
  §3  not unplugged  — route, registry, layout row, resident, flow editor and
                       the type→app association all still live (ADR-574 D2/D3)
  §4  the trap       — the removal edge is recorded so it is not re-discovered:
                       APP_SURFACES.docs and the `document` row may only ever
                       be removed together (ADR-574 D3)
  §5  the receipt    — MEASURED, not asserted: a `document` artifact exceeds
                       the MCP read cap on kernel CSS alone and never reaches
                       <body>. This is the evidence ADR-574 §2b stands on; if
                       it ever stops being true, the ADR's premise changed and
                       this gate must be re-read, not silenced.

Run:  cd api && python3 test_adr574_prose_currency.py   (NOT pytest — check()-gate.)
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

    import services.apps  # noqa: F401  (registration side-effects)
    from services.authoring import (
        app_for_kind,
        resident_for_app,
        resolve_app,
        resolve_layout,
    )
    from services.kernel_surfaces import KERNEL_SURFACES

    rows = {s["slug"]: s for s in KERNEL_SURFACES}
    prefs = (root / "web/lib/shell/surface-preferences.ts").read_text()
    kept = prefs.split("DEFAULT_KEPT_SURFACES")[1].split("];")[0]

    # ── §1 The premise (D1) — Text leads for text ────────────────────────
    text = rows.get("text")
    _check(
        "Text is the text premise — primary tier AND default-pinned",
        text is not None
        and text.get("launcher_tier") == "primary"
        and text.get("default_pinned") is True,
    )
    _check(
        "Text ships in the default Dock",
        "'text'," in kept,
    )
    # The prose class is the Text app's, claimed in the FE resolver. Read the
    # branch that RETURNS the surface, not the mere presence of the words —
    # a co-occurrence check cannot defend a specific site.
    ft = (root / "web/lib/file-types/index.ts").read_text()
    _check(
        "the prose class routes to Text (the claiming branch, not a mention)",
        "return APP_SURFACES.text;" in ft,
    )

    # ── §2 The pause (D2) — both fields, together ────────────────────────
    docs = rows.get("docs")
    _check(
        "Docs is PAUSED — search-only tier AND unpinned, together",
        docs is not None
        and docs.get("launcher_tier") == "search-only"
        and docs.get("default_pinned") is False,
    )
    _check(
        "Docs has LEFT the default Dock",
        "'docs'," not in kept,
    )
    _check(
        "the pausing reseed generation exists and its `previous` is the "
        "pre-pause default (a wrong `previous` silently never fires)",
        "dock-reseed-2026-08-17-docs-paused" in prefs
        and "['chat', 'docs', 'text', 'studio', 'radar', 'strings', 'files', 'agents']"
        in prefs,
    )
    _check(
        "the ladder's history is preserved — earlier generations are not rewritten",
        "dock-reseed-2026-08-04-docs" in prefs
        and "dock-reseed-2026-08-14-text" in prefs,
    )

    # ── §3 Hidden, NOT unplugged (D2/D3) ────────────────────────────────
    _check(
        "the route and the application register survive the pause",
        docs is not None
        and docs.get("route") == "/docs"
        and docs.get("register") == "application",
    )
    _check(
        "the type→app association survives — a document still opens into Docs",
        app_for_kind("document") == "docs",
    )
    _check(
        "the `document` layout row is still registered (flow, Docs-owned)",
        resolve_layout("document").get("mode") == "flow"
        and resolve_layout("document").get("app") == "docs",
    )
    _check(
        "the resident survives the pause (ADR-562 — engine follows the resident); "
        "the colleague is still named Writer",
        resident_for_app("docs") == "designer"
        and resolve_app("docs").get("name") == "Writer",
    )
    _check(
        "the surface still mounts — SurfaceRegistry + route file intact",
        "docs: DocsPage"
        in (root / "web/components/shell/SurfaceRegistry.tsx").read_text()
        and (root / "web/app/(authenticated)/docs/page.tsx").exists(),
    )
    _check(
        "the flow editor is MOTHBALLED, not deleted (Docs is its sole consumer)",
        (root / "web/components/authoring/FlowEditor.tsx").exists()
        and (root / "web/lib/authoring/flow/commands.ts").exists(),
    )

    # ── §4 The recorded trap (D3) ───────────────────────────────────────
    # Removing APP_SURFACES.docs while the `document` row still resolves to
    # app "docs" makes resolveSurfaceApplication fall through to
    # DEFAULT_ARTIFACT_APP ('studio') and render a FLOW document as PAGED
    # slides — silently. The two may only ever be removed together.
    _check(
        "APP_SURFACES still carries docs — the pair that must move together",
        "docs: { surface: 'docs', param: 'file'" in ft,
    )
    _check(
        "the fallback that makes the trap real is still the one described",
        "DEFAULT_ARTIFACT_APP" in ft and "'studio'" in ft,
    )

    # ── §5 The receipt (§2b) — MEASURED, not asserted ───────────────────
    # The ADR's load-bearing evidence. Driven through the real builder and
    # the real cap, so the claim cannot rot into folklore.
    from services.authoring import build_skeleton
    from services.mcp_composition import OPEN_CONTENT_CAP

    artifact = build_skeleton("document", title="Gate probe")
    head = artifact[:OPEN_CONTENT_CAP]
    _check(
        "a blank document EXCEEDS the MCP read cap (the artifact is truncated)",
        len(artifact) > OPEN_CONTENT_CAP,
    )
    _check(
        "…and <body> is NEVER reached — an external LLM receives zero authored "
        "content (ADR-574 §2b, the reason the pause is not a taste call)",
        "<body" not in head,
    )
    # The cheapest repair named in ADR-574 §4, still addressable when taken.
    from services.authoring import _KERNEL_ELEMENT_RX

    _check(
        "the named repair stays addressable — the kernel element is regex-locatable",
        _KERNEL_ELEMENT_RX.search(artifact) is not None,
    )

    passed = sum(1 for _, ok in _results if ok)
    total = len(_results)
    print()
    if passed == total:
        print(f"ALL PASS — {passed}/{total}")
        return True
    print(f"FAILED — {passed}/{total}")
    for label, ok in _results:
        if not ok:
            print(f"  FAIL: {label}")
    return False


if __name__ == "__main__":
    sys.exit(0 if run() else 1)

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

    # ── §2 The pause (D2) → the DELETION (ADR-599 D5) ───────────────────
    # D2 paused Docs to `search-only`. ADR-599 D5 then deleted the app in full,
    # which SUPERSEDES the pause: there is no row to carry the two fields. The
    # assertion is re-anchored to the end state rather than left pinning a
    # spelling the system no longer has — a gate that pins a removed state
    # reports the correct system as broken.
    docs = rows.get("docs")
    _check(
        "Docs is GONE, not paused — the app was deleted in full (ADR-599 D5, "
        "superseding this ADR's D2 pause)",
        docs is None,
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

    # ── §3 Hidden, NOT unplugged (D2/D3) → fully unplugged (ADR-599 D5) ──
    # D3 recorded a trap: removing the app while `document` still resolved to
    # it would render a FLOW document as PAGED slides, silently. The deletion
    # took the pair together, so the trap did not fire — assert THAT, which is
    # the invariant worth holding, rather than the survival of a deleted row.
    _check(
        "the deletion took the app AND its type association together — the D3 "
        "trap (a flow document rendering as paged slides) cannot fire",
        app_for_kind("document") != "docs",
    )
    _check(
        "no layout row still claims the deleted app",
        (resolve_layout("document") or {}).get("app") != "docs",
    )
    _check(
        "no resident is declared for the deleted app",
        resident_for_app("docs") is None,
    )
    # ADR-592 SUPERSEDES D2's "hidden, not unplugged": the pause became a HIDE
    # because it never took effect (a curated Dock kept the icon, /docs still
    # rendered, flat search still matched). The surface must now NOT mount —
    # the registry row is gone and the route is a redirect stub → /text.
    # Comments are STRIPPED before matching: this stub's docstring names
    # `StudioSurface` to say what it replaced, and an assertion that matched
    # its own explanatory comment would read the correct file as broken (the
    # recorded comment-vs-code gate defect).
    import re as _re

    def _code_only(text: str) -> str:
        text = _re.sub(r"/\*.*?\*/", "", text, flags=_re.DOTALL)
        return _re.sub(r"^\s*//.*$", "", text, flags=_re.MULTILINE)

    _reg = _code_only((root / "web/components/shell/SurfaceRegistry.tsx").read_text())
    _route = _code_only((root / "web/app/(authenticated)/docs/page.tsx").read_text())
    _check(
        "the surface no longer mounts — no registry row, route is a stub (ADR-592)",
        "docs: DocsPage" not in _reg
        and "redirect(" in _route
        and "StudioSurface" not in _route,
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
    # ADR-592 — the pair MOVED TOGETHER, which is what D3 demanded. The trap
    # D3 recorded (a flow document rendering as PAGED slides) does not fire:
    # `resolvedMode` is read from the LAYOUT vocabulary
    # (`layouts.find(l => l.slug === template)?.mode`), not from the app, and
    # the `document` layout still declares mode='flow'. So the fallback to
    # Studio renders flow — the app changed, the mode did not.
    _check(
        "APP_SURFACES no longer carries docs (moved WITH the surface, ADR-592)",
        "docs: { surface: 'docs', param: 'file'" not in ft,
    )
    _check(
        "the fallback that makes the trap real is still the one described "
        "(the app it names moved studio→slides; the FALLBACK is the invariant)",
        "DEFAULT_ARTIFACT_APP" in ft,
    )

    # ── §5 The receipt (§2b) — MEASURED, not asserted ───────────────────
    # The ADR's load-bearing evidence. Driven through the real builder and
    # the real cap, so the claim cannot rot into folklore.
    from services.authoring import build_skeleton
    from services.mcp_composition import OPEN_CONTENT_CAP

    # §2b is CLOSED (2026-08-28). The receipt inverts: it used to prove the
    # defect (a blank artifact whose <body> the cap never reached); it now
    # proves the repair holds. The RAW measurement is kept — the artifact is
    # still larger than the cap, which is why the repair is load-bearing rather
    # than incidental.
    from services.machine_projection import elide_presentation_css

    artifact = build_skeleton("slides", title="Gate probe")
    _check(
        "the raw artifact still EXCEEDS the read cap (the pressure is real)",
        len(artifact) > OPEN_CONTENT_CAP,
    )
    _check(
        "…and raw, <body> is still never reached — the defect's mechanism is "
        "unchanged; what changed is that the read path no longer ships it",
        "<body" not in artifact[:OPEN_CONTENT_CAP],
    )
    read_form, elided = elide_presentation_css(artifact)
    _check(
        "ADR-574 §2b CLOSED — after elision the body IS inside the first page, "
        "so an external LLM receives authored content, not a stylesheet",
        elided > 0 and "<body" in read_form[:OPEN_CONTENT_CAP],
    )
    # The cheapest repair named in ADR-574 §4 — taken, and still addressable.
    from services.authoring import _KERNEL_ELEMENT_RX

    _check(
        "the repair stays addressable — the kernel element is regex-locatable",
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

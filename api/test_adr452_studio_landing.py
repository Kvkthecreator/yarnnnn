"""
ADR-451 + ADR-452 — open-by-format routing + the Studio landing.

Structural gate, pure-Python (source inspection over api + web). Run directly:
`python test_adr452_studio_landing.py` (the ADR-415 __main__ lesson).

Asserts:
  ADR-451 (the surface-owning app):
   1. file-types exports resolveSurfaceApplication; Studio claims html; the
      inbound/ carve (arrivals stay preview); null → unclaimed.
   2. The Files open path consults it and routes via navigateToSurface; the
      chat FileOpenModal is NOT branched (in-conversation preview stands).
  ADR-452 (the landing + the entrance move):
   3. The Files context-menu entrance is GONE: no onLearnFrom anywhere in
      the Files surface or FileVerbs; LearnFromModal is deleted.
   4. The stacked-menus defect is fixed: openCanvasMenu ignores
      already-claimed (defaultPrevented) events.
   5. The landing: StudioStart carries the Learn-from section (LEARN_TARGETS
      with the three studio-shaped targets), the source picker, and
      thumbnail recents (sandboxed scaled srcDoc render).
   6. The studio flow creates ONE lane with BOTH bindings (artifact_path +
      derive_recipe/derive_source); design-system routes to chat.
   7. The derive-bound lane leads with its Learn-from starter chip.
   8. Backend: the deck recipe exists; build_derive_section takes
      artifact_path; lane_runner passes it (the studio override reaches the
      posture).
"""

import os
import re
import sys

_HERE = os.path.dirname(__file__)
_WEB = os.path.join(_HERE, "..", "web")


def _read(rel: str) -> str:
    p = os.path.join(_WEB, rel)
    return open(p, encoding="utf-8").read() if os.path.exists(p) else ""


def _check(label, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}")
    return bool(ok)


def run() -> int:
    passed = True

    file_types = _read("lib/file-types/index.ts")
    files_page = _read("app/(authenticated)/files/page.tsx")
    ctx_menu = _read("components/workspace/FileContextMenu.tsx")
    studio = _read("components/studio/StudioSurface.tsx")
    flow = _read("components/studio/LearnFromFlowModal.tsx")
    new_artifact = _read("components/studio/NewArtifactModal.tsx")
    open_modal = _read("components/chat-surface/FileOpenModal.tsx")

    # ── 1. the resolver ───────────────────────────────────────────────────
    passed &= _check(
        "resolveSurfaceApplication exists; Studio claims html",
        "export function resolveSurfaceApplication" in file_types
        and "surface: 'studio'" in file_types,
    )
    passed &= _check(
        "arrivals carve: inbound/ html stays preview",
        "isArrival" in file_types and "/inbound/" in file_types,
    )

    # ── 2. the Files open branch ──────────────────────────────────────────
    # NOTE (2026-07-24): the call gained a `kind` arg at ADR-473
    # (`resolveSurfaceApplication(path, undefined, kind)`), so match the verb
    # name + its navigate, not the stale 1-arg literal this asserted before.
    passed &= _check(
        "Files open path consults the resolver + navigates",
        "resolveSurfaceApplication(path" in files_page
        and "navigateToSurface(app.surface, { [app.param]: path })" in files_page,
    )
    passed &= _check(
        "chat FileOpenModal NOT branched (ADR-441 preview stands)",
        bool(open_modal) and "resolveSurfaceApplication" not in open_modal,
    )
    # 2026-07-24 (Option A) — THE ONE DOOR invariant. Every way a member opens
    # a file routes through one funnel (openPath), which consults the resolver
    # once. The pre-cleanup shape resolved per-call-site, so each new door had to
    # REMEMBER to — the tree forgot (Studio artifact blank inline), then the two
    # deep-link jumps forgot (a shared link blank). Same bug three times = a
    # missing funnel. These assertions defend the funnel, not any single door.

    # (a) the funnel exists and is the one open verb.
    passed &= _check(
        "openPath funnel exists (THE ONE DOOR)",
        "const openPath = useCallback((path: string) =>" in files_page,
    )

    # (b) the tree's node-select wrapper DELEGATES to openPath — a re-added inline
    # `setSelectedPath(node.path)` body is the original regression.
    wrapper = re.search(
        r"const handleExplorerSelect = useCallback\(\s*\(node: TreeNode\) =>(.*?),\s*\[",
        files_page,
        re.DOTALL,
    )
    delegates = bool(wrapper) and "openPath(node.path)" in wrapper.group(1)
    passed &= _check(
        "tree select delegates to the funnel (openPath), not an inline set",
        delegates,
        "" if delegates else "handleExplorerSelect must wrap openPath(node.path)",
    )

    # (c) the tree + folder-listing are wired to that verb.
    passed &= _check(
        "the tree + folder-listing are wired to the open verb",
        "onSelect={handleExplorerSelect}" in files_page
        and "onNavigate={handleExplorerSelect}" in files_page,
    )

    # (d) the deep-link doors (cold-load seed + post-mount `?files.path=` jump)
    # route through the funnel via openPathRef — NOT a raw setSelectedPath, which
    # would render a shared artifact link blank inline (the third instance of the
    # bug the audit found).
    passed &= _check(
        "deep-link jumps route through the funnel (openPathRef)",
        "openPathRef.current = openPath" in files_page
        and files_page.count("openPathRef.current(") >= 2,
    )

    # (e) the closing invariant: the ONLY raw setSelectedPath(<a path variable>)
    # OPEN sites are the funnel's own selectInline + the two allowlisted
    # Details-scoping sites (Get Info / Properties select-to-inspect, not open).
    # Every other setSelectedPath is a CLEAR (setSelectedPath(null)) or a
    # selection-preservation updater (setSelectedPath((prev) => …)). A new
    # bare setSelectedPath(<path>) open door outside the allowlist trips this.
    #   allowlisted open-path setters, by their surrounding token:
    #     selectInline    → setSelectedPath(path)          (the funnel terminal)
    #     handleGetInfo   → setSelectedPath(node.path)     (scope Details)
    #     onProperties    → setSelectedPath(t.path)        (scope Details)
    open_setters = re.findall(r"setSelectedPath\((?!null|\(prev)([^)]+)\)", files_page)
    allowed = {"path", "node.path", "t.path"}
    stray = [s.strip() for s in open_setters if s.strip() not in allowed]
    passed &= _check(
        "no un-allowlisted setSelectedPath(<path>) open door outside the funnel",
        not stray,
        "" if not stray else f"stray open setters: {stray}",
    )

    # ── 3. the entrance move ──────────────────────────────────────────────
    passed &= _check(
        "no Learn-from in the Files surface / verbs / menu",
        "onLearnFrom" not in files_page and "onLearnFrom" not in ctx_menu,
    )
    passed &= _check(
        "LearnFromModal deleted",
        not os.path.exists(os.path.join(_WEB, "components/workspace/LearnFromModal.tsx")),
    )

    # ── 4. Finder-flat: no stacked menus ──────────────────────────────────
    passed &= _check(
        "canvas menu ignores claimed events",
        "if (e.defaultPrevented) return;" in files_page,
    )

    # ── 5. the landing ────────────────────────────────────────────────────
    passed &= _check(
        "LEARN_TARGETS: the three studio-shaped targets",
        "LEARN_TARGETS" in studio
        and "recipe: 'prd'" in studio
        and "recipe: 'deck'" in studio
        and "recipe: 'design-system'" in studio,
    )
    # v2: ONE creation grid — type cards + Learn-from as peers; details nest in
    # focused modals (scratch → name-it; learn-from → source-first flow with
    # the upload leg). The target-first SourcePickerModal is superseded.
    passed &= _check(
        "v2: learn-from flow modal exists (source-first) and the landing mounts it",
        "LearnFromFlowModal" in flow and "<LearnFromFlowModal" in studio,
    )
    passed &= _check(
        "v2: the source has two answers — workspace file OR upload",
        "recentRevisions" in flow and "api.documents.upload" in flow,
    )
    passed &= _check(
        "v2: scratch creation nests in the name-it modal (no landing form fields)",
        "NewArtifactModal" in new_artifact and "<NewArtifactModal" in studio
        and "Name it (e.g. IR deck v3)" not in studio,
    )
    passed &= _check(
        "v2: SourcePickerModal superseded (deleted)",
        not os.path.exists(os.path.join(_WEB, "components/studio/SourcePickerModal.tsx")),
    )
    passed &= _check(
        "thumbnail recents: sandboxed scaled srcDoc render",
        "ArtifactThumb" in studio and 'sandbox=""' in studio and "srcDoc" in studio,
    )

    # ── 6. the double-bound creation flow ─────────────────────────────────
    passed &= _check(
        "studio flow: one lane, both bindings",
        "artifact_path: res.path" in studio
        and "derive_recipe: target.recipe" in studio
        and "derive_source: source.path" in studio,
    )
    passed &= _check(
        "design-system target routes to chat",
        "navigateToSurface('chat', { lane: lane.id })" in studio,
    )

    # ── 7. the starter chip ───────────────────────────────────────────────
    passed &= _check(
        "derive-bound lane leads with the Learn-from chip",
        "boundLane.derive_source" in studio and "Learn from ${baseName(boundLane.derive_source)}" in studio,
    )

    # ── 8. backend ────────────────────────────────────────────────────────
    import inspect

    from services.derive_recipes import DERIVE_RECIPES, build_derive_section

    passed &= _check("deck recipe registered", "deck" in DERIVE_RECIPES)
    passed &= _check(
        "build_derive_section takes artifact_path",
        "artifact_path" in inspect.signature(build_derive_section).parameters,
    )
    from services import lane_runner

    conv_src = inspect.getsource(lane_runner.build_lane_conventions)
    passed &= _check(
        "lane_runner threads artifact_path into the derive section",
        "build_derive_section(" in conv_src and "artifact_path=artifact_path" in conv_src,
    )

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(run())

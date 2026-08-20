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


def _strip_comments(src: str) -> str:
    """Drop // line-comments and /* */ blocks.

    Every text assertion below runs on the STRIPPED source. Without this a gate
    can match its OWN explanatory comment — the failure mode that let the first
    cut of the select/open assertions pass against reverted code, because the
    words "coarse" and "detail" survived in the prose describing them. Code
    only, or the gate is testing its own documentation.
    """
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", "", src)


def _check(label, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}")
    return bool(ok)


def run() -> int:
    passed = True

    file_types = _read("lib/file-types/index.ts")
    files_page = _read("app/(authenticated)/files/page.tsx")
    ctx_menu = _read("components/workspace/FileContextMenu.tsx")
    studio = _read("components/authoring/StudioSurface.tsx")
    flow = _read("components/authoring/LearnFromFlowModal.tsx")
    new_artifact = _read("components/authoring/NewArtifactModal.tsx")
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
    # NOTE (2026-07-24): the call gained a `kind` arg at ADR-473.
    # NOTE (2026-08-04): ADR-514 D2 merged the two registries into ONE ordered
    # handler set — openPath now consults `resolveHandlers` (+ the D2.4
    # override) and navigates on the chosen handler's own declaration. The
    # invariant this defends is unchanged: the funnel consults the shared
    # resolver and navigates to the owning app; only the resolver's name moved.
    passed &= _check(
        "Files open path consults the resolver + navigates",
        "resolveHandlers({ paths: [path]" in files_page
        and "navigateToSurface(chosen.open.surface, { [chosen.open.param]: path })"
        in files_page,
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

    # (b) the click wrapper DELEGATES to openPath — a re-added inline open body
    # is the original regression.
    #
    # RE-ANCHORED 2026-08-20 (the selection model). This assertion has twice
    # pinned a SPELLING and twice gone stale silently — it matched the parameter
    # list `(node: TreeNode) =>`, then the name `handleExplorerSelect`, both of
    # which stopped existing. Find the callback by NAME (it is now
    # `handleFileClick`, one grammar for both panes) and assert on what its body
    # DOES, not how it is spelled.
    wrapper = re.search(
        r"const handleFileClick = useCallback\((.*?)\n  \);",
        files_page,
        re.DOTALL,
    )
    body = wrapper.group(1) if wrapper else ""
    # It must call the funnel...
    calls_funnel = "openPath(" in body
    # ...and must NOT hand-roll the funnel's terminal inline. `activateBodyRef`
    # is the drill-in that only an OPEN performs; a select-only branch sets the
    # selection without it. An inline pairing here is the funnel being bypassed.
    inlines_open = "activateBodyRef" in body
    delegates = bool(wrapper) and calls_funnel and not inlines_open
    passed &= _check(
        "the click wrapper delegates to the funnel (openPath), not an inline open",
        delegates,
        ""
        if delegates
        else (
            "handleFileClick not found"
            if not wrapper
            else f"calls openPath={calls_funnel} inlines activateBodyRef={inlines_open}"
        ),
    )

    # (b2) THE SPLIT (2026-08-20): select and open are distinct acts on a fine
    # pointer. The FULL selection grammar (single/⌘/shift/Enter/Escape, and the
    # fact that a plain click renders nothing new) is gated on its own in
    # test_files_selection_model.py; what THIS gate defends is the part that
    # touches the open funnel — that an open still goes through one door and
    # that the pointer branch is on CAPABILITY, never width.
    #
    # Asserted over COMMENT-STRIPPED source: a gate can otherwise match its own
    # explanatory prose (the words "coarse" and "detail" survive in comments
    # describing them), which is how the first cut of these assertions passed
    # against reverted code.
    code = _strip_comments(files_page)
    body_code = _strip_comments(body)

    # The gesture must be COMPUTED from the event's click counter — a literal
    # (`= true`) or a missing read is the pre-split "a click always opens" shape.
    dbl = re.search(r"const isDoubleClick = \(e\?\.detail \?\? 0\) >= 2;", body_code)
    passed &= _check(
        "select/open split: open is computed from the click counter (detail >= 2)",
        dbl is not None,
        "isDoubleClick must be derived from e.detail, not hardcoded",
    )
    # Both outcomes must be reachable: an open branch AND a select-only branch.
    passed &= _check(
        "select/open split: both outcomes exist (openPath AND a select-only path)",
        "openPath(node.path)" in body_code and "selectOne(node.path)" in body_code,
    )
    # The open CONDITION itself is the thing under test — capture it once and
    # assert on its disjuncts, so a dropped term cannot hide behind the same
    # token appearing elsewhere in the callback.
    cond = re.search(r"if \((coarse [^)]*?)\) \{\s*openPath\(node\.path\);", body_code)
    cond_txt = cond.group(1) if cond else ""
    passed &= _check(
        "select/open split: the branch reads pointer capability, not width",
        "useCoarsePointer()" in code
        and cond is not None
        and "coarse" in cond_txt
        and "isMobile" not in body_code,
        f"open condition={cond_txt!r} — must consult coarse, never useViewport().isMobile",
    )
    passed &= _check(
        "select/open split: the open condition consults the click counter",
        "isDoubleClick" in cond_txt,
        f"open condition={cond_txt!r}",
    )
    # RE-ANCHORED 2026-08-20 (the TWO-PANE recut). This asserted that the open
    # condition carried a SOURCE-QUALIFIED folder disjunct (`treeFolder`) — a
    # tree folder opens on click one, a listing folder does not.
    #
    # That disjunct is DELETED, and its deletion is the fix. The left tree is a
    # NAVIGATOR (folders only, one click navigates); the centre pane is the file
    # browser. A click handler that had to be told which pane called it was two
    # handlers wearing one name, and the shared half bled a selection into a
    # pane with nothing to select — the operator met it as a floating chip
    # raised by clicking a FILE IN THE TREE.
    #
    # The claim this gate actually owns is unchanged: THE LISTING's folders must
    # not open on click one, or the grid loses its selection. Asserted directly
    # now (no folder term in the open condition at all) rather than through a
    # discriminator that no longer exists.
    passed &= _check(
        "select/open split: NO folder disjunct — a listing folder never opens on click one",
        "folder" not in cond_txt and "treeFolder" not in body_code,
        f"open condition={cond_txt!r} — must be pointer + click-counter only",
    )
    # The keyboard equivalent double-click does not have — the a11y answer.
    passed &= _check(
        "select/open split: Enter opens the current selection",
        "e.key !== 'Enter'" in code and "openPathRef.current(" in code,
    )
    # RE-ANCHORED 2026-08-20 (the TWO-PANE recut). Two assertions stood here —
    # "the tree forwards the click counter + modifiers" and "the tree still
    # toggles folder disclosure on a single click". Both described a tree that
    # participated in the selection grammar. It does not: it renders FOLDERS
    # ONLY and its single click means exactly one thing (navigate + unfold), so
    # there are no modifiers to forward and no set-gesture to keep out of the
    # disclosure's way.
    #
    # The claim that replaces them is the one the whole recut rests on, scoped
    # to what THIS gate owns (the open funnel): the tree's gesture routes
    # through THE ONE DOOR like every other open, rather than reaching into the
    # surface's state itself. The folders-only rendering and the absent
    # selection are gated in test_files_selection_model.py (claim 10).
    tree_code = _strip_comments(_read("components/workspace/WorkspaceTree.tsx"))
    passed &= _check(
        "the tree's navigate routes through the ONE DOOR (openPath), not into state",
        re.search(
            r"const navigateToFolder = useCallback\(\(node: TreeNode\) => \{ openPath\(node\.path\); \}",
            code,
        )
        is not None,
    )
    passed &= _check(
        "the tree carries no click-intent and no selection (it is a navigator)",
        "FileClickIntent" not in tree_code and "selection" not in tree_code,
    )

    # (c) the tree + folder-listing are wired to that verb.
    passed &= _check(
        "the tree + folder-listing are wired to their OWN grammars",
        "onNavigate={navigateToFolder}" in files_page
        and "onNavigate={handleListingClick}" in files_page
        and "handleTreeClick" not in files_page,
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

    # (e) the closing invariant, RE-ANCHORED 2026-08-20 (the selection model).
    #
    # An earlier shape allowlisted the open-setter by the SPELLING of its
    # argument, which is not a property of the code — it is a property of local
    # variable names, and it started reporting legitimate SELECTS as open-door
    # regressions the moment selects became the point.
    #
    # What actually distinguishes an OPEN from a SELECT in this surface is the
    # DRILL-IN: `activateBodyRef.current()` — the narrow-viewport act of entering
    # the shown object. `showInline` (the funnel's terminal) pairs it with
    # `setViewPath`; a SELECT touches neither.
    #
    # So the invariant is: every drill-in belongs to the funnel or to an
    # explicitly-reasoned non-file site. Any NEW pairing outside the funnel is a
    # second open door, and trips this.
    #
    # Sanctioned drill-in sites (counted, not name-matched) — 5:
    #   openPath/showInline    — the funnel terminal (the ONE door)
    #   openWith               — the ADR-514 D2.2 "Open With ▸" non-default handler
    #   handleUploaded         — post-upload reveal; itself calls openPath, the
    #                            drill only finishes the narrow-viewport move
    #   the two rail buttons   — setViewPath(NULL) + drill: leaving a file for
    #                            the root/Trash listing, which opens no file
    #
    # A ceiling, not an equality: a REMOVED door should not fail the gate, only
    # an ADDED one.
    drill_sites = files_page.count("activateBodyRef.current()")
    passed &= _check(
        "no new drill-in (open) door outside the funnel",
        drill_sites <= 5,
        f"activateBodyRef drill-in sites={drill_sites} (expected <= 5: funnel, openWith, upload reveal, 2 rail clears)",
    )
    # And the funnel's terminal is still the one that moves what is SHOWN.
    passed &= _check(
        "the funnel's terminal still pairs the view move + drill",
        re.search(
            r"const showInline = \(isFolder: boolean\) => \{.*?setViewPath\(path\);.*?activateBodyRef\.current\(\)",
            files_page,
            re.DOTALL,
        )
        is not None,
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
        not os.path.exists(os.path.join(_WEB, "components/authoring/SourcePickerModal.tsx")),
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

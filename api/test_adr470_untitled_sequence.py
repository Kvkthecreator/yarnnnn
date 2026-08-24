"""ADR-549 — a creation act names its object (supersedes ADR-470's two doors).

ADR-470 split creation into an IMMEDIATE door (pick a shape, get the workbench,
born "Untitled ‹kind›") and a DELIBERATE one ("Name it first…"). Those did not
name two things a member could want — they named ONE thing and a TOLL, and the
fast one left litter: `operation/asdfadsf/document.html`, permanent and
attributed, because nothing ever asked what it was.

ADR-549 collapses them. `+ New` picks a SHAPE and opens one dialog that requires
a name and defaults the location. What survives from ADR-470 unchanged:
  • §5 — there is no Save, and there must not be (every keystroke is already an
    attributed revision). This is WHY the "temp file deleted unless saved"
    alternative was refused: it needs an unsaved state the substrate lacks.
  • D2's reasoning about invented names — preserved and now unreachable.
And from ADR-469: the name is lifted to <title>, the path is only a key, and a
collision DISAMBIGUATES rather than refusing.

Run: python3 test_adr470_untitled_sequence.py   (check()-style, NOT pytest)
"""

import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

_pass = 0
_fail = 0


def _check(label: str, cond: bool) -> None:
    global _pass, _fail
    if cond:
        _pass += 1
        print(f"[PASS] {label}")
    else:
        _fail += 1
        print(f"[FAIL] {label}")


def _h1(html: str):
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
    return re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else None


def main() -> int:
    from services.naming import disambiguate, path_slug
    import services.apps  # noqa: F401 — registration side-effect (ADR-599: docs deleted)
    from services.authoring import (
        all_layouts,
        all_templates,
        artifact_name,
        extract_title,
        resolve_layout,
        set_artifact_title,
    )

    root = pathlib.Path(__file__).parent.parent
    routes = (root / "api/routes/studio.py").read_text()
    menu = (root / "web/components/authoring/StudioNewMenu.tsx").read_text()
    surface = (root / "web/components/authoring/StudioSurface.tsx").read_text()
    modal = (root / "web/components/authoring/NewArtifactModal.tsx").read_text()
    client = (root / "web/lib/api/client.ts").read_text()

    print("── 1. THE UNTITLED ARTIFACT renders correctly, unnamed ────────")
    # ADR-518: swept across the REGISTRY (Docs' document + Studio's deck/web +
    # the IMAGES stage) so the flow medium keeps its coverage after the carve.
    for slug, lay in all_layouts().items():
        sk = all_templates()[slug]["skeleton"]
        expect = f"Untitled {lay['label'].lower()}"
        _check(f"{slug}: <title> is the placeholder", extract_title(sk) == expect)
        # It must read back as "Untitled ‹kind›" AT ITS REAL PLACEMENT — the
        # server-assigned `untitled-‹kind›` key from _untitled_path.
        #
        # Browser-tested amendment (2026-07-20): a placeholder title is NOT a
        # name, so `artifact_name` now falls THROUGH it to the folder. Asserting
        # against a fabricated path would test the pre-amendment rule. At the
        # real key the folder titleizes to the same string, so the member-facing
        # invariant is unchanged — and a disambiguated key reads
        # "Untitled document 2", which distinguishes repeat News in Recents.
        real = f"/workspace/operation/untitled-{lay['label'].lower()}/{slug}.html"
        _check(f"{slug}: reads back as '{expect}' at its real placement",
               artifact_name(real, sk) == expect)

    print("\n── 1b. A PLACEHOLDER TITLE IS NOT A NAME (browser-found) ──────")
    # A pre-ADR-469 artifact never got its typed name written into <title>, so
    # it kept the skeleton placeholder while its FOLDER held the real name. Once
    # the lift made content win, such a file read as "Untitled document" — and a
    # member clicking a card so labelled opened `prd-for-yarnnn`. Found by
    # browser test 2026-07-20; one live file was affected.
    # ADR-599: the `document` LAYOUT is deleted with Docs, but the DATA it
    # scaffolded persists — live pre-599 artifacts still carry the "Untitled
    # document" placeholder, so the fall-through must keep firing for them
    # (`_LEGACY_SCAFFOLD_TITLES` in authoring.py — deleting the layout must
    # not resurrect the pre-ADR-469 defect on existing files). The checks now
    # run against a minimal legacy-document body instead of the retired
    # template.
    doc_sk = "<html><head><title>Untitled document</title></head><body></body></html>"
    _check(
        "a LEGACY stale placeholder falls THROUGH to the real folder name",
        artifact_name("/workspace/operation/prd-for-yarnnn/document.html", doc_sk)
        == "Prd for yarnnn",
    )
    _check(
        "a genuinely authored title still wins over the folder",
        artifact_name(
            "/workspace/operation/whatever/document.html",
            doc_sk.replace("<title>Untitled document</title>", "<title>IR deck v3</title>"),
        )
        == "IR deck v3",
    )
    _check(
        "a disambiguated untitled key reads distinctly (Untitled document 2)",
        artifact_name("/workspace/operation/untitled-document-2/document.html", doc_sk)
        == "Untitled document 2",
    )

    print("\n── 1c. THE PAGED NAME-BEARER IS THE KICKER (2026-08-12) ───────")
    # Operator click-pass: a deck created as "deck new test" rendered
    # "UNTITLED DECK" on its own title slide while the tab, the crumb and the
    # Files row all said otherwise. The paged scaffolds carry the name a SECOND
    # time in their `k1` kicker, and nothing wrote it — invisible until ADR-549,
    # because everything used to be BORN "Untitled deck".
    #
    # Reproduces the ROUTE's call exactly (`set_h1=is_flow`), not build_skeleton's
    # default — the two differ on paged, which is the whole point.
    def _k1(html: str):
        m = re.search(r'data-block-id="k1"[^>]*>(.*?)</p>', html, re.S)
        return re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else None

    for slug, lay in all_layouts().items():
        sk = all_templates()[slug]["skeleton"]
        is_flow = lay["mode"] == "flow"
        named = set_artifact_title(sk, "deck new test", set_h1=is_flow)
        if _k1(sk) is None:
            continue  # flow layouts ship no kicker — nothing to bear the name
        _check(
            f"{slug}: the kicker takes the typed name (not 'Untitled {lay['label'].lower()}')",
            _k1(named) == "deck new test",
        )
        # …and the paged h1 is STILL the thesis. The kicker fix must not smuggle
        # the filename into authored content — that is ADR-459's whole rule, and
        # the reason `set_h1` is False here in the first place.
        if not is_flow:
            _check(
                f"{slug}: the h1 thesis is UNTOUCHED (a filename dictates no content)",
                _h1(named) == _h1(sk),
            )

    # An AUTHORED kicker is never overwritten — the same placeholder guard the
    # h1 uses, so a member's words survive every later rename.
    _deck_sk = all_templates()["deck"]["skeleton"]
    _authored = _deck_sk.replace(">Untitled deck<", ">ACME CORP<")
    _check(
        "an AUTHORED kicker survives a rename",
        _k1(set_artifact_title(_authored, "new name", set_h1=False)) == "ACME CORP",
    )
    # A content-PROMPT kicker ("Kicker", "Part", "Thank you") lives on ordinary
    # inserted slides. Those are not the artifact's name and must not take it.
    for _prompt in ("Kicker", "Part", "Thank you"):
        _other = _deck_sk.replace(">Untitled deck<", f">{_prompt}<")
        _check(
            f"a content-prompt kicker ({_prompt!r}) is NOT treated as the name",
            _k1(set_artifact_title(_other, "new name", set_h1=False)) == _prompt,
        )
    # The placeholder set is DERIVED from the scaffolds, never hand-listed —
    # a new app's layout registers its own kicker through the one door.
    from services.authoring import _SCAFFOLD_KICKERS

    _check(
        "the kicker placeholder set is derived at registration, not hand-listed",
        bool(_SCAFFOLD_KICKERS)
        and all(
            _scaf in _SCAFFOLD_KICKERS
            for _scaf in (_k1(r["scaffold"]) for r in all_layouts().values())
            if _scaf
        ),
    )

    print("\n── 2. THE PLACEHOLDER GUARD — why we must NOT invent a name ───")
    # THE TRAP this ADR avoids: writing an invented name at create (e.g. one
    # derived from the path) makes the h1 look AUTHORED, so set_artifact_title's
    # placeholder guard then refuses to replace it — the member's later rename
    # would silently no-op on the h1, forever.
    doc = all_templates()["deck"]["skeleton"]  # ADR-599: document deleted; the guard is layout-agnostic
    renamed_from_placeholder = set_artifact_title(doc, "My real name", set_h1=True)
    _check(
        "a rename REPLACES the untouched placeholder (the offer works)",
        _h1(renamed_from_placeholder) == "My real name",
    )
    invented = set_artifact_title(doc, "Untitled deck 2", set_h1=True)
    _check(
        "…but an INVENTED name is frozen: the guard treats it as authored",
        _h1(set_artifact_title(invented, "My real name", set_h1=True)) == "Untitled deck 2",
    )
    _check(
        "so creation leaves the skeleton alone when no name is given",
        "else template[\"skeleton\"]" in routes,
    )

    print("\n── 3. PLACEMENT: the server owns the KEY, the caller the DEST ──")
    # ADR-549 D1 — there is no pathless door. A caller that sends no path has
    # skipped a question, not chosen a default, so it is REFUSED rather than
    # silently placed at `untitled-<kind>/`.
    def _body(fn_name: str) -> str:
        m = re.search(
            rf"\ndef {fn_name}\(.*?(?=\n(?:@router|def |async def ))",
            routes,
            re.DOTALL,
        )
        return m.group(0) if m else ""

    _handler = re.search(
        r"async def create_artifact\(.*?(?=\n@router|\Z)", routes, re.DOTALL
    )
    _handler_body = _handler.group(0) if _handler else ""
    # Asserted on the BRANCH, not on "is 422 anywhere in the handler" — the
    # handler has other 422s (a non-.html path, a traversal), so a presence
    # check stayed GREEN while the pathless door was restored. Read what the
    # empty-path branch actually DOES: it must raise, not assign a path.
    _empty_branch = re.search(
        r"\n    if not raw:\n(.*?)(?=\n    path = )", _handler_body, re.DOTALL
    )
    _check(
        "a pathless create is REFUSED, not placed (no untitled door)",
        bool(_empty_branch) and "raise HTTPException" in _empty_branch.group(1),
    )
    _check(
        "no `untitled <kind>` key is generated anywhere",
        'f"untitled {label}"' not in routes,
    )
    # The named door still disambiguates — ADR-469 D4 survives the collapse.
    # Asserted INSIDE the function body, not by counting the module: two weaker
    # spellings both stayed green while the call was deleted outright (the
    # import lines made one count; an unrelated third call made the other).
    _named_door = _body("_redirect_to_free_key")
    _check(
        "the create door disambiguates (a taken key steps, never refuses)",
        "disambiguate(" in _named_door,
    )
    _check(
        "it reuses ADR-469's path_slug + disambiguate (no second key rule)",
        "from services.naming import disambiguate, path_slug" in routes
        and "disambiguate(base, taken)" in routes,
    )
    # DP33 — the state is data (the placeholder title it carries), the
    # namespace stays meaning. Assert on the PRODUCED PATH, not on source text:
    # a grep-only check missed that STUDIO_ARTIFACT_REGION already ends in "/",
    # so an appended slash yielded `/workspace/operation//untitled-document/…`.
    from services.authoring import STUDIO_ARTIFACT_REGION

    def _untitled_path_pure(template: str, existing: list[str]) -> str:
        # Mirrors the route's own lookup (resolve_layout — registry-wide since
        # ADR-518), never a single app's table.
        lay = resolve_layout(template)
        label = lay["label"].lower() if lay else template
        base = path_slug(f"untitled {label}")
        prefix = STUDIO_ARTIFACT_REGION
        taken = {
            rest.split("/")[0]
            for rest in (p[len(prefix):] for p in existing if p.startswith(prefix))
            if rest and "/" in rest
        }
        return f"{prefix}{disambiguate(base, taken)}/{template}.html"

    produced = _untitled_path_pure("document", [])
    _check(
        "it lands in the ORDINARY region, not a drafts/ namespace (DP33)",
        produced.startswith(STUDIO_ARTIFACT_REGION) and "/drafts/" not in produced,
    )
    _check(
        "the produced path has NO double slash (the region carries its own)",
        "//" not in produced.lstrip("/") and produced.count("//") == 0,
    )
    _check(
        "the produced path is exactly region/key/template.html",
        produced == f"{STUDIO_ARTIFACT_REGION}untitled-document/document.html",
    )
    _check(
        "the helper never appends a slash to the region",
        'f"{STUDIO_ARTIFACT_REGION}/"' not in routes,
    )
    # And it must respect what's already there, across repeats.
    _seen: list[str] = []
    for _ in range(3):
        _seen.append(_untitled_path_pure("document", _seen))
    _check("repeated New produces 3 distinct real paths", len(set(_seen)) == 3)
    for slug, lay in all_layouts().items():
        base = path_slug(f"untitled {lay['label'].lower()}")
        taken: set[str] = set()
        keys: list[str] = []
        for _ in range(3):
            k = disambiguate(base, taken)
            taken.add(k)
            keys.append(k)
        _check(
            f"{slug}: repeated New yields distinct keys {keys[0]}/{keys[1]}/{keys[2]}",
            len(set(keys)) == 3 and keys[0] == f"untitled-{lay['label'].lower()}",
        )

    print("\n── 4. ONE DOOR, and it asks (ADR-549 D1) ──────────────────────")
    # Comment-stripped: the ABSENCE assertion below matches its own explanatory
    # comment otherwise (the surface's "`createUntitled` … is DELETED" note
    # contains the very name it forbids). The
    # feedback_gate_assertion_matches_its_own_comment shape, caught live.
    _surface_code = re.sub(r"/\*[\s\S]*?\*/", "", surface)
    _surface_code = re.sub(r"(^|[^:])//[^\n]*", r"\1", _surface_code)
    _check(
        "picking a shape opens the DIALOG, never creates outright",
        "setNamingOpen(true)" in _surface_code and "createUntitled" not in _surface_code,
    )
    _check(
        "the second row is GONE — no name-it-first, no onPickNamed",
        "onPickNamed" not in menu and "Name it first" not in menu.split("*/")[-1],
    )
    # Asserted on the SELECTION EXPRESSION, not on the prop's presence. The
    # first spelling — `"initialTemplate" in modal and ... in surface` — stayed
    # GREEN while the reset effect was reverted to `templates[0]`, i.e. while
    # Studio silently opened on Deck no matter which shape you picked. The prop
    # was threaded and then discarded: wired but not READ, the same shape as
    # ADR-541 D4's exported-never-mounted notice.
    #
    # Studio is the only app with two shapes (deck + web), so it is the only
    # place this is observable — which is exactly why it needs a gate.
    _reset = re.search(r"const picked = [\s\S]{0,200}?setTemplateSlug\([^\n]*\);", modal)
    _check(
        "the dialog opens ON the shape the menu chose (the prop is READ)",
        bool(_reset)
        and "initialTemplate" in _reset.group(0)
        and "picked" in _reset.group(0).split("setTemplateSlug")[1],
    )
    _check(
        "…and the surface actually passes it (a read prop nobody sends is moot)",
        "initialTemplate={namingTemplate}" in surface,
    )
    _check(
        "the deliberate modal owns all three decisions (shape too)",
        "templates: TemplateChoice[] | null" in modal and "setTemplateSlug" in modal,
    )
    _check(
        "learn-from sends its SOURCE as the name (it isn't untitled)",
        "name: sourceName," in surface,
    )
    _check(
        "the client exposes one create with both doors",
        # ADR-472 widened the signature across lines (a stage also carries its
        # dimensions), so assert the INVARIANT — one createArtifact taking a
        # template plus an optional bag holding BOTH doors' fields — rather
        # than one line's exact formatting.
        "createArtifact: (" in client
        and "template: string," in client
        and "opts?: {" in client
        and "path?: string;" in client
        and "name?: string;" in client,
    )
    # Singular implementation: the old always-a-modal state is gone.
    _check(
        "the old per-creation modal state is DELETED (no scratchTemplate)",
        "scratchTemplate" not in surface,
    )

    print(f"\n{'PASS' if _fail == 0 else 'FAIL'}: {_pass}/{_pass + _fail} checks")
    return 1 if _fail else 0


if __name__ == "__main__":
    raise SystemExit(main())

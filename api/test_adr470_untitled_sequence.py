"""ADR-470 — New should not interrogate you: the untitled sequence.

The defect: New demanded a name AND a destination before it handed over
anything, unlike every doc processor whose blank state IS the "untitled"
handling. A SEQUENCE defect, felt at the moment of highest intent.

The fix: two doors into one artifact.
  • IMMEDIATE  — pick a shape, get the workbench. Born "Untitled ‹kind›" at a
                 server-placed disambiguated key; the crumb arms so the name is
                 OFFERED, never demanded.
  • DELIBERATE — "Name it first…" keeps the modal, which now owns all three
                 decisions (shape + name + destination).

What made it possible: ADR-469 severed the name from the path. Under ADR-459 D2
the name came from the folder slug, so naming later meant MOVING the folder.

Run: python3 test_adr470_untitled_sequence.py   (check()-style, NOT pytest)
"""

import pathlib
import re
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
    import services.docs  # noqa: F401 — registers the document row (ADR-518)
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
    doc_sk = all_templates()["document"]["skeleton"]
    _check(
        "a stale placeholder falls THROUGH to the real folder name",
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

    print("\n── 2. THE PLACEHOLDER GUARD — why we must NOT invent a name ───")
    # THE TRAP this ADR avoids: writing an invented name at create (e.g. one
    # derived from the path) makes the h1 look AUTHORED, so set_artifact_title's
    # placeholder guard then refuses to replace it — the member's later rename
    # would silently no-op on the h1, forever.
    doc = all_templates()["document"]["skeleton"]
    renamed_from_placeholder = set_artifact_title(doc, "My real name", set_h1=True)
    _check(
        "a rename REPLACES the untouched placeholder (the offer works)",
        _h1(renamed_from_placeholder) == "My real name",
    )
    invented = set_artifact_title(doc, "Untitled document 2", set_h1=True)
    _check(
        "…but an INVENTED name is frozen: the guard treats it as authored",
        _h1(set_artifact_title(invented, "My real name", set_h1=True)) == "Untitled document 2",
    )
    _check(
        "so creation leaves the skeleton alone when no name is given",
        "else template[\"skeleton\"]" in routes,
    )

    print("\n── 3. PLACEMENT is the server's, and reuses ONE key rule ──────")
    # Asserted as a BEHAVIOUR, not a name. This check read `def _untitled_path(`
    # and went red on the 2026-08-11 rename to `_placed_path` — a gate pinning a
    # SPELLING reading a rename as a violation (the ADR-544 lesson, again). What
    # the ADR actually requires is that the SERVER owns placement: a helper that
    # composes the region + a disambiguated key, reachable from create_artifact.
    _placement_helpers = [
        line for line in routes.splitlines()
        if line.startswith("def ") and "path" in line.split("(")[0]
    ]
    _check(
        "a server-side placement helper exists (name-agnostic)",
        any("auth" in line or "template" in line for line in _placement_helpers)
        or "_placed_path(" in routes,
    )
    # And BOTH doors reach it — the 2026-08-11 amendment to D3. The named door
    # used to 409 where the unnamed one stepped to `-2`, while the helper's own
    # docstring claimed they could not drift.
    # Asserted INSIDE each door's own function body, not by counting the module.
    # Two weaker spellings were tried and BOTH stayed green while the named
    # door's disambiguation was deleted outright: `count("disambiguate(") >= 2`
    # (the import lines made the count) and then a call-shaped regex (a THIRD,
    # unrelated call at routes/studio.py:782 made it). A counting gate cannot
    # defend a per-site invariant — read the site.
    def _body(fn_name: str) -> str:
        m = re.search(
            rf"\ndef {fn_name}\(.*?(?=\n(?:@router|def |async def ))",
            routes,
            re.DOTALL,
        )
        return m.group(0) if m else ""

    _named_door = _body("_redirect_to_free_key")
    _unnamed_door = _body("_placed_path")
    _check(
        "the UNNAMED door disambiguates (a taken key steps, never refuses)",
        "disambiguate(" in _unnamed_door,
    )
    _check(
        "the NAMED door disambiguates too — D3's 'one key rule', made structural",
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

    print("\n── 4. BOTH DOORS exist, and only one asks questions ───────────")
    _check(
        "create accepts NEITHER path nor name (the immediate door)",
        "path: Optional[str] = None" in routes and "name: Optional[str] = None" in routes,
    )
    _check(
        "picking a shape CREATES immediately (no modal in between)",
        "onPickTemplate={(t) => void createUntitled(t.slug)}" in surface,
    )
    _check(
        "the immediate door opens the workbench with the crumb ARMED",
        "const createUntitled" in surface and "onRenameRequest(res.path)" in surface,
    )
    _check(
        "the deliberate door is a peer row, not a toll on every creation",
        "onPickNamed" in menu and "Name it first" in menu,
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

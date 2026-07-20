"""ADR-469 — the name is LIFTED from the artifact; the path is only a key.

The regression this pins: before ADR-469 the operator-facing name was
RECONSTRUCTED from the folder slug (ADR-459 D2), and the slug is lossy through
`[^a-z0-9]+`. Casing was the loss D2 accepted (`IR` → `Ir`). Measurement found
two worse grades it had not:

  • PARTIAL erasure — `Q3 전략 보고서` → `q3`; `café` → `caf`.
  • TOTAL erasure   — a name with no Latin characters → the literal `untitled`,
                      so FOUR distinct Korean names collided on ONE path. The
                      member's second such document could not be named at all.

The fix is ADR-459 D1's own lift pattern applied to the name: the artifact
already carries its name in `<title>` (always written, never authored), exactly
as it carries its kind in `data-template`. So the name is read from content and
the path is left to be a mere identity key.

Run: python3 test_adr462_name_is_lifted.py   (check()-style, NOT pytest)
"""

import pathlib
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


def main() -> int:
    from services.naming import FALLBACK_SLUG, MAX_SLUG_LEN, disambiguate, path_slug
    from services.studio import (
        STUDIO_TEMPLATES,
        artifact_name,
        extract_title,
        set_artifact_title,
    )

    root = pathlib.Path(__file__).parent.parent
    routes = (root / "api/routes/studio.py").read_text()
    modal = (root / "web/components/studio/NewArtifactModal.tsx").read_text()

    print("── 1. THE LIFT: the name round-trips EXACTLY ──────────────────")
    doc = STUDIO_TEMPLATES["document"]["skeleton"]
    for typed in [
        "IR deck v3",          # casing — the grade ADR-459 D2 accepted
        "한글 문서",             # total erasure — the collision case
        "Q3 전략 보고서",         # partial erasure
        "Émile résumé",        # accents
        'A & B "quoted"',      # html-escaped chars must survive the round-trip
    ]:
        html = set_artifact_title(doc, typed, set_h1=True)
        _check(
            f"round-trips {typed!r} verbatim",
            artifact_name("/workspace/operation/untitled/document.html", html) == typed,
        )

    print("\n── 2. THE FALLBACK survives (ADR-459 D2, now the 2nd source) ──")
    _check(
        "no content → the titleized meaning folder",
        artifact_name("/workspace/operation/ir-deck-v3/deck.html") == "Ir deck v3",
    )
    _check(
        "empty <title> → the folder (not an empty name)",
        artifact_name("/workspace/operation/ir-deck-v3/deck.html", "<title></title>")
        == "Ir deck v3",
    )
    _check(
        "no <title> element → the folder",
        artifact_name("/workspace/operation/ir-deck-v3/deck.html", "<p>x</p>")
        == "Ir deck v3",
    )
    _check(
        "bare region file → the titleized stem",
        artifact_name("/workspace/operation/deck.html") == "Deck",
    )
    _check("empty path → 'File'", artifact_name("") == "File")
    _check("extract_title returns None on junk", extract_title("nope") is None)

    print("\n── 3. THE KEY: injective via disambiguation ───────────────────")
    taken: set[str] = set()
    for n in ["한글 문서", "日本語", "전략", "회의록"]:
        s = disambiguate(path_slug(n), taken)
        taken.add(s)
    _check(
        "four non-Latin names → four DISTINCT keys (was: all four → 'untitled')",
        len(taken) == 4,
    )
    _check("accents FOLD rather than vanish (café → cafe, was 'caf')",
           path_slug("naïve café") == "naive-cafe")
    _check("a name with no Latin chars → the honest fallback key",
           path_slug("한글") == FALLBACK_SLUG)
    _check(
        "disambiguation respects the length cap",
        len(disambiguate(path_slug("x" * 60), {path_slug("x" * 60)})) <= MAX_SLUG_LEN,
    )
    _check("path_slug is idempotent on an already-slugged key",
           path_slug(path_slug("IR deck v3")) == path_slug("IR deck v3"))

    print("\n── 4. <title> is written for EVERY layout ─────────────────────")
    # THE REGRESSION: the retitle body used to return early on a paged layout,
    # so a renamed deck kept its OLD <title> and the landing card silently
    # reverted to the folder slug. The h1 guard is right; the title guard was
    # the bug — <title> is metadata, never authored, and is the name's home.
    deck = STUDIO_TEMPLATES["deck"]["skeleton"]
    out = set_artifact_title(deck, "한글 덱", set_h1=False)
    _check("a paged layout still gets its <title> set", extract_title(out) == "한글 덱")
    _check(
        "a paged layout's h1 (its thesis) is NOT overwritten",
        "한글 덱" not in out.split("</head>")[1],
    )
    _check(
        "the early-return on paged layouts is gone from the retitle body",
        '"reason": "not_a_flow_layout"' not in routes,
    )

    print("\n── 5. ONE implementation of the slug rule ─────────────────────")
    _check(
        "routes import the shared helper (no inlined regex)",
        "from services.naming import disambiguate, path_slug" in routes
        and 're.sub(r"[^a-z0-9]+", "-", (req.name or "").lower())' not in routes,
    )
    _check(
        "the FE mirrors it (NFKD fold, same fallback)",
        "normalize('NFKD')" in modal and "'untitled'" in modal,
    )
    _check(
        "create carries the TYPED name (not just the slugified path)",
        "name: Optional[str] = None" in routes
        and "(req.name or \"\").strip() or artifact_name(path)" in routes,
    )
    _check(
        "rename passes the typed name into the retitle",
        "_retitle_to(auth, new_path, typed)" in routes,
    )
    _check(
        "the landing lifts the name from content it ALREADY reads (no extra query)",
        'artifact_name(r["path"], r.get("content"))' in routes,
    )

    print(f"\n{'PASS' if _fail == 0 else 'FAIL'}: {_pass}/{_pass + _fail} checks")
    return 1 if _fail else 0


if __name__ == "__main__":
    raise SystemExit(main())

"""ADR-530 gate — the projection is a property of the file.

Guards the DP34 conformance this arc closes. The checks that matter are
EXECUTED, not grepped, because the defect they defend against looked like
working code: `artifact_kind = "html" if leaf.endswith(".html") else "text"`
reads fine and silently asserts that a PDF is text.

  D1  kind comes from the ONE registry dispatcher, never a call-site suffix test
  D2  extraction drops non-prose bodies and never becomes a sanitizer/inliner
  D3  a format with no strategy is MARKED, never dumped (DP34 anti-silent-drop)
  D4  the machine address is an alias: canonical Link, declared discovery
  D6  one seam — `project_for_machine` — so the stored-projection step is a swap

Run:  cd api && python3 test_adr530_machine_projection.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

WEB = Path(__file__).parent.parent / "web"


def _check(label: str, cond: bool, detail: str = "") -> bool:
    print(f"{'PASS' if cond else 'FAIL'}  {label}  {detail}")
    return bool(cond)


def _strip_comments(src: str) -> str:
    """Code only — several checks below name the very symbol they forbid, and an
    assertion that matches its own explanatory comment proves nothing."""
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    src = re.sub(r"^\s*//.*$", "", src, flags=re.MULTILINE)
    return src


def main() -> int:
    results: list[bool] = []
    from services.machine_projection import (
        extract_text_from_html,
        project_for_machine,
    )
    from services.primitives.extract_text_from_blob import registry_strategy

    shares_src = Path(__file__).parent.joinpath("routes/shares.py").read_text(encoding="utf-8")
    proj_src = Path(__file__).parent.joinpath("services/machine_projection.py").read_text(
        encoding="utf-8"
    )

    # ── D1: the registry is the dispatcher ──────────────────────────────────
    results.append(_check(
        "D1a html/htm registered as a text strategy",
        registry_strategy("html") == "text" and registry_strategy("htm") == "text"))
    results.append(_check(
        "D1b images pass through; unknown formats defer",
        registry_strategy("png") == "passthrough"
        and registry_strategy("xlsx") == "deferred"
        and registry_strategy("wat") == "deferred"))

    # The exact defect: a call-site suffix test deciding a KIND. The boundary
    # may still ask "is this html?" for RENDERING (the iframe dispatch), but it
    # must not decide readability that way — that is the registry's job.
    body = shares_src[shares_src.index("async def preview_share("):]
    results.append(_check(
        "D1c the boundary calls the seam, not a suffix test, for readability",
        "project_for_machine(" in body
        and 'endswith((".html", ".htm"))' not in body,
        "the pre-530 line asserted everything not-html IS text"))

    # ── D6: ONE seam ────────────────────────────────────────────────────────
    results.append(_check(
        "D6a exactly one projection entry point in the route",
        body.count("project_for_machine(") == 1))
    results.append(_check(
        "D6b the seam takes (path, content, file_type) so a stored projection swaps in",
        re.search(r"def project_for_machine\(\s*\*,\s*path[^)]*content[^)]*file_type", proj_src,
                  re.DOTALL) is not None))
    results.append(_check(
        "D6c no second extraction implementation in the route",
        "BeautifulSoup" not in shares_src and "def extract" not in shares_src))

    # ── D2: extraction, executed ────────────────────────────────────────────
    cases = [
        ("style body dropped", "<style>body{color:red}</style><p>Real</p>", "Real", "color"),
        ("script body dropped", "<script>alert(1)</script><p>Real</p>", "Real", "alert"),
        ("svg dropped", "<svg><path d='M0'/></svg><p>After</p>", "After", "path"),
        ("head dropped", "<head><title>T</title></head><body><p>B</p></body>", "B", "<title>"),
    ]
    bad = []
    for name, markup, must_have, must_not in cases:
        out = extract_text_from_html(markup)
        if must_have not in out or must_not in out:
            bad.append(name)
    results.append(_check(
        "D2a non-prose element BODIES are dropped, prose survives",
        not bad, str(bad) or f"{len(cases)}/{len(cases)}"))
    results.append(_check(
        "D2b entities unescape and block elements become breaks",
        extract_text_from_html("<h1>A</h1><p>B &amp; C</p>") == "A\n\nB & C",
        repr(extract_text_from_html("<h1>A</h1><p>B &amp; C</p>"))))
    results.append(_check(
        "D2c output carries no markup (it is text, and only ever inserted as text)",
        "<" not in extract_text_from_html(
            '<div class="x"><p>Deep <b>bold</b></p><img src="x.png"></div>')))

    # The sandbox is NOT loosened. This is the check that stops a future session
    # reading "we extract text now" as "we may inline HTML".
    page = _strip_comments((WEB / "app/s/[token]/page.tsx").read_text(encoding="utf-8"))
    results.append(_check(
        "D2d the locked sandbox survives and nothing is inlined",
        'sandbox=""' in page
        and "allow-scripts" not in page
        and "allow-same-origin" not in page
        and "dangerouslySetInnerHTML" not in page))

    # ── D3: anti-silent-drop, executed over the format space ────────────────
    matrix = [
        ("/w/a.md", "# Hi", "text"),
        ("/w/a.txt", "plain", "text"),
        ("/w/a.csv", "a,b", "text"),
        ("/w/a.html", "<p>Hi</p>", "text"),
        ("/w/a.png", None, "passthrough"),
        ("/w/a.xlsx", "PK\x03\x04junk", "deferred"),
        ("/w/a.zip", "junk", "deferred"),
        ("/w/a.pdf", "%PDF-1.4 junk", "deferred"),
        ("/w/noext", "hello", "deferred"),
    ]
    wrong = [p for p, c, want in matrix if project_for_machine(path=p, content=c).strategy != want]
    results.append(_check(
        "D3a the format matrix lands correctly",
        not wrong, str(wrong) or f"{len(matrix)}/{len(matrix)}"))
    results.append(_check(
        "D3b the matrix covers all three strategies",
        {w for _, _, w in matrix} == {"text", "passthrough", "deferred"}))
    # The clause itself: nothing unreadable leaks bytes, and every gap is named.
    leaks = [
        p for p, c, want in matrix
        if want != "text"
        and (project_for_machine(path=p, content=c).text
             or not project_for_machine(path=p, content=c).note)
    ]
    results.append(_check(
        "D3c unreadable formats carry a NOTE and no text (DP34 anti-silent-drop)",
        not leaks, str(leaks) or "no bytes leak, every gap named"))
    # The binary text-family regression found during implementation: pdf/docx
    # are 'text' in the registry but arrive here as a content-column read, so
    # returning them verbatim emitted `%PDF-1.4 …` AS TEXT.
    results.append(_check(
        "D3d binary text-family (pdf/docx) never returns raw bytes as text",
        project_for_machine(path="/w/a.pdf", content="%PDF-1.4 x").text is None
        and project_for_machine(path="/w/a.docx", content="PK\x03\x04").text is None))

    # The boundary must not ship raw content for an unreadable format.
    results.append(_check(
        "D3e the route nulls artifact_content when there is no projection",
        re.search(r"out\.artifact_note\s*=\s*projection\.note", body) is not None
        and re.search(r"out\.artifact_content\s*=\s*None", body) is not None))

    # ── D4: the machine address is an ALIAS ─────────────────────────────────
    results.append(_check(
        "D4a the .txt route exists and precedes the bare-token route",
        shares_src.index('"/s/{token}.txt"') < shares_src.index('"/s/{token}"'),
        "FastAPI matches in declaration order"))
    results.append(_check(
        "D4b it carries Link: rel=canonical back to the share URL",
        're.sub' not in shares_src.split('rel="canonical"')[0][-200:]
        and 'rel="canonical"' in shares_src))
    # Slice the FUNCTION, not a fixed character window — the first cut used
    # [:900] and fell short of the body because the docstring is long. A gate
    # that measures characters is measuring the wrong thing.
    alias_fn = shares_src.split("async def preview_share_text")[1].split("\n@router")[0]
    results.append(_check(
        "D4c it carries the capability headers on every exit",
        "_CAPABILITY_HEADERS" in alias_fn))
    alias = (WEB / "app/s/[token]/txt/route.ts").read_text(encoding="utf-8")
    results.append(_check(
        "D4d the app-domain alias is a pure transport hop (no second projection)",
        "project" not in _strip_comments(alias).lower()
        and "no-store" in alias and "noindex" in alias))
    cfg = (WEB / "next.config.js").read_text(encoding="utf-8")
    results.append(_check(
        "D4e /s/:token.txt rewrites to the route (a segment can't carry a suffix)",
        "/s/:token.txt" in cfg))
    results.append(_check(
        "D4f discovery is DECLARED on the page (rel=alternate text/plain)",
        '"text/plain"' in page and "alternates" in page))

    ok = all(results)
    print(f"\n{'ALL PASS' if ok else 'FAILURES'} — {sum(results)}/{len(results)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

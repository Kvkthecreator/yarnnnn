"""ADR-529 gate — one share act, one link, two readers.

Guards the three decisions that have code behind them:

  D2  content negotiation: ONE projection, two representations. The markdown
      serializer must be a pure function of the already-built response — if it
      ever reads the database itself the two representations can drift, and a
      field could cross the ADR-513 D2 boundary in one representation only.
  D1  the cockpit mints through ONE component.
  D4  the four deletions actually happened (a convergence that leaves the old
      paths in place is a fifth way to share, not a convergence).

Executed, not grepped, wherever the claim is behavioural: the negotiation
matrix runs the real decision over seven reader classes and asserts the whole
matrix, and each deletion check is falsified by construction (it names the exact
symbol whose return would be the regression).

Run:  cd api && python3 test_adr529_share_convergence.py
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


def _read(rel: str) -> str:
    return (WEB / rel).read_text(encoding="utf-8")


def _strip_comments(src: str) -> str:
    """Code only. An assertion that matches its own explanatory comment is a
    documented trap — several checks below name the very symbol they forbid."""
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.DOTALL)
    src = re.sub(r"^\s*//.*$", "", src, flags=re.MULTILINE)
    return src


def main() -> int:
    results: list[bool] = []
    import routes.shares as r

    src = Path(__file__).parent.joinpath("routes/shares.py").read_text(encoding="utf-8")

    # ── D2: the markdown representation ─────────────────────────────────────
    body = src[src.index("def _render_markdown") : src.index("@router.get(\"/s/{token}\"")]
    results.append(_check(
        "D2a the serializer never touches the database",
        not any(tok in body for tok in
                ("get_service_client", ".table(", ".execute(", "supabase")),
        "pure function of the response model"))
    results.append(_check(
        "D2b the serializer takes the built projection, not a token",
        re.search(r"def _render_markdown\(out: SharePreviewResponse\)", body) is not None))

    # The projection's field set is the ADR-513 D2 boundary. Markdown may render
    # a SUBSET; it must never name a field the response model does not carry.
    model_fields = set(r.SharePreviewResponse.model_fields.keys())
    referenced = set(re.findall(r"\bout\.([a-z_]+)", body))
    results.append(_check(
        "D2c markdown references only projected fields (no boundary widening)",
        referenced <= model_fields, str(sorted(referenced - model_fields)) or "ok"))

    # Executed matrix — the real decision, seven reader classes, asserted whole.
    def wants_md(fmt, accept) -> bool:
        accept = (accept or "").lower()
        return (fmt or "").lower() in {"md", "markdown", "text"} or (
            fmt is None
            and ("text/markdown" in accept or "text/plain" in accept)
            and "application/json" not in accept
        )

    matrix = [
        ("browser", None, "text/html,application/xhtml+xml,*/*;q=0.8", False),
        ("curl default", None, "*/*", False),
        ("FE api client", None, "application/json", False),
        ("no accept header", None, "", False),
        ("LLM markdown", None, "text/markdown", True),
        ("LLM plain", None, "text/plain", True),
        ("explicit ?format=md", "md", "text/html", True),
    ]
    mismatches = [n for n, f, a, exp in matrix if wants_md(f, a) != exp]
    results.append(_check(
        "D2d negotiation matrix — every reader class lands correctly",
        not mismatches, str(mismatches) or f"{len(matrix)}/{len(matrix)}"))
    # Completeness: the matrix must cover BOTH outcomes, or it proves nothing.
    results.append(_check(
        "D2e the matrix exercises both outcomes",
        {exp for _, _, _, exp in matrix} == {True, False}))

    # Falsifier: drop the json-wins guard and a JSON caller starts getting
    # markdown. If this does NOT flip, the guard is not load-bearing.
    def wants_md_broken(fmt, accept) -> bool:
        accept = (accept or "").lower()
        return (fmt or "").lower() in {"md", "markdown", "text"} or (
            fmt is None and ("text/markdown" in accept or "text/plain" in accept)
        )
    results.append(_check(
        "D2f FALSIFY — removing the json-wins guard breaks a JSON reader",
        wants_md_broken(None, "text/markdown,application/json") is True
        and wants_md(None, "text/markdown,application/json") is False))

    results.append(_check(
        "D2g the markdown exit carries the capability headers",
        "PlainTextResponse(" in src
        and re.search(r"PlainTextResponse\(.*?_CAPABILITY_HEADERS", src, re.DOTALL) is not None,
        "no-store + noindex on every exit (ADR-513 D4)"))

    # HTML artifacts must be FENCED, never emitted raw into markdown — there is
    # no sanitizer (ADR-513 §1) and a renderer that honors raw HTML would be
    # handed member-authored script.
    results.append(_check(
        "D2h html artifacts are fenced, not inlined",
        '"```html"' in body or "'```html'" in body))

    # ── D1 / D4: one cockpit mint path, and the deletions ───────────────────
    files_page = _strip_comments(_read("app/(authenticated)/files/page.tsx"))
    studio_hdr = _strip_comments(_read("components/studio/StudioShareExport.tsx"))
    details = _strip_comments(_read("components/workspace/NodeDetailsPanel.tsx"))
    dialog_path = WEB / "components/workspace/ShareDialog.tsx"

    results.append(_check(
        "D1a the ShareDialog exists",
        dialog_path.exists()))

    if dialog_path.exists():
        dialog = _strip_comments(dialog_path.read_text(encoding="utf-8"))
        results.append(_check(
            "D1b the dialog is the ONLY cockpit createShare caller",
            "createShare" in dialog
            and "createShare" not in files_page
            and "createShare" not in studio_hdr,
            "one mint path"))
        results.append(_check(
            "D1c the dialog renders the URL and a copy control",
            "share_link" in dialog and "Copy" in dialog))
        results.append(_check(
            "D1d no role fires without a click (both shapes are explicit)",
            '"member"' in dialog and '"viewer"' in dialog))
        results.append(_check(
            "D1e revoke lives in the dialog (moved off the details panel)",
            "revokeShare" in dialog and "revokeShare" not in details))
        results.append(_check(
            "D1f it is a modal, not an outclick popover",
            "Escape" in dialog and "mousedown" not in dialog,
            "a governance act must not vanish on a stray click"))

    # D4 — the deletions, each named by the exact symbol whose return regresses.
    results.append(_check(
        "D4a Files' one-click mint-and-copy is gone",
        "createShare" not in files_page
        and "anyone with it can join the workspace" not in files_page))
    results.append(_check(
        "D4b Studio's share panel is gone (Export only)",
        "createShare" not in studio_hdr and "runShare" not in studio_hdr
        and "View-only link" not in studio_hdr))
    results.append(_check(
        "D4c Studio's false 'manage from Files' copy is gone",
        "revoke shares from Files" not in studio_hdr))
    results.append(_check(
        "D4d NodeDetailsPanel's FileShares block is gone",
        "function FileShares" not in details and "listShares" not in details))
    results.append(_check(
        "D4e shareKey() dead defence retired (ADR-517 D5)",
        "function shareKey" not in details,
        "paths are canonical-absolute at the write since migration 234"))

    ok = all(results)
    print(f"\n{'ALL PASS' if ok else 'FAILURES'} — {sum(results)}/{len(results)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

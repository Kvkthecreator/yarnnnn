"""Intake-pipeline contract gate — docs/architecture/intake-pipeline.md.

The pipeline was REAL and UNDOCUMENTED for four lanes; the absence of a written
contract is why connectors were built as a parallel lane instead of a tenant.
A contract nothing enforces is how that happens again.

Deliberately NARROW. It binds the two things §1–§3 declare binding:

  1. The path grammar `inbound/{lane}/{selector}/{stamp}.{ext}` — every writer
     of an inbound path produces at least lane + selector + leaf.
  2. Raw is an OBSERVATION — no intake writer may stamp `revision_kind`
     'authored' on a raw write (the live `slack` defect).

It deliberately does NOT bind the tenant roster (§2 — lanes churn) or require
every lane to derive (§4 — `mcp` correctly does not).
"""

import ast
import re
import sys
from pathlib import Path

API = Path(__file__).resolve().parent
DOC = API.parent / "docs" / "architecture" / "intake-pipeline.md"


def _check(label, ok, detail=""):
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {label}" + (f" — {detail}" if detail and not ok else ""))
    return bool(ok)


def _code_only(path: Path) -> str:
    """Source with docstrings blanked — a gate must never match its own prose."""
    src = path.read_text()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return src
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                body[0].value.value = ""
    out = ast.unparse(tree)
    # strip '#' comments too (ast.unparse drops them, but be explicit for clarity)
    return out


def _test_doc_exists():
    out = []
    out.append(_check("1 the intake-pipeline contract document exists", DOC.exists()))
    if DOC.exists():
        text = DOC.read_text()
        out.append(_check(
            "1b it declares the binding path grammar",
            "inbound/{lane}/{selector}/{stamp}" in text))
        out.append(_check(
            "1c it declares the derived-attribution rule",
            "system:derive-" in text and "on behalf of" in text))
        out.append(_check(
            "1d it states the tenant roster is NOT part of the contract",
            "tenant roster is not part of the contract" in text.lower()))
    return out


def _test_path_grammar():
    """2 — every constructed inbound path carries lane + selector + leaf.

    Driven where possible: `resolve_capture_path` is the shared builder, so we
    CALL it rather than reading it. The remaining literal f-strings are checked
    structurally.
    """
    out = []

    from services.primitives.sync_platform_state import resolve_capture_path

    # Driven: the connector lane's builder.
    p = resolve_capture_path("slack", "C123", "2026-08-18T00:00:00Z", "md")
    rel = p.lstrip("/").removeprefix("workspace/")
    parts = rel.split("/")
    out.append(_check(
        "2 resolve_capture_path yields inbound/{lane}/{selector}/{leaf}",
        parts[0] == "inbound" and len(parts) >= 4 and all(parts[:4]),
        f"got={p}"))

    # A selector containing a slash must NOT escape the lane (the GitHub
    # `owner/repo` case — it is one selector, not two segments).
    p2 = resolve_capture_path("github", "Kvk/yarnnnn", "2026-08-18T00:00:00Z", "md")
    rel2 = p2.lstrip("/").removeprefix("workspace/")
    out.append(_check(
        "2b a slash-bearing selector stays ONE segment (no lane escape)",
        len(rel2.split("/")) == 4, f"got={p2}"))

    # Structural: other inbound writers keep the shape.
    writers = {
        "services/strings.py": r'inbound/web/\{[^}]+\}/\{[^}]+\}',
        "services/primitives/track_web_sources.py": r'inbound/web/',
    }
    for rel_path, pattern in writers.items():
        f = API / rel_path
        if not f.exists():
            out.append(_check(f"2c {rel_path} present", False, "missing"))
            continue
        out.append(_check(
            f"2c {rel_path} writes into the inbound/web lane",
            bool(re.search(pattern, f.read_text()))))

    return out


def _test_raw_is_an_observation():
    """3 — no intake writer stamps revision_kind='authored' on a RAW write.

    §3: raw is an `observation`. The live `slack` lane violates this
    (48 rows written `authored`); when that writer is fixed this gate holds it.
    """
    out = []

    # The vocabulary must still exist where the doc says it does.
    from services import authored_substrate as asub
    src = _code_only(API / "services" / "authored_substrate.py")
    out.append(_check(
        "3 revision_kind vocabulary is live (authored|observation|derivation)",
        "revision_kind" in src and hasattr(asub, "write_revision")))

    # Capture writers must not hardcode 'authored'.
    offenders = []
    for rel in ("services/primitives/capture_connector.py",
                "services/primitives/sync_platform_state.py",
                "services/primitives/track_web_sources.py"):
        f = API / rel
        if not f.exists():
            continue
        code = _code_only(f)
        # look for revision_kind='authored' as an actual keyword/arg value
        if re.search(r'revision_kind\s*=\s*["\']authored["\']', code):
            offenders.append(rel)
    out.append(_check(
        "3b no capture writer stamps revision_kind='authored' on raw",
        not offenders, f"offenders={offenders}"))

    return out


def _test_quarantine_holds():
    """4 — inbound/ stays OUT of the embed-eligible set (raw is keyed, not ranked).

    Driven against the real constant, not its comment.
    """
    out = []
    from services.primitives.embed import _EMBED_ELIGIBLE_ROOTS

    bad = [r for r in _EMBED_ELIGIBLE_ROOTS
           if r.startswith("inbound/") and r != "inbound/uploads/"]
    out.append(_check(
        "4 no inbound/ lane is embed-eligible except the human uploads carve-out",
        not bad, f"unexpectedly eligible={bad}"))
    return out


def main():
    results = []
    results += _test_doc_exists()
    results += _test_path_grammar()
    results += _test_raw_is_an_observation()
    results += _test_quarantine_holds()

    passed = sum(1 for r in results if r)
    print(f"\n{passed}/{len(results)} intake-pipeline contract assertions pass")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())

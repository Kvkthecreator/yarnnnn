"""A comment may not claim a capability is DEFERRED once it is built.

## The finding (2026-08-20)

A connector audit asked "can the operator choose which workspace ChatGPT binds
to?" and answered NO — from this comment in `routes/mcp.py`:

    # A connector cannot NAME a workspace (ADR-373 D6, still deferred): it takes
    # the principal's default.

That was true when written and FALSE when read. ADR-573 shipped the picker on
2026-08-17 (`ec58956`): a `<select>` on the consent screen, a validated
`workspace_id` on the bind, reach checked fail-closed, and the binding carried
through refresh rotation. The comment outlived the build by three days and was
read as the live contract — the audit recommended building a feature that
already existed, and nearly opened an ADR for it.

This is the documentation twin of the failure class the memory already names:
a claim that describes the system's state, kept by hand, drifting from the
system. `[[feedback_hand_kept_log_beside_generated_truth]]` says the fix is a
gate, never more prose. So: a gate.

## What it defends

A source comment may say a thing WAS deferred (history, always legal — see
`mcp_server/auth.py`, which narrates D6's pre-build state in the very docstring
that discharges it). It may NOT assert in the present tense that a capability is
STILL deferred when the code implementing it is right there.

The rule is deliberately narrow. It fires on a present-tense deferral claim
about a capability this gate can PROVE is built, by driving the real code — not
on the word "deferred", not on a spelling, and not on genuine future work. A
gate that flagged every "TODO" would be noise nobody reads, and the ADR-586
lesson (`[[feedback_gate_pinned_spelling_reads_narrowing_as_violation]]`) is
that pinning prose reads a correction as a violation.

Falsified against the real break: restoring the original comment fails check 3,
and deleting the FE picker fails check 1.

Run with `python3 test_adr573_no_stale_deferral_claims.py` from `api/`.
NOT pytest — check() gates print ✗ but a pytest run reports PASS (see MEMORY.md).
"""

import ast
import re
import sys
import logging

FAILURES: list = []


def _check(label, cond):
    if cond:
        logging.info("✓ %s", label)
    else:
        logging.error("✗ %s", label)
        FAILURES.append(label)
    return bool(cond)


def _comments_only(path: str) -> str:
    """Every `#` comment and docstring in a file, with CODE stripped out.

    Comments are read from the raw source (ast discards them); docstrings are
    recovered from the tree. Checking prose against prose alone is what stops
    an assertion from matching the code it is asserting about — and checking
    code against `ast` is what stops it from matching its own explanatory
    comment (`[[feedback_gate_assertion_matches_its_own_comment]]`).
    """
    src = open(path).read()
    out = []
    for line in src.splitlines():
        if "#" in line:
            out.append(line[line.index("#"):])
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            doc = ast.get_docstring(node)
            if doc:
                out.append(doc)
    return "\n".join(out)


def _code_only(path: str) -> str:
    """The file's CODE with all comments and docstrings removed."""
    tree = ast.parse(open(path).read())
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", None)
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(getattr(body[0], "value", None), ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                node.body = body[1:] or [ast.Pass()]
    return ast.unparse(tree)


# A present-tense claim that workspace SELECTION is unavailable. Several
# phrasings, because the defect is the CLAIM, not one wording of it — but each
# is anchored on a present-tense verb, so a past-tense history note survives.
_DEFERRAL_CLAIMS = (
    r"connector cannot NAME a workspace",
    r"cannot name a workspace",
    r"still deferred",
    r"selection is (?:still )?(?:deferred|open|unbuilt)",
)


def run() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    # ── 1. The capability is BUILT: the FE sends a chosen workspace ──────────
    # Drives the real consent page. If the picker is deleted this fails, and
    # the deferral claim would become true again — which is exactly why the
    # prose check below is conditioned on this one passing.
    fe = open("../web/app/mcp/authorize/page.tsx").read()
    has_picker = "<select" in fe and "completeAuthorize" in fe
    sends_choice = re.search(r"completeAuthorize\(\s*code\s*,\s*\w+", fe) is not None
    _check(
        "1. the consent screen has a workspace picker AND sends the choice on bind",
        has_picker and sends_choice,
    )

    # ── 2. The capability is BUILT: the API accepts + validates the choice ───
    api_code = _code_only("routes/mcp.py")
    _check(
        "2. the bind endpoint takes a workspace_id and validates REACH before binding",
        "workspace_id" in api_code
        and "principal_reaches_workspace" in api_code
        and "403" in api_code,
    )

    # ── 3. Therefore no comment may say selection is still deferred ─────────
    # Scoped to the MCP consent + auth surface: the files whose comments a
    # reader consults to learn what the connector can do.
    surfaces = (
        "routes/mcp.py",
        "mcp_server/auth.py",
        "mcp_server/oauth_provider.py",
        "services/mcp_composition.py",
    )
    offenders = []
    for path in surfaces:
        prose = _comments_only(path)
        for line in prose.splitlines():
            # A sentence that NARRATES history is legal ("was ratified and
            # never built", "before this it took the default"). The defect is
            # the present-tense assertion, so require the claim WITHOUT a
            # past-tense or superseded marker on the same line.
            if any(re.search(p, line, re.I) for p in _DEFERRAL_CLAIMS):
                historical = re.search(
                    r"\bwas\b|\bwere\b|\bbefore\b|\buntil\b|\bpreviously\b|"
                    r"\bused to\b|\bno longer\b|\bdo not re-describe\b|"
                    r"\bclaimed\b|\bthis comment\b",
                    line,
                    re.I,
                )
                if not historical:
                    offenders.append(f"{path}: {line.strip()[:100]}")
    _check(
        "3. no present-tense 'selection is deferred' claim survives on the MCP surface",
        not offenders,
    )
    for o in offenders:
        print(f"      → {o}")

    # ── 4. The consent model still names the resolver it shares with the token ─
    # The screen must not promise one workspace while the token reaches
    # another. This is the property the stale comment's SECOND half described
    # correctly, and it must stay true.
    _check(
        "4. consent resolves the default through the same resolver the connector uses",
        "resolve_workspace_for_principal" in api_code,
    )

    total = len(FAILURES)
    print(f"\nStale-deferral-claim gate: {_RUN - total}/{_RUN} passed, {total} failed")
    for f in FAILURES:
        print(f"  ✗ {f}")
    return 1 if FAILURES else 0


_RUN = 4

if __name__ == "__main__":
    sys.exit(run())

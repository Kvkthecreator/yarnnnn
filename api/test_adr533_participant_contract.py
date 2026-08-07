"""
ADR-533 — one participant contract across every surface.

The anti-drift ratchet. Every participant-facing envelope COMPOSES the kernel
commons-contract constants; no surface restates a clause inline. The interop
verb table is DERIVED from the roster, never hand-written. Every write-capable
surface can author the ADR-448 reference edge.

WHAT THIS GATE ASSERTS: structure — that a constant is imported, that a list is
derived, that a parameter is threaded, that two sets match.

WHAT IT DELIBERATELY DOES NOT ASSERT: the prose those things produce (ADR-533
D5). Prior gates in this repo went void by pinning an expression's first token
or matching their own explanatory comment. A clause must stay editable without
turning this file red. If you find yourself asserting a sentence, stop.

Pure-Python source-guard (no DB, no `mcp` package — the interop module is read
via AST so this runs without the MCP SDK installed).

Run:  python3 test_adr533_participant_contract.py      (from api/)
"""

import ast
import inspect
import re
import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parent


def _check(label, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}")
    return bool(ok)


def _read(rel: str) -> str:
    return (API_ROOT / rel).read_text()


def rendered_instructions() -> str:
    """The connector self-description as the HOST actually receives it.

    Public helper (ADR-533 D2): the verb table is derived at import time, so the
    bullets are not literals in `server.py` any more. Any gate asserting what the
    host is taught must assert THIS, not grep the source. The ADR-512 verb gates
    import it — one implementation of the extraction, not three copies.
    """
    return _interop_namespace()["_build_interop_instructions"]()


def _interop_namespace() -> dict:
    """Exec ONLY the ADR-533 roster + builder out of the interop server module.

    `mcp_server/server.py` imports the `mcp` SDK at module scope, which is not
    installed in the gate environment. Extracting the two ADR-533 symbols by AST
    keeps this gate dependency-free AND proves the composition itself has no MCP
    dependency — it is pure kernel-constant composition.
    """
    tree = ast.parse(_read("mcp_server/server.py"))
    want = {"_INTEROP_VERBS", "_build_interop_instructions"}

    def name_of(node):
        if isinstance(node, ast.FunctionDef):
            return node.name
        if isinstance(node, ast.AnnAssign):
            return getattr(node.target, "id", None)
        if isinstance(node, ast.Assign):
            return next((getattr(t, "id", None) for t in node.targets), None)
        return None

    nodes = [n for n in tree.body if name_of(n) in want]
    ns: dict = {}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "adr533", "exec"), ns)
    return ns


def run() -> int:
    ok = True

    # ── D1: the commons-contract clauses exist as kernel constants ────────────
    import services.workspace_paths as wp

    CLAUSES = (
        "PARTICIPANT_COMMONS_CONTRACT",
        "PARTICIPANT_ATTRIBUTION_RULE",
        "PARTICIPANT_CITATION_RULE",
        "PARTICIPANT_FORMAT_DISCIPLINE",
        "PARTICIPANT_READ_BEFORE_WRITE",
    )
    for name in CLAUSES:
        val = getattr(wp, name, None)
        ok &= _check(
            f"D1 {name} exists + non-trivial",
            isinstance(val, str) and len(val.strip()) > 40,
        )

    # The clauses are kernel-UNIVERSAL: no workspace-specific intent may leak in
    # (that is the D6 boundary, enforced structurally rather than by review).
    for name in CLAUSES:
        val = getattr(wp, name, "") or ""
        ok &= _check(
            f"D6 {name} carries no workspace-specific intent",
            "MANDATE" not in val,
            "(the mandate is per-workspace; these constants are kernel-universal)",
        )

    # ── D1: the LANE composes the clauses (does not restate them) ─────────────
    lane_src = inspect.getsource(
        __import__("services.lane_runner", fromlist=["x"]).build_lane_conventions
    )
    for name in CLAUSES + ("PARTICIPANT_FILESYSTEM_MODEL",):
        ok &= _check(
            f"D1 lane composes {name}",
            name in lane_src,
        )

    from services.lane_runner import _CONVENTIONS_FRAME

    for slot in (
        "{commons_contract}",
        "{attribution_rule}",
        "{citation_rule}",
        "{format_discipline}",
        "{read_before_write}",
        "{filesystem_model}",
    ):
        ok &= _check(f"D1 lane frame injects {slot}", slot in _CONVENTIONS_FRAME)

    # ── D1: the INTEROP surface composes the same clauses ─────────────────────
    server_src = _read("mcp_server/server.py")
    for name in CLAUSES + ("PARTICIPANT_FILESYSTEM_MODEL",):
        ok &= _check(f"D1 interop composes {name}", name in server_src)

    ns = _interop_namespace()
    instructions = ns["_build_interop_instructions"]()
    for name in CLAUSES + ("PARTICIPANT_FILESYSTEM_MODEL",):
        clause = getattr(wp, name)
        ok &= _check(
            f"D1 interop OUTPUT carries {name} verbatim",
            clause.strip() in instructions,
            "(composed, not paraphrased)",
        )

    # ── D2: the interop verb table is DERIVED, never hand-written ─────────────
    roster = {name for name, _ in ns["_INTEROP_VERBS"]}
    ok &= _check("D2 verb roster is non-empty", len(roster) >= 6, f"({len(roster)} verbs)")

    # Every registered @mcp.tool must be in the roster and vice versa. This is the
    # gate that would have caught the "Four verbs / six verbs" drift at authoring
    # time: a verb can never ship announced-but-absent or absent-but-announced.
    tree = ast.parse(server_src)
    registered = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.AsyncFunctionDef):
            continue
        for dec in node.decorator_list:
            func = dec.func if isinstance(dec, ast.Call) else dec
            is_tool = (
                isinstance(func, ast.Attribute)
                and func.attr == "tool"
                and getattr(func.value, "id", None) == "mcp"
            )
            if not is_tool:
                continue
            # An explicit name= kwarg overrides the function name (e.g. open_file → "open").
            explicit = None
            if isinstance(dec, ast.Call):
                explicit = next(
                    (
                        kw.value.value
                        for kw in dec.keywords
                        if kw.arg == "name" and isinstance(kw.value, ast.Constant)
                    ),
                    None,
                )
            registered.add(explicit or node.name)

    ok &= _check(
        "D2 roster == registered tool set",
        roster == registered,
        f"roster-only={sorted(roster - registered)} registered-only={sorted(registered - roster)}",
    )

    # No hand-written verb COUNT in the prose (the exact drift ADR-533 D2 removes).
    # Assert on the OUTPUT, not the source: a count word anywhere in what the host
    # reads is the defect, wherever it came from.
    counts = re.findall(
        r"\b(?:one|two|three|four|five|six|seven|eight|nine|ten)\s+verbs\b",
        instructions,
        re.IGNORECASE,
    )
    ok &= _check("D2 no hand-written verb count in the prose", not counts, f"{counts}")

    # Every verb name in the roster appears in the rendered table (derivation
    # actually ran — not a roster that exists beside hand-written prose).
    ok &= _check(
        "D2 every rostered verb appears in the output",
        all(name in instructions for name in roster),
    )

    # ── D3: derived_from is authorable from the interop write path ────────────
    comp_src = _read("services/mcp_composition.py")
    save_fn = re.search(
        r"async def compose_save\((.*?)\) -> dict:", comp_src, re.DOTALL
    )
    ok &= _check(
        "D3 compose_save accepts derived_from",
        bool(save_fn) and "derived_from" in save_fn.group(1),
    )
    # Threaded to the primitive, not merely accepted and dropped.
    ok &= _check(
        "D3 compose_save threads derived_from into the WriteFile input",
        re.search(r'write_input\[["\']derived_from["\']\]\s*=', comp_src) is not None,
    )
    save_tool = re.search(
        r"async def save\((.*?)\) -> dict:", server_src, re.DOTALL
    )
    ok &= _check(
        "D3 the save tool exposes derived_from to the host",
        bool(save_tool) and "derived_from" in save_tool.group(1),
    )

    # D3's deliberate EXCLUSION: `remember` writes raw arrivals
    # (revision_kind='observation'), which by definition are not made FROM a
    # workspace file. A citation edge there would invite manufactured provenance.
    # Freezing the exclusion keeps a future "consistency" pass from adding it
    # without reading the ADR.
    remember_fn = re.search(
        r"async def dispatch_remember_this\((.*?)\) -> dict:", comp_src, re.DOTALL
    )
    ok &= _check(
        "D3 remember does NOT take derived_from (raw arrivals are not derivations)",
        bool(remember_fn) and "derived_from" not in remember_fn.group(1),
    )

    print()
    print("ADR-533 participant-contract ratchet:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(run())

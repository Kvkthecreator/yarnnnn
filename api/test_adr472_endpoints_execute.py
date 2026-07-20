"""ADR-472 — the endpoint bodies EXECUTE (the class of bug source-greps miss).

WHY THIS EXISTS (a real prod break, 2026-07-20). The ADR-472 carve routed
/studio/templates + /studio/vocabulary through the cross-app layout registry.
A scripted edit injected the new imports into a FUNCTION-LOCAL
`from services.studio import (...)` block belonging to a different handler, so
the names were scoped to that one function. Every gate stayed green — they read
source text, and the text was all present — and both endpoints 500'd in prod
with `NameError: name 'all_templates' is not defined`.

The lesson: a gate that greps for a symbol proves the symbol EXISTS somewhere,
never that the handler can REACH it. This gate CALLS the handlers.

Run:  python3 api/test_adr472_endpoints_execute.py   (NOT pytest — check()-gate.)
"""

import asyncio
import sys
from pathlib import Path

_results: list[tuple[str, bool]] = []


def _check(label: str, cond: bool) -> None:
    _results.append((label, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {label}")


class _FakeAuth:
    """The minimum an auth-dependent handler touches. These endpoints are pure
    kernel-vocabulary reads — they never touch the DB — so a stub suffices."""

    user_id = "00000000-0000-0000-0000-000000000000"
    client = None


def run() -> bool:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import routes.studio as rs

    auth = _FakeAuth()

    # ── The two endpoints the carve rewired ──────────────────────────────
    try:
        templates = asyncio.run(rs.list_templates(auth))
        slugs = {t["slug"] for t in templates["templates"]}
        _check("GET /studio/templates EXECUTES (no NameError in the body)", True)
        _check(
            "…and serves both apps' layouts (Studio's + the IMAGES stage)",
            {"document", "deck", "article"} <= slugs and "image" in slugs,
        )
    except Exception as exc:  # noqa: BLE001
        _check(f"GET /studio/templates EXECUTES — raised {type(exc).__name__}: {exc}", False)
        _check("…and serves both apps' layouts", False)

    try:
        vocab = asyncio.run(rs.get_vocabulary(auth))
        v_slugs = {l["slug"] for l in vocab["layouts"]}
        _check("GET /studio/vocabulary EXECUTES (no NameError in the body)", True)
        _check(
            "…and its layout roster carries the stage",
            "image" in v_slugs and "canvas" not in v_slugs,
        )
    except Exception as exc:  # noqa: BLE001
        _check(f"GET /studio/vocabulary EXECUTES — raised {type(exc).__name__}: {exc}", False)
        _check("…and its layout roster carries the stage", False)

    # ── The structural cause, pinned so it cannot recur ──────────────────
    src = Path(__file__).resolve().parent.joinpath("routes/studio.py").read_text()
    module_import = "\nfrom services.studio import all_layouts, all_templates, resolve_layout"
    _check(
        "the cross-app resolver is imported at MODULE level, not inside a handler",
        module_import in src,
    )
    _check(
        "the IMAGES registration import is present (else the stage 404s at create)",
        "import services.images" in src,
    )

    ok = all(c for _, c in _results)
    print()
    print(f"{'PASS' if ok else 'FAIL'}: {sum(c for _, c in _results)}/{len(_results)} checks")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)

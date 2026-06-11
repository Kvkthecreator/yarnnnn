"""ADR-338 D4.5 gate — installer-shaped program preview.

The audit found WorkspaceSection / /setup / /program showed only title +
tagline + activate button before activation — never the bundle's four-flow
declaration (what the program perceives / produces / attests / learns). The
operator activated without seeing what they were committing to. This gate
proves the four-flow preview is derived + surfaced pre-activation.

`four_flow_preview` is tested behaviorally against the REAL bundles
(alpha-trader / alpha-author active; alpha-commerce deferred), mirroring the
D9 conformance gate's canonical four-flow slots so preview + gate agree.

Usage:
    cd api
    python test_adr338_installer.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_API_ROOT = Path(__file__).resolve().parent
_WEB = _API_ROOT.parent / "web"

PASSED = 0
FAILED = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global PASSED, FAILED
    if condition:
        print(f"  ✓ {label}")
        PASSED += 1
    else:
        print(f"  ✗ {label}{(' — ' + detail) if detail else ''}")
        FAILED += 1


def _read(rel: str, root: Path = _WEB) -> str:
    p = root / rel
    return p.read_text() if p.exists() else ""


def test_four_flow_preview_real_bundles() -> None:
    print("\n[backend] four_flow_preview derives the four flows from real bundles")
    sys.path.insert(0, str(_API_ROOT))
    try:
        from services.bundle_reader import four_flow_preview
    except Exception as exc:  # pragma: no cover
        check("services.bundle_reader.four_flow_preview imports", False, str(exc))
        return
    check("four_flow_preview imports", True)

    # alpha-trader (active) — all four flows present.
    at = four_flow_preview("alpha-trader")
    check("alpha-trader preview returned", at is not None)
    if at:
        keys = {f["key"] for f in at["flows"]}
        check("declares all four canonical flow keys",
              keys == {"perception", "work_out", "outcomes", "loop"},
              f"got {keys}")
        present = {f["key"] for f in at["flows"] if f["present"]}
        check("alpha-trader: all four flows present (active program)",
              present == {"perception", "work_out", "outcomes", "loop"},
              f"present={present}")
        check("alpha-trader: capabilities surfaced",
              "read_trading" in at["capabilities"])
        check("alpha-trader: ground truth surfaced",
              at["ground_truth"] and "money_truth" in at["ground_truth"])
        check("alpha-trader: watch count > 0", at["watch_count"] > 0)
        # Present flows carry a summary; absent flows carry rationale-or-null.
        for f in at["flows"]:
            if f["present"]:
                check(f"alpha-trader {f['key']}: present → has summary",
                      bool(f.get("summary")))

    # alpha-author (active, lean) — perception via web watch, all four present.
    aa = four_flow_preview("alpha-author")
    if aa:
        present = {f["key"] for f in aa["flows"] if f["present"]}
        check("alpha-author: all four flows present (web watch + capabilities)",
              present == {"perception", "work_out", "outcomes", "loop"},
              f"present={present}")

    # alpha-commerce (deferred) — perception + loop N/A (honest absence).
    ac = four_flow_preview("alpha-commerce")
    if ac:
        by_key = {f["key"]: f for f in ac["flows"]}
        check("alpha-commerce: work_out present (commerce capabilities)",
              by_key["work_out"]["present"] is True)
        check("alpha-commerce: outcomes present (revenue ground truth)",
              by_key["outcomes"]["present"] is True)
        # perception/loop absent — present=False, never crashes.
        check("alpha-commerce: absent flows render present=False (no crash)",
              by_key["perception"]["present"] is False)

    # Missing bundle → None (graceful).
    check("unknown bundle → None (graceful)", four_flow_preview("no-such-program") is None)


def test_routes_expose_preview() -> None:
    print("\n[routes] activatable + workspace-state expose flow_preview")
    prog = _read("routes/programs.py", root=_API_ROOT)
    check("activatable route imports four_flow_preview", "four_flow_preview" in prog)
    check("activatable item carries flow_preview", '"flow_preview": four_flow_preview(slug)' in prog)
    ws = _read("routes/workspace.py", root=_API_ROOT)
    check("ProgramItem model declares flow_preview", "flow_preview: Optional[dict]" in ws)
    check("workspace-state populates flow_preview", "flow_preview=four_flow_preview(slug)" in ws)


def test_fe_renders_installer_panel() -> None:
    print("\n[fe] WorkspaceSection renders the installer panel pre-activation")
    src = _read("components/settings/WorkspaceSection.tsx")
    check("FlowPreview component present", "function FlowPreview" in src)
    check("rendered only for not-yet-active programs", "!isActive && program.flow_preview" in src)
    check('installer framing copy ("What this program does")', "What this program does" in src)
    check("absent flows framed as not-applicable (honest)", "not applicable" in src)
    client = _read("lib/api/client.ts")
    check("getState available_programs type carries flow_preview",
          "flow_preview:" in client and "watch_count: number" in client)
    check("listActivatable type carries flow_preview (consumer coherence)",
          client.count("watch_count: number") >= 2)


def main() -> int:
    print("=" * 70)
    print("ADR-338 D4.5 — installer-shaped program preview gate")
    print("=" * 70)
    test_four_flow_preview_real_bundles()
    test_routes_expose_preview()
    test_fe_renders_installer_panel()
    print("\n" + "=" * 70)
    print(f"  {PASSED} passed, {FAILED} failed")
    print("=" * 70)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())

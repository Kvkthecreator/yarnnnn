"""ADR-296 v2 Checkpoint 2 — Full landing regression gate.

Asserts the architectural shape Checkpoint 2 commits:

  - services/wake.py is the singular invocation gateway
    (submit_wake_proposal + stream_addressed_wake)
  - services/wake_evaluation.py exports the funnel API (Tier 1 + Tier 2)
  - services/wake_sources/ package contains all 5 wake-source modules
  - services/primitives/manage_hook.py is the ManageHook primitive
  - ManageHook registered in CHAT/HEADLESS/REVIEWER primitive sets + HANDLERS
  - Old services/invocation_dispatcher.py is GONE (Singular Implementation)
  - All known dispatch() call sites migrated to wake_sources.* modules
  - alpha-trader trade-proposal recurrence DELETED
  - alpha-author pre-ship-audit moved to _hooks.yaml
  - alpha-trader + alpha-author bundles ship _hooks.yaml
  - Reviewer principles.md teaches cadence+intent, not FireInvocation

Run: python api/test_adr296_v2_full_landing.py
"""

from __future__ import annotations

import sys
import re
from pathlib import Path

ROOT = Path(__file__).parent
REPO_ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))


def _ok(msg: str) -> None:
    print(f"  PASS  {msg}")


def _fail(label: str, detail: str = "") -> None:
    print(f"  FAIL  {label}" + (f" — {detail}" if detail else ""))
    raise SystemExit(1)


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _read_repo(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


def _exists(rel: str) -> bool:
    return (ROOT / rel).exists()


def _exists_repo(rel: str) -> bool:
    return (REPO_ROOT / rel).exists()


# ----------------------------------------------------------------------------
# 1. services/wake.py is the singular invocation gateway
# ----------------------------------------------------------------------------

def test_wake_py_is_singular_gateway() -> None:
    if not _exists("services/wake.py"):
        _fail("services/wake.py does not exist", "Phase 1A git mv failed")
    _ok("services/wake.py exists")

    src = _read("services/wake.py")

    if "async def submit_wake_proposal(" not in src:
        _fail("submit_wake_proposal not defined", "Phase 1A signature missing")
    _ok("submit_wake_proposal() is defined")

    if "async def stream_addressed_wake(" not in src:
        _fail("stream_addressed_wake not defined", "Phase 1A SSE entry missing")
    _ok("stream_addressed_wake() async generator is defined")

    # Old dispatch() function name must be gone (Singular Implementation).
    if re.search(r"^async def dispatch\(", src, re.MULTILINE):
        _fail(
            "dispatch() function still defined in wake.py",
            "Singular Implementation: only submit_wake_proposal survives",
        )
    _ok("dispatch() function name is gone (Singular Implementation)")

    # Public API exports
    if not re.search(r'__all__\s*=\s*\[\s*\n?\s*"submit_wake_proposal"', src):
        _fail("wake.py __all__ missing submit_wake_proposal", "")
    _ok("wake.py __all__ exports submit_wake_proposal")


# ----------------------------------------------------------------------------
# 2. Old invocation_dispatcher.py is gone
# ----------------------------------------------------------------------------

def test_invocation_dispatcher_removed() -> None:
    if _exists("services/invocation_dispatcher.py"):
        _fail(
            "services/invocation_dispatcher.py still exists",
            "Should be renamed via git mv to services/wake.py",
        )
    _ok("services/invocation_dispatcher.py removed (renamed to wake.py)")


# ----------------------------------------------------------------------------
# 3. wake_evaluation.py funnel
# ----------------------------------------------------------------------------

def test_wake_evaluation_funnel() -> None:
    if not _exists("services/wake_evaluation.py"):
        _fail("services/wake_evaluation.py missing", "Phase 1B")
    _ok("services/wake_evaluation.py exists")

    src = _read("services/wake_evaluation.py")
    for name in (
        "def tier_1_decision(",
        "async def tier_2_decision(",
        "async def evaluate(",
        "class BudgetSignals",
    ):
        if name not in src:
            _fail(f"wake_evaluation missing {name}", "")
    _ok("wake_evaluation exports tier_1_decision + tier_2_decision + evaluate + BudgetSignals")


# ----------------------------------------------------------------------------
# 4. wake_sources/ package — all 5 modules
# ----------------------------------------------------------------------------

def test_wake_sources_package() -> None:
    package_files = {
        "services/wake_sources/__init__.py": None,
        "services/wake_sources/cron_tick.py": "dispatch_recurrence",
        "services/wake_sources/addressed.py": "async def stream(",
        "services/wake_sources/proposal_arrival.py": "async def on_created(",
        "services/wake_sources/substrate_event.py": "async def walk_hooks(",
        "services/wake_sources/manual_fire.py": "async def fire(",
    }
    for path, marker in package_files.items():
        if not _exists(path):
            _fail(f"{path} missing", "Phase 1C")
        if marker is not None:
            src = _read(path)
            if marker not in src:
                _fail(f"{path} missing {marker!r}", "")
    _ok("wake_sources/ package has all 5 modules with expected entry points")


# ----------------------------------------------------------------------------
# 5. ManageHook primitive
# ----------------------------------------------------------------------------

def test_manage_hook_primitive() -> None:
    if not _exists("services/primitives/manage_hook.py"):
        _fail("services/primitives/manage_hook.py missing", "Phase 1C")
    src = _read("services/primitives/manage_hook.py")
    for name in ("MANAGE_HOOK_TOOL", "async def handle_manage_hook("):
        if name not in src:
            _fail(f"manage_hook.py missing {name}", "")
    _ok("manage_hook.py exports MANAGE_HOOK_TOOL + handle_manage_hook")


def test_manage_hook_registry_registration() -> None:
    src = _read("services/primitives/registry.py")

    if "from .manage_hook import MANAGE_HOOK_TOOL, handle_manage_hook" not in src:
        _fail("registry.py does not import manage_hook", "")
    _ok("registry imports manage_hook module")

    if '"ManageHook": handle_manage_hook' not in src:
        _fail("HANDLERS missing ManageHook entry", "")
    _ok("HANDLERS['ManageHook'] = handle_manage_hook")

    from services.primitives.registry import (
        CHAT_PRIMITIVES, HEADLESS_PRIMITIVES, FREDDIE_PRIMITIVES,
    )
    chat_names = {t["name"] for t in CHAT_PRIMITIVES}
    headless_names = {t["name"] for t in HEADLESS_PRIMITIVES}
    reviewer_names = {t["name"] for t in FREDDIE_PRIMITIVES}

    for label, names in (
        ("CHAT_PRIMITIVES", chat_names),
        ("HEADLESS_PRIMITIVES", headless_names),
        ("FREDDIE_PRIMITIVES", reviewer_names),
    ):
        if "ManageHook" not in names:
            _fail(f"{label} missing ManageHook", "")
    _ok("ManageHook registered in CHAT + HEADLESS + REVIEWER primitive sets")


# ----------------------------------------------------------------------------
# 6. No stale invocation_dispatcher imports in live code
# ----------------------------------------------------------------------------

def test_no_invocation_dispatcher_references() -> None:
    # Walk services/, routes/, jobs/, scripts/, agents/ for any
    # `services.invocation_dispatcher` reference.
    violations: list[str] = []
    for subdir in ("services", "routes", "jobs", "scripts", "agents"):
        base = ROOT / subdir
        if not base.exists():
            continue
        for py_file in base.rglob("*.py"):
            if "__pycache__" in py_file.parts:
                continue
            if py_file.name.startswith("test_"):
                continue
            try:
                content = py_file.read_text(encoding="utf-8")
            except Exception:
                continue
            if "services.invocation_dispatcher" in content or \
               "services/invocation_dispatcher" in content:
                violations.append(str(py_file.relative_to(ROOT)))
    if violations:
        _fail(
            "stale invocation_dispatcher references in live code",
            ", ".join(violations),
        )
    _ok("Zero stale invocation_dispatcher references in live code")


# ----------------------------------------------------------------------------
# 7. dispatch() callers migrated
# ----------------------------------------------------------------------------

def test_callers_migrated() -> None:
    # Each of these call sites should now import from wake_sources.* not
    # from invocation_dispatcher.
    expected_migrations = [
        ("jobs/unified_scheduler.py",
         "from services.wake_sources.cron_tick import dispatch_recurrence"),
        ("services/primitives/fire_invocation.py",
         "from services.wake_sources.manual_fire import fire"),
        ("services/operator_proxy/scenarios.py",
         "from services.wake_sources.manual_fire import fire"),
        ("routes/recurrences.py",
         "from services.wake_sources.manual_fire import fire"),
        ("routes/admin.py",
         "from services.wake_sources.manual_fire import fire"),
        ("routes/agents.py",
         "from services.wake_sources.manual_fire import fire"),
        ("scripts/alpha_ops/manual_fire.py",
         "from services.wake_sources.manual_fire import fire"),
        ("services/primitives/propose_action.py",
         "from services.wake_sources.proposal_arrival import on_created"),
        ("routes/feed.py",
         "from services.wake_sources.addressed import stream"),
    ]
    for path, expected_import in expected_migrations:
        src = _read(path)
        if expected_import not in src:
            _fail(
                f"{path} not migrated",
                f"expected import: {expected_import}",
            )
    _ok(f"All {len(expected_migrations)} caller sites migrated to wake_sources.*")


# ----------------------------------------------------------------------------
# 8. Bundle migrations
# ----------------------------------------------------------------------------

def test_alpha_trader_trade_proposal_deleted() -> None:
    src = _read_repo("docs/programs/alpha-trader/reference-workspace/_recurrences.yaml")
    # The trade-proposal recurrence entry must be gone. Check for the slug
    # in a definition position (`  - slug: trade-proposal`).
    if re.search(r"^\s*-\s+slug:\s*trade-proposal\s*$", src, re.MULTILINE):
        _fail(
            "alpha-trader still ships trade-proposal recurrence",
            "Phase 3: must be deleted; logic inlined into signal-evaluation",
        )
    _ok("alpha-trader trade-proposal recurrence DELETED")

    # signal-evaluation prompt should now contain inline ProposeAction guidance.
    if "ProposeAction(" not in src:
        _fail(
            "alpha-trader signal-evaluation prompt missing inline ProposeAction",
            "Phase 3: trade-proposal logic should inline here",
        )
    _ok("alpha-trader signal-evaluation prompt teaches inline ProposeAction")


def test_alpha_trader_principles_no_fireinvocation() -> None:
    src = _read_repo(
        "docs/programs/alpha-trader/reference-workspace/persona/principles.md"
    )
    # The "Commission substrate via FireInvocation" clause must be gone.
    if "Commission substrate via FireInvocation" in src:
        _fail(
            "alpha-trader principles.md still teaches Commission via FireInvocation",
            "ADR-296 v2 D3",
        )
    # The "fire the track-positions ... via FireInvocation" directive must be gone.
    if re.search(r"fire\s+the\s+`?track-positions`?\s+mechanical\s+recurrence\s+via\s+FireInvocation", src):
        _fail(
            "alpha-trader principles.md still has track-positions FireInvocation directive",
            "ADR-296 v2 D3",
        )
    _ok("alpha-trader principles.md: FireInvocation teachings removed")


def test_alpha_author_pre_ship_audit_migrated_to_hooks() -> None:
    recurrences = _read_repo(
        "docs/programs/alpha-author/reference-workspace/_recurrences.yaml"
    )
    if re.search(r"^\s*-\s+slug:\s*pre-ship-audit\s*$", recurrences, re.MULTILINE):
        _fail(
            "alpha-author still ships pre-ship-audit recurrence",
            "Phase 3: must migrate to _hooks.yaml",
        )
    _ok("alpha-author pre-ship-audit recurrence DELETED")

    hooks_path = "docs/programs/alpha-author/reference-workspace/_hooks.yaml"
    if not _exists_repo(hooks_path):
        _fail(f"{hooks_path} missing", "Phase 3 must scaffold _hooks.yaml")
    hooks = _read_repo(hooks_path)
    if "slug: pre-ship-audit" not in hooks:
        _fail("alpha-author _hooks.yaml missing pre-ship-audit entry", "")
    if "path_match:" not in hooks or "field_change:" not in hooks:
        _fail("alpha-author _hooks.yaml missing required hook fields", "")
    _ok("alpha-author _hooks.yaml ships pre-ship-audit substrate-event hook")


def test_alpha_trader_hooks_yaml_scaffolded() -> None:
    path = "docs/programs/alpha-trader/reference-workspace/_hooks.yaml"
    if not _exists_repo(path):
        _fail(f"{path} missing", "Phase 3 scaffold")
    content = _read_repo(path)
    if "hooks:" not in content:
        _fail("alpha-trader _hooks.yaml missing 'hooks:' key", "")
    _ok("alpha-trader _hooks.yaml scaffolded (empty hooks: [] at activation)")


# ----------------------------------------------------------------------------
# 9. ADR status flip
# ----------------------------------------------------------------------------

def test_adr296_status_flipped() -> None:
    src = _read_repo("docs/adr/ADR-296-continuous-judgment-cycle.md")
    if "**Status**: Implemented" not in src:
        _fail("ADR-296 status not flipped to Implemented", "Phase 4")
    _ok("ADR-296 status flipped to Implemented")


# ----------------------------------------------------------------------------
# 10. py_compile gate — all touched files compile cleanly
# ----------------------------------------------------------------------------

def test_all_files_compile() -> None:
    import py_compile
    paths = [
        "services/wake.py",
        "services/wake_evaluation.py",
        "services/wake_sources/__init__.py",
        "services/wake_sources/cron_tick.py",
        "services/wake_sources/addressed.py",
        "services/wake_sources/proposal_arrival.py",
        "services/wake_sources/manual_fire.py",
        "services/wake_sources/substrate_event.py",
        "services/primitives/manage_hook.py",
        "services/primitives/registry.py",
        "services/primitives/fire_invocation.py",
        "services/primitives/propose_action.py",
        "routes/feed.py",
        "routes/agents.py",
        "routes/admin.py",
        "routes/recurrences.py",
        "services/operator_proxy/scenarios.py",
        "scripts/alpha_ops/manual_fire.py",
        "jobs/unified_scheduler.py",
        "services/scheduling.py",
    ]
    for rel in paths:
        try:
            py_compile.compile(str(ROOT / rel), doraise=True)
        except Exception as exc:
            _fail(f"{rel} fails py_compile", str(exc))
    _ok(f"All {len(paths)} touched files py_compile clean")


# ----------------------------------------------------------------------------
# Runner
# ----------------------------------------------------------------------------

def main() -> None:
    print("=" * 72)
    print("ADR-296 v2 Checkpoint 2 — Full Landing Regression Gate")
    print("=" * 72)

    test_wake_py_is_singular_gateway()
    test_invocation_dispatcher_removed()
    test_wake_evaluation_funnel()
    test_wake_sources_package()
    test_manage_hook_primitive()
    test_manage_hook_registry_registration()
    test_no_invocation_dispatcher_references()
    test_callers_migrated()
    test_alpha_trader_trade_proposal_deleted()
    test_alpha_trader_principles_no_fireinvocation()
    test_alpha_author_pre_ship_audit_migrated_to_hooks()
    test_alpha_trader_hooks_yaml_scaffolded()
    test_adr296_status_flipped()
    test_all_files_compile()

    print()
    print("=" * 72)
    print("All ADR-296 v2 Checkpoint 2 assertions PASS")
    print("=" * 72)


if __name__ == "__main__":
    main()

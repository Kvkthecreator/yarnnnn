"""ADR-244 regression gate — Workspace Settings Surface.

Validates: endpoint rename + shape extension, deactivation primitive
(soft, idempotent, ADR-209-attributed), L2/L4 program preservation,
OnboardingModal deletion, callback redirect target, singular activate
call site (the surface is the only FE caller of api.programs.activate).

Pure-Python script per ADR-236 Rule 3 (no JS test runner). Run with:
    python -m api.test_adr244_workspace_settings_surface
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# ─── Files we expect to exist / not to exist ────────────────────────────

ADR_FILE = REPO_ROOT / "docs" / "adr" / "ADR-244-workspace-settings-surface.md"
PROGRAMS_SVC = REPO_ROOT / "api" / "services" / "programs.py"
WORKSPACE_ROUTE = REPO_ROOT / "api" / "routes" / "workspace.py"
PROGRAMS_ROUTE = REPO_ROOT / "api" / "routes" / "programs.py"
MEMORY_ROUTE = REPO_ROOT / "api" / "routes" / "memory.py"
ACCOUNT_ROUTE = REPO_ROOT / "api" / "routes" / "account.py"

WORKSPACE_SECTION_FE = REPO_ROOT / "web" / "components" / "settings" / "WorkspaceSection.tsx"
SETTINGS_PAGE_FE = REPO_ROOT / "web" / "app" / "(authenticated)" / "settings" / "page.tsx"
CALLBACK_PAGE_FE = REPO_ROOT / "web" / "app" / "auth" / "callback" / "page.tsx"
API_CLIENT_FE = REPO_ROOT / "web" / "lib" / "api" / "client.ts"

ONBOARDING_MODAL_FE = REPO_ROOT / "web" / "components" / "onboarding" / "OnboardingModal.tsx"
ONBOARDING_DIR_FE = REPO_ROOT / "web" / "components" / "onboarding"
ADR240_TEST = REPO_ROOT / "api" / "test_adr240_onboarding_activation.py"


def assertion_1_adr_exists():
    """ADR-244 ADR file is committed."""
    assert ADR_FILE.exists(), f"ADR file missing: {ADR_FILE}"
    body = ADR_FILE.read_text()
    assert "Supersedes" in body, "ADR must declare what it supersedes"
    assert "ADR-240" in body, "ADR must cite ADR-240 supersession"
    assert "ADR-226" in body, "ADR must cite ADR-226 amendment"


def assertion_2_programs_service_module_exists():
    """services/programs.py exports parse_active_program_slug + strip_program_marker_from_mandate."""
    assert PROGRAMS_SVC.exists(), f"services/programs.py missing"
    src = PROGRAMS_SVC.read_text()
    assert "def parse_active_program_slug" in src, "parse_active_program_slug missing"
    assert "def strip_program_marker_from_mandate" in src, "strip_program_marker_from_mandate missing"


def assertion_3_parse_active_program_slug_correctness():
    """Parser returns slug for bundle template, None for kernel default."""
    sys.path.insert(0, str(REPO_ROOT / "api"))
    try:
        from services.programs import (
            parse_active_program_slug,
            strip_program_marker_from_mandate,
        )
    finally:
        sys.path.pop(0)

    # Kernel-default + edge cases → None
    assert parse_active_program_slug(None) is None
    assert parse_active_program_slug("") is None
    assert parse_active_program_slug("# Mandate") is None
    assert parse_active_program_slug("## Section\n# Mandate") is None  # H2 first, no H1 marker
    # Bundle template marker → slug
    assert parse_active_program_slug("# Mandate — alpha-trader (template)\n\n## Body") == "alpha-trader"
    assert parse_active_program_slug("# Mandate — alpha-commerce (template)") == "alpha-commerce"
    # Marker strip
    assert strip_program_marker_from_mandate("# Mandate — alpha-trader (template)\n\nbody") == "# Mandate\n\nbody"
    # Idempotency
    assert strip_program_marker_from_mandate("# Mandate\n\nbody") == "# Mandate\n\nbody"
    assert strip_program_marker_from_mandate("") == ""


def assertion_4_workspace_state_endpoint_registered():
    """GET /workspace/state lives in routes/workspace.py with extended shape."""
    src = WORKSPACE_ROUTE.read_text()
    assert "@router.get(\"/workspace/state\"" in src, "GET /workspace/state route missing"
    assert "WorkspaceStateResponse" in src, "WorkspaceStateResponse model missing"
    assert "substrate_status" in src, "substrate_status field missing"
    assert "capability_gaps" in src, "capability_gaps field missing"
    assert "available_programs" in src, "available_programs field missing"
    # Side effects preserved
    assert "X-Timezone" in src, "browser timezone header read missing"
    assert "workspace_init_complete" in src, "system_card write preserved from legacy endpoint"


def assertion_5_legacy_onboarding_state_deleted():
    """routes/memory.py no longer registers GET /user/onboarding-state."""
    src = MEMORY_ROUTE.read_text()
    assert "/user/onboarding-state\"" not in src.replace(" ", ""), \
        "Legacy /user/onboarding-state route must be deleted"
    assert "OnboardingStateResponse" not in src.split("ADR-244")[0], \
        "OnboardingStateResponse model must be removed (only mentioned in ADR-244 deletion comment)"


def assertion_6_deactivate_endpoint_registered():
    """POST /programs/deactivate registered with soft-by-design semantics."""
    src = PROGRAMS_ROUTE.read_text()
    assert "@router.post(\"/deactivate\"" in src, "POST /deactivate route missing"
    assert "deactivate_program" in src, "deactivate_program function missing"
    assert "strip_program_marker_from_mandate" in src, \
        "deactivate must use strip_program_marker_from_mandate (soft semantic)"
    assert "system:program-deactivate" in src, \
        "deactivate must attribute via authored_by per ADR-209"


def assertion_7_l2_l4_preserve_program():
    """clear_workspace + reset_account capture active_program_slug pre-purge
    and pass to initialize_workspace during reinit."""
    src = ACCOUNT_ROUTE.read_text()
    # Both purge paths must reference the parser
    assert src.count("parse_active_program_slug") >= 2, \
        "L2 + L4 must both capture active_program_slug pre-purge"
    # Both reinit paths must thread program_slug
    assert src.count("program_slug=prior_program_slug") >= 2, \
        "L2 + L4 reinit must pass program_slug to initialize_workspace"
    # Stale "essential tasks" message must be gone (audit gap #2)
    assert "essential tasks" not in src.lower(), \
        "Stale 'essential tasks' wording must be removed (ADR-206 collapsed signup tasks)"


def assertion_8_onboarding_modal_deleted():
    """OnboardingModal.tsx + onboarding/ dir + ADR-240 test gate deleted."""
    assert not ONBOARDING_MODAL_FE.exists(), \
        f"OnboardingModal.tsx must be deleted: {ONBOARDING_MODAL_FE}"
    assert not ONBOARDING_DIR_FE.exists(), \
        f"web/components/onboarding/ must be deleted: {ONBOARDING_DIR_FE}"
    assert not ADR240_TEST.exists(), \
        f"ADR-240 test gate must be deleted: {ADR240_TEST}"


def assertion_9_callback_redirects_to_settings():
    """auth/callback/page.tsx redirects first-run to /settings?tab=workspace."""
    src = CALLBACK_PAGE_FE.read_text()
    assert "OnboardingModal" not in src, \
        "callback must not import OnboardingModal anymore"
    assert "/settings?tab=workspace&first_run=1" in src, \
        "callback must redirect first-run to settings workspace tab"
    assert "api.workspace.getState" in src, \
        "callback must use renamed api.workspace endpoint"


def assertion_10_settings_workspace_tab_wired():
    """settings/page.tsx renders the Workspace tab + section."""
    src = SETTINGS_PAGE_FE.read_text()
    assert "WorkspaceSection" in src, "Settings page must import WorkspaceSection"
    assert '"workspace"' in src, "Settings tab type must include 'workspace'"
    assert "tab=workspace" not in src or "tabParam" in src, \
        "Settings page must read ?tab=workspace param"


def assertion_11_workspace_section_component_shape():
    """WorkspaceSection has activate / switch / deactivate affordances + zero edit fields."""
    src = WORKSPACE_SECTION_FE.read_text()
    # Affordances
    assert "api.programs.activate" in src, "Activate must call api.programs.activate"
    assert "api.programs.deactivate" in src, "Deactivate must call api.programs.deactivate"
    # Hard boundary — no substrate edit fields (D7)
    assert "<textarea" not in src, "Workspace surface must not render textarea (ADR-244 D7)"
    assert "<input" not in src.replace("<input ", ""), \
        "Workspace surface must not render input fields (ADR-244 D7)"
    # First-run hint
    assert "first_run" in src, "First-run query param must be honored"


def assertion_12_api_client_renamed():
    """api.onboarding deleted; api.workspace + api.programs.deactivate present.

    Strip explanatory comments before checking for live references — the
    "ADR-244: api.onboarding deleted" docblock is intentional documentation,
    not a live caller.
    """
    src = API_CLIENT_FE.read_text()
    # Strip line-comments to avoid matching documentation
    code_lines = [
        ln for ln in src.splitlines()
        if not ln.strip().startswith("//") and not ln.strip().startswith("*")
    ]
    code = "\n".join(code_lines)
    assert "api.onboarding" not in code, \
        "api.onboarding must be deleted (replaced by api.workspace) — found live reference"
    assert "/api/memory/user/onboarding-state" not in src, \
        "Legacy onboarding-state URL must be removed from client"
    assert "/api/workspace/state" in src, "api.workspace.getState URL must be /api/workspace/state"
    assert "/api/programs/deactivate" in src, "api.programs.deactivate URL must be present"


def assertion_13_singular_activate_call_site():
    """Only one FE file calls api.programs.activate — WorkspaceSection.tsx (the surface).
    The OnboardingModal (the previous singular call site) is deleted."""
    activate_callers: list[Path] = []
    for tsx in REPO_ROOT.glob("web/**/*.tsx"):
        if "node_modules" in tsx.parts or ".next" in tsx.parts:
            continue
        if "api.programs.activate" in tsx.read_text():
            activate_callers.append(tsx)
    assert len(activate_callers) == 1, (
        f"Expected exactly one FE caller of api.programs.activate; found {activate_callers}"
    )
    expected = REPO_ROOT / "web" / "components" / "settings" / "WorkspaceSection.tsx"
    assert activate_callers[0] == expected, (
        f"The single caller must be {expected}; got {activate_callers[0]}"
    )


def assertion_14_no_dangling_legacy_references():
    """No code path still references the deleted endpoint or modal."""
    for tsx in (REPO_ROOT / "web").rglob("*.tsx"):
        if "node_modules" in tsx.parts or ".next" in tsx.parts:
            continue
        text = tsx.read_text()
        assert "api.onboarding.getState" not in text, \
            f"Dangling api.onboarding.getState in {tsx}"
    for ts in (REPO_ROOT / "web").rglob("*.ts"):
        if "node_modules" in ts.parts or ".next" in ts.parts:
            continue
        text = ts.read_text()
        # The api/client.ts itself contains "api.onboarding deleted" comment — exempt
        if "api.onboarding deleted" in text:
            continue
        assert "api.onboarding.getState" not in text, f"Dangling reference in {ts}"


def main() -> int:
    tests = [
        assertion_1_adr_exists,
        assertion_2_programs_service_module_exists,
        assertion_3_parse_active_program_slug_correctness,
        assertion_4_workspace_state_endpoint_registered,
        assertion_5_legacy_onboarding_state_deleted,
        assertion_6_deactivate_endpoint_registered,
        assertion_7_l2_l4_preserve_program,
        assertion_8_onboarding_modal_deleted,
        assertion_9_callback_redirects_to_settings,
        assertion_10_settings_workspace_tab_wired,
        assertion_11_workspace_section_component_shape,
        assertion_12_api_client_renamed,
        assertion_13_singular_activate_call_site,
        assertion_14_no_dangling_legacy_references,
    ]
    failures: list[str] = []
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
        except AssertionError as e:
            failures.append(f"{t.__name__}: {e}")
            print(f"  FAIL  {t.__name__}: {e}")
    print()
    if failures:
        print(f"ADR-244 regression gate: {len(tests) - len(failures)}/{len(tests)} passed")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"ADR-244 regression gate: {len(tests)}/{len(tests)} passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

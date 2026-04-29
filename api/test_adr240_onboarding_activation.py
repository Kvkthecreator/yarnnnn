"""
ADR-240 regression gate — onboarding-as-activation.

Asserts eight invariants for the FE consumption layer landed in ADR-240
(Round 4 of the ADR-236 frontend cockpit coherence pass).

Same Python-test-over-TS-source pattern as ADR-237 / ADR-238 / ADR-239
(no JS test runner today; see ADR-236 Rule 3).

Run via:
    python -m pytest api/test_adr240_onboarding_activation.py -v

Or as a standalone script:
    python api/test_adr240_onboarding_activation.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

WEB_MODAL = REPO_ROOT / "web" / "components" / "onboarding" / "OnboardingModal.tsx"
WEB_AUTH_CALLBACK = REPO_ROOT / "web" / "app" / "auth" / "callback" / "page.tsx"
WEB_API_CLIENT = REPO_ROOT / "web" / "lib" / "api" / "client.ts"
API_MEMORY = REPO_ROOT / "api" / "routes" / "memory.py"
API_ACTIVATION_PROMPT = REPO_ROOT / "api" / "agents" / "prompts" / "chat" / "activation.py"


def _read(p: Path) -> str:
    if not p.exists():
        raise AssertionError(f"Missing file: {p.relative_to(REPO_ROOT)}")
    return p.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Test gate
# ---------------------------------------------------------------------------

def test_onboarding_modal_exists_and_exports_modal():
    """Assertion #1: web/components/onboarding/OnboardingModal.tsx exists
    and exports OnboardingModal."""
    src = _read(WEB_MODAL)
    assert "export function OnboardingModal" in src, (
        "OnboardingModal.tsx must export OnboardingModal per ADR-240 D1."
    )


def test_auth_callback_imports_onboarding_modal():
    """Assertion #2: auth/callback/page.tsx imports OnboardingModal."""
    src = _read(WEB_AUTH_CALLBACK)
    assert "from '@/components/onboarding/OnboardingModal'" in src or \
        'from "@/components/onboarding/OnboardingModal"' in src, (
        "auth/callback/page.tsx must import OnboardingModal per ADR-240 D1."
    )


def test_api_client_exposes_programs_namespace():
    """Assertion #3: web/lib/api/client.ts exposes
    api.programs.listActivatable and api.programs.activate."""
    src = _read(WEB_API_CLIENT)
    # Both methods must exist; checking for the unique strings the
    # implementations contain.
    assert "/api/programs/activatable" in src, (
        "client.ts must call /api/programs/activatable per ADR-240 D1."
    )
    assert "/api/programs/activate" in src, (
        "client.ts must call /api/programs/activate per ADR-240 D1."
    )
    assert "programs:" in src, (
        "client.ts must define a `programs` API namespace."
    )


def test_api_client_extends_onboarding_state_type():
    """Assertion #4: client.ts onboarding-state return type includes
    activation_state and active_program_slug fields."""
    src = _read(WEB_API_CLIENT)
    assert "activation_state" in src, (
        "client.ts onboarding-state type must include activation_state per ADR-240 D5."
    )
    assert "active_program_slug" in src, (
        "client.ts onboarding-state type must include active_program_slug per ADR-240 D5."
    )


def test_memory_route_returns_activation_state_and_program_slug():
    """Assertion #5: api/routes/memory.py OnboardingStateResponse
    includes activation_state + active_program_slug fields, AND the
    endpoint populates them."""
    src = _read(API_MEMORY)
    assert "activation_state: str" in src, (
        "memory.py OnboardingStateResponse must declare activation_state per ADR-240 D5."
    )
    assert "active_program_slug: Optional[str]" in src, (
        "memory.py OnboardingStateResponse must declare active_program_slug per ADR-240 D5."
    )
    # The endpoint body must populate both fields, not just declare them.
    assert "activation_state=activation_state" in src, (
        "memory.py endpoint must return activation_state value per ADR-240 D5."
    )
    assert "active_program_slug=active_program_slug" in src, (
        "memory.py endpoint must return active_program_slug value per ADR-240 D5."
    )


def test_activation_prompt_includes_capability_gap_paragraph():
    """Assertion #6: activation.py includes the D6 capability-gap
    paragraph instructing YARNNN to surface platform-connection gaps."""
    src = _read(API_ACTIVATION_PROMPT)
    assert "Capability gap awareness" in src, (
        "activation.py must include the ADR-240 D6 capability-gap paragraph "
        "section header."
    )
    assert "ADR-240 D6" in src, (
        "activation.py must cite ADR-240 D6 in the new section."
    )
    # The substantive instruction — surface honestly, don't gate the walk.
    assert "knowledge mode" in src or "advisory" in src, (
        "activation.py D6 paragraph must explain the knowledge-mode fallback."
    )


def test_singular_activation_call_site():
    """Assertion #7: Singular Implementation regression guard. Exactly
    one FE file calls api.programs.activate — OnboardingModal.tsx. No
    other surface should activate programs."""
    web_dir = REPO_ROOT / "web"
    callers = []
    for path in web_dir.rglob("*.tsx"):
        if "node_modules" in path.parts:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except Exception:
            continue
        if "api.programs.activate" in content:
            callers.append(path.relative_to(REPO_ROOT))
    expected = Path("web/components/onboarding/OnboardingModal.tsx")
    assert len(callers) == 1 and callers[0] == expected, (
        f"api.programs.activate must have exactly one caller "
        f"(web/components/onboarding/OnboardingModal.tsx). Found: {callers}. "
        "Singular Implementation per ADR-240 D1."
    )


def test_modal_does_not_import_settings_section():
    """Assertion #8: OnboardingModal.tsx does NOT import
    ConnectedIntegrationsSection. Step 2 reuses the authorization API
    call site, not the Settings component (per ADR-240 §"What this ADR
    does NOT do" — no duplication). Comments mentioning the symbol as
    rationale are allowed; only actual imports are forbidden."""
    src = _read(WEB_MODAL)
    # Forbidden: any line that imports the component.
    forbidden_patterns = [
        "import { ConnectedIntegrationsSection }",
        "import {ConnectedIntegrationsSection}",
        "from '@/components/settings/ConnectedIntegrationsSection'",
        'from "@/components/settings/ConnectedIntegrationsSection"',
    ]
    for pattern in forbidden_patterns:
        assert pattern not in src, (
            f"OnboardingModal.tsx must NOT import ConnectedIntegrationsSection. "
            f"Found forbidden pattern: {pattern!r}. "
            "Step 2 reuses the authorization API call site only per ADR-240 D3."
        )


# ---------------------------------------------------------------------------
# Standalone runner
# ---------------------------------------------------------------------------

def _run_all() -> int:
    tests = [
        test_onboarding_modal_exists_and_exports_modal,
        test_auth_callback_imports_onboarding_modal,
        test_api_client_exposes_programs_namespace,
        test_api_client_extends_onboarding_state_type,
        test_memory_route_returns_activation_state_and_program_slug,
        test_activation_prompt_includes_capability_gap_paragraph,
        test_singular_activation_call_site,
        test_modal_does_not_import_settings_section,
    ]
    failed = 0
    for fn in tests:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {fn.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} ADR-240 assertions passed.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(_run_all())

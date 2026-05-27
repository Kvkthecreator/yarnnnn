"""ADR-304 D3 regression gate — YARNNN chat honors bundle MANIFEST.

Asserts the load-bearing properties of `get_platform_tools_for_user`'s
rewrite per ADR-304 D3:

  1. Pre-rewrite "for provider in connected_providers" iteration is
     DELETED from the function body. No raw-provider iteration; tools
     surface because bundles DECLARE the capability, not because the
     operator happens to have an OAuth connection to the provider.

  2. The rewrite reads bundle MANIFEST capability declarations via
     `list_bundle_capabilities`. Source-level guard that the import is
     present.

  3. The rewrite gates on `platform_connections` via the kernel's
     `capability_available` path. Source-level guard.

  4. SYSTEM_INFRASTRUCTURE_TOOLS surface as Layer 1 unconditionally —
     pre-activation workspaces (no bundle, no platform connections)
     still see the 3 operator-addressing system-infrastructure tools.

The headless path (`get_platform_tools_for_capabilities` and its caller
`get_platform_tools_for_agent`) is unchanged by ADR-304 — it already
gated on declared capability sets per ADR-227 + ADR-261. ADR-304 D3
brings YARNNN chat into the same gating discipline.

Run: python api/test_adr304_yarnnn_chat_honors_bundle_manifest.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "api"))


def test_get_platform_tools_for_user_does_not_iterate_raw_providers() -> None:
    """ADR-304 D3: pre-rewrite "for provider in connected_providers" + raw
    PLATFORM_TOOLS_BY_PROVIDER.get(provider) iteration is DELETED. Singular
    Implementation — the unconditional-per-provider surfacing path doesn't
    survive."""
    import inspect
    from services import platform_tools

    source = inspect.getsource(platform_tools.get_platform_tools_for_user)

    # Pre-rewrite pattern that must be gone.
    assert "for provider in connected_providers" not in source, (
        "get_platform_tools_for_user still iterates connected_providers — "
        "ADR-304 D3 required this pattern deleted. Surfacing must flow "
        "through bundle MANIFEST declarations, not raw platform_connections."
    )
    assert "PLATFORM_TOOLS_BY_PROVIDER.get(provider, [])" not in source, (
        "get_platform_tools_for_user still calls PLATFORM_TOOLS_BY_PROVIDER.get(provider) "
        "for surfacing — the raw-provider iteration pattern. ADR-304 D3 required "
        "this deleted; tool lookup happens at definition resolution, not "
        "provider-keyed iteration."
    )


def test_get_platform_tools_for_user_reads_bundle_capabilities() -> None:
    """ADR-304 D3: the rewrite reads bundle MANIFEST capability declarations
    via `list_bundle_capabilities`. Source-level guard for the new pattern."""
    import inspect
    from services import platform_tools

    source = inspect.getsource(platform_tools.get_platform_tools_for_user)

    assert "list_bundle_capabilities" in source, (
        "get_platform_tools_for_user does NOT import list_bundle_capabilities — "
        "ADR-304 D3 requires the rewrite to read bundle MANIFEST declarations "
        "as the workspace-capability source."
    )


def test_get_platform_tools_for_user_gates_on_capability_available() -> None:
    """ADR-304 D3: the rewrite gates declared bundle capabilities through
    the kernel's `capability_available` path (which checks platform_connections
    for connection-required capabilities). Source-level guard."""
    import inspect
    from services import platform_tools

    source = inspect.getsource(platform_tools.get_platform_tools_for_user)

    assert "capability_available" in source, (
        "get_platform_tools_for_user does NOT call capability_available — "
        "ADR-304 D3 requires the bundle-declared capabilities to be gated "
        "on the kernel's _resolve_capability path so connection-required "
        "capabilities are honored consistently with the headless path."
    )


def test_get_platform_tools_for_user_layer_1_surfaces_system_infrastructure() -> None:
    """ADR-304 D3 Layer 1: SYSTEM_INFRASTRUCTURE_TOOLS surfaces unconditionally
    — pre-activation workspaces (no bundle, no connections) still see the
    operator-addressing system-infrastructure tools."""
    import inspect
    from services import platform_tools

    source = inspect.getsource(platform_tools.get_platform_tools_for_user)

    assert "SYSTEM_INFRASTRUCTURE_TOOLS" in source, (
        "get_platform_tools_for_user does NOT reference SYSTEM_INFRASTRUCTURE_TOOLS — "
        "ADR-304 D3 Layer 1 requires unconditional surfacing of system "
        "infrastructure regardless of bundle activation or platform "
        "connections."
    )

    # The Layer 1 surfacing block must appear BEFORE the bundle-capability
    # Layer 2 block. Source-order check (Layer 1 unconditional, Layer 2
    # bundle-declared).
    sys_infra_idx = source.find("SYSTEM_INFRASTRUCTURE_TOOLS")
    bundle_caps_idx = source.find("list_bundle_capabilities")
    assert sys_infra_idx < bundle_caps_idx, (
        "SYSTEM_INFRASTRUCTURE_TOOLS surfacing appears AFTER list_bundle_capabilities "
        "in the function body — ADR-304 D3 requires Layer 1 (system "
        "infrastructure) to surface BEFORE Layer 2 (bundle-declared)."
    )


def test_get_platform_tools_for_user_headless_parity() -> None:
    """ADR-304 D3: the rewrite brings YARNNN chat into the same gating
    discipline as the headless path. Both functions:
      - merge SYSTEM_INFRASTRUCTURE_TOOLS as a Layer 1 unconditional set
      - gate workspace-capability tools through declared capability sets
        + platform_connections via _resolve_capability
    """
    import inspect
    from services import platform_tools

    user_src = inspect.getsource(platform_tools.get_platform_tools_for_user)
    cap_src = inspect.getsource(platform_tools.get_platform_tools_for_capabilities)

    for func_name, src in (
        ("get_platform_tools_for_user", user_src),
        ("get_platform_tools_for_capabilities", cap_src),
    ):
        assert "SYSTEM_INFRASTRUCTURE_TOOLS" in src, (
            f"{func_name} does NOT merge SYSTEM_INFRASTRUCTURE_TOOLS — "
            "ADR-304 D3 requires parity across YARNNN chat + headless paths."
        )


if __name__ == "__main__":
    tests = [
        test_get_platform_tools_for_user_does_not_iterate_raw_providers,
        test_get_platform_tools_for_user_reads_bundle_capabilities,
        test_get_platform_tools_for_user_gates_on_capability_available,
        test_get_platform_tools_for_user_layer_1_surfaces_system_infrastructure,
        test_get_platform_tools_for_user_headless_parity,
    ]
    failures: list[str] = []
    for fn in tests:
        try:
            fn()
            print(f"  PASS  {fn.__name__}")
        except AssertionError as exc:
            failures.append(f"  FAIL  {fn.__name__}\n         {exc}")
            print(f"  FAIL  {fn.__name__}")
            print(f"         {exc}")
        except Exception as exc:
            failures.append(f"  ERROR {fn.__name__}\n         {type(exc).__name__}: {exc}")
            print(f"  ERROR {fn.__name__}")
            print(f"         {type(exc).__name__}: {exc}")
    print()
    print(f"{len(tests) - len(failures)}/{len(tests)} tests passed")
    if failures:
        sys.exit(1)

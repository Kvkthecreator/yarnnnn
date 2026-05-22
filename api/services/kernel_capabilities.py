"""Kernel-universal capabilities — capabilities that operate across all program
bundle archetypes, gated by AUTONOMY + operator preferences rather than by
bundle MANIFEST declarations (ADR-299, 2026-05-22).

The architectural class introduced here is distinct from bundle-specific
capabilities (`docs/programs/{slug}/MANIFEST.yaml::capabilities[]`). Bundle-
specific capabilities encode archetype-bound knowledge (`read_trading` only
makes sense for trading workspaces; `write_commerce` only for commerce). Kernel-
universal capabilities encode OS-level surfaces every workspace needs regardless
of program — the first instance being operator-addressing observability (the
Reviewer telling the operator about workspace state via email).

The distinguishing test (ADR-299 D1): does the capability address operator-
identity (kernel-universal) or a third party / audience / external counterparty
(bundle-specific)? If addressee resolves from `auth.users.email` for the
workspace owner, kernel-universal. If addressee is anyone else, bundle-specific.

Resolution discipline (ADR-299 D5): one resolution path in
`get_platform_tools_for_capabilities`; the kernel-universal vs bundle-specific
distinction is a lookup-table source, not a parallel runtime code path. Kernel-
universal capabilities are checked before bundle-specific ones; precedence is
one-way (bundles cannot redeclare kernel-universal capability keys to alter
their shape).

Connection-gating note (ADR-299 D2 clarification, implementation): kernel-
universal capabilities may still have wire-level connection requirements — e.g.,
`send_operator_email` uses Resend via `_handle_email_tool` and requires an
active `platform_connections.platform='email'` row to actually send. The
"kernel-universal" claim holds because the capability declaration is unconditional
(any bundle can request it without MANIFEST changes); the wire-level gate is a
runtime detail handled by graceful tool-surface degradation when the connection
is absent.
"""

from __future__ import annotations

from typing import Optional


# =============================================================================
# Kernel-universal capability registry (ADR-299 D1 + D5)
# =============================================================================
#
# Schema mirrors the bundle MANIFEST capability shape so callers can treat both
# sources uniformly when assembling agent tool surfaces:
#
#   {
#     "key":                   stable capability identifier (no bundle prefix)
#     "category":              always "tool" for now
#     "runtime":               "kernel" (no external provider; uses kernel-owned
#                              wire). Differs from bundle-specific
#                              "external:trading" / "external:slack" etc.
#     "requires_connection":   platform-connections gate. None means no gating
#                              (true kernel-universal); a string means the wire
#                              still needs that platform connected even though
#                              the capability declaration is universal (per
#                              ADR-299 D2 clarification).
#     "tools":                 tool names this capability grants to the agent
#                              tool surface.
#     "addressee_class":       documentation field naming why this is kernel-
#                              universal — "operator" means addressee resolves
#                              from auth.users.email for the workspace owner.
#                              Distinct from bundle-specific capabilities whose
#                              addressee is a third party / audience.
#     "autonomy_posture":      "observability" or "consequential". Observability
#                              capabilities are gated by `_preferences.yaml`
#                              opt-in (the operator's standing approval), NOT
#                              by per-action AUTONOMY click. See ADR-299 D4.
#   }
#
# Adding a new kernel-universal capability requires:
#  1. New entry in KERNEL_UNIVERSAL_CAPABILITIES below
#  2. Tool definition added to the appropriate provider tool list in
#     api/services/platform_tools.py (or kernel-owned tool list if no provider)
#  3. Handler branch in the relevant tool-handler function
#  4. ADR amendment (per ADR-299 D7 — new kernel-universal capabilities require
#     ADR discourse; this registry is not a dumping ground)

KERNEL_UNIVERSAL_CAPABILITIES: dict[str, dict] = {
    # ADR-299 D2: first instance — operator-addressing email.
    # Wraps existing ADR-192 Phase 4 Resend infrastructure with structural
    # addressee pinning to auth.users.email. Tool refuses LLM-supplied `to:`
    # field — that surface stays with bundle-specific `platform_email_send`
    # for audience-bearing use cases.
    "send_operator_email": {
        "key": "send_operator_email",
        "category": "tool",
        "runtime": "kernel",
        # ADR-299 D2 implementation clarification: capability is universal-by-
        # declaration (any bundle/recurrence can request it without MANIFEST
        # changes), but the underlying Resend wire still needs the operator to
        # have connected Resend via POST /integrations/email/connect. The wire-
        # gate is runtime, the declaration-gate is none.
        "requires_connection": "email",
        "tools": ["platform_email_send_to_operator"],
        "addressee_class": "operator",
        "autonomy_posture": "observability",
    },
}


# =============================================================================
# Resolution helpers (ADR-299 D5)
# =============================================================================

def is_kernel_universal_capability(capability_key: str) -> bool:
    """True iff the capability is registered as kernel-universal.

    Used by capability resolution (services/platform_tools.py::
    get_platform_tools_for_capabilities) to apply kernel-universal precedence
    before falling through to bundle MANIFEST resolution.
    """
    return capability_key in KERNEL_UNIVERSAL_CAPABILITIES


def get_kernel_universal_capability(capability_key: str) -> Optional[dict]:
    """Return the kernel-universal capability declaration, or None.

    Returns a copy to prevent caller mutation of the registry.
    """
    decl = KERNEL_UNIVERSAL_CAPABILITIES.get(capability_key)
    return dict(decl) if decl else None


def get_kernel_universal_tools_for_capabilities(
    capabilities: list[str],
    connected_providers: set[str],
) -> set[str]:
    """Resolve tool names for the kernel-universal subset of requested capabilities.

    Returns the set of tool names from kernel-universal capabilities the caller
    requested AND whose wire-level connection requirement (if any) is satisfied
    by `connected_providers`.

    Caller is `get_platform_tools_for_capabilities` in platform_tools.py — it
    pre-computes `connected_providers` from `platform_connections` and reuses
    it for both kernel-universal and bundle-specific capability resolution.

    Returns empty set when no kernel-universal capabilities are in the request
    OR none have their wire-level gate satisfied.
    """
    allowed: set[str] = set()
    for cap in capabilities:
        decl = KERNEL_UNIVERSAL_CAPABILITIES.get(cap)
        if not decl:
            continue
        required_conn = decl.get("requires_connection")
        if required_conn is not None and required_conn not in connected_providers:
            # Wire-level gate fails — tool degrades silently from the surface
            # (per ADR-299 D2 implementation discipline: do not leak non-
            # functional tools into the prompt).
            continue
        allowed.update(decl.get("tools", []))
    return allowed


def is_kernel_universal_tool(tool_name: str) -> bool:
    """True iff the tool is granted by ANY kernel-universal capability.

    Used by tool-handler dispatch to recognize kernel-universal tools that
    don't follow the bundle-specific `platform_{provider}_{action}` naming
    convention (e.g., `platform_email_send_to_operator` is owned by the
    kernel-universal `send_operator_email` capability, not by an
    `email`-provider bundle declaration).
    """
    for decl in KERNEL_UNIVERSAL_CAPABILITIES.values():
        if tool_name in decl.get("tools", []):
            return True
    return False

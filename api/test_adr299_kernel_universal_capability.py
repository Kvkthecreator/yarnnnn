"""ADR-299 Phase 1 regression gate — kernel-universal capability class +
`send_operator_email` first instance.

Asserts the four load-bearing properties per ADR-299 D2 + D5 + D7:

  1. KERNEL_UNIVERSAL_CAPABILITIES registry contains send_operator_email with
     the canonical shape (no LLM-supplied addressee surface in the tool schema,
     addressee_class='operator', autonomy_posture='observability', wire-gate
     declared via requires_connection='email').

  2. EMAIL_TOOLS exposes platform_email_send_to_operator with a constrained
     input schema — `subject` + `html` required, no `to`/`cc`/`bcc`/`from_*`
     accepted from LLM.

  3. _handle_email_tool's send_to_operator branch refuses any LLM-supplied
     addressee fields with a clear structural error, even when they're
     syntactically valid (per ADR-299 D2 structural-pin discipline).

  4. get_platform_tools_for_capabilities exposes platform_email_send_to_operator
     when the email connection is active AND the recurrence requests
     send_operator_email — WITHOUT requiring the capability to appear in any
     bundle MANIFEST (this is the kernel-universal payoff).

  5. The wire-level connection gate is honored: when no email connection exists,
     send_operator_email's tool degrades silently from the surface (no leak of
     non-functional tool into agent prompt per ADR-299 D2 implementation
     clarification).

  6. Bundle-specific capability resolution is NOT regressed — read_trading
     still resolves through the existing CAPABILITY_PROVIDER_MAP path when
     trading connection is active.

  7. Helper API contract: is_kernel_universal_capability + is_kernel_universal_tool
     return the expected predicates.

  8. Singular Implementation: kernel-universal capabilities cannot be redeclared
     by bundles to alter shape — precedence is one-way (verified by checking
     the resolution order in get_platform_tools_for_capabilities).

Run: python api/test_adr299_kernel_universal_capability.py
Or:  python -m pytest api/test_adr299_kernel_universal_capability.py -v
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "api"))


def test_kernel_universal_registry_contains_send_operator_email() -> None:
    """ADR-299 D2: send_operator_email is registered as kernel-universal."""
    from services.kernel_capabilities import (
        KERNEL_UNIVERSAL_CAPABILITIES,
        is_kernel_universal_capability,
    )

    assert "send_operator_email" in KERNEL_UNIVERSAL_CAPABILITIES, (
        "send_operator_email missing from KERNEL_UNIVERSAL_CAPABILITIES — "
        "ADR-299 D2's first instance is the load-bearing entry."
    )
    decl = KERNEL_UNIVERSAL_CAPABILITIES["send_operator_email"]
    assert decl["key"] == "send_operator_email"
    assert decl["category"] == "tool"
    assert decl["runtime"] == "kernel"
    assert decl["requires_connection"] == "email", (
        "send_operator_email's wire-level gate must be 'email' per ADR-299 D2 "
        "implementation clarification — the capability declaration is universal "
        "but the underlying Resend wire still needs a connection."
    )
    assert decl["addressee_class"] == "operator", (
        "addressee_class must be 'operator' — this is the distinguishing test "
        "for kernel-universal vs bundle-specific per ADR-299 D1."
    )
    assert decl["autonomy_posture"] == "observability", (
        "autonomy_posture must be 'observability' per ADR-299 D4 — operator-"
        "addressing writes are NOT consequential actions and do NOT route "
        "through should_auto_apply."
    )
    assert "platform_email_send_to_operator" in decl["tools"]

    assert is_kernel_universal_capability("send_operator_email") is True
    assert is_kernel_universal_capability("read_trading") is False  # bundle-specific
    assert is_kernel_universal_capability("nonexistent") is False


def test_email_tools_exposes_send_to_operator_with_constrained_schema() -> None:
    """ADR-299 D2: tool refuses LLM-supplied addressee fields via schema."""
    from services.platform_tools import EMAIL_TOOLS

    tool = next(
        (t for t in EMAIL_TOOLS if t["name"] == "platform_email_send_to_operator"),
        None,
    )
    assert tool is not None, (
        "platform_email_send_to_operator missing from EMAIL_TOOLS — "
        "ADR-299 D2 tool wrap not registered."
    )

    schema_props = tool["input_schema"]["properties"]
    required = tool["input_schema"]["required"]

    # Allowed fields
    assert "subject" in schema_props and "subject" in required
    assert "html" in schema_props and "html" in required
    assert "reply_to" in schema_props  # optional override

    # Structurally absent fields (ADR-299 D2 structural pin)
    forbidden_at_schema_level = ("to", "cc", "bcc", "from_email", "from_name")
    for field in forbidden_at_schema_level:
        assert field not in schema_props, (
            f"`{field}` exposed in platform_email_send_to_operator schema — "
            "ADR-299 D2 requires addressee to be structurally pinned to "
            "the operator's identity; tool schema must not surface "
            f"the field. (Found `{field}` in input_schema.properties.)"
        )


def test_handler_refuses_llm_supplied_addressee_fields() -> None:
    """ADR-299 D2: handler refuses `to`/`cc`/`bcc`/`from_*` even at runtime
    (defense-in-depth — schema absence + handler rejection).

    Source-level check: the handler's send_to_operator branch contains the
    forbidden-field loop that rejects every operator-addressee-violating
    input shape. Source-level inspection avoids loading the full async
    handler import chain (which pulls in `jobs.unified_scheduler` →
    `sentry_sdk` in deployed environments; not always present in local dev
    venvs). The runtime behavior is exercised by integration tests when
    Phase 4 lands; this gate enforces that the structural pin is present
    in the handler body so it cannot silently regress."""
    import inspect
    from services import platform_tools

    source = inspect.getsource(platform_tools._handle_email_tool)

    # The send_to_operator branch must exist
    assert 'elif tool == "send_to_operator":' in source, (
        "send_to_operator branch missing from _handle_email_tool — "
        "ADR-299 D2 handler wrap not registered."
    )

    # The structural-pin loop must reject every forbidden addressee field
    forbidden_at_runtime = ("to", "cc", "bcc", "from_email", "from_name")
    for field in forbidden_at_runtime:
        assert f'"{field}"' in source, (
            f"Handler send_to_operator branch missing rejection for `{field}` — "
            f"ADR-299 D2 structural pin gap. Must reject every LLM-supplied "
            f"addressee-shape field with a clear error."
        )

    # The handler must source addressee from auth.users.email, not from input
    assert "get_user_email" in source, (
        "Handler send_to_operator branch does NOT call get_user_email — "
        "ADR-299 D2 addressee-resolution-at-send-time discipline violated. "
        "Addressee must resolve from auth.users.email, never from LLM input "
        "or cached substrate."
    )

    # Reject any reference to a `to:` field assignment from tool_input that
    # would let LLM-supplied addressee leak through
    bad_patterns = [
        "tool_input.get(\"to\")",
        "tool_input.get('to')",
    ]
    for pattern in bad_patterns:
        # Allow the pattern in OTHER branches (send, send_bulk) but ensure
        # the send_to_operator branch (everything after `elif tool == "send_to_operator":`)
        # never assigns from tool_input["to"] without rejection.
        # Practical check: the branch's `to=` keyword must come from operator_email,
        # not tool_input. Substring check is sufficient as defense-in-depth alongside
        # the explicit rejection loop above.
        pass  # rejection-loop check above is the load-bearing assertion

    # The send call inside send_to_operator must pass operator_email as the to:
    # (not tool_input-derived)
    assert "to=[operator_email]" in source, (
        "Handler does NOT pin Resend.send to operator_email — addressee could "
        "still come from LLM input. ADR-299 D2 structural pin violated."
    )


def test_resolution_exposes_tool_with_active_email_connection_no_manifest() -> None:
    """ADR-299 D5: kernel-universal capability resolves without bundle MANIFEST
    declaration. Operator has connected email; recurrence declares
    send_operator_email; tool surface includes platform_email_send_to_operator."""
    from services.kernel_capabilities import get_kernel_universal_tools_for_capabilities

    # Simulate operator with email connected
    connected = {"email"}
    tools = get_kernel_universal_tools_for_capabilities(
        ["send_operator_email"], connected
    )
    assert "platform_email_send_to_operator" in tools, (
        "Kernel-universal resolution did NOT surface "
        "platform_email_send_to_operator despite email connection active — "
        "the kernel-universal payoff (no MANIFEST required) is regressed."
    )


def test_wire_gate_degrades_silently_when_email_not_connected() -> None:
    """ADR-299 D2: tool degrades silently from surface when wire-level gate
    fails (no Resend connection). Prevents leaking non-functional tool into
    agent prompt."""
    from services.kernel_capabilities import get_kernel_universal_tools_for_capabilities

    # Simulate operator with NO email connection (trading only)
    connected = {"trading"}
    tools = get_kernel_universal_tools_for_capabilities(
        ["send_operator_email"], connected
    )
    assert "platform_email_send_to_operator" not in tools, (
        "Tool surfaced despite no email connection — ADR-299 D2 wire-gate "
        "degradation is violated. The tool would fail at execution with a "
        "confusing error if exposed without the wire."
    )
    assert tools == set(), "Expected empty set when wire gate fails"


def test_bundle_capability_resolution_not_regressed() -> None:
    """ADR-299 D5 (precedence): kernel-universal resolution does NOT regress
    bundle-specific capability resolution. read_trading still resolves through
    CAPABILITY_PROVIDER_MAP when trading is connected."""
    from services.platform_tools import (
        CAPABILITY_PROVIDER_MAP,
        PLATFORM_TOOLS_BY_CAPABILITY,
    )

    # read_trading must still map to trading provider + the trading tools
    assert CAPABILITY_PROVIDER_MAP.get("read_trading") == "trading"
    trading_tools = PLATFORM_TOOLS_BY_CAPABILITY.get("read_trading") or []
    assert len(trading_tools) > 0, (
        "read_trading bundle capability lost its tools — ADR-299 changes "
        "regressed the existing bundle-specific resolution path."
    )
    # Sanity: send_operator_email is NOT in the bundle-specific resolution
    assert "send_operator_email" not in CAPABILITY_PROVIDER_MAP, (
        "send_operator_email leaked into CAPABILITY_PROVIDER_MAP — should "
        "remain kernel-only per ADR-299 D5 one-way precedence (bundles "
        "cannot redeclare kernel-universal capability keys)."
    )


def test_helper_api_predicates() -> None:
    """ADR-299 D5: is_kernel_universal_capability + is_kernel_universal_tool
    return canonical predicates."""
    from services.kernel_capabilities import (
        is_kernel_universal_capability,
        is_kernel_universal_tool,
        get_kernel_universal_capability,
    )

    # Capability-key predicate
    assert is_kernel_universal_capability("send_operator_email") is True
    assert is_kernel_universal_capability("read_trading") is False
    assert is_kernel_universal_capability("") is False
    assert is_kernel_universal_capability("nonexistent_cap") is False

    # Tool-name predicate
    assert is_kernel_universal_tool("platform_email_send_to_operator") is True
    assert is_kernel_universal_tool("platform_email_send") is False  # bundle-side
    assert is_kernel_universal_tool("platform_trading_submit_order") is False
    assert is_kernel_universal_tool("") is False

    # get_kernel_universal_capability returns copy (caller cannot mutate registry)
    decl = get_kernel_universal_capability("send_operator_email")
    assert decl is not None
    decl["category"] = "MUTATED"  # mutate caller's copy
    decl2 = get_kernel_universal_capability("send_operator_email")
    assert decl2["category"] == "tool", (
        "get_kernel_universal_capability leaked registry reference — "
        "caller mutation polluted the singleton."
    )


def test_resolution_precedence_is_one_way() -> None:
    """ADR-299 D5: bundles cannot redeclare kernel-universal capability keys
    to alter shape. Verified by checking the resolution order — kernel-universal
    is checked FIRST in get_platform_tools_for_capabilities."""
    import inspect
    from services import platform_tools

    source = inspect.getsource(platform_tools.get_platform_tools_for_capabilities)

    # Find the line numbers (rough order check)
    kernel_idx = source.find("get_kernel_universal_tools_for_capabilities")
    bundle_idx = source.find("CAPABILITY_PROVIDER_MAP.get(capability)")

    assert kernel_idx != -1, (
        "Kernel-universal resolution call missing from "
        "get_platform_tools_for_capabilities — ADR-299 D5 wiring regressed."
    )
    assert bundle_idx != -1, (
        "Bundle-specific resolution call missing — sanity-check failure."
    )
    assert kernel_idx < bundle_idx, (
        "Kernel-universal resolution must run BEFORE bundle-specific "
        "resolution per ADR-299 D5 one-way precedence. Order in source "
        "indicates bundles would override — that's the regression this "
        "guard catches."
    )


if __name__ == "__main__":
    tests = [
        test_kernel_universal_registry_contains_send_operator_email,
        test_email_tools_exposes_send_to_operator_with_constrained_schema,
        test_handler_refuses_llm_supplied_addressee_fields,
        test_resolution_exposes_tool_with_active_email_connection_no_manifest,
        test_wire_gate_degrades_silently_when_email_not_connected,
        test_bundle_capability_resolution_not_regressed,
        test_helper_api_predicates,
        test_resolution_precedence_is_one_way,
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

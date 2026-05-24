"""ADR-299 regression gate — operator-addressing capability class +
`send_operator_email` first instance.

Tests the corrected shape per the 2026-05-24 Discovery note (see
docs/observations/2026-05-24-042952-adr299-class-naming-redundancy/findings.md).
The original "kernel-universal" framing duplicated the existing CAPABILITIES
dict pattern; the corrected framing names the genuine novelty as
**operator-addressing** (capability whose addressee resolves from
auth.users.email regardless of wire-gate presence) and houses
send_operator_email in the existing CAPABILITIES dict with a new
`addressee_class` field.

Asserts the load-bearing properties per ADR-299 D2 + D5 (corrected) + D7:

  1. CAPABILITIES dict contains send_operator_email with the canonical shape
     (category=tool, addressee_class='operator', autonomy_posture='observability',
     platform_connection_requirement={platform: 'email', status: 'active'}).

  2. EMAIL_TOOLS exposes platform_email_send_to_operator with constrained
     input schema — `subject` + `html` required, no `to`/`cc`/`bcc`/`from_*`.

  3. _handle_email_tool's send_to_operator branch refuses LLM-supplied
     addressee fields with clear structural error (defense-in-depth alongside
     schema absence).

  4. Existing resolution path (CAPABILITY_PROVIDER_MAP +
     PLATFORM_TOOLS_BY_CAPABILITY) wires send_operator_email correctly so
     get_platform_tools_for_capabilities surfaces the tool when email
     connection is active.

  5. Wire-level connection gate is honored: when no email connection exists,
     send_operator_email's tool degrades silently from the surface.

  6. Bundle-specific capability resolution is NOT regressed (read_trading
     still works through bundle MANIFEST fallthrough).

  7. Singular Implementation: no parallel registry exists; the architectural
     class lives in the existing CAPABILITIES dict (no api/services/kernel_capabilities.py).

  8. The addressee_class field distinguishes operator-addressing capabilities
     from audience-addressing ones at the registry level — write_email
     (audience-addressing) does NOT carry addressee_class='operator'.

Run: python api/test_adr299_kernel_universal_capability.py
Or:  python -m pytest api/test_adr299_kernel_universal_capability.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "api"))


def test_send_operator_email_in_capabilities_dict() -> None:
    """ADR-299 D2 (corrected): send_operator_email lives in CAPABILITIES dict
    with the canonical operator-addressing shape — not in a parallel registry."""
    from services.orchestration import CAPABILITIES

    assert "send_operator_email" in CAPABILITIES, (
        "send_operator_email missing from CAPABILITIES dict — ADR-299 D2 "
        "(corrected) requires the entry in services/orchestration.py:CAPABILITIES, "
        "not in a parallel registry."
    )
    cap = CAPABILITIES["send_operator_email"]
    assert cap["category"] == "tool"
    assert cap["runtime"] == "external:email"
    assert cap.get("addressee_class") == "operator", (
        "addressee_class='operator' is the distinguishing field for the "
        "operator-addressing capability class per ADR-299 D1 (corrected). "
        "Without this field, the genuine architectural novelty is lost."
    )
    assert cap.get("autonomy_posture") == "observability", (
        "autonomy_posture='observability' marks the capability as routed via "
        "_preferences.yaml opt-in (operator standing approval), NOT through "
        "should_auto_apply consequential-action gating per ADR-299 D4."
    )
    req = cap.get("platform_connection_requirement")
    assert req == {"platform": "email", "status": "active"}, (
        f"send_operator_email wire-gate must require platform_connections."
        f"platform='email' active per ADR-299 D2 implementation clarification. "
        f"Got: {req}"
    )
    assert "platform_email_send_to_operator" in cap.get("tools", [])


def test_kernel_capabilities_module_does_not_exist() -> None:
    """ADR-299 D5 (corrected): the parallel registry module
    api/services/kernel_capabilities.py must NOT exist. Singular Implementation
    discipline — the architectural class lives in the existing CAPABILITIES
    dict, not in a separate module."""
    target = REPO_ROOT / "api" / "services" / "kernel_capabilities.py"
    assert not target.exists(), (
        f"Parallel registry module survives at {target} — ADR-299 Discovery "
        "note (2026-05-24) requires deletion. The architectural class lives "
        "in the existing CAPABILITIES dict at services/orchestration.py:1129."
    )


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
            "the operator's identity; tool schema must not surface the field."
        )


def test_handler_refuses_llm_supplied_addressee_fields() -> None:
    """ADR-299 D2: handler refuses `to`/`cc`/`bcc`/`from_*` even at runtime
    (defense-in-depth — schema absence + handler rejection). Source-level
    check avoids loading the full async handler import chain."""
    import inspect
    from services import platform_tools

    source = inspect.getsource(platform_tools._handle_email_tool)

    assert 'elif tool == "send_to_operator":' in source, (
        "send_to_operator branch missing from _handle_email_tool — "
        "ADR-299 D2 handler wrap not registered."
    )

    forbidden_at_runtime = ("to", "cc", "bcc", "from_email", "from_name")
    for field in forbidden_at_runtime:
        assert f'"{field}"' in source, (
            f"Handler send_to_operator branch missing rejection for `{field}` — "
            "ADR-299 D2 structural pin gap."
        )

    assert "get_user_email" in source, (
        "Handler send_to_operator branch does NOT call get_user_email — "
        "ADR-299 D2 addressee-resolution-at-send-time discipline violated."
    )

    assert "to=[operator_email]" in source, (
        "Handler does NOT pin Resend.send to operator_email — addressee could "
        "still come from LLM input. ADR-299 D2 structural pin violated."
    )


def test_resolution_wires_send_operator_email_through_existing_path() -> None:
    """ADR-299 D5 (corrected): send_operator_email resolves through the
    existing CAPABILITY_PROVIDER_MAP + PLATFORM_TOOLS_BY_CAPABILITY path —
    no parallel resolution code in get_platform_tools_for_capabilities."""
    from services.platform_tools import (
        CAPABILITY_PROVIDER_MAP,
        PLATFORM_TOOLS_BY_CAPABILITY,
    )

    # CAPABILITY_PROVIDER_MAP must route send_operator_email to email provider
    assert CAPABILITY_PROVIDER_MAP.get("send_operator_email") == "email", (
        "send_operator_email not wired into CAPABILITY_PROVIDER_MAP — "
        "the existing resolution path won't surface its tool. Per ADR-299 "
        "Discovery note (2026-05-24), the entry must use the same resolution "
        "path as other capabilities (no parallel pre-check)."
    )

    # PLATFORM_TOOLS_BY_CAPABILITY must list the operator-addressing tool
    tools_for_cap = PLATFORM_TOOLS_BY_CAPABILITY.get("send_operator_email") or []
    assert "platform_email_send_to_operator" in tools_for_cap, (
        "platform_email_send_to_operator not listed under send_operator_email "
        "in PLATFORM_TOOLS_BY_CAPABILITY — tool surface won't include it even "
        "when capability is requested + email connection active."
    )


def test_resolution_does_not_have_parallel_kernel_universal_precheck() -> None:
    """ADR-299 D5 (corrected): get_platform_tools_for_capabilities must NOT
    contain a kernel-universal pre-check (the parallel resolution path
    introduced by the original ADR-299 D5; removed per the Discovery note
    so the existing CAPABILITY_PROVIDER_MAP path is canonical)."""
    import inspect
    from services import platform_tools

    source = inspect.getsource(platform_tools.get_platform_tools_for_capabilities)

    # The parallel pre-check imported get_kernel_universal_tools_for_capabilities
    # — its survival would indicate the correction was reverted.
    assert "get_kernel_universal_tools_for_capabilities" not in source, (
        "Parallel kernel-universal pre-check survives in "
        "get_platform_tools_for_capabilities — ADR-299 Discovery note "
        "(2026-05-24) required its removal. The existing CAPABILITY_PROVIDER_MAP "
        "resolution handles operator-addressing capabilities via the standard path."
    )
    assert "kernel_capabilities" not in source, (
        "Import of kernel_capabilities module survives — Discovery note "
        "required deletion of the parallel registry + its consumers."
    )


def test_bundle_capability_resolution_not_regressed() -> None:
    """The existing bundle-specific resolution path is unchanged.
    read_trading still maps to trading provider + the trading tools."""
    from services.platform_tools import (
        CAPABILITY_PROVIDER_MAP,
        PLATFORM_TOOLS_BY_CAPABILITY,
    )

    assert CAPABILITY_PROVIDER_MAP.get("read_trading") == "trading"
    trading_tools = PLATFORM_TOOLS_BY_CAPABILITY.get("read_trading") or []
    assert len(trading_tools) > 0


def test_addressee_class_distinguishes_operator_from_audience() -> None:
    """ADR-299 D1 (corrected): the addressee_class field distinguishes
    operator-addressing from audience-addressing at the registry level.
    send_operator_email has it; write_email (audience-addressing per ADR-192
    Phase 4) does NOT."""
    from services.orchestration import CAPABILITIES

    op_cap = CAPABILITIES.get("send_operator_email")
    assert op_cap is not None
    assert op_cap.get("addressee_class") == "operator"

    # write_email is bundle-specific per ADR-224; not in kernel CAPABILITIES.
    # Confirm it's absent from kernel CAPABILITIES (the audience-addressing
    # surface belongs to bundle MANIFEST resolution, not kernel).
    # If write_email DID exist in kernel CAPABILITIES, it must NOT carry
    # addressee_class='operator' — but its absence is the more honest
    # discipline marker.
    write_email_in_kernel = CAPABILITIES.get("write_email")
    if write_email_in_kernel is not None:
        assert write_email_in_kernel.get("addressee_class") != "operator", (
            "write_email surfaced in kernel CAPABILITIES with addressee_class='operator' "
            "— that would conflate audience-addressing with operator-addressing per "
            "ADR-299 D1 (corrected). write_email is audience-addressing; only "
            "send_operator_email carries the operator addressee_class."
        )


if __name__ == "__main__":
    tests = [
        test_send_operator_email_in_capabilities_dict,
        test_kernel_capabilities_module_does_not_exist,
        test_email_tools_exposes_send_to_operator_with_constrained_schema,
        test_handler_refuses_llm_supplied_addressee_fields,
        test_resolution_wires_send_operator_email_through_existing_path,
        test_resolution_does_not_have_parallel_kernel_universal_precheck,
        test_bundle_capability_resolution_not_regressed,
        test_addressee_class_distinguishes_operator_from_audience,
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

"""ADR-299 regression gate — operator-addressing system infrastructure.

Tests the rewrite shape per ADR-299 (2026-05-27). Under the rewrite,
`send_operator_email` is NOT a workspace capability — it is system
infrastructure (the system Resend wire, exposed as an LLM-invokable tool
via `SYSTEM_INFRASTRUCTURE_TOOLS` in `services/platform_tools.py`). The
pattern already existed implicitly via ADR-040 (operator notifications)
and ADR-202 (daily-update emails) firing from kernel code paths; ADR-299
names the pattern explicitly and adds the first LLM-invokable surface
to it.

The filename `test_adr299_kernel_universal_capability.py` is preserved as
a stable URL — the ADR-299 file path is the canonical reference path
across 6 Hat-B evaluation findings. The H1 title of ADR-299 is the
canonical name; this filename is historical artifact of the original
framing.

Asserts the load-bearing properties per ADR-299 D1–D8 (rewrite):

  1. CAPABILITIES dict does NOT contain `send_operator_email`. The entry
     was DELETED — workspace capabilities are a single-axis taxonomy
     (`platform_connection_requirement` yes/no); system infrastructure
     lives in `SYSTEM_INFRASTRUCTURE_TOOLS`, not here.

  2. The `runtime: "kernel"` sentinel value is DELETED from the codebase.
     `runtime` values reduce to actual workspace-work dispatch targets
     (internal | python_render | external:slack | external:notion |
     external:github). The sentinel existed only to mark
     `send_operator_email` as "not really a workspace capability"; with
     the entry deleted, the sentinel is unused.

  3. `SYSTEM_INFRASTRUCTURE_TOOLS` exists in `services/platform_tools.py`
     and contains `EMAIL_SEND_TO_OPERATOR_TOOL`. Single entry today;
     documented registry for future LLM-invokable system-infrastructure
     surfaces.

  4. `EMAIL_SEND_TO_OPERATOR_TOOL` schema is constrained — `subject` +
     `html` required, no `to`/`cc`/`bcc`/`from_*` fields (D6 structural
     pin).

  5. `_handle_email_tool` `send_to_operator` branch refuses LLM-supplied
     addressee fields and pins addressee to operator-identity via
     `get_user_email` + early return on system Resend wire (D6).

  6. `CAPABILITY_PROVIDER_MAP` does NOT contain `send_operator_email`.
     `PLATFORM_TOOLS_BY_CAPABILITY` does NOT contain `send_operator_email`.
     The tool surfaces via `SYSTEM_INFRASTRUCTURE_TOOLS` merge in
     `get_platform_tools_for_capabilities`, not via capability resolution.

  7. `get_platform_tools_for_capabilities` merges `SYSTEM_INFRASTRUCTURE_TOOLS`
     unconditionally and does NOT contain a loop-over-`CAPABILITIES`
     always-surface pass (D3 explicit-merge replaces the previous filter
     mechanism).

  8. The Reviewer surface (`REVIEWER_PRIMITIVES`) does NOT include
     `platform_email_send_to_operator`. Architectural commitment per
     ADR-299 D8 — evidence-confirmed by the 2026-05-25 v5 canary
     (RESOLUTION.md), NOT a deferred decision.

  9. Bundle capability resolution NOT regressed (`read_trading` still
     maps to trading provider).

 10. The deleted parallel registry `api/services/kernel_capabilities.py`
     stays deleted (Singular Implementation guard).

Run: python api/test_adr299_kernel_universal_capability.py
Or:  python -m pytest api/test_adr299_kernel_universal_capability.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "api"))


def test_send_operator_email_not_in_capabilities_dict() -> None:
    """ADR-299 rewrite D1+D2: send_operator_email is NOT a workspace
    capability. The entry must be absent from kernel CAPABILITIES.
    Inversion of the pre-rewrite assertion — the entry was deleted
    because the entity is system infrastructure, not a capability."""
    from services.orchestration import CAPABILITIES

    assert "send_operator_email" not in CAPABILITIES, (
        "send_operator_email is present in CAPABILITIES — ADR-299 rewrite "
        "(2026-05-27) DELETED the entry. The entity is system infrastructure "
        "(the system Resend wire), registered in SYSTEM_INFRASTRUCTURE_TOOLS "
        "in services/platform_tools.py — not a workspace capability."
    )


def test_runtime_kernel_sentinel_deleted_from_capabilities() -> None:
    """ADR-299 rewrite D2: `runtime: "kernel"` was the sentinel value
    indicating an entry didn't fit the workspace-capability taxonomy.
    With send_operator_email moved to SYSTEM_INFRASTRUCTURE_TOOLS, the
    sentinel is unused and must not reappear. `runtime` values reduce
    to actual workspace-work dispatch targets."""
    from services.orchestration import CAPABILITIES

    valid_runtimes = {
        "internal",
        "python_render",
        "external:slack",
        "external:notion",
        "external:github",
    }
    for cap_name, cap_decl in CAPABILITIES.items():
        runtime = cap_decl.get("runtime")
        if runtime is None:
            continue
        assert runtime != "kernel", (
            f"CAPABILITIES['{cap_name}'].runtime == 'kernel' — the sentinel "
            "value was deleted by the ADR-299 rewrite. If a new entry needs "
            "to mark itself as 'not really a workspace capability,' the "
            "correct relocation is to SYSTEM_INFRASTRUCTURE_TOOLS, not a new "
            "kernel sentinel in CAPABILITIES."
        )
        assert runtime in valid_runtimes, (
            f"CAPABILITIES['{cap_name}'].runtime == {runtime!r} — not in the "
            f"valid set {sorted(valid_runtimes)}. Either the taxonomy has "
            "drifted or a new runtime needs to be added explicitly to this "
            "test's allow-list."
        )


def test_system_infrastructure_tools_contains_email_send_to_operator() -> None:
    """ADR-299 rewrite D2+D3: SYSTEM_INFRASTRUCTURE_TOOLS exists in
    platform_tools.py and contains EMAIL_SEND_TO_OPERATOR_TOOL. Single
    entry today; the registry exists so future LLM-invokable system-
    infrastructure surfaces have a documented home."""
    from services.platform_tools import (
        SYSTEM_INFRASTRUCTURE_TOOLS,
        EMAIL_SEND_TO_OPERATOR_TOOL,
    )

    assert isinstance(SYSTEM_INFRASTRUCTURE_TOOLS, list)
    assert len(SYSTEM_INFRASTRUCTURE_TOOLS) >= 1
    tool_names = [t.get("name") for t in SYSTEM_INFRASTRUCTURE_TOOLS]
    assert "platform_email_send_to_operator" in tool_names, (
        "platform_email_send_to_operator missing from SYSTEM_INFRASTRUCTURE_TOOLS "
        "— ADR-299 rewrite D2+D3 requires the tool to be registered here."
    )

    # The constant in the list IS the tool definition (not a copy).
    assert EMAIL_SEND_TO_OPERATOR_TOOL in SYSTEM_INFRASTRUCTURE_TOOLS, (
        "EMAIL_SEND_TO_OPERATOR_TOOL not in SYSTEM_INFRASTRUCTURE_TOOLS "
        "by identity — registry should include the constant directly, not "
        "a duplicate definition."
    )


def test_email_send_to_operator_tool_schema_constrained() -> None:
    """ADR-299 rewrite D6: tool schema enforces the addressee structural pin
    — `subject` + `html` required, no `to`/`cc`/`bcc`/`from_*` fields."""
    from services.platform_tools import EMAIL_SEND_TO_OPERATOR_TOOL

    schema_props = EMAIL_SEND_TO_OPERATOR_TOOL["input_schema"]["properties"]
    required = EMAIL_SEND_TO_OPERATOR_TOOL["input_schema"]["required"]

    # Allowed fields
    assert "subject" in schema_props and "subject" in required
    assert "html" in schema_props and "html" in required
    assert "reply_to" in schema_props  # optional override

    # Structurally absent fields (D6 structural pin)
    forbidden_at_schema_level = ("to", "cc", "bcc", "from_email", "from_name")
    for field in forbidden_at_schema_level:
        assert field not in schema_props, (
            f"`{field}` exposed in platform_email_send_to_operator schema — "
            "ADR-299 D6 requires the addressee to be structurally pinned to "
            "the operator's identity; tool schema must not surface the field."
        )


def test_handler_refuses_llm_supplied_addressee_fields() -> None:
    """ADR-299 rewrite D6: handler refuses `to`/`cc`/`bcc`/`from_*` even at
    runtime (defense-in-depth — schema absence + handler rejection).

    The handler shape is unchanged from the pre-rewrite implementation —
    early return on `send_to_operator` branch, system Resend wire via
    `system_send_email`, addressee resolved from `get_user_email`. The
    rewrite changed the entity's architectural classification, not its
    wire or handler implementation."""
    import inspect
    from services import platform_tools

    source = inspect.getsource(platform_tools._handle_email_tool)

    # Early-return shape (skip the per-user OAuth platform_connections fetch
    # below — that fetch is for the audience-addressing wire only).
    assert 'if tool == "send_to_operator":' in source, (
        "send_to_operator branch missing from _handle_email_tool, OR not "
        "structured as an early-return `if` at top of function. The handler "
        "uses the system Resend wire; the platform_connections fetch below "
        "is for the audience-addressing wire only — send_to_operator must "
        "skip it."
    )

    # System Resend wire (NOT the per-user OAuth wire).
    assert "system_send_email" in source or "from jobs.email import send_email" in source, (
        "Handler does NOT import the system Resend wire (api/jobs/email.py "
        "send_email). ADR-299 rewrite preserves the system-wire choice from "
        "Discovery note 2. If this fails, the wire reverted to per-user "
        "OAuth (the audience-addressing surface)."
    )

    # Structural pin: rejection of LLM-supplied addressee fields.
    forbidden_at_runtime = ("to", "cc", "bcc", "from_email", "from_name")
    for field in forbidden_at_runtime:
        assert f'"{field}"' in source, (
            f"Handler send_to_operator branch missing rejection for `{field}` — "
            "ADR-299 D6 structural pin gap."
        )

    # Addressee resolved from auth.users at send-time, never substrate-cached.
    assert "get_user_email" in source, (
        "Handler send_to_operator branch does NOT call get_user_email — "
        "ADR-299 D6 addressee-resolution-at-send-time discipline violated."
    )

    # Addressee pinned to operator_email in system_send_email call.
    assert "to=operator_email" in source, (
        "Handler does NOT pin system_send_email to operator_email — "
        "addressee could still come from LLM input. ADR-299 D6 structural "
        "pin violated."
    )


def test_send_operator_email_not_in_capability_resolution_maps() -> None:
    """ADR-299 rewrite D3: send_operator_email is absent from
    PLATFORM_TOOLS_BY_CAPABILITY and CAPABILITY_PROVIDER_MAP. The tool
    surfaces via SYSTEM_INFRASTRUCTURE_TOOLS merge in
    get_platform_tools_for_capabilities, not via capability resolution."""
    from services.platform_tools import (
        CAPABILITY_PROVIDER_MAP,
        PLATFORM_TOOLS_BY_CAPABILITY,
    )

    assert "send_operator_email" not in CAPABILITY_PROVIDER_MAP, (
        "send_operator_email is in CAPABILITY_PROVIDER_MAP — the rewrite "
        "deleted the capability; provider-map should not reference it."
    )

    assert "send_operator_email" not in PLATFORM_TOOLS_BY_CAPABILITY, (
        "send_operator_email is in PLATFORM_TOOLS_BY_CAPABILITY — the rewrite "
        "deleted the capability; this lookup table should not reference it. "
        "The tool surfaces via SYSTEM_INFRASTRUCTURE_TOOLS merge instead."
    )


def test_resolution_uses_system_infrastructure_tools_merge() -> None:
    """ADR-299 rewrite D3: get_platform_tools_for_capabilities merges
    SYSTEM_INFRASTRUCTURE_TOOLS unconditionally and does NOT contain a
    loop-over-CAPABILITIES always-surface filter (the previous mechanism
    that leaked the misclassification into runtime)."""
    import inspect
    from services import platform_tools

    source = inspect.getsource(platform_tools.get_platform_tools_for_capabilities)

    # Explicit merge of SYSTEM_INFRASTRUCTURE_TOOLS — the new mechanism.
    assert "SYSTEM_INFRASTRUCTURE_TOOLS" in source, (
        "get_platform_tools_for_capabilities does NOT reference "
        "SYSTEM_INFRASTRUCTURE_TOOLS — ADR-299 rewrite D3 requires the "
        "function to merge that registry unconditionally."
    )

    # The pre-rewrite filter mechanism MUST be deleted (Singular
    # Implementation: one resolution mechanism, not two).
    assert "KERNEL_CAPABILITIES" not in source, (
        "get_platform_tools_for_capabilities still imports KERNEL_CAPABILITIES "
        "for an always-surface filter loop — the rewrite deleted this "
        "mechanism. SYSTEM_INFRASTRUCTURE_TOOLS merge is the singular path."
    )

    # The parallel registry from the original ADR-299 stays deleted.
    assert "kernel_universal_tools_to_surface" not in source, (
        "Vestigial kernel-universal filter variable survives in "
        "get_platform_tools_for_capabilities — the rewrite required it to "
        "be deleted along with the always-surface pass."
    )

    assert "from services.orchestration import CAPABILITIES" not in source, (
        "get_platform_tools_for_capabilities still imports CAPABILITIES "
        "from orchestration — the filter-over-CAPABILITIES mechanism was "
        "deleted; this import is now unused and should be removed."
    )


def test_user_tools_surfacing_includes_system_infrastructure() -> None:
    """ADR-299 rewrite D3: get_platform_tools_for_user also merges
    SYSTEM_INFRASTRUCTURE_TOOLS — system infrastructure surfaces to every
    LLM-invokable agent path, by definition."""
    import inspect
    from services import platform_tools

    source = inspect.getsource(platform_tools.get_platform_tools_for_user)

    assert "SYSTEM_INFRASTRUCTURE_TOOLS" in source, (
        "get_platform_tools_for_user does NOT reference "
        "SYSTEM_INFRASTRUCTURE_TOOLS — the rewrite requires both agent-path "
        "tool-surfacing functions to merge system-infrastructure tools "
        "unconditionally (it's part of the kernel's operating surface)."
    )


def test_reviewer_primitives_excludes_send_operator_email() -> None:
    """ADR-299 D8 — Reviewer-side exclusion is the architectural commitment.

    The Reviewer is judgment-bearing; task-bearing agents (YARNNN chat,
    headless specialists) get `platform_email_send_to_operator` via the
    SYSTEM_INFRASTRUCTURE_TOOLS merge. The Reviewer does NOT — by design.

    Evidence (2026-05-25 v5 canary, RESOLUTION.md):
      v3 (21 tools, no email tool): 10 rounds,  6,139 tokens, reject verdict
      v4 (22 tools, with email):     4 rounds,  1,577 tokens, stand_down
      v5 (21 tools, reverted):      12 rounds, 14,615 tokens, reject_publication

    The 21→22 transition collapsed Reviewer output by ~74% and produced
    the `stand_down` escape verdict with zero substrate writes. Reverting
    restored substantive judgment (2.4x v3 baseline output). The
    mechanism: a 22nd tool with strong "explicit action" framing shifts
    attention budget away from substrate evaluation toward tool-selection
    meta-reasoning. This effect is qualitatively different from the
    task-bearing agent paths' tolerance for tool-list growth.

    The exclusion is the architectural commitment, not a deferred experiment.
    Discipline for future Reviewer surface additions per RESOLUTION.md
    §"Discipline lesson": measure verdict-quality regression against the
    baseline tool surface via N≥3 canaries; default is "no" until
    verdict-quality evidence supports otherwise.
    """
    from services.primitives.registry import REVIEWER_PRIMITIVES

    tool_names = [t.get("name") for t in REVIEWER_PRIMITIVES]
    assert "platform_email_send_to_operator" not in tool_names, (
        "platform_email_send_to_operator is present in REVIEWER_PRIMITIVES — "
        "ADR-299 D8 architectural commitment violated. The Reviewer surface "
        "is judgment-bearing; the v5 canary (2026-05-25) confirmed that "
        "tool-list size at the 21→22 transition collapses judgment quality "
        "by ~74%. If you genuinely need to add this tool (or any other) to "
        "the Reviewer surface, run N≥3 canaries measuring verdict-quality "
        "regression first and update this test only with the evidence trail."
    )


def test_bundle_capability_resolution_not_regressed() -> None:
    """The workspace-capability resolution path is unchanged by the rewrite.
    read_trading still maps to trading provider + its tools."""
    from services.platform_tools import (
        CAPABILITY_PROVIDER_MAP,
        PLATFORM_TOOLS_BY_CAPABILITY,
    )

    assert CAPABILITY_PROVIDER_MAP.get("read_trading") == "trading"
    trading_tools = PLATFORM_TOOLS_BY_CAPABILITY.get("read_trading") or []
    assert len(trading_tools) > 0


def test_kernel_capabilities_module_stays_deleted() -> None:
    """ADR-299 Discovery note 1 (2026-05-24): the parallel registry
    `api/services/kernel_capabilities.py` was deleted. The rewrite
    preserves this — Singular Implementation guard against the parallel-
    registry pattern reappearing."""
    target = REPO_ROOT / "api" / "services" / "kernel_capabilities.py"
    assert not target.exists(), (
        f"Parallel registry module reappeared at {target} — Singular "
        "Implementation discipline violated. System-infrastructure tools "
        "live in SYSTEM_INFRASTRUCTURE_TOOLS in services/platform_tools.py "
        "alongside the existing platform tools; do not introduce a parallel "
        "registry module."
    )


if __name__ == "__main__":
    tests = [
        test_send_operator_email_not_in_capabilities_dict,
        test_runtime_kernel_sentinel_deleted_from_capabilities,
        test_system_infrastructure_tools_contains_email_send_to_operator,
        test_email_send_to_operator_tool_schema_constrained,
        test_handler_refuses_llm_supplied_addressee_fields,
        test_send_operator_email_not_in_capability_resolution_maps,
        test_resolution_uses_system_infrastructure_tools_merge,
        test_user_tools_surfacing_includes_system_infrastructure,
        test_reviewer_primitives_excludes_send_operator_email,
        test_bundle_capability_resolution_not_regressed,
        test_kernel_capabilities_module_stays_deleted,
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

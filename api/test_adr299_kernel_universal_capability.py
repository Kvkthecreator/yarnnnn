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


def test_system_infrastructure_tools_contains_operator_addressing_writes() -> None:
    """ADR-299 D2+D3 + ADR-304 D1+D2: SYSTEM_INFRASTRUCTURE_TOOLS contains
    all three operator-addressing writes — email (ADR-299), Slack DM and
    Notion comment (ADR-304 generalization). Each constant is included
    by identity (no duplicate definitions)."""
    from services.platform_tools import (
        SYSTEM_INFRASTRUCTURE_TOOLS,
        EMAIL_SEND_TO_OPERATOR_TOOL,
        SLACK_SEND_MESSAGE_TOOL,
        NOTION_CREATE_COMMENT_TOOL,
    )

    assert isinstance(SYSTEM_INFRASTRUCTURE_TOOLS, list)
    assert len(SYSTEM_INFRASTRUCTURE_TOOLS) >= 3
    tool_names = [t.get("name") for t in SYSTEM_INFRASTRUCTURE_TOOLS]

    expected = {
        "platform_email_send_to_operator",
        "platform_slack_send_message",
        "platform_notion_create_comment",
    }
    for name in expected:
        assert name in tool_names, (
            f"{name} missing from SYSTEM_INFRASTRUCTURE_TOOLS — ADR-304 D1+D2 "
            f"requires all three operator-addressing writes registered here."
        )

    # Each constant is in the list by identity (Singular Implementation —
    # no duplicate definitions across module-level constant + per-provider list).
    for const in (EMAIL_SEND_TO_OPERATOR_TOOL, SLACK_SEND_MESSAGE_TOOL, NOTION_CREATE_COMMENT_TOOL):
        assert const in SYSTEM_INFRASTRUCTURE_TOOLS, (
            f"{const['name']} not in SYSTEM_INFRASTRUCTURE_TOOLS by identity — "
            "registry should include the constant directly, not a duplicate."
        )


def test_slack_send_message_lifted_out_of_slack_tools() -> None:
    """ADR-304 D2: platform_slack_send_message MUST NOT survive in
    SLACK_TOOLS (which is now read-tools only). Singular Implementation —
    tool defined once at module level as SLACK_SEND_MESSAGE_TOOL."""
    from services.platform_tools import SLACK_TOOLS

    slack_tool_names = [t.get("name") for t in SLACK_TOOLS]
    assert "platform_slack_send_message" not in slack_tool_names, (
        "platform_slack_send_message survives in SLACK_TOOLS — ADR-304 D2 "
        "lifted it to SLACK_SEND_MESSAGE_TOOL + SYSTEM_INFRASTRUCTURE_TOOLS. "
        "SLACK_TOOLS should contain only read tools."
    )


def test_notion_create_comment_lifted_out_of_notion_tools() -> None:
    """ADR-304 D2: platform_notion_create_comment MUST NOT survive in
    NOTION_TOOLS (which is now read-tools only). Singular Implementation."""
    from services.platform_tools import NOTION_TOOLS

    notion_tool_names = [t.get("name") for t in NOTION_TOOLS]
    assert "platform_notion_create_comment" not in notion_tool_names, (
        "platform_notion_create_comment survives in NOTION_TOOLS — ADR-304 "
        "D2 lifted it to NOTION_CREATE_COMMENT_TOOL + SYSTEM_INFRASTRUCTURE_TOOLS. "
        "NOTION_TOOLS should contain only read tools."
    )


def test_write_slack_and_write_notion_are_kernel_universal_audience_writes() -> None:
    """ADR-304 amendment (2026-06-19): write_slack + write_notion are KERNEL-
    UNIVERSAL audience-write capabilities (the operator-confirmed ambient
    capability), declared in kernel CAPABILITIES with `feeds: action` ⇒ HIGH
    tier, WITH the ADR-307 uniform gate as the safety floor.

    Reverses ADR-304 D2 (which deleted these keys). The invariant that MUST
    hold: they point at the AUDIENCE-write tools, NEVER back at the operator-
    addressing infrastructure tools (platform_slack_send_message /
    platform_notion_create_comment, which stay in SYSTEM_INFRASTRUCTURE_TOOLS
    per ADR-304 D1)."""
    from services.orchestration import CAPABILITIES, required_tier

    for cap_name in ("write_slack", "write_notion"):
        assert cap_name in CAPABILITIES, (
            f"{cap_name} must be in kernel CAPABILITIES — the ADR-304 amendment "
            f"(2026-06-19) makes audience-writes kernel-universal (ambient, no "
            f"per-program friction)."
        )
        cap = CAPABILITIES[cap_name]
        assert cap.get("feeds") == "action", (
            f"{cap_name} must declare `feeds: action` so required_tier=HIGH "
            f"(it is a primary external write)."
        )
        assert required_tier(cap) == "HIGH", f"{cap_name} required_tier must be HIGH"
        # Points at audience-write tools, never the operator-addressing infra.
        tools = set(cap.get("tools") or [])
        assert "platform_slack_send_message" not in tools
        assert "platform_notion_create_comment" not in tools

    assert "platform_slack_send_to_channel" in (CAPABILITIES["write_slack"].get("tools") or [])
    assert {"platform_notion_create_page", "platform_notion_append_block"} <= set(
        CAPABILITIES["write_notion"].get("tools") or []
    )


def test_operator_addressing_writes_stay_system_infrastructure() -> None:
    """ADR-304 D1 (preserved by the 2026-06-19 amendment): the operator-DM Slack
    send + operator-page Notion comment remain operator-addressing system
    infrastructure. The kernel-universal write_slack / write_notion audience
    capabilities point at DISTINCT audience tools (asserted in the
    capabilities test), never at these infra tools."""
    from services.platform_tools import SYSTEM_INFRASTRUCTURE_TOOLS

    infra_names = {t.get("name") for t in SYSTEM_INFRASTRUCTURE_TOOLS}
    assert "platform_slack_send_message" in infra_names
    assert "platform_notion_create_comment" in infra_names


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


def test_reviewer_primitives_excludes_all_system_infrastructure_tools() -> None:
    """ADR-299 D8 + ADR-304 D6 — Reviewer-side exclusion is the architectural
    commitment, applies to ALL system-infrastructure tools.

    The Reviewer is judgment-bearing; task-bearing agents (YARNNN chat,
    headless specialists) get all SYSTEM_INFRASTRUCTURE_TOOLS via the
    merge. The Reviewer does NOT — by design.

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
    from services.platform_tools import SYSTEM_INFRASTRUCTURE_TOOLS

    reviewer_tool_names = {t.get("name") for t in REVIEWER_PRIMITIVES}
    system_infra_names = {t.get("name") for t in SYSTEM_INFRASTRUCTURE_TOOLS}

    overlap = reviewer_tool_names & system_infra_names
    assert not overlap, (
        f"Reviewer surface includes system-infrastructure tools: {overlap}. "
        "ADR-299 D8 + ADR-304 D6 architectural commitment violated — the "
        "Reviewer is judgment-bearing and the v5 canary (2026-05-25) "
        "confirmed that tool-list size at the 21→22 transition collapses "
        "judgment quality by ~74%. The commitment generalizes: ALL system-"
        "infrastructure tools (current + future) are excluded from "
        "REVIEWER_PRIMITIVES. If you genuinely need to add any tool to the "
        "Reviewer surface, run N≥3 canaries measuring verdict-quality "
        "regression first and update this test only with the evidence trail."
    )


def test_reviewer_primitives_excludes_all_platform_write_tools() -> None:
    """ADR-304 D6 (preserved by the 2026-06-19 kernel-universal amendment): the
    Reviewer reaches external effect ONLY via ProposeAction. It has NO platform
    write tool — neither the new kernel-universal audience-writes (write_slack /
    write_notion → channel post / page create / block append) nor any capital
    write. Making audience-writes kernel-universal must NOT leak a platform
    write into the Reviewer surface; the seat stays propose-only."""
    from services.primitives.registry import REVIEWER_PRIMITIVES
    from services.platform_tools import is_platform_tool

    reviewer_tool_names = {t.get("name") for t in REVIEWER_PRIMITIVES}
    platform_in_reviewer = {n for n in reviewer_tool_names if is_platform_tool(n or "")}
    assert not platform_in_reviewer, (
        f"Reviewer surface includes platform tools: {platform_in_reviewer}. "
        "ADR-299 D8 / ADR-304 D6: the Reviewer is propose-only — it reaches "
        "external effect via ProposeAction, never a direct platform write. "
        "Kernel-universal audience-writes (ADR-304 amendment) surface to "
        "task-bearing agent paths via PLATFORM_TOOLS_BY_CAPABILITY, NOT to "
        "REVIEWER_PRIMITIVES."
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
        test_system_infrastructure_tools_contains_operator_addressing_writes,
        test_slack_send_message_lifted_out_of_slack_tools,
        test_notion_create_comment_lifted_out_of_notion_tools,
        test_write_slack_and_write_notion_are_kernel_universal_audience_writes,
        test_operator_addressing_writes_stay_system_infrastructure,
        test_reviewer_primitives_excludes_all_platform_write_tools,
        test_email_send_to_operator_tool_schema_constrained,
        test_handler_refuses_llm_supplied_addressee_fields,
        test_send_operator_email_not_in_capability_resolution_maps,
        test_resolution_uses_system_infrastructure_tools_merge,
        test_user_tools_surfacing_includes_system_infrastructure,
        test_reviewer_primitives_excludes_all_system_infrastructure_tools,
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

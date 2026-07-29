"""ADR-501 regression gate — the read path follows the binding, and the
ceiling follows the grant.

Two halves:
  1. BEHAVIORAL — `_is_path_locked_for_principal` is EXECUTED (not grepped)
     against member / owner / no-grant / freddie / explicit-scope auth shapes,
     with the grant lookup stubbed. This is the S1 security fix: a member's
     NULL-scope grant must resolve to the AGENT class (the ADR-373 D3 member
     ceiling), not the operator transport default — while freddie/system
     callers must NOT inherit the owner grant's operator class.
  2. SWEEP — source assertions that each rescoped endpoint reads through the
     workspace spine (substrate_scope_filter / acting_workspace_owner /
     _purge_scope), so a revert re-fails loudly. (Gates grep text, not
     execution — the behavioral half above is the load-bearing one.)

Run: cd api && python3 -m pytest test_adr501_read_path_binding.py -q
"""

from __future__ import annotations

import pathlib
from types import SimpleNamespace

import pytest

API = pathlib.Path(__file__).parent


# ---------------------------------------------------------------------------
# 1. Behavioral — the gate itself
# ---------------------------------------------------------------------------

from services.primitives import workspace as wsp  # noqa: E402


def _auth(caller_identity: str = "operator") -> SimpleNamespace:
    return SimpleNamespace(
        user_id="00000000-0000-0000-0000-000000000001",
        principal_id="00000000-0000-0000-0000-000000000001",
        workspace_id="00000000-0000-0000-0000-0000000000ws",
        caller_identity=caller_identity,
        freddie_caller=caller_identity.startswith("freddie:"),
        client=None,
    )


@pytest.fixture()
def stub_axes(monkeypatch):
    """Stub the grant lookup; each test sets `holder['axes']`."""
    holder = {"axes": None}
    monkeypatch.setattr(wsp, "_lookup_grant_axes", lambda auth: holder["axes"])
    return holder


def test_member_null_scopes_gets_agent_ceiling(stub_axes):
    """THE S1 FIX: a member's NULL-scope grant → agent class, so governance/
    constitution/persona/contract are locked and operation/ is open."""
    stub_axes["axes"] = {"read": None, "write": None, "role": "member"}
    auth = _auth("operator")
    for locked in (
        "/workspace/governance/_autonomy.yaml",
        "/workspace/constitution/MANDATE.md",
        "/workspace/persona/IDENTITY.md",
        "/workspace/contract/_preferences.yaml",
        "/workspace/system/manifest.json",
    ):
        assert wsp._is_path_locked_for_principal(auth, locked), locked
    assert not wsp._is_path_locked_for_principal(auth, "/workspace/operation/notes.md")


def test_member_lane_caller_gets_agent_ceiling(stub_axes):
    """ADR-411 D4 lane writes run under the member's grant → same ceiling."""
    stub_axes["axes"] = {"read": None, "write": None, "role": "member"}
    auth = _auth("member:00000000-0000-0000-0000-000000000001 via anthropic/claude")
    assert wsp._is_path_locked_for_principal(auth, "/workspace/governance/_budget.yaml")
    assert not wsp._is_path_locked_for_principal(auth, "/workspace/operation/notes.md")


def test_owner_byte_identical(stub_axes):
    """owner → operator on both the role table and the transport default."""
    stub_axes["axes"] = {"read": None, "write": None, "role": "owner"}
    auth = _auth("operator")
    assert not wsp._is_path_locked_for_principal(auth, "/workspace/governance/_autonomy.yaml")
    assert not wsp._is_path_locked_for_principal(auth, "/workspace/constitution/MANDATE.md")
    assert wsp._is_path_locked_for_principal(auth, "/workspace/system/manifest.json")


def test_no_grant_keeps_transport_class(stub_axes):
    """No grant row (pre-grant paths) → today's transport fallback, unchanged."""
    stub_axes["axes"] = None
    auth = _auth("operator")
    assert not wsp._is_path_locked_for_principal(auth, "/workspace/governance/_autonomy.yaml")
    assert wsp._is_path_locked_for_principal(auth, "/workspace/system/manifest.json")


def test_freddie_not_widened_by_owner_grant(stub_axes):
    """THE GUARD: the steward resolves its principal to the owner's user_id, so
    the owner grant's operator class must NOT leak onto a freddie caller."""
    stub_axes["axes"] = {"read": None, "write": None, "role": "owner"}
    auth = _auth("freddie:sonnet")
    assert wsp._is_path_locked_for_principal(auth, "/workspace/governance/_autonomy.yaml")
    assert wsp._is_path_locked_for_principal(auth, "/workspace/system/manifest.json")
    assert not wsp._is_path_locked_for_principal(auth, "/workspace/operation/notes.md")


def test_explicit_write_scopes_unchanged(stub_axes):
    """An explicit allow-list still wins over any class default."""
    stub_axes["axes"] = {"read": None, "write": ["operation/reports/"], "role": "member"}
    auth = _auth("operator")
    assert not wsp._is_path_locked_for_principal(auth, "/workspace/operation/reports/q3.md")
    assert wsp._is_path_locked_for_principal(auth, "/workspace/operation/notes.md")
    assert wsp._is_path_locked_for_principal(auth, "/workspace/governance/_autonomy.yaml")


def test_role_class_is_the_d3_table():
    from services.principals import role_class

    assert role_class("owner") == "operator"
    assert role_class("member") == "agent"
    assert role_class("own-agent") == "agent"
    assert role_class("foreign-llm") == "mcp"
    assert role_class("a2a") == "mcp"
    assert role_class(None) is None
    assert role_class("unknown-role") is None


def test_display_and_gate_read_one_table():
    """The roster's member write_regions must equal the complement the gate now
    enforces — one table, two readers (the S1 contradiction, closed)."""
    from services.principals import class_default_write_regions, role_class
    from services.workspace_paths import CALLER_WRITE_POLICY

    regions = class_default_write_regions("member")
    locked = set(CALLER_WRITE_POLICY[role_class("member")])
    assert "operation/" in regions
    assert not (set(regions) & locked)


# ---------------------------------------------------------------------------
# 2. Sweep — each rescoped endpoint reads through the spine
# ---------------------------------------------------------------------------


def _src(rel: str) -> str:
    return (API / rel).read_text()


def test_radar_routes_are_owner_keyed():
    src = _src("routes/radar.py")
    assert "_acting_owner" in src
    assert 'discover_radar_hubs(auth.client).get(actor' in src
    # No data query keys on the raw caller anymore.
    assert '.eq("user_id", auth.user_id)' not in src
    assert "_read_declaration(auth.client, actor" in src  # the 409 guard sees the workspace


def test_nav_recurrences_workspace_scoped():
    src = _src("routes/workspace.py")
    idx = src.index('table("tasks")')
    window = src[idx: idx + 500]
    assert "_substrate_scope_filter(auth)" in window
    assert '.eq("user_id", auth.user_id)' not in window


def test_activity_and_heartbeat_workspace_scoped():
    src = _src("routes/system.py")
    ev = src.index('table("execution_events")')
    assert "substrate_scope_filter" in src[ev - 600: ev + 900]
    hb = src.index('"scheduler_heartbeat"')
    assert "substrate_scope_filter" in src[hb - 900: hb]


def test_emissions_owner_keyed():
    src = _src("routes/emissions.py")
    assert "acting_workspace_owner(auth.client, auth.user_id)" in src


def test_alpha_evaluator_workspace_scoped():
    src = _src("routes/alpha_trader.py")
    idx = src.index('"signal-evaluation"')
    assert "substrate_scope_filter" in src[idx - 900: idx]


def test_purge_preview_and_l3_workspace_scoped():
    src = _src("routes/account.py")
    stats = src.index("def get_danger_zone_stats")
    window = src[stats: stats + 2600]
    assert "resolve_purge_workspace(user_id)" in window
    assert "_purge_scope(" in window
    # The residual helpers thread workspace_id.
    assert "def _count_workspace_paths(\n    client, user_id: str, path_prefix: str, workspace_id" in src
    assert "def _delete_workspace_file_versions_by_path(\n    client, user_id: str, path_prefix: str, workspace_id" in src
    l3 = src.index("async def clear_integrations")
    assert "resolve_purge_workspace" in src[l3: l3 + 3000]


def test_principal_roster_binding_aware():
    src = _src("services/principals.py")
    fn = src.index("def load_principal_roster")
    window = src[fn: fn + 1400]
    assert "effective_workspace_id(user_id)" in window
    assert "resolve_owner_workspace_id(user_id)" not in window


def test_memberships_carries_can_clear():
    src = _src("routes/workspace.py")
    assert "can_clear: bool" in src
    assert "has_workspace_clear_authority(auth.user_id, acting)" in src


def test_danger_zone_reads_verdict_not_role():
    src = (API.parent / "web/components/workspace-concepts/WorkspaceDangerZone.tsx").read_text()
    assert "ms.can_clear" in src
    assert 'active?.role === "owner"' not in src


def test_dead_code_deleted():
    assert not (API.parent / "web/lib/entity-cache.ts").exists()
    src = (API.parent / "web/lib/workspace/upload-frontmatter.ts").read_text()
    assert "export function resolveContentUrl" not in src


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))

"""Gate — actor identity (authored_by) on the narrative envelope (2026-06-30).

The actor-identity unification: every narrative row carries the ADR-209
`authored_by` taxonomy string so the FE (attribution.ts + principal-badge.tsx)
shows WHO acted — "ChatGPT (via MCP)" / "Claude" / "Freddie" / "You" — instead
of collapsing every non-human actor to "system" on the Flow / Notifications /
chat surfaces.

This gate locks the BACKEND half: the serializer accepts + stamps authored_by
into the metadata envelope (same layer as writtenTo/tool), and each live call
site passes the right taxonomy string. Pure file-assertion + a serializer
envelope check (no DB) per ADR-236 Rule 3.

Run: cd api && python -m pytest test_authored_by_narrative.py -q
"""

from __future__ import annotations

from pathlib import Path

_API = Path(__file__).resolve().parent


_WEB = _API.parent / "web"


def _read(rel: str) -> str:
    return (_API / rel).read_text(encoding="utf-8")


def _read_web(rel: str) -> str:
    return (_WEB / rel).read_text(encoding="utf-8")


# ---- 1. the serializer threads authored_by into the envelope ----------------

def test_write_narrative_entry_accepts_and_stamps_authored_by():
    src = _read("services/narrative.py")
    # The param exists on the signature…
    assert "authored_by: Optional[str] = None" in src
    # …and lands in the envelope (rides the same metadata layer as writtenTo).
    assert 'envelope["authored_by"] = authored_by' in src


def test_append_message_pops_authored_by_to_envelope_param():
    # append_message (feed.py) must pop authored_by to the explicit param so a
    # caller can add it to its metadata dict the same way it adds pulse/weight.
    src = _read("routes/feed.py")
    assert 'authored_by = md.pop("authored_by", None)' in src
    assert "authored_by=authored_by," in src


# ---- 2. each live call site stamps the right taxonomy string ----------------

def test_operator_message_authored_as_operator():
    src = _read("routes/feed.py")
    assert '"authored_by": "operator"' in src


def test_mcp_writes_authored_as_mcp_host():
    # The interop wedge: an external-LLM write is attributed by host so the FE
    # renders "ChatGPT (via MCP)" / "Claude (via MCP)". client_name is the
    # canonical lowercase host slug attribution.ts keys on.
    src = _read("mcp_server/server.py")
    assert 'authored_by=f"yarnnn:mcp:{client_name}"' in src


def test_freddie_authored_as_reviewer():
    src = _read("services/freddie_chat_surfacing.py")
    assert 'authored_by=f"freddie:{occupant}" if occupant else "freddie:reviewer"' in src
    # The action-narration site distinguishes the persona Clarify from the
    # system-agent-directed action.
    assert '"freddie:reviewer"' in src
    assert '"system:reviewer-directed"' in src


def test_system_agent_paths_authored_as_system():
    src = _read("routes/feed.py")
    assert '"authored_by": "system:execution-router"' in src
    assert '"authored_by": "system:agent-gate"' in src


def test_notification_authored_as_system():
    src = _read("services/notifications.py")
    assert 'authored_by="system:notification"' in src


# ---- 3. the taxonomy strings are within the ADR-209 / attribution shape -----

def test_authored_by_strings_match_attribution_classes():
    """Every authored_by string we emit must classify into a known FE
    AuthorClass prefix (the attribution.ts startswith table), so none falls
    through to 'unknown' and renders without an icon."""
    known_prefixes = (
        "operator",
        "yarnnn:mcp:",
        "yarnnn:",
        "freddie:",
        "reviewer:",
        "agent:",
        "a2a:",
        "specialist:",
        "platform:",
        "system:",
    )
    emitted = [
        "operator",
        "yarnnn:mcp:{client_name}",
        "freddie:{occupant}",
        "freddie:reviewer",
        "system:reviewer-directed",
        "system:execution-router",
        "system:agent-gate",
        "system:notification",
    ]
    for s in emitted:
        assert any(s.startswith(p) for p in known_prefixes), (
            f"authored_by {s!r} does not classify into a known AuthorClass"
        )


# ---- 4. the FE registry + wire consume authored_by --------------------------

def test_fe_narrative_envelope_carries_authored_by():
    desk = _read_web("types/desk.ts")
    assert "authoredBy?: string" in desk
    client = _read_web("lib/api/client.ts")
    assert "authored_by?: string" in client
    loader = _read_web("contexts/NarrativeContext.tsx")
    assert "authoredBy: m.metadata.authored_by" in loader


def test_fe_principal_badge_extends_attribution_with_icon():
    # The badge is the visual half built ON attribution.ts (the ADR-388 seam),
    # not a parallel module — it imports the pure classifier/label.
    badge = _read_web("lib/workspace/principal-badge.tsx")
    assert "from './attribution'" in badge
    assert "export function PrincipalBadge" in badge
    assert "export function principalIcon" in badge
    # Brand-SVG-where-known, glyph fallback (the operator's icon-style decision).
    assert "getMcpHostIcon" in badge
    icons = _read_web("components/ui/PlatformIcons.tsx")
    assert "ClaudeIcon" in icons and "ChatGPTIcon" in icons
    assert "export function getMcpHostIcon" in icons


def test_fe_surfaces_adopt_the_badge():
    # Flow rows + chat routine row + notifications activity all render the
    # shared badge (registry + shared primitive, per-surface layout kept).
    for rel in (
        "components/feed/StandaloneEventRow.tsx",
        "components/feed/OperatorEventMarker.tsx",
        "components/tp/MessageRow.tsx",
        "components/shell/AttentionCenter.tsx",
    ):
        src = _read_web(rel)
        assert "PrincipalBadge" in src, f"{rel} does not adopt PrincipalBadge"


if __name__ == "__main__":
    import sys

    passed = failed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  ✓ {name}")
                passed += 1
            except AssertionError as exc:
                print(f"  ✗ {name} — {exc}")
                failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)

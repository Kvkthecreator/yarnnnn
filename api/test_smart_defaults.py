"""
Test: compute_smart_defaults() heuristics — ADR-113

Validates that smart defaults select work-relevant sources over noise
using the multi-signal scoring introduced in ADR-113.

Run: cd api && python test_smart_defaults.py
"""

import sys
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(message)s")


def test_slack_prefers_work_over_noise():
    """#engineering (30 members) should rank above #random (500 members)."""
    from services.landscape import compute_smart_defaults

    resources = [
        {"id": "C1", "name": "#random", "type": "channel", "metadata": {"num_members": 500, "purpose": "fun stuff and memes"}},
        {"id": "C2", "name": "#engineering", "type": "channel", "metadata": {"num_members": 30, "purpose": "engineering team discussions"}},
        {"id": "C3", "name": "#social", "type": "channel", "metadata": {"num_members": 200, "purpose": "non-work social chat"}},
        {"id": "C4", "name": "#product-launches", "type": "channel", "metadata": {"num_members": 50, "purpose": "launch coordination"}},
        {"id": "C5", "name": "#pets", "type": "channel", "metadata": {"num_members": 100, "purpose": "cute animal photos"}},
        {"id": "C6", "name": "#incident-response", "type": "channel", "metadata": {"num_members": 15, "purpose": "production incidents"}},
        {"id": "C7", "name": "#general", "type": "channel", "metadata": {"num_members": 400, "purpose": "company announcements"}},
        {"id": "C8", "name": "#watercooler", "type": "channel", "metadata": {"num_members": 300, "purpose": "off-topic watercooler chat"}},
    ]

    selected = compute_smart_defaults("slack", resources, max_sources=3)
    selected_ids = [s["id"] for s in selected]

    # Work channels should be selected
    assert "C2" in selected_ids, f"#engineering should be selected, got {selected_ids}"
    assert "C7" in selected_ids, f"#general should be selected, got {selected_ids}"

    # Noise channels should NOT be selected (despite higher member count)
    assert "C1" not in selected_ids, f"#random should NOT be selected, got {selected_ids}"
    assert "C3" not in selected_ids, f"#social should NOT be selected, got {selected_ids}"
    assert "C5" not in selected_ids, f"#pets should NOT be selected, got {selected_ids}"
    assert "C8" not in selected_ids, f"#watercooler should NOT be selected, got {selected_ids}"

    logger.info("✓ Slack: work channels ranked above noise channels")


def test_slack_purpose_text_boosts():
    """Channels with work-relevant purpose text should rank higher."""
    from services.landscape import compute_smart_defaults

    resources = [
        {"id": "C1", "name": "#alpha", "type": "channel", "metadata": {"num_members": 20, "purpose": "weekly sprint planning and roadmap updates"}},
        {"id": "C2", "name": "#beta", "type": "channel", "metadata": {"num_members": 20, "purpose": ""}},
        {"id": "C3", "name": "#gamma", "type": "channel", "metadata": {"num_members": 20, "purpose": "random fun and games"}},
    ]

    selected = compute_smart_defaults("slack", resources, max_sources=1)
    assert selected[0]["id"] == "C1", f"Channel with work purpose should rank first, got {selected[0]}"

    logger.info("✓ Slack: purpose text with work keywords boosts ranking")


def test_slack_private_small_deprioritized():
    """Private channels with <3 members should be deprioritized."""
    from services.landscape import compute_smart_defaults

    resources = [
        {"id": "C1", "name": "#dm-like", "type": "channel", "metadata": {"num_members": 2, "is_private": True, "purpose": ""}},
        {"id": "C2", "name": "#small-team", "type": "channel", "metadata": {"num_members": 5, "is_private": False, "purpose": ""}},
    ]

    selected = compute_smart_defaults("slack", resources, max_sources=1)
    assert selected[0]["id"] == "C2", f"Public channel should rank above tiny private, got {selected[0]}"

    logger.info("✓ Slack: private channels with <3 members deprioritized")


def test_notion_databases_over_pages():
    """Databases should rank above pages (project trackers > random notes)."""
    from services.landscape import compute_smart_defaults

    resources = [
        {"id": "N1", "name": "Random Note", "type": "page", "metadata": {"parent_type": "page", "last_edited": "2026-03-15T10:00:00Z"}},
        {"id": "N2", "name": "Sprint Tracker", "type": "database", "metadata": {"parent_type": "workspace", "last_edited": "2026-03-14T10:00:00Z"}},
        {"id": "N3", "name": "Untitled", "type": "page", "metadata": {"parent_type": "page", "last_edited": "2026-03-16T10:00:00Z"}},
        {"id": "N4", "name": "Team Wiki", "type": "page", "metadata": {"parent_type": "workspace", "last_edited": "2026-03-13T10:00:00Z"}},
    ]

    selected = compute_smart_defaults("notion", resources, max_sources=2)
    selected_ids = [s["id"] for s in selected]

    # Database + workspace should be top picks
    assert "N2" in selected_ids, f"Sprint Tracker (database+workspace) should be selected, got {selected_ids}"
    # Untitled should NOT be selected despite being most recent
    assert "N3" not in selected_ids, f"Untitled should NOT be selected, got {selected_ids}"

    logger.info("✓ Notion: databases and workspace pages ranked above untitled/nested pages")


def test_notion_untitled_deprioritized():
    """Untitled pages should rank last even if recently edited."""
    from services.landscape import compute_smart_defaults

    resources = [
        {"id": "N1", "name": "Untitled", "type": "page", "metadata": {"parent_type": "page", "last_edited": "2026-03-16T12:00:00Z"}},
        {"id": "N2", "name": "Meeting Notes", "type": "page", "metadata": {"parent_type": "page", "last_edited": "2026-03-10T10:00:00Z"}},
    ]

    selected = compute_smart_defaults("notion", resources, max_sources=1)
    assert selected[0]["id"] == "N2", f"Named page should rank above Untitled, got {selected[0]}"

    logger.info("✓ Notion: Untitled pages deprioritized despite recency")


def test_gmail_unchanged():
    """Gmail heuristics should still prioritize INBOX > SENT > user labels."""
    from services.landscape import compute_smart_defaults

    resources = [
        {"id": "INBOX", "name": "INBOX", "type": "label", "metadata": {"type": "system", "platform": "gmail"}},
        {"id": "SENT", "name": "SENT", "type": "label", "metadata": {"type": "system", "platform": "gmail"}},
        {"id": "STARRED", "name": "STARRED", "type": "label", "metadata": {"type": "system", "platform": "gmail"}},
        {"id": "SPAM", "name": "SPAM", "type": "label", "metadata": {"type": "system", "platform": "gmail"}},
        {"id": "Label_1", "name": "Projects/Active", "type": "label", "metadata": {"type": "user", "platform": "gmail"}},
    ]

    selected = compute_smart_defaults("google", resources, max_sources=3)
    selected_ids = [s["id"] for s in selected]

    assert selected_ids[0] == "INBOX", f"INBOX should be first, got {selected_ids}"
    assert selected_ids[1] == "SENT", f"SENT should be second, got {selected_ids}"
    assert "SPAM" not in selected_ids, f"SPAM should not be selected, got {selected_ids}"

    logger.info("✓ Gmail: INBOX > SENT > user labels, noise excluded")


def test_empty_resources():
    """Empty resource list should return empty selection."""
    from services.landscape import compute_smart_defaults

    assert compute_smart_defaults("slack", [], 5) == []
    assert compute_smart_defaults("notion", [], 5) == []
    assert compute_smart_defaults("google", [], 5) == []

    logger.info("✓ Edge case: empty resources returns empty selection")


def test_max_sources_respected():
    """Should never return more than max_sources."""
    from services.landscape import compute_smart_defaults

    resources = [
        {"id": f"C{i}", "name": f"#team-{i}", "type": "channel", "metadata": {"num_members": 100}}
        for i in range(20)
    ]

    selected = compute_smart_defaults("slack", resources, max_sources=3)
    assert len(selected) == 3, f"Should return exactly 3, got {len(selected)}"

    selected = compute_smart_defaults("slack", resources, max_sources=1)
    assert len(selected) == 1, f"Should return exactly 1, got {len(selected)}"

    logger.info("✓ Edge case: max_sources limit respected")


if __name__ == "__main__":
    tests = [
        test_slack_prefers_work_over_noise,
        test_slack_purpose_text_boosts,
        test_slack_private_small_deprioritized,
        test_notion_databases_over_pages,
        test_notion_untitled_deprioritized,
        test_gmail_unchanged,
        test_empty_resources,
        test_max_sources_respected,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            logger.error(f"✗ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            logger.error(f"✗ {test.__name__}: unexpected error: {e}")
            failed += 1

    logger.info(f"\n{'=' * 50}")
    logger.info(f"Results: {passed} passed, {failed} failed out of {len(tests)}")

    if failed > 0:
        sys.exit(1)
    logger.info("All smart default heuristic tests passed.")

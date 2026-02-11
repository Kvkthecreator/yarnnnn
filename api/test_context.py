"""
Quick test for context builder (ADR-038)

Run: cd api && python test_context.py
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone

# Test the formatting functions (no DB required)
from services.context import (
    format_context_for_prompt,
    estimate_context_tokens,
    _calculate_freshness,
)


def test_format_context_for_prompt():
    """Test that context formats correctly for prompt injection."""
    context = {
        "user_profile": {
            "name": "Kevin",
            "role": "Founder",
            "preferences": {},
            "timezone": "Asia/Seoul",
        },
        "user_facts": [
            "Presenting to board next month",
            "Prefers bullet-point format",
        ],
        "active_deliverables": [
            {
                "id": "uuid-1",
                "title": "Weekly Status",
                "frequency": "weekly",
                "recipient": "Product Team",
                "next_run": "2026-02-12T09:00:00Z",
            },
            {
                "id": "uuid-2",
                "title": "Board Update",
                "frequency": "monthly",
                "recipient": "Marcus",
                "next_run": "2026-03-01T09:00:00Z",
            },
        ],
        "connected_platforms": [
            {
                "provider": "slack",
                "status": "connected",
                "last_synced": "2026-02-11T08:00:00Z",
                "freshness": "fresh",
            },
            {
                "provider": "notion",
                "status": "connected",
                "last_synced": "2026-02-09T08:00:00Z",
                "freshness": "2 days ago",
            },
        ],
        "recent_sessions": [
            {
                "date": "2026-02-10",
                "summary": "Discussed pausing the weekly report",
            },
        ],
    }

    formatted = format_context_for_prompt(context)

    print("=== Formatted Context ===")
    print(formatted)
    print()

    # Assertions
    assert "Kevin" in formatted, "Should contain user name"
    assert "Founder" in formatted, "Should contain user role"
    assert "Presenting to board next month" in formatted, "Should contain user fact"
    assert "Weekly Status" in formatted, "Should contain deliverable title"
    assert "slack" in formatted, "Should contain platform"
    assert "2026-02-10" in formatted, "Should contain session date"

    print("✅ format_context_for_prompt: PASSED")
    return formatted


def test_estimate_context_tokens():
    """Test token estimation stays under budget."""
    context = {
        "user_profile": {"name": "Kevin", "role": "Founder"},
        "user_facts": ["Fact 1", "Fact 2", "Fact 3"],
        "active_deliverables": [
            {"id": f"uuid-{i}", "title": f"Deliverable {i}", "frequency": "weekly", "recipient": "Team"}
            for i in range(5)
        ],
        "connected_platforms": [
            {"provider": "slack", "status": "connected", "freshness": "fresh"},
            {"provider": "notion", "status": "connected", "freshness": "1 day ago"},
        ],
        "recent_sessions": [
            {"date": "2026-02-10", "summary": "Session summary here"},
        ],
    }

    tokens = estimate_context_tokens(context)
    print(f"Estimated tokens: {tokens}")

    assert tokens < 2000, f"Token count {tokens} exceeds budget of 2000"
    print("✅ estimate_context_tokens: PASSED")
    return tokens


def test_calculate_freshness():
    """Test freshness calculation."""
    now = datetime.now(timezone.utc)

    # Fresh (< 1 hour)
    recent = (now - timedelta(minutes=30)).isoformat()
    assert _calculate_freshness(recent, now) == "fresh"

    # Hours ago
    hours_ago = (now - timedelta(hours=5)).isoformat()
    assert "hours ago" in _calculate_freshness(hours_ago, now)

    # Days ago
    days_ago = (now - timedelta(days=3)).isoformat()
    assert "days ago" in _calculate_freshness(days_ago, now)

    # Stale
    stale = (now - timedelta(days=10)).isoformat()
    assert "stale" in _calculate_freshness(stale, now)

    # Never synced
    assert _calculate_freshness(None, now) == "never synced"

    print("✅ _calculate_freshness: PASSED")


def test_empty_context():
    """Test handling of empty context."""
    context = {
        "user_profile": {},
        "user_facts": [],
        "active_deliverables": [],
        "connected_platforms": [],
        "recent_sessions": [],
    }

    formatted = format_context_for_prompt(context)
    print("=== Empty Context ===")
    print(formatted)

    # Should still have header
    assert "Your Context" in formatted

    print("✅ empty context: PASSED")


if __name__ == "__main__":
    print("\n🧪 Running context builder tests...\n")

    test_calculate_freshness()
    test_empty_context()
    formatted = test_format_context_for_prompt()
    tokens = test_estimate_context_tokens()

    print(f"\n✅ All tests passed! Estimated token usage: {tokens}/2000")

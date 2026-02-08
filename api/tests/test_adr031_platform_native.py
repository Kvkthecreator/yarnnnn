"""
ADR-031 Platform-Native Deliverables Test Suite

Comprehensive validation of:
1. Phase 6: Cross-platform synthesizers and project resources
2. Phase 4: Event triggers and cooldown logic
3. Phase 2: Platform output generation (Slack blocks, Gmail HTML)
4. Multi-destination delivery

This test uses the service key to bypass RLS for testing.
"""

import os
import sys
import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import hashlib

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
TEST_USER_ID = "2abf3f96-118b-4987-9d95-40f2d9be9a18"


def get_client():
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


class TestResults:
    def __init__(self):
        self.passed = []
        self.failed = []

    def record(self, name, passed, details=""):
        if passed:
            self.passed.append((name, details))
            print(f"  ✓ {name}")
        else:
            self.failed.append((name, details))
            print(f"  ✗ {name}: {details}")

    def summary(self):
        total = len(self.passed) + len(self.failed)
        print(f"\n{'='*60}")
        print(f"Results: {len(self.passed)}/{total} tests passed")
        if self.failed:
            print("\nFailed tests:")
            for name, details in self.failed:
                print(f"  - {name}: {details}")
        print('='*60)
        return len(self.failed) == 0


# =============================================================================
# Phase 6: Schema Tests
# =============================================================================

def test_phase6_schema(results):
    """Validate database schema for ADR-031 Phase 6."""
    print("\n=== Phase 6 Schema Validation ===")
    client = get_client()

    # Test 1: project_resources table exists
    try:
        result = client.table("project_resources").select("*").limit(1).execute()
        results.record("project_resources table exists", True)
    except Exception as e:
        results.record("project_resources table exists", False, str(e))
        return

    # Test 2: synthesizer_context_log table exists
    try:
        result = client.table("synthesizer_context_log").select("*").limit(1).execute()
        results.record("synthesizer_context_log table exists", True)
    except Exception as e:
        results.record("synthesizer_context_log table exists", False, str(e))

    # Test 3: destination_delivery_log table exists
    try:
        result = client.table("destination_delivery_log").select("*").limit(1).execute()
        results.record("destination_delivery_log table exists", True)
    except Exception as e:
        results.record("destination_delivery_log table exists", False, str(e))

    # Test 4: deliverables has destinations column
    try:
        result = client.table("deliverables").select("destinations").limit(1).execute()
        results.record("deliverables.destinations column exists", True)
    except Exception as e:
        results.record("deliverables.destinations column exists", False, str(e))

    # Test 5: deliverables has is_synthesizer column
    try:
        result = client.table("deliverables").select("is_synthesizer").limit(1).execute()
        results.record("deliverables.is_synthesizer column exists", True)
    except Exception as e:
        results.record("deliverables.is_synthesizer column exists", False, str(e))


# =============================================================================
# Phase 6: Cross-Platform Synthesizer Tests
# =============================================================================

def test_cross_platform_synthesizer(results):
    """Test cross-platform synthesizer service functions."""
    print("\n=== Cross-Platform Synthesizer Service ===")

    from services.cross_platform_synthesizer import (
        PlatformResource,
        ContextItem,
        AssembledContext,
        format_context_for_prompt,
    )

    # Test 1: PlatformResource dataclass
    try:
        resource = PlatformResource(
            id="test-id",
            platform="slack",
            resource_type="channel",
            resource_id="C123",
            resource_name="#general",
            is_primary=True,
            include_filters={"message_types": ["user"]},
            exclude_filters={},
            last_synced_at=None,
        )
        results.record("PlatformResource dataclass works", resource.platform == "slack")
    except Exception as e:
        results.record("PlatformResource dataclass works", False, str(e))

    # Test 2: ContextItem dataclass
    try:
        item = ContextItem(
            platform="slack",
            resource_id="C123",
            resource_name="#general",
            content="Test message",
            content_type="message",
            source_timestamp=datetime.now(timezone.utc),
            platform_metadata={"thread_ts": "123.456"},
        )
        results.record("ContextItem dataclass works", item.platform == "slack")
    except Exception as e:
        results.record("ContextItem dataclass works", False, str(e))

    # Test 3: AssembledContext dataclass
    try:
        context = AssembledContext(
            items=[],
            sources_summary=[],
            total_items_pulled=0,
            total_after_dedup=0,
            platforms_used=["slack"],
            time_range_start=datetime.now(timezone.utc) - timedelta(days=7),
            time_range_end=datetime.now(timezone.utc),
            freshness_score=0.8,
            overlap_score=0.1,
        )
        results.record("AssembledContext dataclass works", context.freshness_score == 0.8)
    except Exception as e:
        results.record("AssembledContext dataclass works", False, str(e))

    # Test 4: format_context_for_prompt with empty context
    try:
        context = AssembledContext(
            items=[],
            sources_summary=[],
            total_items_pulled=0,
            total_after_dedup=0,
            platforms_used=[],
            time_range_start=datetime.now(timezone.utc),
            time_range_end=datetime.now(timezone.utc),
            freshness_score=0.0,
            overlap_score=0.0,
        )
        prompt = format_context_for_prompt(context)
        results.record("format_context_for_prompt handles empty context", "No context available" in prompt)
    except Exception as e:
        results.record("format_context_for_prompt handles empty context", False, str(e))

    # Test 5: format_context_for_prompt with items
    try:
        items = [
            ContextItem(
                platform="slack",
                resource_id="C123",
                resource_name="#general",
                content="Hello world",
                content_type="message",
                source_timestamp=datetime.now(timezone.utc),
                platform_metadata={},
            ),
            ContextItem(
                platform="gmail",
                resource_id="inbox",
                resource_name="Inbox",
                content="Email content here",
                content_type="email",
                source_timestamp=datetime.now(timezone.utc),
                platform_metadata={},
            ),
        ]
        context = AssembledContext(
            items=items,
            sources_summary=[
                {"platform": "slack", "resource_id": "C123", "items_count": 1},
                {"platform": "gmail", "resource_id": "inbox", "items_count": 1},
            ],
            total_items_pulled=2,
            total_after_dedup=2,
            platforms_used=["slack", "gmail"],
            time_range_start=datetime.now(timezone.utc) - timedelta(days=7),
            time_range_end=datetime.now(timezone.utc),
            freshness_score=0.9,
            overlap_score=0.05,
        )
        prompt = format_context_for_prompt(context)
        # The function uses platform.title() so check for Slack/Gmail
        has_slack = "Slack" in prompt
        has_gmail = "Gmail" in prompt
        results.record("format_context_for_prompt groups by platform", has_slack and has_gmail)
    except Exception as e:
        results.record("format_context_for_prompt groups by platform", False, str(e))


# =============================================================================
# Phase 6: Project Resources API Tests
# =============================================================================

async def test_project_resources_api(results):
    """Test project resources CRUD operations."""
    print("\n=== Project Resources API ===")
    client = get_client()

    # Get any workspace
    workspace_result = client.table("workspaces").select("id").limit(1).execute()
    if not workspace_result.data:
        results.record("Project Resources API tests", False, "No workspace available for test")
        return
    workspace_id = workspace_result.data[0]["id"]

    # Get or create a test project
    project_result = client.table("projects").select("id").eq("workspace_id", workspace_id).limit(1).execute()
    if not project_result.data:
        # Create a test project
        try:
            create_result = client.table("projects").insert({
                "workspace_id": workspace_id,
                "name": "Test Project for ADR-031",
            }).execute()
            if create_result.data:
                project_id = create_result.data[0]["id"]
            else:
                results.record("Project Resources API tests", False, "Could not create test project")
                return
        except Exception as e:
            results.record("Project Resources API tests", False, f"Project creation failed: {e}")
            return
    else:
        project_id = project_result.data[0]["id"]

    # Test 1: Create a project resource
    test_resource_id = f"test-{uuid4().hex[:8]}"
    try:
        insert_result = client.table("project_resources").insert({
            "project_id": project_id,
            "user_id": TEST_USER_ID,
            "platform": "slack",
            "resource_type": "channel",
            "resource_id": test_resource_id,
            "resource_name": "#test-channel",
            "is_primary": False,
            "include_filters": {},
        }).execute()

        if insert_result.data:
            created_id = insert_result.data[0]["id"]
            results.record("Create project resource", True)
        else:
            results.record("Create project resource", False, "No data returned")
            return
    except Exception as e:
        results.record("Create project resource", False, str(e))
        return

    # Test 2: Query project resources
    try:
        query_result = client.table("project_resources").select("*").eq(
            "project_id", project_id
        ).eq("resource_id", test_resource_id).execute()

        results.record("Query project resource", len(query_result.data) > 0)
    except Exception as e:
        results.record("Query project resource", False, str(e))

    # Test 3: Update resource (set as primary)
    try:
        update_result = client.table("project_resources").update({
            "is_primary": True
        }).eq("id", created_id).execute()

        results.record("Update project resource", update_result.data[0]["is_primary"] == True)
    except Exception as e:
        results.record("Update project resource", False, str(e))

    # Test 4: Delete resource
    try:
        delete_result = client.table("project_resources").delete().eq(
            "id", created_id
        ).execute()

        results.record("Delete project resource", True)
    except Exception as e:
        results.record("Delete project resource", False, str(e))

    # Test 5: Verify deletion
    try:
        verify_result = client.table("project_resources").select("id").eq(
            "id", created_id
        ).execute()

        results.record("Verify resource deleted", len(verify_result.data) == 0)
    except Exception as e:
        results.record("Verify resource deleted", False, str(e))


# =============================================================================
# Phase 4: Event Trigger Tests
# =============================================================================

def test_event_triggers(results):
    """Test event trigger matching and cooldown logic."""
    print("\n=== Event Trigger Logic ===")

    from services.event_triggers import (
        PlatformEvent,
        CooldownConfig,
        TriggerMatch,
        check_cooldown,
        record_trigger,
        cleanup_expired_cooldowns,
        _get_cooldown_key,
        _cooldown_cache,
    )

    # Clear cooldown cache before tests
    _cooldown_cache.clear()

    # Test 1: PlatformEvent dataclass
    try:
        event = PlatformEvent(
            platform="slack",
            event_type="message",
            user_id=TEST_USER_ID,
            resource_id="C123",
            resource_name="#general",
            event_data={"text": "Hello"},
            event_ts=datetime.now(timezone.utc),
            thread_id=None,
            sender_id="U456",
            content_preview="Hello",
        )
        results.record("PlatformEvent dataclass works", event.platform == "slack")
    except Exception as e:
        results.record("PlatformEvent dataclass works", False, str(e))

    # Test 2: Cooldown key generation - global
    try:
        event = PlatformEvent(
            platform="slack",
            event_type="message",
            user_id=TEST_USER_ID,
            resource_id="C123",
            resource_name=None,
            event_data={},
            event_ts=datetime.now(timezone.utc),
        )
        key = _get_cooldown_key("del-123", "global", event)
        results.record("Cooldown key - global", key == "del-123:global")
    except Exception as e:
        results.record("Cooldown key - global", False, str(e))

    # Test 3: Cooldown key generation - per_channel
    try:
        key = _get_cooldown_key("del-123", "per_channel", event)
        results.record("Cooldown key - per_channel", key == "del-123:channel:C123")
    except Exception as e:
        results.record("Cooldown key - per_channel", False, str(e))

    # Test 4: Cooldown key generation - per_sender
    try:
        event_with_sender = PlatformEvent(
            platform="slack",
            event_type="message",
            user_id=TEST_USER_ID,
            resource_id="C123",
            resource_name=None,
            event_data={},
            event_ts=datetime.now(timezone.utc),
            sender_id="U789",
        )
        key = _get_cooldown_key("del-123", "per_sender", event_with_sender)
        results.record("Cooldown key - per_sender", key == "del-123:sender:U789")
    except Exception as e:
        results.record("Cooldown key - per_sender", False, str(e))

    # Test 5: Check cooldown - not in cooldown
    try:
        _cooldown_cache.clear()
        cooldown = CooldownConfig(
            type="global",
            duration_minutes=5,
            max_triggers_per_duration=1,
        )
        in_cooldown, reason = check_cooldown("del-new", cooldown, event)
        results.record("Check cooldown - not in cooldown", in_cooldown == False)
    except Exception as e:
        results.record("Check cooldown - not in cooldown", False, str(e))

    # Test 6: Record trigger and check cooldown
    try:
        record_trigger("del-test", cooldown, event)
        in_cooldown, reason = check_cooldown("del-test", cooldown, event)
        results.record("Check cooldown - in cooldown after record", in_cooldown == True)
    except Exception as e:
        results.record("Check cooldown - in cooldown after record", False, str(e))

    # Test 7: Cleanup expired cooldowns
    try:
        # Add an old entry
        old_key = "del-old:global"
        _cooldown_cache[old_key] = datetime.now(timezone.utc) - timedelta(hours=2)

        count = cleanup_expired_cooldowns()
        results.record("Cleanup expired cooldowns", count >= 1 and old_key not in _cooldown_cache)
    except Exception as e:
        results.record("Cleanup expired cooldowns", False, str(e))


# =============================================================================
# Phase 2: Platform Output Tests
# =============================================================================

def test_platform_output(results):
    """Test platform-native output generation."""
    print("\n=== Platform Output Generation ===")

    from services.platform_output import (
        generate_slack_blocks,
        generate_gmail_html,
        generate_platform_output,
        _chunk_text,
        _markdown_to_mrkdwn,
        _markdown_to_email_html,
    )

    # Test 1: Generate Slack blocks - basic
    try:
        blocks = generate_slack_blocks("Hello world", "default", {})
        has_blocks = isinstance(blocks, list) and len(blocks) > 0
        results.record("Generate Slack blocks - basic", has_blocks)
    except Exception as e:
        results.record("Generate Slack blocks - basic", False, str(e))

    # Test 2: Generate Slack blocks - digest variant
    try:
        content = """## Summary
This is a summary.

## Key Discussions
- Discussion 1
- Discussion 2
"""
        blocks = generate_slack_blocks(content, "slack_digest", {"channel_name": "#general"})
        results.record("Generate Slack blocks - digest", len(blocks) > 1)
    except Exception as e:
        results.record("Generate Slack blocks - digest", False, str(e))

    # Test 3: Markdown to mrkdwn conversion
    try:
        # Test bold conversion (** -> *)
        mrkdwn = _markdown_to_mrkdwn("**bold** text")
        has_bold = "*bold*" in mrkdwn and "**" not in mrkdwn
        # Test strikethrough conversion (~~ -> ~)
        mrkdwn2 = _markdown_to_mrkdwn("~~strikethrough~~")
        has_strike = "~strikethrough~" in mrkdwn2 and "~~" not in mrkdwn2
        results.record("Markdown to mrkdwn conversion", has_bold and has_strike)
    except Exception as e:
        results.record("Markdown to mrkdwn conversion", False, str(e))

    # Test 4: Text chunking - within limit
    try:
        chunks = _chunk_text("Short text", max_length=2800)
        results.record("Text chunking - within limit", len(chunks) == 1)
    except Exception as e:
        results.record("Text chunking - within limit", False, str(e))

    # Test 5: Text chunking - exceeds limit
    try:
        # Create multi-paragraph text that will need chunking
        paragraph = "This is a paragraph with some content. " * 30  # ~1200 chars
        long_text = f"{paragraph}\n\n{paragraph}\n\n{paragraph}\n\n{paragraph}"  # ~5000 chars
        chunks = _chunk_text(long_text, max_length=2800)
        all_within_limit = all(len(c) <= 2800 for c in chunks)
        results.record("Text chunking - exceeds limit", len(chunks) > 1 and all_within_limit)
    except Exception as e:
        results.record("Text chunking - exceeds limit", False, str(e))

    # Test 6: Generate Gmail HTML - basic
    try:
        html = generate_gmail_html("Hello world", "default", {})
        has_html = "<html>" in html or "<div" in html
        results.record("Generate Gmail HTML - basic", has_html)
    except Exception as e:
        results.record("Generate Gmail HTML - basic", False, str(e))

    # Test 7: Generate Gmail HTML - digest variant
    try:
        html = generate_gmail_html("# Summary\n\nContent here", "email_weekly_digest", {"title": "Weekly Digest"})
        has_container = "container" in html
        results.record("Generate Gmail HTML - digest", has_container)
    except Exception as e:
        results.record("Generate Gmail HTML - digest", False, str(e))

    # Test 8: Markdown to email HTML
    try:
        html = _markdown_to_email_html("**bold** and [link](http://example.com)")
        has_strong = "<strong>bold</strong>" in html
        has_link = 'href="http://example.com"' in html
        results.record("Markdown to email HTML", has_strong and has_link)
    except Exception as e:
        results.record("Markdown to email HTML", False, str(e))

    # Test 9: Unified platform output - Slack
    try:
        output = generate_platform_output("slack", "Hello", "default", {})
        results.record("Unified output - Slack", output["format"] == "blocks")
    except Exception as e:
        results.record("Unified output - Slack", False, str(e))

    # Test 10: Unified platform output - Gmail
    try:
        output = generate_platform_output("gmail", "Hello", "default", {})
        results.record("Unified output - Gmail", output["format"] == "html")
    except Exception as e:
        results.record("Unified output - Gmail", False, str(e))

    # Test 11: Empty content handling
    try:
        blocks = generate_slack_blocks("", "default", {})
        results.record("Empty content handling", isinstance(blocks, list))
    except Exception as e:
        results.record("Empty content handling", False, str(e))


# =============================================================================
# Multi-Destination Delivery Tests
# =============================================================================

def test_multi_destination_delivery(results):
    """Test multi-destination delivery logic."""
    print("\n=== Multi-Destination Delivery ===")

    from services.delivery import MultiDestinationResult

    # Test 1: MultiDestinationResult dataclass
    try:
        result = MultiDestinationResult(
            total_destinations=3,
            succeeded=2,
            failed=1,
            results=[
                {"destination_index": 0, "platform": "slack", "status": "delivered"},
                {"destination_index": 1, "platform": "gmail", "status": "delivered"},
                {"destination_index": 2, "platform": "notion", "status": "failed", "error": "Not connected"},
            ],
            all_succeeded=False,
        )
        results.record("MultiDestinationResult dataclass", result.failed == 1)
    except Exception as e:
        results.record("MultiDestinationResult dataclass", False, str(e))

    # Test 2: All succeeded flag
    try:
        result = MultiDestinationResult(
            total_destinations=2,
            succeeded=2,
            failed=0,
            results=[],
            all_succeeded=True,
        )
        results.record("All succeeded flag", result.all_succeeded == True)
    except Exception as e:
        results.record("All succeeded flag", False, str(e))


# =============================================================================
# Deliverable Type Config Tests
# =============================================================================

def test_deliverable_types(results):
    """Test ADR-031 deliverable type configurations."""
    print("\n=== Deliverable Type Configs ===")

    from routes.deliverables import (
        WeeklyStatusConfig,
        ProjectBriefConfig,
        CrossPlatformDigestConfig,
        ActivitySummaryConfig,
        TYPE_TIERS,
    )

    # Test 1: WeeklyStatusConfig
    try:
        config = WeeklyStatusConfig(
            project_name="Test Project",
            project_id="proj-123",
            time_range_days=7,
        )
        results.record("WeeklyStatusConfig", config.time_range_days == 7)
    except Exception as e:
        results.record("WeeklyStatusConfig", False, str(e))

    # Test 2: ProjectBriefConfig
    try:
        config = ProjectBriefConfig(
            project_name="Test Project",
            brief_type="overview",
        )
        results.record("ProjectBriefConfig", config.brief_type == "overview")
    except Exception as e:
        results.record("ProjectBriefConfig", False, str(e))

    # Test 3: CrossPlatformDigestConfig
    try:
        config = CrossPlatformDigestConfig(
            time_range_days=14,
            priority_focus="urgent",
        )
        results.record("CrossPlatformDigestConfig", config.priority_focus == "urgent")
    except Exception as e:
        results.record("CrossPlatformDigestConfig", False, str(e))

    # Test 4: ActivitySummaryConfig
    try:
        config = ActivitySummaryConfig(
            time_range_days=3,
            max_items=5,
        )
        results.record("ActivitySummaryConfig", config.max_items == 5)
    except Exception as e:
        results.record("ActivitySummaryConfig", False, str(e))

    # Test 5: Synthesizer types are experimental tier
    try:
        synth_types = ["weekly_status", "project_brief", "cross_platform_digest", "activity_summary"]
        all_experimental = all(TYPE_TIERS.get(t) == "experimental" for t in synth_types)
        results.record("Synthesizer types are experimental", all_experimental)
    except Exception as e:
        results.record("Synthesizer types are experimental", False, str(e))


# =============================================================================
# Main Test Runner
# =============================================================================

async def run_all_tests():
    """Run all ADR-031 tests."""
    print("=" * 60)
    print("ADR-031 Platform-Native Deliverables Test Suite")
    print("=" * 60)

    results = TestResults()

    # Phase 6 Schema
    test_phase6_schema(results)

    # Cross-Platform Synthesizer Service
    test_cross_platform_synthesizer(results)

    # Project Resources API
    await test_project_resources_api(results)

    # Event Triggers
    test_event_triggers(results)

    # Platform Output
    test_platform_output(results)

    # Multi-Destination Delivery
    test_multi_destination_delivery(results)

    # Deliverable Types
    test_deliverable_types(results)

    # Summary
    return results.summary()


def main():
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

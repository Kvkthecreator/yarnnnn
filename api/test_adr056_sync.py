"""
Tests for ADR-056: Per-Source Platform Sync

Run: cd api && python test_adr056_sync.py

Tests validate:
1. selected_sources filtering works for each provider
2. Skips sync when no sources selected
3. _get_selected_sources extracts IDs correctly from landscape
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch


# =============================================================================
# Test: _get_selected_sources extraction
# =============================================================================

def test_get_selected_sources_extracts_ids():
    """Test that _get_selected_sources extracts IDs from landscape objects."""
    from jobs.platform_sync_scheduler import _get_selected_sources

    # Mock supabase client
    mock_client = MagicMock()

    # Test case 1: selected_sources as list of objects with 'id' field
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={
            "landscape": {
                "selected_sources": [
                    {"id": "C123", "name": "#general"},
                    {"id": "C456", "name": "#random"},
                ]
            }
        }
    )

    result = asyncio.run(_get_selected_sources(mock_client, "user123", "slack"))
    assert result == ["C123", "C456"], f"Expected ['C123', 'C456'], got {result}"
    print("✅ _get_selected_sources with objects: PASSED")

    # Test case 2: selected_sources as list of plain strings
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={
            "landscape": {
                "selected_sources": ["label:INBOX", "label:Label_123"]
            }
        }
    )

    result = asyncio.run(_get_selected_sources(mock_client, "user123", "gmail"))
    assert result == ["label:INBOX", "label:Label_123"], f"Expected labels, got {result}"
    print("✅ _get_selected_sources with strings: PASSED")

    # Test case 3: No landscape data
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data=None
    )

    result = asyncio.run(_get_selected_sources(mock_client, "user123", "notion"))
    assert result == [], f"Expected empty list, got {result}"
    print("✅ _get_selected_sources with no data: PASSED")

    # Test case 4: Empty selected_sources
    mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={"landscape": {"selected_sources": []}}
    )

    result = asyncio.run(_get_selected_sources(mock_client, "user123", "calendar"))
    assert result == [], f"Expected empty list, got {result}"
    print("✅ _get_selected_sources with empty list: PASSED")


# =============================================================================
# Test: Slack sync filtering
# =============================================================================

def test_sync_slack_filters_by_selected_sources():
    """Test that _sync_slack only syncs channels in selected_sources."""
    from workers.platform_worker import _sync_slack

    mock_client = MagicMock()

    integration = {
        "settings": {"bot_token": "xoxb-test", "team_id": "T123"},
        "access_token": "xoxb-test",
    }

    # Selected only C123 and C456
    selected_sources = ["C123", "C456"]

    # Mock MCPClientManager - patch at the source module
    with patch("integrations.core.client.MCPClientManager") as MockManager:
        mock_manager = AsyncMock()
        MockManager.return_value = mock_manager

        # Return 4 channels, only 2 are selected
        mock_manager.list_slack_channels.return_value = [
            {"id": "C123", "name": "general"},
            {"id": "C456", "name": "random"},
            {"id": "C789", "name": "not-selected"},
            {"id": "C999", "name": "also-not-selected"},
        ]

        # Return some messages for selected channels
        mock_manager.get_slack_messages.return_value = [
            {"text": "Hello", "user": "U123", "ts": "1234567890.123"},
        ]

        result = asyncio.run(_sync_slack(mock_client, "user123", integration, selected_sources))

        # Should have synced 2 channels (1 message each)
        assert result["channels_synced"] == 2, f"Expected 2 channels synced, got {result}"
        assert result["channels_skipped"] == 2, f"Expected 2 channels skipped, got {result}"
        assert result["items_synced"] == 2, f"Expected 2 items (1 per channel), got {result}"

        # Verify get_slack_messages was only called for selected channels
        assert mock_manager.get_slack_messages.call_count == 2

        print("✅ _sync_slack filters by selected_sources: PASSED")


def test_sync_slack_skips_when_no_sources():
    """Test that _sync_slack skips when no sources selected."""
    from workers.platform_worker import _sync_slack

    mock_client = MagicMock()
    integration = {"settings": {"bot_token": "xoxb-test"}}

    result = asyncio.run(_sync_slack(mock_client, "user123", integration, []))

    assert result["items_synced"] == 0
    assert result.get("skipped") == "no_sources_selected"
    print("✅ _sync_slack skips when empty: PASSED")


# =============================================================================
# Test: Gmail sync with labels
# =============================================================================

def test_sync_gmail_uses_label_ids():
    """Test that _sync_gmail passes label_ids to GoogleAPIClient."""
    from workers.platform_worker import _sync_gmail

    mock_client = MagicMock()
    integration = {
        "settings": {},
        "refresh_token": "refresh-token-123",
    }

    selected_sources = ["label:Label_123", "Label_456"]  # Both formats

    # Patch at source module
    with patch("integrations.core.google_client.GoogleAPIClient") as MockClient:
        with patch.dict("os.environ", {"GOOGLE_CLIENT_ID": "client-id", "GOOGLE_CLIENT_SECRET": "client-secret"}):
            mock_google = AsyncMock()
            MockClient.return_value = mock_google

            # Return message list
            mock_google.list_gmail_messages.return_value = [
                {"id": "msg1"},
            ]

            # Return full message
            mock_google.get_gmail_message.return_value = {
                "id": "msg1",
                "snippet": "Test email content",
                "payload": {
                    "headers": [
                        {"name": "Subject", "value": "Test Subject"},
                        {"name": "From", "value": "test@example.com"},
                        {"name": "Date", "value": "2026-02-12"},
                    ]
                },
                "labelIds": ["Label_123"],
            }

            result = asyncio.run(_sync_gmail(mock_client, "user123", integration, selected_sources))

            # Should have synced 2 labels (1 message each)
            assert result["labels_synced"] == 2, f"Expected 2 labels synced, got {result}"
            assert result["items_synced"] == 2, f"Expected 2 items, got {result}"

            # Verify list_gmail_messages was called with label_ids
            calls = mock_google.list_gmail_messages.call_args_list
            assert len(calls) == 2

            # First call should have label_ids=["Label_123"]
            assert calls[0].kwargs.get("label_ids") == ["Label_123"]
            # Second call should have label_ids=["Label_456"]
            assert calls[1].kwargs.get("label_ids") == ["Label_456"]

            print("✅ _sync_gmail uses label_ids: PASSED")


def test_sync_gmail_skips_when_no_sources():
    """Test that _sync_gmail skips when no sources selected."""
    from workers.platform_worker import _sync_gmail

    mock_client = MagicMock()
    integration = {"settings": {}, "refresh_token": "token"}

    result = asyncio.run(_sync_gmail(mock_client, "user123", integration, []))

    assert result["items_synced"] == 0
    assert result.get("skipped") == "no_sources_selected"
    print("✅ _sync_gmail skips when empty: PASSED")


# =============================================================================
# Test: Notion sync with direct page fetch
# =============================================================================

def test_sync_notion_fetches_pages_directly():
    """Test that _sync_notion fetches pages by ID directly."""
    from workers.platform_worker import _sync_notion

    mock_client = MagicMock()
    integration = {
        "settings": {"notion_token": "secret_token"},
        "access_token": "secret_token",
    }

    selected_sources = ["page-id-123", "page-id-456"]

    # Patch at source module
    with patch("integrations.core.client.MCPClientManager") as MockManager:
        mock_manager = AsyncMock()
        MockManager.return_value = mock_manager

        # Return page content for each page
        mock_manager.get_notion_page_content.side_effect = [
            {"title": "Page 1", "content": "Content 1", "url": "https://notion.so/page1"},
            {"title": "Page 2", "content": "Content 2", "url": "https://notion.so/page2"},
        ]

        result = asyncio.run(_sync_notion(mock_client, "user123", integration, selected_sources))

        assert result["pages_synced"] == 2, f"Expected 2 pages synced, got {result}"
        assert result["items_synced"] == 2, f"Expected 2 items, got {result}"

        # Verify get_notion_page_content was called for each page ID
        assert mock_manager.get_notion_page_content.call_count == 2

        # Verify it was called with specific page IDs
        calls = mock_manager.get_notion_page_content.call_args_list
        assert calls[0].kwargs.get("page_id") == "page-id-123"
        assert calls[1].kwargs.get("page_id") == "page-id-456"

        print("✅ _sync_notion fetches pages directly: PASSED")


def test_sync_notion_skips_when_no_sources():
    """Test that _sync_notion skips when no sources selected."""
    from workers.platform_worker import _sync_notion

    mock_client = MagicMock()
    integration = {"settings": {"notion_token": "token"}}

    result = asyncio.run(_sync_notion(mock_client, "user123", integration, []))

    assert result["items_synced"] == 0
    assert result.get("skipped") == "no_sources_selected"
    print("✅ _sync_notion skips when empty: PASSED")


# =============================================================================
# Test: Calendar sync
# =============================================================================

def test_sync_calendar_fetches_per_calendar():
    """Test that _sync_calendar fetches events per calendar ID."""
    from workers.platform_worker import _sync_calendar

    mock_client = MagicMock()
    integration = {
        "settings": {},
        "refresh_token": "refresh-token-123",
    }

    selected_sources = ["primary", "work@example.com"]

    # Patch at source module
    with patch("integrations.core.google_client.GoogleAPIClient") as MockClient:
        with patch.dict("os.environ", {"GOOGLE_CLIENT_ID": "client-id", "GOOGLE_CLIENT_SECRET": "client-secret"}):
            mock_google = AsyncMock()
            MockClient.return_value = mock_google

            # Return events for each calendar
            mock_google.list_calendar_events.side_effect = [
                [
                    {"id": "event1", "summary": "Meeting 1", "start": {"dateTime": "2026-02-12T10:00:00Z"}},
                    {"id": "event2", "summary": "Meeting 2", "start": {"dateTime": "2026-02-12T14:00:00Z"}},
                ],
                [
                    {"id": "event3", "summary": "Work Event", "start": {"date": "2026-02-13"}},
                ],
            ]

            result = asyncio.run(_sync_calendar(mock_client, "user123", integration, selected_sources))

            assert result["calendars_synced"] == 2, f"Expected 2 calendars synced, got {result}"
            assert result["items_synced"] == 3, f"Expected 3 events, got {result}"

            # Verify list_calendar_events was called for each calendar
            calls = mock_google.list_calendar_events.call_args_list
            assert len(calls) == 2
            assert calls[0].kwargs.get("calendar_id") == "primary"
            assert calls[1].kwargs.get("calendar_id") == "work@example.com"

            print("✅ _sync_calendar fetches per calendar: PASSED")


def test_sync_calendar_skips_when_no_sources():
    """Test that _sync_calendar skips when no sources selected."""
    from workers.platform_worker import _sync_calendar

    mock_client = MagicMock()
    integration = {"settings": {}, "refresh_token": "token"}

    result = asyncio.run(_sync_calendar(mock_client, "user123", integration, []))

    assert result["items_synced"] == 0
    assert result.get("skipped") == "no_sources_selected"
    print("✅ _sync_calendar skips when empty: PASSED")


# =============================================================================
# Test: sync_platform entry point
# =============================================================================

def test_sync_platform_extracts_selected_sources_from_landscape():
    """Test that sync_platform extracts selected_sources when not provided."""
    from workers.platform_worker import _sync_platform_async

    with patch("workers.platform_worker.create_client") as mock_create:
        mock_client = MagicMock()
        mock_create.return_value = mock_client

        # Return integration with landscape
        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={
                "id": "int-123",
                "status": "connected",
                "settings": {"bot_token": "xoxb-test"},
                "landscape": {
                    "selected_sources": [
                        {"id": "C123", "name": "#general"},
                    ]
                },
            }
        )

        with patch("workers.platform_worker._sync_slack") as mock_sync:
            mock_sync.return_value = {"items_synced": 1, "channels_synced": 1}

            result = asyncio.run(_sync_platform_async(
                user_id="user123",
                provider="slack",
                selected_sources=None,  # Not provided - should extract from landscape
                supabase_url="https://test.supabase.co",
                supabase_key="test-key",
            ))

            # Verify _sync_slack was called with extracted selected_sources
            mock_sync.assert_called_once()
            call_args = mock_sync.call_args
            selected = call_args[0][3]  # 4th positional arg is selected_sources
            assert selected == ["C123"], f"Expected ['C123'], got {selected}"

            print("✅ sync_platform extracts selected_sources: PASSED")


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    print("\n🧪 Running ADR-056 Per-Source Sync tests...\n")

    print("\n--- _get_selected_sources tests ---")
    test_get_selected_sources_extracts_ids()

    print("\n--- Slack sync tests ---")
    test_sync_slack_filters_by_selected_sources()
    test_sync_slack_skips_when_no_sources()

    print("\n--- Gmail sync tests ---")
    test_sync_gmail_uses_label_ids()
    test_sync_gmail_skips_when_no_sources()

    print("\n--- Notion sync tests ---")
    test_sync_notion_fetches_pages_directly()
    test_sync_notion_skips_when_no_sources()

    print("\n--- Calendar sync tests ---")
    test_sync_calendar_fetches_per_calendar()
    test_sync_calendar_skips_when_no_sources()

    print("\n--- sync_platform entry point tests ---")
    test_sync_platform_extracts_selected_sources_from_landscape()

    print("\n✅ All ADR-056 tests passed!")

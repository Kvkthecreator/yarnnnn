import asyncio
from unittest.mock import AsyncMock, MagicMock, patch


def _build_query_mock(*, data=None, count=None):
    query = MagicMock()
    query.select.return_value = query
    query.eq.return_value = query
    query.or_.return_value = query
    query.order.return_value = query
    query.range.return_value = query
    query.execute.return_value = MagicMock(data=data or [], count=count)
    return query


def test_sync_slack_records_error_when_channel_history_fails():
    from workers.platform_worker import _sync_slack

    integration = {"settings": {"bot_token": "xoxb-test"}}
    mock_client = MagicMock()

    with patch("integrations.core.slack_client.get_slack_client") as mock_get_slack_client, \
         patch("services.freshness.get_sync_state", new_callable=AsyncMock) as mock_get_sync_state, \
         patch("services.freshness.update_sync_registry", new_callable=AsyncMock) as mock_update_sync_registry:
        mock_slack = AsyncMock()
        mock_get_slack_client.return_value = mock_slack
        mock_get_sync_state.return_value = None

        # Simulate Slack API failure for a selected channel.
        mock_slack.get_channel_history_paginated.return_value = ([], "not_in_channel")
        mock_slack.join_channel.return_value = False

        result = asyncio.run(
            _sync_slack(
                client=mock_client,
                user_id="user-1",
                integration=integration,
                selected_sources=["C123"],
            )
        )

        assert result["items_synced"] == 0
        assert result["channels_synced"] == 0
        assert "error" in result
        assert mock_update_sync_registry.await_count == 1
        assert mock_update_sync_registry.await_args.kwargs["last_error"].startswith("Slack API error:")


def test_get_platform_context_applies_offset_range():
    from routes.integrations import get_platform_context

    row = {
        "id": "pc-1",
        "content": "hello",
        "content_type": "message",
        "resource_id": "C123",
        "resource_name": "#general",
        "source_timestamp": "2026-03-05T00:00:00+00:00",
        "fetched_at": "2026-03-05T00:05:00+00:00",
        "retained": False,
        "retained_reason": None,
        "retained_at": None,
        "expires_at": "2026-03-20T00:05:00+00:00",
        "metadata": {},
    }

    main_query = _build_query_mock(data=[row])
    count_query = _build_query_mock(count=51)
    retained_query = _build_query_mock(count=9)

    client = MagicMock()
    client.table.side_effect = [main_query, count_query, retained_query]
    auth = MagicMock()
    auth.user_id = "user-1"
    auth.client = client

    response = asyncio.run(
        get_platform_context(
            provider="slack",
            limit=20,
            offset=40,
            auth=auth,
        )
    )

    assert main_query.range.call_args[0] == (40, 59)
    assert response.total_count == 51
    assert response.retained_count == 9
    assert len(response.items) == 1

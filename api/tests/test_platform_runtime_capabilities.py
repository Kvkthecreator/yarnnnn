import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.platform_tools import get_platform_tools_for_capabilities
from services.primitives.registry import (
    create_headless_executor,
    get_headless_tools_for_agent,
)


class FakeResult:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, rows):
        self._rows = rows
        self._filters = []

    def select(self, _columns):
        return self

    def eq(self, field, value):
        self._filters.append((field, value))
        return self

    def execute(self):
        rows = list(self._rows)
        for field, value in self._filters:
            rows = [row for row in rows if row.get(field) == value]
        return FakeResult(rows)


class FakeClient:
    def __init__(self, rows):
        self._rows = rows

    def table(self, _name):
        return FakeQuery(self._rows)


class PlatformCapabilityRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_capability_scoped_tools_follow_connected_provider(self):
        client = FakeClient([
            {"user_id": "u1", "platform": "slack", "status": "active"},
            {"user_id": "u1", "platform": "notion", "status": "active"},
            {"user_id": "u1", "platform": "github", "status": "inactive"},
        ])
        auth = SimpleNamespace(client=client, user_id="u1")

        tools = await get_platform_tools_for_capabilities(
            auth,
            ["read_slack", "write_notion", "read_github"],
        )

        self.assertEqual(
            {tool["name"] for tool in tools},
            {
                "platform_slack_list_channels",
                "platform_slack_get_channel_history",
                "platform_notion_create_comment",
            },
        )

    async def test_headless_tool_resolution_uses_agent_capabilities(self):
        client = FakeClient([
            {"user_id": "u1", "platform": "slack", "status": "active"},
            {"user_id": "u1", "platform": "notion", "status": "inactive"},
        ])
        agent = {"id": "a1", "title": "Slack Bot", "role": "slack_bot"}

        tools = await get_headless_tools_for_agent(
            client,
            "u1",
            agent=agent,
            agent_sources=[],
        )

        tool_names = {tool["name"] for tool in tools}
        self.assertIn("platform_slack_list_channels", tool_names)
        self.assertIn("platform_slack_get_channel_history", tool_names)
        self.assertIn("platform_slack_send_message", tool_names)
        self.assertNotIn("platform_notion_search", tool_names)

    async def test_headless_executor_allows_dynamic_platform_tools(self):
        executor = create_headless_executor(
            client=object(),
            user_id="u1",
            dynamic_tools=[{"name": "platform_slack_list_channels"}],
        )

        blocked = await create_headless_executor(
            client=object(),
            user_id="u1",
        )("platform_slack_list_channels", {})
        self.assertEqual(blocked["error"], "not_available")

        with patch(
            "services.primitives.registry.handle_platform_tool",
            new=AsyncMock(return_value={"success": True, "messages": []}),
        ) as platform_mock:
            result = await executor("platform_slack_list_channels", {"channel_id": "C123"})

        self.assertTrue(result["success"])
        platform_mock.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()

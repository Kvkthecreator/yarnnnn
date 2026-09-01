import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.platform_tools import get_platform_tools_for_capabilities


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



# ADR-626 D4.b (2026-09-01): the two HEADLESS tests that lived here
# (`test_headless_tool_resolution_uses_agent_capabilities`,
# `test_headless_executor_allows_dynamic_platform_tools`) are DELETED with
# `create_headless_executor` / `get_headless_tools_for_agent` and the
# `dispatch_specialist` primitive that was their only caller. Role-keyed
# dispatch was superseded by capability-at-the-app (ADR-601/603 D2).
# The capability-scoping test below is UNAFFECTED and stays: it drives
# `get_platform_tools_for_capabilities`, which is live.


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

if __name__ == "__main__":
    unittest.main()

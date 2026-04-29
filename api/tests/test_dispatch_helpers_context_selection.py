import sys
import unittest
from pathlib import Path
import re


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.dispatch_helpers import _gather_context_domains, _match_entities_to_objective


class FakeResult:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, rows, executed_queries):
        self._rows = rows
        self._executed_queries = executed_queries
        self._selected = None
        self._eq_filters = []
        self._like_filters = []
        self._order = None
        self._limit = None

    def select(self, columns):
        self._selected = [column.strip() for column in columns.split(",")]
        return self

    def eq(self, field, value):
        self._eq_filters.append((field, value))
        return self

    def like(self, field, pattern):
        self._like_filters.append((field, pattern))
        return self

    def order(self, field, desc=False):
        self._order = (field, desc)
        return self

    def limit(self, value):
        self._limit = value
        return self

    def execute(self):
        self._executed_queries.append({
            "eq": list(self._eq_filters),
            "like": list(self._like_filters),
        })
        rows = list(self._rows)
        for field, value in self._eq_filters:
            rows = [row for row in rows if row.get(field) == value]
        for field, pattern in self._like_filters:
            regex = "^" + re.escape(pattern).replace("%", ".*") + "$"
            rows = [
                row for row in rows
                if re.match(regex, row.get(field) or "")
            ]
        if self._order:
            field, desc = self._order
            rows = sorted(rows, key=lambda row: row.get(field) or "", reverse=desc)
        if self._limit is not None:
            rows = rows[:self._limit]
        if self._selected:
            rows = [{column: row.get(column) for column in self._selected} for row in rows]
        return FakeResult(rows)


class FakeClient:
    def __init__(self, rows):
        self._rows = rows
        self.executed_queries = []

    def table(self, _name):
        return FakeQuery(self._rows, self.executed_queries)


class MatchEntitiesToObjectiveTests(unittest.TestCase):
    def test_matches_slug_and_name_without_substring_false_positive(self):
        task_info = {
            "title": "Competitive positioning brief",
            "objective": {
                "deliverable": "Compare Acme Corp against Beta Labs",
                "purpose": "Clarify market position",
            },
            "success_criteria": ["Mention pricing differences between Acme Corp and Beta Labs"],
        }

        matched = _match_entities_to_objective(
            ["acme-corp", "beta-labs", "ion"],
            task_info,
        )

        self.assertEqual(matched, ["acme-corp", "beta-labs"])


class GatherContextDomainsTests(unittest.IsolatedAsyncioTestCase):
    async def test_targeted_loading_uses_tracker_and_primary_file_breadth(self):
        rows = [
            {
                "user_id": "u1",
                "path": "/workspace/context/competitors/landscape.md",
                "content": "# Competitive Landscape\n\nAcme is rising.",
                "updated_at": "2026-04-03T09:00:00Z",
            },
            {
                "user_id": "u1",
                "path": "/workspace/context/competitors/_tracker.md",
                "content": (
                    "# Entity Tracker — Competitors\n\n"
                    "| Slug | Last Updated | Files | Status |\n"
                    "|------|-------------|-------|--------|\n"
                    "| acme-corp | 2026-04-02 | profile, product | active |\n"
                    "| beta-labs | 2026-03-30 | profile | active |\n"
                ),
                "updated_at": "2026-04-03T09:01:00Z",
            },
            {
                "user_id": "u1",
                "path": "/workspace/context/competitors/acme-corp/profile.md",
                "content": "# Acme Corp\n\nProfile",
                "updated_at": "2026-04-02T10:00:00Z",
            },
            {
                "user_id": "u1",
                "path": "/workspace/context/competitors/acme-corp/product.md",
                "content": "# Product\n\nDetails",
                "updated_at": "2026-04-01T10:00:00Z",
            },
            {
                "user_id": "u1",
                "path": "/workspace/context/competitors/beta-labs/profile.md",
                "content": "# Beta Labs\n\nProfile",
                "updated_at": "2026-03-30T10:00:00Z",
            },
        ]
        client = FakeClient(rows)

        result = await _gather_context_domains(
            client,
            "u1",
            ["competitors"],
            task_info={
                "title": "Acme competitive review",
                "objective": {"deliverable": "Analyze Acme Corp positioning"},
                "success_criteria": [],
            },
            max_files_per_domain=4,
        )

        self.assertIn("landscape.md (synthesis", result)
        self.assertIn("acme-corp/profile.md (matched", result)
        self.assertIn("acme-corp/product.md (matched", result)
        self.assertIn("beta-labs/profile.md", result)
        self.assertTrue(
            any(
                ("path", "/workspace/context/competitors/_tracker.md") in query["eq"]
                for query in client.executed_queries
            )
        )
        self.assertFalse(
            any(
                ("path", "/workspace/context/competitors/%/%") in query["like"]
                for query in client.executed_queries
            )
        )

    async def test_general_objective_uses_domain_primary_file_not_profile_only(self):
        rows = [
            {
                "user_id": "u1",
                "path": "/workspace/context/market/overview.md",
                "content": "# Market Overview\n\nSummary",
                "updated_at": "2026-04-03T09:00:00Z",
            },
            {
                "user_id": "u1",
                "path": "/workspace/context/market/_tracker.md",
                "content": (
                    "# Entity Tracker — Market\n\n"
                    "| Slug | Last Updated | Files | Status |\n"
                    "|------|-------------|-------|--------|\n"
                    "| enterprise-ai | 2026-04-02 | analysis | active |\n"
                    "| smb-automation | 2026-03-28 | analysis | active |\n"
                ),
                "updated_at": "2026-04-03T09:01:00Z",
            },
            {
                "user_id": "u1",
                "path": "/workspace/context/market/enterprise-ai/analysis.md",
                "content": "# Enterprise AI\n\nAnalysis",
                "updated_at": "2026-04-02T10:00:00Z",
            },
            {
                "user_id": "u1",
                "path": "/workspace/context/market/smb-automation/analysis.md",
                "content": "# SMB Automation\n\nAnalysis",
                "updated_at": "2026-03-28T10:00:00Z",
            },
        ]
        client = FakeClient(rows)

        result = await _gather_context_domains(
            client,
            "u1",
            ["market"],
            task_info={
                "title": "Weekly market brief",
                "objective": {"deliverable": "Summarize the market landscape"},
                "success_criteria": [],
            },
            max_files_per_domain=5,
        )

        self.assertIn("overview.md (synthesis", result)
        self.assertIn("enterprise-ai/analysis.md", result)
        self.assertIn("smb-automation/analysis.md", result)
        self.assertNotIn("/profile.md", result)


if __name__ == "__main__":
    unittest.main()

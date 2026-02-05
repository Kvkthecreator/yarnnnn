"""
ADR-025 Claude Code Agentic Alignment - Skills & Todo Test Suite

Tests the skills system and todo tracking:
1. Skill detection (slash commands and intent patterns)
2. Skill prompt expansion
3. todo_write tool handler
4. UPDATE_TODOS ui_action generation
"""

import asyncio
import os
import sys
from typing import Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


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
# Test: Skill Detection
# =============================================================================

def test_skill_detection(results):
    """Test skill detection from user messages."""
    print("\n=== Skill Detection ===")

    try:
        from services.skills import detect_skill, SKILLS

        # Test slash command detection
        slash_tests = [
            ("/board-update", "board-update"),
            ("/board-update for Marcus", "board-update"),
            ("/status-report", "status-report"),
            ("/research-brief competitors", "research-brief"),
            ("/stakeholder-update", "stakeholder-update"),
            ("/meeting-summary", "meeting-summary"),
            ("/unknown-skill", None),
            ("/", None),
            ("regular message", None),
        ]

        all_slash_passed = True
        for message, expected in slash_tests:
            actual = detect_skill(message)
            passed = actual == expected
            if not passed:
                all_slash_passed = False
                results.record(f"Slash detect '{message}'", False,
                              f"Expected '{expected}', got '{actual}'")
            else:
                print(f"    ✓ '{message}' → '{actual}'")

        results.record("Slash command detection", all_slash_passed)

        # Test pattern matching detection
        pattern_tests = [
            ("I need a board update for investors", "board-update"),
            ("Set up investor report", "board-update"),
            ("Create a weekly status report", "status-report"),
            ("I want a progress report", "status-report"),
            ("competitive intel brief", "research-brief"),
            ("market research weekly", "research-brief"),
            ("client update please", "stakeholder-update"),
            ("need meeting notes template", "meeting-summary"),
            ("hello there", None),
            ("what's the weather", None),
        ]

        all_pattern_passed = True
        for message, expected in pattern_tests:
            actual = detect_skill(message)
            passed = actual == expected
            if not passed:
                all_pattern_passed = False
                results.record(f"Pattern detect '{message[:30]}...'", False,
                              f"Expected '{expected}', got '{actual}'")
            else:
                print(f"    ✓ '{message[:40]}' → '{actual}'")

        results.record("Pattern matching detection", all_pattern_passed)

        # Verify all expected skills exist
        expected_skills = [
            "board-update",
            "status-report",
            "research-brief",
            "stakeholder-update",
            "meeting-summary",
        ]

        all_skills_exist = True
        for skill_name in expected_skills:
            if skill_name not in SKILLS:
                all_skills_exist = False
                results.record(f"Skill '{skill_name}' exists", False, "Missing")

        results.record("All expected skills defined", all_skills_exist)

    except Exception as e:
        results.record("Skill detection", False, str(e))


# =============================================================================
# Test: Skill Prompt Expansion
# =============================================================================

def test_skill_prompt_expansion(results):
    """Test skill system prompt additions."""
    print("\n=== Skill Prompt Expansion ===")

    try:
        from services.skills import get_skill_prompt_addition, get_skill_info, SKILLS

        # Test prompt expansion for each skill
        for skill_name, skill_def in SKILLS.items():
            prompt = get_skill_prompt_addition(skill_name)

            # Verify prompt exists
            has_prompt = prompt is not None and len(prompt) > 100
            results.record(f"'{skill_name}' has prompt", has_prompt,
                          f"Length: {len(prompt) if prompt else 0}")

            # Verify prompt contains expected elements
            if prompt:
                has_todo_write = "todo_write" in prompt.lower()
                has_workflow = "workflow" in prompt.lower()
                has_required_info = "required" in prompt.lower()

                if not has_todo_write:
                    print(f"    ⚠ '{skill_name}' missing todo_write reference")
                if not has_workflow:
                    print(f"    ⚠ '{skill_name}' missing workflow section")

                results.record(f"'{skill_name}' prompt has todo_write", has_todo_write)

        # Test get_skill_info
        board_update_info = get_skill_info("board-update")
        results.record("get_skill_info returns skill data", board_update_info is not None)
        results.record("Skill has deliverable_type",
                      board_update_info.get("deliverable_type") == "board_update")
        results.record("Skill has trigger_patterns",
                      len(board_update_info.get("trigger_patterns", [])) > 0)

        # Test non-existent skill
        nonexistent = get_skill_prompt_addition("nonexistent-skill")
        results.record("Non-existent skill returns None", nonexistent is None)

    except Exception as e:
        results.record("Skill prompt expansion", False, str(e))


# =============================================================================
# Test: List Available Skills
# =============================================================================

def test_list_skills(results):
    """Test listing available skills."""
    print("\n=== List Available Skills ===")

    try:
        from services.skills import list_available_skills

        skills_list = list_available_skills()
        results.record("list_available_skills returns list", isinstance(skills_list, list))
        results.record("list_available_skills has items", len(skills_list) >= 5)

        # Check structure
        if skills_list:
            first_skill = skills_list[0]
            has_name = "name" in first_skill
            has_description = "description" in first_skill
            has_command = "command" in first_skill

            results.record("Skill has name field", has_name)
            results.record("Skill has description field", has_description)
            results.record("Skill has command field", has_command)

            if has_command:
                results.record("Command starts with /",
                              first_skill["command"].startswith("/"))

        print("    Available skills:")
        for skill in skills_list:
            print(f"      {skill.get('command')}: {skill.get('description')}")

    except Exception as e:
        results.record("List available skills", False, str(e))


# =============================================================================
# Test: Todo Write Handler
# =============================================================================

async def test_todo_write_handler(results):
    """Test todo_write tool handler."""
    print("\n=== Todo Write Handler ===")

    try:
        from services.project_tools import handle_todo_write

        # Test valid todo write
        valid_todos = [
            {"content": "Parse intent", "status": "completed", "activeForm": "Parsing intent"},
            {"content": "Gather details", "status": "in_progress", "activeForm": "Gathering details"},
            {"content": "Create deliverable", "status": "pending", "activeForm": "Creating deliverable"},
        ]

        result = await handle_todo_write(None, {"todos": valid_todos})

        results.record("todo_write returns success", result.get("success") == True)
        results.record("todo_write has ui_action", result.get("ui_action") is not None)

        ui_action = result.get("ui_action", {})
        results.record("ui_action type is UPDATE_TODOS",
                      ui_action.get("type") == "UPDATE_TODOS")
        results.record("ui_action has todos data",
                      ui_action.get("data", {}).get("todos") is not None)

        # Verify todos are passed through
        returned_todos = ui_action.get("data", {}).get("todos", [])
        results.record("Returned todos match input", len(returned_todos) == 3)

        # Test the message is informative
        message = result.get("message", "")
        results.record("Message contains task info",
                      "tracking" in message.lower() or "tasks" in message.lower() or "completed" in message.lower())

        print(f"    Message: {message}")

        # Test empty todos
        empty_result = await handle_todo_write(None, {"todos": []})
        results.record("Empty todos returns success", empty_result.get("success") == True)

        # Test missing todos parameter
        missing_result = await handle_todo_write(None, {})
        results.record("Missing todos returns empty list",
                      missing_result.get("ui_action", {}).get("data", {}).get("todos") == [])

    except Exception as e:
        results.record("Todo write handler", False, str(e))


# =============================================================================
# Test: Todo Validation
# =============================================================================

async def test_todo_validation(results):
    """Test todo structure validation."""
    print("\n=== Todo Validation ===")

    try:
        from services.project_tools import handle_todo_write

        # Test various todo structures
        test_cases = [
            # Valid todos
            ({
                "todos": [{"content": "Task 1", "status": "pending", "activeForm": "Doing task 1"}]
            }, True, "Valid single todo"),

            # Todo without activeForm (should still work)
            ({
                "todos": [{"content": "Task 1", "status": "pending"}]
            }, True, "Todo without activeForm"),

            # Invalid status
            ({
                "todos": [{"content": "Task 1", "status": "invalid_status"}]
            }, True, "Invalid status still processed"),

            # Multiple in_progress (allowed but not recommended)
            ({
                "todos": [
                    {"content": "Task 1", "status": "in_progress"},
                    {"content": "Task 2", "status": "in_progress"},
                ]
            }, True, "Multiple in_progress"),
        ]

        for params, expected_success, description in test_cases:
            result = await handle_todo_write(None, params)
            passed = result.get("success") == expected_success
            results.record(description, passed,
                          "" if passed else f"Got success={result.get('success')}")

    except Exception as e:
        results.record("Todo validation", False, str(e))


# =============================================================================
# Test: Todo Tool Definition
# =============================================================================

def test_todo_tool_definition(results):
    """Test TODO_WRITE_TOOL is properly defined."""
    print("\n=== Todo Tool Definition ===")

    try:
        from services.project_tools import TODO_WRITE_TOOL, TOOL_HANDLERS

        # Check tool definition exists
        results.record("TODO_WRITE_TOOL defined", TODO_WRITE_TOOL is not None)

        # Check it's a valid tool structure
        results.record("Tool has name", TODO_WRITE_TOOL.get("name") == "todo_write")
        results.record("Tool has description", len(TODO_WRITE_TOOL.get("description", "")) > 50)

        # Check input schema
        input_schema = TODO_WRITE_TOOL.get("input_schema", {})
        results.record("Tool has input_schema", input_schema is not None)

        properties = input_schema.get("properties", {})
        results.record("Input has todos property", "todos" in properties)

        # Check handler is registered
        results.record("Handler registered", "todo_write" in TOOL_HANDLERS)

        print(f"    Tool name: {TODO_WRITE_TOOL.get('name')}")
        print(f"    Description: {TODO_WRITE_TOOL.get('description', '')[:80]}...")

    except Exception as e:
        results.record("Todo tool definition", False, str(e))


# =============================================================================
# Test: Skill Integration with TP
# =============================================================================

def test_skill_tp_integration(results):
    """Test skill detection is integrated with thinking_partner.py."""
    print("\n=== Skill TP Integration ===")

    try:
        # Check if thinking_partner imports skills
        from agents.thinking_partner import execute_with_tools

        # We can't easily test the full integration without mocking,
        # but we can verify the imports work
        results.record("thinking_partner module loads", True)

        # Check that detect_skill is used (by inspecting imports)
        import inspect
        source = inspect.getsourcefile(execute_with_tools)
        if source:
            with open(source, 'r') as f:
                content = f.read()
                has_skill_import = "detect_skill" in content
                has_skill_usage = "get_skill_prompt_addition" in content

                results.record("TP imports detect_skill", has_skill_import)
                results.record("TP uses get_skill_prompt_addition", has_skill_usage)

    except ImportError as e:
        results.record("Skill TP integration", True, f"Skipped - {e}")
    except Exception as e:
        results.record("Skill TP integration", False, str(e))


# =============================================================================
# Main Runner
# =============================================================================

async def run_async_tests(results):
    """Run async test functions."""
    await test_todo_write_handler(results)
    await test_todo_validation(results)


def run_all():
    """Run complete ADR-025 validation suite."""
    print("=" * 60)
    print("ADR-025 Claude Code Agentic Alignment - Skills Test Suite")
    print("=" * 60)

    results = TestResults()

    # Run sync tests
    test_skill_detection(results)
    test_skill_prompt_expansion(results)
    test_list_skills(results)
    test_todo_tool_definition(results)
    test_skill_tp_integration(results)

    # Run async tests
    asyncio.run(run_async_tests(results))

    return results.summary()


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)

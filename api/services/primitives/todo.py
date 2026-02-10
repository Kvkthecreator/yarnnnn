"""
Todo Primitive

Track intent/progress for multi-step work.

Usage:
  Todo(items=[{content: "...", status: "pending", activeForm: "..."}])
"""

from typing import Any


TODO_TOOL = {
    "name": "Todo",
    "description": """Track progress for multi-step work.

Use when:
- Setting up a new deliverable (multiple steps)
- Executing a complex request
- Any work requiring 3+ steps

States:
- pending: Not yet started
- in_progress: Currently working (only ONE at a time)
- completed: Finished

Examples:
- Todo(items=[{content: "Create deliverable", status: "in_progress", activeForm: "Creating deliverable"}])
- Todo(items=[...existing..., {content: "Done", status: "completed"}])

Always include both content (imperative: "Create X") and activeForm (present continuous: "Creating X").""",
    "input_schema": {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "Task in imperative form (e.g., 'Create deliverable')"
                        },
                        "status": {
                            "type": "string",
                            "enum": ["pending", "in_progress", "completed"]
                        },
                        "activeForm": {
                            "type": "string",
                            "description": "Task in present continuous (e.g., 'Creating deliverable')"
                        }
                    },
                    "required": ["content", "status"]
                }
            }
        },
        "required": ["items"]
    }
}


async def handle_todo(auth: Any, input: dict) -> dict:
    """
    Handle Todo primitive.

    Args:
        auth: Auth context (not used for todos, they're session-scoped)
        input: {"items": [...]}

    Returns:
        {"success": True, "todos": [...], "message": "..."}
    """
    items = input.get("items", [])

    if not items:
        return {
            "success": True,
            "todos": [],
            "message": "Todo list cleared",
            "ui_action": {
                "type": "UPDATE_TODOS",
                "data": {"todos": []},
            },
        }

    # Validate items
    validated = []
    in_progress_count = 0

    for item in items:
        content = item.get("content", "").strip()
        status = item.get("status", "pending")
        active_form = item.get("activeForm", content)

        if not content:
            continue

        if status not in ("pending", "in_progress", "completed"):
            status = "pending"

        if status == "in_progress":
            in_progress_count += 1

        validated.append({
            "content": content,
            "status": status,
            "activeForm": active_form,
        })

    # Generate summary
    total = len(validated)
    completed = sum(1 for t in validated if t["status"] == "completed")
    pending = sum(1 for t in validated if t["status"] == "pending")

    if completed == total and total > 0:
        message = f"All {total} tasks completed"
    elif in_progress_count > 0:
        current = next((t for t in validated if t["status"] == "in_progress"), None)
        message = current["activeForm"] if current else f"Working on {in_progress_count} task(s)"
    else:
        message = f"{pending} task(s) pending"

    return {
        "success": True,
        "todos": validated,
        "count": total,
        "completed": completed,
        "pending": pending,
        "in_progress": in_progress_count,
        "message": message,
        "ui_action": {
            "type": "UPDATE_TODOS",
            "data": {"todos": validated},
        },
    }

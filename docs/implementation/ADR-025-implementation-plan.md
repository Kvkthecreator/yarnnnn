# ADR-025 Implementation Plan: Claude Code Agentic Alignment

**Created:** 2026-02-05
**Status:** Ready for Implementation
**Related ADR:** [ADR-025-claude-code-agentic-alignment.md](../adr/ADR-025-claude-code-agentic-alignment.md)

---

## Overview

This plan implements the Claude Code agentic alignment in two phases:
1. **Validation Phase** — `todo_write` tool + single skill (`/board-update`)
2. **Full Rollout** — All skills, full frontend integration

**Approach:** Singular implementation, no dual approaches. Delete legacy code when replaced.

---

## Phase 1: Validation (Backend First)

### 1.1 Add `todo_write` Tool

**File:** `api/services/project_tools.py`

**Add tool definition after line 421 (after `SUGGEST_PROJECT_FOR_MEMORY_TOOL`):**

```python
# =============================================================================
# Todo Tracking Tool (ADR-025 Claude Code Alignment)
# =============================================================================

TODO_WRITE_TOOL = {
    "name": "todo_write",
    "description": """Track and update task progress for multi-step work.

ADR-025: Claude Code Agentic Alignment - Use this for visibility and accountability.

Use this when:
- Setting up a new deliverable (multiple steps involved)
- Executing a complex user request
- Any work requiring 3+ steps

Task states:
- pending: Not yet started
- in_progress: Currently working on (only ONE at a time)
- completed: Finished successfully

Always:
- Create todos at the start of multi-step work
- Update status as you progress
- Mark complete immediately when done (don't batch)
- Include both content (imperative: "Gather details") and activeForm (present continuous: "Gathering details")
""",
    "input_schema": {
        "type": "object",
        "properties": {
            "todos": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "Task description in imperative form (e.g., 'Gather details')"
                        },
                        "status": {
                            "type": "string",
                            "enum": ["pending", "in_progress", "completed"]
                        },
                        "activeForm": {
                            "type": "string",
                            "description": "Task description in present continuous (e.g., 'Gathering details')"
                        }
                    },
                    "required": ["content", "status"]
                }
            }
        },
        "required": ["todos"]
    }
}
```

**Add handler after line ~750 (in handlers section):**

```python
async def handle_todo_write(auth, input: dict) -> dict:
    """
    Handle todo tracking for multi-step work.

    ADR-025: Todos are ephemeral (session-scoped), not persisted.
    The frontend displays them via ui_action and clears on session end.
    """
    todos = input.get("todos", [])

    # Return todos in ui_action for frontend to display
    return {
        "success": True,
        "todos": todos,
        "ui_action": {
            "type": "UPDATE_TODOS",
            "data": {
                "todos": todos
            }
        }
    }
```

**Update `THINKING_PARTNER_TOOLS` list (around line 653):**

Add `TODO_WRITE_TOOL` to the list:

```python
THINKING_PARTNER_TOOLS = [
    # Communication (conversation as explicit tool choice)
    RESPOND_TOOL,
    CLARIFY_TOOL,
    # Progress tracking (ADR-025)
    TODO_WRITE_TOOL,
    # Navigation (open surfaces to show data)
    LIST_PROJECTS_TOOL,
    # ... rest unchanged
]
```

**Update `execute_tool` function (around line 900+):**

Add handler mapping:

```python
TOOL_HANDLERS = {
    # ... existing handlers
    "todo_write": handle_todo_write,
}
```

---

### 1.2 Update TP System Prompt

**File:** `api/agents/thinking_partner.py`

**Add new section to `SYSTEM_PROMPT_WITH_TOOLS` after the "Domain Vocabulary" section (~line 145):**

```python
---

## Task Progress Tracking (ADR-025)

For multi-step work (deliverable setup, complex requests), use `todo_write` to:
1. **Plan** — Create todos at the start showing your intended steps
2. **Update** — Mark tasks in_progress as you work on them, completed when done
3. **Revise** — If assumptions are wrong, update the todo list

**Pattern:**
```
User: "Set up a monthly board update"
→ todo_write([
    {content: "Parse intent", status: "completed", activeForm: "Parsing intent"},
    {content: "Gather required details", status: "in_progress", activeForm: "Gathering required details"},
    {content: "Confirm deliverable setup", status: "pending", activeForm: "Confirming deliverable setup"},
    {content: "Create deliverable", status: "pending", activeForm: "Creating deliverable"},
    {content: "Offer first draft", status: "pending", activeForm: "Offering first draft"}
  ])
```

**When to use:**
- ✅ Creating a deliverable (4-6 steps)
- ✅ Complex user request with multiple actions
- ✅ Any work requiring 3+ steps
- ❌ Simple navigation ("show my memories")
- ❌ Single-turn conversation
- ❌ Quick actions (pause deliverable, create memory)

**Rules:**
- Only ONE task can be `in_progress` at a time
- Mark complete IMMEDIATELY when done (don't batch)
- If you discover something unexpected, update the todo list
```

---

### 1.3 Implement Skills System

**New file:** `api/services/skills.py`

```python
"""
Skills System (ADR-025 Claude Code Alignment)

Skills are packaged workflows triggered by slash commands or intent recognition.
Each skill expands to a system prompt addition that guides TP through a structured process.
"""

from typing import Optional, Dict, Any

# =============================================================================
# Skill Definitions
# =============================================================================

SKILLS: Dict[str, Dict[str, Any]] = {
    "board-update": {
        "name": "board-update",
        "description": "Create a recurring board update deliverable",
        "trigger_patterns": ["board update", "investor update", "board report", "investor report"],
        "deliverable_type": "board_update",
        "system_prompt_addition": """
## Active Skill: Board Update Creation

You are helping the user create a recurring board update deliverable.

**Expected workflow (use todo_write to track):**
1. Parse intent (board update, extract frequency if mentioned)
2. Gather required details (company name, stage, recipient, frequency)
3. Confirm deliverable setup with user
4. Create deliverable with create_deliverable
5. Offer to generate first draft

**Required information:**
- Recipient name (e.g., "Marcus Webb", "the board")
- Company/project name
- Frequency (default: monthly on 1st)
- Company stage (seed, Series A, etc.) — helpful for tone

**Use clarify() for missing required info. Don't guess.**

**After creation, the deliverable will include these sections:**
- Executive Summary
- Key Metrics & KPIs
- Progress & Milestones
- Challenges & Risks
- Asks & Support Needed
- Outlook & Next Period
""",
    },

    "status-report": {
        "name": "status-report",
        "description": "Create a recurring status report deliverable",
        "trigger_patterns": ["status report", "weekly report", "progress report", "status update"],
        "deliverable_type": "status_report",
        "system_prompt_addition": """
## Active Skill: Status Report Creation

You are helping the user create a recurring status report deliverable.

**Expected workflow (use todo_write to track):**
1. Parse intent (status report, extract frequency/recipient if mentioned)
2. Gather required details (recipient, frequency, what to cover)
3. Confirm deliverable setup with user
4. Create deliverable with create_deliverable
5. Offer to generate first draft

**Required information:**
- Recipient name (e.g., "Sarah", "my manager", "the team")
- Frequency (default: weekly on Monday)
- Focus areas (optional: what should be covered)

**Use clarify() for missing required info. Don't guess.**
""",
    },

    "research-brief": {
        "name": "research-brief",
        "description": "Create a recurring research brief deliverable",
        "trigger_patterns": ["research brief", "competitive intel", "market research", "competitor analysis"],
        "deliverable_type": "research_brief",
        "system_prompt_addition": """
## Active Skill: Research Brief Creation

You are helping the user create a recurring research brief deliverable.

**Expected workflow (use todo_write to track):**
1. Parse intent (research topic, extract frequency if mentioned)
2. Gather required details (topic focus, competitors/areas, frequency)
3. Confirm deliverable setup with user
4. Create deliverable with create_deliverable
5. Offer to generate first draft

**Required information:**
- Research focus (competitors, market trends, technology, etc.)
- Frequency (default: weekly)
- Data sources or areas to monitor (optional)

**Use clarify() for missing required info. Don't guess.**
""",
    },
}

# =============================================================================
# Skill Detection & Expansion
# =============================================================================

def detect_skill(user_message: str) -> Optional[str]:
    """
    Detect if user message triggers a skill.

    Returns skill name if detected, None otherwise.

    Detection methods:
    1. Explicit slash command: /board-update
    2. Pattern matching: "board update", "investor update"
    """
    message_lower = user_message.lower().strip()

    # Check for explicit slash command
    if message_lower.startswith("/"):
        command = message_lower[1:].split()[0]  # Get first word after /
        if command in SKILLS:
            return command

    # Check trigger patterns
    for skill_name, skill_def in SKILLS.items():
        for pattern in skill_def.get("trigger_patterns", []):
            if pattern in message_lower:
                return skill_name

    return None


def get_skill_prompt_addition(skill_name: str) -> Optional[str]:
    """Get the system prompt addition for a skill."""
    skill = SKILLS.get(skill_name)
    if skill:
        return skill.get("system_prompt_addition", "")
    return None


def get_skill_info(skill_name: str) -> Optional[Dict[str, Any]]:
    """Get full skill definition."""
    return SKILLS.get(skill_name)
```

---

### 1.4 Integrate Skills into TP

**File:** `api/agents/thinking_partner.py`

**Add import at top:**

```python
from services.skills import detect_skill, get_skill_prompt_addition
```

**Update `execute_with_tools` method to detect and inject skill:**

In the `execute_with_tools` method (around line 470), add skill detection before building system prompt:

```python
async def execute_with_tools(
    self,
    user_message: str,
    messages: list[dict] | None = None,
    context: ContextBundle | None = None,
    auth = None,
    include_context: bool = True,
    is_onboarding: bool = False,
    surface_context: Optional[dict] = None,
    selected_project_id: Optional[str] = None,
    selected_project_name: Optional[str] = None,
) -> AsyncGenerator[dict, None]:
    """Execute with tools, streaming response."""

    # ADR-025: Detect skill from user message
    active_skill = detect_skill(user_message)
    skill_prompt = get_skill_prompt_addition(active_skill) if active_skill else None

    # Build system prompt
    system_prompt = self._build_system_prompt(
        context or ContextBundle([], [], []),
        include_context,
        with_tools=True,
        is_onboarding=is_onboarding,
        surface_content=surface_context.get("content") if surface_context else None,
        selected_project_name=selected_project_name,
        skill_prompt=skill_prompt,  # NEW: Pass skill prompt
    )

    # ... rest of method unchanged
```

**Update `_build_system_prompt` to accept skill_prompt:**

Add parameter and inject skill prompt:

```python
def _build_system_prompt(
    self,
    context: ContextBundle,
    include_context: bool,
    with_tools: bool = False,
    is_onboarding: bool = False,
    surface_content: Optional[str] = None,
    selected_project_name: Optional[str] = None,
    skill_prompt: Optional[str] = None,  # NEW
) -> str:
    # ... existing code ...

    # ADR-025: Inject skill prompt if active
    if skill_prompt:
        # Insert skill prompt before the context section
        prompt = prompt.replace("{context}", f"{skill_prompt}\n\n{{context}}")

    # ... rest of method unchanged
```

---

## Phase 1: Validation (Frontend)

### 1.5 Extend TPContext with Todos State

**File:** `web/contexts/TPContext.tsx`

**Update TPState interface (around line 10):**

```typescript
// In types/desk.ts, add:
export interface Todo {
  id?: string;
  content: string;
  status: 'pending' | 'in_progress' | 'completed';
  activeForm?: string;
}

// In TPContext.tsx, update initialState:
const initialState: TPState = {
  messages: [],
  isLoading: false,
  error: null,
  todos: [],           // NEW: Current todo list
  activeSkill: null,   // NEW: Active skill name
};
```

**Add new state and actions:**

```typescript
// Add to TPContextValue interface:
todos: Todo[];
activeSkill: string | null;
setWorkPanelExpanded: (expanded: boolean) => void;
workPanelExpanded: boolean;

// Add to reducer:
case 'SET_TODOS':
  return { ...state, todos: action.todos };

case 'SET_ACTIVE_SKILL':
  return { ...state, activeSkill: action.skill };

case 'CLEAR_WORK_STATE':
  return { ...state, todos: [], activeSkill: null };
```

**Handle `UPDATE_TODOS` ui_action in SSE parsing (around line 237):**

```typescript
} else if (action.type === 'UPDATE_TODOS') {
  // ADR-025: Todo tracking
  const todos = action.data?.todos as Todo[] || [];
  dispatch({ type: 'SET_TODOS', todos });
  // Auto-expand work panel when todos appear
  if (todos.length > 0) {
    setWorkPanelExpanded(true);
  }
}
```

---

### 1.6 Create TPWorkPanel Component

**New file:** `web/components/tp/TPWorkPanel.tsx`

```typescript
'use client';

/**
 * ADR-025: Claude Code Agentic Alignment
 * TPWorkPanel - Displays todo progress + chat during multi-step work
 */

import { useState } from 'react';
import { X, CheckCircle2, Circle, Loader2 } from 'lucide-react';
import { useTP, Todo, TPMessage } from '@/contexts/TPContext';
import { cn } from '@/lib/utils';

interface TPWorkPanelProps {
  onCollapse: () => void;
}

export function TPWorkPanel({ onCollapse }: TPWorkPanelProps) {
  const { todos, messages, activeSkill, sendMessage, isLoading, status } = useTP();
  const [input, setInput] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    sendMessage(input);
    setInput('');
  };

  // Get recent messages (last 10)
  const recentMessages = messages.slice(-10);

  return (
    <div className="flex flex-col h-full bg-background border-l border-border">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">
            {activeSkill ? `Creating: ${activeSkill.replace('-', ' ')}` : 'Working...'}
          </span>
        </div>
        <button
          onClick={onCollapse}
          className="p-1 hover:bg-muted rounded"
          aria-label="Collapse panel"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Todos */}
      {todos.length > 0 && (
        <div className="px-4 py-3 border-b border-border">
          <div className="text-xs font-medium text-muted-foreground mb-2">Progress</div>
          <div className="space-y-1.5">
            {todos.map((todo, i) => (
              <TodoItem key={i} todo={todo} />
            ))}
          </div>
        </div>
      )}

      {/* Chat messages */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
        {recentMessages.map((msg) => (
          <div
            key={msg.id}
            className={cn(
              'text-sm',
              msg.role === 'user' ? 'text-muted-foreground' : 'text-foreground'
            )}
          >
            <span className="font-medium text-xs">
              {msg.role === 'user' ? 'You' : 'TP'}:
            </span>
            <p className="mt-0.5">{msg.content}</p>
          </div>
        ))}

        {/* Status indicator */}
        {status.type === 'thinking' && (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Loader2 className="w-3 h-3 animate-spin" />
            <span className="text-xs">Thinking...</span>
          </div>
        )}
        {status.type === 'tool' && (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Loader2 className="w-3 h-3 animate-spin" />
            <span className="text-xs">{status.toolName}...</span>
          </div>
        )}
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-3 border-t border-border">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={isLoading}
          placeholder="Type a response..."
          className="w-full px-3 py-2 text-sm border border-border rounded-lg bg-background focus:outline-none focus:ring-1 focus:ring-primary"
        />
      </form>
    </div>
  );
}

function TodoItem({ todo }: { todo: Todo }) {
  return (
    <div className="flex items-center gap-2">
      {todo.status === 'completed' ? (
        <CheckCircle2 className="w-4 h-4 text-green-600 shrink-0" />
      ) : todo.status === 'in_progress' ? (
        <Loader2 className="w-4 h-4 text-primary animate-spin shrink-0" />
      ) : (
        <Circle className="w-4 h-4 text-muted-foreground shrink-0" />
      )}
      <span
        className={cn(
          'text-sm',
          todo.status === 'completed' && 'text-muted-foreground line-through',
          todo.status === 'in_progress' && 'text-foreground font-medium'
        )}
      >
        {todo.status === 'in_progress' ? todo.activeForm || todo.content : todo.content}
      </span>
    </div>
  );
}
```

---

### 1.7 Integrate TPWorkPanel into Surfaces

**File:** `web/components/surfaces/DeliverableDetailSurface.tsx`

Add conditional rendering of TPWorkPanel:

```typescript
import { TPWorkPanel } from '@/components/tp/TPWorkPanel';
import { useTP } from '@/contexts/TPContext';

// In component:
const { todos, workPanelExpanded, setWorkPanelExpanded } = useTP();

// In render, wrap content in a flex container:
return (
  <div className="flex h-full">
    {/* Main content */}
    <div className={cn(
      "flex-1 overflow-y-auto",
      workPanelExpanded && "max-w-[60%]"
    )}>
      {/* ... existing surface content ... */}
    </div>

    {/* Work panel (shown when todos exist or explicitly expanded) */}
    {(workPanelExpanded || todos.length > 0) && (
      <div className="w-[40%] min-w-[320px]">
        <TPWorkPanel onCollapse={() => setWorkPanelExpanded(false)} />
      </div>
    )}
  </div>
);
```

**Similar integration for `IdleSurface.tsx`:**

The work panel can overlay as a card on the idle surface when active.

---

## Phase 1: Testing Checklist

Before proceeding to Phase 2:

- [ ] `todo_write` tool defined and handler works
- [ ] TP uses `todo_write` for deliverable creation (prompted by system prompt)
- [ ] Frontend displays todos via `UPDATE_TODOS` ui_action
- [ ] TPWorkPanel renders correctly
- [ ] `/board-update` skill detected and injects prompt
- [ ] End-to-end: user types "/board-update" → TP tracks progress with todos → deliverable created
- [ ] "Receipt" is visible: user can see todo history after completion

---

## Phase 2: Full Rollout (After Validation)

### 2.1 Port All Deliverable Types as Skills

Add to `api/services/skills.py`:

- `/stakeholder-update`
- `/meeting-summary`
- `/newsletter-section`
- `/changelog`
- `/one-on-one-prep`
- `/client-proposal`
- `/performance-review`

### 2.2 Skill Picker UI (Optional)

Add autocomplete/picker in TPBar for skill discovery.

### 2.3 Mobile Adaptations

Slide-up panel behavior for TPWorkPanel on mobile.

### 2.4 Receipt/History View (Optional)

If persistent receipts are desired, implement `skill_executions` table:

```sql
CREATE TABLE skill_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    skill_name TEXT NOT NULL,
    session_id UUID,
    todos JSONB,
    tool_calls JSONB,
    deliverable_id UUID REFERENCES deliverables(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);
```

---

## File Summary

### Backend (api/)

| File | Action | Description |
|------|--------|-------------|
| `services/project_tools.py` | MODIFY | Add `TODO_WRITE_TOOL`, handler, register in tools list |
| `services/skills.py` | CREATE | New file with skill definitions and detection |
| `agents/thinking_partner.py` | MODIFY | Add skill detection, inject skill prompt, update system prompt |

### Frontend (web/)

| File | Action | Description |
|------|--------|-------------|
| `types/desk.ts` | MODIFY | Add `Todo` interface |
| `contexts/TPContext.tsx` | MODIFY | Add `todos`, `activeSkill`, `workPanelExpanded` state + handlers |
| `components/tp/TPWorkPanel.tsx` | CREATE | New component for todo + chat panel |
| `components/surfaces/DeliverableDetailSurface.tsx` | MODIFY | Integrate TPWorkPanel |
| `components/surfaces/IdleSurface.tsx` | MODIFY | Integrate TPWorkPanel (overlay) |

---

## Commit Strategy

1. **Commit 1:** Backend - Add `todo_write` tool and handler
2. **Commit 2:** Backend - Add skills system with `/board-update`
3. **Commit 3:** Backend - Integrate skills into TP, update system prompt
4. **Commit 4:** Frontend - Extend TPContext with todos state
5. **Commit 5:** Frontend - Create TPWorkPanel component
6. **Commit 6:** Frontend - Integrate panel into surfaces
7. **Commit 7:** End-to-end testing, fixes

---

## Database Changes

**Phase 1:** None required. Todos are session-scoped (ephemeral).

**Phase 2 (optional):** `skill_executions` table for audit trail.

---

## Rollback Plan

If validation fails:

1. Revert skill system (remove `skills.py`, revert TP changes)
2. Keep `todo_write` tool (useful even without skills)
3. Frontend changes are additive; TPWorkPanel can be hidden

---

*This plan prioritizes singular implementation. Legacy patterns are replaced, not preserved alongside new code.*

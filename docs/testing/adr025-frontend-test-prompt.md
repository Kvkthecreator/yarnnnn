# ADR-025 Frontend Testing Prompt (Claude Browser Session)

Use this prompt in a Claude browser session to systematically test the ADR-025 "Claude Code Agentic Alignment" features in the YARNNN frontend.

---

## Pre-Testing Setup

1. **Open the YARNNN app** in your browser (usually `http://localhost:3000`)
2. **Open browser DevTools** (F12 or Cmd+Option+I)
3. **Go to the Console tab** - you'll be monitoring for `[TP]` logs
4. **Log in** if not already authenticated

---

## Test Prompt for Claude Browser

Copy and paste the following into a Claude browser chat session:

---

### START OF TESTING PROMPT

I need you to help me test the ADR-025 "Claude Code Agentic Alignment" implementation in YARNNN. This feature adds:

1. **Skills system** - Slash commands like `/board-update` that trigger packaged workflows
2. **Todo tracking** - Real-time progress display via `TPWorkPanel`
3. **UPDATE_TODOS ui_action** - SSE streaming of todo state to frontend

## Test Scenarios

### Test 1: Skill Detection via Slash Command

**Action:** In the YARNNN chat input, type:
```
/board-update for Marcus Webb monthly
```

**Expected Results:**
1. Console should show: `[TP] tool_use: todo_write`
2. A collapsible work panel should appear on the right side
3. Panel should show todos with statuses:
   - "Parse intent" - completed (green checkmark)
   - "Gather required details" - in_progress (spinning)
   - "Confirm deliverable setup" - pending (empty circle)
   - "Create deliverable" - pending
   - "Offer first draft" - pending

**Monitor Console For:**
```
[TP] UPDATE_TODOS: X items
[TP] tool_result raw: {"success":true,...}
```

**Report:** Did the work panel appear? Did you see todos with correct statuses?

---

### Test 2: Skill Detection via Intent Pattern

**Action:** In the YARNNN chat input, type:
```
I need to set up a weekly status report for my manager Sarah
```

**Expected Results:**
1. TP should recognize "status report" pattern and activate skill
2. Work panel should appear with skill-specific todos
3. TP should ask clarifying questions (frequency, focus areas, etc.)

**Report:** Did skill detection work without using a slash command?

---

### Test 3: Todo Progress Updates

**Action:** Continue the conversation from Test 1 or 2, providing requested info:
```
Yes, that looks right. Please create the deliverable.
```

**Expected Results:**
1. Watch the work panel - todos should update in real-time
2. "Gather required details" should change from in_progress to completed
3. "Confirm deliverable setup" should become in_progress, then completed
4. "Create deliverable" should become in_progress

**Console should show multiple:**
```
[TP] UPDATE_TODOS: X items
```

**Report:** Did you see todos updating as TP progressed through the workflow?

---

### Test 4: Work Panel Collapse/Expand

**Action:**
1. Click the X button on the work panel header
2. Start a new skill workflow (e.g., `/research-brief competitors`)

**Expected Results:**
1. Panel should collapse when X is clicked
2. Panel should auto-expand when new todos appear
3. `workPanelExpanded` state managed by TPContext

**Report:** Did collapse/expand work correctly?

---

### Test 5: TPWorkPanel Chat Integration

**Action:** While the work panel is visible:
1. Type a message in the work panel's chat input
2. Send it

**Expected Results:**
1. Message should appear in the panel's message list
2. TP should respond
3. Status indicator should show "Thinking..." then "Typing..."

**Report:** Does the work panel chat work independently from the main chat?

---

### Test 6: Multiple Surfaces with Work Panel

**Action:**
1. Navigate to a deliverable detail page
2. Start a skill workflow from there
3. Navigate to the dashboard/idle surface
4. Check if work panel persists

**Expected Results:**
1. Work panel should appear in DeliverableDetailSurface
2. Work panel should appear in IdleSurface
3. Todos should persist across surface navigation (same TPContext)

**Report:** Does the work panel work on different surfaces?

---

### Test 7: Error State Handling

**Action:** Test an error scenario:
1. Disconnect network or backend
2. Try to send a message

**Expected Results:**
1. Error should appear in chat
2. Work panel should handle gracefully (not crash)
3. Status should reset to idle

**Report:** How did error states display?

---

## Console Log Reference

Key logs to watch for:
- `[TP] tool_use: todo_write` - TP is updating todos
- `[TP] tool_result raw: {...}` - Raw tool result
- `[TP] UPDATE_TODOS: X items` - Frontend received todo update
- `[TP] OPEN_SURFACE: ...` - Navigation happening
- `[TP] RESPOND: ...` - TP sending a response

---

## Reporting Template

After each test, please report:

```
Test X: [Test Name]
- Pass/Fail: [PASS/FAIL]
- Work Panel Appeared: [Yes/No]
- Todos Visible: [Yes/No/Count]
- Console Logs: [Key observations]
- Issues: [Any bugs or unexpected behavior]
```

---

### END OF TESTING PROMPT

---

## Additional Notes for Tester

### Files Involved in ADR-025 Frontend

- `web/contexts/TPContext.tsx` - State management for todos, workPanelExpanded
- `web/components/tp/TPWorkPanel.tsx` - The work panel component
- `web/components/surfaces/IdleSurface.tsx` - Dashboard surface with panel integration
- `web/components/surfaces/DeliverableDetailSurface.tsx` - Detail surface with panel
- `web/types/desk.ts` - Todo interface, UPDATE_TODOS action type

### Backend Files

- `api/services/skills.py` - Skill definitions and detection
- `api/services/project_tools.py` - todo_write handler
- `api/agents/thinking_partner.py` - Skill integration with TP

### Known Behaviors

1. **Todos are ephemeral** - They don't persist to database, cleared on session end
2. **Panel auto-expands** - When `todos.length > 0`, panel expands automatically
3. **Skill prompts include todo_write examples** - Each skill has todo tracking built in
4. **Only one in_progress** - By convention, only one todo should be in_progress at a time

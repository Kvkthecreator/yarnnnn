# Claude Code Architecture Analysis

**Date:** 2026-04-01
**Source:** Decompiled CC CLI source (~30MB TypeScript), stored locally at `docs/analysis/src_claudeCC/` (gitignored)
**Purpose:** Reference for YARNNN architectural decisions — what to learn, what to ignore, why

---

## What Claude Code Is

CC is a **developer tool CLI** — a human sits at a terminal, works on a codebase, one session at a time. The entire architecture serves interactive, human-in-the-loop coding assistance. YARNNN is an **autonomous agent platform for recurring knowledge work** — agents run unattended on schedule. These are fundamentally different products sharing some structural patterns.

---

## Architecture Overview

### Six Core Systems

| System | Purpose | Key Files |
|--------|---------|-----------|
| **Tools** (45+) | Capabilities the model can invoke | `tools/`, `Tool.ts`, `tools.ts` |
| **Skills** | Prompt-based extensible commands | `skills/`, `commands.ts` |
| **Hooks** (25 events) | Event-driven shell/prompt/agent/HTTP callbacks | `hooks/` |
| **Tasks** (7 types) | Background process tracking | `tasks/`, `Task.ts` |
| **Memory** (4 types) | Cross-session file-based knowledge | `memdir/` |
| **Query Engine** | Conversation loop state machine | `query.ts`, `query/`, `QueryEngine.ts` |

---

## 1. Skills System

### How It Works
Skills are prompt-based commands loaded from multiple sources in precedence order:
1. **Managed** — admin policy (`getManagedFilePath()/.claude/skills/`)
2. **User** — personal (`~/.claude/skills/`)
3. **Project** — repo-specific (`./.claude/skills/`)
4. **Bundled** — compiled into CLI (12+ built-in skills)
5. **Plugin/MCP** — external extensions

### SKILL.md Convention
```markdown
---
name: skill-display-name
description: One-line description
when_to_use: "Use when..."
allowed-tools: [Read, Grep, "Bash(git:*)"]
model: haiku
context: inline | fork
agent: general-purpose
paths: src/**/*.{ts,tsx}    # Conditional activation
effort: medium
---
# Skill content (markdown + shell blocks)
```

### Key Patterns
- **Conditional activation** — skills with `paths:` stay hidden until matching files are touched. Prevents overwhelming the model with irrelevant options.
- **Inline vs fork** — inline skills expand into the conversation; forked skills spawn a sub-agent with the skill as system prompt.
- **Dynamic discovery** — when model reads/writes files, walks up directory tree looking for `.claude/skills/` dirs.
- **Deduplication** — uses `realpath()` to handle symlinks; first-wins preserves source precedence.

### YARNNN Relevance
- **Conditional activation** is directly applicable to task-type-specific capabilities. Tasks could declare which primitives/skills they need rather than loading everything.
- **SKILL.md convention** validates YARNNN's ADR-118 approach. Our render skills already follow this pattern.
- **Multi-source precedence** is overkill for YARNNN (we don't have managed/user/project separation).

---

## 2. Tools System

### Architecture
Factory pattern via `buildTool()` from `ToolDef` -> `Tool`. Every tool has:
- **Execution**: `call(args, context, canUseTool, parentMessage, onProgress?)`
- **Safety flags**: `isReadOnly()`, `isDestructive()`, `isConcurrencySafe()`
- **Permission check**: `checkPermissions()` with pattern matching
- **UI rendering**: React components for progress/results

### Permission Model (3 layers)
1. **Tool-level validation** — Zod schema (fail-closed)
2. **Permission rules** — glob/regex pattern matching per tool (e.g., `Bash(git:*)`)
3. **User prompting** — dialog unless auto-allow/auto-deny mode

### Tool Categories
- **Core file ops**: Read, Edit, Write, Glob, Grep, NotebookEdit
- **Execution**: Bash, PowerShell, REPL
- **Web**: WebSearch, WebFetch
- **Multi-agent**: Agent (spawn subagent), Skill (invoke skill), TeamCreate/Delete
- **Tasks**: TaskCreate/Get/List/Update/Output/Stop, TodoWrite (legacy)
- **Planning**: EnterPlanMode, ExitPlanMode
- **MCP**: MCPTool (dynamic per-server), ListMcpResources, ReadMcpResource, McpAuth
- **Scheduling**: CronCreate/Delete/List, RemoteTrigger

### Deferred Loading
Heavy tools only loaded when explicitly requested via ToolSearch. Model calls `ToolSearchTool` to find tools by keyword. Reduces initial prompt size.

### YARNNN Relevance
- **`isReadOnly`/`isDestructive` per tool** — worth adopting for TP primitives. Would allow auto-approving safe operations.
- **Deferred loading** — YARNNN could defer rarely-used primitives, reducing prompt size for common interactions.
- **Tool result size caps** — CC caps results at 100KB with disk spillover. YARNNN should consider similar limits for context-heavy primitives.

---

## 3. Hooks System

### What Hooks Are
Tripwires in the conversation lifecycle. The **harness** (not Claude) executes them. They fire at specific events and can inject context, block execution, or modify tool inputs.

### The Flow
```
User types message
    |
[UserPromptSubmit hook fires]
    | hook can: inject context, block submission (exit 2)
    v
Claude thinks, decides to call a tool (e.g., Edit)
    |
[PreToolUse hook fires, matcher: "Edit"]
    | hook can: BLOCK the tool, MODIFY the tool's input, inject context
    v
Tool executes
    |
[PostToolUse hook fires, matcher: "Edit"]
    | hook can: inject context, run prettier on the file
    v
Claude responds
    |
[Stop hook fires]
```

### 25 Event Types
**Lifecycle**: SessionStart, SessionEnd, Setup, CwdChanged, FileChanged, ConfigChange, WorktreeCreate/Remove
**Execution**: PreToolUse, PostToolUse, PostToolUseFailure, PermissionDenied, PermissionRequest, UserPromptSubmit, SubagentStart/Stop, Stop/StopFailure
**Memory**: InstructionsLoaded
**Specialized**: PreCompact, PostCompact, Notification, TeammateIdle, TaskCreated/Completed, Elicitation/ElicitationResult

### 5 Hook Types
1. **Command** — shell script, exit code semantics (0=success, 2=blocking error)
2. **Prompt** — Claude invocation with structured input
3. **Agent** — spawn full agent task
4. **HTTP** — POST to external endpoint
5. **Function** — runtime TypeScript callbacks (internal only)

### Hook Configuration (settings.json)
```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Write|Edit",
      "hooks": [{
        "type": "command",
        "command": "jq -r '.tool_input.file_path' | { read -r f; prettier --write \"$f\"; }",
        "timeout": 30
      }]
    }]
  }
}
```

### PreToolUse: Input Modification & Blocking
The most powerful hook. Can return:
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow|deny|ask",
    "updatedInput": { "file_path": "/modified/path.txt" },
    "additionalContext": "Extra context for Claude"
  }
}
```

**Important**: Hook `allow` does NOT bypass settings.json deny/ask rules. If settings.json has `deny` -> hook allow still gets overridden.

### PostToolUse: Post-Processing
Fires after tool completes. Can inject context or modify MCP tool output (not built-in tool output — tool already ran).

### UserPromptSubmit
Fires after user submits, before Claude's turn. Receives `{ prompt: "user's text" }` on stdin. Can inject `additionalContext` or block (exit 2). **Cannot modify** the user's message.

### SessionStart
Fires on startup/resume/clear/compact. Can inject `additionalContext`, set `initialUserMessage` (auto-sent as first message), and register `watchPaths` for FileChanged hooks. Can write env vars to `$CLAUDE_ENV_FILE` for subsequent bash commands.

### Execution Model
- **Parallel** — all matching hooks for an event run concurrently
- **Per-hook timeouts** — default 10 minutes, configurable
- **Async hooks** — `async: true` backgrounds the hook, `asyncRewake: true` also wakes model on completion
- **Trust-gated** — no hooks run until workspace trust is accepted (interactive mode)

### YARNNN Relevance
- YARNNN uses 2 hooks (UserPromptSubmit for discipline reminders, SessionStart for orientation). This covers our needs.
- **PreToolUse/PostToolUse** could be useful for audit logging or rate limiting primitive calls, but premature now.
- **Hook types beyond shell** (prompt hooks, agent hooks, HTTP hooks) are interesting but overkill for YARNNN.

---

## 4. Tasks System (Background Process Tracking)

### What Tasks Are
CC's system for **running things in the background while the user keeps chatting**. When "npm test" takes 3 minutes, you don't stare at a spinner — the test runs in background, you keep working, and Claude gets notified when it's done.

### 7 Task Types
| Type | What It Is | Example |
|------|-----------|---------|
| `local_bash` | Shell command | `npm test`, `docker build` |
| `local_agent` | Subagent (Agent tool) | Research task spawned in background |
| `remote_agent` | Cloud session | Ultraplan, background PR creation |
| `in_process_teammate` | Cowork teammate | Multi-agent collaboration |
| `dream` | Memory consolidation | Auto-reviews sessions, updates memory files |
| `local_workflow` | Workflow script | Feature-gated |
| `monitor_mcp` | MCP monitor | Feature-gated |

### Task Lifecycle
```
pending --> running --> completed --+
                 |         ^       |
                 +--> failed  +     +--> [evicted after grace period]
                 |         ^       |
                 +--> killed --+--+
                        ^        |
                   [notified=true]
                      |
                  [grace period]
                      |
                 [evict from AppState]
```

### How the Model Learns a Task Finished
When a background task completes, the harness injects XML into the message stream:

```xml
<task_notification>
  <task_id>b123abc</task_id>
  <output_file>/Users/you/.claude/tasks/b123abc.log</output_file>
  <status>completed</status>
  <summary>Background command "npm test" completed (exit code 0)</summary>
</task_notification>
```

Claude sees this, can `Read` the output file, and respond with results. The model doesn't poll — it gets interrupted with a notification.

### Notification Deduplication
- `notified` flag set atomically in `updateTaskState()` to prevent double-notification
- Eviction only happens after both terminal status AND notified=true
- Killed tasks suppress notifications for bash (noise reduction)

### Progress Tracking
```typescript
{
  toolUseCount: number,           // Total tool invocations
  latestInputTokens: number,      // Context size (cumulative in API)
  cumulativeOutputTokens: number, // Summed output tokens
  recentActivities: string[]      // Last 5 tool uses with descriptions
}
```

### Concrete Example: Backgrounding a Running Agent

1. User: "research this in the background"
2. Claude calls Agent tool with `run_in_background: true`
3. `registerTask()` adds to `AppState.tasks` with unique ID
4. Subagent spawns, output streams to `~/.claude/tasks/{id}.log`
5. Footer pill shows "1 local agent"
6. User keeps chatting about other things
7. Subagent finishes
8. `updateTaskState()` -> status='completed', `notified=true`
9. XML notification injected into Claude's message stream
10. Claude: "The research agent found 3 relevant papers..."
11. Task evicted from AppState after grace period

### The Dream Task (Memory Consolidation)
A special background subagent that:
1. Reviews recent sessions (tracks `sessionsReviewing` count)
2. Extracts patterns, preferences, project context
3. Writes/updates memory files (tracks `filesTouched[]`)
4. Shows "dreaming" in footer pill
5. Has phases: `starting` -> `updating` (when first Edit/Write lands)
6. On kill: rolls back consolidation lock mtime (safe abort)
7. **No model notification** — dream is UI-only, not surfaced to Claude

YARNNN does similar work with nightly memory extraction cron (`memory.py`), but CC's approach is per-session and immediate rather than batched nightly.

### Footer Pill (UI Surface)
Background tasks show in a compact footer:
- "1 shell" / "3 shells" — bash commands
- "1 local agent" — subagent running
- "1 team" — teammate in cowork
- "dreaming" — memory consolidation
- "open/filled ultraplan" — with CTA "press down-arrow to view"

### YARNNN Relevance
- **Progress tracking** — YARNNN's `agent_runs` is simpler (start -> content -> done). Accumulating tool use count + recent activities per run would improve observability.
- **XML notification pattern** — structured completion signals. If YARNNN adds real-time run monitoring (e.g., in the meeting room / task detail), this pattern applies.
- **Dream task** — immediate per-session memory consolidation vs YARNNN's nightly cron. A per-run reflection step could be more responsive to feedback.
- **Notification deduplication** — atomic `notified` flag prevents double-notification. Relevant if YARNNN adds run completion webhooks.

---

## 5. Memory System (Highest YARNNN Relevance)

### Architecture
File-per-memory in `~/.claude/projects/{sanitized-root}/memory/` with `MEMORY.md` as index.

### 4 Closed Types
| Type | Scope | When to Save | Structure |
|------|-------|-------------|-----------|
| **User** | Private | Learning user details | Free-form |
| **Feedback** | Private/Team | Corrections OR confirmations | Rule + **Why:** + **How to apply:** |
| **Project** | Private/Team | Who/what/why/when (absolute dates) | Fact + **Why:** + **How to apply:** |
| **Reference** | Team | External system pointers | Pointer + purpose |

### What NOT to Save (Explicit Exclusions)
- Code patterns, architecture, file paths (derivable from code)
- Git history (use `git log`)
- Debugging solutions (fix is in code, context in commit)
- CLAUDE.md content (already loaded)
- Ephemeral task details

### Retrieval: LLM-Powered Selection
1. Scan all memory file headers (name, description, type, mtime)
2. Filter already-surfaced memories
3. Call **Haiku** with `SELECT_MEMORIES_SYSTEM_PROMPT`
4. Model selects up to 5 most relevant
5. Add staleness caveat if >1 day old

### Staleness Caveat (injected as system-reminder)
> "This memory is {N} days old. Memories are point-in-time observations, not live state — claims about code behavior or file:line citations may be outdated. Verify against current code before asserting as fact."

### Index Truncation
- Line cap: 200 lines
- Byte cap: 25KB
- Warning suffix if truncated

### YARNNN Relevance
- **Staleness caveat** — YARNNN agents read workspace context without freshness signals. Adding "written N days/runs ago" to injected context would improve reliability.
- **LLM-powered memory selection** — instead of loading all workspace files, a cheap Haiku call could pick the 5 most relevant for a given task execution. Reduces context bloat.
- **Explicit exclusions** — CC's "what NOT to save" list prevents memory pollution. YARNNN's feedback distillation could benefit from similar guardrails.
- **Structured feedback format** (Rule + Why + How to apply) — worth adopting for YARNNN's `memory/feedback.md` files.

---

## 6. Query Engine (Conversation Loop)

### Architecture
Async generator state machine yielding messages + stream events.

### Per-Turn Lifecycle
1. **Attachment** — memory prefetch, skill discovery (parallel with streaming)
2. **Compaction cascade** (before API call):
   - Tool result budget enforcement (per-message caps)
   - Snip compaction (prune deep history, keep tail)
   - Microcompact (time-based tool result cleanup)
   - Autocompact (full Claude summary when >threshold, 13k token buffer)
3. **API call** — streaming with tool execution
4. **Recovery** — prompt-too-long -> reactive compact -> retry
5. **Stop hooks** — post-turn background work (memory extraction, suggestions)

### Key Constants
- `AUTOCOMPACT_BUFFER_TOKENS = 13000` — trigger threshold
- Max output tokens escalation: 8k default -> 64k on overflow
- Diminishing returns detection: 3+ continuations with <500 delta tokens -> stop

### YARNNN Relevance
- **Compaction cascade** — YARNNN's TP sessions grow unbounded. A staged compression strategy (cheap pruning first, expensive summarization last) would prevent context overflow.
- **Streaming tool execution** — execute tools as they arrive from the model, not batch after. Could improve TP responsiveness.
- **Stop hooks** — post-turn background work. YARNNN could extract feedback or update workspace state after each TP interaction without blocking the response.

---

## Cross-Comparison Summary

### What YARNNN Should Learn

1. **Memory staleness caveats** — cheap, high-impact improvement to agent context reliability
2. **LLM-powered context selection** — Haiku picks top-N relevant files instead of loading everything
3. **Structured feedback format** — Rule + Why + How to apply
4. **Tool safety classification** — `isReadOnly`/`isDestructive` per primitive
5. **Conditional capability activation** — don't show agents capabilities they won't use for this task

### What YARNNN Should Ignore

1. **CLI UX patterns** — CC is a terminal app; YARNNN is a web app
2. **Permission dialogs** — CC asks humans; YARNNN agents run unattended
3. **Multi-source skill precedence** — managed/user/project layers are for developer tools
4. **Team memory / cowork** — CC's multi-user patterns don't apply to YARNNN's workspace model
5. **Compaction implementation details** — the concept applies, but CC's implementation is for interactive chat, not agent runs

### What YARNNN Already Does Better

1. **Workspace as filesystem** — YARNNN's `workspace_files` is a proper virtual FS with search, embedding, lifecycle. CC's memory is flat files.
2. **Multi-agent coordination** — YARNNN has agents with types, tasks, scheduling. CC's "teammates" are ephemeral in-process agents.
3. **Structured output pipeline** — YARNNN's task pipeline (context -> generate -> deliver) is purpose-built for recurring work. CC generates ad-hoc.
4. **Domain-scoped context** — YARNNN's context domains (`/workspace/context/competitors/`, etc.) are richer than CC's flat memory.

---

## Key Takeaway

CC is a masterclass in **developer tool engineering** — permission cascades, compaction, progressive disclosure, safety classification. But YARNNN's problem space (autonomous recurring agents) is different enough that wholesale adoption would be wrong. Cherry-pick the patterns listed above; ignore the rest.

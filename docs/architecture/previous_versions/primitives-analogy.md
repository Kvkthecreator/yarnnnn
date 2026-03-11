# Primitives Analogy: Filesystem ↔ Entities ↔ MCPs

> **Status**: Design Reference
> **Created**: 2026-02-11
> **Related**: [primitives.md](./primitives.md), ADR-036/037

---

## The Core Analogy

YARNNN primitives mirror Claude Code's filesystem operations, but operate on **entities** (database) and **platforms** (APIs via MCP).

```
Claude Code (Files)     →  YARNNN (Entities)      →  YARNNN (Platforms via MCP)
─────────────────────────────────────────────────────────────────────────────────
Read(file_path)         →  Read(ref)              →  Read(platform:slack/channels)
Write(file_path)        →  Write(ref)             →  Execute(platform.publish)
Edit(file_path)         →  Edit(ref)              →  (platforms are read-mostly)
Glob(pattern)           →  List(pattern)          →  List(platform:*)
Grep(pattern)           →  Search(query)          →  Search across platform content
Bash(command)           →  Execute(action)        →  Execute(platform.sync)
TodoWrite(todos)        →  Todo(todos)            →  (same)
```

---

## Substrate Mapping

| Concept | Claude Code | YARNNN |
|---------|-------------|--------|
| **Storage** | Filesystem | Supabase (entities) + Platform APIs |
| **Address** | `/path/to/file` | `type:identifier` |
| **Read** | File content | Entity JSON |
| **Write** | Create file | Insert row |
| **Edit** | Modify file | Update row |
| **Search** | Grep (regex) | Semantic (embeddings) |
| **List** | Glob (pattern) | Filter (query params) |
| **Execute** | Bash (shell) | MCP (platform APIs) |

---

## Reference Syntax Analogy

```
Filesystem Path              YARNNN Reference
───────────────────────────────────────────────
/src/main.py                 agent:uuid-123
/src/*.py                    agent:*
/src/                        agent:?status=active
./main.py                    agent:latest
(create new)                 agent:new
```

### Entity Types as "Directories"

| Entity Type | Analogous To | Contains |
|-------------|--------------|----------|
| `agent` | `/agents/` | Recurring content configs |
| `platform` | `/platforms/` or `/mnt/` | Connected integrations |
| `memory` | `/context/` | Knowledge/facts |
| `document` | `/uploads/` | User-uploaded files |
| `work` | `/jobs/` | One-time agent tasks |
| `session` | `/sessions/` | Chat history |

---

## Platform Integration via MCP

Platforms (Slack, Gmail, Notion) are like **mounted filesystems** or **remote drives**:

```
Claude Code                   YARNNN
───────────────────────────────────────────────
/mnt/github/                  platform:github
/mnt/github/issues            Execute(action="platform.sync", target="platform:github")
git clone ...                 Execute(action="platform.auth", target="platform:slack")
git push ...                  Execute(action="platform.publish", ...)
```

### MCP as the "Driver Layer"

```
┌─────────────────────────────────────────────────────────────────┐
│                         YARNNN TP                                │
│                    (issues primitives)                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Execute Primitive                           │
│              (routes to appropriate handler)                     │
└─────────────────────────────────────────────────────────────────┘
                              │
            ┌─────────────────┼─────────────────┐
            ▼                 ▼                 ▼
     ┌───────────┐     ┌───────────┐     ┌───────────┐
     │  Slack    │     │  Gmail    │     │  Notion   │
     │  MCP      │     │  API      │     │  MCP      │
     └───────────┘     └───────────┘     └───────────┘
```

---

## Inline Display Analogy

Claude Code shows file operations inline in the terminal. YARNNN should show entity operations inline in chat.

### Current State (Implemented)

| Primitive | Claude Code Display | YARNNN Display |
|-----------|---------------------|----------------|
| Read | File content preview | ✅ Entity card (title, status, key fields) |
| Write | "Created file.py" | ✅ Confirmation card + entity type |
| Edit | Diff view | ✅ Change summary (field: old → new) |
| List | File list | ✅ Entity-type-aware compact list |
| Search | Match results | ✅ Query + match count |
| Execute | Command output | ✅ Action result card |
| Todo | Progress bar | ✅ Progress indicator |

### Implementation

**Component:** `web/components/tp/ToolResultCard.tsx`

```tsx
// Actual implementation
<ToolResultCard result={toolResult} compact={true} />
<ToolResultList results={toolResults} compact />
```

**Entity-aware rendering** - Each entity type displays appropriate fields:
- `agent`: title, status badge (active/paused), frequency
- `memory`: content preview, tags as chips
- `platform`: provider name, connection status
- `work`: description, status

See [primitives.md](./primitives.md#entity-schemas) for full schema reference.

---

## Action Catalog (Execute Primitive)

Like shell commands, Execute actions follow namespaced conventions:

| Action | Analogous Bash | Description |
|--------|----------------|-------------|
| `platform.sync` | `git pull` | Fetch latest from platform |
| `platform.publish` | `git push` | Send content to platform |
| `platform.auth` | `ssh-keygen` | Set up credentials |
| `agent.generate` | `make build` | Run content generation |
| `agent.schedule` | `crontab -e` | Configure timing |
| `memory.extract` | `grep -o` | Extract facts from content |

---

## Configuration Benchmark

### Claude Code Configuration

```
~/.claude/           # User config root
├── settings.json    # Preferences
├── projects/        # Project-specific
└── keys/            # API keys
```

### YARNNN Configuration (Analogous)

```
user_profile (Supabase)     # User config root
├── preferences             # UI/behavior settings
├── context_domains/        # Domain-specific context
└── user_integrations/      # Platform credentials (OAuth)
```

### Per-Entity Configuration

```
Claude Code (per project)    YARNNN (per agent)
───────────────────────────────────────────────────
.claude/project.json         agent.sources
.gitignore                   agent.extraction_rules
package.json                 agent.output_config
```

---

## Implementation Status

### ✅ 1. Inline Display (Completed 2026-02-11)

**Status:** Implemented

**Implementation:**
- `web/components/tp/ToolResultCard.tsx` - Entity-aware inline cards
- `web/components/desk/ChatFirstDesk.tsx` - Renders `ToolResultList`
- `web/components/tp/TPMessages.tsx` - Renders `ToolResultList`

Each primitive type renders appropriate content:
- Read/Write/Edit: Entity preview with type-specific fields
- List: Compact entity rows with status indicators
- Search: Query and match count
- Execute: Action name and result message
- Todo: Progress bar

### 🔲 2. Platform Read Operations

**Status:** Not started

**Current:** Platforms are write-mostly (publish, sync)

**Target:** Read from platforms like reading files

```python
# Future: Read from platform like reading a file
Read(ref="platform:slack/channels/C123/messages?limit=10")
```

### 🔲 3. Entity Subpaths

**Status:** Partial (credentials subpath works)

**Current:** Basic subpath support (`platform:twitter/credentials`)

**Target:** Full nested navigation

```python
Read(ref="agent:uuid/versions/latest")
Read(ref="agent:uuid/sources/0")
```

---

## Design Principles

1. **Isomorphism**: Every Claude Code operation has a YARNNN equivalent
2. **Familiarity**: Developers who know Claude Code understand YARNNN primitives
3. **Composability**: Complex operations = primitive compositions
4. **Visibility**: Inline display makes operations transparent
5. **Extensibility**: New entity types = new "directories", not new primitives

---

## See Also

- [Primitives Architecture](./primitives.md) - Full primitive specification
- [TP Prompt Guide](./tp-prompt-guide.md) - How TP uses primitives
- [ADR-036](../adr/ADR-036-two-layer-architecture.md) - Two-Layer Architecture

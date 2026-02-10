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
/src/main.py                 deliverable:uuid-123
/src/*.py                    deliverable:*
/src/                        deliverable:?status=active
./main.py                    deliverable:latest
(create new)                 deliverable:new
```

### Entity Types as "Directories"

| Entity Type | Analogous To | Contains |
|-------------|--------------|----------|
| `deliverable` | `/deliverables/` | Recurring content configs |
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

### Current State

| Primitive | Claude Code Display | YARNNN Display (Current) |
|-----------|---------------------|--------------------------|
| Read | File content preview | ❌ Just counter |
| Write | "Created file.py" | ❌ Just counter |
| Edit | Diff view | ❌ Just counter |
| List | File list | ❌ Just counter |
| Search | Match results | ❌ Just counter |

### Target State

| Primitive | YARNNN Display (Target) |
|-----------|-------------------------|
| **Read** | Entity card (title, status, key fields) |
| **Write** | Confirmation card + preview |
| **Edit** | Change summary ("status: active → paused") |
| **List** | Compact entity grid/list |
| **Search** | Results with relevance scores |
| **Execute** | Action result card (success/error + details) |

### Display Component Mapping

```tsx
// Target inline rendering structure
<ToolResultCard>
  <ToolResultHeader>
    <PrimitiveIcon type="Read" />
    <EntityRef ref="deliverable:uuid-123" />
  </ToolResultHeader>
  <ToolResultBody>
    <EntityPreview data={result.data} type="deliverable" />
  </ToolResultBody>
</ToolResultCard>
```

---

## Action Catalog (Execute Primitive)

Like shell commands, Execute actions follow namespaced conventions:

| Action | Analogous Bash | Description |
|--------|----------------|-------------|
| `platform.sync` | `git pull` | Fetch latest from platform |
| `platform.publish` | `git push` | Send content to platform |
| `platform.auth` | `ssh-keygen` | Set up credentials |
| `deliverable.generate` | `make build` | Run content generation |
| `deliverable.schedule` | `crontab -e` | Configure timing |
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
Claude Code (per project)    YARNNN (per deliverable)
───────────────────────────────────────────────────
.claude/project.json         deliverable.sources
.gitignore                   deliverable.extraction_rules
package.json                 deliverable.output_config
```

---

## Implementation Gaps

### 1. Inline Display (Priority)

**Current:** Tool results show only `{N} action(s) performed`

**Target:** Rich inline cards per primitive type

**Files to modify:**
- `web/components/desk/ChatFirstDesk.tsx` - Add inline result rendering
- `web/components/tp/` - Create `ToolResultCard`, `EntityPreview` components

### 2. Platform Read Operations

**Current:** Platforms are write-mostly (publish, sync)

**Target:** Read from platforms like reading files

```python
# Future: Read from platform like reading a file
Read(ref="platform:slack/channels/C123/messages?limit=10")
```

### 3. Entity Subpaths

**Current:** Basic subpath support (`platform:twitter/credentials`)

**Target:** Full nested navigation

```python
Read(ref="deliverable:uuid/versions/latest")
Read(ref="deliverable:uuid/sources/0")
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

# Primitives Architecture Discourse

> **Date**: 2026-02-10
> **Participants**: Kevin Kim, Claude
> **Outcome**: First principles analysis of agent primitives
> **Context**: ADR-036/037 Chat-First implementation session
> **Duration**: Extended architectural discourse following implementation work

---

## Executive Summary

This document captures a fundamental architectural discourse that emerged during the ADR-037 (Chat-First Surface Architecture) implementation session. What began as tactical UX fixes evolved into a first-principles examination of whether YARNNN needs its own agent primitives or should directly adopt/wrap the primitives proven by Claude Code.

**Key insight discovered**: Claude Code's primitives (Read, Write, Edit, Grep, Glob, Bash, Task, TodoWrite) aren't arbitrary—they're the minimal sufficient set for any agent operating on structured data. YARNNN's domain-specific tools should be reconceived as implementations of these universal primitives against a different substrate (database/APIs instead of filesystem).

---

## Part 1: Background and Context

### The Session's Origin

The session began with tactical implementation work:
- Adding ephemeral image attachment support (Claude Code style)
- Fixing empty TP message bubbles
- Removing legacy OPEN_SURFACE ui_actions from tools
- Implementing route-first navigation per ADR-037

### The Pivot Point

After removing OPEN_SURFACE actions from 8 tool occurrences in `project_tools.py`, Kevin observed that we might have misunderstood the deeper intent of ADR-036/037:

> "ui_actions and redirects actually isn't needed. everything stays in chat..."

This triggered a shift from "how do we fix these UX issues" to "what is the fundamental interaction model we're building toward?"

### Kevin's Framing Question

> "my assumption is that, the primitive approach and trying our best to layer on top of the more fundamental and thus closer mirroring to that of claude code may actually end up being more straightforward implementation..."

This led directly to the discourse on primitives.

---

## Part 2: What Claude Code Actually Does

### Requested Analysis

Kevin asked for a "discourse on claude code fundamentals" with "specific primitives and how they're working" - focusing on tool-calling patterns, sequencing, and why the claude code UX "feels great."

### The Primitive Inventory

Claude Code's tool set can be categorized:

| Primitive | Function | Why It Exists |
|-----------|----------|---------------|
| **Read** | Retrieve state | Agent cannot act without perceiving |
| **Write** | Create new state | Creation is distinct from modification |
| **Edit** | Modify existing state | Surgical changes preserve context |
| **Grep** | Find by content/pattern | Semantic search across state |
| **Glob** | Find by structure/name | Structural navigation |
| **Bash** | Execute in environment | Side effects / external systems |
| **Task** | Delegate to sub-agent | Composition / divide-and-conquer |
| **TodoWrite** | Track intent | Working memory externalization |

### The Key Observation: Infrastructure Invisibility

Claude Code's primitives are what ADR-036 calls "Infrastructure Layer" - they're invisible to the user. Users don't think about Read/Write/Edit. They see:
- Code appearing
- Problems getting solved
- Changes happening

The primitives are plumbing. The interaction layer (conversation, inline rendering, status indicators) is what users experience.

### Sequencing and Agentic Loops

Claude Code's power comes from:
1. **Tool → Result → Reasoning → Tool** loops that continue until task complete
2. **TodoWrite** externalizing intent so the agent doesn't forget
3. **Task** enabling sub-agent delegation for complex work
4. **Inline rendering** of results without navigating away

The user stays in one place (the conversation). Work happens through tool calls. Results appear inline.

---

## Part 3: The Critical Question

### Kevin's Axiomatic Challenge

> "do we even need our own primitives? is there anyway we can just surface claude code 'almost like an API wrapper, but everything wrapper?' if not, could not the primitives be the same? grep, todo, read, write, such forth? please help us stay grounded in first principles and rational approach here with your assessment. even axiomatic thinking"

This is the question that prompted full first-principles analysis.

---

## Part 4: First Principles Assessment

### Axiom 1: The Primitive Set is Universal

Claude Code's primitives aren't "Claude Code's primitives"—they're **the** primitives. Any sufficiently capable agent converges here because these operations are the minimal sufficient set for operating on structured data:

| Operation | Why Fundamental |
|-----------|-----------------|
| **Read** | Cannot act without perceiving state |
| **Write** | Creation is a distinct operation from modification |
| **Edit** | Surgical modification preserves context (vs. full rewrite) |
| **Search by content** | Finding by what something contains |
| **Search by structure** | Finding by where something is / what it's named |
| **Execute externally** | Affecting systems outside the agent's direct control |
| **Delegate** | Composition enables handling complexity beyond single-agent capacity |
| **Track intent** | Externalizing working memory enables long-running coherent work |

This set is not arbitrary. It emerges from information theory and the requirements of autonomous operation.

### Axiom 2: Domain = Target, Not Method

YARNNN's domain differs from Claude Code's only in **what** it operates on, not **how**:

| Claude Code Target | YARNNN Target |
|-------------------|---------------|
| Files | Deliverables, Platforms, Memories |
| Directories | Collections, Lists |
| File content | Deliverable content, Platform config |
| Codebase | Knowledge base / Context |
| Git/npm/shell | Platform APIs (Twitter, Slack, etc.) |

The **operations** are identical. The **substrate** differs.

### Axiom 3: Wrapping vs Implementing

**Can we literally wrap Claude Code?**

Technically no. Claude Code is a CLI tool that operates on files. You can't call `claude read` to read a deliverable from Supabase.

**Can we adopt the same primitives?**

Absolutely yes. We can:
1. Mirror the primitive interface exactly
2. Implement against our domain substrate

```python
# Claude Code: Read operates on files
claude.Read(file_path="/src/main.py")

# YARNNN: Read operates on entities
yarnnn.Read(ref="deliverable:uuid-123")
yarnnn.Read(ref="platform:twitter")
yarnnn.Read(ref="memory:uuid-456")
```

The semantics are identical. The implementation differs.

### Axiom 4: The API is the Same, The Substrate Differs

This is the key architectural insight:

**Shared between Claude Code and YARNNN:**
- Same tool interface contract (input → output)
- Same message/response streaming patterns
- Same inline rendering philosophy
- Same todo tracking for intent
- Same task delegation for complexity

**Different between Claude Code and YARNNN:**
- Substrate: filesystem vs database + external APIs
- Entities: files vs deliverables/platforms/memories
- External systems: git/npm vs Twitter/Slack/Gmail

---

## Part 5: Implications for YARNNN Architecture

### Current Tool Architecture (Before This Analysis)

YARNNN's current TP tools are **composed operations**:

```python
# Current tools are high-level operations
create_deliverable(type, platform, schedule, ...)
list_platforms()
publish_content(deliverable_id, ...)
fetch_latest_content(platform, channel, ...)
```

These are useful but they're not primitives. They're conveniences built on implicit primitives.

### Proposed Primitive-Based Architecture

**Core Primitives (mirror Claude Code):**

| YARNNN Primitive | Claude Code Equivalent | What It Does |
|-----------------|------------------------|--------------|
| `Read(ref)` | `Read(file_path)` | Get any entity by reference |
| `Write(ref, content)` | `Write(file_path, content)` | Create new entity |
| `Edit(ref, changes)` | `Edit(file_path, old, new)` | Modify existing entity |
| `Search(query)` | `Grep(pattern)` | Find entities by content |
| `List(pattern)` | `Glob(pattern)` | Find entities by structure/type |
| `Execute(action)` | `Bash(command)` | External system operations |
| `Task(prompt)` | `Task(prompt)` | Delegate to sub-agent |
| `Todo(items)` | `TodoWrite(items)` | Track intent/progress |

**Domain Operations become Execute targets:**

```python
# Instead of:
publish_content(deliverable_id)

# Becomes:
Execute(action="publish", target="deliverable:uuid", platform="twitter")

# Instead of:
fetch_latest_content(platform, channel)

# Becomes:
Execute(action="sync", target="platform:slack", scope="channel:C123")
```

### The Reference System

A key implementation detail: **entity references** that work like file paths:

```
deliverable:uuid-123          # Specific deliverable
deliverable:*                 # All deliverables
platform:twitter              # Platform by name
platform:twitter/posts        # Sub-entity
memory:uuid-456               # Specific memory
memory:type=fact              # Query-based reference
```

This mirrors how file paths work but for YARNNN's entity types.

---

## Part 6: What This Enables

### Simpler Mental Model

Instead of learning 15+ domain-specific tools, TP works with 8 universal primitives. The domain specificity moves to the reference system and action types.

### Easier Evolution

As LLM providers improve tool calling (which they will), YARNNN automatically benefits. We're building on the same patterns that Anthropic, OpenAI, and others are optimizing for.

### Better Inline Experience

When tools are primitives, their results are naturally displayable inline:
- `Read` → show content
- `Write` → show confirmation + preview
- `Edit` → show diff
- `Search` → show results
- `Execute` → show action result

This aligns perfectly with ADR-036's vision: infrastructure invisible, results inline.

### Composition Over Convention

Complex workflows become primitive compositions:

```
"Create a weekly standup deliverable for Twitter"

TP composes:
1. Read(ref="platform:twitter")           # Check platform exists
2. Write(ref="deliverable:new", content={
     type: "thread",
     platform: "twitter",
     schedule: "weekly"
   })                                      # Create the deliverable
3. Todo([{content: "Created deliverable", status: "completed"}])
```

The TP decides the composition. We provide the primitives.

---

## Part 7: Downstream Implications

### For TP (Thinking Partner)

1. **Tool Reduction**: Replace 15+ tools with 8 primitives + reference syntax
2. **System Prompt Simplification**: Primitive semantics are universal, less explanation needed
3. **Agentic Loops**: More natural tool chaining since primitives are composable

### For Frontend (Chat-First)

1. **Inline Rendering**: Each primitive has a natural inline display
2. **Status Indicators**: Primitive-based status is simpler (reading... writing... searching...)
3. **Result Uniformity**: All primitive results follow same display patterns

### For Backend

1. **API Simplification**: Fewer endpoints, unified around primitive operations
2. **Reference Resolution**: New ref system needs implementation
3. **Action Registry**: External system operations need cataloging

### For Future Development

1. **MCP Alignment**: MCP servers naturally expose Read/Write/Execute primitives
2. **Provider Evolution**: As Claude/GPT improve tool calling, we benefit directly
3. **New Domains**: Adding new entity types = adding new ref patterns, not new tools

---

## Part 8: What We're NOT Doing

### Not: Literally Wrapping Claude Code

Claude Code operates on files. We operate on entities. The substrate is different.

### Not: Abandoning Domain Semantics

References like `deliverable:uuid` and actions like `publish` still encode domain knowledge. We're not making users think in primitives—we're making TP think in primitives.

### Not: Breaking Existing Patterns

Current tools can coexist during migration. They can be reimplemented as primitive compositions internally.

### Not: Over-Abstracting

Primitives should be thin wrappers. `Read("deliverable:123")` should just fetch from database. No magic.

---

## Part 9: Open Questions

### Implementation Questions

1. **Reference Syntax**: What's the exact grammar? `type:id`, `type:id/subpath`, `type:query=value`?
2. **Action Catalog**: What Execute actions exist? How are they discovered?
3. **Error Handling**: How do primitive errors surface inline?
4. **Permissions**: How does ref-based access control work?

### Architectural Questions

1. **Migration Path**: How do we move from current tools to primitives?
2. **Tool Discovery**: Does TP auto-discover available refs and actions?
3. **Batching**: Can primitives be batched? `Read(["deliverable:1", "deliverable:2"])`

### UX Questions

1. **User Visibility**: Do users ever see primitive names or only their results?
2. **Debug Mode**: Should there be a way to see raw primitive calls?
3. **Learning Curve**: Will users understand inline results without primitive context?

---

## Part 10: Relationship to ADR-036 and ADR-037

### ADR-036: Two-Layer Architecture

This discourse directly implements ADR-036's vision:

| Layer | What It Is | Primitives Role |
|-------|------------|-----------------|
| **Interaction Layer** | Fluid conversation, inline results | Results of primitives displayed here |
| **Infrastructure Layer** | Invisible, structured, reliable | Primitives ARE this layer |

The primitives ARE the infrastructure layer. They're the invisible plumbing that makes the interaction layer possible.

### ADR-037: Chat-First Surface

This discourse extends ADR-037:

> "Everything stays in chat"

Primitives make this natural. Every primitive has an inline-displayable result. No navigation needed.

---

## Part 11: Lessons from This Discourse

### On Convergent Design

Multiple AI agent systems are converging on the same primitive set. This isn't coincidence—it's the result of working from first principles on "what operations are sufficient for autonomous work on structured data?"

### On Layering

Domain-specific convenience should layer on universal primitives, not replace them. `create_deliverable` is a convenience that composes `Read` + `Write` + `Todo`. Both can coexist.

### On Future-Proofing

Building on proven primitives means we benefit from ecosystem improvements. As Claude's tool calling improves, our primitive-based system improves automatically.

### On Simplicity

8 primitives is simpler than 20 domain-specific tools. The complexity moves to reference resolution and action catalogs, which are more maintainable.

---

## Appendix A: The Primitive Isomorphism

```
yarnnn.Read(ref)       ≅  claude.Read(file_path)
yarnnn.Write(ref, c)   ≅  claude.Write(file_path, c)
yarnnn.Edit(ref, d)    ≅  claude.Edit(file_path, d)
yarnnn.Search(q)       ≅  claude.Grep(pattern)
yarnnn.List(p)         ≅  claude.Glob(pattern)
yarnnn.Execute(a)      ≅  claude.Bash(cmd)
yarnnn.Task(prompt)    ≅  claude.Task(prompt)
yarnnn.Todo(items)     ≅  claude.TodoWrite(items)
```

The `≅` symbol denotes isomorphism: same structure, different implementation.

---

## Appendix B: Key Quotes from Discussion

> "the primitive approach and trying our best to layer on top of the more fundamental and thus closer mirroring to that of claude code may actually end up being more straightforward implementation..." - Kevin

> "do we even need our own primitives? is there anyway we can just surface claude code 'almost like an API wrapper, but everything wrapper?'" - Kevin

> "Claude Code's primitives aren't arbitrary—they're the minimal sufficient set for any agent operating on a codebase... These aren't 'Claude Code's primitives'—they're THE primitives." - Claude

> "YARNNN's domain differs from Claude Code's only in WHAT it operates on, not HOW." - Claude

> "The API is the Same, The Substrate Differs." - Claude

---

## Appendix C: Reference Materials

- ADR-036: Two-Layer Architecture (Interaction + Infrastructure)
- ADR-037: Chat-First Surface Architecture
- Claude Code documentation (primitives and tool calling)
- [context-domains-discussion-2026-02-09.md](./context-domains-discussion-2026-02-09.md) - Previous first-principles session

---

## Next Steps

This discourse establishes the philosophical and architectural foundation. Implementation would proceed as:

1. **Design Reference Syntax**: Formalize `type:id` grammar
2. **Catalog Execute Actions**: Document all external system operations
3. **Prototype Primitives**: Implement core 8 against existing backend
4. **Migrate Incrementally**: Reimplement current tools as primitive compositions
5. **Update TP System Prompt**: Teach primitive-first thinking

Whether to proceed with this architecture is a product decision that depends on timeline, priorities, and confidence in the direction.

---

*This document is a living analysis. As implementation proceeds, insights should be added.*

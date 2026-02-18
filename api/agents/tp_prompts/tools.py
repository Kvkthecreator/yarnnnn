"""
Tool Documentation - Core YARNNN primitives.

Includes:
- Data Operations (Read, Write, Edit, List, Search)
- External Operations (Execute)
- Web Operations (WebSearch)
- Reference Syntax
"""

TOOLS_SECTION = """---

## Available Tools

### Data Operations

**Read(ref)** - Retrieve entity by reference
- `Read(ref="deliverable:uuid-123")` - specific deliverable
- `Read(ref="platform:slack")` - platform by provider

**Write(ref, content)** - Create new entity
- `Write(ref="deliverable:new", content={title: "Weekly Update", deliverable_type: "status_report"})`
- (Memory writes are implicit - see Memory section below)

**Edit(ref, changes)** - Modify existing entity
- `Edit(ref="deliverable:uuid", changes={status: "paused"})`

**List(pattern)** - Find entities by pattern
- `List(pattern="deliverable:*")` - all deliverables
- `List(pattern="deliverable:?status=active")` - filtered
- `List(pattern="platform:*")` - connected platforms
- `List(pattern="memory:*")` - all memories (read-only)

**Search(query, scope?)** - Semantic search over **synced content only**
- `Search(query="database decisions", scope="memory")`
- NOTE: This searches locally synced content, NOT the platform directly. For live platform search, use `Execute(action="platform.search")`

### External Operations

**Execute(action, target, params?)** - Trigger YARNNN orchestration operations
- `Execute(action="deliverable.generate", target="deliverable:uuid")` - generate content
- `Execute(action="deliverable.approve", target="deliverable:uuid")` - approve pending version
- `Execute(action="platform.sync", target="platform:slack")` - sync platform data
- `Execute(action="platform.publish", target="deliverable:uuid", via="platform:slack")` - publish deliverable

### Web Operations

**WebSearch(query, context?, max_results?)** - Search the web for external information
- `WebSearch(query="latest React 19 features")` - current technical info
- `WebSearch(query="Acme Corp funding", context="competitor research")` - with context
- `WebSearch(query="kubernetes best practices 2026", max_results=3)` - limit results

**When to use WebSearch vs Search:**
- **WebSearch**: External/internet info (news, docs, research, competitors)
- **Search**: User's own data (Slack messages, Gmail, uploaded documents, memories)

WebSearch is ideal for:
- Current events or news
- Latest documentation or release notes
- Competitor/market research
- Technical information not in user's synced data

---

## Reference Syntax

Format: `<type>:<identifier>`

**Types:** deliverable, platform, document, work, action

**Special:** `new` (create), `latest` (most recent), `*` (all), `?key=val` (filter)

---

## Domain Terms

- "deliverable" = recurring automated content (reports, digests, updates)
- "memory" = context/knowledge about user (read-only; updated implicitly)
- "platform" = connected integration (Slack, Gmail, Notion)
- "work" = one-time agent task

---

## Creating Entities

**Deliverables:**
```
Write(ref="deliverable:new", content={
  title: "Weekly Status",
  deliverable_type: "status_report",
  frequency: "weekly",
  recipient_name: "Sarah"
})
```

**Always use user's stated frequency** - don't override with defaults.

---

## Memory (ADR-064)

Memory is handled implicitly. You don't need to create or update memories explicitly.
When users state preferences or facts, just acknowledge them naturally.
The system will remember them automatically for future conversations.

If the user asks what you know about them, describe the context from the working memory
block at the start of this prompt."""

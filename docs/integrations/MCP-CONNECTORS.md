# MCP Connectors: Conceptual Framework

**Last Updated:** 2026-02-25
**Status:** Draft — active discourse, decisions pending
**Technical Implementation:** [ADR-075](../adr/ADR-075-mcp-connector-architecture.md)

---

## What This Document Is

This document captures the product rationale, user flow thinking, and open questions around exposing YARNNN as an MCP server for Claude AI (Desktop + Code) and ChatGPT. It is deliberately separate from the technical ADR because:

1. The technical wiring (how to build an MCP server, transport selection, auth) is a solved problem — ADR-075 covers it
2. The product questions (what tools to expose, what user flows to support, how this reshapes activation) are **not solved** and need ongoing discourse

This document is a living working doc, not a decision record.

---

## The Core Premise

### Why MCP Connectors

YARNNN's current activation requires users to adopt a new product interface (yarnnn.com → Thinking Partner). MCP connectors invert this: **YARNNN goes to where the user already works** (Claude Desktop, ChatGPT).

The user's daily AI interaction doesn't change. They stay in their existing LLM. But now that LLM has access to YARNNN's accumulated context and deliverable pipeline.

```
WITHOUT MCP:
User → yarnnn.com → TP interface → deliverables → value

WITH MCP:
User → Claude/ChatGPT (already open) → YARNNN tools → same pipeline → same value
```

The backend is identical. The activation friction is dramatically lower.

### MCP as Top of Funnel

The MCP connector is a **surface**, not the product. The product is the backend: platform sync, content accumulation, signal processing, memory extraction, deliverable execution. These run regardless of which surface triggers them.

```
┌─────────────────────────────────────────────────────┐
│                  YARNNN BACKEND                      │
│                                                      │
│  Platform Sync ──→ platform_content (accumulation)   │
│  Signal Processing ──→ signal-emergent deliverables  │
│  Memory Extraction ──→ user_context (compounding)    │
│  Deliverable Scheduler ──→ autonomous delivery       │
│                                                      │
├──────────────┬──────────────┬────────────────────────┤
│  Surface 1   │  Surface 2   │  Surface 3             │
│  TP (Web)    │  Scheduler   │  MCP Connector         │
│  Interactive │  Autonomous  │  Embedded in existing   │
│  sessions    │  delivery    │  LLM tools              │
└──────────────┴──────────────┴────────────────────────┘
```

The upgrade path is natural: start with MCP (low friction) → see value → configure deliverables on yarnnn.com for autonomous scheduling → full product adoption.

---

## What Works Today (Prerequisite Understanding)

### The Deliverable Content Architecture

Deliverables have two orthogonal classification axes. The MCP connector interacts with the **trigger** axis, not the **content** axis:

**Content Binding** (where context comes from — unchanged by MCP):

| Binding | What It Does | Example Types |
|---------|-------------|---------------|
| `platform_bound` | Reads from a single platform's synced content | slack_channel_digest, gmail_inbox_brief, meeting_prep, weekly_calendar_preview |
| `cross_platform` | Synthesizes across multiple platforms | status_report, weekly_status, project_brief, stakeholder_update |
| `research` | Web research, optionally grounded in platform content | research_brief, deep_research |
| `hybrid` | Web research + platform data fetched in parallel | intelligence_brief |

**Trigger Origin** (how execution starts — MCP adds a new trigger):

| Origin | Initiated By | Existing? |
|--------|-------------|-----------|
| `scheduled` | Unified scheduler (cron) | Yes |
| `manual` | User via web UI "Run Now" button | Yes |
| `signal_emergent` | Signal processing pipeline | Yes |
| `mcp` | User via Claude/ChatGPT tool call | **New** |

The `mcp` trigger calls the same `execute_deliverable_generation()` as all other triggers. No new pipeline. No different content strategy. A `cross_platform` status report triggered via MCP reads from the same `platform_content` table and produces the same output.

### What the User Must Still Do on yarnnn.com

MCP connectors do not eliminate the web UI. They eliminate the need to **stay** in it:

| Action | Where | Why |
|--------|-------|-----|
| Sign up | yarnnn.com | Account creation |
| Connect platforms (OAuth) | yarnnn.com | OAuth redirects require web browser |
| Configure deliverables | yarnnn.com | Type selection, source mapping, schedule, destination — too complex for MCP tool parameters |
| Generate API token | yarnnn.com Settings | Auth for MCP connection |
| Select sources per platform | yarnnn.com Context pages | Tier-gated source limits |

| Action | Where | Why |
|--------|-------|-----|
| Trigger deliverable execution | Claude/ChatGPT (MCP) | On-demand, in-flow |
| Read deliverable output | Claude/ChatGPT (MCP) | In-context with conversation |
| Query accumulated context | Claude/ChatGPT (MCP) | "What do you know about X?" |
| Check system status | Claude/ChatGPT (MCP) | Transparency |

---

## Open Questions (Active Discourse)

### 1. Tool Surface — What to Expose

ADR-075 proposes 6 tools for MVP. This section captures the reasoning and open questions around each.

**Agreed (high confidence):**

| Tool | Rationale | Open Questions |
|------|-----------|----------------|
| `get_status` | Essential for transparency; also serves as hello-world validation | None — straightforward |
| `list_deliverables` | Users need to discover what's configured before triggering | How much detail? Just titles, or include schedule/destination? |
| `run_deliverable` | Core value — trigger execution from LLM | Async vs sync? Current plan: async (returns immediately). Is polling UX acceptable? |
| `get_deliverable_output` | Read the generated content | Should this include delivery status? Past versions? |

**Probable but needs validation:**

| Tool | Rationale | Open Questions |
|------|-----------|----------------|
| `get_context` | Lets host LLM understand user's accumulated memory | Is this the right interface? Should it be free-text search or structured categories? How does this interact with the host LLM's own memory features (ChatGPT memory, Claude Projects)? |
| `search_content` | Query synced platform content | Does the user understand they're searching cached/synced data, not live? Will staleness cause confusion? Should we surface freshness metadata prominently? |

**Deferred but worth tracking:**

| Tool | Why Interesting | Why Deferred |
|------|----------------|-------------|
| `create_deliverable` | "Set up a weekly Slack digest" from within Claude — very natural | Configuration complexity: type selection, source mapping, schedule, destination. Would need a multi-step conversation flow, not a single tool call. Revisit after seeing how users interact with MVP tools. |
| `add_memory` | "Remember that Acme's contract renews in March" — natural | Memory is implicit (ADR-064). Adding explicit memory writing via MCP contradicts the extraction-based model. But users may want it. Product decision needed. |
| Platform tools (Slack, Gmail, etc.) | "Send this to #general" from Claude via YARNNN | Native platform MCP servers already exist. YARNNN shouldn't duplicate. But: YARNNN has the user's OAuth tokens already. Is there a convenience argument? |

### 2. User Flow Mapping — How Conversations Map to Tool Calls

This is the least resolved area. The host LLM (Claude/ChatGPT) decides which tools to call based on user intent + tool descriptions. We don't control the host LLM's reasoning. But we can shape tool descriptions to guide it.

**Expected natural language → tool mapping:**

| User says (in Claude/ChatGPT) | Expected tool sequence |
|-------------------------------|----------------------|
| "Run my weekly status report" | `list_deliverables()` → identify match → `run_deliverable(id)` → `get_deliverable_output(id)` |
| "What do you know about Project Acme?" | `get_context(search="Acme")` + `search_content(query="Acme")` |
| "What happened in #engineering this week?" | `search_content(query="engineering", platform="slack", days=7)` |
| "Is my data fresh?" | `get_status()` |
| "Show me the last client update you generated" | `list_deliverables()` → identify match → `get_deliverable_output(id)` |

**Unresolved flows:**

| User says | Problem |
|-----------|---------|
| "Write me a status update for the Acme project" | Is this a deliverable trigger (existing deliverable) or a new request? If no matching deliverable exists, what happens? Should the MCP connector suggest creating one on yarnnn.com? |
| "Send this report to my team on Slack" | Delivery is part of the deliverable pipeline (destination is pre-configured). Should MCP allow ad-hoc delivery to arbitrary destinations? This is a significant scope expansion. |
| "What's new since yesterday?" | Maps to `search_content(days=1)` but across all platforms. Is this a deliverable request in disguise (daily digest)? Or a content query? |
| "Remember that I prefer bullet points" | Memory writing — deferred. But the user expects it to work. What's the graceful fallback? |

### 3. Activation Sequencing — When Does MCP Get Offered?

**Current thinking:**

The user must have completed onboarding (connected at least 1 platform, initial sync done) before MCP is useful. MCP without synced content returns empty results.

**Open question:** Where in the activation funnel does MCP connector setup appear?

Option A: **After onboarding, as an alternative to TP**
> "You can chat with your Thinking Partner here, or connect YARNNN to Claude/ChatGPT with this token: [copy]"

Option B: **As the primary path, with TP as the fallback**
> "Connect your platforms, then add YARNNN to Claude or ChatGPT: [setup instructions]. Or use our built-in Thinking Partner."

Option C: **Separate discovery, post-activation**
> After the user has experienced value via TP, surface MCP connector as "Take YARNNN everywhere: connect to Claude or ChatGPT"

Each option has different implications for onboarding flow, Settings page, and messaging. Not decided yet.

### 4. Cross-Platform Synthesis Without Explicit Deliverable

The most interesting (and unresolved) value proposition:

A user in Claude Desktop says "Give me a summary of what happened across my projects this week." They don't have a deliverable configured for this. But YARNNN has the synced content across Slack, Gmail, Notion, and Calendar.

**Options:**

A. **MCP returns raw content, host LLM synthesizes.** `search_content()` returns platform content; Claude/ChatGPT does the synthesis. YARNNN is a data pipe.

B. **MCP triggers an ad-hoc deliverable.** Create a temporary `cross_platform` deliverable, execute it, return the output. YARNNN does the synthesis with its prompt engineering.

C. **Not supported in MVP.** User must configure a deliverable on yarnnn.com first, then trigger it via MCP.

Option A is simplest but loses YARNNN's prompt engineering. Option B is powerful but adds complexity (temporary deliverable lifecycle). Option C is restrictive but clean.

**This is a key product decision that affects the tool surface design.** If we choose B, we need a `generate_ad_hoc` tool. If A, `search_content` is sufficient. If C, current 6-tool surface is correct.

### 5. Token Budget and Tier Implications

MCP tool calls that trigger `run_deliverable` consume token budget (same as any execution trigger). But `get_context` and `search_content` are database reads — no LLM tokens consumed.

**Open question:** Should MCP tool calls have separate rate limits? Or just respect existing tier budgets?

**Current leaning:** Same tier budgets. MCP is just another surface. But `search_content` could be called very frequently by an active host LLM — should there be a read rate limit even though it doesn't consume LLM tokens?

---

## Relationship to Other Surfaces

### MCP Connector vs. Thinking Partner

| Dimension | TP (Web) | MCP Connector |
|-----------|----------|---------------|
| Conversational context | Working memory injected (profile, preferences, recent activity, system state) | None — host LLM provides its own context |
| Skill detection | Hybrid pattern + semantic (ADR-025/040) | None — host LLM reasons about tool selection |
| Multi-turn state | Session-based, compacted (ADR-067) | Stateless per tool call |
| Platform tools | Full set (Slack, Gmail, Notion, Calendar via MCP Gateway + Direct APIs) | Not exposed — use native platform MCPs |
| Memory writing | Implicit extraction at session end (ADR-064) | Not available (deferred) |
| Deliverable creation | Full UI with type selection, source mapping, schedule | Not available (deferred) |

**Key insight:** The MCP connector is deliberately less capable than TP. It's a focused tool surface, not a TP replica. The host LLM provides the conversational intelligence; YARNNN provides the data and execution.

### MCP Connector vs. Scheduler

| Dimension | Scheduler (Cron) | MCP Connector |
|-----------|-------------------|---------------|
| Trigger | Time-based, autonomous | User-initiated, on-demand |
| Frequency | Per deliverable schedule (daily, weekly, etc.) | Ad-hoc |
| Signal processing | Runs independently, creates signal-emergent deliverables | Not involved |
| Delivery | Automatic to configured destination | Same pipeline (delivers to configured destination) |
| Content freshness | Checks freshness before execution (ADR-049) | Same check applies |

**Not competing:** MCP complements the scheduler. Scheduler handles recurring autonomous work; MCP handles "run this now" requests.

---

## Next Steps

1. **Validate technical wiring** — Phase 0 in ADR-075: `get_status` tool via stdio → Claude Desktop
2. **Resolve Open Question #4** (ad-hoc synthesis) — Affects tool surface design
3. **Resolve Open Question #3** (activation sequencing) — Affects onboarding flow
4. **Build MVP tool surface** — Phase 1 in ADR-075: 6 tools
5. **User testing** — Real user triggers deliverable from Claude Desktop, evaluates experience
6. **Iterate on tool descriptions** — How host LLMs actually use the tools may differ from expectations

---

## References

- [ADR-075: MCP Connector Technical Architecture](../adr/ADR-075-mcp-connector-architecture.md) — Implementation spec
- [ADR-050: MCP Gateway Architecture](../adr/ADR-050-mcp-gateway-architecture.md) — Existing outbound MCP
- [ADR-072: Unified Content Layer](../adr/ADR-072-unified-content-layer-tp-execution-pipeline.md) — Backend that MCP surfaces
- [ADR-064: Unified Memory Service](../adr/ADR-064-unified-memory-service.md) — Why memory writing is implicit
- [ADR-068: Signal-Emergent Deliverables](../adr/ADR-068-signal-emergent-deliverables.md) — Backend-only, not exposed via MCP
- [ACTIVATION_PLAYBOOK.md](../ACTIVATION_PLAYBOOK.md) — Current activation strategy (pre-MCP)

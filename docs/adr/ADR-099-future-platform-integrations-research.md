# ADR-099: Future Platform Integrations Research

> **Status**: Research / Not Scoped for Development
> **Created**: 2026-02-12
> **Purpose**: Catalog high-value platform integrations, their MCP maturity, auth models, and integration approach for when YARNNN is ready to expand beyond Slack/Notion/Gmail/Calendar.

---

## Key Learnings from Notion Integration (Feb 2026)

Before evaluating new platforms, the Notion experience taught us critical lessons:

1. **OAuth tokens ≠ internal integration tokens.** The open-source `@notionhq/notion-mcp-server` expects `ntn_` internal tokens, not OAuth access tokens. This is a fundamental incompatibility for multi-tenant SaaS products.

2. **"Has MCP server" is not enough.** You must verify: Does the MCP server support OAuth (multi-tenant)? Or only static API keys (single-user/developer tooling)?

3. **Remote hosted MCP vs local open-source MCP** are fundamentally different architectures. Remote (e.g., `mcp.notion.com/mcp`) supports OAuth natively. Local open-source servers typically expect static tokens.

4. **Direct REST API is always a fallback.** If the MCP ecosystem doesn't support your auth model, the platform's REST API always works with OAuth tokens.

---

## Evaluation Framework

For each platform, we need to answer:

| Question | Why It Matters |
|----------|---------------|
| **Does an official remote MCP server exist?** | Remote servers handle auth, hosting, and maintenance. Best option. |
| **Does it support OAuth / dynamic client registration?** | Required for multi-tenant SaaS like YARNNN. |
| **Is there a usable open-source MCP server?** | Fallback if no remote server, but check auth model. |
| **Does the open-source server accept OAuth tokens?** | If not, it's unusable for us without forking. |
| **Is there a REST API we can call directly?** | Always-available fallback (like Gmail/Calendar pattern). |
| **Is the remote MCP server open to any client?** | Some (Figma) whitelist approved clients only. |
| **What's the value to YARNNN users?** | Prioritization signal. |

### Integration Approach Decision Tree

```
Platform has official remote MCP with OAuth?
  ├─ YES → Connect as remote MCP client (best option)
  │         Gateway acts as MCP client → remote server
  │
  └─ NO → Platform has REST API + our OAuth tokens work?
            ├─ YES → Direct API client (Gmail/Calendar pattern)
            │
            └─ NO → Open-source MCP server accepts OAuth tokens?
                      ├─ YES → Run in MCP Gateway (Slack pattern)
                      └─ NO → Skip or fork (not worth it early on)
```

---

## Current Stack (Reference)

| Platform | Approach | Auth | Status |
|----------|----------|------|--------|
| **Slack** | MCP Gateway (local server) | Bot token from OAuth | ✅ Working |
| **Notion** | MCP Gateway → **needs migration** | OAuth token (incompatible with local MCP server) | ❌ Broken — migrate to remote MCP or direct API |
| **Gmail** | Direct REST API | OAuth | ✅ Working |
| **Calendar** | Direct REST API | OAuth | ✅ Working |

---

## Tier 1: High-Value Platforms to Research

### Linear

**Value for YARNNN**: High. Engineering teams are core users. Push deliverables as issues, pull project context for recurring reports.

| Dimension | Finding |
|-----------|---------|
| Official remote MCP | ✅ `https://mcp.linear.app/mcp` — hosted by Linear |
| OAuth support | ✅ OAuth 2.1 with dynamic client registration (MCP spec compliant) |
| Open-source MCP | Deprecated (`jerhadf/linear-mcp-server`). Linear recommends their remote server. |
| REST API | ✅ GraphQL API, well-documented |
| Client restrictions | ❌ None apparent — open to any MCP client |
| Transport | Streamable HTTP + SSE |

**Recommended approach**: Remote MCP client. Linear is the gold standard — official remote server, OAuth, no client restrictions. This is the model we want all platforms to follow.

**Integration value**:
- Pull: Sprint status, issue summaries, team workload → feed into recurring deliverables
- Push: Create issues from deliverable outputs, post updates to projects

---

### GitHub

**Value for YARNNN**: Medium-high. Developer-focused users. Pull repo activity, PR summaries, issue context for engineering reports.

| Dimension | Finding |
|-----------|---------|
| Official remote MCP | ✅ `https://api.githubcopilot.com/mcp/` — hosted by GitHub |
| OAuth support | ✅ OAuth (one-click) + PAT fallback |
| Open-source MCP | ✅ `github/github-mcp-server` — can run locally with PAT |
| REST API | ✅ Excellent REST + GraphQL APIs |
| Client restrictions | Requires Copilot for some tools, but MCP server itself is open |
| Transport | Streamable HTTP |

**Recommended approach**: Remote MCP client (for OAuth) or Direct API (simpler, more control). GitHub's API is so well-documented that direct API might actually be easier than MCP for our specific use cases.

**Integration value**:
- Pull: PR summaries, commit activity, issue status → engineering standup reports
- Push: Create issues, post comments from deliverable outputs

---

### Figma

**Value for YARNNN**: Medium. Design teams. Pull design context for handoff docs, component inventories.

| Dimension | Finding |
|-----------|---------|
| Official remote MCP | ✅ `https://mcp.figma.com/mcp` — hosted by Figma |
| OAuth support | ✅ OAuth, but... |
| Open-source MCP | Desktop MCP server (requires Figma desktop app running) |
| REST API | ✅ Figma REST API with OAuth + PAT |
| Client restrictions | ⚠️ **YES — whitelisted clients only.** Dynamic client registration returns 403 for unapproved clients. Beta access via application form. |
| Transport | Streamable HTTP |

**Recommended approach**: **Wait.** Figma's remote MCP is restricted to approved clients (Claude, Cursor, VS Code, etc.). YARNNN would need to apply and get approved, which is uncertain. Direct REST API is the reliable fallback, but Figma's value for recurring deliverables is lower priority.

**Integration value**:
- Pull: Design specs, component data, variable definitions → design handoff docs
- Push: Limited (Figma is primarily read-only for integrations)
- Reality check: Most Figma MCP usage is code-generation focused, less relevant for YARNNN's deliverable automation

---

## Tier 2: Worth Watching

### Asana

| Dimension | Finding |
|-----------|---------|
| Official remote MCP | ✅ `https://mcp.asana.com/sse` |
| OAuth support | Likely (remote hosted servers typically support OAuth) |
| REST API | ✅ Well-documented |

**Value**: Project management context for deliverables. Similar use case to Linear but for non-engineering teams.

### Jira

| Dimension | Finding |
|-----------|---------|
| Official remote MCP | ❓ No official Atlassian-hosted MCP server found yet |
| Open-source MCP | Several community servers, PAT-based |
| REST API | ✅ Atlassian REST API with OAuth 2.0 |

**Value**: Enterprise engineering teams. Large market but Jira's API is complex. Direct API probably best approach.

### Google Drive / Docs

| Dimension | Finding |
|-----------|---------|
| Official remote MCP | ❌ No Google-hosted MCP server |
| Open-source MCP | Community servers exist |
| REST API | ✅ Google APIs (same OAuth we already have) |

**Value**: High. We already have Google OAuth. Adding Drive/Docs read access would let YARNNN pull context from existing docs for deliverable generation. Minimal incremental auth work since we already have Google OAuth.

**Recommended approach**: Direct API (extend existing `GoogleAPIClient`). Easiest expansion since auth is already done.

### HubSpot

| Dimension | Finding |
|-----------|---------|
| Official remote MCP | ❓ TBD |
| REST API | ✅ Well-documented REST API with OAuth |

**Value**: Sales/marketing teams. CRM data for recurring reports (pipeline updates, deal summaries). High value if YARNNN targets GTM teams.

---

## Tier 3: Interesting but Deprioritized

### ChatGPT / OpenAI

**Nuance**: OpenAI is an LLM provider, not a data platform. Integration would be about:
- Using OpenAI models as an alternative to Claude for generation (already supported)
- Accessing ChatGPT conversation history (no API for this)
- No MCP server concept applies here

**Verdict**: Not an integration target. It's a model provider, not a data source.

### Claude AI / Anthropic

**Nuance**: Similar to ChatGPT — Claude is our primary LLM, not a data source to integrate with. Anthropic's MCP connectors (Notion, Slack, etc.) are for Claude's own use, not for third-party platforms to consume.

**Verdict**: Not an integration target. We already use Claude as our generation engine.

### Microsoft Teams / Outlook

| Dimension | Finding |
|-----------|---------|
| REST API | ✅ Microsoft Graph API with OAuth 2.0 |
| MCP | Community servers exist |

**Value**: Enterprise market. Would be important if targeting enterprise customers. Complex OAuth (Azure AD).

---

## Architecture Implications

### Gateway Evolution

Our MCP Gateway currently only spawns local MCP subprocesses (stdio transport). To support remote MCP servers like Linear and Notion's hosted MCP, the gateway needs to evolve:

```
Current:  Gateway → spawns local process → stdio MCP
Future:   Gateway → HTTP client → remote MCP server (OAuth)
          Gateway → spawns local process → stdio MCP (Slack)
          API     → direct REST calls (Gmail, Calendar, maybe GitHub)
```

The gateway should support both connection modes:
1. **Local subprocess** (stdio) — for MCP servers that require it (Slack)
2. **Remote HTTP client** (streamable HTTP / SSE) — for hosted MCP servers (Linear, Notion remote, GitHub)

### Auth Model Matrix

| Auth Model | Examples | YARNNN Compatibility |
|------------|----------|---------------------|
| Remote MCP + OAuth 2.1 + dynamic client registration | Linear | ✅ Best case — fully compatible |
| Remote MCP + OAuth but whitelisted clients | Figma | ⚠️ Requires approval |
| Local MCP + static API key / internal token | Notion open-source, old Linear | ❌ Not compatible with multi-tenant |
| Local MCP + bot token from OAuth | Slack | ✅ Works (current approach) |
| Direct REST API + OAuth | Gmail, Calendar, GitHub | ✅ Always works |

### Priority Order for New Integrations

Based on value × feasibility:

1. **Google Drive/Docs** — Lowest friction (reuse existing Google OAuth), high pull value
2. **Linear** — Perfect MCP story (remote, OAuth, no restrictions), high value for eng teams
3. **GitHub** — Great API, flexible approach options, developer audience
4. **Asana** — Remote MCP available, PM team expansion
5. **Figma** — Wait for client restrictions to lift
6. **Jira** — Direct API only, complex but large enterprise market

---

## Open Questions

- [ ] Should the MCP Gateway evolve to support remote MCP, or should remote MCP connections live in the Python API directly?
- [ ] For platforms with both remote MCP and REST API (GitHub), which approach gives us more control and better DX?
- [ ] How do we handle MCP server versioning? (Notion v2.0.0 broke tool names)
- [ ] Should we build an abstraction layer that normalizes across MCP and direct API, or keep them separate?
- [ ] What's the minimum viable "pull" integration? (Read-only context fetching for deliverable generation)

---

## References

- [MCP Specification — Authorization](https://spec.modelcontextprotocol.io/specification/2024-11-05/security/)
- [Linear MCP docs](https://linear.app/docs/mcp)
- [Notion MCP Supported Tools](https://developers.notion.com/docs/mcp-supported-tools)
- [Figma MCP Server Guide](https://developers.figma.com/docs/figma-mcp-server/)
- [GitHub MCP Server](https://github.com/github/github-mcp-server)
- [mcp-remote](https://github.com/geelen/mcp-remote) — bridge for clients that don't support remote MCP natively

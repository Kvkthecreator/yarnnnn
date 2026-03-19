# YARNNN Competitive Landscape Analysis

**March 2026 — Supplemental to IR Deck**
**Kevin Kim · kvkthecreator@gmail.com · yarnnn.com**

---

## Market Context

The agentic AI market has entered its acceleration phase. In 2025, agentic AI companies raised $5.99B across 213 rounds (up from $4.6B across 232 rounds in 2024). In Q4 2025/Q1 2026, the average round size for leading agentic AI startups hit $155M — nearly double the $82M average from H1 2025.

As of March 2026, there are 1,041 active companies in the agentic AI sector, with 530 having received funding. The US alone has attracted $13.8B in total agentic AI investment. Microsoft is calling 2026 "the year of the agent." The thesis that work shifts from human to agents is consensus. The question: who owns the application layer for knowledge work?

YARNNN's position: cross-platform knowledge accumulation for recurring autonomous output. No competitor occupies this specific intersection.

---

## Category 1: LLM Providers / Big Players

These are platform companies building AI into their existing ecosystems. Massive distribution, massive resources, fundamentally different business model than YARNNN.

### OpenAI / ChatGPT

**Status:** Dominant consumer AI. GPT-5.4 shipped March 2026 with autonomous workflow execution and 1M token context window. ChatGPT-6 planned mid-to-late 2026 with persistent memory and agentic autonomy. Estimated 300M+ weekly active users.

**Memory capabilities:** As of April 2025, ChatGPT references all past conversations for tailored responses. Plus/Pro users get long-term understanding. Free users get lightweight short-term continuity.

**What they have:** Unmatched distribution. Best-in-class models. Growing conversational memory. GPT-5.4 can execute multi-step tasks with 1M token context.

**What they lack:** Memory is conversational (remembers what you said), not operational (understands your work patterns). No cross-platform perception pipeline — ChatGPT doesn't connect to your Slack, Gmail, Notion as persistent data sources. No recurring scheduled agents. No agent workforce management (Composer equivalent). No feedback distillation from edits. Each work context starts fresh. No agent identity or tenure.

**Why they won't build this:** OpenAI is a model company optimizing for API revenue and general-purpose capability. Building a vertical SaaS for knowledge worker automation would be structurally at odds with their platform business model. They'll enable it via APIs (which YARNNN uses), not build the application layer.

### Anthropic / Claude

**Status:** Claude Cowork launched as desktop agent (Mac initially, Windows Feb 2026). Claude Code is the CLI coding agent. Pro subscription $20/mo. Sonnet 4.5 is the current frontier model.

**Key capabilities:** Local filesystem access. Scheduled tasks via /schedule. SKILL.md pattern for capability injection. MCP server ecosystem. Cowork mode provides sandboxed Linux VM for file operations.

**What they have:** Genuinely excellent agentic architecture. Claude Code's SKILL.md + filesystem + tools model is the structural inspiration for YARNNN's output gateway (we acknowledge this explicitly). Scheduled tasks. Growing plugin ecosystem.

**What they lack:** Tasks execute and complete — no persistent agent workforce with identity, memory, and tenure across runs. No cross-platform perception (doesn't connect to Slack + Gmail + Notion as ongoing data sources). No Composer-like autonomous orchestration that manages an agent workforce. No feedback distillation where edits improve future outputs. Each scheduled task is independent — no cross-agent intelligence.

**Why they won't build this:** Anthropic is a safety-focused model company. Claude Code and Cowork extend the model's capability surface, not build vertical SaaS. They'll provide the infrastructure (which YARNNN uses); they won't build the persistent, cross-platform knowledge layer.

**YARNNN's explicit relationship:** YARNNN is "Claude Code online" — same capabilities model (SKILL.md, filesystem, tools) but persistent, autonomous, and cloud-native. This is complementary, not competitive. YARNNN uses Claude's API. If Anthropic builds a marketplace or ecosystem for persistent agent platforms, YARNNN is a natural participant.

### Google Gemini

**Status:** Chrome Auto Browse (Jan 2026) handles multi-step browser tasks. Android task automation on flagship devices. Gemini 3.1 Pro has 1M token context.

**What they have:** Deepest integration with Google ecosystem. Strong models. Android + Chrome as distribution surfaces. Google Workspace AI.

**What they lack:** Platform-locked to Google ecosystem. No cross-platform knowledge accumulation across Slack + non-Google tools. Browser automation is task-oriented, not knowledge-oriented. No persistent agent workforce.

**Why they won't build this:** Google's incentive is to keep users in Google Workspace. A cross-platform agent that synthesizes Slack + Gmail + Notion is structurally misaligned with Google's platform strategy.

### Microsoft Copilot

**Status:** Major 2026 shift from per-command copilot to autonomous agents. M365 E7 bundle ($99/user/mo) combines M365 E5 + Copilot + Agent 365. Copilot Cowork (built with Anthropic) enables cross-app agent execution within M365. Agent 365 provides governance. Global price increases effective July 1, 2026 bundle AI into baseline subscriptions.

**What they have:** Unbeatable enterprise distribution. Deep integration across Office, Teams, Outlook, SharePoint. Agent 365 governance platform. Will be bundled into M365 (no separate purchase). Multi-app workflow execution within Microsoft ecosystem.

**What they lack:** Microsoft ecosystem only. No Slack, no Notion (competitors to Teams). Copilot agents serve the Microsoft graph — blind to everything outside M365. Most knowledge workers use tools across ecosystems. $99/user/mo E7 bundle is enterprise pricing, not individual knowledge worker pricing.

**Why they won't build cross-platform:** Microsoft has no incentive to make Slack or Notion first-class data sources. Their strategy is to replace those tools with Teams/Loop, not compose across them.

---

## Category 2: Agent Startups

These are venture-backed startups building agent platforms. Closest to YARNNN's category, but with fundamentally different architectural bets.

### Genspark ($1.25B valuation)

**Funding:** $275M Series B (Nov 2025). $50M ARR within five months of launch.
**What it is:** AI workspace with Mixture-of-Agents architecture orchestrating 30+ models with 150+ in-house tools. Users state intent, platform delivers finished work.

**Strengths:** Massive funding. Fast growth. Multi-model orchestration. Broad tool ecosystem. Strong at one-shot complex task execution.

**Weakness for YARNNN's market:** Task-oriented, not knowledge-accumulating. Each execution is independent — the 12th Genspark execution doesn't know anything about the first 11. No persistent agent identity. No perception pipeline. No feedback substrate. Users provide full context per task.

**Structural difference:** Genspark is a better prompt-to-output pipeline. YARNNN is a persistent workforce that compounds knowledge. Different architectural bet entirely.

### Lindy AI

**Funding:** Series A (undisclosed, est. ~$30-50M). Starting at $19.99/mo.
**What it is:** No-code agent builder with 5,000+ integrations, computer use capabilities, AI phone agents (Gaia). SOC 2, HIPAA, GDPR compliant.

**Strengths:** Strong integration ecosystem. Clean no-code UX. Computer use skill with web automation. Enterprise compliance. Good for structured, repeatable automation workflows.

**Weakness for YARNNN's market:** Workflow-oriented, not intelligence-oriented. Agents follow predefined workflows — they don't accumulate knowledge, develop seniority, or learn from feedback. Credit-based pricing (1-10 credits per action) punishes complex recurring work. No cross-platform knowledge base. No autonomous workforce management (Composer equivalent).

**Structural difference:** Lindy agents are reliable AI employees that follow instructions. YARNNN agents are developing knowledge workers that get smarter with tenure.

### Relevance AI ($24M Series B)

**Funding:** $24M Series B led by Bessemer Venture Partners with Insight Partners. 40,000 agents created in January 2025 alone.
**What it is:** AI workforce platform specifically for sales and GTM teams. Visual drag-and-drop multi-agent workflows. "Workforce" feature enables no-code multi-agent systems.

**Strengths:** Strong GTM/sales vertical focus. Multi-agent team orchestration. Self-driving workforces that optimize themselves. Event-triggered automation.

**Weakness for YARNNN's market:** Vertically focused on sales/GTM — not general knowledge work. Agents optimize sales processes (lead qualification, prospecting, account research), not recurring knowledge output. No cross-platform knowledge accumulation from Slack + Gmail + Notion. Workflow-driven, not substrate-driven.

**Structural difference:** Relevance AI builds AI sales teams. YARNNN builds an AI knowledge workforce. Different customer, different architecture.

### Dust.tt (Enterprise)

**Funding:** Series A (est. ~$50M). SOC 2 Type II, GDPR compliant.
**What it is:** Custom AI agents connected to company data (Slack, Google Drive, Notion, Confluence, GitHub). Agents run on schedules or webhooks.

**Strengths:** Strong enterprise positioning. Multi-source knowledge connection. Schedule-based agent execution. Good governance model. Solid data source coverage.

**Weakness for YARNNN's market:** Enterprise-first — team workspaces, not individual knowledge workers. Agents are custom-built by users, not auto-created from platform signals. No Composer-like autonomous orchestration. No feedback-to-intelligence loop (agents don't learn from user edits). No seniority progression.

**Structural difference:** Dust asks "what agents do you want to build?" YARNNN answers "here are the agents your work patterns require." Dust is a platform for building agents; YARNNN is a product where agents emerge from use.

**Closest competitor to YARNNN:** Dust is the most structurally similar — multi-source data, scheduled agents, knowledge work focus. The key differentiator is YARNNN's autonomous orchestration (Composer), feedback substrate, and individual-first (not enterprise-first) positioning.

### Zapier Agents

**Funding:** Zapier is profitable, private, estimated $5B+ valuation. 2.2M+ customers.
**What it is:** AI agents within the Zapier automation ecosystem. 7,000+ app integrations. Agents reason, search the web, and decide actions autonomously.

**Strengths:** Massive integration ecosystem (7,000+ apps). Huge existing customer base. Agents can work across entire business ecosystems. Web research capability.

**Weakness for YARNNN's market:** Automation-first, not intelligence-first. Zapier agents automate workflows (when X happens, do Y); they don't accumulate knowledge about your work patterns over weeks/months. No persistent agent identity with memory and preferences. No feedback loop from edits. No knowledge base that deepens with tenure.

**Structural difference:** Zapier automates actions across apps. YARNNN accumulates intelligence across platforms. When Zapier runs the same automation twice, nothing is different. When YARNNN runs the same agent twice, the second run is informed by everything the first run learned.

### Relay.app

**Funding:** Early-stage (undisclosed). Starting at $19/mo.
**What it is:** AI automation platform with human-in-the-loop control. 100+ app integrations. Supports GPT, Claude, and Gemini. AI Agent Builder within workflows.

**Strengths:** Clean UX. Human-in-the-loop approval flows. Multi-model support. Good for teams needing oversight over AI actions.

**Weakness for YARNNN's market:** Workflow automation with AI steps, not autonomous knowledge agents. Agents operate within predefined workflow templates. No knowledge accumulation. No persistent agent identity.

---

## Category 3: Workspace AI / Platform Intelligence

These are existing productivity platforms adding AI capabilities. Massive distribution, platform-locked.

### Notion AI Custom Agents (Feb 2026)

**Status:** Launched February 24, 2026 as "Notion 3.3." Available on Business ($18/user/mo) and Enterprise plans. Credit-based pricing: $10 per 1,000 credits; each agent run uses ~17-33 credits. Free through May 3, 2026.
**What it is:** Fully autonomous agents within Notion workspaces — up to 20 minutes of autonomous work across hundreds of pages. Custom triggers, schedules. MCP integrations with Slack, Figma, Linear, HubSpot.

**Strengths:** Deep integration with Notion ecosystem. 100M+ Notion users. Autonomous execution with schedule/trigger. Cross-tool visibility via MCP. Custom agent builder. Can automate task triaging, standups, status reports.

**Weakness for YARNNN's market:** Notion-anchored — agents reason over Notion's data model as the primary substrate. Can pull from Slack/Figma via MCP but intelligence lives in Notion. No independent perception pipeline across platforms. No feedback distillation from user edits. No agent workforce autonomy (Composer equivalent). Credit-based pricing punishes heavy use.

**Structural difference:** Notion agents make Notion smarter. YARNNN agents make your work smarter regardless of platform. Notion Custom Agents are the best single-workspace AI; YARNNN is the cross-workspace intelligence layer.

### Slack AI / Salesforce Agentforce

**Status:** Slack AI provides channel summaries, thread summaries, search. Agentforce brings autonomous agents to Salesforce. Einstein Copilot across Sales/Service/Marketing clouds.
**What it is:** Platform-native AI within Salesforce ecosystem.

**Strengths:** Deep Slack/Salesforce integration. Enterprise distribution. CRM-aware agents.

**Weakness for YARNNN's market:** Single-platform. Slack AI makes Slack smarter; Agentforce makes Salesforce smarter. Neither composes cross-platform knowledge into independent agent outputs.

### Microsoft Copilot (covered in Category 1)

M365-locked. Most relevant as enterprise competition.

---

## Category 4: Enterprise Knowledge AI

These companies build enterprise knowledge infrastructure — search, Q&A, internal knowledge management.

### Glean ($7.2B valuation)

**Funding:** $150M Series F (June 2025) at $7.2B. Total raised: $620M+. $100M+ ARR. Investors include Sequoia, Kleiner Perkins, Lightspeed, DST Global.
**What it is:** Enterprise AI work assistant. Unified search across company knowledge. Glean Agents platform powering 100M+ agent actions annually, on pace for 1B by year-end 2025.

**Strengths:** Massive enterprise traction. Deep integrations across enterprise tools. Strong security and governance. Search + agents in one platform.

**Weakness for YARNNN's market:** Enterprise-first (team knowledge, not individual knowledge worker output). Glean indexes company knowledge for Q&A and search — it doesn't produce recurring autonomous outputs (digests, briefs, reports). No feedback loop from user edits. Different use case: "find information" vs. "produce recurring deliverables."

**Structural difference:** Glean makes company knowledge searchable. YARNNN makes individual work knowledge actionable through persistent agents.

### Moveworks (Acquired by ServiceNow for $2.85B)

**Status:** Acquired December 2025. $100M+ ARR. 5M employee users in 18 months. Previously raised $300M+ from Tiger Global, Iconiq, Kleiner Perkins.
**What it is:** Enterprise AI agent platform for IT, HR, and employee support.

**Why it matters:** Validates the enterprise agent market at $2.85B exit. Shows that agent platforms with accumulating enterprise context command premium valuations. ServiceNow acquired for agentic AI capability + enterprise customer base.

**Difference from YARNNN:** Moveworks targeted enterprise IT/HR support. YARNNN targets individual knowledge workers with recurring output obligations. Different customer, different use case, but the exit validates the agent platform category.

### Mem.ai ($29.1M total raised)

**Funding:** $23.5M led by OpenAI Startup Fund (2022) at $110M post-money. $29.1M total. Investors include Andreessen Horowitz.
**What it is:** AI-powered personal knowledge assistant / note-taking app. Mem 2.0 (2026) works as a "parallel mind" for complex workflows.

**Strengths:** OpenAI investment signals model-company endorsement. Smart Write / Smart Edit features. Pattern detection across notes.

**Weakness for YARNNN's market:** Note-taking tool with AI features, not an autonomous agent platform. Mem organizes what you put into it; YARNNN perceives your work across platforms without you putting anything in. No scheduled agent runs. No cross-platform perception pipeline. No agent workforce.

**Critical context:** A Medium analysis titled "Mem AI: The $40M Second Brain Failure" suggests execution challenges despite strong funding. Validates the knowledge management pain point but questions the note-taking-first approach.

### Dashworks (Acquired by HubSpot, May 2025)

**Funding:** $14.5M total. Acquired by HubSpot.
**What it was:** AI assistant for enterprise internal knowledge search across tools. NLP-powered unified knowledge base.

**Why it matters:** HubSpot acquiring a knowledge search tool validates that CRM/productivity platforms see value in cross-tool knowledge unification. But acquisition effectively removes Dashworks as an independent competitor.

---

## Category 5: Task/Browser Automation

These tools automate specific workflows — browser actions, scheduling, task management. Different category than YARNNN, but investors sometimes conflate them.

### MultiOn

**Funding:** Undisclosed. Building "Motor Cortex layer for AI."
**What it is:** Autonomous browser agent API. Executes web tasks based on natural language. Supports millions of concurrent agents. Best-in-class web scraping.

**Difference:** Browser automation (transactional tasks: book flights, fill forms). Not knowledge accumulation. Different category entirely.

### Adept AI (Acqui-hired by Amazon, June 2024)

**Status:** Key team hired by Amazon. Remaining company received ~$25M. Previously raised $415M ($350M Series B).
**What it was:** AI agent for software workflow automation. Built ACT models for computer use.

**Why it matters:** $415M raised, acqui-hired — shows the difficulty of building general-purpose agent platforms even with massive funding. Validates that the hard problem isn't building agents, it's building agents that sustainably deliver value. YARNNN's focus on knowledge accumulation (the value compounds) is a direct response to this challenge.

---

## The Positioning Map

|  | Single Platform | Cross-Platform |
|---|---|---|
| **Task Execution (one-shot)** | Notion AI, Slack AI, Copilot | Genspark, Lindy, Zapier, MultiOn |
| **Workflow Automation (repeating)** | Notion Custom Agents | Relay.app, Zapier Agents |
| **Knowledge Search (enterprise)** | Slack AI | Glean, Dashworks (HubSpot) |
| **Knowledge Accumulation (compounding)** | — | **YARNNN** |

The bottom-right quadrant — cross-platform knowledge that accumulates and compounds — is empty except for YARNNN. Every competitor is either single-platform, task-oriented, or enterprise-first. No one builds persistent autonomous agents that accumulate cross-platform work knowledge for individual knowledge workers and improve with tenure.

---

## Funding Landscape Summary

| Company | Category | Valuation | Total Raised | Stage | Status |
|---------|----------|-----------|-------------|-------|--------|
| Glean | Enterprise Knowledge | $7.2B | $620M+ | Series F | Independent |
| Genspark | Agent Platform | $1.25B | ~$300M+ | Series B | Independent |
| Moveworks | Enterprise Agent | $2.85B (exit) | $300M+ | Acquired | ServiceNow |
| Mem.ai | Knowledge Mgmt | $110M (2022) | $29.1M | Series A | Independent |
| Relevance AI | Sales Agent | — | $24M | Series B | Independent |
| Dust.tt | Enterprise Agent | ~$50M est. | Series A | Series A | Independent |
| Lindy | Agent Builder | ~$50M est. | Series A | Series A | Independent |
| Adept AI | Agent Platform | — | $415M | Acqui-hired | Amazon |
| Dashworks | Knowledge Search | — | $14.5M | Acquired | HubSpot |
| **YARNNN** | **Cross-Platform Intelligence** | **$5M (ask)** | **Pre-Seed** | **Pre-Seed** | **Independent** |

**Market signal:** The agentic AI sector attracted $5.99B in 2025 alone. Average late-stage round: $200M. The Moveworks exit ($2.85B) and Glean valuation ($7.2B) confirm that agent platforms with accumulating enterprise context command premium multiples. YARNNN's pre-seed entry at $5M post-money is early enough to build the knowledge accumulation moat before well-funded competitors recognize the quadrant.

---

## Why Competitors Can't Pivot to YARNNN's Position

**Big Players (OpenAI, Anthropic, Google, Microsoft)** are model/platform companies. Building a vertical SaaS for knowledge worker automation is structurally at odds with their business model. They'll build the infrastructure (APIs, models, MCP). YARNNN builds the application layer on top.

**Agent Startups (Genspark, Lindy, Relevance)** are optimized for task execution or specific verticals. Their architectures are stateless per execution (Genspark), workflow-oriented (Lindy), or vertically focused (Relevance AI on sales). Pivoting to knowledge accumulation would require rearchitecting their core product — not just adding features, but changing the fundamental data model.

**Workspace AI (Notion, Slack, Microsoft)** has no incentive to become cross-platform. Their business model is platform engagement. A cross-platform agent layer that reduces dependency on any single tool is antithetical to their strategy.

**Enterprise Knowledge (Glean, Moveworks)** serves enterprise teams, not individual knowledge workers. Different buyer, different price point, different value proposition. Glean makes company knowledge searchable; YARNNN makes individual work knowledge actionable through autonomous agents.

**YARNNN's bet:** The application layer of AI will be won by products that accumulate proprietary user context across platforms — not by platforms that AI-enhance their own walled garden, not by task runners that start fresh every time, and not by enterprise tools that serve IT departments instead of knowledge workers.

---

*Sources: Tracxn, Crunchbase, TechCrunch, PitchBook, company websites and blogs, G2, VentureBeat, CNBC, Fortune, Semafor — March 2026*

*kvkthecreator@gmail.com · yarnnn.com*

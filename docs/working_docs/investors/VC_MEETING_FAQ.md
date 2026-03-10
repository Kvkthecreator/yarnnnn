# VC Meeting FAQ

**Purpose**: Pre-emptive answers to expected investor questions for live meetings.
**Date**: 2026-03-11 (v2 — tightened per a16z memo guidance, added GTM + Vision)
**Source**: IR Deck v19 + VC Answer Bank v3.1 + Agent Platform Architecture doc + founder notes
**How to use**: Prep doc for Thursday meetings. Tight answers for live delivery, "if pressed" for when they dig deeper. At pre-seed, say just enough — don't give them rope to hang you.

---

## 1 · Platform Risk

### Q: Why won't Anthropic / OpenAI / Google just build this?

Every platform cycle follows the same pattern: the platform provider doesn't build the application layer. Google didn't become Salesforce. AWS didn't become Datadog. LLM providers optimize for breadth across all users. We optimize for depth in one user's recurring work — different priorities, different data models, different architecture.

> *If pressed:* Code was the easy application layer — model capability maps directly to output. Work context is the hard case: unstructured, personal, cross-platform, domain-specific. That's where the application layer always emerges.

### Q: What happens when ChatGPT adds better memory and scheduled tasks?

ChatGPT's memory is conversation-scoped — it remembers preferences from past chats. YARNNN's knowledge is platform-scoped — it continuously syncs four work platforms, accumulates what matters, and produces autonomous output. Learning your name is different from knowing which Slack channels have signal for your weekly board report.

> *If pressed:* Scheduled tasks in ChatGPT are prompt-based reminders. YARNNN agents have persistent identity, compounding memory, and learned preferences from your edits. Fundamentally different architecture.

### Q: You're built on Claude's API. What if Anthropic changes pricing or cuts you off?

Model-agnostic by design. Swapping Claude for GPT-4 or Gemini is a configuration change, not a rewrite. Our value is the context layer and accumulated knowledge — none of which lives inside the model.

> *If pressed:* We already use multiple models: Sonnet for generation, Haiku for lightweight review passes. If economics shift, we shift models.

---

## 2 · Moat & Defensibility

### Q: What's your moat? Someone could build the same integrations in a weekend.

The integrations aren't the moat — the accumulated context is. After 90 days, a YARNNN agent knows your clients, metrics, communication style, and editorial preferences. A competitor starting from zero can't replicate that. Switching cost increases with every execution.

> *If pressed:* The 50th run of your weekly status report is incomparably better than the 1st — 50 runs of accumulated memory, learned preferences, retained knowledge. That's a compounding data moat, not a feature moat.

### Q: Isn't this just a wrapper on Claude's API?

No. A wrapper sends a prompt and returns a response. YARNNN is a purpose-built agent platform: four-platform perception, retention-based knowledge accumulation, five execution modes, four-layer intelligence model, orchestrator managing a network of persistent agents. 100+ Architecture Decision Records. Infrastructure, not a skin.

> *If pressed:* That's 6+ months of solo architectural work. The architecture doc is available as a leave-behind.

### Q: What about Notion AI, Glean, Granola — don't they already have work context?

Single-platform context, no autonomous output. Notion AI knows your pages but not your Slack. Glean is enterprise search with no agent layer. YARNNN is the only product that accumulates cross-platform context and uses it for autonomous recurring deliverables.

> *If pressed:* Notion ($11B), Glean ($7.2B), Granola ($250M), Mem.ai ($110M) — all validated demand for AI-powered context. We add the autonomous output layer none of them have.

---

## 3 · Business Model & Traction

### Q: You're pre-revenue. What gives you confidence people will pay?

Three signals. ClawdBot proved explosive demand — 17,830 GitHub stars in 24 hours — but 95% couldn't use it (required VPS, 200+ security leaks). Our beta users have real integrations connected — live Slack, Gmail, Notion data. And our ICP already pays $15–50/month for tools that do far less.

### Q: How do you get to $1M ARR?

$19/month Pro tier, ~4,400 subscribers to $1M. Entry wedge is 5 million solo consultants globally. Path: prove retention with the first 100 users (edit distance decreasing over time), then grow through consultant network effects — one consultant shows a client, the client's team wants their own agents.

> *If pressed:* Early Bird at $9/month lowers conversion barrier during validation. Move to $19 once retention metrics prove compounding value.

### Q: What are your unit economics?

Per-agent execution costs $0.02–$0.08 per run. A Pro user with 5 active weekly agents costs ~$0.50–$1.75/month in LLM spend against $19/month revenue. 90%+ gross margin on compute. Infrastructure is ~$50/month total at current scale.

> *If pressed:* Every LLM price drop from Anthropic, OpenAI, or Google directly improves our margins. We're on the right side of the cost curve.

### Q: $19/month feels low. What's the expansion path?

Intentionally low — prosumer entry point. Expansion: solo consultant → small team (shared agents) → department (20–50 seats, coordinator agents). Enterprise per-seat pricing is a 2027–2028 play. $19/month wins the individual who becomes the internal champion.

---

## 4 · Team & Execution

### Q: Why are you a solo founder?

Not by default — by conviction after trying. Explored cofounders locally and through YC cofounder matching. Candidates either lacked the technical depth or weren't aligned on the vision. I'd rather build solo than split equity with someone who doesn't understand why accumulated context is the moat. Proof is in the output: shipped the entire MVP solo before raising a dollar.

> *If pressed:* I hire painfully slow — bad hires at this stage are existential. The $500K is purpose-built for two hires: senior Tech Lead and GTM Lead. I have candidates identified from my enterprise consulting network. Not hypothetical.

### Q: How do you plan to use the $500K?

Two hires and 18 months of runway. Tech Lead (~$150K) for perception pipeline, agent execution, infrastructure. GTM Lead (~$120K) for consultant wedge — community-led growth, content, direct outreach. Remainder covers infra, LLM spend, operational buffer. No office, no excess overhead.

### Q: What's your founder-market fit?

A decade navigating contexts that don't connect. Deployed CRM for Japan Tobacco in post-military Myanmar — rebuilt every enterprise software assumption from zero. Built GTM systems for cross-border sales. The through-line: systems that should talk to each other but don't, and building the bridge. YARNNN is the product expression of that instinct.

> *If pressed:* Systems thinker from cross-cultural work + deep domain expertise + ability to ship full stack solo. Not a typical pre-seed profile.

### Q: What happens if you can't hire in time?

The product is live. The raise accelerates, it doesn't unblock. Without hires, I do both engineering and GTM myself — slower, not stopped. With hires, we parallelize.

---

## 5 · GTM & Distribution

### Q: How are you acquiring customers?

Three channels. First, community-led: solo consultant communities on Slack, Reddit, and X where the pain is discussed daily. Second, content marketing: showing the compounding effect with real before/after examples — week 1 output vs. week 12 output from the same agent. Third, product-led virality: when a consultant's agent produces a client deliverable, the client sees what's possible.

> *If pressed:* The wedge is narrow by design. Solo consultants have no procurement process — individual purchase decision, same day. CAC should be near-zero through organic channels initially.

### Q: What's your distribution advantage?

The product is its own distribution. Every agent output that reaches a client or stakeholder is a demonstration of the platform. A weekly status report that arrives better than a human wrote it — that's the growth loop. Plus, the MCP server means YARNNN agents are accessible from Claude.ai and other AI surfaces, expanding touchpoints without us building more UI.

---

## 6 · Technical

### Q: Walk me through what happens when an agent runs.

Scheduler checks every 5 minutes. When an agent fires: (1) trigger dispatcher evaluates the mode, (2) execution pipeline assembles the prompt from four intelligence layers, (3) agentic LLM loop with tool use — search, read, web search, (4) output delivered via email/Slack/Notion, (5) output written back to knowledge base as retained content, (6) user edits extracted as learned preferences for next run.

### Q: How does the knowledge accumulation actually compound?

Three mechanisms. Retention model: synced content starts ephemeral, gets marked retained when referenced — knowledge base becomes a curated corpus of what mattered. Agent memory: each execution writes observations to per-agent memory. Feedback loop: user edits become learned preferences injected into next run. The 50th run has 50 executions worth of all three.

### Q: What's the MCP server for?

Lets external AI tools — Claude.ai, Claude Desktop, ChatGPT — access YARNNN's agent network. A user can ask Claude "what did my Slack Digest agent find this week?" without opening our UI. Strategic positioning: as AI fragments across surfaces, the value layer is the persistent context underneath.

---

## 7 · Market & Timing

### Q: Why solo consultants? That's a niche market.

It's a wedge, not the destination. Clearest pain, shortest sales cycle (no procurement), highest willingness to pay. 5 million globally, $1.14B SAM at our pricing.

> *If pressed:* Notion started with individuals, now sells to enterprises. Superhuman started with power users, now has team plans. The wedge earns the right to expand.

### Q: Why now?

LLM capabilities crossed the agentic threshold — tool use, long context, reliable instruction following. Market demand validated explosively by ClawdBot. Every platform cycle's application layer forms 3–5 years after platform maturity. LLMs are 3 years in. The window is open.

### Q: Isn't the ClawdBot signal borrowed credibility?

It's market validation. ClawdBot proved tens of thousands want personalized, persistent AI — but 95% couldn't use it. We're not ClawdBot. We're the productized version of the demand they proved. The signal is theirs. The product is ours.

---

## 8 · Vision

### Q: What does YARNNN look like in 5 years?

The operating system for knowledge work. Today, one user with a handful of agents. In 2–3 years, teams where agents coordinate across departments — a coordinator agent that watches the sales pipeline and auto-triggers client deliverables, meeting prep, and follow-up chains. In 5 years, the context layer that every AI surface plugs into via MCP — the persistent understanding of how a company actually works.

> *If pressed:* The wedge is consultants. The category is agent infrastructure for recurring knowledge work. Owning the context layer gives us the right to expand the product surface indefinitely — same pattern as Notion going from docs to databases to projects to AI.

### Q: Is this a feature or a company?

It's a company. Features get absorbed. Companies own data moats. Every YARNNN agent accumulates context that no platform provider has — the specific intersection of a user's Slack, email, docs, and calendar, refined by months of feedback. That accumulated intelligence doesn't exist anywhere else. It's not a feature you can bolt on.

---

*Prepared for pre-seed investor meetings, March 2026. For the full pitch, see the IR Deck. For technical architecture, see the Agent Platform Architecture document.*

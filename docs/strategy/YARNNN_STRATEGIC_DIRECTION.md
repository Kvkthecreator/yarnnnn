# YARNNN Strategic Direction: Recurring Deliverables as Wedge to A2A Infrastructure

**Date:** February 1, 2026
**Status:** Committed direction — ready for implementation
**Companion Document:** `YARNNN_CLAUDE_CODE_BUILD_BRIEF.md` (implementation request)

---

## 1. Strategic Arc — How We Got Here

### The Starting Problem

Kevin, YARNNN's solo founder, noticed he doesn't use his own product. Claude's native capabilities (memory, file handling, integrations, Chrome extension) have been closing the gap on what YARNNN was designed to provide. This trend is structural and accelerating — foundation model providers will continue absorbing peripheral capabilities.

### The Deeper Observation

Kevin's own work behavior has shifted: 9-10 out of 10 times, he now wants all work to go "through AI." He doesn't want to touch the work — he wants to ask for it to be done. If this experience is representative of a broader shift, the implications for YARNNN are significant.

### Three Layers of AI Product Strategy

Through discourse, we identified three strategic layers with different competitive dynamics:

**Layer 1 — Tools for humans to use AI better.** This is what most AI wrappers do. It's a race to the bottom as foundation models improve. YARNNN positioned here would lose.

**Layer 2 — Tools that act on behalf of humans through AI.** YARNNN v2's "scheduled agents" positioning. Better than Layer 1, but still tethered to humans as primary orchestrator. Vulnerable to incumbents adding similar features.

**Layer 3 — Infrastructure for AI-to-AI coordination.** The frontier. The missing context substrate that lets agents understand what other agents have done, what the state of a project is, what needs to happen next. No one does this well yet. YARNNN's architectural DNA is well-suited here.

### The Timing Problem

The A2A future is probably real, but timing matters. The multi-agent coordination problem becomes acute only when specialization fragments the AI landscape enough that no single provider covers everything. That's likely 18-36 months out.

### The Resolution — The Cursor Sequencing Model

Cursor didn't launch as "the coordination layer for coding agents." It launched as something useful today (better code editor with AI) and evolved toward the bigger vision (autonomous background agents). YARNNN needs the same sequencing.

**The critical question became: What is YARNNN's equivalent of "useful today, positioned for A2A tomorrow"?**

---

## 2. The Answer — Recurring Deliverables

### Why Recurring Deliverables

Most knowledge work has ambiguous quality signals, subjective outputs, and long feedback cycles. That's why no "Cursor for marketing" exists despite many attempts. But there is one knowledge work pattern with tight, measurable feedback: **recurring deliverables with known recipients.**

A consultant sending a weekly client status update has a clear loop: context goes in, deliverable comes out, client responds (or doesn't complain). The output format is known. The quality bar is "does the client accept it without asking for revisions." The feedback cycle is weekly, not quarterly. And critically — it's work people hate doing but can't stop doing.

### Why This Is the Bridge to A2A

A recurring deliverable is already a multi-agent coordination problem. You need a context-gathering step (pull updates from relevant sources), a synthesis step (turn raw context into structured deliverable), and a formatting/delivery step. That's a 2-3 step agent chain — small enough to build and validate quickly but structurally identical to the A2A pattern.

### The Flywheel

Each delivery cycle adds to the project's context. The 10th weekly report is better than the 1st because YARNNN has 9 weeks of project history. This is the moat — it gets better with use, which is the moat against someone just doing this manually in Claude.

### The Product Thesis (Stated Plainly)

YARNNN is the system that produces and delivers your recurring work — the reports, updates, briefs, and summaries you owe to other people on a schedule. It gets better every cycle because it accumulates context. Under the hood, it's a multi-agent coordination layer that will become infrastructure for a larger A2A future, but users never need to know or care about that.

---

## 3. Design Decisions (Resolved)

### Decision 1: Deliverable as Versioned Template

The Deliverable is a **versioned template**, not a living document that overwrites. Each execution produces a new version, preserving clear footprints of user feedback, accumulated context, and the output derived for each specific sequence/turn.

**Rationale:** Versioning provides auditability, enables comparison across deliveries (was version 8 better than version 5?), supports the feedback engine (what changed between what YARNNN produced and what the user actually sent?), and preserves provenance — critical for the eventual A2A layer where multiple agents contribute across versions.

### Decision 2: Feedback Capture — Heavy Investment, Core Feature

The feedback mechanism is not a nice-to-have — it IS the core product engine. When a user edits a staged deliverable before sending, the system should capture and categorize edits at the medium-to-heavy level:

- **Additions** = context gaps (YARNNN missed something)
- **Deletions** = irrelevance signals (YARNNN included something unnecessary)
- **Restructuring** = format preference signals
- **Rewrites** = tone/voice/framing signals

This categorized feedback feeds back into the synthesis agent's instructions for the next cycle. The deliverable converges toward what the user would have written themselves over time.

**Measurable quality metric:** Edit distance between YARNNN's output and what the user actually sends. This decreases over time. Eventually marketable: "By week 4, users edit less than 10% of the deliverable."

### Decision 3: Cold Start — Front-Load Onboarding

Strongly encourage uploading past examples during onboarding. "Show me your last 3 reports and I'll learn your style." If users provide examples, the first output can be surprisingly good via style transfer plus context injection.

Fallback: if no examples available, make the first deliverable explicitly collaborative — a chat-driven refinement process where the TP walks the user through improving the first draft, and that refinement process becomes initial context.

**General principle:** Willing to risk front-loading (asking for more rather than less upfront) to avoid a disappointing cold start that loses the user.

### Decision 4: Delivery Mechanism — Staged Review, Phase Automated Later

Initial build: staged review only. "Your deliverable is ready for review" with copy/export. User sends via their own channels. Email sending infrastructure already exists in the system and can serve as a notification/staging mechanism.

**Rationale:** Staging forces the user to look at the deliverable, which means they'll edit it, which means you get feedback signal. Also — if the core deliverable quality is strong and trustable, users won't mind copy-pasting or resharing to their existing platforms. It's the work that counts, not the delivery plumbing.

Automated direct delivery (email, Slack, etc.) is a Phase 2 feature once trust is established and the feedback loop has sufficient data.

### Decision 5: TP Integration — Folded Into Deliverable Refinement

The Thinking Partner chat interface is preserved but repositioned. It's not the entry point or primary product surface anymore. Instead, it's the mechanism for refining deliverables during the collaborative cold-start flow and for ongoing adjustments ("for next week's report, emphasize the budget section more").

---

## 4. Architecture Alignment — What the Codebase Assessment Confirmed

Claude Code assessed the existing YARNNN repo (github.com/Kvkthecreator/yarnnnn) and found:

### Strengths (Preserve)
- **Context assembly pipeline (9/10)** — `load_context_for_work()` assembles ContextBundle with importance ranking, scoping, tagging. This is the competitive core. It's what makes the 10th deliverable better than the 1st.
- **Agent architecture** — Clean BaseAgent interface, factory pattern, modular tool definitions. Extensible for pipeline stages.
- **Work execution pipeline** — Timeout handling, error capture, status tracking, retry logic. Robust.
- **Scheduling infrastructure** — Cron-based scheduling exists for recurring work.
- **Email infrastructure** — Already working in the system.

### Gaps (Build)
- **No work chaining** — Each work ticket is independent. Need `depends_on_work_id` for pipeline execution.
- **No output-to-memory conversion** — Agent outputs don't feed back into the context graph.
- **No MCP server** — Tool infrastructure is MCP-adjacent but no actual MCP implementation.
- **No external write path** — APIs require user auth; need service-to-service auth for agent writes.
- **No event-based triggers** — Scheduler is time-based only; no "when work X completes, run work Y."

### Overall Alignment Score: 6.5/10
The critical finding: gaps are **additive features, not architectural rewrites**. The foundation supports this direction.

---

## 5. Positioning and Naming

### Current Positioning (Retiring)
"Build context. Schedule agents. Get work delivered." — Too abstract. Sells infrastructure, not outcomes.

### New Positioning Direction
The product sells the outcome: recurring work that improves over time.

**Core message:** "Your recurring deliverables, produced and improving every cycle. Set up once, refine over time, never start from scratch again."

**Supporting messages:**
- "The reports, updates, and briefs you owe people — handled."
- "Gets better every cycle because it remembers everything."
- "Your 10th delivery is dramatically better than your 1st."

**Target user (sharpened):** Anyone who owes someone a recurring deliverable and hates producing it from scratch every time. Initially: agency owners, consultants, founders with investor/client reporting obligations.

**What YARNNN is NOT:** Another AI chat interface. Another prompt wrapper. Another "AI assistant." It's the system that does the work you owe other people, on schedule, and gets better at it over time.

---

## 6. Competitive Moat Analysis

### Why This Is Defensible

**The feedback flywheel:** Each edit cycle makes the next deliverable better. A new competitor starting from scratch has no accumulated context or learned preferences. Switching costs increase with every delivery cycle.

**Context accumulation as byproduct:** Users don't need to "build their knowledge graph." Context accumulates naturally through the deliverable production process — uploaded examples, gathered sources, edit feedback. This is the Cursor pattern: value comes from doing the work, not from configuration.

**The A2A option value:** The chained agent pipeline, shared context ledger, and MCP integration are architectural assets that unlock the larger A2A play when the market is ready. Competitors building simple report generators won't have this infrastructure.

### Where This Is Vulnerable

**Quality ceiling:** If the deliverables aren't good enough to trust, the feedback loop never starts. First-delivery quality is critical.

**Incumbent risk:** If Anthropic, OpenAI, or Google add native "recurring scheduled outputs" to their platforms, the wrapper value disappears. The defense is that accumulated context and learned preferences don't transfer.

**Narrow wedge risk:** "Recurring deliverables" is specific enough to validate but might be too narrow to sustain a business. The A2A expansion path is the answer to this, but it's deferred.

---

## 7. Open Questions for Ongoing Validation

1. **Who hates producing recurring deliverables the most?** Kevin's 10+ years of go-to-market experience should inform which deliverable type to prioritize. Weekly client status reports? Monthly investor updates? Competitive briefs?

2. **Will 5 people say "I want that" when you describe this product?** This conversation hasn't been validated with potential users yet. The strategic logic is sound, but customer pull hasn't been confirmed.

3. **What's the pricing model?** Per-deliverable? Per-project? Subscription with deliverable limits? This affects how the value is framed.

4. **When does the A2A positioning go public?** For now, the A2A layer is architectural advantage, not marketing message. When does that change?

---

*This document captures the strategic direction as of February 1, 2026. It should be updated as customer validation provides new signals. The companion implementation brief (`YARNNN_CLAUDE_CODE_BUILD_BRIEF.md`) translates this strategy into technical execution guidance for Claude Code.*

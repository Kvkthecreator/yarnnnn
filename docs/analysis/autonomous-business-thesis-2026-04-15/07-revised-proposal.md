# Revised Proposal — The Forward Path

> **Date**: 2026-04-15
> **Parent**: [README.md](README.md)
> **Status**: Proposal for founder review — captures the strategic direction emerging from the full audit + founder challenge

---

## The One-Sentence Reframe

**YARNNN is infrastructure for running autonomous information businesses — powered by a recursive agent workforce that accumulates domain expertise and gets better every cycle.**

Architecture = recursive agent workforce with shared filesystem coordination.
Service model = run your information business with AI agents.
Moat = accumulated domain expertise that makes output quality compound over time.
Measurement = revenue.

---

## The ICP: Business-Ambitious Builder

### Who they are

Individuals who want to build an information business but lack the team to sustain one. They have domain knowledge, editorial direction, and ambition. They lack production capacity: researchers, writers, analysts, trackers.

They're the same psychographic as Lovable/Bolt/v0 users — ambitious individuals who use AI to create capability they couldn't otherwise access. The difference: Lovable enables one-time software creation. YARNNN enables ongoing information business operation.

### Where to find them

| Channel | Relevance |
|---------|-----------|
| Indie Hackers | Building businesses, comparing tools, seeking leverage |
| X/Twitter (build-in-public) | Newsletter founders, content creators, side-project builders |
| ProductHunt | Early adopter ICP — will try tools that promise capability leverage |
| Newsletter communities | Beehiiv community, Substack community, Newsletter Twitter |
| Lovable/Bolt adjacent | Same psychographic, different output category |
| Reddit (r/entrepreneur, r/SideProject, r/Newsletters) | Active builders sharing approaches |

### Why the automation paradox doesn't apply

They're not automating existing work with existing stakes. They're creating new work that agents make possible. No existing clients to protect. No reputation to risk. Error cost is "subscriber doesn't convert" not "client fires me." They can iterate publicly because they're building something new.

---

## The Service Model

### What the user gets

1. **A pre-built team** — Researcher, Analyst, Writer, Tracker, Designer, Thinking Partner. Ready at signup.
2. **Accumulated domain expertise** — Agents accumulate knowledge in the user's niche across cycles. Month 6 output is structurally better than month 1.
3. **Autonomous production** — Tasks run on schedule. Newsletter issues, intelligence briefs, signal digests produced and delivered without manual intervention.
4. **Business operations intelligence** — Tracker agent monitors subscriber behavior, content performance, competitive landscape. Analyst synthesizes. TP recommends strategic direction.
5. **Delivery infrastructure** — Resend for email, Lemon Squeezy for billing (user's own account), exports for cross-posting.

### What the user does

- **Set direction**: What niche, what audience, what format, what editorial standards
- **Review and steer**: Read agent output, provide feedback, adjust direction
- **Build audience**: Distribution is the user's job — YARNNN handles production, the builder handles growth
- **Scale**: Add tasks, expand domain coverage, increase cadence as the business grows

### What agents do

- **Research**: Web search, source monitoring, entity tracking across the niche
- **Analyze**: Pattern detection, trend synthesis, cross-source correlation
- **Write**: Editorial content, intelligence briefs, signal digests, formatted for delivery
- **Track**: Subscriber metrics (via Lemon Squeezy), content performance, competitive landscape
- **Design**: Charts, visualizations, assets for rich output
- **Orchestrate (TP)**: Coordinate multi-agent work, recommend strategic adjustments, manage task lifecycle

---

## The Moat Story

### For users (service model language)

"Your agents accumulate domain expertise in your niche — competitive intelligence, audience understanding, editorial patterns. After 6 months, your information product is better than anything a fresh start could produce. Switch to ChatGPT + manual workflow and watch the quality regress. The expertise is in your workspace, and it doesn't port."

### For VCs (architecture language)

"The recursive perception substrate creates structural output quality improvement over time. Revenue metrics prove the moat is load-bearing. Subscriber retention correlates with accumulated workspace depth. Switching causes quality regression that directly impacts revenue — the strongest possible switching cost because it's measured in money, not sentiment."

### The measurement plan

Track these metrics in the reference implementation:

| Metric | What it proves |
|--------|---------------|
| Output quality month 1 vs. month 6 | Accumulation advantage is real |
| Subscriber retention rate | Accumulated context produces output worth paying for |
| Revenue growth trajectory | The business-ambitious builder ICP is real |
| Quality regression on fresh-context test | The moat is load-bearing |

---

## Build Sequence

### Phase 0: Reference Implementation (Now → +60 days)

Kevin builds and runs one YARNNN-powered information product. This is not a demo — it's a real business:

1. **Choose the niche.** Needs to be a domain Kevin has authority in. Candidates: AI agent landscape tracking, competitive intelligence in the AI tools market, autonomous systems market intelligence.

2. **Run with existing architecture.** No Lemon Squeezy integration needed yet. Use existing task types, context domains, and delivery infrastructure. Manual Lemon Squeezy setup for monetization. Manual cross-posting for distribution.

3. **Measure explicitly.** Track output quality trajectory, subscriber growth, retention, revenue. This data becomes Beat 2 proof and Beat 5 moat evidence.

4. **Document the process.** "Building an autonomous information business, week by week" becomes the content marketing engine. Build-in-public content that demonstrates the product while building the audience.

**Success criteria**: After 60 days, the reference implementation has subscribers, measurable quality improvement, and a revenue trajectory that validates the thesis.

### Phase 1: Lemon Squeezy Integration (+60 days)

If Phase 0 validates:

- Phase 1a: Read-only integration (~6 hours) — API client, platform tools, tracker agent monitors revenue
- Phase 1b: Webhook-driven subscriber management (~6 hours) — subscriber events → workspace updates, delivery targeting
- Phase 1c: Agent-driven business operations (~5 hours) — checkout URL generation, product management, campaign tools

Total: ~17 hours (see [05-lemon-squeezy-technical.md](05-lemon-squeezy-technical.md) for detailed breakdown).

### Phase 2: Platform Generalization (+90 days)

Formalize the information business workflow as a first-class YARNNN capability:

- New task types: `subscriber-digest` (accumulates_context), `revenue-report` (produces_deliverable), `audience-analysis` (produces_deliverable)
- Onboarding flow variant: "Start an information business" as an entry path alongside "Connect your work tools"
- Template library: pre-configured task sets for common information business types (newsletter, intelligence product, signal tracker)

### Phase 3: Positioning Update (+90 days, parallel with Phase 2)

If the reference implementation and early users validate:

- ESSENCE.md v12.0 — service model language
- NARRATIVE.md — add service model narrative mode (Mode B), update Beat 3 demo, update Beat 6 ICP
- GTM_POSITIONING.md v4.0 — business-ambitious builder ICP, new value prop, new channels
- Landing page redesign — service model narrative (Beat sequence B)
- Content strategy pivot — build-in-public + intelligence product showcase

---

## The Narrative Bridge

The tightest version of the full story, spanning both audiences:

> "AI tools are extraordinarily good at general intelligence. Nobody is building *your specific intelligence*. YARNNN gives you a team of AI agents that accumulate domain expertise in your niche and run your information business — research, write, track, deliver, all on schedule. Every cycle, the output improves because agents are reading what previous cycles produced. You set the direction. They run the rest. After 6 months, the accumulated intelligence is irreplaceable — and your revenue proves it."

This contains:
- The platform-cycle argument ("nobody is building your specific intelligence")
- The service model ("run your information business")
- The architecture ("agents reading what previous cycles produced")
- The moat ("irreplaceable")
- The measurement ("revenue proves it")
- The ICP's posture ("you set the direction")

---

## What This Resolves

| Tension | Resolution |
|---------|-----------|
| Capability ambiguity ("what does YARNNN do?") | "Run your information business with AI agents" — immediately concrete |
| Trust deficit ("will it actually work?") | Revenue is the proof. "Our reference implementation has X subscribers at Y MRR" |
| ICP confusion (3 competing profiles) | Business-ambitious builder — findable, reachable, no automation paradox |
| Moat invisibility (filesystem legibility problem) | Revenue makes the moat measurable without users needing to browse workspace files |
| Architecture vs. service model conflation | Architecture stays in FOUNDATIONS.md + SERVICE-MODEL.md. Service model leads in ESSENCE.md + NARRATIVE.md + GTM |
| Founder doesn't use own product | Kevin IS the reference implementation ICP — running an information business on YARNNN |
| "Use case vs. identity" stalemate | "Agent OS" is architecture (invisible). "Autonomous information business infrastructure" is service model (visible). Both are true. |

---

## What Remains Unresolved

1. **Reference implementation niche selection.** Needs Kevin's judgment — which domain has the right combination of his authority, market demand, and demonstration value.

2. **Quality floor validation.** Can accumulated context produce output that paying subscribers will sustain subscriptions for? This is empirically testable through the reference implementation but unknown today.

3. **Distribution strategy.** YARNNN handles production; the builder handles growth. For Kevin's reference implementation, the content marketing engine (build-in-public) IS the distribution. For future users, distribution is their problem. Is that acceptable, or does YARNNN need to help with distribution?

4. **SAM resizing.** The business-ambitious builder ICP needs market sizing. "People who want to build information businesses with AI" is a growing market but unsized. The Lovable parallel suggests the market is large (Lovable has thousands of users), but YARNNN's niche within it (information businesses, not software) is narrower.

5. **Pricing evolution.** $19/mo is the current Pro price. If users are running businesses that generate revenue on YARNNN, the pricing model may need to evolve — revenue share, usage-based, or higher flat rate. This is a good problem to have but needs thinking before it becomes urgent.

---

## Decision Requested

This proposal recommends:

1. **Accept the service model reframe** — YARNNN's product identity becomes "infrastructure for autonomous information businesses" while the architecture identity ("recursive agent workforce") stays in technical/VC docs
2. **Accept the business-ambitious builder ICP** — replaces the consultant and intelligence-hungry professional as primary target
3. **Start the reference implementation immediately** — Kevin builds a real information product on YARNNN as Phase 0 validation
4. **Defer Lemon Squeezy integration to post-Phase 0** — validate the thesis manually before automating the last mile
5. **Maintain the architecture narrative for VCs** while developing the service model narrative for users — two narrative modes, one truth

If the direction is confirmed, next steps are: (a) choose the reference implementation niche, (b) set up the manual workflow (YARNNN produces, Kevin handles LS + distribution), (c) begin build-in-public content series.

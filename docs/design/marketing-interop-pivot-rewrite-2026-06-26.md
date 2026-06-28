# Marketing rewrite — the interop-first pivot

> **IMPLEMENTED 2026-06-26 (plain-language voice).** KVK approved a *plainer, Apple-style* voice than the copy drafted in §2–§6 below. The shipped copy lives in the page files and is the source of truth: `web/app/page.tsx`, `web/app/how-it-works/page.tsx`, `web/app/about/page.tsx`, `web/app/pricing/page.tsx`, `web/lib/metadata.ts`. The strategy (§0–§1, §7) is unchanged and still authoritative; the **copy blocks in §2–§6 are the earlier, more technical draft** — kept for the reasoning, superseded by the plain voice in the code. Full typecheck passes. The §7 open flags still apply — see the note at the bottom of this banner.
>
> **Plain-voice translation applied everywhere:** substrate→"your memory" · principal→"you / your team / your tools / your AIs" · trace→"see every change / who changed what" · cross-LLM/MCP→"every AI you use" · steward/Reviewer→"a second set of eyes / a checker (beta)" · git's model kept only as a quiet under-the-hood line on `/about`.
>
> **§7 flags as resolved in this pass:** (1) steward shown as **"in beta"** (not "coming soon") — safe whether or not the agent is gated off; flip to "coming soon" only if you actually gate it off for new users. (2) multi-principal kept light (one belief + a chip). (3) vertical chips **removed** (→ rooms/AIs). (5) receipts count → **377**. The landing beta section has **no CTA button** (no beta-signup route exists yet — add one if you want a waitlist).

**Date:** 2026-06-26
**Status:** Implemented (plain voice). Below is the strategy of record + the original (more technical) draft copy.
**Scope:** Landing (`/`), How it works, About, Pricing (light), metadata/SEO + brand strings + CTA labels.
**Discourse base:** [interop-first-pivot-and-agent-gating](../analysis/interop-first-pivot-and-agent-gating-2026-06-25.md) · [the-three-rung-framework-and-the-multi-principal-wedge](../analysis/the-three-rung-framework-and-the-multi-principal-wedge-2026-06-26.md) · [ADR-373](../adr/ADR-373-multi-principal-workspace-and-the-re-key.md) · [ADR-374](../adr/ADR-374-presentation-ia-substrate-face-and-the-steward-posture.md) · [ADR-375](../adr/ADR-375-phase-1-substrate-for-humans-and-external-agents.md)

**Chosen direction (from KVK, 2026-06-26):** lead with interop; multi-principal secondary; demote the steward to a beta / coming-soon upgrade.

---

## 0. The pivot in one breath

**Old hero (current site):** *agent-first.* "Agents you own produce your work; a judgment seat answers for what ships." The agent is the product; the substrate is plumbing.

**New hero:** *substrate-first / interop-first.* The product is the **attributed, version-controlled, cross-LLM context filesystem** your tools and every model you use share. The `trace` differentiator leads. The judgment seat (the **steward**, → "Freddie") becomes a named **beta upgrade**, not the headline.

The site is already half-pivoted — the pricing page ("free workspace, reachable from any AI you use, pay for what runs") is interop-forward, but the hero and the product/about copy still lead agent-first. This rewrite finishes the move.

---

## 1. The positioning spine (the three rungs)

The framework that replaces the old "git → GitHub → Copilot" pitch (it tested 2/3 wrong against the code) is **ledger / membrane / steward**. Each rung is a different product altitude with a different competitor set. We **lead the wedge at the ledger, land the home at the membrane, tease the steward**.

| Rung | What it is | Surfaces as | Marketing weight | Competes with |
|---|---|---|---|---|
| **Ledger** | Content-addressed, attributed, parent-pointered filesystem — "git minus branches." `trace` shows who contributed each version. | Files + revision/trace (on demand) | **The proof.** The uncopyable property. | storage/memory MCPs — Mem0, Letta, generic MCP filesystems |
| **Membrane** | One substrate reachable by every principal, from every room (Claude, ChatGPT, Slack, agents). | The home / the landing | **The face. Lead here.** | in-room memories — ChatGPT memory, Claude Projects |
| **Steward** | Accountable judgment seat that places, judges, and acts on the commons. | A posture the workspace *enters* — beta | **Tease, dated, gated.** Not a tab. | autonomous-agent products |

### The moat sentence (use verbatim or close)
> A single attributed substrate — every entry signed by its principal, parent-pointered, single-head — served to every room each principal works in.

### The "who we are NOT" sentence (the anti-commoditization line)
> Attribution + parent-pointered revision history + a single enforced write path — git's model, served cross-LLM. Not a memory cache, not an MCP filesystem, not a notes app.

### The multi-principal note (secondary, "and not just you")
A *principal* is any authenticated caller that reaches the substrate — you, your agents, teammates, their agents, platforms, foreign LLMs. "Personal" is the N=1 case. Keep this as a deepening beat, **never the headline** — it's heavier to grasp and a weaker cold-start story. Surfaces strongest on `trace`: "which principal — human, agent, platform, or model — contributed each version."

### Voice + guardrails (unchanged from current site)
- Lowercase `yarnnn`. Restrained, no hype, "receipts, not claims."
- **Truth in receipts:** 377 recorded ADRs is real; attribution-at-the-write-path is real; cross-LLM via MCP is real and shipping.
- **Steward = forward.** Don't claim the seat as a present, central feature in the interop story. See the timing flag in §7 — this is the one place the copy can get ahead of the live deploy.

---

## 2. Landing page (`/`) — section-by-section

Structure stays (hero → problem → product trio → [dial] → insight → pricing/CTA). Copy and emphasis change: interop leads, the trio re-sequences to **Traceable → Cross-LLM → Compounds**, the autonomy-dial section becomes a steward-beta teaser.

### Hero
- **Brand line:** `yarnnn` *(unchanged)*
- **H1:** Your AI context, version-controlled across every model.
- **Sub:** yarnnn is one attributed filesystem your tools and every LLM you use share. Write it in Claude, it's there in ChatGPT — every change signed, every version traceable. Git's model for LLM context, not another memory cache.
- **Primary CTA:** Start free *(unchanged)*
- **Secondary CTA:** See how it works *(was "See how it compounds")*
- **Chips (replace the vertical chips):** `Claude` · `ChatGPT` · `Slack` · `Notion` · `your own agents`
  *(Rationale: the old chips — "a newsletter / a portfolio / a shop" — sell the agent/operation vertical. The interop story sells the rooms the substrate reaches. Keep the `IntegrationHub` visual; it already shows connected tools feeding the substrate.)*

### Section 2 — the problem (reframed from "self-audit gap" → "context that doesn't travel")
- **H2:** Your context is trapped in whichever chat window made it.
- **Body:**
  > Every model now has memory. But it's *their* memory — walled to that app, that account, unreadable, unversioned. Switch from ChatGPT to Claude and you start over. Let an agent touch it and you can't see what changed or who changed it.
  >
  > So the context you build never becomes an asset. It's scattered across tools that each keep their own copy, none of which can tell you how a fact got there or whether it's still true.

### Section 3 — the product (the trio, re-sequenced)
- **H2:** One filesystem. Every model. Every change accounted for.
- **Card 1 — Traceable** *(lead)*
  - Title: Every version has an author.
  - Body: Every file, every change, every fact is attributed and parent-pointered. `trace` shows you which principal — you, an agent, a platform, a model — wrote each version. A plain storage connector can't show this.
- **Card 2 — Cross-LLM** *(new — the membrane)*
  - Title: Written once, there everywhere.
  - Body: One substrate, reachable from every room you work in over MCP. Write it in Claude, read it in ChatGPT, feed it from Slack and Notion. Neutral by design — no lab can be neutral across its rivals.
- **Card 3 — Compounds** *(kept, de-agented)*
  - Title: Corrections carry forward.
  - Body: Fix one source file and every future read inherits the fix. Your context is monotonically improving — it doesn't reset when you close the tab.
- **Footer line:** `fix one file → every future read inherits it`

### Section 4 — was "the delegation dial," now the steward teaser
*(The autonomy dial is a steward capability. With the steward demoted to beta, this section becomes the upgrade teaser rather than a present-tense feature.)*
- **Eyebrow:** Coming next — beta
- **H2:** Soon: a judgment seat that answers for the commons.
- **Body:**
  > The substrate is the product today. Next, an accountable seat that watches the workspace, places what every principal contributes, and acts within ceilings you set — reconciled against what actually happened, not a safety filter. You'll author its principles; it earns the dial.
- **CTA:** Join the beta list *(or keep present-tense "Supervised / Delegated / Autonomous" trio if you decide the steward ships at launch — see §7)*

### Section 5 — the insight (kept, sharpened to the substrate-as-asset)
- **H2:** Execution is a commodity. The accounted-for context is yours.
- **Body:**
  > As more work moves to models, the durable asset isn't the output — it's the context, with its history intact: your files, your corrections, who-changed-what, served to whatever model you use next. Ninety days in, starting over anywhere else means starting from zero. Not lock-in. Accumulation.
- **Bento (Day 1 / 30 / 90):** keep, lightly de-agented —
  - Day 1: The asset exists. You connect a tool or write a fact; it's attributed and instantly reachable cross-LLM.
  - Day 30: Corrections have compounded. Every model you open starts from the same improving context.
  - Day 90: The history reads like a ledger — nothing forgotten, every change accounted for, every principal on the record.

### Section 6 — pricing teaser + CTA (kept; already on-message)
- **H2:** Free to keep. Pay only for what runs. *(unchanged)*
- **Body:** The workspace is free forever — your files, your context, reachable from any AI you use. When you run an operation on it, you pay only the usage it draws, capped by a monthly budget you set. No seats, no subscription. *(unchanged)*

---

## 3. How it works — re-sequenced

The current five-step walk is an *operation setup* walk (pick a program → write the constitution → … → the seat answers). That's the steward story. For interop-first, the walk becomes a **substrate loop**, with the operation/steward as the final, optional beta step.

- **Metadata title:** How yarnnn works — one context filesystem across every model
- **Hero H1:** Connect once. → It's everywhere you work.
- **Hero sub:** yarnnn turns your scattered AI context into one attributed, versioned filesystem — fed by your tools, reachable from every model. Here's the loop, from an empty workspace to context that travels.

### New steps
1. **Connect your tools** — Link Slack, Notion, your files and history. Reality flows in as attributed observation — not a context window that empties when you close the tab.
2. **It becomes owned, attributed substrate** — Every fact lands as a file with an author and a version. Nothing is anonymous; nothing is overwritten silently. (`trace` proves it.)
3. **Reach it from every room** — The same substrate is served over MCP to Claude, ChatGPT, your agents. Write in one, read in the next. One source of truth across rivals.
4. **Correct once; it compounds** — Fix a source file and every future read inherits the fix. The context is monotonically improving.
5. **Beta — add a steward** *(reframed step 5)* — When you're ready, turn on an accountable judgment seat: it places what every principal contributes, proposes and acts within ceilings you set, and reconciles its calls against outcomes. You author the principles; trust accrues on the record.

### Mechanism trio (bottom) — re-aim from Traceable/Compounds/Judged → Traceable/Cross-LLM/Compounds
- Traceable: Every change has an author and a version.
- Cross-LLM: One substrate, served to every model — neutral by design.
- Compounds: Fix once; the future inherits it. Everywhere else resets.

*(Drop or relabel the "Approve / Queue / Defer" verdict trio — it's pure steward. Move it into the beta step or cut it for the interop pass.)*

---

## 4. About — re-sequenced beliefs

Hero pivots from "the layer platforms structurally can't build" (self-audit/judgment thesis) → "the neutral context layer no lab can build." Same structural argument, aimed at the membrane instead of the steward.

- **Metadata title:** About — the neutral context layer no lab can build
- **Hero H1:** We built the context layer / the labs structurally can't.
- **Hero body:**
  > Every model now has memory. But a lab's memory is walled to that lab and that account, by design — it cannot be neutral across its rivals, and it will never let your context travel to the competitor. The cross-model, cross-tool context layer is *structurally* incompatible with being any one of those models. Nobody owns it because nobody *can*.
  >
  > yarnnn is that layer: one attributed, versioned filesystem your tools and every model share — git's model for LLM context, served cross-LLM. We built it operator-first, run it on its own operations, and record every architectural decision in the open.

### Beliefs (re-ordered; substrate beliefs first, judgment belief demoted to forward)
1. **Context should be an asset, not exhaust** — Built once, owned forever, reachable everywhere. Your accumulated substrate is the asset; models are interchangeable labor. *(replaces "work should be cumulative" as belief #1 — same idea, substrate-framed)*
2. **Authored, not inferred** — Your context, your rules, written by you, versioned forever, never silently mutated. Every revision attributed. *(keep, strong)*
3. **Neutral across models** — One substrate served to every room, no lab in the middle. The portability is the point; a walled memory can't deliver it. *(new — the membrane belief)*
4. **One model, many principals** — You, your agents, your team, their agents, platforms, foreign models — all attribute into one commons. "Personal" is just the smallest case. *(new — multi-principal, kept lightweight)*
5. **Judgment is separate from execution** — *(keep, but reframe as forward/beta)* The seat that answers for consequential action is the next layer, not the wedge — neutral, model-agnostic, reconciled against outcomes. The separation is architectural; it's what makes autonomy trustworthy later.
6. **Receipts, not claims** — 377 recorded architecture decisions; attribution enforced at the write path; built operator-first. *(keep; update count 300+ → 377)*

### "What yarnnn is not" — re-aim
- Not a memory cache locked to one app *(was "chat session that resets")* — your context isn't walled to ChatGPT or Claude; it's one substrate both read, versioned and attributed.
- Not a storage connector *(new)* — a plain MCP filesystem hands back bytes. `trace` hands back the history: who wrote each version, and how it changed.
- Not a notes app — notes sit still. This is a single enforced write path with attribution and revision under it, wired to flow in from your tools and out to every model.
- Not a platform memory that grades its own homework *(keep, demote to forward/steward)* — when the judgment seat arrives, it's neutral and reconciled against reality, not a vendor judging its own model.

### "Who it's for" — broaden from solopreneur-operation → context-owner
Current page narrows to "operator of a bounded operation" (newsletter/portfolio/shop). Interop-first widens the top of funnel:
- Replace chips `a newsletter / a portfolio / a shop / a pipeline / a book of business` → `power users of Claude + ChatGPT · multi-tool teams · agent builders · anyone whose context lives in five apps`.
- Keep one "bounded operation" card for the eventual steward audience, but lead with "anyone tired of re-explaining themselves to every new model."

---

## 5. Pricing — light touch (already interop-forward)

The pricing page is the most on-message page already. Two small alignments:

1. **"What's an operation?" card** — currently defines an operation as "your newsletter operation, your portfolio operation" and assumes the agent runs. With the steward as beta, soften to: *"An operation is the optional agent layer running on your workspace — in beta. The workspace, files, context and cross-LLM access are always free; an operation is what draws metered usage when you turn it on."*
2. **Card 1 (Workspace $0) blurb** — already says "your context reachable from any AI you use (MCP)." Strengthen to lead the value: *"The substrate: files, uploads, your context — attributed, versioned, and reachable from every model you use over MCP. `trace` included. Starts with a $3 usage balance."*

Everything else (balance, budget ceiling, hard-stop-at-zero, no-subscription) stays — it's accurate and well-built. Title/keywords unchanged.

---

## 6. Metadata / SEO + brand strings + CTA labels

### `web/lib/metadata.ts` — BRAND (sitewide; currently agent-first)
- **tagline:** `Autonomous Agents for Recurring Knowledge Work` → **`Version-controlled context for every AI you use`**
- **description:** `Persistent agents, shared workspace context, and recurring tasks…` → **`One attributed, versioned filesystem your tools and every LLM you use share. Write it in Claude, read it in ChatGPT — every change signed and traceable. Free workspace, pay only for what runs.`**

### Per-page metadata
| Page | New title | New description (≤ ~155 chars) |
|---|---|---|
| `/` | The version-controlled context layer for every AI you use \| yarnnn | One attributed filesystem your tools and every LLM share. Write in Claude, read in ChatGPT — every change signed and traceable. Free to keep. |
| `/how-it-works` | How yarnnn works — one context filesystem across every model | Connect your tools; your context becomes owned, attributed, versioned substrate, reachable from every LLM over MCP. Correct once; it compounds. |
| `/about` | About — the neutral context layer no lab can build | A lab's memory is walled to that lab. The cross-model context layer is structurally incompatible with being any one model. We built it. |
| `/pricing` | *(keep current — already accurate)* | *(keep)* |

### Keywords (swap the agent-first set)
Drop / demote: `autonomous ai agents`, `ai judgment seat`, `ai for solopreneurs`, `ai for your newsletter/portfolio/shop`.
Lead with: `cross-llm context`, `mcp context filesystem`, `version-controlled ai memory`, `attributed ai context`, `portable ai memory`, `ai context across chatgpt and claude`, `git for llm context`, `model-agnostic ai memory`. Keep `accountable ai` / `ai judgment seat` in the long tail for the steward beta.

### CTA labels (`web/lib/cta.ts`)
- `PRIMARY_CTA_LABEL` "Start free" → **keep.**
- Sitewide secondary "See how it compounds" → **"See how it works"** (compounding is now one beat of several, not the whole promise).
- `stageBLabel` / `seatCheckout` mechanics → **leave as-is** (no pricing change in this pass).

---

## 7. Open decisions / flags before I apply to `.tsx`

These are the calls where the copy could get ahead of the live system — worth a yes/no from you:

1. **Steward timing — "coming soon" vs "now in beta."** ADR-375 ships the agent gated *off by default for the interop launch deploy*, but the **current live product still exposes the full Reviewer/agent**. If the live site still has agents working today, "coming soon" reads as a downgrade/contradiction to existing users. Options: (a) "now in beta" if it stays on, (b) "coming soon" only if you're actually gating it off at the interop launch. **Default I'll use unless you say otherwise: "beta," present-but-secondary.**

2. **Multi-principal exposure level.** I've kept it to one belief + the `trace` line + a chip. The re-key (ADR-373) is Phase-1-in-progress, not shipped end-to-end. Confirm you want it *mentioned* now (forward-safe) vs *held* until the re-key fully lands.

3. **Vertical chips removal.** The "newsletter / portfolio / shop" chips appear on landing + about and carry the solopreneur-operation framing. Interop-first replaces them with rooms/principals. Confirm you're OK dropping the vertical framing from the top of funnel (it still lives in the steward/operation beta narrative).

4. **`IntegrationHub` visual.** It currently shows connected *input* tools. On-message as-is. Optional enhancement (separate task): show the *output* side too — substrate → Claude/ChatGPT — to literally draw the membrane. Flag if you want that.

5. **Receipts count.** I'll update "300+ architecture decisions" → "377" (current ADR count). Say if you'd rather keep it round ("370+").

---

## 8. What I'll do on your go

Per page, the actual `.tsx` edits are contained: each page is a single component with copy in inline JSX + a `STEPS`/`BELIEFS`/`metadata` const at the top. No structural/layout rewrites needed — this is a copy + emphasis pass. I'll apply in this order: `metadata.ts` + `cta.ts` (sitewide strings) → `page.tsx` (landing) → `how-it-works` → `about` → `pricing` (light). Then a quick `pnpm build`/typecheck pass to confirm nothing broke.

---

## 9. Interaction design (2026-06-29)

The copy pivot above shipped the *message*. A follow-on pass reframes the *interaction* model —
the pages had gone visually flat (static text blocks replacing richer sections; two animated
components orphaned). The reframe starts from the positioning, not the existing components: the
governing principle is **"interaction demonstrates the mechanism, it does not decorate the page"**
— motion is spent only on the three moat rungs (membrane / ledger-trace / compounds), and
everything else stays calm on purpose.

The design spec of record is **[marketing-interaction-design-2026-06-29.md](./marketing-interaction-design-2026-06-29.md)**.
It owns: the governing principle, the global motion rules (scroll-reveal contract,
`prefers-reduced-motion`, no-hero-animation, no-CLS), the per-page intent→interaction→component
tables, the component inventory + retirement ledger (`MockOutputs` + `AnimatedTimeline` retired),
the a11y/perf checklist, and the 5-phase build sequence. This pivot doc remains the strategy of
record for *message*; that doc is the strategy of record for *interaction*.

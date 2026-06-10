# Site Copy Spec v1 — Full-Site Refactor to Canon (2026-06-10)

> **Status**: Ratified spec — ready for FE implementation
> **Scope**: Full site in one push (operator-ratified): `/` · `/pricing` · `/how-it-works` · `/faq` · `/about` · `/invest` · `/blog` (framing only)
> **Inputs (all ratified)**: ESSENCE v14.1 · NARRATIVE v5 (beat structure + surface adaptations) · GTM_POSITIONING v4 (incl. the verb-frame hero, noun-pass doc) · ADR-334 (pricing) · Path-A decision: **judgment trail, not returns** (no P&L claims anywhere on the site)
> **Why**: the live site is two narrative eras stale — "Describe your work, YARNNN creates the agents," "$19/mo for the full palette" — and actively contradicts ratified canon.

---

## 0. Global rules (apply to every page)

1. **Retired copy is banned** (ESSENCE v14 retired-seeds + NARRATIVE v5 retired table): no "team you build by chatting," "full palette," "domain experts," "$19/mo," no bare capability adjectives (*persistent / compounds / autonomous / self-improving / runs while you sleep*) **without the mechanism in the same breath** (*owned · attributed · corrections carry forward · judged against what actually happened*).
2. **No P&L / performance claims** (Path-A decision). Proof = the judgment trail artifact.
3. **Vocabulary**: per NARRATIVE v5 table. "Delegate" always welded to *judgment*, never *task*. "Judgment seat," never "approval workflow/guardrails." "Operation," "the work you run." "Solopreneur" allowed in SEO surfaces (page titles/meta) only — never as the on-page identity claim.
4. **Tone**: plain, declarative, A-diction (short sentences). No exclamation marks. Mechanism over adjectives.
5. **Vertical chips** appear wherever the umbrella claim lands: *a newsletter · a portfolio · a shop · a pipeline · a book of business*.
6. **CTA pair, sitewide**: primary "Start free" (bare workspace) · secondary "See how it compounds" (→ /how-it-works). When ADR-331 Stage B ships the retrospective audit, primary CTA upgrades to "Bring your track record" — leave the slot wired for the swap.

---

## 1. `/` — Landing

**Section 1 — Hero (ratified verbatim):**

> # The work you run shouldn't reset.
> YARNNN is the workspace where it compounds. Agents you own produce it. Corrections carry forward. A judgment seat answers for what ships — even when you're not there.
>
> [Start free]  [See how it compounds]
>
> *a newsletter · a portfolio · a shop · a pipeline · a book of business*

**Section 2 — The problem (Beat 1, the self-audit gap):**

> ## Every platform now sells you an AI delegate. None will tell you if its judgment is any good.
> The agents got good. Scheduled runs, persistent memory, work done while you're away — that part is everywhere now. But look closer: the same vendor that builds the delegate grades the delegate. Memory you can't read. Actions with no attributed trail. "Improvement" you take on faith.
> And underneath it all, the work stays episodic. Every artifact is generated fresh. Fix today's output and tomorrow starts from the same place. Nothing is owned, so nothing compounds — and nothing answers for itself.

**Section 3 — The product (Beat 3, the cumulative workspace, three mechanisms):**

> ## A workspace where nothing is lost and everything answers for itself.
> **Everything is traceable.** Every file has an author. Every change has a revision. The deck your agent built cites the files it was composed from.
> **Corrections compound.** Fix one source file and every future artifact inherits the fix. Work here is monotonically improving. Work everywhere else resets.
> **Judgment is independent.** Consequential actions pass through a Reviewer — a judgment seat you author the principles for, whose calls are reconciled against what actually happened. Not a safety filter. A track record.
> *(visual: fix-one-file → three artifacts improve; or a revision chain with authors)*

**Section 4 — The delegation dial:**

> ## You decide how much it runs without you.
> **Supervised** — every consequence waits for your approval. **Delegated** — it acts within ceilings you declared. **Autonomous** — it runs the framework you wrote, and the trail shows you everything. Trust is earned in the record, and the dial only moves when you move it.

**Section 5 — Proof (judgment trail; NO returns):**

> ## This is what accountable looks like.
> *(real artifact excerpts, lightly redacted: an attributed verdict with reasoning; a calibration entry reconciling a past call against its outcome; a Reviewer declining an operator's pressure-edit with the rule cited)*
> Every call, attributed. Every outcome, reconciled. Every rule change, authored and dated. Not screenshots of a dashboard — the actual record the operation keeps about itself.

**Section 6 — The insight (Beat 4):**

> ## Execution is becoming a commodity. What compounds is yours.
> As more work gets delegated, what's left that matters is the context only you have and the judgment only you can authorize. That's the asset this workspace accumulates: your files, your corrections, your watchlist's history, your seat's track record. Ninety days in, starting over anywhere else means starting from zero. That's not lock-in. That's accumulation.

**Section 7 — Pricing teaser + CTA (Beat 6):**

> ## Free to keep. Priced when it runs for you.
> The workspace is free forever — your files, your context, reachable from any AI you use. When you're ready to run an operation on it, seats start at $149/month — priced by how much you delegate, not by features. 14-day trial, no card.
> [Start free]  [See pricing]

---

## 2. `/pricing` (content = ADR-334)

**Header:** *Priced by trust, not by features.* Sub: *Every plan is the full product. The only thing a tier changes is how much the operation may do without your approval — and how much usage is included.*

**Free card — "Workspace":** $0 forever. The substrate: files, uploads, chat, your context reachable from any AI (MCP). No running operation. Includes $3 usage credit; top-ups available. CTA: Start free.

**Seat cards (per operation / month, annual = 10×):**
- **Supervised — $149**: every consequential action waits for you · $15/mo usage included · full workspace, full trail.
- **Delegated — $299** *(highlight)*: acts within ceilings you declare · $30/mo usage included · everything in Supervised.
- **Autonomous — $499**: runs the framework you authored · $60/mo usage included · everything in Delegated.

All cards: *14-day trial, no card required.*

**Below the cards — three honest paragraphs:**
1. *What's an operation?* An activated program running on your workspace — your newsletter operation, your portfolio operation. Each runs on its own seat with its own dial. The workspace itself is never paid.
2. *What's "usage"?* Every model call is metered at transparent rates and drawn from your included balance — you can read every line of it. Most operations use a fraction of what's included; heavy months top up from $10.
3. *Why per-operation?* Because the value isn't compute — it's the calls made correctly and the asset that compounds. You pay for a running operation you trust, at the level you trust it.

**Mini-FAQ on page:** trial mechanics · what happens at zero balance (it stops, nothing is lost) · cancel = operation deactivates, workspace and every file remain yours.

---

## 3. `/how-it-works`

Structure = the `/setup` walk, in operator language (the four flows without the jargon):

1. **Pick your operation** — choose a program (trading, authoring; more coming) or start with a bare workspace.
2. **Write the constitution** — what it's for, the rules it judges by, how much it may do alone. Authored by you, amendable by you, versioned forever.
3. **Connect and bring in your reality** — link your platforms; import your files and history. *(Stage-B slot: "bring your track record — the seat reconciles your past decisions into a calibration trail on day one.")*
4. **It produces; you correct; corrections stay** — artifacts trace to sources; fixing a source fixes the future.
5. **The seat answers for what ships** — proposals, verdicts, reconciled outcomes, a trail you can audit. Move the dial as trust accrues.

Close with the mechanism trio (traceable / compounds / judged) and CTA pair.

---

## 4. `/faq` (key entries; keep ≤12)

- **How is this different from ChatGPT / Claude / Cowork?** Use GTM v4 §4 objection lines verbatim ("they grade their own homework…"). Concede capability parity plainly; differentiate on owned/attributed/judged.
- **Is my data mine?** Yes, structurally: every file attributed, every revision kept, exportable, reachable from other AIs via MCP. The workspace is the asset; we never train on it.
- **What's an operation / a program?** (per pricing ¶1.)
- **Can it write my newsletter for me?** Honest author-blindness answer: it drafts, researches, and runs the operation; what ships under your name is yours to approve. For work where *being you* is the product, it's the desk, not the byline.
- **What does the Reviewer actually do?** Verdict + reasoning + reconciliation, with the trail as proof. Not a content filter.
- **What happens when the trial ends / balance hits zero / I cancel?** Nothing is deleted; the operation pauses; the workspace stays free.
- **Which model powers it?** Model-agnostic by design; judgments are calibrated against outcomes, not against a vendor's say-so.
- **Is this autonomous trading? Is this financial advice?** No performance claims, no advice; you author the rules, the seat enforces them, paper-first. (Required hedge; keep tight.)

---

## 5. `/about`

Thesis-as-revelation, compressed (NARRATIVE v5 Beats 1→4 in ~300 words) + the founder's note: built operator-first, run on its own operations, 300+ recorded architecture decisions — *receipts culture* as identity. No team-page theater.

## 6. `/invest`

Rewrite against NARRATIVE v5's written-VC-application adaptation (Beats 1 and 5 weighted; high-ACV motion per GTM v4 §5; judgment-trail proof posture). Keep gated/low-key. **Remove all v3-era figures ($1.14B SAM, $19/mo, solo-consultant wedge).**

## 7. `/blog`

No structural change; add the standing rule: posts argue the thesis publicly (the five-post Anthropic-response pattern) and never use retired seeds. Tag pages by vertical chip nouns for SEO ("solopreneur" allowed here).

---

## 8. Implementation notes (for the build session)

- Pages live at `web/app/{page.tsx,pricing,how-it-works,faq,about,invest,blog}`. Single-file edits per page; stage by name; concurrent lanes active.
- Keep existing component/styling system; this is a copy + section-IA refactor, not a redesign. Cut sections that have no spec equivalent (e.g., current "palette" grid).
- CTA targets: "Start free" → existing signup; "See how it compounds" → /how-it-works. Leave the Stage-B retrospective-audit CTA behind a constant for the swap.
- Proof-section artifacts (§1.5): pull real excerpts from the alpha workspaces' decisions/calibration files, redact tickers/amounts, render as styled blocks — coordinate with operator for selection. **No dollar figures.**
- Meta/SEO: titles may use "solopreneur," "AI for your newsletter/portfolio/shop"; on-page identity stays verb-frame.
- `/pricing` must match ADR-334 exactly; if implementation precedes ADR-334 P1–P3, add "trial opens [month]" wording rather than shipping a broken checkout.

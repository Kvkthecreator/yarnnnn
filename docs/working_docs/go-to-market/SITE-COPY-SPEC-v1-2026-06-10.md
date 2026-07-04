# Site Copy Spec v1 — Full-Site Refactor to Canon (2026-06-10)

> **STALENESS NOTE (2026-07-04, ADR-404)**: the live pages have moved past this spec twice — first to the "Shared memory for AI + human work" framing, then the **ADR-404 commons-first re-center** (team invites first-class; automatic connector capture de-emphasized — the capture lane is dormant behind `CONNECTOR_CAPTURE_ENABLED`; no outbound multi-model orchestration promised). Do not implement against this spec without reconciling; a v2 spec is the right vehicle for the next full pass.

> **Status**: Ratified spec — ready for FE implementation. **Discourse pass 2026-06-10** (operator-ratified) hardened seven decisions; see §-9 (Discourse outcomes) for the diffs from the original draft.
> **Scope**: Full site in one push (operator-ratified): `/` · `/pricing` · `/how-it-works` · `/faq` · `/about` · `/invest` · `/blog` (framing only)
> **Inputs (all ratified)**: ESSENCE v14.1 · NARRATIVE v5 (beat structure + surface adaptations) · GTM_POSITIONING v4 (incl. the verb-frame hero, noun-pass doc) · ADR-334 (pricing — **Ratified-direction; checkout P1–P3 UNBUILT**) · Path-A decision: **judgment trail, not returns** (no P&L claims anywhere on the site)
> **Why**: the live site is two narrative eras stale — "Describe your work, YARNNN creates the agents," "$19/mo for the full palette," the Specialist palette, "tasks are what," `$1.14B SAM` — and actively contradicts ratified canon.
> **Build basis**: copy + section-IA refactor on the existing component/styling system. `/how-it-works`, `/about`, `/invest` are **section-IA rewrites** (their current sections encode retired canon — the Specialist palette, "tasks are what," banned market figures), not copy swaps. One new file permitted: `web/lib/cta.ts` (CTA-target constants — the "leave the slot wired" ask, §0.7).

---

## 0. Global rules (apply to every page)

1. **Retired copy is banned** (ESSENCE v14 retired-seeds + NARRATIVE v5 retired table): no "team you build by chatting," "full palette," "domain experts," "$19/mo," no bare capability adjectives (*persistent / compounds / autonomous / self-improving / runs while you sleep*) **without the mechanism in the same breath** (*owned · attributed · corrections carry forward · judged against what actually happened*).
2. **No P&L / performance claims** (Path-A decision). Proof = the judgment trail artifact.
3. **Vocabulary**: per NARRATIVE v5 table. "Delegate" always welded to *judgment*, never *task*. "Judgment seat," never "approval workflow/guardrails." "Operation," "the work you run." "Solopreneur" allowed in SEO surfaces (page titles/meta) only — never as the on-page identity claim.
4. **Tone**: plain, declarative, A-diction (short sentences). No exclamation marks. Mechanism over adjectives.
5. **Vertical chips** appear wherever the umbrella claim lands: *a newsletter · a portfolio · a shop · a pipeline · a book of business*.
6. **CTA pair, sitewide**: primary "Start free" (bare workspace) · secondary "See how it compounds" (→ /how-it-works). When ADR-331 Stage B ships the retrospective audit, primary CTA upgrades to "Bring your track record" — leave the slot wired for the swap.
7. **CTA targets are constants, not literals.** All CTA hrefs route through `web/lib/cta.ts` (new): `CTA.signup` = `/auth/login` (the existing bare-workspace entry — there is no separate signup route), `CTA.howItWorks` = `/how-it-works`, plus the wired-but-unused `CTA.stageBLabel` ("Bring your track record") and `CTA.seatCheckout` (null until ADR-334 P2 ships LS seat products). One home for the future swaps; no scattered string literals.
8. **CHECKOUT GUARD — current default state (binding).** ADR-334 is *Ratified-direction*; the seat-checkout substrate (P1 entitlement record, P2 LS seat products + webhooks, P3 tier plumbing) **does not exist.** `/pricing` therefore displays the real seat tiers but its CTAs route to `CTA.signup` (`/auth/login`, the bare workspace) under **"seat trials open soon"** framing — NEVER to a seat purchase. `CTA.seatCheckout` stays null and unwired until P2 lands. Shipping three "Start trial / no card" buttons against a checkout that doesn't exist is a broken funnel and is prohibited.

---

## 1. `/` — Landing

> **Beat selection (per NARRATIVE v5 landing adaptation):** the landing runs Beats **1 · 3 · 4 · 6** only — problem → product → insight → CTA. Beat 2 (proof of demand) and Beat 5 (the four-property moat) are **deck/VC-only by design** and deliberately absent here; do not add a moat or demand-validation section. The original draft's proof block (Beat-5-adjacent) was **cut in the 2026-06-10 discourse** (§-9.1) — "accountable" is carried entirely by the three mechanisms in Section 3, which is sufficient.

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

> **Implementation pin (discourse §-9.6):** this section describes the **AUTONOMY substrate** (real, shipped — `AUTONOMY.md`, declared ceilings, the manual→bounded→autonomous posture). It is NOT the ADR-334 *seat tier* (unbuilt). The three words coincide with the pricing tiers by design (the dial *is* the pricing axis), but on the landing page this is a product-capability claim about authored autonomy, not an entitlement claim. No "trial," no price, no checkout language in this section.

**Section 5 — The insight (Beat 4):**

> *(Proof block CUT in v1 per discourse §-9.1. Beat 5 moat is deck/VC-only. Section renumbered from 6.)*

> ## Execution is becoming a commodity. What compounds is yours.
> As more work gets delegated, what's left that matters is the context only you have and the judgment only you can authorize. That's the asset this workspace accumulates: your files, your corrections, your watchlist's history, your seat's track record. Ninety days in, starting over anywhere else means starting from zero. That's not lock-in. That's accumulation.

**Section 6 — Pricing teaser + CTA (Beat 6):**

> ## Free to keep. Priced when it runs for you.
> The workspace is free forever — your files, your context, reachable from any AI you use. When you're ready to run an operation on it, seats start at $149/month — priced by how much you delegate, not by features. 14-day trial, no card.
> [Start free]  [See pricing]

---

## 2. `/pricing` (content = ADR-334)

> **Full teardown.** The current page is the retired v3 model ($3 free / $19 Pro / "every feature on every plan"). Replace wholesale with the three-seat model below. **CHECKOUT GUARD (§0.8):** all seat-card CTAs route to `CTA.signup` (`/auth/login`) under "seat trials open soon" framing — the seat-checkout substrate (ADR-334 P1–P3) is unbuilt. The free "Workspace" card's CTA also routes to `CTA.signup` (that's the live path today). No "no card required / start trial" button may imply a working seat purchase.

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

> **Section-IA rewrite (discourse §-9.5), not a copy swap.** The current page encodes retired canon: Step 02 is the **Specialist palette** ("Six roles. Your agents are built from them") and the step sequence is the old "describe your work → YARNNN creates the agents" flow. **CUT the palette section entirely** (§8: cut sections with no spec equivalent). Reshape the numbered-step IA to the five-step `/setup` walk below. Keep the existing section scaffolding/styling (the numbered `00/01/02…` band pattern, border-top sections); replace the step *content and sequence*.

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

> **Verbatim copy below (discourse §-9.2), section-IA reshape.** The current "What we believe" cards carry retired canon — notably **"Agents are who. Tasks are what."** (the task abstraction was sunset by ADR-231). Drop that card; reshape the belief set to current canon. Keep "Operating system, not application" (ADR-222 holds). Keep the existing three-band structure (hero / belief cards / "what it's not" / who-it's-for / CTA).

Thesis-as-revelation, compressed (NARRATIVE v5 Beats 1→4 in ~300 words) + the founder's note: built operator-first, run on its own operations, 300+ recorded architecture decisions — *receipts culture* as identity. No team-page theater.

**Hero:**

> # We built the layer the platforms structurally can't.
> Every platform now sells you an AI delegate. None will tell you whether its judgment is any good — they're grading their own homework. YARNNN is the workspace where work is cumulative and a neutral judgment seat answers for what ships. We built it operator-first, run it on its own operations, and record every architectural decision in the open.

**What we believe (belief cards — replaces the retired set):**
- **Work should be cumulative, not episodic.** Fix something once; everything after inherits it. The substrate is the asset.
- **Operating system, not application.** A kernel runs the operation; programs run in userspace; the workspace is yours. *(ADR-222)*
- **Judgment is separate from execution.** Consequential actions pass through a Reviewer — a seat you author the principles for — whose calls are reconciled against what actually happened.
- **Authored, not inferred.** Your context, your rules, your voice — written by you, versioned forever, never silently mutated.
- **You supervise; the operation runs.** You set the delegation dial. The operation runs at the level of trust it has earned, and the trail shows you everything.
- **Receipts, not claims.** 300+ recorded architecture decisions; attribution enforced at the write path; the calibration loop live in the alpha programs. The architecture *is* the proof.

**What yarnnn is not** (keep the existing contrastive cards, refreshed): not a chat session that resets · not a platform agent that grades its own homework · not a memory wiki with no operation · not a safety filter bolted onto a model.

**Who it's for:** someone with something that's theirs to run, that they can't be continuously present for, and who refuses to let it reset — the operator of a bounded operation (*a newsletter · a portfolio · a shop · a pipeline · a book of business*).

**CTA:** Start free → `CTA.signup`. Secondary: See how it compounds → `CTA.howItWorks`.

## 6. `/invest`

> **Verbatim copy below (discourse §-9.8), section-IA reshape. NO hard $ figures (ratified):** remove `$1.14B SAM`, `$19/mo`, "solo-consultant wedge," and the headline raise number. Lead with **stage + traction + architecture-as-evidence + the high-ACV expansion motion** (NARRATIVE v5 Beat 5/6). Operator adds any raise/market numbers later — the page must read complete without them, never invent them. Keep gated/low-key. Keep existing section scaffolding (hero / raise → reframe to "stage & traction" / bifurcation / what's-live / thesis / market → reframe to "motion").

Rewrite against NARRATIVE v5's written-VC-application adaptation (Beats 1 and 5 weighted; high-ACV motion per GTM v4 §5; judgment-trail proof posture).

**Hero:**

> # Platforms build delegates. They won't build the layer that holds delegates accountable.
> For the same structural reason ratings agencies aren't run by the banks they rate: a platform judging its own model's agents has a self-audit problem. A neutral, model-agnostic judgment seat does not. YARNNN is the workspace where work is cumulative and every consequential call passes through a seat with a track record.

**Stage & traction** (replaces the "$1.14B SAM / headline raise number" card — no hard figures):
> Alpha. Running on its own operations. The calibration loop is live in the alpha programs; the workspace, the judgment seat, the delegation dial, and the attributed substrate all ship today. 300+ architectural decisions recorded in the open — the receipts culture is the diligence surface.

**The bifurcation** (keep the existing AI-tools-vs-persistent-systems contrast, refreshed to the self-audit thesis): the platforms moved up the stack into work context in 2026 — and that *creates* the accountability gap rather than closing it. Tools that grade their own homework vs. a neutral seat that answers for what ships.

**What's live** (refresh the existing card grid to current canon — drop Specialist/workforce framing): the cumulative workspace + authored substrate (attribution enforced at the write path) · the judgment seat + reconciled calibration trail · the delegation dial (manual → bounded → autonomous, governance boundary held in code) · model-agnostic + MCP-native (the substrate other agents read and write through).

**Investment thesis:** execution commoditizes; context and judgment compound. The durable asset is the owned, attributed workspace + the installed judgment seat with a track record — a composition the platforms face *structurally* (incentive and position, not capability) and memory startups can't reach (substrate with no operation is a wiki).

**Motion** (replaces "market" / removes SAM): premium, high-ACV, expansion-led. Land narrow on bounded operations with fast feedback loops; price per running operation tiered by delegation level (the trust dial is the pricing axis); expand through tight communities. Hundreds of operators paying real money is a real business — never a volume play.

**CTA:** keep gated (e.g. contact `admin@yarnnn.com`).

## 7. `/blog`

No structural change; add the standing rule: posts argue the thesis publicly (the five-post Anthropic-response pattern) and never use retired seeds. Tag pages by vertical chip nouns for SEO ("solopreneur" allowed here).

---

## 8. Implementation notes (for the build session)

- Pages live at `web/app/{page.tsx,pricing,how-it-works,faq,about,invest,blog}`. Single-file edits per page; stage by name; concurrent lanes active (do NOT `git add -A` — stage by name).
- Keep existing component/styling system; this is a copy + section-IA refactor, not a redesign. Cut sections that have no spec equivalent (the `/how-it-works` "palette" grid — §3 note; the `/about` "tasks are what" card — §5 note; the `/invest` SAM/headline-raise figures — §6 note).
- CTA targets via `web/lib/cta.ts` (§0.7): `CTA.signup` (`/auth/login`), `CTA.howItWorks` (`/how-it-works`), `CTA.stageBLabel` + `CTA.seatCheckout` (wired-but-unused — the Stage-B / seat-checkout swap slots).
- **Proof section (§1.5) is CUT from v1** (discourse §-9.1). No fabricated judgment-trail excerpts. The real-excerpt pull is a separate operator-gated follow-up.
- Meta/SEO: titles may use "solopreneur," "AI for your newsletter/portfolio/shop"; on-page identity stays verb-frame.
- **`/pricing` checkout guard** is §0.8 (promoted from a buried footnote): real tiers shown, CTAs → `CTA.signup` with "seat trials open soon" framing, no broken seat checkout.

---

## -9. Discourse outcomes (2026-06-10 pass — diffs from the original draft)

The original draft was sound; this pass hardened seven decisions before implementation. Recorded so future editors see *why* the spec reads as it does.

1. **Proof section cut from v1** — §1.5 (real judgment-trail excerpts) required live operator substrate; a build session synthesizing plausible excerpts would fabricate the one block whose entire claim is "this is the actual record." Cut rather than risk fabrication. Landing = Beats 1·3·4·6. Real-excerpt pull is a separate operator-gated follow-up (or waits for ADR-331 Stage B's stronger artifact).
2. **`/about` + `/invest` written verbatim now** (not left as pointers) — every other page ships verbatim copy; pointers invite invented prose. Done as section-IA reshapes because their current sections encode retired canon.
3. **`/invest` carries no hard $ figures** — NARRATIVE v5 Beat 6 gives the *motion* (high-ACV, expansion-led) but deliberately no SAM/TAM. The page leads with stage + traction + architecture-as-evidence; operator supplies any numbers later. Inventing a market figure on an investor page is the one place sloppiness actually costs.
4. **Pricing CTAs → `/auth/login`** — ADR-334 checkout (P1–P3) is unbuilt; the real $149/$299/$499 tiers show, CTAs route to the live bare-workspace entry under "seat trials open soon." (Codified as §0.8.)
5. **`/how-it-works`, `/about`, `/invest` are section-IA rewrites** — not copy swaps. The Specialist palette and "tasks are what" are retired *structure*, not just stale words.
6. **Landing §4 dial pinned to the AUTONOMY substrate**, not ADR-334 seat entitlements — the three words coincide by design but the landing makes a product-capability claim (authored autonomy, shipped), not an entitlement claim (unbuilt).
7. **CTA-constants module** (`web/lib/cta.ts`) — the one permitted new file; gives the Stage-B label swap and the future seat-checkout URL a single home (the spec's "leave the slot wired" ask).
8. **Landing beat-omission made explicit** — Beats 2 (demand) and 5 (moat) are deck/VC-only and deliberately absent from the landing; the note in §1 prevents a future editor "restoring" them.

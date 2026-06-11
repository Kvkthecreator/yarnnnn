# Perception rungs 2 + 4 in totality — the psychographic-consumer scope

> **Status**: Strategy scoping (discourse-earned 2026-06-11, KVK + Claude). Feeds the next ADR cycle; nothing here lands as canon until ratified. Companion to [ADR-335](../adr/ADR-335-perception-field.md) (the perception field, Crawl-A landed) + the context-in primacy ladder (ADR-335 §4).
>
> **The question this answers**: can a long-running, self-improving agent with substrate achieve a fully closed loop for a *generalized consumer* — psychographic-driven (defined by what they care about), not job-driven (defined by an operation) — without rungs 2 (websearch) and 4 (standing web watches)? If not, which rungs are the highest-leverage strategic investment before real-user activation?

## 1. The answer: no — and the four-flow model says exactly why

The context-in primacy ladder (ADR-335 §4) was derived for job-driven operators, and it holds for them: the trader closes its loop on rung 3 (platform = ground truth), the author on rung 1 (their corpus IS the context). **The psychographic consumer inverts the ladder.** They have no work corpus to upload (rung 1 thin), no work platform whose state is their ground truth (rung 3 weak), and their entire world-present cell — the things they care about, follow, want watched — lives on the open web. For this profile:

- **Rung 2 (websearch) and rung 4 (standing watches) are not extensions — they are the consumer's primary perception.**
- Without them: flow 1 is thin (nothing accumulates but chat), flow 3 has no signal to grade against, flow 4 has nothing to calibrate → no self-improvement → the "off" feeling ADR-332 named as flow-incompleteness. A perception-less consumer workspace is a chatbot with files.

**The bare-workspace corollary** (the question's second half): a non-program default workspace *never* achieves a closed loop — by ratified design (Direction A: no program = no declared flows; the Stage-0 soak validates exactly that honest incompleteness). The strategic gap is therefore NOT "make default workspaces loop" — it is **ship the program shape whose declared flows match a psychographic consumer**. Direction A stays intact: consumers activate a program too; theirs is just interest-shaped, not job-shaped.

## 2. The validated prototype already exists: anr-scout is psychographic in structure

The A&R journey (2026-06-11, Stages 1–3 PASS) is structurally the consumer shape wearing a job costume: **declared interests** (artists) → **evidence gathering** → **judgment briefs with watch-calls-and-triggers** → **operator verdicts**. Swap "artists" for any psychographic interest set (creators, markets, scenes, topics, teams) and the judgment shape transfers unchanged. This is why the journey persona was chosen to be re-runnable — the consumer program generalizes it.

## 3. The investment ladder (leverage order, with the steady-state bar)

The bar for each phase: **stable, tested, verified — eval-gated like everything else this week** (episodic gate → standing instrument → tenure read).

| # | Investment | Status today | Build size | Why this leverage |
|---|---|---|---|---|
| **P1** | **Rung 2 exercised** — websearch as agent-attested evidence inside judgment, distilled (never dumped) into substrate | `WebSearch` primitive LIVE in kernel registry; alpha-author declares the capability; never exercised in a judgment eval | ~zero build; one eval turn (anr-scout: "verify Mara Voss's claimed numbers") + observation-discipline read | Closes the only untested built rung; gives the consumer's evidence-gathering half its receipts |
| **P2** | **Rung 4a — generic web/RSS standing watch (ADR-335 D7, pulled forward)** — one mechanical primitive reading declared URLs/feeds on cadence, distilling into signal substrate per the observation contract | Kernel slot (`substrate_abi.watches`), observation contract, Check 7 instrument, wake machinery ALL landed (Crawl-A); only the transport executor is missing | ~1–2 weeks incl. eval. Deterministic distillation: feed/page → structured observation entries (title/url/published/excerpt — feed entries are already summaries, ADR-153-clean); semantic reading happens at judgment wakes, keeping mechanical = zero-LLM | **The consumer's standing perception.** "Watch this for me" is the core psychographic verb, and every piece of kernel scaffolding for it shipped this week. The R3 staging refinement explicitly anticipated D7 pulling forward of the MCP client — the psychographic ICP IS that demand |
| **P3** | **Consumer-shaped ground truth (flow 3)** — two sources: (a) operator attestation (approve/reject/usefulness verdicts on briefs — the proposal machinery already produces this), (b) **prediction grading**: watch-calls-with-named-triggers graded against subsequent observations ("said watch X on trigger Y; Y happened/didn't") | The brief shape already carries triggers (mara-voss: "upgrade trigger = retention holds while geo diversifies"); reconciliation recurrence exists | Mostly substrate convention + reconciliation prompt; no new kernel | **Without this, P1+P2 give perception but no closed loop** — nothing grades the judgment, flow 4 starves. Prediction-grading is the consumer analog of `by_signal` expectancy, and it makes the seat's calls falsifiable — the self-improvement axis |
| **P4** | **The interest-scout program bundle** — packages P1–P3 as an activatable program: declared interest set (the `_universe.yaml` analog), web/RSS watches, periodic briefs in the operator's voice, prediction-graded `_signal.md`-class ground truth | anr-scout validated the judgment shape; bundle spec machinery (ADR-223) + four-flow gate ready | A bundle (docs + reference workspace), not kernel code | Direction A compliance for consumers: they activate a program like everyone else; this is the program. Also the honest scope-limiter — we ship ONE consumer program shape, not route-i's full assembly |
| **P5 (deferred)** | **Rung 4b — MCP client** | Unbuilt (Crawl-B), demand-pulled | — | The trigger sharpens: *the first consumer watch web/RSS can't serve* (platform-locked signals: Spotify stats, Strava, etc.). Until then, RSS/web covers the open-web tail, and the transport-blind contract means MCP slots in later with zero redesign |

## 4. What "stable steady state for activation" means, concretely

Activation-ready = a psychographic signup can: activate the scout program → declare interests through chat (Stage-1 shape, validated) → watches go live on web/RSS (P2) → briefs arrive with watch-calls (validated shape) → their verdicts + outcomes grade the seat (P3) → calibration prunes attention (Check 7 + the calibration mirror, both live). Every step eval-gated: P1 gets an episodic turn; P2 gets a per-source contract test + Check 7 (already transport-blind — applies unchanged); P3 gets a tenure-read axis (prediction-grade accuracy); P4 gets the four-flow conformance gate (already enforcing).

## 5. What this deliberately does NOT scope

- No route-i operator-assembled programs (P4 is one curated bundle, not assembly).
- No MCP client until the named trigger fires (P5).
- No connector catalog, no perception manager, no push/webhook ingestion — all ADR-335 anti-goals stand.
- No new attestation taxonomy: rung 2 observations are `agent`-attested, rung 4a `platform|agent` per source provenance — the existing enum.

## 6. Recommended sequence from today

1. **P1 this week** (one eval turn on the live anr-scout soak — doubles as its rung-2 perception read).
2. **Ratify P2–P4 as the next ADR** (the "interest-scout perception" ADR — D7 executor + prediction-graded ground truth + the bundle), built against the Crawl-A kernel slots.
3. The three live soaks keep running underneath — they are the regression floor for everything above.

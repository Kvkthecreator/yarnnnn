# Rhythm, Expected Output, and Autonomy-as-Witness — a synthesis discourse

**Date**: 2026-06-19
**Status**: Discourse / analysis — NOT canon. Written to get the synthesis right on paper before any FOUNDATIONS or governance-file move. Operator scopes what ratifies.
**Provenance**: the operator's questions across 2026-06-18/19 — "where does the standing obligation / expected output reside? is it in mandate? … shouldn't the open Path-A/B decision be an autonomy + budget handling style? … for full autonomy shouldn't the agent work in FULL without operator intervention? … [the standing brief] is the literal heartbeat / essence of the service operating system … step back, not bounded by existing architecture … yes it's a heartbeat and rhythm, but **equally important is the expected output, which I believe are fundamentally different things we need to explicitly capture for each workspace.**"

> **Correction note (the load-bearing one):** an earlier draft of this discourse said *"budget × pace × expected-output are three facets of one fact."* That was a **category error.** Budget and pace ARE one fact (tempo — ADR-327 proved it). **Expected Output is a separate, orthogonal fact** — the output *contract*, not a rate. This rewrite separates them. The operator caught the collapse; the separation is the point.

---

## TL;DR

The operator declares, per workspace, **four orthogonal things** — two already canon, one needs a prose reframe, one is a genuine gap to build:

| Concept | Answers | Nature | Home | Status |
|---|---|---|---|---|
| **Rhythm** (heartbeat) | *How often do I show up to work?* | a **rate** (tempo) | `_budget.yaml` (governance) | ✅ canon (ADR-327) |
| **Expected Output** | *What am I on the hook to have produced?* | a **contract** (kind + delivery-cadence + bar) | MANDATE `## Expected Output` (prose) + `_expected_output.yaml` (machine sidecar) | ❌ **the gap — to build** |
| **Autonomy** | *Which beats does the operator witness before they bind?* | a **witness dial** | `_autonomy.yaml` (governance) | ⚠️ mechanism canon; **prose framing backwards** |
| **Persona** | *How do I reason?* | voice | IDENTITY.md + principles.md (persona) | ✅ canon |

The crux the operator corrected: **Rhythm and Expected Output are orthogonal, not facets of one rate.** You cannot derive one from the other (proof in §2). They must be captured *separately and explicitly* for every workspace.

---

## 1. Rhythm (the heartbeat) — already canon, just unnamed

The operation's **rate of attention**: how often it wakes, reasons, spends a judgment cycle. This is a *rate* (beats per unit time), and YARNNN already collapsed it correctly.

ADR-327 proved that **budget IS pace**: *"pace was always a budget wearing a frequency costume."* `_pace.yaml` was deleted; tempo became the Reviewer's allocation problem within a declared `amount_usd × window` envelope. The three operator dials (Budget · Autonomy · Persona) are already canonized as the trifecta (ADR-298 D11).

**What's missing is only the name + the synthesis** — that the spend envelope, read as a tempo, is the operation's *heartbeat* (its metabolic rate of attention). This is pure pedagogy: the mechanism is shipped, the word isn't. Zero architecture change.

**Rhythm is governance** (operator declares it, Reviewer reads-not-authors — like budget today) because it is a *ceiling/envelope the agent runs under*, not work the agent produces.

## 2. Expected Output — the orthogonal concept, the genuine gap

The operation's **output contract**: what it is on the hook to *produce* — the *kind* of artifact, the *count/delivery-cadence*, the *bar*. This is a **deliverable contract**, not a rate. It is the **measurable half of the mandate** — *"why we exist"* (compound a corpus) made concrete (*"~2 on-thesis essays a month, anti-slop clean"*).

**Why it is NOT the heartbeat (the orthogonality proof):**
- A trader can wake **every minute** (fast rhythm) and correctly produce **zero trades** for weeks (no output owed when no signal fires). Fast rhythm · no output — *and that is correct behavior.*
- An author can wake **weekly** (slow rhythm) and owe **2 essays a month** (real output). Slow rhythm · definite output.

You cannot derive one from the other. A fast heartbeat does not imply high output; a high output contract does not imply a fast heartbeat. They answer different questions — *how often do I show up* vs *what do I owe when I'm here.* The earlier "three facets of one fact" framing was wrong precisely here: it folded the output contract into the rate, which is why expected-output kept having "no home" — it was being wedged into `_budget.yaml`, where it does not belong.

**Why it has no home today:** ADR-344 made the Reviewer *derive* the owed-output at wake-time (budget × mandate × bar). Derivation is correct as a *floor* (a workspace that declares nothing still gets a standing-obligation check), but a derived-only referent is **unstable and unshared** — the operator and the agent have no declared contract they both point at. That is the direct cause of the author Reviewer's repeated *"what's the production cadence?"* Clarify: it was reaching for a referent that was never declared.

**Home (decided): MANDATE prose + machine sidecar.** Expected Output is the operator's *promise* — intent, not a ceiling — so its human-readable form lives in **`constitution/MANDATE.md` → `## Expected Output`** (survives occupant rotation; the measurable half of the job description; ADR-344 already opened this optional section). A **machine sidecar `_expected_output.yaml`** (the AUTONOMY.md + `_autonomy.yaml` pattern) carries the parseable form the standing-obligation check (ADR-344/DP30) and any conformance gate read reliably. One concern, two faces: human promise in constitution, machine referent alongside.

**Critical: a delivery-cadence + bar, NOT a hard volume quota.** The output contract declares a *rhythm of delivery the floor still gates* ("biweekly essays, on-thesis, anti-slop clean — slot slips if nothing clears the bar"), not a number that must be hit ("ship 2 no matter what"). A quota creates internal pressure to ship marginal work — the exact Goodhart hazard the aperture/floor split (ADR-342/343) forbids externally, now arising internally from a self-imposed target. MANDATE's own alpha-author editorial principle already says this: *"Cadence is a floor, not a ceiling. If I have nothing on-thesis to ship in a given week, the slot goes empty or slips."* The Expected Output inherits that discipline — it is a contract the floor regulates, not a body count.

## 3. Autonomy is the witness dial — mechanism right, prose backwards

The operator's instinct — *"autonomy is almost a given/expected default; the modes are just the permission gate"* — is **literally how the code works.** Verified in `permission.py::resolve_permission`:

- The gate runs *after* the Reviewer has reasoned and **decided to call a primitive** (the tool-call IS the decided act). It then returns:
  - **APPLY** — the decided act runs now (the beat is subconscious).
  - **QUEUE** — the act routes to `action_proposals` and **waits for the operator to witness it before it binds** (`permission.py:21,:44` "operator approves later"). The agent *acted*; the beat *surfaced*.
  - **DENY** — governance-locked, bypass-immune.
- The autonomy mode selects the policy: `autonomous` → APPLY; `bounded` → APPLY under `ceiling_cents`, QUEUE above; `manual` → QUEUE every consequential beat (`review_policy.py:28`).

So **QUEUE has never meant "the agent was blocked below a ceiling."** It means "the agent worked the job, and *this* beat is one the operator chose to witness before it binds." That is a **witness-selector**. The "trust ceiling / approval degree" prose (ADR-249/307) describes the dial from the operator's permission-anxiety, not from what the agent does.

**The reframe (prose, not code):**
> Full autonomy is the default expectation of a judgment seat — it works the whole job in the operator's absence. The AUTONOMY dial does not decide *whether* the agent works; it decides *which beats the operator witnesses before they bind*. `autonomous` = the whole rhythm runs subconsciously (the operator reads the trail at leisure); `bounded`/`manual` = chosen beats surface first. The agent always works the full job.

**This resolves the Path-A/B "open decision."** The author Reviewer asking *"author a compose cadence (B) or feed drafts (A)?"* was **not** correct consent-seeking — it was a *symptom of the missing Expected Output.* With a declared output contract (produce at delivery-cadence R) + `autonomous`, there is nothing to ask: the agent authors its own compose organ and produces at R, and the dial only decides whether each ship auto-binds or surfaces. The Clarify was the agent reaching for the contract that wasn't declared.

## 4. How the four compose (the clean separation of concerns)

A workspace is fully specified by four orthogonal operator declarations + the kernel frame:

- **MANDATE** (constitution) — *why we exist* + the primary action (intent) **+ `## Expected Output`** (the measurable promise: what we owe).
- **`_budget.yaml`** (governance) — *Rhythm*: the rate of attention (spend = tempo).
- **`_autonomy.yaml`** (governance) — *Autonomy*: the witness dial (which beats surface).
- **IDENTITY.md + principles.md** (persona) — *Persona*: how we reason + the rules each act clears (the bar).
- **`_expected_output.yaml`** (machine sidecar) — the parseable form of the MANDATE promise, for the standing-obligation check + conformance.

The standing-obligation check (ADR-344/DP30) becomes sharper: it measures **actual output** (recent fires + ground-truth + what exists) against the **declared Expected Output** (not a derived guess), classifies a shortfall as (A) quiet-world or (B) structurally-can't, and acts — under the witness dial. A *declared* contract makes "behind on the output contract" unambiguous, which is exactly what the current derive-only model lacks.

## 5. Recommended canon moves (minimal — operator scopes)

Cheapest-truest first. (1)–(3) are naming/framing; (4) is the one structural build.

1. **Name the Rhythm (heartbeat).** GLOSSARY + a FOUNDATIONS pointer: the operation's rate of attention; spend-as-tempo (ADR-327) is its declaration. Pure pedagogy.
2. **Name Expected Output as a distinct, first-class concept** — explicitly orthogonal to Rhythm. GLOSSARY entry + the FOUNDATIONS note that a workspace declares *both* a rhythm (rate) *and* an output contract (deliverable), and they do not derive from each other.
3. **Flip the autonomy prose** from ceiling → witness-dial (ADR-249/307 framing + AUTONOMY.md template). No code change; canonizes "full autonomy = works the whole job, dial routes attention"; reclassifies the Path-A/B Clarify as a missing-contract symptom.
4. **Build the Expected Output home** (the one structural move; warrants its own ADR): `MANDATE ## Expected Output` (prose, the promise) + `_expected_output.yaml` (machine sidecar, the referent), as a **delivery-cadence + bar, never a quota**. Wire the standing-obligation check (ADR-344) to read the *declared* contract, falling back to derivation only when undeclared. Bundle templates (trader + author) ship their own Expected Output as the worked instance.

**Validate (4) before it ratifies** (evidence-before-canon, the pattern that's held this arc): a **fresh** author workspace with a declared Expected Output (delivery-cadence R, `autonomous`), left to run — does the agent author its own compose organ and produce at R *without the spurious Clarify*? That is the falsifiable proof. (The current yarnnn-author can't be the test bed — its revision DAG is contaminated and the Reviewer reads history, per the 2026-06-18 finding.)

## 6. What this does NOT change

- The aperture/floor split (ADR-342/343) — the floor still gates every beat; Expected Output is a floor-gated delivery-cadence, not a quota that pressures the floor (§2).
- The permission gate mechanism (ADR-307) — already correct; only its prose framing flips (§3).
- The five-root topology (ADR-320) — Rhythm + Autonomy stay governance; Expected Output's prose is constitution (the promise), its sidecar is governance-adjacent machine state. No new root.
- The standing-obligation self-check (ADR-344/DP30) — unchanged in shape; it gains a *declared* referent to measure against, sharpening the (A)/(B) classifier.

---

## Appendix — receipts

| Claim | Receipt |
|---|---|
| Budget = pace (Rhythm) already shipped | ADR-327 "pace was always a budget wearing a frequency costume"; `_pace.yaml` deleted; `_budget.yaml` header "Replaces _pace.yaml — tempo is the Reviewer's allocation problem" |
| Trifecta already canon | ADR-298 D11 (Budget · Autonomy · Persona) + cadence-and-wakes §1a |
| Rhythm ⟂ Expected Output (orthogonality) | trader: fast wake / zero output (correct); author: slow wake / definite output — neither derives the other (§2) |
| Gate runs after the agent decides; QUEUE = acted-and-waits | `permission.py:162-256` (`resolve_permission` called before dispatch on a primitive the Reviewer already chose); `:21,:44` QUEUE = "route to action_proposals; operator approves later" |
| Autonomy mode selects witness policy | `review_policy.py:28` bounded = "auto-approve up to ceiling_cents, queue above"; `permission.py:236` "manual/bounded → queue; autonomous → apply" |
| Expected Output is derived, not declared (the gap) | ADR-344 §2 (derived from budget×mandate×bar); MANDATE `## Expected Output` optional, never required, no machine sidecar |
| Cadence-not-quota already in MANDATE | alpha-author MANDATE editorial: "Cadence is a floor, not a ceiling… the slot goes empty or slips" |

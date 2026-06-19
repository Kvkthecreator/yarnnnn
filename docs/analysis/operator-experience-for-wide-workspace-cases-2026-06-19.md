# The operator experience for a wide range of workspace cases — a discourse

**Date**: 2026-06-19
**Status**: Discourse / analysis — **NOT canon, NOT code.** Written to map the problem on paper before any surface/registry/ADR move. Operator scopes what ratifies.
**Hat**: A-facing question (real-operator surfaces), explored in Hat-B discipline (stress-test against observed substrate + named forks before committing canon).
**Provenance**: the operator's carry-over ask — *"now that the backend operating-contract model exists (Rhythm / Expected Output / Witness / Persona + the standing-obligation loop), how does the OPERATOR see, set, and tune it — and how does the UX hold up across a wide, heterogeneous range of workspace types (trader, author, marketer, e-commerce, A&R, designer, research, and ones we haven't imagined)?"*

> **Discipline note.** This doc does not reinvent the surface canon. It grounds every claim against the live registry (`api/services/kernel_surfaces.py`), the live content-shapes (`web/lib/content-shapes/`), the live program bundles (`docs/programs/*/SURFACES.yaml`), and the surface ADRs (297 / 312 / 331 / 338 / 340 / 341 / 345). Where a claim is a receipt it carries its file:line; where it is a fork it is named as one, not resolved silently.

---

## 0. TL;DR

The backend now specifies a workspace by **four orthogonal operator declarations** (the operating contract, ADR-342→345):

| Declaration | Answers | Substrate home | FE home today |
|---|---|---|---|
| **Rhythm** (`_budget.yaml`) | how often do I work? | `governance/` | ✅ System Settings → Governance → Budget pane (live inline editor) |
| **Witness** (`_autonomy.yaml`) | which beats does the operator witness before they bind? | `governance/` | ✅ System Settings → Governance → Autonomy pane (live inline editor) |
| **Persona** (`IDENTITY.md` + `principles.md`) | how do I reason + the bar? | `persona/` + `constitution/` | ✅ Workspace Settings → Constitution panes (read + edit-via-chat) |
| **Expected Output** (`MANDATE ## Expected Output` + `governance/_expected_output.yaml`) | what am I on the hook to produce when I work? | `constitution/` prose + `governance/` sidecar | ❌ **homeless** — backend-wired, **zero FE** |

**The single concrete FE gap is Expected Output (ADR-345).** It is wired into the wake envelope (`reviewer_envelope.py:102`, `reviewer_agent.py:682`) and read by the standing-obligation check (DP30), but the operator has **no surface to declare, see, or tune it.** Three of the four declarations already have coherent, live homes after ADR-341. The fourth is the one structural build.

**The wide-use-case question has a reassuring answer and one real risk.** The kernel-slots / program-weights contract (ADR-312) is genuinely program-neutral and *already* survives a 5-program heterogeneity sample (trader, author, commerce, prediction, defi) — including programs that declare **zero** program-shaped Home slots. The compositor seam (ADR-225/312) is the right scaling primitive and it is not the thing that breaks. The risk is narrower and more interesting: **the four-declaration contract is currently a fragmented mirror set (four panes in two doors), not a composition.** ADR-340's own principle ("compose few") says the operator's *standing acts* deserve compositions; "specify what this operation is and owes" is a standing act with no composition. That is the higher-altitude FE move, and it is where Expected Output should land — not as a fifth lonely pane.

The recommended minimal set (detail in §7):
1. **Build the Expected Output mirror** (the one forced build) — content-shape + pane, mirroring the autonomy/budget editor pattern.
2. **Decide its door** (the one genuine fork — §4): Governance (it's governance-region substrate) vs Constitution (its prose half is the mandate's promise). Recommendation inside.
3. **Resolve the live canon contradiction** (§3) — ADR-341 D2 says "zero inline substrate editors in Settings" but autonomy/budget panes *are* inline editors. Expected Output's editability decision can't be made coherently until this is named.
4. **(Optional, higher-altitude) the contract composition** — a single "what this operation is + owes + how it's governed" reading that the four mirrors hang under. This is the ADR-340 "compose few" move; it future-proofs the wide-use-case scaling far more than any per-program FE work.

---

## 1. Where the contract lives today (the receipts)

### 1.1 Three of four declarations are home — and the home is coherent (ADR-341)

ADR-341 (2026-06-18, *after* the ADR-340 program and *not in the carry-over's reading list*) split the single System Settings door into **two doors**, each internally coherent and **backed by the ADR-320 permission topology**:

- **System Settings** (`/settings`) — *the OS governing the agent*. `governance/` (operator-only ceilings the agent runs under but **cannot write**). Panes: **Governance** group = **Autonomy · Budget**; General = Billing · Usage · Account. (`kernel_surfaces.py` `settings`, `autonomy`, `budget` → `pane_of: "settings"`, `pane_group: "Governance"`.)
- **Workspace Settings** (`/workspace-settings`) — *what this operation is*. `constitution/` + `operation/` + `persona/` (the agent **amends** these). Panes: **Constitution** = Mandate · Identity · Principles; **Operation** = Program; **Perception** = Connectors · Sources. (`kernel_surfaces.py` `mandate`/`identity`/`principles`/`program`/`connectors`/`sources` → `pane_of: "workspace-settings"`.)

Mapping the operating-contract vocabulary onto this:

- **Rhythm** = System Settings → Governance → **Budget**. Live inline editor (`budget.ts` `WRITE_CONTRACT='configuration'`, `setBudget()`).
- **Witness** = System Settings → Governance → **Autonomy**. Live inline editor (`autonomy.ts` `setDelegation/setPause/setNeverAuto`).
- **Persona** = Workspace Settings → Constitution → **Identity + Principles**, read-mostly with edit-via-chat (ADR-341 D2).

So the door structure *already teaches the lock model for free* (ADR-341 §4): governing-the-agent vs configuring-the-operation maps to governance-region (agent-can't-write) vs constitution/operation/persona (agent-amends). This is a real, recent, well-grounded structure. **The wide-use-case discourse should build on it, not relitigate it.**

### 1.2 Expected Output is the homeless fourth (the gap)

ADR-345 shipped Expected Output as **backend-only**:

- `governance/_expected_output.yaml` is the machine sidecar (`workspace_paths.py:90` `GOVERNANCE_EXPECTED_OUTPUT_PATH`).
- It loads into the wake envelope (`reviewer_envelope.py:102` `("expected_output_yaml", GOVERNANCE_EXPECTED_OUTPUT_PATH)`), reaches `ReviewerContext.expected_output_yaml` (`occupant_contract.py:151`), and renders in the persona-frame as *"the operator's output contract (what you owe; a floor-gated cadence, NOT a quota)"* (`reviewer_agent.py:682-686`).
- The standing-obligation check (DP30) reads-declared-then-derives against it.

**But on the FE it does not exist:**
- No `web/lib/content-shapes/expected-output.ts` (the directory has 14 shapes; this is not one).
- No registry entry, no pane, no `pane_of`, no Home slot.
- The two FE references to `expected_output` are the *deliverable metadata chrome* (`KernelDeliverableMetadata.tsx`, `DeliverableMiddle.tsx`) — an unrelated, pre-existing field name collision, **not** ADR-345's contract.

So the operator can declare Rhythm, Witness, and Persona through surfaces, but **cannot declare or see the one thing ADR-345 named as "the measurable half of the mandate."** Its only authoring path today is chat → `WriteFile` to `governance/_expected_output.yaml` (and the prose half to `MANDATE ## Expected Output`), which is exactly the kind of harness-dependency ADR-338 D1 named as the failure mode ("a real operator cannot do what the developer harness did").

This is the **forced build**. Everything else in this discourse is framing around it.

---

## 2. The wide-use-case stress test: does one kernel surface set serve heterogeneous programs?

The carry-over's question 2 — *"how does a single compositor + kernel surface set serve a WIDE range of workspace cases without per-program FE forks?"* — is testable **right now** against the 5 live bundles. I ran it.

### 2.1 The contract is genuinely program-neutral (the reassuring half)

The kernel-slots / program-weights contract (ADR-312 D2 + amendments) holds across the sample:

| Program | Declares Home `program_sections`? | Slot #2 (hero) | Slot #4 (entities) |
|---|---|---|---|
| **alpha-trader** | yes (7 → being reshaped to 2) | money-truth | positions |
| **alpha-author** | yes (exactly 2) | `AuthorHero` (voice holding/drifting) | `AuthorPieces` (corpus) |
| **alpha-commerce** | **no** | — (kernel-universal slots only) | — |
| **alpha-prediction** | **no** | — | — |
| **alpha-defi** | **no** | — | — |

The fact that **three of five programs declare no program-shaped Home slots** and still render a coherent Home (constitution band + kernel-universal decision-queue / recent-artifacts / judgment-trail, each self-hiding when empty per the D2 amendment) is the strongest evidence the contract scales. A new program that declares *nothing* gets a working, honest Home for free. A program with a strong ground-truth signal (trader's P&L, author's voice) declares its two slots and gets a tailored hero. **There is no per-program FE fork** — the I5 invariant (`compositor.md`: "kernel code never branches on `program_slug`") is intact, enforced by gate.

**Conclusion on Q2/Q3: the compositor is not where the wide-use-case problem breaks.** The kernel-universal/program-declared/compositor-resolved partition is already drawn and already proven across heterogeneity. What is kernel-universal: the slot set, the four-declaration governance/constitution surfaces, the standing loop (Decide/Read/Dwell/Tune/Amend/Setup). What is program-declared: the two Home slots, pinned tasks, chat chips, phase banners, watch-source declarations, the autonomy *default*. What is compositor-resolved: which component fills each slot. This holds for trader, author, and the three programs that lean entirely on kernel defaults.

### 2.2 Where it actually strains (the honest half)

The strain is **not** at the Home composition. It is at **the contract-declaration surfaces**, and it has three faces:

**(a) The contract is mirrored, not composed.** The four declarations are four panes across two doors. ADR-340 D1's own principle is "**mirror once, compose few**" — every substrate concern earns one mirror, and the operator's *standing acts* are carried by compositions. "Specify what this operation is and what it owes" is a standing act (it is literally ADR-340's **Tune** + **Amend** acts), but it has **no composition** — only four mirrors the operator must assemble in their head across two settings doors. The author Reviewer's repeated *"what's the production cadence?"* Clarify (the ADR-345 trigger) is the agent-side symptom of the same gap: nobody — operator or agent — has a single place that says "here is the whole contract." Expected Output landing as a *fifth lonely pane* would deepen this fragmentation, not resolve it.

**(b) Expected Output is *kind*-shaped, and kinds are wildly heterogeneous.** Rhythm is a scalar (amount × window). Witness is an enum + a guard list. Persona is prose. But Expected Output is *"kind + delivery-cadence + bar"* — and the **kind** ranges enormously: a trader owes *trades when signal fires* (event-shaped, possibly zero for weeks — correct); an author owes *~2 on-thesis essays/month* (count + cadence); a marketer owes *a campaign per launch* (event-shaped); an A&R scout owes *a shortlist per cycle* (recurring digest); a designer owes *N concepts per brief* (on-demand). A single rigid form ("how many of what, how often") fits the author and breaks on the trader. **This is the real wide-use-case design problem** — not the Home, the Expected Output editor. (§5 addresses it.)

**(c) A live canon contradiction blocks the editability decision.** ADR-341 D2 + D3 assert *"Settings is read-mostly with zero inline substrate editors"* (citing ADR-244 D7). But the **autonomy and budget panes are live inline editors** — `autonomy.ts` ships `setDelegation/setPause/setNeverAuto`, `budget.ts` ships `setBudget`, both routing through `writeShape(... WRITE_CONTRACT='configuration')`. The reconciliation that the codebase actually embodies (and that is correct): **governance-region panes edit inline** (scalar dials, agent-can't-write, safe to expose a control), **constitution/persona panes are read + edit-via-chat** (prose the agent co-authors, ADR-206 D6). ADR-341 D2's blanket "zero inline editors" is **stale** — it describes only the constitution panes it was reasoning about, and over-generalizes. **This must be named before Expected Output's editability is decided**, because Expected Output straddles the line: its sidecar is governance-region (→ inline-editable by the established pattern), its prose is constitution-region (→ edit-via-chat). (§4.)

---

## 3. The canon contradiction, isolated (must resolve first)

> **Claim A** (ADR-341 D2): *"substrate authoring stays in chat/Files; Settings is read-mostly with zero inline substrate editors"* — citing ADR-244 D7.
> **Claim B** (live code): `autonomy.ts` and `budget.ts` are inline editors with `WRITE_CONTRACT='configuration'` and `set*` mutators that `writeShape` directly from the pane.

These cannot both be unqualifiedly true. The code is the ground truth (substrate-receipts discipline: the running system wins over the doc claim). The honest reconciliation, which the code already follows:

**The editability of a governance/constitution pane is determined by its substrate region, not by a blanket Settings rule:**
- **`governance/` panes** (Rhythm, Witness) — operator-only ceilings the agent **cannot write** (ADR-320). A scalar dial the operator owns exclusively is *safe and correct* to expose as an inline control. These ARE inline editors. ✅ (matches code)
- **`constitution/` + `persona/` panes** (Mandate, Identity, Principles) — prose the agent **co-authors** (ADR-320 amends). Inline editing would create a two-writer race with the agent's revision chain; ADR-206 D6 routes authoring through chat/Files. These are read + edit-via-chat. ✅ (matches code)

**Recommended canon fix (small, in the Expected-Output ADR):** amend ADR-341 D2's "zero inline editors" to the region-conditional rule above. It is not a new decision — it is naming what the code already does, removing a stale over-generalization that would otherwise make Expected Output's editability incoherent.

---

## 4. The one genuine fork: which door does Expected Output live behind?

Expected Output is the one declaration that **straddles** the two-door split:

- Its **machine sidecar** `governance/_expected_output.yaml` is, by path, **governance-region** → System Settings → Governance, alongside Budget/Autonomy. (It loads via the *governance* envelope path, `GOVERNANCE_EXPECTED_OUTPUT_PATH`.)
- Its **prose half** `MANDATE ## Expected Output` is **constitution-region** → Workspace Settings → Constitution, alongside the Mandate it's a section of. (ADR-345: "the measurable half of the mandate"; ADR-344 opened it as an optional MANDATE section.)

This is a real fork because the two-door split (ADR-341) is *substrate-region-driven*, and Expected Output's two faces sit in two regions. The options:

**Option A — Governance door (with Budget + Autonomy).** Rationale: the *editable* face is the sidecar, which is governance-region; the standing-obligation check reads it as governance state; it sits naturally next to Rhythm and Witness as "the dials." This groups the **three machine-readable governance declarations** (Rhythm/Witness/Expected-Output) in one place — arguably "the operating contract" *is* the Governance group. Risk: it visually separates Expected Output from the MANDATE prose it's the measurable half of, weakening the "promise" framing ADR-345 cared about.

**Option B — Constitution door (under Mandate).** Rationale: ADR-345 is emphatic that Expected Output is *the mandate's promise* — "why we exist made concrete." Co-locating it with Mandate (its prose half *is* a MANDATE section) keeps the promise legible. Risk: the sidecar is governance-region substrate, and an editable control in the Constitution door (which is otherwise read + edit-via-chat) would be the only inline editor there — inconsistent with the door's character, and it'd cross the region line the door structure teaches.

**Option C — neither door yet; Expected Output gets a Home composition (the "compose few" move).** Treat the whole four-declaration contract as one *composition surface* (ADR-340 D1: one surface ↔ one operator act = "specify/tune what this operation is and owes"). The four mirrors stay where they are (Rhythm/Witness in Governance, Persona in Constitution); a new **composition** reads all four (+ the standing-obligation actual-vs-owed read) into one "the operating contract" view, and *that* is where Expected Output is primarily declared/tuned, deep-linking down to the mirrors. This is more work but is the only option that resolves §2.2(a) (the contract is mirrored-not-composed) and future-proofs the wide-use-case scaling.

**My recommendation: A for the mirror (build the editable Expected Output pane in the Governance group, next to Budget/Autonomy — it's the third machine-readable governance dial and the editor pattern is identical), and C as the deferred-but-named horizon (the contract composition is the right ADR-340-shaped move, but it should be evidence-forced after the mirror exists and is used).** B loses on the region-consistency argument. This is the fork I most want the operator's steer on.

---

## 5. The harder design problem: an Expected-Output editor that survives heterogeneity

Even once the door is chosen, the editor itself faces §2.2(b): **"kind + delivery-cadence + bar" ranges across program shapes more than any other declaration.** Three candidate shapes:

**Shape 1 — Free prose only (no structured editor).** Expected Output is authored as prose in `MANDATE ## Expected Output` via chat; the `_expected_output.yaml` sidecar is the agent's distillation of that prose (the InferContext pattern, ADR-324). The pane is **read-only** (shows the declared contract + the standing-obligation actual-vs-owed read). Pro: zero heterogeneity problem — prose fits trader and author equally. Pro: matches the constitution-region edit-via-chat character (→ favors door B). Con: no crisp machine referent the operator directly controls; relies on the agent's distillation being faithful.

**Shape 2 — Structured, program-declared form.** The bundle's `SURFACES.yaml` declares the Expected-Output *form shape* (the compositor pattern, exactly how Home slots work): trader declares an event-shaped form ("trades when signal fires; no count"), author declares a count+cadence form ("N pieces per window, bar = anti-slop/voice"). The kernel renders whatever form the program declares; programs that declare nothing get a generic kind+cadence+bar form. Pro: heterogeneity handled by the *same* program-weighting mechanism that already works for Home (§2.1) — provably scalable. Pro: the operator gets a real control. Con: more compositor surface; another thing bundles must author.

**Shape 3 — Generic structured form, kind-agnostic.** One kernel form: `kind` (free text), `delivery_cadence` (enum: per-event / weekly / biweekly / monthly / on-demand), `bar` (free text or principle deep-link). No program declaration. Pro: simplest; one form everywhere. Con: the `per-event` / no-count case (trader) and the count case (author) are awkward in one form — the form must make "zero is correct" first-class or it reads as a quota (the exact Goodhart hazard ADR-345 forbids).

**My lean: Shape 1 for v1 (prose-authored, read-only pane showing declared-vs-owed), with Shape 2 as the earned upgrade** if operators find prose-only insufficient. Shape 1 is cheapest, dodges the heterogeneity trap entirely, matches the "promise" framing, and the read-only actual-vs-owed view is the high-value part (it makes the standing-obligation check *visible* to the operator — the thing that's currently invisible). Shape 2 generalizes cleanly later *because the mechanism already exists.* This lean interacts with the door fork: Shape 1 (prose, read-only) leans door B; a structured editor (2/3) leans door A. **So §4 and §5 are coupled** — see the question set.

---

## 6. Onboarding / Setup for the heterogeneous future (Q4)

ADR-331 already answers most of this and is sound: `/setup` is a **Sequence rendering over `api.workspace.getState()`** with **no stored wizard state** — five derived steps (pick program → author constitution → connect → bring in reality → first artifact). It is program-neutral by construction (it reads activation state, not program identity) and re-enterable (Migration-Assistant property).

The four-declaration contract maps onto Setup's existing steps with **one addition**:

- **Pick program** → activation; the bundle ships its Rhythm (`minimum_pace`), Witness (autonomy default, ADR-312 D7), and Persona (reference-workspace) defaults. So three of four declarations arrive *pre-filled by the program* — the operator tunes, doesn't author from scratch. This is the right default for the wide-use-case future: a new program is a *flow-declaration set* (ADR-332/DP26) that includes contract defaults.
- **Author constitution** → Mandate + Identity. **This step should grow the Expected-Output prose declaration** (it's a MANDATE section). If Shape 1 (prose) wins, Expected Output is authored *here, in context*, exactly as ADR-338 §7.3 / ADR-340 D7 prescribe ("teach the consequence at the moment of first use"): "what will this operation produce, and on what cadence?" asked once, in the guided flow, then left as a Workspace/System Settings reference pane.
- The other steps (connect, harvest, first artifact) are unchanged.

So the heterogeneous-onboarding answer is: **the program supplies contract defaults at activation; `/setup` walks the operator through tuning them once; the settings panes are the return-to-tune reference.** No new onboarding system. The only Setup change is surfacing Expected-Output authoring in the "author constitution" step — and only if Shape 1 wins. This is the cheapest possible heterogeneity story because it pushes program-specific contract shape into the bundle (where ADR-222 says program-specific things belong) and keeps `/setup` kernel-generic.

---

## 7. Recommended minimal FE/UX move set

Ordered cheapest-truest-first, matching the arc's evidence-before-canon discipline.

1. **Resolve the canon contradiction (§3)** — one paragraph in the forthcoming Expected-Output ADR: governance-region panes edit inline; constitution/persona panes read + edit-via-chat. Names what the code does; unblocks the editability decision. *(No code; doc-only.)*

2. **Build the Expected Output mirror (the forced build, §1.2)** — `web/lib/content-shapes/expected-output.ts` (parse/serialize/`useExpectedOutput`, mirroring `autonomy.ts`/`budget.ts`) + a pane in the chosen door (§4 fork) + registry entry. **Critically: the pane's headline value is the read — "owed vs produced," the standing-obligation check made visible** — not just the editor. This is the single change that lets a real operator do what the harness does.

3. **Wire Expected-Output authoring into `/setup` step 2** (§6) — only if Shape 1 (prose) wins; surfaces the declaration at the moment of first use, per ADR-340 D7.

4. **(Deferred, named) the contract composition (§2.2a, §4 Option C)** — an ADR-340-shaped "operating contract" composition surface that reads all four declarations + the actual-vs-owed standing-obligation state into one view, deep-linking to the four mirrors. This is the real wide-use-case future-proofing (it's the "compose few" act the contract currently lacks), but it should be **evidence-forced after the mirror is used** — the same two-stage discipline ADR-340 itself followed (mirror first, measure the gap, then compose). Do not build it speculatively.

**What this set explicitly does NOT do** (boundary discipline):
- Does not relitigate the two-door split (ADR-341) or the kernel-slots contract (ADR-312) — both are sound and proven across the 5-program sample.
- Does not add a per-program FE fork — Expected-Output heterogeneity is handled by prose (Shape 1) or the existing program-weighting mechanism (Shape 2), never by `if program_slug`.
- Does not build a new onboarding system — `/setup` already covers it.
- Does not turn Expected Output into a quota control — the pane shows a *floor-gated cadence* and makes "zero is correct" first-class (ADR-345's Goodhart guard).

---

## 8. Open questions for operator steer

1. **The door fork (§4)** — Governance (A, with the dials) vs Constitution (B, with the mandate) vs deferred-composition (C). My rec: A for the mirror, C as the named horizon.
2. **The editor shape (§5)** — prose-only read-only pane (Shape 1) vs structured program-declared form (Shape 2) vs generic structured form (Shape 3). My rec: Shape 1 for v1. **Coupled to #1**: Shape 1 → door B leans; structured → door A leans.
3. **The composition horizon (§7.4)** — is the "operating contract" composition worth committing to as a *named deferred* now (so the mirror is built knowing it'll hang under a composition later), or left fully open until the mirror's usage forces it?
4. **Scope of this session's next step** — write the Expected-Output FE ADR (doc-first), or prototype the mirror pane first and let the build inform the ADR? (The arc's pattern has been doc-first; the carry-over asked for discourse-first, which this is.)

---

## 9. Operator decision (2026-06-19) — the answers, and what the combination forces

**The operator chose the opposite-corner combination from the discourse's lean:**

| Fork | Operator pick | Discourse lean |
|---|---|---|
| **Door (§4)** | **B — Constitution, under Mandate** | A (Governance) |
| **Shape (§5)** | **Shape 2 — structured, program-declared** | Shape 1 (prose, read-only) |

**This is coherent and it refutes one of the discourse's own claims.** §2.2(c) / §5 asserted "structured editor → leans door A (governance), because the only inline editors today are governance-region." The operator's pick says: a **structured editor can live in the Constitution door** — which means the rule "editability is determined by substrate region" (§3) needs a sharper third clause, not just two:

- **`governance/` panes** — operator-only ceilings the agent can't write → **inline scalar dials** (Rhythm, Witness). ✅
- **`constitution/`+`persona/` *prose*** — agent co-authored → **read + edit-via-chat** (Mandate prose, Identity, Principles). ✅
- **`constitution/` *operator-declared structured contract*** (NEW class, surfaced by this pick) — the operator's **declaration of what the operation is/owes**, structured, **operator-authored not agent-co-authored** → **inline structured editor, in the Constitution door.** Expected Output is the first member.

The discrimination that resolves the §3 contradiction cleanly is **not** "governance = editable, constitution = read-only." It is **"operator-authored = inline-editable (scalar or structured); agent-co-authored = edit-via-chat."** Rhythm/Witness are operator-authored scalars (inline). Mandate-prose/Identity/Principles are agent-co-authored prose (edit-via-chat). Expected Output is an **operator-authored structured contract** (inline structured) that happens to live in the constitution region because it *is the operation declaring itself*, not the OS governing the agent. The two-door split (governing-the-agent vs configuring-the-operation, ADR-341) still holds — Expected Output is configuring-the-operation, hence Workspace Settings / Constitution, hence door B. The operator's pick is **more faithful to ADR-341's own object-distinction than door A would have been** (Expected Output is not an OS-governance ceiling; it's part of what the operation *is*).

**What Shape-2 forces (the program-declared form).** The Expected-Output editor's *form shape* is declared by the bundle's `SURFACES.yaml`, resolved by the compositor — the **same mechanism** as Home slots (§2.1), so the heterogeneity is handled by a proven primitive, no `if program_slug`. Concretely:
- A new compositor slot (call it `expected_output.form` in `SURFACES.yaml`) declares the form's fields per program: author = `{count, window, bar→principles}`; trader = `{trigger: per-event, no-count, bar→risk-envelope}`; a program that declares nothing gets a **generic kernel fallback form** (the Shape-3 form becomes the *default*, not the only option — Shape 2 subsumes Shape 3).
- The pane still **headlines the read** (owed-vs-produced, the standing-obligation check made visible) — the editor is below it. The read is kernel-universal; only the *editor form* is program-declared.
- The "zero is correct" / floor-gated-not-quota guard (ADR-345) is enforced at the form level: an event-shaped form (trader) has no count field to miss, so it *cannot* render as a quota; a count-shaped form (author) labels the count as a floor with explicit "slips if nothing clears the bar" copy.

**Combined consequence for the build (supersedes §7's lean):**
1. **§3 canon fix gets the sharper rule** — operator-authored (inline) vs agent-co-authored (edit-via-chat), not governance vs constitution. This is the load-bearing reframe; it must land in the Expected-Output ADR and amend ADR-341 D2.
2. **The mirror is built in Workspace Settings → Constitution, under Mandate** — read-headline (owed-vs-produced, kernel-universal) + program-declared structured editor form below.
3. **A new compositor slot** `expected_output.form` (bundle-declared, kernel-fallback) — the heterogeneity primitive. alpha-trader + alpha-author ship their form declarations as the worked instances (matching how they ship Home slots today).
4. **`/setup` step 2** ("author constitution") gains the Expected-Output declaration in-context — now a *structured form* prompt, not prose (per the Shape-2 pick), still taught-at-first-use (ADR-340 D7).
5. **The contract composition (§4 Option C)** remains the named-deferred horizon — but the operator's door-B pick means Expected Output is *already* co-located with Mandate, so the "mirrored-not-composed" gap (§2.2a) is partially pre-resolved (the constitution door already gathers Mandate + Identity + Principles + Expected Output = three of four declarations in one door; only Rhythm/Witness sit in the other door). The composition is now a *smaller* future move: unite the two doors' contract views, not assemble four scattered panes.

This is a stronger resting point than either single-rec because it (a) resolves the §3 contradiction with a sharper, truer rule, (b) keeps Expected Output legible as the mandate's promise, and (c) handles heterogeneity with the already-proven program-weighting mechanism instead of betting on prose-distillation fidelity.

---

## 10. The bigger reframe (2026-06-19) — collapse to one Settings door; account goes to the UserMenu

After the door/shape decision, the operator surfaced a **deeper discomfort with the existing surface allocation itself**: *"the governance sub-group should actually be in Workspace [Settings]."* Pulling that thread revealed a live seam error in the current canon and a cleaner resolution than ADR-341 reached. **This supersedes the §9 framing materially** and is the dominant recommendation of this discourse.

### 10.1 The live seam error (ADR-341 ⟂ ADR-346)

There are, as of today, **three** surfaces dealing with "operating the operation," and two of them disagree:

- **ADR-341** (2026-06-18) files **Governance (Autonomy + Budget) under System Settings**, on the `governance/`-can't-write permission line.
- **ADR-346** (Proposed 2026-06-19, this arc) §7 names the **Operation surface** as *"the natural read/tune home"* for the **Rhythm · Expected Output · Witness** triad — i.e. it wants Rhythm + Witness in the operation neighborhood, **not** in System Settings.

So canon today has the triad's stated natural home (Operation/Workspace) contradicting where two of its three members are filed (System Settings). The operator's discomfort was the system reporting this contradiction. (Receipt: `kernel_surfaces.py` `autonomy`/`budget` → `pane_of: "settings"`, `pane_group: "Governance"`; ADR-346 §7 lines 84–86.)

### 10.2 The false trichotomy ADR-341 embodied

ADR-341's case rested on "two genuinely different objects: the OS governing the agent vs the operation." The collapse shows that was a **mis-grouping** — there are three things, and ADR-341 split them on the wrong line:

1. **The human / account** — billing, usage, sign-in. Belongs to the **principal**, not to any workspace. Identical across every workspace the human owns. **Home: the UserMenu** (top-right avatar — already account-only per ADR-340 D3, lines 71–72; already holds Billing + Sign-out).
2. **The operation** — Constitution · Contract · Program · Perception. Per-workspace, changes per program. **Home: one Settings door.**
3. **The phantom "System governs the agent" object** — ADR-341 manufactured this by **borrowing Governance (Autonomy/Budget) from the operation** so the System door would hold something besides account. Autonomy/Budget are not machine config; they are *how this operation runs* (a trader runs autonomous/fast, an A&R scout manual/weekly — as per-operation as the mandate). The `governance/`-can't-write substrate fact is a **permission detail, not an operator-facing object boundary**: operators do not navigate by "can the agent write this?"

Remove the borrowing and the System door has nothing operation-shaped left. It dissolves.

### 10.3 The decided resolution — one door + UserMenu

**Operator decision (§8-followup): collapse to one Settings door.**

- **UserMenu** (top-right avatar) = the human/principal: Profile · Billing · Usage · Sign out. *(Completes its existing ADR-340 D3 job — account-only — by absorbing the last machine-level panes.)*
- **Settings** (the one door — formerly Workspace Settings) = the whole operation, grouped:
  - **Constitution** — Mandate · Identity · Principles
  - **Contract** — Rhythm (Budget) · Witness (Autonomy) · **Expected Output** *(the §4 door-fork is now moot: with one door, Expected Output's "which door?" question dissolves — it sits in the Contract group next to its two siblings, and beside the Mandate it's the measurable half of)*
  - **Operation** — Program
  - **Perception** — Connectors · Sources

This **finishes ADR-340 D4's original instinct correctly.** ADR-340 D4 tried to kill the "which door?" guess with one System Settings door; ADR-341 reintroduced the guess by splitting into two. The single door felt wrong not because it was *one* door but because it **lumped the account with the operation**. Pull the account to where the human lives (UserMenu) and one door is exactly right.

### 10.4 What it supersedes / harmonizes

- **Supersedes ADR-341 D1 (two doors), D3 (the `configure` tier holding two doors), D6 (pane re-homing into System Settings).** The two-door split is reversed; one operation-Settings door remains.
- **Harmonizes ADR-346.** The heartbeat-band forward-pointer (ADR-346 §7) now lands cleanly: Rhythm · Witness · Expected Output all live in the one door's **Contract** group, and the Operation surface's future band reads them from one neighborhood instead of straddling two doors.
- **Preserves the §3 / §9 editability rule** — operator-authored panes edit inline (Contract group: scalar dials + the structured Expected-Output form), agent-co-authored prose edits via chat (Constitution group). The rule no longer maps to *which door* (there's one); it maps to *which group/pane within the door*. **The rule gets cleaner, not weaker.**
- **Preserves ADR-312 D5** — the constitution stays first-class on the Home band; the Settings Constitution group remains the read/manage destination (unchanged from ADR-341 D2's realization).
- **Cost paid (named honestly):** ADR-341's claim that "the door structure teaches the lock model for free" (ADR-320 permission topology mirrored in the sidebar) is **given up** — Contract(can't-write) sits beside Constitution(can-amend) in one door. Assessment: that pedagogy was a post-hoc rationalization of a substrate fact, not a real operator need. The lock model is taught by the consent line (ADR-338 D3) and the autonomy pane's own copy, not by door membership. Small cost; the gain (one coherent operating-contract door, no "which door?" guess, ADR-346 harmonized) is larger.

### 10.5 Revised build set (supersedes §7)

1. **Resolve §3 with the operator-authored-vs-agent-co-authored rule** (now per-pane, not per-door). Doc.
2. **Collapse the two doors → one** — `kernel_surfaces.py`: delete the `settings` container; re-parent `autonomy`/`budget` → the one door's Contract group; move billing/usage/account → UserMenu; collapse the `configure` launcher tier to one Settings row; consider renaming `workspace-settings` → `settings` (Singular Implementation: it's now *the* settings door, the obvious name). Amend ADR-341.
3. **Build the Expected Output mirror** in the Contract group — read-headline (owed-vs-produced) + program-declared structured form (Shape 2) + the new `expected_output.form` compositor slot; trader + author ship worked instances.
4. **`/setup` step 2** gains the structured Expected-Output declaration in-context.
5. **The Operation surface (ADR-346) is the composition** the §4-Option-C horizon pointed at — already Proposed today; its §7 heartbeat band becomes buildable once Expected Output's pane + sidecar exist. The "operating contract composition" is **not a new surface to invent** — it's ADR-346's heartbeat band, fed by the now-unified Contract group.

This reframe is why the operator's "I wasn't comfortable with the allocation" was load-bearing: it wasn't a preference, it was the correct read of a seam ADR-341 cut on the wrong axis, now corrected to **machine-vs-operation (with the machine going to the human's UserMenu)** instead of **agent-can-write-vs-can't.**

---

## 11. Open questions after the reframe (for operator steer)

1. **Rename `workspace-settings` → `settings`?** With one door, "Workspace Settings" vs "Settings" is a naming call. Singular Implementation leans toward `settings` (the obvious name for the only door); but `workspace-settings` is already the live slug and "Settings" was the dissolved System door's title. My lean: rename to `settings` and let the dissolved door's slug die.
2. **UserMenu scope** — ~~does Usage belong in UserMenu or the Contract group?~~ **DECIDED (2026-06-19, operator-delegated to Claude): Usage → UserMenu, with Billing + Account.** Substrate receipt: the Usage endpoints are **`user_id`-scoped, not workspace-scoped** — `/user/limits` + `/user/usage-detail` call `get_usage_summary(client, user_id)` / `get_usage_detail(client, user_id)` (`api/routes/integrations.py:1811,1862`), returning the human's `balance_usd` / `raw_balance_usd` / `spend_usd` (the ADR-171/172 account balance: signup grant + top-ups + Pro reset, netted against total token spend). Usage is the **human's spend ledger**, the same account-level axis as Billing (which tops up that same balance) — both belong to the principal, hence UserMenu. **The per-operation burn signal is NOT lost**: the Contract group's Budget/Rhythm pane already shows *this operation's* `_budget.yaml` envelope + window-to-date utilization (`budget.ts:22`, computed from this workspace's `execution_events`). So the cut is clean and **future-correct, not just convenient**: when a human runs ≥2 operations (the wide-use-case future), Usage = "my total spend across all operations" (UserMenu, `user_id`-scoped) ≠ Budget utilization = "this operation's spend vs its envelope" (Contract group, `_budget.yaml`-scoped). The two reads are genuinely different (receipt: `user_id` vs workspace `_budget.yaml` path); today in single-workspace alpha they happen to coincide, which is why the distinction reads as invisible now.
3. **Sequencing vs ADR-346** — ADR-346 is Proposed today and demotes Feed/Queue to Utilities + adds the Operation composition. The door-collapse is a *separate* change to the *Settings* surface. They're orthogonal (composition surfaces vs config door) and can land independently, but both touch the launcher tier model — worth landing in a coherent sequence so the launcher isn't re-sorted twice.
4. **ADR shape** — does the door-collapse fold into the Expected-Output ADR (they're entangled — the collapse moots the door fork), or is it its own ADR amending ADR-341 (cleaner supersession trail)? My lean: its own short ADR amending ADR-341, with the Expected-Output ADR depending on it.

---

## Appendix — receipts

| Claim | Receipt |
|---|---|
| Two settings doors, region-backed | ADR-341 D1; `kernel_surfaces.py` `settings` (Governance: autonomy/budget) + `workspace-settings` (Constitution: mandate/identity/principles) |
| Rhythm/Witness are live inline editors | `web/lib/content-shapes/budget.ts:40,234` (`setBudget`); `autonomy.ts:481,504,537` (`setDelegation/setPause/setNeverAuto`); both `WRITE_CONTRACT='configuration'` |
| Persona is read + edit-via-chat | ADR-341 D2; constitution panes reuse `MandateCard`/`IdentityBrandCard`/`PrinciplesCard` read variants |
| Expected Output is backend-wired, FE-absent | `reviewer_envelope.py:102`; `reviewer_agent.py:682-686`; `occupant_contract.py:151`; `workspace_paths.py:90`; NO `content-shapes/expected-output.ts`; NO registry/pane |
| Kernel-slots contract survives heterogeneity | `docs/programs/*/SURFACES.yaml` — author declares 2 slots, trader 7→2, commerce/prediction/defi declare 0 (kernel-universal only); `compositor.md` I5 (no `program_slug` branch) |
| Canon contradiction (zero inline editors) | ADR-341 D2 "zero inline substrate editors" vs `autonomy.ts`/`budget.ts` live editors |
| Setup is program-neutral, no stored state | ADR-331 D1; `kernel_surfaces.py` `setup` (archetype `sequence`, `substrate_paths: []`) |
| Teach-in-context at first use | ADR-340 D7; ADR-338 §7.3 |
| Expected Output is a floor-gated cadence, not a quota | ADR-345; `reviewer_agent.py:684` "a floor-gated cadence, NOT a quota" |

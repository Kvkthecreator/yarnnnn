# What blocks ADR-653 — the open discourses, set up for a ruling

*Four questions. Two are already ruled on and the ADR should cite rather than reopen them. One is genuinely open and load-bearing. One is a precondition with a number on it.*

> **Status**: Analysis (2026-09-16). **No ADR rides this document.** It is the companion to [ADR-653](../adr/ADR-653-an-app-is-an-ai-native-program.md) §9, setting up each open question for an operator ruling: what is actually decided, what the prior record already says, what the options are, and what evidence would settle it.
> **Authors**: KVK (operator) + Claude (collaborator)
> **Hat**: A (system canon).
> **Method**: driven against live code at `aaf641a`, plus the ADR record for each question. Where a prior ADR already ruled, it is quoted rather than paraphrased — several of these questions have answers the discourse did not know about.
> **Frame**: [the-app-is-an-ai-native-program-2026-09-16.md](the-app-is-an-ai-native-program-2026-09-16.md).

---

## 0. The headline, before the detail

The operator posed two questions: **how agent accumulation is managed**, and **whether app-bound agents are a different species** living in the app folder. Auditing both produced a sharper finding than either:

> ⭐⭐⭐ **ADR-624 already ruled on both, eighteen days ago, and ruled AGAINST the species split — pre-emptively, with the scaling argument written out.**

That is not a reason to dismiss the operator's instinct. It is a reason to read what the prior ruling actually decided, because **the instinct is right about something the ruling did not cover** (§2.4), and the part it did cover is already answered.

The four questions, sorted by what they actually need:

| # | Question | State | What it needs |
|---|---|---|---|
| 1 | Agent accumulation — first-class? | **Ruled (ADR-624 D1/D2). Built as a shelf; NO writer.** | One decision: who writes, and when |
| 2 | Are app-bound agents a different species? | **Ruled AGAINST (ADR-624, the scaling test).** | Recognition — plus §2.4, the part left open |
| 3 | What makes two pieces of work ONE app? | **Genuinely open. Load-bearing.** | An operator ruling; no prior record |
| 4 | The component vocabulary | **Open, bounded.** | A first real app to derive from |
| 5 | The RED gate | **A precondition with a number.** | ~1 session, independent of everything here |

---

## 1. Accumulation — the shelf is built; nothing writes to it

### 1.1 What is already decided

ADR-624 (ratified 2026-08-31) gave every agent a home and ruled its contents in one sentence:

> **A being's home holds what it KNOWS (free) and the GRANTS it runs under (locked). Nothing else.**

```
agents/{slug}/
  memory/          — what the being has learned. FREELY WRITABLE by that being.
  _autonomy.yaml   — the witness dial.    GRANT SIDECAR — locked.
  _budget.yaml     — its allocation.      GRANT SIDECAR — locked.
```

**So accumulation is ALREADY first-class**, in the strongest sense available here: it is substrate. ADR-624 D2's reasoning is worth quoting because it pre-answers the "how is it managed" question:

> *Do not build a dossier — give the being a folder and let it write ordinary files. A dossier is a mechanism with its own writer, reader and rules; a folder is the substrate doing the job it already does.*

`write_revision` gives it append-only history, attribution, revertibility and a reading face for free. There is no schema to design.

### 1.2 What is missing — exactly one thing

Verified at `aaf641a`:

- `agent_memory_root` has **three references**: its own definition (`workspace_paths.py:154`) and two in `api/routes/lanes.py:613,645` — both serving the **address**, not the contents.
- `grep -n "memory" api/services/lane_runner.py` → **one hit**, an unrelated docstring line. Agent memory is **never composed into the lane frame or the standing frame**.
- The confinement gate exists (`_is_foreign_agent_home`, `primitives/workspace.py:2644-2672`) and is wired into `_is_path_locked_for_principal` (`:2951-2956`).
- The one recognized leaf is `agents/{slug}/memory/feedback.md`, classified for the activity log (`primitives/workspace.py:975`). The instruction to write it lives **only in prompt prose** (`orchestration.py:80`). No code path calls it.

> **The shelf, the lock, the address and the taxonomy row all exist. No writer, and no reader into a turn.**

ADR-624 D3 recorded this honestly and explained why the guard shipped first:

> *⚠️ Honestly recorded: today this rule binds almost nothing, and that is not a reason to skip it… A being writing its own memory is therefore a WRITE THE MEMBER MAKES, today.*

### 1.3 The decision that is actually open

Not *where* memory lives (ruled) and not *what shape* it has (ordinary markdown, ruled). Only:

> **What causes a write, and what causes a read?**

Three options for the write:

| | **A — Prompt instruction** | **B — Turn-end judgment** | **C — Member-triggered** |
|---|---|---|---|
| Mechanism | the frame tells the agent to append when corrected | a cheap bounded turn after a lane turn decides if anything was learned | "remember that" writes it |
| Cost | one prompt clause | a second model call per turn | one door |
| Precedent | ADR-156 (memory in the moment of learning); `orchestration.py:80` already does this shape | none here; ADR-156 explicitly **retired** batch extraction | MCP `remember` is this shape |
| Failure | silent — the agent simply does not, and nothing notices | expensive, and the ADR-647 finding is that **prompt cost dominates** | nothing accumulates unless asked |

⭐ **The ADR-156 precedent points hard at A**, and it is already half-built: `orchestration.py:80` carries exactly this instruction for `feedback.md`, and the classifier recognizes the path. What it lacks is evidence anyone follows it. **The cheapest honest next step is to measure whether the existing instruction fires at all** before adding a second mechanism — because if a prompt clause does not work for feedback, it will not work for memory, and that is a finding worth having before choosing.

For the read, the question is sharper and has a hard constraint:

**The frame is at its byte ceiling already.** `UNBOUND_INDEX_CEILING` is 4,000 bytes, its docstring records a measurement of 3,947/4,000 *"with all eleven listed"* — and there are **12** kernel skills on disk. The unbound lane is at or past its ceiling and evicting its rank-2 tail. **Adding a memory section to the frame is not free**; it displaces something, and ADR-306/DP22 makes adding the last resort. The likely answer is that memory is **read on demand through `ReadFile`, indexed by a single line**, exactly as skill bodies are — the progressive-disclosure pattern already ratified.

### 1.4 What this means for ADR-653

The frame doc promises an agent that *"accumulates judgment about this specific work."* Today that is false, and the ADR says so (§9.2). **The ADR does not need to solve this to be interim-complete** — it needs to state the promise honestly and name the dependency: the **derived** origin (D6) is the one that needs accumulation, and it is already sequenced last.

---

## 2. The species question — ruled against, pre-emptively

### 2.1 The proposal

*App-dedicated agents reside within the app folder structure, becoming a different breed from those not bound to apps.*

### 2.2 What ADR-624 already decided — the scaling test

This is the part the discourse did not know. ADR-624 ran the twenty-beings/thirty-apps test and wrote out the failure:

> *Editor serves Slides and Text; its purpose at each differs, so one `MANDATE.md` cannot hold both. Either Editor forks into `slides-editor`/`text-editor` — **re-introducing the injectivity ADR-601 D1 retired on a measurement** — or the mandate becomes so generic it says nothing.*
>
> **Every per-desk fact in the ADR-414 home breaks under many-to-one.**

And it refused the per-app memory split by name, with its reasoning stated in the code:

> *Flat, NOT desk-scoped… A per-desk split (`memory/{app}/`) was considered and refused for now: it guesses at a structure before there is evidence, and the being can subdivide its OWN folder without a schema change the day per-desk blur actually appears.* (`workspace_paths.py:143-147`)

**This is live today.** Editor serves both `slides` and `text` — four apps, three agents. Putting Editor inside an app folder forces the fork ADR-601 measured away (job overlay 86.7% of a Slides frame vs character 2.4% — an agent's prompt weight is **constant** in apps served).

### 2.3 The species framing runs into the register too

ADR-600 collapsed three registers into one, and its reasoning is the same shape:

> *Three dicts with identical row shapes and one shared resolution namespace were never a type distinction — they were a **VISIBILITY FLAG modelled as three containers**, and modelling a property of a being as the identity of its container means the agent changes identity when the property changes.*

A species split by folder is that pattern returning: **"which app it serves" is a property, and locating it in the container makes it an identity.** If Editor later serves a member app too, it would have to move, and its slug rides ~65 live cast rows and every lane stamp.

**The ADR-653 D2 answer is already the non-species one**: a member agent is an `AGENTS`-shaped row with `kernel: False` — *declared inside* `_app.yaml`, not *living in* the app folder. Declaration site ≠ residence. One species, one register, one resolution path, one memory home.

### 2.4 ⭐ What the instinct IS right about — the part nothing has ruled

The operator's framing contains a real distinction that survives §2.2, and it is not about species:

> **A kernel agent serves many apps and is `kernel: True`. A member's app agent serves exactly one app and is authored by them. Those differ in LIFECYCLE, not in kind.**

Concretely, and **nothing in the record covers these**:

1. **What happens to `agents/{slug}/memory/` when the app is deleted?** ADR-653 D1 promises *"deleting it dismisses the agent and leaves every file untouched"* — but the agent's memory is under `agents/`, not under `apps/`. Deleting the app orphans a memory folder whose agent no longer resolves. **Open.**
2. **Can two apps name the same member agent?** Kernel many-to-one is live and free. If member agents may be shared, the "one app is one agent's remit" intuition (§3) weakens; if they may not, that is a new asymmetry needing a reason.
3. **Slug collision across apps.** Two members' apps both naming their agent `mara`; slugs are data-compat and ride cast rows. Namespacing (`apps/{app}/{slug}`) vs global uniqueness is undecided.

**These are the questions the species instinct was really pointing at.** They are lifecycle questions, and ADR-653 should answer at least (1) — because it makes a promise that its own storage layout does not keep.

---

## 3. What makes two pieces of work ONE app — genuinely open

### 3.1 Why this is load-bearing

If boundaries are emergent and hardened by use (frame §6, the operator's accepted risk), then something must make an app **cohere** — or a workspace is one undifferentiated blob of concerns and "app" means nothing. This is the definition of the core object and **there is no prior record on it.**

### 3.2 The candidates

| | **A — The who** | **B — The region** | **C — The rhythm** | **D — The member says so** |
|---|---|---|---|---|
| One app is… | one agent's remit | one region of the filesystem | one recurring cycle | whatever they named |
| Test | *would it be strange for two different people to handle these?* | do they share a folder? | do they come due together? | — |
| Fits the frame? | ✅ — the resident IS the app (frame §5) | ❌ — frame §6 rules region emergent | 🟡 — many apps have no rhythm | ✅ trivially |
| Fails when… | one person handles everything | work spans folders (frame §6: *"real work is not folder-shaped"*) | the work is reactive | the member does not know either |
| Structural? | a real constraint | contradicts a ruling | too narrow | no constraint at all |

**B is eliminated** by the frame's own soft-boundary ruling. **C** is too narrow — an app that only ever acts when asked is still an app. **D** is honest but provides nothing: if the member is the only thing distinguishing two apps, they will make one app called "work."

### 3.3 The case for A, and its honest cost

**A is the only candidate that is both a real constraint and consistent with the frame.** It reads directly off the program metaphor: an app is a post, and a post is one agent's station.

It is also a **human** intuition rather than a structural rule, which may be exactly right for a product whose point is mapping to how people already think about their work. The cost is that it makes the crowding risk (frame §5.2) structural rather than incidental: **six concerns = six agents = six voices.** If you rule A, you are ruling that apps are *few* — and the product should probably say so.

⚠️ **A has a live counter-example in the kernel.** Editor serves Slides and Text — two apps, one agent. If "one app is one agent's remit" were a law, they would be one app. They are not, and ADR-602 D1's reason is that *"the member asking 'who is responsible for my writing?' gets one answer across decks and documents."* So **A is not injective in the kernel today**, and §2.4's question (2) is the same question from the other side.

The resolvable version: **one app has exactly one resident; one agent may resident several apps.** That is the kernel's live shape, it preserves ADR-601, and it gives coherence without injectivity — an app coheres because *someone is minding it*, not because nobody else is.

### 3.4 What would settle it

The frame doc's own suggestion, unrun: **take three deliberately unlike scenarios — ideally one not document-shaped, and one where the work is mostly deciding rather than producing — and check whether each splits cleanly under A.** If two scenarios keep wanting to be one app under A but feel like two to a person, A is wrong.

**This is a one-session test and it does not need code.**

---

## 4. The component vocabulary — open, bounded, and best deferred

ADR-653 D3.b calls this *"the riskiest decision in this ADR."* Too small and nothing composes; too large and this is a page builder — the feature race the app-seam analysis warns against.

**It cannot be settled by reasoning, and it does not need to be settled now.** The deleted `dispatchComponent` already had the right posture: an unknown kind rendered an honest amber *"referenced in composition but not registered"* box. That means **the vocabulary can start at one or two kinds and grow on demand**, with every refused kind counted as the demand measurement (ADR-653 §9.6).

The discipline to rule: **a kind is added when a real app needs it and cannot be served, never speculatively.** If the operator rules that, this stops being a blocker and becomes a build-time judgment.

---

## 5. The RED gate — a precondition, not a discourse

Not a question, and included because it is the only item with a hard number.

`api/test_adr338_surface_registry_parity.py` is **RED at baseline — 15 passed, 2 failed**, verified directly. `connectors` is a phantom slug: FE union (`web/types/surface.ts:91`) and allowlist (`:133`), `stage: internal` so never served (`kernel_surfaces.py:832`), no registry entry. Clicking anything naming it opens an **empty window** (`Launcher.tsx:268` admits it, `SurfaceViewport.tsx:185` renders `null`).

ADR-425 lineage, stranded when ADR-645 deleted the Settings → Connectors door. **Pre-existing; ADR-653 must not absorb it.** But ADR-653 D3.c touches that gate, so **it must be green on its own merits first or its green under ADR-653 is meaningless.**

Independent of every question above. Roughly one session. Nine more pre-existing defects are catalogued in ADR-653 §10.

---

## 6. What actually blocks an interim-complete ADR-653

Sorted honestly:

**Does NOT block it:**
- **Accumulation** (§1) — the ADR already names it as open and sequences the dependent origin last. A promise stated honestly is not a blocker.
- **The species question** (§2.1-2.3) — already ruled. The ADR should **cite ADR-624 and ADR-600** rather than leave it open, which makes the ADR *more* complete, not less.
- **The component vocabulary** (§4) — deferrable by ruling the growth discipline.

**DOES block it:**
- ⭐⭐⭐ **§3 — what makes two pieces of work one app.** This is the definition of the object the ADR proposes. An ADR that cannot say when two things are one app cannot gate an implementation, and §3.3's live counter-example (Editor serving two apps) means the obvious answer needs the refinement stated there.
- ⭐ **§2.4 — the lifecycle questions.** At minimum (1): the ADR promises deleting an app leaves files untouched, while the agent's memory lives under `agents/`, not `apps/`. **The ADR currently makes a promise its own layout does not keep.**

**Blocks the BUILD, not the ADR:**
- §5 — the RED gate.

---

## 7. Proposed sequence

1. **Rule §3** (the coherence question) — one ruling, no code. This is the blocker.
2. **Rule §2.4 (1)** (memory orphaning) — a paragraph in ADR-653 D1/D2.
3. **Amend ADR-653** to cite ADR-624/ADR-600 on the species question, moving it from *open* to *decided*.
4. **Rule the vocabulary growth discipline** (§4) — one sentence in D3.b.
5. Then ADR-653 is interim-complete and ratifiable.
6. **Independently**: fix the RED gate (§5), before any build touches it.
7. **Deferred, evidence-first**: measure whether the existing `feedback.md` prompt instruction fires at all (§1.3) — the cheapest read on whether a prompt clause can drive accumulation.

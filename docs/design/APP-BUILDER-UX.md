# The app-builder — the member's path

*What she sees, what she does, and how someone minding her work is made visible without becoming noise.*

> **Status**: Design spec, first cut 2026-09-17. **ADR-653 is ACCEPTED (2026-09-17); this document is its design half and is ratified with it.** §8 is the sequence: **steps 1–3 are BUILT and click-passed** (2026-09-17 — §8.1 records what they taught); steps 4–7 are not.
> **Authors**: KVK (operator) + Claude (collaborator)
> **Why a dedicated document**: ADR-653 carries exactly ONE frontend decision (D3.c — widen the Launcher's slug gate, mount a generic app surface), and that is a routing fix, not a design. The frame's whole argument is a UX argument — *an app is a **visible claim**… not capability, but legibility of capability* — so an ADR that argues for visibility and specifies none of it is half an ADR. This is the other half.
> **Binding constraints**: [VOICE-AND-TONE.md](VOICE-AND-TONE.md) §2 slot budgets and §3 word map are LAW here, guarded by `api/test_voice_no_kernel_nouns_in_copy.py`. Every string in this document is written to a measured budget, and no kernel noun appears in any of them.
> **Frame**: [the-app-is-an-ai-native-program](../analysis/the-app-is-an-ai-native-program-2026-09-16.md) · **Blockers**: [what-blocks-adr-653](../analysis/what-blocks-adr-653-2026-09-16.md)

---

## 0. The one sentence this design must earn

> **She could see it could do anything, which meant she could not see what it did.**

Every decision below is answerable to that. The test for any screen here is not *can she do it* but **can she tell what this is for before she asks.**

---

## 1. What is undesigned today — the honest inventory

A member cannot, at `fd82fba`:  *(rows 1, 3 and 4 are CLOSED as of 2026-09-17 — §8.1)*

| # | She cannot… | Why |
|---|---|---|
| 1 | See that apps exist | No door. Not in the Launcher, not in Files, nowhere. |
| 2 | Get one | All three origins named in ADR-653 D6 with zero interaction design |
| 3 | See one open | D3.b says "a bounded component vocabulary" and names no kind |
| 4 | Feel the agent is there | The frame's strongest idea — *someone minding your work* — has no rendering |
| 5 | Fix a wrong one | D6 calls the builder "the escape hatch that makes the other two safe"; the hatch is undesigned |
| 6 | Get rid of one | Deletion is promised as safe (D1) and never shown |

⭐ **§1.3 is not deferrable the way ADR-653 implied.** The blockers doc §4 rules the vocabulary *"grows on demand from a real app"* — right as a growth discipline, and it quietly assumes a first vocabulary exists to grow from. **Kind #1 cannot be derived from usage that cannot happen until kind #1 exists.** So the first cut is a design decision (§5), and the demand measurement starts at kind #2.

---

## 2. The shape of the thing on screen

### 2.1 An app is a surface, and it sits where the apps already sit

The Launcher already groups by tier (`Launcher.tsx:83-99`) and **already has a `program` tier** with its own group shape. An app joins the tier list under one heading:

```
Workspace          Chat · Text · Slides · Images · Blogger · Files · Agents · Reach
Your apps          Photos · Client work                      ← new
Workspace settings …
```

**"Your apps"**, not "Programs", not "Composed surfaces". Two words, possessive, and it says whose they are. The Dock holds an app only if she keeps it there — same gesture as every other surface, no new concept.

### 2.2 What an app surface shows — the three-band frame

Every app renders the same three bands. **The bands are fixed; only their contents are declared.** This is what keeps an app from being a page builder.

```
┌──────────────────────────────────────────────────────────┐
│  Photos                                          ⌄       │  ← name + what it is
│  Client shoots, culled and delivered.                    │
├──────────────────────────────────────────────────────────┤
│  Mara has been looking after this.                       │  ← the resident band
│  "3 shoots from last week still need culling."    Open → │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  [ the sections the app declares ]                       │  ← the work band
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**Band 1 — what this is.** The name and the one-line `about`. Written to the **pane subtitle budget**: two short sentences, ≤ ~130 characters (VOICE §2). This band is the visible claim; if it cannot say what the app is for, the app is wrong.

**Band 2 — who is minding it.** The resident, named, with the one thing worth saying right now or nothing at all. §4 is entirely about this band.

**Band 3 — the work.** The declared sections. §5 is the vocabulary.

### 2.3 Why a fixed frame and not a canvas

Three reasons, in order of weight:

1. **It bounds the build.** A canvas is a layout engine; three bands is a component.
2. **It makes every app legible the same way.** She learns one shape and reads every app she or anyone else makes.
3. **It puts the resident in a fixed place.** The frame's central promise — *someone is minding this* — renders identically everywhere rather than being something an app might forget to include.

⚠️ **The cost, stated:** an app cannot look distinctive. That is the intended trade. Distinctiveness is what turns this into Wix, and the app-seam analysis names that as the feature race we lose.

---

## 3. The three origins, as three gestures

ADR-653 D6 names chosen · derived · authored. Their **build order is not their importance order**, and their UX differs completely.

### 3.1 Chosen — at the empty workspace

The first-run answer, and the only origin available at minute zero. Not a wizard: **one question, four or five answers, skippable.**

```
  What do you work on?

  [ Photos and shoots ]  [ Writing ]  [ Research ]  [ Client work ]

  Skip — I'll look around first
```

What lands: a named app, its folders, its agent, its skills. **Nothing about the answer is binding** — it is a reading, and the next screen says so in one line: *"You can change any of this later, or delete it. Your files stay."*

⭐ **This sentence is the whole psychological unlock** and it is true by construction (D1: the declaration is a file; the work is not). Every other product makes setup a bet. Say plainly that this one is not.

### 3.2 Derived — the proposal, after work has happened

The differentiated origin, and **the one that needs accumulation** (blockers §1) — so it ships last, not first.

The gesture: she has been working; something notices a shape; it offers. The rendering rides **the attention mechanism that already exists** (`api/services/mentions.py` — a derived, per-viewer surface with one cursor, advanced by visiting). A proposal is an item in To-do, never a modal, never an interruption:

> **Make this an app?**
> You've been filing shoots under `clients/` for three weeks. I can set up a place for this with someone to look after it.
> [ Show me ]   [ No thanks ]

**[ Show me ]** opens a preview of the app as it *would* be — the three bands, populated, not yet real — with **[ Keep it ]** and **[ Discard ]**. She sees the thing before it exists.

⚠️ **"No thanks" must be durable.** A proposal that returns is the noise failure (§4.2) in its most annoying form. Declining a shape declines that shape, not proposals in general.

### 3.2a The builder is itself an app (ADR-653 R2)

**Ruled 2026-09-17.** There is no builder surface, no builder route, no builder component. The thing that makes apps **is an app**: the same three bands, the same resident, the same declaration, reachable from the same "Your apps" group.

```
┌──────────────────────────────────────────────────────────┐
│  Apps                                            ⌄       │
│  What you've set up, and what's looking after it.        │
├──────────────────────────────────────────────────────────┤
│  Bo looks after this.                                    │
├──────────────────────────────────────────────────────────┤
│  Photos        Mara      3 shoots need culling           │
│  Client work   Tess      quiet                           │
│                                                          │
│  + Set one up                                            │
└──────────────────────────────────────────────────────────┘
```

⭐⭐⭐ **This is the design's own falsification test.** If the three-band frame cannot express the builder, the frame is too weak — and we find that out at build time rather than after members have five apps each. The builder is the first app and the hardest one.

It also **tests the vocabulary before any member app exists**: that screen is `needs-you` (apps wanting attention) over `apps/`, plus a door. §5's riskiest decision gets exercised by us, on ourselves, first.

**"+ Set one up"** does not open a form. It starts the conversation (§3.3) — the builder's own bound lane, with its resident. The door is a door into talking, which is the one authoring interface this product is good at.

### 3.3 Authored — in chat, and it is the cheapest to build

*"Set me up something for tracking client work."* A lane writes the declaration file. No builder surface, no form — **the builder is a conversation**, which is the one authoring interface this product already has and is good at.

This should ship **first**, precisely because it is cheap: it needs no new surface, it exercises the whole declaration path end to end, and it is the repair path for both other origins. ADR-653 D6's own line — *"the builder is the escape hatch that makes the other two safe"* — is an argument for building it first, not last.

### 3.4 Editing and deleting

**Editing is chat.** *"Mara, stop watching the invoices folder."* The declaration is a file; the agent can revise it; the change is versioned and attributable like everything else. A form editor is the second authoring face and should not exist.

**Deleting** is the ⌄ menu in band 1, and the confirm is the promise made visible:

> **Delete Photos?**
> The app and Mara go away. Your photos, folders and files stay exactly where they are.
> [ Delete app ]   [ Cancel ]

✅ **Ruled 2026-09-17 (ADR-653 R1): memory is deleted with the app.** The confirm above is therefore TRUE as written — the app and its agent go away together, and the member's own files stay. The copy names the two things a member would worry about (the agent, their photos) and does not mention memory at all, which is correct: *what Mara learned* is part of Mara, and a confirm that itemised it would be explaining our storage rather than her consequence.

⚠️ **One mechanism question the ruling opens** (ADR-653 §8a R1): the agent's memory sits at `agents/{slug}/memory/`, keyed by slug rather than by app, so the delete must derive the pairing. That is a backend question and does not change this screen.

---

## 4. The resident band — presence without noise

The hardest design problem here, and the one that is judgment rather than mechanism (ADR-653 §9.4). The frame is blunt about it:

> *The failure mode of a standing watcher is that it surfaces noise to prove it is alive. Then the person learns to ignore it… **"most of the time it says nothing" has to be a design goal rather than an embarrassment.***

### 4.1 The three states, and the resting state is the common one

| State | Renders | When |
|---|---|---|
| **Resting** | `Mara looks after this.` | most of the time — **the default** |
| **Working** | `Mara is culling last week's shoots.` + the bounded-wait primitive (ADR-651) | a run is in flight |
| **Raising** | `Mara: "3 shoots still need culling."` + one action | something is genuinely worth saying |

⭐ **Resting is not an empty state.** It is the RESTING state and it should read as calm rather than as absence. *"Mara looks after this"* is a complete, reassuring sentence — someone is on it and there is nothing to do. Compare *"No new activity"*, which says the same thing and sounds like a failure.

### 4.2 The rule for raising, stated so it can be enforced

> **Raise only what changes what she would do next.**

Not *what happened* — the timeline already holds that, and it is one click away. A raise is a claim on her attention and it must earn it by being actionable.

Three properties this design commits to:

1. **At most one raise per app at a time.** Band 2 is one line. Structural, not policy — there is no room for two, by construction.
2. **A raise is discharged by visiting**, reusing the ADR-637 cursor — *opening it is the discharge*. No Done button, no dismiss, no second clearing path. The badge and the band agree by construction because the same cursor decides both.
3. **A raise that is not acted on decays.** It does not persist forever getting louder. If it still matters next run, it comes back; if it does not, it was not worth the line.

### 4.3 Where a raise appears outside the app

It rides To-do and the existing attention derivation. **It does not send email by default** — the account-email class (ADR-650) is a separate decision with its own dials, and an app that mails her unprompted is the noise failure escaping the product.

### 4.4 The crowding question, unresolved

ADR-653 §9.5: six apps is six agents entitled to speak. Three options, and I do not think this can be settled before it is felt:

| | Per-app voice | Pooled | Capped |
|---|---|---|---|
| Each app raises in its own band | ✅ clear whose | 🟡 needs a shared place | ✅ |
| Across apps | 🔴 six voices | ✅ one list, attributed | ✅ few apps by design |
| Risk | surveilled | who said this? | arbitrary limit |

**The band-2 design works under all three**, so this does not block the first build — it blocks the *second* app. Named here so it is not discovered.

---

## 5. The component vocabulary — the first cut

§1's finding: this cannot be deferred to demand, because demand cannot start until it exists. So: **four kinds, argued.**

The principle: **a kind is a way of SEEING files, never a way of styling them.** Every kind below answers a question about work the filesystem cannot answer by listing.

| kind | Shows | The question it answers | Why first |
|---|---|---|---|
| `files` | a filtered region — grid or list | *what is here?* | the irreducible one; without it an app shows nothing |
| `recent` | what changed lately, attributed | *what moved?* | the accumulation made visible; already exists as `RecentsView` |
| `needs-you` | files matching a declared condition | *what is waiting on me?* | the only kind that makes an app feel like work rather than storage |
| `note` | a rendered `.md` from the workspace | *what did we decide?* | the contract/brief, readable in place; costs nothing, reuses the viewer |

**What is deliberately NOT in the first cut**, and why each would be a mistake now:

- **charts / metrics** — invites the dashboard, which invites the metric, which is a different product. Wait for a real ask.
- **a table with editable cells** — that is Notion's database, and the substrate has no schema to back it.
- **anything with a layout prop** — the moment a kind takes `columns` or `align`, this is a page builder.
- **an embed / iframe kind** — the third-party seam (ADR-427 §9 / the app-seam analysis), gated separately and deliberately.

⭐ **`needs-you` is the load-bearing one** and the riskiest. It is what separates "a nicer folder" from "someone is minding this", and its condition is where judgment enters the declaration. First cut: a declared condition the resident evaluates (*"shoots with no culled set"*), rendered as a list with a count. If that proves unimplementable, the honest fallback is that the resident raises it in band 2 and the kind waits.

**The growth rule** (ADR-653 D3.b, unchanged): a kind is added when a real app needs it and cannot be served — never speculatively — and every refused kind is counted. **The count starts now, at kind #5.**

---

## 6. The copy, written to budget

Every string that ships, at its measured slot. VOICE §2 budgets applied; §3 word map observed — **no "lane", "artifact", "substrate", "declaration", "resident", "composition" appears anywhere a member can read.**

| Slot | Budget | String |
|---|---|---|
| Launcher group | — | `Your apps` |
| Launcher summary (per app) | **≤ 312 px / ~48 chars** | the app's own `about`, truncation-checked at author time |
| Band 1 subtitle | ≤ ~130 chars | the app's `about` |
| Band 2 resting | one line | `{Name} looks after this.` |
| Band 2 raising | one line | `{Name}: "{one sentence}"` |
| Empty app | title ≤ 4 words + one sentence | **`Nothing here yet.`** / `Files you add to these folders show up here.` |
| Delete confirm | two sentences | §3.4 |
| First-run question | — | `What do you work on?` |
| First-run reassurance | one sentence | `You can change any of this later, or delete it. Your files stay.` |

⚠️ **The launcher summary is the tightest constraint in the product** and it now applies to member-authored text. An app whose `about` exceeds ~48 characters truncates in the Launcher. **The authoring path must measure it and say so at write time** — not truncate silently. VOICE §2's own rule: *if it cannot say what the surface is for in 48 characters, the surface's name is wrong, not the budget.*

---

## 7. What this design does NOT include

Named so their absence is a decision:

- **No app store, no gallery, no browse.** Apps are files; sharing one is sharing a file. A marketplace surface is a separate arc with its own trust questions.
- **No form-based builder.** Editing is chat (§3.4). A form is a second authoring face.
- **No per-app notification settings.** ADR-593's ruling stands: apps declare semantics, the kernel derives emission, and management is one central place.
- **No app-specific theming, icon picking or color.** §2.3's trade, held.
- **No mobile-specific layout.** Three bands stack; the existing responsive shell handles it. If it does not, that is a bug in the shell, not a design gap here.

---

## 8. Sequence — what to build, in what order

Ordered by *what teaches the most per unit of build*, not by completeness.

| # | Ships | Needs | Teaches |
|---|---|---|---|
| 1 | ✅ **Authored origin** (§3.3) — chat writes a declaration | the D1 file format, nothing visual | whether the declaration format survives a real ask |
| 2 | ✅ **The app binding kind** — a lane bound to an app (R3) | `create_lane` + posture widening | whether an app-level conversation composes |
| 3 | ✅ **The surface** (§2.2) with `files` + `note` | D3.c's gate widening; two kinds | whether three bands is enough shape |
| 4 | **The builder, as an app** (§3.2a) | `needs-you` over `apps/` | ⭐ whether the frame can express its own maker |
| 5 | **Band 2 resting + raising** (§4) | the resident read | whether presence reads as calm or as noise |
| 6 | **Chosen origin** (§3.1) — first-run | a small catalog | time-to-value at minute zero |
| 7 | **Derived origin** (§3.2) | accumulation (blockers §1) | the differentiated claim |

⭐ **Step 1 ships no UI at all**, and that is deliberate: it proves the whole backend path with one chat message before a pixel is drawn. If the declaration format is wrong, it is wrong cheaply.

⭐⭐ **Step 4 is the design's falsification** and it moved up because of R2. Building the builder as an ordinary app, before any member has one, tests the frame and the vocabulary against the hardest case we control. If it needs a special case, we have learned the frame is wrong while it is still cheap to change.

✅ **Step 2's precondition cleared**: the ADR-653 §10.1 parity gate (`connectors`, a phantom slug) went green in `0096569` and has stayed green (17/0) through step 3.

### 8.1 What steps 1–3 taught — 2026-09-17

**Three bands IS enough shape** (step 3's question), on the one app we have driven. Band 1's claim,
band 2's resting line and a band of declared sections read as one thing, and the `note` kind carrying
a full markdown document — headings, a table, task list, code fence — did not strain the frame.
⚠️ Untested at the shapes that would strain it: many sections, a long `about`, a narrow viewport.

**The vocabulary's first refusal is already recorded.** A declaration naming `needs-you` renders the
honest amber miss — *"This app asks for a needs-you section, which this workspace cannot show yet."*
That is §5's growth rule working before any member has asked for anything: the server admits four
kinds, the client draws two, and the gap is VISIBLE rather than blank. ⭐ The count of refused kinds
starts here, and the first entry is one of our own.

**An app-level conversation composes** (step 2's question): the app-bound lane appears in Chat
labelled by the app, with its agent seated. Driven on the rig, receipts in ADR-653 §11.1.

⚠️ **What step 3 did NOT ship, and is owed to step 5**: band 2 renders the RESTING state only.
*"{Name} looks after this."* is live; working and raising are not, because raising needs the resident
read. §4.2's rules (one raise at a time, discharged by visiting, decaying if unacted) are unexercised
— the hardest part of this design is still ahead of it.

---

## 9. Open — design questions, not mechanism

0. ✅ **One app, one agent** — **RULED (ADR-653 R4)**, for member apps only; kernel apps keep many-to-one. Every design decision below that assumed it is now sound rather than assumed: the Dock shows one door per concern, band 2 names one agent, and "would two different people handle these?" is a real constraint the builder can apply when a member describes two things at once.

1. ✅ **Does the Dock show apps, or agents?** **RULED (ADR-653 R3): apps.** An app is one door opening one pane with one conversation in it. Agents are met where they work — ADR-600 D2's `offered: False` posture — and do not need a second row of icons.
2. ✅ **What does the app's own chat look like?** **RULED (ADR-653 R3): a bound lane**, consistent with every existing app. ⚠️ This is the largest mechanism consequence of the rulings: `create_lane` derives boundness from an ARTIFACT (`api/routes/lanes.py:971`) and an app-level lane has none, so the request is refused at `:976` today. **A third binding kind — the app itself — is required**, and the job overlay signature (`posture(client, user_id, artifact_path, artifact)`) widens with it.

   ⭐ **The design consequence is that the app surface and its conversation are one thing, not two.** Band 3 (§2.2) is what the resident is looking at; the conversation is how she talks to it about that. The existing bound-pane shape — conversation on one side, the work on the other — is the precedent, and this design inherits it rather than inventing a second chat home.
3. **Does an app appear in Files?** `apps/{slug}/_app.yaml` is a real file in a real folder. Showing it is honest and consistent with "everything is files"; hiding it keeps the folder tree about her work. Probably show it, in the same way `system/` is shown.
4. **What does a broken app render?** A declaration naming a kind that does not exist gets the honest amber miss (ADR-653 D3.b). But a declaration naming a *folder* that no longer exists is more common and needs its own answer.
5. **Does the first-run question ship before apps do?** Asking "what do you work on?" and then not acting on it is worse than not asking.

---

## 10. The one-line statement

**An app renders as three fixed bands — what this is, who is minding it, and the work — reachable from a "Your apps" group in the launcher; it is born from a chat sentence, a first-run question or a proposal in To-do, edited by talking to the agent that lives in it, and deleted with a confirm that says the files stay; its resident says nothing most of the time, raises at most one thing at a time, and is discharged by being visited; and its sections speak a four-kind vocabulary that grows only when a real app cannot be served — because the product's claim is not that she can do anything here, but that she can see what this is for.**

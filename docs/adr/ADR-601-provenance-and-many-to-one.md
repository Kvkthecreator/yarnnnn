# ADR-601: A being declares who authored it — and one being may serve many desks

**Status**: Ratified + Implemented 2026-08-24 (operator ruling, continuing the ADR-600 discourse: *"critical agents much like Editor, and future Blogger, are closer to yarnnn-internal system managed agents … although visible on the agents pane front end for users to see, isn't editable."*)

**Supersedes**: ADR-597 D2 (injectivity — one app, one dedicated colleague). Retains ADR-467 D1 (an app pins ONE resident), ADR-600 D1/D2 (one register, `offered` as a field), and the ADR-460 D3.a cliff.

## Context

ADR-600 collapsed the agent registers to one dict plus `offered`, establishing the shape: **every question about a being is a field on the being.** Two questions were still answered structurally rather than declaratively.

### The capability layer already lives at the APP, not the agent — measured

A bound lane's system frame composes three layers. Measured on a real Slides turn (`deck` artifact, Designer resident):

| Layer | Size | Home |
|---|---|---|
| Kernel participant contract | 2,248 ch (10.9%) | `workspace_paths.py` — every being, every principal |
| **Character** (`posture`) | **503 ch (2.4%)** | `AGENTS[slug]["posture"]` |
| **Job overlay** | **17,881 ch (86.7%)** | the app's own module |

The job overlay is selected by `app`, never by the resident (`lane_runner`: `app == "strings"` → keeper desk posture · `app == "text"` → text posture · else → studio posture). And it is not prose: `_blocks_grammar(app)` and `_arrangements_grammar(template)` **derive** the grammar from the same registries the toolbar renders from — measured, `slides` offers `callout`/`component`/`toggle` that `text` does not. A hand-written `SKILLS.md` would be a second home for facts the app already declares, drifting the moment either side is edited; a derived grammar cannot drift.

**Consequence: a being's prompt weight is CONSTANT in the number of desks it serves.** Editor over Text + Blogger costs the same 528 characters as Editor over Text alone. Injectivity was therefore never buying efficiency — it was a legibility policy, and ADR-600 removed the structural reason for it (a being is no longer identified by the container it sits in).

### "Not editable" was true only by absence

`routes/agents.py` never imports the registry — the edit door reaches the legacy `agents` table and cannot touch a being. So kernel beings are uneditable today because **no door exists**, not because one refuses. That is precisely the shape ADR-600 was written to end: a real property, unrepresented, holding until someone builds the door. The moment member-authored beings exist, an edit door appears and the protection must already be in the row.

## D1 — Many-to-one: a being may serve many desks

ADR-597 D2's injectivity is **retired**. `register_app` was always many-to-one (apps hold a resident slug; residents know nothing of apps), and `resident_for_app` is a one-way lookup — the constraint lived only in a gate.

What survives, unchanged: **an app pins exactly ONE resident** (ADR-467 D1). The relation is many-apps-to-one-being, never the reverse. A desk with two voices is the ambiguity the registration exists to prevent.

The named-exceptions machinery (`exceptions <= {"images"}`) is deleted with the rule it guarded. Sharing is now ordinary, so a gate that treats it as a violation-to-be-excused would misreport the architecture.

**Legibility moves to the surface, where it belongs**: a being lists the desks it serves (D4), so a member reads "Editor — Text, Blogger" rather than inferring one-to-one from silence.

## D2 — Provenance: `kernel: bool`

Each row declares **who authored it**. `kernel: True` — yarnnn wrote this being; the apps depend on it. `kernel: False` — the member wrote it (none today; the register is entirely kernel).

**It is descriptive, never authority.** `kernel` answers *who wrote this row*, never *what this being may do*. The moment it gates capability rather than editability it becomes authority on a being, which is the ADR-460 D3.a cliff. The banned-vocabulary gate is unchanged and `kernel` passes it: provenance is a fact about the row's origin, in the same family as `slug`.

**Provenance, not `editable`, deliberately.** The two coincide today and could diverge — a member might later rename a kernel being's display name without touching its posture, or fork one into a member-authored copy. Provenance is the durable fact; editability is a policy over it (D3). Naming the field `editable` would collapse the durable fact into today's policy and lose the distinction.

The three row-level questions are now orthogonal and each declared:

| field | question |
|---|---|
| `offered` | may a member invite this being into a conversation? |
| `kernel` | did yarnnn author this being, or did the member? |
| *(capability)* | — not on the row at all; it is the app's |

## D3 — The refusal is a gate, not a missing route

`PATCH /api/agents/{id}` operates on the legacy `agents` table and is untouched. The registry gains `assert_editable(slug)` — the single chokepoint any future edit door calls, which refuses a kernel being **with its reason** ("Editor is a yarnnn system agent — it comes with the apps it works in") rather than a generic 404.

Built before the door it guards, deliberately. A protection written at the same time as the feature it constrains is a protection the feature's author may forget; the ADR-563 lesson (guard at the chokepoint, not at call sites) applies to a chokepoint that does not yet have callers. It is exercised by the gate, so it is not untested code.

## D4 — The surface renders provenance and desks, served not inferred

The `beings` envelope key carries `kernel: bool` and `homes: string[]` (replacing the single `home`). The surface renders "yarnnn system agent" from the FIELD and the desk list from the ARRAY — never from a being's absence from some list, which would have the pane asserting something the API never said (the ADR-600 D6 lesson, one layer up).

`homes` is ordered by registration and may hold several entries; a being serving no desk has an empty array.

## Consequences

- Blogger can seat Editor when it lands: an app registration plus a job overlay, no new being, no prompt-weight cost.
- The pane tells a member which agents are yarnnn's and which are theirs, before any member-authored being exists — so the distinction is legible from the first one.
- The external-AI-principal question (an MCP principal receives the 2,248-char kernel contract and **nothing** of the 18K job layer) is now cleanly posable: the grammar is derivable per app, so serving it on demand is a design question, not a refactor. Named here, deliberately not answered.
- Gates: `test_agent_registry.py` extended (provenance shape, the cliff over the new field, `assert_editable` behaviour, surface rendering); `test_adr597_resident_derivation.py`'s `test_injectivity` REPLACED by a many-to-one check (an app pins exactly one resident; sharing is ordinary). Every new check falsified.

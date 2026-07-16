# The Agent Hiring Card — the surface, and the concepts behind it

**Status**: Spec. §1–§6 (the surface) is ready to build; **§7 (Skills · Tools · Connections) is CONCEPT ONLY — stated, deliberately not built**, with the receipts for why.
**Date**: 2026-07-16
**Derivation**: the operator's ChatGPT business-agent screenshots (2026-07-16) read as a benchmark + a warning.
**Relates to**: personified-agents spec (the substrate this fronts) · ADR-460 D3.a (the cliff this must *show* without inviting) · ADR-449 (the folder precedent) · ADR-307 (the gate the benchmark sells as a dropdown) · ADR-118 (skills — **dead**, §7) · ADR-404 (the connector lane — **dormant**, §7).

---

## 1. The benchmark, and what it confirms

ChatGPT's business-agent editor shows: **avatar · name · Channels · Apps · Skills · Files · Memory · Instructions**. Two readings, both load-bearing.

**Reading 1 — the folder was right.** An Agent there is a **page**, not a row: `quote-formatter-ko` as a skill chip, `2 files` + `Memory` as contents. That is a folder's worth of object; a flat registry row could never hold it. The operator chose folder-per-Agent *before* seeing this — the shape converges, which is the cheap kind of validation.

**Reading 2 — the warning.** The second screen carries:

> **Write action safety: `Never ask`** · Agent-owned account · Write actions: *Uncheck all*

**That is the ADR-307 consequential gate, sold as a dropdown.** "Never ask" *is* autonomy over consequential action — set from a config screen, by anyone, in one click, with no mandate, no witness, and no track record. It is precisely the cliff [ADR-460 D3.a](../adr/ADR-460-agents-one-concept-independent-facts-one-gate.md) made unrepresentable, rendered as a `<select>`.

**So the benchmark is a benchmark for the FORM and an anti-pattern for the POWER.** Copy the page; refuse the dropdown.

## 2. The framing: hiring, not configuring

The operator's words, and they are the whole design:

> "the concept is **'you're hiring, or bringing to life a Critic Agent that you can name as Lisa and can be serious toned'** or 'you're configuring a Designer Agent that you can name and is more fun'."

This inverts the "what's editable vs locked" question in a way that matters. **A settings panel with greyed-out fields invites "how do I enable this?"** A hiring card doesn't — because when you hire someone you don't configure their competence. You learn what they're good at, then decide what to call them and how you want them to sound.

**The capability is not withheld. It is who they are.** Lisa can't be given new tools for the same reason a copy-editor you hired can't be given a forklift licence by renaming her.

That reframe does real work: it makes the honest limits *readable as facts about a colleague* rather than as locks on a product.

## 3. D1 — Three zones, and the reason each is what it is

| Zone | State | Why it reads as natural, not withheld |
|---|---|---|
| **Who they are** — the capability (from `based_on`): what they're for, the engine, the five tools | **Fixed** | It is the job you hired for. Changing it means hiring someone else — which is exactly what "make another Agent" is. |
| **Who they are to you** — avatar · name · tone · color | **Yours** | Identity costs nothing, gates nothing, routes nothing (personified-agents spec §3). |
| **The engine** | **Yours, but never asked** | Available under a "Details" disclosure, not on the front of the card. The picker asks WHO; a member deliberately building a colleague may look under the hood (spec §4). |

**And a fourth thing that is not a zone — because it is not a control:**

> **What Lisa can't do.** Stated as prose, as a fact about her: *"Lisa works on your files — reads, writes, edits. She can't send email, spend money, or act while you're away. She answers when you ask."*

**This is the cliff, shown without a switch.** A greyed-out `Write action safety` invites a support ticket; a sentence saying *she only ever works on your files* invites nothing, because it is simply true. **No disabled toggle, no "upgrade to unlock", no affordance-shaped hole where authority would go** — the FE must contain no authority control at all, in any state, or D3.a's structural guarantee becomes a CSS property.

## 4. D2 — The form: a quick fill-in, not a config screen

The operator: *"it should be very simple, almost like quick forms fill-in, and here actually focus on the cosmetics like avatar or image upload (like a user profile)."*

```
┌─────────────────────────────────────────────┐
│  [avatar]   Name:  [ Lisa            ]      │
│   upload                                     │
│                                              │
│  Hiring:    ○ Sonnet   ● Critic   ○ Scout   │
│             "Pressure-tests an idea —        │
│              finds the hole before it costs  │
│              you."                           │
│                                              │
│  Tone:      [ Warm and direct. Skips        │
│               preamble. Calls me Kev.  ]     │
│                                              │
│  Color:     ● ● ● ● ●                        │
│                                              │
│  Lisa works on your files — reads, writes,   │
│  edits. She can't send email, spend money,   │
│  or act while you're away. She answers when  │
│  you ask.                                    │
│                                              │
│  › Details (engine: GPT-5)                   │
│                                    [ Hire ]  │
└─────────────────────────────────────────────┘
```

Four fields, one of them optional prose, one an image. **No section headers, no tabs, no "advanced".** The `based_on` blurb renders live under the choice — the answer to *"who am I hiring?"* is on screen, not learned.

**The avatar** rides the built ADR-395 bucket lane (`services/documents.py::IMAGE_TYPES` — png/jpg/webp/gif already accepted, signed-URL read). No new storage; the same lane Phase-A attachments use. It lands as `avatar:` in the manifest — **a sixth identity key**, which the strict-key parser must be widened to accept *deliberately* (§6).

## 5. D3 — Where it lives

The picker's **"+ Make your own"** → this card → `POST /api/agents` (built) → the manifest lands → she appears in the picker, first, tagged as yours.

Editing = the same card over an existing folder (`PATCH`, a second revision on the ledger — the file stays the source of truth, versioned and revertible). **The UI is a door, not a database** (ADR-449's posture).

## 6. D4 — What the build touches

1. `AGENT_MANIFEST_KEYS` gains **`avatar`** — one key, identity-class, deliberate. *(The strict-key parser refusing `avatar:` today is the guard working exactly as designed: widening the vocabulary must be an explicit act, not an accident.)*
2. `POST /api/agents` gains `avatar` + a `PATCH /api/agents/{slug}` for edit.
3. FE: `AgentCard.tsx` (the form) + "+ Make your own" in the picker + the avatar on the lane chip.
4. Gate: the FE contains **no authority control in any state** (the D3.a ratchet, FE-side — asserted against the same banned-word list, over the component source); `avatar` is identity-class (no capability meaning); edit writes a second revision.

## 7. Skills · Tools · Connections — the concepts, with receipts

The operator: *"what I think is also important to state but not readily set up in code."* **Taken literally: stated here, built nowhere.** Each with the receipt for why, so a future session doesn't mistake the concept for a gap.

### Tools — REAL, and showable today
`LANE_TOOL_NAMES = (ReadFile · WriteFile · EditFile · SearchFiles · ListFiles)` — five, and **every Agent has all five** (ADR-411 D3). This is the true answer to "what can it do", and it is what §3's prose sentence says in the member's words. **No per-Agent tool scope**: a field with one possible value lies about being a choice (the registry spec's own rule). If a second value ever exists, `tools` becomes a *capability* key on the kernel row — **never on the member's manifest** (that is the ADR-382 back door).

### Skills — the concept is live; **the machinery is DEAD**
Receipt: `services/orchestration.py:1366` — *"returns False universally; no SKILL.md injection, no RuntimeDispatch."* ADR-118's two-filesystem skill layer was **decommissioned with the render service (ADR-417)**. There is no skill registry, no `SKILL.md` loader, no dispatch.

**So a Skills row on the card today would be an empty box that lies.** The concept — a skill as a folder-local `SKILL.md` the Agent's posture composes, the ADR-118 shape reborn *inside the workspace* rather than on a Docker image — is a genuinely good direction and **fits the folder**: `/workspace/agents/lisa/skills/quote-format.md`. That is the one place the ChatGPT benchmark is ahead of us and worth chasing. **Not now**: it needs a composition rule, a size budget, and a "what happens when two skills disagree" answer — a spec, not a field.

### Connections — the direction the operator named, and the honest blocker
> "I am thinking of expanding connections, for **higgsfield**, or **cursor agent**, or slightly more verticalized agents that need connections and then can do that specific work."

**This is the strongest expansion on the board** — a Designer Agent with Higgsfield is a *different job*, not a different tone, and it is what makes "hiring" more than a costume. Three receipts to carry into that spec:

1. **The connector capture lane is DORMANT** (`CONNECTOR_CAPTURE_ENABLED` off, ADR-404). Connections-as-perception is built and switched off. Whether an Agent's connection rides that lane or is a new thing is the spec's first question.
2. **A connection is a peripheral, not a principal** (ADR-401 D1). "Lisa has Higgsfield" must mean *Lisa can call a tool the workspace has connected* — never *Lisa is a principal with her own credential*. The ADR-425 credential-as-account object is the seam.
3. **⚠️ This is where the cliff gets tested.** A connection that *writes outward* (posts to Slack, spends on Higgsfield) is **consequential action** — the exact thing ADR-307 gates and ADR-380 D2 defers. A "connections" field on a member's manifest would be the ChatGPT `Never ask` dropdown, rebuilt. **The likely shape: connections are a WORKSPACE capability the kernel grants to a `based_on` class, never a key in a member's file** — same capability/identity cut, one level out. That is the spec's central question and it is not answered here.

## 8. Receipts (built 2026-07-16)

**Gate**: `test_agent_registry.py` — **82/82** (from 69). The new §11 block is the **cliff on the surface**: `AgentCard.tsx`'s *body* is asserted clean of `authority`/`autonomy`/`consequential`/`mandate`/`scopes`/`never ask` in any form. (The header comment is excluded from the scan on purpose — it *names* the anti-pattern so the next reader knows why the control is absent.) Siblings green.

**FE**: `✓ Compiled successfully` in a clean HEAD worktree.

**Two real bugs the build caught that no gate would have:**

1. **A route + client namespace collision.** `routes/agents.py` **already owns** `POST /api/agents` and `PATCH /api/agents/{id}` (the ADR-251 roster — the workspace's own entities), and `client.ts` already had an `agents:` key. My `POST /api/agents` would have shadowed a live endpoint, and my duplicate `agents:` object key **silently won in JS**, shadowing the whole roster API. Fixed by naming mine what they are: **`/api/lane-agents`** + `api.lanes.makeAgent/editAgent`. *The collision was not an accident of naming — it is two genuinely different things that wanted the same word. The rename says which is which, and the gate now asserts the roster's namespace stays unsquatted.*
2. **`api.documents.upload` returns a BATCH** (`results[]`), not `{path}` — the avatar read `res.path` (undefined) and would have silently uploaded nothing. Now reads `results[0].workspace_path` and surfaces the per-file error.

**A third caught by the gate itself**: adding `avatar` to the chooser payload, I also let `model` slip in — contradicting the chooser's whole point. The check *"list_agents does NOT serve `model`"* failed and I removed it rather than weakening the check. `based_on`/`tone`/`avatar`/`color` do ride along (the card pre-fills an edit from them; they are the member's own identity choices). **A field the card never renders is a field that leaks.**

**Not covered**: the card under a human click (compiles clean; the form wants an eye — especially the avatar upload round-trip), and the avatar is currently rendered as a colour swatch rather than the uploaded image (the signed-URL read is a follow-on; the path is stored and the manifest carries it).

## 9. One-line statement

**Copy ChatGPT's page and refuse its dropdown: an Agent is a hiring card — avatar, name, tone, and the job you hired them for, with what they can't do written as a fact about a colleague rather than a switch you're not allowed to flip; skills and connections are named as the real expansions, and left unbuilt with their receipts, because the machinery for one is dead and the other is where the cliff gets tested.**

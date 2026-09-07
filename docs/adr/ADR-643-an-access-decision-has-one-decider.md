# ADR-643 — An access decision has one decider

**Status**: Accepted. D1 implemented (`cf8bf18`); D2–D5 sequenced below.
**Date**: 2026-09-07
**Supersedes**: nothing. Completes ADR-501 S1 and closes the recurrence its own
lesson could not stop.
**Related**: ADR-320 (the five-root permission topology) · ADR-373 (the grant) ·
ADR-400 A1 (the organize carve) · ADR-422 D2 (raw intake carved) · ADR-501 S1
(the grant consult on the write doors) · ADR-570 D4 (the prose class) ·
ADR-572 D8 (Text's one always-editable canvas) · ADR-424 D2 (pure-OS folder
creation) · ADR-209 (`write_revision`, the single write path)
**Dimension** (Axiom 0): **Authority** (Axiom 4 — every act has a Who-may).

---

## Context

The operator, looking at the shell: *"I see them surface on existing apps like
text, and files surface to be editable, moveable. I think this goes against our
canon and approach."* Then, on being shown the audit: *"I just want to make sure
our implementation doesn't result downstream, to create similar divergences. And
thus, a more singular, long standing solution and conceptual framing that will
be future proof."*

That second ask is the one this ADR answers. The findings are symptoms; the
framing is the subject.

### The predicates are fine. The composition has no home.

Four predicates govern who may touch what. Each has exactly ONE definition and
each is individually correct:

| Predicate | Question it answers | Home |
|---|---|---|
| `operator_can_organize(path)` | may ANYONE hand-organize a file in this position | `workspace_paths.py` |
| `is_prose_document(path)` | is this the FORMAT class a member edits as text | `workspace_paths.py` |
| `CALLER_WRITE_POLICY[class]` | which roots does this CLASS never write | `workspace_paths.py` |
| `_is_path_locked_for_principal(auth, path)` | may THIS caller write THIS path | `primitives/workspace.py` |

**What has no single home is the act of asking them together.** So every door
hand-assembles its own subset, and they diverged:

| Door | Composed | Asked the grant |
|---|---|---|
| `edit_workspace_file` | prose ∧ carve, then **OR**'d with a prefix list | yes |
| `write_artifact` | html ∧ carve | yes |
| `create_artifact` | carve | **no** |
| `set_default_design_system_route` | — | **no** |
| documents: trash · restore · restore-group · permadelete · folder-trash · folder-move · create-folder | carve only | **no** |
| documents: move · duplicate | carve, then delegates to a primitive | via primitive |
| folder primitives · folder sweep · upload tickets · images | carve only | **no** |

The client has the same disease. `web/lib/workspace/ownership.ts` is a faithful
mirror of the carve law — and sits unused beside three sites in
`file-types/index.ts` and `TextSurface.tsx` that hand-rebuild fragments of it.
One of those *comments that it mirrors the write door exactly* while
implementing two of the door's three carves.

### ⭐⭐⭐ The recurrence mechanism, named

ADR-501 already wrote the lesson:

> **"a permission fix must enumerate the doors, not the deciders."**

It was right, and it could not hold, because **enumeration is not a structure —
it is a to-do list that expires silently.** ADR-501 enumerated the two doors it
knew about. `test_adr570_member_prose_door.py` then ratcheted *those two by
name*, which means the ratchet is constitutionally unable to go red for a door
nobody added to it. Seven more doors were written afterwards, each correct-looking
in isolation, and the gate stayed green through all of them.

The proof is in this ADR's own D1: a gate that DISCOVERS the roster instead of
naming it found four doors a careful manual audit had missed, on the commit that
introduced it.

### ⭐⭐ A carve law is not an authorization check

The deepest confusion, and the one that made the divergence look reasonable at
every individual call site: `operator_can_organize` LOOKS like permission. It
returns a boolean about a path and raises a 403.

It is a **filesystem-integrity rule about path shape** — "don't rename a file
another program finds by path" — and it returns the SAME answer for every
principal. `constitution/`, `persona/`, `governance/` and `contract/` all PASS
it, deliberately, because ADR-320 says those are the operator's own to
reorganize. A door that asks only this question has asked nothing about the
caller.

Measured: a principal whose grant resolves to the `agent` class gets `WRITE=403`
and `TRASH=200` on all four roots. **A principal who may not write a file could
destroy it.**

### ⚠️ And N=1 is no longer true

`primitives/workspace.py:2616` reads *"At N=1 (every live workspace) the only
grant rows are the owner's with NULL scopes"*, and reasoning downstream inherited
it. `principal_grants` on production, 2026-09-07: **11 owner · 5 member ·
11 foreign-llm · 1 viewer**. Sixteen non-owner grants whose class is locked from
four roots they could trash. Every "latent at N=1" judgement in this area is
stale and must be re-taken.

### One more thing the audit found: "system" means three different things

`workspace_paths.py:252` says it outright — *"group is the operator zone,
semantic_class is the permission class; two orthogonal facts."* There are
actually three, and they do not coincide:

| Notion | Members |
|---|---|
| **display zone** (`WORKSPACE_ROOTS[…].group == "system"`) | SEVEN roots fold under "System files" |
| **organize carve** (`operator_can_organize`) | `system/`, raw `inbound/`, `_*.{yaml,yml,json}` anywhere |
| **write lock** (`CALLER_WRITE_POLICY`) | FIVE roots for a non-owner; `system/` only for the owner |

So a file the UI files under "System files" is **not thereby protected**, and
`MANDATE.md` being editable is CORRECT for the owner and wrong for everyone
else. This is not a bug to be fixed by hiding things; it is a fact the surfaces
must be able to ask about per viewer, which is what D3 provides.

---

## Decision

**An access decision is a single function of (principal, path, verb), and no
door composes its own.**

### D1 — Every door asks the principal, and the roster is DISCOVERED ✅ `cf8bf18`

Seven doors and one loop gained the grant consult. The ratchet
(`test_adr501_every_door_asks.py`) walks the AST for handlers reaching a
mutating substrate call and requires each to consult, itself or via
`execute_primitive`. **It names no doors.** It carries a not-vacuous floor so a
rename of the mutating verbs cannot leave it green over zero, and an EXECUTED
check that the carve law and the grant gate genuinely disagree.

⭐ If a future change adds a name to a literal roster in that file, the gate has
been defeated. Fix the door, not the list.

### D2 — `resolve_access(auth, path, verb) -> Decision` is the one decider

One function, in one module, composing all four predicates in a fixed order and
returning a structured answer:

```
Decision(allowed: bool, reason: str | None, code: str | None)
```

The predicates KEEP their homes and their gates; they become **inputs to one
decider** rather than ingredients each caller measures out. A door's only job is
to name its verb and honour the answer. Verbs are the substrate's own:
`read · write · create · move · rename · trash · restore · destroy`.

⭐⭐⭐ **This is what makes the property structural rather than diligent.** A new
door cannot accidentally ask a SMALLER question, because there is only one
question. A new verb must be added to the decider, where the gate can see it.

`reason` is not decoration — it is what D3 and D4 serve to the client, so a
refusal explains itself in the operator's words rather than as a bare 403.

### D3 — The client is TOLD the decision, never re-derives it

Operator ruling, 2026-09-07 (*"Server decides, client is told"*). The file and
tree payloads carry the decision per path. `ownership.ts` and the three
hand-rebuilt sites in `file-types/index.ts` + `TextSurface.tsx` are **DELETED**,
not kept in sync — a mirror that must be maintained is a divergence with a
schedule.

⚠️ This is the half that makes the framing durable. A served decision cannot
drift from the decider, because it IS the decider's output.

Files' Windows-Explorer model is **preserved exactly** (ADR-400 A1 / ADR-422 D2):
offer the verb, explain the refusal. That model was never the problem, and this
ADR does not grey out menu items. What changes is only where the explanation
comes from.

### D4 — Text routes only prose, and renders read-only what the viewer cannot write

Operator ruling, 2026-09-07 (*"Both: route only prose, read-only for the
unwritable"*).

- **Route only prose.** `resolveSurfaceApplication` must make true the claim its
  comment already makes — it mirrors the write door, including the carve it
  currently omits. `governance/_autonomy.yaml` reaching a MARKDOWN canvas is the
  case the operator's report was sharpest about: machine-parsed YAML rendered as
  prose, comments as H1 headings, keys as inline code, and an inspector
  asserting *"it stays a .md file."*
- **Read-only for the unwritable.** ADR-572 D8's one-always-editable-canvas is
  **amended, not overturned**: there is still ONE canvas, and it still has no
  modes. It gains a single non-editable state driven by the served decision.

⭐⭐ A canvas that accepts keystrokes it will 403 is strictly worse than a menu
item that explains itself: the organize verbs are one-shot acts with a pre-empt
and a styled reason, while the canvas is a CONTINUOUS affordance whose failure
arrives asynchronously, after typing, as a raw error string. `studio.py:690`
documents this exact split-brain as already-fixed for Studio. It was reproduced
verbatim in Text.

### D5 — The composition is a conjunction, and stale premises are re-taken

- `editable_prefixes` in `edit_workspace_file` is **deleted or conjoined**. It
  is currently OR'd with the carve law, so `/workspace/system/` is re-admitted
  one line after the carve law rejects it. Today the write is still refused —
  but only because `CALLER_WRITE_POLICY` happens to lock `system/` for every
  class. **A refusal that works by accident is not a decision.**
- Every "latent at N=1" comment in the access path is re-taken against the real
  grant table, starting with `primitives/workspace.py:2616`.

---

## Consequences

**A door becomes boring.** Name your verb, honour the answer. That is the whole
contract, and it is the point: the interesting judgement lives in one place
where it can be read, tested and changed.

**The FE stops being a second source of truth** about a rule it does not own.

**One risk, stated plainly.** A single decider is a single point of failure: a
bug in `resolve_access` is a bug everywhere at once. That is the trade being
made deliberately — a bug in ONE place is findable and gate-able, whereas the
divergence being replaced was unfindable by construction, and had to be
discovered by an operator looking at a screen.

**What this ADR does NOT do:** it does not narrow the owner's write reach over
`constitution/` and `persona/` (ADR-320 says those are theirs), it does not grey
out Files' context menu, and it does not add a permission concept. Every
predicate it composes already existed. The only new thing is that they are asked
together, once.

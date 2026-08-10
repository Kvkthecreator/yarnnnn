# ADR-512 — The File Is the Unit of Interop: One Verb Contract, Species-Blind, Bound Per Channel

> **Status**: **Accepted — operator-ratified 2026-08-02** (the file-as-the-what discourse
> session: full share/chat audit → axiomatic re-derivation → the Finder verb mapping).
> **Completed by [ADR-543](ADR-543-the-interop-surface-speaks-the-kernel-verbs.md)
> (2026-08-10)**: the D3 kernel verb `list` — named in the contract but never bound at
> the MCP surface — ships; the memory verbs this ADR tolerated beside the file verbs
> (§9's evidence-gated rename) retire in full (`recall`→`search`, `trace`→`history`,
> `remember` dissolved into `save` + the taught filesystem model). One ontology across
> the manifest; §10's "the costume ends" is now true of the verbs themselves.
> Phase 1 implemented in the same pass: the `open` verb + the connector self-description
> re-frame + the handle grammar + ADR-465 Phase D (`share-as-view`).
> **Amended 2026-08-03 (§8a — the `save` verb, operator delegation "implement all
> tiers")**: the write half of the exact-version guarantee ships with read-before-write
> CAS conflict semantics. Tier 2 of the same delegation landed D6's Get-Info reach panel
> + attach-as-bind; ADR-513 + ADR-465 B/C/F landed as the arrival arc.
> **Date**: 2026-08-02
> **Authors**: KVK (operator) + Claude (collaborator)
> **Hat**: A (kernel invariant + interop surface; the GTM canon consumes it per ADR-508 D3)
> **Dimensions**: Substrate (Axiom 1 — what the record's unit is) + Identity (Axiom 2 —
> who may speak which verbs) + Channel (Axiom 6 — how the contract binds per host)

**Supersedes**: [ADR-368](ADR-368-memory-first-interop-surface.md) **D1's ontology ruling
only** — "the surface is the user's memory mental model." ADR-368's **Correction 1**
(consumer hosts chain ~3–5 tool rounds → multi-step composition lives server-side) is
**preserved as a binding constraint** on every consumer binding, and its D3–D6 mechanics
(the dump-into-inbound model, operator-visibility, the gate, the foreign-caller audit
lens, per-request identity, protocol-agnostic verbs) stand unchanged.
**Revives (at contract altitude)**: [ADR-311](ADR-311-primitive-interop-surface.md)'s D2
verb contract and §3 (revision-archaeology as the killer capability). Its D1 delivery
mechanism (the host chains raw primitives) stays dead — ADR-368's channel evidence killed
the *delivery*, not the *ontology*, and this ADR separates the two rulings ADR-368 merged.
**Amends**: [ADR-465](ADR-465-share-the-membership-primitive-and-the-two-doors-unification.md)
(records the partial ratification — see §6) · `docs/architecture/primitives-matrix.md`
(MCP-mode rows gain `open`) · `docs/features/mcp/` (framing) · the connector
`instructions` block (`api/mcp_server/server.py`).
**Relates to**: ADR-209 (attributed substrate — the thing every verb operates on) ·
ADR-222 (the syscall-ABI vocabulary this ADR uses) · ADR-310 (one moat, two faces —
unchanged) · ADR-413 (the invocation contract: projection in, attributed revision out) ·
ADR-457 D2 (the transcript is never the system of record) · ADR-495 (the species-law
knife, applied here one layer up) · ADR-504 (the interop principal invariant — this is
its verb-surface companion) · CANON-LOCK-2026-07-30 (the ICP whose mental model selects
the file).

---

## 1. Context — the costume outlived the era

The interop surface has swung twice: intent tools (ADR-169) → a ratified-never-built
pure-primitive surface (ADR-311) → the live memory verbs `remember`/`recall`/`trace`
(ADR-368). ADR-368 made **two rulings in one motion** and only one of them still holds:

1. **The channel ruling** (empirical): consumer chat hosts execute ~3–5 tool rounds per
   turn, so composition must live server-side. **Still true. Binding on every consumer
   compound in this ADR.**
2. **The ontology ruling** (a match-the-user's-mental-model judgment): the surface speaks
   "memory." **Dissolved by the canon underneath it.** The v19 canon lock
   (2026-07-30) moved the ICP to the copy-paste seam — *"I'm the human clipboard between
   my AI and my team"* — and what the clipboard carries is **work product: files**, not
   ambient memories. The hero subhead promises *"co-work on shared files and documents."*
   ESSENCE §What-YARNNN-Is-Not opens with *"not a memory feature."* Yet the connector
   introduces yarnnn to every foreign LLM as *"the user's durable, attributed memory."*
   ADR-368's own selection criterion — match the consumer's mental model — now selects
   the file.

The axiomatic re-derivation (this session) confirms the deeper fact: **what settles is a
file.** Axiom 1 (state lives in files) + ADR-209 (every mutation is an attributed,
parent-pointered revision through one write door) + ADR-457 D2 (the transcript is never
the system of record). *Conversation* is member-experience scope; *context* is a view
over a region of the file plane; *memory* is a region of it (`operation/memory/` is a
directory of files). The moat statement — "the system of record where human and AI work
settles" — bottoms out in exactly one object: **the attributed file with its revision
chain and its grant reach.**

## 2. D1 — The record's unit is the attributed file; every face serves it

The first-class object on **every** face — cockpit, apps, interop — is the file (content
+ attribution + revision chain + grant reach). Memory, context, and conversation are
views or regions of the file plane, never peer ontologies. A surface may *speak* in a
view's vocabulary (a compound named `recall` is fine); it may not *present* a view as the
system's unit.

## 3. D2 — The species-blind verb invariant (ADR-504's companion)

ADR-495 found `scope: private|shared` was species law in substrate costume. The same
audit applied one layer up finds the live tool surfaces keyed on principal species: the
member and the kernel agent get file verbs (the primitive matrix); the external LLM — a
first-class principal in the *ledger* per ADR-504 — gets only memory verbs. A principal
that can be *recorded* as a co-worker but only *offered* the vocabulary of a diary is
half a principal.

> **Invariant**: the verb ontology is one contract for every principal. What varies per
> principal is the **grant** (scopes, roles, locks) and per channel the **binding**
> (how the contract is served) — never the ontology. Any future surface that offers a
> principal class a different *kind* of verb set (not a narrower *reach*) must supersede
> this ADR explicitly.

## 4. D3 — Two layers: the kernel verb contract, and channel-shaped bindings

- **Layer 1 — the contract (kernel, protocol-agnostic, species-blind).** The file +
  revision + membership verbs the kernel already owns: read · write · list · search ·
  revisions (`ListRevisions`/`ReadRevision`/`DiffRevisions`) · **share** (the grant act,
  ADR-465 D1) · trace (provenance). ADR-311 D7's framing is re-ratified: **the verbs are
  the contract; every surface — MCP, the in-app primitives, future A2A/direct-API — is a
  binding of it.**
- **Layer 2 — bindings (per channel, compound where the channel demands it).** A
  consumer chat host gets few, server-composed compound tools (ADR-368 Correction 1,
  binding). An agentic host may get the raw contract. An in-app surface mounts gestures
  (the share sheet, attach-in-chat). **Compounds are compositions of Layer-1 facts and
  say so; a compound may never introduce an object the contract doesn't have.** Macros
  never precede syscalls.

The Finder mapping (the operator's reference set, 2026-08-02) is the sanity check: Open →
resolve+read; Open With → renderer choice (ADR-436); Get Info → trace + attribution +
reach; Duplicate/Save-As → seeded write; Make Alias → reference edge (ADR-448); Move to
Trash → the retention arc; Compress/Export → the egress lane (ADR-510). Nearly every row
already exists in the kernel — the defect was never the ABI's absence; it was that only
some principals were told it exists.

## 5. D4 — `open`: the deterministic read joins the consumer binding (additive)

The consumer binding gains a fourth verb, **`open`**: resolve a **named file** (a
workspace-relative path or a D5 handle) → content + attribution + recent revision
summary, composed server-side in one round (the channel constraint holds — `open` chains
nothing on the host side).

`open` is the missing half of the co-work claim: `recall` is *search-and-hope*;
`open` is *this exact file* — the exact-version guarantee that makes "work on the
shared doc from your own AI" real. Read-only; the gate and the ADR-311 D5 foreign-caller
audit lens apply as to every read.

**Deliberately additive**: `remember`/`recall`/`trace` keep their names and behavior.
They are re-described as what they always secretly were — compounds over the file plane
(`remember` = attributed write into the memory region; `recall` = ranked search) — but a
rename/removal of live connector verbs is a breaking UX change that requires observed
evidence, not this ADR's derivation. The connector `instructions` block is re-framed to
the workspace/co-work ontology in the same pass (the self-description was the loudest
costume).

## 6. D5 — The handle grammar: one canonical way to name a file across the boundary

> `yarnnn://workspace/{workspace-relative-path}`

is the canonical cross-boundary file reference. It is transport-neutral text: the Studio
"Copy AI reference" affordance emits it (promoted from app-local prose to kernel
grammar), `open` accepts it (alongside a bare workspace-relative path), and future
bindings (A2A, direct-API) resolve the same form. A handle names a file, never a
revision (revisions ride `trace`/`ReadRevision`); it carries no authorization — reach is
always the caller's grant (D2). Extension to a revision-pinned form
(`yarnnn://workspace/{path}@{revision_id}`) is reserved, not shipped.

## 7. D6 — Share splits across the layers; reach vs egress stays honest

The share **act** is Layer 1 — ADR-465 D1's membership primitive (a grant + a handle,
never a copy). The share **sheet** — destinations: into a conversation, to a member, to
an external principal's AI, copy link — is Layer 2, mounting the one primitive
(ADR-492 D6.e already ruled: chat mounts share, never owns it). Two disciplines bind the
future sheet:

- **Reach vs egress**: grant destinations (one file, N principals) and egress
  destinations (a copy leaves the ledger — download, PDF, export) render as visibly
  different classes. A sheet that flattens them launders the moat.
- **Attach-in-chat is bind-then-maybe-grant**: within the commons an attach is a
  reference edge (ADR-448), no grant change; the grant question surfaces inline only
  when a cast member lacks reach (the paste-a-Drive-link pattern).

**Ratification record (2026-08-02, this session's operator discourse):** ADR-465 **D3
(`share-as-view`) and D5 (the interop `share` verb — as direction) are ratified**;
ADR-465 **D2 (join-only genesis) and D4 (the switcher) remain open** and are untouched
here. ADR-465 Phase D ships with this ADR's pass; Phase F waits on the Phase B/C
(genesis-invariant) decisions.

## 8. What this pass builds / defers

**Built (Phase 1, this pass):**
1. `open` on the MCP binding (read-only, path/handle-addressed, server-composed) +
   re-framed connector `instructions`.
2. The D5 handle grammar (emit: Studio Copy-AI-reference; accept: `open`).
3. ADR-465 Phase D — `share-as-view`: the share-creation shape choice
   (`member` | `viewer`), the accept-time birth-narrowed grant (powerbox axes:
   `write_scopes=[]`, `read_scopes=[artifact]`), honest accept copy. One grant model
   holds (ADR-437 D4.3): a viewer is a member grant narrowed at birth, not a new access
   object; an existing broader grant is never downgraded by a later view-link accept.

**Deferred, named:** renaming/removing `remember`/`recall` (evidence-gated);
`save`/write on the consumer binding (wants the same care as `open`, next); the MCP
`share` verb build (ADR-465 F, after B/C); the Layer-2 share sheet + attach-in-chat FE;
the Get Info panel; unauthenticated artifact view (its own ADR — it touches the public
boundary); ADR-368's deferred-primitives back door for agentic hosts (still unbuilt;
still the stated direction).

## 8a. Amendment (2026-08-03) — `save`: the write half of the exact-version guarantee

The consumer binding gains **`save(reference, content, base_revision?, message?)`** —
an attributed revision to a named file, from any host. The design question §8 deferred
(conflict semantics over a boundary where the host holds no session) resolves onto the
kernel's own CAS seam (ADR-406), not a new mechanism:

- **Read-before-write is the contract.** For an EXISTING file, `base_revision` (the
  head revision id `open` returned) is **required** — omitted → `base_required` + the
  current head's attribution, never a write. Last-write-wins is refused: it would
  corrupt the exact-version guarantee `open` established. For a NEW file, `base_revision`
  is omitted and the write creates it.
- **The race is closed at the ledger, not by a check.** The WriteFile primitive threads
  `expected_parent_version_id` into `write_revision`, whose ADR-406 linearity guard
  (migration 197) makes the compare-and-set atomic. A lost race returns a structured
  `stale_write` conflict carrying the intervening head's attribution — *who* moved past
  you, when, and why (ADR-405: a conflict is a witness moment) — and the host's
  resolution is revert-as-write: re-`open`, merge in its own context, `save` again.
- **All consequence at the gate, unchanged** (ADR-311 D4): `save` dispatches through
  `execute_primitive` under the mcp caller identity — `CALLER_WRITE_POLICY["mcp"]`
  bounds what it can touch (the operation commons; never governance/persona/system),
  attribution rides ADR-288, and the empty-content guard + kernel-style retrofit apply
  as to every write. `save` adds no second write door.
- **Scope**: overwrite of one named file. No append mode (remember owns accumulation),
  no multi-file transactions, no delete/move (in-app verbs; a foreign principal asking
  to reorganize the commons is a conversation, not a syscall).

## 9. Rejected alternatives

- **Keep the memory ontology, add file verbs beside it** — two ontologies on one
  surface is the muddiness ADR-368 §4 warned about, now permanent. Rejected: one
  ontology (the file), memory re-described as a region.
- **Full re-cut now (rename remember→save, recall→search)** — breaks live connector
  muscle-memory on a derivation, not evidence. Rejected; evidence-gated.
- **A raw file API on the consumer binding** — re-runs ADR-311 D1 against ADR-368's
  standing channel evidence. Rejected; the contract is served compound where the channel
  demands it.
- **An artifact-scoped access object for view shares** — ADR-437 D4.3 already refused
  the second grant model; the powerbox narrows the one model. Rejected again here.

## 10. The one-line statement

**The record's unit is the attributed file, so there is one verb contract — open · save ·
share · trace and kin — owned by the kernel, species-blind by invariant, and bound per
channel; memory was a costume the interop face wore for one ICP era, and the era ended
2026-07-30.**

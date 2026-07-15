# ADR-457: Think and Make — the Service Model

**Status**: Accepted (2026-07-14, operator-ratified through a three-pass discourse: first-principles
rederivation → adversarial re-check → live filesystem stress test; ruling: "execute, document
towards it even stronger"). This is the service-model capstone of the ADR-435→454 subtraction arc:
it names what the product IS now that the desk is front-and-center, and commits to it.
**Date**: 2026-07-14
**Dimension**: Purpose (what the service is for) + Channel (where its verbs live). The deepest
Purpose-dimension ADR since ADR-207 — it re-cuts the *product identity*, not a surface.

**Amends**: ADR-454 (the verb pair renames: Converse → **Think**; ADR-454's census and chrome
decisions stand) · FOUNDATIONS DP29 (fourth amendment, v9.18) · ESSENCE (v16 companion — the
desk/record two-layer statement) · SERVICE-MODEL (v2.0 vocabulary) · GLOSSARY (v3.3).
**Re-cuts, does not reverse**: the era-1 interop-first posture (ADR-375/380 §5). The substrate
commons reached from every AI remains a real door and a real wedge — but it is the **floor**, no
longer the **product identity**. Two doors, one moat (ADR-310) is unchanged; what flips is
investment priority (D5).
**Preserves**: the moat statement (ESSENCE v15 — the system of record where human and AI work
settles) as the *moat* statement; every posture-invariant investment (ledger, powerbox,
projection, block grammar, invocation contract); the ambient steward (ADR-454 D3); the app-seam
canon (apps are contractors; Studio + chat are the MacWrite/MacPaint exception, see D6).

---

## 1. Context — the shift, named

The product's history has three postures, each encoding who we believed the user was:

1. **The hum** (era 1, the interop wedge): yarnnn as a Dropbox-like settlement layer behind other
   AIs. The user was *absent* — they worked in ChatGPT/Claude; Freddie tended the record. The
   moat was real; the flaw was structural: **a settlement layer generates trust, not sessions.**
2. **The supervised operation** (the cockpit era): the user was a *supervisor* — Decide, Read,
   Tune. Direct manipulation beat conversational supervision every time it shipped, and the
   cockpit dissolved (ADR-435).
3. **The desk** (now): multi-member, multi-principal, multi-engine, Studio, the ambient steward.
   The user is a **thinker and maker**. The OS framing stops being an architecture metaphor and
   becomes the literal experience claim.

The reframe in one sentence: **the backdrop hum did not disappear — it was demoted from product
identity to product floor.** Every OS-class product has this shape: the moat-grade machinery
(the filesystem, the ledger, the index) is invisible; what is felt is the desk and the apps. The
ledger is felt at **staged moments** — the *why-is-this-here* moment (`trace`), the
*correct-once-everything-inherits* moment, the *leave-with-everything* moment, and (new, D3) the
*settle* moment — never as the ambient experience itself.

### The derivation (first principles, held under adversarial re-check)

Knowledge work with AI reduces to five acts: **perceive · think · make · settle · govern**.
Perceive is increasingly ambient (connectors, MCP, uploads); settle is the floor; govern is
dials (ADR-454). Exactly two acts are *felt* daily — think and make — and their media differ by
the phase of work: divergent work has no stable visual state, so its medium is **dialogue**;
convergent work does, so its medium is **the artifact** (direct manipulation — proven in-house
every time it shipped: ADR-444/446/453). *Words for exploring, hands for shaping.*

> **The service, in one sentence: a desk with two verbs — Think and Make — over a commons that
> remembers.**

The derivation has independent bite (it is not a rationalization of the current product): it
predicted the missing settle moment (D3), the dormant perceive lane, and the shared-discussion
gap (comments) before any of them were shipped.

## D1 — The verb pair is **Think · Make**

ADR-454's pair (Converse · Make) named one verb by its medium and one by its job. Both verbs now
name the **job**:

- **Think — `/chat`.** Workspace-scoped. Research, ideation, weighing, deciding — grounded in
  the commons, multi-engine, and *landing* (D3). The asset side: chat works the workspace's
  knowledge.
- **Make — `/studio`.** Artifact-scoped. Composition, shaping, polish. The dividend side: Studio
  works the deliverables.

Surface **labels stay** Chat and Studio — users should not have to learn a noun; the verbs are
canon vocabulary and the design brief. One caveat is written down deliberately: **the verb names
the north star, not the exhaustive job list.** Chat retains the member's-hands operational jobs
(file verbs, uploads, organizing, learn-from dispatch — ADR-408 A2) as *means*; thinking is the
*end* they serve.

## D2 — The pipeline: think → settle → make

The two surfaces are not siblings; they are a pipeline, and its embryo already ships: the
derive-recipe registry (ADR-450) lands `context-brief` in chat and `deck`/`prd` in Studio.
Canonized: **thinking distills into the commons; making learns from the distillates.** Research
in a lane → settle a brief (D3) → "Learn from" the brief into an artifact. The multi-user form
of the same principle: **diverge privately, settle publicly** — lanes stay member-private
(ADR-407, correct), and collaboration happens through what lands on the commons (distillates,
artifacts, and the forthcoming comments object).

## D3 — The settle verb (chat's flagship; direction ratified here, built in the chat waves)

A first-class **"keep this"** act: distill a lane conversation's insight into a substrate
note/decision/brief — an attributed derived act citing the conversation (`derived_from` → the
lane; DP32 applied to thought: the transcript is the raw, the distillate is the derived citing
act). It lands per D4 **and embeds on write**.

Three birds, one verb:
1. **The felt moment of the moat** — the on-screen instant where episodic becomes cumulative.
2. **The missing derive organ** — the connector→recall chain has been broken at *derive* since
   the ADR-401 audit (autonomous derive never fired). The settle verb is that organ,
   human-staged instead of autonomous.
3. **The retrieval fix** — settled products embed, so Think's grounding reads an indexed corpus
   (today, Studio artifacts and lane writes are mostly *not* embedded — embedding fires only on
   the explicit primitive, wake-derives, and uploads).

## D4 — The think-home convention

Thinking products land as **dated markdown in a meaning-folder under `operation/`**
("Documents"): `operation/{topic}/{yyyy-mm-dd}-{slug}.md`, with the Documents root as fallback
when no topic fits. This canonizes the live de facto pattern (the busiest workspace already does
exactly this) and the `PARTICIPANT_FILESYSTEM_MODEL` prose — no new namespace, no kernel noun,
no scaffolding. The settle verb targets this convention. (The stress test found
`operation/memory/` and `operation/decisions/` were demo residue, not conventions — they are
explicitly *not* canonized.)

## D5 — The floor is posture-invariant; the desk leads

Two doors, one commons (ADR-310, unchanged): work **in** yarnnn (the desk) or reach the commons
**from** any LLM (the interop face). What this ADR flips is the **investment thesis**: era 1 bet
distribution on the interop face; this era bets retention on the desk. The bet is smaller than
it looks because every irreversible investment — the ledger, powerbox, projection, block
grammar, invocation contract — serves both postures identically. If D8's falsifiers fire,
priority flips back without architectural loss. **The moat is not being bet; the roadmap is.**

## D6 — The MacWrite/MacPaint doctrine + the guards

An OS bootstraps through first-party apps that teach the platform's idioms until third parties
arrive. Chat and Studio are yarnnn's MacWrite and MacPaint — deep first-party investment is the
OS bet, not a betrayal of it, under one discipline: **every capability they gain must decompose
into kernel ABI + app behavior** (mounts, grants, projection, derive recipes, the block grammar
— the pattern already held).

The guards, held as discipline (not doubt):
- **The floor-leverage test**: every chat(think) feature must exploit the floor — grounding,
  settling, provenance, multi-engine. Generic chat-parity features are refused; that treadmill
  is unwinnable and off-moat (engines are rented, ADR-417/420).

  > **Amendment (2026-07-15, operator-ratified in the chat(think) three-axes discourse):** the
  > test as written over-rotated — there is a minimum chassis below which the surface is not
  > usable daily, and no differentiation lands on an unusable chassis. Refined guard: **catch up
  > to the bar, differentiate above it; never compete ON the bar.** The cut is *mechanics vs
  > features*: turn mechanics (stop/regenerate/edit/copy), attachments, rendering quality, and
  > conversation hygiene are what a chat **is** — owed as a one-time enumerated debt (the
  > Phase-A chassis five), not tracked against competitors' release notes. Features chat
  > products *compete on* (voice, GPT-store analogs, image generation, canvas, memory-settings
  > UI) stay refused behind the floor-leverage test. A bar item enters the debt list only when
  > its absence blocks daily use or contaminates D8 (an unusable chassis makes falsifier 1 fire
  > for the wrong reason). Discourse capture:
  > `docs/analysis/chat-think-three-axes-discourse-2026-07-15.md`.
- **The two-front guard**: chat's waves stay *shallow* — framing plus floor-riding features
  (grounding UX, the settle verb, research-as-rented-tool, multi-engine polish). Studio carries
  the deep-editor investment (the ADR-455/456 waves). If a chat feature needs a new axiomatic
  layer, it is out of scope by default.
- Chat is **not** artifact-editing #2 (the bound lane in Studio owns artifact conversation,
  ADR-440 D3) and **not** the OS shell (governance stays in Settings/Activity; the steward stays
  ambient, ADR-454 D3).
- **The acquisition wedge is an open question, named honestly**: grounding and settling are
  retention features. Candidate wedges — multi-engine/BYOK economics, the shared team commons,
  MCP-side capture funneling into the desk — are plausible and unproven. GTM must not pretend
  otherwise (the NARRATIVE re-cut is deferred to its own pass for exactly this reason).

## D7 — Sequencing preconditions (from the 2026-07-14 live stress test)

The filesystem **model** held under stress (meaning-placement is the live convention; revision
churn is moderate; no embedding-COGS runaway). The **handling** has four named findings that
become this ADR's sequencing:

- **P1 — Media is gated on the storage phase.** The binary path does not exist (every write
  decodes utf-8 — `storage_backend.py:191`; stream implementation deferred) and the ledger has
  **zero GC** (live receipt: 34,698 blobs vs 464 live version references — ~99% orphans; account
  wipes never reclaim blobs). Studio's image/video block expansion ships **after** ADR-427
  Phases 2–3 (binary + pins-as-GC-roots), executed as one unit. No media promises before it.
- **P2 — The multi-user wave is a prerequisite, not polish.** Two simultaneous editors today get
  a lossy 409 (the second editor's in-flight edits are discarded on blind reload —
  `StudioSurface.tsx` catch-and-reload). The wave: courteous 409 (preserve local text, offer
  re-apply), presence soft-awareness ("someone else has this open" — never merge/CRDT, ADR-406
  reaffirmed), and **comments-as-substrate** (the 2026-07-13 discourse; drafted as its own ADR).
- **P3 — The root-directories invariant (declared; migrated coherently, not piecemeal).** The
  workspace root converges to **directories only**. Root-level machine files (`_recurrences.yaml`,
  `_hooks.yaml`, `_captures.yaml`, `_capture_signal.yaml`, `_program.yaml`,
  `_workspace_guide.md`) migrate to `system/` as **one coherent move** when the scheduler/walker
  is next opened — never a partial split. **This pass ships the display half + hygiene**: loose
  `_*` root files fold into the Files System zone (they currently surface beside Documents), and
  the five orphan `/agents/system-agent/AGENT.md` rows (pre-ADR-414 residue, no live writer,
  last write 2026-07-04, stored outside the `/workspace/` prefix) are tombstoned.
- **P4 — Grounding reads a partially-indexed corpus** until D3 ships (see D3 item 3). Known,
  accepted, fixed by the settle verb rather than by resurrecting autonomous embedding sweeps.

## D8 — Falsifiers (instrumented, not vibes)

Within 60–90 days of the chat waves shipping, three signals — all readable from
`execution_events` + session counts, no new telemetry system:

1. Sessions concentrate in Studio and chat is used only as a command line → Think was the wrong
   frame for chat; chat reverts to hands+capture and thinking stays external.
2. The settle verb goes unused after honest staging → the compounding moment is not felt; GTM
   must not lead with it.
3. MCP traffic dwarfs desk traffic among real users → the hum is the true wedge; investment
   priority flips back per D5.

These are printed here so future sessions evaluate the bet against declared criteria rather than
re-litigating it.

## 9. Shipped in this pass (code)

Deliberately small — the doc hardening is the deliverable; the code is the safe cleanup subset:
- `web/app/(authenticated)/files/page.tsx`: loose `_*` files at the workspace root fold into the
  System files zone (display; the substrate move is P3's coherent migration).
- `api/scripts/oneshot/adr457_tombstone_orphan_agent_files.py`: attributed deletion of the five
  out-of-prefix `/agents/system-agent/AGENT.md` orphans.

## 10. Deferred (each named with its owner-pass)

1. **The chat(think) wave scoping** — the next discourse: grounding UX (scoped sources +
   citations), the settle verb spec, research-as-rented-tool, multi-engine polish. Waves mirror
   the Studio session's pattern. *Discourse opened 2026-07-14→15 and captured (not yet locked —
   the operator holds further consideration points) in
   `docs/analysis/chat-think-three-axes-discourse-2026-07-15.md`: three axes (chassis / rooms /
   axiomatic uniques), the orchestration re-cut (designation resolves invocation; the unified
   Conversation object), the Phase-A chassis greenlit unconditionally. The D6 guard amendment
   above is the one ratified doc change; the horizon ADR takes the next free number at draft
   time (459 was taken by the Studio lane).*
2. **The comments ADR** (the shared-discussion object; shape agreed in the 2026-07-13 discourse).
3. **NARRATIVE/GTM lead re-cut** — external copy shifts from substrate-portability-led to
   desk-led-with-mechanism; its own pass, operator eyes on wording (ESSENCE v16 lands the
   internal canon now; the external story follows).
4. **P3's coherent root migration** — with the next scheduler-touching pass.
5. **ADR-427 Ph2–3** (binary + GC) — before any media block.

## Key files

Docs: this ADR · `docs/architecture/FOUNDATIONS.md` (DP29 fourth amendment, v9.18) ·
`docs/ESSENCE.md` (v16 — the desk/record two-layer statement) ·
`docs/architecture/SERVICE-MODEL.md` (v2.0 vocabulary) · `docs/architecture/GLOSSARY.md` (v3.3
Think·Make entry) · amendment banner on ADR-454.
Code: `web/app/(authenticated)/files/page.tsx` (loose-root-file zone fold) ·
`api/scripts/oneshot/adr457_tombstone_orphan_agent_files.py` (orphan hygiene).
Evidence: the 2026-07-14 live stress test (root census, writer→placement map, revision-chain
depths, storage/GC/concurrency receipts) — summarized in §D7; queries reproducible read-only.

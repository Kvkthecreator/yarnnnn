# Chat(Think) — the Three-Axes Discourse

**Status**: Discourse capture (2026-07-14 → 15), **deliberately not ratified**. The operator ruled:
document the discourse, proceed on the Phase-A chassis unconditionally, and **hold the strategic
layer open** — further consideration points are coming before anything below locks into the
horizon ADR. Nothing in §4–§8 is canon; §3 is.
**Owner-pass**: the chat(think) horizon ADR (ADR-457 §10 item 1). It takes the **next free ADR
number at draft time** — ADR-459 was taken mid-discourse by the parallel Studio lane
(`ADR-459-the-artifact-reads-as-what-it-is.md`).
**Relates to**: ADR-457 (the service model this scopes within — D6 amended by this discourse),
ADR-454 (two-verb census), ADR-411 (the lane contract this would subsume), ADR-408 (D4 router,
D6 lanes — the no-shared-chatrooms rejection this would amend), ADR-450 (bindings pattern),
ADR-440 D3 (the binding mechanism), ADR-402/413 (routing-as-kernel-data precedent).

---

## 1. The frame: three axes (ratified as a frame)

The operator re-cut the chat build from "wave list" into three axes:

- **Axis 1 — the chassis (catch-up)**: the minimum 1:1 bar below which the surface isn't usable
  daily. Must-meet, not differentiation.
- **Axis 2 — rooms (the assumed differentiator, adversarially confirmed)**: shared, attributed,
  multi-model (and later multi-human) conversation over the commons. The combination —
  cross-vendor models addressing each other's turns + multiple humans + one attributed ledger +
  settle — is unoccupied, and the cross-vendor half is structurally ours (vendor-neutral by
  construction; single-vendor hosts by impossibility).
- **Axis 3 — the axiomatic uniques**: settle (the flagship, ADR-457 D3), scoped grounding +
  citations, trace affordances. The prior session's W1/W2 re-homed.

## 2. Falsifier hygiene (why Axis 1 is W0-adjacent)

An unusable chassis contaminates ADR-457 D8: falsifier 1 (chat-as-command-line-only) can fire
because Think was the wrong frame *or* because there is no stop button. The instruments only
measure the bet if the chassis isn't the bottleneck. Axis 1 is falsifier hygiene, not parity
chasing — this is the argument that carried the D6 amendment.

## 3. Settled in this discourse (operator-ratified)

1. **ADR-457 D6 guard amendment — applied** (see the amendment note in ADR-457 D6): *catch up to
   the bar, differentiate above it; never compete ON the bar.* The cut is **mechanics vs
   features**: turn mechanics, attachments, rendering, hygiene are what a chat **is** — owed as a
   one-time enumerated debt (the Phase-A five). Features chat products *compete on* (voice,
   GPT-store analogs, image generation, canvas, memory-settings UI) stay refused behind the
   floor-leverage test.
2. **The Phase-A five — greenlit unconditionally** ("proceed regardless of our further
   considerations"): response ceiling · turn controls · attachments · rendering quality ·
   conversation hygiene. Spec in §9.
3. **The never-ambient invariant** — held across every variant discussed: **a model turn fires
   only on a human act; models never speak unaddressed.** What varies by design (§4) is only who
   *selects* the responder.
4. **The divergence amendment — direction agreed, application deferred.** ADR-457 D2's "diverge
   privately, settle publicly" was descriptive of the only conversation object we had, not a
   derived necessity. It re-states as: *divergence may be private (lanes) or shared (rooms);
   settling is always public.* The surviving invariant: **the transcript is never the system of
   record.** The D2 edit lands only when rooms lock — not applied now.

## 4. The orchestration re-cut (2026-07-15 — the operator's insight; NOT locked)

The prior synthesis treated invocation as an **addressing** problem (@claude/@gpt per turn). The
operator re-cut it as an **orchestration** problem:

> The tech stack should be rooms (multi-model, multi-human capable), but the initial offering is
> a **single user's cohesive experience** that combines those concepts. Either rooms with models
> *designated for specific work* — resolving "who does what, who responds to what" — or
> designated lanes per work-kind: "gemini for images, sonnet for thinking," "both in the same
> chat," "both cross-checking each other during research." Abstraction and orchestration of LLM
> routing, models, and workflows.

Per-turn @-addressing makes the human do the routing on every message — expert-mode ceremony, and
the "command line" feel D8 falsifier 1 warns about. Designation declared once, routing resolved
from structure, is the product answer. Consequences worked through in-session:

- **The lane's model pin dissolves.** ADR-411 D1 pins one model per lane; every example above
  breaks the pin. Once it dissolves, lane-vs-room collapses to one seam: **scope**. Designated
  lanes alone (the operator's second option) don't solve the felt problem — the fragmentation is
  that engines can't share context, so combining two models on one problem means copy-pasting
  between your own hands.
- **The unified Conversation object** (the proposed ADR centerpiece):
  `{scope: private|shared, cast: {model → designation}, bindings: {artifact|derive|…}}`.
  A today-lane is the degenerate case (private, cast of one). A room is the same object at shared
  scope. This **subsumes** ADR-411 rather than siblinging it — one conversation substrate serving
  lanes, Studio bound lanes, rooms, and (per §7) comments.
- **The staging insight.** "Tech stack = rooms, offering = single-user" is not a compromise: the
  cast-conversation *is* the room grammar rehearsed solo — distinct attributed voices, addressed
  turns, settle. When a second human arrives (2b), they slot into an interaction model the user
  already knows. One grammar; engines first, humans later.
- **The routing ladder** (deterministic before intelligent): (a) per-turn model picker on the
  composer — switch engines mid-thread, full shared context (alone this already delivers "gemini
  and sonnet in the same chat"); (b) remembered designations as *defaults* pre-selecting the
  picker; (c) **gestures** — one-click deterministic orchestrations ("cross-check this,"
  "arbitrate"); (d) auto-routing by turn classification — an LLM deciding which LLM answers.
  Session lean: ship a→c, hold (d) until felt need (a hidden metered routing call + mis-routed
  turns are opaque in exactly the way this product refuses to be). @-address survives as the
  manual override, not the primary UX.
- **Acquisition-wedge upgrade.** "Every engine at one desk, orchestrated, on your own record" is
  a demoable N=1 wedge single-vendor hosts structurally cannot copy — stronger than "rooms" as a
  headline, no team-adoption dependency, and it productizes the multi-engine floor pillar
  (ADR-457 D6 named multi-engine/BYOK a candidate wedge, unproven).

## 5. The guards the re-cut needs (session-derived; travel with it if it locks)

1. **Designations are routing facts, never identities.** Mechanism-dimension data (which engine
   answers which kind of turn) — no standing intent, no mandate, nothing acts unaddressed,
   attribution stays `member:{id} via {model}` verbatim. Anything more backdoors A3 and unwinds
   the Rung-2 deferral. Naming: **not "roles"** (collides with production roles), **not "seats"**
   (collides with judgment seats) — "cast"/"designations" as working names; kernel names the
   category, the member assigns instances (the `LANE_MODELS`/`DERIVE_RECIPES` precedent line).
2. **Route deterministically before routing intelligently** (the ladder above; hold rung d).
3. **Media designations follow the storage phase.** "Gemini for images" is aspirational until
   ADR-427 Ph2/3 (ADR-457 D7 P1). Honest v1 designations are text-work: thinking/drafting,
   critique/cross-check, research (meets research-as-rented-tool).

## 6. The ADR-408 D6 amendment, scoped narrowly

ADR-408 D6 ("cross-model collaboration happens through the filesystem, never through each
other's transcripts") was written for **actor isolation** — autonomous actors building on each
other's unsettled context. Within **one member's addressed thread**, the transcript is the
member's own working context under their witness, every turn attributed inline; two engines
reading it differs in degree, not kind, from one. Across threads and across autonomous actors the
filesystem rule stands untouched. Same amendment shape as §3.4, one layer down. (Cost note: each
model turn re-reads the shared transcript at its own token rates — metered, fine, worth a line in
the ADR.)

## 7. The comments inversion (counter-proposal; NOT locked)

Both prior options ("hold the comments ADR until Phase D" / "separate objects") were rejected in
discourse. Holding until Phase D has a timing conflict: ADR-457 D7 P2 puts comments-as-substrate
inside the **Studio** multi-user wave, likely needed before chat's Phase D — if Studio builds
comments as a separate object first, the convergence assessment is moot. The inversion: **make
the Conversation binding-capable from birth** (the ADR-440/450 pattern that already exists). A
comment thread = a shared-scoped conversation bound to an artifact (+ block anchor). The comments
ADR, whenever the Studio lane needs it, *consumes* the conversation contract instead of inventing
a parallel object.

## 8. The proposed program (labels re-cut; NOT locked)

- **Phase A — the chassis** (greenlit, underway): the five + token/round profile.
- **Phase B — the orchestrated multi-engine conversation**, single-user, private scope (2a
  re-cut: cast + picker + cross-check gesture) **+ settle riding on it**. Open question from
  session: pull settle forward into A/A.5 — it is the smallest differentiator, starts the D8
  falsifier-2 observation clock, and every week it's live shrinks the P4 grounding debt before
  Phase C reads the corpus.
- **Phase C — grounding + citations** (axis 3; the retrieval widening ruling).
- **Phase D — the scope flip** (shared rooms, multi-human, presence-lite, attention routing —
  ADR-405 territory; comments convergence per §7). Note: rooms dodge the Studio 409 problem —
  append-only conversations don't conflict like concurrent edits.
- **W0 — D8 falsifier counters instrumented before Phase B ships.** Also noted: shipping rooms
  changes what chat *is* mid-observation; falsifiers should be evaluated per-phase, not on one
  clock.
- **Two-front guard honesty**: rooms/cast are NOT "shallow framing plus floor-riders" — a new
  object and a schema delta. They ride the floor (multi-engine, attribution, grants) and don't
  compete with Studio's editor depth, but the horizon ADR must re-cut the guard's letter
  ("chat waves don't build editor depth; structural waves must ride the floor") rather than
  contradict it silently.

## 9. Phase-A chassis spec (the five, with receipts)

Baseline receipts (`api/services/lane_runner.py`, 2026-07-15): exactly 5 file verbs (no
QueryKnowledge/recall, no web); `_LANE_MAX_TOKENS = 2048` / `_LANE_MAX_ROUNDS = 8` /
`_LANE_TIMEOUT_S = 120`; streaming exists (`run_lane_turn_stream`); bound/derive lanes already
get the 8192 authoring profile via `_studio_max_tokens()`; `LANE_MODELS` = 7 rows across 4
providers.

1. **Response ceiling** — **open** (attempted 2026-07-15: applied + gate-passed, then reverted
   in the shared working tree before commit; the tree stands at 2048 — re-apply only in a
   coordinated pass). The standing recommendation: 2048 → **4096** (the think profile) — 4096
   preserves the ADR-440 "authoring profile (8192) > chat profile" ordering asserted by
   `test_adr440_studio.py`; revisit upward against felt truncation, not speculation. Rounds stay
   8 (a cost ceiling — tokens were the quality lever, not rounds).
2. **Turn controls** — stop generation, regenerate, edit-and-resend, copy. Stop requires the
   stream abort path; regenerate/edit are tail operations on `session_messages`.
3. **Attachments** — **two items wearing one name**: (a) document attachments ride the built
   ADR-395 intake + DP34 projection — clean; (b) **image input may collide with the D7 P1 media
   gate** — no binary retention path (`storage_backend.py:191` utf-8 wall) and DP32 requires the
   raw be retained; an image the model saw but the ledger never kept violates the intake axiom.
   Probe what ADR-395 does with binary today before ruling; either a narrow retained path exists
   or image input defers with media.
4. **Rendering quality** — markdown/code-block polish, tables, latency-to-first-token feel.
5. **Conversation hygiene** — auto-naming, search across lanes, pin/archive.

Deliberately skipped (the amended guard doing its job): voice, GPT-store analog, canvas (Studio
is our canvas), image generation (ADR-427-gated anyway), memory-settings UI (our memory is the
substrate).

## 10. Pending rulings (open when the discourse resumes)

The operator holds further consideration points; these are queued, not blocking Phase A:

- **(a)** The unified-object re-cut — one Conversation (`scope · cast · bindings`), subsuming
  ADR-411's lane rather than siblinging it.
- **(b)** The routing ladder stop-point — v1 stops at gestures (a→c), or does the "singular
  cohesive experience" want auto-routing (d) in scope now, accepting the opacity trade?
- **(c)** The comments inversion (§7) — binding-capable from birth vs hold-until-Phase-D.
- **(d)** Settle's phase — B (as proposed) or pulled forward to A/A.5 (§8).
- **(e)** The operator's further consideration points, to be stated.

Sequencing 2a→2b was confirmed *as re-labeled* in §8 (single-user orchestrated conversation
before the scope flip). Invocation semantics are settled at the invariant level (§3.3) and open
at the ladder level (b).

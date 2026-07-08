# Naming-Drift Policy — the standing rule for internal names that outlive a renamed concept

**Date**: 2026-07-08
**Status**: **Ratified + folded into canon** (2026-07-08). Surfaced from the ADR-414 F2a
`reviewer_identity` / `reviewer_reasoning` column-rename decision; the governing rule (§2)
is now the header of GLOSSARY §Exceptions, and the one backlog item (§5 row 1, the proposals
boundary-map) is Implemented (`routes/proposals.py::serialize_proposal`, commit on 2026-07-08).
**Owner-layer**: a *canon* rule — GLOSSARY §Exceptions is its instance set.
**Relates to**: ADR-381 D1 (relabel-keep-slug), ADR-251 (the precedent), ADR-410 D4 (the
render-layer vocabulary ban), GLOSSARY §Exceptions + §"Retired terms cannot appear".

---

## 0. The problem, stated once

A concept gets renamed (Reviewer → the agent; thinking_partner → Freddie; Specialist →
production role; deliverable → agent). The *canon* vocabulary moves the same day. But the
name is also embedded in five different technical layers, each with a different cost to
change and a different blast radius. Today we decide layer-by-layer, per rename, from
precedent and gut ("keep the slug", "rename the FE shape") — and each decision leaves a
row in the GLOSSARY Exceptions table with a bespoke justification.

That worked at 3 exceptions. At 8+ (the current count, inventoried in §5) it is becoming
an **exception table every new developer must memorize** to know that a column reading
`reviewer_` means "the agent", a `role='thinking_partner'` row means "the system agent",
and an `authored_by='specialist:writer'` prefix means "a production role". The drift
between internal slugs and canon vocabulary is monotonically widening. This doc sets the
**standing rule** so the decision is mechanical, not re-litigated per rename, and the
Exceptions table stops being a pile of one-offs.

---

## 1. The taxonomy — the five layers a name lives in

Ordered from cheapest-to-rename / smallest-blast-radius to most expensive. The layer a
name sits in is the *only* input the rule needs.

| # | Layer | Examples | Who reads it | Rename cost | Blast radius |
|---|-------|----------|--------------|-------------|--------------|
| **(a)** | **DB column / table names** | `action_proposals.reviewer_identity`, `agents.role`, table `action_proposals` | Every writer + reader + every join + probes + FE (if serialized 1:1) | **High** — migration + backfill + every SQL string + cache refresh + coordinated deploy across 4 Render services | Wide + irreversible-ish (old data carries old shape) |
| **(b)** | **Internal enum / slug VALUES** | `authored_by='reviewer:…'` / `'specialist:writer'`, `role='thinking_partner'`, `session_type='thinking_partner'`, `agent_class='meta-cognitive'` | Dispatch code that switches on the value; revision-chain data format (ADR-209, immutable) | **Very high** — the *value* is baked into historical immutable rows (`workspace_file_versions.authored_by`); renaming means a data-format break or a dual-read shim forever | Wide + **immutable data** (ADR-209 makes these permanent) |
| **(c)** | **Python / TS identifiers** | `TPContext`, `useTP`, `FreddieContext`, `_JUDGMENT_HOME_FILES`, component `tp/ProposalCard.tsx` | The codebase only | **Medium** — mechanical rename across N import sites; no data, no migration | Code-only, reversible, caught by the compiler/typechecker |
| **(d)** | **API response field names** | the JSON `{reviewer_identity, reviewer_reasoning}` the FE client types at `web/lib/api/client.ts` | The FE contract — a cross-process boundary | **Medium-high** — must change server serializer AND every FE consumer in lockstep (or version the endpoint); breaks any external consumer | Cross-process, but *internal* (our own FE) — no third party today |
| **(e)** | **Operator-facing rendered strings** | badge text, pane titles, the word a human reads on screen | The human operator | **Low** — a label-map edit, no data, no contract | Render-only, reversible |

**The already-settled layer.** ADR-410 D4 governs layer (e) and only (e): *retired
vocabulary is banned from operator-facing strings; the FE label layer owns the mapping.*
That is not in question. This doc governs (a)–(d), which ADR-410 D4 is silent on.

---

## 2. The rule — default action per layer when a concept is renamed

> **The rename propagates DOWN from canon only as far as the render layer by default.
> Below the render boundary, internal names are STABLE by default — renamed only when a
> specific, named trigger fires.**

Concretely, per layer, on any concept rename:

| Layer | Default action | Rename only when… |
|-------|----------------|-------------------|
| **(e)** render strings | **RENAME immediately** (ADR-410 D4 — mandatory) | always |
| **(d)** API fields | **BOUNDARY-MAP** (serialize the new canon name over the unchanged internal source) — see §3 | never rename the internal source *because of* the field; the field is renamed via the map |
| **(c)** identifiers | **KEEP** (relabel-keep-slug) | the rename is small (< ~15 sites), compiler-checked, AND you're already editing the file for another reason — opportunistic, never a standalone churn commit |
| **(b)** enum/slug values | **KEEP — forever** | effectively never (immutable ADR-209 data; a rename is a data-format break) |
| **(a)** DB columns | **KEEP** (relabel-keep-slug) | the migration threshold in §2.1 is met |

This is the current *de-facto* rule made explicit and given one addition: **layer (d) gets
a boundary-map, not a keep-and-hope.** That addition is what makes the policy scale (§4).

### 2.1 The migration threshold for layer (a)

A DB column rename is worth its cost **only when ALL of these hold**:

1. **The column is a live API contract the FE reads by name** (layer (a) is *also* layer
   (d)) — i.e. the internal drift is leaking across a process boundary, not just sitting
   in the database, AND
2. **the boundary-map (§3) is not viable** — e.g. the field is read by an *external*
   consumer we don't control, or the map would have to live in too many serializers to be
   singular, AND
3. **the concept rename is durable** — it has ratified in canon and is not itself likely
   to churn again soon (renaming a column to `agent_identity` the quarter before "agent"
   itself gets re-cut is negative work).

If any one fails → **keep the column, boundary-map the field.** The `reviewer_identity` /
`reviewer_reasoning` case (§5) fails #2 (the map IS viable — one FE-facing derivation
already maps them) so it correctly stays keep-slug, which is exactly the F2a ruling.

---

## 3. The boundary-map — the mechanism that makes keep-slug scale

The scalability worry the operator named is real: relabel-keep-slug, applied naively,
grows the Exceptions table without bound and forces every new dev to learn "this says
reviewer but means agent." The escape is to **stop letting the internal name reach the
reader at all** — rename it once, at the serialization boundary, and let internal stay
stable forever.

**The pattern:**

- Internal (layers a/b/c) keep their stable names — `action_proposals.reviewer_identity`,
  `authored_by='specialist:…'`, `FreddieContext`. No migration, no data-format break.
- **One adapter** at the API serialization boundary maps internal → canon on the way out
  (and canon → internal on the way in, if the field is writable). The FE contract (layer
  d) speaks *canon*; the DB (layer a) speaks *stable-internal*; the adapter is the only
  place the two vocabularies meet.
- The Exceptions table then records **one fact per drifted name** — "internal `reviewer_*`
  → canon `agent_*` at the `proposals` serializer" — and a new dev reads the adapter, not
  a scattered mental map. The adapter *is* the documentation.

**Why this beats the two alternatives** the operator asked to weigh:

- **(i) pure relabel-keep-slug** (today): cheap per-rename, but the reader-facing gap never
  closes — every FE dev sees `reviewer_identity` in the JSON and has to know it means the
  agent. Scales badly on *comprehension*.
- **(ii) migrate the column per rename**: closes the gap but pays the full migration tax
  (schema + every writer/reader + the ground-truth join + probes + FE) *per rename*, on
  immutable-ish data. Scales badly on *cost*, and layer (b) can't even do it (immutable).
- **(iii) boundary-map** (recommended): pays a one-time adapter cost per drifted field,
  closes the reader-facing gap (the FE only ever sees canon), leaves internal + immutable
  data untouched. The gap that remains — internal code sees `reviewer_identity` — is read
  only by *backend* devs, who are the ones who should know the seat's history anyway, and
  it's localized to the write path + the adapter, not smeared across the FE.

**The standing policy is (iii): boundary-map at layer (d); keep-slug below it.** Migration
(ii) is the reserved exception, gated by §2.1.

### 3.1 Where the adapter lives (singular-implementation)

One adapter module per bounded contract, not per field. For proposals: a single
`serialize_proposal(row) -> dict` that renames `reviewer_identity → agent_identity`,
`reviewer_reasoning → agent_reasoning` once, used by every route that emits a proposal.
The FE client types the canon shape. The DB column, the primitive that writes it, the
ground-truth join, and the probes all keep `reviewer_*` — none of them cross the boundary.

---

## 4. Why this is the durable answer (the scalability argument)

As more concepts rename, the internal-vs-canon gap widens *only where a reader can see it*.
The boundary-map confines the gap to the backend, where the audience is small and the
history is relevant. The Exceptions table's growth becomes **bounded by the number of
serialization adapters, not the number of drifted names** — because one adapter can carry
many field renames, and the table records "see the adapter" instead of N justification
rows. The rule is also **mechanical**: given a drifted name, you read off its layer and
apply §2's table — no per-case judgment, no precedent-hunting. That is the property the
operator asked for ("durable, scalable rule," "a decision to ratify, then apply").

---

## 5. The concrete backlog — every known drift, classified under the policy

Inventory of the current internal↔canon drifts, each with its verdict. This turns the
policy into an actionable list.

| Drift | Layer(s) | Current state | **Verdict** | Action |
|-------|----------|---------------|-------------|--------|
| `action_proposals.reviewer_identity` / `reviewer_reasoning` | (a) + (d) — column IS the FE field | **RESOLVED 2026-07-08**: keep-slug (a) + boundary-map (d) Implemented | **KEEP-SLUG (a) + BOUNDARY-MAP (d)** — §2.1 fails #2 (map is viable). | **DONE**: `routes/proposals.py::serialize_proposal` emits `agent_identity`/`agent_reasoning` from the unchanged columns (list + get endpoints); `web/lib/api/client.ts` + `ProposalCard.tsx` + `QueueBody.tsx` read the canon aliases. The column stays. `decisions.ts` (parses the `decisions.md`/`judgment_log.md` SUBSTRATE format, written by `freddie_audit`) is a separate file-format layer, keep-slug per File Format Discipline §9. |
| `session_type='thinking_partner'` | (b) enum value | keep-slug (ADR-414 D3) | **KEEP — forever** | none; it's the retired-row continuity key, immutable-class |
| `authored_by='reviewer:…'` legacy prefix | (b) immutable data | historical rows carry it; live writes use `freddie:` | **KEEP — forever** | none; ADR-209 immutable. Readers already `.or_` over `freddie:`+`reviewer:` (the B1 undercount fix) — that dual-read is the correct permanent shim for immutable data |
| `authored_by='specialist:<role>'` / `agent_class='meta-cognitive'` | (b) + (c) + (d) | keep-slug (GLOSSARY Exceptions) | **KEEP — forever** (b/immutable); **BOUNDARY-MAP** if/when a surface renders them raw | none now; if a future surface exposes `agent_class`, map it at that serializer |
| `role='thinking_partner'` / slug `thinking-partner` | (a) + (b) | keep-slug (GLOSSARY Exceptions); the ROW itself retired by ADR-414 D3 migration 205 | **KEEP** — the value is locked into the `agents.role` CHECK constraint; §2.1 #1 fails (never serialized to FE) | none |
| `TPContext`/`useTP`/`TPProvider`/`tp/` component dir | (c) identifiers | keep-slug (GLOSSARY Exceptions — "15+ import sites") | **KEEP by default; rename opportunistically** — a compiler-checked (c) rename is cheap when you're already in the file, but never a standalone churn commit | fold into whatever next touches `web/components/tp/*` |
| `_JUDGMENT_HOME_FILES` / `_UNIVERSAL_ENVELOPE_DECLS` | (c) identifiers | current | **KEEP** — accurate names for what they are; not a drift, listed only to confirm they're out of scope | none |

**Net actionable output**: exactly one gap the policy flags as worth closing —
the `reviewer_identity`/`reviewer_reasoning` **API field** (layer d), via boundary-map,
as a small standalone follow-on. Everything else is correctly at KEEP under the standing
rule. The column (layer a) stays; only the field the FE sees (layer d) gets canon.

---

## 6. Recommendation (the one-line decision to ratify)

> **Ratify: rename to the render layer by default; boundary-map at the API contract;
> keep-slug below it; migrate a DB column only when it is also a live API field AND the
> boundary-map is not viable AND the rename is durable (§2.1). Fold this rule into GLOSSARY
> §Exceptions as the policy its table instances.**

If ratified, the single concrete follow-on is the proposals boundary-map (§5 row 1) — its
own small commit, not owed by ADR-414. All other drifts are already policy-conformant.

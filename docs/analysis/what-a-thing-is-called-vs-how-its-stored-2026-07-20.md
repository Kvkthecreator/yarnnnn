# What a thing is called vs. how it's stored — the naming layer under a non-Latin name

> **Status**: **Closed** — resolved by [ADR-469](../adr/ADR-469-the-name-is-lifted-the-path-is-a-key.md)
> (Implemented 2026-07-20), which took **Option C** (lift the name from the
> artifact) *with* **Option A**'s accent folding, and answered §6 Q1: ADR-459 D2
> is **amended** — the folder becomes the fallback, not the name's source.
> This document is retained as the derivation.
>
> Originally: discourse / audit opening the question ADR-459 D2 explicitly
> deferred ("if fidelity ever outweighs the storage cost, that is its own ADR —
> not a smarter regex").
> **Date**: 2026-07-20
> **Touches**: ADR-459 D2 (name is the namespace) · DP33 (meaning in the
> namespace, category in data) · ADR-209/286 (attributed substrate,
> single-writer-per-path) · ADR-448 (the lift pattern)

---

## 1. The observation

The Studio's creation modal turns a typed name into a path:

```
"IR deck v3"  →  operation/ir-deck-v3/deck.html
```

`slugify` keeps `[a-z0-9]` and collapses everything else to `-`. ADR-459 D2 then
reads the name back out of the folder by titleizing it. No stored name, no
column — the namespace carries the meaning, which is exactly DP33.

For Latin names this is a good trade, and D2's reasoning about it is sound. The
lossy step is *casing*, the reconstruction is wrong in **one predictable way**
(`IR` reads `Ir`), and the ADR argues persuasively that a predictable small
wrongness beats a cleverer unpredictable one.

**That reasoning silently assumes the input is Latin.** It isn't always.

## 2. What actually happens (measured, not reasoned)

Round-tripping `slugify` → `_titleize` across scripts:

| typed | slug | reads back as |
|---|---|---|
| `IR deck v3` | `ir-deck-v3` | `Ir deck v3` |
| `Acme Q3` | `acme-q3` | `Acme q3` |
| `Q3 전략 보고서` | `q3` | `Q3` |
| `투자 유치 v2` | `v2` | `V2` |
| `한글 문서` | `untitled` | `Untitled` |
| `日本語` | `untitled` | `Untitled` |
| `Émile résumé` | `mile-r-sum` | `Mile r sum` |
| `naïve café` | `na-ve-caf` | `Na ve caf` |

Three distinct failure grades, only the first of which D2 anticipated:

1. **Casing loss** (`IR` → `Ir`) — the ceiling D2 recorded and accepted.
2. **Partial erasure** — `Q3 전략 보고서` keeps only its Latin residue. The
   document is named after the least meaningful part of what was typed. Accented
   Latin degrades the same way: `café` → `caf`.
3. **Total erasure → collision.** A name with no Latin characters slugs to the
   literal fallback `untitled`.

Grade 3 is not a display bug. It is a **namespace collision**:

```
"한글 문서" → operation/untitled/deck.html
"日本語"   → operation/untitled/deck.html
"전략"     → operation/untitled/deck.html
"회의록"   → operation/untitled/deck.html
```

Four distinct documents, one path. Creation is guarded — `routes/studio.py:683`
409s with *"{path} already exists — open it in the Studio instead."* — so there
is **no silent data loss**, which matters and should be said plainly.

But the operator-facing behaviour is: *the second Korean-named document you ever
create is refused, and the error names a path you never typed and cannot see.*
A member working in Korean hits this on their second document. Forever.

### 2a. The two doors disagree

Create and rename slugify independently, and diverge on exactly the failing case:

| typed | create (`NewArtifactModal.slugify`) | rename (`routes/studio.py:432`) |
|---|---|---|
| `IR deck` | `ir-deck` | `ir-deck` |
| `Q3 전략` | `q3` | `q3` |
| `한글 문서` | `untitled` (silent) | **422 "A name is required."** |

`studio.py:428-431` states the intent — *"the two entrances into a name … can
never disagree about what a name becomes"* — and for Latin input they don't. On
a name with no Latin characters they produce opposite outcomes: creation
silently accepts a wrong name, rename refuses a valid one with a message that
misdescribes the problem (a name *was* given).

This matters for scoping: the fix has **two call sites minimum**, and the intent
of singular implementation is already recorded, so unifying them is a repair of
stated canon rather than a new decision.

### 2b. The rule is reimplemented nine times

`[^a-z0-9]+ → -` appears independently in at least:

- `web/components/studio/NewArtifactModal.tsx:35` (artifact create)
- `web/lib/agent-identity.ts:310`
- `api/routes/studio.py:432` (artifact rename), `:309` (design systems)
- `api/services/settle.py:112`, `api/services/mcp_composition.py:299`
- `api/routes/lanes.py:837` (agent slugs), `api/routes/integrations.py:2762`

Not all are operator-facing names — `mcp_composition` and `lanes` derive
internal identifiers, where ASCII-only is defensible and arguably correct. The
audit any fix needs is **which of these name a thing a member reads**, and only
those move. A blanket change would be wrong.

## 3. Why this is a canon question, not a regex question

The tempting fix — "make `slugify` unicode-aware" — is the exact move ADR-459 D2
forecloses ("not a smarter regex"), and it's foreclosed for a good reason. But
the reason is subtler than it first appears, and worth stating precisely:

**The namespace is doing double duty.** It is simultaneously:

- **a meaning carrier** — DP33's claim, the basis for storing no name; and
- **an identity key** — `(workspace_id, path)` is the substrate's binding unit
  (ADR-373), the single-writer unit (ADR-286), and the revision-chain key
  (ADR-209).

For Latin input those two roles coexist happily. Under lossy transliteration
they **come apart**: the meaning carrier becomes non-injective (many names → one
slug) while the identity key still demands uniqueness. The 409 is the substrate
correctly refusing to let a lossy display concern corrupt an identity concern.

So the question is not "how do we slug better." It is:

> **Should the operator-facing name be derived from the identity key at all?**

ADR-459 D2 answered *yes* — and it was right for the case it examined. This is
the falsifying case it named in advance.

## 4. The options, honestly weighed

### Option A — Unicode-permissive slug

Allow non-ASCII word characters in the path segment: `operation/한글-문서/deck.html`.

- **For**: injective again; collisions gone; name reads back perfectly; no
  storage; D2's "namespace carries meaning" thesis is *strengthened*, not
  weakened — it starts working for members it currently fails.
- **Against**: paths become non-ASCII. Needs an audit of every path consumer
  (URL encoding in `?studio.file=`, the MCP face, `derived_from` edges, export
  filenames, any shell-adjacent tooling). Casing loss (grade 1) remains.
- **Note**: this is not exotic — macOS and Linux filesystems have handled
  unicode paths for two decades, and the substrate is Postgres `text`, not a
  filesystem with encoding constraints.

### Option B — Store the typed name

Add a name field; the path stays an opaque ASCII key.

- **For**: perfect fidelity including casing; solves all three grades at once.
- **Against**: this is precisely the "second source" D2 refuses, and ADR-456 D1
  refuses for the DOM. It re-opens *which name is real* — the stored one or the
  folder — and creates a rename-skew class of bug. **The strongest objection is
  architectural, not effort:** it would make the name storage-authoritative
  while ADR-448/459's whole direction is lift-from-what-exists.

### Option C — Lift the name from the artifact (the ADR-448/459 pattern)

The artifact already carries its title in the DOM. Creation writes the typed
name into it (`routes/studio.py:684-690` — "the name is ONE fact"). So: serve
the name by **lifting it from content**, exactly as D1 lifts the *kind* from
`data-template`, and let the path stay a dumb ASCII key.

- **For**: no new storage; no second source (content is already authoritative);
  identical in shape to D1, which is ratified and shipped; fixes casing *and*
  script loss together; the path is freed to be purely an identity key.
- **Against**: the path can still collide (`untitled`) even if the *display* is
  correct — so this needs a disambiguating suffix on collision, which is a real
  but small mechanism. Costs a content read per row, though D1 already pays
  exactly this cost on the same endpoint.
- **Tension**: D2 says the name needs no storage because the folder holds it.
  Under C the folder *doesn't* hold it — the DOM does. That is a genuine
  amendment to D2, not a compatible reading.

### Option D — Do nothing

- **For**: no risk; the 409 prevents corruption; N=1 operator may not hit it.
- **Against**: the operator is Korean-speaking. This is not hypothetical for
  *this* workspace.

## 5. Where the weight seems to fall

**C, with a collision suffix on the path** looks strongest, because it is the
pattern canon already ratified one decision earlier: D1 lifts the kind from
content rather than spelling it in the filename, and gives the exact reason —
*"the kind was never in the name."* The same sentence is true of the name.

That reframes the whole thing cleanly:

> The **path** is an identity key (ASCII, collision-free, machine-facing).
> The **name** is a fact the artifact carries (unicode, exact, member-facing).
> Neither impersonates the other.

**A is the cheaper honest fix** and could stand alone if the path audit comes
back clean — it fixes grades 2 and 3 without touching canon at all, since it
only widens what `slugify` preserves. A and C are not exclusive; A makes the
key readable, C makes the name exact.

**B should be resisted** unless A and C both fail.

## 6. What must be resolved before any code

1. **Is D2 amended or preserved?** C amends it (the folder stops being the name
   source). A preserves it. This is the operator's call, not an implementation
   detail.
2. **Path-consumer audit** (required for A, cheap insurance for C). **Partially
   done here, and the early read is favourable:**
   - FE path params are consistently `encodeURIComponent`'d
     (`lib/api/client.ts` — file reads, revisions, diffs, dependents). No raw
     interpolation found on those routes.
   - No path *validator* or sanitizer rejects non-ASCII — there is no
     `normalize_path` / `_sanitize_path` gate to update.
   - The only ASCII regex touching a stored path is
     `studio.py:1472`, and it matches the **extension** (`\.[a-z0-9]+$`), not
     the name — unaffected by a unicode name segment.
   - Substrate storage is Postgres `text`; there is no filesystem encoding
     constraint (ADR-427 Phase 1's StorageBackend seam is the place to re-check
     if binary/disk lands later).
   - **Still unaudited**: the MCP face, export/download filename construction,
     and any `Content-Disposition` header. These are the realistic remaining
     risk and should be checked before A ships.
3. **Collision policy** — if two artifacts would take one slug, does the second
   get `-2`, get refused (today), or is the question dissolved by A?
4. **Retroactivity** — does an existing `operation/untitled/…` get repaired, or
   is this forward-only? (ADR-209 makes a move a revision, so repair is
   attributable and reversible — it is not a destructive migration.)

## 7. Explicitly not claimed here

- Not claimed that D2 was wrong. It was right about the case it examined and
  recorded its own ceiling; this is that ceiling being reached.
- Not claimed this is urgent for correctness. The 409 holds; nothing corrupts.
- Not claimed which option ships. This document opens the discourse; the ADR
  closes it.

## 8. The one-line statement

**A slug is a fine name until it stops being injective — and the moment the
operator's own language makes it non-injective, the namespace can no longer be
both the meaning and the key.**

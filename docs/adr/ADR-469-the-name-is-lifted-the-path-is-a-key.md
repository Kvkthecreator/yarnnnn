# ADR-469 — The name is lifted, the path is a key

> **Status**: Implemented (2026-07-20)
> **Amends**: ADR-459 D2 (the name is the namespace, titleized)
> **Extends**: ADR-459 D1 (the kind is LIFTED from content) — same pattern, second fact
> **Preserves**: DP33 · ADR-456 D1 (content is the sole source) · ADR-209/286/373 · the whole of ADR-459 except D2's *primary* source
> **Derivation**: [`docs/analysis/what-a-thing-is-called-vs-how-its-stored-2026-07-20.md`](../analysis/what-a-thing-is-called-vs-how-its-stored-2026-07-20.md)

---

## 1. The observation

ADR-459 D2 derived the operator-facing name from the meaning folder: the member
typed `IR deck v3`, it became `operation/ir-deck-v3/deck.html`, and the card
read the folder back as `Ir deck v3`. No stored name, no column — DP33 exactly.

D2 recorded its own ceiling honestly: the slug is lossy, casing is
unrecoverable, and *"if acronym fidelity ever outweighs the storage cost, that
is its own ADR — not a smarter regex."* This is that ADR, reached from a
direction D2 did not anticipate.

**D2's reasoning assumed Latin input.** Measured across scripts, the loss has
three grades, not one:

| typed | reads back as | grade |
|---|---|---|
| `IR deck v3` | `Ir deck v3` | casing — the loss D2 accepted |
| `Q3 전략 보고서` | `Q3` | **partial erasure** (`café` → `caf` too) |
| `한글 문서` | `Untitled` | **total erasure** |

Grade 3 is not a display defect. `slugify` stops being injective, so four
distinct Korean names produce one path:

```
"한글 문서" · "日本語" · "전략" · "회의록"   →  operation/untitled/deck.html
```

Creation was guarded (`routes/studio.py` 409'd), so nothing corrupted. But the
member's **second** non-Latin-named document could not be named at all, and the
error named a path they never typed. A workspace operated in Korean hit this
immediately and permanently.

## 2. Why a wider regex was the wrong fix

The namespace was doing double duty:

- a **meaning carrier** — DP33's claim, the basis for storing no name; and
- an **identity key** — `(workspace_id, path)` is the substrate's binding unit
  (ADR-373), the single-writer unit (ADR-286), the revision-chain key (ADR-209).

For Latin input the two roles coexist. Under lossy transliteration they come
apart: the meaning carrier becomes non-injective while the identity key still
demands uniqueness. The 409 was the substrate correctly refusing to let a
display concern corrupt an identity concern.

So the question was never "how do we slug better." It was **whether the
operator-facing name should be derived from the identity key at all.**

## 3. Decisions

### D1 — The name is LIFTED from the artifact's `<title>`

`services/studio.py::extract_title` reads the name from the artifact's own
`<title>`. This is ADR-459 D1's pattern applied to the second fact, for D1's own
stated reason — *"the kind was never in the name"* — which is equally true of
the name.

`<title>` is the right carrier and the codebase already said so:
`set_artifact_title`'s contract is *"the `<title>` element is always set — it is
metadata, never authored."* Unlike the `<h1>` (a thesis on a paged layout,
member-authored words once touched), nothing else may write it. It is already
written at creation and at every rename.

**No storage.** No column, no migration, no second source — content was already
authoritative (ADR-456 D1), and the landing endpoint already reads `content` to
lift the kind, so the name costs one regex on a string it already holds.

### D2 — The path is an identity key, and only that

`services/naming.py` is the one implementation:

- `path_slug(name)` — ASCII, lowercase, NFKD-folded so accents become their base
  letter (`café` → `cafe`, previously `caf`). A fully non-Latin name yields the
  honest fallback `untitled`.
- `disambiguate(slug, taken)` — `untitled`, `untitled-2`, `untitled-3`. This is
  what makes the fallback safe.

The slug stays **deliberately dumb**. A romanizing slug (`한글` → `hangeul`)
would be guessing, and guessing wrong is worse here than being opaque — nobody
reads the key. `untitled` is an honest key; only its *collisions* needed fixing.

### D3 — ADR-459 D2 becomes the FALLBACK, not the primary

The titleized-meaning-folder rule is preserved verbatim and still serves
everything whose content isn't to hand — the tree-node picker
(`artifactNaming.ts`, which cannot fetch every artifact's body to name a row),
and any artifact predating the lift. Degradation is stepwise and honest: no
content → the folder; no meaning folder → the titleized stem; nothing → `File`.

**This is a genuine amendment, not a compatible reading.** D2 said the name
needs no storage *because the folder holds it*. Under D1 the folder does not
hold it — the DOM does. What survives is the deeper claim both share: **the name
is never stored as a second source.**

### D4 — A key collision is disambiguated, never refused

Rename previously 409'd `'{name}' already exists — pick another name.` That was
right while the key carried the name. It is wrong now: two artifacts sharing a
key is of no consequence to the member, because each still reads back as what
they typed. Refusal left a Korean workspace unable to name a second document.

The **meaning-folder merge guard is preserved** — disambiguation is precisely
what stops two artifacts landing in one namespace, more strongly than refusal
did.

## 4. The bug this surfaced

`_retitle_to_match_filename` returned early on a paged layout — before writing
anything. Under ADR-459 that was invisible (the name came from the folder
regardless). Under D1 it would have been silent data loss: **a renamed deck
would keep its old `<title>`, and the landing card would revert to the folder
slug.**

Split in two: the `<h1>` guard is preserved exactly (a deck's h1 is its title
slide's thesis; a page's is its headline — a filename does not dictate authored
content), while `<title>` is now written for **every** layout. Guarding the h1
was right; guarding the title was the bug.

The helper is renamed `_retitle_to` — the old name described the old direction
of travel. Causality now runs from the typed name into **both** the title
(verbatim) and the folder key (slugified); the filename dictates nothing.

## 5. What is deliberately not built

- **No `title` column, no migration.** The storage half is refused, again.
- **No romanizing transliteration.** The key is not read; guessing is worse.
- **`summary` is still not promoted to a name.** It stays a description.
- **The Files surface is untouched.** It is the mirror; it shows the raw leaf.
- **Internal identifier derivation is NOT routed through `naming.py`.**
  `mcp_composition._slugify` (entity matching) and `routes/lanes.py` (agent
  slugs) name things no member reads, where ASCII-only is correct. The audit was
  *which slugs name something a member reads* — a blanket change would be wrong.

## 6. Falsifiers

1. Creating `한글 문서` and then `日本語` both succeed, land on distinct paths,
   and each reads back as typed. (Before: the second was refused.)
2. `IR deck v3` reads `IR deck v3` on the landing card, not `Ir deck v3`.
3. Renaming a **deck** updates its landing card name. (Before D4's fix: it
   would have silently reverted to the folder slug.)
4. A deck's title-slide h1 is unchanged by a rename.
5. `grep` finds no `ADD COLUMN.*title` — the ADR ships no storage.
6. An artifact with no `<title>` still names itself from its folder.

## 7. The one-line statement

**The path is an identity key; the name is a fact the artifact carries. A slug
is a fine name until the operator's own language makes it non-injective — and
then the namespace can no longer be both the meaning and the key.**

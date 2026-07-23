# ADR-483 — The name is what the member typed: the lift's last caller, and the IME's Enter

- **Status**: **Accepted** (2026-07-23, operator-ratified — *"aligned, let's harden this
  decision both in doc and code in singular streamlined manner"*)
- **Date**: 2026-07-23
- **Dimension**: Channel (primary — what the member reads on the surface). No new substrate,
  no new write path, no schema, no migration, no new primitive.
- **Amends**:
  - **ADR-469** — the lift is *completed*, not revised. ADR-469 made the artifact's `<title>`
    the name and taught `services/studio.py::artifact_name` to read it first. The Studio
    workbench was never migrated, so the crumb kept deriving from the path. §2 is that
    caller finally arriving. The rule is ADR-469's; only its coverage changes.
  - **ADR-459 D2** — the titleized meaning folder is confirmed as the *fallback* half, and is
    now named as such in code (`artifactNameFromPath`), so no future caller mistakes it for
    the resolver.
- **Preserves**: ADR-469's path/name split **in full** (§4 — the path stays an ASCII identity
  key; this ADR explicitly declines to change it) · ADR-209 (one attributed write door — no
  new writer) · ADR-373/286 (`(workspace_id, path)` binding + single-writer) · ADR-448
  (`derived_from` edges are path-keyed and untouched) · ADR-470 (the two doors) · every
  Latin-named artifact, byte-identical.

---

## 1. Why this ADR exists

An operator created a document and reported: *"it asks to rename the document name for
create new document, then nothing renders for me to actually input."*

The report was reproducible in the browser and not in the code. Three separate static
readings each produced a confident wrong cause (state reset on navigation, no re-render
from `replaceState`, the `canvasActive` gate) — every one of them disproved. The surface
looked broken in a way the source did not explain.

It was not broken in the way it appeared. The substrate ledger settles it:

```
workspace_file_versions — /workspace/operation/sd/document.html
  MoveFile: from /workspace/operation/untitled-document-2/document.html
            → /workspace/operation/sd/document.html      01:19:46.374
  Studio: name → 'sdㄴ'                                   01:19:46.717
```

The input **rendered**. The member **typed into it**. `commitRename` **fired** and the
rename **committed**, 343ms after creation. The immediate door (ADR-470) worked end to end.

Two defects then conspired to make a working rename look like a dead one:

**D1 — the crumb read a name the member never typed.** `sdㄴ` is what committed; `Sd` is
what the crumb displayed.

**D2 — `sdㄴ` is not what the member typed either.** It is a half-formed Hangul syllable: a
bare jamo (`ㄴ`) still mid-composition when Enter was taken.

Compounded: type a Korean name, press Enter, and the surface shows a Latin fragment of it.
Reported honestly as *the rename did nothing*.

---

## 2. D1 — the lift's last unmigrated caller

ADR-469 split the two facts and stated the rule plainly (`services/naming.py`):

> The **PATH** is an identity key — ASCII, lowercase, collision-free, machine facing. It
> must be injective; *it does not have to be readable.*
> The **NAME** is a fact the artifact carries — its own `<title>`, unicode and exact. It
> must be readable; *it does not have to be unique.*

`artifact_name(path, content)` implements that: lift the `<title>`, fall back to the
titleized meaning folder. The landing, the recents and the Open picker all read it.

The Studio workbench did not. `StudioSurface.tsx` carried a local `artifactName(p)` that
was a path-only copy of the **fallback branch**, under a comment claiming it *"mirrors
`artifact_name`"* — true before ADR-469, stale after it. So the one surface a member reads
*while working* was the one surface still deriving the name from the lossy key:

| typed | path key | crumb said | title held |
|---|---|---|---|
| `sdㄴ` | `operation/sd/` | **Sd** | `sdㄴ` |
| `한글 문서` | `operation/untitled/` | **Untitled** | `한글 문서` |
| `IR deck v3` | `operation/ir-deck-v3/` | **Ir deck v3** | `IR deck v3` |

**Decision D1**: the workbench derives the name through the same two-source rule as the
server — `<title>` first, meaning folder behind it — computed **once** as
`artifactDisplayName` and read by every surface that shows a name (the OS window crumb, the
toolbar crumb, the rename field's starting value, the export filename, the Move/Trash
confirmations). The path-only derivation survives only as the explicitly-named fallback
*inside* the resolver. One derivation; no caller re-derives.

### 2a. The placeholder guard is served, never re-derived

`artifact_name` falls through to the folder when the `<title>` is still a scaffold — a
pre-ADR-469 artifact never got the typed name written in, so content-wins would relabel a
real document "Untitled document". The FE needs the same predicate.

It cannot compute it. The scaffold set is **not** `Untitled ‹label›`:

```
{'The headline promise.', 'The one-line thesis goes here.',
 'Untitled article', 'Untitled document'}
```

A deck/page scaffold h1 is a *thesis*. Re-deriving from the served labels would fork the
rule and drift from `_is_placeholder_title`.

**Decision D2**: the kernel **serves** the scaffold titles (`GET /studio/vocabulary` →
`placeholder_titles`, derived from `_SCAFFOLD_TITLES`, itself derived from the layout
registry). The FE reads them. The kernel names the category once; nothing downstream
invents one — the ADR-447/461 pattern this endpoint already exists to serve.

---

## 3. D3 — the IME owns Enter first

`sdㄴ` reached the server because the rename field acted on Enter **during an IME
composition**.

Typing Korean/Japanese/Chinese, the first Enter commits the **syllable**, not the field.
`KeyboardEvent.isComposing` is `true` and the buffer holds an unassembled fragment. The
handler had no guard, so it took that Enter as a submit and renamed the artifact to the
fragment. `path_slug` then dropped the non-Latin character on the way into the key, and
`sd` is the folder that resulted.

**Decision D3**: both inputs that name an artifact return early while
`e.nativeEvent.isComposing` — the crumb's rename field and the named door's
`NewArtifactModal`. The member gets their Enter once the syllable is assembled, which is
what every native text field already gives them. `blur` needs no guard (composition has
ended by then). Latin typing is unaffected.

This is one bug in two places, fixed once in both — not a Studio-specific rule.

---

## 4. What this ADR deliberately does NOT do

**It does not allow non-Latin path slugs.** This was considered directly, benchmarked
against Windows/macOS (both of which store `한글.txt` happily), and **declined**.

A Windows filename has exactly one consumer: a human in a file browser. A yarnnn path has
four:

- `(workspace_id, path)` — the substrate's binding unit (ADR-373), the single-writer unit
  (ADR-286), the revision-chain key (ADR-209)
- a URL parameter (`?studio.file=operation%2Fsd%2Fdocument.html`)
- an agent-facing address — MCP `recall`/`trace`, ADR-448 `derived_from` reference edges
- a `data-ref` citation pin

Unicode there buys readability **nobody reads** and costs encoding fragility across all
four. `%ED%95%9C%EA%B8%80` is not more readable than `untitled-2`.

The sharper benchmark is macOS, whose model yarnnn already matches: a display name the
member reads, an immutable inode underneath. Here the `<title>` is the display name and the
path is the inode. Both problems people reach for Unicode slugs to solve are already
solved — **readability** by ADR-469's lift, **collision** by `disambiguate` (`untitled-2`,
`-3`). What remained was one caller reading the wrong half.

`path_slug` is unchanged. `한글 문서` still keys to `untitled`; `sdㄴ` still keys to `sd`.
That is correct, and the gate asserts it stays that way.

---

## 5. Consequences

- A member naming an artifact in any script sees **what they typed**, everywhere the name
  appears, at every moment.
- The two names for one thing are gone at the last surface that still had them.
- Enter means Enter, after the syllable is finished.
- No substrate change. No migration. Every Latin-named artifact renders byte-identically.
- One derivation of the name in the workbench, with the lossy half named as the fallback it
  is — so the next caller cannot reach for it by accident.

---

## 6. Validation

`web/scripts/gates/adr483_name_lift_and_ime.mjs` (**14/14**) — the load-bearing gate. It
**executes** the real `artifactNameOf` / `extractTitle` and the real crumb `onKeyDown` body
extracted from source, and carries a **falsifier for each defect**: restore the pre-fix
path-only derivation and assert `sdㄴ` mangles to `Sd` again; strip the `isComposing` guard
and assert the fragment commits again. A test that cannot fail proves nothing, which is the
lesson ADR-482 §1 recorded when ADR-481's own gate stayed green over an unusable surface.

`api/test_adr483_name_lift_and_ime.py` (**17/17**) — the committed regression guard: the
single-derivation invariant, the FE/BE parity of the served placeholder set (every served
title *is* a placeholder by the server's own predicate), the IME guard on both inputs, and
the §4 decision that `path_slug` did not move.

`api/test_studio_name_is_one_fact.py` amended (34/34) — two checks asserted the pre-lift
function shape. The invariant they protect (the crumb shows the NAME, never the type leaf)
is unchanged and now better enforced; only the function carrying it is renamed.

Siblings green: ADR-469 (25/25) · ADR-470 (33/33) · ADR-466 (45/45) · ADR-480 (30/30) ·
ADR-481 (32/32) · ADR-482 (34/34). `next build` clean.

**Owed**: a human click-pass in the browser confirming the Korean rename end to end. The
gates execute the handlers, but no gate can see a live IME — that is a real ceiling, not a
formality.

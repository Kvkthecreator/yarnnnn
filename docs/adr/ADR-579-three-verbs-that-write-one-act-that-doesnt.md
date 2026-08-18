# ADR-579 — Three verbs that write, one act that doesn't: ADD · NEW · UPDATE, and ASK

> **Status**: **Accepted** (2026-08-18); D4/D5/D9 **Implemented** same day; **D5.a/D6 Implemented same day** after the operator's click-pass follow-up (*"these also get replaced, swapped in full with the triad… while right click menu triad perhaps becomes 2 tier, nested"*); D7–D8 phased.
> Operator-ratified through the insert-model discourse: *"the top buttons than gets
> stremline towards ADD, NEW, UPDATE … that consistency applies to the center buttons,
> right click, AND the chat pane"*, with full sequencing delegated: *"do the resolution in
> full … streamline code and documentation, and can and should delete codebase where
> warranted to avoid dual approaches and future ambiguity."*
>
> **Preserves**: [ADR-444](ADR-444-the-mechanical-layer-executing-toolbar-and-slide-masters.md) D1 (two write paths —
> mechanical free, judgment metered; this ADR renames the *presentation* of that seam,
> never the seam) · [ADR-509](ADR-509-the-insert-route-follows-the-medium.md) (the route
> follows the medium; the named target) · [ADR-506](ADR-506-the-insert-door.md) (one
> rendered list, both doors — D4 here **takes** its §7 named-not-taken deferral) ·
> [ADR-466](ADR-466-the-mode-native-carve-one-grammar-n-native-editors.md) D4 (insert is provenance-shaped) ·
> [ADR-462](ADR-462-the-block-context-menu-and-the-metered-badge.md) D4 (the meter badge means METERED, not
> MUTATING — the badge survives unchanged) · [ADR-479](ADR-479-rearrange-as-planned-judgment.md)
> (prompt → named plan → validated mechanical execution — the consent shape D7 generalizes)
> · [ADR-454](ADR-454-the-two-verb-experience-converse-and-make-ambient-steward.md)/ADR-458
> (one conversation substrate; the artifact binding is data, never a second chat system) ·
> [ADR-333](ADR-333-compose-as-lazy-projection.md) D5 (no second production pass — the
> doctrinal ground for D9's deletion of `RepurposeOutput`).
>
> **Supersedes / closes**: [ADR-185](ADR-185-distribution-derivatives.md) (Proposed
> 2026-04-15, never implemented — closed **refused**, see D9) · ADR-506 §7's provenance
> deferral (taken) · [ADR-450](ADR-450-the-derive-recipe-registry-learn-from.md)'s four-recipe registry (amended
> to three — `context-brief` deleted, see D9).
>
> **Dimensional classification** (Axiom 0): **Mechanism** (Axiom 5 — where each act sits
> on the code↔judgment spectrum, and how that seam is *named* to the member) +
> **Channel** (Axiom 6 — which door carries which verb at which grain).

---

## 1. Context — four grammars in one menu, and an empty provenance

The 2026-08-18 canon audit (FOUNDATIONS/ESSENCE + the Studio, Text, and compose/derive
ADR lineages) found the insert model in a coherent but unnamed state:

- **Every insert in Text and Studio is deterministic by ratified law** (ADR-570 D7,
  ADR-572 D5, ADR-444 D1), licensed by two properties: *a connector cannot tell a toolbar
  press from a keystroke*, and *deleting the rendering leaves the file byte-identical*.
- **The LLM composes beside the canvas, never at the caret** — the bound lane writes whole
  files or DOM blocks as attributed revisions; the one judgment act inside Studio
  (Re-arrange) emits no markup (ADR-479).
- **ADR-466 D4 already names three insert provenances** — *from thin air / from the
  workspace / from inference* — and ADR-506 §7 deferred surfacing the grouping.
  "From inference" has **zero members**: the taxonomy exists, unpopulated.
- The Studio right-click menu carries four grammars at once: plumbing (Copy/Duplicate/
  Delete), conversion (Turn into), a **mechanism-named** section ("WRITE WITH AI"), and
  record acts (Copy link/History).
- The repurpose/compose lineage is fossils: `RepurposeOutput` is registered and **crashes
  on an undefined name** (`tw`, `repurpose.py:267`) after paying for the LLM call, with
  zero FE consumers since ADR-185; `context-brief` is a derive recipe with zero FE
  consumers; the format-agnostic axiom's mechanical toggle was deleted (ADR-447 D7.5).

What was missing is a **member-facing grammar** that names the seams the architecture
already has — and the deletion of the dual approaches that contradict it.

## 2. Decisions

### D1 — The verb grammar: ADD · NEW · UPDATE, and ASK

Every member-initiated act on an authoring surface is one of four, and the first
question each answers is about the **object**, never the mechanism:

| Verb | The question it answers | Lands a revision? | Mechanism |
|---|---|---|---|
| **ADD** | it exists elsewhere — bring it here | yes | always the hand — citation/arrival (upload or workspace pick). You cannot "infer" an existing thing into place. |
| **NEW** | it doesn't exist — create it | yes | forks: *myself* (thin-air fragment, free) / *with the colleague* (inference, metered) |
| **UPDATE** | it exists here — change it | yes | forks: *myself* (turn-into, move, edit — free) / *with the colleague* (rewrite, re-arrange — metered) |
| **ASK** | tell me about it | **no** | always the colleague, metered — an answer in the pane, zero writes |

Connectors are **out of scope for ADD** (operator ruling, 2026-08-18): ADD is workspace
pick or upload, nothing else. Plumbing (Copy/Paste/Duplicate/Delete) and record acts
(Copy link, History) stay **outside** the grammar — forcing them in would tax the
taxonomy for no member benefit.

### D2 — Grain follows the door

The verbs are constant; the **grain of the target** varies by door — ADR-509's "the
route follows the medium," extended one notch:

- **Toolbar** — artifact/page grain (New slide · Re-arrange · the palette door).
- **Right-click** — block grain (New block · Turn into · Rewrite · Ask).
- **`/` at the caret** — text grain (the palette, flow only).
- **The chat pane** — any grain, target *named* (D7).

UPDATE from a door without a selection acts at that door's grain and says so; the verb
never guesses a target (ADR-509 D3 restated as grammar).

### D3 — The mechanism seam is WHO, never HOW

Section labels and group headers **never name a mechanism** ("AI", "LLM",
"mechanical"). The seam the member reads is *who authors the revision*: myself, or the
colleague — with the meter badge (ADR-462 D4, unchanged) and, in the pane, the signed
attribution (`you · via ‹colleague›`, ADR-562 D5) as the receipts. The "WRITE WITH AI"
section header is retired by D5. The AI badge itself **survives**: it marks METERED,
which is a fact about cost, not a taxonomy of sections.

### D4 — Provenance grouping in the palettes (takes ADR-506 §7) — **Implemented**

Both block palettes group their one list by the first two provenances:

- **Studio** (`StudioSlashPalette` + `StudioBlockInsertMenu`, the two mounts of
  `blockRows`): group **Add — from the workspace** = kinds whose served row declares
  `cites != 'none'` (ADR-539 D2's derivation, so the grouping cannot drift from the
  registry); group **New** = the thin-air kinds. One list, two headers, both doors
  inherit — the grouping lives beside `blockRows`, not per-door.
- **Text** (`SlashMenu` + toolbar order): the same two groups — **Add** = image ·
  table-from-CSV (the two workspace-backed inserts, ADR-572 D17/D18); **New** =
  everything else.

Filtering still searches across both groups; an empty group renders no header. The
third group — **New with ‹colleague›** (from inference) — is D7's arrival; the grouping
ships now so its slot exists.

### D5 — The right-click menu re-sections by verb — **Implemented**

`StudioBlockMenu` reorders into: **New block…** (paged, leads — creation before
everything that acts on what exists) → plumbing, unlabeled (Copy · Paste · Duplicate ·
Delete) → **Update** (Turn into · Move · Bring · **Rewrite… ✦**) → **Ask** (**Check
this… ✦** · **Ask about this… ✦**) → **This block** (Copy link · History). The
mechanism-named "Write with AI" header is deleted per D3; `Check this…` moves out of a
"write" section it never belonged to (it writes nothing — ADR-462 D4's own observation,
now structural). The member-facing label "Insert block…" renames to **"New block…"**
(the grammar's word for creation; the internal `insert` vocabulary — props, ops,
ADR-509's language — is unchanged: it names *placement*, which is still what the code
does).

**D5.a — two-tier (operator-ratified same day, implemented).** The flat sections became
the menu's **top tier**: Update and Ask are expandable rows (the convert-submenu
pattern), so the menu reads `New block… → plumbing → Update ▸ → Ask ▸ → This block` at
a glance and expands on intent. Every wired handler is unchanged — a tier is chrome,
never a second write path (ADR-462 D1). Move/Bring/Turn-into and their ADR-482/541
withdrawal rules live inside the Update tier with conditions intact; the badge marks
the colleague's paid rows exactly as before.

### D6 — The toolbar triad — **Implemented** (operator-ratified in full, same day)

The Studio toolbar re-cuts to the verb cluster **wholesale** — the operator's ruling:
*"these also get replaced, swapped in full with the triad (thus, even new slide,
re-arrange find their appropriate home under new discipline)."*

- **[+ Add]** — no dropdown (Add has no page-grain member): opens the one grouped
  palette filtered to the from-the-workspace group, at the resolved target (paged) or
  the caret (flow).
- **[+ New]** — on paged, a dropdown carrying BOTH grains: `Block…` (the palette's New
  group at the resolved target) above the New-‹noun› arrangement gallery. On flow, the
  direct block door (types the `/` — ADR-506 D1 preserved).
- **[Update]** — Re-arrange re-homed under its verb; judgment, plan validation, and the
  `Refining…` state unchanged (ADR-479, ADR-524 D4). Absent on flow (no page-grain
  update exists there; block-grain Update lives in the right-click menu, at the target).

The verb rides `onInsert(at, verb?)` → `openInsertMenu(x, y, verb)` /
`pendingSlashVerb` → the palettes filter to the verb's group. **One list, one write
path** under every door (the ADR-506 D3 rule holds — the filter is a view of the one
grouping, never a second list). The standalone Insert button is deleted.

### D7 — The pane hosts structured turns, never a second surface (phase)

Colleague-routed verbs (NEW-with, UPDATE-with, ASK) surface in the **one** conversation
as typed turns — components *in* the transcript (ADR-454/458's one-substrate law):

1. **Seed turn** — every ✦ row lands here first: target named (ADR-509 D3), intent
   editable, meter visible; nothing fires until Send. This is `seedComposer` promoted
   from prefill-text to a typed turn — one mechanism behind every door (ADR-444 D3's
   visible-seed rule).
2. **Receipt turn** — the landed revision as a signed, revertible fact (author line,
   diff, History) replacing prose claims of success. Axiom 9: the act is an invocation;
   the pane is its narrative entry.
3. **Plan turn — coarse grain only.** Block-grain updates land directly (every revision
   is revertible; preview on a one-block rewrite is friction the undo covers).
   Artifact-grain updates get the ADR-479 shape: named plan shown, validated, then the
   deterministic mechanism executes. **Grain decides consent depth, not mechanism.**

### D8 — File-altitude ADD / NEW (phase)

Files and app landing pages carry the two buttons literally: **ADD** (upload ·
workspace pick — the arrival acts, ADR-552–555) · **NEW** (blank file — *myself*; "from
sources…" — *with the colleague*: pick N files → brief/deck/PRD, the multi-source
derive). "From sources…" is where the level-3 repurpose act gets its door — a **new
artifact citing its sources** (`derived_from`), never a second production pass over a
finished one (ADR-333 D5 holds). The landing question deferred by ADR-572 §3.3 (where a
derived brief lands) is answered by the door itself: the member is standing in the
folder it lands in, or names it in the seed turn.

### D9 — The deletion ledger — **Implemented**

Dual approaches deleted so the grammar has no shadow competitor:

| Deleted | What it was | Why |
|---|---|---|
| `services/primitives/repurpose.py` + `RepurposeOutput` registry rows + dispatch | LLM editorial re-format of finished output (ADR-148 Ph4) | **Broken** (`NameError: tw` after the paid LLM call), zero FE consumers since ADR-185, and doctrinally refused by ADR-333 D5 (a second production pass). Its replacement is D8's *new artifact from sources*. |
| `POST /recurrences/{slug}/repurpose` | The only live importer of the above | Dead door to a crashing primitive. |
| `system_calls.py` `"repurpose"` row | The model binding for the above | Sole caller deleted; an unpriced/uncalled row is registry noise. |
| `derive_recipes.py` `"context-brief"` | Derive recipe, zero FE consumers (verified again 2026-08-18) | Subsumed by D8's NEW-from-sources; a registry row without a door is exactly the ratified-but-unbuilt shape ADR-573 warned about. **Reversal condition**: if D8 ships and a single-source brief needs its own recipe, re-add it *with* its door in the same commit. |
| `cockpit_awareness.py` RepurposeOutput mention · `compose/task_html.py` caller note | Stale prose references | Reference sweep. |
| ADR-185 | Proposed, never built, superseded in every part | Closed **refused** by this ADR. |

`Compose` (the primitive) and the compose engine are **kept**: the engine has live
report/email callers (ADR-417), and the primitive is its chat door — dormant is not
broken, and deleting it is a report-lineage decision this ADR does not own.

## 3. What this ADR deliberately does not do

- **No LLM routing for ADD or NEW-myself rows** — the free/deterministic law (ADR-444
  D1, ADR-570 D7) is load-bearing: metering, the connector-indistinguishability
  property, and the operator's own ratified verdict ("select and edit ON SCREEN, IN
  REAL TIME", ADR-446).
- **No second chat system** — D7 is turns in the one lane, never a flow surface.
- **No connector sources in ADD** — out of scope by operator ruling.
- **No format-agnostic mechanical toggle revival** — repurposing is a judgment act
  producing a new cited artifact (ADR-443-as-amended, ADR-447 D7.5 stand).

## 4. Gates

- `api/test_adr579_verb_grammar.py` (script-style) — D4 grouping derives from `cites`
  (both mounts, one grouping module); D5 sections present, "Write with AI" absent as a
  section header, Check/Ask outside any write-named section; D9 absences (module,
  registry symbols, route, syscall row, recipe row) checked as *absences with
  falsifiable presence controls*.
- Amended: `test_adr450_derive_recipes.py` (three-recipe set), `test_adr556_system_calls.py`
  + `test_adr548_primitive_scope_doorway.py` (file lists), `test_adr509_insert_route.py`
  + `test_adr462_context_menu.py` (renamed label anchors).

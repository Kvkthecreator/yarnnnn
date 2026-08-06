# ADR-527: The emphasis tier — read off the bar

> **Status**: **Proposed** (2026-08-06). Derived from the operator's method, not a
> principle: *"can't we cross compare to existing google slides feature than work our ways
> backwards"* — supplied with a screenshot of the Google Slides/Docs format bar. The prior
> cross-comparison (ADR-526) answered a **structure** question because the Studio work it
> compared against was structural; the operator's actual intent was the **editing
> surface**, where the honest report is *"referencing google docs is too thin."*
> **Date**: 2026-08-06
> **Dimension**: **Channel** (what the member can say about text). No Substrate change —
> no new file, no new write door, no revision semantics. Every op below is either an
> existing `execCommand` through the ADR-521 D3 segmentation, or an existing `setToken`.
> **Relates to**: ADR-521 D2/D3 (the text tier and its per-block-intersection machinery —
> the mechanism every range op here rides), ADR-525 D3 (the Layout withdrawal this ADR
> **partially corrects** — align was bundled into a refusal it did not belong in),
> ADR-449 (the design-system contract — why colour is palette-bound and metrics are not
> offered), ADR-516 D6 (geometry/meaning boundary), ADR-519 §1 (the benchmark-reading
> method this ADR reuses: read the reference panel, classify every control, ship the gaps
> and record the refusals).

---

## 1. Context — the method, and what it exposes

ADR-519 did not reason from principles about what Studio's inspector needed. It put
Figma's panel beside ours and read off the differences, importing *"the panel grammar, not
the node types."* This ADR applies the same method to Docs with the Google Slides/Docs
format bar as the reference.

**The bar, left to right, against yarnnn Docs at `a361052`:**

| # | Control | Docs today | Verdict |
|---|---|---|---|
| 1 | Normal text ▾ (style ramp) | ✅ Typography dropdown | have it |
| 2 | Arial ▾ (font family) | ⚠️ document scope only | design system owns; per-block refused |
| 3 | − 22.5 + (point size) | ❌ | **refused** (§4) |
| 4 | **B** | ✅ ⌘B, cross-block (ADR-521 D3) | have it |
| 5 | *I* | ✅ | have it |
| 6 | <u>U</u> underline | ❌ | **ship** |
| 7 | **A** text colour | ❌ at range grain | **ship, palette-bound** |
| 8 | 🖍 highlight | ❌ | **ship, palette-bound** |
| 9 | 🔗 link | ✅ | have it |
| 10 | 💬 comment | ❌ | out of scope — a different ADR |
| 11 | 🖼 image | ✅ slash → cited figure | have it, different door |
| 12 | ▤▾ align | ❌ — withdrawn by ADR-525 D3 | **restore** (§3 D3) |
| 13 | ↕ line spacing | ❌ | **refused** (§4) |
| 14 | ☑ / ▤ / ⒈ lists | ✅ three block kinds | have it |
| 15 | ⇤ ⇥ indent / outdent | ⚠️ Tab in lists only | **ship at block grain** |
| 16 | ✂ clear formatting | ❌ | **ship** |
| — | the ruler (margins, indents) | ❌ | **refused** — presumes a page (ADR-480 D6) |

Plus **strikethrough**, which this bar omits but Notion and Docs both carry, and which is
the exact sibling of underline.

**The finding**: of sixteen controls, five are already shipped, three are refusals with
standing reasons, one is a separate product (comments), and **six are simply absent with
no ADR refusing them**. That last pile is the answer to "too thin" — and it is entirely
*emphasis*, the tier ADR-521 D2 already named and built the machinery for.

## 2. Why the thinness happened, precisely

Not carelessness, and not a wrong decision — a **partial inheritance**.

yarnnn Docs is Notion-class on the axis that matters most: **who decides metrics**. Notion
says the system does (you pick Heading 1; the app decides 30px). Google Docs and Word say
the writer does (point sizes, line spacing, a ruler). yarnnn is Notion here and should
stay there, because yarnnn documents wear a *workspace* design system (ADR-449) — they are
not self-contained artifacts, which is exactly what Docs and Word assume.

But **"the system owns metrics" was never a reason to be thin on emphasis.** Notion holds
the metrics line *and* ships underline, strikethrough, highlight, text colour. We inherited
the restriction without the compensating richness. That is the whole diagnosis.

## 3. Decisions

### D1 — Range emphasis extends the existing text tier

> **Underline, strikethrough and clear-formatting are text-tier ops, and they ride the
> ADR-521 D3 machinery unchanged.**

`applyToggle(cmd)` already performs per-block-intersection segmentation with the
deterministic Word rule (if any eligible segment is unformatted, apply everywhere; only
when all are formatted does it remove). It takes any `execCommand` name. `underline` and
`strikeThrough` are therefore **one registry row each**, not new mechanisms — the same
"one implementation, N entrances" shape as ADR-521 D4's ⌘B.

- **Underline** — `applyToggle('underline')`, commits as `<u>`.
- **Strikethrough** — `applyToggle('strikeThrough')`, commits as `<s>`.
- **Clear formatting** — `removeFormat` over the segments, plus an explicit strip of the
  palette marks D2 adds (they are spans, and `removeFormat` does not reliably drop
  attribute-carrying spans). Never clears *structure*: a heading stays a heading, a list
  item stays a list item. Clearing arrangement is D3's job, not this one.

The b/i → strong/em normalization at the commit (ADR-446 D2 / ADR-456 W2) is extended to
u → `<u>` and s → `<s>`; the source keeps speaking semantic tags.

### D2 — Colour is palette-bound, at range grain

> **Text colour and highlight ship as a fixed set of design-system roles, never a colour
> picker.**

This is the one place this ADR chooses canon over the benchmark, deliberately. Google Docs
offers an arbitrary picker; ADR-449 and the pane's own words (*"emphasis via the palette
variables — never raw color"*) forbid one. **Notion's answer is the shape we take**: a
fixed palette of text and background colours, which closes the gap without breaking the
commitment.

The roles come from the kernel palette that already exists (`--ink · --muted · --accent ·
--fresh · --warn · --danger · --paper`):

- **Text colour** — Default | Muted | Accent | Success | Warning | Danger.
- **Highlight** — Default (none) | Accent | Success | Warning | Danger, each rendered as
  `color-mix(in srgb, var(--role) 15%, transparent)` — the callout-variant precedent
  (ADR-487 D2), reused rather than re-invented.

Both write a **`data-mark` span** (`<span data-mark="accent">`, `<span
data-highlight="warn">`), never an inline `color:` or `background:`. The kernel supplies
one rule per role, so a design-system change re-themes every document that used them —
which is the entire reason for the constraint. The mark attributes join the ADR-526 D4
internal-paste keep-list, so cut/paste of coloured text round-trips.

### D3 — Align is restored; indent joins it at block grain

> **`data-align` is arrangement-in-measure, not box geometry. ADR-525 D3 withdrew it as
> collateral, and this ADR puts it back.**

The receipt is the kernel's own rule: `[data-align="center"] { text-align: center; }`
(`studio.py:1050`). That is *text* alignment — a property of prose inside its own measure,
which flow has. ADR-525 D3 withdrew the **whole Layout section** because `size` (Hug|Fill)
is a container row and flow has no containers; that reasoning is correct for `size` and
does not reach `align`. Bundling them was an over-cut, and this ADR says so plainly rather
than quietly re-adding the row.

- **Align** returns at block grain on flow, as **Left | Center | Right** (absence = left,
  the ADR-461 B1 convention). It renders in a new **Text** section, not a resurrected
  Layout section — the section name matters: this is arrangement of text, and Docs still
  has *no layout surface* (ADR-521 D1 stands).
- **Indent / outdent** at block grain — `data-indent="1|2|3"`, one kernel rule each
  (`margin-inline-start`). Bounded to three steps: enumerable values, so a token, not a
  measure (the ADR-461 D4 line). The existing Tab/⇧Tab in lists (ADR-521 D4) is unchanged
  and remains list-scoped; this is the paragraph-grain affordance the bar's ⇤/⇥ carry.

`size` (Hug|Fill) stays withdrawn on flow. The ADR-525 D4 re-key of `size`/`align` to
`["block-staged","media"]` is **amended**: `align` becomes
`["block-staged","media","block-flow"]` — the `block-flow` grain ADR-525 D4 added to the
vocabulary and, until now, nothing used.

### D4 — The pane is the home; the bar keeps what follows the caret

> **Range emphasis renders in the properties pane at block scope, as a Text section.**

The operator's instruction is explicit — *"implement the features themselves now to the
properties panel where existing information is"* — and the diagnosis behind it is that
Docs' pane currently *"looks very similar to studio apps"*: a heading selection offers
Typography · Tone · Turn into, three controls, which reads as a thinned layout pane rather
than a writing pane.

So the pane gains a **Text** section (D1's toggles + D2's palettes + D3's align/indent),
sitting between Identity and Typography. The inline bar keeps B/I/code/link — it is the
*at-the-caret* affordance and ADR-521 D3 built it — and gains nothing here; two entrances
to one implementation, which is the standing shape.

**The pane can now drive a range op**, which is new: a `yarnnn-fmt-op` command on the
existing parent→runtime channel, so the pane's buttons and the bar's buttons call the same
`applyFmt`. The runtime **preserves the live range across the round-trip** (the pane steals
focus; the saved-range mechanism the link input already uses is reused).

Section order follows the spine (ADR-519 D3, unchanged): **Identity → Text → Typography →
Style → Content**. Text precedes Typography because emphasis is the more frequent act.

## 4. Refused, with reasons recorded

- **Point size** (bar #3), **line spacing** (#13), **the ruler / margins** — all *metrics*,
  and metrics belong to the design system (ADR-449). Offering them makes the system
  advisory rather than authoritative, which is a far larger decision than a toolbar row and
  is not this ADR's to take. Notion agrees; Docs and Word predate design systems.
- **Per-block font family** (#2) — same reason; the face is a document-scope token.
- **A colour picker** — D2's palette is the answer (ADR-449, "never raw color").
- **Comments** (#10) — multi-principal annotation on shared substrate is a product, not a
  row. Out of scope by size, not by principle.
- **No new op, no new primitive, no schema change.** Range ops are `execCommand` through
  D3's segmentation; block ops are `setToken`.

## 5. Implementation scope

| # | Site | Change |
|---|---|---|
| 1 | `projection.ts` | `applyFmt` gains underline · strikeThrough · clear · mark · highlight |
| 2 | `projection.ts` | palette marks as `data-mark`/`data-highlight` spans, never inline colour |
| 3 | `projection.ts` | `yarnnn-fmt-op` command + range preservation across the pane round-trip |
| 4 | `projection.ts` | u/s in the commit normalization; marks in the ADR-526 D4 paste keep-list |
| 5 | `api/services/studio.py` | kernel rules for the mark/highlight roles + `data-indent` |
| 6 | `api/services/studio.py` | `align` re-keyed to include `block-flow`; `indent` token added |
| 7 | `StudioDesignTab.tsx` | the **Text** section at block scope on flow |
| 8 | `StudioCanvas.tsx` / `StudioSurface.tsx` | the format command prop |
| 9 | `AUTHORING.md` | the Inline-format matrix rows; the pane matrix's Docs cells |

New gate `adr527_emphasis_tier.mjs`: executes the real toggle routing, the mark
construction (asserting no raw colour reaches the DOM), the clear op's structure-preserving
behaviour, and the align/indent token grains — falsifier per claim.

## 6. Consequences

**Docs' pane reads as a writing pane.** A heading selection goes from three controls to a
Text section with the emphasis a writer expects, plus Typography, Tone and Turn into.

**The design-system commitment is untouched and is now visibly the reason** — every colour
in D2 is a role, and the pane already says so.

**Accepted cost**: two homes for format (bar and pane). This is deliberate, not drift —
they are two entrances to one `applyFmt`, the ADR-521 D4 shape. The bar follows the caret;
the pane shows the full set. A member who never opens the pane loses nothing they had.

**Accepted cost**: `data-mark`/`data-highlight` are two more annotations on the substrate.
They are *inert names* by the ADR-511 D8 rule — skins style them, nothing gates on them —
and they are palette roles, so they cannot carry a raw value.

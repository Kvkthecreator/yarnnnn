# ADR-455 — Document-grain tokens, the file-verb completion, and the navigator that earns its place

> **Amended by ADR-458** (2026-07-14, placement reversal): the surface-bar ⋯ ("File actions" —
> Copy link · Duplicate · Rename · Move · Trash) is DELETED; the file verbs move into the Design
> tab's **document scope** (the one settings home — completing the consolidation this ADR started
> when it moved Notion's typography half there). The verbs and the shared `useFileOrganizeVerbs`
> implementation are unchanged; only the chrome moved.

> **Status**: **Accepted** (2026-07-13, operator-ratified — "full aligned, lets proceed"). The
> operator, from Notion's page menu (Ag Default/Serif/Mono · Copy link · Duplicate · Move to ·
> Trash), asked whether the Studio can accommodate document-level design controls — and whether
> the left navigator (for documents, a read-only list) should simply be deleted. The assessment
> held: Notion's menu CONTENT fits the ADR-453 grain homes exactly (its single mixed-grain menu
> shape does not — we do not clone it); and the document outline is dead weight only because its
> v1 never navigated — the fix is cheaper than the deletion, so it navigates and collapses
> instead. Deletion remains a one-line conditional if use proves it worthless.

**Date**: 2026-07-13
**Dimension**: Substrate (document-grain tokens on the artifact root) + Channel (Design tab
document scope · surface-bar `⋯` · the navigator).

**Amends**: ADR-453 (the token registry gains the **document grain** — `data-font`,
`data-measure` on the artifact root; the kernel element bumps to v2 and self-retrofits;
`setToken` targets the root) · ADR-447 D7.2 (the navigator becomes collapsible; the
document/article outline becomes navigational — deck parity via the same scroll bridge) ·
ADR-446 (the surface-bar `⋯` grows Duplicate + Copy link beside Rename/Move/Trash).
**Preserves**: the one mechanical write door + CAS + free (every new act is one attributed
revision or a pure FE act) · tokens-not-pixels · absence-is-default · the ADR-449 cascade
(the skin still outranks tokens — the Design tab hints when a design system is applied).

## D1 — Document-grain tokens: `data-font` and `data-measure`

Two new token families on the **artifact root** (`<html>`), a new `applies` grain:

| Token | Applies | Values | CSS |
|---|---|---|---|
| `data-font` | `document` (all layouts) | `serif · sans · mono` | `html[data-font=…] body { font-family: … }` — Auto = the layout/skin default |
| `data-measure` | `document-flow` (document + article; a deck is fixed-stage) | `wide` | relaxes `main`/`article` max-width |

Absence is the default, as ever. The kernel CSS bumps to **v2**; the ADR-453 D2 retrofit
mechanism (versioned marked element, upserted on any token op) carries the new rules into
existing artifacts with zero migration. Because tokens sit below the skin in the cascade, an
applied design system may override the font — **correct semantics** (workspace identity
outranks a local switch); the Design tab shows a hint rather than fighting the cascade.

## D2 — The Design tab's document scope becomes a real panel

Typography chips with **"Ag" previews** (Auto · Serif · Sans · Mono, each rendered in its own
stack — the Notion affordance, our grammar) + the Width control (document/article only) +
the existing design-system picker. Current values parse from the artifact SOURCE at render
(derived, never stored). The lane learns the new families automatically — the posture's token
section derives from the registry (one grammar, both hands; prompts CHANGELOG entry).

## D3 — The file-verb completion: Duplicate · Copy link

Surface-bar `⋯` (the ADR-446 organize menu) gains, via a generic `extraItems` extension point
on the shared `FileContextMenu`:

- **Duplicate** — read the open artifact's content, write it at a `-copy` sibling path through
  the existing mechanical door (one attributed revision, `Studio: duplicate …`), open the copy.
- **Copy link** — the `?studio.file=` deep link to the clipboard; the workspace is
  multi-member (ADR-373), a member-facing URL is now genuinely useful. Distinct from the
  ADR-437 Share origin (which stays untouched).

Studio-only in this pass; Files-surface parity is a named follow-on. "Copy page contents" is
deferred (marginal); a command palette ("Search actions…") is a separate idea, not smuggled in.

## D4 — The navigator earns its place: navigable + collapsible

- **The outline navigates** (document/article): entries carry their heading's
  `data-block-id` (scaffolds + posture already annotate headings); clicking one SELECTS the
  heading block (anchoring the Design tab) and scrolls the canvas to it via a new
  `yarnnn-scroll-to-block` runtime message — the deck's D7.7 scroll bridge, generalized.
- **The navigator collapses** (all layouts): a toolbar toggle hides the left column on desktop
  and reclaims its width (compounds with the 77ce421 narrow-viewport guard). Session-local
  state; persistence is a later nicety. Mobile is untouched (the nav is already a tab there).
- **Deletion deliberately not taken**: judged against the benchmark class (Docs' outline rail,
  Word's nav pane) on the Studio's long-document direction — but recorded as the fallback if a
  *navigating* outline still goes unused.

## The one-line statement

**Notion's page menu arrives sorted by grain, not cloned: document typography and width land as
root-grain property tokens (self-retrofitting kernel CSS v2, skin still wins, the Design tab's
document scope becomes a real panel with Ag-preview chips), Duplicate and Copy link complete the
surface-bar file menu through the same one door, and the left navigator — instead of dying for
the crime of a v1 that never navigated — gains click-to-scroll heading navigation and a collapse
toggle, so it earns its width or gets out of the way.**

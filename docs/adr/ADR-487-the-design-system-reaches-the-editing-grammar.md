# ADR-487 — The design system reaches the editing grammar: the playable ramp, semantic variants, and system-aware controls

- **Status**: Accepted + **Implemented** (2026-07-25) — D2/D4 (kernel v13, `998eb61`), D1
  registry+turn-into (`fc39e20`), D3 painted controls (`a486789`), D5 workspace default
  (`d4f19bd`). **Two named remainders, deliberately deferred to the flow lane** (§9).
- **Dimension**: Channel (primary — what the member can shape, and what the controls speak) + Substrate (three new kernel slots, one new config file; no schema)
- **Supersedes**: nothing
- **Amends**: ADR-455 (the `font` token's values resolve through face *slots* — the supply/select line completed) · ADR-456 (the block/token registry grows by one wave: heading grammar + callout variants) · DESIGN-SYSTEMS.md §5 ("semantic `--fresh/--danger/--warn` wire no selector yet" — they wire now)
- **Preserves**: ADR-453 D1 (tokens reference intent, never raw values) · ADR-461 (the enumerated-token invariant — every value pre-declared, every selector in the kernel) · ADR-443 R1 (the DOM is the model) · ADR-449/453 D4 (one mechanical apply door) · the §5 fallback discipline (a skin-less artifact is byte-identical)
- **Derivation**: the 2026-07-24/25 operator discourse (Figma text-styles reference → the first-principles audit of the editable grammar)

---

## 1. The question

The operator, from Figma's Text-styles panel (`display/lg · 50/130`, a Fill picker showing
`label/body`): *once a design system is applied — or is the workspace's default — the member
should see it in the artifact's scaffolding AND in every editing gesture: headings, fonts,
colors, the slash command, the properties panel. Selecting and adjusting should feel
"design-system applied."*

An audit of the editable grammar (2026-07-25, against `STUDIO_TOKENS` / `STUDIO_BLOCKS` /
`STUDIO_MEASURES` / the kernel CSS / the flow format bar) asked the first-principles form of
that question: **a design system is roles with instances; where does the system have instances
but the grammar no role to receive them?**

## 2. What the audit found

1. **The type ramp has zero member-facing controls.** The kernel carries a full ramp
   (`--text-xs…5xl`, §5 Move 1); layouts map h1→3xl/4xl, h2→xl/2xl. But `heading` is not in
   the insertable registry (it exists only in template scaffolds), `TURN_INTO_KINDS` excludes
   it, and the flow format bar is Bold/Italic/Code/Link — nothing more. The single most
   important axis a design system ships is present in the kernel and unplayable by the member.
2. **The semantic color trio is dead contract.** `--fresh/--danger/--warn` entered the §5
   vocabulary with the honest note "no kernel chrome reads status color." Meanwhile `callout`
   has exactly one hardcoded accent look. Each is the other's fix.
3. **The choice surfaces are design-system-blind.** Tone chips are gray text; the `font`
   token shows generic labels in the UI font; nothing shows a selected block's resolved
   face/size. The system applies to the canvas and changes nothing about the controls.
4. **Apply is artifact-only.** There is no workspace default — a new artifact is born
   skin-less even when the workspace has exactly one identity it always wears.
5. **Adequately scoped already**: shape/radius member-invisible (identity, not per-artifact
   choice); align/valign/measures sound and already themable.

## 3. The governing principle

**Every member control names a role or a rung, never a raw value — then every new control is
design-system-fed by construction.** The member picks *heading 2*, *accent tone*, *the serif
family*; the applied system supplies what those resolve to. The document never records a pixel
or a hex, so removing or swapping the system never leaves a dangling instance — the closed
vocabulary discipline (ADR-453/461) holds at full strength while the *experience* converges on
Figma's named-styles feel.

## 4. Decisions

### D1 — The type ramp becomes playable (heading grammar)

Heading joins the member grammar on all three entrances:

- **Registry**: `heading` becomes an insertable block kind
  (`<h2 data-block="heading">…</h2>`) — it already exists in every scaffold; the registry row
  makes the slash/insert surfaces offer what the scaffolds already use.
- **Turn-into**: the conversion surface gains heading *levels* — Heading 1/2/3 as targets, and
  a heading can change level (same kind, the tag carries the rung) or demote to Text. The old
  exclusion ("headings anchor pages") was about *sweeping them in re-arrange* — that
  protection stays; it never needed to make headings unauthorable.
- **Flow format bar**: a text-style switch (Text · H1 · H2 · H3) joins B/I/Code/Link — the
  Notion gesture, on the block the caret is in.

The kernel already sizes every level from the ramp, so this ships pre-themed: applying a
system visibly restyles the levels the member now actively chooses between. No new CSS
mechanism — h1/h2/h3 are semantic tags, not tokens, so the ADR-461 invariant is untouched.

### D2 — Callout variants wire the semantic trio (kernel v13)

A new block-grain token, gated to callouts:

```
variant: note | success | warning   (applies: block-callout; absence = the accent default)
```

Kernel selectors read the §5 semantic slots with exact-current-behavior fallbacks:
`[data-variant="success"]` → `--fresh`, `warning` → `--warn`, `note` → `--ink-10`-hairline
neutral; the *danger* slot stays reserved (a fourth value is one row when demanded). This
closes §5's "wire no selector yet" honestly: the selectors arrive with the member affordance
that justifies them, not as speculative chrome. New `applies` target `block-callout` joins
`APPLIES_TARGETS`; the FE gates on `blockKind === 'callout'` (the `media` precedent).

### D3 — The controls wear the applied skin (FE, derived-never-stored)

- **Tone chips** are painted with the *resolved* skin's actual values (the shared `skinVars`
  parse against the artifact's marked element — same source the theme panel reads).
- **The font token's options** render each label in the face it resolves to.
- **The selected block gets a type readback** — "Heading 2 · 1.7rem · ‹face›" — computed from
  the projection's resolved styles. Read legibility only; no new state, no new endpoint.

This is the Figma feel at the exact moment of editing, achieved without instance-naming.

### D4 — The `font` token resolves through face slots (kernel v13)

The three kernel rules gain slots with their exact current stacks as fallbacks:

```css
html[data-font="serif"] body { font-family: var(--font-serif, Georgia, 'Times New Roman', serif); }
html[data-font="sans"]  body { font-family: var(--font-sans, system-ui, …); }
html[data-font="mono"]  body { font-family: var(--font-mono, ui-monospace, …); }
```

A design system supplies *instances for the three family categories* (`--font-serif: 'Tiempos'…`).
The member's choice stays the closed three-value vocabulary (serif/sans/mono — categories,
ADR-222); the system decides what each category *is*. This completes ADR-455's "a skin
supplies faces; the token selects among them" — previously true of sizes only. A system that
ships no face slots changes nothing (fallbacks are the current stacks). Named per-face styles
(a fourth+ value from the skin) are **refused** here — see D8.

### D5 — The workspace-default design system

- **Storage**: `/workspace/operation/_studio.yaml` (machine-parsed, underscore convention,
  ADR-254) with one key: `default_design_system: <manifest-path>`. Written through the one
  door (`write_revision`), attributed to the operator.
- **Birth-apply**: artifact creation (`build_skeleton` callers) resolves the default and
  applies its skin element at birth — a new artifact is *born wearing the house identity*.
  Absence of the file/key = today's behavior, byte-identical.
- **Surface**: the manage panel (`studio.system=`) gains "Set as workspace default" /
  "Default ✓"; the landing card shows a `Default` badge. Vocabulary payload carries
  `default_design_system` (it already carries the systems list — one fetch, no new roundtrip
  for the read side); one small POST route sets it.
- Per-artifact apply/remove is **unchanged and always wins** — the default is an inheritance
  rule at creation, never a live coupling. (A "re-skin everything retroactively" verb is a
  different, heavier act — not taken here.)

### D6 — Space ramp: considered, deferred

A `--space-*` ramp was scoped and **deferred with a named reason**: the four `pad` literals
mix magnitudes (a slide's `2rem` and a band's `0.25rem` are both "small"), so a single
category slot would either mis-scale one context or need per-context instance slots — which
drifts toward the kernel naming instances. The §5 lesson ("widen where the eye reads the
brand") also ranks spacing below type/color for felt identity. Re-open when a real system's
spacing scale demonstrably misses.

### D7 — Re-arrange previews wear the skin: named, trailing

The arrangement gallery previews render generically today. Rendering them through the applied
skin extends "feels applied" to layout choice. Real but trailing — sequenced last, after the
decisions above prove out, and it touches only preview rendering (no grammar).

### D8 — Refused (recorded so the boundary is honest)

- **Skin-defined token values** (`data-tone="brand-teal"`): a removed system would leave
  dangling attributes — the Figma detached-style rot the closed vocabulary exists to prevent.
  Needs its own ADR if ever; not taken.
- **Composite named text styles** (a `styles:` manifest section; blocks selecting
  `display/lg`): re-imports the freeform-tool problem Studio's semantic blocks avoid. If
  D1+D3 land, the ramp handles + readback deliver the felt experience without it.
- **Raw value pickers** (font-size/hex inputs): breaks ADR-453 D1; never.

## 5. FE experience (the acceptance frame)

Flow document: select text → style switch; "Heading 2" snaps to the system's h2 — face, size,
leading. Deck: select a block → type readback + tone chips in the system's palette; callouts
offer note/success/warning in the system's colors. Landing: the house system carries a
`Default` badge; every new artifact is born wearing it. Slash: heading insertable at level.
Everything the member touches confirms the identity; nothing they write records an instance.

## 6. What a design system author gains

Three new slot categories to ship: `--font-serif/sans/mono` (faces per family) — plus the
already-live semantic trio now *renders* (callout variants). The derive recipe
(`derive_recipes.py`) names all of these so Freddie-authored systems hit them.

## 7. Gates

- `test_adr453_property_layer.py` — the `variant` token: registered, interpreting selectors,
  posture-derived (existing invariants pick it up; counts re-pinned).
- `test_adr449_design_system.py` — face slots in the contract; probe (a)-bucket re-pinned.
- `test_adr456_*` — registry growth (heading row) conforms to wave discipline.
- New checks ride the existing gate files (one gate home per concern, no new file unless a
  concern has none — D5's birth-apply lands in `test_adr449`).
- FE: `npx next build`; the live click-pass remains owed and named (the standing Studio debt).

## 8. Sequencing (each its own commit)

1. This ADR + docs cascade (DESIGN-SYSTEMS.md §5/§6 amendments, STUDIO.md §Theme).
2. **Kernel v13** (D2 + D4): variant token + selectors, face slots, `APPLIES_TARGETS`,
   derive recipe, gates re-pinned.
3. **D1 backend + FE**: heading registry row + Turn-into levels.
4. **D3**: system-aware controls (Design tab).
5. **D5**: workspace default (yaml + birth-apply + manage/landing affordance).
6. **D1 format bar** (flow style switch) — sequenced LAST deliberately: the format bar is the
   sibling flow lane's active territory (ADR-480/481/482; two open regressions adjacent);
   land against freshly-pulled main with the tightest possible diff.
7. (Trailing, unscheduled) D7 previews.

## 9. Implementation status (2026-07-25) — what landed, what is handed off

**Landed** (each its own commit + gate, all on main): kernel v13 (`998eb61` — variant token
37/37, probe (a)-bucket 17→21) · heading registry + turn-into levels (`fc39e20` — reachable in
BOTH modes: Design tab "Turn into" and the right-click submenu, which work in flow too since
blocks stay annotated there) · painted controls (`a486789`) · workspace default (`d4f19bd` —
ADR-449 gate 49 checks incl. a live broken-read behavior check).

**Handed off to the flow lane** (the ADR-480/481/482 arc), with the design constraint found
during this pass recorded so it isn't re-derived:

- **The format-bar style switch** (D1's third entrance). A naive
  `execCommand('formatBlock')` **drops `data-*` attributes** — it would strip
  `data-block`/`data-block-id` and corrupt the annotation grain. The correct shape is an
  attribute-preserving re-tag (create the new tag, copy attributes, move children, restore
  the caret) against whatever flow DOM shape that arc settles (legacy flattens at
  projection, ADR-481). Two open flow regressions sit in exactly this code region; landing
  the switch inside that arc is the honest sequencing, not a scope cut — the capability
  (heading levels) already ships via the other two entrances.
- **The type readback** (D3's remainder): "Heading 2 · 1.7rem · ‹face›" on the selected
  block wants resolved computed styles, which only the projection's selection payload can
  carry — same file, same seam, same rider.

**The live click-pass on the whole ADR-487 surface remains owed** (the standing Studio debt —
compile + gates are the validation ceiling until a human drives it).

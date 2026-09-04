# ADR-641 — the mark carries an accent

**Status**: Accepted
**Date**: 2026-09-04
**Supersedes**: nothing. Amends the presentation half of ADR-297 (surface icons)
and ADR-422 D3 (root icons).
**Related**: ADR-297 (surfaces + `icon_key`) · ADR-422 D3 (kernel-named root
glyphs) · ADR-459 (`studioShapes`, the pattern this copies) · ADR-431 (brand
marks at `currentColor`) · ADR-258 (colour deleted from chat roles) ·
ADR-601 D1 (an agent serves many apps) · ADR-636 (assert the relation, both
directions)

---

## Context

The operator observed that the app and agent marks across the authenticated
shell are monotone, and asked whether they could carry more colour — with
Google Workspace's product row as the reference.

The first read of the codebase said the monotone was doctrine. That read was
**half wrong**, and the correction is the substance of this ADR.

### What the sweep actually found

Three colour registries already ship, and have for months:

| Registry | Shape | Consumers |
|---|---|---|
| `web/components/authoring/studioShapes.ts` | `{ icon, color }` per shape slug — document sky · deck amber · web emerald · image rose | 4 |
| `web/components/workspace/FileIcon.tsx` | `{ icon, color }` per extension, 20 rows | file grid + tiles |
| `web/lib/workspace/attribution.ts::authorAccent` | a **ratified hue vocabulary** per principal class — you=primary · reviewer=indigo · yarnnn=sky · mcp=amber · member=teal · **agent=violet** · platform=cyan | attribution dots + badges |

So the shell was not monotone on principle. It was monotone **inconsistently**:
Files and Studio were colourful, while the Dock, the Launcher, the surface page
headers, the Agents page and the new-chat door were grey.

The inversion had a sharp instance. In `WorkspaceTree.folderIcon`, the
**canonical** backend-driven root glyphs (ADR-422 D3) rendered
`text-muted-foreground`, while the **deprecated path-string fallback**
immediately beneath them carried a full hue ladder
(`/explorer/context` → sky, `/explorer/outputs` → orange, `/workspace/agents` →
purple, and five more). The dead code was the colourful code.

### What genuinely cuts the other way

Three decisions do argue against colour, and all three survive:

- **`AgentFace.tsx`** records an operator ruling (2026-07-16): an agent's face
  is an **uploaded image**, and *"not a colour swatch (the shipped placeholder,
  which was debt: 'a picture you upload and never see is worse than no
  picture')."* A per-agent swatch was shipped, judged debt, and replaced.
- **ADR-431** forced external-LLM brand marks to `currentColor` *"so the
  neutral roster tone is preserved."*
- **ADR-258** deleted colour differentiation from chat roles in favour of name
  + icon.

Each of those is about **identity-by-colour for a PRINCIPAL** — a face, a
brand, a speaker. None governs an app's glyph. That is the line this ADR draws.

### Why the Workspace reference does not transfer whole

Gmail's red envelope is a **trademark**: those icons are colourful because each
names a separately-branded product. yarnnn's four apps are not four brands;
they are panes of one workspace. And ADR-449's design-system contract lets a
member's skin repaint the chrome through `--accent` / `--ink`, so hard-coded
per-app brand marks would be the one thing in the shell a skin cannot touch.

The Dock also already answers *"tell them apart at a glance"* structurally,
with semantic bands and dividers: `Chat │ Studio Images │ Files Agents` —
think / make / record.

---

## Decision

**D1 — an accent map sits beside each glyph map, in the `studioShapes` shape.**
`resolveSurfaceAccent(slug)` in `surface-icons.tsx` and
`resolveRootAccent(iconName)` in `root-icons.tsx`: a `Record<string, string>`
of Tailwind classes with a **neutral fallback**, so an undeclared row renders
exactly as it did before. This is not new architecture — it applies a ratified
pattern to the two registries that missed it.

**D2 — the surface accent is keyed on the SLUG, not the `icon_key`.**
An `icon_key` is shared (`bell` dresses Notifications and the alerts row;
`message-circle` dresses Chat and the chat-drawer), so a hue keyed on the glyph
would paint every sharer alike — the opposite of telling apps apart. The root
accent IS keyed on the icon name, because a root's glyph is 1:1 with its root.

**D3 — accent is IDENTITY; state and semantics keep their own colours.**

- The Dock encodes **state** with colour already: foregrounded is an inverted
  `bg-foreground text-background` slab, kept-not-open is dimmed to `/50`. The
  accent applies **only to the open-and-backgrounded cell** — the one cell with
  no state claim on the colour. Two colour languages on one 9×9 icon is the
  ADR-258 fault arriving in the Dock.
- **Red and amber are reserved.** `--destructive` (the notification badge) and
  the amber AttentionCenter rows mean *something is wrong / wants you*. No
  surface or root takes either. This cost Slides its amber (it matched
  `studioShapes`' deck hue) — an app permanently wearing the attention colour
  would read as *"Slides needs you"* forever. It is orange instead. The two
  tables need not agree: `studioShapes` colours an **artifact** in a grid of
  artifacts; this colours an **app** in a row of apps, and only the second one
  lives beside the alerts.

**D4 — the agent glyph carries ONE hue for the class, reusing `authorAccent`'s
violet.** Not per-agent, and **not derived from the agent's app**: since
ADR-601 D1 an agent may serve several apps (Editor → Slides + Text), so an
app-derived hue has no single answer for exactly the many-to-one case that ADR
made free — it would pick one app and silently misname the others. The glyph
says *"an agent"*; the app **chips** on the same row carry the per-app accents
and say *which apps*. Reusing violet means the roster and the attribution dots
in Files cannot disagree about what an agent looks like.

The `AgentFace` ruling is untouched: a face is still an uploaded image. A
**glyph** is not a face — it is the fallback mark for an agent that has no
picture, and giving it the class hue is not the per-agent swatch that was
judged debt.

**D5 — the system roots are deliberately UNCOLOURED, and the path-string
ladder is DELETED.** The first cut gave every root its own hue and the rendered
spine was a rainbow: eleven saturated rows where colour distinguished nothing
because everything had it — and the two rows left neutral read as *broken*
rather than *quiet*. Only the two live zones carry colour (Documents teal,
Downloads cyan, matching `authorAccent`'s member + platform); the kernel
residue behind the collapsed "System files" disclosure stays neutral. That
restraint is what makes the two live zones legible, and it is exactly the
distinction `WORKSPACE_ROOTS.group` already draws.

The path-string ladder in `folderIcon` is deleted with it. Every arm was
unreachable — the pane renders `treeNodes`, and all four nodes the Files page
builds set `icon_name`, so the registry branch always won.

---

## Consequences

- Four apps, Chat, Agents, Files and Connectors carry a hue in the Dock,
  Launcher and agent-row chips. Every other surface is unchanged.
- The Files spine gains a two-zone reading (authored vs arrived) and loses a
  dead code path.
- `file-cog` gains a glyph. It had none, so a **loose machine file** rendered
  with the generic **folder** glyph — a file drawn as a folder, in the one
  disclosure where that distinction is the point.
- Six lucide imports leave `WorkspaceTree.tsx` with the ladder.
- A skin swap still cannot repaint these hues. They are Tailwind palette
  classes, like `studioShapes` and `FileIcon` before them. If the design-system
  contract should reach the chrome's accents, that is its own ADR — widening
  `maps:` to cover them, not scattering more literals first.

### Gate

`api/test_adr641_icon_accents.py` — 23 checks, four falsifiers driven:

| Falsifier | Result |
|---|---|
| accent row for an undeclared surface | FAIL (phantom named) |
| a registered app with no accent | FAIL (the ADDITION direction) |
| re-add a path-string arm to `folderIcon` | FAIL ×2 |
| Dock paints the accent unconditionally | FAIL |

⭐ **A parity check is worthless until the registry is actually loaded.** The
app-direction check first passed **vacuously over one app while claiming to
cover four**: apps register by import side-effect (ADR-562), and without
`import services.apps` the `all_apps()` call returned `{'slides'}` alone. It
went green when an app's accent was deleted. Caught only by running the
falsifier — the gate now asserts `len(app_slugs) >= 4` before comparing.

⭐ **A gate that greps prose goes red on its own documentation.** The
reserved-family check matched the word "amber" **in the comment explaining why
amber is reserved**, and stayed red after the last amber value was gone. It now
parses the `slug: 'text-<hue>'` rows and ignores comments — assert the ROW,
never the prose around it. (Same defect as
`feedback_a_gate_check_that_matches_its_own_documentation`.)

### Driven

Rendered through a temporary harness mounting the real registries, screenshotted
in **both themes**, harness deleted. That pass is what produced D5: the gates
were green on a Files spine that read as a rainbow, because no assertion can
tell you eleven hues in a column distinguish nothing. ⭐ **A colour decision has
to be looked at; a green gate is not a look.**

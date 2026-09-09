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

---

# Amendment — the face fallback carries the class accent (2026-09-08)

**Status**: Accepted. Amends D3/D4; the 2026-07-16 face ruling is UNTOUCHED.

## What the operator observed

*"Check that the icons are consistently applied across the service — the chat
surface in full, and in-app chat surfaces as well, even chat message bubbles."*

Driven on production, they were not. The Dock, the Launcher, the Agents page,
the Slides breadcrumb and the app chips were all correct. But **Designer
rendered a grey "D" in the Slides chat pane while the same agent wore violet
two surfaces away on Agents** — and the same grey initials led every row of the
chat list, every message bubble, the header face stack and the mention menu.

**The gate was green at 23/23 the entire time.** It asserted the two registries
agree; nothing asserted that the chat surfaces consult them at all. This is the
ADR's own ⭐ recurring one section down: *a colour decision has to be looked at;
a green gate is not a look.*

## Why the original exemption was right, and where it stopped being right

D4 exempted the face deliberately, drawing the line at *"a glyph is not a
face"*: a face is an uploaded PICTURE (the 2026-07-16 ruling), and per-agent
colour swatches were shipped once, judged debt, and deleted.

That holds. What it did not cover is the **initial fallback**, which is neither
a picture nor a mark — it was the one element in the shell that NAMED a
principal while saying nothing about their class. That is the ADR-258 fault
(colour disagreeing with itself across surfaces), not the ADR-641 one the face
was exempted for.

## Decision

**A1 — the fallback carries the class accent; the picture never does.**
`faceAccent(kind)` in `attribution.ts`, beside `authorAccent` and drawing on
its hues: **agent violet, member teal, you neutral**. A member who sees a violet
dot beside an agent-authored file in Files now meets the same violet on that
agent's face in chat. One vocabulary, three renderings — dot, glyph, face.

`you` is deliberately NEUTRAL: you are the fixed point, not a participant to
tell apart, and the D3 reserve (red/amber mean *something is wrong*) holds.

**A2 — ⭐ `kind` is a REQUIRED prop, and that is the whole fix.**
The cause was never CSS. `AgentFace` took `name` + `avatarUrl` — both display
STRINGS — so all five call sites threw away a `member_kind` they **already
held**, and no styling inside the component could have coloured the fallback
correctly because *the information never arrived*.

So the accent is not the durable part; the **contract** is. A required `kind`
means a new chat surface cannot compile without answering *"who is this?"* — the
question the accent depends on. No `?`, no default: an optional `kind` with an
`?? 'human'` fallback would restore the exact silence this deletes (ADR-633's
"REQUIRED: no `?`, no default"; ADR-592's `stage`, inert for five days because
it back-derived itself).

**A3 — a hand-rolled initial disc is a second home, and is deleted.**
`ConversationDetail`'s invite list drew its own grey circle for people while
calling `AgentFace` for agents one branch below — so the two could drift apart
unnoticed, which is precisely how the first drift happened. Both now resolve
through the one component.

**A4 — `SurfacePage.tsx` is DELETED.** It resolved a glyph and hard-coded it
`text-muted-foreground`, bypassing the accent — and had **zero render sites**.
Its only mention was a stale comment describing a `/queue` surface ADR-642
absorbed. Dead code that would have read as a real inconsistency to the next
reader (the ADR-641 D5 lesson: the dead code was the colourful code).

## Consequences

- Faces are accented in all five chat surfaces: the chat list, the message
  bubbles (in-app panes included), the header stack, the participants drill-in
  and the mention menu.
- `PrincipalKind` is deliberately NARROWER than `authorClass`: agent | human |
  you, mapping 1:1 onto the `member_kind` the cast already serves. A face that
  had to guess `mcp` vs `agent` would be inventing, not reading. Widening is
  additive.
- `faceAccent` returns ground AND ink as one string. A caller that must pair
  `bg-violet-500/10` with `text-violet-600` itself is a caller that can forget,
  and violet-on-violet is how that reads.

### Gate

`test_adr641_icon_accents.py` §7 — 46 checks total (was 23). Three falsifiers
driven, each red:

| Falsifier | Result |
|---|---|
| make `kind` optional (`kind?:`) | FAIL ×2 |
| a call site drops `kind` (LanePanel) | FAIL |
| re-add a hand-rolled initial disc | FAIL |

⭐ The sweep asserts BOTH directions (ADR-636 §9): every `<AgentFace>` names a
kind (catches a deletion), AND no chat surface hand-rolls a rounded initial
outside it (catches an ADDITION — the check tsc cannot make).

### Driven

Rendered through a temporary harness mounting the real `AgentFace` at all three
sizes and both stacked, screenshotted in **both themes**, harness deleted — the
same method that produced D5. The look is what confirmed the tinted-ground pair
reads as quiet identity rather than a second rainbow, and that the `dark:` ink
variants earn their place.

---

# Amendment 2 — an agent has a REAL face (2026-09-08)

**Status**: Accepted. Completes the 2026-07-16 ruling rather than eroding it.

## What the operator observed

*"I'm seeing letters and not their actual icons?"* — and, on the options:
*"my opinion is that the long standing, future proof resolution and
implementation is actually real avatars."*

Agreed, and for a stronger reason than looks. Amendment 1 made the fallback
**correct**; it did not make it **rare**. The three options on the table were
(1) render the craft glyph in chat, (2) ship real faces, (3) leave it. Only (2)
honors the ruling: (1) quietly redefines a face as a glyph — the exact line D4
drew — and (3) leaves the ruling true on paper and dead in practice.

## The finding underneath the question

`AgentFace.tsx` was built for the ruling and shipped with the whole URL chain
wired — manifest path → registry `content_url` → signed URL exchange. And
**nothing ever supplied a picture.** `avatar_url` appeared in exactly two FE
type declarations and **nowhere in the backend**: not in `agents_registry`, not
in a route, not in a payload. Every agent fell to its initial forever.

⭐ **A field declared on one side of a boundary and never populated on the other
is not a feature; it is a shape that looks like one.** It survived four months
because the fallback is legible: letters look deliberate.

## Decision

**A5 — yarnnn's kernel agents ship WITH faces, as code.**
`api/services/agent_faces/{slug}.png`, versioned and deployed, beside the
`_generate.py` that makes them from **Lucide's own path geometry** — the same
glyphs the Agents page renders, so a face and its roster mark cannot drift.
A hand-drawn asset nobody can reproduce ossifies at the first palette change.
(The generator is pure-Python — pillow + svgpathtools. The first cut used
cairosvg, which needs a native libcairo the API image does not carry: an asset
regenerable only on a machine with a system library stops being regenerable.)

**A6 — a face is a FILE IN THE COMMONS, not a bundled static asset.**
A face served from `/static/` would be invisible to the substrate: unreadable
by a lane, unlistable in Files, unreachable by a connected principal,
unattributable, unreplaceable. Everything a principal can SEE here is a file
(ADR-209), so faces land as ordinary `write_revision` rows on the binary lane
(ADR-427's CAS seam).

**A7 — it MIRRORS, exactly as ADR-630's skills do.** Seeding at genesis would
freeze each workspace on the face it was born with, so a re-drawn glyph would
reach new workspaces and never old ones. Manifest-cheap, sha-compared,
idempotent, on the same scheduler tick.

**A8 — ⭐ THE MEMBER'S FACE WINS, and that is the point.**
`agents/{slug}/face.png` (the member's own, in the agent's home — ADR-624's
freely-writable half) outranks `system/agents/{slug}/face.png` (ours, locked).
The two are different files and **the lookup order is the entire policy**.
*"An agent you HIRED having a face you CHOSE"* is the ruling; this is what
makes choosing possible, and the mirror can never fight it.

**A9 — `AgentMark` is the ONE component answering "how does this agent
appear?"** The disc wrapping `<AgentIcon/>` was spelled **four times** across
the Agents detail, the Agents roster, the offered list and the new-chat door —
four places a face would have had to be added, and four places a fifth could
quietly render only the glyph. `AgentFace` is deliberately NOT reused: it falls
back to an INITIAL, which is right in a conversation (a letter reads as a
speaker) and wrong on a roster (the craft glyph says more than "B").

## Consequences

- Faces reach the chat list, the bubbles, the header stack, the mention menu,
  the Agents page and the new-chat door. The accented initial from Amendment 1
  remains the fallback — for people, and for any agent without a picture.
- `PrincipalKind`'s violet stays the CLASS marker; a face is per-agent, which
  is why per-agent colour is legitimate there and nowhere else.

### ⚠️ The bug the driven pass caught

`_read_manifest` queried the workspace-**relative** path while rows are stored
**absolute** (`/workspace/…`), so the version check never matched: the mirror
reported `written: 3` on every run and would have rewritten all three faces
**on every scheduler tick, forever**, minting a fresh revision each time.

⭐ **It was invisible to inspection because the faces were present and
correct.** Only re-running the mirror and watching `written` fail to fall to 0
exposed it. A mirror's correctness is not "the files are right"; it is "the
second run does nothing."

### Gate

`test_adr641_icon_accents.py` §8 — **66 checks total** (was 46). Three
falsifiers driven, each red: kernel outranks member (the ruling inverted) ·
a face missing for one agent · the scheduler stops mirroring.

⭐ The gate asserts the **supply**, not the pixels: that a face exists for every
registered agent (both directions — a new agent with no face is the
regression), that something SERVES it, batched, and that the member's upload
outranks ours. Two of its own checks were WRONG on the first run and went red
against correct code — the rank regex missed an f-string wrapper, and the
disc sweep banned every `rounded-full bg-muted`, flagging an **engine** brand
disc that correctly stays neutral by ADR-431. ⭐ *A gate that bans a shape must
name the shape it means.*

### Driven

On production data, against three real workspaces: mirror wrote 3 faces each,
second run `skipped: True` (after the path fix), every served URL fetched and
**sha-matched the shipped bytes**, and a member-uploaded face was shown to
override the kernel's and then be cleaned up. The faces themselves were
**looked at** at 512/56/36/24px on light and dark grounds — which is what
caught the palette's wells rendering as sub-pixel specks at `r=.5` (Lucide's
own value) and nudged them to `.9`.

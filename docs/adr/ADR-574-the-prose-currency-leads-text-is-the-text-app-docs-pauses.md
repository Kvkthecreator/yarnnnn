# ADR-574 — The prose currency leads: Text is the text app, Docs pauses

> **Status**: **Accepted + Implemented** (2026-08-17, operator-ratified through the
> service-philosophy discourse — *"the docs APP should be sunset and hidden, and now
> officially paused… instead, make the text APP the main text-based premise… the more
> AI native and interoperable between multiple LLM chats like chatgpt and claude and
> gemini, is ultimately more accommodative with the text apps given the file format and
> overall data handling."*). The measurement half was resolved by the operator in the
> same exchange: **the live `document` artifacts are 100% test data** — *"the usage
> numbers are 100% tests so should not influence our approach"* — which retires
> ADR-518 D5's unveil evidence rather than contradicting it.
> **Date**: 2026-08-17
> **Dimension**: **Channel** (Axiom 6 — what the operator is shown at rest, and which
> app owns the text premise). **No Substrate, Identity, or Mechanism change**: no
> schema, no migration, no write-door change, no format change, nothing deleted.
> **Relates to**: **ADR-488** (the template this re-runs verbatim — IMAGES went
> `primary` → `search-only`, "hidden, not unplugged", with a written re-unveil
> checklist), **ADR-456 D1/D6** (the markdown ruling + the Wave-4 interchange bridge
> that was never built — the load-bearing evidence), **ADR-518** (the Docs/Studio
> carve, whose D5 unveil this pauses and whose D1–D4/D6/D7 stand untouched),
> **ADR-571/572** (the Text app and its depth), **ADR-507 D1** (the acts are open —
> the growth rule, run in reverse), **ADR-310/311** (two doors, one moat — the door
> the measurement is taken at), **ADR-473** (type→app routing — the reason hidden ≠
> unplugged), **ADR-486 D7** (registration is not unveil).
> **Amends**: ADR-518 D5 (the unveil), ADR-507 D1's Make row, GLOSSARY §Make,
> ESSENCE §The Desk.

---

## 1. Context — the question the operator asked

The operator asked for a conceptual audit rather than a feature: *does the Docs app
still earn its place, given that the Text app now exists and given what the interop
face actually is?* The thesis offered was that **the prose currency (`.md`) is the more
AI-native and interoperable one**, that Text should therefore become the main
text-based premise, and that any future HTML-native surface should be reconsidered
from scratch as a **publishing** surface rather than as a better word processor.

The audit ran against canon and the live tree. It returned a stronger form of the
thesis than the one offered, and the strongest evidence was not the one the thesis led
with.

## 2. What the evidence said

### 2a. The bridge that justified HTML-as-sole-source was never built

ADR-456 D1 (2026-07-14) ruled: *"HTML stays the sole canonical source for Studio
artifacts. Markdown is an interchange projection, never a second source format."* That
ruling was made safe by an explicit condition stated in the same decision:

> `.md` is the substrate's prose currency; `.html` is the Studio's authored-artifact
> currency. **The bridge is projection both ways.**

The bridge is **Wave 4** (ADR-456 D6): md import + html→md export, marked
*demand-gated*, and **sequenced "with the publish arc it belongs to."** Waves 1, 2 and
3 all shipped same-day, each with its own gate (`test_adr456_studio_wave1/2/3.py`).
**Wave 4 is the only wave that never landed**, and ADR-570 re-confirmed the deferral a
month later (*"No conversion. md→html up-projection stays ADR-456 Wave 4,
demand-gated"*).

So the two-currency OS has been running on one currency's terms for a month, with no
way back across.

### 2b. Measured: a Docs artifact is not merely degraded through the second door — it is invisible

This is the finding that decided the ADR. It was **measured by driving the real code
path**, not read off source.

A blank `document` artifact, built by the shipped `build_skeleton("document", …)`:

```
stored artifact chars : 26,482
kernel style element  : 24,008        (compose_kernel_style_element())
STUDIO_KERNEL_CSS     : 23,953
_SHARED_CSS           :  1,722
OPEN_CONTENT_CAP      : 24,000        (services/mcp_composition.py:583)
```

`compose_kernel_style_element()` inlines the kernel CSS into **every stored artifact's
`<head>`**, ahead of the body (`services/authoring.py`), and re-asserts it on every
write (`ensure_kernel_style_in_html`). The style element **alone exceeds the MCP read
cap by 8 characters**, before `_SHARED_CSS`, before the layout skin, before the
doctype, before one authored word.

Driven through the cap:

```
truncated at cap?      : True
</style> in first 24k? : True
<body>  in first 24k?  : False        <-- the body is never reached
```

**An external LLM calling `open` on a Docs artifact receives ~24KB of CSS and zero
authored content.** The last thing it sees is a CSS comment about a slide-clipping
defect. And `open` returns `success: true, found: true` — so neither the model nor the
member is ever told.

**This is an incorrect success**: the failure class the record cannot see, and the same
shape as the connector-workspace defect closed at `e0fa233` last week (writes landing
in the wrong commons, *succeeding, with a revision id, invisible*). Sentry is blind to
it by construction.

Three effects compound it, all verified:

- **The semantic index is polluted.** FTS indexes `to_tsvector('english', wf.content)`
  over raw content, and `get_embedding` takes the string unsanitized. Studio artifacts
  live under `operation/`, which is in `_EMBED_ELIGIBLE_ROOTS` — so an artifact's
  embedding vector is dominated by stylesheet tokens and competes against genuine `.md`
  prose in the same index.
- **`save` is guarded off.** `compose_save` refuses whole-file overwrite above
  `OPEN_CONTENT_CAP` without `confirm_full_replace`. The guard is correct; it simply
  fires on 100% of artifacts.
- **`edit` is the only viable write, and it is a trap.** It anchors on raw HTML
  (`data-block-id`) inside a document the model could never fully read — and cited
  content (tables, charts, images) is stored as **empty** `data-ref` elements resolved
  **client-side only** (`projection.ts`). Even a completed Wave-4 exporter would return
  empty containers without a server-side projection.

**The interop face is entirely format-blind** — there is not one `.html`/`.md` branch
in `api/mcp_server/` or `services/mcp_composition.py`. It is a byte pipe. That is not
neutrality in effect: it means one currency passes through whole and the other passes
through as nothing.

### 2c. The machinery already treats markdown as the authoring currency

`services/derive_recipes.py` targets `.md` for prose outputs (*"One markdown brief in a
meaning-folder, citing the source"*, *"One PRD markdown file…"*); `compose/engine.py`
runs **markdown → HTML**. The system's own generative layer authors in markdown and
treats HTML as a projection at the boundary — exactly ADR-456 D1's shape, except that
D1 assigned **the member's** authoring to the HTML side. The machinery and the member's
app assignment point in opposite directions.

### 2d. Two adjacent document apps ship pinned, with no bridge between them

The Dock as shipped: `chat · docs · text · studio · radar · strings · files · agents`.
**Docs and Text sit side by side, both `primary`, both `default_pinned`** — one over
HTML, one over markdown, with no conversion in either direction. A new member meets
both on first login with no way to tell which one their writing belongs in, and no way
to move it if they guess wrong.

The defect is not that Docs is bad. **It is that the pair is incoherent** — and
incoherence at the Dock is a Channel-dimension defect, which is the dimension ADR-488
operated on.

### 2e. The usage evidence, resolved honestly

ADR-518 D5 unveiled Docs in full on a measurement: *"9 of 18 live artifacts, and the
only ones with real authored substance."* This ADR does **not** claim that number
inverted. The operator resolved it directly: **the live artifacts are 100% test data.**
The D5 count was a count of the operator's own probes, so no member work is stranded by
the pause, and no adoption verdict is claimed in either direction.

Recorded in the ADR-507 D3 discipline: **an instrument that never measured member
behaviour cannot be cited as if it had.** D5's evidence is retired as inapplicable, not
refuted.

## 3. Decisions

### D1 — Text is the text-based premise; Docs is no longer "the writing app"

The prose currency leads. **Text** (`.md`/`.markdown`/`.txt`, ADR-571 D2) is the app the
product names for text, in canon and on every operator-facing surface. Docs remains a
live, registered, working app — it is simply no longer the app the product leads with,
and no canon sentence may call it "the writing app."

Rationale, stated so it is not re-litigated from taste: the text premise belongs to the
currency that **passes through both doors**. Text's `.md` is authored through the
member door, read whole through MCP, indexed as prose, and round-trips safely. That is
the moat's own portability wedge (ESSENCE: *"reachable from any LLM"*), and it is not a
preference between two editors — it is the difference between a currency that reaches
the second door and one that does not.

ADR-518 D1's carve **stands**: Docs owns `document`, Studio owns `deck` · `web`. This
ADR changes which app the product *leads* with, not which app owns which type.

### D2 — Docs pauses: `primary` → `search-only`, and it leaves the default Dock

Verbatim ADR-488 D1's shape — **hidden, not unplugged**:

- `kernel_surfaces.py` docs row: `launcher_tier: "primary"` → `"search-only"`,
  `default_pinned: True` → `False`. **Both fields move together**, because
  `test_adr297_phase1.py` gates `default_pinned == the primary tier` as a set — a
  half-flip is a gate failure by design.
- `DEFAULT_KEPT_SURFACES` drops `'docs'`, carried by **one new dock-reseed
  generation** whose `previous` is the current default. The ladder's rule is unchanged
  and is the reason this is safe: a stored Dock is rewritten **only when byte-equal to
  the prior seeded default**. An operator who curated even one icon — including a
  deliberate Docs pin — is never overwritten.

**Everything else stands**: the route `/docs`, the `SurfaceRegistry` row, the
`APP_SURFACES` row, `services/apps/docs.py` and its `register_layouts` /
`register_app("docs", resident="designer", name="Writer")`, the `document` layout row,
the flow editor, the gates. The app is findable by flat search — the internal-access
path, exactly as Radar's and IMAGES' pre-unveil states were.

**A `document` artifact still opens into `/docs`** via ADR-473 type→app routing.
Nothing is stranded and nothing needs migrating.

### D3 — Removal is explicitly NOT taken, and the trap is recorded

The audit found a real edge that argues for pausing rather than removing, recorded here
so a future session does not rediscover it as novel:

`resolveSurfaceApplication` (`web/lib/file-types/index.ts`) resolves an `.html`
artifact's app and falls back `?? DEFAULT_ARTIFACT_APP`, which is `'studio'`. **Removing
`APP_SURFACES.docs` while leaving the `document` layout row would silently route every
document into Studio's `paged` mode** — a flow document rendered as slides, with no
error. The two must only ever be removed together, and this ADR removes neither.

Second reason, equally load-bearing: **Docs is the sole consumer of the flow stack.**
`document` is the only layout with `"mode": "flow"`; `FlowEditor.tsx` +
`web/lib/authoring/flow/*` (~52KB) is mounted nowhere else, and **Text does not share
it** (Text has its own `ProseCanvas`). Pausing mothballs the system's only flow editor
under live gates; deleting would discard it. ADR-488 D4's discipline applies directly —
the gates stay in force so a hidden app cannot silently drift while the shared kernel
evolves under it.

### D4 — The reopening condition: an outbound Publish surface, never a better word processor

Docs reopens for **one** reason: an HTML-native **publishing** surface — a Publish/blog
app that carves the `web` type out of Studio, consolidates the document canvas, and
earns its housing with capability the system does not have today (connected-account
posting, social distribution automation, published-page management).

This is **named as a condition, not designed here.** ADR-518 §6 already left the carve
open (*"if web later earns Wix-grain divergence, it carves from Studio the same way —
the third run of a now twice-proven pattern"*), and ADR-456 D6 already filed md
interchange as belonging **"with the publish arc."** Those two clauses and this one
describe the same future app; whoever builds it writes its own ADR.

**What is refused, permanently, is the other reopening story**: "a more HTML-native
document editor / word processor." `docs/analysis/the-commons-is-the-os-2026-07-09.md`
§4 names that as the trap (*"this is how every workspace company dies"*), and ADR-518
§2 gives the test — **does the app's value come from yarnnn having BUILT it, or from
yarnnn having HOUSED it?** Publishing is housed value: it needs the attributed record,
the grants, the provenance chain, connected accounts. A better word processor is built
value, competing on interaction feel with very deep incumbents forever.

**A prerequisite the future app inherits, stated now**: any HTML-native surface must
ship a **server-side projection** resolving `data-ref` citations, or it inherits §2b's
invisibility through the second door. Wave 4 alone does not fix this — an exporter over
unresolved `data-ref` elements returns empty containers.

### D5 — The growth rule, run in reverse

ADR-507 D1 established that a new **app** is a row under an existing act and needs no
ADR, while a new **act** needs one. This ADR records the symmetric case: **un-leading an
app is a Channel decision that needs an ADR**, because it changes what the product
names at rest — even though, mechanically, it is two registry fields and a dock
generation.

The Make act's app list becomes: **`text`** (the prose premise) · `studio` · `docs`
(paused) · `images` (internal, ADR-488). Text is named first because D1 makes it the
lead, not because the list is ordered by tier.

## 4. What this ADR explicitly does NOT do

- Does **not** delete or deprecate any code, gate, or canon. Singular-implementation
  cuts the other way here, exactly as in ADR-488 §4: the app is one implementation,
  merely unpromoted.
- Does **not** revisit ADR-518's carve (D1–D4, D6, D7 stand — Docs still owns
  `document`; the machinery stays singular with three consumers).
- Does **not** build Wave 4, design the Publish app, or change any format, write door,
  schema or migration.
- Does **not** create a "paused apps" mechanism. `search-only` already is that
  mechanism (ADR-340 D5; exercised by Radar pre-unveil, the dormant `setup`/`program`
  rows, and IMAGES).
- Does **not** claim an adoption verdict on Docs. §2e records why none is available.
- Does **not** fix §2b's invisibility. It is recorded as a **standing defect** with a
  named cheapest repair (strip `<style data-kernel>` on the MCP read path — already
  regex-addressable via `_KERNEL_ELEMENT_RX`), owed against whoever next touches the
  artifact read path. Pausing Docs reduces its blast radius; it does not repair it, and
  Studio's `deck`/`web` artifacts still carry it.

> **RESOLVED 2026-08-28 — §2b is CLOSED.** The repair named here was taken, by the
> session that next touched the artifact read path. Two changes, both in
> `compose_open`:
>
> 1. **The marked stylesheets are elided on read.** `elide_presentation_css()` lives in
>    `services/machine_projection.py` — the ADR-530/DP34 "one seam" for what a machine
>    may read — NOT in a new module. It removes only `data-kernel` / `data-skin`, which
>    are machine-composed and re-stamped on every write and so cannot hold an authored
>    byte; the **unmarked layout `<style>` survives**, because it is baked once at
>    `build_skeleton` and never retrofitted, making it the one sheet that could carry a
>    per-artifact edit. It is a READ-path act only — reaching a write door would
>    silently undo the ADR-453 D2 retrofit contract.
> 2. **`open` gained the continuation `list` has had since ADR-545 D3** (`offset` /
>    `next_offset` / `content_chars`). This was the deeper half: the cap's own comment
>    claimed "history/search stay available for the rest", and **they do not** —
>    `search` returns a short excerpt and points back at `open`, and `history` carries
>    revision messages, not body text. A file past the cap had no path to its own tail.
>
> Measured on the live artifact that surfaced it (`operation/yarrnnnn-decl/deck.html`):
> 48,323 chars, first slide markup at 39,118 — **15,118 past the 24,000 cap**, so an
> `open` returned CSS and zero authored content under `success: true, found: true`.
> After elision the whole deck is 14,609 chars: **all 9 slides in a single page.**
> Across the workspace the kernel sheet was **72.7% of all artifact bytes** (18 of 19
> HTML artifacts, ~20,380 bytes each).
>
> Not done, deliberately: **the sheet is still inlined per artifact.** De-duplicating it
> would break self-containment and the versioned in-place retrofit (`data-kernel-v`)
> that ADR-453 D2 depends on — the storage cost is the price of an artifact that is one
> portable file. Elision is a read-path concern and stays there.
>
> Receipt: `test_adr512_open_verb.py` §6 (9 rows, driven against a real-shaped
> artifact; 8 falsified red against the pre-fix code). §5 of this ADR's own gate is
> inverted — it proved the defect, it now proves the repair.

## 5. Reopening checklist (the ADR-488 §3 pattern)

Re-unveiling Docs — or superseding it with Publish — is a **deliberate decision
recorded against this ADR**, not a flag flip:

1. The D4 condition is met: an outbound publishing capability exists, or its ADR is
   ratified with the `web` carve.
2. The §2b prerequisite is met: a server-side projection resolves `data-ref` citations.
   (The second half — an artifact `open` returning authored content rather than CSS —
   is **met as of 2026-08-28**; see §4.)
3. Registry: `search-only` → `primary`, `default_pinned` → `True`.
4. `DEFAULT_KEPT_SURFACES` re-adds the app **plus a new reseed generation** whose
   `previous` is the then-current default — the D2 ladder pattern.
5. `test_adr574_prose_currency.py` §2 is updated in the same commit (it pins the
   *paused* state and will correctly fail on a half-unveil).
6. Public docs re-list the app.

## 6. Consequences

**Positive.** The Dock stops shipping two adjacent document apps with no bridge between
them. The app the product leads with for text is the one whose currency reaches both
doors — the portability wedge is honest at the surface, not just in the moat statement.
The flow editor is mothballed under live gates rather than discarded. The Publish
question stays open with a *motive* attached, rather than as a taste observation.

**Costs, stated.** The flow editor — the system's only one — is unadvertised work that
now accrues no traffic. The §2b artifact invisibility was unrepaired at ratification and
still affected Studio; it is **closed as of 2026-08-28** (see §4). `document` remains a type with no leading app, which is a slightly odd shape and
is the honest cost of pausing rather than removing.

**Reversibility.** Total. Two registry fields, one dock generation, one gate section.
Nothing is deleted; §5 is the path back.

## 7. Key files

`api/services/kernel_surfaces.py` (the docs row — tier + pin) ·
`web/lib/shell/surface-preferences.ts` (`DEFAULT_KEPT_SURFACES` + the 2026-08-17 reseed
generation) · `api/test_adr574_prose_currency.py` (**new** — the paused-state gate) ·
`api/test_adr518_docs_app.py` (§4 re-pinned to the paused state) ·
`web/scripts/gates/adr546_rung_law.mjs` (stale path repaired: `api/services/docs.py` →
`api/services/apps/docs.py` — broken before this ADR, independent of it) ·
`docs/ESSENCE.md` (v20 — §The Desk) · `docs/architecture/GLOSSARY.md` (§Make) ·
`docs/architecture/ADR-LEDGER.md` · ADR-456 / ADR-518 / ADR-571 amendment banners.

## 8. The one-line statement

**The text premise belongs to the currency that reaches both doors: Text leads, Docs
pauses intact behind a search-only door, and the HTML canvas reopens only as a
publishing surface — never as a better word processor.**

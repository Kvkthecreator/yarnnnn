# ADR-595: Strings is the tending surface — the pane shows the situation, never the contents

> **Status**: **Accepted** (2026-08-22, operator-ratified — "yes, aligned in full
> … delegate implementation details"; the design discourse is the 2026-08-21/22
> Strings-audit thread: "the dedicated center pane actually doesn't show the
> actual contents … but the surrounding information, setup, and alike", and
> "management and display of sources in — the N to 1 relational aspects —
> should also be first class … recommend tab-based structure"). **BUILT** with
> this ratification.
> **Date**: 2026-08-22
> **Dimension (Axiom 0)**: **Channel** (what the desk renders) primary;
> **Substrate** (what the view serves) secondary.
> **Amends**: ADR-569 **D7's center-pane architecture** (the five stacked
> zones, and zone 1's "the FILE is the canvas"). The rest of D7 — creation
> doors, direct switches, conversational management, loud states — stands.
> **Relates to**: ADR-590 (the rendered face is the editing surface — in
> Text/Files, which is WHY Strings must not own a second one), ADR-572 D10
> (two hand-maintained faces drift), ADR-594 (reach with a receipt — the
> receipts this surface now shows), ADR-486 D2/D5 (subject-first;
> derived-never-stored), ADR-567 (the desk pattern, unchanged).

---

## 1. Context

ADR-569 D7 made the maintained file the desk's canvas: zone 1 rendered the
document (a private CSV table, a markdown branch, a `<pre>`), with the
machinery stacked beneath as four co-equal cards. Two structural problems,
surfaced by the 2026-08-21 audit and the operator's re-cut:

1. **The canvas was a second file face.** The OS owns exactly one reading
   face (`readingFace.ts` / the shared viewer) and one editing face (Text,
   ADR-590). Strings' private renderers were the drift ADR-572 D10 names.
2. **Sources were config lines, not parties.** A string is an N→1 relation —
   N declared sources feeding 1 maintained leaf — and after ADR-594 each
   source has live standing (inside/outside the connection's aperture),
   receipts (landed snapshots), and a contribution history (revisions citing
   its raws). The flat "Setup" card flattened all of it.

The operator's vision, ratified here: **the dedicated center pane does not
render the document; it shows the surrounding information — currency,
provenance, governance, audience — and hands the member a door to the file
itself.** Reading and correcting happen in the file's own homes.

## 2. Decisions

### D1 — The law: the pane never renders the maintained file's contents

Enforced at the API, not by FE convention: **the desk view stops serving the
head's content** (`StringView.content` is deleted). The view carries head
FACTS instead — `head_updated_at`, `head_lines`, `head_bytes` — enough for
the glance ("is it current, how big, when did it move"), not the document.
The private renderers (`FileCanvas`, the CSV table, the markdown/`<pre>`
branches) are deleted with it. Reading = the file's own surface (the Open
door, routed through Files); correcting = editing the file there or telling
Keeper — the pane says so instead of hosting a lesser copy.

### D2 — Four tabs, derived from the four kinds of surrounding information

`Overview · Sources · Activity · Contract`, as a remembered `tab` param on
the existing desk housing. Loud states (unparseable declaration, problem,
refused write) render ABOVE the tabs — a repair is never hidden behind a tab.

- **Overview** — the glance: the status card (file facts + currency +
  staleness + the Open door) and the **N→1 flow strip** (source chips →
  the file → cited-by), plus the consumers list.
- **Sources** — D3.
- **Activity** — the existing attributed rail (runs · corrections ·
  repairs · restore), full height.
- **Contract** — the charter rendered as prose, with shape and cadence
  beside it: the terms under which the N feed the 1.

### D3 — Sources are first-class parties, at three grains

Each source card shows: **identity** (connector slice or HTTP pull),
**standing** (for connector sources, whether the selector is inside the
connection's aperture — the ADR-594 intersection law made visible instead of
failing as a generic empty), **receipts** (the newest landed snapshot, as an
openable file), and **contribution** (when this source last moved the leaf —
the N→1 edge at revision grain). Management stays conversational (ADR-567
D3's one-gesture law) with **precise seeds carrying the source id**, and the
format's arity law stated in the pane (structured = exactly one feed; prose
weaves up to twelve), not discovered by refusal.

The view composes this per source, derived-never-stored (ADR-486 D5):
`last_landed_at` / `last_landed_path` (newest file under the source's
deterministic receipt prefix — `inbound/{platform}/{selector}/` per ADR-594
D1, `inbound/web/{slug}/` for HTTP), `in_aperture` (a `selected_sources`
check), `last_contributed_at` (newest leaf revision whose `derived_from`
cites that prefix). Nothing new is stored; every fact is a read over the
ledger and the fixed grammar. The roster list (`GET /strings`) stays light —
enrichment rides the desk view only.

### D4 — Setup is first-class (2026-08-23 amendment, operator-directed)

The first click-pass found the unconfigured pane was a placard pointing at a
side conversation — it *described* setup without *carrying* it ("this current
surfacing has no implication to do so"). Re-cut: **the unconfigured pane IS
the setup surface.** The string's anatomy renders as four numbered slots —
the file (the one direct gesture, ADR-567 D3 unchanged) · the contract · the
sources · the cadence — each act a precise seed into Keeper's lane. Slots
fill live as the files land (the contract slot renders CONTRACT.md the
moment Keeper writes it — the substrate is the state machine), and the desk
promotes to the tabs when the declaration parses.

The sources slot surfaces **the aperture at designation**: the selected
slices across the member's connections render as chips whose click seeds
"pull from this slice" with the selector id — so a connector source is
composed from what the connection may already read, instead of being guessed
in prose and failing later as out-of-selection. Authorship stays
conversational throughout — the slots sharpen the seeds; they are not a
form.

### D4 amended — one surface, not two (2026-08-28, operator-directed)

> **D4's diagnosis stands; its remedy is superseded.** The placard genuinely was a placard, the anatomy genuinely is four things, and the aperture genuinely belongs at designation. What was wrong is that all of it went onto a **separate page**.

The operator, looking at both states side by side: *"the non-finished set-up screen difference is actually confusing... maybe just showing the actual as if completed information (and thus handling the empty states) is preferred."*

They were right, and the reason is structural. D4 produced **two pages for one object**: a numbered ladder for `unconfigured`, four tabs for `ready`. Sources and contract appeared in **both**, in different shapes and different places. So the declaration landing did not *fill* the desk — it **swapped** it, and things the member was looking at moved.

**The desk already knew how to render absence.** Every empty state the undeclared view needs was already built and simply unreachable behind a 404: *"No sources declared yet"*, *"No contract declared"*, *"no sources declared"* in the flow strip, *"No version yet"*, *"Nothing cites this file yet"*. The 404 was a policy choice, never a data limitation — every `StringSummary` field but `topic`/`declaration_path` already carries a safe empty default.

**And this surface already had the right pattern one state over.** A declaration that parses but cannot run (`problem`) and one whose last write was refused (`repair`) both arrive as a **normal view with a loud card layered above intact tabs**. `unconfigured` was the single state that substituted a different page instead of layering. The amendment puts it back under the rule the file already followed.

So:

- **`GET /strings/{topic}` serves the undeclared desk** rather than 404-ing, with `declared: false` and honest empties. A `target` query param carries a *designation-in-flight* — the leaf picked before anything was written, which only the client knows. It is read on the undeclared path only, so it can never re-point a live string, and a malformed value is dropped rather than refused (it is a URL param on a read).
- **`SetupPanel`, `SetupSlot`, and the `unconfigured` phase are DELETED**, not hidden. Keeping the ladder beside the tabs would leave two authorities on "is this set up?" — precisely the [ADR-532](ADR-532-the-access-pane-shows-the-grant-that-exists.md) §3a failure, where the honest state was bolted onto the editor built for the model it replaced (*"preserving the legacy approach while accommodating the discipline"*).
- **Each ask moves into the tab that owns it**, so nothing relocates when the declaration lands: the aperture chips into **Sources**, the contract seed into **Contract**, the cadence presets beside the `—` in the **cadence row**, the file pick into the Overview card when no leaf is designated. The one direct gesture (D4, ADR-567 D3) survives exactly where the thing it designates is shown.
- **Header controls are disabled-with-a-reason, never absent.** A control that appears from nowhere reads as a different page; a greyed one that says why is the same page, not yet ready. This reuses the disabled path `Run now` already had for `problem`.
- **A "not kept current yet" line** sits above the tabs naming what is still needed — the one thing the ladder carried that the tabs do not, collapsed to a phrase rather than a page.

**A defect the ladder had, worth recording**: slots ③ and ④ carried **no `done` flag at all**, so the checklist never ticked its last two boxes even when satisfied. It promised progress tracking it did not deliver — an argument against preserving its ordering, not for it.

**A capability this gains**: the aperture roster was fetched *only* in the unconfigured state, so a **declared** desk could never show "what else could I pull from". In Sources it now serves both.

Gate: `api/test_adr595_desk_is_one_surface.py` (19 assertions, falsified 10-red).

## 3. What this ADR does NOT do

- **No change to the string's mechanics** — declaration grammar, run body,
  confinement, metering are ADR-569/594's and untouched.
- **No workspace-global pane** (ADR-486 D2 holds; the rail of subjects is
  still the only roster).
- **No in-pane editing of sources/cadence/shape** — management stays
  conversational; the tabs sharpen the seeds, they do not add forms.
- **No new storage** — every enrichment is derived at read time.

## 4. Gates

`api/test_adr595_tending_surface.py` — the content law at the model
(`StringView` serves no `content`), the receipt-prefix derivation driven,
the enrichment fields present, the FE carries the four tabs and no private
file renderer (composition-anchored, comment-stripped). Existing
`test_adr569_strings.py` unchanged (mechanics). Each new check falsified.

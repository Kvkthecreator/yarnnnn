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

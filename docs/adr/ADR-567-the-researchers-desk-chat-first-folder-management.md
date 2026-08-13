# ADR-567: The Researcher's Desk — the watched folder is managed in conversation

> **Status**: **Accepted** (2026-08-13, operator-ratified — *"aligned. and agent name is
> Researcher. proceed"*, closing the folder-centering discourse that followed the ADR-565
> bridge). The third cut of the radar re-cut arc (ADR-564 frame → ADR-565 artifact → this
> ADR's surface + colleague).
> **Date**: 2026-08-13
> **Dimension**: **Channel** (the app's surface contract — a desk, not a form) + **Identity**
> (the colleague fronted; a lane fact added) primary; **Mechanism** (management runs through
> the lane's ordinary tools) secondary. No schema, no migration.
> **Amends**: **ADR-565** — D6 widens (the bound lane is layer 2's *authoring* surface,
> creation included, not only its revision surface); the form-based create flow is replaced
> (§D3). **ADR-467 D1 / ADR-558** — the bound-lane roster ("Studio · Docs · IMAGES pin a
> resident") gains radar as the fourth row, deliberately. **ADR-486** — the R1 wording
> ("watch-authoring path" as a form) is superseded at the product door; the REST routes
> survive as the programmatic door (§D5).
> **Preserves**: ADR-562 (the resident comes from the app's own registration —
> `register_app("radar", resident="scout")` is the fact this ADR fronts; no new declaration),
> ADR-460/558 (no authority on agents; the colleague never picks itself), ADR-384/564 layer 1
> (the folder choice stays the operator's unscriptable act — §D3's one direct gesture),
> ADR-254 (format-follows-consumer — the lane authors both file classes under their own
> rules), Axiom 1 (the substrate is the bus — Researcher manages by writing files; the kernel
> schedules by reading them), Axiom 4 (agents author trigger declarations, attributed).

---

## 1. Context — the framing, internalized the rest of the way

The ADR-565 bridge shipped the folder-centered *object model* (criterion + report + any-depth
attachment) under an app-centric *surface*: a "Topic" text field minting containers, a form
composing machine config, no folder identity anywhere the member looks. The operator's
correction (2026-08-13): the folder premise must be internalized into the app itself — and the
app should work the way Docs and Studio work: **a named colleague does the work, and you talk
to it.**

The complete model:

> **Researcher is a colleague who tends folders you point them at. The app is Researcher's
> desk: the center pane shows the folder under management — its setup restated from the
> files, its recent changes, its report — and the lane beside it is how the member and
> Researcher run the folder's lifecycle together.**

Everything needed already exists: `register_app("radar", resident="scout")` is live
(ADR-562), `create_lane(app=...)` resolves the resident server-side (D3), the lane knows what
the member is looking at (ADR-522 — radar already declares its focus), and lanes hold
`WriteFile`/`EditFile`. The app simply never created a lane.

## 2. Decisions

### D1 — Researcher is fronted as the app's colleague; the app's own name stays deferred

The member reads **Researcher** — in the lane panel (`speakerLabel`, the ADR-562 D5
machinery), in the desk's copy, in the revision messages the sweep already writes. This
resolves the ADR-565 D8 tension along the Studio↔Designer precedent: the app is named for the
medium, the colleague for the persona; fronting Researcher requires no app rename, and the
app-name question stays held for the maintainer-phase discourse.

### D2 — The desk: the center pane is the folder's lifecycle; the lane sits beside it

The fourth bound-lane app (the ADR-467 D1 roster amends to **Studio · Docs · IMAGES ·
radar**). The center pane reads *from the files*, so Researcher's edits and the member's land
in one view:

1. **What it manages** — the folder, presented as the folder (path-shaped identity; Files
   reachable but never the center of gravity — the desk is where the folder is managed).
2. **How** — the setup restated: the criterion card, the source portfolio, the cadence — each
   a projection of `CRITERION.md` / `_radar.yaml`. Layer 2 held up to the light, so drift
   between what the member meant and what is declared is visible. An unparseable declaration
   renders loudly, never as a silently dead hub.
3. **Recent changes** — the lifecycle rail: report revisions + sweep events (the ledger is
   the source, as in the ADR-486 D5 discipline).
4. **The report** — the living artifact (ADR-565 D1), unchanged.

Direct switches stay direct: Pause/Resume is a button. Not every gesture becomes chat.

### D3 — Creation is conversational, with exactly one direct gesture

The flow: **pick the folder** (a picker over the workspace tree — choose existing or name new;
the operator's act) → the desk opens in its *unconfigured* state with the bound lane → the
member tells Researcher what matters and where to look → **Researcher authors `CRITERION.md`
and `_radar.yaml`** through its ordinary tools, attributed, under the member's grant → the
scheduler discovers the declaration on its next tick and the standing loop begins.

The folder choice is deliberately NOT delegated: ADR-384's triple-check proved
meaning-grouping is the unscriptable operator-judgment act, and ADR-564 keys layer 1 on the
operator. Layers 2–3 are exactly where the colleague belongs — the criterion and portfolio are
revised by correction, and conversation is the correction medium.

**The form is replaced, not supplemented** (Singular Implementation). Management is the same
conversation, ongoing: add/prune sources, retune the cadence, tighten the criterion —
Researcher edits the files; the desk re-reads them.

**No new API exists or is needed**: the substrate is the bus (Axiom 1). Researcher writes the
declaration; `discover_radar_hubs` reads it on the drain tick, exactly as it reads an
operator-authored one. Axiom 4 already canonizes agents authoring trigger declarations with
their own attribution.

### D4 — A bound lane carries its binding app: `lane_meta["app"]`

The runner keys the job overlay on `artifact_path` alone today, which would hand a radar desk
lane **Studio's authoring posture**. Two non-fixes rejected: keying on the agent slug is a
coincidence, not a declaration (Docs and Studio share `designer` — the slug cannot name the
app); deriving from the document works for authoring apps (`data-template` in the HTML — the
ADR-562-era reasoning) but radar's artifact is plain markdown and carries no template, so for
this class the app is irreducibly a *lane* fact.

`create_lane` persists `app` into `lane_meta` for bound lanes; the turn dispatch threads it to
`build_lane_conventions`, which selects the job overlay: `app == "radar"` → the **desk
posture** (composed fresh per turn from the declaration + criterion + report — the grammar of
the two files, the setup flow, the management verbs, never-invent-sources, re-read after
writing machine config); otherwise the studio posture as today. Scope guard: `lane_meta.app`
selects the JOB only — never the resident (set at create from the registration), never the
engine, never display copy.

### D5 — The REST routes survive as the programmatic door

`POST/PATCH /api/radar/hubs` remain for programmatic callers (evals, MCP, scripts) and for
the direct switches (pause). The product door is the conversation. Stated so the two doors
are one product path plus one API — not a dual product path.

### D6 — Malformed machine config is a first-class legible state

An LLM authoring `_radar.yaml` will eventually write yaml that does not parse. The parse
already fails safe (hub skipped, logged); this D makes it *visible*: the desk's setup card
states plainly that the declaration is unparseable and the lane is the repair surface. The
desk posture teaches re-read-after-write for the machine file.

## 3. Cascade / blast radius

- **Backend**: `routes/lanes.py` (persist + expose `lane_meta["app"]`; thread to dispatch;
  re-point the app-registry docstring's dangling "ADR-564" cite to ADR-562);
  `services/lane_runner.py` (`app` param; posture branch); `services/radar.py`
  (`build_desk_posture` — reads declaration + criterion + report, composes the job overlay).
- **FE**: `RadarSurface.tsx` rewritten into the desk (folder picker attach flow, unconfigured
  state, setup cards, lifecycle rail, report, LanePanel mount with `speakerLabel` resolving
  Researcher); `web/lib/api/client.ts` (lanes.create `app` already typed; radar vocabulary).
- **Vocabulary**: operator-facing strings say *watched folder* / *Watch a folder*;
  "Researcher" names the colleague. "Hub" survives only in code/API identifiers (the ADR-539
  identifiers-not-renamed discipline).
- **Gates**: `api/test_adr567_researchers_desk.py` (lane_meta.app persisted; runner selects
  the desk posture for app="radar" and the studio posture otherwise; desk posture carries the
  file grammar + never-invent + unparseable-repair teaching; falsified by construction);
  ADR-558's create_lane gate unaffected (an unbound `app` still 422s — D4 changes bound lanes
  only).

## 4. What this ADR does NOT decide

- **The app's display name** (D1 — held for the maintainer phase, with the colleague named
  now).
- **Connector sources / the capture re-light** (ADR-565 D7 phase-next, unchanged).
- **A general "every app gets a chat-created object" rule** — this is radar's contract;
  generalizing is a future observation, not a rider.

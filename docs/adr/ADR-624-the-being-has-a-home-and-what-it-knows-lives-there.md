# ADR-624: The being has a home — and what it knows lives there

**Status**: Ratified 2026-08-31 (operator thesis, tested in discourse across two
re-cuts and aligned in full). Implemented same day.

**Builds on**: ADR-596 (a being is identity ⊕ character ⊕ engine; authority,
clock and judgment live on grants, declarations and gates — never on the being)
· ADR-600 (one register) · ADR-601 (capability lives at the APP; many-to-one)
· ADR-610 (a being is someone a member MEETS) · ADR-320 (topology IS the
permission policy) · ADR-156/064 (memory is in-session, written as ordinary
files in the moment of learning).

**Supersedes** the ADR-414 D6 per-agent home CONTENTS (twelve files); the
folder and its grant-sidecar lock survive, re-cut. **Discharges** ADR-421's and
ADR-418's "surfaced on the agent detail" pointers by deleting the four dormant
surface rows they parked. **Does not** reopen ADR-599 D2 (member-authored
beings return as app pairings, not as dormant machinery).

---

## Context

The `/agents` per-being page (ADR-602 D6) renders five of the register's nine
row keys and one control. It is thin, and the operator's thesis was that it
should evolve toward "related information" — cadence, standing work, autonomous
work, setup.

Auditing that thesis produced a sharper finding than the thesis itself:

**The register is pure Python constants with zero substrate reads.** The pane is
already at ~100% coverage of its data source. There is no unrendered richness to
surface — every route to a fuller page needs a *new* source of agent-shaped
facts. The question is therefore not "what should we show" but "where do
per-agent facts live, given a register that is a code constant?"

### The fossil that answered it wrongly

`workspace_paths.py` already specified a complete per-agent home —
`agents/{slug}/` with twelve files — built for the ADR-414 "hired agent" and
never used by an ADR-596 being. Measured: `agent_home()` has **two consumers,
both in `programs.py`** (bundle fork); `lane_runner.py` reads **zero** agent
substrate; all three beings are `kernel: True`, so `assert_editable` refuses
every one of them.

Held against ADR-596 D1, **two of the twelve files are being-shaped**:

| File | ADR-596 D1 places it on |
|---|---|
| `IDENTITY.md` | the being ✓ |
| `_preferences.yaml` | the being ✓ |
| `MANDATE.md` · `_expected_output.yaml` · `standing_intent.md` | a **declaration** ✗ |
| `principles.md` · `_principles.yaml` | a **gate** ✗ |
| `AUTONOMY.md` · `_autonomy.yaml` · `_budget.yaml` | a **grant** ✗ |
| `judgment_log.md` · `reflection.md` | — (the trail; see D2) |

That is not a naming slip. It is a faithful implementation of a model where a
being *did* own its authority, clock and judgment — the model ADR-596→601
replaced. Awakening the file set wholesale would not extend the current frame;
it would re-litigate it.

### The scaling test, which is what settles it

Run the twelve-file home to twenty beings and thirty apps. Editor serves Slides
and Text; its purpose at each differs, so one `MANDATE.md` cannot hold both.
Either Editor forks into `slides-editor`/`text-editor` — **re-introducing the
injectivity ADR-601 D1 retired on a measurement** — or the mandate becomes so
generic it says nothing. The same breaks `principles.md` and
`_expected_output.yaml`.

**Every per-desk fact in the ADR-414 home breaks under many-to-one.** The
alternative scales the other way: a new app costs a registration plus a job
overlay; a new being costs a row; a being's prompt weight is CONSTANT in desks
served (measured: job overlay 86.7% of frame, character 2.4%).

### What the thesis was right about

The asymmetry is real: everything else load-bearing in yarnnn is substrate —
attributed, parent-pointered, revertible — and the being was the one thing
living outside the substrate of record. A being that cannot accumulate anything
cannot learn, and ADR-603 D3 named that gap explicitly and did not fill it:

> Worth porting later, and named here so it is not lost: Freddie's **judgment
> log and calibration trail**. A Supervisor whose proposed cadence gets
> corrected should accumulate that — it is the ADR-596 D2 dossier, and it is
> the part of Freddie that was right. Not built here.

The operator's second re-cut is what makes this cheap: **do not build a
dossier — give the being a folder and let it write ordinary files.** A dossier
is a mechanism with its own writer, reader and rules; a folder is the substrate
doing the job it already does. `write_revision` already gives append-only
history, attribution, revertibility and a reading face for free, and ADR-156
already ratified exactly this shape for memory ("memory happens in the moment
of learning, not as a batch job").

---

## Decision

### D1 — `agents/{slug}/` is a PRINCIPAL HOME, and it holds two things

The folder survives; its contents are re-cut to what ADR-596 D1 permits:

```
agents/{slug}/
  memory/          — what the being has learned. FREELY WRITABLE by that being.
  _autonomy.yaml   — the witness dial it runs under.   GRANT SIDECAR — locked.
  _budget.yaml     — its allocation (reserved).         GRANT SIDECAR — locked.
```

One sentence, and it is the whole rule:

> **A being's home holds what it KNOWS (free) and the GRANTS it runs under
> (locked). Nothing else.**

The ten ADR-414 files that put authority, clock, purpose or per-desk judgment on
a being are **deleted from the spec** — not deprecated, not dormant. Each has a
live home already: purpose and clock in **declarations** (ADR-603 D1, app-named
so they survive re-pairing), judgment rules in **gates** and the app's job
overlay (`agent-composition.md` §3.2.1 is the singular home for that
partition), character in `posture` (the register), authority in **grants**.

`IDENTITY.md` is deleted as redundant rather than as misplaced: it is
being-shaped, but the being already HAS a character in the register, and two
homes for one fact is the ADR-562 drift.

**The distinction the topology already knew.** `_is_path_locked` carries one
leaf-shaped exception on top of the five-root prefix table, and its comment
states this ADR's premise in advance: *"an agent home is a principal-home, not a
semantic root — the root table cannot express it."* The five roots
(`governance/` `constitution/` `persona/` `operation/` `system/`) answer *what a
file MEANS*; a principal home answers *whose it IS*. Different axis. This ADR
does not add a root; it gives the existing exception its second half.

### D2 — The trail is memory, not a new concept

`judgment_log.md` and `reflection.md` do not return as named files with parsers.
What ADR-603 D3 asked for — a being that accumulates what it learned when
corrected — is served by `memory/` as ordinary markdown, written by the being
through `WriteFile(mode="append")` exactly as ADR-156 already has it write
`memory/notes.md` today.

**Flat, not desk-scoped.** `agents/{slug}/memory/` accumulates across every desk
the being serves. A per-desk split (`memory/{app}/`) was considered and refused
for now: it guesses at a structure before there is evidence, and the being can
subdivide its OWN folder without a schema change the day per-desk blur actually
appears. That is the point of it being substrate.

### D3 — A being writes freely in its own home, and nowhere else in `agents/`

`agents/` is in **no** locked prefix set today, so `caller_class="agent"` may
write any being's home — including another being's. That is the gap this D
closes, and it closes it at the SAME chokepoint the sidecar rule already uses
(`_is_path_locked`), never at call sites (the ADR-563 lesson).

The rule, in the order it evaluates:

1. A **grant sidecar** (`_autonomy.yaml` / `_budget.yaml`) under any agent home
   is locked for `freddie` / `mcp` / `agent`. *(Unchanged — ADR-414 D6.)*
2. A path under `agents/{other}/` is locked for an `agent`-class caller whose
   own slug is not `{other}`. **New.**
3. Everything else falls through to the root-prefix table. *(Unchanged.)*

Rule 2 needs the caller's own slug, which `_caller_class` discards. The class
resolver keeps its signature and its five return values; a **separate**
`_caller_agent_slug(auth)` reads it from `caller_identity` (`agent:{slug}` /
`specialist:{slug}`), returning None when the identity carries no slug. Fails
CLOSED: an agent-class caller with no resolvable slug is locked out of every
agent home rather than admitted to all of them.

**⚠️ Honestly recorded: today this rule binds almost nothing, and that is not a
reason to skip it.** A lane's `caller_identity` is `member:{user_id} via
{model}` (`lane_caller_identity`), which `_caller_class` maps to **`operator`**
— a lane writes under the MEMBER's grant, per ADR-411 D4, not under a being's.
So no live caller is `agent`-class-with-a-slug today. The guard is built now,
before the writer, for the ADR-601 D3 reason its sibling `assert_editable` was:
a protection written alongside the feature it constrains is one that feature's
author may forget. It is exercised by the gate, so it is not untested code.

**A being writing its own memory is therefore a WRITE THE MEMBER MAKES, today.**
That is coherent — the lane is the member's embodiment — and it is stated here
rather than left to be discovered, because it is the seam any future
being-authored write must cross.

### D4 — The surface renders READS, not a second model

The per-being page gains what already exists elsewhere, rendered at the being.
Nothing here is a new store:

| Section | Source | Already existed |
|---|---|---|
| Works in | `desks_for_agent` ← app registrations | ✅ served, rendered |
| Runs on | the register's `model` | ✅ served, rendered |
| Connections | `member_state` opt-in | ✅ served, rendered |
| **Memory** | `agents/{slug}/memory/` via the Files door | **new — D1** |

Memory renders as **files, openable in Files like anything else** — never a
bespoke viewer. The OS owns one reading face (ADR-590/ADR-595 D1); a private
memory renderer would be the second-face drift ADR-595 deleted a canvas to
avoid.

**Autonomy is NOT given an editable dial here.** ADR-551 D5 left an inverted
gate (`test_adr238_autonomy_substrate` asserts the deleted shape module stays
gone) precisely so that re-adding an operator autonomy dial must argue with a
red gate rather than arrive as a UI addition. Rendering a locked grant is a
READ and that gate permits it; the dial itself waits for ADR-382 and its own
ADR. Named, deliberately not built.

### D5 — The four dormant surface rows are DELETED

`identity` · `mandate` · `principles` · `expected-output` have carried
`route: ""` and "dormant until the per-agent FE (ADR-382)" since 2026-07-08.
They describe the ADR-414 hired agent — a model with **zero instances** — and
D1 has now decided that those four concepts do not live on a being at all.

A row reserved for a surface that this ADR has just declined to build is the
ADR-592 inert-field shape: a declaration nobody honours, waiting to be
misread as intent. They are deleted, not left dormant. The steward-era
substrate paths they pointed at (`persona/`, `constitution/`, `contract/`) are
untouched — substrate is never deleted by a surface's retirement (ADR-599 D5),
and the pre-ADR-414 workspaces that hold those files keep reading them through
Files.

`StandingBand` (the Notifications "To do" head) still reads
`contract/_expected_output.yaml` + `persona/standing_intent.md` and is
UNTOUCHED: it renders steward-era substrate, not a per-agent home, and it
already renders nothing when both reads are empty.

---

## Consequences

- **The being becomes a tenant of the substrate of record** without becoming a
  second agent model. What it knows is attributed, versioned, revertible and
  readable in Files — because it is ordinary substrate, not a dossier.
- **Many-to-one survives.** Nothing in the home is per-desk, so Editor serving
  Slides and Text needs no fork and no second mandate.
- **One agent model, not two.** The ADR-414 twelve-file spec leaves
  `workspace_paths.py`; the register plus the principal home is the whole story.
- **The confinement guard exists before its writer** and fails closed, so the
  day a being writes under its own identity there is nothing to remember.
- Named, deliberately not answered: the per-agent autonomy dial (ADR-382 +
  ADR-551 D5's gate); whether memory should ever be desk-scoped (D2 — awaiting
  evidence, not design); a being-class write identity, which D3 records as the
  seam it will cross.
- Gates: `test_adr624_the_being_has_a_home.py` — the home's shape, the
  confinement rule in both directions, the sidecar rule preserved, the deleted
  rows staying deleted, and the register's coverage by the pane. Every check
  falsified against the pre-change tree.

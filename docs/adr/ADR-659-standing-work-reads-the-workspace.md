# ADR-659 — Standing work reads the workspace: the source is a path, the run is paced, the claim is its own

> **D2 superseded by [ADR-666](ADR-666-the-run.md) D2** (2026-09-24): what a run wrote is stored on its row in
> `runs` (`revision_id`), and what it read is its steps; the 180-second time-window join is deleted.
>
> **Status**: **Accepted + Implemented** (2026-09-20, operator: *"aligned in full … delegate implementation
> details"*). D1–D7 shipped; §9 has the receipts and the one thing not yet driven (the door's click-pass).
> **Date**: 2026-09-20
> **Authors**: KVK (operator) + Claude (collaborator)
> **Dimensional classification** (Axiom 0): **What** (the material a run reads) and **When** (the pace of a run).
> **Frame**: [`docs/analysis/the-supervisor-from-first-principles-2026-09-20.md`](../analysis/the-supervisor-from-first-principles-2026-09-20.md)
> — this ADR is its §5 steps **0–2**. Steps 3–5 are named in §8 and are not decided here.
> Gate: `api/test_adr659_standing_work_reads_the_workspace.py`.

**Amends** — ADR-569 D4 / ADR-582 D6 (the source grammar gains a third shape) · ADR-618 D2 (the claim) ·
ADR-658 A1.8 (its heuristic is deleted, §2) · ADR-639 D3 (`app` refuses a composed app).

**Preserves** (load-bearing, untouched):
- **FOUNDATIONS Axiom 4** — *two trigger shapes, and only two*. Nothing here wakes on a change. §6 is careful.
- **ADR-596 D1 / ADR-626 D4.a** — no authority on a being; *agents do not orchestrate agents; declarations do*.
  This ADR is that sentence, applied.
- **ADR-639 §1.3** — the unattended turn stays **toolless**. A path source is gathered by the kernel and
  handed to the turn; the guard that *a clock and a credential never meet* is not approached.
- **ADR-569 D1/D3** — designation stays explicit; the write stays confined to the one designated leaf.
- **ADR-209** — `write_revision()` is the one write path; every gathered path is cited in `derived_from`.
- **Axiom 1** — no per-run state is stored. The pace rule and the run's product are both **derived** (§3, §6).

---

## 1. The problem

The audit's standard was the member's own sentence: *things come in, something gets made or done, over and
over, show it to me, tell me what needs me.* Scored against the live lane, two findings are structural and
everything else follows from them.

**A source cannot be a workspace path.** `_classify_sources` accepts an `http(s)` URL or a `{connector,
selector}` slice and nothing else; a third shape makes the *whole declaration* `sources_invalid`. So unattended
work can watch the outside world and **cannot read the commons it exists to compound** — not an upload, not
what an outside AI saved over MCP, not another declaration's kept file. Nothing chains. This limit was never
ruled: no ADR refuses a workspace source. It was named as a gap three times (ADR-656 D5, the handoff, the
09-18 analysis) and built by no one.

**Every tick of a prose declaration is a paid turn**, whether or not anything moved. The honest no-op is
detected *after* the spend (`content == current`), or judged by the model (`NO_CHANGE`). The pace law that once
guarded this (ADR-580 D2's `is_due`) was deleted with the digest and survives only as capture's freshness floor.

And one defect underneath both, **driven 2026-09-20**: the run's claim is stored in `tasks.next_run_at`, the
column the materializer owns. A never-run door-created declaration is claimed → the next tick's
`materialize_standing_index` reads the future sentinel, `preserve_due_commitment` declines to keep a future
value, and the row is rewritten to *now* → due again → **a second claim succeeds while the first run is in
flight**. ADR-658 A1.8 closed the mirror of this at the manual door with a heuristic (*"a `next_run_at` the
schedule could not have produced"*); the cause is shared and is fixed here at the root.

---

## 2. D1 — The claim is its own column, and it is a lock

`tasks.claimed_until timestamptz NOT NULL DEFAULT 'epoch'` (migration 258). `claim_run` becomes one
conditional update — *hold this row until T, if nobody holds it now* — which the database serialises. It
compares against **no value its caller read**, so there is no sentinel to read back and mistake for a
commitment, and the materializer cannot clobber it because the materializer never writes the column.

- the due scan skips a held row; `record_run` releases the hold with the schedule advance; a crashed run's
  hold lapses after `CLAIM_HOLD_HOURS`.
- Run now **materializes, then claims** — a never-indexed declaration gets its row first, so "no row yet" stops
  being a special case that skipped the claim.
- **Deleted**: the sentinel-in-`next_run_at`, `claim_run`'s `original_next_run` parameter and the third element
  of every `due` triple, `routes/standing_work.py::_claim_in_flight` (A1.8's heuristic), and
  `read_standing_task_row`. Also the stale `__all__` in `scheduling.py`, which exports four functions ADR-632
  deleted, and its header's claim that `tasks` *"survives as data until a follow-up migration drops it"* —
  ADR-639 D3 re-founded the table as the one drain loop's index.

`NOT NULL DEFAULT 'epoch'` rather than a nullable column is deliberate: the claim is then a single `lt` filter,
the shape the due scan already proves in production, instead of an `or(is.null, lt)` expression.

## 3. D2 — A run shows what it wrote

The detail's runs are rows of the **cost** ledger and could not say what a run produced. The product already
exists: a successful run is exactly one `system:standing` `derivation` revision on the target. The detail joins
each successful write row to that revision **at read time** (nearest `system:standing` revision on the target
within the run's own window) and serves its id and its `derived_from`. Derived, never stored — no column is
added to `execution_events`.

## 4. D3 — A composed app executes nothing

`app: supervisor` parsed clean and `resolve_executor` returned the Supervisor, against ADR-658 D3 and the app's
own registration comment: the only guard was the *absence* of `standing_executor`, which the resident fallback
defeats. Ruled from material, not by name: the executor derives from **what the file is** (ADR-596 D1), and a
composed app (`register: "composition"`, `is_composition()`) owns no material — so it can be no file's app.
`_classify_app` answers `app_invalid`. No new field; the existing register is read.

## 5. D4 — A source may be a workspace path

```yaml
sources:
  - id: inbox
    path: inbound/uploads/          # a FOLDER (trailing slash) — its live text files, newest first
  - id: digest
    path: research/digest.md        # a FILE — for instance another declaration's kept file
```

`{id, path}` joins `{id, url}` and `{id, connector, selector}` in the one parser. The kernel gathers the
material and hands it to the same toolless turn; every path read is cited in `derived_from`, so **the graph is
witnessed on the ledger** the moment it exists (ADR-448) — nothing else stores it.

**The rules, each refused by a named problem, never silently:**

1. **Inside the workspace, normalised once.** `/workspace/x`, `workspace/x` and `x` are one path (the write
   door's `_normalize_workspace_rel`); `..` and an empty path are `sources_invalid`.
2. **Never its own machinery.** A source may not be the declaration's own target, `CONTRACT.md` or
   `_standing.yaml`. A folder source that *contains* them gathers around them — *"summarise this folder into
   `summary.md`"* is the obvious declaration and must work.
3. **Structured targets take exactly one FILE.** `csv · json · txt` map one body to the leaf; a folder is
   `sources_invalid` there, as two URLs already are.
4. **Bounded.** A folder gathers at most `_MAX_FOLDER_FILES` live text files, newest first, each cut at the
   existing per-source slice. The material's header says how many were left out — the turn is told what it did
   not see. Binary and Trash are never gathered (the 2026-09-07 lifecycle lesson).
5. **Scoped to the declaration's workspace** — `StandingDecl` carries `workspace_id` from discovery and every
   gather filters on it, so an owner of two workspaces cannot have one's run read the other's files.
6. **The door checks the declarer can read it** (`_is_path_readable_for_principal`, the ONE matcher): a source
   outside the caller's `read_scopes` is refused `source_unreadable`, because the run reads with the owner's
   reach and would otherwise launder it. ⚠️ **Named limit**: the conversational path writes the YAML through
   `WriteFile`, which checks *write* scopes only. Every principal with a narrowed read axis today is a
   share-as-view grant with `write_scopes=[]` and cannot author a declaration at all; the day a
   write-but-narrowed-read grant exists, the run must check the declaration's author. Not built; do not forget.

### 5.1 D5 — The cycle is refused by name

Once a target can be a source, a loop is expressible: A keeps `a.md` from `b.md`, B keeps `b.md` from `a.md`.
Under §6 each write re-arms the other — spend with no floor. `source_cycle` is computed at discovery over the
workspace's declarations (a target reachable from itself through file or folder sources) and **every
declaration on the cycle** gets the problem, so none runs and the roster says why. A problem declaration gets
no index row (ADR-639 D3, unchanged), which is what makes the refusal structural rather than advisory.

## 6. D6 — The pace rule: a run whose sources have not moved is skipped at $0

`make`'s one rule. Before the paid turn, the run asks: *has any prerequisite moved since this declaration was
last judged?*

- **last judged** = the newest `standing-write:{topic}` ledger row that is `success` or `skipped/no_change`.
  A failed or refused run is *not* a judgment, so it retries. Read from the ledger; nothing is stored.
- **moved** = a path source's head is newer · a connector's landed snapshot is newer · an HTTP body differs from
  the last retained raw · **`CONTRACT.md` is newer** (a changed contract must re-judge an unchanged world).
  A member's edit of the *target* neither hastens nor delays (ADR-580 D2, kept).
- nothing moved → `standing-write` is recorded `skipped` / **`sources_unchanged`**, mechanical, **no model
  call**. A first run (never judged) always proceeds. **Run now always proceeds** — the member asked.
- an HTTP body identical to the last retained raw is **not retained again**: the raw lane stops accumulating
  byte-identical observations (one per tick today).

⭐ **Axiom 4 is not amended.** The drain is still the only thing that fires a run, on the declaration's
schedule; a change in the world is still *read on the next turn* and *causes* none. What changes is that a
tick which finds nothing new costs nothing — so a member may declare a tight schedule, and a chain
(*capture → digest → report*) settles within a few ticks of its head moving, without any event source, wake
queue or funnel. The three incidents behind Axiom 4's recut (ADR-428's paid no-ops, ADR-632's dormant stack,
ADR-603 D5's contract-less clock) are each *answered* by this shape rather than routed around.

## 7. D7 — The door and the skill say it

ADR-658's own lesson: *a capability reachable only by naming it unprompted is indistinguishable from one that
is absent.* `GET /api/standing/starts` gains the always-present **"something in your workspace"** start beside
the web page; the door's source field accepts a path; the detail names a path source as the file or folder it
is. `declaring-standing-work` teaches the third shape and the chain; `keeping-a-file-current` is unchanged (the
craft does not depend on where material came from). Prompt-change protocol applies (CHANGELOG + ratchets).

---

## 8. What this does NOT decide

Named so they are not silently assumed — the analysis's §5 steps 3–5, each its own ADR:

- **Attention reads the work** — `needs-you` still reads chat mentions; a refused run does not reach it.
- **The Supervisor's job text** — still ADR-656's subject; it never mentions standing work.
- **The graph in the cockpit** — the edges exist on the ledger after D4; nothing draws them yet.
- **The proposed act** — a run still cannot end in a witnessed send or publish.
- **Compose targets, the generator cardinality, the 4096-token ceiling** — a kept file is still a short document.
- **Connector capture has no driver of its own** — it runs only when a declaration reaches for it.

## 9. Implementation status

| Decision | Status |
|---|---|
| D1 the claim column | **Implemented.** Migration 258 applied and verified against the LIVE column (`timestamptz NOT NULL DEFAULT epoch`), PostgREST cache reloaded. **Driven against the live table** with a throwaway row that could never come due: claim `True` → second claim `False` → `record_run` releases to epoch → claimable again; row deleted, index back to 0. |
| D2 run → revision | **Implemented** — `_recent_runs` joins at read time; the detail shows what each update was made from. |
| D3 composed app refused | **Implemented** — `app: supervisor` → `app_invalid`; `blogger` and the derived default unchanged. |
| D4 path sources · D5 cycles | **Implemented** — parser, gather, discovery marker, and the door's `source_unreadable` / `source_cycle` guard on create AND edit. |
| D6 the pace rule | **Implemented** — including the run-start anchor (below) and the raw lane's de-duplication. |
| D7 door + skill | **Implemented** — the workspace start, the door's path field (offering the workspace's real folders from `getRoots`), the skill + CHANGELOG `[2026.09.20.1]`. ⚠️ **Not click-passed**: `tsc` clean and `next build` green, but the door's new field has not been driven in a browser. Owed; in SESSION-HANDOFF. |

**Found while building, and fixed in the same change:**

- ⭐ **The pace rule's first cut had a hole.** It compared a source's time against when the judged run's
  *ledger row was written* — so a source that moved DURING the ~20 s model call was older than the judgment and
  would never be re-read. The anchor is now the run's START (its `standing-sweep` row's time less that row's own
  duration), erring early: one redundant turn in a rare race, never a missed change.
- **Run now recorded outside a `finally`**, so a run that raised would have stranded its own hold for two hours.
- **Two of this gate's own arms stayed GREEN under falsification** and were vacuous: the *held row is not due*
  arm scanned a workspace with no declaration file (so it returned `[]` whatever it filtered), and the LIKE
  over-match arm used a folder name with no underscore (so the wildcard could never fire). Both rewritten until
  they went RED. `ADR-582`'s gate crashed on the connector reader's new third return value and was amended
  (50/50, +1 arm asserting the landed stamp).

**Gate**: `test_adr659_standing_work_reads_the_workspace.py` **79/79**, fifteen in-place falsifications all RED.
Inherited, re-run: ADR-658 **121/121** · ADR-639 ✓ · ADR-618 **18/18** · ADR-582 **50/50** · ADR-393 9/9 ·
ADR-580 9/9 · registry 145/145 · ADR-653 95/0 · ADR-592 45/45 · ADR-338 17/0 · ADR-297 161/0 · skills 153/0 ·
seat 73/0 · voice guard 0 · changelog discipline 4/4.

## 10. Verification

Gate: `api/test_adr659_standing_work_reads_the_workspace.py` — script-shaped, reports a count, every arm
proven RED by an in-place edit restored in a `finally`.

- **D1**: on an in-memory index — claim, then materialize a never-run `fire_on_activation` declaration: the hold
  survives and a second claim is refused (the driven defect, inverted); a lapsed hold is claimable; `record_run`
  releases. `_claim_in_flight`, `read_standing_task_row` and `original_next_run` are absent from the code.
- **D2**: a successful write row carries the revision it wrote; a failed row carries none.
- **D3**: `app: supervisor` → `app_invalid`; `app: blogger` still resolves.
- **D4**: a file source and a folder source are gathered, the folder skips the declaration's own machinery,
  Trash and binary are never read, another workspace's same-named path is never read, and `derived_from` cites
  exactly what was read. The three spellings of one path normalise to one.
- **D5**: own-target and a two-declaration loop are `source_cycle`; a straight chain is healthy.
- **D6**: driven through the REAL sweep with a spy on the model call — unmoved sources → no call, a
  `sources_unchanged` row; a moved source, a newer contract, a first run, and `force` each → the call happens;
  a failed prior run does not count as judged.
- Inherited, re-run: ADR-618 · 639 · 658 · 393 (capture shares the loop) · 580.
- The migration is verified against the LIVE table, not the runner's exit code.

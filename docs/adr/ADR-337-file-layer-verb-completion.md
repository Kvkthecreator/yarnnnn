# ADR-337 — File-Layer Verb Completion: the Working-Tree Half of the Repo Analogy

> **Status**: Implemented (2026-06-11) · **Amended 2026-08-21** (D8 — the folder grain; **D9 — one delete, one meaning: D2's live-row removal becomes ARCHIVE**; D6's MCP bullet superseded)
> **Date**: 2026-06-11
> **Authors**: KVK, Claude
> **Dimensional classification**: **Mechanism** (Axiom 5 — the primitive vocabulary) + **Substrate** (Axiom 1 — what the verbs mutate) + **Identity** (Axiom 2 — who maintains the working tree)

## Companion canon

- FOUNDATIONS Axiom 1 (Substrate; every write attributed and retained) + Axiom 5 (Mechanism; primitives are its vocabulary)
- ADR-209 — Authored Substrate (revision chain; D7 revert-as-write; **extended by this ADR**: the verb set gains delete/move; the chain's retention guarantee is what makes them safe)
- ADR-168 — Primitive Matrix naming reform (`*File` family naming; this ADR continues the convention)
- ADR-307 — Unified Permission Taxonomy (the new verbs are consequential, gate-owned, path-addressed)
- ADR-275 — housekeeping cadence is Reviewer-authored (the cadence slot this ADR finally gives verbs to)
- ADR-319 — Stewardship of Intent against Ground Truth (the posture, one altitude down: stewardship of the *medium* the intent lives in)
- 2026-06-11 alpha substrate audit + write-integrity fix (`f1ef557`) — the evidence trail

## Context — the audit finding

The 2026-06-11 alpha substrate audit traced three pathology classes across the alpha
workspaces (0-byte deliverables, dead `context/` trees, permanent litter) and the
holistic follow-up audit found their common root: **the Claude Code analogy that canon
repeatedly invokes was implemented faithfully at the cognitive altitude (memory,
compaction, skills, sub-agents, hooks, permission gating — each with an explicit ADR)
and only half-implemented at the substrate-verb altitude.**

Claude Code operating on a repo has `Read, Write, Edit, Glob, Grep, rm, mv, git
log/show/diff/revert`. YARNNN's file layer had `ReadFile, WriteFile(overwrite|append),
ListFiles, SearchFiles(BM25), ListRevisions, ReadRevision, DiffRevisions` — read-side
complete (richer than bare git), write-side **create/overwrite/append only**. No
surgical edit. No delete. No move. The absence was never decided: ADR-209 D10
explicitly scoped out branching + replication but is silent on delete/move; no ADR
ever proposed or rejected an edit primitive (verified by exhaustive sweep, 2026-06-11).

The pathologies map 1:1 onto the missing verbs:

1. **0-byte truncation wipes** ← no `EditFile`. Every change to an 18KB
   `principles.md` or a growing `judgment_log.md` was a whole-file rewrite — the
   exact write shape that collided with the output-token ceiling and produced the
   truncated empty writes fixed in `f1ef557`. The `max_tokens` fix treats the
   symptom; whole-file-rewrite-as-only-verb is the exposure.
2. **Litter is permanent** ← no `DeleteFile`. Pollution could only be buried, never
   removed — by anyone except a developer with psql.
3. **Migration residue + `conflict-backups/`** ← no `MoveFile` + overwrite-only
   writes. The `context/`→`operation/` re-root was a hand-rolled mass `git mv`.
4. **Wiped-file recovery was dev-only** ← revert-as-write (ADR-209 D7) is composable
   from `ReadRevision` + `WriteFile`, but nothing senses the need or names the duty.

The sharpest form of the posture gap: this repo's own execution discipline #1 —
*"Singular Implementation: delete legacy code when replacing"* — is enforced on the
system's developers but was structurally impossible for the system's agent. ADR-319
ratified stewardship-with-urgency over the *intent*; the agent had no verbs to steward
the *medium*.

## The naming question, settled

Should the verbs adopt bash/Claude Code names (`Edit`, `rm`, `mv`, `Bash`)? **No.**
The decision rule this ADR ratifies:

> **Names and safety semantics are YARNNN's (the primitive matrix is our syscall
> ABI); parameter contracts follow Claude Code's tool shapes wherever a trained
> model prior exists (the competence is borrowed).**

Rationale, in force-ranked order:

1. **The names carry semantics bash would lie about.** YARNNN's delete removes the
   live view while the revision chain retains every byte; `rm` signals irreversible
   destruction. YARNNN's writes are attributed commits, not byte streams. The
   descriptive names ARE the safety model, for both the LLM and the operator.
2. **ADR-168's `*File` family naming is standing canon.** `EditFile` / `DeleteFile` /
   `MoveFile` are its zero-churn continuation.
3. **The ABI is multi-vendor** (ADR-310/311 interop). Bash names bias every foreign
   caller toward POSIX expectations (flags, globs, pipes) that don't exist here.
4. **Operator legibility** (Derived Principle 12): primitive names leak into feed
   narration, revision messages, and the proposals queue. `DeleteFile` is
   self-explanatory to a layman; `rm` is jargon.
5. **No `Bash`.** Bash is arbitrary compute, not a verb. Its absence is the one
   deliberate, defensible divergence from Claude Code: the ADR-307 gating model works
   because every mutation passes through a typed, classifiable verb. (It is also why
   missing verbs hurt so much here — there is no shell escape hatch — which argues
   for completing the verb set, not adding the hatch.)

Where literal alignment pays: **input schemas.** Claude models carry heavy trained
priors on Claude Code's exact tool contracts. `EditFile(path, old_string, new_string,
replace_all)` is literally the Claude Code `Edit` shape — uniqueness-of-match,
include-surrounding-context disambiguation, prefer-small-surgical-edits all transfer
for free. A novel patch shape (line numbers, ranges, diffs) would forfeit that prior
and buy a fresh failure-mode discovery process.

## Decisions

### D1 — `EditFile`: surgical in-place replacement (the Claude Code `Edit` contract)

`EditFile(path, old_string, new_string, replace_all=false, scope, authored_by?,
message?)`. Reads the current file, replaces `old_string` with `new_string`, writes
the result through the Authored Substrate (one new revision, attributed).

Contract (mirrors Claude Code `Edit` exactly — borrowed prior):
- `old_string` must exist in the file → else `old_string_not_found`.
- Without `replace_all`, `old_string` must be **unique** → else
  `old_string_not_unique` (the model already knows to add surrounding context).
- `old_string == new_string` → `no_change` error.
- The resulting content must be non-empty → else `empty_content_blocked` (the
  `f1ef557` write-integrity guard applies uniformly; emptying a file is `DeleteFile`'s
  job, by intent, not an edit side-effect).
- Permission: consequential, **path-addressed gate-queueable** (joins `WriteFile` in
  `_PATH_ADDRESSED_QUEUEABLE` — governance locks DENY, bounded/manual QUEUE).

This verb retires the largest residual exposure of the 0-byte class: appending one
entry to `judgment_log.md` or fixing one threshold in `principles.md` no longer
regenerates the whole file through the output-token ceiling.

### D2 — `DeleteFile`: move to Trash; the chain retains everything

> ⚠️ **AMENDED 2026-08-21 (see D9).** As originally written this decision
> specified **live-row removal**. It now ARCHIVES (`lifecycle='archived'`), the
> same act the Files surface performs — because two deletes with different
> recoverability was one delete too many. The original text is preserved below
> for the reasoning it carries; the second step is what changed.

`DeleteFile(path, scope, authored_by?, message?)`. Two-step, both attributed:

1. **Archive revision** — a `workspace_file_versions` row is inserted with the
   file's *current* blob (no new blob), `message` prefixed `DeleteFile:`. The chain
   records who deleted, when, why, and what the content was at deletion.
2. ~~**Live-row removal**~~ → **the row is kept, marked `lifecycle='archived'`**
   (D9). The file leaves the active workspace, appears in **Trash**, and is
   restorable in one act. Row removal survives for MOVE, where the source must
   genuinely go.

Restore is **`Restore`** (D9) — one verb, both grains — over the same
revert-as-write ADR-209 D7 defines. Deleting a file is a **view change, not
information loss**.

Errors: `file_not_found`. Permission: consequential, path-addressed (governance locks
DENY — the Reviewer cannot delete `governance/`, `constitution/` etc. under the same
`DEFAULT_REVIEWER_WRITE_LOCKS` that protect them from overwrite).

### D3 — `MoveFile`: relocation as one attributed operation

`MoveFile(path, new_path, scope, authored_by?, message?)`. Composition of D1's write
and D2's delete, as a single primitive call:

1. Revision at `new_path` with the current content (`message`: `MoveFile: from
   {path}`). Destination must not already exist → `destination_exists` (refuse
   silent overwrite; an intentional replace is `DeleteFile` then `MoveFile`).
2. Tombstone + live-row removal at `path` (`message`: `MoveFile: to {new_path}`).

The permission gate checks **both** paths against governance locks (the gate's
path-resolution helper generalizes from one path key to the verb's declared path
keys). The `context/`→`operation/` class of migration becomes a sequence of normal,
attributed operations instead of bespoke dev scripts + conflict backups.

### D4 — `SearchFiles` gains exact match (the grep half)

`SearchFiles(query, match="semantic"|"exact", scope, path_prefix?)`. Default
`semantic` is the existing BM25 path, unchanged. `exact` does case-insensitive
substring match over content (and path), returning matched paths with a snippet
around the first occurrence — the verb today's audit needed raw SQL for ("find every
file containing `context/`"). Stays `read_only` (never gates).

### D5 — Registry placement + the tool-count canary

All three verbs land in `CHAT_PRIMITIVES`, `HEADLESS_PRIMITIVES`, and
`REVIEWER_PRIMITIVES`. The Reviewer placement is deliberate despite the 2026-05-25
canary evidence (one added tool → ~74% output collapse): that canary added a
**novel-surface communication tool** (`platform_email_send_to_operator`) that changed
the judgment posture; these are **same-family file verbs** alongside the existing
`ReadFile`/`WriteFile` — low conceptual novelty, tight one-line descriptions. The
Reviewer is also the verb's primary customer: ADR-275's housekeeping cadence runs as
Reviewer wakes, and hygiene without delete/move is a duty without hands.
**Commitment**: the standing alpha soak (perception-field liveness instrument)
watches post-deploy Reviewer output volume; a collapse fingerprint reverts the
Reviewer placement (chat + headless keep the verbs regardless).

### D6 — What stays out, by decision

- **`cp`** — no demonstrated need; demand-pull discipline (ADR-225 lesson).
- **`Bash`** — capability, not verb; deliberate divergence (see naming section).
- **MCP exposure** — ⚠️ **SUPERSEDED by ADR-545** (2026-08). The interop surface
  binds `edit` / `delete` / `move` over these very verbs; a foreign caller does
  restructure, under the same ADR-307 gate and governance locks as anyone else.
  The original reasoning (foreign callers ask the operator) did not survive the
  file-native recut — the gate, not the roster, is the boundary.
- **A `Glob` tool** — `ListFiles` + `SearchFiles(match="exact")` cover the territory.
- **Branching / replication** — remain out of scope per ADR-209 D10.

### D9 — One delete, one meaning (amendment, 2026-08-21)

D2 shipped `DeleteFile` as live-row removal. The Files surface (ADR-400) shipped
delete as ARCHIVE. Both honour ADR-209 — the chain retains everything either way
— so both looked correct in isolation, and nothing compared them.

They are not the same act **to the operator**. Their own click puts a file in
Trash, where it is visible and restorable in one gesture. An agent's `DeleteFile`
made the file vanish from Trash as well, recoverable only by hand via
`ReadRevision` + `WriteFile`. Measured immediately before this amendment: **27
archived rows and 13 row-removal tombstones** — two populations of "deleted",
different recoverability, nothing distinguishing them.

The failure surfaced the way these always do. A member asked where a file had
gone; the model answered *"the file is still live — I read it directly"*, then
*"it wasn't deleted, it's sitting right there"*. It could not say the file was in
Trash because nothing in the system says so: the state was a lifecycle flag that
reads either as content (if a reader forgets it) or as **absence** (if a reader
respects it). Neither is the truth.

**D9.a — `DeleteFile` archives.** `archive_live_file` in
`services/authored_substrate.py` is the single act, called by the primitive AND
the Files route. One implementation, not two that agree.

**D9.b — `delete_live_file` stays, for MOVE.** A move's source row must genuinely
go: the file lives at its destination, and archiving the source would put a moved
file in Trash. The two acts answer different questions and both are correct.

This held for moved FILES and was violated for moved FOLDERS: `move_folder`
archived the source MARKER, leaving an empty ghost folder in Trash the operator
never deleted — and one `Restore` would have brought back at the old path. The
marker now tombstones-and-removes like the files it contained. **A move is not a
deletion at either grain.**

**D9.b′ — one act each, at both grains.** The folder fan-out, the single-file
route and the `Restore` primitive each carried their own archive/restore write
with its own copy of the ADR-427 head-blob form — three near-identical peers that
AGREED. Agreement is not singularity: the next change to what archiving means
would have had to be made three times, and the third is the one that gets
forgotten. All three now call `archive_live_file` / `restore_live_file`, and the
head-blob form lives once in `authored_substrate` — it is a property of the
LEDGER, not of whichever caller needs it.

**D9.c — `Restore` is a verb.** Trash without Put Back is `rm` with extra steps.
One verb, both grains: a single trashed file, or a folder trashed as a unit
(resolved from its `trashed_with` stamp, never from the caller — asking a caller
to know which grain they hold is handing them our bookkeeping). Bound to the same
`restore_group` the Trash view calls.

**D9.d — Trashed is a STATE, not an absence.** A read of a trashed path answers
*"is in Trash (moved {date}), as part of the folder {root}"* via
`describe_if_trashed` — the ADR-588 D1 shape: name what the thing IS and route to
the verb that answers it. Metadata only; the bytes stay behind `ReadRevision`,
because "deleted but still readable in one call" is exactly the ambiguity the
read filter removed.

**Why this is the axiomatic form rather than a bigger design.** The OS lesson is
not "add retention policies and quotas" — it is that in a desktop, **trashed is a
place you can open**, with Put Back beside it. The reversibility is VISIBLE, and
that visibility is what makes it trustworthy. We had modelled it as a hidden
flag, which has exactly two failure modes and we shipped both. Making the state
legible and the inverse verb present is the whole fix. Retention, auto-empty and
Trash sizing are deliberately NOT decided here (ADR-400 Q3 stands: archived is
permanent-but-hidden; ADR-478 supplies the terminal step when the operator wants
one).

Gates: `test_trashed_file_does_not_read_back.py` (the unification + the four read
paths), `test_verb_families_are_one_set.py` (the `trash` family is whole on every
surface).

### D8 — The folder grain (amendment, 2026-08-21)

`DeleteFolder` and `MoveFolder` join the set. **This ADR's own project,
completed** — not a new decision so much as the discovery that it had been left
half-finished, and that the half-finish cost exactly what this ADR predicted it
would.

**What happened.** A member asked their lane to delete a folder. The lane
answered that the workspace primitives *"only operate file-by-file rather than
recursively wiping whole directory trees"* and advised running **`rm -rf` in a
terminal**. Both halves were wrong. The fan-out existed —
`services/folder_organize.py`, shipped that week, and the Files surface had
carried Rename / Move / Move-to-Trash on folders since. And `rm -rf` on the repo
would not have touched the files at all: the substrate is Postgres, not disk.

This ADR named the failure mode in advance, in the passage ruling out `Bash`:

> *"It is also why missing verbs hurt so much here — there is no shell escape
> hatch — which argues for COMPLETING THE VERB SET, not adding the hatch."*

A missing verb does not degrade gracefully in a system with no shell. It becomes
a confident refusal plus a workaround that corrupts the operator's model of
where their own substrate lives.

**The verbs bind the existing fan-out**, never a second implementation:
`DeleteFolder` → `folder_organize.trash_folder`, `MoveFolder` →
`folder_organize.move_folder` (which itself fans out over the `MoveFile`
primitive, so an upload's `.extracted.md` projection travels with its raw per
ADR-554 D1). The operator's click and the lane's tool call are one act.

**No extra gate in front of them — and the reasoning matters more than the
outcome.** The first design instinct was to make a lane's folder-delete queue
for approval, or cap its fan below the operator's. Both were rejected on this
ADR's own first principles. The naming section rules that *the descriptive names
ARE the safety model*; here the safety is structural rather than procedural.
`trash_folder` writes one attributed `lifecycle='archived'` revision **per
file** — nothing is removed, the group restores as ONE unit, locked children are
refused and reported. That makes it **safer than the `rm -rf` the model reached
for**, and safer than `WriteFile`, which can truncate a file's content and flows
freely. Gating the safest destructive verb in the system while the lossy one
runs unimpeded is incoherence, not caution.

The Claude Code comparison holds for a reason worth stating: Claude Code handles
bulk deletion comfortably because **git** carries the safety, not a confirmation
prompt. YARNNN has that substrate and a stronger version of it — there is no
uncommitted state to lose, and group restore is one act rather than a path
argument.

**Distinct verbs, not a folder-aware `DeleteFile`.** Blast radius must be
legible in the verb the model CHOOSES and in the narration the operator later
READS — primitive names leak into feed narration, revision messages and the
proposals queue (Derived Principle 12). `DeleteFile` on a folder path would make
the transcript lie about what happened.

**Names ours, contracts borrowed** — the decision rule above, held verbatim.
`DeleteFolder` / `MoveFolder` continue ADR-168's family naming; never `rm -r` /
`mv -r`, which would import POSIX priors (flags, globs, `-f`) that do not exist
here. The schemas mirror the file verbs the model already knows.

**The interop roster does NOT grow.** MCP keeps one `delete` and one `move`;
`_names_a_folder` picks the grain. A foreign caller addresses a name, and the
kernel knows whether that name is a file or a folder — it should not have to
learn our taxonomy to say "delete this".

**Standing discipline.** The gate generalizes from file-verb-shaped to
family-shaped: `api/test_verb_families_are_one_set.py` declares the families and
asserts each is whole on every principal-facing surface, with deliberate
narrowings named in code AND required to be explained in
`docs/architecture/primitives-matrix.md`. Both sides of every comparison are
derived; a hand-kept list would reproduce the failure it guards.

### D7 — Stewardship posture (the duty the verbs serve)

The verbs exist so substrate hygiene can be **internalized** instead of dev-applied.
Three layers, per Axiom 5's determinism-to-judgment spectrum:

1. **Kernel guarantees** (deterministic): write-integrity guards (`f1ef557`),
   governance locks, the empty-content gate.
2. **Mechanical sensing** (deterministic, deferred to demand): topology conformance
   (any live file outside `_workspace_guide.md`'s declared roots is residue by
   definition), 0-byte anomalies. Named here; shipped when the housekeeping cadence
   first wants a sensor (ADR-305 discipline — no dead substrate ahead of a reader).
   **Trigger sharpened by ADR-339 D5 (2026-06-12)**: pull-shaped sensing is covered
   by the recursive metadata `ListFiles` (bytes column makes 0-byte anomalies
   visible in any listing); this layer ships only if push-shaped anomaly *wakes*
   are wanted.
3. **Reviewer judgment**: what is litter vs. load-bearing — decided at the
   Reviewer's own ADR-275-authored housekeeping cadence, executed with these verbs,
   attributed in the chain, gated by ADR-307.

The discipline cuts both ways: **developers do not hand-clean the working set**
(that is the agent's stewardship), and **the agent does not clean defect litter**
(that is a kernel bug to fix at the guard layer).

## Consequences

- The repo-analogy verb table in `primitives-matrix.md` becomes explicit (one
  mapping table: `EditFile ≈ Edit`, `DeleteFile ≈ rm` (view-only), `MoveFile ≈ mv`,
  `SearchFiles(exact) ≈ grep -F`) so future sessions don't re-litigate.
- `_PATH_ADDRESSED_QUEUEABLE` grows from `{WriteFile}` to `{WriteFile, EditFile,
  DeleteFile, MoveFile}`; the ADR-307 gate test's exact-set assertion updates in the
  same commit (ratified contract change).
- Tool counts: chat 28→31, headless 26→29, Reviewer 21→24 (+ ReturnVerdict).
- `workspace_files` deletion stops being a psql-only operation; every deletion is
  attributed in the revision chain from now on.

## Key files

`api/services/authored_substrate.py` (delete-with-tombstone helper),
`api/services/primitives/workspace.py` (3 tool defs + handlers + `_apply_edit` pure
function + exact-match branch + gate path-keys helper),
`api/services/primitives/registry.py` (3 lists + HANDLERS),
`api/services/primitives/permission.py` (queueable + path-addressed sets, multi-path
lock check), `docs/architecture/primitives-matrix.md` (rows + analogy table +
counts), `api/prompts/CHANGELOG.md`, `api/test_adr337_file_verbs.py` (gate),
`api/test_adr307_permission_taxonomy.py` (exact-set assertion updated).

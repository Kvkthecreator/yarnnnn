# Two theses, tested: skills-as-files, and the Agents page

> **Hat B** — evaluation capture. 2026-09-04, follow-up to ADR-639. Neither
> ruling changes the system by itself; each says what a system-hat change
> would have to be, and what the receipts allow.
>
> **Method**: real `run_lane_turn` calls against LIVE production substrate as
> the workspace owner, with real tools — not `route_completion` over a
> synthetic frame. Arm B monkeypatches `services.skills.skills_index_section`
> to `""`; every other byte of the frame is identical. Receipts are revision
> rows, `derived_from` edges, the ledger, and the produced files' own bytes,
> recovered from the CAS (`workspace_blobs.content` by `blob_sha`).

## Thesis A — "Skills as files let agents compose documents in a rich way"

**Ruling: the index is a RELIABLE DISCOVERY MECHANISM and an UNPROVEN CRAFT
MECHANISM. Not theatre — but not yet what ADR-630's argument claims.**

### The A/B

Three asks × two arms × repeated trials, all as real `run_lane_turn` calls
against live production substrate with real tools:

| ask | app | the skill it maps to | index in ARM A |
|---|---|---|---|
| a brief from several sources | text | `summarizing-sources` | 3,101 B (8 skills) |
| a deck from sources | slides | `presenting-from-sources` | 2,762 B (7 skills) |
| "keep this file current" | *unbound* (open chat) | `declaring-standing-work` | 3,947 B (11 skills) |

ARM B is the identical frame with `skills_index_section` returning `""`
(frame 10,792 → 7,691 B on the Text lane).

### What replicated: discovery

**The skill body was read in 6/10 ARM-A runs and 1/10 ARM-B runs** (the one ARM-B hit is the contaminated `keep` r1, which found the skills after listing the workspace root). The index
does exactly what ADR-630 §3 says it does — the description makes the body
findable, and the agent pulls it. That is not in doubt.

### What did NOT replicate: any effect on the artifact

The brief ask is the only one of the three that never saturates the 8-round
cap, so it carries the statistics: **n=6 per arm**, scored on the produced
file's own bytes.

| measure | ARM A (index) | ARM B (none) | |
|---|---|---|---|
| skill body read | 0.33 | 0.00 | *the discovery effect* |
| distinct sources read | 3.83 | 3.83 | identical |
| `derived_from` edges | 2.00 | **2.50** | favours B |
| inline path citations | 11.67 | 6.83 | **p = 0.500** |
| rounds | 5.33 | 5.33 | identical |
| tokens in | 69,504 | 73,318 | within noise |

Per-run inline citations — A `{22, 5, 23, 19, 1, 0}`, B `{5, 5, 23, 5, 0, 3}`.
An **exact two-sided permutation test over all 924 splits gives p = 0.500**:
the gap between the means is precisely what reshuffling the same twelve numbers
produces half the time. Both arms span 0–23. **This is chance.**

⚠️ And the one measure that *looked* like a clean win in the first trial —
22 vs 5 citations — did not survive: ARM A's next run scored 5, ARM B's third
scored 23. Reading trial 1 as a result would have been exactly the ADR-365
error the ADR-638 probe was written to avoid, in the opposite direction.

**`derived_from` was never the index's to move.** It is carried by
`PARTICIPANT_CITATION_RULE`, a kernel commons clause (ADR-533 D1) composed
into **both** arms. Both complied in 9/12 runs. The skill's *inline*
citation rule — the half only the skill states — is the one that came out at
p = 0.500.

### The keep ask: byte-identical output, without the index and without the skill

The sharpest single result. `keep` r2, arm-scoped so neither arm could see the
other's target:

| | ARM A | ARM B |
|---|---|---|
| index | 3,947 B (11 skills) | 0 B |
| skill body read | `declaring-standing-work` | **none** |
| rounds | 7 | 4 |
| wrote | folder + `CONTRACT.md` + `_standing.yaml` | the same three |

The two `_standing.yaml` files are **186 bytes each** and the two
`CONTRACT.md` are **1,771 bytes each**. Normalising only the target's
filename, they are **byte-identical — SHA-256 `ad41f443e7cd` and
`26835d5a1b19` on both sides.**

Arm B's tool trace explains it: it read arm A's declaration as an example.
That is contamination — so the ask was re-run in a **fresh meaning-folder with
no declaration anywhere near it**, where the only routes to the craft are the
index or the model's own prior. Arm B, index suppressed, ran
`ListFiles ""` → `ListFiles system/` → found `system/skills/`, read both
skills, and wrote a correct declaration.

⭐⭐⭐ **The mirror is the discovery mechanism; the index is a shortcut to it.**
ADR-630 mirrors every kernel skill into `system/skills/` as ordinary files
precisely so every reader reaches them — and that turns out to be sufficient
on its own. An agent that wants craft goes looking, and finds it, because the
files are *there*.

### The clean-folder run: what the index actually changed was the REFUSAL

The `keep` ask, re-run three times per arm in a **fresh meaning-folder** with
no declaration anywhere near it, so the only routes to the craft are the index
or the model's prior:

| | ARM A (index) | ARM B (none) |
|---|---|---|
| rounds to reach the skill | 1 | 4 (root → `system/` → search → read) |
| rounds total | 3, 4, 3 | 6, 7, 7 |
| seconds | 13, 30, 12 | 43, 43, 39 |
| **wrote the declaration** | **1 of 3** | **3 of 3** |

Every A run beat every B run on rounds and wall-clock — a perfect separation
(exact permutation p = 0.100, which is the *floor* at n=3: 2/20 splits).

⚠️ **And the first reading of that table was wrong.** A is not "faster": in
2 of 3 runs it wrote **nothing**, because it stopped and asked the member:

> *"Before I write the contract and schedule, I need a few specifics from you:
> 1. **Sources** … 2. **Cadence** — how often should prices get re-checked?"*

That is not a failure. `declaring-standing-work` step 2 is *"Get the contract
stated before the cadence. Ask what the file must stay true to … in the
member's words."* Step 4: *"Never invent a source URL. When unsure, say so and
ask."* Anti-patterns: *"A cadence with no contract"* and *"A schedule tighter
than anyone reads (every run spends the member's balance)."*

**ARM A read the skill and obeyed it. ARM B guessed a cadence and wrote.**

⭐⭐⭐ **That is the ADR-633 §5a effect, and it is on the REFUSAL side, not the
output side.** The question "did the skill change what the agent NOTICED and
REFUSED" has an answer here: it refused to declare a schedule the member had
not chosen, on a file whose every run spends their balance.

### …and the artifact was identical anyway

The one ARM-A run that *did* complete (c2) produced a `_standing.yaml`
**byte-identical to all three ARM-B declarations** — same weekly cron
`0 13 * * 1`, same two source ids, same `app: text`. Together with the earlier
`keep` r2 pair (identical SHA-256 on both `_standing.yaml` and `CONTRACT.md`),
that is five independent runs converging on the same bytes with the index on
and off.

**So both halves are true, and they are different halves:**

- **composition quality**: no measurable effect (citations p = 0.500;
  `derived_from` favours B; identical artifacts in 5 runs);
- **interaction discipline**: a real, visible effect — the skill's *"ask
  before you set a cadence"* rule fired in the arm that read it and not in the
  arm that did not.

### Ruling

**Not theatre. But the value is not where the thesis puts it.**

1. **Discovery works, reliably.** 6/10 vs 1/10 skill-body reads; 1 round vs 4
   to reach the craft in a cold folder. Keep the index.
2. **"Rich composition" is NOT supported.** Every artifact measure is null or
   slightly against: inline citations p = 0.500 over n=6/arm, `derived_from`
   2.00 vs 2.50, sources read identical, rounds identical, and five runs
   producing byte-identical declarations across both arms. ADR-639 D6's note
   (*"unmeasured prose until driven"*) should now read **driven, and null on
   output quality**.
3. **The measured effect is on REFUSAL and on the member's balance.** The
   skill's asking rule is the one instruction that visibly changed behaviour,
   and it is the one that protects spend on an unattended schedule. That is a
   better argument for skills than the composition claim, and it is testable
   the same way for the other ten.
4. **The load-bearing mechanism is the MIRROR, not the index.** ARM B found
   both skills by listing `system/` in 3 of 3 cold runs. Anyone proposing to
   save frame bytes by dropping the mirror and keeping the index has it
   backwards; the index is a *shortcut to* the mirror.
5. **Argue ceilings on rounds and refusals, not on quality.** `INDEX_CEILING`
   (3,400) / `UNBOUND_INDEX_CEILING` (4,000) were raised in ADR-639 D2 with a
   coverage receipt. Their benefit receipt is §above — round-count and the
   asking rule — never a composition claim.

### What this does NOT falsify

The probe measures **one member, one engine (`claude-sonnet-5`), three asks,
in a workspace whose substrate is rich with prior examples.** A model with a
weaker prior, a workspace with no examples, or a skill teaching something
genuinely non-obvious (`deriving-a-design-system`'s `_design.yaml` contract is
the candidate — it encodes a yarnnn-specific file format no prior could
supply) could all show the effect this did not. ⭐ **A null result on
`summarizing-sources` and `declaring-standing-work` is a null result on skills
whose craft a strong model already knows** — which is most of the eleven, and
is itself the finding worth carrying.

---

## Thesis B — "Evolve the Agents page in full"

**Ruling: NO EVOLUTION of the page's shape. Two derived rows, or nothing.**

### What the page is, and what it already answers

`web/components/agents/AgentsSurface.tsx` (527 lines) is a list of three
agents sectioned by `offered`, each with a detail page carrying: name, blurb,
provenance mark, **Works in** (app chips), Add-to-a-chat, **Runs on** (the
engine), **Memory** (a Files door), and **Connections** (the ADR-612 scope
toggles). The roster is server-driven from `routes/lanes.py::_agents_payload`,
which derives every row from `agents_registry.AGENTS` + `apps_for_agent`.

### The six facts, audited (ADR-616 discipline — count callers, not labels)

| Fact ADR-603 names | Where it lives today | Verdict |
|---|---|---|
| who works here | `_agents_payload` → the list | **already served** |
| in which app | `apps_for_agent` → `AppChips` | **already served** |
| what it has learned | `memory_path` → Files door (1 consumer) | **already served** |
| with which craft | **nowhere for a member** — `list_skills()` drops `metadata.apps` | derivable, unserved |
| tending which files | **nowhere** — `resolve_executor()` exists, has no reader outside the run | derivable, unserved |
| with what receipts | attribution is `member:{id} via {model}` (ADR-411 D4) | **refused — see below** |

Receipts against the live workspace (2026-09-04, `d5b9029b`):

- `execution_events` slugs: 494 × `lane`, and **no agent column at all**.
- `workspace_file_versions.authored_by` top values: `operator` (482),
  `system:mirror-recent-execution` (237), `member:{uuid} via
  anthropic/claude-sonnet-4-6` (24), `… sonnet-5` (18). **No agent ever
  appears in an attribution string**, by construction.
- Files under `agents/`: exactly **one** — `agents/editor/memory/notes.md`.
  Designer's and Blogger's "What X has learned" doors open an empty folder.

### The cliff, and what it refuses

`AGENT_ROW_KEYS` is a frozenset whitelist (`slug, name, blurb, icon, model,
token_profile, posture, offered, kernel`), asserted by
`test_agent_registry.py` (125/125 green at HEAD) against a banned-word list.
The client mirror `web/lib/apps/registry.ts` states the same rule from the
other side: *"a client row naming ANY authority is the D3.a cliff arriving
through a config file."*

So the ruling on each candidate door:

- **"What this agent did"** — a per-agent receipt ledger. *Refused as
  designed, and it is worse than unbuildable: it is misleading.* A partial
  join exists (`execution_events.session_id` → `chat_sessions.
  context_metadata.lane.agent`), and reading it teaches the actual lesson.
  It is **lossy**: of 200 sampled `lane` rows, 162 carry a `session_id`. And
  the agent stamps behind them include two retired slugs (`scout`, `keeper`)
  and **25 lanes stamped `app='text' agent='designer'`**.

  Those 25 are the interesting ones, and the first read of them was wrong.
  They are not a stamping defect: every one is dated 2026-08-14 → 08-20, and
  **ADR-602 moved Text from Designer to Editor on 2026-08-24**. The stamps
  are *historically correct* — Designer really did hold Text when those
  conversations happened.

  ⭐ **That is precisely why the row must not be built.** A truthful
  per-agent history is not aggregatable in the present tense: "Designer:
  25 documents" would be a true statement about August and a false statement
  about who does that work now, and the page has no honest place to say
  which. ADR-460 D2 keeps the ledger unrewritten *on purpose*; a surface that
  sums an unrewritten ledger under a present-tense heading launders history
  into a current claim.

  Beneath that, the deeper reason: ADR-411 D4 makes the member the author and
  the engine the mechanism *on purpose* — the agent is a character worn by the
  member's hands. "What Designer did" is not a fact the substrate holds, and
  manufacturing one puts an actor where the canon has a costume.
- **"Assign work / a skill / reach to an agent"** — refused by the cliff, not
  debatable.
- **"Which skills apply here"** — derivable and honest (below).
- **"Which files this agent tends"** — derivable and honest (below).

### The two rows that are derived, and would be new

Both computed live against production, purely, with **zero new state**:

```
agent    apps                skills that apply (metadata.apps ∪ universal)
designer [images]            4   composing-an-image, creating-skills,
                                 declaring-standing-work, deriving-a-design-system
editor   [slides, text]     10   + comparing-options, keeping-a-file-current,
                                 presenting-from-sources, reviewing-drafts,
                                 summarizing-sources, writing-a-spec, writing-updates
blogger  [blogger]           7   …

declaration                              app   -> resolve_executor()
operation/fundraising                    text  -> editor
operation/fundraising/market-sizing      text  -> editor
```

`resolve_executor` is already pure and already the run's own derivation; the
skills scoping is the same `_applies_to` the frame composes with. Neither
needs a column, a table, or a write path. Both pass the cliff test: they
state a **relation the kernel already derives**, and neither is settable.

### Why the ruling is still "no evolution"

The falsifier was: *if every fact the page would gain is already one click
away and nothing on it would be derived, the ruling is "no evolution".* It
half-fired, so the ruling is narrower than either extreme:

1. **The one fact that would justify a new PAGE — receipts — is refused.**
   Without "what this agent did", the page cannot become "the one place a
   member reads who works here … with what receipts".

   And **ADR-603 never asked for that page.** Its Consequences read: *"Runs
   stop being a concept: receipts surface in notifications (**what happened**)
   and on the agent page (**what this agent tends**)."* The sentence already
   splits them — receipts to notifications, tending to the agent page. The
   "with what receipts" framing is this audit's own extrapolation, and reading
   the source closed the question. ⭐ **Check whether the canon you are
   extending actually says the thing you are extending.**
2. **The craft fact is genuinely one click away.** All 11 kernel skills are
   mirrored into `system/skills/` (12 rows in this workspace) and readable in
   Files. The member is not blocked; they are merely not *told* which apply.
3. **The tending fact is one click away too** — Notifications → Standing
   work lists every declaration with target, cadence, sources and last run.
   What it omits is only *who* runs it (`StandingWork.tsx` renders no agent
   and no app, though the API already serves `app`).

So the honest scope is **two derived rows on the existing detail page**, not
a new surface and not a new noun:

- **Works with** — the skills that apply to this agent's apps, each a Files
  door into `system/skills/{slug}/SKILL.md`. Presentation of an existing
  derivation; the withheld/offered logic already exists in `_applies_to`.
- **Tends** — the standing declarations whose `resolve_executor` is this
  agent, each a door to the file's folder. Presentation of an existing
  derivation.

And one row that belongs on the **other** surface: Standing work should name
the app (already served) and the derived executor, because "who keeps this
current?" is asked where the declaration is, not where the agent is.

That is a one-commit change if the operator wants it, and it is deliberately
**not** made in this arc: it is a product judgment about a page nobody has
complained about, and the two facts it adds are each already reachable. What
this audit does settle is the boundary — **the receipts row must never be
built**, and the reason is on the record above.

---

## OWED item 1, settled: the GitHub reach landed nothing — and both hypotheses were wrong

Part O left this open: *"Either `run_connector_capture` writes only on change
(then the receipt should say so) or it degrades silently."* Neither. A third
cause, and it is the one worth the finding.

**The receipts.**

- `inbound/github/kvkthecreator-yarnnnn/` holds **exactly one file, ever**:
  `2026-08-28T01:45:25Z.md` (6,588 bytes), authored `system:capture-github`.
- `execution_events` where `slug LIKE '%capture%'`: **zero github rows, ever**.
  The only capture receipts in the workspace are `capture-slack` /
  `derive-capture-slack` from 2026-07-03.
- The connection row is healthy: `status='active'`, scope `read:user,repo`,
  aperture `['Kvkthecreator/yarnnnn']`, landscape discovered 2026-08-18.

**What the binding actually reads.** `CONNECTOR_CAPTURE_BINDINGS['github']`
is `platform_github_get_issues(state=all, limit=50)` — **issues and pull
requests, never commits**. The landed snapshot's newest item is PR #21,
`2026-07-08`. Checked against the live GitHub API this session:

```
newest 5 issues/PRs by updated:  #21 2026-07-08T02:32:06Z  (then #20, #19, #18, #17 — all July 1-2)
newest 3 commits:                2026-09-04T04:33:30Z, 04:23:57Z, 2026-09-04T01:36:13Z
```

So the repo is *extremely* active — and has had **no new issue or PR in two
months**, because the work is committed straight to `main`. The reach ran,
read the same 50 items, hashed identical bytes, and correctly skipped the
write (the diff baseline in `run_connector_capture` is the slice's latest
snapshot). **The standing run folded a week-old file because the connector's
chosen aperture does not observe the activity the operator actually
produces.**

**The real defect is the receipt, and it is structural.** In
`standing_work._reach_connector_sources`:

```python
try:
    await run_connector_capture(client, user_id, row, observed_at=…, selectors=stale)
except Exception as e:
    logger.warning("[STANDING] connector reach failed %s/%s: %s", …)
```

`run_connector_capture`'s own docstring says it *"never raises past its own
boundary"* — it returns `{success, paths_written, paths_skipped, items,
error}`. **The only handler is `except Exception`, so the failure mode the
writer actually produces is unloggable by construction**, and the rich return
— which distinguishes *wrote 1* from *skipped 1, unchanged* from *0 items,
credential dead* — is discarded at the call site.

That is why the handoff could not tell the two hypotheses apart: the
`standing-sweep` receipt for the 04:26Z run says `status='success'`,
`duration_ms=1001`, and carries **no field that could hold a reach outcome at
all**. A run whose sources all failed and a run whose sources were all
unchanged produce byte-identical receipts.

⭐ **A `try/except Exception` around a function documented never to raise is
not error handling — it is a comment that reads like error handling.** The
fix is to read the return, not to widen the catch.

### What is owed from this (not fixed here — ADR-594's seam, per Part O)

1. **Read the return.** `_reach_connector_sources` should carry
   `paths_written` / `paths_skipped` / `error` into the sweep's receipt, so
   "the source did not move" and "the source could not be read" stop looking
   identical. This is the ADR-628 lesson one seam over: *the stage with
   neither a receipt nor a refusal is the unsafe one.*
2. **The aperture is the product bug.** A GitHub connection that reads only
   issues and PRs cannot keep a file current about a repo whose history is
   commits. Either the binding gains commits, or the connector's
   `reads` string (which is already declared on the binding, and already
   rendered) needs to be read by whoever declares a GitHub source — the
   string is honest, nobody was looking at it.

---

## Method notes — what went wrong in the probe, and what it teaches

Recorded because two of these nearly produced a false ruling.

1. **The first trial was a false positive, and it was the most persuasive one.**
   `brief` r1 scored 22 inline citations with the index against 5 without, and
   ARM A read the skill. Written up then, it would have read as a clean win. By
   n=6 it was p = 0.500. ⭐ **A first trial that confirms the thesis is the one
   to distrust most**, and the fix is cheap: the extra four trials per arm cost
   ~8 minutes of wall clock.

2. **The substrate is itself a craft-transmission channel, and it contaminates
   an A/B run in one workspace.** Every later trial read an *earlier arm's*
   output as an example — `keep` r2's ARM B produced a byte-identical
   declaration after reading ARM A's. The fix was per-arm targets and then
   fresh meaning-folders. ⭐ **In a shared workspace, arm N+1 can see arm N's
   work; scope every artifact per arm or the null result is manufactured.**

3. **A "faster" arm was a non-completing arm.** ARM A won rounds and wall-clock
   3/3 in the clean folders — because in 2 of 3 it asked a question instead of
   writing. Reading the latency table alone would have credited the index with
   efficiency it did not deliver, and missed the real (and better) effect.
   ⭐ **Score completion before you score speed.**

4. **The deck ask measured the round cap, not the craft.** Both arms hit
   `_LANE_MAX_ROUNDS = 8` in 3 of 4 runs and emitted the "ran out of steps"
   message. A task that saturates the loop cannot discriminate anything; it is
   excluded from the statistics above and reported only qualitatively.

5. **A gate sweep against a shared live workspace must be the ONLY sweep
   running — and "backgrounded" is not "finished".** This bit twice. The first
   sweep read `0 PASS / 367 FAIL` (a driver bug: a glob path re-joined under
   `cwd`). The second read a plausible `259 PASS / 108 FAIL` — which was
   **also wrong**: a `ps` check later found **three live `test_adr209_*`
   processes** left over from the aborted runs, writing revisions to the same
   production workspace and reading each other's. (My first reading of that
   `ps` output said "three `sweep.py` processes"; two of those were shell
   wrappers of one command — the *children* were the real contention.)
   ⭐ **A background job I stopped reading is not a background job that
   stopped** — and killing the parent does not reap the child.

   ⭐⭐ **And then the sweep itself turned out to be the wrong instrument.**
   This arc changes **no runtime code** — three documents, one new gate file —
   so a 367-gate sweep cannot regress anything by construction, and every red
   in it is environmental (the ADR-209 phase gates write and re-read real
   production revisions, and are minutes each). *Verification should be scoped
   to what the change can reach.* The 15 gates covering the touched surfaces
   were run uncontested and are listed in the handoff; no full-sweep figure is
   claimed, because none was honestly obtained.

## What is owed

1. **The reach receipt** (ADR-594's seam) — `_reach_connector_sources` should
   read `run_connector_capture`'s return rather than catching an exception the
   writer documents itself as never raising. Detail in the OWED-1 section.
2. **The GitHub aperture** — `platform_github_get_issues` cannot observe a repo
   whose history is commits. Either the binding widens, or the declaration door
   surfaces the binding's own `reads` string, which is honest and unread.
3. **The `ADR-411 D4` phantom citation** — 33 sites across 26 files, cited to a
   decision that does not exist. Cite ADR-408 (origin) / ADR-460 (preserved).
   One mechanical commit.
4. **`operation/fundraising/market-sizing/`** — the `keep` probe moved the
   operator's real `market-sizing-reference.md` into its own folder and wrote a
   correct `CONTRACT.md` + `_standing.yaml` over it (monthly, three verified
   source URLs). **Left in place deliberately** — it is a good declaration over
   a real file — but it was created by a probe, not by the operator, and is now
   live in the scheduler (next run 2026-10-01). Keep or unwind, operator's call.
   Every other probe artifact (34 files, 6 index rows) was removed.
5. **Orphan index rows** — deleting a `_standing.yaml` leaves its `tasks` row
   behind. Inert (`_due_standing` skips a row whose declaration no longer
   discovers), so hygiene rather than defect; observed while cleaning up.
6. **The two derived rows of ADR-640 D2**, if the operator wants them. One
   commit; both derivations already exist and are pure.

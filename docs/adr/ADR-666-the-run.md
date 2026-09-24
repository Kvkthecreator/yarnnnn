# ADR-666 — The run: work that acts, seen while it happens

> **Amended by [ADR-667](ADR-667-the-supervisor-is-set-up-in-conversation.md)** (2026-09-24): D1's member stamp holds
> at the kernel (`browser_member_unknown`); a taken-up run keeps `trigger: scheduled` (D4); needs-you lists a waiting
> run only for its own member, and the band names whose browser (D8).
>
> **Status**: **Accepted** (2026-09-24; operator: *"yes, aligned in full … ensure singular streamlined discipline
> with code and docs, scoping in deletion and clean-up of code where warranted"*). Implemented with this
> document — §9 is the census.
> **Date**: 2026-09-24
> **Authors**: KVK (operator) + Claude (collaborator)
> **Dimensional classification** (Axiom 0): **What** (a run is the work, happening) + **Channel** (the member's
> browser, ADR-664, as a way standing work is done).
> **Gate**: `api/test_adr666_the_run.py`.

**Supersedes** — [ADR-665](ADR-665-browser-workflows.md) in full (Proposed, never built). Its idea survives —
work that lives in files and happens in the member's browser — but not its shape: a `WORKFLOW.md` procedure on a
schedule with no contract is the recurrence ADR-603 D5 retired, and `runs.md` is one file where a run needs its
own. **Amends**: ADR-658 D5 (the cockpit's sections) · ADR-659 D2 (what a run wrote is now stored on the run, not
joined by time) · ADR-662 D3 (a receipt's home is the run, not the reply). **Preserves**: ADR-662 D9 — browser
hands act only in a lane turn the member is present for; nothing in this ADR acts unattended · ADR-645 D1 — no
credential moves · ADR-639 — one drain loop, one declaration shape · ADR-231 — no task abstraction (§4).
**Derivation**: the discussion recorded in [access is brokered, never held](../analysis/access-is-brokered-never-held-2026-09-24.md)
§4, and [the Supervisor from first principles](../analysis/the-supervisor-from-first-principles-2026-09-20.md) §1.

## 1. The problem

From the member's chair a supervisor must show five things: what comes in, how work feeds work, what gets made
**or done**, what needs them, and one place to see it all (the 09-20 analysis §1). The browser (ADR-662/664) is
the widest *intake* and the only *execute* the product has — the two capabilities the 09-20 scorecard found
empty. So browser work is not a neighbour of the Supervisor; it is the missing half of it.

Three things stood in the way, each measured:

1. **A run had no life of its own.** A standing run was a toolless turn that finished in seconds; what the
   Supervisor called a run was reconstructed from cost-ledger rows (`standing-sweep:` / `standing-write:` in
   `execution_events`) and a revision matched to them **by a 180-second time window**. A browser run lasts
   minutes, is watched, can be stopped, and can wait — it needs a state, and nothing could hold one.
2. **What the browser did was private.** A browser act's receipt lived only on the assistant row of the
   member's own conversation (`metadata.receipts`) — and conversations are private (ADR-411). A colleague could
   not see that an agent posted to a site on the workspace's behalf.
3. **Nothing was live outside the chat that started it.** The realtime channel carried messages and file
   revisions only; the Supervisor re-read on click.

## 2. Decisions

### D1 — Browser work is standing work

A declaration gains **one** key, `browser`:

```yaml
target: prices.csv
schedule: "0 9 * * 1"
browser:
  member: 5f0e…          # whose browser does it — always the member who declared it
  sites: [example.com, shop.example.org]
sources: []              # optional: workspace paths the run reads first
```

Everything else is the declaration ADR-639 already runs: the kept file, the schedule, `paused`, and
**`CONTRACT.md` — which stays load-bearing**. For browser work it says what must be true when the run finishes
*and* how to get there, in one prose file. There is no second procedure file.

- `member` is the declarer, stamped by the door from the signed-in member. A member can put browser work only on
  **their own** browser; nobody can name another member's (ADR-645 D1: reach follows the acting member).
- `sites` is the run's scope. `BrowserOpen` on a site not listed (or a subdomain of one) is refused before it
  reaches the member's machine, in words the agent reads.
- A browser declaration's app derives as any other's; a target type with no app (csv, json) runs under Text.
- A malformed block is the problem `browser_invalid`, loud like every problem (ADR-569 D3).

### D2 — A run is a row

`runs` — one row per run, of every kind:

| Column | Meaning |
|---|---|
| `workspace_id`, `user_id` | the workspace; the member it runs as (the owner for a derive run) |
| `topic` | the declaration's folder; null for a run started in chat |
| `lane_id` | the conversation it runs in, when it runs in one |
| `kind` | `derive` (the toolless standing turn) · `browser` |
| `trigger` | `scheduled` · `manual` · `chat` |
| `state` | `queued` · `running` · `waiting` · `done` · `failed` · `stopped` |
| `waiting_on` | why it waits — today only `{"kind": "member"}`: due, and waiting for its member to run it |
| `outcome` | on `done`: `wrote` · `no_change` · `skipped`; on `failed`: the reason |
| `steps` | the acts, each the receipt ADR-662 D3 made — `{name, text, ok, record}` — plus `at` |
| `revision_id` | what it wrote to the kept file — stored, never joined by time |
| `record_path` | its record file (D3) |

It is an **act ledger**, the fourth beside `workspace_file_versions`, `execution_events` and `action_proposals`
— what happened, never workspace state (Axiom 1 holds: what a run *made* is files). `execution_events` stays the
**cost** ledger and nothing else reads it for runs.

### D3 — A declared browser run leaves a record file

At its end a browser run of a declaration writes `{topic}/runs/{YYYY-MM-DD-HHMM}.md` (UTC): when, who, how it
was started, how it ended, every step, what it wrote. Attributed `system:standing`, versioned, exportable, and
readable by the next run — which is how a run learns what the last one already did. A derive run writes no
record: the revision it made *is* its record. A run started in chat writes none: it belongs to no folder.

### D4 — Attended first: a browser run happens in its conversation

A browser run is a **lane turn** — the only place browser hands exist (ADR-662 D9, unchanged).

- **Run now** on browser work writes the run's opening message into the work's own conversation — the lane bound
  to the kept file (`artifact_path` = the target, `app` = its app, the ADR-653 R3 binding) — and the Supervisor
  opens that conversation in place. The member's page streams the turn and performs the acts; the member watches
  the steps, can stop, and can talk to it mid-run.
- **The schedule** never acts. When browser work comes due the drain opens a run `waiting` on its member —
  *due, run it now* — and advances the clock. One waiting run per declaration; a second due tick does not stack.
- **Unattended browser work** (ADR-665's option B) is **not ruled here**. It needs the extension to hold its own
  connection and a pending act kept somewhere shared; §8 carries the question with its facts.

### D5 — A browser turn in chat is a run too

The first browser act in any lane turn opens a run (`trigger: chat`); every receipt lands on it; the turn's end
closes it. One run shape for chat and for declared work — the ADR-231 graduation, now with something to
graduate: a run done in chat is the thing a member later declares.

The reply row carries `run_id`; `GET /lanes/{id}/messages` hydrates the steps from the run. The stored
`metadata.receipts` is **deleted** — migrated into runs by the migration that creates the table.

### D6 — Every member sees every run, live

`runs` is readable by every member of its workspace and published to the realtime channel (the migration 240
ceremony, RLS on). **The conversation stays private; the run is shared**: what an agent did on a site in a
member's browser is the workspace's to see, even when the authority was one member's.

Stopping is the run's own member's act, or the workspace owner's. A stopped running run ends its turn at the
next act; a stopped waiting run is dismissed.

### D7 — One run view

`RunView` — state, the member it runs as, the steps as they land, what it wrote, Stop — is the one rendering of a
run. It mounts in the Supervisor and in the shell's run tray (D9). Chat keeps drawing its own turn's steps inline,
from the same stream and, on reload, from the same run.

### D8 — The cockpit reads by run state

The Supervisor's sections become:

```
running    what is happening now                      runs: queued · running
needs-you  what is waiting on me                      runs waiting on me · recent failures · mentions
work       what standing work I have                  the roster (unchanged)
recent     what just happened                         runs: done · failed · stopped, newest first
```

`note` is **deleted**: `DECISIONS.md` has no writer (ADR-656 §8 said so) and no workspace holds one (0 rows,
2026-09-24). A declaration's detail shows its runs from `runs`; browser work's detail also holds its
conversation, where a run is started and watched.

### D9 — The run tray

The shell's top bar carries a tray when the workspace has a run going or one waiting on the viewer: a count,
and on open the live runs in `RunView`, linking to the Supervisor. It is absent when nothing runs.

## 3. What this does not do

- Act unattended, or hold a credential (§8 carries the unattended question; the sign-in question is parked in
  the analysis above).
- Queue consequential acts for approval — attended acts are immediate (ADR-662 D5; the queue is for absence,
  ADR-307 D3).
- Scope a site after the page is open. A link the agent follows off the list is not refused — the step names the
  site, so it is visible. The extension-side check is owed with the next extension release.
- Add a way to show the agent's tab from yarnnn ("show me the tab") — also an extension release.

## 4. Why a run is not a task

ADR-231 retired tasks because the agent created one per request, each with its own folder and schedule, until a
workspace was a pile of them. A run is created by the **kernel when something runs**, carries no schedule and no
folder of its own, and means nothing beyond *this occurrence*. The declaration stays the only thing a member
creates; the run is its trace.

## 5. Canon tensions, resolved

| Tension | Resolution |
|---|---|
| Axiom 1 — state lives in files | A run is an act ledger row, like `execution_events`; what it made is files, and a declared browser run's record is a file (D3) |
| ADR-411 — conversations are private | The conversation stays private; the run, a record of acts on the world, is shared (D6) |
| ADR-603 D5 — no schedule without a contract | Browser work keeps `CONTRACT.md` load-bearing (D1); ADR-665's `WORKFLOW.md` is not built |
| ADR-662 D9 — attended only | Held: a browser run is a lane turn; the schedule only raises it (D4) |
| ADR-659 D2 — the run → revision join | Replaced by a stored pointer; the time-window join is deleted |

## 6. Build order (all in this change)

1. Migration 262: `runs`, its RLS, its publication; `metadata.receipts` moved into runs.
2. `services/runs.py` — the one writer of runs and records.
3. Standing work: every run is a row; the `browser` key; due browser work waits on its member.
4. The lane turn: a browser act opens or joins a run; `run_id` on regenerate; the site scope; stop.
5. `routes/runs.py` — list, one, stop. The standing routes read runs.
6. The cockpit (D8), `RunView` (D7), the tray (D9), the browser door and the work's conversation.

## 7. Gate

`api/test_adr666_the_run.py`: the parser accepts `browser` and refuses a malformed one by name; the door stamps
the signed-in member; every standing run writes exactly one row and finishes it; due browser work opens one
waiting run and never runs; a browser act outside `sites` is refused before it reaches the client; a lane turn's
receipts land on its run and the reply carries `run_id`; `metadata.receipts` has no writer; the standing routes
read no run from `execution_events`; the time-window join is gone; the record file is written for a declared
browser run only; the cockpit declares `running · needs-you · work · recent` and no `note`.

## 8. The unattended question, carried from ADR-665

Unattended browser work needs: the extension holding an authenticated connection to the API while it is on (a
standing session in the browser); the pending act kept in shared state instead of `client_tools._TURNS` (which
is in-process and correct only on one API instance); and a stop that reaches a run nobody is watching. The
`runs` row is the shared state it would use. Ratify separately, after attended runs have been measured —
how often a run stalls, and how often a sign-in stops it.

## 9. Implementation census

| Where | What |
|---|---|
| `supabase/migrations/262_adr666_runs.sql` · `263_adr666_run_cost.sql` | `runs` + RLS + realtime; the 9 stored receipts moved; `cost_usd`. Applied and verified live 2026-09-24 |
| `api/services/runs.py` | NEW — the one writer: open · steps · finish (cost by ledger id) · raise_due · start_browser_run · stop · record file · `TurnRun` |
| `api/services/standing_work.py` | the `browser` key and site grammar; `run_standing_sweep` wraps `_sweep` in a run whose steps are its reads and write; browser work is due-raised; `BROWSER_RUN_ASK` |
| `api/services/lane_runner.py` · `client_tools.py` | the site scope before the act; stop (`bind_run` · `stop_run` · `STOPPED_*`); `ledger_ids` on `done` |
| `api/routes/lanes.py` | a browser turn is a run; `run_id` on regenerate (`_run_for_turn`); receipts hydrated on read; `find_bound_lane` |
| `api/routes/runs.py` | NEW — `GET /runs`, `GET /runs/{id}`, `POST /runs/{id}/stop`; `RunOut`, the one served shape |
| `api/routes/standing_work.py` | runs read from `runs`; the browser door and Run now; the browser start. DELETED: `_join_revision`, `_written_revisions`, `_last_runs`, `_recent_runs`, `LastRun`, `StandingRun`, the legacy ledger prefixes |
| `api/services/supervisor_state.py` | `note` DELETED — the payload is `{needs_you}` |
| `web/lib/runs/useRuns.ts` · `web/components/runs/*` | the one client store (realtime + poll floor); `RunView`; `useRunWords`; `RunTray` in the top bar |
| `web/components/supervisor/*` | the cockpit by run state; the detail's runs, sites and conversation (`WorkConversation`); the browser door and start |
| `web/components/chat-surface/LanePanel.tsx` | `startRunId` — performs a started run through regenerate |

**Owed** (`docs/SESSION-HANDOFF.md`): the extension-side site check and "show me the tab" (an extension
release); a real browser run driven end to end in a Chrome holding the published extension; §8.

## 10. Driven on production (2026-09-24)

Chrome for Testing with the extension loaded unpacked, signed in as the owner rig (`kvkthecreator@yarnnn.com`,
workspace `bf5b25a9`), English interface. Receipts are row ids in `runs` and revisions.

| Path | Result |
|---|---|
| The door → "Do something on websites" → create | `_standing.yaml` names `member: 67c5c637…` (server-stamped), revision `45672f7e` |
| Run now, in the page holding the extension | run `4381151e`: done · wrote · 47.7 s · $0.1736; revision `739746e0` attributed `member:67c5c637… via anthropic/claude-sonnet-5`; record `runs/2026-09-24-0459.md` |
| ⭐ The site scope, unprompted | the agent reached for `timeanddate.com` to learn the date — refused before the extension: *"Did not open timeanddate.com: this work may open only example.com, iana.org."* |
| Stop from the run card, mid-run | the act in flight answered "stopped", the turn ended, record written |
| Due, through the real scheduler tick | run `28f55c12` WAITING on its member, nothing performed, clock advanced to the next Monday; tray "1 run due"; Needs you → Run it took up the SAME row (waiting → queued → running → done) |
| A derive run | done · wrote · $0.0077; steps "Read inbound/web/example-com/…" · "Wrote …/summary.md"; no record file |
| RLS | owner 9 · a non-member 0 · anon 0. **Not driven**: a second member seeing another's run (the rig has no second member) |
| Retire | declarations archived, index rows dropped; files, records and runs kept |

**Defects only driving found**, each fixed with a gate arm proven RED: Run now returned the browser start
un-awaited (a 500 the browser reported as CORS) · a stopped run carried `outcome: no_change` · a Run now that
lost the claim said "nothing changed" above the run card saying the file was updated · "Done" twice on a chat run ·
the picker still asked "What should it keep current?" · the browser start's line truncated · a browser
declaration's YAML header described fetching sources.


# ADR-667 — The Supervisor is set up in conversation, and the browser is its prerequisite

> **Status**: **Accepted** (2026-09-24; operator: *"yes, aligned in full … delegate implementation details …
> singular streamlined discipline with code and docs, scoping in deletion and clean-up"*). Implemented with this
> document — §7 is the census.
> **Date**: 2026-09-24
> **Authors**: KVK (operator) + Claude (collaborator)
> **Dimensional classification** (Axiom 0): **Channel** (how a member makes work: a conversation, not a form) +
> **Identity** (whose browser a declaration names — stamped, never written).
> **Gate**: `api/test_adr667_the_supervisor_is_set_up_in_conversation.py`.

**Amends** — ADR-658 D4/D7 and Amendment 3 (the door is a conversation; the two-step modal is deleted) · ADR-666 D1
(the member stamp holds at the kernel, not only the door) · ADR-666 D4 (a taken-up run keeps its trigger) ·
ADR-666 D8 (needs-you is the viewer's) · ADR-569 D7 (conversational creation goes through the one door).
**Preserves** — ADR-662 D9 (browser hands only in an attended lane turn; nothing here acts unattended) · ADR-645 D1
(no credential moves) · ADR-639 (one drain, one declaration shape) · ADR-596 D1 (no authority on a being — the
executor stays derived from the target, §3) · ADR-666 D6 (the run is the workspace's; the conversation stays
private).
**Derivation** — [the Supervisor from first principles](../analysis/the-supervisor-from-first-principles-2026-09-20.md)
§4–5 step 3, and the 2026-09-24 audit reported in-session (scorecard receipts are in §1).

## 1. The problem

Measured 2026-09-24 against HEAD `085c6f9` and production:

1. **The Supervisor's agent could not be met, and did not know its job.** Its registration says it is *"met
   there"* — in the Supervisor pane — but the pane mounted no conversation for it: **one** Supervisor-bound lane
   exists in production, from 2026-09-18. Its job text was still ADR-656's (splitting threads, a `supervisor/`
   folder for decisions) and never mentioned standing work, runs or the browser.
2. **Setting work up was a form**, a picker and a two-step modal (`StartPicker` + `NewStandingWorkModal`, ~640
   lines), while the agent that could hold the conversation sat unused beside it.
3. **The conversational path could not declare browser work, and had no stamp.** The `declaring-standing-work`
   skill hand-wrote `_standing.yaml` through `WriteFile` and never named the `browser` key. Its member must be
   stamped by the server, so teaching the skill would not have been enough.
4. **ADR-666 D1's rule held at one door.** The door stamped the signed-in member; the parser checked only that
   `browser.member` looked like a uuid, so any writer of the file could name anyone — and `raise_due` opened a
   run waiting on a non-member forever.
5. **Attention disagreed with itself.** Needs-you listed every member's waiting run; the tray listed the
   viewer's. The band read *"Supervisor looks after this."* while a run was due on the viewer, and *"Supervisor
   is updating X"* for browser work done by the Text app's agent in one member's browser.
6. **A schedule-raised run read `manual`** once its member took it up (production run `28f55c12`).

## 2. Decisions

### D1 — The Supervisor is set up in conversation

The Supervisor pane holds its agent's conversation — the app-bound lane (ADR-653 R3, `app: supervisor`, no
artifact), found or created by the pane. A member says what keeps happening; the agent sets it up. The two-step
door is **deleted**. The pre-shaped starts (ADR-658 D7, `GET /api/standing/starts`, unchanged) become the
conversation's opening suggestions.

**Setup by doing.** For work on websites the agent does the task once, now, in the member's browser — an
ordinary chat run (ADR-666 D5), receipted and visible to the workspace — and then offers to keep doing it,
declaring what it just did: the sites it used, the file it kept, the contract written from the steps. A run done
in chat is the thing a member declares (ADR-666 D5, ADR-231's graduation) — now the path, not a possibility.

### D2 — One door, two callers: the routes and `DeclareWork`

`services/standing_door.py` holds the composer (`compose_standing_yaml`, moved from the routes), **declare**
and **revise**, and the refusal words. `POST`/`PATCH /api/standing` and the lane tool **`DeclareWork`** both call
it; neither formats YAML of its own. Attribution follows the caller: the routes write as the member; the tool
writes as `member:{id} via {model}` with the member's identity stamped.

- `DeclareWork` joins the lane's uniform tool set (ADR-467 D4) as a consequential verb. `sites` present makes it
  browser work **in the acting member's browser** — the server stamps who; no caller names a member.
- `WriteFile` and `EditFile` refuse a `_standing.yaml` path, naming `DeclareWork`. One way to declare. Retiring is
  still a delete (`DeleteFile`, or the route), unchanged.
- The skill says `DeclareWork`, and names the browser.

### D3 — The member stamp holds at the kernel

Discovery asks the one reach function (`principal_reaches_workspace`) whether a declaration's `browser.member`
reaches its workspace. One that does not is the problem **`browser_member_unknown`** — loud, and never raised as
a waiting run. An undecidable check leaves the declaration as it was (a dead socket is not an answer about
anyone's grant).

### D4 — The browser is the prerequisite for setting up and running, never for seeing

The pane asks the page for its browser hands (`browserHands()`, ADR-662 D15). Without them, the conversation
column opens on **the install step** — what the extension is for, *Add to Chrome* when the store listing exists,
*Switch it on* when it is installed but off — and a quieter **continue without it**, which opens the same
conversation for work that reads files and websites but acts on none. The work, its runs and their records stay
open to every member with or without the extension (ADR-666 D6): the run is the workspace's; the live stream is
the member's own conversation and was always private.

⚠️ **The switch is `storeUrl`, not the app stage.** ADR-592's stage is per app; staging the Supervisor would hide
the runs from members who only need to see them. The install step names the extension either way and offers
*Add to Chrome* only when `CHROME_EXTENSION.storeUrl` is set — which ADR-661's tripwire holds until ADR-662 is
Accepted. One switch, already guarded.

### D5 — The agent's job, re-derived

The Supervisor's job text says what it is now: the author of the member's standing work. It sets work up (by
doing it once when it is on websites), reads the roster and each piece's last run from a compact state block the
posture carries per turn, explains a failure from the run's record, and changes or retires work through the door.
It performs no piece of standing work itself — runs happen in each piece's own conversation (ADR-666 D4). The
`supervisor/` folder is deleted from the job: nothing wrote there (ADR-666 D8).

### D6 — Attention is the viewer's, and the band follows the ledger

Needs-you (amends ADR-666 D8): runs **waiting on the viewer** (`user_id` = viewer — the tray's rule, now one
predicate for both), the newest failure of each piece of work (a failure is the work's, so every member sees
it), and the viewer's mentions.

The band: **working** names who does it — *"Updating X."* for a derive run, *"{member}'s browser is working on
X."* for a browser run; **raising** names a run due on the viewer first (*"X is due — run it."*), then a
declaration that cannot run; **resting** is unchanged.

### D7 — A run keeps its trigger

Taking up a waiting run (`start_browser_run`) moves it to `queued` and keeps `trigger: scheduled` — the schedule
raised it, the member performed it, and the row says both (`waiting_on` cleared, `lane_id` set).

## 3. Why the Supervisor's agent may run a trial

ADR-658 D3 and ADR-659 D3 say the Supervisor app executes no standing work — the executor of a declaration is
derived from its target's app. A trial run in the Supervisor's conversation is not standing work: it is a chat
turn by the member's hands (ADR-645 D1), recorded as a chat run with no topic. What it becomes, once declared, is
run by the derived executor in the work's own conversation. The distinction ADR-639 drew is intact.

## 4. What this does not do

- Run browser work unattended (ADR-666 §8 is still unruled; the extension being always on is not attendance).
- Make the extension installable — the Web Store review and ADR-662's ratification are the operator's (§6).
- Add a declaration kind, a table or a route.

## 5. Gate

`api/test_adr667_the_supervisor_is_set_up_in_conversation.py`: the door module is the one composer and the routes
and `DeclareWork` both call it; the tool stamps the acting member and refuses a caller-named one; `WriteFile` and
`EditFile` refuse `_standing.yaml`; discovery marks a non-member `browser_member_unknown` and `raise_due` opens no
run for it; `start_browser_run` keeps the trigger; the posture names standing work, runs and `DeclareWork` and
no longer names `supervisor/`; the skill names `DeclareWork` and the browser; the pane mounts the Supervisor's
conversation and the install step; the deleted door is gone; needs-you filters waiting runs by viewer; the band
names a browser run's member.

## 6. Owed

- **The operator**: ADR-662's ratification (one run in the operator's own Chrome), then `storeUrl` once the Web
  Store review clears. Until then the install step names the extension without a link.
- ADR-666's owed items stand, one narrowed: a second member **seeing** another's run (the live stream was never
  theirs to see).

## 7. Implementation census

| Where | What |
|---|---|
| `api/services/standing_door.py` | NEW — `compose_standing_yaml` (moved), `declare`, `revise`, `DoorRefusal`, the refusal words |
| `api/routes/standing_work.py` | create and PATCH call the door; DELETED: the local composer, `_refuse`'s table, the create/revise bodies |
| `api/services/primitives/declare_work.py` | NEW — `DeclareWork` |
| `api/services/primitives/workspace.py` | `WriteFile` / `EditFile` refuse `_standing.yaml` |
| `api/services/lane_runner.py` · `primitives/registry.py` · `permission.py` | the tool on the lane surface, its handler, its class |
| `api/services/standing_work.py` | `browser_member_unknown` at discovery |
| `api/services/runs.py` | `start_browser_run` keeps the trigger; `raise_due` refuses a problem declaration |
| `api/services/apps/supervisor.py` | the job re-derived; the per-turn state block; `SUPERVISOR_HOME` DELETED |
| `api/services/skills/declaring-standing-work/SKILL.md` | `DeclareWork`; the browser |
| `web/components/supervisor/SupervisorSurface.tsx` | the conversation column and the install step |
| `web/components/supervisor/Conversation.tsx` | `WorkConversation` generalised: a given lane, or the app's own |
| `web/components/supervisor/BrowserGate.tsx` | NEW — the install step |
| `web/components/supervisor/SupervisorSection.tsx` · `MinderBand.tsx` | D6 |
| DELETED | `StartPicker.tsx`, `NewStandingWorkModal.tsx`, `WorkConversation.tsx` (renamed), their catalog keys |

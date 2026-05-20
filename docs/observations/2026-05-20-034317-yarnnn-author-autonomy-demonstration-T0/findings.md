# Findings — T0 (yarnnn-author autonomy demonstration baseline)

> **No interpretation at T0.** This folder captures the *before-snapshot* of the autonomy demonstration window. Findings belong in subsequent T+24h / T+48h observation folders after the system has been observed running autonomously.

What this folder establishes:

1. **T0 substrate state captured.** See `PLAYBOOK.md` for the full state declaration + setup history.
2. **No diff to interpret.** Baseline IS endpoint at this instant; `substrate-diff.md`, `decisions.md`, `proposals.md`, `transcript.md`, `token-usage.md` show empty diffs (no events since baseline was taken because baseline IS now).
3. **The autonomy hypothesis being tested:**
   - The Reviewer + System Agent + Orchestration substrate produces material behavior (recurrence fires, judgment_log writes, standing_intent updates, possibly substrate amendments) **without operator-on-behalf interjection** during the elapsed window.

What to look for at T+24h / T+48h:

- pre-ship-audit reactive fire on the seeded `governance-as-trust` piece — fire-or-not is itself a binary finding.
- Scheduled recurrence fires: 3-4 expected within 48h.
- Reviewer-authored revisions on `review/judgment_log.md` + `review/standing_intent.md` substrate.
- Any operator-canon edit (rare, would be highly informative — evaluate against ADR-295 D1-D4 Edit Checklist).
- Any wake failures (round-budget exhaustion, infrastructure errors, missing-substrate errors).

Cross-reference: `PLAYBOOK.md` here, `docs/observations/2026-05-20-034317-adr-292-gap-finding.md` (sibling Hat-A finding from setup work).

---

## Interim note — T+~26m liveness check (2026-05-20T04:09Z server-time)

Per the re-framed cadence in `docs/observations/sessions/alpha-author-autonomy-loop.md` (event-anchored rather than wall-clock T+24h ladder), a read-only liveness check ran shortly post-T0. **No snapshot folder** — this is a sanity probe + diagnostic audit, not a capture. Recorded here because the audit surfaced a structural finding worth Hat-A attention.

### Correction on wall-clock framing

The initial framing in conversation referenced "T+~9h" against my session-local clock, but the database server's `now()` is **2026-05-20T04:09Z**, ~26 minutes after T0 (2026-05-20T03:43Z), not ~9 hours. The `outcome-reconciliation` next-due time (`2026-05-20T05:00Z`) is **51 minutes in the future, not 7 hours in the past**. The persona was activated very recently in real wall-clock time; the audit is "T+~26m," not mid-window. This corrects an interpretation error in the initial liveness write-up.

### Expected at T+~26m (corrected expectations)

At T+~26m, expectations are necessarily modest:
- `outcome-reconciliation` (scheduled `0 5 * * *`, next due 05:00Z) — has not yet had a chance to fire; due in ~51 minutes.
- `corpus-coherence-check` — next Mon/Thu 12:00Z; first opportunity is Thu 2026-05-21T12:00Z.
- `pre-ship-audit` (`schedule: null`, declared reactive on `ready_for_review`) — *should* have fired on the T0 substrate-seeding event that wrote `status: ready_for_review` to `governance-as-trust/profile.md`. This is the **only** expected fire by T+~26m, and it didn't happen.

### Observed

- **Zero `execution_events` rows for user `0b7a852d-...` since T0.** Last event in the table is `outcome-reconciliation` at 2026-05-19T05:04:02Z — *prior* to the demo window.
- **`tasks.next_run_at` for `outcome-reconciliation` is `2026-05-20T05:00:00+00`** — ~51 minutes in the future. Scheduler is *not* stalled here; the time has not yet arrived. **Prior interim-note interpretation #1 (scheduler stall) was wrong** and is retracted below.
- **Cross-user scheduler health is normal.** Other users have fired 38 reactive cron-anchored events in the 6 hours preceding T0 (track-account, track-regime, track-universe, mirror-signal-state during 23-02 UTC). The scheduler cron is alive and dispatching across workspaces.
- **No scheduled recurrences are past-due anywhere in the system** (DIAG-4: zero rows with `next_run_at < now() AND not paused`). The scheduler's pointer-advance logic is operating normally — `last_run_at` updates and `next_run_at` advances as cron fires complete.
- **`pre-ship-audit` row has `schedule: NULL`, `next_run_at: NULL`, `last_run_at: NULL`** — never fired in this workspace's lifetime. Same `schedule: NULL` shape exists for `pre-ship-audit` on all three alpha-author personas (yarnnn-author, netflix-script-author, korea-thriller-shorts) and `trade-proposal` on all three alpha-trader personas. **Across all six personas + all time, neither `pre-ship-audit` nor `trade-proposal` has ever produced an `execution_events` row.**
- **Substrate intact**: `_autonomy.yaml` still `delegation: autonomous`; seeded piece still `status: ready_for_review`; content lengths unchanged.

### The empirical finding

Code-level grep of the api/ tree:

- `grep -rn "ready_for_review" api/` — **zero hits.**
- `grep -rn "pre.ship.audit\|pre_ship_audit" api/` — **zero hits.**

Cross-user audit across all six personas (alpha-author × 3 + alpha-trader × 3) confirms:

- Only two recurrence slugs in the entire database have `schedule: null`: `pre-ship-audit` (3 users) and `trade-proposal` (3 users).
- **Neither has ever produced an `execution_events` row across all of time.**
- Cron-anchored wakes are healthy: 38 fires across other users in the 6h before T0 (`track-*`, `mirror-signal-state`, `outcome-reconciliation`, `corpus-coherence-check`, etc.).

The kernel has two wake paths today (per FOUNDATIONS Axiom 4 v8.5):

1. **Reactive** — a `judgment`-mode recurrence fires on schedule via the recurrence walker, OR a specialized handler decides to wake (today only `on_proposal_created` in `review_proposal_dispatch.py`).
2. **Addressed** — operator or MCP caller posts to the feed surface.

Per FOUNDATIONS Axiom 4 + ADR-263 D-statement (verbatim): **"There is no derived-from-substrate wake mechanism. Authoring intent is the wake signal."**

### Reading the bundle declarations under canon

The alpha-author `_recurrences.yaml` comments on `pre-ship-audit` say `# reactive — fires on draft state change via FireInvocation`. The alpha-trader `_recurrences.yaml` comments on `trade-proposal` say `# reactive — fires on signal trigger via FireInvocation`. **The bundles themselves declare the wake mechanism: `FireInvocation` from an upstream wake.**

This is the canon model:

- `schedule: null` + `mode: judgment` recurrences exist as *named, parametrized invocation handles* the upstream Reviewer wake can call.
- The wake chain is: cron-anchored wake → Reviewer reads substrate → decides to dispatch → `FireInvocation(slug="pre-ship-audit")` → second Reviewer wake with the dispatched recurrence's prompt as envelope.
- There is no kernel-side substrate watcher because Axiom 4 explicitly prohibits one.

### The actual gap (corrected diagnosis)

**The upstream FireInvocation chain is not closing.** Two specific instances:

1. **alpha-author**: nothing in the bundle's other recurrences (`outcome-reconciliation`, `corpus-coherence-check`, `revision-audit`, `weekly-corpus-review`, `quarterly-voice-audit`) instructs the Reviewer to detect `ready_for_review` drafts and `FireInvocation("pre-ship-audit")`. The chain has no upstream link. The bundle declared the *handle* without declaring the *caller*.

2. **alpha-trader**: `signal-evaluation` is supposed to be the caller — when a signal fires, the Reviewer in signal-evaluation should `FireInvocation("trade-proposal")`. Empirically `signal-evaluation` has fired 3 times across 2 users, but `trade-proposal` has fired 0 times. Three possible sub-causes (Hat-A debugging needed to discriminate): (a) signal-evaluation never reaches a "fire" decision (no triggering signals); (b) it reaches the decision but doesn't actually call FireInvocation; (c) it calls FireInvocation but the row insert fails or the dispatcher rejects it. Whichever, the chain isn't closing in practice.

### Retracted earlier interpretation

An earlier draft of this interim note recommended building a "substrate-event dispatcher" — a kernel daemon that would watch `workspace_files` mutations and fire matching recurrences. **That recommendation is retracted.** It would have introduced exactly the "derived-from-substrate wake mechanism" FOUNDATIONS Axiom 4 + ADR-263 D-statement explicitly prohibits. The canon answer was always option (c) from that draft — FireInvocation-only dispatch — which is what the bundles already declare via their inline comments.

The discipline rule that worked: CLAUDE.md "check ADRs first" — FOUNDATIONS Axiom 4 had already decided this question. Reaching for a new kernel capability before reading the canon is the failure mode the rule exists to prevent.

### Retracted earlier cleanup-discipline packet

The "Cleanup discipline for the dispatcher ADR" subsection (six cleanup candidates A–F, four phase-plan discipline rules) is **also retracted** — it was scoped to a dispatcher ADR that should not be drafted. Some of the candidates may still be valid as small standalone cleanup work (e.g., audit cron-disguised polling shapes; clarify `trigger_type` column-value semantics) but they belong in separate, smaller scopes that don't depend on a kernel-capability ADR. Listing them as a "packet" tied to a dispatcher ADR would steer Hat-A toward drafting an ADR that violates canon.

### System-canon recommendations (Hat-A work — NOT done in this thread)

1. **Close the FireInvocation chain in the alpha-author bundle.** Two options worth weighing:
   - **(a)** Add a `daily-draft-sweep` cron-anchored recurrence (e.g., `0 6 * * *`) whose prompt instructs the Reviewer to list drafts with `status: ready_for_review` and `FireInvocation("pre-ship-audit")` for each. Honest, declarative, lives in `_recurrences.yaml`.
   - **(b)** Extend `outcome-reconciliation`'s existing daily prompt to include a "before reconciling, check for any `ready_for_review` drafts and dispatch pre-ship-audit for each" clause. Reuses existing wake; no new recurrence.

   Either honors Axiom 4 (Reviewer-authored upstream wake calls FireInvocation; no kernel-side substrate watching). (b) is cheaper to ship and proves the model; (a) is cleaner separation if there are multiple kinds of "substrate-state sweep" the bundle eventually needs.

2. **Debug the alpha-trader FireInvocation chain.** `signal-evaluation` exists; `trade-proposal` never fires. Hat-A diagnostic needed to discriminate between (a) the Reviewer in signal-evaluation never reaching a "propose" decision under current signal conditions, (b) it reaches the decision but the prompt doesn't actually call FireInvocation, (c) FireInvocation fires but the dispatched wake fails silently. This is a real bundle-prompt or Reviewer-instruction debugging task, not a kernel capability question.

3. **Audit bundle declarations for FireInvocation-chain completeness.** Any recurrence with `schedule: null` MUST have an upstream caller declared somewhere — either in another bundle recurrence's prompt, or in a specialized handler. Currently the convention is documented only in inline YAML comments. A short Hat-A note in `docs/architecture/recurrences.md` (or similar) making the convention explicit would close the bundle-author confusion that produced this finding's class of bug.

4. **Optional small cleanup ADR** (only if Hat-A drafting consensus warrants): trigger-taxonomy-vocabulary hygiene — clarify `execution_events.trigger_type` value semantics, document the `schedule: null` + FireInvocation-only contract, audit cron-disguised polling shapes (e.g., `mirror-signal-state` at `@every 1min`) for whether they're really FireInvocation-only recurrences that should be made declaration-explicit. Small scope; no new kernel capability; no FOUNDATIONS amendment. Optional because items 1+2 may close the actual operator-visible gap without needing the cleanup formalized.

These four items are surfaced for the operator. Hat-A work — bundle prompt edits, Reviewer-instruction debugging, possibly a small cleanup ADR — happens in `api/` / `docs/adr/` / `docs/programs/` commits, not here.

#### Retracted: cleanup-discipline packet for a dispatcher ADR

An earlier draft of this note included a six-item cleanup packet scoped to a substrate-event dispatcher ADR. That ADR was retracted (see "Retracted earlier interpretation" above — it violates FOUNDATIONS Axiom 4). The cleanup packet is retracted with it because the packet's framing presupposed the dispatcher's existence. Some individual cleanup candidates may still be valid as small standalone work (Recommendation #4 above names this as an optional small-scope ADR). They should not be re-grouped as a "packet" tied to a kernel-capability addition that canon prohibits.

### Retraction

The earlier conversational interpretation that "the scheduler appears stalled" was wrong. Scheduler is healthy across all users; `outcome-reconciliation` for yarnnn-author is correctly waiting for 05:00Z (~51 minutes future). The real finding is the substrate-event reactive-dispatch gap, not a scheduler bug. Retracted in-place to keep this note as the singular accurate record of the audit.

### Next capture

Event-anchored per the re-framed cadence. The next *expected* fire is `outcome-reconciliation` at 2026-05-20T05:00Z (~51 min from this note). If it fires, open `post-outcome-reconciliation` snapshot folder + capture. If it doesn't fire on time, the scope of the finding expands. Either way, the `pre-ship-audit` lane is now expected to remain silent until the kernel-side architectural decision (recommendation #1 above) ships.

— Liveness check + diagnostic audit by Claude/Sonnet, Hat B, no substrate writes to the workspace.

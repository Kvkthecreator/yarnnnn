# Interruption Surface Smoke Checklist

> **Scope**: manual end-to-end validation of the operator's interruption
> surface — the autonomy chip + pause modal (Commit G) + Stop button
> (Commit H), built on the now-functional autonomy gate (Commit F).
> **Backed by**: `api/test_commit_f_autonomy_alignment.py` (gate verifies
> backend invariants automatically; this checklist verifies the surfaces
> the operator actually touches).
> **Date**: 2026-05-11
> **Cadence**: run after every push that touches `web/components/feed-surface/`,
> `web/components/tp/FeedPanel.tsx`, `web/contexts/NarrativeContext.tsx`,
> `web/lib/content-shapes/autonomy.ts`, or the autonomy/cancellation
> backend paths (`review_policy.py`, `reviewer_agent.py`,
> `routes/feed.py::cancel_active_loop`).

---

## Why this exists

The interruption surface spans 6 commits (C, F, G, H + the substrate-as-bus
hardening that preceded them). It crosses backend (Reviewer cooperative
cancellation, autonomy gate), real-time infrastructure (Supabase Realtime
subscriptions on `session_messages` + `chat_sessions`), and FE state
(NarrativeContext loop-active derivation, useAutonomy pause/resume).

There is **no FE test infrastructure** in this repo. The Python regression
gate (`test_commit_f_autonomy_alignment.py`) covers backend contracts;
this checklist covers everything the operator can break by clicking.

Run it after each architecturally-relevant push. ~30-40 min focused
session. Don't ad-hoc click — follow the steps in order; the flows are
designed so each one's setup is the prior flow's teardown.

---

## Pre-flight (5 min)

1. Backend deploy is live on Render (check `yarnnn-api` last-deploy timestamp).
2. FE deploy is live on Vercel (check production URL).
3. You are logged in as the alpha-trader-2 operator (or another workspace
   you can safely mutate). For first-pass testing, use a workspace that
   does NOT have a real platform connection — the `setPause` and Stop
   actions write substrate but don't fire real trades.
4. Open the browser DevTools network tab. You'll watch for a few specific
   requests during the flows below.
5. Run the gate locally: `cd api && python test_commit_f_autonomy_alignment.py`
   should print `13/13 passed`. If not, fix the gate before manual testing
   (a backend contract regression masks operator-facing bugs).

---

## Flow 1 — Autonomy chip in feed header (Commit G)

**What this validates**: the chip is in the right frame, the pause modal
opens, the four duration presets work, the chip flips to paused state,
and the substrate persists across page reloads.

```
[ ] 1.1  Open /feed.
         Observe AutonomyHeaderChip in the top-right of the surface
         identity header (next to the filter + context buttons,
         right of the "yarnnn" logo).

[ ] 1.2  Composer bottom toolbar shows ONLY [+] and [send].
         No "Bounded ⌄" chip alongside.
         (Pre-Commit-G that chip lived here; if it's still there,
         either you're on a stale FE deploy or G was reverted.)

[ ] 1.3  Chip label matches the workspace's _autonomy.yaml content.
         For alpha-trader (canonical state): "Bounded · $200" with
         shield-alert icon (amber-tinted).
         For a fresh workspace: "Manual" (gray).
         For autonomous: "Full auto" with shield-check (primary tint).

[ ] 1.4  Click the chip. Modal opens with:
         - Title "Autonomy"
         - Subtitle: "How much explicit approval each Reviewer-approved
           action requires."
         - Pause section (top, with optional reason input + 4 preset
           buttons: 1 hour / 4 hours / Until end of day / Indefinite)
         - Delegation section (bottom, with Manual / Bounded / Autonomous
           radio-button-style options; current selection has primary tint)

[ ] 1.5  Type "testing pause flow" into the reason input.
         Click "1 hour" preset.
         Modal closes. Chip flips to amber "Paused until <1h-from-now>".
         DevTools network tab shows: PATCH /api/workspace/file (writeShape
         to _autonomy.yaml). Response 200.

[ ] 1.6  Refresh the page (cmd-R / ctrl-R).
         Chip still shows the paused state. (Substrate persisted; FE
         re-reads it on mount via useAutonomy.)

[ ] 1.7  Click the (paused) chip. Modal opens. Top section is now an
         amber state-card showing:
         - "Paused until <timestamp>" with the pause icon
         - Reason "testing pause flow" beneath
         - "Resume autonomy" button
         Delegation section is dimmed/disabled (pause supersedes).

[ ] 1.8  Click Resume autonomy.
         Modal closes. Chip flips back to active state ("Bounded · $200"
         or whatever the prior delegation was).
         DevTools shows another PATCH /api/workspace/file.

[ ] 1.9  Click chip again. Modal back to default (no pause card; all
         duration presets visible; delegation section enabled).
         Click "Indefinite". Chip flips to "Paused indefinitely".
         (Year-2099 sentinel timestamp; never auto-expires.)

[ ] 1.10 Resume autonomy via the modal. Chip back to active.
```

**Failure modes to watch for**:
- Chip in wrong location (still in composer) → FE deploy stale or G reverted
- Modal opens but shows old 4-value enum (Manual / Assisted / Bounded autonomous / Autonomous) → FE deploy stale or F reverted
- PATCH returns 4xx → backend rejects the write (likely WriteShape contract violation; check api logs)
- Chip stays unpaused after PATCH 200 → useAutonomy not reading paused_until (parse() bug); check `web/lib/content-shapes/autonomy.ts`

---

## Flow 2 — Stop button on operator's own send (Commit H, path A)

**What this validates**: the Send button toggles to Stop while the
operator's own sendMessage stream is in flight, clicking Stop aborts
the stream and the Reviewer exits within 1-2 rounds.

```
[ ] 2.1  Composer is in idle state (Send icon, primary color).

[ ] 2.2  Type a long-running prompt: "Research recent moves in the
         semiconductor sector across the web in detail and summarize
         what changed this week."
         Hit Send (or press Enter).

[ ] 2.3  IMMEDIATELY observe the bottom toolbar:
         - Send icon disappears
         - Square (Stop) icon appears in its place (foreground color,
           filled square)
         - Hover tooltip: "Stop the Reviewer's in-flight Loop"

[ ] 2.4  Wait ~3 seconds (let a tool round or two start). Then click Stop.

[ ] 2.5  Observe within 1-2 seconds:
         - Stop icon disappears, Send returns
         - Status returns to idle
         - The Reviewer's last partial output may still be visible in
           the feed (substrate-as-bus: writes already committed are
           preserved; only the next round was skipped)

[ ] 2.6  DevTools network tab during step 2.4 should show:
         - The /api/feed POST stream gets aborted (red entry, status 0
           or "(canceled)")
         - A POST /api/feed/cancel — status 200, response includes
           applied: true and a session_id

[ ] 2.7  Open /activity and find the most recent execution_event for
         this session. status should be `success` (the Reviewer
         exited cleanly with stand_down, not failure).

[ ] 2.8  Open /context?path=/workspace/review/decisions.md.
         Most recent entry should NOT be a stand_down for the
         interrupted turn (addressed turns don't write decisions.md
         entries — only proposal verdicts and recurrence-fires do).
         If the interrupted turn DID emit substrate writes mid-loop
         (e.g., it called WriteFile), those are present — that's
         expected, not a bug.
```

**Failure modes**:
- Send button doesn't toggle to Stop → loopActive derivation broken;
  check NarrativeContext.tsx; verify `status.type !== 'idle'` during stream
- Stop button visible but click does nothing → stopActiveLoop wired
  incorrectly; check the click handler in FeedPanel.tsx
- Cancel POST returns 4xx → backend route broken; check api/routes/feed.py
- Reviewer keeps running for 30+ seconds after click → cooperative
  check not running between rounds; check api/agents/reviewer_agent.py
  per-round `_check_session_cancellation` call

---

## Flow 3 — Stop button on autonomous wake (Commit H, path B — the harder one)

**What this validates**: the Stop button surfaces during a cron-fired or
Reviewer-fired autonomous Loop wake (where the operator's browser doesn't
have an HTTP stream to abort), the server-side cooperative cancel kicks
in via the cancellation_requested flag, and the Reviewer exits within
~1-2 rounds.

This is the trickier flow because the trigger is server-side, not
operator-initiated. Easiest setup: use Schedule or FireInvocation in
chat to manually fire a judgment recurrence.

```
[ ] 3.1  Composer is in idle state.

[ ] 3.2  In the composer, type: "Fire morning-reflection now."
         (Or any judgment-mode recurrence in your workspace's
         _recurrences.yaml — check via /schedule.)
         Hit Send.

[ ] 3.3  YARNNN's response should fire the recurrence via FireInvocation
         primitive. Within ~5-10s, you'll start seeing System Agent
         narration bubbles arriving on the feed (Reviewer's tool calls
         on its own behalf).

[ ] 3.4  IMMEDIATELY when you see the first System Agent bubble arriving,
         observe the composer:
         - Stop button (Square) is visible — even though your own send
           completed
         - This is the realtime-recent detection: lastRealtimeActivity
           was just updated by useSessionMessagesRealtime

[ ] 3.5  Click Stop.

[ ] 3.6  Observe within ~1-3 seconds (Reviewer checks the flag at the
         top of every round):
         - Stop button returns to Send
         - Realtime narration arrivals stop
         - The Reviewer's mid-loop substrate writes (if any) are
           preserved — substrate-as-bus invariant

[ ] 3.7  Open /context?path=/workspace/review/decisions.md.
         Look for a `--- recurrence-fire ---` entry timestamped just now,
         with reasoning containing "Operator interrupted the in-flight
         Loop via the Stop affordance."

[ ] 3.8  Open /activity. The execution_event for the recurrence should
         show status=success (clean stand_down exit, not failure).
```

**Failure modes**:
- Stop button never appears → realtime hook not delivering; check
  Supabase Realtime publication for session_messages
  (`SELECT * FROM pg_publication_tables WHERE tablename = 'session_messages';`)
  + check browser console for WebSocket errors
- Stop button appears but Reviewer keeps running → cooperative check
  not finding the session; verify `find_active_workspace_session`
  returns the correct session_id for this user
- decisions.md doesn't get the "Operator interrupted" entry → the
  Reviewer might be exiting via a different code path; check the
  per-round check in reviewer_agent.py

---

## Flow 4 — Pause persists across cron fires (Commit F+G integration)

**What this validates**: setting paused_until via the chip actually
prevents the auto-execute gate from firing, end-to-end. This is the
"is the autonomy mode wired up correctly" question that motivated
Commit F.

```
[ ] 4.1  Pre-condition: workspace has at least one judgment-mode
         recurrence with a pending proposal expectation. alpha-trader's
         signal-evaluation works.

[ ] 4.2  Set autonomy to bounded with a high-enough ceiling that
         proposals would normally auto-execute (e.g., $20,000).
         Use the chip → modal → Bounded.

[ ] 4.3  Pause autonomy via the chip → modal → "1 hour" preset.
         Reason: "testing pause persistence."

[ ] 4.4  In the composer, type: "Fire signal-evaluation now."
         (Or whatever recurrence in your workspace produces an action
         proposal that would auto-execute under the prior settings.)
         Hit Send.

[ ] 4.5  Wait for the recurrence to complete and produce its proposal.

[ ] 4.6  Open /context?path=/workspace/review/decisions.md.
         The recurrence-fire entry should show the Reviewer rendered
         its verdict, and the resulting proposal entry's outcome
         should be `pending_operator` (not `executed`) with reason
         containing "autonomy_paused until <timestamp>".

[ ] 4.7  Lift the pause via the chip → Resume autonomy.

[ ] 4.8  Fire the same recurrence again. This time the verdict should
         auto-execute (assuming bounded + within ceiling).

[ ] 4.9  Verify in /activity that two execution_events landed: the
         first with the proposal pending, the second with execution
         completed.
```

**Failure modes**:
- Proposal auto-executes despite pause → pause field not being read;
  this is the original Commit F defect re-introduced. Run the Gate 1
  Python test to confirm; if Gate 1 passes but the surface fails,
  there's a serialization round-trip bug between FE writes and BE reads.
- decisions.md never shows the recurrence-fire entry → either the
  Reviewer didn't run (substrate write path broken — check
  `append_recurrence_fire`) or the recurrence didn't fire at all
  (check the dispatcher — `invocation_dispatcher.py`)

---

## Flow 5 — End-to-end approve flow (Commits A+B+C+H integration)

**What this validates**: the full operator→Queue→modal→approve→executed→
audit pipeline. Validates the Commit C unification (cockpit modal
opens via the same useProposalModal as the chat-stream chip) plus
the audit-first transactional pattern from Commit C LB-3.

```
[ ] 5.1  Set autonomy to MANUAL via the chip. (We want every proposal
         to defer.)

[ ] 5.2  Trigger any Reviewer-fires-a-proposal flow. Easiest: in chat,
         "Propose a small NVDA buy as a test" (or similar
         workspace-relevant ProposeAction).

[ ] 5.3  Wait for the Reviewer to render its verdict. The proposal
         should land in:
         - The chat feed (inline ProposalCard chip — ProposeAction
           narration includes proposal_id; DD-4 from Audit pass 2)
         - The cockpit Queue (TrackingFace's "Pending decisions"
           section)
         - /work proposal-related views (if applicable)

[ ] 5.4  Click the proposal IN THE COCKPIT (TrackingFace pending row).
         Modal should open showing:
         - Rationale
         - Expected effect
         - Inputs (action_type-keyed renderer per DD-6 — for trading,
           an "Order ticket" grid with Symbol/Side/Quantity/etc.)
         - Reviewer reasoning
         - Reject + Approve buttons

[ ] 5.5  This is the SAME modal the chat-stream ProposalCard would
         open (Commit C LB-2 unification). Verify by closing the modal,
         scrolling up to find the proposal in the chat feed (the
         InlineProposalChipById should render an inline chip), and
         clicking THAT chip — it should open the same modal.

[ ] 5.6  Click Approve.

[ ] 5.7  Open /context?path=/workspace/review/decisions.md.
         Look for TWO entries timestamped within seconds of each
         other (audit-first transactional pattern from Commit C LB-3):
         - First: outcome="executing" with reason containing
           "Operator confirmed; dispatching to execution layer."
         - Second: outcome="executed" with reason starting
           "Execution succeeded."

[ ] 5.8  If your workspace has a real platform connection, verify the
         action actually fired (e.g., Alpaca paper trade in the broker
         account). If not, the test passes on the substrate evidence
         alone.
```

**Failure modes**:
- Cockpit row clicks don't open modal → useProposalModal not wired
  in TrackingFace; check `web/components/library/faces/TrackingFace.tsx`
- Modal opens but shows different fields than chat-stream version →
  ProposalDetail component drift; both surfaces should mount the
  same component
- Only one entry in decisions.md (no "executing" intent) → audit-
  first pattern was reverted; check
  `api/services/primitives/propose_action.py::handle_execute_proposal`

---

## Post-test: production observation

After running the smoke checklist + verifying the Python gate, the
final layer is alpha-trader-2 actually running for a paper-trading day.

**Queries to run the next morning** (against production via psql with
the connection string in `docs/database/ACCESS.md`):

```sql
-- Did any Reviewer wake exit via the operator-interrupted path?
SELECT created_at AT TIME ZONE 'America/Los_Angeles' AS la_time,
       slug, status, error_reason
FROM execution_events
WHERE user_id = '<the operator user_id>'
  AND created_at > now() - interval '24 hours'
  AND error_reason IS NOT NULL
ORDER BY created_at DESC;

-- Did the auto-execute gate fire correctly?
SELECT created_at AT TIME ZONE 'America/Los_Angeles' AS la_time,
       action_type, status, approved_by, reviewer_identity
FROM action_proposals
WHERE user_id = '<the operator user_id>'
  AND created_at > now() - interval '24 hours'
ORDER BY created_at DESC LIMIT 20;

-- Were any actions blocked by autonomy_paused?
SELECT created_at AT TIME ZONE 'America/Los_Angeles' AS la_time,
       action_type, status, rejection_reason, execution_result
FROM action_proposals
WHERE user_id = '<the operator user_id>'
  AND created_at > now() - interval '24 hours'
  AND (rejection_reason ILIKE '%paus%' OR execution_result::text ILIKE '%paus%');
```

The substrate is the ground truth. If something feels off in the live
operation, these queries surface what actually happened across all
three interruption modes.

---

## Maintenance

When this checklist starts to feel ad-hoc or wrong:
- The flows are step-numbered for a reason. If you find yourself
  skipping or re-ordering steps, either the flow is broken
  (update the checklist) or you're not really running it
  (acknowledge that and run it properly).
- New surface added to the interruption family? Add a Flow N+1.
- A flow keeps catching the same bug? Promote it to a Python
  regression gate so it's covered without manual cycles.

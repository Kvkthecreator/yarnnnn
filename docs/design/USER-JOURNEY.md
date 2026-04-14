# User Journey

**Version:** v1.2 (2026-04-14)
**Status:** Canonical
**ADRs:** 138, 141, 144, 152, 161, 163, 164, 176, 178, 179
**See also:** [TASK-SETUP-FLOW.md](TASK-SETUP-FLOW.md) · [ONBOARDING-SCAFFOLD-AND-BRIEFING.md](ONBOARDING-SCAFFOLD-AND-BRIEFING.md) · [SHARED-CONTEXT-WORKFLOW.md](SHARED-CONTEXT-WORKFLOW.md)

---

## Thesis

Work exists first. Agents serve work, not the other way around.

Users provide raw context once. The system reverse-engineers the work structure, populates the workspace, and starts producing — without the user configuring anything.

**System events surface as chat cards, not toasts.** Every significant system action produces a pre-composed card in the TP chat stream — zero LLM cost. TP reads these as history context on the next real turn. See [ADR-179](../adr/ADR-179-system-event-cards.md).

---

## Stage 1 — Sign-up

Auth → callback → workspace init → `/chat`.

**`initialize_workspace()` runs once, silently, in the callback.** Six phases:

| Phase | What gets created | Why |
|-------|------------------|-----|
| Directory structure | `/workspace/context/`, `/workspace/outputs/`, `/workspace/uploads/`, `/tasks/`, etc. (ADR-152) | Filesystem substrate — agents write to known paths from first run |
| Agent roster | 9 agents from `DEFAULT_ROSTER`: Researcher · Analyst · Writer · Tracker · Designer · Reporting · Thinking Partner · Slack Bot · Notion Bot · GitHub Bot (ADR-176) | Team exists before user sees anything — no configuration step |
| Workspace files | `IDENTITY.md`, `BRAND.md`, `AWARENESS.md`, `CONVENTIONS.md`, `_playbook.md`, `style.md`, `notes.md` | Empty templates TP and agents fill in — structural skeleton is in place |
| `WORKSPACE.md` manifest | Snapshot of agents, tasks, and context domain file counts | TP reads this at session start for meta-awareness |
| Default tasks | `daily-update` (essential, ADR-161), `back-office-agent-hygiene` (TP-owned, ADR-164), `back-office-workspace-cleanup` (TP-owned, ADR-164) | Heartbeat + maintenance exist from day one — no dormant silence |
| Signup balance | $3 one-time grant (ADR-172) | Cold-start executions don't require billing setup |

**On landing at `/chat`:** the init result seeds a system card as the first assistant message — pre-composed, no LLM. Sets expectations before the user speaks. TP reads it as history on their first message.

---

## Stage 2A — Cold Start (ContextSetup)

**Condition:** `IDENTITY.md` is empty.
**Component:** `ContextSetup.tsx` — full-width overlay above chat input.

Three input lanes: **Links** (company site, LinkedIn, competitor URLs) · **Files** (PDF, DOCX, TXT) · **Notes** (free text).

Submitting composes one rich message and dismisses the modal. **Chat panel must be in view and scrolled to bottom as TP responds** — the user sees the response arriving, not a blank screen.

TP acts on the message. Two Clarify moments may occur:

**Clarify #1 — post-inference gap check** (before domain scaffold):
After `UpdateContext(target="identity")` returns, if `single_most_important_gap.severity == "high"`, TP issues one Clarify with the suggested question. At most one, only high-severity. If no high-severity gap, proceeds directly.

**Clarify #2 — accuracy gate** (after domain scaffold, before task creation):
After `ManageDomains(action="scaffold")`, TP presents what was scaffolded and requires confirmation before creating tasks. Hard gate — tasks are recurring commitments, errors compound.

Full sequence:
```
ContextSetup submit → UpdateContext(identity) → [Clarify #1: gap?] → UpdateContext(brand)
  → ManageDomains(scaffold) → Clarify #2: accuracy gate → ManageTask(create) × N
  → ManageTask(trigger) × N → system card: "Track Competitors is running"
```

On task completion, a second system card appears: "Track Competitors finished. [View →]"

---

## Stage 2B — Returning User

**Condition:** Active tasks exist.
**Surface:** `/chat` with workspace state header above chat input (frontend-rendered, zero LLM cost).

Header shows: **What happened** (recent runs) · **Coming up** (scheduled) · **Needs attention** (gaps, idle agents). Collapses to one-line summary after the first user message.

Any system cards from background task completions since last session appear at the top of chat on open. TP loads compact filesystem index (~200–500 tokens) + last 5 messages (ADR-159) — working memory already surfaces task run timestamps and output freshness, so TP opens with awareness of what ran while the user was away.

---

## Stage 2C — Starting New Work (TaskSetup)

**Trigger:** Plus-menu → "Start new work" → `TaskSetupModal`.
**Design doc:** [TASK-SETUP-FLOW.md](TASK-SETUP-FLOW.md)

**Screen 0 — Route:**

| Card | Intent shape |
|------|-------------|
| Track something | Domain to monitor — context accumulates, no fixed end |
| Get a deliverable | Output to receive — report, deck, digest, dashboard |

**Route B (Track) — Screen 1B captures:** domain chip · cadence · sources · links/files/notes to seed entities.
TP output: `ManageTask(action="create", type_key="track-*", focus=..., schedule=..., sources=...)`

**Route A (Deliverable) — Screen 1A captures:** surface type · mode (recurring / one-time) · cadence · delivery · links/files/notes to shape `DELIVERABLE.md`.
TP output: `ManageTask(action="create", type_key=..., mode=..., schedule=..., delivery=..., page_structure=...)`

Both routes compose a complete intent statement — TP creates the task in one turn with no clarifying rounds. TP's response confirms creation; task execution produces a completion card when done.

---

## Stage 3 — Recurring Loop

Once tasks are active the system runs without user intervention:

```
Scheduler → execute_task() → gather context → generate → compose HTML → deliver
                ↑                                               ↓
         next_run_at                          completion card (if session open)
                                              working memory (next session)
                                              feedback → DELIVERABLE.md improves
```

- **Accumulation tasks** write to `/workspace/context/{domain}/` — each cycle deepens the knowledge
- **Deliverable tasks** read accumulated context, compose HTML, deliver via email or in-app
- **`daily-update`** synthesises recent runs each morning — one artifact summarising workforce activity
- **TP heartbeat** surfaces gaps, idle agents, and quality signals as Heads Up flags → triggers Stage 2C

---

## System Event Cards — Decision Table

Pre-composed assistant messages, zero LLM. TP reads as history.

| Event | Card | LLM? |
|-------|------|------|
| Workspace init complete | "Your workspace is ready — 9 agents, 3 tasks, daily update at 9am." | No |
| Task triggered | "Track Competitors is running — first results in a few minutes." | No |
| Task complete (session open) | "Track Competitors finished. [View →]" | No |
| Task complete (session closed) | Nothing — working memory covers it on next open | No |
| ContextSetup submitted | Real TP turn (already is one) | Yes — one turn |

---

## What the User Never Touches

- Agent types, roster configuration, domain naming
- Task assignment to agents
- Directory structure or workspace manifest
- Manual run triggers (unless they want to)

---

## Revision History

| Version | Date | Change |
|---------|------|--------|
| v1.2 | 2026-04-14 | Added system event cards pattern (ADR-179), two Clarify moments in 2A, chat-visible guarantee on ContextSetup, decision table |
| v1.1 | 2026-04-14 | Added workspace init as Stage 1 (6 phases), tightened all sections |
| v1.0 | 2026-04-14 | Initial draft |

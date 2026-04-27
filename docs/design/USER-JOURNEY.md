# User Journey

**Version:** v1.3 (2026-04-27)
**Status:** Canonical (Bucket A mechanical catch-up — full reshape pending ACTIVATION-FLOW.md discourse)
**ADRs:** 138, 141, 144, 152, 161, 163, 164, 176, 178, 179, 205, 222, 226
**See also:** [TASK-SETUP-FLOW.md](TASK-SETUP-FLOW.md) · [SHARED-CONTEXT-WORKFLOW.md](SHARED-CONTEXT-WORKFLOW.md)

---

## Thesis

Work exists first. Agents serve work, not the other way around.

Users provide raw context once. The system reverse-engineers the work structure, populates the workspace, and starts producing — without the user configuring anything.

**System events surface as chat cards, not toasts.** Every significant system action produces a pre-composed card in the TP chat stream — zero LLM cost. TP reads these as history context on the next real turn. See [ADR-179](../adr/ADR-179-system-event-cards.md).

---

## Stage 1 — Sign-up

Auth → callback → (optional program selection) → workspace init → `/chat`.

**Program selection** (ADR-226 Phase 2 — UI deferred, see ACTIVATION-FLOW.md when authored). The operator may pick an active program bundle (e.g. `alpha-trader`) before init runs, or skip. The selection threads `program_slug` into `initialize_workspace()`.

**`initialize_workspace(program_slug=None)` runs once, silently, in the callback.** Per ADR-205 the kernel scaffolds exactly **one persistent agent row — YARNNN** — plus universal substrate. Specialists, Platform Bots, and program-specific domains materialize on demand (specialists at first dispatch; Platform Bots on OAuth connect; domains at first write).

| Phase | What gets created | Why |
|-------|------------------|-----|
| Universal substrate | `/workspace/memory/`, `/workspace/review/` (Reviewer IDENTITY + principles + decisions skeletons), `/workspace/context/_shared/` (IDENTITY · BRAND · CONVENTIONS · MANDATE skeletons), `/agents/`, `/tasks/`, `/uploads/` (ADR-152, ADR-205, ADR-206) | Filesystem substrate — every workspace gets the kernel skeleton |
| YARNNN agent row | One row, role=`thinking_partner`, origin=`system_bootstrap` (ADR-205 + ADR-164) | Sole persistent identity at signup; everything else is lazy-created |
| Default tasks | `daily-update` (essential, ADR-161), `back-office-agent-hygiene` + `back-office-workspace-cleanup` (YARNNN-owned, ADR-164) | Heartbeat + maintenance from day one |
| Signup balance | $3 one-time grant (ADR-172) | Cold-start executions don't require billing setup |
| **(if program_slug)** Reference-workspace fork | Bundle's `reference-workspace/` files copied into `/workspace/`, honoring three-tier categorization: `canon` (verbatim), `authored` (skeleton + prompt — operator must fill), `placeholder` (empty — accumulates from work). Writes attributed `authored_by="system:bundle-fork"` per ADR-209. | Program-shaped substrate seeded from the bundle (ADR-226 Phase 1) |

**On landing at `/chat`:** the init result seeds a system card as the first assistant message — pre-composed, no LLM. Sets expectations before the user speaks. YARNNN reads it as history on their first message. If a program was selected and `authored`-tier files are still skeleton, the **activation overlay** prompt engages YARNNN to walk those files in declared order via `UpdateContext` (ADR-226 Phase 1, prompt `activation.py`).

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
| Workspace init complete (no program) | "Your workspace is ready. Tell me what you want to track or build." | No |
| Workspace init complete (program forked) | "Your `{program}` workspace is forked. Let's author the parts that need your judgment." (cues activation overlay) | No |
| Task triggered | "Track Competitors is running — first results in a few minutes." | No |
| Task complete (session open) | "Track Competitors finished. [View →]" | No |
| Task complete (session closed) | Nothing — working memory covers it on next open | No |
| ContextSetup submitted | Real YARNNN turn (already is one) | Yes — one turn |

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
| v1.3 | 2026-04-27 | Bucket A catch-up to ADR-222 OS pivot — Stage 1 reflects ADR-205 (YARNNN as sole persistent row) + ADR-226 (program selection + reference-workspace fork). System event cards updated for program-aware copy. ONBOARDING-SCAFFOLD-AND-BRIEFING cross-ref dropped (archived). |
| v1.2 | 2026-04-14 | Added system event cards pattern (ADR-179), two Clarify moments in 2A, chat-visible guarantee on ContextSetup, decision table |
| v1.1 | 2026-04-14 | Added workspace init as Stage 1 (6 phases), tightened all sections |
| v1.0 | 2026-04-14 | Initial draft |

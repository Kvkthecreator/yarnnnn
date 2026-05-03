# ADR-246: Three-Party Narrative Model — YARNNN as System Name, Reviewer as Operator-Named Persona

> **Status**: Proposed
> **Date**: 2026-05-03
> **Authors**: KVK, Claude
> **Supersedes**: naming sections of ADR-241 (surface collapse correct; persona naming deferred at the time)
> **Amends**: ADR-194 v2 (Reviewer operator-facing presentation), ADR-216 (YARNNN reclassification), FOUNDATIONS Axiom 2 (operator-facing framing clarification), LAYER-MAPPING.md (vocabulary table)
> **Dimensional classification**: **Identity** (Axiom 2) primary — names what the operator sees for each entity; **Channel** (Axiom 6) secondary — the narrative surface renders three distinct parties

---

## Context

### The question this ADR resolves

The discourse session of 2026-05-03 surfaced a clean question that had been deferred since ADR-241: **what do the operator and user actually *call* the entities they interact with?**

ADR-241 correctly collapsed the Reviewer as a separate cockpit card into the Thinking Partner detail view. But it left the naming question open. The result: the chat surface presents an entity named "Thinking Partner" (an internal architecture term the operator was never supposed to see) while the Reviewer renders as a generic "Reviewer" card with no persona attribution.

Neither name reflects what these entities *are* to the operator.

### The discourse conclusion

Three parties are present in the narrative at all times:

1. **The operator** — the human principal
2. **YARNNN** — the system. The OS shell. Not a named agent persona; the brand itself.
3. **The operator's named delegate** — the Reviewer seat, filled with an operator-authored (or program-shipped) persona that has a declared name

This is already structurally true in the message schema (`session_messages.role` has six values; three of them — `user`, `assistant`, `reviewer` — map to these three parties). The gap is naming and rendering, not architecture.

### Why "Thinking Partner" was always wrong as a user-facing name

"Thinking Partner" described an era (ADR-189, 2026-04-17) when the system was collaborative — you and the system reason together about what work to do. ADR-231 (mandate-driven invocations), ADR-207 (primary-action-centric workflow), and ADR-222 (OS framing) ended that era. The operator now has a declared mandate and the system runs autonomously. The operator supervises, not co-reasons. "Thinking Partner" describes the wrong relationship.

Furthermore: "YARNNN" is both the brand and the system. Having a separate agent name for the chat surface ("Thinking Partner") creates a naming collision — the operator doesn't know whether they're talking to the brand or a sub-entity. They're talking to the system. It's YARNNN.

### Why the Reviewer should surface its persona name

The Reviewer seat holds an operator-authored (or program-shipped) judgment persona declared in `/workspace/review/IDENTITY.md`. The persona has a name — it may be "Simons", "Buffett", "your risk steward", or an operator-original character. When the Reviewer renders a verdict in the narrative, the operator should read "Simons approved this trade" — not "Reviewer approved this trade." The persona name is the operator-facing identity. "Reviewer" is the internal seat name.

This is the difference between an architectural label and a relationship. The operator has a relationship with their named delegate. They do not have a relationship with an abstract "Reviewer" role.

---

## Decisions

### D1: YARNNN is the system name and the chat surface name — no separate agent persona name

The conversational surface in `/chat` speaks as **YARNNN**. Not "Thinking Partner," not "TP," not any other persona name. The system brand and the chat surface are the same thing.

**What changes**:
- Any user-facing label, display string, page title, or UI copy that says "Thinking Partner" is replaced with "YARNNN" or removed
- The chat surface header (if it shows a name) shows "YARNNN"
- `SurfaceIdentityHeader.tsx` and related components use "YARNNN" as the surface name

**What does NOT change**:
- Backend DB slug `thinking_partner` — intentional glossary exception per LAYER-MAPPING.md, kept for data compatibility
- URL param `?agent=thinking-partner` — kept for backwards compatibility and bookmark safety
- Route constant `THINKING_PARTNER_ROUTE` — kept as code constant (internal name, not user-visible)
- `role='thinking_partner'` in `agents` table — kept as DB compatibility slug
- `YarnnnAgent` class name — already correct
- All prompt directives that say "never refer to yourself as TP or Thinking Partner" — already correct, kept

**Rationale**: YARNNN is the OS shell (ADR-222 Principle 16). The shell speaks as the system. A user's terminal prompt doesn't have a separate persona name — it *is* the system interface. Same here.

### D2: The Reviewer seat surfaces its operator-authored persona name in narrative verdicts

When a Reviewer verdict renders in the chat narrative (`role='reviewer'`, shape `reviewer-verdict`), the occupant label reads the persona name from `/workspace/review/IDENTITY.md` rather than showing a hardcoded "Reviewer" or "AI Reviewer" string.

**Persona name resolution**:
- Parse `/workspace/review/IDENTITY.md` for the operator-declared persona name (first `# ` heading or declared name field)
- If `IDENTITY.md` exists and has a declared name → use it (e.g., "Simons", "your Steward")
- If `IDENTITY.md` is the program-shipped skeleton (still template) → use "your Reviewer"
- If `IDENTITY.md` is absent → use "Reviewer" as neutral fallback
- The AI occupant identity string (`ai:reviewer-sonnet-v1`) is an implementation detail, not the display label

**What changes**:
- `ReviewerCard.tsx`: `occupantLabel()` extended to accept resolved persona name; passes it as display label when available
- `GET /api/workspace/state` or a new lightweight `GET /api/reviewer/persona` endpoint returns the resolved persona name for FE consumption
- Alternatively: the compact index already surfaces IDENTITY.md content — a thin FE hook can read `/workspace/review/IDENTITY.md` via the existing file API and extract the name

**What does NOT change**:
- `/workspace/review/` substrate paths — unchanged
- `reviewer_audit.py` write path — unchanged
- `reviewer_agent.py` AI occupant logic — unchanged
- `review_proposal_dispatch.py` dispatch logic — unchanged
- The `reviewer` role in `session_messages` — unchanged
- `decisions.md` write format — unchanged

**Rationale**: The operator named their delegate. The delegate should show up by that name. This closes the gap between the architecture's persona-bearing Reviewer (ADR-194 v2, ADR-216) and what the operator actually sees.

### D3: The three-party narrative model is formally ratified

The chat narrative (`/chat`, `session_messages`) is a **multi-party log** where three primary parties speak:

| Party | `session_messages.role` | Rendered shape | Display name |
|-------|------------------------|----------------|--------------|
| Operator | `user` | `user-bubble` | (operator's own messages) |
| YARNNN | `assistant` | `yarnnn-bubble` | YARNNN |
| Reviewer delegate | `reviewer` | `reviewer-verdict` | Operator-authored persona name |

Plus three secondary parties already in the schema:
| Party | Role | Shape | Notes |
|-------|------|-------|-------|
| Domain agents | `agent` | `agent-bubble` | User-authored agents posting outputs |
| System | `system` | `system-event` | Mechanical events (housekeeping) |
| External | `external` | `external-event` | MCP / platform write-back |

This is not a two-way chat. It is a **narrative** — the operator-facing log of every invocation, attributed by identity, rendered by shape weight. Axiom 9 Clause B.

**What changes**: documentation only — this structure already exists in code. ADR-237 `MessageDispatch.tsx` already implements the six-shape dispatch. This ADR ratifies the three-party framing as canonical vocabulary.

### D4: Primitives map cleanly to YARNNN vs. the Reviewer seat — no change needed, but formally documented

This ADR resolves the "who does what" question for primitives:

**YARNNN (chat primitives — 26 tools)** — the orchestration surface uses these when the operator is present and driving:

| Primitive | Who it's for |
|-----------|-------------|
| `LookupEntity`, `ListEntities`, `SearchEntities`, `EditEntity` | Reading/editing relational entities |
| `ReadFile`, `WriteFile`, `SearchFiles`, `ListFiles` | Substrate reads/writes from chat |
| `GetSystemState` | System introspection |
| `WebSearch` | External research |
| `list_integrations` | Platform connection awareness |
| `InferContext`, `InferWorkspace` | Inference-merged substrate writes (identity, brand) |
| `ManageDomains` | Domain scaffolding |
| `ManageAgent` | Agent lifecycle |
| `ManageRecurrence` | Recurrence declaration lifecycle |
| `FireInvocation` | Manual trigger of a recurrence |
| `RepurposeOutput` | Output export/repackage |
| `RuntimeDispatch` | Asset rendering |
| `ProposeAction` | Propose an external write (routes to Reviewer) |
| `ExecuteProposal` | Execute an approved proposal |
| `RejectProposal` | Reject a proposal |
| `Clarify` | Ask operator for input |
| `ListRevisions`, `ReadRevision`, `DiffRevisions` | Revision-aware substrate reads |

**The Reviewer** — uses NO primitives directly. It is a pure judgment entity. It reads substrate files (`IDENTITY.md`, `principles.md`, `_performance.md`, the proposal) and writes to `decisions.md` via `reviewer_audit.py`. It does not call `execute_primitive()`. This is load-bearing: the Reviewer's independence (THESIS Commitment 2) is structurally enforced because it has no primitive surface — it cannot scaffold, compose, or route. It can only judge.

**Headless agents (production roles)** — use the headless primitive set (21 static + dynamic platform tools). Notably they have `ProposeAction` but NOT `ExecuteProposal` or `RejectProposal` — production agents can propose, they cannot bind.

**The key YARNNN/Reviewer distinction at the primitive level**:
- YARNNN has `ExecuteProposal` and `RejectProposal` — it can bind decisions when the operator acts through chat
- The Reviewer has neither — it cannot bind decisions through the primitive surface; binding goes through `review_proposal_dispatch.py` after autonomy gating
- This is the structural expression of the operator-principal relationship: YARNNN routes the operator's intent; the Reviewer renders independent judgment; neither can override the other's domain

**What changes**: documentation only. The primitive registry is correctly structured. This ADR documents the intentional design.

### D5: The Reviewer's periodic pulse is the missing wire for the autonomy loop — scoped as follow-on

The discourse identified that `autonomous` delegation mode currently means "Reviewer approves → executes" but has no longitudinal pattern detection. After N cycles, if win rate drops or drift from mandate accumulates, nothing surfaces this.

The correct fix is a **periodic pulse for the Reviewer seat** — a back-office recurrence declaration that runs daily/weekly, reads `_performance.md` + `decisions.md` + `calibration.md`, reasons about drift, and either:
- Posts a narrative entry surfacing the pattern to the operator
- Writes a pause marker to AUTONOMY.md when thresholds are crossed

This is architecturally clean (Reviewer already has both reactive and periodic trigger shapes per Axiom 4), doesn't merge YARNNN and Reviewer, and closes the autonomy loop properly.

**Scoped to follow-on ADR** (ADR-247): this is a non-trivial implementation (new recurrence declaration, new Reviewer prompt profile, pause-marker write path, AUTONOMY.md mutation rules). It deserves its own ADR.

---

## What This ADR Does NOT Change

- YARNNN's architectural classification as orchestration chat surface (ADR-216)
- Reviewer's architectural classification as judgment Agent (ADR-194 v2)
- The backend separation of `yarnnn.py` and `reviewer_agent.py` — this is correct and intentional per THESIS Commitment 2 (independence)
- Any substrate paths (`/workspace/review/`, `/workspace/memory/`)
- Any DB schema
- Any primitive registry
- ADR-241's surface collapse decision — that was correct

---

## Implementation Plan

### Commit 1 — Naming cleanup (Category B from audit)
Update user-facing strings in web components. Docstrings and comments that say "Thinking Partner" → "YARNNN". No logic changes.

Files: `SurfaceIdentityHeader.tsx`, `PrinciplesTab.tsx`, `SubstrateTab.tsx`, `MandateTab.tsx`, `AutonomyTab.tsx`, `AgentContentView.tsx`, `TPContext.tsx`, `README.md`

### Commit 2 — Persona name resolution (Category C from audit)
Wire persona name from `/workspace/review/IDENTITY.md` into `ReviewerCard.tsx` rendering.

Options (pick one):
- **Option A**: FE hook reads `/api/workspace/files?path=/workspace/review/IDENTITY.md` and extracts first `# ` heading as persona name — no new endpoint
- **Option B**: `GET /api/reviewer/persona` — thin endpoint reads IDENTITY.md, returns `{name, occupant_class}` — cleaner FE contract

Recommendation: Option A first (no new endpoint, uses existing file API). Option B when the endpoint is needed for other surfaces.

### Commit 3 — Doc sync
Update FOUNDATIONS.md Axiom 2 operator-facing framing, LAYER-MAPPING.md vocabulary table, THESIS.md §Vocabulary. Add ADR-246 to CLAUDE.md ADR index.

---

## Test Gate

`api/test_adr246_three_party_narrative.py`:
1. No user-facing "Thinking Partner" string in `web/components/tp/` display text (excluding URL params and code comments)
2. No user-facing "Thinking Partner" string in `web/components/agents/` display text
3. `ReviewerCard.tsx` references a persona name resolution path (not hardcoded "AI Reviewer" as only label)
4. `MessageDispatch.tsx` has exactly six shapes — no new shapes added
5. `session_messages.role` constraint includes `reviewer` (substrate preserved)
6. `/workspace/review/IDENTITY.md` path referenced in at least one FE file (persona resolution wired)
7. `reviewer_agent.py` unchanged (backend judgment layer intact)
8. `review_proposal_dispatch.py` unchanged (dispatch logic intact)

---

## Relationship to Existing ADRs

| ADR | Relationship |
|-----|-------------|
| ADR-216 | Preserves YARNNN-as-orchestration-surface classification; this ADR only adds "and the surface name is YARNNN" |
| ADR-194 v2 | Preserves Reviewer substrate entirely; this ADR only amends operator-facing persona name rendering |
| ADR-241 | Surface collapse was correct; this ADR completes the naming work that ADR-241 deferred |
| ADR-237 | MessageDispatch six-shape model preserved and ratified |
| ADR-222 | OS framing: YARNNN is the shell — D1 above expresses this in user-facing naming |
| ADR-245 | Frontend kernel three-layer model — D2 persona resolution is an L3 affordance (structured read of a content-shaped file) |
| ADR-231 | Narrative model ratified — `/chat` is the narrative surface per Axiom 9 |

# ADR-274: Trigger-Authoring Implementation — Reviewer Cadence Self-Awareness

**Status**: **Proposed 2026-05-14** — implementation ADR for FOUNDATIONS v8.5 Axiom 4 amendment + Derived Principle 18.

**Authors**: KVK + Claude (discourse session 2026-05-14)

**Companion canon change** (atomic with this ADR):
- FOUNDATIONS v8.5 — Axiom 4 sub-clause "Trigger authoring is an Identity-layer responsibility" + Derived Principle 18 "Standing intent implies Trigger-authoring authority."

**Amends**:
- ADR-261 D4 — `Schedule` primitive belongs in `REVIEWER_PRIMITIVES`. ADR-261 declared the capability; ADR-274 enacts the discipline that makes the capability load-bearing.
- ADR-209 Phase 3 — read-side revision primitives (`ListRevisions` / `ReadRevision` / `DiffRevisions`). ADR-274 names them as the Reviewer's cadence-history surface.
- ADR-268 — market-context-aware schedules. ADR-274 names time + market context as wake-envelope concerns.

**Preserves**:
- FOUNDATIONS Axioms 1–8 unchanged. Axiom 4 amended in canon (FOUNDATIONS v8.5); this ADR is its minimal implementation.
- ADR-209 Authored Substrate model unchanged.
- Schema unchanged (no new tables, no new columns).
- Primitives surface unchanged (no new primitives — `Schedule` already exists in `REVIEWER_PRIMITIVES`).
- Cron scheduler unchanged.
- Bundle structure unchanged (recurrences ship as scaffold per the amended axiom; no deletions).

**Dimensional classification**: **Trigger** (Axiom 4) primary; **Identity** (Axiom 2) secondary; **Substrate** (Axiom 1) tertiary — all via existing infrastructure.

---

## 1. Why this ADR

FOUNDATIONS v8.5 amended Axiom 4 to commit:

> **Triggers are authored by Identity layers, not by kernel infrastructure or bundle declarations. The kernel's cron + the bundle's initial recurrences are scaffolds; they do not own the Trigger dimension across the workspace's lifecycle.**

This ADR is the minimal implementation that enacts the amendment. It is small because the system was already 90% built for this — the missing pieces are:

1. **The `Schedule` primitive's `authored_by` parameter defaults to `"operator"`** — silent attribution drift would break the audit trail the amendment depends on.
2. **The Reviewer's wake-time envelope contains no time / market-context block** — without this, the Reviewer cannot perceive *now* and cannot author cadence sensibly.
3. **The Reviewer's system prompt does not name the cadence-authoring responsibility** — without explicit citation of the amended axiom, the LLM has no anchor for exercising the authority.

Everything else load-bearing already exists:
- Authored Substrate's `authored_by` attribution (ADR-209)
- The `Schedule` primitive in `REVIEWER_PRIMITIVES` (ADR-261 D4)
- Read-side revision primitives (`ListRevisions`, `ReadRevision`, `DiffRevisions`) in `REVIEWER_PRIMITIVES` (ADR-209 Phase 3)
- `execution_events` outcome log
- `get_user_timezone` + `get_market_context_for_user` (kernel-side, ADR-268)
- `decisions.md` reasoning trail (ADR-194 v2)
- `/work` Schedule tab + revision panel for operator legibility

This ADR is **prompt-layer + primitive-contract**, not new infrastructure.

---

## 2. Decisions

### D1 — `Schedule` primitive: `authored_by` is load-bearing, fail-fast on missing

`api/services/primitives/schedule.py::handle_schedule` currently:

```python
authored_by = input.get("authored_by") or "operator"
```

Silent default to `"operator"` violates Derived Principle 13 (Authored Substrate: every mutation carries an `authored_by` *identity*, enforceable at the write path). Per the v8.5 amendment, the authoring Identity must be explicit at every call site.

Change:

```python
authored_by = input.get("authored_by")
if not authored_by or not isinstance(authored_by, str) or not authored_by.strip():
    return {
        "success": False,
        "error": "missing_authored_by",
        "message": (
            "Schedule requires authored_by per Axiom 4 v8.5 — caller must "
            "assert which Identity is authoring the recurrence "
            "(e.g., 'operator', 'reviewer:simons', 'agent:portfolio-tracker', "
            "'system:bundle-fork'). Silent attribution would break the "
            "Trigger-dimension audit trail."
        ),
    }
authored_by = authored_by.strip()
```

Caller paths updated:

| Caller | Identity asserted |
|---|---|
| Operator chat (YARNNN-routed `Schedule`) | `authored_by="operator"` |
| Reviewer mid-loop | `authored_by="reviewer:{occupant}"` (occupant resolved from `IDENTITY.md`) |
| Bundle fork (`workspace_init`) | `authored_by="system:bundle-fork"` |
| Operational scripts (alpha-ops harness) | `authored_by="operator"` (acts on behalf of operator) |

### D2 — Reviewer wake envelope: `## Operating Context` block

`api/agents/reviewer_agent.py::_build_user_message` adds a new section assembled from existing services:

```
## Operating Context (Axiom 4 v8.5)

**Now**: 2026-05-14T05:11:00Z (Wed, in your tz: 14:11 KST UTC+9)
**Operator timezone**: America/New_York
**Market state**: pre-market (RTH opens in 4h 19m at 13:30 UTC = 09:30 ET)
**Workspace tenure**: 27 days since activation
```

Sources:
- `now` — `datetime.now(timezone.utc)`
- Operator timezone — `services.scheduling.get_user_timezone(client, user_id)`
- Market state — `services.bundle_reader.get_market_context_for_user(user_id, client)` (returns the calendar+state dict already used by cron resolution)
- Workspace tenure — `workspaces.created_at` delta from now

For workspaces where market context isn't applicable (non-trading programs), the **Market state** line omits gracefully.

No new infrastructure; pure projection.

### D3 — Reviewer system prompt: one-paragraph addition citing the amended axiom

`api/agents/reviewer_agent.py::_PERSONA_FRAME` adds (after the existing inline-default discipline from ADR-272 follow-ups):

> **Your operating cadence is yours to author (Axiom 4 v8.5 + Derived Principle 18).**
>
> Per the amended Axiom 4, Triggers are authored by Identity layers — including yours. The bundle's initial recurrences are scaffolds, not your permanent rhythm. When your judgment warrants a cadence change — adding a new wake, rescheduling an existing one, archiving a stale one — call `Schedule(action="create"|"update"|"pause"|"resume"|"archive", authored_by="reviewer:{your-occupant}", ...)`. Always assert `authored_by` explicitly; default-attribution is rejected at the primitive layer.
>
> Your cadence-authoring history is queryable: `ListRevisions(path="/workspace/_recurrences.yaml")` returns every revision with `authored_by`; `ReadRevision` returns specific versions; `DiffRevisions` shows what changed. Pair these with `decisions.md` reasoning to make your operating judgment auditable. The two-table pair (revision intent + `execution_events` outcomes) is the canonical Trigger audit trail per FOUNDATIONS v8.5 — no parallel `cadence.md` or schedule-tracking substrate.
>
> First wake at activation: scaffold cadence is in place. Observe operation against it. Author refinements when evidence warrants — not premptively.

This is the prompt-level enactment of Derived Principle 18.

### D4 — No bundle changes

Per Axiom 4 v8.5, the bundle's existing recurrences are *structurally* scaffolds — their `authored_by="system:bundle-fork"` makes this explicit in the audit trail. Operator + Reviewer + Agents author over them with their own attribution. No deletions, no thinning, no migrations. The amendment retroactively re-frames the bundle's role without code change.

### D5 — Audit trail uses existing infrastructure (no new file)

Per the v8.5 amendment, the Trigger audit trail lives in:
- `workspace_file_versions` filtered to `path='/workspace/_recurrences.yaml'` — every Identity-authored revision
- `execution_events` filtered by user_id — every kernel-dispatched outcome

The mid-discourse `cadence.md` idea is rejected as a Singular Implementation violation. Existing infrastructure is sufficient.

### D6 — Operator-legibility floor unchanged

`/work` Schedule tab already shows every recurrence with last-run + next-run timestamps. ADR-209 Phase 4 revision panel surfaces `authored_by` on revisions. The combination provides operator legibility on cadence ownership transitions. No new FE surface this ADR.

---

## 3. What this ADR explicitly does NOT do

- **Does not change schema.** No new tables, columns, or migrations.
- **Does not add primitives.** `Schedule` + read-side revision primitives already in `REVIEWER_PRIMITIVES`.
- **Does not delete or thin bundle recurrences.** Bundle scaffolds remain; Reviewer authors over them.
- **Does not create `/workspace/review/cadence.md` or similar audit file.** Existing two-table pair suffices.
- **Does not project recent fires into the Reviewer envelope.** The Reviewer can query `execution_events` via `GetSystemState` when judgment requires — eager projection would be prompt-bloat.
- **Does not commit any FE work.** Operator legibility lives in existing `/work` Schedule + ADR-209 revision panel.

---

## 4. Implementation phasing

**Single atomic commit:**

1. `api/services/primitives/schedule.py` — fail-fast on missing `authored_by` per D1.
2. `api/agents/reviewer_agent.py::_build_user_message` — add `_format_operating_context_block()` helper per D2.
3. `api/agents/reviewer_agent.py::_PERSONA_FRAME` — append cadence-authoring discipline section per D3.
4. Caller-site audit — update all live `Schedule` callers to pass explicit `authored_by`:
   - `services/workspace_init.py` fork path → `"system:bundle-fork"`
   - `agents/reviewer_agent.py` Reviewer-loop dispatch → `"reviewer:{occupant}"` (via the Reviewer's own tool call composition)
   - `routes/feed.py` chat-routed Schedule (if any direct calls) → `"operator"`
   - `scripts/alpha_ops/*.py` if any → `"operator"`
5. Regression test gate `api/test_adr274_trigger_authoring.py`:
   - `Schedule` fails on missing `authored_by`
   - `Schedule` accepts each of: `operator`, `reviewer:`-prefixed, `agent:`-prefixed, `system:bundle-fork`
   - Reviewer `_PERSONA_FRAME` contains the cadence-authoring discipline section (string assertion)
   - Reviewer `_build_user_message` injects the `## Operating Context` block (call-result assertion against mock context)
6. Doc cascade:
   - ADR-274 marked Implemented
   - ADR-261 D4 note → "discipline now in FOUNDATIONS Axiom 4 v8.5; this ADR enacts the implementation"
   - ADR-209 Phase 3 note → "read-side primitives are the Reviewer's cadence-history surface per ADR-274"
   - `api/prompts/CHANGELOG.md` entry
   - `CLAUDE.md` ADR summary block update

**Total scope**: ~80-100 LOC across 4-5 files + test gate + docs.

---

## 5. Risks + mitigations

**Risk 1 — Existing callers of `Schedule` that don't pass `authored_by` would crash post-deploy.**
Mitigation: caller-site audit at implementation time identifies every live call; each is updated to explicit attribution. Regression test ensures no caller hits the fail-fast path.

**Risk 2 — Reviewer reads the discipline section but doesn't engage with Schedule authoring.**
Mitigation: this is an *empirical* question, not architectural. Observe behavior over the next few wakes — if no Reviewer-authored revisions appear in `workspace_file_versions`, the prompt wording is insufficient and a sharper prompt revision lands as a follow-up. The architecture is correct regardless.

**Risk 3 — Reviewer over-authors (churns cadence too aggressively).**
Mitigation: the prompt's "observe operation against scaffold; author refinements when evidence warrants — not preemptively" frames the discipline. The audit trail surfaces churn; the operator can intervene.

**Risk 4 — Bundle-authored recurrences and Reviewer-authored recurrences in the same `_recurrences.yaml` could confuse operators.**
Mitigation: `authored_by` on every revision makes the lineage explicit. ADR-209 Phase 4 revision panel surfaces this in the FE. The `/work` Schedule tab can be extended with a "source" column in a future FE pass if confusion materializes.

**Risk 5 — Time-projection in the envelope adds tokens to every Reviewer wake.**
Cost: ~50 tokens per wake. Negligible relative to existing envelope (~15-30K tokens). Net win: enables Reviewer Trigger authoring.

---

## 6. Why this implementation is sufficient

The system was 90% built for this:

| Capability | Existing | This ADR adds |
|---|---|---|
| Schedule primitive callable by Reviewer | ADR-261 D4 | — |
| Authored Substrate with `authored_by` | ADR-209 | Contract tightening (fail-fast) |
| Revision-aware reads in Reviewer's tool surface | ADR-209 Phase 3 | Prompt naming them as cadence surface |
| Time + market context computed kernel-side | ADR-268 | Wake-envelope projection |
| Reasoning trail in `decisions.md` | ADR-194 v2 | (no change) |
| Operator-legibility on `/work` Schedule | Existing | (no change) |
| Bundle = scaffold attribution | ADR-209 | Axiom-level commitment (FOUNDATIONS v8.5) |

The minimal scope is itself the validation: when an architectural amendment requires only contract-tightening + prompt-layer projection + caller-site discipline, the underlying axiom was correctly architected and the missing piece was the explicit Identity-layer commitment.

---

## 7. Discourse log

This ADR concludes the session-2026-05-14 architectural arc:

1. ADR-272 Phase 1 + Phase 2 + follow-ups shipped, validated live on seulkim88 and kvk.
2. Operator (KVK) asked whether kvk's morning-reflection wake at 07:00 UTC is bundle-author cron OR Reviewer's own meta-awareness.
3. Audit confirmed: bundle-author cron; Reviewer was structurally passive on Trigger dimension.
4. Discourse converged on: this is an axiom-level gap, not a feature-level gap. Standing intent implies Trigger-authoring authority. Existing infrastructure already provides everything except the explicit Identity-layer commitment and the prompt-layer projection.
5. FOUNDATIONS v8.5 amends Axiom 4 with the Identity-authoring commitment + Derived Principle 18.
6. ADR-274 lands the minimal implementation that enacts the amendment.

**Empirical validation**: kvk's morning-reflection wake at 07:00 UTC (or the next Reviewer wake post-deploy) is the first live observation of behavioral pickup. Expected: Reviewer reads the `## Operating Context` block, reads the cadence-authoring discipline section, *may* call `Schedule(authored_by="reviewer:...")` if it judges cadence refinement warranted. If no Reviewer-authored revisions appear after several wakes, the prompt wording requires sharpening — that's a follow-up commit, not an architectural reversal.

---

**End of ADR-274.** Implementation follows in the same commit.

# ADR-283 step 6 — Dogfood readiness assessment (2026-05-17)

> Operator-driven readiness assessment. This memo captures what's structurally ready, what's not, and the concrete steps required for kvk (or any operator) to actually activate alpha-author against a live workspace and exercise the loop end-to-end.

## What's structurally ready (steps 1-5 shipped)

| Layer | Status | Reference |
|---|---|---|
| Bundle (MANIFEST + SURFACES + README) | ✅ Shipped | `docs/programs/alpha-author/` |
| Reference-workspace substrate (operator-canon templates) | ✅ Shipped | `docs/programs/alpha-author/reference-workspace/context/_shared/` + `context/authored/` + `review/` |
| Capability specs (6 specs) | ✅ Shipped | `docs/programs/alpha-author/reference-workspace/specs/` |
| Recurrences (4 entries: pre-ship-audit, corpus-coherence-check, revision-audit, outcome-reconciliation) | ✅ Shipped | `docs/programs/alpha-author/reference-workspace/_recurrences.yaml` |
| Entity-continuity substrate (`_entities.md` + `entities/_example.md`) | ✅ Shipped (step 2) | `docs/programs/alpha-author/reference-workspace/context/authored/entities/` |
| Cockpit faces (AuthorMandate / AuthorCorpus / AuthorVoice / AuthorPipeline) | ✅ Shipped (step 3) | `web/components/library/programs/alpha-author/` |
| Persona registry rows + override directories | ✅ Shipped (step 4) | `docs/alpha/personas.yaml` + `docs/alpha/personas/alpha-author/` |
| Activation harness smoke-tested + kind=none bug fixed | ✅ Shipped (step 5) | `api/scripts/alpha_ops/activate_persona.py` |
| Programs registry listing alpha-author | ✅ Shipped (step 1) | `docs/programs/README.md` |
| FOUNDATIONS Axiom 8 (Ground-Truth Substrate) supports multi-signal alpha-author instance | ✅ Shipped (ADR-282) | `docs/architecture/FOUNDATIONS.md` |

## What's NOT ready (step 6 work)

These are the concrete blockers between "bundle exists" and "operator actually using it":

### Blocker 1 — Real Supabase workspace provisioning

The persona rows in `personas.yaml` use placeholder all-zeros UUIDs:
```yaml
user_id: 00000000-0000-0000-0000-000000000000
workspace_id: 00000000-0000-0000-0000-000000000000
```

Real activation requires real Supabase records:
1. Sign up `yarnnn-author@yarnnn.com` (and `netflix-script-author@yarnnn.com` separately) through the YARNNN signup flow on production
2. After signup, retrieve the real `user_id` from the Supabase `auth.users` table and `workspace_id` from the `workspace_files` or `chat_sessions` tables (whichever returns first)
3. Update both persona rows in `personas.yaml` with the real values (single commit)

This is operator-self-service work — I can't sign up email accounts for the operator.

### Blocker 2 — Decide whether to use kvk's existing workspace OR new dedicated workspaces

**Two viable paths**:

**Path A — Dedicated workspaces per persona.** Sign up two new email accounts (or use sub-addressing like `kvk+yarnnn-author@gmail.com`). Each gets a clean alpha-author workspace. Pros: clean separation; can dogfood both yarnnn-author and netflix-script-author simultaneously without interference. Cons: managing 3+ separate accounts (kvk's alpha-trader + 2 alpha-author).

**Path B — Activate alpha-author in kvk's existing workspace.** Run `POST /api/programs/activate?program=alpha-author` against kvk's current workspace (which has alpha-trader activated). The kernel supports one program per workspace per ADR-230 D1; activating a second program would either swap (overwrite alpha-trader's substrate) or layer (both programs' substrate side-by-side). I haven't validated which one the current code does — would need to test. **This path requires care** and possibly an ADR amendment if multi-program-per-workspace was never the intent.

Recommendation: **Path A**. Cleaner dogfood, no risk of stepping on alpha-trader's substrate, validates the bundle on its own terms.

### Blocker 3 — Operator authoring time

The bundle ships templates. The operator must author specific content for each workspace to make the loop meaningful:

For `yarnnn-author`:
- Author `MANDATE.md` (specific Primary Action for YARNNN founder content)
- Author `IDENTITY.md` (your authorial posture)
- Author `_voice.md` (your declared voice fingerprint with positive markers + anti-patterns — the load-bearing substrate the Reviewer audits against)
- Author `_editorial.md` (what gets shipped vs held for this workspace)
- Optionally: customize `principles.md` with workspace-specific Reviewer principles
- Optionally: declare initial entities in `_entities.md` (recurring concepts your founder content references — e.g., "the substrate-continuity archetype", "alpha-trader as exemplar")

For `netflix-script-author`:
- Same shape, plus declare characters as entities at `entities/{character-slug}.md` early (the entity-continuity audit is most load-bearing here)
- Specifically declare multi-voice in `_voice.md` (author voice for stage directions + per-character voice declarations)

Realistic operator effort: 2-4 hours per workspace for first-pass authoring, with iteration ongoing.

### Blocker 4 — First-piece authoring + pre-ship-audit exercise

Until at least one draft piece exists at `/workspace/context/authored/{piece-slug}/content.md` and gets marked `ready_for_review`, the `pre-ship-audit` recurrence has nothing to fire on. The first-wake loop is:

1. Operator authors a draft (founder post, screenplay scene, whatever)
2. Operator marks the draft `ready_for_review` (via piece `profile.md` frontmatter edit or via chat)
3. `pre-ship-audit` recurrence fires reactively, Reviewer audits
4. Operator observes Reviewer behavior — does the voice-audit detect the right anti-patterns? Does it surface the right entity-continuity flags?

This is the dogfood proof. Without it, the bundle is structurally complete but architecturally unproven.

### Blocker 5 — Cockpit empty-state validation

The four Author* cockpit faces (step 3) ship with graceful empty-state messaging for pre-activation workspaces. Real activation will surface whether the empty states are operator-actionable:

- AuthorMandate empty-state: "Mandate not yet authored — open chat to declare your Primary Action" — does it lead the operator into chat usefully?
- AuthorCorpus empty-state: "Calibration cycle not started — `_signal.md` populates after first reconciliation" — is this honest enough that the operator doesn't think it's broken?
- AuthorVoice empty-state: "Voice fingerprint not yet declared" — same question
- AuthorPipeline empty-state: "No pieces yet — drafts land under /workspace/context/authored/{piece-slug}/content.md" — is the path guidance enough?

Real-activation observation will surface UX issues to log.

## Realistic step 6 timeline

If kvk decides to actually dogfood:

| Activity | Effort |
|---|---|
| Sign up `yarnnn-author@yarnnn.com` + retrieve real UUIDs | ~30 min |
| Update `personas.yaml` placeholder UUIDs + commit | ~5 min |
| Run `activate_persona.py --persona yarnnn-author` against production | ~2 min |
| Verify activation via cockpit visit + read of forked substrate | ~15 min |
| Author first-pass `MANDATE.md` + `IDENTITY.md` + `_voice.md` + `_editorial.md` via chat | ~2-3 hours |
| Author + mark first draft `ready_for_review` | ~30 min - 2 hours (depends on piece) |
| Observe first `pre-ship-audit` Reviewer behavior + record findings | ~30 min |
| Record findings as `docs/alpha/observations/2026-XX-XX-adr283-alpha-author-first-wake-yarnnn-author.md` | ~30 min |
| **Sub-total: ~5-8 hours** for yarnnn-author first activation cycle |  |

Repeat for netflix-script-author (~3-5 hours since some patterns established) → **total 8-13 hours of operator-driven dogfood for first real loop exercise**.

This is real work and should be scheduled deliberately, not squeezed into a session.

## What I (claude) cannot do for step 6

- Sign up email accounts on production
- Provision Supabase rows
- Author the operator's MANDATE / IDENTITY / voice fingerprint (those are operator-authored stance per ADR-209 attribution discipline — `authored_by="operator:..."` is load-bearing; ghostwriting them would invalidate the substrate's truthfulness)
- Author actual content pieces in either workspace
- Observe the first-wake Reviewer behavior live (requires operator at the keyboard with real substrate)

## What I (claude) can do once operator triggers step 6

- Help draft the operator-facing content via chat (operator's call which to actually use)
- Patch any bugs the first-wake observation surfaces
- Iterate on cockpit face empty-states based on what feels confusing
- Iterate on Reviewer principles based on what audit findings feel wrong
- Help author the observation memos from raw notes

## Honest assessment

**The bundle is structurally complete and dogfood-ready.** Steps 1-5 closed the architectural surface. Step 6 is operator dogfood — work that *must* be done by you, not me, and that surfaces what the architecture got right vs wrong only after real use.

The ADR-283 roadmap intent was always: "build the bundle, then let it sit until kvk actually wants to dogfood it." That moment is now. Whether to invest the 8-13 hours of first-loop exercise is a separate decision from whether to build alpha-author — which is now done.

## Recommendation on closing ADR-283

ADR-283 status can flip from `Proposed` to `Implemented (steps 1-5, step 6 operator-driven)` based on this commit chain:

| Step | Commit |
|---|---|
| 1 — Reference-workspace authoring | `cb698c0` |
| 2 — Substrate enrichment for long-arc authorship | `8ab04f2` |
| 3 — Cockpit face components | `3775f3c` |
| 4 — Persona registry update | `904f9a4` |
| 5 — Activation harness smoke-test + kind=none fix | `5624842` |
| 6 — Dogfood activation | Operator-driven; not on the architectural critical path |

The bundle is shipped. The next ADR-283 activity isn't more architecture — it's operator dogfood when kvk chooses to invest the time. The architecture stands ready.

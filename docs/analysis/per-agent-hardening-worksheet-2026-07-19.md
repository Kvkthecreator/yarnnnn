# Per-agent hardening — the worksheet (go one agent at a time, no drift)

> **Status**: Working scaffold. The companion to `base-agent-hardening-audit-and-discourse-2026-07-18.md` (the shared audit + discourse). That doc found the frame; **this doc is the repeatable per-agent procedure** so each agent's pass asks the same questions in the same order and lands within the same canon ceiling. Fill one section per agent; do not reorder the planes; do not skip the click pass.
> **Date**: 2026-07-19
> **Scope**: base agents only — Researcher (`scout`) · Thinker (`sonnet`) · Designer (`designer`) · the Critic posture (`critic`). NOT judgment agents (Rung-2, ADR-382), NOT Freddie.

---

## 0. What changed since the audit (so we start from truth)

- **The capability bug is FIXED** (commit `5ba26e1`, 2026-07-19). `lane_tool_names(extra)` is now the single source; the declared payload, the executor allowlist, and the prompt's `## Your tools` all read it. A live Gemini call confirmed Scout calls `QueryKnowledge` and the guard dispatches it. Regression-guarded in `test_agent_registry.py` (158/158, the three-way-agreement invariant).
- So D1 (§5 of the audit) is **done**. This worksheet begins at the point the audit called D2/D3/D4: **which reads each agent needs, proven by a live turn, and how thick each posture should be.**

## 1. The invariants every pass MUST honor (the ceiling — do not re-litigate)

| Plane | The one rule | Where it's enforced |
|---|---|---|
| **Capability** | A tool may name ONLY a non-consequential primitive (reads + our own primitives). **Never an outward write.** | `resolve_agent_tools` filters against `permission.py::READ_ONLY_PRIMITIVES` (ADR-463 D4.a). Gate-proven to bite. |
| **Skill** | Base agents get **NO skills folder** — the kernel corpus is code. A base agent's "skill" IS its posture + capability. | ADR-464 §4. `find_agent_skills` unreachable for a kernel slug. Skills are a *member* affordance only. |
| **Posture** | Kernel postures are code (ours to edit). Members get `tone` (additive), never full posture authoring. | ADR-464 §6. `build_agent_posture` composes character → name → tone → skills. |
| **Engine** | Per-agent engine bias is LAST and **evidence-gated** on a real output difference — not vendor symmetry. | ADR-463 D5. Sonnet + Designer already share `claude-sonnet-4-6`. **Out of scope for these passes.** |

**The grantable read pool** (the whole legitimate capability surface a base agent could gain), from `permission.py:60-90`:
`LookupEntity · ListEntities · SearchEntities · ReadFile · ListFiles · SearchFiles · ReadAgentFile · ListRevisions · ReadRevision · DiffRevisions · QueryKnowledge · GetSystemState · DiscoverAgents · list_integrations · WebSearch · ReturnVerdict`.
Everything outside is consequential and fail-closed. **The five file verbs (`ReadFile/WriteFile/EditFile/SearchFiles/ListFiles`) are the baseline every lane already holds** — hardening a capability = adding from the read pool above, nothing else.

## 2. The per-agent procedure (same six steps, every agent)

For each agent, in this order. Do not move to the next step until the current one has a receipt.

1. **State the JOB in one sentence.** What member intent does addressing this agent serve? (The audit's addressed-operation.) This is the yardstick every plane is measured against.
2. **CAPABILITY — does the job need a read it lacks?** Walk the grantable pool (§1). For each candidate, answer: *does the JOB require it, or is it nice-to-have?* Only "the job requires it" earns a grant. Record the candidate, the verdict, and the one-line reason.
3. **POSTURE — read the current text; name where it fails the job.** Transcribe the posture verbatim. Ask: does it steer the model toward the job, or is it a label? Note thinness/richness relative to siblings — but **do not thicken yet.**
4. **CLICK PASS — one live turn, observed.** Drive a real turn that exercises the job. Watch: does the agent reach for the right tools? does the posture hold? where does it drift? **This is the evidence that turns steps 2–3 from taste into fact.** A pass-through LLM call (like the Scout confirmation) is enough — not a battery.
5. **APPLY — grant the read the click pass proved needed; thicken the posture where the click pass showed it drifting.** Never for symmetry, never for completeness — only from an observed failure. Cite the observation in the commit.
6. **REGRESSION — extend the gate.** Any new tool → assert payload == allowlist == prompt (the three-way invariant already in `test_agent_registry.py`). Any posture change → the gate already asserts each posture is >40 chars and present; add an intent assertion if the change encodes a specific discipline.

**Discipline**: each agent is its own commit (or its own small set). The worksheet section for that agent is updated in the SAME commit (doc-first-alongside-code, CLAUDE.md §1). Stage by name — a parallel lane is usually live.

---

## 3. Agent worksheets

> Fill these in as each pass runs. Empty = not yet done. The first three are pre-seeded with the audit's candidates so the discourse has a starting position, NOT a decision.

### 3.1 Researcher (`scout`) — ACQUIRE

- **JOB**: bring the world + commons into view — "find / dig up / what do we know about X", with sources.
- **Current capability**: 5 verbs + `QueryKnowledge` + `WebSearch` (the only base agent past the five; now actually executable post-fix).
- **Capability candidates**: *arguably complete.* Possible additions from the pool: `ListRevisions`/`ReadRevision`/`DiffRevisions` (dig through *history*, not just current state — "what changed about X and when"). `DiscoverAgents`/`GetSystemState` (dig through the workspace's own shape). **Verdict: pending the click pass** — does a real research turn reach for history and find it can't?
- **Current posture** (`agents_registry.py:123-129`): the richest base posture; names its tools + a search order (meaning-before-files) + two disciplines (don't editorialize; 'not here' over guessing). **Likely already well-steered** — the click pass confirms.
- **Click pass**: DONE for the extra-tool dispatch (the bug fix). NOT done for "does it want history/discovery." → open.
- **Applied**: — 
- **Regression**: the three-way invariant covers scout today.

### 3.2 Thinker (`sonnet`) — REASON

- **JOB**: turn state into judgment — "think this through / decide / weigh / what should we do."
- **Current capability**: 5 verbs only.
- **Capability candidates**: **`QueryKnowledge` is the lead** — the audit's sharpest claim: *"a thinker that cannot recall the workspace is as much a lie as pre-fix Scout was."* Reason over a commons it can't semantically search is reason with its eyes closed. This is the exact ADR-463 P2 argument, one agent over. **Strong candidate; the click pass should make it obvious** (a reasoning turn that needs a prior decision and can only `SearchFiles` by exact string). Secondary: revision reads (reason about how intent *evolved*, DP24-adjacent) — weaker, click-pass-gated.
- **Current posture** (`agents_registry.py:98-102`): thin (3 sentences, one discipline: shortest-honest-over-complete). Parallel with Designer. **Possibly correct** (a thinking partner shouldn't be over-scripted) **or under-baked** — the click pass decides. Candidate depth: a line on *reasoning from the workspace's own record* (pairs with a QueryKnowledge grant).
- **Click pass**: — (drive a reasoning turn that needs a recorded prior decision; watch whether it wants recall).
- **Applied**: —
- **Regression**: —

### 3.3 Designer (`designer`) — PRODUCE

- **JOB**: turn judgment into an artifact in the commons — "make the deck / write the doc / build the thing."
- **Current capability**: 5 verbs only (writes to the commons via WriteFile/EditFile — the baseline, correct for a maker).
- **Capability candidates**: weaker than Thinker's. Possible: `QueryKnowledge` / revision reads to pull prior artifacts + their history before composing (a maker that reads what came before). But Designer mostly works in the artifact in front of it (bound Studio lane, where the studio posture supplies the target). **Verdict: likely no grant; click-pass-gated.** Do not grant reflexively.
- **Current posture** (`agents_registry.py:175-180`): thin (3 sentences, one discipline: smallest-honest-version + state assumptions). Parallel with Thinker. The bound-lane case adds the studio posture on top, so Designer's character is thinner *by design* (the JOB comes from the binding). **Probably correct** — confirm in a bound turn.
- **Click pass**: — (drive a bound Studio make turn; watch character + studio-posture composition).
- **Applied**: —
- **Regression**: —

### 3.4 Critic (`critic`, posture over Reason)

- **JOB**: pressure-test — "find the hole / what's wrong with this / steelman the objection."
- **Note**: Critic is a POSTURE (`based_on: sonnet`), not a base operation. It inherits Thinker's capability. **A capability grant to Thinker flows to Critic** (via `based_on`) — so Critic has no independent capability pass; it rides Thinker's. This is correct and worth stating so nobody grants Critic tools directly (postures declare none — `POSTURE_ROW_KEYS`).
- **Current posture** (`agents_registry.py:257-262`): thick (4 sentences, the only hard prohibition "Never flatter" + a survival-clause protocol). **Likely the best-steered of the four.** Its depth is a good reference for what "well-steered" looks like when thickening the others.
- **Click pass**: — (drive an adversarial turn; is the posture doing work, or is gpt-5 just being contrarian?).
- **Applied**: —
- **Regression**: —

---

## 4. The sequence across agents (recommended order)

1. **Thinker first** — it has the sharpest, most-defensible candidate (`QueryKnowledge`), and proving it validates the whole "grant reads the job needs" thesis on the clearest case. If a reasoning turn visibly wants recall, the pattern is set.
2. **Researcher second** — mostly confirmation (tools now work) + the history-reads question.
3. **Designer third** — most likely "no new capability, posture is correctly thin"; a fast confirmation pass.
4. **Critic last** — rides Thinker's capability; a posture-only look.

Each is small. The value is the *observed turn* per agent — the thing the whole codebase has never had (the elephant). The worksheet exists so that after four passes we have four receipts in one place, and the next person adding a fifth agent (a fifth addressed operation, per AGENT-TAXONOMY) runs the same six steps.

## 5. One-line statement

**Hardening runs one agent at a time through six fixed steps — state the job, ask which read the job needs, read the posture, run ONE live observed turn, apply only what the turn proved, extend the gate — inside a ceiling that is already decided (reads-only capability, member-only skills, code-owned postures, evidence-gated engines), so that going agent-by-agent produces four receipts in one worksheet instead of four ad-hoc decisions, and the sharpest first case (QueryKnowledge for Thinker — reason that can't recall the workspace is reason with its eyes closed) sets the pattern the rest confirm or refuse.**

# ADR-640 — An agent has no record of its own

> **Status**: **Accepted** (2026-09-04). Ruling from the ADR-639 follow-up audit: should the Agents page become *"the one place a member reads who works here, in which app, with which craft, tending which files, with what receipts"*? Four of those five are derivable and honest. **The fifth is refused**, and this ADR is why — and ADR-603 §Consequences had already routed receipts to notifications and only *tending* to the agent page.
> **Date**: 2026-09-04
> **Dimensional classification** (Axiom 0): **Identity** (Axiom 2 — what an agent *is* determines what can be predicated of it). No Trigger, Mechanism or Substrate change; nothing ships behind this but the refusal itself.
> **Builds on**: [ADR-408](ADR-408-the-coworking-contract-and-the-three-ai-altitudes.md) + [ADR-411](ADR-411-chat-lanes-and-the-lane-tool-surface.md) (a lane write attributes `member:{id} via {model}`; see §2a on the citation) · [ADR-460 D2/D3.a](ADR-460-agents-one-concept-independent-facts-one-gate.md) (the ledger is the fact; consequential authority on an agent is unrepresentable) · [ADR-596 D1/D2](ADR-596-the-agent-is-a-being.md) (authority lives on grants, declarations and gates) · [ADR-600 D2](ADR-600-one-register-hireability-is-a-field.md) (every question about an agent is a *field* on the agent) · [ADR-601 D1](ADR-601-provenance-and-many-to-one.md) (capability lives at the app) · [ADR-610](ADR-610-the-keeper-dissolves-into-the-supervisor.md) (a being is someone a member meets) · [ADR-624 D4](ADR-624-the-being-has-a-home-and-what-it-knows-lives-there.md) (an agent's home is memory + locked grant sidecars)
> **Preserves**: every one of the above. This ADR adds no field, no table, no route.
> **Gate**: `api/test_adr640_no_agent_record.py`.

---

## 1. The question, and why it looked answerable

ADR-603's Consequences say it plainly: *"Runs stop being a concept: receipts
surface in notifications (**what happened**) and on the agent page (**what this
agent tends**)."* Note that the sentence already splits them — receipts to
notifications, *tending* to the agent page. This ADR is largely that split,
enforced. ADR-639
then moved standing work to a kernel lane, mirrored eleven skills into every
workspace, and left the Agents page showing name · provenance · apps · engine ·
memory · connector scope. The natural next step reads as: finish the sentence.
Add *which craft* and *which files* and *what receipts*, and the page becomes
the one place a member understands their colleagues.

Three of those are fine. This ADR is about the fourth.

## 2. What the receipts actually say

Measured against the live production workspace `d5b9029b` on 2026-09-04
(full capture: [`docs/analysis/skills-discovery-and-the-agents-page-2026-09-04.md`](../analysis/skills-discovery-and-the-agents-page-2026-09-04.md)):

| Where a "what this agent did" row would read from | What is there |
|---|---|
| `execution_events.slug` | 494 × `lane` — **no agent column exists** |
| `workspace_file_versions.authored_by` | `operator` (482) · `system:*` (many) · `member:{uuid} via anthropic/claude-sonnet-5` (18) — **no agent ever appears** |
| `chat_sessions.context_metadata.lane.agent` | present, and the only agent-shaped fact in the system |

So the only join is `execution_events.session_id → chat_sessions →
.lane.agent`. It has two defects, and the second is the interesting one.

**It is lossy.** Of 200 sampled `lane` ledger rows, 162 carry a `session_id`.
A page summing that join under-reports by ~19% with no way to say so.

**It is historically true in a way that makes present-tense aggregation
false.** 25 live lanes are stamped `app='text' agent='designer'`. The first
read of that is "a stamping defect". It is not: every one of the 25 is dated
2026-08-14 → 08-20, and **ADR-602 moved Text from Designer to Editor on
2026-08-24**. Designer *really did* hold Text when those conversations
happened. The stamps are correct. The retired slugs in the same join
(`scout`, `keeper`) are correct for the same reason.

⭐ **A truthful per-agent history is not summable in the present tense.**
"Designer — 25 documents" is a true statement about August and a false
statement about who does that work now, and a roster page has no honest place
to put the difference. ADR-460 D2 keeps the ledger unrewritten *deliberately*;
a surface that totals an unrewritten ledger under a present-tense heading
launders history into a current claim.

### 2a. A citation-hygiene note found while writing this

The `member:{id} via {model}` rule is cited **33 times across 26 files in the
repo as "ADR-411 D4"** — `lane_runner.py:17` and `:721`,
`agents_registry.py:14`, `platform_credentials.py:56`, `authored_substrate.py`,
`primitives/workspace.py`, four gates, and a dozen canon documents including
ADR-460, ADR-501, ADR-566 and the ADR-LEDGER. **ADR-411 has no numbered
decisions at all.** The rule is stated in ADR-411 §"Attribution" citing
**ADR-408**, and is preserved and strengthened by **ADR-460** (which retired
ADR-408's altitude table while keeping this fact). The phantom D-number has
been copied forward by every session that grepped for it — including this one,
until the link check failed.

⭐ **A citation that resolves to a file but not to a decision reads as
verified.** The fix is cheap (cite ADR-408/460 for the rule) and is recorded
as owed rather than swept here, because a 26-file rename is its own
commit and this ADR should not carry it.

## 3. The deeper reason: there is no actor to have a record

The attribution rule states a lane write as `member:{id} via {model}` — the
member authored, the engine ran. That is not an omission awaiting a third field. It
is the claim: **an agent is a character the member's hands wear**, and the
substrate records the hands and the tool.

`agents_registry.AGENTS` states the same thing from the other side. Its
`AGENT_ROW_KEYS` whitelist is `{slug, name, blurb, icon, model, token_profile,
posture, offered, kernel}` — identity ⊕ character ⊕ engine, and the module's
own comment: *"There is NO field here for consequential authority, and there
must never be one. The authority is UNREPRESENTABLE, not merely unset."*

A record of deeds is not authority, but it is the same category error running
the other way: it predicates *agency* of something the canon defines as a
costume. ADR-610's test — *a being is someone a member MEETS* — is about
presence, not history. You meet Editor in the Text pane; you do not meet
Editor's résumé.

## D1 — An agent carries no record of what it has done

**No surface, payload, ledger column or derived view may present work,
output, cost or history attributed to an agent as its own.** Specifically:

- `_agents_payload` gains no `runs`, `revisions`, `spend`, `last_active`,
  `history` or equivalent, and no key from which one could be assembled.
- No new join is served from `execution_events` or `workspace_file_versions`
  keyed by agent.
- The Agents page shows **who works here now** — a roster, present tense.
  Where a member wants what happened, the answer is the Activity ledger and
  the file's own history, which are keyed the way the work actually was:
  by member, by engine, by file.

**What is NOT refused**, and stays available: a *conversation* still names who
spoke in it (`conversation_cast`, the transcript, `HISTORICAL_AGENT_NAMES`
resolving a retired slug to the name it signed as). That is the room saying
who was in it — a fact about the conversation, not a dossier on the agent.

## D2 — The two relations that ARE derivable stay derivable, and stay read-only

The audit found two facts the page could honestly gain. Neither is built here;
both are recorded as permitted, so a later commit does not have to re-litigate
the cliff:

- **the craft** — the skills whose `metadata.apps` intersect this agent's apps
  (or that declare none). Computed live: Designer 4 · Editor 10 · Blogger 7.
  Presentation of `services.skills._applies_to`, which the frame already runs.
- **the tending** — the standing declarations whose `resolve_executor()` is
  this agent. Computed live: both live declarations → `editor`. Presentation of
  a pure function the run already calls.

Both are **relations the kernel already derives**, stated read-only. Neither
is settable from a surface: a door that *assigns* a skill, a file or reach to
an agent is authority on an agent and is refused by ADR-596 D1, unchanged.

## D3 — Where "who keeps this current?" is answered

At the declaration, not at the agent. `GET /api/standing` already serves
`app`; the Standing work pane renders neither `app` nor the derived executor.
If that question is worth answering it is answered there, where the member is
already looking at the file — not by giving the agent a page of its deeds.

## 4. The rule this ADR leaves behind

> **An agent is met, not audited.** The roster says who works here now; the
> ledger says what happened and who authorized it. A surface that merges them
> gives a costume a career.

## 5. Consequences

- The Agents page's scope is settled: a present-tense roster, plus at most two
  derived read-only relations (D2). It does not become a dossier, and ADR-603
  D4's sentence is answered as far as the substrate honestly allows.
- One fewer plausible-looking join in the codebase's future: the
  `session_id → lane.agent` path is now documented as *correct and
  unaggregatable*, so the next session that finds it does not build on it.
- No migration, no payload change, no deletion. The cost of this ADR is one
  gate.

## 6. Gate

`api/test_adr640_no_agent_record.py`:

- `_agents_payload` serves no history-shaped key (whitelist, falsified by construction).
- `AGENT_ROW_KEYS` still carries no history-shaped key — the ADR-460 whitelist, extended in spirit.
- No route or service composes an agent-keyed aggregate over `execution_events` or `workspace_file_versions`.
- The two D2 derivations exist and are pure (`_applies_to`, `resolve_executor`) — asserted so a later change that makes them impure is red.

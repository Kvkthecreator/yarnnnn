# Layer Mapping — Agents as a Fact-Vector, and Orchestration

> **Status**: Canonical (internal)
> **Date**: 2026-04-24; **rewritten 2026-07-18 (ADR-460)** — the three-AI-altitude *ladder* is dissolved into a **fact-vector**: one concept (Agent) whose facts vary independently, with the one non-dial fact (consequential authority) relocated to the ADR-307 gate. The three *distinctions* the altitude table drew (management / member-hands / judgment) are **preserved and strengthened** — as fact-clusters, not rungs (ADR-460:9). Prior amendment chain: ADR-216 → 217 → 247 → 249 → 251 → 272 → 414 (three altitudes, folded) → 460 (this rewrite). The pre-460 three-altitude version is preserved in git history.
> **Authors**: KVK, Claude
> **Scope**: The authoritative taxonomy for every acting entity in YARNNN. Names each, classifies it, and specifies where it lives in code and substrate.
> **Audience**: Internal. The philosophical claim behind the taxonomy lives in [THESIS.md](THESIS.md) §Vocabulary; the axes-of-classification history lives in [AGENT-TAXONOMY.md](AGENT-TAXONOMY.md); the model itself in [ADR-460](../adr/ADR-460-agents-one-concept-independent-facts-one-gate.md).

---

## The principals — above every AI classification

Before any AI taxonomy, there are the **human principals**: the workspace has N of them (ADR-373/407, DP17 v9.15), each holding a `principal_grants` row, each one principal with two runtime embodiments — the cockpit shell and the external-LLM interop face. The **owner** remains the constitutional author (ADR-386 D4). The coworking contract (ADR-408 D1): a principal acting within their grant **binds immediately** (after-witness); peers are told, never asked; approval queues belong to agents, never to members; no rule keys on species (human vs AI) or role enum.

The workspace itself is the **commons** — the authored, attributed, portable substrate every actor settles work into (ESSENCE v15: the system of record where human and AI work settles). Everything below exists to act *on* the commons under a grant.

---

## There is one concept: an Agent. Its facts are independent. (ADR-460)

**The three-altitude ladder is retired** (ADR-460 D1). "Altitude" was never a dimension — it was a *bundle* of facts that vary independently, and reasoning about the ordinal (A1 < A2 < A3) instead of the facts was the drift Axiom 0 names. The runtime never had altitudes: the gate branches on one question — *does this write attribute to a human, or to itself?* — and that is a two-valued fact, not a three-rung ladder.

> **An Agent is a named, configured entity. Its facts are independent and optional: it may or may not carry a persona; may or may not carry governance files; may or may not hold standing intent. There is no ordinal. Configuration is a vector, not a rung.** (ADR-460:72)

### The five facts (the vector)

| Fact | Dimension | Range | Where it lives |
|---|---|---|---|
| **Attribution** | Identity (Axiom 2) | `member:{id} via {model}` **or** `agent:{slug}` | `VALID_AUTHOR_PREFIXES`; branched by `_caller_class` |
| **Configuration** | Mechanism (Axiom 5) | engine · tools · posture · token profile | the Agent registry (`agents_registry.py`) |
| **Standing intent** | Trigger (Axiom 4) | none (addressed-only) → wake sources | ADR-296 wake sources |
| **Governance files** | Substrate (Axiom 1) | none → persona/mandate/principles | ADR-383 (same schema, different content) |
| **Consequential authority** | **the gate, NOT the entity** | witness-first → autonomous | **[ADR-307](../adr/ADR-307-unified-permission-taxonomy.md) `execute_primitive()`** |

**Four are dials. One is a cliff** — consequential authority — and it is not a property of the entity at all. It is the ADR-307 gate, and it is **unrepresentable** in the kernel Agent registry by construction (ADR-460 D3.a; `test_agent_registry.py` fails if a field for it is added). This is the anti-oscillation ratchet the pre-460 eras lacked: the one boundary that must never become a "kind" cannot be expressed as one.

---

## The three fact-clusters (what the altitudes were pointing at)

The altitude table drew three real distinctions. They survive — as **recurring clusters of fact-values**, the shapes an Agent commonly takes — not as ranked kinds. "Same chrome must never imply same kind" holds exactly as before; what changes is that "kind" is now *read off the facts*, not asserted by an ordinal.

| Cluster (the shape) | Attribution | Standing intent | Governance | Consequential authority | Cardinality | Chrome home |
|---|---|---|---|---|---|---|
| **The system agent** — Freddie | `agent:system-agent` / `freddie:` (internal `reviewer` slug, data-compat) | steward wake sources | **kernel constants** (no persona files, ADR-414 D2) | the steward dial (`governance/_autonomy.yaml`); substrate-family autonomous (ADR-408 D3) | exactly one per workspace | **the rail only** (chat drawer) + Workspace Settings → System Agent. Never a roster card |
| **Member hands** — kernel agents + lanes | **`member:{id} via {model}`** (ADR-411 D4) — *not a principal* | **none** (addressed-only) | none | **none** — binds after-witness *as the member*, under the member's grant | zero-to-many per member | **`/chat`** (the lane) + **`/agents`** (the roster of who you can address) |
| **Judgment agents** — hired persona / domain Agents | `agent:{slug}` — own principal, own grant row (ADR-414 D5) | own wake sources | the full ADR-383 file set (IDENTITY, MANDATE, principles) lives here | own witness dial; the Rung-2 exogenous clock for consequential action (ADR-380) | zero-to-many per workspace | **`/agents`** (as tenure-bearing, fiduciary Agents) |

**Reading the clusters as facts, not rungs:**
- Freddie is *management* — accountable for the desk running clean, never for a production outcome. It is **judgment-free and kernel-constituted**; rendering it as a roster peer or auditing it against a production obligation are category errors (ADR-380 D3, ADR-412 D5).
- **Member hands** attribute *as the member* — the load-bearing fact ADR-408 D2 established, now *strengthened* (ADR-460:9): a lane helper is not a class of caller, it resolves to `operator` because it **is** the member. A named kernel agent (`Sonnet`) running as the member's hands **does not become a principal by acquiring a name** — the face is an Agent, the ledger says the member's hands.
- **Judgment agents** attribute *as themselves* and carry the four commitments of the operation (declared intent · independent judgment · ground-truth evaluation — DP24/DP30/Axiom 8, ADR-382 §3). This is where the *sharp* word "Agent" (fiduciary, tenure-accumulating) is heaviest — but it is a **cluster of fact-values**, not a floor an entity must reach to be called an Agent.

### The `/agents` roster holds member hands AND judgment agents (corrected)

> ⚠️ **Correction (ADR-460, 2026-07-18).** The pre-460 doc said *"the roster is Altitude 3 only."* **That is now false.** The kernel Agent registry (`Sonnet · Scout · Critic · Designer`) ships on `/agents`, and those are **member hands** (`member:` attribution, no standing intent) — a member-hands cluster, not a judgment cluster. `/agents` is *"who you can address / hire"* — it spans the member-hands cluster (the base agents + a member's own named instances) and, when hired, the judgment cluster (persona agents). Freddie is the one thing that is **never** on the roster (it is the rail, not a colleague). The industry-`agent` note stands but re-reads: what the operator sees on `/agents` are Agents in the *addressable-colleague* sense, of which the *judgment* cluster is the sharpest but not the only, kind.

### Accountability, two orders (ADR-382 §3, preserved verbatim — a mandate-holding fact, never an altitude fact)

| Accountability | Holder | Example |
|---|---|---|
| **Judgment** — the operation's calls, its mandate's reachability | the judgment-cluster agent | the trader answers for the trades |
| **System** — the desk, who was hired, substrate integrity, arbitration | Freddie | the manager answers for the workspace running clean |

---

## Orchestration (unchanged class, collapsed surface)

**Orchestration** remains the non-Identity-bearing machinery: primitive dispatch, the wake funnel + queue + drainer (ADR-296/298), scheduler, the compositor, protocol drivers (ADR-413). Stateless per Axiom 1; configurations to tune, never occupants to rotate; writes carry the invoking principal's identity, never their own.

> **Note on production roles.** The historical capability bundles (`researcher/analyst/writer/tracker/designer/reporting`) survive in canon as orchestration vocabulary, but the live `PRODUCTION_ROLES` registry is **empty** (collapsed 6→1→0 across ADR-272→ADR-417); `DispatchSpecialist` is a dormant seam. The current agent *capability* axis is the kernel registry's `tools` field (ADR-463) + skills (ADR-464), not a role catalogue. See [AGENT-TAXONOMY.md](AGENT-TAXONOMY.md) §2 Axis-4 for why the role *roster* dissolved while the cognitive-function *vocabulary* survived.

**The ADR-216 seam is collapsed (ADR-414 D3).** "YARNNN the orchestration chat surface" as an entity distinct from the agent is retired: there is **one system agent, and the rail is its voice**. The `thinking_partner` agents-table row is retired; `session_type='thinking_partner'` survives as a data-compat slug (GLOSSARY exception). **YARNNN is the brand and the system's name**, not an entity in this table.

---

## Specific clarifications (to prevent drift)

1. **Agents use tools; that doesn't make them orchestration.** A judge uses court records. Every actor calls primitives through the same `execute_primitive` gate.
2. **Lane helpers / base agents are not junior judgment agents.** They have no standing intent, no home, no dial, no principal-hood — they are the member's hands. This is a *fact difference* (empty standing-intent, `member:` attribution), not a rank.
3. **The steward is not a persona agent with an empty persona.** It is a different fact-cluster: kernel-constituted, judgment-free, one-per-workspace. Roster-peer / persona-editor / production-audit are all category errors.
4. **Programs are hires, not types** (ADR-414 D5). Activation mints a judgment-cluster grant row and installs the bundle into the agent's home. The workspace is never typed.
5. **External LLM callers (MCP) are the member's embodiment**, not a separate kind — the same principal through the interop face (DP17 two-embodiments).
6. **The base agents (`Sonnet/Scout/Critic/Designer`) are the member-hands cluster**, typed by the *reason a member reaches for a colleague* (a verb: think/read/pressure-test/make — [AGENT-TAXONOMY.md](AGENT-TAXONOMY.md) Axis 6). **Whether that roster is complete or representative is an OPEN question, not settled canon** — see the note below.

> **Open: is the base roster complete/representative?** (flagged 2026-07-18) The four base agents are the current member-hands roster, but the *vocabulary of reasons* has never been derived from first principles — ADR-176 asserted six cognitive roles, the kernel ships four verbs, and neither proved its set. A recommendation exists (`docs/analysis/the-recommended-agent-set-2026-07-18.md`) arguing four is complete *by construction* for the addressed-no-standing-intent space; **that argument is contested and not ratified.** This doc records the roster as *current*, never as *complete*. A fifth base agent is a live possibility; the discipline (AGENT-TAXONOMY §4) is only that it must be a new **verb**, not a modality/output/platform/domain of an existing one.

---

## The filesystem rule

| Fact-cluster | Cardinality | Path shape |
|---|---|---|
| System agent (Freddie) | one per workspace | **No persona path** — kernel constants + `governance/_autonomy.yaml` + `governance/_budget.yaml` (ADR-414 D2) |
| Judgment agent / domain Agent | zero-to-many | `agents/{slug}/` — home carries the full ADR-383 file set (+ `skills/*.md`, ADR-464) |
| Member hands — base agents | fixed kernel set | **kernel constants** (`KERNEL_AGENTS`) — not member-owned |
| Member hands — named instances | zero-to-many per member | `agents/{slug}/_agent.yaml` (+ `skills/`) — a member's own colleague, `based_on` a kernel verb (ADR-449/460) |
| Member hands — lanes | zero-to-many per member | none — transcripts are member-experience scope (`chat_sessions`); work lands in the commons |
| Orchestration | n/a | `system/` accumulation only; never Identity-bearing |

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-23/24 | v1/v1.1 — the sharp Agent/Orchestration split (ADR-212/216) |
| 2026-05-04→14 | ADR-249 operator-runtime amendment; ADR-251 System Agent label; ADR-272 System-Agent-as-cockpit-entity dissolved |
| 2026-07-07 | v2 — the three-altitudes taxonomy (ADR-414) |
| 2026-07-18 | **v3 — the ladder dissolves into a fact-vector (ADR-460).** Three ranked altitudes → one concept + five independent facts + one gate. The three distinctions preserved as fact-clusters, not rungs. Corrected the false *"roster is Altitude 3 only"* line (the base agents are member-hands on `/agents`). Roster-completeness flagged as an OPEN, contested question, not settled canon. Cross-linked AGENT-TAXONOMY.md. |

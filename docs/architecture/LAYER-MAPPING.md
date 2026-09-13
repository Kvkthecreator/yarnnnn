# Layer Mapping — Agents as a Fact-Vector, and Machinery

> **Status**: Canonical (internal)
> **Date**: 2026-04-24; rewritten 2026-07-18 (ADR-460 — the altitude ladder dissolves into a fact-vector); **v4 recut 2026-09-12 (ADR-596/600/624/632)** — the management cluster is deleted with the steward, the vector's facts are restated on the agent as ADR-596 defines it, and orchestration is named machinery. v3 is archived verbatim at [previous_versions/LAYER-MAPPING-v3-2026-09-12.md](previous_versions/LAYER-MAPPING-v3-2026-09-12.md).
> **Authors**: KVK, Claude
> **Scope**: The authoritative taxonomy for every acting entity in YARNNN. Names each, classifies it, and specifies where it lives in code and substrate.
> **Audience**: Internal. The philosophical claim lives in [THESIS.md](THESIS.md) §Vocabulary; the axes-of-classification history in [AGENT-TAXONOMY.md](AGENT-TAXONOMY.md); the model in [ADR-460](../adr/ADR-460-agents-one-concept-independent-facts-one-gate.md) and [ADR-596](../adr/ADR-596-the-agent-is-a-being.md).

---

## The principals — above every AI classification

Before any AI taxonomy, there are the **human principals**: the workspace has N of them (ADR-373/407), each holding a `principal_grants` row, each acting through embodiments — the desktop, a lane, the interop face — that are all *that principal* (FOUNDATIONS DP17). The **owner** remains the constitutional author (ADR-386 D4) and the root of every grant chain (ADR-596 D1). The coworking contract (ADR-408 D1): a principal acting within their grant **binds after-witness**; peers are told, never asked; no rule keys on species (human vs AI) or role enum (ADR-405).

The workspace itself is the **commons** — the authored, attributed, portable substrate every actor settles work into (ESSENCE: the system of record where human and AI work settles). Everything below exists to act *on* the commons under a grant.

---

## There is one concept: an agent. Its facts are independent. (ADR-460 → ADR-596)

**The three-altitude ladder is retired** (ADR-460 D1). "Altitude" was never a dimension — it was a *bundle* of facts that vary independently. The runtime never had altitudes: the gate branches on one question — *does this write attribute to a human, or to itself?* — a two-valued fact, not a three-rung ladder.

> **An agent is identity ⊕ character ⊕ engine, and nothing else.** (ADR-596 D1) An agent row carries identity facts only — never authority, never reach, never a clock. Authority attaches to relations and declarations, never to beings; it is granted, audited, revocable, and enforced by kernel gates.

### The five facts (the vector, restated)

| Fact | Dimension | Range today | Where it lives |
|---|---|---|---|
| **Attribution** | Identity (Axiom 2) | `member:{id} via {model}` (a lane) · `system:standing` (a run) · `system:*` (machinery) · `agent:{slug}` only for a hired agent's own principal (ADR-414 D5; none exist) | `VALID_AUTHOR_PREFIXES`; the acting principal on the ledger row |
| **Configuration** | Mechanism (Axiom 5) | identity · character (posture) · engine · token profile | the one register — `AGENTS` in `api/services/agents_registry.py` (ADR-600) |
| **Standing intent** | Trigger (Axiom 4) | **none, on any agent** (ADR-596 D1) — standing work is a *member's* declaration beside the file it keeps (ADR-603/639) | `{folder}/_standing.yaml` + `CONTRACT.md` |
| **Governance files** | Substrate (Axiom 1) | **none** — an agent's home is `memory/` + two locked grant sidecars; the twelve-file set is deleted (ADR-624) | `agents/{slug}/` |
| **Consequential authority** | **the gate, NOT the entity** | witness-first → autonomous, per family, set by the member | [ADR-307](../adr/ADR-307-unified-permission-taxonomy.md) `execute_primitive()` · the witness dial (ADR-405) · the one access decider (ADR-643) |

**One is a dial the member turns, three are now constants, and one is a cliff** — consequential authority — which is not a property of the entity at all and is **unrepresentable** in the register by construction (ADR-460 D3.a; `test_agent_registry.py` fails if a field for it is added; ADR-636 enforces the same whitelist on the client row). This is the anti-oscillation ratchet: the one boundary that must never become a "kind" cannot be expressed as one.

---

## The clusters (what the altitudes were pointing at)

| Cluster | Attribution | Standing intent | Governance | Consequential authority | Cardinality | Where it is met |
|---|---|---|---|---|---|---|
| **Member hands** — the kernel agents in a member's lanes (Designer · Editor · Blogger) | `member:{id} via {model}` — *not a principal* | none | none (memory + sidecars) | **none of its own** — binds after-witness *as the member*, under the member's grant | one register; N lanes per member | **Chat** (the lane) + **Agents** (the register, sectioned by app with provenance — ADR-600; no record of its own — ADR-640) |
| **Residents at work** — the same agents doing standing work | `system:standing` on the member's declaration | none — the *declaration* carries the schedule | none | **none** — toolless, contract-checked, refused any outbound credential (ADR-603/618/645) | one run per due declaration | Notifications → Standing work (the receipts); never a chat |
| **Hired agents** — a program's judgment cluster | `agent:{slug}`, own grant row (ADR-414 D5) | none on the agent; the *program's* mandate and standing declarations | memory + sidecars | the witness dial the member set for it; review only as a declared grant (ADR-596 D3(d)) | zero today | Agents, when hired |
| ~~**The system agent** — Freddie / the steward~~ | — | — | — | — | **deleted (ADR-632)** | nowhere: substrate integrity is machinery + the member; the `freddie:` prefix survives on historical revisions, display-resolved |

**Reading the clusters as facts, not rungs:**
- **Member hands** attribute *as the member* — the load-bearing fact (ADR-408 D2, strengthened by ADR-460): a lane helper is not a class of caller; it **is** the member's hands. A named agent does not become a principal by acquiring a name — the face is an agent, the ledger says the member.
- **A resident at work** is the same agent under a different attribution because the *trigger* differs (a declaration came due) — not a different kind of entity, and not one with a clock of its own.
- **Hired agents** are the only cluster that ever attributes as itself, and only because a program's activation mints a grant row for it. None exist on production; the cluster is a shape the register admits, not a floor an entity must reach to be called an agent.

### The `/agents` surface

The Agents pane shows **the one register** sectioned by app, with provenance served (which app, which resident, whether offered — ADR-600/601). It answers *who can I work with*, never *what did they do*: no work list, output, cost or history is attributed to an agent (ADR-640 — an agent is met, not audited). The cast of a conversation is joined from inside it (ADR-495/558), never chosen on the roster.

### Accountability

| Accountability | Holder | Example |
|---|---|---|
| **Judgment** — whether a consequential act binds | the member's verdict under the witness dial (ADR-632 D2); a granted review when one exists | the member executes the trade proposal |
| **Contract** — whether a kept file is true | the standing declaration's `CONTRACT.md`, checked by the kernel on every run (ADR-603/618) | the run refuses when the contract is unmet |
| **System** — substrate integrity, the desk running clean | machinery (the mirrors, the gates, the drain loop) + the member (the grants) | the skills mirror; the one access decider |

---

## Machinery (was: Orchestration)

**Machinery** is the kernel code that runs unconditionally under a `system:*` attribution: the one drain loop, capture, the kernel mirrors (skills, faces), the compose engine, the gates, the compositor. Stateless per Axiom 1; configurations to tune, never occupants to rotate; it holds no grants and no character of its own. It may wear an agent's costume for display (a standing run resolving the app's resident) while attributing `system:standing` (ADR-596 D1).

The historical vocabulary — production roles, capability bundles, the wake funnel and queue, the ADR-216 "YARNNN the orchestration chat surface" — is retired; **YARNNN is the brand and the system's name**, not an entity in this table.

---

## Specific clarifications (to prevent drift)

1. **Agents use tools; that doesn't make them machinery.** Every actor calls primitives through the same `execute_primitive` gate; what differs is the attribution and the grant.
2. **Lane helpers are not junior judgment agents.** They have no standing intent, no dial, no principal-hood — they are the member's hands. This is a *fact difference* (empty standing intent, `member:` attribution), not a rank.
3. **There is no system agent.** Substrate integrity is machinery's and the member's. A proposal to reintroduce a systemic, persona-bearing agent with a clock re-opens ADR-632; the answer is a grant or a gate, never a seat.
4. **Programs are hires, not types** (ADR-414 D5). Activation mints a grant row and installs the bundle; the workspace is never typed.
5. **External LLM callers (MCP) are the member's embodiment**, not a separate kind — the same principal through the interop face (DP17).
6. **Whether the register is complete is an open question, never settled canon.** Three kernel agents ship today, typed by the app they serve; a new one is a new *character for a medium the existing ones do not cover*, never a modality, output or platform of an existing one ([AGENT-TAXONOMY.md](AGENT-TAXONOMY.md) §4).

---

## The filesystem rule

| Cluster | Cardinality | Path shape |
|---|---|---|
| An agent's home (ADR-624) | one per agent | `agents/{slug}/` — **exactly two things**: `memory/` (what it KNOWS — freely writable by it, ordinary substrate) and the grant sidecars `_autonomy.yaml` + `_budget.yaml` (locked). ⚠️ The ADR-414 twelve-file set is **deleted, not dormant**. |
| The register | one | **kernel constants** — identity ⊕ character ⊕ engine (`AGENTS`). The home holds what an agent learns; the register holds what it is. A member-authored agent is a `kernel: False` row in the same register (ADR-601 D2). |
| Lanes | zero-to-many per member | none — transcripts are member-experience scope (`chat_sessions`); work lands in the commons |
| Standing declarations | zero-to-many per workspace | `{folder}/_standing.yaml` + `CONTRACT.md`, beside the kept file — a member's, never an agent's |
| Machinery | n/a | `system/` — the mirrors and runtime state; never Identity-bearing |

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-23/24 | v1/v1.1 — the sharp Agent/Orchestration split (ADR-212/216) |
| 2026-05-04→14 | ADR-249 operator-runtime amendment; ADR-251 System Agent label; ADR-272 System-Agent-as-cockpit-entity dissolved |
| 2026-07-07 | v2 — the three-altitudes taxonomy (ADR-414) |
| 2026-07-18 | v3 — the ladder dissolves into a fact-vector (ADR-460) |
| 2026-09-12 | **v4 — the post-steward recut (ADR-596/600/624/632).** The management cluster deleted; the five facts restated on the agent as identity ⊕ character ⊕ engine (standing intent and governance files are constants: none); the residents-at-work row added (same agent, different trigger); orchestration renamed machinery; accountability restated as judgment (the member's verdict) · contract (the kernel's check) · system. v3 archived verbatim. |

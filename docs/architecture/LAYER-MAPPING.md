# Layer Mapping — The Three Altitudes and Orchestration

> **Status**: Canonical (internal)
> **Date**: 2026-04-24; **rewritten 2026-07-07 (ADR-414, per ADR-408 D2 + ADR-381 D4 + ADR-382 §3)** — the two-class Agent/Orchestration taxonomy is re-instantiated as the **three AI altitudes**; the ADR-216 orchestration-surface seam is collapsed (ADR-414 D3). Prior amendment chain: ADR-216 → 217 → 247 → 249 → 251 → 272 (all folded; the pre-rewrite doc with its implementation-planning history is preserved in git history at commit ac85b35 and earlier).
> **Authors**: KVK, Claude
> **Scope**: The authoritative taxonomy for every acting entity in YARNNN. Names each, classifies it, and specifies where it lives in code and substrate.
> **Audience**: Internal. The philosophical claim behind the taxonomy lives in [THESIS.md](THESIS.md) §Vocabulary; the altitude/chrome pairing lives in [ADR-412](../adr/ADR-412-three-altitudes-three-chromes.md); the coworking contract in [ADR-408](../adr/ADR-408-the-coworking-contract-and-the-three-ai-altitudes.md).

---

## The principals — above every AI classification

Before any AI taxonomy, there are the **human principals**: the workspace has N of them (ADR-373/407, DP17 v9.15), each holding a `principal_grants` row, each one principal with two runtime embodiments — the cockpit shell and the external-LLM interop face. The **owner** remains the constitutional author (ADR-386 D4). The coworking contract (ADR-408 D1): a principal acting within their grant **binds immediately** (after-witness); peers are told, never asked; approval queues belong to agents, never to members; no rule keys on species (human vs AI) or role enum.

The workspace itself is the **commons** — the authored, attributed, portable substrate every actor settles work into (ESSENCE v15: the system of record where human and AI work settles). Everything below exists to act *on* the commons under a grant.

---

## The Three AI Altitudes (ADR-408 D2)

One table, three kinds, each with exactly one chrome home (ADR-412 — "placement is the pedagogy"):

| Altitude | Entity | Cardinality | Identity & attribution | Persona? | Dial? | Substrate home | Chrome home |
|---|---|---|---|---|---|---|---|
| **1 — the system agent** | **Freddie** (operator-relabelable) | Exactly one per workspace, serving N member sessions | `agent:system-agent` / `freddie:` attribution prefix; internal `reviewer` slug retained (data-compat) | **No** — steward role; identity/mandate/principles are **kernel constants** (ADR-414 D2) | Own witness dial (`governance/_autonomy.yaml`; substrate family autonomous per ADR-408 D3) + budget allocation | Kernel constants + the two dial files; **no persona files** | **The rail only** (chat drawer); inspection at Workspace Settings → System Agent. Never a window, launcher tile, roster card, or chat-among-chats |
| **2 — seat-level helpers (lanes)** | The member's model-pinned helper threads | Zero-to-many per member | **The member's** — `member:{user_id} via {model}` (ADR-411 D4); **not principals**, no principal machinery | No — and the mount never carries behavior (ADR-413 D3) | **No dial of its own** — acts under the member's grant, binds after-witness like the member | None (transcripts are member-experience scope; work lands in the commons) | **The Chat surface** (`/chat`) |
| **3 — judgment agents** | **Persona agents** (program hires) + **user-authored domain Agents** | Zero-to-many per workspace; each recorded as a **grant row** (ADR-414 D5) | Own principal; own attribution (`agent:{slug}`) | **Yes** — the full ADR-383 file set lives HERE (IDENTITY, MANDATE, principles, governance sidecars) | Own witness dial, per-family; Rung-2 clock for consequential action (ADR-380) | `agents/{slug}/` — the agent's home | **`/agents`** — the roster is Altitude 3 only (ADR-412 D5) |

**The sharp word "Agent" lands at Altitude 3** — judgment-bearing, fiduciary, standing intent, tenure-accumulating (THESIS §Vocabulary's claim, unchanged). Altitude 1 is management infrastructure with a voice; Altitude 2 is the member's hands. Same chrome must never imply same kind.

### Where the four commitments attach (THESIS two-order re-derivation)

- **Authored accumulation** → the **workspace commons** (the floor; the moat).
- **Declared intent, independent judgment, ground-truth evaluation** → the **hired Altitude-3 agent's operation** (DP24/DP30/Axiom 8 relocated per ADR-382 §3 / FOUNDATIONS v9.16).
- The **system agent** carries the stewardship standing-obligation only (substrate coherent, attributed, placed, legible) — never a production obligation, never a ground-truth loop.

### Accountability, two orders (ADR-382 §3)

| Accountability | Holder | Example |
|---|---|---|
| **Judgment** — the operation's calls, its mandate's reachability | The Altitude-3 persona agent | The trader answers for the trades |
| **System** — the desk, who was hired, substrate integrity, arbitration | Freddie | The manager answers for the workspace running clean |

---

## Orchestration (unchanged class, collapsed surface)

**Orchestration** remains the non-Identity-bearing machinery: primitive dispatch, the wake funnel + queue + drainer (ADR-296/298), scheduler, capability bundles (production roles: researcher/analyst/writer/tracker/designer/reporting; platform integrations: Slack/Notion/GitHub/Commerce/Trading), the compositor, protocol drivers (ADR-413). Stateless per Axiom 1; configurations to tune, never occupants to rotate; writes carry the invoking principal's identity, never their own.

**The ADR-216 seam is collapsed (ADR-414 D3).** "YARNNN the orchestration chat surface" as an entity distinct from the agent is retired: there is **one system agent, and the rail is its voice**. The seam ADR-216 drew separated orchestration from *judgment* — and judgment moved to Altitude 3, so the seam now runs between Altitude 1 and Altitude 3, not through the chat surface. The `thinking_partner` agents-table row is retired (ADR-414 D3 migration); `session_type='thinking_partner'` survives as a data-compat slug (GLOSSARY exception). **YARNNN is the brand and the system's name**, not an entity in this table.

---

## Specific clarifications (to prevent drift)

1. **Agents use tools; that doesn't make them orchestration.** A judge uses court records. The persona agent calls primitives through the same `execute_primitive` gate as everyone; that's Agents-using-tools.
2. **Lane helpers are not junior agents.** They have no standing intent, no home, no dial, no principal-hood — widening the lane tool surface beyond the five file verbs is a policy change with its own ADR (ADR-411 D3 / ADR-413 D5).
3. **The steward is not a persona agent with an empty persona.** It is a different kind: kernel-constituted, judgment-free, one-per-workspace. Rendering it as a roster peer, giving it a persona editor, or auditing it against a production obligation are all category errors (ADR-380 D3, ADR-412 D5, DP30 two-order annotation).
4. **Programs are hires, not types** (ADR-414 D5). Activation mints an Altitude-3 grant row and installs the bundle into the agent's home. The workspace is never typed; `parse_active_program_slug` and the MANDATE prose marker are deleted vocabulary.
5. **External LLM callers (MCP) are the member's embodiment**, not a fourth altitude — the same principal through the interop face (DP17 two-embodiments, generalized).
6. **Industry "agent" vocabulary** (LLM + tools + loop) maps closest to Altitude-2 helpers and orchestration capability bundles. YARNNN's sharp usage reserves the word for Altitude 3. External UI aligns naturally: what the operator sees on `/agents` ARE Agents in the sharp sense.

---

## The filesystem rule

| Entity class | Cardinality | Path shape |
|---|---|---|
| System agent (Altitude 1) | one per workspace | **No persona path** — kernel constants + `governance/_autonomy.yaml` + `governance/_budget.yaml` (ADR-414 D2) |
| Persona agent / domain Agent (Altitude 3) | zero-to-many | `agents/{slug}/` — home carries the full file set (ADR-414 D6) |
| Lane helper (Altitude 2) | zero-to-many per member | none — transcripts are member-experience scope (`chat_sessions`), work lands in the commons |
| Orchestration | n/a | `system/` accumulation only; never Identity-bearing |

The pre-2026-07 systemic path (`/workspace/persona/` — the six seat files) was the one-judgment-seat world's home; its contents re-home per ADR-414 D5/D6 (the operation persona to the hired agent's home; the steward's to kernel constants). The path-named-by-role convention survives only in the minimized DP25 residue (principal-homes).

---

## Revision history

| Date | Change |
|------|--------|
| 2026-04-23/24 | v1/v1.1 — the sharp Agent/Orchestration split (ADR-212/216); registry restructure; six-commit landing plan (see git history for the full planning record) |
| 2026-05-04→14 | ADR-249 operator-runtime amendment; ADR-251 System Agent label; ADR-272 System-Agent-as-cockpit-entity dissolved |
| 2026-07-07 | **v2 — rewritten to the three-altitudes taxonomy (ADR-414).** Two classes → three altitudes + orchestration; ADR-216 seam collapsed (one system agent, the rail is its voice); four commitments re-attached (commons vs hired agent); accountability two-order table added; filesystem rule updated to kernel-constants + agent-homes; programs = hires. |

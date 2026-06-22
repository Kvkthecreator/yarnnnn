# ADR-357 — A Citation Binds a Claim to its Source, Never to the Internal Path (Citation Discipline)

**Status**: Implemented (2026-06-22)
**Dimensional classification**: **Substrate** (Axiom 1 §8 — perception) + **Channel** (Axiom 6 — how authored output references its provenance)
**Implements**: FOUNDATIONS Derived Principle 31 (new) — the authoring/output twin of Derived Principle 27 (the Perception Field, ADR-335).
**Extends / reuses (no new taxonomy)**: ADR-335 (`source_ref` on the Observation contract — the true Source), ADR-209 (`authored_by` — Attribution), ADR-330 (the attestation enum). This ADR adds a *binding rule* between concepts that already exist; it invents none.
**Preserves**: ADR-306 / DP22 (the minimal frame — this adds one interface-grammar clause, not a section), agent-composition §3.2.1 (the partition — recorded there in the same commit), the anti-confabulation action-grammar (this is its perception-field instance).
**Driving evidence**: the 2026-06-22 citation-verification of the first repo-watch-authored piece (`docs/evaluations/2026-06-22-author-the-agent-authors-VALIDATION.md` + this session's verification): every cited receipt traced to perceived substrate (no hallucination), but the citations were *bare names* ("ADR-354") with no resolvable Source — the gap was *form*, not honesty.

---

## 1. Problem statement — three concepts were tangling at authoring time

The first piece authored from a repo watch (ADR-356) cited its claims as bare names: "ADR-306", "ADR-342's original sin", "ADR-354". Verification showed **every citation traced to perceived substrate** — all 4 execution-event IDs and 3 ADR refs were present in the `_repo_signal.yaml` the agent read through the GitHub MCP watch. So the agent did not hallucinate; it authored honestly from what it perceived.

But a reader cannot *verify* a bare "ADR-354" — it points at nothing resolvable. And the bundle's own sourcing rule said *"a card whose number cannot be traced to a workspace file does not ship"* — which tells the agent to trace to the **internal filesystem path** (`/workspace/operation/authored/_repo_signal.yaml`), the place *this operation filed its distilled copy*, not the place the truth lives. That is exactly the confusion: three distinct concepts were being conflated.

The operator named the decomposition precisely: *"the actual source of the content (github repo, websearch website url) is the right concept; the internal file system is more about attribution."*

## 2. The three concepts (all but one already in canon)

| Concept | Question it answers | Canon name | Status before this ADR |
|---|---|---|---|
| **Source** | Where did this come from *in the world*? | `source_ref` (ADR-335 Observation / DP27) | Existed — but stopped at the watch signal; never propagated to authored artifacts. |
| **Attribution** | Who *in YARNNN* wrote this down? | `authored_by` (ADR-209) | Existed and correct — the internal-record concept, done right. |
| **Internal path** | Where is the distilled copy filed? | the `workspace_files.path` | Plumbing — was being mis-used as a citation target. |
| **Citation** | What claim rests on which Source? | — | **Missing** — no rule said "bind to Source, not path." |

The vocabulary wasn't missing; the **binding rule** was. `source_ref` is the true Source and it is *already paired with each excerpt* in the observation block — the agent had it available and cited the bare name anyway, because nothing told it to use the `source_ref`, and the bundle rule actively pointed it at the internal file.

## 3. Decision

**D1 — Derived Principle 31 (FOUNDATIONS).** A **citation** binds a claim to its **Source** (the observation's `source_ref`); never to the internal filesystem path (where the distilled copy lives), never to `authored_by` (who recorded it). This is the authoring/**output** twin of DP27's perception/**input** contract: DP27 fixes how reality enters (`{source_ref, attestation, observed_at, distilled_content}`); DP31 fixes how a claim grounded in it exits (citing that `source_ref`). **Source and Attribution are orthogonal**: Source = where it came from in the world; Attribution = who wrote it down here.

**D2 — The floor: a claim with no resolvable Source does not ship.** The perception-field instance of the anti-confabulation rule — you may not assert (or cite) what you cannot point at. This *replaces* "trace to a workspace file" wherever it appears (that phrasing encodes the internal-path confusion D1 forbids).

**D3 — Where it lands (per §3.2.1).** The *interface-grammar* (cite the Source not the path; attribution is separate) is **frame-resident** — one clause appended to the persona-frame action-grammar's existing "cite what drove your verdict" clause (same category: making provenance legible; not a rule of judgment; DP22-legal because it is the model↔runtime contract for how authored output references perceived input). The per-program *sourcing rule* lives in `principles.md` / the bundle authoring spec.

**D4 — Kernel-wide, not program-private.** Any program that authors from observations inherits this (it is a property of authoring-from-perception, not an alpha-author quirk). The principle is kernel-level; each program's `principles.md`/spec carries its instance of the no-unsourced-claim floor.

## 4. Validation (proven before canonizing)

The kernel frame clause was added, then `compose-piece` was re-fired on yarnnn-author (exec_event `82a17a2f`, autonomous). The agent re-authored `content.md` (6,398 chars) and now cites the resolvable Source:

> "Receipts: exec_event `89113f75`; proposal `fc7ee88e`; full breakdown in `docs/evaluations/2026-06-22-full-autonomy-resolution-VALIDATION.md` **(source: Kvkthecreator/yarnnnn repo, observed 2026-06-22T07:05:56Z)**."

The citation now carries the repo + path + `observed_at` from the observation contract — a resolvable Source, not a bare name and not the internal `_repo_signal.yaml` path. (Remaining bare "ADR-306" mentions are content cross-references — the essay *discussing* ADR-306 as a concept — not sourced claims; correctly not every mention is a citation.)

## 5. What this is NOT

- **Not** a new taxonomy — reuses `source_ref` (ADR-335) + `authored_by` (ADR-209) + the attestation enum (ADR-330). It names the binding rule between them.
- **Not** a frame section — one clause appended to the existing citation clause in the action-grammar (DP22 anti-rebloat respected).
- **Not** a claim that the agent was dishonest — verification proved every prior citation traced to perceived substrate. The fix is *form* (make citations resolvable), not *integrity* (which held).
- **Not** "cite everything" — a citation binds a *sourced claim* to its Source; content cross-references (discussing a concept) are not citations.

## 6. Files

- `docs/architecture/FOUNDATIONS.md` — Derived Principle 31 + v9.10 version-history line (D1/D2).
- `docs/architecture/GLOSSARY.md` — Source, Citation, Attribution entries (bridging Observation ↔ authored_by).
- `docs/architecture/agent-composition.md` — §3.2.1 partition row (D3).
- `api/agents/reviewer_agent.py` — the action-grammar citation clause (D3, frame-resident).
- `docs/programs/alpha-author/reference-workspace/operation/specs/piece-composition.md` — sourcing rule "trace to Source", not "trace to a workspace file" (D2/D4).
- `api/prompts/CHANGELOG.md` — `[2026.06.22.4]`.
- Evaluation: `docs/evaluations/2026-06-22-author-the-agent-authors-VALIDATION.md` (the verification that triggered this).

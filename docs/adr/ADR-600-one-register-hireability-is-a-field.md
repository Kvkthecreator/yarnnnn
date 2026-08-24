# ADR-600: One register — an agent is an agent, and hireability is a field on it

**Status**: Ratified + Implemented 2026-08-24 (operator ruling after a first-principles audit of the ADR-596→599 arc: *"do we need a distinction from kernel agents to app agents? … in essence all agents are agents."*)

**Supersedes**: ADR-598 D1 (three registers) · ADR-598 D2 (roster serves colleagues only, as a *register* rule) · ADR-599 D3's register placement. The ADR-460 D3.a cliff, ADR-597's read-time derivation, and ADR-599's *deletion* of the colleague roster all stand unchanged.

## Context

ADR-598 split `agents_registry` into three top-level dicts — `KERNEL_AGENTS` (base operations), `KERNEL_POSTURES` (colleague stances), `APP_RESIDENTS` (desk voices) — to stop an app's furniture appearing under "Who you can hire". The separation was the right *observation*; the register split was the wrong *mechanism*.

ADR-599 then emptied the first two registers and, in D3, deleted `based_on` from resident rows to make them self-contained. That completed a convergence nobody named at the time:

| | keys |
|---|---|
| `AGENT_ROW_KEYS` | slug · name · blurb · icon · model · token_profile · posture |
| `RESIDENT_ROW_KEYS` | **identical** |
| `POSTURE_ROW_KEYS` | identical + `based_on` (register now empty) |

Under ADR-596 D1 — *an agent is identity ⊕ character ⊕ engine; authority, clock and judgment live on grants, declarations and gates, never on the being* — two rows with identical shape and identical resolution are **the same type**. Nothing in a row records which register it came from.

### What the split actually gated — measured, not argued

`_kernel_character()` **unions all three registers**. Every consumer that matters resolves through it: `resolve_agent` · `get_agent` · `model_for_agent` · `build_agent_posture`. So the split was invisible to lane creation, turn routing, posture composition, engine resolution and attribution rendering.

It was visible in exactly one place: `list_agents()` reads `KERNEL_AGENTS` only, and returns `[]`.

**The split was never a type distinction. It was a visibility flag modelled as three namespaces.**

### The cost, paid in full within ~14 days

Modelling a *property of a being* as *the identity of its container* means a being changes identity when the property changes. Three live defects, all executed against the running code, all traceable to `designer` moving registers in ADR-599 D4:

1. **Two AI planners dead, silently.** `services/apps/images/decompose.py` and `services/studio_arrangement_plan.py` both did `KERNEL_AGENTS["designer"]["model"]` → `KeyError` on an empty dict → swallowed by each site's broad `except Exception` → permanent fallback to the heuristic/mechanical path. Both files carry a comment stating the *import* is outside the `try` **deliberately**, so a bad symbol cannot masquerade as "the router is off" — but the *subscript* was inside it. The exact failure the comment was written to prevent is the failure that shipped. IMAGES layer planning and Slides arrangement planning ran degraded in production from ADR-599 until this ADR.

2. **The ADR-559 pricing/currency ratchet protected zero rows.** It hand-spells `KERNEL_AGENTS.values()` and `KERNEL_POSTURES.values()`; both are empty. Measured: **0 rows iterated**. The three engines that actually run carried no currency check and no `has_billing_rate` check. The gate was green because it was *vacuous* — the failure mode CLAUDE.md names as green-gates-test-the-room-not-the-doorway.

3. **The cast door contradicted the roster.** `POST /lanes/{id}/participants` gates on `resolve_agent`, which unions. Measured: `designer`/`editor`/`keeper` **accepted** into any chat lane's cast; `sonnet`/`critic` refused. Residents were hireable through the API while ADR-598's central claim was that they are not — the refusal existed only in the surface's silence. This is the ADR-373 D6 incorrect-success class.

Plus five stale doc claims of the form *"register X holds Y"* across four files. A being that can move between registers makes every such reference a standing liability.

## D1 — One register

`agents_registry` holds ONE dict, `AGENTS`, keyed by slug. `KERNEL_AGENTS`, `KERNEL_POSTURES`, `APP_RESIDENTS`, `AGENT_ROW_KEYS`, `POSTURE_ROW_KEYS`, `RESIDENT_ROW_KEYS` and `_kernel_character` are **DELETED** — not aliased, not re-exported. A shim here would preserve exactly the property that caused the defects: a second name for the place a being lives.

`AGENT_ROW_KEYS` is replaced by a single `AGENT_ROW_KEYS` whitelist over the one shape. `based_on` is gone with the postures register (ADR-599 D3 already deleted it from the rows that survive).

Resolution is unchanged in behaviour: `resolve_agent(slug)` → `AGENTS.get(slug)`. Every live lane, cast row and attribution resolves exactly as before. **Slugs remain data-compat** (`designer` rides ~65 live cast rows) — this ADR moves no data and renames nothing.

## D2 — Hireability is a field: `offered`

Each row carries `offered: bool` — *is this being on the roster a member picks from?*

- `offered: False` — the being's home is a desk; it is met where it works, never invited. Today: `designer` (Slides) · `editor` (Text) · `keeper` (Strings).
- `offered: True` — a colleague a member can invite into a conversation. Today: **nobody**, per ADR-599 D1, which this ADR does not reopen.

`list_agents()` returns `[r for r in AGENTS.values() if r["offered"]]` — still `[]`, now as an **observable fact about the beings** rather than a property of a deleted namespace.

**`offered` is reach, not authority.** It answers *who may be invited*, never *what they may do*. The ADR-460 D3.a cliff is untouched and its gate unweakened: no authority-shaped key, no `tools`, nothing outside the whitelist. A future session adding `authority` beside `offered` violates ADR-460 exactly as before.

## D3 — The cast door asks the field, not the namespace

`POST /lanes/{id}/participants` gates on `offered`, not on bare resolvability. A resident is refused with a message that says *why* — it has a desk — rather than the generic "no agent called…". The API and the surface now answer the same question; defect 3 becomes structurally unreachable.

Historical cast rows pinning a non-offered slug keep resolving and rendering: this gates the **invite**, never the read.

## D4 — Machinery resolves a being, never a container

`decompose.py` and `studio_arrangement_plan.py` resolve their engine through `resolve_agent("designer")["model"]`, inside the same deliberate outside-the-`try` import discipline their comments already describe. A missing being is a **bug that raises**, not a fallback condition — the fallback covers a failing *call*, never a failing *lookup*.

Direct subscripting of the registry from a call site is banned and gate-asserted: the pattern that broke is the pattern the gate now refuses.

## D5 — The gate iterates the register, not a hand-spelled list

`test_adr559`'s currency + pricing ratchet iterates `AGENTS.values()`. It cannot go vacuous again: a register with rows in it is the thing being checked, and a new being is covered the moment it is added. Falsified both ways (an unpriced engine and a superseded id each trip it).

## D6 — The surface shows beings, sectioned by where they live

`/agents` currently tells a member they have nobody. That is **false**: Designer answered them in Slides an hour ago. The honest surface shows every being, sectioned:

- **At a desk** — non-offered beings, with the app each speaks for. Met, not hired.
- **Available to work with** — offered beings. Empty today, honestly.

Non-empty and true, replacing empty and true-by-omission. The empty state that survives is the *offered* section's, which is the one ADR-599 actually ruled on.

## Consequences

- Two production planners repaired; IMAGES and Slides plan with their resident again.
- The ADR-559 ratchet covers every live engine for the first time since ADR-599.
- API and surface agree on who may be invited.
- Five stale register references deleted with the registers that made them wrong.
- The ADR-596 axiom now holds *structurally*: there is one kind of being, and every question about a being is a field on it. The next such question (can this being hold a grant? run on a clock?) has an obvious home — and ADR-596's answer stays "not on the row".
- Gates: `test_agent_registry.py` re-anchored to the one register + the field; `test_adr559` de-vacuumed; `test_adr562`/`test_adr569`/`test_adr592`/`test_adr597` re-pointed. Each new check falsified before trusting it.

# FINDING — Freddie's wake envelope carries one slice of the perception field, not the field; the steward frame names duties the envelope gives no substrate to act on

**Date**: 2026-06-30. **Hat**: B (evaluation), with a Hat-A architectural recommendation that ESCALATES to a first-principles re-scope (see the companion analysis: `docs/analysis/perception-and-the-principal-commons-first-principles-2026-06-30.md`). **Surfaced from**: the operator's read of the attribution-fact confirmation FAIL ([2026-06-30-attribution-fact-confirmation-FINDING.md](2026-06-30-attribution-fact-confirmation-FINDING.md)) — "does the envelope accommodate the FULL perception scope (Connections, Sources, External Agents), or only the one attribution slice we just hardened?"

> **Verdict**: **CONFIRMED gap, narrower than "pre-Freddie posture" but real.** The persona-frame WAS correctly re-carved to the steward self-model (ADR-383) — it explicitly names "keeping the files, context, **attributions, intake, and connections** coherent" as the system agent's job. But the **wake envelope** surfaces substrate for only ONE of those duties (attribution, via the ADR-387 fact). Connections-health, Sources-health, and the principal roster (who is authorized to write into the commons) are **absent from the envelope** — Freddie would have to discover each unprompted. The attribution-fact arc just proved (across three wakes) that **a signal Freddie must fetch unprompted is a signal it does not act on**. So the same structural cause behind the attribution catch-miss applies to the rest of the perception field. The frame names the duties; the envelope under-equips them.

---

## What was checked (receipts)

### The frame IS Freddie-native (not pre-Freddie) — ADR-383 landed

`api/agents/freddie_agent.py::_compute_minimal_frame` (@262) leads with the steward self-model and names the perception duties explicitly:

> *"When it declares **stewardship of this workspace's substrate** — keeping the files, context, attributions, intake, and **connections** coherent, well-placed, and legible — you are the **system agent**…"* (@318-320)
> *"for the system agent it is stewardship (place the intake, fix the attribution, reconcile the commons)"* (@385-386)

So the *posture* is correct. The hypothesis "the setup still assumes the prior capital-judge Reviewer" is **half-true**: the FRAME was migrated (ADR-383, the 2026-05-29 collapse), but the ENVELOPE was not re-designed around the steward's job — it accreted.

### The envelope carries one perception slice, not the field

`api/services/freddie_envelope.py::load_freddie_governance_envelope` (@235-391) loads, in full:
- **Governance/persona** (universal): IDENTITY, principles, PRECEDENT, MANDATE, AUTONOMY, preferences, budget, expected-output, occupant, standing-intent
- **Program substrate** (bundle-declared `substrate_abi.reviewer_wake_envelope`): ground-truth, risk, operator-profile, signals
- **Derived facts**: specs-inventory (@367), reflection-gap-fact (@379, ADR-364), **attribution-fact (@386, ADR-387)**
- **Operating context** (@354): now / tz / market-state / tenure

A grep of the entire assembler + the `FreddieContext` contract (`api/agents/occupant_contract.py:100-226`) for `platform_connections | sources | watches | principal_grants | foreign | external.agent` returns **zero hits**. Confirmed absent:

| Perception channel (the Channels surface) | Substrate exists? | In the wake envelope? | Freddie can pull on demand? |
|---|---|---|---|
| **Sources** (web/RSS watches) | ✅ `inbound/web/` + distilled signal, `authored_by=system:track-web-sources` (ADR-335/336, fully wired + tested) | ❌ **No** | ⚠️ Indirectly — `ReadFile` the signal file IF it knows the path; no inventory |
| **Connections** (Slack/Notion/broker) | ⚠️ Split: OAuth row is runtime; **mirrored data** lands via `SyncPlatformState` `authored_by=system:sync-platform-state` (ADR-264, live in alpha-trader `_recurrences.yaml:43/59/70`) | ❌ **No** (neither connection health nor "this is mirrored-external" framing) | ✅ `ListIntegrations` (@registry.py:222) + `GetSystemState` (@system_state.py:145) — but unprompted |
| **External Agents** (MCP LLM principals) | ✅ `inbound/mcp/{client}/`, `authored_by=yarnnn:mcp:{client}`; **grant-backed** in `principal_grants` (ADR-373, table+gate+endpoint live) | ⚠️ **Partial** — appears ONLY as `authored_by` strings inside the attribution-fact; the **roster** (who/role/scopes) is NOT loaded | ❌ **No** — `principal_grants` is a relational table, not a substrate file; no primitive reads the roster |

### Freddie CAN discover some of it — but discovery-on-demand ≠ perception

`FREDDIE_PRIMITIVES` (`registry.py:444`) includes the full read family + `ListIntegrations` + `GetSystemState` + `QueryKnowledge` + `SearchFiles`. So Freddie is *not blind* — it could `ListIntegrations`, `SearchFiles inbound/web/`, etc. **But the attribution-fact arc is the controlled experiment that settles whether that's enough**: in all three wakes Freddie had `ListRevisions` available and the duty named in the frame, yet only *investigated attribution at all* once the kernel **pre-loaded** the attribution fact — and even then under-used it. The lesson generalizes: **the steward acts on what the envelope makes salient, not on what it could in principle go fetch.** Discovery-on-demand is the pre-ADR-387 state for every perception channel except attribution.

## The connection to the catch-miss (why this is one problem, not two)

The attribution-fact confirmation FAIL was diagnosed as a *rule-trigger* gap ("the model doesn't fire AI-voiced + operator-stamp = violation"). That diagnosis stands — but this finding reveals it sits inside a larger envelope-completeness gap. The most pointed instance: the mis-attribution catch is fundamentally a **principal** question ("which principal really wrote this, and is that consistent with who's authorized to?"). Freddie has **no principal roster** in the envelope — it sees `authored_by: operator` as a bare string with nothing to check it against. A steward that knew the workspace's principals (owner = human X; foreign-llm = claude-desktop; no other human writers) has a frame to reason *"AI-voiced content stamped `operator` — but the only `operator` principal is human X, and this isn't their voice"*. Without the roster, the attribution fact is a stamp with no referent. **The rule-trigger sharpening (the FINDING's named next lever) and the principal-roster envelope addition are complementary, not alternatives** — and the latter is arguably the more first-principles fix.

## What this opens — the recommendation is to RE-SCOPE, not patch

The honest reading is that the operator is right: **this is the moment for a first-principles pass on the wake envelope + the perception primitives**, not another one-slice bolt-on (reflection-gap, then attribution-fact, then connections-fact, then sources-fact, then principal-fact… is the accretion that produced the gap). The companion analysis works the conceptual framing — the load-bearing distinction it lands is **principal vs peripheral** (an MCP LLM is a principal with standing intent + a grant; a web feed / broker API is a peripheral / driver-class transport) — and proposes what a steward-shaped envelope should carry. Read it before building anything.

**Guardrail (carried from the attribution arc):** probe before canon. The analysis is a *direction*, not a ratified plan. The specific cheap probe to validate the highest-leverage slice: add a **principal-roster fact** to the envelope (the `principal_grants` roster + the "who is authorized to write where" the gate already computes) and re-fire the bare-steward wake — does a steward that can see its principals now catch the mis-attribution? One ~$0.10 wake tests the most first-principles version of the fix before any envelope re-architecture.

## What's NOT claimed here

- Not claimed: the primitives are wrong. The read family looks sufficient for a filesystem-native steward (the operator's instinct — "filesystem-native should be inherently meta-aware via substrate attribution" — is largely borne out: ReadFile/ListFiles/ListRevisions over an attributed FS IS meta-awareness *on demand*). The gap is **envelope pre-load (salience), not primitive capability (reach)** — the same presence-vs-salience distinction the attribution arc earned, now applied to the whole perception field. An audit of the primitive *set* is worth doing but is secondary to the envelope re-scope.
- Not claimed: Connections must become a principal. The analysis argues the opposite (Connections/Sources are peripherals, correctly attributed `system:*`). The framing question is whether the steward should *perceive peripheral health* (probably yes, as a fact) distinctly from *perceiving the principal commons* (definitely yes, as a roster).
- Not fixed here: anything. This is a finding + a pointer to the analysis. No code, no canon moved.

## Reproduce / verify the gap

```bash
# the envelope's full load surface (no connections/sources/principals):
sed -n '235,391p' api/services/freddie_envelope.py
# the contract fields (no principal roster):
sed -n '100,226p' api/agents/occupant_contract.py
# the frame DOES name the duties (ADR-383, the asymmetry):
sed -n '262,395p' api/agents/freddie_agent.py
# the substrate that EXISTS but isn't pre-loaded:
#   Sources:        api/services/primitives/track_web_sources.py  (inbound/web/, system:track-web-sources)
#   Connections:    api/services/primitives/sync_platform_state.py (ADR-264, system:sync-platform-state)
#   External Agents: supabase/migrations/189_adr373_multi_principal_rekey.sql (principal_grants)
#                    api/routes/workspace.py:782  (GET /api/workspace/members — the roster endpoint)
```

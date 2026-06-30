# Perception and the Principal Commons — a first-principles pass on Freddie's wake envelope

**Date**: 2026-06-30. **Status**: analysis / direction — NOT ratified canon. Doc-first; probe before building.
**Companion finding**: [2026-06-30-perception-envelope-completeness-FINDING.md](../evaluations/2026-06-30-perception-envelope-completeness-FINDING.md) (the receipted gap).
**Origin**: the operator's read of the attribution-fact arc — "the prompt envelope + primitives may need revisiting from first principles, because the current setup still assumes the pre-Freddie reviewer posture; and I'm not sure how Sources/Connections are fundamentally different from an MCP-AI writing documents into the substrate — if that nuance needs its own scoping, now is the time."

This doc answers that. It is deliberately conceptual: it draws the line first, then says what follows for the envelope, the primitives, and the surface. It does **not** prescribe an implementation; it scopes the thing to be ratified.

---

## 1. The question, stated precisely

Freddie (the system agent / Rung-1 substrate steward, ADR-381/383) is woken to *tend the commons*: place intake, fix attribution, reconcile the workspace, keep connections coherent. Its persona-frame names all of that. But its **wake envelope** carries only governance + program substrate + two derived facts (reflection-gap, attribution). The three things the operator's Channels surface shows — **Connections, Sources, External Agents** — are essentially invisible to the steward at wake time (see the finding for receipts).

The operator's two sub-questions:
1. Is the envelope (and the primitive set) still shaped for the **prior reviewer** (the capital-judge), rather than the **steward**?
2. Are Connections and Sources **fundamentally different** from an MCP-AI writing a document — or are they the same kind of thing, just different transports?

Question 2 is the load-bearing one. Its answer determines everything about question 1.

---

## 2. The answer to Q2: they converge at the ledger floor, they diverge at the principal layer

Trace all three context-in transports to the substrate (receipts in the finding):

| Transport | Raw lands at | Attributed as | Has standing intent? | Authorized by a grant? |
|---|---|---|---|---|
| **MCP LLM** (Claude Desktop, ChatGPT) | `inbound/mcp/{client}/` | `yarnnn:mcp:{client}` | **Yes** — it reasons | **Yes** — `principal_grants` row |
| **Web/RSS source** (ADR-335/336) | `inbound/web/{source}/` | `system:track-web-sources` | No — it's a feed | No — it's declared, not granted |
| **Platform connection** (Slack/broker; ADR-264 `SyncPlatformState`) | `operation/...` (mirrored state) | `system:sync-platform-state` | No — it's an API | No — it's capability-gated, not granted |

**At the ledger floor, all three are the same kind of thing** — context-in transports that (per ADR-376, the ledger-intake axiom) *retain + attribute + cite*: raw observation in, derived citing act out, raw never rewritten. This unification already exists in canon. The operator's instinct — "I'm not sure Sources/Connections are different from an MCP-AI writing a document" — is **correct at this layer**. They aren't. They all write attributed substrate.

**At the principal layer, exactly one of them is a principal.** This is the distinction the system has half-drawn but never named as one model:

> **A PRINCIPAL is an authoring identity with standing intent and a grant.** It reasons; it could be right, wrong, careless, or adversarial in a way that requires *judgment* about the writer, not just the write. It attributes *as itself* (`yarnnn:mcp:claude-desktop`), and it holds a `principal_grants` row that authorizes it. Humans, their agents, other humans, foreign LLMs, A2A callers — the open set of ADR-373.
>
> **A PERIPHERAL is a driver-class transport with no intent.** A web feed, a broker API, an RSS endpoint. It has no judgment to be questioned — there is no "who" behind the bytes, only a "what." It attributes as the *mechanism* that operated it (`system:track-web-sources`, `system:sync-platform-state`), because the system, not the source, is the author of record. ADR-335 already calls these "peripherals … driver-class, transport-blind judgment" — it just never contrasted them with principals as a single taxonomy.

This is the framing the operator asked whether we need. **We do, and this is it.** The Channels surface visually groups three panes as if they were peers; architecturally they are **two principals-vs-peripherals classes wearing one UI**:

```
Channels surface (today)        →    The actual taxonomy
─────────────────────────             ─────────────────────────
  Connections   ┐                       PERIPHERALS (mechanisms, system:-attributed)
  Sources       ┘ "peripherals"   →       Connections (mirrored external state)
                                          Sources     (declared watches)
  External Agents "principals"    →     PRINCIPALS (intent-bearing, grant-backed, self-attributed)
                                          External Agents (MCP LLMs, A2A, …)
                                          + the owner, + members, + own-agents (not yet shown here)
```

### Why the distinction is load-bearing (not academic)

The attribution catch-miss is the proof. The mis-attribution Freddie failed to catch is a **principal question**: AI-voiced content stamped `authored_by=operator`. To catch it, the steward needs to reason *about a writer* — "the `operator` principal is human X; this isn't X's voice; therefore the stamp is wrong." Freddie can't do that today because it has **no principal roster** — `authored_by: operator` is a bare string with no referent. You cannot judge an attribution against the set of who's-authorized if you can't see that set.

Peripherals never raise this question. A `system:track-web-sources` stamp is true by construction — the mechanism did write it. There's no lie a peripheral can tell about *who it is*, because it isn't a who. The only judgment a peripheral invites is about its *health* (is the feed live? is the connection expired? is the data stale?), not its *honesty*.

**So the steward's two perception duties are categorically different:**
- Over **principals**: judge the *honesty and coherence* of the commons — who wrote what, does the attribution match the content, is a writer drifting. (Needs a roster.)
- Over **peripherals**: judge the *health and freshness* of the inputs — is what feeds the operation live and current. (Needs a status surface.)

The current envelope serves neither cleanly. The attribution-fact is a half-step toward the first (it shows authored_by strings but no roster to check them against). Nothing serves the second.

---

## 3. The answer to Q1: the envelope is post-Freddie in FRAME, pre-Freddie in SHAPE

The persona-frame was re-carved correctly (ADR-383 — it leads with the steward, names the perception duties). But the **envelope was never redesigned around the steward's job.** It was built for the capital-judge Reviewer — governance ceilings + program ground-truth + a proposal to judge — and perception has been **bolted on one slice at a time**:

- ADR-364 → reflection-gap-fact (the outcome side of capital judgment)
- ADR-387 → attribution-fact (one slice of commons-honesty)
- next, by the accretion logic, would be: connections-fact, sources-fact, principal-fact, …

That accretion IS the gap. Each bolt-on is locally reasonable and globally incoherent — the envelope has no model of "the perception field" as a whole, so it grows one fact per eval-failure. The first-principles move is to **define what a steward-shaped envelope carries**, derived from the steward's actual duties, rather than continuing to append facts.

A steward's envelope should carry, by derivation from the duties:

1. **The governance it runs under** — already present (MANDATE, principles, AUTONOMY, budget, preferences). Keep.
2. **The principal commons** — the roster: who has a grant, their role, their write-regions, and recent per-principal authorship. *This is the missing first-class structure.* The attribution-fact becomes a *projection* of this (recent writes by principal), not a standalone string.
3. **The peripheral field** — connection health + source health as a *status fact* (live/expired/stale per transport), so the `connection-hygiene` and source-freshness duties have substrate. Distinct from the principal commons by construction.
4. **The substrate state it tends** — intake awaiting placement, recent revisions, specs inventory. Partially present (attribution-fact, specs-inventory); should be unified as "what needs tending."
5. **The operating context** — now/tz/tenure. Present. Keep.

The reframe: **the envelope is the steward's perception of the workspace as a commons-with-a-perimeter**, not a governance-packet-plus-a-proposal. The capital-judge envelope is the *special case* that applies when a program has installed an operation (then ground-truth/risk/signals/proposal join) — exactly the inversion ADR-383's two-order model implies (steward is the base case; judgment is program-activated).

---

## 4. What follows for the primitives (the audit the operator asked for)

The operator's hypothesis: "most primitives will remain similar but need auditing; filesystem-native should be inherently meta-aware via substrate attribution (knowing what's where by default)."

**Largely borne out.** The read family over an attributed filesystem (`ReadFile/ListFiles/SearchFiles/ListRevisions/ReadRevision/DiffRevisions`) IS meta-awareness — *on demand*. A steward can walk the substrate and see who-wrote-what because ADR-209 made attribution intrinsic to every revision. The primitive *reach* is sufficient; what the attribution arc proved is that **reach ≠ salience** — Freddie acts on what the envelope pre-loads, not on what it could fetch.

So the primitive audit's finding is likely: **the gap is not missing primitives, it's missing pre-load.** Two qualifications worth checking in a real audit:

- **The principal roster has no read primitive.** `principal_grants` is a relational table, not a substrate file — Freddie cannot `ReadFile` it. Either (a) the roster is pre-loaded into the envelope (preferred — it's perception, it should be a fact), or (b) a `ListPrincipals`-style introspection primitive is added (like `ListIntegrations` / `GetSystemState`, which are the *peripheral* analogues). Given the salience lesson, (a) is the first-principles answer; (b) is at best a complement.
- **`ListIntegrations` + `GetSystemState` are peripheral-introspection primitives that exist but aren't pre-loaded.** They're the right *reach* for the peripheral field; they need to become an envelope *fact* for salience.

The audit should also confirm a *removal*: the capital-judge envelope assumes a proposal-to-judge and program ground-truth as near-universal. On a bare steward workspace those are correctly empty — but the envelope/frame should make the steward base-case the default shape and the capital-judge additions the program-activated overlay, not the reverse. (This is a coherence cleanup, not a behavior change — the values are already empty on bare workspaces; the question is whether the *shape* leads steward or leads judge.)

---

## 5. What follows for the surface

The Channels surface (ADR-385) groups Connections · Sources · External Agents. The taxonomy above suggests the *operator-facing* grouping is fine (the operator thinks in transports), but the *names* could honor the line: External Agents is the principal pane; Connections + Sources are the peripheral panes. The deeper point is internal, not cosmetic — the **steward's** view (the envelope) should reflect principal-vs-peripheral even if the **operator's** view (the surface) keeps the transport grouping. One substrate, two views (DP29) already licenses this: the operator sees transports; the steward sees principals-and-peripherals.

---

## 6. Relationship to the re-founding keystone (don't collide)

The re-founding direction (`docs/analysis/the-re-founding-meaning-folders-and-permission-as-metadata-2026-06-29.md`, doc-only, not ratified) proposes that the filesystem is organized by **meaning**, with permission + provenance as **metadata** on files/revisions. That arc *strengthens* this one: if provenance (which principal wrote each revision) is first-class metadata, the **principal commons** becomes a natural projection of revision metadata — the roster + per-principal authorship the envelope needs is exactly a `GROUP BY principal` over the ledger. The two are complementary: the re-founding makes principal-provenance a first-class revision property; this analysis says the steward's envelope must *perceive* it. **Do not build the principal-roster fact in a way that hard-codes `principal_grants` as a separate source if the re-founding is going to fold provenance into revision metadata** — design the envelope fact to read "the principals of this commons + their recent authorship," sourced from wherever the re-founding lands provenance. Coordinate; don't fork.

The inbound/ raw-lane is also under the re-founding's reconsideration (provenance → revision metadata). Since Sources (`inbound/web/`) and MCP (`inbound/mcp/`) both use it, the peripheral-vs-principal line should be drawn at the *attribution/grant* layer, not at the *path* layer — which the re-founding's "meaning-not-namespace" thesis already wants.

---

## 7. Recommended sequence (probe-first, no canon moved yet)

1. **Ratify the taxonomy** (cheap, doc-only): principal vs peripheral as a named distinction. This is the conceptual scoping the operator asked whether we need. It can land as a short ADR or a FOUNDATIONS amendment to Axiom 1 §8 (the perception field already half-says it). Everything below depends on it.
2. **Probe the highest-leverage slice** (~$0.10, before any envelope work): add a **principal-roster fact** to the bare-steward envelope (roster + recent per-principal authorship) and re-fire the attribution wake. *Does a steward that can see its principals catch the mis-attribution?* This tests the most first-principles version of the catch-fix AND validates the envelope direction in one wake. If it catches → the principal commons is the fix and the rule-trigger sharpening may be unnecessary. If it still misses → the rule-trigger limb (the prior FINDING's named lever) is the next probe, now with the roster ruled in or out.
3. **Only then** design the steward-shaped envelope (§3) as a coherent whole — principal commons + peripheral field + substrate-to-tend + governance — rather than appending a fifth fact. Coordinate with the re-founding (§6).
4. **Audit the primitive set** (§4) as a parallel, lower-priority pass — confirm reach-is-sufficient, add a principal-roster read path only if §2 shows pre-load isn't enough.

The discipline that earned this whole arc: **probe before canon; the cause is usually one layer simpler than the grand reframe.** This analysis is the grand reframe's *scope*; step 2 is the probe that tells us how much of it the catch actually needs. Do not skip step 2 to build step 3.

---

## Appendix — receipts (for the curious; full set in the finding)

- Frame names the duties: `api/agents/freddie_agent.py:318-320, 385-386`
- Envelope loads (no connections/sources/principals): `api/services/freddie_envelope.py:235-391`
- Contract fields (no principal roster): `api/agents/occupant_contract.py:100-226`
- Sources → substrate: `api/services/primitives/track_web_sources.py` (`inbound/web/`, `system:track-web-sources`); ADR-335/336
- Connections → substrate: `api/services/primitives/sync_platform_state.py` (ADR-264, `system:sync-platform-state`); live in `docs/programs/alpha-trader/reference-workspace/_recurrences.yaml:43,59,70`
- Connections OAuth row is runtime: `platform_connections` table; `ListIntegrations` @ `api/services/primitives/registry.py:222`
- Principals → grant-backed: `supabase/migrations/189_adr373_multi_principal_rekey.sql:51-67`; roster endpoint `api/routes/workspace.py:782-860`
- MCP principal attribution: `api/mcp_server/auth.py:119-138` (`yarnnn:mcp:{client}`)
- ADR-376 ledger-intake axiom (the floor unification): `docs/adr/ADR-376-*.md`
- Re-founding (coordinate): `docs/analysis/the-re-founding-meaning-folders-and-permission-as-metadata-2026-06-29.md`

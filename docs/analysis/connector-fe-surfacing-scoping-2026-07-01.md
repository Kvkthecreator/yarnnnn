# Connector FE surfacing — a scoping pass (universal, not per-platform)

> **Date**: 2026-07-01. **Status**: scoping / direction — NO code. Produced as a planning turn (operator: "just scope now, build nothing yet"). The build is directed later, per this doc's sequencing.
> **Companion**: [ADR-392](../adr/ADR-392-the-connector-lane.md) (the connector lane) + [connectors-at-large-first-principles](connectors-at-large-first-principles-2026-07-01.md) (the backend derivation). This doc is the FE half.
> **Origin**: after the ADR-392 backend + the thin selection panel shipped, the FE surfacing was scoped as unfinished. The operator's steer: *"some connectors seem to warrant their own dedicated [view], but that's not future-proof or scalable — maybe similar to how MCPs display tools, a universal approach to the front-end handling."* This doc answers that: **the surface is connector-agnostic, metadata-driven; the Nth connector is a registry entry, not a code change.**

---

## 1. The load-bearing decision: universal, not per-platform

The operator's instinct is correct and is already **canon**: the kernel never hardcodes a program/platform noun (ADR-222), and transports are peripherals — *driver-class, known by contract, never by device* (ADR-335, DP27). A per-platform Slack view / Notion view / Gmail view is the exact anti-pattern that framing forbids.

**The codebase already contains the pattern to copy — twice:**

1. **`WorkspaceMembersCard`** (`web/components/workspace-concepts/WorkspaceMembersCard.tsx`) — ONE component over ONE substrate (`principal_grants`), rendering *filtered views* by `roleFilter`, driven by per-role **metadata** (`{label, icon, tone}` per role). The "AI Connections" pane is just this component with `roleFilter=[foreign-llm, a2a, platform]`. *One substrate, N views, zero per-principal code.* This is the operator's "how MCPs display" precedent, already built.

2. **ADR-379 host profiles** (`api/mcp_server/presentation/hosts.py`) — the interop-reach registry whose thesis is stated verbatim: **"The Nth host is a registry entry, not a code change."** Host-specific behavior (does it render widgets? text-safe default?) is *data in a registry*, resolved by a single resolver, never a per-host branch.

**The connector FE must adopt the same shape.** Today it does the opposite.

### The anti-pattern we shipped (and must retire)

`ConnectedIntegrationsSection.tsx` today is **7 hardcoded per-platform card blocks** (`slackIntegration ? … : …`, `notionIntegration ? …`, `githubIntegration ? …`, commerce, trading, + the `Manage channels`/`Manage pages`/`Manage repos` literals). The ADR-392 D7b work *added to* this hardcoding (three near-identical Manage buttons + three `ConnectorSelectionPanel` mounts differing only by a `resourceNoun` string). Adding an 8th connector = copy-paste a ~60-line JSX block. **That is precisely the "not scalable, not future-proof" shape the operator flagged.** The FE surfacing work is, first, a *de-duplication into the universal pattern* — and only then the new-legibility additions.

---

## 2. The connector metadata registry (the seam that makes it universal)

The universal card needs per-connector facts that today live scattered as JSX literals + hardcoded booleans. Lift them into ONE registry — the connector analog of `hosts.py` + the `ROLE_META` map inside `WorkspaceMembersCard`:

```
CONNECTOR_REGISTRY: Record<provider, {
  displayName:   string      // "Slack", "Notion", "GitHub", "Gmail"
  icon:          IconRef      // the brand glyph (today: inline SVG per card)
  tagline:       string      // "Team collaboration and context"
  resourceNoun:  string      // "channels" | "pages" | "repos" | "labels"
  authKind:      'oauth' | 'apikey'   // gates the connect UX (commerce/trading = apikey)
  capabilities:  string[]    // ['read_slack','write_slack'] — for the write-ready + feeds display
  driver:        'first-party' | 'composio'   // ADR-353 — informational, not branching
}>
```

**Where it lives**: FE-side (`web/lib/connectors/registry.ts`) seeded from — or ideally *served by* — the backend so it stays singular with `orchestration.py::CAPABILITIES` + `oauth.py::OAUTH_CONFIGS` + `WRITE_SCOPE_MARKERS` (all already per-provider registries). A `GET /api/connectors/catalog` that projects those backend registries into the FE shape is the DP29 "one substrate, one view" move — the FE never re-declares what the backend already knows. (Open: build the endpoint, or hand-seed the FE registry first and converge later. Recommend endpoint — it kills the drift class where FE lists a connector the backend can't gate.)

**The payoff**: every connector surface below becomes `CONNECTOR_REGISTRY.map(...)`. Adding Gmail = one registry entry + (if new) one backend capability/OAuth entry. Zero new JSX. This is the whole thesis.

---

## 3. The surface inventory — what exists, what's missing, mirror-vs-compose

The four-phase lane (connect · select · capture · derive) mapped to surfaces. The ADR-340 rule — **mirror once, compose few** — decides each: a *mirror* is one-surface-to-one-substrate (the escape hatch); a *composition* is one-surface-to-one-operator-act.

| Phase | Operator act | Status | Surface home | Mirror or compose |
|---|---|---|---|---|
| **1 Connect** | connect/disconnect | ✅ shipped (but hardcoded per-platform) | Channels → Connections | compose (the connect act) — **de-dup into registry** |
| **1 Connect** | see connection health | ✅ exists | peripheral field (steward) + card status | mirror |
| **2 Select** | pick channels/pages | ✅ shipped (thin) | Manage subsurface | compose (the tune act) — **de-dup + enrich** |
| **2 Select** | see selection *consequence* | ❌ missing | Manage subsurface | compose — declared × observed (the `SourcesCard` shape) |
| **3 Capture** | browse captured raw | ⚠️ generic-only | Files → **Intake** root (`inbound/`, ADR-388) | **mirror** — already exists; do NOT compose a per-connector raw browser |
| **3 Capture** | see the intake event stream | ✅ exists | Activity → **In** pane (narrative-filtered) | mirror |
| **4 Derive** | see derived understanding | ❌ missing + **blocked** (derive step unbuilt) | Files → operation/ (mirror) + ? | mirror + maybe a compose |
| **4 Derive** | walk the `trace` chain (raw→derived) | ❌ missing + **blocked** | ? (the differentiator surface) | compose — the ADR-368 `trace` verb, connector-scoped |
| **Retention (D8)** | set the 7/14/30 window | ❌ no UI | Connections pane or Settings | compose (one control) |
| **Retention (D8)** | see prune legibility | ❌ no UI | Connections pane | mirror (a stat line) |

**The mirror-vs-compose calls (resolving the operator's tension directly):**

- **Captured raw = MIRROR, never compose.** `inbound/` is already a first-class Files root ("Intake", ADR-388 `WORKSPACE_ROOTS`, `arrow-down-to-line`). Building a per-connector raw browser would *duplicate the mirror* — the exact ADR-340 violation. The operator browses raw in Files → Intake; the connector surface *links* there, never re-renders it.
- **Selection consequence = COMPOSE (one act).** The Manage subsurface is the operator act "tune what this connector perceives." It should show declared × observed (last-captured, freshness, item count) — the `SourcesCard` shape already proven for web watches. This is a *composition*, and it's the highest-value un-built piece that is NOT derive-blocked.
- **The `trace` chain = COMPOSE, but derive-blocked.** The raw→derived→ground-truth chain is the moat differentiator (ADR-368/376). It deserves a composed surface — but it cannot exist until the derive step writes `derived_from`. Scope it; park it.
- **Retention = COMPOSE (one control).** A small dial. Placement open (§5).

---

## 4. What is BLOCKED on the derive step (be honest about the ceiling)

Two of the highest-value legibility pieces cannot be built until the deferred code limb (the derive step + scheduler GC, ADR-392 §5 step 8) lands:

- **The derived-understanding view** — there is no derived object to show until a derive act writes one.
- **The connector `trace` chain** — `derived_from` doesn't exist on connector data until derive writes it.

So the FE work partitions cleanly:

- **Derive-INDEPENDENT (buildable now)**: the registry de-dup (§2), the enriched selection surface (declared × observed), the retention dial, capture freshness. These stand on Phase 1–3 substrate that already exists.
- **Derive-DEPENDENT (scoped, parked)**: the derived view + the trace chain. Build when derive ships.

**Do not pretend the connector story is legible end-to-end before derive exists.** The mirror (Files → Intake) shows raw; the moat surface (trace) waits.

---

## 5. Open questions the build session must resolve

1. **Registry: backend-served or FE-seeded?** Recommend `GET /api/connectors/catalog` projecting the existing backend per-provider registries (kills FE/BE drift). Fallback: hand-seed `web/lib/connectors/registry.ts`, converge later.
2. **Retention dial placement.** Per-connection (in the Manage subsurface — most contextual)? Or workspace-level (one `governance/_retention.yaml`, so a single control in Settings)? The substrate is currently per-workspace (D8 wrote one `governance/_retention.yaml`); a per-connection dial would need a per-connection retention key. Recommend workspace-level control first (matches the substrate), per-connection later if demanded.
3. **Does the enriched selection surface need a capture-freshness backend?** Web watches read `_watch_signal.yaml`; connectors have no equivalent "observed" signal yet. Either the capture recurrence writes a `_capture_signal.yaml` sibling (the SourcesCard-symmetry move), or freshness is derived from the newest `inbound/{platform}/` file mtime. Recommend the signal file — it's the proven shape and survives the re-founding mechanism flip.
4. **Where does the `trace` chain surface (when unblocked)?** Options: inside the Manage subsurface (per-connector), the Activity → In pane (per-event), or the Files Get-Info modal (per-file, the ADR-388 revision-chain precedent). The Files Get-Info modal already shows revision chains — extending it to walk `derived_from` may be the singular move. Decide at derive-build time.
5. **Commerce/Trading cards.** They're `authKind: apikey`, not OAuth, and Trading is a program ground-truth connection, not context-in. The registry must model `authKind` so the universal card renders the API-key connect UX for them without a special-case block. Confirm they fold into the registry cleanly (they should — they're just another metadata shape).

---

## 6. Recommended sequence (when the operator directs build)

**Phase A — de-dup to universal (derive-independent, highest structural payoff):**
1. Build/seed `CONNECTOR_REGISTRY` (§2) — ideally the backend catalog endpoint.
2. Refactor `ConnectedIntegrationsSection` from 7 hardcoded blocks → `registry.map(<ConnectorCard/>)`. One universal card. **This retires the anti-pattern the operator flagged** and is the prerequisite for everything else being scalable.

**Phase B — enrich selection (derive-independent, highest operator value):**
3. Capture-freshness signal (`_capture_signal.yaml` or mtime) + the enriched Manage subsurface (declared × observed), mirroring `SourcesCard`.
4. The retention dial (workspace-level control over `governance/_retention.yaml`).

**Phase C — derive-dependent (parked until the derive step + GC land):**
5. The derived-understanding view (mirror via Files + a compose).
6. The connector `trace` chain (the differentiator; decide placement per §5.4).

Phase A is the one that matters most for the operator's stated concern (scalability) and is pure refactor — no new backend. Phase B is the highest-value new legibility. Phase C waits on the backend limb by construction.

---

## 7. The one-line thesis

**Connectors get ONE universal, metadata-driven surface family — a registry + a universal card + filtered mirrors — exactly like `WorkspaceMembersCard` does for principals and `hosts.py` does for MCP hosts. The Nth connector is a registry entry, not a code change. Raw is mirrored (Files → Intake), never re-composed; the moat `trace` chain is composed but waits on the derive step. The per-platform card is the anti-pattern to retire, not extend.**

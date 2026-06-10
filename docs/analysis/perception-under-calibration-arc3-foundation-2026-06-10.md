# Perception Under Calibration — the Arc-3 Conceptual Foundation

**Date:** 2026-06-10 (fifth session capture, same day)
**Hat:** B (external-developer surface — discourse capture). This is the
conceptual foundation the eventual arc-3 ADR drafts from. No code, no canon
edits — FOUNDATIONS/GLOSSARY touches happen at arc-3 ratification.
**Origin:** the 2026-06-10 regroup, continued after ADR-330/331 ratification.
The operator asked: *what is the most axiomatic, durable, future-proof
treatment of reality-in — analogous to filesystem-native substrate? Or is it
API/MCP-maxxing done scalably? Or something more fundamental?* Then: *is the
implied systematic approach MCP-as-perception-in resolved through a
marketplace/registry, rather than one-by-one connectors?*
**Succeeds:** `four-flow-completeness-and-program-floor-2026-06-10.md` §2
(the perception field — this doc supplies its axiomatic treatment),
`reality-in-current-standing-and-setup-as-rendering-2026-06-10.md`.
**Status:** Hardened as conceptual foundation. Build deferred to arc-3
(demand-pull triggers unchanged: bundle #3, first non-trader watch need, or
alpha-author post-330 deepening). A scoped Claude Code audit/ADR session will
branch from this doc when the operator calls it.

---

## 1. Why integration-maxxing is the trap (stated structurally)

The conventional SaaS answer — a connector catalog, value = coverage —
commoditizes twice: once because Zapier/Composio-class platforms
industrialized it, and again because **MCP is commoditizing them** — every
platform is shipping its own MCP server, making the connector layer a public
utility. A solo founder cannot and should not compete there. The good news
inside the threat: **transports are being commoditized FOR us.** The
architectural conclusion: never let transport be the layer where identity
lives.

## 2. The axiom-shaped answer: representation over mechanism

Filesystem-native substrate was durable because it axiomatized the *form
persistence takes* (attributed files, revision chains) and left mechanisms
swappable. ADR-330 made the identical move for outcomes without naming it:
the durable thing is the **candidate shape** (attested, idempotent,
provenance-carrying row) + one pipe; providers are peripherals. Perception
wants the same three-layer cut:

| Layer | What it is | Durability class |
|---|---|---|
| **1. Declaration** (kernel, axiomatic) | The operation declares what it watches — the universe/watch declaration. Judgment about which slice of infinite reality serves the mandate. | **Cannot commoditize** — it is not technology. Selection is the scarce thing (the operator's correction, four-flow capture §2). |
| **2. Contract** (kernel, axiomatic) | Reality enters **only as an observation**: attributed, attested, source-referenced, dated, *distilled* — written to substrate per Axiom 1. The perception twin of `OutcomeCandidate`, **reusing the same attestation enum** (ADR-330 D2). | Representation bet — outlives any protocol. |
| **3. Transport** (deliberately commodity) | REST, RSS, CSV, MCP, whatever follows MCP. Device drivers. The kernel knows the driver-class contract, never the device. | Swappable by design; consumed from the ecosystem, not built. |

OS framing pays rent again: **transports are drivers; MCP is USB; the
marketplace/registry is the driver repository.**

## 3. The fundamental thing: perception is the operation's epistemics — under calibration

Perception is not data ingestion. The kernel question is never "how do we get
data in" — it is **"what does this operation believe about the world, on what
evidence, attested by whom, as of when."** Two consequences:

- **Observations are claims with provenance**, living in the same attributed
  revision chain as everything else, subject to the same distill-don't-mirror
  rule (ADR-153 honored permanently).
- **Perception is calibratable — flow 4 judges attention, not just actions.**
  The trader already proves it end-to-end: `by_signal` expectancy attribution
  in money-truth is the loop reporting which watched signals earned their
  keep. Generalized: **the watch declaration is a portfolio of attention;
  calibration prunes it over tenure.** No integration platform has this —
  Zapier moves data and has no concept of whether a feed deserved the
  attention. This is the layer beyond MCP-maxxing.

**Candidate axiom clauses (for arc-3 FOUNDATIONS treatment, operator to
ratify):**

> *Reality enters only as attributed observation. Watches are declared, never
> crawled. Transports are peripherals. Attention is calibrated.*

Each clause is already proven somewhere in the trader; none is touchable by a
connector catalog or by whatever replaces MCP.

## 4. The systematic approach (the operator's read, confirmed + disciplined)

**The flow — declaration drives discovery, never the reverse:**

1. Operator (or program) **declares a watch** ("watch these competitors'
   changelogs," "watch SEC filings mentioning X," "watch my newsletter
   stats").
2. The system **resolves a transport**: first against already-connected
   transports, then by **searching the MCP registry/marketplace** for a
   server that can perceive the declared thing.
3. Candidates surface as a **proposal**; the operator **authorizes the
   binding** — a trust grant, same governance shape as `platform_connections`.
4. The watch goes live: recurrence reads through the transport, **distills
   observations into attributed substrate**, narrative-traced.
5. **Calibration eventually prunes**: which watches earned their attention.

**Discipline qualification 1 — never capability-shopping.** The failure mode
is "browse the marketplace and add interesting perception" — the
connector-catalog disease wearing the new protocol. Bright line: **a
transport only ever enters because a declared watch needs it.** Watch-first,
transport-second, always. The declaration layer (judgment) stays sovereign
over the transport layer (commodity).

**Discipline qualification 2 — binding a foreign MCP server is an epistemic
and security act.** Every binding carries an attestation grade (official
platform server ≈ `platform`; community server ≈ weaker — the ADR-330 enum
extends, no new taxonomy). Foreign tool output is untrusted input: never raw
into substrate, only as distilled attributed observations; consequential
actions remain Reviewer-gated. Containment = disciplines that already exist,
named as applying here.

## 5. The one early transport decision: become an MCP **client**

YARNNN is already an MCP *server* (ADR-169 interop face — context flowing
out). The symmetric move — **one MCP-client implementation in the kernel** —
makes every platform's MCP server a Mode-A read transport automatically:
capability-gated, usable by harvest (ADR-331) and recurrences, **zero bespoke
connectors ever again.** One implementation; the ecosystem builds the driver
catalog for free, forever. This is the architecturally-scalable form of
"maxxing" — and the only transport-layer investment that earns kernel status.

## 6. Staging (crawl / walk / run)

| Stage | What ships | Trust shape |
|---|---|---|
| **Crawl** | Kernel MCP client; operator-pasted server configs (manual binding). | Operator authorizes each binding explicitly. |
| **Walk** | Registry search resolves declared watches into **proposed** bindings (the marketplace move). | Proposal → operator authorization; attestation grade from registry provenance. |
| **Run** | The Reviewer notices a perception gap against the mandate and itself **proposes** a new watch + transport — perception management under the same propose/approve loop as capital actions. | Fully inside the existing judgment loop; delegation-level gated. |

**Bundle consequence (durability dividend):** MANIFESTs get *more* durable —
a program can declare a required perception **shape** ("continuous price
oracle") rather than a vendor binding ("Alpaca"); resolution moves to
setup-time, exactly where ADR-331's sequence lives. Vendor bindings become
late-bound.

## 7. Fences + for the time being

- **ADR-330/331 untouched** — they proceed on existing tools; nothing here is
  in their scope.
- **Arc-3 build stays demand-pulled** (triggers per four-flow capture §4).
  This doc is its discourse base, not its starting gun.
- **Out of scope here and at arc-3 v1:** building any bespoke connector;
  webhook/push ingestion (pull + wake-on-event via existing wake sources
  first); observation-contract schema details (arc-3 ADR's job); FOUNDATIONS
  amendment text (drafted at ratification, from §3's candidate clauses).
- **The durability test, recorded:** representation bets outlive mechanism
  bets (filesystems vs databases-of-the-decade; HTTP vs its transports;
  RSS-the-contract vs every reader). Declaration + observation-contract +
  calibrated attention is a representation bet; "N integrations" is a
  mechanism bet. YARNNN makes the first kind.

---

## 8. Addendum (2026-06-10, later same day) — feasibility verified + route-(i) program assembly hardened

**MCP feasibility (evidence-checked):** the ecosystem matured into exactly the
shape §5–§6 assumed. The official registry is live with a queryable API
(registry.modelcontextprotocol.io — "an app store for MCP servers"); remote
servers standardized on OAuth 2.1 with `.well-known` discovery (servers
classed as OAuth resource servers, June-2025 spec); the 2026-07-28 release
candidate moves the protocol to a stateless HTTP core — a structural fit for
stateless-computation-over-substrate. Crawl-stage implementation = small
build: MCP client in the API (same SDK family as the existing FastMCP
server), bindings stored on the `platform_connections` pattern (encrypted
tokens, existing OAuth machinery), foreign tools surfacing as dynamic entries
in the existing capability-gated dispatch. Hard parts are non-protocol:
per-server consent UX, tool-schema heterogeneity, community-server quality
variance, injection surface (already disciplined — distill-only,
Reviewer-gated), foreign-call cost (budget gate already meters).

**Route (i) — program assembly via inference (hardened in-session):** the
operator proposed the setup loop close as two routes — *"explain your
workspace so we can infer from it"* OR *"pick from curated yarnnn-authored
programs."* Route (ii) is ADR-331 step 1 (built territory). Route (i) is the
deferred operator-assembled-program horizon (ADR-312) re-entering through a
structured door, made **specifiable by the four-flow model**: inference's job
= **drafting the four flow declarations** (constitution · watches/domains ·
deliverable specs · ground-truth declaration) from the operator's explanation
+ uploads + harvest; the operator ratifies the draft; it forks like any
bundle. It remains *a program* — assembly, never freehand workspace-level
declarations — so ADR-332 D3's singular path survives intact.

**The gating correction (the operator's closing question, answered):** route
(i)'s viability does NOT ride on perception breadth — it rides on **flow-3
declarability**. ADR-330's CSV fallback gives ground truth a universal floor;
331's harvest + uploads + websearch floor flow 1 — so a *thin but honest*
route (i) is feasible right after 330+331, before any MCP client. Arc-3 adds
*richness* (world-present watches, registry resolution as a setup step), not
viability. Where a described operation has no declarable ground truth, the
flow-completeness vocabulary supplies the honest sentence: "this program runs
flow-incomplete — knowledge mode, no calibration."

**The dependency ordering (ratified):** 330/331 implementation → arc-3 crawl
(MCP client, manual bindings; ADR drafted with ratification pause) →
**program-assembly ADR** (route i — a named future ADR, added to ADR-332 §5's
ledger) → walk (registry resolution inside setup). One workspace mantra for
the resist-half: Direction A's line stays — no *operating* workspace without
a program; the bare workspace remains a coherent resting state (Layer-1
floor + interop trojan); what's new is that **no onboarding path dead-ends in
programlessness** — `/setup` always confronts the program decision via the
two-route card.

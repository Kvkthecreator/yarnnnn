# ADR-437 — BYOK key scope, the enterprise tier, and the pre-lane metering floor

**Status**: Accepted (2026-07-10, operator-ratified — doc-first, no code). Implementation is demand-gated to the seat lane going GA (as ADR-409); this ADR closes the two BYOK ambiguities ADR-409 left open so that build, when it lands, has no undecided fork. The metering-floor items (§4) are the exception — they are pre-lane-launch hardening, buildable independent of BYOK, and should ship before the chat lanes leave the `MODEL_ROUTER_ENABLED`-off state.

**Revision (2026-07-10, same session):** §3 originally made BYOK the enterprise tier's *gate/definition*. Operator review corrected this: **BYOK is an *option within* the enterprise tier, not its definition** — enterprise is the *capability bundle* (custody controls · on-prem lane · support · scale/seats), and BYOK is a toggle inside it (default OFF = YARNNN-managed keys + metering; ON = the customer's key, seat-chat draws nothing). Enterprise capabilities and key-ownership are **orthogonal axes**: a security-conscious org with no in-house LLM procurement wants the bundle but is happy for YARNNN to hold the keys and bill them. Making BYOK mandatory-for-enterprise would push that (larger) segment to a lower tier they've outgrown. §3 + §6 are rewritten to reflect this; D1 (workspace-scoped key) and §4 (metering floor) are unchanged.
**Date**: 2026-07-10
**Dimension**: Purpose (Axiom 3 — what the operation pays for, and on whose key the intelligence runs) over the ADR-391 cost architecture.
**Relates to**: ADR-409 (per-seat Type-B — the pricing model this refines), ADR-408 (three altitudes + the seat lane + the D4 router), ADR-391 (balance/allocation/ledger — preserved), ADR-396 (one meter, hide-dollars — preserved), ADR-310/311 (the MCP interop face — the de-facto BYOK already true today), ADR-373/378 (the workspace is the unified, outermost binding unit — no data fork).
**Amends**: ADR-409 — closes its two deliberate ambiguities. ADR-409 D4 named "BYOK / BYO-endpoint access" as a tier axis and §3 called it "the customer's own **keys**," but left unresolved (a) whether the key attaches to the **workspace** or each **member**, and (b) whether BYOK is a **tier gate** or a cross-tier **add-on**. This ADR resolves both. Everything else in ADR-409 (D1 seat=human, D2 per-workspace pool, D3 steward-always-meters, D5 hard-stop) is **preserved verbatim**.

---

## 1. The model in one paragraph (the regrouping)

Money in YARNNN bills **three things, at two scopes, and BYOK moves exactly one line.**

| What is billed | Scope | Who pays | Key it runs on | BYOK effect |
|---|---|---|---|---|
| **The plan** — base + allowance | **Workspace** | Workspace owner | — (a subscription, not compute) | unchanged — you still pay for the substrate + the team |
| **The steward** — Freddie, embeddings, system judgment | **Workspace** | Workspace pool | **always our platform keys** | **never** — platform infrastructure a customer key cannot substitute (ADR-409 D3) |
| **Seat-level chat** — a member's model-as-hands (Altitude 2, ADR-408) | **Principal** (the member) drawing the **workspace** pool | Workspace pool today | our keys today; **the customer's key under BYOK** | **this is the only line BYOK moves** |

The load-bearing insight: **BYOK is not a discount on the whole bill — it is the member's *hands* going free while the substrate and the steward stay yours (and stay ours to meter).** This is why ADR-409 could rule "no usage tax on BYOK" without giving away the business: the parts that constitute the moat (the attributed substrate, the steward's judgment) were never the parts BYOK touches. It also dissolves the "personal vs enterprise" anxiety — there is **no data/substrate/RLS/metering fork** (ADR-373/378: one unified commons, N=1 byte-identical). "Enterprise" is a **capability flag on the same workspace**, not an account type.

## 2. D1 — The BYOK key attaches to the WORKSPACE, not to each member

A BYOK provider key is set **once, by the workspace owner, on the workspace.** Every member's seat-level chat lane resolves to that one key; there is no per-member key.

**Why workspace-scoped:**
- It is the enterprise **key-custody** story in its honest form: IT/procurement provisions one credential against the org's own Anthropic/OpenAI/Google account, and the whole team's model-as-hands usage runs on it. That is precisely the "your keys, your infra, our substrate" empowerment the tier is sold on.
- It keeps resolution simple: one key per workspace, resolved at the router call site by `workspace_id` — the same axis the pool, the allowance, and the tier already key on (ADR-391/407). No new principal-level key machinery, no per-member key UI, no mixed metered/un-metered lanes inside one workspace to reason about.
- It matches the substrate model: the workspace is the binding unit (ADR-373). A credential that powers the workspace's seat lanes belongs at the workspace, alongside the connector credentials the workspace already holds (the `platform_connections` pattern — a workspace-scoped secret, owner-managed).

**Explicitly rejected: member-level keys** (each member brings their own). Rejected because it produces no single custody story, splits one workspace into metered and un-metered lanes that the pool math must special-case per-principal, and multiplies the key-management surface — the over-engineering ADR-378's "one commons" discipline warns against. A member's *own standing MCP connection* remains a `foreign-llm` grant (ADR-373/386) and is unaffected by this decision — that is the interop face (§5), not the seat lane.

**Deferred, not rejected: a member override on top of the workspace key.** ADR-409's phrasing left room for "member/workspace"; this ADR takes the workspace side and parks the member-override as a demand-gated future (build iff a real customer needs per-member keys inside a BYOK workspace). The workspace key is the floor; an override is additive and would not change the workspace-key resolution path.

## 3. D2 — Enterprise is a capability bundle; BYOK is an OPTION within it (default: YARNNN-managed)

BYOK is available **only on the enterprise tier** — but it is **not what defines the tier, and not mandatory within it.** Enterprise is defined by its **capability bundle**: key-custody controls, the on-prem endpoint lane (ADR-409 D4), longer retention, support, and scale/seats. **BYOK is a toggle inside that bundle**, with two settings:

- **Default (OFF) — YARNNN-managed.** The enterprise workspace uses *our* keys and *our* metering, exactly like every lower tier. The customer pays and never touches a key. This is the byte-identical-to-lower-tiers key path — zero new resolution logic, it *is* the default.
- **ON — customer's key.** The workspace's seat-chat lanes resolve to the customer's own workspace-scoped key (D1), and that line draws nothing (ADR-409 D2). The steward keeps metering on our keys regardless (D3).

**Why enterprise capabilities and key-ownership are ORTHOGONAL (the correction):** "wants enterprise scale/custody/support" and "wants to run on their own LLM keys" are independent. A large, security-conscious org with **no in-house LLM procurement** wants the bundle but is *happier* for YARNNN to hold the keys and send one bill (one vendor, one invoice, zero key ops). Welding BYOK to the tier's definition would force that org — likely the *larger* enterprise segment — either into a lower tier they've outgrown or away entirely. Making BYOK an **option** captures both the "we run our own keys" org *and* the "just handle it for us" org under one enterprise tier.

**Why still enterprise-only (not cross-tier):**
- The **capability bundle** (on-prem, custody controls, support, scale) is what gives enterprise its honest, non-fakeable reason to exist and re-justifies a rung above the ADR-429 Free + one-paid collapse. BYOK availability is *one* of those capabilities, not the whole reason. Lower tiers stay internalized-only (fastest setup, our keys, usage margin) — the ADR-409 D4 solo-vs-enterprise segmentation, now carried by the bundle rather than by BYOK alone.
- Keeping BYOK availability *inside* enterprise (rather than a cross-tier add-on any paid workspace can flip) keeps the **zero-draw optics** clean: "your model calls draw nothing because they're on your key" reads as an enterprise-capability benefit, not a "pay us a subscription AND pay your own LLM bill" add-on tax. The margin-on-their-own-key optics ADR-409 flagged stay avoided.

**Explicitly rejected: a separate "Enterprise-BYOK" tier.** BYOK-managed and BYOK-on are the *same* enterprise tier with a toggle — **not two named tiers on the pricing page** (that reintroduces the tier proliferation ADR-429 killed). If BYOK-ON meaningfully lowers *our* COGS (the customer's seat-chat usage is off our books), that may surface as a discount or a different seat-allowance *modifier on the one tier* — never as a second tier.

**Explicitly rejected: cross-tier add-on toggle** (any paid workspace flips BYOK). It decouples BYOK from the enterprise narrative and muddies the zero-draw copy for the mass tiers; enterprise-only-but-optional gets the flexibility without the story cost.

## 4. D3 — The pre-lane metering floor (buildable now, independent of BYOK)

The seat-chat routers were built ledger-first and are correctly accounted for: every tool-loop round writes one `execution_events` row, priced by the single `compute_cost_usd_inclusive`, attributed `principal_id` + `workspace_id`, drawing the workspace pool exactly like a steward call (ADR-408 D4 spike, verified with prod receipts; the router *reports*, the ledger *records* — ADR-396 double-charge invariant intact). This is **not an accounting gap.** But two guards are *soft* today, and both should be hardened **before** the lanes leave the `MODEL_ROUTER_ENABLED`-off state — because the moment lanes go GA, a soft guard becomes a live liability:

- **F1 — Unpriced model = hard block, not a warning.** Today a routed model with no `_BILLING_RATES` row logs a warning and prices at the Sonnet default rate (`model_router.py` warns; `telemetry.py` falls back to `_DEFAULT_RATE`). Before GA this must be a **hard block**: a model with no rate row does not route in prod. The `LANE_MODELS` ↔ `_BILLING_RATES` sync is already gate-tested, so in practice every routable model is priced — this makes the guarantee enforced rather than incidental. (This is the D4-spike rule "an unpriced model never routes in prod" promoted from convention to enforcement.)
- **F2 — Dropped ledger row = alert.** `record_execution_event` is fail-open (never raises) and the lane loop swallows a failed write as a warning — the standard fail-open posture, correct for not breaking a user's turn on a transient DB blip, but it means a cost row can silently vanish. Before GA, a dropped-write path should **emit an alert** (not merely a log line) so a systematic drop is caught, not just an isolated one. The call still succeeds; the alert is the observability floor.

Neither F1 nor F2 is a router bypass and neither depends on the BYOK decision — they are the metering floor the lane launch rides on. **A BYOK call is the one case that legitimately lands a row with cost-to-us = 0** (ADR-409 D2) — F1/F2 must treat a zero-cost BYOK row as *correct*, not as a dropped/unpriced row. The distinguisher is provenance (the row carries the BYOK-key marker), not the cost being zero.

## 5. The interop face is already de-facto BYOK — and stays distinct

When an external ChatGPT/Claude/Gemini reaches into the workspace over MCP as a `foreign-llm` principal (ADR-310/311/373), **that LLM's inference runs on the customer's own subscription, off our books entirely** — we store and judge the write but run no model call for it; we meter only our *own* platform-side work on that principal's behalf (the async judgment wake, embeddings). This is structurally "the customer's own key/subscription pays for the external inference" and it is **live today**.

This ADR does **not** fold the interop face into BYOK. They are two different lines:
- **Interop (foreign-llm, live today):** the customer's *external* LLM reaches *in*; its inference was never on our books; free to add, we meter only our steward-side work on its writes (ADR-416 D2). No key custody by us — the customer's LLM holds its own credential.
- **BYOK seat lane (enterprise-gated, this ADR):** the customer's key powers the *in-app* Altitude-2 chat lanes (model-as-hands *inside* YARNNN); we hold the key (workspace-scoped custody) and resolve to it at the router.

Keeping them distinct matters: the interop face is the free, always-on reach that anyone gets; the BYOK seat lane is a paid enterprise capability. Conflating them would either wrongly gate the free interop face behind enterprise, or wrongly imply we run the external LLM's inference. The enterprise pitch may *reference* both ("connect your own ChatGPT over MCP for free, and run your in-app team lanes on your own enterprise key") — but they are two capabilities, not one.

## 6. What this makes "enterprise" (the summary)

Enterprise is **not an account type and not a data split.** It is a **capability bundle** on the *same* unified workspace — custody controls · on-prem lane · support · scale/seats — with **BYOK as a default-off option inside it**:
- **Managed (default):** the enterprise workspace runs on our keys and our meter, byte-identical to lower tiers on the key path. The customer pays for the *bundle* (custody controls, on-prem, support, seats) and never touches a key. Priced on the bundle + per-seat + usage-through-the-pool.
- **BYOK (toggle ON):** the workspace's own key (workspace-scoped, §2) powers the seat-chat lanes → that line draws nothing (ADR-409 D2) → the customer's own LLM account carries that usage. Priced on the bundle + per-seat (usage is theirs now); a possible COGS-based modifier, never a separate tier (§3).

In both settings: same substrate, same RLS, same single metering ledger; the steward always meters on our keys (D3) so the meter stays honest and the moat stays ours. BYOK-ON is **one flag flipping one resolution path** — the managed default adds nothing.

This is the "empowering but not over-engineered" shape: the enterprise customer who *wants* key custody gets it; the enterprise customer who *doesn't want to think about keys* just pays and we handle it — **one tier, one toggle, no fork.**

## 7. Amends / preserves

**Amends ADR-409:** resolves its two open BYOK sub-questions — key scope (→ workspace, §2) and shape (→ enterprise-only but *optional within* the tier, §3). ADR-409's §4 implementation note ("`TIER_CONFIG` gains a `byok` flag") is refined: BYOK *availability* is an enterprise-tier capability, but BYOK *engagement* is a **per-workspace toggle** (default OFF = managed) — so the implementation is a tier-level `byok_available` capability **plus** a workspace-level `byok_enabled` setting pointing at a **workspace-scoped** key resolved by `workspace_id` at the router call site. Managed-default is the byte-identical lower-tier key path; BYOK-ON is the one added resolution branch.

**Preserves (unchanged):** ADR-409 D1 (seat = human member), D2 (per-workspace pool, one ledger, router-reports/ledger-records, BYOK rows land at cost-to-us = 0), D3 (steward always meters on platform keys), D5 (hard-stop + top-up, no overage billing, no credit currency). ADR-396 (one meter, hide-dollars, Type-B). ADR-391 (balance/allocation/ledger). ADR-373/378 (unified commons, workspace as binding + outermost unit, no data fork). ADR-310/311/416 (the interop face and its metering split, §5).

## 8. Open (deliberately)

- **Numbers** — the enterprise-tier seat price, allowance sizes, and where BYOK sits relative to any intermediate tier — set at implementation as launch-test values against UNIT-ECONOMICS (ADR-396 discipline), changed freely on evidence.
- **Member-override key** — parked (§2), build iff a real BYOK customer needs per-member keys inside one workspace.
- **On-prem endpoint lane** — the sibling enterprise capability (ADR-409 D4); its own build scope when the tier builds.
- **Altitude-3 persona-agent pricing** — still its own future ADR (ADR-409 §5 / ADR-334-superseded), unaffected here.

# ADR-561 — The marketing surface states only what the code does

> **Status**: **Accepted + Implemented** (2026-08-13). Four false claims retracted from the marketing surface, one false runtime string corrected at its cause, and the data page rebuilt as the single honest home for data-handling claims.
> **Date**: 2026-08-13
> **Authors**: KVK (operator) + Claude (collaborator)
> **Dimensional classification** (Axiom 0): **Discipline**. The defect was not in any mechanism — it was that the copy describing our mechanisms was written independently of them, and drifted.

**Amends**:
- **SITE-COPY-SPEC-v1 §4** — the FAQ ceiling moves from ≤12 to ≤15 to admit a "Your data" category. The spec predates this audit.
- **`/privacy` §4, §5, §7** — sub-processors, connector reach, and retention all restated.

**Preserves**: [ADR-478](ADR-478-permanent-delete-and-the-trash-that-holds.md) **D2** (no retention timer, ever, by default — this ADR makes the *copy* match the decision rather than reversing it), [ADR-209](ADR-209-authored-substrate.md) (attribution at the write path — the claim this ADR leans on hardest), [ADR-474](ADR-474-blob-ownership.md) / [ADR-476](ADR-476-purge-workspace-scope.md) (blob collection, whose helpers L5 now reuses).

---

## 1. Context

The operator asked for an audit of the landing and marketing pages, benchmarked against comparable providers, on what we can *honestly* say about data handling.

The audit's finding was not the expected one. **The engineering is more honest than the marketing copy.** The ADRs openly refuse to build what the privacy page promises; the export manifest enumerates its own omissions; `write_revision()` makes attribution structurally unskippable. The exposure was concentrated in a handful of sentences written *about* the architecture without being checked *against* it.

Four claims were false at audit time:

1. **"we will remove your personal data within 30 days"** (`/privacy` §7). Contradicted by ADR-478 D2 — *"No retention timer. Ever, by default."* The claim was wrong in both directions: deletion where it happens is immediate and synchronous, and nothing sweeps up what immediate deletion misses.
2. **"AI providers (Anthropic Claude, OpenAI)"** (`/privacy` §4), presented as the complete list. `LANE_MODELS` carries four prefixes — Gemini and DeepSeek were undisclosed. Not hypothetical: ADR-557 §1 records a production call that reached Gemini over the network on a scheduled path with no human in the loop. The landing page's own connector chips already advertised Gemini, so the site contradicted itself.
3. **Connectors can "Save" and "Read"** (`/privacy` §5). The MCP roster is nine verbs including `delete`, `move`, and `share` — and `share` can mint a **member** grant. A materially larger authority than disclosed.
4. **"All data has been deleted."** — returned by `DELETE /account/deactivate` at the moment of deletion, while that path never collected blob content. Bucket objects survived account deletion, unreachably.

A fifth claim, *"it's all yours to export"*, is partially true: the git export is real and carries the full attributed revision chain, but the manifest omits conversations.

## 2. D1 — A marketing claim is a claim about the code, and is checked against it

The rule this ADR establishes: **every data-handling sentence on the marketing surface names a behavior some file enforces, or it does not ship.** The audit's receipts (`lane_runner.py:63–79`, `authored_substrate.py:614–634`, `mcp_server/server.py:337–400`, ADR-478 D2) are the standard of evidence — not the writer's model of the system.

The corollary is the harder half: **claims we cannot make are named rather than implied.** The three audited comparables diverge sharply here, and the divergence is the decision.

| | Data claims on the product page | Certifications | What a reader assumes |
|---|---|---|---|
| x.ai/bot | **None** — zero matches for privacy/train/retention/encrypt | None named; `/security` ~120 words, deep-dive subpaths 404 | That there are some |
| OpenAI | One dedicated page, ~2,300 w, tiered Q&A | SOC 2 Type 2, ISO 27001 | Accurate |
| Notion | Six-word claims + a linked mechanism FAQ | SOC 2 Type 2, ISO 27001, HIPAA | Accurate |

x.ai sells an agent that asks to log into your tools and says nothing about data handling; its hard commitments are enterprise-tier only, while its consumer policy lists training as a default use. **We inherit Notion's two-register shape** — a short claim on the landing page, the mechanism and every exception one click away — and we inherit *nobody's* silence.

## 3. D2 — No badge without an audit

The operator asked whether we could emphasize trust marks in the style of a competitor's certification row (CASA, SOC 2 Type II seals).

**We cannot, and the page says so.** A badge reads as *externally verified* in a way prose does not; there is no honest way to render one for an audit that has not happened. `/privacy-architecture` carries a four-mark row in that visual shape, filled with **mechanisms rather than certifications** — never trained on, signed at the write path, no retention timer, exports as plain git. Each maps to enforced behavior.

The page states the absence plainly rather than letting a seal imply otherwise. This is not an apology. Against a comparable set where the weakest player lets readers assume, saying it is the differentiator a small team can actually hold — and it follows CANON-LOCK-2026-07-30 §19, which already named the constraint as the position: *"a solo founding team with no enterprise privacy/compliance apparatus cannot serve procurement — and does not need to."*

**Amendment (2026-08-13, same day).** The operator asked that the gaps read as *planned* rather than merely absent — a fair ask, and honest **only where a plan exists**. The four gaps are therefore split, and must not be recombined:

| Gap | Framing | Why |
|---|---|---|
| Blob persistence after deletion; private-body reads on app-layer checks | **"On the roadmap"** | Both are named as owed in §7 below. Scheduled work — "planned" is a fact. |
| SOC 2, ISO 27001 | **"Not yet started"**, conditioned on customer need | No roadmap exists anywhere in canon. Calling these planned would invent a commitment, which is the same defect as inventing a badge — one asserts a credential we lack, the other a timeline we lack. |
| DPA, BAA | **Route to a conversation** | Neither is an audit. They are signable agreements, so the honest answer is "not off the shelf; ask us," not a status. |

The rule generalizes: **"planned" is a claim about the future and needs the same evidentiary standard as a claim about the present.** A roadmap item is checkable against the owed list; an aspiration is not.

## 4. D3 — "Private" is the wrong frame; boundary and receipt are the right one

yarnnn is a shared, attributed commons. Teammates and their AI connections are *supposed* to see the work — that is the product. **A blanket privacy claim would be the one genuinely false thing on the page.**

Every line therefore speaks to boundary and receipt instead: who can read a file is a **grant** you make and revoke (never a species rule, per ADR-405), every change is **signed** at the write path, and content leaving over MCP is governed by the receiving provider's terms. This also produces the strongest available claim: **per-action attribution, which neither OpenAI nor Anthropic publishes.** Anthropic's closest line is that Claude inherits your permissions and there are no elevated service accounts; ours is structurally stronger, because every write carries a named principal by enforcement.

## 5. D4 — A false message is fixed at its cause, not its wording

`DELETE /account/deactivate` returned *"All data has been deleted."* The tempting fix was to soften the sentence. **The right fix was to make it true**, because the sentence described what the endpoint was supposed to do.

L5 now reuses the ADR-474/476 helpers the L2 purge path already had: `_collect_blob_shas()` runs **before** the revision chain is deleted (the revisions are the only thing naming the blob), and `_delete_workspace_blobs()` removes the rows and their bucket objects after. Both were already imported from a single home; neither needed new code.

The message still changed — to name what was removed rather than assert totality — because blob collection is best-effort per object and "all data" is a claim this path cannot keep even now. **Wording follows behavior; it does not substitute for it.**

## 6. What did NOT change, and why

- **ADR-478 D2 stands.** The 30-day promise was retracted, not honored. A retention timer remains refused by default; the copy now presents its absence as the deliberate protection it is.
- **The MCP scope gap is not written around.** `valid_scopes=["read"]` is the only scope and nothing enforces per-verb, so a read-labelled token can call `delete` and `share`. The copy states real connector reach honestly, but **this is a code defect and is owed a fix** — see §7.
- **Export omissions are disclosed, not fixed.** Conversations still do not export.

## 7. Owed

1. ~~**Per-verb MCP scope enforcement**~~ — **CLOSED by [ADR-563](ADR-563-the-mcp-scope-authorizes-it-does-not-decorate.md)** (2026-08-13). Three additive scopes (`files:read` ⊂ `files:write` ⊂ `files:share`), enforced at the `resolve_request_client()` chokepoint; the legacy `read` grant is retained so no live connector breaks.
2. **The `workspace_blobs` blanket read policy** — `USING (true)` from migration 158, never dropped or replaced. Any authenticated user knowing a SHA-256 can read any blob row. Named on the data page as current work; owed as a migration.
3. **Conversation export**, to make "it's all yours to export" unqualified.
4. **A copy-vs-code gate.** This ADR's discipline is currently prose. The durable form is a test asserting that the provider list rendered on `/privacy-architecture` matches `LANE_MODELS` — the drift that started this audit would have been caught the day it appeared.

## 8. Consequences

The marketing surface is now checkable: every claim traces to a file, and the two pages that carry claims (`/privacy`, `/privacy-architecture`) are reachable from the footer rather than one being orphaned. The cost is that the site now advertises its own gaps — deliberately, since a reader who finds an unstated gap discounts every stated claim, and the comparable set shows exactly what that silence buys.

# ADR-494 — The Connector Registry Is Singular, and a Door Opens Itself

**Status**: Accepted (2026-07-29, operator-ratified — "delegate the detail and sequencing to you… ensure streamlined, singular implementation"). Implemented same day.
**Date**: 2026-07-29
**Authors**: KVK (operator) + Claude (collaborator)
**Hat**: A
**Dimension**: Channel (Axiom 6 — what the operator is offered, and where a door lands) + Substrate (Axiom 1 — one source for one fact)
**Relates to**: ADR-392 (the connector lane + the FE registry this extends), ADR-401 (the connection lifecycle — the nine stages; D6 health-derived-never-stored), ADR-404 D2 + its 2026-07-04 amendment (capture dormancy + the ratified pane-level hide), ADR-425 (the credential is an account object — why Connectors lives behind the account door at all), ADR-183 (commerce), ADR-187 (trading), ADR-414 D5 (program-as-hire — why trading has no reachable capture path), ADR-491 (the settings doors re-cut, whose D1/D3 normalizers this deletes), ADR-340 DP29 (mirror once, compose few)
**Amends**: **ADR-491 D1 + D3** (the two retired-pane normalizers are deleted — the symptom is removed by fixing the cause). **ADR-392** (the FE registry gains a `status` field and is no longer the *only* offered-set source — it is now one half of a CI-gated pair). **ADR-183 / ADR-187** (commerce + trading are retired from the offered set; their substrate, tools, and webhook are untouched).

---

## 1. Context — an audit of what the operator is actually offered

The operator opened User Settings and found (a) the Connectors pane, not Account, and (b) five offered connectors, two of which — Lemon Squeezy and Alpaca Trading — read as concepts from an earlier era. The question asked was sharper than "hide them": *is there an up-to-date way of handling what connectors are shown here, and how?*

The audit answer was no. Three findings, each with a receipt.

### 1a. The offered set had three sources, and they had already drifted

| Source | Members |
|---|---|
| `web/lib/connectors/registry.tsx` (renders the list) | slack, notion, github, commerce, trading |
| `routes/integrations.py::SUPPORTED_PLATFORMS` (filters the summary) | slack, notion, github, commerce, trading |
| the summary EMISSION loop, a bare tuple | slack, notion, github |

The third was a live bug: a connected commerce or trading connection was never emitted as active, and the frontend keys connectedness off that summary — so a *connected* Lemon Squeezy would have rendered under "New connection" forever. Nothing detected the divergence because nothing compared the lists.

(Five further partial registries exist — OAuth configs, provider aliases, the tool registry, capture bindings, landscape discovery — and have genuinely drifted: `reddit` carries a full OAuth config with no connect surface. Those are *capability* registries, not the offered set, and are deliberately out of scope here.)

### 1b. Two connectors were an invitation into a dead end

Prod receipts, 2026-07-29:

```
platform | status | count          /workspace/_captures.yaml → captures: []
---------+--------+------
notion   | active |     1
slack    | active |     1
```

**Zero commerce and zero trading rows have ever existed.** Neither appears in `CONNECTOR_CAPTURE_BINDINGS` — neither has ever had a connector-lane reader. Trading's only capture path is the alpha-trader bundle's `SyncPlatformState` mirrors, which require a hire that has no operator surface (ADR-414 D5; ADR-382 deferred; "13 workspaces, 0 minted"). An operator who pasted an Alpaca key would have connected successfully and then perceived nothing, forever, with no way to discover why.

### 1c. A dormant connector was claiming a reading

The live UI showed *"Slack ✓ Connected · Last read 3w ago · 2 sources read."* The substrate says otherwise:

```
/workspace/_capture_signal.yaml → capture-slack: {items: 2, observed_at: '2026-07-03T06:40:31Z'}
```

That signal was frozen the day before ADR-404 made the capture lane dormant. `captures: []` means nothing has read since. The connected-row rendered `freshness` **ungated by `captureEnabled`**, so it kept displaying the last pre-dormancy signal as though current. ADR-392 D5 established honest freshness for the *not-yet-reading* case; the *no-longer-reading* case was never covered.

Compounding it: `captureEnabled` was inferred *incidentally* from a per-provider capture-signal response, so it stayed false whenever no connected freshness-capable provider happened to be fetched. The endpoint built for this exact purpose — `GET /api/integrations/capture-lane`, ADR-404's own amendment — shipped with **no caller at all**.

### 1d. The door didn't open itself

The operator's landing on Connectors was not a default — `defaultPane="account"` was already correct. It was **restore**: `settings.pane` is RESTORE-class, replayed on every foreground.

But the UserMenu offers **"User Settings"** (the door) and **"Connectors"** (one pane) as separate items. Under restore they collapse into the same destination. And this is the same shape that produced the bug ADR-491 patched a day earlier in `274c2be`: a remembered `billing` made the account door literally unenterable. The fix there was a hand-written per-value normalizer — which every future pane retirement would need again.

---

## 2. D1 — The registry is the single offered-set source, CI-gated across the language boundary

A connector's presentation must live in TypeScript (the browser renders it) and its authorization must live in Python (the API guards it). That duplication cannot be deleted. So it is **gated** instead: `api/services/connector_registry.py` holds `{provider: status}`, and `api/test_adr494_connector_registry.py` *parses the .tsx* and asserts provider-for-provider, status-for-status, order-for-order equality. Adding the Nth connector to one side only fails CI.

`SUPPORTED_PLATFORMS` is deleted (derived from `CONNECTOR_PROVIDERS`). The emission tuple is deleted (iterates the registry) — which fixes 1a's live bug by construction. Both literals are banned-pattern checked so they cannot grow back.

**`status` has exactly two values, `live` and `retired`. There is deliberately no `dormant`** — dormancy is a property of the capture LANE (one flag, ADR-404 D2), not of a connector. Encoding it per-row would recreate the two-sources-for-one-fact problem this ADR exists to remove.

## 3. D2 — Commerce and trading are RETIRED (hide-not-delete)

Retired = **not offered**, still **recognized**. The split is load-bearing and the two halves of the UI read different lists on purpose:

- **connected** ← the full registry, so a historical connection still renders with its real name and brand and stays disconnectable. *Retiring must never orphan an existing fact.*
- **available** ← `OFFERED_CONNECTORS`, so a retired connector is never offered.

`_reject_if_retired()` — one guard, derived from the one registry — closes the connect verb with a 410 at both api-key endpoints. Their credential FORMS are deleted (see D6); the endpoints survive because the Lemon Squeezy webhook is an independent live path and an alpha-trader re-hire must be able to re-light trading with a one-word change.

This follows the ADR-404/425 hide-not-delete precedent exactly: substrate, tools, clients, and the webhook are untouched.

## 4. D3 — The summary reports every recognized provider

The emission loop iterates the registry, retired providers included. They exist, so they must be *reportable*; they are simply not *offered*. This is what makes D2's "connected" half work.

## 5. D4 — One read of the capture-lane flag, and a dormant connector says so

`getCaptureLane()` gains its caller: the flag is read **once, directly**, from the zero-DB endpoint built for it. The per-signal inference is deleted (one source, one fact).

With a trustworthy flag, the connected row tells the truth: **"Connected — not reading (capture is paused)."** A connector that cannot read must not claim a reading. This extends ADR-392 D5's honest-freshness discipline from the not-yet case to the no-longer case.

Note what is deliberately *not* done: ADR-404's amendment ratified hiding the Connections pane **entirely** while dormant. That was correct when Connectors was a Channels-surface *perception* pane. ADR-425 then reframed the credential as an **account object** — holding, seeing, and revoking your own Slack credential is legitimate whether or not a lane reads it. So the pane stays and tells the truth inside itself. This is a conscious, narrow scoping of ADR-404's amendment at the pane it no longer describes, not an oversight.

## 6. D5 — `settings.pane` is ephemeral: a door opens itself

`settings.pane` and `workspace-settings.pane` move to `SURFACE_EPHEMERAL_PARAM_KEYS`. They stay **OWNED** — every deep-link still works (the UserMenu's Connectors item, `?pane=billing` from the balance glance, old bookmarks) — and are only dropped from the **REMEMBERED** set.

Applying `surface-preferences.ts`'s own test (*does replaying it answer a question the member is asking NOW?*): a pane is a momentary look at one drawer, not a place you live in. The nav list sits one click away, so nothing is lost. `chat.lane` stays RESTORE — a conversation genuinely *is* a place you live in.

**Both ADR-491 normalizers are deleted.** They existed only to clean *persisted* stale values; nothing is persisted now, so a retired pane falls to the default-pane fallback by construction. One mechanism replaces a hand-written case per retirement — the Singular Implementation discipline applied to the fix itself. `settings.connector` (the ADR-392 Phase B Manage drill-in) is ephemeral too: it is document-identity-shaped by the same test.

## 6a. D6 — The "New connection" blurb is capture-state-aware (follow-on, same day)

D4 made the connected rows honest, and that immediately exposed a contradiction **within one pane**: a row reading *"Connected — not reading (capture is paused)"* sat directly above a blurb promising *"a capture reads the selected ones into your workspace."* Operator-caught on the deployed build.

The blurb was the frozen-freshness error in its **forward-looking** form. Verified: while the lane is dormant, connecting a platform stores a credential and does nothing else — the watch seed is gated (`routes/integrations.py` Select) and the drain never runs (`unified_scheduler.py`). So the promise described a chain that cannot execute.

The blurb now branches on `captureEnabled`. Dormant, it says what is actually true — the credential is held, yours, disconnectable, and nothing will be pulled in yet. The pane header ("Connect, see status, disconnect") is left unchanged: it promises no reading, so it was already accurate.

**The general rule this makes explicit: a surface may not promise a capability whose mechanism is gated off.** D4 covers the past tense (don't claim a reading that happened before dormancy); D6 covers the future tense (don't promise one that can't happen after).

## 7. What was NOT done, and why

- **The endpoints were not deleted.** ~470 lines of commerce/trading routes interleave with the live Lemon Squeezy webhook and scaffold helpers. Deleting them would break an independent live path for no gain the retirement doesn't already deliver. Retirement is enforced at the door.
- **The five capability registries were not unified.** OAuth configs, aliases, tool registry, capture bindings, landscape discovery answer *what can this platform do*, not *what is offered*. Folding them in is a real follow-on; conflating them here would have widened the cut past the operator's question.
- **The dead FE bot-role fossils** (`slack_bot`/`notion_bot`/`github_bot` in `types/index.ts`, `agent-identity.ts`, the orphaned `constants/agents.ts` and `IsometricRoom.tsx`) were left. They are genuine ADR-414 Phase F vocabulary debt, but they are *agent*-vocabulary, not connector-registry — a separate sweep with its own blast radius.

## 8. Validation

- `api/test_adr494_connector_registry.py` — **29/29**, covering registry parity (membership · status · order), retirement semantics, both deleted literals as banned patterns, the guard call sites, the FE derivations, the one-flag-one-read invariant, the freshness gate, the ephemeral keys, both deleted normalizers, and the D6 capture-aware blurb (verified to FAIL when the unconditional promise is reintroduced).
- Siblings green: `test_adr404_capture_dormancy.py` 28/28 · `test_adr341_two_settings_doors.py` 46/46.
- `tsc --noEmit` clean; `next build` green (170/170 routes).
- Prod receipts in §1b/§1c are reproducible: the `platform_connections` count query and the two `workspace_files` reads.

**Not verified by these gates** (needs a human click): the rendered account door landing on Account after a foreground, and the "Connected — not reading" sub-label in a live browser session.

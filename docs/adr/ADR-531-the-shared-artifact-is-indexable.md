# ADR-531 — The shared artifact is indexable: the conscious accommodation

**Status**: Accepted (2026-08-07, operator-ratified over the collaborator's stated objection —
recorded as such deliberately, see §4).
**Date**: 2026-08-07
**Authors**: KVK (operator) + Claude (collaborator)
**Hat**: A (system canon — real-operator-facing)
**Dimension**: Channel (Axiom 6 — who may reach a shared artifact, and through which retrieval
architecture)

**Amends**: **ADR-513 D4** — `noindex` is removed from the `/s/{token}` surface (page + API
exits). `Cache-Control: no-store` and the status/expiry enforcement are **unchanged**; "dark
means dark" survives at the origin. What changes is that a share link may now be **retained by a
third-party index**, which makes revocation authoritative *at the origin* and **best-effort in
the world** (§3).

**Preserves**: ADR-513 D1 (the token is the read capability) · D2 (the projection boundary) ·
D3 (member HTML renders exclusively in `sandbox=""`) · ADR-530 (the machine projection + the
`.txt` address) · ADR-517 (grants govern; mint authority unchanged).

---

## 1. Context — the measured finding

ADR-529/530 made the share link readable by machines: server-rendered HTML, a text projection,
a `.txt` machine address, and `robots.txt` no longer forbidding the fetch (D4.1/D4.2). Claude,
Slack-class unfurlers and direct fetchers all read it. **ChatGPT still could not**, and the
diagnosis took several wrong turns before landing.

The isolating test: a share minted with a **nine-character token** (`readme777`) — short enough
that transcription error is impossible. It still failed. Running ChatGPT's own checklist against
it:

| Check | Measured |
|---|---|
| HTTP 200, not 403/404/redirect | PASS |
| Content in the initial HTML (SSR) | PASS |
| No user-agent filtering | PASS — `ChatGPT-User`, `GPTBot`, `OAI-SearchBot` all 200 with content |
| `robots.txt` not restrictive | PASS — `/s/` allowed (ADR-530 D4.1) |
| `.txt` returns `text/plain` | PASS |
| **not sending `noindex`** | **FAIL — we send it** |

And the symptom named the mechanism: *"the **search engine** doesn't even index or fetch the URL
— it falls back to unrelated results."* **ChatGPT's link retrieval is search-index-mediated;
`noindex` is precisely the instruction not to retain a page in an index.** Claude fetches the URL
directly, which is why Claude reads the same link fine. This was never JS rendering, bot
blocking, DNS, host, or token — every one of which was tested and cleared.

## 2. The framing correction (the collaborator's error, recorded)

The collaborator first presented this as *"removing `noindex` loosens the privacy posture."*
**That was wrong, and the operator corrected it**: *"IF an artifact is shared via link for anyone
to access (including AI), aren't we assuming privacy is fore-gone?"*

Correct — and ADR-513 D1 already said so: *"the sharer already decided the world-with-the-link
may see this."* Three properties were being collapsed into one word:

| Property | Controlled by | State once a link is minted |
|---|---|---|
| **Confidentiality** — may a holder read it | the token | **already surrendered, deliberately** |
| **Discoverability** — may a non-holder find it | `noindex` | the actual question |
| **Revocability** — may I take it back | `status='revoked'` | **the real remaining control** |

`noindex` never protected confidentiality; it cannot. So the decision is **not** privacy-vs-reach.
It is **discoverability-vs-revocation-integrity**, and stating it that way is what makes the
trade-off honest.

## 3. D1 — The `/s/{token}` surface is indexable, and the cost is named

`noindex` is removed from the share page's metadata and from the API's share exits.
`Cache-Control: no-store` **remains** on every exit (including 404/410), as does the
status/expiry enforcement — an intermediary must still not serve a revoked link from cache.

**The cost, stated plainly rather than discovered later:**

> **A revoked link goes dark at the origin. A copy already retained by a third-party index does
> not.** Revocation remains authoritative *for the URL we serve* and becomes **best-effort in the
> world**: an indexed snapshot may outlive the revoke by however long that index chooses to keep
> it. This is a real reduction in the strength of the one guarantee that survives handing out a
> capability link.

This is accepted knowingly for the reason in §4. It is **not** a discovery we made afterwards,
and any future session finding an indexed-but-revoked share should read this section rather than
file a bug.

**What does NOT change**: the token remains 192 bits (`secrets.token_urlsafe(24)`) — a link is
still undiscoverable *by guessing*. Indexing makes it discoverable *by searching*, which is a
different and now-accepted threat model. Mint authority (ADR-517 D3), the viewer/member shapes,
the projection boundary (ADR-513 D2) and the locked sandbox (D3) are all untouched.

## 4. D2 — Why: market reality, over the collaborator's objection

The collaborator recommended **against** this, arguing that accommodating one vendor's retrieval
architecture with a permanent weakening of revoke was a large concession for a narrow cause, and
that MCP already reaches ChatGPT without any link.

**Operator ruling**: *"although i agree with your reasoning, the reality is chatgpt is still the
most widely used web based chat LLM. and thus, we should try and accommodate them."*

Ratified. The reasoning is recorded rather than smoothed over, because the trade-off is real and
a future reader deserves both halves: **a share link that the most-used assistant cannot read is
a broken share link in practice, whatever the architecture says.** Reach through the front door
the market actually uses beats a cleaner guarantee nobody exercises.

## 5. D3 — What this ADR deliberately does NOT do

- **No "publish" act.** The operator scoped it out explicitly (*"publish is of a different
  concern"*): publishing is a **distribution** act (audience, reach, GTM); sharing is an
  **interop** act (a specific collaborator, human or AI, in a specific document). Conflating
  them would repeat the ADR-515 one-button-three-jobs error. If publish is ever built, it is its
  own ADR.
- **No TTL wiring.** `ttl_days` exists on `ShareCreateRequest` and no surface passes it. Bounded
  exposure is good cowork hygiene and remains owed — but it is **not** an answer to indexing
  (expiry governs the URL; an index governs its own copy) and must not be shipped as though it
  were.
- **No change to `robots.txt`** — `/s/` is already allowed (ADR-530 D4.1). `/invite/` stays
  disallowed.
- **No indexing of anything else.** Only the `/s/{token}` share surface. The authenticated
  cockpit, `/invite/`, and every API route outside shares keep their existing posture.
- **No weakening of `no-store`, the sandbox, the projection boundary, or mint authority.**

## 6. Open

1. **Does an indexed-and-revoked share need an operator-facing signal?** Today revoke is silent
   about the world. A "this may persist in search results" line at revoke time would be honest.
   Named, not built.
2. **TTL** (§5) — owed on its own merits.

## 7. The one-line statement

**A capability link already surrendered confidentiality at mint, so the real question was never
privacy but revocation integrity — and we knowingly trade some of it for reach, because a share
link the most-used assistant cannot read is a broken share link.**

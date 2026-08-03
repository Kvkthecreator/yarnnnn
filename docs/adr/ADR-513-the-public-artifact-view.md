# ADR-513 — The Public Artifact View: the Attribution Walk as the Landing Page

> **Status**: **Accepted — operator-delegated 2026-08-03** (the Tier-1 "arrival arc" of the
> ADR-512 deferred queue; the operator's continued-delegation ruling: "implement in full
> all the tiers"). Implemented in the same pass.
> **Date**: 2026-08-03
> **Authors**: KVK (operator, by delegation) + Claude (collaborator)
> **Hat**: A (a new public boundary — the first unauthenticated read surface)
> **Dimensions**: Channel (Axiom 6 — a new entry door) + Identity (what an anonymous
> visitor is: a *reader of a capability link*, never a principal) + Substrate (what may
> cross the public boundary)

**Relates to**: ADR-437 D4 (the share wedge — "the artifact is the landing page, `trace`
demonstrated on contact"; this ADR makes that literally true for strangers) · ADR-465
(share the membership primitive; D2 join-only genesis is the sibling half of the arrival
arc) · ADR-512 (the file is the unit of interop; the walk is its proof surface) ·
CANON-LOCK-2026-07-30 ("share with a link" — the hero sentence this makes non-false for
non-members) · ADR-478/476 (deletion — a revoked share must go dark).
**Amends**: the `/s/{token}` surface (ADR-437 D4.1): preview becomes public and
content-bearing; accept stays auth-gated. Fixes a pre-existing hole: preview did not
check `status`/`expires_at` — a revoked or expired share still previewed.

---

## 1. Context

"Share with a link" (the v19 PRODUCT sentence) was false for non-members: `/s` sat in the
middleware's protected prefixes, so a stranger clicking a shared deck bounced to signup
before seeing anything. Every minted share was a dead end for exactly the audience the
copy-paste-seam ICP shares *to*. Meanwhile the moat's one felt demonstration — the
attribution walk ("you · Aug 2 · your agent · Aug 5 · Claude · Aug 6") — sat behind the
same wall.

The 2026-08-03 recon fixed the design constraints with receipts:

- **There is no HTML sanitizer in the codebase.** `ensure_kernel_style_in_html` is a CSS
  retrofitter, not a sanitizer; nothing strips scripts. Member-authored HTML is arbitrary
  HTML+JS.
- The in-app render pattern for untrusted artifacts is the fully-locked iframe
  (`sandbox=""`, no scripts — `WebViewer`); two in-app viewers use looser sandboxes and
  are explicitly NOT the pattern here.
- Public FastAPI routes exist by *omitting* the auth dependency (the webhook precedent);
  data access then rides the service client, so **the token is the only authority**.
- `get_share_by_token` fetches more than preview returns (`shared_by`, `workspace_id`,
  share `id`) — the response model is the safety belt.

## 2. D1 — The share link is a capability; reading it requires no account

`GET /api/s/{token}` becomes **public** (no auth dependency). Possession of the token IS
the read authority — the same model as the accept surface's "any authenticated principal
may accept," extended one honest step: the sharer already decided the world-with-the-link
may *see* this. The token is `secrets.token_urlsafe(24)` (192 bits) — enumeration is not
a real threat; revocation is the control (D4).

An anonymous visitor is **not a principal**: no grant row, no attribution, no write path,
no session. They are a reader of a capability. Becoming a principal still requires
auth + accept (unchanged, `POST /s/{token}/accept` keeps its auth dependency).

## 3. D2 — What crosses the public boundary (the projection, exact)

The public payload is a **narrow projection**, enumerated here so additions are deliberate:

| Field | Content | Rationale |
|---|---|---|
| `workspace_name`, `label`, `role`, `status` | as today | the preview facts |
| `artifact_name`, `artifact_kind` | display name + `html \| text` | rendering dispatch |
| `artifact_content` | the artifact's **current content only** | the thing being shared |
| `walk` | `[{authored_by, when, change}]`, newest-first, capped | **the attribution walk — the moat demonstrated on contact** |

What **never** crosses: `shared_by` (a user UUID), `workspace_id`, the share row `id`,
revision **content** or **diffs** (the walk is metadata — who/when/what-message; the
history's bytes stay members-only), any second file (no listing, no links into the
commons), embeddings, grants. A bare workspace share (no artifact) returns the preview
facts only.

## 4. D3 — Rendering: locked sandbox, never inline, never same-origin

The FE renders `artifact_content` of kind `html` exclusively via
`<iframe srcDoc sandbox="">` — the `WebViewer` grammar: no scripts, no same-origin, no
forms, no popups. Text/markdown kinds render as escaped text. Because there is no
sanitizer (§1), **inlining member HTML into the public page DOM is forbidden**, as is any
looser sandbox; a future sanitizer changes nothing here (defense stays layered). The
public page skips the authed projection/citation pass (`useArtifactProjection`) — raw
current content only.

## 5. D4 — Lifecycle honesty: dark means dark

The public route enforces `status == 'active'` and `expires_at` (marking expired on
read, as accept does) — closing the pre-existing hole where a revoked share still
previewed. Responses carry `Cache-Control: no-store` and `X-Robots-Tag: noindex` — a
capability link must be neither cached by intermediaries nor indexed; revocation must be
the end of it.

## 6. D5 — What this deliberately does not do

- **No rate limiter in this pass** — named owed, not silently skipped. The MCP
  `AuthRateLimitMiddleware` (1b3409c) is per-process and keys the raw socket IP, which
  behind Render's proxy is the proxy — honoring `X-Forwarded-For` safely is its own small
  piece of work. The token's 192 bits carry enumeration; the limiter is anti-scraping
  polish for a *known* link.
- **No public revisions endpoint, no public RevisionHistoryPanel** — the walk rides the
  one payload; the in-app panel (with revert) stays members-only.
- **No unauthenticated accept, no anonymous comments/reactions** — reading is the whole
  public surface.
- **No second token class** — one share row, one token; `member`/`viewer` (ADR-465 D3)
  govern what accepting mints, not what previewing shows.

## 7. Implementation (this pass)

1. `api/routes/shares.py` — `GET /s/{token}` drops the auth dependency; adds
   status/expiry enforcement; response extends with `artifact_name/kind/content` +
   `walk` (service-client read of the artifact + its revision metadata, capped);
   headers per D4.
2. `web/lib/supabase/middleware.ts` — `"/s"` leaves `PROTECTED_PREFIXES` (verified:
   `/settings`/`/sources`/`/setup`/`/schedule`/`/system` are separately listed).
3. `web/app/s/[token]/page.tsx` — dual-state: the public view (sandboxed artifact +
   the walk + honest role copy) for everyone; the accept action gates on session
   presence and bounces to login with `?next=/s/{token}` when absent.
4. Gate: `api/test_adr513_public_view.py` — public route has no auth dep; projection
   contains no forbidden fields; status/expiry enforced; headers present; middleware
   prefix removed; FE sandbox is the locked form.

## 8. The one-line statement

**The share link becomes what the hero already claims it is: a stranger clicks it and
sees the work and who made it — the attribution walk as the landing page — with reading
as a capability, joining as the auth-gated act, and revocation as the end of both.**

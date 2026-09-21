# Korean on the marketing site — IP, a toggle, or `/ko`

**Date**: 2026-09-21 · **Status**: analysis, nothing built
**Occasion**: the operator, after the Korean audit: *"can we consider like IP of the accessing user to
show korean? if not, at least a language toggle like conventional web app … if troublesome for
components, can scope to just text or whatever best judgment."*

> Measured on 2026-09-21 against the live tree and a real `next build`.

---

## 0. The answer in one paragraph

**Do not use IP.** It is the one option here that is actively worse than doing nothing, and the
reasons are not preference — they are SEO mechanics and a correctness argument (§2). **The toggle you
asked for as a fallback is in fact the right primary**, and it is much cheaper than it looks, because
ADR-660 already built the entire mechanism: catalogs, a resolution chain, a cookie, `Accept-Language`
negotiation, and a working switcher component. The marketing site is the only place that does not use
it, and only because mounting the provider in the root layout would have made every page dynamic
(ADR-660 D3). **That constraint is real and is the whole design problem.** §4 gives a shape that keeps
every marketing route static AND speaks Korean, by putting the locale in the URL (`/ko/…`) — which is
what ADR-660 D1 already said indexed pages should do, and the reason it left the app URL-free.

**Recommended: Option C (`/ko` prefix + toggle), phase 1 scoped to 6 pages.** ~2–3 days. It is the
only option that is simultaneously static, indexable, shareable, and correct.

---

## 1. What already exists (so this is not a from-scratch build)

| Piece | Where | Reusable for marketing? |
|---|---|---|
| `next-intl`, ICU, catalogs | `web/messages/{en,ko}.json` — 2330 keys | ✅ add a `marketing` namespace |
| The roster + endonyms | `web/i18n/config.ts` (`English`, `한국어`) | ✅ unchanged |
| The resolution chain | `resolveLocale` in `web/i18n/resolve.ts` — account → cookie → `Accept-Language` → en | ✅ steps 2–4 are exactly what a signed-out page can use |
| `Accept-Language` negotiation | `negotiateLocale` in `i18n/config.ts` | ✅ **already handles the "detect their language" goal, honestly** |
| The cookie | `NEXT_LOCALE`, written by the switcher | ✅ |
| A working switcher | used on `/auth/login` today | ✅ drop into `LandingHeader` |
| Middleware on marketing routes | `middleware.ts` matcher already covers them | ✅ the hook point for a prefix rewrite |
| `alternates.canonical` | `lib/metadata.ts:158` | ⚠️ needs an `alternates.languages` sibling for hreflang |

**Nothing needs inventing.** The question is purely *where the locale comes from* and *what it costs
the static build*.

## 2. Why NOT IP geolocation — three independent reasons, any one sufficient

Vercel exposes `x-vercel-ip-country` and the middleware already runs on every marketing route, so
this is **technically trivial** — roughly five lines. It is still the wrong call.

**2.1 It breaks SEO, which is the entire point of the marketing site.**
Googlebot crawls predominantly from **US IPs**. Serving different content at the same URL based on IP
means Google indexes the English version and never discovers the Korean one — so the Korean pages you
paid to write earn zero organic search, which is the only thing `/ko` was for. Google's own guidance
calls IP-based redirection a crawlability problem and recommends distinct URLs with `hreflang`. IP
targeting and SEO are in direct conflict; you cannot have both.

**2.2 Location is not language.** The Korean diaspora, expats and English-preferring Koreans in Korea
all get Korean they did not ask for; a Korean speaker in Seattle gets English. `Accept-Language`
carries what the user *actually configured* — it is a declaration, not an inference. Using IP when a
truer signal is already in the request is strictly worse information.

**2.3 It collides with a live ruling.** ADR-660 D2 ruled that a negotiated guess is **never written
down**, because *"a guess recorded as a cookie would be indistinguishable from a choice."* An IP guess
is a weaker guess than `Accept-Language` and would inherit the same problem. The chain's ranking
(choice > device > guess > English) is the existing law, and IP does not improve any rung of it.

⭐ **The good news: what you wanted from IP, you already have.** `Accept-Language` *already* detects a
Korean user automatically — ADR-660 §9 drove it: `ko-KR,ko;q=0.9` → Korean, `en-US` → English, with
**zero** `Set-Cookie`. A Korean visitor with a Korean browser/OS gets Korean with no toggle touched.
That is the auto-detection you asked for, by a better signal, already built and already tested.

## 3. The real constraint: static marketing vs. a locale the server must read

ADR-660 D3: the provider mounts in four scopes and **never the root layout**, because reading a cookie
or header there makes every route dynamic. `app/layout.tsx:23` still hardcodes `<html lang="en">` and
imports nothing from `next-intl` — deliberately.

**Receipt — the current build, this tree:** every marketing route is `○` (static): `/`, `/about`,
`/blog`, `/developers`, `/engines`, `/faq`, `/how-it-works`, `/invest`, `/llms.txt`,
`/.well-known/mcp.json`, plus `● /blog/[slug]` × 113 SSG paths.

So a naive "just add the provider to the root layout" would:
- turn ~20 static routes dynamic, including 113 blog pages,
- cost TTFB and CDN caching on exactly the pages that need to be fast for SEO,
- and break the invariant ADR-660 guarded across four separate passes.

**This is why the answer is a URL prefix rather than a cookie read.** With `/ko/pricing` as its own
route, the locale is in the path — statically knowable at build time — so both language versions
prerender. No dynamic rendering, no cookie read, and the page is separately indexable and shareable.

That is precisely what ADR-660 D1 already said: *"URL-prefixed locales are the convention for indexed
pages, and the app is `noindex`."* The ADR excluded the app from prefixes **and pointed at prefixes
for the marketing site**. This is not a new decision; it is the other half of one already made.

## 4. The three options, costed

### Option A — IP detection
**Cost**: ~5 lines. **Verdict: rejected**, §2. Not recommended at any scope.

### Option B — Toggle + cookie, no URL change
Mount the provider on a marketing layout, read `NEXT_LOCALE`, add the switcher to `LandingHeader`.

- ✅ Cheapest translation path; no routing work.
- ❌ **Turns ~20 static routes dynamic**, 113 blog pages included.
- ❌ **Zero SEO value** — one URL serving two languages; Google indexes one.
- ❌ A shared link shows the recipient *your* language, or theirs — never the one you meant.

**Verdict**: acceptable only if you explicitly do not want Korean SEO. It buys readability for
Koreans you already reached, not reach.

### Option C — `/ko` prefix + toggle + hreflang ⭐ RECOMMENDED
`next-intl`'s documented App Router pattern: an `app/[locale]/` segment with
`generateStaticParams` returning both locales.

- ✅ **Every route stays static** — each prerenders twice (en + ko).
- ✅ **Indexable**: `/ko/pricing` is a real URL with its own `hreflang` alternate.
- ✅ **Shareable**: a Korean link stays Korean for the recipient.
- ✅ **Auto-detection retained**: middleware negotiates `Accept-Language` on `/` and redirects a
  `ko-KR` browser to `/ko` — the IP goal, by the better signal, and Googlebot (US, `en`) still lands
  on the English canonical.
- ✅ The toggle becomes a link between two real URLs — no client state.
- ⚠️ Build time and output roughly double for translated routes.
- ⚠️ Every internal marketing `<Link>` must be locale-aware (`next-intl`'s `Link` handles this).

**Cost: ~2–3 days for phase 1.**

## 5. Recommended scope — phase 1 is six pages, not fifteen

Translating all ~336 strings across 15 pages plus 113 blog posts is a month and mostly waste. Scope by
what a Korean visitor actually needs to decide to sign up.

**Phase 1 — the decision path (6 pages, ~120 strings):**
`/` (landing) · `/pricing` · `/how-it-works` · `/faq` · `LandingHeader` · `LandingFooter`

Plus `<html lang>`, `openGraph.locale` (`lib/metadata.ts:104` hardcodes `en_US`), `alternates.languages`
for hreflang, and the sitemap emitting both.

**Phase 2, only if phase 1 earns it:** `/about`, `/engines`.

**Explicitly OUT, and why:**
- **The blog (113 posts)** — a translated post is a *content* project, not a string swap. Out by the
  09-16 analysis's own scoping. `/ko/blog` should link the English posts rather than 404.
- **`/privacy`, `/terms`** — legal text. A mistranslated term of service is a liability; these stay
  English with a note, or get a professional translation, never a dev-written one.
- **`/invest`, `/developers`** — investor and developer audiences read English.
- **The stage notice** — ADR-660 §8 ruled it single-sourced; do not fork it.

## 6. Build order

1. **Decide the option** (§7 asks you).
2. Move the marketing routes under `app/[locale]/`, `generateStaticParams` → `['en','ko']`.
   **Gate the whole step on the build's route table**: every marketing route must still read `○`, and
   the count must roughly double rather than drop. That is the receipt ADR-660 used four times.
3. Extract phase-1 copy into a `marketing` namespace. Existing ADR-660 gate arms (parity,
   placeholders, is-it-Korean, every `t()` resolves, no Hangul in an `en` value, `one`-arm plurals)
   cover it **for free**, since they read the whole catalog.
4. Middleware: negotiate `Accept-Language` on an unprefixed path and redirect; never write a cookie
   (ADR-660 D2), and let Googlebot reach the English canonical.
5. `hreflang` + `x-default`, `openGraph.locale`, sitemap both locales.
6. Toggle into `LandingHeader` (and `LandingFooter`), as links between URLs.
7. Drive it: `/` and `/ko/` at 390px, Korean and English, plus a real `curl` with `Accept-Language:
   ko-KR` confirming the redirect and **no `Set-Cookie`**.

## 7. What I need you to rule

- **IP detection — I recommend against it** (§2: it breaks the SEO that is the site's whole purpose,
  location ≠ language, and ADR-660 D2 already ruled a guess is never recorded). `Accept-Language`
  gives you the same auto-detection from a better signal and is already built. **Confirm you accept
  dropping IP**, since you raised it first.
- **Option B or C.** C is the recommendation and the only one that buys Korean organic search;
  B is cheaper and buys none. This is a go-to-market call, not a technical one.
- **Phase-1 scope** — the six pages of §5, or a different cut.
- **Legal pages** — English-only with a note, or budget a professional translation? Not a
  dev-translation call.

## 8. Receipts

| Claim | How measured |
|---|---|
| Every marketing route static today | `npx next build` route table — `○` on all 15 + `●` × 113 |
| Root layout is `lang="en"`, no next-intl | `app/layout.tsx:23` |
| ~336 distinct marketing strings, 15 pages / 21 landing components | scripted JSX-text + copy-prop scan |
| Blog is 113 posts | `ls content/posts/*.md \| wc -l` |
| Mechanism already exists | `i18n/resolve.ts`, `i18n/config.ts`, `messages/{en,ko}.json` (2330 keys) |
| `Accept-Language` already negotiated, never recorded | `resolveLocale` step 3; ADR-660 §9 drove it |
| Middleware already runs on marketing routes | `middleware.ts` matcher |
| `openGraph.locale` hardcodes `en_US` | `lib/metadata.ts:104` |
| `alternates` has canonical but no `languages` | `lib/metadata.ts:158` |
| One shared header/footer | `components/landing/LandingHeader.tsx` (113 lines), `LandingFooter.tsx` (177) |

## 9. Related

- `docs/adr/ADR-660-the-interface-speaks-korean.md` — D1 (no prefix in the *app*, prefixes are for
  indexed pages), D2 (a guess is never written down), D3 (why the root layout stays clean), §8 (defers
  exactly this).
- `docs/analysis/korean-beyond-the-interface-2026-09-21.md` §3.11.
- `docs/analysis/language-support-korean-feasibility-2026-09-16.md` — scoped the blog out.

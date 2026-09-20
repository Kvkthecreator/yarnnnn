# ADR-660 — The interface speaks Korean: a language is a member's preference, never a workspace's

> **Status**: **Accepted + Implemented — the mechanism and the sign-in path** (2026-09-20, operator: *"consistent
> request to support korean language as an optionality … industry conventions, just fitting to our service
> specifics"*). D1–D6 shipped and driven (§9). **Coverage is the open half**: 1005 lines of literal copy
> across 104 files remain English, held by D4's ratchet; §8 names what is not decided here.
> **Date**: 2026-09-20
> **Authors**: KVK (operator) + Claude (collaborator)
> **Dimensional classification** (Axiom 0): **Who** (a preference of the human, not of the commons).
> Gate: `api/test_adr660_the_interface_speaks_korean.py`.

**Amends** — [VOICE-AND-TONE.md](../design/VOICE-AND-TONE.md) §5 (the guard follows copy into the catalogs) and
gains §7 (the Korean register).

**Preserves** (load-bearing, untouched):
- **ADR-638** — that ADR is about REGISTER (no internal vocabulary in an agent's prose). This one is about the
  natural language of the INTERFACE. Neither touches the other; `PARTICIPANT_REGISTER` is not edited.
- **The prompt change protocol** — no language instruction enters the lane frame. §6 says why.
- **ADR-405 D5 / ADR-407** — presentation state is never consulted for authorization. A locale is presentation.
- **`updateSession`** — the sole auth gate is not edited. Locale resolution does not pass through it.
- **ADR-373/378** — the workspace is a multi-principal commons. A file has no locale column and gains none.

---

## 1. The problem

Members have asked, repeatedly, for Korean. Every string a member reads is an English literal inside a
component: 239 `.tsx` files, `<html lang="en">` hard-coded, no catalog, no locale anywhere in the request.
Dates already format with `toLocaleDateString(undefined, …)` — the browser's locale — so a Korean member
today reads Korean dates inside English sentences. Nothing in the canon has ruled on natural language; the
limit is *never ruled*, not law.

## 2. D1 — The mechanism is the convention: next-intl, catalogs, no URL prefix in the app

`next-intl` (App Router, RSC + client, ICU messages). Catalogs are `web/messages/{locale}.json`, keyed by
namespace. The roster is `web/i18n/config.ts` — `LOCALES`, `DEFAULT_LOCALE`, the endonyms the switcher shows
(`English`, `한국어`; a language is always named in itself). Adding a third language is a catalog and a roster
row, nothing else.

The authenticated app carries **no locale in the URL**. A path there is an address members share with each
other across languages (`/files`, `/text`); a `/ko/files` link would hand an English reader a Korean shell.
URL-prefixed locales are the convention for *indexed* pages, and the app is `noindex`.

## 3. D2 — A language belongs to the human

A workspace holds several humans; two of them can read different languages and work in the same files. So
the preference is **account-level**, never workspace-level — `member_state` is scoped `(workspace, principal)`
and is the wrong home, because a member who chose Korean would meet English in their second workspace.

It lives in `auth.users.user_metadata.locale`: keyed by the human, no migration, already beside
`full_name`, and returned by the `getUser()` the authenticated layout already makes.

**One resolution chain, one function** (`resolveLocale` in `web/i18n/resolve.ts`):

1. the account's preference — signed in, fresh from `getUser()`, so a change follows the member to every device;
2. the device cookie `NEXT_LOCALE` — what was chosen on this device, which is all a signed-out page can know;
3. `Accept-Language`, negotiated per request and **never written down** — a guess recorded as a cookie would
   be indistinguishable from a choice and would outrank nothing honestly;
4. English.

The switcher writes the account *and* the cookie (so the sign-in page after sign-out is still in their
language), account first — the chain ranks it above the cookie, so refreshing before the write re-renders the
old language. On the sign-in page it writes the cookie alone; the first authenticated render adopts a cookie
into an account that has no preference yet. The reverse also holds: a signed-in render brings the device cookie
into line with the account (found by driving, §9).

The provider's error sentences are English. `AuthForm` words the common ones from their **code**
(`invalid_credentials`, `email_not_confirmed`, …); an unrecognised one keeps the provider's own sentence.

## 4. D3 — The provider is scoped, so the marketing site stays static

Reading a cookie in the root layout makes every route dynamic. The provider (`IntlScope`) therefore mounts in
three layouts only — `(authenticated)`, `auth/login`, `mcp/auth` — and the root layout imports nothing from
`next-intl`. `<html lang>` is set from inside the scope. The gate holds this, and the build's route table is
the receipt: the marketing routes stay `○`.

Three scopes, not two: `mcp/auth` mounts the same `AuthForm` as `auth/login`, and `useTranslations` **throws**
outside a provider — converting the form under two scopes would have broken the connector's sign-in. The gate
resolves each unscoped route's imports one level deep for exactly this. The cost is stated, not hidden: a
signed-out page can only learn its language from the request, so `/auth/login` and `/mcp/auth` stop being
prerendered.

A module-level constant (`PANE_GROUPS`, a label table) is evaluated once, before any member's language is known.
Such a roster holds catalog **keys** (`labelKey`), and the component words it at render.

## 5. D4 — The guard follows the strings

`test_voice_no_kernel_nouns_in_copy.py` reads JSX text and copy-bearing props under `web/`. A string moved
into `messages/en.json` leaves its sight, and the guard would go green over an emptying codebase. It gains a
catalog arm in the same commit that creates the catalogs — every catalog value is rendered copy by
construction, so the arm needs no context heuristic.

The Korean catalog is held by this ADR's gate rather than by English patterns:

- **parity** — `en` and `ko` have the same key set, both directions;
- **placeholders** — each key's ICU arguments match across locales (a dropped `{count}` renders a hole);
- **it is Korean** — a `ko` value contains Hangul, or is on a short allowlist of names that do not translate;
- **every call resolves** — each `t('…')` under a `useTranslations('ns')` names a key that exists in `en`
  (a missing key renders its own path in production, silently);
- **coverage only ratchets down** — the count of member-facing files that still render literal copy has a
  ceiling that a pass lowers and nothing raises. The allowlist-as-progress-meter, again.

A missing `ko` key falls back to English rather than throwing: a half-translated surface reads as English,
never as a broken one.

## 6. D5 — What an agent writes is not the interface

No language instruction enters the lane frame. Attended: the engine answers in the language it is addressed
in, and there is no receipt of it failing — the protocol admits an instruction only against a repeated,
observed failure. Unattended: a standing declaration writes a **file in the commons**, read by every member;
its language is a property of the work (its `CONTRACT.md`, its sources), not of whichever member's preference
happened to be nearest. Sending the locale to the API is also refused for now: nothing there would read it.

## 7. D6 — The Korean register

`해요체` throughout — the polite-informal register Korean product interfaces have converged on. Never
`합쇼체` (reads as a terms-of-service page), never `반말`. Buttons are nouns or bare verb stems
(`저장`, `삭제`), not sentences. Loanwords where Korean software already uses them (`워크스페이스`, `에이전트`,
`파일`); the product's own name and the app names that are brands stay in Latin script. The banned-noun
discipline of §4 applies in translation: a kernel noun does not come back as its Korean transliteration.

## 8. What this ADR does not decide

- **The marketing site in Korean** — indexed pages want `/ko/…` + `hreflang`, a different mechanism (D1).
- **Served strings** — 136 `HTTPException` details, the served roster, reach sentences. The convention is an
  error *code* the client words; that is its own pass.
- **Outbound email** — `account_email.py`, `notifications.py`.
- **The rest of the app.** This ADR ships the mechanism and the path a new member walks first; D4's ratchet
  carries the remainder. By measurement the next pass is the shell and the chat surface (115 lines, 15 files —
  what every session shows), then the per-app surfaces where the copy concentrates.
- **The stage notice** on the sign-up door stays English. It is one deliberately single-sourced sentence in
  `web/lib/metadata.ts`, shared with the marketing wordmark and `llms.txt`; a catalog copy would fork it.
- **Korean banned-noun patterns.** The guard scans `ko.json` with the English patterns only. A Korean pattern
  earns its place the way an English one does — with a string that shipped.

## 9. Receipts (2026-09-20)

- **Gate** `api/test_adr660_the_interface_speaks_korean.py` — **29/29**. Each arm proven RED by an in-place
  edit, restored in place: **17 falsifications, 0 stayed green**. The guard's catalog arm: RED on a banned noun
  in a `ko` VALUE, silent on the same word as a KEY. Voice guard 0 violations.
- **Build** — static routes **138 → 136**; left the set: exactly `/auth/login`, `/mcp/auth`; joined: none. Every
  marketing route still `○`. The server source-map invariants of `next.config.js` survived the extra webpack
  wrapper: 158 server maps, **0** carrying source text; 3134 trace references to `.js.map`, **0** dangling; 0
  client maps.
- **Negotiation, server-side** — no cookie: `ko-KR,ko;q=0.9` → Korean, `en-US` → English, `ja,fr` → English.
  `Set-Cookie: NEXT_LOCALE` across those responses: **0** (a guess is never written down).
- **Driven, signed out** (own headless Chrome, clean context) — choosing 한국어 re-renders, sets
  `<html lang="ko">`, writes the cookie; survives a reload and outranks an English browser; the ICU argument
  renders (`6자 이상이어야 해요`); `/mcp/auth` renders Korean; `/pricing` under a `ko` cookie stays English.
- **Driven, signed in** (the `bare-kernel` rig, three isolated contexts as three devices; account restored to
  `locale: null`, other metadata intact) — A: the choice lands on the account, `user_metadata.locale = "ko"`.
  B: a second device with **no cookie** renders Korean from the account alone. B switches to English and A
  follows on its next load. C: a cookie chosen while signed out is adopted into an account with no
  preference (`null → "ko"`).
- **Found by driving, fixed**: A followed the account to English while its own cookie still said `ko`, so
  signing out there would have greeted the member in the language they had just left.
- **Not mine, seen on the way**: `/favicon.ico` answers 500 under `next dev` — `app/favicon.ico` and
  `public/favicon.ico` have collided since January. The production build prerenders it.

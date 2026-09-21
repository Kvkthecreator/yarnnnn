# ADR-660 — The interface speaks Korean: a language is a member's preference, never a workspace's

> **Status**: **Accepted + Implemented — the mechanism, the sign-in path, and the shell** (2026-09-20, operator:
> *"consistent request to support korean language as an optionality … industry conventions, just fitting to our
> service specifics"*). D1–D6 shipped and driven (§9); the shell pass and its ruling on served titles in §10.
> **Coverage is DONE** (2026-09-21, §13). Every member-facing surface reads the catalog; what stays English
> is what the operator ruled stays English. §10 shell · §11 chat · §12 the account door · §13 the rest.
> **The marketing site speaks Korean at `/ko`** (2026-09-21, §14) — D9 refuses IP, D10 adds a fifth scope
> whose locale is an argument so every marketing route stays static.
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

- ~~**The marketing site in Korean**~~ — **CLOSED for the landing page by §14** (D9/D10): `/ko` +
  `hreflang`, IP refused. `/pricing`, `/how-it-works` and `/faq` are rostered and are the next pass;
  the blog and the legal pages stay English, each for a stated reason.
- **Served error details** — 136 `HTTPException` details, reach sentences. The convention is an
  error *code* the client words; that is its own pass. (The served *roster* left this list on 2026-09-20 —
  §10 ruling 1 words it client-side by slug, with no API change.)
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

---

## 10. The shell pass (2026-09-20)

**Ruling 1 (operator) — a served surface title is worded CLIENT-SIDE by slug.** The Launcher, the Dock, the
window title bar and the locator crumb all name apps from the composition fetch, whose titles are English
literals in `api/services/kernel_surfaces.py`. Rather than open the served-strings question §8 defers, the
shell looks up `surfaces.{slug}.title` and falls back to the served title when the key is absent. One
resolver, `useSurfaceWords` in `web/lib/compositor/useSurfaceTitle.ts`, wraps the existing
`surfaceTitleFor`; every consumer goes through it. No API change, and a program surface the kernel never
heard of still reads as whatever the compositor served.

Summaries come with the titles, because the Launcher **filters** on them: a Korean member typing `파일` has
to find Files. The filter matches the served English *and* the worded string, so neither language loses a
surface.

Three app names stay in Latin script — `Blogger`, `Supervisor`, `Reach`. They name things in the workspace,
not common nouns (`블로거` reads as a person who blogs), which is D6's brand-name rule; they are on the
gate's `UNTRANSLATED_OK` allowlist and nowhere else.

**Translated**: `UserMenu`, `Desktop`, `Launcher`, `chrome/TopBarSurface`, `AttentionCenter`,
`GlobalLocatorStrip`, `SurfaceViewport`. Two module-level label tables now hold catalog KEYS per D3 —
`KERNEL_TIER_GROUPS` (the Launcher's at-rest groups) and the Dock's context menu.

**Found by driving, not by the meter:**

- A workspace row's ROLE rendered a lowercase database enum (`owner`) made English by CSS `capitalize`.
  A member's role would have stayed Latin in every language. It is a catalog key now.
- `${n} ${n === 1 ? 'person' : 'people'}` — an English pluralization rule in a template literal. Korean has
  no plural form, so an ICU `plural` with one `other` arm is the honest shape.
- The meter saw none of the above, nor the Dock tooltips, nor four `title=` attributes on the theme toggle.
  It reads JSX text and copy props; a string built in a `useMemo` or a template literal is invisible to it.
  **The ratchet is a floor, and a pass has to read the file, not the meter.**
- `useIsFirstTime()` in `Desktop.tsx` has conditional early returns. A `useTranslations` placed there by a
  careless edit would have been a hooks-order violation; the hook belongs in the component that renders.

**Receipts**: gate **29/29**. Voice guard 0 violations. `npx tsc --noEmit` 0 errors. `npx next build`
succeeded with **136** prerendered routes (23 `○` + 113 SSG blog paths) — unchanged, every marketing route
still static. Driven on the `bare-kernel` rig, own headless Chrome, API on :8000:
`<html lang="ko">`; the Launcher lists 채팅 / 슬라이드 / Blogger / 이미지 / 텍스트 / Supervisor / 파일 /
에이전트 / Reach with Korean summaries; searching `파일` returns Files; the user menu reads `1명 (소유자)`,
`접근 권한 관리`, `결제`, `연결`, `의견 보내기`, `사용자 설정`, `로그아웃`; the bell popover and the
Desktop empty state are Korean; the locator strip reads `데스크톱`. The same rig at `locale: "en"` renders
`1 person (Owner)` — identical to the pre-pass string. Account restored to no `locale` key afterwards.

**Found while restoring**: `auth.admin.update_user_by_id` **merges** `user_metadata` — omitting a key does
not remove it. Clearing the rig's locale needed an explicit `{'locale': None}`; the first restore left
`locale: "en"` behind and read as clean.

**Next by measurement**: the chat surface (`ChatSurface` 24, `LanePanel` 21, `ConversationDetail` 15,
plus `toolLabels.ts`, which the meter cannot see), then `settings/page.tsx`, then Studio and billing.
`AttentionCenter` still borrows three shared label layers — `actorLine`, `proposalLabel`,
`proposalQueuedByDialLine` — that also feed the Notifications and Reach surfaces; they translate with
those surfaces, not ahead of them.

---

## 11. The chat surface (2026-09-20)

**Translated**: `ChatSurface`, `LanePanel`, `ConversationDetail`, `ConversationHeader`, `MentionMenu`,
`NewChatModal`, `ArtifactCard`, `StreamSteps`, and `toolLabels.ts` — what a running tool says it is doing.
**898 lines across 93 files** remain (972 → 898).

**`toolLabels.ts` is the D3 case at its largest.** 23 primitive verbs × up to three tenses, a module-level
table evaluated at import. It now names no words at all: it resolves a primitive to a catalog **key plus
args** (`ToolLabelRef`), and one hook — `useToolLabels` — words it, so the streaming steps and the settled
footer cannot drift into two spellings of the same verb. `withSubject` moved from a CONCATENATION
(`"reading" + path`) to a whole ICU message, because joining a verb to its object in that order is English
grammar, not a sentence: Korean puts the subject first (`{subject} 읽는 중`). `seedTargetNoun` in
`LanePanel` got the same treatment.

**⭐ The gate was green over work it could not see.** `USE`, the regex binding a `useTranslations(…)` call to
its namespace, matched a **double-quoted** namespace only. Every file translated in this session writes
`useTranslations('chat')` — the prevailing style under `components/` — so **17 of 22 bindings never bound**,
and the "every `t()` resolves" arm checked *none* of the ~200 keys in them. It was green when the shell pass
shipped, and it would have stayed green over a missing key rendering its own path in production. The regex
now accepts both quote styles, at the binding and at the call site; proven RED by breaking `t('signOut')` in
`UserMenu.tsx` **in place** and restored byte-identical. **A gate that reads source with a regex is only as
wide as its own syntax assumptions, and the assumption is invisible while everything it does read passes.**

The repaired arm immediately found a real defect it had been blind to: `chat.newChat` was both a string (the
button) and an object (the modal's namespace), so `t('newChat')` resolved to a node. Split into
`chat.newChat` and `chat.newChatModal`.

**Two arms added** for keys no scan can infer, both proven RED in place:
- every tool verb's messages exist in every catalog, both directions (a verb in code with no entry; an entry
  naming no verb; a `withSubject` the code will never ask for);
- every seed-target shape the composer can build is named.

**Found by the voice guard**, once the catalog arm could read the moved strings: `Pin lane` / `Unpin lane` —
a kernel noun in two `aria-label`s, carried forward unexamined from the old JSX. Now `Pin this chat`.

**Receipts**: gate **32/32** (29 + 3 new arms). Voice guard 0. `tsc` 0 errors. `next build` 136 prerendered
routes (23 static + 113 SSG), unchanged, marketing all static. Driven on the `bare-kernel` rig with the API
up and `LANES_ENABLED=1`: the chat list, the new-chat modal, an opened lane, the composer and the cast
detail all read Korean — `채팅은 에이전트 한 명과 나누고, 서로 분리돼 있어요`, `메시지를 입력해 보세요…`,
`이 대화에 2명`, `대화 전체를 읽어요` — with **0 page errors**. The same rig at `locale: "en"` renders the
pre-pass strings unchanged (`Write a message…`, `2 IN THIS CONVERSATION`, `Reads the whole conversation`).
Account restored to no `locale` key.

**Still English inside the chat surface, and why**: the lane's NAME (`_DEFAULT_LANE_NAME = "New chat"` in
`api/routes/lanes.py`) and the agent names and descriptions in the new-chat modal are SERVED — §8's open
question, the same class the shell's roster left by §10's ruling. `just now` / `2m ago` come from
`formatRelativeTime` in `lib/formatting.ts`, a shared layer reaching **15 surfaces**; it translates with a
pass of its own, not ahead of them.

**Next by measurement**: `app/(authenticated)/settings/page.tsx` (25), then `StudioDesignTab` (61),
`SubscriptionCard` (46), `ManageConnectionSubsurface` (38), `FindConnectorModal` (35),
`WorkspaceMembersCard` (32), `TextEditor` (31).

---

## 12. The account door (2026-09-20)

`app/(authenticated)/settings/page.tsx` — the Data & Privacy pane, both destructive confirms, and the
Notifications pane. **875 lines across 93 files** remain (898 → 875; the file itself 25 → 2, and those 2 are
the meter reading `link: (chunks) => (`).

A sentence carrying a **link** moved to `t.rich` with a `<link>` tag, not a concatenation: "it lives in
{link}" would have fixed the clause order, and the link sits mid-sentence in Korean
(`…워크스페이스 설정 → 위험 구역에 있어요`).

**⭐ The same arm was blind a second way.** After the quote-style repair of §11, the call-site regex still
required a bare `t(` — so `t.rich("…")`, `t.has("…")` and `t.raw("…")` were unchecked. A broken `t.rich` key
stayed green; proven by breaking one in place. The regex now accepts `t`, `t.rich`, `t.has`, `t.raw` and
`t.markup`, and both method forms were falsified RED in place and restored byte-identical. **Two blind spots
in one arm in one day: when a regex-backed gate is found narrow, look for the next narrowing before trusting
it again.**

**Receipts**: gate **32/32**. Voice guard 0. `tsc` 0. `next build` 136 prerendered, marketing all static.
Driven on the `bare-kernel` rig, Korean: the Notifications pane reads
`My workspace이(가) 회원님에게 알리는 방식이에요`, the in-app note renders its embedded link, and every dial
option is Korean (`중요한 것만` · `작업할 때마다` · `받지 않기` · `받기` · `언급될 때마다` · `항상 보내요`).
Both destructive confirms render fully in Korean with live counts (`워크스페이스 파일 38개`, `채팅 3개`) and
**both were cancelled, never confirmed**. 0 page errors.

**Named, not done — the shared confirm shell.** The confirm's Cancel button still reads English: it is
`FeedbackContext`'s own chrome, and `FeedbackProvider` mounts in **two** places — `AuthenticatedLayout`
(inside the scope) and `app/admin/layout.tsx` (outside it, since the console is not under
`(authenticated)`). Translating it as-is would throw at render on `/admin`, which is the `AuthForm` hazard
of §4 exactly. It needs its own decision — an `IntlScope` on the admin layout, or a locale-free shell — and
the gate's one-level import check does cover it, because `app/admin/layout.tsx` imports the context
directly.

Still served, so still §8: the notification kinds' labels and descriptions (the backend registry).

---

## 13. Full coverage (2026-09-21)

The operator asked for the whole scope rather than a half measure: *"it doesn't make sense to do half measure
translation (albeit, if some wording can remain english that is perfectly fine). i just mean we should
complete the scope itself."*

**2330 keys across 17 namespaces.** Seven surface groups converted in parallel, plus the shared layers below.
The meter reads **262 lines / 43 files** (from 875 / 93), and that number now means something different —
see *What the ceiling measures now*.

### D7 — a fourth scope, because a MOUNT decides where a scope is needed

`FeedbackContext`'s confirm shell (Cancel · Continue · Dismiss · the generic outcome lines) is member-facing
copy on every destructive flow in the app. `FeedbackProvider` mounts in `AuthenticatedLayout` **and** in
`app/admin/layout.tsx`, which is outside `(authenticated)`. Translating the shell as-is would have thrown at
render on `/admin` — the §4 `AuthForm` hazard exactly, one layer deeper. So `app/admin` gained the fourth
`IntlScope`: a server layout over a client `AdminShell`. The console's OWN chrome stays English (operator
ruling — it is a Hat-B instrument, outside the member-facing meter); the scope exists so the shared layer can
render. **A shared component's mounts decide where a scope is needed, never the route's own audience.**

Build receipt: **136 → 135** prerendered routes. `/admin` is the one that left, and it is `noindex` and
already resolved its viewer client-side. Every marketing route is still `○`.

### D8 — the entry routes stay English, and a gate holds the consequence

Four member-facing entry routes are outside every scope: `/invite/{token}`, `/s/{token}`, `/mcp/authorize`,
`/auth/callback`. Scoping them would have cost two more prerendered routes; **the operator ruled they stay
English.** The consequence is not obvious and had to be made mechanical: four components are reachable only
from them — `NewArtifactModal`, `WorkspacePicker`, `Working`, `BlogPostList`. A translation hook in any of
those ships a **runtime crash on a signed-out entry path that `tsc`, the build and every other arm pass
cleanly.** `SCOPELESS_BY_RULING` in the gate forbids the import; proven RED in place.

Their 36 metered lines are a **permanent floor**. If a later ruling scopes those routes, that set is the one
line to delete.

### The shared label layers — one implementation each

These were the real work, and none of them was visible to the meter:

- **`formatAuthorLabel`** (`lib/workspace/attribution.ts`) reaches **17 files**. Translating any one surface
  alone would have split the vocabulary — "나" on one row, "You" on the next. It returns a catalog key now;
  `useAuthorLabel` words it.
- **`resolveActorForViewer`** sliced the rendered English label at the literal `"(via"` to rebuild
  "You via GPT-4o mini". In Korean that produced a name with **no transport at all**. The transport is an ICU
  argument of one whole message now.
- **`toolLabels.ts`** (§11), **`proposal-labels.ts`**, **`timeline-rows.tsx`**, **`StandingRow`**'s schedule
  words, **`legibilityDescriptor`**, and **`conflict.ts`** — all module-level, all now key-returning or hooks.
- **`structureLabels.ts`** is the interesting one: it is the ONE label ladder, called from panes *and*
  serialised into the sandboxed canvas runtime by `labelForJS`. The runtime cannot read a catalog — a key
  baked into the iframe would render as `roles.body` on the member's canvas. So the WORDS ride the same
  global channel `__yarnnnBlockLabels` and `__yarnnnFrameNoun` already use (ADR-544 D4 / ADR-633 D3),
  resolved once at the injection site. One derivation, injected.

### ⭐ Three defect classes no existing arm could see

1. **`\w` matches Hangul in Python.** `{count, plural, other {다른 멤버 #명}}` read `다른` as a second ICU
   argument, so a *correct* Korean plural registered as argument drift against its English twin. Two agents
   had already contorted their Korean word order around it before it was found. `ICU_ARG` anchors on a real
   argument now (ASCII identifier followed by `}` or `,`); genuine drift still fails in both directions.
2. **English sentences carrying Korean counters.** A pass that writes one plural arm and uses it for both
   locales shipped "2개 of the tools…" and "5명 · 3석 billed" — 25 of them. Argument parity cannot see it: the
   arguments are identical, the TEXT is in the wrong language. New arm: no Hangul in an English value.
3. **English plurals that lost their `one` arm** — the inverse, and it shipped: **"1 people"**, rendered on
   the Workspace Members pane and found by DRIVING it, not by reading. Korean has no plural form and takes
   `other` alone; copying that shape to English breaks every singular. 13 of them. New arm holds the default
   locale only.

All three arms were falsified in place and restored byte-identical.

### The voice guard finally reads the copy

Moving strings into the catalogs put them where `test_voice_no_kernel_nouns_in_copy.py` can read them, and it
immediately found **27 violations** that had been invisible inside JSX: `artifact` (11 of them — a kernel
noun on the Studio surface), `lane`, `commons`, `principals`, `attributed`, `re-scaffolded`, `no-op`, and an
**ADR reference in member copy** (`"Markdown export arrives with the interchange wave (ADR-456 W4)"`). All 27
were reworded in both languages rather than allowlisted. The allowlist did not grow: its two `Freddie`
entries were re-keyed from the old call sites to the catalog keys they became.

### What the ceiling measures now

**226 of the remaining 262 lines are false positives** inside fully-translated files: the meter marks
JSX-text continuation lines, and Prettier wraps a long `t('…', { … })` call across several, so it counts JS
identifiers and date-format options as prose. Reflowing real code to satisfy a meter would be the tail
wagging the dog. The other **36** are D8's floor. So coverage is done, and `LITERAL_COPY_CEILING` now guards
against NEW literal copy rather than measuring remaining work.

### Receipts

- **ADR-660 gate 36/36** (29 → 36; seven arms added across §10–§13, each falsified in place).
- **Voice guard 0 violations**, allowlist unchanged in size.
- **`tsc` 0 errors**; **`next build`** clean, **135** prerendered, every marketing route static.
- **198 gates that read `web/` source, re-run against a stashed baseline: ZERO regressions.** ADR-571 was the
  one gate this pass broke (286 → 274; it asserts Text-app copy as English source literals) and it is back at
  **286/288**, its two remaining failures pre-existing and untouched. Its checks are keyed on catalog keys
  now, which is language-independent and stronger than the literal match; its node probes mount the real
  `NextIntlClientProvider` with the shipped English catalog, because rendering a translated component bare is
  testing a shape production never has.
- **Driven in Korean** on the `bare-kernel` rig across Files, Agents, Reach, Supervisor, Notifications,
  Workspace settings, Text and Studio — every surface renders Korean, 0 page errors. The same rig at
  `locale: "en"` renders correct English on all eight. Account restored to no `locale` key.

### Still English, by ruling or by rule

The four scopeless components and their entry routes (D8). The `/admin` console chrome. Every **served**
string, which §8 still defers: surface titles beyond the shell's slug map, agent names and blurbs, the
notification-kind registry, connector titles, `HTTPException` details, the lane's default name, revision
messages (substrate data, ADR-209), and `blockLabels` (the served block vocabulary, ADR-544 D4). Brand and
app names in Latin script per D6. `lib/formatting.ts`'s relative times, which are a shared layer on 15
surfaces and translate with their own pass.

---

## 14. The marketing site (2026-09-21)

§8 deferred `/ko` + `hreflang` as "a different mechanism (D1)". This ships that mechanism for the
landing page. Occasion: the operator asked whether the visitor's **IP** could pick the language, or
failing that a header toggle. Analysis: `docs/analysis/korean-marketing-site-2026-09-21.md`.

### D9 — IP is refused; the language is the ADDRESS

**IP geolocation is rejected**, on three independent grounds, any one sufficient:

1. **It breaks the SEO the marketing site exists for.** Googlebot crawls predominantly from US IPs,
   so serving two languages at one URL means Google indexes English and never discovers the Korean
   page — removing the only reason to write it.
2. **Location is not language.** Diaspora, expats and English-preferring Koreans all get a language
   they did not ask for. `Accept-Language` carries what the visitor *configured*; it is a
   declaration, not an inference, and it is already negotiated (D2 step 3, driven in §9).
3. **D2 already ruled it.** A guess is never written down. An IP guess is a weaker guess than the
   one the request already carries.

So English stays **unprefixed** at `/` and Korean lives at **`/ko`**. English URLs do not move: no
redirect is introduced, and no existing ranking is disturbed. This is D1's other half — D1 excluded
the *app* from prefixes and said in the same breath that *"URL-prefixed locales are the convention
for indexed pages"*. `lib/marketing/locale.ts` encodes the asymmetry once, and `TRANSLATED_PATHS` is
the single roster deciding which paths may be prefixed; a link to an English-only page (the blog,
the legal pages, `/invest`, `/developers`) stays bare rather than 404ing under `/ko`.

### D10 — a FIFTH scope, whose locale is an argument and not a lookup

The four D3/D7 scopes resolve a locale by reading a cookie and the account. **That read is what makes
a route dynamic**, and it is why the provider was kept out of the root layout. Marketing cannot pay
it: every marketing route is statically prerendered, an invariant this ADR guarded on the build's
route table four times.

So `MarketingIntlScope` takes `locale` as a **prop** — the route already knows it, because the locale
is in the path — and imports the catalog directly rather than through `getMessages()`.

⭐ **The static guarantee nearly died, and a build receipt caught it.** A first pass rendered the
provider in a server component and `/` fell from `○` to `ƒ`. Isolated by bisecting down to a bare
page: `NextIntlClientProvider` asks the request config for `now`/`timeZone`, and a server-side
`useTranslations` reads it too. Both are avoided — `now`/`timeZone` are pinned explicitly and the
page body renders as a **client** component — so no request state is consulted at all. The gate now
asserts each of those three properties rather than the outcome alone.

### ⭐ The D8 hazard, reached through an embed

`TraceCard` and `CompoundsStepper` are rendered **inside blog posts** via `lib/blog-embeds.tsx`
(`<!-- embed:TraceCard -->`, 2 posts). The blog stays English by ruling and renders outside every
scope, so converting those two to `useTranslations` **broke the prerender of both posts while `tsc`,
the type check and every other arm stayed clean** — D8's failure shape, arriving through an indirection
no reading of the landing page would surface. They take **words as a prop** with English defaults now,
which is what `LandingHeader` and `LandingFooter` already do for the same reason: shared chrome renders
on untranslated marketing pages too.

Two more found only by driving: `MarketingLanguageToggle` was a server component imported by a client
one (the whole chrome failed to prerender), and `/ko`'s title read `… | yarnnn | yarnnn` because a
nested route inherits the root layout's `title.template` while the root page does not.

### The toggle is a link, not a switch

`components/i18n/LanguageSwitcher.tsx` stays as it is — signed in, a language is a property of the
human (D2), so it writes the account and refreshes. On marketing the language is the address, so
`MarketingLanguageToggle` renders two anchors: no client state, a crawler follows it to the Korean
page, and it cannot record a guess as a choice.

### Scope — phase 1 is the decision path

Translated: the landing page and the shared chrome. **Deliberately NOT translated**, each for a reason:
the blog (113 posts — translating a post is a content project, and a machine-drafted post is published
prose), `/privacy` and `/terms` (legal text; a mistranslated clause is a liability, so these want a
professional translation or nothing), `/invest` and `/developers` (those audiences read English).
`/pricing`, `/how-it-works` and `/faq` are in `TRANSLATED_PATHS` and are the next pass.

### Receipts

- **Build**: **24 static routes** (23 baseline + `/ko`); every pre-existing marketing route still `○`;
  `/blog/[slug]` still 113 SSG paths; **0 prerender errors**.
- **Gate 41 checks** (36 → 41): five arms for the fifth scope — it takes its locale as an argument and
  never calls `resolveLocale`/`getLocale`, it pins `now` and `timeZone`, both pages provide it, and the
  shared chrome imports no `next-intl`.
- **Voice guard 0**, allowlist unchanged — it found `principal` and `attributed` in copy that JSX had
  hidden and the catalog exposed (the §13 effect again); both reworded in both languages.
- **`tsc` 0**. Driven at 390px in both languages: 0 clipped Hangul nodes, no horizontal scroll;
  `/ko` carries `hreflang` en/ko/x-default, a self-canonical, and `og:locale: ko_KR`.
- Known RED, not ours: the literal-copy ceiling (268 > 262), measured identically in a clean worktree
  at HEAD — another session's, and this pass's delta is zero.

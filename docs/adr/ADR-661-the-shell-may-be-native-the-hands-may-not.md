# ADR-661 — A native shell, and the local hands it may grow

> **Status**: **Accepted** (2026-09-21, operator-ratified). **Phase 0 (this document) only**; no code rides it beyond one dependency cleanup (§7). The Mac shell is **scoped and authorized in principle**. **Local attended computer use is IN SCOPE as a downstream capability** — §5 rules the distinction that makes it canon-coherent, §6 states the four conditions it must meet at birth, and §8 orders the build so the shell accommodates it rather than having to be reopened for it.
> **Date**: 2026-09-21
> **Authors**: KVK (operator) + Claude (collaborator)
> **Dimensional classification** (Axiom 0): **Channel** (Axiom 6 — the client is a form of addressed surface, and §5 adds a *local* channel that is not a boundary crossing) + **Identity** (Axiom 2 — the whole of §5 is who acts and who the far side sees). **No authority change**: the credential chokepoint, the grant model and the kernel are untouched.
>
> **Origin**: the operator's question, asked from a Claude desktop session whose own transcript ended *"Want me to type it into the Outlook reply window?"* — *"how difficult would it be to make yarnnn a desktop app for mac? … and, thus, could we have computer use on that if we chose to do so?"*
>
> **The operator's correction, which this ADR encodes** (2026-09-21, mid-draft): *"forgo prior concepts that prevent computer use. given that computer use for a localized app is not necessarily the same thing as the separate sandbox compute like approach, we should scope that in full, or at least approach the build to accommodate that downstream."* A first draft of this ADR declined computer use by reading it as a reach mechanism. **That reading collapsed two different things** — §5.1 records the distinction and why the first draft was wrong.

**Preserves** (load-bearing, untouched):
- **ADR-645 D1/D2** — the credential is a human's; model (A) — a workspace adopting a member's token — stays CLOSED; no workspace credential store. §5.2 shows local attended hands are **(B)**, not (A).
- **ADR-577 §7** — the re-entry test: a driven trace, never a gate and never a docstring. §6 inherits it verbatim.
- **ADR-209 D1** — the three write-path invariants; `write_revision()` stays the single write path with no escape hatch. §6.2 is how a local act satisfies it.
- **ADR-639 / ADR-615** — the unattended derive turn is **toolless by construction**. §6.1 keeps it that way: local hands are attended-only, forever.
- **ADR-642** — the boundary's three reach mechanisms stay the closed set. §5.3 argues a local act is **not a boundary crossing at all**, so it adds no fourth.
- **ADR-222 / ADR-407 D2** — the kernel boundary, and "one filesystem and N shells".
- **ADR-308** — a redirect stub is pure server transport. §7.3 explains why the shell omits stubs rather than converting them.

**Amends**: nothing. **Supersedes**: nothing.

---

## 1. Why this ADR

Two questions arrived as one, joined by the word *thus*: can yarnnn be a Mac app, and *thus* can it have computer use?

They are genuinely separable — packaging is a Channel question about the form of a client; computer use is an Identity question about who acts. But they are not **opposed**, which is what a first draft of this ADR got wrong. The correct relationship is narrower and more useful: **the native shell is the only place local hands could ever live**, so the shell's design must not foreclose them.

This ADR rules both, in that order.

---

## 2. The shell is not assumed to be a browser

Canon was searched for a statement binding the client to a browser. **There is none**, and the evidence runs the other way:

- **ADR-407 D2**: *"the workspace has one filesystem and N shells"* — a shell instance is member-experience scope. A Mac shell is **another shell instance**, exactly what D2 licenses.
- **ADR-297's axiom** decouples surface identity from the URL; **ADR-308** enforces that the URL must not decide whether the shell engages.
- The product **already calls its web UI a desktop shell** — ADR-435:17, ADR-375:50 (*"the macOS-desktop shell"*). `HOME_ROUTE` is `/desktop`.
- `browser` in `docs/design/WORKSPACE.md` means **file browser**, modeled on Finder, in every occurrence.

And there is latent demand. ADR-649:55 and `design/WORKSPACE.md`:217 record a defect and its workaround:

> *"Finder can do that because **a menu bar stands behind the gesture** (File → New Folder); **this shell has no menu bar**, so the gesture alone left a new member with no door."*

Canon has already hit, and routed around, a limitation a native shell removes.

**D1 — A native shell is a permitted client form.** A shell instance under ADR-407 D2, carrying no new authority and no kernel change. Packaging is not an architectural act.

---

## 3. The code is already shaped for it

Driven against `5fa373f`, receipts in `web/`:

- **43 pages under `app/(authenticated)/`; 29 are ADR-308 redirect stubs**; the rest are `'use client'`. **Zero real server pages.**
- **Zero Server Actions, zero `server-only`, zero route handlers under `(authenticated)`, zero `next/font`, no `next/image` in the authenticated tree, zero relative fetches.**
- **The API is a pure bearer service** — `get_user_client(authorization, X-Workspace-Id)` at `api/services/supabase.py:696`. No cookie, no origin dependency.
- **The auth flow is already client-side** — PKCE and `token_hash` branches all in `app/auth/callback/page.tsx`.

**Two server couplings, both in `app/(authenticated)/layout.tsx`**: `getRequestUser()` (used only for `userEmail`) and `IntlScope` (async server component reaching `next/headers` via `i18n/resolve.ts:2`).

**D2 — The port is a client-form change.** No API change, no schema change, no primitive change, no new env var on any Render service.

**D4 — One codebase, N build targets.** The desktop shell is a **build target of `web/`**, never a fork and never a second component tree: one component tree, one app registry, one surface roster, one copy catalog, with a host directory (`src-tauri/`) beside it and a second build script. This is the industry-default shape for this class of app — a web product with a thin native host — and the reason to name it as a ruling rather than leave it to taste is drift: a second tree is how a hand-kept list diverges from a derived truth, which is ADR-592's failure class (*"a hand-kept list beside a derived truth drifts, and the drift reads as success"*). A platform difference is expressed as a **capability seam the host fills**, never as a branch in a surface.

---

## 4. What the shell costs

Four real items; the first estimate in the originating discourse understated them.

**4.1 A mount-time auth gate must be BUILT, not inherited.** `components/shell/AuthenticatedLayout.tsx:59-63` says in its own words that the `onAuthStateChange` listener is *"Live sign-out invalidation only — NOT an auth gate."* It fires after mount and paint — the exact 2026-08-20 defect recorded at `lib/supabase/middleware.ts:30-43`, where eight surfaces served a full 200 to logged-out visitors. A shell with no middleware must not re-open it.

**4.1a The session is stored in a COOKIE, which the shell will not have.** Found while driving step 1 (2026-09-21). `lib/supabase/client.ts` uses `createClientComponentClient` from `@supabase/auth-helpers-nextjs`, and that library persists the session as `sb-{ref}-auth-token` **in `document.cookie`** — verified by probing a live page's storage (localStorage held nothing; the auth-helpers-shared bundle writes `document.cookie` directly). A cookie is a browser-origin concept: under a custom scheme there is no origin to scope it to, and the packaged shell must move the session to a token store (`autoRefreshToken` against Tauri secure storage). ⭐ **This is the one place the port is a security change rather than plumbing**, because today the cookie is ALSO rotated server-side by `updateSession` on every request, and a token store has no equivalent. It does not affect `AuthGate`, which asks `getSession()` and does not care where the answer is kept — that indifference is why the gate ports unchanged.

**4.2 The locale chain is server-only by construction.** `i18n/resolve.ts` reads `cookies()` and `headers()`; steps 2–3 of ADR-660 D2's chain have **no source** without a request, so a naive static shell falls silently to English. Catalogs are plain JSON (366KB) and bundle fine; `LocaleEffects` is already client-side.

**4.3 Seven external navigations would trap a member in a native window** — four OAuth handoffs (`ManageConnectionSubsurface.tsx:311`, `FindConnectorModal.tsx:303,347,400`) and three Stripe jumps (`useSubscription.ts:100,119,137`). Each must become a system-browser open.

**4.4 Share links would be minted dead** — four sites build URLs from `window.location.origin` (`StudioSurface.tsx:2327,3561,4835`, `TextEditor.tsx:725`). **A share link is a web address even when the shell is not.**

Secondary: the `/api/feed-proxy` same-origin retry (`chatTransport.ts:6,29-38`) dies silently; `next.config.js:39-53`'s six redirects are dropped by `output: 'export'`; Sentry and Vercel Analytics are Vercel-coupled.

---

## 5. Local hands are a different thing from a sandbox — D3

### 5.1 The distinction the first draft collapsed

A first draft declined computer use outright, reading it as a fourth reach mechanism and applying ADR-645 D1's identity argument to it. **That conflated two mechanisms that differ on every axis that the governing rulings actually turn on:**

| | **Remote sandbox** (ADR-395 am.1 §8.7, declined there) | **Local attended hands** (this ADR) |
|---|---|---|
| Where code runs | A third party's VM, a named jurisdiction | The member's own Mac, in front of them |
| Whose bytes | Member bytes **leave Supabase** for a vendor | Nothing leaves the machine it is already on |
| Execution boundary | **A new one** — the kernel has none | The member's own OS, which already grants it |
| Who is present | Nobody — that is the point of it | **The member, by construction** |
| Data residency | Becomes a stated property with a second sentence | Unchanged |
| Render parity | A fourth execution home, outside Render | None — no service, no deploy |

§8.7's five costs were reasons against **the sandbox**. Four of the five — new execution boundary, Render parity, data residency, sandbox output as untrusted input — **do not apply to a local attended act at all**. The fifth (attribution must survive) does apply, and §6.2 is how it is met.

**The trigger has also fired.** §8.7's named trigger is *"a member asking, more than once, for something that needs execution."* The Outlook sentence is that ask, and it is not the first of its kind. The operator has now asked directly. That is the trigger doing its job.

### 5.2 Local attended hands are model (B), not model (A)

This is the ruling that makes the capability canon-coherent, and it was already written. ADR-645 D1, immediately after the chokepoint table:

> *"A member's chat **lane** stamps `member:{id} via {model}` and **IS the member's hands** — so an AI driving a member's lane correctly reaches through *that member's* connection. **This is not an exception to (B); it is (B).**"*

What D1 forbids is model (A): *"the owner's Slack silently backs everyone else's actions"* — a workspace adopting one human's credential so that **other principals** act as them, unattended and invisibly. Every word of that fails to describe a member sitting at their own Mac watching an agent draft a reply in their own Outlook:

- It is **not silent** — the member is present and watching.
- It backs **nobody else's** actions — one principal, their own machine, their own session.
- It adopts **no credential** — there is nothing to mirror, no token in a second place with a second expiry. `resolve_platform_credential` is not routed around because it is never on the path.

The far side does see the member — and **correctly**, because the member is the one acting, through an instrument, in their own presence. That is what `member:{user_id} via {model}` (`api/services/lane_runner.py:1065`) already means. The attribution shape needs no extension.

### 5.3 It is not a boundary crossing, so it adds no fourth mechanism

ADR-642's three mechanisms — intake, turn reach, outbound — are all **workspace boundary** crossings: something enters or leaves the commons. A local act on the member's own desktop crosses no such boundary; it never touches the commons at all unless it comes back as a write, and if it does, it comes back through `write_revision()` like everything else.

ADR-642's strategic read stands and is not contradicted:

> *"the frontier labs' agents are becoming the hands on existing software … yarnnn cannot out-shell a lab's shell; what no lab can offer neutrally is the kernel — the attributed, multi-principal record of what crossed."*

**We are not out-shelling anyone.** We are not building a general agentic desktop. We are letting the member's own attended lane finish a job on their own machine — and then **recording it in the kernel**, which is the part no lab offers. Local hands without the record would be out-shelling; local hands *with* the record is the moat applied one surface further out.

### 5.4 ADR-413 D5 is the door, and it names this exact case

> *"**The stateful-session driver (browser/computer use) follows the same rule, later.**"*

The rule: its own ADR, carrying the D1 invocation contract at birth. ⚠️ **A correction any future reader needs**: D5 grounds this by saying it extends *"the render service's existing seam"* — and **ADR-417 deleted that service two days later**, saying so in its Amends line. So D5's mechanism is gone but its **rule** survives intact, and this ADR is the "own ADR" D5 demands. §6 is the contract carried at birth.

**D3 — Local attended computer use is in scope as a downstream capability of the native shell**, subject to §6. It is distinguished from the remote sandbox, which stays declined under ADR-395 am.1 §8.7 on its own separate reasoning.

---

## 6. The four conditions, binding at birth

Any implementation must satisfy all four. They are not staging advice; they are the contract ADR-413 D5 requires, and a proposal missing any one of them is refused.

**6.1 Attended only, and unattended-impossible by construction.** A local act requires a member present in a lane. The unattended path (`run_bounded_derive_turn`) is **toolless by construction** (ADR-615, ADR-639, `api/services/derive_turn.py:91-97` passes no `tools=`), and this capability must never be reachable from it. ADR-615 states the property exactly: *"deleting the toolless construction would [open it], which is why the gate asserts that construction directly."* **A clock plus hands is the combination this forbids** — the same shape as a clock plus a credential.

**6.2 Every act leaves a receipt, and the receipt is the point.** ADR-209 D1's invariants have no escape hatch, and Axiom 9 Clause B is absolute — *every invocation emits an entry*. So:
- Each local act emits a **narrative entry** attributed `member:{user_id} via {model}`, with what was done in plain words.
- Anything durable comes back through **`write_revision()`** as an attributed revision, never as a side effect that exists only on the far side.
- An act whose effect the product cannot describe afterwards is **not permitted to run**. DP12: *"an action without a visible channel is a trust leak."*

This is the condition that distinguishes what we would build from what a lab ships. **A lab's agent clicks; ours clicks and signs.**

**6.3 The member sees it happen and can stop it.** Local hands run visibly — in front of the member, interruptible, never behind a window they are not looking at. ADR-642 D3's rule applies unchanged: *"a stage with neither a receipt nor a refusal is served as unresolved, never as fine."*

**6.4 The re-entry test binds.** ADR-577 §7, inherited verbatim: before this capability may claim it acts correctly, it must exhibit **a driven trace** — a real act, through the real path, producing the real receipt — **not a passing gate and not a docstring**. ADR-645 D2 restates it. This is the standard the credential claim failed for four months while reading as live.

---

## 7. What this ADR does NOT do

**7.1 It does not adopt the remote sandbox.** ADR-395 am.1 §8.7's decline stands on its own reasoning, which §5.1 shows is largely inapplicable to the local case and wholly applicable to the remote one. Two different mechanisms, two different rulings.

**7.2 It does not fork the product.** One codebase, one app registry, one surface roster. The shell is a packaging target of the same client. A second client is how a hand-kept list drifts from a derived truth (ADR-592's failure class).

**7.3 It omits redirect stubs rather than converting them.** ADR-308 forbids the naive conversion — a `'use client'` stub redirecting in `useEffect` *"paints one orphaned frame inside the OS shell (no Desktop, dead dock)"*. But `lib/routes.ts:41-45` gives their purpose: bookmark and deep-link continuity, removable when *"no inbound external links to the route are known."* **A desktop app has no inherited bookmarks.** The stubs stay on the web build; the shell ships live surfaces only.

**7.4 It does not widen reach, authority or scheduling.** No new grant shape, no credential change, no fourth Render service. §6.1 keeps the unattended path exactly as toolless as it is today.

**7.5 It does not build anything yet.** One cleanup landed with this document: `@supabase/ssr` and `@supabase/auth-helpers-react` were declared dependencies with **zero source imports**, removed from `web/package.json`. `@supabase/ssr` is precisely what a desktop port would reach for; declared-but-unused is the ambiguity this ADR exists to prevent.

**7.6 It does not design against Windows — and does not design for it either.** The shell ships macOS first because that is where the operator and the first members are, not because the client assumes a platform. Audited at `67dda80`, it does not:

- **Zero runtime platform detection.** No `navigator.platform`, no `userAgent` branching anywhere in `web/`. There is nothing to unwind.
- **Every key handler is already cross-platform.** The house idiom is `e.metaKey || e.ctrlKey` — Cmd and Ctrl accepted identically — in `projection.ts`, `TextEditor.tsx`, `PagedNavigator.tsx`, `AuthenticatedLayout.tsx` and `SurfaceLink.tsx`. **This is the rule, and it stays the rule**: a handler never branches on the platform.
- **macOS is vocabulary, not binding.** Dock, zoom, minimize, Finder (ADR-297 D19.1/D19.3, `surface-preferences.ts`) are design metaphors in comments and docs. They constrain no runtime behaviour.

The one exception was **copy**, and it was a live web defect rather than a desktop one: three strings hardcoded `⌘` in both catalogs, so a Windows member on yarnnn.com read a key their keyboard does not have. Fixed in `26a7360` — `lib/shell/modifier-key.ts` is the ONE place the product decides which glyph to print, passed to the catalogs as the `mod` ICU argument so word order stays theirs (ADR-660). ⭐ **The separator belongs to the key name, not the catalog**: Apple prints `⌘Z` closed up, Windows prints `Ctrl+Z`, so a bare `Ctrl` against `"{mod}Z"` renders `CtrlZ`. That was the first cut, and **tsc was clean across it** — it was caught by rendering all twelve arms through the real ICU formatter.

**Windows is therefore a build-target question, not an architecture question**, and it stays out of scope until there is a member asking. Both Tauri and Electron cross-compile; the port is days *provided no Mac-only assumption accumulates*, which §9's arm now enforces. ⚠️ **The exception is local hands (§5).** Screen capture and synthetic input are the most platform-divergent APIs in the OS — ScreenCaptureKit and its permission model have no Windows equivalent. That implementation ADR scopes **one platform at a time** and says which; it does not get to assume the second is free.

---

## 7a. The export spike — driven, not read (2026-09-21, `96c5d99`)

Everything in §3 and §4 was established by reading. Before authorizing
implementation the operator asked for a final pass, so `output: 'export'` was
actually switched on and `next build` run to exhaustion, peeling one blocker at
a time. **The spike was thrown away; only its findings are kept.** It changed
the plan in one material way.

**Blocker 1 — a route handler with `force-dynamic` fails the build outright.**
`app/api/feed-proxy/route.ts` (`dynamic = "force-dynamic"`) is a hard error
under export, not a warning. The six marketing/SEO handlers (`llms.txt`,
`openapi.json`, `rss.xml`, `.well-known/mcp.json`, `/s/[token]/txt`) are the
same class. **Confirms §7.3's shape**: the shell ships the authenticated group
only, and these stay on the web build.

**Blocker 2 — a dynamic segment without `generateStaticParams` fails.**
`/integrations/[provider]`, `/agents/[id]`, `/invite/[token]`. All three are
legacy-link compatibility stubs, so §7.3's ruling (omit, don't convert) resolves
them — but the build **stops**, it does not warn.

**Blocker 3 — 41 routes fail on `cookies`, from one file.** Every authenticated
route errored with *"couldn't be rendered statically because it used `cookies`"*.
Patching only `app/(authenticated)/layout.tsx` — dropping `getRequestUser()` and
swapping `IntlScope` for a client provider — **collapsed all 41 at once**. This
is §4.1 + §4.2 confirmed from the build rather than from reading, and it is the
whole of the server coupling: two calls in one file, 41 routes downstream.

**Blocker 4 — the one the audit got wrong, and the reason this spike earned its
cost.** With the layout patched, **12 prerender failures remained**:

> `⨯ useSearchParams() should be wrapped in a suspense boundary at page "/chat"`

…and the same for `/files`, `/settings`, `/supervisor`, `/text`, `/slides`,
`/images`, `/notifications` — **the product's most-used surfaces.** The audit
had reported `useSearchParams` as *"works fine under static export"* because its
consumers are wrapped in `<Suspense>` "where required". Under `output: export`
the requirement is **stricter**: the boundary must exist at the **page**, and on
these pages it does not — the hook is reached through a child, and
`grep -c Suspense` on each page returns 0.

⭐⭐⭐ **A hook that is Suspense-wrapped for SSR is not Suspense-wrapped for
export.** Reading found the hook and the wrapper and concluded correctly for the
wrong build mode. Only running the target build asks the right question.

**What this changes.** Step 3 of §8 gains a member: a page-level Suspense
boundary on each of the eight surfaces. It is small and mechanical — and it is
an improvement to the **web** build too (the same bailout costs client-side
rendering on a slow first paint today) — but it was invisible to every static
check, and it would have surfaced on the first day of implementation as eight
broken surfaces rather than as a listed task.

**§7a.1 — the fix, and what it taught (2026-09-21, step 3 driven).** Eight pages got a shared `SurfaceBoundary` (one component, not eight hand-written fallbacks — `Working` is already "the ONE way to say wait", ADR-651, and eight bespoke ones drift). Three of them (`files`, `settings`, `notifications`) call the hook in the page component itself, so the boundary had to go OUTSIDE it: the body was renamed `…Body` and a thin default export wraps it. **A boundary inside the component is reached only after the hook has already run.**

⭐⭐⭐ **The first attempt made it WORSE — 12 failures became 40.** `AuthGate` (§8 step 1, landed hours earlier) called `useSearchParams` for the bounce URL, and it sits ABOVE every page, so it demanded a boundary on all 41 authenticated routes. **A hook in a layout is a hook on every route beneath it.** The gate now reads `window.location.search` inside its effect — the same question without the opt-in, since an effect only runs in the browser. Re-run: **0 suspense failures**, and the export's only remaining prerender errors are `/orchestrator` and `/team` (the two `searchParams` stubs §7.3 omits) plus `/admin` (outside the shell by design).

**Not blockers, confirmed**: the six `next.config.js` redirects and the one
rewrite warn (`"will not automatically work"`) rather than fail, so they degrade
rather than break; Sentry emits deprecation warnings only; nothing in the
authenticated tree needs `next/image` or `next/font` work.

---

## 7b. Step 4 — the shell exists (2026-09-21, driven)

**A `.app` was built and run.** Rust 1.98.1 → `cargo tauri build` → `yarnnn.app`, 15MB, launched, stable at 102MB RSS with live WebKit content processes.

**The mechanism: one tree, two builds, selected by file extension.** `YARNNN_SHELL=1` switches `next.config.js` to `output: 'export'`. Which routes exist in which build is declared through `pageExtensions`: the WEB build lists `web.tsx`/`web.ts` as route extensions, the shell build does not, so a file named `page.web.tsx` is a route on the web and invisible to the shell. Nothing is copied, moved or deleted per target — **D4 satisfied by construction**, and the web build's route table is byte-identical through the whole change (28 static / 52 dynamic, before and after).

⚠️ **Verified by building, not assumed.** The first cut had the direction backwards — it gave the SHELL the extra extension — and a `page.web.tsx` probe was then invisible to **both** builds: a route that silently does not exist anywhere. Next matches a route file as `page.<ext>` EXACTLY.

**What the shell excludes, and why each is right** (§7.3): the six marketing/SEO route handlers · the three legacy dynamic stubs · `/orchestrator` and `/team` (the two `searchParams` stubs) · `/admin` (Hat B) · `/mcp/auth` + `/mcp/authorize` (a browser OAuth flow for third-party clients) · the whole marketing surface. The shell's `/` is a redirect stub to `HOME_ROUTE`, because a member who opened the app has already arrived.

**The layout pair.** `layout.web.tsx` (web) and `layout.tsx` (shell) differ in exactly two things, both forced by the absence of a request: no `getRequestUser()` (a `cookies()` read that made all 41 authenticated routes un-exportable — patching this ONE file cleared all 41 at once), and `ShellIntlScope` instead of `IntlScope`. The shell scope runs the same ADR-660 D2 chain from `resolveLocaleClient` (§8 step 2) with both catalogs bundled.

**The session moves stores** (§4.1a). `lib/supabase/client.ts` branches once: the web keeps `createClientComponentClient` (cookie, rotated server-side by `updateSession` — unchanged), the shell uses plain supabase-js over `localStorage` with `autoRefreshToken`. `AuthGate` is indifferent — it asks `getSession()` — which is why the gate ported unchanged and the seam is a two-line branch.

**The proof it works end to end.** Run against a dev server so the requests are observable:

```
GET /                                   307   ← the shell root redirect fired
GET /desktop/                           200   ← the authenticated boot route
GET /auth/login/?next=%2Fdesktop%2F     200   ← AuthGate ran IN THE NATIVE WINDOW,
                                                found no session, bounced with ?next=
```

Steps 1, 2 and 4 in one trace, inside the packaged app.

**The installer.** `cargo tauri build` produces `yarnnn_0.1.0_aarch64.dmg` — **7.8MB**, `hdiutil verify` VALID, mounting to the standard drag-to-install layout (`yarnnn.app` beside an `Applications` symlink, with a volume icon). Driven: mounted, copied to a fresh location, unmounted, launched from the copy — it runs at 107MB RSS with a live WebKit content process. ⚠️ The DMG step failed on the FIRST attempt and succeeded unchanged on the second; `bundle_dmg.sh` drives Finder through AppleScript, which is timing-sensitive under load. **A DMG failure is worth one retry before it is a finding** — the first read of it as "needs Finder scripting, unavailable here" was wrong.

**Owed, and not done here**: notarization and auto-update are step 5 (they need an Apple Developer ID); the OAuth deep-link back into the app is not wired, so sign-in currently completes in the system browser and does not hand back.

---

## 7c. Step 5 — the return leg, and a publishable build (2026-09-21, driven)

**The deep link closes the loop.** §4.3 sends OAuth to the system browser, which is right; without a way back it is one-way, and the shell could only ever use a session already in its store. The host registers `yarnnn://`, forwards an incoming URL as an app-wide event, and `DeepLinkBridge` converts it to in-app navigation. It parses no token and touches no Supabase client: `app/auth/callback` already handles every shape the provider sends, earned against production, and must keep exactly one home.

Driven, against a logging static server so the navigation was observable:

```
yarnnn://auth/callback?next=%2Ffiles     → host received it
  → GET /auth/callback?next=%2Ffiles     → the bridge navigated the app
  → GET /auth/login?error=no_session     → the callback ran its real logic
                                            (correct: the probe URL carried no token)
```

⭐⭐⭐ **Two bugs, and the second was invisible without instrumenting both halves.**

1. **The bridge was mounted below the auth boundary.** It sat in the authenticated layout — but a member completing sign-in is on `/auth/login`, *outside* that group. The listener did not exist at the one moment it is needed. It now mounts in the ROOT layout, which is safe under ADR-660 D3 because it reads no cookie and no request state. The symptom was the app waking on the link and never navigating.
2. **`win.emit` and `listen()` are different scopes.** The host emitted to the window; the web layer subscribes app-wide. The host logged the URL, the page never heard it, and every static check was green. Found only by instrumenting the Rust side and the JS side at once.

**A publishable build needs three things, not one.** `scripts/release-shell.sh` signs, notarizes and staples, then asks Gatekeeper directly whether a stranger could open the result — because the real question is not "did the commands succeed". Its preflight refuses early with an actionable sentence.

⚠️ **The preflight itself failed silently at first**: with no certificate, `grep` matches nothing, exits 1, and `set -e` killed the script *before* the message explaining what to do. A helpful check defeated by its own strictness — exit 1, no output. `|| true` on the capture.

**The entitlements are load-bearing.** Notarization requires the hardened runtime, which denies the webview's JIT by default: a notarized build without `com.apple.security.cs.allow-jit` launches to a blank window. The roster is two entries and is an audit surface, like the Tauri capability file.

**Owed, and named**: this machine has no Developer ID, so the sign → notarize → staple chain is **configured and gate-asserted but never executed**. Everything else in step 5 is driven. The operator's four setup steps and the verification that matters — driving a quarantined DMG on a machine that never built it — are in [publishing-the-mac-app.md](../infrastructure/publishing-the-mac-app.md). Auto-update is deliberately not built: it has its own key management, and one unversioned build is the smaller first step.

---

## 7d. Step 5a — the sign-in round trip, found by a member (2026-09-22)

§7c proved the deep link carries a URL back. It did not prove a member can sign in, and they could not. Three bugs on one path, reported from a real build with a screenshot of **Google's consent screen rendering inside the app's own window**, recognising no passkey and offering no password field.

**1. `signInWithOAuth` navigates the window itself.** §4.3's `openExternal` was never on this path — the Supabase call redirects internally, so the consent page loaded in the webview. A provider's sign-in page assumes a browser: it reaches for platform credentials, WebAuthn and the member's existing Google session, none of which a bare webview has. Fixed with `skipBrowserRedirect: true` and handing the returned URL to `openExternal`. ⭐ **A helper only covers the calls that go through it** — the audit found `window.location.href` sites and stopped there, and a library doing its own navigation is invisible to that search.

**2. The PKCE code was never exchanged.** The shell's client sets `detectSessionInUrl: false` — correct, because its callback arrives as a deep link the host hands over, not a navigation the client can inspect — but `app/auth/callback` relied on exactly that auto-detection. The member would return with a valid `?code=` and no session. Now exchanged explicitly, which serves both builds: `exchangeCodeForSession` is idempotent, so the web path is unchanged in behaviour and no longer depends on a side effect.

**3. A hard navigation reboots a static export.** `window.location.href = next` is deliberate on the web — it makes the next request pass through `middleware.ts`, which re-reads the fresh cookie. In the shell it is a full load of `index.html`: the app restarts, the just-established session is not yet consulted, and the member lands back on sign-in. The operator's words: *"sign in, redirects to the landing page, click sign in again, it goes through auth although it recognises I was already logged in."* Both sites (`callback`, `login`) now use `router.replace` in the shell.

⭐⭐⭐ **Three bugs, one path, none reachable by reading.** Each was in a different layer — a library's internal behaviour, a client option's second-order effect, and a navigation idiom that is correct on one build and wrong on the other. §7c's trace was green while all three were live, because it drove the *transport* and never the *act*. **A round trip is only verified by a member completing it.**

⚠️ The falsification of these arms was itself wrong first: replacing the FIRST occurrence of `exchangeCodeForSession` hit the comment, not the call, and the arm stayed green. The gate was sound; the probe was not. Re-run against the call site, all three go red.

---

## 7e. The CSP that shipped a dead app (2026-09-22)

`tauri.conf.json` carries **no CSP** (`"csp": null`), deliberately, and the reasoning belongs here because JSON cannot hold a comment and "we removed the security header" must never read as an oversight.

**What happened.** The shell rendered its sign-in page and **no button did anything**. Reported by the operator with a screenshot.

**Why.** Tauri injects a **nonce** into `script-src` whenever a CSP is set. Per the CSP spec, the presence of a nonce makes a browser **ignore `'unsafe-inline'`** — so every inline script was blocked no matter what the policy string said. Next.js delivers React's hydration payload through inline scripts (`self.__next_f.push(...)`), so the app shipped as **dead HTML**: it looked right and was inert.

Confirmed by isolating the halves — the same static export served over plain HTTP and driven in a headless browser reported `hydrated=true buttons=4`. **The export was always fine; the policy killed it.**

**What still bounds the shell without a CSP:**
- the content is **local**, compiled into the binary — there is no server to inject into it, and no third-party script tag anywhere in the bundle;
- the **capability roster** (`capabilities/default.json`) is what actually limits what the page may ask the host to do, and it is three entries;
- Tauri's IPC boundary is unaffected by this field.

⭐⭐⭐ **A security header that silently disables the product is worse than none.** The right long-term fix is a nonce-aware integration with Next's own `nonce` support, not a hand-written policy; until Tauri supports that, the policy comes out.

⚠️ **The debugging lesson, and the operator's correction that produced it.** I chased this through four layers of custom instrumentation — a console-forwarding fetch, a log server, a self-driving click probe, a window-title channel — before checking whether the export hydrates *at all* outside Tauri. The operator's note mid-way (*"let's make sure we don't implement something that isn't conventional… this should be straightforward using existing industry standards"*) was the right instinct: **isolate the two halves with the plainest possible tool before instrumenting either.** One `python3 -m http.server` and one headless browser answered in two minutes what the probes had not in twenty.

---

## 7f. The root exported as an error page (2026-09-22)

After a successful Google sign-in the member landed on something that looked like a logged-out start — *"redirected to the landing page, confusing, as if I'm not logged in already."*

**The shell's `/` was exporting as an ERROR PAGE.** `redirect()` from `next/navigation` is a SERVER call; a static export has no server, so Next emitted the route with `id="__next_error__"` instead. Visible in one line of the built HTML and in nothing else — every build was green, 48/48 pages generated, and the route "existed".

The fix is a client redirect, and **that is not a violation of ADR-308 — it is the only thing that works here.** ADR-308 requires a stub to be pure server transport because a `'use client'` redirect paints one orphaned frame inside the OS shell. That ruling is about the build that HAS a server. In the shell the orphaned-frame cost does not apply the same way: this route is reached only at cold boot, before any Desktop exists to be orphaned, and `replace` keeps it out of history. `page.web.tsx` is untouched and still the marketing landing page.

Driven: the rebuilt export served over plain HTTP and loaded at `/` lands on `Sign In | yarnnn`, proving the chain `/` → `/desktop` → `AuthGate` runs. With a session it goes straight through.

⭐⭐ **Three bugs in this arc shared one shape: a server-ism that a static export silently converts into something inert.** `cookies()` made 41 routes un-exportable (§7a), `redirect()` became an error page (§7f), and Tauri's CSP nonce killed hydration (§7e). None failed a build. The shell's rule: **anything that needs a request is either moved to the client or excluded from the shell build** — and the way to find the next one is to read the exported HTML, not the build log.

⚠️ The gate arm for this was WRONG on its first cut: it asserted `page.web.tsx` keeps a server `redirect()`, but the web's `/` is the marketing landing page, not a stub. The two roots are different pages, which is the whole reason the shell needs its own.

---

## 7g. The desktop auth architecture, checked against convention (2026-09-22)

The operator's instruction after the third failed sign-in: *"reflect on how conventional SaaS like Notion or Claude would handle this architecturally… double-check our approach hasn't veered off industry best practice."* That was the right correction, and checking it found the actual bug in one step where three rounds of symptom-patching had not.

**The conventional shape for a desktop app's OAuth** — what Notion, Slack, Claude and every native client do, and what RFC 8252 (*OAuth 2.0 for Native Apps*) specifies:

1. the consent screen opens in the **system browser**, never an embedded webview — providers actively block embedded webviews, and passkeys/password managers do not work in one;
2. the flow is **PKCE**, not implicit — no client secret can be kept in a distributed binary, and the verifier never leaves the device;
3. the result returns on a **custom scheme** the OS routes to the running app;
4. the session lives in the **client's own store**, refreshed by the client.

We had 1, 3 and 4. **We did not have 2**, and that was the bug.

**`supabase-js` defaults to `flowType: 'implicit'`.** The web build never hit this because `@supabase/auth-helpers-nextjs` sets `flowType: "pkce"` for you; the shell's hand-rolled `createClient` did not, and inherited the library default. Implicit returns the session in a **URL fragment** (`#access_token=…`) — and a fragment is never transmitted: not to a server, and not through a custom-scheme hand-off. The app received a callback carrying nothing and stayed signed out, which is exactly the loop the operator reported three times: *"after log in, I go back to landing… as if I'm not logged in already."*

⭐⭐⭐ **The lesson is the operator's, not mine.** I fixed three real bugs on this path (§7e hydration, §7f the error-page root, the `window.open` no-op) and each was genuine — but none was the cause, because I was reading the symptom rather than checking the design against the standard. **Asking "what does the conventional architecture look like" is a debugging step, not a review step**, and it should come before the second round of instrumentation, never after the fourth.

Verified against the live service rather than assumed: `GET /auth/v1/authorize?provider=google&redirect_to=yarnnn://auth/callback` returns **302** and passes the scheme straight through to Google, so the provider leg was never the problem.

---

## 7h. A failed sign-in says why (2026-09-22)

`useState(initialError)` captures the prop on the FIRST render only, and the login page reads `?error=` in an effect — so an error arriving with the URL was computed and then **silently discarded**. A member bounced back from a failed callback saw a bare sign-in form with no reason at all, which reads as "it just didn't work" and is unreportable.

Found while diagnosing the desktop sign-in loop: the callback WAS redirecting with `?error=code_exchange&message=…` and the screen said nothing. The error-surfacing code had existed all along and never rendered.

**This is a WEB defect, not a shell one** — the same silent drop happens on yarnnn.com whenever an OAuth callback fails.

⭐⭐ **It paid for itself on the next bug.** §7k's failure (`Auth session missing!`) was the first in this arc the product reported in words the operator could relay, and that one sentence was the whole diagnosis. **A product that cannot say why it failed makes every subsequent bug cost a debugging round.**

⚠️ The gate arm was BLIND on its first cut: it checked for `useEffect` and `initialError` as separate names, and `useEffect` appears elsewhere in the file, so it stayed green through exactly the deletion it exists to catch.

---

## 7i. The browser signs in; the app receives a session (2026-09-22)

**D5 — the shell does not authenticate. The website does.**

After three rounds of fixes to a design where the browser STARTED OAuth and the app FINISHED it, the operator asked the question that settled it: *"some apps like Notion actually send you to a web browser for the auth handling — do you think this may be better?"* Yes, and it is the conventional shape (Notion, Slack, Linear, Claude's own desktop client):

| | Previous design | Now |
|---|---|---|
| Consent screen | system browser | system browser |
| **OAuth completes** | **in the app**, via `yarnnn://auth/callback` | **in the browser**, on yarnnn.com |
| PKCE verifier | written in the app, read after a browser hop | never leaves the browser |
| App receives | a raw `?code=` to exchange | a session already established |
| Auth implementations | two (auth-helpers + a hand-rolled client) | **one** |

The flow: the shell's sign-in opens `https://www.yarnnn.com/auth/desktop`. That page signs the member in with the ordinary web flow — the same one that has always worked — and hands the session back over `yarnnn://auth/session?refresh_token=…`. `DeepLinkBridge` calls `refreshSession` (§7k — the first cut called `setSession`, which needs both tokens) and routes to the desktop.

**Why this is not a bespoke credential.** `refreshSession({ refresh_token })` is the primitive supabase-js provides for exactly this hand-off, so nothing is minted and nothing routes around the one credential path. ADR-645 D2 forbids a second store and a mirrored token; this is the SAME member's own session moving to the device they are sitting at, which is what a refresh token is for.

⚠️ **The token rides a URL**, and that is a real exposure bounded three ways: the scheme hands it to a LOCAL app rather than over a network, macOS routes it only to the registered bundle, and it is consumed once — Supabase rotates refresh tokens on use, so a replayed URL is already spent.

**What this design also buys**, beyond escaping the bug: it is the only shape that works for a cold first launch (a stranger with no session meets a real web page, with their password manager and their existing Google session), and it survives providers tightening against native clients — Google already blocks embedded webviews and the trend is one way.

⭐⭐⭐ **The lesson is about when to change architecture rather than patch.** I fixed four real bugs on the old path — hydration, the error-page root, a `window.open` no-op, the implicit flow — and every one was genuine. None produced a working sign-in, because the design put a secret in one context and required it in another. **When three consecutive correct fixes do not move the outcome, the next thing to question is the design, not the fifth symptom.** The operator asked that question twice before I acted on it.

---

## 7j. The opener had permission but no scope (2026-09-22)

§7i's hand-off shipped and the member saw *"Signing you in…"* **inside the app**, spinning. The string exists only in `page.web.tsx`, which the shell does not ship — so the app was rendering the WEBSITE's page in its own window.

**Two faults, and the second hid the first.**

1. **`opener:allow-open-url` was granted without a URL scope.** The plugin's scope defaults to EMPTY, which refuses every URL. The permission was present, the command was callable, and every call was denied — **silently**, since `openUrl` rejects rather than throwing anywhere visible.

2. **`openExternal` caught that rejection and fell back to `window.location.href`** — navigating the app's own window to the external page. That is the exact trap the helper exists to prevent, so the fallback converted a clean failure into the failure mode the design was built around. The member got yarnnn.com's sign-in hand-off rendering inside the app, spinning for ever because it had no session there.

The scope is now explicit and narrow: our own hosts, the provider consent screens, the payment pages. **Not `https://*`** — a wildcard would let any page the app renders ask the OS to open anything. And the fallback is gone: a refusal now logs and stops, because a fallback that reintroduces the failure mode is worse than an error.

⭐⭐⭐ **A permission is not a capability.** Tauri's roster says which commands the page may CALL; the scope says what it may call them WITH. Granting the first and leaving the second empty produces a build where everything looks wired and nothing works — and the gate arm that read the roster was green throughout, because it checked for the identifier and not for its scope.

⚠️ Two gate arms in this section were blind on their first cut, both from slicing on the string they were testing for: one split the shell branch on `window.location.href = url;`, which appears in the comment forbidding it, truncating the slice before the code. **A check that searches for a string must not also use it as a delimiter.**

---

## 7k. `setSession` needs both tokens (2026-09-22)

§7j's scope fix landed and the hand-off finally ran end to end: the app opened the browser, the browser signed the member in, and the deep link came back. The app then said **`handoff: Auth session missing!`**

The bridge called `setSession({ access_token: '', refresh_token })`. `_setSession` opens with:

```js
if (!currentSession.access_token || !currentSession.refresh_token) {
    throw new AuthSessionMissingError();
}
```

— so an empty `access_token` fails the guard **before the refresh token is ever used**. The primitive for a refresh-token-only hand-off is `refreshSession({ refresh_token })`, which takes the token alone and mints a fresh session from it. That is exactly what a hand-off carries: the browser holds the live session, and the app is given the means to establish its own.

⭐⭐ **The error message was the whole diagnosis.** "Auth session missing!" is `AuthSessionMissingError` by name, and one grep of the library found the guard that throws it. This was the first failure in the arc that the product reported in words a member could relay — because §7h had just fixed the notice that silently swallowed them. **The error-surfacing fix paid for itself on the next bug.**

⚠️ This is also the fourth time in this arc that a library's contract differed from what I assumed while writing a plausible-looking call (`window.open` routing to the browser, `flowType` defaulting to pkce, a permission implying a scope, `setSession` accepting a partial session). The pattern is mine: **reading the function's guard clauses costs a minute and would have caught all four.**

---

## 7l. The return target was refused by our own guard (2026-09-23)

The first real sign-in after §7k: the app opened the browser, the member signed in, and the browser landed on **`/desktop`** — the web product, signed in — while the app waited for a deep link that never came. Reported with a screenshot.

The hand-off page is `/auth/desktop`. A signed-out member reaching it is bounced through login with `?next=/auth/desktop`. `getSafeNextPath` (`web/lib/auth/redirect.ts`, since 2026-02-26) refuses **every** `next` beginning with `/auth/` — correctly, for its original purpose: a `next` of `/auth/login` or `/auth/callback` would loop. All three stages that carry `next` — middleware, the login page, the callback — run it, so the hand-off target was rewritten to `HOME_ROUTE` at each.

The fix is an **exact-match** exemption for the one `/auth/` page that is a destination rather than a step of the sign-in. No loop is possible: `/auth/desktop` bounces to login only when there is no session, and it is reached from login only once there is one. Every other `/auth/` path — including `/auth/desktop/x` — stays refused.

⭐⭐⭐ **This time the guard clause was ours.** §7k's lesson was to read a library's guards before writing a call; the same applies to a route handed to our own redirect chain. `/auth/desktop` was placed under `/auth/` because it is an auth page, and that placement is exactly what the guard keys on. §7i's design never ran end to end until today, because §7j and §7k failed first — each fix revealed the next stage, not a regression.

The gate arm **runs the real function** under Node's type stripping rather than reading its text, with three arms: the harness ran (a crash reports nothing, so it is its own check), `/auth/desktop` survives, and the exemption is exact. Each proven RED in place: exemption removed, exemption widened to a prefix, module broken.

---

## 8. The order — built so the hands fit later

Steps 1–3 are **true of the web product today** and worth doing whether or not the shell ships — each fixes something real in the web build (the auth gate closes a known defect class, the locale chain removes a silent-English failure, and the Suspense boundaries remove a client-render bailout on first paint).

1. **The client auth gate** (§4.1) — a mount-time session resolve rendering nothing until it settles, with the derived `KERNEL_SURFACE_SLUGS` prefix set ported verbatim. First, because it is the one item that can re-open a known production defect.
2. **The locale chain, client-side** (§4.2). ⚠️ The ADR-660 gate asserts the literal `<IntlScope>` in named layouts; it moves in the same commit or it goes red for the wrong reason.
3. **External navigations, share links, and the Suspense boundaries** (§4.3, §4.4, §7a blocker 4) — system-browser opens, a canonical web-origin constant, and a page-level `<Suspense>` on the eight surfaces whose `useSearchParams` bails out under export (`/chat`, `/files`, `/settings`, `/supervisor`, `/text`, `/slides`, `/images`, `/notifications`).
4. **The packaging target** — static export of the authenticated group, custom scheme, OAuth callback deep-linked. **Tauri, and the choice is now load-bearing rather than aesthetic**: §5 makes local OS access a planned capability, and Tauri's Rust host is where a screen/input capability would live, behind a per-act permission the member grants. Electron would work; Tauri makes step 6 a smaller step.
5. **Notarization and auto-update.**
6. **Local hands** (§5, §6) — after the shell is real and stable, as its own implementation ADR carrying §6's four conditions and a driven trace. Not before: §6.4's standard cannot be met against a shell that does not yet exist.

**What step 4 must not foreclose**, so step 6 does not require reopening it: the shell keeps a host-side capability seam (Tauri commands) rather than assuming a pure web sandbox; the lane transport can carry a tool whose executor is **local to the client** rather than server-side; and the narrative/receipt path (§6.2) is reachable from a client-originated act, not only from an API-originated one.

---

## 9. Gate

`api/test_adr661_the_shell_may_be_native.py`. Doc-first ADR, doc-shaped gate — it asserts the **conditions**, because those are what erode:

1. The unattended path stays toolless — `run_bounded_derive_turn` passes no `tools=` (guards §6.1; mirrors ADR-615's own gate rather than replacing it).
2. `resolve_platform_credential`'s agent refusal is intact — local hands must not become a way around it (§5.2).
3. `write_revision` remains the single write path with no second writer (§6.2).
4. No local-hands capability ships **before** its own implementation ADR exists: no `computerUse`/`computer_use` primitive, tool or client-registry capability while this ADR is the only one on the subject (§6.4's evidence standard, enforced as a tripwire rather than as a ban).
5. The two dead Supabase packages stay absent from `web/package.json` (§7.5).
6. `docs/analysis/src_claudeCC/` stays gitignored — it is a vendored copy of Claude Code's own source, and **22 of 28 "computer use" matches under `docs/` are that tree, not canon.** A future session grepping for prior art will be misled; this keeps it out of the repo.

---

## 10. Consequences

- **The Mac shell is authorized in principle and unbuilt.** It needs the operator to call §8, not another ADR.
- **Local attended computer use is scoped, not declined** — with the distinction from the remote sandbox recorded (§5.1) so the two are never again collapsed, and with four conditions binding at birth (§6).
- **The remote sandbox stays declined** under ADR-395 am.1 §8.7.
- **Steps 1–3 are live debt on the web product**, independent of packaging.
- **The kernel is untouched.** No mechanism was added: a client form is not an architectural act, and local hands are an instrument of a member already present, not a new principal.

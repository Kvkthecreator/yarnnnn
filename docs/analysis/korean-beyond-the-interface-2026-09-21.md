# Korean beyond the interface — what a Korean member hits that the string catalog cannot fix

**Date**: 2026-09-21 · **Status**: audit, nothing built, nothing decided
**Occasion**: ADR-660 §13 shipped full interface coverage (`3bc215b`, 2026-09-21). This asks what
Korean actually requires *beyond* the interface strings, and whether anyone already thought about it.
**Hat**: B (evaluation) — findings recommend; a fix lands under Hat A.

> Every load-bearing claim below carries a receipt measured on 2026-09-21. Where a number here
> disagrees with an ADR or an earlier analysis, the number was re-measured and the source is named.

---

## 0. The one-paragraph answer

**This was already analysed, and the analysis is better than this one would have been.**
`docs/analysis/language-support-korean-feasibility-2026-09-16.md` (364 lines, five days before
ADR-660 shipped) cut the problem into three layers — behaviour, search, chrome — and ranked them
**behaviour → search → chrome**. ADR-660 shipped the chrome, which that document called step 5 of 7
and explicitly named as "the botch" order if done first. That is not a criticism of ADR-660: the
operator asked for the interface, and the interface is done and done well. But it means **the two
layers the earlier analysis ranked ABOVE the chrome are still open**, and one of them is measurably
broken on live production data today.

The ranking survives re-measurement, with one correction and one new finding:

- **Behaviour is fine** and needs no work — D5 holds (receipt §3.1).
- **Search is the real defect**, confirmed on real Korean files in production (§3.2).
- **NFC/NFD is a new finding neither prior document raised**, and it is already in production
  data — 4 Hangul paths, 2 stored NFC, 2 stored NFD, mutually unfindable (§3.3).
- **The layout fear was wrong.** Measured with the app's real font stack, Korean is
  **0.86× English width**, not the assumed 2×. Zero slots overflow (§3.6).

---

## 1. Was this already analysed? — decided / deferred / never ruled

### 1.1 DECIDED — live rulings that outrank fresh analysis

| # | Ruling | Where | Status |
|---|---|---|---|
| **R1** | **A language is a member's preference, never a workspace's.** `auth.users.user_metadata.locale`; one chain `resolveLocale`; no locale in app URLs. | ADR-660 D1/D2 | Implemented |
| **R2** | **No language instruction enters the lane frame.** Attended: the engine mirrors the member. Unattended: a standing declaration writes a file in the commons, whose language is the work's, not the nearest member's. | ADR-660 D5 | Implemented; **re-verified holding** §3.1 |
| **R3** | **An IME composition owns Enter first.** One rule, `web/lib/shell/submit-key.ts`; honours both `isComposing` and the legacy `keyCode === 229`. | `80b9874` (2026-09-13), generalising ADR-483 D3 | Implemented; **re-verified** §3.5 |
| **R4** | **The path is an identity key; the name is a fact the artifact carries.** A fully non-Latin name slugs to `untitled` and is disambiguated, never romanised — "guessing wrong is worse than being opaque". | ADR-469, `api/services/naming.py` | Implemented; **re-verified** §3.4 |
| **R5** | **The four entry routes stay English**, and `SCOPELESS_BY_RULING` forbids a translation hook in the four components reachable only from them. | ADR-660 D8 | Operator ruling — **law** |
| **R6** | **`/admin` console chrome stays English** (a Hat-B instrument). | ADR-660 D7 | Operator ruling — **law** |
| **R7** | **Brand and app names stay in Latin script** (`Blogger`, `Supervisor`, `Reach`); a kernel noun does not return as its Korean transliteration. | ADR-660 D6, VOICE §7 | Implemented |
| **R8** | **Substrate content is language-neutral and stays that way** — a file gets no language column; that would put a type where the kernel refuses one. | ADR-222 / ADR-373/378, restated in the 09-16 analysis §8 | Law by derivation |

**R2 and R8 are the two most important for this audit**, because the obvious "fix" for several gaps
below is to tag a file with a language or push a locale into the lane frame. Both are already ruled
against, on kernel grounds. Do not re-litigate them; design around them.

### 1.2 CONSIDERED AND DEFERRED — with a stated reason

| Item | Deferred by | Stated reason |
|---|---|---|
| **Served strings** (error details, agent names/blurbs, notification-kind registry, connector titles, lane default name) | ADR-660 §8, still open after §13 | "The convention is an error *code* the client words; that is its own pass." A **cost deferral**, not law. |
| **Outbound email** | ADR-660 §8 | Named, no reason given beyond scope. **Cost deferral.** |
| **The marketing site in Korean** (`/ko` + `hreflang`) | ADR-660 §8 / D1 | Indexed pages want a URL-prefix mechanism, which the app deliberately does not use. **Cost deferral with a design reason.** |
| **`lib/formatting.ts` relative times** | ADR-660 §11/§13 | "A shared layer on 15 surfaces; it translates with a pass of its own." **Cost deferral.** |
| **Korean banned-noun patterns in the voice guard** | ADR-660 §8 | "A Korean pattern earns its place the way an English one does — with a string that shipped." **Deliberate; correct.** |
| **The stage notice on the sign-up door** | ADR-660 §8 | Single-sourced with the marketing wordmark and `llms.txt`; a catalog copy would fork it. |
| **Name fidelity vs. storage** (a Korean name slugging to `untitled`) | ADR-459 D2 → resolved by ADR-469 | Closed by the path/name split. |

### 1.3 NEVER RULED — the operator's call, listed for §6

These were *raised* by the 2026-09-16 analysis but never went to a decision, or were never thought of
at all. **Per the operator's standing correction — classify by the limit's stated reason, and ask
rather than infer from ADR precedent — these are the ones to rule on.**

- **N1 — Search under Korean.** Raised (09-16 §3), measured, never ruled. No ADR mentions it.
- **N2 — Unicode normalization (NFC/NFD) of paths.** **Never thought of by anyone.** Not in any ADR,
  not in either analysis. Already live in production data.
- **N3 — Whose language is an unattended file?** ADR-660 D5 answers "the work's, not the member's",
  which is a coherent ruling — but it was made for the *attended* case's reason ("no observed
  failure"). The unattended edge has a named owner (`CONTRACT.md`) and was never separately ruled.
- **N4 — The skills mirror writes English into every member's own filesystem.** Raised (09-16 §8),
  never ruled. The byte ceilings make it more than a translation question.
- **N5 — Does a Korean member get English email?** Deferred, but nobody has asked whether that is
  *acceptable* or merely unbuilt.

---

## 2. What ADR-660 already solved that the 09-16 analysis listed as blockers

Worth stating, because the earlier document's §7 "three structural blockers" reads as open and is not:

| 09-16 blocker | Status now |
|---|---|
| §7.2 `toolLabels.ts` runtime verb composition (English SOV baked in) | **Solved.** ADR-660 §11 — resolves to a catalog key + args; `withSubject` became a whole ICU message. |
| §7.1 mid-sentence runtime concatenation | **Solved** for the named sites; `resolveActorForViewer`'s `"(via"` slice was the deepest instance (§13). |
| §7.3 copy passed as props (`AuthForm`) | **Solved** — keys moved to the caller. |
| §5 "the bilingual transcript" — the highest usability-per-string defect | **Solved.** This was the single best-argued item in the 09-16 document and it is done. |
| §4 the 870-string first-session set | **Done** — 2330 keys / 17 namespaces. |
| §6 slot budgets at Korean width | **Measured clean** — see §3.6, and the estimate that worried it was wrong. |

**So ADR-660 did the expensive layer and did it thoroughly.** What remains is the cheap layer the
earlier analysis said to do *first*, plus one thing nobody saw.

---

## 3. The gaps, each with a receipt

### 3.1 Agent output — D5 holds. No gap. ✅

**Receipt** (2026-09-21):
```
grep -rn "locale|language" services/lane_runner.py services/derive_turn.py services/standing_work.py
  → empty
grep -rniE "in english|respond in|language" services/workspace_paths.py
  → empty
```
The ADR-660 gate's own D5 arm passes (3 checks: `lane_runner`, `standing_work`, `derive_turn` read no
member locale). Nothing pins the agent to English, so a member writing Korean gets Korean back.

**The unattended edge (N3) is genuinely well-designed, not an oversight.** `_STANDING_JOB`
(`api/services/standing_work.py:1159`) hands the model THE CONTRACT, THE CURRENT FILE and THE FRESH
SOURCE MATERIAL, and says nothing about language. So an unattended run inherits the language of
`CONTRACT.md` and of the file it is revising — which is exactly R2's principle ("the language of the
work") expressed mechanically rather than by instruction. A Korean member who writes a Korean
`CONTRACT.md` gets Korean output; one whose sources are English gets English.

**Severity: none.** Recommend: leave it. If the operator wants to rule N3 explicitly, the ruling to
write down is the one already implemented — *the language of a kept file is the language of its
contract and its sources* — so that a future session does not "fix" it by injecting the member's
locale, which would violate R2 and R8 at once.

### 3.2 Search — CONFIRMED BROKEN on live production data. 🔴 The highest-severity finding.

`search_workspace` hardcodes `'english'` in six places
(`supabase/migrations/246_search_covers_the_name_and_degrades.sql:54-56, 74, 77, 84, 87-88`).
Still true today; also `111`, `212`, `218`.

**Receipt A — the mechanism** (live DB, read-only, 2026-09-21):
```
to_tsvector('english','3분기 매출 보고서입니다. 매출이 증가했습니다.')
  → '3분기':1 '매출':2 '매출이':4 '보고서입니다':3 '증가했습니다':5

bare noun matches                      → t
noun + subject particle 이/가 hides it  → f
noun + topic particle 은/는 hides it    → f
noun + object particle 을/를 hides it   → f
English control (reports → report)     → t
```
The English stemmer whitespace-splits Korean and stems nothing. Korean is agglutinative, so a noun
carrying a particle is a different lexeme from the bare noun.

**Receipt B — on a REAL member file, through the REAL RPC.** A Korean connector smoke test already
exists in production (`/workspace/operation/한국어-커넥터-테스트.md`, authored 2026-09-18) whose own
item 3 asks *"한국어 질의로 이 파일을 다시 찾을 수 있는가"* — can I find this file again with a
Korean query. Answering it against `search_workspace(...)` in the workspace that holds it
(`d5b9029b-…`):

| Query | In the file as | Hits |
|---|---|---|
| `커넥터` | bare | **2** |
| `한국어` | bare | **1** |
| `테스트` | bare | **1** |
| `파일` | bare (also `파일은`) | **1** |
| `삭제` | only `삭제하거나` (conjugated) | **0** ❌ |
| `본문` | only `본문이` (particle) | **0** ❌ |
| `workspace` (English control) | — | **20** ✅ |

So the smoke test's question 3 has an answer: **sometimes.** Bare nouns are found; inflected and
particle-bearing forms — the majority of real Korean prose — are not. Search does not error. It
returns fewer rows, and a member reports that as *"search is bad"*, never as *"search is broken"*.

**Receipt C — no config swap can fix it.**
```
Korean/CJK text-search configs available on this instance: NONE (only 'simple' among CJK-relevant)
to_tsvector('simple','매출이 증가했습니다') @@ plainto_tsquery('simple','매출') → false
'매출이 증가했습니다' LIKE '%매출%'                                            → true
```
`simple` merely skips stemming; the particle still welds to the noun. A substring/n-gram approach is
what works.

**Receipt D — closes the 09-16 open question.** That analysis could not check extension availability.
Measured today:
```
pg_available_extensions ~ bigm|groonga|trgm  →  pg_trgm 1.6, pgroonga 3.2.5, pgroonga_database 3.2.5
installed extensions                          →  pg_net, pg_stat_statements, pgcrypto, plpgsql,
                                                 supabase_vault, uuid-ossp, vector
```
**`pgroonga` 3.2.5 is AVAILABLE on this Supabase instance and not installed.** pgroonga is the
standard CJK full-text solution; `pg_trgm` is the lighter fallback. This materially changes the cost
estimate the 09-16 analysis had to leave open.

**Receipt E — the semantic fallback is still effectively dead**: `8 of 902` `workspace_files` rows
carry an embedding (0.9%). The 09-16 measurement was 7/774. Lexical FTS is all there is.

⚠️ **Latent second defect, re-confirmed.** The OR-degradation path (mig 246:84) rewrites
`plainto_tsquery` output by string-replacing `' & '`, justified by a comment reading *"english
lexemes cannot contain the separator."* Measured: `plainto_tsquery('english','매출 보고서')` →
`'매출' & '보고서'`, which rewrites correctly — so the premise happens to hold for Hangul. But the
comment's reasoning is about English specifically, and it should be restated rather than relied on.

**Receipt F — pgroonga MEASURED, 2026-09-21, inside rolled-back transactions.** The 09-16 analysis
could not check this and §7 below listed it as unverified. Now driven:

- `CREATE EXTENSION pgroonga` **succeeds** on this instance (3.2.5).
- Recall on the 34 Korean-bearing rows — pgroonga fixes exactly the failures, and never returns fewer:

| Query | in the file as | english FTS | pgroonga | **hybrid (OR)** |
|---|---|---|---|---|
| `본문` | `본문이` (particle) | **0** ❌ | 1 | **1** ✅ |
| `삭제` | `삭제하거나` (conjugated) | **0** ❌ | 1 | **1** ✅ |
| `파일` | bare + `파일은` | 1 | 2 | **2** ✅ |
| `커넥터` | bare | 2 | 2 | 2 |

- ⚠️ **pgroonga ALONE regresses English**, because it substring-matches without stemming:
  `reports` 181 → **103** (it no longer matches `report`). So pgroonga is **not a replacement** for
  the English config.
- ⭐ **The hybrid is strictly better than either**: `reports` 181 → **187**, `workspace` 387 → **412**,
  while the Korean failures go 0 → 1. The design is therefore *keep `to_tsvector('english', …)`,
  add a pgroonga index, and OR the two* — which is the shape `search_workspace`'s existing
  strict/loose CTE already has.
- **Cost, measured**: indexing all 902 rows (8657 kB of content) grew the database **312 MB → 402 MB**,
  i.e. **~90 MB of index for ~8.6 MB of content (~10×)**. Not free; `pg_relation_size` reads 0 because
  pgroonga stores outside the Postgres relation, so measure by database-size delta, not relation size.

**Severity: HIGH — blocks real Korean use.** — ✅ **CLOSED 2026-09-21, migration 260.** The hybrid
shipped and is verified on the live object: `본문` and `삭제` now return 1 each (labelled
`match_mode='korean'`), every English query is byte-identical, and all four filters hold through the
new tier. The grader caps a substring hit at WEAK. Gate `api/test_search_speaks_korean.py` 20/20
against the live database, falsified both ways. This is the one that cannot be retrofitted by any
translation effort and degrades silently.

### 3.3 Unicode normalization (NFC/NFD) — NEW FINDING, already in production. 🔴

**Nobody has raised this.** Not in any ADR, not in either prior analysis. macOS/HFS+ has historically
stored filenames decomposed (NFD) while typing in a browser produces composed (NFC); the two are
byte-different and equal to no one.

**Receipt A — no normalization exists anywhere on a write path.**
```
grep -rn "unicodedata" api/services api/routes
  → services/naming.py:34 and :58 ONLY (inside the ASCII fold)
```
Every other path normalizer (`_normalize_workspace_rel`, `parse_file_reference`, `_repo_rel`,
`_normalize_rel`) does prefix/`..` handling and no Unicode work.

**Receipt B — it is live in production data.** 902 files; **4 carry Hangul in the path**, 34 carry
Hangul content. Of the four paths:

| Path | NFC? | NFD? |
|---|---|---|
| `/workspace/사업/경기도-AI데이터산업체조사/2023-모집단-추출로직-분석.md` | ✅ | — |
| `/workspace/inbound/uploads/operator/배출증-출력.extracted.md` | — | ✅ |
| `/workspace/inbound/uploads/operator/배출증-출력namechange.pdf` | — | ✅ |
| `/workspace/operation/한국어-커넥터-테스트.md` | ✅ | — |

**Both forms are already stored**, split exactly along provenance: the two under
`inbound/uploads/operator/` (a macOS upload) are NFD; the two authored in-app are NFC.

**Receipt C — the consequence, on those live rows:**
```
NFD file looked up by its NFC-typed name  → f   ❌
same file looked up by its NFD name       → t
NFC file looked up as NFD                 → f   ❌
NFC file looked up as NFC                 → t
```
And through the MCP chokepoint:
```
parse_file_reference(NFC) == parse_file_reference(NFD)  → False
```
Postgres agrees: `'한글' = normalize('한글', NFD)` → `f`, `length` 2 vs 6.

**What this means in the product.** Two visually identical Korean filenames are two different keys.
An agent told a filename in one form cannot `open`, `edit`, `move` or `history` the file stored in
the other. `(workspace_id, path)` is the substrate's binding unit (ADR-373), the single-writer unit
(ADR-286) and the revision-chain key (ADR-209) — so this is not a display bug, it is a **key
integrity** question. A member could also create a second file that looks byte-for-byte identical in
the UI, and `write_revision()`'s parent-pointer chain would treat them as unrelated.

Export inherits it: `_repo_rel` preserves bytes verbatim (correct for git), so NFC and NFD export as
**two different tree entries** that can collide or duplicate on a macOS checkout.

**Severity: HIGH, low incidence today.** — ✅ **CLOSED 2026-09-21, migration 259.** Applied: 0
non-NFC rows remain in either table, all 4 Hangul paths intact, every head matches its version chain,
and the two previously-unfindable files now resolve by their composed name. Only 4 files, and the collision needs the same name typed
two ways. But it is silent, it is in the substrate's primary key, and the fix is cheapest now while
4 rows exist rather than after Korean adoption. Note the one mercy: `path_slug` ASCII-folds, so
*generated* slugs are immune (`slug(NFC) == slug(NFD) == 'untitled'`) — this only bites paths where
Hangul reaches the path directly, i.e. uploads and told-names.

### 3.4 Files and naming — R4 holds. No gap. ✅

**Receipt** — driving `api/services/naming.py`:
```
'한글 문서'          → untitled
'3분기 매출 보고서'   → 3
'회의록'            → untitled-2
'제안서'            → untitled-3
distinct keys: 4 of 4
```
The ADR-469 path/name split works: four distinct Korean names produce four distinct keys, each
reading back as the name the member typed (carried on the artifact's own `<title>`). The Grade-3
"total erasure → namespace collision" finding of `what-a-thing-is-called-vs-how-its-stored-2026-07-20.md`
was **acted on and closed**.

⚠️ One cosmetic oddity worth noting, not a defect: `'3분기 매출 보고서'` → `3`, because the only
ASCII survivor is the digit. Honest and collision-free, but a folder literally named `3`. Consistent
with R4's "the key is not read by anyone".

`HOME_ALIASES` is unchanged (`{"Documents": "operation", "Downloads": "inbound"}`) and gate-locked to
prompt prose; a Korean told-name would fail that gate outright rather than drift — which is the
correct behaviour, and forces the decision into the open if anyone wants Korean home names.

### 3.5 IME composition — R3 holds. No gap. ✅

The 09-16 analysis did not raise this; `80b9874` (2026-09-13) had already fixed it, three days
earlier. **15 files** import `lib/shell/submit-key.ts`, including every text-submit surface the
prompt names: the chat composer (`ChatSurface`, `LanePanel`), rename fields (`RenameModal`,
`NameDocumentModal`), `NewFolderModal`, `ShareDialog`, `WorkspaceMembersCard`, `SourcesCard`,
`TextEditor`, `ProseCanvas`, `StudioSurface`, `StudioDesignTab`, `NewArtifactModal`,
`WorkspaceCreatePane`.

**Receipt — the sweep for stragglers.** Two files use a raw `key === 'Enter'` without the guard, and
both are correct as-is:
- `components/workspace/viewers/projection.ts:2794` — inside the **sandboxed canvas iframe**, a
  link-URL field (`https://… or a workspace path`), not a composition surface.
- `components/authoring/PagedNavigator.tsx:590` — `Enter || Space` **card activation** (a11y keyboard
  affordance on a non-input element). No IME session can be open.

**Severity: none.** The rule is genuinely general and genuinely applied.

### 3.6 Layout — measured, and the prior estimate was WRONG in the safe direction. ✅

The 09-16 analysis §6 assumed Hangul is full-width (~12px at 12px font, ~2× Latin) and flagged its own
§10 that this was *assumed, not measured*. It was right to flag it.

**Receipt — measured in the running app with `canvas.measureText` and the app's real font stack**
(`ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, …`), at 12px:
```
Latin advance : 6.35 px
Hangul advance: 10.38 px      (ratio 1.63×, NOT 2×)
```
Applied to all **17 launcher summaries** in the catalog against the VOICE §2 budget of **312px**
(390px phone):
```
over budget in English: 0
over budget in Korean : 0
widest Korean         : 242 px   (slides)
widest English        : 298 px   (workspace-settings)
mean ko/en width ratio: 0.86×
```
**Korean is narrower than English on this slot, by 14% on average.** Because Korean runs ~0.5–0.6× the
character count and only 1.63× the width per character, the net is below parity. The VOICE §7 line
("Korean is usually shorter per idea and wider per glyph; check the slot, do not assume") is correct
and now has a measurement behind it.

**Receipt — driven at phone width.** `/desktop` and the open Launcher at 390×844, Korean rendering
(`<html lang="ko">`, `경계 / 연결됨 / 나가는 중 / 오간 기록`):
```
horizontal page scroll : false
Hangul nodes clipped by ellipsis : 0
Hangul nodes overflowing viewport: 0
```

**Severity: none found.** Caveat stated honestly: I drove `/desktop` and the Launcher, not all
eight surfaces, and the workspace I drove has little content. The catalog-wide width scan (below) is
the broader signal.

⚠️ **One thing the width scan does surface**: across all 2330 pairs, some Korean values *are* wider
than their English twin — the worst by +186px is `supervisor.notifications.standingSubtitle`. None
of these sit in a VOICE §2 measured slot (they are wrapping subtitles and empty states, where width
is not the budget). Worth a spot-check if a future pass puts one of them in a fixed slot.

### 3.7 Dates, numbers, sort — a real, small gap. 🟡

**The two can now disagree.** `toLocaleDateString(undefined, …)` and `toLocaleString([], …)` follow
the **browser's** locale; ADR-660 made the member's locale an **account** preference. Before ADR-660
there was one source of truth; now there are two, and nothing reconciles them.

**Receipt — ~30 call sites pass `undefined` or `[]`**, including the whole shared layer
`web/lib/formatting.ts` (lines 34, 47, 67, 87, 90, 103, 115, 134) plus `files/page.tsx:421`,
`SubscriptionCard.tsx` (×6), `UsagePaneBody.tsx` (×2), `ShareDialog.tsx:98`, `ShareClient.tsx:27`,
`ManageConnectionSubsurface.tsx:112`, `AttachedConnectorSubsurface.tsx:70`, `EmissionsView.tsx:49`,
`decisions.ts:146`.

Concretely: a Korean member on an English-locale browser (common — corporate laptops, default OS
installs) sees a fully Korean interface with `Mar 12` and `3:45 PM` instead of `3월 12일` and
`오후 3:45`. The reverse also holds.

**`formatting.ts` additionally hardcodes English words** that no locale argument would fix:
`just now`, `soon`, `Today`, `Yesterday`, and the `2m ago` / `3h ago` / `2d ago` / `5w ago` grammar.
This is the shared layer ADR-660 §11/§13 deferred, reaching **15 surfaces**.

**Sorting**: 3 sites use `localeCompare` without a locale (`ContentViewer.tsx:304`,
`SendToSlack.tsx:99`, `ActivityLedger.tsx:170`). Default `localeCompare` sorts Hangul in correct
Unicode/jamo order, so this is **not** a defect — but it also follows the browser, so ordering could
differ between two members looking at the same list.

**Severity: MEDIUM, cosmetic-to-confusing.** Does not block use. The fix is one shared layer plus a
locale argument threaded from the existing provider.

### 3.8 Served strings — the deferral is real and larger than recorded. 🟡

**Receipt**: `266` `HTTPException(... detail=)` strings across `27` files.
(ADR-660 §8 says 136; the 09-16 analysis says 235. **The repo wins: 266 today.** The count has grown
~13% in five days, which is itself the argument for doing this incrementally as errors are touched
rather than as a big-bang pass.)

The envelope is already the right shape — an unauthenticated probe returns:
```
{"error":{"code":"not_found","message":"Not Found","hint":null}}
```
A `code` already rides alongside the English `message`, so client-side wording by code is
architecturally cheap — the same move ADR-660 §10 ruling 1 made for surface titles, where the shell
words `surfaces.{slug}.title` and falls back to the served string.

Also still served and English: the notification-kind registry (`services/notifications.py:66-109` —
`Decisions & activity`, `Reports`, `Mentions`, `Agent runs`, `Account` with their descriptions),
agent names/blurbs, connector titles, the lane's default name, and `blockLabels`.

**Severity: MEDIUM.** A Korean member meets English at every error and in the notification settings
pane. Annoying, not blocking, and the fallback pattern is already proven.

### 3.9 Email — English, and nothing reads a locale. 🟡

**Receipt**: `grep -rn "locale|language" services/account_email.py services/notifications.py` → empty.
Subjects are hardcoded English literals: `"Welcome to yarnnn"` (`:181`), `f"You joined {ws}"` (`:216`),
`f"You were removed from {ws}"` (`:246`), `"Your yarnnn account was deleted"` (`:278`).

A Korean member receives English mail. Nothing **breaks** on a Hangul display name — the `{ws}`
interpolation is a Python f-string into an HTML body, UTF-8 throughout, and the workspace name is
already Hangul-capable (the live `사업/` path proves Hangul survives the pipeline).

⚠️ One thing not tested and worth flagging rather than claiming: **MIME encoding of a Hangul subject
line**. `f"You joined {ws}"` with a Korean workspace name produces a non-ASCII subject; whether the
transport RFC-2047-encodes it correctly was not driven here (it needs a real send).

**Severity: LOW-MEDIUM.** Email is infrequent and account-level. The locale is now available
account-side (`user_metadata.locale`), so the plumbing exists — this is the one deferred item whose
prerequisite ADR-660 quietly delivered.

### 3.10 The skills mirror — English in the member's own filesystem, with a byte trap. 🟠

Raised by 09-16 §8, never ruled. `ensure_kernel_skills()` mirrors 12 `SKILL.md` files into every
workspace at `system/skills/{slug}/SKILL.md`. Genesis itself is pure (ADR-414 D4), but the mirror
reintroduces English into the member's own substrate — and the voice guard does not scan `SKILL.md`
at all.

**Receipt — the byte ceilings are a latent English assumption, and tighter than recorded:**
```
kernel index                 : 3716 bytes
UNBOUND_INDEX_CEILING (4000) : 284 bytes headroom
INDEX_CEILING (3400)         : -316  (a bound pane already self-truncates)
ASCII chars in the index     : 3677
if translated (≈0.6× chars × 3 bytes/char UTF-8) : ≈6618 bytes
```
**Korean would need ~1.65× the ceiling.** UTF-8 Hangul is 3 bytes/char vs 1 for ASCII, so a byte
ceiling silently penalises every non-Latin language. And `api/services/skills/__init__.py` requires
A/B evidence to raise a ceiling (ADR-630 / DP22), so this cannot be bumped casually.

The real design question the 09-16 analysis posed and nobody answered: **should a byte ceiling be a
character or token ceiling?** A byte budget encodes an English assumption into a language-neutral
mechanism. Note that ADR-660's own D4 gate hit the same class of bug from the other side — Python's
`\w` matching Hangul — so "a measure that assumed ASCII" is a recurring shape here.

**Severity: MEDIUM, and it is a ruling question, not a build task.** Recommend **not** translating
skills. R8's logic applies: skills are craft instructions read by the model, which is multilingual;
translating them spends the scarcest budget in the system for no measured gain, and the 09-16
document's own warning stands — *never prune or judge a skill on a quality score* (CLAUDE.md), and
by symmetry never translate one without evidence.

### 3.11 Marketing / SEO — what `/ko` would cost and buy. 🟢

Deferred by ADR-660 §8/D1 with a real design reason: the app is `noindex` and a path is an address
members share across languages, so URL-prefixed locales are for *indexed* pages only.

**What it costs**: a second mechanism alongside the existing one — `/ko/…` routing, `hreflang`
alternates, a translated marketing catalog, and Korean versions of the blog corpus (113 SSG paths
today). The 09-16 analysis explicitly scoped `content/posts/` (193 files, ~1MB) **out**. The build
receipt discipline would need re-establishing: ADR-660 guarded "every marketing route stays `○`"
across four passes, and a locale prefix touches exactly that invariant.
**What it buys**: Korean organic search. Nothing for existing members — a signed-in Korean member
already gets a Korean app.

**Severity: LOW / strategic.** This is a go-to-market question, not a product-correctness one, and
it is the only item here that is genuinely a *later* decision rather than a deferred one.

---

## 4. Severity summary

| # | Gap | Severity | Blocks real Korean use? | Class |
|---|---|---|---|---|
| 3.2 | **Search silently under-returns** | 🔴 HIGH | **Yes** | Never ruled (N1) |
| 3.3 | **NFC/NFD path split, live in prod** | 🔴 HIGH (low incidence) | Yes, when hit | **Never thought of** (N2) |
| 3.10 | Skills mirror + byte ceilings | 🟠 MEDIUM | No | Never ruled (N4) |
| 3.7 | Dates/times follow the browser, not the member | 🟡 MEDIUM | No | Cost deferral |
| 3.8 | 266 served error details + notification registry | 🟡 MEDIUM | No | Cost deferral |
| 3.9 | Email is English | 🟡 LOW-MED | No | Cost deferral (N5) |
| 3.11 | Marketing `/ko` + hreflang | 🟢 LOW | No | Cost deferral (design reason) |
| 3.1 | Agent output / unattended language | ✅ none | No | **Ruled** (R2) |
| 3.4 | Korean file names | ✅ none | No | **Ruled** (R4) |
| 3.5 | IME composition | ✅ none | No | **Ruled** (R3) |
| 3.6 | Layout at Korean width | ✅ none found | No | Measured clean |

---

## 5. Proposed build order — cheapest high-value first

**0. Rule the never-ruled (N1–N5). Costs nothing; prevents the expensive mistakes.**
Especially N2, because the fix gets more expensive with every Korean file created.

**1. NFC normalization at the write and read doors.** *Cheapest high-value item.*
One `unicodedata.normalize("NFC", …)` at `parse_file_reference` (the ADR-588 D2 chokepoint every
interop verb already resolves through) and at the upload path, plus a one-time migration of the 2 NFD
rows. NFC is the correct target — it is the web/W3C default and what browsers produce. The gate is
easy and falsifiable: assert `parse_file_reference(NFC) == parse_file_reference(NFD)` for a Hangul
path, and that no `workspace_files.path` differs from its NFC form.
⚠️ Must be driven, not read: re-run the two live NFD rows' lookups before and after.

**2. Search under Korean.** *The one that cannot be retrofitted.*
Now measured (§3.2 Receipt F), so the shape is settled: **keep `to_tsvector('english', …)`, add a
pgroonga index, and OR the two.** pgroonga alone would regress English (`reports` 181 → 103); the
hybrid beats both (181 → 187) while taking the Korean failures 0 → 1. That maps onto
`search_workspace`'s existing strict/loose CTE structure. The honest gate is the smoke-test file's
own question: `삭제` and `본문` must return ≥1, AND an English control must not drop. Also restate
mig 246:84's English-specific comment.
⚠️ **The cost is real and should be the operator's call**: ~90MB of index for ~8.6MB of content
(database 312MB → 402MB) on today's corpus.

**3. `lib/formatting.ts` + the locale argument.** One shared layer, 15 surfaces, ~30 call sites.
Moves `just now` / `Today` / `Yesterday` / `2m ago` into the catalog and threads the member's locale
into every `toLocale*` call. This is the largest *visible* remaining English in a Korean session and
it is a single well-bounded pass ADR-660 already scoped.

**4. Served errors, by code, as they are touched.** Not a big-bang pass — 266 and growing ~13%/week.
The envelope already carries `code`; word it client-side with the served `message` as fallback,
exactly as ADR-660 §10 ruling 1 did for surface titles. Start with the notification-kind registry
(5 labels + 5 descriptions), which is a fixed, small, high-traffic set.

**5. Email.** ~4 templates. The locale is already on the account. Drive one real send to verify
RFC-2047 subject encoding with a Hangul workspace name (§3.9's untested edge).

**6. Marketing `/ko` + hreflang.** Strategic; decide separately, and only with a growth reason.

**Not recommended**: translating skills (§3.10), or tagging files with a language (R8).

---

## 6. For the operator — the rulings I am asking for, not inferring

Per the standing correction (*classify each limit by its stated reason — law / deferral / cost scar /
never ruled — and ask rather than lean on ADR precedent*):

- **N1 — Search.** Is Korean search worth a Postgres extension (`pgroonga`) and an index? Now costed
  rather than guessed: it **works** (0 → 1 on the failures, and the hybrid improves English too), and
  it costs **~90MB of index for ~8.6MB of content**. That ratio is the decision. **Never ruled.**
- **N2 — NFC normalization.** Should `(workspace_id, path)` be normalization-insensitive? I believe
  yes and cheaply, but it touches the substrate's binding unit (ADR-373/286/209), so it is not mine
  to assume. **Never thought of by anyone.**
- **N3 — Unattended language.** Confirm the implemented behaviour as the written ruling: *the
  language of a kept file is its contract's and its sources', never the nearest member's preference.*
  Currently correct by accident of silence; worth making explicit so nobody "fixes" it. **Implemented
  but never separately ruled.**
- **N4 — Skills.** Do kernel skills stay English permanently, and should the index ceiling be
  measured in characters/tokens rather than bytes? The byte ceiling quietly penalises every non-Latin
  language. **Never ruled.**
- **N5 — Email.** Is English email to a Korean member acceptable indefinitely, or deferred? ADR-660
  §8 lists it without a reason either way. **Deferral with no stated reason.**

Items under R1–R8 are **law** and I have not re-argued them. Items in §1.2 are **cost deferrals**
whose reasons still hold; they need scheduling, not re-deciding.

---

## 7. What this audit did NOT do

- **Did not drive all eight surfaces in Korean** — only `/desktop` and the Launcher at 390px. The
  catalog-wide width scan (2330 pairs) is the broader evidence; a per-surface click-pass in Korean
  would be stronger.
- **Did not send a real email** with a Hangul workspace name, so §3.9's MIME-encoding question is
  open, stated rather than answered.
- ~~Did not test `pgroonga`~~ — **DONE 2026-09-21** (§3.2 Receipt F): it installs, it fixes the exact
  Korean failures, it regresses English stemming ALONE so the hybrid is the design, and it costs
  ~90MB of index for ~8.6MB of content. Measured inside rolled-back transactions; production
  untouched. What is still unverified: recall on a Korean corpus larger than 34 rows, and query
  latency under the hybrid.
- **Did not probe the MCP surface end-to-end** under a Hangul path — the NFC/NFD receipt is at the
  `parse_file_reference` chokepoint, not through a live connector call.
- **No Korean speaker reviewed** the linguistic claims about particles and conjugation. The FTS
  behaviour is measured; the grammatical framing is inherited from the 09-16 analysis.
- **Did not change any state.** One device cookie was set and cleared. The two accounts reading
  `locale: "ko"` were written at 23:55 and 00:33 UTC, **before** this session's browser work began at
  00:37 UTC — pre-existing state from the ADR-660 session, deliberately left as found.

---

## 8. Receipts index

| Claim | How measured |
|---|---|
| ADR-660 gate 36/36; voice guard 0 | `python3 test_adr660_the_interface_speaks_korean.py`, `test_voice_no_kernel_nouns_in_copy.py` |
| D5 holds | grep over `lane_runner.py`, `derive_turn.py`, `standing_work.py`, `workspace_paths.py` |
| Korean FTS particle failure | live `psql` read-only, 5 probes + English control |
| Korean search on a real file | `search_workspace('d5b9029b-…', …)` × 7 queries |
| pgroonga available, not installed | `pg_available_extensions` / `pg_extension` |
| Embeddings 8/902 | `count(embedding)` on `workspace_files` |
| 4 Hangul paths, 2 NFC / 2 NFD | `path ~ '[가-힣…]'` + `normalize(path, NFC/NFD)` comparison |
| NFC/NFD lookup miss | 4 `EXISTS` probes on live rows |
| `parse_file_reference` does not reconcile | driven in Python against the real function |
| naming.py 4/4 distinct keys | driven against `path_slug` + `disambiguate` |
| IME: 15 importers, 2 benign stragglers | grep + read of both sites |
| Hangul 10.38px vs Latin 6.35px | `canvas.measureText` in the running app, real font stack |
| 0/17 launcher summaries over 312px | same, against the VOICE §2 budget |
| No clipping at 390px in Korean | driven, `scrollWidth`/`clientWidth` sweep over Hangul text nodes |
| 266 `HTTPException` details / 27 files | grep over `api/routes`, `api/services` |
| Skills index 3716 bytes, 284 headroom | driven against `services.skills.skills_index_section()` |
| Email reads no locale | grep over `account_email.py`, `notifications.py` |

---

## 9. Related

- `docs/analysis/language-support-korean-feasibility-2026-09-16.md` — **read this first**; the
  three-layer cut and the impact ordering are its contribution, and they survive re-measurement.
- `docs/analysis/what-a-thing-is-called-vs-how-its-stored-2026-07-20.md` — the non-Latin naming
  question, closed by ADR-469.
- `docs/adr/ADR-660-the-interface-speaks-korean.md` — the interface layer, complete.
- `docs/adr/ADR-638-the-agent-speaks-the-members-language.md` — REGISTER, not natural language; a
  near-miss on the name, and the seam a language clause would use if one were ever wanted.
- `docs/adr/ADR-469-the-name-is-lifted-the-path-is-a-key.md` — R4.
- `web/lib/shell/submit-key.ts` — R3, with the defect narrated in its own docstring.

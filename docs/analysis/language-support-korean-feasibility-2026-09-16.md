# Language support (Korean) — feasibility and shape

**Date**: 2026-09-16 · **Status**: exploratory, nothing decided, nothing built
**Occasion**: a beta tester asked whether YARNNN could support Korean. The operator asked
for an assessment before beta users arrive, with the explicit constraint: *"if we ever do
decide to implement, I don't want it to be a botch or temporary approach."*
**Scope as re-cut by the operator mid-session**: core product + web app services only.
`content/posts/` (193 files, ~1 MB) is **out of scope** — it needs no language
consideration. The ask is best read as **new-user usability that accommodates language**,
not full product localization.

> This is a jumping-off point for a future session, kept only in case language is ever
> pursued. It is an analysis, not a plan and not an ADR. Nothing here has been ratified.
> Every load-bearing claim carries a receipt; every number was measured on 2026-09-16 at
> `2953499` and will drift.

---

## 0. The one-paragraph answer

Korean support is **three separable layers with wildly different economics**, and the
mistake that would produce a botch is treating them as one project. The *behaviour* layer
(the agent speaking Korean) is nearly free and may already work. The *search* layer is
silently broken for Korean and cannot be fixed later by any translation effort. The *chrome*
layer is ~870 first-session strings with three structural blockers, and is a genuine
project. The correct order is behaviour → search → chrome, which is the reverse of the
order a conventional "add i18n" instinct would pick.

---

## 1. The finding that reframes everything: nothing pins the agent to English

Grepped the entire composed frame — `PARTICIPANT_*` in `api/services/workspace_paths.py`,
`build_lane_conventions` in `api/services/lane_runner.py`, the app postures in
`api/services/authoring.py` and `api/services/apps/*.py`.

**There is no "respond in English" instruction anywhere in the codebase.**

```
grep -rniE "in english|write in english|respond in english|language" \
  api/services/workspace_paths.py api/services/lane_runner.py api/services/authoring.py
→ one unrelated hit (a docstring about plain-language naming mechanics)
```

Modern models mirror the user's language by default. So a Korean member who types Korean
today **very likely already gets Korean back**, with no work at all.

⭐⭐⭐ **THE FIRST THING A FUTURE SESSION MUST DO IS VERIFY THIS EMPIRICALLY.** One Korean
message into a live lane answers it. If it holds, the bulk of what the tester is asking for
already exists, and the expensive work drops down the priority list. This assessment was
written *without* that probe having been run — it is the single largest open unknown here,
and it is cheap to close.

⚠️ Emergent ≠ guaranteed. `LANE_MODELS` (`api/services/lane_runner.py:74`) spans Anthropic,
OpenAI and Google. Language-mirroring is a model behaviour, not a product guarantee, and it
can differ per engine and drift per model revision. That is the argument for D1 below even
if the probe comes back green.

---

## 2. The architecture already has the right seam

ADR-638 — *the agent speaks the member's language, not ours* — is a near-miss on the name.
It is about **register** (jargon vs plain words), not natural language. But the mechanism it
built is exactly the one a language preference wants:

- `PARTICIPANT_REGISTER` (`api/services/workspace_paths.py:521`, 672 chars) is composed into
  the lane frame by `build_lane_conventions` as `## Talking to {member}`.
- The frame **already interpolates the member**. A language clause is a sibling of the
  register clause, in a structure built to carry precisely this.

`api/test_voice_no_kernel_nouns_in_copy.py` already draws the distinction the whole problem
turns on, in its own SCOPE docstring: **rendered copy** vs **prompt text**
(`frame_paragraph` is allowlisted as "a prompt, not copy"). That is the same cut as
behaviour-layer vs chrome-layer. The codebase understands this seam; it just has not had to
apply it to language.

### Storage: no new table needed

`member_state` is live — `(workspace_id, principal_id, key, value jsonb)`, 23 rows on prod.
It is the established home for exactly this class of per-member preference; **the member's
engine pick already lives there** (`api/services/lane_runner.py:515`).

⚠️ `member_state` is **service-role-only** (`api/services/agent_connectors.py:53`) — a
language preference needs an API-mediated door, not a direct client write. The engine-pick
precedent already works this way; follow it.

⭐ **Language is a MEMBER preference, never a workspace column.** The kernel says workspaces
have no types (ADR-222) and a workspace is one multi-principal commons (ADR-373/378). Two
members of one workspace must be able to read the same Korean file with different UI
languages. Keying on `principal_id` is the decision that is expensive to reverse later;
everything else is mechanical. **This is the ruling worth writing down even if no code is
ever shipped.**

---

## 3. Search is broken for Korean — measured, not theorised

`search_workspace` hardcodes `'english'` in **six places** in
`supabase/migrations/246_search_covers_the_name_and_degrades.sql` (lines 54–56, 74, 77, 84,
87–88).

Probed live via `scripts/db/run-migration.sh --dry-run` (read-only, rolled back), 2026-09-16:

```
to_tsvector('english', '3분기 매출 보고서입니다. 매출이 증가했습니다.')
  → '3분기':1 '매출':2 '매출이':4 '보고서입니다':3 '증가했습니다':5

plainto_tsquery('english', '매출')                              → '매출'
to_tsvector('english','3분기 매출 보고서') @@ plainto_tsquery(…)  → true
to_tsvector('english','매출이 증가했습니다') @@ plainto_tsquery(…) → FALSE   ⭐
```

The English stemmer whitespace-splits Korean and stems nothing. Korean is agglutinative —
particles (이/가/은/는/을/를) attach directly to the noun. **So a search finds a word only
when it happens to appear without a particle, which in real Korean prose is the minority
case.** Search does not error; it silently returns fewer rows.

A tester reports this as *"search is bad"*, never as *"search is broken"*. That is how it
would eat weeks.

Two aggravating facts:

1. **Postgres ships no Korean text-search config.** All 29 available, enumerated live:
   `simple, arabic, armenian, basque, catalan, danish, dutch, english, finnish, french,
   german, greek, hindi, hungarian, indonesian, irish, italian, lithuanian, nepali,
   norwegian, portuguese, romanian, russian, serbian, spanish, swedish, tamil, turkish,
   yiddish`. No Korean, no CJK at all. The fix is a `simple`-config bigram/n-gram approach
   or an extension (e.g. pg_bigm / pgroonga, availability on Supabase unverified) — not a
   config swap.
2. **The semantic fallback is effectively dead**: `7 of 774` rows in `workspace_files` have
   a non-null `embedding`. Lexical FTS is all there is. (Measured 2026-09-16.)

⚠️ Latent second defect: the OR-degradation path at line 84 rewrites `plainto_tsquery`
output by string-replacing `' & '`, justified in a comment reading *"english lexemes cannot
contain the separator."* That premise is about English specifically and should be re-checked
under CJK input before anyone trusts the degradation path.

**This is the layer that cannot be retrofitted by a translation pass**, which is why it
outranks the chrome despite being invisible in session one.

---

## 4. The chrome: sized, and larger than it looks

Counts are **distinct** strings across `web/app/(authenticated)/` + `web/components/`,
excluding `admin/`, marketing routes and the blog. Measured 2026-09-16.

| Scope | Distinct strings | Files |
|---|---|---|
| **First-session reachable** | **870** | 73 |
| Narrowest "first ten minutes" (auth + shell + chat + files) | ~440 | — |
| All authenticated app copy | 1,581 | 177 |

⭐ **The first-session set is 55% of the entire app's copy.** There is no small "onboarding
slice" to translate — for this product the onboarding surface *is* the product. Any plan
premised on "just do the new-user bits first" should be checked against this number.

### Per-surface

| Surface | Distinct | Note |
|---|---|---|
| Files | 222 | `files/page.tsx` (38) + `web/components/workspace/*` |
| Text | 167 | `page.tsx` = 0 |
| Chat | 165 | 108 in `chat-surface/*` + 57 from tool labels |
| Settings | 141 | `settings/page.tsx` (53) + `web/components/settings/*` |
| Notifications | 63 | |
| Shell / desktop | 58 | `Desktop.tsx` 6, `Launcher.tsx` 18, `UserMenu.tsx` 22 |
| Reach | 52 | |
| Auth / sign-up | 25 | the smallest, highest-stakes slice |
| Agents | 22 | |

`chat/page.tsx`, `text/page.tsx`, `agents/page.tsx` all carry **zero** strings — they are
registry stubs. **All copy lives in `web/components/`**, which is where any extraction pass
should point.

### Length distribution (first-session set: 870 strings, 22,724 chars, median 17)

| Bucket | Count | Share |
|---|---|---|
| under 20 chars | 490 | 56.3% |
| 20–60 | 299 | 34.4% |
| 61–120 | 66 | 7.6% |
| over 120 | 15 | 1.7% |

⭐ **Bimodal, and the two modes carry opposite risks.**

- The **56% short tail** (median 17: *"Add files"*, *"New folder"*, *"Sign out"*) is cheap
  to translate and is a **layout** risk. These sit in dock labels, icon tooltips, context
  menus and `WindowFrame` title bars — fixed-width slots.
- The **~9% long tail** (81 strings over 60 chars) is ~35% of character volume and is
  *exactly* what a confused new user depends on: the `/desktop` welcome, every empty state,
  every auth error. Losing nuance here costs more than the other 790 combined. The auth
  form's own comments record that a bad error message nearly lost a beta user.

### Existing abstraction — partial, domain-scoped, not a copy module

Four label modules exist, each for one vocabulary:
`web/lib/proposal-labels.ts` · `web/components/chat-surface/toolLabels.ts` ·
`web/components/authoring/structureLabels.ts` · `web/lib/cta.ts`. Plus a **second,
deliberately unmerged** tool map at `web/lib/utils.ts::TOOL_DISPLAY_NAMES` (the ADR-441
altitude seam; the two disagree in spelling for shared names, documented in `toolLabels.ts`'s
own header). Everything else is inline. `web/lib/` has **no** strings/copy/i18n module.

---

## 5. The highest usability-per-string defect: the bilingual transcript

`web/components/chat-surface/toolLabels.ts` renders the transcript's action steps
**client-side, in fixed English**:

```ts
ReadFile:  { doing: 'reading a file in your workspace', did: 'read a file', withSubject: 'reading' },
WriteFile: { doing: 'writing a file in your workspace', did: 'wrote a file', withSubject: 'writing' },
```

So a Korean member writes Korean, the agent replies in Korean — and **in between, the stream
reads "writing a file in your workspace."** The conversation is bilingual against itself.
This is the thing that makes an app feel broken rather than merely untranslated.

⚠️ **This is NOT a one-day string swap, contrary to a first reading.** 23 entries produce 57
distinct strings, and they are composed at runtime as verb *fragments*:
`sentenceCase(\`${withSubject} ${path}\`)`. English word order is baked into the
composition. Korean is SOV — `"reading" + "Documents/memo.md"` inverts. The composition
model needs rebuilding, not the strings replacing.

---

## 6. Slot budgets are measured in pixels, and Hangul is full-width

`docs/design/VOICE-AND-TONE.md` §2 defines budgets in **measured pixels**, not characters —
launcher summary **≤ 312 px at 12 px system font** on a 390 px phone, verified with
`canvas.measureText`. That discipline is unusually well-suited to catching this, because the
spec already insists budgets are measured rather than guessed.

Latin advance ≈ 6 px at 12 px; Hangul is full-width ≈ 12 px.

| | chars that fit in 312 px |
|---|---|
| Latin | ~52 (spec says ~48 in practice) |
| Korean | **~26** |

Korean translations run ~0.5–0.7× the character count of English but ~2× the width per
character — net **~1.0–1.4× the pixels**. A 47-char English summary lands at **282–395 px**:
fine at the optimistic end, **over budget** at the pessimistic end.

Bounded, though: **21 surface titles + 21 summaries, served from one file**,
`api/services/kernel_surfaces.py`. Every under-budget summary is currently ≤ 50 chars. Any
language pass must re-measure per language rather than trusting the English receipt.

---

## 7. Three structural blockers — fix before any extraction

None of these is translation work. All three are refactors that improve the code regardless
of whether language is ever pursued, and doing them early makes a later pass mechanical.

1. **Mid-sentence runtime concatenation.** `web/components/notifications/ActivityLedger.tsx`
   builds `'Nothing here' + (' under these filters' | ' yet') + ' — …'`. This cannot survive
   translation — Korean word order alone breaks it. Must become whole messages per branch.
   The composer placeholder in `LanePanel.tsx:1836` is a 5-way conditional, 3 branches
   interpolating a name; same problem.
2. **`toolLabels.ts` runtime verb composition** — see §5.
3. **Copy passed as props.** `AuthForm` takes `loginSubheading` / `signupSubheading` /
   `submitLabel` from its caller (the same component serves `/mcp/auth` with different
   copy). Also `WorkspacePicker`'s `emptyMessage`, `LanePanel`'s `emptyState` node. Keys
   belong to the **caller**, not the component.

Plus: `"Use at least {n} characters."` is interpolated against `MIN_PASSWORD_LENGTH` — a
real message format with plural handling is needed, not a flat key map.

---

## 8. Other seams a future session will trip over

- **`HOME_ALIASES` is gate-locked to prompt prose.** `{"Documents": "operation", "Downloads":
  "inbound"}` at `api/services/workspace_paths.py:992`, bidirectional with the inverse
  derived so the two cannot diverge. `api/test_adr588_folder_markers_and_home_aliases.py:203`
  asserts every key appears **verbatim** inside `PARTICIPANT_FILESYSTEM_MODEL`, and line 222
  pins the key set to exactly `{"documents","downloads"}`. A Korean told-name does not drift —
  it **fails the gate outright**. That is good: the gate forces the decision into the open.
  ⚠️ A told-name must never reach a composed path — the PATCH door runs no `HOME_ALIASES`
  pass, and Text's create modal already shipped that bug once (phantom `/workspace/Documents/`
  root). Ten more display names live at `workspace_paths.py:257–377`, with an English
  `.title()` fallback for unknown roots.
- **The prompt byte ratchets are a latent English assumption.** `INDEX_CEILING = 3_400`
  measured at 3,327 — **~70 bytes of headroom** — and `UNBOUND_INDEX_CEILING = 4_000`
  (`api/services/skills/__init__.py`). UTF-8 Hangul is **3 bytes/char** vs 1 for ASCII. If
  skills are ever translated these ceilings blow immediately, and
  `api/services/skills/__init__.py:141` requires A/B evidence to raise one. A byte ceiling
  should arguably be a **character or token** ceiling; that is a real design question, not a
  number to bump.
- **`ensure_kernel_skills()` writes English into every workspace.** 12 SKILL.md files
  (~29,885 chars) mirrored into `system/skills/{slug}/SKILL.md` on every workspace-state read
  (`api/services/skills/__init__.py:690`, called from `api/routes/workspace.py:3911`).
  Genesis itself is pure (ADR-414 D4 — `workspace_init.py` seeds only machine YAML), but the
  skills mirror quietly reintroduces English into the member's own filesystem. The voice
  guard does not scan SKILL.md at all.
- **Server-side prose far exceeds the voice guard's roster.** The guard covers a
  hand-maintained 5-file list (`notifications.py`, `narrative.py`, `kernel_surfaces.py`,
  `reach_status.py`, `account_email.py`). Outside it: **235 `HTTPException(detail=)` strings
  across 27 files** and **337 returned prose fields across 22 files**. Every error a Korean
  member sees stays English unless these move behind a code+params shape. Argues for doing it
  as errors are touched, not as a big-bang pass.
- **Zero locale plumbing exists.** No i18n dependency in `web/package.json`; no message
  catalog; no locale column in any migration; no `Accept-Language` read on any inbound
  request; `<html lang="en">` hardcoded at `web/app/layout.tsx:23`. The only locale literal
  in the entire product is `locale: "en_US"` in OpenGraph metadata
  (`web/lib/metadata.ts:104`). `Intl`/`toLocaleString` are used for dates/numbers but never
  passed an explicit locale.
- **Substrate content is already language-neutral and should stay that way.** Files are bytes
  with paths; Postgres is UTF-8. Korean content *stores* fine today. ⭐ Resist any temptation
  to tag files with a language — that would put a type where the kernel refuses one.

---

## 9. If it is ever pursued — the order, and why

Impact order, not alphabetical. The conventional instinct ("pull in next-intl, extract the
strings") starts at step 5 and is the botch: it spends the expensive effort on the layer a
new user notices least, while the transcript still reads half-English and search still
under-returns.

0. **Probe whether the agent already speaks Korean** (§1). Cheapest, highest-information.
   Everything below is re-prioritised by the answer.
1. **Write the ruling, not the code**: language is a per-member preference on `member_state`,
   keyed by `principal_id` (§2). Costs nothing; prevents the expensive-to-reverse mistake.
2. **The language clause + `member_state` key.** Makes step 0's behaviour *guaranteed* rather
   than emergent across a multi-provider roster.
   ⭐⭐⭐ **A/B IT — DO NOT ASSUME IT TOOK.** ADR-638 §4 records that ADR-365's first,
   *vague* directive was ratified, shipped, and then **falsified** (2.72 vs 2.60 jargon per
   1000 chars — noise). What worked was naming a concrete bad→good failure per rule. The rig
   exists: `api/scripts/operator/probe_adr638_register_ab.py`.
3. **Fix the three structural blockers** (§7). Good hygiene independent of language.
4. **Search** (§3). Before Korean users are taken seriously — it is the one that degrades
   silently and cannot be retrofitted.
5. **The 21 launcher pairs**, re-measured at Korean width (§6).
6. **Empty states** — ~56 strings across 33 components; disproportionate value for someone
   who does not yet know what the product does.
7. **The 870-string first-session pass** with a real message-format library. Its own project,
   properly resourced. Not a pre-beta task.

⭐ **The honest bottom line for a beta decision**: if only one thing can be done, do the
**behaviour** layer and leave the chrome English. *A Korean user with a Korean-speaking agent
and an English UI is a coherent product.* A half-translated UI with English fragments
composed mid-sentence into Korean text is not — and that is precisely what a rushed pass
produces.

---

## 10. What was NOT done here

- **The Korean-lane probe was never run** (§1). Largest open unknown in this document.
- No Korean speaker reviewed any of the linguistic claims about particles, word order, or
  translation length ratios. The FTS behaviour is measured; the ratios are estimates.
- Korean glyph width (~12 px at 12 px font) is **assumed full-width, not measured** with
  `canvas.measureText` against the app's actual font stack — unlike the English budgets,
  which were. §6's conclusion should be re-derived properly before anyone acts on it.
- Availability of Korean-capable FTS extensions on Supabase was not checked.
- **The tester was never asked what they actually meant.** *"Korean language support"* could
  mean *"I want to write documents in Korean and have the agent understand them"* — which
  largely works today, modulo search — or *"I want the buttons in Korean."* Those are
  opposite ends of the cost curve, and the cheap one may be the one they care about.
  **Ask before building anything.**

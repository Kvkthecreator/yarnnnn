# ADR-575 — The document hears other principals before it collides with them

**Status**: Accepted + Implemented (2026-08-18)
**Supersedes in part**: ADR-572 D5, D7, D10 (the conflict-banner lineage)
**Related**: ADR-209 (attributed substrate), ADR-570 (the prose write path), ADR-574 (Text is the text app)

## 1. What the operator saw

One screenshot of the deployed surface carried three claims that cannot all be
true at once:

| The surface said | Actually true |
|---|---|
| *"Someone else revised this document while you were editing"* | there had been a 409 |
| **`Editing…`** — copy chosen to mean *nothing is at risk* | autosave was **suspended**; nothing would save until the member chose |
| **`No revisions yet.`** | **four** revisions existed |

Measured against production, not inferred —
`/workspace/seulki/babo-song-concept.md`:

```
713108b0…  operator              2026-08-17 09:11:40
b2ae1eec…  operator              2026-08-17 08:32:20
62d1bbf5…  operator              2026-08-17 08:09:54
679987fc…  yarnnn:mcp:claude.ai  2026-08-17 04:24:41   ← the peer write
```

The operator's diagnosis was right and better than mine: *"most likely… the way
the autosave to features and thus artifact mutation is handled."*

## 2. The two defects, and their shared root

**Defect 1 — a successful save never refreshed the revision state.** `commit()`
advanced `baseHead`, set `baseline`, flashed `Saved`, and never bumped
`reloadKey`. `headRevision` is fetched only inside `useFileLoad`'s effect, keyed
on `[path, reloadKey, withRevision]` — so `LAST EDITED` showed whatever was true
**at mount, forever**.

The structural read: **every mutation path bumped `reloadKey` except autosave**
— rename, conflict-discard, the lane's `onArtifactWrite`, the error retry all
did. Autosave was the last writer added (ADR-572 D10 deleted the Save button)
and it inherited the CAS and queue discipline **without inheriting the refresh
discipline**. Same shape as ADR-568's *a new writer must inherit the lane's
rule*.

**Defect 2 — the banner outlived its own meaning.** The conflict state also
*gates* autosave (`if (!dirty || conflict) return;`), so during a conflict the
header fell through to `dirty ? 'Editing…'` — a string whose comment says it is
deliberate because *"nothing is at risk"*. During a conflict something is.

## 3. The decision: subscribe, don't merge

**The conflict dialog is not a feature. It is the cost of not listening**, made
visible to the member and handed to them as a decision.

Benchmarked against Notion, Google Docs, Figma and Linear before choosing. The
findings that mattered:

- **Notion never shows a "choose whose version wins" dialog for prose.** Text
  merges automatically; only *non-text* properties are last-write-wins, and
  Notion says so plainly in its help centre.
- **"Last edited by" is pushed, not polled.** Rendering a record *subscribes*
  the client to it; MessageStore pushes a **version number** on commit and the
  client answers with a targeted refetch (`syncRecordValues`). **The push is an
  invalidation signal, not content.**
- **Notion shows no persistent save status online at all** — a sync indicator
  appears only offline, where the guarantee is genuinely in question. Google
  Docs is the opposite (always-visible "All changes saved"). Ours should mean
  one thing at a time.

### 3.1 The claim ADR-572 D7 got wrong

D7 justified the banner: a 409 *"cannot be re-applied without inventing a
merge."* That is false about the medium. **Merging prose is the most solved
problem, not the least** — Jupiter/OT (Google Docs) and sequence CRDTs (Yjs,
Automerge, Loro) all operate on **flat character sequences**, which is exactly
what a `.md` is. Blocks are not a prerequisite for merging text; they add the
*harder* problem (tree moves — the part Notion needed "offline trees" for).

**The fourth instance of this arc's signature error**: a constraint read as a
ceiling. Recorded, and deliberately **not acted on** — merge is a real option
(ADR-575 §6) but it was not this decision.

### 3.2 What a block model genuinely buys, which we cannot have

Stated so it is not re-litigated. From Figma's published model: the server
tracks the latest value per *property* per *object*, so a conflict requires
*same property, same object*. **A markdown string is one object with one
property** — every concurrent edit is a same-property collision by
construction. Blocks also give **stable anchors** (a UUID survives rewriting;
a string offset does not).

So we cannot have *edits that never meet*. We can absolutely have *edits we
hear about before they meet*, and that is what shipped.

## 4. What shipped

**D1 — the substrate is published to Realtime** (migration 240). Verified
against production first: the `supabase_realtime` publication carried exactly
`chat_sessions` and `session_messages`. A subscription on file revisions would
have delivered **nothing while reporting `SUBSCRIBED`** — the failure mode that
reads as *"realtime is wired and quiet"*.

RLS is **not** relaxed. `"Members view workspace file versions"` is
workspace-scoped (owner ∪ active grants) and Realtime evaluates it per
subscriber. **Publishing a table widens WHEN a member finds out, never WHAT
they may see.** Falsified as a real principal in a `ROLLBACK` transaction:

```
total in table            6 workspaces / 1758 revisions
member 2be30ac5… sees     2 workspaces / 1517 revisions   ← owner ∪ one grant
principal with no grants  0                               ← the control
```

The migration also **refuses to publish if RLS is off** — publishing to a
replication slot is precisely the moment a disabled RLS flag stops being latent
and starts broadcasting every workspace's revision feed.

**D2 — `useFileRevisionsRealtime`**, the second tenant of the primitive
`use-session-messages-realtime.ts` explicitly describes ("same primitive
reusable… each gets its own hook against its own table"). Filters **server-side**
on `path=eq.…` — filtering in the callback would ship every workspace's
revisions to every open editor and discard them locally.

⭐ **The own-write rule.** Every autosave INSERTs a revision that returns down
this channel. Without an echo filter the surface would announce the member's own
typing as a peer edit ~2s after every pause — *the document accusing you of
editing behind your own back*. The editor records the revision ids it authored
and drops their echoes.

**D3 — the refresh is revision-only.** A save changes the *revision*, not the
member's text, so it calls `refreshRevision()` rather than bumping `reloadKey`.
The blunt reload re-runs `getFile`, which re-fires the consumer's
`setText(content)` effect — and a keystroke landing during that refetch is
destroyed. That is ADR-572 D12's stale-prop shape, **which has already shipped
once in this app**, so the narrow path is not a preference.

**D4 — a peer write branches on unsaved text.** No unsaved text → reload
silently; the member had nothing at stake and now sees the current document.
Unsaved text → **notify, do not touch the document**, because reloading over
unsaved text discards their typing. Conflating those two is what made the old
banner confusing.

**D5 — the header says one thing at a time.** `Paused — resolve above` while a
conflict suspends autosave; `Editing…` keeps its original meaning.

**Whole-document CAS is unchanged.** The 409 still exists and still asks. It
becomes **rare and informed** instead of routine and surprising.

### D6/D7 — Subscribed, filtered, and silent (found by driving production)

**The click-pass found the feature did not work at all**, and neither cause was
visible to 232 green checks, `tsc`, or `next build`.

The channel joined correctly:

```
["1",null,"realtime:file-revisions:%2Fworkspace%2FDocuments%2Fadr572-click-pass.md",
 "system",{"message":"Subscribed to PostgreSQL","status":"ok", ...}]
```

with the right server-side filter. A peer then wrote through the real API; the
revision row landed (`b5da51e9…`, confirmed in `workspace_file_versions`).
**No INSERT frame was ever delivered — only Phoenix heartbeats.**

**Three theories were refuted by measurement before the real ones were found**,
which is the part worth keeping:

1. *"The table isn't published"* — it is; migration 240 verified the catalog.
2. *"RLS forbids the subscriber"* — it does not. As the real principal, in a
   `ROLLBACK` transaction, `SELECT … WHERE id=b5da51e9…` returns **1**.
3. *"The policy subquery is too complex"* — `session_messages`' working policy
   also subqueries another table and delivers today.

**D6 — `REPLICA IDENTITY DEFAULT`** (migration 241). Realtime re-checks RLS
against the row **as reconstructed from the WAL record**. Under `DEFAULT` that
record carries only the **primary key**, so every other column reads NULL during
the check. This table's policy keys on `workspace_id` — not the PK — so the
predicate could never be satisfied and the row was dropped silently.
`session_messages` was unaffected because its policy keys on `session_id`, which
its own record carries. ⭐ Note this is not a general "set FULL on realtime
tables" rule: it is required exactly when the **policy references a column
outside the replica identity**.

**D7 — the socket carried no user JWT.** Realtime evaluates RLS using the token
the **socket** holds, not the one the REST calls hold. Nothing called
`realtime.setAuth()`, so the socket connected with the anon apikey, `auth.uid()`
was NULL, and rows were dropped while the channel still reported `SUBSCRIBED`.
Measured directly — the `phx_join` frame carried no `access_token`:

```
["1","1","realtime:file-revisions:…","phx_join",
 {"config":{"postgres_changes":[{"event":"INSERT","schema":"public",
  "table":"workspace_file_versions","filter":"path=eq./workspace/…"}],...}}]
```

⭐⭐⭐ **The omission was latent in `use-session-messages-realtime.ts` first** —
the hook this pattern was copied from, whose policy also resolves `auth.uid()`.
So it is fixed **at the source**, not only in the new tenant. The
`session_messages` subscription was very likely never delivering in production
either; the surrounding code refetches on chat-turn, which would have masked it.

In the file-revisions hook the join is **sequenced behind the session read**.
Fire-and-forget beside `subscribe()` is a race whose losing side is the silent
one: it resolves from cache locally and fails on a cold load.

**The lesson, stated plainly: publishing a table is necessary and not
sufficient.** Migration 240's own header warned about a subscription that
reports `SUBSCRIBED` and delivers nothing — and did not prevent it. **A gate
asserting the wiring cannot see whether a byte ever crossed the socket.**

## 5. Verification

```
cd api && python3 test_adr571_text_app.py            # 232/232, SCRIPT-STYLE
cd api && python3 -m pytest test_lane_artifacts.py test_adr570_member_prose_door.py -q   # 19
cd api && python3 test_adr562_app_owned_config.py    # GREEN
node web/lib/file-types/__gate_adr514_d2.mjs         # 41/41, from REPO ROOT
cd web && node_modules/.bin/next build               # 171/171, tsc clean
```

§19 adds 11 checks, **each falsified**. Two worth keeping:

- ⭐⭐⭐ **19g catches a temporal-dead-zone throw that `tsc` passes clean.**
  `ownRevisions` is written by `commit` and must be declared above it; moving
  the declaration below reproduces a runtime throw on first save with a **green
  typecheck and a green build**. Verified by running `tsc` against the broken
  form — exit 0.
- ⭐⭐ **19j passed its own falsification** (ninth occurrence this arc). It
  required `pg_publication_tables` + `RAISE EXCEPTION` anywhere in the
  migration; deleting the whole publication-verify block left both tokens in the
  **sibling RLS block**. It now extracts the verify block and asserts over that.

## 6. Not done / named so it is not re-discovered

- **Three-way prose merge on 409.** We hold the common base (`baseline`), so a
  standard three-way merge would resolve non-overlapping edits silently, as
  Notion does for text. §3.1 establishes this is *possible*, contra D7. Deferred
  as its own decision — it needs a merge library, its own gates, and a rule for
  what "overlapping" means in prose.
- **Live presence / shared cursors / CRDT.** Would change the write path, the
  ADR-209 attribution model (revisions are signed; a CRDT streams ops) and the
  `.md` serialization thesis. Almost certainly wrong for a file whose product
  claim is byte-for-byte connector round-trip.
- **Other surfaces.** Docs, Files and Studio have the same collision-first
  discovery. The hook is deliberately generic enough to adopt; nothing here
  assumes Text.

## 7. Falsifiers / click-pass (OWED)

1. Open a document in two browsers as **two different principals**. B saves →
   A's `LAST EDITED` updates **without A reloading**, and A's document reloads
   silently because A had not typed.
2. A types (unsaved), then B saves → A sees *"B saved a new version… your text
   here is untouched"*, A's text is **still there**, and `Keep writing` dismisses
   it.
3. A saves normally → **no** peer-edit notice appears (the own-write echo rule).
4. Force a real 409 → the header reads `Paused — resolve above`, and both exits
   still work.
5. Watch the network tab during ordinary typing: one WebSocket, and **no**
   `getFile` refetch per save.

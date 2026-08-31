# Lisa cleanup — the last member-agent, removed in full

**Date**: 2026-08-31 · **Operator-directed**, executed against production
**Workspace**: `d5b9029b…` (kvkthecreator@gmail.com)
**Context**: surfaced by the ADR-624 click-pass, which noticed
`/workspace/agents/lisa/_agent.yaml` still present under the newly-legible
`agents/` root.

Lisa was the only member-authored agent ever created (2026-07-16), under the
model **ADR-599 D2 deleted** ("Make one" / `_agent.yaml` / `based_on`). Her
machinery has been gone since 2026-08-24; this removes the residue.

---

## Correction to the click-pass report

The ADR-624 finding said the manifest "still exists in production substrate."
**Imprecise.** It was already `lifecycle='archived'` — ADR-599 D2 had performed
the file-lifecycle act exactly as its text said ("Lisa's manifest is archived in
the substrate — the file lifecycle act, never a row deletion"). It was in Trash,
not live. The corrected statement: ADR-599 D2 did its job; what remained was
archived residue plus two cast rows it never claimed to touch.

---

## The full footprint, as measured

| # | Artifact | State found | Disposition |
|---|---|---|---|
| A | `/workspace/agents/lisa/_agent.yaml` | `archived`, 2 revisions | **hard-deleted** (row + both revisions) |
| B | cast row on conv `bd4bdfb3` (**0 messages**) | active, orphan | **deleted** |
| C | cast row on conv `26ab6ad3` (**53 messages**) | active | **KEPT** |
| D | avatar `inbound/uploads/operator/image.png` | `active` | **archived** (trash-not-erase) |

Code references to "Lisa" across `api/` and `web/` (≈40) are **comments, test
fixtures and historical receipts** — the record of *why* code exists
(`addressing.py`'s "@lisa can you hear me" bug, migration 217's avatar-upload
receipt). Zero live wiring. **Not touched**: rewriting them would falsify the
trail that justifies the code.

---

## Why C was kept (the one real constraint)

Conversation `26ab6ad3` holds **53 real messages**, including a genuine RLS-bug
receipt. Deleting Lisa from its cast would leave the transcript's replies
unattributable to any participant — a history rewrite at the cast layer, to no
benefit.

It costs nothing to keep, because **ADR-599 already designed for this**:
`resolve_agent('lisa')` returns `None`, and `_cast_roster` simply omits an
unresolvable slug. Verified live: the resolver returns `None`; the roster drops
it. The same conversation also carries `sonnet` — another ADR-599-deleted slug —
so this is a **general pattern, not Lisa-specific**, and a one-off purge would
not have addressed it anyway.

---

## Why A was hard-deleted, against two standing rules

This is the part that needs justification on the record, because it is an
**exception**, not the rule:

- **ADR-599 D2** chose archive-not-delete ("the file lifecycle act — never a row
  deletion; ADR-209 history intact").
- **ADR-209** holds that revision history is not deleted.

The operator directed a full removal. Both rules exist to protect **the commons
and its walkable history** — and this file is the manifest of an agent model
that no longer exists, in a folder ADR-624 has just made member-visible, whose
only remaining function was to describe a being nothing can instantiate. Its
`based_on: critic` names a being deleted in the same ADR.

**The precedent is deliberately narrow**: a retired *model's* own manifest, with
zero live references, removed at the operator's explicit instruction. It is not
a precedent for deleting authored content, and ADR-209's rule is unchanged.

**Pre-image preserved in this record** (the honest substitute for the deleted
history):

```yaml
# /workspace/agents/lisa/_agent.yaml  (deleted 2026-08-31)
based_on: critic
name: Lisa
tone: |
  Warm and direct. Skips preamble. Calls me Kev.
avatar: /workspace/inbound/uploads/operator/image.png
```

| revision | author | message | created |
|---|---|---|---|
| `fb26ae09` | operator | made an agent: Lisa | 2026-07-16T00:26:44Z |
| `f0d683b5` | operator | updated an agent: Lisa | 2026-07-16T04:02:28Z |

---

## Execution + verification

Deletion order was forced by two FKs and is worth recording: **file row first**
(it holds `head_version_id` → `f0d683b5`), then the **child revision**, then the
**parent** (`parent_version_id` chain). Pre-checked that nothing outside the
chain referenced either id (`heads=0 parents=0` for both).

Post-state, all verified:

- `workspace_files` matching `%lisa%`: **0**
- `workspace_file_versions` matching `%lisa%`: **0**
- cast rows `agent_slug='lisa'`: **1** (the preserved 53-message room)
- avatar: `lifecycle='archived'`
- preserved conversation: **53 messages intact**, cast = human + `sonnet` + `lisa`
- emptied conversation `bd4bdfb3`: cast = human only

**Referential integrity, paged over all 1,740 workspace revisions: 0 dangling
`head_version_id`, 0 dangling `parent_version_id`.**

⚠️ **A probe defect worth recording**: my first integrity check reported *100
dangling heads and 236 dangling parents* and looked like catastrophic damage. It
was the probe — PostgREST's default page size truncated the id set I was
comparing against, so most live ids read as missing. Re-run with explicit
paging, the answer is zero. **A referential-integrity check whose reference set
is silently truncated reports the truncation as corruption.** Page it, or assert
the specific ids.

## Gates

`test_adr624` GREEN · `test_agent_registry` 120/120 · addressing/cast gates 38
passed. One pre-existing failure, **confirmed not this change's** by checking
out `2d05512` (before any ADR-624 work) and reproducing it:
`test_adr502_503_gate::test_the_responder_comes_from_the_cast` asserts
`lane_meta.get("agent")` inside the `_turn_stream_response` slice, while the
string lives at `lanes.py:341` in a helper outside that slice — a slice-scoped
assertion reading the wrong region, unrelated to Lisa or to the DB.

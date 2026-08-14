# Session handoff — 2026-08-14 (multi-agent conversations: addressing → surface → default)

`origin/main` clean. Started as "image generation is broken"; became the
multi-principal chat arc. Everything below is pushed and deployed.

> **The prior handoff (ADR-561 + ADR-563, data-handling honesty) is ABSORBED.**
> Its owed items live in memory (`project_adr561_marketing_honesty_audit`,
> `project_adr563_mcp_scope_enforcement`) — chiefly `workspace_blobs USING(true)`
> and a narrow-scope MCP client. Nothing from it is stranded here.

## 1. What landed

| Commit | What |
|---|---|
| `346f19a` | Image gen 403'd: the binary lane needs the SERVICE client (`workspace-cas` is service-role-only, mig 219) — and the call was never metered |
| `12ab92e` | Image path: placement by MEANING, not the pre-ADR-395 `uploads/` legacy root |
| `54b32bc` | **ADR-495 D3 addressing, finally built** — `@lisa` routes the turn |
| `5ce5d99` | The multi-agent surface — a turn is authored by a PRINCIPAL |
| `0f24405` | A person has a name — one resolver; `member-2abf3f96` was a UUID leak |
| `f25b977` → `b82d7b3` | The default recipient, made visible → then made QUIET |

## 2. The finding worth carrying

**A model that denies what the UI shows may be telling the truth.** Thinker
answered "there's no agent by that name … that I can see" about a cast-mate the
header displayed. It was correct: `_CONVENTIONS_FRAME` named exactly two
entities and `build_lane_conventions` had no cast parameter. Not a
hallucination — a missing injection point. The tell was the scoped hedge.

**Species law survives in the renderer.** ADR-495 made the cast species-blind in
substrate; `LanePanel`'s `foreign` still required `role === 'user'`, so an
assistant could never be "someone else". Twelve symptoms, one line.

**Ask what the default means before building the next feature.** I shipped
addressing, then the surface, then offered a *concurrency* decision — while the
no-mention path (what almost every message is) was undesigned. The operator
stopped me. Then I over-corrected into a standing instructional banner, and they
stopped me again. Both catches were right.

## 3. Owed

- **Click-pass the quiet version** (`b82d7b3`): placeholder should read
  "Message Thinker…"; Details should mark one agent "Replies when you don't say
  who". Nothing was driven after that commit.
- **`DuplicateFile` is path-addressed but NOT gate-queueable** → its path branch
  is unreachable, so the verb gates on nothing. Found while re-deriving
  `test_adr307_permission_taxonomy`; named there as a self-checking exemption.
  **ADR-514's to close, not this arc's.**
- **Realtime is still a 15s poll.** The gate is now correct (any other
  principal, not "another human"), but the mechanism is unchanged; real
  subscriptions are blocked on session RLS being creator-scoped.
- **Deferred, deliberately**: concurrent turns (needs an ADR — ADR-495 D3 and
  ADR-558 D3 both say ONE responder), human-mention notifications (ADR-495 D6,
  needs an attention surface), FE `@` autocomplete beyond the menu.

## 4. Verification notes

- `test_adr495_addressing.py` is **pytest-style** — 24 checks, run with
  `python3 -m pytest` from `api/`.
- **Four gates pinned a spelling this session** and were re-derived, not
  re-spelled: `test_adr502_503` (its polling check has now been renamed
  THREE times for the same reason), `test_agent_registry`, `test_adr558`,
  `test_adr562`. When a gate needs renaming a third time, the gate is wrong.
- ⚠️ **Green gates kept testing helpers, not wiring.** Neutering
  `select_responder("")` at the route left all 30 checks green. The new
  AST-walking check on the call site is the fix; prefer that shape when a pure
  function is reached through one call site.
- `test_adr307_permission_taxonomy::test_non_path_primitive_gates_on_delegation_only`
  is RED pre-existing (Schedule under autonomous), verified on a clean tree.

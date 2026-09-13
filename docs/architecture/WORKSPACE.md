---
title: Workspace (Architecture)
counterpart: docs/design/WORKSPACE.md
scope: conceptual — substrate, files, layers, genesis, the two execution paths
status: Canonical
version: v2.0 (2026-09-12 — the post-steward recut, ADR-596/603/632; v1 archived at previous_versions/WORKSPACE-architecture-2026-09-12-pre-recut.md)
last_updated: 2026-09-12
---

# Workspace — Architecture

**Counterpart (design):** [docs/design/WORKSPACE.md](../design/WORKSPACE.md) — the member-facing surfaces over the same substrate.
**Canon this doc derives from:** [FOUNDATIONS](FOUNDATIONS.md) Axioms 1, 2, 4 · [ADR-209](../adr/ADR-209-authored-substrate.md) · [ADR-373](../adr/ADR-373-multi-principal-workspace-and-the-re-key.md) · [ADR-378](../adr/ADR-378-the-workspace-as-the-outermost-unit.md) · [ADR-414](../adr/ADR-414-the-pure-workspace-genesis-system-agent-program-as-hire.md) · [ADR-588](../adr/ADR-588-folders-are-first-class-and-the-told-name-is-an-address.md) · [ADR-596](../adr/ADR-596-the-agent-is-a-being.md) · [ADR-603](../adr/ADR-603-the-standing-declaration-and-the-supervisor-desk.md) · [ADR-624](../adr/ADR-624-the-being-has-a-home-and-what-it-knows-lives-there.md) · [ADR-639](../adr/ADR-639-standing-work-is-a-kernel-lane.md).

> **Recut (2026-09-12).** The previous version described the pre-ADR-320 tree (`context/_shared/`, `review/`, `memory/`), a five-phase init that seeded a steward, a Reviewer-run autonomy loop and its cold-start failure modes. All of that machinery is deleted (ADR-414 D4, ADR-603 D5, ADR-632). The record is archived verbatim at [previous_versions/WORKSPACE-architecture-2026-09-12-pre-recut.md](previous_versions/WORKSPACE-architecture-2026-09-12-pre-recut.md); this document states the live form.

This doc answers five questions, in order:

0. **Which layer is what?** — kernel · workspace · app · agent, plus where user-account concerns live.
1. **What is the substrate, and what does a workspace hold?** — the filesystem as the kernel tells it.
2. **How is a workspace born, and what accumulates in it?** — genesis and growth.
3. **What does unattended work require?** — the standing declaration.
4. **How does work run?** — the two execution paths.

For how an agent *reads* this substrate at reasoning time (the lane frame), see [lane-frame.md](lane-frame.md) and [agent-composition.md](agent-composition.md).

---

## 0. Layer model

YARNNN is an agent-native operating system ([ADR-222](../adr/ADR-222-agent-native-operating-system-framing.md)). Four layers touch a workspace; user-account concerns are a fifth, orthogonal channel that never touches workspace substrate.

| Layer | What lives here | Who owns it |
|---|---|---|
| **User account** | billing, email, notification preferences, credentials (`platform_connections`, keyed `user_id` — ADR-577) | the human, across all their workspaces |
| **Kernel** | the filesystem over Postgres, the primitives, the gates, the one drain loop, the mirrors it writes into `system/` (skills — ADR-630; agent faces — ADR-641 am.2) | the system; reviewed as code, attributed `system:*` |
| **Workspace** | the commons: every file the members and their agents author, the grants (`principal_grants`), the timeline, the balance | its members (ADR-373 — one multi-principal attributed commons; the outermost unit, ADR-378) |
| **App** | the artifact type it edits and the resident that works it (`register_app` — ADR-562/592/646) | the system; a client `AppDescriptor` mirrors it (ADR-636) |
| **Agent** | identity ⊕ character ⊕ engine (ADR-596); its home `agents/{slug}/` holds `memory/` + two locked grant sidecars (ADR-624) | the register (`AGENTS`, ADR-600); the member's own face wins |

Workspaces have no types. A program (`docs/programs/{slug}/`) is a post-genesis hire (ADR-414 D5) that forks a reference workspace in; nothing about a workspace's shape is fixed at birth.

---

## 1. The substrate — the filesystem as the kernel tells it

The workspace is a **virtual filesystem of human-readable files over Postgres** (`workspace_files` + `workspace_file_versions`, ADR-106/209). Path conventions are the schema; new capabilities extend paths, not tables. **`write_revision()` in `api/services/authored_substrate.py` is the single write path**: every mutation lands a content-addressed revision with `authored_by` and a message, parent-pointered to the one before it. Binary bytes ride the same lane through the CAS seam (ADR-427). There is no filename versioning and no `/history/` folder — the revision chain *is* the history.

### What every participant is told

The kernel tells every agent the same thing (`PARTICIPANT_FILESYSTEM_MODEL`, `api/services/workspace_paths.py` — composed into every lane frame and the MCP binding, ADR-533):

- **Where** — a file's path is its meaning. Two homes are provided: **Documents** (authored work with no more specific home) and **Downloads** (what arrived from outside — uploads, observations from connected apps). Everything else at the top level is a meaning-named folder someone created; writing a file into a new folder creates it.
- **Whether** — a grant decides if a path may be written. Most of the home is the participant's; the system's own settings and runtime state are not.
- **Who** — every write is attributed and versioned; nothing is silently overwritten.

The told names are addresses, not paths: `HOME_ALIASES` resolves **Documents → `operation/`** and **Downloads → `inbound/`** at `parse_file_reference`, the one chokepoint (ADR-588). A told name must never reach a composed path.

### Roots

| Root | What it is | Written by |
|---|---|---|
| `operation/` (**Documents**) | the commons' meaning folders — `operation/{folder}/…` for whatever members name; `operation/reports/` for composed outputs; `operation/CONVENTIONS.md` when a program ships one | members, agents in their lanes, standing declarations |
| `inbound/` (**Downloads**) | what arrived: `inbound/{lane}/{selector}/{stamp}.{ext}` (the BINDING grammar, [intake-pipeline.md](intake-pipeline.md)); `inbound/uploads/` for human uploads; observations from captures | the intake pipeline (`system:capture-{platform}`), uploads |
| `uploads/` | the legacy human-upload root; permanent | members |
| `agents/{slug}/` | an agent's home: `memory/` (ordinary substrate, freely writable by it) + `_autonomy.yaml` + `_budget.yaml` (the grant sidecars, LOCKED — ADR-624). Nothing else; the ADR-414 twelve-file set is deleted | the agent (memory); the member (sidecars) |
| `system/` | the kernel's region: `system/skills/` (the mirrored kernel skills, ADR-630), `system/agents/{slug}/` (what the kernel ships for an agent — its face), runtime state | the kernel only |
| `governance/` | the workspace dials — `_autonomy.yaml` (the witness dial, ADR-405) + `_budget.yaml` (the spend envelope, ADR-327). Absent on most workspaces: `budget.py` degrades to kernel defaults | the owner |
| `constitution/` · `contract/` | the operator's declarations when they exist — `constitution/MANDATE.md` + `PRECEDENT.md` (intent, ADR-207/320); `contract/_preferences.yaml` + `_expected_output.yaml` (what the operation owes, ADR-345/366) | the operator |

Older workspaces may still carry `persona/` (the retired seat's files, ADR-632) and `context/`; no live code reads either as a home.

### Folders, names, lifecycle

- **A folder exists iff a file exists under its prefix** — the tree is derived. An *empty* folder is a marker row (trailing-slash path, `content_type='inode/directory'`), written via `write_revision`, never through `WriteFile`; every listing filters on `is_folder_marker` (presentation, never authorization) (ADR-588).
- **Format follows the consumer** (ADR-254): `UPPERCASE.md` prose for operator/LLM, `lowercase.md` append-only narrative, `_name.yaml` machine-parsed config (`yaml.safe_load`; ints are ints), `.json` manifests, `.html` composed artifacts, `face.png` an agent's face. No new YAML-frontmatter `.md`; no hand-rolled frontmatter parsers.
- **A file declares its type in its own bytes** (`data-template`); a layout row declares the owning app; the server scopes which types an app opens (`kinds_for_app`, ADR-473/646). An unowned type opens in the generic viewer, never a default app.
- **Lifecycle** (`workspace_files.lifecycle`, ADR-119): `active` · `permanent` (uploads) · `ephemeral` · `delivered` · `archived` (the Trash — a folder fan-out archives one revision per file, grouped by `metadata.trashed_with`).
- **Permission is owned by the grant, defaulted by meaning; one decider** ([ADR-643](../adr/ADR-643-an-access-decision-has-one-decider.md)): `_is_path_locked_for_principal` in `api/services/primitives/workspace.py` answers *may this principal do this verb on this path* and fails closed. The path-anchored residue is exactly the grant sidecars, `system/`, and the principal homes.

---

## 2. Genesis and growth

### Genesis is pure (ADR-414 D4, ADR-465 D2)

A workspace is minted by **`ensure_owner_workspace`** (`api/services/supabase.py`), called from `get_user_client` — the one dependency every authenticated request passes — for a principal who resolves no workspace at all. **The mint is two rows**: the `workspaces` row *and the owner's `principal_grants` row*. `is_workspace_member()` (mig 221) reads grants only, so a workspace without its owner grant is reachable by nobody, including its owner (found and fixed on both mint sites 2026-09-12; 7 live workspaces healed). A share-first arrival already holds a member grant and never triggers the mint: join-only is real (ADR-404).

Nothing is seeded. There is no steward, no mandate, no persona, no template: the workspace is born empty, constituted by its grants, and everything renders (ADR-414 D4). `initialize_workspace()` (`api/services/workspace_init.py`, v3.0) survives for the reset paths (`DELETE /account/workspace`, `DELETE /account/reset`, the purge reinit) and writes only the two governance dials and the signup balance audit row; the workspace-state route still calls it but has no live reader (an open item).

### What accumulates

- **The kernel's mirrors** — the scheduler's mirror lane writes `system/skills/` and the agents' faces on every tick; a mirror's correctness is that the second run does nothing (ADR-630/641).
- **The members' work** — files written in lanes through the five file verbs and the apps' verbs, attributed `member:{user_id} via {model}`; uploads into Downloads; folders named by meaning.
- **What arrives** — captures landing attributed observations at the intake lane on a connection's schedule (ADR-582/591); the derive step distils, and judgment reads the distillate ([intake-pipeline.md](intake-pipeline.md)).
- **What agents know** — `agents/{slug}/memory/`, ordinary substrate the agent writes freely (ADR-624).
- **Standing declarations** — `{folder}/_standing.yaml` + `CONTRACT.md` beside the file they keep (ADR-603/639).
- **A program, if hired** — `POST /api/programs/activate` forks `docs/programs/{slug}/reference-workspace/` in (`fork_reference_workspace`, tiers `canon` / `authored` / `placeholder`; ADR-226); `reapply_platform_substrate` (ADR-292) is the `claude --update` shape for taking later bundle changes.

---

## 3. What unattended work requires

Nothing wakes on its own initiative (ADR-632). Attended work needs only a member and a lane. **Unattended work is a member's standing declaration**, and it needs exactly:

| Requirement | Where it lives | If missing |
|---|---|---|
| a **target** — the file the declaration keeps | the kept file itself | nothing to keep; no declaration |
| a **contract** — what "true" means for the kept file | `{folder}/CONTRACT.md` | the run is refused (ADR-603 D6) |
| a **schedule** + sources + the app | `{folder}/_standing.yaml`; the app derives from the target's type (an agent slug there is `app_invalid`) | not due; never drained |
| **budget** — spend bounded by the pool | the member's balance; `governance/_budget.yaml` when present | the run is refused with a receipt (ADR-618) |
| a **grant** — the declaring member may write the target | `principal_grants` | the write is refused by the one decider |

A declaration is made from inside any lane (the `declaring-standing-work` skill, ADR-630/639) and shows in Notifications → Standing work with Run now / Pause. It carries no outbound reach by design (a standing run is refused a credential — ADR-577/645); the successor is a workspace bot identity, never adoption.

---

## 4. How work runs — the two execution paths

| Path | Trigger | Runner | Attribution | Bounds |
|---|---|---|---|---|
| **Attended** | a member's message in a lane | `run_lane_turn` (`api/services/lane_runner.py`) — the agent's tool-use loop; the frame is `build_lane_conventions` | `member:{user_id} via {model}` | the member's grant; the read cap and history ceiling (ADR-648); prompt caching in the router (ADR-634/647) |
| **Unattended** | a standing declaration comes due | the ONE drain loop (`claim_run` · `record_run` · `drain_due`, `api/services/scheduling.py`) → `run_bounded_derive_turn` (`api/services/derive_turn.py`): toolless, contract-checked, receipted | `system:standing` | the pool (ADR-618); the contract; a third unattended kind is an adapter on the same loop, never a twin |

The substrate is the bus: a turn reads what the last one wrote, and there is no control-flow channel between turns except the revision itself (FOUNDATIONS Axiom 1). Capture rides the same drain loop as the intake twin.

---

## 5. Failure modes that are live

| Condition | What happens | Recovery |
|---|---|---|
| a workspace row with no owner grant | reachable by nobody; every read empty; the first hard error is a postgrest 42501 on a lane insert — an INSERT's error for a READ-BACK failure | both mint sites now write the grant; backfill via `ensure_owner_workspace` itself |
| a told name (`Documents/`) in a composed path | a phantom root shadows `operation/` — the PATCH door runs no alias pass | resolve at `parse_file_reference`; never compose a told name |
| a standing declaration without `CONTRACT.md` | refused, receipted | write the contract |
| the pool exhausted | the unattended run is refused with a receipt (ADR-618); attended turns are gated by balance | top up |
| a member without a grant on the target | the one decider refuses the write | share (ADR-517) |

---

## 6. Key files

| File | Role |
|---|---|
| [api/services/authored_substrate.py](../../api/services/authored_substrate.py) | `write_revision()` — the single write path |
| [api/services/workspace.py](../../api/services/workspace.py) · [api/services/primitives/workspace.py](../../api/services/primitives/workspace.py) | the filesystem over Postgres; the file verbs; `_clip_read`; `_is_path_locked_for_principal` (the decider) |
| [api/services/workspace_paths.py](../../api/services/workspace_paths.py) | the root constants; `PARTICIPANT_FILESYSTEM_MODEL` · `PARTICIPANT_COMMONS_CONTRACT` · `PARTICIPANT_REGISTER`; `HOME_ALIASES` |
| [api/services/supabase.py](../../api/services/supabase.py) | `ensure_owner_workspace` (the mint, owner grant included) · `get_user_client` (the door) |
| [api/services/workspace_init.py](../../api/services/workspace_init.py) | `initialize_workspace()` — the reset paths' reinit (dials + balance audit) |
| [api/services/programs.py](../../api/services/programs.py) · [api/services/substrate_reapply.py](../../api/services/substrate_reapply.py) | `fork_reference_workspace()`; `reapply_platform_substrate()` |
| [api/services/standing_work.py](../../api/services/standing_work.py) · [api/services/scheduling.py](../../api/services/scheduling.py) · [api/services/derive_turn.py](../../api/services/derive_turn.py) | the standing declaration; the one drain loop; the bounded derive turn |
| [api/services/skills/__init__.py](../../api/services/skills/__init__.py) · [api/services/agents_registry.py](../../api/services/agents_registry.py) | the kernel skills + their mirror; the one agent register |
| [api/services/directory_registry.py](../../api/services/directory_registry.py) · [api/services/workspace_utils.py](../../api/services/workspace_utils.py) | `WORKSPACE_DIRECTORIES`; `is_skeleton_content()` / `classify_file_state()` |
| [api/routes/workspace.py](../../api/routes/workspace.py) · [api/routes/account.py](../../api/routes/account.py) | the file routes; the reset endpoints |

## 7. Related

- [docs/design/WORKSPACE.md](../design/WORKSPACE.md) — the surfaces over this substrate
- [lane-frame.md](lane-frame.md) · [agent-composition.md](agent-composition.md) — how an agent reads the substrate at reasoning time
- [intake-pipeline.md](intake-pipeline.md) · [connectors.md](connectors.md) — how outside content reaches the commons
- [authored-substrate.md](authored-substrate.md) — the revision chain in depth
- [compositor.md](compositor.md) — the kernel/app seam for surfaces
- [docs/programs/README.md](../programs/README.md) — the program bundles

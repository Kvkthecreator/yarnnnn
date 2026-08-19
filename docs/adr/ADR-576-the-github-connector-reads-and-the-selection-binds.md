# ADR-576 — The GitHub Connector Reads, and the Selection Binds

> **Note (ADR-582, 2026-08-19)**: D2's aperture binding HOLDS and is re-pointed to the ONE selection store (`landscape.selected_sources` via `services/connectors.py::selected_ids`); receipts below citing `connector_watch.py` describe the deleted mirror path. Gate `test_adr576_github_connector.py` re-pointed and green.

**Status**: Proposed (2026-08-18)
**Date**: 2026-08-18
**Authors**: KVK (operator) + Claude (collaborator)
**Hat**: A
**Dimension**: Channel (Axiom 6 — what the operation may perceive, and through which aperture) + Substrate (Axiom 1 — one source for one fact)
**Relates to**: ADR-147 (the GitHub integration), ADR-392 D7/D9 (the connector lane; the watch declaration; the write-ready invariant this amends), ADR-394 D2 (seed-at-select — the selection's one true consumer), ADR-401 (the connection lifecycle — §3 stages 2/5/9), ADR-404 D2 (capture-lane dormancy), ADR-494 (the connector registry is singular — §1a's five deferred capability registries), ADR-563 (scopes answer what a principal may do)
**Amends**: **ADR-392 D9** (the write-ready invariant becomes bidirectional — a write scope without a write capability is now a violation, not a silent allowance). **ADR-147** (the GitHub OAuth scope narrows from `repo` to a read set).

---

## 1. Context — an audit that started with a red line in the UI

The operator connected GitHub, landed on the connector detail pane, and found three things wrong at once:

1. `Test connection` returned **`unknown — Unknown provider: github`**.
2. Connecting produced no dedicated step — "it just said connected."
3. The tool surface "seems narrow and needs a revisit."

Each is real. Each is a symptom of the same structural fact: **GitHub was wired into the doors and never into the rooms.**

### 1a. GitHub is in two of four registries

ADR-494 §1a unified the *offered set* across three sources and explicitly deferred "five further partial registries … capability registries, not the offered set." One of those has now produced a user-visible error.

| Registry | slack | notion | github |
|---|---|---|---|
| `OAUTH_CONFIGS` (`integrations/core/oauth.py:66`) | ✓ | ✓ | ✓ |
| `CONNECTOR_CAPTURE_BINDINGS` (`services/connector_watch.py:175`) | ✓ | ✓ | ✓ |
| `PLATFORM_REGISTRY` (`integrations/platform_registry.py:22`) | ✓ | ✓ | **✗** |
| `validation.py::_test_auth` branch (`:194`) | ✓ | ✓ | **✗** |

`validate_integration` looks the provider up in `PLATFORM_REGISTRY` and, finding nothing, returns `status="unknown"` with `Unknown provider: github` (`validation.py:95-98`). The probe cannot fail *honestly* — it cannot run at all.

Two asymmetries make this worse than a missing key:

- **`?validate=false` returns `healthy` unconditionally** (`routes/integrations.py:897-905`), never touching the registry. So the connector reports healthy everywhere *except* when asked to prove itself.
- **`PLATFORM_REGISTRY` is itself dead canon.** Its entries describe `mcp_server` / `transport: stdio` / "Platform tools via MCP Gateway (ADR-050)" — a gateway ADR-076 deleted. It survives only because `validate_integration` still reads it.

### 1b. The connect flow is correct — the *absence* of a modal is the design

There is deliberately **one connect verb** for all three providers (`ConnectedIntegrationsSection.tsx:151-155`, ADR-494 D2). No modal exists for Slack or Notion either. The operator's perception of a difference traces to one cosmetic fact: Slack's token exchange stores `team_name`, which renders in the subsurface header (`oauth.py:426-436`); GitHub stores none, so its header reads a bare "Connected."

**This ADR changes nothing about the connect flow.** It is recorded here so the finding is not re-opened: the singular connect verb is ratified and correct.

### 1c. The `repo` scope is held for a capability that does not exist

The GitHub OAuth config requests `repo` + `read:user` (`oauth.py:96-107`). On a classic OAuth app, `repo` grants full read **and write** to all public and private repositories: code, commits, branches, **force-push and ref deletion**, issues, PRs, wiki, settings, webhooks, deploy keys, **repo-scoped secrets and Actions**. It is the broadest non-admin GitHub scope.

It is requested deliberately, under ADR-392 D9's write-ready-by-construction invariant (`oauth.py:113-148`):

> the OAuth connect flow MUST request the read+write scope UNION — otherwise a later `write_{platform}` is capability-available but FAILS at execution for lack of the write scope, forcing a re-auth.

**The premise is false.** `write_github` does not exist:

- absent from `services/orchestration.py::CAPABILITIES`
- absent from `PLATFORM_TOOLS_BY_CAPABILITY` (`platform_tools.py:1279` declares only `read_github`)
- no tool in `GITHUB_TOOLS` writes anything

And the guard cannot notice. `connection_is_write_ready` (`oauth.py:151+`) is **one-directional**: it fails when a capability lacks its scope, and is structurally silent when a scope has no capability. The D9 gate encodes the same asymmetry — check 19 hardcodes `github` as write-ready (`test_adr392_connector_lane.py:235`), asserting the conclusion rather than testing it.

Compounding it: `github_client.py:350` carries a fully-built `create_issue` under a section header reading `# Write operations (Phase 2 — delivery)`, with **zero callers**. The write path was built, never wired, and is now cited — via the scope it justifies — as the reason to hold write authority over every private repo the operator owns.

Four further client methods are equally dead: `get_user` (:149), `get_issue_comments` (:222), `list_pull_requests` (:242), `get_languages` (:339).

### 1d. The selection reads as an aperture and binds nothing an agent touches

The SCOPE pane says: *"Selected repos become your operation's perception. Selecting is a declaration, not a sync."* The declaration is real and durable — production substrate, 2026-08-18:

```
/workspace/operation/_connectors/github/_watch.yaml   2061 bytes
  selections:
  - id: Kvkthecreator/yarnnnn
    selected: true
```

Its one true consumer is the capture lane: `capture_connector.py:195` calls `read_selected_ids` and iterates only selected ids. That lane is dormant by ratified decision (ADR-404 D2), so nothing has been captured:

```
/workspace/_captures.yaml → captures: []      (untouched since 2026-07-09)
inbound/github/**         → 0 files
any github-derived file   → 0
```

**The only GitHub artifact in the entire workspace is the selection file itself.**

But dormancy is not the sharp finding. This is: **at tool-execution time the selection is not consulted at all.**

- `platform_github_list_repos` calls `list_repos(token, max_repos=50)` (`platform_tools.py:2100`) with no reference to `selected_sources`, `_watch.yaml`, or `read_selected_ids`. It returns every repo the token can see — including private ones, including ones the operator explicitly *deselected*.
- The other four tools accept an arbitrary `owner/repo` string from the model with only a `"/" in repo` format check (`:2119`, `:2151`, `:2160`, `:2169`). No membership test against the selected set.

So an operator who ticks one box out of forty has narrowed their **capture cost**, not the agent's **reach**. The checkbox grammar reads as an aperture; it is not one.

A limit mismatch makes the incoherence visible: the tool caps at `max_repos=50` while landscape discovery uses `max_repos=200` (`landscape.py:129`). The agent's `list_repos` view can be a different, smaller, unrelated slice than the list the operator was shown and chose from.

### 1e. The read surface cannot answer the questions a repo exists to answer

Five tools ship: `list_repos`, `get_issues`, `get_repo_metadata`, `get_readme`, `get_releases`. Absent from the client entirely: **commits** (no `/commits`), **PR diffs/files/reviews** (no `/pulls/{n}/files`), **file contents at a path** (no `/contents/{path}`), **search** (no `/search/*`).

The connector cannot answer *"what changed this week"* — except via releases, which most repos never publish — or *"find X"*. `get_issues` returns PRs as issue-shaped rows, so a PR is visible as a title and never as a change.

`get_readme`'s docstring frames the gap as intentional: *"not raw markdown to avoid code analysis"* (`:295`), reinforced by the tool description *"NOT for code analysis"* (`:404`). That was a defensible Phase-1 posture. It is no longer coherent alongside a `repo` scope that grants force-push.

One more silent narrowing: `list_repos` hardcodes `affiliation: "owner,collaborator"` (`github_client.py:177`), **excluding `organization_member`**. Repos reachable only through org-team membership never appear in the tool *or* the landscape. And its docstring claims *"Excludes forks by default"* — no fork filter exists; forks are only deprioritized in scoring (`landscape.py:395`).

---

## 2. D1 — The dead write path is deleted, and the scope narrows to what is exercised

**Decision.** GitHub is a **read connector**. The unreferenced write path is deleted, and the OAuth scope narrows to the read set that the shipped tools actually exercise.

- Delete `github_client.create_issue` and its `# Write operations (Phase 2 — delivery)` section header.
- Delete the four other unreferenced client methods: `get_user`, `get_issue_comments`, `list_pull_requests`, `get_languages`.
- Narrow `OAUTH_CONFIGS["github"].scopes` from `["repo", "read:user"]` to **`["repo:status", "public_repo", "read:org", "read:user"]`**.
- Set `WRITE_SCOPE_MARKERS["github"] = None` with the exemption reason stated inline: GitHub ships no `write_github` capability.

**Why deletion rather than wiring `create_issue`.** The singular-implementation discipline says a superseded or unreached path is removed, not preserved on speculation. `create_issue` has never had a caller, has no capability declaration, no tool, no gate, and no operator surface. Wiring it would be shipping a write authority nobody asked for in order to retroactively justify a scope we already hold — the argument running backwards. If GitHub write is wanted later, it arrives as its own decision: a `write_github` capability, an ADR-307 gate, and the scope re-request that D9 exists to force.

**Why `read:org` is added while narrowing.** It is not scope creep; it corrects 1e's silent exclusion. Without it, org-team repos are invisible to both the tool and the landscape, so an operator whose work lives in an org sees an empty or misleading list. Narrowing the *authority* and widening the *visibility* are the same move toward honesty.

**What narrowing costs.** `public_repo` covers public repositories only. **Private-repo metadata is not reachable on a classic OAuth app by any scope narrower than `repo`.** So this is a real trade: private repos leave the read surface. That is the correct default — an operator who has not asked for private-repo perception should not be granting force-push to obtain it. Restoring private reads is a deliberate, separately-consented act, and belongs to the GitHub App / fine-grained-PAT migration named in §5, which can grant `metadata:read` + `contents:read` + `issues:read` on selected repos *without* any write authority. That migration is the right home for private access; `repo` is not.

**Live connections are unaffected until re-consent.** A stored token carries the scope it was granted. Narrowing the config changes what *future* connects request; the existing connection keeps `repo` until the operator reconnects. The connector detail pane already reads granted scopes back from `metadata.scope` and displays them — so the drift is visible, not hidden. Operators are not force-disconnected.

### D1.a — The write-ready invariant becomes bidirectional

**Decision.** ADR-392 D9 is amended. The invariant is no longer "a write capability implies its scope"; it is **"a write capability and its write scope imply each other."**

`connection_is_write_ready` keeps its meaning. The new half is a gate assertion, not a runtime branch: **a provider declaring a write scope marker with no `write_{platform}` capability fails CI.** The gate is written to derive both directions from `CAPABILITIES` + `WRITE_SCOPE_MARKERS`, so neither list can drift without failing.

Check 19 — which hardcodes `slack/notion/github` as write-ready — is **replaced, not edited**. It asserted its own conclusion; a provider list baked into an assertion is the shape that let this survive. The replacement derives the provider set from the capability registry.

This is the general lesson, not a GitHub one: an over-broad grant held for an unbuilt feature is invisible to a one-directional guard. ADR-563 established that scopes answer *what a principal may do*; a scope answering for a capability that does not exist answers a question nobody asked.

---

## 3. D2 — The selection binds tool reach, not only capture cadence

**Decision.** The repo selection becomes an **access boundary at tool-execution time**, not merely a scheduler scope.

- `platform_github_list_repos` returns **only selected repos** when a selection exists.
- The four repo-addressed tools (`get_issues`, `get_repo_metadata`, `get_readme`, `get_releases`) **refuse an unselected repo**, returning a legible error naming the aperture rather than silently succeeding.
- **Empty selection means unrestricted**, preserving today's behavior for every operator who never opened the pane. A boundary that springs shut on an operator who never declared one would be a silent regression; the aperture must be *declared* to bind.

**Why this is a decision and not a bug fix.** ADR-394 D2 defined selection as *seed-at-select* for the capture lane — its scope was cadence, and it honored that contract exactly. Extending it to tool reach adds a meaning the ratified contract did not carry. That is why it lands as an amendable decision with its own gate, rather than as a patch.

**Why extend it rather than re-word the pane.** The alternative was honest copy — "selection governs background capture only; agents may read any repo." Rejected: it would make the pane's checkbox grammar *describe* a permission it deliberately withholds, and it contradicts what the surrounding copy already promises. "Selected repos become your operation's perception" is the right promise. The defect is that reach did not honor it.

**The refusal is legible, never silent.** An agent asking for an unselected repo is told the repo is outside the declared aperture and that the operator can widen it in the connector pane. A silent empty result would read as "no issues," which is the failure mode Sentry cannot see: an incorrect success.

**Consequence for `max_repos`.** The 50/200 mismatch is resolved by making the tool's ceiling irrelevant in the common case — a selection is an explicit list, and the tool honors it directly rather than fetching a page and filtering. Unrestricted (empty-selection) listing keeps a bounded page.

---

## 4. D3 — GitHub joins the validation registry, and the probe reads

**Decision.** GitHub gets a `PLATFORM_REGISTRY` entry and a real `_test_auth` branch, so `Test connection` performs an actual read (`GET /user` semantics via the client's live surface) and reports an honest verdict.

Adding the registry key alone is insufficient — `_test_auth` branches only on slack/notion, so a keyed-but-unbranched GitHub would clear the `unknown` guard and then fail auth. Both, or the button still cannot pass.

**Scope discipline.** This ADR does **not** delete `PLATFORM_REGISTRY`, though it is fossil canon describing a deleted MCP gateway (§1a). Collapsing it into `CONNECTOR_REGISTRY` is the correct end-state and is named in §5 as follow-on work. Doing it here would bundle a cross-provider refactor into a GitHub fix — the two should be separately revertible.

### D3.a — The pane states dormancy where the promise is made

The connector list row already says "Connected — not reading (capture is paused)." The drill-in SCOPE section — where "Selected repos become your operation's perception" is written — does not. The caveat moves to where the promise is made.

With D2 in force the copy also becomes true in a second sense: selection binds reach even while capture sleeps. The sentence stops depending on a dormant lane to be accurate.

---

## 5. What this ADR does not decide

> **The deferred items below are carried forward in
> [`connector-reach-and-the-commons.md`](../architecture/connector-reach-and-the-commons.md)**
> — the standing brief for that discourse. Read it before reopening any of them.

- **Derive (ADR-401 §3 stage 5) stays open.** No code path derives `inbound/github/` → `operation/`. Even with capture enabled, raw would accumulate and never reach the commons. That is the largest gap in the connector arc and needs its own ADR; it is not a GitHub question.
- **Read-surface breadth (commits, PR diffs, file contents, search) is not added here.** §1e documents the gap. Adding those verbs under a *narrowed* scope is coherent follow-on work; adding them in the same change as a scope narrowing and a reach boundary would make the blast radius unreviewable.
- **`PLATFORM_REGISTRY`'s collapse into `CONNECTOR_REGISTRY`** — named above, deferred.
- **The GitHub App / fine-grained-PAT migration** — the correct long-term answer to private-repo reads without write authority. Deferred, and named as the home for restoring private access.
- **`orchestration.py:1313` lists 2 tools for `read_github` where `platform_tools.py:1279` lists 5.** Corrected in passing as a drift fix; it decides nothing.

---

## 6. Gate

`api/test_adr576_github_connector.py` asserts:

1. No unreferenced write path — `create_issue` is absent from the GitHub client.
2. The four other dead methods are absent.
3. `OAUTH_CONFIGS["github"].scopes` contains no `repo` write scope.
4. `WRITE_SCOPE_MARKERS["github"] is None`, and GitHub declares no `write_github` capability.
5. **Bidirectional D9** — every write scope marker has a matching capability, and every write capability has a matching marker (derived from both registries; no hardcoded provider list).
6. `list_repos` filters by selection when one exists; returns unrestricted when empty.
7. A repo-addressed tool refuses an unselected repo with a legible aperture error.
8. GitHub resolves in `PLATFORM_REGISTRY` and `_test_auth` has a GitHub branch.

`api/test_adr392_connector_lane.py` check 19 is replaced by the derived form (D1.a).

Each assertion is falsified against a real call before landing — a gate that passes against the broken shape is not a gate.

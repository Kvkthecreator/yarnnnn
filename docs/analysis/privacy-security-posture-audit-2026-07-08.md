# Privacy & Security Posture Audit — Carry-Over Findings + Independent Read

**Date:** 2026-07-08
**Scope:** YARNNN data custody, authored substrate, connector credentials, cross-LLM egress, purge/deletion promises, and public privacy-architecture positioning.
**Status:** Actionable audit input. This is not a legal policy; it is the engineering/privacy basis for the public privacy architecture page.

## Executive summary

The prior audit's center of gravity is correct: the largest privacy risk is not the relational app model, which is comparatively mature, but the authored-substrate layer that stores content-addressed bodies in `workspace_blobs`. The relational tables generally carry user scoping, RLS, attribution, and explicit purge paths. The blob store deliberately removed user scoping because deduplication was treated as a storage primitive; that choice now conflicts with deletion, least privilege, and data-minimization promises.

My independent read preserves the carry-over ranking but reframes the publishable privacy story around three truths:

1. **What is already strong:** row-scoped application tables, encrypted connector credentials for most sensitive integrations, no default PII to Sentry, and visible provenance/revision history.
2. **What must not be over-claimed publicly:** deletion completeness, blob isolation, retention minimization, redaction before AI-provider calls, and key-rotation maturity.
3. **What should become the privacy architecture roadmap:** scoped blob reads, blob garbage collection, tasks RLS, credential rotation/history scrub, credential field normalization, retention controls, and explicit cross-LLM disclosures.

## Carry-over findings, independently assessed

| Rank | Finding | Independent assessment | Publishable framing | Required action |
| --- | --- | --- | --- | --- |
| Critical | Production database credential committed in repository history | Treat as active exposure if the reported files/history are accurate. Do not rely on repo privacy or later deletion; rotate immediately and scrub history. | Do **not** publish the incident details on a marketing page unless there is a formal disclosure decision. Public page can say secrets are being moved to managed environment variables and rotated. | Rotate Supabase DB password/keys, invalidate any derived URLs, remove plaintext from tracked files, scrub git history, audit access logs. |
| Critical | Account deletion leaves `workspace_blobs` content behind | Confirmed by schema shape: blobs are content-addressed, have no user/workspace owner column, and are referenced by `workspace_file_versions.blob_sha`; purge code deletes revisions/files but not orphaned blobs. | Be precise: deletion is designed around workspace rows today; blob garbage collection is a named hardening item before stronger erasure claims. | Add reachability-based blob GC after deleting versions; consider a `workspace_blob_refs` table or owner-scoped blob table. |
| High | Blanket authenticated `SELECT` on `workspace_blobs` | Confirmed in migration 158: authenticated users can read any blob if they know its SHA-256. The app normally reads through scoped revisions, but RLS does not enforce that boundary at the blob table. | Publicly explain tenant-scoped reads; do not claim every storage primitive is independently tenant-isolated until fixed. | Replace direct blob read policy with service-role-only reads or a SECURITY DEFINER function that joins through user-owned versions. |
| High | `tasks` table lacks RLS | Confirmed in the task-creation migration: tasks are user-scoped by `user_id` but RLS is not enabled there in the same migration. This creates a sharp app-layer footgun. | Public page can say task isolation is an active hardening item unless a later migration proves RLS is live in production. | Add `ALTER TABLE tasks ENABLE ROW LEVEL SECURITY` and owner/service policies; test authenticated cross-user reads/writes. |
| Medium | Alpha Vantage / market-data key stored in metadata | Confirmed pattern: Alpaca key/secret are encrypted as `credentials_encrypted`, but optional `market_data_key` is placed in JSON metadata. | Say API credentials are encrypted at rest where stored as credentials; avoid blanket claims over all connector metadata until normalized. | Move market-data keys to encrypted credential payload or separate encrypted field; migrate existing rows. |
| Medium | Static Fernet key with no versioning | Confirmed by `TokenManager`: one `INTEGRATION_ENCRYPTION_KEY` decrypts all rows; no key id/version appears in the ciphertext model. | Publicly phrase as encrypted-at-rest, not as mature key lifecycle/rotation. | Add key IDs, decrypt-with-old/encrypt-with-new rotation path, and migration tooling. |
| Medium | AI-provider egress has no PII redaction layer | Product-inherent but privacy-significant: user substrate is sent to model providers to perform work. The right control is transparency, minimization, and future redaction/classification, not denial. | Disclose AI provider processing clearly, including that user-requested AI work can send relevant workspace content to model APIs. | Add prompt-context minimization receipts, optional redaction policies, and provider controls where possible. |
| Medium | MCP / cross-LLM egress is by design | Confirmed by MCP positioning: connected LLM assistants can read/write user memory when authorized. This is a feature and a disclosure requirement. | Publish this directly: connecting ChatGPT/Claude lets that assistant access the workspace material the user asks it to use. | Keep OAuth revocation obvious; log assistant attribution; expose connection roster and access scope. |
| Medium | Retention defaults toward forever | Revision history, execution events, and run ledgers are architecturally durable. This supports accountability but conflicts with minimization unless users get retention controls. | Frame as “durable by default, deletable by user action” only after blob deletion is fixed; otherwise say retention controls are being expanded. | Define TTLs or user-configured retention for telemetry/run events; keep billing/legal exceptions explicit. |

## What genuinely holds up

- **Most connector credentials use application-layer Fernet encryption.** OAuth tokens and Alpaca/commerce-style credential payloads flow through `TokenManager`, which encrypts before storage.
- **Major content and conversation tables are designed around user scoping.** `workspace_files`, `workspace_file_versions`, `chat_sessions`, and related surfaces usually filter by `user_id` in application code and/or RLS policies.
- **Sentry is configured with `send_default_pii=False`.** This is the right default for crash telemetry.
- **Authored-substrate provenance is a real privacy asset.** Every substrate mutation can carry who wrote it, when, and why. That gives users inspection and accountability most memory products lack.
- **The purge model is structured.** The L1-L5 taxonomy is not hand-wavy; it is an explicit data-deletion model. Its problem is coverage drift, not lack of design.

## Additional security and privacy considerations from this audit

### 1. Public claims need a two-tier model

YARNNN should separate **security posture** from **privacy architecture**:

- Security posture: credential handling, RLS, encryption, least privilege, incident response, dependency/runtime controls.
- Privacy architecture: what content is stored, why it is retained, who/what can read it, when it leaves YARNNN, how deletion works, and what provenance users can inspect.

The marketing page should emphasize the second without inflating the first.

### 2. Content-addressed storage creates a privacy-specific threat model

CAS deduplication is safe for public assets and risky for private user memory. A SHA-256 key is not a permission boundary. For personal documents, the system must assume:

- Most blobs are single-user in practice.
- A content hash can be leaked through logs, APIs, support tooling, browser state, or a guessed low-entropy document.
- Deleting references is not equivalent to deleting content.

### 3. Revision history is both the product moat and the retention liability

The revision chain is why users can trust the record, trace authorship, and recover context. It is also why old financial details, mandates, identity edits, and assistant-contributed memories can live indefinitely. A good privacy architecture page should say “we keep history so you can inspect changes” and pair that with “we are adding retention/deletion controls,” not simply “we minimize data.”

### 4. LLM egress should be expressed as a user-mediated data flow

The honest privacy model is: the user asks YARNNN or a connected assistant to perform work; relevant workspace content may be sent to AI providers so the work can be done. The control layer is authorization, scope, provenance, and revocation — not pretending the data never leaves.

### 5. Secrets and credentials need a migration from “encrypted values” to “key lifecycle”

Fernet encryption is a good baseline, but privacy/security maturity requires operational rotation. The target state should include per-row key versioning, a rotation job, emergency revoke/re-encrypt playbooks, and metadata hygiene so no API keys live in plaintext JSON.

## Recommended remediation sequence

1. **Credential exposure response**
   - Rotate Supabase database password and any service keys that could have been derived or copied.
   - Remove plaintext connection strings from tracked files.
   - Scrub git history and invalidate old clones where feasible.
   - Review database access logs for anomalous usage.

2. **Blob privacy fix**
   - Remove authenticated blanket `SELECT` on `workspace_blobs`.
   - Add scoped read path through user-owned `workspace_file_versions`.
   - Add orphan-blob garbage collection after L2/L4/L5 and the purge harness.
   - Add tests proving account deletion removes single-user blob content and preserves only blobs still referenced by another user.

3. **RLS coverage fix**
   - Enable RLS on `tasks` with owner policies and service-role manage policy.
   - Add schema test that every user-scoped table has RLS unless explicitly exempted with a documented rationale.

4. **Credential normalization**
   - Migrate market-data keys out of `metadata` into encrypted credential storage.
   - Add key IDs and rotation support to encrypted credential rows.

5. **Retention controls**
   - Define retention classes: user-authored content, revision history, operational telemetry, billing ledger, connector logs.
   - Add configurable retention for telemetry/run artifacts where legal/billing requirements allow.

6. **Public privacy architecture page**
   - Publish a page that explains the real architecture: ownership, provenance, authorization, AI-provider egress, connector access, deletion model, and current hardening roadmap.
   - Link it from the privacy policy and sitemap.

## Public-page claim discipline

Safe claims now:

- “Your workspace is scoped to your account/workspace.”
- “Connected assistants require OAuth authorization and can be revoked.”
- “We record provenance for saved memory and revisions.”
- “Most connector credentials are encrypted at rest.”
- “AI work may send relevant context to AI providers.”

Avoid until remediated:

- “All data is deleted on account deletion.”
- “Every storage layer is tenant-isolated by RLS.”
- “We retain data only as long as necessary.”
- “All API keys are encrypted.”
- “We redact PII before model-provider calls.”

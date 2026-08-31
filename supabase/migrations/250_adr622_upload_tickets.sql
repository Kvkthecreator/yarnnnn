-- ADR-622 — the upload ticket: a scoped, single-use capability to add bytes.
--
-- The connector cannot carry bytes (ADR-621 D5: base64 through a token stream
-- is measured to corrupt, and a REMOTE MCP server cannot read the caller's
-- disk). The industry answer, converged on by Box, Notion, Dropbox, S3 and
-- SEP-2631, is a HANDSHAKE: the control channel mints a short-lived scoped
-- capability; a separate authenticated HTTP channel carries the bytes.
--
-- ⭐⭐⭐ WHY A ROW AND NOT A SIGNED STRING. A JWT-shaped ticket cannot be
-- SINGLE-USE — statelessness is exactly what makes it replayable — and it
-- cannot be revoked before its expiry. Both properties are the point of a
-- write capability into an attributed commons, so the ticket is a row:
-- `redeemed_at` makes redemption idempotent-by-refusal, and a row can be
-- deleted. The cost is one indexed lookup per redemption, which the upload
-- (a multi-MB body through the derive pipeline) does not notice.
--
-- ⭐ WHY NOT A SUPABASE SIGNED-UPLOAD URL. storage3 offers
-- `create_signed_upload_url`, which writes STRAIGHT INTO A BUCKET — bypassing
-- type-derivation-from-bytes (ADR-427 D5), the size caps, `write_revision`
-- (ADR-209's single write path), attribution, and the ADR-395 text projection.
-- Bytes would land somewhere the substrate does not know about, needing a
-- reconciler: a SECOND intake path, which CLAUDE.md's Singular Implementation
-- rule forbids. The ticket points at a yarnnn endpoint that redeems through the
-- ONE existing upload pipeline instead.

CREATE TABLE IF NOT EXISTS workspace_upload_tickets (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id   UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    -- The redemption secret. Opaque, high-entropy, never derived from the id.
    token          TEXT NOT NULL UNIQUE,
    -- The owning human. The redemption writes AS this user through the same
    -- pipeline the browser upload uses, so attribution is unchanged and an
    -- agent cannot mint itself a wider reach than its principal has.
    user_id        UUID NOT NULL,
    -- Who asked for the ticket — the principal string, e.g. 'yarnnn:mcp:claude.ai'
    -- or 'member:<uuid>'. Provenance for the audit trail; NOT an authorization
    -- input (the grant was checked at mint time, against user_id).
    minted_by      TEXT NOT NULL,
    -- The destination folder, workspace-relative, no leading slash. NULL = the
    -- intake lane (exactly what an omitted `destination` means to the browser
    -- upload). AUTHORIZED AT MINT TIME, then frozen: the redeemer cannot move
    -- the write somewhere the minting principal was not allowed to put it.
    destination    TEXT,
    -- The declared filename. The extension is a HINT for type derivation; the
    -- real verdict comes from the BYTES at redemption (ADR-427 D5), so a
    -- caller cannot smuggle a payload by naming it .md.
    filename       TEXT NOT NULL,
    -- The declared byte size, used to refuse an oversized upload BEFORE the
    -- body is streamed. Re-checked against the actual bytes at redemption —
    -- this is a fast-fail courtesy, never the enforcement.
    declared_bytes BIGINT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Short by design: a capability that outlives the conversation that minted
    -- it is a standing write door. 1 hour, matching the ADR-427 D4 serving URL.
    expires_at     TIMESTAMPTZ NOT NULL,
    -- Single-use. Set on the FIRST successful redemption; a second attempt is
    -- refused by the partial index below rather than by application logic.
    redeemed_at    TIMESTAMPTZ,
    -- The path the redemption actually wrote, for the audit trail.
    written_path   TEXT
);

-- The redemption lookup: by token, unredeemed, unexpired. Partial so the index
-- holds only live tickets.
CREATE INDEX IF NOT EXISTS idx_upload_tickets_live
    ON workspace_upload_tickets (token)
    WHERE redeemed_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_upload_tickets_workspace
    ON workspace_upload_tickets (workspace_id, created_at DESC);

-- ⭐ RLS: service-role only, deliberately. Both doors (mint + redeem) run
-- server-side under the service client — the minting principal is authorized
-- BEFORE the row is written, and the redeemer authenticates with the TOKEN, not
-- with a session. A user-visible policy would imply the table is queryable by a
-- principal, which it is not: a ticket is a secret, and listing secrets is the
-- one thing no policy here should permit.
--
-- (This is the ADR-615 / ADR-618 lesson applied at design time rather than
-- after a live failure: a table read by a service-role path must not be given a
-- user policy that silently returns zero rows to the real caller.)
ALTER TABLE workspace_upload_tickets ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE workspace_upload_tickets IS
    'ADR-622 — single-use, short-lived capability to add bytes to the workspace. '
    'Minted by an authorized principal (MCP or member), redeemed over plain HTTP '
    'through the ONE upload pipeline. Service-role only; a ticket is a secret.';

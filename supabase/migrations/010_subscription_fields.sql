-- Migration: Add subscription fields for Lemon Squeezy integration
-- ADR: docs/monetization/STRATEGY.md

-- Add subscription fields to workspaces table
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS subscription_status TEXT DEFAULT 'free';
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS subscription_expires_at TIMESTAMPTZ;
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS lemonsqueezy_customer_id TEXT;
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS lemonsqueezy_subscription_id TEXT;

-- Also store owner email for admin queries (populated on workspace creation)
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS owner_email TEXT;

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_workspaces_ls_customer
  ON workspaces(lemonsqueezy_customer_id);
CREATE INDEX IF NOT EXISTS idx_workspaces_ls_subscription
  ON workspaces(lemonsqueezy_subscription_id);
CREATE INDEX IF NOT EXISTS idx_workspaces_subscription_status
  ON workspaces(subscription_status);

-- Subscription events audit log
CREATE TABLE IF NOT EXISTS subscription_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    event_source TEXT NOT NULL DEFAULT 'lemonsqueezy',
    ls_subscription_id TEXT,
    ls_customer_id TEXT,
    payload JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for subscription_events
CREATE INDEX IF NOT EXISTS idx_subscription_events_workspace
  ON subscription_events(workspace_id);
CREATE INDEX IF NOT EXISTS idx_subscription_events_type
  ON subscription_events(event_type);
CREATE INDEX IF NOT EXISTS idx_subscription_events_created
  ON subscription_events(created_at DESC);

-- RLS policies for subscription_events
ALTER TABLE subscription_events ENABLE ROW LEVEL SECURITY;

-- Users can read their own subscription events
CREATE POLICY subscription_events_select_own ON subscription_events
    FOR SELECT USING (
        workspace_id IN (
            SELECT id FROM workspaces WHERE owner_id = auth.uid()
        )
    );

-- Allow service role to insert (webhooks bypass RLS with service key)
-- No explicit policy needed - service role bypasses RLS

-- Comment on purpose
COMMENT ON TABLE subscription_events IS 'Audit log for all subscription-related webhook events from Lemon Squeezy';
COMMENT ON COLUMN workspaces.subscription_status IS 'Current subscription tier: free, pro';
COMMENT ON COLUMN workspaces.subscription_expires_at IS 'When the current billing period ends/renews';
COMMENT ON COLUMN workspaces.lemonsqueezy_customer_id IS 'Lemon Squeezy customer ID for portal access';
COMMENT ON COLUMN workspaces.lemonsqueezy_subscription_id IS 'Lemon Squeezy subscription ID for status tracking';

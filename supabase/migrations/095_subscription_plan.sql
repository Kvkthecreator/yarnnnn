-- ADR-100: Track subscription plan variant (pro vs pro_early_bird)
-- subscription_status tracks tier (free/pro), subscription_plan tracks pricing variant
ALTER TABLE workspaces ADD COLUMN IF NOT EXISTS subscription_plan text;

-- Backfill: check most recent subscription event for Early Bird variant
UPDATE workspaces w
SET subscription_plan = CASE
    WHEN se.variant_id = '1301254' THEN 'pro_early_bird'
    ELSE 'pro'
END
FROM (
    SELECT DISTINCT ON (workspace_id)
        workspace_id,
        payload->'data'->'attributes'->>'variant_id' as variant_id
    FROM subscription_events
    WHERE event_type IN ('subscription_created', 'subscription_updated')
    ORDER BY workspace_id, created_at DESC
) se
WHERE w.id = se.workspace_id
  AND w.subscription_status = 'pro';

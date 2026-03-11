-- Migration 098: Agentic Terminology Rename (ADR-103)
-- Renames all "deliverable" tables/columns/functions to "agent" terminology.
-- This is a DESTRUCTIVE migration — all existing data in deliverable tables is dropped.
-- Safe because: all data is test data, no production users.

BEGIN;

-- ============================================================================
-- PHASE 1: DROP ALL DELIVERABLE-NAMED OBJECTS
-- ============================================================================

-- Drop the view first (depends on deliverables + deliverable_versions)
DROP VIEW IF EXISTS deliverable_type_metrics;

-- Drop all RPC functions
DROP FUNCTION IF EXISTS get_due_deliverables(TIMESTAMPTZ);
DROP FUNCTION IF EXISTS get_next_version_number(UUID);
DROP FUNCTION IF EXISTS get_deliverable_domain(UUID);
DROP FUNCTION IF EXISTS get_deliverable_export_history(UUID, INTEGER);
DROP FUNCTION IF EXISTS get_deliverable_source_freshness(UUID);
DROP FUNCTION IF EXISTS get_suggested_deliverable_versions(UUID);
DROP FUNCTION IF EXISTS should_propose_deliverable(UUID, TEXT, JSONB, INTEGER);
DROP FUNCTION IF EXISTS get_or_create_chat_session(UUID, UUID, TEXT, TEXT, INTEGER, UUID);

-- Drop tables that FK to deliverable_versions (must go first)
DROP TABLE IF EXISTS deliverable_validation_results CASCADE;
DROP TABLE IF EXISTS deliverable_source_runs CASCADE;
DROP TABLE IF EXISTS synthesizer_context_log CASCADE;
DROP TABLE IF EXISTS destination_delivery_log CASCADE;
DROP TABLE IF EXISTS export_log CASCADE;

-- Drop tables that FK to deliverables
DROP TABLE IF EXISTS deliverable_export_preferences CASCADE;
DROP TABLE IF EXISTS deliverable_proposals CASCADE;
DROP TABLE IF EXISTS trigger_event_log CASCADE;
DROP TABLE IF EXISTS event_trigger_log CASCADE;
DROP TABLE IF EXISTS signal_history CASCADE;

-- Drop core deliverable tables
DROP TABLE IF EXISTS deliverable_versions CASCADE;
DROP TABLE IF EXISTS deliverables CASCADE;

-- Drop the deliverable_id column from chat_sessions
ALTER TABLE chat_sessions DROP COLUMN IF EXISTS deliverable_id;

-- Update notifications: drop constraint first, update data, re-add constraint
ALTER TABLE notifications DROP CONSTRAINT IF EXISTS notifications_source_type_check;
UPDATE notifications SET source_type = 'agent' WHERE source_type = 'deliverable';
ALTER TABLE notifications ADD CONSTRAINT notifications_source_type_check
    CHECK (source_type = ANY (ARRAY['system'::text, 'monitor'::text, 'tp'::text, 'agent'::text, 'event_trigger'::text, 'suggestion'::text]));

-- Update any platform_content retained_reason values
UPDATE platform_content SET retained_reason = 'agent_execution' WHERE retained_reason = 'deliverable_execution';

-- ============================================================================
-- PHASE 2: RECREATE AS AGENT TABLES
-- ============================================================================

-- Core agents table (was: deliverables)
CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    description TEXT,
    recipient_context JSONB DEFAULT '{}',
    template_structure JSONB DEFAULT '{}',
    schedule JSONB NOT NULL DEFAULT '{}',
    sources JSONB DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_run_at TIMESTAMPTZ,
    next_run_at TIMESTAMPTZ,
    agent_type TEXT NOT NULL DEFAULT 'custom',
    type_config JSONB DEFAULT '{}',
    type_tier TEXT DEFAULT 'stable',
    destination JSONB,
    platform_variant TEXT,
    destinations JSONB DEFAULT '[]',
    is_synthesizer BOOLEAN DEFAULT false,
    type_classification JSONB DEFAULT '{}',
    domain_id UUID,
    origin TEXT NOT NULL DEFAULT 'user_configured',
    agent_instructions TEXT NOT NULL DEFAULT '',
    agent_memory JSONB NOT NULL DEFAULT '{}',
    mode TEXT NOT NULL DEFAULT 'recurring',
    proactive_next_review_at TIMESTAMPTZ,
    trigger_type TEXT NOT NULL DEFAULT 'schedule',
    trigger_config JSONB,
    last_triggered_at TIMESTAMPTZ,

    -- Check constraints
    CONSTRAINT agents_status_check CHECK (status = ANY (ARRAY['active', 'paused', 'archived'])),
    CONSTRAINT agents_agent_type_check CHECK (agent_type = ANY (ARRAY['digest', 'brief', 'status', 'watch', 'deep_research', 'coordinator', 'custom'])),
    CONSTRAINT agents_mode_check CHECK (mode = ANY (ARRAY['recurring', 'goal', 'reactive', 'proactive', 'coordinator'])),
    CONSTRAINT agents_origin_check CHECK (origin = ANY (ARRAY['user_configured', 'analyst_suggested', 'signal_emergent', 'coordinator_created'])),
    CONSTRAINT agents_trigger_type_check CHECK (trigger_type = ANY (ARRAY['schedule', 'event', 'manual'])),
    CONSTRAINT agents_type_tier_check CHECK (type_tier = ANY (ARRAY['stable', 'beta', 'experimental'])),
    CONSTRAINT agents_governance_ceiling_check CHECK (destination IS NULL OR TRUE)
);

-- Indexes
CREATE INDEX idx_agents_user ON agents(user_id);
CREATE INDEX idx_agents_project ON agents(project_id);
CREATE INDEX idx_agents_status ON agents(status) WHERE status = 'active';
CREATE INDEX idx_agents_next_run ON agents(next_run_at) WHERE status = 'active';
CREATE INDEX idx_agents_type ON agents(agent_type);
CREATE INDEX idx_agents_origin ON agents(user_id, origin) WHERE origin != 'user_configured';
CREATE INDEX idx_agents_type_classification ON agents USING GIN (type_classification);
CREATE INDEX idx_agents_platform_variant ON agents(platform_variant) WHERE platform_variant IS NOT NULL;
CREATE INDEX idx_agents_destinations ON agents USING GIN (destinations jsonb_path_ops) WHERE destinations IS NOT NULL AND destinations != '[]'::jsonb;
CREATE INDEX idx_agents_synthesizer ON agents(is_synthesizer) WHERE is_synthesizer = true;
CREATE INDEX idx_agents_destination_platform ON agents((destination->>'platform')) WHERE destination IS NOT NULL;

-- RLS
ALTER TABLE agents ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage their own agents" ON agents
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

-- Agent runs table (was: deliverable_versions)
CREATE TABLE agent_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'generating',
    draft_content TEXT,
    final_content TEXT,
    edit_diff JSONB,
    edit_categories JSONB,
    edit_distance_score DOUBLE PRECISION,
    feedback_notes TEXT,
    context_snapshot_id UUID,
    pipeline_run_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    staged_at TIMESTAMPTZ,
    approved_at TIMESTAMPTZ,
    delivery_status TEXT,
    delivery_external_id TEXT,
    delivery_external_url TEXT,
    delivered_at TIMESTAMPTZ,
    delivery_error TEXT,
    source_fetch_summary JSONB,
    delivery_mode TEXT,
    source_snapshots JSONB DEFAULT '[]',
    analyst_metadata JSONB,
    metadata JSONB,

    CONSTRAINT agent_runs_unique_version UNIQUE(agent_id, version_number),
    CONSTRAINT agent_runs_status_check CHECK (status = ANY (ARRAY['generating', 'staged', 'reviewing', 'approved', 'rejected', 'suggested', 'delivered', 'failed'])),
    CONSTRAINT agent_runs_delivery_status_check CHECK (delivery_status = ANY (ARRAY['pending', 'delivering', 'delivered', 'failed', NULL])),
    CONSTRAINT agent_runs_delivery_mode_check CHECK (delivery_mode = ANY (ARRAY['draft', 'direct', NULL]))
);

-- Indexes
CREATE INDEX idx_agent_runs_agent ON agent_runs(agent_id);
CREATE INDEX idx_agent_runs_status ON agent_runs(status);
CREATE INDEX idx_agent_runs_staged ON agent_runs(agent_id, status) WHERE status = 'staged';
CREATE INDEX idx_agent_runs_suggested ON agent_runs(agent_id, status) WHERE status = 'suggested';
CREATE INDEX idx_agent_runs_analyst ON agent_runs(created_at DESC) WHERE status = 'suggested' AND analyst_metadata IS NOT NULL;
CREATE INDEX idx_agent_runs_delivered ON agent_runs(agent_id, delivered_at DESC) WHERE status = 'delivered';
CREATE INDEX idx_agent_runs_failed ON agent_runs(agent_id, created_at DESC) WHERE status = 'failed';
CREATE INDEX idx_agent_runs_delivery_mode ON agent_runs(delivery_mode) WHERE delivery_mode IS NOT NULL;

-- RLS
ALTER TABLE agent_runs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can manage runs of their agents" ON agent_runs
    USING (agent_id IN (SELECT id FROM agents WHERE user_id = auth.uid()))
    WITH CHECK (agent_id IN (SELECT id FROM agents WHERE user_id = auth.uid()));

-- Agent export preferences (was: deliverable_export_preferences)
CREATE TABLE agent_export_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    destination JSONB NOT NULL DEFAULT '{}',
    auto_export BOOLEAN DEFAULT false,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT agent_export_prefs_unique UNIQUE(agent_id, provider)
);

CREATE INDEX idx_agent_export_prefs_agent ON agent_export_preferences(agent_id);
CREATE INDEX idx_agent_export_prefs_auto ON agent_export_preferences(auto_export) WHERE auto_export = true;

ALTER TABLE agent_export_preferences ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view export prefs for own agents" ON agent_export_preferences FOR SELECT
    USING (EXISTS (SELECT 1 FROM agents a WHERE a.id = agent_export_preferences.agent_id AND a.user_id = auth.uid()));
CREATE POLICY "Users can insert export prefs for own agents" ON agent_export_preferences FOR INSERT
    WITH CHECK (EXISTS (SELECT 1 FROM agents a WHERE a.id = agent_export_preferences.agent_id AND a.user_id = auth.uid()));
CREATE POLICY "Users can update export prefs for own agents" ON agent_export_preferences FOR UPDATE
    USING (EXISTS (SELECT 1 FROM agents a WHERE a.id = agent_export_preferences.agent_id AND a.user_id = auth.uid()));
CREATE POLICY "Users can delete export prefs for own agents" ON agent_export_preferences FOR DELETE
    USING (EXISTS (SELECT 1 FROM agents a WHERE a.id = agent_export_preferences.agent_id AND a.user_id = auth.uid()));
CREATE POLICY "Service role can manage all agent export prefs" ON agent_export_preferences TO service_role
    USING (true);

-- Trigger for updated_at
CREATE TRIGGER update_agent_export_preferences_timestamp
    BEFORE UPDATE ON agent_export_preferences
    FOR EACH ROW EXECUTE FUNCTION update_integration_timestamp();

-- Agent source runs (was: deliverable_source_runs)
CREATE TABLE agent_source_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    run_id UUID REFERENCES agent_runs(id) ON DELETE SET NULL,
    source_index INTEGER NOT NULL,
    source_type TEXT NOT NULL,
    provider TEXT,
    resource_id TEXT,
    scope_used JSONB DEFAULT NULL,
    time_range_start TIMESTAMPTZ,
    time_range_end TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'pending',
    items_fetched INTEGER DEFAULT 0,
    items_filtered INTEGER DEFAULT 0,
    content_summary TEXT,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ,

    CONSTRAINT agent_source_runs_unique_version UNIQUE(run_id, source_index),
    CONSTRAINT agent_source_runs_status_check CHECK (status = ANY (ARRAY['pending', 'fetching', 'completed', 'failed', 'skipped']))
);

CREATE INDEX idx_agent_source_runs_agent ON agent_source_runs(agent_id);
CREATE INDEX idx_agent_source_runs_run ON agent_source_runs(run_id);
CREATE INDEX idx_agent_source_runs_status ON agent_source_runs(status);

ALTER TABLE agent_source_runs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view source runs for their agents" ON agent_source_runs FOR SELECT
    USING (agent_id IN (SELECT id FROM agents WHERE user_id = auth.uid()));
CREATE POLICY "Service role can manage all agent source runs" ON agent_source_runs TO service_role
    USING (true);

-- Agent validation results (was: deliverable_validation_results)
CREATE TABLE agent_validation_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
    is_valid BOOLEAN NOT NULL,
    validation_score FLOAT,
    issues JSONB DEFAULT '[]',
    validated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    validator_version TEXT
);

CREATE INDEX idx_agent_validation_run ON agent_validation_results(run_id);

ALTER TABLE agent_validation_results ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view validation results for their agents" ON agent_validation_results FOR SELECT
    USING (run_id IN (SELECT ar.id FROM agent_runs ar JOIN agents a ON ar.agent_id = a.id WHERE a.user_id = auth.uid()));

-- Agent proposals (was: deliverable_proposals)
CREATE TABLE agent_proposals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    proposed_type TEXT NOT NULL,
    proposed_config JSONB NOT NULL DEFAULT '{}',
    proposed_classification JSONB NOT NULL DEFAULT '{}',
    trigger_pattern TEXT NOT NULL,
    trigger_evidence JSONB,
    status TEXT NOT NULL DEFAULT 'pending',
    created_agent_id UUID REFERENCES agents(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    responded_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ DEFAULT (now() + INTERVAL '7 days'),

    CONSTRAINT agent_proposals_status_check CHECK (status = ANY (ARRAY['pending', 'accepted', 'dismissed', 'expired']))
);

CREATE INDEX idx_agent_proposals_user_status ON agent_proposals(user_id, status) WHERE status = 'pending';

ALTER TABLE agent_proposals ENABLE ROW LEVEL SECURITY;
CREATE POLICY "agent_proposals_select" ON agent_proposals FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "agent_proposals_insert" ON agent_proposals FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "agent_proposals_update" ON agent_proposals FOR UPDATE USING (auth.uid() = user_id);

-- Export log (recreate with agent_run_id instead of deliverable_version_id)
CREATE TABLE export_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_run_id UUID NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    destination JSONB,
    status TEXT NOT NULL,
    error_message TEXT,
    external_id TEXT,
    external_url TEXT,
    content_hash TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    completed_at TIMESTAMPTZ,
    platform_metadata JSONB DEFAULT '{}',
    outcome JSONB,
    outcome_observed_at TIMESTAMPTZ
);

CREATE INDEX idx_export_log_run ON export_log(agent_run_id);
CREATE INDEX idx_export_log_user ON export_log(user_id);
CREATE INDEX idx_export_log_status ON export_log(status);
CREATE INDEX idx_export_log_created ON export_log(created_at DESC);
CREATE INDEX idx_export_log_provider ON export_log(provider);

ALTER TABLE export_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own export logs" ON export_log FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can insert own export logs" ON export_log FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update own export logs" ON export_log FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Service role can manage all export logs" ON export_log TO service_role USING (true);

-- Trigger event log (recreate with agent_id)
CREATE TABLE trigger_event_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    platform TEXT NOT NULL,
    event_type TEXT NOT NULL,
    resource_id TEXT,
    event_data JSONB DEFAULT '{}',
    event_timestamp TIMESTAMPTZ NOT NULL,
    triggered BOOLEAN NOT NULL DEFAULT false,
    skip_reason TEXT,
    run_id UUID REFERENCES agent_runs(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_trigger_event_log_agent ON trigger_event_log(agent_id, created_at DESC);
CREATE INDEX idx_trigger_event_log_user ON trigger_event_log(user_id, created_at DESC);

ALTER TABLE trigger_event_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view their own trigger logs" ON trigger_event_log FOR SELECT USING (user_id = auth.uid());
CREATE POLICY "Service role can manage all trigger event logs" ON trigger_event_log TO service_role USING (true);

-- Event trigger log (recreate with agent_id)
CREATE TABLE event_trigger_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    agent_id UUID REFERENCES agents(id) ON DELETE SET NULL,
    monitor_id UUID,
    platform TEXT NOT NULL,
    event_type TEXT NOT NULL,
    resource_id TEXT,
    event_data JSONB,
    cooldown_key TEXT NOT NULL,
    result TEXT,
    skip_reason TEXT,
    triggered_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT event_trigger_log_result_check CHECK (result = ANY (ARRAY['executed', 'skipped', 'failed']))
);

CREATE INDEX idx_event_trigger_log_cooldown ON event_trigger_log(cooldown_key, triggered_at DESC);
CREATE INDEX idx_event_trigger_log_user ON event_trigger_log(user_id, triggered_at DESC);
CREATE INDEX idx_event_trigger_log_agent ON event_trigger_log(agent_id, triggered_at DESC);

ALTER TABLE event_trigger_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own event trigger logs" ON event_trigger_log FOR SELECT USING (user_id = auth.uid());

-- Signal history (recreate with agent_id)
CREATE TABLE signal_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    signal_type TEXT NOT NULL,
    signal_ref TEXT NOT NULL,
    last_triggered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    agent_id UUID REFERENCES agents(id) ON DELETE SET NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT signal_history_unique UNIQUE(user_id, signal_type, signal_ref)
);

CREATE INDEX idx_signal_history_user_type ON signal_history(user_id, signal_type);
CREATE INDEX idx_signal_history_triggered ON signal_history(last_triggered_at);

ALTER TABLE signal_history ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own signal history" ON signal_history FOR SELECT USING (user_id = auth.uid());
CREATE POLICY "Service role can manage all signal history" ON signal_history TO service_role USING (true);

-- Agent context log (was: synthesizer_context_log)
CREATE TABLE agent_context_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    sources_assembled JSONB NOT NULL DEFAULT '[]',
    total_items_pulled INTEGER DEFAULT 0,
    total_items_after_dedup INTEGER DEFAULT 0,
    assembly_started_at TIMESTAMPTZ DEFAULT now(),
    assembly_completed_at TIMESTAMPTZ,
    assembly_duration_ms INTEGER
);

CREATE INDEX idx_agent_context_log_run ON agent_context_log(run_id);
CREATE INDEX idx_agent_context_log_agent ON agent_context_log(agent_id);

ALTER TABLE agent_context_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own agent context logs" ON agent_context_log FOR SELECT
    USING (user_id = auth.uid());
CREATE POLICY "Service role can manage all agent context logs" ON agent_context_log TO service_role
    USING (true);

-- Destination delivery log (recreate with agent_id)
CREATE TABLE destination_delivery_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    destination_index INTEGER NOT NULL,
    destination JSONB NOT NULL,
    platform TEXT NOT NULL,
    status TEXT NOT NULL,
    external_id TEXT,
    external_url TEXT,
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_dest_delivery_run ON destination_delivery_log(run_id);
CREATE INDEX idx_dest_delivery_status ON destination_delivery_log(status);

ALTER TABLE destination_delivery_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view their own delivery logs" ON destination_delivery_log FOR SELECT
    USING (user_id = auth.uid());
CREATE POLICY "Service role can manage all delivery logs" ON destination_delivery_log TO service_role
    USING (true);

-- Add agent_id column to chat_sessions (was: deliverable_id)
ALTER TABLE chat_sessions ADD COLUMN agent_id UUID REFERENCES agents(id) ON DELETE SET NULL;
CREATE INDEX idx_chat_sessions_agent ON chat_sessions(agent_id) WHERE agent_id IS NOT NULL;

-- ============================================================================
-- PHASE 3: RECREATE RPC FUNCTIONS WITH AGENT NAMING
-- ============================================================================

-- get_due_agents (was: get_due_deliverables)
CREATE OR REPLACE FUNCTION get_due_agents(check_time TIMESTAMPTZ DEFAULT NOW())
RETURNS TABLE(agent_id UUID, user_id UUID, project_id UUID, title TEXT, template_structure JSONB, sources JSONB, recipient_context JSONB)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    SELECT
        a.id as agent_id,
        a.user_id,
        a.project_id,
        a.title,
        a.template_structure,
        a.sources,
        a.recipient_context
    FROM agents a
    WHERE a.status = 'active'
      AND a.next_run_at IS NOT NULL
      AND a.next_run_at <= check_time;
END;
$$;

-- get_next_run_number (was: get_next_version_number)
CREATE OR REPLACE FUNCTION get_next_run_number(p_agent_id UUID)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    next_num INTEGER;
BEGIN
    SELECT COALESCE(MAX(version_number), 0) + 1
    INTO next_num
    FROM agent_runs
    WHERE agent_id = p_agent_id;

    RETURN next_num;
END;
$$;

-- get_agent_domain (was: get_deliverable_domain)
CREATE OR REPLACE FUNCTION get_agent_domain(p_agent_id UUID)
RETURNS UUID
LANGUAGE plpgsql SECURITY DEFINER
AS $$
DECLARE
    v_user_id UUID;
    v_domain_id UUID;
BEGIN
    SELECT user_id INTO v_user_id
    FROM agents
    WHERE id = p_agent_id;

    IF v_user_id IS NULL THEN
        RETURN NULL;
    END IF;

    SELECT kd.id INTO v_domain_id
    FROM knowledge_domains kd
    JOIN agents a ON a.id = p_agent_id
    WHERE kd.user_id = v_user_id
    AND kd.is_active = true
    AND kd.is_default = false
    AND EXISTS (
        SELECT 1
        FROM jsonb_array_elements(kd.sources) AS ds
        JOIN jsonb_array_elements(a.sources) AS dd ON true
        WHERE ds->>'resource_id' = dd->>'resource_id'
        AND (ds->>'platform' = dd->>'provider' OR ds->>'provider' = dd->>'provider')
    )
    LIMIT 1;

    IF v_domain_id IS NULL THEN
        SELECT id INTO v_domain_id
        FROM knowledge_domains
        WHERE user_id = v_user_id AND is_default = true
        LIMIT 1;
    END IF;

    RETURN v_domain_id;
END;
$$;

-- get_agent_export_history (was: get_deliverable_export_history)
CREATE OR REPLACE FUNCTION get_agent_export_history(p_agent_id UUID, p_limit INTEGER DEFAULT 20)
RETURNS TABLE(id UUID, version_number INTEGER, provider TEXT, status TEXT, external_url TEXT, created_at TIMESTAMPTZ)
LANGUAGE plpgsql SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    SELECT
        el.id,
        ar.version_number,
        el.provider,
        el.status,
        el.external_url,
        el.created_at
    FROM export_log el
    JOIN agent_runs ar ON ar.id = el.agent_run_id
    WHERE ar.agent_id = p_agent_id
    ORDER BY el.created_at DESC
    LIMIT p_limit;
END;
$$;

-- get_agent_source_freshness (was: get_deliverable_source_freshness)
CREATE OR REPLACE FUNCTION get_agent_source_freshness(p_agent_id UUID)
RETURNS TABLE(source_index INTEGER, source_type TEXT, provider TEXT, last_fetched_at TIMESTAMPTZ, last_status TEXT, items_fetched INTEGER, is_stale BOOLEAN)
LANGUAGE plpgsql SECURITY DEFINER
AS $$
BEGIN
    RETURN QUERY
    WITH latest_runs AS (
        SELECT DISTINCT ON (asr.source_index)
            asr.source_index,
            asr.source_type,
            asr.provider,
            asr.completed_at as last_fetched_at,
            asr.status as last_status,
            asr.items_fetched,
            (asr.completed_at IS NULL OR
             asr.completed_at < (now() - interval '7 days')) as is_stale
        FROM agent_source_runs asr
        WHERE asr.agent_id = p_agent_id
        ORDER BY asr.source_index, asr.completed_at DESC NULLS LAST
    )
    SELECT * FROM latest_runs;
END;
$$;

-- get_suggested_agent_runs (was: get_suggested_deliverable_versions)
CREATE OR REPLACE FUNCTION get_suggested_agent_runs(p_user_id UUID)
RETURNS TABLE(run_id UUID, agent_id UUID, agent_title TEXT, agent_type TEXT, analyst_metadata JSONB, created_at TIMESTAMPTZ)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public
AS $$
BEGIN
    RETURN QUERY
    SELECT
        ar.id as run_id,
        ar.agent_id,
        a.title as agent_title,
        a.agent_type,
        ar.analyst_metadata,
        ar.created_at
    FROM agent_runs ar
    JOIN agents a ON a.id = ar.agent_id
    WHERE a.user_id = p_user_id
      AND ar.status = 'suggested'
    ORDER BY ar.created_at DESC;
END;
$$;

-- should_propose_agent (was: should_propose_deliverable)
CREATE OR REPLACE FUNCTION should_propose_agent(p_user_id UUID, p_pattern_type TEXT, p_pattern_data JSONB, p_threshold INTEGER DEFAULT 3)
RETURNS BOOLEAN
LANGUAGE plpgsql SECURITY DEFINER
AS $$
DECLARE
    pattern_record user_interaction_patterns;
    existing_proposal agent_proposals;
BEGIN
    SELECT * INTO pattern_record
    FROM user_interaction_patterns
    WHERE user_id = p_user_id
      AND pattern_type = p_pattern_type
      AND pattern_data = p_pattern_data;

    IF NOT FOUND THEN
        RETURN FALSE;
    END IF;

    IF pattern_record.occurrence_count < p_threshold THEN
        RETURN FALSE;
    END IF;

    SELECT * INTO existing_proposal
    FROM agent_proposals
    WHERE user_id = p_user_id
      AND trigger_pattern = p_pattern_type
      AND trigger_evidence @> p_pattern_data
      AND status IN ('pending', 'accepted');

    IF FOUND THEN
        RETURN FALSE;
    END IF;

    RETURN TRUE;
END;
$$;

-- get_or_create_chat_session (recreated with agent_id parameter)
CREATE OR REPLACE FUNCTION get_or_create_chat_session(
    p_user_id UUID,
    p_project_id UUID,
    p_session_type TEXT DEFAULT 'thinking_partner',
    p_scope TEXT DEFAULT 'daily',
    p_inactivity_hours INTEGER DEFAULT 4,
    p_agent_id UUID DEFAULT NULL
)
RETURNS chat_sessions
LANGUAGE plpgsql SECURITY DEFINER
AS $$
DECLARE
    v_session chat_sessions;
    v_inactivity_cutoff TIMESTAMPTZ;
BEGIN
    IF p_scope = 'conversation' THEN
        INSERT INTO chat_sessions (user_id, project_id, session_type, status, agent_id)
        VALUES (p_user_id, p_project_id, p_session_type, 'active', p_agent_id)
        RETURNING * INTO v_session;
        RETURN v_session;
    END IF;

    IF p_scope = 'daily' THEN
        v_inactivity_cutoff := NOW() - (p_inactivity_hours || ' hours')::INTERVAL;

        SELECT * INTO v_session
        FROM chat_sessions
        WHERE user_id = p_user_id
          AND (
              (p_project_id IS NULL AND project_id IS NULL)
              OR project_id = p_project_id
          )
          AND (
              (p_agent_id IS NULL AND agent_id IS NULL)
              OR agent_id = p_agent_id
          )
          AND session_type = p_session_type
          AND status = 'active'
          AND updated_at >= v_inactivity_cutoff
        ORDER BY updated_at DESC
        LIMIT 1;
    ELSIF p_scope = 'project' THEN
        SELECT * INTO v_session
        FROM chat_sessions
        WHERE user_id = p_user_id
          AND (
              (p_project_id IS NULL AND project_id IS NULL)
              OR project_id = p_project_id
          )
          AND (
              (p_agent_id IS NULL AND agent_id IS NULL)
              OR agent_id = p_agent_id
          )
          AND session_type = p_session_type
          AND status = 'active'
        ORDER BY started_at DESC
        LIMIT 1;
    END IF;

    IF v_session.id IS NOT NULL THEN
        RETURN v_session;
    END IF;

    INSERT INTO chat_sessions (user_id, project_id, session_type, status, agent_id)
    VALUES (p_user_id, p_project_id, p_session_type, 'active', p_agent_id)
    RETURNING * INTO v_session;

    RETURN v_session;
END;
$$;

-- ============================================================================
-- PHASE 4: RECREATE VIEW
-- ============================================================================

CREATE VIEW agent_type_metrics AS
SELECT
    a.user_id,
    a.agent_type,
    a.type_tier,
    count(DISTINCT a.id) AS agent_count,
    count(ar.id) AS total_runs,
    count(ar.id) FILTER (WHERE ar.status = 'approved') AS approved_runs,
    count(ar.id) FILTER (WHERE ar.status = 'rejected') AS rejected_runs,
    avg(ar.edit_distance_score) FILTER (WHERE ar.status = 'approved') AS avg_edit_distance,
    count(ar.id) FILTER (WHERE ar.edit_distance_score < 0.3 AND ar.status = 'approved') AS low_edit_count,
    count(ar.id) FILTER (WHERE ar.edit_distance_score >= 0.3 AND ar.status = 'approved') AS high_edit_count
FROM agents a
LEFT JOIN agent_runs ar ON a.id = ar.agent_id
GROUP BY a.user_id, a.agent_type, a.type_tier;

COMMIT;

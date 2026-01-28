-- YARNNN v5 Schema
-- 8 core tables, minimal complexity

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-----------------------------------------------------------
-- 1. WORKSPACES (multi-tenancy root)
-----------------------------------------------------------
CREATE TABLE workspaces (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    owner_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS
ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own workspaces"
    ON workspaces FOR SELECT
    USING (owner_id = auth.uid());

CREATE POLICY "Users can create workspaces"
    ON workspaces FOR INSERT
    WITH CHECK (owner_id = auth.uid());

-----------------------------------------------------------
-- 2. PROJECTS (work containers)
-----------------------------------------------------------
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    description TEXT,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_projects_workspace ON projects(workspace_id);

-- RLS
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view projects in their workspaces"
    ON projects FOR SELECT
    USING (
        workspace_id IN (
            SELECT id FROM workspaces WHERE owner_id = auth.uid()
        )
    );

CREATE POLICY "Users can create projects in their workspaces"
    ON projects FOR INSERT
    WITH CHECK (
        workspace_id IN (
            SELECT id FROM workspaces WHERE owner_id = auth.uid()
        )
    );

-----------------------------------------------------------
-- 3. BLOCKS (atomic knowledge units)
-----------------------------------------------------------
CREATE TABLE blocks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content TEXT NOT NULL,
    block_type TEXT NOT NULL DEFAULT 'text', -- text, structured, extracted
    metadata JSONB DEFAULT '{}',
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_blocks_project ON blocks(project_id);
CREATE INDEX idx_blocks_type ON blocks(block_type);

-- RLS
ALTER TABLE blocks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view blocks in their projects"
    ON blocks FOR SELECT
    USING (
        project_id IN (
            SELECT p.id FROM projects p
            JOIN workspaces w ON p.workspace_id = w.id
            WHERE w.owner_id = auth.uid()
        )
    );

CREATE POLICY "Users can manage blocks in their projects"
    ON blocks FOR ALL
    USING (
        project_id IN (
            SELECT p.id FROM projects p
            JOIN workspaces w ON p.workspace_id = w.id
            WHERE w.owner_id = auth.uid()
        )
    );

-----------------------------------------------------------
-- 4. DOCUMENTS (uploaded files)
-----------------------------------------------------------
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename TEXT NOT NULL,
    file_url TEXT NOT NULL,
    file_type TEXT, -- pdf, docx, xlsx, etc.
    file_size INTEGER,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_documents_project ON documents(project_id);

-- RLS
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view documents in their projects"
    ON documents FOR SELECT
    USING (
        project_id IN (
            SELECT p.id FROM projects p
            JOIN workspaces w ON p.workspace_id = w.id
            WHERE w.owner_id = auth.uid()
        )
    );

CREATE POLICY "Users can manage documents in their projects"
    ON documents FOR ALL
    USING (
        project_id IN (
            SELECT p.id FROM projects p
            JOIN workspaces w ON p.workspace_id = w.id
            WHERE w.owner_id = auth.uid()
        )
    );

-----------------------------------------------------------
-- 5. BLOCK_RELATIONS (semantic links)
-----------------------------------------------------------
CREATE TABLE block_relations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id UUID NOT NULL REFERENCES blocks(id) ON DELETE CASCADE,
    target_id UUID NOT NULL REFERENCES blocks(id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL, -- supports, contradicts, extends, references
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT unique_relation UNIQUE (source_id, target_id, relation_type)
);

CREATE INDEX idx_relations_source ON block_relations(source_id);
CREATE INDEX idx_relations_target ON block_relations(target_id);

-- RLS (inherits from blocks)
ALTER TABLE block_relations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view relations for their blocks"
    ON block_relations FOR SELECT
    USING (
        source_id IN (SELECT id FROM blocks)
    );

-----------------------------------------------------------
-- 6. WORK_TICKETS (work request lifecycle)
-----------------------------------------------------------
CREATE TABLE work_tickets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task TEXT NOT NULL,
    agent_type TEXT NOT NULL, -- research, content, reporting
    status TEXT NOT NULL DEFAULT 'pending', -- pending, running, completed, failed
    parameters JSONB DEFAULT '{}',
    error_message TEXT,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_tickets_project ON work_tickets(project_id);
CREATE INDEX idx_tickets_status ON work_tickets(status);

-- RLS
ALTER TABLE work_tickets ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view tickets in their projects"
    ON work_tickets FOR SELECT
    USING (
        project_id IN (
            SELECT p.id FROM projects p
            JOIN workspaces w ON p.workspace_id = w.id
            WHERE w.owner_id = auth.uid()
        )
    );

CREATE POLICY "Users can manage tickets in their projects"
    ON work_tickets FOR ALL
    USING (
        project_id IN (
            SELECT p.id FROM projects p
            JOIN workspaces w ON p.workspace_id = w.id
            WHERE w.owner_id = auth.uid()
        )
    );

-----------------------------------------------------------
-- 7. WORK_OUTPUTS (agent deliverables)
-----------------------------------------------------------
CREATE TABLE work_outputs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    output_type TEXT NOT NULL, -- text, file
    content TEXT, -- for text outputs
    file_url TEXT, -- for file outputs
    file_format TEXT, -- pdf, pptx, docx, etc.
    ticket_id UUID NOT NULL REFERENCES work_tickets(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_outputs_ticket ON work_outputs(ticket_id);

-- RLS
ALTER TABLE work_outputs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view outputs for their tickets"
    ON work_outputs FOR SELECT
    USING (
        ticket_id IN (
            SELECT wt.id FROM work_tickets wt
            JOIN projects p ON wt.project_id = p.id
            JOIN workspaces w ON p.workspace_id = w.id
            WHERE w.owner_id = auth.uid()
        )
    );

-----------------------------------------------------------
-- 8. AGENT_SESSIONS (execution logs for provenance)
-----------------------------------------------------------
CREATE TABLE agent_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_type TEXT NOT NULL,
    messages JSONB DEFAULT '[]', -- conversation history
    metadata JSONB DEFAULT '{}', -- model, tokens, etc.
    ticket_id UUID REFERENCES work_tickets(id) ON DELETE SET NULL,
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_sessions_project ON agent_sessions(project_id);
CREATE INDEX idx_sessions_ticket ON agent_sessions(ticket_id);

-- RLS
ALTER TABLE agent_sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view sessions in their projects"
    ON agent_sessions FOR SELECT
    USING (
        project_id IN (
            SELECT p.id FROM projects p
            JOIN workspaces w ON p.workspace_id = w.id
            WHERE w.owner_id = auth.uid()
        )
    );

-----------------------------------------------------------
-- FUNCTIONS
-----------------------------------------------------------

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER workspaces_updated_at
    BEFORE UPDATE ON workspaces
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER blocks_updated_at
    BEFORE UPDATE ON blocks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

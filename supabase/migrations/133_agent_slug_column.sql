-- ADR-140: Add slug column to agents table
-- Slugs are used for workspace paths (/agents/{slug}/) and task assignment.
-- Previously assumed but never created as a DB column.

-- 1. Add slug column
ALTER TABLE agents ADD COLUMN IF NOT EXISTS slug TEXT;

-- 2. Populate from title (lowercase, replace non-alphanumeric with hyphens)
UPDATE agents SET slug = lower(regexp_replace(regexp_replace(trim(title), '[^a-zA-Z0-9]', '-', 'g'), '-+', '-', 'g'));

-- 3. Remove trailing hyphens
UPDATE agents SET slug = regexp_replace(slug, '-+$', '');

-- 4. Make unique per user
ALTER TABLE agents ADD CONSTRAINT agents_user_slug_unique UNIQUE (user_id, slug);

-- 5. Create index for slug lookups
CREATE INDEX idx_agents_slug ON agents (user_id, slug);

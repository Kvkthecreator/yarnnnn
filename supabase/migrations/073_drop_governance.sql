-- Migration: 073_drop_governance.sql
-- Removes deprecated governance and governance_ceiling columns
--
-- ADR-066 removed governance gates — all deliverables deliver immediately.
-- Fields were marked deprecated=True in Pydantic models on 2026-02-19.
-- Waiting period complete. Removing columns per CLAUDE.md discipline:
-- "Delete legacy code when replacing with new implementation"

ALTER TABLE deliverables
    DROP COLUMN IF EXISTS governance,
    DROP COLUMN IF EXISTS governance_ceiling;

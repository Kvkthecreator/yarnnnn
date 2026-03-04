-- Drop signal_history table — ADR-092 Phase 5
-- Signal processing dissolved from L3. Coordinator deliverables (L4) replace it.
-- signal_history stored per-item signal triage results from the old signal_extraction service.

DROP TABLE IF EXISTS signal_history;

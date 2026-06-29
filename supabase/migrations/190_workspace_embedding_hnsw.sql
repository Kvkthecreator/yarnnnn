-- 190 — Replace the workspace_files embedding index: ivfflat → HNSW
--
-- ROOT CAUSE (2026-06-29, docs/evaluations/2026-06-29-recall-empty-embedding-gap.md):
-- semantic `recall` returned empty even with embeddings present. The original index
-- (migration 100) is IVFFlat with lists=100:
--
--   CREATE INDEX idx_ws_embedding ON workspace_files
--       USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)
--       WHERE embedding IS NOT NULL;
--
-- IVFFlat partitions vectors into `lists` clusters and only probes the nearest few
-- at query time. With lists=100 but only tens of embedded rows per workspace, the
-- index is pathologically under-trained: most lists are empty, the query probes
-- lists that contain none of the workspace's vectors, and `ORDER BY embedding <=>
-- query LIMIT k` returns ZERO rows — while a seq-scan of the same data returns the
-- correct nearest neighbours. IVFFlat needs thousands of rows for lists=100 to be
-- valid; a per-workspace corpus is far smaller. This never surfaced before because
-- the embedding column was entirely unpopulated (the embed primitive had no caller)
-- — the index was empty, so recall was empty for a *different* reason. Once
-- embeddings exist, the broken index becomes the active failure.
--
-- FIX: HNSW (Hierarchical Navigable Small World). HNSW has NO minimum-rows /
-- training requirement and returns correct nearest-neighbour results at any table
-- size — it is the modern pgvector default for exactly this small-to-mid corpus
-- case. One index, correct at 10 rows or 10M. (m/ef_construction left at pgvector
-- defaults: 16 / 64 — well-suited to this scale; tune only if recall latency ever
-- regresses on a large corpus.)
--
-- The semantic RPC (search_workspace_semantic, ORDER BY embedding <=> query) is
-- unchanged — HNSW serves the same cosine-distance order operator as ivfflat
-- (vector_cosine_ops). No query, no application code changes.

DROP INDEX IF EXISTS idx_ws_embedding;

CREATE INDEX idx_ws_embedding ON workspace_files
    USING hnsw (embedding vector_cosine_ops)
    WHERE embedding IS NOT NULL;

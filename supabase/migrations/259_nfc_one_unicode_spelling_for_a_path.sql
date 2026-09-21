-- 259 — One Unicode spelling for a path: fold the legacy NFD rows to NFC.
--
-- A non-Latin name has two byte forms that render IDENTICALLY. `한` is either
-- one composed syllable (NFC) or three combining jamo (NFD), and nothing
-- compares them equal — Postgres included:
--
--     SELECT '한글' = normalize('한글', NFD);   -- false
--     SELECT length('한글'), length(normalize('한글', NFD));   -- 2, 6
--
-- macOS decomposes filenames, so a Korean file uploaded from Finder landed NFD
-- while the same name typed in the browser landed NFC. Measured 2026-09-21: of
-- four Hangul paths in `workspace_files`, two were NFC (authored in-app) and
-- two NFD (uploaded), and each was findable ONLY in the form it was stored in.
--
-- `path` is the substrate's binding unit (ADR-373), the single-writer unit
-- (ADR-286) and the revision-chain key (ADR-209), so two spellings of one name
-- are two identities. The doors that MINT a path now fold to NFC
-- (`services/naming.py::nfc`, applied at `_filename_to_slug` and
-- `parse_file_reference`, with the TS twin in `web/lib/interop/fileHandle.ts`).
-- This migration moves the rows that predate that fix.
--
-- Scope, measured on production before writing this file:
--   workspace_files          2 rows  (both `archived`)
--   workspace_file_versions  6 rows
-- Both tables move TOGETHER: `workspace_file_versions.path` is the revision
-- chain's key, and folding the head without its history would orphan it.
--
-- Safety:
--   · No NFC target is already taken (verified before writing; re-verified by
--     the guard below, which ABORTS rather than clobbering a live row).
--   · NFC is a no-op for every ASCII path, so the predicate `path <>
--     normalize(path, NFC)` touches nothing Latin — it cannot run away.
--   · Idempotent: re-running matches zero rows.
--
-- The runner supplies the transaction (--single-transaction); this file carries
-- no BEGIN/COMMIT of its own, or --dry-run would apply for real.

-- Guard: refuse to fold a path onto one that already exists. Two rows folding
-- to one key would be a silent merge of two distinct files — the exact failure
-- this migration exists to prevent, arriving by a different door.
DO $$
DECLARE
    collisions int;
BEGIN
    SELECT count(*) INTO collisions
    FROM workspace_files a
    WHERE a.path <> normalize(a.path, NFC)
      AND EXISTS (
        SELECT 1 FROM workspace_files b
        WHERE b.workspace_id = a.workspace_id
          AND b.path = normalize(a.path, NFC)
          AND b.id <> a.id
      );
    IF collisions > 0 THEN
        RAISE EXCEPTION
          'NFC fold would collide on % row(s) — resolve by hand, do not merge', collisions;
    END IF;
END $$;

-- The revision chain first, so no window exists where a head points at a
-- spelling its history does not carry.
UPDATE workspace_file_versions
SET path = normalize(path, NFC)
WHERE path <> normalize(path, NFC);

UPDATE workspace_files
SET path = normalize(path, NFC)
WHERE path <> normalize(path, NFC);

-- Verify in the same transaction: nothing may remain in a second spelling.
DO $$
DECLARE
    remaining int;
BEGIN
    SELECT (SELECT count(*) FROM workspace_files WHERE path <> normalize(path, NFC))
         + (SELECT count(*) FROM workspace_file_versions WHERE path <> normalize(path, NFC))
      INTO remaining;
    IF remaining > 0 THEN
        RAISE EXCEPTION 'NFC fold incomplete — % row(s) still non-NFC', remaining;
    END IF;
END $$;

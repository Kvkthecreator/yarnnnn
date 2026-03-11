-- ADR-108: Migrate user_memory key-value rows → /memory/ filesystem files
-- This is a one-time data migration. After this runs, the application reads
-- from workspace_files /memory/ paths instead of the user_memory table.
-- The user_memory table is NOT dropped yet (Phase 3).

-- For each user with user_memory rows, create three workspace_files:
--   /memory/MEMORY.md     — profile fields (name, role, company, timezone, summary)
--   /memory/preferences.md — tone/verbosity per platform
--   /memory/notes.md       — fact:*, instruction:*, preference:* entries

DO $$
DECLARE
    _user_id uuid;
    _memory_content text;
    _prefs_content text;
    _notes_content text;
    _row record;
    _platform text;
    _prefs_map jsonb;
    _now timestamptz := now();
BEGIN
    -- Process each user that has user_memory rows
    FOR _user_id IN
        SELECT DISTINCT user_id FROM user_memory
    LOOP
        -- 1. Build MEMORY.md from profile keys
        _memory_content := '# About Me' || E'\n';
        FOR _row IN
            SELECT key, value FROM user_memory
            WHERE user_id = _user_id
              AND key IN ('name', 'role', 'company', 'timezone', 'summary')
            ORDER BY
                CASE key
                    WHEN 'name' THEN 1
                    WHEN 'role' THEN 2
                    WHEN 'company' THEN 3
                    WHEN 'timezone' THEN 4
                    WHEN 'summary' THEN 5
                END
        LOOP
            IF _row.value IS NOT NULL AND _row.value != '' THEN
                _memory_content := _memory_content || E'\n' || _row.key || ': ' || _row.value;
            END IF;
        END LOOP;

        -- Only write if there's actual content beyond the header
        IF length(_memory_content) > 13 THEN
            _memory_content := _memory_content || E'\n';
            INSERT INTO workspace_files (user_id, path, content, summary, updated_at)
            VALUES (_user_id, '/memory/MEMORY.md', _memory_content, 'User identity and profile', _now)
            ON CONFLICT (user_id, path) DO UPDATE SET
                content = EXCLUDED.content,
                summary = EXCLUDED.summary,
                updated_at = EXCLUDED.updated_at;
        END IF;

        -- 2. Build preferences.md from tone_*/verbosity_* keys
        _prefs_content := '# Communication Preferences' || E'\n';
        _prefs_map := '{}';

        FOR _row IN
            SELECT key, value FROM user_memory
            WHERE user_id = _user_id
              AND (key LIKE 'tone_%' OR key LIKE 'verbosity_%')
            ORDER BY key
        LOOP
            IF _row.key LIKE 'tone_%' THEN
                _platform := substring(_row.key FROM 6);
                _prefs_map := jsonb_set(
                    _prefs_map,
                    ARRAY[_platform, 'tone'],
                    to_jsonb(_row.value),
                    true
                );
            ELSIF _row.key LIKE 'verbosity_%' THEN
                _platform := substring(_row.key FROM 11);
                _prefs_map := jsonb_set(
                    _prefs_map,
                    ARRAY[_platform, 'verbosity'],
                    to_jsonb(_row.value),
                    true
                );
            END IF;
        END LOOP;

        -- Render preferences markdown from the map
        IF _prefs_map != '{}' THEN
            FOR _platform IN
                SELECT jsonb_object_keys(_prefs_map) ORDER BY 1
            LOOP
                _prefs_content := _prefs_content || E'\n## ' || _platform || E'\n';
                IF _prefs_map->_platform->>'tone' IS NOT NULL THEN
                    _prefs_content := _prefs_content || '- tone: ' || (_prefs_map->_platform->>'tone') || E'\n';
                END IF;
                IF _prefs_map->_platform->>'verbosity' IS NOT NULL THEN
                    _prefs_content := _prefs_content || '- verbosity: ' || (_prefs_map->_platform->>'verbosity') || E'\n';
                END IF;
            END LOOP;

            INSERT INTO workspace_files (user_id, path, content, summary, updated_at)
            VALUES (_user_id, '/memory/preferences.md', _prefs_content, 'Communication and content preferences', _now)
            ON CONFLICT (user_id, path) DO UPDATE SET
                content = EXCLUDED.content,
                summary = EXCLUDED.summary,
                updated_at = EXCLUDED.updated_at;
        END IF;

        -- 3. Build notes.md from fact:*/instruction:*/preference:* keys
        -- Deduplicate by value (the main problem with user_memory)
        _notes_content := '# Notes' || E'\n';
        FOR _row IN
            SELECT DISTINCT ON (value) key, value FROM user_memory
            WHERE user_id = _user_id
              AND (key LIKE 'fact:%' OR key LIKE 'instruction:%' OR key LIKE 'preference:%')
            ORDER BY value, confidence DESC, updated_at DESC
        LOOP
            IF _row.key LIKE 'instruction:%' THEN
                _notes_content := _notes_content || E'\n' || '- Instruction: ' || _row.value;
            ELSIF _row.key LIKE 'preference:%' THEN
                _notes_content := _notes_content || E'\n' || '- Preference: ' || _row.value;
            ELSE
                _notes_content := _notes_content || E'\n' || '- Fact: ' || _row.value;
            END IF;
        END LOOP;

        -- Only write if there are actual notes beyond the header
        IF length(_notes_content) > 9 THEN
            _notes_content := _notes_content || E'\n';
            INSERT INTO workspace_files (user_id, path, content, summary, updated_at)
            VALUES (_user_id, '/memory/notes.md', _notes_content, 'Standing instructions and observed facts', _now)
            ON CONFLICT (user_id, path) DO UPDATE SET
                content = EXCLUDED.content,
                summary = EXCLUDED.summary,
                updated_at = EXCLUDED.updated_at;
        END IF;

    END LOOP;

    RAISE NOTICE 'ADR-108: user_memory → /memory/ filesystem migration complete';
END $$;

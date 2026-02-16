# Prompt Changelog

Track changes to system prompts, tool definitions, and LLM-facing content.

Format: `[YYYY.MM.DD.N]` where N is the revision number for that day.

---

## [2026.02.16.2] - Document reading and tool exhaustion fixes

### Changed
- `api/services/primitives/refs.py`: Added `_enrich_document_with_content()` to fetch chunks when reading documents
- `api/services/primitives/read.py`: Updated tool description to emphasize UUID refs from Search results
- `api/services/primitives/search.py`: Updated tool description to clarify ref workflow
- `api/services/anthropic.py`: Added final text response when max_tool_rounds exhausted
- **Behavior**:
  - Read(ref="document:UUID") now returns full document content, not just metadata
  - Tool descriptions explicitly guide TP to use refs from Search results
  - When tool rounds exhaust, TP now generates a summary instead of silent failure
- **Impact**:
  - TP can now read and summarize uploaded documents
  - No more silent failures when TP uses many tools
  - Clearer workflow: Search → get ref → Read with ref

---

## [2026.02.16.1] - Document content search fix

### Changed
- `api/services/primitives/search.py`: Added `_search_document_content()` function
- **Behavior**: Document search now queries `filesystem_chunks.content` instead of only `filesystem_documents.filename`
- **Impact**: TP can now find content within uploaded PDFs, DOCX, TXT, MD files

---

## [2026.02.15.1] - ADR-058 schema alignment

### Changed
- `api/services/primitives/search.py`: Updated `_search_user_memories()` to query `knowledge_entries` table
- `api/services/primitives/read.py`: Updated memory refs to resolve from `knowledge_entries`
- **Behavior**: Memory/knowledge search uses new ADR-058 schema
- **Impact**: TP working memory injection now pulls from `knowledge_entries`

---

## [2026.02.13.1] - Initial prompt tracking

### Established
- TP system prompt in `api/agents/thinking_partner.py`
- Tool definitions in `api/services/primitives/*.py`:
  - `Search` - Find entities by content
  - `Read` - Retrieve entity by reference
  - `Write` - Create/update entities
  - `Remember` - Store user facts
  - `CreateWork` - Create work tickets
  - `Schedule` - Schedule tasks
- Extraction prompt in `api/services/extraction.py`
- Inference prompt in `api/services/profile_inference.py`

---

## Template

```markdown
## [YYYY.MM.DD.N] - Short description

### Changed
- file.py: What changed
- **Behavior**: How this affects LLM behavior
- **Impact**: User-visible effects

### Added
- New prompt or tool

### Removed
- Deprecated prompt or tool
```

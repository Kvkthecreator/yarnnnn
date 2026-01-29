# Feature: Context & Memory System

**Status:** Planning
**ADR:** [ADR-003-context-memory-architecture](../adr/ADR-003-context-memory-architecture.md)

## Overview

The Context & Memory System is YARNNN's unified approach to capturing, storing, and serving project knowledge to agents. It enables:

1. **Multi-channel input**: Chat, documents, manual entry, external imports
2. **Shared memory**: All agents in a project access the same context
3. **Smart assembly**: Priority-based context retrieval for token-efficient agent calls

## User Stories

### As a user, I want to:
- Add text notes to my project context manually
- Have insights from my ThinkingPartner conversations automatically captured
- Import my Claude/ChatGPT conversations into a project
- Upload documents and have key information extracted
- See all my context in one place, organized by type

### As an agent, I want to:
- Receive relevant project context assembled for my task
- Know the source and confidence of context items
- Access recent context preferentially over stale items

## Architecture

```
                    ┌────────────────────┐
                    │   User Interface   │
                    └─────────┬──────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐   ┌─────────────────┐   ┌───────────────┐
│  Manual Entry │   │  Chat Sessions  │   │  File Upload  │
│   (Context    │   │ (ThinkingPartner│   │  (Documents)  │
│     Tab)      │   │    Agent)       │   │               │
└───────┬───────┘   └────────┬────────┘   └───────┬───────┘
        │                    │                    │
        │           ┌────────▼────────┐           │
        │           │ Async Extraction│           │
        │           │    Service      │◄──────────┘
        │           └────────┬────────┘
        │                    │
        └────────────────────┼────────────────────┘
                             │
                    ┌────────▼────────┐
                    │     Blocks      │
                    │    (Memory)     │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ Context Assembly│
                    │    Service      │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │     Agents      │
                    └─────────────────┘
```

## Data Model

### Blocks (Extended)

```sql
blocks (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL,
    content TEXT NOT NULL,

    -- Type classification
    block_type TEXT DEFAULT 'text',        -- text, structured, extracted
    semantic_type TEXT,                     -- fact, guideline, requirement, insight, note, question

    -- Source tracking
    source_type TEXT DEFAULT 'manual',     -- manual, chat, document, import
    source_ref UUID,                        -- FK to source (session_id, document_id, import_id)

    -- Retrieval scoring
    importance FLOAT DEFAULT 0.5,          -- 0-1, affects retrieval priority

    -- Lifecycle
    expires_at TIMESTAMPTZ,                -- optional TTL for time-bound context
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
)
```

### Semantic Types

| Type | Description | Example |
|------|-------------|---------|
| `fact` | Verified information | "Company founded in 2020" |
| `guideline` | Rule or principle | "Always use formal tone in reports" |
| `requirement` | Must-have constraint | "Report must include executive summary" |
| `insight` | Derived understanding | "Users prefer visual data over tables" |
| `note` | General annotation | "Check with legal before publishing" |
| `question` | Open question | "What is the target audience?" |

### Source Types

| Type | Description | How Created |
|------|-------------|-------------|
| `manual` | User-entered directly | Context tab "Add Block" |
| `chat` | Extracted from conversation | Async extraction after chat |
| `document` | Extracted from uploaded file | Document processing pipeline |
| `import` | From external LLM export | Import feature |

## Phase 1: Manual Blocks (Immediate)

### API Endpoints

Already exist in `/api/routes/context.py`:
- `POST /projects/{id}/blocks` - Create block
- `GET /projects/{id}/blocks` - List blocks
- `DELETE /blocks/{id}` - Delete block

### Schema Migration

```sql
-- Migration: 004_extend_blocks.sql

ALTER TABLE blocks
ADD COLUMN semantic_type TEXT,
ADD COLUMN source_type TEXT DEFAULT 'manual',
ADD COLUMN source_ref UUID,
ADD COLUMN importance FLOAT DEFAULT 0.5,
ADD COLUMN expires_at TIMESTAMPTZ;

CREATE INDEX idx_blocks_semantic_type ON blocks(semantic_type);
CREATE INDEX idx_blocks_source_type ON blocks(source_type);
CREATE INDEX idx_blocks_importance ON blocks(importance);
```

### Frontend: Context Tab

```tsx
function ContextTab({ projectId }: { projectId: string }) {
  const [blocks, setBlocks] = useState<Block[]>([]);
  const [showAddModal, setShowAddModal] = useState(false);

  // Fetch blocks on mount
  useEffect(() => {
    api.blocks.list(projectId).then(setBlocks);
  }, [projectId]);

  return (
    <div>
      <header className="flex justify-between mb-6">
        <h2>Context</h2>
        <div className="flex gap-2">
          <Button onClick={() => setShowAddModal(true)}>+ Add Block</Button>
          <Button variant="outline" disabled>Upload Document</Button>
        </div>
      </header>

      {blocks.length === 0 ? (
        <EmptyState onAdd={() => setShowAddModal(true)} />
      ) : (
        <BlockList blocks={blocks} onDelete={handleDelete} />
      )}

      {showAddModal && (
        <AddBlockModal
          onClose={() => setShowAddModal(false)}
          onCreate={handleCreate}
        />
      )}
    </div>
  );
}
```

### Add Block Modal

```tsx
function AddBlockModal({ onClose, onCreate }) {
  const [content, setContent] = useState('');
  const [semanticType, setSemanticType] = useState('note');

  return (
    <Modal onClose={onClose}>
      <h3>Add Context Block</h3>

      <Label>Type</Label>
      <Select value={semanticType} onChange={setSemanticType}>
        <option value="note">Note</option>
        <option value="fact">Fact</option>
        <option value="guideline">Guideline</option>
        <option value="requirement">Requirement</option>
        <option value="question">Question</option>
      </Select>

      <Label>Content</Label>
      <Textarea
        value={content}
        onChange={e => setContent(e.target.value)}
        placeholder="Enter context information..."
        rows={4}
      />

      <footer>
        <Button variant="outline" onClick={onClose}>Cancel</Button>
        <Button onClick={() => onCreate({ content, semantic_type: semanticType })}>
          Add Block
        </Button>
      </footer>
    </Modal>
  );
}
```

## Phase 2: Chat-Derived Extraction

### Extraction Service

```python
# api/services/extraction.py

import asyncio
from anthropic import Anthropic

EXTRACTION_PROMPT = """Analyze this conversation and extract important context items.

For each item, identify:
- type: fact, guideline, requirement, insight, or question
- content: the actual information (1-2 sentences)
- importance: 0.0-1.0 (how important to remember)

Return JSON array. Only extract genuinely useful information, not chit-chat.

Conversation:
{messages}

Extract:"""

async def extract_from_conversation(
    project_id: str,
    messages: list[dict],
    db_client
) -> list[dict]:
    """Extract context blocks from a conversation."""

    # Format messages for extraction
    formatted = "\n".join([
        f"{m['role'].upper()}: {m['content']}"
        for m in messages[-10:]  # Last 10 messages
    ])

    # Call LLM for extraction
    client = Anthropic()
    response = client.messages.create(
        model="claude-3-haiku-20240307",  # Fast + cheap for extraction
        max_tokens=1000,
        messages=[{
            "role": "user",
            "content": EXTRACTION_PROMPT.format(messages=formatted)
        }]
    )

    # Parse response
    extracted = parse_extraction_response(response.content[0].text)

    # Upsert blocks
    for item in extracted:
        await upsert_block(
            db_client,
            project_id=project_id,
            content=item['content'],
            semantic_type=item['type'],
            source_type='chat',
            importance=item.get('importance', 0.5)
        )

    return extracted
```

### Integration with Chat Route

```python
# In api/routes/chat.py

@router.post("/projects/{project_id}/chat")
async def send_message(project_id: UUID, request: ChatRequest, auth: UserClient):
    # ... existing streaming response code ...

    async def response_stream():
        full_response = ""

        async for chunk in agent.execute_stream(...):
            full_response += chunk
            yield f"data: {json.dumps({'content': chunk})}\n\n"

        yield f"data: {json.dumps({'done': True})}\n\n"

        # Fire-and-forget extraction (doesn't block response)
        messages = request.history + [
            {"role": "user", "content": request.content},
            {"role": "assistant", "content": full_response}
        ]
        asyncio.create_task(
            extract_from_conversation(str(project_id), messages, auth.client)
        )
```

### Context Assembly for Agents

```python
# api/services/context_assembly.py

async def assemble_agent_context(
    db_client,
    project_id: str,
    max_chars: int = 8000
) -> str:
    """Assemble context for agent consumption."""

    # Fetch blocks with priority ordering
    result = db_client.table("blocks")\
        .select("*")\
        .eq("project_id", project_id)\
        .order("importance", desc=True)\
        .order("updated_at", desc=True)\
        .limit(50)\
        .execute()

    blocks = result.data

    # Group by semantic type
    grouped = {}
    for block in blocks:
        st = block.get('semantic_type') or 'note'
        if st not in grouped:
            grouped[st] = []
        grouped[st].append(block['content'])

    # Format for agent
    sections = []
    type_order = ['requirement', 'guideline', 'fact', 'insight', 'note', 'question']

    for st in type_order:
        if st in grouped:
            sections.append(f"## {st.title()}s")
            for content in grouped[st][:10]:  # Max 10 per type
                sections.append(f"- {content}")
            sections.append("")

    context_str = "\n".join(sections)

    # Truncate if needed
    if len(context_str) > max_chars:
        context_str = context_str[:max_chars] + "\n\n[Context truncated]"

    return context_str
```

## Phase 3: Document & Import (Future)

### Document Processing

```python
async def process_document(document_id: str, db_client):
    """Extract text from document and derive blocks."""

    doc = await get_document(document_id, db_client)

    # Extract text based on file type
    if doc['file_type'] == 'pdf':
        text = await extract_pdf_text(doc['file_url'])
    elif doc['file_type'] in ['docx', 'doc']:
        text = await extract_word_text(doc['file_url'])
    else:
        text = await fetch_file_content(doc['file_url'])

    # Store extracted text
    await update_document(document_id, {
        'extracted_text': text,
        'extraction_status': 'completed'
    }, db_client)

    # Extract blocks from text
    await extract_from_text(doc['project_id'], text, 'document', document_id, db_client)
```

### External Import

```python
async def import_claude_conversation(project_id: str, export_json: dict, db_client):
    """Import Claude conversation export."""

    # Parse Claude export format
    messages = []
    for msg in export_json.get('messages', []):
        messages.append({
            'role': msg['role'],
            'content': msg['content'][0]['text'] if isinstance(msg['content'], list) else msg['content']
        })

    # Store import record
    import_id = await create_import(project_id, 'claude', export_json, db_client)

    # Extract blocks
    await extract_from_conversation(
        project_id,
        messages,
        db_client,
        source_type='import',
        source_ref=import_id
    )
```

## UI Mockups

### Context Tab - Block List

```
┌─────────────────────────────────────────────────────────────┐
│ Context                              [+ Add Block] [Upload] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ REQUIREMENT                                    ⋮  [×]   │ │
│ │ Report must include executive summary and key findings  │ │
│ │ 📝 manual · Jan 29                                      │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ FACT                                           ⋮  [×]   │ │
│ │ Target audience is C-level executives                   │ │
│ │ 💬 from chat · Jan 29                                   │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ GUIDELINE                                      ⋮  [×]   │ │
│ │ Use formal tone, avoid jargon                           │ │
│ │ 📄 from document · Jan 28                               │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Add Block Modal

```
┌─────────────────────────────────────────┐
│ Add Context Block                   [×] │
├─────────────────────────────────────────┤
│                                         │
│ Type                                    │
│ ┌─────────────────────────────────────┐ │
│ │ Note                              ▼ │ │
│ └─────────────────────────────────────┘ │
│                                         │
│ Content                                 │
│ ┌─────────────────────────────────────┐ │
│ │                                     │ │
│ │ Enter context information...        │ │
│ │                                     │ │
│ │                                     │ │
│ └─────────────────────────────────────┘ │
│                                         │
│            [Cancel]  [Add Block]        │
└─────────────────────────────────────────┘
```

## Success Metrics

- **Extraction Quality**: >70% of extracted blocks rated "useful" by users
- **Context Coverage**: Agents reference context in >80% of responses
- **Import Adoption**: >30% of users import external conversations
- **Block Growth**: Average project has 20+ blocks after 1 week of use

## Open Questions

1. **Duplicate Detection**: How aggressively should we deduplicate similar blocks?
2. **Expiration**: Should extracted blocks auto-expire after N days?
3. **User Curation**: Should users be able to "pin" important blocks?
4. **Cross-Project**: Future support for sharing context across projects?

## Dependencies

- Anthropic API for extraction (Claude Haiku)
- Supabase Storage for documents
- PDF/DOCX parsing libraries (Phase 3)

# User Flows

End-to-end user journeys through YARNNN.

---

## 1. Document Upload Flow

**Entry**: User clicks "Upload Document" in project or global context

```
User selects file (PDF/DOCX/TXT/MD, max 25MB)
    ↓
Frontend: POST /documents/upload (multipart form)
    ↓
Backend validates:
  - File type allowed
  - File size < 25MB
  - Project exists (if project_id provided)
    ↓
Upload to Supabase Storage: documents/{user_id}/{doc_id}/original.{ext}
    ↓
Create document record (processing_status: pending)
    ↓
Process document (synchronous):
  1. Extract text (PyPDF2/python-docx/plain)
  2. Chunk into ~400 token segments
  3. Generate embeddings for chunks
  4. Store chunks in DB
  5. Extract memories from each chunk (LLM)
  6. Store memories with embeddings
    ↓
Update document status: completed/failed
    ↓
Return: { document_id, filename, processing_status, message }
```

**Key tables**: documents, chunks, memories

**RLS notes**:
- Documents: `user_id = auth.uid()`
- Chunks: via `documents.user_id`
- Memories: `user_id = auth.uid()`
- Service client used for chunk/memory insertion (bypasses RLS after auth)

---

## 2. Chat with Thinking Partner

**Entry**: User opens chat (global or project-scoped)

```
User sends message
    ↓
Frontend: POST /chat/stream (SSE)
  - session_id (existing or create new)
  - project_id (optional)
  - message content
    ↓
Backend:
  1. Get/create chat_session
  2. Store user message in session_messages
  3. Retrieve context:
     - User memories (project_id IS NULL)
     - Project memories (if project_id)
     - Recent session messages
  4. Build system prompt with context
  5. Stream response from Claude
  6. Store assistant message
  7. Async: Extract memories from conversation
    ↓
SSE stream to frontend
    ↓
Context extraction (background):
  - LLM extracts facts/preferences
  - Deduplicates against existing
  - Stores as memories (user or project scoped)
```

**Key tables**: chat_sessions, session_messages, memories

---

## 3. Memory Management

### 3a. Manual Memory Creation

```
User enters memory content + optional tags
    ↓
POST /memories
    ↓
Generate embedding
    ↓
Store memory (source_type: manual)
```

### 3b. Bulk Import

```
User pastes text blob
    ↓
POST /memories/bulk
    ↓
LLM extracts multiple memories
    ↓
Deduplicate against existing
    ↓
Store with embeddings (source_type: bulk)
```

### 3c. Memory Retrieval for Context

```
Query arrives (chat message or search)
    ↓
Generate query embedding
    ↓
Semantic search (pgvector cosine similarity)
    ↓
Score: 0.7 * similarity + 0.3 * importance
    ↓
Return top N relevant memories
```

---

## 4. Project Creation

```
User creates project
    ↓
POST /projects
    ↓
Create project in user's workspace
    ↓
Project starts with:
  - No project-scoped memories
  - Access to user-scoped memories
  - Empty document list
```

---

## 5. Subscription Flow (Lemon Squeezy)

### 5a. Upgrade to Pro

```
User clicks "Upgrade" in settings
    ↓
GET /subscription/checkout?variant_id={monthly|yearly}
    ↓
Redirect to Lemon Squeezy checkout
    ↓
User completes payment
    ↓
LS webhook: subscription_created
    ↓
Backend updates workspace:
  - subscription_status: pro
  - subscription_expires_at
  - lemonsqueezy_subscription_id
    ↓
Log event in subscription_events
```

### 5b. Manage Subscription

```
User clicks "Manage" in settings
    ↓
GET /subscription/portal
    ↓
Redirect to LS customer portal
    ↓
User cancels/updates
    ↓
LS webhook: subscription_updated/cancelled
    ↓
Backend updates workspace status
```

---

## 6. Onboarding Flow

```
New user signs up
    ↓
Check onboarding state:
  - memory_count
  - document_count
  - has_recent_chat
    ↓
State: cold_start (0 memories, 0 docs, no chat)
  → Show starter prompts
  → Suggest document upload
  → Guide first conversation
    ↓
State: minimal_context (< 5 memories)
  → Continue onboarding hints
    ↓
State: active (5+ memories)
  → Full experience
```

---

## Data Flow Summary

```
                    ┌─────────────┐
                    │   User      │
                    └─────┬───────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
   ┌─────────┐      ┌─────────┐      ┌─────────┐
   │  Chat   │      │Document │      │ Manual  │
   │ Session │      │ Upload  │      │ Memory  │
   └────┬────┘      └────┬────┘      └────┬────┘
        │                │                │
        │           ┌────┴────┐           │
        │           │ Chunks  │           │
        │           └────┬────┘           │
        │                │                │
        └────────────────┼────────────────┘
                         ▼
                   ┌───────────┐
                   │ Memories  │ (unified storage)
                   │           │
                   │ user_id   │ (ownership)
                   │ project_id│ (scope: null=user, else=project)
                   │ embedding │ (semantic search)
                   └───────────┘
                         │
                         ▼
                   ┌───────────┐
                   │  Context  │ (retrieval for chat)
                   │  Bundle   │
                   └───────────┘
```

---

## Error Handling

| Flow | Error | User Experience |
|------|-------|-----------------|
| Document upload | File too large | "File too large. Maximum size is 25MB" |
| Document upload | Unsupported type | "Unsupported file type. Allowed: PDF, DOCX, TXT, MD" |
| Document upload | Extraction failed | Status: failed, error_message in record |
| Chat | Context fetch fails | Gracefully continue without context |
| Memory | Duplicate detected | Silently skip (deduplication) |
| Subscription | Webhook failure | Retry with exponential backoff |

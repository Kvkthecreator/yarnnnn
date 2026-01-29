# Frontend Document Integration Design

**Date:** 2026-01-29
**Status:** Proposed
**Related:** ADR-008 (Document Pipeline)

---

## Philosophy: Beyond the Claude Cowork Pattern

The Claude Desktop "Cowork" interface offers quick actions ("Create a file", "Crunch data", "Prep for a meeting") as prominent UI elements. While visually appealing, this pattern:

1. **Adds cognitive overhead** - User must choose before engaging
2. **Creates artificial separation** - Actions feel disconnected from conversation
3. **Assumes task clarity** - User already knows what they want to do

### YARNNN's Approach: Conversation-First Context Loading

YARNNN's core experience is the **Thinking Partner chat**. Documents should feel like **giving the TP more to work with** - not a separate "document management" feature.

**Key insight:** Users don't want to "upload documents." They want the TP to **know their work**.

---

## User Mental Models

### New User (Cold Start)
```
"I just signed up. The TP doesn't know anything about me or my work."

→ Need: Easy way to share existing context quickly
→ Solution: Onboarding flow that encourages context seeding
```

### Returning User (Adding Context)
```
"I'm working on a project and want the TP to reference this document."

→ Need: Quick upload without leaving the conversation
→ Solution: Drop zone in chat or dedicated upload in context panel
```

### Power User (Managing Knowledge)
```
"I want to see what the TP knows and where it came from."

→ Need: View and manage documents and extracted memories
→ Solution: Documents list with memory lineage
```

---

## Proposed Touch Points

### 1. Dashboard Onboarding (New Users)

**When:** User has no memories and no documents

**UI:** Replace empty chat state with onboarding prompt

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│     Welcome to YARNNN                                   │
│                                                         │
│     Help me get to know you better. You can:            │
│                                                         │
│     📄 Upload documents                                 │
│        Share PDFs, docs, or notes about your work       │
│                                                         │
│     ✏️  Tell me about yourself                          │
│        Start a conversation to share context            │
│                                                         │
│     📋 Paste text                                       │
│        Import notes, meeting transcripts, or briefs     │
│                                                         │
│                          [Skip for now]                 │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Behavior:**
- "Upload documents" → Opens file picker, uploads to user-scope (no project)
- "Tell me about yourself" → Focus chat input, hide prompt
- "Paste text" → Opens bulk import modal
- "Skip for now" → Dismisses prompt, shows normal chat

### 2. Chat Interface Drop Zone

**When:** Always available in chat

**UI:** Subtle drop zone indicator when dragging file over chat

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  [Previous messages...]                                 │
│                                                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │                                                   │  │
│  │        Drop file here to add context              │  │
│  │        PDF, DOCX, TXT supported                   │  │
│  │                                                   │  │
│  └───────────────────────────────────────────────────┘  │
│                                                         │
│  [Message input]  [📎] [Send]                           │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Behavior:**
- Drag file over chat area → Shows drop zone overlay
- Drop file → Uploads, shows processing indicator inline
- Processing complete → Shows confirmation in chat: "✓ Uploaded project_brief.pdf - extracted 5 memories"
- 📎 button → Alternative click-to-upload

**Scoping:**
- Dashboard chat (no project) → User-scoped document
- Project chat → Project-scoped document

### 3. Context Panel Documents Section

**When:** Viewing "About You" or "Context" tab

**UI:** Documents grouped with memories they produced

```
┌─────────────────────────────────────────────────────────┐
│  About You                                              │
│  ─────────────────────────────────────────────────────  │
│                                                         │
│  📁 Documents                               [+ Upload]  │
│  ─────────────────────────────────────────────────────  │
│                                                         │
│  📄 project_brief.pdf                                   │
│     Uploaded Jan 29 · 5 memories extracted              │
│     [View] [Download] [Delete]                          │
│                                                         │
│  📄 meeting_notes.docx                                  │
│     Uploaded Jan 28 · 3 memories extracted              │
│     [View] [Download] [Delete]                          │
│                                                         │
│  ─────────────────────────────────────────────────────  │
│                                                         │
│  🏷️ Memories                                            │
│  ─────────────────────────────────────────────────────  │
│                                                         │
│  [existing memory list...]                              │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Behavior:**
- "+ Upload" → File picker
- "View" → Expand to show document's extracted memories
- "Download" → Signed URL download
- "Delete" → Confirmation, removes document (memories persist)

### 4. Processing Feedback

**During upload and processing:**

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  📄 Uploading project_brief.pdf...                      │
│  ████████████████░░░░░░░░░░░░░░░░  45%                  │
│                                                         │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                                                         │
│  📄 Processing project_brief.pdf                        │
│  ⏳ Extracting text...                                  │
│                                                         │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                                                         │
│  ✓ project_brief.pdf ready                              │
│    Extracted 5 memories · 2,450 words                   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Error state:**

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  ⚠️ Failed to process document.pdf                      │
│     Could not extract text from this file               │
│     [Try again] [Remove]                                │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## User Workflows

### Workflow 1: New User Onboarding

```
1. User signs up, lands on Dashboard
2. Sees onboarding prompt (no context yet)
3. Clicks "Upload documents"
4. Selects a PDF about their company/project
5. Sees processing indicator
6. Processing completes, memories extracted
7. Onboarding prompt replaced with chat
8. Chat shows: "I've learned about [extracted entities]. What are you working on?"
9. User starts conversing with context-aware TP
```

### Workflow 2: Adding Context Mid-Conversation

```
1. User is chatting with TP about a project
2. TP asks: "Do you have any documentation about the requirements?"
3. User drags requirements.pdf into chat
4. Drop zone appears, user drops file
5. Inline message: "📄 Uploading requirements.pdf..."
6. Processing completes: "✓ requirements.pdf - 8 memories extracted"
7. User continues: "Now that you have the requirements..."
8. TP responds with context from the document
```

### Workflow 3: Reviewing What TP Knows

```
1. User navigates to Dashboard → Context tab
2. Sees Documents section with uploaded files
3. Clicks "View" on a document
4. Expands to show memories extracted from that document
5. Can delete individual memories if incorrect
6. Can re-upload if original was updated
```

---

## Implementation Phases

### Phase 1: Core Upload (MVP) ✅ Complete

**Components:**
- [x] `DocumentList.tsx` - Combined upload + list + status (simplified from separate components)
- [x] `useDocuments.ts` - Hook with upload progress tracking

**API Client Updates:**
- [x] Update `api.documents` endpoints to match new routes
- [x] Add user-scoped document endpoints (no project required)

**Integration:**
- [x] Add Documents section to `UserContextPanel.tsx`
- [x] Upload button in section header

**Commit:** `4e9ce58`

### Phase 2: Chat Drop Zone ✅ Complete

**Components:**
- [x] Update `Chat.tsx` to handle file drops (inline, no separate component)
- [x] Inline upload message in chat stream

**UX:**
- [x] Drag detection on chat container
- [x] Visual feedback during drag (full-screen overlay with dashed border)
- [x] Processing indicator in message stream

**Commit:** `73aa014`

### Phase 3: Onboarding Flow

**Components:**
- [ ] `OnboardingPrompt.tsx` - New user welcome with CTAs
- [ ] `BulkImportModal.tsx` - Text paste for quick import

**Logic:**
- [ ] Detect "cold start" (no memories, no documents)
- [ ] Show onboarding instead of empty chat
- [ ] Dismiss on first action or explicit skip

### Phase 4: Polish

- [ ] Document detail view (expand to see memories)
- [ ] Re-process button for failed documents
- [ ] Memory lineage (link memory → source document)
- [ ] Mobile-optimized upload experience

---

## Technical Notes

### API Endpoints (ADR-008)

```typescript
// New document endpoints (api/routes/documents.py)
POST   /api/documents/upload          // Multipart file + optional project_id
GET    /api/documents                 // List user's documents
GET    /api/documents/{id}            // Get with stats
GET    /api/documents/{id}/download   // Signed download URL
DELETE /api/documents/{id}            // Delete (cascades chunks)
```

### Updated Types

```typescript
// types/index.ts additions
export interface Document {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  storage_path: string;
  project_id?: string;        // null = user-scoped
  processing_status: "pending" | "processing" | "completed" | "failed";
  processed_at?: string;
  error_message?: string;
  page_count?: number;
  word_count?: number;
  created_at: string;
}

export interface DocumentDetail extends Document {
  chunk_count: number;
  memory_count: number;
}

export interface UploadResponse {
  document_id: string;
  filename: string;
  processing_status: string;
  message: string;
}
```

### API Client Updates

```typescript
// lib/api/client.ts - updated documents section
documents: {
  // User's documents (all scopes)
  list: (projectId?: string) =>
    request<Document[]>(`/api/documents${projectId ? `?project_id=${projectId}` : ""}`),

  // Upload (project_id in FormData)
  upload: async (file: File, projectId?: string) => {
    const headers = await getAuthHeaders();
    delete (headers as Record<string, string>)["Content-Type"];

    const formData = new FormData();
    formData.append("file", file);
    if (projectId) formData.append("project_id", projectId);

    const response = await fetch(`${API_BASE_URL}/api/documents/upload`, {
      method: "POST",
      credentials: "include",
      headers,
      body: formData,
    });

    if (!response.ok) throw new APIError(...);
    return response.json() as Promise<UploadResponse>;
  },

  // Get with stats
  get: (documentId: string) =>
    request<DocumentDetail>(`/api/documents/${documentId}`),

  // Download URL
  download: (documentId: string) =>
    request<{ url: string; expires_in: number }>(`/api/documents/${documentId}/download`),

  // Delete
  delete: (documentId: string) =>
    request<{ success: boolean }>(`/api/documents/${documentId}`, { method: "DELETE" }),
},
```

### State Management

```typescript
// hooks/useDocuments.ts
export function useDocuments(projectId?: string) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [uploadProgress, setUploadProgress] = useState<UploadProgress | null>(null);

  const load = useCallback(async () => { ... }, [projectId]);

  const upload = useCallback(async (file: File) => {
    setUploadProgress({ filename: file.name, status: "uploading" });
    const result = await api.documents.upload(file, projectId);
    setUploadProgress({ filename: file.name, status: result.processing_status, ...result });
    await load(); // Refresh list
    return result;
  }, [projectId, load]);

  const remove = useCallback(async (documentId: string) => { ... }, [load]);

  return { documents, isLoading, uploadProgress, upload, remove, reload: load };
}
```

---

## Open Questions

1. **Should memories persist when document is deleted?**
   - Current: Yes (memories are extracted knowledge)
   - Alternative: Offer "delete document + memories" option

2. **How to handle duplicate uploads?**
   - Same filename = overwrite? Or reject?
   - Content hash deduplication?

3. **Mobile upload experience?**
   - Drop zone doesn't work on mobile
   - File picker is the primary path
   - Camera capture for photos of documents?

4. **Large file handling?**
   - Current limit: 25MB
   - Should we show estimated processing time?
   - Background processing with polling?

---

## Success Metrics

- **Onboarding completion:** % of new users who upload a document or paste text
- **Context density:** Average memories per user after 7 days
- **Upload success rate:** % of uploads that complete successfully
- **TP relevance:** User satisfaction with context-aware responses

---

## References

- [ADR-008: Document Pipeline](../adr/ADR-008-document-pipeline.md)
- [ADR-005: Unified Memory](../adr/ADR-005-unified-memory-with-embeddings.md)
- [Roadmap](../roadmap/v5-next-steps.md)

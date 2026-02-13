"""
Document Processing Service

ADR-005: Unified memory with embeddings
Handles document upload, parsing, chunking, and memory extraction.
"""

import io
from typing import Optional
from datetime import datetime

from services.embeddings import get_embedding, get_embeddings_batch
from services.extraction import extract_memories_from_text


# =============================================================================
# TEXT EXTRACTION
# =============================================================================

async def extract_text_from_pdf(file_content: bytes) -> tuple[str, int]:
    """
    Extract text from PDF file.

    Returns:
        Tuple of (extracted_text, page_count)
    """
    try:
        from PyPDF2 import PdfReader

        reader = PdfReader(io.BytesIO(file_content))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)

        return "\n\n".join(pages), len(reader.pages)
    except Exception as e:
        print(f"PDF extraction failed: {e}")
        return "", 0


async def extract_text_from_docx(file_content: bytes) -> tuple[str, int]:
    """
    Extract text from DOCX file.

    Returns:
        Tuple of (extracted_text, paragraph_count)
    """
    try:
        import docx

        doc = docx.Document(io.BytesIO(file_content))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]

        return "\n\n".join(paragraphs), len(paragraphs)
    except Exception as e:
        print(f"DOCX extraction failed: {e}")
        return "", 0


async def extract_text_from_txt(file_content: bytes) -> tuple[str, int]:
    """
    Extract text from plain text file.

    Returns:
        Tuple of (text, line_count)
    """
    try:
        text = file_content.decode("utf-8")
        lines = text.split("\n")
        return text, len(lines)
    except Exception as e:
        print(f"TXT extraction failed: {e}")
        return "", 0


async def extract_text(file_content: bytes, file_type: str) -> tuple[str, int]:
    """
    Extract text from file based on type.

    Args:
        file_content: Raw file bytes
        file_type: File extension (pdf, docx, txt, etc.)

    Returns:
        Tuple of (extracted_text, unit_count)
    """
    file_type = file_type.lower().strip(".")

    if file_type == "pdf":
        return await extract_text_from_pdf(file_content)
    elif file_type in ("docx", "doc"):
        return await extract_text_from_docx(file_content)
    elif file_type in ("txt", "md", "markdown"):
        return await extract_text_from_txt(file_content)
    else:
        # Try as plain text
        return await extract_text_from_txt(file_content)


# =============================================================================
# CHUNKING
# =============================================================================

def semantic_chunk(
    text: str,
    target_tokens: int = 400,
    overlap_ratio: float = 0.1
) -> list[dict]:
    """
    Split text into semantic chunks.

    Uses paragraph boundaries when possible, falls back to sentence splitting.

    Args:
        text: Full document text
        target_tokens: Target tokens per chunk (~4 chars per token)
        overlap_ratio: Overlap between chunks (0-1)

    Returns:
        List of dicts with: content, chunk_index, token_count
    """
    target_chars = target_tokens * 4
    overlap_chars = int(target_chars * overlap_ratio)

    # Split by paragraphs first
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks = []
    current_chunk = ""
    chunk_index = 0

    for para in paragraphs:
        # If adding this paragraph exceeds target, start new chunk
        if current_chunk and len(current_chunk) + len(para) > target_chars:
            chunks.append({
                "content": current_chunk.strip(),
                "chunk_index": chunk_index,
                "token_count": len(current_chunk) // 4
            })
            chunk_index += 1

            # Keep overlap from end of previous chunk
            if overlap_chars > 0 and len(current_chunk) > overlap_chars:
                current_chunk = current_chunk[-overlap_chars:] + "\n\n" + para
            else:
                current_chunk = para
        else:
            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para

    # Don't forget the last chunk
    if current_chunk.strip():
        chunks.append({
            "content": current_chunk.strip(),
            "chunk_index": chunk_index,
            "token_count": len(current_chunk) // 4
        })

    return chunks


# =============================================================================
# DOCUMENT PROCESSING PIPELINE
# =============================================================================

async def process_document(
    document_id: str,
    file_content: bytes,
    file_type: str,
    project_id: str,
    user_id: str,
    db_client
) -> dict:
    """
    Full document processing pipeline:
    1. Extract text from file
    2. Chunk into segments
    3. Generate embeddings for chunks
    4. Store chunks
    5. Extract memories from chunks
    6. Update document status

    Args:
        document_id: Document UUID
        file_content: Raw file bytes
        file_type: File extension
        project_id: Project UUID
        user_id: User UUID
        db_client: Supabase client

    Returns:
        Dict with processing results
    """
    try:
        # Update status to processing
        db_client.table("filesystem_documents").update({
            "processing_status": "processing"
        }).eq("id", document_id).execute()

        # 1. Extract text
        text, unit_count = await extract_text(file_content, file_type)

        if not text or len(text) < 50:
            db_client.table("filesystem_documents").update({
                "processing_status": "failed",
                "error_message": "No text could be extracted from document"
            }).eq("id", document_id).execute()
            return {"success": False, "error": "No text extracted"}

        # Estimate word count
        word_count = len(text.split())

        # 2. Chunk text
        chunks = semantic_chunk(text)

        if not chunks:
            db_client.table("filesystem_documents").update({
                "processing_status": "failed",
                "error_message": "Failed to chunk document"
            }).eq("id", document_id).execute()
            return {"success": False, "error": "Chunking failed"}

        # 3. Generate embeddings for all chunks
        chunk_texts = [c["content"] for c in chunks]
        try:
            embeddings = await get_embeddings_batch(chunk_texts)
        except Exception as e:
            print(f"Embedding generation failed: {e}")
            embeddings = [None] * len(chunks)

        # 4. Store chunks
        chunks_inserted = 0
        for i, chunk in enumerate(chunks):
            chunk_record = {
                "document_id": document_id,
                "content": chunk["content"],
                "chunk_index": chunk["chunk_index"],
                "token_count": chunk["token_count"],
                "metadata": {}
            }

            if embeddings[i]:
                chunk_record["embedding"] = embeddings[i]

            try:
                db_client.table("filesystem_chunks").insert(chunk_record).execute()
                chunks_inserted += 1
            except Exception as e:
                print(f"Failed to insert chunk {i}: {e}")

        # 5. Extract memories from chunks
        memories_inserted = 0
        for chunk in chunks:
            try:
                memories = await extract_memories_from_text(chunk["content"])

                for mem in memories:
                    # For documents, project-scoped memories go to this project
                    mem_project_id = None if mem["scope"] == "user" else project_id

                    # Generate embedding
                    try:
                        embedding = await get_embedding(mem["content"])
                    except:
                        embedding = None

                    record = {
                        "user_id": user_id,
                        "domain_id": mem_project_id,  # project_id → domain_id
                        "content": mem["content"],
                        "tags": mem["tags"],
                        "importance": mem["importance"],
                        "source": "document",  # ADR-058
                        "entry_type": "fact",
                        "source_ref": {
                            "document_id": document_id,
                            "chunk_index": chunk["chunk_index"]
                        }
                    }

                    if embedding:
                        record["embedding"] = embedding

                    db_client.table("knowledge_entries").insert(record).execute()
                    memories_inserted += 1

            except Exception as e:
                print(f"Memory extraction from chunk failed: {e}")

        # 6. Update document status
        db_client.table("filesystem_documents").update({
            "processing_status": "completed",
            "processed_at": datetime.utcnow().isoformat(),
            "page_count": unit_count if file_type == "pdf" else None,
            "word_count": word_count,
            "error_message": None
        }).eq("id", document_id).execute()

        return {
            "success": True,
            "chunks_created": chunks_inserted,
            "memories_extracted": memories_inserted,
            "word_count": word_count
        }

    except Exception as e:
        # Update status to failed
        db_client.table("filesystem_documents").update({
            "processing_status": "failed",
            "error_message": str(e)
        }).eq("id", document_id).execute()

        return {"success": False, "error": str(e)}

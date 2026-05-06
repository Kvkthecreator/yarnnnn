'use client';

/**
 * Shared file attachment handling for chat surfaces.
 *
 * ADR-249: Two-Intent File Handling.
 * - Images: base64 inline (ephemeral, Claude vision, unchanged)
 * - Documents: ephemeral via POST /chat/attach → Anthropic Files API file_id
 *   returned as FileAttachment for inclusion in ChatRequest.file_attachments.
 *   Nothing persisted to workspace.
 *
 * Supports:
 * - Click-to-upload (paperclip / file input)
 * - Drag-and-drop onto chat area
 * - Clipboard paste (Cmd+V / Ctrl+V) — images only
 * - File size validation
 * - Preview thumbnails for images
 */

import { useState, useRef, useCallback } from 'react';
import type { TPImageAttachment } from '@/types/desk';

const MAX_IMAGE_SIZE = 5 * 1024 * 1024;  // 5MB — Claude API limit for images
const MAX_DOC_SIZE = 20 * 1024 * 1024;   // 20MB — Anthropic Files API limit
const IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
const DOCUMENT_TYPES = [
  'application/pdf',
  'text/plain',
  'text/markdown',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
];
const DOCUMENT_EXTENSIONS = ['.pdf', '.txt', '.md', '.docx'];

function isImage(file: File): boolean {
  return IMAGE_TYPES.includes(file.type) || file.type.startsWith('image/');
}

function isDocument(file: File): boolean {
  if (DOCUMENT_TYPES.includes(file.type)) return true;
  const ext = '.' + file.name.split('.').pop()?.toLowerCase();
  return DOCUMENT_EXTENSIONS.includes(ext);
}

/** Ephemeral document attachment — either a Files API file_id or extracted text. */
export interface EphemeralDocAttachment {
  filename: string;
  status: 'uploading' | 'done' | 'error';
  /** Returned when attachment type is "file_id" (PDF, TXT, MD) */
  file_id?: string;
  mime_type?: string;
  /** Returned when attachment type is "text_block" (DOCX) */
  content?: string;
}

export interface DropZoneProps {
  onDragEnter: (e: React.DragEvent) => void;
  onDragOver: (e: React.DragEvent) => void;
  onDragLeave: (e: React.DragEvent) => void;
  onDrop: (e: React.DragEvent) => void;
}

export interface UseFileAttachmentsReturn {
  /** Image files (for base64 inline path) */
  attachments: File[];
  attachmentPreviews: string[];
  isDragging: boolean;
  error: string | null;
  /** Ephemeral document attachments (for Files API path) */
  docAttachments: EphemeralDocAttachment[];

  dropZoneProps: DropZoneProps;
  handleFileSelect: (e: React.ChangeEvent<HTMLInputElement>) => void;
  handlePaste: (e: React.ClipboardEvent) => void;
  removeAttachment: (index: number) => void;
  removeDocAttachment: (filename: string) => void;
  clearAttachments: () => void;
  /** Returns Claude API-ready image blocks for base64 images */
  getImagesForAPI: () => Promise<TPImageAttachment[]>;
  /** Returns file_attachment objects ready for ChatRequest.file_attachments */
  getDocAttachmentsForAPI: () => Array<{ file_id: string; filename: string; mime_type: string }>;
  /** Returns DOCX text-block content for appending to message text */
  getDocxTextBlocks: () => Array<{ filename: string; content: string }>;

  fileInputRef: React.RefObject<HTMLInputElement>;
}

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      resolve(result.split(',')[1]);
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

function addPreview(file: File, setter: React.Dispatch<React.SetStateAction<string[]>>) {
  const reader = new FileReader();
  reader.onload = (e) => {
    setter((prev) => [...prev, e.target?.result as string]);
  };
  reader.readAsDataURL(file);
}

export function useFileAttachments(): UseFileAttachmentsReturn {
  const [attachments, setAttachments] = useState<File[]>([]);
  const [attachmentPreviews, setAttachmentPreviews] = useState<string[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [docAttachments, setDocAttachments] = useState<EphemeralDocAttachment[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dragCounterRef = useRef(0);

  const showError = useCallback((msg: string) => {
    setError(msg);
    setTimeout(() => setError(null), 5000);
  }, []);

  const attachDocument = useCallback(async (file: File) => {
    const { api } = await import('@/lib/api/client');
    setDocAttachments((prev) => [...prev, { filename: file.name, status: 'uploading' }]);
    try {
      const result = await api.chat.attach(file);
      setDocAttachments((prev) =>
        prev.map((d) =>
          d.filename === file.name
            ? {
                filename: file.name,
                status: 'done' as const,
                file_id: result.file_id,
                mime_type: result.mime_type,
                content: result.content,
              }
            : d
        )
      );
    } catch {
      setDocAttachments((prev) =>
        prev.map((d) =>
          d.filename === file.name ? { ...d, status: 'error' as const } : d
        )
      );
      showError(`Failed to attach ${file.name}`);
    }
  }, [showError]);

  const addFiles = useCallback(
    (files: File[]) => {
      const images: File[] = [];
      const docs: File[] = [];
      let hasUnsupported = false;

      for (const file of files) {
        if (isImage(file)) {
          if (file.size > MAX_IMAGE_SIZE) {
            showError('Images must be under 5MB');
            continue;
          }
          images.push(file);
        } else if (isDocument(file)) {
          if (file.size > MAX_DOC_SIZE) {
            showError('Documents must be under 20MB');
            continue;
          }
          docs.push(file);
        } else {
          hasUnsupported = true;
        }
      }

      if (images.length > 0) {
        images.forEach((f) => addPreview(f, setAttachmentPreviews));
        setAttachments((prev) => [...prev, ...images]);
      }

      // Ephemeral path: upload to Anthropic Files API via /chat/attach
      if (docs.length > 0) {
        docs.forEach((f) => attachDocument(f));
      }

      if (hasUnsupported) {
        showError('Some files skipped — supported: images, PDF, DOCX, TXT, MD.');
      }
    },
    [showError, attachDocument]
  );

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      addFiles(Array.from(e.target.files || []));
      if (fileInputRef.current) fileInputRef.current.value = '';
    },
    [addFiles]
  );

  const handlePaste = useCallback(
    (e: React.ClipboardEvent) => {
      const files = Array.from(e.clipboardData.files);
      if (files.length === 0) return;
      const imageFiles = files.filter((f) => isImage(f));
      if (imageFiles.length === 0) return;
      e.preventDefault();
      addFiles(imageFiles);
    },
    [addFiles]
  );

  const onDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounterRef.current++;
    if (dragCounterRef.current === 1) setIsDragging(true);
  }, []);

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const onDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounterRef.current--;
    if (dragCounterRef.current === 0) setIsDragging(false);
  }, []);

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      dragCounterRef.current = 0;
      setIsDragging(false);
      addFiles(Array.from(e.dataTransfer.files));
    },
    [addFiles]
  );

  const removeAttachment = useCallback((index: number) => {
    setAttachments((prev) => prev.filter((_, i) => i !== index));
    setAttachmentPreviews((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const removeDocAttachment = useCallback((filename: string) => {
    setDocAttachments((prev) => prev.filter((d) => d.filename !== filename));
  }, []);

  const clearAttachments = useCallback(() => {
    setAttachments([]);
    setAttachmentPreviews([]);
    setDocAttachments([]);
  }, []);

  const getImagesForAPI = useCallback(async (): Promise<TPImageAttachment[]> => {
    const images: TPImageAttachment[] = [];
    for (const file of attachments) {
      const base64 = await fileToBase64(file);
      const mediaType = file.type as TPImageAttachment['mediaType'];
      if (IMAGE_TYPES.includes(mediaType)) {
        images.push({ data: base64, mediaType });
      }
    }
    return images;
  }, [attachments]);

  const getDocAttachmentsForAPI = useCallback(
    () =>
      docAttachments
        .filter((d) => d.status === 'done' && d.file_id)
        .map((d) => ({
          file_id: d.file_id!,
          filename: d.filename,
          mime_type: d.mime_type || 'application/octet-stream',
        })),
    [docAttachments]
  );

  const getDocxTextBlocks = useCallback(
    () =>
      docAttachments
        .filter((d) => d.status === 'done' && d.content)
        .map((d) => ({ filename: d.filename, content: d.content! })),
    [docAttachments]
  );

  return {
    attachments,
    attachmentPreviews,
    isDragging,
    error,
    docAttachments,
    dropZoneProps: { onDragEnter, onDragOver, onDragLeave, onDrop },
    handleFileSelect,
    handlePaste,
    removeAttachment,
    removeDocAttachment,
    clearAttachments,
    getImagesForAPI,
    getDocAttachmentsForAPI,
    getDocxTextBlocks,
    fileInputRef,
  };
}

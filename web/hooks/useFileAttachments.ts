'use client';

/**
 * Shared file attachment handling for chat surfaces.
 *
 * Supports:
 * - Click-to-upload (paperclip / file input)
 * - Drag-and-drop onto chat area
 * - Clipboard paste (Cmd+V / Ctrl+V)
 * - File size validation (5MB limit)
 * - Preview thumbnails
 */

import { useState, useRef, useCallback } from 'react';
import type { TPImageAttachment } from '@/types/desk';

const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5MB — Claude API limit for images
const MAX_DOC_SIZE = 20 * 1024 * 1024; // 20MB — document upload limit
const IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
const DOCUMENT_TYPES = ['application/pdf', 'text/plain', 'text/markdown',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document']; // pdf, txt, md, docx

export interface DropZoneProps {
  onDragEnter: (e: React.DragEvent) => void;
  onDragOver: (e: React.DragEvent) => void;
  onDragLeave: (e: React.DragEvent) => void;
  onDrop: (e: React.DragEvent) => void;
}

export interface UseFileAttachmentsReturn {
  attachments: File[];
  attachmentPreviews: string[];
  isDragging: boolean;
  error: string | null;
  /** Documents uploaded via drag-and-drop (non-image files) */
  uploadedDocs: Array<{ name: string; status: 'uploading' | 'done' | 'error' }>;

  /** Spread on the container element: {...dropZoneProps} */
  dropZoneProps: DropZoneProps;
  handleFileSelect: (e: React.ChangeEvent<HTMLInputElement>) => void;
  handlePaste: (e: React.ClipboardEvent) => void;
  removeAttachment: (index: number) => void;
  clearAttachments: () => void;
  getImagesForAPI: () => Promise<TPImageAttachment[]>;

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
  const [uploadedDocs, setUploadedDocs] = useState<Array<{ name: string; status: 'uploading' | 'done' | 'error' }>>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const dragCounterRef = useRef(0);

  const showError = useCallback((msg: string) => {
    setError(msg);
    setTimeout(() => setError(null), 5000);
  }, []);

  const uploadDocument = useCallback(async (file: File) => {
    const { api } = await import('@/lib/api/client');
    setUploadedDocs((prev) => [...prev, { name: file.name, status: 'uploading' }]);
    try {
      await api.documents.upload(file);
      setUploadedDocs((prev) =>
        prev.map((d) => d.name === file.name ? { ...d, status: 'done' as const } : d)
      );
    } catch {
      setUploadedDocs((prev) =>
        prev.map((d) => d.name === file.name ? { ...d, status: 'error' as const } : d)
      );
      showError(`Failed to upload ${file.name}`);
    }
  }, [showError]);

  const addFiles = useCallback(
    (files: File[]) => {
      const images: File[] = [];
      const docs: File[] = [];
      let hasUnsupported = false;

      for (const file of files) {
        if (IMAGE_TYPES.includes(file.type)) {
          if (file.size > MAX_FILE_SIZE) {
            showError('Images must be under 5MB');
            continue;
          }
          images.push(file);
        } else if (DOCUMENT_TYPES.includes(file.type)) {
          if (file.size > MAX_DOC_SIZE) {
            showError('Documents must be under 20MB');
            continue;
          }
          docs.push(file);
        } else {
          hasUnsupported = true;
        }
      }

      // Attach images inline (for Claude vision)
      if (images.length > 0) {
        images.forEach((f) => addPreview(f, setAttachmentPreviews));
        setAttachments((prev) => [...prev, ...images]);
      }

      // Upload documents via document pipeline
      if (docs.length > 0) {
        docs.forEach((f) => uploadDocument(f));
      }

      if (hasUnsupported && images.length === 0 && docs.length === 0) {
        showError('Unsupported file type. Supported: images, PDF, DOCX, TXT, MD.');
      }
    },
    [showError, uploadDocument]
  );

  // --- File input (paperclip button) ---

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      addFiles(Array.from(e.target.files || []));
      if (fileInputRef.current) fileInputRef.current.value = '';
    },
    [addFiles]
  );

  // --- Clipboard paste ---

  const handlePaste = useCallback(
    (e: React.ClipboardEvent) => {
      const files = Array.from(e.clipboardData.files);
      if (files.length === 0) return;
      const imageFiles = files.filter((f) => IMAGE_TYPES.includes(f.type));
      if (imageFiles.length === 0) return;
      e.preventDefault();
      addFiles(imageFiles);
    },
    [addFiles]
  );

  // --- Drag and drop ---
  // Uses a counter to avoid flicker from child element drag events

  const onDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounterRef.current++;
    if (dragCounterRef.current === 1) {
      setIsDragging(true);
    }
  }, []);

  const onDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const onDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounterRef.current--;
    if (dragCounterRef.current === 0) {
      setIsDragging(false);
    }
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

  // --- Attachment management ---

  const removeAttachment = useCallback((index: number) => {
    setAttachments((prev) => prev.filter((_, i) => i !== index));
    setAttachmentPreviews((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const clearAttachments = useCallback(() => {
    setAttachments([]);
    setAttachmentPreviews([]);
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

  return {
    attachments,
    attachmentPreviews,
    isDragging,
    error,
    uploadedDocs,
    dropZoneProps: { onDragEnter, onDragOver, onDragLeave, onDrop },
    handleFileSelect,
    handlePaste,
    removeAttachment,
    clearAttachments,
    getImagesForAPI,
    fileInputRef,
  };
}

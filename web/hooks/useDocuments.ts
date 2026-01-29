"use client";

/**
 * useDocuments hook
 * ADR-008: Document Pipeline
 *
 * Manages document upload, listing, and deletion.
 * Supports both user-scoped (no project) and project-scoped documents.
 */

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api/client";
import type { Document, DocumentUploadResponse } from "@/types";

export interface UploadProgress {
  filename: string;
  status: "uploading" | "processing" | "completed" | "failed";
  message?: string;
}

export function useDocuments(projectId?: string) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [uploadProgress, setUploadProgress] = useState<UploadProgress | null>(
    null
  );

  const load = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.documents.list(projectId);
      setDocuments(response.documents);
    } catch (err) {
      setError(err as Error);
      console.error("Failed to load documents:", err);
    } finally {
      setIsLoading(false);
    }
  }, [projectId]);

  const upload = useCallback(
    async (file: File): Promise<DocumentUploadResponse | null> => {
      setUploadProgress({ filename: file.name, status: "uploading" });
      setError(null);

      try {
        const result = await api.documents.upload(file, projectId);

        setUploadProgress({
          filename: file.name,
          status: result.processing_status === "completed" ? "completed" : "processing",
          message: result.message,
        });

        // Refresh the list
        await load();

        // Clear progress after a delay
        setTimeout(() => setUploadProgress(null), 3000);

        return result;
      } catch (err) {
        setUploadProgress({
          filename: file.name,
          status: "failed",
          message: (err as Error).message,
        });
        setError(err as Error);
        console.error("Failed to upload document:", err);
        return null;
      }
    },
    [projectId, load]
  );

  const remove = useCallback(
    async (documentId: string) => {
      try {
        await api.documents.delete(documentId);
        setDocuments((prev) => prev.filter((d) => d.id !== documentId));
      } catch (err) {
        setError(err as Error);
        console.error("Failed to delete document:", err);
        throw err;
      }
    },
    []
  );

  const download = useCallback(async (documentId: string) => {
    try {
      const result = await api.documents.download(documentId);
      // Open in new tab
      window.open(result.url, "_blank");
    } catch (err) {
      setError(err as Error);
      console.error("Failed to get download URL:", err);
      throw err;
    }
  }, []);

  const clearProgress = useCallback(() => {
    setUploadProgress(null);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return {
    documents,
    isLoading,
    error,
    uploadProgress,
    upload,
    remove,
    download,
    reload: load,
    clearProgress,
  };
}

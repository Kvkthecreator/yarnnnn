"use client";

/**
 * DocumentList component
 * ADR-008: Document Pipeline
 *
 * Displays uploaded documents with upload button, status, and actions.
 * Used in UserContextPanel to show user's documents and extracted memories.
 */

import { useRef, useState } from "react";
import {
  FileText,
  Upload,
  Loader2,
  Trash2,
  Download,
  ChevronDown,
  ChevronRight,
  AlertCircle,
  CheckCircle,
  Clock,
} from "lucide-react";
import { useDocuments, UploadProgress } from "@/hooks/useDocuments";
import type { Document } from "@/types";

interface DocumentListProps {
  projectId?: string;
  compact?: boolean;
}

const ALLOWED_TYPES = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "text/plain",
  "text/markdown",
];

const ALLOWED_EXTENSIONS = [".pdf", ".docx", ".txt", ".md"];

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffDays = Math.floor(
    (now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24)
  );

  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays} days ago`;

  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function StatusIcon({ status }: { status: Document["processing_status"] }) {
  switch (status) {
    case "completed":
      return <CheckCircle className="w-3.5 h-3.5 text-green-500" />;
    case "processing":
      return <Loader2 className="w-3.5 h-3.5 text-blue-500 animate-spin" />;
    case "pending":
      return <Clock className="w-3.5 h-3.5 text-yellow-500" />;
    case "failed":
      return <AlertCircle className="w-3.5 h-3.5 text-red-500" />;
    default:
      return null;
  }
}

function UploadProgressIndicator({ progress }: { progress: UploadProgress }) {
  return (
    <div className="p-3 rounded-lg border border-border bg-muted/50 mb-3">
      <div className="flex items-center gap-2">
        {progress.status === "uploading" || progress.status === "processing" ? (
          <Loader2 className="w-4 h-4 animate-spin text-primary" />
        ) : progress.status === "completed" ? (
          <CheckCircle className="w-4 h-4 text-green-500" />
        ) : (
          <AlertCircle className="w-4 h-4 text-red-500" />
        )}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium truncate">{progress.filename}</p>
          <p className="text-xs text-muted-foreground">
            {progress.status === "uploading" && "Uploading..."}
            {progress.status === "processing" && "Processing document..."}
            {progress.status === "completed" && progress.message}
            {progress.status === "failed" && (progress.message || "Upload failed")}
          </p>
        </div>
      </div>
    </div>
  );
}

function DocumentItem({
  document,
  onDelete,
  onDownload,
}: {
  document: Document;
  onDelete: () => void;
  onDownload: () => void;
}) {
  const [isDeleting, setIsDeleting] = useState(false);

  const handleDelete = async () => {
    if (!confirm(`Delete "${document.filename}"? Extracted memories will be kept.`)) {
      return;
    }
    setIsDeleting(true);
    try {
      await onDelete();
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="group relative p-2.5 rounded-lg hover:bg-muted/50 transition-colors">
      <div className="flex items-start gap-2.5">
        <div className="p-1.5 rounded bg-primary/10 shrink-0">
          <FileText className="w-4 h-4 text-primary" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            <p className="text-sm font-medium truncate">{document.filename}</p>
            <StatusIcon status={document.processing_status} />
          </div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground mt-0.5">
            <span>{formatDate(document.created_at)}</span>
            <span>·</span>
            <span>{formatFileSize(document.file_size)}</span>
            {document.word_count && (
              <>
                <span>·</span>
                <span>{document.word_count.toLocaleString()} words</span>
              </>
            )}
          </div>
          {document.processing_status === "failed" && document.error_message && (
            <p className="text-xs text-red-500 mt-1">{document.error_message}</p>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          onClick={onDownload}
          className="p-1.5 rounded hover:bg-muted text-muted-foreground hover:text-foreground"
          title="Download"
        >
          <Download className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={handleDelete}
          disabled={isDeleting}
          className="p-1.5 rounded hover:bg-muted text-muted-foreground hover:text-destructive disabled:opacity-50"
          title="Delete"
        >
          {isDeleting ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <Trash2 className="w-3.5 h-3.5" />
          )}
        </button>
      </div>
    </div>
  );
}

export function DocumentList({ projectId, compact = false }: DocumentListProps) {
  const {
    documents,
    isLoading,
    error,
    uploadProgress,
    upload,
    remove,
    download,
  } = useDocuments(projectId);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isExpanded, setIsExpanded] = useState(true);
  const [dragOver, setDragOver] = useState(false);

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      await upload(file);
    }
    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);

    const file = e.dataTransfer.files?.[0];
    if (file) {
      // Validate file type
      const isAllowed =
        ALLOWED_TYPES.includes(file.type) ||
        ALLOWED_EXTENSIONS.some((ext) =>
          file.name.toLowerCase().endsWith(ext)
        );

      if (!isAllowed) {
        alert("Please upload a PDF, DOCX, TXT, or MD file.");
        return;
      }

      await upload(file);
    }
  };

  if (isLoading) {
    return (
      <div className="py-4">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
          <span>Loading documents...</span>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`${dragOver ? "ring-2 ring-primary ring-offset-2 rounded-lg" : ""}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.docx,.txt,.md,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown"
        onChange={handleFileSelect}
        className="hidden"
      />

      {/* Section Header */}
      <div className="flex items-center justify-between mb-2">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center gap-2 text-xs font-medium text-muted-foreground hover:text-foreground"
        >
          {isExpanded ? (
            <ChevronDown className="w-3 h-3" />
          ) : (
            <ChevronRight className="w-3 h-3" />
          )}
          <FileText className="w-3.5 h-3.5" />
          <span>Documents</span>
          <span className="ml-1 text-muted-foreground">({documents.length})</span>
        </button>

        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={!!uploadProgress}
          className="flex items-center gap-1.5 px-2 py-1 text-xs font-medium rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          <Upload className="w-3 h-3" />
          <span>Upload</span>
        </button>
      </div>

      {isExpanded && (
        <>
          {/* Upload Progress */}
          {uploadProgress && <UploadProgressIndicator progress={uploadProgress} />}

          {/* Error */}
          {error && (
            <div className="p-2 mb-2 rounded bg-destructive/10 text-destructive text-xs">
              {error.message}
            </div>
          )}

          {/* Document List */}
          {documents.length === 0 ? (
            <div
              className={`border-2 border-dashed border-muted rounded-lg p-4 text-center cursor-pointer hover:border-primary/50 transition-colors ${
                dragOver ? "border-primary bg-primary/5" : ""
              }`}
              onClick={() => fileInputRef.current?.click()}
            >
              <Upload className="w-6 h-6 mx-auto text-muted-foreground mb-2" />
              <p className="text-sm text-muted-foreground">
                Drop files here or click to upload
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                PDF, DOCX, TXT, MD supported
              </p>
            </div>
          ) : (
            <div className="space-y-1">
              {documents.map((doc) => (
                <DocumentItem
                  key={doc.id}
                  document={doc}
                  onDelete={() => remove(doc.id)}
                  onDownload={() => download(doc.id)}
                />
              ))}

              {/* Drop zone hint when documents exist */}
              {!compact && (
                <div
                  className={`mt-2 p-2 border border-dashed border-muted rounded text-center text-xs text-muted-foreground cursor-pointer hover:border-primary/50 ${
                    dragOver ? "border-primary bg-primary/5" : ""
                  }`}
                  onClick={() => fileInputRef.current?.click()}
                >
                  Drop or click to add more
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}

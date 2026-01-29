"use client";

import { useState } from "react";
import { X, Loader2, ClipboardPaste } from "lucide-react";
import { api } from "@/lib/api/client";

interface BulkImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  /** Optional project ID for project-scoped import. Omit for user-level import. */
  projectId?: string;
}

/**
 * Modal for bulk importing text as memories.
 *
 * Supports two modes:
 * - User-level: Omit projectId to import user-scoped memories
 * - Project-level: Pass projectId to import project-scoped memories
 */
export function BulkImportModal({
  isOpen,
  onClose,
  onSuccess,
  projectId,
}: BulkImportModalProps) {
  const [text, setText] = useState("");
  const [isImporting, setIsImporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{ memories_extracted: number } | null>(null);

  const handleImport = async () => {
    if (text.trim().length < 50) {
      setError("Please enter at least 50 characters of text.");
      return;
    }

    setIsImporting(true);
    setError(null);

    try {
      let response: { memories_extracted: number };

      if (projectId) {
        // Project-scoped import
        response = await api.projectMemories.importBulk(projectId, { text });
      } else {
        // User-level import
        response = await api.userMemories.importBulk({ text });
      }

      setResult(response);

      // Auto-close after brief success display
      setTimeout(() => {
        setText("");
        setResult(null);
        onSuccess();
      }, 1500);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Import failed";
      setError(message);
    } finally {
      setIsImporting(false);
    }
  };

  const handleClose = () => {
    if (isImporting) return; // Prevent closing during import
    setText("");
    setError(null);
    setResult(null);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-background/80 backdrop-blur-sm"
        onClick={handleClose}
      />

      {/* Modal */}
      <div className="relative z-10 w-full max-w-lg mx-4 bg-card border border-border rounded-lg shadow-lg">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div className="flex items-center gap-2">
            <ClipboardPaste className="w-5 h-5 text-primary" />
            <h2 className="font-semibold">Paste Context</h2>
          </div>
          <button
            onClick={handleClose}
            disabled={isImporting}
            className="p-1 rounded hover:bg-muted disabled:opacity-50"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4">
          <p className="text-sm text-muted-foreground mb-4">
            Paste meeting notes, project briefs, or any text that helps me understand
            your work. I&apos;ll extract key information automatically.
          </p>

          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Paste your text here..."
            disabled={isImporting || !!result}
            className="w-full h-48 p-3 text-sm border border-border rounded-md bg-background resize-none focus:outline-none focus:ring-2 focus:ring-primary/50 disabled:opacity-50"
          />

          {/* Character count */}
          <p className="text-xs text-muted-foreground mt-2">
            {text.length} characters {text.length < 50 && "(minimum 50)"}
          </p>

          {/* Error */}
          {error && (
            <div className="mt-3 p-2 bg-destructive/10 text-destructive text-sm rounded">
              {error}
            </div>
          )}

          {/* Success */}
          {result && (
            <div className="mt-3 p-2 bg-primary/10 text-primary text-sm rounded">
              Extracted {result.memories_extracted} {result.memories_extracted === 1 ? "memory" : "memories"}!
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 p-4 border-t border-border">
          <button
            onClick={handleClose}
            disabled={isImporting}
            className="px-4 py-2 text-sm border border-border rounded-md hover:bg-muted disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleImport}
            disabled={isImporting || text.trim().length < 50 || !!result}
            className="px-4 py-2 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 flex items-center gap-2"
          >
            {isImporting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Processing...
              </>
            ) : (
              "Import Context"
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

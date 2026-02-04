"use client";

/**
 * Setup Confirmation Modal
 *
 * Shown after TP creates a deliverable to confirm context before first run.
 * Part of the Deliverable Workflow assurance pattern.
 */

import { useState } from "react";
import {
  X,
  CheckCircle,
  FileText,
  Brain,
  Calendar,
  Plus,
  FileUp,
  Loader2,
  Play,
} from "lucide-react";
import { api } from "@/lib/api/client";
import { useDesk } from "@/contexts/DeskContext";
import { DeskSurface } from "@/types/desk";

export interface SetupConfirmData {
  deliverableId: string;
  title: string;
  schedule: string;
  context: {
    user_memory_count: number;
    deliverable_memory_count: number;
    document_count: number;
    sample_memories: string[];
  };
}

interface SetupConfirmModalProps {
  open: boolean;
  onClose: () => void;
  data: SetupConfirmData | null;
}

export function SetupConfirmModal({
  open,
  onClose,
  data,
}: SetupConfirmModalProps) {
  const { setSurface } = useDesk();
  const [isRunning, setIsRunning] = useState(false);

  if (!open || !data) return null;

  const handleConfirm = async (runNow: boolean) => {
    if (runNow) {
      setIsRunning(true);
      try {
        await api.deliverables.run(data.deliverableId);
      } catch (err) {
        console.error("Failed to run deliverable:", err);
        // Continue to navigation even if run fails - user can retry from detail surface
      }
      setIsRunning(false);
    }

    // Navigate to deliverable detail
    const surface: DeskSurface = {
      type: "deliverable-detail",
      deliverableId: data.deliverableId,
    };
    setSurface(surface);
    onClose();
  };

  const handleEditContext = () => {
    // Navigate to context browser for this deliverable's scope
    const surface: DeskSurface = {
      type: "context-browser",
      scope: "deliverable",
      scopeId: data.deliverableId,
    };
    setSurface(surface);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-background/80 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative z-10 w-full max-w-lg mx-4 bg-card border border-border rounded-lg shadow-lg">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div className="flex items-center gap-2">
            <CheckCircle className="w-5 h-5 text-green-500" />
            <div>
              <h2 className="font-semibold">{data.title}</h2>
              <p className="text-sm text-muted-foreground">
                Ready to generate your first draft
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            disabled={isRunning}
            className="p-1 rounded hover:bg-muted disabled:opacity-50"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4">
          {/* What I'll Create */}
          <section className="p-3 rounded-lg bg-muted">
            <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
              <FileText className="w-4 h-4" />
              What I'll Create
            </h4>
            <p className="text-sm text-muted-foreground flex items-center gap-2">
              <Calendar className="w-3 h-3" />
              {data.title} &bull; {data.schedule}
            </p>
          </section>

          {/* Context I'll Use */}
          <section className="p-3 rounded-lg bg-muted">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-medium flex items-center gap-2">
                <Brain className="w-4 h-4" />
                Context I'll Use
              </h4>
              <button
                onClick={handleEditContext}
                className="text-xs text-primary hover:underline"
              >
                Edit
              </button>
            </div>

            <div className="space-y-2 text-sm text-muted-foreground">
              <div>
                <span className="font-medium">Your context:</span>{" "}
                {data.context.user_memory_count} memories
              </div>
              {data.context.deliverable_memory_count > 0 && (
                <div>
                  <span className="font-medium">Deliverable context:</span>{" "}
                  {data.context.deliverable_memory_count} memories
                </div>
              )}
              {data.context.document_count > 0 && (
                <div>
                  <span className="font-medium">Documents:</span>{" "}
                  {data.context.document_count} attached
                </div>
              )}

              {/* Sample memories preview */}
              {data.context.sample_memories.length > 0 && (
                <div className="mt-2 pt-2 border-t border-border">
                  <p className="text-xs text-muted-foreground mb-1">Preview:</p>
                  <ul className="text-xs space-y-1">
                    {data.context.sample_memories.map((mem, i) => (
                      <li key={i} className="truncate">
                        &bull; {mem}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            <div className="flex gap-2 mt-3">
              <button
                onClick={handleEditContext}
                className="px-2 py-1 text-xs border border-border rounded hover:bg-background flex items-center gap-1"
              >
                <Plus className="w-3 h-3" />
                Add context
              </button>
              <button
                onClick={handleEditContext}
                className="px-2 py-1 text-xs border border-border rounded hover:bg-background flex items-center gap-1"
              >
                <FileUp className="w-3 h-3" />
                Add document
              </button>
            </div>
          </section>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 p-4 border-t border-border">
          <button
            onClick={() => handleConfirm(false)}
            disabled={isRunning}
            className="px-4 py-2 text-sm border border-border rounded-md hover:bg-muted disabled:opacity-50"
          >
            Just Add to Schedule
          </button>
          <button
            onClick={() => handleConfirm(true)}
            disabled={isRunning}
            className="px-4 py-2 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 flex items-center gap-2"
          >
            {isRunning ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Starting...
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                Run First Draft Now
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

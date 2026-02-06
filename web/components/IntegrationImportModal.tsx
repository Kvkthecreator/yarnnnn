"use client";

import { useState, useEffect, useCallback } from "react";
import {
  X,
  Loader2,
  Download,
  Hash,
  FileText,
  Check,
  AlertTriangle,
  RefreshCw,
  Lock,
} from "lucide-react";
import { api } from "@/lib/api/client";

type Provider = "slack" | "notion";

interface SlackChannel {
  id: string;
  name: string;
  is_private: boolean;
  num_members: number;
  topic: string | null;
  purpose: string | null;
}

interface NotionPage {
  id: string;
  title: string;
  parent_type: string;
  last_edited: string | null;
  url: string | null;
}

interface ImportJob {
  id: string;
  provider: string;
  resource_id: string;
  resource_name: string | null;
  status: string;
  progress: number;
  result: {
    blocks_created: number;
    items_processed: number;
    items_filtered: number;
    summary: string;
    style_learned?: boolean;
    style_confidence?: string;
  } | null;
  error_message: string | null;
}

interface IntegrationImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  provider: Provider;
  projectId?: string;
}

/**
 * Modal for importing context from connected integrations.
 *
 * ADR-027: Integration Read Architecture - Phase 3 Onboarding UI
 *
 * Flow:
 * 1. Load available resources (channels/pages) from connected integration
 * 2. User selects resource and optionally provides instructions
 * 3. Start import job (async processing)
 * 4. Poll for completion, show result
 */
export function IntegrationImportModal({
  isOpen,
  onClose,
  onSuccess,
  provider,
  projectId,
}: IntegrationImportModalProps) {
  // Resource selection state
  const [channels, setChannels] = useState<SlackChannel[]>([]);
  const [pages, setPages] = useState<NotionPage[]>([]);
  const [isLoadingResources, setIsLoadingResources] = useState(false);
  const [resourceError, setResourceError] = useState<string | null>(null);

  // Selection state
  const [selectedResource, setSelectedResource] = useState<string | null>(null);
  const [instructions, setInstructions] = useState("");
  const [learnStyle, setLearnStyle] = useState(false);  // ADR-027 Phase 5

  // Import state
  const [isImporting, setIsImporting] = useState(false);
  const [importJob, setImportJob] = useState<ImportJob | null>(null);
  const [importError, setImportError] = useState<string | null>(null);

  // Load resources when modal opens
  const loadResources = useCallback(async () => {
    setIsLoadingResources(true);
    setResourceError(null);

    try {
      if (provider === "slack") {
        const response = await api.integrations.listSlackChannels();
        setChannels(response.channels);
      } else {
        const response = await api.integrations.listNotionPages();
        setPages(response.pages);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load resources";
      setResourceError(message);
    } finally {
      setIsLoadingResources(false);
    }
  }, [provider]);

  useEffect(() => {
    if (isOpen) {
      loadResources();
    }
  }, [isOpen, loadResources]);

  // Poll for job completion
  useEffect(() => {
    if (!importJob || importJob.status === "completed" || importJob.status === "failed") {
      return;
    }

    const pollInterval = setInterval(async () => {
      try {
        const updated = await api.integrations.getImportJob(importJob.id);
        setImportJob(updated);

        if (updated.status === "completed" || updated.status === "failed") {
          clearInterval(pollInterval);
        }
      } catch {
        // Silently retry on poll failure
      }
    }, 2000);

    return () => clearInterval(pollInterval);
  }, [importJob]);

  const handleImport = async () => {
    if (!selectedResource) return;

    setIsImporting(true);
    setImportError(null);

    try {
      // Get resource name for display
      let resourceName: string | undefined;
      if (provider === "slack") {
        const channel = channels.find((c) => c.id === selectedResource);
        resourceName = channel ? `#${channel.name}` : undefined;
      } else {
        const page = pages.find((p) => p.id === selectedResource);
        resourceName = page?.title;
      }

      const job = await api.integrations.startImport(provider, {
        resource_id: selectedResource,
        resource_name: resourceName,
        project_id: projectId,
        instructions: instructions.trim() || undefined,
        config: learnStyle ? { learn_style: true } : undefined,
      });

      setImportJob(job as unknown as ImportJob);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to start import";
      setImportError(message);
      setIsImporting(false);
    }
  };

  const handleClose = () => {
    if (isImporting && importJob?.status === "processing") return;

    // Reset state
    setSelectedResource(null);
    setInstructions("");
    setLearnStyle(false);
    setImportJob(null);
    setImportError(null);
    setChannels([]);
    setPages([]);

    onClose();

    // If import completed successfully, trigger refresh
    if (importJob?.status === "completed") {
      onSuccess();
    }
  };

  if (!isOpen) return null;

  const resources = provider === "slack" ? channels : pages;
  const providerName = provider === "slack" ? "Slack" : "Notion";
  const resourceLabel = provider === "slack" ? "channel" : "page";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-background/80 backdrop-blur-sm"
        onClick={handleClose}
      />

      {/* Modal */}
      <div className="relative z-10 w-full max-w-lg mx-4 bg-card border border-border rounded-lg shadow-lg max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border shrink-0">
          <div className="flex items-center gap-2">
            <Download className="w-5 h-5 text-primary" />
            <h2 className="font-semibold">Import from {providerName}</h2>
          </div>
          <button
            onClick={handleClose}
            disabled={isImporting && importJob?.status === "processing"}
            className="p-1 rounded hover:bg-muted disabled:opacity-50"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 overflow-y-auto flex-1">
          {/* Show import result if job exists */}
          {importJob ? (
            <ImportJobStatus job={importJob} provider={provider} />
          ) : (
            <>
              <p className="text-sm text-muted-foreground mb-4">
                Select a {resourceLabel} to import context from. I&apos;ll extract key decisions,
                action items, and project context automatically.
              </p>

              {/* Resource list */}
              {isLoadingResources ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
                </div>
              ) : resourceError ? (
                <div className="p-4 bg-destructive/10 text-destructive rounded-lg flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5 shrink-0" />
                  <div>
                    <p className="font-medium">Failed to load {resourceLabel}s</p>
                    <p className="text-sm">{resourceError}</p>
                  </div>
                  <button
                    onClick={loadResources}
                    className="ml-auto p-2 hover:bg-destructive/20 rounded"
                  >
                    <RefreshCw className="w-4 h-4" />
                  </button>
                </div>
              ) : resources.length === 0 ? (
                <div className="p-4 bg-muted/50 rounded-lg text-center text-muted-foreground">
                  <p>No {resourceLabel}s found.</p>
                  <p className="text-sm mt-1">
                    Make sure the {providerName} integration has access to the {resourceLabel}s you want to import.
                  </p>
                </div>
              ) : (
                <div className="space-y-2 max-h-64 overflow-y-auto border border-border rounded-lg p-2">
                  {provider === "slack"
                    ? channels.map((channel) => (
                        <button
                          key={channel.id}
                          onClick={() => setSelectedResource(channel.id)}
                          className={`w-full p-3 text-left rounded-lg transition-colors ${
                            selectedResource === channel.id
                              ? "bg-primary/10 border border-primary"
                              : "hover:bg-muted border border-transparent"
                          }`}
                        >
                          <div className="flex items-center gap-2">
                            {channel.is_private ? (
                              <Lock className="w-4 h-4 text-muted-foreground" />
                            ) : (
                              <Hash className="w-4 h-4 text-muted-foreground" />
                            )}
                            <span className="font-medium">{channel.name}</span>
                            <span className="text-xs text-muted-foreground ml-auto">
                              {channel.num_members} members
                            </span>
                          </div>
                          {channel.purpose && (
                            <p className="text-xs text-muted-foreground mt-1 truncate">
                              {channel.purpose}
                            </p>
                          )}
                        </button>
                      ))
                    : pages.map((page) => (
                        <button
                          key={page.id}
                          onClick={() => setSelectedResource(page.id)}
                          className={`w-full p-3 text-left rounded-lg transition-colors ${
                            selectedResource === page.id
                              ? "bg-primary/10 border border-primary"
                              : "hover:bg-muted border border-transparent"
                          }`}
                        >
                          <div className="flex items-center gap-2">
                            <FileText className="w-4 h-4 text-muted-foreground" />
                            <span className="font-medium">{page.title || "Untitled"}</span>
                          </div>
                          {page.last_edited && (
                            <p className="text-xs text-muted-foreground mt-1">
                              Last edited: {new Date(page.last_edited).toLocaleDateString()}
                            </p>
                          )}
                        </button>
                      ))}
                </div>
              )}

              {/* Instructions (optional) */}
              {resources.length > 0 && (
                <div className="mt-4">
                  <label className="block text-sm font-medium mb-2">
                    Instructions (optional)
                  </label>
                  <textarea
                    value={instructions}
                    onChange={(e) => setInstructions(e.target.value)}
                    placeholder="e.g., Focus on product decisions and technical requirements"
                    className="w-full h-20 p-3 text-sm border border-border rounded-md bg-background resize-none focus:outline-none focus:ring-2 focus:ring-primary/50"
                  />
                </div>
              )}

              {/* Style Learning Toggle - ADR-027 Phase 5 */}
              {resources.length > 0 && (
                <div className="mt-4 p-3 border border-border rounded-lg bg-muted/30">
                  <label className="flex items-start gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={learnStyle}
                      onChange={(e) => setLearnStyle(e.target.checked)}
                      className="mt-1 h-4 w-4 rounded border-border"
                    />
                    <div>
                      <span className="text-sm font-medium">Learn my writing style</span>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {provider === "slack"
                          ? "Analyze your messages to capture your casual communication style"
                          : "Analyze this content to capture your documentation style"}
                      </p>
                    </div>
                  </label>
                </div>
              )}

              {/* Error */}
              {importError && (
                <div className="mt-3 p-2 bg-destructive/10 text-destructive text-sm rounded">
                  {importError}
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 p-4 border-t border-border shrink-0">
          {importJob?.status === "completed" ? (
            <button
              onClick={handleClose}
              className="px-4 py-2 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
            >
              Done
            </button>
          ) : importJob?.status === "failed" ? (
            <>
              <button
                onClick={() => {
                  setImportJob(null);
                  setImportError(null);
                }}
                className="px-4 py-2 text-sm border border-border rounded-md hover:bg-muted"
              >
                Try Again
              </button>
              <button
                onClick={handleClose}
                className="px-4 py-2 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
              >
                Close
              </button>
            </>
          ) : (
            <>
              <button
                onClick={handleClose}
                disabled={isImporting}
                className="px-4 py-2 text-sm border border-border rounded-md hover:bg-muted disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={handleImport}
                disabled={!selectedResource || isImporting}
                className="px-4 py-2 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 flex items-center gap-2"
              >
                {isImporting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Importing...
                  </>
                ) : (
                  <>
                    <Download className="w-4 h-4" />
                    Import Context
                  </>
                )}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Component to show import job status and result.
 */
function ImportJobStatus({ job, provider }: { job: ImportJob; provider: Provider }) {
  const providerName = provider === "slack" ? "Slack" : "Notion";

  if (job.status === "pending" || job.status === "processing") {
    return (
      <div className="py-8 text-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary mx-auto mb-4" />
        <p className="font-medium">Importing from {job.resource_name || providerName}...</p>
        <p className="text-sm text-muted-foreground mt-2">
          {job.status === "pending"
            ? "Waiting to start..."
            : "Extracting context and filtering noise..."}
        </p>
      </div>
    );
  }

  if (job.status === "failed") {
    return (
      <div className="py-4">
        <div className="flex items-center gap-2 text-destructive mb-4">
          <AlertTriangle className="w-6 h-6" />
          <span className="font-medium">Import failed</span>
        </div>
        <p className="text-sm text-muted-foreground">
          {job.error_message || "An unexpected error occurred. Please try again."}
        </p>
      </div>
    );
  }

  // Completed
  return (
    <div className="py-4">
      <div className="flex items-center gap-2 text-green-600 dark:text-green-400 mb-4">
        <Check className="w-6 h-6" />
        <span className="font-medium">Import complete!</span>
      </div>

      {job.result && (
        <div className="space-y-3">
          <div className="grid grid-cols-3 gap-3 text-center">
            <div className="p-3 bg-muted/50 rounded-lg">
              <div className="text-2xl font-bold">{job.result.blocks_created}</div>
              <div className="text-xs text-muted-foreground">Memories created</div>
            </div>
            <div className="p-3 bg-muted/50 rounded-lg">
              <div className="text-2xl font-bold">{job.result.items_processed}</div>
              <div className="text-xs text-muted-foreground">Items processed</div>
            </div>
            <div className="p-3 bg-muted/50 rounded-lg">
              <div className="text-2xl font-bold">{job.result.items_filtered}</div>
              <div className="text-xs text-muted-foreground">Noise filtered</div>
            </div>
          </div>

          {job.result.summary && (
            <div className="p-3 bg-muted/30 rounded-lg text-sm text-muted-foreground">
              {job.result.summary}
            </div>
          )}

          {/* Style Learning Result - ADR-027 Phase 5 */}
          {job.result.style_learned && (
            <div className="p-3 bg-primary/10 border border-primary/20 rounded-lg">
              <div className="flex items-center gap-2 text-sm">
                <Check className="w-4 h-4 text-primary" />
                <span className="font-medium text-primary">Writing style captured</span>
                {job.result.style_confidence && (
                  <span className="text-xs text-muted-foreground ml-auto">
                    {job.result.style_confidence} confidence
                  </span>
                )}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Your {providerName.toLowerCase()} communication style will be applied to future deliverables.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

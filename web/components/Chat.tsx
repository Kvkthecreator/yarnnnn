"use client";

import { useState, useRef, useEffect, FormEvent } from "react";
import { Send, Loader2, Upload, FileText, X, Paperclip } from "lucide-react";
import { useChat } from "@/hooks/useChat";
import { useDocuments } from "@/hooks/useDocuments";
import { useOnboardingState } from "@/hooks/useOnboardingState";
import { WelcomePrompt, MinimalContextBanner } from "@/components/WelcomePrompt";
import { BulkImportModal } from "@/components/BulkImportModal";

interface ChatProps {
  /**
   * Project ID for project-scoped chat.
   * Omit for global (user-level) chat.
   */
  projectId?: string;
  /**
   * Project name for scope indicator display.
   * Only used when projectId is provided.
   */
  projectName?: string;
  /**
   * Whether to include context in the chat.
   * For project chat: includes user + project context.
   * For global chat: includes user context only.
   */
  includeContext?: boolean;
  /**
   * Custom empty state message
   */
  emptyMessage?: string;
  /**
   * Custom height class (default: h-[calc(100vh-240px)])
   */
  heightClass?: string;
  /**
   * Callback when a project is created/modified via TP.
   * If not provided, dispatches 'refreshProjects' event.
   */
  onProjectChange?: () => void;
}

// File size formatter
function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// Allowed file types
const ALLOWED_TYPES = [
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "text/plain",
  "text/markdown",
];
const ALLOWED_EXTENSIONS = [".pdf", ".docx", ".txt", ".md"];

function isFileAllowed(file: File): boolean {
  return (
    ALLOWED_TYPES.includes(file.type) ||
    ALLOWED_EXTENSIONS.some((ext) => file.name.toLowerCase().endsWith(ext))
  );
}

/**
 * Reusable chat component for Thinking Partner conversations.
 *
 * Supports two modes:
 * - Project chat: Pass projectId for project + user context
 * - Global chat: Omit projectId for user context only
 *
 * ADR-007: TP can use tools to manage projects. When a project is
 * created/modified, the sidebar is automatically refreshed.
 *
 * ADR-008: Supports drag-and-drop file attachment with attach-then-send UX.
 */
export function Chat({
  projectId,
  projectName,
  includeContext = true,
  emptyMessage,
  heightClass = "h-[calc(100vh-240px)]",
  onProjectChange,
}: ChatProps) {
  const handleProjectChange = onProjectChange || (() => {
    window.dispatchEvent(new CustomEvent("refreshProjects"));
  });

  const { messages, isLoading, isLoadingHistory, error, sendMessage } = useChat({
    projectId,
    includeContext,
    onProjectChange: handleProjectChange,
  });
  const { uploadProgress, upload, clearProgress } = useDocuments(projectId);
  const {
    state: onboardingState,
    isLoading: isLoadingOnboarding,
    memoryCount,
    dismiss: dismissWelcome,
    isDismissed: isWelcomeDismissed,
    reload: reloadOnboardingState,
  } = useOnboardingState();

  const [input, setInput] = useState("");
  const [isDragOver, setIsDragOver] = useState(false);
  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const [attachError, setAttachError] = useState<string | null>(null);
  const [pendingMessage, setPendingMessage] = useState<string | null>(null); // Optimistic message during upload
  const [showBulkImportModal, setShowBulkImportModal] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const dragCounterRef = useRef(0);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounterRef.current++;
    if (e.dataTransfer.types.includes("Files")) {
      setIsDragOver(true);
    }
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounterRef.current--;
    if (dragCounterRef.current === 0) {
      setIsDragOver(false);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    dragCounterRef.current = 0;
    setAttachError(null);

    const file = e.dataTransfer.files?.[0];
    if (!file) return;

    if (!isFileAllowed(file)) {
      setAttachError("Unsupported file type. Use PDF, DOCX, TXT, or MD.");
      return;
    }

    setAttachedFile(file);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    setAttachError(null);
    const file = e.target.files?.[0];
    if (!file) return;

    if (!isFileAllowed(file)) {
      setAttachError("Unsupported file type. Use PDF, DOCX, TXT, or MD.");
      return;
    }

    setAttachedFile(file);
    // Reset input so same file can be selected again
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const removeAttachment = () => {
    setAttachedFile(null);
    setAttachError(null);
    clearProgress();
  };

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (isLoading) return;

    // Need either text or file
    if (!input.trim() && !attachedFile) return;

    const message = input;
    const file = attachedFile;

    // Clear input immediately for responsiveness
    setInput("");
    setAttachedFile(null);

    if (file) {
      // Build the message that will be sent
      const fileMessage = message.trim()
        ? `${message}\n\n[Attached: ${file.name}]`
        : `I've uploaded a document: ${file.name}. Please review it and let me know what you think.`;

      // Show optimistic message immediately (user sees their message right away)
      setPendingMessage(fileMessage);

      // Upload file first and wait for it to complete
      // The document needs to be processed before TP can see its contents
      const uploadResult = await upload(file);

      // Clear pending message (sendMessage will add the real one)
      setPendingMessage(null);

      if (!uploadResult) {
        // Upload failed - don't send message, error shown via uploadProgress
        console.warn("File upload failed");
        return;
      }

      // Now send the message - by now the document is processed
      // and its extracted memories are available to the TP
      await sendMessage(fileMessage);
    } else {
      // Just send the text message
      await sendMessage(message);
    }
  };

  const defaultEmptyMessage = projectId
    ? "Hi! I'm your Thinking Partner. I can help you analyze your project context and think through problems. What would you like to explore?"
    : "Hi! I'm your Thinking Partner. I'm here to help you think through ideas, explore problems, and work on anything. What's on your mind?";

  const isSubmitDisabled = isLoading || (!input.trim() && !attachedFile);

  // Welcome prompt handlers
  const handleWelcomeUpload = () => {
    dismissWelcome();
    fileInputRef.current?.click();
  };

  const handleWelcomePaste = () => {
    dismissWelcome();
    setShowBulkImportModal(true);
  };

  const handleWelcomeStart = () => {
    dismissWelcome();
    inputRef.current?.focus();
  };

  const handleSelectPrompt = (prompt: string) => {
    dismissWelcome();
    setInput(prompt);
    inputRef.current?.focus();
  };

  const handleBulkImportSuccess = () => {
    setShowBulkImportModal(false);
    reloadOnboardingState();
  };

  // Determine if we should show welcome UI
  const showWelcome =
    !isLoadingOnboarding &&
    !isWelcomeDismissed &&
    onboardingState === "cold_start" &&
    messages.length === 0 &&
    !isLoadingHistory;

  const showMinimalContextBanner =
    !isLoadingOnboarding &&
    !isWelcomeDismissed &&
    onboardingState === "minimal_context" &&
    messages.length === 0 &&
    !isLoadingHistory;

  return (
    <div
      className={`flex flex-col ${heightClass} relative`}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      {/* Drop Zone Overlay */}
      {isDragOver && (
        <div className="absolute inset-0 z-50 bg-background/90 backdrop-blur-sm flex items-center justify-center rounded-lg border-2 border-dashed border-primary">
          <div className="text-center">
            <Upload className="w-12 h-12 mx-auto text-primary mb-3" />
            <p className="text-lg font-medium text-foreground">Drop file to attach</p>
            <p className="text-sm text-muted-foreground mt-1">PDF, DOCX, TXT, MD supported</p>
          </div>
        </div>
      )}

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.docx,.txt,.md,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown"
        onChange={handleFileSelect}
        className="hidden"
      />

      {/* Bulk Import Modal */}
      <BulkImportModal
        isOpen={showBulkImportModal}
        onClose={() => setShowBulkImportModal(false)}
        onSuccess={handleBulkImportSuccess}
        projectId={projectId}
      />

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4">
        {/* Scope Indicator */}
        <div className="flex items-center gap-2 text-xs text-muted-foreground px-1">
          <span className="w-2 h-2 rounded-full bg-primary/60" />
          <span>
            {projectId ? `Chatting in: ${projectName || "Project"}` : "Chatting in: Dashboard"}
          </span>
        </div>

        {isLoadingHistory && (
          <div className="flex justify-center py-4">
            <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
          </div>
        )}

        {/* Welcome Prompt for cold_start users */}
        {showWelcome && (
          <WelcomePrompt
            onUpload={handleWelcomeUpload}
            onPaste={handleWelcomePaste}
            onStart={handleWelcomeStart}
            onSelectPrompt={handleSelectPrompt}
          />
        )}

        {/* Minimal Context Banner for users with few memories */}
        {showMinimalContextBanner && (
          <MinimalContextBanner
            memoryCount={memoryCount}
            onDismiss={dismissWelcome}
          />
        )}

        {/* Default empty message for active users */}
        {!isLoadingHistory && messages.length === 0 && !showWelcome && !showMinimalContextBanner && (
          <div className="p-4 bg-muted rounded-lg max-w-[80%]">
            <p className="text-sm">{emptyMessage || defaultEmptyMessage}</p>
          </div>
        )}

        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex ${
              message.role === "user" ? "justify-end" : "justify-start"
            }`}
          >
            <div
              className={`p-4 rounded-lg max-w-[80%] ${
                message.role === "user"
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted"
              }`}
            >
              <p className="text-sm whitespace-pre-wrap">{message.content}</p>
            </div>
          </div>
        ))}

        {/* Optimistic pending message during file upload */}
        {pendingMessage && (
          <div className="flex justify-end">
            <div className="p-4 rounded-lg max-w-[80%] bg-primary text-primary-foreground opacity-70">
              <p className="text-sm whitespace-pre-wrap">{pendingMessage}</p>
              <p className="text-xs mt-1 opacity-70">Uploading...</p>
            </div>
          </div>
        )}

        {isLoading && messages[messages.length - 1]?.role !== "assistant" && (
          <div className="flex justify-start">
            <div className="p-4 bg-muted rounded-lg">
              <Loader2 className="w-4 h-4 animate-spin" />
            </div>
          </div>
        )}

        {error && (
          <div className="p-4 bg-destructive/10 text-destructive rounded-lg max-w-[80%]">
            <p className="text-sm">Error: {error}</p>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t border-border pt-4">
        {/* Attachment Preview */}
        {attachedFile && (
          <div className="mb-3 p-3 bg-muted rounded-lg flex items-center gap-3">
            <div className="p-2 bg-primary/10 rounded">
              <FileText className="w-5 h-5 text-primary" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{attachedFile.name}</p>
              <p className="text-xs text-muted-foreground">
                {formatFileSize(attachedFile.size)}
                {uploadProgress && (
                  <span className="ml-2">
                    {uploadProgress.status === "uploading" && "• Uploading..."}
                    {uploadProgress.status === "processing" && "• Processing..."}
                    {uploadProgress.status === "failed" && (
                      <span className="text-destructive">• {uploadProgress.message || "Failed"}</span>
                    )}
                  </span>
                )}
              </p>
            </div>
            <button
              type="button"
              onClick={removeAttachment}
              className="p-1.5 hover:bg-background rounded text-muted-foreground hover:text-foreground"
              aria-label="Remove attachment"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Attachment Error */}
        {attachError && (
          <div className="mb-3 p-2 bg-destructive/10 text-destructive text-sm rounded">
            {attachError}
          </div>
        )}

        {/* Input Form */}
        <form onSubmit={handleSubmit}>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={isLoading || !!attachedFile}
              className="px-3 py-2 border border-border rounded-md bg-background hover:bg-muted disabled:opacity-50 text-muted-foreground hover:text-foreground"
              aria-label="Attach file"
            >
              <Paperclip className="w-4 h-4" />
            </button>
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={attachedFile ? "Add a message (optional)..." : "Type a message..."}
              disabled={isLoading}
              className="flex-1 px-4 py-2 border border-border rounded-md bg-background disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={isSubmitDisabled}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-md disabled:opacity-50 flex items-center gap-2"
            >
              {isLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
              Send
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

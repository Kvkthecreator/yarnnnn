"use client";

import { useState, useRef, useEffect, FormEvent } from "react";
import { Send, Loader2, Upload, FileText, CheckCircle, AlertCircle } from "lucide-react";
import { useChat } from "@/hooks/useChat";
import { useDocuments } from "@/hooks/useDocuments";

interface ChatProps {
  /**
   * Project ID for project-scoped chat.
   * Omit for global (user-level) chat.
   */
  projectId?: string;
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

/**
 * Reusable chat component for Thinking Partner conversations.
 *
 * Supports two modes:
 * - Project chat: Pass projectId for project + user context
 * - Global chat: Omit projectId for user context only
 *
 * ADR-007: TP can use tools to manage projects. When a project is
 * created/modified, the sidebar is automatically refreshed.
 */
export function Chat({
  projectId,
  includeContext = true,
  emptyMessage,
  heightClass = "h-[calc(100vh-240px)]",
  onProjectChange,
}: ChatProps) {
  const handleProjectChange = onProjectChange || (() => {
    // Default behavior: dispatch event for sidebar to catch
    window.dispatchEvent(new CustomEvent("refreshProjects"));
  });

  const { messages, isLoading, isLoadingHistory, error, sendMessage } = useChat({
    projectId,
    includeContext,
    onProjectChange: handleProjectChange,
  });
  const { uploadProgress, upload } = useDocuments(projectId);
  const [input, setInput] = useState("");
  const [isDragOver, setIsDragOver] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const dragCounterRef = useRef(0);

  // Allowed file types for upload
  const ALLOWED_TYPES = [
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/markdown",
  ];
  const ALLOWED_EXTENSIONS = [".pdf", ".docx", ".txt", ".md"];

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

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    dragCounterRef.current = 0;

    const file = e.dataTransfer.files?.[0];
    if (!file) return;

    // Validate file type
    const isAllowed =
      ALLOWED_TYPES.includes(file.type) ||
      ALLOWED_EXTENSIONS.some((ext) => file.name.toLowerCase().endsWith(ext));

    if (!isAllowed) {
      // Could add toast notification here
      console.warn("Unsupported file type:", file.type);
      return;
    }

    await upload(file);
  };

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const message = input;
    setInput("");
    await sendMessage(message);
  };

  const defaultEmptyMessage = projectId
    ? "Hi! I'm your Thinking Partner. I can help you analyze your project context and think through problems. What would you like to explore?"
    : "Hi! I'm your Thinking Partner. I'm here to help you think through ideas, explore problems, and work on anything. What's on your mind?";

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
            <p className="text-lg font-medium text-foreground">Drop file here to add context</p>
            <p className="text-sm text-muted-foreground mt-1">PDF, DOCX, TXT, MD supported</p>
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4">
        {isLoadingHistory && (
          <div className="flex justify-center py-4">
            <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
          </div>
        )}

        {!isLoadingHistory && messages.length === 0 && (
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

        {/* Upload Progress Inline */}
        {uploadProgress && (
          <div className="flex justify-start">
            <div className="p-4 bg-muted rounded-lg max-w-[80%]">
              <div className="flex items-center gap-3">
                {uploadProgress.status === "uploading" || uploadProgress.status === "processing" ? (
                  <Loader2 className="w-5 h-5 animate-spin text-primary shrink-0" />
                ) : uploadProgress.status === "completed" ? (
                  <CheckCircle className="w-5 h-5 text-green-500 shrink-0" />
                ) : (
                  <AlertCircle className="w-5 h-5 text-red-500 shrink-0" />
                )}
                <div>
                  <div className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-muted-foreground" />
                    <span className="text-sm font-medium">{uploadProgress.filename}</span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {uploadProgress.status === "uploading" && "Uploading..."}
                    {uploadProgress.status === "processing" && "Processing document..."}
                    {uploadProgress.status === "completed" && (uploadProgress.message || "Document added to context")}
                    {uploadProgress.status === "failed" && (uploadProgress.message || "Upload failed")}
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="border-t border-border pt-4">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type a message..."
            disabled={isLoading}
            className="flex-1 px-4 py-2 border border-border rounded-md bg-background disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
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
  );
}

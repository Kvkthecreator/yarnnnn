"use client";

import { useState, useRef, useEffect, FormEvent } from "react";
import {
  FileText,
  Briefcase,
  MessageSquare,
  Send,
  Loader2,
  Trash2,
  Upload,
  X,
  MessageCircle,
  FileQuestion,
  Lightbulb,
  CheckCircle,
  BookOpen,
  HelpCircle,
} from "lucide-react";
import { useChat } from "@/hooks/useChat";
import { api } from "@/lib/api/client";
import type { Block, SemanticType } from "@/types";

type Tab = "context" | "work" | "chat";

interface Project {
  id: string;
  name: string;
  description?: string;
}

export default function ProjectPage({ params }: { params: { id: string } }) {
  const [activeTab, setActiveTab] = useState<Tab>("context");
  const [project, setProject] = useState<Project | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchProject() {
      try {
        const data = await api.projects.get(params.id);
        setProject(data);
      } catch (err) {
        console.error("Failed to fetch project:", err);
        setError("Failed to load project");
      } finally {
        setIsLoading(false);
      }
    }
    fetchProject();
  }, [params.id]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="min-h-screen p-8">
        <div className="p-4 bg-destructive/10 text-destructive rounded-lg">
          {error || "Project not found"}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="border-b border-border">
        <div className="container mx-auto px-4 py-4">
          <h1 className="text-xl font-semibold">{project.name}</h1>
          {project.description && (
            <p className="text-sm text-muted-foreground mt-1">
              {project.description}
            </p>
          )}
        </div>
      </header>

      {/* Tab Navigation */}
      <nav className="border-b border-border">
        <div className="container mx-auto px-4">
          <div className="flex gap-1">
            <TabButton
              active={activeTab === "context"}
              onClick={() => setActiveTab("context")}
              icon={<FileText className="w-4 h-4" />}
              label="Context"
            />
            <TabButton
              active={activeTab === "work"}
              onClick={() => setActiveTab("work")}
              icon={<Briefcase className="w-4 h-4" />}
              label="Work"
            />
            <TabButton
              active={activeTab === "chat"}
              onClick={() => setActiveTab("chat")}
              icon={<MessageSquare className="w-4 h-4" />}
              label="Chat"
            />
          </div>
        </div>
      </nav>

      {/* Tab Content */}
      <main className="container mx-auto px-4 py-6">
        {activeTab === "context" && <ContextTab projectId={params.id} />}
        {activeTab === "work" && <WorkTab projectId={params.id} />}
        {activeTab === "chat" && <ChatTab projectId={params.id} />}
      </main>
    </div>
  );
}

function TabButton({
  active,
  onClick,
  icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
        active
          ? "border-primary text-primary"
          : "border-transparent text-muted-foreground hover:text-foreground"
      }`}
    >
      {icon}
      {label}
    </button>
  );
}

const SEMANTIC_TYPE_CONFIG: Record<
  SemanticType,
  { label: string; icon: React.ReactNode; color: string }
> = {
  fact: {
    label: "Fact",
    icon: <CheckCircle className="w-3 h-3" />,
    color: "text-blue-600 bg-blue-50",
  },
  guideline: {
    label: "Guideline",
    icon: <BookOpen className="w-3 h-3" />,
    color: "text-purple-600 bg-purple-50",
  },
  requirement: {
    label: "Requirement",
    icon: <FileQuestion className="w-3 h-3" />,
    color: "text-red-600 bg-red-50",
  },
  insight: {
    label: "Insight",
    icon: <Lightbulb className="w-3 h-3" />,
    color: "text-yellow-600 bg-yellow-50",
  },
  note: {
    label: "Note",
    icon: <FileText className="w-3 h-3" />,
    color: "text-gray-600 bg-gray-50",
  },
  question: {
    label: "Question",
    icon: <HelpCircle className="w-3 h-3" />,
    color: "text-green-600 bg-green-50",
  },
};

const SOURCE_TYPE_LABELS: Record<string, { label: string; icon: React.ReactNode }> = {
  manual: { label: "manual", icon: <FileText className="w-3 h-3" /> },
  chat: { label: "from chat", icon: <MessageCircle className="w-3 h-3" /> },
  bulk: { label: "imported", icon: <Upload className="w-3 h-3" /> },
  document: { label: "from doc", icon: <FileText className="w-3 h-3" /> },
  import: { label: "imported", icon: <Upload className="w-3 h-3" /> },
};

function ContextTab({ projectId }: { projectId: string }) {
  const [blocks, setBlocks] = useState<Block[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showImportModal, setShowImportModal] = useState(false);
  const [isImporting, setIsImporting] = useState(false);

  // Fetch blocks
  useEffect(() => {
    async function fetchBlocks() {
      try {
        const data = await api.context.listBlocks(projectId);
        setBlocks(data);
      } catch (err) {
        console.error("Failed to fetch blocks:", err);
      } finally {
        setIsLoading(false);
      }
    }
    fetchBlocks();
  }, [projectId]);

  const handleDelete = async (blockId: string) => {
    try {
      await api.context.deleteBlock(blockId);
      setBlocks((prev) => prev.filter((b) => b.id !== blockId));
    } catch (err) {
      console.error("Failed to delete block:", err);
    }
  };

  const handleImport = async (text: string) => {
    setIsImporting(true);
    try {
      const result = await api.context.importBulk(projectId, { text });
      // Refresh blocks list
      const updated = await api.context.listBlocks(projectId);
      setBlocks(updated);
      setShowImportModal(false);
      alert(`Extracted ${result.blocks_extracted} blocks from your text.`);
    } catch (err) {
      console.error("Failed to import:", err);
      alert("Failed to import text. Please try again.");
    } finally {
      setIsImporting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-lg font-semibold">Context</h2>
        <div className="flex gap-2">
          <button
            onClick={() => setShowImportModal(true)}
            className="px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded-md inline-flex items-center gap-1"
          >
            <Upload className="w-4 h-4" />
            Import Text
          </button>
        </div>
      </div>

      {blocks.length === 0 ? (
        <div className="text-center py-12 border border-dashed border-border rounded-lg">
          <FileText className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
          <h3 className="text-lg font-medium mb-2">No context yet</h3>
          <p className="text-muted-foreground mb-4 max-w-md mx-auto">
            Context is automatically extracted from your chat conversations.
            You can also import existing notes or documents.
          </p>
          <button
            onClick={() => setShowImportModal(true)}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md inline-flex items-center gap-2"
          >
            <Upload className="w-4 h-4" />
            Import Text
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {blocks.map((block) => {
            const semanticConfig = block.semantic_type
              ? SEMANTIC_TYPE_CONFIG[block.semantic_type]
              : SEMANTIC_TYPE_CONFIG.note;
            const sourceConfig = block.source_type
              ? SOURCE_TYPE_LABELS[block.source_type]
              : SOURCE_TYPE_LABELS.manual;

            return (
              <div
                key={block.id}
                className="p-4 border border-border rounded-lg hover:border-muted-foreground/30 transition-colors group"
              >
                <div className="flex justify-between items-start gap-2">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${semanticConfig.color}`}
                      >
                        {semanticConfig.icon}
                        {semanticConfig.label}
                      </span>
                      <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                        {sourceConfig.icon}
                        {sourceConfig.label}
                      </span>
                    </div>
                    <p className="text-sm">{block.content}</p>
                  </div>
                  <button
                    onClick={() => handleDelete(block.id)}
                    className="p-1 text-muted-foreground hover:text-destructive opacity-0 group-hover:opacity-100 transition-opacity"
                    title="Delete block"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {showImportModal && (
        <ImportModal
          onClose={() => setShowImportModal(false)}
          onImport={handleImport}
          isImporting={isImporting}
        />
      )}
    </div>
  );
}

function ImportModal({
  onClose,
  onImport,
  isImporting,
}: {
  onClose: () => void;
  onImport: (text: string) => void;
  isImporting: boolean;
}) {
  const [text, setText] = useState("");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (text.trim().length >= 50) {
      onImport(text.trim());
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-background border border-border rounded-lg p-6 w-full max-w-2xl max-h-[80vh] flex flex-col">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold">Import Context</h2>
          <button
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <p className="text-sm text-muted-foreground mb-4">
          Paste your notes, meeting transcripts, or any text. We&apos;ll
          automatically extract key facts, requirements, and insights.
        </p>

        <form onSubmit={handleSubmit} className="flex-1 flex flex-col">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Paste your text here... (minimum 50 characters)"
            className="flex-1 min-h-[200px] w-full px-3 py-2 border border-border rounded-md bg-background resize-none"
            autoFocus
          />

          <div className="flex justify-between items-center mt-4">
            <span className="text-xs text-muted-foreground">
              {text.length} characters
              {text.length < 50 && text.length > 0 && " (need 50+)"}
            </span>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 border border-border rounded-md"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={text.trim().length < 50 || isImporting}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-md disabled:opacity-50 inline-flex items-center gap-2"
              >
                {isImporting && <Loader2 className="w-4 h-4 animate-spin" />}
                {isImporting ? "Extracting..." : "Extract Blocks"}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}

function WorkTab({ projectId }: { projectId: string }) {
  // TODO: Fetch tickets from API
  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-lg font-semibold">Work Tickets</h2>
        <button className="px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded-md">
          + New Request
        </button>
      </div>

      <div className="space-y-3">
        {/* Placeholder ticket */}
        <div className="p-4 border border-border rounded-lg">
          <div className="flex justify-between items-start mb-2">
            <h3 className="font-medium">No work tickets yet</h3>
            <span className="px-2 py-0.5 text-xs bg-muted rounded">pending</span>
          </div>
          <p className="text-sm text-muted-foreground">
            Create a work request to have an agent analyze your context.
          </p>
        </div>
      </div>
    </div>
  );
}

function ChatTab({ projectId }: { projectId: string }) {
  const { messages, isLoading, error, sendMessage } = useChat({
    projectId,
    includeContext: true,
  });
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

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

  return (
    <div className="flex flex-col h-[calc(100vh-240px)]">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4">
        {messages.length === 0 && (
          <div className="p-4 bg-muted rounded-lg max-w-[80%]">
            <p className="text-sm">
              Hi! I&apos;m your Thinking Partner. I can help you analyze your
              project context and think through problems. What would you like to
              explore?
            </p>
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

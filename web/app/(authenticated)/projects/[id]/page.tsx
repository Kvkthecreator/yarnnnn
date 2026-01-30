"use client";

import { useState, useEffect, FormEvent } from "react";
import {
  FileText,
  Briefcase,
  MessageSquare,
  Loader2,
  Trash2,
  Upload,
  X,
  MessageCircle,
  Tag,
  Star,
  CheckCircle2,
  XCircle,
  Clock,
  Play,
  Lightbulb,
  FileEdit,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import { Chat } from "@/components/Chat";
import { api } from "@/lib/api/client";
import type { Memory, WorkTicket, WorkOutput, WorkTicketCreate } from "@/types";

type Tab = "context" | "work" | "chat";

interface Project {
  id: string;
  name: string;
  description?: string;
}

export default function ProjectPage({ params }: { params: { id: string } }) {
  const [activeTab, setActiveTab] = useState<Tab>("chat");
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
              active={activeTab === "chat"}
              onClick={() => setActiveTab("chat")}
              icon={<MessageSquare className="w-4 h-4" />}
              label="Chat"
            />
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
          </div>
        </div>
      </nav>

      {/* Tab Content */}
      <main className="container mx-auto px-4 py-6">
        {activeTab === "context" && <ContextTab projectId={params.id} />}
        {activeTab === "work" && <WorkTab projectId={params.id} />}
        {activeTab === "chat" && <ChatTab projectId={params.id} projectName={project.name} />}
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

const SOURCE_TYPE_LABELS: Record<string, { label: string; icon: React.ReactNode }> = {
  manual: { label: "manual", icon: <FileText className="w-3 h-3" /> },
  chat: { label: "from chat", icon: <MessageCircle className="w-3 h-3" /> },
  bulk: { label: "imported", icon: <Upload className="w-3 h-3" /> },
  document: { label: "from doc", icon: <FileText className="w-3 h-3" /> },
  import: { label: "imported", icon: <Upload className="w-3 h-3" /> },
};

function ContextTab({ projectId }: { projectId: string }) {
  const [memories, setMemories] = useState<Memory[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showImportModal, setShowImportModal] = useState(false);
  const [isImporting, setIsImporting] = useState(false);

  // Fetch memories
  useEffect(() => {
    async function fetchMemories() {
      try {
        const data = await api.projectMemories.list(projectId);
        setMemories(data);
      } catch (err) {
        console.error("Failed to fetch memories:", err);
      } finally {
        setIsLoading(false);
      }
    }
    fetchMemories();
  }, [projectId]);

  const handleDelete = async (memoryId: string) => {
    try {
      await api.memories.delete(memoryId);
      setMemories((prev) => prev.filter((m) => m.id !== memoryId));
    } catch (err) {
      console.error("Failed to delete memory:", err);
    }
  };

  const handleImport = async (text: string) => {
    setIsImporting(true);
    try {
      const result = await api.projectMemories.importBulk(projectId, { text });
      // Refresh memories list
      const updated = await api.projectMemories.list(projectId);
      setMemories(updated);
      setShowImportModal(false);
      alert(`Extracted ${result.memories_extracted} memories from your text.`);
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

      {memories.length === 0 ? (
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
          {memories.map((memory) => {
            const sourceConfig = memory.source_type
              ? SOURCE_TYPE_LABELS[memory.source_type]
              : SOURCE_TYPE_LABELS.manual;

            return (
              <div
                key={memory.id}
                className="p-4 border border-border rounded-lg hover:border-muted-foreground/30 transition-colors group"
              >
                <div className="flex justify-between items-start gap-2">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2 flex-wrap">
                      {/* Tags */}
                      {memory.tags.map((tag) => (
                        <span
                          key={tag}
                          className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium text-primary bg-primary/10"
                        >
                          <Tag className="w-3 h-3" />
                          {tag}
                        </span>
                      ))}
                      {/* Importance indicator */}
                      {memory.importance >= 0.8 && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium text-yellow-600 bg-yellow-50">
                          <Star className="w-3 h-3" />
                          Important
                        </span>
                      )}
                      {/* Source type */}
                      <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
                        {sourceConfig.icon}
                        {sourceConfig.label}
                      </span>
                    </div>
                    <p className="text-sm">{memory.content}</p>
                  </div>
                  <button
                    onClick={() => handleDelete(memory.id)}
                    className="p-1 text-muted-foreground hover:text-destructive opacity-0 group-hover:opacity-100 transition-opacity"
                    title="Delete memory"
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
                {isImporting ? "Extracting..." : "Extract Memories"}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}

const STATUS_CONFIG: Record<string, { icon: React.ReactNode; color: string; label: string }> = {
  pending: { icon: <Clock className="w-3 h-3" />, color: "text-yellow-600 bg-yellow-50", label: "Pending" },
  running: { icon: <Loader2 className="w-3 h-3 animate-spin" />, color: "text-blue-600 bg-blue-50", label: "Running" },
  completed: { icon: <CheckCircle2 className="w-3 h-3" />, color: "text-green-600 bg-green-50", label: "Completed" },
  failed: { icon: <XCircle className="w-3 h-3" />, color: "text-red-600 bg-red-50", label: "Failed" },
};

const AGENT_TYPE_CONFIG: Record<string, { icon: React.ReactNode; label: string; description: string }> = {
  research: { icon: <Lightbulb className="w-4 h-4" />, label: "Research", description: "Analyze context and find insights" },
  content: { icon: <FileEdit className="w-4 h-4" />, label: "Content", description: "Generate content from context" },
  reporting: { icon: <FileText className="w-4 h-4" />, label: "Reporting", description: "Create structured reports" },
};

const OUTPUT_TYPE_ICONS: Record<string, React.ReactNode> = {
  finding: <CheckCircle2 className="w-4 h-4 text-blue-500" />,
  recommendation: <AlertTriangle className="w-4 h-4 text-amber-500" />,
  insight: <Lightbulb className="w-4 h-4 text-purple-500" />,
  draft: <FileEdit className="w-4 h-4 text-green-500" />,
  report: <FileText className="w-4 h-4 text-indigo-500" />,
};

function WorkTab({ projectId }: { projectId: string }) {
  const [tickets, setTickets] = useState<WorkTicket[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [expandedTicket, setExpandedTicket] = useState<string | null>(null);
  const [ticketOutputs, setTicketOutputs] = useState<Record<string, WorkOutput[]>>({});

  // Fetch tickets
  useEffect(() => {
    async function fetchTickets() {
      try {
        const data = await api.work.list(projectId);
        setTickets(data);
      } catch (err) {
        console.error("Failed to fetch tickets:", err);
      } finally {
        setIsLoading(false);
      }
    }
    fetchTickets();
  }, [projectId]);

  // Load outputs when ticket is expanded
  const handleToggleExpand = async (ticketId: string) => {
    if (expandedTicket === ticketId) {
      setExpandedTicket(null);
      return;
    }

    setExpandedTicket(ticketId);

    // Load outputs if not cached
    if (!ticketOutputs[ticketId]) {
      try {
        const detail = await api.work.get(ticketId);
        setTicketOutputs(prev => ({
          ...prev,
          [ticketId]: detail.outputs,
        }));
      } catch (err) {
        console.error("Failed to fetch ticket outputs:", err);
      }
    }
  };

  const handleCreate = async (data: WorkTicketCreate) => {
    setIsCreating(true);
    try {
      const result = await api.work.create(projectId, data);
      // Refresh tickets list
      const updated = await api.work.list(projectId);
      setTickets(updated);
      setShowCreateModal(false);

      // Auto-expand the new ticket to show outputs
      if (result.ticket_id) {
        setExpandedTicket(result.ticket_id);
        setTicketOutputs(prev => ({
          ...prev,
          [result.ticket_id]: result.outputs,
        }));
      }
    } catch (err) {
      console.error("Failed to create work:", err);
      alert("Failed to create work request. Please try again.");
    } finally {
      setIsCreating(false);
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
        <h2 className="text-lg font-semibold">Work Tickets</h2>
        <button
          onClick={() => setShowCreateModal(true)}
          className="px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded-md inline-flex items-center gap-1"
        >
          + New Request
        </button>
      </div>

      {tickets.length === 0 ? (
        <div className="text-center py-12 border border-dashed border-border rounded-lg">
          <Briefcase className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
          <h3 className="text-lg font-medium mb-2">No work tickets yet</h3>
          <p className="text-muted-foreground mb-4 max-w-md mx-auto">
            Create a work request to have an agent analyze your context and produce structured outputs.
          </p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-md inline-flex items-center gap-2"
          >
            + New Request
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {tickets.map((ticket) => {
            const statusConfig = STATUS_CONFIG[ticket.status] || STATUS_CONFIG.pending;
            const agentConfig = AGENT_TYPE_CONFIG[ticket.agent_type] || AGENT_TYPE_CONFIG.research;
            const isExpanded = expandedTicket === ticket.id;
            const outputs = ticketOutputs[ticket.id] || [];

            return (
              <div
                key={ticket.id}
                className="border border-border rounded-lg overflow-hidden"
              >
                {/* Ticket Header */}
                <div
                  className="p-4 cursor-pointer hover:bg-muted/30 transition-colors"
                  onClick={() => ticket.status === "completed" && handleToggleExpand(ticket.id)}
                >
                  <div className="flex justify-between items-start">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        {/* Agent type badge */}
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-muted">
                          {agentConfig.icon}
                          {agentConfig.label}
                        </span>
                        {/* Status badge */}
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${statusConfig.color}`}>
                          {statusConfig.icon}
                          {statusConfig.label}
                        </span>
                        {/* Expand indicator for completed tickets */}
                        {ticket.status === "completed" && (
                          <span className="text-muted-foreground">
                            {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                          </span>
                        )}
                      </div>
                      <p className="text-sm">{ticket.task}</p>
                      <p className="text-xs text-muted-foreground mt-1">
                        {new Date(ticket.created_at).toLocaleString()}
                        {ticket.completed_at && ` • Completed ${new Date(ticket.completed_at).toLocaleString()}`}
                      </p>
                    </div>
                  </div>
                  {ticket.error_message && (
                    <div className="mt-2 p-2 bg-destructive/10 text-destructive text-xs rounded">
                      {ticket.error_message}
                    </div>
                  )}
                </div>

                {/* Expanded Outputs */}
                {isExpanded && outputs.length > 0 && (
                  <div className="border-t border-border bg-muted/20 p-4">
                    <h4 className="text-sm font-medium mb-3">Outputs ({outputs.length})</h4>
                    <div className="space-y-3">
                      {outputs.map((output) => (
                        <OutputCard key={output.id} output={output} />
                      ))}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {showCreateModal && (
        <CreateWorkModal
          onClose={() => setShowCreateModal(false)}
          onCreate={handleCreate}
          isCreating={isCreating}
        />
      )}
    </div>
  );
}

function OutputCard({ output }: { output: WorkOutput }) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Parse content JSON
  let body: { summary?: string; details?: string; evidence?: string[]; implications?: string[] } | null = null;
  try {
    if (output.content) {
      body = JSON.parse(output.content);
    }
  } catch {
    // Content might be plain text
  }

  return (
    <div className="p-3 bg-background border border-border rounded-lg">
      <div
        className="flex items-start gap-2 cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        {OUTPUT_TYPE_ICONS[output.output_type] || <FileText className="w-4 h-4" />}
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="font-medium text-sm">{output.title}</span>
            <span className="text-xs text-muted-foreground capitalize">{output.output_type}</span>
          </div>
          {body?.summary && !isExpanded && (
            <p className="text-sm text-muted-foreground mt-1 line-clamp-2">{body.summary}</p>
          )}
        </div>
        <span className="text-muted-foreground">
          {isExpanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </span>
      </div>

      {isExpanded && body && (
        <div className="mt-3 pl-6 space-y-2 text-sm">
          {body.summary && (
            <div>
              <span className="font-medium text-muted-foreground">Summary:</span>
              <p>{body.summary}</p>
            </div>
          )}
          {body.details && (
            <div>
              <span className="font-medium text-muted-foreground">Details:</span>
              <p className="whitespace-pre-wrap">{body.details}</p>
            </div>
          )}
          {body.evidence && body.evidence.length > 0 && (
            <div>
              <span className="font-medium text-muted-foreground">Evidence:</span>
              <ul className="list-disc list-inside ml-2">
                {body.evidence.map((e, i) => <li key={i}>{e}</li>)}
              </ul>
            </div>
          )}
          {body.implications && body.implications.length > 0 && (
            <div>
              <span className="font-medium text-muted-foreground">Implications:</span>
              <ul className="list-disc list-inside ml-2">
                {body.implications.map((imp, i) => <li key={i}>{imp}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}

      {isExpanded && !body && output.content && (
        <div className="mt-3 pl-6 text-sm whitespace-pre-wrap">
          {output.content}
        </div>
      )}
    </div>
  );
}

function CreateWorkModal({
  onClose,
  onCreate,
  isCreating,
}: {
  onClose: () => void;
  onCreate: (data: WorkTicketCreate) => void;
  isCreating: boolean;
}) {
  const [task, setTask] = useState("");
  const [agentType, setAgentType] = useState<"research" | "content" | "reporting">("research");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (task.trim().length >= 10) {
      onCreate({ task: task.trim(), agent_type: agentType });
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-background border border-border rounded-lg p-6 w-full max-w-lg">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-semibold">New Work Request</h2>
          <button
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Agent Type Selection */}
          <div>
            <label className="block text-sm font-medium mb-2">Agent Type</label>
            <div className="grid grid-cols-3 gap-2">
              {Object.entries(AGENT_TYPE_CONFIG).map(([type, config]) => (
                <button
                  key={type}
                  type="button"
                  onClick={() => setAgentType(type as "research" | "content" | "reporting")}
                  className={`p-3 border rounded-lg text-left transition-colors ${
                    agentType === type
                      ? "border-primary bg-primary/5"
                      : "border-border hover:border-muted-foreground/30"
                  }`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    {config.icon}
                    <span className="font-medium text-sm">{config.label}</span>
                  </div>
                  <p className="text-xs text-muted-foreground">{config.description}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Task Input */}
          <div>
            <label className="block text-sm font-medium mb-2">Task Description</label>
            <textarea
              value={task}
              onChange={(e) => setTask(e.target.value)}
              placeholder="Describe what you want the agent to do..."
              className="w-full px-3 py-2 border border-border rounded-md bg-background resize-none h-24"
              autoFocus
            />
            <p className="text-xs text-muted-foreground mt-1">
              {task.length} characters {task.length < 10 && task.length > 0 && "(need 10+)"}
            </p>
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-border rounded-md"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={task.trim().length < 10 || isCreating}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-md disabled:opacity-50 inline-flex items-center gap-2"
            >
              {isCreating && <Loader2 className="w-4 h-4 animate-spin" />}
              {isCreating ? "Running..." : "Run Agent"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function ChatTab({ projectId, projectName }: { projectId: string; projectName: string }) {
  return <Chat projectId={projectId} projectName={projectName} includeContext />;
}

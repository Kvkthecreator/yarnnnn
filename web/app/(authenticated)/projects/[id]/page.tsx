"use client";

import { useState, useRef, useEffect, FormEvent } from "react";
import {
  FileText,
  Briefcase,
  MessageSquare,
  Send,
  Loader2,
} from "lucide-react";
import { useChat } from "@/hooks/useChat";
import { api } from "@/lib/api/client";

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

function ContextTab({ projectId }: { projectId: string }) {
  // TODO: Fetch blocks from API
  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-lg font-semibold">Context</h2>
        <div className="flex gap-2">
          <button className="px-3 py-1.5 text-sm border border-border rounded-md">
            + Add Block
          </button>
          <button className="px-3 py-1.5 text-sm border border-border rounded-md">
            Upload Document
          </button>
        </div>
      </div>

      <div className="space-y-3">
        {/* Placeholder blocks */}
        <div className="p-4 border border-border rounded-lg">
          <div className="text-xs text-muted-foreground mb-2">TEXT</div>
          <p>Add your first block to start building context...</p>
        </div>
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

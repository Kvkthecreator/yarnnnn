"use client";

import { useState } from "react";
import { FileText, Briefcase, MessageSquare } from "lucide-react";

type Tab = "context" | "work" | "chat";

export default function ProjectPage({ params }: { params: { id: string } }) {
  const [activeTab, setActiveTab] = useState<Tab>("context");

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="border-b border-border">
        <div className="container mx-auto px-4 py-4">
          <h1 className="text-xl font-semibold">Project {params.id}</h1>
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
  // TODO: Implement chat with SSE streaming
  return (
    <div className="flex flex-col h-[calc(100vh-200px)]">
      <div className="flex-1 overflow-y-auto space-y-4 mb-4">
        {/* Placeholder message */}
        <div className="p-4 bg-muted rounded-lg max-w-[80%]">
          <p className="text-sm">
            Hi! I&apos;m your Thinking Partner. I can help you analyze your
            project context and think through problems. What would you like to
            explore?
          </p>
        </div>
      </div>

      <div className="border-t border-border pt-4">
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="Type a message..."
            className="flex-1 px-4 py-2 border border-border rounded-md bg-background"
          />
          <button className="px-4 py-2 bg-primary text-primary-foreground rounded-md">
            Send
          </button>
        </div>
      </div>
    </div>
  );
}

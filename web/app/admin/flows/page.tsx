"use client";

import { useEffect, useRef, useState } from "react";
import mermaid from "mermaid";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Workflow,
  Zap,
  MessageSquare,
  Cog,
  TrendingUp,
  Boxes,
  ShieldCheck,
} from "lucide-react";
import flowsData from "@/lib/data/flows.json";

type FlowKey = "scheduled" | "reactive" | "addressed" | "mechanical" | "outcomes";
type TabKey = FlowKey | "specialist" | "invariants";

interface FlowNode {
  id: string;
  label: string;
  kind: string;
  actor: string;
  file_ref: string | null;
}

interface FlowGate {
  id: string;
  predicate: string;
  branches: string[];
  file_ref: string | null;
}

interface Flow {
  id: string;
  title: string;
  summary: string;
  primary_adrs: string[];
  mermaid: string;
  nodes: FlowNode[];
  gates: FlowGate[];
  cross_cuts_hit: string[];
  key_files: string[];
}

interface CrossCut {
  label: string;
  description: string;
  file_ref?: string;
  appears_in_flows: string[];
}

interface Invariant {
  id: string;
  statement: string;
  rationale: string;
  enforced_by: string;
}

interface Actor {
  kind: string;
  description: string;
}

interface FlowsData {
  snapshot: {
    as_of: string;
    commit: string;
    canonical_refs: string[];
    note: string;
  };
  actors: Record<string, Actor>;
  cross_cuts: Record<string, CrossCut>;
  invariants: Invariant[];
  flows: Record<FlowKey, Flow>;
  specialist_subloop: {
    title: string;
    description: string;
    primary_adrs: string[];
    file_refs: string[];
    roles: string[];
    mermaid: string;
  };
}

const data = flowsData as unknown as FlowsData;

const TABS: { key: TabKey; label: string; group: string; icon: typeof Workflow }[] = [
  { key: "scheduled", label: "Scheduled", group: "Triggers", icon: Workflow },
  { key: "reactive", label: "Reactive (proposal)", group: "Triggers", icon: Zap },
  { key: "addressed", label: "Addressed (Feed)", group: "Triggers", icon: MessageSquare },
  { key: "mechanical", label: "Mechanical dispatch", group: "Execution", icon: Cog },
  { key: "outcomes", label: "Outcome reconciliation", group: "Execution", icon: TrendingUp },
  { key: "specialist", label: "Specialist sub-loop", group: "Reference", icon: Boxes },
  { key: "invariants", label: "Invariants & cross-cuts", group: "Reference", icon: ShieldCheck },
];

const CROSS_CUT_STYLES: Record<string, string> = {
  authored_substrate_write: "border-emerald-500/40 text-emerald-600 dark:text-emerald-400",
  token_ledger_write: "border-amber-500/40 text-amber-600 dark:text-amber-400",
  narrative_append: "border-sky-500/40 text-sky-600 dark:text-sky-400",
  decisions_md_append: "border-rose-500/40 text-rose-600 dark:text-rose-400",
  autonomy_gate: "border-orange-500/40 text-orange-600 dark:text-orange-400",
  balance_gate: "border-orange-500/40 text-orange-600 dark:text-orange-400",
  execution_event_record: "border-border text-muted-foreground",
};

function FileRef({ value }: { value: string | null | undefined }) {
  if (!value) return null;
  return (
    <code className="inline-block bg-muted/50 border border-border/50 text-xs font-mono px-1.5 py-0.5 rounded">
      {value}
    </code>
  );
}

function Chip({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <span
      className={`inline-block text-xs font-normal border rounded-full px-2.5 py-0.5 mr-1.5 mb-1.5 ${className}`}
    >
      {children}
    </span>
  );
}

function CrossCutPill({ name }: { name: string }) {
  const style = CROSS_CUT_STYLES[name] ?? "border-border text-muted-foreground";
  return <Chip className={style}>{name.replace(/_/g, " ")}</Chip>;
}

function MermaidDiagram({ chart, id }: { chart: string; id: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ref.current) return;
    let cancelled = false;

    (async () => {
      try {
        // Render: returns { svg } string we inject. Use unique id per render.
        const { svg } = await mermaid.render(`mermaid-${id}-${Date.now()}`, chart);
        if (!cancelled && ref.current) {
          ref.current.innerHTML = svg;
        }
      } catch (e: any) {
        if (!cancelled) setError(e?.message ?? "Render failed");
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [chart, id]);

  if (error) {
    return (
      <div className="rounded-md border border-rose-500/40 bg-rose-500/5 p-4 text-sm text-rose-600 dark:text-rose-400">
        <p className="font-medium mb-1">Mermaid render error</p>
        <pre className="text-xs font-mono whitespace-pre-wrap">{error}</pre>
      </div>
    );
  }

  return (
    <div className="rounded-md border border-border/50 bg-muted/20 p-6 overflow-x-auto">
      <div ref={ref} className="mermaid-container flex justify-center min-h-[200px]" />
    </div>
  );
}

function FlowPanel({ flow }: { flow: Flow }) {
  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-2xl font-semibold tracking-tight mb-1.5">{flow.title}</h2>
        <div className="flex gap-1.5 flex-wrap mb-3">
          {flow.primary_adrs.map((adr) => (
            <Chip key={adr} className="font-mono bg-muted/40 border-border/60 text-foreground">
              {adr}
            </Chip>
          ))}
        </div>
        <p className="text-muted-foreground max-w-4xl leading-relaxed">{flow.summary}</p>
      </div>

      <MermaidDiagram chart={flow.mermaid} id={flow.id} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs uppercase tracking-wide text-muted-foreground">
              Decision gates
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2.5">
            {flow.gates.length === 0 ? (
              <p className="text-sm text-muted-foreground">No explicit gates.</p>
            ) : (
              flow.gates.map((g) => (
                <div
                  key={g.id}
                  className="border-l-2 border-orange-500/60 pl-3 py-1 text-sm"
                >
                  <div>
                    <span className="font-mono text-xs text-orange-600 dark:text-orange-400 font-medium mr-2">
                      {g.id}
                    </span>
                    <span className="italic">{g.predicate}</span>
                  </div>
                  <div className="mt-1 text-xs text-muted-foreground space-y-0.5">
                    {g.branches.map((b, i) => (
                      <div key={i}>→ {b}</div>
                    ))}
                  </div>
                  {g.file_ref && (
                    <div className="mt-1">
                      <FileRef value={g.file_ref} />
                    </div>
                  )}
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs uppercase tracking-wide text-muted-foreground">
              Cross-cuts hit
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="mb-3">
              {flow.cross_cuts_hit.map((cc) => (
                <CrossCutPill key={cc} name={cc} />
              ))}
            </div>
            <h4 className="text-xs uppercase tracking-wide text-muted-foreground mb-2">
              Key files
            </h4>
            <ul className="space-y-1">
              {flow.key_files.map((f) => (
                <li key={f}>
                  <FileRef value={f} />
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-xs uppercase tracking-wide text-muted-foreground">
            Nodes (file:line refs for code navigation)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2">
            {flow.nodes.map((n) => (
              <li key={n.id} className="text-sm">
                <span className="text-foreground font-medium">{n.label}</span>
                <span className="text-muted-foreground ml-2 text-xs">
                  ({n.kind} · {n.actor})
                </span>
                {n.file_ref && (
                  <div className="mt-0.5">
                    <FileRef value={n.file_ref} />
                  </div>
                )}
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}

function SpecialistPanel() {
  const s = data.specialist_subloop;
  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-2xl font-semibold tracking-tight mb-1.5">{s.title}</h2>
        <div className="flex gap-1.5 flex-wrap mb-3">
          {s.primary_adrs.map((adr) => (
            <Chip key={adr} className="font-mono bg-muted/40 border-border/60 text-foreground">
              {adr}
            </Chip>
          ))}
        </div>
        <p className="text-muted-foreground max-w-4xl leading-relaxed mb-2">{s.description}</p>
        <p className="text-sm text-muted-foreground">
          <span className="font-medium text-foreground">Roles:</span>{" "}
          {s.roles.map((r, i) => (
            <span key={r}>
              <code className="bg-muted/50 px-1.5 py-0.5 rounded text-xs">{r}</code>
              {i < s.roles.length - 1 ? " · " : ""}
            </span>
          ))}
        </p>
      </div>

      <MermaidDiagram chart={s.mermaid} id="specialist" />

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-xs uppercase tracking-wide text-muted-foreground">
            File refs
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-1">
            {s.file_refs.map((f) => (
              <li key={f}>
                <FileRef value={f} />
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}

function InvariantsPanel() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold tracking-tight mb-1.5">
          Invariants &amp; cross-cutting concerns
        </h2>
        <p className="text-muted-foreground max-w-4xl leading-relaxed">
          Eight invariants the architecture upholds — verify them after any change to dispatch,
          the Reviewer, or substrate writes. Cross-cuts are concerns that surface in multiple
          flows; each entry below shows where it fires.
        </p>
      </div>

      <div>
        <h3 className="text-sm uppercase tracking-wide text-muted-foreground mb-2.5">
          Invariants
        </h3>
        <div className="space-y-2">
          {data.invariants.map((inv) => (
            <div
              key={inv.id}
              className="border border-border/50 border-l-2 border-l-emerald-500/60 rounded-md p-3.5 bg-muted/10"
            >
              <div className="text-sm">
                <span className="font-mono text-xs text-emerald-600 dark:text-emerald-400 font-medium mr-2">
                  {inv.id}
                </span>
                <span className="text-foreground">{inv.statement}</span>
              </div>
              <p className="mt-1.5 text-xs text-muted-foreground">{inv.rationale}</p>
              <p className="mt-1.5 text-xs text-muted-foreground/70">
                Enforced by: <span className="font-mono">{inv.enforced_by}</span>
              </p>
            </div>
          ))}
        </div>
      </div>

      <div>
        <h3 className="text-sm uppercase tracking-wide text-muted-foreground mb-2.5">
          Cross-cutting concerns
        </h3>
        <div className="space-y-3">
          {Object.entries(data.cross_cuts).map(([key, cc]) => (
            <Card key={key}>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <CrossCutPill name={key} />
                  <span>{cc.label}</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <p className="text-sm text-muted-foreground">{cc.description}</p>
                {cc.file_ref && <FileRef value={cc.file_ref} />}
                <div className="text-xs text-muted-foreground/70">
                  Appears in flows:{" "}
                  {cc.appears_in_flows.map((f, i) => (
                    <span key={f}>
                      <code className="bg-muted/50 px-1.5 py-0.5 rounded">{f}</code>
                      {i < cc.appears_in_flows.length - 1 ? " · " : ""}
                    </span>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      <div>
        <h3 className="text-sm uppercase tracking-wide text-muted-foreground mb-2.5">
          Actor reference
        </h3>
        <Card>
          <CardContent className="pt-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
              {Object.entries(data.actors).map(([key, actor]) => (
                <div key={key} className="text-muted-foreground">
                  <span className="font-medium text-foreground">{key}</span>{" "}
                  <span className="text-muted-foreground/70 text-xs">({actor.kind})</span>
                  <div className="text-xs mt-0.5">{actor.description}</div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export default function AdminFlowsPage() {
  const [activeTab, setActiveTab] = useState<TabKey>("scheduled");

  // Initialize mermaid once with dark-mode-aware theme
  useEffect(() => {
    const isDark =
      typeof window !== "undefined" &&
      document.documentElement.classList.contains("dark");
    mermaid.initialize({
      startOnLoad: false,
      theme: isDark ? "dark" : "default",
      themeVariables: {
        fontFamily: "ui-sans-serif, system-ui, sans-serif",
        fontSize: "13px",
      },
      flowchart: { curve: "basis", padding: 12 },
      securityLevel: "loose",
    });
  }, []);

  // Honour ?tab=<key> on first load
  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    const t = params.get("tab") as TabKey | null;
    if (t && TABS.some((x) => x.key === t)) {
      setActiveTab(t);
    }
  }, []);

  // Update URL hash on tab change
  useEffect(() => {
    if (typeof window === "undefined") return;
    const url = new URL(window.location.href);
    url.searchParams.set("tab", activeTab);
    window.history.replaceState({}, "", url.toString());
  }, [activeTab]);

  // Group tabs for sidebar
  const groups = TABS.reduce<Record<string, typeof TABS>>((acc, tab) => {
    if (!acc[tab.group]) acc[tab.group] = [];
    acc[tab.group].push(tab);
    return acc;
  }, {});

  return (
    <div>
      {/* Snapshot header */}
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight mb-2">
          Architecture &amp; Flows
        </h1>
        <div className="flex flex-wrap gap-2 text-xs text-muted-foreground mb-2">
          <span className="bg-muted/40 border border-border/50 rounded px-2 py-0.5">
            Snapshot: <span className="font-medium text-foreground">{data.snapshot.as_of}</span>
          </span>
          <span className="bg-muted/40 border border-border/50 rounded px-2 py-0.5">
            Commit: <code className="font-mono">{data.snapshot.commit}</code>
          </span>
          <span className="bg-muted/40 border border-border/50 rounded px-2 py-0.5">
            Post-ADR-260/261/262 merge
          </span>
        </div>
        <p className="text-xs text-muted-foreground/80 max-w-4xl leading-relaxed">
          {data.snapshot.note}
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[220px_1fr] gap-6">
        {/* Sidebar tabs */}
        <nav className="border-r border-border/40 lg:pr-2 -ml-2">
          {Object.entries(groups).map(([group, tabs]) => (
            <div key={group} className="mb-3">
              <div className="text-[10px] uppercase tracking-wider text-muted-foreground/70 px-3 pb-1.5">
                {group}
              </div>
              {tabs.map((tab) => {
                const Icon = tab.icon;
                const isActive = activeTab === tab.key;
                return (
                  <button
                    key={tab.key}
                    onClick={() => setActiveTab(tab.key)}
                    className={`w-full text-left flex items-center gap-2 px-3 py-1.5 text-sm border-l-2 transition-colors ${
                      isActive
                        ? "border-primary text-foreground bg-muted/40"
                        : "border-transparent text-muted-foreground hover:text-foreground hover:bg-muted/20"
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5 shrink-0" />
                    <span>{tab.label}</span>
                  </button>
                );
              })}
            </div>
          ))}
        </nav>

        {/* Content */}
        <div className="min-w-0">
          {activeTab === "specialist" ? (
            <SpecialistPanel />
          ) : activeTab === "invariants" ? (
            <InvariantsPanel />
          ) : (
            <FlowPanel flow={data.flows[activeTab]} />
          )}
        </div>
      </div>
    </div>
  );
}

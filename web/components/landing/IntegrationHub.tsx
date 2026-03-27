"use client";

import { useEffect, useRef, useState, useCallback } from "react";

/**
 * Animated Beam Integration Hub
 *
 * Context (left) → yarnnn (center) → Agents (right)
 *
 * Left side shows the four ways context reaches agents:
 *   Conversation, Documents, Slack, Notion
 * Right side shows the four specialist agents:
 *   Research, Content, Marketing, CRM
 *
 * Beams animate left→center (context in) and center→right (work out).
 * Hidden below lg breakpoint.
 */

// ─── Node definitions ────────────────────────────────────────────────────────

interface NodeDef {
  id: string;
  label: string;
  icon: React.ReactNode;
  color: string;
  side: "left" | "right";
}

// ─── Icons ───────────────────────────────────────────────────────────────────

const ChatIcon = () => (
  <svg viewBox="0 0 24 24" className="w-[18px] h-[18px]" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
  </svg>
);

const DocsIcon = () => (
  <svg viewBox="0 0 24 24" className="w-[18px] h-[18px]" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <polyline points="14 2 14 8 20 8" />
    <line x1="16" y1="13" x2="8" y2="13" />
    <line x1="16" y1="17" x2="8" y2="17" />
    <polyline points="10 9 9 9 8 9" />
  </svg>
);

const SlackIcon = () => (
  <svg viewBox="0 0 24 24" className="w-[18px] h-[18px]" fill="currentColor">
    <path d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zM6.313 15.165a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313zM8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zM8.834 6.313a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312zM18.956 8.834a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834zM17.688 8.834a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.165 0a2.528 2.528 0 0 1 2.523 2.522v6.312zM15.165 18.956a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.165 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52zM15.165 17.688a2.527 2.527 0 0 1-2.52-2.523 2.526 2.526 0 0 1 2.52-2.52h6.313A2.527 2.527 0 0 1 24 15.165a2.528 2.528 0 0 1-2.522 2.523h-6.313z" />
  </svg>
);

const NotionIcon = () => (
  <svg viewBox="0 0 24 24" className="w-[18px] h-[18px]" fill="currentColor">
    <path d="M4.459 4.208c.746.606 1.026.56 2.428.466l13.215-.793c.28 0 .047-.28-.046-.326L17.86 1.968c-.42-.326-.981-.7-2.055-.607L3.01 2.295c-.466.046-.56.28-.374.466zm.793 3.08v13.904c0 .747.373 1.027 1.214.98l14.523-.84c.841-.046.935-.56.935-1.167V6.354c0-.606-.233-.933-.748-.887l-15.177.887c-.56.047-.747.327-.747.933zm14.337.745c.093.42 0 .84-.42.888l-.7.14v10.264c-.608.327-1.168.514-1.635.514-.748 0-.935-.234-1.495-.933l-4.577-7.186v6.952l1.448.327s0 .84-1.168.84l-3.222.186c-.093-.186 0-.653.327-.746l.84-.233V9.854L7.822 9.76c-.094-.42.14-1.026.793-1.073l3.456-.233 4.764 7.279v-6.44l-1.215-.14c-.093-.514.28-.887.747-.933zM1.936 1.035l13.31-.98c1.634-.14 2.055-.047 3.082.7l4.249 2.986c.7.513.934.653.934 1.213v16.378c0 1.026-.373 1.634-1.68 1.726l-15.458.934c-.98.047-1.448-.093-1.962-.747l-3.129-4.06c-.56-.747-.793-1.306-.793-1.96V2.667c0-.839.374-1.54 1.447-1.632z" />
  </svg>
);

const AgentIcon = ({ letter }: { letter: string }) => (
  <span className="text-xs font-bold leading-none">{letter}</span>
);

const nodes: NodeDef[] = [
  // Context sources (left)
  { id: "chat", label: "Conversation", icon: <ChatIcon />, color: "#8b5cf6", side: "left" },
  { id: "docs", label: "Documents", icon: <DocsIcon />, color: "#3b82f6", side: "left" },
  { id: "slack", label: "Slack", icon: <SlackIcon />, color: "#E01E5A", side: "left" },
  { id: "notion", label: "Notion", icon: <NotionIcon />, color: "#191919", side: "left" },
  // Agents (right)
  { id: "research", label: "Research", icon: <AgentIcon letter="R" />, color: "#6366f1", side: "right" },
  { id: "content", label: "Content", icon: <AgentIcon letter="C" />, color: "#0ea5e9", side: "right" },
  { id: "marketing", label: "Marketing", icon: <AgentIcon letter="M" />, color: "#f59e0b", side: "right" },
  { id: "crm", label: "CRM", icon: <AgentIcon letter="CR" />, color: "#10b981", side: "right" },
];

const leftNodes = nodes.filter((n) => n.side === "left");
const rightNodes = nodes.filter((n) => n.side === "right");

// ─── Animated beam (SVG) ─────────────────────────────────────────────────────

function AnimatedBeam({
  pathD,
  color,
  delay,
  duration,
  id,
  reverse,
}: {
  pathD: string;
  color: string;
  delay: number;
  duration: number;
  id: string;
  reverse?: boolean;
}) {
  return (
    <g>
      {/* Faint static path */}
      <path d={pathD} fill="none" stroke={color} strokeOpacity={0.06} strokeWidth={2} />

      {/* Animated gradient beam */}
      <path
        d={pathD}
        fill="none"
        stroke={`url(#beam-grad-${id})`}
        strokeWidth={2}
        strokeLinecap="round"
      />

      <defs>
        <linearGradient id={`beam-grad-${id}`} gradientUnits="userSpaceOnUse">
          <stop stopColor={color} stopOpacity={0}>
            <animate
              attributeName="offset"
              values={reverse ? "1;-0.5" : "-0.5;1"}
              dur={`${duration}s`}
              begin={`${delay}s`}
              repeatCount="indefinite"
            />
          </stop>
          <stop stopColor={color} stopOpacity={0.5}>
            <animate
              attributeName="offset"
              values={reverse ? "1.15;-0.35" : "-0.35;1.15"}
              dur={`${duration}s`}
              begin={`${delay}s`}
              repeatCount="indefinite"
            />
          </stop>
          <stop stopColor={color} stopOpacity={0.5}>
            <animate
              attributeName="offset"
              values={reverse ? "1.5;0" : "0;1.5"}
              dur={`${duration}s`}
              begin={`${delay}s`}
              repeatCount="indefinite"
            />
          </stop>
          <stop stopColor={color} stopOpacity={0}>
            <animate
              attributeName="offset"
              values={reverse ? "1.65;0.15" : "0.15;1.65"}
              dur={`${duration}s`}
              begin={`${delay}s`}
              repeatCount="indefinite"
            />
          </stop>
        </linearGradient>
      </defs>
    </g>
  );
}

// ─── Main component ──────────────────────────────────────────────────────────

export function IntegrationHub() {
  const containerRef = useRef<HTMLDivElement>(null);
  const centerRef = useRef<HTMLDivElement>(null);
  const nodeElMap = useRef<Record<string, HTMLDivElement | null>>({});
  const [paths, setPaths] = useState<{ id: string; d: string; color: string; reverse: boolean }[]>([]);
  const [ready, setReady] = useState(false);

  const assignRef = useCallback((id: string) => (el: HTMLDivElement | null) => {
    nodeElMap.current[id] = el;
  }, []);

  useEffect(() => {
    function compute() {
      const container = containerRef.current;
      const center = centerRef.current;
      if (!container || !center) return;

      const cr = container.getBoundingClientRect();
      const ce = center.getBoundingClientRect();
      const cx = ce.left + ce.width / 2 - cr.left;
      const cy = ce.top + ce.height / 2 - cr.top;

      const result: typeof paths = [];

      nodes.forEach((node) => {
        const el = nodeElMap.current[node.id];
        if (!el) return;
        const r = el.getBoundingClientRect();
        const nx = r.left + r.width / 2 - cr.left;
        const ny = r.top + r.height / 2 - cr.top;

        // Cubic bezier — smooth horizontal curve to center
        const cpX1 = nx + (cx - nx) * 0.55;
        const cpX2 = cx - (cx - nx) * 0.45;

        const d = `M ${nx} ${ny} C ${cpX1} ${ny}, ${cpX2} ${cy}, ${cx} ${cy}`;
        result.push({
          id: node.id,
          d,
          color: node.color,
          reverse: node.side === "right",
        });
      });

      setPaths(result);
      setReady(true);
    }

    const t = setTimeout(compute, 50);
    window.addEventListener("resize", compute);
    return () => {
      clearTimeout(t);
      window.removeEventListener("resize", compute);
    };
  }, []);

  return (
    <div className="hidden lg:block">
      <div
        ref={containerRef}
        className="relative w-[500px] h-[340px]"
      >
        {/* SVG beams */}
        <svg
          className="absolute inset-0 w-full h-full pointer-events-none"
          style={{ overflow: "visible", opacity: ready ? 1 : 0, transition: "opacity 0.6s ease" }}
        >
          {paths.map((p, i) => (
            <AnimatedBeam
              key={p.id}
              id={p.id}
              pathD={p.d}
              color={p.color}
              delay={i * 0.3}
              duration={2.8}
              reverse={p.reverse}
            />
          ))}
        </svg>

        {/* 3-column node layout */}
        <div className="absolute inset-0 flex items-center justify-between px-3">
          {/* Left — Context */}
          <div className="flex flex-col items-center gap-6">
            <div className="text-[9px] text-[#1a1a1a]/25 uppercase tracking-[0.2em] font-medium">
              Context
            </div>
            {leftNodes.map((node) => (
              <div key={node.id} ref={assignRef(node.id)} className="group flex flex-col items-center gap-1.5">
                <div
                  className="w-11 h-11 rounded-full border-2 bg-white shadow-md flex items-center justify-center transition-all duration-300 group-hover:scale-110 group-hover:shadow-lg"
                  style={{ borderColor: `${node.color}30`, color: node.color }}
                >
                  {node.icon}
                </div>
                <span className="text-[10px] text-[#1a1a1a]/40 font-medium tracking-wide">
                  {node.label}
                </span>
              </div>
            ))}
          </div>

          {/* Center — yarnnn */}
          <div ref={centerRef} className="relative z-10">
            <div className="absolute inset-0 rounded-2xl bg-white/80 blur-xl" />
            <div className="relative w-[72px] h-[72px] rounded-2xl bg-white shadow-xl border border-[#1a1a1a]/5 flex items-center justify-center">
              <span className="font-brand text-xl text-[#1a1a1a]">y</span>
            </div>
          </div>

          {/* Right — Agents */}
          <div className="flex flex-col items-center gap-6">
            <div className="text-[9px] text-[#1a1a1a]/25 uppercase tracking-[0.2em] font-medium">
              Agents
            </div>
            {rightNodes.map((node) => (
              <div key={node.id} ref={assignRef(node.id)} className="group flex flex-col items-center gap-1.5">
                <div
                  className="w-11 h-11 rounded-full border-2 bg-white shadow-md flex items-center justify-center transition-all duration-300 group-hover:scale-110 group-hover:shadow-lg"
                  style={{ borderColor: `${node.color}30`, color: node.color }}
                >
                  {node.icon}
                </div>
                <span className="text-[10px] text-[#1a1a1a]/40 font-medium tracking-wide">
                  {node.label}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Subtitle */}
      <div className="text-center mt-6">
        <p className="text-xs text-[#1a1a1a]/30 tracking-wide">
          Context flows in. Work flows out.
        </p>
      </div>
    </div>
  );
}

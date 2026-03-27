"use client";

/**
 * MockOutputs — fake rendered output previews that show what agents produce.
 * Each mock simulates a real deliverable format (PDF, email, brief).
 * Supports light and dark variants.
 */

interface MockVariantProps {
  variant?: "light" | "dark";
}

// Shared color helpers
function c(variant: "light" | "dark") {
  const dark = variant === "dark";
  return {
    cardBg: dark ? "bg-white/[0.04]" : "bg-white",
    cardBorder: dark ? "border-white/[0.08]" : "border-[#1a1a1a]/[0.06]",
    cardShadow: dark ? "" : "shadow-md",
    sectionBorder: dark ? "border-white/[0.06]" : "border-[#1a1a1a]/[0.04]",
    barHeavy: dark ? "bg-white/[0.12]" : "bg-[#1a1a1a]/[0.08]",
    barLight: dark ? "bg-white/[0.06]" : "bg-[#1a1a1a]/[0.04]",
    barSection: dark ? "bg-white/[0.10]" : "bg-[#1a1a1a]/[0.07]",
    textMuted: dark ? "text-white/40" : "text-[#1a1a1a]/40",
    textFaint: dark ? "text-white/30" : "text-[#1a1a1a]/30",
    textLight: dark ? "text-white/60" : "text-[#1a1a1a]/60",
    textStrong: dark ? "text-white/70" : "text-[#1a1a1a]/70",
    label: dark ? "text-white/30" : "text-[#1a1a1a]/30",
  };
}

export function MockPDF({ variant = "light" }: MockVariantProps) {
  const s = c(variant);
  return (
    <div className="w-full max-w-[220px] mx-auto">
      <div className={`rounded-lg ${s.cardShadow} border ${s.cardBorder} ${s.cardBg} overflow-hidden`}>
        {/* PDF header bar */}
        <div className={`bg-red-500/10 px-3 py-1.5 flex items-center gap-2 border-b ${s.sectionBorder}`}>
          <div className="w-3 h-3 rounded-sm bg-red-500/70 flex items-center justify-center">
            <span className="text-white text-[6px] font-bold">PDF</span>
          </div>
          <span className={`text-[10px] ${s.textMuted} font-medium`}>weekly-status.pdf</span>
        </div>
        {/* Fake content lines */}
        <div className="p-3 space-y-2">
          <div className={`h-2.5 ${s.barHeavy} rounded w-[80%]`} />
          <div className={`h-1.5 ${s.barLight} rounded w-full`} />
          <div className={`h-1.5 ${s.barLight} rounded w-[90%]`} />
          <div className={`h-1.5 ${s.barLight} rounded w-[70%]`} />
          <div className={`mt-3 h-1.5 ${s.barLight} rounded w-full`} />
          <div className={`h-1.5 ${s.barLight} rounded w-[85%]`} />
          <div className={`h-1.5 ${s.barLight} rounded w-[60%]`} />
          {/* Fake chart */}
          <div className="mt-2 flex items-end gap-1 h-8">
            <div className="w-3 bg-indigo-400/30 rounded-t" style={{ height: "40%" }} />
            <div className="w-3 bg-indigo-400/40 rounded-t" style={{ height: "65%" }} />
            <div className="w-3 bg-indigo-400/50 rounded-t" style={{ height: "55%" }} />
            <div className="w-3 bg-indigo-400/60 rounded-t" style={{ height: "80%" }} />
            <div className="w-3 bg-indigo-400/70 rounded-t" style={{ height: "100%" }} />
          </div>
        </div>
      </div>
      <div className="text-center mt-2">
        <span className={`text-[10px] ${s.label} font-medium`}>PDF report</span>
      </div>
    </div>
  );
}

export function MockEmail({ variant = "light" }: MockVariantProps) {
  const s = c(variant);
  return (
    <div className="w-full max-w-[260px] mx-auto">
      <div className={`rounded-lg ${s.cardShadow} border ${s.cardBorder} ${s.cardBg} overflow-hidden`}>
        {/* Email header */}
        <div className={`px-3 py-2 border-b ${s.sectionBorder} space-y-1`}>
          <div className="flex items-center gap-2">
            <span className={`text-[9px] ${s.textFaint}`}>From:</span>
            <span className={`text-[9px] ${s.textLight} font-medium`}>Content Agent</span>
          </div>
          <div className="flex items-center gap-2">
            <span className={`text-[9px] ${s.textFaint}`}>Subject:</span>
            <span className={`text-[9px] ${s.textStrong} font-medium`}>Weekly Team Recap — Mar 24</span>
          </div>
        </div>
        {/* Fake body */}
        <div className="p-3 space-y-2">
          <div className={`text-[9px] ${s.textLight} font-medium`}>Key highlights this week:</div>
          <div className="space-y-1.5 pl-2">
            <div className="flex items-start gap-1.5">
              <div className="w-1 h-1 rounded-full bg-indigo-400/60 mt-1 shrink-0" />
              <div className={`h-1.5 ${s.barLight} rounded w-full`} />
            </div>
            <div className="flex items-start gap-1.5">
              <div className="w-1 h-1 rounded-full bg-indigo-400/60 mt-1 shrink-0" />
              <div className={`h-1.5 ${s.barLight} rounded w-[85%]`} />
            </div>
            <div className="flex items-start gap-1.5">
              <div className="w-1 h-1 rounded-full bg-amber-400/60 mt-1 shrink-0" />
              <div className={`h-1.5 ${s.barLight} rounded w-[75%]`} />
            </div>
          </div>
          <div className={`mt-2 h-1.5 ${s.barLight} rounded w-full`} />
          <div className={`h-1.5 ${s.barLight} rounded w-[90%]`} />
        </div>
      </div>
      <div className="text-center mt-2">
        <span className={`text-[10px] ${s.label} font-medium`}>Email delivery</span>
      </div>
    </div>
  );
}

export function MockBrief({ variant = "light" }: MockVariantProps) {
  const s = c(variant);
  return (
    <div className="w-full max-w-[240px] mx-auto">
      <div className={`rounded-lg ${s.cardShadow} border ${s.cardBorder} ${s.cardBg} overflow-hidden`}>
        {/* Brief header */}
        <div className={`px-3 py-2 border-b ${s.sectionBorder} flex items-center justify-between`}>
          <span className={`text-[10px] ${s.textLight} font-medium`}>Competitor Brief</span>
          <div className="flex items-center gap-1">
            <div className="w-4 h-4 rounded-full bg-indigo-100 flex items-center justify-center">
              <span className="text-[7px] text-indigo-600 font-bold">R</span>
            </div>
            <span className={`text-[8px] ${s.textFaint}`}>Research Agent</span>
          </div>
        </div>
        {/* Fake sections */}
        <div className="p-3 space-y-3">
          <div>
            <div className={`h-2 ${s.barSection} rounded w-[60%] mb-1.5`} />
            <div className={`h-1.5 ${s.barLight} rounded w-full`} />
            <div className={`h-1.5 ${s.barLight} rounded w-[80%] mt-0.5`} />
          </div>
          <div>
            <div className={`h-2 ${s.barSection} rounded w-[50%] mb-1.5`} />
            <div className={`h-1.5 ${s.barLight} rounded w-[95%]`} />
            <div className={`h-1.5 ${s.barLight} rounded w-[70%] mt-0.5`} />
          </div>
          {/* Status indicator */}
          <div className="flex items-center gap-1.5 pt-1">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            <span className={`text-[8px] ${s.textMuted}`}>Updated 2h ago</span>
          </div>
        </div>
      </div>
      <div className="text-center mt-2">
        <span className={`text-[10px] ${s.label} font-medium`}>Intelligence brief</span>
      </div>
    </div>
  );
}

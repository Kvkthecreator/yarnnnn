/**
 * CarouselHub — the connect/attribution slide for the ad carousel
 * (1080×1080, 6s). Ported from the landing page's IntegrationHub
 * (web/components/landing/IntegrationHub.tsx).
 *
 * ── COMPACT SCAFFOLDING (differs deliberately from CarouselFiles) ──
 * Built to the brief "no unnecessary opening and closing blank screens" and
 * "consider the thumbnail":
 *
 *   1. FRAME 0 IS THE POSTER. Every element — headline, both columns, all
 *      eight nodes, the hub, the caption — is at full opacity from the first
 *      frame. Nothing fades in from blank, nothing fades out at the end. A
 *      social platform that samples frame 0 for a thumbnail (most do) gets
 *      the finished composition, not an empty peach square.
 *   2. THE ONLY MOTION IS THE BEAMS. Pulses travel the wires continuously and
 *      seamlessly, so the loop has no seam to hide and the clip can be cut at
 *      any length without breaking.
 *   3. NO OUTRO FADE. The last frame equals the first; a looping card cuts
 *      clean without a dip to background.
 *
 * Geometry is COMPUTED, not measured. The web component measures DOM nodes
 * (useRef + getBoundingClientRect) to lay out its beams — impossible to do
 * deterministically per-frame. Here the same layout is derived arithmetically,
 * which makes every frame independently renderable.
 */

import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig, interpolate } from "remotion";
import { COLOR, FONT, Watermark, YarnBall } from "../design";
import {
  ClaudeMark, ChatGPTMark, SlackMark, NotionMark,
  FilesMark, DocumentsMark, AgentsMark, HistoryMark,
} from "../replicas/marks";

/** Verbatim from the landing hub + AppShowcase hero copy. */
const HEADLINE = "Work in any AI.";
const SUBLINE = "It lands in one workspace \u2014 signed.";

const LEFT = [
  { label: "Claude", Mark: ClaudeMark },
  { label: "ChatGPT", Mark: ChatGPTMark },
  { label: "Slack", Mark: SlackMark },
  { label: "Notion", Mark: NotionMark },
];
const RIGHT = [
  { label: "Files", Mark: FilesMark },
  { label: "Documents", Mark: DocumentsMark },
  { label: "Agents", Mark: AgentsMark },
  { label: "History", Mark: HistoryMark },
];

// ── Computed geometry (canvas coordinates) ──
const CX = 540;          // hub centre x
const CY = 648;          // hub centre y — below the headline block
const COL_L = 176;       // left column centre x
const COL_R = 904;       // right column centre x
const ROW_0 = 474;       // first node centre y
const ROW_GAP = 116;
const NODE = 78;         // node diameter
const HUB = 108;         // hub diameter

const rowY = (i: number) => ROW_0 + i * ROW_GAP;

/** A cubic curve from a column node into the hub, matching the page's arcs. */
const beamPath = (fromX: number, fromY: number, toX: number, toY: number) => {
  const midX = (fromX + toX) / 2;
  return `M ${fromX} ${fromY} C ${midX} ${fromY}, ${midX} ${toY}, ${toX} ${toY}`;
};

/** One node: mark in a white disc, label beneath. Static — never animates. */
const Node: React.FC<{
  x: number; y: number; label: string; Mark: React.FC<{ size?: number; color?: string }>;
}> = ({ x, y, label, Mark }) => (
  <div
    style={{
      position: "absolute",
      left: x - NODE / 2,
      top: y - NODE / 2,
      width: NODE,
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
    }}
  >
    <div
      style={{
        width: NODE, height: NODE, borderRadius: "50%",
        backgroundColor: "#fffdfb",
        border: "1px solid rgba(26,26,26,0.07)",
        boxShadow: "0 2px 10px rgba(26,26,26,0.05)",
        display: "flex", alignItems: "center", justifyContent: "center",
        color: COLOR.fg,
      }}
    >
      <Mark size={34} color={COLOR.fg} />
    </div>
    <span
      style={{
        marginTop: 12, fontFamily: FONT.body, fontSize: 20,
        color: "rgba(26,26,26,0.5)", whiteSpace: "nowrap",
      }}
    >
      {label}
    </span>
  </div>
);

/**
 * A pulse travelling one wire. Uses a dash-offset walk rather than an SVG
 * <animate> (which Remotion cannot seek) so the position is a pure function
 * of the frame.
 */
const Beam: React.FC<{ d: string; length: number; offset: number; reverse: boolean }> = ({
  d, length, offset, reverse,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const cycle = durationInFrames;           // one full traverse per loop
  const t = ((frame / cycle) + offset) % 1;
  const dash = length * 0.22;               // visible pulse length
  const travel = reverse ? (1 - t) : t;
  const pos = interpolate(travel, [0, 1], [-dash, length]);

  return (
    <>
      <path d={d} fill="none" stroke={COLOR.fg} strokeOpacity={0.07} strokeWidth={2} />
      <path
        d={d}
        fill="none"
        stroke={COLOR.fg}
        strokeOpacity={0.3}
        strokeWidth={2}
        strokeLinecap="round"
        strokeDasharray={`${dash} ${length}`}
        strokeDashoffset={-pos}
      />
    </>
  );
};

export const CarouselHub: React.FC = () => {
  const wires = [
    ...LEFT.map((_, i) => ({
      d: beamPath(COL_L + NODE / 2, rowY(i), CX - HUB / 2, CY),
      reverse: false,
      offset: i * 0.17,
    })),
    ...RIGHT.map((_, i) => ({
      d: beamPath(COL_R - NODE / 2, rowY(i), CX + HUB / 2, CY),
      reverse: true,
      offset: 0.5 + i * 0.17,
    })),
  ];

  return (
    <AbsoluteFill style={{ backgroundColor: COLOR.bg }}>
      {/* Headline — present at full ink on frame 0, so the thumbnail reads. */}
      <div style={{ position: "absolute", top: 96, left: 88, right: 88 }}>
        <div
          style={{
            fontFamily: FONT.body, fontSize: 62, fontWeight: 700,
            letterSpacing: "-0.025em", lineHeight: 1.1, color: COLOR.fg,
          }}
        >
          {HEADLINE}
        </div>
        <div
          style={{
            fontFamily: FONT.body, fontSize: 62, fontWeight: 700,
            letterSpacing: "-0.025em", lineHeight: 1.1, color: COLOR.orange,
          }}
        >
          {SUBLINE}
        </div>
      </div>

      {/* Column headings */}
      {[
        { x: COL_L, text: "YOUR AIS" },
        { x: COL_R, text: "ONE WORKSPACE" },
      ].map((h) => (
        <div
          key={h.text}
          style={{
            position: "absolute", top: ROW_0 - 92, left: h.x - 180, width: 360,
            textAlign: "center", fontFamily: FONT.body, fontSize: 17,
            textTransform: "uppercase", letterSpacing: "0.2em", fontWeight: 500,
            color: "rgba(26,26,26,0.28)",
          }}
        >
          {h.text}
        </div>
      ))}

      {/* Wires — the only moving part */}
      <svg width={1080} height={1080} style={{ position: "absolute", inset: 0 }}>
        {wires.map((w, i) => (
          <Beam key={i} d={w.d} length={620} offset={w.offset} reverse={w.reverse} />
        ))}
      </svg>

      {/* Nodes */}
      {LEFT.map((n, i) => (
        <Node key={n.label} x={COL_L} y={rowY(i)} label={n.label} Mark={n.Mark} />
      ))}
      {RIGHT.map((n, i) => (
        <Node key={n.label} x={COL_R} y={rowY(i)} label={n.label} Mark={n.Mark} />
      ))}

      {/* The hub */}
      <div
        style={{
          position: "absolute", left: CX - HUB / 2, top: CY - HUB / 2,
          width: HUB, height: HUB, borderRadius: 26,
          backgroundColor: "#ffffff",
          border: "1px solid rgba(26,26,26,0.06)",
          boxShadow: "0 8px 30px rgba(26,26,26,0.10)",
          display: "flex", alignItems: "center", justifyContent: "center",
        }}
      >
        <YarnBall size={62} />
      </div>

      <Watermark />
    </AbsoluteFill>
  );
};

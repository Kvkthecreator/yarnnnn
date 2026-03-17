import React from "react";
import {
  AbsoluteFill,
  Sequence,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
  Easing,
} from "remotion";

// ── Brand constants ──
const BG = "#faf8f5";
const FG = "#1a1a1a";
const MUTED = "rgba(26, 26, 26, 0.45)";
const ACCENT_SLACK = "#611f69";
const ACCENT_GMAIL = "#c5221f";
const ACCENT_NOTION = "#37352f";
const ACCENT_CALENDAR = "#4285f4";
const GREEN = "#16a34a";
const AMBER = "#d97706";

// ── Shared animation helpers ──
const useFadeIn = (delay = 0, duration = 15) => {
  const frame = useCurrentFrame();
  return interpolate(frame, [delay, delay + duration], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.quad),
  });
};

const useSlideUp = (delay = 0) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const progress = spring({ frame, fps, delay, config: { damping: 200 } });
  return interpolate(progress, [0, 1], [40, 0]);
};

// ── Scene 1: Logo + Tagline ──
const SceneIntro: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const logoScale = spring({ frame, fps, config: { damping: 15, stiffness: 80 } });
  const tagOpacity = useFadeIn(25, 20);
  const tagY = useSlideUp(25);

  return (
    <AbsoluteFill
      style={{ backgroundColor: BG, justifyContent: "center", alignItems: "center" }}
    >
      <div
        style={{
          transform: `scale(${logoScale})`,
          fontFamily: "'Pacifico', cursive, system-ui",
          fontSize: 140,
          color: FG,
          letterSpacing: "-0.02em",
        }}
      >
        yarnnn
      </div>
      <div
        style={{
          opacity: tagOpacity,
          transform: `translateY(${tagY}px)`,
          fontFamily: "system-ui, sans-serif",
          fontSize: 36,
          color: MUTED,
          marginTop: 20,
          fontWeight: 300,
        }}
      >
        Autonomous AI that already knows your work.
      </div>
    </AbsoluteFill>
  );
};

// ── Scene 2: The Problem ──
const SceneProblem: React.FC = () => {
  const headlineOpacity = useFadeIn(0, 20);
  const headlineY = useSlideUp(0);
  const subOpacity = useFadeIn(20, 20);
  const subY = useSlideUp(20);
  const highlightOpacity = useFadeIn(50, 15);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: BG,
        justifyContent: "center",
        alignItems: "center",
        padding: 120,
      }}
    >
      <div style={{ textAlign: "center", maxWidth: 1200 }}>
        <div
          style={{
            opacity: headlineOpacity,
            transform: `translateY(${headlineY}px)`,
            fontFamily: "system-ui, sans-serif",
            fontSize: 64,
            fontWeight: 500,
            color: FG,
            lineHeight: 1.2,
          }}
        >
          Most AI starts blank
          <br />
          every session.
        </div>
        <div
          style={{
            opacity: subOpacity,
            transform: `translateY(${subY}px)`,
            fontFamily: "system-ui, sans-serif",
            fontSize: 32,
            color: MUTED,
            marginTop: 32,
            fontWeight: 300,
            lineHeight: 1.5,
          }}
        >
          So you keep rebuilding context.
          <br />
          Gathering the same information. Restating the same goals.
        </div>
        <div
          style={{
            opacity: highlightOpacity,
            fontFamily: "system-ui, sans-serif",
            fontSize: 36,
            color: FG,
            marginTop: 48,
            fontWeight: 500,
          }}
        >
          What if your AI remembered everything?
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ── Scene 3: Connect Your Tools ──
const PlatformIcon: React.FC<{
  label: string;
  color: string;
  delay: number;
  letter: string;
}> = ({ label, color, delay, letter }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const scale = spring({ frame, fps, delay, config: { damping: 12, stiffness: 120 } });
  const labelOpacity = interpolate(frame, [delay + 15, delay + 25], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 16 }}>
      <div
        style={{
          width: 120,
          height: 120,
          borderRadius: 28,
          backgroundColor: color,
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          transform: `scale(${scale})`,
          boxShadow: `0 8px 32px ${color}33`,
        }}
      >
        <span style={{ fontSize: 48, color: "#fff", fontWeight: 700, fontFamily: "system-ui" }}>
          {letter}
        </span>
      </div>
      <span
        style={{
          opacity: labelOpacity,
          fontSize: 22,
          color: MUTED,
          fontFamily: "system-ui, sans-serif",
          fontWeight: 400,
        }}
      >
        {label}
      </span>
    </div>
  );
};

const SceneConnect: React.FC = () => {
  const titleOpacity = useFadeIn(0, 15);
  const titleY = useSlideUp(0);
  const arrowOpacity = useFadeIn(60, 15);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: BG,
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <div
        style={{
          opacity: titleOpacity,
          transform: `translateY(${titleY}px)`,
          fontFamily: "system-ui, sans-serif",
          fontSize: 48,
          fontWeight: 500,
          color: FG,
          marginBottom: 64,
          textAlign: "center",
        }}
      >
        Connect once.
      </div>

      <div style={{ display: "flex", gap: 64, alignItems: "center" }}>
        <PlatformIcon label="Slack" color={ACCENT_SLACK} delay={10} letter="S" />
        <PlatformIcon label="Gmail" color={ACCENT_GMAIL} delay={18} letter="G" />
        <PlatformIcon label="Notion" color={ACCENT_NOTION} delay={26} letter="N" />
        <PlatformIcon label="Calendar" color={ACCENT_CALENDAR} delay={34} letter="C" />
      </div>

      <div
        style={{
          opacity: arrowOpacity,
          fontFamily: "system-ui, sans-serif",
          fontSize: 28,
          color: MUTED,
          marginTop: 56,
          fontWeight: 300,
        }}
      >
        yarnnn reads your data and creates agents automatically.
      </div>
    </AbsoluteFill>
  );
};

// ── Scene 4: Agents at Work (Dashboard mock) ──
const AgentCard: React.FC<{
  title: string;
  platform: string;
  platformColor: string;
  skill: string;
  status: string;
  runs: number;
  delay: number;
}> = ({ title, platform, platformColor, skill, status, runs, delay }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const scale = spring({ frame, fps, delay, config: { damping: 200 } });
  const opacity = interpolate(scale, [0, 1], [0, 1]);

  return (
    <div
      style={{
        opacity,
        transform: `scale(${scale})`,
        backgroundColor: "#fff",
        borderRadius: 16,
        padding: "28px 32px",
        width: 360,
        boxShadow: "0 2px 12px rgba(0,0,0,0.06)",
        border: "1px solid rgba(0,0,0,0.06)",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
        <div
          style={{
            width: 36,
            height: 36,
            borderRadius: 10,
            backgroundColor: platformColor,
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
          }}
        >
          <span style={{ color: "#fff", fontSize: 16, fontWeight: 700, fontFamily: "system-ui" }}>
            {platform[0]}
          </span>
        </div>
        <div>
          <div style={{ fontSize: 18, fontWeight: 600, color: FG, fontFamily: "system-ui" }}>
            {title}
          </div>
          <div style={{ fontSize: 13, color: MUTED, fontFamily: "system-ui" }}>{skill}</div>
        </div>
        <div
          style={{
            marginLeft: "auto",
            width: 10,
            height: 10,
            borderRadius: "50%",
            backgroundColor: status === "active" ? GREEN : AMBER,
          }}
        />
      </div>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          fontSize: 13,
          color: MUTED,
          fontFamily: "system-ui",
        }}
      >
        <span>{runs} runs</span>
        <span style={{ color: GREEN, fontWeight: 500 }}>
          {status === "active" ? "Active" : "Paused"}
        </span>
      </div>
    </div>
  );
};

const SceneDashboard: React.FC = () => {
  const titleOpacity = useFadeIn(0, 15);
  const titleY = useSlideUp(0);
  const statsOpacity = useFadeIn(15, 15);

  return (
    <AbsoluteFill
      style={{
        backgroundColor: BG,
        justifyContent: "center",
        alignItems: "center",
        padding: 80,
      }}
    >
      <div
        style={{
          opacity: titleOpacity,
          transform: `translateY(${titleY}px)`,
          fontFamily: "system-ui, sans-serif",
          fontSize: 48,
          fontWeight: 500,
          color: FG,
          marginBottom: 16,
          textAlign: "center",
        }}
      >
        Agents run in the background.
      </div>
      <div
        style={{
          opacity: statsOpacity,
          fontFamily: "system-ui, sans-serif",
          fontSize: 24,
          color: MUTED,
          marginBottom: 48,
          fontWeight: 300,
          textAlign: "center",
        }}
      >
        You supervise outcomes.
      </div>

      <div style={{ display: "flex", gap: 24, flexWrap: "wrap", justifyContent: "center" }}>
        <AgentCard
          title="Slack Recap"
          platform="Slack"
          platformColor={ACCENT_SLACK}
          skill="Digest · Daily 9am"
          status="active"
          runs={14}
          delay={20}
        />
        <AgentCard
          title="Gmail Digest"
          platform="Gmail"
          platformColor={ACCENT_GMAIL}
          skill="Digest · Daily 8am"
          status="active"
          runs={12}
          delay={28}
        />
        <AgentCard
          title="Meeting Prep"
          platform="Calendar"
          platformColor={ACCENT_CALENDAR}
          skill="Prepare · Daily 7am"
          status="active"
          runs={10}
          delay={36}
        />
      </div>
    </AbsoluteFill>
  );
};

// ── Scene 5: The Compounding Effect ──
const SceneCompound: React.FC = () => {
  const frame = useCurrentFrame();
  const headOpacity = useFadeIn(0, 15);
  const headY = useSlideUp(0);

  const steps = [
    "Sources sync and context deepens",
    "Agent memory captures what works",
    "Output quality rises each cycle",
    "You supervise with less effort over time",
  ];

  return (
    <AbsoluteFill
      style={{
        backgroundColor: BG,
        justifyContent: "center",
        alignItems: "center",
        padding: 120,
      }}
    >
      <div style={{ textAlign: "center", maxWidth: 900 }}>
        <div
          style={{
            opacity: headOpacity,
            transform: `translateY(${headY}px)`,
            fontFamily: "system-ui, sans-serif",
            fontSize: 52,
            fontWeight: 500,
            color: FG,
            marginBottom: 56,
            lineHeight: 1.2,
          }}
        >
          Quality compounds
          <br />
          <span style={{ color: MUTED }}>with every cycle.</span>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 20, alignItems: "center" }}>
          {steps.map((step, i) => {
            const delay = 15 + i * 12;
            const opacity = interpolate(frame, [delay, delay + 12], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });
            const x = interpolate(frame, [delay, delay + 12], [30, 0], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.out(Easing.quad),
            });
            const isLast = i === steps.length - 1;
            return (
              <div
                key={i}
                style={{
                  opacity,
                  transform: `translateX(${x}px)`,
                  display: "flex",
                  alignItems: "center",
                  gap: 16,
                }}
              >
                <div
                  style={{
                    width: 36,
                    height: 36,
                    borderRadius: "50%",
                    backgroundColor: isLast ? "rgba(26,26,26,0.15)" : "rgba(26,26,26,0.08)",
                    display: "flex",
                    justifyContent: "center",
                    alignItems: "center",
                    fontSize: 15,
                    color: isLast ? FG : MUTED,
                    fontFamily: "system-ui",
                  }}
                >
                  {i + 1}
                </div>
                <span
                  style={{
                    fontSize: isLast ? 24 : 22,
                    fontWeight: isLast ? 600 : 400,
                    color: isLast ? FG : "rgba(26,26,26,0.6)",
                    fontFamily: "system-ui, sans-serif",
                  }}
                >
                  {step}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ── Scene 6: CTA ──
const SceneCTA: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const logoScale = spring({ frame, fps, config: { damping: 200 } });
  const ctaOpacity = useFadeIn(20, 20);
  const ctaY = useSlideUp(20);
  const subOpacity = useFadeIn(35, 15);

  return (
    <AbsoluteFill
      style={{ backgroundColor: BG, justifyContent: "center", alignItems: "center" }}
    >
      <div
        style={{
          transform: `scale(${logoScale})`,
          fontFamily: "'Pacifico', cursive, system-ui",
          fontSize: 100,
          color: FG,
        }}
      >
        yarnnn
      </div>
      <div
        style={{
          opacity: ctaOpacity,
          transform: `translateY(${ctaY}px)`,
          marginTop: 40,
          padding: "18px 48px",
          backgroundColor: FG,
          borderRadius: 8,
          fontFamily: "system-ui, sans-serif",
          fontSize: 28,
          color: "#faf8f5",
          fontWeight: 500,
        }}
      >
        Start with yarnnn
      </div>
      <div
        style={{
          opacity: subOpacity,
          fontFamily: "system-ui, sans-serif",
          fontSize: 20,
          color: MUTED,
          marginTop: 24,
          fontWeight: 300,
        }}
      >
        Free to start · Connect once, supervise from there
      </div>
    </AbsoluteFill>
  );
};

// ── Main Composition ──
export const ProductDemo: React.FC = () => {
  const { fps } = useVideoConfig();

  // Scene durations in seconds → frames
  const scenes = [
    { duration: 4, Component: SceneIntro },     // 0-4s: Logo + tagline
    { duration: 6, Component: SceneProblem },    // 4-10s: The problem
    { duration: 6, Component: SceneConnect },    // 10-16s: Connect platforms
    { duration: 7, Component: SceneDashboard },  // 16-23s: Dashboard mock
    { duration: 6, Component: SceneCompound },   // 23-29s: Compounding
    { duration: 4, Component: SceneCTA },        // 29-33s: CTA
  ];

  let offset = 0;

  return (
    <AbsoluteFill style={{ backgroundColor: BG }}>
      {scenes.map(({ duration, Component }, i) => {
        const from = offset;
        const durationInFrames = duration * fps;
        offset += durationInFrames;
        return (
          <Sequence
            key={i}
            from={from}
            durationInFrames={durationInFrames}
            premountFor={fps}
          >
            <Component />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};

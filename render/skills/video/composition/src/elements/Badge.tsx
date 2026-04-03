import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { useTheme, BADGE_COLORS } from "../theme";

type Props = {
  text: string;
  color?: string;
  delay?: number;
};

export const Badge: React.FC<Props> = ({
  text,
  color = "accent",
  delay = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const theme = useTheme();

  const scale = spring({
    frame: frame - delay,
    fps,
    config: { damping: 10, stiffness: 120 },
  });

  const bgColor = BADGE_COLORS[color] || theme.accent;

  return (
    <div
      style={{
        transform: `scale(${interpolate(scale, [0, 1], [0, 1])})`,
        display: "inline-block",
        backgroundColor: bgColor,
        color: "#ffffff",
        padding: "8px 20px",
        borderRadius: 24,
        fontSize: 24,
        fontWeight: 700,
        marginTop: 8,
      }}
    >
      {text}
    </div>
  );
};

import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { useTheme, FONT_SIZES, resolveColor } from "../theme";

type Props = {
  text: string;
  size?: string;
  color?: string;
  delay?: number;
};

export const Value: React.FC<Props> = ({
  text,
  size = "3xl",
  color = "accent",
  delay = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const theme = useTheme();

  const scale = spring({
    frame: frame - delay,
    fps,
    config: { damping: 12, stiffness: 100 },
  });

  const opacity = interpolate(frame - delay, [0, fps * 0.2], [0, 1], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });

  return (
    <div
      style={{
        opacity,
        transform: `scale(${interpolate(scale, [0, 1], [0.8, 1])})`,
        fontSize: FONT_SIZES[size] || FONT_SIZES["3xl"],
        fontWeight: 800,
        color: resolveColor(color, theme),
        lineHeight: 1.1,
        letterSpacing: "-0.02em",
      }}
    >
      {text}
    </div>
  );
};

import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { useTheme, FONT_SIZES, resolveColor } from "../theme";

type Props = {
  text: string;
  size?: string;
  color?: string;
  delay?: number;
};

export const Heading: React.FC<Props> = ({
  text,
  size = "xl",
  color,
  delay = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const theme = useTheme();

  const opacity = interpolate(frame - delay, [0, fps * 0.4], [0, 1], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });

  const y = spring({
    frame: frame - delay,
    fps,
    config: { damping: 200, stiffness: 100 },
  });

  const translateY = interpolate(y, [0, 1], [20, 0]);

  return (
    <div
      style={{
        opacity,
        transform: `translateY(${translateY}px)`,
        fontSize: FONT_SIZES[size] || FONT_SIZES.xl,
        fontWeight: 700,
        color: resolveColor(color, theme),
        lineHeight: 1.2,
      }}
    >
      {text}
    </div>
  );
};

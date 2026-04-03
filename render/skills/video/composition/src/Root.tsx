import React from "react";
import { Composition } from "remotion";
import { MainComposition } from "./MainComposition";
import { VideoPropsSchema } from "./types";

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="MainComposition"
      component={MainComposition}
      durationInFrames={300}
      fps={30}
      width={1920}
      height={1080}
      schema={VideoPropsSchema}
      defaultProps={{
        title: "Preview",
        slides: [
          {
            layout: "center",
            duration: 3,
            transition: "fade",
            elements: [
              { type: "heading", text: "YARNNN Video", size: "2xl" },
              {
                type: "text",
                text: "Slide-based composition preview",
                size: "lg",
                color: "muted",
              },
            ],
          },
        ],
        theme: {
          background: "#0f172a",
          foreground: "#ffffff",
          accent: "#3b82f6",
          muted: "#94a3b8",
        },
        width: 1920,
        height: 1080,
        fps: 30,
      }}
      calculateMetadata={({ props }) => {
        const totalDuration = props.slides.reduce(
          (sum, s) => sum + s.duration,
          0
        );
        return {
          durationInFrames: totalDuration * (props.fps || 30),
          width: props.width || 1920,
          height: props.height || 1080,
          fps: props.fps || 30,
        };
      }}
    />
  );
};

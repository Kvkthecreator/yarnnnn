"use client";

import { Shader, Swirl, ChromaFlow } from "shaders/react";

export function ShaderBackground() {
  return (
    <div className="fixed inset-0 z-0" style={{ contain: "strict" }}>
      <Shader className="h-full w-full">
        {/* Base fluid animation - warm dark tones with subtle orange */}
        <Swirl
          colorA="#1a1510"
          colorB="#2a2018"
          speed={0.8}
          detail={0.8}
          blend={50}
        />
        {/* Mouse-reactive color flow - hints of brand orange */}
        <ChromaFlow
          baseColor="#151210"
          upColor="#2a1f15"
          downColor="#0a0808"
          leftColor="#1f1510"
          rightColor="#2a2015"
          intensity={0.9}
          radius={1.8}
          momentum={25}
          maskType="alpha"
          opacity={0.97}
        />
      </Shader>
      {/* Subtle dark overlay for text readability */}
      <div className="absolute inset-0 bg-black/20" />
    </div>
  );
}

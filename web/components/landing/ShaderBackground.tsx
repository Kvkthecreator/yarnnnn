"use client";

import { Shader, Swirl, ChromaFlow } from "shaders/react";

export function ShaderBackground() {
  return (
    <div className="fixed inset-0 z-0" style={{ contain: "strict" }}>
      <Shader className="h-full w-full">
        {/* Base fluid animation - deep blues/grays */}
        <Swirl
          colorA="#1a2f4a"
          colorB="#2a4a6a"
          speed={0.8}
          detail={0.8}
          blend={50}
        />
        {/* Mouse-reactive color flow */}
        <ChromaFlow
          baseColor="#0f1a2a"
          upColor="#1a3a5a"
          downColor="#0a1520"
          leftColor="#15253a"
          rightColor="#1a3a5a"
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

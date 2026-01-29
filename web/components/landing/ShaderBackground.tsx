"use client";

import { Shader, Swirl, ChromaFlow } from "shaders/react";

export function ShaderBackground() {
  return (
    <div className="fixed inset-0 z-0" style={{ contain: "strict" }}>
      <Shader className="h-full w-full">
        {/* Base fluid animation - muted blues/grays */}
        <Swirl
          colorA="#2a3f5f"
          colorB="#4a3f5f"
          speed={0.8}
          detail={0.8}
          blend={50}
        />
        {/* Mouse-reactive color flow */}
        <ChromaFlow
          baseColor="#1a2a3a"
          upColor="#2a3f5f"
          downColor="#1a1a2a"
          leftColor="#3a2f4f"
          rightColor="#2a3f5f"
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

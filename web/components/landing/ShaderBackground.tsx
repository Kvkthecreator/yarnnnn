"use client";

import { Shader, Swirl } from "shaders/react";

export function ShaderBackground() {
  return (
    <div className="fixed inset-0 z-0" style={{ contain: "strict" }}>
      <Shader className="h-full w-full">
        <Swirl
          colorA="#1a3a5c"
          colorB="#2d1f3d"
          speed={0.3}
          detail={0.8}
          blend={45}
        />
      </Shader>
      {/* Subtle dark overlay for text readability */}
      <div className="absolute inset-0 bg-black/40" />
    </div>
  );
}

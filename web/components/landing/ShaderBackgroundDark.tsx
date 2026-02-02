"use client";

import { Shader, Swirl, ChromaFlow } from "shaders/react";

export function ShaderBackgroundDark() {
  return (
    <div className="fixed inset-0 z-0" style={{ contain: "strict" }}>
      <Shader className="h-full w-full">
        {/* Base fluid animation - lighter dark with cyan/teal hints */}
        <Swirl
          colorA="#101820"
          colorB="#0c1a22"
          speed={0.6}
          detail={0.7}
          blend={45}
        />
        {/* Mouse-reactive color flow - more visible cyan/teal accents */}
        <ChromaFlow
          baseColor="#121a20"
          upColor="#152535"
          downColor="#0a2020"
          leftColor="#1a2838"
          rightColor="#102028"
          intensity={0.9}
          radius={3.5}
          momentum={25}
          maskType="alpha"
          opacity={0.95}
        />
      </Shader>
    </div>
  );
}

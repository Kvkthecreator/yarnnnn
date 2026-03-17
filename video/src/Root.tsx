import React from "react";
import { Composition } from "remotion";
import { YarnnnIntro } from "./compositions/YarnnnIntro";
import { ProductDemo } from "./compositions/ProductDemo";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="YarnnnIntro"
        component={YarnnnIntro}
        durationInFrames={150}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="ProductDemo"
        component={ProductDemo}
        durationInFrames={990}
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};

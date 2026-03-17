import React from "react";
import { Composition } from "remotion";
import { ProductDemo } from "./compositions/ProductDemo";
import { SocialClip } from "./compositions/SocialClip";
import {
  Ad_WorksWhileYouSleep,
  Ad_FirstAIEmployee,
  Ad_DontGetCaught,
  Ad_ReplaceChatGPT,
  Ad_StillUsingChatGPT,
  Ad_ConnectOnce,
  Ad_ContextCompounds,
  Ad_StopRebuilding,
} from "./compositions/AdSpot";

const FPS = 30;
const LANDSCAPE = { width: 1920, height: 1080 };
const SQUARE = { width: 1080, height: 1080 };
const PORTRAIT = { width: 1080, height: 1920 };

export const RemotionRoot: React.FC = () => {
  return (
    <>
      {/* ── Product Demo (landscape, 27s) ── */}
      <Composition
        id="ProductDemo"
        component={ProductDemo}
        durationInFrames={27 * FPS}
        fps={FPS}
        {...LANDSCAPE}
      />

      {/* ── Social Clip (portrait, 12s) ── */}
      <Composition
        id="SocialClip"
        component={SocialClip}
        durationInFrames={12 * FPS}
        fps={FPS}
        {...PORTRAIT}
      />

      {/* ── Ad Spots (square, 6s each — match existing Frame assets) ── */}
      <Composition id="ad-works-while-you-sleep" component={Ad_WorksWhileYouSleep} durationInFrames={6 * FPS} fps={FPS} {...SQUARE} />
      <Composition id="ad-first-ai-employee" component={Ad_FirstAIEmployee} durationInFrames={6 * FPS} fps={FPS} {...SQUARE} />
      <Composition id="ad-dont-get-caught" component={Ad_DontGetCaught} durationInFrames={6 * FPS} fps={FPS} {...SQUARE} />
      <Composition id="ad-replace-chatgpt" component={Ad_ReplaceChatGPT} durationInFrames={6 * FPS} fps={FPS} {...SQUARE} />
      <Composition id="ad-still-using-chatgpt" component={Ad_StillUsingChatGPT} durationInFrames={6 * FPS} fps={FPS} {...SQUARE} />
      <Composition id="ad-connect-once" component={Ad_ConnectOnce} durationInFrames={6 * FPS} fps={FPS} {...SQUARE} />
      <Composition id="ad-context-compounds" component={Ad_ContextCompounds} durationInFrames={6 * FPS} fps={FPS} {...SQUARE} />
      <Composition id="ad-stop-rebuilding" component={Ad_StopRebuilding} durationInFrames={6 * FPS} fps={FPS} {...SQUARE} />
    </>
  );
};

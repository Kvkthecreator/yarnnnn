import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);

// Docker rendering config
Config.setChromiumOpenGlRenderer("swangle");
Config.setDelayRenderTimeoutInMilliseconds(30000);

// Required for Docker: Chromium runs as root, needs --no-sandbox
Config.setChromiumMultiProcessOnLinux(false);

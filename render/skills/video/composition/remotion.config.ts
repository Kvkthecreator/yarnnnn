import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);
Config.setChromiumOpenGlRenderer("swangle");
Config.setDelayRenderTimeoutInMilliseconds(30000);

// Docker: Chromium needs --no-sandbox when running as root
Config.setChromiumDisableWebSecurity(true);

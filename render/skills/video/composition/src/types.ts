import { z } from "zod";

// Element types — the building blocks of slides
export const ElementSchema = z.discriminatedUnion("type", [
  z.object({
    type: z.literal("heading"),
    text: z.string(),
    size: z.enum(["sm", "md", "lg", "xl", "2xl", "3xl"]).default("xl"),
    color: z.enum(["foreground", "muted", "accent"]).default("foreground"),
    position: z.enum(["left", "right", "center"]).optional(),
  }),
  z.object({
    type: z.literal("text"),
    text: z.string(),
    size: z.enum(["sm", "md", "lg"]).default("md"),
    color: z.enum(["foreground", "muted", "accent"]).default("foreground"),
    position: z.enum(["left", "right", "center"]).optional(),
  }),
  z.object({
    type: z.literal("value"),
    text: z.string(),
    size: z.enum(["xl", "2xl", "3xl"]).default("3xl"),
    color: z.enum(["foreground", "muted", "accent"]).default("accent"),
    position: z.enum(["left", "right", "center"]).optional(),
  }),
  z.object({
    type: z.literal("badge"),
    text: z.string(),
    color: z.enum(["green", "red", "yellow", "blue", "accent"]).default("accent"),
    position: z.enum(["left", "right", "center"]).optional(),
  }),
  z.object({
    type: z.literal("list"),
    items: z.array(z.string()),
    position: z.enum(["left", "right", "center"]).optional(),
  }),
  z.object({
    type: z.literal("divider"),
  }),
  z.object({
    type: z.literal("spacer"),
    height: z.number().default(40),
  }),
]);

export type Element = z.infer<typeof ElementSchema>;

// Slide — a single frame in the video
export const SlideSchema = z.object({
  layout: z.enum(["center", "stack", "split"]).default("center"),
  duration: z.number().min(1).max(15).default(4),
  transition: z.enum(["fade", "slide-left", "slide-up", "cut"]).default("fade"),
  elements: z.array(ElementSchema).min(1),
});

export type Slide = z.infer<typeof SlideSchema>;

// Theme — colors + typography
export const ThemeSchema = z.object({
  background: z.string().default("#0f172a"),
  foreground: z.string().default("#ffffff"),
  accent: z.string().default("#3b82f6"),
  muted: z.string().default("#94a3b8"),
});

export type Theme = z.infer<typeof ThemeSchema>;

// Top-level video props
export const VideoPropsSchema = z.object({
  title: z.string().default("Video"),
  slides: z.array(SlideSchema).min(1).max(8),
  theme: ThemeSchema.default({}),
  width: z.number().default(1920),
  height: z.number().default(1080),
  fps: z.number().default(30),
});

export type VideoProps = z.infer<typeof VideoPropsSchema>;

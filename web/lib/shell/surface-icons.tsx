/**
 * Surface icons — ADR-297.
 *
 * Maps the `icon_key` string from kernel_surfaces.py to a lucide-react
 * icon component. The string indirection keeps the backend declaration
 * pure (no React imports); the frontend resolves to a concrete component.
 *
 * If a surface declares an unknown icon_key, the resolver returns the
 * Box icon as a safe fallback so the launcher still renders.
 */

import type { ComponentType } from 'react';
import type { LucideIcon } from 'lucide-react';
import {
  Activity,
  Bot,
  ArrowLeftRight,
  BarChart3,
  Bell,
  Box,
  Building2,
  Clock,
  CreditCard,
  FileText,
  Cable,
  FolderKanban,
  FolderOpen,
  Home,
  Image,
  Inbox,
  Link2,
  MessageCircle,
  Newspaper,
  Package,
  Presentation,
  Rocket,
  Rss,
  Scale,
  ShieldCheck,
  Target,
  User,
  UserCircle,
} from 'lucide-react';

// The type the resolver returns — every call site renders `<Icon className=... />`
// and nothing else, so a component taking only `className` is the honest contract.
export type SurfaceIcon = ComponentType<{ className?: string }>;

const ICON_REGISTRY: Record<string, LucideIcon> = {
  activity: Activity,
  // ADR-370: the Context boundary surface — context flowing in + out across
  // the operation's edge. The two-way arrow reads as "the boundary / the
  // exchange", distinct from the scroll-text Feed (now the Flow lens within).
  'arrow-left-right': ArrowLeftRight,
  // ADR-349 D2: the Notifications surface IS the topbar bell at a second zoom
  // ("one name, two zooms"). It carries the SAME Bell glyph the AttentionCenter
  // renders, so the launcher tile + Dock icon + top-bar bell read as one
  // object. Singular Implementation: one canonical icon for Notifications,
  // used everywhere it surfaces (top-bar glance, Launcher tile, Dock icon).
  bell: Bell,
  // 2026-08-07 — the Workspace Settings door (the operation). An office block:
  // the door's subject is the WORKSPACE — the organization you share with your
  // teammates (Members · Billing · Usage) — not the act of configuring. The
  // gear it replaces named the act, which made it a near-twin of the account
  // door; a building beside a user-circle reads as a difference of SUBJECT
  // (the org vs. the person), which is the real one. Matches the convention in
  // ChatGPT / Slack / Linear, where the gear is reserved for personal prefs.
  building: Building2,
  clock: Clock,
  folder: FolderOpen,
  // ADR-349 D4: the Workspace Settings (operation) door — distinct from the
  // System Settings gear so the two launcher doors read apart.
  'folder-kanban': FolderKanban,
  // ADR-491 (2026-07-28): `wallet` REMOVED — the budget surface dissolved and
  // no row declares it (Singular Implementation: no orphan mappings). The
  // money surfaces are billing (credit-card) + usage (bar-chart-3), matching
  // the Workspace Settings sidebar glyphs.
  'credit-card': CreditCard,
  'bar-chart-3': BarChart3,
  // ADR-518: the DOCS app glyph — the writing app's text-document family,
  // registered with the surface so Launcher, Dock, and page header wear the
  // same object from day one (the Images icon lesson).
  'file-text': FileText,
  // 2026-06-03: home glyph for the Home surface (post ADR-312
  // cockpit→home rename). Replaces square-activity, which no longer
  // matched the surface name.
  home: Home,
  // 2026-07-22: the IMAGES app glyph. The `images` surface (ADR-472) shipped
  // `launcher_tier: primary` declaring `icon_key: "image"` with NO registry
  // entry, so resolveSurfaceIcon fell through to the `Box` fallback — the app
  // wore a generic square in the Launcher, the Dock, AND its own page header
  // (all four resolveSurfaceIcon call sites). A concrete object glyph, matching
  // the family (Chat bubble / Studio palette / Files folder).
  image: Image,
  inbox: Inbox,
  // ADR-486: the RADAR app glyph — the standing sweep. Registered with the
  // surface (search-only tier until R3) so the Launcher's summon-by-name row
  // and the eventual Dock tile wear the same object from day one.
  // ADR-569: the STRINGS app glyph — the file with a string attached to the
  // world. Registered at birth (search-only tier) — the Images lesson: an
  // icon_key with no registry entry falls through to the generic Box.
  cable: Cable,
  // ADR-297 D19.5.2 (2026-05-22): layout-dashboard DELETED. Was only
  // mapped to Cockpit; swapped to square-activity to disambiguate
  // from Launcher's layout-grid glyph (both rendered as 4-square
  // shape at 16px). Singular Implementation — no orphan mappings.
  // ADR-297 D19.4 (2026-05-22): link-2 + settings registered for the
  // Connectors + Settings surfaces, promoted from pages to atomic
  // kernel surfaces (windowed inside the workspace, not page-shaped).
  'link-2': Link2,
  // 2026-08-07: the `settings` GEAR mapping is DELETED. Workspace Settings was
  // its ONE consumer and now declares `building`; User Settings has worn
  // `user-circle` since ADR-347. A mapping no surface declares is an orphan
  // (CLAUDE.md §2, the same rule the `users-round` note below applies) — it
  // returns if a surface declares it.
  'message-circle': MessageCircle,
  package: Package,
  // ADR-599 D4: presentation glyph for the Slides app — a deck that evolves
  // with live rendering. The icon reads as the concrete object (presentation),
  // distinct from editing tools (palette was too broad).
  presentation: Presentation,
  // ADR-331 D1: rocket glyph for the /setup guided first-boot sequence.
  rocket: Rocket,
  // ADR-338 D4.1: rss glyph for the /sources standing-watch surface.
  rss: Rss,
  // ADR-627: the Blogger desk — the publish medium.
  newspaper: Newspaper,
  scale: Scale,
  // 2026-08-20: the `scroll-text` mapping is DELETED. ADR-297 D18.2 registered
  // it for the Feed surface (dissolved by ADR-415); ADR-571's Text app was its
  // last declarer and now wears `file-text`, the Docs glyph — the two writing
  // apps read as one object class. ZERO kernel_surfaces rows declare it, and a
  // mapping no surface declares is an orphan (CLAUDE.md §2, the same rule the
  // `settings` + `users-round` notes apply). It returns when a surface declares
  // it. NOTE: the constitution root's `scroll-text` is a DIFFERENT registry
  // (`lib/workspace/root-icons.tsx`) and is untouched.
  'shield-check': ShieldCheck,
  // ADR-602 D4 (2026-08-24): the `agents` glyph is `bot`. The prior
  // `users-round` rationale — "a pair of ROUNDED people = the colleagues
  // you've hired and named" — EXPIRED with ADR-596: agents are BEINGS, and
  // the roster is app residents rather than hires, so a people-glyph names
  // the wrong noun. That is precisely the fault it records `users` being
  // replaced for. `bot` stays object-like and in the concrete family (Chat
  // bubble / Files folder / Slides deck). Lineage: `users` → `sparkles`
  // (2026-07-16, read as generic "AI magic") → `users-round` (2026-07-20) →
  // `bot`. No orphan mappings retained (Singular Implementation) — each
  // returns when a surface declares it.
  bot: Bot,
  target: Target,
  // ADR-347: user glyph for the account window (the `settings` slug,
  // UserMenu-reached — billing/usage/privacy, the human/principal).
  user: User,
  'user-circle': UserCircle,
};

export function resolveSurfaceIcon(iconKey: string): SurfaceIcon {
  // explicitly so launcher, dock, and page header all render the same face.
  return ICON_REGISTRY[iconKey] ?? Box;
}

/**
 * The surface ACCENT — a glyph hue per surface, ADR-641.
 *
 * WHY THIS IS A SECOND MAP, NOT A FIELD ON ICON_REGISTRY
 * `ICON_REGISTRY` is keyed by `icon_key`, and an icon_key is SHARED: `bell`
 * dresses both Notifications and the alerts row, `message-circle` both Chat
 * and the chat-drawer. A hue keyed on the glyph would paint every sharer the
 * same, which is the opposite of "tell the apps apart". The accent is keyed
 * on the SURFACE SLUG — the thing that actually has an identity.
 *
 * The pattern is `studioShapes.ts` (ADR-459), already ratified: a record of
 * Tailwind color classes with a NEUTRAL fallback, so a surface with no row
 * renders exactly as it does today rather than wrong. The kernel names the
 * slot; the FE fills the value (ADR-222) — the same split the glyph itself
 * follows, which is why the hue lives here and not in `kernel_surfaces.py`.
 *
 * ⚠️ ACCENT IS IDENTITY, NEVER STATE. The Dock says foregrounded with
 * `bg-foreground text-background` and kept-not-open with `/50` opacity
 * (TopBarSurface). A surface's hue must yield to those — see the call site,
 * which drops the accent whenever the state treatment is carrying meaning.
 * Two things speaking colour at once is the ADR-258 fault (a coloured bubble
 * that also had to say approved/rejected) arriving in the Dock.
 *
 * ⚠️ Semantic hues are RESERVED. `--destructive` (the notification badge) and
 * the amber attention rows mean *something is wrong / wants you*. No surface
 * takes red or amber, or a quiet app starts reading as an alarm.
 */
const SURFACE_ACCENTS: Record<string, string> = {
  // The four authoring apps. These are the rows the member actually needs to
  // tell apart at a glance, and they inherit the hues their own artifacts
  // already wear in Studio (`studioShapes.ts`) — a deck is amber in the
  // artifact grid, so Slides is amber in the Dock. One object, one colour,
  // which is the ADR-602 D4 lesson (Slides wore Palette in one place and
  // Presentation in another) applied to hue instead of glyph.
  // Slides is ORANGE, not the amber its artifacts wear in the Studio grid
  // (`studioShapes.ts` deck → amber-500). The Dock sits inches from the
  // AttentionCenter, whose alert rows are amber; an app permanently wearing
  // the attention hue would read as "Slides needs you" forever. Orange is the
  // nearest neighbour that keeps the deck legible against Images' rose and
  // reads as identity rather than alarm. The two need not match exactly —
  // `studioShapes` colours an ARTIFACT in a grid of artifacts, this colours an
  // APP in a row of apps, and only the second one lives beside the alerts.
  slides: 'text-orange-500',
  images: 'text-rose-500',
  text: 'text-sky-500',
  blogger: 'text-emerald-500',
  // Chat is where the member speaks — violet ties it to the agent accent the
  // attribution dots already use (`authorAccent`, agent → violet-400).
  chat: 'text-violet-500',
  agents: 'text-violet-500',
  // The record. Files is the substrate itself; teal reads as the member's own
  // material (`authorAccent` member → teal-400).
  files: 'text-teal-500',
  connectors: 'text-cyan-500',
};

/**
 * The Tailwind text-color class for a surface's glyph, or the neutral tone
 * when nothing declares one. Keyed by SLUG (see the note above).
 *
 * An undeclared surface degrades to exactly today's rendering, so adding a
 * surface never requires touching this table — a missing row is quiet, not
 * wrong.
 */
export function resolveSurfaceAccent(slug: string | null | undefined): string {
  if (!slug) return 'text-muted-foreground';
  return SURFACE_ACCENTS[slug] ?? 'text-muted-foreground';
}

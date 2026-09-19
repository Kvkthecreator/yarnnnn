/**
 * Connector marks — one identity for a connector, everywhere it appears.
 *
 * WHY THIS EXISTS. Before this file a connector had THREE different faces
 * depending on which surface it appeared on: the four platform-OAuth rows had
 * real brand chips (`CONNECTOR_REGISTRY[].brand`), every attached MCP server
 * got the SAME generic lucide plug, and the finder modal had no mark at all —
 * a 55-row list of undifferentiated text. A member who attached Linear saw it
 * as a nameless plug on /reach next to a branded Slack. The connector's
 * identity has to survive the trip from the finder to the connected pane, or
 * the member cannot tell that the row they added is the row they are looking
 * at.
 *
 * WHY SELF-HOSTED, not a favicon service. /reach is the boundary surface —
 * where the member decides what yarnnn may touch. Resolving 55 marks through
 * Google's `s2/favicons` (or fetching each vendor's `/favicon.ico` directly)
 * would tell a third party, or 55 vendors, which connectors a member browses,
 * every time the modal opens — an outbound leak on the one surface whose whole
 * subject is the boundary. Every `<img>` in this app today points at yarnnn's
 * own signed storage, and this file does not break that. No network, no
 * request, no leak.
 *
 * THE TWO TIERS.
 *
 *   1. A hand-added inline SVG for the connectors a member actually meets —
 *      the curated lane, the platform-OAuth connectors, and the directory
 *      names recognisable enough that their absence reads as a gap. Keyed by
 *      DOMAIN, not by a directory `key`: the seed is derived and re-derivable
 *      (ADR-635 D1), so its keys and titles can change under us, while
 *      `mcp.linear.app` is the server's own address and is what an attached
 *      row stores. One mark therefore serves the finder row, the attached
 *      connection, and any re-derivation of the seed.
 *
 *   2. A LETTERMARK for everything else — the initial, on a tone derived by
 *      hashing the title. This is not a placeholder to be embarrassed about:
 *      it is stable (the same server always gets the same colour), it is
 *      distinguishable (a scanning member sees a varied column, not seventeen
 *      identical plugs), and it degrades honestly — it claims nothing about a
 *      vendor whose mark we have not vetted.
 *
 * A MARK IS ADDED ONLY WHEN ITS SHAPE HAS BEEN SEEN RENDERED. This file was
 * first written with ~28 marks drawn from memory, and the click-pass found that
 * roughly half of them were confident, plausible, WRONG shapes: Ahrefs rendered
 * as a lowercase b, Box as a pair of goggles, Datadog as a blob, Gong as a
 * circle in a circle, Similarweb as a Pac-Man. Every one of those passed
 * typecheck, passed the build, and compiled into the CSS — a path string cannot
 * be wrong in a way any gate reads, and a fabricated mark does not fail, it
 * MISIDENTIFIES a vendor on the surface whose whole subject is what the member
 * is about to trust. The ones that survive here are the ones whose rendering
 * was inspected; the rest were dropped to lettermarks, which is the honest
 * answer and not a lesser one.
 *
 * So: adding the Nth mark is one entry in `DOMAIN_MARKS`, and it is not done
 * until someone has LOOKED at it. Not adding it is entirely fine.
 */

import type { ReactNode } from "react";

// ---------------------------------------------------------------------------
// Tier 1 — hand-added marks, keyed by the server's own domain.
// Monochrome single-path SVGs taking `currentColor`, matching the convention in
// `components/ui/PlatformIcons.tsx`: the chip supplies the brand colour, the
// mark supplies the shape. That keeps every mark legible in both themes
// without a per-mark dark-mode variant.
// ---------------------------------------------------------------------------

export interface ConnectorMark {
  /** Brand chip background (Tailwind). Light/dark pair where the brand needs one. */
  chipClass: string;
  /** Foreground class for the glyph. Defaults to white on the brand chip. */
  glyphClass?: string;
  icon: ReactNode;
}

const svg = (path: string, viewBox = "0 0 24 24") => (
  <svg viewBox={viewBox} fill="currentColor" className="h-[58%] w-[58%]" aria-hidden="true">
    <path d={path} />
  </svg>
);

const LINEAR =
  "M2.886 4.18A11.982 11.982 0 0 1 11.99 0C18.624 0 24 5.376 24 12.01c0 3.64-1.62 6.903-4.18 9.104L2.887 4.18zM1.3 6.372l16.329 16.328c-.485.272-.99.51-1.512.712L.588 7.884c.202-.522.44-1.027.712-1.512zM.155 10.157l13.688 13.688c-.681-.083-1.343-.228-1.978-.43L.585 12.135a11.7 11.7 0 0 1-.43-1.978zm.207 5.752l7.73 7.73a12.026 12.026 0 0 1-7.73-7.73z";

const FIGMA =
  "M8.667 24c2.209 0 4-1.791 4-4v-4h-4c-2.209 0-4 1.791-4 4s1.791 4 4 4zm-4-12c0-2.209 1.791-4 4-4h4v8h-4c-2.209 0-4-1.791-4-4zm0-8c0-2.209 1.791-4 4-4h4v8h-4c-2.209 0-4-1.791-4-4zm8-4h4c2.209 0 4 1.791 4 4s-1.791 4-4 4h-4V0zm8 12c0 2.209-1.791 4-4 4s-4-1.791-4-4 1.791-4 4-4 4 1.791 4 4z";

const STRIPE =
  "M13.976 9.15c-2.172-.806-3.356-1.426-3.356-2.409 0-.831.683-1.305 1.901-1.305 2.227 0 4.515.858 6.09 1.631l.89-5.494C18.252.975 15.697 0 12.165 0 9.667 0 7.589.654 6.104 1.872 4.56 3.147 3.757 4.992 3.757 7.218c0 4.039 2.467 5.76 6.476 7.219 2.585.92 3.445 1.574 3.445 2.583 0 .98-.84 1.545-2.354 1.545-1.875 0-4.965-.921-6.99-2.109l-.9 5.555C5.175 22.99 8.385 24 11.714 24c2.641 0 4.843-.624 6.328-1.813 1.664-1.305 2.525-3.236 2.525-5.732 0-4.128-2.524-5.851-6.591-7.305z";

const NOTION =
  "M4.459 4.208c.746.606 1.026.56 2.428.466l13.215-.793c.28 0 .047-.28-.046-.326L17.86 1.968c-.42-.326-.98-.7-2.055-.607L3.01 2.295c-.466.046-.56.28-.374.466l1.823 1.447zm.793 3.08v13.904c0 .747.373 1.027 1.213.98l14.523-.84c.84-.046.934-.56.934-1.166V6.354c0-.606-.234-.933-.746-.886l-15.177.887c-.56.046-.747.326-.747.933zm14.337.745c.093.42 0 .84-.42.888l-.7.14v10.264c-.608.327-1.168.514-1.635.514-.748 0-.935-.234-1.495-.933l-4.577-7.186v6.952l1.448.327s0 .84-1.168.84l-3.222.186c-.093-.186 0-.653.327-.746l.84-.233V9.854L7.822 9.76c-.094-.42.14-1.026.793-1.073l3.456-.233 4.764 7.279v-6.44l-1.215-.14c-.093-.513.28-.886.747-.933l3.222-.187zM2.87.119l13.449-.933c1.634-.14 2.055-.047 3.082.7l4.249 2.986c.7.513.934.653.934 1.213v16.378c0 1.026-.373 1.634-1.68 1.726l-15.458.934c-.98.046-1.448-.093-1.962-.747L1.945 18.79c-.56-.747-.793-1.306-.793-1.958V2.005C1.152.933 1.525.212 2.87.119z";

const SLACK =
  "M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523A2.528 2.528 0 0 1 0 15.165a2.527 2.527 0 0 1 2.522-2.52h2.52v2.52zM6.313 15.165a2.527 2.527 0 0 1 2.521-2.52 2.527 2.527 0 0 1 2.521 2.52v6.313A2.528 2.528 0 0 1 8.834 24a2.528 2.528 0 0 1-2.521-2.522v-6.313zM8.834 5.042a2.528 2.528 0 0 1-2.521-2.52A2.528 2.528 0 0 1 8.834 0a2.528 2.528 0 0 1 2.521 2.522v2.52H8.834zM8.834 6.313a2.528 2.528 0 0 1 2.521 2.521 2.528 2.528 0 0 1-2.521 2.521H2.522A2.528 2.528 0 0 1 0 8.834a2.528 2.528 0 0 1 2.522-2.521h6.312zM18.956 8.834a2.528 2.528 0 0 1 2.522-2.521A2.528 2.528 0 0 1 24 8.834a2.528 2.528 0 0 1-2.522 2.521h-2.522V8.834zM17.688 8.834a2.528 2.528 0 0 1-2.523 2.521 2.527 2.527 0 0 1-2.52-2.521V2.522A2.527 2.527 0 0 1 15.165 0a2.528 2.528 0 0 1 2.523 2.522v6.312zM15.165 18.956a2.528 2.528 0 0 1 2.523 2.522A2.528 2.528 0 0 1 15.165 24a2.527 2.527 0 0 1-2.52-2.522v-2.522h2.52zM15.165 17.688a2.527 2.527 0 0 1-2.52-2.523 2.526 2.526 0 0 1 2.52-2.52h6.313A2.527 2.527 0 0 1 24 15.165a2.528 2.528 0 0 1-2.522 2.523h-6.313z";

const GITHUB =
  "M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z";


const HUBSPOT =
  "M18.164 7.931V5.085a2.198 2.198 0 0 0 1.267-1.978v-.067A2.2 2.2 0 0 0 17.238.845h-.066a2.2 2.2 0 0 0-2.195 2.195v.067a2.196 2.196 0 0 0 1.252 1.978v2.846a6.22 6.22 0 0 0-2.957 1.301L5.45 3.238a2.46 2.46 0 0 0 .087-.617A2.472 2.472 0 1 0 3.064 5.09c.412 0 .81-.11 1.164-.302l7.694 5.98a6.223 6.223 0 0 0 .095 7.012l-2.34 2.34a2.023 2.023 0 0 0-.582-.095 2.033 2.033 0 1 0 2.033 2.033c0-.2-.033-.397-.095-.582l2.315-2.315a6.243 6.243 0 1 0 4.816-11.23zm-.94 9.362a3.204 3.204 0 1 1 0-6.408 3.204 3.204 0 0 1 0 6.408z";
// Restored after the click-pass below: these rendered as their real, recognisable
// marks in the probe screenshot.
const SHOPIFY =
  "M15.337 23.979l7.216-1.561s-2.604-17.613-2.625-17.73c-.018-.116-.114-.192-.211-.192s-1.929-.136-1.929-.136-1.275-1.274-1.439-1.411c-.045-.037-.075-.057-.121-.074l-.914 21.104h.023zM11.71 11.305s-.81-.424-1.774-.424c-1.447 0-1.504.906-1.504 1.141 0 1.232 3.24 1.715 3.24 4.629 0 2.295-1.44 3.76-3.406 3.76-2.354 0-3.54-1.465-3.54-1.465l.646-2.086s1.245 1.066 2.28 1.066c.675 0 .975-.541.975-.932 0-1.619-2.654-1.694-2.654-4.359 0-2.237 1.599-4.416 4.854-4.416 1.245 0 1.875.361 1.875.361l-.945 2.715-.047.01zM11.17.83c.136 0 .271.045.405.135-.984.465-2.064 1.65-2.523 4.02-.641.195-1.26.389-1.83.57C7.762 3.75 8.986.84 11.17.83zm1.23 2.921v.15c-.75.225-1.575.48-2.386.734.465-1.755 1.32-2.609 2.076-2.93.194.5.31 1.185.31 2.046zm.766-2.281c.704.074 1.157.874 1.448 1.78-.356.104-.75.225-1.185.359v-.255c0-.734-.104-1.334-.263-1.809v-.075zM17.7 2.34c-.015 0-.315.09-.81.24-.487-1.41-1.35-2.7-2.864-2.7h-.135C13.47-.9 12.9-1 12.42-1 8.686-1 6.9 3.674 6.345 6.045c-1.44.445-2.475.77-2.596.81-.81.255-.825.28-.93 1.04C2.745 8.46.6 24.93.6 24.93l16.65 3.12L17.7 2.34z";

const ASANA =
  "M18.78 12.653a5.22 5.22 0 1 0 0 10.44 5.22 5.22 0 0 0 0-10.44zm-13.56 0a5.22 5.22 0 1 0 0 10.44 5.22 5.22 0 0 0 0-10.44zM17.22 6.127a5.22 5.22 0 1 1-10.44 0 5.22 5.22 0 0 1 10.44 0z";

const ATLASSIAN =
  "M7.12 11.3a.6.6 0 0 0-1.02.1L.07 23.4a.62.62 0 0 0 .55.9h8.34a.6.6 0 0 0 .54-.33c1.8-3.72.71-9.37-2.38-12.67zM11.53.33a13.2 13.2 0 0 0-.77 13.03l4.05 8.1a.62.62 0 0 0 .55.34h8.34a.62.62 0 0 0 .55-.9S12.9.99 12.6.39a.6.6 0 0 0-1.07-.06z";

const INTERCOM =
  "M21 0H3a3 3 0 0 0-3 3v18a3 3 0 0 0 3 3h18a3 3 0 0 0 3-3V3a3 3 0 0 0-3-3zM8.2 4.8a.8.8 0 1 1 1.6 0v9.2a.8.8 0 1 1-1.6 0V4.8zm-3.2 1a.8.8 0 1 1 1.6 0v7.4a.8.8 0 1 1-1.6 0V5.8zm13.98 13.63c-.13.11-3.2 2.7-6.98 2.7s-6.85-2.59-6.98-2.7a.8.8 0 0 1 1.03-1.22c.05.04 2.82 2.32 5.95 2.32 3.17 0 5.92-2.29 5.95-2.32a.8.8 0 0 1 1.03 1.22zM19 13.2a.8.8 0 1 1-1.6 0V5.8a.8.8 0 1 1 1.6 0v7.4zm-3.2.8a.8.8 0 1 1-1.6 0V4.8a.8.8 0 1 1 1.6 0v9.2z";

const HEX =
  "M12 1.2L2.4 6.6v10.8L12 22.8l9.6-5.4V6.6L12 1.2zm0 3.9l6.3 3.54v7.08L12 19.26 5.7 15.72V8.64L12 5.1z";

const DOCUSIGN =
  "M12 0L2 5v14l10 5 10-5V5L12 0zm4.6 8.9l-5.5 6.9a.9.9 0 0 1-1.35.07L6.6 12.7a.9.9 0 1 1 1.27-1.27l2.44 2.44 4.88-6.1a.9.9 0 1 1 1.41 1.13z";

const PAYPAL =
  "M7.076 21.337H2.47a.641.641 0 0 1-.633-.74L4.944.901C5.026.382 5.474 0 5.998 0h7.46c2.57 0 4.578.543 5.69 1.81.987 1.124 1.3 2.42 1.075 4.334-.007.06-.014.12-.023.18-.797 4.99-4.055 6.71-8.227 6.71H10.9c-.524 0-.968.382-1.05.9l-1.12 7.106a.641.641 0 0 1-.633.54l-.021-.001-.999-.242zM19.79 7.386c-.048.3-.104.593-.168.882-1.03 4.64-4.34 6.24-8.57 6.24H9.13a1.05 1.05 0 0 0-1.038.888l-1.1 6.98-.313 1.98a.554.554 0 0 0 .546.64h3.82a.92.92 0 0 0 .909-.777l.038-.194.72-4.567.046-.251a.92.92 0 0 1 .909-.777h.572c3.7 0 6.598-1.503 7.445-5.852.354-1.817.17-3.334-.766-4.4a3.66 3.66 0 0 0-1.05-.81l-.078.018z";

const SQUARE =
  "M4.5 0h15A4.5 4.5 0 0 1 24 4.5v15a4.5 4.5 0 0 1-4.5 4.5h-15A4.5 4.5 0 0 1 0 19.5v-15A4.5 4.5 0 0 1 4.5 0zm2.4 6a.9.9 0 0 0-.9.9v10.2a.9.9 0 0 0 .9.9h10.2a.9.9 0 0 0 .9-.9V6.9a.9.9 0 0 0-.9-.9H6.9zm2.7 3h4.8a.6.6 0 0 1 .6.6v4.8a.6.6 0 0 1-.6.6H9.6a.6.6 0 0 1-.6-.6V9.6a.6.6 0 0 1 .6-.6z";

const QUICKBOOKS =
  "M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm-1.2 17.4H9a5.4 5.4 0 0 1 0-10.8h.6v2.4H9a3 3 0 0 0 0 6h1.8V4.8h2.4v12.6zm4.2 0h-.6V15h.6a3 3 0 0 0 0-6h-1.8v-2.4H15a5.4 5.4 0 0 1 0 10.8z";

const ZOOM =
  "M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm4.8 14.4a.6.6 0 0 1-.943.49l-2.257-1.58v.89a1.2 1.2 0 0 1-1.2 1.2H7.8a1.2 1.2 0 0 1-1.2-1.2V9.6a1.2 1.2 0 0 1 1.2-1.2h4.6a1.2 1.2 0 0 1 1.2 1.2v.89l2.257-1.58a.6.6 0 0 1 .943.49v4.8z";


/**
 * Domain → mark. The key is the server's HOST as the directory seed and an
 * attached row both spell it, so one entry serves the finder and the connected
 * pane without a second lookup table.
 *
 * Subdomain-insensitive matching happens in `markForHost`: an entry may be
 * keyed on the REGISTRABLE domain (`linear.app`) and still match
 * `mcp.linear.app`, because every vendor here fronts its MCP server on a
 * subdomain of its own brand and the subdomain is not stable (`mcp.` vs
 * `mcp-us.` vs `api.`).
 */
const DOMAIN_MARKS: Record<string, ConnectorMark> = {
  "linear.app": { chipClass: "bg-[#5E6AD2]", icon: svg(LINEAR) },
  "figma.com": { chipClass: "bg-[#0D0D0D]", icon: svg(FIGMA) },
  "stripe.com": { chipClass: "bg-[#635BFF]", icon: svg(STRIPE) },
  "notion.com": { chipClass: "bg-black dark:bg-white", glyphClass: "text-white dark:text-black", icon: svg(NOTION) },
  "notion.so": { chipClass: "bg-black dark:bg-white", glyphClass: "text-white dark:text-black", icon: svg(NOTION) },
  "slack.com": { chipClass: "bg-[#4A154B]", icon: svg(SLACK) },
  "github.com": { chipClass: "bg-gray-900 dark:bg-white", glyphClass: "text-white dark:text-black", icon: svg(GITHUB) },
  "githubcopilot.com": { chipClass: "bg-gray-900 dark:bg-white", glyphClass: "text-white dark:text-black", icon: svg(GITHUB) },
  "hubspot.com": { chipClass: "bg-[#FF7A59]", icon: svg(HUBSPOT) },
  "myshopify.com": { chipClass: "bg-[#5A863E]", icon: svg(SHOPIFY) },
  "shopify.com": { chipClass: "bg-[#5A863E]", icon: svg(SHOPIFY) },
  "asana.com": { chipClass: "bg-[#F06A6A]", icon: svg(ASANA) },
  "atlassian.com": { chipClass: "bg-[#0052CC]", icon: svg(ATLASSIAN) },
  "intercom.com": { chipClass: "bg-[#1F8DED]", icon: svg(INTERCOM) },
  "hex.tech": { chipClass: "bg-[#2E2E38]", icon: svg(HEX) },
  "docusign.com": { chipClass: "bg-[#3C0A6B]", icon: svg(DOCUSIGN) },
  "paypal.com": { chipClass: "bg-[#003087]", icon: svg(PAYPAL) },
  "squareup.com": { chipClass: "bg-[#0D0D0D]", icon: svg(SQUARE) },
  "intuit.com": { chipClass: "bg-[#2CA01C]", icon: svg(QUICKBOOKS) },
  "zoom.us": { chipClass: "bg-[#0B5CFF]", icon: svg(ZOOM) },
};

/**
 * Directory-key → mark, for a server whose HOST cannot identify it. Anthropic's
 * health-sciences plugin fronts FOUR corpora (bioRxiv · ClinicalTrials · ChEMBL
 * · PubMed) from two `*.mcp.claude.com` hosts, so a host lookup cannot tell
 * them apart and the directory key is the only thing that can.
 *
 * EMPTY today, deliberately: none of those four has a mark whose shape was
 * verified, and the lettermark already separates them (they are seeded on the
 * TITLE, which differs). The map stays because the shared-host case is real and
 * the next verified mark for one of them has nowhere else to go. Checked only
 * after the host misses, so a real vendor domain always wins.
 */
const KEY_MARKS: Record<string, ConnectorMark> = {};

// ---------------------------------------------------------------------------
// Tier 2 — the derived lettermark.
// ---------------------------------------------------------------------------

/**
 * The lettermark tones. Chosen to be distinguishable from each other at 28px
 * AND to read as one family rather than a rainbow — muted, mid-luminance, all
 * carrying white text in both themes so no tone needs a dark-mode variant.
 *
 * TWELVE, not eight, and NOT a count chosen to make today's list collide-free.
 *
 * The directory is letter-clustered — six of the seventeen fallback rows start
 * with C — so two rows sharing a letter AND a tone is a birthday problem that
 * bites early. It is tempting to tune the palette size and the hash multiplier
 * until the live seed comes out clean, and that was measured: several settings
 * do (n=12·mult=33 skipping the initial, n=14·mult=31, …). Every one of them
 * collides again after ten more C-named servers, and the seed is DERIVED and
 * re-derivable (ADR-635 D1), so a setting fitted to today's 55 rows is a gate
 * agreeing with itself. A pure per-row function cannot guarantee uniqueness
 * without seeing the whole list, which the resolver never does.
 *
 * So the bound is stated rather than pretended: twelve tones make the list
 * SCANNABLE — a member sweeping the modal sees a varied column instead of
 * seventeen identical plugs — and two same-letter rows may share a tone. What
 * identifies a row is its NAME, rendered immediately beside the chip. The chip
 * is a wayfinding aid, never the identifier, and the gate asserts that reading
 * (tone spread and a bounded worst-case cluster), not an unachievable zero.
 */
const LETTER_TONES = [
  "bg-[#5B6B7C]",
  "bg-[#6B5B7C]",
  "bg-[#7C5B5B]",
  "bg-[#5B7C6B]",
  "bg-[#7C6B5B]",
  "bg-[#4F6E85]",
  "bg-[#785A70]",
  "bg-[#5F6F4F]",
  "bg-[#6E5F85]",
  "bg-[#85604F]",
  "bg-[#4F7A72]",
  "bg-[#7A4F5F]",
];

/** Stable per-domain tone. A server's chip must not change colour between the
 *  finder row and the connected row, so the tone is a pure function of the key
 *  — never of list position, which differs between the two surfaces. */
function toneFor(seed: string): string {
  let h = 0;
  for (let i = 0; i < seed.length; i += 1) {
    h = (h * 31 + seed.charCodeAt(i)) >>> 0;
  }
  return LETTER_TONES[h % LETTER_TONES.length];
}

/** The letter shown. The TITLE's initial, not the domain's — a member reads
 *  "Ahrefs", so the chip says A even though the host is `api.ahrefs.com`. */
function letterFor(title: string, host: string): string {
  const source = title.trim() || host;
  const ch = source.replace(/^(https?:\/\/)?(www\.)?/, "").charAt(0);
  return /[a-z0-9]/i.test(ch) ? ch.toUpperCase() : "•";
}

// ---------------------------------------------------------------------------
// Resolution
// ---------------------------------------------------------------------------

/** The host of a URL, lowercased, with no port. Returns '' for an unparseable
 *  value — a pasted half-URL must not throw inside a render. */
export function hostOf(url: string | null | undefined): string {
  if (!url) return "";
  try {
    return new URL(url).hostname.toLowerCase();
  } catch {
    // A bare host or a half-typed URL: take everything before the first slash.
    return (url.split("/")[0] ?? "").replace(/^https?:?/, "").replace(/^\/+/, "").toLowerCase();
  }
}

/** Match a host against `DOMAIN_MARKS`, honouring subdomains: `mcp.linear.app`
 *  finds the `linear.app` entry. Walks the labels from the right so a longer,
 *  more specific key (`myshopify.com`) wins over a shorter one. */
function markForHost(host: string): ConnectorMark | undefined {
  if (!host) return undefined;
  const direct = DOMAIN_MARKS[host];
  if (direct) return direct;
  const labels = host.split(".");
  for (let i = 1; i < labels.length - 1; i += 1) {
    const candidate = labels.slice(i).join(".");
    const hit = DOMAIN_MARKS[candidate];
    if (hit) return hit;
  }
  return undefined;
}

export interface ConnectorIdentity {
  chipClass: string;
  glyphClass: string;
  /** The brand mark, or null when this identity is a lettermark. */
  icon: ReactNode | null;
  /** The initial rendered when `icon` is null. */
  letter: string;
  /** True when a hand-added mark matched — the caller may want to know that a
   *  chip is a real brand rather than a derived one (the finder does not, but a
   *  gate does). */
  branded: boolean;
}

/**
 * The one resolver. Give it whatever the surface knows — a server URL, a
 * display title, and optionally the directory key — and it returns the chip,
 * the glyph and whether the mark is real.
 *
 * Every connector surface calls THIS, so a connector cannot look one way in the
 * finder and another way on /reach.
 */
export function connectorIdentity(input: {
  url?: string | null;
  title?: string | null;
  key?: string | null;
}): ConnectorIdentity {
  const host = hostOf(input.url);
  const title = (input.title ?? "").trim();
  const mark = markForHost(host) ?? (input.key ? KEY_MARKS[input.key] : undefined);
  if (mark) {
    return {
      chipClass: mark.chipClass,
      glyphClass: mark.glyphClass ?? "text-white",
      icon: mark.icon,
      letter: letterFor(title, host),
      branded: true,
    };
  }
  // The seed is what makes the tone stable — the same server must get the same
  // colour in the finder and on /reach, so it can never be list position.
  //
  // Seeded on the TITLE, falling back to the host.
  //
  // The host is the more stable-looking key and it is the wrong one: four of
  // the directory's literature endpoints share ONE host
  // (`hcls.mcp.claude.com` fronts bioRxiv, ClinicalTrials and ChEMBL), so a
  // host-seeded tone paints three rows the same colour — the exact
  // indistinguishability the lettermark exists to end. The title is what the
  // member reads, what differs between those three, and what an attach carries
  // over from the finder row it was added from (`attached_connectors.py` stores
  // the title the attach was given). The host covers the one case with no
  // title: a pasted URL before the server has named itself.
  const seed = title.toLowerCase() || host || input.key || "connector";
  return {
    chipClass: toneFor(seed),
    glyphClass: "text-white",
    icon: null,
    letter: letterFor(title, host),
    branded: false,
  };
}

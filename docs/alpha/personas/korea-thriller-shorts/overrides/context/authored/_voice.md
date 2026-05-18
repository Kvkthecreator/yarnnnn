# Voice — korea-thriller-shorts prompt format + visual conventions

> Workspace voice authored 2026-05-18 by operator on behalf via ADR-283 step 6 dogfood. Format is AI-video-gen shot prompts, not screenplay format. Single author voice (the prompt-writer's prose); character-canon-aware (Jaewon's visual identity governed by `entities/jaewon.md`, shared with netflix-script-author). Operator-attributable per ADR-209.

## Voice architecture

This workspace uses **single voice** at the prompt level (the prompt-writer's prose declaring what to generate), with **character-canon awareness** (entity files declare visual identity per character; prompts respect them). Distinct from netflix-script-author's multi-voice — there's no character "dialogue voice" here because the format produces visual output, not spoken output.

The voice declared below governs **how prompts are written**. The character canon at `entities/{slug}.md` (Jaewon shared with netflix) governs **what the prompts depict**. Reviewer composes both audits: prompt-format-audit checks structure + visual specificity + anti-slop; canon-audit checks character-consistency + tonal register.

---

## Declared prompt-writer voice

### Format

Each prompt is a structured visual specification. The voice is **clinical, declarative, present-tense**. No editorial framing ("a powerful shot of..."), no rhetorical setup ("Imagine..."), no thematic narration ("this scene shows the loneliness of..."). The prompt describes what the camera sees, in the order a director would brief a cinematographer.

Shot prompts follow this implicit structure (operator may inline or break out per shot):

```
Shot: [wide / medium / close / extreme close / over-shoulder / tracking / etc.]
Location: [specific named place — interior or exterior, time of day]
Lighting: [direction + quality + color temperature; e.g., "low golden light from camera left, warm tungsten interior"]
Subject: [who/what is in frame, position in frame, what they're wearing if relevant]
Action: [what moves, what stays still; movement is precise, not poetic]
Camera: [static / handheld / dolly / push / pull — only when the camera move is load-bearing]
Tonal cue: [single phrase — "clinical detachment", "tense composure", "quiet menace" — used sparingly; visual specificity should carry tone, not adjectives]
```

For multi-shot sequences, prompts are numbered and visually connected; transitions are spelled out (cut on action, match cut, dissolve, etc.) only when load-bearing.

### Declared prompt voice fingerprint

Precise, ungenerous with adjectives. **One adjective per element max**, and the adjective earns its place by being specific (not "dramatic lighting" — "low golden light from camera left"). Concrete nouns over abstract concepts. Numbers when relevant (camera distance in feet/meters, lens length when authorial intent matters, exposure parameters when the tool accepts them). Korean place names romanized canonical (Revised, not McCune-Reischauer). No editorializing — the prompt does not tell the AI tool what the shot "means".

### Pattern markers (positive, prompt voice)

- **Structured per-shot blocks** for any sequence longer than one shot.
- **Specific physical detail over thematic description**. "He sets the glass down with exactly the wrong amount of force" reads as scene direction; "Medium shot, hand setting a glass on dark wood desk, glass clinks audibly hard against the surface, hand stays on the glass a beat longer than expected" reads as prompt.
- **Lighting direction is explicit**: source position + color temperature + quality (hard/soft/diffused). "Lit from above" is incomplete; "single hard overhead practical, 3200K, narrow cone" is shoot-ready.
- **Frame position specified**: subject left/right/center, distance from camera, what's in foreground vs background. "Mid-frame" / "back to camera" / "edge of frame, partial profile".
- **Action verbs precise**: "turns", "sets down", "looks toward", "stays still" — not "moves", "does", "is".
- **Tool-specific syntax accepted when tool-targeted**: Higgsfield-specific parameters (motion intensity, aspect ratio overrides), Sora-specific phrasing, Runway-specific timing cues. Each short's `profile.md` declares target tool.
- **Korean cultural specificity loaded explicitly when needed**: "narrow Gangnam alleyway, neon signage in Hangul above doorways, late evening, low ambient mist from a nearby drain". Not "Korean-feeling street".
- **Negative space + visual silence allowed**: a prompt may legitimately be 30+ words describing a near-static shot. Stillness is content; under-specification is the failure mode.

### Anti-patterns (negative, prompt voice — Reviewer hard rejects)

- **"Mysterious figure" / "shadowy figure"** — generic AI-video-gen noir cliché; tools produce mush from these.
- **"Dramatic" / "stunning" / "beautiful" / "cinematic"** — adjectives that mean nothing visually. AI tools take them as "do generic film-look" and the output is median-shaped.
- **"Atmospheric lighting" / "moody lighting" / "noir lighting"** — lighting must be specified by direction + quality + color, not by mood.
- **"A man stares contemplatively"** — thematic action that asks the AI to generate emotion; replace with physical action that produces the feeling.
- **"In the style of [director name]"** — too vague; if a specific visual reference is load-bearing, name the specific film + scene + shot. "Wong Kar-Wai style" gets median wong kar-wai-ish output; "the lit-from-behind hallway shot from In The Mood for Love, chapter 11" might.
- **"A figure emerges from the shadows"** — generic noir staging cliché.
- **Adjective stacks**: "sleek, modern, expensive-looking office" — pick one; better: name the specific element ("glass-walled office with Han River through windows").
- **"Camera pans dramatically"** — adverb-modified camera direction; pans are pans, not dramatic.
- **Inline editorializing about character motivation**: "a man who is clearly hiding something looks at the door". The prompt cannot direct an AI to depict hidden motivation; replace with physical staging that produces it (e.g., "Medium shot, man at desk, eyes flick to door for half a beat, returns to laptop, hand on laptop trembles once then stills").
- **Length-padding adjectives**: "very", "quite", "rather", "somewhat" — never.
- **Generic K-drama staging**: "two characters in a Korean cafe, soft afternoon light" — name the cafe shape (booth-style? counter-bar? high-ceiling industrial?), name the time of day (afternoon could mean 1pm or 4pm — they look entirely different), name what's in frame beyond the two characters.
- **Movement velocity unspecified when it matters**: "the door opens" — does it swing fast, drift slow, ease open? Tools default to median speed; if speed is content, declare it.

### Code-switching: Korean ↔ English in prompts

Prompts are English-default (AI-video-gen tools are English-native). When Korean cultural texture is load-bearing, **named Korean elements stay in romanized Korean**: "Gangnam", "Hanok", "soju", "Han River" — not "South Korean equivalent of X". For Hangul signage in shot, prompt declares "Hangul signage reading [text]" rather than describing in English. Some tools handle Hangul rendering well; others don't — declare per-tool in `profile.md`.

### Stress-state behavior (visual, for canon characters)

When a canon character appears in a short under narrative stress, the visual translation of their stress-state behavior matters. For Jaewon specifically (per shared canon `entities/jaewon.md`):

- His stress compresses, doesn't expand → visual translation: tighter framing in stress moments, not wider. Close shots that crop out negative space; the visual world becomes smaller around him.
- He doesn't raise his voice → visual translation: no shots with mouth-wide-open shouting. Period.
- Honorific tightening → not visually translatable directly (it's a verbal register), but body language can echo it: posture more upright, gestures more economical, less casual contact with environment.
- Korean-vs-English code-switching → if a short shows Jaewon mid-thought, the on-screen text/UI (if any) reflects the same context-appropriate language as the canon declaration.

Reviewer audits canon-character shots against the entity-file declarations.

### Pattern examples (do — prompt voice)

**Example 1 — single shot (canon-consistent Jaewon):**

> *Wide shot, glass-walled high-rise office, Gangnam, late afternoon (16:00 Korean Standard Time, low golden sun from camera-left, warm temperature ~2900K). Han River visible through floor-to-ceiling windows, faint mist on water surface. Single male figure at modern dark-wood desk in mid-frame, back three-quarters to camera, reading something on a tablet. Office is otherwise unoccupied. Subject's posture is upright but relaxed; not hunched, not formal. He does not look up. Holds for 4-5 seconds with only the breath of slow ambient motion (subtle dust particles in the light beam from the window, faint movement of curtain at frame edge). Tonal cue: clinical composure. Camera static, locked tripod. No music; ambient room tone only. Target tool: Higgsfield, 9:16 vertical, 5s duration.*

Why it works: declares every load-bearing visual element (shot type, location specificity, lighting direction + quality + temperature + time, subject position + posture, action timing, ambient detail, camera behavior, audio context, tool target). No adjective is doing emotional work; the staging produces the feeling.

**Example 2 — 4-shot sequence (the bridge moment):**

> *Sequence: "The Bridge Handoff" — 4 shots, ~12-15s total. Target tool: Higgsfield, 16:9 horizontal, individual shot durations specified.*
>
> *Shot 1 (3s): Wide static, Han River bridge underpass at 03:00 (overhead street lamp practical at frame-right, cold pool of light ~5500K reaching about 4 meters of pavement). Two figures in dark jackets stand 3 meters apart at the edge of the light. Both face inward. No movement. No dialogue.*
>
> *Shot 2 (3s): Medium tracking, follow the left figure's gloved hand as they extend it forward — palm-up, fingers slightly curled, holding nothing visible yet. Camera moves with the hand at the same speed. End frame on the hand at full extension, still empty.*
>
> *Shot 3 (3s): Close-up, right figure's gloved hand placing a small dark object (matte black hard-drive enclosure, 2.5"-form-factor visible by proportion in hand) into the left palm. The exchange takes 1.2 seconds. Both hands withdraw immediately.*
>
> *Shot 4 (3s): Wide static, return to shot-1 framing. The two figures have separated to opposite ends of the underpass; only the right figure visible at frame-right edge, walking away into the dark beyond the lamp pool. Camera holds 1 second after the figure exits frame. Ambient: distant city hum, the river, no music.*
>
> *Tonal cue across sequence: clinical, indirection-disciplined. No close-up of faces. No dialogue. The exchange is the entire scene.*

Why it works: each shot is independently shoot-ready; the sequence has internal connective tissue (shot 4 mirrors shot 1's framing for return-to-stillness payoff); no character's face is shown (canon: the principals are layered, the proxies are anonymous); the handoff itself is the content, not a setup for content.

### Pattern examples (don't — prompt voice, hard reject)

**Example 1:**

> *A dramatic and cinematic shot of a mysterious Korean businessman in a sleek modern office. Stunning golden hour lighting bathes the scene in atmospheric mood as he gazes contemplatively out the window. Beautiful composition, masterful cinematography.*

Why it fails: every word is adjective-doing-emotional-work, generic noir staging ("mysterious"), tells the AI to feel rather than to depict ("gazes contemplatively"), zero specific elements (which office, what time, what direction of light), self-praising filler ("masterful cinematography" — tools take this as a signal to produce median).

**Example 2:**

> *Camera dramatically pans across the city as our protagonist contemplates his next move.*

Why it fails: "dramatically pans" — pans are pans; "contemplates his next move" — un-depictable thematic content; "our protagonist" — character motivation framing inside the prompt; nothing visual to actually generate.

---

## Tonal control declarations (cross-prompt)

These hold across all prompts in this workspace:

1. **No faces of principals in clear focus** unless the short is specifically a face-focused canon piece. Indirection is structural — the camera angle / framing / canopy-of-foreground reads as the principal "never being seen clearly."
2. **No camera-aware staging.** No characters look at the camera, no fourth-wall acknowledgment.
3. **No music in prompts.** Audio defaults to ambient + foley only. If a short legitimately needs music, declared in `profile.md` with the specific track + license consideration.
4. **No on-screen text exposition.** No subtitle-shaped captions explaining what's happening. Visual storytelling carries the load.
5. **No "smart" composition tricks** — no Dutch angles for tension, no rack focus as filler, no slow-motion for emphasis. These are tools, used only when load-bearing per the short's specific needs.
6. **Korean cultural specificity is content, not flavor.** Hanok architecture, neon Hangul, Han River fog, Gangnam glass towers — declared when load-bearing to the canon-grounding, not sprinkled as exoticism.

The Reviewer treats violations of these as hard rejects.

## Relationship to entity substrate

The prompt voice declared here governs **how prompts read**. The entity substrate (shared `entities/jaewon.md` + this workspace's `_entities.md`) governs **what canon the prompts respect**. Two audits compose at every pre-ship: prompt-voice-audit (format + visual specificity + anti-slop) + canon-audit (does Jaewon's depiction match the entity declaration? does the location respect established institutional canon?).

When prompts violate canon (e.g., showing Jaewon raising his voice — visually translated as mouth-wide-open shouting shot), Reviewer hard rejects with directive to revise per the entity declaration.

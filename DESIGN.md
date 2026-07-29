---
name: MiroFish Lemon
description: Editorial document studio for AI character simulation packages
colors:
  paper: "#FAFAF7"
  card-cream: "#FFFDF8"
  ink: "#1A1A1A"
  parchment-border: "#DDD8CC"
  studio-sage: "#6B8F71"
  sage-wash: "#EEF3EC"
  linen: "#F3EFE3"
  linen-muted: "#F6F3EA"
  muted-ink: "#6E685E"
  marker-gold: "#E8C87A"
  gold-wash: "#FAF3DF"
  gold-deep: "#8A6D2A"
  approve-emerald: "#10B981"
  emerald-wash: "#E9F9F1"
  correction-red: "#B94B4B"
  workbench-ink: "#111827"
  workbench-line: "#E5E7EB"
typography:
  display:
    fontFamily: "Georgia, 'Times New Roman', serif"
    fontSize: "27px-44px"
    fontWeight: 600
    letterSpacing: "-0.01em"
  headline:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "14.5px-20px"
    fontWeight: 600
  body:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "13px-15px"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "'JetBrains Mono', 'Fira Mono', monospace"
    fontSize: "9px-12px"
    fontWeight: 400
    letterSpacing: "0.08em-0.18em"
rounded:
  sm: "4px"
  md: "6px"
  lg: "8px"
  card: "10px"
  pill: "999px"
spacing:
  xs: "8px"
  sm: "12px"
  md: "16px"
  lg: "20px"
  xl: "36px"
components:
  button-primary:
    backgroundColor: "{colors.studio-sage}"
    textColor: "#FFFFFF"
    rounded: "{rounded.lg}"
    padding: "10px 17px"
    typography: "{typography.label}"
  button-approve:
    backgroundColor: "{colors.approve-emerald}"
    textColor: "#FFFFFF"
    rounded: "{rounded.lg}"
    padding: "10px 17px"
  button-plain:
    backgroundColor: "#FFFFFF"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    padding: "10px 17px"
  phase-tab-active:
    backgroundColor: "{colors.gold-wash}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
  doc-card:
    backgroundColor: "{colors.card-cream}"
    rounded: "{rounded.card}"
    padding: "18px 20px"
  doc-card-done:
    backgroundColor: "{colors.emerald-wash}"
    rounded: "{rounded.card}"
  state-pill:
    backgroundColor: "{colors.gold-wash}"
    textColor: "{colors.gold-deep}"
    rounded: "{rounded.pill}"
    padding: "3px 11px"
    typography: "{typography.label}"
---

# Design System: MiroFish Lemon

## 1. Overview

**Creative North Star: "The Screening Room"**

MiroFish Lemon is where Lemon Studios projects a story's future before committing a writers' room to it. The system's destination is a private screening room: dark, focused, the material the only bright thing. The current implementation is the system's **paper phase**: a warm editorial document studio where source documents look like working pages, phases read like production stages, and approval is a physical act (a page turning emerald). Every design decision should still pass the Screening Room test: does this put light on the story and keep the machinery in the dark?

The system explicitly rejects generic AI-SaaS dashboards (gradient heroes, metric cards, purple-blue everything), enterprise chrome (dense toolbars, tiny gray text), and wall-to-wall cyberpunk (the terminal aesthetic belongs exclusively to the Character Engine sub-app). Engine telemetry (iterations, tool counts, console noise) stays out of the producer's line of sight.

**Key Characteristics:**
- Warm paper surfaces with serif display headlines: documents feel like documents.
- Mono uppercase micro-labels carry all metadata and status voice.
- Emerald means done or approved, everywhere, without exception.
- Gold marks the active phase and anything authored by the wizard.
- Drama comes from the story content (quotes, character names), never from UI effects.

## 2. Colors: The Studio Paper Palette

Warm tinted neutrals with one working accent (sage) and two semantic voices (gold for active/authored, emerald for done): a Restrained strategy.

### Primary
- **Studio Sage** (#6B8F71): primary actions and progress fills. The color of "advance": Advance to CAST, Submit Answer, meters in motion.

### Secondary
- **Marker Gold** (#E8C87A, wash #FAF3DF, deep #8A6D2A): the highlighter. Active phase tabs, wizard-authored provenance, the recommended path. Never decorative; always means "this is where you are or what the AI wrote".
- **Approve Emerald** (#10B981, wash #E9F9F1): done-states only. Approved documents, completed phases, the Resume/Download confidence actions. Pairing rule: emerald always arrives with a checkmark or the word itself, never color alone.

### Neutral
- **Paper** (#FAFAF7): app background.
- **Card Cream** (#FFFDF8): raised working surfaces.
- **Ink** (#1A1A1A): primary text. Never #000.
- **Parchment Border** (#DDD8CC): all hairlines and card edges.
- **Muted Ink** (#6E685E): secondary text, labels at rest.
- **Linen** (#F3EFE3) / **Linen Muted** (#F6F3EA): fills for chips, wells, quiet zones.
- **Correction Red** (#B94B4B): errors and destructive actions only.
- **Workbench Ink/Line** (#111827 / #E5E7EB): the legacy engine screens (report workbench) run cooler neutrals; when touching them, warm them toward the studio palette rather than extending the cool set.

### Named Rules
**The Emerald Oath.** Emerald appears only when something is genuinely finished or approved. A button that merely continues is sage; a state that is merely active is gold. If emerald shows, the producer may trust it.

**The Telemetry Curtain.** Engine internals (round counts, tool calls, console text) never take color. They live in muted ink, small, behind the story.

## 3. Typography

**Display Font:** Georgia (with Times New Roman, serif)
**Body Font:** Inter (with system-ui, sans-serif)
**Label/Mono Font:** JetBrains Mono (with Fira Mono, monospace)

Hierarchy is serif display (27 to 44px, weight 600, tight tracking) over Inter body (13 to 15px), annotated by mono uppercase micro-labels (9 to 12px, letterspaced 0.08 to 0.18em). The serif carries editorial warmth; the mono carries operational truth (counts, states, filenames). Body line length caps at 75ch. Scale contrast between adjacent steps stays at or above 1.25.

## 4. Elevation

Essentially flat with tonal layering: cream cards on paper, separated by parchment hairlines. One soft ambient shadow is permitted on frames and pages that represent physical objects (browser frames, working pages, the draft review sheet): large blur, negative spread, warm gray, never stacked. No glassmorphism, no glow.

## 5. Components

- **Buttons**: mono uppercase labels, 8px radius. Primary = sage fill; Approve = emerald fill; Plain = white with parchment border; Ghost = borderless muted ink. Hover shifts border or deepens fill; no transforms.
- **Phase tabs / stepper**: numbered mono index + name; active tab takes the gold wash with gold border.
- **Document tiles (doc-card)**: cream, 10px radius, full parchment border; done state takes the emerald wash with soft green border. State pills (UPLOADED / AUTHORED / APPROVED) are mono, pill-shaped, wash-tinted.
- **Progress meters**: 6px full-radius track in linen; fill is sage in motion, emerald at 100%.
- **Question/quote cards**: serif question text on cream; producer quotes render as indented serif blockquotes. Quotes are first-class content, styled larger than chrome.
- **Inputs**: dashed parchment border at rest, solid gold on focus; generous padding; always dictation-friendly (full-width textareas over constrained fields).
- **Tables (reports)**: full hairline grid, linen header row, 13px body; horizontal scroll inside the table container, never the page.

## 6. Do's and Don'ts

**Do:**
- Put the story's words (character quotes, document text) in the largest, warmest type on the screen.
- Use gold for "you are here" and "the AI wrote this"; make provenance always visible.
- Keep Spanish and English strings equal citizens; no English-only states.
- Respect reduced motion; transitions are opacity/transform only, ease-out, under 300ms.

**Don't:**
- No side-stripe accents (colored border-left/right thicker than 1px); use full borders or washes instead. (Two legacy instances exist in InterviewView and PrepView; remove on next touch.)
- No gradient text, no glassmorphism, no hero-metric cards, no identical icon-card grids.
- No modals as first resort; prefer inline expansion (the accordion report sections are the model).
- No engine jargon in producer-facing copy: "Iteration 3, Tools: Yes" style strings are defects.
- No pure #000 or #FFF; every neutral stays warm.
- Never let the cyberpunk Character Engine aesthetic leak into the main app.

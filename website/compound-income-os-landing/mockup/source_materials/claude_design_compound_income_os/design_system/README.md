# Compound Income OS — Design System

> **Brand essence:** *The discipline of compounding, made auditable.*
> A local-first portfolio research operating system for serious long-term investors.
> Calm, precise, evidence-driven. Apple-inspired clarity meets engineering credibility.

This folder is the canonical design system for **Compound Income OS** — colors, typography, motion, components, and high-fidelity UI kits intended to be picked up by a React/Tailwind implementation later.

---

## 1. Product context

**Compound Income OS** is a local-first portfolio research and decision-support system. It converts local files (broker exports, fundamentals files, watchlists, evidence inputs) into reproducible CSV + Markdown artifacts: portfolio snapshots, rankings, dashboards, dividend-snowball analysis, monthly decision reports, and decision journals.

It is **not** a trading platform, robo-advisor, or screener. It does not execute orders, connect to brokerages, or give investment advice.

**Audience.** Technically sophisticated dividend-growth and quality-compounder investors; engineers, analysts, and finance/data professionals who want reproducible local files over cloud dashboards.

**Two surfaces:**
1. **Marketing site** — landing page direction. Premium, calm, Apple-inspired. Wordmark only.
2. **The OS / Local dashboard** — the application itself. Engineering dashboard meets research workbench. Light app shell with a dark accent surface for the dashboard preview.

**Monetization.** Open-source core (free) → optional Pro Modules → one-time Setup Service → GitHub Sponsors / Early Access.

**Three CTAs in priority order:**
- Primary — *Join Early Access*
- Secondary — *Request GitHub Access*
- Tertiary — *Request Setup Service*

---

## 2. Sources

| Source | Path / Link | Status |
|---|---|---|
| Brand strategy & landing copy | `source_materials/01_brand_strategy_and_copy.md` | full document, source of truth for copy |
| Product notes (IA, dashboard semantics) | `source_materials/product_notes.md` | full document |
| Dummy dashboard data (KPIs, holdings, coverage, etc.) | `source_materials/dummy_dashboard_data.json` | use as the *only* dummy data source for the prototype |
| Mounted seed folder (read-only) | `claude_design_compound_income_os_seed/` | original input |

> No codebase or Figma was provided. The design is built from copy + product notes + dummy data only.

---

## 3. Index

| File / Folder | What it is |
|---|---|
| `colors_and_type.css` | All foundation tokens — color, type scale, spacing, radii, shadows, motion, semantic aliases. **Single source of truth.** |
| `assets/` | Wordmark SVGs, icon usage notes. (Lucide is used as the icon system, via CDN — see ICONOGRAPHY.) |
| `preview/` | Static HTML cards that populate the Design System tab — Type, Colors, Spacing, Components, Brand. |
| `ui_kits/marketing/` | Marketing site UI kit — landing page direction, hero, dashboard preview, sections, footer. |
| `ui_kits/app/` | OS / dashboard UI kit — sidebar, KPI cards, holdings table, coverage panel, decision queue, run manifest. |
| `source_materials/` | Verbatim copies of provided seed materials, for traceability. |
| `SKILL.md` | Cross-compatible Claude Skill front-matter so this directory can be downloaded and used as a Claude Code skill. |

---

## 4. CONTENT FUNDAMENTALS

### Voice
Declarative. Concrete. Numerate. Quietly confident. Short sentences, active verbs.

The brand is the calm, well-read engineer at the back of the room — the one who reads 10-Ks for fun and keeps a paper journal next to a Linux laptop. Never breathless. Never apologetic.

### Person
- **Third-person product**, then **second-person reader.** *"Compound Income OS turns your broker exports… into reproducible artifacts."*
- Avoid first-person plural marketing-speak (*"we believe…"*).
- Reader is *you*, not *the user* — except in technical methodology copy.

### Casing
- **Headlines:** sentence case. *"A local operating system for long-term investing."* — never Title Case.
- **Buttons:** Title Case. *"Join Early Access"*, *"Request GitHub Access"*.
- **Section labels / eyebrows:** UPPERCASE with wide tracking, used sparingly. *"MONTHLY WORKFLOW"*.
- **Status codes & artifact identifiers:** ALL_CAPS_SNAKE — *`COVERED`, `PARTIAL`, `REVIEW`, `MISSING_DATA`, `NO_MATCH`, `INSUFFICIENT_HISTORY`*.
- **Run IDs / paths:** monospace, lowercase. *`reports/demo/decision_journal_2026-04.md`*.

### Punctuation & rhythm
- Em dashes for the calm aside — used freely but not for drama.
- No exclamation marks. None. Anywhere.
- Periods end every list item that is a sentence. Bare nouns may stand alone.
- Numbers, intervals, and statuses are part of the voice.

### Vocabulary
**Prefer:** *reproducible · deterministic · local · manifest · coverage · evidence · gates · artifacts · journal · discipline · practice · visible · traceable · workflow · cycle*.

**Avoid:** *empower · unlock · supercharge · seamless · intelligent · smart · effortless · transform · next-generation · game-changing · revolutionary · AI-driven · insights · empower · streamline · leverage*.

### Examples — what to write, what not to write

| ❌ Avoid | ✅ Prefer |
|---|---|
| "Unlock the power of your portfolio with AI-driven insights." | "Compound Income OS turns your broker exports, fundamentals, and evidence files into reproducible rankings, dashboards, and monthly decision reports." |
| "Smart buy signals on every holding." | "Holdings are scored. Candidate status is rule-based. Coverage gaps stay visible." |
| "Beats the market, every quarter." | "Reproducible monthly research, on inputs you control." |
| "Effortless investing, supercharged." | "A cadence built for long horizons." |
| "AI tells you what to buy." | "Rules-based ranking with visible coverage." |

### Compliance — always, never
**Always include, somewhere visible:**
- "Local-first."
- "No broker execution."
- "Not investment advice."
- "Open-source core."

**Never include:**
- Specific return figures, percentages, or backtested performance claims on the homepage.
- Customer logos or testimonials that imply professional advisory use.
- Anything framing the system as a substitute for an advisor, accountant, or broker.

### Microcopy patterns
- **Empty states:** *"No coverage yet. Drop a broker export into `data/raw/` to begin."*
- **Errors / blockers:** state the cause, the artifact, and the action. *"`MISSING_DATA` — `roic`, `roce` not present in master. Open evidence registry."*
- **CTA microcopy:** one line, factual. *"Open-source core. No cloud account required. Not investment advice."*

### Emoji
**Not used.** Anywhere. Status is communicated via typed pills (`COVERED`, `REVIEW`, etc.) and a single colored dot.

---

## 5. VISUAL FOUNDATIONS

### Tone
Premium, calm, precise, data-driven. **Apple-inspired** in clarity and whitespace; **Bloomberg / engineering dashboard** in numerical density; never trading-app, never crypto, never gaming. The product looks like something you would trust with two decades of decisions.

### Color
- **Canvas** is warm off-white (`--paper-50` `#FBFAF7`) — paper-like, never pure white. This is the single most important brand cue: warmth over sterility.
- **Ink** is near-black charcoal (`--ink-900` `#14181C`) — never #000.
- **Single accent** is muted graphite blue (`--accent-500` `#3F5C7E`). Used for primary buttons, links, active nav, the primary chart line. Never used for decoration or large fills.
- **Soft gold** (`--gold-500` `#B08A3E`) is reserved for editorial moments, the dividend-snowball highlight, and Pro Module marks. Never for buttons or system messaging.
- **Dark accent surface** (`--dark-800` `#131A21`) — used for the hero band on the marketing site, the dashboard preview block, and the dashboard chrome itself. Quietly authoritative; not glossy.
- **Status semantics are calm**, not trading red/green:
  - `OK` / `COVERED` → muted sage green
  - `PARTIAL` → soft amber
  - `REVIEW` → warmer ochre
  - `MISSING_DATA` / `BLOCKED` → muted rose (never alarm-red)
  - `NOT_AVAILABLE` / `INSUFFICIENT_*` → neutral slate

### Type
- **Geist** for all UI and display. Modern, slightly geometric, calm. Tightened tracking on display sizes (`-0.02em`).
- **JetBrains Mono** for KPI numerics, run IDs, artifact paths, and any code. Never decorative.
- **Source Serif 4** appears sparingly — pull-quotes in long-form essays, the brand essence on the About page, occasional editorial block. Italic only. ≤ 2 occurrences per page.
- Headings are sentence-case, weight 500–600, never bold-bold.
- KPI numbers are **always** in mono. Always.

> **Substitution flag.** The brand direction calls for an Apple-feel display; **Söhne / Inter Display** would be ideal but require licensing. **Geist** (free, modern, calm) is the substitute. If a licensed face is preferred, swap `--font-sans` in `colors_and_type.css`.

### Spacing
4-px base scale. Generous on the marketing site (`--space-20` between sections); denser inside the app (`--space-4`/`--space-6`). White space is the primary luxury signal — never decorate to fill it.

### Backgrounds
- **No gradients as decoration.** Ever.
- **No background imagery on the marketing site.** No stock fintech photography.
- **No repeating patterns or textures.**
- The dark surface is a flat fill with a single 1-px inner highlight at the top (`inset 0 1px 0 rgba(255,255,255,0.04)`) — that is the entire decorative vocabulary on dark.
- **Subtle dot grid** is permitted as a *very* low-opacity background on the dashboard preview only (8 % charcoal dots on dark, 4 % charcoal dots on the dashboard light surface).

### Animation
- Calm and brief. `--dur-base: 180ms` is the workhorse; nothing exceeds 280 ms.
- Easing is `cubic-bezier(0.2, 0, 0.2, 1)` (standard). No bounces. No springs.
- Only three animation patterns are sanctioned:
  1. **Fade + 4-px translate-up** for content reveals on scroll.
  2. **Color/opacity transition** on hover and press.
  3. **Width transition** on progress bars and coverage meters.
- No hero parallax. No marquee scrollers. No floating decorative elements.

### Hover & press
- **Hover** on buttons darkens the fill by one accent step (`--accent-500 → --accent-600`); secondary buttons lighten the surface (`--paper-50 → --paper-100`).
- **Press** darkens further (`--accent-500 → --accent-700`) and applies a 1-px inset shadow — no scale transforms.
- **Card hover** raises shadow from `--shadow-xs` to `--shadow-md` and tightens border to `--ink-200`. No transforms.
- **Link hover** swaps to `--accent-hover` plus an underline.

### Borders
- 1-px hairline at `--border-default` (`#E2DCD1`) is the canonical separator on light surfaces.
- On dark surfaces, dividers are `--dark-600` (`#233040`) at 1 px.
- Cards rely on borders + `--shadow-xs`, not heavy box-shadows.
- The `pill` component uses a 1-px tinted border matching its background.

### Shadows — quiet depth
- `--shadow-xs` is the resting state for cards.
- `--shadow-md` is hover-only.
- `--shadow-lg` is reserved for floating menus and popovers.
- Never blur > 32 px; never opacity > 0.10 on light surfaces.
- Focus rings use a 3-px translucent accent halo — visible but not loud.

### Transparency & blur
- **No glassmorphism.** No backdrop-blur on cards or chrome.
- One exception: a soft top-of-page protection gradient on the dashboard (rgba(251,250,247,0) → rgba(251,250,247,1)) when the table scrolls beneath the sticky header. ≤ 24-px tall.
- Pills, badges, and chips are **fully opaque**. Status backgrounds never use alpha.

### Corner radii
- **12 px** (`--radius-lg`) — canonical card, button, input.
- **6 px** (`--radius-sm`) — pills inside dense tables; nested elements.
- **999 px** (`--radius-pill`) — status pills, tag chips.
- **0 px** — table cells, divider lines. The system never uses fully sharp corners decoratively, but data tables stay angular for legibility.

### Cards
- 1-px `--border-default` border.
- 12-px radius.
- `--shadow-xs` resting; `--shadow-md` hover.
- Inner padding `--space-6` on marketing, `--space-4` to `--space-5` inside the app.
- A card title sits at `--t-h4`, a value at `--t-mono-lg`, and a trend caption at `--t-mono-sm` — that is the canonical KPI card.

### Layout rules
- Marketing container max width: **1200 px**.
- App content area: **1320 px max**, sidebar **264 px** fixed.
- Sticky top nav: **64 px**, hairline bottom border, opaque canvas.
- Sticky app header: **56 px** with the same hairline.
- Section padding on marketing: **96–128 px** vertical, **24 px** horizontal min.
- Grid gap: **24 px** default.

### Imagery (when used)
- Cool-leaning monochrome — no warm sunset stock photography.
- B&W or near-B&W with a slight cool grade is preferred. Subtle grain is acceptable; HDR is not.
- The first prototype uses **no imagery** other than the wordmark and the dashboard mockup itself.

### Iconography
See **ICONOGRAPHY** below.

---

## 6. ICONOGRAPHY

**System.** [**Lucide**](https://lucide.dev) — open-source, 1.5-px stroke, rounded line caps, geometric. Loaded from CDN (`https://unpkg.com/lucide@latest`) so the project carries no heavy icon font.

**Substitution flag.** No project icon set was provided. **Lucide** is the closest match for the calm, precise, slightly technical tone — same stroke weight as Apple SF Symbols Light, friendlier than Material Outlined. If the brand later commissions a custom set, the swap target is the `<i data-lucide>` markup in the kits.

**Stroke + size rules**
- **Default stroke width:** `1.5`. Never bolder.
- **Sizes:** 16 px (inline w/ body text), 20 px (nav, buttons), 24 px (section headers), 32 px (feature cards). No 12 px or smaller.
- **Color:** inherits `currentColor`. Use `--fg-muted` for inactive nav, `--fg-default` for active, `--accent-500` for primary actions only.

**Where icons are allowed**
- Sidebar nav (one per section).
- Pills + badges where the typed status alone might be ambiguous (rare).
- Section eyebrows on the marketing page (one optional 20-px icon).
- Document/artifact list rows (file-icon, link-icon).

**Where icons are not allowed**
- Hero. The hero is wordmark + headline + dashboard. No icon decoration.
- KPI cards. The number is the icon.
- Status pills. The colored dot + typed status is sufficient.
- Inside body paragraphs as bullets — paragraphs use prose, lists use either `–` or numbered lists.

**Emoji.** Not used.
**Unicode glyphs as icons.** Not used (no `→`, `✓`, `★` decoration). Within prose copy, an em dash or "→" can appear as punctuation; never as a UI affordance.

**Logos / wordmark.** The first prototype is wordmark-only — `Compound Income OS` set in Geist. Two SVGs ship in `assets/`:
- `assets/wordmark-ink.svg` — for light surfaces
- `assets/wordmark-paper.svg` — for the dark accent surface
A glyph mark may be added later; the design system does not invent one.

---

## 7. How to use

1. Pull `colors_and_type.css` into any new HTML file.
2. Use the semantic CSS variables (`--bg-canvas`, `--fg-default`, `--accent`, etc.) — not the raw hex.
3. Reference `ui_kits/` for component patterns; copy and trim.
4. Read `CONTENT FUNDAMENTALS` before writing copy. Read `Compliance — always, never` before publishing.
5. When in doubt, choose the calmer option.

---

*Compound Income OS is a research and decision-support tool. It does not provide investment, tax, or legal advice, does not guarantee any return, and does not execute orders or connect to brokerages. All decisions, risks, and outcomes remain solely with the user. Past data does not predict future results.*

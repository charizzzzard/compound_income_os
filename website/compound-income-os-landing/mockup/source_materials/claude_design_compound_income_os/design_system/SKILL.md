---
name: compound-income-os-design
description: Use this skill to generate well-branded interfaces and assets for Compound Income OS, either for production or throwaway prototypes/mocks/etc. Contains essential design guidelines, colors, type, fonts, assets, and UI kit components for prototyping the local-first portfolio research operating system.
user-invocable: true
---

# Compound Income OS — Design Skill

Compound Income OS is a **local-first portfolio research and decision-support system** for technically sophisticated dividend-growth and quality-compounder investors. It is not a broker, not a robo-advisor, not a screener. It turns local files into reproducible CSV + Markdown artifacts.

## Read these first

1. `README.md` — full content + visual foundations (voice, casing, vocabulary, color, type, motion, hover/press, borders, shadows, radii, layout, iconography).
2. `colors_and_type.css` — single source of truth for design tokens. **Always import this file.** Use semantic CSS variables (`--bg-canvas`, `--fg-default`, `--accent-500`, `--font-sans`, etc.), never raw hex.
3. `source_materials/01_brand_strategy_and_copy.md` — verbatim landing copy. Use as source of truth for product copy. **Do not invent features or financial claims.**
4. `source_materials/product_notes.md` — IA, dashboard semantics, status code definitions.
5. `source_materials/dummy_dashboard_data.json` — the only sanctioned dummy data source for prototypes.

## Then explore

- `assets/` — wordmark SVGs (`wordmark-ink.svg` for light, `wordmark-paper.svg` for dark accent surfaces).
- `preview/` — the design-system cards (Type, Colors, Spacing, Components, Brand). Useful as visual references for tokens in use.
- `ui_kits/marketing/` — full marketing-site direction. `index.html` is the live landing page. Copy `Sections.jsx`, `Hero`, `DashboardPreview` patterns.
- `ui_kits/app/` — local OS surface. `index.html` shows Dashboard / Monthly Run / Decision Journal / SEC Evidence views with a working sidebar.

## Working rules — non-negotiable

- **No emoji. No unicode-as-icon.** Status is communicated by typed pills (`COVERED`, `PARTIAL`, `REVIEW`, `MISSING_DATA`, `INSUFFICIENT_HISTORY`) and a single colored dot.
- **No trading red/green** as the primary visual language. Use the calm semantic palette in `colors_and_type.css`.
- **No glassmorphism, no gradients as decoration, no stock fintech imagery, no fake customer logos, no fake performance charts, no return promises.**
- **KPI numbers are always JetBrains Mono with tabular numerals.**
- **Headlines are sentence case.** Buttons are Title Case. Run IDs and paths are monospace lowercase.
- **Always include the disclaimer** in any landing or marketing-style output: "Compound Income OS is a research and decision-support tool. It does not provide investment, tax, or legal advice, does not guarantee any return, and does not execute orders or connect to brokerages. All decisions, risks, and outcomes remain solely with the user. Past data does not predict future results."
- **CTAs in priority order:** Join Early Access (primary) → Request GitHub Access (secondary) → Request Setup Service (tertiary).

## Iconography

[Lucide](https://lucide.dev) at 1.5px stroke, loaded from CDN. Do not draw icons by hand; do not use emoji. The hero, KPI cards, and status pills do not get icons.

## When invoked

- For **visual artifacts** (slides, mocks, throwaway prototypes): copy the assets you need out of this folder and create static HTML files. Always link `colors_and_type.css`. Always include the disclaimer if marketing-style.
- For **production code**: read the rules above and become an expert in designing with this brand. The tokens map cleanly to a Tailwind config; the semantic variables are stable.
- If invoked with no other guidance: ask what the user wants to build, ask a few focused questions about audience and surface (marketing vs app), then act as an expert designer who outputs HTML artifacts or production code based on the need. Default to honoring the brand's calm, precise, evidence-driven tone over flourish.

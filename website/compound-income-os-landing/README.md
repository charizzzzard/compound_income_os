# Compound Income OS Landing Page

This is an isolated React/Vite prototype for the Compound Income OS landing page. It presents the local-first portfolio research workflow, synthetic dashboard mockups, and review screenshot artifacts for external visual QA.

The page is a marketing prototype only. It is not investment advice, does not execute orders, and does not connect to brokerages. All dashboard values shown in the page and screenshots are synthetic demo values.

## Commands

Install dependencies:

```bash
npm install
```

Run a local development preview:

```bash
npm run dev -- --host 127.0.0.1 --port 5173
```

Build the production bundle:

```bash
npm run build
```

Run a local production preview after building:

```bash
npm run preview -- --host 127.0.0.1 --port 4173
```

Generate deterministic review screenshots:

```bash
npm run screenshots
```

Do not open `index.html` directly via `file://`. Use the Vite dev server or a built preview so module imports, assets, and styles resolve correctly.

## Deployment

The production build writes static files to:

```text
dist/
```

Important:

- Do not commit `dist/`.
- Do not commit `node_modules/`.
- Do not open source `index.html` directly via `file://`.
- If reviewing from a Handoff ZIP, extract the ZIP first and run the npm commands from this folder.

Deployment options:

- Vercel: import `website/compound-income-os-landing` as the project folder, or configure it as the root directory.
- Netlify: use build command `npm run build` and publish directory `dist`.
- GitHub Pages: possible, but requires a repository/public workflow decision.
- Own server: upload `dist/` after `npm run build`.

## CTA Configuration

CTA URLs and shared site metadata live in:

```text
src/siteConfig.js
```

Optional deployment overrides can be provided with `VITE_*` environment variables. Copy `.env.example` to a local `.env` file if needed. The app builds without these variables and falls back to placeholder `mailto:` links and `TBD` public links.

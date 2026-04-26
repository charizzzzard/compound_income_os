# Landing Page Deployment Dry Run

Date: 2026-04-26
Commit: `2c082dbfc4521f5996b5dfaa5c666d864e33604e`

## Build

Build command:

```bash
npm run build
```

Local production preview command:

```bash
npm run preview:host
```

The generated static publish directory is:

```text
dist/
```

Expected hosting mode: static site.

For host integrations, use publish directory `dist`.

## Deployment Package

Generated deployment ZIP:

```text
website/compound-income-os-landing/deploy_artifacts/compound-income-os-landing-dist_20260426-203648_2c082db.zip
```

SHA256:

```text
40544F8F2D0428A8D8D8539170904083802BC53C3F02CF7CEE6A6CCA1AE63809
```

The deployment ZIP contains only `dist/index.html`, `dist/assets/*`, and `DEPLOYMENT_NOTES.txt`.

## CTA Configuration

CTA URLs are still placeholders unless deployment-specific `VITE_*` environment variables are configured.

Configured optional variables:

```text
VITE_EARLY_ACCESS_URL
VITE_GITHUB_ACCESS_URL
VITE_SETUP_SERVICE_URL
VITE_GITHUB_URL
VITE_SPONSORS_URL
VITE_PRIVACY_URL
VITE_IMPRINT_URL
```

Do not commit local `.env` files.

## Claim Guardrails

Compound Income OS is a research and decision-support tool. It does not provide investment advice and does not execute orders or connect to brokerages.

No secrets were used for this dry run.

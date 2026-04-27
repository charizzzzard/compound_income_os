# Website Static Build Package QA

## Executive Summary

- Static build QA status: `PASS`
- Build status: `PASS`
- Lint status: `PASS`
- Screenshots status: `PASS`
- Preview status: `PASS`
- Public deploy performed: `False`

## Repo / Website Inputs

- Website directory: `website/compound-income-os-landing`
- Vite base setting: `relative` (`VITE_BASE_RELATIVE`)
- Build script: `yes`
- Lint script: `yes`
- Screenshots script: `yes`
- Preview host script: `yes`

## Build Validation

- `npm install`, `npm run build`, `npm run lint`, and `npm run screenshots` are validated outside this generator.
- The generator inspects the produced `dist/` folder and records package safety checks.

## Dist Artifact Inspection

| Check | Status | Details |
|---|---:|---|
| `dist_exists` | `PASS` | True |
| `dist_index_exists` | `PASS` | True |
| `asset_paths_static_safe` | `PASS` | Asset paths are relative/static handoff-safe |
| `no_dev_entry_in_dist` | `PASS` | True |
| `no_env_files_in_dist` | `PASS` | 0 |
| `no_node_modules_in_dist` | `PASS` | 0 |
| `no_private_raw_paths_in_dist` | `PASS` | True |
| `no_private_sec_identity_markers_in_dist` | `PASS` | True |
| `no_private_values_in_dist` | `PASS` | True |
| `sample_payload_in_dist` | `PASS` | True |
| `main_routes_build_safe` | `PASS` | SPA route tokens present in built bundle |
| `direct_url_route_risk_documented` | `PASS` | Direct static URL fallback requires host rewrite support for SPA routes; documented as private-preview review item. |
| `public_launch_blockers_documented` | `PASS` | True |
| `no_public_deploy_performed` | `PASS` | No deploy command, hosting config, DNS change, or CI/CD publication was performed by this QA. |
| `static_package_created` | `PASS` | C:\Users\sc_mprinsen\Documents\compound_income_os\website\compound-income-os-landing\deploy_artifacts\compound-income-os-landing-private-preview-dist_20260427_d5146b7.zip |
| `static_package_forbidden_entries` | `PASS` | 0 |

## Route / SPA Fallback Review

- Built SPA route tokens are checked in `dist/`.
- Direct URL routes such as `/workflow`, `/evidence`, `/portfolio`, `/dashboard`, `/manifesto`, and `/about` require host fallback behavior when served outside Vite preview.
- No public rewrite or hosting configuration was added.

## Local Preview QA

- Preview status: `PASS`
- Existing `preview:host` script is used for local-only preview QA when run.

## Static Review Package

- Package path: `C:\Users\sc_mprinsen\Documents\compound_income_os\website\compound-income-os-landing\deploy_artifacts\compound-income-os-landing-private-preview-dist_20260427_d5146b7.zip`
- Package SHA256: `DB55D3E9883B02D9A3FEE8EF2B548D4F08BAC72F5710C4532A8EC58B52F7CEFF`
- Package file count: `6`
- Package forbidden entries: `0`
- Package is private-review only and is not included in the repo handoff ZIP.

## Public Launch Blockers

- Imprint and privacy URLs must be configured before public launch.
- CTA targets, pricing/scope, route fallback behavior, and payload privacy checks must be revalidated before any public deployment.
- No public deployment is performed by this QA.

## Privacy / Advice / Dummy Claim Guardrails

- Private data leak detected: `False`
- Dummy claims detected: `False`
- The build remains private-preview only and does not provide investment, tax, or legal advice.

## Handoff Impact

- Static build QA CSVs and this report are allowlisted for repo handoff export.
- `dist/` and `deploy_artifacts/` remain excluded from repo handoff.

## Remaining Review Items

- Direct URL route fallback must be rechecked against any future public host.
- Public launch blockers intentionally remain active.

## Recommended Next Patch

`PATCH / WEBSITE PRIVATE PREVIEW FINAL REVIEW / PRODUCT COPY FREEZE / NO SCOPE EXPANSION`

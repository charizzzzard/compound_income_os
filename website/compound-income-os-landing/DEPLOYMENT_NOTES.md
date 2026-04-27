# Deployment Notes - Compound Income OS Landing Page

This page is currently a **private preview build**. It is intended for internal review and limited demo handoffs only. It is **not** ready for public deployment.

### Mockup Master Plan v4 - Wave 1

This private-preview build contains only the first implementation wave of the website mockup plan. It is not a full public marketing site.

Implemented:
- Home wayfinder
- Workflow page
- Monthly Decision Report mockup
- Local Dashboard Viewer mockup

Not yet fully implemented:
- Evidence page
- Portfolio page
- Dashboard page
- Manifesto / Access page

The build remains blocked for public launch until real CTA targets, imprint, privacy policy, pricing/scope, and public-launch review are complete.

## Public Launch Blockers

The following items are required before any public deploy. Each blocker has both a legal/compliance and a credibility dimension.

### 1. Imprint

- Legal requirement in DE/EU.
- Configure `VITE_IMPRINT_URL` in environment.
- Until set, the footer renders the "Imprint" link as a non-clickable, dimmed label with a "Pending - required before public launch" tooltip.

### 2. Privacy policy

- Required by GDPR and equivalent regimes.
- Configure `VITE_PRIVACY_URL` in environment.
- Until set, the footer renders the "Privacy" link with the same dimmed pending state.

### 3. Real CTA targets

- `VITE_SAMPLE_REPORT_URL` - destination for "See the sample monthly report".
- `VITE_EARLY_ACCESS_URL` - destination for "Request private preview" on the Pro Modules card.
- `VITE_SETUP_SERVICE_URL` - destination for "Request setup" on the Setup Service card.
- `VITE_GITHUB_URL` - repository link for header, secondary final CTA, and Open-Source Core card.
- The current build **never** falls back to `mailto:early-access@example.invalid` or any other placeholder address. Unset URLs render as honest pending states.

### 4. Pricing and scope

- Pro Modules: pricing currently rendered as `Pricing TBD - Private preview`. Replace with real pricing or a real preview-list URL before any public sales surface.
- Setup Service: pricing currently rendered as `Pricing on request - Private preview`. Define scope before any public sales surface.

### 5. No public deploy performed

- No CI/CD pipeline targeting a public domain is currently configured.
- No DNS records have been pointed at this build.

### 6. Synthetic demo values only

- Every KPI, chart line, and dashboard number on the page is synthetic and explicitly labeled `synthetic demo values`.
- No real portfolio, broker, or fundamentals data is rendered.

### 7. Not investment, tax, or legal advice

- The product is a research and decision-support system. It does not connect to brokerages, does not execute orders, and does not provide personalized recommendations.
- The footer disclaimer must remain visible on any public version.

## Allowed deployment surfaces current build

- Local development server.
- Private review handoffs.
- Internal stakeholder demos with explicit private-preview framing.

## Disallowed deployment surfaces current build

- Public domain.
- Public marketing channels.
- Any surface where the page could be indexed by search engines or shared as a launched product.

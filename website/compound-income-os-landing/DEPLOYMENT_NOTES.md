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

## Wave Two Evidence Page

The `/evidence` page is a private-preview marketing and product-UI mockup. All holdings, values, statuses, and proposed updates are synthetic demo values.

The page does not perform SEC network access, does not expose private identity maps, and does not apply evidence updates. It visualizes the intended evidence workflow only.

### Wave Two-B - Local Dashboard page

The `/dashboard` page is a private-preview marketing mockup backed by sanitized local readiness artifacts and synthetic demo visuals.

It must not be presented as:
- a live public portfolio dashboard
- investment advice
- tax advice
- a forecast
- a brokerage or order execution interface

Before public launch, all CTA targets, imprint/privacy, pricing/scope, and payload privacy checks must be revalidated.

### Wave Three - Portfolio Model page

The `/portfolio` page is a private-preview marketing mockup. All allocations, rule bands, holding states, and concentration examples are synthetic or illustrative.

It must not be presented as:
- personal portfolio allocation guidance
- investment advice
- an execution signal
- a brokerage interface

Before public launch, all CTA targets, imprint/privacy, pricing/scope, and payload privacy checks must be revalidated.

### Wave Four - Manifesto / Access page

The `/manifesto` page is a private-preview marketing page. It frames the product principles, audience, access model, and public-launch blockers.

It must not be presented as:
- a public launch
- a legal/compliance-complete website
- investment advice
- a brokerage or order execution interface
- a finished SaaS pricing page

Before public launch, all CTA targets, imprint/privacy, pricing/scope, and payload privacy checks must be revalidated.

### Private Preview Route Matrix QA

The website route matrix must pass before any private demo handoff:

- all main routes render
- header navigation targets real routes or honest pending states
- unset external CTAs do not become fake links
- imprint/privacy remain pending unless configured
- no private raw paths or values appear in website files
- no page implies decision readiness or public launch readiness

### Static build package QA

The static build can be used for private review only.

Before any public deployment:

- verify imprint and privacy URLs
- verify real CTA targets
- verify pricing/scope language
- verify route fallback behavior for direct URLs
- verify no private raw data or environment files are included
- verify no page implies decision readiness or investment advice

No public deployment is performed by the build or QA process.

### Private Preview Copy Freeze

Before any private demo handoff, the website copy-freeze checks must pass or explicitly document review items.

The freeze does not mean public launch readiness. Public launch still requires real CTA targets, imprint, privacy policy, pricing/scope review, hosting/rewrite validation, and final compliance review.

### Private Preview Release Notes

The private-preview release notes are a handoff aid only. They do not indicate public launch readiness.

Public launch still requires:

- real CTA targets
- imprint URL
- privacy policy URL
- pricing/scope review
- hosting and route-fallback validation
- final compliance review.

### Private Preview Final Handoff QA

The final handoff QA validates the private-preview ZIP contents. It does not indicate public launch readiness.

Public launch still requires real CTA targets, imprint/privacy URLs, pricing/scope review, production hosting route fallback validation, and final compliance review.

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
- The current build **never** falls back to placeholder email addresses or fake public links. Unset URLs render as honest pending states.

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

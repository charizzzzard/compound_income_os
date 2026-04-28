TASK TYPE: PATCH / WEBSITE MICROCOPY CONSISTENCY / COMPLIANCE-SAFE UX COPY / MINIMAL-INVASIVE

REPO CONTEXT
Project: compound_income_os
Website scope: Compound Income OS landing website.
Expected website path may be:
- website/compound-income-os-landing/
But first inspect the repo and confirm the real file layout.

GOAL
Implement the final microcopy and visual-consistency pass from the Wave 5 Mockup Review.

This is NOT a redesign.
Do NOT add new pages.
Do NOT add new product capabilities.
Do NOT add new sections unless already present in the page structure.
Do NOT refactor broadly.
Do NOT introduce fake claims, fake testimonials, fake partner logos, real company logos, broker/trading language, or recommendation language.

The website should clearly position Compound Income OS as:

“A calm local portfolio review system that shows what changed, what is missing, what needs attention, and keeps the reasoning.”

It must NOT feel like:
- a broker
- a trading app
- a stock recommendation engine
- a robo-advisor
- a performance promise
- a generic finance dashboard

A. REPO REALITY CHECK

1. Print:
   - repo root
   - current branch
   - HEAD
   - git status --short
   - website package path
   - relevant files found

2. Inspect before editing:
   - website package.json
   - src/App.jsx or equivalent page file
   - src/siteConfig.js if present
   - main CSS file(s), e.g. src/App.css, src/landing.css, src/index.css
   - existing components / helpers such as SmartLink, Pill, SloganBar, Footer, Section components

3. Do not overwrite unrelated dirty work.
4. If the worktree is dirty, only modify files needed for this patch and clearly report which files were touched.

B. PATCH SCOPE

Implement exactly this patch wave:

1. Status-pills and labels:
   - Replace NEEDS REVIEW with REVIEW where it is a strict status pill.
   - Replace TOO EARLY with NOT_APPLICABLE or NOT YET DUE.
   - Prefer repo-/briefing-safe status language:
     COVERED
     PARTIAL
     REVIEW
     MISSING
     NOT_APPLICABLE
     OK
   - For human-facing explanatory copy, phrases like “Needs review” may be used in prose, but not as the canonical status pill if a status system is being shown.

2. CTA consistency:
   - Header CTA across all pages:
     Open sample
   - Main hero CTA across pages:
     Open sample review packet
   - Secondary CTAs:
     See how it works
     View the evidence trail
     Explore the local dashboard
   - Manifesto hero must NOT use “Get early access” as the primary hero CTA.
   - Keep “Request early access” or similar only inside the Private Preview access card.

3. Portfolio page visual source of truth:
   - Use the colored Portfolio Allocation treatment as canonical:
     Core ETF = blue
     Dividend Quality ETF = green
     Single Stock = gold/yellow
     Cash = purple
   - Preserve:
     dark Portfolio Allocation panel
     synthetic demo values pill
     rule limits row
     “Framework only · not allocation advice”
   - Ensure CSS variables exist for sleeve colors, for example:
     --sleeve-core
     --sleeve-quality
     --sleeve-stock
     --sleeve-cash
   - Do not turn the whole site colorful. Use sleeve colors sparingly outside Portfolio.

4. Portfolio Attention Queue:
   - Use synthetic holdings only:
     CORE ETF
     QUALITY ETF
     ATLAS
     NOVA
     RIVER
     CASH BUFFER
   - Remove real tickers and real company names.
   - Avoid:
     Buy
     Sell
     Do Not Buy
     Candidate
     Core holding
     Target allocation
     Fair value range
   - Replace:
     Fair value range -> Within review range
     Review threshold -> Review point OR Watch context
   - Reduce repeated “Within range” pills if they clutter the default state.
     Either:
     a) omit pills for default/in-range cells, or
     b) use a shorter OK / Within label consistently.
   - Keep safe labels:
     Within range
     Within review range
     REVIEW
     Watch context
     Review point
     Valuation stretched
     Outside current rules
     Keep context
     Ready for review
     Complete
     Partial

5. Evidence page:
   - Keep the page mostly unchanged.
   - Replace status pill NEEDS REVIEW -> REVIEW.
   - Replace TOO EARLY -> NOT_APPLICABLE or NOT YET DUE.
   - Replace “Check valuation context” with “Open valuation context” if used as a next-step/action label.
   - Replace prominent “SEC filings” wording with:
     official filings
     official numbers
   - Keep:
     “Nothing is silently filled.”
     “Review confidence becomes clearer when evidence is visible.”
   - Ensure no phrase says “You can rely on it.”
     Replace with:
     Complete enough for review.

6. Workflow page:
   - Resolve duplication between the dark Review Flow panel and the six stage cards.
   - Preferred minimal fix:
     Keep the six stage cards as the main workflow explanation.
     Keep the dark Review Flow panel only as a compact status snapshot, not a duplicate full explanation.
   - Make stage count consistent where practical.
     If keeping 5 dark-panel rows and 6 cards, make the dark panel clearly a “status snapshot”, not “the complete workflow”.
   - Stage labels:
     01 Bring in your portfolio
     02 Clean and normalize the data
     03 Check evidence
     04 Build the attention queue
     05 Write the review packet
     06 Keep the context
   - Proof labels:
     Portfolio Snapshot
     Clean Portfolio View
     Evidence Trail
     Attention Queue
     Review Packet
     Context Archive
   - Make stage icons neutral ink/black rather than all blue, so blue remains semantically tied to Core/Structure on Portfolio.
   - Synchronize Review Packet date with Home.
     Use either Apr 2026 everywhere or May 2026 everywhere.
     Preferred: Apr 2026 for Review Packet and archive demo.
   - Avoid:
     price targets
     guidance
     margin drivers
     growth trend
     decision rules if advisory
     buy/sell/trade/recommendation
     what to act on

7. Home page:
   - Preserve hero:
     A calmer way to run a long-term portfolio.
   - Keep:
     See what changed.
     See what’s missing.
     Keep the reasoning.
   - Keep:
     Broker apps show positions. Spreadsheets hold data. Compound Income OS keeps the reasoning.
   - Replace “Review evidence” card title with:
     Check the evidence
     or:
     Review the evidence
   - Ensure the problem card says:
     A review can look complete even when important numbers are missing.
   - Supporting copy:
     Critical inputs can be incomplete even when a review looks clear.
   - Make the three Review Snapshot status pills stylistically consistent:
     Option A:
       WITHIN RANGE
       REVIEW
       READY
     Option B:
       OK
       REVIEW
       READY FOR REVIEW
   - Prefer Option A unless current implementation already has a clean pattern.
   - Home feature cards should either:
     a) be clickable links to related pages, or
     b) visually read as feature cards, not page-nav cards.
   - Do not add a new section.

8. Dashboard page:
   - Preserve:
     One local dashboard. The full picture.
     Where do I stand?
     What changed?
     What needs attention?
     LOCAL VIEW ONLY · READ-ONLY · NO CLOUD
   - Replace defensive trust-box:
     Not another portfolio tracker. A review system for the decisions behind your portfolio.
   - With positive wording:
     A review console for the decisions behind your portfolio.
   - Keep no-trades/no-execution language.
   - Replace or neutralize YTD demo performance value:
     Avoid prominent red negative underperformance.
     Use neutral value such as:
       0.00%
       +0.00%
       Historical comparison
     Or keep the value only if visually de-emphasized and clearly labelled:
       Historical comparison only
       Not a forecast
   - Reduce visual density in lower module row:
     Use fewer chart types.
     Remove or simplify the Cost/Tax donut chart if it creates chart-demo feel.
     Prefer number KPI + short context text.
   - Keep only 2 visual chart styles if practical:
     bar chart for income history
     line chart for historical comparison
   - Avoid:
     score
     rating
     ratings changed
     annual growth
     outperforming
     forecast
   - Use:
     Review completeness
     Quality context
     Review status changed
     Income history

9. Manifesto page:
   - Keep mostly unchanged.
   - Hero primary CTA:
     Open sample review packet
   - Keep Private Preview access card with request-access CTA.
   - Keep:
     Built for people who think for the long run.
     I built this because spreadsheets kept the data, but not the reasoning.
   - Shorten slogan/footer bar to 4–5 items:
     BUILT FOR INVESTORS, NOT TRADERS
     PRIVACY BY DEFAULT
     NO HYPE
     JUST SIGNAL
   - Optional fifth:
     EVIDENCE OVER OPINION
   - Avoid a 7-item footer wall.

10. Date consistency:
   - Do not mix May 2026 on Home and Apr 2026 on Workflow.
   - Use one demo period across Review Packet surfaces.
   - Preferred:
     Apr 2026
     month_01
     generated 12 days ago
   - Avoid future-looking exact dates where possible.
   - Prefer relative demo language:
     generated 12 days ago
     last review 12 days ago

C. COPY STRINGS TO CENTRALIZE

If siteConfig.js exists, add or extend a central copy object.
Do not duplicate these strings across pages if avoidable.

Suggested structure:

siteConfig.copy = {
  taglineHero: 'A calmer way to run a long-term portfolio.',
  reasoningStatement: 'Spreadsheets hold data. Compound Income OS keeps the reasoning.',
  reasoningStatementFull: 'Numbers change. Context compounds. Keep the story behind the numbers.',
  notAdviceLine: 'Framework only · not allocation advice.',
  syntheticDemoPill: 'SYNTHETIC DEMO VALUES',
  ctaHeader: 'Open sample',
  ctaSamplePrimary: 'Open sample review packet',
  ctaSeeWorkflow: 'See how it works',
  ctaEvidenceTrail: 'View the evidence trail',
  ctaDashboard: 'Explore the local dashboard',
  ctaEarlyAccess: 'Request early access'
}

If existing naming differs, adapt minimally to the current code style.

D. CSS / VISUAL PATCHES

1. Add or reuse sleeve CSS variables:
   --sleeve-core
   --sleeve-quality
   --sleeve-stock
   --sleeve-cash

2. Ensure Portfolio Allocation uses:
   blue core icon/bar
   green quality icon/bar
   gold single-stock icon/bar
   purple cash icon/bar

3. Workflow stage icons:
   neutral ink/black, not all blue.

4. Dashboard:
   reduce lower-chart clutter.
   keep whitespace.
   keep review-console feel.

5. Footer slogan:
   shorten as specified.

E. VALIDATION

Run the project’s real checks.
First inspect package.json and use the available scripts.

At minimum, if this is a Vite site:
   npm install only if needed and dependencies are missing
   npm run build

Also run:
   git diff --check

Add lightweight grep checks if practical:

Check forbidden terms do not appear in prominent page copy:
   Buy
   Sell
   Do Not Buy
   Strong Buy
   price target
   target allocation
   fair value range
   outperforming
   expected return
   best ideas
   ratings changed
   annual growth
   TOO EARLY
   NEEDS REVIEW

Note:
- “buy” may appear inside unrelated package files or dependencies; restrict grep to src/ if needed.
- If a forbidden string appears in an intentional internal comment, report it and explain why it is safe.

Check approved synthetic names only:
   ATLAS
   NOVA
   RIVER
   HELIO
   CORE ETF
   QUALITY ETF
   CASH BUFFER

Ensure these do NOT appear in website source:
   MSFT
   JNJ
   KO
   Visa
   Microsoft
   Johnson
   Coca-Cola
   INDX
   STBL

F. OUTPUT FORMAT

Return:

1. REPO REALITY
   - repo root
   - branch
   - HEAD before
   - HEAD after
   - relevant dirty files before/after

2. IMPLEMENTED CHANGES
   - files changed
   - short summary of copy changes
   - short summary of visual changes
   - mention if no layout redesign was done

3. EXACT FIX MAP
   Include a compact table:
   old wording -> new wording
   e.g.
   NEEDS REVIEW -> REVIEW
   TOO EARLY -> NOT_APPLICABLE
   Fair value range -> Within review range
   Get early access hero -> Open sample review packet

4. VALIDATION
   - npm/build command result
   - git diff --check result
   - grep checks result
   - any screenshot/script result if available

5. REVIEW NOTES
   - anything intentionally left unchanged
   - any copy that could not be changed because it was not present in the current repo
   - any existing dirty/unrelated files left untouched

IMPORTANT
Do not broaden the task.
Do not implement new feature sections.
Do not invent new claims.
Do not add new data.
Do not add pricing.
Do not add testimonials.
Do not add partner logos.
Do not modify backend, scoring, fundamentals, SEC, portfolio engines, or data pipelines.
This is a website microcopy and visual consistency patch only.
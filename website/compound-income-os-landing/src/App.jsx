import wordmarkInk from './assets/wordmark-ink.svg'
import wordmarkPaper from './assets/wordmark-paper.svg'
import { siteConfig } from './siteConfig'

const navItems = [
  ['Workflow', '#workflow'],
  ['Evidence', '#evidence'],
  ['Access', '#access'],
  ['GitHub', siteConfig.links.github],
]

const heroKpis = [
  ['Portfolio Value', '€128,420', 'ok', 'OK'],
  ['Dividend Growth 5Y', '7.8%', 'ok', 'COVERED'],
  ['Cash Weight', '8.4%', 'ok', 'OK'],
  ['Monthly Candidate', 'REVIEW', 'review', 'REVIEW'],
]

const dashboardKpis = [
  ['Portfolio Value', '€128,420', 'Synthetic demo value', 'ok', 'OK'],
  ['Cash Weight', '8.4%', 'Reserve inside rule band', 'ok', 'OK'],
  ['Positions', '24', 'Within target range', 'ok', 'OK'],
  ['Top 5 Weight', '38.7%', 'Within concentration cap', 'ok', 'OK'],
  ['Dividend Income TTM', '€3,240', 'Synthetic demo value', 'ok', 'COVERED'],
  ['Dividend Growth 5Y', '7.8%', 'Synthetic demo value', 'ok', 'COVERED'],
  ['Data Quality', 'PARTIAL', 'Review needed', 'partial', 'PARTIAL'],
  ['Monthly Candidate', 'REVIEW', 'Review required', 'review', 'REVIEW'],
  ['Valuation Band', 'Fair / Watch', 'Valuation review', 'review', 'REVIEW'],
  ['Review Flags', '2', 'Open artifacts', 'review', 'REVIEW'],
]

const principles = [
  ['Local-first', 'Runs from local files and emits local CSV and Markdown artifacts.'],
  ['Privacy-first', 'Raw portfolio inputs remain under user control and separate from processed outputs.'],
  ['No cloud lock-in', 'Core workflow is portable files and code. No cloud account required.'],
  ['Decisions, not orders', 'The system documents, ranks, and reports. It never executes orders or connects to a brokerage.'],
  ['Evidence-only', 'Missing data stays visible. Values are never guessed or silently imputed.'],
  ['Reproducible by design', 'Every run records inputs, manifests, and generated artifacts for later review.'],
]

const workflowSteps = [
  ['Broker export in', 'Normalize local position files into a snapshot artifact.'],
  ['Data quality check', 'Gate holdings with explicit coverage and profile statuses.'],
  ['Scoring & ranking', 'Compute rule-based candidate scores from available evidence.'],
  ['Dividend impact', 'Show synthetic scenario contribution under declared assumptions.'],
  ['Monthly decision report', 'Explain candidate status, blockers, and data gaps in Markdown.'],
  ['Decision journal', 'Preserve the reasoning beside the run artifacts - month after month.'],
]

const primaryModules = [
  [
    'Watchlist & Monthly Ranking',
    'A cash-aware queue of candidates, ordered by transparent rule-based scores. Blockers, review states, and concentration limits stay visible.',
  ],
  [
    'Monthly Decision Report',
    'One Markdown artifact per run. Explains the current candidate, the blockers, the data gaps, and the reasoning under your current rule set.',
  ],
  [
    'Decision Journal & Local Dashboard',
    'A re-readable record of every monthly decision, alongside a local KPI dashboard that consolidates processed artifacts.',
  ],
]

const evidenceLayers = [
  ['Portfolio Snapshot', 'Local position snapshot with allocation and concentration context.'],
  ['SEC Evidence Pipeline', 'Read-only SEC CompanyFacts path for reviewed eligible US stock identities.'],
  ['Evidence-Applied Fundamentals', 'A separate evidence-applied master that preserves traceability.'],
  ['Data Quality Gates', 'Status labels (COVERED, PARTIAL, REVIEW, MISSING_DATA) as first-class outputs.'],
  ['Dividend Snowball Scenarios', 'Reproducible income scenarios under declared assumptions. Not a forecast.'],
]

const secStages = [
  ['Reviewed identity inputs', 'You confirmed the ticker matches the SEC filer.'],
  ['SEC CompanyFacts snapshot', "A read-only copy of the SEC's filed numbers."],
  ['Evidence registry', 'An index of which fields came from where.'],
  ['Research backlog', 'Things flagged for human review.'],
  ['Proposed updates', 'Changes waiting for your approval.'],
]

const statusExplanations = [
  ['COVERED', 'Required evidence is present and current.', 'ok'],
  ['PARTIAL', 'Some required fields are missing or stale.', 'partial'],
  ['REVIEW', 'Human decision pending before this can score.', 'review'],
  ['NO_MATCH', 'Identity could not be linked to a filer.', 'partial'],
  ['MISSING_DATA', 'Field is not available; not silently filled.', 'missing'],
  ['INSUFFICIENT_INPUTS', 'Not enough fields to compute a meaningful score.', 'partial'],
  ['INSUFFICIENT_HISTORY', 'Not enough time series for this metric.', 'partial'],
]

const audienceItems = [
  ['Dividend-growth investors', 'You care about a multi-year compounding thesis, not a quarterly trading idea.'],
  ['Quality-compounder investors', 'You want evidence-led conviction on fewer, higher-quality positions.'],
  ['Independent operators', 'You run your own research and want a deterministic, local workflow.'],
]

const accessCards = [
  {
    title: 'Open-Source Core',
    price: 'Free - Open-source',
    body: 'Local pipeline for positions, fundamentals, watchlist ranking, monthly ranking, reports, and dashboard artifacts.',
    label: 'View the workflow',
    href: siteConfig.links.github || '#workflow',
    pending: !siteConfig.links.github,
  },
  {
    title: 'Pro Modules',
    price: 'Pricing TBD - Private preview',
    body: 'Optional local extensions for deeper evidence review, scenario inspection, and additional dashboards.',
    label: siteConfig.ctas.earlyAccess.label,
    href: siteConfig.ctas.earlyAccess.href,
    pending: !siteConfig.ctas.earlyAccess.href,
    pendingPill: siteConfig.ctas.earlyAccess.pendingPill,
  },
  {
    title: 'Setup Service',
    price: 'Pricing on request - Private preview',
    body: 'Guided setup, local environment preparation, input mapping, and first reproducible run support.',
    label: siteConfig.ctas.setupService.label,
    href: siteConfig.ctas.setupService.href,
    pending: !siteConfig.ctas.setupService.href,
    pendingPill: siteConfig.ctas.setupService.pendingPill,
  },
]

function Pill({ tone = 'partial', children }) {
  return <span className={`pill pill-${tone}`}>{children}</span>
}

function PendingPill({ children }) {
  return <span className="pending-pill">{children}</span>
}

function SmartLink({ href, fallbackHref, className, children, pendingLabel, title, ...props }) {
  const targetHref = href || fallbackHref
  if (!targetHref) {
    return (
      <span className={`${className} is-disabled`} aria-disabled="true" title={title || pendingLabel} {...props}>
        {children}
      </span>
    )
  }
  const external = targetHref.startsWith('http')
  return (
    <a className={className} href={targetHref} target={external ? '_blank' : undefined} rel={external ? 'noreferrer' : undefined} title={title} {...props}>
      {children}
    </a>
  )
}

function Header() {
  return (
    <header className="fixed inset-x-0 top-0 z-50 border-b border-[color:var(--paper-300)] bg-[rgba(251,250,247,0.86)] px-5 py-3 backdrop-blur-xl sm:px-8">
      <nav className="mx-auto flex max-w-7xl items-center justify-between gap-4" aria-label="Main navigation">
        <a href="#top" className="rounded-md" aria-label={`${siteConfig.productName} home`}>
          <img src={wordmarkInk} alt={`${siteConfig.productName} wordmark`} className="h-7 w-auto" />
        </a>
        <div className="hidden items-center gap-7 md:flex">
          {navItems.map(([label, href]) =>
            href ? (
              <SmartLink key={label} href={href} className="text-sm font-medium text-[color:var(--ink-600)] hover:text-[color:var(--ink-900)]" title={!siteConfig.links.github && label === 'GitHub' ? siteConfig.ctas.githubAccess.pendingTooltip : undefined}>
                {label}
              </SmartLink>
            ) : (
              <span key={label} className="text-sm font-medium text-[color:var(--ink-400)]" title={siteConfig.ctas.githubAccess.pendingTooltip}>
                {label}
              </span>
            ),
          )}
        </div>
        <div className="hidden items-center gap-4 lg:flex">
          <SmartLink href={siteConfig.links.github} className="text-sm font-semibold text-[color:var(--ink-600)] hover:text-[color:var(--ink-900)]" title={siteConfig.ctas.githubAccess.pendingTooltip}>
            {siteConfig.ctas.githubAccess.label}
          </SmartLink>
          <SmartLink className="button button-primary px-4 py-2" href={siteConfig.ctas.earlyAccess.href} fallbackHref="#access" pendingLabel={siteConfig.ctas.earlyAccess.pendingPill}>
            {siteConfig.ctas.earlyAccess.headerLabel}
          </SmartLink>
        </div>
        <SmartLink className="button button-primary whitespace-nowrap px-4 py-2 text-xs md:hidden" href={siteConfig.ctas.earlyAccess.href} fallbackHref="#access" pendingLabel={siteConfig.ctas.earlyAccess.pendingPill}>
          {siteConfig.ctas.earlyAccess.shortLabel}
        </SmartLink>
      </nav>
    </header>
  )
}

function Hero() {
  return (
    <section id="top" className="section pt-32 lg:pt-40" data-screenshot="hero">
      <div className="container-xl grid items-center gap-12 lg:grid-cols-[0.95fr_1.05fr]">
        <div>
          <p className="eyebrow hero-eyebrow">Start with the workflow, not the trade.</p>
          <h1 className="mt-4 max-w-3xl text-5xl font-semibold leading-[1.02] tracking-[-0.055em] text-[color:var(--ink-900)] sm:text-6xl lg:text-7xl">
            {siteConfig.tagline}
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-[color:var(--ink-600)]">
            Compound Income OS turns your broker exports, fundamentals, and SEC evidence into one reproducible monthly
            decision report - locally, with every data gap visible.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <SmartLink className="button button-primary" href={siteConfig.ctas.sampleReport.href} fallbackHref={siteConfig.ctas.sampleReport.fallbackAnchor} pendingLabel={siteConfig.ctas.sampleReport.pendingPill}>
              {siteConfig.ctas.sampleReport.label}
            </SmartLink>
            <SmartLink className="button button-secondary" href={siteConfig.ctas.workflowAnchor.href}>
              {siteConfig.ctas.workflowAnchor.label}
            </SmartLink>
          </div>
          {!siteConfig.ctas.sampleReport.href && (
            <div className="mt-4">
              <PendingPill>Private preview - sample available on request</PendingPill>
            </div>
          )}
          <p className="mt-5 font-mono text-xs tracking-[0.04em] text-[color:var(--ink-500)]">
            Local-first - Open-source core - Evidence-based - No broker. No cloud.
          </p>
          <div className="mt-10 grid max-w-xl grid-cols-3 gap-4 border-t border-[color:var(--paper-300)] pt-5">
            {[
              ['Mode', 'Local files'],
              ['Outputs', 'CSV / Markdown'],
              ['Cadence', 'Monthly'],
            ].map(([label, value]) => (
              <div key={label}>
                <div className="eyebrow text-[10px]">{label}</div>
                <div className="mt-2 font-mono text-sm text-[color:var(--ink-800)]">{value}</div>
              </div>
            ))}
          </div>
        </div>
        <HeroDashboardPreview />
      </div>
    </section>
  )
}

function HeroDashboardPreview() {
  return (
    <aside className="dark-panel rounded-[1.35rem] border p-5 sm:p-6 lg:p-7" aria-label="Compact synthetic dashboard preview">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3 border-b border-[color:var(--dark-600)] pb-4">
        <div className="flex items-center gap-3">
          <span className="h-2.5 w-2.5 rounded-full bg-[color:var(--gold-300)] shadow-[0_0_0_4px_rgba(217,190,131,0.12)]" aria-hidden="true" />
          <span className="font-mono text-xs tracking-[0.06em] text-[color:var(--dark-fg-3)]">manifest - local run</span>
        </div>
        <Pill tone="partial">synthetic demo values</Pill>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        {heroKpis.map(([label, value, tone, pill]) => (
          <article className="kpi-card" key={label}>
            <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[color:var(--dark-fg-3)]">{label}</div>
            <div className="mt-3 font-mono text-2xl font-semibold tracking-[-0.03em] text-[color:var(--dark-fg)]">{value}</div>
            <div className="mt-4">
              <Pill tone={tone}>{pill}</Pill>
            </div>
          </article>
        ))}
      </div>

      <div className="mt-4 rounded-2xl border border-[color:var(--dark-600)] bg-[rgba(26,35,44,0.76)] p-4">
        <div className="flex items-center justify-between gap-4">
          <div>
            <div className="eyebrow text-[color:var(--dark-fg-3)]">compact chart</div>
            <div className="mt-2 font-mono text-sm text-[color:var(--dark-fg-2)]">Dividend income scenario - Not a forecast.</div>
          </div>
          <span className="font-mono text-xs text-[color:var(--dark-fg-3)]">DEMO-20260426</span>
        </div>
        <svg className="mt-4 h-28 w-full" viewBox="0 0 420 120" role="img" aria-label="Compact synthetic dividend income chart">
          {[24, 48, 72, 96].map((y) => (
            <line key={y} x1="0" x2="420" y1={y} y2={y} stroke="var(--dark-600)" strokeWidth="1" />
          ))}
          <path d="M0 92 C58 88 96 82 138 74 C198 62 230 66 286 48 C334 34 366 30 420 22" className="chart-line" />
          <path d="M0 92 C58 88 96 82 138 74 C198 62 230 66 286 48 C334 34 366 30 420 22 L420 120 L0 120 Z" fill="rgba(127,163,204,0.08)" />
        </svg>
      </div>

      <p className="mt-4 font-mono text-[11px] leading-5 text-[color:var(--dark-fg-3)]">
        OK = within rules - COVERED = evidence complete - REVIEW = pending decision - PARTIAL / MISSING_DATA = gaps stay visible (see Evidence)
      </p>
      <div className="artifact-strip mt-5 border-[color:var(--dark-600)] text-[color:var(--dark-fg-3)]">
        <span>run - manifest visible</span>
        <span>source - processed artifacts</span>
      </div>
    </aside>
  )
}

function DashboardPreview() {
  return (
    <section id="dashboard" className="section-tight" data-screenshot="dashboard">
      <div className="container-xl">
        <div className="dark-panel rounded-[1.35rem] border p-4 sm:p-6 lg:p-8" aria-label="Synthetic dashboard preview">
          <div className="mb-6 flex flex-wrap items-center justify-between gap-4 border-b border-[color:var(--dark-600)] pb-4">
            <div className="flex items-center gap-3">
              <img src={wordmarkPaper} alt="Compound Income OS dashboard wordmark" className="h-6 w-auto" />
              <span className="font-mono text-xs tracking-[0.06em] text-[color:var(--dark-fg-3)]">local - monthly run - synthetic demo</span>
            </div>
            <div className="flex flex-wrap gap-2">
              <Pill tone="partial">synthetic demo values</Pill>
              <span className="font-mono text-xs tracking-[0.04em] text-[color:var(--dark-fg-3)]">DEMO-20260426-160500</span>
            </div>
          </div>

          <div className="dashboard-grid">
            {dashboardKpis.map(([label, value, note, tone, pill]) => (
              <article className="kpi-card" key={label}>
                <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[color:var(--dark-fg-3)]">{label}</div>
                <div className="mt-3 font-mono text-2xl font-semibold tracking-[-0.03em] text-[color:var(--dark-fg)]">{value}</div>
                <div className="mt-4 flex flex-wrap items-center gap-2 text-xs text-[color:var(--dark-fg-3)]">
                  <Pill tone={tone}>{pill}</Pill>
                  <span>{note}</span>
                </div>
              </article>
            ))}
          </div>

          <div className="mt-5 grid gap-4 lg:grid-cols-[1.6fr_1fr]">
            <div className="rounded-2xl border border-[color:var(--dark-600)] bg-[rgba(26,35,44,0.76)] p-5">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <div className="eyebrow text-[color:var(--dark-fg-3)]">Subtle chart area</div>
                  <div className="mt-2 font-mono text-2xl font-semibold text-[color:var(--dark-fg)]">€3,240 TTM dividend income</div>
                  <p className="mt-2 text-sm text-[color:var(--dark-fg-2)]">Illustrative scenario - synthetic demo data</p>
                </div>
                <Pill tone="review">REVIEW</Pill>
              </div>
              <svg className="mt-7 h-36 w-full" viewBox="0 0 500 140" role="img" aria-label="Synthetic dividend income trend preview">
                {[22, 50, 78, 106, 134].map((y) => (
                  <line key={y} x1="0" x2="500" y1={y} y2={y} stroke="var(--dark-600)" strokeWidth="1" />
                ))}
                <path d="M0 112 C70 108 90 100 140 94 C210 85 230 70 290 66 C360 60 400 43 500 32" className="chart-line" />
                <path d="M0 112 C70 108 90 100 140 94 C210 85 230 70 290 66 C360 60 400 43 500 32 L500 140 L0 140 Z" fill="rgba(127,163,204,0.08)" />
              </svg>
            </div>
            <div className="rounded-2xl border border-[color:var(--dark-600)] bg-[rgba(26,35,44,0.76)] p-5">
              <div className="eyebrow text-[color:var(--dark-fg-3)]">Source and manifest indicators</div>
              <div className="mt-4 space-y-3">
                {[
                  ['manifest', 'personal_run_manifest.json'],
                  ['used inputs', 'personal_run_used_inputs.csv'],
                  ['source mode', 'EVIDENCE_APPLIED'],
                  ['artifact', 'monthly_decision_report.md'],
                ].map(([label, value]) => (
                  <div key={label} className="flex justify-between gap-4 border-b border-[color:var(--dark-600)] pb-3 font-mono text-xs">
                    <span className="text-[color:var(--dark-fg-3)]">{label}</span>
                    <span className="text-right text-[color:var(--dark-fg)]">{value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="artifact-strip mt-6 border-[color:var(--dark-600)] text-[color:var(--dark-fg-3)]">
            <span>artifact - positions_snapshot.csv</span>
            <span>artifact - company_scores.csv</span>
            <span>artifact - dashboard_kpis.csv</span>
            <span>manifest - deterministic local run</span>
          </div>
        </div>
      </div>
    </section>
  )
}

function ProblemSolution() {
  return (
    <>
      <section id="problem" className="section">
        <div className="container-xl">
          <p className="eyebrow">Problem</p>
          <h2 className="section-title">Where long-term portfolios actually break.</h2>
          <p className="section-lede">
            Research fragments over time. Watchlists drift. Reasons get lost. The monthly decision becomes an act of memory
            rather than evidence.
          </p>
          <div className="mt-10 grid gap-5 md:grid-cols-3">
            {[
              ['The watchlist no one updated.', 'Tickers added years ago, never reviewed since. The thesis is gone. The position is still in.'],
              ["The KPI that was missing.", "A score gets computed anyway. The decision rests on data that wasn't there. You don't notice until next quarter."],
              ["The decision you can't reconstruct.", '"Why did I buy that?" The reasoning was in your head. It\'s no longer there. The position is.'],
            ].map(([title, body], index) => (
              <article className="card" key={title}>
                <div className="font-mono text-sm text-[color:var(--accent-600)]">0{index + 1}</div>
                <h3 className="mt-4 text-xl font-semibold text-[color:var(--ink-900)]">{title}</h3>
                <p className="mt-3 text-sm leading-6 text-[color:var(--ink-600)]">{body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="section-tight bg-[color:var(--paper-100)]">
        <div className="container-xl">
          <p className="eyebrow">Solution</p>
          <h2 className="section-title">The portfolio as local infrastructure.</h2>
          <p className="section-lede">
            Compound Income OS treats the research workflow as a deterministic local pipeline: declared inputs in,
            reproducible artifacts out. Data quality, evidence status, and reasoning are first-class outputs at every step.
          </p>
        </div>
      </section>
    </>
  )
}

function Principles() {
  return (
    <section id="product" className="section">
      <div className="container-xl">
        <p className="eyebrow">Product principles</p>
        <h2 className="section-title">Architecture-level guardrails - not slogans.</h2>
        <div className="mt-10 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
          {principles.map(([title, body]) => (
            <article className="card" key={title}>
              <h3 className="text-xl font-semibold text-[color:var(--ink-900)]">{title}</h3>
              <p className="mt-3 text-sm leading-6 text-[color:var(--ink-600)]">{body}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}

function Workflow() {
  return (
    <section id="workflow" className="section-tight bg-[color:var(--paper-100)]">
      <div className="container-xl">
        <p className="eyebrow">Monthly workflow</p>
        <h2 className="section-title">Six stages. One monthly cadence. A growing archive.</h2>
        <p className="section-lede">
          Compound Income OS runs the same six stages every month - from broker export to decision journal - so that month
          12 looks like month 1, eleven times audited.
        </p>
        <div className="mt-10 grid gap-4 md:grid-cols-2 xl:grid-cols-6">
          {workflowSteps.map(([title, body], index) => (
            <article className="card relative min-h-48" key={title}>
              <div className="font-mono text-sm text-[color:var(--accent-600)]">0{index + 1}</div>
              <h3 className="mt-4 font-semibold text-[color:var(--ink-900)]">{title}</h3>
              <p className="mt-3 text-sm leading-6 text-[color:var(--ink-600)]">{body}</p>
            </article>
          ))}
        </div>
        <div className="mt-8 rounded-2xl border border-[color:var(--paper-300)] bg-white/60 p-5">
          <h3 className="font-mono text-sm font-semibold uppercase tracking-[0.12em] text-[color:var(--accent-600)]">The archive that compounds.</h3>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-[color:var(--ink-600)]">
            Each monthly run leaves one decision report, one journal entry, and one snapshot. Twelve runs become an auditable year.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            {['month_01/monthly_decision_report.md', 'month_06/monthly_decision_report.md', 'month_12/monthly_decision_report.md'].map((tag) => (
              <span className="rounded-full border border-[color:var(--paper-300)] bg-[color:var(--paper-50)] px-3 py-1 font-mono text-xs text-[color:var(--ink-600)]" key={tag}>
                {tag}
              </span>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

function CoreFeatures() {
  return (
    <section className="section">
      <div className="container-xl">
        <p className="eyebrow">Core features</p>
        <h2 className="section-title">One local pipeline. Three modules. Five evidence layers.</h2>
        <div className="mt-10 grid gap-5 lg:grid-cols-3" data-feature-group="primary-modules">
          {primaryModules.map(([title, body]) => (
            <article className="card" key={title}>
              <h3 className="text-xl font-semibold text-[color:var(--ink-900)]">{title}</h3>
              <p className="mt-3 text-sm leading-6 text-[color:var(--ink-600)]">{body}</p>
            </article>
          ))}
        </div>
        <div className="mt-6 grid gap-3 md:grid-cols-5" data-feature-group="secondary-evidence-layers">
          {evidenceLayers.map(([title, body]) => (
            <article className="rounded-2xl border border-[color:var(--paper-300)] bg-white/55 p-4" key={title}>
              <h3 className="text-sm font-semibold text-[color:var(--ink-900)]">{title}</h3>
              <p className="mt-2 text-xs leading-5 text-[color:var(--ink-600)]">{body}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}

function Snowball() {
  return (
    <section className="section-tight bg-[color:var(--paper-100)]" data-screenshot="dividend-snowball">
      <div className="container-xl grid gap-8 lg:grid-cols-[0.85fr_1.15fr]">
        <div>
          <p className="eyebrow">Dividend Snowball Analysis</p>
          <h2 className="section-title">Your dividend snowball, modeled honestly.</h2>
          <p className="section-lede">
            Run reproducible income scenarios from your own holdings, your own assumptions, and your own concentration caps.
            Every assumption is declared. Nothing is predicted.
          </p>
          <div className="mt-6">
            <Pill tone="review">Illustrative scenario - not a forecast</Pill>
          </div>
        </div>
        <div className="dark-panel rounded-3xl border p-6">
          <div className="grid gap-4 sm:grid-cols-2">
            {[
              ['Current Dividend Income TTM', '€3,240'],
              ['Candidate contribution', '€42 illustrative annualized'],
              ['Cash deployment assumption', '€300 reviewed amount'],
              ['Data quality', 'PARTIAL - review pending'],
            ].map(([label, value]) => (
              <div className="kpi-card" key={label}>
                <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[color:var(--dark-fg-3)]">{label}</div>
                <div className="mt-3 font-mono text-xl font-semibold text-[color:var(--dark-fg)]">{value}</div>
              </div>
            ))}
          </div>
          <svg className="mt-7 h-52 w-full" viewBox="0 0 640 220" role="img" aria-label="Illustrative future dividend income path">
            {[40, 80, 120, 160, 200].map((y) => (
              <line key={y} x1="0" x2="640" y1={y} y2={y} stroke="var(--dark-600)" />
            ))}
            <path d="M20 182 C120 172 170 150 250 138 C340 124 405 90 500 75 C560 66 600 50 620 42" stroke="var(--gold-300)" strokeWidth="3" fill="none" strokeLinecap="round" />
            <path d="M20 182 C120 172 170 150 250 138 C340 124 405 90 500 75 C560 66 600 50 620 42 L620 220 L20 220 Z" fill="rgba(217,190,131,0.1)" />
          </svg>
          <div className="artifact-strip border-[color:var(--dark-600)] text-[color:var(--dark-fg-3)]">
            <span>rule-based concentration caps</span>
            <span>reinvestment/manual scenario assumptions</span>
            <span>source - dividend_snowball.csv</span>
          </div>
        </div>
      </div>
    </section>
  )
}

function EvidenceAndQuality() {
  return (
    <section id="evidence" className="section" data-screenshot="evidence-quality">
      <div className="container-xl grid gap-8 lg:grid-cols-2">
        <article className="card">
          <p className="eyebrow">SEC Evidence Pipeline</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-[-0.03em] text-[color:var(--ink-900)]">Read-only. Reviewed. Optional.</h2>
          <p className="mt-4 leading-7 text-[color:var(--ink-600)]">
            For eligible US stocks, the system can pull fundamentals from SEC CompanyFacts - read-only, after manual
            identity review. The fundamentals master is never silently overwritten. Updates are staged, reviewed, and only
            then applied.
          </p>
          <div className="mt-6 space-y-3">
            {secStages.map(([title, body]) => (
              <div key={title} className="grid gap-2 border-b border-[color:var(--paper-300)] pb-3 sm:grid-cols-[0.55fr_1fr]">
                <span className="text-sm font-semibold text-[color:var(--ink-800)]">{title}</span>
                <span className="text-sm leading-6 text-[color:var(--ink-600)]">{body}</span>
              </div>
            ))}
          </div>
          <div className="mt-6 flex flex-wrap gap-2">
            <Pill tone="review">Review update</Pill>
            <Pill tone="partial">Stage update</Pill>
            <Pill tone="ok">Apply to evidence-applied master</Pill>
          </div>
        </article>

        <article className="card">
          <p className="eyebrow">Data Quality Gates</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-[-0.03em] text-[color:var(--ink-900)]">Missing data stays explicit.</h2>
          <p className="mt-4 leading-7 text-[color:var(--ink-600)]">
            Status labels are first-class outputs, not hidden implementation details. They keep monthly decisions from
            pretending incomplete evidence is complete.
          </p>
          <p className="mt-3 text-sm leading-6 text-[color:var(--ink-600)]">
            Conservative by default: incomplete evidence stays visible instead of being forced into a score.
          </p>
          <div className="mt-6 space-y-3">
            {statusExplanations.map(([status, body, tone]) => (
              <div key={status} className="grid gap-3 border-b border-[color:var(--paper-300)] pb-3 sm:grid-cols-[max-content_1fr]">
                <Pill tone={tone}>{status}</Pill>
                <span className="text-sm leading-6 text-[color:var(--ink-600)]">{body}</span>
              </div>
            ))}
          </div>
        </article>
      </div>
    </section>
  )
}

function JournalAudienceAccess() {
  return (
    <section className="section-tight bg-[color:var(--paper-100)]">
      <div className="container-xl grid gap-8 lg:grid-cols-2">
        <article className="card">
          <p className="eyebrow">Decision Journal</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-[-0.03em] text-[color:var(--ink-900)]">The record beside the run.</h2>
          <pre className="mt-6 overflow-x-auto rounded-2xl bg-[color:var(--dark-800)] p-5 font-mono text-xs leading-6 text-[color:var(--dark-fg-2)]">
{`run_id: DEMO-20260426-160500
monthly_candidate: REVIEW
candidate_allocation: €300 under current rule set
review_amount: €300 within concentration limit
blocker: valuation_data_status != OK
artifact: reports/demo/monthly_decision_report.md`}
          </pre>
        </article>
        <article className="card">
          <p className="eyebrow">Audience</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-[-0.03em] text-[color:var(--ink-900)]">Built for independent operators.</h2>
          <div className="mt-6 space-y-5 text-sm leading-6 text-[color:var(--ink-600)]">
            {audienceItems.map(([title, body]) => (
              <div key={title} className="border-b border-[color:var(--paper-300)] pb-4">
                <h3 className="font-semibold text-[color:var(--ink-900)]">{title}</h3>
                <p className="mt-1">{body}</p>
              </div>
            ))}
          </div>
          <div className="mt-6 rounded-2xl border border-[color:var(--paper-300)] bg-[color:var(--paper-50)] p-4">
            <div className="font-mono text-xs font-semibold uppercase tracking-[0.14em] text-[color:var(--accent-600)]">Not built for</div>
            <p className="mt-2 text-sm leading-6 text-[color:var(--ink-600)]">
              Day traders, options speculators, leveraged or crypto-driven strategies, signal subscribers, anyone seeking
              execution, hot tips, or personalized investment advice.
            </p>
          </div>
        </article>
      </div>
    </section>
  )
}

function Access() {
  return (
    <section id="access" className="section" data-screenshot="access">
      <div className="container-xl">
        <p className="eyebrow">Access</p>
        <h2 className="section-title">Open-source core. Optional help around the workflow.</h2>
        <div className="mt-10 grid gap-5 lg:grid-cols-3" data-access-card-count="3">
          {accessCards.map((card) => (
            <article className="card flex flex-col" key={card.title} data-access-card>
              <h3 className="text-xl font-semibold text-[color:var(--ink-900)]">{card.title}</h3>
              <div className="mt-2 font-mono text-sm text-[color:var(--gold-700)]">{card.price}</div>
              <p className="mt-4 flex-1 text-sm leading-6 text-[color:var(--ink-600)]">{card.body}</p>
              {card.pending && card.pendingPill ? (
                <div className="mt-6">
                  <span className="button button-secondary is-disabled" aria-disabled="true">
                    {card.label}
                  </span>
                  <div className="mt-3">
                    <PendingPill>{card.pendingPill}</PendingPill>
                  </div>
                </div>
              ) : (
                <SmartLink className="button button-secondary mt-6" href={card.href}>
                  {card.label}
                </SmartLink>
              )}
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}

function FooterLink({ label, href }) {
  if (!href) {
    return (
      <span className="footer-link-pending" aria-disabled="true" title="Pending - required before public launch">
        {label}
      </span>
    )
  }
  return (
    <a href={href} className="text-[color:var(--ink-600)] hover:text-[color:var(--ink-900)]" target="_blank" rel="noreferrer">
      {label}
    </a>
  )
}

function FinalCtaFooter() {
  const finalSecondaryLabel = siteConfig.links.github ? 'View the workflow on GitHub' : 'View the workflow'
  const finalSecondaryHref = siteConfig.links.github || '#workflow'

  return (
    <>
      <section id="early-access" className="section dark-panel border-y border-[color:var(--dark-600)]" data-screenshot="final-cta">
        <div className="container-xl max-w-4xl">
          <p className="eyebrow text-[color:var(--dark-accent)]">Final CTA</p>
          <h2 className="mt-4 text-4xl font-semibold tracking-[-0.04em] text-[color:var(--dark-fg)] sm:text-5xl">
            One reproducible decision a month. Locally. With evidence.
          </h2>
          <p className="mt-5 max-w-2xl text-lg leading-8 text-[color:var(--dark-fg-2)]">
            Get the sample monthly report or review the local-first workflow.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <SmartLink className="button button-primary" href={siteConfig.ctas.sampleReport.href} fallbackHref={siteConfig.ctas.sampleReport.fallbackAnchor} pendingLabel={siteConfig.ctas.sampleReport.pendingPill}>
              {siteConfig.ctas.sampleReport.label}
            </SmartLink>
            <SmartLink className="button button-quiet" href={finalSecondaryHref}>
              {finalSecondaryLabel}
            </SmartLink>
          </div>
        </div>
      </section>

      <footer className="section-tight" data-screenshot="footer">
        <div className="container-xl">
          <div className="rounded-3xl border border-[color:var(--paper-300)] bg-white/60 p-6 text-sm leading-7 text-[color:var(--ink-600)]">
            <p>
              <strong className="text-[color:var(--ink-900)]">{siteConfig.productName}</strong>
              {siteConfig.disclaimerShort.slice(siteConfig.productName.length)}
            </p>
            <details className="mt-4">
              <summary className="cursor-pointer font-semibold text-[color:var(--ink-800)]">Read full disclaimer</summary>
              <p className="mt-3">{siteConfig.disclaimer}</p>
            </details>
          </div>
          <div className="mt-8 flex flex-wrap items-center justify-between gap-4 text-xs text-[color:var(--ink-500)]">
            <img src={wordmarkInk} alt={`${siteConfig.productName} wordmark`} className="h-6 w-auto" />
            <span>No cloud account required. Core runs locally. No broker connection.</span>
          </div>
          <div className="mt-5 flex flex-wrap gap-x-5 gap-y-2 font-mono text-xs">
            <FooterLink label="Imprint" href={siteConfig.links.imprint} />
            <FooterLink label="Privacy" href={siteConfig.links.privacy} />
            <FooterLink label="GitHub" href={siteConfig.links.github} />
            <FooterLink label="GitHub Sponsors" href={siteConfig.links.sponsors} />
          </div>
        </div>
      </footer>
    </>
  )
}

export default function App() {
  return (
    <div className="site-shell">
      <Header />
      <main>
        <Hero />
        <DashboardPreview />
        <ProblemSolution />
        <Principles />
        <Workflow />
        <CoreFeatures />
        <Snowball />
        <EvidenceAndQuality />
        <JournalAudienceAccess />
        <div data-screenshot="access-disclaimer">
          <Access />
          <FinalCtaFooter />
        </div>
      </main>
    </div>
  )
}

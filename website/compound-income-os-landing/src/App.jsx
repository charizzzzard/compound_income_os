import { useEffect, useState } from 'react'

import wordmarkInk from './assets/wordmark-ink.svg'
import wordmarkPaper from './assets/wordmark-paper.svg'
import { siteConfig } from './siteConfig'

const safeRoutes = [
  ['Workflow', '/workflow', false],
  ['Evidence', '/evidence', false],
  ['Portfolio', '/portfolio', false],
  ['Dashboard', '/dashboard', false],
  ['Manifesto', '/manifesto', false],
]

const promises = [
  ['Workflow', 'One decision a month - same six stages, every month.', '/workflow', false],
  ['Evidence', 'Every KPI carries a status, and missing data remains visible.', '/evidence', false],
  ['Portfolio', 'Four sleeves. One mandate. Visible rules.', '/portfolio', false],
  ['Dashboard', 'One local dashboard. Five KPI groups.', '/dashboard', false],
  ['Manifesto / Access', 'Open-source core. Builder-led. No venture capital.', '/manifesto', false],
]

const workflowStages = [
  ['01', 'Import broker data', 'broker exports / CSV / PDF', 'import_broker + normalize_positions', 'positions_snapshot.csv'],
  ['02', 'Score holdings', 'positions + fundamentals master', 'scoring_engine', 'company_scores.csv + score_audit.csv'],
  ['03', 'Review evidence', 'SEC snapshots + manual evidence', 'SEC pipeline + evidence engines', 'evidence_registry.csv + evidence_applied_master.csv'],
  ['04', 'Rank watchlist and monthly candidates', 'watchlist + score artifacts', 'watchlist_engine + monthly_ranking_engine', 'watchlist_ranked.csv + monthly_buy_ranking.csv'],
  ['05', 'Generate the decision report', 'processed artifacts', 'build_monthly_decision_report', 'monthly_decision_report.md'],
  ['06', 'Journal it', 'report + run manifest', 'personal_run_engine', 'personal_run_manifest.json'],
]

const reportSections = [
  ['Monthly Decision Report', 'Run: DEMO-2026-04', 'REVIEW'],
  ['Candidate Review', '2 candidates require source review before use.', 'PARTIAL'],
  ['Blockers', 'Valuation and dividend / FCF inputs are missing.', 'MISSING_DATA'],
  ['Evidence Status', 'Core KPI closure queue is open; SEC refresh preflight is gated.', 'REVIEW'],
  ['Reasoning', 'No values are filled automatically. Missing inputs stay visible.', 'COVERED'],
  ['Output artifacts', 'monthly_decision_report.md, score_audit.csv, personal_run_manifest.json', 'OK'],
]

const dashboardGroups = [
  ['Portfolio / Structure', 'cash band visible', 'OK'],
  ['Score / Fundamentals', 'core review open', 'REVIEW'],
  ['Benchmark / Performance', 'history gate visible', 'PARTIAL'],
  ['Cost / Tax', 'ledger diagnostics only', 'PARTIAL'],
  ['Data Quality / Methodology', 'decision readiness blocked', 'MISSING_DATA'],
]

const readinessRows = [
  ['Demo readiness', 'BLOCKED', 'review'],
  ['Decision readiness', 'BLOCKED', 'missing'],
  ['Dashboard readiness', 'REVIEW', 'review'],
  ['Handoff readiness', 'REVIEW', 'partial'],
]

const dashboardReadinessMetrics = [
  ['Demo', 'BLOCKED', 'missing'],
  ['Decision', 'BLOCKED', 'missing'],
  ['Dashboard', 'REVIEW', 'review'],
  ['Handoff', 'REVIEW', 'partial'],
  ['Active blockers', '11', 'missing'],
  ['P0 blockers', '6', 'missing'],
  ['P1 reviews', '4', 'review'],
  ['Next actions', '5', 'partial'],
]

const dashboardKpiGroups = [
  ['Portfolio / Structure', ['total assets', 'cash weight', 'top-5 weight', 'sleeve weights'], 'synthetic / illustrative', 'PARTIAL'],
  ['Score / Fundamentals', ['business score', 'valuation status', 'quality flag', 'missing KPI blockers'], 'review gates visible', 'REVIEW'],
  ['Benchmark / Performance', ['benchmark comparison', 'rolling return', 'drawdown', 'volatility'], 'Requires explicit local benchmark archive. Not a prediction.', 'INSUFFICIENT_HISTORY'],
  ['Cost / Tax', ['gross dividends', 'net dividends', 'withholding taxes', 'tax drag'], 'Requires explicit cost/tax ledger evidence.', 'REVIEW'],
  ['Data Quality / Methodology', ['coverage', 'partial', 'review', 'missing data', 'methodology notes'], 'readiness payload and blocker matrix', 'MISSING_DATA'],
]

const portfolioSleeves = [
  ['Core ETF', 'Broad market foundation and long-term compounding base.', '45-60%', 'illustrative rule band', 'OK'],
  ['Dividend Quality ETF', 'Income-oriented diversification with quality and durability constraints.', '10-25%', 'illustrative rule band', 'PARTIAL'],
  ['Single Stock', 'Reviewed quality compounders and dividend-growth holdings with explicit evidence.', '20-35%', 'review required', 'REVIEW'],
  ['Cash', 'Optionality, drawdown buffer, and monthly deployment discipline.', '5-15%', 'rule-based reserve', 'OK'],
]

const portfolioWorkspaceRows = [
  ['Core ETF', 'synthetic', '45-60%', 'OK', 'within illustrative band'],
  ['Dividend Quality ETF', 'synthetic', '10-25%', 'PARTIAL', 'income evidence review open'],
  ['Single Stock', 'synthetic', '20-35%', 'REVIEW', 'valuation and evidence gates open'],
  ['Cash', 'synthetic', '5-15%', 'MISSING_DATA', 'cash source not connected'],
]

const portfolioRiskRules = [
  ['Max single position', 'illustrative limit', 'REVIEW'],
  ['Max top-10 weight', 'concentration visible', 'PARTIAL'],
  ['Max sector exposure', 'methodology gate', 'REVIEW'],
  ['Minimum cash reserve', 'rule-based reserve', 'OK'],
]

const portfolioGuardrails = [
  ['Concentration', 'Position and top-holding limits keep concentration visible.'],
  ['Sleeve discipline', 'Every holding belongs to a sleeve, not a vague watchlist bucket.'],
  ['Cash-aware decisions', 'Monthly candidate review considers cash context before any action is documented.'],
  ['Evidence gates', 'A holding can look attractive and still remain blocked if required evidence is missing.'],
  ['Review states', 'REVIEW, PARTIAL, and MISSING_DATA remain visible instead of being hidden behind a score.'],
]

const holdingStatuses = [
  ['Core candidate', 'Potential long-term fit, pending evidence and valuation review.'],
  ['Quality compounder', 'Strong business profile, but still subject to data quality and valuation gates.'],
  ['Dividend growth', 'Income thesis visible, but Dividend/FCF evidence must be reviewed.'],
  ['Too expensive', 'Good company, but valuation review blocks action.'],
  ['Review', 'Needs more data or manual evidence before it can support a decision.'],
  ['Reject', 'Does not meet the current rule set or evidence threshold. This is a review outcome, not an execution instruction.'],
]

const portfolioReadinessBlockers = [
  ['Decision readiness', 'BLOCKED', 'missing'],
  ['Valuation inputs', 'missing', 'missing'],
  ['Dividend / FCF inputs', 'missing', 'missing'],
  ['Core KPI review', 'open', 'review'],
  ['Provenance', 'incomplete', 'partial'],
  ['Watchlist', 'sample input active', 'missing'],
]

const manifestoPrinciples = [
  ['Local-first', 'Runs from local files and emits local artifacts you can inspect.'],
  ['Evidence-only', 'Missing data stays visible. Values are never guessed or silently filled.'],
  ['Process over impulse', 'The monthly workflow matters more than a one-off opinion.'],
  ['Decisions, not brokerage actions', 'The system documents, ranks, and reports. It never connects to a brokerage.'],
  ['Privacy by default', 'Raw portfolio inputs remain under user control and outside public handoffs.'],
  ['Reproducible by design', 'Runs leave manifests, reports, and artifacts that can be reviewed later.'],
]

const builtForCards = [
  ['Dividend-growth investors', 'You care about a multi-year compounding thesis, not a quarterly speculation idea.'],
  ['Quality-compounder investors', 'You want evidence-led conviction on fewer, higher-quality positions.'],
  ['Independent operators', 'You run your own research and want a deterministic, local workflow.'],
  ['Private portfolio builders', 'You want a monthly review system that respects your data and your machine.'],
]

const notBuiltForItems = [
  'intraday speculation workflows',
  'options speculation',
  'leveraged or crypto-driven strategies',
  'signal subscriptions',
  'hot tips',
  'brokerage connectivity',
  'personalized allocation guidance',
]

const publicLaunchBlockers = [
  ['Imprint', 'Required before public launch. Pending until VITE_IMPRINT_URL is configured.'],
  ['Privacy Policy', 'Required before public launch. Pending until VITE_PRIVACY_URL is configured.'],
  ['Real CTA targets', 'Sample report, private preview, setup, and GitHub targets must be real before public launch.'],
  ['Pricing and scope', 'Pro Modules and Setup Service need real scope before any public sales surface.'],
  ['Readiness state', 'Decision readiness is currently blocked in the sample payload. The page must not imply otherwise.'],
]

const snowballMetrics = [
  ['Current Dividend Income TTM', 'synthetic scenario', 'PARTIAL'],
  ['Candidate contribution', 'review pending', 'REVIEW'],
  ['Cash deployment assumption', 'declared input', 'PARTIAL'],
  ['Data quality', 'review pending', 'PARTIAL'],
]

const cashflowMonths = [
  ['Jan', 'Known'],
  ['Feb', 'Estimated'],
  ['Mar', 'Known'],
  ['Apr', 'Review'],
  ['May', 'Missing'],
  ['Jun', 'Known'],
  ['Jul', 'Estimated'],
  ['Aug', 'Review'],
  ['Sep', 'Known'],
  ['Oct', 'Missing'],
  ['Nov', 'Estimated'],
  ['Dec', 'Known'],
]

const benchmarkRows = [
  ['Local portfolio series', 'synthetic index', 'PARTIAL'],
  ['MSCI World archive', 'local benchmark required', 'INSUFFICIENT_HISTORY'],
  ['FTSE All-World archive', 'local benchmark required', 'INSUFFICIENT_HISTORY'],
]

const costTaxRows = [
  ['Gross dividends', 'ledger evidence required', 'REVIEW'],
  ['Net dividends', 'ledger evidence required', 'REVIEW'],
  ['Withholding taxes', 'documentation required', 'INSUFFICIENT_DOCUMENTATION'],
  ['Fee drag', 'documentation required', 'INSUFFICIENT_DOCUMENTATION'],
]

const coverageRows = [
  ['MSFT', 'STANDARD', 'OK', 'PARTIAL', 'COVERED', 'PARTIAL', 'WAIT_VALUATION'],
  ['V', 'STANDARD', 'COVERED', 'OK', 'COVERED', 'OK', 'READY'],
  ['JNJ', 'STANDARD', 'OK', 'REVIEW', 'PARTIAL', 'PARTIAL', 'REVIEW_CORE_DATA'],
  ['KO', 'DIVIDEND_QUALITY', 'COVERED', 'PARTIAL', 'COVERED', 'NOT_APPLICABLE', 'HOLD'],
  ['LIN', 'QUALITY_COMPOUNDER', 'OK', 'MISSING_DATA', 'PARTIAL', 'INSUFFICIENT_HISTORY', 'NOT_READY'],
]

const secPipelineStages = [
  ['01', 'Scope Prepare', 'Audit which holdings are in scope for SEC data.', 'personal_sec_scope_prepare', 'personal_sec_scope_review.csv', 'COVERED'],
  ['02', 'Identity Resolve', 'Look up SEC tickers and filing identities.', 'manual review + identity map', 'reviewed identity map', 'REVIEW'],
  ['03', 'Identity Export', 'Export reviewed identities into your private map.', 'personal_sec_identity_export', 'downstream-safe identity map', 'PARTIAL'],
  ['04', 'CompanyFacts Fetch', "Read SEC filed numbers in a future explicit run.", 'external_sec_companyfacts_fetch', 'companyfacts snapshots', 'REVIEW'],
  ['05', 'Snapshot Ingest', 'Match incoming data exactly to your master.', 'fundamentals_snapshot_ingestion', 'snapshot_ingest_review.csv', 'PARTIAL'],
  ['06', 'Snapshot Review', 'You approve or reject each update.', 'fundamentals_snapshot_review', 'reviewed evidence updates', 'REVIEW'],
  ['07', 'Evidence Apply', 'Approved updates project into a separate master.', 'fundamentals_evidence_apply', 'evidence_applied_master.csv', 'BLOCKED'],
]

const evidenceWorkspaceRows = [
  ['MSFT', 'revenue_ttm', 'SEC CompanyFacts', 'COVERED', 'synthetic', 'STAGED', 'exact identity match'],
  ['V', 'free_cash_flow', 'SEC CompanyFacts', 'REVIEW', 'synthetic', 'REVIEW', 'taxonomy mapping requires review'],
  ['JNJ', 'dividend_payout_ratio', 'manual evidence', 'PARTIAL', 'synthetic', 'PENDING', 'manual evidence not applied'],
  ['LIN', 'valuation_band', 'none', 'MISSING_DATA', '', 'BLOCKED', 'no reviewed evidence'],
  ['KO', 'dividend_growth_5y', 'SEC + manual overlay', 'COVERED', 'synthetic', 'APPROVED', 'reviewed overlay present'],
]

const statusLabels = [
  ['COVERED', 'Required evidence is present and current.'],
  ['OK', 'Value is inside the current rule band.'],
  ['PARTIAL', 'Some required fields are missing or stale.'],
  ['REVIEW', 'Human decision pending before this can score.'],
  ['NO_MATCH', 'Identity could not be linked to a filer.'],
  ['MISSING_DATA', 'Field is not available; not silently filled.'],
  ['INSUFFICIENT_INPUTS', 'Not enough fields to compute a meaningful score.'],
  ['INSUFFICIENT_HISTORY', 'Not enough time series for this metric.'],
  ['NOT_APPLICABLE', 'This metric does not apply to this profile or instrument.'],
]

const masterLayers = [
  ['Base Master', 'Your original fundamentals input. Preserved as source material.', 'personal_fundamentals_master.csv'],
  ['Profiled Master', 'Applicability and profile checks added. Missing or not-applicable fields become explicit.', 'personal_fundamentals_profiled_master.csv'],
  ['Evidence-Applied Master', 'Only reviewed evidence updates are projected here. Downstream reports can opt in.', 'personal_fundamentals_evidence_applied_master.csv'],
]

const slogans = ['BUILT SLOW', 'USED MONTHLY', 'PRIVACY BY DEFAULT', 'NO HYPE', 'JUST SIGNAL', 'YOUR DATA', 'YOUR MACHINE']

function currentRoute() {
  if (window.location.pathname === '/workflow') {
    return '/workflow'
  }
  if (window.location.pathname === '/evidence') {
    return '/evidence'
  }
  if (window.location.pathname === '/portfolio') {
    return '/portfolio'
  }
  if (window.location.pathname === '/dashboard') {
    return '/dashboard'
  }
  if (window.location.pathname === '/manifesto' || window.location.pathname === '/about') {
    return '/manifesto'
  }
  return '/'
}

function useRoute() {
  const [route, setRoute] = useState(currentRoute)
  useEffect(() => {
    const onPop = () => setRoute(currentRoute())
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])
  const navigate = (href) => {
    if (href?.startsWith('/workflow') || href?.startsWith('/evidence') || href?.startsWith('/portfolio') || href?.startsWith('/dashboard') || href?.startsWith('/manifesto') || href?.startsWith('/about')) {
      const [path, hash] = href.split('#')
      window.history.pushState({}, '', href)
      setRoute(path === '/about' ? '/manifesto' : path)
      window.setTimeout(() => {
        if (hash) {
          document.getElementById(hash)?.scrollIntoView({ behavior: 'smooth' })
        } else {
          window.scrollTo({ top: 0, behavior: 'smooth' })
        }
      }, path === '/workflow' ? 0 : 0)
      return
    }
    if (href === '/') {
      window.history.pushState({}, '', href)
      setRoute('/')
      window.scrollTo({ top: 0, behavior: 'smooth' })
      return
    }
    window.location.hash = href.replace('#', '')
  }
  return { route, navigate }
}

function Pill({ tone = 'partial', children }) {
  return <span className={`pill pill-${tone}`}>{children}</span>
}

function statusTone(status) {
  if (['OK', 'COVERED', 'READY', 'APPROVED', 'STAGED'].includes(status)) {
    return 'ok'
  }
  if (['PARTIAL', 'INSUFFICIENT_HISTORY', 'INSUFFICIENT_INPUTS', 'PENDING', 'HOLD'].includes(status)) {
    return 'partial'
  }
  if (['REVIEW', 'WAIT_VALUATION', 'REVIEW_CORE_DATA'].includes(status)) {
    return 'review'
  }
  if (['MISSING_DATA', 'NO_MATCH', 'BLOCKED', 'NOT_READY', 'INSUFFICIENT_DOCUMENTATION'].includes(status)) {
    return 'missing'
  }
  return 'partial'
}

function SmartLink({ href, className, children, onNavigate, pending = false, ...props }) {
  if (pending) {
    return (
      <span className={`${className} is-disabled`} aria-disabled="true" {...props}>
        {children}
      </span>
    )
  }
  const external = href?.startsWith('http')
  return (
    <a
      className={className}
      href={href}
      target={external ? '_blank' : undefined}
      rel={external ? 'noreferrer' : undefined}
      onClick={(event) => {
        if (!external && onNavigate) {
          event.preventDefault()
          onNavigate(href)
        }
      }}
      {...props}
    >
      {children}
    </a>
  )
}

function Header({ route, navigate }) {
  return (
    <header className="fixed inset-x-0 top-0 z-50 border-b border-[color:var(--paper-300)] bg-[rgba(251,250,247,0.9)] px-5 py-3 backdrop-blur-xl sm:px-8">
      <nav className="mx-auto flex max-w-7xl items-center justify-between gap-4" aria-label="Main navigation">
        <SmartLink href="/" onNavigate={navigate} className="rounded-md" aria-label={`${siteConfig.productName} home`}>
          <img src={wordmarkInk} alt={`${siteConfig.productName} wordmark`} className="h-7 w-auto" />
        </SmartLink>
        <div className="hidden items-center gap-7 md:flex">
          {safeRoutes.map(([label, href, pending]) => (
            <SmartLink
              key={label}
              href={href}
              pending={pending}
              onNavigate={navigate}
              className={`text-sm font-medium ${route === href ? 'text-[color:var(--ink-900)]' : 'text-[color:var(--ink-600)] hover:text-[color:var(--ink-900)]'}`}
              title={pending ? 'Planned page - private preview placeholder' : undefined}
            >
              {label}
            </SmartLink>
          ))}
        </div>
        <SmartLink className="button button-primary px-4 py-2" href={siteConfig.ctas.sampleReport.href || '/workflow#sample-report'} onNavigate={navigate}>
          {siteConfig.ctas.sampleReport.label}
        </SmartLink>
      </nav>
    </header>
  )
}

function HeroMiniDashboard() {
  return (
    <aside className="dark-panel rounded-[1.35rem] border p-5 sm:p-6 lg:p-7" aria-label="Synthetic readiness dashboard preview">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3 border-b border-[color:var(--dark-600)] pb-4">
        <div>
          <div className="font-mono text-xs tracking-[0.06em] text-[color:var(--dark-fg-3)]">// LOCAL SYSTEM SNAPSHOT</div>
          <h2 className="mt-2 text-xl font-semibold text-[color:var(--dark-fg)]">Private preview readiness</h2>
        </div>
        <Pill tone="partial">synthetic demo values</Pill>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        {readinessRows.map(([label, value, tone]) => (
          <article className="kpi-card" key={label}>
            <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[color:var(--dark-fg-3)]">{label}</div>
            <div className="mt-3 font-mono text-xl font-semibold text-[color:var(--dark-fg)]">{value}</div>
            <div className="mt-4">
              <Pill tone={tone}>{value}</Pill>
            </div>
          </article>
        ))}
      </div>
      <div className="artifact-strip mt-5 border-[color:var(--dark-600)] text-[color:var(--dark-fg-3)]">
        <span>active blockers 11</span>
        <span>p0 blockers 6</span>
        <span>next actions 5</span>
      </div>
    </aside>
  )
}

function HomePage({ navigate }) {
  return (
    <>
      <section id="top" className="section pt-32 lg:pt-40" data-screenshot="home-hero">
        <div className="container-xl grid items-center gap-12 lg:grid-cols-[0.95fr_1.05fr]">
          <div>
            <p className="eyebrow hero-eyebrow">// LOCAL-FIRST INVESTMENT OPERATING SYSTEM</p>
            <h1 className="mt-4 max-w-3xl text-5xl font-semibold leading-[1.02] tracking-[-0.055em] text-[color:var(--ink-900)] sm:text-6xl lg:text-7xl">
              A calmer way to run a long-term portfolio.
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-[color:var(--ink-600)]">
              Compound Income OS turns your broker exports, fundamentals and SEC evidence into one monthly decision you can trust.
            </p>
            <div className="mt-6 space-y-2 text-sm text-[color:var(--ink-700)]">
              {['Research. Rank. Decide. Track.', 'Local-first. Private by default.', 'Built for dividend-growth and quality compounders.'].map((item) => (
                <div key={item}>- {item}</div>
              ))}
            </div>
            <div className="mt-8 flex flex-wrap gap-3">
              <SmartLink className="button button-primary" href="/workflow#sample-report" onNavigate={navigate}>
                Read a sample monthly report
              </SmartLink>
              <SmartLink className="button button-secondary" href="/workflow" onNavigate={navigate}>
                See the workflow
              </SmartLink>
            </div>
            <div className="mt-8 flex flex-wrap gap-2">
              {['LOCAL-FIRST', 'OPEN-SOURCE CORE', 'EVIDENCE-BASED', 'NO BROKER', 'NO CLOUD'].map((tag) => (
                <span className="rounded-full border border-[color:var(--paper-300)] bg-white/60 px-3 py-1 font-mono text-[10px] tracking-[0.12em] text-[color:var(--ink-600)]" key={tag}>
                  {tag}
                </span>
              ))}
            </div>
          </div>
          <HeroMiniDashboard />
        </div>
      </section>
      <ProblemCards />
      <DashboardViewerMockup compact />
      <BuilderTeaser navigate={navigate} />
      <PromiseGrid navigate={navigate} />
    </>
  )
}

function ProblemCards() {
  return (
    <section id="problem" className="section-tight">
      <div className="container-xl">
        <p className="eyebrow">// THE PROBLEM</p>
        <h2 className="section-title">Where long-term portfolios actually break.</h2>
        <div className="mt-10 grid gap-5 md:grid-cols-3">
          {[
            ['The watchlist drifts.', 'Ideas accumulate. Review state disappears. The next month starts from memory.'],
            ['Missing data becomes invisible.', 'A system is only useful when it shows what is covered, partial, reviewed or missing.'],
            ['The reasoning gets lost.', 'A monthly archive should make the same decision legible a year later.'],
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
  )
}

function BuilderTeaser({ navigate }) {
  return (
    <section id="manifesto-teaser" className="section-tight bg-[color:var(--paper-100)]">
      <div className="container-xl grid gap-6 rounded-3xl border border-[color:var(--paper-300)] bg-white/60 p-7 lg:grid-cols-[1fr_0.7fr]">
        <div>
          <p className="eyebrow">// BUILDER NOTE</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-[-0.035em] text-[color:var(--ink-900)]">Open-source core. Builder-led. No venture capital.</h2>
          <p className="mt-4 max-w-3xl leading-7 text-[color:var(--ink-600)]">
            The manifesto and access page keeps pending public-launch items visible instead of pretending they are complete.
          </p>
          <div className="mt-6">
            <SmartLink className="button button-secondary" href="/manifesto" onNavigate={navigate}>
              Read the manifesto
            </SmartLink>
          </div>
        </div>
        <div className="rounded-2xl border border-[color:var(--paper-300)] bg-[color:var(--paper-50)] p-5">
          <div className="font-mono text-xs uppercase tracking-[0.14em] text-[color:var(--accent-600)]">private preview access</div>
          <p className="mt-3 text-sm leading-6 text-[color:var(--ink-600)]">Access cards use honest pending states until real private-preview targets are configured.</p>
        </div>
      </div>
    </section>
  )
}

function PromiseGrid({ navigate }) {
  return (
    <section className="section">
      <div className="container-xl">
        <p className="eyebrow">// FIVE PROMISES</p>
        <h2 className="section-title">Five surfaces. One monthly operating rhythm.</h2>
        <div className="mt-10 grid gap-5 md:grid-cols-2 xl:grid-cols-5">
          {promises.map(([title, body, href, pending], index) => (
            <article className="card flex min-h-64 flex-col" id={href.replace('#', '')} key={title}>
              <div className="font-mono text-sm text-[color:var(--accent-600)]">0{index + 1}</div>
              <h3 className="mt-4 text-xl font-semibold text-[color:var(--ink-900)]">{title}</h3>
              <p className="mt-3 flex-1 text-sm leading-6 text-[color:var(--ink-600)]">{body}</p>
              <SmartLink href={href} pending={pending} onNavigate={navigate} className="mt-6 font-mono text-xs uppercase tracking-[0.14em] text-[color:var(--accent-600)]">
                {pending ? 'Planned page' : 'Open section'}
              </SmartLink>
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}

function WorkflowPage({ navigate }) {
  return (
    <>
      <section className="section pt-32 lg:pt-40" data-screenshot="workflow-hero">
        <div className="container-xl grid gap-10 lg:grid-cols-[0.9fr_1.1fr]">
          <div>
            <p className="eyebrow">// THE WORKFLOW</p>
            <h1 className="mt-4 text-5xl font-semibold leading-[1.02] tracking-[-0.055em] text-[color:var(--ink-900)] sm:text-6xl">
              Six stages, one monthly cadence.
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-[color:var(--ink-600)]">
              The same six stages every month - so month 12 is just month 1, eleven times reviewed.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <SmartLink className="button button-primary" href="/workflow#sample-report" onNavigate={navigate}>
                Read a sample monthly report
              </SmartLink>
              <SmartLink className="button button-secondary" href="/evidence" onNavigate={navigate}>
                See the evidence layer
              </SmartLink>
            </div>
          </div>
          <RunManifestMockup />
        </div>
      </section>
      <WorkflowStages />
      <MonthlyReportRender />
      <DashboardViewerMockup />
      <ArchiveBlock />
    </>
  )
}

function RunManifestMockup() {
  return (
    <aside className="dark-panel rounded-[1.35rem] border p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="font-mono text-xs uppercase tracking-[0.14em] text-[color:var(--dark-fg-3)]">personal_run_manifest.json</div>
        <Pill tone="partial">synthetic demo values</Pill>
      </div>
      <div className="mt-5 space-y-3 font-mono text-xs text-[color:var(--dark-fg-2)]">
        {[
          ['run_id', 'DEMO-2026-04'],
          ['demo_readiness', 'BLOCKED'],
          ['decision_readiness', 'BLOCKED'],
          ['dashboard_readiness', 'REVIEW'],
          ['network_performed', 'false'],
        ].map(([key, value]) => (
          <div className="flex justify-between border-b border-[color:var(--dark-600)] pb-2" key={key}>
            <span>{key}</span>
            <span className="text-[color:var(--dark-fg)]">{value}</span>
          </div>
        ))}
      </div>
    </aside>
  )
}

function WorkflowStages() {
  return (
    <section className="section-tight bg-[color:var(--paper-100)]">
      <div className="container-xl">
        <p className="eyebrow">// MONTHLY CADENCE</p>
        <div className="mt-8 grid gap-4">
          {workflowStages.map(([number, title, input, engine, output]) => (
            <article className="grid gap-5 rounded-2xl border border-[color:var(--paper-300)] bg-white/70 p-5 md:grid-cols-[0.12fr_0.32fr_1fr_1fr_1fr]" key={title}>
              <div className="font-mono text-sm text-[color:var(--accent-600)]">{number}</div>
              <h3 className="font-semibold text-[color:var(--ink-900)]">{title}</h3>
              <StageCell label="Input" value={input} />
              <StageCell label="Engine" value={engine} />
              <StageCell label="Output" value={output} />
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}

function StageCell({ label, value }) {
  return (
    <div>
      <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-[color:var(--ink-400)]">{label}</div>
      <div className="mt-2 text-sm leading-6 text-[color:var(--ink-700)]">{value}</div>
    </div>
  )
}

function MonthlyReportRender() {
  return (
    <section id="sample-report" className="section" data-screenshot="monthly-report-render">
      <div className="container-xl">
        <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="eyebrow">// P2 PRODUCT UI MOCKUP</p>
            <h2 className="section-title">Monthly Decision Report - rendered.</h2>
          </div>
          <Pill tone="partial">synthetic demo values</Pill>
        </div>
        <div className="rounded-[1.6rem] border border-[color:var(--paper-300)] bg-white/80 p-5 shadow-lg lg:p-8">
          <div className="grid gap-5 lg:grid-cols-[0.9fr_1.1fr]">
            <div>
              <div className="font-mono text-xs uppercase tracking-[0.14em] text-[color:var(--accent-600)]">monthly_decision_report.md</div>
              <h3 className="mt-3 text-4xl font-semibold tracking-[-0.04em] text-[color:var(--ink-900)]">April run: blocked until review inputs are complete.</h3>
              <p className="mt-4 leading-7 text-[color:var(--ink-600)]">
                This mockup shows the shape of the report only. Values are synthetic or aggregated, and the report does not imply decision readiness.
              </p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              {reportSections.map(([title, body, status]) => (
                <article className="rounded-2xl border border-[color:var(--paper-300)] bg-[color:var(--paper-50)] p-4" key={title}>
                  <div className="flex items-center justify-between gap-3">
                    <h4 className="font-semibold text-[color:var(--ink-900)]">{title}</h4>
                    <Pill tone={status === 'MISSING_DATA' ? 'missing' : status === 'PARTIAL' ? 'partial' : status === 'REVIEW' ? 'review' : 'ok'}>{status}</Pill>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-[color:var(--ink-600)]">{body}</p>
                </article>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

function DashboardViewerMockup({ compact = false }) {
  return (
    <section id="dashboard-viewer" className={compact ? 'section-tight' : 'section-tight bg-[color:var(--paper-100)]'} data-screenshot="dashboard-viewer">
      <div className="container-xl">
        <div className="dark-panel rounded-[1.35rem] border p-5 sm:p-6 lg:p-8">
          <div className="mb-6 flex flex-wrap items-center justify-between gap-4 border-b border-[color:var(--dark-600)] pb-4">
            <div className="flex items-center gap-3">
              <img src={wordmarkPaper} alt="Compound Income OS dashboard wordmark" className="h-6 w-auto" />
              <div>
                <div className="font-mono text-xs uppercase tracking-[0.14em] text-[color:var(--dark-fg-3)]">Local Dashboard Viewer</div>
                <div className="mt-1 text-sm text-[color:var(--dark-fg-2)]">read-only localhost view - synthetic demo values</div>
              </div>
            </div>
            <Pill tone="review">Dashboard readiness REVIEW</Pill>
          </div>
          <div className="grid gap-5 lg:grid-cols-[0.34fr_1fr]">
            <div className="rounded-2xl border border-[color:var(--dark-600)] bg-[rgba(26,35,44,0.76)] p-4">
              <div className="font-mono text-xs uppercase tracking-[0.14em] text-[color:var(--dark-fg-3)]">KPI groups</div>
              <div className="mt-4 space-y-3">
                {dashboardGroups.map(([label, , status], index) => (
                  <div className="flex items-center justify-between gap-3 border-b border-[color:var(--dark-600)] pb-3 text-sm" key={label}>
                    <span className="text-[color:var(--dark-fg-2)]">{index + 1}. {label}</span>
                    <Pill tone={status === 'MISSING_DATA' ? 'missing' : status === 'PARTIAL' ? 'partial' : status === 'REVIEW' ? 'review' : 'ok'}>{status}</Pill>
                  </div>
                ))}
              </div>
            </div>
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              {readinessRows.map(([label, value, tone]) => (
                <article className="kpi-card" key={label}>
                  <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[color:var(--dark-fg-3)]">{label}</div>
                  <div className="mt-3 font-mono text-xl font-semibold text-[color:var(--dark-fg)]">{value}</div>
                  <div className="mt-4">
                    <Pill tone={tone}>{value}</Pill>
                  </div>
                </article>
              ))}
              {dashboardGroups.map(([label, note, status]) => (
                <article className="kpi-card" key={label}>
                  <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[color:var(--dark-fg-3)]">{label}</div>
                  <div className="mt-3 text-sm leading-6 text-[color:var(--dark-fg-2)]">{note}</div>
                  <div className="mt-4">
                    <Pill tone={status === 'MISSING_DATA' ? 'missing' : status === 'PARTIAL' ? 'partial' : status === 'REVIEW' ? 'review' : 'ok'}>{status}</Pill>
                  </div>
                </article>
              ))}
            </div>
          </div>
          <div className="artifact-strip mt-6 border-[color:var(--dark-600)] text-[color:var(--dark-fg-3)]">
            <span>source - dashboard_readiness_payload.json</span>
            <span>network performed false</span>
            <span>private raw files excluded</span>
          </div>
        </div>
      </div>
    </section>
  )
}

function ArchiveBlock() {
  return (
    <section className="section">
      <div className="container-xl">
        <div className="rounded-3xl border border-[color:var(--paper-300)] bg-white/70 p-7">
          <p className="eyebrow">// ARCHIVE</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-[-0.035em] text-[color:var(--ink-900)]">Twelve runs. One auditable year.</h2>
          <div className="mt-6 flex flex-wrap gap-2">
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

function EvidencePage({ navigate }) {
  const sampleHref = siteConfig.ctas.sampleReport.href || '/workflow#sample-report'
  return (
    <>
      <section className="section pt-32 lg:pt-40" data-screenshot="evidence-hero">
        <div className="container-xl grid gap-10 lg:grid-cols-[0.9fr_1.1fr]">
          <div>
            <p className="eyebrow hero-eyebrow">// EVIDENCE & DATA QUALITY</p>
            <h1 className="mt-4 max-w-3xl text-5xl font-semibold leading-[1.02] tracking-[-0.055em] text-[color:var(--ink-900)] sm:text-6xl">
              See what's covered. See what's missing.
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-[color:var(--ink-600)]">
              Most portfolio tools fill in the blanks. Compound Income OS shows you which blanks exist, where they came from, and what it would take to close them.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <SmartLink className="button button-primary" href={sampleHref} onNavigate={navigate}>
                Read a sample monthly report
              </SmartLink>
              <SmartLink className="button button-secondary" href="/portfolio" onNavigate={navigate}>
                See the portfolio model
              </SmartLink>
            </div>
            <div className="mt-8 flex flex-wrap gap-2">
              {['READ-ONLY SEC PATH', 'MANUAL IDENTITY REVIEW', 'NO SILENT OVERWRITES', 'SYNTHETIC DEMO VALUES'].map((tag) => (
                <span className="rounded-full border border-[color:var(--paper-300)] bg-white/60 px-3 py-1 font-mono text-[10px] tracking-[0.12em] text-[color:var(--ink-600)]" key={tag}>
                  {tag}
                </span>
              ))}
            </div>
          </div>
          <EvidenceHeroCard />
        </div>
      </section>
      <CoverageTierTable />
      <SecPipeline />
      <EvidenceWorkspaceMockup />
      <StatusLabels />
      <ThreeLayerMaster />
      <EvidenceHighlightBar />
    </>
  )
}

function EvidenceHeroCard() {
  return (
    <aside className="rounded-[1.35rem] border border-[color:var(--paper-300)] bg-white/70 p-6 shadow-lg">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[color:var(--paper-300)] pb-4">
        <div>
          <div className="font-mono text-xs uppercase tracking-[0.14em] text-[color:var(--accent-600)]">evidence status language</div>
          <h2 className="mt-2 text-2xl font-semibold tracking-[-0.03em] text-[color:var(--ink-900)]">Every KPI carries a status.</h2>
        </div>
        <Pill tone="partial">synthetic demo values</Pill>
      </div>
      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        {[
          ['Missing values', 'visible', 'missing'],
          ['Identity review', 'manual', 'review'],
          ['Evidence apply', 'reviewed only', 'partial'],
          ['Raw master', 'preserved', 'ok'],
        ].map(([label, value, tone]) => (
          <article className="rounded-2xl border border-[color:var(--paper-300)] bg-[color:var(--paper-50)] p-4" key={label}>
            <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-[color:var(--ink-400)]">{label}</div>
            <div className="mt-3 text-xl font-semibold text-[color:var(--ink-900)]">{value}</div>
            <div className="mt-4">
              <Pill tone={tone}>{value}</Pill>
            </div>
          </article>
        ))}
      </div>
      <p className="mt-5 text-sm leading-6 text-[color:var(--ink-600)]">
        This page is a private-preview product mockup. It uses synthetic holdings and status examples only.
      </p>
    </aside>
  )
}

function CoverageTierTable() {
  return (
    <section className="section-tight bg-[color:var(--paper-100)]" data-screenshot="evidence-coverage">
      <div className="container-xl">
        <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="eyebrow">// COVERAGE TIERS</p>
            <h2 className="section-title">Coverage is tracked by holding and KPI tier.</h2>
            <p className="section-lede">Synthetic demo holdings show how core, valuation, dividend / FCF and advanced tiers stay explicit.</p>
          </div>
          <Pill tone="partial">synthetic demo values</Pill>
        </div>
        <div className="evidence-table-shell">
          <table className="evidence-table">
            <thead>
              <tr>
                {['Holding', 'Profile', 'Core', 'Valuation', 'Dividend FCF', 'Advanced', 'Monthly Action'].map((header) => (
                  <th key={header}>{header}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {coverageRows.map(([holding, profile, core, valuation, dividendFcf, advanced, action]) => (
                <tr key={holding}>
                  <td className="font-mono text-[color:var(--ink-900)]">{holding}</td>
                  <td>{profile}</td>
                  {[core, valuation, dividendFcf, advanced, action].map((status, index) => (
                    <td key={`${holding}-${index}`}>
                      <Pill tone={statusTone(status)}>{status}</Pill>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-4 text-sm leading-6 text-[color:var(--ink-500)]">
          Demo actions illustrate status handling only. They are not personalized guidance.
        </p>
      </div>
    </section>
  )
}

function SecPipeline() {
  return (
    <section className="section">
      <div className="container-xl">
        <div className="mb-10">
          <p className="eyebrow">// SEC PIPELINE</p>
          <h2 className="section-title">Seven stages from filer identity to applied evidence.</h2>
          <p className="section-lede">
            SEC CompanyFacts data only enters the decision layer after identity review, staging, and explicit apply. The raw master is never silently overwritten.
          </p>
        </div>
        <div className="grid gap-4 lg:grid-cols-7">
          {secPipelineStages.map(([number, title, subtitle, engine, output, status]) => (
            <article className="pipeline-card" key={title}>
              <div className="flex items-center justify-between gap-3">
                <span className="font-mono text-sm text-[color:var(--accent-600)]">{number}</span>
                <Pill tone={statusTone(status)}>{status}</Pill>
              </div>
              <h3 className="mt-4 font-semibold text-[color:var(--ink-900)]">{title}</h3>
              <p className="mt-3 text-sm leading-6 text-[color:var(--ink-600)]">{subtitle}</p>
              <div className="mt-4 space-y-2">
                <PipelineMeta label="Engine" value={engine} />
                <PipelineMeta label="Output" value={output} />
              </div>
            </article>
          ))}
        </div>
        <div className="mt-6 flex flex-wrap gap-2">
          {['read-only', 'reviewed', 'optional', 'no network in preview'].map((tag) => (
            <span className="rounded-full border border-[color:var(--paper-300)] bg-white/70 px-3 py-1 font-mono text-xs text-[color:var(--ink-600)]" key={tag}>
              {tag}
            </span>
          ))}
        </div>
      </div>
    </section>
  )
}

function PipelineMeta({ label, value }) {
  return (
    <div className="rounded-xl border border-[color:var(--paper-300)] bg-[color:var(--paper-50)] px-3 py-2">
      <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-[color:var(--ink-400)]">{label}</div>
      <div className="mt-1 font-mono text-xs text-[color:var(--ink-700)]">{value}</div>
    </div>
  )
}

function EvidenceWorkspaceMockup() {
  return (
    <section className="section-tight bg-[color:var(--paper-100)]" data-screenshot="evidence-workspace">
      <div className="container-xl">
        <div className="dark-panel rounded-[1.35rem] border p-5 sm:p-6 lg:p-8">
          <div className="mb-6 flex flex-wrap items-start justify-between gap-4 border-b border-[color:var(--dark-600)] pb-4">
            <div>
              <div className="font-mono text-xs uppercase tracking-[0.14em] text-[color:var(--dark-fg-3)]">Evidence Workspace</div>
              <h2 className="mt-2 text-3xl font-semibold tracking-[-0.04em] text-[color:var(--dark-fg)]">synthetic demo values - private preview</h2>
            </div>
            <div className="space-y-1 text-right font-mono text-[11px] text-[color:var(--dark-fg-3)]">
              <div>run_id DEMO-20260427-EVIDENCE</div>
              <div>source SEC CompanyFacts snapshot</div>
              <div>apply mode reviewed only</div>
            </div>
          </div>
          <div className="grid gap-5 lg:grid-cols-[0.22fr_1fr]">
            <aside className="rounded-2xl border border-[color:var(--dark-600)] bg-[rgba(26,35,44,0.76)] p-4">
              <div className="font-mono text-xs uppercase tracking-[0.14em] text-[color:var(--dark-fg-3)]">Workspace</div>
              <div className="mt-4 space-y-2">
                {['Scope', 'Identity', 'Snapshots', 'Review Queue', 'Apply Log'].map((tab, index) => (
                  <div className={`rounded-xl border px-3 py-2 text-sm ${index === 3 ? 'border-[color:var(--dark-accent)] text-[color:var(--dark-fg)]' : 'border-[color:var(--dark-600)] text-[color:var(--dark-fg-2)]'}`} key={tab}>
                    {tab}
                  </div>
                ))}
              </div>
            </aside>
            <div className="min-w-0">
              <div className="grid gap-3 md:grid-cols-4">
                {[
                  ['Eligible US holdings', '12', 'COVERED'],
                  ['Reviewed identities', '10 / 12', 'PARTIAL'],
                  ['Proposed updates', '18', 'REVIEW'],
                  ['Applied updates', '0 in demo', 'BLOCKED'],
                ].map(([label, value, status]) => (
                  <article className="kpi-card" key={label}>
                    <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[color:var(--dark-fg-3)]">{label}</div>
                    <div className="mt-3 font-mono text-xl font-semibold text-[color:var(--dark-fg)]">{value}</div>
                    <div className="mt-4">
                      <Pill tone={statusTone(status)}>{status}</Pill>
                    </div>
                  </article>
                ))}
              </div>
              <div className="mt-5 overflow-x-auto">
                <table className="workspace-table">
                  <thead>
                    <tr>
                      {['Holding', 'Evidence Field', 'Source', 'Current Status', 'Proposed Value', 'Action', 'Reason'].map((header) => (
                        <th key={header}>{header}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {evidenceWorkspaceRows.map(([holding, field, source, status, proposed, action, reason]) => (
                      <tr key={`${holding}-${field}`}>
                        <td>{holding}</td>
                        <td>{field}</td>
                        <td>{source}</td>
                        <td><Pill tone={statusTone(status)}>{status}</Pill></td>
                        <td>{proposed || '-'}</td>
                        <td><Pill tone={statusTone(action)}>{action}</Pill></td>
                        <td>{reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="artifact-strip mt-5 border-[color:var(--dark-600)] text-[color:var(--dark-fg-3)]">
                <span>No raw master overwrite</span>
                <span>Applied values go to evidence-applied master</span>
                <span>Missing data remains visible</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

function StatusLabels() {
  return (
    <section className="section">
      <div className="container-xl">
        <p className="eyebrow">// STATUS LANGUAGE</p>
        <h2 className="section-title">Nine status labels. No hidden blanks.</h2>
        <p className="section-lede">Every KPI, evidence field, and monthly action can carry a status. These labels are product language, not debug noise.</p>
        <div className="mt-10 grid gap-4 md:grid-cols-3">
          {statusLabels.map(([status, meaning]) => (
            <article className="card" key={status}>
              <Pill tone={statusTone(status)}>{status}</Pill>
              <p className="mt-4 text-sm leading-6 text-[color:var(--ink-600)]">{meaning}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}

function ThreeLayerMaster() {
  return (
    <section className="section-tight bg-[color:var(--paper-100)]" data-screenshot="evidence-master-layers">
      <div className="container-xl">
        <p className="eyebrow">// THREE-LAYER MASTER</p>
        <h2 className="section-title">The raw master is never silently overwritten.</h2>
        <p className="section-lede">
          Evidence updates move through separate layers. The original input stays inspectable; reviewed updates project into an evidence-applied master for downstream reports.
        </p>
        <div className="mt-10 grid gap-5 lg:grid-cols-3">
          {masterLayers.map(([title, body, artifact], index) => (
            <article className="master-layer-card" key={title}>
              <div className="font-mono text-sm text-[color:var(--accent-600)]">0{index + 1}</div>
              <h3 className="mt-4 text-2xl font-semibold tracking-[-0.03em] text-[color:var(--ink-900)]">{title}</h3>
              <p className="mt-3 text-sm leading-6 text-[color:var(--ink-600)]">{body}</p>
              <div className="mt-5 rounded-xl border border-[color:var(--paper-300)] bg-[color:var(--paper-50)] px-3 py-2 font-mono text-xs text-[color:var(--ink-600)]">
                {artifact}
              </div>
            </article>
          ))}
        </div>
        <div className="mt-6 rounded-2xl border border-[color:var(--paper-300)] bg-white/70 p-5 text-center font-mono text-xs uppercase tracking-[0.16em] text-[color:var(--ink-600)]">
          base - profiled - evidence-applied | No raw input mutation. No silent imputation.
        </div>
      </div>
    </section>
  )
}

function EvidenceHighlightBar() {
  return (
    <section className="section-tight">
      <div className="container-xl">
        <div className="rounded-[1.35rem] bg-[color:var(--ink-900)] px-6 py-8 text-center text-3xl font-semibold tracking-[-0.03em] text-[color:var(--paper-50)] sm:text-4xl">
          IF A NUMBER IS MISSING, THE REPORT SAYS SO.
        </div>
      </div>
    </section>
  )
}

function PortfolioPage({ navigate }) {
  return (
    <>
      <section className="section pt-32 lg:pt-40" data-screenshot="portfolio-hero">
        <div className="container-xl grid items-center gap-10 lg:grid-cols-[0.86fr_1.14fr]">
          <div>
            <p className="eyebrow hero-eyebrow">// PORTFOLIO MODEL</p>
            <h1 className="mt-4 max-w-3xl text-5xl font-semibold leading-[1.02] tracking-[-0.055em] text-[color:var(--ink-900)] sm:text-6xl">
              Four sleeves. Clear rules. Long-term focus.
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-[color:var(--ink-600)]">
              A rules-based portfolio model helps separate core exposure, dividend quality, single-stock conviction, and cash without turning the system into a brokerage app.
            </p>
            <div className="mt-6 inline-flex rounded-full border border-[color:var(--paper-300)] bg-white/70 px-4 py-2 font-mono text-xs uppercase tracking-[0.12em] text-[color:var(--ink-600)]">
              Private preview - synthetic demo values - not portfolio allocation guidance
            </div>
          </div>
          <PortfolioHeroPanel />
        </div>
      </section>
      <FourSleevesSection />
      <HoldingsSleevesMockup />
      <PortfolioRulesSection />
      <HoldingStatusModel />
      <PortfolioReadinessBox navigate={navigate} />
    </>
  )
}

function PortfolioHeroPanel() {
  return (
    <aside className="dark-panel rounded-[1.35rem] border p-5 sm:p-6 lg:p-8" aria-label="Portfolio Allocation private preview">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4 border-b border-[color:var(--dark-600)] pb-4">
        <div>
          <div className="font-mono text-xs uppercase tracking-[0.14em] text-[color:var(--dark-fg-3)]">Portfolio Allocation</div>
          <h2 className="mt-2 text-3xl font-semibold tracking-[-0.04em] text-[color:var(--dark-fg)]">Sleeve operating model</h2>
        </div>
        <Pill tone="partial">synthetic demo values</Pill>
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        {[
          ['Portfolio', 'REVIEW', 'review'],
          ['Decision', 'BLOCKED', 'missing'],
          ['Data Quality', 'PARTIAL', 'partial'],
        ].map(([label, value, tone]) => (
          <article className="kpi-card" key={label}>
            <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[color:var(--dark-fg-3)]">{label}</div>
            <div className="mt-3 font-mono text-xl font-semibold text-[color:var(--dark-fg)]">{value}</div>
            <div className="mt-4">
              <Pill tone={tone}>{value}</Pill>
            </div>
          </article>
        ))}
      </div>
      <div className="mt-5 grid gap-3 sm:grid-cols-4">
        {portfolioSleeves.map(([title, , band, , status]) => (
          <article className="rounded-xl border border-[color:var(--dark-600)] bg-[rgba(26,35,44,0.72)] p-3" key={title}>
            <div className="text-[11px] leading-5 text-[color:var(--dark-fg-2)]">{title}</div>
            <div className="mt-2 font-mono text-lg font-semibold text-[color:var(--dark-fg)]">{band}</div>
            <div className="mt-3">
              <Pill tone={statusTone(status)}>{status}</Pill>
            </div>
          </article>
        ))}
      </div>
      <div className="artifact-strip mt-5 border-[color:var(--dark-600)] text-[color:var(--dark-fg-3)]">
        <span>illustrative rule bands</span>
        <span>review gates visible</span>
        <span>no private allocation data</span>
      </div>
    </aside>
  )
}

function FourSleevesSection() {
  return (
    <section className="section">
      <div className="container-xl">
        <p className="eyebrow">// FOUR SLEEVES</p>
        <h2 className="section-title">Four sleeves. One operating model.</h2>
        <p className="section-lede">The model separates portfolio roles so that every position has a job, a rule context, and a review state.</p>
        <div className="mt-10 grid gap-5 md:grid-cols-2 xl:grid-cols-4">
          {portfolioSleeves.map(([title, purpose, band, note, status], index) => (
            <article className="card" key={title}>
              <div className="flex items-center justify-between gap-3">
                <span className="font-mono text-sm text-[color:var(--accent-600)]">0{index + 1}</span>
                <Pill tone={statusTone(status)}>{status}</Pill>
              </div>
              <h3 className="mt-4 text-xl font-semibold text-[color:var(--ink-900)]">{title}</h3>
              <p className="mt-3 text-sm leading-6 text-[color:var(--ink-600)]">{purpose}</p>
              <div className="mt-5 rounded-2xl border border-[color:var(--paper-300)] bg-[color:var(--paper-50)] p-4">
                <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-[color:var(--ink-400)]">example band</div>
                <div className="mt-2 font-mono text-2xl font-semibold text-[color:var(--ink-900)]">{band}</div>
                <p className="mt-2 text-xs leading-5 text-[color:var(--ink-500)]">{note}</p>
              </div>
            </article>
          ))}
        </div>
        <p className="mt-6 max-w-3xl text-sm leading-6 text-[color:var(--ink-500)]">
          The bands are synthetic and illustrative. They describe how a rules view could work; they are not personal allocation guidance.
        </p>
      </div>
    </section>
  )
}

function HoldingsSleevesMockup() {
  return (
    <section className="section-tight bg-[color:var(--paper-100)]" data-screenshot="portfolio-workspace">
      <div className="container-xl">
        <div className="dark-panel rounded-[1.35rem] border p-5 sm:p-6 lg:p-8">
          <div className="mb-6 flex flex-wrap items-center justify-between gap-4 border-b border-[color:var(--dark-600)] pb-4">
            <div>
              <div className="font-mono text-xs uppercase tracking-[0.14em] text-[color:var(--dark-fg-3)]">Holdings & Sleeves Workspace</div>
              <h2 className="mt-2 text-3xl font-semibold tracking-[-0.04em] text-[color:var(--dark-fg)]">Rule bands before review state</h2>
            </div>
            <Pill tone="partial">synthetic demo values</Pill>
          </div>
          <div className="grid gap-5 lg:grid-cols-[1.12fr_0.88fr]">
            <div className="overflow-x-auto rounded-2xl border border-[color:var(--dark-600)] bg-[rgba(13,20,28,0.52)]">
              <table className="workspace-table">
                <thead>
                  <tr>
                    <th>sleeve</th>
                    <th>current band</th>
                    <th>rule band</th>
                    <th>status</th>
                    <th>review flag</th>
                  </tr>
                </thead>
                <tbody>
                  {portfolioWorkspaceRows.map(([sleeve, currentBand, ruleBand, status, flag]) => (
                    <tr key={sleeve}>
                      <td className="font-semibold text-[color:var(--dark-fg)]">{sleeve}</td>
                      <td>{currentBand}</td>
                      <td className="font-mono">{ruleBand}</td>
                      <td>
                        <Pill tone={statusTone(status)}>{status}</Pill>
                      </td>
                      <td>{flag}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
              {portfolioRiskRules.map(([title, body, status]) => (
                <article className="kpi-card" key={title}>
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[color:var(--dark-fg-3)]">{title}</div>
                      <p className="mt-3 text-sm leading-6 text-[color:var(--dark-fg-2)]">{body}</p>
                    </div>
                    <Pill tone={statusTone(status)}>{status}</Pill>
                  </div>
                </article>
              ))}
            </div>
          </div>
          <div className="artifact-strip mt-5 border-[color:var(--dark-600)] text-[color:var(--dark-fg-3)]">
            <span>illustrative concentration rules</span>
            <span>cash reserve visible</span>
            <span>review state required</span>
          </div>
        </div>
      </div>
    </section>
  )
}

function PortfolioRulesSection() {
  return (
    <section className="section">
      <div className="container-xl">
        <p className="eyebrow">// RULES AND GUARDRAILS</p>
        <h2 className="section-title">Rules before opinions.</h2>
        <p className="section-lede">Every portfolio view is constrained by declared rules. If a rule cannot be checked, the dashboard says so.</p>
        <div className="mt-10 grid gap-5 md:grid-cols-2 xl:grid-cols-5">
          {portfolioGuardrails.map(([title, body], index) => (
            <article className="card" key={title}>
              <div className="font-mono text-sm text-[color:var(--accent-600)]">0{index + 1}</div>
              <h3 className="mt-4 text-xl font-semibold text-[color:var(--ink-900)]">{title}</h3>
              <p className="mt-3 text-sm leading-6 text-[color:var(--ink-600)]">{body}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}

function HoldingStatusModel() {
  return (
    <section className="section-tight bg-[color:var(--paper-100)]">
      <div className="container-xl">
        <p className="eyebrow">// HOLDING STATUS MODEL</p>
        <h2 className="section-title">A status model for long-term operators.</h2>
        <p className="section-lede">The system does not need an execution signal. It needs a clear review state.</p>
        <div className="mt-10 grid gap-4 md:grid-cols-3">
          {holdingStatuses.map(([title, body]) => (
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

function PortfolioReadinessBox({ navigate }) {
  return (
    <section className="section">
      <div className="container-xl">
        <div className="grid gap-7 rounded-[1.35rem] border border-[color:var(--paper-300)] bg-white/75 p-6 shadow-sm lg:grid-cols-[0.9fr_1.1fr]">
          <div>
            <p className="eyebrow">// READINESS CONNECTION</p>
            <h2 className="mt-3 text-3xl font-semibold tracking-[-0.035em] text-[color:var(--ink-900)]">Why this portfolio view is not decision-ready yet.</h2>
            <p className="mt-4 text-sm leading-6 text-[color:var(--ink-600)]">
              The page shows the structural model only. The current readiness state remains blocked until missing inputs, evidence gaps, and sample watchlist blockers are resolved.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              {[
                'Review private valuation inputs',
                'Review dividend / FCF inputs',
                'Inspect evidence gaps',
              ].map((label) => (
                <span className="button button-secondary is-disabled" aria-disabled="true" key={label}>
                  {label}
                </span>
              ))}
              <SmartLink className="button button-primary" href="/dashboard" onNavigate={navigate}>
                Open local dashboard
              </SmartLink>
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            {portfolioReadinessBlockers.map(([label, value, tone]) => (
              <article className="rounded-2xl border border-[color:var(--paper-300)] bg-[color:var(--paper-50)] p-4" key={label}>
                <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-[color:var(--ink-400)]">{label}</div>
                <div className="mt-3 text-lg font-semibold text-[color:var(--ink-900)]">{value}</div>
                <div className="mt-4">
                  <Pill tone={tone}>{value}</Pill>
                </div>
              </article>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

function ManifestoPage({ navigate }) {
  return (
    <>
      <section className="section pt-32 lg:pt-40" data-screenshot="manifesto-hero">
        <div className="container-xl grid items-center gap-10 lg:grid-cols-[0.9fr_1.1fr]">
          <div>
            <p className="eyebrow hero-eyebrow">// OUR PROMISE</p>
            <h1 className="mt-4 max-w-3xl text-5xl font-semibold leading-[1.02] tracking-[-0.055em] text-[color:var(--ink-900)] sm:text-6xl">
              Built for people who think for the long run.
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-[color:var(--ink-600)]">
              No hype. No black box. No shortcuts. Just a local system that earns your trust month after month.
            </p>
            <div className="mt-6 inline-flex rounded-full border border-[color:var(--paper-300)] bg-white/70 px-4 py-2 font-mono text-xs uppercase tracking-[0.12em] text-[color:var(--ink-600)]">
              Private preview - research and decision-support only - not investment guidance
            </div>
          </div>
          <ManifestoHeroPanel />
        </div>
      </section>
      <ManifestoPrinciples />
      <BuiltForSection />
      <AccessSection navigate={navigate} />
      <PublicLaunchBlockers />
      <ManifestoFinalCta navigate={navigate} />
    </>
  )
}

function ManifestoHeroPanel() {
  return (
    <aside className="dark-panel rounded-[1.35rem] border p-5 sm:p-6 lg:p-8" aria-label="Compound Income OS manifesto private preview">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4 border-b border-[color:var(--dark-600)] pb-4">
        <div>
          <div className="font-mono text-xs uppercase tracking-[0.14em] text-[color:var(--dark-fg-3)]">The Compound Income OS Manifesto</div>
          <h2 className="mt-2 text-3xl font-semibold tracking-[-0.04em] text-[color:var(--dark-fg)]">Operating principles</h2>
        </div>
        <Pill tone="partial">private preview</Pill>
      </div>
      <div className="grid gap-3">
        {['Clarity over noise.', 'Evidence over opinion.', 'Process over impulse.', 'Discipline over emotion.', 'Long-term over short-term.', 'You decide. We support.'].map((line) => (
          <div className="rounded-2xl border border-[color:var(--dark-600)] bg-[rgba(26,35,44,0.72)] px-4 py-3 text-[color:var(--dark-fg)]" key={line}>
            {line}
          </div>
        ))}
      </div>
      <div className="artifact-strip mt-5 border-[color:var(--dark-600)] text-[color:var(--dark-fg-3)]">
        <span>local-first</span>
        <span>evidence-only</span>
        <span>pending states visible</span>
      </div>
    </aside>
  )
}

function ManifestoPrinciples() {
  return (
    <section className="section">
      <div className="container-xl">
        <p className="eyebrow">// OPERATING PRINCIPLES</p>
        <h2 className="section-title">Principles before features.</h2>
        <p className="section-lede">
          Compound Income OS is built around a simple idea: every long-term investment decision should be reproducible, reviewable, and honest about its data gaps.
        </p>
        <div className="mt-10 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {manifestoPrinciples.map(([title, body], index) => (
            <article className="card" key={title}>
              <div className="font-mono text-sm text-[color:var(--accent-600)]">0{index + 1}</div>
              <h3 className="mt-4 text-xl font-semibold text-[color:var(--ink-900)]">{title}</h3>
              <p className="mt-3 text-sm leading-6 text-[color:var(--ink-600)]">{body}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}

function BuiltForSection() {
  return (
    <section className="section-tight bg-[color:var(--paper-100)]" data-screenshot="manifesto-built-for">
      <div className="container-xl">
        <p className="eyebrow">// BUILT FOR</p>
        <h2 className="section-title">Built for independent operators.</h2>
        <p className="section-lede">This is not a signal product. It is an operating workflow for people who want to own their process.</p>
        <div className="mt-10 grid gap-5 lg:grid-cols-[1.05fr_0.95fr]">
          <div className="grid gap-4 md:grid-cols-2">
            {builtForCards.map(([title, body]) => (
              <article className="card" key={title}>
                <h3 className="text-xl font-semibold text-[color:var(--ink-900)]">{title}</h3>
                <p className="mt-3 text-sm leading-6 text-[color:var(--ink-600)]">{body}</p>
              </article>
            ))}
          </div>
          <aside className="rounded-[1.35rem] border border-[color:var(--paper-300)] bg-[color:var(--ink-900)] p-6 text-[color:var(--paper-50)]">
            <div className="font-mono text-xs uppercase tracking-[0.14em] text-[color:var(--dark-accent)]">Not built for</div>
            <div className="mt-5 grid gap-3">
              {notBuiltForItems.map((item) => (
                <div className="rounded-xl border border-[color:var(--dark-600)] bg-[rgba(26,35,44,0.72)] px-4 py-3 text-sm text-[color:var(--dark-fg-2)]" key={item}>
                  {item}
                </div>
              ))}
            </div>
          </aside>
        </div>
      </div>
    </section>
  )
}

function AccessSection({ navigate }) {
  const accessCards = [
    ['Open-Source Core', 'Free - Open-source', 'Local pipeline for positions, fundamentals, watchlist ranking, monthly ranking, reports, and dashboard artifacts.', 'View the workflow', '/workflow', false, ''],
    ['Pro Modules', 'Pricing TBD - Private preview', 'Optional local extensions for deeper evidence review, scenario inspection, and additional dashboards.', siteConfig.ctas.earlyAccess.label, siteConfig.ctas.earlyAccess.href, !siteConfig.ctas.earlyAccess.href, siteConfig.ctas.earlyAccess.pendingPill],
    ['Setup Service', 'Pricing on request - Private preview', 'Guided setup, local environment preparation, input mapping, and first reproducible run support.', siteConfig.ctas.setupService.label, siteConfig.ctas.setupService.href, !siteConfig.ctas.setupService.href, siteConfig.ctas.setupService.pendingPill],
  ]
  return (
    <section className="section" data-screenshot="manifesto-access">
      <div className="container-xl">
        <p className="eyebrow">// ACCESS MODEL</p>
        <h2 className="section-title">Open-source core. Optional help around the workflow.</h2>
        <p className="section-lede">
          The core system is local and artifact-driven. Optional support can help with setup, review workflows, and private-preview extensions without turning the product into a brokerage or guidance service.
        </p>
        <div className="mt-10 grid gap-5 lg:grid-cols-3">
          {accessCards.map(([title, price, body, label, href, pending, pendingLabel]) => (
            <article className="card flex min-h-80 flex-col" key={title}>
              <div className="flex items-start justify-between gap-3">
                <h3 className="text-2xl font-semibold tracking-[-0.03em] text-[color:var(--ink-900)]">{title}</h3>
                <Pill tone={pending ? 'review' : 'ok'}>{pending ? 'pending' : 'available'}</Pill>
              </div>
              <div className="mt-5 rounded-2xl border border-[color:var(--paper-300)] bg-[color:var(--paper-50)] p-4 font-mono text-sm text-[color:var(--ink-700)]">{price}</div>
              <p className="mt-5 flex-1 text-sm leading-6 text-[color:var(--ink-600)]">{body}</p>
              <SmartLink
                className="button button-secondary mt-6"
                href={href || '#'}
                pending={pending}
                onNavigate={href?.startsWith('/') ? navigate : undefined}
                title={pending ? 'Private preview request target pending' : undefined}
              >
                {pending ? pendingLabel : label}
              </SmartLink>
            </article>
          ))}
        </div>
        <p className="mt-6 font-mono text-xs uppercase tracking-[0.14em] text-[color:var(--ink-500)]">Pending access is shown clearly. No fake checkout flow.</p>
      </div>
    </section>
  )
}

function PublicLaunchBlockers() {
  return (
    <section className="section-tight bg-[color:var(--paper-100)]">
      <div className="container-xl">
        <p className="eyebrow">// PUBLIC LAUNCH STATUS</p>
        <h2 className="section-title">Still private preview.</h2>
        <p className="section-lede">This page is intentionally honest about what is not ready for public launch.</p>
        <div className="mt-10 grid gap-4 md:grid-cols-5">
          {publicLaunchBlockers.map(([title, body]) => (
            <article className="card" key={title}>
              <Pill tone="review">pending</Pill>
              <h3 className="mt-4 text-xl font-semibold text-[color:var(--ink-900)]">{title}</h3>
              <p className="mt-3 text-sm leading-6 text-[color:var(--ink-600)]">{body}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}

function ManifestoFinalCta({ navigate }) {
  return (
    <section className="section">
      <div className="container-xl rounded-[1.35rem] border border-[color:var(--paper-300)] bg-white/75 p-7 text-center shadow-sm">
        <p className="eyebrow">// START WITH THE SYSTEM</p>
        <h2 className="mx-auto mt-3 max-w-3xl text-4xl font-semibold tracking-[-0.04em] text-[color:var(--ink-900)] sm:text-5xl">
          One reproducible decision a month. Locally. With evidence.
        </h2>
        <p className="mx-auto mt-5 max-w-2xl text-sm leading-6 text-[color:var(--ink-600)]">
          Start with the workflow, then inspect the evidence, portfolio model, and local dashboard.
        </p>
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <SmartLink className="button button-primary" href="/workflow" onNavigate={navigate}>
            See the workflow
          </SmartLink>
          <SmartLink className="button button-secondary" href="/dashboard" onNavigate={navigate}>
            Open local dashboard
          </SmartLink>
        </div>
      </div>
    </section>
  )
}

function DashboardPage() {
  return (
    <>
      <section className="section pt-32 lg:pt-40" data-screenshot="dashboard-hero">
        <div className="container-xl grid items-center gap-10 lg:grid-cols-[0.82fr_1.18fr]">
          <div>
            <p className="eyebrow hero-eyebrow">// THE LOCAL DASHBOARD</p>
            <h1 className="mt-4 max-w-3xl text-5xl font-semibold leading-[1.02] tracking-[-0.055em] text-[color:var(--ink-900)] sm:text-6xl">
              One local dashboard. Five KPI groups.
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-[color:var(--ink-600)]">
              After each run, the local dashboard server consolidates processed artifacts into one view: portfolio structure, scores, performance, cost & tax, and data quality. Read-only. Localhost. No cloud.
            </p>
            <div className="mt-6 inline-flex rounded-full border border-[color:var(--paper-300)] bg-white/70 px-4 py-2 font-mono text-xs uppercase tracking-[0.12em] text-[color:var(--ink-600)]">
              Private preview - synthetic demo values - decision readiness currently blocked
            </div>
          </div>
          <DashboardPageHeroPanel />
        </div>
      </section>
      <DashboardReadinessStrip />
      <DashboardKpiGroups />
      <DividendSnowballSection />
      <ReinvestComparisonSection />
      <CashflowCalendarSection />
      <BenchmarkCompareSection />
      <CostTaxLedgerSection />
    </>
  )
}

function DashboardPageHeroPanel() {
  return (
    <aside className="dark-panel rounded-[1.35rem] border p-5 sm:p-6 lg:p-8" aria-label="Local Dashboard Viewer private preview">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4 border-b border-[color:var(--dark-600)] pb-4">
        <div>
          <div className="font-mono text-xs uppercase tracking-[0.14em] text-[color:var(--dark-fg-3)]">Local Dashboard Viewer</div>
          <h2 className="mt-2 text-3xl font-semibold tracking-[-0.04em] text-[color:var(--dark-fg)]">Latest local run overview</h2>
        </div>
        <Pill tone="partial">synthetic demo values</Pill>
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        {[
          ['Dashboard', 'REVIEW', 'review'],
          ['Decision', 'BLOCKED', 'missing'],
          ['Handoff', 'REVIEW', 'partial'],
        ].map(([label, value, tone]) => (
          <article className="kpi-card" key={label}>
            <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[color:var(--dark-fg-3)]">{label}</div>
            <div className="mt-3 font-mono text-xl font-semibold text-[color:var(--dark-fg)]">{value}</div>
            <div className="mt-4">
              <Pill tone={tone}>{value}</Pill>
            </div>
          </article>
        ))}
      </div>
      <div className="mt-5 grid gap-3 sm:grid-cols-5">
        {dashboardKpiGroups.map(([title, , , status]) => (
          <article className="rounded-xl border border-[color:var(--dark-600)] bg-[rgba(26,35,44,0.72)] p-3" key={title}>
            <div className="text-[11px] leading-5 text-[color:var(--dark-fg-2)]">{title}</div>
            <div className="mt-3">
              <Pill tone={statusTone(status)}>{status}</Pill>
            </div>
          </article>
        ))}
      </div>
      <div className="artifact-strip mt-5 border-[color:var(--dark-600)] text-[color:var(--dark-fg-3)]">
        <span>source - readiness_payload.sample.json</span>
        <span>localhost view only</span>
        <span>no cloud account</span>
      </div>
    </aside>
  )
}

function DashboardReadinessStrip() {
  return (
    <section className="section-tight bg-[color:var(--paper-100)]">
      <div className="container-xl">
        <p className="eyebrow">// READINESS STRIP</p>
        <div className="mt-6 grid gap-3 md:grid-cols-4 xl:grid-cols-8">
          {dashboardReadinessMetrics.map(([label, value, tone]) => (
            <article className="rounded-2xl border border-[color:var(--paper-300)] bg-white/70 p-4" key={label}>
              <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-[color:var(--ink-400)]">{label}</div>
              <div className="mt-3 font-mono text-xl font-semibold text-[color:var(--ink-900)]">{value}</div>
              <div className="mt-4">
                <Pill tone={tone}>{value}</Pill>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}

function DashboardKpiGroups() {
  return (
    <section className="section" data-screenshot="dashboard-kpi-groups">
      <div className="container-xl">
        <p className="eyebrow">// KPI GROUPS</p>
        <h2 className="section-title">Five KPI groups. One local view.</h2>
        <p className="section-lede">The dashboard is not a prediction engine. It is a local artifact viewer that shows what the latest run can and cannot support.</p>
        <div className="mt-10 grid gap-5 lg:grid-cols-5">
          {dashboardKpiGroups.map(([title, examples, note, status], index) => (
            <article className="dashboard-kpi-panel" key={title}>
              <div className="flex items-center justify-between gap-3">
                <span className="font-mono text-sm text-[color:var(--accent-600)]">0{index + 1}</span>
                <Pill tone={statusTone(status)}>{status}</Pill>
              </div>
              <h3 className="mt-4 text-xl font-semibold text-[color:var(--ink-900)]">{title}</h3>
              <ul className="mt-4 space-y-2 text-sm leading-6 text-[color:var(--ink-600)]">
                {examples.map((item) => (
                  <li key={item}>- {item}</li>
                ))}
              </ul>
              <p className="mt-5 text-xs leading-5 text-[color:var(--ink-500)]">{note}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}

function DividendSnowballSection() {
  return (
    <section className="section-tight bg-[color:var(--paper-100)]" data-screenshot="dashboard-snowball">
      <div className="container-xl grid gap-8 lg:grid-cols-[0.86fr_1.14fr]">
        <div>
          <p className="eyebrow">// DIVIDEND SNOWBALL ANALYSIS</p>
          <h2 className="section-title">Your dividend snowball, modeled honestly.</h2>
          <p className="section-lede">
            Run reproducible income scenarios from your own holdings, your own assumptions, and your own concentration caps. Every assumption is declared. Nothing is predicted.
          </p>
          <div className="mt-6">
            <Pill tone="partial">Illustrative scenario - not a forecast</Pill>
          </div>
        </div>
        <div className="rounded-[1.35rem] border border-[color:var(--paper-300)] bg-white/75 p-5 shadow-sm">
          <div className="grid gap-3 sm:grid-cols-2">
            {snowballMetrics.map(([label, value, status]) => (
              <article className="rounded-2xl border border-[color:var(--paper-300)] bg-[color:var(--paper-50)] p-4" key={label}>
                <div className="font-mono text-[10px] uppercase tracking-[0.14em] text-[color:var(--ink-400)]">{label}</div>
                <div className="mt-3 text-lg font-semibold text-[color:var(--ink-900)]">{value}</div>
                <div className="mt-4">
                  <Pill tone={statusTone(status)}>{status}</Pill>
                </div>
              </article>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

function ReinvestComparisonSection() {
  return (
    <section className="section">
      <div className="container-xl">
        <p className="eyebrow">// REINVEST COMPARISON</p>
        <h2 className="section-title">Two scenarios. Same starting point.</h2>
        <p className="section-lede">Compare declared assumptions with and without reinvestment. The output is illustrative, not a forecast.</p>
        <div className="mt-8 grid gap-5 md:grid-cols-2">
          {[
            ['Cash income path', 'Declared cash withdrawals stay separate from reinvest assumptions.', 'PARTIAL'],
            ['Reinvested path', 'Compounding effect is shown as a scenario, never as a promised result.', 'REVIEW'],
          ].map(([title, body, status]) => (
            <article className="card" key={title}>
              <div className="flex items-center justify-between gap-3">
                <h3 className="text-xl font-semibold text-[color:var(--ink-900)]">{title}</h3>
                <Pill tone={statusTone(status)}>{status}</Pill>
              </div>
              <p className="mt-4 text-sm leading-6 text-[color:var(--ink-600)]">{body}</p>
            </article>
          ))}
        </div>
        <div className="mt-8 rounded-[1.35rem] bg-[color:var(--ink-900)] px-6 py-7 text-center text-2xl font-semibold tracking-[-0.03em] text-[color:var(--paper-50)] sm:text-3xl">
          REINVESTMENT CAN CHANGE THE INCOME PATH - IN THIS ILLUSTRATIVE SCENARIO.
        </div>
      </div>
    </section>
  )
}

function CashflowCalendarSection() {
  return (
    <section className="section-tight bg-[color:var(--paper-100)]" data-screenshot="dashboard-calendar">
      <div className="container-xl">
        <p className="eyebrow">// CASHFLOW CALENDAR</p>
        <h2 className="section-title">See your dividend rhythm before it happens.</h2>
        <p className="section-lede">A calendar view can show declared dividend timing assumptions and known payment rhythm. Missing or unverified data stays visible.</p>
        <div className="mt-10 grid gap-3 md:grid-cols-6 xl:grid-cols-12">
          {cashflowMonths.map(([month, status]) => (
            <article className="calendar-cell" key={month}>
              <div className="font-mono text-xs text-[color:var(--ink-500)]">{month}</div>
              <div className="mt-4">
                <Pill tone={statusTone(status === 'Known' ? 'OK' : status === 'Estimated' ? 'PARTIAL' : status === 'Review' ? 'REVIEW' : 'MISSING_DATA')}>{status}</Pill>
              </div>
            </article>
          ))}
        </div>
        <div className="mt-5 flex flex-wrap gap-2">
          {['Known', 'Estimated', 'Missing', 'Review'].map((label) => (
            <span className="rounded-full border border-[color:var(--paper-300)] bg-white/70 px-3 py-1 font-mono text-xs text-[color:var(--ink-600)]" key={label}>
              {label}
            </span>
          ))}
        </div>
      </div>
    </section>
  )
}

function BenchmarkCompareSection() {
  return (
    <section className="section">
      <div className="container-xl grid gap-8 lg:grid-cols-[0.82fr_1.18fr]">
        <div>
          <p className="eyebrow">// MULTI-BENCHMARK CONTEXT</p>
          <h2 className="section-title">Compare against local benchmark archives.</h2>
          <p className="section-lede">Benchmark views only become meaningful when enough local history exists. Until then, the dashboard says so.</p>
          <div className="mt-6">
            <Pill tone="partial">Requires explicit local benchmark archive - not a prediction</Pill>
          </div>
        </div>
        <div className="rounded-[1.35rem] border border-[color:var(--paper-300)] bg-white/75 p-5 shadow-sm">
          {benchmarkRows.map(([label, value, status]) => (
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[color:var(--paper-200)] py-4 last:border-b-0" key={label}>
              <div>
                <div className="font-semibold text-[color:var(--ink-900)]">{label}</div>
                <div className="mt-1 text-sm text-[color:var(--ink-500)]">{value}</div>
              </div>
              <Pill tone={statusTone(status)}>{status}</Pill>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

function CostTaxLedgerSection() {
  return (
    <section className="section-tight bg-[color:var(--paper-100)]">
      <div className="container-xl">
        <p className="eyebrow">// COST / TAX LEDGER</p>
        <h2 className="section-title">Costs and taxes stay in the ledger.</h2>
        <p className="section-lede">
          Gross dividends, withholding taxes, realized PnL, tax drag, and fee drag require explicit local evidence. Missing documentation is not silently filled.
        </p>
        <div className="mt-6">
          <Pill tone="review">Requires explicit cost/tax ledger evidence</Pill>
        </div>
        <div className="mt-8 grid gap-4 md:grid-cols-4">
          {costTaxRows.map(([label, value, status]) => (
            <article className="card" key={label}>
              <h3 className="text-lg font-semibold text-[color:var(--ink-900)]">{label}</h3>
              <p className="mt-3 text-sm leading-6 text-[color:var(--ink-600)]">{value}</p>
              <div className="mt-5">
                <Pill tone={statusTone(status)}>{status}</Pill>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}

function SloganBar() {
  return (
    <div className="border-y border-[color:var(--dark-600)] bg-[color:var(--dark-900)] px-5 py-5 text-center font-mono text-xs uppercase tracking-[0.18em] text-[color:var(--dark-fg)]">
      {slogans.join('  ')}
    </div>
  )
}

function Footer({ navigate }) {
  return (
    <>
      <section className="section-tight dark-panel border-y border-[color:var(--dark-600)]" data-screenshot="footer-cta">
        <div className="container-xl max-w-4xl">
          <p className="eyebrow text-[color:var(--dark-accent)]">// PRIVATE PREVIEW</p>
          <h2 className="mt-4 text-4xl font-semibold tracking-[-0.04em] text-[color:var(--dark-fg)] sm:text-5xl">BUILT FOR INVESTORS, NOT TRADERS.</h2>
          <p className="mt-5 max-w-2xl text-lg leading-8 text-[color:var(--dark-fg-2)]">
            Public launch remains blocked until real access targets, imprint, privacy policy, pricing scope and launch review are complete.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <SmartLink className="button button-primary" href="/workflow#sample-report" onNavigate={navigate}>
              Read a sample monthly report
            </SmartLink>
            <SmartLink className="button button-quiet" href="/workflow" onNavigate={navigate}>
              See the workflow
            </SmartLink>
          </div>
        </div>
      </section>
      <footer className="section-tight" data-screenshot="footer-disclaimer">
        <div className="container-xl">
          <div className="rounded-3xl border border-[color:var(--paper-300)] bg-white/60 p-6 text-sm leading-7 text-[color:var(--ink-600)]">
            <p>
              <strong className="text-[color:var(--ink-900)]">{siteConfig.productName}</strong> is local research-support software. It does not provide financial, tax, or legal guidance, does not guarantee returns, and does not connect to brokerages. All product UI values on this private preview are synthetic, sanitized, or aggregated.
            </p>
          </div>
          <div className="mt-8 flex flex-wrap items-center justify-between gap-4 text-xs text-[color:var(--ink-500)]">
            <img src={wordmarkInk} alt={`${siteConfig.productName} wordmark`} className="h-6 w-auto" />
            <span>No cloud account required. Core runs locally. No broker connection.</span>
          </div>
          <div className="mt-5 flex flex-wrap gap-x-5 gap-y-2 font-mono text-xs">
            <span className="footer-link-pending">Imprint pending</span>
            <span className="footer-link-pending">Privacy pending</span>
            <SmartLink href="/workflow" onNavigate={navigate} className="text-[color:var(--ink-600)] hover:text-[color:var(--ink-900)]">
              Workflow
            </SmartLink>
          </div>
        </div>
      </footer>
      <SloganBar />
    </>
  )
}

export default function App() {
  const { route, navigate } = useRoute()
  const page =
    route === '/workflow' ? (
      <WorkflowPage navigate={navigate} />
    ) : route === '/evidence' ? (
      <EvidencePage navigate={navigate} />
    ) : route === '/portfolio' ? (
      <PortfolioPage navigate={navigate} />
    ) : route === '/dashboard' ? (
      <DashboardPage />
    ) : route === '/manifesto' ? (
      <ManifestoPage navigate={navigate} />
    ) : (
      <HomePage navigate={navigate} />
    )
  return (
    <div className="site-shell">
      <Header route={route} navigate={navigate} />
      <main>{page}</main>
      <Footer navigate={navigate} />
    </div>
  )
}

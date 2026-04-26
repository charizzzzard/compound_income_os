import wordmarkInk from './assets/wordmark-ink.svg'
import wordmarkPaper from './assets/wordmark-paper.svg'

const navItems = [
  ['Product', '#product'],
  ['Workflow', '#workflow'],
  ['Evidence', '#evidence'],
  ['Access', '#access'],
]

const ctaTargets = {
  earlyAccess: 'mailto:early-access@example.invalid?subject=Compound%20Income%20OS%20Early%20Access',
  githubAccess: 'mailto:early-access@example.invalid?subject=Compound%20Income%20OS%20GitHub%20Access',
  setupService: 'mailto:early-access@example.invalid?subject=Compound%20Income%20OS%20Setup%20Service',
}

const dashboardKpis = [
  ['Portfolio Value', '€128,420', 'Synthetic demo value', 'ok', 'OK'],
  ['Cash Weight', '8.4%', 'Reserve inside rule band', 'ok', 'OK'],
  ['Positions', '24', 'Two review cases', 'partial', 'PARTIAL'],
  ['Top 5 Weight', '38.7%', 'Within cap', 'ok', 'OK'],
  ['Data Quality', 'PARTIAL', 'Review needed', 'partial', 'PARTIAL'],
  ['Monthly Candidate', 'REVIEW', 'Review required', 'review', 'REVIEW'],
  ['Dividend Income TTM', '€3,240', 'Synthetic demo value', 'partial', 'PARTIAL'],
  ['Dividend Growth 5Y', '7.8%', 'Synthetic demo value', 'partial', 'PARTIAL'],
  ['Valuation Band', 'Fair / Watch', 'Valuation review', 'review', 'REVIEW'],
  ['Review Flags', '6', 'Open artifacts', 'review', 'REVIEW'],
]

const principles = [
  ['Local-first', 'Runs from local files and emits local CSV and Markdown artifacts.'],
  ['Privacy-first', 'Raw portfolio inputs remain under user control and separate from processed outputs.'],
  ['No cloud lock-in', 'Core workflow is portable files and code. No cloud account required.'],
  ['No broker execution', 'The system documents, ranks, and reports. It does not place orders.'],
  ['Evidence-only', 'Missing data remains visible; values are not guessed or silently imputed.'],
  ['Reproducible reports', 'Runs record inputs, manifests, and generated artifacts for later review.'],
]

const workflowSteps = [
  ['Broker export in', 'Normalize local position files into a snapshot artifact.'],
  ['Data quality check', 'Gate holdings with explicit coverage and profile statuses.'],
  ['Scoring & ranking', 'Compute rule-based candidate scores from available evidence.'],
  ['Dividend impact', 'Show synthetic scenario contribution under declared assumptions.'],
  ['Monthly decision report', 'Explain candidate status, blockers, and data gaps in Markdown.'],
  ['Decision journal', 'Preserve the reasoning beside the run artifacts.'],
]

const coreFeatures = [
  ['Portfolio Snapshot', 'Local position snapshot with allocation and concentration context.'],
  ['SEC Evidence Pipeline', 'Read-only SEC CompanyFacts path for reviewed eligible US stock identities.'],
  ['Evidence-Applied Fundamentals', 'Separate evidence-applied master that preserves traceability.'],
  ['Data Quality Gates', 'COVERED, PARTIAL, REVIEW, NO_MATCH, MISSING_DATA, INSUFFICIENT_INPUTS, INSUFFICIENT_HISTORY.'],
  ['Watchlist Ranking', 'Candidate list ordered by transparent score and rule components.'],
  ['Monthly Ranking', 'Cash-aware queue with blockers, review states, and rule constraints.'],
  ['Dividend Snowball Analysis', 'Illustrative income scenario from declared inputs and assumptions.'],
  ['Valuation Bands', 'Fair, watch, and review context without certainty language.'],
  ['Monthly Decision Report', 'Markdown artifact for the current run and data state.'],
  ['Decision Journal', 'Re-readable record of the current rule set and decision context.'],
  ['Local Dashboard', 'Processed artifact consolidation for KPI inspection.'],
]

const statusLabels = [
  'COVERED',
  'PARTIAL',
  'REVIEW',
  'NO_MATCH',
  'MISSING_DATA',
  'INSUFFICIENT_INPUTS',
  'INSUFFICIENT_HISTORY',
]

const accessCards = [
  {
    title: 'Open-Source Core',
    price: 'Core workflow',
    body: 'Local pipeline for positions, fundamentals, watchlist ranking, monthly ranking, reports, and dashboard artifacts.',
    cta: 'Request GitHub Access',
  },
  {
    title: 'Pro Modules',
    price: 'Optional extensions',
    body: 'Additional local workflows for deeper evidence review, dashboards, and scenario inspection where the module exists.',
    cta: 'Join Early Access',
  },
  {
    title: 'Setup Service',
    price: 'Implementation help',
    body: 'Guided setup, local environment preparation, input mapping, and first reproducible run support.',
    cta: 'Request Setup Service',
  },
  {
    title: 'GitHub Sponsors / Early Access',
    price: 'Support channel',
    body: 'Follow build progress, support the project, and request access to the repository workflow.',
    cta: 'Join Early Access',
  },
]

function Pill({ tone = 'partial', children }) {
  return <span className={`pill pill-${tone}`}>{children}</span>
}

function Header() {
  return (
    <header className="fixed inset-x-0 top-0 z-50 border-b border-[color:var(--paper-300)] bg-[rgba(251,250,247,0.86)] px-5 py-3 backdrop-blur-xl sm:px-8">
      <nav className="mx-auto flex max-w-7xl items-center justify-between gap-4" aria-label="Main navigation">
        <a href="#top" className="rounded-md" aria-label="Compound Income OS home">
          <img src={wordmarkInk} alt="Compound Income OS wordmark" className="h-7 w-auto" />
        </a>
        <div className="hidden items-center gap-7 md:flex">
          {navItems.map(([label, href]) => (
            <a key={label} href={href} className="text-sm font-medium text-[color:var(--ink-600)] hover:text-[color:var(--ink-900)]">
              {label}
            </a>
          ))}
        </div>
        <div className="hidden items-center gap-2 lg:flex">
          <a className="button button-secondary px-4 py-2" href={ctaTargets.githubAccess}>
            Request GitHub Access
          </a>
          <a className="button button-primary px-4 py-2" href={ctaTargets.earlyAccess}>
            Join Early Access
          </a>
        </div>
        <a className="button button-primary whitespace-nowrap px-4 py-2 text-xs md:hidden" href={ctaTargets.earlyAccess}>
          <span className="sm:hidden">Join</span>
          <span className="hidden sm:inline">Early Access</span>
        </a>
      </nav>
    </header>
  )
}

function Hero() {
  return (
    <section id="top" className="section pt-32 lg:pt-40" data-screenshot="hero">
      <div className="container-xl grid items-center gap-12 lg:grid-cols-[0.95fr_1.05fr]">
        <div>
          <p className="eyebrow">Local-first portfolio research</p>
          <h1 className="mt-4 max-w-3xl text-5xl font-semibold leading-[1.02] tracking-[-0.055em] text-[color:var(--ink-900)] sm:text-6xl lg:text-7xl">
            A local operating system for long-term investing.
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-[color:var(--ink-600)]">
            Compound Income OS turns your broker exports, fundamentals, and evidence files into reproducible rankings,
            dashboards, and monthly decision reports. Local-first. No broker execution. Not investment advice.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <a className="button button-primary" href={ctaTargets.earlyAccess}>
              Join Early Access
            </a>
            <a className="button button-secondary" href={ctaTargets.githubAccess}>
              Request GitHub Access
            </a>
          </div>
          <p className="mt-5 font-mono text-xs tracking-[0.04em] text-[color:var(--ink-500)]">
            Open-source core. No cloud account required. Not investment advice.
          </p>
          <div className="mt-10 grid max-w-xl grid-cols-3 gap-4 border-t border-[color:var(--paper-300)] pt-5">
            {[
              ['Mode', 'Local files'],
              ['Outputs', 'CSV / Markdown'],
              ['Broker', 'No connection'],
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
          <span className="font-mono text-xs tracking-[0.06em] text-[color:var(--dark-fg-3)]">manifest · local run</span>
        </div>
        <Pill tone="partial">synthetic demo values</Pill>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        {[
          ['Portfolio Value', '€128,420', 'ok', 'OK'],
          ['Data Quality', 'PARTIAL', 'partial', 'PARTIAL'],
          ['Monthly Candidate', 'REVIEW', 'review', 'REVIEW'],
          ['Dividend Income TTM', '€3,240', 'partial', 'PARTIAL'],
        ].map(([label, value, tone, pill]) => (
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
            <div className="mt-2 font-mono text-sm text-[color:var(--dark-fg-2)]">Dividend income scenario · Not a forecast.</div>
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

      <div className="artifact-strip mt-5 border-[color:var(--dark-600)] text-[color:var(--dark-fg-3)]">
        <span>run · manifest visible</span>
        <span>source · processed artifacts</span>
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
              <span className="font-mono text-xs tracking-[0.06em] text-[color:var(--dark-fg-3)]">local · monthly run</span>
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
                  <p className="mt-2 text-sm text-[color:var(--dark-fg-2)]">Illustrative line from synthetic demo values. Not a forecast.</p>
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
            <span>artifact · positions_snapshot.csv</span>
            <span>artifact · company_scores.csv</span>
            <span>artifact · dashboard_kpis.csv</span>
            <span>manifest · deterministic local run</span>
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
          <h2 className="section-title">Where long-term portfolios actually fail.</h2>
          <p className="section-lede">
            Research fragments over time. Broker exports live in one place, fundamentals in another, and evidence in files
            that are hard to reconstruct when a monthly decision needs context.
          </p>
          <div className="mt-10 grid gap-5 md:grid-cols-3">
            {[
              ['Data drift', 'Position, fundamentals, and watchlist files change without a durable run record.'],
              ['Evidence gaps', 'Missing KPIs are often hidden inside spreadsheets instead of surfaced as status.'],
              ['Process loss', 'The reasoning behind a monthly decision is rarely stored beside the artifacts that produced it.'],
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
            Compound Income OS treats the research workflow as a local pipeline: declared inputs in, deterministic artifacts
            out, with data quality and evidence status visible at each step.
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
        <h2 className="section-title">Architecture-level guardrails, not marketing slogans.</h2>
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
        <h2 className="section-title">Six stages from input files to decision journal.</h2>
        <div className="mt-10 grid gap-4 md:grid-cols-2 xl:grid-cols-6">
          {workflowSteps.map(([title, body], index) => (
            <article className="card relative min-h-48" key={title}>
              <div className="font-mono text-sm text-[color:var(--accent-600)]">0{index + 1}</div>
              <h3 className="mt-4 font-semibold text-[color:var(--ink-900)]">{title}</h3>
              <p className="mt-3 text-sm leading-6 text-[color:var(--ink-600)]">{body}</p>
            </article>
          ))}
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
        <h2 className="section-title">One local pipeline. Eleven ways to inspect the evidence.</h2>
        <div className="mt-10 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
          {coreFeatures.map(([title, body]) => (
            <article className="card" key={title}>
              <h3 className="text-lg font-semibold text-[color:var(--ink-900)]">{title}</h3>
              <p className="mt-3 text-sm leading-6 text-[color:var(--ink-600)]">{body}</p>
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
          <h2 className="section-title">A scenario surface for income assumptions.</h2>
          <p className="section-lede">
            This view shows current dividend income, candidate contribution, concentration caps, and manual reinvestment
            assumptions as a reproducible scenario. It is explicitly not a prediction.
          </p>
          <div className="mt-6">
            <Pill tone="review">Illustrative calculation. Not a forecast.</Pill>
          </div>
        </div>
        <div className="dark-panel rounded-3xl border p-6">
          <div className="grid gap-4 sm:grid-cols-2">
            {[
              ['Current Dividend Income TTM', '€3,240'],
              ['Candidate contribution', '€42 illustrative annualized'],
              ['Cash deployment assumption', '€300 review amount'],
              ['Data quality status', 'PARTIAL / Review needed'],
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
            <span>source · dividend_snowball.csv</span>
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
            Eligible US stock data can move through reviewed identity inputs, SEC CompanyFacts snapshots, an evidence
            registry, a research backlog, and proposed updates. The fundamentals master is not silently mutated.
          </p>
          <div className="mt-6 space-y-3">
            {['reviewed identity inputs', 'SEC CompanyFacts snapshot', 'evidence registry', 'research backlog', 'proposed updates'].map((item) => (
              <div key={item} className="flex items-center justify-between gap-4 border-b border-[color:var(--paper-300)] pb-3">
                <span className="text-sm text-[color:var(--ink-700)]">{item}</span>
                <Pill tone="partial">visible</Pill>
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
          <div className="mt-6 flex flex-wrap gap-2">
            {statusLabels.map((status) => (
              <Pill key={status} tone={status === 'COVERED' ? 'ok' : status === 'MISSING_DATA' ? 'missing' : status === 'REVIEW' ? 'review' : 'partial'}>
                {status}
              </Pill>
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
          <ul className="mt-6 space-y-4 text-sm leading-6 text-[color:var(--ink-600)]">
            {['Dividend-growth investors', 'Quality-compounder investors', 'Engineers, analysts, and finance/data professionals', 'Independent operators'].map((item) => (
              <li key={item} className="border-b border-[color:var(--paper-300)] pb-3">
                <span className="font-semibold text-[color:var(--ink-900)]">{item}</span>
              </li>
            ))}
          </ul>
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
        <h2 className="section-title">Open-source core, optional help around the workflow.</h2>
        <div className="mt-10 grid gap-5 md:grid-cols-2 xl:grid-cols-4">
          {accessCards.map((card) => (
            <article className="card flex flex-col" key={card.title}>
              <h3 className="text-xl font-semibold text-[color:var(--ink-900)]">{card.title}</h3>
              <div className="mt-2 font-mono text-sm text-[color:var(--gold-700)]">{card.price}</div>
              <p className="mt-4 flex-1 text-sm leading-6 text-[color:var(--ink-600)]">{card.body}</p>
              <a className="button button-secondary mt-6" href={ctaHrefFor(card.cta)}>
                {card.cta}
              </a>
            </article>
          ))}
        </div>
      </div>
    </section>
  )
}

function FinalCtaFooter() {
  return (
    <>
      <section id="early-access" className="section dark-panel border-y border-[color:var(--dark-600)]" data-screenshot="final-cta">
        <div className="container-xl max-w-4xl">
          <p className="eyebrow text-[color:var(--dark-accent)]">Final CTA</p>
          <h2 className="mt-4 text-4xl font-semibold tracking-[-0.04em] text-[color:var(--dark-fg)] sm:text-5xl">
            Start with the workflow, not the trade.
          </h2>
          <p className="mt-5 max-w-2xl text-lg leading-8 text-[color:var(--dark-fg-2)]">
            Join the early access list or request repository access to review the local-first workflow.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <a className="button button-primary" href={ctaTargets.earlyAccess}>
              Join Early Access
            </a>
            <a className="button button-quiet" href={ctaTargets.githubAccess}>
              Request GitHub Access
            </a>
            <a className="button button-quiet" href={ctaTargets.setupService}>
              Request Setup Service
            </a>
          </div>
        </div>
      </section>

      <footer className="section-tight" data-screenshot="footer">
        <div className="container-xl">
          <div className="rounded-3xl border border-[color:var(--paper-300)] bg-white/60 p-6 text-sm leading-7 text-[color:var(--ink-600)]">
            <strong className="text-[color:var(--ink-900)]">Compound Income OS</strong> is a research and
            decision-support tool. It does not provide investment, tax, or legal advice, does not guarantee any return,
            and does not execute orders or connect to brokerages. All decisions, risks, and outcomes remain solely with
            the user. Past data does not predict future results. Illustrative figures shown throughout this page are
            synthetic demo values for design purposes only.
          </div>
          <div className="mt-8 flex flex-wrap items-center justify-between gap-4 text-xs text-[color:var(--ink-500)]">
            <img src={wordmarkInk} alt="Compound Income OS wordmark" className="h-6 w-auto" />
            <span>No cloud account required. Core runs locally. No broker connection.</span>
          </div>
        </div>
      </footer>
    </>
  )
}

function ctaHrefFor(label) {
  if (label === 'Request GitHub Access') {
    return ctaTargets.githubAccess
  }
  if (label === 'Request Setup Service') {
    return ctaTargets.setupService
  }
  return ctaTargets.earlyAccess
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

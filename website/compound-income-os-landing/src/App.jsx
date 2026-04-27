import { useEffect, useState } from 'react'

import wordmarkInk from './assets/wordmark-ink.svg'
import wordmarkPaper from './assets/wordmark-paper.svg'
import { siteConfig } from './siteConfig'

const safeRoutes = [
  ['Workflow', '/workflow', false],
  ['Evidence', '#planned-evidence', true],
  ['Portfolio', '#planned-portfolio', true],
  ['Dashboard', '#dashboard-viewer', false],
  ['Manifesto', '#manifesto-teaser', true],
]

const promises = [
  ['Workflow', 'One decision a month - same six stages, every month.', '/workflow', false],
  ['Evidence', 'Nothing is silently filled.', '#planned-evidence', true],
  ['Portfolio', 'Four sleeves. One mandate. Visible rules.', '#planned-portfolio', true],
  ['Dashboard', 'One local dashboard. Five KPI groups.', '#dashboard-viewer', false],
  ['Manifesto / Access', 'Open-source core. Builder-led. No venture capital.', '#manifesto-teaser', true],
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

const slogans = ['BUILT SLOW', 'USED MONTHLY', 'PRIVACY BY DEFAULT', 'NO HYPE', 'JUST SIGNAL', 'YOUR DATA', 'YOUR MACHINE']

function currentRoute() {
  return window.location.pathname === '/workflow' ? '/workflow' : '/'
}

function useRoute() {
  const [route, setRoute] = useState(currentRoute)
  useEffect(() => {
    const onPop = () => setRoute(currentRoute())
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])
  const navigate = (href) => {
    if (href?.startsWith('/workflow')) {
      const [path, hash] = href.split('#')
      window.history.pushState({}, '', href)
      setRoute('/workflow')
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
      <BuilderTeaser />
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

function BuilderTeaser() {
  return (
    <section id="manifesto-teaser" className="section-tight bg-[color:var(--paper-100)]">
      <div className="container-xl grid gap-6 rounded-3xl border border-[color:var(--paper-300)] bg-white/60 p-7 lg:grid-cols-[1fr_0.7fr]">
        <div>
          <p className="eyebrow">// BUILDER NOTE</p>
          <h2 className="mt-3 text-3xl font-semibold tracking-[-0.035em] text-[color:var(--ink-900)]">Open-source core. Builder-led. No venture capital.</h2>
          <p className="mt-4 max-w-3xl leading-7 text-[color:var(--ink-600)]">
            The full manifesto and access page is intentionally deferred. This private preview keeps pending public-launch items visible instead of pretending they are complete.
          </p>
        </div>
        <div className="rounded-2xl border border-[color:var(--paper-300)] bg-[color:var(--paper-50)] p-5">
          <div className="font-mono text-xs uppercase tracking-[0.14em] text-[color:var(--accent-600)]">planned in later wave</div>
          <p className="mt-3 text-sm leading-6 text-[color:var(--ink-600)]">Evidence page, portfolio page, local dashboard page and manifesto page remain planned placeholders in Wave 1.</p>
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

function WorkflowPage() {
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
  return (
    <div className="site-shell">
      <Header route={route} navigate={navigate} />
      <main>{route === '/workflow' ? <WorkflowPage /> : <HomePage navigate={navigate} />}</main>
      <Footer navigate={navigate} />
    </div>
  )
}

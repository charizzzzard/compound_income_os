window.ProblemSection = function ProblemSection() {
  return (
    <section className="section" id="product">
      <div className="section-inner">
        <div className="t-eyebrow section-eyebrow">Problem</div>
        <h2 className="section-title">Most long-term portfolios don't fail in market crashes. They fail in slow motion.</h2>
        <p className="section-lede">Position sizes drift past the limits you set. Theses age out without anyone noticing. Evidence — the screenshots, the 10-K passages, the reason you bought — scatters across folders, browsers, and memory. By the time conviction matters, the reasoning behind it is already gone.</p>
        <div style={{ marginTop: "var(--space-10)" }}>
          <div className="callout"><div className="callout-num">01</div><div className="callout-body">Spreadsheets help — until they sprawl.</div></div>
          <div className="callout"><div className="callout-num">02</div><div className="callout-body">Dashboards help — until they're cloud-locked.</div></div>
          <div className="callout"><div className="callout-num">03</div><div className="callout-body">Screeners help — until you realize a screener can't document a decision.</div></div>
        </div>
      </div>
    </section>
  );
};

window.SolutionSection = function SolutionSection() {
  return (
    <section className="section section-tight" style={{ background: "var(--bg-muted)" }}>
      <div className="section-inner">
        <div className="t-eyebrow section-eyebrow">Solution</div>
        <h2 className="section-title">The portfolio as local infrastructure.</h2>
        <p className="section-lede">Compound Income OS takes the files you already have — broker positions, fundamentals data, your watchlist, your evidence — and runs them through a deterministic pipeline. The outputs are CSV and Markdown artifacts. Inputs you control. Outputs you can re-read in two years. Nothing uploaded, nothing executed, nothing invented.</p>
      </div>
    </section>
  );
};

window.PrinciplesSection = function PrinciplesSection() {
  const items = [
    ["Local-first", "Inputs and outputs are local files. The core runs on your machine."],
    ["Privacy-first", "Raw portfolio data is kept separate from processed artifacts. No telemetry."],
    ["No cloud lock-in", "The pipeline is files and code. Move it, fork it, archive it."],
    ["No broker execution", "The system documents and proposes. It never places orders."],
    ["Evidence-only", "Missing fundamentals stay flagged — first-class status codes, never guessed values."],
    ["Reproducible reports", "Each run records its inputs, manifest, and artifacts. Re-runs are deterministic."],
  ];
  return (
    <section className="section">
      <div className="section-inner">
        <div className="t-eyebrow section-eyebrow">Product principles</div>
        <h2 className="section-title">Six principles, enforced by the architecture.</h2>
        <div className="grid-3" style={{ marginTop: "var(--space-10)" }}>
          {items.map(([t,b]) => (
            <div className="feature" key={t}>
              <div className="feature-title">{t}</div>
              <div className="feature-body">{b}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

window.WorkflowSection = function WorkflowSection() {
  const steps = [
    ["Broker export in", "Drop your CSV into the inputs folder. The position parser normalizes it."],
    ["Data quality check", "Coverage is computed against your fundamentals master."],
    ["Scoring & ranking", "Business, valuation, and rule-based candidate scores applied."],
    ["Dividend impact", "The snowball updates against weights and rules."],
    ["Monthly decision report", "Markdown report explains every candidate."],
    ["Decision journal", "Reasoning captured as an artifact, not a tab you'll close."],
  ];
  return (
    <section className="section" id="workflow">
      <div className="section-inner">
        <div className="t-eyebrow section-eyebrow">Monthly workflow</div>
        <h2 className="section-title">A cadence built for long horizons.</h2>
        <div className="workflow" style={{ marginTop: "var(--space-10)" }}>
          {steps.map(([t,b]) => (
            <div className="workflow-step" key={t}>
              <div className="workflow-title">{t}</div>
              <div className="workflow-body">{b}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

window.FeaturesSection = function FeaturesSection() {
  const items = [
    ["Portfolio Snapshot", "Positions normalized from broker exports into a deterministic snapshot artifact."],
    ["SEC Evidence Pipeline", "Read-only, gated workflow that proposes — never silently applies — fundamentals updates."],
    ["Evidence-Applied Fundamentals", "Reviewed proposals enter the master through an explicit, traceable apply step."],
    ["Data Quality Gates", "COVERED, PARTIAL, REVIEW, MISSING_DATA, INSUFFICIENT_HISTORY — first-class outputs."],
    ["Watchlist Ranking", "Candidates ordered by transparent business, valuation, and rule-based candidate-score components."],
    ["Monthly Ranking", "Cash-aware, rule-based decision queue — eligible, deferred, blocked."],
    ["Dividend Snowball Analysis", "Illustrative income calculation from declared rates, weights, and rules."],
    ["Valuation Bands", "Per-holding valuation status, never a forecast, never a buy signal."],
    ["Monthly Decision Report", "Markdown report with candidate rationale, constraints, and blockers."],
    ["Decision Journal", "Each cycle's reasoning preserved as a re-readable artifact."],
    ["Local Dashboard", "Five views consolidating processed artifacts. Every KPI traces back to a source file."],
  ];
  return (
    <section className="section section-tight" style={{ background: "var(--bg-muted)" }} id="evidence">
      <div className="section-inner">
        <div className="t-eyebrow section-eyebrow">Core features</div>
        <h2 className="section-title">One local pipeline. Eleven ways to inspect the evidence.</h2>
        <div className="grid-3" style={{ marginTop: "var(--space-10)" }}>
          {items.map(([t,b]) => (
            <div className="feature" key={t}>
              <div className="feature-title">{t}</div>
              <div className="feature-body">{b}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

window.SpecialSections = function SpecialSections() {
  return (
    <section className="section">
      <div className="section-inner" style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "var(--space-6)" }}>
        <div>
          <div className="t-eyebrow section-eyebrow">Dividend snowball</div>
          <h3 className="t-h3" style={{ margin: "0 0 12px" }}>An illustrative calculation, not a forecast.</h3>
          <p className="t-body" style={{ color: "var(--fg-muted)" }}>Tracks projected income across holdings and watchlist against your weights and rules. The number is reproducible from the inputs you supplied — declared rates, current weights, candidate buys, rule-based caps.</p>
        </div>
        <div>
          <div className="t-eyebrow section-eyebrow">SEC evidence pipeline</div>
          <h3 className="t-h3" style={{ margin: "0 0 12px" }}>Read-only. Reviewed. Optional.</h3>
          <p className="t-body" style={{ color: "var(--fg-muted)" }}>For eligible US-listed holdings, the pipeline refreshes a snapshot from SEC CompanyFacts and proposes — never silently applies — updates to your fundamentals master. You decide what enters.</p>
        </div>
        <div>
          <div className="t-eyebrow section-eyebrow">Data quality gates</div>
          <h3 className="t-h3" style={{ margin: "0 0 12px" }}>Missing data stays visible.</h3>
          <p className="t-body" style={{ color: "var(--fg-muted)" }}>Coverage statuses are first-class outputs. Holdings with insufficient evidence don't get force-classified. They get flagged for review and stay visible until you address them.</p>
        </div>
      </div>
    </section>
  );
};

window.JournalAndAudience = function JournalAndAudience() {
  return (
    <section className="section section-tight" style={{ background: "var(--bg-muted)" }}>
      <div className="section-inner" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-12)", alignItems: "start" }}>
        <div>
          <div className="t-eyebrow section-eyebrow">Decision journal</div>
          <h3 className="t-h3" style={{ margin: "0 0 12px" }}>The audit trail your future self will need.</h3>
          <p className="t-body" style={{ color: "var(--fg-muted)" }}>Two years from now, you can open last August's file and reconstruct exactly why a position was added, deferred, or left alone.</p>
          <pre style={{
            marginTop: 18, padding: 18, background: "var(--bg-elevated)",
            border: "1px solid var(--border-default)", borderRadius: 12,
            font: "400 12px/1.6 var(--font-mono)", color: "var(--ink-700)", whiteSpace: "pre-wrap"
          }}>
{`# decision_journal_2026-04.md
run_id: DEMO-20260426-160500
candidates_eligible: 2
candidates_deferred: 2
review_required: 1
notes:
  - DGB: meets dividend + valuation gates;
    candidate allocation: €300 under current rule set.
  - QCA: high candidate score; valuation gate
    not attractive enough for new capital.`}
          </pre>
        </div>
        <div>
          <div className="t-eyebrow section-eyebrow">Audience</div>
          <h3 className="t-h3" style={{ margin: "0 0 12px" }}>Built for the way you already work.</h3>
          <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "grid", gap: 14 }}>
            <li><strong style={{ color: "var(--fg-strong)" }}>Dividend-growth investors</strong> — maintaining a fundamentals master and a multi-year reinvestment plan.</li>
            <li><strong style={{ color: "var(--fg-strong)" }}>Quality-compounder investors</strong> — scoring on durability, returns on capital, and valuation discipline.</li>
            <li><strong style={{ color: "var(--fg-strong)" }}>Engineers, analysts, finance/data professionals</strong> — preferring reproducible files over cloud dashboards.</li>
            <li><strong style={{ color: "var(--fg-strong)" }}>Independent operators</strong> — who want decisions documented, data on their machine, and no broker integration in the loop.</li>
          </ul>
        </div>
      </div>
    </section>
  );
};

window.AccessSection = function AccessSection() {
  return (
    <section className="section" id="access">
      <div className="section-inner">
        <div className="t-eyebrow section-eyebrow">Access · monetization</div>
        <h2 className="section-title">Open core. Paid where it earns its keep.</h2>
        <div className="grid-4" style={{ marginTop: "var(--space-10)" }}>
          <div className="access-card">
            <div className="access-card-eyebrow">Open-source core</div>
            <div className="access-card-title">Core</div>
            <div className="access-card-price">Free</div>
            <div className="access-card-body">Full local pipeline: positions, scoring, watchlist, monthly ranking, snapshot, decision report, dashboard layer. Installable on your machine. No account.</div>
            <div className="access-card-footer"><a className="btn btn-secondary btn-sm" href="#">Request GitHub Access</a></div>
          </div>
          <div className="access-card is-featured">
            <div className="access-card-eyebrow">Pro Modules</div>
            <div className="access-card-title">Pro</div>
            <div className="access-card-price">Optional · paid</div>
            <div className="access-card-body">Extended evidence workflows, deeper snowball analytics, additional dashboard sections. Same local-first architecture; nothing leaves your machine.</div>
            <div className="access-card-footer"><a className="btn btn-primary btn-sm" href="#">Join Early Access</a></div>
          </div>
          <div className="access-card">
            <div className="access-card-eyebrow">Setup Service</div>
            <div className="access-card-title">Setup</div>
            <div className="access-card-price">One-time</div>
            <div className="access-card-body">Guided installation, input mapping, fundamentals master scaffolding, and a first reproducible monthly run on your portfolio data.</div>
            <div className="access-card-footer"><a className="btn btn-tertiary btn-sm" href="#">Request Setup Service</a></div>
          </div>
          <div className="access-card">
            <div className="access-card-eyebrow">GitHub Sponsors</div>
            <div className="access-card-title">Sponsor</div>
            <div className="access-card-price">Any tier</div>
            <div className="access-card-body">Sponsor on GitHub or join Early Access for build updates, early Pro Module previews, and a direct line to the maintainer.</div>
            <div className="access-card-footer"><a className="btn btn-tertiary btn-sm" href="#">Sponsor on GitHub</a></div>
          </div>
        </div>
      </div>
    </section>
  );
};

window.FinalCTA = function FinalCTA() {
  return (
    <section className="section-dark" id="early-access">
      <div className="section-inner" style={{ maxWidth: 880 }}>
        <div className="t-eyebrow section-eyebrow">Start with the workflow</div>
        <h2 className="section-title" style={{ color: "var(--dark-fg)" }}>Most investing tools are built around a transaction. This one is built around a process.</h2>
        <p className="section-lede" style={{ color: "var(--dark-fg-2)" }}>If a reproducible, local, evidence-backed monthly research workflow is what you've been quietly assembling out of spreadsheets and notebooks — this is the version that already runs.</p>
        <div className="hero-actions" style={{ marginTop: "var(--space-8)" }}>
          <form className="email-capture" onSubmit={(e) => e.preventDefault()}>
            <input type="email" placeholder="you@domain.com" />
            <button className="btn btn-primary">Join Early Access</button>
          </form>
          <a className="btn btn-secondary" href="#">Request GitHub Access</a>
          <a className="btn btn-tertiary" style={{ color: "var(--dark-fg-2)" }} href="#">Request Setup Service</a>
        </div>
        <div className="hero-microcopy" style={{ color: "var(--dark-fg-3)", marginTop: "var(--space-5)" }}>Local-first. Open-source core. Not investment advice.</div>
      </div>
    </section>
  );
};

window.Footer = function Footer() {
  return (
    <footer className="footer">
      <div className="footer-inner">
        <div>
          <div style={{ marginBottom: 14 }}><img src="../../assets/wordmark-ink.svg" alt="Compound Income OS" style={{ height: 22 }} /></div>
          <p className="t-body-sm" style={{ maxWidth: 36 + "ch" }}>A local operating system for long-term investing. Local-first. Open-source core. Not investment advice.</p>
        </div>
        <div>
          <h4>Product</h4>
          <ul><li><a>Workflow</a></li><li><a>Evidence pipeline</a></li><li><a>Dashboard</a></li><li><a>Decision journal</a></li></ul>
        </div>
        <div>
          <h4>Access</h4>
          <ul><li><a>Early Access</a></li><li><a>GitHub Access</a></li><li><a>Setup Service</a></li><li><a>Sponsors</a></li></ul>
        </div>
        <div>
          <h4>Legal</h4>
          <ul><li><a>Disclaimer</a></li><li><a>Privacy</a></li><li><a>License</a></li></ul>
        </div>
      </div>
      <div className="section-inner" style={{ marginTop: "var(--space-10)" }}>
        <div className="disclaimer">
          <strong>Compound Income OS</strong> is a research and decision-support tool. It does not provide investment, tax, or legal advice, does not guarantee any return, and does not execute orders or connect to brokerages. All decisions, risks, and outcomes remain solely with the user. Past data does not predict future results.
        </div>
      </div>
      <div className="footer-bottom">
        <span>© 2026 Compound Income OS · local-first · open-source core</span>
        <span>v0.1 · prototype</span>
      </div>
    </footer>
  );
};

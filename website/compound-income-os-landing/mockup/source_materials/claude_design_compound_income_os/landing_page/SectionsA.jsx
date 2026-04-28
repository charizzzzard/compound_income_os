/* Problem, Solution, Principles, Workflow */

window.ProblemSection = function ProblemSection() {
  return (
    <section className="section" id="problem">
      <div className="section-inner">
        <div className="t-eyebrow section-eyebrow">Problem</div>
        <h2 className="section-title">Where long-term portfolios actually fail.</h2>
        <p className="section-lede">
          Most long-term portfolios don't fail in market crashes. They fail in slow motion.
          Position sizes drift past the limits you set. Theses age out without anyone noticing.
          Evidence — the screenshots, the 10-K passages, the reason you bought — scatters across folders,
          browsers, and memory. By the time conviction matters, the reasoning behind it is already gone.
        </p>
        <div style={{ marginTop: "var(--space-10)" }}>
          <div className="callout">
            <div className="callout-num">01</div>
            <div className="callout-body"><strong>Spreadsheets help — until they sprawl.</strong> A workbook started in 2019 is now seven tabs of half-remembered formulas.</div>
          </div>
          <div className="callout">
            <div className="callout-num">02</div>
            <div className="callout-body"><strong>Dashboards help — until they're cloud-locked.</strong> Your portfolio data is portable on paper. In practice, it lives behind a vendor login.</div>
          </div>
          <div className="callout">
            <div className="callout-num">03</div>
            <div className="callout-body"><strong>Screeners help — until you realize a screener can't document a decision.</strong> A ranked list is not a record of why you acted on it.</div>
          </div>
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
        <p className="section-lede">
          Compound Income OS takes the files you already have — broker positions, fundamentals data,
          your watchlist, your evidence — and runs them through a deterministic pipeline.
          The outputs are CSV and Markdown artifacts. Inputs you control. Outputs you can re-read in two years.
          Nothing uploaded, nothing executed, nothing invented.
        </p>
        <div className="grid-3" style={{ marginTop: "var(--space-10)" }}>
          <div className="feature">
            <div className="feature-mono">data/raw/</div>
            <div className="feature-title">Files in</div>
            <div className="feature-body">Broker exports, fundamentals master, evidence files, your watchlist. All local. All yours.</div>
          </div>
          <div className="feature">
            <div className="feature-mono">pipeline · deterministic</div>
            <div className="feature-title">Rules applied</div>
            <div className="feature-body">Coverage gates, business and valuation scoring, candidate ranking, dividend impact. Same inputs, same outputs.</div>
          </div>
          <div className="feature">
            <div className="feature-mono">reports/ · data/processed/</div>
            <div className="feature-title">Artifacts out</div>
            <div className="feature-body">Reproducible CSVs, Markdown decision reports, a decision journal — auditable two years from now.</div>
          </div>
        </div>
      </div>
    </section>
  );
};

window.PrinciplesSection = function PrinciplesSection() {
  const items = [
    ["01", "Local-first", "Inputs and outputs are local files. The core runs on your machine — no cloud account, no vendor handshake."],
    ["02", "Privacy-first", "Raw portfolio data is kept separate from processed artifacts. No telemetry, no upload, no analytics ping."],
    ["03", "No cloud lock-in", "The pipeline is files and code. Move it, fork it, archive it. The format you keep is yours."],
    ["04", "No broker execution", "The system documents and proposes. It never places orders, never connects to a brokerage."],
    ["05", "Evidence-only", "Missing fundamentals stay flagged — first-class status codes, never guessed values, never silently imputed."],
    ["06", "Reproducible reports", "Each run records its inputs, manifest, and artifacts. Re-runs are deterministic. Past runs stay readable."],
  ];
  return (
    <section className="section">
      <div className="section-inner">
        <div className="t-eyebrow section-eyebrow">Product principles</div>
        <h2 className="section-title">Six principles, enforced by the architecture.</h2>
        <p className="section-lede">Not marketing language. Decisions baked into the file layout, the pipeline boundaries, and the way status flows through the system.</p>
        <div className="grid-3" style={{ marginTop: "var(--space-10)" }}>
          {items.map(([n,t,b]) => (
            <div className="feature" key={t}>
              <div className="feature-mono">{n}</div>
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
    ["Broker export in",    "Drop CSV into the inputs folder. The position parser normalizes it.", "data/raw/positions.csv"],
    ["Data quality check",  "Coverage computed against your fundamentals master.",                  "fundamentals_coverage.csv"],
    ["Scoring & ranking",   "Business, valuation, and rule-based candidate scores applied.",        "company_scores.csv"],
    ["Dividend impact",     "The snowball updates against weights and rules.",                       "dividend_snowball.csv"],
    ["Monthly decision",    "Markdown report explains every candidate, blocker, and constraint.",   "monthly_decision_report.md"],
    ["Decision journal",    "Reasoning captured as an artifact, not a tab you'll close.",            "decision_journal_2026-04.md"],
  ];
  return (
    <section className="section section-tight" style={{ background: "var(--bg-muted)" }} id="workflow">
      <div className="section-inner">
        <div className="t-eyebrow section-eyebrow">Monthly workflow</div>
        <h2 className="section-title">A cadence built for long horizons.</h2>
        <p className="section-lede">Six deterministic stages. Inputs you control at the start; a re-readable Markdown record at the end.</p>
        <div className="workflow" style={{ marginTop: "var(--space-10)" }}>
          {steps.map(([t,b,a]) => (
            <div className="workflow-step" key={t}>
              <div className="workflow-title">{t}</div>
              <div className="workflow-body">{b}</div>
              <div className="workflow-art">{a}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

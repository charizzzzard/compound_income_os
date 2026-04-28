/* Features, special sections, audience, decision journal */

window.FeaturesSection = function FeaturesSection() {
  const items = [
    ["Portfolio Snapshot",         "Positions normalized from broker exports into a deterministic snapshot artifact.",   "positions_snapshot.csv"],
    ["SEC Evidence Pipeline",      "Read-only, gated workflow that proposes — never silently applies — fundamentals updates.", "sec_proposed_updates.csv"],
    ["Evidence-Applied Fundamentals", "Reviewed proposals enter the master through an explicit, traceable apply step.",  "fundamentals_master.csv"],
    ["Data Quality Gates",         "COVERED, PARTIAL, REVIEW, MISSING_DATA, INSUFFICIENT_HISTORY — first-class outputs.",  "fundamentals_coverage.csv"],
    ["Watchlist Ranking",          "Candidates ordered by transparent business, valuation, and rule-based components.",    "watchlist_ranking.csv"],
    ["Monthly Ranking",            "Cash-aware, rule-based decision queue — eligible, deferred, blocked.",                 "monthly_buy_ranking.csv"],
    ["Dividend Snowball Analysis", "Illustrative income calculation from declared rates, weights, and rules.",             "dividend_snowball.csv"],
    ["Valuation Bands",            "Per-holding valuation status, never a forecast, never a buy signal.",                  "valuation_bands.csv"],
    ["Monthly Decision Report",    "Markdown report with candidate rationale, constraints, and blockers.",                 "monthly_decision_report.md"],
    ["Decision Journal",           "Each cycle's reasoning preserved as a re-readable artifact.",                          "decision_journal_2026-04.md"],
    ["Local Dashboard",            "Five views consolidating processed artifacts. Every KPI traces back to a source file.","dashboard_kpis.csv"],
  ];
  return (
    <section className="section" id="features">
      <div className="section-inner">
        <div className="t-eyebrow section-eyebrow">Core features</div>
        <h2 className="section-title">One local pipeline. Eleven ways to inspect the evidence.</h2>
        <p className="section-lede">Every feature is a lens onto the same set of local artifacts. No mode is hidden. No view is computed in the cloud.</p>
        <div className="grid-3" style={{ marginTop: "var(--space-10)" }}>
          {items.map(([t,b,a]) => (
            <div className="feature" key={t}>
              <div className="feature-title">{t}</div>
              <div className="feature-body">{b}</div>
              <div className="feature-artifact">{a}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

window.SpecialSections = function SpecialSections() {
  return (
    <section className="section section-tight" style={{ background: "var(--bg-muted)" }}>
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
          <p className="t-body" style={{ color: "var(--fg-muted)" }}>Coverage statuses are first-class outputs. Holdings with insufficient evidence don't get force-classified — they get flagged for review and stay visible until you address them.</p>
        </div>
      </div>
    </section>
  );
};

window.JournalAndAudience = function JournalAndAudience() {
  return (
    <section className="section">
      <div className="section-inner" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-12)", alignItems: "start" }}>
        <div>
          <div className="t-eyebrow section-eyebrow">Decision journal</div>
          <h3 className="t-h3" style={{ margin: "0 0 12px" }}>The audit trail your future self will need.</h3>
          <p className="t-body" style={{ color: "var(--fg-muted)" }}>Two years from now, you can open last August's file and reconstruct exactly why a position was added, deferred, or left alone. The reasoning lives next to the run, not in a tab you'll close.</p>
          <pre className="codeblock" style={{ marginTop: 18 }}>
{`# decision_journal_2026-04.md
run_id: DEMO-20260426-160500
candidates_eligible: 2
candidates_deferred: 2
review_required: 1
notes:
  - DGB: meets dividend + valuation gates;
    candidate allocation: €300 under current rule set.
  - QCA: high candidate score; valuation gate
    not attractive enough for new capital.
  - HCF: partial coverage; defer until evidence
    review closes 2 missing required KPIs.`}
          </pre>
        </div>
        <div id="audience">
          <div className="t-eyebrow section-eyebrow">Audience</div>
          <h3 className="t-h3" style={{ margin: "0 0 12px" }}>Built for the way you already work.</h3>
          <p className="t-body" style={{ color: "var(--fg-muted)", marginBottom: "var(--space-4)" }}>Not a beginner tool. Not a robo-advisor. The system assumes you already keep a research practice — and gives it scaffolding.</p>
          <ul className="audience-list">
            <li>
              <span className="who">Dividend-growth investors</span>
              <span className="desc">Maintaining a fundamentals master and a multi-year reinvestment plan.</span>
            </li>
            <li>
              <span className="who">Quality-compounder investors</span>
              <span className="desc">Scoring on durability, returns on capital, and valuation discipline.</span>
            </li>
            <li>
              <span className="who">Engineers · analysts · finance/data</span>
              <span className="desc">Preferring reproducible files over cloud dashboards.</span>
            </li>
            <li>
              <span className="who">Independent operators</span>
              <span className="desc">Who want decisions documented, data on their machine, no broker integration in the loop.</span>
            </li>
          </ul>
        </div>
      </div>
    </section>
  );
};

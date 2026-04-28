/* Big dashboard preview block — sits between hero and the rest of the page */

window.DashboardPreview = function DashboardPreview() {
  const kpis = [
    { label: "Portfolio Value",   value: "€128,420", trend: "illustrative",      status: "ok",      pillText: "OK" },
    { label: "Cash Weight",       value: "8.4%",     trend: "Reserve OK",        status: "ok",      pillText: "OK" },
    { label: "Positions",         value: "24",       trend: "2 in review",       status: "partial", pillText: "PARTIAL" },
    { label: "Top 5 Weight",      value: "38.7%",    trend: "Within band",       status: "ok",      pillText: "OK" },
    { label: "Dividend TTM",      value: "€3,240",   trend: "+€186 r/r",         status: "partial", pillText: "PARTIAL" },
    { label: "Div. Growth 5Y",    value: "7.8%",     trend: "illustrative",      status: "partial", pillText: "PARTIAL" },
    { label: "Monthly Candidate", value: "REVIEW",   trend: "awaiting evidence", status: "review",  pillText: "REVIEW" },
    { label: "Review Flags",      value: "6",        trend: "open",              status: "review",  pillText: "REVIEW" },
  ];

  // sparkline points
  const path = "M0,52 L40,49 L80,44 L120,40 L160,36 L200,28 L240,22 L280,18";

  return (
    <div className="dash-shell" id="dashboard">
      <div className="dash-titlebar">
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <img src="design-system/assets/wordmark-paper.svg" alt="" style={{ height: 18 }} />
          <span style={{ font: "400 12px/1 var(--font-mono)", color: "var(--dark-fg-3)", letterSpacing: "0.04em" }}>
            local · monthly run
          </span>
        </div>
        <div className="dash-tabs">
          <span className="tab is-active">portfolio</span>
          <span className="tab">scores</span>
          <span className="tab">dividends</span>
          <span className="tab">decision</span>
          <span className="tab">evidence</span>
        </div>
        <div className="dash-runid">DEMO-20260426-160500 · 2026-04-26</div>
      </div>

      {/* KPI grid */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(4, 1fr)",
        gap: 12,
        marginBottom: 16,
      }}>
        {kpis.map((k) => (
          <div className="kpi on-dark" key={k.label}>
            <div className="kpi-label">{k.label}</div>
            <div className="kpi-value">{k.value}</div>
            <div className="kpi-trend">
              <span className={`pill ${k.status}`}>{k.pillText}</span>
              <span style={{ color: "var(--dark-fg-3)" }}>{k.trend}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Chart + side panel */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "2fr 1fr",
        gap: 12,
      }}>
        <div className="chart-card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 16 }}>
            <div>
              <div className="chart-eyebrow">Dividend snowball · illustrative</div>
              <div className="chart-value">€3,240 → €5,180</div>
              <div className="chart-caption">2026 → 2030 · not a forecast</div>
            </div>
            <span className="pill partial">PARTIAL</span>
          </div>
          <svg viewBox="0 0 280 64" width="100%" height="140" preserveAspectRatio="none">
            {[12,24,36,48,60].map((y,i) => (
              <line key={i} x1="0" x2="280" y1={y} y2={y} stroke="var(--dark-600)" strokeWidth="1" />
            ))}
            <path d={`${path} L280,64 L0,64 Z`} fill="rgba(127,163,204,0.08)" stroke="none" />
            <path d={path} fill="none" stroke="var(--dark-accent)" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
            {[[0,52],[40,49],[80,44],[120,40],[160,36],[200,28],[240,22],[280,18]].map(([cx,cy],i) => (
              <circle key={i} cx={cx} cy={cy} r="2" fill="var(--dark-accent)" />
            ))}
          </svg>
          <div style={{ display: "flex", justifyContent: "space-between", marginTop: 8, font: "400 10px/1 var(--font-mono)", color: "var(--dark-fg-3)", letterSpacing: "0.04em" }}>
            {["2026","2027","2028","2029","2030"].map(y => <span key={y}>{y}</span>)}
          </div>
        </div>

        <div style={{
          background: "var(--dark-700)",
          border: "1px solid var(--dark-600)",
          borderRadius: 12,
          padding: 20,
        }}>
          <div className="chart-eyebrow" style={{ marginBottom: 14 }}>Coverage status</div>
          {[
            ["COVERED", 15, "ok"],
            ["PARTIAL", 5, "partial"],
            ["REVIEW", 2, "review"],
            ["MISSING_DATA", 2, "missing"],
          ].map(([s,c,cls]) => (
            <div key={s} className="cov-row">
              <span className={`pill ${cls}`}>{s}</span>
              <span style={{ font: "500 14px/1 var(--font-mono)", color: "var(--dark-fg)" }}>{c}</span>
            </div>
          ))}
          <div style={{ marginTop: 14, font: "400 11px/1.4 var(--font-mono)", color: "var(--dark-fg-3)" }}>
            reports/demo/<br/>monthly_decision_report.md
          </div>
        </div>
      </div>

      {/* artifact strip */}
      <div style={{
        marginTop: 18, paddingTop: 14, borderTop: "1px solid var(--dark-600)",
        display: "flex", gap: 18, flexWrap: "wrap",
        font: "400 11px/1.2 var(--font-mono)", color: "var(--dark-fg-3)",
        letterSpacing: "0.03em",
      }}>
        <span>artifact · positions_snapshot.csv</span>
        <span>artifact · company_scores.csv</span>
        <span>artifact · monthly_buy_ranking.csv</span>
        <span>artifact · decision_journal_2026-04.md</span>
      </div>
    </div>
  );
};

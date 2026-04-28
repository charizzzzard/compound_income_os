/* Dashboard preview block — sits inside the hero / dashboard band.
   Uses the dark accent surface and demonstrates KPI + chart + run manifest. */

window.DashboardPreview = function DashboardPreview() {
  const kpis = [
    { label: "Portfolio Value",   value: "€128,420", trend: "illustrative",       status: "ok" },
    { label: "Cash Weight",       value: "8.4%",     trend: "Reserve OK",          status: "ok" },
    { label: "Positions",         value: "24",       trend: "2 review",            status: "partial" },
    { label: "Top 5 Weight",      value: "38.7%",    trend: "Within band",         status: "ok" },
    { label: "Dividend TTM",      value: "€3,240",   trend: "illustrative",        status: "partial" },
    { label: "Div. Growth 5Y",    value: "7.8%",     trend: "illustrative",        status: "partial" },
    { label: "Monthly Candidate", value: "REVIEW",   trend: "awaiting evidence",   status: "review" },
    { label: "Review Flags",      value: "6",        trend: "open",                status: "review" },
  ];

  // sparkline points (low-saturation reference line)
  const path = "M0,40 L40,38 L80,33 L120,30 L160,28 L200,22 L240,18 L280,16";

  return (
    <div className="dash-shell">
      <div className="dash-titlebar">
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <img src="../../assets/wordmark-paper.svg" alt="" style={{ height: 18 }} />
          <span style={{ font: "400 12px/1 var(--font-mono)", color: "var(--dark-fg-3)", letterSpacing: "0.04em" }}>
            local · monthly run
          </span>
        </div>
        <div className="dash-runid">DEMO-20260426-160500 · 2026-04-26</div>
      </div>

      {/* KPI grid */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(4, 1fr)",
        gap: 12,
        marginBottom: 24,
      }}>
        {kpis.map((k) => (
          <div className="kpi on-dark" key={k.label}>
            <div className="kpi-label">{k.label}</div>
            <div className="kpi-value">{k.value}</div>
            <div className="kpi-trend">
              <span className={`pill ${k.status}`}>{k.status === "ok" ? "OK" : k.status === "partial" ? "PARTIAL" : "REVIEW"}</span>
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
        {/* chart card */}
        <div style={{
          background: "var(--dark-700)",
          border: "1px solid var(--dark-600)",
          borderRadius: 12,
          padding: 20,
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 12 }}>
            <div>
              <div style={{ font: "500 12px/1 var(--font-sans)", letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--dark-fg-3)" }}>
                Dividend snowball · illustrative
              </div>
              <div style={{ font: "500 22px/1.1 var(--font-mono)", color: "var(--dark-fg)", letterSpacing: "-0.01em", marginTop: 6 }}>€3,240 → €5,180</div>
              <div style={{ font: "400 12px/1.4 var(--font-mono)", color: "var(--dark-fg-3)", marginTop: 4 }}>2026 → 2030 · not a forecast</div>
            </div>
            <span className="pill partial">PARTIAL</span>
          </div>
          <svg viewBox="0 0 280 64" width="100%" height="120" preserveAspectRatio="none">
            {[10,20,30,40,50].map((y,i) => (
              <line key={i} x1="0" x2="280" y1={y} y2={y} stroke="var(--dark-600)" strokeWidth="1" />
            ))}
            <path d={path} fill="none" stroke="var(--dark-accent)" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
            {[
              [0,40],[40,38],[80,33],[120,30],[160,28],[200,22],[240,18],[280,16]
            ].map(([cx,cy],i) => (
              <circle key={i} cx={cx} cy={cy} r="2" fill="var(--dark-accent)" />
            ))}
          </svg>
        </div>

        {/* coverage panel */}
        <div style={{
          background: "var(--dark-700)",
          border: "1px solid var(--dark-600)",
          borderRadius: 12,
          padding: 20,
        }}>
          <div style={{ font: "500 12px/1 var(--font-sans)", letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--dark-fg-3)", marginBottom: 14 }}>
            Coverage status
          </div>
          {[
            ["COVERED", 18, "ok"],
            ["PARTIAL", 4, "partial"],
            ["REVIEW", 1, "review"],
            ["MISSING_DATA", 1, "missing"],
          ].map(([s,c,cls]) => (
            <div key={s} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", borderBottom: "1px solid var(--dark-600)" }}>
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
      }}>
        <span>artifact · positions_snapshot.csv</span>
        <span>artifact · company_scores.csv</span>
        <span>artifact · monthly_buy_ranking.csv</span>
        <span>artifact · decision_journal_2026-04.md</span>
      </div>
    </div>
  );
};

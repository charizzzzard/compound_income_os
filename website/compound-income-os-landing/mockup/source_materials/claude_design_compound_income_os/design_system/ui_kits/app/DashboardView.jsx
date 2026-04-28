/* Dashboard view — five panels: KPI, holdings, coverage, snowball, journal latest. */

const HOLDINGS = [
  { tk: "DGB",  name: "Dividend Growth Bank",  w: 6.2, val: 8120,  yld: 3.4, score: 78, status: "ok" },
  { tk: "QCA",  name: "Quality Compounder A",  w: 8.1, val: 10610, yld: 1.6, score: 84, status: "ok" },
  { tk: "INF",  name: "Infrastructure Co.",    w: 5.4, val: 7080,  yld: 4.2, score: 71, status: "partial" },
  { tk: "PCG",  name: "Pacific Consumer Group",w: 4.8, val: 6290,  yld: 2.8, score: 69, status: "ok" },
  { tk: "MED",  name: "Medical Devices Ltd",   w: 7.0, val: 9170,  yld: 1.1, score: 81, status: "review" },
  { tk: "ENG",  name: "Energy Royalty Trust",  w: 3.9, val: 5110,  yld: 5.4, score: 64, status: "partial" },
  { tk: "SOF",  name: "Software Platform Inc.",w: 9.4, val: 12320, yld: 0.8, score: 86, status: "ok" },
  { tk: "RTL",  name: "Retail Operator Co.",   w: 2.1, val: 2750,  yld: 3.1, score: 58, status: "missing_data" },
];

window.DashboardView = function DashboardView({ onOpenHolding }) {
  const kpis = [
    { label: "Portfolio Value",   value: "€128,420", trend: "illustrative",     status: "ok" },
    { label: "Cash Weight",       value: "8.4%",     trend: "Reserve OK",       status: "ok" },
    { label: "Positions",         value: "24",       trend: "2 review",         status: "partial" },
    { label: "Top 5 Weight",      value: "38.7%",    trend: "Within band",      status: "ok" },
    { label: "Dividend TTM",      value: "€3,240",   trend: "illustrative",     status: "partial" },
    { label: "Div. Growth 5Y",    value: "7.8%",     trend: "illustrative",     status: "partial" },
    { label: "Monthly Candidate", value: "REVIEW",   trend: "awaiting evidence", status: "review" },
    { label: "Review Flags",      value: "6",        trend: "open",              status: "review" },
  ];

  // snowball sparkline
  const snow = "M0,72 L40,68 L80,60 L120,53 L160,46 L200,38 L240,30 L280,22";

  return (
    <>
      <div className="canvas-header">
        <div className="canvas-eyebrow">Local · Run DEMO-20260426-160500</div>
        <h1 className="canvas-title">Dashboard</h1>
        <p className="canvas-sub">Consolidated view across the latest reproducible run. Every KPI traces back to a source artifact in <span className="kbd">/reports/demo/</span>.</p>
      </div>

      <div className="kpi-grid">
        {kpis.map((k) => (
          <div className="kpi" key={k.label}>
            <div className="kpi-label">{k.label}</div>
            <div className="kpi-value">{k.value}</div>
            <div className="kpi-trend">
              <span className={`pill ${k.status}`}>{k.status === "ok" ? "OK" : k.status === "partial" ? "PARTIAL" : "REVIEW"}</span>
              <span style={{ color: "var(--fg-muted)" }}>{k.trend}</span>
            </div>
          </div>
        ))}
      </div>

      {/* holdings + side panel */}
      <div className="split-2" style={{ marginBottom: 16 }}>
        <div className="card" style={{ padding: 0 }}>
          <div className="card-h" style={{ padding: "16px 20px 12px", marginBottom: 0 }}>
            <div className="card-title">Holdings · top 8 by weight</div>
            <div className="card-sub">positions_snapshot.csv</div>
          </div>
          <table className="tbl">
            <thead>
              <tr>
                <th>Ticker</th><th>Name</th>
                <th className="num">Weight</th><th className="num">Value</th>
                <th className="num">Yield</th><th className="num">Score</th>
                <th>Status</th><th />
              </tr>
            </thead>
            <tbody>
              {HOLDINGS.map((h) => (
                <tr key={h.tk}>
                  <td style={{ fontFamily: "var(--font-mono)", fontWeight: 500 }}>{h.tk}</td>
                  <td style={{ color: "var(--ink-700)" }}>{h.name}</td>
                  <td className="num">{h.w.toFixed(1)}%</td>
                  <td className="num">€{h.val.toLocaleString()}</td>
                  <td className="num">{h.yld.toFixed(1)}%</td>
                  <td className="num">{h.score}</td>
                  <td><span className={`pill ${h.status === "missing_data" ? "missing" : h.status}`}>{({ok:"COVERED",partial:"PARTIAL",review:"REVIEW",missing_data:"MISSING_DATA"}[h.status]) || h.status.toUpperCase()}</span></td>
                  <td><span className="row-action" onClick={() => onOpenHolding(h)}>Inspect ›</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="card">
          <div className="card-h">
            <div className="card-title">Dividend snowball</div>
            <div className="card-sub">Illustrative</div>
          </div>
          <div style={{ font: "500 28px/1.1 var(--font-mono)", color: "var(--fg-strong)", letterSpacing: "-0.01em" }}>€3,240 → €5,180</div>
          <div style={{ font: "400 12px/1.4 var(--font-mono)", color: "var(--ink-500)", marginTop: 4 }}>2026 → 2030 · not a forecast</div>
          <svg viewBox="0 0 280 88" width="100%" height="120" preserveAspectRatio="none" style={{ marginTop: 14 }}>
            {[18,36,54,72].map((y,i) => <line key={i} x1="0" x2="280" y1={y} y2={y} stroke="var(--paper-200)" />)}
            <path d={snow} fill="none" stroke="var(--accent-600)" strokeWidth="1.6" />
            {[[0,72],[40,68],[80,60],[120,53],[160,46],[200,38],[240,30],[280,22]].map(([x,y],i) => (
              <circle key={i} cx={x} cy={y} r="2" fill="var(--accent-600)" />
            ))}
          </svg>
          <div style={{ display: "flex", justifyContent: "space-between", marginTop: 8, font: "400 11px/1 var(--font-mono)", color: "var(--ink-500)" }}>
            <span>2026</span><span>2027</span><span>2028</span><span>2029</span><span>2030</span>
          </div>
        </div>
      </div>

      {/* coverage + journal */}
      <div className="split-1-1">
        <div className="card">
          <div className="card-h">
            <div className="card-title">Data quality coverage</div>
            <div className="card-sub">24 holdings</div>
          </div>
          <div className="cov">
            <span style={{ width: "75%", background: "var(--ok-fg)" }} />
            <span style={{ width: "12%", background: "var(--partial-fg)" }} />
            <span style={{ width: "8%",  background: "var(--review-fg)" }} />
            <span style={{ width: "5%",  background: "var(--missing-fg)" }} />
          </div>
          <div className="cov-legend">
            <span className="item"><span className="dot" style={{ background: "var(--ok-fg)" }} />Covered · 18</span>
            <span className="item"><span className="dot" style={{ background: "var(--partial-fg)" }} />Partial · 4</span>
            <span className="item"><span className="dot" style={{ background: "var(--review-fg)" }} />Review · 1</span>
            <span className="item"><span className="dot" style={{ background: "var(--missing-fg)" }} />Missing data · 1</span>
          </div>
          <div style={{ marginTop: 18, padding: "12px 0 0", borderTop: "1px solid var(--border-subtle)", font: "400 12px/1.5 var(--font-mono)", color: "var(--ink-600)" }}>
            Insufficient-history holdings remain visible until evidence is supplied. The pipeline does not force-classify them.
          </div>
        </div>

        <div className="card">
          <div className="card-h">
            <div className="card-title">Latest journal entry</div>
            <div className="card-sub">2026-04</div>
          </div>
          <pre style={{
            margin: 0, font: "400 12px/1.6 var(--font-mono)", color: "var(--ink-700)",
            whiteSpace: "pre-wrap"
          }}>{`run_id: DEMO-20260426-160500
candidates_eligible:  2
candidates_deferred:  2
review_required:      1

notes:
  - DGB · meets dividend + valuation gates;
    candidate allocation: €300 under current
    rule set; within concentration limit.
  - QCA · high candidate score; valuation gate
    not attractive enough for new capital.
  - MED · review; coverage gap on 5y history.`}</pre>
          <div style={{ marginTop: 14, display: "flex", gap: 10 }}>
            <a className="btn btn-secondary btn-sm" href="#">Open journal</a>
            <a className="btn btn-tertiary btn-sm" href="#">Export report.md</a>
          </div>
        </div>
      </div>
    </>
  );
};

window.HoldingDrawer = function HoldingDrawer({ holding, onClose }) {
  if (!holding) return null;
  return (
    <>
      <div className="scrim" onClick={onClose} />
      <div className={"drawer is-open"}>
        <div className="drawer-h">
          <div>
            <div style={{ font: "500 11px/1 var(--font-sans)", letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--accent-600)", marginBottom: 6 }}>Holding inspector</div>
            <div style={{ font: "500 22px/1.1 var(--font-sans)", color: "var(--fg-strong)" }}>{holding.tk} · {holding.name}</div>
            <div style={{ font: "400 12px/1 var(--font-mono)", color: "var(--ink-500)", marginTop: 6 }}>company_scores.csv · row 12</div>
          </div>
          <span className="drawer-close" onClick={onClose}>Close ✕</span>
        </div>
        <div className="drawer-body">
          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 10, marginBottom: 18 }}>
            <div className="kpi"><div className="kpi-label">Weight</div><div className="kpi-value">{holding.w.toFixed(1)}%</div></div>
            <div className="kpi"><div className="kpi-label">Value</div><div className="kpi-value">€{holding.val.toLocaleString()}</div></div>
            <div className="kpi"><div className="kpi-label">Yield</div><div className="kpi-value">{holding.yld.toFixed(1)}%</div></div>
            <div className="kpi"><div className="kpi-label">Score</div><div className="kpi-value">{holding.score}</div></div>
          </div>
          <div className="card-title" style={{ marginBottom: 8 }}>Score components</div>
          {[
            ["Business quality", 82],
            ["Dividend durability", 74],
            ["Valuation", 61],
            ["Capital allocation", 78],
          ].map(([l, v]) => (
            <div key={l} style={{ display: "grid", gridTemplateColumns: "140px 1fr 40px", alignItems: "center", gap: 10, padding: "8px 0", borderBottom: "1px solid var(--border-subtle)" }}>
              <span style={{ font: "400 13px/1 var(--font-sans)", color: "var(--ink-700)" }}>{l}</span>
              <span style={{ background: "var(--paper-200)", height: 6, borderRadius: 3, position: "relative" }}>
                <span style={{ position: "absolute", inset: 0, width: `${v}%`, background: "var(--accent-600)", borderRadius: 3 }} />
              </span>
              <span style={{ textAlign: "right", font: "500 13px/1 var(--font-mono)", color: "var(--fg-strong)" }}>{v}</span>
            </div>
          ))}
          <div style={{ marginTop: 22, padding: 14, border: "1px solid var(--border-default)", borderRadius: 8, background: "var(--paper-50)" }}>
            <div className="card-title" style={{ marginBottom: 6 }}>Provenance</div>
            <div style={{ font: "400 12px/1.6 var(--font-mono)", color: "var(--ink-600)" }}>
              fundamentals_master.csv (2026-04-22)<br/>
              evidence/sec/{holding.tk.toLowerCase()}_companyfacts_2026Q1.json<br/>
              evidence_applied/{holding.tk.toLowerCase()}.md
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

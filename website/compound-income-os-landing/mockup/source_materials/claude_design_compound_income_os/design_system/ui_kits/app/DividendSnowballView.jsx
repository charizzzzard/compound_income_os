/* Dividend Snowball Analysis — high-fidelity feature view.
   Strict illustrative-only framing. No forecast language.
   Reads tokens from ../../colors_and_type.css + ./app.css. */

window.DividendSnowballView = function DividendSnowballView() {
  // 5-year illustrative path. Two scenarios reuse the same axis.
  // Values are in € and labeled illustrative everywhere they appear.
  const years = ["2026", "2027", "2028", "2029", "2030"];
  const reinv = [3240, 3590, 3970, 4520, 5180]; // reinvested-dividends scenario
  const manual = [3240, 3460, 3700, 3950, 4220]; // manual-cash scenario (no reinvestment)
  const candidate = [550, 600, 660, 720, 790];   // candidate contribution layer

  // chart geometry
  const W = 640, H = 220, PAD_L = 56, PAD_R = 16, PAD_T = 14, PAD_B = 32;
  const max = 5400, min = 3000;
  const x = (i) => PAD_L + (i / (years.length - 1)) * (W - PAD_L - PAD_R);
  const y = (v) => PAD_T + (1 - (v - min) / (max - min)) * (H - PAD_T - PAD_B);
  const line = (arr) => arr.map((v, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const area = (arr) => `${line(arr)} L${x(arr.length - 1)},${H - PAD_B} L${x(0)},${H - PAD_B} Z`;
  const ticks = [3000, 3600, 4200, 4800, 5400];

  // candidate breakdown bars (illustrative contribution to next-12mo income)
  const cand = [
    { tk: "DGB", name: "Dividend Growth Bank",  add: 300, dps: 1.92, contrib: 18 },
    { tk: "INF", name: "Infrastructure Co.",    add: 250, dps: 1.34, contrib: 14 },
    { tk: "PCG", name: "Pacific Consumer Group", add: 0,  dps: 0.86, contrib: 0  },
  ];

  return (
    <>
      <div className="canvas-header">
        <div className="canvas-eyebrow">Research · Illustrative</div>
        <h1 className="canvas-title">Dividend Snowball Analysis</h1>
        <p className="canvas-sub">
          A reproducible, rule-based projection of declared income across holdings, candidate allocations, and your reinvestment policy. <strong style={{ color: "var(--fg-strong)" }}>Illustrative calculation. Not a forecast.</strong> No return promise. No alpha claim.
        </p>
      </div>

      {/* KPI summary band */}
      <div className="kpi-grid" style={{ gridTemplateColumns: "repeat(4, 1fr)" }}>
        <div className="kpi">
          <div className="kpi-label">Dividend income TTM</div>
          <div className="kpi-value">€3,240</div>
          <div className="kpi-trend">
            <span className="pill partial">PARTIAL</span>
            <span style={{ color: "var(--fg-muted)" }}>illustrative</span>
          </div>
        </div>
        <div className="kpi">
          <div className="kpi-label">Illustrative income · year 5</div>
          <div className="kpi-value">€5,180</div>
          <div className="kpi-trend">
            <span className="pill ok">REINVEST</span>
            <span style={{ color: "var(--fg-muted)" }}>not a forecast</span>
          </div>
        </div>
        <div className="kpi">
          <div className="kpi-label">Candidate contribution · y1</div>
          <div className="kpi-value">€32</div>
          <div className="kpi-trend">
            <span className="pill partial">RULE-BASED</span>
            <span style={{ color: "var(--fg-muted)" }}>under current rules</span>
          </div>
        </div>
        <div className="kpi">
          <div className="kpi-label">Coverage</div>
          <div className="kpi-value">21 / 24</div>
          <div className="kpi-trend">
            <span className="pill review">REVIEW</span>
            <span style={{ color: "var(--fg-muted)" }}>3 holdings</span>
          </div>
        </div>
      </div>

      {/* Chart card */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-h">
          <div>
            <div className="card-title">Illustrative income path · 5y</div>
            <div className="card-sub" style={{ marginTop: 4 }}>Two scenarios from current holdings + candidate set. Not a forecast.</div>
          </div>
          <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
            <span style={{ display: "flex", alignItems: "center", gap: 6, font: "400 12px/1 var(--font-mono)", color: "var(--ink-600)" }}>
              <span style={{ width: 12, height: 2, background: "var(--accent-600)" }} />Reinvest declared dividends
            </span>
            <span style={{ display: "flex", alignItems: "center", gap: 6, font: "400 12px/1 var(--font-mono)", color: "var(--ink-600)" }}>
              <span style={{ width: 12, height: 2, background: "var(--gold-500)", borderTop: "1px dashed var(--gold-500)" }} />Manual cash, no reinvest
            </span>
          </div>
        </div>

        <svg viewBox={`0 0 ${W} ${H}`} width="100%" height="240" preserveAspectRatio="none" style={{ display: "block" }}>
          {/* gridlines + y-axis labels */}
          {ticks.map((t) => (
            <g key={t}>
              <line x1={PAD_L} x2={W - PAD_R} y1={y(t)} y2={y(t)} stroke="var(--paper-200)" />
              <text x={PAD_L - 8} y={y(t) + 3} textAnchor="end" style={{ font: "400 10px/1 var(--font-mono)", fill: "var(--ink-500)" }}>€{t.toLocaleString()}</text>
            </g>
          ))}

          {/* x ticks */}
          {years.map((yr, i) => (
            <text key={yr} x={x(i)} y={H - 10} textAnchor="middle" style={{ font: "400 11px/1 var(--font-mono)", fill: "var(--ink-500)" }}>{yr}</text>
          ))}

          {/* reinvest area */}
          <path d={area(reinv)} fill="var(--accent-100)" opacity="0.55" />
          {/* manual line */}
          <path d={line(manual)} fill="none" stroke="var(--gold-500)" strokeWidth="1.6" strokeDasharray="4 3" />
          {/* reinvest line */}
          <path d={line(reinv)} fill="none" stroke="var(--accent-600)" strokeWidth="1.8" />

          {/* points */}
          {reinv.map((v, i) => (
            <g key={i}>
              <circle cx={x(i)} cy={y(v)} r="3" fill="var(--accent-600)" />
              <text x={x(i)} y={y(v) - 8} textAnchor="middle" style={{ font: "500 10px/1 var(--font-mono)", fill: "var(--ink-700)" }}>€{v.toLocaleString()}</text>
            </g>
          ))}
          {manual.map((v, i) => (
            <circle key={i} cx={x(i)} cy={y(v)} r="2.4" fill="var(--gold-500)" />
          ))}
        </svg>

        <div style={{
          marginTop: 12, padding: "10px 12px", border: "1px solid var(--border-default)",
          borderRadius: 8, background: "var(--paper-50)",
          font: "400 12px/1.5 var(--font-mono)", color: "var(--ink-600)",
        }}>
          Calculation: declared dividend rates × current weights, applied across reinvestment policy and rule-based candidate additions. Inputs and outputs are local files. <strong style={{ color: "var(--fg-strong)" }}>Illustrative calculation. Not a forecast.</strong>
        </div>
      </div>

      {/* Two-up: assumptions + caps */}
      <div className="split-1-1" style={{ marginBottom: 16 }}>
        <div className="card">
          <div className="card-h"><div className="card-title">Assumptions</div><div className="card-sub">snowball.assumptions.yml</div></div>
          <div style={{ display: "grid", gap: 10 }}>
            {[
              ["Reinvestment policy",       "Declared dividends → cash sleeve, deployed monthly under rule set"],
              ["Cash deployment",           "€600 / month illustrative cap; deployed only against ELIGIBLE candidates"],
              ["Manual scenario",           "No reinvestment; declared dividends accrue as cash; no candidate adds"],
              ["Dividend growth input",     "Declared / static — no growth modeling assumed"],
              ["Currency",                  "EUR; FX held constant (illustrative)"],
              ["Tax / withholding",         "Excluded from this calculation"],
            ].map(([k, v]) => (
              <div key={k} style={{ display: "grid", gridTemplateColumns: "180px 1fr", gap: 12, padding: "6px 0", borderBottom: "1px solid var(--border-subtle)" }}>
                <span style={{ font: "500 12px/1.4 var(--font-sans)", color: "var(--ink-700)" }}>{k}</span>
                <span style={{ font: "400 12px/1.4 var(--font-mono)", color: "var(--ink-600)" }}>{v}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <div className="card-h"><div className="card-title">Rule-based concentration caps</div><div className="card-sub">rules.yml</div></div>
          <div style={{ display: "grid", gap: 10 }}>
            {[
              ["Single position cap",     "8.0%", "current top: SOF 9.4% — flagged"],
              ["Top-5 weight cap",        "45%",  "current: 38.7% — within band"],
              ["Sector weight cap",       "30%",  "current top sector: 21%"],
              ["Monthly deployment cap",  "€600", "candidate set: €550 under cap"],
              ["Per-candidate cap",       "€400", "all candidates within cap"],
            ].map(([k, lim, note]) => (
              <div key={k} style={{ display: "grid", gridTemplateColumns: "1fr 80px 1fr", gap: 12, alignItems: "center", padding: "6px 0", borderBottom: "1px solid var(--border-subtle)" }}>
                <span style={{ font: "400 13px/1.3 var(--font-sans)", color: "var(--ink-700)" }}>{k}</span>
                <span style={{ font: "500 13px/1 var(--font-mono)", color: "var(--fg-strong)", textAlign: "right" }}>{lim}</span>
                <span style={{ font: "400 12px/1.4 var(--font-mono)", color: "var(--ink-500)" }}>{note}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Candidate contribution table */}
      <div className="card" style={{ padding: 0, marginBottom: 16 }}>
        <div className="card-h" style={{ padding: "16px 20px 12px", marginBottom: 0 }}>
          <div className="card-title">Candidate contribution to next-12mo income · illustrative</div>
          <div className="card-sub">Rule-based candidate set</div>
        </div>
        <table className="tbl">
          <thead>
            <tr>
              <th>Ticker</th><th>Name</th>
              <th className="num">Allocation</th>
              <th className="num">Declared DPS</th>
              <th className="num">Δ income · y1</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {cand.map((c) => (
              <tr key={c.tk}>
                <td style={{ fontFamily: "var(--font-mono)", fontWeight: 500 }}>{c.tk}</td>
                <td style={{ color: "var(--ink-700)" }}>{c.name}</td>
                <td className="num">{c.add ? `€${c.add}` : "—"}</td>
                <td className="num">€{c.dps.toFixed(2)}</td>
                <td className="num">{c.contrib ? `€${c.contrib}` : "—"}</td>
                <td>
                  <span className={`pill ${c.add ? "ok" : "neutral"}`}>
                    {c.add ? "ELIGIBLE" : "DEFERRED"}
                  </span>
                </td>
              </tr>
            ))}
            <tr style={{ background: "var(--paper-100)" }}>
              <td colSpan="2" style={{ fontWeight: 500 }}>Total candidate contribution · y1</td>
              <td className="num" style={{ fontWeight: 500 }}>€550</td>
              <td className="num" />
              <td className="num" style={{ fontWeight: 500 }}>€32</td>
              <td><span className="pill partial">RULE-BASED</span></td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Data quality + provenance */}
      <div className="split-1-1" style={{ marginBottom: 16 }}>
        <div className="card">
          <div className="card-h"><div className="card-title">Data quality status</div><div className="card-sub">snowball coverage</div></div>
          <div className="cov">
            <span style={{ width: "75%", background: "var(--ok-fg)" }} />
            <span style={{ width: "12%", background: "var(--partial-fg)" }} />
            <span style={{ width: "8%",  background: "var(--review-fg)" }} />
            <span style={{ width: "5%",  background: "var(--missing-fg)" }} />
          </div>
          <div className="cov-legend">
            <span className="item"><span className="dot" style={{ background: "var(--ok-fg)" }} />COVERED · 18</span>
            <span className="item"><span className="dot" style={{ background: "var(--partial-fg)" }} />PARTIAL · 4</span>
            <span className="item"><span className="dot" style={{ background: "var(--review-fg)" }} />REVIEW · 1</span>
            <span className="item"><span className="dot" style={{ background: "var(--missing-fg)" }} />MISSING_DATA · 1</span>
          </div>
          <div style={{ marginTop: 14, font: "400 12px/1.5 var(--font-mono)", color: "var(--ink-600)" }}>
            Holdings flagged <span className="kbd">INSUFFICIENT_HISTORY</span> or <span className="kbd">NO_MATCH</span> are excluded from the income path. They remain visible until evidence is supplied.
          </div>
        </div>

        <div className="card">
          <div className="card-h"><div className="card-title">Source artifacts</div><div className="card-sub">provenance</div></div>
          <div style={{ display: "grid", gap: 8, font: "400 12px/1.5 var(--font-mono)", color: "var(--ink-700)" }}>
            <div>inputs/broker_export_2026-04-22.csv</div>
            <div>data/fundamentals_master.csv <span style={{ color: "var(--ink-500)" }}>(rev 4f8c)</span></div>
            <div>config/rules.yml <span style={{ color: "var(--ink-500)" }}>(rev 91a3)</span></div>
            <div>config/snowball.assumptions.yml <span style={{ color: "var(--ink-500)" }}>(rev 22de)</span></div>
            <div>reports/demo/dividend_snowball_2026-04.csv</div>
            <div>reports/demo/monthly_buy_ranking.csv</div>
            <div style={{ marginTop: 8, paddingTop: 8, borderTop: "1px solid var(--border-subtle)", color: "var(--ink-500)" }}>
              run_id: DEMO-20260426-160500
            </div>
          </div>
        </div>
      </div>

      {/* Footer disclaimer band */}
      <div style={{
        marginTop: 8, padding: "14px 18px",
        background: "var(--paper-100)", border: "1px solid var(--border-default)", borderRadius: 10,
        font: "400 12.5px/1.55 var(--font-sans)", color: "var(--ink-700)",
      }}>
        <strong style={{ color: "var(--fg-strong)" }}>Illustrative calculation. Not a forecast.</strong>{" "}
        The dividend snowball is a rule-based projection from declared dividend rates, current weights, and the candidate set under your rules.
        It is not a return promise, does not predict future income, and does not constitute investment advice. Local-first. No broker execution. Open-source core.
      </div>
    </>
  );
};

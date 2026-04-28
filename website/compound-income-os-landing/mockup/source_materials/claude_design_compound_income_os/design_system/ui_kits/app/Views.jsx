/* Monthly Run + Journal + Evidence views. */

window.MonthlyRunView = function MonthlyRunView() {
  const queue = [
    { tk: "DGB", name: "Dividend Growth Bank", action: "ELIGIBLE", amount: "€300",  note: "Candidate allocation under current rule set; within concentration limit." },
    { tk: "INF", name: "Infrastructure Co.",   action: "ELIGIBLE", amount: "€250",  note: "Yield gate met; dividend durability acceptable." },
    { tk: "QCA", name: "Quality Compounder A", action: "DEFERRED", amount: "—",     note: "Valuation gate: not attractive enough for new capital under current rules." },
    { tk: "SOF", name: "Software Platform Inc.", action: "DEFERRED", amount: "—",   note: "Concentration: top-5 weight cap reached." },
    { tk: "MED", name: "Medical Devices Ltd",  action: "BLOCKED",  amount: "—",     note: "Coverage gap on 5y history; INSUFFICIENT_HISTORY." },
  ];

  const colorFor = (a) =>
    a === "ELIGIBLE" ? "ok" : a === "DEFERRED" ? "neutral" : "review";

  return (
    <>
      <div className="canvas-header">
        <div className="canvas-eyebrow">Workflow · April 2026</div>
        <h1 className="canvas-title">Monthly Run</h1>
        <p className="canvas-sub">Cash-aware decision queue assembled from the watchlist ranking and the snapshot. Eligible, deferred, blocked — never auto-executed.</p>
      </div>

      <div className="review-banner">
        <strong>1 holding requires review.</strong> Coverage gap on MED prevents inclusion in this cycle. Resolve via the SEC Evidence pipeline or stage manual evidence before the next run.
      </div>

      <div className="toolbar">
        <div className="seg">
          <span className="seg-opt is-active">All</span>
          <span className="seg-opt">Eligible</span>
          <span className="seg-opt">Deferred</span>
          <span className="seg-opt">Blocked</span>
        </div>
        <div style={{ flex: 1 }} />
        <span className="topbar-runid">cash €10,800 · monthly cap €600.00</span>
        <button className="btn btn-secondary btn-sm">Re-run pipeline</button>
        <button className="btn btn-primary btn-sm">Export decision report</button>
      </div>

      <div className="card" style={{ padding: 0 }}>
        <table className="tbl">
          <thead>
            <tr>
              <th>Ticker</th><th>Name</th>
              <th>Action</th><th className="num">Amount</th><th>Rationale</th><th />
            </tr>
          </thead>
          <tbody>
            {queue.map((r) => (
              <tr key={r.tk}>
                <td style={{ fontFamily: "var(--font-mono)", fontWeight: 500 }}>{r.tk}</td>
                <td style={{ color: "var(--ink-700)" }}>{r.name}</td>
                <td><span className={`pill ${colorFor(r.action)}`}>{r.action}</span></td>
                <td className="num">{r.amount}</td>
                <td style={{ color: "var(--ink-600)", maxWidth: 420 }}>{r.note}</td>
                <td><span className="row-action">Open ›</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="split-1-1" style={{ marginTop: 16 }}>
        <div className="card">
          <div className="card-h"><div className="card-title">Run manifest</div><div className="card-sub">runs/2026-04/manifest.json</div></div>
          <pre style={{ margin: 0, font: "400 12px/1.6 var(--font-mono)", color: "var(--ink-700)" }}>{`run_id: DEMO-20260426-160500
inputs:
  positions:    inputs/broker_export_2026-04-22.csv
  fundamentals: data/fundamentals_master.csv (rev 4f8c)
  watchlist:    inputs/watchlist.csv
  rules:        config/rules.yml (rev 91a3)
artifacts:
  - reports/demo/positions_snapshot.csv
  - reports/demo/company_scores.csv
  - reports/demo/monthly_buy_ranking.csv
  - reports/demo/monthly_decision_report.md
  - reports/demo/decision_journal_2026-04.md
exit_status: ok`}</pre>
        </div>

        <div className="card">
          <div className="card-h"><div className="card-title">Rule trace · DGB</div><div className="card-sub">rules.yml</div></div>
          <div style={{ display: "grid", gap: 8 }}>
            {[
              ["dividend_yield ≥ 2.5%", "3.4%", true],
              ["dividend_growth_5y ≥ 4%", "6.1%", true],
              ["valuation_band ≠ stretched", "fair", true],
              ["weight_after ≤ position_cap", "6.5%", true],
              ["sector_weight ≤ sector_cap", "21%", true],
              ["coverage = COVERED", "covered", true],
            ].map(([rule, val, ok]) => (
              <div key={rule} style={{ display: "grid", gridTemplateColumns: "1fr auto 60px", alignItems: "center", gap: 12, padding: "6px 0", borderBottom: "1px solid var(--border-subtle)" }}>
                <span style={{ font: "400 13px/1.3 var(--font-mono)", color: "var(--ink-700)" }}>{rule}</span>
                <span style={{ font: "500 13px/1 var(--font-mono)", color: "var(--fg-strong)" }}>{val}</span>
                <span className={`pill ${ok ? "ok" : "review"}`} style={{ justifySelf: "end" }}>{ok ? "PASS" : "FAIL"}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
};

window.JournalView = function JournalView() {
  const entries = [
    { date: "2026-04", id: "DEMO-20260426-160500", eligible: 2, deferred: 2, review: 1 },
    { date: "2026-03", id: "DEMO-20260322-091200", eligible: 3, deferred: 1, review: 0 },
    { date: "2026-02", id: "DEMO-20260218-102200", eligible: 1, deferred: 4, review: 1 },
    { date: "2026-01", id: "DEMO-20260119-094500", eligible: 0, deferred: 5, review: 2 },
    { date: "2025-12", id: "DEMO-20251215-110900", eligible: 2, deferred: 3, review: 0 },
  ];
  return (
    <>
      <div className="canvas-header">
        <div className="canvas-eyebrow">Records</div>
        <h1 className="canvas-title">Decision Journal</h1>
        <p className="canvas-sub">A re-readable record of each monthly cycle's reasoning. Two years from now, you can open last August's file and reconstruct exactly why a position was added, deferred, or left alone.</p>
      </div>

      <div className="split-2">
        <div className="card" style={{ padding: 0 }}>
          <table className="tbl">
            <thead><tr><th>Cycle</th><th>Run ID</th><th className="num">Eligible</th><th className="num">Deferred</th><th className="num">Review</th><th /></tr></thead>
            <tbody>
              {entries.map((e, i) => (
                <tr key={e.id} style={i === 0 ? { background: "var(--paper-100)" } : {}}>
                  <td style={{ fontFamily: "var(--font-mono)", fontWeight: 500 }}>{e.date}</td>
                  <td style={{ color: "var(--ink-600)", fontFamily: "var(--font-mono)", fontSize: 12 }}>{e.id}</td>
                  <td className="num">{e.eligible}</td>
                  <td className="num">{e.deferred}</td>
                  <td className="num">{e.review}</td>
                  <td><span className="row-action">Open ›</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="card">
          <div className="card-h"><div className="card-title">decision_journal_2026-04.md</div><div className="card-sub">latest</div></div>
          <pre style={{ margin: 0, font: "400 12px/1.6 var(--font-mono)", color: "var(--ink-700)", whiteSpace: "pre-wrap" }}>{`# Cycle 2026-04 · illustrative
run_id: DEMO-20260426-160500
cash_available:   €10,800 (illustrative)
monthly_cap:      €600

## Eligible candidates
- DGB · candidate allocation: €300
  reason: dividend + valuation gates met;
  within concentration limit.
- INF · candidate allocation: €250
  reason: yield gate met; durability ok.

## Deferred
- QCA · valuation not attractive enough
  under current rule set.
- SOF · top-5 weight cap reached.

## Review
- MED · INSUFFICIENT_HISTORY on 5y series.

## Notes
This cycle leaves €50 of monthly cap
unallocated by design. Not a forecast.`}</pre>
        </div>
      </div>
    </>
  );
};

window.EvidenceView = function EvidenceView() {
  const proposals = [
    { tk: "DGB", field: "dps_ttm",       was: "1.84", now: "1.92", source: "DEF 14A 2026-Q1", status: "PROPOSED" },
    { tk: "DGB", field: "payout_ratio",  was: "48%",  now: "46%",  source: "10-Q 2026-Q1",     status: "PROPOSED" },
    { tk: "QCA", field: "fcf_ttm",       was: "412",  now: "438",  source: "10-Q 2026-Q1",     status: "PROPOSED" },
    { tk: "INF", field: "dividend_growth_5y", was: "5.4%", now: "5.9%", source: "DEF 14A archive", status: "REVIEW" },
    { tk: "MED", field: "rev_ttm",       was: "—",    now: "2,140", source: "10-K 2025",        status: "REVIEW" },
  ];
  return (
    <>
      <div className="canvas-header">
        <div className="canvas-eyebrow">Evidence pipeline</div>
        <h1 className="canvas-title">SEC Evidence — proposed updates</h1>
        <p className="canvas-sub">Read-only refresh from SEC CompanyFacts. Nothing is silently applied. Reviewed proposals enter the evidence-applied master through an explicit, traceable Stage → Apply step.</p>
      </div>

      <div className="tabs">
        <span className="tab is-active">Proposed (5)</span>
        <span className="tab">Applied (12)</span>
        <span className="tab">Skipped (3)</span>
        <span className="tab">Sources</span>
      </div>

      <div className="card" style={{ padding: 0 }}>
        <table className="tbl">
          <thead>
            <tr>
              <th>Ticker</th><th>Field</th>
              <th className="num">Current</th><th className="num">Proposed</th>
              <th>Source</th><th>Status</th><th />
            </tr>
          </thead>
          <tbody>
            {proposals.map((p, i) => (
              <tr key={i}>
                <td style={{ fontFamily: "var(--font-mono)", fontWeight: 500 }}>{p.tk}</td>
                <td style={{ color: "var(--ink-700)", fontFamily: "var(--font-mono)" }}>{p.field}</td>
                <td className="num" style={{ color: "var(--ink-500)" }}>{p.was}</td>
                <td className="num" style={{ color: "var(--fg-strong)", fontWeight: 500 }}>{p.now}</td>
                <td style={{ color: "var(--ink-600)", fontSize: 12 }}>{p.source}</td>
                <td><span className={`pill ${p.status === "PROPOSED" ? "partial" : "review"}`}>{p.status}</span></td>
                <td>
                  <span className="row-action">Review update</span>
                  <span className="row-action" style={{ color: "var(--ink-500)" }}>Skip</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="split-1-1" style={{ marginTop: 16 }}>
        <div className="card">
          <div className="card-h"><div className="card-title">Apply to evidence-applied master</div><div className="card-sub">never silent</div></div>
          <p style={{ margin: 0, font: "400 13px/1.5 var(--font-sans)", color: "var(--ink-700)" }}>
            Proposals enter <span className="kbd">fundamentals_master.csv</span> only when explicitly applied. Each apply records the source filing, the run id, and the prior value, producing an evidence-applied artifact.
          </p>
        </div>
        <div className="card">
          <div className="card-h"><div className="card-title">Eligibility</div><div className="card-sub">US-listed only</div></div>
          <p style={{ margin: 0, font: "400 13px/1.5 var(--font-sans)", color: "var(--ink-700)" }}>
            The SEC pipeline only runs against eligible US-listed holdings. Non-US holdings remain managed via the manual fundamentals workflow and are never altered by this pipeline.
          </p>
        </div>
      </div>
    </>
  );
};

window.PlaceholderView = function PlaceholderView({ title, sub }) {
  return (
    <>
      <div className="canvas-header">
        <div className="canvas-eyebrow">Module</div>
        <h1 className="canvas-title">{title}</h1>
        <p className="canvas-sub">{sub}</p>
      </div>
      <div className="card" style={{ padding: 28, color: "var(--fg-muted)" }}>
        This view exists as a placeholder in the UI kit. The Dashboard, Monthly Run, Decision Journal, and SEC Evidence views are the high-fidelity surfaces shipped here.
      </div>
    </>
  );
};

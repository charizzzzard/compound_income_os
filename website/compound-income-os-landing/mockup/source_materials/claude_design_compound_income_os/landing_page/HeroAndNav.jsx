/* Hero, Nav, and the inline hero dashboard mockup */

window.MarketingNav = function MarketingNav() {
  return (
    <nav className="nav">
      <div className="nav-inner">
        <a className="nav-wordmark" href="#top">
          <img src="design-system/assets/wordmark-ink.svg" alt="Compound Income OS" />
        </a>
        <div className="nav-links">
          <a href="#problem">Problem</a>
          <a href="#workflow">Workflow</a>
          <a href="#features">Product</a>
          <a href="#dashboard">Dashboard</a>
          <a href="#access">Access</a>
        </div>
        <div className="nav-actions">
          <a className="btn btn-secondary btn-sm" href="#access">Request GitHub Access</a>
          <a className="btn btn-primary btn-sm" href="#early-access">Join Early Access</a>
        </div>
      </div>
    </nav>
  );
};

window.Hero = function Hero() {
  return (
    <section className="hero-shell" id="top">
      <div className="hero-grid">
        <div className="hero-text">
          <div className="t-eyebrow hero-eyebrow">Local-first portfolio research</div>
          <h1 className="hero-headline">A local operating system for long-term investing.</h1>
          <p className="hero-sub">
            Compound Income OS turns your broker exports, fundamentals, and evidence files
            into reproducible rankings, dashboards, and monthly decision reports.
            Local-first. No broker execution. No advice.
          </p>
          <div className="hero-actions">
            <form className="email-capture" onSubmit={(e) => e.preventDefault()}>
              <input type="email" placeholder="you@domain.com" aria-label="Email address" />
              <button className="btn btn-primary">Join Early Access</button>
            </form>
            <a className="btn btn-secondary" href="#access">Request GitHub Access</a>
          </div>
          <div className="hero-microcopy">
            Open-source core · No cloud account required · Not investment advice
          </div>
          <div className="hero-meta">
            <div><span className="lbl">Runs on</span><span className="val">macOS · Linux · Windows</span></div>
            <div><span className="lbl">Outputs</span><span className="val">CSV · Markdown</span></div>
            <div><span className="lbl">License</span><span className="val">Open-source core</span></div>
          </div>
        </div>

        <HeroDashboard />
      </div>
    </section>
  );
};

window.HeroDashboard = function HeroDashboard() {
  return (
    <div className="hero-dash" aria-hidden="true">
      <div className="hero-dash-bar">
        <div className="left">
          <span className="dot"></span>
          <img src="design-system/assets/wordmark-paper.svg" alt="" style={{ height: 14 }} />
          <span className="meta">local · monthly run</span>
        </div>
        <span className="runid">DEMO-20260426-160500</span>
      </div>

      <div className="hero-dash-primary">
        <div className="big">
          <div className="lbl">Portfolio Value</div>
          <div className="val">€128,420</div>
          <div className="sub">24 positions · Top 5 weight 38.7%</div>
        </div>
        <div className="small">
          <div>
            <div className="lbl">Cash Weight</div>
            <div className="val">8.4%</div>
          </div>
          <span className="pill ok">RESERVE OK</span>
        </div>
      </div>

      <div className="hero-dash-grid">
        <div className="cell">
          <div className="lbl">Dividend TTM</div>
          <div className="val">€3,240</div>
        </div>
        <div className="cell">
          <div className="lbl">Div. Growth 5Y</div>
          <div className="val">7.8%</div>
        </div>
        <div className="cell">
          <div className="lbl">Buy Score</div>
          <div className="val">71.8</div>
        </div>
      </div>

      <div style={{
        background: "var(--dark-700)",
        border: "1px solid var(--dark-600)",
        borderRadius: 10,
        padding: 14,
        marginBottom: 12,
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 8 }}>
          <span style={{ font: "500 10px/1 var(--font-sans)", letterSpacing: "0.14em", textTransform: "uppercase", color: "var(--dark-fg-3)" }}>
            Coverage
          </span>
          <span style={{ font: "400 11px/1 var(--font-mono)", color: "var(--dark-fg-2)" }}>24 holdings</span>
        </div>
        <div className="cov-meter">
          <span className="seg" style={{ width: "62%", background: "#6FA38C" }} />
          <span className="seg" style={{ width: "21%", background: "#C9A765" }} />
          <span className="seg" style={{ width: "8%", background: "#B8843E" }} />
          <span className="seg" style={{ width: "9%", background: "#A75949" }} />
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", marginTop: 10, font: "400 10.5px/1 var(--font-mono)", color: "var(--dark-fg-3)", letterSpacing: "0.04em" }}>
          <span>COVERED · 15</span>
          <span>PARTIAL · 5</span>
          <span>REVIEW · 2</span>
          <span>MISSING · 2</span>
        </div>
      </div>

      <div className="hero-dash-artifact">
        <span>artifact</span><span className="sep">·</span>
        <span>reports/demo/monthly_decision_report.md</span>
      </div>
    </div>
  );
};

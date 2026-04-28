window.MarketingNav = function MarketingNav() {
  return (
    <nav className="nav">
      <div className="nav-inner">
        <a className="nav-wordmark" href="#"><img src="../../assets/wordmark-ink.svg" alt="Compound Income OS" /></a>
        <div className="nav-links">
          <a href="#product">Product</a>
          <a href="#workflow">Workflow</a>
          <a href="#evidence">Evidence</a>
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
    <section className="hero">
      <div className="hero-inner">
        <div className="t-eyebrow hero-eyebrow">Local-first portfolio research</div>
        <h1 className="hero-headline">A local operating system for long-term investing.</h1>
        <p className="hero-sub">Compound Income OS turns your broker exports, fundamentals, and evidence files into reproducible rankings, dashboards, and monthly decision reports. Local-first. No broker execution. No advice.</p>
        <div className="hero-actions">
          <form className="email-capture" onSubmit={(e) => e.preventDefault()}>
            <input type="email" placeholder="you@domain.com" />
            <button className="btn btn-primary">Join Early Access</button>
          </form>
          <a className="btn btn-secondary" href="#access">Request GitHub Access</a>
        </div>
        <div className="hero-microcopy">Open-source core. No cloud account required. Not investment advice.</div>
      </div>
    </section>
  );
};

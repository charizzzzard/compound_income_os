/* Access, Final CTA, Disclaimer, Footer */

window.AccessSection = function AccessSection() {
  const cards = [
    {
      eyebrow: "Open-source core", title: "Core", price: "Free",
      body: "Full local pipeline: positions, scoring, watchlist, monthly ranking, snapshot, decision report, dashboard layer.",
      list: ["Installable on your machine", "No account required", "MIT-style open-source license"],
      cta: "Request GitHub Access", btn: "btn btn-secondary btn-sm",
      featured: false,
    },
    {
      eyebrow: "Pro Modules", title: "Pro", price: "Optional · paid",
      body: "Extended evidence workflows, deeper snowball analytics, additional dashboard sections.",
      list: ["Same local-first architecture", "Nothing leaves your machine", "Drop-in modules over the core"],
      cta: "Join Early Access", btn: "btn btn-primary btn-sm",
      featured: true,
    },
    {
      eyebrow: "Setup Service", title: "Setup", price: "One-time",
      body: "Guided installation, input mapping, fundamentals master scaffolding, and a first reproducible monthly run on your portfolio data.",
      list: ["Installation + environment", "Broker export mapping", "First reproducible monthly run"],
      cta: "Request Setup Service", btn: "btn btn-tertiary btn-sm",
      featured: false,
    },
    {
      eyebrow: "GitHub Sponsors", title: "Sponsor", price: "Any tier",
      body: "Sponsor on GitHub or join Early Access for build updates, early Pro Module previews, and a direct line to the maintainer.",
      list: ["Build update emails", "Early Pro Module previews", "Direct line to maintainer"],
      cta: "Sponsor on GitHub", btn: "btn btn-tertiary btn-sm",
      featured: false,
    },
  ];
  return (
    <section className="section section-tight" style={{ background: "var(--bg-muted)" }} id="access">
      <div className="section-inner">
        <div className="t-eyebrow section-eyebrow">Access · monetization</div>
        <h2 className="section-title">Open core. Paid where it earns its keep.</h2>
        <p className="section-lede">Use the open-source core forever. Pro Modules and the Setup Service exist for the steps that genuinely save you weeks.</p>
        <div className="grid-4" style={{ marginTop: "var(--space-10)" }}>
          {cards.map((c) => (
            <div key={c.title} className={"access-card" + (c.featured ? " is-featured" : "")}>
              <div className="access-card-eyebrow">{c.eyebrow}</div>
              <div className="access-card-title">{c.title}</div>
              <div className="access-card-price">{c.price}</div>
              <div className="access-card-body">{c.body}</div>
              <ul className="access-card-list">
                {c.list.map(x => <li key={x}>{x}</li>)}
              </ul>
              <div className="access-card-footer">
                <a className={c.btn} href="#early-access">{c.cta}</a>
              </div>
            </div>
          ))}
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
        <h2 className="section-title" style={{ color: "var(--dark-fg)", maxWidth: "26ch" }}>Most investing tools are built around a transaction. This one is built around a process.</h2>
        <p className="section-lede" style={{ color: "var(--dark-fg-2)" }}>If a reproducible, local, evidence-backed monthly research workflow is what you've been quietly assembling out of spreadsheets and notebooks — this is the version that already runs.</p>
        <div className="hero-actions" style={{ marginTop: "var(--space-8)" }}>
          <form className="email-capture" onSubmit={(e) => e.preventDefault()}>
            <input type="email" placeholder="you@domain.com" aria-label="Email address" />
            <button className="btn btn-primary">Join Early Access</button>
          </form>
          <a className="btn btn-secondary" href="#">Request GitHub Access</a>
          <a className="btn btn-tertiary" style={{ color: "var(--dark-fg-2)" }} href="#">Request Setup Service</a>
        </div>
        <div className="hero-microcopy" style={{ color: "var(--dark-fg-3)", marginTop: "var(--space-5)" }}>Local-first · Open-source core · Not investment advice</div>
      </div>
    </section>
  );
};

window.DisclaimerBlock = function DisclaimerBlock() {
  return (
    <section style={{ padding: "var(--space-16) var(--space-6) var(--space-8)" }}>
      <div className="section-inner" style={{ maxWidth: 980 }}>
        <div className="disclaimer">
          <strong>Compound Income OS</strong> is a research and decision-support tool. It does not provide investment, tax, or legal advice, does not guarantee any return, and does not execute orders or connect to brokerages. All decisions, risks, and outcomes remain solely with the user. Past data does not predict future results. Illustrative figures shown throughout this page are synthetic demo values for design purposes only.
        </div>
      </div>
    </section>
  );
};

window.Footer = function Footer() {
  return (
    <footer className="footer">
      <div className="footer-inner">
        <div>
          <div style={{ marginBottom: 14 }}>
            <img src="design-system/assets/wordmark-ink.svg" alt="Compound Income OS" style={{ height: 22 }} />
          </div>
          <p className="t-body-sm" style={{ maxWidth: "36ch", margin: 0 }}>A local operating system for long-term investing. Local-first. Open-source core. Not investment advice.</p>
        </div>
        <div>
          <h4>Product</h4>
          <ul>
            <li><a href="#workflow">Workflow</a></li>
            <li><a href="#features">Evidence pipeline</a></li>
            <li><a href="#dashboard">Dashboard</a></li>
            <li><a href="#features">Decision journal</a></li>
          </ul>
        </div>
        <div>
          <h4>Access</h4>
          <ul>
            <li><a href="#early-access">Early Access</a></li>
            <li><a href="#access">GitHub Access</a></li>
            <li><a href="#access">Setup Service</a></li>
            <li><a href="#access">Sponsors</a></li>
          </ul>
        </div>
        <div>
          <h4>Legal</h4>
          <ul>
            <li><a href="#">Disclaimer</a></li>
            <li><a href="#">Privacy</a></li>
            <li><a href="#">License</a></li>
          </ul>
        </div>
      </div>
      <div className="footer-bottom">
        <span>© 2026 Compound Income OS · local-first · open-source core</span>
        <span>v0.1 · prototype</span>
      </div>
    </footer>
  );
};

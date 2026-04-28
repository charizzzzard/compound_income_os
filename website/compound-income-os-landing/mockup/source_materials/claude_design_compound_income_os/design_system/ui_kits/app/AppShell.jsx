/* Sidebar + Topbar + AppShell. */

const NAV = [
  { group: "Overview", items: [
    { id: "dashboard", label: "Dashboard" },
    { id: "monthly",   label: "Monthly Run" },
  ]},
  { group: "Research", items: [
    { id: "watchlist", label: "Watchlist" },
    { id: "ranking",   label: "Ranking" },
    { id: "snowball",  label: "Dividend Snowball" },
  ]},
  { group: "Evidence", items: [
    { id: "evidence",  label: "SEC Evidence" },
    { id: "quality",   label: "Data Quality" },
    { id: "fundamentals", label: "Fundamentals" },
  ]},
  { group: "Records", items: [
    { id: "journal",   label: "Decision Journal" },
    { id: "reports",   label: "Reports" },
    { id: "settings",  label: "Settings" },
  ]},
];

// inline glyphs — flat stroke, currentColor (matches ICONOGRAPHY)
const Glyph = {
  square:   <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4"><rect x="2.5" y="2.5" width="11" height="11" rx="1.5"/></svg>,
  cal:      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4"><rect x="2.5" y="3.5" width="11" height="10" rx="1.5"/><path d="M5 2v3M11 2v3M2.5 6.5h11"/></svg>,
  list:     <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4"><path d="M5 4h8M5 8h8M5 12h8M2.5 4h.01M2.5 8h.01M2.5 12h.01"/></svg>,
  bars:     <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4"><path d="M3 13V8M7 13V4M11 13V10"/></svg>,
  flake:    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4"><path d="M8 2v12M2 8h12M3.8 3.8l8.4 8.4M3.8 12.2l8.4-8.4"/></svg>,
  shield:   <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4"><path d="M8 2l5 2v4c0 3-2.2 5.4-5 6-2.8-.6-5-3-5-6V4l5-2z"/></svg>,
  check:    <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4"><path d="M3 8l3 3 7-7"/></svg>,
  doc:      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4"><path d="M4 2.5h6l3 3V13a.5.5 0 0 1-.5.5h-8.5a.5.5 0 0 1-.5-.5V3a.5.5 0 0 1 .5-.5z"/><path d="M10 2.5V6h3"/></svg>,
  book:     <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4"><path d="M3 3.5h4a2 2 0 0 1 2 2V13a2 2 0 0 0-2-2H3v-7.5zM13 3.5H9a2 2 0 0 0-2 2V13a2 2 0 0 1 2-2h4v-7.5z"/></svg>,
  folder:   <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4"><path d="M2.5 4.5a1 1 0 0 1 1-1h2.5l1.5 1.5h5a1 1 0 0 1 1 1v6a1 1 0 0 1-1 1h-9a1 1 0 0 1-1-1v-7.5z"/></svg>,
  cog:      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4"><circle cx="8" cy="8" r="2"/><path d="M8 1.5v2M8 12.5v2M14.5 8h-2M3.5 8h-2M12.6 3.4l-1.4 1.4M4.8 11.2l-1.4 1.4M12.6 12.6l-1.4-1.4M4.8 4.8L3.4 3.4"/></svg>,
};
const glyphFor = (id) => ({
  dashboard: Glyph.square, monthly: Glyph.cal, watchlist: Glyph.list, ranking: Glyph.bars,
  snowball: Glyph.flake, evidence: Glyph.shield, quality: Glyph.check, fundamentals: Glyph.doc,
  journal: Glyph.book, reports: Glyph.folder, settings: Glyph.cog,
}[id] || Glyph.square);

window.Sidebar = function Sidebar({ active, onChange }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <img src="../../assets/wordmark-ink.svg" alt="Compound Income OS" />
        <span className="sidebar-brand-tag">v0.1</span>
      </div>
      {NAV.map((g) => (
        <div key={g.group}>
          <div className="sidebar-section-label">{g.group}</div>
          <div className="sidebar-nav">
            {g.items.map((it) => (
              <div
                key={it.id}
                className={"sidebar-link" + (active === it.id ? " is-active" : "")}
                onClick={() => onChange(it.id)}
              >
                <span className="glyph">{glyphFor(it.id)}</span>
                <span>{it.label}</span>
              </div>
            ))}
          </div>
        </div>
      ))}
      <div className="sidebar-footer">
        <div className="sidebar-footer-title">Local data</div>
        <div className="sidebar-footer-meta">~/compound-income-os/<br/>data · reports · journal</div>
      </div>
    </aside>
  );
};

window.Topbar = function Topbar({ crumbs, runId }) {
  return (
    <div className="topbar">
      <div className="topbar-crumbs">
        {crumbs.map((c,i) => (
          <span key={i}>
            {i > 0 && <span style={{ margin: "0 8px", color: "var(--ink-300)" }}>/</span>}
            {i === crumbs.length - 1 ? <strong>{c}</strong> : c}
          </span>
        ))}
      </div>
      <div className="topbar-spacer" />
      <span className="topbar-statuschip">Pipeline OK</span>
      <span className="topbar-runid">{runId}</span>
    </div>
  );
};

window.AppShell = function AppShell({ active, onNav, crumbs, runId, children }) {
  return (
    <div className="app">
      <Sidebar active={active} onChange={onNav} />
      <div>
        <Topbar crumbs={crumbs} runId={runId} />
        <div className="canvas">{children}</div>
      </div>
    </div>
  );
};

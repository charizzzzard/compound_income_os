# Compounding Income OS — Mockup Master Plan v4

**Trigger:** Aktueller Repo-Stand zeigt: das System ist 10-Phasen tief, mit 43+ Engines, 11 Configs, einem lokalen Dashboard-Server, einer SEC-Evidence-Pipeline (7 Stufen), Multi-Benchmark-Performance-Engine, Cost/Tax-Ledger, Personal-Run-Orchestrator und einem 4-achsigen Readiness-Gate. Die aktuelle Landingpage zeigt etwa 30 % davon.

**Ziel dieses Plans:** Vorgabe, welche Marketing-Pages und welche Product-UI-Surfaces als Mockups gebaut werden, sodass die nächste Mockup-Runde Compounding Income OS in seiner **Ganzheit** abbildet — ohne den Investor zu überfordern und ohne Brutalismus-Lite-Diskussion (visuelles Treatment kommt parallel über die laufende Spec).

**Nomenklatur:** Code-Stand ist `Compound Income OS`. In dieser Patch-Welle bleibt das so. Ein eventueller Pivot auf `Compounding Income OS` ist eine separate Brand-Decision (siehe Spec v3 Section 2.1).

---

## 1. SYSTEM-INVENTAR (was wir abbilden müssen)

Kondensiert aus `docs/MODULE_CONTRACTS.md`, `docs/CONTEXT_AND_ROADMAP.md`, `configs/*`, `src/*`, `data/processed/*`, `reports/*`. Diese Liste ist die Ground-Truth, gegen die jeder Mockup-Brief unten geprüft wird.

### Pipeline (10 Phasen)
1. **Import** — Broker-CSV / Trade-Republic-PDF read-only normalisieren
2. **Scoring** — Business + Valuation + Buy Score je Holding (0–100, geclamped)
3. **Personal Master / Evidence / Overlay** — Fundamentals-Datenpflege mit 3-stufigem Master (Base / Profiled / Evidence-Applied)
4. **Watchlist** — Kandidaten-Ranking nach Status (CORE / DG / QUALITY_COMPOUNDER / TOO_EXPENSIVE / REVIEW / REJECT)
5. **Monthly Ranking** — Monatskauf-Ranking + Rebalance-Vorschläge, cash-aware
6. **Reports** — Portfolio Snapshot + Monthly Decision Report (Markdown)
7. **Performance & Benchmark** — Multi-Benchmark-Vergleich, Snapshot/Period/History-Modi
8. **Cost / Tax** — Steuer-Ledger, Withholding Taxes, Realized PnL, Fee Drag, Tax Drag
9. **Dashboard** — KPI-Konsolidierung über 5 Metric-Groups + lokaler HTTP-Viewer (`/api/*.json`)
10. **Personal Run Engine** — Stage-Orchestrator mit Manifest, Used-Inputs, Run-Report

### SEC-Evidence-Pipeline (eigene 7-Stufen-Subpipeline)
SEC Scope Prepare → SEC Identity Resolve → SEC Identity Export → SEC CompanyFacts Fetch → Snapshot Ingest → Snapshot Review → Evidence Compose → Evidence Apply

### Portfolio-Architektur (aus `configs/portfolio_rules.yaml`)
4 Sleeves mit harten Bands:
- `CORE_ETF` 45–60 %
- `DIVIDEND_QUALITY_ETF` 10–25 %
- `SINGLE_STOCK` 20–35 %
- `CASH` 5–15 %
Plus: max single position 8 %, max top-10 60 %, max sector 25 %, monthly inflow konfigurierbar.

### Status-Sprache (deutlich reicher als Landingpage zeigt)
- **Coverage:** `COVERED · PARTIAL · REVIEW · MISSING_DATA · NO_MATCH · INSUFFICIENT_INPUTS · INSUFFICIENT_HISTORY · NOT_AVAILABLE · NOT_APPLICABLE`
- **Monthly Action:** `ADD · HOLD · WATCH · REDUCE · EXIT_REVIEW · REVIEW_CORE_DATA · WAIT_VALUATION · DO_NOT_BUY`
- **Readiness:** `READY · REVIEW · BLOCKED` × 4 Achsen (Demo / Decision / Dashboard / Handoff)
- **Blocker-Severity:** `P0_BLOCKER · P1_REVIEW · INFO`
- **Watchlist-Status:** `CORE_CANDIDATE · DG_CANDIDATE · QUALITY_COMPOUNDER_CANDIDATE · TOO_EXPENSIVE · REVIEW · REJECT`

### KPI-Groups (aus `configs/dashboard_kpis.yaml`)
1. Portfolio / Struktur (13 KPIs: total assets, cash weight, top 5/10, sleeves)
2. Score / Fundamentals (gewichtete Business/Valuation/Buy Scores)
3. Benchmark / Performance (rolling, drawdown, volatility — nur aus realen NAVs)
4. Kosten / Steuern (gross/net dividends, withholding, realized PnL, tax drag, fee drag)
5. Datenqualität / Methodik (cross-source flags, methodology notes count, missing block count)

### Reports (existieren als Outputs in `reports/YYYY-MM-DD/`)
14 Report-Typen, u. a. Monthly Decision Report, Portfolio Snapshot, KPI Tier Coverage, Evidence-Applied Downstream Delta, Score-Audit-Provenance, Artifact Freshness, Readiness Status. Jeder ist Markdown + zugehörige CSV-Artefakte.

---

## 2. STRATEGISCHE PRODUKT-NARRATIV-ENTSCHEIDUNG

Bevor ich Pages vorgebe, eine zentrale Strategie-Entscheidung:

**Die Landingpage ist heute eine 1-Page-Story. Das System ist eine 10-Page-Story.** Die Frage ist nicht *"wie machen wir die Landingpage besser"*, sondern *"wie strukturieren wir die Marketing-Site, damit jede Ebene des Systems eine eigene Bühne bekommt, ohne dass der Visitor ertrinkt"*.

Meine Entscheidung: **6 Marketing-Pages + 5 Product-UI-Mockups**.

- **Marketing-Pages** sind das, was potentielle User auf der Website sehen (`/`, `/workflow`, `/evidence`, `/portfolio`, `/dashboard`, `/manifesto`).
- **Product-UI-Mockups** sind eingebettete Screenshots der **realen App-Oberfläche** (lokaler Dashboard-Viewer, Monthly Decision Report Render, Evidence Workspace, Performance Compare, Personal Run Manifest), die auf den Marketing-Pages als visuelle Beweise erscheinen.

Diese Trennung erlaubt:
- **Marketing erzählt** — Identität, Story, Outcome.
- **Product-UI beweist** — die Software existiert wirklich, nicht nur als Konzept.

Beide Tracks haben gemeinsame Markenelemente: Status-Pills, `// CAPS`-Eyebrows, schwarze Highlight-Bars, Paper/Ink/Gold-Palette.

---

## 3. MARKETING-PAGES — 6 PAGES, ENTSCHIEDEN

| # | Page | URL | Zweck in einem Satz | Hauptzielgruppe |
|---|---|---|---|---|
| M1 | **Home** | `/` | Outcome + Identität + 1-Klick-Pfad zu jeder Tiefen-Seite | Erstbesucher, kalt |
| M2 | **The Monthly Decision** | `/workflow` | Wie ein Monat im System aussieht — vom Import bis zum Decision Report | Ernste Investor-Leads |
| M3 | **Evidence & Data Quality** | `/evidence` | Wie das System mit fehlenden Daten umgeht — SEC-Pipeline, Coverage-Tiers, Status-Gates | Skeptiker, Engineering-Mindset |
| M4 | **The Portfolio Model** | `/portfolio` | Sleeves, Rules, Watchlist, Concentration — die Investment-Architektur | Strategie-Interessierte, Dividend-Growth-Mandate |
| M5 | **The Local Dashboard** | `/dashboard` | Was du nach jedem Run lokal sehen kannst — KPIs, Performance, Cost/Tax | Bereits überzeugte Leads, kurz vor Sign-up |
| M6 | **Manifesto & Access** | `/manifesto` | Wer das baut, warum, und wie du Zugang bekommst | Builder-Brand-Affine + alle, die zum CTA wollen |

**Bewusst NICHT als eigene Page:**
- *Pricing* — lebt in M6 als Access-Karten-Block (keine erfundenen Preise).
- *FAQ* — kann später als eigene Page kommen, P2.
- *Performance / Benchmark* eigene Page — wäre Duplikation mit M5.
- *Cost / Tax* eigene Page — Duplikation mit M5.
- *Sample Report Index* — lebt als Link auf M2 (führt zu echtem MD-Sample, sobald URL gesetzt).
- *Builder / About* eigene Page — kompakt in M6 integriert.

**Begründung 6 statt mehr:** Jeder zusätzliche Marketing-Slot frisst Aufmerksamkeit. 6 Pages = 1 Identitätsangebot + 4 Tiefen-Pages (Workflow / Evidence / Portfolio / Dashboard) + 1 Conversion-Page. Mehr brauchen wir nicht. Weniger lässt das System unterverkauft.

---

## 4. PRO PAGE — MOCKUP-BRIEF

Pro Page das gleiche Format: Story-Achse, Sektionen in fester Reihenfolge, eingebettete Product-UI-Mockups, primärer und sekundärer CTA. Alle Texte als finale Englisch-Copy. Status-Sprache und Disclaimer-Regeln aus Spec v2/v3 bleiben erhalten.

---

### M1 — Home (`/`)

**Story-Achse:** *"A calmer way to run a long-term portfolio — and here are five places where the calm is enforced."*
**Veränderung gegenüber heute:** Hero bleibt, alles unter dem Hero wird zu **Teasers für die anderen 5 Pages**, plus das große Final-CTA-Panel. Die heutige One-Pager-Logik (Workflow, Evidence, Snowball, Reinvest, Calendar, Access alle inline) wird **aufgesplittet**.

**Sektionen in Reihenfolge:**

1. **Hero** *(unverändert vs. Mockup-Stand v3)* — H1 `A calmer way to run a long-term portfolio.`, Subline 2 Sätze, Trust-Pill-Cluster, Meta-Strip, Hero-Mini-Dashboard rechts.
2. **3 Problem-Karten** *(unverändert)* — `Where long-term portfolios actually break.`
3. **Builder-Note-Teaser** *(neu, kürzer als Standalone-Page)* — 1 Satz Hook + Link `Read the manifesto →` zu M6.
4. **Five-Promises-Grid** *(neu, ersetzt heutige verteilte Sections)* — eine 5er-Grid, jede Karte ist ein Teaser zu einer Tiefen-Page:
   - Card 1 → M2 Workflow: `One decision a month — same six stages, every month.`
   - Card 2 → M3 Evidence: `Nothing is silently filled.`
   - Card 3 → M4 Portfolio: `Four sleeves. One mandate. Visible rules.`
   - Card 4 → M5 Dashboard: `One local dashboard. Five KPI groups.`
   - Card 5 → M6 Access: `Open-source core. Builder-led. No venture capital.`
5. **Footer-Bar** `BUILT FOR INVESTORS, NOT TRADERS.` *(unverändert)*
6. **Footer + Disclaimer + Mikro-Slogan-Bar** *(unverändert)*

**Eingebettete Product-UI-Mockups (klein, als visuelle Anker):**
- Hero-Mini-Dashboard (existiert bereits — siehe Verifikations-Patch P0)

**Primary CTA:** `Read a sample monthly report` *(unverändert)*
**Secondary CTA:** `See the workflow` *(führt zu M2)*

**Was entfällt gegenüber heute:** Snowball-Section, Reinvest-Comparison-Section und Cashflow-Calendar-Section wandern auf M5 (Dashboard) bzw. M2 (Workflow). Sie waren auf der heutigen 1-Page-Logik überfrachtet. Auf M1 leben sie nur noch als 1-Karten-Teaser im Five-Promises-Grid.

---

### M2 — The Monthly Decision (`/workflow`)

**Story-Achse:** *"This is what a month inside Compound Income OS looks like — from broker export to a Markdown decision report you can re-open in a year."*
**Hauptaufgabe:** Der **wichtigste Beweis** dafür, dass das System ein laufendes monatliches OS ist und kein Einmal-Tool. Diese Page muss den Investor in den Workflow hineinziehen.

**Sektionen in Reihenfolge:**

1. **Page-Hero** — Eyebrow `// THE WORKFLOW`, H1 `Six stages, one monthly cadence.`, Subline `The same six stages every month — so month 12 is just month 1, eleven times reviewed.`
2. **6-Stage-Detail** *(jede Stage als eigene horizontale Karte mit Input → Engine → Output)*:
   - 01. `Import broker data` — Input: Trade Republic PDF / CSV · Engine: `import_broker` + `normalize_positions` · Output: `positions_snapshot.csv`
   - 02. `Score holdings` — Input: positions + fundamentals master · Engine: `scoring_engine` · Output: `company_scores.csv` + `score_audit.csv`
   - 03. `Review evidence` — Input: SEC CompanyFacts + manual evidence · Engine: SEC pipeline + evidence engines · Output: `evidence_registry.csv` + `evidence_applied_master.csv`
   - 04. `Rank watchlist & monthly candidates` — Input: scores + watchlist + portfolio rules · Engine: `watchlist_engine` + `monthly_ranking_engine` · Output: `watchlist_ranked.csv` + `monthly_buy_ranking.csv` + `rebalance_proposals.csv`
   - 05. `Generate the decision report` — Input: alle obigen Artefakte · Engine: `build_monthly_decision_report` · Output: `monthly_decision_report.md`
   - 06. `Journal it` — Input: report + manifest · Engine: `personal_run_engine` · Output: `personal_run_manifest.json` + datierte Reports
3. **The Monthly Decision Report — opened** — Großes Visual: ein **echter, gerenderter Monthly Decision Report** als Long-Screenshot mit Annotationen, was wo steht (Buy / Hold / Review / Blockers / Reasoning). Nicht ein abstraktes Code-Block-Snippet, sondern ein vollständiger Markdown-Render. Siehe Product-UI P2.
4. **The Archive that Compounds** *(aus Spec v3 Section 6.3)* — kompakte Mini-Komposition mit drei Mono-Tags `month_01` / `month_06` / `month_12`. Headline: `Twelve runs. One auditable year.`
5. **Highlight-Bar** `THE SAME WORKFLOW EVERY MONTH. THE SAME WORKFLOW NEXT YEAR.` (schwarz, Mono-Caps, max. 1× auf dieser Page)
6. **Footer** *(unverändert)*

**Eingebettete Product-UI-Mockups:**
- **P1 — Personal Run Manifest** (rechte Seite der Hero-Section, kompakt)
- **P2 — Monthly Decision Report Render** (Hauptvisual nach Section 2)

**Primary CTA:** `Read a sample monthly report` *(öffnet echten MD-Sample wenn `VITE_SAMPLE_REPORT_URL` gesetzt)*
**Secondary CTA:** `See the evidence layer →` *(führt zu M3)*

**Compliance:** Alle Demo-Werte synthetic-demo-gelabelt. Stages benennen explizite Engine-Namen + Output-Filenamen — das ist Authority-Signal für Engineer-Zielgruppe und erfordert keine erfundenen Aussagen.

---

### M3 — Evidence & Data Quality (`/evidence`)

**Story-Achse:** *"Every KPI carries a status. If a number is missing, the report says so. Here is the full machinery that keeps it that way."*
**Hauptaufgabe:** Diese Page ist der **größte Differenzierer gegenüber Yahoo Finance / Sharesight / Excel**. Sie muss tief technisch sein, ohne unzugänglich zu werden. Kernpunkt: das 7-Stufen-SEC-Evidence-Modell + die 9 Status-Labels.

**Sektionen in Reihenfolge:**

1. **Page-Hero** — Eyebrow `// EVIDENCE & DATA QUALITY`, H1 `See what's covered. See what's missing.`, Subline `Most portfolio tools fill in the blanks. Compound Income OS shows you which blanks exist, where they came from, and what it would take to close them.`
2. **The Coverage Tier Table** — eine kompakte Tabelle, die die 4 KPI-Tiers je Holding zeigt: `Core` / `Valuation` / `Dividend FCF` / `Advanced`. Jede Zelle: `OK` / `PARTIAL` / `MISSING` / `NOT_APPLICABLE`. Daneben pro Zeile ein `monthly_action`-Tag (`REVIEW_CORE_DATA` / `WAIT_VALUATION` / `DO_NOT_BUY` / `READY`). Real, aus `personal_kpi_tier_coverage.csv` gelesener Sample-Frame mit synthetischen Tickers.
3. **The 7-Stage SEC Pipeline** *(neu, größtes neues Asset auf dieser Page)* — Horizontaler Flow mit 7 Schritten. Jede Stage hat: Input-Pill, Engine-Name (Mono), Output-Pill, **plus** ein Klartext-Untertitel für Investor:
   - `Scope Prepare` — *"Audit which holdings are in scope for SEC data."*
   - `Identity Resolve` — *"Look up SEC tickers and CIK numbers."*
   - `Identity Export` — *"Export reviewed identities into your private map."*
   - `CompanyFacts Fetch` — *"Read SEC's filed numbers — read-only."*
   - `Snapshot Ingest` — *"Match incoming data exactly to your master."*
   - `Snapshot Review` — *"You approve or reject each update."*
   - `Evidence Apply` — *"Approved updates project into a separate master."*
4. **The 9 Status Labels — explained** — die volle Status-Tabelle (heute zeigt die Landingpage 7, Code hat 9), je mit Klartext-Erklärung. Brutalismus-Lite: Pills in Original-Farben, Erklärungen in Mono-Klein.
5. **The Three-Layer Master** *(neu)* — eine Grafik, die zeigt: `Base Master` (was du eingegeben hast) → `Profiled Master` (welche Holdings im STANDARD-Profil sind) → `Evidence-Applied Master` (was nach reviewed Updates der Stand ist). Wichtig: Original wird **nie** überschrieben — das ist Marken-Authority.
6. **Highlight-Bar** `IF A NUMBER IS MISSING, THE REPORT SAYS SO.` (schwarz, max. 1×)
7. **Footer** *(unverändert)*

**Eingebettete Product-UI-Mockups:**
- **P3 — Evidence Workspace** (zwischen Section 3 und 4 als Visualisierung der SEC-Stage-Pipeline mit echten Status-Pills)

**Primary CTA:** `Read a sample monthly report`
**Secondary CTA:** `See the portfolio model →` *(führt zu M4)*

**Compliance:** Coverage-Sample-Tabelle muss klar als `synthetic demo values` markiert sein. SEC-Stages dürfen explizit benannt werden, da sie Engineering-Realität sind. Drei-Layer-Master ist Architektur-Aussage und claim-safe.

---

### M4 — The Portfolio Model (`/portfolio`)

**Story-Achse:** *"Four sleeves. One mandate. Visible rules. Every monthly decision lives inside this frame."*
**Hauptaufgabe:** Die Investment-Architektur sichtbar machen — wer das System als Investor evaluieren will, will wissen, welches Portfolio-Modell durchgesetzt wird. Heute fehlt diese Page komplett.

**Sektionen in Reihenfolge:**

1. **Page-Hero** — Eyebrow `// THE PORTFOLIO MODEL`, H1 `Four sleeves. One mandate.`, Subline `Compound Income OS enforces a long-term allocation across four sleeves — Core ETF, Dividend Quality ETF, Single Stocks, and Cash. Concentration limits, sector caps, and monthly cash inflow are config, not opinion.`
2. **Sleeve Allocation Bar** — eine horizontale Stacked Bar, die die 4 Sleeves mit ihren Bands zeigt:
   - `CORE_ETF` 45–60 %
   - `DIVIDEND_QUALITY_ETF` 10–25 %
   - `SINGLE_STOCK` 20–35 %
   - `CASH` 5–15 %
   Daneben: `Max single position 8 %`, `Max top-10 60 %`, `Max sector 25 %` als kleine Pill-Kette. Werte aus `configs/portfolio_rules.yaml` direkt zitiert (also keine Erfindung).
3. **The Mandate** *(neu, kurz aber wichtig)* — eine ruhige Section mit dem Watchlist-Universum-Statement aus `configs/watchlist.yaml`: `Target Universe: Dividend Growth + Quality Compounders.` Plus die Watchlist-Status-Pill-Reihe: `CORE_CANDIDATE · DG_CANDIDATE · QUALITY_COMPOUNDER_CANDIDATE · TOO_EXPENSIVE · REVIEW · REJECT`.
4. **The Score Stack** — eine Visualisierung der drei Scores: `Business Score (55%) + Valuation Score (18%) + Expected Return Score (11.25%) + Drawdown Opportunity (9%) + Portfolio Fit (6.75%) = Buy Score`. Aus `configs/scoring_weights.yaml` direkt. Plus die Buy-Rule-Schwellen: `min_business_score: 75 · min_valuation_score: 60 · min_buy_score: 72`.
5. **The Monthly Action Matrix** — Tabelle, die zeigt, welche Holding-Aktion bei welcher Bedingung greift: `ADD / HOLD / WATCH / REDUCE / EXIT_REVIEW / REVIEW_CORE_DATA / WAIT_VALUATION / DO_NOT_BUY`. Pro Aktion: 1-Satz-Bedingung in Klartext.
6. **Watchlist Sample** — ein kleiner gerenderter Watchlist-Block (3-5 Zeilen), der eine echte gerankte Liste mit Status-Pills zeigt. Synthetic-Demo-gelabelt.
7. **Highlight-Bar** `RULES, NOT OPINIONS.` (schwarz, max. 1×)
8. **Footer** *(unverändert)*

**Eingebettete Product-UI-Mockups:**
- **P4 — Holdings & Sleeves View** (nach Section 2 als Tabelle mit Sleeve-Tags)

**Primary CTA:** `Read a sample monthly report`
**Secondary CTA:** `See the local dashboard →` *(führt zu M5)*

**Compliance:** Alle Werte direkt aus den Configs zitiert — keine Erfindung. Klare Trennung "Mandate ist Config, nicht Empfehlung" muss im Subtext lesbar sein.

---

### M5 — The Local Dashboard (`/dashboard`)

**Story-Achse:** *"After every monthly run, your dashboard tells you four things in one local view: where you stand, how it performs, what it costs in tax, and whether the data is honest."*
**Hauptaufgabe:** Diese Page ist der **Conversion-Hebel**. Sie zeigt, was du **nach jedem Run** lokal siehst. Hier leben auch die Snowball / Reinvest / Cashflow-Calendar-Sections, die heute auf der Landingpage stehen — mit echtem Kontext: das ist nicht ein Marketing-Versprechen, das ist die App-Oberfläche.

**Sektionen in Reihenfolge:**

1. **Page-Hero** — Eyebrow `// THE LOCAL DASHBOARD`, H1 `One local dashboard. Five KPI groups.`, Subline `After each run, the local dashboard server consolidates processed artifacts into one view: portfolio structure, scores, performance, cost & tax, and data quality. Read-only. Localhost. No cloud.`
2. **The Five KPI Groups** — fünf horizontal angeordnete Mini-Panels, je 3-4 KPIs:
   - `Portfolio / Structure` — total assets, cash weight, top-5 weight, sleeve weights
   - `Score / Fundamentals` — weighted business / valuation / buy score
   - `Benchmark / Performance` — vs MSCI World / FTSE All-World, with `INSUFFICIENT_HISTORY` flag if applicable
   - `Cost / Tax` — total dividends gross/net, withholding taxes, realized PnL after tax
   - `Data Quality / Methodology` — cross-source flag, methodology notes count, missing block count
3. **Dividend Snowball** *(verschoben von Landingpage)* — Headline `Your dividend snowball, modeled honestly.` plus Edit-Buttons für Annahmen. Ohne Forecast-Wording (`PROJECTED` → `ILLUSTRATIVE`, gemäß Verifikations-Patch P0.2).
4. **Reinvest Comparison** *(verschoben von Landingpage)* — `Two scenarios. Same starting point.` mit Highlight-Bar `REINVESTMENT GENERATES UP TO 2.1× MORE MONTHLY INCOME — IN THIS SCENARIO.` (max. 1× auf dieser Page; `BUILT FOR INVESTORS, NOT TRADERS` lebt im Footer)
5. **Cashflow Calendar** *(verschoben von Landingpage)* — `See your dividend rhythm before it happens.` mit 5-Jahre-Heatmap.
6. **Multi-Benchmark Compare** *(neu)* — eine kompakte Komposition: deine Portfolio-Timeseries vs. zwei wählbare Benchmarks aus dem Archiv. Disclaimer-Pill: `Requires explicit local benchmark archive. Not a prediction.`
7. **Cost & Tax Ledger** *(neu)* — eine Mini-Tabelle: `Total Dividends Gross / Net / Withholding Taxes / Tax Drag / Fee Drag Estimate`. Klar gelabelt: `Requires explicit cost/tax ledger evidence. Otherwise INSUFFICIENT_DOCUMENTATION.`
8. **Footer** *(unverändert)*

**Eingebettete Product-UI-Mockups:**
- **P5 — Local Dashboard Viewer** (Hauptvisual nach Hero — ein gerenderter Screenshot des lokalen HTTP-Dashboards mit Sidebar-Navigation und 5 KPI-Groups)

**Primary CTA:** `Read a sample monthly report`
**Secondary CTA:** `Get access →` *(führt zu M6)*

**Compliance:** Alle Demo-Werte synthetic-demo-gelabelt. Performance-Section MUSS sichtbar machen, dass Performance-Engine erst ab 12 expliziten NAV-Punkten vollständig läuft (`INSUFFICIENT_HISTORY`-Sprache aus Code). Cost/Tax-Section MUSS sichtbar machen, dass ohne Event-Evidenz kein Full-Ledger berechnet wird (`INSUFFICIENT_DOCUMENTATION`-Sprache aus Code). Beides ist im Code dokumentiert und claim-safe.

---

### M6 — Manifesto & Access (`/manifesto`)

**Story-Achse:** *"This is who built it, why, and how to get access — without venture capital, without a black box, without hype."*
**Hauptaufgabe:** Die Builder-Voice voll ausgespielt + 3 Access-Karten + Honest-Pending-State. Fasst Marken-Identität und Conversion in einer Page.

**Sektionen in Reihenfolge:**

1. **Page-Hero** — Eyebrow `// THE MANIFESTO`, H1 `I built this because the tools I needed didn't exist.`, gleicher Body-Text wie heute, gleiches Wordmark-Echo statt Beton-Foto. Aber: hier auf eigener Page voll ausgespielt, mit mehr Atem.
2. **Six Commitments** *(die 6 Architecture-Principles, voll ausgespielt mit den menschlicheren Bodies aus Spec v3 Section 4)*:
   - `Local-first` · *"Your portfolio runs from your files, on your machine."*
   - `Privacy-first` · *"Your raw broker data never mixes with what we generate."*
   - `No cloud lock-in` · *"Core workflow is portable files and code."*
   - `Decisions, not orders` · *"Compound Income OS shows you what to look at. You decide what to do with it."*
   - `Nothing is silently filled` · *"If a number is missing, the report says so."*
   - `The same inputs, the same outputs` · *"Every monthly run records what went in, what came out, and what changed."*
3. **What this is not** *(neu, der Anti-Audience-Block aus Spec v2/v3)* — `Not built for: day traders, options speculators, leveraged or crypto-driven strategies, signal subscribers, anyone seeking execution, hot tips, or personalized investment advice.` 1 Satz, mono, gedimmter Container.
4. **Access** — die 3 Karten (`Open-Source Core` / `Pro Modules` / `Setup Help`) genau wie auf der heutigen Landingpage. Footer-Microline `Pending access is shown clearly. No fake checkout flow.`
5. **Public Launch Status** *(neu, ehrliches Statement)* — eine kleine Box mit Pending-Items: `Imprint pending · Privacy policy pending · Real CTA targets pending · Pricing TBD`. Direkt aus den `siteConfig.js`-Pending-States. Demonstriert Brand-Honesty.
6. **Footer** *(unverändert)*

**Eingebettete Product-UI-Mockups:** keine — diese Page ist Builder-Voice-getrieben, die App lebt auf den anderen 5 Pages.

**Primary CTA:** `Get early access` *(öffnet `VITE_EARLY_ACCESS_URL` oder rendert Pending-Pill)*
**Secondary CTA:** `View on GitHub` *(öffnet `VITE_GITHUB_URL` oder Pending)*

---

## 5. PRODUCT-UI-MOCKUPS — 5 SURFACES, ENTSCHIEDEN

Diese Mockups sind **App-Screenshots**, eingebettet in die Marketing-Pages oben. Sie sind keine Live-UI-Komponenten — sie sind hochwertige Renderings, die zeigen, was real ist. Sie nutzen die Status-Sprache und Brutalismus-Lite-Visuals der Landingpage.

| # | Surface | Wo eingebettet | Was es zeigt | Aus welchem Engine |
|---|---|---|---|---|
| **P1** | Personal Run Manifest View | M2 Hero-rechts | Ein gerenderter `personal_run_manifest.json`-Auszug + Stage-Status-Liste mit Pills | `personal_run_engine` |
| **P2** | Monthly Decision Report (rendered Markdown) | M2 Hauptvisual | Ein vollständig gerenderter `monthly_decision_report.md` mit Buy/Hold/Review/Blockers/Reasoning-Sektionen | `build_monthly_decision_report` |
| **P3** | Evidence Workspace | M3 Mitte | Eine Tabelle mit SEC-Pipeline-Stages und je Stage Status-Pills (`PENDING / APPROVED / REJECTED / STAGED`) plus Evidence-Apply-Registry | SEC-Pipeline + `fundamentals_evidence_engine` |
| **P4** | Holdings & Sleeves View | M4 nach Sleeve-Bar | Eine Tabelle: Ticker · ISIN · Sleeve-Tag · Coverage-Tier · Monthly Action · Score | `fundamentals_master` + `portfolio_review` |
| **P5** | Local Dashboard Viewer | M5 Hauptvisual | Ein gerenderter Browser-Screenshot des lokalen HTTP-Viewers (`localhost:port/`) mit Sidebar (5 KPI-Groups), Hauptpanel, Zeitstempel-Header | `dashboard_server` |

**Was wir bewusst NICHT als Product-UI-Mockup machen:**
- Eine "Holdings Detail"-Seite — zu spezifisch, lebt in P4 als Tabellenzeile.
- Ein "Watchlist Editor" — Watchlist ist Input-CSV, kein editierbares UI im aktuellen System.
- Ein "Settings" / "Profile" Screen — gehört in einer späteren Produkt-Phase, nicht im aktuellen System.
- Cost/Tax-Editor — Cost/Tax-Inputs sind manuelle Ledger-CSVs, kein UI.
- Personal Run Engine als interactive UI — der Run ist CLI-getriggert, nicht UI-getriggert; die Manifest-Sicht (P1) genügt.

**Product-UI-Stilregeln (für alle 5 Mockups):**
- Dunkles Panel (Paper-Ink-Gold-Palette, gleiches Treatment wie heutiges Hero-Dashboard).
- Status-Pills in Original-Farben (`OK` grün-ish, `PARTIAL` gold, `REVIEW` orange, `MISSING_DATA` red-ish).
- Mono-Font für Code-/Filename-/Manifest-Felder.
- Sichtbares `synthetic demo values`-Label im Header jedes Mockups.
- Synthetische Tickers (`MSFT`, `V`, `JNJ`, `KO`, `LIN`) — keine erfundenen Companies.
- Synthetische, aber realistische Werte (€-Beträge im Bereich realer DACH-Investor-Größen, nicht $1.23M Aspirational).

---

## 6. WAS AUF JEDER PAGE GEMEINSAM IST (Marken-Konstanten)

Diese Elemente erscheinen **auf jeder Marketing-Page** und gewährleisten Marken-Konsistenz, ohne dass jede Page neu erfunden werden muss:

| Element | Wo | Inhalt |
|---|---|---|
| **Header** | top, alle Pages | Wordmark links · Nav: `Workflow · Evidence · Portfolio · Dashboard · Manifesto` · Primary CTA `Get early access` · Secondary Textlink `View on GitHub` |
| **Eyebrow-Format** | top jeder Section | `// CAPS` (mit `//`-Prefix in Mono) |
| **Trust-Pill-Cluster** | Hero auf M1, optional M6 | `LOCAL-FIRST · OPEN-SOURCE CORE · EVIDENCE-BASED · NO BROKER · NO CLOUD` |
| **Highlight-Bar** | max. 1× pro Page | schwarze full-width Bar, weiße Mono-Caps, eine prägnante Aussage |
| **Status-Pills** | überall wo Daten gerendert sind | farb-codiert nach `pill-ok` / `pill-partial` / `pill-review` / `pill-missing` |
| **Synthetic-Demo-Pill** | jedes Demo-Visual | `synthetic demo values` (mono, klein) |
| **Footer-Bar** | unter Final-CTA jeder Page | `BUILT FOR INVESTORS, NOT TRADERS.` |
| **Mikro-Slogan-Bar** | unten jeder Page | `BUILT SLOW · USED MONTHLY · PRIVACY BY DEFAULT · NO HYPE · JUST SIGNAL · YOUR DATA · YOUR MACHINE` |
| **Footer-Disclaimer + Pending-Footer-Links** | jede Page | identischer Disclaimer-Block + `Imprint` / `Privacy` als Pending-Links |

**Deltas zu heute (Landingpage 1-Pager):**
- Snowball, Reinvest, Cashflow-Calendar wandern von M1 nach M5.
- Builder-Note wandert von M1 (Section) nach M6 (eigene Page) — bleibt aber als Teaser auf M1.
- Workflow wandert von M1 (Section) nach M2 (eigene Page) — bleibt als Teaser auf M1.
- Evidence wandert von M1 (Section) nach M3 (eigene Page) — bleibt als Teaser auf M1.
- Access wandert von M1 (Section) nach M6 (eigene Page) — bleibt als Teaser auf M1.

**M1 wird dadurch radikal kürzer** — Hero + 3 Problem-Karten + 5 Teaser-Karten + Footer. Vielleicht 4–5 Bildschirmhöhen statt heute 8–10. Das ist Absicht: M1 ist Wegweiser, nicht Encyclopedia.

---

## 7. PRIORISIERUNG — WELCHE MOCKUPS ZUERST

Wir können nicht 6 Marketing-Pages + 5 Product-UI-Mockups auf einmal in Mockup-Qualität liefern. Hier die Reihenfolge nach Impact-pro-Stunde:

### Welle 1 — Strukturpfeiler *(diese Mockup-Runde)*

| Page / Surface | Warum jetzt |
|---|---|
| **M1 Home** *(redesign zu Wegweiser-Layout)* | Bestehende Page, größter Conversion-Hebel, Mockup ist Brutalismus-Lite-Showcase |
| **M2 Workflow** | Wichtigster neuer Beweis dafür, dass das System ein OS ist, nicht ein Tool |
| **P2 Monthly Decision Report Render** | Belegt M2 visuell — ohne diesen Render ist M2 leer |
| **P5 Local Dashboard Viewer** | Wenn nur EIN Product-UI-Mockup gemacht wird, dann dieser — er beantwortet "Was sehe ich nach jedem Run" |

### Welle 2 — Tiefen-Beweise *(nächste Mockup-Runde)*

| Page / Surface | Warum dann |
|---|---|
| **M3 Evidence & Data Quality** | Kerndifferenzierer, aber tiefer technisch — folgt Welle 1 |
| **M5 Local Dashboard** *(eigene Page)* | Verlagert Snowball/Reinvest/Calendar von M1 hierher; sobald P5 existiert ist das schnell |
| **P3 Evidence Workspace** | Belegt M3 visuell |
| **P1 Personal Run Manifest View** | Kompaktes Asset, belegt die Auditierbarkeit |

### Welle 3 — Vervollständigung *(später)*

| Page / Surface | Warum später |
|---|---|
| **M4 Portfolio Model** | Wichtige Page, aber bestehende Investoren-Audience kann auch ohne überzeugt werden — ergänzt das Bild |
| **M6 Manifesto & Access** *(eigene Page)* | Heutige Sections funktionieren als Übergangslösung; eigene Page kommt sobald Welle 1+2 stehen |
| **P4 Holdings & Sleeves View** | Belegt M4 |

### Bewusst NICHT in dieser Mockup-Welle

- **Brutalismus-Lite-Visualisierung** — das ist eine eigene Spec (Strategy Review v3 Section 7), zieht parallel.
- **Mobile-Mockups** — alle Mockups Desktop-first, Mobile als Folge-Patch.
- **Animationen / Microinteractions** — zu früh; Mockups sind statische Stills.
- **Dark-Mode global** — die Marketing-Site bleibt Paper/Ink/Gold; die Product-UI bleibt Dark-Panel. Das ist Absicht.

---

## 8. DECISION CHECKPOINTS — WAS DU JETZT BESTÄTIGEN MUSST

Bevor die nächste Mockup-Runde startet, drei Punkte, die ich nicht autoritär entscheiden kann:

1. **Markenname final** — Code-Stand ist `Compound Income OS`. Du hast in der Frage `compounding income os` geschrieben. Wenn das nur Sprechgewohnheit ist: Markenname bleibt. Wenn das ein impliziter Pivot ist: das wäre ein eigener Patch-Zyklus, der Repo-Name, Domain, GitHub-Handle, alle Markenassets berührt — und ich würde das **nicht** in dieser Mockup-Runde mitziehen.
2. **Sprache final** — Marketing-Pages bleiben Englisch (laut letztem Briefing). Wenn DACH-Markt im Fokus ist und du DE willst, ist das jetzt der Zeitpunkt — danach 6 Pages auf DE statt EN zu ziehen wird teuer.
3. **Welle-1-Umfang final** — Ich schlage vor: M1 Redesign + M2 Neue Page + P2 Report-Render + P5 Dashboard-Viewer. Das sind 4 Mockup-Assets. Wenn du nur 2 willst: M2 + P5 (die zwei stärksten Neuigkeiten). Wenn du 6 willst: + M3 Evidence + P3 Evidence Workspace.

Ich empfehle **die 4 Welle-1-Assets** — das ist der größte Sprung mit kontrollierbarem Aufwand.

---

## 9. WAS WIR DAMIT *NICHT* TUN

- Wir bauen keinen Code-Change in dieser Runde. Mockups gehen vor Implementation.
- Wir erfinden keine Features (`Compare benchmarks` als Workflow-Step #5 bleibt aus den Mockups draußen, bis das Modul aus Engineering bestätigt ist).
- Wir verwenden keine Live-User-Daten in Mockups. Alle Werte sind synthetic-demo-gelabelt.
- Wir bauen keine Public-Launch-Pages. Imprint/Privacy/Pricing bleiben Pending-States.
- Wir werfen keine bestehenden Marken-Assets weg. Wordmark, Paper/Ink/Gold-Palette, Status-Sprache, Disclaimer-Strenge bleiben.
- Wir machen die Product-UI-Mockups **nicht** als interaktive UI-Komponenten — sie sind hochwertige statische Renderings für die Marketing-Site.

---

## 10. FINAL RECOMMENDATION

**Was als nächstes konkret passiert:**
1. Diese Mockup-Plan-Spec von dir bestätigt bekommen *(insbesondere die 3 Decision Checkpoints in Section 8)*.
2. Mockups für **Welle 1** beginnen: M1 Redesign + M2 Workflow Page + P2 Report Render + P5 Dashboard Viewer.
3. Brutalismus-Lite-Visual-Patch parallel ziehen (separate Spec, Strategy Review v3 Section 7).

**Was bewusst nicht passiert:**
- Wir bauen keine M3/M4/M5/M6 in der ersten Welle.
- Wir machen keine Brand-Pivots.
- Wir verschieben keine Compliance-Constraints.

**Drei Änderungen mit dem größten Impact in Welle 1:**
1. **M1-Redesign zum Wegweiser** — alle Tiefen-Sections weg, dafür 5-Promises-Grid mit Page-Teasern. Macht M1 atembar und gibt jeder Tiefen-Story Raum.
2. **M2 als eigene Page mit P2 Report-Render** — der wichtigste neue Beweis, dass das ein OS ist, nicht ein Hero-Tool.
3. **P5 Local Dashboard Viewer** — das einzige Visual, das die User-Frage *"was kriege ich nach jedem Run zu sehen"* direkt beantwortet.

**Bestehende Markenelemente, die geschützt bleiben:**
- Hero-H1 `A calmer way to run a long-term portfolio.` und gesamte Tonalität aus Verifikations-Mockups.
- Status-Sprache (`COVERED · PARTIAL · REVIEW · MISSING_DATA`).
- Builder-Voice mit anonymer Signatur.
- Anti-Hype-Disclaimer-Strenge.
- Paper/Ink/Gold-Palette + Wordmark.
- Mikro-Slogan-Bar im Footer.
- Pending-Honest-States für CTAs ohne ENV-URL.

---

*Master Plan erstellt auf Basis von `compound_income_os_HANDOFF_20260427-101335_c02419b.zip` (vollständiger Repo-Stand inkl. `docs/MODULE_CONTRACTS.md`, `configs/*`, `src/* ` 43 Engines, `data/processed/* ` Outputs, `reports/*` 14 Report-Typen). Keine Codeänderungen vorgenommen. Dieser Plan ist die Vorgabe für die nächste Mockup-Runde — keine Spec-Änderung, keine Implementation.*

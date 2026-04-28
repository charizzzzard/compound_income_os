# Compound Income OS — Landingpage Fix Spec

**Scope:** Entscheidungsfertige Spezifikation für eine minimal-invasive Patch-Runde der bestehenden Landingpage. Keine Codeänderungen in diesem Dokument, kein Audit, kein Codex-Prompt — nur die Specs, die ein Engineer und ein Codex-Operator anschließend deterministisch in Patches überführen können.

**Eingabequellen:** `context/Compound_Income_OS_Landingpage_Audit.md`, `website/src/App.jsx`, `website/src/siteConfig.js`, `website/src/styles/design-tokens.css`, `website/src/styles/landing.css`, `screenshots/01–06`, `samples_optional_sanitized/*`, `docs_optional/PROJECT_CHARTER.md`.

**Sprache:** Landingpage-Copy = Englisch. Erläuterungen/Begründungen = Deutsch.

---

## A. EXECUTIVE DECISION

Die Landingpage wechselt von einer prozess-/architektur-getriebenen Erzählung zu einer **outcome- + cadence-getriebenen** Erzählung, ohne den ruhigen, evidenzbasierten Markenton zu verlieren. Die neue Story-Achse heißt: *„One defensible investment decision a month — locally, with evidence."* Diese Achse trägt die Zielgruppe (Dividend Growth + Quality Compounders), grenzt sich klar gegen Trading/Broker-Tools ab, ist seriös ohne Hype und macht Retention (monatlicher Zyklus + Decision-Archiv) zur Hauptbotschaft statt zu einer Randbemerkung.

**Bewusst geändert:** Hero-Headline + Subline werden outcome-orientiert; das Hero-Demo-Dashboard wird auf 3× OK + 1× REVIEW umkonfiguriert; Disclaimer-Last im Hero wird reduziert (drei Negativ-Aussagen → ein kompaktes Trust-Statement); CTAs werden auf eine klare Hierarchie (Primary „See the sample monthly report" / Secondary „View the workflow") gestrafft; `mailto:early-access@example.invalid` wird als sichtbare produktive CTA-Adresse vollständig entfernt; Access-Karten von 4 auf 3 reduziert; Core Features in 3 Hauptmodule + 5 Sub-Features hierarchisiert; Workflow um eine kleine Archive-Story ergänzt; SEC/Data-Quality-Section bekommt Klartext-Erklärungen pro Status-Pill.

**Bewusst erhalten:** Paper/Ink/Gold-Palette, Typografie, dunkles Dashboard-Panel, Decision-Journal-Code-Block, Status-Pill-Sprache (`COVERED`, `PARTIAL`, `REVIEW`, `MISSING_DATA`, `INSUFFICIENT_INPUTS`, `INSUFFICIENT_HISTORY`), die 6 Architekturprinzipien als Markenherz, der ehrliche Anti-Hype-/Anti-Broker-/Anti-Cloud-Ton, der ausführliche Footer-Disclaimer.

**Mit diesem Fix adressiert (P0):** Hero-Outcome, Hero-Demo-Wahrnehmung („unfertig"), Mailto-Platzhalter als sichtbares CTA-Ziel, Access-Redundanz, Cognitive Overload bei Core Features.

**Bleibt bewusst Blocker, nur dokumentiert:** Impressum, Datenschutzerklärung, finale Pricing-Werte, echte Early-Access-/Repo-/Sample-URLs, öffentlicher Deploy. Diese werden in `README.md` und `DEPLOYMENT_NOTES.md` als „Public Launch Blockers" festgehalten, aber nicht durch Fake-Inhalte ersetzt.

---

## B. FINAL POSITIONING

**1. One-liner Positioning**
> Compound Income OS is a local, evidence-based operating system for one defensible investment decision a month — built for long-term dividend-growth and quality-compounder investors who want structure, not signals.

**2. Category Name**
> **Monthly Decision OS** *(Subtitel auf Marketing-Materialien optional: „for long-term compounders")*.

**3. Primary Audience Statement**
> Long-term private investors with a dividend-growth and quality-compounder mandate, who run their portfolio research themselves, are comfortable with local files and Markdown reports, and want a reproducible monthly decision instead of a daily noise feed.

**4. Anti-Audience Statement**
> Not for day traders, options speculators, leveraged or crypto-driven strategies, signal subscribers, or anyone looking for execution, hot tips, or personalized investment advice.

**5. Brand Principles (max. 5)**
1. **Local-first.** Your portfolio runs from your files, on your machine.
2. **Evidence-based.** Missing data stays visible; nothing is silently filled.
3. **Decisions, not orders.** The system documents and ranks. It never executes.
4. **Monthly cadence.** One reproducible decision a month, not a stream of signals.
5. **Reproducible by design.** Every run leaves an auditable artifact behind.

**6. Messaging Pillars (max. 4)**
1. **Outcome:** *„One defensible monthly decision."* Replaces the seven-Excel-tab ritual with a deterministic, journaled run.
2. **Trust:** *„Evidence stays visible."* Status labels (`COVERED`, `PARTIAL`, `REVIEW`, `MISSING_DATA`) are first-class outputs.
3. **Boundaries:** *„No broker. No cloud. No advice."* Anti-trading, anti-cloud, anti-advice — said once, said clearly, then dropped.
4. **Compounding archive:** *„Twelve months become an audit trail."* Each run grows a personal decision history in your own files.

---

## C. FINAL HERO PACKAGE

**Entscheidungen vorab (so wie das Briefing gefragt hat):**
- ✅ **„Start with the workflow, not the trade."** wandert in den Hero — als **Eyebrow**, nicht als H1. Das macht den Anti-Trading-Anker zur ersten lesbaren Aussage und schützt die H1 für Outcome.
- ✅ **„One defensible investment decision a month."** wird die H1, leicht gekürzt gegenüber dem Audit-Vorschlag. *„Locally. With evidence."* wandert in die Trust-Zeile, damit die H1 atmen kann.
- ✅ **„Not investment advice"** wird **aus dem Hero entfernt** und nur noch in (a) der kompakten Trust-Zeile als Teil eines kombinierten Statements und (b) im Footer-Disclaimer geführt. Doppel-/Tripel-Disclaimer im Hero entfällt.

### Finale Hero-Copy

| Element | Finaler Wert |
|---|---|
| **Eyebrow** | `Start with the workflow, not the trade.` |
| **H1** | `One defensible investment decision a month.` |
| **Subheadline** | `Compound Income OS turns your broker exports, fundamentals, and SEC evidence into one reproducible monthly decision report — locally, with every data gap visible.` |
| **Primary CTA Label** | `See the sample monthly report` |
| **Primary CTA Behavior** *(siehe G für Funnel-Spec)* | Wenn `VITE_SAMPLE_REPORT_URL` gesetzt → externer Link. Wenn nicht gesetzt → Anchor zu `#access` + Hero zeigt direkt unter den CTAs den Status-Pill `Private preview · sample available on request`. **Niemals** Mailto-Platzhalter. |
| **Secondary CTA Label** | `View the workflow` |
| **Secondary CTA Behavior** | Anchor-Link zu `#workflow`. Funktioniert immer, ohne externe URL. |
| **Trust Statement** *(ersetzt die aktuelle Microcopy unter den CTAs)* | `Local-first · Open-source core · Evidence-based · No broker. No cloud.` |
| **Meta Strip (3 Items, behalten + ein Wert getauscht)** | `Mode: Local files` · `Outputs: CSV / Markdown` · `Cadence: Monthly` |

**Was aus dem Hero entfernt wird:**
- Bisherige Microcopy `Open-source core. No cloud account required. Not investment advice.` → ersetzt durch das Trust Statement oben (kein zweiter Disclaimer mehr im Hero).
- Bisheriger Meta-Strip-Wert `Broker: No connection` → ersetzt durch `Cadence: Monthly` (No-Broker-Aussage steckt jetzt im Trust Statement; Cadence ist die wichtigere Outcome-Dimension).
- Doppelter „Not investment advice"-Stempel aus der Subline. **„Not investment advice" bleibt nur im Footer-Disclaimer.**

**Was im Hero erhalten bleibt:**
- Layout (Text links, dunkles Dashboard-Panel rechts).
- Premium-Typografie und Paper-/Ink-/Gold-Farbpalette.
- Synthetic-Demo-Pill auf dem Dashboard-Panel.

---

## D. HERO DASHBOARD DEMO SPEC

**Regel:** Mehrheits-OK im Hero. Datentransparenz bleibt sichtbar (1× REVIEW), aber prägt nicht den ersten Eindruck. Keine echten Finanzdaten — alles synthetisch und so gelabelt.

### Hero-Demo (4 KPIs, kompakt, dunkles Panel rechts)

| KPI | Demo Value | Status | Begründung |
|---|---|---|---|
| Portfolio Value | `€128,420` | `OK` | Solider Anker-KPI, signalisiert „Software arbeitet". |
| Dividend Growth 5Y | `7.8%` | `COVERED` | Macht den Quality-Compounder-Mandat sichtbar; `COVERED` zeigt eine zweite, stärkere Vertrauensstufe. |
| Cash Weight | `8.4%` | `OK` | Zeigt Portfolio-Disziplin („Reserve inside rule band"); ruhiges, kompetentes Signal. |
| Monthly Candidate | `REVIEW` | `REVIEW` | Bewusst sichtbar — beweist „Evidence stays visible" als Markenversprechen. Genau ein REVIEW im Hero. |

**Synthetic-Demo-Note (klein, oberhalb des KPI-Grids, behalten):**
> `synthetic demo values`

**Status-Legende (klein, unter dem Dashboard-Panel, neu):**
> `OK = within rules · COVERED = evidence complete · REVIEW = pending decision · PARTIAL / MISSING_DATA = gaps stay visible (see Evidence)`

### Volle Dashboard-Preview-Section (zweite Section, unverändert in Funktion, aber Pill-Verteilung optimiert)

Die volle Dashboard-Preview-Section (10 KPIs, dunkles Panel) **darf** weiterhin Lücken zeigen — sie ist der Ort, an dem die Marke „Missing data stays explicit" beweist. Aber die Verteilung wird leicht zugunsten des positiven Signals verschoben:

| KPI | Demo Value | Status |
|---|---|---|
| Portfolio Value | `€128,420` | `OK` |
| Cash Weight | `8.4%` | `OK` |
| Positions | `24` | `OK` |
| Top 5 Weight | `38.7%` | `OK` |
| Dividend Income TTM | `€3,240` | `COVERED` |
| Dividend Growth 5Y | `7.8%` | `COVERED` |
| Data Quality | `PARTIAL` | `PARTIAL` |
| Monthly Candidate | `REVIEW` | `REVIEW` |
| Valuation Band | `Fair / Watch` | `REVIEW` |
| Review Flags | `2` | `REVIEW` |

**Verschiebung gegenüber dem aktuellen Stand:** `Positions` und `Top 5 Weight` wechseln auf `OK` (waren teils `PARTIAL`/`OK`); `Dividend Income TTM` und `Dividend Growth 5Y` werden zu `COVERED` (waren `PARTIAL`); `Review Flags` von `6` → `2` (zwei klar lesbare offene Punkte statt einer Zahl, die nach „Software hat 6 Probleme" aussieht).

**Subtle Chart Area (rechts unten im großen Dashboard):** Untertitel ändern von `Illustrative line from synthetic demo values. Not a forecast.` zu kürzer und ruhiger:
> `Illustrative scenario · synthetic demo data`

---

## E. SECTION-BY-SECTION FIX SPEC

Pro Sektion: **Aktion · Ziel · finale Headline · finale Lede/Subline · finale Cards/Bullets · konkrete Replacements · UX-Hinweise · was nicht geändert wird.**

### 1. Header

- **Aktion:** **Reduce.**
- **Ziel:** Genau ein Primärbutton, ein Secondary-Textlink. Navigationspunkte präziser.
- **Nav-Labels (final):** `Workflow · Evidence · Access · GitHub`
- **Header-CTAs (final):** Primary Button `Get early access` *(siehe G zu Behavior)*. Secondary als Textlink: `View on GitHub` *(linkt extern wenn `VITE_GITHUB_URL` gesetzt, sonst optisch dezent gestyled mit `aria-disabled` Tooltip „Repository link pending")*.
- **Replacements:**
  - Aktuelle Nav-Labels `['Product', 'Workflow', 'Evidence', 'Access']` → `['Workflow', 'Evidence', 'Access', 'GitHub']` (Anker `#workflow`, `#evidence`, `#access`, externer Link via siteConfig).
  - Aktueller Header-CTA `Request GitHub Access` als Secondary-Button → ersetzt durch dezenten Textlink `View on GitHub`.
  - Aktueller Header-CTA `Join Early Access` → bleibt als einziger Primary-Button, Label-Tausch auf `Get early access`.
- **UX-Hinweise:** Sticky-Header und Backdrop-Blur unverändert lassen. Mobile: Primary-Button rechts behalten, Short-Label `Get access` (ersetzt aktuelles `Join`).
- **Nicht ändern:** Logo, Position, Backdrop-Blur, Höhe.

### 2. Hero

- **Aktion:** **Rewrite.** Komplett neue Copy laut Section C.
- **Ziel:** Outcome zuerst, Cadence sichtbar, Disclaimer-Last halbiert, klare CTA-Hierarchie.
- **Final:** siehe Section C, übernehmen 1:1.
- **UX-Hinweise:** Eyebrow visuell etwas größer als bisher gestalten (markant), damit „Start with the workflow, not the trade." trägt. Primary- und Secondary-Button visuell klar unterschiedlich (Solid + Ghost statt zwei stark gefärbte Buttons).

### 3. Dashboard Preview *(Hero-Mini-Dashboard und große Preview-Section gemeinsam)*

- **Aktion:** **Rewrite Demo Values.**
- **Ziel:** Erster Eindruck = kompetente Software, zweiter Eindruck = ehrliche Software.
- **Final:** siehe Section D.
- **Section-Subtitel der großen Preview-Section (neu, kleiner Eyebrow oberhalb des Panels):** `Local · monthly run · synthetic demo`
- **UX-Hinweise:** Status-Legende (siehe D) als kleine, monospace-gesetzte Zeile unter dem Panel platzieren — gehört visuell zum Panel, nicht zur nächsten Section.
- **Nicht ändern:** Dunkles Panel, Manifest-Sidebar, Artifact-Strip am unteren Rand, Wordmark im Panel-Header.

### 4. Problem

- **Aktion:** **Rewrite copy.** Struktur (3 Karten) bleibt.
- **Ziel:** Aus Engineer-Symptomen werden Investor-Symptome.
- **Headline (final):** `Where long-term portfolios actually break.`
- **Lede (final):** `Research fragments over time. Watchlists drift. Reasons get lost. The monthly decision becomes an act of memory rather than evidence.`
- **Karten (final):**

| # | Title | Body |
|---|---|---|
| 01 | `The watchlist no one updated.` | `Tickers added years ago, never reviewed since. The thesis is gone. The position is still in.` |
| 02 | `The KPI that was missing.` | `A score gets computed anyway. The decision rests on data that wasn't there. You don't notice until next quarter.` |
| 03 | `The decision you can't reconstruct.` | `"Why did I buy that?" The reasoning was in your head. It's no longer there. The position is.` |

- **Replacements:** Aktuelle Karten `Data drift / Evidence gaps / Process loss` werden durch obige drei ersetzt. Eyebrow `Problem` und Section-Titel `Where long-term portfolios actually fail.` → Section-Titel ändert sich auf `Where long-term portfolios actually break.` (kleines Wording, aktiver).
- **Nicht ändern:** Layout, 01/02/03-Indices, Card-Styling.

### 5. Solution

- **Aktion:** **Rewrite copy + leicht aufladen.**
- **Ziel:** Kein leerer Übergang mehr. Klare Brücke zwischen Problem und Workflow.
- **Eyebrow:** `Solution`
- **Headline (final):** `The portfolio as local infrastructure.`
- **Lede (final):** `Compound Income OS treats the research workflow as a deterministic local pipeline: declared inputs in, reproducible artifacts out. Data quality, evidence status, and reasoning are first-class outputs at every step.`
- **UX-Hinweise:** Section bleibt schmal (eine Spalte). Kein neues Bild nötig in dieser Patch-Runde.
- **Nicht ändern:** Hintergrundfarbe (`paper-100`), Zentrierung.

### 6. Product Principles

- **Aktion:** **Reduce + Rewrite ein Item.**
- **Ziel:** 6 → 6 (Anzahl bleibt), aber „No broker execution" wird positiv.
- **Eyebrow:** `Product principles`
- **Headline (final, leicht entschärft):** `Architecture-level guardrails — not slogans.`
- **Karten (final):**

| Title | Body |
|---|---|
| `Local-first` | `Runs from local files and emits local CSV and Markdown artifacts.` *(unverändert)* |
| `Privacy-first` | `Raw portfolio inputs remain under user control and separate from processed outputs.` *(unverändert)* |
| `No cloud lock-in` | `Core workflow is portable files and code. No cloud account required.` *(unverändert)* |
| `Decisions, not orders` | `The system documents, ranks, and reports. It never executes orders or connects to a brokerage.` ← **ersetzt** „No broker execution / The system documents, ranks, and reports. It does not place orders." |
| `Evidence-only` | `Missing data stays visible. Values are never guessed or silently imputed.` ← **leicht geschärft** |
| `Reproducible by design` | `Every run records inputs, manifests, and generated artifacts for later review.` ← **leicht geschärft** (Title gekürzt von „Reproducible reports") |

- **UX-Hinweise:** Card-Layout (3 Spalten desktop) unverändert.
- **Nicht ändern:** Anzahl Karten, Layout, Eyebrow.

### 7. Monthly Workflow

- **Aktion:** **Keep + Augment.** Die 6 Schritte bleiben. Zyklus-Story wird durch eine kleine Zusatz-Komposition unterhalb der 6 Karten gestärkt (kein neuer Block-Heavy-Section).
- **Ziel:** Sichtbar machen, dass dies ein **wiederkehrender** Zyklus ist und ein **Archiv** entsteht.
- **Eyebrow:** `Monthly workflow`
- **Headline (final):** `Six stages. One monthly cadence. A growing archive.`
- **Lede (final, neu unter der Headline):** `Compound Income OS runs the same six stages every month — from broker export to decision journal — so that month 12 looks like month 1, eleven times audited.`
- **Karten (final, leichte Wording-Schärfungen):**

| # | Title | Body |
|---|---|---|
| 01 | `Broker export in` | `Normalize local position files into a snapshot artifact.` *(unverändert)* |
| 02 | `Data quality check` | `Gate holdings with explicit coverage and profile statuses.` *(unverändert)* |
| 03 | `Scoring & ranking` | `Compute rule-based candidate scores from available evidence.` *(unverändert)* |
| 04 | `Dividend impact` | `Show synthetic scenario contribution under declared assumptions.` *(unverändert)* |
| 05 | `Monthly decision report` | `Explain candidate status, blockers, and data gaps in Markdown.` *(unverändert)* |
| 06 | `Decision journal` | `Preserve the reasoning beside the run artifacts — month after month.` *(leicht ergänzt)* |

- **Augment (neu, kompakte Mini-Komposition unter den 6 Karten):**

> **Headline (klein, eyebrow-Größe):** `The archive that compounds.`
>
> **Body (eine Zeile, ruhig):** `Each monthly run leaves one decision report, one journal entry, and one snapshot. Twelve runs become an auditable year.`
>
> **Drei Mono-Tags (visuell wie kleine Code-Pillen):** `month_01/monthly_decision_report.md` `month_06/monthly_decision_report.md` `month_12/monthly_decision_report.md`

- **UX-Hinweise:** Diese Mini-Komposition ist kein zweites Section-Heavy-Layout, nur eine schmale Zusatzleiste am unteren Rand der bestehenden Workflow-Section. Dieselbe Background-Farbe (`paper-100`) wie die Workflow-Section.
- **Nicht ändern:** 6-Karten-Grid, Reihenfolge, Indices.

### 8. Core Features

- **Aktion:** **Reduce + Hierarchize.** 11 gleichwertige Karten → **3 Hauptmodule + 5 Sub-Features**.
- **Ziel:** Sofortige Lesbarkeit. Eine Marketing-Story statt einer `features.csv`.
- **Eyebrow:** `Core features`
- **Headline (final):** `One local pipeline. Three modules. Five evidence layers.`

**3 Hauptmodule (groß, gleiche Card-Optik wie bisher):**

| Title | Body |
|---|---|
| `Watchlist & Monthly Ranking` | `A cash-aware queue of candidates, ordered by transparent rule-based scores. Blockers, review states, and concentration limits stay visible.` |
| `Monthly Decision Report` | `One Markdown artifact per run. Explains the current candidate, the blockers, the data gaps, and the reasoning under your current rule set.` |
| `Decision Journal & Local Dashboard` | `A re-readable record of every monthly decision, alongside a local KPI dashboard that consolidates processed artifacts.` |

**5 Sub-Features (kompakter, kleinere Pillen oder Mini-Cards unterhalb):**

| Title | One-liner |
|---|---|
| `Portfolio Snapshot` | `Local position snapshot with allocation and concentration context.` |
| `SEC Evidence Pipeline` | `Read-only SEC CompanyFacts path for reviewed eligible US stock identities.` |
| `Evidence-Applied Fundamentals` | `A separate evidence-applied master that preserves traceability.` |
| `Data Quality Gates` | `Status labels (COVERED, PARTIAL, REVIEW, MISSING_DATA) as first-class outputs.` |
| `Dividend Snowball Scenarios` | `Reproducible income scenarios under declared assumptions. Not a forecast.` |

- **Replacements:** Aktuelle 11-Item-Liste in `coreFeatures` wird durch obige zwei Listen ersetzt: ein Array `coreFeaturesPrimary` (3 Items) und ein Array `coreFeaturesSecondary` (5 Items). Render-Logik in `App.jsx` zeigt zuerst die 3 Hauptmodule (3-Spalten-Grid), darunter die 5 Sub-Features als kompakteres Grid (5 Spalten desktop, 2–3 mobile).
- **Aus dem alten Feature-Set entfernt/aufgegangen:** „Monthly Ranking" geht in `Watchlist & Monthly Ranking` auf. „Local Dashboard" geht in `Decision Journal & Local Dashboard` auf. „Valuation Bands" wird nicht eigens als Karte geführt — bleibt im Dashboard sichtbar als KPI und in der SEC/Quality-Section adressiert.
- **Nicht ändern:** Card-Styling, Section-Position in der Reihenfolge.

### 9. Dividend Snowball

- **Aktion:** **Rewrite copy.** Layout bleibt.
- **Ziel:** Emotionaler Anker („Snowball" ist der Investor-Sehnsuchtsbegriff), aber claim-safe (keine Returns, keine Forecasts).
- **Eyebrow:** `Dividend Snowball Analysis`
- **Headline (final):** `Your dividend snowball, modeled honestly.`
- **Lede (final):** `Run reproducible income scenarios from your own holdings, your own assumptions, and your own concentration caps. Every assumption is declared. Nothing is predicted.`
- **Disclaimer-Pill (final, unverändert in Funktion, leicht geschärft):** `Illustrative scenario · not a forecast`
- **KPI-Grid (final, klarer benannt):**

| Label | Demo Value |
|---|---|
| `Current Dividend Income TTM` | `€3,240` |
| `Candidate contribution` | `€42 illustrative annualized` |
| `Cash deployment assumption` | `€300 reviewed amount` |
| `Data quality` | `PARTIAL · review pending` |

- **UX-Hinweise:** Goldener Chart-Stroke unverändert lassen — er ist der einzige warme Farbakzent der Seite und passt thematisch.
- **Nicht ändern:** Chart, Pill-Konzept, Source-Tags.

### 10. SEC Evidence + Data Quality Gates

- **Aktion:** **Rewrite + Augment.** Engineer-Slang in Klartext-Investor-Sprache übersetzen, ohne die technische Genauigkeit zu verlieren.
- **Ziel:** Auch ein Investor ohne Coding-Hintergrund versteht in <60 Sekunden, was hier passiert und warum es Vertrauen aufbaut.

**Linke Karte — SEC Evidence Pipeline**
- **Eyebrow:** `SEC Evidence Pipeline`
- **Headline (final, unverändert):** `Read-only. Reviewed. Optional.`
- **Body (final, übersetzt):** `For eligible US stocks, the system can pull fundamentals from SEC CompanyFacts — read-only, after manual identity review. The fundamentals master is never silently overwritten. Updates are staged, reviewed, and only then applied.`
- **Stages-Liste (final, mit Klartext-Mini-Erklärung pro Zeile):**

| Stage | Visible state | Plain meaning |
|---|---|---|
| `Reviewed identity inputs` | `visible` | `You confirmed the ticker matches the SEC filer.` |
| `SEC CompanyFacts snapshot` | `visible` | `A read-only copy of the SEC's filed numbers.` |
| `Evidence registry` | `visible` | `An index of which fields came from where.` |
| `Research backlog` | `visible` | `Things flagged for human review.` |
| `Proposed updates` | `visible` | `Changes waiting for your approval.` |

- **Pill-Reihe (final, unverändert):** `Review update · Stage update · Apply to evidence-applied master`

**Rechte Karte — Data Quality Gates**
- **Eyebrow:** `Data Quality Gates`
- **Headline (final, unverändert):** `Missing data stays explicit.`
- **Body (final, leicht gekürzt):** `Status labels are first-class outputs, not hidden implementation details. They keep monthly decisions from pretending incomplete evidence is complete.`
- **Status-Pill-Liste (final, jede Pill bekommt einen Klartext-Untertitel als kleine Zeile darunter, monospace, ein Satz):**

| Status | Plain meaning |
|---|---|
| `COVERED` | `Required evidence is present and current.` |
| `PARTIAL` | `Some required fields are missing or stale.` |
| `REVIEW` | `Human decision pending before this can score.` |
| `NO_MATCH` | `Identity could not be linked to a filer.` |
| `MISSING_DATA` | `Field is not available; not silently filled.` |
| `INSUFFICIENT_INPUTS` | `Not enough fields to compute a meaningful score.` |
| `INSUFFICIENT_HISTORY` | `Not enough time series for this metric.` |

- **UX-Hinweise:** Klartext-Untertitel deutlich schwächer/mono-typografiert als die Pill selbst — Pill bleibt das Hauptelement, Klartext ist Lesehilfe.
- **Nicht ändern:** Card-Splitting (links/rechts), Pill-Farbgebung.

### 11. Decision Journal + Audience

- **Aktion:** **Keep + Rewrite Audience.** Code-Block bleibt.
- **Ziel:** Audience-Liste aus passiven Tags wird aktive Selbstidentifikation. Anti-Audience kommt dazu.

**Linke Karte — Decision Journal (unverändert in Funktion, Code-Block bleibt):**
- **Eyebrow:** `Decision Journal`
- **Headline (final, unverändert):** `The record beside the run.`
- **Code-Block (final, unverändert):** *bestehender Block beibehalten.*

**Rechte Karte — Audience (umgebaut):**
- **Eyebrow:** `Audience`
- **Headline (final):** `Built for independent operators.`
- **Items (final, je mit erklärendem Satz):**

| Audience | Why this fits them |
|---|---|
| `Dividend-growth investors` | `You care about a multi-year compounding thesis, not a quarterly trading idea.` |
| `Quality-compounder investors` | `You want evidence-led conviction on fewer, higher-quality positions.` |
| `Independent operators` | `You run your own research and want a deterministic, local workflow.` |

- **Anti-Audience-Block (neu, unter der Audience-Liste, optisch dezenter):**
> **Label:** `Not built for`
> **Body:** `Day traders, options speculators, leveraged or crypto-driven strategies, signal subscribers, anyone seeking execution, hot tips, or personalized investment advice.`

- **Replacements:** Aktuelle 4 Audience-Items werden durch obige 3 + Anti-Audience ersetzt. Aus den aktuellen Items entfällt `Engineers, analysts, and finance/data professionals` als eigene Zeile — das ist eine Querschnittsbeobachtung, kein Mandat. Die Architektur-Tugenden ziehen diese Gruppe ohnehin an, ohne sie als eigene Zielgruppe ausrufen zu müssen.
- **Nicht ändern:** Card-Splitting, Hintergrund (`paper-100`), Code-Block-Optik.

### 12. Access

- **Aktion:** **Reduce 4 → 3 + Rewrite.** Keine erfundenen Preise.
- **Ziel:** Klare Hierarchie: Self-Serve / Pro-Modules / Setup-Service. „GitHub Sponsors" wird ein Footer-Link, keine Karte.
- **Eyebrow:** `Access`
- **Headline (final):** `Open-source core. Optional help around the workflow.` *(unverändert.)*
- **Karten (final, 3 statt 4) — siehe Section H für die volle Tabelle.**

### 13. Final CTA

- **Aktion:** **Reduce + Rewrite.**
- **Ziel:** Genau ein Primary, ein Secondary als Textlink. „Setup Service" verschwindet aus dem Final-CTA-Block (lebt in der Access-Section).
- **Eyebrow:** `Final CTA`
- **Headline (final):** `One reproducible decision a month. Locally. With evidence.` *(neuer Satz, weil „Start with the workflow, not the trade." in den Hero gewandert ist.)*
- **Lede (final):** `Get the sample monthly report or review the local-first workflow.`
- **Buttons (final):** **Primary:** `See the sample monthly report` (gleiches Behavior wie Hero-Primary, siehe G). **Secondary (Textlink):** `View the workflow on GitHub` (extern wenn `VITE_GITHUB_URL` gesetzt, sonst Anchor zu `#workflow`).
- **Replacements:** Aktuelle drei Buttons (`Join Early Access`, `Request GitHub Access`, `Request Setup Service`) → durch obige zwei ersetzt. `Request Setup Service` lebt in der Access-Section weiter, nicht hier.
- **Nicht ändern:** Dunkles Panel, Hintergrundfarbe.

### 14. Footer

- **Aktion:** **Keep Disclaimer + Add honest links.**
- **Ziel:** Rechtliche Footer-Pflichtlinks ehrlich behandelt — ohne Fake-Imprint und Fake-Privacy.
- **Disclaimer (final, gekürzt — siehe Section F.15 für vollen Wortlaut):** Kürzere Version mit Akkordeon „Read full disclaimer".
- **Footer-Nav (final):**
  - `Imprint` → solange `VITE_IMPRINT_URL` nicht gesetzt: Link wird optisch dezent gerendert mit Tooltip `Pending — required before public launch`. **Kein Link auf eine Fake-Seite.**
  - `Privacy` → identisches Verhalten.
  - `GitHub` → linkt extern wenn gesetzt, sonst „Pending".
  - `GitHub Sponsors` → linkt extern wenn gesetzt, sonst „Pending".
- **Bottom-Line (final, unverändert):** `No cloud account required. Core runs locally. No broker connection.`
- **Nicht ändern:** Layout, Wordmark-Position.

---

## F. FINAL COPY BLOCKS (kopierbar)

### F.1 Header / Nav

```
Nav:
  Workflow
  Evidence
  Access
  GitHub

Header CTA Primary:        Get early access
Header CTA Secondary text: View on GitHub
Mobile short label:        Get access
```

### F.2 Hero

```
Eyebrow:      Start with the workflow, not the trade.
H1:           One defensible investment decision a month.
Subheadline:  Compound Income OS turns your broker exports, fundamentals, and SEC evidence into one reproducible monthly decision report — locally, with every data gap visible.
Primary CTA:  See the sample monthly report
Secondary:    View the workflow
Trust line:   Local-first · Open-source core · Evidence-based · No broker. No cloud.
Meta strip:   Mode: Local files | Outputs: CSV / Markdown | Cadence: Monthly
```

### F.3 Hero KPI Labels

```
synthetic demo values

Portfolio Value          €128,420         OK
Dividend Growth 5Y       7.8%             COVERED
Cash Weight              8.4%             OK
Monthly Candidate        REVIEW           REVIEW

Status legend:
OK = within rules · COVERED = evidence complete · REVIEW = pending decision · PARTIAL / MISSING_DATA = gaps stay visible (see Evidence)
```

### F.4 Problem Section

```
Eyebrow:   Problem
Headline:  Where long-term portfolios actually break.
Lede:      Research fragments over time. Watchlists drift. Reasons get lost. The monthly decision becomes an act of memory rather than evidence.

Card 01  The watchlist no one updated.
         Tickers added years ago, never reviewed since. The thesis is gone. The position is still in.

Card 02  The KPI that was missing.
         A score gets computed anyway. The decision rests on data that wasn't there. You don't notice until next quarter.

Card 03  The decision you can't reconstruct.
         "Why did I buy that?" The reasoning was in your head. It's no longer there. The position is.
```

### F.5 Solution Section

```
Eyebrow:   Solution
Headline:  The portfolio as local infrastructure.
Lede:      Compound Income OS treats the research workflow as a deterministic local pipeline: declared inputs in, reproducible artifacts out. Data quality, evidence status, and reasoning are first-class outputs at every step.
```

### F.6 Product Principles

```
Eyebrow:   Product principles
Headline:  Architecture-level guardrails — not slogans.

Local-first             Runs from local files and emits local CSV and Markdown artifacts.
Privacy-first           Raw portfolio inputs remain under user control and separate from processed outputs.
No cloud lock-in        Core workflow is portable files and code. No cloud account required.
Decisions, not orders   The system documents, ranks, and reports. It never executes orders or connects to a brokerage.
Evidence-only           Missing data stays visible. Values are never guessed or silently imputed.
Reproducible by design  Every run records inputs, manifests, and generated artifacts for later review.
```

### F.7 Monthly Workflow

```
Eyebrow:   Monthly workflow
Headline:  Six stages. One monthly cadence. A growing archive.
Lede:      Compound Income OS runs the same six stages every month — from broker export to decision journal — so that month 12 looks like month 1, eleven times audited.

01  Broker export in
    Normalize local position files into a snapshot artifact.
02  Data quality check
    Gate holdings with explicit coverage and profile statuses.
03  Scoring & ranking
    Compute rule-based candidate scores from available evidence.
04  Dividend impact
    Show synthetic scenario contribution under declared assumptions.
05  Monthly decision report
    Explain candidate status, blockers, and data gaps in Markdown.
06  Decision journal
    Preserve the reasoning beside the run artifacts — month after month.

Mini-augment block under the 6 cards:
  Eyebrow: The archive that compounds.
  Body:    Each monthly run leaves one decision report, one journal entry, and one snapshot. Twelve runs become an auditable year.
  Tags:    month_01/monthly_decision_report.md   month_06/monthly_decision_report.md   month_12/monthly_decision_report.md
```

### F.8 Core Feature Groups

```
Eyebrow:   Core features
Headline:  One local pipeline. Three modules. Five evidence layers.

Primary modules:
  Watchlist & Monthly Ranking
    A cash-aware queue of candidates, ordered by transparent rule-based scores. Blockers, review states, and concentration limits stay visible.
  Monthly Decision Report
    One Markdown artifact per run. Explains the current candidate, the blockers, the data gaps, and the reasoning under your current rule set.
  Decision Journal & Local Dashboard
    A re-readable record of every monthly decision, alongside a local KPI dashboard that consolidates processed artifacts.

Secondary layers (5 compact items):
  Portfolio Snapshot              Local position snapshot with allocation and concentration context.
  SEC Evidence Pipeline           Read-only SEC CompanyFacts path for reviewed eligible US stock identities.
  Evidence-Applied Fundamentals   A separate evidence-applied master that preserves traceability.
  Data Quality Gates              Status labels (COVERED, PARTIAL, REVIEW, MISSING_DATA) as first-class outputs.
  Dividend Snowball Scenarios     Reproducible income scenarios under declared assumptions. Not a forecast.
```

### F.9 Dividend Snowball

```
Eyebrow:   Dividend Snowball Analysis
Headline:  Your dividend snowball, modeled honestly.
Lede:      Run reproducible income scenarios from your own holdings, your own assumptions, and your own concentration caps. Every assumption is declared. Nothing is predicted.
Pill:      Illustrative scenario · not a forecast

KPI grid:
  Current Dividend Income TTM     €3,240
  Candidate contribution          €42 illustrative annualized
  Cash deployment assumption      €300 reviewed amount
  Data quality                    PARTIAL · review pending
```

### F.10 Evidence / Data Quality

```
Left card — SEC Evidence Pipeline
  Eyebrow:   SEC Evidence Pipeline
  Headline:  Read-only. Reviewed. Optional.
  Body:      For eligible US stocks, the system can pull fundamentals from SEC CompanyFacts — read-only, after manual identity review. The fundamentals master is never silently overwritten. Updates are staged, reviewed, and only then applied.

  Stages (each with plain meaning):
    Reviewed identity inputs       — You confirmed the ticker matches the SEC filer.
    SEC CompanyFacts snapshot      — A read-only copy of the SEC's filed numbers.
    Evidence registry              — An index of which fields came from where.
    Research backlog               — Things flagged for human review.
    Proposed updates               — Changes waiting for your approval.

  Action pills: Review update · Stage update · Apply to evidence-applied master

Right card — Data Quality Gates
  Eyebrow:   Data Quality Gates
  Headline:  Missing data stays explicit.
  Body:      Status labels are first-class outputs, not hidden implementation details. They keep monthly decisions from pretending incomplete evidence is complete.

  Status pills + plain meanings:
    COVERED               Required evidence is present and current.
    PARTIAL               Some required fields are missing or stale.
    REVIEW                Human decision pending before this can score.
    NO_MATCH              Identity could not be linked to a filer.
    MISSING_DATA          Field is not available; not silently filled.
    INSUFFICIENT_INPUTS   Not enough fields to compute a meaningful score.
    INSUFFICIENT_HISTORY  Not enough time series for this metric.
```

### F.11 Decision Journal

```
Eyebrow:   Decision Journal
Headline:  The record beside the run.

Code block (unchanged):
  run_id: DEMO-20260426-160500
  monthly_candidate: REVIEW
  candidate_allocation: €300 under current rule set
  review_amount: €300 within concentration limit
  blocker: valuation_data_status != OK
  artifact: reports/demo/monthly_decision_report.md
```

### F.12 Audience + Anti-Audience

```
Eyebrow:   Audience
Headline:  Built for independent operators.

  Dividend-growth investors      You care about a multi-year compounding thesis, not a quarterly trading idea.
  Quality-compounder investors   You want evidence-led conviction on fewer, higher-quality positions.
  Independent operators          You run your own research and want a deterministic, local workflow.

Not built for:
  Day traders, options speculators, leveraged or crypto-driven strategies, signal subscribers, anyone seeking execution, hot tips, or personalized investment advice.
```

### F.13 Access Cards

*(Volle Tabelle in Section H.)*

```
Eyebrow:   Access
Headline:  Open-source core. Optional help around the workflow.

Card 1  Open-Source Core           Free · Open-source
        Local pipeline for positions, fundamentals, watchlist ranking, monthly ranking, reports, and dashboard artifacts.
        CTA: View the workflow
Card 2  Pro Modules                Pricing TBD · Private preview
        Optional local extensions for deeper evidence review, scenario inspection, and additional dashboards.
        CTA: Request private preview
Card 3  Setup Service              Pricing on request · Private preview
        Guided setup, local environment preparation, input mapping, and first reproducible run support.
        CTA: Request setup
```

### F.14 Final CTA

```
Eyebrow:   Final CTA
Headline:  One reproducible decision a month. Locally. With evidence.
Lede:      Get the sample monthly report or review the local-first workflow.

Primary CTA:    See the sample monthly report
Secondary link: View the workflow on GitHub
```

### F.15 Footer Disclaimer (Short Version)

```
Short (visible by default):
  Compound Income OS is a research and decision-support tool. It is not investment, tax, or legal advice, never connects to a brokerage, and never executes orders. All values shown on this page are synthetic demo values.

Expandable: Read full disclaimer →
  (full text = current siteConfig.disclaimer, unchanged)

Bottom line:
  No cloud account required. Core runs locally. No broker connection.

Footer nav:
  Imprint   ← rendered with "Pending" tooltip when VITE_IMPRINT_URL is unset; no fake link.
  Privacy   ← rendered with "Pending" tooltip when VITE_PRIVACY_URL is unset; no fake link.
  GitHub
  GitHub Sponsors
```

### F.16 Public Launch Blocker Note (rendered as a small dev-only banner — see Section I)

```
This build is a private preview. Imprint, privacy policy, real CTA targets, and pricing are pending. No public deploy has been performed. Synthetic demo values only.
```

---

## G. CTA + FUNNEL SPEC

### G.1 Primärer Funnel

`Hero Primary → See the sample monthly report`

- **If `VITE_SAMPLE_REPORT_URL` is set:** linkt extern auf die hinterlegte URL (z. B. eine signierte MD-/PDF-Sample-Datei oder eine Notion-/Tally-Page mit E-Mail-Capture vor dem Sample).
- **If unset (default state, current build):** Klick scrollt zu `#access` und dort wird in der Access-Section ein zusätzlicher kleiner Status-Pill `Sample available on request — pending` sichtbar gemacht. **Kein Mailto. Kein Fake-Form.**

### G.2 Sekundärer Funnel

`Hero Secondary → View the workflow`

- **Always:** Anchor-Link zu `#workflow`. Funktioniert ohne externe URL.
- Final-CTA-Secondary `View the workflow on GitHub` linkt extern auf `VITE_GITHUB_URL` wenn gesetzt; wenn unset, fällt sie auf den `#workflow`-Anchor zurück und der Linktext ändert sich auf `View the workflow` (ohne „on GitHub").

### G.3 Mikro-Conversion (solange kein echtes Ziel existiert)

In dieser Patch-Runde wird **bewusst kein Fake-Formular** und **keine Fake-Warteliste** eingebaut. Die Mikro-Conversion ist `See the sample monthly report` mit `#access`-Anchor-Fallback. Sobald eine echte Sample-/Listen-URL existiert, wird sie als ENV-Variable `VITE_SAMPLE_REPORT_URL` hinterlegt und der CTA wechselt automatisch in den produktiven Modus.

### G.4 Verhalten für Placeholder-Zustand (private build)

| CTA target unset | Sichtbares Verhalten |
|---|---|
| `VITE_SAMPLE_REPORT_URL` unset | Hero/Final Primary: scrollt zu `#access`, dort Pill „Sample available on request — pending" sichtbar. |
| `VITE_GITHUB_URL` unset | Header und Final-CTA-Secondary: Linktext zeigt nicht „on GitHub", `aria-disabled="true"`-Variante mit Tooltip `Repository link pending`. |
| `VITE_PRIVACY_URL` / `VITE_IMPRINT_URL` unset | Footer-Links rendern als gedimmter Text mit Tooltip `Pending — required before public launch`. **Nicht klickbar.** |
| `VITE_EARLY_ACCESS_URL` / `VITE_SETUP_SERVICE_URL` unset | Access-Karten-CTAs `Request private preview` / `Request setup` rendern mit Pill `Private preview · request pending`. Keine Mailto-Platzhalterdomain mehr. |

### G.5 Verhalten für private Demo

Vor jeder privaten Demo-Weitergabe wird in `.env.local` (nicht commited) konfiguriert:

```
VITE_SAMPLE_REPORT_URL=https://...   # echtes Sample-Ziel oder Notion-Page
VITE_GITHUB_URL=https://github.com/...
```

Bleibt etwas leer → die Seite ist **ehrlich** im Placeholder-Zustand (siehe G.4) statt zu lügen.

### G.6 Verhalten für Public Launch (später, dieser Patch ändert das nicht)

Public Launch ist in dieser Patch-Runde **nicht im Scope**. Die in Section I dokumentierten Public-Launch-Blocker müssen vorher real geklärt sein:
- echte Imprint- + Privacy-URLs gesetzt,
- echte Pricing-Werte für Pro Modules und Setup Service,
- echte Early-Access-URL oder Form-Provider (Notion, Tally, EmailOctopus),
- Domain-/DNS-Setup,
- Deploy-Pipeline.

### G.7 Welche CTAs sichtbar bleiben

- Header: 1× Primary (`Get early access`), 1× Secondary-Textlink (`View on GitHub`).
- Hero: 1× Primary (`See the sample monthly report`), 1× Secondary (`View the workflow`).
- Access-Section: 3× Karten-CTA (siehe H).
- Final-CTA-Block: 1× Primary (`See the sample monthly report`), 1× Secondary-Textlink (`View the workflow on GitHub`).

### G.8 Welche CTAs entfernt oder herabgestuft werden

- `Request GitHub Access` als Header-Button → herabgestuft zu Textlink `View on GitHub`.
- `Join Early Access` als Wording-Wiederholung 5×+ → vereinheitlicht auf zwei Wordings: `Get early access` (Header) + `See the sample monthly report` (Hero/Final).
- `Request Setup Service` aus dem Final-CTA-Block → entfernt; lebt nur noch in der Access-Section.
- `GitHub Sponsors / Early Access` als eigene Access-Karte → entfernt; lebt nur noch als Footer-Link.
- Alle `mailto:early-access@example.invalid`-Defaults → **entfernt**. Wenn ENV-URL fehlt, fällt das CTA-Verhalten auf die ehrlichen Pending-Zustände zurück (siehe G.4), nicht auf eine Platzhalter-Mailadresse.

---

## H. ACCESS SECTION SPEC

**Entscheidung:** 3 Karten statt 4. Vierte Karte `GitHub Sponsors / Early Access` entfällt — wandert als Footer-Link.

| # | Title | Audience | Copy | CTA Label | CTA Target / Behavior | Status / Pricing Text | Notes |
|---|---|---|---|---|---|---|---|
| 1 | `Open-Source Core` | Independent operators who want to run the workflow themselves | `Local pipeline for positions, fundamentals, watchlist ranking, monthly ranking, reports, and dashboard artifacts.` | `View the workflow` | If `VITE_GITHUB_URL` is set → external link. Else → anchor to `#workflow`. | `Free · Open-source` | Self-serve. No private-preview gate. |
| 2 | `Pro Modules` | Investors who want deeper evidence review and additional dashboards | `Optional local extensions for deeper evidence review, scenario inspection, and additional dashboards.` | `Request private preview` | If `VITE_EARLY_ACCESS_URL` is set → external link. Else → render as button with `aria-disabled="true"` and a small inline pill `Private preview · request pending`. **No mailto fallback.** | `Pricing TBD · Private preview` | Pricing wird **nicht** erfunden. |
| 3 | `Setup Service` | Investors who want guided implementation | `Guided setup, local environment preparation, input mapping, and first reproducible run support.` | `Request setup` | If `VITE_SETUP_SERVICE_URL` is set → external link. Else → identisches Pending-Verhalten wie Karte 2. | `Pricing on request · Private preview` | Skopus bewusst nicht in Stunden/Paketpreisen festgelegt. |

**Begründung 4. Karte entfernt:** `GitHub Sponsors / Early Access` doppelte sich funktional mit Karte 1 (Repo-Pfad) und Karte 2 (Early Access). Der GitHub-Sponsors-Pfad bleibt als sekundärer Footer-Link erhalten.

---

## I. PUBLIC LAUNCH BLOCKERS

Beide Versionen sind so formuliert, dass sie 1:1 in die jeweiligen Dateien kopierbar sind.

### I.1 Kurze README-Version (für `website/compound-income-os-landing/README.md`, neuer Abschnitt am Ende)

```markdown
## Public Launch Blockers

This build is a private preview. The following items must be real and verified before any public deploy:

- Imprint page (legal requirement in DE/EU); `VITE_IMPRINT_URL` must be set.
- Privacy policy page; `VITE_PRIVACY_URL` must be set.
- Real CTA targets: `VITE_SAMPLE_REPORT_URL`, `VITE_EARLY_ACCESS_URL`, `VITE_SETUP_SERVICE_URL`, `VITE_GITHUB_URL`.
- Real pricing or scope for Pro Modules and Setup Service.
- No public deploy has been performed.
- All KPI and chart values shown are synthetic demo values.
- The product is not investment, tax, or legal advice.
```

### I.2 Ausführliche Deployment-Notes-Version (neue Datei `website/compound-income-os-landing/DEPLOYMENT_NOTES.md`)

```markdown
# Deployment Notes — Compound Income OS Landing Page

This page is currently a **private preview build**. It is intended for internal review and limited demo handoffs only. It is **not** ready for public deployment.

## Public Launch Blockers

The following items are required before any public deploy. Each blocker has both a legal/compliance and a credibility dimension.

### 1. Imprint
- Legal requirement in DE/EU.
- Configure `VITE_IMPRINT_URL` in environment.
- Until set, the footer renders the "Imprint" link as a non-clickable, dimmed label with a "Pending — required before public launch" tooltip.

### 2. Privacy policy
- Required by GDPR and equivalent regimes.
- Configure `VITE_PRIVACY_URL` in environment.
- Until set, the footer renders the "Privacy" link with the same dimmed pending state.

### 3. Real CTA targets
- `VITE_SAMPLE_REPORT_URL` — destination for "See the sample monthly report".
- `VITE_EARLY_ACCESS_URL` — destination for "Request private preview" on the Pro Modules card.
- `VITE_SETUP_SERVICE_URL` — destination for "Request setup" on the Setup Service card.
- `VITE_GITHUB_URL` — repository link for header, secondary final CTA, and Open-Source Core card.
- The current build **never** falls back to `mailto:early-access@example.invalid` or any other placeholder address. Unset URLs render as honest pending states.

### 4. Pricing and scope
- Pro Modules: pricing currently rendered as `Pricing TBD · Private preview`. Replace with real pricing or a real preview-list URL before any public sales surface.
- Setup Service: pricing currently rendered as `Pricing on request · Private preview`. Define scope (hours, deliverables, response times) before any public sales surface.

### 5. No public deploy performed
- No CI/CD pipeline targeting a public domain is currently configured.
- No DNS records have been pointed at this build.

### 6. Synthetic demo values only
- Every KPI, chart line, and dashboard number on the page is synthetic and explicitly labeled `synthetic demo values`.
- No real portfolio, broker, or fundamentals data is rendered.

### 7. Not investment, tax, or legal advice
- The product is a research and decision-support system. It does not connect to brokerages, does not execute orders, and does not provide personalized recommendations.
- The footer disclaimer must remain visible on any public version.

## Allowed deployment surfaces (current build)

- Local development server (Vite dev / preview).
- Private review handoffs (ZIP, password-protected static preview, internal Vercel preview, or equivalent).
- Internal stakeholder demos with explicit "private preview" framing.

## Disallowed deployment surfaces (current build)

- Public domain.
- Public marketing channels.
- Any surface where the page could be indexed by search engines or shared as a launched product.
```

---

## J. CODEX IMPLEMENTATION BRIEF

*(Keine Codex-Prompts. Keine Shell-Kommandos. Nur die Patch-Spezifikation.)*

### J.1 Ziel

Minimal-invasiver Patch der bestehenden Landingpage gemäß den Sections C–I dieses Dokuments, ohne Erweiterung der Komponentenarchitektur. Keine neuen NPM-Abhängigkeiten. Kein neuer State-Management-Layer. Kein Routing.

### J.2 Scope

In Scope:
- Copy-Replacements in `App.jsx`.
- Daten-Replacements in `App.jsx` (KPI-Arrays, `principles`, `coreFeatures`-Aufteilung, `accessCards`, `workflowSteps`).
- Erweiterung von `siteConfig.js` um (a) Sample-Report-URL und (b) eine ENV-aware CTA-Helper-Funktion oder ein erweiterten `ctas`-Objekt mit Pending-Flags.
- Footer-Link-Rendering: Pending-Zustand für unset URLs.
- README-Ergänzung um „Public Launch Blockers"-Abschnitt.
- Optional neu: `DEPLOYMENT_NOTES.md`.

Nicht in Scope (siehe J.4).

### J.3 Betroffene Dateien

| Datei | Änderungstyp |
|---|---|
| `website/compound-income-os-landing/src/App.jsx` | Copy + Daten-Replacements; Render-Logik für Pending-CTAs in Footer und Access-Karten; neue Mini-Komposition unter Workflow-Section. |
| `website/compound-income-os-landing/src/siteConfig.js` | Neue Felder: `ctas.sampleReport`; Pending-Flags je CTA; angepasste Defaults (kein Mailto-Fallback mehr); ggf. `productCadence`. |
| `website/compound-income-os-landing/.env.example` | Eintrag `VITE_SAMPLE_REPORT_URL=` ergänzen. |
| `website/compound-income-os-landing/README.md` | Neuer Abschnitt „Public Launch Blockers" am Ende (siehe I.1). |
| `website/compound-income-os-landing/DEPLOYMENT_NOTES.md` *(neu)* | Inhalt aus Section I.2. |

### J.4 Nicht-Ziele

- Keine neuen Sections (außer der Mini-Komposition unter dem Workflow, die zur bestehenden Section gehört).
- Keine neuen Komponenten-Dateien.
- Keine Routing-Änderungen.
- Keine Backend-Anbindung.
- Keine echten Formularfelder.
- Keine neuen Bilder, keine Stockfotos.
- Keine Internationalisierung.
- Keine Animation-Bibliotheken.
- Keine A/B-Test-Infrastruktur.
- Keine Analytics-Integration.

### J.5 Reihenfolge der Änderungen (empfohlen)

1. **`siteConfig.js`** — neue Struktur, ENV-Defaults (kein Mailto mehr).
2. **`App.jsx` Hero + Header** — Copy-Replacements und neue CTA-Helper-Aufrufe.
3. **`App.jsx` Hero-Dashboard + Full-Dashboard-Preview** — KPI-Arrays anpassen, Status-Legende ergänzen.
4. **`App.jsx` Problem + Solution** — Copy-Replacements.
5. **`App.jsx` Principles** — Karte „No broker execution" → „Decisions, not orders".
6. **`App.jsx` Workflow** — Lede ergänzen, Mini-Augment-Block unter den 6 Karten.
7. **`App.jsx` Core Features** — Aufteilung in 3 Hauptmodule + 5 Sub-Features.
8. **`App.jsx` Snowball + Evidence/Quality** — Copy-Replacements, Klartext-Untertitel pro Status-Pill.
9. **`App.jsx` Decision Journal + Audience** — Audience-Items mit Sätzen + Anti-Audience-Block.
10. **`App.jsx` Access** — 4 Karten → 3 Karten.
11. **`App.jsx` Final CTA + Footer** — neue Headline, Pending-Footer-Links, Disclaimer-Akkordeon.
12. **`README.md`** — neuer Abschnitt.
13. **`DEPLOYMENT_NOTES.md`** — neue Datei.

### J.6 Copy-Replacement-Mapping (Auszug — vollständige Texte siehe F)

| Stelle in `App.jsx` (sinngemäß) | Alt | Neu |
|---|---|---|
| `siteConfig.tagline` | `A local operating system for long-term investing.` | wird im Hero nicht mehr direkt als H1 verwendet; bleibt als textuelle Tagline in Config, aber **Hero rendert die neue H1 als statischen String**, nicht aus `tagline`. *(Alternativ: `tagline` auf neuen H1-Wert umstellen — siehe J.7.)* |
| Hero Eyebrow `Local-first portfolio research` | s. links | `Start with the workflow, not the trade.` |
| Hero H1 `{siteConfig.tagline}` | s. links | `One defensible investment decision a month.` |
| Hero Subheadline (ganzer Text) | aktueller `Compound Income OS turns your broker exports …` | siehe F.2 (neue Subline) |
| Hero Microcopy `Open-source core. No cloud account required. Not investment advice.` | s. links | `Local-first · Open-source core · Evidence-based · No broker. No cloud.` |
| Hero Meta-Strip 3. Item `['Broker', 'No connection']` | s. links | `['Cadence', 'Monthly']` |
| Section `id="problem"` Headline | `Where long-term portfolios actually fail.` | `Where long-term portfolios actually break.` |
| Problem-Karten (3 Items) | aktuelle `Data drift / Evidence gaps / Process loss` | siehe F.4 |
| Section `id="product"` (Principles) Headline | `Architecture-level guardrails, not marketing slogans.` | `Architecture-level guardrails — not slogans.` |
| Principles-Item 4 | `['No broker execution', 'The system documents, ranks, and reports. It does not place orders.']` | `['Decisions, not orders', 'The system documents, ranks, and reports. It never executes orders or connects to a brokerage.']` |
| Principles-Item 5 (`Evidence-only`) | aktueller Body | `Missing data stays visible. Values are never guessed or silently imputed.` |
| Principles-Item 6 | `['Reproducible reports', 'Runs record inputs, manifests, and generated artifacts for later review.']` | `['Reproducible by design', 'Every run records inputs, manifests, and generated artifacts for later review.']` |
| Section `id="workflow"` Headline | `Six stages from input files to decision journal.` | `Six stages. One monthly cadence. A growing archive.` |
| Workflow-Lede | (existiert bisher nicht direkt unter der Headline) | siehe F.7 |
| Workflow-Mini-Augment-Block (neu unter den 6 Karten) | — | siehe F.7 |
| Section Core Features Headline | `One local pipeline. Eleven ways to inspect the evidence.` | `One local pipeline. Three modules. Five evidence layers.` |
| `coreFeatures` (11 Items) | s. links | wird aufgeteilt in `coreFeaturesPrimary` (3) und `coreFeaturesSecondary` (5) gemäß F.8 |
| Snowball Headline | `A scenario surface for income assumptions.` | `Your dividend snowball, modeled honestly.` |
| Snowball Lede | aktueller Text | siehe F.9 |
| SEC Pipeline Body | aktueller Text | siehe F.10 (linke Karte) |
| SEC Pipeline Stages-Liste | aktuell `['reviewed identity inputs', …]` als reine Strings | erweitern zu Tupeln `[label, plain meaning]` (siehe F.10) |
| Data Quality Gates Body | aktueller Text | siehe F.10 (rechte Karte) |
| `statusLabels` (Array of 7 strings) | s. links | erweitern zu Tupeln `[status, plain meaning]` |
| Audience-Liste (4 Items) | s. links | siehe F.12 (3 Items mit Sätzen + Anti-Audience-Block) |
| `accessCards` (4 Items) | s. links | siehe H (3 Karten) |
| Final-CTA Headline | `Start with the workflow, not the trade.` | `One reproducible decision a month. Locally. With evidence.` *(weil der alte Satz in den Hero-Eyebrow gewandert ist)* |
| Final-CTA Buttons (3 Stück) | s. links | 1× Primary `See the sample monthly report` + 1× Secondary-Textlink (siehe F.14) |
| Footer Bottom-Line | `No cloud account required. Core runs locally. No broker connection.` | unverändert |
| Footer Disclaimer | aktueller Volltext | Short-Version sichtbar, Volltext im Akkordeon (siehe F.15) |

### J.7 Config-Replacement-Mapping (`siteConfig.js`)

```
PRINZIPIELLE STRUKTUR (final):

productName: 'Compound Income OS'
tagline:     'One defensible investment decision a month.'   // wird Hero-H1
positioning: 'Local · Evidence-based · Monthly'              // optional, kann an mehreren Stellen genutzt werden

ctas:
  sampleReport:    { label: 'See the sample monthly report', href: env.VITE_SAMPLE_REPORT_URL || null, fallbackAnchor: '#access', pendingPill: 'Sample available on request — pending' }
  earlyAccess:     { label: 'Request private preview',       href: env.VITE_EARLY_ACCESS_URL    || null, pendingPill: 'Private preview · request pending' }
  setupService:    { label: 'Request setup',                 href: env.VITE_SETUP_SERVICE_URL   || null, pendingPill: 'Private preview · request pending' }
  githubAccess:    { label: 'View on GitHub',                href: env.VITE_GITHUB_URL          || null, pendingTooltip: 'Repository link pending' }
  workflowAnchor:  { label: 'View the workflow',             href: '#workflow' }   // immer aktiv
  headerPrimary:   { label: 'Get early access',              href: env.VITE_EARLY_ACCESS_URL    || null, fallbackAnchor: '#access', pendingPill: 'Private preview · request pending' }

links:
  github:    env.VITE_GITHUB_URL    || null
  sponsors:  env.VITE_SPONSORS_URL  || null
  privacy:   env.VITE_PRIVACY_URL   || null
  imprint:   env.VITE_IMPRINT_URL   || null

disclaimer (full):  unchanged
disclaimerShort:    'Compound Income OS is a research and decision-support tool. It is not investment, tax, or legal advice, never connects to a brokerage, and never executes orders. All values shown on this page are synthetic demo values.'
```

**Wichtige Regel:** Defaults sind **nicht mehr** `mailto:early-access@example.invalid?...`. Defaults sind `null`. Render-Logik in `App.jsx` muss `null` als „pending" interpretieren und entsprechend rendern (siehe G.4).

### J.8 Demo-KPI-Mapping (`App.jsx`)

```
Hero compact dashboard (4 KPIs):
  ['Portfolio Value',       '€128,420',   'ok',      'OK']
  ['Dividend Growth 5Y',    '7.8%',       'ok',      'COVERED']
  ['Cash Weight',           '8.4%',       'ok',      'OK']
  ['Monthly Candidate',     'REVIEW',     'review',  'REVIEW']

Full dashboard (10 KPIs):
  ['Portfolio Value',       '€128,420',   'Synthetic demo value',           'ok',      'OK']
  ['Cash Weight',           '8.4%',       'Reserve inside rule band',       'ok',      'OK']
  ['Positions',             '24',         'Within target range',            'ok',      'OK']
  ['Top 5 Weight',          '38.7%',      'Within concentration cap',       'ok',      'OK']
  ['Dividend Income TTM',   '€3,240',     'Synthetic demo value',           'ok',      'COVERED']
  ['Dividend Growth 5Y',    '7.8%',       'Synthetic demo value',           'ok',      'COVERED']
  ['Data Quality',          'PARTIAL',    'Review needed',                  'partial', 'PARTIAL']
  ['Monthly Candidate',     'REVIEW',     'Review required',                'review',  'REVIEW']
  ['Valuation Band',        'Fair / Watch','Valuation review',              'review',  'REVIEW']
  ['Review Flags',          '2',          'Open artifacts',                 'review',  'REVIEW']

Subtle chart area subtitle (full dashboard):
  'Illustrative scenario · synthetic demo data'
```

### J.9 README / Notes-Ergänzungen

- `website/compound-income-os-landing/README.md`: neuer Abschnitt am Ende, Wortlaut siehe **I.1**.
- `website/compound-income-os-landing/DEPLOYMENT_NOTES.md`: neue Datei, Wortlaut siehe **I.2**.
- `website/compound-income-os-landing/.env.example`: Zeile `VITE_SAMPLE_REPORT_URL=` ergänzen.

### J.10 Risiken

| Risiko | Beschreibung | Mitigation |
|---|---|---|
| **Status-Pill-Mismatch** | Status-Pill-Klassen (`pill-ok`, `pill-partial`, `pill-review`, `pill-missing`) sind mit den neuen Werten konsistent zu halten — `COVERED` wird visuell auf `pill-ok` gemappt. | Mapping in `App.jsx` explizit dokumentieren, kein neuer Pill-Type nötig. |
| **Anchor-Fallback funktioniert nicht** | Wenn `#access` oder `#workflow` umbenannt würden, brechen Hero-CTAs. | Section-IDs unverändert lassen. |
| **Klartext-Untertitel sprengen Layout** | Status-Pill-Reihen mit zusätzlicher Mini-Erklärungszeile könnten Mobile-Layout brechen. | Erklärungstext als kleine Zeile **unter** der Pill, nicht inline; in Mobile als 1-Spalten-Liste rendern. |
| **Pending-CTA-State wirkt „kaputt"** | Wenn der Visitor einen `aria-disabled` Button sieht, könnte das wie ein Bug aussehen. | Begleitende Pill `Private preview · request pending` direkt am Button, sodass es offensichtlich Absicht ist. |
| **Disclaimer-Akkordeon-Pattern** | Footer-Disclaimer im Accordion könnte für Compliance heikel sein, falls die Short-Version weniger sagt als die Long-Version. | Short-Version muss alle juristisch relevanten Aussagen (no advice, no broker, synthetic) enthalten — was sie tut. Long-Version bleibt verfügbar via expand. |
| **README-Konsistenz** | `README.md` referenziert sonst keine ENV-Variablen mit `VITE_SAMPLE_REPORT_URL`. | In `.env.example` ergänzen, im README-Public-Launch-Abschnitt benennen. |

### J.11 Rollback-Hinweise

- Alle Änderungen liegen in 5 Dateien (siehe J.3). Ein `git revert` der einzelnen Commit-Logik je Section (siehe J.5) genügt.
- Es werden **keine** bestehenden Funktionen, Routen oder Komponenten entfernt — nur Inhalt und einzelne Daten-Arrays geändert.
- Section-IDs (`#top`, `#product`, `#workflow`, `#evidence`, `#access`, `#early-access`) bleiben unverändert, sodass externe Links nicht brechen.
- Keine Datenbank, kein Backend, kein Migrationsschritt nötig.

---

## K. ACCEPTANCE CRITERIA

**Hero & Outcome**
- AC-1. Hero-H1 lautet `One defensible investment decision a month.` — outcome-orientiert, kein Kategorie-Label.
- AC-2. Hero-Eyebrow lautet `Start with the workflow, not the trade.`.
- AC-3. Hero-Subheadline enthält `monthly decision report`, `locally`, `every data gap visible` als sinnverwandte Wörter (Reihenfolge frei).
- AC-4. Hero zeigt **maximal einen** KPI mit Status `REVIEW`, `PARTIAL` oder `MISSING_DATA`. Alle übrigen Hero-KPIs haben Status `OK` oder `COVERED`.

**CTA & Funnel**
- AC-5. Kein sichtbares Hyperlink-Ziel der gerenderten Seite enthält `example.invalid` oder eine `mailto:`-URL.
- AC-6. Wenn `VITE_SAMPLE_REPORT_URL` unset ist, scrollt der Hero-Primary-Button zu `#access` und rendert dort einen sichtbaren Pending-Pill.
- AC-7. Wenn `VITE_GITHUB_URL` unset ist, rendert der Header-Secondary-Link mit `aria-disabled="true"` und einem „Repository link pending"-Tooltip — er führt nicht zu einer Mailto- oder Platzhalterseite.
- AC-8. Im gesamten Render-Output erscheint genau ein Wording-Cluster für „Get / Request" pro Funktion: `Get early access` (Header), `See the sample monthly report` (Hero/Final-Primary), `Request private preview` (Pro Modules Karte), `Request setup` (Setup Service Karte). Keine doppelten Wordings.

**Access**
- AC-9. Die Access-Section enthält genau 3 Karten.
- AC-10. Keine Access-Karte zeigt einen erfundenen Zahlenpreis. Erlaubte Werte: `Free · Open-source`, `Pricing TBD · Private preview`, `Pricing on request · Private preview`.

**Public-Launch-Blocker**
- AC-11. `README.md` enthält einen Abschnitt mit Überschrift `Public Launch Blockers`.
- AC-12. `DEPLOYMENT_NOTES.md` existiert und enthält die in I.2 spezifizierten Pflicht-Items.
- AC-13. Footer-Links `Imprint` und `Privacy` zeigen entweder auf real konfigurierte URLs (über ENV) oder rendern als visuell gedimmte, nicht klickbare Labels mit Pending-Tooltip — niemals als Fake-Link.

**Claims & Compliance**
- AC-14. Auf der gesamten Seite erscheint kein Claim, der Investmenterträge, Performance, Out-/Underperformance, Sicherheit oder personalisierte Empfehlungen verspricht.
- AC-15. Auf der gesamten Seite erscheint mindestens einmal sichtbar `synthetic demo values` (Hero-Dashboard) und einmal die Kernaussage, dass das Produkt nicht Investment-/Steuer-/Rechtsberatung ist (Footer-Disclaimer Short oder Long).
- AC-16. Status-Sprache (`COVERED`, `PARTIAL`, `REVIEW`, `MISSING_DATA`, `INSUFFICIENT_INPUTS`, `INSUFFICIENT_HISTORY`, `NO_MATCH`) bleibt erhalten und ist um Klartext-Untertitel ergänzt.

**Markenkonsistenz**
- AC-17. Anti-Trading-/Anti-Broker-/Anti-Cloud-Aussagen erscheinen mindestens einmal sichtbar (Trust-Statement im Hero) und sind nicht entfernt worden.
- AC-18. Die 6 Architektur-Prinzipien sind weiterhin sichtbar; das vierte Prinzip ist umformuliert auf `Decisions, not orders`.
- AC-19. Decision-Journal-Code-Block bleibt im Layout sichtbar.
- AC-20. Goldener Chart-Stroke in der Snowball-Section bleibt visuell erhalten.

---

## L. VALIDATION CHECKLIST

### L.1 Visual QA
- [ ] Hero-Layout (Text links, Dashboard-Panel rechts) ist auf Desktop-Breakpoint ≥1024px stabil.
- [ ] Hero auf Mobile: H1 atmet (mind. 3 Zeilen), Buttons stapeln korrekt, Demo-Panel beginnt knapp unter dem Fold.
- [ ] Status-Legende unter dem großen Dashboard-Panel ist auf Mobile lesbar (kein Overflow).
- [ ] Mini-Augment-Block unter dem Workflow ist optisch klar als Footer der Workflow-Section erkennbar, nicht als neue Section.
- [ ] Anti-Audience-Block ist visuell dezenter als die Audience-Liste.
- [ ] Klartext-Untertitel pro Status-Pill brechen das Pill-Grid auf Mobile nicht.
- [ ] Pending-CTAs sind als nicht-aktiv erkennbar (kein gleicher Hover-State wie aktive CTAs).

### L.2 Copy QA
- [ ] Hero-Eyebrow, H1, Subline, Trust Statement entsprechen exakt den Strings in F.2.
- [ ] Keine doppelten Disclaimer-Aussagen im Hero (max. 1× „No broker", max. 0× „Not investment advice" im Hero — letzteres lebt in Footer).
- [ ] Problem-Karten enthalten die neuen User-Side-Texte.
- [ ] Principles enthalten `Decisions, not orders` statt `No broker execution`.
- [ ] Workflow-Headline beginnt mit `Six stages.`.
- [ ] Core-Features-Headline lautet `One local pipeline. Three modules. Five evidence layers.`.
- [ ] Snowball-Headline lautet `Your dividend snowball, modeled honestly.`.
- [ ] Audience-Items haben jeweils einen erklärenden Satz.
- [ ] Anti-Audience-Block ist sichtbar.
- [ ] Final-CTA-Headline ist `One reproducible decision a month. Locally. With evidence.`.

### L.3 Funnel QA
- [ ] Hero-Primary-Button verhält sich gemäß G.4 (extern wenn URL gesetzt, sonst Anchor + Pending-Pill).
- [ ] Hero-Secondary-Button scrollt zu `#workflow`.
- [ ] Header-Primary-Button verhält sich gemäß G.4.
- [ ] Header-Secondary-Textlink hat Pending-Tooltip wenn `VITE_GITHUB_URL` unset.
- [ ] Final-CTA-Block enthält genau 2 sichtbare CTAs (Primary + Secondary).
- [ ] Access-Karte 1 CTA ist `View the workflow` (immer aktiv).
- [ ] Access-Karten 2+3 CTAs sind im Pending-Zustand wenn ENV nicht gesetzt; **kein** Mailto-Fallback.

### L.4 Legal/Compliance QA
- [ ] Footer-Disclaimer (Short oder Long) enthält wörtlich oder sinngemäß: „not investment, tax, or legal advice", „does not execute orders or connect to brokerages", „synthetic demo values".
- [ ] Imprint- und Privacy-Footer-Links sind im Pending-Zustand nicht klickbar und nicht als reguläre Links gestylt.
- [ ] Auf der gesamten Seite erscheint kein Performance-/Return-Claim.
- [ ] Auf der gesamten Seite erscheint kein erfundener Preis.
- [ ] Auf der gesamten Seite erscheint kein Testimonial, kein Logo eines vermeintlichen Kunden, keine Pressereferenz.

### L.5 Technical Build QA
- [ ] `npm install` läuft fehlerfrei.
- [ ] `npm run dev -- --host 127.0.0.1 --port 5173` läuft.
- [ ] `npm run build` läuft fehlerfrei.
- [ ] `npm run preview -- --host 127.0.0.1 --port 4173` rendert die produzierte Seite identisch.
- [ ] `npm run screenshots` läuft erfolgreich (sofern Skript existiert).
- [ ] Keine neuen Console-Errors im Browser-Devtool.
- [ ] Keine ungenutzten Imports in `App.jsx`.
- [ ] `siteConfig.js` exportiert weiterhin `siteConfig` als named export.

### L.6 Handoff ZIP QA
- [ ] ZIP enthält aktualisierte `App.jsx`, `siteConfig.js`, `README.md`, `DEPLOYMENT_NOTES.md`, `.env.example`.
- [ ] ZIP enthält **keine** `node_modules/`, **kein** `dist/`, **keine** `.env.local`-Datei mit echten Credentials.
- [ ] Aktualisierte Review-Screenshots zeigen:
  - Hero mit neuer H1 und 3× OK + 1× REVIEW.
  - Volle Dashboard-Preview mit aktualisierter Pill-Verteilung.
  - Workflow-Section mit Mini-Augment-Block.
  - Access-Section mit 3 Karten.

### L.7 Regression Risks
- [ ] Anchor-Links `#top`, `#product`, `#workflow`, `#evidence`, `#access`, `#early-access` funktionieren weiterhin.
- [ ] Wordmark-Imports und Asset-Pfade unverändert.
- [ ] Tailwind-Klassen und CSS-Variablen unverändert.
- [ ] Farbpalette unverändert (Paper/Ink/Gold/Status-Pills).
- [ ] Dark-Panel-Styling (`dark-panel`-Klasse) unverändert.
- [ ] Pill-Klassen (`pill-ok`, `pill-partial`, `pill-review`, `pill-missing`) unverändert.

---

## M. PRIORISIERUNG

### P0 — Muss jetzt (vor jeder externen Weitergabe, auch privat)

| Änderung | Warum | Erwarteter Effekt | Aufwand | Risiko |
|---|---|---|---|---|
| **`mailto:example.invalid`-Defaults aus `siteConfig.js` entfernen, Pending-Logik in App.jsx einführen** | RFC-Platzhalter dürfen nie als sichtbares CTA-Ziel rendern. Höchstes Marken-/Glaubwürdigkeitsrisiko. | Funktioneller, ehrlicher Funnel; keine versehentlichen Lecks. | M | Low |
| **Hero-H1 + Subline + Trust auf neue Copy umstellen** | Kernpositionierung. Aktuelle H1 ist abstrakt, Subline ist Feature-Liste. | Sofortige Outcome-Klarheit. | S | Low |
| **Hero-Demo-KPIs auf 3× OK + 1× REVIEW umkonfigurieren** | Erster Eindruck = kompetent statt unfertig. | Höhere Above-the-fold-Glaubwürdigkeit. | S | Low |
| **`README.md` Public-Launch-Blocker-Abschnitt + neue `DEPLOYMENT_NOTES.md`** | Schutz vor versehentlichem Public-Deploy. Compliance-Dokumentation. | Klarer Status für jede Person, die das Repo öffnet. | S | Low |
| **Final-CTA-Block auf 1 Primary + 1 Secondary reduzieren, alte Headline `Start with the workflow, not the trade.` in Hero-Eyebrow umziehen** | Klarere Hierarchie, der stärkste Satz erhält Top-Position. | Klarer Conversion-Pfad am Seitenende. | S | Low |

### P1 — Danach (gleicher Patch-Zyklus, falls Zeit; spätestens vor erweiterter Demo-Runde)

| Änderung | Warum | Erwarteter Effekt | Aufwand | Risiko |
|---|---|---|---|---|
| **Problem-Section auf User-Side-Symptome umschreiben** | Emotionaler Anker, der aktuell fehlt. | Höhere Identifikation der Zielgruppe. | S | Low |
| **Principles: „No broker execution" → „Decisions, not orders"** | Positiver Frame, gleicher Inhalt. | Marken-Resonanz steigt, Defensiv-Last sinkt. | S | Low |
| **Workflow-Lede + Mini-Augment-Block „The archive that compounds"** | Retention-Story explizit machen. | Klarer „kein One-off"-Eindruck. | M | Low |
| **Core Features 11 → 3 Hauptmodule + 5 Sub-Features** | Cognitive Overload reduzieren. | Bessere Scanbarkeit. | M | Medium *(Layout-Anpassung an zwei Grids)* |
| **Snowball-Headline + Lede emotional + claim-safe** | Sehnsuchtsmoment ohne Hype. | Höhere Section-Engagement. | S | Low |
| **Status-Pills + Klartext-Untertitel in der Evidence-Section** | Investor-Verständlichkeit. | Geringere Abbruchrate in der Mid-Page. | M | Low |
| **Audience-Items mit Sätzen + Anti-Audience-Block** | Schärfe = Selbstidentifikation. | Bessere Pre-Qualifikation der Leads. | S | Low |
| **Access 4 → 3 Karten** | Redundanz raus, Hierarchie rein. | Klarere Conversion-Architektur. | S | Low |

### P2 — Später (separater Patch-Zyklus)

| Änderung | Warum | Erwarteter Effekt | Aufwand | Risiko |
|---|---|---|---|---|
| **Solution-Section visuell stärken (z. B. SVG-Vorher/Nachher)** | Aktuell visuell leer. | Höhere visuelle Spannungskurve. | M | Low |
| **Workflow-Karten zu Loop-Visualisierung erweitern** | Zyklus-Story stärker machen. | Klares „dies wiederholt sich"-Bild. | L | Medium |
| **Echtes Sample-Report-PDF/MD verlinken (sobald produziert)** | Mikro-Conversion mit echtem Wert. | E-Mail-Liste, höhere Conversion. | M | Low |
| **Founder-Note / Manifest-Section** | Menschlicher Anker bei sonst kühlem Ton. | Identifikation. | M | Low |
| **Disclaimer-Akkordeon-Pattern feinmachen** | Lesefreundlichkeit. | Bessere Footer-UX. | S | Low |
| **Real Imprint + Privacy + Pricing einsetzen** | Public-Launch-Voraussetzung. | Public-Launch unblockt. | L *(juristisch)* | High *(juristisch)* |

---

## N. FINAL RECOMMENDATION

**1. Was soll Codex als nächstes konkret umsetzen?**

Den **P0-Block** in der in J.5 vorgegebenen Reihenfolge:

a) `siteConfig.js` umbauen — Mailto-Defaults entfernen, neue `ctas.sampleReport`-Struktur, Pending-Flags je CTA, aktualisierte Tagline, neue Disclaimer-Short-Version.
b) `App.jsx` Hero — neue Copy laut F.2, KPI-Array für Hero-Demo laut J.8, neue Pending-Render-Logik der CTAs.
c) `App.jsx` Full Dashboard — KPI-Array umkonfigurieren laut J.8, Status-Legende ergänzen.
d) `App.jsx` Final CTA + Footer — neue Headline, Pending-Footer-Links, Disclaimer-Akkordeon.
e) `README.md` neuer Public-Launch-Blocker-Abschnitt; neue Datei `DEPLOYMENT_NOTES.md`; `.env.example` ergänzen.

Damit ist die Seite handoff-fähig, ehrlich im Pending-Zustand, outcome-stark in der Hero und compliance-dokumentiert. Anschließend folgt der **P1-Block** als zweiter Patch-Zyklus.

**2. Was soll bewusst NICHT umgesetzt werden?**

- **Keine echten Preise** für Pro Modules oder Setup Service. Bleibt `Pricing TBD · Private preview` und `Pricing on request · Private preview`.
- **Keine Fake-Imprint-/Privacy-Seiten** und keine Dummy-Inhalte unter „Imprint" oder „Privacy". Footer-Links bleiben im Pending-Zustand bis echte Inhalte vorliegen.
- **Keine Fake-Testimonials**, keine erfundenen Logos, keine vermeintlichen Pressereferenzen.
- **Keine Performance-/Return-/Alpha-Claims** an irgendeiner Stelle.
- **Kein Fake-Newsletter-Form** und keine Fake-Warteliste, solange `VITE_SAMPLE_REPORT_URL` und `VITE_EARLY_ACCESS_URL` unset sind.
- **Keine neuen Sections** außer der Mini-Augment-Komposition unter dem Workflow.
- **Kein Routing**, kein Backend, keine Internationalisierung, keine Analytics.
- **Keine Änderung der Section-IDs** (`#top`, `#product`, `#workflow`, `#evidence`, `#access`, `#early-access`).

**3. Was muss vor Public Launch zwingend real geklärt werden?**

In dieser Reihenfolge:
1. **Imprint** real anlegen und unter `VITE_IMPRINT_URL` hinterlegen — DE/EU-Pflicht.
2. **Privacy Policy** real anlegen und unter `VITE_PRIVACY_URL` hinterlegen — GDPR-Pflicht.
3. **Real CTA targets** für Sample-Report und Early Access (via Notion/Tally/EmailOctopus oder eigener Endpoint) — `VITE_SAMPLE_REPORT_URL`, `VITE_EARLY_ACCESS_URL`.
4. **Pricing-/Scope-Entscheidung** für Pro Modules und Setup Service.
5. **GitHub-/Sponsor-URLs** entscheiden — `VITE_GITHUB_URL`, `VITE_SPONSORS_URL`.
6. **Domain + Deploy-Pipeline** (z. B. Vercel) einrichten und absichern (kein versehentlicher öffentlicher Index vor Punkt 1–5).

**4. Welche 3 Änderungen bringen den größten Conversion-Gewinn?**

1. **Hero-H1 + Subline + Trust-Statement umstellen.** Outcome zuerst, Disclaimer-Last halbiert. Effekt auf den ersten Eindruck ist dramatisch — die Seite hört auf, „eine Architekturbeschreibung" zu sein, und wird ein „Versprechen".
2. **Hero-Demo auf 3× OK + 1× REVIEW.** Beseitigt den größten visuellen Conversion-Killer der Seite. Erste 1,5 Sekunden lesen sich nicht mehr als „diese Software hat Probleme".
3. **Mailto-Defaults raus + ehrliche Pending-Zustände rein.** Schützt vor versehentlichem Lead-Verlust und vor Marken-Schaden bei versehentlichem Deploy. Schafft die Voraussetzung dafür, dass eine echte Mikro-Conversion (`See the sample monthly report`) später wirken kann.

**5. Welche bestehenden Markenelemente müssen geschützt werden?**

- **Anti-Hype-Ton.** Keine Neon-Buttons, keine „get rich"-Sprache, keine Stockfotos. Diese Zurückhaltung *ist* der Markenkern.
- **Paper/Ink/Gold-Farbpalette und Typografie.** Premium-Wirkung ist eine der höchsten gegenwärtigen Stärken.
- **Die 6 Architekturprinzipien als Markenherz.** Auch nach der Umformulierung von „No broker execution" zu „Decisions, not orders" bleibt die Anzahl, die Reihenfolge und die Aussage ungeschwächt.
- **Status-Pill-Sprache** (`COVERED`, `PARTIAL`, `REVIEW`, `MISSING_DATA`, `INSUFFICIENT_INPUTS`, `INSUFFICIENT_HISTORY`, `NO_MATCH`). Das ist die wichtigste konkrete Differenzierung gegenüber Yahoo Finance / Sharesight / Excel.
- **„Decision Journal"** als Begriff und als sichtbarer Code-Block.
- **Goldener Snowball-Chart-Stroke.** Einziger warmer Farbakzent, thematisch passend.
- **Footer-Disclaimer in voller Strenge.** Verkürzen für die Default-Sicht ja, abschwächen nein.
- **Local-first / No-Broker / No-Cloud-Aussagen.** Werden im Trust-Statement gebündelt, aber nicht entfernt. Sie sind Marken-Hard-Edges.

---

*Spec erstellt auf Basis von `opus_landingpage_fix_context_2026-04-26.zip` (`product_notes.md`, `App.jsx`, `siteConfig.js`, `design-tokens.css`, alle 6 Screenshots, Sample-Reports, Project Charter, Audit). Keine Codeänderungen vorgenommen. Alle Copy-Strings sind final und kopierbar. Alle Pending-/Blocker-Texte sind so formuliert, dass sie keine erfundenen Inhalte einführen.*

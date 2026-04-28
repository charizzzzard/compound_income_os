# Compound Income OS — Mockup Review v5 (Wave 5 / Review-OS-Pivot)

**Trigger:** Sechs neue Mockups (Home, Workflow, Evidence, Portfolio, Dashboard, Manifesto). Strategischer Pivot von „One Decision a Month" auf eine **Review-/Reasoning-OS-Erzählung** — *„Spreadsheets hold the data. Compound Income OS keeps the reasoning."* Plus neues Farbsystem (Blau/Grün/Gold/Lila als Sleeve-Coding) und neue Nomenklatur (Review Packet, Evidence Trail, Attention Queue, Context Archive).

**Scope dieser Review:** Strict Audit gegen das Briefing. Keine neue Strategie, kein Re-Design — nur Pass/Fail, Copy- und Visual-Fixes, Implementation-Plan.

---

## A. SHORT VERDICT

Die Mockups sind **directionally ready to implement, mit einer microcopy-Iteration davor.** Der Pivot von „One decision a month" zu „Keeps the reasoning" ist ein klarer Gewinn — die Erzählung ist ehrlicher, breiter, und passt wesentlich besser zum tatsächlichen System (Review Packet, Evidence Trail, Context Archive sind reale Engine-Outputs). Das neue Farbsystem (Blau/Grün/Gold/Lila als Sleeve-Coding) trägt; die Portfolio-Page ist die stärkste der Sechs und funktioniert als visueller Anker. Home und Manifesto sind nahezu freigabefertig. Workflow ist gut, aber überfrachtet. Evidence ist sehr stark, hat aber ein Wording-Risiko mit `NEEDS REVIEW` als Status-Label. Dashboard ist die uneinheitlichste Seite und braucht zwei kleinere Eingriffe. Insgesamt: kein neues Visual-Round nötig, aber **ein einziger Microcopy-Pass + zwei kleine Visual-Patches**.

---

## B. WHAT WORKS (zu erhalten)

### Visuelle Identität
- **Off-white Paper / Dark-Navy-Panel-Split** ist konsistent durchgezogen, ohne dass die Seite kalt wirkt.
- **Editorial-Typografie** der Hero-H1s (Serif, eng tracking, große Größe) trägt den Premium-Anspruch.
- **Sparsamer Farbeinsatz** (Blau/Grün/Gold/Lila nur dort, wo sie semantische Bedeutung tragen) — keine Farbe um der Farbe willen.
- **`// CAPS`-Eyebrows** sind über alle 6 Pages konsistent.
- **Dark-Panel als Product-UI-Anker** rechts vom Hero auf jeder Page schafft eine Wiedererkennung über die Site.

### Produktklarheit
- **„Spreadsheets hold the data. Compound Income OS keeps the reasoning."** ist der stärkste Marketing-Satz der ganzen Site und wiederholt sich auf Home + Workflow + Manifesto. Das ist Story-Konsistenz, nicht Drift.
- **Review Packet, Evidence Trail, Attention Queue, Context Archive** sind als Vier-Begriff-System klar etabliert und auf jeder Page mit demselben Wording referenziert.
- **Status-Pills** (`COVERED`, `PARTIAL`, `NEEDS REVIEW`, `MISSING`, `TOO EARLY`) haben eine sofort lesbare Farbsemantik.

### Compliance-Safe Positionierung
- **„Framework only · not allocation advice"** auf der Portfolio-Page steht prominent unter dem Allocation-Panel — exakt dort, wo der Visitor instinktiv „ist das eine Empfehlung?" denkt.
- **Synthetische Holdings ATLAS / NOVA / RIVER / HELIO + CORE/QUALITY ETF + CASH BUFFER** sind durchgehend, keine echten Tickers (MSFT/V/JNJ aus früheren Mockup-Runden sind weg).
- **Synthetic Demo Values-Pill** ist auf jedem Dashboard-Panel sichtbar.
- **Manifesto „What this product is not"** mit `Not a broker / Not a trading terminal / Not crypto / Not a social feed / Not personalized investment advice` ist die explizite Anti-Audience-Form, die das Briefing fordert.

### Review Packet Proof
- Latest Review Packet auf Home (Image 1, oben rechts) mit `Packet ID DEMO-2026-04 / Generated May 23, 2026 / Scope 23 holdings / LOCAL-FIRST · READ-ONLY` ist das **stärkste Trust-Asset** der gesamten Site. Es belegt visuell, dass das System einen Output produziert, den man öffnen kann.
- `What Changed 12 changes / What's Missing 3 gaps / Notes Saved 9 notes / Archived Reasoning 16 entries` ist eine Zahlen-Konkretion, die abstrakte Versprechungen in greifbare Counts übersetzt.

### Evidence Trail Proof
- **Evidence Check-Tabelle** auf Image 3 (ATLAS 95% COVERED, NOVA 62% PARTIAL, RIVER 28% NEEDS REVIEW, HELIO 0% MISSING) zeigt die volle Range visuell — von „funktioniert" bis „transparent leer".
- **„How evidence flows into the system"** mit 5 nummerierten Schritten (Match the holding → Pull official numbers → Review the update → Approve what is usable → Keep the source visible) ist die menschlichste Erklärung der SEC-Pipeline, die ich auf der Site bisher gesehen habe.
- **„Nothing is silently filled."** als Footer-Highlight-Bar ist die zweitbeste Single-Sentence-Aussage der Site nach dem Reasoning-Satz.

### Portfolio Allocation Style (canonical anchor)
- Die 4 farbigen Sleeve-Cards mit Icon + Range + Bar-Indikator sind die erste Stelle, an der die Marke **sympathisch** wirkt und nicht nur seriös.
- `Max single 8% · Top 10 max 60% · Sector max 25%` als Mono-Pillenreihe direkt unter dem Allocation-Panel — sehr stark, weil es Regeln zeigt statt Behauptungen.
- **Attention Queue** (synthetisch) mit 6 Holdings, Sleeve-Tag, Rule Fit / Valuation Context / Evidence Status / Review Status: 4 Status-Spalten pro Zeile sind die richtige Tiefe — informativ ohne überfordernd.

### Dashboard-Nutzen
- **3-Frage-Struktur** (`Where do I stand? / What changed? / What needs attention?`) im Dark-Panel oben ist die beste Dashboard-Headline-Komposition, die ich auf einer Investor-Tool-Site gesehen habe.
- **Local View Only / Read-Only / No Cloud** als Footer-Bar ist klare Privacy-Aussage ohne Verteidigungs-Ton.

### Manifesto-Trust
- **„I built this because spreadsheets kept the data, but not the reasoning."** signiert mit `— A builder and long-term investor` ist ehrlicher als „I built this because the tools I needed didn't exist" der Vorgängerversion.
- **6 Operating Principles** mit Icon + Sub-Klartext-Erklärung (`Clarity over noise / Evidence over opinion / …`) sind die saubere Verschärfung der vorherigen 6 Architecture Principles.

---

## C. WHAT STILL NEEDS FIXING

### C.1 Copy-Drift / leichte Advice-Risiken

**1. „NEEDS REVIEW" als Status-Pill auf Evidence-Page** (Image 3, RIVER 28% Status-Spalte) — das Briefing listet `NEEDS REVIEW` *nicht* in der erlaubten Status-Sprache. Die Code-Sprache des Repo ist `REVIEW` (z. B. `WAIT_VALUATION`, `REVIEW_CORE_DATA`). „NEEDS REVIEW" ist menschlicher, aber driftet weg von der konsistenten Status-Sprache des Backends. **Fix:** Auf `REVIEW` umstellen — passt zur internen Sprache und bleibt menschlich genug.

**2. „TOO EARLY" als Status-Pill** (Image 3, Coverage-Tabelle, NOVA Advanced + HELIO Advanced) — das ist erfunden. Das Repo hat `INSUFFICIENT_INPUTS / INSUFFICIENT_HISTORY / NOT_APPLICABLE`. „TOO EARLY" suggeriert eine Empfehlung („zu früh um zu kaufen"), was gefährlich nah an Advice-Sprache ist. **Fix:** Ersetzen durch `NOT_APPLICABLE` oder `NOT YET DUE` (Briefing-konform).

**3. „Open sample review" als Header-CTA** (alle 6 Pages oben rechts) vs. **„Open sample review packet" / „Open a sample review packet"** auf den Hero-Buttons. Drei verschiedene Wordings für denselben CTA. **Fix:** Auf eine einheitliche Form. Empfehlung: `Open sample review packet` (lang, in Hero) und `Open sample` (kurz, in Header). Aktuell mischt die Site beide ohne System.

**4. „Get early access" auf Manifesto** (Image 6, Hero-CTA) — vs. allen anderen Pages, die `Open sample review` als Primary haben. Inkonsistenz. **Fix:** Manifesto-Hero-CTA auf `Open sample review packet` umstellen, `Get early access` lebt bei den 3 Access-Cards weiter unten.

**5. „Within range" Status-Pill** (Image 4, Attention-Queue-Tabelle) erscheint **8x** in derselben Tabelle. Visuell ist das eine fast-vollständig-grüne Spalte, die Aussage relativiert sich selbst. **Fix:** Bei 5 von 6 Holdings ist „Within range" der Default-Zustand — die Pill weglassen und nur dort zeigen, wo etwas *außerhalb* der Range ist. Oder: kürzere Pill `OK / Outside`.

**6. „Review threshold"** (Image 4, RIVER-Zeile, Spalte „Review Status") — ist nicht in der erlaubten Sprache des Briefings. **Fix:** `Review point` oder `Watch context` (beide briefing-konform).

**7. „Review evidence"** als Promise-Card auf Home (Image 1, untere Zeile, zweite Karte): *„See what's covered, what is missing, and the quality of the data."* — okay. Aber die Card-Headline `Review evidence` ist Verb + Nomen, während die anderen 4 Cards Verb-Phrasen sind (`Import broker data / Build an attention queue / Track income and history / Save the review packet`). Inkonsistente Grammatik. **Fix:** `Review the evidence` oder `Check the evidence`.

### C.2 Visuelle Probleme

**8. Dashboard-Page hat 3 visuell konkurrierende Layoutsysteme:** (a) das Dark-Panel oben (3-Spalten-Frage-Layout) — schön, (b) eine 5-Spalten-Modul-Reihe mit nummerierten Cards `01–05` darunter — auch okay, aber (c) eine zweite Reihe mit 6 verschiedenen Datentyp-Visuals (Bar-Chart, Pfeil-Liste, Linien-Chart, Donut-Chart, Icon-Liste). Das ist **eine Visualisierungs-Type pro Card** — was wie eine Charting-Demo wirkt, nicht wie ein konsolidiertes Dashboard. **Fix:** Auf 2 Visualisierungstypen reduzieren — z. B. nur Bar-Charts und Number-KPIs. Donut-Chart auf der Cost-/Tax-Card raus, durch Number-KPI ersetzen.

**9. Color-System-Spillover auf Workflow-Page** (Image 2): Die 6 Stage-Cards 01–06 nutzen alle das **blaue** Icon. Das funktioniert, aber konkurriert mit der Portfolio-Page-Farbsemantik (Blau = Core / Structure). Auf Workflow ist Blau nicht semantisch — es ist Default-Akzent. **Fix:** Workflow-Stage-Icons in Ink/Schwarz statt Blau, damit Blau auf der Portfolio-Page seinen semantischen Anker behält. Sonst verwässert das System.

**10. Footer-Slogan-Bar auf Manifesto** (Image 6, ganz unten): `BUILT FOR INVESTORS, NOT TRADERS · CLARITY OVER NOISE · EVIDENCE OVER OPINION · PROCESS OVER IMPULSE · PRIVACY BY DEFAULT · NO HYPE · JUST SIGNAL` — 7 Items. Die anderen Pages haben (laut bisherigem Repo-Stand) eine kürzere Bar. **Fix:** Auf 4–5 Items kürzen, sonst wird die Bar zur Wand. Empfehlung: `BUILT FOR INVESTORS, NOT TRADERS · PRIVACY BY DEFAULT · NO HYPE · JUST SIGNAL`.

**11. Home-Hero-Dashboard zeigt 3 KPIs in einer Reihe** (Image 1): `PORTFOLIO 23 holdings · 4 sleeves WITHIN RANGE / EVIDENCE 3 gaps need review NEEDS REVIEW / REVIEW ITEMS 4 items to check READY FOR REVIEW`. Die Pill-Wordings sind 3 verschiedene Stile: `WITHIN RANGE` (status-like), `NEEDS REVIEW` (action-like), `READY FOR REVIEW` (state-like). **Fix:** Drei konsistente Status-Pills: z. B. `WITHIN RANGE / REVIEW / READY` oder ein durchgehender state-Stil.

**12. Latest Review Packet-Card auf Home** (Image 1, mittlere Zeile rechts) und **Portfolio Review Packet — Apr 2026** auf Workflow (Image 2, Mitte) zeigen **unterschiedliche Datumsangaben**: Home `May 23, 2026` / `May 2026 v1.0`, Workflow `Apr 2026`. Wenn der Visitor zwischen den Pages switcht, wirkt das wie Datum-Drift. **Fix:** Beide auf `Apr 2026` oder beide auf `May 2026` synchronisieren.

### C.3 Strukturelle Beobachtungen

**13. Home-Page: 5 Promise-Cards in der unteren Zeile** (Image 1): `Import broker data / Review evidence / Build an attention queue / Track income and history / Save the review packet`. Das sind 5 Verben — aber das Master-Plan-v4 hatte 5 Page-Teaser, die zu den 5 Tiefen-Pages führen. Hier sind es **Action-Cards ohne Page-Link**. **Fix:** Entweder die 5 Cards verlinken (z. B. „Review evidence → /evidence", „Build an attention queue → /portfolio") oder offen lassen, dass das nur Funktionsbeschreibungen sind. Aktuell unklar.

**14. Workflow-Page: 6-Stage-Karten + Review-Flow-Panel oben rechts zeigen denselben Inhalt zweimal** (Image 2). Stages 01–06 als große Cards mit Beschreibung + identische 5-Stage-Liste im Dark-Panel oben rechts (`Bring in your portfolio / Check the evidence / Build the attention queue / Write the review packet / Keep the context`). Doppelung. **Fix:** Das Review-Flow-Panel hat 5 Stages, die Cards 6 Stages — das verwirrt zusätzlich. Eines von beiden raus, oder Stages auf einheitlich 5 oder 6 normalisieren.

**15. Dashboard-Page: „Not another portfolio tracker" Trust-Box** (Image 5, links unter den CTAs) ist defensiv formuliert. Ein „Wir sind kein …" als Trust-Statement ist schwächer als ein „Wir sind …". **Fix:** Reformulieren als positives Statement, z. B. `A review console for the decisions behind your portfolio.`

---

## D. PAGE-BY-PAGE REVIEW

### D.1 Home (Image 1)

**Was funktioniert:**
- Hero-H1 + Subline („See what changed, what is missing, and what deserves attention. All your research, evidence, and context in one place.") → menschlich, klar, ohne Promise-Last.
- Drei kleine Bulletpoint-Sätze unter der Subline (`See what changed / See what's missing / Keep the reasoning`) etablieren das Review-Trio.
- Review Snapshot + Latest Review Packet rechts ist der stärkste Trust-Beweis der Site.
- Footer-Bar `Local Dashboard · Review Packet · Context Archive` macht die 3 Output-Typen sofort sichtbar.
- Reasoning-Satz „Broker apps show positions. Spreadsheets hold data. Compound Income OS keeps the reasoning."

**Was schwach ist:**
- 5 Promise-Cards unten ohne klare Hierarchie zu den 5 Tiefen-Pages (Punkt 13).
- Home-Hero-Dashboard-Pills inkonsistent (Punkt 11).
- 2 CTAs nebeneinander (`Open sample review packet` + `See how it works`) — okay, aber `See how it works` führt nirgendwo sichtbar hin (kein Anker, kein Link-Pfeil, nur Play-Icon).

**Exact copy issues:**
- `Review evidence` (Card 02) → `Review the evidence` oder `Check the evidence`.
- Hero-Pills `WITHIN RANGE / NEEDS REVIEW / READY FOR REVIEW` → einheitlicher Status-Stil.

**Exact visual issues:**
- Header-Nav hat 5 Items, aber die Home-Page selbst hat keinen Active-Indicator (vs. allen anderen Pages, wo der jeweilige Punkt unterstrichen ist). Heißt: auf Home weiß man nicht, dass man auf Home ist.

**Was zu erhalten:**
- Hero-Komposition ohne Modification.
- Review Snapshot + Latest Review Packet 1:1.
- 3 Problem-Cards im unteren Drittel.

**Was zu ändern vor Implementation:**
- Card-Wording-Konsistenz.
- Hero-Pill-Stil.
- 5 Promise-Cards entweder verlinken oder die Logik begründen (Section-Anchor zur jeweiligen Tiefen-Page).

### D.2 Workflow (Image 2)

**Was funktioniert:**
- H1 `A process you can trust, repeat, and revisit.` ist der zweitbeste Hero-Satz der Site nach dem Reasoning-Statement.
- 6 Stage-Cards (01–06) mit Title + Body + Output-Pill (`Portfolio Snapshot`, `Evidence Trail`, `Attention Queue`, `Review Packet`, `Context Archive`) sind die klarste Workflow-Visualisierung der ganzen Site-History.
- Review Archive (`Apr 2026 / Nov 2025 / Oct 2024 / All reviews in one place`) belegt die Retention-/Archiv-Story konkret mit fingerten Daten + Counts.
- Highlight-Bar unten *„Spreadsheets hold data. Compound Income OS keeps the review context. Numbers change. Context compounds."* — perfekt.

**Was schwach ist:**
- Doppelung zwischen 6-Stage-Karten und 5-Stage-Review-Flow-Panel oben rechts (Punkt 14).
- Portfolio Review Packet-Block in der Mitte zeigt 6 Spalten (`What changed / What needs attention / What data is missing / Notes for next review / Archived reasoning / Review context`) — das ist viel auf einmal. Die Spalten haben je 2–3 Bullets darunter, also ist die Card am Ende sehr text-dicht.

**Exact copy issues:**
- `Bring in your portfolio` (Stage 01) vs. `Import broker data` (Home-Card-Wording) → uneinheitlich. Auf einer Page heißt es Bringen, auf der anderen Importieren.
- `Clean up the view` (Stage 02) — etwas vage. Spec-Begriff ist `Normalize positions` oder `Data quality check`. Vorschlag: `Clean and normalize the data`.

**Exact visual issues:**
- Datum-Drift zur Home-Page (Apr 2026 vs. May 2026, Punkt 12).
- Workflow-Stage-Icons alle blau (Punkt 9, Color-System-Spillover).

**Was zu erhalten:**
- 6-Stage-Card-Layout.
- Review Archive-Section mit datierten Cards.
- Footer-Highlight-Bar mit `Spreadsheets hold data. Compound Income OS keeps the review context.`

**Was zu ändern vor Implementation:**
- Doppelung Review Flow vs. Stage Cards auflösen — eines der beiden raus oder die Stages auf 5 oder 6 angleichen.
- Stage 02 Wording schärfen.
- Stage-Icons in neutrales Schwarz.

### D.3 Evidence (Image 3)

**Was funktioniert:**
- H1 `See which numbers you can trust.` — direkt, klar, sticht aus der Site heraus.
- Evidence Check-Tabelle mit 4 Holdings + Coverage-Bar + Status-Pill + Review-Context-Spalte ist visuell die stärkste Tabelle der Site (klar, scannbar, vollständig).
- Coverage by holding and KPI tier-Tabelle dahinter (mit 4 KPI-Tiers + Status-Pill je Zelle) übersetzt eine technische Ground-Truth (das System hat tatsächlich diese 4 Tiers im Code) in eine sofort lesbare Marketing-Form.
- *„How evidence flows into the system"* mit 5 nummerierten Schritten — die menschlichste SEC-Pipeline-Erklärung der ganzen Site-History.
- *„What the status labels mean"* rechts daneben — Klartext-Glossar pro Pill.
- Footer-Bar *„Nothing is silently filled."*

**Was schwach ist:**
- `NEEDS REVIEW` Status-Pill nicht in der erlaubten Sprachliste (Punkt 1).
- `TOO EARLY` Status-Pill ist erfunden + advice-nah (Punkt 2).
- Die `Next step`-Spalte (`Ready for review / Check valuation context / Needs review / Keep context`) ist gut, aber `Check valuation context` ist sehr nah an Advice (`Check valuation` impliziert eine Entscheidungsempfehlung).

**Exact copy issues:**
- `NEEDS REVIEW` → `REVIEW` (briefing-konform, repo-sprache-konform).
- `TOO EARLY` → `NOT_APPLICABLE` oder `NOT YET DUE`.
- `Check valuation context` → `Open valuation context` (neutraler).

**Exact visual issues:**
- Coverage-Balken (Image 3, Evidence Check-Tabelle) sind 4 verschiedene Farben (grün/gelb/orange/grau). Das ist gut. Aber die Reihenfolge (95% grün → 62% gelb → 28% orange → 0% grau) erinnert an eine Bewertungsskala. Das ist ungewollt, weil das System keine Holdings-Bewertung ist, sondern Daten-Coverage. **Empfehlung:** Coverage-Balken-Farbe an Status-Pill koppeln (grün/gelb/orange/rot ist okay, weil es Coverage-Status ist, nicht Holdings-Quality).

**Was zu erhalten:**
- Evidence Check-Tabelle 1:1.
- 5-Schritt-Erklärung 1:1.
- Status-Label-Glossar 1:1 (mit Pill-Replacements oben).
- *„Nothing is silently filled."* Footer-Bar 1:1.

**Was zu ändern vor Implementation:**
- 2 Status-Pill-Wordings (siehe Copy issues).
- 1 Next-Step-Wording.

### D.4 Portfolio (Image 4) — **Canonical Visual Anchor**

**Was funktioniert:**
- H1 `Four sleeves. Clear rules. Long-term focus.` ist die direkteste Hero-Aussage der Site.
- Portfolio-Allocation-Panel mit 4 farbigen Sleeve-Boxen (Blau/Grün/Gold/Lila) + Bar-Indicator + Range — das ist der **Visual Anchor der ganzen Site**.
- `Max single 8% · Top 10 max 60% · Sector max 25%` als Mono-Pill-Reihe direkt darunter.
- *„Framework only · not allocation advice"* prominent.
- 4 Sleeve-Cards unter dem Hero mit denselben 4 Icons + Range + Body-Text.
- Attention Queue-Tabelle mit 6 Holdings + 4 Status-Spalten — sehr scanbar.
- 5 Guardrail-Karten unten (`Concentration limits / Sector caps / Watchlist status / Review thresholds / Cash awareness`) mit denselben 4 Sleeve-Farben in den Icons.
- Trust-Banner `This framework provides structure and context. You stay in control.` ist die honestste Brand-Aussage der Site.

**Was schwach ist:**
- Attention-Queue zeigt `Within range` 8 Mal (Punkt 5) — verwässert.
- `Review threshold` Wording (Punkt 7) — nicht briefing-konform.

**Exact copy issues:**
- Attention Queue: `Within range` → in Default-Zustand weglassen oder durch `OK` ersetzen.
- RIVER-Zeile: `Review threshold` → `Review point` oder `Watch context`.

**Exact visual issues:**
- Keine kritischen.
- Die 5 Guardrail-Karten unten haben wieder die 4 Sleeve-Farben → konsistent, aber Karte 4 (Review thresholds) hat Gold-Icon, was thematisch nicht zur Sleeve-Farbsemantik passt (Gold = Single Stock, nicht Review). Acceptable Drift, da der Icon-Stil pro Karte semantisch zur jeweiligen Funktion passt.

**Was zu erhalten:**
- Komplette Page als Visual Anchor.
- 4-Farben-System.
- Attention-Queue-Layout (mit den 2 Wording-Fixes).

**Was zu ändern vor Implementation:**
- 2 Wording-Fixes (Within range Default, Review threshold).
- Sonst nichts.

### D.5 Dashboard (Image 5)

**Was funktioniert:**
- H1 `One local dashboard. The full picture.` — klar.
- 3-Frage-Struktur im Dark-Panel oben (`Where do I stand? / What changed? / What needs attention?`) ist die beste Dashboard-Headline-Komposition der ganzen Site-History.
- Footer-Bar `LOCAL VIEW ONLY · READ-ONLY · NO CLOUD` mit Icons.
- 5 Modul-Cards (`Portfolio / Structure`, `Review / Fundamentals`, `Historical Comparison`, `Cost / Tax`, `Data Quality / Methodology`) entsprechen den 5 KPI-Groups des realen Dashboard-Engine im Repo. Authentisch.

**Was schwach ist:**
- Zweite Datenreihe (Bar-Chart, Pfeil-Liste, Linien-Chart, Donut-Chart, Icon-Liste) ist visuell überladen (Punkt 8).
- `Not another portfolio tracker` Trust-Box defensiv formuliert (Punkt 15).
- Die Card-Number-Indikatoren `+18 / -0.42% / 12 days ago / 0.48% / High` mischen Format-Stile sehr stark — Prozente, absolute Counts, qualitatives „High". Das ist real, aber visuell unruhig.

**Exact copy issues:**
- Trust-Box: `Not another portfolio tracker. A review system for the decisions behind your portfolio.` → reformulieren auf positiv: `A review console for the decisions behind your portfolio.`
- `Vs benchmark (YTD) -0.42%` zeigt einen negativen Wert in roter Farbe → funktional korrekt, aber: ein Marketing-Mockup, der einen YTD-Underperformance-Wert in Rot prominent zeigt, ist eine ungewöhnliche Wahl. Mit `Historical comparison only · Not a forecast` direkt darunter ist das compliance-mäßig okay, aber visuell ist Rot+negativer Wert eine Botschaft, die der Visitor mitnimmt. **Fix:** Demo-Wert auf positiv oder neutral wechseln (`+0.84%` oder `+0.00%`), um keine Performance-Behauptung implizit zu machen.

**Exact visual issues:**
- Reduktion der 6 Visualisierungstypen auf 2 (siehe Punkt 8).

**Was zu erhalten:**
- 3-Frage-Hero-Komposition.
- 5-Modul-Card-Layout.
- Footer-Privacy-Bar.

**Was zu ändern vor Implementation:**
- Visualisierungs-Reduktion in der zweiten Reihe.
- Trust-Box positiv reformulieren.
- Demo-Wert YTD-Performance auf neutral.

### D.6 Manifesto (Image 6)

**Was funktioniert:**
- H1 `Built for people who think for the long run.`
- Operating Principles-Panel mit 6 Items + Klartext-Erklärung + Icon → visuell die ruhigste Komposition der Site, was zur Marken-DNA passt.
- 3 Cards (`What this product is / What this product is not / I built this because…`) → die Anti-Audience-Form wird durch das positive Pendant balanciert.
- 3 Access-Cards (`Open-source core / Private preview / Setup help`) mit `Access details are still taking shape` als ehrlichem Pending-State.
- Final-CTA `See Compound Income OS in practice` führt sauber zum Sample-Review-Packet.
- Slogan-Bar (mit Punkt 10 als Längenfix).

**Was schwach ist:**
- Hero-CTA `Get early access` (Punkt 4) inkonsistent mit allen anderen Pages.
- Slogan-Bar mit 7 Items zu lang (Punkt 10).

**Exact copy issues:**
- Hero-Primary `Get early access` → `Open sample review packet` (konsistent mit allen anderen Pages).
- `Get early access` als CTA bleibt in der Private-Preview-Access-Card weiter unten.

**Exact visual issues:**
- Slogan-Bar kürzen.

**Was zu erhalten:**
- Operating Principles-Panel 1:1.
- 3 What-this-is/is-not/I-built-this-Cards 1:1.
- 3 Access-Cards 1:1.
- Final-CTA 1:1.

**Was zu ändern vor Implementation:**
- 2 Mini-Fixes (Hero-CTA, Slogan-Bar-Länge).

---

## E. PROJECT CONTEXT FIT

| Dimension | Mockup-Repräsentation | Repo-Realität | Drift? |
|---|---|---|---|
| **Local-first** | Footer-Bar `LOCAL VIEW ONLY · READ-ONLY · NO CLOUD`, Tags `LOCAL-FIRST` auf jeder Page | `personal_run_engine`, Dashboard-Server bindet nur 127.0.0.1 | ✅ Korrekt |
| **Review Packet / Report Generation** | Latest Review Packet auf Home, Review Packet Apr 2026 auf Workflow, Sample-CTA durchgängig | `build_monthly_decision_report` produziert `monthly_decision_report.md`. Naming-Drift: Code sagt "Decision", Mockup sagt "Review" | ⚠️ Naming-Drift, aber positionierungs-konsistent (Review < Decision compliance-mäßig) |
| **Evidence Workflow** | 5-Schritt-Pipeline auf Evidence-Page, Evidence Trail-Begriff durchgängig | `fundamentals_evidence_engine`, `fundamentals_evidence_compose`, `fundamentals_evidence_apply`, SEC-Snapshot-Pipeline | ✅ Korrekt — sogar konservativer übersetzt als der Code |
| **Data Quality Visibility** | `COVERED / PARTIAL / NEEDS REVIEW / MISSING / TOO EARLY` Pill-System auf Evidence + Coverage-Tabelle | Code hat: `COVERED / PARTIAL / REVIEW / MISSING_DATA / NO_MATCH / INSUFFICIENT_INPUTS / INSUFFICIENT_HISTORY / NOT_APPLICABLE` | ⚠️ `NEEDS REVIEW` und `TOO EARLY` sind Mockup-Erfindungen — siehe C.1 |
| **Portfolio Structure** | 4-Sleeve-Modell (Core ETF / Dividend Quality ETF / Single Stock / Cash) mit konkreten Range-Bands | `configs/portfolio_rules.yaml` definiert exakt diese 4 Sleeves mit denselben Bands (45–60 / 10–25 / 20–35 / 5–15) | ✅ 1:1 korrekt |
| **Dashboard** | 5 KPI-Groups, lokale Read-Only-View, kein Cloud | `dashboard_engine` + `dashboard_server` mit genau 5 Metric-Groups (Portfolio/Struktur, Score/Fundamentals, Benchmark/Performance, Kosten/Steuern, Datenqualität/Methodik) | ✅ 1:1 korrekt |
| **Review Archive** | Apr 2026 / Nov 2025 / Oct 2024 + „All reviews in one place" auf Workflow | `personal_run_engine` produziert dated Reports unter `reports/<date>/`, plus `personal_run_manifest.json` | ✅ Korrekt |
| **Non-Broker / Non-Execution** | Manifesto „What this product is not" + Footer-Disclaimer auf jeder Page | `Project Charter` Nicht-Ziele Section 1: "Keine Broker-Orderausfuehrung, kein Auto-Trading" | ✅ Korrekt |
| **Synthetic Holding Names** | ATLAS / NOVA / RIVER / HELIO / CORE ETF / QUALITY ETF / CASH BUFFER | Briefing erlaubt diese Namen | ✅ Korrekt |
| **Costs / Tax Context** | Cost / Tax Card im Dashboard mit Donut + 0.48% Total Costs + Platform Fees / FX / Tax Drag | `cost_tax_engine` liefert genau diese Metriken | ✅ Korrekt |

**Erfundene oder problematische Elemente:**
1. `NEEDS REVIEW` und `TOO EARLY` als Status-Pills — siehe C.1.
2. **`-0.42%` YTD-Underperformance-Demo** auf Dashboard — siehe D.5. Compliance-mäßig okay, aber implizite Performance-Aussage.
3. **`Latest Review Packet · Generated May 23, 2026` mit konkretem Datum** — wenn der Visitor die Site am 1. Mai aufruft, wirkt ein Future-Date als Bug. Ein Generic-Tag (`Generated last week / 12 days ago`) ist robuster.
4. **`Review thresholds`** in Portfolio-Page-Guardrails-Section — Wording.

---

## F. IMPLEMENTATION READINESS

### F.1 Visual Source of Truth

Die **Portfolio-Page (Image 4)** ist der canonical visual anchor laut Briefing — bestätigt. Das gesamte Sleeve-Farbsystem (Blau/Grün/Gold/Lila) wird als CSS-Variablen extrahiert:

```css
--sleeve-core: #blue       /* Core ETF — structure */
--sleeve-quality: #green   /* Dividend Quality — evidence */
--sleeve-stock: #gold      /* Single Stock — attention */
--sleeve-cash: #purple     /* Cash — flexibility */
```

Diese 4 Variablen werden **nur** in folgenden Kontexten verwendet:
- Portfolio-Page (alle Sleeve-Karten, Allocation-Panel, Attention-Queue-Spalten, Guardrail-Icons)
- Cross-Page-Sleeve-Tags (z. B. wenn Workflow oder Evidence einen Sleeve-Namen erwähnt, ist der Tag farb-codiert)
- **Nicht** als Default-Akzentfarben für Buttons, Links, Icons, Status-Pills

Default-Akzent bleibt das bestehende Gold (warm) oder ein neutrales Blau-Grau, abhängig von der finalen Marken-Palette.

### F.2 Wiederverwendbare Komponenten

Folgende Komponenten werden zentralisiert (in dieser Reihenfolge):

| Komponente | Wo verwendet | Props |
|---|---|---|
| `<DarkProductPanel>` | jede Page Hero rechts | `title`, `eyebrow`, `children`, `pill?` |
| `<StatusPill>` | überall | `status: COVERED \| PARTIAL \| REVIEW \| MISSING \| NOT_APPLICABLE \| OK` |
| `<SleeveBadge>` | Portfolio + Cross-Page | `sleeve: core \| quality \| stock \| cash`, `label` |
| `<KPITile>` | Dashboard + Hero-Mini-Dashboards | `label`, `value`, `subValue?`, `tone?` |
| `<ReviewPacketCard>` | Home + Workflow | `packetId`, `generated`, `scope`, `version` |
| `<AttentionQueueRow>` | Portfolio + Dashboard | `holding`, `sleeve`, `ruleFit`, `valuationContext`, `evidenceStatus`, `reviewStatus` |
| `<EyebrowMono>` | jede Section | `children` |
| `<HighlightBar>` | je 1× pro Page max | `children` |
| `<SloganBar>` | Footer | konstanter Inhalt |
| `<PendingFooterLink>` | Footer | `label` (Imprint / Privacy) |
| `<SmartLink>` | bestehend, beibehalten | unverändert |

### F.3 Zu zentralisierende Copy

Folgende Copy-Strings werden in `siteConfig.js` als shared constants extrahiert, damit sie nicht über 6 Page-Komponenten driften:

```js
siteConfig.copy = {
  taglineHero: 'A calmer way to run a long-term portfolio.',
  reasoningStatement: 'Spreadsheets hold data. Compound Income OS keeps the reasoning.',
  reasoningStatementFull: 'Numbers change. Context compounds. Keep the story behind the numbers.',
  notAdviceLine: 'Framework only · not allocation advice.',
  privacyLine: 'Local view only · Read-only · No cloud',
  syntheticDemoPill: 'SYNTHETIC DEMO VALUES',
  ctaSamplePrimary: 'Open sample review packet',
  ctaSampleShort: 'Open sample',
  ctaSeeWorkflow: 'See how it works',
  ctaEarlyAccess: 'Request early access',  // nur in Manifesto-Access-Card, NICHT als Hero
}
```

### F.4 Implementation-Reihenfolge (P0 → P3)

| Wave | Scope | Dateien | Aufwand |
|---|---|---|---|
| **P0** | Microcopy-Pass auf alle 6 Pages: 7 Status-Pill-Fixes, 4 CTA-Konsistenz-Fixes, 3 Date-Sync-Fixes | `App.jsx` (alle 6 Page-Komponenten), `siteConfig.js` (neue `copy`-Sektion) | S |
| **P1** | Sleeve-Color-System als CSS-Variablen + Portfolio-Page-Komponenten | `landing.css` (neue 4 Variablen), `App.jsx` (`<SleeveBadge>` + Portfolio-Page-Refactor) | M |
| **P2** | Komponenten-Extraktion: `<DarkProductPanel>`, `<StatusPill>`, `<KPITile>`, `<ReviewPacketCard>`, `<AttentionQueueRow>` | neue Komponenten-Files unter `src/components/` (oder inline in `App.jsx` falls bestehende Konvention) | M–L |
| **P3** | Visual-Patches: Workflow-Stage-Icons in Schwarz, Dashboard-Visualisierungs-Reduktion, Slogan-Bar-Kürzung | `App.jsx` punktuell | S |

**Vor jedem Patch:**
- Git-Status prüfen (ist die Datei bereits dirty?)
- Bestehende Komponenten-Konvention im Repo prüfen (inline vs. separate files)
- Screenshot-Script-Routes verifizieren (Dashboard-Screenshot-Coverage aus letztem QA-Patch).

### F.5 Was deferred wird

- **Mobile-Responsive-Spezifika** (kein Briefing-Punkt für diese Runde).
- **i18n / DE-Variante** (nicht Scope).
- **Animation / Microinteractions** (zu früh).
- **A/B-Test-Infrastructure** (zu früh).
- **Analytics-Integration** (Public-Launch-Blocker).
- **Echte Imprint / Privacy / Pricing** (Public-Launch-Blocker).
- **Echte CTA-Targets** (Public-Launch-Blocker, ENV-basiert wie bisher).

### F.6 Vor Coding zu prüfen

1. **Ist `App.jsx` bereits dirty?** Aktueller Repo-Stand zeigt `M App.jsx`-Treffer in vorherigen Runs — vor Beginn `git diff` lesen.
2. **Existieren die 4 Sleeve-Farben bereits als CSS-Variablen** oder werden sie neu eingeführt?
3. **Welche Komponenten existieren schon inline** in `App.jsx` (z. B. `<Pill>`, `<SmartLink>`, `<SloganBar>`, `<Footer>`)? Diese nicht duplizieren.
4. **Welche Headlines sind in `siteConfig.tagline`** vs. inline in `App.jsx`? Bei der Copy-Extraktion nicht doppelt halten.
5. **Screenshot-Script aktualisieren** auf 6 Pages (nicht 7), Dashboard-Page einbeziehen — laut letztem QA-Run war `/dashboard` nicht abgedeckt.

---

## G. FINAL RECOMMENDATION

**Option 2: One more microcopy-only iteration.**

Begründung:
- Visuell ist die Direction sauber, der Pivot von „One decision a month" zu Review-OS hat alles offene strategische Issue gelöst.
- Compliance-Risiken sind klein und ausschließlich in 7 Status-Pill- und CTA-Wordings konzentriert.
- Visuelle Inkonsistenzen (Workflow-Icon-Farbe, Dashboard-Visualisierungs-Dichte, Slogan-Bar-Länge) sind im selben Patch lösbar wie die Microcopy-Korrekturen.
- Eine zweite Visual-Round wäre Overinvestment; eine vollständige Repositionierung wäre unbegründet.

**Konkrete Sequenz für die Microcopy-Iteration:**

1. **Status-Pill-Sprache vereinheitlichen** (Briefing-konform): `NEEDS REVIEW → REVIEW`, `TOO EARLY → NOT_APPLICABLE`.
2. **CTA-Sprache vereinheitlichen**: Header durchgehend `Open sample`, Hero durchgehend `Open sample review packet`, Manifesto-Hero auf gleiche Form (statt `Get early access`).
3. **Within-range-Pill** in Default-Zustand der Attention-Queue weglassen.
4. **YTD-Demo-Wert** auf neutral wechseln (statt `-0.42%`).
5. **Date-Drift** zwischen Home (May 2026) und Workflow (Apr 2026) synchronisieren.
6. **Trust-Box** auf Dashboard positiv reformulieren.
7. **Slogan-Bar** auf 4 Items kürzen.
8. **Workflow-Stage-Icons** in Ink/Schwarz statt Blau.
9. **Dashboard-Visualisierungstypen** auf 2 Typen reduzieren.
10. **Doppelung** Workflow Review Flow vs. Stage Cards auflösen.

Diese 10 Punkte sind **eine Patch-Welle**, nicht zehn separate Iterationen. Aufwand insgesamt ~3–5 Stunden, kein neuer Komponenten-Code, keine neuen Pages, keine Strategy-Änderungen.

**Nach diesem Microcopy-Pass:** Freigabe zur Implementation.

---

*Review erstellt auf Basis der 6 hochgeladenen Mockup-Bilder (Wave 5) und des bestätigten Repo-Stands `71624cb`. Keine Codeänderungen, keine Spec-Erweiterung — nur Audit gegen das Briefing.*

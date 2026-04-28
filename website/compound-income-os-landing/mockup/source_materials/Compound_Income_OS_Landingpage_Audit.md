# Compound Income OS — Landingpage Audit

**Scope:** Analyse basiert auf dem im Handoff-ZIP enthaltenen Quellcode (`src/App.jsx`, `src/siteConfig.js`) und den deterministischen Review-Screenshots (`review_screenshots/01_…`–`06_…`). Diese repräsentieren den Renderzustand unter `http://127.0.0.1:5173/#top`. Keine Codeänderungen; ausschließlich strategische Bewertung.

**Sichtbare Hauptsektionen (in dieser Reihenfolge):**
Header → Hero → Dashboard Preview → Problem → Solution → Product Principles → Monthly Workflow → Core Features → Dividend Snowball → SEC Evidence + Data Quality Gates → Decision Journal + Audience → Access (4 Karten) → Final CTA → Footer mit Disclaimer.

---

## A. EXECUTIVE VERDICT

Die Seite ist visuell ruhig, typografisch stark und tonal seriös — sie passt zur Markenhaltung „kein Trading, kein Hype". Damit ist sie eine der wenigen Investor-SaaS-Seiten, die *nicht* mit Lambo-Charts und Buttons in Neon arbeiten. Genau dieser Premium-/Anti-Hype-Ton ist die Hauptstärke und der einzige Grund, warum die Seite überhaupt schon vorzeigbar ist.

Gleichzeitig ist sie **unterverkauft, übertechnisch und zu defensiv**. Die Hero-Headline „A local operating system for long-term investing." sagt die Kategorie, aber nicht das Ergebnis. Die Subline ist eine Feature-Liste mit drei Negativ-Aussagen („Local-first. No broker execution. Not investment advice."), bevor der erste Nutzen genannt wurde. Der Demo-Dashboard im Hero zeigt fast ausschließlich gelbe `PARTIAL`- und blaue `REVIEW`-Pills — was intellektuell gemeint ist („wir verstecken Lücken nicht"), aber für einen ersten Besucher wie *unfertige Software* aussieht.

- **Hauptstärke:** Premium-, Anti-Hype-, Engineer-Trust-Ton. Typografie, Farbpalette (Paper/Ink/Gold), die Idee „Decision Journal" und das Versprechen Local-first / Privacy-first / No broker — das ist ein eigenständiges, glaubwürdiges Brand-Territorium.
- **Hauptschwäche:** Die Seite verkauft den **Prozess**, nicht das **Ergebnis**. Es fehlt eine Outcome-Story. Der Leser erfährt nicht, was sich nach 3, 6, 12 Monaten Nutzung in seinem Portfolio-Leben ändert.
- **Größte Conversion-Bremse:** Die Hero-Dashboard-Demo voller `PARTIAL`/`REVIEW`/`MISSING_DATA`-Pills. Sie liest sich wie ein Bug-Report, nicht wie ein Demo-Asset. Plus: keine Preise, keine Beweise, alle CTAs zeigen auf `mailto:early-access@example.invalid` (Platzhalter — die Seite ist technisch noch nicht für externe Empfänger ready).
- **Größter strategischer Hebel:** Der Footer-Final-CTA-Satz **„Start with the workflow, not the trade."** ist der beste Satz auf der ganzen Seite und gehört nach **oben**. Er trägt mehr Differenzierung als die aktuelle Hero-Headline.

Verdict in einem Satz: **Inhaltlich seriös, optisch premium, strategisch zu zurückhaltend — bereit für eine 1:1-Demo, aber nicht für einen offenen Handoff oder Public Launch.**

---

## B. SCORECARD

| Kategorie | Score | Begründung | Wichtigste Verbesserung |
|---|---:|---|---|
| Above-the-fold Klarheit | 5/10 | Headline beschreibt Kategorie, kein Outcome. „A local operating system for long-term investing." ist abstrakt. | Outcome- oder Mechanik-getriebene Headline (siehe Section I). |
| Value Proposition | 4/10 | Subline = Feature-Aufzählung („broker exports, fundamentals, evidence files into reproducible rankings…"). Nutzen muss man selbst übersetzen. | Eine konkrete Vorher/Nachher-Aussage in der Subline. |
| Zielgruppen-Fit | 5/10 | Audience-Card existiert, ist aber tief vergraben („Decision Journal" Section). Im Hero kein Signal „für mich". Sprache schließt Nicht-Engineers tendenziell aus. | Audience-Signal im Eyebrow oder direkt unter der Subline. |
| Differenzierung | 5/10 | „Local-first / no broker / no cloud" ist differenzierend, aber abstrakt. Es gibt keinen direkten Vergleich gegen Excel, Sharesight, Yahoo Finance, Broker-Dashboards. | Eine sichtbare „Why not Excel / why not a tracker"-Section. |
| Trust & Proof | 3/10 | Null Sozialproof, keine Founder-Note, keine echten Reports zum Download, keine Zitate, keine Logos, kein „as featured in". Nur synthetische Demo-Werte. | Mindestens ein Sample-Report (PDF/MD) zum echten Download und/oder eine Founder-Manifest-Section. |
| Funnel-Führung | 4/10 | Drei CTAs („Join Early Access", „Request GitHub Access", „Request Setup Service") konkurrieren. Keine Mikro-Conversion (Newsletter, Sample-Report). Alle Links → `mailto:` Platzhalter. | Eine klare Primär-CTA + eine niedrigschwellige Mikro-Conversion. |
| CTA-Strategie | 4/10 | „Join Early Access" erscheint 5+ mal mit identischer Bezeichnung. Keine Hierarchie zwischen Primary und Secondary über die Seite hinweg. | Primär-CTA durchgängig identisch, Sekundär-CTA visuell klar untergeordnet. |
| Lesbarkeit | 7/10 | Typografie und Whitespace sind exzellent. Aber Vokabular („manifest", „evidence-applied master", „INSUFFICIENT_INPUTS") ist Engineer-Slang. | Glossar-Hinweis oder Klartext-Übersetzung neben den Status-Pills. |
| Psychologischer Aufbau | 5/10 | Problem → Solution → Principles → Workflow → Features ist eine valide Struktur, aber emotional flach. Kein „Was du fühlst, nachdem du das benutzt" Moment. | Eine Outcome-/Vorher-Nachher-Section vor dem Final-CTA. |
| Retention-/Ecosystem-Story | 4/10 | „Monthly workflow" ist sichtbar, aber als Prozess-Diagramm — nicht als Erlebnis. Decision Journal als Code-Block ist zu abstrakt. Kein Bild davon, wie sich die Library aus 12, 24, 36 Monatsentscheidungen aufbaut. | Eine „After 12 months, you have…"-Section mit Screenshot eines wachsenden Decision-Archivs. |
| Premium-SaaS-Wirkung | 8/10 | Paper-/Ink-/Gold-Palette, dunkles Dashboard-Panel, klare Typo, kein Stockfoto-Kitsch. Wirkt wie Linear / Things / Wise. | Konsistenter halten: weniger Status-Pill-Lärm im Hero-Demo. |
| Mobile/Responsive Eindruck | 7/10 | Mobile Hero (Screenshot 03) ist sauber, Headline atmet, Buttons stapeln korrekt. Hero-Dashboard rutscht aber unter den Fold. | Mobile sollte oberhalb des Folds einen kompakteren visuellen Beweis liefern (kleine KPI-Pillenreihe statt voller Dark-Panel). |

**Gesamtscore: 5.1 / 10** — solides, aber unterverkauftes Premium-Prototyp-Niveau. Nicht bereit für Public, gut genug für eine kleine, kommentierte Vorab-Demo-Runde.

---

## C. SECTION-BY-SECTION REVIEW

### 1) Header / Navigation

**Aktueller Zustand:** Wordmark links, Nav-Items „Product · Workflow · Evidence · Access", rechts „Request GitHub Access" + „Join Early Access".

- **Funktioniert:** Sticky-Header mit Backdrop-Blur, gute Premium-Anmutung; klare 4-Punkt-Navigation.
- **Funktioniert nicht:** Beide Header-CTAs konkurrieren visuell stark. „Request GitHub Access" suggeriert Repo-Zugang ist nahe — der Button führt aber an ein `mailto:`-Postfach. Falsches Versprechen.
- **Fehlt:** Es gibt keinen „Sample Report"-, „Demo"-, oder „Pricing"-Link in der Nav. „Access" ist semantisch unklar — Pricing? Login? Beta?
- **Verbesserung:** Header-CTA reduzieren auf einen einzigen Primär-Button („Get Early Access" o. Ä.) plus textlicher Sekundär-Link „GitHub". Nav umbenennen in „Workflow · Evidence · Pricing · GitHub".

### 2) Hero

**Aktueller Zustand:**
- Eyebrow: `LOCAL-FIRST PORTFOLIO RESEARCH`
- H1: `A local operating system for long-term investing.`
- Sub: `Compound Income OS turns your broker exports, fundamentals, and evidence files into reproducible rankings, dashboards, and monthly decision reports. Local-first. No broker execution. Not investment advice.`
- Microcopy: `Open-source core. No cloud account required. Not investment advice.`
- Meta-Strip: `Mode: Local files / Outputs: CSV / Markdown / Broker: No connection`
- Visual: dunkles Mini-Dashboard, 4 KPIs, Chart, „synthetic demo values"-Pill.

- **Funktioniert:** Typo, Komposition, dass das visuelle Element kein Stockfoto ist. „Open-source core" als Anker-Microcopy ist stark.
- **Funktioniert nicht:**
  - **Headline ist eine Kategorie, kein Versprechen.** „Operating system for long-term investing" — okay, aber *was tut es für mich?* Tools wie Linear, Notion, Things beschreiben sich nicht so abstrakt; sie nennen einen konkreten Mechanik-Vorteil.
  - **Subline ist eine Feature-Aufzählung.** Drei Substantive verkettet, dann drei Negativ-Aussagen. Defensive Sprache (`No broker execution`, `Not investment advice`) gehört in den Footer-Disclaimer, nicht als drittes, viertes Wort der Wertversprechung.
  - **Microcopy wiederholt „Not investment advice"** unmittelbar darunter — dreifache Disclaimer-Last in einer Sektion. Das untergräbt Selbstvertrauen.
  - **„Mode / Outputs / Broker" Strip** ist schön gesetzt, aber inhaltlich fast eine Wiederholung der Subline. Whitespace-Verschwendung, kein Mehrwert.
- **Fehlt:**
  - Soziale Hinweise (z. B. „From dividend-growth investors who used to work in spreadsheets" oder vergleichbar).
  - Ein konkreter Outcome-Anker („Make one defensible monthly decision instead of fifteen Excel tabs.").
  - Sichtbarer Mikro-Conversion-Pfad (z. B. „See a real monthly report" → öffnet Sample-MD).
- **Verbesserung:** Siehe Section I für Headline-Alternativen.

### 3) Hero-Dashboard-Preview (rechts vom Hero)

**Aktueller Zustand:** 4 KPIs (Portfolio Value `€128,420 · OK`, Data Quality `PARTIAL`, Monthly Candidate `REVIEW`, Dividend Income TTM `€3,240 · PARTIAL`) + Compact-Chart „Dividend income scenario · Not a forecast." + Pill „synthetic demo values".

- **Funktioniert:** Dunkles Panel ist visuell distinktiv und passt zur Marke. Chart ist ruhig.
- **Funktioniert nicht:** **Drei von vier KPIs sind im Warnzustand.** Für einen Erstbesucher liest sich das wie *„diese Software funktioniert nicht / hat keine Daten"*. Die Intention („wir zeigen Lücken offen") ist intellektuell richtig, aber kommunikativ falsch im allerersten visuellen Eindruck.
- **Fehlt:** Ein KPI mit klarem `OK`/Erfolg-State, der die Software *kompetent* statt *unfertig* aussehen lässt.
- **Verbesserung:** Im Hero-Demo bewusst eine **gemischte, aber überwiegend grüne** Demo-Konfiguration zeigen: 3× `OK`, 1× `REVIEW`. Das volle Lückenpanorama gehört in die untere `EvidenceAndQuality`-Section, wo der Leser den Kontext „Missing data stays explicit" bereits gelesen hat.

### 4) Full Dashboard Preview

**Aktueller Zustand:** 10 KPIs in dark panel, davon ca. 7 mit `PARTIAL`/`REVIEW`/`PARTIAL`-Status. „Subtle chart area €3,240 TTM dividend income · Illustrative line from synthetic demo values. Not a forecast." Source/Manifest-Indikatoren rechts (`personal_run_manifest.json`, `EVIDENCE_APPLIED`, `monthly_decision_report.md`).

- **Funktioniert:** Layout ist klar und scanbar; Manifest-Sidebar ist eine schöne Authority-Geste für Engineering-Käufer.
- **Funktioniert nicht:** Wieder dieselbe Pill-Lärm-Logik wie im Hero. „Review Flags: 6 — Open artifacts" ist unklar — sind 6 Flags gut, schlecht, normal? **Keine Tooltip-Erklärung sichtbar.** „Valuation Band: Fair / Watch — REVIEW" ist semantisch widersprüchlich für Laien.
- **Fehlt:** Ein **Beispiel-Report-Link** unter dem Dashboard („Open this run's monthly_decision_report.md →"). Aktuell ist das Markdown-Artifact erwähnt, aber nicht klickbar.
- **Verbesserung:** Mindestens ein KPI sollte „grün und konkret" sein (z. B. `Dividend Growth 5Y · 7.8%` mit `OK`-Pill). Status-Legende als kleine Footnote unter dem Panel.

### 5) Problem („Where long-term portfolios actually fail.")

**Aktueller Zustand:** Drei Karten: Data drift / Evidence gaps / Process loss.

- **Funktioniert:** Headline ist die zweitstärkste der ganzen Seite. „Where long-term portfolios actually fail" hat Härte.
- **Funktioniert nicht:** Die drei Probleme sind **prozesszentriert**, nicht *nutzererlebniszentriert*. „Data drift" ist die Sprache des Software-Architekten, nicht des Investors. Der echte Schmerz heißt: *„Ich habe diesen Monat das Gefühl, meine Entscheidung hängt von 5 verschiedenen Excel-Tabellen ab, die ich vor 3 Monaten zuletzt aufgemacht habe."*
- **Fehlt:** Eine Kontrastsektion „Symptoms you'll recognize": konkrete, namentlich genannte Frustrationen (Excel-Tabs, vergessener Watchlist-Eintrag, vergessenes Reasoning eines Kaufs vor 18 Monaten).
- **Verbesserung:** Karten umbenennen auf user-side: **„The watchlist that no one updated", „The KPI that was actually missing", „The decision you can't reconstruct".** Gleiche Idee, aber emotional zugänglich.

### 6) Solution („The portfolio as local infrastructure.")

**Aktueller Zustand:** Eine Headline + Lede, sonst nichts.

- **Funktioniert:** Headline ist konzeptionell stark.
- **Funktioniert nicht:** **Die Section ist visuell leer.** Kein Bild, keine Karten, kein Diagramm, kein Vorher/Nachher. Sie wirkt wie ein Übergangs-Slot.
- **Fehlt:** Eine schlanke „Before vs After"-Komposition: links zerstreute Files (Excel, PDF, E-Mail, Broker-CSV), rechts ein lokales OS mit klarem Output (CSV, MD, Dashboard, Journal).
- **Verbesserung:** Diese Section ist im aktuellen Zustand verzichtbar. Entweder ausbauen (ein einfaches SVG-Schema reicht) oder mit „Problem" zusammenführen.

### 7) Product Principles („Architecture-level guardrails, not marketing slogans.")

**Aktueller Zustand:** 6 Karten: Local-first, Privacy-first, No cloud lock-in, No broker execution, Evidence-only, Reproducible reports.

- **Funktioniert:** Diese Section ist das *Markenherz* der Seite. Sechs scharfe, wiederholbare Prinzipien. Sehr stark.
- **Funktioniert nicht:** „No broker execution" ist eher ein **Disclaimer als ein Prinzip**. Es wiederholt eine Aussage aus Hero und Footer und schwächt die Liste. Die übrigen 5 Prinzipien sind asymmetrisch zu „No broker execution".
- **Fehlt:** Ein **Prinzip 7**, das den Kompounder-Mindset adressiert: z. B. „Slow enough to think" oder „Monthly cadence over daily noise". Aktuell sind 6/6 Prinzipien Engineering-Tugenden, 0/6 Investor-Tugenden.
- **Verbesserung:** „No broker execution" entfernen oder zu einer Karte „Decisions, not orders" umwandeln, die positiver formuliert ist.

### 8) Monthly Workflow („Six stages from input files to decision journal.")

**Aktueller Zustand:** 6 Karten: Broker export in / Data quality check / Scoring & ranking / Dividend impact / Monthly decision report / Decision journal.

- **Funktioniert:** Konzeptionell die wichtigste Section der Seite — sie zeigt, dass dies ein **wiederkehrendes** OS ist, kein Einmalwerkzeug. Das ist Kerndifferenzierung.
- **Funktioniert nicht:** Visuell sind es **6 gleichförmige Karten**, kein Pfeilfluss, kein Zyklus. Die Wiederholung des Prozesses (jeden Monat erneut) ist nicht visuell codiert. Der Leser sieht 6 Schritte und nicht „dies wiederholt sich Monat 1, Monat 2, Monat 3 …".
- **Fehlt:** Ein **Loop-Diagramm** oder eine Mini-Zeitachse, die zeigt, wie aus den 6 Schritten ein Archiv wird.
- **Verbesserung:** Die Schritte 5 und 6 (Monthly Decision Report → Decision Journal) sollten visuell als „Output, der bleibt" markiert sein. Idealerweise ein 7. visueller Block: „Archive grows month by month".

### 9) Core Features („One local pipeline. Eleven ways to inspect the evidence.")

**Aktueller Zustand:** 11 gleich gestaltete Karten: Portfolio Snapshot / SEC Evidence Pipeline / Evidence-Applied Fundamentals / Data Quality Gates / Watchlist Ranking / Monthly Ranking / Dividend Snowball / Valuation Bands / Monthly Decision Report / Decision Journal / Local Dashboard.

- **Funktioniert:** Headline ist klever („One … eleven …" — gut). Symmetrische Optik.
- **Funktioniert nicht:** **11 Karten ist zu viel.** Der Leser overflood. Manche Karten überlappen inhaltlich erheblich (z. B. „Watchlist Ranking" + „Monthly Ranking", „Monthly Decision Report" + „Decision Journal", „Evidence-Applied Fundamentals" + „SEC Evidence Pipeline"). Die Section liest sich wie eine `features.csv`, nicht wie eine kuratierte Story.
- **Fehlt:** **Hierarchie.** Welche 3 Features sind die Hauptfunktionen, welche sind Hilfsfunktionen? Aktuell visuell flach.
- **Verbesserung:** Auf **3 Hauptmodule + 5 Sub-Features** reduzieren. Vorschlag:
  - Hauptmodule: **Watchlist & Ranking** / **Monthly Decision Report** / **Decision Journal & Dashboard**.
  - Darunter kleiner: SEC Evidence, Data Quality Gates, Valuation Bands, Snowball, Portfolio Snapshot.

### 10) Dividend Snowball

**Aktueller Zustand:** Headline „A scenario surface for income assumptions." + 4 KPIs + gold-line Chart + Disclaimer-Pill „Illustrative calculation. Not a forecast."

- **Funktioniert:** Visuell die schönste Section der Seite. Goldener Chart-Stroke ist die einzige farbliche „Wärme" und passt thematisch zu „Income". Die Anti-Forecast-Pill ist intellektuell ehrlich.
- **Funktioniert nicht:** **„A scenario surface for income assumptions."** ist eine zu akademische Headline für eine emotionale Funktion. Snowball-Charts sind *die* emotionale Investorensehnsucht — die Headline löscht das Gefühl.
- **Fehlt:** Eingabefelder oder zumindest sichtbare Annahmen-Achsen (z. B. „at 7% dividend growth, €300/month reinvestment, 20 years"). Aktuell nur 4 statische Werte.
- **Verbesserung:** Headline emotional + ehrlich: **„See your dividend snowball, without lying to yourself."** oder „An honest snowball model. Assumptions in, scenarios out."

### 11) SEC Evidence Pipeline + Data Quality Gates (Doppelsection)

**Aktueller Zustand:** Links: „Read-only. Reviewed. Optional." Rechts: „Missing data stays explicit." Plus 7 Status-Labels (`COVERED, PARTIAL, REVIEW, NO_MATCH, MISSING_DATA, INSUFFICIENT_INPUTS, INSUFFICIENT_HISTORY`).

- **Funktioniert:** Section ist intellektuell stark und differenziert massiv vs. Yahoo Finance / Sharesight / Excel. „Missing data stays explicit" ist eine der wenigen Aussagen, die ein anspruchsvoller Investor *sofort* respektiert.
- **Funktioniert nicht:** **Sehr engineer-lastig.** „Reviewed identity inputs", „evidence registry", „research backlog", „proposed updates" — das sind Begriffe aus der Datenbank-Welt. Ein Dividend-Investor ohne Coding-Hintergrund versteht hier <50 %.
- **Fehlt:** Ein konkretes Mini-Beispiel: *„Apple's revenue field shows COVERED. Our small-cap watchlist position X shows MISSING_DATA. The system blocks X from the monthly candidate queue until you decide."* Eine Story von **3 Sätzen** würde diese Section verzehnfachen.
- **Verbesserung:** Status-Pill-Liste mit jeweils *einer* Klartext-Erklärung pro Pill ergänzen (z. B. `MISSING_DATA → field not available; not silently filled`). Alternativ ein Glossar-Tooltip.

### 12) Decision Journal + Audience (Doppelsection)

**Aktueller Zustand:** Links: Code-Block mit `run_id: DEMO-20260426-160500 / monthly_candidate: REVIEW / candidate_allocation: €300 …`. Rechts: 4 Audience-Items (Dividend-growth investors / Quality-compounder investors / Engineers, analysts, finance/data professionals / Independent operators).

- **Funktioniert:** Code-Block ist authentisches Authority-Signal für Engineer-Zielgruppe. „Independent operators" ist eine starke, eigene Identitätsbezeichnung.
- **Funktioniert nicht:**
  - **Audience-Liste ist passiv.** Keiner der vier Items hat einen erklärenden Satz. „Dividend-growth investors" — ja, und? Wofür *konkret* ist das Tool für Dividend-Growth-Investors gut?
  - **Code-Block ist undokumentiert.** Was bedeutet `valuation_data_status != OK` für einen Nicht-Coder? Das verschreckt eher als zu trösten.
- **Fehlt:** **Anti-Audience.** Wer ist es *nicht* für? Day-Trader, Krypto-Investoren, Buy-Now-Sell-Tomorrow-User. Dieser explizite Ausschluss würde die Premium-Positionierung sofort schärfen.
- **Verbesserung:** Audience-Liste auf 3 Punkte schneiden, jeden mit einem Satz versehen. Plus eine 4. Negativ-Karte „Not for: Day traders, options speculators, anyone looking for execution or hot tips."

### 13) Access (4 Karten)

**Aktueller Zustand:** Open-Source Core / Pro Modules / Setup Service / GitHub Sponsors–Early Access. Statt Preisen: „Core workflow", „Optional extensions", „Implementation help", „Support channel".

- **Funktioniert:** Vier-Spalten-Layout ist modern. Open-Source-Core als Anker ist Trust-Signal.
- **Funktioniert nicht:**
  - **Keine Preise.** Bei „Pro Modules" und „Setup Service" hätte der Leser konkrete Preisanker erwartet (€/Monat, €/Setup). Stattdessen vier Wischwasch-Begriffe.
  - **Karten 2 (Pro Modules) und 4 (GitHub Sponsors / Early Access) überlappen** — beide führen via `earlyAccess` auf dasselbe `mailto:`. De-facto eine Karte zu viel.
  - **„Open-source core" und „GitHub Sponsors / Early Access" sind beides „Repo-Pfade"** — also auch hier Redundanz.
- **Fehlt:** Echte Preisstruktur oder ehrliche „TBD"-Markierung mit Datum („Pricing announced Q3 2026").
- **Verbesserung:** Auf **3 Karten** reduzieren: (1) Open-Source Core (Free, GitHub) (2) Pro Modules (Pricing TBD oder konkreter Betrag) (3) Setup Service (Pricing on request). Die GitHub-Sponsors-Karte ist als Footer-Link besser aufgehoben.

### 14) Final CTA („Start with the workflow, not the trade.")

**Aktueller Zustand:** Dunkles Panel, Headline, Subline „Join the early access list or request repository access to review the local-first workflow.", drei Buttons (Join Early Access / Request GitHub Access / Request Setup Service).

- **Funktioniert:** **Headline ist der beste Satz der Seite.** Sie sagt in 7 Wörtern, was die Marke ausmacht.
- **Funktioniert nicht:**
  - **Drei CTAs nebeneinander** verteilen Aufmerksamkeit. Klassischer Funnel-Leak.
  - **Subline ist generisch** und wiederholt die CTA-Funktion auf Klartextebene — das ist Tautologie.
- **Fehlt:** Eine konkrete Reibungsreduktion: *„Read a real monthly_decision_report.md (3-min read)"* — eine Mikro-Conversion vor dem Mailto-Pfad.
- **Verbesserung:** Headline nach oben in den Hero. Final-CTA mit nur einem Primärbutton + einem Sekundär-Text-Link.

### 15) Footer / Disclaimer

**Aktueller Zustand:** Großer beruhigender Disclaimer-Block mit „Compound Income OS is a research and decision-support tool. It does not provide investment, tax, or legal advice…"; darunter Wordmark + „No cloud account required. Core runs locally. No broker connection."

- **Funktioniert:** Disclaimer ist sauber, vollständig, juristisch ordentlich. Trust-positiv.
- **Funktioniert nicht:** **Keine echten Footer-Links.** `privacy: 'TBD'`, `imprint: 'TBD'` (siehe `siteConfig.js`). Für deutschen Markt ein **Hard-Stopper**: ohne Impressum und Datenschutz ist die Seite nicht abmahnsicher publishable.
- **Verbesserung:** Vor jedem öffentlichen Launch zwingend Impressum und Datenschutz hinterlegen, Footer-Nav ergänzen (Imprint · Privacy · GitHub · Status).

---

## D. FUNNEL-DIAGNOSE

**Aktueller primärer Funnel:**
Hero → Hero-CTA „Join Early Access" → `mailto:early-access@example.invalid?subject=Compound%20Income%20OS%20Early%20Access`

**Aktueller sekundärer Funnel:**
Header / Final-CTA → „Request GitHub Access" → ebenfalls `mailto:` mit anderem Subject.

**Aktuelle CTA-Hierarchie (gezählt aus dem Code):**
- `Join Early Access`: 5× sichtbar (Header, Hero, Access-Karte 2, Access-Karte 4, Final-CTA)
- `Request GitHub Access`: 4× (Header, Hero, Access-Karte 1, Final-CTA)
- `Request Setup Service`: 2× (Access-Karte 3, Final-CTA)

→ Im Final-CTA stehen alle drei in einer Reihe nebeneinander. Das ist die kritischste Stelle der Seite und genau dort ist die Hierarchie *nicht* aufgelöst.

**Funnel-Leaks:**
1. **Mailto-Sackgasse.** Alle CTAs öffnen den lokalen Mail-Client. Auf mobilen Browsern ohne konfigurierten Mail-Client = Leak. Auf Desktop-Web ohne Outlook/Mail = Leak. Estimate: 30–60 % der Klicks gehen verloren.
2. **`early-access@example.invalid`** ist eine **explizite Platzhalter-Domain** (RFC 6761). Wenn dieser Build versehentlich öffentlich geht, gehen ALLE Sign-ups ins Nichts. P0.
3. **Keine Mikro-Conversion.** Es gibt keinen Newsletter-Opt-in, keinen Sample-Report-Download, keinen „See live demo"-Pfad. Wer nicht sofort einen Mailto-Klick wagt, ist verloren.
4. **Pro Modules ohne Preis.** Wer auf „Join Early Access" auf der Pro-Modules-Karte klickt, weiß nicht, ob das später 9, 49 oder 490 €/Monat kostet. Reibung.
5. **Setup Service ohne Skopus.** „Implementation help" — wie viele Stunden, welcher Preis, welcher Outcome? Reibung.

**Empfohlener idealer Funnel (P1):**

```
Hero
  → Primary CTA: "Get the Sample Monthly Report" (Mikro-Conversion → Email-Capture → MD-Datei)
  → Secondary: "Join Early Access" (Mail-Capture → Calendly oder Wartelistenseite)

Mid-page
  → Inline-CTA "See the full demo dashboard" (öffnet 02_full_dashboard_preview als Lightbox o. ähnlich)

Final
  → Single Primary: "Get Early Access"
  → Sekundär als Text-Link: "Or read the open-source workflow on GitHub"
```

Sample-Report als Mikro-Conversion ist der wichtigste Hebel: Er liefert Wert *vor* dem Commitment, ist markenkonsistent („evidence-only"), und liefert sofort eine E-Mail-Liste.

---

## E. PSYCHOLOGISCHE UX-ANALYSE

| Dimension | Bewertung | Beobachtung |
|---|---|---|
| Aufmerksamkeit | Mittel | Hero-Headline ist groß und schön gesetzt, aber semantisch leer. Auge bleibt am Dashboard-Panel hängen — und dort dominiert visuell `PARTIAL`. |
| Vertrauen | Mittel-Hoch | Architektur-Prinzipien, SEC-Pipeline, Disclaimer = stark. Fehlende Founder-Note, fehlende echte User-Stimmen = schwach. |
| Motivation | Niedrig | Kein einziger Satz beantwortet „Warum *jetzt* einsteigen?" Keine Knappheits-Heuristik (außer „Early Access", was ohne Liste leer ist). Kein Outcome-Bild („In 6 Monaten hast du …"). |
| Risikoabbau | Hoch | „Local-first / no broker / not investment advice / synthetic demo values" — Risikoabbau ist *übererfüllt* und schlägt teilweise in Defensivität um. |
| Konkrete Nutzenbilder | Niedrig | Es gibt **kein** „Tag im Leben"-Bild, **keine** Vorher/Nachher-Story, **kein** „mein Portfolio nach 12 Monaten OS"-Beispiel. |
| Daten-/Evidence-Vertrauen | Hoch | Die Status-Gates und der SEC-CompanyFacts-Pfad sind ein starkes Authority-Signal — ehrlicher als 90 % der Tracker-Konkurrenz. |
| Emotionale Spannung ohne Hype | Niedrig-Mittel | Der ruhige Ton ist richtig, aber die Seite **schwingt zu wenig**. Sie ist mehr „white paper" als „you should try this". Die Marke verträgt 1 stilles Ausrufezeichen. |

**Cognitive-Load-Diagnose:** Hoch im Mittelteil. 6 Prinzipien + 6 Workflow-Schritte + 11 Core Features + SEC-Pipeline + Data-Quality-Gates + Decision-Journal-Code-Block = der Leser bekommt **>30 sekundär gleich gewichtete Items** zwischen Problem und Access. Reduktion auf ca. 18–20 wäre besser.

---

## F. MARKETING-POSITIONIERUNG

**Aktuelle wahrgenommene Positionierung (auf Basis der Seite):**
„Ein lokales, datenehrliches Tool für anspruchsvolle Privatanleger, die Excel überwunden haben und ihre monatlichen Investmententscheidungen reproduzierbar dokumentieren wollen."

→ Korrekt, aber zu lang und zu intern. Liest sich wie eine Selbstbeschreibung, nicht wie eine Kampfansage gegenüber Excel/Tracker.

**Bessere Positionierung in einem Satz:**
> **Compound Income OS ist das ruhige Operating System für eine Investmententscheidung pro Monat — lokal, evidenzbasiert, ohne Broker, ohne Cloud, ohne Lärm.**

**Bessere Kategoriebezeichnung — drei Optionen:**
1. **Monthly Decision OS** — fokussiert auf den Kern-Rhythmus.
2. **Dividend Growth Research OS** — fokussiert auf Zielgruppe.
3. **Local Portfolio Operating System** — fokussiert auf Privacy/Local-first-Differenzierung.

Aktuell verwendet die Seite *Local-first portfolio research*, was schwächer ist als alle drei.

**3 alternative Hero-Headlines (je mit anderem Schwerpunkt):**

| # | Headline | Schwerpunkt |
|---|---|---|
| 1 | **One defensible investment decision a month. Locally. With evidence.** | Outcome + Rhythmus + Trust |
| 2 | **Stop running your portfolio out of seven Excel tabs.** | Konkurrenz/Schmerz |
| 3 | **The quiet operating system for long-term compounders.** | Markenton + Identität |

**3 alternative Subheadlines:**
1. „Compound Income OS turns your broker exports, fundamentals, and SEC evidence into one reproducible monthly decision report. **No broker. No cloud. No noise.**"
2. „A local-first research workflow that ranks, scores, and journals every monthly investment decision — and shows the data gaps you'd otherwise have hidden."
3. „From scattered spreadsheets to a deterministic monthly decision report — without ever connecting your broker."

**3 CTA-Varianten (statt aktuell „Join Early Access"):**
1. **„Get the sample monthly report"** (Mikro-Conversion, hochwirksam, markenkonsistent)
2. **„See a real monthly run"** (Demo-Tonalität, niedrige Reibung)
3. **„Get early access"** (klassisch — wenn nichts anderes verfügbar, dann zumindest kürzer als „Join Early Access")

---

## G. RETENTION & ECOSYSTEM REVIEW

**Aktuelle Vermittlung des wiederkehrenden Charakters:**

| Element | Sichtbar? | Stärke |
|---|---|---|
| Monatlicher Workflow | Ja, als 6-Stufen-Diagramm | Mittel — als Schritte, nicht als Zyklus dargestellt |
| Portfolio-Review-Zyklus | Indirekt (KPI „Review Flags") | Schwach |
| Watchlist-Zyklus | Erwähnt in Core Features | Schwach |
| Fundamentals-Coverage | SEC-Pipeline-Section | Stark |
| Dividend-/Compounding-Verlauf | Snowball-Section | Mittel |
| Entscheidungsarchiv | Decision-Journal-Code-Block | Mittel — aber als Einzelrun, nicht als Archiv |
| Dashboard-Nutzung | Dashboard-Preview-Section | Stark visuell, aber statisch |
| Handoff-/Export-Vertrauen | „CSV/Markdown" Microcopy | Stark technisch, schwach erzählerisch |

**Kernproblem:** Die Seite zeigt **eine** Monatsiteration. Sie zeigt **nicht**, wie aus 12 Iterationen ein Vermögensaufbau-Archiv wird. Das ist die Retention-Story, die fehlt.

**Konkrete Section-Vorschläge zum Ergänzen:**

1. **„Month 1, Month 6, Month 12"-Section.** Drei Mini-Screenshots (synthetisch) eines Decision-Journal-Folders, der über Zeit wächst. Visualisiert „dies ist ein OS, kein One-Off".

2. **„The Archive that Compounds"-Section.** Eine ruhige Section nach dem Workflow, die zeigt, wie sich `monthly_decision_report.md` über Monate sammelt. „Year 1 ends with 12 reproducible reports, 12 journal entries, and a decision history you can audit yourself."

3. **„Cadence over Drama"-Section.** Direktes Anti-Trading-Statement: „This system is built for one decision per month. Daily noise is by design out of scope." Stärkt Marke + verdrängt die falsche Zielgruppe.

4. **Optional: Founder-Manifest.** Ein 200-Wort-Block, signiert, was den emotionalen Anker liefert, der sonst überall fehlt. Dies ist der einfachste Weg, die Seite menschlicher zu machen, ohne den Premium-Ton zu verlieren.

---

## H. PRIORISIERTER VERBESSERUNGSPLAN

### P0 — Muss vor *jeder* externen Weitergabe verbessert werden

| # | Problem | Warum es wichtig ist | Konkrete Änderung | Erwarteter Effekt |
|---|---|---|---|---|
| P0.1 | Alle CTAs zeigen auf `mailto:early-access@example.invalid` (RFC-Platzhalter-Domain). | Wenn dieser Build versehentlich publik geht, sind 100 % aller Sign-ups verloren. Marken-Risiko. | Echte E-Mail oder Wartelisten-URL (z. B. EmailOctopus, Notion-Form, Tally) in `siteConfig.js`. | Funktionsfähiger Funnel. |
| P0.2 | Kein Impressum, keine Datenschutzerklärung (`privacy: 'TBD'`, `imprint: 'TBD'` im siteConfig). | DE/EU rechtliche Anforderung. Ohne diese darf die Seite nicht öffentlich. | Beide Seiten anlegen + im Footer verlinken. | Rechtssicherheit. |
| P0.3 | Hero-Dashboard zeigt 3/4 KPIs als `PARTIAL`/`REVIEW`. | Erster Eindruck = „diese Software ist unfertig". Direkter Conversion-Killer. | Demo-Konfiguration auf 3× `OK` + 1× `REVIEW` ändern. | Höhere Above-the-fold-Glaubwürdigkeit. |
| P0.4 | „Pro Modules" und „Setup Service" haben keinen Preis und keinen Skopus. | Sales-Reibung. Macht Access-Sektion wirkungslos. | Entweder konkrete Preise oder ehrliches „Pricing announced [Datum]". | Klarere Conversion-Pfade. |

### P1 — Starker Conversion-Hebel

| # | Problem | Warum es wichtig ist | Konkrete Änderung | Erwarteter Effekt |
|---|---|---|---|---|
| P1.1 | Hero-Headline beschreibt Kategorie, nicht Outcome. | Die wichtigste 1,5 Sekunden der Seite. | Auf eine der 3 alternativen Headlines wechseln (siehe F). | +30–50 % Above-the-fold-Engagement (Heuristik). |
| P1.2 | Keine Mikro-Conversion. Alles geht direkt auf Mailto. | 80–90 % der Besucher klicken keinen primären CTA. Mikro-Conversion fängt diese auf. | „Get the sample monthly report"-Form (E-Mail in, MD-Datei out). | E-Mail-Liste wächst, Conversion-Funnel wird messbar. |
| P1.3 | Zu viele identische CTAs (5× „Join Early Access"). | Auswahlparalyse. Verwässert Hierarchie. | Primär-CTA durchgängig identisch (1 Wording, 1 Farbe). Sekundärer als Textlink, nicht als Button. | Klare Hierarchie. |
| P1.4 | „Final CTA"-Headline „Start with the workflow, not the trade." ist im Footer versteckt. | Bester Satz der Seite — steht an der schwächsten Position. | In den Hero hochziehen oder als Eyebrow zum Hero verwenden. | Sofortige Markenklarheit. |
| P1.5 | Core Features = 11 Karten, ohne Hierarchie. | Cognitive Overload. | Reduktion auf 3 Hauptmodule + 5 Sub-Features. | Bessere Scanbarkeit. |
| P1.6 | Kein direkter Vergleich gegen Excel / Tracker / Broker-Dashboards. | Die Zielgruppe vergleicht aktiv. Wenn die Seite den Vergleich nicht macht, macht sie ihn falsch. | „Why not Excel? Why not a tracker?"-Section mit 3 ehrlichen Argumenten. | Stärkere Differenzierung. |
| P1.7 | Audience-Section ohne Erklärung, kein „Anti-Audience". | Schärfe = Conversion. | 3 Audience-Items mit je 1 Satz + 1 negative Karte „Not for…". | Klarere Selbstidentifikation. |

### P2 — Nice-to-have / spätere Optimierung

| # | Problem | Konkrete Änderung |
|---|---|---|
| P2.1 | „Solution"-Section ist visuell leer. | Vorher/Nachher-SVG (Excel-Chaos → CIO Pipeline). |
| P2.2 | Workflow als 6 Karten, ohne Zyklus-Visualisierung. | Loop-Pfeil oder Zeitachse einfügen. |
| P2.3 | Fehlendes „Month 1 / 6 / 12"-Bild. | Drei Mini-Screenshots eines wachsenden Archivs. |
| P2.4 | SEC-Section zu engineer-lastig. | Klartext-Tooltips bei Status-Pills. |
| P2.5 | Keine Founder-Note / kein Manifest. | 200-Wort-Block am Ende der Seite, signiert. |
| P2.6 | Nav-Punkt „Access" ist semantisch unklar. | Umbenennen in „Pricing" oder „Get Started". |
| P2.7 | Mobile-Hero pusht Demo-Panel unter den Fold. | Kompakte 2-KPI-Pillenreihe mobil zeigen. |
| P2.8 | Disclaimer-Block sehr lang im Footer. | Auf 2 Sätze + Akkordeon „Full disclaimer" verkürzen. |

---

## I. KONKRETE COPY-VORSCHLÄGE

**Hero Headline (Primärempfehlung):**
> **One defensible investment decision a month. Locally. With evidence.**

Alternative (markentonal weicher): „The quiet operating system for long-term compounders."

**Hero Subheadline:**
> Compound Income OS turns your broker exports, fundamentals, and SEC evidence into one reproducible monthly decision report — with every data gap visible, not hidden. No broker connection. No cloud account. No noise.

**Primary CTA:**
> **Get the sample monthly report** *(Mikro-Conversion, E-Mail-Capture)*

**Secondary CTA:**
> **See the local workflow on GitHub** *(textueller Link, kein Button)*

**Trust Statement (statt Microcopy „Open-source core. No cloud account required. Not investment advice."):**
> Open-source core · Local-first · Evidence-based · No broker, no cloud, no advice.

**Problem Section (Headline + 3 Karten):**
> **Headline:** „Where long-term portfolios actually break."
>
> Karte 1: **The watchlist no one updated.** Tickers added in 2023, never reviewed since. The reasons are gone. The position is still in.
>
> Karte 2: **The KPI that was missing.** A score gets computed anyway. The decision rests on data that wasn't there. You don't notice until next quarter.
>
> Karte 3: **The decision you can't reconstruct.** „Why did I buy that?" The reasoning was in your head. It's no longer there. The position is.

**Product Workflow Section:**
> **Headline:** „One monthly cadence. Six deterministic steps. A growing archive."
>
> **Lede:** „Compound Income OS runs the same six stages every month — from broker export to decision journal — so that month 12 looks like month 1 plus eleven reproducible records."

**Dashboard / Analytics Section:**
> **Headline:** „A dashboard that shows you what's missing."
>
> **Lede:** „Every KPI carries a status. Covered, partial, review, missing — first-class outputs, not silent imputations. The portfolio is shown as it is, not as it would look pretty."

**Retention / Ecosystem Section (neu zu ergänzen):**
> **Headline:** „Month 12 is just month 1, eleven times audited."
>
> **Lede:** „Each monthly run produces one decision report, one journal entry, and one snapshot of the data state. After a year, you don't just have a portfolio — you have its decision history, locally, in your own files, in your own Markdown."

**Disclaimer / Anti-Hype Statement (kürzer als aktuell):**
> Compound Income OS is a research and decision-support tool. It is not investment advice, does not guarantee returns, and never connects to a brokerage. All values shown on this page are synthetic demo values. *(Full disclaimer →)*

---

## J. FINAL RECOMMENDATION

**1. Ist die Landingpage aktuell gut genug für eine erste private Handoff-/Demo-Runde?**
**Ja, mit zwei Auflagen:** (a) Die `mailto:early-access@example.invalid`-Platzhalter müssen durch eine reale Adresse oder eine Demo-Handoff-Notiz im Begleittext ersetzt werden. (b) Die Empfänger müssen vorab wissen, dass die Status-Pill-Lärm-Anhäufung im Hero-Demo Absicht ist. Mit diesen zwei Hinweisen ist die Seite **eine fachlich glaubwürdige, eigenständig wirkende Demo-Asset** — besser als 80 % vergleichbarer Investor-Tool-Seiten.

**2. Ist sie gut genug für öffentliche Kommunikation?**
**Nein.** Vier blockierende Gründe:
- Mailto-Platzhalter (P0.1)
- Fehlendes Impressum + Datenschutz (P0.2) — DE/EU-rechtliche Hürde
- Hero-Dashboard mit Mehrheits-Warnpills (P0.3) — Conversion-Killer
- Fehlende Preise auf zwei der vier Access-Karten (P0.4)

Plus eine semantische Hürde: Die Hero-Headline trägt die Marke aktuell nicht öffentlich. Vor Public-Launch sollte sie auf eine outcome-orientierte Variante wechseln.

**3. Die 3 wichtigsten Änderungen vor öffentlicher Veröffentlichung:**

1. **Hero-Headline + Subline auf Outcome umstellen.** Die aktuelle Variante ist zu intern. Empfehlung: „One defensible investment decision a month. Locally. With evidence." (siehe I).
2. **Mikro-Conversion einführen.** „Get the sample monthly report" als primären Hero-CTA, der eine echte MD-Datei ausliefert. Das ist der einzige Weg, eine E-Mail-Liste vor Pricing/Repo-Access aufzubauen, und ist absolut markenkonsistent.
3. **Hero-Dashboard-Demo bereinigen** (3× OK + 1× REVIEW statt 1× OK + 3× PARTIAL/REVIEW). Optional: einen klickbaren „Open this run's report"-Link unter dem Dashboard, der zu der echten Markdown-Beispieldatei führt.

**4. Was sollte bewusst NICHT geändert werden, weil es zur Marke passt:**

- **Der ruhige, anti-hype Ton.** Keine Neon-Buttons, keine „Get rich fast"-Sprache, keine Stockfotos. Diese Zurückhaltung ist Differenzierung pur.
- **Die Paper-/Ink-/Gold-Farbpalette** und die Typografie. Premium-Wirkung ist eine der höchsten Stärken der Seite.
- **Die Architecture-Principles-Section („Architecture-level guardrails, not marketing slogans.").** Markenkern, ungeschwächt lassen.
- **Die `MISSING_DATA / INSUFFICIENT_INPUTS / PARTIAL`-Status-Pill-Sprache** als Konzept (nicht aber als Hero-Demo-Konfiguration). Es ist ein echter Differenzierer gegenüber Yahoo Finance / Sharesight, die alle Lücken silently imputieren.
- **„Decision Journal" als Begriff.** Eines der wenigen Worte, das emotionalen Anker und Engineering-Klarheit verbindet. Beibehalten.
- **Disclaimer-Strenge.** Ja, sie ist defensiv — aber sie ist auch genau richtig für ein seriöses Finanzprodukt. Verkürzen ja, abschwächen nein.

**Bottom line:**
Die Marke ist da. Das Produkt-Narrativ ist da. Was fehlt, ist der **Outcome-Schwung** und der **funktionierende Funnel**. Beides ist in 1–2 Tagen Copy/Config-Arbeit machbar — keine Code-Architektur-Änderung nötig.

---
*Audit erstellt auf Basis des Handoff-ZIP-Pakets `compound_income_os_HANDOFF_20260426-201924_2c082db.zip`. Quellen: `src/App.jsx`, `src/siteConfig.js`, `review_screenshots/01_…–06_…`. Keine Codeänderungen vorgenommen.*

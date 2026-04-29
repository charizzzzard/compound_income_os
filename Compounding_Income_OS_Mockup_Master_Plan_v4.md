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
7. **SEC-Evidence-Pipeline (7 Stufen)** — EDGAR-Daten, Parsing, Evidence-Extraktion, Overlay
8. **Multi-Benchmark-Performance-Engine** — Vergleich gegen Benchmarks
9. **Cost/Tax-Ledger** — Kosten- und Steuer-Tracking
10. **Personal-Run-Orchestrator** — Manifest-gesteuerter Gesamt-Run

---

## 2. STRATEGISCHE VERZWEIGUNGEN (mit Empfehlungen)

Drei offene Brand-Fragen, die deine Mockups aufwerfen. Für jede gebe ich eine Empfehlung; finale Entscheidung liegt bei dir.

### 2.1 Markenname

**Beobachtung:** Mockups verwenden mindestens drei Namen:
- `Compound Income OS` *(aktueller Code)*
- `Operating Income OS` *(Mockups Brutalist + Editorial + Premium SaaS)*
- `COMPOUNDING INCOME` *(Hero-Mockup im Übersichtsbild oben links)*

**Empfehlung:** **In dieser Patch-Runde nicht umbenennen.** Eine Umbenennung berührt Repo-Name, GitHub-URL, Domain, Discord-Handles, alle Marketing-Assets, evtl. Markenrechte. Das ist eine eigene Entscheidung mit Vorlauf, kein Hero-Patch. *Wenn* du umbenennst, wäre `Compounding Income` der Favorit (kommunikativ wärmer, „compounding" ist das Verb, das Investoren nutzen — nicht das Substantiv).

**Was in dieser Runde passiert:** Markenname bleibt `Compound Income OS`. Die Tonalität der Mockups wird auf diesen Namen angewendet.

### 2.2 Sprache

**Empfehlung:** Marketing-Pages bleiben **Englisch** (laut letztem Briefing). Wenn DACH-Markt im Fokus ist: das wäre jetzt der Zeitpunkt für einen DE-Pivot — danach 6 Pages auf DE statt EN zu ziehen wird teuer.

### 2.3 Visuelles Treatment

Brutalismus-Lite-Visual-Patch läuft als separate Spec parallel. Nicht Teil dieser Mockup-Welle.

---

## 3. DIAGNOSE — WARUM DIE AKTUELLEN TEXTE MASCHINELL WIRKEN

Die aktuelle Hero-Headline beschreibt **das Output**, nicht **die Person, für die es gemacht ist**:

> Aktuell: *„One defensible investment decision a month."*
>
> Mockup-Varianten: *„Portfolio research for people who think for themselves."* / *„A calmer process in a louder market."* / *„Run your portfolio like a long-term income system."*

Der Unterschied ist nicht „englisch vs. deutsch". Der Unterschied ist:
- **Aktuell** spricht *über* das System (was es liefert).
- **Mockups** sprechen *zur* Person (wer du bist, was du willst, was dich nervt) **oder** geben ein konkretes Sehnsuchtsbild.

Das ist die Differenz zwischen *Spec-Sheet* und *Marketing-Voice*. Folgesymptome: Subline ist eine Kommatakette aus Engineering-Substantiven (`broker exports, fundamentals, and SEC evidence`), Trust-Zeile besteht aus Negativ-Aufzählungen (`No broker. No cloud.`), und das gesamte Mid-Page-Vokabular (`deterministic`, `evidence-applied master`, `INSUFFICIENT_INPUTS`) gehört in eine Datenbank-Doku, nicht auf eine Investor-Landingpage.

### Drei Hebel

1. **Hero-Pivot von Output zu Identität.** Headline benennt den Investor-Typ oder den emotionalen Kontrast, nicht den Pipeline-Output.
2. **Anti-Maschinen-Sprachregeln im Mid-Page.** Engineering-Vokabular wird in Investor-Klartext übersetzt. Status-Sprache (`COVERED`, `REVIEW` …) bleibt — aber lebt in der Evidence-Section, nicht im Top-of-page.
3. **Builder-Voice einführen.** Eine kleine, ehrliche „Note from the builder"-Section macht die Seite menschlich, ohne den Premium-Ton zu brechen.

---

## 4. MOCKUP-PLAN — 6 MARKETING-PAGES + 5 PRODUCT-UI-SURFACES

### Marketing-Pages (M)

| ID | Page | Kern-Story | Welle |
|---|---|---|---|
| M1 | Hero / Home Redesign | Identität + 5-Promises-Grid mit Page-Teasern | 1 |
| M2 | Workflow Page | 6-Step-Process + Report-Render | 1 |
| M3 | Evidence Page | SEC-Pipeline + Trust-Architektur | 2 |
| M4 | Philosophy Page | Builder-Voice + Investment-Prinzipien | 2 |
| M5 | Watchlist Page | Kandidaten-Status-System | 3 |
| M6 | Income Engine Page | Cashflow + Reinvest-Vergleich | 3 |

### Product-UI-Surfaces (P)

| ID | Surface | Kern-Visual | Welle |
|---|---|---|---|
| P1 | Portfolio Snapshot | Score-Grid + Status-Distribution | 2 |
| P2 | Monthly Decision Report | Markdown-Render in Browser | 1 |
| P3 | Evidence Workspace | SEC-Evidence-Overlay-View | 2 |
| P4 | Watchlist View | Kandidaten-Tabelle mit Status-Badges | 3 |
| P5 | Local Dashboard Viewer | HTTP-Server-Output im Browser | 1 |

---

## 5. WELLE 1 — ASSET-BRIEFS

### M1 — Hero / Home Redesign

**Was sich ändert:** Alle Tiefen-Sections raus. Dafür 5-Promises-Grid mit Page-Teasern. M1 wird zum **Wegweiser**, nicht zum Vollständigkeits-Anspruch.

**Hero-Option A (empfohlen):**
- H1: `A calmer process in a louder market.`
- Subline: Verb-Liste `Import / Normalize / Review / Rank / Decide / Report`
- Trust-Cluster: 6 Pills `LOCAL-FIRST · NO CLOUD · NO BROKER · READ-ONLY · MONTHLY · EVIDENCE-BASED`

**Builder-Note-Section** (neu, unterhalb Hero):
- Dunkles Panel + Wordmark als typografisches Pattern (gedimmt, nicht als Marke)
- Kurzer ehrlicher Text: „I built this because..."
- Mono-Caps-Eyebrow mit `//`-Prefix

### M2 — Workflow Page

**Kern:** 6-Step-Workflow (`Import → Score → Review → Rank → Decide → Report`) als visuelle Sequenz + P2 Report-Render als Beweis.

### P2 — Monthly Decision Report Render

**Kern:** Wie sieht der Output nach einem echten Run aus? Synthetic-Demo-Daten. Markdown-Render in Browser-Fenster-Komposition.

### P5 — Local Dashboard Viewer

**Kern:** Das einzige Visual, das die User-Frage *„Was kriege ich nach jedem Run zu sehen?"* direkt beantwortet. HTTP-Server-Output, dark panel, real-looking data (synthetic).

---

## 6. VISUELLE ELEMENTE — WAS ÜBERNOMMEN WIRD

**✅ Übernommen aus Mockups:**
- Tonalität `A calmer process in a louder market` → Hero-Option A
- Verb-Liste `Import / Normalize / Review / Rank …` → Subline-Idee
- 6 Trust-Pills `LOCAL-FIRST · …` → Hero-Trust-Cluster
- Builder-Note „I built this because…" → neue Section
- Reinvest-Comparison-Komposition → neue Section
- Cashflow-Heatmap-Kalender → neue Section (P2)
- Schwarze Highlight-Bar als Pattern → max. 2× pro Seite
- Footer-Bar `BUILT FOR INVESTORS, NOT TRADERS`
- Footer-Mikro-Slogans `BUILT SLOW · USED MONTHLY · …` → neue schmale Bar
- Mono-Caps-Eyebrows mit `//`-Prefix
- Härtere schwarze Borders auf 3 Section-Card-Sets

**❌ Nicht übernommen:**
- Beton-/Wald-/Mountain-Stockfotos
- Magenta/Pink-Akzent
- Retro-Terminal-Ästhetik
- Gelb statt Gold (separate Markenfarben-Frage)
- Markenname-Wechsel (`Operating Income OS`, `COMPOUNDING INCOME`)
- All-Caps für jede Headline
- Riesige Wordmark-Echos überall
- Sprach-Pivot auf Deutsch
- Trust-Logos „EXTRAETF / justETF / …" (keine echten Partnerschaften)
- „Download macOS & Windows" (anderes Distributionsmodell)
- Konkrete Forecast-Jahreszahlen prominent (`2032`)
- 7-Step-Workflow (das aktuelle 6-Step bleibt)

---

## 7. PATCH-PLAN — PRIORISIERT

### P0 — Sprach-Pivot *(kurzfristig)*

| Änderung | Datei | Aufwand |
|---|---|---|
| Hero-H1, Subline, Eyebrow auf Option A umstellen | `App.jsx`, `siteConfig.js` | S |
| Trust-Zeile von Fließtext zu Pill-Cluster | `App.jsx` | S |
| Eyebrows global auf `// CAPS`-Format | `App.jsx` | S |
| Anti-Maschinen-Übersetzungen anwenden | `App.jsx` | M |
| Mid-Page-Wording: Principles, Core Features, Audience, Snowball-Lede, SEC-Body, Final-CTA | `App.jsx` | M |

**Erwarteter Effekt:** Seite liest sich menschlich. Erste 5–10 Sekunden tragen.

### P1 — Neue Sections *(mittelfristig)*

- Builder-Note-Panel
- Reinvest-Comparison-Section
- Cashflow-Heatmap-Kalender (synthetic demo)
- Footer-Mikro-Slogan-Bar

### P2 — Full Page Redesigns *(Welle 1–3)*

Gemäß Mockup-Plan oben.

---

## 8. DECISION CHECKPOINTS — WAS DU BESTÄTIGEN MUSST

Bevor die nächste Mockup-Runde startet, drei Punkte:

1. **Markenname final** — Code-Stand ist `Compound Income OS`. Wenn das nur Sprechgewohnheit ist: bleibt. Wenn das ein impliziter Pivot ist: eigener Patch-Zyklus, nicht in dieser Welle.
2. **Sprache final** — Marketing-Pages bleiben Englisch. Wenn DACH-Markt im Fokus → jetzt entscheiden.
3. **Welle-1-Umfang final** — Empfehlung: **M1 + M2 + P2 + P5** (4 Assets). Minimum: **M2 + P5** (2 stärkste Neuigkeiten). Maximum: **+ M3 + P3** (6 Assets).

---

## 9. CONSTRAINTS — WAS WIR NICHT TUN

- Kein Code-Change in dieser Runde. Mockups gehen vor Implementation.
- Keine erfundenen Features (`Compare benchmarks` bleibt draußen bis Engineering-Bestätigung).
- Keine Live-User-Daten in Mockups. Alle Werte sind synthetic-demo-gelabelt.
- Keine Public-Launch-Pages. Imprint/Privacy/Pricing bleiben Pending-States.
- Keine bestehenden Marken-Assets wegwerfen: Wordmark, Paper/Ink/Gold-Palette, Status-Sprache, Disclaimer-Strenge bleiben.
- Product-UI-Mockups sind **statische Renderings** — keine interaktiven UI-Komponenten.

---

## 10. FINAL RECOMMENDATION

**Was als nächstes konkret passiert:**
1. Diesen Mockup-Plan bestätigen *(insbesondere die 3 Decision Checkpoints in Section 8)*.
2. Mockups für **Welle 1** beginnen: M1 Redesign + M2 Workflow Page + P2 Report Render + P5 Dashboard Viewer.
3. Brutalismus-Lite-Visual-Patch parallel ziehen (separate Spec, Strategy Review v3 Section 7).

**Was bewusst nicht passiert:**
- Keine M3/M4/M5/M6 in der ersten Welle.
- Keine Brand-Pivots.
- Keine Compliance-Constraint-Verschiebungen.

**Drei Änderungen mit dem größten Impact in Welle 1:**
1. **M1-Redesign zum Wegweiser** — alle Tiefen-Sections weg, dafür 5-Promises-Grid mit Page-Teasern.
2. **M2 als eigene Page mit P2 Report-Render** — stärkster Beweis, dass das ein OS ist, nicht ein Hero-Tool.
3. **P5 Local Dashboard Viewer** — beantwortet direkt: *„Was kriege ich nach jedem Run zu sehen?"*

---

*Master Plan erstellt auf Basis von `compound_income_os_HANDOFF_20260427-101335_c02419b.zip` (vollständiger Repo-Stand inkl. `docs/MODULE_CONTRACTS.md`, `configs/*`, `src/*` 43 Engines, `data/processed/*` Outputs, `reports/*` 14 Report-Typen). Keine Codeänderungen vorgenommen. Dieser Plan ist die Vorgabe für die nächste Mockup-Runde — keine Spec-Änderung, keine Implementation.*

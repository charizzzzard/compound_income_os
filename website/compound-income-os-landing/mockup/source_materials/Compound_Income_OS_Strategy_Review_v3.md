# Compound Income OS — Strategy Review v3

**Trigger:** Aktuelle Seite ist technisch sauber (Fix-Spec v2 zu ~95 % umgesetzt), aber liest sich noch maschinell. User-Mockups (Brutalist Berlin) zeigen, was menschlicher klingt. Diese Runde liefert Sprach-Pivot + visueller Pivot + Komponenten-Decision aus den Mockups, jeweils minimal-invasiv und claim-safe.

**Sprache:** Landingpage-Copy bleibt **Englisch** (so im letzten Briefing festgelegt). Die Mockups sind teils auf Deutsch — ihre *Tonalität* (du-Form, konkret, menschlich) wird ins Englische übertragen, nicht 1:1 übersetzt. Siehe Section 2 für die Sprach-Verzweigung.

**Markenname:** Bleibt **Compound Income OS** in dieser Runde. Die Mockups testen alternative Namen (`Operating Income OS`, `COMPOUNDING INCOME`) — eine Marken-Umbenennung ist eine separate, größere Entscheidung und nicht Scope dieser Patch-Runde. Siehe Section 2 für die Decision-Frage.

---

## 1. EXECUTIVE STRATEGY REVIEW

### Was funktioniert (nicht anfassen)

- Markenton ist ruhig, anti-hype, premium. Differenziert klar gegen Trader-Tools.
- Hero-Demo zeigt jetzt 3× OK + 1× REVIEW — der erste Eindruck liest sich als „Software arbeitet", nicht mehr „Software ist unfertig".
- Funnel ist ehrlich: keine Mailto-Platzhalter mehr, Pending-Pill ist sichtbar.
- Architecture-Principles, Decision Journal, SEC-Pipeline, Evidence-Sprache — alles claim-safe und differenzierend.
- Disclaimer-Strenge ist intakt.

### Warum die Texte trotzdem maschinell wirken (Diagnose)

Die aktuelle Hero-Headline beschreibt **das Output**, nicht **die Person, für die es gemacht ist**:

> Aktuell: *„One defensible investment decision a month."*
>
> Mockup-Variante: *„Portfolio research for people who think for themselves."* / *„A calmer process in a louder market."* / *„Run your portfolio like a long-term income system."*

Der Unterschied ist nicht „englisch vs. deutsch". Der Unterschied ist:
- **Aktuell** spricht *über* das System (was es liefert).
- **Mockups** sprechen *zur* Person (wer du bist, was du willst, was dich nervt) **oder** geben ein konkretes Sehnsuchtsbild (1.000 € / Monat, Income-System).

Das ist die Differenz zwischen *Spec-Sheet* und *Marketing-Voice*. Der Rest ist Folgesymptom: Subline ist eine Kommatakette aus Engineering-Substantiven (`broker exports, fundamentals, and SEC evidence`), Trust-Zeile besteht aus Negativ-Aufzählungen (`No broker. No cloud.`), und das gesamte Mid-Page-Vokabular (`deterministic`, `evidence-applied master`, `INSUFFICIENT_INPUTS`) gehört in eine Datenbank-Doku, nicht auf eine Investor-Landingpage.

### Was sich ändern muss (drei Hebel)

1. **Hero-Pivot von Output zu Identität.** Headline benennt den Investor-Typ oder den emotionalen Kontrast, nicht den Pipeline-Output.
2. **Anti-Maschinen-Sprachregeln im Mid-Page.** Engineering-Vokabular wird in Investor-Klartext übersetzt. Status-Sprache (`COVERED`, `REVIEW` …) bleibt — aber lebt in der Evidence-Section, nicht im Top-of-page.
3. **Builder-Voice einführen.** Eine kleine, ehrliche „Note from the builder"-Section macht die Seite menschlich, ohne den Premium-Ton zu brechen. Direkt aus den Mockups übernommen.

Plus: zwei visuelle Komponenten aus den Mockups (Reinvest-Vergleich + Ausschüttungskalender) als neue Sections — aber **claim-safe** gerahmt.

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

**Beobachtung:** Die emotional stärkste Mockup-Headline ist auf Deutsch (`SIEH, WANN DEIN PORTFOLIO 1.000 € PRO MONAT AUSSCHÜTTET`). Das ist kein Zufall — Deutsch ist deine Denksprache, und der DACH-DIY-Investor-Markt ist sehr aktiv (Finanzfluss, justETF, Parqet, ExtraETF — die in deinem Mockup als Trust-Logos auftauchen).

**Empfehlung-Trade-off:**

| Pfad | Pro | Contra |
|---|---|---|
| **EN bleiben** *(aktuelle Briefing-Vorgabe)* | Internationaler Reach; Engineering-Repo ist EN; Disclaimer-/Compliance-Sprache bereits EN | Verschenkt die emotionale Schärfe, die deine deutschen Mockups haben; DACH-Zielgruppe wird auf Englisch gelesen |
| **DE pivot** | Trifft Zielgruppe direkter; *„1.000 € pro Monat"* schlägt jede englische Übersetzung; Marken-Authentizität (Built in Europe) | Großer Switch; alle Footer-/README-/Asset-Texte werden DE; Code-Identifier bleiben EN, was zu Mischformen führt |
| **Bilingual** *(EN default, DE als Switch)* | Beste beider Welten | Engineering-Aufwand für i18n-Layer, Routing, Sprach-Switch — kein Hero-Patch mehr |

**Meine Empfehlung:** **EN bleiben in dieser Runde, aber mit der Tonalität der deutschen Mockups übersetzt.** Die deutschen Headlines werden nicht 1:1 ins Englische gezwungen, sondern in englische Äquivalente überführt, die *denselben emotionalen Hit* liefern. *„1.000 € pro Monat ausschüttet"* wird im Englischen nicht zu *„pays out €1,000 a month"* (klingt steif) — sondern zu einem Identitätsangebot wie *„Portfolio research for people who think for themselves"* oder einem Kontrastversprechen wie *„A calmer way to run a long-term portfolio"*. Ein DE-Pivot kann später folgen — als zweiter Patch, wenn klar ist, dass DACH der Hauptmarkt ist.

### 2.3 Visuelle Richtung — Brutalismus-Level

**Beobachtung:** Du sagst: Brutalismus-Idee gut, aber kein Tryhard, keine Beton-Bilder, beste Mockups sind unten links (Reinvest-Vergleich) und unten rechts (Ausschüttungskalender).

**Empfehlung:** **Brutalismus-Lite.** Konkret:

| Übernehmen | Nicht übernehmen |
|---|---|
| Größere, breitere Display-Type für Hero-Headline (mehr Gewicht, weniger tracking-tight) | Beton-Stockfotos (du hast das explizit ausgeschlossen) |
| Klare schwarze Borders bei Cards, weniger Soft-Shadow | All-Caps für jede Headline (wirkt Tryhard, sobald >2 Sections es nutzen) |
| Mono-Eyebrows in `// THIS FORMAT` oder Doppelbalken-Optik | Magenta/Pink-Akzent (in einem Mockup gesehen) — passt nicht zur Income-Marke |
| Schwarze Highlight-Leisten als Quote-Container *(Beispiel aus Mockup unten links: „REINVESTITION ERZEUGT BIS ZU 2,1X MEHR MONATLICHES EINKOMMEN")* | Tabular Mono-Font für Body-Text — wird unleserlich |
| Ein einziger Akzent-Gelb-Touch optional (wie in Mockup oben rechts: „ZIEL ERREICHT IM JAHR 2032") — *aber* optional, das aktuelle Gold passt thematisch besser zum Income-Thema | Riesige Wordmark-Echos (`OI` / `OS` als Hintergrund-Pattern) — Tryhard |
| Footer-Mikro-Slogan-Bar wie *„BUILT SLOW. USED DAILY."* — kompakt, ehrlich | Industrial-Marker-Streifen, Schraffuren als Decoration |

Kernregel: **Ein einziges brutalistisches Element pro Section-Block, kein Sammelsurium.** Die aktuelle Paper/Ink/Gold-Palette bleibt; Brutalismus kommt über Typografie (größer, fetter), Borders (härter), Highlight-Bars (schwarz), nicht über Stockfotos und Akzentfarben-Wechsel.

---

## 3. MOCKUP-KOMPONENTEN-DECISION

Du hast 18 Mockup-Bilder geliefert. Hier ist die explizite Decision-Tabelle, was übernommen wird, was nicht, und in welcher Form.

| # | Element / Section aus Mockups | Entscheidung | Begründung |
|---|---|---|---|
| 1 | **Hero mit Beton-Foto** *(Brutalist, Übersichtsbild oben links)* | ❌ **Nicht übernehmen** | Du hast es selbst ausgeschlossen. Beton-Bild trägt keine Bedeutung für ein Finanzprodukt — wirkt aufgesetzt. |
| 2 | **„DEIN INCOME-PLAN" Dashboard mit gelbem Balkenchart** *(Übersichtsbild oben rechts)* | ⚠️ **Konzept ja, Form anpassen** | Das ist ein **Forecast/Simulation-Dashboard mit konkreter Jahreszahl 2032** — claim-mäßig heikel. Im Marketing geht das nur als „illustrative Szenario", nicht als Versprechen. Übernehme das **Layout** (großer Akzent-Block + Zielkarten) für die Snowball-Section, **lasse die Forecast-Year-Aussage weg**. |
| 3 | **„REINVESTIEREN MACHT DEN UNTERSCHIED" — Mit/Ohne-Reinvestition-Vergleich** *(Übersichtsbild unten links)* | ✅ **Ganz übernehmen** *(als neue Section)* | Klar, scanbar, illustrativ. Die Aussage „Reinvestition erzeugt bis zu 2,1× mehr monatliches Einkommen" ist auf Englisch und als illustratives Szenario claim-safe formulierbar. Wird neue Section zwischen Snowball und Evidence. Du hast diese Komposition explizit als Favorit markiert. |
| 4 | **„AUSSCHÜTTUNGSKALENDER" — Heatmap-Kalender 2024–2032** *(Übersichtsbild unten rechts)* | ✅ **Konzept übernehmen, Implementierung schrumpfen** *(als neue Section oder als zweite Visual in Snowball)* | Heatmap-Layout ist eine starke, eigenständige Visualisierung der Income-Cadence. Funktioniert als „Cashflow Calendar"-Section. Aber: Mockup zeigt 9 Jahre × 12 Monate = 108 Zellen mit echten Werten — das ist für Marketing-Zweck zu viel. Schrumpfen auf 3–5 Jahre und mit Synthetic-Demo-Pill labeln. |
| 5 | **„INDEPENDENT SOFTWARE FOR THOUGHTFUL INVESTING" + Builder-Note** *(Brutalist Mockup 4)* | ✅ **Tonalität übernehmen** *(als neue Builder-Section)* | Die „Note from the builder" mit „Built by one person" ist genau der menschliche Anker, der aktuell fehlt. Wird als kleine Section eingebaut. |
| 6 | **„A CALMER PROCESS IN A LOUDER MARKET" + 7-Step-Workflow** *(Brutalist Mockup 3)* | ⚠️ **Headline-Tonalität ja, 7-Step nicht** | Das aktuelle 6-Step-Workflow ist gut. Kein Wechsel auf 7 Schritte. Aber die Tonalität dieser Headline („calmer process / louder market") ist genau der Hero-Sprachstil, den wir suchen. |
| 7 | **„PORTFOLIO RESEARCH FOR PEOPLE WHO THINK FOR THEMSELVES" + Verb-Liste** *(Brutalist Mockup 2)* | ✅ **Headline-Idee + Verb-Liste übernehmen** | Die Verb-Liste *„Import broker data. Normalize positions. Review fundamentals coverage. …"* ist die menschliche Form der Pipeline-Beschreibung. Wird Subline-Idee. |
| 8 | **6 Pills LOCAL-FIRST / EVIDENCE-BASED / REVIEWABLE / NO HYPE / NO BLACK BOX / NO BROKERAGE EXECUTION** *(Brutalist Mockup 4 + 2)* | ✅ **Übernehmen als Hero-Trust-Cluster** | Aktuell ist die Trust-Zeile Fließtext (`Local-first · Open-source core · …`). Als visuelle Pill-Reihe direkt unter den CTAs wirkt sie stärker. |
| 9 | **„Run your portfolio like a long-term income system" + grünes SaaS-Dashboard** *(Premium SaaS)* | ⚠️ **Headline als Option B** | Verträgt sich gut mit dem Markenton, ist aber weniger differenzierend als „calmer/louder" oder „think for themselves". Liefere ich als Backup-Option. |
| 10 | **„A calm process for better portfolio decisions" + Wald-Hintergrund** *(Editorial)* | ⚠️ **Tonalität ja, Hintergrund nein** | Wald-Stockfoto im Hintergrund ist genauso problematisch wie das Beton-Foto — symbolisch, nicht informativ. |
| 11 | **Magenta/Pink-Akzent** *(Disciplined Investing Mockup)* | ❌ **Nicht übernehmen** | Bricht die Income-/Gold-Markenfarbe. Magenta gehört zu Tech-/Crypto-Pitches. |
| 12 | **Retro/Terminal-Richtung** *(03_retro_indie)* | ❌ **Nicht übernehmen** | Coding-Aesthetik trägt die falsche Identität — sieht nach Hobby-Tool aus, nicht nach Premium-Operating-System. |
| 13 | **„NO HYPE. JUST SIGNAL." vertikales Trust-Mantra** *(Brutalist Mockup 4)* | ✅ **Übernehmen als Footer-Mikro-Slogan** | Sehr starkes Tagline-Format. Ersetzt einen Footer-Bottom-Line-Block. |
| 14 | **„BUILT FOR INVESTORS, NOT TRADERS." Footer-Bar** *(Brutalist Mockup 2)* | ✅ **Übernehmen als Footer-Bar** | Stärker als die aktuelle Footer-Bottom-Line. |
| 15 | **„Download macOS & Windows. Free to try. No sign-up."** *(Brutalist Mockup 2)* | ❌ **Nicht übernehmen** | Das ist eine andere Distributionsform (Desktop-App). Compound Income OS ist aktuell ein lokales Python-CLI-Repo, kein installierbarer Desktop-Build. Das wäre eine Produkt-Pivot, nicht ein Marketing-Patch. |
| 16 | **Trust-Logos „EXTRAETF / justETF / finanzfluss / PARQET"** *(Übersichtsbild oben links)* | ❌ **Nicht jetzt** | Du brauchst echte Partnerschaften oder Trust-Statements von echten Investoren — nicht erfundene Brand-Logo-Reihen. „Vertraut von DIY-Investoren" mit zugehörigen Logos wäre eine Lüge, solange diese Plattformen Compound Income OS nicht aktiv referenzieren. |
| 17 | **Großes Wordmark im Sidebar-Pattern** *(diverse Mockups)* | ⚠️ **Optional, klein dosiert** | In *einer* Section akzeptabel (z. B. im Footer als großer typografischer Abschluss). Mehrfache Wordmark-Echos überall = Tryhard. |
| 18 | **Schwarze Highlight-Leiste mit Outcome-Aussage** *(„REINVESTITION ERZEUGT 2,1× MEHR EINKOMMEN")* | ✅ **Übernehmen als Pattern** | Wirksam für eine Outcome-Aussage pro großem Visual. Wird in der Reinvest-Comparison-Section verwendet. |

---

## 4. ANTI-MASCHINEN-SPRACHREGELN

Konkrete Übersetzungstabelle für die Mid-Page-Sprache. Linke Spalte = aktuell auf der Seite. Rechte Spalte = menschlicher, gleiche Bedeutung. Die Status-Sprache (`COVERED`, `REVIEW`, `MISSING_DATA`) bleibt erhalten — aber nur in der Evidence-Section, nicht weiter oben.

| Aktuell (zu maschinell) | Neu (menschlich, claim-safe) |
|---|---|
| `One defensible investment decision a month.` | *(Hero — siehe Section 5 für 3 finale Optionen)* |
| `Compound Income OS turns your broker exports, fundamentals, and SEC evidence into one reproducible monthly decision report — locally, with every data gap visible.` | `Built for long-term investors who want one clear monthly decision instead of a daily noise feed. Import your broker data, review what you actually own, and end the month with one report you can read in five minutes — and re-open in a year.` |
| `Local-first · Open-source core · Evidence-based · No broker. No cloud.` *(Trust-Zeile)* | Bleibt als Pill-Cluster (siehe 3.8), aber im Format: `LOCAL-FIRST` · `OPEN-SOURCE CORE` · `EVIDENCE-BASED` · `NO BROKER` · `NO CLOUD` |
| `Where long-term portfolios actually break.` | Bleibt — ist gut. |
| `Six stages from input files to decision journal.` | `Six stages, one monthly cadence. The same workflow every month — so month 12 is just month 1, eleven times reviewed.` *(bereits sinngemäß in der Spec, aber „from input files to decision journal" ist zu engineery für die Headline)* |
| `Architecture-level guardrails — not slogans.` | `Six commitments, not six slogans.` *(„architecture-level" ist Engineering-Vokabular, „commitments" ist Investor-Vokabular)* |
| `Reproducible by design` *(Principle Title)* | `The same inputs, the same outputs.` *(Mockup-Inspiration: „Same inputs, same outputs. Transparent methodology. Repeatable results.")* |
| `Every run records inputs, manifests, and generated artifacts for later review.` *(Principle Body)* | `Every monthly run keeps a copy of what went in, what came out, and what changed — so you can read your reasoning a year from now.` |
| `Evidence-only` *(Principle Title)* | `Nothing is silently filled.` |
| `Missing data stays visible. Values are never guessed or silently imputed.` *(Principle Body)* | `If a number is missing, the report says so. We don't fill in the blanks for you.` |
| `Decisions, not orders.` *(Principle Title — bleibt)* | Bleibt — funktioniert gut. |
| `The system documents, ranks, and reports. It never executes orders or connects to a brokerage.` | `Compound Income OS shows you what to look at. You decide what to do with it. We don't trade. We don't connect to brokers.` *(menschlicher; aktiv statt passiv)* |
| `Local-first` *(Principle Title — bleibt)* | Bleibt. |
| `Runs from local files and emits local CSV and Markdown artifacts.` *(Principle Body)* | `Your portfolio runs from your files, on your machine. Outputs are CSVs and Markdown reports you own.` |
| `Privacy-first` *(Principle Title — bleibt)* | Bleibt. |
| `Raw portfolio inputs remain under user control and separate from processed outputs.` *(Principle Body)* | `Your raw broker data never mixes with what we generate. You always know which is which.` |
| `One local pipeline. Three modules. Five evidence layers.` *(Core Features Headline)* | `One local pipeline. Three things it does. Five ways it stays honest.` |
| `Watchlist & Monthly Ranking` → `A cash-aware queue of candidates, ordered by transparent rule-based scores. Blockers, review states, and concentration limits stay visible.` | `Watchlist that ranks itself.` → `A cash-aware queue that puts the most defensible candidates first. The rules are visible; the blockers are visible; nothing scores in the dark.` |
| `Monthly Decision Report` → `One Markdown artifact per run. Explains the current candidate, the blockers, the data gaps, and the reasoning under your current rule set.` | `One report a month.` → `A short Markdown file that explains what you'd act on, what's blocking you, and what data is still missing — in plain language.` |
| `Decision Journal & Local Dashboard` → `A re-readable record of every monthly decision, alongside a local KPI dashboard that consolidates processed artifacts.` | `Decisions that don't get lost.` → `Every monthly decision is written down beside the run that produced it. The local dashboard pulls those runs into one view.` |
| `Your dividend snowball, modeled honestly.` *(Snowball Headline)* | Bleibt — ist gut. |
| `Run reproducible income scenarios from your own holdings, your own assumptions, and your own concentration caps. Every assumption is declared. Nothing is predicted.` *(Snowball Lede)* | `Show me what my dividend income could look like — with my real holdings, my real assumptions, and the concentration limits I've set. Not a forecast. A scenario you can rerun a year from now.` *(Stimme wechselt von „Run …" zu „Show me …" — der Investor spricht zur Software, nicht umgekehrt)* |
| `For eligible US stocks, the system can pull fundamentals from SEC CompanyFacts — read-only, after manual identity review. The fundamentals master is never silently overwritten.` | `For US stocks, we can pull fundamentals straight from SEC filings — read-only, after you confirm the ticker matches. Updates wait in a queue. Nothing overwrites your file unless you say so.` |
| `Status labels (COVERED, PARTIAL, REVIEW, MISSING_DATA) as first-class outputs.` | `Every KPI carries a status. If a number is missing, it's labeled missing — not filled.` |
| `Built for independent operators.` *(Audience Headline)* | `Built for people who run their own research.` |
| `Open-Source Core / Free · Open-source / Local pipeline for positions, fundamentals, watchlist ranking, monthly ranking, reports, and dashboard artifacts.` *(Access Card 1)* | `Open-Source Core / Free · MIT (or whichever license) / The full local workflow: import, rank, report, journal. Run it yourself, fork it, or just read the code.` |
| `Pro Modules / Pricing TBD · Private preview / Optional local extensions for deeper evidence review, scenario inspection, and additional dashboards.` *(Access Card 2)* | `Pro Modules / Pricing TBD · Private preview / Extra local modules for deeper evidence review and scenario work. Email me if you want early access.` *(Builder-Voice — „Email me" statt „Request private preview")* |
| `Setup Service / Pricing on request · Private preview / Guided setup, local environment preparation, input mapping, and first reproducible run support.` *(Access Card 3)* | `Setup Help / Pricing on request · Private preview / I'll walk you through the local setup, map your broker exports, and run your first month with you.` *(„I'll" — wieder Builder-Voice)* |
| `One reproducible decision a month. Locally. With evidence.` *(Final CTA Headline)* | `One decision a month. Locally. On your terms.` |
| `Compound Income OS is a research and decision-support tool. It is not investment, tax, or legal advice, never connects to a brokerage, and never executes orders. All values shown on this page are synthetic demo values.` *(Disclaimer Short — bleibt)* | Bleibt unverändert — Disclaimer ist Compliance, nicht Marketing. |

**Anti-Maschinen-Faustregel für zukünftige Texte:**
1. **Streiche jedes Wort, das in einem System-Spec besser aufgehoben wäre.** Beispiele: `deterministic`, `pipeline`, `manifest`, `artifact` (außer in der Code-Block-Section), `master`, `imputed`, `pipeline`, `gate`, `eligible`, `traceability`.
2. **Wechsle von Passiv zu Aktiv.** „The system documents …" → „Compound Income OS shows you …" oder besser: Builder-Voice „I built it to …".
3. **Wechsle von Substantiv-Ketten zu Verben.** „broker exports, fundamentals, and SEC evidence" → „import your broker data, review what you own, pull SEC filings when you need them".
4. **Eine konkrete Sache pro Satz.** Aktuelle Sublines verketten oft 3–5 Konzepte mit Komma. Lieber 3 kurze Sätze.

---

## 5. NEUE HERO-PACKAGE-OPTIONEN

Drei finale Optionen, jede claim-safe, jede menschlicher als der aktuelle Stand. Du wählst eine.

### Option A — „Calmer Process" *(meine Empfehlung — Brutalist Mockup 3 + Editorial-Mockup-Tonalität)*

| Element | Wert |
|---|---|
| **Eyebrow** | `LOCAL-FIRST INVESTMENT OPERATING SYSTEM` |
| **H1** | `A calmer way to run a long-term portfolio.` |
| **Subheadline** | `Built for dividend-growth and quality-compounder investors who want one clear monthly decision instead of a daily noise feed. Import your broker data, review what you actually own, and end the month with a report you can re-open in a year.` |
| **Primary CTA** | `Read a sample monthly report` |
| **Secondary CTA** | `See the workflow` |
| **Trust pill cluster** *(unter den CTAs, statt Fließtext)* | `LOCAL-FIRST` · `OPEN-SOURCE CORE` · `EVIDENCE-BASED` · `NO BROKER` · `NO CLOUD` |
| **Meta strip** *(unverändert)* | `MODE Local files` · `OUTPUTS CSV / Markdown` · `CADENCE Monthly` |

**Warum Option A:** Stärkster emotionaler Kontrast (calm/loud), nicht englisch-aus-deutsch übersetzt, schließt direkt an deinen anti-hype-Markenkern an, lässt Identität (long-term investor) und Outcome (monthly decision, re-openable in a year) gleichzeitig anklingen, ohne Performance-Claim.

### Option B — „Think for Themselves" *(Brutalist Mockup 2 — identitäts-getrieben)*

| Element | Wert |
|---|---|
| **Eyebrow** | `INDEPENDENT PORTFOLIO RESEARCH SOFTWARE` |
| **H1** | `Portfolio research for people who think for themselves.` |
| **Subheadline** | `Compound Income OS is independent local software for long-term investors. Import broker data. See what you actually own. Rank what's worth your attention. End the month with one decision report you can read in five minutes — and revisit a year from now.` |
| **Primary CTA** | `Read a sample monthly report` |
| **Secondary CTA** | `See the workflow` |
| **Trust pill cluster** | identisch Option A |
| **Meta strip** | identisch Option A |

**Warum Option B:** Stärkstes Identitätsangebot („for people who …"). Direkter in der Werteansage. Funktioniert besonders gut, wenn du dich als „Anti-Mainstream-Investor-Tool" positionierst.

### Option C — „Income System" *(Premium SaaS Mockup — Outcome-konkret, näher am deutschen „1.000 € pro Monat")*

| Element | Wert |
|---|---|
| **Eyebrow** | `LOCAL DIVIDEND-GROWTH RESEARCH` |
| **H1** | `Run your portfolio like a long-term income system.` |
| **Subheadline** | `Compound Income OS gives dividend-growth and quality-compounder investors a local, reviewable workflow — built around the income you compound, not the trades you chase. One monthly decision report. On your machine. In your files.` |
| **Primary CTA** | `Read a sample monthly report` |
| **Secondary CTA** | `See the workflow` |
| **Trust pill cluster** | identisch Option A |
| **Meta strip** | identisch Option A |

**Warum Option C:** Outcome-konkreter als A und B. „Income system" ist die englische Version dessen, was deine deutschen Mockups mit „1.000 € pro Monat" konkret machen — ohne Zahlversprechen. Aber: Etwas weniger differenzierend als A/B (Premium-SaaS-typisch).

### Empfehlung: **Option A.**

Ist menschlich, claim-safe, anti-hype-konsistent, hat den emotionalen Kontrast, der den Markenton trägt. Bei Bedarf kann der Eyebrow später durch *„BUILT IN BERLIN. USED MONTHLY."* o. Ä. ersetzt werden, sobald du dich als Builder-Brand mehr exponieren willst.

---

## 6. NEUE SECTIONS (aus Mockups übernommen)

Drei neue Section-Vorschläge. Alle minimal-invasiv (keine neuen Komponenten-Files, kein State-Management, keine neuen Libraries). Reihenfolge in der Seite:

```
Header → Hero → Dashboard Preview → Problem → Solution → Principles
→ [NEU] Builder Note
→ Workflow → Core Features
→ Snowball
→ [NEU] Reinvest Comparison
→ [NEU] Cashflow Calendar
→ Evidence + Data Quality
→ Decision Journal + Audience → Access → Final CTA → Footer
```

### 6.1 Builder Note *(neue Section, zwischen Principles und Workflow)*

**Direkt aus Brutalist Mockup 4 übernommen:** Kleine, ehrliche Founder-/Builder-Stimme. Macht die Seite menschlich, ohne den Premium-Ton zu brechen.

**Eyebrow:** `A NOTE FROM THE BUILDER`

**Headline:** `I built this because the tools I needed didn't exist.`

**Body:**
> Most portfolio software is loud. It's built for trading, not for thinking. It hides its math, runs on someone else's cloud, and forgets every decision you make.
>
> Compound Income OS is the opposite of that. It runs on your machine. It shows its work. It writes your monthly decision down beside the data that produced it — so a year from now you can still read what you were thinking and why.
>
> No venture capital. No black box. No hype. Just a structured monthly process for long-term investors.

**Signatur:** *(klein, mono)* `— Built and maintained independently.`

**Visuell:** Linke Spalte Text, rechte Spalte ein leeres dunkles Panel mit dem Wordmark als großer typografischer Abschluss (statt Beton-Foto). Optional: ein kleiner Bookmark-Block mit `Read the manifesto →` *(verlinkt nach unten zu Principles oder bleibt als Pending-Link wenn keine separate Manifesto-Seite existiert)*.

**Wenn du dich anonym halten willst:** Lass die Signatur weg. „Built and maintained independently" reicht aus, ohne Person nennen zu müssen.

**Wenn du namentlich erscheinen willst:** Signatur mit Vorname (`— Florian` o. ä.) — wirkt deutlich vertrauensvoller. Aber das ist deine Entscheidung.

### 6.2 Reinvest Comparison *(neue Section, nach Snowball)*

**Direkt aus Übersichtsbild unten links übernommen.** Du hast diese Komposition explizit als Favorit markiert.

**Eyebrow:** `WHAT REINVESTING ACTUALLY DOES`

**Headline:** `Two scenarios. Same starting point.`

**Lede:** `Same portfolio, same monthly contribution, same dividend yield assumption — one path reinvests, one path doesn't. Run it on your own holdings to see your version.`

**Layout:** Zwei Karten nebeneinander.

| Card | Title | KPI top | KPI breakdown | Mini chart |
|---|---|---|---|---|
| Left | `WITH REINVESTMENT` | `€1,028 / month` *(monthly income, scenario year)* | `Portfolio value · €415,000` `Total contributions · €146,000` `Total distributions · €269,000` | rising line |
| Right | `WITHOUT REINVESTMENT` | `€485 / month` | `Portfolio value · €198,000` `Total contributions · €146,000` `Total distributions · €78,000` | flatter line |

**Schwarze Highlight-Leiste unter den beiden Karten** *(Brutalismus-Element — direkt aus Mockup):*
> `REINVESTMENT GENERATES UP TO 2.1× MORE MONTHLY INCOME — IN THIS SCENARIO.`

**Disclaimer-Pill direkt darunter:**
> `Illustrative scenario · synthetic demo values · not a forecast`

**Wichtige Compliance-Anpassung gegenüber dem Mockup:**
- Mockup-Aussage „REINVESTITION ERZEUGT BIS ZU 2,1X MEHR MONATLICHES EINKOMMEN" wirkt wie ein Versprechen.
- Englische Variante hängt explizit `IN THIS SCENARIO.` an.
- Synthetic-Pill direkt darunter.
- Year-Marker (Mockup: `2032`) kommt nicht prominent vor — als kleiner Mono-Text unten links (`scenario horizon: ~10 years`), nicht als großes Datum.

### 6.3 Cashflow Calendar *(neue Section, nach Reinvest Comparison)*

**Direkt aus Übersichtsbild unten rechts übernommen.** Heatmap-Kalender.

**Eyebrow:** `CASHFLOW CALENDAR`

**Headline:** `See your dividend rhythm before it happens.`

**Lede:** `Most dividends arrive on a quarterly schedule. The calendar makes the rhythm visible — which months are heavy, which are light, and which positions actually drive each month.`

**Layout:** Heatmap-Grid: Y-Achse = Jahre (5 Jahre statt 9 — der Mockup-Wert von 2024–2032 ist zu viel für eine Marketing-Seite), X-Achse = Monate (Jan–Dec). Zellen sind 4 Stufen (no payout / low / medium / high) — passend zur Paper/Ink/Gold-Palette.

**KPI-Sidecar rechts:**
| Label | Value |
|---|---|
| `AVERAGE MONTHLY INCOME (year 5)` | `€1,028` |
| `TOP MONTHS (year 5)` | `JUN €142` `SEP €128` `DEC €126` |
| `PAYOUT FREQUENCY` | `Quarterly` |

**Disclaimer-Pill:** `Illustrative scenario · synthetic demo values · not a forecast`

**Wenn Implementierung-Aufwand zu hoch:** Diese Section ist P2 (siehe Section 9). Reinvest Comparison + Builder Note sind P1.

---

## 7. VISUELLER BRUTALISMUS-LITE-SPEC

Konkret, was sich an der Optik ändern soll. Keine neuen Libraries, keine Layout-Pivots — nur Typo, Borders, ein neues Highlight-Pattern.

### 7.1 Typografie

- **Hero-H1:** Aktuell `text-5xl … sm:text-6xl lg:text-7xl tracking-[-0.055em]`. Neu: bleiben, aber **font-weight von `font-semibold` (600) auf `font-bold` (700) erhöhen**. Brutalismus lebt von Gewicht.
- **Section-Titles:** Aktuelle Section-Titles bleiben. Aber: **Eyebrows in Mono-Caps mit Doppel-Slash-Prefix** wie in den Mockups (`// LOCAL-FIRST INVESTMENT OPERATING SYSTEM` statt `LOCAL-FIRST PORTFOLIO RESEARCH`). Das ist das einzige durchgehende Mockup-Element, das den Brutalismus signalisiert, ohne aufzudrängen.
- **Rest unverändert.** Keine globale All-Caps-Pflicht.

### 7.2 Borders

- Karten in den Sections `Principles`, `Core Features`, `Access` bekommen eine **härtere schwarze Border** (`border border-[color:var(--ink-900)]` statt der aktuellen weichen `paper-300`-Border). Soft-Shadow bleibt — das gibt das Premium-Gefühl. Es ist die Border, die brutalistisch wird, nicht die Schatten.
- Nur diese drei Sections, nicht jede Karte überall — sonst wirkt es Tryhard.

### 7.3 Highlight-Bar-Pattern *(neu)*

Schwarze, full-width-Bar mit weißer Mono-Caps-Schrift, die *eine* Outcome-Aussage trägt. Wird sparsam eingesetzt:

- Unter der Reinvest-Comparison-Section: `REINVESTMENT GENERATES UP TO 2.1× MORE MONTHLY INCOME — IN THIS SCENARIO.`
- Optional als Footer-Bar oberhalb des Disclaimers: `BUILT FOR INVESTORS, NOT TRADERS.` *(direkt aus Mockup)*

**Maximal 2× pro Seite.** Wenn die Bar 3-mal vorkommt, wird sie zur Dekoration und verliert Wirkung.

### 7.4 Akzentfarbe

- **Gold bleibt.** Wechsel auf Gelb (wie im Mockup) wäre eine Markenfarben-Pivot — nicht Scope.
- Goldener Snowball-Stroke bleibt. Goldene CTAs haben wir bisher nicht; das bleibt so.

### 7.5 Footer-Mikro-Slogan-Bar *(neu, aus Mockup übernommen)*

Direkt über dem Disclaimer-Block, eine schmale Bar mit 4 kurzen Slogan-Items, mono, klein:

```
BUILT SLOW · USED MONTHLY  |  PRIVACY BY DEFAULT  |  NO HYPE · JUST SIGNAL  |  YOUR DATA · YOUR MACHINE
```

Ersetzt nicht den Disclaimer — steht *zwischen* der bestehenden Footer-Bottom-Line und dem Disclaimer-Block. Optisch: schwarzer Streifen, weiße Mono-Caps.

### 7.6 Wordmark im Builder-Note-Panel

Statt Beton-Foto: ein dunkles Panel rechts vom Builder-Note-Text mit dem Wordmark groß typografisch als Pattern (nicht als Marke selbst — eine zweite, gedimmte Wordmark-Instanz wirkt poetisch ohne illustrativ zu sein). Bleibt typografisch, also markenkonsistent.

---

## 8. MOCKUP-DECISION ZUSAMMENGEFASST

Falls du nur eine Übersicht brauchst:

**✅ Übernommen:**
- Tonalität von „A calmer process in a louder market" → Hero-Option A
- Verb-Liste „Import / Normalize / Review / Rank …" → Subline-Idee
- 6 Trust-Pills `LOCAL-FIRST · …` → Hero-Trust-Cluster
- Builder-Note „I built this because…" → neue Section
- Reinvest-Comparison-Komposition → neue Section
- Cashflow-Heatmap-Kalender → neue Section (P2)
- Schwarze Highlight-Bar als Pattern → max. 2× pro Seite
- Footer-Bar „BUILT FOR INVESTORS, NOT TRADERS" → ersetzt aktuelle Bottom-Line
- Footer-Mikro-Slogans `BUILT SLOW · USED MONTHLY · …` → neue schmale Bar
- Mono-Caps-Eyebrows mit `//`-Prefix → globaler Tonal-Shift
- Härtere schwarze Borders auf 3 Section-Card-Sets

**❌ Nicht übernommen:**
- Beton-Stockfotos
- Wald-/Mountain-Stockfotos
- Magenta/Pink-Akzent
- Retro-Terminal-Ästhetik
- Gelb statt Gold (separate Markenfarben-Frage)
- Markenname-Wechsel (`Operating Income OS`, `COMPOUNDING INCOME`)
- All-Caps für jede Headline
- Riesige Wordmark-Echos überall
- Sprache-Pivot auf Deutsch
- Trust-Logos „EXTRAETF / justETF / …" (du hast keine echten Partnerschaften)
- „Download macOS & Windows" (anderes Distributionsmodell)
- Konkrete Forecast-Jahreszahlen prominent (`2032`)
- 7-Step-Workflow (das aktuelle 6-Step bleibt)

---

## 9. PATCH-PLAN — PRIORISIERT

Drei Patch-Wellen. Jede ist minimal-invasiv (keine neuen Libraries, keine Routing-Änderungen, keine Komponenten-Files, kein i18n).

### P0 — Sprach-Pivot *(diese Woche)*

| Änderung | Datei | Aufwand |
|---|---|---|
| Hero-H1, Subline, Eyebrow auf Option A umstellen | `App.jsx`, `siteConfig.js (tagline)` | S |
| Trust-Zeile von Fließtext zu Pill-Cluster | `App.jsx` | S |
| Eyebrows global auf `// CAPS`-Format | `App.jsx` (einmalige Find-Replace-Logik im Eyebrow-Render) oder kleine Helper-Funktion | S |
| Anti-Maschinen-Übersetzungen anwenden (siehe Section 4 Tabelle) | `App.jsx` | M |
| Mid-Page-Wording: Principles, Core Features, Audience, Snowball-Lede, SEC-Body, Final-CTA | `App.jsx` | M |

**Erwarteter Effekt:** Seite liest sich menschlich. Erste 5–10 Sekunden tragen.

### P1 — Visueller Brutalismus-Lite + Builder Note *(nächste Woche)*

| Änderung | Datei | Aufwand |
|---|---|---|
| H1 von `font-semibold` auf `font-bold` | `App.jsx` | XS |
| Härtere schwarze Borders auf Principles/Core-Features/Access-Cards | `landing.css` (eine Klasse `.card-hard` einführen) | S |
| Builder-Note-Section bauen | `App.jsx` (neue Section-Komponente) | M |
| Highlight-Bar-Pattern als wiederverwendbare Komponente | `App.jsx` | S |
| Footer-Bar „BUILT FOR INVESTORS, NOT TRADERS" + Mikro-Slogan-Bar | `App.jsx` | S |

**Erwarteter Effekt:** Visuell mutiger, ohne Tryhard. Builder-Note macht die Seite menschlich auch jenseits der Hero.

### P2 — Outcome-Visuals *(später, optional)*

| Änderung | Datei | Aufwand |
|---|---|---|
| Reinvest-Comparison-Section | `App.jsx` (neue Section mit 2 KPI-Karten + 2 SVG-Mini-Charts + Highlight-Bar) | M |
| Cashflow-Calendar-Section (Heatmap) | `App.jsx` (neue Section mit 5×12 Grid + KPI-Sidecar) | M–L |
| Manifesto-Page *(falls Builder-Note auf eine echte Seite verlinken soll)* | neue Route oder MD-Datei | M |

**Erwarteter Effekt:** Outcome-Sehnsucht wird visuell ausgesprochen — claim-safe als Szenario.

### Nicht-Ziele für diese Patch-Welle

- Keine Marken-Umbenennung.
- Kein Sprach-Pivot auf Deutsch.
- Keine Routing-Änderungen.
- Keine i18n-Infrastruktur.
- Keine Markenfarben-Pivot (Gold bleibt; kein Gelb).
- Keine echten Trust-Logos einbauen, solange keine echten Partnerschaften bestehen.
- Keine Forecast-/Performance-Claims.

---

## 10. ACCEPTANCE CRITERIA — DELTA ZUR LETZTEN SPEC

Zusätzlich zu den 20 ACs der vorherigen Spec (alle bleiben gültig), gelten neu:

- AC-21. Hero-H1 enthält keine der folgenden Wörter: `defensible`, `reproducible`, `deterministic`, `pipeline`. Stattdessen ein menschliches Identitäts-/Kontrast-Wort (z. B. `calmer`, `independent`, `long-term`).
- AC-22. Hero-Subline ist mindestens **2 Sätze** lang (nicht eine Komma-Verkettung) und enthält mindestens ein menschliches Verb (`import`, `review`, `read`, `re-open`).
- AC-23. Mid-Page enthält keine der Wörter: `manifest`, `evidence-applied master`, `imputed`, `gate` (Verb), `eligible`. Diese leben nur noch in der Evidence-Section + im Decision-Journal-Code-Block.
- AC-24. Builder-Note-Section ist sichtbar und enthält mindestens einen Ich-Satz (`I built …`, `I'll …`, `Email me …`).
- AC-25. Schwarze Highlight-Bar erscheint maximal 2× pro Seite.
- AC-26. Eyebrow-Format `// CAPS` ist konsistent über alle Sections angewendet (nicht teilweise alt + teilweise neu).
- AC-27. Wenn Reinvest-Comparison oder Cashflow-Calendar gerendert sind, tragen sie sichtbar `Illustrative scenario · synthetic demo values · not a forecast`.
- AC-28. Es ist nirgends auf der Seite eine konkrete Jahreszahl als Forecast prominent (z. B. `2032` als großer Display-Wert).

---

## 11. FINAL RECOMMENDATION

**Was Codex/Engineer als Nächstes konkret tun sollte:**
1. Hero-Pivot auf Option A umsetzen (P0).
2. Anti-Maschinen-Übersetzungstabelle (Section 4) anwenden (P0).
3. Trust-Zeile zu Pill-Cluster, Eyebrows auf `// CAPS`-Format (P0).
4. Builder-Note-Section bauen (P1).
5. Footer-Bar + Mikro-Slogans (P1).
6. Härtere Borders auf 3 Card-Sets (P1).

Das ist eine Patch-Welle, keine Re-Architektur. Mit diesen Änderungen liest sich die Seite menschlich und visuell mutiger, ohne dass etwas Bestehendes weggeworfen wird.

**Was bewusst NICHT umzusetzen ist:**
- Marken-Umbenennung
- Sprach-Pivot
- Stockfotos jeglicher Art
- Trust-Logos ohne echte Partnerschaften
- Forecast-Jahreszahlen prominent
- Magenta/Gelb als Akzentfarbe

**Drei Änderungen mit dem größten Impact (Reihenfolge):**
1. **Hero-H1 von „One defensible investment decision" auf „A calmer way to run a long-term portfolio"** *(oder Option B/C)*. Erste 1,5 Sekunden lesen sich nicht mehr techy.
2. **Builder-Note-Section.** Eine ehrliche „Ich"-Stimme auf einer ansonsten anonymen Seite ist der größte Trust-Hebel, den du jetzt ziehen kannst, ohne Geld auszugeben oder echte Testimonials zu erfinden.
3. **Subline-/Mid-Page-Übersetzung von Engineer-Vokabular zu Investor-Klartext.** Macht den Unterschied zwischen „Spec-Sheet" und „Marketing-Seite", den dein Feedback adressiert.

**Bestehende Markenelemente, die geschützt bleiben:**
- Anti-Hype-Tonalität, Local-first, No-Cloud, No-Broker als harte Marken-Kanten.
- Status-Sprache (`COVERED`, `PARTIAL`, `REVIEW`, `MISSING_DATA` …) in der Evidence-Section.
- Decision-Journal-Code-Block.
- Disclaimer-Strenge.
- Paper/Ink/Gold-Palette.
- 6 Architecture-Principles als Markenherz (mit den menschlicheren Bodies aus Section 4).

**Eine letzte Beobachtung:**

Du hast in den Mockups schon die Sprache, die du suchst — sie ist nur auf Deutsch und unter einem anderen Markennamen. Diese Patch-Runde übersetzt sie ins Englische und unter den aktuellen Markennamen, ohne die Kraft zu verlieren. Wenn du nach dieser Runde merkst, dass die deutsche Mockup-Energie immer noch fehlt, ist der nächste Schritt nicht „mehr Brutalismus", sondern entweder ein DE-Pivot oder eine Marken-Umbenennung. Beides ist ein eigener Patch-Zyklus, kein Hero-Patch.

---

*Strategy Review erstellt auf Basis von `compound_income_os_HANDOFF_20260427-093203_169712c.zip` (aktueller Code-Stand), `operating_income_os_mockups.zip` (4 Mockup-Richtungen × 18 Bilder) und der Übersichtsdatei `1777275750843_image.png`. Keine Codeänderungen vorgenommen. Alle Copy-Strings sind kopierbar. Anti-Maschinen-Tabelle ist 1:1 in `App.jsx` anwendbar.*

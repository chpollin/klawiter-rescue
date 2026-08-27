---
title: Oberfläche und Kuration
aliases: [frontend, interface, EIL, curation tool]
project:
  name: Klawiter Bibliography
  repository: https://github.com/chpollin/klawiter-rescue
status: complete
language: de
version: 1.2
tags: [frontend, eil, accessibility, export]
created: 2026-03-29
updated: 2026-08-27
authors: [Christopher Pollin]
related: [data, pipeline, testing, production-readiness]
---

# Oberfläche und Kuration

## Aufgabe

Die statische Anwendung unter `docs/` macht den geretteten Bestand recherchierbar und stellt eine lokale Expert-in-the-Loop-Kurationsoberfläche bereit. Sie benötigt keinen Build-Schritt und keinen Serverprozess außer einem statischen localhost-Server für den Editiermodus.

Die öffentliche Anwendung unterstützt Suche, Facetten, Zeitverlauf, Sprach- und Ortsauswertung, Referenz-Ranglisten, Detailkarten, eine Datenqualitäts-Werkbank und Zitationsexporte. Die lokale Kurationsschicht ergänzt Fundstellen, Provenienz, Triage, subjektbezogene Normdaten-Entscheidungen und den versionierten Patch-Export. Die Oberflächensprache ist durchgehend Englisch, auch im Editiermodus.

## Architektur

`docs/index.html` lädt klassische Skripte (kein Modulsystem, gemeinsamer globaler Namensraum) und lokal vendorte Abhängigkeiten (`docs/vendor/`: FlexSearch, D3 v7, topojson-client, d3-sankey, `countries-110m.json` mit Provenienzvermerk). Die Visualisierungs-Bundles sind `defer` geladen und blockieren den ersten Aufbau nicht. Die Anwendung kontaktiert zur Laufzeit keinen externen Host.

| Modul | Aufgabe |
|---|---|
| `app.js` | Daten laden, Zustand, Hash-Routing, Ergebnisliste, Karten, Editiermodus-Schalter |
| `constants.js` | Typ- und Periodenlabels, Farbkonstanten, Chart-Maße |
| `utils.js` | Escaping, Highlighting, Zähl- und Downloadhelfer |
| `home.js` | Startansicht mit Kennzahlen und Einstiegen |
| `facets.js` | Facettenleiste der Ergebnisansicht |
| `detail.js` | Eintragsdetail in zwei Layouts: kompakte Leseansicht, Adjudikationstabelle im Editiermodus |
| `edit.js` | lokale Feld- und Reconciliation-Kuration, Triage-Hinweise, Fundstellen, Patch-Export |
| `curate.js` | Datenqualitäts-Werkbank (`#quality`): Vollständigkeitsmatrix, Arbeitsvorräte, Kandidaten-Queue |
| `export.js` | BibTeX-, RIS-, Einzel- und Gesamtexport, Permalink |
| `pages.js` | die beiden statischen Seiten About und Data, Zahlen dynamisch aus `_meta` |
| `jsonld-playground.js` | interaktive JSON-LD-Ansicht mit escaptem Syntax-Highlighting, als Abschnitt der Data-Seite gerendert |
| `explore.js` | Explore-Rahmen: Modi, geteilte Filter, URL-Zustand, Detailpanel |
| `explore-timeline.js` | Zeitverlauf mit Sprach-, Typ- und Provenienz-Schichten |
| `explore-geography.js` | Globus- und Kartenansicht aus der vendorten Geometrie |
| `explore-network.js` | Referenz-Rangliste (meistreferenzierte Einträge) und Übersetzer-Sankey |

Die Anwendung lädt `docs/data/klawiter.json` (blockierend, mit `resp.ok`-Prüfung und escapter Fehlermeldung), `reconciliation.json` (nicht blockierend, additive Kurationsdaten) und `triage.json` (erst beim Betreten des Editiermodus). Der Suchindex wird lazy bei der ersten Suche gebaut. Fehlende Reconciliation-Daten führen nicht zu erfundenen Links; die betroffenen UI-Bereiche bleiben leer.

## Navigation, Routen und Seitenzuschnitt

Die Kopfnavigation führt vier Ziele, Overview, Explore, Data und About. Ein Dropdown gibt es nicht mehr; alles, was dort lag, ist in die beiden Textseiten eingegangen oder steht im Footer. Der Footer trägt zwei Spalten, links Kompilator, herausgebendes Umfeld und die Lizenzzeile, rechts die Verweise.

| Route | Inhalt |
|---|---|
| `#` | Startseite mit Suche, Browse-Einstieg und den Kategoriengruppen als Karten |
| `#stats`, `#stats/<modus>` | Explore mit Zeit-, Karten- und Verbindungsansicht |
| `#data`, `#data/<abschnitt>` | Datenmodell, Spezifikation und Vokabular, Downloads, JSON-LD-Playground, Verweis auf die Werkbank |
| `#about`, `#about/<abschnitt>` | Projekt, Methodik, Hilfe, Impressum als Abschnitte einer Seite mit Anker-Navigation |
| `#quality` | Datenqualitäts-Werkbank |
| `#browse`, `#q=…`, `#entry=…`, Facettenparameter | Ergebnisliste |

Eine statische Seite adressiert ihre Abschnitte über ein Suffix im Hash (`#about/imprint`); der Router rendert die Seite und scrollt anschließend auf `sec-<abschnitt>`. Die vier Deep-Links der früheren Seitenaufteilung bleiben gültig und werden im Router auf ihren Abschnitt umgeschrieben, `#methodology` und `#help` und `#imprint` nach `#about/…`, `#jsonld` nach `#data/playground`. Der Dokumenttitel wird ausschließlich in `App._updateTitle` gesetzt, Basistitel „Klawiter — Stefan Zweig Bibliography" wie im ausgelieferten HTML.

Die About-Seite führt die Zahlen des Bestands dynamisch aus `_meta` (Bestandsgröße, Sprachen, Jahresspanne, Feldabdeckung, Typenzahl), damit Prosa und Datenstand nicht auseinanderlaufen. Die Data-Seite benennt die ausgelieferten Dateien unter `docs/data/` mit ihrer Rolle und weist die kanonischen Graphen unter `data/output/` als nur über das Repository erreichbar aus. Der Gesamtexport heißt „Download dataset (JSON)", weil er die flache Projektion in Frontend-Schlüsseln liefert und keinen `@context` trägt.

## Gestaltungs- und Zugänglichkeitsvertrag

Die Oberfläche verwendet die etablierte Stefan-Zweig-Digital-Palette, Source Serif 4 für Lesetext und Source Sans 3 für Navigation und Bedienung. CSS-Variablen sind die einzige Quelle für Farben und Abstände. Bibliotheken und Fonts liegen lokal.

Semantisches HTML, sichtbarer Tastaturfokus, beschriftete Formulare, ARIA-Labels für ikonische Steuerelemente und ausreichende Kontraste bilden die Basis. `prefers-reduced-motion` wird global respektiert (Animationen und Smooth-Scrolling entfallen). Inhaltliche Zustände werden nie ausschließlich über Farbe vermittelt. Mobile Layouts bewahren Suche, Filter und Detailinformationen ohne horizontales Scrollen; die Vollständigkeitsmatrix scrollt in ihrem eigenen Container.

## Rechercheansichten

- Die Übersicht zeigt Umfang, zeitliche Verteilung, Sprachen, Typen und Orte.
- Die Ergebnisliste kombiniert Textsuche, Facetten und Sortierung. Die Karte zeigt Typ, Titel, Jahr, Sprache, Ort, Verlag und Seitenzahl; der Quelltext-Auszug entfällt, weil die aufgeklappte Karte den Volleintrag führt.
- Die aufgeklappte Leseansicht ergänzt nur, was der Kartenkopf nicht trägt (Originaltitel, Übersetzer, Kategorien, Wikidata-Ortslink), rendert die Contents als strukturierte Liste mit Seitenangaben und hält den vollständigen Klawiter-Originaleintrag als eingeklappte Quelle. Strittige Claims bleiben in der Leseansicht sichtbar.
- Zeit-, Karten- und Verbindungsansichten leiten ihre Daten aus derselben gefilterten Record-Menge ab. Die Verbindungsansicht ist eine Rangliste der meistreferenzierten Seiten mit aufklappbaren Verweislisten; der frühere globale Communities-Graph ist entfernt, weil sein größter Knoten die Restmüll-Aggregation war und er keine bibliographische Frage beantwortete. Der Übersetzer-Sankey bleibt; Mehrfachnennungen werden an Konjunktionen aufgeteilt, abgeschnittene Werte ausgeschlossen, Kleinstknoten in „Other translators" gebündelt.
- Explore-Konventionen nach der Fix-Runde: fehlende Sprache heißt in allen drei Ansichten „Not recorded" und bleibt von „Other languages" (seltene, erfasste Sprachen) getrennt; jede Ansicht benennt, was sie nicht zeichnet (jahrlose Einträge, nicht geokodierte Orte) und öffnet diese Mengen als Ergebnisliste; das Provenienz-Overlay ist ein eigener Streifen unter der Zeitachse; die Modusreiter sind schlichte Buttons mit `aria-pressed`, die SVGs `role="group"`, die Legenden echte, filternde Buttons als Tastaturweg; `prefers-reduced-motion` nullt alle d3-Transitionsdauern. Klickwege übergeben ihre Filter vollständig an die Ergebnisroute, die dafür auch `publisher`, `translator` und Jahresbereiche kennt; nur der Länderfilter der Karte bleibt sitzungsgebunden, weil die Ergebnisroute `locations.json` nicht lädt.
- Weiterleitungen erscheinen nicht als eigene Suchtreffer; die Redirect-Map (inklusive Seitentitel-Aliasse aus Stufe 05) leitet Suchanfragen und Querverweise zum kanonischen Eintrag.

## Datenqualitäts-Werkbank (`#quality`)

Die Route `#quality` beantwortet die Kurationsfrage, ob alle Daten sauber bearbeitet sind, aus den publizierten Artefakten selbst:

- Statuszeile mit Bestandsgröße, Prüfhinweis-, LLM-, Referenz-, Normdaten- und Claim-Zählern, live berechnet.
- Vollständigkeitsmatrix Feld × Eintragstyp; jede Zelle mit Lücken öffnet die betroffenen Einträge als Ergebnisliste.
- Arbeitsvorräte als klickbare Listen: Census-Anomalien, nicht im Quelltext belegte Werte, erkennbare aber nicht extrahierte Werte, LLM-abgeleitete Felder, unauflösbare Querverweise (mit Liste der häufigsten Rotlink-Ziele), strittige Normdatenclaims.
- Kandidaten-Queue für Übersetzer- und Verlagsnamen: subjektbezogen, sortiert offene Fälle nach Reichweite (Vorkommenszahl) zuerst. Öffentlich lesbar; entscheiden lässt sie sich nur im lokalen Editiermodus, dort mit Tastatur (Pfeile/j/k bewegen, y bestätigt den Top-Kandidaten, n lehnt ab, Enter zeigt die betroffenen Einträge).

Die Werkbank-Listen sind Sitzungsansichten ohne eigene Hash-Adresse, weil sie aus Artefakten und nicht aus Filterzustand abgeleitet sind.

## EIL Curation Interface

Der Editiermodus ist ausschließlich auf `localhost` aktiv; der Schalter prüft `isLocal` im Setter, die publizierte Site kann den Modus auch über die Konsole nicht betreten. Der Schalter im Kopf ist zusätzlich viewabhängig sichtbar und erscheint nur dort, wo Edieren tatsächlich ansetzt, auf Startseite, Ergebnisliste und Werkbank; auf den Textseiten und in Explore ist er ausgeblendet. Der Modus-Zustand selbst bleibt über den Viewwechsel erhalten. Bearbeitet werden Verlag, Publikationsort, Übersetzer und Seitenzahl. Jede Feldaktion ist typisiert:

- `accept` bestätigt einen vorhandenen Wert;
- `correct` ersetzt einen Wert und bewahrt den Vorgänger;
- `add` ergänzt einen zuvor leeren Wert.

Für jede Aktion zeigt die Oberfläche die belegbare Textstelle oder den vollständigen Quelltext. Triage-Hinweise priorisieren Round-Trip-Abweichungen, fehlende oder modellgestützte Provenienz sowie Census-Anomalien; eine Provenienz-Legende erklärt die R/L/E-Badges. Im Editiermodus laufen j/k als Kartennavigation durch die Ergebnisliste, und die Sortierung „Needs review first" ordnet nach dringlichstem Datensignal. Laufende Änderungen bleiben bis zum Export in `localStorage`; der Save-Zähler im Kopf zeigt den ungesicherten Stand.

Die Orts-Reconciliation bietet `confirm`, `reject` und `unresolved`; `unresolved` hält konkurrierende Deutungen als offenen Claim fest. Übersetzer- und Verlagskandidaten bieten dieselben Aktionen, seit Gate 2 je Agentsubjekt die Fundstellen aus der klassifizierten Quelle erhebt und `docs/data/reconciliation.json` sie unter `sourceOccurrences` ausweist; eine unaufgelöste Agent-Entscheidung ist damit quellengebunden belegt. Beide Kandidatenarten sind subjektbezogen; die Oberfläche weist die Reichweite („applies to N entries") aus. Kandidaten bleiben Vorschläge; nichts publiziert ohne Entscheidung. Der kombinierte Export verwendet `patchVersion: 2` und `reconciliationPatchVersion: 1`.

Der Prüfstatus-Chip liest das `review`-Feld des Eintrags, dessen Semantik in [[data]] steht. Ein Eintrag ohne dieses Feld bleibt ungeprüft, eine ungesicherte Bearbeitung der laufenden Sitzung bleibt ein eigener Zustand der Oberfläche.

## Darstellung strittiger Aussagen

Bestätigte Beziehungen und strittige Aussagen werden getrennt gerendert. Ein offener Normdatenclaim zeigt Quellenwert, Kandidaten, Entscheidungsgeschichte und offenen Status. Der Adaptionsfall auf Seite 4916 zeigt beide Werkdeutungen, Quellenkennung und Reviews.

Die UI erzeugt aus einem strittigen Kandidaten keinen klickbaren bestätigten Normdatenlink. Kennzahlen zählen ausschließlich publizierbare Beziehungen. Die Anzahl offener Claims wird getrennt ausgewiesen.

## Export

- BibTeX und RIS dienen der Zitationsweitergabe der flachen Records.
- Der JSON-LD-Einzelexport ergänzt vorhandene Editionsclaims als eigene Graphknoten.
- Der Gesamtexport enthält strittige Editions- und Normdatenclaims zusätzlich zu den bestätigten Beziehungen.
- Die kanonischen vollständigen Graphen bleiben `data/output/editions/work-editions.jsonld` und die Gate-2-Artefakte unter `data/output/reconciliation/`.

Ein Claim mit Prädikat `schema:exampleOfWork` wird exportiert, ohne gleichzeitig die entsprechende bestätigte Beziehung am Editionsknoten zu setzen.

## Validierung

Node-Tests prüfen Fundstellenlogik, Triage-Reihenfolge, Reconciliation-Lookup, stabilen Patch-Export, die Trennung strittiger Claims, den Routing-Guard samt Editiermodus-Gate, die Redirects der alten Deep-Links, den Abschnitts-Suffix statischer Seiten, die Sichtbarkeitsregel des Edit-Schalters und die Ordnung der Kandidaten-Queue. `node --check` validiert jedes Modul syntaktisch. Die Python-Suite prüft die erzeugten Datenverträge (inklusive Frontend-Projektionsvertrag) und ruft die Node-Tests über die gemeinsame Testbrücke auf.

Ein lokaler Smoke-Test läuft mit einem statischen Server über `docs/`:

```bash
python -m http.server 8000 --directory docs
```

Die Anwendung ist danach unter `http://localhost:8000/` erreichbar; nur dort ist die Kurationsoberfläche aktiv.

## Deployment und Grenzen

GitHub Pages veröffentlicht den Inhalt von `docs/`. Die Anwendung führt keine Live-Rückschreibung aus. Exporte werden lokal heruntergeladen und anschließend als geprüfte Repository-Patches integriert.

Die flache Detailseite kann editionenspezifische Felder auf Mehrfachausgabenseiten nicht vollständig trennen. Der Editionsgraph und seine Queue bleiben für diese Fälle maßgeblich. Titelbearbeitung und institutionelle Werkentscheidungen gehören nicht zum aktuellen lokalen Editor.

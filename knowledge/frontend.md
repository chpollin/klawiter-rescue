---
title: Oberfläche und Kuration
aliases: [frontend, interface, EIL, curation tool]
project:
  name: Klawiter Bibliography
  repository: https://github.com/chpollin/klawiter-rescue
status: complete
language: de
version: 1.4
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

`docs/index.html` lädt klassische Skripte (kein Modulsystem, gemeinsamer globaler Namensraum) und lokal vendorte Abhängigkeiten (`docs/vendor/`: FlexSearch, D3 v7, topojson-client, d3-sankey, `countries-110m.json` mit Provenienzvermerk). FlexSearch ist `defer` geladen, weil jeder Besuch den Suchindex braucht. Die drei Visualisierungs-Bundles lädt `App.ensureExploreLibs` erst beim ersten Wechsel auf `#stats` in fester Reihenfolge nach und rendert Explore hinter einem einmaligen Promise-Gate; scheitert der Nachladevorgang, zeigt die Explore-Ansicht eine Fehlermeldung mit Retry, während Suche und Ergebnisliste unberührt weiterlaufen. Die Anwendung kontaktiert zur Laufzeit keinen externen Host.

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
| `jsonld-playground.js` | interaktive JSON-LD-Ansicht mit escaptem Syntax-Highlighting, als Abschnitt der Data-Seite gerendert; adressierbar über `#data/playground/<pageId>`, Vorschlagsliste als `listbox` mit Pfeil- und Enter-Bedienung und eigenem Leerzustand, Ansichts-Buttons mit `aria-pressed`, Dokument-Listener einmalig registriert, Eintragstypen aus `constants.js` |
| `explore.js` | Explore-Rahmen: Modi, geteilte Filter, URL-Zustand, Detailpanel |
| `explore-timeline.js` | Zeitverlauf mit Sprach-, Typ- und Provenienz-Schichten |
| `explore-geography.js` | Globus- und Kartenansicht aus der vendorten Geometrie |
| `explore-network.js` | Referenz-Rangliste (meistreferenzierte Einträge) und Übersetzer-Sankey |

Die Anwendung lädt `docs/data/klawiter.json` blockierend mit `resp.ok`-Prüfung. Scheitert dieser Ladevorgang, tritt ein ganzseitiger Fehlerzustand an die Stelle der Startansicht, der die Ursache benennt und einen Retry anbietet; Navigation und Suchfeld sind dabei sichtbar deaktiviert, weil ohne Bestand keine von beiden etwas auflöst. `reconciliation.json` wird dort geladen, wo die Daten zum ersten Mal sichtbar werden (aufgeklappte Karte, Editiermodus, Werkbank), über eine geteilte Ladezusage, und eine bereits offene Karte wird nach dem Eintreffen aufgefrischt. `triage.json` kommt erst beim Betreten des Editiermodus. Der Suchindex wird nach dem ersten Paint über `requestIdleCallback` vorgebaut, mit `setTimeout`-Fallback und Lazy-Bau bei der ersten Suche als Rückfallweg. Die Datenverifikation (`verifyData`) läuft nur auf `localhost`, weil sie ein Entwicklungsinstrument ist und mehrere Vollpässe über den Bestand kostet. Fehlende Reconciliation-Daten führen nicht zu erfundenen Links; die betroffenen UI-Bereiche bleiben leer.

## Navigation, Routen und Seitenzuschnitt

Die Kopfnavigation führt vier Ziele, Overview, Explore, Data und About. Ein Dropdown gibt es nicht mehr; alles, was dort lag, ist in die beiden Textseiten eingegangen oder steht im Footer. Der Footer trägt zwei Spalten, links Kompilator, herausgebendes Umfeld und die Lizenzzeile, rechts die Verweise.

| Route | Inhalt |
|---|---|
| `#` | Startseite mit Suche, Browse-Einstieg und den Kategoriengruppen als Karten |
| `#stats`, `#stats/<modus>` | Explore mit Zeit-, Karten- und Verbindungsansicht |
| `#data`, `#data/<abschnitt>` | Datenmodell, Spezifikation und Vokabular, Downloads, JSON-LD-Playground, Verweis auf die Werkbank |
| `#data/playground/<pageId>` | Playground mit vorgeladenem Eintrag; die Aktionsleiste der Eintragskarte verlinkt als „View as JSON-LD" dorthin |
| `#about`, `#about/<abschnitt>` | Projekt, Methodik, Hilfe, Impressum als Abschnitte einer Seite mit Anker-Navigation |
| `#quality` | Datenqualitäts-Werkbank |
| `#browse`, `#q=…`, `#entry=…`, Facettenparameter | Ergebnisliste |

Benutzerausgelöste Zustandswechsel (Facette wählen, Chip entfernen, Suche übernommen, Sortierung) schreiben einen echten History-Eintrag; `replaceState` bleibt den Normalisierungen vorbehalten, die einen bereits in der URL stehenden Zustand nur nachziehen. Damit führt der Zurück-Weg durch die Rechercheschritte, statt die Anwendung nach der ersten Interaktion zu verlassen. Der Router ignoriert das Fragment `#main-content` des Skip-Links, weil es ein Element adressiert und keine Route.

Ein `#entry=`-Permalink beschriftet die Ergebniszeile nach dem Render als „Permalink — 1 entry". Löst die Kennung nicht auf, erscheint ein eigener Zustand mit dem Hinweis auf eine mögliche Weiterleitung und einem Weg zur Startseite; ein `#title=` ohne Treffer in Redirect-Map und Titelindex führt zum selben Zustand, statt still auf die Startseite durchzufallen. Die statischen Seiten und `#quality` setzen Query, Filter und Suchfeld zurück wie der Explore-Zweig.

Eine statische Seite adressiert ihre Abschnitte über ein Suffix im Hash (`#about/imprint`); der Router rendert die Seite und scrollt anschließend auf `sec-<abschnitt>`. Die vier Deep-Links der früheren Seitenaufteilung bleiben gültig und werden im Router auf ihren Abschnitt umgeschrieben, `#methodology` und `#help` und `#imprint` nach `#about/…`, `#jsonld` nach `#data/playground`. Der Dokumenttitel wird ausschließlich in `App._updateTitle` gesetzt, Basistitel „Klawiter — Stefan Zweig Bibliography" wie im ausgelieferten HTML.

Die About-Seite führt die Zahlen des Bestands dynamisch aus `_meta` (Bestandsgröße, Sprachen, Jahresspanne, Feldabdeckung, Typenzahl), damit Prosa und Datenstand nicht auseinanderlaufen. Die Data-Seite benennt die ausgelieferten Dateien unter `docs/data/` mit ihrer Rolle und weist die kanonischen Graphen unter `data/output/` als nur über das Repository erreichbar aus. Der Gesamtexport heißt „Download dataset (JSON)", weil er die flache Projektion in Frontend-Schlüsseln liefert und keinen `@context` trägt.

## Gestaltungs- und Zugänglichkeitsvertrag

Die Oberfläche verwendet die etablierte Stefan-Zweig-Digital-Palette, Source Serif 4 für Lesetext und Source Sans 3 für Navigation und Bedienung. CSS-Variablen sind die einzige Quelle für Farben und Abstände. Bibliotheken und Fonts liegen lokal.

Semantisches HTML, sichtbarer Tastaturfokus, beschriftete Formulare, ARIA-Labels für ikonische Steuerelemente und ausreichende Kontraste bilden die Basis. Nach einem Ansichtswechsel setzt `showView` den Fokus auf die Überschrift der Ansicht oder auf `#main-content`, damit die Hash-Navigation bei Screenreadern ankommt; ein Wechsel, der aus dem Tippen im Suchfeld folgt, lässt den Fokus dort. Alle Tastaturkürzel steigen bei gedrückter Steuerungs-, Meta- oder Alt-Taste aus. `prefers-reduced-motion` wird global respektiert (Animationen und Smooth-Scrolling entfallen). Inhaltliche Zustände werden nie ausschließlich über Farbe vermittelt. Mobile Layouts bewahren Suche, Filter und Detailinformationen ohne horizontales Scrollen; die Vollständigkeitsmatrix scrollt in ihrem eigenen Container.

## Rechercheansichten

- Die Übersicht zeigt Umfang, zeitliche Verteilung, Sprachen, Typen und Orte.
- Die Ergebnisliste kombiniert Textsuche, Facetten und Sortierung. Die Karte zeigt Typ, Titel, Jahr, Sprache, Ort, Verlag und Seitenzahl; der Quelltext-Auszug entfällt, weil die aufgeklappte Karte den Volleintrag führt. Der Kartenkopf führt `aria-expanded` und `aria-controls` auf die Detail-ID.
- Der Suchindex faltet Diakritika (`charset: 'latin:advanced'`), damit die Transliterationen des Bestands auch in schlichter Schreibweise auffindbar sind. Ab zwei Zeichen läuft eine Suche, darunter keine. Die Trefferzahl ist auf 5.000 gekappt; ist die Kappung erreicht, sagt das Ergebnislabel es. Kopf- und Startseitenfeld hängen am selben Handler, das Startseitenfeld wird beim Rendern mit der aktuellen Query vorbelegt, und beim Wechsel auf die Ergebnisansicht wandert der Fokus in das Kopffeld. Markiert wird auf dem Rohtext und escapt wird segmentweise, damit Apostroph, Ampersand und Anführungszeichen in der Query treffen und keine Entity zerrissen wird.
- Facettenzähler folgen dem Standard-Drilldown: jede Facette zählt gegen die Menge, die alle anderen Filter anwendet, sodass die Alternativen einer gewählten Facette wählbar bleiben. Sprache und Ort zeigen die häufigsten Werte und klappen je Gruppe auf den vollen Bestand auf. Chips tragen beschriftete Schließer und ab zwei aktiven Filtern einen „Clear all"-Chip; der Leerzustand bietet dieselbe Aktion an.
- Die mobile Schublade verschiebt die Sidebar per DOM-Move in das Overlay und beim Schließen zurück, statt ihr Markup zu klonen. Der Fokus springt beim Öffnen auf den Schließen-Button, bleibt zyklisch im Panel, Escape schließt, eine Auswahl schließt, und der Fokus kehrt zum Öffner zurück. Der mobile Filter-Button erscheint nur auf der Ergebnisansicht.
- Die aufgeklappte Leseansicht ergänzt nur, was der Kartenkopf nicht trägt (Originaltitel, Übersetzer, Kategorien, Wikidata-Ortslink), rendert die Contents als strukturierte Liste mit Seitenangaben und hält den vollständigen Klawiter-Originaleintrag als eingeklappte Quelle. Trägt ein Eintrag außer dem Volleintrag nichts, wird die Quelle aufgeklappt gerendert, weil eine Aufklappung, die nur aus einer zugeklappten Zeile besteht, leer wirkt. Strittige Claims bleiben in der Leseansicht sichtbar, ebenso der Prüfstatus-Chip, der in beiden Layouts steht. Ein Kategorienlink filtert auf die Kategorie selbst (`#category=`); ein Contents-Item, dessen Titel einen eigenen Eintrag hat, wird zum `#entry=`-Link.
- Zeit-, Karten- und Verbindungsansichten leiten ihre Daten aus derselben gefilterten Record-Menge ab. Die Verbindungsansicht ist eine Rangliste der meistreferenzierten Seiten mit aufklappbaren Verweislisten; der frühere globale Communities-Graph ist entfernt, weil sein größter Knoten die Restmüll-Aggregation war und er keine bibliographische Frage beantwortete. Der Übersetzer-Sankey bleibt; Mehrfachnennungen werden an Konjunktionen aufgeteilt, abgeschnittene Werte ausgeschlossen, Kleinstknoten in „Other translators" gebündelt.
- Explore-Konventionen nach der Fix-Runde: fehlende Sprache heißt in allen drei Ansichten „Not recorded" und bleibt von „Other languages" (seltene, erfasste Sprachen) getrennt; jede Ansicht benennt, was sie nicht zeichnet (jahrlose Einträge, nicht geokodierte Orte) und öffnet diese Mengen als Ergebnisliste; das Provenienz-Overlay ist ein eigener Streifen unter der Zeitachse; die Modusreiter sind schlichte Buttons mit `aria-pressed`, die SVGs `role="group"`, die Legenden echte, filternde Buttons als Tastaturweg; `prefers-reduced-motion` nullt alle d3-Transitionsdauern. Klickwege übergeben ihre Filter vollständig an die Ergebnisroute, die dafür auch `publisher`, `translator` und Jahresbereiche kennt; nur der Länderfilter der Karte bleibt sitzungsgebunden, weil die Ergebnisroute `locations.json` nicht lädt.
- Weiterleitungen erscheinen nicht als eigene Suchtreffer; die Redirect-Map (inklusive Seitentitel-Aliasse aus Stufe 05) leitet Suchanfragen und Querverweise zum kanonischen Eintrag.

## Datenqualitäts-Werkbank (`#quality`)

Die Route `#quality` beantwortet die Kurationsfrage, ob alle Daten sauber bearbeitet sind, aus den publizierten Artefakten selbst:

- Statuszeile mit Bestandsgröße, Prüfhinweis-, LLM-, Referenz-, Normdaten- und Claim-Zählern, live berechnet.
- Vollständigkeitsmatrix Feld × Eintragstyp; jede Zelle mit Lücken öffnet die betroffenen Einträge als Ergebnisliste.
- Arbeitsvorräte als klickbare Listen: Census-Anomalien, nicht im Quelltext belegte Werte, erkennbare aber nicht extrahierte Werte, LLM-abgeleitete Felder, unauflösbare Querverweise (mit Liste der häufigsten Rotlink-Ziele), strittige Normdatenclaims.
- Kandidaten-Queue für Übersetzer- und Verlagsnamen: subjektbezogen, sortiert offene Fälle nach Reichweite (Vorkommenszahl) zuerst. Öffentlich lesbar; entscheiden lässt sie sich nur im lokalen Editiermodus.

Die Queue ist eine `listbox` mit wanderndem Tabindex, also ein einziger Tabstopp, der auf der Zeile aufsetzt, an der die Arbeit beginnt (zuletzt bearbeitetes Subjekt, sonst erster offener Fall). Tastenweg im Editiermodus: Pfeile und j/k bewegen, y bestätigt den Top-Kandidaten, n lehnt ab, u hält offen, z und Backspace nehmen die letzte Entscheidung zurück, Enter öffnet die betroffenen Einträge. Alle Queue-Tasten steigen bei gedrückter Steuerungs-, Meta- oder Alt-Taste aus. Der Rückweg aus der Ergebnisliste findet das zuletzt bearbeitete Subjekt über seine Kennung wieder, scrollt darauf und setzt den Fokus. Jede Zeile zeigt den Top-Kandidaten und hält die weiteren in einem aufklappbaren Block mit eigenem Bestätigen-Button je Kandidat, damit eine Entscheidung nicht auf den höchsten Score gezwungen wird. Ein Neuzeichnen der Queue schreibt das Statuspanel darüber mit fort, weil dessen Zähler der laufenden Sitzung sonst dem Save-Zähler widerspricht.

Scheitert `triage.json` oder `reconciliation.json`, hält der Ladezustand das im Modul fest, und die betroffenen Zähler und Blöcke weisen sich als „not available (failed to load)" aus. Ein Ladefehler ist damit von einem sauberen Bestand unterscheidbar.

Die Werkbank-Listen sind Sitzungsansichten ohne eigene Hash-Adresse, weil sie aus Artefakten und nicht aus Filterzustand abgeleitet sind. Der Dokumenttitel übernimmt dann das Listenlabel, und über der Liste steht ein sichtbarer Rückweg auf die Ansicht, aus der sie geöffnet wurde (Werkbank oder Explore).

## EIL Curation Interface

Der Editiermodus ist ausschließlich auf `localhost` aktiv; der Schalter prüft `isLocal` im Setter, die publizierte Site kann den Modus auch über die Konsole nicht betreten. Der Schalter im Kopf ist zusätzlich viewabhängig sichtbar und erscheint nur dort, wo Edieren tatsächlich ansetzt, auf Startseite, Ergebnisliste und Werkbank; auf den Textseiten und in Explore ist er ausgeblendet. Der Modus-Zustand selbst bleibt über den Viewwechsel erhalten. Bearbeitet werden Verlag, Publikationsort, Übersetzer und Seitenzahl. Jede Feldaktion ist typisiert:

- `accept` bestätigt einen vorhandenen Wert;
- `correct` ersetzt einen Wert und bewahrt den Vorgänger;
- `add` ergänzt einen zuvor leeren Wert.

Für jede Aktion zeigt die Oberfläche die belegbare Textstelle oder den vollständigen Quelltext. Triage-Hinweise priorisieren Round-Trip-Abweichungen, fehlende oder modellgestützte Provenienz sowie Census-Anomalien; eine Provenienz-Legende erklärt die R/L/E-Badges. Im Editiermodus laufen j/k als Kartennavigation durch die Ergebnisliste, und die Sortierung „Needs review first" ordnet nach dringlichstem Datensignal.

Ein Feld mit offener Korrektur zeigt den korrigierten Wert; der ersetzte Datenbestandswert steht durchgestrichen daneben, sodass ein Re-Render die eben getippte Eingabe nicht scheinbar zurücknimmt. Ein leeres Feld trägt neben der Platzhalterfläche einen beschrifteten Add-Button, der es fokussiert. In einem `contenteditable`-Feld schließt Enter die Eingabe ab (Zeilenumbruch unterbunden, Feld verlassen) und Escape verwirft sie auf den gerenderten Stand zurück; jedes Feld führt `role="textbox"` und ein `aria-label` mit dem Feldnamen. Sämtliche Bedienelemente der Karte laufen über Event-Delegation mit Data-Attributen, in der Aktionsleiste ebenso wie in den Kandidatenblöcken; Orts- und Agent-Kandidaten teilen sich einen Renderer, der über die Subjektart parametrisiert ist.

Laufende Änderungen bleiben bis zum Export in `localStorage`, zusammen mit dem Zeitstempel des letzten Schreibvorgangs; der Save-Zähler im Kopf zeigt den ungesicherten Stand und bei einer aus einer früheren Sitzung wiederhergestellten Lage den Vermerk „resumed from <Datum>". Bringt ein Reload offene Entscheidungen zurück, ohne dass der Editiermodus an ist, steht neben dem Zähler eine Notiz, dass der Modus für die Weiterarbeit einzuschalten ist. Nach dem Patch-Download fragt die Oberfläche, ob die Sitzung geleert wird oder mit den offenen Entscheidungen weiterläuft, weil der Download allein über den Verbleib der Sitzung nichts aussagt.

Der Sitzungszustand ist von der Datenlage getrennt. Eine ungesicherte Feldaktion macht den Eintrag „edited (unsaved)"; „approved" bleibt der `review`-Projektion des Datenbestands vorbehalten, die die Pipeline nach angewandtem Patch schreibt.

Die Orts-Reconciliation bietet `confirm`, `reject` und `unresolved`; `unresolved` hält konkurrierende Deutungen als offenen Claim fest. Übersetzer- und Verlagskandidaten bieten dieselben Aktionen, seit Gate 2 je Agentsubjekt die Fundstellen aus der klassifizierten Quelle erhebt und `docs/data/reconciliation.json` sie unter `sourceOccurrences` ausweist; eine unaufgelöste Agent-Entscheidung ist damit quellengebunden belegt. Beide Kandidatenarten sind subjektbezogen; die Oberfläche weist die Reichweite („applies to N entries") aus. Kandidaten bleiben Vorschläge; nichts publiziert ohne Entscheidung. Der kombinierte Export verwendet `patchVersion: 2` und `reconciliationPatchVersion: 1`.

Der Prüfstatus-Chip liest das `review`-Feld des Eintrags, dessen Semantik in [[data]] steht. Ein Eintrag ohne dieses Feld bleibt ungeprüft, eine ungesicherte Bearbeitung der laufenden Sitzung bleibt ein eigener Zustand der Oberfläche.

## Darstellung strittiger Aussagen

Bestätigte Beziehungen und strittige Aussagen werden getrennt gerendert. Ein offener Normdatenclaim zeigt Quellenwert, Kandidaten, Entscheidungsgeschichte und offenen Status. Der Adaptionsfall auf Seite 4916 zeigt beide Werkdeutungen, Quellenkennung und Reviews.

Die UI erzeugt aus einem strittigen Kandidaten keinen klickbaren bestätigten Normdatenlink. Kennzahlen zählen ausschließlich publizierbare Beziehungen. Die Anzahl offener Claims wird getrennt ausgewiesen.

## Export

- BibTeX und RIS dienen der Zitationsweitergabe der flachen Records. Beide lesen dieselbe Typregel und legen den Permalink bei (`url` beziehungsweise `UR`); der erfasste Seitenumfang steht in `pagetotal`, weil `pages` den Seitenbereich innerhalb eines Behälters meint. Ein Lauf auf `localhost` oder über `file://` zitiert die publizierte Adresse, damit der Link beim Empfänger auflöst.
- Der Gesamtexport der Ergebnisliste beschriftet sich mit der Trefferzahl und fragt oberhalb von tausend Einträgen zurück.
- Das Kopieren des Permalinks fängt eine verweigerte Zwischenablage ab und bietet die Adresse dann in einem auswählbaren Feld an.
- Der JSON-LD-Einzelexport ergänzt vorhandene Editionsclaims als eigene Graphknoten.
- Der Gesamtexport enthält strittige Editions- und Normdatenclaims zusätzlich zu den bestätigten Beziehungen.
- Die kanonischen vollständigen Graphen bleiben `data/output/editions/work-editions.jsonld` und die Gate-2-Artefakte unter `data/output/reconciliation/`.

Ein Claim mit Prädikat `schema:exampleOfWork` wird exportiert, ohne gleichzeitig die entsprechende bestätigte Beziehung am Editionsknoten zu setzen.

## Validierung

Node-Tests prüfen Fundstellenlogik, Triage-Reihenfolge, Reconciliation-Lookup, stabilen Patch-Export, die Trennung strittiger Claims, den Routing-Guard samt Editiermodus-Gate, die Redirects der alten Deep-Links, den Abschnitts-Suffix statischer Seiten, die Sichtbarkeitsregel des Edit-Schalters und die Ordnung der Kandidaten-Queue. `tests/edit_session.test.js` hält den Sitzungszustand fest: gerendeter Korrekturwert mit durchgestrichenem Vorgänger, Add-Bedienelement am leeren Feld, „edited" statt „approved", der Index über strittige Claims, der Kategorienlink, Prüfstatus-Chip und aufgeklappte Quelle in der Leseansicht sowie die Playground-Route. Dazu kommen die Suchzusagen in `tests/search_logic.test.js` (Diakritika-Faltung des Index, Markieren gegen Escaping, Mindestquerylänge, Facetten-Drilldown, Labelauflösung und Kappungsnotiz) sowie die History-Zusage und die Fehlrouten in `tests/routing_guard.test.js`. `node --check` validiert jedes Modul syntaktisch. Die Python-Suite prüft die erzeugten Datenverträge (inklusive Frontend-Projektionsvertrag) und ruft die Node-Tests über die gemeinsame Testbrücke auf.

Ein lokaler Smoke-Test läuft mit einem statischen Server über `docs/`:

```bash
python -m http.server 8000 --directory docs
```

Die Anwendung ist danach unter `http://localhost:8000/` erreichbar; nur dort ist die Kurationsoberfläche aktiv.

## Deployment und Grenzen

GitHub Pages veröffentlicht den Inhalt von `docs/`. Die Anwendung führt keine Live-Rückschreibung aus. Exporte werden lokal heruntergeladen und anschließend als geprüfte Repository-Patches integriert.

Die flache Detailseite kann editionenspezifische Felder auf Mehrfachausgabenseiten nicht vollständig trennen. Der Editionsgraph und seine Queue bleiben für diese Fälle maßgeblich. Titelbearbeitung und institutionelle Werkentscheidungen gehören nicht zum aktuellen lokalen Editor.

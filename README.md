# Klawiter Bibliography

Die Klawiter Bibliography erschließt die von Randolph J. Klawiter zusammengestellte Stefan-Zweig-Bibliographie aus einer stillgelegten MediaWiki-Datenbank. Das Repository enthält die reproduzierbare Extraktions- und Modellierungspipeline, die JSON-LD-Daten, eine statische Rechercheoberfläche und die beleggebundene Kurationsschicht.

Die veröffentlichte Oberfläche liegt unter [chpollin.github.io/klawiter-rescue](https://chpollin.github.io/klawiter-rescue/).

## Gegenstand und Datenbestand

Die Quelldaten umfassen 6.725 MediaWiki-Seiten in mehreren Namensräumen. Davon sind 6.296 Bibliographieseiten im Hauptnamensraum. Eine Seite, `page_id 2979`, besitzt in den gelieferten BLOB-Dateien keinen Textkörper und bleibt deshalb als belegter Stub erhalten.

Der Produktionslauf erzeugt zwei komplementäre Darstellungen:

- Der flache Kompatibilitätsbestand enthält 6.725 JSON-LD-Einträge einschließlich 1.546 Weiterleitungen. Die Oberfläche verwendet 5.179 Nicht-Weiterleitungen und zeigt 4.751 Einträge aus dem Hauptnamensraum.
- Das Werk-/Ausgabe-Modell segmentiert alle 443 Hauptnamensraumseiten mit mindestens zwei ratifizierten Ausgabe-Headern in 443 Werke, 1.886 Ausgaben und 1.886 quellengebundene Web Annotations. 75 Ausgaben sind agentisch bestätigt, 1.810 bleiben Vorschläge und eine Werksbindung ist ausdrücklich strittig.

Aktuelle Kennzahlen stehen in `data/output/quality-report.json`, `data/output/editions/manifest.json` und `data/output/reconciliation/manifest.json`.

## Datenmodell

Der flache Bestand verwendet Schema.org, Dublin Core und das projektspezifische Präfix `klawiter:`. Quellkennungen, Klassifikation, Provenienz und Kurationsstatus bleiben am Eintrag erhalten. Das Vokabular ist unter `docs/vocab/` dokumentiert.

Das Editionsmodell trennt vier Ebenen:

- `schema:CreativeWork` bezeichnet das Werk der jeweiligen MediaWiki-Seite.
- `schema:Book` bezeichnet eine aus einem Ausgabe-Header segmentierte Publikation.
- `oa:Annotation` verbindet jede Ausgabe über einen `oa:TextPositionSelector` mit ihrem exakten Quellausschnitt.
- `schema:PublicationVolume` bezeichnet ausschließlich belegte Träger-Vorkommen. Diese Knoten behaupten keine globale Identität verschiedener Sammelbände.

Strittige Beziehungen sind Teil des finalen Graphen. Ein `klawiter:ContestedClaim` besitzt eine stabile Kennung, den exakten Quellenbezug einschließlich SHA-256, mindestens zwei konkurrierende Deutungen, den Prüfverlauf und `klawiter:decisionStatus = open`. Eine strittige Bindung erscheint weder als `schema:exampleOfWork` noch als `schema:sameAs`. Damit bleiben bestätigte Beziehungen und offene Aussagen maschinell sowie visuell unterscheidbar.

Die Reconciliation trennt Kandidaten, Entscheidungen und publizierbare Links. Der aktuelle Stand umfasst 382 Orts- und 443 Werk-Subjekte. 26 Ortslinks und drei Werklinks beruhen auf belegten `confirm`- oder `correct`-Entscheidungen. Fünf offene Ortsentscheidungen werden als strittige Claims ausgegeben. Die vollständige priorisierte Prüfliste enthält 796 Fälle.

## Einrichtung

Voraussetzungen sind Python 3.11 oder neuer, Node.js für die Frontend-Logiktests und die Quelldateien unter `data/raw/`.

```bash
python -m pip install uv==0.12.5
python -m uv sync --locked
```

`uv.lock` fixiert die Produktions- und Entwicklungsabhängigkeiten. Die Standardausführung verwendet den versionierten LLM-Cache und benötigt weder Netzwerkzugriff noch einen API-Schlüssel.

## Produktionslauf

```bash
python -m uv run python pipeline/run_pipeline.py
```

Der Befehl führt fail-fast aus:

1. SQL- und BLOB-Extraktion, Encoding-Reparatur und Wiki-Parsing;
2. Anwendung des eingefrorenen LLM-Enrichments und regelgebundene Normalisierung;
3. Klassifikation;
4. Werk-/Ausgabe-Segmentierung mit SHACL-, Selektor-, ID-, Queue- und Determinismusprüfung;
5. Entitäts-Reconciliation mit getrennter Kandidaten-, Entscheidungs-, Claim- und Publikationsschicht;
6. JSON-LD- und Frontend-Export;
7. Qualitätsbericht, Round-Trip-Verifikation, Census, Provenienzprojektion, Triage, Korrektur-Overlay und abschließende Reconciliation-Prüfung.

Teilbereiche lassen sich über stabile Stufenkennungen ausführen:

```bash
python -m uv run python pipeline/run_pipeline.py --from-stage 03 --to-stage gate2 --no-postprocess
python -m uv run python pipeline/run_pipeline.py --llm-mode off
```

Ein neuer API-Aufruf ist ausschließlich mit `--llm-mode live` möglich. Dafür muss `GEMINI_API_KEY` gesetzt sein. Live-Ergebnisse werden vor einer Übernahme als neuer eingefrorener Provenienzbestand geprüft.

## Validierung

```bash
python -m uv run pytest -q
python -m uv run pytest -q -m semantic
python -m uv run ruff check pipeline tests
python -m uv run ruff format --check pipeline tests
git diff --check
```

Der Standardsatz prüft Census, Schema, Konsistenz, Regression, Extraktionsregeln, Normalisierung, Provenienz, Korrekturverträge, Editionsmodell, Reconciliation, Produktionsrunner und Frontend-Logik. Die semantische Suite ist separat markiert; ihre verbleibenden bekannten Fehler sind als Grenzen dokumentiert und werden nicht durch gelockerte Assertions verdeckt.

Gate 1 schreibt SHACL- und EARL-Nachweise nach `data/output/editions/`. Gate 2 schreibt Kandidaten, Entscheidungen, publizierbare Links, strittige Claims, Queue, PROV/EARL und Manifest nach `data/output/reconciliation/`. Beide Validatoren bauen ihre Ergebnisse aus den eingefrorenen Eingaben neu auf und vergleichen sie deterministisch.

## Kuration und Reconciliation

Der lokale Editiermodus der Oberfläche erzeugt ein kombiniertes Kurationsdokument. Feldänderungen verwenden `patchVersion: 2`; Reconciliation-Entscheidungen verwenden `reconciliationPatchVersion: 1`. Freigegebene Dateien liegen unter `data/corrections/` und werden bei jedem Produktionslauf erneut angewendet.

Feldkorrekturen bewahren den Maschinenwert im `edit_history` und setzen die Feldprovenienz auf `editor`. Eine neue Normdatenentscheidung ersetzt die vorherige Entscheidung unter Erhalt der Supersessionskette. `unresolved` materialisiert einen offenen Claim. Erst `confirm` oder `correct` erzeugt einen publizierbaren Link.

## Ausgaben und Export

| Artefakt | Inhalt |
|---|---|
| `data/output/klawiter.jsonld` | Vollständiger flacher JSON-LD-Bestand |
| `data/output/entries/` | Regenerierbare JSON-LD-Einzeldateien |
| `docs/data/klawiter.json` | Datengrundlage der statischen Oberfläche |
| `data/output/editions/work-editions.jsonld` | Werk-/Ausgabe-Graph mit Quellenannotationen und strittigen Claims |
| `data/output/editions/review-queue.json` | Vollständige Gate-1-Prüfliste |
| `data/output/reconciliation/` | Kandidaten, Entscheidungen, Claims, publizierbare Links und Nachweise |
| `docs/data/reconciliation.json` | Kompakte Reconciliation- und Claim-Daten für die Oberfläche |

Die Oberfläche exportiert BibTeX und RIS für Zitationszwecke. Der JSON-LD-Einzelexport bindet vorhandene strittige Editionsclaims mit ihren Deutungen und Prüfhandlungen ein. Der vollständige Frontend-Export enthält sowohl strittige Editions- als auch Normdatenclaims. Die kanonischen, vollständig validierten Graphartefakte bleiben die Dateien unter `data/output/`.

## Bekannte Grenzen

- Der flache Bestand bewahrt die historische Ein-Seite-ein-Eintrag-Sicht. Bei Mehrfachausgabenseiten können seine Einzelwerte verschiedene Publikationsblöcke repräsentieren. Für diese Seiten ist `data/output/editions/work-editions.jsonld` die strukturell präzisere Darstellung.
- Fehlende Verlags-, Übersetzer- oder Seitenangaben sind häufig quellenbedingt. Die Pipeline ergänzt keine bibliographischen Werte ohne Fundstelle.
- 1.810 segmentierte Ausgaben sind deterministische Vorschläge. Davon führt Gate 1 317 markierte oder offene Fälle in der priorisierten Prüfliste; die agentische Stichprobe bestätigt ausschließlich ihre 75 exakt geprüften Selektoren.
- Die Bindung von `klawiter:edition/4916-2016-b` an das ursprüngliche Werk oder an ein eigenständiges Graphic-Novel-Adaptionswerk bleibt offen. Beide Deutungen sind im Claim `klawiter:claim/work-binding/4916-2016-b` erhalten.
- Reconciliation-Kandidaten sind Vorschläge. Ungeprüfte und strittige Kandidaten werden in Daten und Oberfläche gezeigt, jedoch nicht als bestätigte Normdatenlinks publiziert.
- Eine spätere externe Fachprüfung erweitert die agentische Evidenz. Sie ist keine Voraussetzung für die Reproduzierbarkeit des gegenwärtigen Stands.

## Repository und Wiedereinstieg

`CLAUDE.md` ist die einzige repository-spezifische Agentenanweisung. `knowledge/index.md` führt durch das kanonische Projektwissen; der jüngste Eintrag in `knowledge/journal.md` hält den terminalen Produktionsstand. Eine zusätzliche `AGENTS.md` ist nicht erforderlich.

Die wichtigsten Verzeichnisse sind:

```text
pipeline/        Produktions- und Prüfcode
tests/           automatisierte und semantische Prüfungen
data/raw/        unveränderte MediaWiki-Quelle
data/output/     erzeugte Daten und Evidenzartefakte
data/provenance/ eingefrorene externe und LLM-Eingaben
data/reconciliation/ belegte Modellierungs- und Normdatenentscheidungen
docs/            statische Oberfläche
knowledge/       kanonisches Projektwissen
```

## Zitation, Credits und Lizenz

Randolph J. Klawiter erarbeitete die zugrunde liegende Bibliographie an der University of Notre Dame. Christopher Pollin verantwortet die digitale Edition. Die maschinenlesbaren Zitationsangaben stehen in `CITATION.cff`.

Der Code steht unter MIT. Dokumentation und strukturierte Edition stehen unter CC BY 4.0. Die Quellbibliographie ist bei einer Nachnutzung gemäß `CITATION.cff` zu nennen; Einzelheiten stehen in `LICENSE`.

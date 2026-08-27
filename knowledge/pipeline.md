---
title: Produktionspipeline
aliases: [pipeline, extraction, transformation, production runner]
project:
  name: Klawiter Bibliography
  repository: https://github.com/chpollin/klawiter-rescue
status: complete
language: de
version: 1.1
tags: [pipeline, reproducibility, provenance]
created: 2026-03-29
updated: 2026-08-27
authors: [Christopher Pollin]
related: [data, testing, frontend, production-readiness]
---

# Produktionspipeline

## Ausführung

Die fixierte Umgebung und der vollständige Produktionslauf werden mit folgenden Befehlen hergestellt:

```bash
python -m pip install uv==0.12.5
python -m uv sync --locked
python -m uv run python pipeline/run_pipeline.py
```

Der Standardlauf verwendet den versionierten LLM-Cache, benötigt keinen API-Schlüssel und führt keine Netzwerkanfrage aus. `--llm-mode off` deaktiviert die eingefrorene Anreicherung. `--llm-mode live` ist eine explizite Neuberechnung mit `GEMINI_API_KEY`; ihr Arbeitscache wird erst nach Prüfung und Übernahme in `data/provenance/` produktiv.

Teilbereiche werden über Stufenkennungen gewählt:

```bash
python -m uv run python pipeline/run_pipeline.py --from-stage 03 --to-stage gate2 --no-postprocess
```

Der Runner beendet sich beim ersten Fehler. Pfade stammen ausschließlich aus `pipeline/lib/config.py`.

## Stufen

| Stufe | Eingabe | Aufgabe | Hauptausgabe |
|---|---|---|---|
| `01` | SQL und BLOBs | Seiten, Slots und Textadressen extrahieren | `01_extracted.csv` |
| `01v` | Dump und Extrakt | Zeilenidentität Dump = Extrakt erzwingen (Stufe-01-Census, harter Fehler) | Census-Prüfung |
| `02` | extrahierte Texte | UTF-8-als-Latin-1-Mojibake reparieren | `02_encoding_fixed.csv` |
| `03` | reparierte Texte | Wiki-Markup und bibliographische Felder parsen | `03_parsed.csv` |
| `03b` | Parsergebnis, eingefrorener Cache | ausschließlich fehlende Felder ergänzen | `03b_llm_enriched.csv` |
| `03c` | angereicherte Werte | Werte normalisieren und unzulässige Werte verwerfen | `03c_normalized.csv` |
| `04` | normalisierte Werte | Eintragstypen und Zeiträume klassifizieren | `04_classified.csv` |
| `gate1` | klassifizierte Quelle, Modellierungsentscheidungen | Werk-/Ausgabe-Graph und Queue erzeugen | `data/output/editions/` |
| `gate1v` | Gate-1-Artefakte | Schema, Selektoren, IDs, Queue und Determinismus prüfen | Validation und EARL |
| `gate2` | Gate 1, Ortsdaten, SZD-Index, Entscheidungen | Kandidaten, Claims und publizierbare Links erzeugen | `data/output/reconciliation/` |
| `05` | klassifizierte Daten, publizierbare Links | JSON-LD und Frontend-Daten erzeugen | `klawiter.jsonld`, `klawiter.json` |
| `06` | JSON-LD | Schema- und Qualitätsbericht erzeugen | `quality-report.json` |

Danach folgen Round-Trip-Verifikation, Census, Provenienzprojektion, Triage, Patch-Replay, die Generierung der dereferenzierbaren Vokabular-Termseiten und die abschließende Gate-2-Prüfung.

## Extraktion und Encoding

Stufe 01 liest MediaWiki-Tabellen und externe Textspeicher direkt. Ein Datenbankserver ist nicht erforderlich. Der Extraktor bewahrt Seiten-, Text- und BLOB-IDs, damit jede spätere Aussage zur Quelle zurückgeführt werden kann.

Stufe 02 repariert bekannte Mojibake-Sequenzen abschnittsweise und idempotent. Die Reparatur wird nur übernommen, wenn die Bytesequenz als UTF-8 validiert. Absichtlich vorhandene Unicode-Zeichen bleiben unverändert.

Stufe 03 kombiniert strukturelles Wiki-Parsing und beleggebundene Muster. Bei fett gesetzten Ausgabe-Headern wie `[1939]` oder `[ca. 1965]` bleibt der MediaWiki-Seitentitel maßgeblich; der Header wird nicht als Werktitel ausgegeben. Leere Quellseiten behalten ihren Seitentitel als Stub.

## Eingefrorene Anreicherung

Stufe 03b füllt ausschließlich leere Felder. Sie überschreibt keinen Parserwert. Der Produktionscache enthält Ergebnis, Quellkennung und Modellprovenienz. Die Ausgabe wird erneut auf Typ, Fundstelle und Encoding geprüft. Der getrennte lokale Arbeitscache gehört nicht zur reproduzierbaren Eingabe.

Stufe 03c normalisiert Publikationsorte, Übersetzer und Seitenangaben. Sie verwirft Werte, deren Form oder Wertebereich den dokumentierten Vertrag verletzt. Eine geringere Abdeckung ist zulässig, wenn sie eine unbelegte Aussage entfernt.

## Gate 1: Segmentierung

`pipeline/lib/editions.py` wählt die 443 Mehrfachausgabenseiten über das ratifizierte Header-Schema aus. Jeder Block beginnt an einem Ausgabe-Header und endet am nächsten Header oder Seitenende. `pipeline/segment_editions.py` erzeugt Werke, Ausgaben, exakte Textselektoren, Annotationen, belegte Träger und Aussagezustände.

Die 76-Fälle-Stichprobe wurde von zwei unabhängigen Agenten geprüft und durch einen unabhängigen stärkeren Verifikations-Agenten reconciliert. Korrekturen und der offene Adaptionsfall liegen unter `data/reconciliation/edition-modeling-decisions.json`. Kein unsicherer Fall wird automatisch bestätigt.

## Gate 2: Reconciliation

`pipeline/lib/reconciliation.py` bildet Kandidaten aus vier eingefrorenen Quellen: historische Ortskandidaten, unabhängige Ortsprüfung, SZD-Werkindex und dem Wikidata-Abgleich für Übersetzer- und Verlagsnamen (`data/provenance/agent-reconciliation.json`, Schwelle fünf Vorkommen). Entscheidungseingaben unter `data/reconciliation/` bleiben davon getrennt. Die Refreezing-Werkzeuge `reconcile_locations.py` und `reconcile_agents.py` kontaktieren das Netz nur mit dem expliziten Schalter `--i-am-refreezing`; der Produktionslauf bleibt netzfrei.

Die Publikationsregel lautet: Nur eine belegte `confirm`- oder `correct`-Entscheidung erzeugt eine Beziehung in `publishable-links.json`. `unresolved` erzeugt einen quellengebundenen `klawiter:ContestedClaim`. `reject` bewahrt die negative Entscheidung, veröffentlicht jedoch keinen Link.

Quellvorkommen werden aus `04_classified.csv` mit Seiten-ID, Text-ID, Zeilennummer, exaktem Text und SHA-256 belegt. Mehrteilige Ortswerte verwenden einen dokumentierten Component-Set-Match. Neue Kurationspatches ersetzen keine Geschichte; die vorherige Entscheidung bleibt in `supersedes` erhalten.

## Export und Oberfläche

Stufe 05 übernimmt aus Gate 2 ausschließlich bestätigte Links. Die flache JSON-LD-Datei enthält alle 6.725 Records. Die Frontend-Datei entfernt Weiterleitungen und ergänzt eine Weiterleitungsmap. `inject_provenance.py` fügt Feldprovenienz aus genau dem gewählten LLM-Modus hinzu.

`docs/data/reconciliation.json` ist eine deterministische Projektion von Kandidaten, Entscheidungen, offenen Claims und Editionsclaims. Laufzeitstempel stehen nur in Audit- und Manifestartefakten und verändern diese öffentliche Datendatei nicht.

## Patch-Replay

`pipeline/apply_patches.py` wendet freigegebene Feldkorrekturen aus `data/corrections/` an. Reconciliation-Patches werden beim Neuaufbau von Gate 2 eingelesen. Beide Patcharten validieren Version, Subjekt, Aktion, Evidenz und erlaubte Felder. Der Produktionslauf bleibt dadurch aus Quellbestand und Entscheidungen vollständig rekonstruierbar.

## Wiederholbarkeit

Gate 1 und Gate 2 bauen ihre Kerndokumente innerhalb der Validatoren erneut auf und vergleichen die Ergebnisse. Zusätzlich wurden zwei vollständige Produktionsläufe mit identischen SHA-256 für den Editionsgraphen, beide Queues, alle Reconciliation-Kerndokumente und den flachen JSON-LD-Bestand ausgeführt. Die UI-Reconciliation-Projektion ist ebenfalls byteidentisch über getrennte Neuaufbauten.

Zeitabhängige Felder sind auf Manifeste, PROV-Aktivitäten, EARL-Berichte und Lauf-Audits begrenzt. Sie dokumentieren den Ausführungszeitpunkt und gehören nicht zum deterministischen Datenkern.

## Grenzen

- Vier Quellseiten besitzen keinen gelieferten Textkörper; eine davon ist bibliographisch.
- Der flache Bestand bleibt für 443 Mehrfachausgabenseiten strukturell ungenau.
- 19 Einträge ohne Parserwert besitzen im eingefrorenen Cache kein LLM-Ergebnis.
- Live-Anreicherung ist absichtlich kein Bestandteil des Standardlaufs.
- Externe Fachprüfung kann die agentische Evidenz erweitern, verändert aber nicht die technische Wiederholbarkeit.

Die aktuellen Ergebnisse und Operator Points stehen in [[production-readiness]], die Prüfkommandos und Aussagegrenzen in [[testing]].

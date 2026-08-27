---
title: Qualitätssicherung
aliases: [testing, tests, validation, quality assurance]
project:
  name: Klawiter Bibliography
  repository: https://github.com/chpollin/klawiter-rescue
status: complete
language: de
version: 1.1
tags: [testing, validation, quality, evidence]
created: 2026-04-01
updated: 2026-08-27
authors: [Christopher Pollin]
related: [data, pipeline, frontend, production-readiness]
---

# Qualitätssicherung

## Prüfkommandos

```bash
python -m uv run pytest -q
python -m uv run pytest -q -m semantic
python -m uv run pre-commit run --all-files
python -m compileall -q pipeline tests
node --test tests/*.test.js
git diff --check
```

Die statischen Prüfungen (ruff check, ruff format) sind in `.pre-commit-config.yaml` definiert; CI führt denselben Hook-Satz aus.

Der Standard-Pytest-Satz schließt die diagnostischen Einzelassertionen mit Marker `semantic` aus. Ein aggregiertes Bound verhindert dennoch, dass die bekannte semantische Abweichungszahl unbemerkt steigt. Die semantische Suite wird separat ausgeführt und darf bekannte, exakt dokumentierte Abweichungen sichtbar melden.

## Testschichten

### Record-Vollständigkeit

`pipeline/census.py` und `tests/test_census.py` prüfen die Identitäten Quelle = JSON-LD und Frontend = JSON-LD minus Weiterleitungen. Fehlende, erfundene und doppelte Records führen zum Fehler. Die eine bibliographische Seite ohne Textkörper ist als benannter Stub explizit begrenzt.

### Schema und Wertebereiche

`tests/test_schema.py` prüft alle Records auf Typen, Jahres- und Seitenbereiche, Sprachcodes, leere Werte, Wiki-Markup und bekannte Encoding-Artefakte. Diese Schicht erkennt strukturelle Fehler, kann jedoch plausible fachlich falsche Werte nicht allein beurteilen.

### Konsistenz und Regression

`tests/test_consistency.py`, `tests/test_heuristic.py` und `tests/test_regression.py` prüfen Querbeziehungen, Verteilungen und bekannte Fehlergrenzen. `.github/baseline-metrics.json` enthält die ratcheting-fähigen Bounds. Eine nachgewiesene Verbesserung senkt einen Fehlerbound oder erhöht die stabile Weiterleitungsauflösung; eine Verschlechterung darf nicht als neue Baseline eingefroren werden.

Der Titel-Fallback verwendet MediaWiki-Seitentitel anstelle von Ausgabe-Headern als Recordtitel; die Weiterleitungskarte enthält zusätzlich Seitentitel-Aliasse aus Stufe 05, wodurch die verbleibenden gebrochenen `seeAlso`-Verweise echte Rotlinks sind. Die eingefrorenen Zählungen stehen in `.github/baseline-metrics.json`.

### Extraktions- und Normalisierungseinheiten

Unit- und Real-Entry-Tests decken Encoding, Wiki-Parser, Feldmuster, Vokabular, Normalisierung, Patch-Replay, Provenienz und den Produktionsrunner ab. Regressionstests bewahren den quellenbedingt leeren Stub und die Behandlung von `[ca. year]`-Headern.

### Werk-/Ausgabe-Gate

Gate 1 prüft den vollständigen Graphen:

- SHACL für Werk, Ausgabe, Annotation, Träger, Claim, Interpretation, ReviewAction und Werkidentitätskandidat;
- exakte Textselektoren und SHA-256;
- stabile und eindeutige Identifikatoren;
- vollständige priorisierte Queue;
- Trennung bestätigter Beziehungen und strittiger Claims;
- deterministischen Neuaufbau aus eingefrorenen Eingaben.

Die Ergebnisse werden in `validation-report.json` und EARL festgehalten.

### Reconciliation-Gate

Gate 2 prüft:

- vollständige Trennung von Kandidat, Entscheidung, offenem Claim und publizierbarem Link;
- exakte Quellenbelege für jeden unresolved Fall;
- Fundstellen oder einen ausformulierten Nullbefund für jedes Agentsubjekt mit Kandidat;
- Supersessionsgeschichte bei Entscheidungspatches;
- Eingabehashes für Editionsgraph, Ortsdaten, Review, Entscheidungen, SZD-Index und klassifizierte Quelle;
- identische JSON-LD- und Frontendprojektion;
- deterministischen Neuaufbau.

`tests/test_reconciliation.py` sichert die Datenverträge, `tests/contested_claims.test.js` die Darstellung und den Export strittiger Aussagen.

### Frontend-Logik

Node-Tests prüfen exakte Fundstellen, Snippetbildung, Triagepriorität, pending/editor-Suppression, Reconciliation-Lookup, stabil sortierten Export, den Routing-Guard samt Editiermodus-Gate und die Ordnung der Kandidaten-Queue der Datenqualitäts-Werkbank. Syntaxprüfungen laufen für alle JavaScript-Module. Ein Browser-Smoke-Test bleibt eine ergänzende visuelle Prüfung.

## Agentisches Review

Die Editionsstichprobe umfasst 76 Segmente aus drei komplexen Seiten. Zwei unabhängige Erstprüfungen arbeiteten gegen Schema, Quellausschnitt und Hash. Ein unabhängiger stärkerer Verifikations-Agent reconciliierte Abweichungen. Das Ergebnis bestätigt 75 Segmente und erhält eine Werkbindung als offenen Claim.

Die Ortsprüfung untersuchte die verbliebenen niedrig bewerteten Fälle unabhängig. Bestätigungen und Korrekturen wurden als Entscheidungen übernommen. Fünf Fälle blieben fachlich offen und wurden als strittige Claims materialisiert.

Agentische Entscheidungen sind durch Reviewer, Eingabehash, Ergebnis und Evidenzdatei nachvollziehbar. Eine spätere externe Fachprüfung ist zusätzliche Validierung.

## Semantische Stichprobe

`tests/wiki_ground_truth.json` enthält zehn gegen die frühere Webdarstellung geprüfte Einträge mit sieben Feldern. Die Stichprobe macht konkrete Feldabweichungen sichtbar, misst aber keine corpusweite Fehlerrate. Mehrfachausgabenseiten dominieren ihre bekannten Fehler.

Die per-Feld-Tests bleiben bewusst separat markiert. Das aggregierte Standardtest-Bound in `.github/baseline-metrics.json` verhindert eine stille Verschlechterung. Nach einer belegten Korrektur wird der Bound nach unten ratcheted.

## Produktionsnachweise

| Nachweis | Aussage |
|---|---|
| `data/output/quality-report.json` | Recordzahlen, Abdeckung und Schemahinweise |
| `data/output/verification-report.json` | Fundstellenbasierte Feldverifikation |
| `data/output/census-report.json` | verlustfreie Record-Kette |
| `data/output/editions/validation-report.json` | Gate-1-Vertrag |
| `data/output/reconciliation/validation-report.json` | Gate-2-Vertrag |
| `data/output/*/earl.jsonld` | maschinenlesbare Prüfergebnisse |
| `data/output/audits/` | Baseline, Wiederholbarkeit und unabhängige Schlussprüfung |

## Aussagegrenzen

Automatisch belegt sind Record-Vollständigkeit, Schema, bekannte Bounds, Selektorintegrität, Entscheidungsseparation und Wiederholbarkeit des Datenkerns. Agentisch belegt sind die dokumentierten Sample- und Low-Score-Entscheidungen.

Zwei strukturelle Grenzen der Round-Trip-Verifikation sind zu benennen. Erstens die Zirkularität: `verify.py` prüft extrahierte Werte gegen denselben Rohtext, aus dem sie extrahiert wurden; eine systematisch falsche, aber im Text vorhandene Zeichenkette besteht die Prüfung. Der Abgleich belegt Quellentreue, keine fachliche Richtigkeit. Zweitens die Teilstring-Schwäche der `correct`-Definition: ein Wert gilt als belegt, sobald er als Teilzeichenkette im Rohtext vorkommt; ein verkürzter oder aus dem falschen Editionsblock stammender Wert kann so als korrekt zählen, besonders auf Mehrfachausgabenseiten. Die Fundstellen-Anzeige im Editiermodus macht Mehrfachvorkommen deshalb explizit.

Nicht belegt sind eine corpusweite fachliche Genauigkeitsquote, die institutionelle Werkidentität der Graphic-Novel-Adaption und die Richtigkeit ungeprüfter Kandidaten (einschließlich des neuen Übersetzer- und Verlags-Prüfvorrats). Die vollständigen Queues halten diese Fälle sichtbar. [[production-readiness]] nennt die verbleibenden Operator Points.

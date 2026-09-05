> Historical completed edition-sample review. The original German record is preserved below. Current model, acceptance scope and counts are maintained in [Data](../../../knowledge/data.md), [Production readiness](../../../knowledge/production-readiness.md) and [Status](../../../knowledge/status.md).

# Stichprobenprüfung der Werk-/Ausgaben-Segmentierung

## Status und Prüfumfang

Dieses Dokument hält das abgeschlossene agentische Stichproben-Gate für die Werk-/Ausgaben-Segmentierung fest. Geprüft wurden sämtliche 76 Ausgabenblöcke auf drei quellenreichen Seiten:

| Seite | Werk | Ausgabenblöcke |
|---:|---|---:|
| 54 | Ungeduld des Herzens | 31 |
| 56 | Die Welt von Gestern | 20 |
| 4916 | Schachnovelle / Volume | 25 |

Die Dateien `*.draft.json` bewahren den ungeprüften Segmentierungsstand. Die Dateien `reviewer-a.json` und `reviewer-b.json` enthalten zwei voneinander unabhängige Prüfungen. `reviews/reconciliation.json` führt ihre Befunde mit einer unabhängigen Verifikation zusammen und ist die kanonische Entscheidungsevidenz dieser Stichprobe.

## Verfahren

Beide Erstprüfungen kontrollierten für jeden Fall die stabile Ausgaben-ID, den Textselektor, den SHA-256-Hash des Quellausschnitts, die extrahierten Felder und die Modellzuordnung. Die anschließende Reconciliation prüfte die 152 Einzelurteile erneut gegen die sechs Eingabedateien und die ratifizierte Werk-/Ausgaben-Spezifikation. Alle 76 Selektoren und Quellausschnitte ließen sich reproduzieren; die beiden Prüfdateien decken dieselbe Fallmenge ab.

Die Reconciliation unterscheidet vier Ergebnisarten:

| Ergebnis | Anzahl | Bedeutung |
|---|---:|---|
| `confirm` | 57 | Segment und Felder sind innerhalb des Prüfvertrags bestätigt. |
| `correct` | 7 | Eine deterministische Feldbereinigung ist umgesetzt und belegt. |
| `reject-proposal` | 11 | Eine Eskalation oder Alternativdeutung der Erstprüfung wurde quellengebunden verworfen; die festgehaltene Behandlung ist bestätigt. |
| `unresolved` | 1 | Die Werkidentität erfordert eine autorisierte fachliche Entscheidung und bleibt quarantänisiert. |

Damit sind 75 Fälle bestätigt. Ein Fall bleibt offen. Kein unsicherer Fall wurde still hochgestuft.

## Umgesetzte Segmentierungsregeln

Die Stichprobe belegt neun eng begrenzte Regeln, die der Vollsegmentierer in `pipeline/lib/editions.py` ausführt:

1. Text hinter einer geschlossenen Fettschriftspanne bleibt als Qualifikator erhalten und verunreinigt den Ort nicht.
2. Ein einzelner Punkt zwischen einem Verlagsnamen auf `Verlag` und einem Ortsnamen dient als Trennzeichen, wenn kein Komma vorhanden ist.
3. Ein terminaler eckiger Reihenzusatz wird aus dem Ortsfeld gelöst und als Rohbeleg bewahrt.
4. Verwaiste schließende Wiki-Klammern werden ausschließlich am Feldende entfernt.
5. Zwei vollständige Publikationsangaben in einem Doppel-Header erzeugen zwei Ausgaben mit gemeinsamem physischem Quellblock.
6. Ein `ca.`-Jahr behält den vierstelligen ID-Anker; `yearRaw` und das Unsicherheitsmerkmal bewahren die Quellform.
7. Die begrenzte Seitennotation `(N)p.` liefert `pageCount = N`; die Rohform bleibt erhalten.
8. Die im Korpus belegte Fehlform `N/M)p.` liefert `pageCount = N`; die Rohform und die Normalisierungskennzeichnung bleiben erhalten.
9. Eine fehlende schließende Fettschriftmarkierung löst ein Diagnosemerkmal aus. Sauber extrahierte Felder behalten ihren Wert.

## Korrigierte Felder

| Ausgabe | Umsetzung |
|---|---|
| `54-1981-c` | Ort `Frankfurt am Main`; Serienresiduum separat bewahrt |
| `54-1981-d` | Ort `Frankfurt am Main`; verwaiste Klammern aus dem normalisierten Feld entfernt |
| `56-1952-a` | Verlag `S. Fischer Verlag`, Ort `Frankfurt am Main`, Reihe separat bewahrt |
| `56-1978-a` | Ort `Frankfurt am Main`, Qualifikator `Special edition` separat bewahrt |
| `56-1981-b` | Ort `Frankfurt am Main`, Reihe separat bewahrt |
| `56-2010-a` | Seitenzahl 463 aus der belegten Rohform `463/1)p.` |
| `4916-1995-a` | Seitenzahl 80 aus der belegten Rohform `(80)p.` |

Die Kopfzeilen `54-1960-a` und `54-1964-a` bleiben zwei Ausgaben mit einem gemeinsamen Textselektor. Die beiden `ca. 1965`-Ausgaben verwenden weiterhin den numerischen Anker `1965`; die ungefähre Datierung bleibt maschinenlesbar erhalten. Der Quellwert `Zũrich` in `54-1957-a` bleibt unverändert. Eine spätere Normdatenform wird als eigene provenienzgebundene Aussage geführt.

## Trägerwerke

Sechs bestätigte Vorkommen erhalten `schema:isPartOf` zu einem minimalen Trägerknoten. Seine ID bezeichnet ausschließlich das konkrete Vorkommen im Quellblock. Eine Zusammenführung gleicher oder ähnlicher Trägerangaben gehört zur späteren Identitätsprüfung.

Betroffen sind `54-1981-d`, `54-1982-a`, `54-1995-a`, `54-2020-a`, `56-1981-c` und `4916-1966-a`. Die normalisierten Trägerbezeichnungen und ihre Entscheidungsgrenze stehen in `data/reconciliation/edition-modeling-decisions.json`.

VIST-Seiten wie Seite 6820 enthalten Vorkommens- und Übersetzungslisten. Ohne passende Ausgaben-Kopfzeilen fallen sie nicht in die Gate-1-Auswahl. Eine spätere Modellierung kann ihre Einträge mit denselben Trägerrelationen erfassen.

## Quarantänisierter Fall

`klawiter:edition/4916-2016-b` beschreibt eine Graphic Novel von Thomas Humeau. Blockgrenze, Verlag, Ort und Seitenzahl sind quellengebunden bestätigt. Die Zuordnung zum Werk `klawiter:work/4916` würde eine eigenständige Adaption als Exemplar der Schachnovelle behandeln. Diese Werkidentität benötigt eine autorisierte Reconciliation.

Der Vollbestand führt deshalb nur `klawiter:workBindingCandidate`. Die Ausgabe fehlt in `schema:workExample`, trägt den Status `unresolved` und das Merkmal `work-identity-quarantine`. Der Fall steht mit Priorität P0 in der kanonischen Prüfliste.

## Übertragung auf den Vollbestand

Der reproduzierbare Gate-1-Lauf verarbeitet alle Seiten im Namensraum 0 mit mindestens zwei passenden vierstelligen oder ungefähren Jahreskopfzeilen. Der aktuelle Bestand umfasst:

| Ergebnis | Anzahl |
|---|---:|
| Werke | 443 |
| Ausgaben | 1.886 |
| Web-Annotationen | 1.886 |
| bestätigte Stichproben-Ausgaben | 75 |
| quarantänisierte Ausgaben | 1 |
| weitere Vorschläge | 1.810 |
| minimale Trägerknoten | 6 |
| priorisierte Prüffälle | 317 |

`pipeline/validate_editions.py` prüft SHACL-Konformität, eindeutige IDs, exakte Textselektoren und Quellhashes, die vollständige Prüflistenabdeckung sowie den deterministischen Neuaufbau. Alle Prüfungen bestehen. Die 1.810 weiteren Vorschläge bleiben als Vorschläge gekennzeichnet; die priorisierte Liste bildet den vollständigen Folgeprüfbestand.

## Evidenz und Reproduktion

- Unabhängige Prüfungen: `data/output/edition-samples/reviews/reviewer-a.json` und `reviewer-b.json`
- Reconciliation: `data/output/edition-samples/reviews/reconciliation.json`
- Modellierungsentscheidungen: `data/reconciliation/edition-modeling-decisions.json`
- Vollgraph: `data/output/editions/work-editions.jsonld`
- PROV-Evidenz: `data/output/editions/provenance.jsonld`
- Prüfliste: `data/output/editions/review-queue.json`
- Validierung: `data/output/editions/validation-report.json` und `earl.jsonld`

```powershell
python pipeline/segment_editions.py
python pipeline/validate_editions.py
python -m pytest -q tests/test_editions.py
```

Eine spätere externe Fachprüfung erweitert die Evidenz. Sie ist keine Voraussetzung für den belegten Gate-1-Produktionslauf.

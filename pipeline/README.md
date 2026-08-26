# Produktionspipeline

Die Pipeline transformiert den MediaWiki-Dump in den flachen JSON-LD-Bestand, den Werk-/Ausgabe-Graphen, die Reconciliation-Schichten und die Daten der statischen Oberfläche.

## Ausführung

```bash
python -m uv run python pipeline/run_pipeline.py
```

Der Standardlauf ist reproduzierbar und netzwerkfrei. Er verwendet den versionierten LLM-Cache. Stufen lassen sich explizit begrenzen:

```bash
python -m uv run python pipeline/run_pipeline.py --from-stage 03 --to-stage gate2 --no-postprocess
python -m uv run python pipeline/run_pipeline.py --llm-mode off
python -m uv run python pipeline/run_pipeline.py --llm-mode live
```

`live` benötigt `GEMINI_API_KEY` und erzeugt einen neuen, vor der Übernahme zu prüfenden Modellbestand.

## Stufen

| ID | Skript | Ergebnis |
|---|---|---|
| `01` | `01_extract.py` | SQL- und BLOB-Inhalte als CSV |
| `02` | `02_fix_encoding.py` | reparierter Quelltext |
| `03` | `03_parse_entries.py` | regelbasiert extrahierte Felder |
| `03b` | `03b_llm_enrich.py` | eingefrorenes oder explizit live erzeugtes Gap-Filling |
| `03c` | `03c_normalize.py` | belegbare Normalisierungen |
| `04` | `04_classify.py` | Eintragstypen und Zeiträume |
| `gate1` | `segment_editions.py` | Werk-/Ausgabe-Graph, Quellenannotationen und strittige Editionsclaims |
| `gate1v` | `validate_editions.py` | SHACL-, Selektor-, ID-, Queue-, Claim- und Determinismusprüfung |
| `gate2` | `reconcile_entities.py` | Kandidaten, Entscheidungen, strittige Claims und publizierbare Links |
| `05` | `05_to_jsonld.py` | flacher JSON-LD- und Frontend-Bestand |
| `06` | `06_validate.py` | Qualitätsbericht |

Nach Stufe `06` führt der Runner `verify.py`, `census.py`, `inject_provenance.py`, `build_triage.py`, `apply_patches.py` und `validate_reconciliation.py` aus.

## Kontrollverträge

Gate 1 segmentiert jede Hauptnamensraumseite mit mindestens zwei vierstelligen oder `ca.`-Ausgabe-Headern. Jede Ausgabe besitzt eine stabile ID, einen exakten `oa:TextPositionSelector` und den SHA-256 ihres Quellblocks. Bestätigte Ausgaben, Vorschläge und strittige Claims bleiben getrennt.

Gate 2 liest Orts- und Werkkandidaten, belegte Entscheidungen und Expert-in-the-Loop-Patches. `confirm` und `correct` erzeugen publizierbare Links. `unresolved` erzeugt einen Claim mit stabiler ID, Quellenfundstellen, konkurrierenden Interpretationen und Prüfverlauf. Stufe `05` liest ausschließlich `data/output/reconciliation/publishable-links.json`.

## Kernmodule

| Modul | Verantwortung |
|---|---|
| `lib/config.py` | Pfade, CSV- und JSON-I/O, Logging |
| `lib/wiki_parser.py` | MediaWiki-Strukturen und Titel |
| `lib/patterns.py` | bibliographische Extraktionsmuster |
| `lib/encoding.py` | Mojibake-Erkennung und -Reparatur |
| `lib/llm_extract.py` | strukturiertes, quellengebundenes LLM-Gap-Filling |
| `lib/editions.py` | deterministische Werk-/Ausgabe-Segmentierung und Claim-Modell |
| `lib/reconciliation.py` | Kandidaten, Entscheidungen, Claims und öffentliche Links |
| `lib/vocabulary.py` | JSON-LD-Kontext und Typabbildung |

Die ausführliche fachliche Begründung steht in `knowledge/pipeline.md` und `knowledge/production-readiness.md`.

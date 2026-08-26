# Klawiter Bibliography — Repository-Anweisungen

Diese Datei ist die einzige repository-spezifische Agentenanweisung. Lege keine parallele `AGENTS.md` an. Fachliche und architektonische Begründungen stehen in `knowledge/`; ausführbare Nutzungshinweise stehen in `README.md`.

## Einstieg

Vor Änderungen:

1. `git status -sb`, aktuellen Branch und jüngste Commits prüfen. Unbekannte Änderungen als fremde oder parallele Arbeit erhalten.
2. `knowledge/index.md` lesen und für die Aufgabe die dort angegebene Lesestrecke verwenden. Der jüngste Eintrag in `knowledge/journal.md` enthält den letzten terminalen Stand.
3. Den aktuellen Code und die erzeugten Manifeste gegen Dokumentationsaussagen prüfen. Volatile Kennzahlen ausschließlich aus `data/output/quality-report.json`, `data/output/editions/manifest.json`, `data/output/reconciliation/manifest.json` und `docs/data/klawiter.json` beziehen.

## Datenintegrität

Bibliographische Werte dürfen nur übernommen werden, wenn sie in der MediaWiki-Quelle belegt sind. Eine quellenbedingte Leerstelle ist ein gültiges Ergebnis. Normdaten-IDs und abgeleitete Geodaten sind zulässig, sobald die zugrunde liegende Entität quellenbelegt und die Zuordnung als eigene Reconciliation-Entscheidung provenienziert ist.

Die LLM-Stufe arbeitet ausschließlich als Gap-Filler. Sie darf bestehende regelbasierte Werte nicht überschreiben. Der Standardlauf verwendet `data/provenance/llm-enrichment-cache.json` und führt keinen Modellaufruf aus. `--llm-mode live` ist eine bewusste, netzwerkabhängige Neuberechnung; ihr Ergebnis wird erst nach Prüfung und aktualisierter Provenienz eingefroren.

Kandidaten, Entscheidungen und publizierte Beziehungen sind getrennte Schichten:

- `proposed` bezeichnet eine deterministische, ungeprüfte Aussage.
- `confirmed` bezeichnet eine exakt quellengebundene, überprüfte Aussage.
- `contested` bezeichnet eine offene Aussage mit stabiler Claim-ID, Quellenbezug, konkurrierenden Deutungen und Prüfverlauf.
- Nur `confirm` und `correct` erzeugen `schema:sameAs` oder eine andere bestätigte Beziehung. `unresolved` erzeugt einen offenen Claim.

Strittige Aussagen bleiben im finalen Datenmodell und in der Oberfläche sichtbar. Sie dürfen weder verworfen noch als bestätigte Beziehung ausgegeben werden.

## Produktionslauf

Abhängigkeiten und Befehle laufen über die fixierte uv-Umgebung:

```bash
python -m uv sync --locked
python -m uv run python pipeline/run_pipeline.py
```

Der Runner führt die Stufen `01`, `02`, `03`, `03b`, `03c`, `04`, `gate1`, `gate1v`, `gate2`, `05`, `06` und danach `verify`, `census`, `provenance`, `triage`, `patches`, `gate2v` fail-fast aus. Teilbereiche werden mit `--from-stage`, `--to-stage` und bei einem Ende vor `06` mit `--no-postprocess` gewählt. Numerische Positionsargumente sind nicht unterstützt.

Relevante Schichten:

- `pipeline/lib/config.py` ist die einzige Pfaddefinition.
- `pipeline/lib/editions.py` und `pipeline/segment_editions.py` erzeugen den vollständigen Werk-/Ausgabe-Graphen des ratifizierten Mehrfachausgaben-Korpus.
- `pipeline/lib/reconciliation.py` und `pipeline/reconcile_entities.py` erzeugen Kandidaten, Entscheidungen, strittige Claims und publizierbare Links.
- `pipeline/05_to_jsonld.py` liest ausschließlich die belegten Links aus `data/output/reconciliation/publishable-links.json`.
- `pipeline/apply_patches.py` spielt freigegebene Feldkorrekturen ein. Reconciliation-Patches werden beim Neuaufbau von Gate 2 eingelesen und bewahren eine Supersessionskette.

## Prüfpflicht

Nach substantiellen Änderungen mindestens die betroffenen Tests und Validatoren ausführen. Vor Commit und Push gilt:

```bash
python -m uv run pytest -q
python -m uv run pytest -q -m semantic
python -m uv run ruff check pipeline tests
python -m uv run ruff format --check pipeline tests
python -m uv run python pipeline/run_pipeline.py
git diff --check
```

Gate 1 muss SHACL, exakte Selektoren und Hashes, stabile IDs, vollständige Queue, Claim-Vertrag und deterministischen Neuaufbau bestehen. Gate 2 muss Entscheidungsseparation, strittige Claims, Eingabehashes, JSON-LD- und Frontendprojektion sowie deterministischen Neuaufbau bestehen. Bekannte semantische Fehler werden dokumentiert und bleiben durch feste Erwartungen sichtbar.

## Code- und Dokumentationskonventionen

- Python 3.11+, uv, Ruff und pytest verwenden. Kein neues Werkzeug einführen, wenn die vorhandene Schicht die Aufgabe trägt.
- Frontend bleibt Vanilla JavaScript und CSS ohne Build-Schritt. Bibliotheken und Fonts liegen lokal unter `docs/vendor/` und `docs/fonts/`.
- Code-Kommentare sind knapp, englisch und beschreiben nur nicht offensichtliche Constraints.
- Projektdokumentation ist deutsch. Bestehende fachliche Begriffe und persistente Identifikatoren dürfen englisch bleiben.
- Erzeugte Dateien über die zuständigen Pipelinefunktionen schreiben; Entscheidungseingaben unter `data/reconciliation/` und eingefrorene externe Eingaben unter `data/provenance/` sind versionierte Quellen.
- Rohdaten unter `data/raw/` nicht verändern. `data/intermediate/` und `data/output/entries/` sind regenerierbar und gitignoriert.

## Bekannte Grenzen

Der flache Bestand modelliert weiterhin eine MediaWiki-Seite als Eintrag. Für die 443 Seiten des ratifizierten Mehrfachausgaben-Korpus ist `data/output/editions/work-editions.jsonld` die präzisere Darstellung. Die agentische Stichprobe bestätigt 75 konkrete Ausgaben; 1.810 Ausgaben bleiben Vorschläge, von denen Gate 1 317 markierte oder offene Fälle priorisiert. Der Adaptionsfall `klawiter:claim/work-binding/4916-2016-b` bleibt fachlich offen. Fünf offene Ortszuordnungen liegen als strittige Reconciliation-Claims vor.

Neue Veröffentlichungsformate, Gate-3-Wiki-/Print-Merge, institutionell inhaltverändernde Entscheidungen und Live-Rückschreibungen in externe Systeme gehören nicht zum Produktionslauf.

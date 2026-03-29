# Architekturentscheidungen

Dokumentation der zentralen Entscheidungen im [[Klawiter-Projekt]] mit Begründung und Trade-offs.

## 1. Domänenspezifisches Vokabular statt Schema.org

**Entscheidung**: Eigener `klawiter:` Namespace statt Schema.org, Dublin Core oder BibFrame.

**Begründung**:
- Die Bibliographie enthält Entitätstypen ohne Schema.org-Pendant (z.B. "Dramatic Reading", "Symposium")
- BibFrame (FRBR-basiert: Work/Instance/Item) wäre korrekt, aber Overengineering für diesen Datensatz
- Dublin Core ist zu flach (keine Typunterscheidung)
- Ein domänenspezifisches Modell kann die Daten 1:1 abbilden

**Trade-off**: Nicht direkt maschinenlesbar für Bibliothekssysteme. Mapping zu Schema.org ist als späterer Schritt vorgesehen — siehe [[Datenmodell#Offenes Mapping]].

## 2. Direkte Datei-Extraktion statt MySQL

**Entscheidung**: SQL-Dump und Binärdateien direkt in Python parsen, ohne MySQL-Installation.

**Begründung**:
- Eliminiert die größte externe Abhängigkeit
- Pipeline wird portabel (läuft überall mit Python 3.10+)
- Die 4-Tabellen-Verknüpfung (page → revision → slots → content) lässt sich direkt aus INSERT-Statements parsen

**Trade-off**: Der SQL-Parser ist fragiler als native MySQL-Queries. Funktioniert aber deterministisch und liefert 99,99% Extraktion.

## 3. Vanilla JS Frontend ohne Framework

**Entscheidung**: HTML + Tailwind (CDN) + vanilla JS. Kein React, Vue, Svelte, Astro.

**Begründung**:
- 4.751 Einträge sind klein genug für vollständiges Client-Side-Rendering
- Kein Build-Step → direkt auf GitHub Pages deploybar
- Keine CI/CD-Konfiguration nötig
- FlexSearch + Chart.js decken Suche und Visualisierung ab

**Trade-off**:
- 8,5 MB JSON muss vollständig geladen werden (kein Lazy Loading)
- Kein SSR/SSG → kein SEO für Einzeleinträge
- State-Management ist manuell (kein reaktives Framework)

## 4. Redirects als Map statt aufgelöste Einträge

**Entscheidung**: 1.545 Redirects werden nicht in die Haupteinträge integriert, sondern als `{ "Titel" → page_id }` Map im Frontend gespeichert.

**Begründung**:
- Redirects sind keine eigenständigen Inhalte, sondern Aliases
- Die Map ermöglicht URL-Auflösung (`#title=Alter+Name` → `#entry=123`)
- Hält die Hauptdaten sauber (4.751 echte Einträge)

**Trade-off**: 314 Redirects (20%) können nicht aufgelöst werden, weil der Zieltitel nicht exakt mit einem existierenden Eintrag übereinstimmt.

## 5. Encoding-Fix vor Parsing

**Entscheidung**: Mojibake wird in Stufe 2 repariert, bevor Stufe 3 die Felder parst.

**Begründung**: Regex-Patterns für Titel, Verlag, Ort etc. funktionieren nur auf korrektem UTF-8. "Insel-Verlag" wird erkannt, "Insel-VÃ©rlag" nicht.

## 6. page_title als Titel-Fallback

**Entscheidung**: Wenn die Titel-Extraktion aus dem Wiki-Markup ein `[year]: Publisher`-Pattern liefert, wird stattdessen der MediaWiki-Seitenname verwendet.

**Begründung**: Bei Sammelwerk-Einträgen steht die Publikationsinfo in der Bold-Zeile (`'''[1922]: Insel-Verlag'''`), nicht der Werktitel. Der page_title enthält immer den korrekten Werknamen.

**Ergebnis**: Bracket-Titel von 1.579 (33%) auf 33 (0,7%) reduziert.

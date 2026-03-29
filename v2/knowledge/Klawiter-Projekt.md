# Klawiter-Projekt

Das Klawiter-Projekt rettet die umfassendste Stefan-Zweig-Bibliographie der Welt aus einer stillgelegten [[MediaWiki-Datenbank]] und überführt sie in ein strukturiertes [[JSON-LD]]-Format mit einer statischen Web-Oberfläche als Wiki-Ersatz.

## Kontext

Die Bibliographie wurde von **Dr. Randolph J. Klawiter** (University of Notre Dame) über Jahrzehnte kompiliert. Sie umfasst **6.296 Einträge** zu Stefan Zweigs Werk: Erstausgaben, Übersetzungen, Sekundärliteratur, Verfilmungen, Korrespondenz — in über 40 Sprachen.

Das ursprüngliche MediaWiki wurde eingestellt. Die Daten existierten nur noch als SQL-Dump mit 8 Binärdateien (363 MB), in denen die Inhalte in einer vierschichtigen Struktur vergraben waren.

## Projektstruktur

- [[Pipeline]] — 6-stufige Extraktion und Transformation
- [[Datenmodell]] — Domänenspezifisches JSON-LD-Vokabular
- [[Datenqualitaet]] — Feldabdeckung, Encoding, bekannte Limitierungen
- [[Frontend]] — Statische Web-Oberfläche (Wiki-Ersatz)
- [[Entitaetstypen]] — Die 16 Kategorien der Bibliographie
- [[Encoding-Problem]] — Das Mojibake-Problem und seine Lösung
- [[Architekturentscheidungen]] — Vokabular, Tech-Stack, Begründungen

## Zahlen

| Metrik | Wert |
|--------|------|
| Gesamteinträge | 6.296 |
| Davon Redirects | 1.545 |
| Inhaltliche Einträge | 4.751 |
| Sprachen | 40+ |
| Zeitraum | 1815–2020 |
| Extraktionsrate | 99,99% |

## Repository

- GitHub: `chpollin/klawiter-rescue`
- Pfad: `v2/` (Pipeline, Frontend, Daten)
- Deployment-Ziel: GitHub Pages

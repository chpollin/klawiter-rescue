# Kurations- und Entscheidungsstore

Dieses Verzeichnis enthält freigegebene Expert-in-the-Loop-Patches. Die Dateien und ihre Git-Historie bilden den Audit-Trail für Feldkorrekturen und Normdatenentscheidungen. Der Browser verändert den Datensatz nie direkt; er exportiert ein Kurationsdokument, das nach Prüfung hier abgelegt wird.

## Feldkorrekturen

Feldpatches verwenden `patchVersion: 2` und werden durch `pipeline/apply_patches.py` nach Provenienzprojektion und Triage eingespielt.

```json
{
  "patchVersion": 2,
  "created": "2026-08-21T20:00:00Z",
  "source": "klawiter-eil-interface",
  "patches": [
    {
      "pageId": 4012,
      "field": "publisher",
      "action": "correct",
      "oldValue": "Leipzig",
      "newValue": "Insel-Verlag",
      "previousProvenance": "llm",
      "edited_by": "Editor (SZD)",
      "edited_at": "2026-08-21T20:00:00Z",
      "source": "human"
    }
  ]
}
```

`action` ist `accept`, `correct` oder `add`. Die letzte chronologische Entscheidung bestimmt den Wert; alle Schritte bleiben im `edit_history`. `oldValue` schützt vor einer stillen Anwendung auf einen veränderten Ausgangsbestand.

## Reconciliation-Entscheidungen

Reconciliation-Patches verwenden `reconciliationPatchVersion: 1`. `pipeline/reconcile_entities.py` liest sie vor dem Gate-2-Neuaufbau.

```json
{
  "reconciliationPatchVersion": 1,
  "reconciliationPatches": [
    {
      "entityType": "location",
      "subject": "Tyresö",
      "action": "confirm",
      "qid": "Q113730",
      "label": "Tyresö Municipality",
      "decisionId": "location/Tyreso/Q113730/editor-2026-08-21",
      "decidedBy": "Editor (SZD)",
      "decidedAt": "2026-08-21T20:00:00Z",
      "evidence": ["source-imprint"],
      "source": "human"
    }
  ]
}
```

Für Werke lautet der Subjektschlüssel `subjectId`; die Zielkennung ist `szdId`. Zulässige Aktionen sind `confirm`, `correct`, `reject` und `unresolved`. Eine neue Entscheidung bewahrt die vorherige Entscheidung als Supersessionsnachweis.

`confirm` und `correct` erzeugen nach erneuter Prüfung einen publizierbaren Link. `reject` entfernt die Kandidaten aus der Publikationsschicht. `unresolved` hält den Fall als stabilen, quellengebundenen Claim mit offenem Entscheidungsstatus im finalen Reconciliation-Artefakt.

Ein kombiniertes Exportdokument darf beide Patchfelder enthalten. Die CI validiert beide Verträge mit denselben Funktionen wie der Produktionslauf.

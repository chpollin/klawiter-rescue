> Historical location-review artifact. Its direct-edit instructions are superseded by the [current reconciliation and patch contract](../corrections/README.md) and [data model](../../knowledge/data.md). Do not use this snapshot as the current production procedure.

# Unmatched Publication Locations — Editor Review Template

This is a **review template for human (editor-in-the-loop) decisions**. Nothing here is applied
automatically. The 22 location strings below are the cases that `pipeline/reconcile_locations.py`
could **not** auto-match against Wikidata: 19 with status `unmatched` (no candidate above the
`MIN_SCORE = 70` threshold) and 3 with status `low_score` (a candidate was returned, but it was a
building/monument, not a settlement). All 22 already carry `lat`/`lng`/`country` in
`docs/data/locations.json` (from an earlier geocoding pass) but lack a `wikidataId`.

The proposed Q-IDs were researched manually via the Wikidata search API
(`wbsearchentities`, English + German) and cross-checked against the existing geocoordinates in
`locations.json`. **Verify each proposal before applying.**

## How to apply an accepted proposal

Three mechanisms, depending on the case classification:

1. **`match-candidate` / `ambiguous` (real place, Q-ID confirmed)** — add the Wikidata fields to the
   entry in `docs/data/locations.json`. The key is the exact location string (left column below).
   Mirror the shape used by already-reconciled entries:
   ```json
   "Girona": {
     "lat": 41.9794, "lng": 2.8214, "country": "ES",
     "wikidataId": "Q7038", "wikidataLabel": "Girona", "wikidataScore": 100,
     "countryQid": "Q29"
   }
   ```
   (`wikidataScore` is informational for manual edits; `countryQid` is optional — the pipeline
   normally fills it via SPARQL.) The frontend reads `locations.json` directly, so the map/geo view
   picks up the Q-ID on next deploy; no pipeline re-run is required for a manual Q-ID add.

2. **Spelling/transliteration variant of an already-matched place** — instead of (or in addition to)
   editing `locations.json`, add a mapping to `pipeline/data/location_normalize.json` so the variant
   collapses onto the canonical name on the next pipeline run, e.g.
   `"Rio de Janiro": "Rio de Janeiro"`, `"Kuala Lampur": "Kuala Lumpur"`. This is the cleaner fix for
   typos and OCR/encoding artifacts, because it removes the duplicate location key entirely rather
   than reconciling a misspelling. **Note:** the canonical target must itself be a `locations.json`
   key; check the existing keys first.

3. **`not-a-place` (parsing artifact / multi-place residue / mojibake)** — do **not** add a Q-ID.
   For location strings there is currently no dedicated reject list (only
   `pipeline/data/publisher_reject_patterns.json` exists, for publishers). The appropriate action is
   either (a) a `location_normalize.json` mapping that rewrites the residue to the intended single
   place, or (b) leaving it as a known coverage gap. If a class of location residue becomes frequent,
   consider adding a `location_reject_patterns.json` analogous to the publisher one — but that is a
   pipeline change, out of scope for this review.

A note on **apostrophes**: several strings in `locations.json` use a straight apostrophe (`'`,
U+0027) while the same place in `docs/data/klawiter.json`'s `location` field uses a typographic
apostrophe (`’`, U+2019) — e.g. `La Tour d'Aigues` vs. `La Tour d’Aigues`. That mismatch is why two
of the strings below show 0 occurrences in `klawiter.json` even though the place clearly appears.
When mapping via `location_normalize.json`, match the exact byte form used by the entries.

---

## Overview table

| # | location string | occ. | classification | proposed QID | wikidata label | conf. | rationale |
|---|---|---|---|---|---|---|---|
| 1 | `Rio de Janiro` | 1 | match-candidate (typo) | Q8678 | Rio de Janeiro | high | Typo of "Rio de Janeiro"; coords (-22.91/-43.17) match Q8678 exactly. Better: normalize to existing key. |
| 2 | `T'aipei` | 14 | match-candidate | Q1867 | Taipei | high | Wade-Giles "T'aipei" = Taipei; coords 25.03/121.57 match Q1867 (25.04/121.56). High frequency — worth fixing. |
| 3 | `Girona` | 6 | match-candidate | Q7038 | Girona | high | Catalan city; coords 41.98/2.82 match Q7038. Reconciler likely missed it as `type=settlement` ambiguity. |
| 4 | `RĀ«ga` | 0 | not-a-place (mojibake) → Riga | Q1773 | Riga | high | Mojibake of "Rīga" (`ī` → `Ā«`). Intended place is Riga (Q1773). Normalize to existing `Riga` key. |
| 5 | `Varna, Sofija` | 1 | ambiguous (two places) | Q6506 / Q472 | Varna / Sofia | med | Two BG cities in one string. locations.json coords (43.21/27.91) = **Varna** (Q6506). Split or pick primary. |
| 6 | `Sofija, Varna` | 1 | ambiguous (two places) | Q472 / Q6506 | Sofia / Varna | med | Mirror of #5. Coords (42.70/23.32) = **Sofia** (Q472). Split or pick primary. |
| 7 | `Soul T'ŭkpyŏlsi, Sŏul-si` | 0 | match-candidate (translit.) | Q8684 | Seoul | high | McCune-Reischauer translit. of "Seoul Teukbyeolsi, Seoul-si" = Seoul. Coords 37.57/126.98 match Q8684. |
| 8 | `Soul-si [Seoul, South Korea]` | 1 | match-candidate (translit.) | Q8684 | Seoul | high | "Soul-si" + bracketed gloss = Seoul. Coords match Q8684. Normalize / bracket-strip would also fix. |
| 9 | `Longpont-sur-Orge` | 2 | match-candidate | Q247627 | Longpont-sur-Orge | high | Commune in Essonne, FR. Single unambiguous hit; coords 48.63/2.29 match. Reconciler likely below threshold on hyphenated name. |
| 10 | `Lannuon` | 2 | match-candidate (Breton) | Q207581 | Lannion | high | Breton name for Lannion (FR). Coords 48.73/-3.46 match Q207581 exactly. (Low-score hit was a school chapel.) |
| 11 | `Montevideo, Uruguay` | 1 | match-candidate | Q1335 | Montevideo | high | "City, Country" form. Coords -34.90/-56.16 match capital Q1335. Strip country suffix to fix. |
| 12 | `La Tour d'Aigues` | 0* | match-candidate | Q625669 | La Tour-d'Aigues | high | FR commune (Vaucluse). Coords 43.73/5.56 match Q625669. *0 occ. due to apostrophe form (’ in entries). |
| 13 | `Villeneuve d'Ascq` | 0* | match-candidate | Q43295 | Villeneuve-d'Ascq | high | FR commune (Nord). Coords 50.62/3.14 match Q43295. *0 occ. due to apostrophe form (’ in entries). |
| 14 | `Bloemfontein, Kaapstad` | 1 | ambiguous (two places) | Q37701 / Q5465 | Bloemfontein / Cape Town | med | Two ZA cities. Coords (-29.09/26.16) = **Bloemfontein** (Q37701). "Kaapstad" = Cape Town (Q5465). Split. |
| 15 | `Kuala Lampur` | 1 | match-candidate (typo) | Q1865 | Kuala Lumpur | high | Typo "Lampur" → "Lumpur". Coords 3.14/101.69 match Q1865. Normalize to "Kuala Lumpur". |
| 16 | `Saint-Aignan` | 1 | no-match (ambiguous, no coords help) | — | (multiple) | low | 5+ FR communes named Saint-Aignan. Coords 47.27/1.38 nearest **Saint-Aignan, Loir-et-Cher** but that commune is "-sur-Cher" (Q832394 @47.27/1.38). Needs editor confirmation. |
| 17 | `Nabeul` | 1 | match-candidate | Q867615 | Nabeul | high | Tunisian town. Coords 36.46/10.74 match Q867615 (note duplicate item Q3117290 exists). |
| 18 | `Scheveningen, Netherlands` | 1 | match-candidate | Q837211 | Scheveningen | high | District of The Hague. Coords 52.11/4.28 match Q837211. (Low-score hit "Bloedpoort" was a city gate.) |
| 19 | `Vestmanna, Streymoy, Faeroe Islands` | 1 | match-candidate | Q608352 | Vestmanna | high | FO settlement on Streymoy. Coords 62.156/-7.164 match settlement Q608352 (not municipality Q945823). |
| 20 | `Kafr El Sheikh, Egypt` | 1 | match-candidate | Q328176 | Kafr el-Sheikh | high | EG city. Coords 31.11/30.94 match city Q328176 (not governorate Q30946). (Low-score hit was the university.) |
| 21 | `Étival-lès-Le Mans` | 1 | match-candidate | Q1224451 | Étival-lès-le-Mans | high | FR commune (Sarthe). Single unambiguous hit; coords 48.05/0.14 match. Diacritics likely tripped reconciler. |
| 22 | `Tyresö` | 1 | match-candidate | Q113730 | Tyresö Municipality | high | SE municipality (Stockholm County). Coords 59.238/18.227 closest to municipality Q113730 (not district Q21667397). |

\* Occurrence count is 0 in `klawiter.json` because the entry uses a typographic apostrophe (’) while
the `locations.json` key uses a straight apostrophe (').

---

## Per-case detail

**1. `Rio de Janiro`** — match-candidate (typo). Single-character typo of the canonical key
"Rio de Janeiro" (which is already matched to Q8678). Cleanest fix: add
`"Rio de Janiro": "Rio de Janeiro"` to `location_normalize.json`. Coordinates confirm the city, not
the state (Q41428) or the Buenos Aires metro station (Q3352487).

**2. `T'aipei`** — match-candidate. Wade-Giles romanization of Taipei (Q1867), capital of Taiwan.
14 occurrences — the most frequent unmatched string, so worth fixing. Coords 25.033/121.565 confirm
the city over New Taipei (Q244898). Add Q1867 to `locations.json` or normalize to "Taipei".

**3. `Girona`** — match-candidate. Catalan city and provincial capital (Q7038); coords 41.98/2.82
match. The reconciler probably returned the family name (Q37487064) or electoral district
(Q24932380) at low confidence. Apply Q7038 directly.

**4. `RĀ«ga`** — not-a-place / mojibake. The sequence `Ā«` is a double-encoding artifact of `ī`;
the intended name is "Rīga" → Riga (Q1773), which is already a separate matched key. This is an
encoding residue, not a distinct location. Recommend `location_normalize.json`: `"RĀ«ga": "Riga"`.
0 occurrences in the frontend JSON, so impact is limited to the JSON-LD / locations table.

**5. `Varna, Sofija`** — ambiguous. Two distinct Bulgarian cities concatenated (a multi-location
publication string). The stored coordinates (43.21/27.91) resolve to **Varna** (Q6506), so if a
single Q-ID is forced it should be Varna. Better: editor decides whether to split into two locations
(Varna Q6506 + Sofia Q472) per the data model.

**6. `Sofija, Varna`** — ambiguous. Same two cities, reversed order; coords (42.70/23.32) resolve to
**Sofia** (Q472). Symmetric to #5. Note #5 and #6 are listed as separate keys only because of word
order — both are multi-place residues from the same kind of source string.

**7. `Soul T'ŭkpyŏlsi, Sŏul-si`** — match-candidate (transliteration). McCune-Reischauer romanization
of "서울특별시, 서울시" (Seoul Special City, Seoul-si) = Seoul (Q8684). Coords 37.57/126.98 confirm.
0 occurrences in frontend JSON. Map to Seoul or normalize.

**8. `Soul-si [Seoul, South Korea]`** — match-candidate. "Soul-si" with a bracketed English gloss;
the reconciler's bracket-stripping (`clean_name`) yields "Soul-si" / "Seoul, South Korea", neither of
which matched cleanly. Target is Seoul (Q8684). Apply Q8684 or add a normalize mapping.

**9. `Longpont-sur-Orge`** — match-candidate. Commune in Essonne, France (Q247627); the only
settlement hit, coords 48.63/2.29 match. Apply Q247627. Likely fell below the score threshold because
the reconciliation endpoint scored the long hyphenated name conservatively.

**10. `Lannuon`** — match-candidate. Breton-language name for **Lannion** (Q207581), a commune in
Côtes-d'Armor. Coords 48.7325/-3.4569 match Q207581 (48.7325/-3.455) exactly. The auto-match returned
a low score (18) for "Chapel Skolaj Sant-Jozef Lannuon" — a school chapel, not the town. Apply Q207581
(or normalize "Lannuon" → "Lannion" if a Lannion key is preferred).

**11. `Montevideo, Uruguay`** — match-candidate. "City, Country" suffix form; the reconciler's state-
suffix rule only strips 2–3-letter uppercase codes, so "Uruguay" stayed. Capital Montevideo (Q1335),
coords -34.90/-56.16. Apply Q1335 or normalize to existing "Montevideo".

**12. `La Tour d'Aigues`** — match-candidate. French commune in Vaucluse (Q625669); coords 43.73/5.56
match. The canonical Wikidata label hyphenates ("La Tour-d'Aigues"). 0 occurrences shown because the
entry text uses a typographic apostrophe; verify the exact key form before mapping. Apply Q625669.

**13. `Villeneuve d'Ascq`** — match-candidate. French commune in Nord (Q43295); coords 50.62/3.14
match. Same apostrophe caveat as #12 (entry uses ’). Apply Q43295.

**14. `Bloemfontein, Kaapstad`** — ambiguous. Two South African cities: Bloemfontein (judicial
capital, Q37701) and Kaapstad = Cape Town (Q5465). Stored coords (-29.09/26.16) resolve to
**Bloemfontein**. Editor decision: split into two locations or pick the primary (Bloemfontein Q37701).

**15. `Kuala Lampur`** — match-candidate (typo). "Lampur" → "Lumpur"; Kuala Lumpur (Q1865), coords
3.14/101.69. Recommend `location_normalize.json`: `"Kuala Lampur": "Kuala Lumpur"`.

**16. `Saint-Aignan`** — no-match (genuinely ambiguous). At least five French communes are named
Saint-Aignan (Morbihan Q127505, Ardennes Q688478, Gironde Q653687, Sarthe Q952806, and the
"-sur-Cher" form Q832394). The stored coordinates 47.27/1.38 sit on **Saint-Aignan-sur-Cher**
(Q832394, Loir-et-Cher) — but the bare string "Saint-Aignan" does not name that commune, so this needs
editor confirmation against the source citation rather than an automatic pick. Left as `no-match`
pending that check; if confirmed, Q832394 is the most likely target.

**17. `Nabeul`** — match-candidate. Tunisian coastal town (Q867615); coords 36.46/10.74 match. Note
Wikidata has a near-duplicate item Q3117290 for the same town — prefer the one with full settlement
statements (Q867615). Apply Q867615.

**18. `Scheveningen, Netherlands`** — match-candidate. District/seaside resort of The Hague (Q837211);
coords 52.11/4.28 match. The low-score auto-hit "Bloedpoort" (Q2149259, a historic city gate) was
spurious. Apply Q837211. (Note: Scheveningen is a district, not an independent municipality — acceptable
as a publication place.)

**19. `Vestmanna, Streymoy, Faeroe Islands`** — match-candidate. "Settlement, island, country" form.
Target is the **settlement** Vestmanna (Q608352, coords 62.156/-7.166), which matches the stored
62.156/-7.164 more closely than the municipality Q945823 (62.153/-7.171). Apply Q608352.

**20. `Kafr El Sheikh, Egypt`** — match-candidate. "City, Country" form; target is the city
Kafr el-Sheikh (Q328176, coords 31.11/30.94), not the governorate (Q30946) or university (Q4115998,
which is what the low-score auto-match returned). Apply Q328176.

**21. `Étival-lès-Le Mans`** — match-candidate. Commune in Sarthe, France (Q1224451); single hit,
coords 48.05/0.14 match. The casing/diacritics ("-lès-Le" vs. Wikidata's "-lès-le") likely lowered
the reconciliation score below threshold. Apply Q1224451.

**22. `Tyresö`** — match-candidate. Swedish locality in Stockholm County. Stored coords 59.238/18.227
are closest to **Tyresö Municipality** (Q113730, 59.233/18.217), not the district Q21667397 (lng 18.30)
or the parish Q10707702. For a publication place the municipality is the conventional choice. Apply Q113730.

---

## Classification summary

- **match-candidate:** 17 — single clear place resolved (#1, 2, 3, 7, 8, 9, 10, 11, 12, 13, 15, 17, 18,
  19, 20, 21, 22). Includes the transliteration/typo cases that collapse onto one settlement.
- **ambiguous (two real places in one string):** 3 (#5, 6, 14)
- **not-a-place (mojibake / encoding residue):** 1 (#4 `RĀ«ga`)
- **no-match (real place, no confident Wikidata pick):** 1 (#16 `Saint-Aignan`)

Total: 17 + 3 + 1 + 1 = 22.

(Note: #1, 4, 7, 8, 11, 15 are also "variant/typo of an existing key" and are best handled via
`location_normalize.json` rather than adding a duplicate Q-ID'd entry.)

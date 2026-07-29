# E-S06 - Synthese replay minimal

- **Experience :** E - Replay minimal
- **Scenario :** E-S06
- **Statut :** valide avec reserves
- **Date :** 2026-07-28T14:29:03Z
- **Objectif :** consolider les preuves E-S01 a E-S05 et conclure sur la viabilite du replay minimal.
- **Reserve :** conclusion hors Unity UI, hors compression finale et hors charge 12 a 20 voitures.

## Decision

- Decision : **validee avec reserves**
- Niveau de confiance : **moyen a bon**
- Scenarios valides : 5 / 5

## Contrat candidat

- Kind : `AutomationLapReplay`
- Schema : `0.1.0`
- Format : JSON readable prototype
- Unites : `s`, `m`, `m/s`, `rad`
- Telemetrie de reference : 4.0 Hz
- Images-cles : toutes les 1.0 s
- Politique version : strict accept list, no automatic migration in prototype

## Preuves consolidees

- E-S01 : replay autonome `55 s`, `221` frames, `3` vehicules, `3` evenements, `148756` octets.
- E-S02 : `9` commandes, `36` samples, `3` clamps, `0` echec de monotonicite.
- E-S03 : `3` sauts evenementiels, `3` contextes valides.
- E-S04 : `5` frequences mesurees, `41831` a `719882` octets, `760.6` a `13088.8` octets/s.
- E-S05 : `10` cas de compatibilite, `0` mismatch.

## Risques residuels

- JSON readable and not optimized; compression or binary packing remains to evaluate.
- Measurements use one deterministic 55 s scenario with 3 vehicles.
- Replay rendering and interpolation are not validated inside Unity UI yet.
- Schema migration is not implemented; incompatible versions are rejected explicitly.
- Advanced event categories, bookmarks and camera metadata are not covered yet.
- Load impact with 12 to 20 vehicles belongs to experiment F.

## Travaux recommandes

- Use the E-S01 replay contract as candidate input for debugging and F load tests.
- Keep 4 Hz telemetry and 1 s keyframes as baseline until F measures cost at scale.
- Design schema migrations only when a second real replay schema exists.

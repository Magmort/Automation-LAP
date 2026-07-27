# A9 - Resultat steering raw graphs

- **Experience :** A - Extraction Automation
- **Statut :** validee
- **Date :** 2026-07-26
- **Version exportee :** `0.1.13-a9-steering-raw-graphs`
- **Dossier source :** `C:\Users\jerem\Documents\Automation LAP Smoke Test`
- **Sortie assemblee :** `outputs/a9-raw-vehicle-data/`

## Objectif

Verifier que la DLL A9 exporte bien les graphes de direction en series brutes completes :

- `LowSpeedSteering`
- `HighSpeedSteering`

avec les series :

- `Speed`
- `Steering`
- `UnderSteer`
- `OverSteer`

## Validation

Les trois exports passent les validateurs :

- `automation-lap-vehicle.json`
- `automation-lap-field-inventory.json`
- `automation-lap-graph-inventory.json`
- `automation-lap-raw-graphs.json`

Les trois documents unifies `automation-lap-raw-vehicle-data.json` ont ete assembles dans `outputs/a9-raw-vehicle-data/` et passent le validateur `AutomationRawVehicleData`.

## Graphes bruts

| Voiture | Graphes bruts | Series | Valeurs | Series tronquees |
|---|---:|---:|---:|---:|
| AIXAM Coupe GTI | 5 | 32 | 23 763 | 0 |
| PCM - Magmort Carcharhini Recif | 5 | 32 | 28 432 | 0 |
| QFC55 - Magmort Carcharhini RCZ | 5 | 32 | 36 309 | 0 |

## Graphes de direction

| Voiture | LowSpeedSteering points | HighSpeedSteering points | Series |
|---|---:|---:|---|
| AIXAM Coupe GTI | 3 764 | 1 525 | `OverSteer`, `Speed`, `Steering`, `UnderSteer` |
| PCM - Magmort Carcharhini Recif | 4 259 | 1 657 | `OverSteer`, `Speed`, `Steering`, `UnderSteer` |
| QFC55 - Magmort Carcharhini RCZ | 5 438 | 2 157 | `OverSteer`, `Speed`, `Steering`, `UnderSteer` |

## Observations

- La limite A9 de `10000` valeurs par serie suffit pour les trois voitures.
- Les graphes `LowSpeedSteering` et `HighSpeedSteering` sont maintenant disponibles dans `rawGraphs`, pas seulement dans `graphInventory`.
- Le validateur A8/A9 reste compatible avec les anciens exports A8.
- L'avertissement `Automation version was not exposed by Lua data` reste non bloquant.

## Decision

A9 est validee.

Les nouveaux exports peuvent remplacer les exports A8 comme entree de travail pour la suite de l'experience B.

## Suite

Reprendre B-S04 avec les graphes de direction bruts pour determiner s'ils peuvent remplacer ou completer le proxy `FrontGripG + RearGripG`.

# A7 - Resultat export complet des courbes ciblees

- **Experience :** A - Extraction Automation
- **Statut :** validee en `0.1.12`
- **Date :** 2026-07-26
- **Exports analyses :** `C:\Users\jerem\Documents\Automation LAP Smoke Test`
- **Version initiale analysee :** `0.1.11-a7-raw-graphs`
- **Version validee :** `0.1.12-a7-json-values-fix`

## Synthese

Les trois voitures reexportees avec `0.1.12-a7-json-values-fix` produisent bien les quatre fichiers attendus :

- `automation-lap-vehicle.json`
- `automation-lap-field-inventory.json`
- `automation-lap-graph-inventory.json`
- `automation-lap-raw-graphs.json`

Les quatre contrats sont valides sur les trois voitures. Les series de `automation-lap-raw-graphs.json` contiennent bien le champ obligatoire `values`, avec une longueur egale au `count` declare.

## Historique du correctif `0.1.11`

Les exports `0.1.11-a7-raw-graphs` avaient echoue car l'encodeur JSON Lua excluait toute cle nommee `values`.

Cette exclusion etait prevue pour le wrapper interne utilise par `json_array`, mais elle s'appliquait aussi aux objets metier. Les series A7 contenaient donc bien les longueurs, min/max et metadonnees, mais le tableau complet de valeurs etait supprime lors de la serialisation.

La correction `0.1.12-a7-json-values-fix` conserve l'exclusion de `__json_kind` mais n'exclut plus la cle `values` pour les objets normaux. Les exports `0.1.12` valident ce correctif.

## Validation des exports `0.1.12`

| Voiture | Vehicle | Field inventory | Graph inventory | Raw graphs A7 |
| --- | --- | --- | --- | --- |
| AIXAM Coupe GTI | valide | valide | valide | valide |
| PCM - Magmort Carcharhini Recif | valide | valide | valide | valide |
| QFC55 - Magmort Carcharhini RCZ | valide | valide | valide | valide |

L'avertissement habituel `Automation version was not exposed by Lua data` reste non bloquant.

## Resultat des courbes completes

Les chemins des graphes ciblees sont corrects et les series sont exportees completement.

| Voiture | AccelerationToTopSpeed | Braking | BrakingVGrip | Series totales | Valeurs exportees | Series tronquees |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| AIXAM Coupe GTI | 17 series x 113 points | 2 series x 98 points | 5 series x 98 points | 24 | 2607 | 0 |
| PCM - Magmort Carcharhini Recif | 17 series x 215 points | 2 series x 159 points | 5 series x 159 points | 24 | 4768 | 0 |
| QFC55 - Magmort Carcharhini RCZ | 17 series x 273 points | 2 series x 184 points | 5 series x 184 points | 24 | 5929 | 0 |

Dans chaque graphe, les longueurs de series sont coherentes, les longueurs de `values` correspondent aux `count`, et aucun diagnostic interne n'est remonte.

## Exemples de plages observees

| Voiture | Acceleration speed max | Braking speed max | BrakingVGrip front force | BrakingVGrip rear force |
| --- | ---: | ---: | ---: | ---: |
| AIXAM Coupe GTI | 115.179 | 113.685 | 2939.046 | 950.064 |
| PCM - Magmort Carcharhini Recif | 223.008 | 220.560 | 4030.895 | 1345.350 |
| QFC55 - Magmort Carcharhini RCZ | 287.795 | 284.945 | 5946.793 | 1917.058 |

Ces valeurs confirment que `BrakingVGrip.Speed` suit la meme plage que `Braking.Speed`.

## Decision

A7 est validee.

Le prototype prouve que les courbes calculees ciblees par Automation peuvent etre exportees integralement et validees de facon independante.

## Prochaine action

Preparer A8 : definir le contrat `AutomationRawVehicleData` v0.1 a partir des champs scalaires confirmes et des graphes complets A7, sans convertir les unites encore inconnues.

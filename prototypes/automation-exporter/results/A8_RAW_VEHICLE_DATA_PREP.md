# A8 - Preparation `AutomationRawVehicleData` v0.1

- **Experience :** A - Extraction Automation
- **Statut :** contrat et outillage prets, valides sur les trois exports locaux
- **Date :** 2026-07-26
- **Source d'entree :** exports `0.1.12-a7-json-values-fix`
- **Contrat produit :** `AutomationRawVehicleData` v0.1

## Objectif

A8 fige un premier contrat brut utilisable par la suite du projet, sans choisir encore le modele physique final.

Le document unifie sert de frontiere propre entre :

- les exports directs d'Automation ;
- les futures conversions d'unites ;
- le futur `VehicleDefinition` exploite par la simulation.

## Fichier cible

```text
automation-lap-raw-vehicle-data.json
```

Ce fichier est assemble hors Automation a partir des quatre fichiers produits par l'exporteur :

- `automation-lap-vehicle.json`
- `automation-lap-field-inventory.json`
- `automation-lap-graph-inventory.json`
- `automation-lap-raw-graphs.json`

## Artefacts ajoutes

```text
prototypes/automation-exporter/schemas/automation-raw-vehicle-data-v0.1.schema.json
prototypes/automation-exporter/samples/raw-vehicle-data.example.json
prototypes/automation-exporter/tools/build_raw_vehicle_data.py
prototypes/automation-exporter/tools/validate_raw_vehicle_data.py
```

## Structure du contrat

Le document A8 contient :

- `source` : provenance Automation, version d'exporteur, horodatage, empreintes SHA-256 des quatre fichiers d'entree ;
- `identity` : modele et trim ;
- `unitPolicy` : valeurs brutes preservees, aucune conversion appliquee, SI seulement comme cible candidate ;
- `controlledFields` : inventaire controle complet des champs scalaires et sondes connues ;
- `graphInventory` : graphes disponibles et enfants assimilables a des series ;
- `rawGraphs` : courbes completes `AccelerationToTopSpeed`, `Braking`, `BrakingVGrip` ;
- `diagnostics` : diagnostics agreges.

Les chemins locaux absolus ne sont pas ecrits dans le document unifie.

## Politique d'unites

A8 ne convertit pas les valeurs.

Les unites deja confirmees restent indiquees champ par champ via `unitSource` et `unitInternalCandidate`. Les unites non confirmees restent explicitement marquees `unknown`. Cette decision evite d'introduire une fausse precision avant l'experience B.

## Validation locale

Les trois exports `0.1.12` ont ete assembles et valides dans :

```text
outputs/a8-raw-vehicle-data/
```

| Voiture | Champs presents | Graphes disponibles | Graphes complets | Series | Valeurs | Diagnostics |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| AIXAM Coupe GTI | 73 / 73 | 10 | 3 | 24 | 2607 | non bloquants |
| PCM - Magmort Carcharhini Recif | 73 / 73 | 10 | 3 | 24 | 4768 | non bloquants |
| QFC55 - Magmort Carcharhini RCZ | 73 / 73 | 10 | 3 | 24 | 5929 | non bloquants |

Diagnostics non bloquants :

- `automation_version_not_exposed`
- `documented_functions_not_called_without_protected_lua_calls`

## Commandes

Assembler un export :

```powershell
python prototypes\automation-exporter\tools\build_raw_vehicle_data.py `
  "C:\chemin\vers\un\dossier\voiture"
```

Valider le document A8 :

```powershell
python prototypes\automation-exporter\tools\validate_raw_vehicle_data.py `
  "C:\chemin\vers\automation-lap-raw-vehicle-data.json"
```

## Decision

A8 est prete pour revue.

Le contrat brut est suffisamment stable pour servir de base a l'experience B, a condition de conserver les exports Automation comme fixtures privees et de ne pas promouvoir automatiquement le prototype Lua vers du code de production.

## Prochaine etape proposee

Faire une revue de cloture de l'experience A :

- confirmer que `AutomationRawVehicleData` v0.1 est le bon format d'entree pour B ;
- identifier les conversions SI immediatement sures ;
- lister les unites restant inconnues ;
- decider si l'on garde l'assembleur Python comme outil de fixture ou si l'on porte le contrat directement dans le futur importeur.
